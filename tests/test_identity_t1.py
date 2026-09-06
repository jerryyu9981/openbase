"""U1 T1（RA-01/OB-1）Principal 主体模型与 agent 密钥面 TDD 用例.

RED→GREEN 断言对齐《OpenBase-U1-统一身份收口设计草案》v1.0.0 §11 T1-1~T1-8：
- T1-1  subject_type=agent 行创建成功，credential_type 恒为 api_key、拒绝 password/oidc
- T1-2  明文 sk-agent-* 仅创建响应展示一次，DB 只存 key_hash
- T1-3  agent 密钥鉴权成功（Authorization: Bearer sk-agent-* 放行）
- T1-4  login 端点对 agent 拒绝，且 0 条可达 agent 的密码校验路径
- T1-5  agent 默认 viewer 角色挂载；未显式授权 users:manage → 403；显式提权后可放行
- T1-6  轮换/吊销：吊销后同密钥 401、多密钥并存互不影响
- T1-7  迁移幂等：重放两次无异常、无重复行（W1-4 / WHERE NOT EXISTS）
- T1-8  存量行回填：subject_type=user、status_state 映射正确、token_version=0、tenant_code 回填
"""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.models import Base, Permission, Role, User, role_permission, user_role
from openbase.modules.auth import hash_password
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t1.db"
_MIG_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t1_mig.db"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _rows(sql: str) -> list[tuple]:
    conn = sqlite3.connect(_DB_PATH)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _build_app() -> TestClient:
    """装配启用 identity 模块的应用 + SQLite 库种子（admin/viewer/org_admin 角色与权限矩阵）."""
    settings = Settings()
    for module_name in ("auth", "tenant", "users", "audit", "config", "identity"):
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
            role_org_admin = Role(name="组织管理员", code="org_admin", is_system=True)
            session.add_all([role_admin, role_viewer, role_org_admin])
            await session.flush()
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                status=1,
            )
            session.add(admin)
            await session.flush()
            perms = [
                Permission(code="*", name="全部权限", module="system", type=3),
                Permission(code="users:manage", name="用户管理", module="users", type=3),
                Permission(code="users:view", name="用户查看", module="users", type=3),
                Permission(code="identity:manage", name="主体管理", module="identity", type=3),
                Permission(code="identity:view", name="主体查看", module="identity", type=3),
            ]
            session.add_all(perms)
            await session.flush()
            perm_by_code = {p.code: p for p in perms}
            await session.execute(
                user_role.insert().values(
                    [
                        {"user_id": admin.id, "role_id": role_admin.id},
                    ]
                )
            )
            await session.execute(
                role_permission.insert().values(
                    [
                        {"role_id": role_admin.id, "permission_id": perm_by_code["*"].id},
                        {
                            "role_id": role_org_admin.id,
                            "permission_id": perm_by_code["users:manage"].id,
                        },
                        {
                            "role_id": role_org_admin.id,
                            "permission_id": perm_by_code["users:view"].id,
                        },
                    ]
                )
            )
            await session.commit()

    asyncio.run(_setup())
    app = init_app(settings)
    return TestClient(app)


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _identity_module_app() -> TestClient:
    """模块级应用装配（在模块执行起点构建，避免 import 期污染全局 engine 单例）.

    本仓各测试模块以「模块级 SQLite 文件库 + 全局 engine 单例」运作；若在 import
    期即 init_db 会把全局 engine 指向本模块库文件，影响同进程内先执行的其他模块。
    故延迟到本模块首个用例执行前装配，保证本模块断言与建号/种子数据一致。
    """
    global client
    client = _build_app()
    yield client
    client = None


