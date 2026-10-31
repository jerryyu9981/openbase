"""OIDC 登出联动存储（C-03 ``id_token_hint`` + C-04 back-channel logout）.

- **id_token_hint**：回调成功后按 ``client_id + 统一主体 sub`` 保存 ID Token
  （记录同时带 ``issuer``，取回时校验），TTL 对齐 refresh 有效期；登出时透传给
  IdP（RP-Initiated Logout），不落日志、不落库明文；
- **sid 索引**：保存 ``sid → 统一主体 sub``，供仅携带 ``sid`` 的 back-channel
  logout token 定位主体；
- **jti 一次性**：logout token 的 ``jti`` 以 SET NX 语义消费（Redis 原子；
  Redis 不可用回退进程内），防重放。

Redis 不可用时一律回退进程内（单实例语义，不新增放行）。
"""

from __future__ import annotations

import json
import logging
import threading
import time

from openbase.core.cache import redis_client

logger = logging.getLogger("openbase.auth.oidc")

HINT_KEY_PREFIX = "openbase:oidc:id_token_hint:"
SID_KEY_PREFIX = "openbase:oidc:logout_sid:"
SUB_KEY_PREFIX = "openbase:oidc:logout_sub:"
JTI_KEY_PREFIX = "openbase:oidc:logout_jti:"
DEFAULT_TTL_SECONDS = 300

__all__ = [
    "DEFAULT_TTL_SECONDS",
    "HINT_KEY_PREFIX",
    "JTI_KEY_PREFIX",
    "OidcLogoutStore",
    "SID_KEY_PREFIX",
    "SUB_KEY_PREFIX",
    "get_logout_store",
]


def _now() -> float:
    """单调时钟（不受系统时间跳变影响）."""
    return time.monotonic()


def _hint_key(client_id: str, subject: str) -> str:
    return f"{HINT_KEY_PREFIX}{client_id}:{subject}"


def _sid_key(client_id: str, sid: str) -> str:
    return f"{SID_KEY_PREFIX}{client_id}:{sid}"


def _sub_key(client_id: str, idp_subject: str) -> str:
    return f"{SUB_KEY_PREFIX}{client_id}:{idp_subject}"


def _jti_key(client_id: str, jti: str) -> str:
    return f"{JTI_KEY_PREFIX}{client_id}:{jti}"


