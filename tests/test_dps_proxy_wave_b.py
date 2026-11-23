"""dps-proxy 波次 B（2.19.0）组织与引入任务透传用例.

验证新增的 ``/orgs/*`` 与 ``/ingest/*`` 端点把请求转发到上游 ``/api/v2/*``，
身份头由代理构造，请求体与路径参数保持保真。
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
    """启用 auth + dps_proxy 的应用，替换上游客户端并关闭探活."""
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


def test_org_tree_forwards_to_v2(client: TestClient) -> None:
    """GET /orgs/tree → 上游 /api/v2/orgs/tree."""
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/orgs/tree", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == "GET"
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/orgs/tree"


def test_org_members_put_forwards_body(client: TestClient) -> None:
    """PUT /orgs/{code}/members → 上游同名路径 + 请求体."""
    token = _token(client)
    body = {"members": [{"person_id": "P1", "is_primary": True}]}
    resp = client.put(
        "/api/v1/dps-proxy/orgs/dept1/members",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == "PUT"
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/orgs/dept1/members"
    assert call["json"] == body


def test_ingest_execute_forwards_body(client: TestClient) -> None:
    """POST /ingest/execute → 上游 /api/v2/ingest/execute."""
    token = _token(client)
    body = {"file_path": "/tmp/a.csv", "file_format": "csv"}
    resp = client.post(
        "/api/v1/dps-proxy/ingest/execute",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == "POST"
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/ingest/execute"
    assert call["json"] == body


def test_ingest_task_errors_path(client: TestClient) -> None:
    """GET /ingest/tasks/{id}/errors → 上游同名路径."""
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/ingest/tasks/import-abc/errors",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/ingest/tasks/import-abc/errors"


def test_portrait_list_forwards_org_code(client: TestClient) -> None:
    """画像列表 org_code → 上游 /api/v2/portrait/list 同名参数."""
    token = _token(client)
    resp = client.get(
        "/api/v1/dps-proxy/portraits?org_code=dept1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")
    assert call["params"]["org_code"] == "dept1"
