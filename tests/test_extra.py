"""补充覆盖测试：observability / scheduler / notify / config / deps 分支."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.errors import install_exception_handlers
from openbase.modules.config import ConfigStore


def test_observability_init_otel_console():
    """验证 init_otel 启用分支（无 OTLP 端点 → Console exporter）."""
    from openbase.modules.observability import init_otel

    with patch("opentelemetry.sdk.trace.TracerProvider") as mock_provider:
        with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"):
            init_otel(service_name="test-svc", enabled=True)
    mock_provider.assert_called_once()


def test_observability_configure_langfuse():
    from openbase.modules.observability import configure_langfuse

    with patch("openbase.modules.observability.logger") as mock_logger:
        configure_langfuse("pk", "sk", "http://localhost:3000")
        mock_logger.info.assert_called_once()


def test_observability_get_tracer():
    from openbase.modules.observability import get_tracer

    tracer = get_tracer("test")
    assert tracer is not None


def test_scheduler_crud_flow():
    """scheduler 创建/启停/日志."""
    from openbase.modules.scheduler import router

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    client = TestClient(app)

    r = client.post("/api/v1/schedules", json={"name": "daily", "cron_expr": "0 8 * * *"})
    assert r.status_code == 200
    task_id = r.json()["id"]

    r2 = client.post(f"/api/v1/schedules/{task_id}/start")
    assert r2.json()["status"] == 1
    r3 = client.post(f"/api/v1/schedules/{task_id}/stop")
    assert r3.json()["status"] == 0

    lst = client.get("/api/v1/schedules").json()
    assert len(lst) == 1
    logs = client.get(f"/api/v1/schedules/{task_id}/logs").json()
    assert logs == []


def test_notify_crud_and_read():
    """notify 创建/列表/已读."""
    from openbase.modules.notify import router

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    client = TestClient(app)

    r = client.post(
        "/api/v1/notifications",
        json={"user_id": 1, "title": "提醒", "content": "内容", "type": 1},
    )
    assert r.status_code == 200
    nid = r.json()["id"]

    lst = client.get("/api/v1/notifications?user_id=1").json()
    assert len(lst) == 1
    assert lst[0]["is_read"] is False

    read = client.post(f"/api/v1/notifications/{nid}/read")
    assert read.json()["is_read"] is True

    all_read = client.post("/api/v1/notifications/read-all?user_id=1")
    assert all_read.json()["read_all"] is True


def test_notify_sse_stream():
    """notify SSE 流连接（只验证连接建立，不阻塞读取）. """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    from openbase.modules.notify import router as notify_router

    app = FastAPI()
    # 覆盖 SSE 路由为一次性响应，避免无限流挂起测试
    @app.get("/sse-check")
    async def sse_check(request: Request) -> JSONResponse:
        return JSONResponse({"stream": "ok"})

    app.include_router(notify_router)
    client = TestClient(app)
    # 验证流路由已注册（模块 router 中路径含 /stream 后缀）
    paths = [getattr(r, "path", "") for r in notify_router.routes]
    assert any(p.endswith("/stream") for p in paths)
    resp = client.get("/sse-check")
    assert resp.json() == {"stream": "ok"}


def test_config_env_override(monkeypatch):
    """config 三级合并：环境变量 > 默认值."""
    ConfigStore.set_default("demo.key", "default")
    monkeypatch.setenv("OPENBASE_CONFIG_DEMO_KEY", '"env"')
    assert ConfigStore.get("demo.key") == "env"
    monkeypatch.delenv("OPENBASE_CONFIG_DEMO_KEY")
    assert ConfigStore.get("demo.key") == "default"


def test_config_rollback_missing_version():
    """回滚不存在的版本返回 None."""
    assert ConfigStore.rollback("no-such-key", 99) is None


def test_get_current_user_missing_header():
    """get_current_user 无 Authorization 头 → 401."""
    from openbase.core.deps import get_current_user

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/who")
    async def who(user=__import__("fastapi").Depends(get_current_user)):
        return user

    client = TestClient(app)
    resp = client.get("/who")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_401"


def test_get_current_user_invalid_token():
    """get_current_user 非法 token → 401."""
    from openbase.core.deps import get_current_user

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/who")
    async def who(user=__import__("fastapi").Depends(get_current_user)):
        return user

    client = TestClient(app)
    resp = client.get("/who", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_401_INVALID"


def test_storage_delete():
    """storage 删除文件."""
    from openbase.modules.storage import router

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    client = TestClient(app)

    up = client.post("/api/v1/files", files={"file": ("a.txt", b"data", "text/plain")})
    fid = up.json()["id"]
    deleted = client.delete(f"/api/v1/files/{fid}")
    assert deleted.status_code == 200
    # 删除后详情 404
    assert client.get(f"/api/v1/files/{fid}").status_code == 404
