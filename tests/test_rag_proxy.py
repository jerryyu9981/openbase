"""测试 v1.4.4 R-380 AC-144-03：rag-proxy JWT 门禁 + 转发 + 统一响应 + {detail} 归一化 + SSE 透传 + multipart 上传."""

import json
from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.modules.auth import UserService
from openbase.settings import Settings

UPSTREAM_BASE = "http://127.0.0.1:8010"


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
        return b'{"code": 404, "message": "collection not found"}'


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
        return FakeResponse(200, {"code": 0, "message": "success", "data": {"items": []}})

    def stream(self, method: str, url: str, **kwargs) -> FakeStream:
        self.request_calls.append({"method": method, "url": url, "stream": True, **kwargs})
        if self.stream_response is not None:
            return self.stream_response
        return FakeStream(status_code=200)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """构造启用 auth + rag_proxy 的应用，替换上游 httpx 客户端并覆盖 rag 配置."""
    settings = Settings()
    for module in ("auth", "proxy", "rag_proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    settings.rag_upstream_base = UPSTREAM_BASE
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


# ---------------------------------------------------------------------------
# 认证门禁（AC-144-02-1 / AC-144-03-5）
# ---------------------------------------------------------------------------


def test_rag_proxy_no_token_returns_401(client: TestClient) -> None:
    """无认证头 → 401（AC-144-02-1 / AC-144-03-5）."""
    resp = client.get("/api/v1/rag-proxy/collections")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


def test_rag_proxy_sse_requires_auth(client: TestClient) -> None:
    """SSE 流式端点无认证 → 401（AC-144-03-5 前置）."""
    resp = client.post(
        "/api/v1/rag-proxy/collections/c1/query/stream",
        json={"query": "hi"},
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# 知识库族（AC-144-03-1/2）
# ---------------------------------------------------------------------------


def test_rag_proxy_collections_list_success(client: TestClient) -> None:
    """知识库列表 → 200 统一 {code,message,data,timestamp} + 分页参数透传（AC-144-03-1/2）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [{"id": "col-1", "name": "产品知识库", "document_count": 3}],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                },
            },
        ),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/collections?page=1&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "data", "timestamp"}
    assert body["code"] == 0
    assert body["data"]["items"][0]["id"] == "col-1"

    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    # OpenRAG 无认证：不注入 Authorization / X-API-Key
    assert "Authorization" not in call["headers"]
    assert "X-API-Key" not in call["headers"]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/collections")
    assert call["params"] == {"page": 1, "page_size": 20}


def test_rag_proxy_collection_create_success(client: TestClient) -> None:
    """创建知识库 → 200 + collection_id 返回（AC-144-05-1 前置）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {"id": "col-new", "name": "研发知识库", "chunk_size": 512},
            },
        ),
    ])
    payload = {"name": "研发知识库", "chunk_size": 512, "chunk_overlap": 50}
    resp = client.post(
        "/api/v1/rag-proxy/collections",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == "col-new"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["json"] == payload
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/collections")


def test_rag_proxy_collection_detail_success(client: TestClient) -> None:
    """知识库详情 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {"id": "col-1", "name": "产品知识库", "status": "ready"},
            },
        ),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/collections/col-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "ready"


def test_rag_proxy_collection_delete_success(client: TestClient) -> None:
    """删除知识库 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 0, "message": "success", "data": {"deleted": True}}),
    ])
    resp = client.delete(
        "/api/v1/rag-proxy/collections/col-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["deleted"] is True


# ---------------------------------------------------------------------------
# 错误归一化（AC-144-03-3）
# ---------------------------------------------------------------------------


def test_rag_proxy_detail_error_normalization(client: TestClient) -> None:
    """上游 {detail} 字符串 → 归一化：code=HTTP 状态码，message=detail（AC-144-03-3）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(404, {"detail": "知识库不存在: col-404"}),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/collections/col-404",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["code"] == 404
    assert "知识库不存在" in body["message"]


def test_rag_proxy_detail_dict_error_normalization(client: TestClient) -> None:
    """上游 {detail: {error, code, message}} → 归一化：code/message 提取."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            409,
            {
                "detail": {
                    "error": "COLLECTION_NAME_CONFLICT",
                    "code": 409,
                    "message": "知识库名称已存在: 研发知识库",
                }
            },
        ),
    ])
    resp = client.post(
        "/api/v1/rag-proxy/collections",
        json={"name": "研发知识库"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["code"] == 409
    assert "已存在" in body["message"]


def test_rag_proxy_gateway_error_passthrough(client: TestClient) -> None:
    """上游网关错误体 {code, message} → code/message 透传（AC-144-03-3）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(500, {"code": 5000, "message": "internal error", "timestamp": "2026-08-30T00:00:00Z"}),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/collections/col-x",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 500, resp.text
    body = resp.json()
    assert body["code"] == 5000
    assert body["message"] == "internal error"


def test_rag_proxy_detail_list_error_normalization(client: TestClient) -> None:
    """上游 422 detail 为 FastAPI 数组 → 归一化提取各 msg（AC-144-03-3）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            422,
            {
                "detail": [
                    {"type": "string_too_short", "loc": ["body", "query"], "msg": "String should have at least 1 character", "input": ""},
                    {"type": "missing", "loc": ["body", "collection_ids"], "msg": "Field required", "input": {}},
                ]
            },
        ),
    ])
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query",
        json={"query": "hi", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == 422
    assert "String should have at least 1 character" in body["message"]
    assert "Field required" in body["message"]


def test_rag_proxy_query_collection_ids_passthrough(client: TestClient) -> None:
    """RAG 查询透传 collection_ids（OpenRAG 多集合契约）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 0, "message": "success", "data": {"answer": "ok"}}),
    ])
    payload = {"query": "hi", "collection_ids": ["col-1", "col-2"]}
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["json"]["collection_ids"] == ["col-1", "col-2"]


def test_rag_proxy_upstream_unreachable_returns_502(client: TestClient) -> None:
    """上游不可达 → 502 级错误（SYS_UPSTREAM_ERROR，AC-144-03-6）."""
    token = _token(client)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    resp = client.get(
        "/api/v1/rag-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


# ---------------------------------------------------------------------------
# 文档族（AC-144-03-1，multipart 上传）
# ---------------------------------------------------------------------------


def test_rag_proxy_document_upload_pending(client: TestClient) -> None:
    """文档上传 multipart → 返回 PENDING + document_id（AC-144-05-2 前置）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {"status": "PENDING", "document_id": "doc-1"},
            },
        ),
    ])
    files = {"file": ("guide.pdf", b"%PDF-1.4 fake pdf", "application/pdf")}
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "PENDING"
    assert resp.json()["data"]["document_id"] == "doc-1"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/collections/col-1/documents")
    # multipart 原始体透传（不解析表单，边界/编码原样，文件字节在体内）
    assert b"%PDF-1.4 fake pdf" in call["content"]
    assert call["headers"]["Content-Type"].startswith("multipart/form-data")


