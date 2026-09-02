"""auth 模块：OIDC 统一认证（OB-AUTH-OIDC）.

OpenBase 统一网关单点集成 OIDC：授权码流程对接外部 IdP，签发统一 JWT
（与本地账号登录同一套 claims 语义），下游服务以网关模式消费。

默认关闭（oidc_enabled=false），不影响现有本地账号认证。
"""

from __future__ import annotations

import logging
import secrets
import urllib.parse
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.modules.auth.jwt import create_access_token, create_refresh_token
from openbase.settings import get_settings

logger = logging.getLogger("openbase.auth.oidc")

# 简单内存 state 存储（授权码流程 CSRF 防护；多实例部署可换 Redis）
_state_store: dict[str, str] = {}


class OIDCError(Exception):
    """OIDC 流程错误."""


class OIDCClient:
    """OIDC 客户端（discovery + 授权码流程 + ID Token 解析）.

    每次操作读取最新全局 settings（get_settings），避免单例缓存旧配置。
    """

    def __init__(self, settings=None) -> None:
        # 显式注入的 settings 优先；None 时每次动态读取全局单例
        self._injected_settings = settings
        self._discovery: dict[str, Any] | None = None
        self._discovery_url: str = ""  # 已缓存 discovery 的 URL 指纹
        self._authorization_endpoint = ""
        self._token_endpoint = ""
        self._issuer = ""

    def _settings(self):
        return self._injected_settings or get_settings()

    @property
    def enabled(self) -> bool:
        s = self._settings()
        return bool(
            s.oidc_enabled and s.oidc_discovery_url and s.oidc_client_id
        )

    async def _load_discovery(self) -> None:
        """拉取并缓存 IdP discovery 文档（幂等；按 discovery URL 指纹失效）."""
        url = self._settings().oidc_discovery_url
        if self._discovery is not None and self._discovery_url == url:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            doc = resp.json()
        self._issuer = doc.get("issuer", "")
        self._authorization_endpoint = doc.get("authorization_endpoint", "")
        self._token_endpoint = doc.get("token_endpoint", "")
        if not self._authorization_endpoint or not self._token_endpoint:
            raise OIDCError("discovery document missing endpoints")
        self._discovery = doc
        self._discovery_url = url

    async def build_authorize_url(self, state: str) -> str:
        """构造 IdP 授权端点 URL（302 重定向目标）. """
        s = self._settings()
        await self._load_discovery()
        params = {
            "response_type": "code",
            "client_id": s.oidc_client_id,
            "redirect_uri": s.oidc_redirect_uri,
            "scope": s.oidc_scopes,
            "state": state,
        }
        return f"{self._authorization_endpoint}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """授权码换取令牌（token_endpoint），返回含 ID Token 的完整响应. """
        s = self._settings()
        await self._load_discovery()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": s.oidc_redirect_uri,
            "client_id": s.oidc_client_id,
            "client_secret": s.oidc_client_secret,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self._token_endpoint, data=payload)
            resp.raise_for_status()
            return resp.json()

    def parse_id_token(self, id_token: str) -> dict[str, Any]:
        """解析 ID Token 并校验签名（IdP JWKS 公钥 RS256）与 issuer/aud/exp. """
        s = self._settings()
        if not self._discovery:
            raise OIDCError("discovery not loaded")
        jwks_uri = self._discovery.get("jwks_uri")
        if not jwks_uri:
            raise OIDCError("discovery document missing jwks_uri")
        with httpx.Client(timeout=10.0) as client:
            jwks = client.get(jwks_uri).json()
        try:
            claims = jose_jwt.decode(
                id_token,
                jwks,
                algorithms=["RS256"],
                audience=s.oidc_client_id,
                issuer=self._issuer or None,
            )
        except JWTError as exc:
            raise OIDCError(f"id token validation failed: {exc}") from exc
        return claims

    def map_claims(self, claims: dict[str, Any]) -> dict[str, Any]:
        """OIDC claims → 统一 JWT claims 映射（sub/org_id/role/租户）. """
        s = self._settings()
        sub = str(claims.get("sub") or "oidc-anonymous")
        tenant = (
            claims.get("tenant_id")
            or claims.get("org")
            or claims.get("org_id")
            or s.oidc_default_tenant
        )
        role_raw = claims.get(s.oidc_claim_role) or claims.get("role")
        if isinstance(role_raw, list):
            role = role_raw[0] if role_raw else "viewer"
        else:
            role = role_raw or "viewer"
        return {
            "sub": sub,
            "username": claims.get("preferred_username") or claims.get("email") or sub,
            "tenant_id": str(tenant),
            "extra": {"org_id": str(tenant), "role": role},
        }


_oidc_client: OIDCClient | None = None


def _get_oidc_client() -> OIDCClient:
    global _oidc_client
    if _oidc_client is None:
        _oidc_client = OIDCClient()
    return _oidc_client


router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth"])


# ---- OIDC 用户体系绑定（OB-AUTH-OIDC v1.3.0：JIT 自动建号 + sub 映射） ----


async def _ensure_roles(session: Any, user_id: int, claims: dict[str, Any]) -> str | None:
    """幂等确保用户绑定 claims roles 对应的 Role（缺失补绑），返回主角色 code.

    白名单过滤（admin/org_admin/user/viewer）；未知 role code 忽略。
    """
    from sqlalchemy import select

    from openbase.core.models import Role, user_role

    raw_roles = claims.get("roles") or claims.get("role") or []
    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    want_codes = [
        str(r) for r in raw_roles if str(r) in ("admin", "org_admin", "user", "viewer")
    ]
    if not want_codes:
        return None

    # 现有绑定
    existing = await session.execute(
        select(Role.code)
        .join(user_role, user_role.c.role_id == Role.id)
        .where(user_role.c.user_id == user_id)
    )
    have_codes = set(existing.scalars().all())

    bound_role: str | None = None
    for code in want_codes:
        if bound_role is None and code in have_codes:
            bound_role = code
        if code in have_codes:
            continue
        r_res = await session.execute(select(Role).where(Role.code == code))
        role = r_res.scalar_one_or_none()
        if role is None:
            continue
        if bound_role is None:
            bound_role = role.code
        await session.execute(
            user_role.insert().values(user_id=user_id, role_id=role.id)
        )
    return bound_role or next((c for c in want_codes if c in have_codes), None)


async def _bind_or_create_user(
    claims: dict[str, Any], session: Any
) -> dict[str, Any] | None:
    """OIDC 身份 → OpenBase 用户绑定（自动建号）.

    策略（OB-AUTH-OIDC v1.3.0）：
    1) 按 IdP sub（+issuer）查 OidcIdentity → 命中即复用绑定用户；
    2) 未命中则 JIT 建号：username/display_name/email 来自 claims，
       password_hash 置随机（不可密码登录），租户按 claims 匹配 Tenant.code，
       角色按 claims roles 映射 Role.code 并绑定 user_role；
    3) DB 异常返回 None（调用方降级：以 IdP sub 直签 JWT，保证可用性）。

    Returns:
        用户信息 dict {id, username, tenant_id, role}；DB 不可用返回 None。
    """
    from sqlalchemy import select

    from openbase.core.models import OidcIdentity, Tenant, User

    try:
        issuer = claims.get("iss") or ""
        sub = str(claims.get("sub") or "")
        if not sub:
            return None
        # 1) 既有映射复用
        result = await session.execute(
            select(OidcIdentity, User)
            .join(User, User.id == OidcIdentity.user_id)
            .where(OidcIdentity.sub == sub, OidcIdentity.issuer == issuer)
        )
        row = result.first()
        if row is not None:
            identity, user = row
            # 更新 IdP 侧快照（幂等）
            identity.idp_username = claims.get("preferred_username") or claims.get("email")
            identity.idp_email = claims.get("email")
            await _ensure_roles(session, user.id, claims)
            # get_db 会话请求结束自动回滚，须显式提交（首次分支在末尾 commit）
            await session.commit()
            return {
                "id": user.id,
                "username": user.username,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            }
        # 2) JIT 自动建号
        # 租户：claims tenant/org/org_id → Tenant.code；无匹配则 None（与 admin 一致）
        tenant_code = (
            claims.get("tenant_id") or claims.get("org") or claims.get("org_id")
        )
        tenant = None
        if tenant_code:
            t_res = await session.execute(
                select(Tenant).where(Tenant.code == str(tenant_code))
            )
            tenant = t_res.scalar_one_or_none()

        # 用户名：preferred_username > email 前缀 > sub；冲突加随机后缀
        base = (
            claims.get("preferred_username")
            or (claims.get("email") or "").split("@")[0]
            or sub[:32]
        )
        username = str(base)[:48] or "oidc-user"
        u_res = await session.execute(
            select(User).where(User.username == username)
        )
        if u_res.scalar_one_or_none() is not None:
            username = f"{username}-{secrets.token_hex(2)}"

        # 密码：随机占位（OIDC 用户不可密码登录）
        from openbase.modules.auth import hash_password

        user_obj = User(
            username=username,
            password_hash=hash_password(secrets.token_hex(32)),
            display_name=(
                claims.get("name")
                or claims.get("preferred_username")
                or username
            )[:128],
            email=(claims.get("email") or None),
            status=1,
            tenant_id=tenant.id if tenant else None,
        )
        session.add(user_obj)
        await session.flush()

        # 角色：幂等绑定（claims roles → Role.code 白名单过滤，复用 _ensure_roles）
        bound_role = await _ensure_roles(session, user_obj.id, claims)

        # 3) 写 OIDC 映射
        session.add(
            OidcIdentity(
                user_id=user_obj.id,
                sub=sub,
                issuer=issuer,
                idp_username=claims.get("preferred_username") or claims.get("email"),
                idp_email=claims.get("email"),
            )
        )
        await session.commit()
        return {
            "id": user_obj.id,
            "username": username,
            "tenant_id": str(user_obj.tenant_id) if user_obj.tenant_id else None,
            "role": bound_role or "viewer",
        }
    except Exception:  # noqa: BLE001 - DB 不可用时降级（网关可用性优先）
        logger.warning("oidc user binding failed, fallback to raw sub", extra={"sub": str(claims.get("sub", ""))})
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


@router.get("/authorize")
async def oidc_authorize() -> dict:
    """发起 OIDC 授权码流程：返回 IdP 授权 URL（前端 302/跳转）. """
    client = _get_oidc_client()
    if not client.enabled:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    state = secrets.token_urlsafe(32)
    _state_store[state] = "pending"
    try:
        authorize_url = await client.build_authorize_url(state)
    except OIDCError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"authorize_url": authorize_url, "state": state}


@router.get("/callback")
async def oidc_callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> dict:
    """OIDC 回调：code 换令牌 → 解析 ID Token → 映射 claims → 签发统一 JWT.

    v1.3.0 绑定策略：claims 解析后执行 JIT 绑定（OidcIdentity 映射表），
    绑定成功则统一 JWT 的 sub = OpenBase 用户 id（与本地账号同体系）；
    DB 不可用时降级以 IdP sub 直签（网关可用性优先）。
    """
    if error:
        raise HTTPException(status_code=400, detail=f"oidc error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing code or state")
    if _state_store.pop(state, None) is None:
        raise HTTPException(status_code=400, detail="invalid state")

    client = _get_oidc_client()
    if not client.enabled:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    try:
        token_resp = await client.exchange_code(code)
        id_token = token_resp.get("id_token")
        if not id_token:
            raise OIDCError("token response missing id_token")
        claims = client.parse_id_token(id_token)
    except (OIDCError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    mapped = client.map_claims(claims)
    settings = get_settings()

    # v1.3.0：OIDC 用户体系绑定（JIT 建号/复用；DB 不可用返回 None → 降级）
    bound = await _bind_or_create_user(claims, session)
    if bound is not None:
        subject = str(bound["id"])
        username = bound.get("username") or mapped["username"]
        tenant_id = bound.get("tenant_id") or mapped["tenant_id"]
        # 角色：绑定角色（首次建号映射）> claims 原角色 > viewer
        raw_role = bound.get("role") or (mapped["extra"].get("role") or "viewer")
    else:
        subject = mapped["sub"]
        username = mapped["username"]
        tenant_id = mapped["tenant_id"]
        raw_role = mapped["extra"].get("role") or "viewer"

    extra = {"org_id": tenant_id, "role": raw_role}
    access = create_access_token(
        subject,
        username=username,
        tenant_id=tenant_id,
        extra=extra,
    )
    refresh = create_refresh_token(subject, tenant_id)
    # 透传 IdP 身份供审计/身份头注入（下游网关模式消费）
    request.state.oidc_claims = claims
    request.state.bound_user = bound is not None
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_seconds,
        "refresh_token": refresh,
        "refresh_expires_in": settings.refresh_expire_seconds,
    }
