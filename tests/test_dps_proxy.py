"""测试 v1.4.5 R-381 AC-145-03：dps-proxy JWT 门禁 + 身份头注入 + 统一响应 + {detail} 归一化.

P0-3（DPS 端口对齐）：UPSTREAM_BASE 对齐 DPS 源码默认 api_port=8000
（DPS src/config.py：API_PORT 默认 8000；rest_api.app/MCP 部署入口为 8013，
真实部署由 OPENBASE_DPS_UPSTREAM_BASE 环境变量覆盖）。
"""

import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules.auth import UserService
from openbase.modules.auth.jwt import create_access_token
from openbase.settings import Settings

UPSTREAM_BASE = "http://127.0.0.1:8000"


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
    # P0-3：业务转发/透传类用例显式关闭上游健康探活，避免探活请求插入
    # request_calls 序列破坏 URL 顺序断言（探活行为由下方专门用例覆盖）
    settings.dps_health_check_enabled = False
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
    # P2-1 T7（OB-8 别名收敛）：X-Org-ID == X-Tenant-ID（org 不再取 org_id 独立链）
    assert headers["X-Org-ID"] == "tenant-001"
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
    # P2-1 T7（OB-8）：org 恒取 tenant 同源别名（default-org deprecated，不再独立注入）
    assert headers["X-Org-ID"] == "default-tenant"
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


def test_dps_proxy_portrait_update(client: TestClient) -> None:
    """画像更新（PUT）→ 转发 URL/方法/身份头 + C1 契约 body 透传.

    真实契约落地立项方案 Phase C2 T5：OpenLLM ProfileAdapter 写/漂移的持久化落点
    PUT /api/v2/portrait/{person_id}；沿用 mock 上游模式，探活开关按既有约定关闭。
    """
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            200,
            {"code": 200, "message": "success", "data": {"person_id": "p1", "version": 2}},
        ),
    ])
    payload = {
        "person": {"name": "张三"},
        "business": {"attributes": {"industry": "金融"}},
    }
    resp = client.put(
        "/api/v1/dps-proxy/portraits/p1",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["version"] == 2
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == "PUT"
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/p1")
    assert call["json"] == payload
    headers = call["headers"]
    assert headers["X-User-ID"] == "42"
    assert headers["X-Tenant-ID"] == "tenant-001"
    assert headers["X-Org-ID"] == "tenant-001"  # P2-1 T7 别名收敛
    assert headers["X-User-Role"] == "admin"


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


# ---------------------------------------------------------------------------
# P0-3 DPS 上游健康探活（端口对齐守护：settings.dps_upstream_base → 8000）
# ---------------------------------------------------------------------------


def _enable_health_probe(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, interval: float = 3600.0
) -> None:
    """打开探活开关并重置模块级探活状态（隔离用例间污染）.

    interval 取大值：单用例内第二次转发受节流跳过，便于断言"仅首次探活"。
    """
    monkeypatch.setattr(dps_proxy_module, "_last_dps_health_probe_at", None)
    monkeypatch.setattr(dps_proxy_module, "_dps_health_ok", None)
    settings = dps_proxy_module.get_settings()
    settings.dps_health_check_enabled = True
    settings.dps_health_interval = interval


def test_dps_proxy_health_probe_before_first_forward_and_throttled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """首次业务转发前先探活 DPS {base}/health；interval 内再次转发不再重复探活."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"status": "healthy"}),
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": []}}),
    ])
    _enable_health_probe(client, monkeypatch)
    resp = client.get(
        "/api/v1/dps-proxy/portraits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    calls = client.fake.request_calls  # type: ignore[attr-defined]
    assert len(calls) == 2, "首请求应恰有一次探活 + 一次转发"
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == f"{UPSTREAM_BASE}/health"
    assert calls[1]["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")
    # interval（3600s）内第二次转发：不再触发探活
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": [{"person_id": "p2"}]}}),
    ])
    resp2 = client.get(
        "/api/v1/dps-proxy/portraits/p2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200, resp2.text
    calls = client.fake.request_calls  # type: ignore[attr-defined]
    assert len(calls) == 3
    assert calls[2]["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/p2")


def test_dps_proxy_health_probe_connect_error_degrades_then_forward_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """探活连接异常 → WARN 降级提示；转发同样不可达时保持既有 502（AC-145-03-5）."""
    token = _token_with_identity()
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    _enable_health_probe(client, monkeypatch)
    with caplog.at_level(logging.WARNING, logger="openbase.dps_proxy"):
        resp = client.get(
            "/api/v1/dps-proxy/portraits",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"
    calls = client.fake.request_calls  # type: ignore[attr-defined]
    assert calls[0]["url"] == f"{UPSTREAM_BASE}/health"
    assert any(
        "health" in record.getMessage() and "degraded" in record.getMessage()
        for record in caplog.records
    ), "探活连接异常应记录 WARN 降级提示"


def test_dps_proxy_health_probe_recovery_logs_info(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """探活由失败翻转为成功 → INFO 恢复日志（previous_ok=False 分支）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(503, {"detail": "unavailable"}),
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": []}}),
    ])
    _enable_health_probe(client, monkeypatch)
    with caplog.at_level(logging.WARNING, logger="openbase.dps_proxy"):
        resp = client.get(
            "/api/v1/dps-proxy/portraits",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text
    assert dps_proxy_module._dps_health_ok is False
    # 模拟 interval 到期后 DPS 恢复：清除时间戳，下一请求重新探活成功
    monkeypatch.setattr(dps_proxy_module, "_last_dps_health_probe_at", None)
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(200, {"status": "healthy"}),
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": []}}),
    ])
    with caplog.at_level(logging.INFO, logger="openbase.dps_proxy"):
        resp2 = client.get(
            "/api/v1/dps-proxy/portraits",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp2.status_code == 200, resp2.text
    assert dps_proxy_module._dps_health_ok is True
    assert any(
        "recovered" in record.getMessage() for record in caplog.records
    ), "探活恢复应记录 INFO"


def test_dps_proxy_health_probe_non_2xx_degrades_and_keeps_forwarding(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """探活返回非 2xx → WARN 降级提示，转发仍继续（fail-open，不改写既有语义）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(503, {"detail": "unavailable"}),
        FakeResponse(200, {"code": 200, "message": "success", "data": {"items": []}}),
    ])
    _enable_health_probe(client, monkeypatch)
    with caplog.at_level(logging.WARNING, logger="openbase.dps_proxy"):
        resp = client.get(
            "/api/v1/dps-proxy/portraits",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text
    calls = client.fake.request_calls  # type: ignore[attr-defined]
    assert calls[0]["url"] == f"{UPSTREAM_BASE}/health"
    assert calls[1]["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")
    assert any(
        "health" in record.getMessage() and "degraded" in record.getMessage()
        for record in caplog.records
    ), "探活失败应记录 WARN 降级提示"
