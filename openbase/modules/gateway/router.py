"""gateway 模块路由（对齐 API 接口设计 v1.4.0 §2）.

/api/v1/services —— 服务发现（注册/列表/下线/健康/连通性）
/api/v1/gateway/aggregate —— 聚合编排执行
全部端点 JWT 鉴权 + gateway:* 权限点。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends

from openbase.modules.auth.rbac import require_permission
from openbase.modules.gateway.aggregate import execute_aggregate
from openbase.modules.gateway.discovery import ServiceInstance
from openbase.modules.gateway.schemas import (
    AggregateOut,
    AggregateRequest,
    ServiceInstanceOut,
    ServiceRegisterRequest,
)

logger = logging.getLogger("openbase.gateway")

router = APIRouter(prefix="/api/v1", tags=["gateway"])

__all__ = ["router"]


def _provider():
    """获取全局 Provider 单例（惰性初始化）."""
    from openbase.modules.gateway import get_provider

    return get_provider()


def _to_out(instance: ServiceInstance) -> ServiceInstanceOut:
    return ServiceInstanceOut(
        system=instance.system,
        instance_id=instance.instance_id,
        host=instance.host,
        port=instance.port,
        weight=instance.weight,
        healthy=instance.healthy,
        last_heartbeat=instance.last_heartbeat,
        consecutive_failures=instance.consecutive_failures,
        meta=instance.meta,
    )


# ---- 服务发现 API ----

@router.get(
    "/services",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("gateway:view"))],
)
async def list_all_services() -> dict[str, Any]:
    """全部服务实例列表（含健康状态）."""
    provider = _provider()
    systems: list[dict[str, Any]] = []
    for system in ("openllm", "openrag", "openmemory", "dps"):
        instances = provider.list_instances(system)
        if instances:
            systems.append({"system": system, "instances": [_to_out(i).model_dump() for i in instances]})
    return {"systems": systems}


@router.get(
    "/services/{system}",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("gateway:view"))],
)
async def list_system_services(system: str) -> dict[str, Any]:
    """指定系统实例列表."""
    provider = _provider()
    instances = provider.list_instances(system)
    return {"instances": [_to_out(i).model_dump() for i in instances]}


@router.post(
    "/services",
    response_model=ServiceInstanceOut,
    dependencies=[Depends(require_permission("gateway:register"))],
)
async def register_service(req: ServiceRegisterRequest) -> ServiceInstanceOut:
    """实例注册（四系统启动时调用）."""
    provider = _provider()
    instance = provider.register_instance(
        system=req.system,
        instance_id=req.instance_id or f"{req.host}:{req.port}",
        host=req.host,
        port=req.port,
        weight=req.weight,
    )
    instance.meta = req.meta
    return _to_out(instance)


@router.delete(
    "/services/{system}/{instance_id}",
    response_model=dict[str, str],
    dependencies=[Depends(require_permission("gateway:register"))],
)
async def deregister_service(system: str, instance_id: str) -> dict[str, str]:
    """实例下线."""
    provider = _provider()
    provider.deregister_instance(system, instance_id)
    return {"deleted": instance_id}


@router.get(
    "/gateway/health",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("gateway:view"))],
)
async def gateway_health() -> dict[str, Any]:
    """网关发现层健康状态."""
    provider = _provider()
    registry = provider.get_registry()
    systems: list[dict[str, Any]] = []
    for system in registry.systems():
        instances = registry.list_all(system)
        healthy = sum(1 for i in instances if i.healthy)
        systems.append(
            {
                "system": system,
                "healthy": healthy > 0,
                "instance_count": len(instances),
                "health_rate": round(healthy / len(instances), 2) if instances else 0.0,
            }
        )
    return {"systems": systems}


@router.get(
    "/gateway/ping",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("gateway:view"))],
)
async def gateway_ping() -> dict[str, Any]:
    """四系统连通性一键检测."""
    provider = _provider()
    results: list[dict[str, Any]] = []
    for system in ("openllm", "openrag", "openmemory", "dps"):
        instances = provider.list_instances(system)
        if not instances:
            results.append({"system": system, "reachable": False, "latency_ms": None})
            continue
        target = instances[0]
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://{target.host}:{target.port}/health")
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            results.append(
                {"system": system, "reachable": 200 <= response.status_code < 300, "latency_ms": latency_ms}
            )
        except httpx.HTTPError:
            results.append({"system": system, "reachable": False, "latency_ms": None})
    return {"results": results}


# ---- 聚合编排 API ----

@router.post(
    "/gateway/aggregate",
    response_model=AggregateOut,
    dependencies=[Depends(require_permission("gateway:aggregate"))],
)
async def aggregate(request: AggregateRequest) -> AggregateOut:
    """聚合编排执行（代码式并发聚合）."""
    result = await execute_aggregate(request.model_dump())
    return AggregateOut(**result)
