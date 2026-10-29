"""测试 v1.4.1 R-367 AC-367-2：/proxy 通道 JWT 优先 + 服务 Key 回退双通道认证（HTTP 层）."""

import asyncio
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.core.db.session import get_engine, init_db
from openbase.core.models import Base
from openbase.modules.auth import UserService
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_proxy_auth.db"


def build_test_app() -> TestClient:
    """构造启用 auth + proxy 的测试应用（服务 Key 落 SQLite，不依赖外部 PG）."""
    settings = Settings()
    for module in ("auth", "proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    UserService.seed_memory_user("admin", "admin123")
    UserService.seed_memory_user("viewer", "viewer123")

    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)

    async def _create_schema() -> None:
        async with get_engine().begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())
    app = init_app(settings)
    return TestClient(app)


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _proxy_auth_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局 engine 单例）."""
    global client
    client = build_test_app()
    yield client
    client = None


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
    """有效服务 Key（scope 匹配）→ 认证通过（非 401/403；上游结果随环境）."""
    admin_token = _token("admin", "admin123")
    key = _create_key(admin_token, "svc-openllm", {"system": ["openllm"], "tenants": ["*"]})

    resp = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": key})
    # 认证已通过（非 401/403）；上游不可达→SYS_502、无 /chat 路由→404、可达→200
    assert resp.status_code not in (401, 403), resp.text
    body = resp.json()
    assert not str(body.get("code", "")).startswith(("AUTH", "PERM"))


def test_proxy_bearer_api_key_authenticates() -> None:
    """Authorization: Bearer <ob_k_...> → 服务 Key 认证通过."""
    admin_token = _token("admin", "admin123")
    key = _create_key(admin_token, "svc-bearer", {"system": ["*"], "tenants": ["*"]})

    resp = client.get("/api/v1/proxy/openllm/chat", headers={"Authorization": f"Bearer {key}"})
    # 认证通过（非 401/403）；上游结果随环境
    assert resp.status_code not in (401, 403), resp.text


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
    # 认证通过（非 401/403）；上游结果随环境
    assert resp.status_code not in (401, 403), resp.text
    body = resp.json()
    assert not str(body.get("code", "")).startswith(("AUTH", "PERM"))


# ---- E0-3（R2）：服务 Key 租户 scope 生效 ----

def _tenant_token(tenant_code: str) -> str:
    """签发携带 tenant_code 的访问 Token（仅用于租户声明，签名有效）."""
    from openbase.modules.auth.jwt import create_access_token

    return create_access_token("admin", username="admin", tenant_code=tenant_code)


def test_tenant_scoped_key_requires_tenant_declaration() -> None:
    """租户受限 Key 未声明租户 → 403（tenant_required，不得静默放行）."""
    admin_token = _token("admin", "admin123")
    key = _create_key(
        admin_token, "svc-site-a", {"system": ["openllm"], "tenants": ["site-a"]}
    )

    resp = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": key})
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERM_API_KEY_SCOPE"
    assert resp.json()["detail"]["reason"] == "tenant_required"


def test_tenant_scoped_key_rejects_cross_tenant() -> None:
    """跨站点：Key scope=site-a，声明 site-b → 403."""
    admin_token = _token("admin", "admin123")
    key = _create_key(
        admin_token, "svc-site-a-x", {"system": ["openllm"], "tenants": ["site-a"]}
    )

    resp = client.get(
        "/api/v1/proxy/openllm/chat",
        headers={"X-API-Key": key, "Authorization": f"Bearer {_tenant_token('site-b')}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERM_API_KEY_SCOPE"


def test_tenant_scoped_key_allows_matching_tenant() -> None:
    """同站点：Key scope=site-a，声明 site-a → 认证通过（非 401/403）."""
    admin_token = _token("admin", "admin123")
    key = _create_key(
        admin_token, "svc-site-a-ok", {"system": ["openllm"], "tenants": ["site-a"]}
    )

    resp = client.get(
        "/api/v1/proxy/openllm/chat",
        headers={"X-API-Key": key, "Authorization": f"Bearer {_tenant_token('site-a')}"},
    )
    assert resp.status_code not in (401, 403), resp.text


def test_untrusted_tenant_header_is_not_trusted() -> None:
    """非受信来源自带 X-Tenant-Id 不采信 → 仍按「未声明租户」拒绝."""
    admin_token = _token("admin", "admin123")
    key = _create_key(
        admin_token, "svc-site-a-hdr", {"system": ["openllm"], "tenants": ["site-a"]}
    )

    resp = client.get(
        "/api/v1/proxy/openllm/chat",
        headers={"X-API-Key": key, "X-Tenant-Id": "site-a"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERM_API_KEY_SCOPE"
    assert resp.json()["detail"]["reason"] == "tenant_required"


# ---- E1-1（R9）：服务 Key 到期与轮换在数据面生效 ----


def test_expired_api_key_rejected_at_proxy() -> None:
    """已过期服务 Key → 401 AUTH_API_KEY_INVALID（到期即失效）."""
    import datetime as dt

    admin_token = _token("admin", "admin123")
    expired_at = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)
    ).isoformat()
    resp = client.post(
        "/api/v1/auth/api-keys",
        json={
            "name": f"svc-expired-{uuid.uuid4().hex[:6]}",
            "scope": {"system": ["*"], "tenants": ["*"]},
            "expires_at": expired_at,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    key = resp.json()["key"]

    call = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": key})
    assert call.status_code == 401, call.text
    assert call.json()["code"] == "AUTH_API_KEY_INVALID"


def test_rotated_key_grace_zero_switches_immediately() -> None:
    """轮换宽限 0：新 Key 可用，旧 Key 立即失效（数据面）。"""
    admin_token = _token("admin", "admin123")
    old_key = _create_key(admin_token, "svc-rotate-old", {"system": ["*"], "tenants": ["*"]})

    list_resp = client.get(
        "/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {admin_token}"}
    )
    old_key_id = next(
        row["id"] for row in list_resp.json() if row["name"].startswith("svc-rotate-old-")
    )
    rotate = client.post(
        f"/api/v1/auth/api-keys/{old_key_id}/rotate",
        json={"grace_hours": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rotate.status_code == 200, rotate.text
    new_key = rotate.json()["key"]

    old_call = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": old_key})
    assert old_call.status_code == 401, old_call.text
    new_call = client.get("/api/v1/proxy/openllm/chat", headers={"X-API-Key": new_key})
    assert new_call.status_code not in (401, 403), new_call.text
