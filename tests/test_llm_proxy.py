"""测试 v1.4.3 R-379 AC-143-03：llm-proxy Bearer 注入 + 统一响应适配 + 错误透传 + 401 拦截."""

import json
from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from openbase import init_app
from openbase.modules import llm_proxy as llm_proxy_module
from openbase.modules.auth import UserService
from openbase.modules.auth.jwt import create_access_token
from openbase.settings import Settings

UPSTREAM_BASE = "http://127.0.0.1:8001"
LLM_API_KEY = "sk-openllm-test-00000000000000000000000000000000"


def _identity_token() -> str:
    """签发带完整外部身份的 JWT（sub/org_id 与现 JWT claim 同源）.

    P0-2（Q4 最小档）：llm_proxy 注入 X-User-ID(sub)/X-Org-ID(org_id)/
    X-Proxy-Source，供 OpenLLM TRUSTED_PROXY_SOURCES 可信源解析。
    """
    return create_access_token(
        "42",
        username="identity-user",
        tenant_id="tenant-001",
        extra={"org_id": "org-001", "role": "admin"},
    )


class FakeResponse:
    """模拟 httpx.Response."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeStream:
    """模拟 httpx.AsyncClient.stream 的异步上下文（SSE 事件流）."""

    def __init__(self, lines: list[str] | None = None, status_code: int = 200, raise_error: Exception | None = None):
        self.lines = lines or []
        self.status_code = status_code
        self.raise_error = raise_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aiter_lines(self) -> AsyncGenerator[str, None]:
        if self.raise_error is not None:
            raise self.raise_error
        for line in self.lines:
            yield line

    async def aread(self) -> bytes:
        return b'{"code": 1001, "message": "auth failed"}'


class FakeAsyncClient:
    """模拟 httpx.AsyncClient：记录请求并返回预设响应."""

    def __init__(self, *args, **kwargs):
        self.request_calls: list[dict] = []
        self.responses: list[FakeResponse] = []
        self.fail_with: Exception | None = None
        self.stream_response: FakeStream | None = None

    def set_responses(self, responses: list[FakeResponse]) -> None:
        self.responses = responses

    def set_stream(self, stream: FakeStream) -> None:
        self.stream_response = stream

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.request_calls.append({"method": method, "url": url, **kwargs})
        if self.fail_with is not None:
            raise self.fail_with
        if self.responses:
            resp = self.responses.pop(0)
            if not self.responses:
                self.responses.append(resp)
            return resp
        return FakeResponse(200, {"results": [], "trace_id": None})

    def stream(self, method: str, url: str, **kwargs) -> FakeStream:
        self.request_calls.append({"method": method, "url": url, "stream": True, **kwargs})
        if self.stream_response is not None:
            return self.stream_response
        return FakeStream(status_code=200)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """构造启用 auth + llm_proxy 的应用，替换上游 httpx 客户端并覆盖 llm 配置."""
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


def _token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_llm_proxy_no_token_returns_401(client: TestClient) -> None:
    """无认证头 → 401（AC-143-03-5）."""
    resp = client.get("/api/v1/llm-proxy/models")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


def test_llm_proxy_models_success_unified_response(client: TestClient) -> None:
    """认证 models → 200 统一 {code,message,data,timestamp} + Bearer sk-openllm- 注入（AC-143-03-1/2）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "models": [
                        {"id": "qwen2.5-7b", "object": "model", "created": 0, "owned_by": "openllm"}
                    ]
                },
            },
        ),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "data", "timestamp"}
    assert body["code"] == 0
    assert body["data"]["models"][0]["id"] == "qwen2.5-7b"

    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    headers = call["headers"]
    # OpenLLM 认证契约：API Key 仅 Authorization Bearer 传递（不支持 X-API-Key 头）
    assert headers["Authorization"].startswith("Bearer sk-openllm-")
    assert "X-API-Key" not in headers
    assert call["url"].startswith(f"{UPSTREAM_BASE}/openllm/v1/models")
    # P0-2（Q4 最小档）：登录 JWT 携带身份 → 注入 X-User-ID/X-Proxy-Source
    # （memory 演示用户 org 为空，故此处不要求 X-Org-ID，见身份专用用例）
    assert headers["X-User-ID"] == "1"
    assert headers["X-Proxy-Source"] == llm_proxy_module.PROXY_SOURCE_IDENTIFIER


