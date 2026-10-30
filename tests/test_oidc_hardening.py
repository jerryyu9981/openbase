"""OIDC P1 安全硬化单测（v1.14.0）.

覆盖：
- state 一次性消费 / TTL（多实例 Redis 降级为进程内）
- PKCE S256 challenge（RFC 7636 向量）
- nonce 校验（缺失/不匹配 → AUTH_401_INVALID）
- ID Token 算法白名单与 discovery 取交集（无交集失败）
- 启动门禁（TTL 非正 / 未接线算法拒绝）
- 端点错误码统一为 {code,message,detail,request_id}
"""

from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openbase import init_app
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth import oidc as oidc_module
from openbase.modules.auth import oidc_state as oidc_state_module
from openbase.modules.auth.oidc import (
    OIDCError,
    code_challenge_for,
    resolve_id_token_algorithms,
    verify_id_token_nonce,
)


@pytest.fixture(autouse=True)
def _no_redis(monkeypatch):
    """强制 Redis 不可用（走进程内回退路径，保证测试不依赖外部服务）."""
    monkeypatch.setattr(oidc_state_module.redis_client, "get_client", lambda: None)
    oidc_state_module.get_state_store().clear()
    yield
    oidc_state_module.get_state_store().clear()


# ---------------------------------------------------------------------------
# state 存储：一次性消费 + TTL
# ---------------------------------------------------------------------------


def test_state_store_consumed_once():
    store = oidc_state_module.OidcStateStore(ttl_seconds=600)
    store.issue("state-1", {"nonce": "n-1", "code_verifier": "v-1"})
    assert store.consume("state-1") == {"nonce": "n-1", "code_verifier": "v-1"}
    assert store.consume("state-1") is None


def test_state_store_expiry(monkeypatch):
    store = oidc_state_module.OidcStateStore(ttl_seconds=10)
    monkeypatch.setattr(oidc_state_module, "_now", lambda: 100.0)
    store.issue("state-2", {"nonce": "n-2"})
    monkeypatch.setattr(oidc_state_module, "_now", lambda: 111.0)
    assert store.consume("state-2") is None


# ---------------------------------------------------------------------------
# PKCE / nonce / 算法
# ---------------------------------------------------------------------------


def test_code_challenge_matches_rfc7636_vector():
    """RFC 7636 附录 B 标准向量."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge_for(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_nonce_mismatch_raises_auth_invalid():
    with pytest.raises(BaseError) as exc_info:
        verify_id_token_nonce("expected-nonce", {"nonce": "other-nonce"})
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_INVALID

    with pytest.raises(BaseError):
        verify_id_token_nonce("expected-nonce", {})


def test_nonce_match_passes():
    verify_id_token_nonce("same-nonce", {"nonce": "same-nonce"})


def test_algorithms_intersect_with_discovery():
    configured = ["RS256", "ES256"]
    assert resolve_id_token_algorithms(configured, {"id_token_signing_alg_values_supported": ["ES256"]}) == ["ES256"]
    # discovery 未声明 → 以仓内可用算法全集为口径
    assert resolve_id_token_algorithms(configured, {}) == configured


def test_algorithms_without_intersection_fails():
    with pytest.raises(OIDCError):
        resolve_id_token_algorithms(["RS256"], {"id_token_signing_alg_values_supported": ["HS256"]})


# ---------------------------------------------------------------------------
# 启动门禁
# ---------------------------------------------------------------------------


def test_settings_rejects_non_positive_state_ttl():
    from openbase.settings import Settings

    with pytest.raises(ValidationError):
        Settings(oidc_state_ttl_seconds=0)


def test_settings_rejects_unwired_signing_algorithm():
    from openbase.settings import Settings

    with pytest.raises(ValidationError):
        Settings(oidc_signing_algorithms="SM2")


def test_settings_accepts_wired_signing_algorithms():
    from openbase.settings import Settings

    settings = Settings(oidc_signing_algorithms="RS256,ES256")
    assert settings.oidc_signing_algorithms == "RS256,ES256"


# ---------------------------------------------------------------------------
# 端点错误码（统一契约）
# ---------------------------------------------------------------------------


@pytest.fixture()
def disabled_oidc_client():
    settings_module = sys.modules["openbase.settings"]
    settings_module._settings = None
    oidc_module._oidc_client = None
    settings = settings_module.Settings()
    settings.enable_module("auth")
    settings.oidc_enabled = False
    settings_module._settings = settings
    yield TestClient(init_app(settings))
    settings_module._settings = None
    oidc_module._oidc_client = None


def test_oidc_disabled_error_contract(disabled_oidc_client):
    resp = disabled_oidc_client.get("/api/v1/auth/oidc/authorize")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == ErrorCode.BIZ_NOT_FOUND.value
    assert set(body) == {"code", "message", "detail", "request_id"}


def test_oidc_callback_invalid_state_error_contract(disabled_oidc_client):
    resp = disabled_oidc_client.get(
        "/api/v1/auth/oidc/callback?code=any-code&state=unknown-state"
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == ErrorCode.PARAM_INVALID.value
    assert set(body) == {"code", "message", "detail", "request_id"}
