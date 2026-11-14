"""OIDC 覆盖率边角补测（覆盖率治理 v1.5.0）.

覆盖 ``openbase/modules/auth/oidc.py`` 中难以经既有 E2E 触发的分支：

- 客户端配置解析/回落（Provider redirect/default_tenant、算法归一）；
- discovery 缺失端点、断言前置校验、令牌验签失败包装；
- Keycloak 角色聚合的异常形状；
- 用户绑定/租户解析的降级路径（DB 不可用、回滚失败）；
- 回调错误码（error 参数、缺参、未启用、缺 id_token、角色兜底）；
- 登出本地吊销与 IdP 登出尽力而为；
- back-channel logout 的载荷解析、候选发现失败与 sid 未命中。
"""
from __future__ import annotations

import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

import openbase.modules.auth.oidc as oidc_module
from openbase import init_app
from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth.idp_registry import IdpProviderConfig
from openbase.modules.auth.oidc import (
    BACKCHANNEL_LOGOUT_EVENT,
    OIDCClient,
    OIDCError,
    _audience_matches,
    _bind_or_create_user,
    _ensure_roles,
    _logout_token_algorithms,
    _registered_providers,
    _roles_from_keycloak,
    _tenant_code_from_id,
    _verify_logout_token,
)
from openbase.modules.auth.oidc_logout import get_logout_store
from openbase.modules.auth.oidc_state import get_state_store

# ---------------------------------------------------------------------------
# 夹具
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _oidc_force_no_db(monkeypatch):
    """强制「DB 不可用 → 降级直签」路径（与 OIDC E2E 族同口径）."""
    monkeypatch.setenv(
        "OPENBASE_DB_URL",
        "postgresql+asyncpg://no-db-user:no-pass@127.0.0.1:1/no_db",
    )
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    from conftest import reset_db_singletons

    reset_db_singletons()
    yield
    import sys

    try:
        sys.modules["openbase.settings"]._settings = None
    except KeyError:
        pass
    reset_db_singletons()


@pytest.fixture()
def settings_module(monkeypatch):
    """重置全局 settings / OIDC 客户端单例 / Provider 缓存."""
    monkeypatch.setenv(
        "OPENBASE_JWT_SECRET", "test-jwt-secret-v680-0123456789abcdefghij"
    )
    import sys

    import openbase.settings  # noqa: F401  确保 sys.modules 注册真模块

    module = sys.modules["openbase.settings"]
    module._settings = None
    oidc_module._oidc_client = None
    oidc_module._provider_clients.clear()
    yield module
    oidc_module._oidc_client = None
    oidc_module._provider_clients.clear()
    module._settings = None


@pytest.fixture()
def logout_store(monkeypatch):
    """登出存储清空（Redis 不可用 → 进程内确定性）."""
    from openbase.core.cache import redis_client

    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    store = get_logout_store()
    store.clear_all()
    yield store
    store.clear_all()


def _settings(**overrides):
    """OIDCClient 注入用最小配置对象."""
    defaults = {
        "oidc_enabled": True,
        "oidc_discovery_url": "http://idp/.well-known/openid-configuration",
        "oidc_client_id": "cid",
        "oidc_client_secret": "secret",
        "oidc_redirect_uri": "http://app/callback",
        "oidc_scopes": "openid profile",
        "oidc_profile": "generic",
        "oidc_claim_role": "roles",
        "oidc_default_tenant": "tenant-1",
        "oidc_pkce_enabled": True,
        "oidc_signing_algorithms": "RS256",
        "oidc_token_auth_method": "client_secret_post",
        "oidc_client_assertion_algorithm": "RS256",
        "oidc_client_private_key_path": "",
        "oidc_client_assertion_kid": "",
        "oidc_client_cert_path": "",
        "oidc_client_key_path": "",
        "oidc_client_ca_path": "",
        "idp_providers": "",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _build_app(settings_module, **overrides):
    """装配启用 OIDC 的应用（真实 Settings，供路由级用例使用）."""
    s = settings_module.Settings()
    s.enable_module("auth")
    s.oidc_enabled = True
    s.oidc_discovery_url = "http://127.0.0.1:1/.well-known/openid-configuration"
    s.oidc_client_id = "edge-client"
    s.oidc_client_secret = "edge-secret"
    s.oidc_redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    s.idp_providers = ""
    s.oidc_keycloak_client_roles = True
    for field_name, value in overrides.items():
        setattr(s, field_name, value)
    settings_module._settings = s
    return s, TestClient(init_app(s))


class _FakeResult:
    """SQLAlchemy 结果替代（scalars/scalar_one_or_none 链式）."""

    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _QueueSession:
    """按调用顺序返回预设结果的异步会话."""

    def __init__(self, results=None, *, get_value=None, fail_get=False, fail_rollback=False):
        self._results = list(results or [])
        self._get_value = get_value
        self._fail_get = fail_get
        self._fail_rollback = fail_rollback
        self.calls: list = []

    async def execute(self, stmt):
        self.calls.append(stmt)
        return self._results.pop(0) if self._results else _FakeResult([])

    async def get(self, model, pk):
        if self._fail_get:
            raise RuntimeError("db unreachable")
        return self._get_value

    async def rollback(self):
        if self._fail_rollback:
            raise RuntimeError("rollback failed")


class _SyncHttp:
    """同步 httpx.Client 替代（JWKS 拉取）."""

    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url):
        return SimpleNamespace(json=lambda: self._payload)


