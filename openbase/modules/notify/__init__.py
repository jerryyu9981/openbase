"""notify 模块：通知中心（SSE 推送/站内信/已读管理，数据库优先 + 内存回退）."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.services import BaseDBService
from openbase.core.db.session import get_db
from openbase.core.models import Notification

logger = logging.getLogger("openbase.notify")

router = APIRouter(prefix="/api/v1/notifications", tags=["notify"])

# 内存回退存储
_notifications: list[dict] = []
_next_id = 1
# SSE 订阅者队列（channel -> queue）
_subscribers: dict[str, list[asyncio.Queue]] = {}


class NotificationCreate(BaseModel):
    """创建通知请求."""

    user_id: int
    title: str
    content: str | None = None
    type: int = 1  # 1=站内信 2=SSE 3=系统


class NotificationOut(BaseModel):
    """通知响应."""

    id: int
    user_id: int
    title: str
    content: str | None
    type: int
    is_read: bool


def _to_out(n: dict) -> NotificationOut:
    return NotificationOut(
        id=n["id"], user_id=n["user_id"], title=n["title"],
        content=n.get("content"), type=n.get("type", 1), is_read=bool(n.get("is_read")),
    )


async def publish(channel: str, payload: dict) -> None:
    """发布消息到 SSE 通道（本地队列 + Redis 跨实例广播）."""
    message = json.dumps(payload, ensure_ascii=False)
    # 本地订阅者（单实例 SSE 直推）
    for queue in _subscribers.get(channel, []):
        await queue.put(message)
    # Redis 广播（多实例场景，其他实例可订阅 channel 接收）
    from openbase.core.cache.redis_client import pub as redis_pub

    redis_pub(f"openbase:notify:{channel}", payload)


class NotificationService(BaseDBService):
    """通知服务：数据库优先 + 内存回退."""

    @classmethod
    async def create(cls, session: AsyncSession, user_id: int, title: str,
                     content: str | None, type_: int) -> dict:
        n = Notification(user_id=user_id, title=title, content=content, type=type_)
        session.add(n)
        await session.commit()
        return {"id": n.id, "user_id": user_id, "title": title, "content": content,
                "type": type_, "is_read": False}

    @classmethod
    async def list_by_user(cls, session: AsyncSession, user_id: int) -> list[dict]:
        rows = (
            await session.execute(
                select(Notification).where(Notification.user_id == user_id).order_by(Notification.id)
            )
        ).scalars().all()
        return [{"id": r.id, "user_id": r.user_id, "title": r.title, "content": r.content,
                 "type": r.type, "is_read": r.is_read} for r in rows]

    @classmethod
    async def mark_read(cls, session: AsyncSession, notification_id: int) -> dict | None:
        r = (await session.execute(select(Notification).where(Notification.id == notification_id))).scalar_one_or_none()
        if r is None:
            return None
        r.is_read = True
        r.read_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
        return {"id": r.id, "user_id": r.user_id, "title": r.title, "content": r.content,
                "type": r.type, "is_read": True}

    @classmethod
    async def mark_all_read(cls, session: AsyncSession, user_id: int) -> int:
        rows = (
            await session.execute(select(Notification).where(Notification.user_id == user_id))
        ).scalars().all()
        for r in rows:
            r.is_read = True
            r.read_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
        return len(rows)

    # ---- 内存回退 ----
    @classmethod
    async def create_mem(cls, user_id: int, title: str, content: str | None, type_: int) -> dict:
        global _next_id
        n = {"id": _next_id, "user_id": user_id, "title": title, "content": content,
             "type": type_, "is_read": False}
        _notifications.append(n)
        _next_id += 1
        return n

    @classmethod
    async def list_by_user_mem(cls, user_id: int) -> list[dict]:
        return [n for n in _notifications if n["user_id"] == user_id]

    @classmethod
    async def mark_read_mem(cls, notification_id: int) -> dict | None:
        for n in _notifications:
            if n["id"] == notification_id:
                n["is_read"] = True
                return n
        return None

    @classmethod
    async def mark_all_read_mem(cls, user_id: int) -> int:
        count = 0
        for n in _notifications:
            if n["user_id"] == user_id:
                n["is_read"] = True
                count += 1
        return count


@router.post("", response_model=NotificationOut)
async def create_notification(
    req: NotificationCreate, session: AsyncSession = Depends(get_db)
) -> NotificationOut:
    """创建通知（站内信/系统；落库）."""
    try:
        notification = await NotificationService.create(session, req.user_id, req.title, req.content, req.type)
    except Exception as exc:  # noqa: BLE001
        NotificationService._fallback("notify.create", exc)
        notification = await NotificationService.create_mem(req.user_id, req.title, req.content, req.type)
    if req.type == 2:  # SSE 推送
        await publish(f"user:{req.user_id}", notification)
    return _to_out(notification)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user_id: int, session: AsyncSession = Depends(get_db)
) -> list[NotificationOut]:
    """通知列表（按 user_id 过滤）."""
    try:
        rows = await NotificationService.list_by_user(session, user_id)
    except Exception as exc:  # noqa: BLE001
        NotificationService._fallback("notify.list", exc)
        rows = await NotificationService.list_by_user_mem(user_id)
    return [_to_out(n) for n in rows]


@router.get("/stream")
async def stream(user_id: int) -> StreamingResponse:
    """SSE 推送流（长连接）.

    Returns:
        text/event-stream 响应。
    """
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(f"user:{user_id}", []).append(queue)

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            _subscribers[f"user:{user_id}"].remove(queue)
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: int, session: AsyncSession = Depends(get_db)
) -> NotificationOut:
    """标记已读."""
    try:
        n = await NotificationService.mark_read(session, notification_id)
    except Exception as exc:  # noqa: BLE001
        NotificationService._fallback("notify.read", exc)
        n = await NotificationService.mark_read_mem(notification_id)
    if n is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.PARAM_NOT_FOUND, "notification not found")
    return _to_out(n)


@router.post("/read-all", response_model=dict)
async def mark_all_read(user_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    """全部已读."""
    try:
        await NotificationService.mark_all_read(session, user_id)
    except Exception as exc:  # noqa: BLE001
        NotificationService._fallback("notify.read_all", exc)
        await NotificationService.mark_all_read_mem(user_id)
    return {"read_all": True}


# ---- 多实例 SSE 订阅接收（TD-11-04，BL-109） ----


def _redis_message_handler(channel: str, payload: dict) -> None:
    """Redis 广播消息处理器：按 user id 推送到本地 SSE 订阅队列.

    channel 形如 openbase:notify:user:{user_id}。
    """
    user_id = str(payload.get("user_id", ""))
    if not user_id:
        return
    local_channel = f"user:{user_id}"
    message = json.dumps(payload, ensure_ascii=False)
    for queue in _subscribers.get(local_channel, []):
        try:
            queue.put_nowait(message)
        except Exception:  # noqa: BLE001
            logger.debug("sse queue full or closed", extra={"channel": local_channel})


def start_redis_subscriber() -> bool:
    """启动 Redis 频道模式订阅（跨实例 SSE 广播接收）.

    单实例场景 Redis 广播直接由本地 publish 处理，无需订阅；
    多实例场景实例 B 通过订阅接收实例 A 发布的广播。
    Redis 不可用时返回 False（保持单实例本地队列模式）。

    Returns:
        订阅是否启动成功。
    """
    from openbase.core.cache.redis_client import subscribe_pattern

    return subscribe_pattern("openbase:notify:user:*", _redis_message_handler)


# 应用启动时自动启动订阅（模块导入即注册，实例级）
start_redis_subscriber()

__version__ = "1.1.0"
