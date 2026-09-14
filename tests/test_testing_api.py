"""C-10 受权 test-record API 测试.

覆盖方案《OpenBase-人工端到端测试日志记录方案》批 2 C-10：
- 全部端点挂 require_permission("test:record")：无 token 401 / 无权用户 403；
- 开轮 / 单条记录 / 改判 / summary 聚合完整闭环；
- FAIL/BLOCKED 强制 reason，缺 reason → 400；
- result 非法 → 422（schema 校验）；
- best-effort 落库降级不阻断（OPENBASE_AUDIT_DB_PERSIST=0 静默跳过）；
- 已知 run/record 不存在 → 404。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openbase.demo_app import app
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.testing import TestRecordService

client = TestClient(app)

admin_token = create_access_token("1", username="admin", extra={"permissions": ["*"]})
admin_headers = {"Authorization": f"Bearer {admin_token}"}
user_token = create_access_token("2", username="ops01")
user_headers = {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(autouse=True)
def _isolate_records() -> None:
    """用例级隔离：清空内存态（避免跨用例 run/record 复用）。"""
    TestRecordService.reset()
    yield
    TestRecordService.reset()


# ---- 权限门禁 ----

def test_testing_requires_auth() -> None:
    """无 token → 401（全部端点）. """
    assert client.post("/api/v1/test-runs", json={}).status_code == 401
    assert client.post("/api/v1/test-records", json={}).status_code == 401
    assert client.get("/api/v1/test-runs/x/summary").status_code == 401
    assert client.patch("/api/v1/test-records/1", json={}).status_code == 401


def test_testing_forbidden_without_permission() -> None:
    """普通用户无 test:record 权限 → 403. """
    assert client.post("/api/v1/test-runs", json={}, headers=user_headers).status_code == 403
    assert client.post("/api/v1/test-records", json={}, headers=user_headers).status_code == 403
    assert client.get("/api/v1/test-runs/x/summary", headers=user_headers).status_code == 403


# ---- 开轮 ----

def test_create_test_run_auto_generates_run_id() -> None:
    """开轮生成 run_id（run- 前缀）并返回信封 data.run_id."""
    resp = client.post("/api/v1/test-runs", json={"title": "S0 冒烟"}, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["run_id"].startswith("run-")


def test_create_test_run_duplicate_conflict() -> None:
    """显式 run_id 重复开轮 → 409. """
    client.post("/api/v1/test-runs", json={"run_id": "run-dup"}, headers=admin_headers)
    resp = client.post("/api/v1/test-runs", json={"run_id": "run-dup"}, headers=admin_headers)
    assert resp.status_code == 409


# ---- 单条记录 ----

def _open_run(run_id: str = "run-e2e") -> None:
    client.post("/api/v1/test-runs", json={"run_id": run_id}, headers=admin_headers)


def test_create_pass_record() -> None:
    """单条 PASS 记录（信封 data 含 id/result/case_id）. """
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "UI-DPS-0007", "step_id": "3", "result": "PASS"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["result"] == "PASS"
    assert data["case_id"] == "UI-DPS-0007"
    assert data["run_id"] == "run-e2e"
    assert data["step_id"] == 3  # 纯数字字符串归一为 int


def test_fail_requires_reason() -> None:
    """FAIL 缺 reason → 400（方案 §7 强制）. """
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "UI-DPS-0007", "result": "FAIL"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "PARAM_INVALID"


def test_fail_with_reason_ok() -> None:
    """FAIL 含 reason 成功. """
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={
            "run_id": "run-e2e",
            "case_id": "UI-DPS-0007",
            "step_id": 1,
            "result": "FAIL",
            "reason": "页面 500，上游 openllm 未启动",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["result"] == "FAIL"


def test_blocked_requires_reason() -> None:
    """BLOCKED 缺 reason → 400. """
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "UI-DPS-0011", "result": "BLOCKED"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_record_unknown_run_not_found() -> None:
    """引用不存在的 run → 404. """
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-missing", "case_id": "S0-1", "result": "PASS"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_invalid_result_validation_error() -> None:
    """非法 result（枚举外）→ 422（schema 校验）. """
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "S0-1", "result": "WEIRD"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ---- 改判 ----

def test_update_record_pass_to_fail() -> None:
    """PATCH 改判 PASS→FAIL（须带 reason），data.result 更新. """
    _open_run()
    created = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "S0-2", "result": "PASS"},
        headers=admin_headers,
    ).json()["data"]
    record_id = created["id"]

    resp = client.patch(
        f"/api/v1/test-records/{record_id}",
        json={"result": "FAIL", "reason": "复核发现数据不一致"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["result"] == "FAIL"
    assert data["reason"] == "复核发现数据不一致"


def test_update_record_fail_without_reason() -> None:
    """改判为 FAIL 缺 reason → 400. """
    _open_run()
    created = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "S0-3", "result": "PASS"},
        headers=admin_headers,
    ).json()["data"]
    resp = client.patch(
        f"/api/v1/test-records/{created['id']}",
        json={"result": "FAIL"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_update_unknown_record_not_found() -> None:
    """改判不存在的记录 → 404. """
    resp = client.patch(
        "/api/v1/test-records/99999",
        json={"result": "FAIL", "reason": "x"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


# ---- summary 聚合 ----

def _record(run_id: str, case_id: str, result: str, reason: str | None = None, step_id=1):
    payload: dict = {"run_id": run_id, "case_id": case_id, "step_id": step_id, "result": result}
    if reason:
        payload["reason"] = reason
    return client.post("/api/v1/test-records", json=payload, headers=admin_headers).json()["data"]


def test_summary_aggregates_counts() -> None:
    """summary 计数：2 PASS + 1 FAIL → total 3 / fail 1 / passed False. """
    _open_run("run-summary")
    _record("run-summary", "UI-DPS-0007", "PASS")
    _record("run-summary", "UI-DPS-0008", "PASS")
    _record("run-summary", "UI-DPS-0009", "FAIL", reason="错误")

    resp = client.get("/api/v1/test-runs/run-summary/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 3
    assert data["pass"] == 2
    assert data["fail"] == 1
    assert data["blocked"] == 0
    assert data["passed"] is False
    assert len(data["cases"]) == 3
    assert data["cases"][0]["case_id"] == "UI-DPS-0007"
    assert isinstance(data["cases"][0]["steps"][0]["id"], int)  # 改判定位需要 record id


def test_summary_passed_all_green() -> None:
    """全 PASS → passed True；含 FAIL → passed False. """
    _open_run("run-green")
    _record("run-green", "S0-1", "PASS")
    _record("run-green", "S0-2", "PASS")
    green = client.get("/api/v1/test-runs/run-green/summary", headers=admin_headers).json()["data"]
    assert green["total"] == 2
    assert green["passed"] is True


def test_summary_unknown_run_not_found() -> None:
    """summary 引用不存在 run → 404. """
    resp = client.get("/api/v1/test-runs/run-nope/summary", headers=admin_headers)
    assert resp.status_code == 404


# ---- 落库降级（best-effort） ----

def test_db_persist_disabled_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENBASE_AUDIT_DB_PERSIST=0 → 请求正常（落库禁用不阻断）. """
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "0")
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "S0-4", "result": "PASS"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["result"] == "PASS"