class _AsyncHttp:
    """异步 httpx.AsyncClient 替代（discovery/token 端点）."""

    def __init__(self, get_payload=None, post_payload=None):
        self._get_payload = get_payload or {}
        self._post_payload = post_payload or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url):
        return SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: self._get_payload
        )

    async def post(self, url, data=None, **kwargs):
        return SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: self._post_payload
        )


# ---------------------------------------------------------------------------
# 客户端配置与 discovery
# ---------------------------------------------------------------------------


def test_normalized_algorithms_dedupes_and_ignores_blanks():
    assert oidc_module._normalized_algorithms(" rs256, ,RS256,es256 ") == [
        "RS256",
        "ES256",
    ]
    assert oidc_module._normalized_algorithms("") == []


def test_client_provider_redirect_and_default_tenant():
    """Provider 声明优先；未声明回落全局（C-05）."""
    provider = IdpProviderConfig(
        name="p1",
        discovery_url="http://idp/.well-known/openid-configuration",
        client_id="p1-client",
        redirect_uri="http://idp/callback",
        default_tenant="tenant-p1",
    )
    client = OIDCClient(settings=_settings(), provider=provider)
    assert client.redirect_uri == "http://idp/callback"
    assert client.default_tenant == "tenant-p1"

    plain = OIDCClient(
        settings=_settings(
            oidc_redirect_uri="http://global/callback", oidc_default_tenant="tenant-g"
        )
    )
    assert plain.redirect_uri == "http://global/callback"
    assert plain.default_tenant == "tenant-g"


async def test_load_discovery_rejects_missing_endpoints(monkeypatch):
    fake = _AsyncHttp(get_payload={"issuer": "http://idp"})
    monkeypatch.setattr(oidc_module.httpx, "AsyncClient", lambda *a, **k: fake)
    client = OIDCClient(settings=_settings())
    with pytest.raises(OIDCError, match="missing endpoints"):
        await client._load_discovery()
    assert client.issuer == "http://idp"


async def test_build_authorize_url_omits_optional_params(monkeypatch):
    fake = _AsyncHttp(
        get_payload={
            "issuer": "http://idp",
            "authorization_endpoint": "http://idp/authorize",
            "token_endpoint": "http://idp/token",
        }
    )
    monkeypatch.setattr(oidc_module.httpx, "AsyncClient", lambda *a, **k: fake)
    client = OIDCClient(settings=_settings())
    url = await client.build_authorize_url("state-1")
    params = parse_qs(urlparse(url).query)
    assert params["state"] == ["state-1"]
    assert "nonce" not in params
    assert "code_challenge" not in params


def test_build_client_assertion_requires_endpoint_and_private_key():
    client = OIDCClient(settings=_settings())
    with pytest.raises(OIDCError, match="token endpoint"):
        client._build_client_assertion()
    client._token_endpoint = "http://idp/token"
    with pytest.raises(OIDCError, match="private key path"):
        client._build_client_assertion()


