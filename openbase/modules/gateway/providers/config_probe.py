"""ConfigProbeProvider：阶段一默认服务发现提供者（零新增依赖）.

实例来源三选一（优先级递减）：
1. 动态注册 API（POST /api/v1/services 触发 register_instance）
2. config 键 proxy.{system}.instances（ConfigStore 热加载）
3. 静态表 PROXY_SYSTEMS 兜底

健康探测：由 scheduler interval job 调用 probe_all()（复用 scheduler 模块）。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from openbase.modules.gateway.discovery import DiscoveryProvider, ServiceInstance
from openbase.modules.gateway.registry import DiscoveryRegistry

logger = logging.getLogger("openbase.gateway.config_probe")


class ConfigProbeProvider(DiscoveryProvider):
    """阶段一实现（对齐技术方案 §3.3/§3.4）."""

    def __init__(self) -> None:
        self._registry = DiscoveryRegistry()
        self._health_path = "/health"
        self._interval = 10
        self._cooldown = 60.0

    # ---- 注册来源：动态注册 API + config + 静态表 ----

    def register_instance(
        self, system: str, instance_id: str, host: str, port: int, weight: int = 1
    ) -> ServiceInstance:
        """动态注册实例（POST /api/v1/services 触发）."""
        instance = ServiceInstance(
            system=system,
            instance_id=instance_id or f"{host}:{port}",
            host=host,
            port=port,
            weight=weight,
            healthy=True,
            last_heartbeat=time.time(),
        )
        self._registry.upsert(instance)
        logger.info(
            "instance registered",
            extra={"system": system, "instance_id": instance.instance_id},
        )
        return instance

    def deregister_instance(self, system: str, instance_id: str) -> None:
        """实例下线."""
        self._registry.remove(system, instance_id)
        logger.info(
            "instance deregistered",
            extra={"system": system, "instance_id": instance_id},
        )

    def list_instances(self, system: str) -> list[ServiceInstance]:
        """返回某系统健康实例列表（注册实例优先；缺失时回退 config/静态表）."""
        instances = self._registry.list_all(system)
        if instances:
            return instances
        return self._load_from_config_and_static(system)

    def _load_from_config_and_static(self, system: str) -> list[ServiceInstance]:
        """config 键 proxy.{system}.instances 优先，其次静态表 PROXY_SYSTEMS 兜底."""
        candidates: list[dict[str, Any]] = []
        try:
            from openbase.modules.config import ConfigStore

            configured = ConfigStore.get(f"proxy.{system}.instances")
            if isinstance(configured, list) and configured:
                candidates = configured
        except Exception:  # noqa: BLE001
            logger.debug("config instances read failed", extra={"system": system})

        if not candidates:
            try:
                from openbase.modules.proxy import PROXY_SYSTEMS

                static = PROXY_SYSTEMS.get(system)
                if static:
                    parsed = static["base_url"].replace("http://", "").replace("https://", "").split(":")
                    host = parsed[0]
                    port = int(parsed[1]) if len(parsed) > 1 else 80
                    candidates = [{"host": host, "port": port, "weight": 1}]
            except Exception:  # noqa: BLE001
                logger.debug("static proxy table read failed", extra={"system": system})

        instances: list[ServiceInstance] = []
        for entry in candidates:
            host = str(entry.get("host", "127.0.0.1"))
            port = int(entry.get("port", 80))
            instance_id = str(entry.get("instance_id", f"{host}:{port}"))
            instances.append(
                ServiceInstance(
                    system=system,
                    instance_id=instance_id,
                    host=host,
                    port=port,
                    weight=int(entry.get("weight", 1)),
                    healthy=True,
                    last_heartbeat=time.time(),
                )
            )
        return instances

    # ---- 健康探测 ----

    def probe_all(self) -> None:
        """健康探测一轮（由 scheduler interval job 调用）.

        复用 scheduler 模块注册 job：gateway_probe（每 10s 一轮）。
        探测路径 GET {host}:{port}/health；连续 3 次失败剔除，冷却 60s 后成功恢复。
        """
        from openbase.modules.gateway.probe import build_http_probe, probe_system

        probe_fn = build_http_probe()
        systems = set(self._registry.systems())
        # 探测全部已知系统（含 config/静态表来源）
        for system in systems:
            probe_system(
                self._registry, system, probe_fn, health_path=self._health_path, cooldown_seconds=self._cooldown
            )
        for system in ("openllm", "openrag", "openmemory", "dps"):
            if system not in systems and self.list_instances(system):
                probe_system(
                    self._registry, system, probe_fn, health_path=self._health_path, cooldown_seconds=self._cooldown
                )

    def get_registry(self) -> DiscoveryRegistry:
        """暴露注册表（供路由层读取实例列表）. """
        return self._registry

    def mark_unhealthy(self, system: str, instance_id: str) -> None:
        """转发级熔断：请求 5xx/超时 → 连续失败累加，≥3 剔除（不等下一轮探测）."""
        instance = self._registry.get(system, instance_id)
        if instance is None or not instance.healthy:
            return
        instance.consecutive_failures += 1
        if instance.consecutive_failures >= 3:
            self._registry.mark_unhealthy(system, instance_id)
            logger.warning(
                "instance circuit-broken on request failure",
                extra={"system": system, "instance_id": instance_id},
            )
