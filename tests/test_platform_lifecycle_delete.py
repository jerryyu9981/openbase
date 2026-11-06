"""平台模块生命周期缺口修复用例：字典类型／配置键／agent 主体的删除闭环.

对应《OpenBase-基础设施子系统全生命周期走查报告-v1.0.0》§7：
- GAP-01 字典类型无删除接口 → ``DELETE /api/v1/dicts/{type_code}``（有字典项时 409）
- GAP-02 配置键仅 GET → ``DELETE /api/v1/configs/{key}``（回退默认值；仅默认值 409；未知键 404）
- GAP-03 身份 agent 仅 POST → ``GET /api/v1/identity/agents``（分页列表）＋
  ``DELETE /api/v1/identity/agents/{agent_id}``（软删 + 级联吊销密钥）

闭环口径：创建 → 列表可见 → 删除 → 状态变更/不可再鉴权 → 重复删除幂等或 404。
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.models import Base, Permission, Role, User, role_permission, user_role
from openbase.modules.auth import hash_password
from openbase.modules.config import ConfigStore
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_platform_delete.db"

client: TestClient | None = None


def _unique(prefix: str) -> str:
    """生成唯一标识（避免模块级 SQLite 复用撞键）."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _build_app() -> TestClient:
    """装配启用 dict/config/identity 的应用，并种子 admin 角色与权限矩阵."""
    settings = Settings()
    for module_name in ("auth", "tenant", "users", "audit", "config", "identity", "dict"):
        settings.enable_module(module_name)
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)

    async def _setup() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_session_factory()() as session:
            role_admin = Role(name="系统管理员", code="admin", is_system=True)
            role_viewer = Role(name="只读用户", code="viewer", is_system=True)
            session.add_all([role_admin, role_viewer])
            await session.flush()
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                status=1,
            )
            session.add(admin)
            await session.flush()
            perm = Permission(code="*", name="全部权限", module="system", type=3)
            session.add(perm)
            await session.flush()
            await session.execute(
                user_role.insert().values([{"user_id": admin.id, "role_id": role_admin.id}])
            )
            await session.execute(
                role_permission.insert().values(
                    [{"role_id": role_admin.id, "permission_id": perm.id}]
                )
            )
            await session.commit()

    asyncio.run(_setup())
    return TestClient(init_app(settings))


@pytest.fixture(scope="module", autouse=True)
def _platform_app() -> TestClient:
    """模块级应用装配（延迟到首个用例，避免 import 期污染全局 engine 单例）."""
    global client
    client = _build_app()
    yield client
    client = None


def _admin_headers() -> dict[str, str]:
    """登录 admin 获取 Bearer token."""
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# GAP-01 字典类型删除
# ---------------------------------------------------------------------------


