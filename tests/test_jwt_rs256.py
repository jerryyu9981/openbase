"""E1-5A 非对称签名单测（RS256 签发/验签、JWKS 发布、双验签过渡、配置门禁）."""

import base64
import json
import sys
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt
from pydantic import ValidationError

from openbase.core.security.jwt_keys import clear_key_cache, public_pem_for_kid
from openbase.modules.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    jwks_document,
)

STRONG = "x9kQ2vR8pLmN4cJ6tWzY3uEaFhG1sBd0iK5nM7qPrS"
PREVIOUS = "v8pQ2aR4sT6uW8yZ0cE3gI5kM7oQ9sU1wY4"
KID = "ob-2026a"

_KEY_DIR = Path(tempfile.mkdtemp(prefix="openbase-jwt-rs256-"))


def _generate_key_pair(name: str) -> tuple[Path, Path]:
    """生成 RSA 密钥对并写 PEM 文件，返回 (私钥路径, 公钥路径)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path = _KEY_DIR / f"{name}-private.pem"
    public_path = _KEY_DIR / f"{name}-public.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


PRIVATE_PATH, PUBLIC_PATH = _generate_key_pair("current")
OLD_PRIVATE_PATH, OLD_PUBLIC_PATH = _generate_key_pair("previous")


def _settings_module():
    # openbase/__init__.py 将包属性 settings 覆盖为实例；须经 sys.modules 取真模块
    return sys.modules["openbase.settings"]


@pytest.fixture(autouse=True)
def _reset_settings():
    """每个用例重置 settings 单例与密钥缓存，避免跨用例污染."""
    clear_key_cache()
    _settings_module()._settings = None
    yield
    clear_key_cache()
    _settings_module()._settings = None


def _configure(**overrides) -> object:
    """构造并注入带 RS256 配置的 settings 单例（默认启用非对称签发）."""
    values: dict[str, object] = {
        "env": "development",
        "jwt_secret": STRONG,
        "jwt_rsa_private_key_path": str(PRIVATE_PATH),
        "jwt_signing_kid": KID,
    }
    values.update(overrides)
    settings = _settings_module().Settings(**values)
    _settings_module()._settings = settings
    return settings


def _enable_hs256_only() -> object:
    settings = _settings_module().Settings(env="development", jwt_secret=STRONG)
    _settings_module()._settings = settings
    return settings


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# RS256 签发 / 验签
# ---------------------------------------------------------------------------


def test_rs256_signing_carries_kid_and_standard_claims() -> None:
    """新签发 token：alg=RS256 + kid 头 + iss/aud claim."""
    _configure()
    token = create_access_token("42", username="alice")
    header = jose_jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"
    assert header["kid"] == KID
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["iss"] == "openbase"
    assert payload["aud"] == "openbase-api"


def test_rs256_roundtrip_access_and_refresh_types() -> None:
    _configure()
    access = create_access_token("7")
    refresh = create_refresh_token("7")
    assert decode_access_token(access) is not None
    assert decode_access_token(refresh) is None
    assert decode_refresh_token(refresh) is not None
    assert decode_refresh_token(access) is None


def test_rs256_rejects_unknown_kid() -> None:
    """未登记 kid → 拒绝（fail-closed，不回退其它公钥）."""
    _configure()
    token = jose_jwt.encode(
        {"sub": "1", "type": "access", "iss": "openbase", "aud": "openbase-api"},
        PRIVATE_PATH.read_text(encoding="utf-8"),
        algorithm="RS256",
        headers={"kid": "unknown-kid"},
    )
    assert decode_access_token(token) is None


def test_rs256_rejects_wrong_audience_and_issuer() -> None:
    _configure()
    private_pem = PRIVATE_PATH.read_text(encoding="utf-8")
    wrong_audience = jose_jwt.encode(
        {"sub": "1", "type": "access", "iss": "openbase", "aud": "other-api"},
        private_pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    wrong_issuer = jose_jwt.encode(
        {"sub": "1", "type": "access", "iss": "attacker", "aud": "openbase-api"},
        private_pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    missing_issuer = jose_jwt.encode(
        {"sub": "1", "type": "access", "aud": "openbase-api"},
        private_pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    assert decode_access_token(wrong_audience) is None
    assert decode_access_token(wrong_issuer) is None
    assert decode_access_token(missing_issuer) is None


def test_hs256_token_cannot_pass_as_rs256() -> None:
    """算法混淆防护：alg=none 一律拒绝."""
    _configure()
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    body = _b64url(json.dumps({"sub": "1", "type": "access"}).encode("utf-8"))
    assert decode_access_token(f"{header}.{body}.") is None


# ---------------------------------------------------------------------------
# 双验签过渡（存量 HS256）
# ---------------------------------------------------------------------------


def test_legacy_hs256_token_still_verifies_during_transition() -> None:
    _configure()
    legacy = jose_jwt.encode({"sub": "5", "type": "access"}, STRONG, algorithm="HS256")
    payload = decode_access_token(legacy)
    assert payload is not None and payload["sub"] == "5"


def test_legacy_hs256_previous_secret_grace() -> None:
    _configure(jwt_secret_previous=PREVIOUS)
    legacy = jose_jwt.encode(
        {"sub": "6", "type": "access"}, PREVIOUS, algorithm="HS256"
    )
    payload = decode_access_token(legacy)
    assert payload is not None and payload["sub"] == "6"


# ---------------------------------------------------------------------------
# JWKS 发布
# ---------------------------------------------------------------------------


def test_jwks_document_exposes_public_material_only() -> None:
    _configure()
    document = jwks_document()
    assert len(document["keys"]) == 1
    entry = document["keys"][0]
    assert entry["kid"] == KID
    assert entry["kty"] == "RSA"
    assert entry["alg"] == "RS256"
    assert entry["use"] == "sig"
    assert entry["n"] and entry["e"]
    # 绝不输出私钥分量
    for private_field in ("d", "p", "q", "dp", "dq", "qi"):
        assert private_field not in entry


def test_jwks_empty_without_rs256_configuration() -> None:
    _enable_hs256_only()
    assert jwks_document() == {"keys": []}


def test_extra_public_key_registered_and_verifiable() -> None:
    """双验签期：JWKS 登记历史 kid 公钥后，其签名可验签."""
    extra_map = json.dumps(
        {"ob-2025z": OLD_PUBLIC_PATH.read_text(encoding="utf-8")}
    )
    _configure(jwt_jwks_public_keys=extra_map)
    kids = {entry["kid"] for entry in jwks_document()["keys"]}
    assert kids == {KID, "ob-2025z"}

    historical_token = jose_jwt.encode(
        {"sub": "8", "type": "access", "iss": "openbase", "aud": "openbase-api"},
        OLD_PRIVATE_PATH.read_text(encoding="utf-8"),
        algorithm="RS256",
        headers={"kid": "ob-2025z"},
    )
    payload = decode_access_token(historical_token)
    assert payload is not None and payload["sub"] == "8"


def test_public_pem_for_kid_single_key_fallback() -> None:
    _configure()
    assert public_pem_for_kid(None, private_key_path=str(PRIVATE_PATH), signing_kid=KID)
    assert (
        public_pem_for_kid(
            "unknown-kid", private_key_path=str(PRIVATE_PATH), signing_kid=KID
        )
        is None
    )


# ---------------------------------------------------------------------------
# 配置门禁（fail-fast）
# ---------------------------------------------------------------------------


def test_require_rs256_without_key_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings_module().Settings(
            env="production",
            jwt_secret=STRONG,
            enforce_token_version=True,
            jwt_require_rs256=True,
        )


def test_private_key_without_kid_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings_module().Settings(
            env="development",
            jwt_secret=STRONG,
            jwt_rsa_private_key_path=str(PRIVATE_PATH),
        )


def test_missing_private_key_file_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings_module().Settings(
            env="development",
            jwt_secret=STRONG,
            jwt_rsa_private_key_path=str(_KEY_DIR / "absent.pem"),
            jwt_signing_kid=KID,
        )


def test_invalid_extra_public_keys_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings_module().Settings(
            env="development",
            jwt_secret=STRONG,
            jwt_jwks_public_keys="{not-json",
        )


def test_revocations_page_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _settings_module().Settings(
            env="development", jwt_secret=STRONG, jwt_revocations_page_limit=0
        )


def test_require_rs256_satisfied_starts() -> None:
    settings = _settings_module().Settings(
        env="development",
        jwt_secret=STRONG,
        jwt_require_rs256=True,
        jwt_rsa_private_key_path=str(PRIVATE_PATH),
        jwt_signing_kid=KID,
    )
    assert settings.jwt_signing_kid == KID
