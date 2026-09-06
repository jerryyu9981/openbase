"""U1 T6（L1-2，Q-5=A）retention/purge 策略落地 TDD 用例.

RED→GREEN 断言对齐《OpenBase-U1-统一身份收口设计草案》v1.0.0 §11 T6-1~T6-5 与
§9（Q-5=A：保留+全链阻断；purge 仅显式合规触发、二次授权、影响范围报告确认、全程审计；
无自动限期清除）：

- T6-1  无自动限期清除：全仓静态扫描 0 条「按保留期限自动 purge」路径；无 scheduler 任务；
        purge 执行器仅被显式入口（受权端点/CLI）引用
- T6-2  purge 非 deactivated 主体 → 400 ``BIZ_NOT_PURGEABLE``
- T6-3  purge 无二次授权码/无效/过期 → 403 ``BIZ_PURGE_AUTH_REQUIRED``（含范围报告未确认）
- T6-4  合法 purge（deactivated + 授权码 + 范围报告确认）→ 主体数据物理清除、
        状态=purged（终态台账/状态机矩阵）、audit_logs 留痕；阻断/幂等历史保留
- T6-5  幂等防并发：并发双触发仅一次执行；重复触发对已 purged 主体 400 终态拒绝
- 补充：purge 权限门禁（identity:purge）；agent 主体 purge 联动密钥清除；
       purge 后存量 token 拒绝（行缺失 tombstone 判定）而 OIDC 直签/未知行维持 fail-open。

纪律：先写测试（RED）→ 实现（GREEN）；ruff 0；文件独立进程执行（不复用他模块 app/DB）。
"""

from __future__ import annotations

import asyncio
import io
import json
import sqlite3
import sys
import tempfile
import uuid
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import (
    Base,
    Permission,
    PurgeRecord,
    Role,
    Tenant,
    User,
    role_permission,
    user_role,
)
from openbase.modules.auth import hash_password
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t6.db"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH)


def _rows(sql: str) -> list[tuple]:
    conn = _conn()
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _build_app() -> TestClient:
    """装配启用 identity 模块的应用 + SQLite 库种子（admin/viewer + identity:* 权限）."""
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
        async with get_session_factory()() as session:  # type: ignore[call-arg]
            role_admin = Role(name="系统管理员", code="admin", is_system=True)
            role_viewer = Role(name="只读用户", code="viewer", is_system=True)
            session.add_all([role_admin, role_viewer])
            await session.flush()
            session.add(Tenant(name="Acme", code="acme", status=1, isolation_level=1))
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
                Permission(code="identity:view", name="主体查看", module="identity", type=3),
                Permission(code="identity:manage", name="主体管理", module="identity", type=3),
                Permission(code="identity:lifecycle", name="生命周期管理", module="identity", type=3),
                Permission(code="identity:purge", name="数据清除", module="identity", type=3),
            ]
            session.add_all(perms)
            await session.flush()
            perm_by_code = {p.code: p for p in perms}
            await session.execute(
                user_role.insert().values([{"user_id": admin.id, "role_id": role_admin.id}])
            )
            await session.execute(
                role_permission.insert().values(
                    [{"role_id": role_admin.id, "permission_id": perm_by_code["*"].id}]
                )
            )
            await session.commit()

    asyncio.run(_setup())
    app = init_app(settings)
    return TestClient(app)


