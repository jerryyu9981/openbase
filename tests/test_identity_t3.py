"""U1 T3（K04 / OB-2 吊销，方案 a token 版本号）token 吊销即时性强校验 TDD 用例.

RED→GREEN 断言对齐《OpenBase-U1-统一身份收口设计草案》v1.0.0 §11 T3-1~T3-7：
- T3-1  suspend 后存量 access → 立即 401 AUTH_PRINCIPAL_DISABLED
- T3-2  suspend 后 refresh → 拒绝（签发侧状态校验）
- T3-3  deactivate 后 access/refresh/sk-agent-*/OIDC 重登全部 401/403
- T3-4  restore 后旧 token 401 AUTH_TOKEN_STALE；重新 login 成功
- T3-5  tvn 落后任意整数即拒（模拟 token_version=2 但 claim tvn=1）；
       补充：enforce 开启下 v0（无 tvn）令牌过渡窗口仍放行（草案 §5.2/§6.2）
- T3-6  静态扫描 0 条「仅验签不验状态」路径（AuthMiddleware/get_current_user
       打桩断言 verify_principal 必被调 + 源码级断言）
- T3-7  缓存一致性：状态/版本变更后 principal:{id} 缓存键失效（下一请求命中新状态）

两段式发布（草案 §12.1 风险 1/§6.2）：
- settings.enforce_token_version 默认 False：版本强校验关，存量 v0/落后 tvn 过渡窗口
  不误杀（T3-4b/T3-5 补充用例覆盖默认放行语义）；
- 每请求主体状态校验不依赖该开关（默认即生效，T3-1/T3-3 断言）。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Base, Permission, Role, Tenant, User, user_role
from openbase.modules.auth import hash_password
from openbase.modules.auth.jwt import create_access_token
from openbase.settings import Settings, get_settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t3.db"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH)


def _rows(sql: str) -> list[tuple]:
    conn = _conn()
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _build_app() -> TestClient:
    """装配启用 identity 模块的应用 + SQLite 库种子（admin/viewer/org_admin + identity:* 权限）."""
    settings = Settings()
    for module_name in ("auth", "tenant", "users", "audit", "config", "identity"):
        settings.enable_module(module_name)
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)

    async def _setup() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_session_factory()() as session:  # type: ignore[call-arg]
            role_admin = Role(name="系统管理员", code="admin", is_system=True)
            role_viewer = Role(name="只读用户", code="viewer", is_system=True)
            role_org_admin = Role(name="组织管理员", code="org_admin", is_system=True)
            session.add_all([role_admin, role_viewer, role_org_admin])
            await session.flush()
            tenant = Tenant(name="Acme", code="acme", status=1, isolation_level=1)
            session.add(tenant)
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                status=1,
            )
            session.add(admin)
            await session.flush()
            perms = [
                Permission(code="*", name="全部权限", module="system", type=3),
                Permission(code="users:manage", name="用户管理", module="users", type=3),
                Permission(code="users:view", name="用户查看", module="users", type=3),
                Permission(code="identity:view", name="主体查看", module="identity", type=3),
                Permission(code="identity:manage", name="主体管理", module="identity", type=3),
                Permission(code="identity:lifecycle", name="生命周期管理", module="identity", type=3),
            ]
            session.add_all(perms)
            await session.flush()
            perm_by_code = {p.code: p for p in perms}
            from openbase.core.models import role_permission

            await session.execute(
                user_role.insert().values(
                    [{"user_id": admin.id, "role_id": role_admin.id}]
                )
            )
            await session.execute(
                role_permission.insert().values(
                    [
                        {"role_id": role_admin.id, "permission_id": perm_by_code["*"].id},
                        {
                            "role_id": role_org_admin.id,
                            "permission_id": perm_by_code["users:manage"].id,
                        },
                        {
                            "role_id": role_org_admin.id,
                            "permission_id": perm_by_code["users:view"].id,
                        },
                    ]
                )
            )
            await session.commit()

    asyncio.run(_setup())
    app = init_app(settings)
    return TestClient(app)


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _identity_t3_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局 engine 单例）."""
    global client
    client = _build_app()
    yield client
    client = None


