"""DW-01 回归（2026-10-28）：只读聚合端点放宽超时 + GET 传输级失败重试 1 次.

背景：全页面走查中 `/dashboard` 的 `monitoring/dashboard` 出现 1 次 502，
单跑 200（1.3~3.9s）——跨网链路抖动下上游读超时。修复策略：
- 仅对只读聚合路径（dashboard / 成本 / 用量）把超时放宽到 30s；
- GET/HEAD 在 `httpx.TransportError` 时重试 1 次，写请求不重试（避免重复副作用）。
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from openbase.modules.proxy import (
    SLOW_PATH_TIMEOUT,
    _request_upstream,
    _timeout,
)


class _FlakyClient:
    """首次抛传输错误、第二次返回成功响应的假客户端。"""

    def __init__(self) -> None:
        self.calls = 0

    async def request(self, method, url, headers=None, content=None):
        self.calls += 1
        if self.calls == 1:
            raise httpx.ConnectError("connection reset")
        return httpx.Response(200, json={"ok": True})


def test_slow_aggregate_path_gets_wider_timeout() -> None:
    """聚合端点 30s，普通端点保持 10s。"""
    assert _timeout("openllm", "/api/v1/monitoring/dashboard") == SLOW_PATH_TIMEOUT
    assert _timeout("openllm", "/api/v1/billing/v2/cost-analysis") == SLOW_PATH_TIMEOUT
    assert _timeout("openllm", "/api/v1/monitoring/usage") == SLOW_PATH_TIMEOUT
    assert _timeout("openllm", "/api/v1/models") == 10.0


def test_get_retries_once_after_transport_error() -> None:
    """GET 传输级失败重试 1 次后成功。"""
    client = _FlakyClient()
    response = asyncio.run(_request_upstream(client, "GET", "http://upstream/x", {}, None))
    assert response.status_code == 200
    assert client.calls == 2


def test_post_does_not_retry() -> None:
    """写请求不重试，异常原样上抛。"""
    client = _FlakyClient()
    with pytest.raises(httpx.ConnectError):
        asyncio.run(_request_upstream(client, "POST", "http://upstream/x", {}, b"{}"))
    assert client.calls == 1
