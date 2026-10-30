"""E2 审计日志防篡改（链式哈希）测试.

覆盖：连续插入成链 / 篡改中间行 / 删除中间行 / 遗留 NULL 行跳过 /
同批次 flush 内成链 / 空表 / limit 截断 / 校验端点返回结构 /
写入串行化锁（PG 取锁、非 PG 放行、取锁先于读末条哈希）。
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, delete, insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from openbase.core.db import audit_chain
from openbase.core.db.audit_chain import (
    AUDIT_CHAIN_LOCK_KEY,
    _acquire_write_lock,
    verify_audit_chain,
)
from openbase.core.models import AuditLog, Base


def _clear_metadata_schema() -> None:
    """SQLite 无 schema 概念：建表前置空（与既有用例同口径）."""
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None


@pytest.fixture()
async def chain_engine(tmp_path):
    """文件型 SQLite 引擎（函数级，表已建好；用例间互不干扰）."""
    _clear_metadata_schema()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit_chain.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def chain_session(chain_engine):
    """会话工厂产出的独立会话（用例内多次 open，模拟多次提交）."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _add_rows(factory, count: int) -> list[int]:
    """分多次提交插入 ``count`` 条审计行，返回按插入顺序的 id 列表."""
    row_ids: list[int] = []
    for index in range(1, count + 1):
        async with factory() as session:
            record = AuditLog(
                user_id=index,
                action=f"test.action.{index}",
                resource="/api/v1/test",
                request_id=f"req-chain-{index}",
                detail={"index": index},
            )
            session.add(record)
            await session.commit()
            row_ids.append(record.id)
    return row_ids


async def _verify(engine, limit: int | None = None) -> dict:
    """用全新会话执行链校验（避免身份映射缓存干扰）."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        return await verify_audit_chain(session, limit=limit)


async def test_three_rows_form_chain_and_verify_ok(chain_engine, chain_session) -> None:
    """连续插入 3 条 → 链成立，verify ok 且 checked=3."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    await _add_rows(factory, 3)

    rows = (
        await chain_session.execute(select(AuditLog).order_by(AuditLog.id.asc()))
    ).scalars().all()
    assert [row.entry_hash is not None for row in rows] == [True, True, True]
    assert rows[0].prev_hash is None
    assert rows[1].prev_hash == rows[0].entry_hash
    assert rows[2].prev_hash == rows[1].entry_hash

    result = await _verify(chain_engine)
    assert result == {"ok": True, "checked": 3, "first_broken_id": None, "reason": None}


async def test_tampered_middle_row_breaks_chain(chain_engine) -> None:
    """篡改中间一条 action → verify 失败，first_broken_id 指向该条."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    row_ids = await _add_rows(factory, 3)

    async with factory() as session:
        await session.execute(
            update(AuditLog)
            .where(AuditLog.id == row_ids[1])
            .values(action="tampered.action")
        )
        await session.commit()

    result = await _verify(chain_engine)
    assert result["ok"] is False
    assert result["first_broken_id"] == row_ids[1]
    assert result["reason"] == "entry_hash_mismatch"


async def test_deleted_middle_row_breaks_chain(chain_engine) -> None:
    """删除中间一条 → verify 失败（后继行 prev_hash 断裂）."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    row_ids = await _add_rows(factory, 3)

    async with factory() as session:
        await session.execute(delete(AuditLog).where(AuditLog.id == row_ids[1]))
        await session.commit()

    result = await _verify(chain_engine)
    assert result["ok"] is False
    assert result["first_broken_id"] == row_ids[2]
    assert result["reason"] == "prev_hash_mismatch"


async def test_legacy_null_rows_skipped(chain_engine) -> None:
    """遗留行（entry_hash=NULL）被跳过且不影响后续链."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)

    # 链前遗留行：Core INSERT 绕过 ORM 单元工作，不发生 before_flush 哈希赋值
    async with factory() as session:
        for index in (1, 2):
            await session.execute(
                insert(AuditLog).values(
                    action=f"legacy.action.{index}",
                    request_id=f"req-legacy-{index}",
                    created_at=dt.datetime.now(dt.timezone.utc),
                )
            )
        await session.commit()

    await _add_rows(factory, 2)

    result = await _verify(chain_engine)
    assert result["ok"] is True
    assert result["checked"] == 2, "遗留行不应计入校验条数"


async def test_same_flush_batch_forms_chain(chain_engine) -> None:
    """同一次 flush 内多条记录形成链（批次内以内存上一条哈希接续）."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    async with factory() as session:
        for index in range(1, 4):
            session.add(
                AuditLog(
                    action=f"batch.action.{index}",
                    request_id=f"req-batch-{index}",
                    detail={"index": index},
                )
            )
        await session.commit()

    async with factory() as session:
        rows = (
            await session.execute(select(AuditLog).order_by(AuditLog.id.asc()))
        ).scalars().all()

    assert len(rows) == 3
    assert rows[0].prev_hash is None
    assert rows[1].prev_hash == rows[0].entry_hash
    assert rows[2].prev_hash == rows[1].entry_hash
    assert (await _verify(chain_engine))["checked"] == 3


