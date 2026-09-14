"""C-16 上游响应专段补全：专用代理族（DPS / OpenLLM / OpenRAG / OpenMemory）接线测试.

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》§5 批 4 C-16 / §11.5 归因矩阵，
以及《OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0》§14#2 遗留项
（专用代理族 ``_forward`` 上游专段接线）。

覆盖口径：

- **四族非流式转发**（``dps_proxy`` / ``llm_proxy`` / ``rag_proxy``（含 multipart）/
  ``memory_proxy``（含 ``_forward_raw``））：成功路径记 ``upstream_status``/``upstream_digest``，
  不可达路径复用同一结构（无 status/digest，有 ``upstream_error``）；
- **``system`` 标识对齐**：与通用代理通道（``/api/v1/proxy/{system}`` 的路由键）一致，
  避免同一上游在两条通道下产生两套标识；
- **采集开关集中读取**：``OPENBASE_CAPTURE_UPSTREAM`` 开启时摘要必经 C-18 脱敏（手机号不算原文）；
- **无 request 上下文静默跳过**：不抛错、不影响既有转发语义（向后兼容）；
- **SSE 流式端点仅头部级专段**：流式体不可预读 → 无 digest，且在首事件前落位。
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase.demo_app import app
from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules import llm_proxy as llm_proxy_module
from openbase.modules import rag_proxy as rag_proxy_module
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.proxy import PROXY_SYSTEMS
from openbase.modules.proxy import memory_proxy as memory_proxy_module
from openbase.modules.proxy.upstream_observe import (
    UPSTREAM_SYSTEM_DPS,
    UPSTREAM_SYSTEM_OPENLLM,
    UPSTREAM_SYSTEM_OPENMEMORY,
    UPSTREAM_SYSTEM_OPENRAG,
)

client = TestClient(app)

admin_headers = {
    "Authorization": f"Bearer {create_access_token('1', username='admin', extra={'permissions': ['*']})}"
}

SENSITIVE_PHONE = "13812345678"
MASKED_PHONE = "138****5678"


class _FakeUpstreamResponse:
    """httpx 响应替身（仅暴露转发层使用到的接口）."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.content = json.dumps(payload).encode()
        self.text = self.content.decode()

    def json(self) -> dict[str, Any]:
        return json.loads(self.content)


class _FakeStream:
    """httpx 流式响应替身（SSE 用例）."""

    def __init__(self, status_code: int, lines: list[str]) -> None:
        self.status_code = status_code
        self.headers = {"content-type": "text/event-stream"}
        self._lines = lines

    async def aread(self) -> bytes:
        return json.dumps({"code": "BIZ_UPSTREAM_DOWN", "message": "upstream down"}).encode()

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeAsyncClient:
    """httpx.AsyncClient 替身：类属性驱动，不触网."""

    response: Any = None
    stream_result: Any = None
    error: Exception | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:  # noqa: ARG002
        if type(self).error is not None:
            raise type(self).error
        return type(self).response

    def stream(self, method: str, url: str, **kwargs: Any) -> Any:  # noqa: ARG002
        outer = self

        class _StreamContext:
            async def __aenter__(self_inner) -> Any:
                if type(outer).error is not None:
                    raise type(outer).error
                return type(outer).stream_result

            async def __aexit__(self_inner, *exc: Any) -> bool:
                return False

        return _StreamContext()


def _request() -> SimpleNamespace:
    """最小 Request 替身（专段仅依赖 ``request.state``）."""
    return SimpleNamespace(state=SimpleNamespace())


def _async_bytes(payload: bytes):
    """构造可 await 的 body 读取器（Request.body 替身）."""

    async def _read() -> bytes:
        return payload

    return _read


@pytest.fixture(autouse=True)
def _isolate_runtime(monkeypatch: pytest.MonkeyPatch):
    """用例级隔离：httpx 替身归零 + Settings 单例重置 + DPS 失败计数归零."""
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(dps_proxy_module, "_dps_consecutive_failures", 0)

    import sys

    from openbase.modules.audit import AuditService

    settings_module = sys.modules["openbase.settings"]
    original = settings_module._settings
    settings_module._settings = None
    AuditService._records.clear()
    yield
    settings_module._settings = original
    AuditService._records.clear()
    _FakeAsyncClient.response = None
    _FakeAsyncClient.stream_result = None
    _FakeAsyncClient.error = None


def _dps_forward(request: Any, method: str = "GET", path: str = "/api/v2/portrait/list"):
    return dps_proxy_module._forward(method, path, headers={}, request=request)


def _llm_forward(request: Any):
    return llm_proxy_module._forward("GET", "/openllm/v1/health", headers={}, request=request)


def _rag_forward(request: Any):
    return rag_proxy_module._forward("GET", "/api/v1/collections", request=request, user=None)


