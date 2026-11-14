"""测试 v1.4.2 R-378 AC-142-05：memory-proxy 双通道注入 + 统一响应适配 + 401 拦截."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response

import openbase.modules.proxy.memory_proxy as memory_proxy_module
from openbase import init_app
from openbase.modules.auth import UserService
from openbase.modules.proxy.memory_proxy import (
    _adapt_response,
    _build_upstream_headers,
    _effective_subject_id,
    _original_bearer_token,
)
from openbase.settings import Settings

UPSTREAM_BASE = "http://127.0.0.1:8020"


class FakeResponse:
    """模拟 httpx.Response."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    """模拟 httpx.AsyncClient：记录请求并返回预设响应."""

    def __init__(self, *args, **kwargs):
        self.request_calls: list[dict] = []
        self.responses: list[FakeResponse] = []
        self.fail_with: Exception | None = None

    def set_responses(self, responses: list[FakeResponse]) -> None:
        self.responses = responses

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
            # 无更多预设时复用最后一条（列表多参数场景）
            if not self.responses:
                self.responses.append(resp)
            return resp
        return FakeResponse(200, {"results": [], "trace_id": None})


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """构造启用 auth + proxy 的应用，并替换上游 httpx 客户端."""
    settings = Settings()
    for module in ("auth", "proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
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


def test_memory_proxy_no_token_returns_401(client: TestClient) -> None:
    """无认证头 → 401（AC-142-05-4）."""
    resp = client.post("/api/v1/memory-proxy/remember", json={"content": "x"})
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


def test_memory_proxy_remember_success_unified_response(client: TestClient) -> None:
    """认证 remember → 200 统一 {code,message,data,timestamp}（AC-142-05-1/3）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"memory_id": "mem-1", "status": "success", "memory": None}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/remember",
        json={"content": "用户喜欢美式咖啡", "user_id": "1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "data", "timestamp"}
    assert body["code"] == 0
    assert body["message"] == "success"
    assert body["data"]["memory_id"] == "mem-1"

    # 双通道注入：X-API-Key + Bearer JWT + X-Org-ID/X-User-ID + X-Tenant-ID（AC-142-05-2）
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    headers = call["headers"]
    assert headers["X-API-Key"] == "openbase-gw-key-20260830"
    assert headers["Authorization"].startswith("Bearer ")
    # P2-1 T7（OB-8 别名收敛）：org 取 tenant 同源别名（openbase-default 默认链退役）
    assert headers["X-Org-ID"] == "tenant-1"
    assert headers["X-User-ID"] == "1"
    # C1-a 终态（2026-10-08）：JWT 无 tenant_id → 取登记兜底码（原 default，现 tenant-1）
    assert headers["X-Tenant-ID"] == "tenant-1"
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/remember")


def test_memory_proxy_upstream_unreachable_returns_502(client: TestClient) -> None:
    """上游不可达 → SYS_502 统一错误（SYS_UPSTREAM_ERROR）."""
    token = _token(client)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    resp = client.post(
        "/api/v1/memory-proxy/recall",
        json={"query": "q", "user_id": "1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


def test_memory_proxy_detail_not_found_passthrough(client: TestClient) -> None:
    """详情 404 → 错误码透传（AC-142-05-3）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(404, {"detail": {"error": "NOT_FOUND", "message": "Memory x not found"}}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories/not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert "not found" in body["message"]
    assert body["data"] is None


def test_memory_proxy_list_pagination_and_normalize(client: TestClient) -> None:
    """列表：recall 适配 + 分页 + tags/created_at 归一化（AC-142-06-1）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {
            "results": [
                {"memory_id": "m1", "content": "a", "memory_type": "persistent",
                 "metadata": {"tags": ["t1"], "created_at": "2026-08-29T00:00:00Z"}},
                {"memory_id": "m2", "content": "b", "memory_type": "persistent",
                 "metadata": {"tags": ["t2"], "created_at": "2026-08-28T00:00:00Z"}},
                {"memory_id": "m3", "content": "c", "memory_type": "text",
                 "metadata": {"tags": [], "created_at": "2026-08-27T00:00:00Z"}},
            ],
            "trace_id": None,
        }),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 3
    assert data["page"] == 1
    assert len(data["items"]) == 2
    first = data["items"][0]
    assert first["tags"] == ["t1"]
    assert first["created_at"] == "2026-08-29T00:00:00Z"

    # 本地过滤：memory_type
    resp = client.get(
        "/api/v1/memory-proxy/memories?memory_type=persistent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 2


def test_memory_proxy_list_native_pagination(client: TestClient) -> None:
    """R6：上游原生分页可用时直连，total 取自上游（不再 recall 适配）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {
            "code": 0,
            "message": "success",
            "data": {
                "items": [{"id": "m1", "memory_id": "m1", "content": "a", "tags": ["t1"]}],
                "total": 42,
                "offset": 0,
                "limit": 20,
            },
        }),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories?page=1&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 42
    assert data["items"][0]["memory_id"] == "m1"

    calls = client.fake.request_calls  # type: ignore[attr-defined]
    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert "/api/v1/memories?offset=0&limit=20" in calls[0]["url"]


def test_memory_proxy_list_upstream_error_adapted(client: TestClient) -> None:
    """列表上游 4xx → 统一错误响应（不落 items）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(500, {"detail": {"error": "INTERNAL_ERROR", "message": "boom"}}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 500, resp.text
    assert resp.json()["code"] == "INTERNAL_ERROR"


def test_memory_proxy_error_extraction_error_field(client: TestClient) -> None:
    """错误体 {error, message}（详情 404/网关认证失败）→ code 提取 error 字段."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(404, {"error": "NOT_FOUND", "message": "Memory x not found"}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories/not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert body["data"] is None


def test_memory_proxy_rate_limit_retry_after_passthrough(client: TestClient) -> None:
    """限流 429 {error, retry_after} → 透传 retry_after 到 data（指南 12.1）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(429, {"error": "RATE_LIMIT_ERROR",
                           "message": "Rate limit exceeded", "retry_after": 35}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/recall",
        json={"query": "q", "user_id": "1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert body["code"] == "RATE_LIMIT_ERROR"
    assert body["data"] == {"retry_after": 35}


def test_memory_proxy_improve_passthrough(client: TestClient) -> None:
    """improve 优化记忆 → 透传（指南 5.3.4）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"memory_ids": ["mem-new-001"], "status": "success",
                           "improvements": [], "improved_count": 1}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/improve",
        json={"user_id": "1", "operations": [
            {"type": "compress", "query": "项目进度", "similarity_threshold": 0.85}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["improved_count"] == 1
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/improve")


def test_memory_proxy_sessions_and_decay_passthrough(client: TestClient) -> None:
    """会话管理 + 衰减配置 → 透传（指南 5.6/5.7）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"sessions": [], "total": 0}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 0

    client.fake.set_responses([
        FakeResponse(200, {"strategy": "adaptive", "time_decay_factor": 0.95}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/decay/config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["strategy"] == "adaptive"
    call = client.fake.request_calls[1]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/decay/config")


def test_memory_proxy_health_and_monitor_passthrough(client: TestClient) -> None:
    """健康/监控透传（指南 5.2/5.9）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"status": "healthy",
                           "dependencies": {"vector_store": "healthy",
                                            "metadata_store": "healthy",
                                            "session_store": "healthy"}}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "healthy"

    client.fake.set_responses([
        FakeResponse(200, {"range": "24h", "qps": 1.2}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/monitor?range=7d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[1]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/monitor")
    assert call["params"] == {"range": "7d"}


def test_memory_proxy_image_upload_multipart(client: TestClient) -> None:
    """图像记忆上传（multipart 透传，指南 5.4.1）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"id": "img-001", "tenant_id": "default",
                           "storage_path": "memories/img-001.png", "format": "png",
                           "size_bytes": 1024, "created_at": "2026-08-30T10:00:00Z"}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/memories/image",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        data={"metadata": '{"source": "mobile"}'},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == "img-001"

    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/memories/image")
    assert call["method"] == "POST"
    files_kw = call["files"]
    assert files_kw is not None and "file" in files_kw
    filename, content, content_type = files_kw["file"]
    assert filename == "test.png"
    assert content.startswith(b"\x89PNG")
    assert content_type == "image/png"
    # multipart 边界由 httpx 生成，不应保留 Content-Type
    assert "Content-Type" not in call["headers"]


def test_memory_proxy_image_search_json(client: TestClient) -> None:
    """图像文本搜索（JSON 透传，指南 5.4.2）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"results": []}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/memories/image/search",
        json={"query": "风景照片", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/memories/image/search")
    assert call["json"]["query"] == "风景照片"


def test_memory_proxy_audio_transcribe_multipart(client: TestClient) -> None:
    """语音转写（multipart 透传，指南 5.5.1）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"id": "audio-1", "text": "你好", "segments": [],
                           "duration": 1.2, "language": "zh"}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/audio/transcribe",
        files={"file": ("voice.wav", b"RIFF" + b"\x00" * 16, "audio/wav")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["text"] == "你好"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/audio/transcribe")
    assert call["files"]["file"][0] == "voice.wav"


def test_memory_proxy_remember_with_audio_json(client: TestClient) -> None:
    """语音记忆存储（JSON 透传，指南 5.5.2）."""
    token = _token(client)
    client.fake.set_responses([
        FakeResponse(200, {"memory_id": "mem-a1", "status": "success",
                           "memory": None, "created_at": "2026-08-30T10:00:00Z"}),
    ])
    resp = client.post(
        "/api/v1/memory-proxy/memories/remember-with-audio",
        json={"audio_file_id": "audio-1", "text": "会议纪要", "user_id": "1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["memory_id"] == "mem-a1"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/memories/remember-with-audio")


def test_memory_proxy_multipart_no_token_401(client: TestClient) -> None:
    """多模态端点未认证 → 401."""
    resp = client.post(
        "/api/v1/memory-proxy/memories/image",
        files={"file": ("test.png", b"png", "image/png")},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


def test_memory_proxy_graph_overview_passthrough(client: TestClient) -> None:
    """图谱 overview（v7.8.0 P6）→ limit 透传 + 统一信封."""
    token = _token(client)
    payload = {
        "nodes": [{"id": "mem-1", "label": "OpenBase", "node_type": "memory"}],
        "edges": [],
        "stats": {"memory_nodes": 1, "entity_nodes": 0, "edges": 0,
                  "outbox_pending": 0, "outbox_dead": 0},
    }
    client.fake.set_responses([FakeResponse(200, payload)])  # type: ignore[attr-defined]

    resp = client.get(
        "/api/v1/memory-proxy/graph/overview?limit=60",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["stats"]["memory_nodes"] == 1
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == "GET"
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/graph/overview")
    assert call["params"] == {"limit": 60}


def test_memory_proxy_patch_whitelist_only(client: TestClient) -> None:
    """R4：编辑记忆仅透传白名单字段（越权/未知字段丢弃）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"memory_id": "m1", "content": "新内容", "status": "success"}),
    ])
    resp = client.patch(
        "/api/v1/memory-proxy/memories/m1",
        json={
            "content": "新内容",
            "owner": "2",
            "tenant_id": "attacker-tenant",
            "user_id": "999",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["content"] == "新内容"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == "PATCH"
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v1/memories/m1")
    assert call["json"] == {"content": "新内容", "owner": "2"}


def test_memory_proxy_patch_without_editable_field_returns_400(
    client: TestClient,
) -> None:
    """无任何白名单字段 → 400 PARAM_INVALID，不发起上游请求."""
    token = _token(client)
    resp = client.patch(
        "/api/v1/memory-proxy/memories/m1",
        json={"tenant_id": "attacker-tenant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "PARAM_INVALID"
    assert client.fake.request_calls == []  # type: ignore[attr-defined]


def test_memory_proxy_patch_owner_forbidden_passthrough(
    client: TestClient,
) -> None:
    """owner 变更未授权 → 上游 400 语义原样透传."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            400,
            {
                "detail": {
                    "error": "MEMORY_OWNERSHIP_CHANGE_FORBIDDEN",
                    "message": "allow_ownership_change required",
                }
            },
        ),
    ])
    resp = client.patch(
        "/api/v1/memory-proxy/memories/m1",
        json={"owner": "2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "MEMORY_OWNERSHIP_CHANGE_FORBIDDEN"


# ---------------------------------------------------------------------------
# 覆盖率补测：响应适配边角 / 上游不可达（raw 转发）/ 其余透传端点 / 列表回退
# ---------------------------------------------------------------------------


def test_memory_proxy_response_adaptation_edges() -> None:
    """委托主体取值 + 非 JSON 响应体 + detail 字符串与状态码兜底."""
    assert _effective_subject_id({"id": "u1", "delegated": {"subject_id": 7}}) == "7"
    assert _effective_subject_id({"id": "u1"}) == "u1"

    class _RawResponse:
        status_code = 500
        text = "upstream plain text"

        def json(self) -> dict:
            raise ValueError("not json")

    adapted = _adapt_response(_RawResponse())
    assert adapted.status_code == 500
    assert json.loads(adapted.body)["data"] is None

    # detail 为字符串 → 作为 message；code 缺省回落 HTTP 状态码
    adapted = _adapt_response(FakeResponse(400, {"detail": "bad request"}))
    body = json.loads(adapted.body)
    assert body["code"] == 400
    assert body["message"] == "bad request"

    # detail 为对象但仅含 message → code 仍回落状态码
    adapted = _adapt_response(FakeResponse(503, {"detail": {"message": "boom"}}))
    assert json.loads(adapted.body)["code"] == 503


def test_memory_proxy_forget_and_other_passthrough_endpoints(client: TestClient) -> None:
    """forget / 会话详情与终止 / 衰减配置写入 / 召回追踪 / 就绪存活 / 图像嵌入."""
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    def _call(method: str, path: str, **kwargs):
        client.fake.set_responses([FakeResponse(200, {"ok": True})])  # type: ignore[attr-defined]
        return client.request(method, f"/api/v1/memory-proxy{path}", headers=headers, **kwargs)

    assert _call("POST", "/forget", json={"content": "x"}).status_code == 200
    assert _call("GET", "/sessions/s-1").status_code == 200
    assert _call("POST", "/sessions/s-1/terminate").status_code == 200
    assert _call("PUT", "/decay/config", json={"strategy": "adaptive"}).status_code == 200
    assert _call("GET", "/recall/traces/t-1").status_code == 200
    assert _call("GET", "/health/readiness").status_code == 200
    assert _call("GET", "/health/liveness").status_code == 200
    resp = _call(
        "POST",
        "/multimodal/image-embed",
        files={"file": ("img.png", b"\x89PNG", "image/png")},
    )
    assert resp.status_code == 200


def test_memory_proxy_raw_forward_upstream_unreachable(client: TestClient) -> None:
    """列表原生分页路径上游不可达 → 502（raw 转发异常分支）."""
    token = _token(client)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    resp = client.get(
        "/api/v1/memory-proxy/memories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


def test_memory_proxy_detail_tags_normalization_and_bad_body(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """详情：metadata.tags 提升为顶层；响应体非 JSON 时跳过归一化."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"memory_id": "m1", "metadata": {"tags": ["t1"]}}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories/m1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["tags"] == ["t1"]

    async def _fake_forward(*args, **kwargs):
        return Response(content=b"not-json", status_code=200)

    monkeypatch.setattr(memory_proxy_module, "_forward", _fake_forward)
    monkeypatch.setattr(memory_proxy_module, "_build_upstream_headers", lambda *a, **k: {})
    response = asyncio.run(memory_proxy_module.memory_detail("m1", SimpleNamespace(), {"id": "1"}))
    assert response.status_code == 200
    assert response.body == b"not-json"


def test_memory_proxy_list_native_and_recall_fallbacks(client: TestClient) -> None:
    """列表：原生顶层 items / 非对象响应回退 recall / 404 回退 / recall 报错透传."""
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 原生 body.data 为顶层 {items,total}，且 tag 参数透传上游
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"items": [{"memory_id": "m1"}], "total": 1}),
    ])
    resp = client.get("/api/v1/memory-proxy/memories?tag=t1", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 1
    assert "tag=t1" in client.fake.request_calls[-1]["url"]  # type: ignore[attr-defined]

    # 原生返回非对象（列表）→ 回退 recall，并在本地按 tag/memory_type 过滤
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, [{"memory_id": "ignored"}]),
        FakeResponse(200, {"results": [
            {"memory_id": "a", "tags": ["t1"], "memory_type": "text"},
            {"memory_id": "b", "tags": ["t2"], "memory_type": "text"},
        ]}),
    ])
    resp = client.get(
        "/api/v1/memory-proxy/memories?tag=t1&memory_type=text", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["memory_id"] == "a"

    # 原生 404 → 回退 recall；recall 5xx → 原样返回错误信封
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(404, {"error": "NOT_FOUND", "message": "no native"}),
        FakeResponse(500, {"error": "INTERNAL_ERROR", "message": "boom"}),
    ])
    resp = client.get("/api/v1/memory-proxy/memories", headers=headers)
    assert resp.status_code == 500, resp.text
    assert resp.json()["code"] == "INTERNAL_ERROR"


def test_memory_proxy_original_token_and_header_branches() -> None:
    """原 JWT 透传：非 Bearer/空 token 返回 None；匿名与 sk-agent 不构造伪 JWT."""
    assert _original_bearer_token(SimpleNamespace(headers={})) is None
    assert _original_bearer_token(SimpleNamespace(headers={"Authorization": "Basic x"})) is None
    assert _original_bearer_token(SimpleNamespace(headers={"Authorization": "Bearer   "})) is None

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/remember",
        "raw_path": b"/api/v1/remember",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    request = StarletteRequest(scope)
    anonymous = _build_upstream_headers(request, None)
    assert "Authorization" not in anonymous
    assert anonymous["X-API-Key"]

    service_agent = _build_upstream_headers(request, {"id": "1", "auth_method": "sk-agent"})
    assert "Authorization" not in service_agent


def test_memory_proxy_detail_normalization_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """详情归一化：data 非 dict / metadata 缺失 / tags 已存在 → 保持原响应."""
    responses = [
        JSONResponse(status_code=200, content={"code": 0, "data": {"memory_id": "m1"}}),
        JSONResponse(
            status_code=200,
            content={"code": 0, "data": {"memory_id": "m2", "metadata": {}, "tags": ["t"]}},
        ),
    ]

    async def _fake_forward(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(memory_proxy_module, "_forward", _fake_forward)
    monkeypatch.setattr(memory_proxy_module, "_build_upstream_headers", lambda *a, **k: {})

    first = asyncio.run(memory_proxy_module.memory_detail("m1", SimpleNamespace(), {"id": "1"}))
    assert json.loads(first.body)["data"] == {"memory_id": "m1"}
    second = asyncio.run(memory_proxy_module.memory_detail("m2", SimpleNamespace(), {"id": "1"}))
    assert json.loads(second.body)["data"]["tags"] == ["t"]
