"""auth 模块：鉴权认证（JWT + RBAC + 登录/刷新 + 数据库用户）.

来源：OpenLLM app/services/auth_service.py（数据库用户校验模式）+ edgerouter/auth
（JWT/RBAC），适配 openbase core/db 与会话管理。
"""

from __future__ import annotations

import asyncio
import logging
import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import NotificationPreference, Role, User, user_role
from openbase.modules.auth.jwt import (
    decode_refresh_token,
    issue_token_pair,
)
from openbase.modules.auth.service_keys import ServiceKeyService, public_record
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    SUBJECT_TYPE_AGENT,
    SUBJECT_TYPE_USER,
    assert_loginable,
)
from openbase.settings import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# v1.4.6（OB-AUTH-OIDC）：OIDC 统一认证路由独立前缀挂载（/api/v1/auth/oidc/*）
# 默认 oidc_enabled=false 时路由 404，不影响现有本地认证
try:
    from openbase.modules.auth.oidc import router as oidc_router

    extra_routers = [oidc_router]
except ImportError:  # 依赖缺失时降级，不阻塞 auth 模块装配
    extra_routers = []


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

    # v1.4.6（OB-AUTH-OIDC）：OIDC sub 为 IdP 侧字符串主体，id 支持 int（本地账号）/ str（OIDC）
    id: int | str
    username: str
    tenant_id: str | None = None
    permissions: list[str] = []
    # v1.9.7（R7）：个人设置页所需的资料字段
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None


class ProfileUpdateRequest(BaseModel):
    """个人资料更新请求（仅更新传入字段）."""

    display_name: str | None = Field(None, min_length=1, max_length=128)
    email: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)


class ChangePasswordRequest(BaseModel):
    """修改密码请求."""

    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


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
                    # U1 T1（RA-01/OB-1）：Principal 语义字段随用户一并读取（登录面分叉用）
                    "subject_type": user.subject_type,
                    "credential_type": user.credential_type,
                    "status_state": user.status_state,
                    "status_reason": user.status_reason,
                    "token_version": user.token_version,
                    "tenant_code": user.tenant_code,
                }
                from openbase.core.cache.redis_client import cache_set

                cache_set(f"user:{username}", data, ttl=300)
                return data
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("openbase.auth").warning(
                "user query failed, fallback to memory: %s", exc
            )
        return cls._memory_users.get(username)

    @classmethod
    async def get_roles(
        cls,
        user_id: int | str,
        session: AsyncSession,
        username: str = "",
    ) -> list[str]:
        """查询用户角色码列表（数据库优先；内存用户按用户名兜底）.

        v1.4.2 R-375：角色码用于 JWT Payload（role）与权限校验。
        """
        try:
            result = await session.execute(
                select(Role.code)
                .join(user_role, user_role.c.role_id == Role.id)
                .where(user_role.c.user_id == int(user_id))
            )
            codes = list(result.scalars().all())
            if codes:
                return codes
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("openbase.auth").warning(
                "role query failed, fallback to default: %s", exc
            )
        # 内存降级：admin 用户 → admin 角色；其余 → viewer
        return ["admin"] if username == "admin" else ["viewer"]


# ---- 路由 ----

logger = logging.getLogger(__name__)


