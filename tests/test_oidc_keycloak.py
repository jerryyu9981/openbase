"""OIDC Keycloak profile 适配测试（OB-AUTH-OIDC v1.4.0）.

覆盖: openbase/modules/auth/oidc.py
  - _roles_from_keycloak：realm_access/resource_access 嵌套角色聚合纯函数
  - callback keycloak 分支：ID Token 无角色 → 验签 access token 兜底聚合
mock IdP 以 Keycloak 默认形状签发（角色仅进 access token，ID Token 不含），
网关 oidc_profile=keycloak 跑授权码全链路。
"""
from __future__ import annotations

import base64
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from openbase import init_app
from openbase.modules.auth.oidc import _roles_from_keycloak


@pytest.fixture(autouse=True)
def _oidc_keycloak_force_no_db(monkeypatch):
    """Keycloak profile E2E 族强制"DB 不可用 → 降级直签"路径（空库语义，T2 隔离修复 2026-09-06）.

    与 test_oidc_gateway.py 同因：断言 sub==IdP claims 仅在降级直签路径成立；
    测试进程注入 POSTGRES_URL 使共享库可达时，固定 sub=kc-user-001 命中历史
    OidcIdentity 行复用旧用户（实得 '4'，2026-09-05 全量失败）。强制 db 不可达
    等价"空库"，任何环境下稳定走降级语义。
    """
    monkeypatch.setenv(
        "OPENBASE_DB_URL",
        "postgresql+asyncpg://no-db-user:no-pass@127.0.0.1:1/no_db",
    )
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    # 全量 pytest 中前序用例可能已按真实库建全局 engine 单例，须重置避免绕过 env 隔离
    from conftest import reset_db_singletons

    reset_db_singletons()
    yield
    # teardown 复原：清空 settings/engine 单例，使后续文件按已恢复 env 重建
    import sys

    try:
        settings_module = sys.modules["openbase.settings"]
        settings_module._settings = None
    except KeyError:
        pass
    reset_db_singletons()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sign(payload: dict, pem: bytes, kid: str) -> str:
    from jose import jwt as jose_jwt

    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    return jose_jwt.encode(payload, pem, algorithm="RS256", headers=header)


class KeycloakStyleIdp:
    """Keycloak 默认形状 mock IdP：角色仅进 access token（realm_access/resource_access）.

    ID Token 仅携带标准身份 claims（模拟未配置角色 mapper 的默认 client）。
    """

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
        numbers = self.public_key.public_numbers()
        n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
        self.kid = "kc-idp-key-1"
        self.jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": _b64url(n),
            "e": _b64url(e),
        }
        self.now = int(time.time())

    def app(self) -> FastAPI:
        app = FastAPI(title="keycloak-style-idp")

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
            form = await request.form()
            assert form.get("client_id") == self.client_id
            assert form.get("client_secret") == self.client_secret
            identity = {
                "iss": self.issuer,
                "sub": "kc-user-001",
                "aud": self.client_id,
                "exp": self.now + 3600,
                "iat": self.now,
                "preferred_username": "kc-user",
                "email": "kc-user@example.com",
                "tenant_id": "default",
            }
            # ID Token：无角色（Keycloak 默认不含）
            id_token = _sign(dict(identity), self._pem, self.kid)
            # access token：Keycloak 默认形状（realm_access 含默认伪角色在前）
            access_payload = dict(identity)
            access_payload["realm_access"] = {
                "roles": ["default-roles-openbase", "org_admin", "offline_access"]
            }
            access_payload["resource_access"] = {
                "account": {"roles": ["view-profile"]},
                self.client_id: {"roles": ["viewer"]},
            }
            access_token = _sign(access_payload, self._pem, self.kid)
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 3600,
                "id_token": id_token,
            }

        return app


