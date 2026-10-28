"""测试 v1.4.1 服务 Key 签发 API 层（R-367 补充：POST/GET/DELETE /api/v1/auth/api-keys）."""

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

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_api_keys_api.db"


def build_test_app() -> TestClient:
    """构造启用核心模块的测试应用（服务 Key 落 SQLite，不依赖外部 PG）."""
    settings = Settings()
    for module in ("auth", "tenant", "audit", "config", "org", "dict", "storage", "notify"):
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
def _api_keys_api_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局 engine 单例）."""
    global client
    client = build_test_app()
    yield client
    client = None


def _token(username: str, password: str) -> str:
    """登录获取 access token."""
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _unique(name: str) -> str:
    return f"{name}-{uuid.uuid4().hex[:6]}"


def test_api_key_create_requires_auth() -> None:
    """未登录创建服务 Key → 401."""
    resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc"), "scope": {"system": ["openllm"], "tenants": ["*"]}},
    )
    assert resp.status_code == 401


def test_api_key_create_list_and_revoke() -> None:
    """创建（返回明文 ob_k_ 前缀）→ 列表可见 → 吊销后 revoked=True."""
    admin_token = _token("admin", "admin123")
    name = _unique("svc-b")

    create_resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": name, "scope": {"system": ["openllm"], "tenants": ["*"]}},
        headers=_auth(admin_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    body = create_resp.json()
    assert body["key"].startswith("ob_k_")
    assert body["name"] == name
    assert body["scope"]["system"] == ["openllm"]

    list_resp = client.get("/api/v1/auth/api-keys", headers=_auth(admin_token))
    assert list_resp.status_code == 200
    records = list_resp.json()
    assert any(record["name"] == name for record in records)
    assert all("key" not in record or record["key"] is None for record in records)

    revoke_resp = client.delete(f"/api/v1/auth/api-keys/{body['key']}", headers=_auth(admin_token))
    assert revoke_resp.status_code == 200

    after = client.get("/api/v1/auth/api-keys", headers=_auth(admin_token)).json()
    record = next(item for item in after if item["name"] == name)
    assert record["revoked"] is True


def test_api_key_permission_required() -> None:
    """普通用户（viewer）创建服务 Key → 403."""
    viewer_token = _token("viewer", "viewer123")
    resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc-d"), "scope": {"system": ["*"], "tenants": ["*"]}},
        headers=_auth(viewer_token),
    )
    assert resp.status_code == 403


def test_api_key_list_requires_auth() -> None:
    """未登录列表 → 401."""
    assert client.get("/api/v1/auth/api-keys").status_code == 401