def _admin_headers() -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_agent(headers: dict[str, str], display_name: str = "Agent Demo") -> dict:
    resp = client.post(
        "/api/v1/identity/agents",
        json={"username": _unique("agent"), "display_name": display_name, "role": "viewer"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "api_key" in body
    return body


# ---- T1-1 ----


def test_t1_1_agent_subject_requires_credential_api_key() -> None:
    """agent 主体行创建成功且 credential_type 恒为 api_key；password/oidc 一律拒绝."""
    admin_headers = _admin_headers()
    created = _create_agent(admin_headers)
    agent_id = created["agent_id"]
    assert created["subject_type"] == "agent"
    assert created["credential_type"] == "api_key"
    assert created["status_state"] == "active"

    row = _rows(f"SELECT subject_type, credential_type, status, status_state, token_version "
                f"FROM users WHERE id = {agent_id}")
    assert len(row) == 1
    subject_type, credential_type, status_int, status_state, token_version = row[0]
    assert subject_type == "agent"
    assert credential_type == "api_key"
    assert status_int == 1
    assert status_state == "active"
    assert token_version == 0

    # 拒绝把 agent 的凭据面写成 password/oidc（identity 建号服务统一强制 api_key）
    from openbase.core.errors import BaseError, ErrorCode
    from openbase.modules.identity.agents import create_agent_subject

    async def _refuse(credential_type: str) -> BaseError:
        try:
            await create_agent_subject(
                get_session_factory()(),
                username=_unique("agent"),
                display_name="Bad Agent",
                credential_type=credential_type,
            )
        except BaseError as exc:
            return exc
        raise AssertionError(f"credential_type={credential_type} should be rejected")

    for bad_type in ("password", "oidc"):
        err = asyncio.run(_refuse(bad_type))
        assert err.status_code == 400
        assert err.code == ErrorCode.PARAM_INVALID


# ---- T1-2 ----


def test_t1_2_agent_key_plaintext_once_and_hash_only_in_db() -> None:
    """创建 agent 返回明文 sk-agent-* 一次；DB 只存 key_hash（sha256）与 key_prefix."""
    admin_headers = _admin_headers()
    created = _create_agent(admin_headers)
    agent_id = created["agent_id"]
    api_key = created["api_key"]
    raw_key = api_key["raw_key"]
    assert raw_key.startswith("sk-agent-")
    assert api_key["key_prefix"] == "sk-agent-"
    assert api_key["status"] == "active"

    rows = _rows(
        f"SELECT key_hash, key_prefix, key_suffix, name FROM agent_api_keys "
        f"WHERE agent_id = {agent_id}"
    )
    assert len(rows) == 1
    key_hash, key_prefix, key_suffix, _name = rows[0]
    assert key_hash != raw_key
    assert key_prefix == "sk-agent-"
    assert key_hash == hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    assert raw_key.endswith(key_suffix or "")

    # 列表不回显明文（raw_key 缺省 None 或键不存在；key_hash 一律不出现在响应）
    list_resp = client.get(f"/api/v1/identity/agents/{agent_id}/keys", headers=admin_headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    assert "key_hash" not in listed[0]
    assert listed[0].get("raw_key") is None
    assert listed[0]["status"] == "active"


# ---- T1-3 ----


def test_t1_3_agent_key_bearer_auth_succeeds() -> None:
    """Authorization: Bearer sk-agent-* 经 agent 校验器放行（/auth/me 可自证）."""
    created = _create_agent(_admin_headers())
    agent_id = created["agent_id"]
    raw_key = created["api_key"]["raw_key"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == agent_id
    assert body["username"] == created["username"]


# ---- T1-4 ----


def test_t1_4_login_rejects_agent_and_no_password_path(monkeypatch) -> None:
    """agent 无人工登录面：login 一律拒绝，且验证 0 条可达 agent 的密码校验路径."""
    created = _create_agent(_admin_headers())

    # 回归：正常用户登录路径不受影响（在打桩前验证）
    admin_login = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert admin_login.status_code == 200

    # 打桩：若 agent 登录到达密码校验则立即失败（0 可达 agent 密码路径断言）
    def _boom(plain: str, hashed: str) -> bool:  # pragma: no cover - 不应被调用
        raise AssertionError("verify_password must not be called for agent login")

    monkeypatch.setattr("openbase.modules.auth.verify_password", _boom)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": created["username"], "password": "whatever"},
    )
    assert resp.status_code in (401, 403)
    # 明文密钥也不可作为凭据登录
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"username": created["username"], "password": created["api_key"]["raw_key"]},
    )
    assert resp2.status_code in (401, 403)


# ---- T1-5 ----


def test_t1_5_agent_default_viewer_and_explicit_escalation() -> None:
    """agent 默认挂 viewer 角色；未显式授权 users:manage 的调用 → 403；提权后放行."""
    admin_headers = _admin_headers()
    created = _create_agent(admin_headers)
    agent_id = created["agent_id"]
    raw_key = created["api_key"]["raw_key"]
    agent_headers = {"Authorization": f"Bearer {raw_key}"}

    roles = _rows(
        f"SELECT r.code FROM roles r JOIN user_role ur ON ur.role_id = r.id "
        f"WHERE ur.user_id = {agent_id}"
    )
    assert "viewer" in {r[0] for r in roles}
    assert created["roles"] == ["viewer"]

    # 默认 viewer 无 users:manage → 越权调用 403
    resp = client.post(
        "/api/v1/users",
        json={
            "username": _unique("u"),
            "password": "pass123",
            "display_name": "越权",
            "role": "viewer",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 403

    # 显式提权（admin 分配 org_admin，其持有 users:manage）后放行
    esc_resp = client.put(
        f"/api/v1/users/{agent_id}/role", json={"role": "org_admin"}, headers=admin_headers
    )
    assert esc_resp.status_code == 200, esc_resp.text
    assert "org_admin" in esc_resp.json()["roles"]
    ok_resp = client.post(
        "/api/v1/users",
        json={
            "username": _unique("u2"),
            "password": "pass123",
            "display_name": "提权后可建",
            "role": "viewer",
        },
        headers=agent_headers,
    )
    assert ok_resp.status_code == 200, ok_resp.text


# ---- T1-6 ----


def test_t1_6_rotate_and_revoke_agent_key() -> None:
    """多密钥并存互不影响；吊销后同密钥 401，其余密钥不受影响."""
    admin_headers = _admin_headers()
    created = _create_agent(admin_headers)
    agent_id = created["agent_id"]
    key1_raw = created["api_key"]["raw_key"]

    key2_resp = client.post(
        f"/api/v1/identity/agents/{agent_id}/keys",
        json={"name": "rotate-second"},
        headers=admin_headers,
    )
    assert key2_resp.status_code == 200, key2_resp.text
    key2_body = key2_resp.json()
    key2_raw = key2_body["raw_key"]
    assert key2_raw.startswith("sk-agent-")
    assert key2_raw != key1_raw

    # 并存互不影响
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {key1_raw}"}).status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {key2_raw}"}).status_code == 200

    # 吊销 key2
    revoke_resp = client.delete(
        f"/api/v1/identity/agents/{agent_id}/keys/{key2_body['id']}", headers=admin_headers
    )
    assert revoke_resp.status_code == 200, revoke_resp.text
    assert revoke_resp.json()["revoked"] is True

    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {key2_raw}"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {key1_raw}"}).status_code == 200

    listed = client.get(f"/api/v1/identity/agents/{agent_id}/keys", headers=admin_headers).json()
    status_by_id = {item["id"]: item["status"] for item in listed}
    assert status_by_id[key2_body["id"]] == "revoked"
    assert status_by_id[created["api_key"]["id"]] == "active"
    assert len(listed) == 2


