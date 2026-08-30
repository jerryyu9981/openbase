"""测试 v1.4.0 统一网关增强（TD-14-25/26/N3/N5，RT-425/426）.

验证：① 网关错误码与权限点定义；② ServiceInstance 数据模型；
③ DiscoveryProvider 抽象与工厂；④ ConfigProbeProvider 注册/列表/下线；
⑤ DiscoveryRegistry 加权轮询与故障剔除；⑥ 健康探测剔除与冷却恢复；
⑦ 聚合编排（并发/超时/部分失败）；⑧ proxy 兜底开关。
"""

import asyncio
from typing import Any

import pytest

from openbase.core.errors import ErrorCode
from openbase.core.errors.codes import ERROR_HTTP_MAP

# ---- 1. 错误码与权限点 ----

def test_gateway_error_codes_defined() -> None:
    """网关错误码定义齐全."""
    assert ErrorCode.SYS_TIMEOUT == "SYS_TIMEOUT"
    assert ErrorCode.PARAM_AGGREGATE_STEP_INVALID == "PARAM_AGGREGATE_STEP_INVALID"
    assert ErrorCode.BIZ_AGGREGATE_PARTIAL_FAILURE == "BIZ_AGGREGATE_PARTIAL_FAILURE"
    assert ErrorCode.PERM_GATEWAY_REGISTER == "PERM_GATEWAY_REGISTER"
    assert ErrorCode.PERM_GATEWAY_AGGREGATE == "PERM_GATEWAY_AGGREGATE"
    assert ErrorCode.PERM_GATEWAY_VIEW == "PERM_GATEWAY_VIEW"


def test_gateway_error_http_map() -> None:
    """网关错误码 HTTP 映射正确."""
    assert ERROR_HTTP_MAP[ErrorCode.SYS_TIMEOUT] == 503
    assert ERROR_HTTP_MAP[ErrorCode.PARAM_AGGREGATE_STEP_INVALID] == 400
    assert ERROR_HTTP_MAP[ErrorCode.PERM_GATEWAY_REGISTER] == 403
    assert ERROR_HTTP_MAP[ErrorCode.PERM_GATEWAY_AGGREGATE] == 403
    assert ERROR_HTTP_MAP[ErrorCode.PERM_GATEWAY_VIEW] == 403


def test_gateway_permission_points_registered() -> None:
    """权限点 gateway:register/view/aggregate 已注册."""
    from openbase.modules.gateway import GATEWAY_PERMISSIONS

    for point in ("gateway:register", "gateway:view", "gateway:aggregate"):
        assert point in GATEWAY_PERMISSIONS, f"missing permission point: {point}"


# ---- 2. 数据模型 ----

def test_service_instance_model() -> None:
    """ServiceInstance 数据模型字段与默认值."""
    from openbase.modules.gateway.discovery import ServiceInstance

    inst = ServiceInstance(system="openllm", instance_id="h1:8001", host="h1", port=8001)
    assert inst.system == "openllm"
    assert inst.weight == 1
    assert inst.healthy is True
    assert inst.consecutive_failures == 0


# ---- 3. Provider 抽象与工厂 ----

def test_discovery_provider_factory() -> None:
    """create_provider('config') 返回 ConfigProbeProvider；未知 kind 默认 config."""
    from openbase.modules.gateway.discovery import create_provider
    from openbase.modules.gateway.providers.config_probe import ConfigProbeProvider

    provider = create_provider("config")
    assert isinstance(provider, ConfigProbeProvider)
    assert isinstance(create_provider("unknown"), ConfigProbeProvider)


# ---- 4. ConfigProbeProvider 注册/列表/下线 ----

def _make_provider():
    from openbase.modules.gateway.providers.config_probe import ConfigProbeProvider

    return ConfigProbeProvider()


def test_provider_register_list_deregister() -> None:
    """注册/列表/下线实例."""
    provider = _make_provider()
    provider.register_instance(system="openllm", instance_id="h1:8001", host="h1", port=8001)
    provider.register_instance(system="openllm", instance_id="h2:8001", host="h2", port=8001)

    instances = provider.list_instances("openllm")
    assert len(instances) == 2
    assert {i.instance_id for i in instances} == {"h1:8001", "h2:8001"}

    provider.deregister_instance("openllm", "h1:8001")
    assert len(provider.list_instances("openllm")) == 1


