"""Redis 客户端：懒初始化 + 连接失败降级（缓存层可选）.

设计要点（redis-development 规范）：
- 连接池复用、连接超时、键 TTL
- 键命名：openbase:{domain}:{key}
- Redis 不可用时返回 None（调用方回退内存/直连数据库），不阻塞业务
- U1 T5（L1-1）事件投递：publish/subscribe 双形态 —— Redis 广播（跨进程消费端）
  + 进程内本地通道兜底（无 Redis 时契约桩/同进程消费端不丢事件；DB outbox 仍为
  可靠主通道，草案 §8.2/§12.1 风险 3）
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

logger = logging.getLogger("openbase.cache")

_client = None
_client_available: bool | None = None

# ---- U1 T5（L1-1）：进程内事件订阅注册表（Redis 不可用时的本地通道兜底） ----
# publish 先投递本地处理器（同步，确定性），再尽力 Redis 广播（跨进程）。
# 本地处理器与 Redis 订阅互斥（subscribe 仅注册本地，远程消费端自行订阅 Redis 频道），
# 避免同进程重复投递。
_LOCAL_EVENT_HANDLERS: dict[str, set[Any]] = {}
_LOCAL_EVENT_LOCK = threading.Lock()


def get_client():
    """获取 Redis 客户端（懒初始化；不可用时返回 None）.

    Returns:
        redis.Redis；Redis 不可用时返回 None。
    """
    global _client, _client_available
    if _client_available is False:
        return None
    if _client is None:
        try:
            from redis import Redis

            from openbase.settings import get_settings

            settings = get_settings()
            _client = Redis.from_url(
                settings.redis_url,
                socket_timeout=2,
                socket_connect_timeout=2,
                decode_responses=True,
            )
            _client.ping()
            _client_available = True
            logger.info("redis cache enabled", extra={"url": settings.redis_url.split("@")[-1]})
        except Exception as exc:  # noqa: BLE001
            _client_available = False
            logger.warning("redis unavailable, cache disabled: %s", exc)
            return None
    return _client


def cache_get(key: str) -> Any | None:
    """读取缓存 JSON 值.

    Args:
        key: 缓存键（内部自动加 openbase: 前缀）。

    Returns:
        反序列化值；未命中或 Redis 不可用返回 None。
    """
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(f"openbase:{key}")
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """写入缓存 JSON 值（带 TTL）.

    Args:
        key: 缓存键。
        value: 可 JSON 序列化值。
        ttl: 过期秒数（默认 300s，对齐设计文档 dict TTL 5min）。

    Returns:
        是否写入成功（Redis 不可用返回 False）。
    """
    client = get_client()
    if client is None:
        return False
    try:
        return bool(client.set(f"openbase:{key}", json.dumps(value, ensure_ascii=False), ex=ttl))
    except Exception:  # noqa: BLE001
        return False


def cache_delete(*keys: str) -> bool:
    """删除缓存键（配置变更/数据变更时失效）.

    Args:
        keys: 缓存键列表。

    Returns:
        是否执行成功。
    """
    client = get_client()
    if client is None:
        return False
    try:
        client.delete(*[f"openbase:{k}" for k in keys])
        return True
    except Exception:  # noqa: BLE001
        return False


def subscribe(channel: str, handler: Any) -> bool:
    """注册进程内事件处理器（U1 T5 契约桩/本地消费端；Redis 不可用不丢事件）.

    Args:
        channel: 频道名（如 openbase:identity:events）。
        handler: 消息处理回调（payload: dict）——本地通道同步调用。

    Returns:
        是否注册成功。
    """
    with _LOCAL_EVENT_LOCK:
        _LOCAL_EVENT_HANDLERS.setdefault(channel, set()).add(handler)
    logger.info("local event subscriber registered", extra={"channel": channel})
    return True


def unsubscribe(channel: str, handler: Any) -> bool:
    """注销进程内事件处理器（幂等；供测试清理）."""
    with _LOCAL_EVENT_LOCK:
        handlers = _LOCAL_EVENT_HANDLERS.get(channel)
        if handlers is not None:
            handlers.discard(handler)
            if not handlers:
                _LOCAL_EVENT_HANDLERS.pop(channel, None)
    return True


def publish(channel: str, payload: dict) -> bool:
    """发布事件：先投递本地进程内处理器，再尽力向 Redis 广播（双形态，草案 §8.2）.

    本地投递保证同进程契约桩/订阅端确定性收到（Redis 不可用时仍可达）；
    Redis 广播供跨进程真实消费端（S2/S3/S5 DPS/OpenMemory/OpenRAG）订阅。

    Args:
        channel: 频道名。
        payload: 事件载荷（可 JSON 序列化 dict）。

    Returns:
        True 表示至少一个通道投递成功（本地有处理器或 Redis 发布成功）；
        False 表示无任何通道可达 —— 调用方（outbox dispatcher）重试退避，不丢事件。
    """
    delivered_local = False
    with _LOCAL_EVENT_LOCK:
        handlers = tuple(_LOCAL_EVENT_HANDLERS.get(channel, ()))
    for handler in handlers:
        try:
            handler(payload)
            delivered_local = True
        except Exception as exc:  # noqa: BLE001 - 单处理器失败不影响其他通道
            logger.debug(
                "local event handler failed",
                extra={"channel": channel, "error": str(exc) or exc.__class__.__name__},
            )

    client = get_client()
    if client is not None:
        try:
            client.publish(channel, json.dumps(payload, ensure_ascii=False))
            return True
        except Exception as exc:  # noqa: BLE001 - Redis 发布失败 → 本地已投递则兜底成功
            logger.warning(
                "redis publish failed; local channel fallback",
                extra={"channel": channel, "error": str(exc) or exc.__class__.__name__},
            )
    return delivered_local


def pub(channel: str, payload: dict) -> bool:
    """发布消息到 Redis channel（SSE 跨实例推送）.

    Args:
        channel: 频道名（如 notify:user:1）。
        payload: 消息负载。

    Returns:
        是否发布成功。
    """
    client = get_client()
    if client is None:
        return False
    try:
        client.publish(channel, json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:  # noqa: BLE001
        return False


def subscribe_pattern(pattern: str, handler) -> bool:
    """启动后台线程订阅 Redis 频道模式（多实例 SSE 广播接收）.

    订阅线程持续运行，收到消息调用 handler(channel, payload_dict)；
    Redis 不可用时返回 False（调用方回退单实例本地队列）。

    Args:
        pattern: 频道模式（如 openbase:notify:user:*）。
        handler: 消息处理回调（channel: str, payload: dict）。

    Returns:
        订阅是否启动成功。
    """
    client = get_client()
    if client is None:
        return False
    import threading

    def _run() -> None:
        pubsub = client.pubsub()
        try:
            pubsub.psubscribe(pattern)
            for message in pubsub.listen():
                if message.get("type") != "pmessage":
                    continue
                try:
                    payload = json.loads(message.get("data") or "{}")
                    handler(message.get("channel", ""), payload)
                except Exception:  # noqa: BLE001
                    logger.debug("subscribe handler failed", extra={"pattern": pattern})
        except Exception:  # noqa: BLE001
            logger.warning("redis subscribe stopped", extra={"pattern": pattern})
        finally:
            try:
                pubsub.close()
            except Exception:  # noqa: BLE001
                pass

    threading.Thread(target=_run, name=f"redis-sub-{pattern}", daemon=True).start()
    logger.info("redis subscribe started", extra={"pattern": pattern})
    return True
