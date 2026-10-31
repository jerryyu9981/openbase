"""auth 模块：OIDC 统一认证（OB-AUTH-OIDC）.

OpenBase 统一网关单点集成 OIDC：授权码流程对接外部 IdP，签发统一 JWT
（与本地账号登录同一套 claims 语义），下游服务以网关模式消费。

默认关闭（oidc_enabled=false），不影响现有本地账号认证。
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
import urllib.parse
from collections.abc import Mapping
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Role, Tenant, User, user_role
from openbase.modules.auth.idp_registry import IdpProviderConfig, parse_idp_providers
from openbase.modules.auth.jwt import issue_token_pair
from openbase.modules.auth.oidc_state import get_state_store
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    SUBJECT_TYPE_USER,
)
from openbase.settings import OIDC_ID_TOKEN_ALGORITHMS, get_settings

logger = logging.getLogger("openbase.auth.oidc")

# RFC 7523 §2.2：private_key_jwt 的 client_assertion_type 固定 URN
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
# 客户端断言有效期（秒）：仅用于单次 token 请求，短有效期即可
CLIENT_ASSERTION_TTL_SECONDS = 300


class OIDCError(Exception):
    """OIDC 流程错误."""


def _normalized_algorithms(raw: str) -> list[str]:
    """配置串 → 算法名列表（大写、去重保序，空项忽略）."""
    result: list[str] = []
    for item in (raw or "").split(","):
        name = item.strip().upper()
        if name and name not in result:
            result.append(name)
    return result


def resolve_id_token_algorithms(
    configured: list[str], discovery: dict[str, Any]
) -> list[str]:
    """配置白名单 ∩ IdP discovery 声明（无交集即失败，禁静默降级）."""
    declared = discovery.get("id_token_signing_alg_values_supported")
    if isinstance(declared, list):
        declared_names = {str(item).upper() for item in declared}
    else:
        declared_names = set(OIDC_ID_TOKEN_ALGORITHMS)
    algorithms = [name for name in configured if name in declared_names]
    if not algorithms:
        raise OIDCError("no mutually supported id_token signing algorithm")
    return algorithms


def code_challenge_for(verifier: str) -> str:
    """PKCE S256 challenge：base64url(sha256(verifier))，去填充."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_id_token_nonce(expected: str, claims: Mapping[str, Any]) -> None:
    """校验 ID Token nonce（防重放）；不一致抛 AUTH_TOKEN_INVALID.

    Raises:
        BaseError: nonce 缺失或不匹配（HTTP 401 AUTH_401_INVALID）。
    """
    actual = claims.get("nonce")
    if not expected or not secrets.compare_digest(str(actual or ""), str(expected)):
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "oidc id_token nonce mismatch")


