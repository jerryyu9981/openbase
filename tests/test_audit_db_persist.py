"""C-4 审计记录落库测试（TDD：先 RED，后实现）.

设计依据：《OpenBase-人工端到端测试日志记录方案》§5 批 1 C-4（审计记录异步落 DB，
复用 ``audit_logs``（D-2=①，JSON 扩展字段零迁移），best-effort：失败仅 WARN 不阻断）、
§6 验收（持久性：服务重启后仍可查询）、§7/§9.1 决议。

测试策略：持久化路径用「记录型假会话」验证（确定性、无外部依赖）；查询路径用
内存 SQLite 真实建表验证（与既有 `tests/test_rbac_db.py` 同法）。
"""

from __future__ import annotations

import asyncio
import logging
import types

import pytest
from starlette.requests import Request as StarletteRequest

from openbase.modules.audit import (
    ACTION_API_REQUEST,
    ENV_AUDIT_DB_PERSIST,
    APICallRecord,
    AuditMiddleware,
    query_audit_logs_by_case,
)


class _RecordingSession:
    """记录 add/commit/rollback 的假会话（DB 免依赖断言）."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FailingSession(_RecordingSession):
    async def commit(self) -> None:
        raise RuntimeError("db down")


def _patch_session_factory(monkeypatch: pytest.MonkeyPatch, session: object) -> None:
    import importlib

    session_mod = importlib.import_module("openbase.core.db.session")

    class _SessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc: object) -> bool:
            return False

    class _FakeFactory:
        def __call__(self) -> _SessionCM:
            return _SessionCM()

    monkeypatch.setattr(session_mod, "get_session_factory", lambda: _FakeFactory())


def _scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/dps-proxy/portraits",
        "raw_path": b"/api/v1/dps-proxy/portraits",
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }


def _request_with_case() -> StarletteRequest:
    request = StarletteRequest(_scope())
    request.state.request_id = "req-db-1"
    request.state.test_case_id = "UI-DPS-0007"
    request.state.test_step_id = 3
    request.state.test_run_id = "run-db-1"
    request.state.user_id = "42"
    request.state.tenant_id = "acme"
    return request


def _request_with_case_headers() -> StarletteRequest:
    """带用例上下文**请求头**的请求（dispatch 以头为准并重写 state）。"""
    headers = [
        (b"x-test-case-id", b"UI-DPS-0007"),
        (b"x-test-step-id", b"3"),
        (b"x-test-run-id", b"run-db-1"),
    ]
    return StarletteRequest(_scope(headers))


def _sample_record() -> APICallRecord:
    return APICallRecord(
        method="GET",
        path="/api/v1/dps-proxy/portraits",
        status_code=200,
        duration_ms=12,
        request_id="req-db-1",
        operator_id="42",
        tenant_id="acme",
        ip_address="127.0.0.1",
        user_agent="pytest",
        extra={
            "case_id": "UI-DPS-0007",
            "step_id": 3,
            "run_id": "run-db-1",
            "channel": "B",
        },
    )


# ---------------------------------------------------------------------------
# 落库（best-effort）
# ---------------------------------------------------------------------------


def test_persist_audit_record_writes_audit_log_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """落库：action=api.request，request_id 与入站一致，用例字段入 detail（JSON 零迁移）。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    asyncio.run(middleware._persist_audit_record(_request_with_case(), _sample_record()))

    assert session.committed is True
    assert len(session.added) == 1
    row = session.added[0]
    assert row.action == ACTION_API_REQUEST
    assert row.request_id == "req-db-1"
    assert row.resource == "/api/v1/dps-proxy/portraits"
    assert row.user_id == 42
    assert row.ip == "127.0.0.1"
    assert row.detail["case_id"] == "UI-DPS-0007"
    assert row.detail["step_id"] == 3
    assert row.detail["run_id"] == "run-db-1"
    assert row.detail["channel"] == "B"
    assert row.detail["status_code"] == 200
    assert row.detail["duration_ms"] == 12


def test_persist_audit_record_disabled_by_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开关关闭（默认在测试环境关闭）：完全不触碰 DB。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "0")
    import importlib

    session_mod = importlib.import_module("openbase.core.db.session")

    def _boom() -> None:
        raise AssertionError("开关关闭时不得访问 DB")

    monkeypatch.setattr(session_mod, "get_session_factory", _boom)

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    asyncio.run(middleware._persist_audit_record(_request_with_case(), _sample_record()))


def test_persist_audit_record_degrades_without_blocking(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """落库失败降级：仅 WARN + 回滚，不抛出（不阻断请求）。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _FailingSession()
    _patch_session_factory(monkeypatch, session)

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    with caplog.at_level(logging.WARNING, logger="openbase.audit"):
        asyncio.run(
            middleware._persist_audit_record(_request_with_case(), _sample_record())
        )

    assert session.rolled_back is True
    assert any(r.levelno == logging.WARNING for r in caplog.records), "缺少降级 WARN"


def test_dispatch_persists_audit_record_after_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dispatch 响应后接线：内存缓冲 + DB 落库（同 request_id）。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)

    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = _request_with_case_headers()

    async def _call_next(_request: StarletteRequest) -> types.SimpleNamespace:
        return types.SimpleNamespace(status_code=201, headers={})

    from openbase.modules.audit import AuditService

    AuditService._records.clear()
    response = asyncio.run(middleware.dispatch(request, _call_next))

    assert response.status_code == 201
    assert len(session.added) == 1
    assert session.added[0].request_id == request.state.request_id
    assert session.added[0].request_id.startswith("req-")
    assert session.added[0].detail["case_id"] == "UI-DPS-0007"
    assert session.added[0].detail["run_id"] == "run-db-1"
    AuditService._records.clear()


# ---------------------------------------------------------------------------
# 按 case_id 查询（跨重启查询路径；内存 SQLite 真实建表）
# ---------------------------------------------------------------------------


def _sqlite_rows(case_id: str | None, run_id: str | None) -> list[dict]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from openbase.core.models import AuditLog, Base

    async def _scenario() -> list[dict]:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for index, (case, run) in enumerate(
                (("UI-DPS-0007", "run-1"), ("S7-T2-1", "run-2")), start=1
            ):
                session.add(
                    AuditLog(
                        action=ACTION_API_REQUEST,
                        request_id=f"req-q{index}",
                        detail={"case_id": case, "run_id": run, "channel": "B"},
                    )
                )
            await session.commit()
            rows = await query_audit_logs_by_case(session, case_id=case_id, run_id=run_id)
        await engine.dispose()
        return rows

    return asyncio.run(_scenario())


def test_query_audit_logs_by_case_id() -> None:
    """DB 查询：按 case_id 过滤（跨重启持久化后的检索口）。"""
    rows = _sqlite_rows("UI-DPS-0007", None)

    assert [row["request_id"] for row in rows] == ["req-q1"]
    assert rows[0]["detail"]["case_id"] == "UI-DPS-0007"


def test_query_audit_logs_by_run_id() -> None:
    """DB 查询：按 run_id 过滤。"""
    rows = _sqlite_rows(None, "run-2")

    assert [row["request_id"] for row in rows] == ["req-q2"]


def test_query_audit_logs_without_filter_returns_all() -> None:
    """DB 查询：无过滤条件返回全部（按 id 倒序）。"""
    rows = _sqlite_rows(None, None)

    assert [row["request_id"] for row in rows] == ["req-q2", "req-q1"]
