"""v1.4.2 R-375 用户管理 API 测试（TDD RED→GREEN）.

覆盖：用户 CRUD（创建/列表/详情/启停/角色分配）+ 新用户可登录 + JWT Payload 含 org_id/role
（OpenMemory 双层认证前置）+ 权限（401/403）。数据落库（SQLite 文件库）。
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from openbase import init_app
from openbase.core.db.session import init_db
from openbase.core.models import Base, Role, User, user_role
from openbase.modules.auth import hash_password
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_users_v142.db"


def _build_app() -> TestClient:
    settings = Settings()
    for module in ("auth", "tenant", "users", "audit", "config", "org", "dict", "storage", "notify"):
        settings.enable_module(module)
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)

    async def _create_tables() -> None:
        from openbase.core.db.session import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    async def _seed() -> None:
        from openbase.core.db.session import get_session_factory

        async with get_session_factory()() as session:  # type: ignore[call-arg]
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


client = _build_app()


def _token(username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _decode(token: str) -> dict:
    settings = Settings()
    return jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# ---- RED 用例 ----


def test_user_create_requires_auth() -> None:
    """未登录创建用户 → 401."""
    resp = client.post(
        "/api/v1/users",
        json={"username": _unique("u"), "password": "pass123", "display_name": "新用户", "role": "viewer"},
    )
    assert resp.status_code == 401


def test_user_crud_flow() -> None:
    """admin 创建用户 → 列表 → 详情 → 启停 → 角色分配，数据落库."""
    admin_token = _token("admin", "admin123")
    headers = _auth(admin_token)
    username = _unique("u1")

    create_resp = client.post(
        "/api/v1/users",
        json={"username": username, "password": "pass123", "display_name": "用户一", "role": "viewer"},
        headers=headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    user = create_resp.json()
    user_id = user["id"]
    assert user["username"] == username
    assert user["status"] == 1
    assert "password_hash" not in user  # 不回显密码

    list_resp = client.get("/api/v1/users", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == user_id for item in list_resp.json())

    detail_resp = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["display_name"] == "用户一"

    disable_resp = client.put(f"/api/v1/users/{user_id}", json={"status": 0}, headers=headers)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["status"] == 0

    role_resp = client.put(f"/api/v1/users/{user_id}/role", json={"role": "admin"}, headers=headers)
    assert role_resp.status_code == 200
    detail_after = client.get(f"/api/v1/users/{user_id}", headers=headers).json()
    assert "admin" in detail_after["roles"]


def test_new_user_can_login() -> None:
    """新建用户（viewer 角色）可登录."""
    admin_token = _token("admin", "admin123")
    headers = _auth(admin_token)
    username = _unique("u2")
    client.post(
        "/api/v1/users",
        json={"username": username, "password": "secret123", "display_name": "可登录用户", "role": "viewer"},
        headers=headers,
    )

    login_resp = client.post("/api/v1/auth/login", json={"username": username, "password": "secret123"})
    assert login_resp.status_code == 200, login_resp.text
    assert login_resp.json()["access_token"]


def test_jwt_payload_contains_org_id_and_role() -> None:
    """登录 JWT Payload 含 org_id + role（OpenMemory 双层认证前置）."""
    admin_token = _token("admin", "admin123")
    payload = _decode(admin_token)
    assert payload["sub"]
    assert payload["role"] == "admin"
    # org_id：无租户用户时为 None 或缺失均可，但键必须存在且语义正确
    assert "org_id" in payload


def test_user_permission_required() -> None:
    """viewer 创建/列表用户 → 403."""
    viewer_token = _token("viewer", "viewer123")
    headers = _auth(viewer_token)

    create_resp = client.post(
        "/api/v1/users",
        json={"username": _unique("uv"), "password": "pass123", "display_name": "越权", "role": "viewer"},
        headers=headers,
    )
    assert create_resp.status_code == 403

    list_resp = client.get("/api/v1/users", headers=headers)
    assert list_resp.status_code == 403
