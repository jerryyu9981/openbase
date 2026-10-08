"""测试 v1.4.2 R-378 AC-142-05：memory-proxy 双通道注入 + 统一响应适配 + 401 拦截."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.modules.auth import UserService
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