def test_llm_proxy_injects_external_identity_headers(client: TestClient) -> None:
    """P0-2：带完整身份 JWT → 注入 X-User-ID/X-Org-ID/X-Proxy-Source（Q4/M3）."""
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "models": [
                        {"id": "qwen2.5-7b", "object": "model", "created": 0, "owned_by": "openllm"}
                    ]
                },
            },
        ),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/models",
        headers={"Authorization": f"Bearer {_identity_token()}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    headers = call["headers"]
    # 外部身份归属头（与 JWT claim 同源：sub → X-User-ID；org_id → X-Org-ID）
    assert headers["X-User-ID"] == "42"
    assert headers["X-Org-ID"] == "org-001"
    assert headers["X-Proxy-Source"] == llm_proxy_module.PROXY_SOURCE_IDENTIFIER
    # 服务密钥不变；不引入 X-API-Key
    assert headers["Authorization"].startswith("Bearer sk-openllm-")
    assert "X-API-Key" not in headers


def test_llm_proxy_identity_headers_omitted_without_jwt() -> None:
    """P0-2：无身份来源（匿名/服务级内部调用）→ 不注入任何外部身份头."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/openllm/v1/models",
        "raw_path": b"/openllm/v1/models",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    headers = llm_proxy_module._build_upstream_headers(StarletteRequest(scope))
    assert headers["Authorization"].startswith("Bearer sk-openllm-")
    assert "X-API-Key" not in headers
    assert "X-User-ID" not in headers
    assert "X-Org-ID" not in headers
    assert "X-Proxy-Source" not in headers


def test_llm_proxy_error_code_passthrough(client: TestClient) -> None:
    """上游 1001 → 响应 code=1001 透传 + HTTP 401（AC-143-03-3）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(401, {"code": 1001, "message": "authentication failed", "request_id": "r-1"}),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["code"] == 1001
    assert "authentication failed" in body["message"]


def test_llm_proxy_upstream_unreachable_returns_502(client: TestClient) -> None:
    """上游不可达 → 502 级错误（SYS_UPSTREAM_ERROR，AC-143-03-6）."""
    token = _token(client)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    resp = client.get(
        "/api/v1/llm-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


def test_llm_proxy_health_success(client: TestClient) -> None:
    """health → 200 统一响应（AC-143-03-1）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {"code": 0, "message": "success", "data": {"status": "healthy", "version": "2.13.0"}},
        ),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "healthy"


def test_llm_proxy_chat_stream_requires_auth(client: TestClient) -> None:
    """SSE 流式端点无认证 → 401（AC-143-03-4 前置）."""
    resp = client.post("/api/v1/llm-proxy/chat/stream", json={"model": "m", "messages": []})
    assert resp.status_code == 401, resp.text


def test_llm_proxy_chat_success(client: TestClient) -> None:
    """对话端点 → 200 统一响应 + 请求体透传（AC-143-03-1）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "choices": [{"message": {"role": "assistant", "content": "你好"}}],
                    "usage": {"total_tokens": 10},
                },
            },
        ),
    ])
    payload = {"model": "qwen2.5-7b", "messages": [{"role": "user", "content": "你好"}]}
    resp = client.post(
        "/api/v1/llm-proxy/chat",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["choices"][0]["message"]["content"] == "你好"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["json"] == payload
    assert call["url"].startswith(f"{UPSTREAM_BASE}/openllm/v1/chat")


# ---------------------------------------------------------------------------
# 会话端点族（M1 未实施前：上游 401 透传；此处验证 proxy 转发契约与响应适配）
# ---------------------------------------------------------------------------


def test_llm_proxy_conversations_list(client: TestClient) -> None:
    """会话列表 → 统一响应 + 分页参数透传（AC-143-03-1）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"items": [{"id": "c1", "title": "t"}], "total": 1}),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/conversations?skip=0&limit=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["items"][0]["id"] == "c1"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/conversations")
    assert call["params"] == {"status": None, "skip": 0, "limit": 20}


def test_llm_proxy_conversation_create(client: TestClient) -> None:
    """新建会话 → 统一响应 + body 透传."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"id": "c2", "title": "新会话"}),
    ])
    payload = {"title": "新会话", "model": "qwen2.5-7b"}
    resp = client.post(
        "/api/v1/llm-proxy/conversations",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == "c2"
    assert client.fake.request_calls[0]["json"] == payload  # type: ignore[attr-defined]


def test_llm_proxy_conversation_detail(client: TestClient) -> None:
    """会话详情 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"id": "c1", "title": "t"}),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/conversations/c1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == "c1"


def test_llm_proxy_conversation_delete(client: TestClient) -> None:
    """删除会话 → 统一响应（软删）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"deleted": True}),
    ])
    resp = client.delete(
        "/api/v1/llm-proxy/conversations/c1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["deleted"] is True


def test_llm_proxy_conversation_archive(client: TestClient) -> None:
    """归档会话 → 统一响应 + body 透传（含空 body 场景）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"id": "c1", "archived": True}),
    ])
    resp = client.post(
        "/api/v1/llm-proxy/conversations/c1/archive",
        json={"archived": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["archived"] is True
    assert client.fake.request_calls[0]["json"] == {"archived": True}  # type: ignore[attr-defined]


def test_llm_proxy_conversation_messages(client: TestClient) -> None:
    """会话消息列表 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, [{"role": "user", "content": "hi"}]),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/conversations/c1/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0


