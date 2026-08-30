"""gateway 模块：服务发现提供者抽象（适配器模式，对齐技术方案 §3.6）.

DiscoveryProvider 抽象：config/scheduler（阶段一）与 Nacos（阶段二）均可实现。
create_provider 工厂按配置创建 Provider（gateway.discovery.provider = config | nacos）。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("openbase.gateway.discovery")


@dataclass
class ServiceInstance:
    """服务实例（对齐技术方案 §3.2 数据模型）.

    Attributes:
        system: 所属系统（openllm/openrag/openmemory/dps）。
        instance_id: 实例唯一 ID（如 host:port）。
        host: 实例主机。
        port: 实例端口。
        weight: 负载权重（加权轮询）。
        healthy: 健康状态。
        last_heartbeat: 最近心跳时间戳。
        consecutive_failures: 连续失败计数（熔断剔除）。
        meta: 扩展元数据。
    """

    system: str
    instance_id: str
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    last_heartbeat: float = 0.0
    consecutive_failures: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


class DiscoveryProvider(ABC):
    """服务发现提供者抽象：config/scheduler 与 Nacos 等均可实现.

    上层（加权轮询/故障剔除/聚合）仅依赖本接口，Provider 实现可插拔切换。
    """

    @abstractmethod
    def list_instances(self, system: str) -> list[ServiceInstance]:
        """返回某系统当前健康实例列表（加权轮询与故障剔除在其上层）."""

    @abstractmethod
    def register_instance(
        self, system: str, instance_id: str, host: str, port: int, weight: int = 1
    ) -> ServiceInstance:
        """注册实例（供四系统启动时调用 /api/v1/services 触发）."""

    @abstractmethod
    def deregister_instance(self, system: str, instance_id: str) -> None:
        """实例下线."""

    @abstractmethod
    def probe_all(self) -> None:
        """健康探测一轮（由 scheduler interval job 触发；Nacos 模式可为空实现）."""


def create_provider(kind: str | None = None) -> DiscoveryProvider:
    """工厂：按配置创建 Provider（gateway.discovery.provider = config | nacos）.

    Args:
        kind: Provider 类型；None/未知时回退阶段一默认 ConfigProbeProvider。

    Returns:
        DiscoveryProvider 实例。
    """
    if kind == "nacos":
        try:
            from openbase.modules.gateway.providers.nacos import NacosProvider

            return NacosProvider()
        except ImportError:  # 阶段二依赖未安装时回退
            logger.warning("nacos provider unavailable, fallback to config provider")
    from openbase.modules.gateway.providers.config_probe import ConfigProbeProvider

    return ConfigProbeProvider()
