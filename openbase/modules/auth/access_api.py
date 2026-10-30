"""E3-1 访问治理端点：三权分立自检 + ABAC 试算（/api/v1/auth/access/*）.

仅提供试算与自检能力，不改动既有鉴权路径：策略命中结果由调用方决定是否
作为 RBAC 的前置门禁使用；``not_applicable`` 表示无策略命中、应由 RBAC 判定。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import ErrorCode
from openbase.modules.auth.access_control import (
    ACCESS_ADMIN_PERMISSION,
    DUTY_ROLE_PERMISSIONS,
    evaluate_abac,
    parse_abac_rules,
)
from openbase.modules.auth.rbac import ensure_user_permission
from openbase.settings import get_settings

router = APIRouter(prefix="/api/v1/auth/access", tags=["auth"])

__all__ = ["router"]


class AccessCheckRequest(BaseModel):
    """ABAC 试算请求."""

    permission: str = Field(min_length=1, max_length=128)
    resource_tenant: str = Field(default="", max_length=128)
    roles: list[str] = Field(default_factory=list)


class AccessCheckResponse(BaseModel):
    """ABAC 试算结果（含可解释原因）."""

    decision: str
    reason: str
    permission: str
    subject_tenant: str
    resource_tenant: str


def _subject_tenant(user: dict) -> str:
    """取主体租户码（``tenant_code`` 优先，回退 ``tenant_id``）."""
    raw = user.get("tenant_code") or user.get("tenant_id")
    return str(raw) if raw else ""


@router.post("/check", response_model=AccessCheckResponse)
async def check_access(
    payload: AccessCheckRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AccessCheckResponse:
    """试算 ABAC 判定（需 ``security:admin`` 权限点或超管）."""
    await ensure_user_permission(
        session, user, ACCESS_ADMIN_PERMISSION, ErrorCode.PERM_403
    )
    subject_tenant = _subject_tenant(user)
    roles = payload.roles or [
        role for role in [str(user.get("role") or "")] if role
    ]
    evaluation = evaluate_abac(
        parse_abac_rules(get_settings().abac_policies),
        permission=payload.permission,
        subject_tenant=subject_tenant,
        resource_tenant=payload.resource_tenant,
        roles=roles,
    )
    return AccessCheckResponse(
        decision=evaluation.decision,
        reason=evaluation.reason,
        permission=payload.permission,
        subject_tenant=subject_tenant,
        resource_tenant=payload.resource_tenant,
    )


@router.get("/duties")
async def list_duties(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """返回三权分立职责与权限点基线（供管理面展示与授权自检）."""
    await ensure_user_permission(
        session, user, ACCESS_ADMIN_PERMISSION, ErrorCode.PERM_403
    )
    return {
        "code": "OK",
        "message": "ok",
        "data": {
            "duties": {
                code: list(permissions)
                for code, permissions in DUTY_ROLE_PERMISSIONS.items()
            },
            "mutually_exclusive": True,
        },
    }