def test_provider_static_default_fallback() -> None:
    """未注册实例时回退静态表 PROXY_SYSTEMS."""
    provider = _make_provider()
    instances = provider.list_instances("openrag")
    assert len(instances) >= 1
    assert instances[0].host == "127.0.0.1"
    assert instances[0].port == 8010


# ---- 5. DiscoveryRegistry 加权轮询与故障剔除 ----

def test_registry_pick_weighted_round_robin() -> None:
    """加权轮询：权重高实例分配更多请求；剔除故障实例后自动避开."""
    from openbase.modules.gateway.discovery import ServiceInstance
    from openbase.modules.gateway.registry import DiscoveryRegistry

    registry = DiscoveryRegistry()
    registry.upsert(ServiceInstance(system="s", instance_id="a", host="a", port=1, weight=2, healthy=True))
    registry.upsert(ServiceInstance(system="s", instance_id="b", host="b", port=1, weight=1, healthy=True))

    picked = [registry.pick("s").instance_id for _ in range(6)]
    assert picked.count("a") == 4  # weight 2/3 * 6
    assert picked.count("b") == 2

    # 剔除 b → 全部落到 a
    registry.mark_unhealthy("s", "b")
    picked2 = [registry.pick("s").instance_id for _ in range(3)]
    assert set(picked2) == {"a"}


def test_registry_pick_none_when_all_unhealthy() -> None:
    """全部实例不健康时 pick 返回 None."""
    from openbase.modules.gateway.discovery import ServiceInstance
    from openbase.modules.gateway.registry import DiscoveryRegistry

    registry = DiscoveryRegistry()
    registry.upsert(ServiceInstance(system="s", instance_id="a", host="a", port=1, healthy=False))
    assert registry.pick("s") is None


# ---- 6. 健康探测：连续失败剔除 + 冷却恢复 ----

def test_probe_removes_after_3_consecutive_failures() -> None:
    """连续 3 次失败 → 实例剔除（healthy=false）；冷却期后成功 1 次恢复."""
    import time as _time

    from openbase.modules.gateway.discovery import ServiceInstance
    from openbase.modules.gateway.probe import probe_instance, probe_system
    from openbase.modules.gateway.registry import DiscoveryRegistry

    registry = DiscoveryRegistry()
    registry.upsert(ServiceInstance(system="s", instance_id="a", host="a", port=1, healthy=True))

    def fake_probe(host: str, port: int, path: str) -> bool:
        return False  # 模拟探测失败

    inst = registry.get("s", "a")
    assert inst is not None
    # 连续 3 次失败
    for _ in range(3):
        probe_instance(inst, fake_probe, health_path="/health")
    assert registry.get("s", "a").healthy is False

    # 冷却期已过（剔除时间置为 120s 前）→ 成功 1 次恢复
    inst2 = registry.get("s", "a")
    assert inst2 is not None
    inst2.last_heartbeat = _time.time() - 120

    def fake_probe_ok(host: str, port: int, path: str) -> bool:
        return True

    probe_system(registry, "s", fake_probe_ok, health_path="/health", cooldown_seconds=60)
    assert registry.get("s", "a").healthy is True


# ---- 7. 聚合编排 ----

