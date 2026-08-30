"""DiscoveryRegistry：服务实例内存注册表（线程安全读写锁 + TTL 心跳）.

system → list[ServiceInstance]，支持注册/上线/下线/标记不健康/加权轮询 pick。
网关重启后从 config 恢复静态实例（见 ConfigProbeProvider）。
"""

from __future__ import annotations

import threading

from openbase.modules.gateway.discovery import ServiceInstance


class DiscoveryRegistry:
    """内存注册表：加权轮询 + 故障剔除（对齐技术方案 §3.4/§3.5）.

    线程安全：全部写操作在读写锁保护下执行；pick 为读操作。
    """

    def __init__(self) -> None:
        self._instances: dict[str, dict[str, ServiceInstance]] = {}
        self._lock = threading.RLock()
        self._cursor: dict[str, int] = {}

    # ---- 写操作 ----

    def upsert(self, instance: ServiceInstance) -> None:
        """新增或覆盖实例."""
        with self._lock:
            self._instances.setdefault(instance.system, {})[instance.instance_id] = instance

    def remove(self, system: str, instance_id: str) -> None:
        """删除实例."""
        with self._lock:
            self._instances.get(system, {}).pop(instance_id, None)

    def mark_unhealthy(self, system: str, instance_id: str) -> None:
        """标记实例不健康（故障剔除，从候选池移除）."""
        with self._lock:
            inst = self._instances.get(system, {}).get(instance_id)
            if inst is not None:
                inst.healthy = False

    def mark_healthy(self, system: str, instance_id: str) -> None:
        """标记实例健康（冷却后探测成功恢复）."""
        with self._lock:
            inst = self._instances.get(system, {}).get(instance_id)
            if inst is not None:
                inst.healthy = True
                inst.consecutive_failures = 0

    # ---- 读操作 ----

    def get(self, system: str, instance_id: str) -> ServiceInstance | None:
        """获取指定实例."""
        with self._lock:
            return self._instances.get(system, {}).get(instance_id)

    def list_all(self, system: str) -> list[ServiceInstance]:
        """返回某系统全部实例（含不健康）."""
        with self._lock:
            return list(self._instances.get(system, {}).values())

    def list_healthy(self, system: str) -> list[ServiceInstance]:
        """返回某系统健康实例列表."""
        with self._lock:
            return [i for i in self._instances.get(system, {}).values() if i.healthy]

    def pick(self, system: str) -> ServiceInstance | None:
        """加权轮询选取一个健康实例；全部不健康返回 None.

        权重高实例被选中概率更高（按权重构造轮询序列后游标推进）。
        """
        healthy = self.list_healthy(system)
        if not healthy:
            return None
        if len(healthy) == 1:
            return healthy[0]

        # 加权轮询：按权重扩展候选序列
        weighted: list[ServiceInstance] = []
        for instance in healthy:
            weighted.extend([instance] * max(1, instance.weight))

        with self._lock:
            cursor = self._cursor.get(system, 0)
            picked = weighted[cursor % len(weighted)]
            self._cursor[system] = cursor + 1
        return picked

    def systems(self) -> list[str]:
        """返回全部已注册系统名."""
        with self._lock:
            return list(self._instances.keys())
