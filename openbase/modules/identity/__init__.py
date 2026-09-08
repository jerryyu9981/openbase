"""identity 模块：统一主体（Principal）管理面（U1 T1/T2/T5/T6，RA-01/RA-02/OB-1/OB-2/L1-2）.

路由前缀 /api/v1/identity。T1 范围：agent 主体创建 + sk-agent-* 密钥族；
T2（RA-02/OB-2 状态机）新增 lifecycle 迁移端点族（activate/suspend/restore/deactivate），
仅 admin/受权（identity:lifecycle）可调用；状态迁移统一经 IdentityLifecycleService
（写 status_reason/审计/L1-1 事件 outbox/清缓存，非法迁移 400 BIZ_STATE_TRANSITION_INVALID）。
T5（L1-1 设计草案 §8/§10.1/§11 T5-1~T5-6）新增契约桩 events API：
POST /events/apply（投递+模拟消费）、GET /events/{event_id}（状态查询/S7 钩子）、
GET /blocked/{subject_id}（数据面阻断对账桩态：blocked → 403 拒绝语义）。
Q-DESIGN-1（OpenBase 责任登记）补单向事件列表 GET /events（Pull 兜底轮询通道，
契约《OpenBase-事件消费契约-v1.0》：无 ack、无 consumer 过滤、cursor=event_id 排他游标
按 (occurred_at,event_id) 稳定序分页，limit 缺省 50/钳制 100；OpenMemory S2 消费端据此对接）。
T6（L1-2，Q-5=A 设计草案 §9/§11 T6-1~T6-5）新增 purge 受权端点：
POST /purge（admin + identity:purge + 一次性授权码 + 影响范围报告确认；仅 deactivated
主体可 purge，非 deactivated → 400 BIZ_NOT_PURGEABLE，授权缺失/过期 → 403
BIZ_PURGE_AUTH_REQUIRED；授权码由 CLI/服务层签发，本模块只消费执行）。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AgentApiKey, OutboxEvent
from openbase.modules.auth.rbac import PermissionService, has_permission
from openbase.modules.identity.agent_keys import AgentKeyService
from openbase.modules.identity.agents import (
    DEFAULT_AGENT_ROLE,
    create_agent_subject,
    ensure_agent_subject,
)
from openbase.modules.identity.consumer_stub import STUB_DATA_DOMAINS, EventConsumerStub
from openbase.modules.identity.dispatcher import OutboxDispatcherService
from openbase.modules.identity.events import (
    EVENTS_PAGE_DEFAULT_LIMIT,
    EVENTS_PAGE_MAX_LIMIT,
    list_published_events_page,
)
from openbase.modules.identity.lifecycle import IdentityLifecycleService
from openbase.modules.identity.purge import IdentityPurgeService
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
IDENTITY_PURGE_PERMISSION = "identity:purge"

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


async def _require_identity_purge(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """purge 端点权限校验（admin 通配 + identity:purge；无权限 403）."""
    return await _check_permission(user, session, IDENTITY_PURGE_PERMISSION)


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


# ---- U1 T6（L1-2，Q-5=A）：purge 显式合规触发端点（草案 §9.2/§10.1/§11 T6-2~T6-5） ----
# 受权端点：admin 通配 + identity:purge（无权限 403）；二次授权码 + 影响范围报告确认；
# 仅 deactivated 主体可 purge（非 deactivated → 400 BIZ_NOT_PURGEABLE）。


class PurgeRequest(BaseModel):
    """purge 请求：deactivated 主体 + 一次性授权码 + 影响范围报告确认哈希."""

    subject_type: str = Field(SUBJECT_TYPE_USER, description="主体具象：user/agent")
    subject_id: int = Field(..., description="主体 id（users.id）")
    purge_authorization_code: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="一次性 purge 授权码（管理员经 CLI/服务签发）",
    )
    scope_report_hash: str = Field(
        ...,
        min_length=16,
        max_length=64,
        description="影响范围报告 sha256 确认哈希（与签发时一致）",
    )
    idempotency_key: str | None = Field(
        None, max_length=64, description="幂等键（可选；purge_records 唯一约束防并发双跑）"
    )


class PurgeOut(BaseModel):
    """purge 成功响应（主体已物理清除；终态由 purge_records 台账承载）."""

    purged: bool = True
    subject_id: int
    subject_type: str
    username: str | None = None
    tenant_code: str | None = None
    previous_state: str
    status_state: str
    scope_report: dict[str, Any]
    scope_report_hash: str
    authorization_ref: str | None = None


@router.post("/purge", response_model=PurgeOut)
async def purge_subject(
    payload: PurgeRequest,
    user: dict = Depends(_require_identity_purge),
    session: AsyncSession = Depends(get_db),
) -> PurgeOut:
    """执行 purge：显式合规触发（deactivated + 授权码 + 范围报告确认）.

    Raises:
        BaseError: BIZ_NOT_FOUND（404 未知主体）；BIZ_NOT_PURGEABLE（400 非
            deactivated/已 purged 终态）；BIZ_PURGE_AUTH_REQUIRED（403 授权码
            缺失/无效/过期/范围报告未确认）。
    """
    validated = _validated_subject_type(payload.subject_type)
    result = await IdentityPurgeService.execute_purge(
        session,
        subject_id=payload.subject_id,
        subject_type=validated,
        authorization_code=payload.purge_authorization_code,
        scope_report_hash=payload.scope_report_hash,
        operator=_subject_id(user),
        idempotency_key=payload.idempotency_key,
    )
    await session.commit()
    logger.info(
        "identity purge api invoked",
        extra={
            "subject_type": validated,
            "subject_id": payload.subject_id,
            "operator": user.get("username"),
            "request_id": result.request_id,
            "audit_log_id": result.audit_log_id,
        },
    )
    return PurgeOut(
        purged=True,
        subject_id=result.subject_id,
        subject_type=result.subject_type,
        username=result.username,
        tenant_code=result.tenant_code,
        previous_state=result.previous_state,
        status_state=result.status_state,
        scope_report=result.scope_report,
        scope_report_hash=result.scope_report_hash,
        authorization_ref=result.authorization_ref,
    )


# ---- U1 T5（L1-1）：契约桩 events API（草案 §10.1/§8.3/§8.4）----
# POST /events/apply（投递+模拟消费）、GET /events/{event_id}（状态查询，S7 钩子）、
# GET /blocked/{subject_id}（数据面阻断对账桩态：blocked → 403 拒绝语义，不真连子系统）。


class EventApplyRequest(BaseModel):
    """契约桩 apply 请求：事件载荷（schema v1）+ 可选模拟消费端域."""

    event: dict = Field(..., description="事件载荷（schema v1：event_type/subject/tenant_code/…）")
    consumer: str | None = Field(
        None,
        description="模拟消费端域（dps/openmemory/openrag）；缺省=全部桩域",
    )


class OutboxEventStatusOut(BaseModel):
    """outbox 事件投递状态（GET /events/{event_id}）. """

    event_id: str
    event_type: str
    status: str
    publish_attempts: int
    next_retry_at: str | None = None
    published_at: str | None = None
    created_at: str
    payload: dict


class IdentityEventListOut(BaseModel):
    """单向事件列表页（GET /events，OpenBase-事件消费契约 v1.0 / Q-DESIGN-1）.

    events 为 schema v1 全字段事件载荷（逐字段透传 outbox payload，含 subject 嵌套与
    role_codes/previous_state/current_state/reason）；next_cursor 为空表示无更多。
    """

    events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="已 published 事件（schema v1 载荷，按 (occurred_at,event_id) 稳定序）",
    )
    next_cursor: str | None = Field(
        None,
        description="下一页游标（本页最后一条 event_id，排他上界）；null=无更多",
    )


def _iso_or_none(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _outbox_status_out(event: OutboxEvent) -> OutboxEventStatusOut:
    return OutboxEventStatusOut(
        event_id=event.event_id,
        event_type=event.event_type,
        status=event.status,
        publish_attempts=event.publish_attempts or 0,
        next_retry_at=_iso_or_none(event.next_retry_at),
        published_at=_iso_or_none(event.published_at),
        created_at=_iso_or_none(event.created_at) or "",
        payload=event.payload or {},
    )


@router.post("/events/apply")
async def event_apply(
    payload: EventApplyRequest,
    user: dict = Depends(_require_identity_manage),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """契约桩 apply（投递 + 模拟消费）：先投递 pending outbox 事件，再按契约落阻断集.

    - 投递：event_id 命中 outbox 且 pending → 同执行体发布（published/重试语义一致）；
    - 模拟消费：schema v1 校验 → 幂等表去重（重放副作用一次）→ user.suspended/deactivated
      阻断、current_state=active（restored）解除阻断（DPS/OpenMemory/OpenRAG 桩态）。
    """
    event = payload.event
    event_id = event.get("event_id", "")
    dispatch_result = await OutboxDispatcherService.dispatch_by_event_id(session, event_id)
    consumption = await EventConsumerStub.apply(
        session, event, consumer=payload.consumer
    )
    await session.commit()
    results = consumption["results"]
    logger.info(
        "identity event apply api invoked",
        extra={
            "event_id": event_id,
            "event_type": event.get("event_type"),
            "operator": user.get("username"),
            "dispatch_outcome": (dispatch_result or {}).get("outcome"),
        },
    )
    return {
        "event_id": event_id,
        "event_type": event.get("event_type"),
        "dispatch": dispatch_result,
        "consumption": {
            "deduplicated": bool(results) and all(r["deduplicated"] for r in results),
            "results": results,
        },
    }


@router.get("/events", response_model=IdentityEventListOut)
async def list_identity_events(
    cursor: str | None = Query(
        None,
        description="排他游标：上一页 next_cursor（须为已 published 事件的 event_id）；缺省=从头部",
    ),
    limit: int | None = Query(
        None,
        description=f"页大小（缺省 {EVENTS_PAGE_DEFAULT_LIMIT}；超上限钳制为 {EVENTS_PAGE_MAX_LIMIT}）",
    ),
    user: dict = Depends(_require_identity_view),
    session: AsyncSession = Depends(get_db),
) -> IdentityEventListOut:
    """单向事件列表（Pull 兜底轮询，契约《OpenBase-事件消费契约-v1.0》/ Q-DESIGN-1）.

    无 ack、无 consumer 过滤；仅返回 outbox 已 published 事件，按 (occurred_at,event_id)
    稳定序分页（cursor 为排他上界 event_id）。未知/未 published 游标与 limit<1 →
    400 PARAM_INVALID；limit 缺省 50、服务端钳制上限 100。
    """
    page_limit = EVENTS_PAGE_DEFAULT_LIMIT if limit is None else limit
    if page_limit < 1:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "limit must be a positive integer",
            detail={"field": "limit", "value": limit},
        )
    page_limit = min(page_limit, EVENTS_PAGE_MAX_LIMIT)
    events, next_cursor = await list_published_events_page(
        session,
        cursor=cursor,
        limit=page_limit,
    )
    return IdentityEventListOut(events=events, next_cursor=next_cursor)


@router.get("/events/{event_id}", response_model=OutboxEventStatusOut)
async def event_status(
    event_id: str,
    user: dict = Depends(_require_identity_view),
    session: AsyncSession = Depends(get_db),
) -> OutboxEventStatusOut:
    """事件投递状态查询（S7 全链核验钩子，草案 §8.4/§10.1）. """
    result = await session.execute(
        select(OutboxEvent).where(OutboxEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"event not found: {event_id}")
    return _outbox_status_out(event)


@router.get("/blocked/{subject_id}")
async def subject_block_status(
    subject_id: int,
    domain: str | None = Query(None, description="数据面域：dps/openmemory/openrag（缺省=全部）"),
    user: dict = Depends(_require_identity_view),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """数据面阻断对账（契约桩态）：deactivated/suspended 后返回拒绝语义（403）.

    模拟 DPS 画像读 / OpenMemory 记忆访问 / OpenRAG 归属行访问在数据面的准入判定：
    blocked → 403 PERM_FORBIDDEN（拒绝语义，detail 含各域检查结果）；未阻断 → 200
    {allowed: True, checks}。不真连子系统（S2/S3/S5 真实数据面按同一语义落地）。
    """
    if domain is not None and domain not in STUB_DATA_DOMAINS:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"unknown domain: {domain}",
            detail={"allowed": list(STUB_DATA_DOMAINS)},
        )
    requested_domains = list(STUB_DATA_DOMAINS) if domain is None else [domain]

    checks: list[dict[str, Any]] = []
    denied_domains: list[dict[str, Any]] = []
    subject_type = "user"
    tenant_code: str | None = None
    for requested in requested_domains:
        block = await EventConsumerStub.load_block(session, subject_id, requested)
        if block is not None:
            subject_type = block.subject_type or subject_type
            tenant_code = block.tenant_code or tenant_code
        is_blocked = block is not None and block.state == "blocked"
        check = {
            "domain": requested,
            "action": STUB_DATA_DOMAINS[requested],
            "allowed": not is_blocked,
            "state": block.state if block is not None else "allowed",
            "reason": block.reason if block is not None else None,
            "event_id": block.event_id if block is not None else None,
        }
        checks.append(check)
        if is_blocked:
            denied_domains.append(check)

    if denied_domains:
        raise BaseError(
            ErrorCode.PERM_FORBIDDEN,
            f"data-plane access denied for subject {subject_id}",
            detail={
                "subject_id": subject_id,
                "subject_type": subject_type,
                "tenant_code": tenant_code,
                "allowed": False,
                "checks": checks,
            },
        )
    return {
        "subject_id": subject_id,
        "subject_type": subject_type,
        "tenant_code": tenant_code,
        "allowed": True,
        "checks": checks,
    }


__version__ = "0.1.0"
