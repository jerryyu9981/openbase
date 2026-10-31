"""OIDC 残余项 P1 批次测试（C-01~C-05）.

- C-01：``tls_client_auth`` 客户端证书 SAN 型绑定本地预检；
- C-02：``private_key_jwt`` 断言算法与私钥类型门禁；
- C-03：回调保存 ID Token 并在登出透传 ``id_token_hint``；
- C-04：``POST /api/v1/auth/oidc/backchannel-logout``（签名/events/jti/404）；
- C-05：Provider 级 PKCE / 签名算法 / 认证方式覆盖与回落。
"""
from __future__ import annotations

import datetime
import ipaddress
import json
import threading
import time
import urllib.request

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from test_oidc_gateway import MockIdp, _authorize_nonce

from openbase import init_app
from openbase.core.cache import redis_client
from openbase.core.errors import ErrorCode
from openbase.modules.auth.idp_registry import IdpProviderConfig, parse_idp_providers
from openbase.modules.auth.oidc import (
    BACKCHANNEL_LOGOUT_EVENT,
    OIDCClient,
)
from openbase.modules.auth.oidc_logout import OidcLogoutStore, get_logout_store


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
    monkeypatch.setenv("OPENBASE_JWT_SECRET", "test-jwt-secret-v680-0123456789abcdefghij")
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


def _start_idp(port: int, idp: MockIdp):
    """启动 mock IdP（uvicorn 线程）并等待 jwks 可达."""
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(idp.app(), host="127.0.0.1", port=port, log_level="error")
    )
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{idp.issuer}/jwks", timeout=1)
            break
        except Exception:  # noqa: BLE001 - 启动探活
            time.sleep(0.2)
    return server


@pytest.fixture(scope="module")
def backchannel_idp():
    """支持 back-channel logout 的 mock IdP（9015）."""
    idp = MockIdp(
        "http://127.0.0.1:9015",
        "p1-client",
        "p1-secret",
        sub="p1-user",
        tenant_id="tenant-1",
        roles=["user"],
        backchannel_logout_supported=True,
    )
    server = _start_idp(9015, idp)
    yield idp
    server.should_exit = True


@pytest.fixture(scope="module")
def no_backchannel_idp():
    """未声明 back-channel logout 的 mock IdP（9016）."""
    idp = MockIdp(
        "http://127.0.0.1:9016",
        "no-bc-client",
        "no-bc-secret",
        sub="no-bc-user",
        tenant_id="tenant-1",
    )
    server = _start_idp(9016, idp)
    yield idp
    server.should_exit = True


@pytest.fixture()
def logout_store(monkeypatch):
    """登出存储：强制 Redis 不可用（确定性走进程内），并清空跨用例残留."""
    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    store = get_logout_store()
    store.clear_all()
    yield store
    store.clear_all()


def _settings_for(settings_module, idp, **overrides):
    """构造指向指定 IdP 的 Settings 并写入全局单例."""
    s = settings_module.Settings()
    s.enable_module("auth")
    s.oidc_enabled = True
    s.oidc_discovery_url = f"{idp.issuer}/.well-known/openid-configuration"
    s.oidc_client_id = idp.client_id
    s.oidc_client_secret = idp.client_secret
    s.oidc_redirect_uri = "http://testserver/api/v1/auth/oidc/callback"
    s.idp_providers = ""
    for field_name, value in overrides.items():
        setattr(s, field_name, value)
    settings_module._settings = s
    return s


# ---------------------------------------------------------------------------
# C-01：客户端证书 SAN 预检
# ---------------------------------------------------------------------------


