"""测试 v1.4.1 服务 Key 签发 API 层（R-367 补充：POST/GET/DELETE /api/v1/auth/api-keys）."""

import asyncio
import json
import sqlite3
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


# ---- E0-4（R4/P0-4）：服务 Key 签发/吊销审计落库 ----


def _audit_rows(key_id: str) -> list[tuple]:
    conn = sqlite3.connect(_DB_PATH)
    try:
        return conn.execute(
            "SELECT action, resource, resource_id, request_id, detail FROM audit_logs "
            "WHERE resource = 'service_api_keys' AND resource_id = ?",
            (key_id,),
        ).fetchall()
    finally:
        conn.close()


def test_api_key_lifecycle_writes_audit_without_plaintext() -> None:
    """签发与吊销均写 AuditLog（key_id/name/scope/操作人/request_id；不含明文）。"""
    admin_token = _token("admin", "admin123")
    name = _unique("svc-audit")

    create_resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": name, "scope": {"system": ["openllm"], "tenants": ["*"]}},
        headers=_auth(admin_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    body = create_resp.json()
    key_id = body["id"]
    raw_key = body["key"]

    rows = _audit_rows(key_id)
    issue_rows = [row for row in rows if row[0] == "auth.service_key.issue"]
    assert len(issue_rows) == 1, rows
    _action, resource, resource_id, request_id, detail = issue_rows[0]
    assert resource == "service_api_keys"
    assert str(resource_id) == key_id
    assert request_id
    assert raw_key not in (detail or "")
    detail_obj = json.loads(detail)
    assert detail_obj["key_id"] == key_id
    assert detail_obj["name"] == name
    assert detail_obj["scope"]["system"] == ["openllm"]

    revoke_resp = client.delete(
        f"/api/v1/auth/api-keys/by-id/{key_id}", headers=_auth(admin_token)
    )
    assert revoke_resp.status_code == 200, revoke_resp.text

    rows = _audit_rows(key_id)
    revoke_rows = [row for row in rows if row[0] == "auth.service_key.revoke"]
    assert len(revoke_rows) == 1, rows
    assert raw_key not in (revoke_rows[0][4] or "")


# ---- E1-1（R9）：服务 Key 默认有效期与轮换 ----


def _list_records(token: str) -> list[dict]:
    resp = client.get("/api/v1/auth/api-keys", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_e1_1_api_key_default_expiry_and_rotate() -> None:
    """默认 90 天到期；轮换签发新 Key（rotated_from），旧 Key 宽限期后自动失效."""
    import time

    admin_token = _token("admin", "admin123")
    create = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc-rot"), "scope": {"system": ["*"], "tenants": ["*"]}},
        headers=_auth(admin_token),
    )
    assert create.status_code == 200, create.text
    body = create.json()
    old_key_id = body["id"]
    old_raw_key = body["key"]
    assert body["expires_at"] is not None
    assert body["expires_at"] > time.time() + 80 * 24 * 3600  # ≈90 天

    rotate = client.post(
        f"/api/v1/auth/api-keys/{old_key_id}/rotate",
        json={"grace_hours": 0},
        headers=_auth(admin_token),
    )
    assert rotate.status_code == 200, rotate.text
    rotated = rotate.json()
    assert rotated["id"] != old_key_id
    assert rotated["rotated_from"] == old_key_id
    assert rotated["key"].startswith("ob_k_")
    assert rotated["key"] != old_raw_key

    records = {row["id"]: row for row in _list_records(admin_token)}
    assert records[old_key_id]["expires_at"] <= time.time()  # 宽限 0 → 立即过期
    assert records[rotated["id"]]["revoked"] is False

    # 轮换审计留痕
    actions = {row[0] for row in _audit_rows(old_key_id)}
    assert "auth.service_key.rotate" in actions


def test_e1_1_rotate_unknown_key_404() -> None:
    """轮换不存在的 Key → 404."""
    admin_token = _token("admin", "admin123")
    resp = client.post(
        "/api/v1/auth/api-keys/not-exist-key/rotate",
        json={},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "BIZ_404"


# ---- E1-4（R13/R14/R15）：吊销不回显明文 / 未命中 404 / 掩码键 ----


def test_e1_4_revoke_by_raw_no_plaintext_echo_and_404() -> None:
    """按明文吊销不再回显明文（仅稳定 id）；未命中 → 404."""
    admin_token = _token("admin", "admin123")
    create = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc-raw"), "scope": {"system": ["*"], "tenants": ["*"]}},
        headers=_auth(admin_token),
    )
    assert create.status_code == 200, create.text
    body = create.json()
    raw_key = body["key"]
    key_id = body["id"]

    revoke = client.delete(f"/api/v1/auth/api-keys/{raw_key}", headers=_auth(admin_token))
    assert revoke.status_code == 200, revoke.text
    payload = revoke.json()
    assert payload == {"revoked": key_id}
    assert raw_key not in json.dumps(payload)

    missing = client.delete(
        f"/api/v1/auth/api-keys/{_unique('ob_k_unknown')}", headers=_auth(admin_token)
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "BIZ_404"


# ---- E1-2（R10）：Key 事件写入 outbox ----

def test_e1_2_service_key_events_enqueued() -> None:
    """签发/吊销服务 Key 同事务写 outbox 事件（service_key.issued/revoked）。"""
    admin_token = _token("admin", "admin123")
    create = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc-evt"), "scope": {"system": ["*"], "tenants": ["*"]}},
        headers=_auth(admin_token),
    )
    assert create.status_code == 200, create.text
    key_id = create.json()["id"]

    conn = sqlite3.connect(_DB_PATH)
    try:
        issued = conn.execute(
            "SELECT COUNT(*) FROM outbox_events WHERE event_type = 'service_key.issued' "
            "AND payload LIKE ?",
            (f"%{key_id}%",),
        ).fetchone()[0]
        assert issued >= 1

        client.delete(f"/api/v1/auth/api-keys/by-id/{key_id}", headers=_auth(admin_token))
        revoked = conn.execute(
            "SELECT COUNT(*) FROM outbox_events WHERE event_type = 'service_key.revoked' "
            "AND payload LIKE ?",
            (f"%{key_id}%",),
        ).fetchone()[0]
        assert revoked >= 1
    finally:
        conn.close()


def test_e1_4_service_key_list_tenant_filter() -> None:
    """列表按归属租户过滤：单租户 scope 的 Key 归属该租户，平台级 Key 不泄漏给租户视角."""
    admin_token = _token("admin", "admin123")
    tenant_key = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc-site"), "scope": {"system": ["*"], "tenants": ["site-a"]}},
        headers=_auth(admin_token),
    ).json()
    platform_key = client.post(
        "/api/v1/auth/api-keys",
        json={"name": _unique("svc-platform"), "scope": {"system": ["*"], "tenants": ["*"]}},
        headers=_auth(admin_token),
    ).json()

    records = {row["id"]: row for row in _list_records(admin_token)}
    assert records[tenant_key["id"]]["tenant_code"] == "site-a"
    assert records[platform_key["id"]]["tenant_code"] is None

    # 租户调用方（权限点透传 + tenant_code）只能看到归属本租户的 Key
    from openbase.modules.auth.jwt import create_access_token

    tenant_token = create_access_token(
        "idp-api-key-viewer",
        username="tenant-key-viewer",
        tenant_code="site-a",
        extra={"permissions": ["auth:api-keys:view"], "role": "viewer"},
    )
    tenant_view = client.get("/api/v1/auth/api-keys", headers=_auth(tenant_token))
    assert tenant_view.status_code == 200, tenant_view.text
    visible_ids = {row["id"] for row in tenant_view.json()}
    assert tenant_key["id"] in visible_ids
    assert platform_key["id"] not in visible_ids
