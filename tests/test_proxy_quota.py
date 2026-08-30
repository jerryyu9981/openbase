"""测试 v1.3.0 代理层 402 错误码统一处理（TD-13-28）.

验证：① 错误码表含 BIZ_MODEL_QUOTA 且 HTTP 映射 402；② 代理层上游 402 → 统一 ErrorResponse。
"""

import asyncio

import pytest
from fastapi import Request

import openbase.modules.proxy as proxy_module
from openbase.core.errors import ErrorCode
from openbase.core.errors.codes import ERROR_HTTP_MAP


def test_biz_model_quota_error_code_defined() -> None:
    """错误码表包含 BIZ_MODEL_QUOTA，且 HTTP 映射为 402."""
    assert ErrorCode.BIZ_MODEL_QUOTA == "BIZ_MODEL_QUOTA"
    assert ERROR_HTTP_MAP[ErrorCode.BIZ_MODEL_QUOTA] == 402


class _FakeResponse:
    """模拟 httpx 上游响应."""

    def __init__(self, status_code: int, json_body: dict | None = None) -> None:
        self.status_code = status_code
        self._json_body = json_body or {"error": "Insufficient Balance"}

    def json(self) -> dict:
        return self._json_body


class _FakeClient:
    """模拟 httpx.AsyncClient.request 返回 402."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def request(self, *args, **kwargs) -> _FakeResponse:
        return self._response


def _run(coro) -> object:
    return asyncio.run(coro)


def _make_request() -> Request:
    """构造最小 Request（依赖 get_current_user 由路由注入，直接调用时置空）. """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/proxy/openllm/health",
        "headers": [],
        "query_string": b"",
        "state": {"request_id": "test-request-id"},
    }
    return Request(scope)


def test_proxy_wraps_402_to_unified_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """上游 402 → 代理层返回统一 ErrorResponse（code=BIZ_MODEL_QUOTA, HTTP 402）."""
    monkeypatch.setattr(
        proxy_module.httpx, "AsyncClient", lambda **kwargs: _FakeClient(_FakeResponse(402))
    )
    request = _make_request()
    response = _run(proxy_module.proxy("openllm", "chat/stream", request, identity={"id": 1}))
    assert response.status_code == 402
    payload = response.body.decode("utf-8")
    assert '"code":"BIZ_MODEL_QUOTA"' in payload
    assert "模型服务余额不足" in payload
    # 不暴露上游原始错误
    assert "Insufficient Balance" not in payload


def test_proxy_passthrough_non_402(monkeypatch: pytest.MonkeyPatch) -> None:
    """非 402 状态码（如 200/404）保持透传，不包装."""
    monkeypatch.setattr(
        proxy_module.httpx, "AsyncClient", lambda **kwargs: _FakeClient(_FakeResponse(200, {"ok": True}))
    )
    request = _make_request()
    response = _run(proxy_module.proxy("openrag", "health", request, identity={"id": 1}))
    assert response.status_code == 200
    assert '"ok":true' in response.body.decode("utf-8")
