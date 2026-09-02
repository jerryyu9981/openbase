"""JWT 签发/验证工具."""

from __future__ import annotations

import datetime as dt
from typing import Any

from jose import JWTError, jwt

from openbase.settings import get_settings


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _sign_secret() -> str:
    """当前签发密钥；未配置则抛错（fail-closed，v1.7.0）. """
    secret = get_settings().jwt_secret or ""
    if len(secret) < 32:
        raise ValueError(
            "JWT 签发密钥未配置或过弱（fail-closed）：请配置 OPENBASE_JWT_SECRET"
        )
    return secret


def _verify_secrets() -> list[str]:
    """验签密钥列表：当前密钥 + 旧密钥（轮换宽限，v1.7.0）.

    轮换流程：先配置新密钥（签发切新）+ 旧密钥写入 jwt_secret_previous（验签保留），
    过渡期后移除 jwt_secret_previous 即完成零中断轮换。
    """
    settings = get_settings()
    secrets = [s for s in (settings.jwt_secret or "", settings.jwt_secret_previous or "")]
    return secrets or [""]


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
    return jwt.encode(claims, _sign_secret(), algorithm=settings.jwt_algorithm)


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
    return jwt.encode(claims, _sign_secret(), algorithm=settings.jwt_algorithm)


def _decode_any(token: str) -> dict[str, Any] | None:
    """以当前密钥或旧密钥（轮换宽限）验签解码.

    Returns:
        payload；签名/算法/过期无效返回 None。
    """
    settings = get_settings()
    for secret in _verify_secrets():
        try:
            return jwt.decode(
                token, secret, algorithms=[settings.jwt_algorithm]
            )
        except JWTError:
            continue
    return None


def decode_access_token(token: str) -> dict[str, Any] | None:
    """解码并校验访问 Token.

    Args:
        token: JWT 字符串。

    Returns:
        payload；无效/过期/类型错误返回 None。
    """
    payload = _decode_any(token)
    if payload is None:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """解码并校验刷新 Token.

    Returns:
        payload；无效/过期/类型错误返回 None。
    """
    payload = _decode_any(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    return payload
