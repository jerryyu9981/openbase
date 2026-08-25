"""Redis 客户端：懒初始化 + 连接失败降级（缓存层可选）.

设计要点（redis-development 规范）：
- 连接池复用、连接超时、键 TTL
- 键命名：openbase:{domain}:{key}
- Redis 不可用时返回 None（调用方回退内存/直连数据库），不阻塞业务
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("openbase.cache")

_client = None
_client_available: bool | None = None


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
