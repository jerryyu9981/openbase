"""RBAC 权限矩阵：配置驱动权限管理器 + 权限点校验依赖.

来源：OpenLLM backend/app/edgerouter/auth/rbac.py（RBACManager 配置驱动模式抽取，
适配 openbase 统一错误与配置约定）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends

from openbase.core.deps import get_current_user
from openbase.core.errors import BaseError, ErrorCode

__all__ = ["require_permission", "has_permission", "PermissionStore"]


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


def require_permission(permission_code: str) -> Callable[..., Any]:
    """生成 RBAC 权限校验依赖.

    校验链（来源: OpenLLM RBACManager 模式）：
    1. JWT payload 携带权限（轻量路径，透传场景）
    2. PermissionStore 角色-权限映射查询（用户-角色-权限矩阵）

    用法::

        @router.get("/users", dependencies=[Depends(require_permission("user:list"))])
        async def list_users(): ...

    Args:
        permission_code: 所需权限点（如 "user:list"）。

    Returns:
        FastAPI 依赖函数。
    """

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        user_id = str(user.get("id", ""))

        # 路径 1：payload 携带权限（透传/轻量场景）
        payload_permissions: list[str] = user.get("permissions") or []
        if has_permission(payload_permissions, permission_code):
            return user

        # 路径 2：PermissionStore 权限矩阵查询
        store_permissions = PermissionStore.permissions_for(user_id)
        if has_permission(store_permissions, permission_code):
            return user

        raise BaseError(
            ErrorCode.AUTH_FORBIDDEN,
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