# ---- T1-7 / T1-8（迁移幂等与存量回填）----

_LEGACY_USERS_DDL = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(128),
    phone VARCHAR(32),
    status INTEGER NOT NULL DEFAULT 1,
    tenant_id INTEGER,
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    deleted_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
"""

_LEGACY_TENANTS_DDL = """
CREATE TABLE tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL UNIQUE,
    code VARCHAR(64) NOT NULL UNIQUE,
    status INTEGER NOT NULL DEFAULT 1,
    isolation_level INTEGER NOT NULL DEFAULT 1,
    quota JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
"""


def _build_legacy_db(path: Path) -> None:
    """构造存量库：users 无 U1 新列（W1-4 迁移前形态）+ 租户与存量用户行."""
    if path.exists():
        path.unlink()

    async def _setup() -> None:
        from sqlalchemy import text

        from openbase.core.db.session import get_engine, init_db

        init_db(f"sqlite+aiosqlite:///{path}", schema=None)
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text(_LEGACY_USERS_DDL))
            await conn.execute(text(_LEGACY_TENANTS_DDL))
            await conn.execute(
                text(
                    "INSERT INTO tenants (id, name, code, status, isolation_level, created_at, updated_at) "
                    "VALUES (1, '存量租户', 'legacy-t1', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO users (id, username, password_hash, display_name, email, status, tenant_id, "
                    "is_deleted, created_at, updated_at) VALUES "
                    "(1, 'legacy-active', 'x', '存量启用', NULL, 1, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                    "(2, 'legacy-disabled', 'x', '存量禁用', NULL, 0, NULL, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
        await engine.dispose()

    asyncio.run(_setup())


def test_t1_7_t1_8_migration_idempotent_and_backfill() -> None:
    """迁移重放两次无异常无重复行；存量行回填 subject_type/status_state/token_version/tenant_code."""
    from openbase.modules.identity.migration import apply_identity_migration

    _build_legacy_db(_MIG_DB_PATH)

    async def _run_migration() -> dict:
        from openbase.core.db.session import init_db as _init_db

        _init_db(f"sqlite+aiosqlite:///{_MIG_DB_PATH}", schema=None)
        engine = get_engine()
        try:
            first = await apply_identity_migration(engine, schema=None)
            second = await apply_identity_migration(engine, schema=None)
            return {"first": first, "second": second}
        finally:
            await engine.dispose()

    result = asyncio.run(_run_migration())

    conn = sqlite3.connect(_MIG_DB_PATH)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        for expected in (
            "subject_type",
            "credential_type",
            "status_state",
            "status_reason",
            "token_version",
            "tenant_code",
            "on_behalf_of",
        ):
            assert expected in cols, f"missing column after migration: {expected}"

        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 2, "migration must not duplicate existing rows"
        assert conn.execute(
            "SELECT COUNT(*) FROM agent_api_keys"
        ).fetchone()[0] == 0

        active = conn.execute(
            "SELECT subject_type, credential_type, status_state, token_version, tenant_code "
            "FROM users WHERE username = 'legacy-active'"
        ).fetchone()
        assert active == ("user", "password", "active", 0, "legacy-t1")

        disabled = conn.execute(
            "SELECT subject_type, credential_type, status_state, token_version, tenant_code "
            "FROM users WHERE username = 'legacy-disabled'"
        ).fetchone()
        assert disabled == ("user", "password", "suspended", 0, None)

        perm_codes = {
            row[0]
            for row in conn.execute("SELECT code FROM permissions WHERE code LIKE 'identity:%'")
        }
        assert {"identity:view", "identity:manage"} <= perm_codes
    finally:
        conn.close()

    # 重放两次：幂等（无异常、行数不变、权限种子不重复）
    assert result["second"]["columns_added"] == []
    assert result["second"]["permissions_seeded"] == 0


def test_t1_7_regression_user_still_loginable_after_migration() -> None:
    """存量用户行迁移后语义不变：可正常登录且 subject_type=user（主键/FK 未动）."""
    from sqlalchemy import text

    _build_legacy_db(_MIG_DB_PATH)

    async def _run() -> None:
        from openbase.core.db.session import get_engine, init_db
        from openbase.modules.identity.migration import apply_identity_migration

        init_db(f"sqlite+aiosqlite:///{_MIG_DB_PATH}", schema=None)
        engine = get_engine()
        try:
            await apply_identity_migration(engine, schema=None)
            async with get_session_factory()() as session:
                await session.execute(
                    text(
                        "UPDATE users SET password_hash = :h WHERE username = 'legacy-active'"
                    ).bindparams(h=hash_password("secret123"))
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_run())

    # 主键/行未重建：既有行 id 仍为 1/2
    conn = sqlite3.connect(_MIG_DB_PATH)
    try:
        ids = sorted(r[0] for r in conn.execute("SELECT id FROM users"))
        assert ids == [1, 2]
    finally:
        conn.close()

    # 语义回归：存量启用用户仍可登录（login 对 user 主体不受影响）
    from fastapi.testclient import TestClient

    settings = Settings()
    for module_name in ("auth", "users", "identity"):
        settings.enable_module(module_name)
    app = init_app(settings)
    with TestClient(app) as tc:
        resp = tc.post(
            "/api/v1/auth/login", json={"username": "legacy-active", "password": "secret123"}
        )
        assert resp.status_code == 200, resp.text
