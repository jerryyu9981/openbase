"""identity 模块：L1-1 生命周期级联事件源骨架（U1 T2；事件源本体/投递器/契约桩 T5 落地）.

设计草案 §8：状态迁移事件在「同一 DB 事务」内写 outbox_events（§8.2 表结构由
openbase/core/models/base.py 的 OutboxEvent 声明，create_all 幂等建表）。
本任务先注册同事务写入占位：``enqueue_lifecycle_event`` —— 避免 T5 返工。
投递（outbox_dispatcher / Redis pub-sub / EventConsumerStub / events apply 契约桩）
与事件源本体在 T5（L1-1）实现，本文件仅冻结事件类型与 v1 载荷 schema。
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.models import OutboxEvent, User

logger = logging.getLogger("openbase.identity.events")

# ---- 事件类型（§8.1 v1 冻结：user.provisioned/suspended/restored/deactivated） ----
EVENT_USER_PROVISIONED = "user.provisioned"
EVENT_USER_SUSPENDED = "user.suspended"
EVENT_USER_RESTORED = "user.restored"
EVENT_USER_DEACTIVATED = "user.deactivated"

EVENT_SCHEMA_VERSION = 1
EVENT_SOURCE = "openbase"
EVENT_STATUS_PENDING = "pending"

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
    "EVENT_SCHEMA_VERSION",
    "EVENT_SOURCE",
    "EVENT_STATUS_PENDING",
    "event_type_for_transition",
    "enqueue_lifecycle_event",
]
