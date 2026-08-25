"""observability 与 mcp 模块测试."""

from unittest.mock import patch


def test_init_otel_disabled():
    from openbase.modules.observability import init_otel

    with patch("openbase.modules.observability.logger") as mock_logger:
        init_otel(enabled=False)
        mock_logger.info.assert_called_once_with("otel disabled")


def test_mcp_register_tool_and_list():
    """验证 mcp 工具注册与 list 接口（fastmcp 不可用时降级）. """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openbase.modules.mcp import register_tool, router

    @register_tool("demo_search", "演示检索工具")
    async def demo_search(query: str) -> str:
        return f"result:{query}"

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-API-Key": "dev-mcp-key"}

    resp = client.get("/mcp/tools/list", headers=headers)
    assert resp.status_code == 200
    tools = resp.json()["tools"]
    names = [t["name"] for t in tools]
    assert "demo_search" in names


def test_audit_middleware_request_id():
    """验证 audit 中间件生成 request_id 响应头."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openbase.modules.audit import AuditMiddleware

    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert "X-Request-Id" in resp.headers
    assert resp.headers["X-Request-Id"].startswith("req-")
