"""服务 Key 异常检测与告警（E1 §10.3-4）.

覆盖三类边缘常见异常（同一 Key）：

- ``multi_ip``：窗口内出现不同来源 IP 超过阈值（疑似凭证共享/外泄）；
- ``ip_prefix_change``：来源 IP 网段发生跳变（**异地登录的近似判定**：无地理库，
  用 IPv4 前两段 / IPv6 前四组作为"地域"替身，只用于告警不作为拒绝依据）；
- ``rate_spike``：单位时间调用量突增（疑似脚本化滥用）。

设计取舍：检测优先在 **Redis 聚合**（跨实例共享计数/集合/冷却，多实例部署下
同一 Key 的异常不再被分摊到单实例窗口），Redis 不可用或调用失败时**回退进程内**
滑动窗口（保留原行为）；告警落 ``AuditLog`` + 结构化 WARN 日志，同类告警按冷却
窗口抑制，避免日志洪泛。异常只告警、**不阻断**认证（可用性优先，处置由运维吊销
Key 完成）。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("openbase.auth.key_anomaly")

KIND_MULTI_IP = "multi_ip"
KIND_IP_PREFIX_CHANGE = "ip_prefix_change"
KIND_RATE_SPIKE = "rate_spike"
# 审计动作码（超出既有 issue/revoke/rotate 之外的安全事件）
ACTION_SERVICE_KEY_ANOMALY = "auth.service_key.anomaly"
_RESOURCE_SERVICE_KEY = "service_api_keys"
_RATE_WINDOW_SECONDS = 60.0
_MAX_TRACKED_KEYS = 10000
# C-07（P2）：Redis 聚合键（键命名 openbase:{domain}:{key}）
_REDIS_PREFIX = "openbase:key_anomaly"


def resolve_client_ip(request: Request) -> str:
    """提取来源 IP（默认只信连接层，显式配置后才采信 ``X-Forwarded-For``）."""
    from openbase.settings import get_settings

    if get_settings().key_anomaly_trust_forwarded_for:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", "") or ""


def ip_prefix(ip: str) -> str:
    """IP 网段（异地近似的"地域"键）：IPv4 前两段；IPv6 前四组."""
    if not ip:
        return ""
    if ":" in ip:
        return ":".join(ip.split(":")[:4])
    return ".".join(ip.split(".")[:2])


def _anomaly(kind: str, key_id: str, ip: str, **detail: Any) -> dict[str, Any]:
    """构造一条告警（不含凭证明文）."""
    return {"kind": kind, "key_id": key_id, "ip": ip, "detail": detail}


def _redis_cooldown_allows(client: Any, key_id: str, kind: str, cooldown: float) -> bool:
    """跨实例冷却（``SET NX EX``）：首次告警返回 True，冷却窗口内返回 False."""
    return bool(
        client.set(
            f"{_REDIS_PREFIX}:cool:{key_id}:{kind}",
            "1",
            nx=True,
            ex=int(cooldown),
        )
    )


def _observe_redis(
    client: Any,
    key_id: str,
    ip: str,
    *,
    window: float,
    cooldown: float,
    max_ips: int,
    rate_limit: int,
) -> list[dict[str, Any]]:
    """Redis 聚合观测（跨实例共享计数/集合/冷却；异常向上抛出由调用方回退）."""
    alerts: list[dict[str, Any]] = []

    def emit(kind: str, **detail: Any) -> None:
        if _redis_cooldown_allows(client, key_id, kind, cooldown):
            alerts.append(_anomaly(kind, key_id, ip, **detail))

    rate_key = f"{_REDIS_PREFIX}:rate:{key_id}"
    count = int(client.incr(rate_key))
    if count == 1:
        client.expire(rate_key, int(_RATE_WINDOW_SECONDS))
    if rate_limit > 0 and count > rate_limit:
        emit(KIND_RATE_SPIKE, count=count, window_seconds=int(_RATE_WINDOW_SECONDS))

    if ip:
        ips_key = f"{_REDIS_PREFIX}:ips:{key_id}"
        previous = set(client.smembers(ips_key) or ())
        previous_prefixes = {ip_prefix(item) for item in previous}
        if previous and previous_prefixes and ip_prefix(ip) not in previous_prefixes:
            emit(
                KIND_IP_PREFIX_CHANGE,
                previous_prefixes=sorted(previous_prefixes),
                current_prefix=ip_prefix(ip),
            )
        client.sadd(ips_key, ip)
        client.expire(ips_key, int(window))
        distinct = int(client.scard(ips_key))
        if max_ips > 0 and distinct > max_ips:
            emit(KIND_MULTI_IP, distinct_ips=distinct, window_seconds=int(window))
    return alerts


class KeyAnomalyTracker:
    """进程内异常检测器（按 Key 维护窗口状态；线程/协程安全由锁保证）."""

    def __init__(self) -> None:
        """初始化空状态."""
        self._lock = threading.Lock()
        self._states: dict[str, dict[str, Any]] = {}

    def reset(self) -> None:
        """清空全部状态（测试与配置热更新用）."""
        with self._lock:
            self._states.clear()

    def observe(self, key_id: str, ip: str, *, now: float | None = None) -> list[dict[str, Any]]:
        """记录一次成功校验并返回本次触发的告警列表.

        Args:
            key_id: 服务 Key 稳定标识。
            ip: 来源 IP（空值仅计数，不参与 IP 维度判定）。
            now: 当前时间（测试注入）。

        Returns:
            告警列表（已按冷却窗口去重）；无异常返回空列表。
        """
        from openbase.settings import get_settings

        settings = get_settings()
        if not settings.key_anomaly_enabled or not key_id:
            return []
        timestamp = time.monotonic() if now is None else now
        window = max(float(settings.key_anomaly_window_seconds), 1.0)
        cooldown = max(float(settings.key_anomaly_alert_cooldown_seconds), 1.0)
        max_ips = int(settings.key_anomaly_max_ips)
        rate_limit = int(settings.key_anomaly_rate_per_minute)

        # C-07（P2）：生产路径（未注入时间）优先 Redis 跨实例聚合；
        # 注入 now 的调用为确定性单测/回放，固定走进程内窗口。
        if now is None:
            try:
                from openbase.core.cache.redis_client import get_client

                client = get_client()
                if client is not None:
                    return _observe_redis(
                        client,
                        key_id,
                        ip,
                        window=window,
                        cooldown=cooldown,
                        max_ips=max_ips,
                        rate_limit=rate_limit,
                    )
            except Exception as exc:  # noqa: BLE001 - Redis 异常回退进程内，不阻断认证
                logger.warning(
                    "key anomaly redis aggregation failed; fallback to process window",
                    extra={
                        "key_id": key_id,
                        "error": str(exc) or exc.__class__.__name__,
                    },
                )

        with self._lock:
            if key_id not in self._states and len(self._states) >= _MAX_TRACKED_KEYS:
                self._states.clear()  # 容量兜底：极端场景重置，避免无界增长
            state = self._states.setdefault(
                key_id, {"ips": {}, "rate_start": timestamp, "rate_count": 0, "alerts": {}}
            )
            # 窗口裁剪
            stale = [item for item, seen in state["ips"].items() if timestamp - seen > window]
            for item in stale:
                del state["ips"][item]

            alerts: list[dict[str, Any]] = []
            if timestamp - state["rate_start"] > _RATE_WINDOW_SECONDS:
                state["rate_start"] = timestamp
                state["rate_count"] = 0
            state["rate_count"] += 1

            def emit(kind: str, **detail: Any) -> None:
                """按冷却窗口抑制同类告警."""
                last = state["alerts"].get(kind, 0.0)
                if timestamp - last < cooldown:
                    return
                state["alerts"][kind] = timestamp
                alerts.append(_anomaly(kind, key_id, ip, **detail))

            if rate_limit > 0 and state["rate_count"] > rate_limit:
                emit(KIND_RATE_SPIKE, count=state["rate_count"], window_seconds=int(_RATE_WINDOW_SECONDS))

            if ip:
                previous_prefixes = {ip_prefix(item) for item in state["ips"]}
                if (
                    state["ips"]
                    and previous_prefixes
                    and ip_prefix(ip) not in previous_prefixes
                ):
                    emit(
                        KIND_IP_PREFIX_CHANGE,
                        previous_prefixes=sorted(previous_prefixes),
                        current_prefix=ip_prefix(ip),
                    )
                state["ips"][ip] = timestamp
                if max_ips > 0 and len(state["ips"]) > max_ips:
                    emit(KIND_MULTI_IP, distinct_ips=len(state["ips"]), window_seconds=int(window))
            return alerts


_tracker = KeyAnomalyTracker()


def get_tracker() -> KeyAnomalyTracker:
    """全局检测器（进程内单例）."""
    return _tracker


async def report_anomalies(
    session: AsyncSession,
    *,
    credential: dict[str, Any],
    anomalies: list[dict[str, Any]],
    request_id: str | None = None,
) -> None:
    """告警落库（审计）+ 结构化 WARN；失败不阻断认证.

    审计只记 Key 元数据、来源 IP 与告警类型，不含明文/哈希。
    显式提交（与 ``touch_last_used`` 同口径），失败回滚并降级为日志。
    """
    if not anomalies:
        return
    from openbase.core.models import AuditLog

    key_id = str(credential.get("id") or "")
    logger.warning(
        "service_key_anomaly",
        extra={
            "key_id": key_id,
            "tenant_code": credential.get("tenant_code"),
            "kinds": [item["kind"] for item in anomalies],
            "source_ip": anomalies[0].get("ip"),
            "request_id": request_id,
        },
    )
    try:
        session.add(
            AuditLog(
                user_id=None,
                action=ACTION_SERVICE_KEY_ANOMALY,
                resource=_RESOURCE_SERVICE_KEY,
                resource_id=key_id,
                request_id=request_id or f"anomaly-{key_id}",
                detail={
                    "key_name": credential.get("name"),
                    "tenant_code": credential.get("tenant_code"),
                    "anomalies": anomalies,
                },
            )
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001 - 告警写入失败不影响认证
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 - rollback 失败仅记录
            pass
        logger.warning(
            "service key anomaly audit persist failed",
            extra={"key_id": key_id, "error": str(exc) or exc.__class__.__name__},
        )