def test_verify_token_requires_discovery_and_jwks_uri():
    client = OIDCClient(settings=_settings())
    with pytest.raises(OIDCError, match="discovery not loaded"):
        client._verify_token("token")
    client._discovery = {
        "issuer": "http://idp",
        "authorization_endpoint": "http://idp/authorize",
        "token_endpoint": "http://idp/token",
    }
    with pytest.raises(OIDCError, match="jwks_uri"):
        client._verify_token("token")


def test_verify_token_wraps_jwt_error(monkeypatch):
    monkeypatch.setattr(
        oidc_module.httpx, "Client", lambda *a, **k: _SyncHttp({"keys": []})
    )
    client = OIDCClient(settings=_settings())
    client._discovery = {
        "issuer": "http://idp",
        "jwks_uri": "http://idp/jwks",
        "id_token_signing_alg_values_supported": ["RS256"],
    }
    with pytest.raises(OIDCError, match="token validation failed"):
        client._verify_token("not-a-jwt")


async def test_build_logout_url_edges():
    client = OIDCClient(settings=_settings())
    client._discovery_url = client.discovery_url  # 命中缓存，跳过真实网络
    client._discovery = {"end_session_endpoint": ""}
    assert await client.build_logout_url() is None

    client._discovery = {"end_session_endpoint": "http://idp/logout"}
    bare = await client.build_logout_url()
    assert bare == "http://idp/logout?client_id=cid"

    with_redirect = await client.build_logout_url(
        post_logout_redirect_uri="http://app/done"
    )
    params = parse_qs(urlparse(with_redirect).query)
    assert params["post_logout_redirect_uri"] == ["http://app/done"]
    assert "id_token_hint" not in params


def test_registered_providers_invalid_config_raises_system_error(monkeypatch):
    monkeypatch.setattr(
        oidc_module, "get_settings", lambda: _settings(idp_providers="{")
    )
    with pytest.raises(BaseError) as exc_info:
        _registered_providers()
    assert exc_info.value.code == ErrorCode.SYS_INTERNAL_ERROR


def test_roles_from_keycloak_ignores_malformed_shapes():
    assert _roles_from_keycloak({"roles": "admin"}, "cid") == ["admin"]
    assert _roles_from_keycloak({"realm_access": {"roles": "admin"}}, "cid") == []
    assert _roles_from_keycloak({"resource_access": {"cid": "admin"}}, "cid") == []
    assert (
        _roles_from_keycloak({"resource_access": {"cid": {"roles": "admin"}}}, "cid")
        == []
    )


# ---------------------------------------------------------------------------
# 用户绑定降级路径（异步单测）
# ---------------------------------------------------------------------------


async def test_ensure_roles_accepts_string_role():
    session = _QueueSession([_FakeResult(["admin"])])
    assert await _ensure_roles(session, 1, {"role": "admin"}) == "admin"


async def test_ensure_roles_returns_none_without_whitelisted_codes():
    session = _QueueSession([])
    assert await _ensure_roles(session, 1, {"roles": ["superuser"]}) is None


async def test_ensure_roles_skips_role_missing_in_database():
    session = _QueueSession([_FakeResult([]), _FakeResult([])])
    assert await _ensure_roles(session, 1, {"roles": ["admin"]}) is None


async def test_tenant_code_from_id_edges():
    assert await _tenant_code_from_id(_QueueSession([]), "") is None
    assert await _tenant_code_from_id(_QueueSession([]), "acme") == "acme"
    assert await _tenant_code_from_id(_QueueSession([_FakeResult(["acme"])]), "42") == "acme"

    class _BrokenSession:
        async def execute(self, stmt):
            raise RuntimeError("db down")

    assert await _tenant_code_from_id(_BrokenSession(), "42") is None


async def test_bind_user_without_sub_returns_none():
    assert await _bind_or_create_user({}, _QueueSession([])) is None


async def test_bind_user_swallows_rollback_failure():
    class _BrokenSession:
        async def execute(self, stmt):
            raise RuntimeError("db down")

        async def rollback(self):
            raise RuntimeError("rollback failed")

    assert await _bind_or_create_user({"sub": "s-1"}, _BrokenSession()) is None


# ---------------------------------------------------------------------------
# 路由级：authorize / callback
# ---------------------------------------------------------------------------


