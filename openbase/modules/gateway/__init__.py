"""gateway 模块：统一网关（服务发现 + 聚合编排，阶段一零依赖）.

v1.4.0 新增（VC-006，对齐《网关服务发现与聚合编排技术方案》ADR-网关-001/002）：
- 服务发现：DiscoveryProvider 适配器 + ConfigProbeProvider（config+scheduler 探测）
- 聚合编排：/api/v1/gateway/aggregate 代码式并发聚合
- 向后兼容：PROXY_SYSTEMS 静态表兜底；gateway.discovery.enabled=false 回退 v1.3.0
"""

from __future__ import annotations

import logging

logger = logging.getLogger("openbase.gateway")

# 网关权限点清单（RBAC 按需校验，此处登记供审计/权限矩阵引用）
GATEWAY_PERMISSIONS: tuple[str, ...] = (
    "gateway:register",
    "gateway:view",
    "gateway:aggregate",
)

__all__ = ["router", "GATEWAY_PERMISSIONS", "get_provider", "get_registry"]


_provider = None


def get_provider():
    """获取全局 DiscoveryProvider 单例（按配置 gateway.discovery.provider 创建）.

    Returns:
        DiscoveryProvider 实例。
    """
    global _provider
    if _provider is None:
        from openbase.modules.config import ConfigStore
        from openbase.modules.gateway.discovery import create_provider

        enabled = ConfigStore.get("gateway.discovery.enabled")
        if enabled is False:
            logger.info("gateway discovery disabled, static proxy table fallback")
        provider_kind = ConfigStore.get("gateway.discovery.provider") or "config"
        _provider = create_provider(str(provider_kind))
        logger.info("gateway provider initialized", extra={"provider": provider_kind})
    return _provider


def get_registry():
    """获取注册表（供 proxy 模块 DiscoveryRegistry.pick 使用）.

    Returns:
        DiscoveryRegistry 实例；discovery 禁用时返回 None。
    """
    from openbase.modules.config import ConfigStore

    enabled = ConfigStore.get("gateway.discovery.enabled")
    if enabled is False:
        return None
    provider = get_provider()
    if hasattr(provider, "get_registry"):
        return provider.get_registry()
    return None


def ensure_probe_job() -> None:
    """注册健康探测定时任务（幂等，随网关启动调用）.

    复用 scheduler 模块（APScheduler interval job，默认每 10s 一轮）。
    """
    from openbase.modules.config import ConfigStore
    from openbase.modules.scheduler import get_scheduler

    interval = int(ConfigStore.get("gateway.discovery.interval") or 10)
    scheduler = get_scheduler()
    if scheduler is None:
        logger.warning("scheduler unavailable, gateway probe job not registered")
        return
    if scheduler.get_job("gateway_probe") is not None:
        return
    try:
        scheduler.add_job(
            get_provider().probe_all,
            trigger="interval",
            seconds=interval,
            id="gateway_probe",
            replace_existing=False,
        )
        logger.info("gateway probe job registered", extra={"interval": interval})
    except Exception:  # noqa: BLE001
        logger.exception("gateway probe job registration failed")


# 注册 gateway 默认配置（SYSTEM 级，供 ConfigStore 热加载覆盖）
from openbase.modules.config import ConfigStore  # noqa: E402
from openbase.modules.gateway.router import router  # noqa: E402  (路由最后导出)

ConfigStore.set_default("gateway.discovery.enabled", True)
ConfigStore.set_default("gateway.discovery.provider", "config")
ConfigStore.set_default("gateway.discovery.interval", 10)
ConfigStore.set_default("gateway.discovery.health_path", "/health")
ConfigStore.set_default("gateway.discovery.ttl", 60)

__version__ = "1.0.0"
