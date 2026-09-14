"""C-15 网关响应级观测测试（resp_status/bytes/content_type/error_code/digest + 开关摘要）.

覆盖方案《OpenBase-人工端到端测试日志记录方案》§11.2 红线与 §5 批 4 C-15：

- **默认关（零采集）**：只产出结构性字段（``resp_status``/``resp_bytes``/
  ``resp_content_type``/``resp_error_code``/``resp_digest``），**不读响应体**、
  不产出 ``resp_summary``；
- **开关开启**：JSON 响应体被读取并生成 ``resp_summary``，且**必经 C-18 脱敏**
  （手机号/凭据不得以原文出现）；
- 非 JSON / SSE 流式响应体**永不读取**（不破坏流式与二进制透传）；
- ``resp_error_code`` 取自统一异常处理器（AUTH_401 / PERM_* 等）；
- 允许清单命中的字段路径保留原值（错误归因用）。
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from openbase.core.errors import ErrorCode
from openbase.demo_app import app
from openbase.modules.audit import (
    AuditService,
    build_response_observation,
    should_capture_body,
)
from openbase.modules.auth.jwt import create_access_token

client = TestClient(app)

admin_headers = {
    "Authorization": f"Bearer {create_access_token('1', username='admin', extra={'permissions': ['*']})}"
}

# 断言口径常量（避免用例内魔法值漂移）
HTTP_UNAUTHORIZED = 401
AUTH_401_CODE = "AUTH_401"
SENSITIVE_PHONE = "13812345678"
MASKED_PHONE = "138****5678"


@pytest.fixture(autouse=True)
def _reset_runtime_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """用例级隔离：重置 Settings 单例（使 env 开关生效）并清空审计内存缓冲.

    注：``openbase.settings`` 模块名在 ``openbase`` 包命名空间被 Settings 实例遮蔽
    （``openbase/__init__.py`` 的 ``settings = get_settings()``），故经 ``sys.modules`` 取模块。
    """
    import sys

    settings_module = sys.modules["openbase.settings"]
    original = settings_module._settings
    settings_module._settings = None
    AuditService._records.clear()
    yield
    settings_module._settings = original
    AuditService._records.clear()


def _last_record() -> dict[str, Any]:
    """取最近一条审计记录（经 AuditService 查询投影）."""
    rows = AuditService.records(limit=1)
    assert rows, "应有审计记录"
    return rows[0]


# ---- 默认关：结构性字段有、摘要无 ----


def test_response_summary_absent_when_switch_off() -> None:
    """默认关：无 resp_summary，结构性字段齐全（零采集）."""
    resp = client.get("/api/v1/test-runs/run-x/summary")
    assert resp.status_code == HTTP_UNAUTHORIZED

    row = _last_record()
    assert row["resp_status"] == HTTP_UNAUTHORIZED
    assert row["resp_error_code"] == AUTH_401_CODE
    assert row["resp_digest"].startswith("sha256:")
    assert isinstance(row["resp_bytes"], int) and row["resp_bytes"] > 0
    assert "resp_summary" not in row


def test_l1_log_carries_structured_response_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L1 请求级日志同样携带结构性响应字段（供 C-17 分析器消费）."""
    with caplog.at_level(logging.INFO, logger="openbase.audit"):
        client.get("/api/v1/test-runs/run-x/summary")
    request_logs = [rec for rec in caplog.records if rec.message == "api.request"]
    assert request_logs, "应有 L1 请求级日志"
    latest = request_logs[-1]
    assert getattr(latest, "resp_status", None) == HTTP_UNAUTHORIZED
    assert getattr(latest, "resp_digest", None)
    assert not hasattr(latest, "resp_summary")


# ---- 开关开启：读取响应体 + 强制脱敏 ----


