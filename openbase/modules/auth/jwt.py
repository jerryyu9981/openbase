"""JWT 签发/验证工具."""

from __future__ import annotations

import datetime as dt
from typing import Any

from jose import JWTError, jwt

from openbase.settings import get_settings


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def create_access_token(
    subject: str,
    username: str = "",
    tenant_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """签发访问 Token（默认有效期 2h）.

    Args:
        subject: 用户 ID（字符串）。
        username: 用户名（冗余进 payload 减少查询）。
        tenant_id: 租户编码（可选）。
        extra: 附加声明。

    Returns:
        JWT 字符串。
    """
    settings = get_settings()
    now = _now()
    claims: dict[str, Any] = {
        "sub": subject,
        "username": username,
        "iat": now,
        "exp": now + dt.timedelta(seconds=settings.jwt_expire_seconds),
        "type": "access",
    }
    if tenant_id:
        claims["tenant_id"] = tenant_id
    if extra:
        claims.update(extra)
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, tenant_id: str | None = None) -> str:
    """签发刷新 Token（默认有效期 7d）.

    Returns:
        JWT 字符串（type=refresh）。
    """
    settings = get_settings()
    now = _now()
    claims: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + dt.timedelta(seconds=settings.refresh_expire_seconds),
        "type": "refresh",
    }
    if tenant_id:
        claims["tenant_id"] = tenant_id
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """解码并校验访问 Token.

    Args:
        token: JWT 字符串。

    Returns:
        payload；无效/过期/类型错误返回 None。
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """解码并校验刷新 Token.

    Returns:
        payload；无效/过期/类型错误返回 None。
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
    if payload.get("type") != "refresh":
        return None
    return payload