def _write_san_certificate(
    tmp_path, *, dns=None, uri=None, ips=None, emails=None, common_name="openbase-gateway"
):
    """生成含指定 SAN 的自签客户端证书（PEM 证书 + PKCS#8 私钥）."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
    san_entries = []
    san_entries.extend(x509.DNSName(item) for item in (dns or []))
    san_entries.extend(
        x509.UniformResourceIdentifier(item) for item in (uri or [])
    )
    san_entries.extend(
        x509.IPAddress(ipaddress.ip_address(item)) for item in (ips or [])
    )
    san_entries.extend(x509.RFC822Name(item) for item in (emails or []))
    if san_entries:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(san_entries), critical=False
        )
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        builder.public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "client.crt"
    key_path = tmp_path / "client.key"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


def test_gate_san_dns_match_is_case_insensitive(settings_module, tmp_path):
    """配置 DNS SAN 与证书一致（大小写不敏感）→ 正常构造."""
    cert, key = _write_san_certificate(tmp_path, dns=["gateway.example.gov"])
    s = settings_module.Settings(
        oidc_token_auth_method="tls_client_auth",
        oidc_client_cert_path=str(cert),
        oidc_client_key_path=str(key),
        oidc_client_cert_san_dns="GATEWAY.example.gov",
    )
    assert s.oidc_client_cert_san_dns == "GATEWAY.example.gov"


def test_gate_san_dns_mismatch_rejects(settings_module, tmp_path):
    """DNS SAN 不匹配 → 拒绝启动."""
    cert, key = _write_san_certificate(tmp_path, dns=["gateway.example.gov"])
    with pytest.raises(ValueError, match="OPENBASE_OIDC_CLIENT_CERT_SAN_DNS"):
        settings_module.Settings(
            oidc_token_auth_method="tls_client_auth",
            oidc_client_cert_path=str(cert),
            oidc_client_key_path=str(key),
            oidc_client_cert_san_dns="another.example.gov",
        )


def test_gate_san_all_kinds_match(settings_module, tmp_path):
    """四类 SAN（DNS/URI/IP/EMAIL）全部命中 → 正常构造."""
    cert, key = _write_san_certificate(
        tmp_path,
        dns=["gateway.example.gov"],
        uri=["spiffe://example.gov/openbase"],
        ips=["127.0.0.1"],
        emails=["ops@example.gov"],
    )
    s = settings_module.Settings(
        oidc_token_auth_method="mtls",
        oidc_client_cert_path=str(cert),
        oidc_client_key_path=str(key),
        oidc_client_cert_san_dns="gateway.example.gov",
        oidc_client_cert_san_uri="spiffe://example.gov/openbase",
        oidc_client_cert_san_ip="127.0.0.1",
        oidc_client_cert_san_email="OPS@example.gov",
    )
    assert s.oidc_client_cert_san_email == "OPS@example.gov"


def test_gate_san_ip_mismatch_rejects(settings_module, tmp_path):
    """IP SAN 不匹配 → 拒绝启动."""
    cert, key = _write_san_certificate(tmp_path, ips=["127.0.0.1"])
    with pytest.raises(ValueError, match="OPENBASE_OIDC_CLIENT_CERT_SAN_IP"):
        settings_module.Settings(
            oidc_token_auth_method="tls_client_auth",
            oidc_client_cert_path=str(cert),
            oidc_client_key_path=str(key),
            oidc_client_cert_san_ip="127.0.0.2",
        )


def test_gate_san_expected_but_certificate_has_none(settings_module, tmp_path):
    """证书无 SAN 扩展但配置了期望 SAN → 拒绝启动."""
    cert, key = _write_san_certificate(tmp_path)
    with pytest.raises(ValueError, match="OPENBASE_OIDC_CLIENT_CERT_SAN_DNS"):
        settings_module.Settings(
            oidc_token_auth_method="tls_client_auth",
            oidc_client_cert_path=str(cert),
            oidc_client_key_path=str(key),
            oidc_client_cert_san_dns="gateway.example.gov",
        )


def test_gate_san_unset_skips_precheck(settings_module, tmp_path):
    """SAN 全留空 → 跳过预检（IdP 侧仍为准，零行为变化）."""
    cert, key = _write_san_certificate(tmp_path, dns=["gateway.example.gov"])
    s = settings_module.Settings(
        oidc_token_auth_method="tls_client_auth",
        oidc_client_cert_path=str(cert),
        oidc_client_key_path=str(key),
    )
    assert s.oidc_client_cert_san_dns == ""


# ---------------------------------------------------------------------------
# C-02：断言算法与私钥类型
# ---------------------------------------------------------------------------


def _write_rsa_key(tmp_path, name="rsa.key"):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path = tmp_path / name
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return path


def _write_ec_key(tmp_path, curve, name="ec.key"):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(curve)
    path = tmp_path / name
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return path, key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def test_gate_assertion_algorithm_defaults_to_rs256(settings_module, tmp_path):
    """默认断言算法为 RS256，RSA 私钥通过门禁."""
    key_path = _write_rsa_key(tmp_path)
    s = settings_module.Settings(
        oidc_token_auth_method="private_key_jwt",
        oidc_client_private_key_path=str(key_path),
    )
    assert s.oidc_client_assertion_algorithm == "RS256"


def test_gate_assertion_algorithm_rejects_unknown(settings_module, tmp_path):
    """未接线断言算法（HS256）→ 拒绝启动."""
    key_path = _write_rsa_key(tmp_path)
    with pytest.raises(ValueError, match="OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM"):
        settings_module.Settings(
            oidc_token_auth_method="private_key_jwt",
            oidc_client_private_key_path=str(key_path),
            oidc_client_assertion_algorithm="HS256",
        )


def test_gate_assertion_algorithm_rs256_requires_rsa_key(settings_module, tmp_path):
    """RS256 配 EC 私钥 → 拒绝启动（私钥类型不匹配）."""
    from cryptography.hazmat.primitives.asymmetric import ec

    key_path, _public = _write_ec_key(tmp_path, ec.SECP256R1())
    with pytest.raises(ValueError, match="需要 RSA 私钥"):
        settings_module.Settings(
            oidc_token_auth_method="private_key_jwt",
            oidc_client_private_key_path=str(key_path),
        )


def test_gate_assertion_algorithm_es256_requires_ec_key(settings_module, tmp_path):
    """ES256 配 RSA 私钥 → 拒绝启动（私钥类型不匹配）."""
    key_path = _write_rsa_key(tmp_path)
    with pytest.raises(ValueError, match="需要 EC 私钥"):
        settings_module.Settings(
            oidc_token_auth_method="private_key_jwt",
            oidc_client_private_key_path=str(key_path),
            oidc_client_assertion_algorithm="ES256",
        )


def test_gate_assertion_algorithm_es256_accepts_ec_key(settings_module, tmp_path):
    """ES256 + P-256 EC 私钥 → 正常构造，算法归一为大写."""
    from cryptography.hazmat.primitives.asymmetric import ec

    key_path, _public = _write_ec_key(tmp_path, ec.SECP256R1())
    s = settings_module.Settings(
        oidc_token_auth_method="private_key_jwt",
        oidc_client_private_key_path=str(key_path),
        oidc_client_assertion_algorithm=" es256 ",
    )
    assert s.oidc_client_assertion_algorithm == "ES256"


def test_gate_assertion_algorithm_es384_rejects_wrong_curve(settings_module, tmp_path):
    """ES384 + P-256 曲线 → 拒绝启动（曲线不匹配）."""
    from cryptography.hazmat.primitives.asymmetric import ec

    key_path, _public = _write_ec_key(tmp_path, ec.SECP256R1())
    with pytest.raises(ValueError, match="SECP384R1"):
        settings_module.Settings(
            oidc_token_auth_method="private_key_jwt",
            oidc_client_private_key_path=str(key_path),
            oidc_client_assertion_algorithm="ES384",
        )


def test_gate_assertion_algorithm_rejects_unparsable_key(settings_module, tmp_path):
    """断言私钥非 PEM → 拒绝启动."""
    key_path = tmp_path / "bad.key"
    key_path.write_text("not-a-private-key")
    with pytest.raises(ValueError, match="无法解析"):
        settings_module.Settings(
            oidc_token_auth_method="private_key_jwt",
            oidc_client_private_key_path=str(key_path),
        )


def test_build_client_assertion_uses_es256(settings_module, tmp_path):
    """运行时断言按配置算法签名（ES256 header/claims 可被 EC 公钥验证）."""
    from cryptography.hazmat.primitives.asymmetric import ec

    key_path, public_pem = _write_ec_key(tmp_path, ec.SECP256R1())
    s = settings_module.Settings(
        oidc_client_id="ec-client",
        oidc_client_secret="ec-secret",
        oidc_redirect_uri="http://unit/callback",
        oidc_token_auth_method="private_key_jwt",
        oidc_client_private_key_path=str(key_path),
        oidc_client_assertion_algorithm="ES256",
    )
    client = OIDCClient(settings=s)
    client._token_endpoint = "http://unit/token"
    payload = client.token_payload("code-1")
    header = jose_jwt.get_unverified_header(payload["client_assertion"])
    assert header["alg"] == "ES256"
    claims = jose_jwt.decode(
        payload["client_assertion"],
        public_pem,
        algorithms=["ES256"],
        options={"verify_aud": False},
    )
    assert claims["iss"] == "ec-client"
    assert claims["aud"] == "http://unit/token"


# ---------------------------------------------------------------------------
# C-05：Provider 级配置
# ---------------------------------------------------------------------------


_BASE_PROVIDER = {
    "name": "p1",
    "discovery_url": "http://127.0.0.1:9015/.well-known/openid-configuration",
    "client_id": "p1-client",
}


def test_provider_parses_optional_overrides():
    """Provider 声明 pkce/算法/认证方式 → 解析并归一."""
    raw = json.dumps(
        [
            {
                **_BASE_PROVIDER,
                "pkce_enabled": False,
                "signing_algorithms": "rs256, es256",
                "token_auth_method": "MTLS",
            }
        ]
    )
    provider = parse_idp_providers(raw)[0]
    assert provider.pkce_enabled is False
    assert provider.signing_algorithms == "RS256,ES256"
    assert provider.token_auth_method == "mtls"


def test_provider_rejects_invalid_token_auth_method():
    """Provider 认证方式非法 → ValueError."""
    raw = json.dumps([{**_BASE_PROVIDER, "token_auth_method": "client_secret_jwt"}])
    with pytest.raises(ValueError, match="token_auth_method"):
        parse_idp_providers(raw)


def test_provider_rejects_invalid_signing_algorithm():
    """Provider 签名算法含未接线项 → ValueError."""
    raw = json.dumps([{**_BASE_PROVIDER, "signing_algorithms": "SM2"}])
    with pytest.raises(ValueError, match="signing_algorithms"):
        parse_idp_providers(raw)


def test_provider_rejects_non_boolean_pkce():
    """Provider pkce_enabled 非布尔 → ValueError."""
    raw = json.dumps([{**_BASE_PROVIDER, "pkce_enabled": "yes"}])
    with pytest.raises(ValueError, match="pkce_enabled"):
        parse_idp_providers(raw)


def _provider(**overrides) -> IdpProviderConfig:
    return IdpProviderConfig(
        name="p1",
        discovery_url="http://unit/.well-known/openid-configuration",
        client_id="p1-client",
        **overrides,
    )


def test_client_uses_provider_overrides(settings_module):
    """Provider 声明优先于全局（PKCE/算法/认证方式）."""
    s = settings_module.Settings(
        oidc_pkce_enabled=False,
        oidc_signing_algorithms="RS256",
        oidc_token_auth_method="client_secret_post",
    )
    client = OIDCClient(
        settings=s,
        provider=_provider(
            pkce_enabled=True,
            signing_algorithms="ES256",
            token_auth_method="client_secret_basic",
        ),
    )
    assert client.pkce_enabled is True
    assert client.signing_algorithms == "ES256"
    assert client.token_auth_method() == "client_secret_basic"


def test_client_falls_back_to_global_when_provider_unset(settings_module):
    """Provider 未声明 → 回落全局值（零行为变化）."""
    s = settings_module.Settings(
        oidc_pkce_enabled=True,
        oidc_signing_algorithms="RS384",
        oidc_token_auth_method="client_secret_post",
    )
    client = OIDCClient(settings=s, provider=_provider())
    assert client.pkce_enabled is True
    assert client.signing_algorithms == "RS384"
    assert client.token_auth_method() == "client_secret_post"


def test_provider_changes_rebuild_client_cache(settings_module, backchannel_idp):
    """Provider 声明变更 → 客户端缓存按 dataclass 等值失效重建."""
    from openbase.modules.auth import oidc as oidc_module

    providers = json.dumps([{**_BASE_PROVIDER, "profile": "generic"}])
    s = _settings_for(settings_module, backchannel_idp, idp_providers=providers)
    first = oidc_module._get_provider_client("p1")
    second = oidc_module._get_provider_client("p1")
    assert first is second
    s.idp_providers = json.dumps(
        [{**_BASE_PROVIDER, "profile": "generic", "pkce_enabled": False}]
    )
    rebuilt = oidc_module._get_provider_client("p1")
    assert rebuilt is not first
    assert rebuilt.pkce_enabled is False


def test_authorize_provider_pkce_disabled_omits_challenge(settings_module, backchannel_idp):
    """Provider 关闭 PKCE → 授权 URL 不带 code_challenge（全局仍为开启）."""
    providers = json.dumps([{**_BASE_PROVIDER, "pkce_enabled": False}])
    s = _settings_for(settings_module, backchannel_idp, idp_providers=providers)
    client = TestClient(init_app(s))
    resp = client.get("/api/v1/auth/oidc/authorize", params={"provider": "p1"})
    assert resp.status_code == 200, resp.text
    assert "code_challenge=" not in resp.json()["authorize_url"]


# ---------------------------------------------------------------------------
# C-03：id_token_hint 保存与登出透传
# ---------------------------------------------------------------------------


def test_logout_store_roundtrip_and_issuer_check():
    """hint 存取：issuer 不匹配不返回；sid 索引可解析主体；clear 后清空."""
    store = OidcLogoutStore(ttl_seconds=60)
    store.save_id_token_hint(
        client_id="c1",
        subject="u1",
        issuer="https://idp.example",
        id_token="hint-token",
        sid="sid-1",
        ttl_seconds=60,
    )
    assert store.id_token_hint(client_id="c1", subject="u1", issuer="https://idp.example")
    assert store.id_token_hint(client_id="c1", subject="u1", issuer="https://other") == ""
    assert store.subject_for_sid(client_id="c1", sid="sid-1") == "u1"
    store.clear(client_id="c1", subject="u1", sid="sid-1")
    assert store.id_token_hint(client_id="c1", subject="u1") == ""
    assert store.subject_for_sid(client_id="c1", sid="sid-1") == ""


def test_logout_store_expires_local_entries(monkeypatch):
    """进程内条目按 TTL 过期（ttl=0 立即失效）."""
    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    store = OidcLogoutStore(ttl_seconds=0)
    store.save_id_token_hint(
        client_id="c1", subject="u1", issuer="i1", id_token="t1", ttl_seconds=0
    )
    assert store.id_token_hint(client_id="c1", subject="u1") == ""
    assert store.consume_jti(client_id="c1", jti="j-expired", ttl_seconds=0) is True


def test_logout_store_jti_consumed_once(monkeypatch):
    """jti 一次性消费：首次 True，重放 False."""
    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    store = OidcLogoutStore()
    assert store.consume_jti(client_id="c1", jti="j1", ttl_seconds=60) is True
    assert store.consume_jti(client_id="c1", jti="j1", ttl_seconds=60) is False


def test_callback_persists_hint_and_logout_passes_it(
    settings_module, backchannel_idp, logout_store
):
    """登录写 hint → 登出 URL 透传 id_token_hint，且登出后 hint 一次性清除."""
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    auth = client.get("/api/v1/auth/oidc/authorize").json()
    nonce = _authorize_nonce(auth["authorize_url"])
    resp = client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": f"mock-code.{nonce}", "state": auth["state"]},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()

    hint = logout_store.id_token_hint(
        client_id=backchannel_idp.client_id,
        subject="p1-user",
        issuer=backchannel_idp.issuer,
    )
    assert hint

    logout = client.post(
        "/api/v1/auth/oidc/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout.status_code == 200, logout.text
    from urllib.parse import parse_qs, urlparse

    params = parse_qs(urlparse(logout.json()["idp_logout_url"]).query)
    assert params["id_token_hint"][0] == hint
    assert (
        logout_store.id_token_hint(
            client_id=backchannel_idp.client_id,
            subject="p1-user",
            issuer=backchannel_idp.issuer,
        )
        == ""
    )


# ---------------------------------------------------------------------------
# C-04：back-channel logout
# ---------------------------------------------------------------------------


BACKCHANNEL_PATH = "/api/v1/auth/oidc/backchannel-logout"


def _logout_token(idp: MockIdp, **overrides) -> str:
    """构造 RFC 8471 logout token（RS256 签名）."""
    now = int(time.time())
    claims = {
        "iss": idp.issuer,
        "aud": idp.client_id,
        "iat": now,
        "exp": now + 300,
        "jti": f"jti-{now}-{idp.client_id}",
        "sub": idp.sub,
        "events": {BACKCHANNEL_LOGOUT_EVENT: {}},
    }
    claims.update(overrides)
    for key in [key for key, value in overrides.items() if value is None]:
        claims.pop(key, None)
    return jose_jwt.encode(
        claims, idp._pem, algorithm="RS256", headers={"alg": "RS256", "kid": idp.kid}
    )


def test_backchannel_logout_accepts_valid_token(
    settings_module, backchannel_idp, logout_store
):
    """有效 logout token → 200（DB 不可达时 revoked=false）."""
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    token = _logout_token(backchannel_idp)
    resp = client.post(BACKCHANNEL_PATH, data={"logout_token": token})
    assert resp.status_code == 200, resp.text
    assert resp.json()["revoked"] is False


def test_backchannel_logout_accepts_json_body(
    settings_module, backchannel_idp, logout_store
):
    """application/json 载荷同样可接收."""
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    resp = client.post(BACKCHANNEL_PATH, json={"logout_token": _logout_token(backchannel_idp)})
    assert resp.status_code == 200, resp.text


def test_backchannel_logout_rejects_replay(settings_module, backchannel_idp, logout_store):
    """同一 jti 二次提交 → 400（一次性消费）."""
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    token = _logout_token(backchannel_idp, jti="replay-jti")
    assert client.post(BACKCHANNEL_PATH, data={"logout_token": token}).status_code == 200
    replay = client.post(BACKCHANNEL_PATH, data={"logout_token": token})
    assert replay.status_code == 400, replay.text
    assert replay.json()["code"] == "PARAM_INVALID"


@pytest.mark.parametrize(
    "overrides, expected_message",
    [
        ({"events": None}, "backchannel logout event"),
        ({"nonce": "forbidden-nonce"}, "nonce"),
        ({"jti": None}, "jti"),
        ({"sub": None, "sid": None}, "sub or sid"),
    ],
)
def test_backchannel_logout_rejects_invalid_claims(
    settings_module, backchannel_idp, logout_store, overrides, expected_message
):
    """events/nonce/jti/sub|sid 校验失败 → 400."""
    s = _settings_for(settings_module, backchannel_idp, idp_providers="")
    client = TestClient(init_app(s))
    token_kwargs = {"jti": f"claim-{expected_message}"}
    token_kwargs.update(overrides)
    token = _logout_token(backchannel_idp, **token_kwargs)
    resp = client.post(BACKCHANNEL_PATH, data={"logout_token": token})
    assert resp.status_code == 400, resp.text
    assert expected_message in resp.json()["message"]


def test_backchannel_logout_rejects_missing_token(settings_module, backchannel_idp):
    """缺少 logout_token → 400."""
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    resp = client.post(BACKCHANNEL_PATH, data={})
    assert resp.status_code == 400, resp.text


def test_backchannel_logout_rejects_bad_signature(settings_module, backchannel_idp, logout_store):
    """非 IdP 私钥签名的 token → 400."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    now = int(time.time())
    foreign_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    foreign_pem = foreign_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = jose_jwt.encode(
        {
            "iss": backchannel_idp.issuer,
            "aud": backchannel_idp.client_id,
            "iat": now,
            "exp": now + 300,
            "jti": "bad-signature-jti",
            "sub": backchannel_idp.sub,
            "events": {BACKCHANNEL_LOGOUT_EVENT: {}},
        },
        foreign_pem,
        algorithm="RS256",
        headers={"alg": "RS256", "kid": backchannel_idp.kid},
    )
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    resp = client.post(BACKCHANNEL_PATH, data={"logout_token": token})
    assert resp.status_code == 400, resp.text


