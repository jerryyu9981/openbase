"""P3 治理批次（G-01~G-03）测试.

- G-01：ABAC 策略变更采用「超管直改 + 事后审计」口径——审计明细含
  ``review_mode=post_audit`` 与变更前快照，并输出结构化 WARN 供事后复核；
- G-02：角色授予路径强制三权分立校验，冲突统一 ``PERM_DUTY_CONFLICT``（HTTP 409）；
- G-03：ABAC 规则规模与判定耗时基线——超阈值输出结构化 WARN（可配），
  非正阈值拒绝启动。
"""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.db import audit_chain  # noqa: F401 - 导入即注册链式哈希钩子
from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode, ERROR_HTTP_MAP, install_exception_handlers
from openbase.core.models import AuditLog, Base
from openbase.modules.auth.abac_policy_store import ABAC_CHANGE_REVIEW_MODE
from openbase.modules.auth.access_api import router as access_router
from openbase.modules.auth.access_control import (
    DUTY_AUDIT_ADMIN,
    DUTY_SECURITY_ADMIN,
    DUTY_SYSTEM_ADMIN,
    AbacRule,
    evaluate_abac,
    ensure_role_grant_allowed,
)
from openbase.settings import Settings


def _clear_metadata_schema() -> None:
    """SQLite 无 schema 概念：建表前置空（与既有用例同口径）."""
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None


async def _create_schema(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture()
def sqlite_engine(tmp_path):
    """文件型 SQLite 引擎（函数级，表已建好）."""
    _clear_metadata_schema()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'p3_governance.db'}"
    )
    asyncio.run(_create_schema(engine))
    yield engine
    asyncio.run(engine.dispose())


def _override_get_db(factory):
    """构造 ``get_db`` 覆写（返回独立会话）."""

    async def _get_db():
        async with factory() as session:
            yield session

    return _get_db


def _admin_identity() -> dict:
    """超管身份（权限通配）."""
    return {"id": "1", "username": "admin", "permissions": ["*"]}


def _access_app(sqlite_engine, monkeypatch) -> tuple[FastAPI, object]:
    """最小应用：仅挂载 ABAC 鉴权域路由."""
    import openbase.modules.auth.access_api as access_api

    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    monkeypatch.setattr(
        access_api, "get_settings", lambda: SimpleNamespace(abac_policies="")
    )
    app = FastAPI()
    app.include_router(access_router)
    install_exception_handlers(app)
    app.dependency_overrides[get_db] = _override_get_db(factory)
    app.dependency_overrides[get_current_user] = _admin_identity
    return app, factory


def _audit_details(factory) -> list[dict]:
    """读取 ABAC 策略审计明细（升序）."""

    async def _query() -> list[dict]:
        async with factory() as session:
            result = await session.execute(
                select(AuditLog.detail)
                .where(AuditLog.resource == "abac_policy")
                .order_by(AuditLog.id.asc())
            )
            return [dict(row) for row in result.scalars().all()]

    return asyncio.run(_query())


# ---- G-01：超管直改 + 事后审计 ----


def test_abac_policy_change_carries_post_audit_marker_and_snapshot(
    sqlite_engine, monkeypatch, caplog
) -> None:
    """新增/更新/删除均留事后审计标记与变更前快照，并输出 WARN."""
    app, factory = _access_app(sqlite_engine, monkeypatch)

    with caplog.at_level(logging.WARNING, logger="openbase.auth.abac_policy_store"):
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/auth/access/policies",
                json={"name": "deny-key-issue", "effect": "deny", "permission": "key:issue"},
            )
            assert created.status_code == 200, created.text
            policy_id = created.json()["data"]["id"]

            updated = client.put(
                f"/api/v1/auth/access/policies/{policy_id}",
                json={
                    "name": "deny-key-issue-v2",
                    "effect": "allow",
                    "permission": "key:issue",
                },
            )
            assert updated.status_code == 200, updated.text

            removed = client.delete(f"/api/v1/auth/access/policies/{policy_id}")
            assert removed.status_code == 200, removed.text

    details = _audit_details(factory)
    assert [detail["review_mode"] for detail in details] == [ABAC_CHANGE_REVIEW_MODE] * 3
    assert details[0]["previous"] is None
    # 更新留变更前快照（名称/效果），供事后复核
    assert details[1]["previous"]["name"] == "deny-key-issue"
    assert details[1]["previous"]["effect"] == "deny"
    assert details[1]["name"] == "deny-key-issue-v2"
    # 删除留删除前快照
    assert details[2]["previous"]["name"] == "deny-key-issue-v2"

    warnings = [
        record for record in caplog.records if "without dual review" in record.getMessage()
    ]
    assert len(warnings) == 3
    assert all(record.levelno == logging.WARNING for record in warnings)