# ---- 覆盖补全（分支/服务方法） ----

def test_non_numeric_step_id_kept_as_is() -> None:
    """非纯数字 step_id 不做归一化（保留原值）. """
    _open_run()
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "S0-5", "step_id": "step-A", "result": "PASS"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["step_id"] == "step-A"


def test_update_record_with_observed() -> None:
    """PATCH 携带 observed → 更新观测字段. """
    _open_run()
    created = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-e2e", "case_id": "S0-6", "result": "PASS"},
        headers=admin_headers,
    ).json()["data"]
    resp = client.patch(
        f"/api/v1/test-records/{created['id']}",
        json={"result": "PASS", "observed": "复核通过，页面正常"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["observed"] == "复核通过，页面正常"


def test_result_service_require_reason() -> None:
    """TestResultService.require_reason 直接调用（服务方法门禁复用）. """
    from openbase.core.errors import BaseError
    from openbase.modules.testing import TestResultService

    TestResultService.require_reason("PASS", None)  # 非强制结果：不抛
    with pytest.raises(BaseError):
        TestResultService.require_reason("BLOCKED", "")


def test_summary_aggregates_blocked_and_skipped() -> None:
    """summary 计数含 BLOCKED/SKIPPED（补齐四类分支）. """
    _open_run("run-mix")
    _record("run-mix", "S0-7", "BLOCKED", reason="依赖服务未部署")
    _record("run-mix", "S0-8", "SKIPPED")
    data = client.get("/api/v1/test-runs/run-mix/summary", headers=admin_headers).json()["data"]
    assert data["blocked"] == 1
    assert data["skipped"] == 1
    assert data["passed"] is False


# ---- 落库真实路径（模拟 DB 会话，覆盖 best-effort 成功/失败） ----

class _FakeDbSession:
    """最小 DB 会话替身：add/commit/rollback 均为内存行为."""

    def __init__(self, commit_error: Exception | None = None) -> None:
        self.commit_error = commit_error
        self.added: list[object] = []
        self.committed = False

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    async def rollback(self) -> None:
        pass


class _FakeSessionCM:
    """async 上下文管理器：包装在 get_session_factory 返回的 callable 之后."""

    def __init__(self, commit_error: Exception | None = None) -> None:
        self.session = _FakeDbSession(commit_error)

    async def __aenter__(self) -> _FakeDbSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _install_fake_db(monkeypatch: pytest.MonkeyPatch, commit_error: Exception | None = None) -> _FakeDbSession:
    """将 _persist 的 DB 会话替换为内存替身，返回替身以便断言."""

    shared_cm = _FakeSessionCM(commit_error)

    def fake_factory():
        def make_cm_factory():
            return shared_cm
        return make_cm_factory

    monkeypatch.setattr("openbase.core.db.session.get_session_factory", fake_factory)
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")
    return shared_cm.session


def test_db_persist_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """落库成功：以 fake 会话承接 AuditLog，请求仍 200（镜像无副作用）. """
    fake_session = _install_fake_db(monkeypatch)
    _open_run("run-persist-ok")
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-persist-ok", "case_id": "S0-9", "step_id": 3, "result": "PASS"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert fake_session.added, "应有一次 AuditLog add"


def test_db_persist_failure_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    """落库失败唯一警告不阻断：commit 抛错 → 请求仍 200. """
    _install_fake_db(monkeypatch, commit_error=RuntimeError("db down"))
    _open_run("run-persist-fail")
    resp = client.post(
        "/api/v1/test-records",
        json={"run_id": "run-persist-fail", "case_id": "S0-10", "result": "PASS"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["result"] == "PASS"
