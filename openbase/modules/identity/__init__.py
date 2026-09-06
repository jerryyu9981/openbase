"""identity 模块：统一主体（Principal）管理面（U1 T1，RA-01/OB-1；设计草案 §10.1）.

路由前缀 /api/v1/identity。T1 范围：
- ``POST /agents``：创建 agent 主体（subject_type=agent，默认 viewer 角色）+ 首条
  sk-agent-* 密钥（明文仅展示一次）；
- ``GET /agents/{agent_id}/keys``：密钥列表（不回显明文/哈希）；
- ``POST /agents/{agent_id}/keys``：新增/轮换密钥（多密钥并存）；
- ``DELETE /agents/{agent_id}/keys/{key_id}``：吊销单条密钥（即时失效）。

鉴权：identity:manage / identity:view（admin 通配放行 + RBAC 兜底，风格与 users 模块一致）。
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
from openbase.modules.identity.state_machine import CREDENTIAL_TYPE_API_KEY

logger = logging.getLogger("openbase.identity")

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])

IDENTITY_MANAGE_PERMISSION = "identity:manage"
IDENTITY_VIEW_PERMISSION = "identity:view"


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


__version__ = "0.1.0"
