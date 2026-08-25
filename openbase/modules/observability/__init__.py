"""observability 模块：可观测性（OTel 初始化 + 业务指标 + 追踪上下文）.

来源：OpenMemory observability/business_metrics.py（业务指标分类与命名结构抽取）
+ OpenLLM core/otel.py（OTel 初始化模式），适配 openbase 统一日志约定。
"""

from __future__ import annotations

import logging
from collections import Counter

from fastapi import APIRouter

logger = logging.getLogger("openbase.observability")

router = APIRouter(tags=["observability"])

_tracer_provider = None
_langfuse_configured = False


class BusinessMetrics:
    """业务指标采集器.

    来源：OpenMemory observability/business_metrics.py（业务事件分类 + 计数语义抽取）。
    v1.0.0 最小实现：内存计数；生产对接 Prometheus Counter/Histogram。
    """

    _counters: Counter[str] = Counter()
    _latencies: dict[str, list[float]] = {}

    @classmethod
    def incr(cls, metric: str, value: int = 1) -> None:
        """业务事件计数（如 auth.login.success / mcp.tools.called）.

        Args:
            metric: 指标名（点分命名，业务域.动作.结果）。
            value: 增量（默认 1）。
        """
        cls._counters[metric] += value

    @classmethod
    def observe_latency(cls, metric: str, seconds: float) -> None:
        """记录延迟观测（如 auth.login.duration）.

        Args:
            metric: 指标名。
            seconds: 秒数。
        """
        cls._latencies.setdefault(metric, []).append(seconds)

    @classmethod
    def snapshot(cls) -> dict:
        """导出计数快照."""
        return {
            "counters": dict(cls._counters),
            "latency_samples": {k: len(v) for k, v in cls._latencies.items()},
        }


def init_otel(service_name: str = "openbase", otlp_endpoint: str = "", enabled: bool = True) -> None:
    """初始化 OpenTelemetry 追踪（OTLP 导出）.

    Args:
        service_name: 服务名。
        otlp_endpoint: OTLP HTTP 端点。
        enabled: 是否启用（关闭时仅设置无操作 provider）。
    """
    global _tracer_provider

    if not enabled:
        logger.info("otel disabled")
        return

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    else:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    logger.info("otel initialized", extra={"service": service_name})


def get_tracer(name: str = "openbase"):
    """获取命名 tracer."""
    from opentelemetry import trace

    return trace.get_tracer(name)


def configure_langfuse(
    public_key: str,
    secret_key: str,
    host: str = "http://localhost:3000",
) -> None:
    """配置 Langfuse（OTLP/API 对接）.

    Args:
        public_key: Langfuse 公钥。
        secret_key: Langfuse 密钥。
        host: Langfuse 服务地址。
    """
    global _langfuse_configured
    _langfuse_configured = bool(public_key and secret_key)
    if _langfuse_configured:
        logger.info("langfuse configured", extra={"host": host})


@router.get("/observability/status")
async def status() -> dict:
    """可观测性配置状态（调试用）."""
    return {
        "otel_enabled": _tracer_provider is not None,
        "langfuse_configured": _langfuse_configured,
        "business_metrics": BusinessMetrics.snapshot(),
    }
