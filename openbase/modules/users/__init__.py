"""users 模块：用户管理 CRUD（v1.4.2 R-375）.

提供用户创建/列表/详情/启停/角色分配管理 API（/api/v1/users），数据落库
（users 表 + user_role 关联），向后兼容既有 login/refresh/me 链路。
权限：admin 通配放行 + RBAC 兜底（PermissionService 模式）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Role, User, user_role
from openbase.modules.auth import hash_password
from openbase.modules.auth.rbac import PermissionService, has_permission

logger = logging.getLogger("openbase.users")

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# 用户管理权限点
USER_MANAGE_PERMISSION = "users:manage"
USER_VIEW_PERMISSION = "users:view"

# 允许分配的角色码（受控枚举）
ALLOWED_ROLES = ("admin", "org_admin", "org_member", "viewer")


# ---- Schemas ----


class UserCreate(BaseModel):
    """创建用户请求."""

    username: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=128)
    email: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    role: str = Field("viewer", description="初始角色码")
    tenant_id: int | None = Field(None, description="所属租户 ID")


class UserUpdate(BaseModel):
    """更新用户请求（启停/基础字段）."""

    status: int | None = Field(None, ge=0, le=1, description="1=启用 0=禁用")
    display_name: str | None = Field(None, max_length=128)
    email: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)


class UserRoleUpdate(BaseModel):
    """角色分配请求."""

    role: str = Field(..., description="角色码（admin/org_admin/org_member/viewer）")


class UserOut(BaseModel):
    """用户响应（不回显密码）."""

    id: int
    username: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    status: int
    tenant_id: int | None = None
    roles: list[str] = []


# ---- 权限依赖 ----


async def _require_user_manage(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """用户管理权限校验（admin 通配放行 + RBAC 兜底）."""
    if user.get("username") == "admin":
        return user
    payload_permissions: list[str] = user.get("permissions") or []
    if has_permission(payload_permissions, USER_MANAGE_PERMISSION):
        return user
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user["id"])
    )
    if has_permission(db_permissions, USER_MANAGE_PERMISSION):
        return user
    raise BaseError(ErrorCode.PERM_FORBIDDEN, f"missing permission: {USER_MANAGE_PERMISSION}")


async def _require_user_view(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """用户查看权限校验（admin 通配放行 + RBAC 兜底）."""
    if user.get("username") == "admin":
        return user
    payload_permissions: list[str] = user.get("permissions") or []
    if has_permission(payload_permissions, USER_VIEW_PERMISSION):
        return user
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user["id"])
    )
    if has_permission(db_permissions, USER_VIEW_PERMISSION):
        return user
    raise BaseError(ErrorCode.PERM_FORBIDDEN, f"missing permission: {USER_VIEW_PERMISSION}")


# ---- Service 辅助 ----


def _to_out(user: User, role_codes: list[str]) -> UserOut:
    """模型 → 响应 DTO（不回显密码哈希）."""
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        status=user.status,
        tenant_id=user.tenant_id,
        roles=role_codes,
    )


async def _role_codes_for(session: AsyncSession, user: User) -> list[str]:
    """查询用户角色码列表."""
    result = await session.execute(
        select(Role.code).join(user_role, user_role.c.role_id == Role.id).where(user_role.c.user_id == user.id)
    )
    return list(result.scalars().all())


async def _resolve_role(session: AsyncSession, role_code: str) -> Role:
    """按角色码解析角色（受控枚举内），不存在报业务错误."""
    if role_code not in ALLOWED_ROLES:
        raise BaseError(ErrorCode.PARAM_INVALID, f"invalid role: {role_code}")
    result = await session.execute(select(Role).where(Role.code == role_code))
    role = result.scalar_one_or_none()
    if role is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"role not found: {role_code}")
    return role


# ---- 路由 ----


@router.post("", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    user: dict = Depends(_require_user_manage),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """创建用户（密码哈希存储 + 角色关联）."""
    existing = await session.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none() is not None:
        raise BaseError(ErrorCode.BIZ_CONFLICT, f"username already exists: {payload.username}")

    new_user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
        status=1,
        tenant_id=payload.tenant_id,
    )
    session.add(new_user)
    await session.flush()

    role = await _resolve_role(session, payload.role)
    await session.execute(user_role.insert().values(user_id=new_user.id, role_id=role.id))
    await session.commit()
    await session.refresh(new_user)

    logger.info("user created", extra={"user_id": new_user.id, "operator": user.get("username")})
    return _to_out(new_user, [payload.role])


@router.get("", response_model=list[UserOut])
async def list_users(
    user: dict = Depends(_require_user_view),
    session: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    """用户列表（按 id 升序）."""
    result = await session.execute(select(User).order_by(User.id))
    rows = result.scalars().all()
    out: list[UserOut] = []
    for row in rows:
        roles = await _role_codes_for(session, row)
        out.append(_to_out(row, roles))
    return out


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    user: dict = Depends(_require_user_view),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """用户详情."""
    row = await session.get(User, user_id)
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"user not found: {user_id}")
    roles = await _role_codes_for(session, row)
    return _to_out(row, roles)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    user: dict = Depends(_require_user_manage),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """更新用户（启停/基础字段）."""
    row = await session.get(User, user_id)
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"user not found: {user_id}")
    if payload.status is not None:
        row.status = payload.status
    if payload.display_name is not None:
        row.display_name = payload.display_name
    if payload.email is not None:
        row.email = payload.email
    if payload.phone is not None:
        row.phone = payload.phone
    await session.commit()
    await session.refresh(row)
    roles = await _role_codes_for(session, row)
    return _to_out(row, roles)


@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    user: dict = Depends(_require_user_manage),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """删除用户（停用语义：status=0，保留数据）."""
    row = await session.get(User, user_id)
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"user not found: {user_id}")
    row.status = 0
    await session.commit()
    return {"code": 0, "user_id": user_id, "status": 0}


@router.put("/{user_id}/role", response_model=UserOut)
async def assign_role(
    user_id: int,
    payload: UserRoleUpdate,
    user: dict = Depends(_require_user_manage),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """分配角色（受控枚举内替换现有角色关联）."""
    row = await session.get(User, user_id)
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"user not found: {user_id}")
    role = await _resolve_role(session, payload.role)
    await session.execute(user_role.delete().where(user_role.c.user_id == user_id))
    await session.execute(user_role.insert().values(user_id=user_id, role_id=role.id))
    await session.commit()
    await session.refresh(row)
    return _to_out(row, [payload.role])


__version__ = "1.0.0"