def apply_login_tenant_policy(
    tenant_code: str | None,
    *,
    default_tenant_code: str = "",
    require_tenant_on_login: bool = False,
    is_production: bool = False,
) -> tuple[str | None, str | None]:
    """解析登录生效租户与兜底原因（R1）.

    顺序：已绑定 → 原值；未绑定 → 显式默认租户兜底；否则按环境策略处理。

    Args:
        tenant_code: 由 users.tenant_id 解析出的租户 code（可能为空）。
        default_tenant_code: 未绑定时的显式兜底租户码（空 = 不兜底）。
        require_tenant_on_login: 生产是否强制要求租户声明。
        is_production: 当前是否生产环境。

    Returns:
        (effective_tenant_code, fallback_reason)；
        fallback_reason ∈ {None, "default_config", "unbound"}。

    Raises:
        BaseError: 生产 + 强制开关开启且无任何租户来源（AUTH_FORBIDDEN，
            detail.reason=tenant_unbound）。
    """
    if tenant_code:
        return tenant_code, None
    if default_tenant_code:
        return default_tenant_code, "default_config"
    if require_tenant_on_login and is_production:
        raise BaseError(
            ErrorCode.AUTH_FORBIDDEN,
            "tenant identity required for login",
            detail={"reason": "tenant_unbound"},
        )
    return None, "unbound"


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

    # U1 T1/T2（RA-01/RA-02，设计草案 §3.2/§4.1）：登录面按 subject_type 分叉 + 状态门禁。
    # agent 无人工登录面（0 可达登录路径）且先于密码校验；user 须 status_state=active
    # （suspended/deactivated/purged/provisioned 即时拒签，AUTH_PRINCIPAL_DISABLED）。
    subject_type = user.get("subject_type") or SUBJECT_TYPE_USER
    if subject_type != SUBJECT_TYPE_USER:
        raise BaseError(
            ErrorCode.AUTH_FORBIDDEN, "agent subjects cannot use interactive login"
        )
    status_state = user.get("status_state") or STATUS_STATE_ACTIVE
    if not assert_loginable(subject_type, status_state):
        raise BaseError(
            ErrorCode.AUTH_PRINCIPAL_DISABLED,
            "principal is not active",
            detail={"status_state": status_state},
        )

    if not await asyncio.to_thread(verify_password, req.password, user["password_hash"]):
        raise BaseError(ErrorCode.AUTH_UNAUTHORIZED, "invalid username or password")

    # v1.4.2 R-375：JWT Payload 扩展 org_id + role（OpenMemory 双层认证前置）
    roles = await UserService.get_roles(
        user["id"], session, user.get("username", "")
    )
    role = roles[0] if roles else "viewer"
    tenant_value = user.get("tenant_id")
    # U1 T2（RA-02/OB-4）：login 无条件全量注入 tenant_code（按 tenant_id 查 tenants.code），
    # 与 refresh/OIDC 共用单一签发器 issue_token_pair（草案 §6.1/§6.3）。
    tenant_code = user.get("tenant_code")
    if not tenant_code:
        tenant_code = await resolve_tenant_code(tenant_value, session)
    # R1：登录期租户策略（已绑定优先；未绑定按显式兜底/环境门禁处理）
    tenant_code, tenant_fallback = apply_login_tenant_policy(
        tenant_code,
        default_tenant_code=settings.default_tenant_code,
        require_tenant_on_login=settings.require_tenant_on_login,
        is_production=str(settings.env).lower() == "production",
    )
    if tenant_fallback == "default_config":
        logger.warning(
            "login tenant fallback applied",
            extra={
                "username": user.get("username"),
                "tenant_code": tenant_code,
                "reason": tenant_fallback,
            },
        )
    elif tenant_fallback == "unbound":
        logger.warning(
            "login without tenant binding",
            extra={"username": user.get("username"), "env": settings.env},
        )
    subject_type = user.get("subject_type") or SUBJECT_TYPE_USER
    token_version = user.get("token_version")
    if token_version is None:
        token_version = 0
    access, refresh = issue_token_pair(
        subject=str(user["id"]),
        username=user.get("username", ""),
        tenant_id=tenant_value,
        tenant_code=tenant_code,
        token_version=token_version,
        role=role,
        subject_type=subject_type,
    )
    return TokenResponse(
        access_token=access,
        expires_in=settings.jwt_expire_seconds,
        refresh_token=refresh,
        refresh_expires_in=settings.refresh_expire_seconds,
    )


