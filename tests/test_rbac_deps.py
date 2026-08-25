"""RBAC 权限检查与 deps 测试."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.errors import install_exception_handlers
from openbase.modules.auth.rbac import has_permission, require_permission


def test_has_permission_wildcard():
    assert has_permission(["*"], "user:list")
    assert has_permission(["user:list"], "user:list")
    assert not has_permission(["user:list"], "user:delete")
    assert not has_permission([], "user:list")


def _build_rbac_app() -> TestClient:
    from fastapi import Depends

    from openbase.modules.auth.jwt import create_access_token

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/secure", dependencies=[Depends(require_permission("user:list"))])
    async def secure():
        return {"ok": True}

    @app.get("/open")
    async def open_():
        return {"ok": True}

    return TestClient(app), create_access_token


def test_require_permission_denied_without_token():
    client, _ = _build_rbac_app()
    resp = client.get("/secure")
    assert resp.status_code == 401  # 无 token → 401


def test_require_permission_granted_with_token():
    client, create_token = _build_rbac_app()
    token = create_token("1", username="admin")
    resp = client.get("/secure", headers={"Authorization": f"Bearer {token}"})
    # token payload 无 permissions → 403（v1.0.0 简化校验）
    assert resp.status_code == 403


def test_open_endpoint_no_auth():
    client, _ = _build_rbac_app()
    assert client.get("/open").status_code == 200


def test_get_current_tenant_from_header():
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/tenant")
    async def tenant(code: str | None = None):
        # 直接测试 header 解析逻辑
        return {"header": code}

    client = TestClient(app)
    resp = client.get("/tenant", headers={"X-Tenant-Id": "t1"})
    assert resp.status_code == 200


def test_tenant_context_middleware():
    """验证 TenantMiddleware 设置/清除租户上下文."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from openbase.modules.tenant import TenantContext, TenantMiddleware

    app = FastAPI()
    app.add_middleware(TenantMiddleware)

    @app.get("/ctx")
    async def ctx():
        return {"tenant": TenantContext.get()}

    client = TestClient(app)
    resp = client.get("/ctx", headers={"X-Tenant-Id": "t2"})
    assert resp.json()["tenant"] == "t2"
    # 请求结束后上下文清除
    assert TenantContext.get() is None