class OIDCClient:
    """OIDC 客户端（discovery + 授权码流程 + ID Token 解析）.

    每次操作读取最新全局 settings（get_settings），避免单例缓存旧配置。
    """

    def __init__(
        self, settings=None, provider: IdpProviderConfig | None = None
    ) -> None:
        # 显式注入的 settings 优先；None 时每次动态读取全局单例
        self._injected_settings = settings
        # 多 Provider（v1.15.0）：非 None 时客户端字段取自 Provider 声明，
        # 未声明的字段（PKCE/算法/Keycloak client 角色）仍读全局 settings
        self._provider = provider
        self._discovery: dict[str, Any] | None = None
        self._discovery_url: str = ""  # 已缓存 discovery 的 URL 指纹
        self._authorization_endpoint = ""
        self._token_endpoint = ""
        self._issuer = ""

    def _settings(self):
        return self._injected_settings or get_settings()

    @property
    def provider_name(self) -> str:
        """Provider 名称（单 IdP 模式为空串）."""
        return self._provider.name if self._provider is not None else ""

    @property
    def discovery_url(self) -> str:
        if self._provider is not None:
            return self._provider.discovery_url
        return self._settings().oidc_discovery_url

    @property
    def client_id(self) -> str:
        if self._provider is not None:
            return self._provider.client_id
        return self._settings().oidc_client_id

    @property
    def client_secret(self) -> str:
        if self._provider is not None:
            return self._provider.client_secret
        return self._settings().oidc_client_secret

    @property
    def redirect_uri(self) -> str:
        # Provider 未显式声明回调时回退全局回调地址（所有回调仍落在同一网关端点）
        if self._provider is not None and self._provider.redirect_uri:
            return self._provider.redirect_uri
        return self._settings().oidc_redirect_uri

    @property
    def scopes(self) -> str:
        if self._provider is not None:
            return self._provider.scopes
        return self._settings().oidc_scopes

    @property
    def profile(self) -> str:
        if self._provider is not None:
            return self._provider.profile
        return self._settings().oidc_profile

    @property
    def claim_role(self) -> str:
        if self._provider is not None:
            return self._provider.claim_role
        return self._settings().oidc_claim_role

    @property
    def default_tenant(self) -> str:
        if self._provider is not None:
            return self._provider.default_tenant
        return self._settings().oidc_default_tenant

    @property
    def enabled(self) -> bool:
        # 全局 oidc_enabled 仍为总开关；Provider 模式再要求 discovery/client_id 齐备
        return bool(self._settings().oidc_enabled and self.discovery_url and self.client_id)

    async def _load_discovery(self) -> None:
        """拉取并缓存 IdP discovery 文档（幂等；按 discovery URL 指纹失效）."""
        url = self.discovery_url
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

    async def build_authorize_url(
        self, state: str, *, nonce: str = "", code_challenge: str = ""
    ) -> str:
        """构造 IdP 授权端点 URL（302 重定向目标）.

        Args:
            state: CSRF 防护随机串。
            nonce: ID Token 重放防护随机串（非空即下发）。
            code_challenge: PKCE S256 challenge（非空即下发 S256 方法）。
        """
        await self._load_discovery()
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": state,
        }
        if nonce:
            params["nonce"] = nonce
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return f"{self._authorization_endpoint}?{urllib.parse.urlencode(params)}"

    def token_auth_method(self) -> str:
        """token 端点客户端认证方式（全局配置；Provider 模式共用）."""
        return (self._settings().oidc_token_auth_method or "").strip().lower()

    def token_request_options(self) -> dict[str, Any]:
        """按认证方式装配 httpx 请求选项（Basic 头 / mTLS 证书）.

        - ``client_secret_basic``：RFC 6749 §2.3.1，凭据经 HTTP Basic 头；
        - ``mtls``：RFC 8705，客户端证书认证（``cert`` + 可选 ``verify``）；
        - ``client_secret_post`` / ``private_key_jwt``：认证材料均在表单，无额外选项。
        """
        method = self.token_auth_method()
        if method == "client_secret_basic":
            return {"auth": httpx.BasicAuth(self.client_id, self.client_secret)}
        if method == "mtls":
            settings = self._settings()
            cert_path = (settings.oidc_client_cert_path or "").strip()
            key_path = (settings.oidc_client_key_path or "").strip()
            ca_path = (settings.oidc_client_ca_path or "").strip()
            cert = (cert_path, key_path) if key_path else cert_path
            return {"cert": cert, "verify": ca_path or True}
        return {}

    def _build_client_assertion(self) -> str:
        """构造 RFC 7523 §2.2 客户端断言（RS256 签名）.

        断言 ``iss`` / ``sub`` 均为 ``client_id``，受众取 discovery 声明的
        token 端点（未加载 discovery 时无法确定受众，直接报错）；带 ``jti``
        与短有效期，满足一次性使用要求。

        Raises:
            OIDCError: discovery 未加载、未配置断言私钥路径。
        """
        token_endpoint = self._token_endpoint
        if not token_endpoint:
            raise OIDCError("client assertion requires discovery token endpoint")
        settings = self._settings()
        private_key_path = (settings.oidc_client_private_key_path or "").strip()
        if not private_key_path:
            raise OIDCError("client assertion private key path is not configured")
        with open(private_key_path, encoding="utf-8") as handle:
            private_key = handle.read()
        issued_at = int(time.time())
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": token_endpoint,
            "iat": issued_at,
            "exp": issued_at + CLIENT_ASSERTION_TTL_SECONDS,
            "jti": secrets.token_urlsafe(16),
        }
        headers = {"alg": "RS256", "typ": "JWT"}
        key_id = (settings.oidc_client_assertion_kid or "").strip()
        if key_id:
            headers["kid"] = key_id
        return jose_jwt.encode(claims, private_key, algorithm="RS256", headers=headers)

    def token_payload(
        self, code: str, *, code_verifier: str | None = None
    ) -> dict[str, str]:
        """token 端点表单载荷（按认证方式决定是否携带 client 凭据）.

        Basic 模式凭据走 Authorization 头，表单不得重复携带（RFC 6749 §2.3.1）；
        mTLS 模式仅带 ``client_id``（客户端已由证书认证）；
        private_key_jwt 模式带 ``client_id`` + ``client_assertion_type`` +
        ``client_assertion``（RFC 7523）。
        """
        method = self.token_auth_method()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier
        if method != "client_secret_basic":
            payload["client_id"] = self.client_id
        if method == "client_secret_post":
            payload["client_secret"] = self.client_secret
        elif method == "private_key_jwt":
            payload["client_assertion_type"] = CLIENT_ASSERTION_TYPE
            payload["client_assertion"] = self._build_client_assertion()
        return payload

    async def exchange_code(
        self, code: str, *, code_verifier: str | None = None
    ) -> dict[str, Any]:
        """授权码换取令牌（token_endpoint），返回含 ID Token 的完整响应.

        客户端认证方式由 ``oidc_token_auth_method`` 决定（v1.17.0 / v1.18.0）：
        ``client_secret_post``（默认）/ ``client_secret_basic`` / ``mtls``
        / ``private_key_jwt``。

        Args:
            code: IdP 回传的授权码。
            code_verifier: PKCE 原始校验串（启用 PKCE 时必传）。
        """
        await self._load_discovery()
        payload = self.token_payload(code, code_verifier=code_verifier)
        request_options = self.token_request_options()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                self._token_endpoint, data=payload, **request_options
            )
            resp.raise_for_status()
            return resp.json()

    def _verify_token(
        self, token: str, *, access_token: str | None = None
    ) -> dict[str, Any]:
        """通用令牌验签：discovery JWKS 公钥 RS256 + issuer/aud/exp 校验.

        ID Token 与 access token 同源签发、同一 JWKS/issuer/audience，
        Keycloak 场景（角色默认仅进 access token）需要同样的验签能力。
        access_token 用于 ID Token 的 at_hash 校验（授权码流标准 claim，
        Keycloak 默认携带；缺失比对目标会验签失败）。
        """
        if not self._discovery:
            raise OIDCError("discovery not loaded")
        jwks_uri = self._discovery.get("jwks_uri")
        if not jwks_uri:
            raise OIDCError("discovery document missing jwks_uri")
        algorithms = resolve_id_token_algorithms(
            _normalized_algorithms(self._settings().oidc_signing_algorithms),
            self._discovery,
        )
        with httpx.Client(timeout=10.0) as client:
            jwks = client.get(jwks_uri).json()
        try:
            return jose_jwt.decode(
                token,
                jwks,
                algorithms=algorithms,
                audience=self.client_id,
                issuer=self._issuer or None,
                access_token=access_token,
            )
        except JWTError as exc:
            raise OIDCError(f"token validation failed: {exc}") from exc

    def parse_id_token(
        self, id_token: str, access_token: str | None = None
    ) -> dict[str, Any]:
        """解析 ID Token 并校验签名（IdP JWKS 公钥 RS256）与 issuer/aud/exp/at_hash. """
        return self._verify_token(id_token, access_token=access_token)

    def verify_access_token(self, access_token: str) -> dict[str, Any]:
        """解析 access token（同 JWKS/issuer/aud 校验）.

        v1.4.0 Keycloak profile：角色默认只出现在 access token（realm_access），
        当 ID Token 无角色时以此作为角色来源。
        """
        return self._verify_token(access_token)

    async def build_logout_url(self, *, post_logout_redirect_uri: str = "") -> str | None:
        """构造 IdP 登出 URL（discovery ``end_session_endpoint``；未声明返回 None）.

        v1.16.0：本地已吊销（token_version 递增）后，前端可跳转该 URL 同时结束
        IdP 会话（前端信道/RP-Initiated Logout，IF-01 RFC 中的可选能力）。
        """
        await self._load_discovery()
        endpoint = (self._discovery or {}).get("end_session_endpoint")
        if not endpoint:
            return None
        params: dict[str, str] = {"client_id": self.client_id}
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri
        return f"{endpoint}?{urllib.parse.urlencode(params)}"

    def map_claims(self, claims: dict[str, Any]) -> dict[str, Any]:
        """OIDC claims → 统一 JWT claims 映射（sub/org_id/role/租户）. """
        sub = str(claims.get("sub") or "oidc-anonymous")
        tenant = (
            claims.get("tenant_id")
            or claims.get("org")
            or claims.get("org_id")
            or self.default_tenant
        )
        role_raw = claims.get(self.claim_role) or claims.get("role")
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
# 多 Provider 客户端缓存（键 = Provider 名；配置变更按 dataclass 等值失效）
_provider_clients: dict[str, OIDCClient] = {}


