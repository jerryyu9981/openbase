"""C-16 上游响应专段测试（proxy ``_forward`` 的 upstream_* 观测）.

覆盖方案《OpenBase-人工端到端测试日志记录方案》§5 批 4 C-16 与 §11.5 归因矩阵：

- 上游响应专段字段：``upstream_system``/``upstream_status``/``upstream_error_code``/
  ``upstream_duration_ms``/``upstream_digest``（结构性，恒记）；
- ``upstream_body_summary`` **仅在** ``OPENBASE_CAPTURE_UPSTREAM=1`` 时产出，且必经
  C-18 脱敏（层级过深/超限 → 只留键名清单）；
- **异常路径复用同一结构**（上游不可达：无 status、有 error，不新增日志点）；
- 专段经 ``request.state.upstream_observation`` 汇聚，与 C-15 网关观测落在**同一条**
  L1 记录上（同请求多次上游调用取最近一次并累计 ``upstream_calls``）。
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase.demo_app import app
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.proxy.upstream_observe import (
    build_upstream_segment,
    extract_upstream_error_code,
    publish_upstream_observation,
)

client = TestClient(app)

admin_headers = {
    "Authorization": f"Bearer {create_access_token('1', username='admin', extra={'permissions': ['*']})}"
}

SENSITIVE_PHONE = "13812345678"
MASKED_PHONE = "138****5678"


# ---- 专段构造（结构性字段） ----


def test_segment_records_status_duration_and_digest() -> None:
    """成功路径：系统/状态/耗时/digest 齐备；默认关 → 无摘要."""
    segment = build_upstream_segment(
        system="dps",
        reached=True,
        duration_ms=42,
        status_code=200,
        content_type="application/json",
        payload=b'{"code":0,"data":{"x":1}}',
    )
    assert segment["upstream_system"] == "dps"
    assert segment["upstream_status"] == 200
    assert segment["upstream_duration_ms"] == 42
    assert segment["upstream_digest"].startswith("sha256:")
    assert "upstream_body_summary" not in segment


def test_segment_extracts_business_error_code() -> None:
    """业务错误码提取：顶层 ``code`` 与嵌套 ``error.code`` 均识别. """
    top_level = build_upstream_segment(
        system="dps",
        reached=True,
        duration_ms=5,
        status_code=404,
        content_type="application/json",
        payload=b'{"code":"BIZ_404","message":"not found"}',
    )
    nested = build_upstream_segment(
        system="openllm",
        reached=True,
        duration_ms=5,
        status_code=500,
        content_type="application/json",
        payload=b'{"error":{"code":"UPSTREAM_500","message":"boom"}}',
    )
    assert top_level["upstream_error_code"] == "BIZ_404"
    assert nested["upstream_error_code"] == "UPSTREAM_500"


def test_error_code_extraction_returns_none_for_unsupported_payloads() -> None:
    """非 JSON / 非对象体 / 非标量错误码 → 不提取（不臆造错误码）."""
    assert extract_upstream_error_code(b"not-json") is None
    assert extract_upstream_error_code(b"[1,2]") is None
    assert extract_upstream_error_code(b'{"code": {"nested": 1}}') is None
    assert extract_upstream_error_code(b'{"code": ""}') is None
    assert extract_upstream_error_code(None) is None


def test_segment_unreachable_keeps_same_structure() -> None:
    """异常路径复用同一结构：无 status/digest，有 error（不新增日志点）."""
    segment = build_upstream_segment(
        system="openrag",
        reached=False,
        duration_ms=7,
        error="connect refused",
    )
    assert segment["upstream_system"] == "openrag"
    assert segment["upstream_duration_ms"] == 7
    assert segment["upstream_error"] == "connect refused"
    assert "upstream_status" not in segment
    assert "upstream_digest" not in segment


# ---- 开关：摘要 / 键名清单 ----


def test_segment_capture_masks_summary() -> None:
    """开：产出摘要且经 C-18 脱敏（隐私不落原文）."""
    payload = json.dumps({"message": f"联系人 {SENSITIVE_PHONE} 不可达"}).encode()
    segment = build_upstream_segment(
        system="dps",
        reached=True,
        duration_ms=3,
        status_code=502,
        content_type="application/json",
        payload=payload,
        capture=True,
    )
    assert MASKED_PHONE in str(segment["upstream_body_summary"])
    assert SENSITIVE_PHONE not in str(segment)


def test_segment_capture_deep_payload_keeps_keys_only() -> None:
    """开：层级 > 5 → 只留键名清单（不存原文）."""
    payload = b'{"a":{"b":{"c":{"d":{"e":{"f":"deep"}}}}}}'
    segment = build_upstream_segment(
        system="dps",
        reached=True,
        duration_ms=3,
        status_code=200,
        content_type="application/json",
        payload=payload,
        capture=True,
    )
    assert "upstream_body_summary" not in segment
    assert segment["upstream_keys"] == ["a"]


def test_segment_capture_allowlist_keeps_attribution_field() -> None:
    """开 + 允许清单：命中路径保留原值（错误归因需要）."""
    payload = b'{"error":{"code":"UPSTREAM_500","message":"boom"}}'
    segment = build_upstream_segment(
        system="dps",
        reached=True,
        duration_ms=3,
        status_code=500,
        content_type="application/json",
        payload=payload,
        capture=True,
        allowlist=("error.code",),
    )
    assert segment["upstream_body_summary"]["error"]["code"] == "UPSTREAM_500"


# ---- request.state 汇聚 ----


def test_publish_accumulates_calls_and_keeps_latest() -> None:
    """同请求多次上游调用：取最近一次 + 累计 upstream_calls. """
    request = SimpleNamespace(state=SimpleNamespace())
    publish_upstream_observation(
        request, build_upstream_segment(system="a", reached=True, duration_ms=1, status_code=200)
    )
    merged = publish_upstream_observation(
        request,
        build_upstream_segment(system="b", reached=True, duration_ms=2, status_code=500),
    )
    assert merged["upstream_calls"] == 2
    assert merged["upstream_system"] == "b"
    assert request.state.upstream_observation["upstream_status"] == 500


# ---- 端到端：通用代理通道 ----


class _FakeUpstreamResponse:
    """httpx 响应替身（仅暴露 _forward 使用到的接口）."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.content = json.dumps(payload).encode()
        self.text = self.content.decode()

    def json(self) -> dict[str, Any]:
        return json.loads(self.content)


