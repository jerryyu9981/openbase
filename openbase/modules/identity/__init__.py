"""identity 模块：统一主体（Principal）管理面（U1 T1/T2，RA-01/RA-02；设计草案 §10.1）.

路由前缀 /api/v1/identity。T1 范围：agent 主体创建 + sk-agent-* 密钥族；
T2（RA-02/OB-2 状态机）新增 lifecycle 迁移端点族（activate/suspend/restore/deactivate），
仅 admin/受权（identity:lifecycle）可调用；状态迁移统一经 IdentityLifecycleService
（写 status_reason/审计/L1-1 事件 outbox/清缓存，非法迁移 400 BIZ_STATE_TRANSITION_INVALID）。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AgentApiKey
from openbase.modules.auth.rbac import PermissionService, has_permission
from openbase.modules.identity.agent_keys import AgentKeyService
from openbase.modules.identity.agents import (
    DEFAULT_AGENT_ROLE,
    create_agent_subject,
    ensure_agent_subject,
)
from openbase.modules.identity.lifecycle import IdentityLifecycleService
from openbase.modules.identity.state_machine import (
    CREDENTIAL_TYPE_API_KEY,
    SUBJECT_TYPE_AGENT,
    SUBJECT_TYPE_USER,
)

logger = logging.getLogger("openbase.identity")

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])

IDENTITY_MANAGE_PERMISSION = "identity:manage"
IDENTITY_VIEW_PERMISSION = "identity:view"
IDENTITY_LIFECYCLE_PERMISSION = "identity:lifecycle"

# lifecycle 端点允许的 subject_type
_VALID_SUBJECT_TYPES = frozenset({SUBJECT_TYPE_USER, SUBJECT_TYPE_AGENT})


# ---- Schemas ----


class AgentCreateRequest(BaseModel):
    """创建 agent 主体请求（username/display_name/tenant_id/role/key_name）."""

    username: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.:-]+$")
    display_name: str = Field(..., min_length=1, max_length=128)
    tenant_id: int | None = Field(None, description="归属租户（按域隔离，可选）")
    role: str = Field(DEFAULT_AGENT_ROLE, description="初始角色码（默认 viewer 最低权限）")
    key_name: str | None = Field(None, min_length=1, max_length=64)


class AgentApiKeyCreateRequest(BaseModel):
    """签发/轮换 sk-agent-* 密钥请求."""

    name: str | None = Field(None, min_length=1, max_length=64)
    expires_at: dt.datetime | None = None


class AgentKeyOut(BaseModel):
    """密钥记录（raw_key 仅创建/签发响应返回一次；列表不回显）. """

    id: int
    agent_id: int
    name: str | None = None
    key_prefix: str
    key_suffix: str | None = None
    status: str
    expires_at: dt.datetime | None = None
    last_used_at: dt.datetime | None = None
    created_at: dt.datetime
    raw_key: str | None = None


class AgentCreated(BaseModel):
    """创建 agent 响应（含首条明文密钥）. """

    agent_id: int
    username: str
    display_name: str
    subject_type: str
    credential_type: str
    status_state: str
    tenant_id: int | None = None
    tenant_code: str | None = None
    roles: list[str]
    api_key: AgentKeyOut


# ---- 权限依赖 ----


def _subject_id(user: dict) -> int | None:
    """当前主体 id（数字 → int；OIDC 字符串主体 → None，created_by 可空）."""
    raw_id = user.get("id")
    if isinstance(raw_id, int):
        return raw_id
    try:
        return int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        return None


async def _check_permission(
    user: dict, session: AsyncSession, permission_code: str
) -> dict:
    """identity 域权限校验（admin 通配放行 + payload/DB RBAC 兜底）."""
    if user.get("username") == "admin":
        return user
    payload_permissions: list[str] = user.get("permissions") or []
    if has_permission(payload_permissions, permission_code):
        return user
    db_permissions = await PermissionService.permissions_for_with_fallback(
        session, str(user["id"])
    )
    if has_permission(db_permissions, permission_code):
        return user
    raise BaseError(ErrorCode.PERM_FORBIDDEN, f"missing permission: {permission_code}")


async def _require_identity_manage(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await _check_permission(user, session, IDENTITY_MANAGE_PERMISSION)


async def _require_identity_view(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await _check_permission(user, session, IDENTITY_VIEW_PERMISSION)


async def _require_identity_lifecycle(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """lifecycle 端点权限校验（admin 通配 + identity:lifecycle；无权限 403，T2-7 断言）."""
    return await _check_permission(user, session, IDENTITY_LIFECYCLE_PERMISSION)


# ---- Lifecycle Schemas（T2，RA-02） ----


class LifecycleTransitionRequest(BaseModel):
    """状态迁移请求（suspend/restore/activate 共用）. """

    reason: str | None = Field(None, max_length=255, description="迁移原因（审计/合规）")


class DeactivateRequest(BaseModel):
    """注销（deactivate）请求：需二次确认 confirm=true（防误触，草案 §4.2）."""

    confirm: bool = False
    reason: str | None = Field(None, max_length=255)


class LifecycleOut(BaseModel):
    """状态迁移响应."""

    id: int
    subject_type: str
    username: str
    previous_state: str
    status_state: str
    status_reason: str | None = None
    token_version: int
    tenant_code: str | None = None
    roles: list[str] = []


def _lifecycle_out(result: Any, subject_type: str) -> LifecycleOut:
    return LifecycleOut(
        id=result.subject.id,
        subject_type=subject_type,
        username=result.subject.username,
        previous_state=result.previous_state,
        status_state=result.subject.status_state,
        status_reason=result.subject.status_reason,
        token_version=result.subject.token_version,
        tenant_code=result.subject.tenant_code,
        roles=result.role_codes,
    )


def _validated_subject_type(subject_type: str) -> str:
    """校验路径 subject_type ∈ {user, agent}（否则 400 PARAM_INVALID）."""
    if subject_type not in _VALID_SUBJECT_TYPES:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"invalid subject_type: {subject_type}",
            detail={"allowed": sorted(_VALID_SUBJECT_TYPES)},
        )
    return subject_type


def _key_out(record: AgentApiKey, raw_key: str | None = None) -> AgentKeyOut:
    return AgentKeyOut(
        id=record.id,
        agent_id=record.agent_id,
        name=record.name,
        key_prefix=record.key_prefix,
        key_suffix=record.key_suffix,
        status=record.status,
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
        created_at=record.created_at,
        raw_key=raw_key,
    )


# ---- 路由 ----


@router.post("/agents", response_model=AgentCreated)
async def create_agent(
    payload: AgentCreateRequest,
    user: dict = Depends(_require_identity_manage),
    session: AsyncSession = Depends(get_db),
) -> AgentCreated:
    """创建 agent 主体（默认 viewer）并签发首条 sk-agent-* 密钥（明文仅此一次）."""
    operator = _subject_id(user)
    agent = await create_agent_subject(
        session,
        username=payload.username,
        display_name=payload.display_name,
        tenant_id=payload.tenant_id,
        role=payload.role,
        created_by=operator,
    )
    raw_key, key_record = await AgentKeyService.issue_key(
        session,
        agent_id=agent.id,
        name=payload.key_name or payload.display_name,
        created_by=operator,
    )
    await session.commit()
    await session.refresh(agent)
    logger.info(
        "identity agent created",
        extra={"agent_id": agent.id, "operator": user.get("username")},
    )
    return AgentCreated(
        agent_id=agent.id,
        username=agent.username,
        display_name=agent.display_name,
        subject_type=agent.subject_type,
        credential_type=CREDENTIAL_TYPE_API_KEY,
        status_state=agent.status_state,
        tenant_id=agent.tenant_id,
        tenant_code=agent.tenant_code,
        roles=[payload.role],
        api_key=_key_out(key_record, raw_key),
    )


@router.get("/agents/{agent_id}/keys", response_model=list[AgentKeyOut])
async def list_agent_keys(
    agent_id: int,
    user: dict = Depends(_require_identity_view),
    session: AsyncSession = Depends(get_db),
) -> list[AgentKeyOut]:
    """agent 密钥列表（不回显明文，含已吊销记录）."""
    await ensure_agent_subject(session, agent_id)
    records = await AgentKeyService.list_keys(session, agent_id=agent_id)
    return [_key_out(record) for record in records]


@router.post("/agents/{agent_id}/keys", response_model=AgentKeyOut)
async def issue_agent_key(
    agent_id: int,
    payload: AgentApiKeyCreateRequest,
    user: dict = Depends(_require_identity_manage),
    session: AsyncSession = Depends(get_db),
) -> AgentKeyOut:
    """为 agent 新增/轮换 sk-agent-* 密钥（多密钥并存；返回明文仅此一次）."""
    await ensure_agent_subject(session, agent_id)
    raw_key, record = await AgentKeyService.issue_key(
        session,
        agent_id=agent_id,
        name=payload.name or "rotated",
        expires_at=payload.expires_at,
        created_by=_subject_id(user),
    )
    await session.commit()
    return _key_out(record, raw_key)


@router.delete("/agents/{agent_id}/keys/{key_id}", response_model=dict[str, Any])
async def revoke_agent_key(
    agent_id: int,
    key_id: int,
    user: dict = Depends(_require_identity_manage),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """吊销单条 agent 密钥（即时失效：后续该校验 401）."""
    await ensure_agent_subject(session, agent_id)
    record = await AgentKeyService.revoke_key(session, agent_id=agent_id, key_id=key_id)
    await session.commit()
    logger.info(
        "identity agent key revoked",
        extra={"agent_id": agent_id, "key_id": key_id, "operator": user.get("username")},
    )
    return {"revoked": True, "agent_id": agent_id, "key_id": record.id}


# ---- U1 T2（RA-02/OB-2 状态机）：lifecycle 迁移端点族（草案 §4.2/§10.1） ----
# 鉴权：admin 通配 + identity:lifecycle（无权限 403）；迁移非法一律 400。


async def _run_transition(
    transition_callable: Any,
    subject_type: str,
    subject_id: int,
    reason: str | None,
    user: dict,
    session: AsyncSession,
) -> LifecycleOut:
    """执行状态迁移服务并提交（统一路由样板：服务编排 → commit → 响应）. """
    operator = _subject_id(user)
    result = await transition_callable(
        session,
        subject_id,
        subject_type=subject_type,
        reason=reason,
        operator=operator,
    )
    await session.commit()
    logger.info(
        "identity lifecycle api invoked",
        extra={
            "subject_type": subject_type,
            "subject_id": subject_id,
            "from": result.previous_state,
            "to": result.target_state,
            "operator": user.get("username"),
        },
    )
    return _lifecycle_out(result, subject_type)


@router.post(
    "/lifecycle/{subject_type}/{subject_id}/activate",
    response_model=LifecycleOut,
)
async def lifecycle_activate(
    subject_type: str,
    subject_id: int,
    payload: LifecycleTransitionRequest,
    user: dict = Depends(_require_identity_lifecycle),
    session: AsyncSession = Depends(get_db),
) -> LifecycleOut:
    """provisioned → active（管理员启用；无吊销副作用，发 user.provisioned 事件）."""
    validated = _validated_subject_type(subject_type)
    return await _run_transition(
        IdentityLifecycleService.activate,
        validated,
        subject_id,
        payload.reason,
        user,
        session,
    )


@router.post(
    "/lifecycle/{subject_type}/{subject_id}/suspend",
    response_model=LifecycleOut,
)
async def lifecycle_suspend(
    subject_type: str,
    subject_id: int,
    payload: LifecycleTransitionRequest,
    user: dict = Depends(_require_identity_lifecycle),
    session: AsyncSession = Depends(get_db),
) -> LifecycleOut:
    """active → suspended（即时拒签 + tvn+1 + 吊销联动 + user.suspended 事件）. """
    validated = _validated_subject_type(subject_type)
    return await _run_transition(
        IdentityLifecycleService.suspend,
        validated,
        subject_id,
        payload.reason,
        user,
        session,
    )


@router.post(
    "/lifecycle/{subject_type}/{subject_id}/restore",
    response_model=LifecycleOut,
)
async def lifecycle_restore(
    subject_type: str,
    subject_id: int,
    payload: LifecycleTransitionRequest,
    user: dict = Depends(_require_identity_lifecycle),
    session: AsyncSession = Depends(get_db),
) -> LifecycleOut:
    """suspended → active（恢复；tvn 再次 +1，旧 token 不复活；发恢复事件）. """
    validated = _validated_subject_type(subject_type)
    return await _run_transition(
        IdentityLifecycleService.restore,
        validated,
        subject_id,
        payload.reason,
        user,
        session,
    )


@router.post(
    "/lifecycle/{subject_type}/{subject_id}/deactivate",
    response_model=LifecycleOut,
)
async def lifecycle_deactivate(
    subject_type: str,
    subject_id: int,
    payload: DeactivateRequest,
    user: dict = Depends(_require_identity_lifecycle),
    session: AsyncSession = Depends(get_db),
) -> LifecycleOut:
    """→ deactivated（注销；全部凭据失效 + user.deactivated 事件；需 confirm=true 二次确认）."""
    if not payload.confirm:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "deactivate requires confirm=true (double confirmation)",
        )
    validated = _validated_subject_type(subject_type)
    return await _run_transition(
        IdentityLifecycleService.deactivate,
        validated,
        subject_id,
        payload.reason,
        user,
        session,
    )


__version__ = "0.1.0"