def test_rag_proxy_documents_list(client: TestClient) -> None:
    """文档列表 → 统一响应 + status_filter 透传."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [{"id": "doc-1", "filename": "guide.pdf", "status": "COMPLETED"}],
                    "total": 1,
                },
            },
        ),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/collections/col-1/documents?status_filter=COMPLETED",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"][0]["status"] == "COMPLETED"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["params"]["status_filter"] == "COMPLETED"


def test_rag_proxy_document_detail_polling(client: TestClient) -> None:
    """文档详情轮询（上传异步 PENDING→COMPLETED，需求 §4.3 契约）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {"id": "doc-1", "status": "COMPLETED", "chunk_count": 12},
            },
        ),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/collections/col-1/documents/doc-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "COMPLETED"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/collections/col-1/documents/doc-1")


def test_rag_proxy_document_delete(client: TestClient) -> None:
    """删除文档 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 0, "message": "success", "data": {"deleted": True}}),
    ])
    resp = client.delete(
        "/api/v1/rag-proxy/collections/col-1/documents/doc-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["deleted"] is True


# ---------------------------------------------------------------------------
# 查询族（AC-144-03-1/4）
# ---------------------------------------------------------------------------


def test_rag_proxy_query_success(client: TestClient) -> None:
    """RAG 查询 → 统一响应 + body 透传."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "answer": "OpenRAG 是检索增强生成框架",
                    "sources": [{"chunk_id": "chunk-1", "score": 0.92}],
                },
            },
        ),
    ])
    payload = {"query": "OpenRAG 是什么", "top_k": 3}
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert "OpenRAG 是检索增强生成框架" in resp.json()["data"]["answer"]
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["json"] == payload


def test_rag_proxy_retrieve_success(client: TestClient) -> None:
    """纯检索 → items 数组."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [{"chunk_id": "chunk-1", "content": "知识内容", "score": 0.95, "retrieval_channel": "hybrid"}],
                    "total": 1,
                },
            },
        ),
    ])
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query/retrieve",
        json={"query": "知识", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"][0]["score"] == 0.95


# ---------------------------------------------------------------------------
# SSE 流式透传（AC-144-03-4 / AC-144-05-4）
# ---------------------------------------------------------------------------


def test_rag_proxy_sse_success_stream(client: TestClient) -> None:
    """SSE 成功：start/token/done 事件逐行透传（AC-144-03-4）."""
    token = _token(client)
    client.fake.set_stream(  # type: ignore[attr-defined]
        FakeStream(
            lines=[
                "event: start",
                'data: {"query": "OpenRAG 是什么"}',
                "",
                "event: token",
                'data: {"delta": "OpenRAG 是"}',
                "",
                "event: token",
                'data: {"delta": "检索增强生成框架"}',
                "",
                "event: done",
                'data: {"answer": "OpenRAG 是检索增强生成框架", "sources": [{"chunk_id": "c1"}]}',
                "",
            ]
        )
    )
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query/stream",
        json={"query": "OpenRAG 是什么", "stream": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert "event: start" in body
    assert "event: token" in body
    assert "event: done" in body
    assert "检索增强生成框架" in body


def test_rag_proxy_sse_upstream_error_event(client: TestClient) -> None:
    """SSE 上游 4xx → error 事件透传."""
    token = _token(client)
    client.fake.set_stream(  # type: ignore[attr-defined]
        FakeStream(status_code=404, lines=[])
    )
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query/stream",
        json={"query": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text  # SSE 连接建立后事件内透传错误
    assert "event: error" in resp.text


def test_rag_proxy_sse_stream_interrupted(client: TestClient) -> None:
    """SSE 上游中断（HTTPError）→ error 事件 + 连接关闭."""
    token = _token(client)
    client.fake.set_stream(  # type: ignore[attr-defined]
        FakeStream(raise_error=httpx.ConnectError("connection lost"))
    )
    resp = client.post(
        "/api/v1/rag-proxy/collections/col-1/query/stream",
        json={"query": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert "event: error" in resp.text
    assert "stream interrupted" in resp.text


# ---------------------------------------------------------------------------
# 健康（AC-144-01-1 透传）
# ---------------------------------------------------------------------------


def test_rag_proxy_health_success(client: TestClient) -> None:
    """health → 200 统一响应（AC-144-01-1 透传）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 0,
                "message": "success",
                "data": {
                    "status": "healthy",
                    "components": {"postgresql": "up", "qdrant": "up"},
                },
            },
        ),
    ])
    resp = client.get(
        "/api/v1/rag-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "healthy"
