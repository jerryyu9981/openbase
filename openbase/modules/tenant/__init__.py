"""tenant 模块：多租户隔离（EdgeRouter 中间件 + 租户上下文 + 配额检查）.

来源：OpenMemory multitenancy/edge_router.py（复制级抽取 Header/Path/Query 三级
上下文解析与命名空间缓存模式）+ quota_checker.py（配额检查算法），
适配 openbase 统一配置与日志约定。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user

router = APIRouter(prefix="/api/v1/tenants", tags=["tenant"])


# ---- 租户上下文（请求级） ----


class TenantContext:
    """请求级租户上下文.

    通过 middleware 在请求开始时设置，请求结束后清除。
    来源：OpenMemory multitenancy/edge_router.py（RequestContext 模式）。
    """

    _context_var: dict[str, str | None] = {}

    @classmethod
    def set(cls, tenant_code: str | None, user_id: str | None = None) -> None:
        cls._context_var["tenant"] = tenant_code
        if user_id is not None:
            cls._context_var["user"] = user_id

    @classmethod
    def get(cls) -> str | None:
        return cls._context_var.get("tenant")

    @classmethod
    def get_user(cls) -> str | None:
        return cls._context_var.get("user")

    @classmethod
    def clear(cls) -> None:
        cls._context_var.pop("tenant", None)
        cls._context_var.pop("user", None)


class TenantMiddleware(BaseHTTPMiddleware):
    """EdgeRouter 租户中间件.

    按优先级从请求解析租户上下文（来源: OpenMemory edge_router.parse_context）：
    1. HTTP Header（X-Tenant-Id, X-User-Id）
    2. Path 参数（tenant_id, user_id）
    3. Query 参数（tenant_id, user_id）
    Schema 级隔离的 search_path 切换由数据库适配器实现。
    """

    async def dispatch(self, request: Request, call_next):
        # Header 优先
        tenant = request.headers.get("X-Tenant-Id")
        user_id = request.headers.get("X-User-Id")

        # Path 参数其次
        if not tenant:
            tenant = request.path_params.get("tenant_id")
        if not user_id:
            user_id = request.path_params.get("user_id")

        # Query 参数兜底
        if not tenant:
            tenant = request.query_params.get("tenant_id")
        if not user_id:
            user_id = request.query_params.get("user_id")

        TenantContext.set(tenant, user_id)
        try:
            response = await call_next(request)
        finally:
            TenantContext.clear()
        return response


class QuotaChecker:
    """租户配额检查器.

    来源：OpenMemory multitenancy/quota_checker.py（配额检查算法抽取）。
    v1.0.0 最小实现：内存配额表；生产接数据库与 Redis 计数。
    """

    _quotas: dict[str, dict[str, int]] = {}
    _usage: dict[str, dict[str, int]] = {}

    @classmethod
    def set_quota(cls, tenant: str, resource: str, limit: int) -> None:
        """设置租户某资源配额上限.

        Args:
            tenant: 租户编码。
            resource: 资源名（如 users/storage）。
            limit: 配额上限（-1 表示不限制）。
        """
        cls._quotas.setdefault(tenant, {})[resource] = limit

    @classmethod
    def check(cls, tenant: str, resource: str, delta: int = 1) -> bool:
        """检查租户配额是否允许本次增量消耗.

        Args:
            tenant: 租户编码。
            resource: 资源名。
            delta: 增量（默认 1）。

        Returns:
            是否允许；无配额配置或 limit=-1 时允许。
        """
        limit = cls._quotas.get(tenant, {}).get(resource)
        if limit is None or limit == -1:
            return True
        current = cls._usage.get(tenant, {}).get(resource, 0)
        return current + delta <= limit

    @classmethod
    def consume(cls, tenant: str, resource: str, delta: int = 1) -> bool:
        """尝试消耗配额（检查 + 递增）.

        Returns:
            消耗成功与否；失败时不递增。
        """
        if not cls.check(tenant, resource, delta):
            return False
        cls._usage.setdefault(tenant, {})[resource] = (
            cls._usage.get(tenant, {}).get(resource, 0) + delta
        )
        return True

    @classmethod
    def usage(cls, tenant: str, resource: str) -> int:
        """查询当前用量."""
        return cls._usage.get(tenant, {}).get(resource, 0)


# ---- Schemas ----


class TenantCreate(BaseModel):
    """创建租户请求."""

    name: str
    code: str
    isolation_level: int = 1
    quota: dict | None = None


class TenantOut(BaseModel):
    """租户响应."""

    id: int
    name: str
    code: str
    status: int
    isolation_level: int
    quota: dict | None = None


@router.get("/context", response_model=dict)
async def get_context() -> dict:
    """获取当前请求的租户上下文（调试/校验用）."""
    return {"tenant": TenantContext.get(), "user": TenantContext.get_user()}


@router.post("/{tenant}/quota", response_model=dict)
async def set_quota(tenant: str, resource: str, limit: int) -> dict:
    """设置租户配额（调试/管理用）."""
    QuotaChecker.set_quota(tenant, resource, limit)
    return {"tenant": tenant, "resource": resource, "limit": limit}


@router.get("/{tenant}/quota", response_model=dict)
async def get_quota(tenant: str, resource: str) -> dict:
    """查询租户配额与用量."""
    return {
        "tenant": tenant,
        "resource": resource,
        "usage": QuotaChecker.usage(tenant, resource),
        "allowed": QuotaChecker.check(tenant, resource),
    }


# ---- v1.4.2 R-374 租户管理 CRUD（数据落库 tenants 表） ----


class TenantUpdate(BaseModel):
    """更新租户请求."""

    name: str | None = None
    status: int | None = None  # 1=启用 0=禁用
    quota: dict | None = None


class TenantQuotaUpdate(BaseModel):
    """租户配额更新请求."""

    quota: dict


async def _require_tenant_manage(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """租户管理权限校验（admin 通配放行 + RBAC 兜底）."""
    from openbase.modules.auth.rbac import PermissionService, has_permission

    if user.get("username") == "admin":
        return user
    payload_permissions: list[str] = user.get("permissions") or []
    if has_permission(payload_permissions, "tenant:manage"):
        return user
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user["id"])
    )
    if has_permission(db_permissions, "tenant:manage"):
        return user
    from openbase.core.errors import BaseError, ErrorCode

    raise BaseError(ErrorCode.PERM_FORBIDDEN, "missing permission: tenant:manage")


async def _require_tenant_view(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """租户查看权限校验（admin 通配放行 + RBAC 兜底）."""
    from openbase.modules.auth.rbac import PermissionService, has_permission

    if user.get("username") == "admin":
        return user
    payload_permissions: list[str] = user.get("permissions") or []
    if has_permission(payload_permissions, "tenant:view"):
        return user
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user["id"])
    )
    if has_permission(db_permissions, "tenant:view"):
        return user
    from openbase.core.errors import BaseError, ErrorCode

    raise BaseError(ErrorCode.PERM_FORBIDDEN, "missing permission: tenant:view")


def _tenant_to_out(tenant) -> dict:
    """Tenant 模型 → 响应 DTO."""
    return {
        "id": tenant.id,
        "name": tenant.name,
        "code": tenant.code,
        "status": tenant.status,
        "isolation_level": tenant.isolation_level,
        "quota": tenant.quota,
    }


@router.post("", response_model=TenantOut)
async def create_tenant(
    payload: TenantCreate,
    user: dict = Depends(_require_tenant_manage),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """创建租户（数据落库）."""
    from sqlalchemy import select as sa_select

    from openbase.core.errors import BaseError, ErrorCode
    from openbase.core.models import Tenant as TenantModel

    existing = await session.execute(
        sa_select(TenantModel).where(
            (TenantModel.code == payload.code) | (TenantModel.name == payload.name)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise BaseError(ErrorCode.BIZ_CONFLICT, f"tenant code/name already exists: {payload.code}")

    tenant = TenantModel(
        name=payload.name,
        code=payload.code,
        isolation_level=payload.isolation_level,
        quota=payload.quota,
        status=1,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return _tenant_to_out(tenant)


@router.get("", response_model=list[TenantOut])
async def list_tenants(
    user: dict = Depends(_require_tenant_view),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """租户列表."""
    from sqlalchemy import select as sa_select

    from openbase.core.models import Tenant as TenantModel

    result = await session.execute(sa_select(TenantModel).order_by(TenantModel.id))
    return [_tenant_to_out(row) for row in result.scalars().all()]


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: int,
    user: dict = Depends(_require_tenant_view),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """租户详情."""
    from openbase.core.errors import BaseError, ErrorCode
    from openbase.core.models import Tenant as TenantModel

    tenant = await session.get(TenantModel, tenant_id)
    if tenant is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"tenant not found: {tenant_id}")
    return _tenant_to_out(tenant)


@router.put("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    user: dict = Depends(_require_tenant_manage),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """更新租户（名称/状态/配额）."""
    from openbase.core.errors import BaseError, ErrorCode
    from openbase.core.models import Tenant as TenantModel

    tenant = await session.get(TenantModel, tenant_id)
    if tenant is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"tenant not found: {tenant_id}")
    if payload.name is not None:
        tenant.name = payload.name
    if payload.status is not None:
        tenant.status = payload.status
    if payload.quota is not None:
        tenant.quota = payload.quota
    await session.commit()
    await session.refresh(tenant)
    return _tenant_to_out(tenant)


@router.delete("/{tenant_id}", response_model=dict)
async def deactivate_tenant(
    tenant_id: int,
    user: dict = Depends(_require_tenant_manage),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """停用租户（status=0，保留数据）."""
    from openbase.core.errors import BaseError, ErrorCode
    from openbase.core.models import Tenant as TenantModel

    tenant = await session.get(TenantModel, tenant_id)
    if tenant is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"tenant not found: {tenant_id}")
    tenant.status = 0
    await session.commit()
    return {"code": 0, "tenant_id": tenant_id, "status": 0}


@router.put("/{tenant_id}/quota", response_model=TenantOut)
async def set_tenant_quota(
    tenant_id: int,
    payload: TenantQuotaUpdate,
    user: dict = Depends(_require_tenant_manage),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """租户配额落库（Tenant.quota JSON）."""
    from openbase.core.errors import BaseError, ErrorCode
    from openbase.core.models import Tenant as TenantModel

    tenant = await session.get(TenantModel, tenant_id)
    if tenant is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"tenant not found: {tenant_id}")
    tenant.quota = payload.quota
    await session.commit()
    await session.refresh(tenant)
    return _tenant_to_out(tenant)


__version__ = "1.2.0"
