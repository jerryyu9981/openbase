"""R1：登录期租户策略契约（2026-10-17）.

背景：``openbase.users.tenant_id`` 为空时 JWT 不带 ``org_id``，导致 llm-proxy
出站缺 ``X-Tenant-ID``，下游按保留码 ``default`` 处理（跨域 404/403）。

本组用例锁定四条不变量：
1. 已绑定租户 → 原值透传，不触发兜底；
2. 未绑定 + 显式默认租户 → 兜底生效并标注原因；
3. 未绑定 + 生产 + 强制开关 → 拒绝登录（AUTH_FORBIDDEN / tenant_unbound）；
4. 未绑定 + 非生产 + 强制开关 → 不阻断，仅标注 unbound（保护联调）。
"""

from __future__ import annotations

import pytest

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth import apply_login_tenant_policy


class TestLoginTenantPolicy:
    def test_bound_tenant_passthrough(self) -> None:
        code, reason = apply_login_tenant_policy("tenant-1")
        assert code == "tenant-1"
        assert reason is None

    def test_default_tenant_fallback(self) -> None:
        code, reason = apply_login_tenant_policy(
            None, default_tenant_code="tenant-1", is_production=True
        )
        assert code == "tenant-1"
        assert reason == "default_config"

    def test_production_requires_tenant(self) -> None:
        with pytest.raises(BaseError) as excinfo:
            apply_login_tenant_policy(
                None, require_tenant_on_login=True, is_production=True
            )
        assert excinfo.value.code == ErrorCode.AUTH_FORBIDDEN
        assert excinfo.value.detail == {"reason": "tenant_unbound"}

    def test_non_production_does_not_block(self) -> None:
        code, reason = apply_login_tenant_policy(
            None, require_tenant_on_login=True, is_production=False
        )
        assert code is None
        assert reason == "unbound"

    def test_unbound_without_switch_stays_none(self) -> None:
        code, reason = apply_login_tenant_policy(None)
        assert code is None
        assert reason == "unbound"
