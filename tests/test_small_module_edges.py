"""小模块覆盖率边角补测（覆盖率治理 v1.4.0）.

覆盖 token_api / idp_registry / jwt / access_control / derivation /
abac_policy_store 中难以经 HTTP 触发的防御性分支与配置解析异常。
"""

import importlib
from types import SimpleNamespace

import pytest

import openbase.modules.auth.jwt as jwt_module
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth.abac_policy_store import validate_policy_payload
from openbase.modules.auth.access_control import (
    DEFAULT_ABAC_EVALUATION_WARN_MS,
    DEFAULT_ABAC_RULE_SOFT_LIMIT,
    _abac_baseline_thresholds,
    _rule_from_object,
)
from openbase.modules.auth.idp_registry import (
    _normalized_signing_algorithms,
    _provider_from_object,
    parse_idp_providers,
)
from openbase.modules.auth.token_api import _require_token_scope
from openbase.modules.logs.derivation import (
    _derive_operation_from_action,
    module_path_prefixes,
)

settings_module = importlib.import_module("openbase.settings")


def _jwt_settings(**overrides):
    defaults = {
        "jwt_expire_seconds": 900,
        "refresh_expire_seconds": 604800,
        "jwt_require_rs256": False,
        "jwt_issuer": "",
        "jwt_audience": "",
        "jwt_jwks_public_keys": "",
        "jwt_rsa_private_key_path": "",
        "jwt_signing_kid": "",
        "jwt_algorithm": "HS256",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_token_api_scope_guard_rejects_mismatch() -> None:
    """内省/吊销面 scope 不含 auth → PERM_API_KEY_SCOPE."""
    with pytest.raises(BaseError) as exc_info:
        _require_token_scope({"scope": {"system": ["openrag"]}})
    assert exc_info.value.code == ErrorCode.PERM_API_KEY_SCOPE
    _require_token_scope({"scope": {"system": ["*"]}})


def test_idp_provider_parsing_edges() -> None:
    """算法去重/空项、非对象条目、非法 JSON、顶层非数组 → ValueError."""
    assert _normalized_signing_algorithms("p", "RS256, ,RS256") == "RS256"
    with pytest.raises(ValueError):
        _provider_from_object([], 1)
    with pytest.raises(ValueError):
        parse_idp_providers("{")
    with pytest.raises(ValueError):
        parse_idp_providers('{"a": 1}')
    assert parse_idp_providers("") == ()


def test_jwt_encode_rs256_claim_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    """RS256 通道注入 iss/aud 与 kid 头；issuer/audience 缺省时不注入."""
    captured: dict = {}

    def _fake_encode(payload, key, algorithm, headers=None):
        captured.update(payload=payload, key=key, algorithm=algorithm, headers=headers)
        return "signed"

    monkeypatch.setattr(jwt_module, "_signing_material", lambda: ("kid-1", "PEM"))
    monkeypatch.setattr(jwt_module.jwt, "encode", _fake_encode)
    monkeypatch.setattr(
        jwt_module,
        "get_settings",
        lambda: _jwt_settings(jwt_issuer="issuer-1", jwt_audience="aud-1"),
    )
    assert jwt_module._encode({"sub": "1"}) == "signed"
    assert captured["payload"]["iss"] == "issuer-1"
    assert captured["payload"]["aud"] == "aud-1"
    assert captured["headers"] == {"kid": "kid-1"}

    # issuer / audience 缺省 → 不注入（走 false 分支）
    monkeypatch.setattr(jwt_module, "get_settings", _jwt_settings)
    assert jwt_module._encode({"sub": "1"}) == "signed"
    assert "iss" not in captured["payload"]
    assert "aud" not in captured["payload"]


def test_jwt_decode_audience_and_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """aud 数组命中判定；RS256 解码异常 → None."""
    assert jwt_module._audience_matches(["a", "b"], "b") is True
    assert jwt_module._audience_matches("b", "c") is False

    def _raise(*args, **kwargs):
        raise jwt_module.JWTError("bad token")

    monkeypatch.setattr(jwt_module, "public_pem_for_kid", lambda *a, **k: "PEM")
    monkeypatch.setattr(jwt_module.jwt, "decode", _raise)
    monkeypatch.setattr(jwt_module, "get_settings", _jwt_settings)
    assert jwt_module._decode_rs256("tampered", "kid-1") is None


def test_jwt_token_factory_optional_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """subject_type 缺省不写 sub_type；token_version=0 写 tvn；extra 透传两 Token."""
    monkeypatch.setattr(jwt_module, "get_settings", _jwt_settings)
    monkeypatch.setattr(jwt_module, "_encode", lambda claims: claims)

    access = jwt_module.create_access_token("1", subject_type=None, token_version=0)
    assert "sub_type" not in access
    assert access["tvn"] == 0

    refresh = jwt_module.create_refresh_token("1", subject_type=None)
    assert "sub_type" not in refresh
    assert refresh["type"] == "refresh"

    access, refresh = jwt_module.issue_token_pair(
        subject="1", username="alice", role="admin", extra={"foo": "bar"}
    )
    assert access["foo"] == "bar"
    assert access["role"] == "admin"
    assert refresh["role"] == "admin"


def test_access_control_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    """ABAC 规则非对象 → ValueError；阈值读取异常回退模块默认值."""
    with pytest.raises(ValueError):
        _rule_from_object([], 1)

    def _broken_settings():
        raise RuntimeError("settings unavailable")

    monkeypatch.setattr(settings_module, "get_settings", _broken_settings)
    assert _abac_baseline_thresholds() == (
        DEFAULT_ABAC_RULE_SOFT_LIMIT,
        DEFAULT_ABAC_EVALUATION_WARN_MS,
    )


def test_abac_policy_payload_invalid_effect() -> None:
    """策略 payload effect 非 allow/deny → PARAM_INVALID."""
    with pytest.raises(BaseError) as exc_info:
        validate_policy_payload({"effect": "nope"})
    assert exc_info.value.code == ErrorCode.PARAM_INVALID


def test_log_derivation_action_edges() -> None:
    """无路径前缀规则返回空元组；动作语义兜底 delete / proxy."""
    assert module_path_prefixes("other") == ()
    assert _derive_operation_from_action("user.delete") == "delete"
    assert _derive_operation_from_action("proxy.outbound") == "proxy"
    assert _derive_operation_from_action("identity.purge") == "config"
    assert _derive_operation_from_action("user.login") == "read"