def _memory_forward(request: Any):
    return memory_proxy_module._forward(
        "POST", "/api/v1/remember", json_body={}, headers={}, request=request
    )


# ---- system 标识对齐（通用通道 ↔ 专用通道） ----


def test_upstream_system_identifiers_align_with_generic_channel() -> None:
    """专用通道 system 取值必须与通用代理通道路由键一致（同一上游只有一套标识）."""
    assert UPSTREAM_SYSTEM_DPS in PROXY_SYSTEMS
    assert UPSTREAM_SYSTEM_OPENLLM in PROXY_SYSTEMS
    assert UPSTREAM_SYSTEM_OPENRAG in PROXY_SYSTEMS
    assert UPSTREAM_SYSTEM_OPENMEMORY in PROXY_SYSTEMS


# ---- 成功路径：四族专段 ----


def test_dps_forward_publishes_success_segment() -> None:
    """DPS 通道：状态/耗时/digest 齐备，且默认关无摘要."""
    import asyncio

    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"code": 200, "data": {"items": []}})
    request = _request()
    result = asyncio.run(_dps_forward(request))

    assert result.status_code == 200
    segment = request.state.upstream_observation
    assert segment["upstream_system"] == UPSTREAM_SYSTEM_DPS
    assert segment["upstream_status"] == 200
    assert segment["upstream_duration_ms"] >= 0
    assert segment["upstream_digest"].startswith("sha256:")
    assert "upstream_body_summary" not in segment
    assert segment["upstream_calls"] == 1


def test_llm_forward_publishes_success_segment() -> None:
    """OpenLLM 通道：专段与通用通道同结构."""
    import asyncio

    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"status": "ok"})
    request = _request()
    asyncio.run(_llm_forward(request))

    segment = request.state.upstream_observation
    assert segment["upstream_system"] == UPSTREAM_SYSTEM_OPENLLM
    assert segment["upstream_status"] == 200
    assert segment["upstream_digest"].startswith("sha256:")


def test_rag_forward_publishes_business_error_code() -> None:
    """OpenRAG 通道：业务错误码可提取（归因矩阵「上游子系统」层依赖该字段）."""
    import asyncio

    _FakeAsyncClient.response = _FakeUpstreamResponse(
        404, {"code": "COLLECTION_NOT_FOUND", "message": "no such collection"}
    )
    request = _request()
    asyncio.run(_rag_forward(request))

    segment = request.state.upstream_observation
    assert segment["upstream_system"] == UPSTREAM_SYSTEM_OPENRAG
    assert segment["upstream_status"] == 404
    assert segment["upstream_error_code"] == "COLLECTION_NOT_FOUND"