def _get_oidc_client() -> OIDCClient:
    global _oidc_client
    if _oidc_client is None:
        _oidc_client = OIDCClient()
    return _oidc_client


def _registered_providers() -> tuple[IdpProviderConfig, ...]:
    """读取已登记 Provider（配置已在启动门禁校验，异常按系统错误处理）."""
    try:
        return parse_idp_providers(get_settings().idp_providers)
    except ValueError as exc:
        raise BaseError(
            ErrorCode.SYS_INTERNAL_ERROR, f"invalid idp provider configuration: {exc}"
        ) from exc


def _get_provider_client(name: str) -> OIDCClient:
    """按名称取 Provider 客户端（缓存；未登记/空登记 → 400 PARAM_INVALID）."""
    providers = _registered_providers()
    if not providers:
        raise BaseError(ErrorCode.PARAM_INVALID, "no oidc provider registered")
    provider = next((item for item in providers if item.name == name), None)
    if provider is None:
        raise BaseError(ErrorCode.PARAM_INVALID, f"unknown oidc provider: {name}")
    cached = _provider_clients.get(name)
    if cached is None or cached._provider != provider:
        cached = OIDCClient(provider=provider)
        _provider_clients[name] = cached
    return cached


def _resolve_oidc_client(provider: str | None) -> OIDCClient:
    """按 ``provider`` 查询参数选择客户端（空/未指定 → 既有单 IdP 路径）."""
    name = (provider or "").strip()
    if not name:
        return _get_oidc_client()
    return _get_provider_client(name)