async def resolve_tenant_code(
    tenant_value: int | str | None, session: AsyncSession
) -> str | None:
    """按 tenants.id 解析租户 code（P3.1；U1 T1 抽为共享函数，供 login/refresh/OIDC/迁移复用）.

    数字形态（tenants.id）→ 查 tenants.code；非数字（IdP 侧 code 直传）原样返回。
    DB 不可达/无匹配返回 None（调用方不追加 tenant_code claim，向后兼容）。

    Args:
        tenant_value: JWT tenant_id 值。
        session: DB 会话。

    Returns:
        tenants.code 字符串；解析失败返回 None。
    """
    from openbase.core.models import Tenant

    if tenant_value is None or tenant_value == "":
        return None
    code_text = str(tenant_value)
    if not code_text.isdigit():
        return code_text
    try:
        result = await session.execute(
            select(Tenant.code).where(Tenant.id == int(code_text))
        )
        return result.scalar_one_or_none()
    except Exception:  # noqa: BLE001 - DB 不可达降级（不追加 claim）
        return None


# 向后兼容别名：旧调用方（OIDC 等）沿用私有名
_resolve_tenant_code = resolve_tenant_code


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """刷新 Token：校验 refresh token 后签发新 access/refresh.

    U1 T2（RA-02/OB-4）刷新链闭环：
    - 全量 claim（修 fidelity）：新 refresh token 自带 username/role/tenant_code/
      sub_type/tvn，刷新时直读直签（§6.1）；
    - v0 存量 refresh（仅 sub/tenant_id）经主体行补齐 tenant_code + 版本升级（§6.2）；
    - 签发侧状态门禁：suspended/deactivated/provisioned 主体 refresh 一律拒绝（即时拒签），
      agent 无刷新链（AUTH_FORBIDDEN）；DB 不可达/非数字 sub（OIDC 直签）保持降级放行。
    """
    settings = get_settings()
    payload = decode_refresh_token(req.refresh_token)
    if payload is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "invalid refresh token")

    subject = payload.get("sub")
    if subject is None:
        raise BaseError(ErrorCode.AUTH_TOKEN_INVALID, "refresh token missing subject")

    # U1 T1/T2：刷新链主体查询（数字 sub → DB 主体；DB 不可达降级保持既有行为）。
    subject_row: User | None = None
    if str(subject).isdigit():
        try:
            subject_row = await session.get(User, int(subject))
        except Exception:  # noqa: BLE001 - DB 不可达兼容内存/降级用户
            subject_row = None
    if subject_row is not None and (subject_row.subject_type or SUBJECT_TYPE_USER) == SUBJECT_TYPE_AGENT:
        raise BaseError(ErrorCode.AUTH_FORBIDDEN, "agent subjects cannot use refresh")

    if subject_row is not None:
        # 状态门禁：仅 active 可续签（suspended/deactivated → 即时拒签）
        if subject_row.status_state != STATUS_STATE_ACTIVE:
            raise BaseError(
                ErrorCode.AUTH_PRINCIPAL_DISABLED,
                "principal is not active",
                detail={"status_state": subject_row.status_state},
            )
        subject_type = subject_row.subject_type or SUBJECT_TYPE_USER
        username = subject_row.username or payload.get("username", "")
        tenant_value = payload.get("tenant_id")
        if not tenant_value and subject_row.tenant_id:
            tenant_value = str(subject_row.tenant_id)
        # tenant_code：payload（新 refresh 自带）> 主体行冗余列 > tenants.code 解析
        tenant_code = payload.get("tenant_code") or subject_row.tenant_code
        if not tenant_code:
            tenant_code = await resolve_tenant_code(tenant_value, session)
        token_version = subject_row.token_version or 0
        roles = await UserService.get_roles(subject_row.id, session, username)
        role = roles[0] if roles else (payload.get("role") or "viewer")
    else:
        # OIDC 直签 / DB 降级形态：以 payload claims 直读直签（v0 无则按缺省）
        subject_type = payload.get("sub_type") or SUBJECT_TYPE_USER
        username = payload.get("username", "")
        tenant_value = payload.get("tenant_id")
        tenant_code = payload.get("tenant_code")
        if not tenant_code:
            tenant_code = await resolve_tenant_code(tenant_value, session)
        token_version = payload.get("tvn") or 0
        role = payload.get("role") or "viewer"

    access, refresh_token = issue_token_pair(
        subject=subject,
        username=username,
        tenant_id=tenant_value,
        tenant_code=tenant_code,
        token_version=token_version,
        role=role,
        subject_type=subject_type,
    )
    return TokenResponse(
        access_token=access,
        expires_in=settings.jwt_expire_seconds,
        refresh_token=refresh_token,
        refresh_expires_in=settings.refresh_expire_seconds,
    )


