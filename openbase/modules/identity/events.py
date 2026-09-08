"""identity 模块：L1-1 生命周期级联事件源骨架（U1 T2；事件源本体/投递器/契约桩 T5 落地）.

设计草案 §8：状态迁移事件在「同一 DB 事务」内写 outbox_events（§8.2 表结构由
openbase/core/models/base.py 的 OutboxEvent 声明，create_all 幂等建表）。
- T2：``enqueue_lifecycle_event`` 同事务写 pending + v1 载荷 schema 冻结；
- T5（L1-1）：本文件补充投递状态常量、事件频道与 schema v1 契约校验
  （``validate_event_payload`` 供 outbox dispatcher / EventConsumerStub / events API 共用）；
  投递器与契约桩本体在 dispatcher.py / consumer_stub.py；
- Q-DESIGN-1：``list_published_events_page`` 单向事件列表 Pull 兜底分页读取
  （GET /identity/events，契约《OpenBase-事件消费契约-v1.0》：cursor/limit 语义定案）。
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import OutboxEvent, User

logger = logging.getLogger("openbase.identity.events")

# ---- 事件类型（§8.1 v1 冻结：user.provisioned/suspended/restored/deactivated） ----
EVENT_USER_PROVISIONED = "user.provisioned"
EVENT_USER_SUSPENDED = "user.suspended"
EVENT_USER_RESTORED = "user.restored"
EVENT_USER_DEACTIVATED = "user.deactivated"

# 合法事件类型集合（schema v1 校验；purge 不对外广播，故不含 user.purged）
VALID_EVENT_TYPES = frozenset(
    {EVENT_USER_PROVISIONED, EVENT_USER_SUSPENDED, EVENT_USER_RESTORED, EVENT_USER_DEACTIVATED}
)

EVENT_SCHEMA_VERSION = 1
EVENT_SOURCE = "openbase"

# ---- outbox 投递状态（§8.2）----
EVENT_STATUS_PENDING = "pending"
EVENT_STATUS_PUBLISHED = "published"
EVENT_STATUS_FAILED = "failed"

# ---- Redis/本地频道（§8.2 双形态通道；键命名 openbase:{domain}:{key}）----
EVENT_CHANNEL = "openbase:identity:events"

# ---- Pull 列表端点（GET /api/v1/identity/events，OpenBase-事件消费契约 v1.0 / Q-DESIGN-1）----
# limit 语义：缺省 50、服务端钳制上限 100（超限不报错，仅截断）；limit<1 → 400 PARAM_INVALID。
EVENTS_PAGE_DEFAULT_LIMIT = 50
EVENTS_PAGE_MAX_LIMIT = 100

# schema v1 必填顶层字段（subject 内另有 subject_id/subject_type）
_REQUIRED_EVENT_FIELDS = (
    "event_id",
    "event_type",
    "occurred_at",
    "source",
    "subject",
    "tenant_code",
    "previous_state",
    "current_state",
    "reason",
    "schema_version",
)
_REQUIRED_SUBJECT_FIELDS = ("subject_id", "subject_type")

# 迁移语义 → 事件类型：按 (previous_state, target_state) 映射
_TRANSITION_EVENT_MAP: dict[tuple[str, str], str] = {
    ("provisioned", "active"): EVENT_USER_PROVISIONED,
    ("active", "suspended"): EVENT_USER_SUSPENDED,
    ("suspended", "active"): EVENT_USER_RESTORED,
    ("active", "deactivated"): EVENT_USER_DEACTIVATED,
    ("suspended", "deactivated"): EVENT_USER_DEACTIVATED,
}


def event_type_for_transition(previous_state: str, target_state: str) -> str | None:
    """状态迁移 → L1-1 事件类型（无对应事件返回 None，如 deactivated→purged 不对外广播）."""
    return _TRANSITION_EVENT_MAP.get((previous_state, target_state))


def validate_event_payload(payload: dict) -> dict:
    """事件 schema v1 契约校验（§8.1；消费端/契约桩/events apply 共用）.

    Args:
        payload: 事件载荷 dict。

    Returns:
        原样 payload（校验通过）。

    Raises:
        BaseError: PARAM_INVALID —— 缺必填字段 / 未知事件类型 / schema_version 非 1。
    """
    missing = [field for field in _REQUIRED_EVENT_FIELDS if field not in payload]
    if missing:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "event payload violates schema v1: missing required fields",
            detail={"missing": missing},
        )
    event_type = payload.get("event_type")
    if event_type not in VALID_EVENT_TYPES:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"unknown event_type: {event_type}",
            detail={"allowed": sorted(VALID_EVENT_TYPES)},
        )
    if payload.get("schema_version") != EVENT_SCHEMA_VERSION:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"unsupported schema_version: {payload.get('schema_version')}",
            detail={"supported": EVENT_SCHEMA_VERSION},
        )
    subject = payload.get("subject")
    if not isinstance(subject, dict):
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "event payload violates schema v1: subject must be an object",
        )
    missing_subject = [field for field in _REQUIRED_SUBJECT_FIELDS if field not in subject]
    if missing_subject:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "event payload violates schema v1: subject missing required fields",
            detail={"missing": missing_subject},
        )
    return payload


async def list_published_events_page(
    session: AsyncSession,
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict], str | None]:
    """Pull 兜底分页读取：返回已 published 事件页（OpenBase-事件消费契约 v1.0 / Q-DESIGN-1）.

    单向事件列表（GET /identity/events，无 ack、无 consumer 过滤，消费端以 event_id
    幂等自滤）。语义定案：

    - 稳定全序：按 (outbox_events.created_at, outbox_events.event_id) 升序；created_at
      为事件入队落库键（与 payload.occurred_at 同事务同刻），等价于契约的
      (occurred_at, event_id) 升序稳定序；
    - cursor：上一页 next_cursor（即上一页最后一条事件的 event_id），**排他上界**——
      本页仅返回严格晚于 cursor 的事件，不含 cursor 自身；
    - cursor 仅接受「已 published」事件：event_id 不存在或行状态非 published →
      400 PARAM_INVALID（不静默从头部返回，消费端据此从头部重拉）；
    - next_cursor：本页之后仍有更多 → 取本页最后一条 event_id；否则 None（无更多）；
    - limit：调用方已钳制到 [1, EVENTS_PAGE_MAX_LIMIT]。

    Args:
        session: 数据库会话（只读，提交由调用方负责）。
        cursor: 排他游标 event_id（None=从头部开始）。
        limit: 本页大小（已钳制）。

    Returns:
        (events, next_cursor)：events 为 schema v1 全字段载荷列表；next_cursor 为空
        （None）表示无更多。
    """
    anchor: OutboxEvent | None = None
    if cursor is not None:
        result = await session.execute(
            select(OutboxEvent).where(OutboxEvent.event_id == cursor)
        )
        anchor = result.scalar_one_or_none()
        if anchor is None:
            raise BaseError(
                ErrorCode.PARAM_INVALID,
                "unknown events list cursor",
                detail={"field": "cursor", "value": cursor, "reason": "event_id not found"},
            )
        if anchor.status != EVENT_STATUS_PUBLISHED:
            raise BaseError(
                ErrorCode.PARAM_INVALID,
                "events list cursor must reference a published event",
                detail={"field": "cursor", "value": cursor, "status": anchor.status},
            )

    stmt = select(OutboxEvent).where(OutboxEvent.status == EVENT_STATUS_PUBLISHED)
    if anchor is not None:
        # 排他上界：created_at 更大，或同 created_at 时 event_id 字典序更大
        stmt = stmt.where(
            or_(
                OutboxEvent.created_at > anchor.created_at,
                and_(
                    OutboxEvent.created_at == anchor.created_at,
                    OutboxEvent.event_id > anchor.event_id,
                ),
            )
        )
    # 多取一条判定是否存在下一页（next_cursor 语义精确，不依赖 == limit 猜测）
    stmt = stmt.order_by(OutboxEvent.created_at, OutboxEvent.event_id).limit(limit + 1)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    events = [row.payload if isinstance(row.payload, dict) else {} for row in page_rows]
    next_cursor = page_rows[-1].event_id if has_more else None
    logger.debug(
        "identity events pull page served",
        extra={
            "cursor": cursor,
            "limit": limit,
            "returned": len(events),
            "next_cursor": next_cursor,
        },
    )
    return events, next_cursor


def _now_iso() -> str:
    """生成 ISO 8601 时间戳（UTC）."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