# ---- G-02：角色授予强制三权分立 ----


def test_role_grant_conflict_raises_perm_duty_conflict() -> None:
    """互斥职责同授 → ``PERM_DUTY_CONFLICT`` 且映射 HTTP 409."""
    with pytest.raises(BaseError) as excinfo:
        ensure_role_grant_allowed([], [DUTY_SYSTEM_ADMIN, DUTY_AUDIT_ADMIN])
    error = excinfo.value
    assert error.code == ErrorCode.PERM_DUTY_CONFLICT
    assert ERROR_HTTP_MAP[ErrorCode.PERM_DUTY_CONFLICT] == 409
    assert "system_admin" in str(error)


def test_role_grant_union_blocks_additive_conflict() -> None:
    """增量授予（不替换）在既有角色与新角色并集上判定冲突."""
    with pytest.raises(BaseError):
        ensure_role_grant_allowed([DUTY_SECURITY_ADMIN], [DUTY_AUDIT_ADMIN])


def test_role_grant_replace_semantics_clears_conflict() -> None:
    """替换授予以「结果角色集」为准，不因历史冲突误拒（可整改）."""
    ensure_role_grant_allowed(
        [DUTY_SYSTEM_ADMIN, DUTY_AUDIT_ADMIN], ["viewer"], replace=True
    )
    ensure_role_grant_allowed([], ["viewer"])


# ---- G-03：ABAC 规模与耗时基线 ----


def _rules(count: int) -> tuple[AbacRule, ...]:
    return tuple(
        AbacRule(effect="allow", permission=f"perm:demo{index}")
        for index in range(count)
    )


def test_abac_rule_count_over_soft_limit_warns_with_index_hint(caplog) -> None:
    """规则数超软上限 → WARN 并提示「需索引/缓存」."""
    with caplog.at_level(logging.WARNING, logger="openbase.auth.access_control"):
        evaluation = evaluate_abac(
            _rules(12),
            permission="perm:demo1",
            subject_tenant="",
            resource_tenant="",
            roles=(),
            soft_limit=10,
            warn_ms=10_000,
        )
    assert evaluation.decision == "allow"
    hints = [
        record for record in caplog.records if "soft limit" in record.getMessage()
    ]
    assert len(hints) == 1
    assert hints[0].levelno == logging.WARNING
    assert getattr(hints[0], "rule_count") == 12


def test_abac_slow_evaluation_warns(caplog) -> None:
    """耗时达阈值 → 结构化 WARN（携带 elapsed_ms / rule_count）."""
    with caplog.at_level(logging.WARNING, logger="openbase.auth.access_control"):
        evaluate_abac(
            _rules(3),
            permission="perm:demo1",
            subject_tenant="",
            resource_tenant="",
            roles=(),
            warn_ms=0,
            soft_limit=10_000,
        )
    slow = [record for record in caplog.records if "slow" in record.getMessage()]
    assert len(slow) == 1
    assert getattr(slow[0], "elapsed_ms") is not None
    assert getattr(slow[0], "rule_count") == 3


def test_abac_evaluation_within_thresholds_stays_quiet(caplog) -> None:
    """阈值内不产生 WARN（避免日志洪泛）."""
    with caplog.at_level(logging.WARNING, logger="openbase.auth.access_control"):
        evaluation = evaluate_abac(
            _rules(2),
            permission="perm:demo0",
            subject_tenant="",
            resource_tenant="",
            roles=(),
            warn_ms=10_000,
            soft_limit=10_000,
        )
    assert evaluation.decision == "allow"
    assert caplog.records == []


def test_settings_reject_non_positive_abac_baseline() -> None:
    """G-03 阈值配置非正 → 启动门禁拒绝."""
    assert Settings(abac_rule_soft_limit=1000).abac_rule_soft_limit == 1000
    with pytest.raises(ValueError):
        Settings(abac_rule_soft_limit=0)
    with pytest.raises(ValueError):
        Settings(abac_evaluation_warn_ms=-1)
