"""安全专项测试：统一鉴权中间件（SR-001）行为验证."""

from fastapi.testclient import TestClient

from openbase import init_app
from openbase.settings import Settings


def _build(login: bool) -> TestClient:
    settings = Settings()
    for module in ("auth", "tenant", "audit", "config", "org", "dict", "scheduler", "storage", "notify", "mcp", "observability"):
        settings.enable_module(module)
    from openbase.modules.auth import UserService

    UserService.seed_memory_user("admin", "admin123")
    client = TestClient(init_app(settings))
    if login:
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client


def test_anonymous_business_api_401():
    """匿名访问业务接口 → 401 统一错误格式."""
    client = _build(login=False)
    for path in ("/api/v1/dicts", "/api/v1/configs/feature.flag", "/api/v1/org/departments", "/audit/records"):
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} → {resp.status_code}"
        body = resp.json()
        assert body["code"] == "AUTH_401"
        assert "request_id" in body


def test_forged_token_401():
    """伪造 token → 401."""
    client = _build(login=False)
    resp = client.get("/api/v1/dicts", headers={"Authorization": "Bearer fake.token.here"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_401"


def test_authenticated_business_api_200():
    """有效 token 访问业务接口 → 200."""
    client = _build(login=True)
    resp = client.get("/api/v1/dicts")
    assert resp.status_code == 200


def test_public_paths_anonymous_ok():
    """白名单路径匿名可访问."""
    client = _build(login=False)
    assert client.get("/health").status_code == 200
    assert client.get("/observability/status").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_unknown_route_with_token_404():
    """带 token 访问不存在路由 → 404（非 401，中间件放行后由路由层处理）."""
    client = _build(login=True)
    resp = client.get("/api/v1/not-exist")
    assert resp.status_code == 404
