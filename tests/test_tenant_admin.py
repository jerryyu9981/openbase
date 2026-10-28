"""v1.4.2 R-374 租户管理 API 测试（TDD RED→GREEN）.

覆盖：租户 CRUD（创建/列表/详情/更新/停用）+ 配额读写 + 权限（401/403）+ 既有端点兼容。
数据落库（SQLite 文件库），admin/viewer 为 DB 种子用户。
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.models import Base, Role, User, user_role
from openbase.modules.auth import hash_password
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_tenant_v142.db"

# 本模块专用 SQLite 会话工厂（与全局单例解耦；见模块级 fixture 说明）
_session_factory: async_sessionmaker | None = None


def _build_app() -> TestClient:
    global _session_factory

    settings = Settings()
    for module in ("auth", "tenant", "users", "audit", "config", "org", "dict", "storage", "notify"):
        settings.enable_module(module)
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)
    _session_factory = get_session_factory()

    async def _create_tables() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    async def _seed() -> None:
        assert _session_factory is not None
        async with _session_factory() as session:  # type: ignore[call-arg]
            role_admin = Role(name="系统管理员", code="admin", is_system=True)
            role_viewer = Role(name="只读用户", code="viewer", is_system=True)
            session.add_all([role_admin, role_viewer])
            await session.flush()
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                status=1,
            )
            viewer = User(
                username="viewer",
                password_hash=hash_password("viewer123"),
                display_name="Viewer",
                status=1,
            )
            session.add_all([admin, viewer])
            await session.flush()
            await session.execute(
                user_role.insert().values(
                    [{"user_id": admin.id, "role_id": role_admin.id}, {"user_id": viewer.id, "role_id": role_viewer.id}]
                )
            )
            await session.commit()

    asyncio.run(_seed())
    app = init_app(settings)
    return TestClient(app)


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _tenant_admin_app() -> TestClient:
    """模块级应用装配 + 全局 DB 工厂硬隔离（避免命中跨网 PG）.

    根因（2026-10-28 全量复跑 10 项失败排查）：
    1. 本文件此前在 **import 期** 装配 app，而 pytest 先收集全部模块再执行用例，
       后续模块会重建全局 engine，导致本文件请求实际命中非 SQLite 库；
    2. 仅"装配时 `init_db(sqlite)`"仍不充分——`AuthMiddleware` 与 `get_db` 在
       **请求期**才通过 `openbase.core.db.session.get_session_factory()` 取全局工厂，
       若全局被改到 `POSTGRES_URL`（跨网主库，偶发 `connection was closed in the
       middle of operation`），用例即随机失败。

    因此本 fixture 除延迟装配外，还把 `get_session_factory` 在本模块期间固定为
    专用 SQLite 工厂（模块结束后 undo + 复位全局单例），保证零外部数据库依赖。
    """
    global client

    from conftest import reset_db_singletons

    import openbase.core.db.session as session_module

    client = _build_app()
    assert _session_factory is not None
    patch = pytest.MonkeyPatch()
    patch.setattr(session_module, "get_session_factory", lambda: _session_factory)
    try:
        yield client
    finally:
        patch.undo()
        client = None
        reset_db_singletons()


def _token(username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


# ---- RED 用例 ----


def test_tenant_create_requires_auth() -> None:
    """未登录创建租户 → 401."""
    resp = client.post(
        "/api/v1/tenants",
        json={"code": _unique("t"), "name": "测试租户", "quota": {"users": 100}},
    )
    assert resp.status_code == 401


def test_tenant_crud_flow() -> None:
    """admin 创建租户 → 列表 → 详情 → 更新 → 停用，数据落库."""
    admin_token = _token("admin", "admin123")
    headers = _auth(admin_token)
    code = _unique("t1")

    create_resp = client.post(
        "/api/v1/tenants",
        json={"code": code, "name": "租户一", "quota": {"users": 50, "storage": 1024}},
        headers=headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    tenant = create_resp.json()
    tenant_id = tenant["id"]
    assert tenant["code"] == code
    assert tenant["status"] == 1

    list_resp = client.get("/api/v1/tenants", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == tenant_id for item in list_resp.json())

    detail_resp = client.get(f"/api/v1/tenants/{tenant_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "租户一"

    update_resp = client.put(
        f"/api/v1/tenants/{tenant_id}", json={"name": "租户一改"}, headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "租户一改"

    deactivate_resp = client.delete(f"/api/v1/tenants/{tenant_id}", headers=headers)
    assert deactivate_resp.status_code == 200
    detail_after = client.get(f"/api/v1/tenants/{tenant_id}", headers=headers).json()
    assert detail_after["status"] == 0


def test_tenant_quota_readwrite() -> None:
    """配额读写落库（Tenant.quota JSON）."""
    admin_token = _token("admin", "admin123")
    headers = _auth(admin_token)
    code = _unique("tq")
    created = client.post(
        "/api/v1/tenants", json={"code": code, "name": "配额租户"}, headers=headers
    ).json()

    set_resp = client.put(
        f"/api/v1/tenants/{created['id']}/quota",
        json={"quota": {"users": 200, "storage": 4096}},
        headers=headers,
    )
    assert set_resp.status_code == 200, set_resp.text

    detail = client.get(f"/api/v1/tenants/{created['id']}", headers=headers).json()
    assert detail["quota"] == {"users": 200, "storage": 4096}


def test_tenant_permission_required() -> None:
    """viewer 创建/列表租户 → 403."""
    viewer_token = _token("viewer", "viewer123")
    headers = _auth(viewer_token)

    create_resp = client.post(
        "/api/v1/tenants", json={"code": _unique("tv"), "name": "越权"}, headers=headers
    )
    assert create_resp.status_code == 403

    list_resp = client.get("/api/v1/tenants", headers=headers)
    assert list_resp.status_code == 403


def test_tenant_context_quota_compat() -> None:
    """既有 /context 与 /{tenant}/quota 端点不回归（已登录可访问）."""
    admin_token = _token("admin", "admin123")
    headers = _auth(admin_token)

    context_resp = client.get("/api/v1/tenants/context", headers=headers)
    assert context_resp.status_code == 200
    assert "tenant" in context_resp.json()

    quota_resp = client.get("/api/v1/tenants/demo/quota", params={"resource": "users"}, headers=headers)
    assert quota_resp.status_code == 200
    assert "usage" in quota_resp.json()