async def test_empty_table_verify_ok(chain_engine) -> None:
    """空表 verify 返回 ok=True、checked=0."""
    assert await _verify(chain_engine) == {
        "ok": True,
        "checked": 0,
        "first_broken_id": None,
        "reason": None,
    }


async def test_verify_limit_caps_checked_rows(chain_engine) -> None:
    """limit 限制校验条数（按 id 升序截断）."""
    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    await _add_rows(factory, 3)

    result = await _verify(chain_engine, limit=2)
    assert result["ok"] is True
    assert result["checked"] == 2


def test_advisory_lock_skipped_on_sqlite_dialect(tmp_path) -> None:
    """非 PostgreSQL 方言（SQLite 单写者）不取锁：返回 False 且不执行 SQL."""
    engine = create_engine(f"sqlite:///{tmp_path / 'lock_noop.db'}")
    with Session(engine) as session:
        assert _acquire_write_lock(session) is False
    engine.dispose()


class _StubSession:
    """最小会话桩：用于断言 PG 分支的 SQL 形态（不连真实数据库）."""

    def __init__(self, dialect_name: str) -> None:
        self._dialect_name = dialect_name
        self.executed: list[tuple[str, dict]] = []
        self.no_autoflush = contextlib.nullcontext()

    def get_bind(self) -> SimpleNamespace:
        return SimpleNamespace(dialect=SimpleNamespace(name=self._dialect_name))

    def execute(self, statement, params=None):
        self.executed.append((str(statement), dict(params or {})))
        return None


def test_advisory_lock_uses_parameterized_key_on_postgres() -> None:
    """PostgreSQL 分支：执行 ``pg_advisory_xact_lock`` 且锁键为绑定参数（非拼接）."""
    stub = _StubSession("postgresql")
    assert _acquire_write_lock(stub) is True

    assert len(stub.executed) == 1
    sql_text, params = stub.executed[0]
    assert "pg_advisory_xact_lock" in sql_text
    assert ":lock_key" in sql_text
    assert params == {"lock_key": AUDIT_CHAIN_LOCK_KEY}
    assert str(AUDIT_CHAIN_LOCK_KEY) not in sql_text, "锁键不得内联进 SQL 文本"


async def test_flush_hook_acquires_lock_before_reading_latest_hash(
    chain_engine, monkeypatch
) -> None:
    """flush 钩子先取串行化锁、再读末条哈希（顺序即多实例安全前提）."""
    order: list[str] = []
    original_latest = audit_chain._latest_entry_hash

    monkeypatch.setattr(
        audit_chain,
        "_acquire_write_lock",
        lambda session: (order.append("lock"), True)[1],
    )
    monkeypatch.setattr(
        audit_chain,
        "_latest_entry_hash",
        lambda session: (order.append("read_latest"), original_latest(session))[1],
    )

    factory = async_sessionmaker(chain_engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            AuditLog(action="lock.order.action", request_id="req-lock-order")
        )
        await session.commit()

    assert order == ["lock", "read_latest"]
    assert (await _verify(chain_engine))["ok"] is True


def test_chain_verify_endpoint_shape(tmp_path) -> None:
    """GET /api/v1/audit/chain/verify 返回 {code, message, data{...}}."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openbase.core.db.session import get_db
    from openbase.core.deps.auth import get_current_user
    from openbase.modules.audit import api_router

    _clear_metadata_schema()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit_chain_api.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            for index in range(1, 3):
                session.add(
                    AuditLog(
                        action=f"api.action.{index}",
                        request_id=f"req-api-{index}",
                    )
                )
            await session.commit()

    asyncio.run(_prepare())

    async def _override_get_db():
        async with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(api_router)
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "1",
        "username": "admin",
        "permissions": ["*"],
    }

    response = TestClient(app).get("/api/v1/audit/chain/verify", params={"limit": 100})
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert body["code"] == "OK"
    assert body["data"]["ok"] is True
    assert body["data"]["checked"] == 2
    assert body["data"]["first_broken_id"] is None

    asyncio.run(engine.dispose())
