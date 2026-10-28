"""v1.9.2 R2：补齐列表端点与服务 Key id 化吊销.

覆盖：
- `GET /api/v1/configs`：列表（含默认值与运行时写入）、prefix 过滤；
- `GET /api/v1/test-records` / `GET /api/v1/test-runs`：列表与轮次/用例/结论过滤；
- `ApiKeyOut.id` 回显 + `DELETE /api/v1/auth/api-keys/by-id/{key_id}` 吊销；
- 未知 id → 404 BIZ_NOT_FOUND。
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from openbase.demo_app import app
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.config import ConfigStore
from openbase.modules.testing import TestRecordService

client = TestClient(app)

admin_token = create_access_token("1", username="admin", extra={"permissions": ["*"]})
admin_headers = {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(autouse=True)
def _isolate_records() -> None:
    TestRecordService.reset()
    yield
    TestRecordService.reset()


# ---- 配置列表 ----


def test_config_list_returns_items_and_total() -> None:
    key = f"r2.verify.{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/v1/configs", json={"key": key, "value": {"v": 1}}, headers=admin_headers)
    assert resp.status_code == 200, resp.text

    listed = client.get("/api/v1/configs", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] == len(body["items"])
    assert any(item["key"] == key for item in body["items"])


def test_config_list_prefix_filter() -> None:
    alpha = f"r2alpha.{uuid.uuid4().hex[:6]}"
    beta = f"r2beta.{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/configs", json={"key": alpha, "value": 1}, headers=admin_headers)
    client.post("/api/v1/configs", json={"key": beta, "value": 2}, headers=admin_headers)

    body = client.get("/api/v1/configs", params={"prefix": "r2alpha."}, headers=admin_headers).json()
    keys = [item["key"] for item in body["items"]]
    assert alpha in keys
    assert beta not in keys
    assert keys == sorted(keys)


def test_config_list_includes_registered_default() -> None:
    """代码默认值（未写入）也应出现在列表中。"""
    ConfigStore.set_default("r2.default.probe", "on")
    body = client.get("/api/v1/configs", params={"prefix": "r2.default."}, headers=admin_headers).json()
    assert [item["key"] for item in body["items"]] == ["r2.default.probe"]
    assert body["items"][0]["value"] == "on"
    assert body["items"][0]["level"] == "system"


# ---- 测试记录 / 轮次列表 ----


def _seed_run(run_id: str) -> None:
    resp = client.post("/api/v1/test-runs", json={"run_id": run_id, "title": "R2 验证"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text


def _seed_record(run_id: str, case_id: str, result: str) -> None:
    payload = {"run_id": run_id, "case_id": case_id, "step_id": 1, "result": result}
    if result in ("FAIL", "BLOCKED"):
        payload["reason"] = "R2 用例"
    resp = client.post("/api/v1/test-records", json=payload, headers=admin_headers)
    assert resp.status_code == 200, resp.text


def test_test_records_list_and_filters() -> None:
    run_id = f"run-r2-{uuid.uuid4().hex[:6]}"
    _seed_run(run_id)
    _seed_record(run_id, "R2-1", "PASS")
    _seed_record(run_id, "R2-2", "FAIL")

    body = client.get("/api/v1/test-records", params={"run_id": run_id}, headers=admin_headers).json()["data"]
    assert body["total"] == 2
    assert len(body["items"]) == 2

    failed = client.get(
        "/api/v1/test-records", params={"run_id": run_id, "result": "FAIL"}, headers=admin_headers
    ).json()["data"]
    assert failed["total"] == 1
    assert failed["items"][0]["case_id"] == "R2-2"

    case = client.get(
        "/api/v1/test-records", params={"run_id": run_id, "case_id": "R2-1"}, headers=admin_headers
    ).json()["data"]
    assert case["total"] == 1
    assert case["items"][0]["result"] == "PASS"


def test_test_records_list_pagination() -> None:
    run_id = f"run-r2p-{uuid.uuid4().hex[:6]}"
    _seed_run(run_id)
    for index in range(3):
        _seed_record(run_id, f"R2P-{index}", "PASS")

    page = client.get(
        "/api/v1/test-records", params={"run_id": run_id, "skip": 1, "limit": 1}, headers=admin_headers
    ).json()["data"]
    assert page["total"] == 3
    assert len(page["items"]) == 1


def test_test_runs_list_reports_record_count() -> None:
    run_id = f"run-r2r-{uuid.uuid4().hex[:6]}"
    _seed_run(run_id)
    _seed_record(run_id, "R2R-1", "PASS")

    body = client.get("/api/v1/test-runs", headers=admin_headers).json()["data"]
    row = next(item for item in body["items"] if item["id"] == run_id)
    assert row["record_count"] == 1
    assert row["title"] == "R2 验证"


def test_test_runs_list_requires_permission() -> None:
    user_token = create_access_token("2", username="ops01")
    resp = client.get("/api/v1/test-runs", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


# ---- 服务 Key id 化吊销 ----


def test_api_key_list_exposes_id_and_revoke_by_id(api_key_client) -> None:
    name = f"r2-key-{uuid.uuid4().hex[:6]}"
    created = api_key_client.post("/api/v1/auth/api-keys", json={"name": name})
    assert created.status_code == 200, created.text
    created_body = created.json()
    assert created_body["key"].startswith("ob_k_")
    assert created_body["id"], "创建响应应回显稳定 id"

    listed = api_key_client.get("/api/v1/auth/api-keys").json()
    record = next(item for item in listed if item["name"] == name)
    assert record["id"] == created_body["id"]
    assert record["revoked"] is False
    assert "key" not in record or record["key"] is None

    revoked = api_key_client.delete(f"/api/v1/auth/api-keys/by-id/{record['id']}")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked"] == record["id"]

    after = api_key_client.get("/api/v1/auth/api-keys").json()
    assert next(item for item in after if item["id"] == record["id"])["revoked"] is True


def test_api_key_revoke_by_unknown_id_returns_404(api_key_client) -> None:
    resp = api_key_client.delete("/api/v1/auth/api-keys/by-id/no-such-id")
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "BIZ_404"