async def enqueue_lifecycle_event(
    session: AsyncSession,
    *,
    subject: User,
    event_type: str,
    previous_state: str,
    current_state: str,
    reason: str | None,
    role_codes: list[str] | None = None,
    operator: int | None = None,
) -> OutboxEvent:
    """在同一 DB 事务内写 outbox_events（§8.2 可靠事件队列表主通道）.

    载荷遵循 §8.1 事件 schema v1；event_id 为幂等消费键（T5 消费端去重）。

    Args:
        session: 数据库会话（提交由调用方/路由负责，保证与状态更新同事务）。
        subject: 主体行（User）。
        event_type: 事件类型（user.* 集）。
        previous_state: 迁移前状态。
        current_state: 迁移后状态。
        reason: 迁移原因。
        role_codes: 角色码快照（可选）。
        operator: 操作者 id（审计透传）。

    Returns:
        已写入（未提交）的 OutboxEvent 行。
    """
    event_id = uuid.uuid4().hex
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": _now_iso(),
        "source": EVENT_SOURCE,
        "request_id": None,
        "subject": {
            "subject_id": subject.id,
            "subject_type": subject.subject_type or "user",
            "username": subject.username,
        },
        "tenant_code": subject.tenant_code,
        "role_codes": role_codes or [],
        "previous_state": previous_state,
        "current_state": current_state,
        "reason": reason,
        "schema_version": EVENT_SCHEMA_VERSION,
    }
    record = OutboxEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        status=EVENT_STATUS_PENDING,
        publish_attempts=0,
    )
    session.add(record)
    await session.flush()
    logger.info(
        "lifecycle event enqueued",
        extra={
            "event_id": event_id,
            "event_type": event_type,
            "subject_id": subject.id,
            "previous_state": previous_state,
            "current_state": current_state,
            "operator": operator,
        },
    )
    return record


__all__ = [
    "EVENT_USER_PROVISIONED",
    "EVENT_USER_SUSPENDED",
    "EVENT_USER_RESTORED",
    "EVENT_USER_DEACTIVATED",
    "VALID_EVENT_TYPES",
    "EVENT_SCHEMA_VERSION",
    "EVENT_SOURCE",
    "EVENT_STATUS_PENDING",
    "EVENT_STATUS_PUBLISHED",
    "EVENT_STATUS_FAILED",
    "EVENT_CHANNEL",
    "EVENTS_PAGE_DEFAULT_LIMIT",
    "EVENTS_PAGE_MAX_LIMIT",
    "event_type_for_transition",
    "enqueue_lifecycle_event",
    "list_published_events_page",
    "validate_event_payload",
]
