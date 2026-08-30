"""gateway 模块 Pydantic 请求/响应模型（对齐 API 接口设计 v1.4.0 §2）."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ServiceRegisterRequest(BaseModel):
    """实例注册请求（POST /api/v1/services）."""

    system: str = Field(..., description="系统标识：openllm/openrag/openmemory/dps")
    instance_id: str | None = Field(None, description="实例唯一 ID（默认 host:port）")
    host: str = Field(..., description="实例主机")
    port: int = Field(..., ge=1, le=65535, description="实例端口")
    weight: int = Field(1, ge=1, description="负载权重（加权轮询）")
    meta: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ServiceInstanceOut(BaseModel):
    """服务实例响应模型（对齐 API 设计 §2.1 ServiceInstance）."""

    system: str
    instance_id: str
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    last_heartbeat: float = 0.0
    consecutive_failures: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class AggregateStep(BaseModel):
    """聚合子请求步骤."""

    id: str = Field(..., description="步骤 ID（供 mapping 引用）")
    system: str = Field(..., description="目标系统")
    path: str = Field(..., description="目标路径（经 /api/v1/proxy 转发）")
    method: str = Field("GET", description="HTTP 方法")
    timeout_ms: int = Field(2000, ge=100, le=10000, description="单步超时")


class AggregateRequest(BaseModel):
    """聚合编排请求（阶段一代码式，对齐 API 设计 §2.2）."""

    steps: list[AggregateStep] = Field(..., min_length=1, max_length=8, description="子请求步骤")
    timeout_ms: int = Field(5000, ge=500, le=30000, description="整体超时")
    on_partial_failure: str = Field("return_errors", description="return_errors/strict/best_effort")
    mapping: dict[str, str] = Field(default_factory=dict, description="结果合并规则")


class AggregateOut(BaseModel):
    """聚合响应."""

    result: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
