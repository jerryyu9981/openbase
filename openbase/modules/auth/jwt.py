"""JWT 签发/验证工具.

U1 T2（RA-02/OB-4）：签发侧收敛为单一签发器 ``issue_token_pair`` ——
login/refresh/OIDC bound/直签共用同一路径（同一 tenant_code/sub_type/tvn/role 注入，
禁止双路径分叉）；access/refresh token 增量携带 tenant_code/sub_type/tvn 等全量 claim
（兼容：新参数全部可选，既有调用方/存量 v0 令牌形态不变）。
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from jose import JWTError, jwt

from openbase.settings import get_settings

# 与 openbase/modules/identity/state_machine.py 内联同值（避免顶层循环导入）
_SUBJECT_TYPE_USER = "user"


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
    subject_type: str = _SUBJECT_TYPE_USER,
    token_version: int | None = None,
    tenant_code: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """签发访问 Token（默认有效期 2h）.

    Args:
        subject: 用户 ID（字符串）。
        username: 用户名（冗余进 payload 减少查询）。
        tenant_id: 租户 id（可选）。
        subject_type: 主体具象（user/agent；写 sub_type claim）。
        token_version: 主体 token 版本快照（写 tvn claim；吊销方案 a）。
        tenant_code: 租户唯一隔离键（冗余 claim，RA-02 全量注入目标）。
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
    if subject_type:
        claims["sub_type"] = subject_type
    if token_version is not None:
        claims["tvn"] = token_version
    if tenant_code:
        claims["tenant_code"] = tenant_code
    if extra:
        claims.update(extra)
    return jwt.encode(claims, _sign_secret(), algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str,
    tenant_id: str | None = None,
    username: str = "",
    subject_type: str = _SUBJECT_TYPE_USER,
    token_version: int | None = None,
    tenant_code: str | None = None,
    role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """签发刷新 Token（默认有效期 7d；U1 T2 起携带全量 claim，修 refresh fidelity）.

    Args:
        subject: 用户 ID（字符串）。
        tenant_id: 租户 id（可选）。
        username: 用户名（冗余）。
        subject_type: 主体具象（写 sub_type claim）。
        token_version: 主体 token 版本快照（写 tvn claim）。
        tenant_code: 租户隔离键（写 tenant_code claim）。
        role: 角色码（写 role claim，refresh 链不再回落 viewer）。
        extra: 附加声明（U1 T4：委托场景携带 on_behalf_of 委托块）。

    Returns:
        JWT 字符串（type=refresh）。
    """
    settings = get_settings()
    now = _now()
    claims: dict[str, Any] = {
        "sub": subject,
        "username": username,
        "iat": now,
        "exp": now + dt.timedelta(seconds=settings.refresh_expire_seconds),
        "type": "refresh",
    }
    if tenant_id:
        claims["tenant_id"] = tenant_id
    if subject_type:
        claims["sub_type"] = subject_type
    if token_version is not None:
        claims["tvn"] = token_version
    if tenant_code:
        claims["tenant_code"] = tenant_code
    if role:
        claims["role"] = role
    if extra:
        claims.update(extra)
    return jwt.encode(claims, _sign_secret(), algorithm=settings.jwt_algorithm)


def issue_token_pair(
    *,
    subject: str,
    username: str = "",
    tenant_id: str | None = None,
    tenant_code: str | None = None,
    token_version: int | None = None,
    role: str = "viewer",
    subject_type: str = _SUBJECT_TYPE_USER,
    extra: dict[str, Any] | None = None,
    delegated: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """单一签发器：统一注入 tenant_code/sub_type/tvn/role 并签发 access+refresh（草案 §5.1/§6）.

    login/refresh/OIDC bound/OIDC 降级直签全部经本函数签发（立项 §6.3 同路径要求）：
    - org_id 为兼容别名 = tenant_code（无 code 时回退 tenant_id）；
    - refresh token 携带 username/role/tenant_code/sub_type/tvn（fidelity 闭环）；
    - 存量 v0 令牌（无 tvn/tenant_code）在签发链升级由调用方（refresh）处理。
    - U1 T4（草案 §7.1/§7.3）：delegated 非空时 access/refresh 均嵌入
      ``on_behalf_of`` claim（归属校验由 identity.delegation 于签名前完成）。

    Args:
        subject: 主体 sub（users.id 或 OIDC IdP sub 字符串）。
        username: 用户名。
        tenant_id: 租户 id（可选）。
        tenant_code: 租户隔离键（100% 注入目标）。
        token_version: 主体 token 版本快照（缺省不入 tvn，v0 形态）。
        role: 角色码。
        subject_type: 主体具象（user/agent）。
        extra: 附加 claim（追加覆盖，如 OIDC 场景）。
        delegated: on_behalf_of 委托块（可选；已由委托校验器核准后传入）。

    Returns:
        (access_token, refresh_token)。
    """
    org_value = tenant_code or tenant_id
    claims_extra: dict[str, Any] = {"org_id": org_value, "role": role}
    if extra:
        claims_extra.update(extra)
    if delegated:
        claims_extra["on_behalf_of"] = delegated

    access = create_access_token(
        subject,
        username=username,
        tenant_id=tenant_id,
        subject_type=subject_type,
        token_version=token_version,
        tenant_code=tenant_code,
        extra=claims_extra,
    )
    refresh = create_refresh_token(
        subject,
        tenant_id,
        username=username,
        subject_type=subject_type,
        token_version=token_version,
        tenant_code=tenant_code,
        role=role,
        extra={"on_behalf_of": delegated} if delegated else None,
    )
    return access, refresh


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