router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth"])


# ---- OIDC 用户体系绑定（OB-AUTH-OIDC v1.3.0：JIT 自动建号 + sub 映射） ----

# OpenBase 角色白名单：OIDC claims 角色仅映射这些 code（未知角色忽略，
# 避免 Keycloak 默认伪角色 default-roles-* / offline_access 等污染统一 JWT role）
OIDC_ROLE_WHITELIST = ("admin", "org_admin", "user", "viewer")


def _roles_from_keycloak(
    claims: dict[str, Any],
    client_id: str,
    include_client_roles: bool = True,
) -> list[str]:
    """Keycloak claims 角色聚合（去重保序）.

    来源：平铺 roles/role（自定义 mapper 兼容）> realm_access.roles（realm 角色）
    > resource_access.<client_id>.roles（client 角色，可配置关闭）。
    Keycloak 默认 realm/client 角色仅进 access token（官方默认 mapper 行为），
    ID Token 是否携带取决于 client mapper 配置——故聚合需同时支持两令牌来源。
    """
    roles: list[str] = []
    flat = claims.get("roles")
    if isinstance(flat, list):
        roles.extend(str(item) for item in flat)
    elif isinstance(flat, str):
        roles.append(flat)
    role_alt = claims.get("role")
    if isinstance(role_alt, str):
        roles.append(role_alt)
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        realm_roles = realm_access.get("roles")
        if isinstance(realm_roles, list):
            roles.extend(str(item) for item in realm_roles)
    if include_client_roles:
        resource_access = claims.get("resource_access")
        if isinstance(resource_access, dict):
            entry = resource_access.get(client_id)
            if isinstance(entry, dict):
                client_roles = entry.get("roles")
                if isinstance(client_roles, list):
                    roles.extend(str(item) for item in client_roles)
    seen: set[str] = set()
    ordered: list[str] = []
    for role in roles:
        if role and role not in seen:
            seen.add(role)
            ordered.append(role)
    return ordered


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
        str(r) for r in raw_roles if str(r) in OIDC_ROLE_WHITELIST
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


