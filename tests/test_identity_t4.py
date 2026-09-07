"""U1 T4（K08 / OB-11）on_behalf_of 委托不跨界 TDD 用例.

RED→GREEN 断言对齐《OpenBase-U1-统一身份收口设计草案》v1.0.0 §11 T4-1~T4-7
（R2 边界：委托头完整唯一签发收口留 P2-1/S1b，本任务完成 claim 结构与域校验骨架）：
- T4-1  同域委托（agent 域 A 代 user 域 A）签发成功；claims 含 on_behalf_of
- T4-2  跨域委托（域 A→域 B）签发 403 `PERM_DELEGATION_CROSS_TENANT`
- T4-3  每请求重校验：token 中 on_behalf_of 域被替换后请求 → 403
- T4-4  三级嵌套链任意一跳跨界 → 403；全同域 → 200
- T4-5  user 挂 on_behalf_of → 403；代理目标非 active → 403；代理角色越权 → 403
- T4-6  审计 detail 记两层（principal+delegated）
- T4-7  dps/memory/llm proxy 委托请求出站头取委托域值（X-Tenant-ID/X-Org-ID=
        委托 tenant_code、X-User-ID=delegated.subject_id）
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import sqlite3
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from openbase import init_app
from openbase.core.db.session import get_session_factory, init_db
from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Base, Permission, Role, User, role_permission, user_role
from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules import llm_proxy as llm_proxy_module
from openbase.modules.auth import hash_password
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.identity import delegation
from openbase.modules.protocol_headers import (
    PROXY_SOURCE_DPS,
    PROXY_SOURCE_LLM,
    PROXY_SOURCE_MEMORY,
)
from openbase.modules.proxy import memory_proxy as memory_proxy_module
from openbase.settings import Settings, get_settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t4.db"


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
    """装配启用 identity 模块的应用 + SQLite 库种子（admin/viewer/org_admin/org_member 角色）."""
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
        from openbase.core.db.session import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_session_factory()() as session:  # type: ignore[call-arg]
            role_admin = Role(name="系统管理员", code="admin", is_system=True)
            role_viewer = Role(name="只读用户", code="viewer", is_system=True)
            role_org_admin = Role(name="组织管理员", code="org_admin", is_system=True)
            role_org_member = Role(name="组织成员", code="org_member", is_system=True)
            session.add_all([role_admin, role_viewer, role_org_admin, role_org_member])
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
                Permission(code="identity:view", name="主体查看", module="identity", type=3),
                Permission(code="identity:manage", name="主体管理", module="identity", type=3),
                Permission(code="identity:lifecycle", name="生命周期管理", module="identity", type=3),
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
def _identity_t4_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局 engine 单例）."""
    global client
    client = _build_app()
    yield client
    client = None


# ---- 数据库辅助 ----

TENANT_SQL = """
INSERT INTO tenants (name, code, status, isolation_level, created_at, updated_at)
VALUES (:name, :code, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""

USER_SQL = """
INSERT INTO users (username, password_hash, display_name, status, tenant_id,
                   subject_type, credential_type, status_state, status_reason,
                   token_version, tenant_code, on_behalf_of, is_deleted,
                   created_at, updated_at)
