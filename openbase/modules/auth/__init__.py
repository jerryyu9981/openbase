"""auth 模块：鉴权认证（JWT + RBAC + 登录/刷新 + 数据库用户）.

来源：OpenLLM app/services/auth_service.py（数据库用户校验模式）+ edgerouter/auth
（JWT/RBAC），适配 openbase core/db 与会话管理。
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_api_key_store, get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Role, User, user_role
from openbase.modules.auth.jwt import (
    decode_refresh_token,
    issue_token_pair,
)
from openbase.modules.auth.rbac import PermissionService, has_permission
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


# ---- v1.4.1 服务级 API Key（R-367，对齐完整方案 2.5 服务 Key ②） ----


class ApiKeyCreate(BaseModel):
    """服务 Key 创建请求."""

    name: str = Field(..., min_length=1, max_length=64)
    scope: dict = Field(default_factory=lambda: {"system": ["*"], "tenants": ["*"]})
    description: str = Field("", max_length=200)


class ApiKeyOut(BaseModel):
    """服务 Key 响应（创建时含明文，列表不回显）."""

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
    """服务 Key 权限校验（admin 通配放行 + RBAC 兜底）.

    Args:
        user: 当前用户（get_current_user 结果）。
        session: 数据库会话。
        permission_code: 所需权限点。

    Raises:
        BaseError: 无权限 → AUTH_FORBIDDEN。
    """
    if user.get("username") == "admin":
        return
    payload_permissions: list[str] = user.get("permissions") or []
    if has_permission(payload_permissions, permission_code):
        return
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user["id"])
    )
    if not has_permission(db_permissions, permission_code):
        raise BaseError(ErrorCode.AUTH_FORBIDDEN, f"missing permission: {permission_code}")


@router.post("/api-keys", response_model=ApiKeyOut)
async def create_api_key(
    payload: ApiKeyCreate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyOut:
    """签发服务级 API Key（需 auth:api-keys:manage）.

    返回明文 Key（仅此一次）；scope 限定可访问系统与租户。
    """
    await _check_api_key_permission(user, session, "auth:api-keys:manage")
    store = get_api_key_store()
    raw_key = store.create(
        name=payload.name,
        scope=payload.scope,
        description=payload.description,
    )
    record = store.list_keys()[-1]
    return ApiKeyOut(
        name=record["name"],
        scope=record["scope"],
        description=record["description"],
        created=record["created"],
        revoked=record["revoked"],
        key=raw_key,
    )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ApiKeyOut]:
    """服务 Key 列表（不回显明文，需 auth:api-keys:view）."""
    await _check_api_key_permission(user, session, "auth:api-keys:view")
    store = get_api_key_store()
    return [
        ApiKeyOut(
            name=record["name"],
            scope=record["scope"],
            description=record["description"],
            created=record["created"],
            revoked=record["revoked"],
        )
        for record in store.list_keys()
    ]


@router.delete("/api-keys/{raw_key}", response_model=dict[str, str])
async def revoke_api_key(
    raw_key: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """吊销服务 Key（需 auth:api-keys:manage）."""
    await _check_api_key_permission(user, session, "auth:api-keys:manage")
    get_api_key_store().revoke(raw_key)
    return {"revoked": raw_key}


__version__ = "1.1.0"
