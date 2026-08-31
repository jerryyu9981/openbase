"""测试 v1.4.5 R-381 AC-145-03：dps-proxy JWT 门禁 + 身份头注入 + 统一响应 + {detail} 归一化."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.modules.auth import UserService
from openbase.modules.auth.jwt import create_access_token
from openbase.settings import Settings

UPSTREAM_BASE = "http://127.0.0.1:8030"


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
            if not self.responses:
                self.responses.append(resp)
            return resp
        return FakeResponse(200, {"code": 200, "message": "success", "data": {"items": []}})


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """构造启用 auth + dps_proxy 的应用，替换上游 httpx 客户端并覆盖 dps 配置.

    注意：dps_proxy 模块内部经 get_settings() 读取全局单例，须 monkeypatch
    openbase.settings._settings 为测试实例（否则 default 兜底值不生效）。
    """
    settings = Settings()
    for module in ("auth", "proxy", "dps_proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    settings.dps_upstream_base = UPSTREAM_BASE
    settings.dps_default_org_id = "default-org"
    settings.dps_default_tenant_id = "default-tenant"
    # 替换 settings 模块全局单例（importlib 获取真实模块，避免 openbase 包 settings 属性干扰）
    import importlib

    settings_module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(settings_module, "_settings", settings)
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    fake = FakeAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: fake)
    tc = TestClient(app)
    tc.fake = fake  # type: ignore[attr-defined]
    return tc


def _token(client: TestClient) -> str:
    """登录获取 token（JWT 含 tenant_id/org_id/role）."""
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _token_with_identity() -> str:
    """直接签发带完整身份的 JWT（sub/tenant_id/org_id/role）."""
    return create_access_token(
        "42",
        username="identity-user",
        tenant_id="tenant-001",
        extra={"org_id": "org-001", "role": "admin"},
    )


# ---------------------------------------------------------------------------
# 认证门禁（AC-145-02-1 / AC-145-03-4）
# ---------------------------------------------------------------------------


def test_dps_proxy_no_token_returns_401(client: TestClient) -> None:
    """无认证头 → 401（AC-145-02-1）."""
    resp = client.get("/api/v1/dps-proxy/portraits")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


def test_dps_proxy_invalid_token_returns_401(client: TestClient) -> None:
    """无效 token → 401."""
    resp = client.get(
        "/api/v1/dps-proxy/portraits",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# 身份头注入（AC-145-02-2）
# ---------------------------------------------------------------------------


def test_dps_proxy_identity_headers_injected(client: TestClient) -> None:
    """认证请求 → 四头注入（X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": [], "total": 0}}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    headers = call["headers"]
    assert headers["X-User-ID"] == "42"
    assert headers["X-Tenant-ID"] == "tenant-001"
    assert headers["X-Org-ID"] == "org-001"
    assert headers["X-User-Role"] == "admin"
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")


def test_dps_proxy_identity_defaults_when_missing(client: TestClient) -> None:
    """JWT 缺 org_id/tenant_id → default 兜底 + 注入."""
    token = _token(client)  # 登录签发，含 org_id=tenant_id；构造缺省场景用纯 sub token
    token = create_access_token("9", username="no-org-user")  # 无 tenant_id/org_id/role
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": []}}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    headers = call["headers"]
    assert headers["X-User-ID"] == "9"
    assert headers["X-Tenant-ID"] == "default-tenant"  # default 兜底
    assert headers["X-Org-ID"] == "default-org"  # default 兜底
    assert headers["X-User-Role"] == "user"  # role 缺省


# ---------------------------------------------------------------------------
# 画像族（AC-145-03-1/2）
# ---------------------------------------------------------------------------


def test_dps_proxy_portraits_list_success(client: TestClient) -> None:
    """画像列表 → 200 统一响应 + 分页参数透传（AC-145-03-1/2）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 200,
                "message": "success",
                "data": {
                    "items": [{"person_id": "p1", "name": "张三", "risk_level": "low", "updated_at": "2026-08-31T00:00:00"}],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                },
            },
        ),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits?page=1&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "data", "timestamp"}
    assert body["code"] == 0
    assert body["data"]["items"][0]["name"] == "张三"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")
    assert call["params"] == {"page": 1, "page_size": 20}


def test_dps_proxy_portrait_detail_success(client: TestClient) -> None:
    """画像详情 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "code": 200,
                "message": "success",
                "data": {"person_id": "p1", "name": "张三", "dimensions": {"basic": {"age": 30}}, "tags": ["vip"]},
            },
        ),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits/p1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dimensions"]["basic"]["age"] == 30
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/p1")


def test_dps_proxy_portrait_calculate(client: TestClient) -> None:
    """画像计算 → 统一响应 + body 透传."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {"code": 200, "message": "success", "data": {"task_id": "t1", "status": "completed"}},
        ),
    ])
    payload = {"person_id": "p1", "data": {"source": "e2e"}}
    resp = client.post(
        "/api/v1/dps-proxy/portraits/calculate",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["task_id"] == "t1"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/calculate")
    assert call["json"] == payload


# ---------------------------------------------------------------------------
# 标签/报表/批量/审计（AC-145-03-1）
# ---------------------------------------------------------------------------


def test_dps_proxy_tags_categories(client: TestClient) -> None:
    """标签分类 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": [{"id": "c1", "name": "消费"}]}}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/tags/categories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"][0]["name"] == "消费"


def test_dps_proxy_reports_overview(client: TestClient) -> None:
    """报表概览 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"total": 100, "risk_high": 5}}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/reports/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 100


def test_dps_proxy_batch_task_status(client: TestClient) -> None:
    """批量任务状态 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"task_id": "t1", "status": "completed", "total": 1000}}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/batch/tasks/t1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "completed"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/batch/import/t1/status")


def test_dps_proxy_audit_logs(client: TestClient) -> None:
    """审计日志 → 统一响应."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": [{"log_id": "l1", "action": "login"}]}}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"][0]["action"] == "login"


# ---------------------------------------------------------------------------
# 错误归一化（AC-145-03-3）
# ---------------------------------------------------------------------------


def test_dps_proxy_detail_error_normalization(client: TestClient) -> None:
    """上游 {detail} 字符串 → 归一化：code=HTTP 状态码，message=detail."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(404, {"detail": "画像不存在: p404"}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits/p404",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["code"] == 404
    assert "画像不存在" in body["message"]


def test_dps_proxy_gateway_error_passthrough(client: TestClient) -> None:
    """上游网关错误体 {code, message} → code/message 透传."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(500, {"code": 5000, "message": "internal error", "data": None}),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/portraits/p-x",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 500, resp.text
    body = resp.json()
    assert body["code"] == 5000
    assert body["message"] == "internal error"


def test_dps_proxy_upstream_unreachable_returns_502(client: TestClient) -> None:
    """上游不可达 → 502 级错误（SYS_UPSTREAM_ERROR，AC-145-03-5）."""
    token = _token(client)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    resp = client.get(
        "/api/v1/dps-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


# ---------------------------------------------------------------------------
# 健康（AC-145-01-1 透传）
# ---------------------------------------------------------------------------


def test_dps_proxy_health_success(client: TestClient) -> None:
    """health → 200 统一响应（DPS /health/liveness 透传）."""
    token = _token(client)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {
                "status": "healthy",
                "checks": {"database": "up"},
                "version": "2.7.1",
                "timestamp": "2026-08-31T00:00:00Z",
            },
        ),
    ])
    resp = client.get(
        "/api/v1/dps-proxy/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "healthy"
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/health/liveness")
