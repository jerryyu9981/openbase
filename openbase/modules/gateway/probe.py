"""健康探测逻辑（对齐技术方案 §3.4）：连续 3 次失败剔除 + 冷却期后恢复.

探测由 scheduler interval job 调用；转发级熔断（5xx/超时累加）在
ConfigProbeProvider 中结合 registry.mark_unhealthy 实现。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from openbase.modules.gateway.discovery import ServiceInstance
from openbase.modules.gateway.registry import DiscoveryRegistry

logger = logging.getLogger("openbase.gateway.probe")

# 连续失败剔除阈值与冷却期（对齐技术方案 §3.4）
FAILURE_THRESHOLD = 3
COOLDOWN_SECONDS = 60.0


def probe_instance(
    instance: ServiceInstance,
    probe_fn: Callable[[str, int, str], bool],
    health_path: str = "/health",
) -> bool:
    """对单个实例执行一次健康探测.

    连续 FAILURE_THRESHOLD 次失败 → healthy=false（进入冷却）；冷却期后
    成功 1 次即恢复 healthy=true（由调用方按时间控制恢复探测）。

    Args:
        instance: 目标实例（registry 内引用，探测结果直接写回）。
        probe_fn: 探测函数（host, port, health_path）→ bool。
        health_path: 健康检查路径。

    Returns:
        本次探测是否成功。
    """
    ok = probe_fn(instance.host, instance.port, health_path)
    if ok:
        instance.consecutive_failures = 0
        instance.last_heartbeat = time.time()
        return True

    instance.consecutive_failures += 1
    if instance.consecutive_failures >= FAILURE_THRESHOLD and instance.healthy:
        instance.healthy = False
        instance.last_heartbeat = time.time()  # 记录剔除时间（冷却起点）
        logger.warning(
            "instance marked unhealthy",
            extra={
                "system": instance.system,
                "instance_id": instance.instance_id,
                "failures": instance.consecutive_failures,
            },
        )
    return False


def build_http_probe(timeout: float = 2.0) -> Callable[[str, int, str], bool]:
    """构建 HTTP 健康探测函数（GET {host}:{port}{health_path}，2xx 视为健康）.

    Args:
        timeout: 探测超时秒数。

    Returns:
        探测函数。
    """
    import httpx

    def _probe(host: str, port: int, path: str) -> bool:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"http://{host}:{port}{path}")
                return 200 <= response.status_code < 300
        except httpx.HTTPError:
            return False

    return _probe


def probe_system(
    registry: DiscoveryRegistry,
    system: str,
    probe_fn: Callable[[str, int, str], bool],
    health_path: str = "/health",
    cooldown_seconds: float = COOLDOWN_SECONDS,
) -> None:
    """对某系统全部实例执行一轮探测；冷却期内不重复探测失败实例.

    Args:
        registry: 实例注册表。
        system: 目标系统。
        probe_fn: 探测函数。
        health_path: 健康检查路径。
        cooldown_seconds: 冷却期（失败实例冷却结束才恢复探测）。
    """
    now = time.time()
    for instance in registry.list_all(system):
        # 冷却期内跳过失败实例的重复探测
        if not instance.healthy and instance.last_heartbeat > 0 and (now - instance.last_heartbeat) < cooldown_seconds:
            continue
        if not instance.healthy:
            # 冷却期结束：恢复探测，成功即恢复
            ok = probe_instance(instance, probe_fn, health_path)
            if ok:
                registry.mark_healthy(system, instance.instance_id)
        else:
            probe_instance(instance, probe_fn, health_path)