def _issue_state(nonce: str, state: str = "") -> str:
    """登记一次性 state（默认按 nonce 派生，避免跨用例复用已消费 state）."""
    state = state or f"edge-state-{nonce}"
    get_state_store().issue(state, {"nonce": nonce, "code_verifier": ""})
    return state


def _fake_callback_client(
    monkeypatch,
    *,
    enabled: bool = True,
    profile: str = "generic",
    token_resp: dict | None = None,
    claims: dict | None = None,
    verify_error: Exception | None = None,
    bound: dict | None = None,
    mapped: dict | None = None,
):
    """打桩 OIDC 客户端与用户绑定（聚焦 callback 分支）."""

    class _FakeClient:
        provider_name = ""
        client_id = "edge-client"
        issuer = ""

        def __init__(self):
            self.enabled = enabled
            self.profile = profile

        async def exchange_code(self, code, *, code_verifier=None):
            return token_resp or {"id_token": "fake-id-token", "access_token": "at"}

        def parse_id_token(self, id_token, access_token=None):
            return dict(claims or {})

        def verify_access_token(self, access_token):
            if verify_error is not None:
                raise verify_error
            return {"realm_access": {"roles": ["org_admin"]}}

        def map_claims(self, parsed):
            if mapped is not None:
                return dict(mapped)
            roles = parsed.get("roles") or ["viewer"]
            return {
                "sub": str(parsed.get("sub") or "oidc-anonymous"),
                "username": parsed.get("preferred_username") or "edge-user",
                "tenant_id": str(parsed.get("tenant_id") or "tenant-1"),
                "extra": {"org_id": "tenant-1", "role": roles[0]},
            }

    monkeypatch.setattr(oidc_module, "_get_oidc_client", lambda: _FakeClient())

    async def _bind(parsed, session):
        return bound

    monkeypatch.setattr(oidc_module, "_bind_or_create_user", _bind)


def test_authorize_discovery_failure_returns_upstream_error(settings_module, monkeypatch):
    class _BrokenClient:
        enabled = True
        provider_name = ""
        pkce_enabled = False

        async def build_authorize_url(self, state, *, nonce="", code_challenge=""):
            raise OIDCError("discovery document missing endpoints")

    monkeypatch.setattr(oidc_module, "_get_oidc_client", lambda: _BrokenClient())
    _, client = _build_app(settings_module)
    resp = client.get("/api/v1/auth/oidc/authorize")
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == ErrorCode.SYS_UPSTREAM_ERROR.value


def test_callback_rejects_error_and_missing_params(settings_module):
    _, client = _build_app(settings_module)
    error_resp = client.get(
        "/api/v1/auth/oidc/callback", params={"error": "access_denied", "state": "s"}
    )
    assert error_resp.status_code == 400, error_resp.text
    assert error_resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert "access_denied" in error_resp.json()["message"]

    missing = client.get("/api/v1/auth/oidc/callback")
    assert missing.status_code == 400, missing.text


def test_callback_rejects_disabled_client(settings_module, monkeypatch):
    _fake_callback_client(monkeypatch, enabled=False)
    _, client = _build_app(settings_module)
    state = _issue_state("nonce-disabled")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value


def test_callback_rejects_missing_id_token(settings_module, monkeypatch):
    _fake_callback_client(
        monkeypatch, token_resp={"access_token": "at"}, claims={"sub": "s"}
    )
    _, client = _build_app(settings_module)
    state = _issue_state("nonce-no-id")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == ErrorCode.SYS_UPSTREAM_ERROR.value


@pytest.mark.parametrize(
    "token_resp, claims, verify_error",
    [
        # ID Token 无角色且响应无 access_token → 跳过兜底
        ({"id_token": "id"}, {"sub": "kc-1", "nonce": "nonce-kc"}, None),
        # access_token 验签失败 → 仅告警，角色保持空
        (
            {"id_token": "id", "access_token": "at"},
            {"sub": "kc-2", "nonce": "nonce-kc"},
            OIDCError("bad access token"),
        ),
        # 仅伪角色 → 白名单过滤后为空
        (
            {"id_token": "id"},
            {"sub": "kc-3", "nonce": "nonce-kc", "roles": ["offline_access"]},
            None,
        ),
    ],
)
def test_callback_keycloak_role_fallback_edges(
    settings_module, monkeypatch, token_resp, claims, verify_error
):
    _fake_callback_client(
        monkeypatch,
        profile="keycloak",
        token_resp=token_resp,
        claims=claims,
        verify_error=verify_error,
    )
    _, client = _build_app(settings_module)
    state = _issue_state("nonce-kc")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 200, resp.text


