"""E3-1 访问治理端点：三权分立自检 + ABAC 试算与策略 CRUD（/api/v1/auth/access/*）.

判定路径不被改写：``/check`` 以「DB 启用策略 ∪ 配置基线」做**试算**并给出可解释
原因，``not_applicable`` 表示无策略命中、应由 RBAC 判定；策略 CRUD 仅管理运行期
规则（ER-24），写入与审计同事务（见 ``abac_policy_store``）。
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import ErrorCode
from openbase.core.models import AbacPolicyRule
from openbase.modules.auth.abac_policy_store import (
    create_policy_rule,
    delete_policy_rule,
    list_policy_rules,
    load_effective_rules,
    update_policy_rule,
)
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


class AbacPolicyRequest(BaseModel):
    """ABAC 策略写入请求（新增/更新共用一个字段集）."""

    name: str = Field(min_length=1, max_length=128)
    effect: Literal["allow", "deny"]
    permission: str = Field(default="*", min_length=1, max_length=128)
    roles: list[str] = Field(default_factory=list)
    tenant: str | None = Field(default=None, max_length=64)
    cross_tenant: bool = False
    enabled: bool = True


class AbacPolicyOut(BaseModel):
    """ABAC 策略对外视图（不含内部审计字段）."""

    id: int
    name: str
    effect: str
    permission: str
    roles: list[str]
    tenant: str | None
    cross_tenant: bool
    enabled: bool
    version: int
    created_by: int | None = None
    updated_by: int | None = None

    @classmethod
    def from_row(cls, row: AbacPolicyRule) -> AbacPolicyOut:
        """由持久化行构造视图."""
        return cls(
            id=row.id,
            name=row.name,
            effect=row.effect,
            permission=row.permission,
            roles=list(row.roles or []),
            tenant=row.tenant,
            cross_tenant=bool(row.cross_tenant),
            enabled=bool(row.enabled),
            version=int(row.version or 1),
            created_by=row.created_by,
            updated_by=row.updated_by,
        )


def _subject_tenant(user: dict) -> str:
    """取主体租户码（``tenant_code`` 优先，回退 ``tenant_id``）."""
    raw = user.get("tenant_code") or user.get("tenant_id")
    return str(raw) if raw else ""


def _request_id(request: Request) -> str:
    """取请求 id（审计中间件已注入；缺失时生成，保证 AuditLog 非空）."""
    return str(getattr(request.state, "request_id", "") or uuid.uuid4().hex)


def _actor_id(user: dict) -> int | None:
    """取操作人主体 id（非数字主体返回 None，审计仍留痕）."""
    raw = str(user.get("id") or "")
    return int(raw) if raw.isdigit() else None


def _policy_fields(payload: AbacPolicyRequest) -> dict:
    """抽出参与判定的字段（name/enabled 属管理属性，不进 ABAC 判定）."""
    return {
        "effect": payload.effect,
        "permission": payload.permission,
        "roles": payload.roles,
        "tenant": payload.tenant,
        "cross_tenant": payload.cross_tenant,
    }


async def _require_access_admin(session: AsyncSession, user: dict) -> None:
    """访问治理端点统一权限门禁（``security:admin`` 或超管）."""
    await ensure_user_permission(
        session, user, ACCESS_ADMIN_PERMISSION, ErrorCode.PERM_403
    )


@router.post("/check", response_model=AccessCheckResponse)
async def check_access(
    payload: AccessCheckRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AccessCheckResponse:
    """试算 ABAC 判定（需 ``security:admin`` 权限点或超管）."""
    await _require_access_admin(session, user)
    subject_tenant = _subject_tenant(user)
    roles = payload.roles or [
        role for role in [str(user.get("role") or "")] if role
    ]
    rules = await load_effective_rules(
        session, baseline=parse_abac_rules(get_settings().abac_policies)
    )
    evaluation = evaluate_abac(
        rules,
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
    await _require_access_admin(session, user)
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


@router.get("/policies")
async def list_policies(
    include_disabled: bool = Query(default=False),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """列出运行期策略（默认仅启用行）."""
    await _require_access_admin(session, user)
    rows = await list_policy_rules(session, include_disabled=include_disabled)
    return {
        "code": "OK",
        "message": "ok",
        "data": [AbacPolicyOut.from_row(row).model_dump() for row in rows],
    }


@router.post("/policies")
async def create_policy(
    payload: AbacPolicyRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """新增策略（名称唯一；与审计同事务）."""
    await _require_access_admin(session, user)
    row = await create_policy_rule(
        session,
        name=payload.name,
        fields=_policy_fields(payload),
        enabled=payload.enabled,
        actor_id=_actor_id(user),
        request_id=_request_id(request),
    )
    return {
        "code": "OK",
        "message": "ok",
        "data": AbacPolicyOut.from_row(row).model_dump(),
    }


@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: int,
    payload: AbacPolicyRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """更新策略（版本自增；与审计同事务）."""
    await _require_access_admin(session, user)
    row = await update_policy_rule(
        session,
        policy_id=policy_id,
        name=payload.name,
        fields=_policy_fields(payload),
        enabled=payload.enabled,
        actor_id=_actor_id(user),
        request_id=_request_id(request),
    )
    return {
        "code": "OK",
        "message": "ok",
        "data": AbacPolicyOut.from_row(row).model_dump(),
    }


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """删除策略（审计留痕先于删除生效，同事务）."""
    await _require_access_admin(session, user)
    await delete_policy_rule(
        session,
        policy_id=policy_id,
        actor_id=_actor_id(user),
        request_id=_request_id(request),
    )
    return {"code": "OK", "message": "ok", "data": {"policy_id": policy_id}}
