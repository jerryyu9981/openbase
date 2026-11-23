"""dps-proxy 波次 C（2.20.0）进度、调度与审计透传用例.

验证 ``/progress/*``、``/business-items``、``/schedules/*``、``/audit/logs``
转发到上游 ``/api/v2/*``，且静态段（``/schedules/preview``）不被动态段吞并。
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient
from test_dps_proxy import UPSTREAM_BASE, FakeAsyncClient

from openbase import init_app
from openbase.modules.auth import UserService
from openbase.settings import Settings


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
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


def _call(client: TestClient) -> dict:
    return client.fake.request_calls[0]  # type: ignore[attr-defined]


def test_progress_trend_forwards_query(client: TestClient) -> None:
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/progress/P1?period_type=week&limit=8",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = _call(client)
    assert call["method"] == "GET"
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/progress/P1")
    assert call["params"] == {"period_type": "week", "limit": "8"}


def test_progress_calculate_forwards_body(client: TestClient) -> None:
    token = _token(client)
    body = {"person_id": "P1", "period_type": "day", "period_key": "2026-11-20"}
    resp = client.post(
        "/api/v1/dps-proxy/progress/calculate",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = _call(client)
    assert call["method"] == "POST"
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/progress/calculate"
    assert call["json"] == body


def test_business_items_list_and_upsert(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        "/api/v1/dps-proxy/business-items?person_id=P1", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert _call(client)["url"] == f"{UPSTREAM_BASE}/api/v2/business-items"

    client.fake.request_calls.clear()  # type: ignore[attr-defined]
    body = {"person_id": "P1", "item_type": "study", "status": "done"}
    resp = client.post(
        "/api/v1/dps-proxy/business-items", json=body, headers=headers
    )
    assert resp.status_code == 200, resp.text
    call = _call(client)
    assert call["method"] == "POST"
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/business-items"
    assert call["json"] == body


def test_schedule_preview_static_segment(client: TestClient) -> None:
    """``/schedules/preview`` 必须走静态段，不被 ``/schedules/{id}`` 吞并."""
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/schedules/preview?expr=0+3+*+*+*",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = _call(client)
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/schedules/preview"
    assert call["params"]["expr"] == "0 3 * * *"


def test_schedule_crud_and_run(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/dps-proxy/schedules", headers=headers).status_code == 200
    assert _call(client)["url"] == f"{UPSTREAM_BASE}/api/v2/schedules"

    client.fake.request_calls.clear()  # type: ignore[attr-defined]
    body = {"datasource_id": "ds1", "schedule_type": "cron", "cron_expr": "0 3 * * *"}
    assert client.post(
        "/api/v1/dps-proxy/schedules", json=body, headers=headers
    ).status_code == 200
    assert _call(client)["json"] == body

    client.fake.request_calls.clear()  # type: ignore[attr-defined]
    assert client.put(
        f"/api/v1/dps-proxy/schedules/s1", json={"enabled": True}, headers=headers
    ).status_code == 200
    assert _call(client)["method"] == "PUT"
    assert _call(client)["url"] == f"{UPSTREAM_BASE}/api/v2/schedules/s1"

    client.fake.request_calls.clear()  # type: ignore[attr-defined]
    assert client.post(
        "/api/v1/dps-proxy/schedules/s1/run", json={}, headers=headers
    ).status_code == 200
    assert _call(client)["url"] == f"{UPSTREAM_BASE}/api/v2/schedules/s1/run"


def test_audit_logs_forwards_action_filter(client: TestClient) -> None:
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/audit/logs?action=EXPORT&result=SUCCESS",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = _call(client)
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/audit/logs"
    assert call["params"] == {"action": "EXPORT", "result": "SUCCESS"}
