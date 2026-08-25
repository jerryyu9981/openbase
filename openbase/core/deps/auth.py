"""通用依赖注入：get_db / get_current_user / get_current_tenant."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.errors import BaseError, ErrorCode

__all__ = ["get_db", "get_current_user", "get_current_tenant"]


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
