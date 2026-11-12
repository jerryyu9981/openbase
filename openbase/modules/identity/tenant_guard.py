"""入口租户守卫（R5 入口强制，方案 §7.7）.

认证通过后统一校验主体是否携带租户，覆盖 JWT / ``sk-agent`` / 服务 Key / MCP
四条入站通道，以及 agent 主体创建入口：

- ``off``：不校验、不计数（非生产默认）；
- ``shadow``：缺失时计数 + 结构化 WARN，放行；
- ``enforce``：缺失时计数 + WARN，抛 403 ``AUTH_FORBIDDEN``
  （``detail.reason=tenant_unbound``，与登录拒签一致）。

模式由 ``settings.entry_tenant_enforce`` 解析（默认 ``auto``：production →
``enforce``，其余 → ``off``）。守卫只读取认证结果中的租户，不采信客户端头，
避免"客户端头覆盖令牌"成为提权路径。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from typing import Any

from fastapi import Request

from openbase.core.errors import BaseError, ErrorCode
from openbase.settings import get_settings, resolve_entry_tenant_enforce_mode

logger = logging.getLogger("openbase.identity.tenant_guard")

ENTRY_TENANT_MODE_OFF = "off"
ENTRY_TENANT_MODE_SHADOW = "shadow"
ENTRY_TENANT_MODE_ENFORCE = "enforce"

# 认证方式 → 守卫通道标识（用于计数与日志分组）
_CHANNEL_BY_AUTH_METHOD: dict[str, str] = {
    "jwt": "jwt",
    "sk-agent": "sk-agent",
    "service-key": "service-key",
    "static-key": "mcp",
    "stdio-token": "mcp",
}

_COUNTER_LOCK = threading.Lock()
_missing_tenant_total = 0


def entry_tenant_mode() -> str:
    """解析当前生效的入口租户守卫模式（off/shadow/enforce）."""
    settings = get_settings()
    return resolve_entry_tenant_enforce_mode(settings.entry_tenant_enforce, settings.env)


def missing_tenant_total() -> int:
    """返回进程内累计的"认证通过但无租户"次数（供 shadow 观察）."""
    with _COUNTER_LOCK:
        return _missing_tenant_total


def reset_missing_tenant_total() -> None:
    """重置缺失计数（仅测试使用）."""
    global _missing_tenant_total
    with _COUNTER_LOCK:
        _missing_tenant_total = 0


def _principal_field(principal: Any, name: str) -> Any:
    """读取主体字段（兼容 Mapping 与属性式对象，如 ``MCPCredential``）."""
    if isinstance(principal, Mapping):
        return principal.get(name)
    return getattr(principal, name, None)


def _tenant_of(principal: Any) -> str:
    """解析主体有效租户（``tenant_code`` 优先，其次 ``tenant_id``）."""
    value = _principal_field(principal, "tenant_code") or _principal_field(
        principal, "tenant_id"
    )
    return str(value or "").strip()


def _channel_of(principal: Any, channel: str | None) -> str:
    """解析守卫通道标识（显式传入优先，否则按认证方式推导）."""
    if channel:
        return channel
    auth_method = str(_principal_field(principal, "auth_method") or "").strip()
    if auth_method in _CHANNEL_BY_AUTH_METHOD:
        return _CHANNEL_BY_AUTH_METHOD[auth_method]
    credential_type = str(_principal_field(principal, "credential_type") or "").strip()
    return _CHANNEL_BY_AUTH_METHOD.get(credential_type, "unknown")


def _bump_missing() -> int:
    """累加缺失计数并返回最新值."""
    global _missing_tenant_total
    with _COUNTER_LOCK:
        _missing_tenant_total += 1
        return _missing_tenant_total


def _record_missing(channel: str, request: Request) -> None:
    """缺失租户计数 + 结构化 WARN（不记录任何凭证信息）."""
    total = _bump_missing()
    logger.warning(
        "tenant unbound",
        extra={
            "channel": channel,
            "missing_total": total,
            "method": getattr(request, "method", None),
            "path": getattr(getattr(request, "url", None), "path", None),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def ensure_tenant_bound(
    principal: Any, request: Request, *, channel: str | None = None
) -> None:
    """认证后统一租户守卫；``shadow`` 只计数，``enforce`` 抛 403.

    Args:
        principal: 认证结果（dict 或 ``MCPCredential`` 等属性式对象）。
        request: 当前请求（用于结构化日志）。
        channel: 通道标识覆盖值（``jwt``/``sk-agent``/``service-key``/``mcp``）。

    Raises:
        BaseError: ``enforce`` 且主体无租户 → 403
            ``AUTH_FORBIDDEN``（``detail.reason=tenant_unbound``）。
    """
    mode = entry_tenant_mode()
    if mode == ENTRY_TENANT_MODE_OFF:
        return
    if _tenant_of(principal):
        return
    resolved_channel = _channel_of(principal, channel)
    _record_missing(resolved_channel, request)
    if mode == ENTRY_TENANT_MODE_SHADOW:
        return
    raise BaseError(
        ErrorCode.AUTH_FORBIDDEN,
        "tenant identity required",
        detail={"reason": "tenant_unbound"},
    )


def ensure_agent_tenant_bound(
    tenant_id: int | None, *, operator_tenant_id: int | None = None
) -> int | None:
    """创建 agent 前解析并校验归属租户（G2 源头治理，三态生效）.

    Args:
        tenant_id: 请求显式指定的归属租户 id。
        operator_tenant_id: 操作者自身租户 id（请求未指定时回退）。

    Returns:
        解析后的租户 id；``off``/``shadow`` 下无任何来源时返回 ``None``。

    Raises:
        BaseError: ``enforce`` 且无任何租户来源 → 400 ``PARAM_INVALID``
            （``detail.reason=tenant_unbound``）。
    """
    resolved = tenant_id if tenant_id is not None else operator_tenant_id
    if resolved is not None:
        return resolved
    mode = entry_tenant_mode()
    if mode == ENTRY_TENANT_MODE_OFF:
        return None
    total = _bump_missing()
    logger.warning(
        "tenant unbound",
        extra={"channel": "agent-create", "missing_total": total},
    )
    if mode == ENTRY_TENANT_MODE_SHADOW:
        return None
    raise BaseError(
        ErrorCode.PARAM_INVALID,
        "tenant_id is required to create agent",
        detail={"reason": "tenant_unbound"},
    )