def test_summary_captured_and_masked_when_switch_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """开：读取 JSON 响应体生成摘要，且摘要中的手机号已被掩码（开时脱敏生效）."""
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    # 触发 422 校验错误：错误信封的 detail[].input 会回带提交原文（承载隐私文本）
    resp = client.post(
        "/api/v1/test-records",
        json={
            "run_id": "run-c15",
            "case_id": "S7-T2-1",
            "step_id": {"contact": SENSITIVE_PHONE},
            "result": "FAIL",
            "reason": "步骤号类型非法",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422

    row = _last_record()
    assert "resp_summary" in row, "开关开启且层级合规时应产出摘要"
    assert SENSITIVE_PHONE not in str(row), "摘要中不得出现隐私原文"
    assert MASKED_PHONE in str(row["resp_summary"]), "摘要应已按 C-18 掩码手机号"


def test_deep_response_keeps_keys_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """开：层级 > 5 的响应体只留 digest + 键名清单（不存原文，方案 §11.4）."""
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    client.post(
        "/api/v1/test-runs",
        json={"run_id": "run-c15-deep", "title": "深层响应"},
        headers=admin_headers,
    )
    client.post(
        "/api/v1/test-records",
        json={"run_id": "run-c15-deep", "case_id": "S7-T2-2", "step_id": 1, "result": "PASS"},
        headers=admin_headers,
    )
    resp = client.get("/api/v1/test-runs/run-c15-deep/summary", headers=admin_headers)
    assert resp.status_code == 200

    row = _last_record()
    assert row["resp_digest"].startswith("sha256:")
    assert "resp_keys" in row
    assert "resp_summary" not in row


def test_credential_headers_are_never_captured(monkeypatch: pytest.MonkeyPatch) -> None:
    """开：凭据类头（Authorization）不进入审计记录，也不进入响应摘要."""
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    raw_token = admin_headers["Authorization"].removeprefix("Bearer ")
    resp = client.get("/api/v1/test-runs/run-x/summary", headers=admin_headers)
    assert resp.status_code == 404  # 未知 run：错误信封由异常处理器产出

    row = _last_record()
    assert raw_token not in str(row)
    assert row["resp_error_code"] == ErrorCode.BIZ_NOT_FOUND.value


# ---- 非 JSON / 流式：永不读体 ----


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("application/json", True),
        ("application/json; charset=utf-8", True),
        ("text/event-stream", False),
        ("text/html; charset=utf-8", False),
        ("application/octet-stream", False),
        ("", False),
    ],
)
def test_should_capture_body_matrix(content_type: str, expected: bool) -> None:
    """仅 JSON 非流式响应体允许读取（保护 SSE 与二进制透传）."""
    assert should_capture_body(content_type) is expected


def test_structural_digest_without_body_capture() -> None:
    """未采集响应体 → digest 为结构性摘要（状态码/类型/长度/错误码的组合）."""
    observed = build_response_observation(
        status_code=403,
        content_type="application/json",
        content_length=64,
        error_code="PERM_FORBIDDEN",
    )
    assert observed["resp_digest"].startswith("sha256:")
    assert observed["resp_bytes"] == 64
    assert observed["resp_error_code"] == "PERM_FORBIDDEN"
    assert "resp_summary" not in observed


def test_observation_with_payload_reports_real_bytes_and_summary() -> None:
    """采集到响应体 → 以真实字节数为准并产出摘要（digest 基于原文）."""
    payload = b'{"code":"AUTH_401","message":"unauthorized"}'
    observed = build_response_observation(
        status_code=401,
        content_type="application/json",
        content_length=None,
        error_code="AUTH_401",
        payload=payload,
    )
    assert observed["resp_bytes"] == len(payload)
    assert observed["resp_summary"]["code"] == "AUTH_401"


def test_allowlist_threaded_into_observation() -> None:
    """允许清单透传至摘要：命中路径保留原值（错误归因需要）."""
    payload = f'{{"message":"联系人 {SENSITIVE_PHONE} 不可达"}}'.encode()
    observed = build_response_observation(
        status_code=502,
        content_type="application/json",
        content_length=len(payload),
        error_code="SYS_UPSTREAM_ERROR",
        payload=payload,
        allowlist=("message",),
    )
    assert SENSITIVE_PHONE in observed["resp_summary"]["message"]
