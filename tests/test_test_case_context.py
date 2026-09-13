"""C-3 / C-5 / C-8 用例上下文贯穿测试（TDD：先 RED，后实现）.

设计依据：《OpenBase-人工端到端测试日志记录方案》§3.2（数据流）、§3.3（关键取舍：
用例上下文用**非身份头**承载）、§4.2（场景扩展字段 case_id/step_id/run_id/channel）、
§5 批 1（C-3 头部解析 + L1 JSON 日志；C-5 出站透传；C-8 查询过滤）。

关键约束（被测不变量）：
- ``X-Test-Case-Id`` / ``X-Test-Step-Id`` / ``X-Test-Run-Id`` 均为**非身份头**，
  不得进入 ``IDENTITY_HEADERS`` / ``INBOUND_IDENTITY_HEADERS``（否则客户端携带即 403）。
"""

from __future__ import annotations

import asyncio
import logging
import types

import pytest
from starlette.requests import Request as StarletteRequest

from openbase.modules.audit import AuditMiddleware, AuditService
from openbase.modules.protocol_headers.constants import (
    HEADER_REQUEST_ID,
    HEADER_TEST_CASE_ID,
    HEADER_TEST_RUN_ID,
    HEADER_TEST_STEP_ID,
    IDENTITY_HEADERS,
    INBOUND_IDENTITY_HEADERS,
)
from openbase.modules.protocol_headers.inject import build_outbound_headers


@pytest.fixture(autouse=True)
def _clear_audit_records():
    """隔离审计内存缓冲，避免跨用例污染。"""
    AuditService._records.clear()
    yield
    AuditService._records.clear()


def _scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/dps-proxy/portraits",
        "raw_path": b"/api/v1/dps-proxy/portraits",
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }


def _header_pairs(**values: str) -> list[tuple[bytes, bytes]]:
    return [(name.lower().encode(), value.encode()) for name, value in values.items()]


def _request(headers: list[tuple[bytes, bytes]] | None = None) -> StarletteRequest:
    return StarletteRequest(_scope(headers))


# ---------------------------------------------------------------------------
# 常量约束：测试用例头必须是非身份头
# ---------------------------------------------------------------------------


def test_test_case_headers_are_not_identity_headers() -> None:
    """X-Test-* 为非身份头：不得进入裁剪/身份头集（否则客户端携带即 403）。"""
    for header in (HEADER_TEST_CASE_ID, HEADER_TEST_STEP_ID, HEADER_TEST_RUN_ID):
        assert header not in IDENTITY_HEADERS, f"{header} 被误加入身份头集"
        assert header not in INBOUND_IDENTITY_HEADERS, f"{header} 被误加入入站裁剪集"


# ---------------------------------------------------------------------------
# C-3：中间件解析用例上下文 → request.state
# ---------------------------------------------------------------------------


def test_extract_test_context_reads_headers() -> None:
    """dispatch 前置解析：读三个测试头并归一化（step_id 数字转 int）。"""
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = _request(
        _header_pairs(**{"X-Test-Case-Id": "UI-DPS-0007", "X-Test-Step-Id": "3"})
    )

    context = middleware._extract_test_context(request)

    assert context["case_id"] == "UI-DPS-0007"
    assert context["step_id"] == 3


def test_extract_test_context_absent_returns_none_values() -> None:
    """未带测试头：上下文为空（不影响既有请求语义）。"""
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]

    context = middleware._extract_test_context(_request())

    assert context["case_id"] is None
    assert context["step_id"] is None
    assert context["run_id"] is None


def test_extract_test_context_run_id_falls_back_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_id 取值：头优先；无头时回退环境变量 OPENBASE_TEST_RUN_ID（人工轮次）。"""
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    monkeypatch.setenv("OPENBASE_TEST_RUN_ID", "run-20260914-0100")
    assert middleware._extract_test_context(_request())["run_id"] == "run-20260914-0100"

    request = _request(_header_pairs(**{"X-Test-Run-Id": "run-from-header"}))
    assert middleware._extract_test_context(request)["run_id"] == "run-from-header"


def test_dispatch_puts_test_context_into_request_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dispatch 把用例上下文写入 request.state（供 L1 日志/出站透传复用）。"""
    monkeypatch.setenv("OPENBASE_TEST_RUN_ID", "run-dispatch-1")
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = _request(
        _header_pairs(**{"X-Test-Case-Id": "S7-T2-1", "X-Test-Step-Id": "7"})
    )

    async def _call_next(_request: StarletteRequest) -> types.SimpleNamespace:
        return types.SimpleNamespace(status_code=200, headers={})

    response = asyncio.run(middleware.dispatch(request, _call_next))

    assert response.status_code == 200
    assert request.state.test_case_id == "S7-T2-1"
    assert request.state.test_step_id == 7
    assert request.state.test_run_id == "run-dispatch-1"


# ---------------------------------------------------------------------------
# C-3：审计记录 extra 增 case_id/step_id/run_id/channel + L1 JSON 日志
# ---------------------------------------------------------------------------


def test_record_extra_carries_case_context_and_channel() -> None:
    """_record 的 extra 增 case_id/step_id/run_id/channel（channel=B 网关编排）。"""
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = _request()
    request.state.request_id = "req-case-1"
    request.state.test_case_id = "UI-DPS-0007"
    request.state.test_step_id = 3
    request.state.test_run_id = "run-1"

    middleware._record(request, 200, 42, "req-case-1")

    record = AuditService._records[-1]
    assert record.extra["case_id"] == "UI-DPS-0007"
    assert record.extra["step_id"] == 3
    assert record.extra["run_id"] == "run-1"
    assert record.extra["channel"] == "B"