async def _load_profile_user(session: AsyncSession, user_id: int | str) -> User | None:
    """按当前主体 ID 加载 users 行（OIDC 字符串主体可能无本地行）."""
    try:
        numeric_id = int(user_id)
    except (TypeError, ValueError):
        return None
    return await session.get(User, numeric_id)


async def _build_me_response(session: AsyncSession, user: dict) -> MeResponse:
    """构建 /auth/me 响应（权限 + 资料字段）."""
    from openbase.modules.auth.rbac import is_superadmin, resolve_user_permissions

    permissions = await resolve_user_permissions(session, user)
    # E0-5（R5）：超管（system:superadmin / * 通配）兜底通配，前端全模块可见
    if is_superadmin(permissions) and "*" not in permissions:
        permissions = ["*", *permissions]
    row = await _load_profile_user(session, user["id"])
    return MeResponse(
        id=user["id"],
        username=user["username"],
        # F-8（2026-10-16）：出参口径统一为字符串。JWT 通道的 tenant_id 来自 claim（str），
        # 而 agent 密钥通道（resolve_agent_principal）返回 DB 的 int，直接透传给
        # `tenant_id: str | None` 会触发 pydantic v2 校验失败 → 500（绑租户主体必现）。
        tenant_id=(
            str(user.get("tenant_id")) if user.get("tenant_id") is not None else None
        ),
        permissions=permissions,
        display_name=row.display_name if row else None,
        email=row.email if row else None,
        phone=row.phone if row else None,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MeResponse:
    """当前用户信息（含权限标识与资料字段）.

    供统一前端登录后拉取用户与权限（v1.2.0 统一前端契约）。
    """
    return await _build_me_response(session, user)


@router.put("/me", response_model=MeResponse)
async def update_me(
    payload: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MeResponse:
    """更新当前用户资料（昵称/邮箱/手机号）."""
    row = await _load_profile_user(session, user["id"])
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, "用户不存在")

    fields = payload.model_dump(exclude_unset=True)
    if "email" in fields and fields["email"]:
        if not EMAIL_PATTERN.match(fields["email"]):
            raise BaseError(ErrorCode.PARAM_INVALID, "邮箱格式不正确")
    if "display_name" in fields:
        row.display_name = fields["display_name"]
    if "email" in fields:
        row.email = fields["email"] or None
    if "phone" in fields:
        row.phone = fields["phone"] or None

    await session.commit()
    return await _build_me_response(session, user)


@router.post("/change-password", response_model=dict[str, str])
async def change_password(
    payload: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """修改当前用户密码（校验旧密码；新密码需含字母与数字）."""
    row = await _load_profile_user(session, user["id"])
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, "用户不存在")
    if not verify_password(payload.old_password, row.password_hash):
        raise BaseError(ErrorCode.PARAM_INVALID, "旧密码不正确")
    if payload.new_password == payload.old_password:
        raise BaseError(ErrorCode.PARAM_INVALID, "新密码不能与旧密码相同")
    if not PASSWORD_PATTERN.match(payload.new_password):
        raise BaseError(ErrorCode.PARAM_INVALID, "密码至少 8 位，且需同时包含字母和数字")

    row.password_hash = hash_password(payload.new_password)
    await session.commit()
    return {"message": "密码已修改"}


# ---- v1.10.1（OB-01）用户通知偏好 ----


DEFAULT_NOTIFICATION_EVENTS: dict[str, bool] = {
    "alert": True,
    "approval": True,
    "system": True,
}
NOTIFICATION_WEBHOOK_PATTERN = re.compile(r"^https?://\S+$")


class NotificationPreferencePayload(BaseModel):
    """通知偏好请求/响应."""

    in_app: bool = True
    email: bool = False
    webhook: bool = False
    webhook_url: str | None = Field(None, max_length=512)
    events: dict[str, bool] = Field(
        default_factory=lambda: dict(DEFAULT_NOTIFICATION_EVENTS)
    )


def _numeric_user_id(user: dict) -> int | None:
    """解析本地用户主键（OIDC 字符串主体可能无本地行）."""
    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


def _notification_payload_from_row(
    row: NotificationPreference | None,
) -> NotificationPreferencePayload:
    """行 → 响应（无行时返回默认值）."""
    if row is None:
        return NotificationPreferencePayload()
    return NotificationPreferencePayload(
        in_app=row.in_app,
        email=row.email,
        webhook=row.webhook,
        webhook_url=row.webhook_url,
        events={**DEFAULT_NOTIFICATION_EVENTS, **(row.events or {})},
    )


@router.get(
    "/notification-preferences", response_model=NotificationPreferencePayload
)
async def get_notification_preferences(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferencePayload:
    """读取当前用户通知偏好（无记录时返回默认值）."""
    user_id = _numeric_user_id(user)
    if user_id is None:
        return NotificationPreferencePayload()
    row = await session.get(NotificationPreference, user_id)
    return _notification_payload_from_row(row)


@router.put(
    "/notification-preferences", response_model=NotificationPreferencePayload
)
async def update_notification_preferences(
    payload: NotificationPreferencePayload,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferencePayload:
    """保存当前用户通知偏好（upsert，幂等）."""
    user_id = _numeric_user_id(user)
    if user_id is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, "用户不存在")

    unknown_events = sorted(set(payload.events) - set(DEFAULT_NOTIFICATION_EVENTS))
    if unknown_events:
        raise BaseError(
            ErrorCode.PARAM_INVALID, f"未知通知事件: {', '.join(unknown_events)}"
        )

    webhook_url = (payload.webhook_url or "").strip() or None
    if payload.webhook and not (
        webhook_url and NOTIFICATION_WEBHOOK_PATTERN.match(webhook_url)
    ):
        raise BaseError(
            ErrorCode.PARAM_INVALID, "启用 Webhook 时必须填写 http(s) 回调地址"
        )
    if webhook_url and not NOTIFICATION_WEBHOOK_PATTERN.match(webhook_url):
        raise BaseError(ErrorCode.PARAM_INVALID, "Webhook 地址需以 http(s):// 开头")

    events = {
        key: bool(payload.events.get(key, default))
        for key, default in DEFAULT_NOTIFICATION_EVENTS.items()
    }

    row = await session.get(NotificationPreference, user_id)
    if row is None:
        row = NotificationPreference(user_id=user_id)
        session.add(row)
    row.in_app = payload.in_app
    row.email = payload.email
    row.webhook = payload.webhook
    row.webhook_url = webhook_url
    row.events = events

    await session.commit()
    return NotificationPreferencePayload(
        in_app=row.in_app,
        email=row.email,
        webhook=row.webhook,
        webhook_url=row.webhook_url,
        events=events,
    )


# ---- v1.4.1 服务级 API Key（R-367，对齐完整方案 2.5 服务 Key ②） ----


class ApiKeyCreate(BaseModel):
    """服务 Key 创建请求."""

    name: str = Field(..., min_length=1, max_length=64)
    scope: dict = Field(default_factory=lambda: {"system": ["*"], "tenants": ["*"]})
    description: str = Field("", max_length=200)


class ApiKeyOut(BaseModel):
    """服务 Key 响应（创建时含明文，列表不回显）."""

    id: str = ""
    name: str
    scope: dict
    description: str = ""
    created: float
    revoked: bool = False
    key: str | None = None


# 服务 Key 权限点（auth:api-keys:manage/view）
AUTH_API_KEY_PERMISSIONS = ("auth:api-keys:manage", "auth:api-keys:view")


async def _check_api_key_permission(
    user: dict, session: AsyncSession, permission_code: str
) -> None:
    """服务 Key 权限校验（E0-5：显式超管权限点 + RBAC，无用户名硬编码）.

    Args:
        user: 当前用户（get_current_user 结果）。
        session: 数据库会话。
        permission_code: 所需权限点。

    Raises:
        BaseError: 无权限 → AUTH_FORBIDDEN。
    """
    from openbase.modules.auth.rbac import ensure_user_permission

    await ensure_user_permission(
        session,
        user,
        permission_code,
        error_code=ErrorCode.AUTH_FORBIDDEN,
    )


@router.post("/api-keys", response_model=ApiKeyOut)
async def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyOut:
    """签发服务级 API Key（需 auth:api-keys:manage）.

    返回明文 Key（仅此一次）；scope 限定可访问系统与租户。
    v1.5：签发记录落 ``service_api_keys`` 表，重启后仍有效（原内存态失效缺陷修复）。
    E0-4：同事务写审计（key_id/name/scope/操作人/request_id）。
    """
    await _check_api_key_permission(user, session, "auth:api-keys:manage")
    raw_key, record = await ServiceKeyService.issue(
        session,
        name=payload.name,
        scope=payload.scope,
        description=payload.description,
        created_by=int(user["id"]) if str(user.get("id", "")).isdigit() else None,
        request_id=getattr(request.state, "request_id", None),
    )
    await session.commit()
    return ApiKeyOut(
        id=record.key_id,
        name=record.name,
        scope=record.scope,
        description=record.description,
        created=record.created_at.timestamp(),
        revoked=False,
        key=raw_key,
    )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ApiKeyOut]:
    """服务 Key 列表（不回显明文，需 auth:api-keys:view）."""
    await _check_api_key_permission(user, session, "auth:api-keys:view")
    records = await ServiceKeyService.list_keys(session)
    return [ApiKeyOut(**public_record(record)) for record in records]


@router.delete("/api-keys/by-id/{key_id}", response_model=dict[str, str])
async def revoke_api_key_by_id(
    key_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """按稳定标识吊销服务 Key（v1.9.2；需 auth:api-keys:manage）.

    列表已回显 ``id``，前端无需持有明文即可吊销；保留原「按明文 Key」端点
    以兼容既有调用方。
    E0-4：同事务写审计（操作人/request_id；不含明文）。
    """
    await _check_api_key_permission(user, session, "auth:api-keys:manage")
    operator_id = int(user["id"]) if str(user.get("id", "")).isdigit() else None
    if not await ServiceKeyService.revoke_by_id(
        session,
        key_id,
        operator_id=operator_id,
        request_id=getattr(request.state, "request_id", None),
    ):
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"api key not found: {key_id}")
    await session.commit()
    return {"revoked": key_id}


@router.delete("/api-keys/{raw_key}", response_model=dict[str, str])
async def revoke_api_key(
    raw_key: str,
    request: Request,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """吊销服务 Key（需 auth:api-keys:manage）.

    E0-4：同事务写审计（操作人/request_id；不含明文）。
    """
    await _check_api_key_permission(user, session, "auth:api-keys:manage")
    operator_id = int(user["id"]) if str(user.get("id", "")).isdigit() else None
    await ServiceKeyService.revoke_by_raw(
        session,
        raw_key,
        operator_id=operator_id,
        request_id=getattr(request.state, "request_id", None),
    )
    await session.commit()
    return {"revoked": raw_key}


__version__ = "1.1.0"
