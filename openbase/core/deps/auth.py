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
        # OB-AUTH-OIDC：OIDC 授权码流程端点公开（回调后签发统一 JWT）
        "/api/v1/auth/oidc",
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
        # U1 T1（RA-01/OB-1）：sk-agent-* 为 agent 主体凭据（无 JWT 面）。中间件放行，
        # 由端点依赖 get_current_user 的 agent 校验器完成认证（fail-closed：无效即 401）。
        if token.startswith("sk-agent-"):
            return await call_next(request)
        payload = decode_access_token(token)
        if payload is None or payload.get("sub") is None:
            return self._unauthorized("invalid or expired token")

        # U1 T3（K04，方案 a）：中间件与依赖层共用同一主体验证器 verify_principal，
        # 每请求校验主体状态（默认生效）+ token 版本（enforce_token_version 开关，
        # 默认关，两段式发布第二段开启），消除「仅验签不验状态」路径（设计草案 §5.1）。
        try:
            await self._verify_request_principal(request, payload)
        except BaseError as exc:
            return self._error_response(exc)

        # 中间件不修改用户上下文（依赖层负责用户信息），此处仅做门禁
        return await call_next(request)

    async def _verify_request_principal(
        self, request: Request, payload: dict
    ) -> None:
        """以请求级短会话执行共享主体验证（主体验证器共用，避免依赖层双读）.

        OIDC 直签/外域主体（sub 非数字）与 DB 不可达由 verify_principal 内部放行；
        仅需开 DB 会话的数值型本地主体场景才真正建立会话（降级直签场景零 DB 开销）。
        """
        subject_text = str(payload.get("sub") or "")
        if not subject_text.isdigit():
            return
        from openbase.core.db.session import get_session_factory
        from openbase.modules.identity import verification as principal_verification

        session_factory = get_session_factory()
        async with session_factory() as session:
            snapshot = await principal_verification.verify_principal(session, payload)
        if snapshot is not None:
            request.state.verified_principal = snapshot

    @staticmethod
    def _error_response(exc: BaseError) -> JSONResponse:
        """统一错误响应（{code, message, detail, request_id}，与异常处理器同构）."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code.value,
                "message": exc.message,
                "detail": exc.detail,
                "request_id": f"req-{uuid.uuid4().hex[:12]}",
            },
        )

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
    # U1 T1（RA-01/OB-1）：agent 主体无 JWT 面，凭据为 sk-agent-* 密钥。
    # 走 agent 密钥校验器（DB 校验 key_hash/状态/域；无效或吊销 → 401/403 BaseError）。
    if token.startswith("sk-agent-"):
        from openbase.modules.identity.agent_keys import resolve_agent_principal

        return await resolve_agent_principal(session, token)
    payload = decode_access_token(token)
    if payload is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "token missing subject")

    # U1 T3（K04，方案 a）：依赖层与中间件共用同一主体验证器 verify_principal——
    # 每请求校验主体状态（默认生效）+ token 版本（enforce_token_version 开关默认关）。
    # 消灭「仅验签不验状态」路径：仅验签通过的 JWT 不再直接进入端点（草案 §5.1/§11 T3-6）。
    from openbase.modules.identity import verification as principal_verification

    await principal_verification.verify_principal(session, payload)

    # 用户信息以 payload 中精简字段返回，详细查询由 auth 模块服务提供
    # permissions 透传（含 "*" 通配），供 require_permission 直接校验
    # v1.4.6（OB-AUTH-OIDC）：OIDC sub 为非数字字符串（IdP 侧主体），保留原值，
    # 仅对本地账号（数字 id）做 int 转换，避免 ValueError
    try:
        user_int_id = int(user_id)
    except (TypeError, ValueError):
        user_int_id = None
    # U1 T4（草案 §7.3）：返回主体上下文（sub_type/tenant_code/role/委托块），
    # 委托令牌含 on_behalf_of——主体验证器已在返回快照后完成逐跳重校验（403 拦截）。
    from openbase.modules.identity.delegation import normalize_on_behalf_of

    delegated = None
    try:
        delegated = normalize_on_behalf_of(payload.get("on_behalf_of"))
    except BaseError:
        # 结构畸形已在 verify_principal（逐跳重校验）拦截，此处兜底置 None
        delegated = None
    return {
        "id": user_int_id if user_int_id is not None else str(user_id),
        "username": payload.get("username", ""),
        "tenant_id": payload.get("tenant_id"),
        "tenant_code": payload.get("tenant_code"),
        "subject_type": payload.get("sub_type", "user"),
        "role": payload.get("role"),
        "permissions": payload.get("permissions") or [],
        "on_behalf_of": delegated,
        "delegated": (
            {
                "subject_id": delegated["subject_id"],
                "subject_type": delegated["subject_type"],
                "tenant_code": delegated["tenant_code"],
                "role": delegated["role"],
            }
            if delegated is not None
            else None
        ),
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


async def get_proxy_identity(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """/proxy 通道双通道认证（R-367 AC-367-2）：JWT 优先 + 服务 Key 回退.

    认证通道判定：
    - X-API-Key 头存在 → 服务 Key 认证（校验路径 system scope）。
    - Authorization: Bearer <ob_k_...> → 服务 Key 认证。
    - 其余（Bearer JWT / 无头）→ JWT 用户认证（get_current_user，U1 T3 经
      依赖注入的真实会话执行 verify_principal 状态/版本门禁）。
    """
    x_api_key = request.headers.get("X-API-Key")
    authorization = request.headers.get("Authorization", "")
    bearer = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    if x_api_key or (bearer and bearer.startswith("ob_k_")):
        return require_api_key(request=request)
    return await get_current_user(request, session)
