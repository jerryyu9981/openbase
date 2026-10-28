"""v1.4.2 R-375 用户管理 API 测试（TDD RED→GREEN）.

覆盖：用户 CRUD（创建/列表/详情/启停/角色分配）+ 新用户可登录 + JWT Payload 含 org_id/role
（OpenMemory 双层认证前置）+ 权限（401/403）。数据落库（SQLite 文件库）。
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy.ext.asyncio import async_sessionmaker

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.models import Base, Role, User, user_role
from openbase.modules.auth import hash_password
from openbase.modules.users import ALLOWED_ROLES
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_users_v142.db"

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
            # 角色种子与生产保持一致（SEEDED_ROLE_CODES 五码），覆盖 org_member 回归场景
            from openbase.core.db.init import SEEDED_ROLE_CODES

            roles: dict[str, Role] = {}
            for code, name, description in SEEDED_ROLE_CODES:
                role = Role(name=name, code=code, description=description, is_system=True)
                session.add(role)
                roles[code] = role
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
                    [
                        {"user_id": admin.id, "role_id": roles["admin"].id},
                        {"user_id": viewer.id, "role_id": roles["viewer"].id},
                    ]
                )
            )
            await session.commit()

    asyncio.run(_seed())
    app = init_app(settings)
    return TestClient(app)


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _users_admin_app() -> TestClient:
    """模块级应用装配 + 全局 DB 工厂硬隔离（避免命中跨网 PG）.

    根因同 ``tests/test_tenant_admin.py``：`AuthMiddleware`/`get_db` 在请求期才取
    全局 `get_session_factory()`，若全局已被其他模块重建为跨网 PG，则用例随机报
    ``connection was closed in the middle of operation``。此处延迟装配并把全局工厂
    固定为专用 SQLite，模块结束后恢复并复位单例。
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


def _decode(token: str) -> dict:
    settings = Settings()
    return jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _user_tenant_columns(user_id: int) -> tuple | None:
    """按主键读 users 行 (tenant_id, tenant_code).

    走全局 engine 会话（与应用同一库），避免本仓「模块级 SQLite 文件库 + 全局 engine
    单例」在多文件同进程运行时读到其它模块库文件的串扰。
    """
    from sqlalchemy import text

    from openbase.core.db.session import get_session_factory

    async def _run() -> tuple | None:
        async with get_session_factory()() as session:  # type: ignore[call-arg]
            res = await session.execute(
                text("SELECT tenant_id, tenant_code FROM users WHERE id = :uid"),
                {"uid": user_id},
            )
            return res.first()

    return asyncio.run(_run())


def _ensure_tenant(code: str) -> int:
    """确保存在租户行并返回其 id（F-9 用例前置）."""
    from sqlalchemy import select as sa_select

    from openbase.core.db.session import get_session_factory
    from openbase.core.models import Tenant

    async def _run() -> int:
        async with get_session_factory()() as session:  # type: ignore[call-arg]
            found = (
                await session.execute(sa_select(Tenant).where(Tenant.code == code))
            ).scalar_one_or_none()
            if found is not None:
                return found.id
            tenant = Tenant(name=f"租户 {code}", code=code)
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            return tenant.id

    return asyncio.run(_run())


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


def test_create_user_derives_tenant_code() -> None:
    """F-9 回归：POST /users 带 tenant_id 时派生 tenant_code（与 identity/agents 口径一致）.

    RED 根因：`create_user` 只落 `tenant_id`、不派生 `tenant_code`（而 `create_agent_subject`
    经 `_resolve_tenant_code` 派生），致该路径建的同域账号作**委托目标**时
    「目标行域为空」→ 合法同域委托被误判 403 `PERM_DELEGATION_CROSS_TENANT`。
    """
    admin_token = _token("admin", "admin123")
    tenant_id = _ensure_tenant("tenant-users-1")
    username = _unique("tuser")
    resp = client.post(
        "/api/v1/users",
        json={
            "username": username,
            "password": "pass123",
            "display_name": "租户用户",
            "role": "viewer",
            "tenant_id": tenant_id,
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200, resp.text
    user_id = resp.json()["id"]

    row = _user_tenant_columns(user_id)
    assert row is not None
    got_tenant_id, got_tenant_code = row
    assert got_tenant_id == tenant_id
    assert got_tenant_code == "tenant-users-1"


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


def test_all_allowed_roles_assignable() -> None:
    """五码可分配角色均能在创建时落库（回归 F2：org_member 未播种 / user 不在枚举）."""
    admin_token = _token("admin", "admin123")
    headers = _auth(admin_token)
    for role_code in ALLOWED_ROLES:
        resp = client.post(
            "/api/v1/users",
            json={
                "username": _unique(f"role-{role_code.replace('_', '')}"),
                "password": "pass123",
                "display_name": f"角色{role_code}",
                "role": role_code,
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"{role_code}: {resp.text}"
        assert role_code in resp.json()["roles"]


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
