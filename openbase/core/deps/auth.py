"""通用依赖注入：get_db / get_current_user / get_current_tenant / AuthMiddleware."""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from openbase.core.db.session import get_db
from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.auth")

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_tenant",
    "AuthMiddleware",
]


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
    return {
        "id": int(user_id),
        "username": payload.get("username", ""),
        "tenant_id": payload.get("tenant_id"),
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
