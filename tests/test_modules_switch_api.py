"""v1.4.6 PATCH /api/v1/modules/{id} 模块开关测试.

覆盖 ADR-146-07 / AC-146-15（Step 3 定案：**先留痕后生效，留痕不可用即拒绝变更**）：

- 权限门禁：无 token 401 / 无 module:manage 403；
- 启用/停用状态变更 + 返回 previous_status / effective=next_login；
- 幂等：同状态重复 → 200 且 previous_status==status（不重复留痕）；
- status 非法 → 422（schema 枚举校验）；
- 模块不存在 → 404（PARAM_404，含 allowed 提示）；
- 语义不变：不改动 id/route_prefix/permission；
- 留痕失败**不改变模块状态**并抛 BIZ 错误：
  ① ``OPENBASE_AUDIT_DB_PERSIST=0``（留痕通道显式不可用）；
  ② 审计落库 commit 失败；
- 状态持久化：dynamic_modules 表（SQLite 会话工厂 + create_all 真实落库），
  读取优先 DB（内存被重置后仍返回持久化状态 = 重启不丢失）；
- 状态落库失败（留痕已成功）→ 回退内存并 WARN，请求仍 200。

测试隔离：默认 ``tests/conftest.py`` 置 ``OPENBASE_AUDIT_DB_PERSIST=0``；
本文件通过 ``sqlite_session_factory`` 夹具显式置 1 并注入 SQLite 会话工厂
（不连真实 PG、不触网）。
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.errors import ErrorCode
from openbase.core.models import AuditLog, Base
from openbase.demo_app import app
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.frontend import ACTION_MODULE_SWITCH, DEFAULT_MODULES, ModuleService

client = TestClient(app)

admin_token = create_access_token("1", username="admin", extra={"permissions": ["*"]})
admin_headers = {"Authorization": f"Bearer {admin_token}"}
user_token = create_access_token("2", username="ops01")
user_headers = {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(autouse=True)
def _restore_module_registry() -> None:
    """用例级隔离：快照并恢复 DEFAULT_MODULES 状态，避免跨用例污染。"""
    snapshot = {item["id"]: item["status"] for item in DEFAULT_MODULES}
    yield
    for item in DEFAULT_MODULES:
        item["status"] = snapshot.get(item["id"], "enabled")


@pytest.fixture
def sqlite_session_factory(monkeypatch: pytest.MonkeyPatch) -> async_sessionmaker:
    """SQLite 内存库会话工厂：注入为全局 session 工厂（留痕 + 状态落库真实写库）.

    说明：demo_app 导入时按 PG 语义把 ``Base.metadata`` 绑定到 openbase schema，
    SQLite 无 schema 概念，故置空后 create_all（与 tests/test_db_modules.py 同口径）。
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _setup() -> None:
        Base.metadata.schema = None
        for table in Base.metadata.tables.values():
            table.schema = None
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr("openbase.core.db.session.get_session_factory", lambda: factory)
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")
    yield factory
    asyncio.run(engine.dispose())


def _audit_module_switch_rows(factory: async_sessionmaker) -> list[dict]:
    """读取 ``audit_logs(action=module.switch)`` 明细（校验留痕内容）。"""

    async def _query() -> list[dict]:
        async with factory() as session:
            statement = (
                select(AuditLog.detail)
                .where(AuditLog.action == ACTION_MODULE_SWITCH)
                .order_by(AuditLog.id)
            )
            return [dict(row) for row in (await session.execute(statement)).scalars().all()]

    return asyncio.run(_query())


def _persisted_status(factory: async_sessionmaker, module_id: str) -> str | None:
    """读取 dynamic_modules 表中持久化状态。"""
    from openbase.core.models import DynamicModule

    async def _query() -> str | None:
        async with factory() as session:
            statement = select(DynamicModule.status).where(DynamicModule.id == module_id)
            return (await session.execute(statement)).scalar_one_or_none()

    return asyncio.run(_query())


# ---- 权限门禁 ----

def test_switch_requires_auth() -> None:
    """无 token → 401. """
    assert client.patch("/api/v1/modules/openllm", json={"status": "disabled"}).status_code == 401