VALUES (:username, :password_hash, :display_name, :status, :tenant_id,
        :subject_type, :credential_type, :status_state, :status_reason,
        :token_version, :tenant_code, :on_behalf_of, 0,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""


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


def _role_id(code: str) -> int | None:
    rows = _rows(f"SELECT id FROM roles WHERE code = '{code}'")
    return rows[0][0] if rows else None


def _make_subject(
    username: str,
    tenant_code: str | None = "acme",
    subject_type: str = "user",
    state: str = "active",
    role: str = "viewer",
    on_behalf_of: dict | None = None,
) -> int:
    """直插主体行（租户 + 角色绑定 + 可选 on_behalf_of JSON），返回 user id."""
    _ensure_tenant(tenant_code) if tenant_code else None
    tenant_id = _tenant_id(tenant_code) if tenant_code else None
    conn = _conn()
    try:
        cur = conn.execute(
            USER_SQL,
            {
                "username": username,
                "password_hash": hash_password("secret123"),
                "display_name": username,
                "status": 1 if state == "active" else 0,
                "tenant_id": tenant_id,
                "subject_type": subject_type,
                "credential_type": "api_key" if subject_type == "agent" else "password",
                "status_state": state,
                "status_reason": None,
                "token_version": 0,
                "tenant_code": tenant_code,
                "on_behalf_of": json.dumps(on_behalf_of) if on_behalf_of is not None else None,
            },
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()
    role_row = _role_id(role)
    if role_row:
        conn = _conn()
        try:
            conn.execute(
                "INSERT INTO user_role (user_id, role_id) VALUES (?, ?)",
                (user_id, role_row),
            )
            conn.commit()
        finally:
            conn.close()
    return user_id  # type: ignore[return-value]


def _username_of(user_id: int) -> str:
    return _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]  # type: ignore[return-value]


def _update_on_behalf_of(user_id: int, on_behalf_of: dict | None) -> None:
    conn = _conn()
    try:
        conn.execute(
            "UPDATE users SET on_behalf_of = ? WHERE id = ?",
            (json.dumps(on_behalf_of) if on_behalf_of is not None else None, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def _future_epoch(seconds: int = 3600) -> int:
    return int((dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)).timestamp())


def _me(token: str) -> object:
    assert client is not None
    return client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


def _decode(token: str) -> dict:
    settings = get_settings()
    return jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _forge_agent_token(
    agent_id: int,
    *,
    principal_tenant: str,
    delegated_claim: dict | None,
    role: str = "viewer",
) -> str:
    """按 agent 主体直签一个 access token（可携带 on_behalf_of 委托块）."""
    return create_access_token(
        str(agent_id),
        username=_username_of(agent_id),
        tenant_code=principal_tenant,
        subject_type="agent",
        token_version=0,
        extra={
            "role": role,
            "org_id": principal_tenant,
            "on_behalf_of": delegated_claim,
        },
    )


def _unified_user_ctx(
    agent_id: int,
    tenant_code: str,
    claim: dict | None,
    *,
    role: str = "viewer",
) -> dict:
    """构造与 ``get_current_user`` 返回同构的统一主体上下文（P2-1 共享包消费面）.

    P2-1 T1（K01）后，dps/llm/memory proxy 不再二次解码 JWT，出站装配直接消费
    统一主体 dict（含 delegated 归一化委托块）。
    """
    return {
        "id": agent_id,
        "username": _username_of(agent_id),
        "tenant_code": tenant_code,
        "tenant_id": None,
        "org_id": tenant_code,
        "subject_type": "agent",
        "role": role,
        "permissions": [],
        "auth_method": "jwt",
        "on_behalf_of": claim,
        "delegated": delegation.normalize_on_behalf_of(claim) if claim is not None else None,
    }


def _run_issue(principal_id: int, delegated_claim: dict | None) -> tuple[str, str]:
    """执行委托签发（提交事务，返回 access/refresh）."""
    async def _do() -> tuple[str, str]:
        async with get_session_factory()() as session:
            result = await delegation.issue_delegated_token_pair(
                session,
                principal_id=principal_id,
                delegated_claim=delegated_claim,
            )
            await session.commit()
            return result

    return asyncio.run(_do())


def _run_issue_error(principal_id: int, delegated_claim: dict | None) -> BaseError:
    """执行委托签发并捕获异常（未提交）. """
    async def _do() -> BaseError | None:
        async with get_session_factory()() as session:
            try:
                await delegation.issue_delegated_token_pair(
                    session,
                    principal_id=principal_id,
                    delegated_claim=delegated_claim,
                )
            except BaseError as exc:
                return exc
            return None

    error = asyncio.run(_do())
    assert error is not None, "预期委托签发被拒绝，但实际成功"
    return error


def _claim(
    subject_id: int,
    subject_type: str,
    tenant_code: str,
    role: str = "viewer",
    exp_seconds: int = 3600,
) -> dict:
    return delegation.build_on_behalf_of_claim(
        subject_id=subject_id,
        subject_type=subject_type,
        tenant_code=tenant_code,
        role=role,
        issuer="t4-test",
        exp_seconds=exp_seconds,
    )


# ---- T4-1 同域委托签发成功；claims 含 on_behalf_of ----


def test_t4_1_same_tenant_delegation_issue_success() -> None:
    """agent 域 A 代 user 域 A（同域）签发成功；access claims 含 on_behalf_of."""
    agent_id = _make_subject(_unique("t41-agent"), "acme", "agent", "active", "viewer")
    user_id = _make_subject(_unique("t41-user"), "acme", "user", "active", "viewer")
    claim = _claim(user_id, "user", "acme")

    access, refresh = _run_issue(agent_id, claim)

    access_payload = _decode(access)
    assert access_payload["sub_type"] == "agent"
    assert access_payload["tenant_code"] == "acme"
    assert access_payload["on_behalf_of"] is not None
    assert access_payload["on_behalf_of"]["subject_id"] == str(user_id)
    assert access_payload["on_behalf_of"]["subject_type"] == "user"
    assert access_payload["on_behalf_of"]["tenant_code"] == "acme"
    assert access_payload["on_behalf_of"]["role"] == "viewer"
    # refresh 同形态（refresh fidelity，草案 §6.3）
    refresh_payload = _decode(refresh)
    assert refresh_payload["on_behalf_of"]["subject_id"] == str(user_id)


# ---- T4-2 跨域委托签发 403 PERM_DELEGATION_CROSS_TENANT ----


def test_t4_2_cross_tenant_delegation_rejected() -> None:
    """agent 域 A 代 user 域 B（域 A→域 B）签发 → 403 PERM_DELEGATION_CROSS_TENANT."""
    agent_id = _make_subject(_unique("t42-agent"), "acme", "agent", "active", "viewer")
    user_id = _make_subject(_unique("t42-user"), "beta", "user", "active", "viewer")
    claim = _claim(user_id, "user", "beta")

    error = _run_issue_error(agent_id, claim)
    assert error.status_code == 403
    assert error.code == ErrorCode.PERM_DELEGATION_CROSS_TENANT


# ---- T4-3 每请求重校验：on_behalf_of 域被替换 → 403 ----


def test_t4_3_delegated_domain_swap_rejected_per_request() -> None:
    """合法同域委托 token 经 /auth/me 200；on_behalf_of 域被替换 → 403."""
    agent_id = _make_subject(_unique("t43-agent"), "acme", "agent", "active", "viewer")
    same_user_id = _make_subject(_unique("t43-same"), "acme", "user", "active", "viewer")
    other_user_id = _make_subject(_unique("t43-other"), "beta", "user", "active", "viewer")

    # 基线：同域委托 token → 200
    legit = _forge_agent_token(
        agent_id,
        principal_tenant="acme",
        delegated_claim=_claim(same_user_id, "user", "acme"),
    )
    ok_resp = _me(legit)
    assert ok_resp.status_code == 200, ok_resp.text

    # 域被替换为 beta（指向 beta 域 user）→ 403 PERM_DELEGATION_CROSS_TENANT
    tampered = _forge_agent_token(
        agent_id,
        principal_tenant="acme",
        delegated_claim=_claim(other_user_id, "user", "beta"),
    )
    blocked = _me(tampered)
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["code"] == ErrorCode.PERM_DELEGATION_CROSS_TENANT.value


# ---- T4-4 三级嵌套链任意一跳跨界 → 403；全同域 → 200 ----


def test_t4_4_nested_chain_same_domain_ok_cross_hop_rejected() -> None:
    """agent A→agent B(agent B 行 on_behalf_of→user C)：全同域 200；B 跳跨域 403."""
    agent_a = _make_subject(_unique("t44-a"), "acme", "agent", "active", "viewer")
    user_c = _make_subject(_unique("t44-c"), "acme", "user", "active", "viewer")
    agent_b = _make_subject(
        _unique("t44-b"),
        "acme",
        "agent",
        "active",
        "viewer",
        on_behalf_of=_claim(user_c, "user", "acme"),
    )
    # A 的 token 委托到 B（同域第一跳），B 行的 on_behalf_of 形成第二跳 → C
    token = _forge_agent_token(
        agent_a,
        principal_tenant="acme",
        delegated_claim=_claim(agent_b, "agent", "acme"),
    )
    ok_resp = _me(token)
    assert ok_resp.status_code == 200, ok_resp.text

    # 第二跳（B→C）被改为跨域：B 的 on_behalf_of 指向 beta 域 user
    cross_user = _make_subject(_unique("t44-x"), "beta", "user", "active", "viewer")
    _update_on_behalf_of(agent_b, _claim(cross_user, "user", "beta"))
    blocked = _me(token)
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["code"] == ErrorCode.PERM_DELEGATION_CROSS_TENANT.value


# ---- T4-5 user 挂 on_behalf_of / 目标非 active / 代理角色越权 全部 403 ----


def test_t4_5_user_principal_cannot_carry_on_behalf_of() -> None:
    """user 主体试图挂 on_behalf_of（签发）→ 403."""
    user_principal = _make_subject(_unique("t45-up"), "acme", "user", "active", "viewer")
    target_id = _make_subject(_unique("t45-ut"), "acme", "user", "active", "viewer")
    error = _run_issue_error(user_principal, _claim(target_id, "user", "acme"))
    assert error.status_code == 403


def test_t4_5_delegation_target_not_active_rejected() -> None:
    """委托目标非 active（suspended）→ 403."""
    agent_id = _make_subject(_unique("t45-ai"), "acme", "agent", "active", "viewer")
    suspended_id = _make_subject(_unique("t45-sus"), "acme", "user", "suspended", "viewer")
    error = _run_issue_error(agent_id, _claim(suspended_id, "user", "acme"))
    assert error.status_code == 403


def test_t4_5_delegated_role_overreach_rejected() -> None:
    """代理角色越权：agent(viewer) 试图以 org_admin 角色代执行 → 403 PERM_DELEGATION_ROLE."""
    agent_id = _make_subject(_unique("t45-ro"), "acme", "agent", "active", "viewer")
    target_id = _make_subject(_unique("t45-rt"), "acme", "user", "active", "viewer")
    claim = _claim(target_id, "user", "acme", role="org_admin")
    error = _run_issue_error(agent_id, claim)
    assert error.status_code == 403
    assert error.code == ErrorCode.PERM_DELEGATION_ROLE


# ---- T4-6 审计 detail 记两层（principal+delegated） ----


def test_t4_6_audit_detail_records_two_layers() -> None:
    """委托签发写 audit_logs：detail 含 {principal:{id,tenant_code}, delegated:{...}}."""
    agent_id = _make_subject(_unique("t46-agent"), "acme", "agent", "active", "viewer")
    user_id = _make_subject(_unique("t46-user"), "acme", "user", "active", "viewer")
    claim = _claim(user_id, "user", "acme")

    access, _refresh = _run_issue(agent_id, claim)
    assert _decode(access)["on_behalf_of"] is not None

    rows = _rows(
        "SELECT detail FROM audit_logs WHERE action = 'identity.delegation.issue' "
        "ORDER BY id DESC LIMIT 1"
    )
    assert len(rows) == 1, "委托签发应写入 identity.delegation.issue 审计"
    detail = json.loads(rows[0][0])
    assert detail["principal"]["id"] == agent_id
    assert detail["principal"]["tenant_code"] == "acme"
    assert detail["delegated"]["id"] == user_id
    assert detail["delegated"]["tenant_code"] == "acme"
    assert detail["delegated"]["role"] == "viewer"


# ---- T4-7 代理族出站头取委托域值 ----


def test_t4_7_dps_proxy_outbound_headers_use_delegated_domain() -> None:
    """dps-proxy 委托请求出站头：X-User-ID=delegated.subject_id、
    X-Tenant-ID/X-Org-ID=委托 tenant_code、X-User-Role=delegated.role."""
    agent_id = _make_subject(_unique("t47d-agent"), "acme", "agent", "active", "viewer")
    user_id = _make_subject(_unique("t47d-user"), "acme", "user", "active", "viewer")
    claim = _claim(user_id, "user", "acme")
    # P2-1 T1：dps-proxy 不再二次解码 JWT，出站装配直接消费统一主体上下文
    user_ctx = _unified_user_ctx(agent_id, "acme", claim)
    headers = dps_proxy_module._build_identity_headers(user_ctx, None)
    assert headers["X-User-ID"] == str(user_id)
    assert headers["X-Tenant-ID"] == "acme"
    assert headers["X-Org-ID"] == "acme"
    assert headers["X-User-Role"] == "viewer"
    assert headers["X-Agent-Id"] == str(agent_id)  # 委托场景执行 agent 标注
    assert headers["X-Proxy-Source"] == PROXY_SOURCE_DPS  # P2-1 T1：来源头补齐


def test_t4_7_llm_proxy_outbound_headers_use_delegated_domain() -> None:
    """llm-proxy 委托请求出站头：X-User-ID=delegated.subject_id、X-Org-ID=委托 tenant_code."""
    from starlette.requests import Request

    agent_id = _make_subject(_unique("t47l-agent"), "acme", "agent", "active", "viewer")
    user_id = _make_subject(_unique("t47l-user"), "acme", "user", "active", "viewer")
    claim = _claim(user_id, "user", "acme")
    token = _forge_agent_token(agent_id, principal_tenant="acme", delegated_claim=claim)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/openllm/v1/models",
        "raw_path": b"/openllm/v1/models",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    headers = llm_proxy_module._build_upstream_headers(Request(scope), _unified_user_ctx(agent_id, "acme", claim))
    assert headers["X-User-ID"] == str(user_id)
    assert headers["X-Org-ID"] == "acme"
    assert headers["X-Tenant-ID"] == "acme"  # P2-1 T1：llm 补 X-Tenant-ID
    assert headers["X-Agent-Id"] == str(agent_id)
    assert headers["X-Proxy-Source"] == PROXY_SOURCE_LLM


def test_t4_7_memory_proxy_outbound_headers_use_delegated_domain() -> None:
    """memory-proxy 委托请求出站头：X-User-ID=delegated.subject_id、
    X-Org-ID/X-Tenant-ID=委托 tenant_code."""
    from starlette.requests import Request

    agent_id = _make_subject(_unique("t47m-agent"), "acme", "agent", "active", "viewer")
    user_id = _make_subject(_unique("t47m-user"), "acme", "user", "active", "viewer")
    claim = _claim(user_id, "user", "acme")
    token = _forge_agent_token(agent_id, principal_tenant="acme", delegated_claim=claim)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/remember",
        "raw_path": b"/api/v1/remember",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    request = Request(scope)
    user_ctx = _unified_user_ctx(agent_id, "acme", claim)
    headers = memory_proxy_module._build_upstream_headers(request, user_ctx)
    assert headers["X-User-ID"] == str(user_id)
    assert headers["X-Org-ID"] == "acme"
    assert headers["X-Tenant-ID"] == "acme"
    assert headers["X-User-Role"] == "viewer"  # P2-1 T1：memory 补 X-User-Role
    assert headers["X-Agent-Id"] == str(agent_id)
    assert headers["X-Proxy-Source"] == PROXY_SOURCE_MEMORY  # P2-1 T1：memory 补来源


# ---- 补充：claim 归一化/每请求骨架单元语义（钉死边界，R2 骨架） ----


def test_t4_claim_normalization_and_safe_payload_extraction() -> None:
    """normalize_on_behalf_of：None→None、合法块归一化、畸形块抛 403."""
    assert delegation.normalize_on_behalf_of(None) is None
    claim = _claim(42, "user", "acme")
    normalized = delegation.normalize_on_behalf_of(claim)
    assert normalized is not None
    assert normalized["subject_id"] == 42

    with pytest.raises(BaseError) as exc_info:
        delegation.normalize_on_behalf_of("garbage")
    assert exc_info.value.status_code == 403

    with pytest.raises(BaseError):
        delegation.normalize_on_behalf_of({"subject_id": 1, "tenant_code": "acme"})

    # 安全提取：畸形块不抛（逐跳重校验前由主体验证器先行拦截）
    assert delegation.delegated_claim_from_payload({"on_behalf_of": "garbage"}) is None
    assert delegation.delegated_claim_from_payload({}) is None


def test_t4_verify_request_delegation_noop_without_claim() -> None:
    """无 on_behalf_of claim：逐跳重校验直接放行（返回快照不变）."""
    snapshot = {"subject_type": "user", "tenant_code": "acme"}
    result = asyncio.run(
        delegation.verify_request_delegation(object(), {}, snapshot)
    )
    assert result == snapshot
