"""auth 模块：鉴权认证（JWT + RBAC + 登录/刷新 + 数据库用户）.

来源：OpenLLM app/services/auth_service.py（数据库用户校验模式）+ edgerouter/auth
（JWT/RBAC），适配 openbase core/db 与会话管理。
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import User
from openbase.modules.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from openbase.settings import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---- Schemas ----


class LoginRequest(BaseModel):
    """登录请求."""

    username: str
    password: str


class RefreshRequest(BaseModel):
    """刷新 Token 请求."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Token 响应."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    refresh_expires_in: int


class MeResponse(BaseModel):
    """当前用户信息响应."""

    id: int
    username: str
    tenant_id: str | None = None
    permissions: list[str] = []


# ---- 密码校验 ----


def _password_ctx():
    """构建 bcrypt 密码上下文（rounds 从 settings 读取，模块级复用）."""
    from passlib.context import CryptContext

    from openbase.settings import get_settings

    ctx = getattr(_password_ctx, "_ctx", None)
    rounds = get_settings().bcrypt_rounds
    if ctx is None or getattr(_password_ctx, "_rounds", None) != rounds:
        ctx = CryptContext(
            schemes=["bcrypt"], deprecated="auto",
            bcrypt__rounds=rounds,
        )
        _password_ctx._ctx = ctx  # type: ignore[attr-defined]
        _password_ctx._rounds = rounds  # type: ignore[attr-defined]
    return ctx


def hash_password(plain: str) -> str:
    """生成 bcrypt 密码哈希（rounds 配置化，默认 12）."""
    return _password_ctx().hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码（bcrypt）.

    Args:
        plain: 明文密码。
        hashed: bcrypt 哈希。

    Returns:
        是否匹配。
    """
    try:
        return _password_ctx().verify(plain, hashed)
    except ValueError:
        return False


# ---- 用户服务（数据库优先 + 内存降级） ----


class UserService:
    """用户存储服务：数据库 users 表 + 内存降级.

    来源：OpenLLM app/services/auth_service.py（用户校验模式抽取）。
    """

    # 内存降级存储（数据库不可用时）
    _memory_users: dict[str, dict] = {}

    @classmethod
    def seed_memory_user(cls, username: str, password: str) -> None:
        """内存降级用户（演示/离线场景）."""
        cls._memory_users[username] = {
            "id": 1,
            "username": username,
            "password_hash": hash_password(password),
            "tenant_id": None,
        }

    @classmethod
    async def get_by_username(
        cls, username: str, session: AsyncSession
    ) -> dict | None:
        """按用户名查询用户（数据库优先，失败回退内存）.

        Args:
            username: 用户名。
            session: 数据库会话。

        Returns:
            用户字典；不存在返回 None。
        """
        # Redis 用户缓存（TTL 300s，对齐设计文档"用户缓存 Redis TTL 5min"）
        from openbase.core.cache.redis_client import cache_get

        cached = cache_get(f"user:{username}")
        if cached is not None:
            return cached
        try:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if user is not None:
                data = {
                    "id": user.id,
                    "username": user.username,
                    "password_hash": user.password_hash,
                    "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                }
                from openbase.core.cache.redis_client import cache_set

                cache_set(f"user:{username}", data, ttl=300)
                return data
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("openbase.auth").warning(
                "user query failed, fallback to memory: %s", exc
            )
        return cls._memory_users.get(username)


# ---- 路由 ----


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """账号密码登录（数据库用户校验）.

    校验通过后签发 access/refresh Token。
    数据库不可用时回退内存演示用户（UserService.seed_memory_user）。
    """
    settings = get_settings()

    user = await UserService.get_by_username(req.username, session)
    if user is None or user.get("password_hash") is None:
        raise BaseError(ErrorCode.AUTH_UNAUTHORIZED, "invalid username or password")

    if not await asyncio.to_thread(verify_password, req.password, user["password_hash"]):
        raise BaseError(ErrorCode.AUTH_UNAUTHORIZED, "invalid username or password")

    access = create_access_token(
        str(user["id"]), username=user["username"], tenant_id=user.get("tenant_id")
    )
    refresh = create_refresh_token(str(user["id"]), user.get("tenant_id"))
    return TokenResponse(
        access_token=access,
        expires_in=settings.jwt_expire_seconds,
        refresh_token=refresh,
        refresh_expires_in=settings.refresh_expire_seconds,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest) -> TokenResponse:
    """刷新 Token：校验 refresh token 后签发新 access/refresh. """
    settings = get_settings()
    payload = decode_refresh_token(req.refresh_token)
    if payload is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "invalid refresh token")

    subject = payload.get("sub")
    if subject is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "refresh token missing subject")

    access = create_access_token(
        subject, username=payload.get("username", ""), tenant_id=payload.get("tenant_id")
    )
    new_refresh = create_refresh_token(subject, payload.get("tenant_id"))
    return TokenResponse(
        access_token=access,
        expires_in=settings.jwt_expire_seconds,
        refresh_token=new_refresh,
        refresh_expires_in=settings.refresh_expire_seconds,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MeResponse:
    """当前用户信息（含权限标识）.

    供统一前端登录后拉取用户与权限（v1.2.0 统一前端契约）。
    """
    from openbase.modules.auth.rbac import PermissionService

    permissions = await PermissionService.permissions_for_with_fallback(session, str(user["id"]))
    # 系统管理员（admin）兜底通配权限：数据库 RBAC 关联未就绪时保证全模块可见
    if user.get("username") == "admin" and "*" not in permissions:
        permissions = ["*", *permissions]
    return MeResponse(
        id=user["id"],
        username=user["username"],
        tenant_id=user.get("tenant_id"),
        permissions=permissions,
    )

__version__ = "1.1.0"
