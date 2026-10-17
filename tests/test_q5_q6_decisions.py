"""Q5 / Q6 裁定落地测试（2026-10-17）.

Q5：生产必须强制登录租户绑定（`require_tenant_on_login=true` 且无显式兜底租户），
    由 `validate_production_login_tenant_policy` 在应用装配期拒绝启动。
Q6：`X-Subject-ID` 纳入受信身份头强校验集合 —— 非白名单来源携带即按既有策略
    判定（enforce=true → 403；过渡期 → 标注忽略）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from openbase.modules.protocol_headers import (
    HEADER_PROXY_SOURCE,
    HEADER_SUBJECT_ID,
    IDENTITY_HEADER_LENGTH_LIMITS,
    INBOUND_IDENTITY_HEADERS,
    InboundClassification,
    classify_inbound,
    inbound_identity_headers_present,
    validate_header_value,
)
from openbase.core.errors import BaseError
from openbase.settings import Settings, validate_production_login_tenant_policy

_STRONG_SECRET = "q5-" + "x" * 40


def _prod_settings(**overrides) -> Settings:
    base = {
        "env": "production",
        "jwt_secret": _STRONG_SECRET,
        "enforce_token_version": True,
    }
    base.update(overrides)
    return Settings(**base)


class TestQ5ProductionTenantGate:
    def test_development_is_not_restricted(self):
        settings = Settings(env="development", require_tenant_on_login=False)
        validate_production_login_tenant_policy(settings)  # 不抛错

    def test_production_requires_tenant_binding(self):
        settings = _prod_settings(require_tenant_on_login=False)
        with pytest.raises(RuntimeError) as exc_info:
            validate_production_login_tenant_policy(settings)
        assert "OPENBASE_REQUIRE_TENANT_ON_LOGIN" in str(exc_info.value)

    def test_production_forbids_explicit_default_tenant(self):
        settings = _prod_settings(
            require_tenant_on_login=True, default_tenant_code="tenant-1"
        )
        with pytest.raises(RuntimeError) as exc_info:
            validate_production_login_tenant_policy(settings)
        assert "OPENBASE_DEFAULT_TENANT_CODE" in str(exc_info.value)

    def test_production_passes_with_strict_policy(self):
        settings = _prod_settings(require_tenant_on_login=True, default_tenant_code="")
        validate_production_login_tenant_policy(settings)  # 不抛错


class TestQ6SubjectHeaderStrongVerify:
    def test_subject_header_in_inbound_identity_set(self):
        assert HEADER_SUBJECT_ID == "X-Subject-ID"
        assert HEADER_SUBJECT_ID in INBOUND_IDENTITY_HEADERS
        assert IDENTITY_HEADER_LENGTH_LIMITS[HEADER_SUBJECT_ID] == 128
        assert validate_header_value(HEADER_SUBJECT_ID, "tenant-1_1") == "tenant-1_1"

    def test_subject_header_length_limit(self):
        with pytest.raises(BaseError):
            validate_header_value(HEADER_SUBJECT_ID, "x" * 129)

    def test_untrusted_source_with_only_subject_header_is_detected(self):
        request = SimpleNamespace(headers={HEADER_SUBJECT_ID: "tenant-1_1"})
        assert inbound_identity_headers_present(request) is True
        assert (
            classify_inbound(request, trusted_sources=["openbase-llm-proxy"], enforce=True)
            == InboundClassification.FORBIDDEN
        )

    def test_untrusted_source_without_enforce_is_ignored(self):
        request = SimpleNamespace(headers={HEADER_SUBJECT_ID: "tenant-1_1"})
        assert (
            classify_inbound(
                request, trusted_sources=["openbase-llm-proxy"], enforce=False
            )
            == InboundClassification.IGNORED
        )

    def test_trusted_source_with_subject_header_is_trusted(self):
        request = SimpleNamespace(
            headers={
                HEADER_PROXY_SOURCE: "openbase-llm-proxy",
                HEADER_SUBJECT_ID: "tenant-1_1",
            }
        )
        assert (
            classify_inbound(
                request, trusted_sources=["openbase-llm-proxy"], enforce=True
            )
            == InboundClassification.TRUSTED
        )
