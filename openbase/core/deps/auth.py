"""通用依赖注入：get_db / get_current_user / get_current_tenant / AuthMiddleware."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from openbase.core.db.session import get_db
from openbase.core.errors import BaseError, ErrorCode

if TYPE_CHECKING:
    from openbase.modules.auth.api_keys import ApiKeyStore

logger = logging.getLogger("openbase.auth")

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_tenant",
    "get_identity_context",
    "require_api_key",
    "get_proxy_identity",
    "AuthMiddleware",
]

# 服务 Key 存储全局单例（v1.4.1 R-367）
# 延迟导入 ApiKeyStore：打破 deps.auth ↔ modules.auth 循环导入（TD-新增-009 相关）
_api_key_store: ApiKeyStore | None = None


def get_api_key_store() -> ApiKeyStore:
    """获取全局 ApiKeyStore 单例."""
    global _api_key_store
    if _api_key_store is None:
        from openbase.modules.auth.api_keys import ApiKeyStore

        _api_key_store = ApiKeyStore()
    return _api_key_store


class AuthMiddleware(BaseHTTPMiddleware):
    """统一鉴权中间件：管理接口必须携带有效 JWT（SR-001）.

    白名单路径（公开）：/health、/audit/health、/docs、/openapi.json、
    /redoc、/api/v1/auth/login、/api/v1/auth/refresh、/observability/status。
    其余路径均要求 Authorization: Bearer <token>，无效时返回统一 401 错误格式。
    """

    PUBLIC_PREFIXES = (
        "/health",
        "/audit/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/observability/status",
        # MCP：服务发现公开；工具调用由 MCP 层 API Key 鉴权（豁免 JWT）
        "/mcp/server/info",
        "/mcp/tools",
        # v1.4.1 R-367 AC-367-2：/proxy 通道由端点层做 JWT 优先 + 服务 Key 回退双通道认证
        "/api/v1/proxy",
    )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        if path.startswith(self.PUBLIC_PREFIXES):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return self._unauthorized("missing bearer token")

        from openbase.modules.auth.jwt import decode_access_token

        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        if payload is None or payload.get("sub") is None:
            return self._unauthorized("invalid or expired token")

        # 中间件不修改用户上下文（依赖层负责用户信息），此处仅做门禁
        return await call_next(request)

    @staticmethod
    def _unauthorized(message: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "code": ErrorCode.AUTH_UNAUTHORIZED.value,
                "message": message,
                "detail": None,
                "request_id": f"req-{uuid.uuid4().hex[:12]}",
            },
        )


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI 依赖：解析当前登录用户.

    从请求头 Authorization: Bearer <token> 解析 JWT，加载用户信息。
    未认证或 Token 无效时抛出 AUTH_401。

    Returns:
        dict: 当前用户信息（id/username/tenant_id 等）。
    """
    from openbase.modules.auth.jwt import decode_access_token

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise BaseError(ErrorCode.AUTH_UNAUTHORIZED, "missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if payload is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "token missing subject")

    # 用户信息以 payload 中精简字段返回，详细查询由 auth 模块服务提供
    # permissions 透传（含 "*" 通配），供 require_permission 直接校验
    return {
        "id": int(user_id),
        "username": payload.get("username", ""),
        "tenant_id": payload.get("tenant_id"),
        "permissions": payload.get("permissions") or [],
    }


async def get_current_tenant(request: Request) -> str | None:
    """FastAPI 依赖：解析当前租户上下文.

    优先取请求头 X-Tenant-Id，其次取 JWT payload 中 tenant_id。

    Returns:
        租户编码（Schema 名）；未指定返回 None。
    """
    header = request.headers.get("X-Tenant-Id")
    if header:
        return header

    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        from openbase.modules.auth.jwt import decode_access_token

        payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
        if payload and payload.get("tenant_id"):
            return str(payload["tenant_id"])
    return None


# ---- v1.4.1 四维身份上下文（R-369，对齐完整方案 2.9/2.11） ----

@dataclass
class IdentityContext:
    """四维身份上下文：用户/租户/团队/智能体.

    Attributes:
        user_id: 用户 ID（X-User-Id 或 JWT sub）。
        tenant_id: 租户（X-Tenant-Id）。
        team_id: 团队（X-Team-Id，可选）。
        agent_id: 智能体（X-Agent-Id，可选）。
    """

    user_id: int | None = None
    tenant_id: str | None = None
    team_id: str | None = None
    agent_id: str | None = None


def get_identity_context(request: Request) -> IdentityContext:
    """解析四维身份上下文（从请求头，缺省返回 None 字段不抛异常）.

    优先级：请求头 > JWT payload（user_id/tenant_id）。
    """
    user_id = request.headers.get("X-User-Id")
    tenant_id = request.headers.get("X-Tenant-Id")
    team_id = request.headers.get("X-Team-Id")
    agent_id = request.headers.get("X-Agent-Id")

    # JWT 回退（user_id/tenant_id）
    authorization = request.headers.get("Authorization", "")
    if user_id is None and authorization.startswith("Bearer "):
        try:
            from openbase.modules.auth.jwt import decode_access_token

            payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
            if payload and payload.get("sub"):
                user_id = str(payload["sub"])
        except Exception:  # noqa: BLE001
            pass
    if tenant_id is None and authorization.startswith("Bearer "):
        try:
            from openbase.modules.auth.jwt import decode_access_token

            payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
            if payload and payload.get("tenant_id"):
                tenant_id = str(payload["tenant_id"])
        except Exception:  # noqa: BLE001
            pass

    return IdentityContext(
        user_id=int(user_id) if user_id and user_id.isdigit() else None,
        tenant_id=tenant_id,
        team_id=team_id,
        agent_id=agent_id,
    )


# ---- v1.4.1 服务级 API Key 认证（R-367/368，对齐完整方案 2.5/2.7） ----

def require_api_key(
    x_api_key: str | None = None,
    request: Request | None = None,
    store: ApiKeyStore | None = None,
) -> dict:
    """服务级 API Key 认证（网关 /proxy 双通道：JWT 优先 + Key 回退）.

    从 X-API-Key 头或 Authorization: Bearer <key> 提取 Key；
    校验有效性 + scope（system 从请求路径提取）。

    Args:
        x_api_key: 显式传入的 Key（测试用）。
        request: FastAPI 请求（提取 X-API-Key 头与路径 system）。
        store: ApiKeyStore 实例（缺省全局单例）。

    Returns:
        通过返回凭据 dict（name/scope）。

    Raises:
        BaseError: Key 无效 → AUTH_API_KEY_INVALID(401)；越 scope → PERM_API_KEY_SCOPE(403)。
    """
    key = x_api_key or (request.headers.get("X-API-Key") if request else None)
    if not key and request is not None:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            candidate = authorization.removeprefix("Bearer ").strip()
            if not candidate.startswith("jwt."):
                key = candidate  # 非 JWT 前缀视为服务 Key

    if not key:
        raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "missing api key")

    store_instance = store or get_api_key_store()
    # 从路径提取 system（/api/v1/proxy/{system}/...）
    system: str | None = None
    if request is not None:
        path = request.url.path
        parts = path.split("/")
        if len(parts) >= 5 and parts[1] == "api" and parts[3] == "proxy":
            system = parts[4]

    credential = store_instance.verify(key, system=system)
    if credential is None:
        if system is not None and store_instance.verify(key) is None:
            raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "invalid api key")
        # Key 有效但 scope 不匹配
        if store_instance.verify(key) is not None:
            raise BaseError(ErrorCode.PERM_API_KEY_SCOPE, "api key scope mismatch")
        raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "invalid api key")
    return credential


async def get_proxy_identity(request: Request) -> dict:
    """/proxy 通道双通道认证（R-367 AC-367-2）：JWT 优先 + 服务 Key 回退.

    认证通道判定：
    - X-API-Key 头存在 → 服务 Key 认证（校验路径 system scope）。
    - Authorization: Bearer <ob_k_...> → 服务 Key 认证。
    - 其余（Bearer JWT / 无头）→ JWT 用户认证（get_current_user）。
    """
    x_api_key = request.headers.get("X-API-Key")
    authorization = request.headers.get("Authorization", "")
    bearer = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    if x_api_key or (bearer and bearer.startswith("ob_k_")):
        return require_api_key(request=request)
    return await get_current_user(request)