def test_callback_bound_subject_lookup_failure_rejected(settings_module, monkeypatch):
    bound = {"id": 5, "username": "bound-user", "tenant_id": None, "role": "user"}
    _fake_callback_client(monkeypatch, claims={"sub": "s", "nonce": "n-bound"}, bound=bound)
    _, client = _build_app(settings_module)
    session = _QueueSession([], fail_get=True)
    client.app.dependency_overrides[get_db] = lambda: session
    state = _issue_state("n-bound")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value


def test_callback_bound_subject_missing_row_rejected(settings_module, monkeypatch):
    bound = {"id": 6, "username": "bound-user", "tenant_id": None, "role": "user"}
    _fake_callback_client(monkeypatch, claims={"sub": "s", "nonce": "n-miss"}, bound=bound)
    _, client = _build_app(settings_module)
    session = _QueueSession([], get_value=None)
    client.app.dependency_overrides[get_db] = lambda: session
    state = _issue_state("n-miss")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 401, resp.text


def test_callback_bound_tenant_code_fallback_and_role_snapshot(settings_module, monkeypatch):
    bound = {"id": 7, "username": "bound-user", "tenant_id": None, "role": "user"}
    _fake_callback_client(monkeypatch, claims={"sub": "s", "nonce": "n-tenant"}, bound=bound)
    _, client = _build_app(settings_module)
    user_row = SimpleNamespace(
        id=7,
        username="bound-user",
        tenant_id=42,
        tenant_code="",
        subject_type="user",
        status_state="active",
        token_version=0,
    )
    session = _QueueSession([_FakeResult(["acme"]), _FakeResult(["user"])], get_value=user_row)
    client.app.dependency_overrides[get_db] = lambda: session
    state = _issue_state("n-tenant")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_callback_bound_inactive_subject_rejected(settings_module, monkeypatch):
    """绑定主体非 active（suspended/deactivated）→ 401 AUTH_PRINCIPAL_DISABLED."""
    bound = {"id": 8, "username": "bound-user", "tenant_id": None, "role": "user"}
    _fake_callback_client(
        monkeypatch, claims={"sub": "s", "nonce": "n-inactive"}, bound=bound
    )
    _, client = _build_app(settings_module)
    user_row = SimpleNamespace(
        id=8,
        username="bound-user",
        tenant_id=None,
        tenant_code="",
        subject_type="user",
        status_state="suspended",
        token_version=0,
    )
    session = _QueueSession([], get_value=user_row)
    client.app.dependency_overrides[get_db] = lambda: session
    state = _issue_state("n-inactive")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value
    assert "not active" in resp.json()["message"]


def test_callback_bound_tenant_code_present_skips_lookup(settings_module, monkeypatch):
    """主体行已有 tenant_code → 不再回查 tenants 表（仅一次角色查询）."""
    bound = {"id": 9, "username": "bound-user", "tenant_id": None, "role": "user"}
    _fake_callback_client(
        monkeypatch, claims={"sub": "s", "nonce": "n-tenant-code"}, bound=bound
    )
    _, client = _build_app(settings_module)
    user_row = SimpleNamespace(
        id=9,
        username="bound-user",
        tenant_id=42,
        tenant_code="acme",
        subject_type="user",
        status_state="active",
        token_version=0,
    )
    session = _QueueSession([_FakeResult(["user"])], get_value=user_row)
    client.app.dependency_overrides[get_db] = lambda: session
    state = _issue_state("n-tenant-code")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 200, resp.text
    assert len(session.calls) == 1


def test_callback_logout_hint_persist_failure_ignored(settings_module, monkeypatch):
    """ID Token hint 保存失败仅告警，不阻断登录."""
    _fake_callback_client(monkeypatch, claims={"sub": "s", "nonce": "n-hint"})

    class _BrokenStore:
        def save_id_token_hint(self, **kwargs):
            raise RuntimeError("logout store down")

    monkeypatch.setattr(oidc_module, "get_logout_store", lambda: _BrokenStore())
    _, client = _build_app(settings_module)
    state = _issue_state("n-hint")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 200, resp.text