def test_llm_proxy_model_detail_not_found(client: TestClient) -> None:
    """模型详情：列表无该模型 → 2001 资源不存在（降级过滤）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 0, "message": "success", "data": {"models": []}}),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/models/nonexistent-model",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == 2001


def test_llm_proxy_model_detail_upstream_error(client: TestClient) -> None:
    """模型详情：上游网关错误 → 错误透传（不降级处理）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(401, {"code": 1001, "message": "auth failed"}),
    ])
    resp = client.get(
        "/api/v1/llm-proxy/models/gpt-4",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == 1001


# ---------------------------------------------------------------------------
# SSE 流式透传（AC-143-03-4）：成功事件流 / 上游 4xx error 事件 / 流中断 error 事件
# ---------------------------------------------------------------------------


def test_llm_proxy_sse_success_stream(client: TestClient) -> None:
    """SSE 成功：routing/chunk/done 事件逐行透传."""
    token = _token(client)
    client.fake.set_stream(  # type: ignore[attr-defined]
        FakeStream(
            lines=[
                "event: routing",
                'data: {"model": "qwen2.5-7b"}',
                "",
                "event: chunk",
                'data: {"delta": "你好"}',
                "",
                "event: done",
                'data: {"usage": {"total_tokens": 10}}',
                "",
            ]
        )
    )
    resp = client.post(
        "/api/v1/llm-proxy/chat/stream",
        json={"model": "qwen2.5-7b", "messages": [{"role": "user", "content": "hi"}], "stream": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert "event: routing" in body
    assert "event: chunk" in body
    assert "event: done" in body
    assert "你好" in body


def test_llm_proxy_sse_upstream_error_event(client: TestClient) -> None:
    """SSE 上游 4xx → error 事件透传 + WARN 日志."""
    token = _token(client)
    client.fake.set_stream(  # type: ignore[attr-defined]
        FakeStream(status_code=401, lines=[])
    )
    resp = client.post(
        "/api/v1/llm-proxy/chat/stream",
        json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text  # SSE 连接建立后事件内透传错误
    assert "event: error" in resp.text


def test_llm_proxy_sse_stream_interrupted(client: TestClient) -> None:
    """SSE 上游中断（HTTPError）→ error 事件 + 连接关闭."""
    token = _token(client)
    client.fake.set_stream(  # type: ignore[attr-defined]
        FakeStream(raise_error=httpx.ConnectError("connection lost"))
    )
    resp = client.post(
        "/api/v1/llm-proxy/chat/stream",
        json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert "event: error" in resp.text
    assert "stream interrupted" in resp.text