async def _tenant_code_from_id(session: Any, tenant_value: str) -> str | None:
    """按 tenants.id 解析 tenant_code（数字形态 → 查 tenants.code；code 串原样透传）.

    DB 不可达/无匹配返回 None（调用方不追加 claim，向后兼容）。
    """
    if not tenant_value:
        return None
    if not tenant_value.isdigit():
        return tenant_value
    try:
        result = await session.execute(
            select(Tenant.code).where(Tenant.id == int(tenant_value))
        )
        return result.scalar_one_or_none()
    except Exception:  # noqa: BLE001 - DB 不可达降级（不追加 claim）
        return None


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
            # F-9（同根因旁路，2026-10-16）：与 POST /users 一致——派生列 tenant_code
            # 必须随 tenant_id 同时落库（委托域不变式要求目标行域非空）。
            tenant_code=tenant.code if tenant else None,
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
        # 可观测性：记录完整异常堆栈（降级是预期兜底，但原因必须可查）
        logger.error(
            "oidc user binding failed, fallback to raw sub",
            extra={"sub": str(claims.get("sub", ""))},
            exc_info=True,
        )
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


@router.get("/authorize")
async def oidc_authorize(provider: str | None = Query(default=None)) -> dict:
    """发起 OIDC 授权码流程：返回 IdP 授权 URL（前端 302/跳转）.

    v1.14.0：state / nonce / PKCE verifier 一次性登记（TTL + 多实例共享），
    authorize URL 携带 ``nonce`` 与 ``code_challenge``（S256）。
    v1.15.0：``provider`` 指定已登记 Provider（空/未指定保持单 IdP ``oidc_*`` 语义），
    state 载荷同时记录 Provider 名，callback 据此还原对应客户端。
    """
    client = _resolve_oidc_client(provider)
    if not client.enabled:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, "oidc not enabled")
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(48) if settings.oidc_pkce_enabled else ""
    get_state_store().issue(
        state,
        {
            "nonce": nonce,
            "code_verifier": code_verifier,
            "provider": client.provider_name,
        },
        ttl_seconds=settings.oidc_state_ttl_seconds,
    )
    try:
        authorize_url = await client.build_authorize_url(
            state,
            nonce=nonce,
            code_challenge=code_challenge_for(code_verifier) if code_verifier else "",
        )
    except OIDCError as exc:
        raise BaseError(ErrorCode.SYS_UPSTREAM_ERROR, str(exc)) from exc
    response = {"authorize_url": authorize_url, "state": state}
    if client.provider_name:
        response["provider"] = client.provider_name
    return response


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
        raise BaseError(ErrorCode.PARAM_INVALID, f"oidc error: {error}")
    if not code or not state:
        raise BaseError(ErrorCode.PARAM_INVALID, "missing code or state")
    stored = get_state_store().consume(state)
    if stored is None:
        raise BaseError(ErrorCode.PARAM_INVALID, "invalid or expired state")

    # v1.15.0：state 记录 Provider 名 → 还原对应客户端（空 = 单 IdP 既有路径）
    client = _resolve_oidc_client(str(stored.get("provider") or ""))
    if not client.enabled:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, "oidc not enabled")
    try:
        token_resp = await client.exchange_code(
            code, code_verifier=stored.get("code_verifier") or None
        )
        id_token = token_resp.get("id_token")
        if not id_token:
            raise OIDCError("token response missing id_token")
        # access_token 供 ID Token at_hash 校验（Keycloak ID Token 默认携带 at_hash）
        claims = client.parse_id_token(id_token, token_resp.get("access_token"))
    except (OIDCError, httpx.HTTPError) as exc:
        logger.warning(
            "oidc code exchange or id_token parse failed",
            extra={"error": str(exc) or exc.__class__.__name__},
        )
        raise BaseError(ErrorCode.SYS_UPSTREAM_ERROR, str(exc)) from exc
    # v1.14.0：nonce 校验（防 ID Token 重放），与授权请求下发的 nonce 必须一致
    verify_id_token_nonce(str(stored.get("nonce") or ""), claims)

    settings = get_settings()
    # v1.4.0 Keycloak profile：realm/client 角色默认仅进 access token（官方默认 mapper，
    # ID Token 不含角色）。ID Token 聚合为空时验签 access token 兜底，归一化写回 roles。
    if client.profile == "keycloak":
        roles = _roles_from_keycloak(
            claims, client.client_id, settings.oidc_keycloak_client_roles
        )
        if not roles:
            access_token = token_resp.get("access_token")
            if access_token:
                try:
                    at_claims = client.verify_access_token(access_token)
                except (OIDCError, httpx.HTTPError) as exc:
                    logger.warning(
                        "keycloak access token verify failed, roles fallback skipped",
                        extra={"error": str(exc)},
                    )
                else:
                    roles = _roles_from_keycloak(
                        at_claims,
                        client.client_id,
                        settings.oidc_keycloak_client_roles,
                    )
        if roles:
            # 白名单过滤（保留顺序）：剔除 Keycloak 默认伪角色
            # （default-roles-* / offline_access / uma_authorization 等），
            # 避免统一 JWT role 取到首个伪角色
            roles = [r for r in roles if r in OIDC_ROLE_WHITELIST]
        if roles:
            claims["roles"] = roles

    mapped = client.map_claims(claims)

    # v1.3.0：OIDC 用户体系绑定（JIT 建号/复用；DB 不可用返回 None → 降级直签）
    bound = await _bind_or_create_user(claims, session)
    subject_row: User | None = None
    if bound is not None:
        subject = str(bound["id"])
        username = bound.get("username") or mapped["username"]
        tenant_id = bound.get("tenant_id") or mapped["tenant_id"]
        # 角色：绑定角色（首次建号映射）> claims 原角色 > viewer
        raw_role = bound.get("role") or (mapped["extra"].get("role") or "viewer")
        # U1 T2（RA-02，草案 §2.2/§6.3）：OIDC 接入状态机——suspended/deactivated 绑定主体
        # 经 IdP 重登/JIT 复用一律被拒（停用拦截，callback 401 AUTH_PRINCIPAL_DISABLED）。
        try:
            user_row = await session.get(User, int(bound["id"]))
        except Exception:  # noqa: BLE001 - 查不到主体按禁用处理（fail-closed）
            user_row = None
        if user_row is None or (user_row.subject_type or SUBJECT_TYPE_USER) != SUBJECT_TYPE_USER:
            raise BaseError(
                ErrorCode.AUTH_PRINCIPAL_DISABLED, "oidc principal is unavailable"
            )
        if user_row.status_state != STATUS_STATE_ACTIVE:
            raise BaseError(
                ErrorCode.AUTH_PRINCIPAL_DISABLED,
                "oidc principal is not active",
                detail={"status_state": user_row.status_state},
            )
        subject_row = user_row
    else:
        subject = mapped["sub"]
        username = mapped["username"]
        tenant_id = mapped["tenant_id"]
        raw_role = mapped["extra"].get("role") or "viewer"

    # U1 T2（RA-02/OB-4）：bound/直签共用同一签发器 issue_token_pair（草案 §6.1/§6.3）。
    # bound 路径以主体行冗余字段为准；直签（DB 降级）以 IdP claims code 原样透传。
    if subject_row is not None:
        subject_type = subject_row.subject_type or SUBJECT_TYPE_USER
        final_username = subject_row.username or username
        final_tenant_id = str(subject_row.tenant_id) if subject_row.tenant_id else None
        oidc_tenant_code = subject_row.tenant_code
        if not oidc_tenant_code and final_tenant_id:
            oidc_tenant_code = await _tenant_code_from_id(session, final_tenant_id)
        token_version = subject_row.token_version or 0
        # role：当前绑定角色快照（claims roles 已幂等同步）> bound/claims 角色 > viewer
        role_result = await session.execute(
            select(Role.code)
            .join(user_role, user_role.c.role_id == Role.id)
            .where(user_role.c.user_id == subject_row.id)
        )
        role_codes = list(role_result.scalars().all())
        final_role = role_codes[0] if role_codes else (raw_role or "viewer")
    else:
        subject_type = SUBJECT_TYPE_USER
        final_username = username
        final_tenant_id = tenant_id
        # 直签：tenant_id 为 IdP 侧 code 字符串原样透传；数字形态尝试查 tenants.code
        oidc_tenant_code = None
        if tenant_id:
            oidc_tenant_code = await _tenant_code_from_id(session, str(tenant_id))
        token_version = 0
        final_role = raw_role

    access, refresh = issue_token_pair(
        subject=subject,
        username=final_username,
        tenant_id=final_tenant_id,
        tenant_code=oidc_tenant_code,
        token_version=token_version,
        role=final_role,
        subject_type=subject_type,
    )
    # 透传 IdP 身份供审计/身份头注入（下游网关模式消费）
    request.state.oidc_claims = claims
    request.state.bound_user = bound is not None
    # v1.6.0：浏览器授权（Accept: text/html）→ 302 前端回调路由，令牌经 URL fragment
    # 传递（不落服务端日志/URL 历史）；脚本/API（Accept: */*）保持 JSON 契约。
    accept = request.headers.get("accept", "")
    if settings.oidc_frontend_redirect and "text/html" in accept:
        fragment = urllib.parse.urlencode(
            {
                "access_token": access,
                "refresh_token": refresh,
                "expires_in": settings.jwt_expire_seconds,
            }
        )
        return RedirectResponse(
            f"{settings.oidc_frontend_redirect}#{fragment}", status_code=302
        )
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_seconds,
        "refresh_token": refresh,
        "refresh_expires_in": settings.refresh_expire_seconds,
    }