def test_record_emits_l1_json_log_with_case_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L1 请求级结构化日志：method/path/status_code/duration_ms/request_id + 用例上下文。"""
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = _request()
    request.state.request_id = "req-l1-1"
    request.state.test_case_id = "S6-1"
    request.state.test_step_id = 2

    with caplog.at_level(logging.INFO, logger="openbase.audit"):
        middleware._record(request, 404, 15, "req-l1-1")

    emitted = [r for r in caplog.records if r.name == "openbase.audit"]
    assert emitted, "未产生 L1 请求级日志"
    record = emitted[-1]
    assert record.levelno == logging.INFO
    assert record.request_id == "req-l1-1"
    assert record.method == "GET"
    assert record.status_code == 404
    assert record.duration_ms == 15
    assert record.case_id == "S6-1"
    assert record.step_id == 2
    assert record.channel == "B"


def test_record_without_case_context_omits_fields() -> None:
    """未启用测试模式：不产生 case_id/step_id（保持既有日志形状，零影响）。"""
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = _request()
    request.state.request_id = "req-plain-1"

    middleware._record(request, 200, 5, "req-plain-1")

    record = AuditService._records[-1]
    assert "case_id" not in record.extra
    assert "step_id" not in record.extra


# ---------------------------------------------------------------------------
# C-5：出站透传 X-Test-Case-Id（与 X-Request-Id 同源策略）
# ---------------------------------------------------------------------------


def test_outbound_headers_carry_test_case_id_from_request_state() -> None:
    """出站头带 X-Test-Case-Id/X-Test-Step-Id（取 request.state，与 request_id 同源）。"""
    request = _request()
    request.state.request_id = "req-out-1"
    request.state.test_case_id = "UI-DPS-0007"
    request.state.test_step_id = 3

    headers = build_outbound_headers(request, None, target_system="dps")

    assert headers[HEADER_REQUEST_ID] == "req-out-1"
    assert headers[HEADER_TEST_CASE_ID] == "UI-DPS-0007"
    assert headers[HEADER_TEST_STEP_ID] == "3"


def test_outbound_headers_omit_test_case_id_when_absent() -> None:
    """非测试模式：出站不带 X-Test-Case-Id（零影响）。"""
    request = _request()
    request.state.request_id = "req-out-2"

    headers = build_outbound_headers(request, None, target_system="rag")

    assert HEADER_TEST_CASE_ID not in headers
    assert HEADER_TEST_STEP_ID not in headers


def test_outbound_headers_explicit_test_case_id_wins() -> None:
    """显式入参优先于 request.state（与 request_id 同源策略一致）。"""
    request = _request()
    request.state.test_case_id = "from-state"

    headers = build_outbound_headers(
        request, None, target_system="memory", test_case_id="explicit-case"
    )

    assert headers[HEADER_TEST_CASE_ID] == "explicit-case"


def test_outbound_headers_reject_header_injection_in_case_id() -> None:
    """用例头值经规范校验：含 CR/LF 的值不得透传（防头注入）。"""
    request = _request()
    request.state.test_case_id = "bad\r\nX-Injected: 1"

    headers = build_outbound_headers(request, None, target_system="llm")

    assert HEADER_TEST_CASE_ID not in headers


# ---------------------------------------------------------------------------
# C-8：/api/v1/audit/records 增 case_id/run_id 过滤
# ---------------------------------------------------------------------------


def _seed_records() -> None:
    from openbase.modules.audit import APICallRecord

    AuditService.record_api_call(
        APICallRecord(
            method="GET",
            path="/api/v1/dps-proxy/portraits",
            status_code=200,
            duration_ms=12,
            request_id="req-a",
            extra={"case_id": "UI-DPS-0007", "step_id": 1, "run_id": "run-1", "channel": "B"},
        )
    )
    AuditService.record_api_call(
        APICallRecord(
            method="POST",
            path="/api/v1/rag-proxy/collections",
            status_code=500,
            duration_ms=33,
            request_id="req-b",
            extra={"case_id": "S7-T2-1", "step_id": 2, "run_id": "run-2", "channel": "B"},
        )
    )


def test_audit_service_records_expose_case_context_and_filter() -> None:
    """AuditService.records 返回用例字段，并支持 case_id/run_id 过滤。"""
    _seed_records()

    everything = AuditService.records(limit=10)
    assert len(everything) == 2
    assert everything[0]["case_id"] == "S7-T2-1"

    only_case = AuditService.records(limit=10, case_id="UI-DPS-0007")
    assert [r["request_id"] for r in only_case] == ["req-a"]

    only_run = AuditService.records(limit=10, run_id="run-2")
    assert [r["request_id"] for r in only_run] == ["req-b"]

    assert AuditService.records(limit=10, case_id="not-exist") == []


def test_audit_records_endpoint_accepts_case_and_run_filters() -> None:
    """GET /audit/records?case_id=&run_id= 走同一过滤口径。"""
    from openbase.modules.audit import audit_records

    _seed_records()

    payload = asyncio.run(audit_records(limit=100, case_id="UI-DPS-0007", run_id=None))
    assert [r["request_id"] for r in payload["records"]] == ["req-a"]

    payload = asyncio.run(audit_records(limit=100, case_id=None, run_id="run-2"))
    assert [r["request_id"] for r in payload["records"]] == ["req-b"]