def _patch_upstream(monkeypatch: pytest.MonkeyPatch, response: _FakeUpstreamResponse) -> None:
    """替换 httpx.AsyncClient.request（不触网，返回值可控）."""

    async def fake_request(self, method, url, **kwargs):  # noqa: ANN001, ARG001
        return response

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)


@pytest.fixture(autouse=True)
def _reset_runtime_state() -> None:
    """用例级隔离：重置 Settings 单例并清空审计内存缓冲."""
    import sys

    from openbase.modules.audit import AuditService

    settings_module = sys.modules["openbase.settings"]
    original = settings_module._settings
    settings_module._settings = None
    AuditService._records.clear()
    yield
    settings_module._settings = original
    AuditService._records.clear()


def test_generic_proxy_records_upstream_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    """通用代理通道：上游专段与网关观测落在同一条审计记录上. """
    _patch_upstream(monkeypatch, _FakeUpstreamResponse(404, {"code": "BIZ_404", "message": "no"}))
    resp = client.get("/api/v1/proxy/dps/api/v2/portrait/list", headers=admin_headers)
    assert resp.status_code == 404

    from openbase.modules.audit import AuditService

    row = AuditService.records(limit=1)[0]
    assert row["upstream_system"] == "dps"
    assert row["upstream_status"] == 404
    assert row["upstream_error_code"] == "BIZ_404"
    assert isinstance(row["upstream_duration_ms"], int)
    assert row["upstream_calls"] == 1
    # C-15 网关侧与 C-16 上游侧同列（归因无需跨行 join）
    assert row["resp_status"] == 404