# ---- 数据库辅助（沿用 T2 直插形态） ----


TENANT_SQL = """
INSERT INTO tenants (name, code, status, isolation_level, created_at, updated_at)
VALUES (:name, :code, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""

USER_SQL = """
INSERT INTO users (username, password_hash, display_name, status, tenant_id,
                   subject_type, credential_type, status_state, status_reason,
                   token_version, tenant_code, is_deleted, created_at, updated_at)
VALUES (:username, :password_hash, :display_name, :status, :tenant_id,
        :subject_type, :credential_type, :status_state, :status_reason,
        :token_version, :tenant_code, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""


def _tenant_id(code: str) -> int | None:
    rows = _rows(f"SELECT id FROM tenants WHERE code = '{code}'")
    return rows[0][0] if rows else None


def _ensure_tenant(code: str) -> int:
    existing = _tenant_id(code)
    if existing is not None:
        return existing
    conn = _conn()
    try:
        conn.execute(TENANT_SQL, {"name": code.title(), "code": code})
        conn.commit()
    finally:
        conn.close()
    return _tenant_id(code)  # type: ignore[return-value]


def _make_user(
    username: str,
    password: str = "secret123",
    tenant_code: str | None = "acme",
    state: str = "active",
    token_version: int = 0,
    role: str = "viewer",
) -> int:
    """直插用户行（附租户 + viewer 角色绑定），返回 user id."""
    _ensure_tenant(tenant_code) if tenant_code else None
    tenant_id = _tenant_id(tenant_code) if tenant_code else None
    conn = _conn()
    try:
        cur = conn.execute(
            USER_SQL,
            {
                "username": username,
                "password_hash": hash_password(password),
                "display_name": username,
                "status": 1 if state == "active" else 0,
                "tenant_id": tenant_id,
                "subject_type": "user",
                "credential_type": "password",
                "status_state": state,
                "status_reason": None,
                "token_version": token_version,
                "tenant_code": tenant_code,
            },
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()
    role_row = _rows(f"SELECT id FROM roles WHERE code = '{role}'")
    if role_row:
        conn = _conn()
        try:
            conn.execute(
                "INSERT INTO user_role (user_id, role_id) VALUES (?, ?)",
                (user_id, role_row[0][0]),
            )
            conn.commit()
        finally:
            conn.close()
    return user_id  # type: ignore[return-value]


def _username_of(user_id: int) -> str:
    return _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]  # type: ignore[return-value]


def _login(username: str, password: str = "secret123"):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _admin_headers() -> dict[str, str]:
    resp = _login("admin", "admin123")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _decode(token: str) -> dict:
    settings = get_settings()
    return jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _state_row(user_id: int) -> tuple:
    row = _rows(
        f"SELECT status_state, token_version, status FROM users WHERE id = {user_id}"
    )
    assert len(row) == 1, f"user {user_id} not found"
    return row[0]


def _lifecycle_url(subject_type: str, subject_id: int, action: str) -> str:
    return f"/api/v1/identity/lifecycle/{subject_type}/{subject_id}/{action}"


def _lifecycle_action(subject_type: str, subject_id: int, action: str, **extra):
    body = {"reason": f"{action} via t3"}
    if action == "deactivate":
        body = {"confirm": True, "reason": "deactivate via t3"}
    body.update(extra)
    return client.post(
        _lifecycle_url(subject_type, subject_id, action),
        json=body,
        headers=_admin_headers(),
    )


def _suspend(subject_type: str, subject_id: int) -> object:
    return _lifecycle_action(subject_type, subject_id, "suspend")


def _restore(subject_type: str, subject_id: int) -> object:
    return _lifecycle_action(subject_type, subject_id, "restore")


def _deactivate(subject_type: str, subject_id: int) -> object:
    return _lifecycle_action(subject_type, subject_id, "deactivate")


def _enable_version_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    """开启版本强校验开关（enforce_token_version=True；monkeypatch 自动复原）."""
    monkeypatch.setattr(get_settings(), "enforce_token_version", True)


def _me(token: str) -> object:
    return client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


# ---- T3-1 suspend 后存量 access 立即 401 AUTH_PRINCIPAL_DISABLED ----


def test_t3_1_suspend_immediately_invalidates_existing_access() -> None:
    """suspend 后存量 access → GET /auth/me 立即 401 AUTH_PRINCIPAL_DISABLED."""
    user_id = _make_user(_unique("s1"), tenant_code="acme")
    username = _username_of(user_id)

    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    access_token = login_resp.json()["access_token"]
    # 基线：suspend 前存量 access 可用
    assert _me(access_token).status_code == 200

    suspend_resp = _suspend("user", user_id)
    assert suspend_resp.status_code == 200, suspend_resp.text
    assert _state_row(user_id)[0] == "suspended"
    assert _state_row(user_id)[1] == 1  # token_version 0 → 1

    # 存量 access 立即 401 AUTH_PRINCIPAL_DISABLED（秒级窗口，无需等 refresh）
    blocked = _me(access_token)
    assert blocked.status_code == 401, blocked.text
    assert blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


# ---- T3-2 suspend 后 refresh 拒绝 ----


def test_t3_2_suspend_blocks_refresh_issuance() -> None:
    """suspend 后 refresh → 401 AUTH_PRINCIPAL_DISABLED（签发侧状态校验）. """
    user_id = _make_user(_unique("s2"), tenant_code="acme")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    refresh_token = login_resp.json()["refresh_token"]

    assert _suspend("user", user_id).status_code == 200

    blocked = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert blocked.status_code == 401, blocked.text
    assert blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


# ---- T3-3 deactivate 后 access/refresh/sk-agent-*/OIDC 重登全拒 ----


def test_t3_3_deactivate_blocks_all_entries_for_user() -> None:
    """deactivate 后存量 access/refresh/login 全拒（401 AUTH_PRINCIPAL_DISABLED）. """
    user_id = _make_user(_unique("d3u"), tenant_code="acme")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    deact = _deactivate("user", user_id)
    assert deact.status_code == 200, deact.text
    assert _state_row(user_id)[0] == "deactivated"
    assert _state_row(user_id)[1] == 1

    # access / refresh / 重登全拒
    assert _me(access_token).status_code == 401
    assert _me(access_token).json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value
    refresh_blocked = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_blocked.status_code == 401, refresh_blocked.text
    login_blocked = _login(username)
    assert login_blocked.status_code == 401, login_blocked.text
    assert login_blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


def test_t3_3_deactivate_agent_revokes_sk_agent_keys() -> None:
    """deactivate agent → sk-agent-* 请求 401（key 吊销 + 主体状态双门禁）. """
    admin_headers = _admin_headers()
    create_resp = client.post(
        "/api/v1/identity/agents",
        json={"username": _unique("agent"), "display_name": "Agent T3", "role": "viewer"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    agent_id = create_resp.json()["agent_id"]
    raw_key = create_resp.json()["api_key"]["raw_key"]
    assert _me(raw_key).status_code == 200

    deact = _deactivate("agent", agent_id)
    assert deact.status_code == 200, deact.text
    key_rows = _rows(f"SELECT status FROM agent_api_keys WHERE agent_id = {agent_id}")
    assert key_rows and all(row[0] == "revoked" for row in key_rows)

    assert _me(raw_key).status_code == 401


def test_t3_3_oidc_relogin_rejected_after_deactivate(monkeypatch: pytest.MonkeyPatch) -> None:
    """deactivated 绑定主体经 IdP 回调重登被拒（callback 401 AUTH_PRINCIPAL_DISABLED）. """
    from types import SimpleNamespace

    import openbase.modules.auth.oidc as oidc_module

    user_id = _make_user(_unique("oidc3"), tenant_code="acme", state="active")
    sub = "t3-oidc-deactivated-sub"
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO oidc_identity (user_id, sub, issuer, created_at, updated_at) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user_id, sub, "http://oidc-t3"),
        )
        conn.commit()
    finally:
        conn.close()
    assert _deactivate("user", user_id).status_code == 200

    claims = {
        "iss": "http://oidc-t3",
        "sub": sub,
        "preferred_username": _username_of(user_id),
        "email": "t3-oidc@openbase.local",
        "roles": ["viewer"],
    }
    mapped = {
        "sub": sub,
        "username": claims["preferred_username"],
        "tenant_id": "acme",
        "extra": {"org_id": "acme", "role": "viewer"},
    }
    oidc_module._state_store["t3-oidc-state"] = "pending"

    class _FakeOidcClient:
        enabled = True

        async def exchange_code(self, code: str) -> dict:
            return {"id_token": "fake-id-token", "access_token": "fake-access"}

        def parse_id_token(self, id_token: str, access_token: str | None = None) -> dict:
            return claims

        def map_claims(self, parsed: dict) -> dict:
            return mapped

    monkeypatch.setattr(oidc_module, "_get_oidc_client", lambda: _FakeOidcClient())
    monkeypatch.setattr(
        oidc_module,
        "get_settings",
        lambda: SimpleNamespace(
            oidc_profile="generic",
            oidc_frontend_redirect="",
            oidc_client_id="openbase-test",
            oidc_keycloak_client_roles=True,
            jwt_expire_seconds=7200,
            refresh_expire_seconds=604800,
        ),
    )
    resp = client.get(
        "/api/v1/auth/oidc/callback?code=mock-code&state=t3-oidc-state"
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


# ---- T3-4 restore 后旧 token 401 AUTH_TOKEN_STALE；重新 login 成功 ----


def test_t3_4_restore_old_access_stale_when_enforced_and_relogin_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """restore 后（tvn 0→2）旧 token：enforce 开启下 401 AUTH_TOKEN_STALE；重登成功."""
    _enable_version_enforcement(monkeypatch)
    user_id = _make_user(_unique("s4"), tenant_code="acme")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    old_access = login_resp.json()["access_token"]
    assert _decode(old_access)["tvn"] == 0

    assert _suspend("user", user_id).status_code == 200
    assert _restore("user", user_id).status_code == 200
    assert _state_row(user_id)[0] == "active"
    assert _state_row(user_id)[1] == 2

    # 旧 token（tvn=0 落后 2）→ AUTH_TOKEN_STALE
    stale = _me(old_access)
    assert stale.status_code == 401, stale.text
    assert stale.json()["code"] == ErrorCode.AUTH_TOKEN_STALE.value

    # 重新 login 成功且携带当前版本
    relogin = _login(username)
    assert relogin.status_code == 200, relogin.text
    new_access = relogin.json()["access_token"]
    assert _decode(new_access)["tvn"] == 2
    assert _me(new_access).status_code == 200


def test_t3_4_default_off_allows_stale_tvn_in_transition_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enforce 默认关：restore 后旧 token（落后 tvn）过渡窗口放行（不误杀存量会话）."""
    # 显式确保默认关闭（Settings 默认 False）
    monkeypatch.setattr(get_settings(), "enforce_token_version", False)
    user_id = _make_user(_unique("s4b"), tenant_code="acme")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    old_access = login_resp.json()["access_token"]
    assert _decode(old_access)["tvn"] == 0

    assert _suspend("user", user_id).status_code == 200
    assert _restore("user", user_id).status_code == 200
    assert _state_row(user_id)[1] == 2

    # 版本强校验关：状态已恢复 active → 旧 token 放行（v0/落后 tvn 过渡窗口）
    assert _me(old_access).status_code == 200, _me(old_access).text


# ---- T3-5 tvn 落后任意整数即拒 ----


def test_t3_5_tvn_behind_by_any_integer_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """enforce 开启：claim tvn=1 而服务端 token_version=2 → 401 AUTH_TOKEN_STALE."""
    _enable_version_enforcement(monkeypatch)
    user_id = _make_user(_unique("tvn5"), tenant_code="acme")
    username = _username_of(user_id)
    # 模拟服务端 token_version 已推进到 2（直接更新 DB）
    conn = _conn()
    try:
        conn.execute("UPDATE users SET token_version = 2 WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    # 签发一个 claim tvn=1 的存量 access（落后 1）
    stale_token = create_access_token(
        str(user_id),
        username=username,
        tenant_id=str(_rows(f"SELECT tenant_id FROM users WHERE id = {user_id}")[0][0]),
        tenant_code="acme",
        token_version=1,
    )
    stale_resp = _me(stale_token)
    assert stale_resp.status_code == 401, stale_resp.text
    assert stale_resp.json()["code"] == ErrorCode.AUTH_TOKEN_STALE.value


def test_t3_5_v0_token_without_tvn_still_allowed_when_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enforce 开启但 claim 无 tvn（v0 存量形态）→ 兼容放行（草案 §5.2/§6.2 过渡窗口）."""
    _enable_version_enforcement(monkeypatch)
    user_id = _make_user(_unique("v05"), tenant_code="acme")
    username = _username_of(user_id)
    # v0 形态 access：create_access_token 不带 token_version → payload 无 tvn
    v0_token = create_access_token(str(user_id), username=username, tenant_id="acme")
    assert "tvn" not in _decode(v0_token)
    assert _me(v0_token).status_code == 200, _me(v0_token).text


# ---- T3-6 静态扫描 0 条「仅验签不验状态」路径 ----


def test_t3_6_verify_principal_must_be_called_by_middleware_and_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """打桩 verify_principal：受保护 JWT 请求必经中间件/依赖层调用（0 条仅验签路径）."""
    from openbase.modules.identity import verification as principal_verification

    original = principal_verification.verify_principal
    calls = {"count": 0}

    async def _counting(session, payload, **kwargs):
        calls["count"] += 1
        return await original(session, payload, **kwargs)

    monkeypatch.setattr(principal_verification, "verify_principal", _counting)

    user_id = _make_user(_unique("scan6"), tenant_code="acme")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    access_token = login_resp.json()["access_token"]

    assert _me(access_token).status_code == 200
    assert calls["count"] >= 1, "verify_principal 必须被调（AuthMiddleware/get_current_user）"


def test_t3_6_static_scan_no_decode_only_auth_gate() -> None:
    """源码级静态扫描：AuthMiddleware.dispatch 与 get_current_user 内不得仅 decode 不 verify.

    对认证门禁（用户 JWT 面）做 AST 断言：凡是引用 decode_access_token 的认证门禁
    函数体必须同时引用 verify_principal（或 agent 密钥解析器），否则即「仅验签不验状态」路径。
    """
    import ast
    import inspect

    from openbase.core.deps import auth as deps_auth

    # 1) 门禁函数（认证必经点）显式引用 verify_principal
    dispatch_src = inspect.getsource(deps_auth.AuthMiddleware.dispatch)
    assert "verify_principal" in dispatch_src, "AuthMiddleware.dispatch 必须调用 verify_principal"
    current_user_src = inspect.getsource(deps_auth.get_current_user)
    assert "verify_principal" in current_user_src, "get_current_user 必须调用 verify_principal"

    # 2) AST 扫描 deps/auth.py：任何函数若调用 decode_access_token 且未同时引用
    #    verify_principal / resolve_agent_principal，判定为仅验签门禁 → 失败。
    #    白名单（非认证门禁的辅助解码，仅供请求头/上下文回退，且主门禁已先行）：
    #    get_current_tenant / get_identity_context —— 仅在提取 X-Tenant-Id/四维头时
    #    从 JWT 补读字段，不作为放行判定（try/except 吞错，非门禁）。
    _NON_GATE_DECODERS = frozenset({"get_current_tenant", "get_identity_context"})
    tree = ast.parse(inspect.getsource(deps_auth))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in _NON_GATE_DECODERS:
            continue
        calls = {
            c.func.attr if isinstance(c.func, ast.Attribute) else getattr(c.func, "id", "")
            for c in ast.walk(node)
            if isinstance(c, ast.Call)
        }
        if "decode_access_token" not in calls:
            continue
        # 门禁解码函数必须直接引用 verify_principal（get_current_user）或经
        # _verify_request_principal（dispatch 委托的共享验证执行体）抵达同一验证器。
        assert calls & {"verify_principal", "_verify_request_principal", "resolve_agent_principal"}, (
            f"仅验签不验状态路径: {node.name} (deps/auth.py)"
        )


# ---- T3-7 缓存一致性 ----


def _install_fake_redis_cache(monkeypatch: pytest.MonkeyPatch) -> dict:
    """以进程内 dict 替身替换 redis_client 缓存函数（确定性断言 principal 键失效）. """
    store: dict[str, str] = {}
    import openbase.core.cache.redis_client as redis_client

    def _get(key: str):
        raw = store.get(key)
        return json.loads(raw) if raw is not None else None

    def _set(key: str, value, ttl: int = 300) -> bool:
        store[key] = json.dumps(value, ensure_ascii=False)
        return True

    def _delete(*keys: str) -> bool:
        for key in keys:
            store.pop(key, None)
        return True

    monkeypatch.setattr(redis_client, "cache_get", _get)
    monkeypatch.setattr(redis_client, "cache_set", _set)
    monkeypatch.setattr(redis_client, "cache_delete", _delete)
    return store


def test_t3_7_state_change_invalidates_principal_cache_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """principal:{id} 缓存键在状态变更（suspend）后被失效 → 下一请求命中新状态 401."""
    store = _install_fake_redis_cache(monkeypatch)

    user_id = _make_user(_unique("c7"), tenant_code="acme")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    old_access = login_resp.json()["access_token"]

    # 首次受保护请求：verify_principal 读库并把 principal:{id} 快照写入缓存
    assert _me(old_access).status_code == 200
    assert f"principal:{user_id}" in store, "principal 缓存键应已写入"

    # suspend（吊销类迁移，tvn+1）：同步删除 principal:{id} / user:{username}
    assert _suspend("user", user_id).status_code == 200
    assert f"principal:{user_id}" not in store, "状态变更后 principal:{id} 必须失效"
    assert f"user:{username}" not in store, "user:{username} 缓存键须随状态变更失效"

    # 下一请求（若缓存未失效本会命中 active 旧快照）→ 命中新状态 suspended → 401
    blocked = _me(old_access)
    assert blocked.status_code == 401, blocked.text
    assert blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


# ---- 补充：共享主体验证器单元语义（降级/缓存分支，T3 兼容钉死） ----
# 存量 v0 / OIDC 直签 / 行缺失（无墓碑）在过渡窗口不被误杀（草案 §6.2/§12.1 风险 1）；
# deactivated 等「保留行 + 非 active」仍即时拦截；**DB 不可达自 B4 起为 fail-closed 拒绝**
# （2026-10-08，人工裁定选项 A，见 tests/test_b4_security_hardening.py）。


class _RaisingSession:
    """DB 读抛异常的会话替身（验证器 fail-open 降级语义）. """

    def __init__(self) -> None:
        self.rolled_back = False

    async def get(self, model, subject_id: int):
        raise RuntimeError("db unreachable")

    async def rollback(self) -> None:
        self.rolled_back = True


def test_verify_principal_missing_subject_raises_token_invalid() -> None:
    """缺 sub → 401 AUTH_TOKEN_INVALID（fail-closed）. """
    from openbase.modules.identity import verification as verifier

    with pytest.raises(BaseError) as exc_info:
        asyncio.run(verifier.verify_principal(object(), {}))
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_INVALID


def test_verify_principal_oidc_direct_string_sub_passthrough() -> None:
    """sub 非数字（OIDC 直签/外域主体）→ 无本地主体行，放行（v0 直签过渡窗口）."""
    from openbase.modules.identity import verification as verifier

    result = asyncio.run(
        verifier.verify_principal(object(), {"sub": "idp-direct-sub-2026"})
    )
    assert result is None


def test_verify_principal_db_unreachable_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB 读不可达 + 显式 policy=reject → fail-closed 拒绝（503 SYS_SOURCE_UNAVAILABLE）.

    环境门控（2026-10-09 修复）：非生产默认「兼容放行」，故本用例**显式钉死**
    ``principal_db_degraded_policy=reject``（生产默认亦为 reject），继续测到安全语义。
    """
    import importlib

    from openbase.modules.identity import verification as verifier

    # 注意：`openbase/__init__.py` 以 `settings = get_settings()` 暴露实例，令
    # `import openbase.settings as m` 绑定到该实例（属性遮蔽）；须用 importlib 取模块。
    monkeypatch.setattr(
        importlib.import_module("openbase.settings"),
        "_settings",
        Settings(principal_db_degraded_policy="reject"),
    )

    session = _RaisingSession()
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(
            verifier.verify_principal(session, {"sub": "42", "tvn": 0})
        )
    assert exc_info.value.code == ErrorCode.SYS_SOURCE_UNAVAILABLE
    assert exc_info.value.status_code == 503
    assert session.rolled_back is True


def test_verify_principal_missing_row_failopen() -> None:
    """主体行不存在（已 purge/软删/降级内存用户）→ WARN 后放行（T6 purge 收口前过渡语义）."""
    from openbase.modules.identity import verification as verifier

    async def _run() -> object:
        async with get_session_factory()() as session:
            return await verifier.verify_principal(
                session, {"sub": "9876543210", "tvn": 1}
            )

    assert asyncio.run(_run()) is None


def test_verify_principal_cache_fallback_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    """缓存分支：脏数据/异常一律视同未命中并静默降级（Redis 不可用不阻断认证）."""
    from openbase.core.cache import redis_client as redis_cache
    from openbase.modules.identity import verification as verifier

    # 1) 缓存值缺关键字段（token_version）→ 视同未命中返回 None
    monkeypatch.setattr(
        redis_cache, "cache_get", lambda key: {"status_state": "active"}
    )
    assert verifier._cache_get_snapshot(1) is None

    # 2) cache_get 抛异常 → 视同未命中返回 None
    def _boom_get(key: str):
        raise RuntimeError("redis down")

    monkeypatch.setattr(redis_cache, "cache_get", _boom_get)
    assert verifier._cache_get_snapshot(1) is None

    # 3) cache_set / cache_delete 抛异常 → 静默降级（不阻断）
    def _boom_set(key: str, value, ttl: int = 300) -> bool:
        raise RuntimeError("redis down")

    def _boom_delete(*keys: str) -> bool:
        raise RuntimeError("redis down")

    monkeypatch.setattr(redis_cache, "cache_set", _boom_set)
    monkeypatch.setattr(redis_cache, "cache_delete", _boom_delete)
    verifier._cache_set_snapshot(1, {"status_state": "active", "token_version": 0})
    verifier.invalidate_principal_cache(1, "admin")
    assert True  # 到达此处即证明异常被吞、未向调用方抛出
