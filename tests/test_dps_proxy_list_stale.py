"""dps-proxy 画像列表 stale 透传用例（v1.8.0 / T-DM-02）.

验证 OpenBase 代理不改变既有语义的前提下，把 ``template_code`` / ``stale``
查询参数原样透传上游，并保持 4xx 错误体保真。
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient
from test_dps_proxy import UPSTREAM_BASE, FakeAsyncClient, FakeResponse

from openbase import init_app
from openbase.modules.auth import UserService
from openbase.settings import Settings


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """启用 auth + dps_proxy 的应用，替换上游 httpx 客户端并关闭探活."""
    settings = Settings()
    for module in ("auth", "proxy", "dps_proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    settings.dps_upstream_base = UPSTREAM_BASE
    settings.dps_default_org_id = "default-org"
    settings.dps_default_tenant_id = "default-tenant"
    settings.dps_health_check_enabled = False
    settings_module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(settings_module, "_settings", settings)
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    fake = FakeAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: fake)
    test_client = TestClient(app)
    test_client.fake = fake  # type: ignore[attr-defined]
    return test_client


def _token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_list_forwards_template_code_and_stale(client: TestClient) -> None:
    """template_code + stale → 上游收到同名参数."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": [], "total": 0}})
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits?template_code=dm-template-v1&stale=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")
    assert call["params"] == {
        "page": 1,
        "page_size": 20,
        "template_code": "dm-template-v1",
        "stale": "true",
    }


def test_list_omits_stale_when_absent(client: TestClient) -> None:
    """未传 stale → 不向上游追加该参数（保持既有行为）."""
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/portraits?template_code=dm-template-v1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["params"] == {
        "page": 1,
        "page_size": 20,
        "template_code": "dm-template-v1",
    }


def test_upstream_400_passthrough(client: TestClient) -> None:
    """上游 400（stale 缺 template_code）→ HTTP 400 + 错误文案保真."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(400, {"detail": "stale 过滤必须同时指定 template_code"})
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits?stale=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["code"] == 400
    assert "template_code" in body["message"]