def test_rag_multipart_forward_publishes_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenRAG multipart（文档上传）通道同样补记专段."""
    import asyncio

    monkeypatch.setattr(rag_proxy_module, "_build_upstream_headers", lambda request, user: {})
    _FakeAsyncClient.response = _FakeUpstreamResponse(202, {"code": 0, "data": {"task_id": "t1"}})
    request = _request()
    request.body = _async_bytes(b"file-bytes")
    request.headers = {"content-type": "multipart/form-data; boundary=x"}

    asyncio.run(
        rag_proxy_module._forward_multipart("/api/v1/collections/c1/documents", request, None)
    )

    segment = request.state.upstream_observation
    assert segment["upstream_system"] == UPSTREAM_SYSTEM_OPENRAG
    assert segment["upstream_status"] == 202


def test_memory_forward_and_raw_publish_segments() -> None:
    """OpenMemory 通道：``_forward`` 与 ``_forward_raw`` 两条出口均补记专段."""
    import asyncio

    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"code": 0, "data": {"results": []}})
    request = _request()
    asyncio.run(_memory_forward(request))
    assert request.state.upstream_observation["upstream_system"] == UPSTREAM_SYSTEM_OPENMEMORY

    raw_request = _request()
    asyncio.run(
        memory_proxy_module._forward_raw(
            "POST", "/api/v1/recall", json_body={}, headers={}, request=raw_request
        )
    )
    assert raw_request.state.upstream_observation["upstream_status"] == 200


# ---- 不可达路径：同一结构 ----


def test_dps_forward_unreachable_publishes_error_segment() -> None:
    """上游不可达：无 status/digest，有 error（复用同一专段结构）."""
    import asyncio

    from openbase.core.errors import BaseError

    _FakeAsyncClient.error = httpx.ConnectError("connect refused")
    request = _request()

    with pytest.raises(BaseError):
        asyncio.run(_dps_forward(request))

    segment = request.state.upstream_observation
    assert segment["upstream_system"] == UPSTREAM_SYSTEM_DPS
    assert "upstream_status" not in segment
    assert "upstream_digest" not in segment
    assert "connect refused" in segment["upstream_error"]


# ---- 采集开关（红线）：默认关 / 开启脱敏 ----


def test_capture_switch_off_keeps_no_summary() -> None:
    """默认关：四族均零采集（摘要字段不出现）."""
    import asyncio

    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"message": f"联系人 {SENSITIVE_PHONE}"})
    request = _request()
    asyncio.run(_dps_forward(request))

    assert "upstream_body_summary" not in request.state.upstream_observation


def test_capture_switch_on_masks_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """开启（非生产）：产出摘要且经 C-18 脱敏（手机号原文不落盘）."""
    import asyncio
    import sys

    monkeypatch.setenv("OPENBASE_CAPTURE_UPSTREAM", "1")
    sys.modules["openbase.settings"]._settings = None

    _FakeAsyncClient.response = _FakeUpstreamResponse(
        200, {"message": f"联系人 {SENSITIVE_PHONE} 已同步"}
    )
    request = _request()
    asyncio.run(_dps_forward(request))

    segment = request.state.upstream_observation
    assert MASKED_PHONE in str(segment["upstream_body_summary"])
    assert SENSITIVE_PHONE not in str(segment)


def test_capture_is_permanently_off_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """生产永久关：env=production 且开关置 1 亦不产摘要（红线 4）."""
    import asyncio
    import sys

    monkeypatch.setenv("OPENBASE_CAPTURE_UPSTREAM", "1")
    monkeypatch.setenv("OPENBASE_ENV", "production")
    sys.modules["openbase.settings"]._settings = None

    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"message": f"联系人 {SENSITIVE_PHONE}"})
    request = _request()
    asyncio.run(_dps_forward(request))

    assert "upstream_body_summary" not in request.state.upstream_observation


# ---- 向后兼容：无 request 上下文 ----


def test_forward_without_request_skips_observation_silently() -> None:
    """未传 request（如脚本/工具直调）：转发语义不变，仅跳过观测（不抛错）."""
    import asyncio

    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"status": "ok"})

    dps_response = asyncio.run(dps_proxy_module._forward("GET", "/health/liveness", headers={}))
    memory_response = asyncio.run(
        memory_proxy_module._forward("POST", "/api/v1/remember", json_body={}, headers={})
    )

    assert dps_response.status_code == 200
    assert memory_response.status_code == 200


# ---- SSE 流式端点：仅头部级专段 ----


def test_sse_forward_publishes_header_level_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SSE 2xx：只记状态/耗时（流式体不预读 → 无 digest），且在首事件前落位."""
    import asyncio

    recorded: list[dict[str, Any]] = []

    def _recorder(request: Any, **kwargs: Any) -> dict[str, Any]:
        recorded.append(kwargs)
        request.state.upstream_observation = kwargs
        return kwargs

    monkeypatch.setattr(rag_proxy_module, "publish_upstream_response", _recorder)
    _FakeAsyncClient.stream_result = _FakeStream(200, ["data: hello", ""])
    request = _request()

    async def _drive() -> None:
        response = await rag_proxy_module._forward_sse(
            "/api/v1/query/stream", {"q": "x"}, request=request
        )
        async for _ in response.body_iterator:
            break

    asyncio.run(_drive())

    assert recorded[0]["system"] == UPSTREAM_SYSTEM_OPENRAG
    assert recorded[0]["status_code"] == 200
    assert recorded[0].get("payload") is None
    assert recorded[0]["reached"] is True


def test_sse_upstream_error_publishes_payload_segment() -> None:
    """SSE 4xx/5xx：错误体可读 → 记状态与错误码（可归因到上游）."""
    import asyncio

    _FakeAsyncClient.stream_result = _FakeStream(500, [])
    request = _request()

    async def _drive() -> None:
        response = await rag_proxy_module._forward_sse(
            "/api/v1/query/stream", {"q": "x"}, request=request
        )
        async for _ in response.body_iterator:
            break

    asyncio.run(_drive())
    segment = request.state.upstream_observation
    assert segment["upstream_status"] == 500
    assert segment["upstream_error_code"] == "BIZ_UPSTREAM_DOWN"


# ---- 端到端：专用通道 → 审计记录同列 ----


def test_dps_proxy_endpoint_records_segment_in_audit() -> None:
    """端到端：``/api/v1/dps-proxy/portraits`` 的上游专段进入同一条审计记录."""
    _FakeAsyncClient.response = _FakeUpstreamResponse(200, {"code": 200, "data": {"items": []}})
    resp = client.get("/api/v1/dps-proxy/portraits", headers=admin_headers)
    assert resp.status_code == 200, resp.text

    from openbase.modules.audit import AuditService

    row = AuditService.records(limit=1)[0]
    assert row["upstream_system"] == UPSTREAM_SYSTEM_DPS
    assert row["upstream_status"] == 200
    assert row["resp_status"] == 200