client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _identity_t6_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局单例）."""
    global client
    client = _build_app()
    yield client
    client = None


# ---- 数据库辅助（沿用 T1~T5 直插形态） ----

TENANT_SQL = """
INSERT INTO tenants (name, code, status, isolation_level, created_at, updated_at)
VALUES (:name, :code, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""

USER_SQL = """
INSERT INTO users (id, username, password_hash, display_name, status, tenant_id,
                   subject_type, credential_type, status_state, status_reason,
                   token_version, tenant_code, is_deleted, created_at, updated_at)
VALUES (:id, :username, :password_hash, :display_name, :status, :tenant_id,
        :subject_type, :credential_type, :status_state, :status_reason,
        :token_version, :tenant_code, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""

# 显式 id 分配器：purge 物理删除会令 SQLite（无 AUTOINCREMENT）复用被删 max rowid，
# 故本模块所有主体一律取显式递增 id（≥ 1_000_000，避开种子 id），杜绝跨用例串扰。
_ID_ALLOCATOR = {"next": 1_000_000}


def _next_id() -> int:
    allocated = _ID_ALLOCATOR["next"]
    _ID_ALLOCATOR["next"] += 1
    return allocated


def _tenant_id(code: str) -> int | None:
    rows = _rows(f"SELECT id FROM tenants WHERE code = '{code}'")
    return rows[0][0] if rows else None


def _ensure_tenant(code: str) -> int:
    existing = _tenant_id(code)
    if existing is not None:
        return existing
    conn = _conn()
    try:
        conn.execute(TENANT_SQL, {"name": code.title(), "code": code})
        conn.commit()
    finally:
        conn.close()
    return _tenant_id(code)  # type: ignore[return-value]


def _make_user(
    username: str,
    tenant_code: str | None = "acme",
    state: str = "active",
    role: str = "viewer",
) -> int:
    """直插 user 行（显式递增 id + 租户 + 角色绑定），返回 user id."""
    _ensure_tenant(tenant_code) if tenant_code else None
    tenant_id = _tenant_id(tenant_code) if tenant_code else None
    user_id = _next_id()
    conn = _conn()
    try:
        conn.execute(
            USER_SQL,
            {
                "id": user_id,
                "username": username,
                "password_hash": hash_password("secret123"),
                "display_name": username,
                "status": 1 if state == "active" else 0,
                "tenant_id": tenant_id,
                "subject_type": "user",
                "credential_type": "password",
                "status_state": state,
                "status_reason": None,
                "token_version": 0,
                "tenant_code": tenant_code,
            },
        )
        conn.commit()
    finally:
        conn.close()
    _bind_role(user_id, role)
    return user_id


def _make_agent(username: str, tenant_code: str = "acme", state: str = "active") -> int:
    """直插 agent 主体行（显式 id + viewer 角色 + 一条 sk-agent-* 密钥），返回 agent id."""
    _ensure_tenant(tenant_code)
    tenant_id = _tenant_id(tenant_code)
    agent_id = _next_id()
    conn = _conn()
    try:
        conn.execute(
            USER_SQL,
            {
                "id": agent_id,
                "username": username,
                "password_hash": "",
                "display_name": username,
                "status": 1 if state == "active" else 0,
                "tenant_id": tenant_id,
                "subject_type": "agent",
                "credential_type": "api_key",
                "status_state": state,
                "status_reason": None,
                "token_version": 0,
                "tenant_code": tenant_code,
            },
        )
        conn.commit()
        conn.execute(
            "INSERT INTO agent_api_keys (agent_id, key_prefix, key_hash, key_suffix, name, "
            "status, expires_at, last_used_at, created_by, created_at, updated_at) "
            "VALUES (?, 'sk-agent-', ?, ?, 't6-agent-key', 'active', NULL, NULL, NULL, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (agent_id, "h" * 64, "abc123"),
        )
        conn.commit()
    finally:
        conn.close()
    _bind_role(agent_id, "viewer")
    return agent_id


def _bind_role(user_id: int, role: str) -> None:
    role_row = _rows(f"SELECT id FROM roles WHERE code = '{role}'")
    if not role_row:
        return
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO user_role (user_id, role_id) VALUES (?, ?)",
            (user_id, role_row[0][0]),
        )
        conn.commit()
    finally:
        conn.close()


def _username_of(user_id: int) -> str:
    rows = _rows(f"SELECT username FROM users WHERE id = {user_id}")
    assert rows, f"user {user_id} not found"
    return rows[0][0]  # type: ignore[return-value]


def _login(username: str, password: str = "secret123"):
    assert client is not None
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _admin_headers() -> dict[str, str]:
    resp = _login("admin", "admin123")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _lifecycle(subject_type: str, subject_id: int, action: str, reason: str) -> object:
    assert client is not None
    body: dict = {"reason": reason}
    if action == "deactivate":
        body = {"confirm": True, "reason": reason}
    return client.post(
        f"/api/v1/identity/lifecycle/{subject_type}/{subject_id}/{action}",
        json=body,
        headers=_admin_headers(),
    )


def _deactivate(subject_type: str, subject_id: int) -> object:
    return _lifecycle(subject_type, subject_id, "deactivate", f"t6 deactivate {subject_id}")


def _issue_authorization(subject_id: int, subject_type: str = "user", ttl_seconds: int | None = None):
    """服务层签发一次性 purge 授权码（RED 断言前置：CLI/受权管理员路径）."""
    from openbase.modules.identity.purge import (
        PURGE_AUTHORIZATION_TTL_SECONDS,
        IdentityPurgeService,
    )

    async def _do() -> object:
        async with get_session_factory()() as session:
            issued = await IdentityPurgeService.issue_authorization(
                session,
                subject_id=subject_id,
                subject_type=subject_type,
                ttl_seconds=ttl_seconds or PURGE_AUTHORIZATION_TTL_SECONDS,
            )
            await session.commit()
            return issued

    return asyncio.run(_do())


def _purge(subject_id: int, code: str, scope_report_hash: str, subject_type: str = "user"):
    assert client is not None
    return client.post(
        "/api/v1/identity/purge",
        json={
            "subject_type": subject_type,
            "subject_id": subject_id,
            "purge_authorization_code": code,
            "scope_report_hash": scope_report_hash,
        },
        headers=_admin_headers(),
    )


def _count(sql: str) -> int:
    rows = _rows(sql)
    return int(rows[0][0]) if rows else 0


def _audit_purge_rows(subject_id: int) -> list[tuple]:
    """audit_logs 中该主体的 identity.purge 记录（id, action, resource_id, detail）."""
    return _rows(
        "SELECT id, action, resource_id, detail FROM audit_logs "
        f"WHERE action = 'identity.purge' AND resource_id = '{subject_id}' ORDER BY id"
    )


# ---- T6-1 无自动限期清除（静态扫描 0 自动 purge 路径） ----


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1] / "openbase"


def test_t6_1_no_auto_retention_purge_path_static_scan() -> None:
    """全仓静态扫描：0 条「按保留期限自动 purge」标识路径."""
    forbidden_tokens = (
        "auto_purge",
        "purge_expired",
        "purge_stale",
        "purge_retention",
        "retention_days",
        "purge_deactivated_expired",
        "_schedule_purge",
    )
    hits: list[tuple[str, str]] = []
    for path in _source_root().rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            if token in text:
                hits.append((str(path.relative_to(_source_root().parent)), token))
    assert not hits, f"发现自动限期清除代码路径: {hits}"


def test_t6_1_no_scheduler_job_registers_purge() -> None:
    """静态扫描：注册定时任务（APScheduler add_job）的模块不得引用 purge 执行器."""
    hits: list[str] = []
    for path in _source_root().rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "add_job(" in text and "purge" in text.lower():
            hits.append(str(path.relative_to(_source_root().parent)))
    assert not hits, f"scheduler 注册了 purge 任务: {hits}"


def test_t6_1_purge_executor_only_reachable_via_explicit_entries() -> None:
    """静态扫描：purge 执行器仅被显式入口（受权端点/CLI）+ 自身模块引用.

    即不存在 scheduler/后台循环/dispatcher/中间件等自动触发路径。
    """
    allowed_files = {
        Path("openbase") / "modules" / "identity" / "purge.py",
        Path("openbase") / "modules" / "identity" / "__init__.py",
        Path("openbase") / "cli" / "purge.py",
    }
    offenders: list[str] = []
    for path in _source_root().rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "IdentityPurgeService" not in text:
            continue
        relative = path.relative_to(_source_root().parent)
        if relative not in allowed_files:
            offenders.append(str(relative))
    assert not offenders, f"purge 执行器出现在非显式入口文件: {offenders}"


# ---- T6-2 非 deactivated 不可 purge（400 BIZ_NOT_PURGEABLE） ----


def test_t6_2_purge_active_subject_rejected_400() -> None:
    """active 主体 purge → 400 BIZ_NOT_PURGEABLE."""
    user_id = _make_user(_unique("t62a"), state="active")
    resp = _purge(user_id, "purge-fake-code-000000", "0" * 64)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_PURGEABLE.value


def test_t6_2_purge_suspended_subject_rejected_400() -> None:
    """suspended 主体 purge → 400 BIZ_NOT_PURGEABLE."""
    user_id = _make_user(_unique("t62s"), state="suspended")
    resp = _purge(user_id, "purge-fake-code-000000", "0" * 64)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_PURGEABLE.value
    # 数据保留（Q-5=A）：非合规触发不物理清除
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 1


# ---- T6-3 二次授权缺失/无效/过期 → 403 BIZ_PURGE_AUTH_REQUIRED ----


def test_t6_3_purge_without_valid_authorization_rejected_403() -> None:
    """deactivated 主体 + 伪造/缺失授权码 → 403 BIZ_PURGE_AUTH_REQUIRED."""
    user_id = _make_user(_unique("t63a"), state="deactivated")
    resp = _purge(user_id, "purge-fake-code-000000", "0" * 64)
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_PURGE_AUTH_REQUIRED.value
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 1


def test_t6_3_purge_expired_authorization_rejected_403() -> None:
    """授权码过期 → 403 BIZ_PURGE_AUTH_REQUIRED（短 TTL 单次有效）."""
    user_id = _make_user(_unique("t63e"), state="deactivated")
    issued = _issue_authorization(user_id)
    # 直接回拨 expires_at 模拟短 TTL 过期
    conn = _conn()
    try:
        conn.execute(
            "UPDATE purge_authorizations SET expires_at = '2000-01-01 00:00:00' "
            f"WHERE subject_id = {user_id}"
        )
        conn.commit()
    finally:
        conn.close()
    resp = _purge(user_id, issued.authorization_code, issued.scope_report_hash)  # type: ignore[union-attr]
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_PURGE_AUTH_REQUIRED.value
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 1


def test_t6_3_purge_scope_report_not_confirmed_rejected_403() -> None:
    """授权码有效但范围报告确认哈希不符 → 403 BIZ_PURGE_AUTH_REQUIRED."""
    user_id = _make_user(_unique("t63h"), state="deactivated")
    issued = _issue_authorization(user_id)
    resp = _purge(user_id, issued.authorization_code, "f" * 64)  # type: ignore[union-attr]
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_PURGE_AUTH_REQUIRED.value
    # 事务回滚：授权码未被消费（可重试）
    active_codes = _count(
        f"SELECT COUNT(*) FROM purge_authorizations WHERE subject_id = {user_id} "
        "AND status = 'active'"
    )
    assert active_codes == 1
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 1


# ---- T6-4 合法 purge：物理清除 + 终态 + 审计留痕 ----


def test_t6_4_purge_success_physical_clear_and_audit() -> None:
    """deactivated + 授权码 + 范围报告确认 → 物理清除、终态台账、audit_logs 留痕."""
    user_id = _make_user(_unique("t64"), state="deactivated")
    username = _username_of(user_id)
    tenant_id = _tenant_id("acme")
    # 业务 owner 数据（notifications.user_id）一并计入清除范围
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO notifications (user_id, title, content, type, is_read, "
            "tenant_id, created_at, updated_at) "
            "VALUES (?, '合规清除', 'purge-scope', 1, 0, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user_id, tenant_id),
        )
        conn.commit()
    finally:
        conn.close()

    issued = _issue_authorization(user_id)
    assert issued.scope_report["tables"].get("notifications") == 1
    assert issued.scope_report["tables"].get("user_role") == 1

    resp = _purge(user_id, issued.authorization_code, issued.scope_report_hash)  # type: ignore[union-attr]
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["purged"] is True
    assert body["subject_id"] == user_id
    assert body["previous_state"] == "deactivated"
    assert body["status_state"] == "purged"
    assert body["username"] == username
    assert body["scope_report_hash"] == issued.scope_report_hash

    # ① 主体主行物理清除
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 0
    assert _count(f"SELECT COUNT(*) FROM users WHERE username = '{username}'") == 0
    # ② 关联绑定物理清除（user_role / notifications）
    assert _count(f"SELECT COUNT(*) FROM user_role WHERE user_id = {user_id}") == 0
    assert _count(f"SELECT COUNT(*) FROM notifications WHERE user_id = {user_id}") == 0

    # ③ 终态台账（purge_records：状态=purged、previous=deactivated、矩阵复用）
    tombstones = _rows(
        "SELECT status_state, previous_state, subject_type, scope_report_hash "
        f"FROM purge_records WHERE subject_id = {user_id}"
    )
    assert len(tombstones) == 1
    status_state, previous_state, subject_type, record_hash = tombstones[0]
    assert status_state == "purged"
    assert previous_state == "deactivated"
    assert subject_type == "user"
    assert record_hash == issued.scope_report_hash

    # ④ 状态机矩阵复用：deactivated → purged 为合法迁移（T2 前置矩阵已含该边）
    from openbase.modules.identity.state_machine import (
        is_transition_allowed,
        validate_transition,
    )

    assert is_transition_allowed("deactivated", "purged") is True
    validate_transition("deactivated", "purged")  # 不抛错即合法

    # ⑤ audit_logs 留痕（action=identity.purge，detail 含 §9.2 schema 字段）
    audits = _audit_purge_rows(user_id)
    assert len(audits) == 1, audits
    _audit_id, action, resource_id, detail_raw = audits[0]
    assert action == "identity.purge"
    assert resource_id == str(user_id)
    detail = json.loads(detail_raw)
    assert detail["subject"]["subject_id"] == user_id
    assert detail["subject"]["username"] == username
    assert detail["tenant_code"] == "acme"
    assert detail["scope_report_hash"] == issued.scope_report_hash
    assert detail["authorization_ref"]
    assert detail["request_id"]
    assert detail["from"] == "deactivated"
    assert detail["to"] == "purged"


def test_t6_4_purge_keeps_audit_blocks_and_consumption_history() -> None:
    """purge 保留审计/阻断/幂等历史（subject_blocks 持续拒绝，不随主行删除）."""
    user_id = _make_user(_unique("t64b"), state="deactivated")
    # 先造阻断集/幂等历史（模拟 T5 消费端已落表），再 purge
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO subject_blocks (domain, subject_id, subject_type, tenant_code, "
            "state, reason, event_id, blocked_at, created_at, updated_at) "
            "VALUES ('dps', ?, 'user', 'acme', 'blocked', 't6-4 retained', 'e-1', "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user_id,),
        )
        conn.execute(
            "INSERT INTO event_consumptions (event_id, consumer, event_type, subject_id, "
            "subject_type, tenant_code, side_effect, consumed_at, created_at, updated_at) "
            "VALUES ('e-1', 'dps', 'user.deactivated', ?, 'user', 'acme', "
            "'{\"state\": \"blocked\"}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

    issued = _issue_authorization(user_id)
    resp = _purge(user_id, issued.authorization_code, issued.scope_report_hash)  # type: ignore[union-attr]
    assert resp.status_code == 200, resp.text

    # 阻断行保留（指向 subject_id 持续拒绝）；幂等历史保留
    assert _count(f"SELECT COUNT(*) FROM subject_blocks WHERE subject_id = {user_id}") == 1
    assert _count(f"SELECT COUNT(*) FROM event_consumptions WHERE subject_id = {user_id}") == 1
    # 阻断对账仍返回 403 拒绝语义（桩态只读阻断集，不依赖 users 行）
    gate = client.get(  # type: ignore[union-attr]
        f"/api/v1/identity/blocked/{user_id}?domain=dps",
        headers=_admin_headers(),
    )
    assert gate.status_code == 403, gate.text
    assert gate.json()["code"] == ErrorCode.PERM_FORBIDDEN.value


def test_t6_4_purge_requires_identity_purge_permission_403() -> None:
    """purge 端点权限门禁：无 identity:purge → 403 PERM_FORBIDDEN."""
    operator_user = _make_user(_unique("t64perm"), state="active", role="viewer")
    username = _username_of(operator_user)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
    victim = _make_user(_unique("t64permv"), state="deactivated")
    assert client is not None
    denied = client.post(
        "/api/v1/identity/purge",
        json={
            "subject_type": "user",
            "subject_id": victim,
            "purge_authorization_code": "purge-fake-code-000000",
            "scope_report_hash": "0" * 64,
        },
        headers=headers,
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == ErrorCode.PERM_FORBIDDEN.value


def test_t6_4_purge_unknown_subject_404() -> None:
    """未知主体 purge → 404 BIZ_NOT_FOUND（无墓碑 = 从未存在）."""
    resp = _purge(424_242_424, "purge-fake-code-000000", "0" * 64)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == ErrorCode.BIZ_NOT_FOUND.value


def test_t6_4_purge_agent_subject_removes_keys_and_role_bindings() -> None:
    """agent 主体 purge：users 行/agent_api_keys/user_role 物理清除，审计留痕."""
    agent_id = _make_agent(_unique("t64agent"))
    assert _count(f"SELECT COUNT(*) FROM agent_api_keys WHERE agent_id = {agent_id}") == 1
    assert _count(f"SELECT COUNT(*) FROM user_role WHERE user_id = {agent_id}") == 1

    # deactivate 后 purge（subject_type=agent）
    assert _deactivate("agent", agent_id).status_code == 200
    issued = _issue_authorization(agent_id, subject_type="agent")
    resp = _purge(agent_id, issued.authorization_code, issued.scope_report_hash, subject_type="agent")  # type: ignore[union-attr]
    assert resp.status_code == 200, resp.text
    assert resp.json()["status_state"] == "purged"

    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {agent_id}") == 0
    assert _count(f"SELECT COUNT(*) FROM agent_api_keys WHERE agent_id = {agent_id}") == 0
    assert _count(f"SELECT COUNT(*) FROM user_role WHERE user_id = {agent_id}") == 0
    assert len(_audit_purge_rows(agent_id)) == 1


# ---- purge 后 token 语义：行缺失 tombstone 判定 ----


def test_t6_purged_subject_existing_token_rejected() -> None:
    """purge 后存量 token 请求 → 401 AUTH_PRINCIPAL_DISABLED（墓碑判定收口）."""
    user_id = _make_user(_unique("t6tok"), state="active")
    username = _username_of(user_id)
    login_resp = _login(username)
    assert login_resp.status_code == 200, login_resp.text
    access_token = login_resp.json()["access_token"]
    # purge 前置：deactivate 后旧 token 已因状态门禁被拒（T3 语义）
    assert _deactivate("user", user_id).status_code == 200

    issued = _issue_authorization(user_id)
    resp = _purge(user_id, issued.authorization_code, issued.scope_report_hash)  # type: ignore[union-attr]
    assert resp.status_code == 200, resp.text

    # 主体行已物理删除：若沿用 T3 遗留 fail-open，token 将被放行 —— T6 收口为拒绝
    me_resp = client.get(  # type: ignore[union-attr]
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 401, me_resp.text
    assert me_resp.json()["code"] == ErrorCode.AUTH_PRINCIPAL_DISABLED.value
    assert me_resp.json()["detail"]["status_state"] == "purged"


def test_t6_unknown_and_oidc_subjects_remain_failopen() -> None:
    """行缺失但无墓碑（未知 id / OIDC 直签）→ 维持 T3 fail-open（兼容放行）."""
    from openbase.modules.identity import verification as verifier

    # ① sub 非数字（OIDC 直签/外域主体）→ 放行
    result = asyncio.run(verifier.verify_principal(object(), {"sub": "idp-direct-sub-t6"}))
    assert result is None

    # ② 数字 id 无行且无墓碑（从未存在）→ 放行（不误杀降级内存用户）
    async def _missing() -> object:
        async with get_session_factory()() as session:
            return await verifier.verify_principal(session, {"sub": "9876000000", "tvn": 0})

    assert asyncio.run(_missing()) is None

    # ③ 墓碑存在 → verify_principal 抛 AUTH_PRINCIPAL_DISABLED（行缺失判定方案）
    purged_id = _make_user(_unique("t6gone"), state="deactivated")
    issued = _issue_authorization(purged_id)
    resp = _purge(purged_id, issued.authorization_code, issued.scope_report_hash)  # type: ignore[union-attr]
    assert resp.status_code == 200, resp.text

    async def _purged() -> object:
        async with get_session_factory()() as session:
            return await verifier.verify_principal(session, {"sub": str(purged_id), "tvn": 0})

    with pytest.raises(BaseError) as exc_info:
        asyncio.run(_purged())
    assert exc_info.value.code == ErrorCode.AUTH_PRINCIPAL_DISABLED
    assert exc_info.value.detail["status_state"] == "purged"


# ---- T6-5 幂等防并发：并发双触发仅一次执行 ----


def test_t6_5_concurrent_double_trigger_executes_once() -> None:
    """并发双触发（同授权码/同范围确认）→ 仅一次执行：单终态台账 + 单审计 + 主行一次删除."""
    from openbase.modules.identity.purge import IdentityPurgeService

    user_id = _make_user(_unique("t65c"), state="deactivated")
    issued = _issue_authorization(user_id)

    async def _fire(worker_index: int) -> str:
        async with get_session_factory()() as session:
            try:
                await IdentityPurgeService.execute_purge(
                    session,
                    subject_id=user_id,
                    subject_type="user",
                    authorization_code=issued.authorization_code,  # type: ignore[union-attr]
                    scope_report_hash=issued.scope_report_hash,  # type: ignore[union-attr]
                    idempotency_key=f"t6-5-concurrent-{worker_index}",
                )
                await session.commit()
                return "ok"
            except BaseError as exc:
                await session.rollback()
                return exc.code.value
            except Exception:  # noqa: BLE001 - 并发锁/竞争降级为失败计数
                await session.rollback()
                return "error"

    async def _double_trigger() -> list[str]:
        return list(await asyncio.gather(_fire(1), _fire(2)))

    results = asyncio.run(_double_trigger())
    assert results.count("ok") == 1, f"并发双触发应仅一次成功，实际结果: {results}"
    # 主行一次物理清除 + 单终态台账 + 单审计（幂等防并发收敛）
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 0
    assert _count(f"SELECT COUNT(*) FROM purge_records WHERE subject_id = {user_id}") == 1
    assert len(_audit_purge_rows(user_id)) == 1


def test_t6_5_repeated_purge_terminal_refusal_400() -> None:
    """purge 后重复触发 → 400 BIZ_NOT_PURGEABLE 终态拒绝（设计 §9.2 取后者）."""
    user_id = _make_user(_unique("t65r"), state="deactivated")
    issued = _issue_authorization(user_id)
    first = _purge(user_id, issued.authorization_code, issued.scope_report_hash)  # type: ignore[union-attr]
    assert first.status_code == 200, first.text

    # 主体行已删 + 终态台账命中 → 400 终态拒绝（不重复物理删除）
    second = _purge(user_id, "purge-fake-code-000000", "0" * 64)
    assert second.status_code == 400, second.text
    assert second.json()["code"] == ErrorCode.BIZ_NOT_PURGEABLE.value
    assert _count(f"SELECT COUNT(*) FROM purge_records WHERE subject_id = {user_id}") == 1
    assert len(_audit_purge_rows(user_id)) == 1


# ---- CLI 入口（设计草案 §9.2：openbase/cli 子命令 identity purge） ----


def test_t6_cli_parser_wiring() -> None:
    """CLI parser：identity purge-authorize / identity purge 子命令接线正确."""
    from openbase.cli.main import build_parser

    parser = build_parser()
    authorize_args = parser.parse_args(
        ["identity", "purge-authorize", "--subject-id", "1", "--tenant-code", "acme"]
    )
    assert authorize_args.command == "identity"
    assert authorize_args.identity_command == "purge-authorize"
    assert authorize_args.subject_id == 1
    assert authorize_args.subject_type == "user"

    purge_args = parser.parse_args(
        [
            "identity",
            "purge",
            "--subject-id",
            "1",
            "--authorization-code",
            "code-xxxx",
            "--scope-report-hash",
            "h" * 64,
        ]
    )
    assert purge_args.identity_command == "purge"
    assert purge_args.authorization_code == "code-xxxx"


def test_t6_cli_authorize_and_purge_end_to_end(capsys: pytest.CaptureFixture) -> None:
    """CLI 端到端：purge-authorize 签发授权码 → purge 执行（显式合规触发）. """
    from openbase.cli.purge import cmd_purge_authorize, cmd_purge_execute

    user_id = _make_user(_unique("t6cli"), state="deactivated")
    authorize_args = Namespace(
        command="identity",
        identity_command="purge-authorize",
        subject_id=user_id,
        subject_type="user",
        tenant_code="acme",
        ttl_seconds=None,
    )
    assert cmd_purge_authorize(authorize_args) == 0
    authorized = json.loads(capsys.readouterr().out)
    assert authorized["ok"] is True
    code = authorized["purge_authorization_code"]
    scope_hash = authorized["scope_report_hash"]
    assert authorized["scope_report"]["tables"]["user_role"] == 1

    purge_args = Namespace(
        command="identity",
        identity_command="purge",
        subject_id=user_id,
        subject_type="user",
        authorization_code=code,
        scope_report_hash=scope_hash,
        tenant_code="acme",
        idempotency_key=None,
    )
    assert cmd_purge_execute(purge_args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True
    assert result["purged"] is True
    assert result["status_state"] == "purged"
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 0
    assert len(_audit_purge_rows(user_id)) == 1


def test_t6_cli_tenant_guard_prevents_cross_tenant_purge() -> None:
    """CLI 租户护栏：--tenant-code 与主体归属不一致时拒绝（不产生清除副作用）."""
    from openbase.cli.purge import cmd_purge_authorize

    user_id = _make_user(_unique("t6guard"), state="deactivated")
    authorize_args = Namespace(
        command="identity",
        identity_command="purge-authorize",
        subject_id=user_id,
        subject_type="user",
        tenant_code="other-tenant",
        ttl_seconds=None,
    )
    stderr = io.StringIO()
    with redirect_stdout(io.StringIO()):
        old_stderr = sys.stderr
        sys.stderr = stderr
        try:
            rc = cmd_purge_authorize(authorize_args)
        finally:
            sys.stderr = old_stderr
    assert rc == 1
    assert "mismatch" in stderr.getvalue()
    assert _count(f"SELECT COUNT(*) FROM purge_authorizations WHERE subject_id = {user_id}") == 0
    assert _count(f"SELECT COUNT(*) FROM users WHERE id = {user_id}") == 1


def test_t6_purge_record_unique_subject_guard_unit() -> None:
    """purge_records.subject_id 唯一约束：防并发双触发的收敛点（重复插入被拒）."""
    from sqlalchemy.exc import IntegrityError

    async def _seed_and_conflict() -> str:
        async with get_session_factory()() as session:
            session.add(
                PurgeRecord(
                    subject_id=9_999_999_991,
                    subject_type="user",
                    username="dup-guard",
                    status_state="purged",
                    previous_state="deactivated",
                )
            )
            await session.flush()
            await session.commit()
        async with get_session_factory()() as session:
            session.add(
                PurgeRecord(
                    subject_id=9_999_999_991,
                    subject_type="user",
                    username="dup-guard",
                    status_state="purged",
                    previous_state="deactivated",
                )
            )
            try:
                await session.flush()
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return "conflict"
        return "no-conflict"

    assert asyncio.run(_seed_and_conflict()) == "conflict"
    assert _count("SELECT COUNT(*) FROM purge_records WHERE subject_id = 9999999991") == 1