async def _revoke_local_tokens(session: AsyncSession, subject: Any) -> int | None:
    """本地登出：主体 token_version 递增，使存量 access/refresh 立即失效.

    Returns:
        新 token_version；非本地主体（OIDC 直签字符串 sub）/行缺失/DB 不可达返回 None。
    """
    try:
        subject_id = int(subject)
    except (TypeError, ValueError):
        return None
    try:
        user_row = await session.get(User, subject_id)
        if user_row is None:
            return None
        user_row.token_version = (user_row.token_version or 0) + 1
        await session.commit()
        return user_row.token_version
    except Exception:  # noqa: BLE001 - DB 不可达时无法吊销，仍允许前端清除本地令牌
        logger.warning("oidc logout local revocation skipped", exc_info=True)
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


@router.post("/logout")
async def oidc_logout(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
    provider: str | None = Query(default=None),
    post_logout_redirect_uri: str | None = Query(default=None),
) -> dict:
    """OIDC 登出（v1.16.0）：本地吊销 + 可选 IdP 会话登出 URL.

    - 本地：主体 ``token_version`` 递增（存量 access/refresh 在强校验开启时立即失效）；
    - IdP：``provider`` 指定时按其 discovery 的 ``end_session_endpoint`` 返回登出 URL，
      未指定时在单 IdP ``oidc_*`` 已启用情形下复用同一能力；未声明则返回 null；
    - 前端凭据清除（localStorage）由调用方负责；本端点不写服务端白名单黑名单。

    Raises:
        BaseError: ``provider`` 未登记（400 PARAM_INVALID）；指定 Provider 但 OIDC 未启用（404）。
    """
    subject = user.get("id") if isinstance(user, dict) else None
    settings = get_settings()
    client: OIDCClient | None = None
    if (provider or "").strip():
        # 先解析 Provider（未登记/未启用 → 直接报错，不产生「已吊销但未登出」半态）
        client = _resolve_oidc_client(provider)
        if not client.enabled:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, "oidc not enabled")
    elif settings.oidc_enabled and settings.oidc_discovery_url and settings.oidc_client_id:
        client = _get_oidc_client()
    token_version = await _revoke_local_tokens(session, subject)
    idp_logout_url: str | None = None
    if client is not None:
        try:
            idp_logout_url = await client.build_logout_url(
                post_logout_redirect_uri=(post_logout_redirect_uri or "").strip()
            )
        except (OIDCError, httpx.HTTPError) as exc:
            # IdP 登出为尽力而为：本地吊销已生效，不得因 IdP 不可达而回滚登出
            logger.warning(
                "oidc idp logout url unavailable",
                extra={"error": str(exc) or exc.__class__.__name__},
            )
    logger.info(
        "oidc logout completed",
        extra={
            "subject": str(subject),
            "token_version": token_version,
            "provider": client.provider_name if client is not None else "",
        },
    )
    return {
        "logged_out": True,
        "token_version": token_version,
        "idp_logout_url": idp_logout_url,
    }