def test_backchannel_logout_404_when_idp_does_not_support(
    settings_module, no_backchannel_idp, logout_store
):
    """IdP 未声明 back-channel logout → 404."""
    s = _settings_for(settings_module, no_backchannel_idp)
    client = TestClient(init_app(s))
    resp = client.post(
        BACKCHANNEL_PATH, data={"logout_token": _logout_token(no_backchannel_idp)}
    )
    assert resp.status_code == 404, resp.text
    # ErrorCode.BIZ_NOT_FOUND 的线上值即 "BIZ_404"（见 core/errors/codes.py）
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value


def test_backchannel_logout_404_for_unknown_issuer(
    settings_module, backchannel_idp, logout_store
):
    """issuer/aud 不匹配任何已登记客户端 → 404."""
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    token = _logout_token(backchannel_idp, iss="https://unknown-idp.example")
    resp = client.post(BACKCHANNEL_PATH, data={"logout_token": token})
    assert resp.status_code == 404, resp.text


def test_backchannel_logout_resolves_subject_from_sid(
    settings_module, backchannel_idp, logout_store
):
    """仅携带 sid 的 token：经 sid 索引定位主体（DB 不可达 → revoked=false）."""
    logout_store.save_id_token_hint(
        client_id=backchannel_idp.client_id,
        subject="7",
        issuer=backchannel_idp.issuer,
        id_token="hint",
        sid="session-1",
        ttl_seconds=300,
    )
    s = _settings_for(settings_module, backchannel_idp)
    client = TestClient(init_app(s))
    token = _logout_token(backchannel_idp, sub=None, sid="session-1")
    resp = client.post(BACKCHANNEL_PATH, data={"logout_token": token})
    assert resp.status_code == 200, resp.text
    assert resp.json()["revoked"] is False


def test_backchannel_logout_provider_registration_path(
    settings_module, backchannel_idp, logout_store
):
    """单 IdP 未启用时按已登记 Provider 解析客户端（覆盖多 Provider 分支）."""
    providers = json.dumps([_BASE_PROVIDER])
    s = _settings_for(
        settings_module,
        backchannel_idp,
        oidc_discovery_url="",
        oidc_client_id="",
        idp_providers=providers,
    )
    client = TestClient(init_app(s))
    resp = client.post(
        BACKCHANNEL_PATH, data={"logout_token": _logout_token(backchannel_idp)}
    )
    assert resp.status_code == 200, resp.text
