"""identity 模块：L1-1 契约桩 EventConsumerStub（U1 T5，设计草案 §8.2/§8.3/§11 T5-2~T5-6）.

模拟 DPS/OpenMemory/OpenRAG 消费端在 U1 内可验证的「数据面阻断语义」骨架：
- ``apply``：按事件契约执行数据面阻断 —— user.suspended/user.deactivated 将目标主体
  （+ 域）写入阻断集（subject_blocks），current_state=active（user.restored 等）解除阻断；
  消费端幂等表 event_consumptions 以 (event_id, consumer) 去重 —— 重放不产生重复副作用；
- ``subscribe``：注册进程内事件订阅（经 redis_client 本地通道兜底，Redis 不可用不丢事件），
  记录到达时刻供「投递秒级窗口 ≤5s」（T5-5）断言；
- ``check_access``/阻断行查询：供 GET /identity/blocked/{subject_id} 对账接口返回拒绝语义
  （403 PERM_FORBIDDEN，桩态，不真连子系统）。

边界：本桩只模拟「消费端如何落阻断并对外返回拒绝语义」，不做 DPS/OpenMemory/OpenRAG
真实数据面实现（真实消费端在 S2/S3/S5 段落地，按本契约对接）。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.cache.redis_client import subscribe as local_subscribe
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import EventConsumption, SubjectBlock
from openbase.modules.identity.events import (
    EVENT_CHANNEL,
    validate_event_payload,
)
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    STATUS_STATE_DEACTIVATED,
    STATUS_STATE_SUSPENDED,
)

logger = logging.getLogger("openbase.identity.consumer_stub")

# 阻断集状态
BLOCK_STATE_BLOCKED = "blocked"
BLOCK_STATE_ALLOWED = "allowed"

# 阻断触发状态（数据面读/写阻断；数据保留，Q-5=A）
_BLOCKING_SUBJECT_STATES = frozenset({STATUS_STATE_SUSPENDED, STATUS_STATE_DEACTIVATED})

# 桩消费端域 → 数据面动作（对账接口返回拒绝语义的动作标识）
STUB_DATA_DOMAINS: dict[str, str] = {
    "dps": "portrait.read",
    "openmemory": "memory.access",
    "openrag": "document.access",
}


def _now_timestamp() -> float:
    return time.monotonic()


def _block_state_for_current(current_state: str) -> str | None:
    """按事件 current_state 判定阻断语义：suspended/deactivated → blocked；
    active（user.restored/user.provisioned 等）→ allowed（解除）；其余 None（无副作用）."""
    if current_state in _BLOCKING_SUBJECT_STATES:
        return BLOCK_STATE_BLOCKED
    if current_state == STATUS_STATE_ACTIVE:
        return BLOCK_STATE_ALLOWED
    return None


# ---- 进程内到达记录（契约桩「投递计时」断言基座；T5-5）----
_RECEIVED_EVENTS: dict[str, dict[str, Any]] = {}


def _on_event(payload: dict) -> None:
    """本地订阅处理器：记录事件到达时刻（供投递秒级窗口断言，幂等计数）. """
    if not isinstance(payload, dict):
        return
    event_id = payload.get("event_id")
    if not event_id:
        return
    entry = _RECEIVED_EVENTS.setdefault(
        event_id, {"received_at": _now_timestamp(), "count": 0, "payload": payload}
    )
    entry["count"] += 1


class EventConsumerStub:
    """L1-1 契约桩（模拟 DPS/OpenMemory/OpenRAG 消费端）.

    方法：
    - ``apply``：按 schema v1 校验事件并执行数据面阻断/解除（幂等，重放副作用一次）；
    - ``validate_event_payload``：schema v1 契约校验（缺字段/未知类型 → 400 PARAM_INVALID）；
    - ``check_access``：读取阻断集（桩态对账：blocked → 拒绝语义 / allowed → 放行）；
    - ``subscribe / clear_received / received``：进程内事件到达计时记录（投递窗口断言）。
    """

    CONSUMER_DOMAINS: tuple[str, ...] = tuple(STUB_DATA_DOMAINS.keys())

    # ---- schema 校验（透传 events.validate_event_payload，供 API/桩共用） ----

    @staticmethod
    def validate_event_payload(payload: dict) -> dict:
        """事件 schema v1 契约校验（缺字段/未知事件类型/schema 非 1 → 400）. """
        return validate_event_payload(payload)

    # ---- 数据面阻断/解除（DB 桩态） ----

    @classmethod
    async def apply(
        cls,
        session: AsyncSession,
        payload: dict,
        consumer: str | None = None,
    ) -> dict[str, Any]:
        """契约桩应用事件：按消费端域执行数据面阻断/解除（幂等）.

        Args:
            session: 数据库会话（提交由调用方负责，保证幂等表与阻断集同事务）。
            payload: 事件载荷（schema v1）。
            consumer: 模拟消费端域（dps/openmemory/openrag）；None = 全部桩域。

        Returns:
            {event_id, event_type, results: [{consumer, action, applied, deduplicated,
            effect}]}。
        """
        cls.validate_event_payload(payload)
        event_id = payload["event_id"]
        event_type = payload["event_type"]
        subject = payload["subject"]

        domains: list[str]
        if consumer is None:
            domains = list(cls.CONSUMER_DOMAINS)
        elif consumer in cls.CONSUMER_DOMAINS:
            domains = [consumer]
        else:
            raise BaseError(
                ErrorCode.PARAM_INVALID,
                f"unknown consumer: {consumer}",
                detail={"allowed": list(cls.CONSUMER_DOMAINS)},
            )

        results: list[dict[str, Any]] = []
        for domain in domains:
            result = await cls._apply_one(
                session,
                payload=payload,
                domain=domain,
                action=STUB_DATA_DOMAINS[domain],
            )
            results.append(result)
        logger.info(
            "event consumer stub applied",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "subject_id": subject.get("subject_id"),
                "domains": domains,
            },
        )
        return {"event_id": event_id, "event_type": event_type, "results": results}

    @classmethod
    async def _apply_one(
        cls,
        session: AsyncSession,
        *,
        payload: dict,
        domain: str,
        action: str,
    ) -> dict[str, Any]:
        """单域应用：幂等表去重 → 阻断/解除副作用 → 消费执行记录（同事务）."""
        event_id = payload["event_id"]
        event_type = payload["event_type"]
        subject = payload["subject"]
        subject_id = int(subject["subject_id"])
        subject_type = str(subject.get("subject_type") or "user")
        tenant_code = payload.get("tenant_code")

        # ① 幂等：同 event_id 该消费端已执行 → 跳过副作用（T5-3 断言）
        existing = await session.execute(
            select(EventConsumption).where(
                EventConsumption.event_id == event_id,
                EventConsumption.consumer == domain,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return {
                "consumer": domain,
                "action": action,
                "applied": False,
                "deduplicated": True,
                "effect": None,
            }

        # ② 判定阻断/解除语义并按 (domain, subject_id) 落阻断集（唯一行 upsert）
        state = _block_state_for_current(str(payload.get("current_state")))
        effect: dict[str, Any] | None = None
        if state is not None:
            effect = await cls._upsert_block(
                session,
                domain=domain,
                action=action,
                subject_id=subject_id,
                subject_type=subject_type,
                tenant_code=tenant_code,
                state=state,
                reason=payload.get("reason"),
                event_id=event_id,
            )

        # ③ 消费执行记录（幂等表：(event_id, consumer) 唯一）
        session.add(
            EventConsumption(
                event_id=event_id,
                consumer=domain,
                event_type=event_type,
                subject_id=subject_id,
                subject_type=subject_type,
                tenant_code=tenant_code,
                side_effect=effect,
            )
        )
        await session.flush()
        return {
            "consumer": domain,
            "action": action,
            "applied": True,
            "deduplicated": False,
            "effect": effect,
        }

    @staticmethod
    async def _upsert_block(
        session: AsyncSession,
        *,
        domain: str,
        action: str,
        subject_id: int,
        subject_type: str,
        tenant_code: str | None,
        state: str,
        reason: str | None,
        event_id: str,
    ) -> dict[str, Any]:
        """阻断集 upsert（(domain, subject_id) 唯一；解除不删行，保留状态审计）. """
        import datetime as dt

        now = dt.datetime.now(dt.timezone.utc)
        row_result = await session.execute(
            select(SubjectBlock).where(
                SubjectBlock.domain == domain,
                SubjectBlock.subject_id == subject_id,
            )
        )
        row = row_result.scalar_one_or_none()
        if row is None:
            if state == BLOCK_STATE_ALLOWED:
                # 无既有阻断 → 解除为空操作（仅记录执行，不造 allowed 行）
                return {"domain": domain, "action": action, "state": state, "changed": False}
            row = SubjectBlock(
                domain=domain,
                subject_id=subject_id,
                subject_type=subject_type,
                tenant_code=tenant_code,
                state=state,
                reason=reason,
                event_id=event_id,
                blocked_at=now,
            )
            session.add(row)
        else:
            row.subject_type = subject_type
            row.tenant_code = tenant_code
            row.state = state
            row.reason = reason
            row.event_id = event_id
            if state == BLOCK_STATE_BLOCKED:
                row.blocked_at = now
                row.unblocked_at = None
            else:
                row.unblocked_at = now
        await session.flush()
        return {"domain": domain, "action": action, "state": state, "changed": True}

    # ---- 阻断对账（桩态读；供 GET /identity/blocked/{subject_id}）----

    @staticmethod
    async def load_block(
        session: AsyncSession, subject_id: int, domain: str
    ) -> SubjectBlock | None:
        """读取 (domain, subject_id) 阻断行（不存在返回 None = 未阻断）. """
        result = await session.execute(
            select(SubjectBlock).where(
                SubjectBlock.domain == domain,
                SubjectBlock.subject_id == subject_id,
            )
        )
        return result.scalar_one_or_none()

    # ---- 进程内订阅/到达记录（投递窗口计时断言基座，T5-5）----

    @classmethod
    def subscribe(cls) -> bool:
        """注册契约桩进程内事件订阅（幂等；Redis 不可用本地通道兜底不丢事件）. """
        return local_subscribe(EVENT_CHANNEL, _on_event)

    @staticmethod
    def clear_received() -> None:
        """清空到达记录（用例前置，隔离计数）. """
        _RECEIVED_EVENTS.clear()

    @staticmethod
    def received(event_id: str) -> dict[str, Any] | None:
        """查询某 event_id 的到达记录（received_at=monotonic 时刻/count/原始 payload）."""
        return _RECEIVED_EVENTS.get(event_id)


__all__ = [
    "BLOCK_STATE_ALLOWED",
    "BLOCK_STATE_BLOCKED",
    "STUB_DATA_DOMAINS",
    "EventConsumerStub",
]