def test_dict_type_delete_rejected_when_items_exist() -> None:
    """存在字典项时删除类型 → 409，且字典项仍在."""
    headers = _admin_headers()
    code = _unique("wt_dict")
    created = client.post("/api/v1/dicts", json={"code": code, "name": "走查字典"}, headers=headers)
    assert created.status_code == 200, created.text
    item = client.post(
        f"/api/v1/dicts/{code}/items",
        json={"label": "甲", "value": "a", "sort_order": 1},
        headers=headers,
    )
    assert item.status_code == 200, item.text
    item_id = item.json()["id"]

    blocked = client.delete(f"/api/v1/dicts/{code}", headers=headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "BIZ_CONFLICT"
    assert blocked.json()["detail"]["item_count"] == 1

    items = client.get(f"/api/v1/dicts/{code}/items", headers=headers)
    assert items.status_code == 200, items.text
    assert [row["id"] for row in items.json()] == [item_id]


def test_dict_type_delete_then_404() -> None:
    """删空字典项后删除类型 → 200；重复删除 → 404."""
    headers = _admin_headers()
    code = _unique("wt_dict")
    client.post("/api/v1/dicts", json={"code": code, "name": "走查字典"}, headers=headers)
    item = client.post(
        f"/api/v1/dicts/{code}/items", json={"label": "乙", "value": "b"}, headers=headers
    )
    assert item.status_code == 200, item.text
    item_id = item.json()["id"]

    removed_item = client.delete(f"/api/v1/dicts/items/{item_id}", headers=headers)
    assert removed_item.status_code == 200, removed_item.text

    removed = client.delete(f"/api/v1/dicts/{code}", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["deleted"] is True

    again = client.delete(f"/api/v1/dicts/{code}", headers=headers)
    assert again.status_code == 404, again.text
    assert again.json()["code"] == "BIZ_404"


# ---------------------------------------------------------------------------
# GAP-02 配置键删除
# ---------------------------------------------------------------------------


def test_config_delete_override_then_404() -> None:
    """删除自定义配置键 → 回退为空；重复删除 → 404."""
    headers = _admin_headers()
    key = _unique("wt.config")
    set_resp = client.post("/api/v1/configs", json={"key": key, "value": "v1"}, headers=headers)
    assert set_resp.status_code == 200, set_resp.text
    assert client.get(f"/api/v1/configs/{key}", headers=headers).json()["value"] == "v1"

    removed = client.delete(f"/api/v1/configs/{key}", headers=headers)
    assert removed.status_code == 200, removed.text
    body = removed.json()
    assert body["deleted"] is True
    assert body["restored_default"] is False

    assert client.get(f"/api/v1/configs/{key}", headers=headers).json()["value"] is None
    again = client.delete(f"/api/v1/configs/{key}", headers=headers)
    assert again.status_code == 404, again.text


def test_config_delete_restores_code_default_and_blocks_default_only() -> None:
    """删除覆盖后回退代码默认值；对仅有默认值的键再删除 → 409."""
    headers = _admin_headers()
    key = _unique("wt.default")
    ConfigStore.set_default(key, 42)
    set_resp = client.post("/api/v1/configs", json={"key": key, "value": 7}, headers=headers)
    assert set_resp.status_code == 200, set_resp.text

    removed = client.delete(f"/api/v1/configs/{key}", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["restored_default"] is True
    assert client.get(f"/api/v1/configs/{key}", headers=headers).json()["value"] == 42

    blocked = client.delete(f"/api/v1/configs/{key}", headers=headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "BIZ_CONFIG_CONFLICT"


# ---------------------------------------------------------------------------
# GAP-03 agent 列表 + 删除
# ---------------------------------------------------------------------------


def _create_agent(headers: dict[str, str]) -> dict:
    """创建 agent 主体（返回 agent_id/username/api_key）."""
    resp = client.post(
        "/api/v1/identity/agents",
        json={"username": _unique("agent"), "display_name": "走查 Agent", "role": "viewer"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["api_key"]["raw_key"].startswith("sk-agent-")
    return body


def test_agent_list_then_delete_and_revoke_keys() -> None:
    """创建 → 列表可见 → 删除（软删＋吊销）→ 密钥失效 → 重复删除幂等."""
    headers = _admin_headers()
    agent = _create_agent(headers)

    listed = client.get("/api/v1/identity/agents?page=1&page_size=100", headers=headers)
    assert listed.status_code == 200, listed.text
    row = [item for item in listed.json() if item["id"] == agent["agent_id"]]
    assert len(row) == 1
    assert row[0]["status"] == 1

    deleted = client.delete(f"/api/v1/identity/agents/{agent['agent_id']}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == 0
    assert deleted.json()["revoked_keys"] >= 1

    after = client.get("/api/v1/identity/agents?page=1&page_size=100", headers=headers).json()
    row = [item for item in after if item["id"] == agent["agent_id"]][0]
    assert row["status"] == 0
    assert row["status_state"] == "suspended"

    key_call = client.get(
        f"/api/v1/identity/agents/{agent['agent_id']}/keys",
        headers={"Authorization": f"Bearer {agent['api_key']['raw_key']}"},
    )
    assert key_call.status_code == 401, key_call.text

    again = client.delete(f"/api/v1/identity/agents/{agent['agent_id']}", headers=headers)
    assert again.status_code == 200, again.text
    assert again.json()["revoked_keys"] == 0


def test_agent_delete_missing_returns_404() -> None:
    """删除不存在的 agent → 404."""
    headers = _admin_headers()
    resp = client.delete("/api/v1/identity/agents/987654321", headers=headers)
    assert resp.status_code == 404, resp.text
