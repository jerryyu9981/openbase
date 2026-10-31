"""OIDC token 端点客户端认证方式测试（v1.17.0）.

覆盖三种 RFC 约定的客户端认证方式：
``client_secret_post``（表单，默认）/ ``client_secret_basic``（RFC 6749 §2.3.1）
/ ``mtls``（RFC 8705 双向 TLS 客户端证书）；含载荷与请求选项装配、授权码
全链路、以及启动门禁（非法方式 / 缺证书路径 / 路径不存在）。
"""
from __future__ import annotations

import threading
import time
import urllib.request

import httpx
import pytest
from fastapi.testclient import TestClient
from test_oidc_gateway import MockIdp, _authorize_nonce

from openbase import init_app
from openbase.modules.auth.oidc import OIDCClient


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
def mock_idp():
    """单 mock IdP（9014）：供 post / basic 两种认证方式全链路使用."""
    import uvicorn

    idp = MockIdp(
        "http://127.0.0.1:9014",
        "token-auth-client",
        "token-auth-secret",
        sub="token-auth-user",
        tenant_id="tenant-1",
        roles=["user"],
    )
    server = uvicorn.Server(
        uvicorn.Config(idp.app(), host="127.0.0.1", port=9014, log_level="error")
    )
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{idp.issuer}/jwks", timeout=1)
            break
        except Exception:  # noqa: BLE001 - 启动探活
            time.sleep(0.2)
    yield idp
    server.should_exit = True


@pytest.fixture()
def settings_module(monkeypatch):
    """重置全局 settings 与 OIDC 客户端单例."""
    monkeypatch.setenv(
        "OPENBASE_JWT_SECRET", "test-jwt-secret-v680-0123456789abcdefghij"
    )
    import sys

    import openbase.settings  # noqa: F401  确保 sys.modules 注册真模块
    from openbase.modules.auth import oidc as oidc_module

    module = sys.modules["openbase.settings"]
    module._settings = None
    oidc_module._oidc_client = None
    oidc_module._provider_clients.clear()
    yield module
    oidc_module._oidc_client = None
    oidc_module._provider_clients.clear()
    module._settings = None


def _build_app(settings_module, idp, *, token_auth_method: str):
    """构造启用 OIDC 的 Settings 并装配应用（显式覆盖 .env 值）."""
    s = settings_module.Settings()
    s.enable_module("auth")
    s.oidc_enabled = True
    s.oidc_discovery_url = f"{idp.issuer}/.well-known/openid-configuration"
    s.oidc_client_id = idp.client_id
    s.oidc_client_secret = idp.client_secret
    s.oidc_redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    s.oidc_token_auth_method = token_auth_method
    s.idp_providers = ""
    settings_module._settings = s
    return s, TestClient(init_app(s))


def _login(client) -> dict:
    """授权码全链路，返回统一 JWT 令牌对."""
    auth = client.get("/api/v1/auth/oidc/authorize").json()
    nonce = _authorize_nonce(auth["authorize_url"])
    resp = client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": f"mock-code.{nonce}", "state": auth["state"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# 载荷 / 请求选项装配（单元）
# ---------------------------------------------------------------------------


def _client_for(settings_module, method: str, **kwargs) -> OIDCClient:
    s = settings_module.Settings(
        oidc_client_id="unit-client",
        oidc_client_secret="unit-secret",
        oidc_redirect_uri="http://unit/callback",
        oidc_token_auth_method=method,
        **kwargs,
    )
    return OIDCClient(settings=s)


def test_token_payload_client_secret_post(settings_module):
    """默认 post：client_id/secret 均在表单，无额外请求选项."""
    client = _client_for(settings_module, "client_secret_post")
    payload = client.token_payload("code-1", code_verifier="verifier-1")
    assert payload["client_id"] == "unit-client"
    assert payload["client_secret"] == "unit-secret"
    assert payload["code_verifier"] == "verifier-1"
    assert client.token_request_options() == {}


def test_token_payload_client_secret_basic(settings_module):
    """basic：凭据走 HTTP Basic 头，表单不得重复携带（RFC 6749 §2.3.1）."""
    client = _client_for(settings_module, "client_secret_basic")
    payload = client.token_payload("code-1")
    assert "client_id" not in payload
    assert "client_secret" not in payload
    options = client.token_request_options()
    assert isinstance(options["auth"], httpx.BasicAuth)


def test_token_payload_mtls(settings_module, tmp_path):
    """mTLS：仅带 client_id，证书/私钥/CA 由 httpx cert/verify 装配（RFC 8705）."""
    cert = tmp_path / "client.pem"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.pem"
    for item in (cert, key, ca):
        item.write_text("dummy")
    client = _client_for(
        settings_module,
        "mtls",
        oidc_client_cert_path=str(cert),
        oidc_client_key_path=str(key),
        oidc_client_ca_path=str(ca),
    )
    payload = client.token_payload("code-1")
    assert payload["client_id"] == "unit-client"
    assert "client_secret" not in payload
    options = client.token_request_options()
    assert options["cert"] == (str(cert), str(key))
    assert options["verify"] == str(ca)


# ---------------------------------------------------------------------------
# 授权码全链路（post / basic）
# ---------------------------------------------------------------------------


def test_exchange_code_default_uses_post(settings_module, mock_idp):
    """默认配置：token 端点收到表单凭据（post），全链路签发统一 JWT."""
    _s, client = _build_app(
        settings_module, mock_idp, token_auth_method="client_secret_post"
    )
    tokens = _login(client)
    assert tokens["access_token"]
    assert mock_idp.token_auth_calls[-1] == "post"


def test_exchange_code_basic_authentication(settings_module, mock_idp):
    """配置 basic：token 端点收到 Authorization Basic 头，全链路仍签发成功."""
    _s, client = _build_app(
        settings_module, mock_idp, token_auth_method="client_secret_basic"
    )
    tokens = _login(client)
    assert tokens["access_token"]
    assert mock_idp.token_auth_calls[-1] == "basic"


# ---------------------------------------------------------------------------
# 启动门禁
# ---------------------------------------------------------------------------


def test_gate_rejects_unknown_token_auth_method(settings_module):
    """非法认证方式 → 拒绝启动."""
    with pytest.raises(ValueError, match="OPENBASE_OIDC_TOKEN_AUTH_METHOD"):
        settings_module.Settings(oidc_token_auth_method="private_key_jwt")


def test_gate_rejects_mtls_without_cert_paths(settings_module):
    """mtls 缺证书/私钥路径 → 拒绝启动."""
    with pytest.raises(ValueError, match="mTLS"):
        settings_module.Settings(oidc_token_auth_method="mtls")


def test_gate_rejects_missing_cert_file(settings_module, tmp_path):
    """mtls 证书路径不存在 → 拒绝启动（避免运行期 token 端点不可用）."""
    with pytest.raises(ValueError, match="不存在"):
        settings_module.Settings(
            oidc_token_auth_method="mtls",
            oidc_client_cert_path=str(tmp_path / "absent.pem"),
            oidc_client_key_path=str(tmp_path / "absent.key"),
        )


def test_gate_accepts_mtls_with_existing_files(settings_module, tmp_path):
    """mtls 证书/私钥/CA 文件均存在 → 正常构造，方式归一为小写."""
    cert = tmp_path / "client.pem"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.pem"
    for item in (cert, key, ca):
        item.write_text("dummy")
    s = settings_module.Settings(
        oidc_token_auth_method=" MTLS ",
        oidc_client_cert_path=str(cert),
        oidc_client_key_path=str(key),
        oidc_client_ca_path=str(ca),
    )
    assert s.oidc_token_auth_method == "mtls"
