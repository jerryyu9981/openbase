"""notify 模块：通知中心（SSE 推送/站内信/已读管理）."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/notifications", tags=["notify"])

# 内存通知存储（v1.0.0 最小实现，生产接数据库）
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


async def publish(channel: str, payload: dict) -> None:
    """发布消息到 SSE 通道."""
    message = json.dumps(payload, ensure_ascii=False)
    for queue in _subscribers.get(channel, []):
        await queue.put(message)


@router.post("", response_model=NotificationOut)
async def create_notification(req: NotificationCreate) -> NotificationOut:
    """创建通知（站内信/系统）."""
    global _next_id
    notification = {
        "id": _next_id,
        "user_id": req.user_id,
        "title": req.title,
        "content": req.content,
        "type": req.type,
        "is_read": False,
    }
    _notifications.append(notification)
    _next_id += 1
    if req.type == 2:  # SSE 推送
        await publish(f"user:{req.user_id}", notification)
    return NotificationOut(**notification)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(user_id: int) -> list[NotificationOut]:
    """通知列表（按 user_id 过滤）."""
    return [
        NotificationOut(**n) for n in _notifications if n["user_id"] == user_id
    ]


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
async def mark_read(notification_id: int) -> NotificationOut:
    """标记已读."""
    for n in _notifications:
        if n["id"] == notification_id:
            n["is_read"] = True
            return NotificationOut(**n)
    from openbase.core.errors import BaseError, ErrorCode

    raise BaseError(ErrorCode.PARAM_NOT_FOUND, "notification not found")


@router.post("/read-all", response_model=dict)
async def mark_all_read(user_id: int) -> dict:
    """全部已读."""
    for n in _notifications:
        if n["user_id"] == user_id:
            n["is_read"] = True
    return {"read_all": True}