@pytest.fixture(scope="module")
def kc_idp_url():
    """启动 Keycloak 形状 mock IdP（uvicorn 线程，9011）. """
    import threading

    import uvicorn

    idp = KeycloakStyleIdp(
        issuer="http://127.0.0.1:9011",
        client_id="openbase-kc",
        client_secret="kc-secret",
    )
    config = uvicorn.Config(idp.app(), host="127.0.0.1", port=9011, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            import urllib.request

            urllib.request.urlopen("http://127.0.0.1:9011/jwks", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    yield "http://127.0.0.1:9011"
    server.should_exit = True


def _enable_oidc(settings_module, kc_url: str, profile: str) -> None:
    """构造指定 profile 的 Settings 写入全局单例. """
    s = settings_module.Settings()
    s.enable_module("auth")
    s.oidc_discovery_url = f"{kc_url}/.well-known/openid-configuration"
    s.oidc_redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    s.oidc_client_id = "openbase-kc"
    s.oidc_client_secret = "kc-secret"
    s.oidc_profile = profile
    settings_module._settings = s


def _run_callback(client, status: int = 200):
    """authorize → 模拟 IdP 302 回调 → 返回令牌响应. """
    auth = client.get("/api/v1/auth/oidc/authorize").json()
    state = auth["state"]
    resp = client.get(
        f"http://testserver/api/v1/auth/oidc/callback?code=mock-code&state={state}"
    )
    assert resp.status_code == status, resp.text
    return resp.json()


def _decode_jwt(token: str, secret: str) -> dict:
    from jose import jwt as jose_jwt

    return jose_jwt.decode(token, secret, algorithms=["HS256"])


# ---------------------------------------------------------------------------
# 纯函数：_roles_from_keycloak
# ---------------------------------------------------------------------------


def test_realm_roles_extracted():
    claims = {"realm_access": {"roles": ["org_admin", "offline_access"]}}
    assert _roles_from_keycloak(claims, "openbase-kc") == [
        "org_admin",
        "offline_access",
    ]


def test_client_roles_only_for_matching_client():
    claims = {
        "realm_access": {"roles": ["user"]},
        "resource_access": {
            "other-app": {"roles": ["evil"]},
            "openbase-kc": {"roles": ["org_admin", "user"]},
        },
    }
    roles = _roles_from_keycloak(claims, "openbase-kc")
    assert "evil" not in roles
    assert "org_admin" in roles
    assert roles.count("user") == 1  # realm+client 同名去重


def test_client_roles_disabled():
    claims = {
        "realm_access": {"roles": ["user"]},
        "resource_access": {"openbase-kc": {"roles": ["org_admin"]}},
    }
    roles = _roles_from_keycloak(claims, "openbase-kc", include_client_roles=False)
    assert roles == ["user"]


def test_flat_roles_compatible_and_dedupe():
    claims = {
        "roles": ["org_admin", "user"],  # 自定义 mapper 平铺
        "realm_access": {"roles": ["org_admin", "offline_access"]},
        "role": "viewer",
    }
    assert _roles_from_keycloak(claims, "openbase-kc") == [
        "org_admin",
        "user",
        "viewer",
        "offline_access",
    ]


def test_no_roles_returns_empty():
    assert _roles_from_keycloak({"sub": "x"}, "openbase-kc") == []


# ---------------------------------------------------------------------------
# 网关全链路（profile=keycloak）
# ---------------------------------------------------------------------------


def _new_client(settings_module, kc_url: str, profile: str):
    _enable_oidc(settings_module, kc_url, profile)
    s = settings_module._settings
    app = init_app(s)
    return TestClient(app), s


def test_keycloak_profile_access_token_role_fallback(monkeypatch, kc_idp_url):
    """ID Token 无角色 → 验签 access token 聚合 realm_access → 统一 JWT role=org_admin. """
    import sys

    from openbase.modules.auth import oidc as oidc_module

    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None
    try:
        client, s = _new_client(settings_module, kc_idp_url, "keycloak")
        tokens = _run_callback(client)
        payload = _decode_jwt(tokens["access_token"], s.jwt_secret)
        assert payload["sub"] == "kc-user-001"  # 测试环境 DB 不可用 → 降级直签
        assert payload["role"] == "org_admin"  # access token 兜底生效
    finally:
        settings_module._settings = None
        oidc_module._oidc_client = None


def test_keycloak_profile_uses_id_token_roles_when_present(monkeypatch, kc_idp_url):
    """ID Token 自带平铺 roles（已配 mapper）→ 直接采用，无需 access token 兜底. """
    import sys

    from openbase.modules.auth import oidc as oidc_module

    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None
    orig_parse = oidc_module.OIDCClient.parse_id_token
    orig_exchange = oidc_module.OIDCClient.exchange_code
    try:
        _enable_oidc(settings_module, kc_idp_url, "keycloak")
        s = settings_module._settings

        async def _fake_exchange(self, code):  # noqa: ANN001
            return {"id_token": "mock-id", "access_token": "mock-at"}

        # 打桩 parse_id_token：返回含平铺 roles 的 claims（模拟 Keycloak 已配置角色 mapper）
        oidc_module.OIDCClient.parse_id_token = (  # type: ignore[method-assign]
            lambda self, tok, access_token=None: {
                "iss": kc_idp_url,
                "sub": "kc-user-001",
                "aud": "openbase-kc",
                "exp": int(time.time()) + 3600,
                "preferred_username": "kc-user",
                "email": "kc-user@example.com",
                "tenant_id": "default",
                "roles": ["org_admin"],
            }
        )
        oidc_module.OIDCClient.exchange_code = _fake_exchange  # type: ignore[method-assign]
        app = init_app(s)
        client = TestClient(app)
        tokens = _run_callback(client)
        payload = _decode_jwt(tokens["access_token"], s.jwt_secret)
        assert payload["role"] == "org_admin"
    finally:
        oidc_module.OIDCClient.parse_id_token = orig_parse
        oidc_module.OIDCClient.exchange_code = orig_exchange
        settings_module._settings = None
        oidc_module._oidc_client = None


def test_generic_profile_ignores_nested_roles(monkeypatch, kc_idp_url):
    """默认 generic profile：不识 realm_access 嵌套（向后兼容边界，角色空 → viewer）. """
    import sys

    from openbase.modules.auth import oidc as oidc_module

    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None
    try:
        client, s = _new_client(settings_module, kc_idp_url, "generic")
        tokens = _run_callback(client)
        payload = _decode_jwt(tokens["access_token"], s.jwt_secret)
        assert payload["role"] == "viewer"
    finally:
        settings_module._settings = None
        oidc_module._oidc_client = None
