"""R7（批次 3）：llm-proxy 上下文裁剪策略透传与 context_meta 回显."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from openbase.settings import Settings

UPSTREAM_BASE = "http://127.0.0.1:8001"
LLM_API_KEY = "sk-openllm-test-00000000000000000000000000000000"


class FakeResponse:
    """模拟 httpx.Response."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeStream:
    """模拟 httpx.AsyncClient.stream（SSE）."""

    def __init__(self, lines: list[str] | None = None, status_code: int = 200):
        self.lines = lines or []
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aiter_lines(self) -> AsyncGenerator[str, None]:
        for line in self.lines:
            yield line

    async def aread(self) -> bytes:
        return b"{}"


class FakeAsyncClient:
    """模拟 httpx.AsyncClient：记录请求并返回预设响应."""

    def __init__(self) -> None:
        self.request_calls: list[dict] = []
        self.responses: list[FakeResponse] = []
        self.stream_response: FakeStream | None = None

    def set_responses(self, responses: list[FakeResponse]) -> None:
        self.responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.request_calls.append({"method": method, "url": url, **kwargs})
        if not self.responses:
            return FakeResponse(200, {"code": 0, "message": "success", "data": {}})
        resp = self.responses.pop(0)
        self.responses.append(resp)
        return resp

    def stream(self, method: str, url: str, **kwargs) -> FakeStream:
        self.request_calls.append({"method": method, "url": url, "stream": True, **kwargs})
        return self.stream_response or FakeStream()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """启用 auth + llm_proxy 的应用，替换上游 httpx 客户端."""
    from openbase import init_app
    from openbase.modules.auth import UserService

    settings = Settings()
    for module in ("auth", "proxy", "llm_proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    settings.llm_api_key = LLM_API_KEY
    settings.llm_upstream_base = UPSTREAM_BASE
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    fake = FakeAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: fake)
    tc = TestClient(app)
    tc.fake = fake  # type: ignore[attr-defined]
    return tc


def _headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_chat_invalid_strategy_rejected_without_upstream(client: TestClient) -> None:
    """非法 strategy → 400 PARAM_INVALID，且不发起上游调用."""
    resp = client.post(
        "/api/v1/llm-proxy/chat",
        json={
            "model": "qwen3-8b",
            "messages": [{"role": "user", "content": "hi"}],
            "context_policy": {"strategy": "invalid"},
        },
        headers=_headers(client),
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "PARAM_INVALID"
    assert client.fake.request_calls == []  # type: ignore[attr-defined]


def test_chat_invalid_max_tokens_rejected(client: TestClient) -> None:
    """max_tokens 非正整数 → 400 PARAM_INVALID."""
    resp = client.post(
        "/api/v1/llm-proxy/chat",
        json={"context_policy": {"max_tokens": 0}},
        headers=_headers(client),
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "PARAM_INVALID"


def test_chat_passes_policy_and_keeps_upstream_context_meta(client: TestClient) -> None:
    """合法策略透传上游；上游 context_meta 原样保留."""
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "content": "ok",
                    "context_meta": {
                        "strategy": "summarize_old",
                        "dropped_messages": 3,
                        "source": "openllm",
                    },
                },
            },
        )
    ])
    resp = client.post(
        "/api/v1/llm-proxy/chat",
        json={
            "model": "qwen3-8b",
            "messages": [{"role": "user", "content": "hi"}],
            "context_policy": {"strategy": "summarize_old", "max_tokens": 2048},
        },
        headers=_headers(client),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["context_meta"]["strategy"] == "summarize_old"
    assert body["data"]["context_meta"]["source"] == "openllm"

    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["json"]["context_policy"] == {
        "strategy": "summarize_old",
        "max_tokens": 2048,
    }


def test_chat_fills_default_context_meta_when_upstream_missing(
    client: TestClient,
) -> None:
    """上游未返回 context_meta → 门户补默认值（applied=false）."""
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 0, "message": "success", "data": {"content": "ok"}})
    ])
    resp = client.post(
        "/api/v1/llm-proxy/chat",
        json={
            "model": "qwen3-8b",
            "messages": [{"role": "user", "content": "hi"}],
            "context_policy": {"strategy": "head_tail"},
        },
        headers=_headers(client),
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["data"]["context_meta"]
    assert meta == {
        "strategy": "head_tail",
        "applied": False,
        "source": "openbase-default",
    }


def test_chat_stream_invalid_policy_rejected(client: TestClient) -> None:
    """流式入口同样前置校验（非法策略 400）."""
    resp = client.post(
        "/api/v1/llm-proxy/chat/stream",
        json={"context_policy": {"preserve_recent_n": -1}},
        headers=_headers(client),
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "PARAM_INVALID"
    assert client.fake.request_calls == []  # type: ignore[attr-defined]