def test_callback_direct_sign_without_tenant(settings_module, monkeypatch):
    """降级直签且 claims 无租户 → 跳过 tenants 回查，仍可签发."""
    mapped = {
        "sub": "direct-sub",
        "username": "direct-user",
        "tenant_id": "",
        "extra": {"org_id": "", "role": "viewer"},
    }
    _fake_callback_client(
        monkeypatch, claims={"sub": "direct-sub", "nonce": "n-direct"}, mapped=mapped
    )
    _, client = _build_app(settings_module)
    state = _issue_state("n-direct")
    resp = client.get(
        "/api/v1/auth/oidc/callback", params={"code": "c", "state": state}
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# 路由级：logout
# ---------------------------------------------------------------------------


def _auth_app(settings_module, session, **overrides):
    s, client = _build_app(settings_module, **overrides)
    client.app.dependency_overrides[get_db] = lambda: session
    client.app.dependency_overrides[get_current_user] = lambda: {"id": "5"}
    return s, client


def test_logout_missing_local_row_keeps_token_version_none(settings_module):
    _, client = _auth_app(
        settings_module, _QueueSession([], get_value=None), oidc_enabled=False
    )
    resp = client.post("/api/v1/auth/oidc/logout")
    assert resp.status_code == 200, resp.text
    assert resp.json()["token_version"] is None


def test_logout_swallows_revocation_rollback_failure(settings_module):
    _, client = _auth_app(
        settings_module,
        _QueueSession([], fail_get=True, fail_rollback=True),
        oidc_enabled=False,
    )
    resp = client.post("/api/v1/auth/oidc/logout")
    assert resp.status_code == 200, resp.text
    assert resp.json()["token_version"] is None


def test_logout_rejects_unenabled_provider(settings_module):
    providers = json.dumps(
        [
            {
                "name": "p1",
                "discovery_url": "http://127.0.0.1:1/.well-known/openid-configuration",
                "client_id": "p1-client",
            }
        ]
    )
    _, client = _auth_app(
        settings_module,
        _QueueSession([], get_value=None),
        oidc_enabled=False,
        idp_providers=providers,
    )
    resp = client.post("/api/v1/auth/oidc/logout", params={"provider": "p1"})
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value


class _FakeLogoutClient:
    provider_name = ""
    client_id = "edge-client"
    issuer = "http://idp"

    def __init__(self, error: Exception | None = None):
        self._error = error

    async def _load_discovery(self):
        if self._error is not None:
            raise self._error

    async def build_logout_url(self, *, post_logout_redirect_uri="", id_token_hint=""):
        return "http://idp/logout"


def test_logout_without_id_token_hint(settings_module, monkeypatch, logout_store):
    monkeypatch.setattr(
        oidc_module, "_get_oidc_client", lambda: _FakeLogoutClient()
    )
    _, client = _auth_app(settings_module, _QueueSession([], get_value=None))
    resp = client.post("/api/v1/auth/oidc/logout")
    assert resp.status_code == 200, resp.text
    assert resp.json()["idp_logout_url"] == "http://idp/logout"


def test_logout_idp_failure_is_best_effort(settings_module, monkeypatch, logout_store):
    monkeypatch.setattr(
        oidc_module,
        "_get_oidc_client",
        lambda: _FakeLogoutClient(OIDCError("discovery down")),
    )
    _, client = _auth_app(settings_module, _QueueSession([], get_value=None))
    resp = client.post("/api/v1/auth/oidc/logout")
    assert resp.status_code == 200, resp.text
    assert resp.json()["idp_logout_url"] is None


# ---------------------------------------------------------------------------
# back-channel logout 内部函数与载荷解析
# ---------------------------------------------------------------------------


def test_audience_matches_variants():
    assert _audience_matches("c1", "c1") is True
    assert _audience_matches(["c0", "c1"], "c1") is True
    assert _audience_matches(["c0"], "c1") is False
    assert _audience_matches(None, "c1") is False


def test_logout_token_algorithms_edges():
    client = OIDCClient(settings=_settings())
    # 未声明 backchannel 算法 → 回落 id_token 算法声明
    client._discovery = {"id_token_signing_alg_values_supported": ["RS256"]}
    assert _logout_token_algorithms(client) == ["RS256"]
    # 声明形状非法（非数组）→ 以仓内全集为口径
    client._discovery = {"id_token_signing_alg_values_supported": "RS256"}
    assert _logout_token_algorithms(client) == ["RS256"]
    # 与客户端白名单无交集 → 失败（禁静默降级）
    client._discovery = {"backchannel_logout_signing_alg_values_supported": ["ES256"]}
    with pytest.raises(OIDCError, match="no mutually supported"):
        _logout_token_algorithms(client)


def test_verify_logout_token_requires_jwks_uri():
    client = OIDCClient(settings=_settings())
    client._discovery = {}
    with pytest.raises(OIDCError, match="jwks_uri"):
        _verify_logout_token(client, "token")


def test_backchannel_rejects_malformed_json_body(settings_module):
    _, client = _build_app(settings_module)
    resp = client.post(
        "/api/v1/auth/oidc/backchannel-logout",
        content="not-json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value

    non_object = client.post(
        "/api/v1/auth/oidc/backchannel-logout", json=["logout_token"]
    )
    assert non_object.status_code == 400, non_object.text


def test_backchannel_rejects_non_jwt(settings_module):
    _, client = _build_app(settings_module)
    resp = client.post(
        "/api/v1/auth/oidc/backchannel-logout",
        data={"logout_token": "not-a-jwt"},
    )
    assert resp.status_code == 400, resp.text
    assert "valid JWT" in resp.json()["message"]


def test_backchannel_rejects_non_object_claims(settings_module, monkeypatch):
    _, client = _build_app(settings_module)
    monkeypatch.setattr(
        oidc_module.jose_jwt, "get_unverified_claims", lambda token: ["not", "claims"]
    )
    resp = client.post(
        "/api/v1/auth/oidc/backchannel-logout",
        data={"logout_token": "header.payload.signature"},
    )
    assert resp.status_code == 400, resp.text
    assert "valid JWT" in resp.json()["message"]


class _CandidateClient:
    def __init__(
        self,
        *,
        issuer: str,
        client_id: str = "candidate-client",
        error: Exception | None = None,
    ):
        self.provider_name = "candidate"
        self.client_id = client_id
        self._issuer = issuer
        self._error = error
        self._discovery = {
            "backchannel_logout_supported": True,
            "jwks_uri": "http://127.0.0.1:1/jwks",
        }

    @property
    def issuer(self):
        return self._issuer

    async def _load_discovery(self):
        if self._error is not None:
            raise self._error


def _hs_token(claims: dict) -> str:
    return jose_jwt.encode(claims, "unit-secret", algorithm="HS256")


def test_backchannel_skips_broken_and_mismatched_candidates(settings_module, monkeypatch):
    broken = _CandidateClient(issuer="http://idp", error=OIDCError("discovery down"))
    mismatched = _CandidateClient(issuer="http://other-idp")
    wrong_aud = _CandidateClient(issuer="http://idp", client_id="other-client")
    monkeypatch.setattr(
        oidc_module, "_logout_candidates", lambda: [broken, mismatched, wrong_aud]
    )
    _, client = _build_app(settings_module)
    token = _hs_token({"iss": "http://idp", "aud": "candidate-client", "jti": "j-1"})
    resp = client.post(
        "/api/v1/auth/oidc/backchannel-logout", data={"logout_token": token}
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value


def test_backchannel_unknown_sid_leaves_subject_empty(
    settings_module, monkeypatch, logout_store
):
    candidate = _CandidateClient(issuer="http://idp")
    monkeypatch.setattr(oidc_module, "_logout_candidates", lambda: [candidate])
    monkeypatch.setattr(
        oidc_module,
        "_verify_logout_token",
        lambda client, token: {
            "iss": "http://idp",
            "aud": "candidate-client",
            "exp": int(time.time()) + 300,
            "jti": "j-unknown-sid",
            "sid": "unknown-session",
            "events": {BACKCHANNEL_LOGOUT_EVENT: {}},
        },
    )
    _, client = _build_app(settings_module)
    token = _hs_token({"iss": "http://idp", "aud": "candidate-client"})
    resp = client.post(
        "/api/v1/auth/oidc/backchannel-logout", data={"logout_token": token}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["revoked"] is False
    assert resp.json()["token_version"] is None