class _FakeAggregateClient:
    """模拟 httpx.AsyncClient.request 返回指定响应."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses
        self._calls: list[str] = []

    async def __aenter__(self) -> "_FakeAggregateClient":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def request(self, method: str, url: str, **kwargs) -> "_FakeAggregateClient":
        self._calls.append(url)
        return self

    @property
    def status_code(self) -> int:
        return 200

    def json(self) -> dict:
        return {"total": 42}


def test_aggregate_merges_two_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """聚合 2 个子请求并发执行并合并结果."""
    import httpx

    from openbase.modules.gateway.aggregate import execute_aggregate

    fake = _FakeAggregateClient([])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: fake)

    request: dict[str, Any] = {
        "timeout_ms": 5000,
        "on_partial_failure": "return_errors",
        "steps": [
            {"id": "models", "system": "openllm", "path": "/models", "method": "GET"},
            {"id": "kbs", "system": "openrag", "path": "/kb/list", "method": "GET"},
        ],
        "mapping": {"model_total": "${models.data.total}", "kb_total": "${kbs.data.total}"},
    }
    result = asyncio.run(execute_aggregate(request))
    assert result["result"]["model_total"] == 42
    assert result["result"]["kb_total"] == 42
    assert len(fake._calls) == 2  # 两个子请求都执行


def test_aggregate_step_timeout_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """单步超时 → 部分失败策略 return_errors 返回 errors 明细."""
    import httpx

    from openbase.modules.gateway.aggregate import execute_aggregate

    class _SlowClient(_FakeAggregateClient):
        async def request(self, method: str, url: str, **kwargs) -> Any:
            self._calls.append(url)
            await asyncio.sleep(0.05)  # 模拟慢请求（超过 models 步骤 1ms 超时）
            return self

    fake = _SlowClient([])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: fake)

    request: dict[str, Any] = {
        "timeout_ms": 5000,
        "on_partial_failure": "return_errors",
        "steps": [
            {"id": "models", "system": "openllm", "path": "/models", "method": "GET", "timeout_ms": 1},
            {"id": "kbs", "system": "openrag", "path": "/kb/list", "method": "GET", "timeout_ms": 100},
        ],
        "mapping": {"model_total": "${models.data.total}", "kb_total": "${kbs.data.total}"},
    }
    result = asyncio.run(execute_aggregate(request))
    # 慢步骤（models，0.05s > 0.01s 下限超时）→ errors 明细；快步骤（kbs）成功
    assert "errors" in result
    assert any("models" in str(e) for e in result["errors"])
    assert result["result"]["kb_total"] == 42


# ---- 8. proxy 兜底开关 ----

def test_proxy_resolve_uses_static_table_when_discovery_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """gateway.discovery.enabled=false 时 _resolve_base_url 回退静态表行为."""
    import openbase.modules.proxy as proxy_module
    from openbase.modules.config import ConfigStore

    monkeypatch.setattr(ConfigStore, "get", lambda key, level=None: False if key == "gateway.discovery.enabled" else None)
    url = proxy_module._resolve_base_url("openllm")
    assert url == "http://127.0.0.1:8001"


def test_gateway_router_registered() -> None:
    """gateway 模块 router 已挂载（存在路由）."""
    from openbase.modules.gateway import router

    routes = {getattr(r, "path", "") for r in router.routes}
    assert "/api/v1/services" in routes
    assert "/api/v1/gateway/health" in routes
    assert "/api/v1/gateway/aggregate" in routes


# ---- 9. T2 接口层边界参数（三要素：状态码 + 结构 + 边界） ----

def test_service_register_schema_rejects_invalid_port() -> None:
    """端口边界校验（<1 / >65535 → Pydantic 校验失败）."""
    import pytest as _pytest
    from pydantic import ValidationError

    from openbase.modules.gateway.schemas import ServiceRegisterRequest

    with _pytest.raises(ValidationError):
        ServiceRegisterRequest(system="openllm", host="h", port=0)
    with _pytest.raises(ValidationError):
        ServiceRegisterRequest(system="openllm", host="h", port=65536)


def test_aggregate_rejects_empty_steps() -> None:
    """空 steps / 超量 steps → 参数校验错误码."""
    import asyncio

    from openbase.modules.gateway.aggregate import execute_aggregate

    with _pytest_raises("aggregate steps required"):
        asyncio.run(execute_aggregate({"steps": []}))
    too_many = {"steps": [{"id": f"s{i}", "system": "openllm", "path": "/"} for i in range(9)]}
    with _pytest_raises("too many steps"):
        asyncio.run(execute_aggregate(too_many))


def test_aggregate_strict_failure_raises() -> None:
    """strict 策略下部分失败 → BIZ_AGGREGATE_PARTIAL_FAILURE."""
    import asyncio

    import httpx as _httpx

    from openbase.modules.gateway.aggregate import execute_aggregate

    class _SlowResp:
        status_code = 500

        def json(self):
            return {}

    class _SlowClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, **kw):
            await asyncio.sleep(0.02)
            return _SlowResp()

    orig = _httpx.AsyncClient
    _httpx.AsyncClient = lambda **kw: _SlowClient()
    try:
        with _pytest_raises("strict failure"):
            asyncio.run(
                execute_aggregate(
                    {
                        "on_partial_failure": "strict",
                        "steps": [{"id": "a", "system": "openllm", "path": "/", "timeout_ms": 1000}],
                    }
                )
            )
    finally:
        _httpx.AsyncClient = orig


def _pytest_raises(code: str) -> Any:
    """便捷断言：捕获 BaseError 并校验错误码."""
    import pytest as _pytest

    from openbase.core.errors import BaseError

    return _pytest.raises(BaseError, match=code)
