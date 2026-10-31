"""OIDC 多 Provider 登录路由测试（v1.15.0）.

覆盖：``GET /api/v1/auth/oidc/authorize?provider=<name>`` 按 Provider 选择客户端、
state 载荷携带 Provider 名、callback 按 state 还原 Provider、未登记/空登记的 400 口径，
以及「不指定 provider」时单 IdP 既有语义不变。
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient
from test_oidc_gateway import MockIdp, _authorize_nonce

from openbase import init_app


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


@pytest.fixture(scope="module")
def multi_idps():
    """启动两个 mock IdP（9012 / 9013），claims 与 client 凭据各不相同."""
    import threading
    import urllib.request

    import uvicorn

    idps = {
        "gov-idp": MockIdp(
            "http://127.0.0.1:9012",
            "gov-client",
            "gov-secret",
            sub="gov-user",
            tenant_id="tenant-gov",
            roles=["user"],
        ),
        "corp-idp": MockIdp(
            "http://127.0.0.1:9013",
            "corp-client",
            "corp-secret",
            sub="corp-user",
            tenant_id="tenant-corp",
            roles=["org_admin"],
        ),
    }
    servers = []
    for port, idp in zip((9012, 9013), idps.values(), strict=True):
        server = uvicorn.Server(
            uvicorn.Config(idp.app(), host="127.0.0.1", port=port, log_level="error")
        )
        threading.Thread(target=server.run, daemon=True).start()
        servers.append(server)
    deadline = time.time() + 10
    for port in (9012, 9013):
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/jwks", timeout=1)
                break
            except Exception:  # noqa: BLE001 - 启动探活
                time.sleep(0.2)
    yield idps
    for server in servers:
        server.should_exit = True


@pytest.fixture()
def oidc_env(monkeypatch):
    """重置 settings 与 OIDC 客户端单例（含 Provider 缓存）."""
    monkeypatch.setenv("OPENBASE_JWT_SECRET", "test-jwt-secret-v680-0123456789abcdefghij")
    import sys

    import openbase.settings  # noqa: F401  确保 sys.modules 注册真模块
    from openbase.modules.auth import oidc as oidc_module

    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None
    oidc_module._provider_clients.clear()
    yield settings_module
    oidc_module._oidc_client = None
    oidc_module._provider_clients.clear()
    settings_module._settings = None


def _providers_json(multi_idps) -> str:
    """两个 Provider 的 ``OPENBASE_IDP_PROVIDERS`` JSON（回调共用网关端点）."""
    return json.dumps(
        [
            {
                "name": "gov-idp",
                "discovery_url": (
                    f"{multi_idps['gov-idp'].issuer}/.well-known/openid-configuration"
                ),
                "client_id": "gov-client",
                "client_secret": "gov-secret",
                "profile": "generic",
                "claim_role": "roles",
                "default_tenant": "tenant-gov",
            },
            {
                "name": "corp-idp",
                "discovery_url": (
                    f"{multi_idps['corp-idp'].issuer}/.well-known/openid-configuration"
                ),
                "client_id": "corp-client",
                "client_secret": "corp-secret",
                "profile": "generic",
                "claim_role": "roles",
                "default_tenant": "tenant-corp",
            },
        ],
        ensure_ascii=False,
    )


def _build_app(settings_module, providers: str, *, enabled: bool = True):
    """构造启用 OIDC + 多 Provider 的 Settings 并装配应用."""
    s = settings_module.Settings()
    s.enable_module("auth")
    # 显式覆盖 .env 可能存在的 OIDC 值，保证用例语义确定
    s.oidc_enabled = enabled
    s.oidc_discovery_url = ""
    s.oidc_client_id = "openbase-test"
    s.oidc_client_secret = "test-secret"
    s.oidc_redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    s.idp_providers = providers
    settings_module._settings = s
    return s, TestClient(init_app(s))


def test_authorize_unknown_provider_returns_param_invalid(oidc_env, multi_idps):
    """未登记 Provider 名 → 400 PARAM_INVALID（口径与 state/参数非法一致）."""
    _s, client = _build_app(oidc_env, _providers_json(multi_idps))
    resp = client.get("/api/v1/auth/oidc/authorize", params={"provider": "unknown-idp"})
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["code"] == "PARAM_INVALID"
    assert "unknown oidc provider" in body["message"]


def test_authorize_without_registered_provider_returns_param_invalid(oidc_env):
    """未登记任何 Provider 时指定 provider → 400（不得回落单 IdP 静默登录）."""
    _s, client = _build_app(oidc_env, "")
    resp = client.get("/api/v1/auth/oidc/authorize", params={"provider": "gov-idp"})
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "PARAM_INVALID"
    assert "no oidc provider registered" in resp.json()["message"]


def test_authorize_provider_uses_provider_client(oidc_env, multi_idps):
    """按 provider 构建授权 URL：端点/ client_id 取自 Provider，state 载荷记 Provider 名."""
    from openbase.modules.auth.oidc_state import get_state_store

    _s, client = _build_app(oidc_env, _providers_json(multi_idps))
    resp = client.get("/api/v1/auth/oidc/authorize", params={"provider": "gov-idp"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["authorize_url"].startswith("http://127.0.0.1:9012/authorize?")
    assert "client_id=gov-client" in data["authorize_url"]
    assert data["provider"] == "gov-idp"
    stored = get_state_store().consume(data["state"])
    assert stored is not None
    assert stored["provider"] == "gov-idp"
    assert stored["nonce"]


def test_callback_uses_provider_from_state(oidc_env, multi_idps):
    """全链路：provider=corp-idp 授权 → 回调按 state 还原客户端 → 统一 JWT 取 corp claims."""
    from jose import jwt as jose_jwt

    s, client = _build_app(oidc_env, _providers_json(multi_idps))
    auth = client.get(
        "/api/v1/auth/oidc/authorize", params={"provider": "corp-idp"}
    ).json()
    nonce = _authorize_nonce(auth["authorize_url"])
    resp = client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": f"mock-code.{nonce}", "state": auth["state"]},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    payload = jose_jwt.decode(
        tokens["access_token"], s.jwt_secret, algorithms=[s.jwt_algorithm]
    )
    assert payload["sub"] == "corp-user"
    assert payload["tenant_id"] == "tenant-corp"
    assert payload["role"] == "org_admin"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["username"] == "corp-user"


def test_single_idp_path_unaffected_without_provider(oidc_env):
    """不指定 provider：OIDC 未启用时仍 404（单 IdP 既有语义零变化）."""
    _s, client = _build_app(oidc_env, "", enabled=False)
    resp = client.get("/api/v1/auth/oidc/authorize")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# v1.16.0：IdP 登出联动
# ---------------------------------------------------------------------------


def _login_tokens(client, provider: str) -> dict:
    """走 provider 授权码全链路，返回统一 JWT 令牌对."""
    auth = client.get(
        "/api/v1/auth/oidc/authorize", params={"provider": provider}
    ).json()
    nonce = _authorize_nonce(auth["authorize_url"])
    resp = client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": f"mock-code.{nonce}", "state": auth["state"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_logout_requires_authentication(oidc_env, multi_idps):
    """未携带令牌 → 401（登出同样受鉴权保护，不允许匿名吊销）."""
    _s, client = _build_app(oidc_env, _providers_json(multi_idps))
    resp = client.post("/api/v1/auth/oidc/logout")
    assert resp.status_code == 401, resp.text


def test_logout_unknown_provider_returns_param_invalid(oidc_env, multi_idps):
    """未知 Provider → 400 PARAM_INVALID，且不产生「已吊销但未登出」半态."""
    _s, client = _build_app(oidc_env, _providers_json(multi_idps))
    tokens = _login_tokens(client, "gov-idp")
    resp = client.post(
        "/api/v1/auth/oidc/logout",
        params={"provider": "unknown-idp"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "PARAM_INVALID"


def test_logout_returns_idp_end_session_url(oidc_env, multi_idps):
    """登出返回 IdP end_session URL（provider 声明）；DB 不可达时本地吊销跳过."""
    _s, client = _build_app(oidc_env, _providers_json(multi_idps))
    tokens = _login_tokens(client, "gov-idp")
    resp = client.post(
        "/api/v1/auth/oidc/logout",
        params={"provider": "gov-idp"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["logged_out"] is True
    assert data["idp_logout_url"].startswith("http://127.0.0.1:9012/logout?")
    assert "client_id=gov-client" in data["idp_logout_url"]
    # DB 不可达 → 无本地主体可递增版本（降级路径不阻断登出）
    assert data["token_version"] is None


def test_revoke_local_tokens_increments_version():
    """本地吊销：数字主体 token_version 递增；非数字（OIDC 直签）主体跳过."""

    class _StubRow:
        token_version = 2

    class _StubSession:
        committed = False

        async def get(self, model, pk):
            return _StubRow()

        async def commit(self):
            self.committed = True

        async def rollback(self):
            return None

    from openbase.modules.auth import oidc as oidc_module

    session = _StubSession()
    assert asyncio.run(oidc_module._revoke_local_tokens(session, "7")) == 3
    assert session.committed is True
    assert asyncio.run(oidc_module._revoke_local_tokens(_StubSession(), "corp-user")) is None
