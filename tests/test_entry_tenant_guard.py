"""R5 入口租户守卫测试（方案 §7.7 T1–T6）.

覆盖：三态语义（off/shadow/enforce）、模式解析（auto 按环境推导）、
agent 创建租户解析（G2）、生产门禁（模式 + per-target 兜底，G5）、
MCP 静态 Key 租户来源（G4）。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.identity.tenant_guard import (
    ensure_agent_tenant_bound,
    ensure_tenant_bound,
    missing_tenant_total,
    reset_missing_tenant_total,
)
from openbase.settings import (
    Settings,
    resolve_entry_tenant_enforce_mode,
    resolve_target_code_space,
    validate_production_login_tenant_policy,
)

_STRONG_SECRET = "entry-guard-" + "x" * 40
_CLEARED_FALLBACKS = (
    '{"targets": {"rag": {"default_tenant_code": null},'
    ' "memory": {"default_tenant_code": null}}}'
)


def _request(path: str = "/api/v1/memories", method: str = "GET") -> SimpleNamespace:
    """最小请求替身（守卫只读取 method/path/request_id）."""
    return SimpleNamespace(
        method=method,
        url=SimpleNamespace(path=path),
        state=SimpleNamespace(request_id="req-test"),
        headers={},
    )


def _apply_mode(monkeypatch: pytest.MonkeyPatch, mode: str, env: str = "development") -> None:
    """把守卫读取的 Settings 替换为最小替身并重置计数."""
    monkeypatch.setattr(
        "openbase.modules.identity.tenant_guard.get_settings",
        lambda: SimpleNamespace(entry_tenant_enforce=mode, env=env),
    )
    reset_missing_tenant_total()


# ---- 模式解析 ----


@pytest.mark.parametrize(
    ("env", "expected"),
    [("production", "enforce"), ("development", "off"), ("test", "off")],
)
def test_resolve_mode_auto_follows_env(env: str, expected: str) -> None:
    """auto/空值按环境推导：production → enforce，其余 → off."""
    assert resolve_entry_tenant_enforce_mode("auto", env) == expected
    assert resolve_entry_tenant_enforce_mode("", env) == expected
    assert resolve_entry_tenant_enforce_mode(None, env) == expected


@pytest.mark.parametrize("mode", ["off", "shadow", "enforce"])
def test_resolve_mode_explicit(mode: str) -> None:
    """显式模式不受环境影响（大小写/空白归一）."""
    assert resolve_entry_tenant_enforce_mode(mode, "production") == mode
    assert resolve_entry_tenant_enforce_mode(f" {mode.upper()} ", "development") == mode


def test_resolve_mode_invalid_raises() -> None:
    """非法取值 fail-fast."""
    with pytest.raises(ValueError):
        resolve_entry_tenant_enforce_mode("block", "development")


def test_settings_rejects_invalid_mode() -> None:
    """非法模式在 Settings 装配期即拒绝."""
    with pytest.raises(ValueError):
        Settings(entry_tenant_enforce="block")


# ---- 守卫三态 ----


def test_guard_off_allows_without_counting(monkeypatch: pytest.MonkeyPatch) -> None:
    """off：空租户放行且不计数."""
    _apply_mode(monkeypatch, "off")
    asyncio.run(ensure_tenant_bound({"auth_method": "jwt"}, _request()))
    assert missing_tenant_total() == 0


def test_guard_shadow_counts_and_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    """shadow：空租户放行，计数 +1."""
    _apply_mode(monkeypatch, "shadow")
    asyncio.run(ensure_tenant_bound({"auth_method": "jwt"}, _request()))
    assert missing_tenant_total() == 1


def test_guard_enforce_raises_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """enforce：空租户 → 403 AUTH_FORBIDDEN（reason=tenant_unbound）."""
    _apply_mode(monkeypatch, "enforce")
    with pytest.raises(BaseError) as exc_info:
        asyncio.run(ensure_tenant_bound({"tenant_code": None}, _request()))
    error = exc_info.value
    assert error.code == ErrorCode.AUTH_FORBIDDEN
    assert error.status_code == 403
    assert error.detail == {"reason": "tenant_unbound"}
    assert missing_tenant_total() == 1


def test_guard_passes_bound_principal_without_counting(monkeypatch: pytest.MonkeyPatch) -> None:
    """有租户主体（dict 与 MCPCredential）不计数、不抛错."""
    from openbase.modules.mcp.credentials import MCPCredential

    _apply_mode(monkeypatch, "enforce")
    asyncio.run(ensure_tenant_bound({"tenant_code": "tenant-1"}, _request()))
    asyncio.run(
        ensure_tenant_bound(
            MCPCredential(
                subject="key-1",
                credential_type="service-key",
                tenant_code="tenant-1",
            ),
            _request(),
        )
    )
    assert missing_tenant_total() == 0


def test_guard_accepts_tenant_id_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """tenant_code 缺失但 tenant_id 存在 → 视为已绑定."""
    _apply_mode(monkeypatch, "enforce")
    asyncio.run(ensure_tenant_bound({"tenant_id": 7}, _request()))
    assert missing_tenant_total() == 0


# ---- agent 创建（G2） ----


def test_agent_creation_requires_tenant_in_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    """enforce：无任何租户来源 → 400 PARAM_INVALID."""
    _apply_mode(monkeypatch, "enforce")
    with pytest.raises(BaseError) as exc_info:
        ensure_agent_tenant_bound(None)
    error = exc_info.value
    assert error.code == ErrorCode.PARAM_INVALID
    assert error.status_code == 400
    assert error.detail == {"reason": "tenant_unbound"}


def test_agent_creation_prefers_request_then_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    """请求值优先，缺省回退操作者租户."""
    _apply_mode(monkeypatch, "enforce")
    assert ensure_agent_tenant_bound(None, operator_tenant_id=9) == 9
    assert ensure_agent_tenant_bound(3, operator_tenant_id=9) == 3
    assert missing_tenant_total() == 0


def test_agent_creation_off_allows_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """非生产 off：保持既有联调行为（返回 None）."""
    _apply_mode(monkeypatch, "off")
    assert ensure_agent_tenant_bound(None) is None


# ---- 生产门禁（G5） ----


def _prod_settings(**overrides: object) -> Settings:
    """生产 Settings 基线（满足既有 Q5 两条门禁）."""
    base: dict[str, object] = {
        "env": "production",
        "jwt_secret": _STRONG_SECRET,
        "enforce_token_version": True,
        "mcp_api_keys": "",
        "mcp_api_key_hashes": "a" * 64,
        "require_tenant_on_login": True,
        "default_tenant_code": "",
        "entry_tenant_enforce": "enforce",
        "proxy_code_map": "",
    }
    base.update(overrides)
    return Settings(**base)


def test_prod_gate_requires_enforce_mode() -> None:
    """生产入口守卫非 enforce → 拒绝启动."""
    with pytest.raises(RuntimeError, match="OPENBASE_ENTRY_TENANT_ENFORCE"):
        validate_production_login_tenant_policy(
            _prod_settings(entry_tenant_enforce="shadow")
        )


def test_prod_gate_rejects_builtin_fallback() -> None:
    """生产仍存在 per-target 兜底码 → 拒绝启动."""
    with pytest.raises(RuntimeError, match="default_tenant_code"):
        validate_production_login_tenant_policy(_prod_settings())


def test_prod_gate_passes_after_clearing_fallback() -> None:
    """清空 rag/memory 内置兜底后生产门禁通过."""
    validate_production_login_tenant_policy(
        _prod_settings(proxy_code_map=_CLEARED_FALLBACKS)
    )


def test_proxy_code_map_null_clears_builtin_fallback() -> None:
    """null 显式清除内置兜底；未覆盖目标保持基线."""
    resolved = resolve_target_code_space(
        '{"targets": {"rag": {"default_tenant_code": null}}}'
    )
    assert resolved["rag"]["default_tenant_code"] is None
    assert resolved["memory"]["default_tenant_code"] == "tenant-1"


# ---- MCP 租户来源（G4） ----


def test_mcp_static_key_ignores_untrusted_tenant_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """静态 Key 不再直接采信客户端 X-Tenant-Id（非受信来源返回 None）."""
    from openbase.core.deps import auth as auth_module
    from openbase.modules.mcp import credentials

    monkeypatch.setattr(credentials, "_match_static_key", lambda provided: "static-id")
    monkeypatch.setattr(credentials, "_static_key_tools", lambda identifier: None)

    async def _untrusted_tenant(request: object) -> None:
        return None

    monkeypatch.setattr(auth_module, "get_current_tenant", _untrusted_tenant)
    _apply_mode(monkeypatch, "off")

    request = SimpleNamespace(
        headers={"X-API-Key": "dev-key", "X-Tenant-Id": "attacker-tenant"}
    )
    credential = asyncio.run(credentials.require_mcp_credential(request))
    assert credential.tenant_code is None
