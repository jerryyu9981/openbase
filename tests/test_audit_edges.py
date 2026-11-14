"""audit 模块覆盖率边角补测（覆盖率治理 v1.7.0）.

覆盖 ``openbase/modules/audit/__init__.py`` 中既有用例未触达的分支：
响应观测/长度解析/步骤归一、环形缓冲淘汰与过滤、落库队列排空/超时/批次边界、
审计中间件的路径跳过、客户端 IP 三级回落、请求体采集与脱敏、异常记录、
内部记录失败降级、worker 启停与导出 until 过滤。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

import openbase.modules.audit as audit_module
from openbase.modules.audit import (
    AuditMiddleware,
    AuditPersistQueue,
    AuditService,
    _normalize_step_id,
    _parse_content_length,
    _write_batch_records,
    audit_export,
    build_audit_record,
    build_response_observation,
    start_audit_persist_worker,
    stop_audit_persist_worker,
)


@pytest.fixture(autouse=True)
def _clean_audit_records():
    AuditService._records.clear()
    yield
    AuditService._records.clear()


def _record(**overrides):
    payload = {
        "method": "GET",
        "path": "/api/v1/echo",
        "status_code": 200,
        "duration_ms": 3,
        "request_id": "req-edge-1",
        "extra": {},
    }
    payload.update(overrides)
    return audit_module.APICallRecord(**payload)


def _mini_app(monkeypatch, *, seed_state: bool = False):
    monkeypatch.setenv(audit_module.ENV_AUDIT_DB_PERSIST, "1")
    captured: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        audit_module,
        "submit_audit_persist",
        lambda kind, payload: captured.append((kind, payload)) or True,
    )

    app = FastAPI()

    @app.get("/echo")
    async def _echo():
        return {"ok": True}

    @app.post("/echo")
    async def _echo_post():
        return {"ok": True}

    @app.get("/boom")
    async def _boom():
        raise RuntimeError("boom")

    app.add_middleware(AuditMiddleware)

    if seed_state:

        class _SeedMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.state.identity = {"principal": {"sub": "u-1"}}
                request.state.upstream_observation = {"upstream_status": 200}
                return await call_next(request)

        app.add_middleware(_SeedMiddleware)

    return TestClient(app, raise_server_exceptions=False), captured


# ---------------------------------------------------------------------------
# 观测 / 解析工具
# ---------------------------------------------------------------------------


def test_build_response_observation_without_keys():
    result = build_response_observation(
        status_code=204,
        content_type="application/json",
        content_length=None,
        error_code=None,
        payload=b"{}",
        allowlist=(),
    )
    assert result["resp_status"] == 204
    assert "resp_keys" not in result


def test_parse_content_length_invalid_returns_none():
    assert _parse_content_length(None) is None
    assert _parse_content_length("") is None
    assert _parse_content_length("12") == 12
    assert _parse_content_length("unknown") is None


def test_normalize_step_id_edges():
    assert _normalize_step_id(None) is None
    assert _normalize_step_id("   ") is None
    assert _normalize_step_id("12") == 12
    assert _normalize_step_id("s-1") == "s-1"


def test_build_audit_record_identity_projection():
    identity = SimpleNamespace(user_id=9, tenant_id="acme", team_id="t1", agent_id="a1")
    with_identity = build_audit_record(
        "GET", "/x", 200, 5, "req-1", identity=identity, operator_name="alice"
    )
    assert with_identity.operator_id == "9"
    assert with_identity.tenant_id == "acme"
    assert with_identity.extra == {"team_id": "t1", "agent_id": "a1"}

    bare = build_audit_record("GET", "/x", 200, 5, "req-2")
    assert bare.operator_id is None
    assert bare.extra == {}


# ---------------------------------------------------------------------------
# 内存服务
# ---------------------------------------------------------------------------


def test_ring_buffer_evicts_oldest(monkeypatch):
    monkeypatch.setattr(AuditService, "MAX_RECORDS", 2)
    for index in range(3):
        AuditService.record_api_call(_record(request_id=f"req-{index}"))
    rows = AuditService.records(limit=10)
    assert [row["request_id"] for row in rows] == ["req-2", "req-1"]


def test_records_filter_by_case_and_run():
    AuditService.record_api_call(_record(request_id="a", extra={"case_id": "c1", "run_id": "r1"}))
    AuditService.record_api_call(_record(request_id="b", extra={"case_id": "c2", "run_id": "r2"}))
    assert [r["request_id"] for r in AuditService.records(case_id="c1")] == ["a"]
    assert [r["request_id"] for r in AuditService.records(run_id="r2")] == ["b"]


# ---------------------------------------------------------------------------
# 落库队列
# ---------------------------------------------------------------------------


async def test_write_batch_records_reraises_when_session_unavailable(monkeypatch):
    from openbase.core.db import session as session_module

    monkeypatch.setenv(audit_module.ENV_AUDIT_DB_PERSIST, "1")

    def _broken_factory():
        raise RuntimeError("db down")

    monkeypatch.setattr(session_module, "get_session_factory", _broken_factory)
    with pytest.raises(RuntimeError, match="db down"):
        await _write_batch_records([("api_request", {"request_id": "req-x"})])


async def test_persist_queue_drain_with_zero_batch_size(monkeypatch):
    monkeypatch.setenv(audit_module.ENV_AUDIT_DB_PERSIST, "1")
    queue = AuditPersistQueue(batch_size=0)
    queue.submit("api_request", {"request_id": "req-1"})
    assert await queue.drain_once() == 0


async def test_persist_queue_run_processes_items(monkeypatch):
    monkeypatch.setenv(audit_module.ENV_AUDIT_DB_PERSIST, "1")

    async def _write(items):
        return len(items)

    monkeypatch.setattr(audit_module, "_write_batch_records", _write)
    queue = AuditPersistQueue(batch_size=1)
    task = asyncio.create_task(queue._run())
    queue.submit("api_request", {"request_id": "req-run"})
    for _ in range(5):
        if queue.stats()["persisted"]:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert queue.stats()["persisted"] == 1
    assert queue.stats()["submitted"] == 1


async def test_persist_queue_stop_timeout_with_empty_queue(monkeypatch):
    queue = AuditPersistQueue()

    async def _raise(timeout=0):
        raise TimeoutError("drain timeout")

    monkeypatch.setattr(queue, "drain_once", _raise)
    await queue.stop(timeout=0.01)
    assert queue.stats()["dropped"] == 0


async def test_worker_module_entrypoints(monkeypatch):
    async def _write(items):
        return 0

    monkeypatch.setattr(audit_module, "_write_batch_records", _write)
    start_audit_persist_worker()
    await stop_audit_persist_worker()


# ---------------------------------------------------------------------------
# 中间件
# ---------------------------------------------------------------------------


def test_middleware_client_ip_resolution(monkeypatch):
    client, _ = _mini_app(monkeypatch)
    client.get("/echo", headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.1"})
    assert AuditService.records(limit=1)[0]["ip_address"] == "9.9.9.9"

    client.get("/echo", headers={"X-Real-IP": "8.8.8.8"})
    assert AuditService.records(limit=1)[0]["ip_address"] == "8.8.8.8"

    client.get("/echo")
    assert AuditService.records(limit=1)[0]["ip_address"] == "testclient"


def test_middleware_unknown_client_ip():
    middleware = AuditMiddleware(app=FastAPI())
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/echo",
            "query_string": b"",
            "headers": [],
            "client": None,
            "server": None,
            "scheme": "http",
        }
    )
    assert middleware._extract_client_ip(request) == "unknown"


def test_middleware_skips_prefixed_paths(monkeypatch):
    client, _ = _mini_app(monkeypatch)
    client.get("/static/anything")
    assert AuditService.records(limit=1) == []


def _body_request(body: bytes, content_type: str = "application/json") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/echo",
        "query_string": b"",
        "headers": [(b"content-type", content_type.encode())],
        "client": None,
        "server": None,
        "scheme": "http",
    }
    messages = [{"type": "http.request", "body": body, "more_body": False}]

    async def _receive():
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, _receive)


async def test_read_request_body_non_json_returns_empty():
    middleware = AuditMiddleware(app=FastAPI())
    assert await middleware._read_request_body(_body_request(b"plain", "text/plain")) == ""


async def test_read_request_body_binary_marker():
    middleware = AuditMiddleware(app=FastAPI())
    assert await middleware._read_request_body(_body_request(b"\xff\xfe")) == "[Binary content]"


async def test_read_request_body_oversize_marker(monkeypatch):
    monkeypatch.setattr(AuditMiddleware, "MAX_BODY_SIZE", 1)
    middleware = AuditMiddleware(app=FastAPI())
    result = await middleware._read_request_body(_body_request(b'{"a": 1}'))
    assert "Body too large" in result


async def test_read_request_body_receive_error_returns_empty():
    middleware = AuditMiddleware(app=FastAPI())

    async def _broken_receive():
        raise RuntimeError("client gone")

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/echo",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": None,
            "server": None,
            "scheme": "http",
        },
        _broken_receive,
    )
    assert await middleware._read_request_body(request) == ""


def test_middleware_sanitizes_sensitive_path_body(monkeypatch):
    client, _ = _mini_app(monkeypatch)
    client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "secret"},
    )
    assert AuditService._records[-1].request_body == "[sensitive]"


def test_middleware_records_exception_and_reraises(monkeypatch):
    client, captured = _mini_app(monkeypatch)
    resp = client.get("/boom")
    assert resp.status_code == 500
    row = AuditService.records(limit=1)[0]
    assert row["status_code"] == 500
    assert "boom" in row["error"]
    assert any(kind == "api_request" for kind, _ in captured)


def test_middleware_persists_identity_detail(monkeypatch):
    client, captured = _mini_app(monkeypatch, seed_state=True)
    client.get("/echo")
    api_payloads = [payload for kind, payload in captured if kind == "api_request"]
    assert api_payloads
    assert api_payloads[-1]["detail"]["identity"] == {"principal": {"sub": "u-1"}}
    assert AuditService._records[-1].extra["upstream_status"] == 200


def test_read_response_body_failure_falls_back():
    async def _broken():
        raise RuntimeError("stream broken")
        yield b""  # pragma: no cover

    broken_response = SimpleNamespace(body_iterator=_broken())
    middleware = AuditMiddleware(app=FastAPI())
    returned, payload = asyncio.run(middleware._read_response_body(broken_response))
    assert returned is broken_response
    assert payload is None


def test_record_failure_returns_none(monkeypatch):
    def _raise(self, request):
        raise RuntimeError("headers broken")

    monkeypatch.setattr(AuditMiddleware, "_safe_headers", _raise)
    client, _ = _mini_app(monkeypatch)
    resp = client.get("/echo")
    assert resp.status_code == 200
    assert AuditService.records(limit=1) == []


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------


class _StreamResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        async def _gen():
            for row in self._rows:
                yield row

        return _gen()


class _StreamSession:
    async def stream(self, statement):
        row = SimpleNamespace(
            id=1,
            user_id=None,
            tenant_id=None,
            action="api_request",
            resource="/x",
            resource_id=None,
            ip=None,
            user_agent=None,
            request_id="req-export",
            detail={},
            created_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            prev_hash=None,
            entry_hash=None,
        )
        return _StreamResult([row])


async def test_audit_export_applies_until_filter(monkeypatch):
    monkeypatch.setattr(
        audit_module,
        "get_settings",
        lambda: SimpleNamespace(audit_export_max_rows=10),
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/audit/export",
            "query_string": b"",
            "headers": [],
            "client": None,
            "server": None,
            "scheme": "http",
            "state": {},
        }
    )
    response = await audit_export(
        request,
        since=None,
        until=dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc),
        limit=1,
        session=_StreamSession(),
    )
    chunks = [chunk async for chunk in response.body_iterator]
    raw = b"".join(item if isinstance(item, bytes) else item.encode() for item in chunks)
    lines = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(lines) == 1
    assert lines[0]["request_id"] == "req-export"
