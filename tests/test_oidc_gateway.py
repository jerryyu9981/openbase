"""OIDC 统一认证端到端测试（OB-AUTH-OIDC）.

覆盖: openbase/modules/auth/oidc.py + core/deps/auth.py 白名单
含 mock OIDC IdP（discovery/token/jwks），验证授权码流程 → 统一 JWT → 受保护端点。
"""
from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse

from openbase import init_app

# ---------------------------------------------------------------------------
# mock OIDC IdP（discovery + token + jwks，RS256 签名 ID Token）
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class MockIdp:
    """极简 mock IdP：RS256 签发 ID Token，校验 client_id/secret. """

    def __init__(self, issuer: str, client_id: str, client_secret: str) -> None:
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        self.public_key = self.private_key.public_key()
        self._pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # JWK（仅保留 n/e 与 kid）
        numbers = self.public_key.public_numbers()
        n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
        self.kid = "mock-idp-key-1"
        self.jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": _b64url(n),
            "e": _b64url(e),
        }

    def app(self) -> FastAPI:
        app = FastAPI(title="mock-idp")

        @app.get("/.well-known/openid-configuration")
        async def discovery():
            return {
                "issuer": self.issuer,
                "authorization_endpoint": f"{self.issuer}/authorize",
                "token_endpoint": f"{self.issuer}/token",
                "jwks_uri": f"{self.issuer}/jwks",
                "response_types_supported": ["code"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"],
            }

        @app.get("/jwks")
        async def jwks():
            return {"keys": [self.jwk]}

        @app.post("/token")
        async def token(request: StarletteRequest):
            # 宽松校验 client 凭据（集成说明约束生产必配）
            form = await request.form()
            assert form.get("client_id") == self.client_id
            assert form.get("client_secret") == self.client_secret
            header = {"alg": "RS256", "typ": "JWT", "kid": self.kid}
            payload = {
                "iss": self.issuer,
                "sub": "oidc-user-001",
                "aud": self.client_id,
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "preferred_username": "oidc-user-001",
                "email": "oidc-user-001@example.com",
                "roles": ["org_admin"],
                "tenant_id": "default",
            }
            from jose import jwt as jose_jwt

            id_token = jose_jwt.encode(
                payload, self._pem, algorithm="RS256", headers=header
            )
            return {
                "access_token": "mock-access",
                "token_type": "bearer",
                "expires_in": 3600,
                "id_token": id_token,
            }

        return app

    @staticmethod
    def authorize_redirect(authorize_url: str) -> RedirectResponse:
        """模拟 IdP 授权页自动放行：302 回网关 callback 带 code/state. """
        from urllib.parse import parse_qs, urlparse

        q = parse_qs(urlparse(authorize_url).query)
        state = q["state"][0]
        redirect_uri = q["redirect_uri"][0]
        return RedirectResponse(
            f"{redirect_uri}?code=mock-code&state={state}"
        )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def oidc_settings(monkeypatch):
    """启用 OIDC 的环境变量（mock IdP 指向本地 TestClient）. """
    monkeypatch.setenv("OPENBASE_OIDC_ENABLED", "true")
    monkeypatch.setenv("OPENBASE_OIDC_CLIENT_ID", "openbase-test")
    monkeypatch.setenv("OPENBASE_OIDC_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("OPENBASE_OIDC_REDIRECT_URI", "http://testserver/api/v1/auth/oidc/callback")
    monkeypatch.setenv("OPENBASE_OIDC_CLAIM_ROLE", "roles")
    monkeypatch.setenv("OPENBASE_JWT_SECRET", "test-jwt-secret-for-v680")
    import sys

    import openbase.settings  # noqa: F401  确保 sys.modules 注册真模块
    from openbase.modules.auth import oidc as oidc_module

    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None  # 重置客户端单例（避免 discovery 缓存跨用例残留）
    yield settings_module
    oidc_module._oidc_client = None
    settings_module._settings = None


def _apply_oidc_settings(settings_module, mock_idp_url) -> None:
    """构造启用 OIDC 的 Settings 并写入全局单例（AuthMiddleware/oidc 共享）. """
    s = settings_module.Settings()
    s.enable_module("auth")
    s.oidc_discovery_url = f"{mock_idp_url}/.well-known/openid-configuration"
    s.oidc_redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    settings_module._settings = s


@pytest.fixture(scope="module")
def mock_idp_url():
    """启动 mock IdP（uvicorn 线程，返回 issuer base URL）. """
    import threading

    import uvicorn

    idp = MockIdp(
        issuer="http://127.0.0.1:9010",
        client_id="openbase-test",
        client_secret="test-secret",
    )
    config = uvicorn.Config(idp.app(), host="127.0.0.1", port=9010, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            import urllib.request

            urllib.request.urlopen("http://127.0.0.1:9010/jwks", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    yield "http://127.0.0.1:9010"
    server.should_exit = True


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


def test_oidc_disabled_returns_404(monkeypatch):
    """默认（oidc_enabled=false）：OIDC 端点返回 404，本地认证不受影响. """
    # 显式置 false（覆盖 .env 的 OPENBASE_OIDC_ENABLED=true，env 优先级高于 env_file）
    monkeypatch.setenv("OPENBASE_OIDC_ENABLED", "false")
    import sys

    from openbase.modules.auth import oidc as oidc_module

    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None
    s = settings_module.Settings()
    s.enable_module("auth")
    settings_module._settings = s
    app = init_app(s)
    client = TestClient(app)
    resp = client.get("/api/v1/auth/oidc/authorize")
    assert resp.status_code == 404
    settings_module._settings = None
    oidc_module._oidc_client = None


def test_oidc_authorize_returns_url(oidc_settings, mock_idp_url):
    """authorize：返回 IdP 授权 URL（含 client_id/scope/state）. """
    settings_module = oidc_settings
    _apply_oidc_settings(settings_module, mock_idp_url)
    s = settings_module._settings
    app = init_app(s)
    client = TestClient(app)
    resp = client.get("/api/v1/auth/oidc/authorize")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authorize_url"].startswith(f"{mock_idp_url}/authorize?")
    assert "client_id=openbase-test" in data["authorize_url"]
    assert "state=" in data["authorize_url"]
    assert data["state"]


def test_oidc_callback_full_flow(oidc_settings, mock_idp_url):
    """授权码全流程：callback → 统一 JWT → 受保护端点 200. """
    settings_module = oidc_settings
    _apply_oidc_settings(settings_module, mock_idp_url)
    s = settings_module._settings
    app = init_app(s)
    client = TestClient(app)

    # 1) authorize 获取 state + authorize_url
    auth = client.get("/api/v1/auth/oidc/authorize").json()
    state = auth["state"]
    # 2) 模拟 IdP 302 回调
    redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    resp = client.get(f"{redirect_uri}?code=mock-code&state={state}")
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    # 3) 统一 JWT 携带 OIDC 映射的 claims（sub/tenant_id/org_id/role）
    from jose import jwt as jose_jwt

    payload = jose_jwt.decode(
        tokens["access_token"],
        s.jwt_secret,
        algorithms=[s.jwt_algorithm],
    )
    assert payload["sub"] == "oidc-user-001"
    assert payload["tenant_id"] == "default"
    assert payload["org_id"] == "default"
    assert payload["role"] == "org_admin"

    # 4) 用统一 JWT 访问受保护端点（auth/me 依赖 JWT 解析，非白名单）
    protected = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert protected.status_code == 200, protected.text
    me = protected.json()
    assert me.get("username") == "oidc-user-001"
