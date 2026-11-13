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


# ---- users 模块补测（补测方案 v1.0.0，UT-USERS-01 ~ 20）----


def _admin_headers() -> dict[str, str]:
    return _auth(_token("admin", "admin123"))


def _create_user(headers: dict[str, str], **overrides) -> dict:
    """创建用户并返回响应体（默认 viewer 角色）。"""
    payload = {
        "username": _unique("ut"),
        "password": "pass123",
        "display_name": "补测用户",
        "role": "viewer",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/users", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _scoped_token(tenant_code: str | None, permissions: list[str]) -> str:
    """构造非超管调用方 JWT（非数字 sub → 无本地主体行，按 OIDC 直签放行）。"""
    from openbase.modules.auth.jwt import create_access_token

    return create_access_token(
        "idp-users-caller",
        username="users-caller",
        tenant_code=tenant_code,
        extra={"permissions": permissions, "role": "viewer"},
    )


def _run_sql(statement: str, params: dict | None = None) -> list[tuple]:
    """在应用同一库上执行单条写/读 SQL（补测造数与断言用）。"""
    from sqlalchemy import text

    from openbase.core.db.session import get_session_factory

    async def _run() -> list[tuple]:
        async with get_session_factory()() as session:  # type: ignore[call-arg]
            result = await session.execute(text(statement), params or {})
            rows = [tuple(row) for row in result.fetchall()] if result.returns_rows else []
            await session.commit()
            return rows

    return asyncio.run(_run())


def _user_status_state(user_id: int) -> tuple[int, str | None]:
    rows = _run_sql("SELECT status, status_state FROM users WHERE id = :uid", {"uid": user_id})
    assert rows, f"用户 {user_id} 不存在"
    return rows[0][0], rows[0][1]


def test_ut_users_01_create_invalid_role_rejected() -> None:
    """UT-USERS-01：角色码不在受控枚举 → 400 PARAM_INVALID（G1）。"""
    resp = client.post(
        "/api/v1/users",
        json={
            "username": _unique("badrole"),
            "password": "pass123",
            "display_name": "非法角色",
            "role": "superuser",
        },
        headers=_admin_headers(),
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["code"] == "PARAM_INVALID"
    assert "invalid role" in body["message"]


def test_ut_users_02_create_role_not_seeded() -> None:
    """UT-USERS-02：角色码合法但库中无对应行 → 404 BIZ_404（G2）。"""
    _run_sql("UPDATE roles SET code = :new WHERE code = :old", {"new": "org_member_hidden", "old": "org_member"})
    try:
        resp = client.post(
            "/api/v1/users",
            json={
                "username": _unique("norole"),
                "password": "pass123",
                "display_name": "未播种角色",
                "role": "org_member",
            },
            headers=_admin_headers(),
        )
        assert resp.status_code == 404, resp.text
        body = resp.json()
        assert body["code"] == "BIZ_404"
        assert "role not found" in body["message"]
    finally:
        _run_sql(
            "UPDATE roles SET code = :old WHERE code = :new",
            {"old": "org_member", "new": "org_member_hidden"},
        )


def test_ut_users_03_create_duplicate_username_conflict() -> None:
    """UT-USERS-03：用户名重复 → 409 BIZ_CONFLICT（G3）。"""
    headers = _admin_headers()
    username = _unique("dup")
    _create_user(headers, username=username)
    resp = client.post(
        "/api/v1/users",
        json={
            "username": username,
            "password": "pass123",
            "display_name": "重复用户",
            "role": "viewer",
        },
        headers=headers,
    )
    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["code"] == "BIZ_CONFLICT"
    assert "username already exists" in body["message"]


def test_ut_users_04_list_without_tenant_returns_empty() -> None:
    """UT-USERS-04：非超管且无租户绑定 → 空列表（G4）。"""
    token = _scoped_token(None, ["users:view"])
    resp = client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_ut_users_05_list_scoped_by_tenant_code() -> None:
    """UT-USERS-05：非超管按 tenant_code 过滤，仅见本租户用户（G5）。"""
    headers = _admin_headers()
    code_a, code_b = _unique("tenant-a"), _unique("tenant-b")
    tenant_a, tenant_b = _ensure_tenant(code_a), _ensure_tenant(code_b)
    _create_user(headers, display_name="Tenant A User", tenant_id=tenant_a)
    _create_user(headers, display_name="Tenant B User", tenant_id=tenant_b)

    token = _scoped_token(code_a, ["users:view"])
    resp = client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert {row["display_name"] for row in resp.json()} == {"Tenant A User"}


def test_ut_users_06_get_missing_user_not_found() -> None:
    """UT-USERS-06：详情不存在 → 404 BIZ_404（G6）。"""
    resp = client.get("/api/v1/users/999999", headers=_admin_headers())
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "BIZ_404"


def test_ut_users_07_update_missing_user_not_found() -> None:
    """UT-USERS-07：更新不存在用户 → 404 BIZ_404（G7）。"""
    resp = client.put(
        "/api/v1/users/999999",
        json={"display_name": "不存在"},
        headers=_admin_headers(),
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "BIZ_404"


def test_ut_users_08_status_transition_active_suspended_roundtrip() -> None:
    """UT-USERS-08：启停合法迁移 active ⇄ suspended，status_state 同步（G8）。"""
    headers = _admin_headers()
    user_id = _create_user(headers)["id"]

    disable = client.put(f"/api/v1/users/{user_id}", json={"status": 0}, headers=headers)
    assert disable.status_code == 200, disable.text
    assert _user_status_state(user_id) == (0, "suspended")

    enable = client.put(f"/api/v1/users/{user_id}", json={"status": 1}, headers=headers)
    assert enable.status_code == 200, enable.text
    assert enable.json()["status"] == 1
    assert _user_status_state(user_id) == (1, "active")

    # 同态写入（active → active）不触发迁移校验，幂等成功
    noop = client.put(f"/api/v1/users/{user_id}", json={"status": 1}, headers=headers)
    assert noop.status_code == 200, noop.text
    assert _user_status_state(user_id) == (1, "active")


def test_ut_users_09_status_transition_deactivated_rejected() -> None:
    """UT-USERS-09：deactivated 终态不可经旧写路径复活 → 400（G8）。"""
    headers = _admin_headers()
    user_id = _create_user(headers)["id"]
    _run_sql("UPDATE users SET status = 0, status_state = 'deactivated' WHERE id = :uid", {"uid": user_id})

    resp = client.put(f"/api/v1/users/{user_id}", json={"status": 1}, headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "BIZ_STATE_TRANSITION_INVALID"
    assert _user_status_state(user_id) == (0, "deactivated")


def test_ut_users_10_update_basic_fields_partial() -> None:
    """UT-USERS-10：display_name/email/phone 部分更新，未传字段保持原值（G9）。"""
    headers = _admin_headers()
    user_id = _create_user(headers)["id"]

    first = client.put(f"/api/v1/users/{user_id}", json={"email": "ut@example.com"}, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["email"] == "ut@example.com"
    assert first.json()["display_name"] == "补测用户"

    second = client.put(
        f"/api/v1/users/{user_id}",
        json={"display_name": "改名后", "phone": "13800000000"},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["display_name"] == "改名后"
    assert body["phone"] == "13800000000"
    assert body["email"] == "ut@example.com"


def test_ut_users_11_status_change_invalidates_principal_cache(monkeypatch) -> None:
    """UT-USERS-11：启停写路径即时失效 principal 缓存（G10）。"""
    headers = _admin_headers()
    user = _create_user(headers)
    calls: list[tuple] = []

    def _spy(subject_id: int, username: str | None = None) -> None:
        calls.append((subject_id, username))

    monkeypatch.setattr(
        "openbase.modules.identity.verification.invalidate_principal_cache", _spy
    )
    resp = client.put(f"/api/v1/users/{user['id']}", json={"status": 0}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert calls == [(user["id"], user["username"])]


def test_ut_users_12_delete_user_soft_delete_flow() -> None:
    """UT-USERS-12：DELETE 软删（status=0 + suspended），数据保留（G11）。"""
    headers = _admin_headers()
    user = _create_user(headers)

    resp = client.delete(f"/api/v1/users/{user['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"code": 0, "user_id": user["id"], "status": 0}
    assert _user_status_state(user["id"]) == (0, "suspended")

    detail = client.get(f"/api/v1/users/{user['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == 0


def test_ut_users_13_delete_missing_user_not_found() -> None:
    """UT-USERS-13：删除不存在用户 → 404 BIZ_404（G11）。"""
    resp = client.delete("/api/v1/users/999999", headers=_admin_headers())
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "BIZ_404"


def test_ut_users_14_delete_suspended_user_keeps_state() -> None:
    """UT-USERS-14：已 suspended 用户再 DELETE 保持 suspended（不复活/不改写）（G11）。"""
    headers = _admin_headers()
    user_id = _create_user(headers)["id"]
    assert client.put(f"/api/v1/users/{user_id}", json={"status": 0}, headers=headers).status_code == 200

    resp = client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert _user_status_state(user_id) == (0, "suspended")


def test_ut_users_15_assign_role_missing_user_not_found() -> None:
    """UT-USERS-15：角色分配目标不存在 → 404 BIZ_404（G12）。"""
    resp = client.put(
        "/api/v1/users/999999/role", json={"role": "admin"}, headers=_admin_headers()
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "BIZ_404"


def test_ut_users_16_assign_role_replaces_previous() -> None:
    """UT-USERS-16：角色分配替换旧角色关联（G12）。"""
    headers = _admin_headers()
    user_id = _create_user(headers, role="viewer")["id"]

    resp = client.put(f"/api/v1/users/{user_id}/role", json={"role": "org_admin"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["roles"] == ["org_admin"]

    detail = client.get(f"/api/v1/users/{user_id}", headers=headers).json()
    assert detail["roles"] == ["org_admin"]


def test_ut_users_17_create_payload_validation_rejected() -> None:
    """UT-USERS-17：参数契约校验——非法用户名/短密码/非法 status → 400 PARAM_400。"""
    headers = _admin_headers()
    invalid_payloads = [
        {"username": "a", "password": "pass123", "display_name": "短用户名"},
        {"username": "bad name", "password": "pass123", "display_name": "非法字符"},
        {"username": _unique("shortpwd"), "password": "123", "display_name": "短密码"},
    ]
    for payload in invalid_payloads:
        resp = client.post("/api/v1/users", json={**payload, "role": "viewer"}, headers=headers)
        assert resp.status_code == 400, f"{payload}: {resp.text}"
        assert resp.json()["code"] == "PARAM_400"

    user_id = _create_user(headers)["id"]
    bad_status = client.put(f"/api/v1/users/{user_id}", json={"status": 2}, headers=headers)
    assert bad_status.status_code == 400, bad_status.text
    assert bad_status.json()["code"] == "PARAM_400"


def test_ut_users_18_all_endpoints_require_auth() -> None:
    """UT-USERS-18：五个端点未认证一律 401。"""
    requests = [
        ("post", "/api/v1/users", {"json": {"username": _unique("na"), "password": "pass123", "display_name": "x"}}),
        ("get", "/api/v1/users", {}),
        ("get", "/api/v1/users/1", {}),
        ("put", "/api/v1/users/1", {"json": {"display_name": "x"}}),
        ("delete", "/api/v1/users/1", {}),
        ("put", "/api/v1/users/1/role", {"json": {"role": "viewer"}}),
    ]
    for method, path, kwargs in requests:
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 401, f"{method.upper()} {path}: {resp.status_code}"


def test_ut_users_19_write_endpoints_forbidden_for_viewer() -> None:
    """UT-USERS-19：viewer 对更新/删除/角色分配一律 403。"""
    headers = _auth(_token("viewer", "viewer123"))
    for method, path, payload in (
        ("put", "/api/v1/users/1", {"display_name": "越权"}),
        ("delete", "/api/v1/users/1", None),
        ("put", "/api/v1/users/1/role", {"role": "admin"}),
    ):
        kwargs = {"headers": headers}
        if payload is not None:
            kwargs["json"] = payload
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 403, f"{method.upper()} {path}: {resp.status_code}"


def test_ut_users_20_response_never_exposes_password_hash() -> None:
    """UT-USERS-20：创建/列表/详情响应均不回显密码哈希，roles 与入参一致。"""
    headers = _admin_headers()
    created = _create_user(headers, role="org_member")
    assert "password_hash" not in created
    assert created["roles"] == ["org_member"]

    listing = client.get("/api/v1/users", headers=headers).json()
    assert all("password_hash" not in row for row in listing)
    detail = client.get(f"/api/v1/users/{created['id']}", headers=headers).json()
    assert "password_hash" not in detail

