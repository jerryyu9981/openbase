"""identity 模块：L1-1 生命周期级联事件源骨架（U1 T2；事件源本体/投递器/契约桩 T5 落地）.

设计草案 §8：状态迁移事件在「同一 DB 事务」内写 outbox_events（§8.2 表结构由
openbase/core/models/base.py 的 OutboxEvent 声明，create_all 幂等建表）。
- T2：``enqueue_lifecycle_event`` 同事务写 pending + v1 载荷 schema 冻结；
- T5（L1-1）：本文件补充投递状态常量、事件频道与 schema v1 契约校验
  （``validate_event_payload`` 供 outbox dispatcher / EventConsumerStub / events API 共用）；
  投递器与契约桩本体在 dispatcher.py / consumer_stub.py。
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

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
    "event_type_for_transition",
    "enqueue_lifecycle_event",
    "validate_event_payload",
]
