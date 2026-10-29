"""MCP 边缘服务凭证适配层（E1 §10.3-3）.

三种接入形态收敛到同一份 :class:`MCPCredential`，供 HTTP 路由与 stdio 宿主共用：

- **静态 Key**：``settings.mcp_api_keys``（联调/过渡形态，生产禁止内置默认值）；
- **服务 Key**：``ob_k_*``（``X-API-Key`` 或 ``Authorization: Bearer``），按
  ``scope.system`` 含 ``mcp`` 校验，按 ``scope.tools`` 做工具级过滤；
- **短期 JWT**：``Authorization: Bearer`` 或 stdio 宿主注入的
  ``OPENBASE_MCP_TOKEN``/``OPENBASE_MCP_TOKEN_FILE``，校验 ``type=access`` 与
  ``exp``（``decode_any_token`` 内完成），按 claims ``scope.tools`` 过滤。

设计取舍：工具级白名单缺省为「不限定」（``tools=None``），只有显式声明
``scope.tools`` 才收窄；通配 ``*`` 表示全量。凭证缺失/无效一律 fail-closed 401，
不提供匿名兜底。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from openbase.core.errors import BaseError, ErrorCode

# JWT/服务 Key 中工具白名单所在的键名（scope.tools；同时兼容顶层 tools claim）
_MCP_TOOL_SCOPE_KEY = "tools"
# 服务 Key 校验的系统维度（scope.system 必须含 "mcp" 或 "*"）
MCP_SYSTEM_NAME = "mcp"
# stdio 宿主注入短期令牌的两种方式（文件优先，避免令牌进进程参数/日志）
STDIO_TOKEN_ENV = "OPENBASE_MCP_TOKEN"
STDIO_TOKEN_FILE_ENV = "OPENBASE_MCP_TOKEN_FILE"

CREDENTIAL_TYPE_STATIC = "static-key"
CREDENTIAL_TYPE_SERVICE_KEY = "service-key"
CREDENTIAL_TYPE_JWT = "jwt"
CREDENTIAL_TYPE_STDIO = "stdio-token"


@dataclass(frozen=True, slots=True)
class MCPCredential:
    """MCP 调用凭证（已校验通过）.

    Attributes:
        subject: 主体标识（服务 Key → key_id；JWT → ``sub``；静态 Key → ``static``）。
        credential_type: 凭证形态（static-key/service-key/jwt/stdio-token）。
        tenant_code: 归属租户（可空）。
        tools: 允许的工具名集合；``None`` 表示不限定。
    """

    subject: str
    credential_type: str
    tenant_code: str | None = None
    tools: tuple[str, ...] | None = None


def _extract_tools(scope: Any, claims: dict[str, Any]) -> tuple[str, ...] | None:
    """从 scope/claims 提取工具白名单（缺省 None = 不限定）."""
    candidate: Any = None
    if isinstance(scope, dict):
        candidate = scope.get(_MCP_TOOL_SCOPE_KEY)
    if candidate is None:
        candidate = claims.get(_MCP_TOOL_SCOPE_KEY)
    if isinstance(candidate, str):
        candidate = [item.strip() for item in candidate.split(",") if item.strip()]
    if not isinstance(candidate, (list, tuple, set)):
        return None
    names = tuple(str(item).strip() for item in candidate if str(item).strip())
    return names or None


def allows_tool(credential: MCPCredential, tool_name: str) -> bool:
    """工具级判定：``None`` 不限定；``*`` 通配；否则精确命中."""
    if credential.tools is None:
        return True
    return "*" in credential.tools or tool_name in credential.tools


def filter_tools(credential: MCPCredential, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按凭证工具白名单过滤 ``tools/list`` 结果."""
    if credential.tools is None:
        return tools
    return [tool for tool in tools if allows_tool(credential, str(tool.get("name", "")))]


def _unauthorized(reason: str) -> BaseError:
    """统一的 401 构造（detail 只带原因码，不回显凭证内容）."""
    return BaseError(ErrorCode.AUTH_UNAUTHORIZED, "invalid mcp credential", detail={"reason": reason})


async def _lookup_service_key(raw_key: str) -> dict[str, Any] | None:
    """按明文服务 Key 查库（独立函数便于测试替换，不泄漏 Key 到日志）."""
    from openbase.core.db.session import get_session_factory
    from openbase.modules.auth.service_keys import ServiceKeyService

    factory = get_session_factory()
    async with factory() as session:
        return await ServiceKeyService.lookup(session, raw_key)


