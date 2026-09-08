"""Q-DESIGN-1（OpenBase 责任登记）身份事件单向列表端点 GET /identity/events TDD 用例.

契约对齐《OpenBase-事件消费契约-v1.0》与 OpenMemory S2 Q-DESIGN-1 冻结契约：
- GET /api/v1/identity/events?cursor={event_id}&limit={N}（无 ack、无 consumer 过滤）；
- 仅返回 outbox 已 published 事件，按 (created_at, event_id) 稳定全序（= occurred_at/event_id
  序的落库等价键）升序；cursor 为排他上界（严格返回 cursor 之后的事件，不含 cursor 自身）；
- next_cursor 非空表示还有更多（取当前页最后一条 event_id），空（null）表示无更多；
- limit 缺省 50、上限 100（服务端钳制，超限不报错）；limit<1 → 400 PARAM_INVALID；
- 未知/未 published 游标 → 400 PARAM_INVALID（消费端从头部重拉）；
- 返回事件为 schema v1 全字段载荷（subject 嵌套/role_codes/previous_state/current_state/reason）；
- 受权：identity:view（admin 通配 + RBAC 兜底），无权限 403 PERM_FORBIDDEN。

纪律：先写测试（RED，端点缺失 → 404/405）→ 实现（GREEN）；ruff 0；独立进程/独立 DB 执行。
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

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.errors import ErrorCode
from openbase.core.models import Base, Permission, Role, Tenant, User, role_permission, user_role
from openbase.modules.auth import hash_password
from openbase.modules.identity import events as identity_events
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_identity_events_list.db"

# 直插 outbox 行的基准时间（created_at 逐 idx 递增 → 稳定序确定）
_TS_BASE = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)


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
def _identity_events_list_app() -> TestClient:
    """模块级应用装配（延迟到首用例，避免 import 期污染全局单例）."""
    global client
    client = _build_app()
    yield client
    client = None


def _login(username: str, password: str = "secret123"):
    assert client is not None
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _admin_headers() -> dict[str, str]:
    resp = _login("admin", "admin123")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _viewer_headers() -> dict[str, str]:
    """构造无任何 identity:* 权限的 viewer 登录头（角色 viewer 无权限映射）."""
    assert client is not None
    username = _unique("viewer-op")
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, status, tenant_id,"
            " subject_type, credential_type, status_state, status_reason, token_version,"
            " tenant_code, is_deleted, created_at, updated_at)"
            " VALUES (?, ?, ?, 1, NULL, 'user', 'password', 'active', NULL, 0, NULL, 0,"
            " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (username, hash_password("secret123"), username),
        )
        conn.commit()
        user_id = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
        role_id = conn.execute("SELECT id FROM roles WHERE code = 'viewer'").fetchone()[0]
        conn.execute("INSERT INTO user_role (user_id, role_id) VALUES (?, ?)", (user_id, role_id))
        conn.commit()
    finally:
        conn.close()
    resp = _login(username)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---- outbox_events 直插辅助（已 published 事件集，created_at 逐 idx 递增） ----

_EVENT_META: dict[str, tuple[str, str]] = {
    identity_events.EVENT_USER_PROVISIONED: ("provisioned", "active"),
    identity_events.EVENT_USER_SUSPENDED: ("active", "suspended"),
    identity_events.EVENT_USER_RESTORED: ("suspended", "active"),
    identity_events.EVENT_USER_DEACTIVATED: ("active", "deactivated"),
}


def _schema_v1_payload(
    event_id: str,
    idx: int,
    event_type: str = identity_events.EVENT_USER_DEACTIVATED,
    reason: str | None = None,
) -> dict:
    """构造 schema v1 事件载荷（occurred_at 与 created_at 同刻同序）. """
    previous_state, current_state = _EVENT_META[event_type]
    occurred_at = (_TS_BASE + dt.timedelta(microseconds=idx)).isoformat()
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "source": identity_events.EVENT_SOURCE,
        "request_id": None,
        "subject": {
            "subject_id": 5000 + idx,
            "subject_type": "user",
            "username": f"subject-{idx}",
        },
        "tenant_code": "acme",
        "role_codes": ["viewer"] if idx % 2 == 0 else [],
        "previous_state": previous_state,
        "current_state": current_state,
        "reason": reason or f"reason-{idx}",
        "schema_version": identity_events.EVENT_SCHEMA_VERSION,
    }


def _insert_outbox(
    idx: int,
    *,
    event_type: str = identity_events.EVENT_USER_DEACTIVATED,
    status: str = identity_events.EVENT_STATUS_PUBLISHED,
    event_id: str | None = None,
    reason: str | None = None,
) -> str:
    """直插一条 outbox 事件（默认 published），返回 event_id."""
    event_id = event_id or _unique("evt")
    payload = _schema_v1_payload(event_id, idx, event_type=event_type, reason=reason)
    ts = _TS_BASE + dt.timedelta(microseconds=idx)
    created_at = ts.strftime("%Y-%m-%d %H:%M:%S.%f")
    published_at = created_at if status == identity_events.EVENT_STATUS_PUBLISHED else None
    publish_attempts = 1 if status == identity_events.EVENT_STATUS_PUBLISHED else 0
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO outbox_events (event_id, event_type, payload, status,"
            " publish_attempts, next_retry_at, published_at, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?)",
            (
                event_id,
                event_type,
                json.dumps(payload, ensure_ascii=False),
                status,
                publish_attempts,
                published_at,
                created_at,
                created_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return event_id


def _published_ordered() -> list[tuple[str, dict]]:
    """当前 outbox 已 published 事件（event_id, payload），按端点稳定序（created_at, event_id）."""
    rows = _rows(
        "SELECT event_id, payload FROM outbox_events"
        f" WHERE status = '{identity_events.EVENT_STATUS_PUBLISHED}'"
        " ORDER BY created_at, event_id"
    )
    return [(event_id, json.loads(payload_raw)) for event_id, payload_raw in rows]


def _events_list(*, cursor: str | None = None, limit: int | None = None, headers: dict | None = None):
    """GET /api/v1/identity/events 请求封装."""
    assert client is not None
    params: dict = {}
    if cursor is not None:
        params["cursor"] = cursor
    if limit is not None:
        params["limit"] = str(limit)
    return client.get("/api/v1/identity/events", params=params, headers=headers or _admin_headers())


def _crawl(page_limit: int) -> list[str]:
    """从头部按 next_cursor 逐页拉取全部事件 id（无重复无遗漏遍历）. """
    collected: list[str] = []
    cursor: str | None = None
    for _ in range(10_000):  # 防御性上限（正常远小于此）
        body = _events_list(cursor=cursor, limit=page_limit).json()
        page = [event["event_id"] for event in body["events"]]
        collected.extend(page)
        if body["next_cursor"] is None:
            break
        if body["next_cursor"] == cursor:
            raise AssertionError("next_cursor 未推进，疑似死循环")
        cursor = body["next_cursor"]
    return collected


# ---- 用例：分页游标稳定序 / 无重复无遗漏遍历全量 / 按 cursor 续拉不重叠 ----

def test_paginate_cursor_stable_order_no_dup_no_gap() -> None:
    """limit 游标翻页：全量遍历无重复无遗漏，且两次独立遍历次序稳定."""
    inserted_ids = [_insert_outbox(100 + i) for i in range(7)]
    expected_ids = [event_id for event_id, _payload in _published_ordered()]
    assert set(inserted_ids).issubset(expected_ids)

    first_walk = _crawl(page_limit=3)
    second_walk = _crawl(page_limit=3)
    assert first_walk == second_walk, "两次遍历次序必须稳定"
    assert len(first_walk) == len(set(first_walk)), "游标翻页不得重复返回事件"
    assert first_walk == expected_ids, "游标翻页必须无遗漏地覆盖全部已 published 事件"


def test_cursor_continue_pull_no_overlap_and_termination() -> None:
    """按 cursor 续拉不重叠：相邻页无交集；末页 next_cursor 为空表示无更多."""
    for i in range(8):
        _insert_outbox(200 + i)
    first = _events_list(limit=3).json()
    assert first["next_cursor"] is not None, "存在更多事件时 next_cursor 必须非空"
    assert len(first["events"]) == 3

    second = _events_list(cursor=first["next_cursor"], limit=3).json()
    first_ids = {event["event_id"] for event in first["events"]}
    second_ids = {event["event_id"] for event in second["events"]}
    assert not (first_ids & second_ids), "续拉页与上一页不得重叠"

    # 沿游标走到底（limit=4）：无重叠无遗漏，末页 next_cursor 为 null
    collected: list[str] = []
    cursor: str | None = None
    seen_ids: set[str] = set()
    for _ in range(10_000):  # 防御性上限
        body = _events_list(cursor=cursor, limit=4).json()
        page = [event["event_id"] for event in body["events"]]
        for event_id in page:
            assert event_id not in seen_ids, "跨页不得重复返回同一事件"
            seen_ids.add(event_id)
        collected.extend(page)
        if body["next_cursor"] is None:
            break
        cursor = body["next_cursor"]
    expected_ids = [event_id for event_id, _payload in _published_ordered()]
    assert collected == expected_ids, "沿游标续拉必须无遗漏覆盖全量且有序"

    # 末页之后无更多：以最后一条已返回事件为游标续拉 → 空 events + next_cursor=null
    tail = _events_list(cursor=expected_ids[-1], limit=4).json()
    assert tail["events"] == [] and tail["next_cursor"] is None


def test_limit_clamped_to_max_and_default() -> None:
    """limit 上限钳制（超 100 返回 100 不报错）；缺省 limit=50."""
    # 保证 published 总数超过 100
    existing = len(_published_ordered())
    for i in range(120 - existing):
        _insert_outbox(300 + i)

    oversized = _events_list(limit=1000).json()
    assert len(oversized["events"]) == 100, "limit 超过上限必须钳制为 100"
    assert oversized["next_cursor"] is not None

    exactly_max = _events_list(limit=100).json()
    assert len(exactly_max["events"]) == 100

    defaulted = _events_list().json()
    assert len(defaulted["events"]) == 50, "缺省 limit 必须为 50"
    assert defaulted["next_cursor"] is not None


def test_limit_below_one_returns_400() -> None:
    """limit<1 → 400 PARAM_INVALID（非合法钳制区间）. """
    bad = _events_list(limit=0)
    assert bad.status_code == 400, bad.text
    assert bad.json()["code"] == ErrorCode.PARAM_INVALID.value
    negative = _events_list(limit=-5)
    assert negative.status_code == 400, negative.text
    assert negative.json()["code"] == ErrorCode.PARAM_INVALID.value


# ---- 用例：事件字段完整性（schema v1 全字段 + 与 outbox 存储一致） ----

def test_events_payload_schema_v1_fields_complete() -> None:
    """列表返回事件为 schema v1 全字段载荷（含 subject 嵌套/role_codes/状态字段）."""
    _insert_outbox(400, event_type=identity_events.EVENT_USER_PROVISIONED, reason="onboard")
    _insert_outbox(401, event_type=identity_events.EVENT_USER_SUSPENDED, reason="hold")
    _insert_outbox(402, event_type=identity_events.EVENT_USER_RESTORED, reason="release")
    _insert_outbox(403, event_type=identity_events.EVENT_USER_DEACTIVATED, reason="offboard")

    # 端点返回的事件必须与 outbox 存储载荷逐字节一致（逐字段透传 schema v1）
    stored = {event_id: payload for event_id, payload in _published_ordered()}
    returned_payloads: list[dict] = []
    for event_id in _crawl(page_limit=100):
        payload = stored[event_id]
        returned_payloads.append(payload)
        for field in (
            "event_id",
            "event_type",
            "occurred_at",
            "source",
            "subject",
            "tenant_code",
            "previous_state",
            "current_state",
            "reason",
            "schema_version",
        ):
            assert field in payload, f"事件缺少 schema v1 字段 {field}"
        assert payload["event_type"] in identity_events.VALID_EVENT_TYPES
        assert payload["schema_version"] == identity_events.EVENT_SCHEMA_VERSION
        # subject 嵌套字段齐全
        subject = payload["subject"]
        for field in ("subject_id", "subject_type", "username"):
            assert field in subject, f"subject 缺少 {field}"
        assert isinstance(subject["subject_id"], int)
        assert isinstance(payload["role_codes"], list)
        assert payload["previous_state"] != payload["current_state"]
    assert returned_payloads == [payload for _event_id, payload in _published_ordered()]
    # 本用例写入的四种事件类型均出现在列表中（覆盖 user.provisioned/suspended/restored/deactivated）
    listed_types = {payload["event_type"] for payload in returned_payloads}
    assert identity_events.VALID_EVENT_TYPES.issubset(listed_types)


# ---- 用例：仅返回已 published 事件（pending/failed 不出现） ----

def test_only_published_events_returned() -> None:
    """pending/failed 事件不进入列表（仅 outbox 已 published 事件可被拉取）. """
    published_id = _insert_outbox(500, status=identity_events.EVENT_STATUS_PUBLISHED)
    _insert_outbox(501, status=identity_events.EVENT_STATUS_PENDING, event_id=_unique("pending"))
    _insert_outbox(502, status=identity_events.EVENT_STATUS_FAILED, event_id=_unique("failed"))

    # 全量遍历整条流（既有事件较多，避免单页截断误判）
    returned_ids = _crawl(page_limit=100)
    assert published_id in returned_ids
    for status in (identity_events.EVENT_STATUS_PENDING, identity_events.EVENT_STATUS_FAILED):
        rows = _rows(f"SELECT event_id FROM outbox_events WHERE status = '{status}'")
        for row in rows:
            assert row[0] not in returned_ids, f"status={status} 事件不得出现在列表中"


# ---- 用例：受权 403（读端点沿用 identity:view 权限模型） ----

def test_list_requires_identity_view_permission() -> None:
    """无 identity:view 权限的普通用户 → 403 PERM_FORBIDDEN（admin 通配放行）."""
    denied = _events_list(headers=_viewer_headers())
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == ErrorCode.PERM_FORBIDDEN.value

    allowed = _events_list()
    assert allowed.status_code == 200, allowed.text


# ---- 用例：未知/未 published 游标行为（与契约一致 → 400 PARAM_INVALID） ----

def test_unknown_cursor_returns_400() -> None:
    """cursor 在 outbox_events 中不存在 → 400 PARAM_INVALID（不静默从头部返回）."""
    resp = _events_list(cursor=uuid.uuid4().hex)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert "cursor" in str(resp.json()["detail"])


def test_cursor_referencing_non_published_event_returns_400() -> None:
    """cursor 引用 pending/failed 事件 → 400 PARAM_INVALID（游标仅接受已 published 事件）."""
    pending_id = _insert_outbox(600, status=identity_events.EVENT_STATUS_PENDING)
    resp = _events_list(cursor=pending_id)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == ErrorCode.PARAM_INVALID.value
    assert resp.json()["detail"].get("status") == identity_events.EVENT_STATUS_PENDING
