"""RBAC 权限矩阵：配置驱动权限管理器 + 数据库权限矩阵 + 权限点校验依赖.

来源：OpenLLM backend/app/edgerouter/auth/rbac.py（RBACManager 配置驱动模式抽取，
适配 openbase 统一错误与配置约定）。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Permission, Role, role_permission, user_role

logger = logging.getLogger("openbase.auth.rbac")

__all__ = [
    "BUILTIN_ROLE_PERMISSIONS",
    "SUPERADMIN_PERMISSION",
    "ensure_user_permission",
    "has_permission",
    "is_superadmin",
    "require_permission",
    "resolve_user_permissions",
    "tenant_filter_code",
    "PermissionStore",
    "PermissionService",
]

# E0-5（R5/P0-5）：显式超管权限点。取代 ``username == "admin"`` 硬编码通配：
# 管理面统一按权限点判定，超管身份来自角色/权限矩阵（可审计、可改名、可多管理员）。
SUPERADMIN_PERMISSION = "system:superadmin"

# 内置角色锚点：DB 权限矩阵不可用（内存降级/未初始化库）时，按 JWT ``role`` claim
# 映射显式权限点。admin 是内置系统角色（DB 种子中持 ``*``），此处保持等价语义。
BUILTIN_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [SUPERADMIN_PERMISSION],
}


class PermissionStore:
    """权限存储：角色-权限映射 + 用户-角色映射.

    来源：OpenLLM edgerouter/auth/rbac.py（RoleConfig/RBACManager 模式抽取）。
    v1.0.0 最小实现：内存映射，支持配置注入与热加载钩子；生产接数据库
    （users/roles/permissions 表 + user_role/role_permission 关联）。
    """

    _role_permissions: dict[str, list[str]] = {}  # role_code -> [permission codes]
    _user_roles: dict[str, list[str]] = {}  # user_id -> [role codes]

    @classmethod
    def configure_roles(cls, role_permissions: dict[str, list[str]]) -> None:
        """配置角色-权限映射（模块初始化或热加载时调用）.

        Args:
            role_permissions: {role_code: [permission codes]}。
        """
        cls._role_permissions = {k: list(v) for k, v in role_permissions.items()}

    @classmethod
    def assign_role(cls, user_id: str, role_code: str) -> None:
        """为用户分配角色."""
        cls._user_roles.setdefault(user_id, []).append(role_code)

    @classmethod
    def permissions_for(cls, user_id: str) -> list[str]:
        """计算用户全部权限点（角色权限并集）.

        Args:
            user_id: 用户 ID。

        Returns:
            权限点列表。
        """
        result: list[str] = []
        for role in cls._user_roles.get(user_id, []):
            result.extend(cls._role_permissions.get(role, []))
        return list(dict.fromkeys(result))  # 去重保序


class PermissionService:
    """权限矩阵数据库服务：用户权限点查询（user → role → permission）.

    SQL 链：user_role → roles → role_permission → permissions。
    数据库不可用时回退 PermissionStore 内存映射。
    """

    @classmethod
    async def permissions_for(cls, session: AsyncSession, user_id: int) -> list[str]:
        """查询用户数据库权限点（含 admin 通配）.

        Args:
            session: 数据库会话。
            user_id: 用户 ID。

        Returns:
            权限点列表（含 * 通配）。
        """
        from sqlalchemy import select

        stmt = (
            select(Permission.code)
            .join(role_permission, role_permission.c.permission_id == Permission.id)
            .join(Role, Role.id == role_permission.c.role_id)
            .join(user_role, user_role.c.role_id == Role.id)
            .where(user_role.c.user_id == user_id)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return list(dict.fromkeys(rows))

    @classmethod
    async def permissions_for_with_fallback(cls, session: AsyncSession, user_id: str) -> list[str]:
        """数据库优先 + 内存回退的用户权限查询."""
        try:
            db_perms = await cls.permissions_for(session, int(user_id))
            if db_perms:
                return db_perms
        except Exception as exc:  # noqa: BLE001
            logger.debug("rbac db query failed, fallback store: %s", exc)
        return PermissionStore.permissions_for(user_id)


def require_permission(
    permission_code: str,
    error_code: ErrorCode = ErrorCode.AUTH_FORBIDDEN,
) -> Callable[..., Any]:
    """生成 RBAC 权限校验依赖.

    校验链（来源: OpenLLM RBACManager 模式）：
    1. JWT payload 携带权限（轻量路径，透传场景）
    2. PermissionStore 角色-权限映射查询（用户-角色-权限矩阵）

    用法::

        @router.get("/users", dependencies=[Depends(require_permission("user:list"))])
        async def list_users(): ...

    Args:
        permission_code: 所需权限点（如 "user:list"）。
        error_code: 权限不足时抛出的错误码。默认为 ``AUTH_FORBIDDEN``（历史契约）；
            v1.4.6 起日志/模块端点显式传 ``PERM_403`` 对齐设计 §5。

    Returns:
        FastAPI 依赖函数。
    """

    async def _checker(
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> dict:
        user_id = str(user.get("id", ""))

        # 路径 1：payload 携带权限（透传/轻量场景）
        payload_permissions: list[str] = user.get("permissions") or []
        if has_permission(payload_permissions, permission_code):
            return user

        # 路径 2：数据库权限矩阵查询（user → role → permission，含 * 通配）
        db_permissions = await PermissionService.permissions_for_with_fallback(session, user_id)
        if has_permission(db_permissions, permission_code):
            return user

        raise BaseError(
            error_code,
            f"missing permission: {permission_code}",
        )

    return _checker


def has_permission(permissions: list[str], code: str) -> bool:
    """工具函数：权限列表是否包含指定权限点（支持 * 通配）.

    Args:
        permissions: 用户权限点列表。
        code: 目标权限点。

    Returns:
        是否授权。
    """
    return "*" in permissions or code in permissions


def is_superadmin(permissions: list[str] | None) -> bool:
    """是否持显式超管权限点（``system:superadmin`` 或通配 ``*``）."""
    granted = permissions or []
    return SUPERADMIN_PERMISSION in granted or "*" in granted


async def resolve_user_permissions(
    session: AsyncSession, user: dict
) -> list[str]:
    """汇总当前主体权限点（E0-5）：payload 透传 + DB 矩阵 + 内置角色锚点兜底.

    优先级：payload ``permissions`` claim 与 DB 权限矩阵并集（去重保序）；
    两者皆空（内存降级 / 库未初始化）时按 JWT ``role`` claim 映射内置角色权限
    （仅内置 admin → ``system:superadmin``），保证内置管理员在新口径下仍可用。
    """
    payload_permissions = list(user.get("permissions") or [])
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user.get("id", ""))
    )
    merged = list(dict.fromkeys([*payload_permissions, *db_permissions]))
    if merged:
        return merged
    return list(BUILTIN_ROLE_PERMISSIONS.get(str(user.get("role") or ""), []))


async def ensure_user_permission(
    session: AsyncSession,
    user: dict,
    permission_code: str,
    error_code: ErrorCode = ErrorCode.PERM_FORBIDDEN,
) -> dict:
    """统一权限门禁：超管权限点/通配放行，否则按权限码判定.

    Raises:
        BaseError: 未授权 → ``error_code``（默认 PERM_FORBIDDEN）。
    """
    permissions = await resolve_user_permissions(session, user)
    if is_superadmin(permissions) or has_permission(permissions, permission_code):
        return user
    raise BaseError(error_code, f"missing permission: {permission_code}")


async def tenant_filter_code(session: AsyncSession, user: dict) -> str | None:
    """列表租户过滤键（E1-4a/R3）.

    Returns:
        ``None`` = 不过滤（显式超管，平台视角）；
        ``""`` = 调用方无租户绑定（非超管 → 不应看到任何租户数据）；
        其余 = 生效租户码（``tenant_code`` 优先，回退 ``tenant_id``）。
    """
    permissions = await resolve_user_permissions(session, user)
    if is_superadmin(permissions):
        return None
    raw = user.get("tenant_code") or user.get("tenant_id")
    return str(raw) if raw else ""
