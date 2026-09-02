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
from fastapi import APIRouter, HTTPException, Query, Request
from jose import JWTError, jwt as jose_jwt

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
        """拉取并缓存 IdP discovery 文档（幂等）. """
        if self._discovery is not None:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self._settings().oidc_discovery_url)
            resp.raise_for_status()
            doc = resp.json()
        self._issuer = doc.get("issuer", "")
        self._authorization_endpoint = doc.get("authorization_endpoint", "")
        self._token_endpoint = doc.get("token_endpoint", "")
        if not self._authorization_endpoint or not self._token_endpoint:
            raise OIDCError("discovery document missing endpoints")
        self._discovery = doc

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
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> dict:
    """OIDC 回调：code 换令牌 → 解析 ID Token → 映射 claims → 签发统一 JWT. """
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
    access = create_access_token(
        mapped["sub"],
        username=mapped["username"],
        tenant_id=mapped["tenant_id"],
        extra=mapped["extra"],
    )
    refresh = create_refresh_token(mapped["sub"], mapped["tenant_id"])
    # 透传 IdP 身份供审计/身份头注入（下游网关模式消费）
    request.state.oidc_claims = claims
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_seconds,
        "refresh_token": refresh,
        "refresh_expires_in": settings.refresh_expire_seconds,
    }
