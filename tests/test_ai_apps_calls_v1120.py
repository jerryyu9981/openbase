"""v1.12.0（OB-03）AI 应用调用记录全局聚合用例.

覆盖：跨应用聚合（含 app_name）、app_id / status 筛选、分页、
路由顺序（``/calls`` 不被 ``/{app_id}`` 吞掉）、分页参数校验。
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import install_exception_handlers
from openbase.modules.ai_apps import AiAppService, router

CALLS_URL = "/api/v1/ai-apps/calls"


def _client() -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "tester", "tenant_id": None}
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_service():
    AiAppService._reset()
    yield
    AiAppService._reset()


def _seed() -> tuple[str, str]:
    service = AiAppService()
    app_a = service.create(name="客服助手", model_config={"provider": "openai", "model": "gpt-4o"})
    app_b = service.create(name="知识问答", model_config={"provider": "ollama", "model": "qwen2.5-7b"})
    service.record_call(app_a["id"], status="success", latency_ms=120)
    service.record_call(app_a["id"], status="error", latency_ms=500, error_code="SYS_500")
    service.record_call(app_b["id"], status="success", latency_ms=80)
    return app_a["id"], app_b["id"]


def test_global_calls_aggregate_across_apps():
    app_a, app_b = _seed()
    resp = _client().get(CALLS_URL)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 3
    assert data["page"] == 1
    names = {item["app_id"]: item["app_name"] for item in data["items"]}
    assert names[app_a] == "客服助手"
    assert names[app_b] == "知识问答"


def test_global_calls_filter_by_app_id():
    app_a, _ = _seed()
    resp = _client().get(CALLS_URL, params={"app_id": app_a})
    data = resp.json()["data"]
    assert data["total"] == 2
    assert {item["app_id"] for item in data["items"]} == {app_a}


def test_global_calls_filter_by_status():
    _seed()
    resp = _client().get(CALLS_URL, params={"status": "error"})
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["error_code"] == "SYS_500"


def test_global_calls_pagination():
    _seed()
    client = _client()
    first = client.get(CALLS_URL, params={"page": 1, "page_size": 2}).json()["data"]
    second = client.get(CALLS_URL, params={"page": 2, "page_size": 2}).json()["data"]
    assert first["total"] == second["total"] == 3
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1


def test_calls_route_not_swallowed_by_app_id():
    """/calls 必须命中全局聚合，而不是被 /{app_id} 当作 app-xxx 查询."""
    _seed()
    resp = _client().get(CALLS_URL)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["total"] == 3


def test_calls_rejects_invalid_page_size():
    """参数越界由统一异常处理器转为 400 PARAM_400（项目错误码契约）."""
    _seed()
    resp = _client().get(CALLS_URL, params={"page_size": 0})
    assert resp.status_code == 400
    assert resp.json()["code"] == "PARAM_400"
    detail = resp.json()["detail"]
    assert any(item.get("field") == "page_size" for item in detail)
