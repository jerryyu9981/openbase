"""U1 T2（RA-02 / OB-2 状态机 + OB-4）生命周期状态机与 login tenant_code 闭环 TDD 用例.

RED→GREEN 断言对齐《OpenBase-U1-统一身份收口设计草案》v1.0.0 §11 T2-1~T2-8：
- T2-1  状态机合法迁移全绿：provisioned→active→suspended→active→suspended→deactivated→purged
- T2-2  非法迁移 0 路径：validate_transition 全量组合（含 active→purged、purged→*、
        provisioned→deactivated 等）一律 400 BIZ_STATE_TRANSITION_INVALID
- T2-3  login/refresh 签发 token claims 100% 含 tenant_code/sub_type/tvn（注入 N 用户抽样断言）
- T2-4  存量无 tenant_code 旧 access 兼容放行（不 401）；refresh 后新 token 补齐 tenant_code
- T2-5  suspended 主体 login/refresh 拒绝（401 AUTH_PRINCIPAL_DISABLED）；restore 后重登成功
- T2-6  OIDC bound 停用拦截：suspended/deactivated 主体经 IdP 回调被拒（callback 401）
- T2-7  lifecycle API 鉴权：非 admin 无 identity:lifecycle → 403
- T2-8  停用→恢复→再停用全链路正确（状态/版本/token 各自断言）+ deactivate 事件出 outbox
- 补充：suspend agent → 全部 sk-agent-* key 失效（吊销联动）
"""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Base, Permission, Role, Tenant, User, user_role
from openbase.modules.auth import hash_password
from openbase.modules.auth.jwt import create_access_token, create_refresh_token
from openbase.settings import Settings, get_settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t2.db"


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
    """装配启用 identity 模块的应用 + SQLite 库种子（角色/权限/租户 acme）."""
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
                    [
                        {"user_id": admin.id, "role_id": role_admin.id},
                    ]
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
def _identity_t2_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局 engine 单例）."""
    global client
    client = _build_app()
    yield client
    client = None


# ---- 数据库辅助 ----

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
        conn.execute(
            TENANT_SQL, {"name": code.title(), "code": code}
        )
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
    credential_type: str = "password",
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
                "credential_type": credential_type,
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
    if role:
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


def _seed_oidc_binding(user_id: int, sub: str, issuer: str = "http://oidc-t2") -> None:
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO oidc_identity (user_id, sub, issuer, created_at, updated_at) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user_id, sub, issuer),
        )
        conn.commit()
    finally:
        conn.close()


def _login(username: str, password: str = "secret123"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return resp


def _admin_headers() -> dict[str, str]:
    resp = _login("admin", "admin123")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _decode(token: str) -> dict:
    settings = get_settings()
    return jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _state_row(user_id: int) -> tuple:
    row = _rows(
        f"SELECT status_state, status_reason, token_version, status FROM users WHERE id = {user_id}"
    )
    assert len(row) == 1, f"user {user_id} not found"
    return row[0]


def _lifecycle_url(subject_type: str, subject_id: int, action: str) -> str:
    return f"/api/v1/identity/lifecycle/{subject_type}/{subject_id}/{action}"


def _suspend(subject_type: str, subject_id: int, reason: str = "suspend via t2"):
    return client.post(
        _lifecycle_url(subject_type, subject_id, "suspend"),
        json={"reason": reason},
        headers=_admin_headers(),
    )


def _restore(subject_type: str, subject_id: int, reason: str = "restore via t2"):
    return client.post(
        _lifecycle_url(subject_type, subject_id, "restore"),
        json={"reason": reason},
        headers=_admin_headers(),
    )


def _deactivate(subject_type: str, subject_id: int, reason: str = "deactivate via t2"):
    return client.post(
        _lifecycle_url(subject_type, subject_id, "deactivate"),
        json={"confirm": True, "reason": reason},
        headers=_admin_headers(),
    )


def _activate(subject_type: str, subject_id: int, reason: str = "activate via t2"):
    return client.post(
        _lifecycle_url(subject_type, subject_id, "activate"),
        json={"reason": reason},
        headers=_admin_headers(),
    )


# ---- T2-1 / T2-2 状态机矩阵（纯函数） ----


def test_t2_1_legal_transition_chain_all_green() -> None:
    """合法迁移链 provisioned→active→suspended→active→suspended→deactivated→purged 全绿."""
    from openbase.modules.identity.state_machine import (
        STATUS_STATE_ACTIVE,
        STATUS_STATE_DEACTIVATED,
        STATUS_STATE_PROVISIONED,
        STATUS_STATE_PURGED,
        STATUS_STATE_SUSPENDED,
        is_transition_allowed,
        validate_transition,
    )

    chain = [
        STATUS_STATE_PROVISIONED,
        STATUS_STATE_ACTIVE,
        STATUS_STATE_SUSPENDED,
        STATUS_STATE_ACTIVE,
        STATUS_STATE_SUSPENDED,
        STATUS_STATE_DEACTIVATED,
        STATUS_STATE_PURGED,
    ]
    # 相邻两两为合法迁移对（chain 7 元素 → 6 对）
    for current, target in zip(chain, chain[1:], strict=False):
        assert is_transition_allowed(current, target), f"{current} -> {target}"
        validate_transition(current, target)  # 不抛即合法


def test_t2_2_illegal_transitions_zero_paths() -> None:
    """非法迁移 0 路径：全量组合断言抛 400 BIZ_STATE_TRANSITION_INVALID."""
    from openbase.modules.identity.state_machine import (
        STATUS_STATE_ACTIVE,
        STATUS_STATE_DEACTIVATED,
        STATUS_STATE_PROVISIONED,
        STATUS_STATE_PURGED,
        STATUS_STATE_SUSPENDED,
        VALID_STATUS_STATES,
        is_transition_allowed,
        validate_transition,
    )

    allowed = {
        (STATUS_STATE_PROVISIONED, STATUS_STATE_ACTIVE),
        (STATUS_STATE_ACTIVE, STATUS_STATE_SUSPENDED),
        (STATUS_STATE_ACTIVE, STATUS_STATE_DEACTIVATED),
        (STATUS_STATE_SUSPENDED, STATUS_STATE_ACTIVE),
        (STATUS_STATE_SUSPENDED, STATUS_STATE_DEACTIVATED),
        (STATUS_STATE_DEACTIVATED, STATUS_STATE_PURGED),
    }
    for current in VALID_STATUS_STATES:
        for target in VALID_STATUS_STATES:
            if (current, target) in allowed:
                continue
            assert not is_transition_allowed(current, target), f"{current} -> {target}"
            try:
                validate_transition(current, target)
            except BaseError as exc:
                assert exc.code == ErrorCode.BIZ_STATE_TRANSITION_INVALID
                assert exc.status_code == 400
            else:
                raise AssertionError(f"illegal transition allowed: {current} -> {target}")


# ---- T2-3 login/refresh 签发 100% tenant_code ----


def test_t2_3_login_and_refresh_tokens_100_percent_tenant_code() -> None:
    """注入 N 用户各签一次：access 与 refresh 再签全含 tenant_code/sub_type/tvn."""
    users: list[int] = []
    for index in range(4):
        users.append(_make_user(_unique(f"tc{index}"), tenant_code="acme"))

    for user_id in users:
        username = _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]
        login_resp = _login(username)
        assert login_resp.status_code == 200, login_resp.text
        body = login_resp.json()
        access_payload = _decode(body["access_token"])
        assert access_payload.get("tenant_code") == "acme", access_payload
        assert access_payload.get("sub_type") == "user"
        assert "tvn" in access_payload
        assert access_payload["sub"] == str(user_id)

        # refresh 再签：新 access 仍 100% 含 tenant_code（fidelity 断言）
        refresh_resp = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
        )
        assert refresh_resp.status_code == 200, refresh_resp.text
        refreshed_payload = _decode(refresh_resp.json()["access_token"])
        assert refreshed_payload.get("tenant_code") == "acme", refreshed_payload
        assert refreshed_payload.get("sub_type") == "user"
        assert "tvn" in refreshed_payload
        # refresh token 本身亦含全量 claim（刷新链 fidelity 闭环）
        assert _decode(body["refresh_token"]).get("tenant_code") == "acme"


# ---- T2-4 存量 v0 令牌兼容 + 刷新补齐 ----


def test_t2_4_v0_access_compatible_and_refresh_upgrades_tenant_code() -> None:
    """存量无 tenant_code 旧 access 不 401（过渡窗口放行）；v0 refresh 刷新后补齐."""
    user_id = _make_user(_unique("v0"), tenant_code="acme")
    username = _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]
    tenant_id = _rows(f"SELECT tenant_id FROM users WHERE id = {user_id}")[0][0]

    # 存量 v0 access（无 tvn/sub_type/tenant_code 的旧形态令牌）→ /auth/me 放行
    legacy_access = create_access_token(str(user_id), username=username)
    me_resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy_access}"}
    )
    assert me_resp.status_code == 200, me_resp.text
    assert me_resp.json()["id"] == user_id

    # v0 refresh（仅 sub + tenant_id）→ 刷新后新 access 补齐 tenant_code + tvn
    legacy_refresh = create_refresh_token(str(user_id), str(tenant_id))
    refresh_resp = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": legacy_refresh}
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    upgraded = _decode(refresh_resp.json()["access_token"])
    assert upgraded.get("tenant_code") == "acme", upgraded
    assert upgraded.get("sub") == str(user_id)


# ---- T2-5 suspended 拒登 / restore 重登 ----


def test_t2_5_suspended_login_refresh_rejected_and_restore_relogin() -> None:
    """suspended 主体 login/refresh 拒绝；restore 后重登成功."""
    user_id = _make_user(_unique("sus"), tenant_code="acme")
    username = _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]

    login_resp = _login(username)
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    suspend_resp = _suspend("user", user_id, reason="security hold")
    assert suspend_resp.status_code == 200, suspend_resp.text
    assert suspend_resp.json()["status_state"] == "suspended"

    # 拒登（401 AUTH_PRINCIPAL_DISABLED）：password 正确亦拒绝
    blocked = _login(username)
    assert blocked.status_code == 401, blocked.text
    assert blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value

    # refresh 拒签（签发侧状态校验）
    refresh_blocked = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_blocked.status_code == 401, refresh_blocked.text
    assert refresh_blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value

    # restore 后重登成功（token_version 已 +1，新令牌携带新版本）
    restore_resp = _restore("user", user_id)
    assert restore_resp.status_code == 200, restore_resp.text
    assert restore_resp.json()["status_state"] == "active"
    relogin = _login(username)
    assert relogin.status_code == 200, relogin.text
    assert _decode(relogin.json()["access_token"]).get("tvn") == 2


# ---- T2-6 OIDC 停用拦截 + bound/直签 token claims ----


def _patch_oidc(
    monkeypatch: pytest.MonkeyPatch,
    claims: dict,
    mapped: dict,
) -> None:
    """打桩 OIDC 客户端：跳过 HTTP 直达 callback 逻辑（state 已注入）. """
    import openbase.modules.auth.oidc as oidc_module

    oidc_module._state_store["t2-oidc-state"] = "pending"

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


def _oidc_callback(code: str = "mock-code") -> object:
    return client.get(
        "/api/v1/auth/oidc/callback?code=mock-code&state=t2-oidc-state"
    )


def test_t2_6_oidc_suspended_and_deactivated_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """suspended/deactivated 绑定主体经 IdP 回调被拒（callback 401 AUTH_PRINCIPAL_DISABLED）."""
    claims = {
        "iss": "http://oidc-t2",
        "sub": "blocked-oidc-sub",
        "preferred_username": "blocked-oidc",
        "email": "blocked-oidc@openbase.local",
        "roles": ["viewer"],
    }
    mapped = {
        "sub": claims["sub"],
        "username": claims["preferred_username"],
        "tenant_id": "acme",
        "extra": {"org_id": "acme", "role": "viewer"},
    }

    for state in ("suspended", "deactivated"):
        per_state_claims = dict(
            claims,
            sub=f"blocked-oidc-sub-{state}",
            preferred_username=f"blocked-oidc-{state}",
            email=f"blocked-oidc-{state}@openbase.local",
        )
        per_state_mapped = dict(
            mapped,
            sub=per_state_claims["sub"],
            username=per_state_claims["preferred_username"],
        )
        user_id = _make_user(_unique(f"oidc-{state}"), tenant_code="acme", state=state)
        _seed_oidc_binding(user_id, per_state_claims["sub"])
        _patch_oidc(monkeypatch, per_state_claims, per_state_mapped)
        resp = _oidc_callback()
        assert resp.status_code == 401, (state, resp.text)
        assert resp.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


def test_t2_6_oidc_bound_active_issues_full_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """OIDC bound 主体（active）经回调签发：sub=用户 id、tenant_code/sub_type/tvn 齐备."""
    user_id = _make_user(_unique("oidc-ok"), tenant_code="acme", state="active")
    sub = "good-oidc-sub"
    _seed_oidc_binding(user_id, sub)
    claims = {
        "iss": "http://oidc-t2",
        "sub": sub,
        "preferred_username": _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0],
        "email": "good@openbase.local",
        "roles": ["viewer"],
    }
    mapped = {
        "sub": sub,
        "username": claims["preferred_username"],
        "tenant_id": "acme",
        "extra": {"org_id": "acme", "role": "viewer"},
    }
    _patch_oidc(monkeypatch, claims, mapped)
    resp = _oidc_callback()
    assert resp.status_code == 200, resp.text
    payload = _decode(resp.json()["access_token"])
    assert payload["sub"] == str(user_id)
    assert payload.get("tenant_code") == "acme"
    assert payload.get("sub_type") == "user"
    assert payload.get("tvn") == 0


def test_t2_6_oidc_direct_sign_issues_full_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """OIDC 降级直签（bound=None）与正常签发共用签发器：tenant_code/sub_type/tvn 齐备."""
    claims = {
        "iss": "http://oidc-t2",
        "sub": "direct-oidc-sub",
        "preferred_username": "direct-oidc",
        "email": "direct@openbase.local",
        "roles": ["org_admin"],
    }
    mapped = {
        "sub": claims["sub"],
        "username": "direct-oidc",
        "tenant_id": "direct-code",
        "extra": {"org_id": "direct-code", "role": "org_admin"},
    }
    _patch_oidc(monkeypatch, claims, mapped)

    import openbase.modules.auth.oidc as oidc_module

    # 强制 DB 降级直签（绑定返回 None → 以 IdP sub 直签）
    async def _force_none(parsed: dict, session: object) -> None:
        return None

    monkeypatch.setattr(oidc_module, "_bind_or_create_user", _force_none)
    resp = _oidc_callback()
    assert resp.status_code == 200, resp.text
    payload = _decode(resp.json()["access_token"])
    assert payload["sub"] == "direct-oidc-sub"
    assert payload.get("tenant_code") == "direct-code"
    assert payload.get("sub_type") == "user"
    assert "tvn" in payload


# ---- T2-7 lifecycle API 鉴权 ----


def test_t2_7_lifecycle_api_requires_identity_lifecycle_permission() -> None:
    """非 admin 无 identity:lifecycle 权限 → 403；admin（通配）可停用."""
    victim = _make_user(_unique("victim"), tenant_code="acme")
    viewer_user = _make_user(_unique("viewer-op"), tenant_code=None, role="viewer")
    viewer_name = _rows(f"SELECT username FROM users WHERE id = {viewer_user}")[0][0]

    viewer_login = _login(viewer_name)
    assert viewer_login.status_code == 200, viewer_login.text
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

    denied = client.post(
        _lifecycle_url("user", victim, "suspend"),
        json={"reason": "noperm"},
        headers=viewer_headers,
    )
    assert denied.status_code == 403, denied.text

    allowed = _suspend("user", victim)
    assert allowed.status_code == 200, allowed.text


def test_t2_1_activate_provisioned_to_active_via_api() -> None:
    """API 触发 provisioned→active（activate 端点）：状态/tvn 正确，激活后即可登录."""
    user_id = _make_user(_unique("prov"), tenant_code="acme", state="provisioned")
    username = _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]
    assert _state_row(user_id)[0] == "provisioned"
    # provisioned 不可登录（active 才可认证）
    assert _login(username).status_code == 401

    resp = _activate("user", user_id, reason="onboarding complete")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["previous_state"] == "provisioned"
    assert body["status_state"] == "active"
    assert body["token_version"] == 0  # 启用无吊销副作用（不递增）
    state = _state_row(user_id)
    assert state[0] == "active"
    assert state[3] == 1  # 兼容读视图 status(int)
    assert _login(username).status_code == 200


# ---- T2-8 停用→恢复→再停用全链路 + deactivate 事件钩子 ----


def test_t2_8_suspend_restore_resuspend_full_chain() -> None:
    """停用→恢复→再停用：状态/版本/token 各自断言."""
    user_id = _make_user(_unique("chain"), tenant_code="acme")
    username = _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]

    # 初始 active / tvn=0
    assert _state_row(user_id)[2] == 0
    login0 = _login(username)
    assert login0.status_code == 200
    assert _decode(login0.json()["access_token"])["tvn"] == 0

    # ① 停用：active→suspended，tvn 0→1
    s1 = _suspend("user", user_id)
    assert s1.status_code == 200
    state1 = _state_row(user_id)
    assert state1[0] == "suspended"
    assert state1[2] == 1
    assert state1[3] == 0  # 兼容读视图 status(int)
    assert s1.json()["previous_state"] == "active"

    # ② 恢复：suspended→active，tvn 1→2（旧 token 不复活：版本已递增）
    r1 = _restore("user", user_id)
    assert r1.status_code == 200
    state2 = _state_row(user_id)
    assert state2[0] == "active"
    assert state2[2] == 2
    assert state2[1] is not None  # status_reason 已写
    login1 = _login(username)
    assert login1.status_code == 200
    assert _decode(login1.json()["access_token"])["tvn"] == 2

    # ③ 再停用：active→suspended，tvn 2→3
    s2 = _suspend("user", user_id)
    assert s2.status_code == 200
    state3 = _state_row(user_id)
    assert state3[0] == "suspended"
    assert state3[2] == 3
    blocked = _login(username)
    assert blocked.status_code == 401
    assert blocked.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value

    # 全链 outbox 事件（同事务写入，T5 事件源本体前的事件表骨架断言）
    events = _rows(
        "SELECT event_type, status FROM outbox_events WHERE payload LIKE "
        f"'%\"subject_id\": {user_id}%' ORDER BY id"
    )
    assert any("user.suspended" in str(row) for row in events)
    assert any("user.restored" in str(row) for row in events)
    assert len(events) == 3  # suspend + restore + suspend


def test_t2_8_deactivate_writes_event_and_blocks_all_issuance() -> None:
    """deactivate：状态=deactivated + tvn+1 + outbox user.deactivated + login/refresh 全拒."""
    user_id = _make_user(_unique("deact"), tenant_code="acme")
    username = _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]

    login_resp = _login(username)
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    # 无 confirm 二次确认 → 400（防误触，草案 §4.2）
    no_confirm = client.post(
        _lifecycle_url("user", user_id, "deactivate"),
        json={"reason": "member left"},
        headers=_admin_headers(),
    )
    assert no_confirm.status_code == 400, no_confirm.text
    assert no_confirm.json()["code"] == ErrorCode.PARAM_INVALID.value

    deact = _deactivate("user", user_id, reason="member left")
    assert deact.status_code == 200, deact.text
    assert deact.json()["status_state"] == "deactivated"
    state = _state_row(user_id)
    assert state[0] == "deactivated"
    assert state[2] == 1

    assert _login(username).status_code == 401
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}).status_code
        == 401
    )
    outbox = _rows("SELECT event_type, status FROM outbox_events ORDER BY id DESC LIMIT 1")
    assert outbox and outbox[0][0] == "user.deactivated"
    assert outbox[0][1] == "pending"


# ---- 补充：agent 状态适用（suspend agent → sk-agent-* 全失效） ----


def test_t2_agent_suspend_revokes_all_agent_keys() -> None:
    """suspend agent → 状态 suspended + 全部 sk-agent-* key 置 revoked（联动吊销）."""
    admin_headers = _admin_headers()
    username = _unique("agent")
    create_resp = client.post(
        "/api/v1/identity/agents",
        json={"username": username, "display_name": "Agent T2", "role": "viewer"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    agent_id = create_resp.json()["agent_id"]
    raw_key = create_resp.json()["api_key"]["raw_key"]

    assert client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {raw_key}"}
    ).status_code == 200

    extra_key = client.post(
        f"/api/v1/identity/agents/{agent_id}/keys",
        json={"name": "second"},
        headers=admin_headers,
    )
    assert extra_key.status_code == 200
    raw_key2 = extra_key.json()["raw_key"]

    suspend_resp = _suspend("agent", agent_id, reason="agent retired")
    assert suspend_resp.status_code == 200, suspend_resp.text
    assert suspend_resp.json()["status_state"] == "suspended"

    # 全部 sk-agent-* key 已吊销（DB status=revoked）
    key_rows = _rows(
        f"SELECT status FROM agent_api_keys WHERE agent_id = {agent_id}"
    )
    assert key_rows and all(row[0] == "revoked" for row in key_rows)

    # 任意已发密钥校验均 401（吊销 + 主体状态双门禁）
    for raw in (raw_key, raw_key2):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})
        assert resp.status_code == 401, resp.text


# ---- T2-1 API 侧补强：lifecycle 端点非法路径 400 ----


def test_t2_1_lifecycle_api_rejects_illegal_transition() -> None:
    """重复 suspend（active 前提破坏）/非法端点迁移 → 400 BIZ_STATE_TRANSITION_INVALID."""
    user_id = _make_user(_unique("badpath"), tenant_code="acme")

    # active → suspended 合法
    assert _suspend("user", user_id).status_code == 200
    # suspended → suspended（同态）非法 → 400
    again = _suspend("user", user_id)
    assert again.status_code == 400, again.text
    assert again.json()["code"] == ErrorCode.BIZ_STATE_TRANSITION_INVALID.value
