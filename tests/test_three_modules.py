"""auth/mcp/audit 三模块抽取增强测试."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from openbase.core.errors import install_exception_handlers
from openbase.modules.audit import APICallRecord, AuditMiddleware, AuditService
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.auth.rbac import PermissionStore, require_permission
from openbase.modules.mcp import MCPServer, get_mcp_server, register_tool

# ---- auth PermissionStore（来源: OpenLLM RBACManager） ----


def test_permission_store_role_permissions():
    """角色-权限配置 + 用户权限并集计算."""
    PermissionStore.configure_roles(
        {"admin": ["user:list", "user:create", "*"], "viewer": ["user:list"]}
    )
    PermissionStore.assign_role("1", "viewer")
    PermissionStore.assign_role("1", "admin")
    perms = PermissionStore.permissions_for("1")
    assert "user:list" in perms
    assert "*" in perms  # admin 通配


def test_require_permission_via_store():
    """权限矩阵查询路径：配置角色后放行."""
    from openbase.modules.auth.jwt import create_access_token

    PermissionStore.configure_roles({"editor": ["doc:edit"]})
    PermissionStore.assign_role("42", "editor")

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/doc", dependencies=[Depends(require_permission("doc:edit"))])
    async def doc():
        return {"ok": True}

    client = TestClient(app)
    token = create_access_token("42", username="alice")
    resp = client.get("/doc", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_require_permission_denied_no_role():
    """未分配角色 → 403."""
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/doc", dependencies=[Depends(require_permission("doc:edit"))])
    async def doc():
        return {"ok": True}

    client = TestClient(app)
    token = create_access_token("999", username="bob")
    resp = client.get("/doc", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ---- audit AuditService（来源: OpenLLM AuditMiddleware + DPS audit_log_engine） ----


def test_audit_service_record_and_query():
    AuditService.record_api_call(
        APICallRecord(method="GET", path="/api/v1/users", status_code=200, duration_ms=5, request_id="req-1")
    )
    AuditService.record_api_call(
        APICallRecord(method="POST", path="/api/v1/auth/login", status_code=401, duration_ms=8, request_id="req-2", error="bad credentials")
    )
    records = AuditService.records(limit=10)
    assert len(records) >= 2
    # 最新在前
    assert records[0]["request_id"] == "req-2"
    assert records[1]["path"] == "/api/v1/users"


def test_audit_middleware_records_and_skips_health():
    """审计中间件：记录业务请求、跳过 /health、响应头带 request_id."""
    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id", "").startswith("req-")

    # /health 被排除，不产生审计记录
    client.get("/health")
    records = AuditService.records(limit=100)
    assert all(r["path"] != "/health" for r in records)


# ---- mcp MCPServer（来源: OpenRAG MCPServer） ----


def test_mcp_server_register_and_protocol():
    """MCPServer 工具注册 + initialize/tools/list/tools/call 协议处理."""
    import pytest

    @pytest.mark.asyncio
    async def _run():
        server = MCPServer(name="test-mcp", version="9.9.9")
        await server.start()

        async def add(a: int, b: int) -> int:
            return a + b

        server.register_tool({"name": "add", "description": "加法", "func": add})

        init_resp = await server.handle_request({"method": "initialize"})
        assert init_resp["protocolVersion"] == "2024-11-05"
        assert init_resp["serverInfo"]["name"] == "test-mcp"

        list_resp = await server.handle_request({"method": "tools/list"})
        assert list_resp["tools"][0]["name"] == "add"

        call_resp = await server.handle_request(
            {"method": "tools/call", "params": {"name": "add", "arguments": {"a": 1, "b": 2}}}
        )
        assert call_resp["content"][0]["text"] == "3"
        assert call_resp["isError"] is False

        unknown = await server.handle_request({"method": "unknown/method"})
        assert unknown["code"] == -32601

        await server.stop()
        assert server.is_running is False

    import asyncio

    asyncio.run(_run())


def test_mcp_register_tool_http_layer():
    """HTTP 层：register_tool 后 tools/list 与 tools/call 可用."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openbase.modules.mcp import router

    @register_tool("echo", "回显工具")
    def echo(text: str) -> str:
        return f"echo:{text}"

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-API-Key": "dev-mcp-key"}

    lst = client.get("/mcp/tools/list", headers=headers).json()
    names = [t["name"] for t in lst["tools"]]
    assert "echo" in names

    call = client.post(
        "/mcp/tools/call", json={"name": "echo", "arguments": {"text": "hi"}}, headers=headers
    )
    assert call.status_code == 200
    assert call.json()["content"][0]["text"] == "echo:hi"


def test_mcp_http_layer_rejects_bad_key():
    """HTTP 层：错误 API Key 拒绝（SR-008）."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openbase.core.errors import install_exception_handlers
    from openbase.modules.mcp import router

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/mcp/tools/list", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_401"


def test_mcp_server_unregister():
    server = get_mcp_server()
    server.register_tool({"name": "temp-tool", "description": "临时"})
    assert server.unregister_tool("temp-tool") is True
    assert server.unregister_tool("temp-tool") is False