def test_switch_forbidden_without_permission() -> None:
    """普通用户无 module:manage → 403 PERM_403（设计 §5 字面值）.

    v1.4.6 契约对齐：module:manage 权限不足字面值由 AUTH_403 调整为 PERM_403。
    """
    resp = client.patch(
        "/api/v1/modules/openllm", json={"status": "disabled"}, headers=user_headers
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERM_403"


# ---- 状态变更（留痕成功 → 生效） ----

def test_switch_disable_enable_roundtrip(sqlite_session_factory) -> None:
    """enabled→disabled→enabled；响应含 previous_status 与 effective=next_login. """
    r1 = client.patch(
        "/api/v1/modules/openllm", json={"status": "disabled"}, headers=admin_headers
    )
    assert r1.status_code == 200, r1.text[:300]
    data = r1.json()["data"]
    assert data["id"] == "openllm"
    assert data["status"] == "disabled"
    assert data["previous_status"] == "enabled"
    assert data["effective"] == "next_login"
    assert data["request_id"]

    # GET 确认读取到新状态（DB 优先）
    detail = client.get("/api/v1/modules/openllm", headers=admin_headers).json()["data"]
    assert detail["status"] == "disabled"

    r2 = client.patch(
        "/api/v1/modules/openllm", json={"status": "enabled"}, headers=admin_headers
    )
    assert r2.status_code == 200, r2.text[:300]
    assert r2.json()["data"]["status"] == "enabled"
    assert r2.json()["data"]["previous_status"] == "disabled"

    # 两次变更 → 两条留痕（先留痕后生效）
    rows = _audit_module_switch_rows(sqlite_session_factory)
    assert [row["status"] for row in rows] == ["disabled", "enabled"]
    assert rows[0]["previous_status"] == "enabled"
    assert rows[0]["module_id"] == "openllm"
    assert rows[0]["operator_id"] == "1"


def test_switch_idempotent_same_status(sqlite_session_factory) -> None:
    """同状态重复 → 200 且 previous_status==status（幂等，不重复留痕）. """
    r1 = client.patch("/api/v1/modules/knowledge", json={"status": "disabled"}, headers=admin_headers)
    assert r1.status_code == 200, r1.text[:300]
    r2 = client.patch("/api/v1/modules/knowledge", json={"status": "disabled"}, headers=admin_headers)
    assert r2.status_code == 200, r2.text[:300]
    data = r2.json()["data"]
    assert data["status"] == "disabled"
    assert data["previous_status"] == "disabled"  # 无变更标记
    assert len(_audit_module_switch_rows(sqlite_session_factory)) == 1, "幂等请求不得重复留痕"


def test_switch_invalid_status_validation() -> None:
    """status 非法 → 400 `PARAM_400`（schema 枚举白名单；v1.4.6 Step 4 裁定）."""
    resp = client.patch(
        "/api/v1/modules/openllm", json={"status": "paused"}, headers=admin_headers
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "PARAM_400"


def test_switch_unknown_module_not_found() -> None:
    """模块不存在 → 404 PARAM_404，detail 含 allowed 清单. """
    resp = client.patch(
        "/api/v1/modules/nosuchmodule", json={"status": "disabled"}, headers=admin_headers
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "PARAM_404"
    assert "nosuchmodule" in (body.get("detail") or {}).get("module_id", "")


def test_get_unknown_module_not_found() -> None:
    """GET 单模块不存在 → 404 PARAM_404（v1.4.6 契约对齐：与原 PATCH 双码统一）.

    v1.4.6 裁定：同资源 GET/PATCH 在模块不存在时应返回同一错误码 PARAM_404，
    消除 BIZ_404 与 PARAM_404 的双码歧义（设计 §5 仅定义 PARAM_404）。
    """
    resp = client.get("/api/v1/modules/nosuchmodule", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "PARAM_404"


def test_switch_semantics_unchanged(sqlite_session_factory) -> None:
    """语义不变：开关不动 id/route_prefix/permission. """
    before = ModuleService().get_module("gateway")
    resp = client.patch(
        "/api/v1/modules/gateway", json={"status": "disabled"}, headers=admin_headers
    )
    assert resp.status_code == 200, resp.text[:300]
    after = ModuleService().get_module("gateway")
    for key in ("id", "route_prefix", "permission", "entry"):
        assert before[key] == after[key], f"字段 {key} 被改动"


# ---- 状态持久化（dynamic_modules） ----

def test_switch_status_persisted_and_survives_restart(sqlite_session_factory) -> None:
    """状态落 dynamic_modules；内存被重置（模拟进程重启）后仍从 DB 读回新状态. """
    resp = client.patch(
        "/api/v1/modules/memory", json={"status": "disabled"}, headers=admin_headers
    )
    assert resp.status_code == 200, resp.text[:300]
    assert _persisted_status(sqlite_session_factory, "memory") == "disabled"

    # 模拟进程重启：仅内存注册表回退到出厂值，DB 状态保留
    for item in DEFAULT_MODULES:
        if item["id"] == "memory":
            item["status"] = "enabled"

    detail = client.get("/api/v1/modules/memory", headers=admin_headers).json()["data"]
    assert detail["status"] == "disabled", "读取未优先 DB（重启即回退内存 = 语义不符）"
    listed = client.get("/api/v1/modules", headers=admin_headers).json()["data"]["items"]
    assert {item["id"]: item["status"] for item in listed}["memory"] == "disabled"


def test_switch_status_write_failure_falls_back_to_memory(
    sqlite_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """留痕成功但状态落库失败 → 回退内存并 WARN，请求仍 200（状态在进程内生效）. """
    from openbase.modules.frontend.repository import ModuleStatusRepository

    async def _broken_upsert(*args, **kwargs) -> None:
        raise RuntimeError("dynamic_modules write down")

    monkeypatch.setattr(ModuleStatusRepository, "upsert_status", _broken_upsert)

    resp = client.patch(
        "/api/v1/modules/portrait", json={"status": "disabled"}, headers=admin_headers
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["data"]["status"] == "disabled"
    assert ModuleService().get_module("portrait")["status"] == "disabled"  # 内存已生效
    assert _persisted_status(sqlite_session_factory, "portrait") is None  # 未落库
    assert len(_audit_module_switch_rows(sqlite_session_factory)) == 1  # 留痕仍在


# ---- 留痕失败 → 变更失败并回滚（Step 3 定案） ----

def test_switch_audit_disabled_rejects_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """``OPENBASE_AUDIT_DB_PERSIST=0`` = 留痕通道不可用 → 变更失败且状态不变. """
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "0")
    resp = client.patch(
        "/api/v1/modules/openllm", json={"status": "disabled"}, headers=admin_headers
    )
    assert resp.status_code != 200, resp.text[:300]
    body = resp.json()
    assert body["code"] == ErrorCode.BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE.value
    assert body["code"].startswith("BIZ")
    assert (body.get("detail") or {}).get("module_id") == "openllm"
    # 状态未被改变（未生效，无需回滚）
    assert ModuleService().get_module("openllm")["status"] == "enabled"
    assert client.get("/api/v1/modules/openllm", headers=admin_headers).json()["data"][
        "status"
    ] == "enabled"


def test_switch_audit_commit_failure_rejects_and_keeps_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """留痕 commit 失败 → 抛 BIZ 错误，模块状态保持不变（不静默生效）. """

    class _FakeDbSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, obj: object) -> None:
            self.added.append(obj)

        async def commit(self) -> None:
            raise RuntimeError("db down")

        async def rollback(self) -> None:
            pass

    fake_session = _FakeDbSession()

    class _FakeCM:
        def __init__(self) -> None:
            self.session = fake_session

        async def __aenter__(self) -> _FakeDbSession:
            return self.session

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    def fake_factory():
        def make_cm_factory():
            return _FakeCM()

        return make_cm_factory

    monkeypatch.setattr("openbase.core.db.session.get_session_factory", fake_factory)
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")

    resp = client.patch(
        "/api/v1/modules/openllm", json={"status": "disabled"}, headers=admin_headers
    )
    assert resp.status_code != 200, resp.text[:300]
    assert resp.json()["code"] == ErrorCode.BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE.value
    # 留痕失败 → 状态不变（定案口径：变更失败并回滚）
    assert ModuleService().get_module("openllm")["status"] == "enabled"
    assert fake_session.added, "应尝试 add 一条 AuditLog"
