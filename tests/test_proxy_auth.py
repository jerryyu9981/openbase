"""测试 v1.4.1 R-367 AC-367-2：/proxy 通道 JWT 优先 + 服务 Key 回退双通道认证（HTTP 层）."""

import uuid

from fastapi.testclient import TestClient

from openbase import init_app
from openbase.modules.auth import UserService
from openbase.settings import Settings


def build_test_app() -> TestClient:
    """构造启用 auth + proxy 的测试应用."""
    settings = Settings()
    for module in ("auth", "proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    UserService.seed_memory_user("admin", "admin123")
    UserService.seed_memory_user("viewer", "viewer123")
    app = init_app(settings)
    return TestClient(app)


client = build_test_app()


def _token(username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _create_key(token: str, name: str, scope: dict) -> str:
    resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": f"{name}-{uuid.uuid4().hex[:6]}", "scope": scope},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["key"]


def test_proxy_no_credentials_returns_401() -> None:
    """无任何认证头 → 401（AUTH_401）."""
    resp = client.get("/api/v1/proxy/openllm/chat")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


def test_proxy_invalid_api_key_returns_401() -> None:
    """无效服务 Key → 401（AUTH_API_KEY_INVALID）."""
    resp = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": "ob_k_invalid"})
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_API_KEY_INVALID"


def test_proxy_valid_api_key_authenticates() -> None:
    """有效服务 Key（scope 匹配）→ 认证通过（上游不可达返回统一 502 包装）."""
    admin_token = _token("admin", "admin123")
    key = _create_key(admin_token, "svc-openllm", {"system": ["openllm"], "tenants": ["*"]})

    resp = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": key})
    # 认证已通过；上游 127.0.0.1:8001 未启动 → SYS_502 统一包装（非 401/403）
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


def test_proxy_bearer_api_key_authenticates() -> None:
    """Authorization: Bearer <ob_k_...> → 服务 Key 认证通过."""
    admin_token = _token("admin", "admin123")
    key = _create_key(admin_token, "svc-bearer", {"system": ["*"], "tenants": ["*"]})

    resp = client.get("/api/v1/proxy/openllm/chat", headers={"Authorization": f"Bearer {key}"})
    assert resp.status_code == 502, resp.text  # 认证通过，上游不可达


def test_proxy_api_key_scope_mismatch_returns_403() -> None:
    """越 scope 服务 Key → 403（PERM_API_KEY_SCOPE）."""
    admin_token = _token("admin", "admin123")
    key = _create_key(admin_token, "svc-llm-only", {"system": ["openllm"], "tenants": ["*"]})

    # 请求路径指向 openrag（越 system scope）
    resp = client.get("/api/v1/proxy/openrag/search", headers={"X-API-Key": key})
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERM_API_KEY_SCOPE"


def test_proxy_jwt_authenticates() -> None:
    """JWT 通道 → 认证通过（上游不可达返回 502 包装）."""
    admin_token = _token("admin", "admin123")
    resp = client.get("/api/v1/proxy/openllm/chat", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"