async def _service_key_credential(raw_key: str, tenant_code: str | None) -> MCPCredential:
    """服务 Key → 凭证（校验系统维度 scope，工具白名单来自 scope.tools）."""
    from openbase.modules.auth.service_keys import scope_allows

    credential = await _lookup_service_key(raw_key)
    if credential is None:
        raise _unauthorized("service_key_invalid")
    scope = credential.get("scope") or {}
    if not scope_allows(scope, MCP_SYSTEM_NAME, tenant_code):
        raise BaseError(ErrorCode.PERM_API_KEY_SCOPE, "api key scope mismatch")
    return MCPCredential(
        subject=str(credential.get("id") or ""),
        credential_type=CREDENTIAL_TYPE_SERVICE_KEY,
        tenant_code=tenant_code,
        tools=_extract_tools(scope, credential),
    )


def _jwt_credential(token: str, credential_type: str) -> MCPCredential:
    """短期 JWT → 凭证（验签/exp/类型由 ``decode_any_token`` 完成）."""
    from openbase.modules.auth.jwt import decode_any_token

    payload = decode_any_token(token)
    if payload is None or payload.get("type") != "access":
        raise _unauthorized("token_invalid_or_expired")
    subject = str(payload.get("sub") or "")
    if not subject:
        raise _unauthorized("token_missing_subject")
    return MCPCredential(
        subject=subject,
        credential_type=credential_type,
        tenant_code=payload.get("tenant_code"),
        tools=_extract_tools(payload.get("scope"), payload),
    )


def _static_keys() -> list[str]:
    """读取静态 MCP Key 清单（逗号分隔）."""
    from openbase.settings import get_settings

    return [item.strip() for item in get_settings().mcp_api_keys.split(",") if item.strip()]


async def require_mcp_credential(request: Request) -> MCPCredential:
    """FastAPI 依赖：解析并校验 MCP 调用凭证（fail-closed）.

    解析顺序：静态 Key（``X-API-Key``）→ ``Authorization: Bearer`` 的
    ``ob_k_*``（服务 Key）/ 其他（JWT）。缺凭证或全部不匹配 → 401。

    Raises:
        BaseError: AUTH_UNAUTHORIZED（缺/无效凭证）；PERM_API_KEY_SCOPE（服务 Key 越权）。
    """
    from openbase.core.deps.auth import get_current_tenant

    provided = request.headers.get("X-API-Key", "")
    static_keys = _static_keys()
    if provided and static_keys and provided in static_keys:
        return MCPCredential(
            subject="static",
            credential_type=CREDENTIAL_TYPE_STATIC,
            tenant_code=request.headers.get("X-Tenant-Id"),
        )

    authorization = request.headers.get("Authorization", "")
    bearer = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    candidate = provided or bearer
    if not candidate:
        raise _unauthorized("missing_credential")

    tenant_code = await get_current_tenant(request)
    if candidate.startswith("ob_k_"):
        return await _service_key_credential(candidate, tenant_code)
    return _jwt_credential(candidate, CREDENTIAL_TYPE_JWT)


def _read_stdio_token() -> str:
    """读取 stdio 宿主注入的令牌（文件优先；内容不落日志）."""
    file_path = os.getenv(STDIO_TOKEN_FILE_ENV, "").strip()
    if file_path:
        try:
            with open(file_path, encoding="utf-8") as handle:
                return handle.read().strip()
        except OSError as exc:
            raise _unauthorized("stdio_token_file_unreadable") from exc
    return os.getenv(STDIO_TOKEN_ENV, "").strip()


def resolve_stdio_credential(token: str | None = None) -> MCPCredential:
    """stdio 模式凭证解析（启动时一次，宿主注入短期令牌）.

    语义（§10.3 MCP 边缘服务）：stdio 视为本地可信传输，但**仍必须**校验令牌
    的签名/``exp``/``aud``；禁止无限期或匿名凭证。令牌缺失/过期一律拒绝启动。

    Args:
        token: 显式令牌（测试用）；缺省从 ``OPENBASE_MCP_TOKEN_FILE`` /
            ``OPENBASE_MCP_TOKEN`` 读取。

    Raises:
        BaseError: AUTH_UNAUTHORIZED —— 令牌缺失、文件不可读或校验失败。
    """
    raw = (token or "").strip() or _read_stdio_token()
    if not raw:
        raise _unauthorized("stdio_token_missing")
    return _jwt_credential(raw, CREDENTIAL_TYPE_STDIO)
