"""U1 T5（L1-1）跨系统生命周期级联事件：事件源 outbox dispatcher + 契约桩/模拟消费端 TDD 用例.

RED→GREEN 断言对齐《OpenBase-U1-统一身份收口设计草案》v1.0.0 §11 T5-1~T5-6 与
§8.1/§8.2/§8.3/§10.1（事件 schema v1 / outbox+Redis 投递 / 消费端幂等 / 阻断语义对账桩态）：

- T5-1  deactivate 提交后 outbox 同事务出现 `user.deactivated` 事件（status=pending）
- T5-2  模拟消费端 apply 事件后：DPS 画像读 / OpenMemory 记忆访问契约桩返回拒绝语义
- T5-3  幂等：同 event_id 重放两次 → 阻断副作用仅一次（消费端幂等表断言）
- T5-4  事件 schema v1 字段完整（subject/tenant_code/previous_state/current_state/reason）
        且缺字段/未知事件类型的 apply 被 400 拒绝
- T5-5  投递秒级窗口：deactivate → outbox dispatcher → Redis 通知消费 ≤5s（契约桩计时断言）
- T5-6  user.suspended 事件阻断；user.restored 事件解除阻断
- 补充：GET /events/{event_id} 状态查询（published/publish_attempts/published_at）；
      未知 event_id → 404。

纪律：先写测试（RED）→ 实现（GREEN）；ruff 0；文件独立进程执行（不复用他模块 app/DB）。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.errors import ErrorCode
from openbase.core.models import (
    Base,
    Permission,
    Role,
    Tenant,
    User,
    role_permission,
    user_role,
)
from openbase.modules.auth import hash_password
from openbase.modules.identity import events as identity_events
from openbase.settings import Settings, get_settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_t5.db"


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
    """装配启用 identity 模块的应用 + SQLite 库种子（admin + identity:* 权限）."""
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
def _identity_t5_app() -> TestClient:
    """模块级应用装配 + 契约桩订阅注册（延迟到首用例，避免 import 期污染全局单例）."""
    global client
    client = _build_app()
    from openbase.modules.identity.consumer_stub import EventConsumerStub

    EventConsumerStub.subscribe()
    yield client
    client = None


# ---- 数据库辅助（沿用 T2/T3/T4 直插形态） ----

TENANT_SQL = """
INSERT INTO tenants (name, code, status, isolation_level, created_at, updated_at)
VALUES (:name, :code, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
"""

USER_SQL = """
INSERT INTO users (username, password_hash, display_name, status, tenant_id,
                   subject_type, credential_type, status_state, status_reason,
                   token_version, tenant_code, is_deleted, created_at, updated_at)
VALUES (:username, :password_hash, :display_name, :status, :tenant_id,
        :subject_type, :credential_type, :status_state, :status_reason,
        :token_version, :tenant_code, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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


def _make_user(username: str, tenant_code: str | None = "acme") -> int:
    """直插 active user 行（附租户），返回 user id."""
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
                "status": 1,
                "tenant_id": tenant_id,
                "subject_type": "user",
                "credential_type": "password",
                "status_state": "active",
                "status_reason": None,
                "token_version": 0,
                "tenant_code": tenant_code,
            },
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()
    return user_id  # type: ignore[return-value]


def _username_of(user_id: int) -> str:
    return _rows(f"SELECT username FROM users WHERE id = {user_id}")[0][0]  # type: ignore[return-value]


def _login(username: str, password: str = "secret123"):
    assert client is not None
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _admin_headers() -> dict[str, str]:
    resp = _login("admin", "admin123")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _decode(token: str) -> dict:
    settings = get_settings()
    return jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _lifecycle_url(subject_type: str, subject_id: int, action: str) -> str:
    return f"/api/v1/identity/lifecycle/{subject_type}/{subject_id}/{action}"


def _lifecycle(subject_type: str, subject_id: int, action: str, reason: str) -> object:
    body: dict = {"reason": reason}
    if action == "deactivate":
        body = {"confirm": True, "reason": reason}
    assert client is not None
    return client.post(
        _lifecycle_url(subject_type, subject_id, action),
        json=body,
        headers=_admin_headers(),
    )


def _outbox_rows_for(subject_id: int) -> list[tuple]:
    """按主体返回 outbox 事件行（event_id, event_type, status, payload），按 id 升序."""
    return _rows(
        "SELECT event_id, event_type, status, payload FROM outbox_events WHERE payload LIKE "
        f"'%\"subject_id\": {subject_id}%' ORDER BY id"
    )


def _payload_of(subject_id: int, event_type: str) -> dict:
    """取指定主体某事件类型的 outbox payload（JSON dict；同类型多条取最新一条）."""
    rows = _outbox_rows_for(subject_id)
    latest_payload: dict | None = None
    for _event_id, row_event_type, _status, payload_raw in rows:
        if row_event_type == event_type:
            latest_payload = json.loads(payload_raw)  # type: ignore[arg-type]
    if latest_payload is None:
        raise AssertionError(f"no {event_type} event found for subject {subject_id}")
    return latest_payload


def _apply_event(event_payload: dict, consumer: str | None = None) -> object:
    """POST /events/apply（契约桩模拟消费；consumer 缺省=全部桩域）."""
    assert client is not None
    body: dict = {"event": event_payload}
    if consumer is not None:
        body["consumer"] = consumer
    return client.post("/api/v1/identity/events/apply", json=body, headers=_admin_headers())


def _gate(subject_id: int, domain: str) -> object:
    """GET /blocked/{subject_id}?domain=… 数据面阻断对账（桩态：拒绝语义=403 PERM_FORBIDDEN）."""
    assert client is not None
    return client.get(
        f"/api/v1/identity/blocked/{subject_id}?domain={domain}",
        headers=_admin_headers(),
    )


def _run_dispatch_once() -> None:
    """手动触发 outbox dispatcher run_once（T5 可测试触发入口；独立会话提交）."""
    from openbase.modules.identity.dispatcher import OutboxDispatcherService

    async def _do() -> None:
        async with get_session_factory()() as session:
            await OutboxDispatcherService.run_once(session)
            await session.commit()

    asyncio.run(_do())


# ---- T5-1 deactivate 同事务出 outbox 事件 ----

def test_t5_1_deactivate_outbox_event_same_transaction() -> None:
    """deactivate 提交后 outbox 出现 user.deactivated（同事务写，status=pending）."""
    user_id = _make_user(_unique("t51"))
    resp = _lifecycle("user", user_id, "deactivate", "member left t5-1")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status_state"] == "deactivated"

    rows = _outbox_rows_for(user_id)
    assert len(rows) == 1, rows
    event_id, event_type, status, _payload_raw = rows[0]
    assert event_type == identity_events.EVENT_USER_DEACTIVATED
    assert status == identity_events.EVENT_STATUS_PENDING


# ---- T5-2 契约桩 apply 后 DPS 画像读 / OpenMemory 记忆访问返回拒绝语义 ----

def test_t5_2_deactivated_apply_denies_dps_portrait_and_memory_access() -> None:
    """user.deactivated apply 到契约桩 → DPS 画像读 / OpenMemory 记忆访问契约桩 403 拒绝语义."""
    user_id = _make_user(_unique("t52"))
    assert _lifecycle("user", user_id, "deactivate", "t5-2 security").status_code == 200
    payload = _payload_of(user_id, identity_events.EVENT_USER_DEACTIVATED)

    applied = _apply_event(payload)
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["event_id"] == payload["event_id"]
    # 默认应用到全部桩域（dps/openmemory/openrag）
    consumed_domains = {result["consumer"] for result in body["consumption"]["results"]}
    assert {"dps", "openmemory", "openrag"}.issubset(consumed_domains)
    assert all(not result["deduplicated"] for result in body["consumption"]["results"])

    # 阻断语义对账（桩态）：拒绝语义 = 403 PERM_FORBIDDEN
    for domain in ("dps", "openmemory"):
        denied = _gate(user_id, domain)
        assert denied.status_code == 403, (domain, denied.text)
        assert denied.json()["code"] == ErrorCode.PERM_FORBIDDEN.value

    # 阻断集落表（桩态 DB）：blocked 状态 + 幂等消费记录
    blocks = _rows(
        "SELECT domain, state FROM subject_blocks "
        f"WHERE subject_id = {user_id} AND state = 'blocked'"
    )
    assert {"dps", "openmemory", "openrag"}.issubset({row[0] for row in blocks})
    consumptions = _rows(
        f"SELECT COUNT(*) FROM event_consumptions WHERE event_id = '{payload['event_id']}'"
    )
    assert consumptions[0][0] == 3  # 三个桩域各一次执行


# ---- T5-3 event_id 幂等：重放不产生重复阻断副作用 ----

def test_t5_3_replay_same_event_id_side_effect_once() -> None:
    """同 event_id 重放两次 → 消费端幂等表仅 1 条执行记录；阻断副作用仅一次."""
    user_id = _make_user(_unique("t53"))
    assert _lifecycle("user", user_id, "deactivate", "t5-3 replay").status_code == 200
    payload = _payload_of(user_id, identity_events.EVENT_USER_DEACTIVATED)
    event_id = payload["event_id"]

    first = _apply_event(payload, consumer="dps")
    assert first.status_code == 200, first.text
    assert first.json()["consumption"]["results"][0]["deduplicated"] is False

    second = _apply_event(payload, consumer="dps")
    assert second.status_code == 200, second.text
    results = second.json()["consumption"]["results"]
    assert results[0]["consumer"] == "dps"
    assert results[0]["deduplicated"] is True

    # 消费端幂等表断言：event_id+consumer 仅一条执行记录
    consumption_count = _rows(
        f"SELECT COUNT(*) FROM event_consumptions WHERE event_id = '{event_id}' "
        "AND consumer = 'dps'"
    )
    assert consumption_count[0][0] == 1, "重放不得产生第二条消费执行记录"

    # 阻断副作用仅一次：阻断集单行 blocked
    block_rows = _rows(
        "SELECT state, event_id FROM subject_blocks "
        f"WHERE subject_id = {user_id} AND domain = 'dps'"
    )
    assert len(block_rows) == 1
    assert block_rows[0][0] == "blocked"
    assert block_rows[0][1] == event_id


# ---- T5-4 事件 schema v1 字段完整 + 非法载荷拒绝 ----

def test_t5_4_outbox_payload_schema_v1_fields_complete() -> None:
    """deactivate 写出的 outbox payload 含 schema v1 全部契约字段（草案 §8.1）. """
    user_id = _make_user(_unique("t54"))
    assert _lifecycle("user", user_id, "deactivate", "t5-4 schema").status_code == 200
    payload = _payload_of(user_id, identity_events.EVENT_USER_DEACTIVATED)

    assert payload["event_type"] == identity_events.EVENT_USER_DEACTIVATED
    assert payload["schema_version"] == identity_events.EVENT_SCHEMA_VERSION
    assert payload["event_id"]
    assert payload["occurred_at"]
    assert payload["source"] == identity_events.EVENT_SOURCE
    subject = payload["subject"]
    assert subject["subject_id"] == user_id
    assert subject["subject_type"] == "user"
    assert subject["username"]
    assert payload["tenant_code"] == "acme"
    assert payload["previous_state"] == "active"
    assert payload["current_state"] == "deactivated"
    assert payload["reason"] == "t5-4 schema"
    assert isinstance(payload["role_codes"], list)


def test_t5_4_apply_rejects_incomplete_and_unknown_event_payload() -> None:
    """缺 schema 字段 / 未知事件类型 → 400 PARAM_INVALID（契约校验）."""
    user_id = _make_user(_unique("t54b"))
    assert _lifecycle("user", user_id, "deactivate", "t5-4 invalid").status_code == 200
    payload = _payload_of(user_id, identity_events.EVENT_USER_DEACTIVATED)

    # 缺 previous_state → 400 PARAM_INVALID
    incomplete = dict(payload)
    del incomplete["previous_state"]
    bad = _apply_event(incomplete)
    assert bad.status_code == 400, bad.text
    assert bad.json()["code"] == ErrorCode.PARAM_INVALID.value

    # 缺 subject → 400
    no_subject = dict(payload)
    del no_subject["subject"]
    bad2 = _apply_event(no_subject)
    assert bad2.status_code == 400, bad2.text
    assert bad2.json()["code"] == ErrorCode.PARAM_INVALID.value

    # 未知事件类型 → 400
    unknown_type = dict(payload, event_type="user.purged")
    bad3 = _apply_event(unknown_type)
    assert bad3.status_code == 400, bad3.text
    assert bad3.json()["code"] == ErrorCode.PARAM_INVALID.value

    # schema_version 非 1 → 400
    bad_version = dict(payload, schema_version=2)
    bad4 = _apply_event(bad_version)
    assert bad4.status_code == 400, bad4.text
    assert bad4.json()["code"] == ErrorCode.PARAM_INVALID.value


# ---- T5-5 投递秒级窗口 ≤5s（outbox dispatcher → Redis 通知消费） ----

def test_t5_5_dispatch_within_seconds_window_and_status_published() -> None:
    """deactivate → dispatcher run_once → 契约桩消费 ≤5s；outbox 状态置 published."""
    from openbase.modules.identity.consumer_stub import EventConsumerStub

    user_id = _make_user(_unique("t55"))
    assert _lifecycle("user", user_id, "deactivate", "t5-5 window").status_code == 200
    event_id = _outbox_rows_for(user_id)[0][0]
    assert (
        _rows(
            f"SELECT status FROM outbox_events WHERE event_id = '{event_id}'"
        )[0][0]
        == identity_events.EVENT_STATUS_PENDING
    )

    # 契约桩订阅已注册（模块 fixture）；触发前清空到达记录并开始计时
    EventConsumerStub.clear_received()
    started = time.monotonic()
    _run_dispatch_once()

    received = EventConsumerStub.received(event_id)
    assert received is not None, "契约桩必须收到 outbox dispatcher 发布的事件"
    elapsed = received["received_at"] - started
    assert elapsed <= 5.0, f"投递超窗口：{elapsed:.3f}s > 5s"

    # 状态查询接口：published + published_at
    status_resp = client.get(  # type: ignore[union-attr]
        f"/api/v1/identity/events/{event_id}",
        headers=_admin_headers(),
    )
    assert status_resp.status_code == 200, status_resp.text
    status_body = status_resp.json()
    assert status_body["event_id"] == event_id
    assert status_body["event_type"] == identity_events.EVENT_USER_DEACTIVATED
    assert status_body["status"] == identity_events.EVENT_STATUS_PUBLISHED
    assert status_body["publish_attempts"] == 1
    assert status_body["published_at"] is not None
    assert status_body["payload"]["current_state"] == "deactivated"

    # 未知 event_id → 404
    missing = client.get(  # type: ignore[union-attr]
        f"/api/v1/identity/events/{uuid.uuid4().hex}",
        headers=_admin_headers(),
    )
    assert missing.status_code == 404, missing.text


# ---- T5-6 suspended 阻断 / restored 解除阻断 ----

def test_t5_6_suspended_blocks_restored_releases() -> None:
    """user.suspended apply → 数据面阻断；user.restored apply → 解除阻断（对账放行）."""
    user_id = _make_user(_unique("t56"))
    username = _username_of(user_id)

    # ① suspend：apply user.suspended → 阻断（403 拒绝语义）
    assert _lifecycle("user", user_id, "suspend", "t5-6 hold").status_code == 200
    suspended_payload = _payload_of(user_id, identity_events.EVENT_USER_SUSPENDED)
    assert _apply_event(suspended_payload).status_code == 200
    denied = _gate(user_id, "dps")
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == ErrorCode.PERM_FORBIDDEN.value

    # ② restore：apply user.restored → 解除阻断（对账放行）
    assert _lifecycle("user", user_id, "restore", "t5-6 release").status_code == 200
    restored_payload = _payload_of(user_id, identity_events.EVENT_USER_RESTORED)
    assert _apply_event(restored_payload).status_code == 200
    allowed = _gate(user_id, "dps")
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["allowed"] is True
    checks = {check["domain"]: check for check in allowed.json()["checks"]}
    assert checks["dps"]["allowed"] is True

    # ③ 解除后主体可登录（状态机语义一致：restore 后重登成功）
    relogin = _login(username)
    assert relogin.status_code == 200, relogin.text

    # ④ 再停用（active→suspended 事件再次阻断）
    assert _lifecycle("user", user_id, "suspend", "t5-6 re-hold").status_code == 200
    re_suspended_payload = _payload_of(user_id, identity_events.EVENT_USER_SUSPENDED)
    assert _apply_event(re_suspended_payload).status_code == 200
    re_denied = _gate(user_id, "dps")
    assert re_denied.status_code == 403, re_denied.text


# ---- 补充：EventConsumerStub 单元语义（契约桩边界钉死） ----

def test_t5_stub_validate_schema_unit() -> None:
    """契约桩 schema 校验纯函数：畸形载荷一律 400 PARAM_INVALID（单元语义）."""
    from openbase.core.errors import BaseError
    from openbase.modules.identity.consumer_stub import EventConsumerStub

    with pytest.raises(BaseError) as exc_info:
        EventConsumerStub.validate_event_payload({})
    assert exc_info.value.code == ErrorCode.PARAM_INVALID

    with pytest.raises(BaseError) as exc_info:
        EventConsumerStub.validate_event_payload(
            {
                "event_id": "x",
                "event_type": "user.deactivated",
                "previous_state": "active",
                "current_state": "deactivated",
                "subject": {},
            }
        )
    assert exc_info.value.status_code == 400
