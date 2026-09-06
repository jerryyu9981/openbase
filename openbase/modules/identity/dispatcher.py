"""identity 模块：L1-1 outbox dispatcher（U1 T5，设计草案 §8.2/§8.3/§12.1 风险 3）.

可靠事件源投递主通道（DB outbox 兜底不丢）：
- ``run_once``：轮询 pending（next_retry_at 到期）→ 经 redis_client.publish 发送
  （Redis pub/sub + 进程内本地通道双形态；无 Redis 时本地/DB 兜底不丢）→ 成功置
  published；失败 publish_attempts+1 并按指数退避重排 next_retry_at，超阈值置 failed；
- ``dispatch_event_row`` / ``dispatch_by_event_id``：单事件投递（events apply 契约桩
  与手动 run_once 共用同一投递执行体，保证语义一致）；
- ``start_background_loop``：挂独立 asyncio 后台任务周期投递（草案 §8.2「挂到
  scheduler 或独立后台任务」；部署入口按需启动，可测试触发以 run_once 为准）。

消费端幂等契约由 EventConsumerStub（consumer_stub.py）在 event_id 幂等表兑现
（重放不产生重复阻断副作用，T5-3 断言）。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.cache.redis_client import publish
from openbase.core.models import OutboxEvent
from openbase.modules.identity.events import (
    EVENT_CHANNEL,
    EVENT_STATUS_FAILED,
    EVENT_STATUS_PENDING,
    EVENT_STATUS_PUBLISHED,
)

logger = logging.getLogger("openbase.identity.dispatcher")

# 投递重试策略（草案 §8.2：失败 attempts+1 + next_retry_at 指数退避，超阈值 failed）
MAX_PUBLISH_ATTEMPTS = 5
RETRY_BASE_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 60.0
# 单轮最多扫描的事件数（分批，避免单轮长事务）
RUN_ONCE_BATCH_LIMIT = 200


def retry_delay_seconds(attempt_after: int) -> float:
    """指数退避：1s/2s/4s/… 封顶 60s（attempt_after=1 → base）. """
    return min(RETRY_BASE_DELAY_SECONDS * (2 ** (attempt_after - 1)), RETRY_MAX_DELAY_SECONDS)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class OutboxDispatcherService:
    """outbox 投递服务（轮询 pending → 发布 → 状态推进/指数退避）. """

    _background_task: asyncio.Task | None = None

    # ---- 单事件投递执行体 ----

    @classmethod
    async def dispatch_event_row(
        cls, session: AsyncSession, event: OutboxEvent
    ) -> dict[str, Any]:
        """投递单个 outbox 事件并推进状态（成功 published / 失败退避或 failed）.

        幂等保护：仅 pending 状态可被推进（published/failed 不重复投递）。

        Args:
            session: 数据库会话（提交由调用方负责）。
            event: 待投递的 OutboxEvent 行（须 status=pending）。

        Returns:
            {event_id, event_type, outcome: published|retry|failed|skipped,
            publish_attempts, next_retry_at}。
        """
        if event.status != EVENT_STATUS_PENDING:
            return {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "outcome": "skipped",
                "publish_attempts": event.publish_attempts,
                "next_retry_at": event.next_retry_at,
            }

        now = _utcnow()
        attempts_after = (event.publish_attempts or 0) + 1
        event.publish_attempts = attempts_after

        payload: dict = event.payload if isinstance(event.payload, dict) else {}
        delivered = bool(publish(EVENT_CHANNEL, payload))
        if delivered:
            event.status = EVENT_STATUS_PUBLISHED
            event.published_at = now
            event.next_retry_at = None
            outcome = "published"
        elif attempts_after >= MAX_PUBLISH_ATTEMPTS:
            event.status = EVENT_STATUS_FAILED
            event.next_retry_at = None
            outcome = "failed"
        else:
            event.next_retry_at = now + dt.timedelta(
                seconds=retry_delay_seconds(attempts_after)
            )
            outcome = "retry"

        logger.info(
            "outbox event dispatched",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "outcome": outcome,
                "publish_attempts": event.publish_attempts,
            },
        )
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "outcome": outcome,
            "publish_attempts": event.publish_attempts,
            "next_retry_at": event.next_retry_at,
        }

    @classmethod
    async def dispatch_by_event_id(
        cls, session: AsyncSession, event_id: str
    ) -> dict[str, Any] | None:
        """按 event_id 投递单个 outbox 事件（契约桩 events apply 前置投递用）.

        Returns:
            投递结果 dict；outbox 无该 event_id 返回 None（不抛错，可能为外部事件）。
        """
        result = await session.execute(
            select(OutboxEvent).where(OutboxEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if event is None:
            return None
        return await cls.dispatch_event_row(session, event)

    # ---- run_once：手动触发/后台周期投递入口（可测试触发，T5-5） ----

    @classmethod
    async def run_once(cls, session: AsyncSession) -> dict[str, Any]:
        """轮询一批到期待投递的 pending 事件并逐条投递（提交由调用方负责）.

        Args:
            session: 数据库会话。

        Returns:
            汇总：{scanned, published, retry, failed, skipped}。
        """
        now = _utcnow()
        result = await session.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == EVENT_STATUS_PENDING,
                or_(
                    OutboxEvent.next_retry_at.is_(None),
                    OutboxEvent.next_retry_at <= now,
                ),
            )
            .order_by(OutboxEvent.id)
            .limit(RUN_ONCE_BATCH_LIMIT)
        )
        events = list(result.scalars().all())
        summary = {"scanned": len(events), "published": 0, "retry": 0, "failed": 0, "skipped": 0}
        for event in events:
            outcome = (
                await cls.dispatch_event_row(session, event)
            )["outcome"]
            if outcome == "published":
                summary["published"] += 1
            elif outcome == "retry":
                summary["retry"] += 1
            elif outcome == "failed":
                summary["failed"] += 1
            else:
                summary["skipped"] += 1
        await session.flush()
        return summary

    # ---- 独立后台任务（部署入口启用；测试以 run_once 手动触发为准）----

    @classmethod
    async def start_background_loop(cls, interval_seconds: float = 1.0) -> None:
        """启动周期投递 asyncio 后台任务（幂等：先停旧任务再启新任务）.

        Args:
            interval_seconds: 轮询间隔（草案 §8.2「秒级窗口」）。
        """
        cls.stop_background_loop()

        async def _loop() -> None:
            while True:
                try:
                    from openbase.core.db.session import get_session_factory

                    async with get_session_factory()() as session:
                        await cls.run_once(session)
                        await session.commit()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 - 后台轮询失败不中断循环
                    logger.warning(
                        "outbox dispatcher loop iteration failed",
                        extra={"error": str(exc) or exc.__class__.__name__},
                    )
                await asyncio.sleep(interval_seconds)

        cls._background_task = asyncio.create_task(_loop(), name="identity-outbox-dispatcher")
        logger.info("outbox dispatcher background loop started")

    @classmethod
    def stop_background_loop(cls) -> None:
        """停止后台投递任务（幂等）. """
        if cls._background_task is not None:
            cls._background_task.cancel()
            cls._background_task = None


__all__ = [
    "MAX_PUBLISH_ATTEMPTS",
    "RETRY_BASE_DELAY_SECONDS",
    "RETRY_MAX_DELAY_SECONDS",
    "RUN_ONCE_BATCH_LIMIT",
    "OutboxDispatcherService",
    "retry_delay_seconds",
]
