"""OIDC 授权码流程 state 存储（一次性消费 + TTL + 多实例共享）.

背景（v1.14.0 P1 安全硬化）：原实现以进程内 dict 保存 state，无锁、无 TTL
且不回收，导致（1）多实例部署时回调落到另一个实例必然失败；（2）长期运行
内存只增不减。本模块把 state 收敛为**一次性凭据**：

- 优先 Redis（``GETDEL`` 原子消费 + ``EX`` 过期），多实例天然共享；
- Redis 不可用时回退进程内字典（带 TTL 与线程锁，单实例可用），
  降级只影响多实例场景，不阻塞登录；
- 键与缓存层统一前缀 ``openbase:``，便于运维识别与清理。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Mapping
from typing import Any

from openbase.core.cache import redis_client

logger = logging.getLogger("openbase.auth.oidc")

STATE_KEY_PREFIX = "openbase:oidc:state:"
DEFAULT_TTL_SECONDS = 600

__all__ = [
    "DEFAULT_TTL_SECONDS",
    "OidcStateStore",
    "STATE_KEY_PREFIX",
    "get_state_store",
]


def _now() -> float:
    """单调时钟（测试可替换；不受系统时间跳变影响）."""
    return time.monotonic()


class OidcStateStore:
    """授权码流程 state 存储（一次性消费语义）."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl_seconds = int(ttl_seconds)
        self._local: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def issue(
        self, state: str, payload: Mapping[str, Any], *, ttl_seconds: int | None = None
    ) -> None:
        """登记 state 及其关联载荷（nonce / code_verifier）.

        Args:
            state: 已生成的随机 state（授权请求与回调共享）。
            payload: 需在回调时取回的载荷（JSON 可序列化）。
            ttl_seconds: 本次有效期；None 时使用实例默认值。
        """
        effective_ttl = int(ttl_seconds if ttl_seconds is not None else self._ttl_seconds)
        data = dict(payload)
        client = redis_client.get_client()
        if client is not None:
            try:
                client.set(
                    STATE_KEY_PREFIX + state,
                    json.dumps(data, ensure_ascii=False),
                    ex=effective_ttl,
                )
                return
            except Exception as exc:  # noqa: BLE001 - 降级到进程内，不阻塞登录
                logger.warning(
                    "oidc state redis write failed, fallback to memory",
                    extra={"error": str(exc) or exc.__class__.__name__},
                )
        expires_at = _now() + effective_ttl
        self._prune()
        with self._lock:
            self._local[state] = (expires_at, data)

    def consume(self, state: str) -> dict[str, Any] | None:
        """消费 state（成功即失效）.

        Returns:
            关联载荷；state 不存在/已过期/已消费返回 None。
        """
        client = redis_client.get_client()
        if client is not None:
            try:
                raw = client.getdel(STATE_KEY_PREFIX + state)
            except Exception as exc:  # noqa: BLE001 - 继续查进程内（可能为降级写入）
                logger.warning(
                    "oidc state redis read failed, fallback to memory",
                    extra={"error": str(exc) or exc.__class__.__name__},
                )
                raw = None
            if raw:
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("oidc state payload is not valid json")
                    return None
        with self._lock:
            entry = self._local.pop(state, None)
        if entry is None:
            return None
        expires_at, data = entry
        if expires_at <= _now():
            return None
        return data

    def clear(self) -> None:
        """清空进程内 state（测试隔离用）."""
        with self._lock:
            self._local.clear()

    def _prune(self) -> None:
        """清理已过期的进程内条目（避免无界增长）."""
        now = _now()
        with self._lock:
            expired_states = [
                state for state, (expires_at, _) in self._local.items() if expires_at <= now
            ]
            for state in expired_states:
                self._local.pop(state, None)


_state_store: OidcStateStore | None = None


def get_state_store() -> OidcStateStore:
    """获取 state 存储单例（进程内字典部分；TTL 按调用方设置传入）."""
    global _state_store
    if _state_store is None:
        _state_store = OidcStateStore()
    return _state_store