class OidcLogoutStore:
    """登出联动存储（hint / sid / jti；Redis 优先，进程内兜底）."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl_seconds = int(ttl_seconds)
        self._local: dict[str, tuple[float, str]] = {}
        # 可重入锁：写路径持锁后调用 _prune（同样需要锁），避免自死锁
        self._lock = threading.RLock()

    def save_id_token_hint(
        self,
        *,
        client_id: str,
        subject: str,
        issuer: str,
        id_token: str,
        sid: str = "",
        idp_subject: str = "",
        ttl_seconds: int | None = None,
    ) -> None:
        """保存 ID Token（含 issuer）与可选 sid / IdP sub 索引；value 不落日志."""
        ttl = int(ttl_seconds if ttl_seconds is not None else self._ttl_seconds)
        entries = [
            (
                _hint_key(client_id, subject),
                json.dumps(
                    {"issuer": issuer, "id_token": id_token}, ensure_ascii=False
                ),
            )
        ]
        if sid:
            entries.append((_sid_key(client_id, sid), subject))
        idp_sub = (idp_subject or "").strip()
        if idp_sub:
            entries.append((_sub_key(client_id, idp_sub), subject))
        client = redis_client.get_client()
        if client is not None:
            try:
                for key, value in entries:
                    client.set(key, value, ex=ttl)
                return
            except Exception as exc:  # noqa: BLE001 - 降级到进程内，不阻塞登录
                logger.warning(
                    "oidc logout store redis write failed, fallback to memory",
                    extra={"error": str(exc) or exc.__class__.__name__},
                )
        expires_at = _now() + ttl
        with self._lock:
            self._prune()
            for key, value in entries:
                self._local[key] = (expires_at, value)

    def id_token_hint(self, *, client_id: str, subject: str, issuer: str = "") -> str:
        """取回 ID Token；issuer 非空且与记录不一致时视为未命中."""
        raw = self._get(_hint_key(client_id, subject))
        if not raw:
            return ""
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("oidc id_token_hint payload is not valid json")
            return ""
        if not isinstance(record, dict):
            return ""
        recorded_issuer = str(record.get("issuer") or "")
        if issuer and recorded_issuer and recorded_issuer != issuer:
            return ""
        return str(record.get("id_token") or "")

    def subject_for_sid(self, *, client_id: str, sid: str) -> str:
        """按 sid 索引解析统一主体 sub；未命中返回空串."""
        return self._get(_sid_key(client_id, sid)) or ""

    def subject_for_idp_sub(self, *, client_id: str, idp_subject: str) -> str:
        """按 IdP sub 索引解析统一主体 sub；未命中返回空串."""
        return self._get(_sub_key(client_id, idp_subject)) or ""

    def clear(self, *, client_id: str, subject: str, sid: str = "") -> None:
        """清理 hint 与 sid 索引（登出后一次性使用）."""
        keys = [_hint_key(client_id, subject)]
        if sid:
            keys.append(_sid_key(client_id, sid))
        client = redis_client.get_client()
        if client is not None:
            try:
                client.delete(*keys)
            except Exception as exc:  # noqa: BLE001 - 清理失败仅告警
                logger.warning(
                    "oidc logout store redis delete failed",
                    extra={"error": str(exc) or exc.__class__.__name__},
                )
        with self._lock:
            for key in keys:
                self._local.pop(key, None)

    def consume_jti(
        self, *, client_id: str, jti: str, ttl_seconds: int | None = None
    ) -> bool:
        """消费 logout token 的 jti（首次 True，重放 False）."""
        ttl = int(ttl_seconds if ttl_seconds is not None else self._ttl_seconds)
        key = _jti_key(client_id, jti)
        client = redis_client.get_client()
        if client is not None:
            try:
                return bool(client.set(key, "1", nx=True, ex=ttl))
            except Exception as exc:  # noqa: BLE001 - 降级到进程内
                logger.warning(
                    "oidc logout store redis jti write failed, fallback to memory",
                    extra={"error": str(exc) or exc.__class__.__name__},
                )
        with self._lock:
            self._prune()
            entry = self._local.get(key)
            if entry is not None and entry[0] > _now():
                return False
            self._local[key] = (_now() + ttl, "1")
            return True

    def clear_all(self) -> None:
        """清空进程内条目（测试隔离用）."""
        with self._lock:
            self._local.clear()

    def _get(self, key: str) -> str | None:
        """读取键值：Redis 优先，未命中/不可用回退进程内（带 TTL 校验）."""
        client = redis_client.get_client()
        if client is not None:
            try:
                raw = client.get(key)
            except Exception as exc:  # noqa: BLE001 - 继续查进程内
                logger.warning(
                    "oidc logout store redis read failed, fallback to memory",
                    extra={"error": str(exc) or exc.__class__.__name__},
                )
                raw = None
            if raw:
                return raw
        with self._lock:
            entry = self._local.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= _now():
                self._local.pop(key, None)
                return None
            return value

    def _prune(self) -> None:
        """清理已过期的进程内条目（避免无界增长）."""
        now = _now()
        with self._lock:
            expired_keys = [
                key
                for key, (expires_at, _) in self._local.items()
                if expires_at <= now
            ]
            for key in expired_keys:
                self._local.pop(key, None)


_logout_store: OidcLogoutStore | None = None


def get_logout_store() -> OidcLogoutStore:
    """获取登出联动存储单例（进程内字典部分；TTL 由调用方传入）."""
    global _logout_store
    if _logout_store is None:
        _logout_store = OidcLogoutStore()
    return _logout_store
