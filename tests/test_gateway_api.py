"""测试网关 API 路由层（T2 接口层：TestClient 集成 + 权限门禁）.

覆盖 router.py 与 __init__.py 中测试空白的行，提升网关模块覆盖率 ≥80%。
"""


import pytest
from fastapi.testclient import TestClient

from openbase.demo_app import app
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.gateway.aggregate import execute_aggregate

client = TestClient(app)
admin_token = create_access_token("1", username="admin", extra={"permissions": ["*"]})
admin_headers = {"Authorization": f"Bearer {admin_token}"}


# ---- 权限门禁 ----

def test_gateway_api_requires_auth() -> None:
    """无 token → 401."""
    assert client.get("/api/v1/services").status_code == 401
    assert client.get("/api/v1/gateway/health").status_code == 401
    assert client.post("/api/v1/gateway/aggregate", json={}).status_code == 401


def test_gateway_api_forbidden_without_permission() -> None:
    """普通用户无 gateway 权限 → 403."""
    user_token = create_access_token("2", username="ops01")
    headers = {"Authorization": f"Bearer {user_token}"}
    assert client.get("/api/v1/services", headers=headers).status_code == 403
    assert client.get("/api/v1/gateway/health", headers=headers).status_code == 403


# ---- 服务发现 API ----

def test_list_all_services_structure() -> None:
    """GET /services 响应结构（systems/instances 字段 + 类型）."""
    resp = client.get("/api/v1/services", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "systems" in body
    for group in body["systems"]:
        assert "system" in group
        assert "instances" in group


def test_list_system_services() -> None:
    """GET /services/{system} 指定系统列表."""
    resp = client.get("/api/v1/services/openllm", headers=admin_headers)
    assert resp.status_code == 200
    assert "instances" in resp.json()


def test_register_and_deregister_via_api() -> None:
    """POST/DELETE /services 注册与下线闭环."""
    reg = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"system": "openllm", "host": "10.1.1.1", "port": 8001, "weight": 3},
    )
    assert reg.status_code == 200
    instance = reg.json()
    assert instance["instance_id"] == "10.1.1.1:8001"
    assert instance["weight"] == 3

    delete = client.delete("/api/v1/services/openllm/10.1.1.1:8001", headers=admin_headers)
    assert delete.status_code == 200
    assert delete.json()["deleted"] == "10.1.1.1:8001"


def test_register_schema_validation() -> None:
    """非法端口 → 422 校验错误."""
    resp = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"system": "openllm", "host": "h", "port": 99999},
    )
    assert resp.status_code == 422


# ---- 网关健康 API ----

def test_gateway_health_api() -> None:
    """GET /gateway/health 响应结构."""
    resp = client.get("/api/v1/gateway/health", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "systems" in body
    for item in body["systems"]:
        assert "healthy" in item
        assert "instance_count" in item


def test_gateway_ping_api() -> None:
    """GET /gateway/ping 响应结构（四系统，可达性布尔）."""
    resp = client.get("/api/v1/gateway/ping", headers=admin_headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 4
    for item in results:
        assert "reachable" in item
        assert item["reachable"] in (True, False)


# ---- 聚合 API ----

def test_aggregate_api_validation() -> None:
    """空 steps → 422（schema 层 min_length 校验拦截，契约预期）."""
    resp = client.post(
        "/api/v1/gateway/aggregate",
        headers=admin_headers,
        json={"steps": [], "mapping": {}},
    )
    assert resp.status_code == 422


def test_aggregate_api_return_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """四系统未启动 → 部分失败 errors 明细（H 类环境提示，成功路径待对接批次）."""
    resp = client.post(
        "/api/v1/gateway/aggregate",
        headers=admin_headers,
        json={
            "steps": [{"id": "a", "system": "openllm", "path": "/models", "timeout_ms": 500}],
            "mapping": {"total": "${a.data.total}"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) >= 1


# ---- 模块入口（__init__.py） ----

def test_get_provider_singleton() -> None:
    """get_provider 返回单例 Provider."""
    from openbase.modules.gateway import get_provider

    provider_a = get_provider()
    provider_b = get_provider()
    assert provider_a is provider_b


def test_get_registry_with_discovery_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """discovery 禁用时 get_registry 返回 None."""
    from openbase.modules.config import ConfigStore
    from openbase.modules.gateway import get_registry

    monkeypatch.setattr(ConfigStore, "get", lambda key, level=None: False if key == "gateway.discovery.enabled" else None)
    assert get_registry() is None


def test_ensure_probe_job_scheduler_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """scheduler 不可用时 probe job 注册降级不抛异常."""
    import openbase.modules.scheduler as scheduler_module
    from openbase.modules.gateway import ensure_probe_job

    monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: None)
    ensure_probe_job()  # 不应抛异常


def test_execute_aggregate_import_smoke() -> None:
    """聚合执行器导入与调用（模块级 import 冒烟）."""
    assert callable(execute_aggregate)
