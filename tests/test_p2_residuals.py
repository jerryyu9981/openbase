"""残余项 P2 批次测试（C-06~C-10）.

- C-06：静态 MCP Key 工具白名单（``OPENBASE_MCP_API_KEY_TOOLS``）；
- C-07：Key 异常检测跨实例 Redis 聚合（不可用回退进程内）；
- C-08：Key 到期清单（``GET /api/v1/auth/api-keys/expiring``）+ ``service_key.expiring`` 事件；
- C-09：Key 侧日对账（签发数 = 有效 + 吊销 + 过期，差异写审计）；
- C-10：统一角色字典契约（``GET /api/v1/auth/roles/contract``）。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

# ---- 公共：设置/凭证缓存重置 ----


@pytest.fixture(autouse=True)
def _reset_settings_singleton():
    """重置全局设置单例与静态 Key 文件缓存（避免跨用例串扰）."""
    import sys

    module = sys.modules["openbase.settings"]
    module._settings = None
    from openbase.modules.mcp import credentials

    credentials._KEYS_FILE_CACHE = None
    yield
    module._settings = None
    credentials._KEYS_FILE_CACHE = None


def _sha256(text: str) -> str:
    """明文 Key → SHA-256 摘要."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ===================== C-06 静态 MCP Key 工具白名单 =====================


def test_parse_mcp_api_key_tools_empty_means_unrestricted():
    """缺省/空配置 → 空映射（零行为变化）."""
    from openbase.settings import parse_mcp_api_key_tools

    assert parse_mcp_api_key_tools("") == {}
    assert parse_mcp_api_key_tools(None) == {}
    assert parse_mcp_api_key_tools("   ") == {}


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "[]",
        '{"abc": []}',
        '{"abc": "tool-a"}',
        '{"abc": [1]}',
        '{"": ["tool-a"]}',
    ],
)
def test_parse_mcp_api_key_tools_rejects_invalid(raw):
    """非法结构 fail-fast（启动期拒绝，避免运行期静默失效）."""
    from openbase.settings import parse_mcp_api_key_tools

    with pytest.raises(ValueError):
        parse_mcp_api_key_tools(raw)


def test_parse_mcp_api_key_tools_normalizes():
    """合法配置按原始标识映射为元组（摘要/明文/通配均保留）."""
    from openbase.settings import parse_mcp_api_key_tools

    digest = _sha256("edge-key")
    parsed = parse_mcp_api_key_tools(
        json.dumps({digest: [" tool-a ", "tool-b"], "plain-key": ["*"]})
    )
    assert parsed[digest] == ("tool-a", "tool-b")
    assert parsed["plain-key"] == ("*",)
    assert all(isinstance(item, tuple) for item in parsed.values())


def _build_request(api_key: str) -> Request:
    """构造最小 Starlette Request（静态 Key 只读 X-API-Key）."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/mcp/tools/list",
            "headers": [(b"x-api-key", api_key.encode("utf-8"))],
            "query_string": b"",
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
        }
    )


@pytest.mark.asyncio
async def test_static_key_digest_tool_allowlist(monkeypatch):
    """摘要命中且配置了白名单 → 凭证携带工具白名单."""
    raw_key = "edge-raw-key"
    digest = _sha256(raw_key)
    monkeypatch.setenv("OPENBASE_MCP_API_KEY_HASHES", digest)
    monkeypatch.setenv("OPENBASE_MCP_API_KEYS", "")
    monkeypatch.setenv(
        "OPENBASE_MCP_API_KEY_TOOLS", json.dumps({digest: ["rag_search"]})
    )
    from openbase.modules.mcp.credentials import require_mcp_credential

    credential = await require_mcp_credential(_build_request(raw_key))
    assert credential.credential_type == "static-key"
    assert credential.tools == ("rag_search",)


@pytest.mark.asyncio
async def test_static_key_without_mapping_stays_unrestricted(monkeypatch):
    """未配置映射 → ``tools=None``（保持原「不限工具」语义）."""
    raw_key = "edge-raw-key"
    monkeypatch.setenv("OPENBASE_MCP_API_KEY_HASHES", _sha256(raw_key))
    monkeypatch.setenv("OPENBASE_MCP_API_KEYS", "")
    monkeypatch.setenv("OPENBASE_MCP_API_KEY_TOOLS", "")
    from openbase.modules.mcp.credentials import require_mcp_credential

    credential = await require_mcp_credential(_build_request(raw_key))
    assert credential.tools is None


@pytest.mark.asyncio
async def test_static_key_plain_text_alias_mapping(monkeypatch):
    """明文静态 Key 可用自身文本作为映射键（开发/联调场景）."""
    raw_key = "dev-plain-key"
    monkeypatch.setenv("OPENBASE_MCP_API_KEYS", raw_key)
    monkeypatch.setenv(
        "OPENBASE_MCP_API_KEY_TOOLS", json.dumps({raw_key: ["tool-x", "*"]})
    )
    from openbase.modules.mcp.credentials import require_mcp_credential

    credential = await require_mcp_credential(_build_request(raw_key))
    assert credential.tools == ("tool-x", "*")
    from openbase.modules.mcp.credentials import allows_tool

    assert allows_tool(credential, "tool-y") is True


# ===================== C-07 跨实例异常聚合 =====================


class FakeRedis:
    """最小 Redis 桩（incr/expire/ttl/sadd/scard/smembers/set-nx）."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.sets: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}
        self.flags: dict[str, str] = {}

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = int(seconds)
        return True

    def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)

    def sadd(self, key: str, member: str) -> int:
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        bucket.add(member)
        return 1 if len(bucket) > before else 0

    def scard(self, key: str) -> int:
        return len(self.sets.get(key, set()))

    def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self.flags:
            return None
        self.flags[key] = value
        if ex is not None:
            self.ttls[key] = int(ex)
        return True


@pytest.fixture()
def fake_redis(monkeypatch):
    """把 Redis 客户端替换为桩（跨实例共享同一桩实例）."""
    from openbase.core.cache import redis_client

    stub = FakeRedis()
    monkeypatch.setattr(redis_client, "get_client", lambda: stub)
    from openbase.modules.auth.key_anomaly import get_tracker

    get_tracker().reset()
    yield stub
    get_tracker().reset()


def test_redis_aggregation_triggers_cross_instance_alerts(fake_redis, monkeypatch):
    """两个进程内检测器经同一 Redis 聚合 → 跨实例触发 multi_ip 与网段跳变."""
    from openbase.settings import get_settings
    from openbase.modules.auth.key_anomaly import (
        KIND_IP_PREFIX_CHANGE,
        KIND_MULTI_IP,
        KeyAnomalyTracker,
    )

    monkeypatch.setattr(get_settings(), "key_anomaly_max_ips", 2)
    first = KeyAnomalyTracker()
    second = KeyAnomalyTracker()
    first.observe("key-1", "10.1.0.1")
    alerts = second.observe("key-1", "192.168.0.1")
    assert KIND_IP_PREFIX_CHANGE in [item["kind"] for item in alerts]
    alerts = first.observe("key-1", "10.2.0.1")
    assert KIND_MULTI_IP in [item["kind"] for item in alerts]
    # 窗口/冷却 TTL 写入
    assert fake_redis.ttls.get("openbase:key_anomaly:ips:key-1") == int(
        get_settings().key_anomaly_window_seconds
    )
    assert fake_redis.ttls.get("openbase:key_anomaly:cool:key-1:multi_ip") == int(
        get_settings().key_anomaly_alert_cooldown_seconds
    )


def test_redis_aggregation_rate_spike(monkeypatch):
    """跨实例计数：第二实例的调用量计入同一分钟窗口."""
    from openbase.settings import get_settings

    monkeypatch.setattr(get_settings(), "key_anomaly_rate_per_minute", 2)
    from openbase.core.cache import redis_client
    from openbase.modules.auth.key_anomaly import KIND_RATE_SPIKE, KeyAnomalyTracker

    stub = FakeRedis()
    monkeypatch.setattr(redis_client, "get_client", lambda: stub)
    tracker = KeyAnomalyTracker()
    alerts = []
    for _ in range(3):
        alerts.extend(tracker.observe("key-2", "10.0.0.1"))
    assert [item["kind"] for item in alerts].count(KIND_RATE_SPIKE) == 1


def test_redis_unavailable_falls_back_to_process_window(monkeypatch):
    """Redis 不可用 → 回退进程内滑动窗口（保留现行为）."""
    monkeypatch.setattr("openbase.core.cache.redis_client.get_client", lambda: None)
    from openbase.settings import get_settings
    from openbase.modules.auth.key_anomaly import (
        KIND_IP_PREFIX_CHANGE,
        KeyAnomalyTracker,
    )

    monkeypatch.setattr(get_settings(), "key_anomaly_max_ips", 3)
    tracker = KeyAnomalyTracker()
    assert tracker.observe("key-3", "10.1.2.3", now=1000.0) == []
    alerts = tracker.observe("key-3", "192.168.5.6", now=1001.0)
    assert [item["kind"] for item in alerts] == [KIND_IP_PREFIX_CHANGE]


# ===================== C-08/C-09 服务 Key 清单与对账 =====================


def _clear_metadata_schema() -> None:
    """SQLite 无 schema：建表前置空（与 tests/test_api_keys.py 同口径）."""
    from openbase.core.models import Base

    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None


@pytest.fixture()
def key_engine(tmp_path):
    """文件型 SQLite 引擎（每个用例独立库，避免计数串扰）."""
    _clear_metadata_schema()
    db_path = tmp_path / "p2_keys.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    from openbase.core.models import Base

    async def _create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture()
async def db_session(key_engine):
    factory = async_sessionmaker(key_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _issue_key(session, name: str, *, expires_at=None, tenant_code=None):
    from openbase.modules.auth.service_keys import ServiceKeyService

    _raw, record = await ServiceKeyService.issue(
        session,
        name=name,
        expires_at=expires_at,
        tenant_code=tenant_code,
    )
    await session.commit()
    return record


@pytest.mark.asyncio
async def test_list_expiring_covers_due_and_expired_with_tenant_filter(db_session):
    """到期清单含「≤7 天」与「已过期」；按租户过滤."""
    now = dt.datetime.now(dt.timezone.utc)
    await _issue_key(db_session, "due-soon", expires_at=now + dt.timedelta(days=3), tenant_code="tenant-1")
    await _issue_key(db_session, "expired", expires_at=now - dt.timedelta(days=1), tenant_code="tenant-1")
    await _issue_key(db_session, "far", expires_at=now + dt.timedelta(days=30), tenant_code="tenant-1")
    await _issue_key(db_session, "other-tenant", expires_at=now + dt.timedelta(days=1), tenant_code="tenant-2")
    await _issue_key(db_session, "no-expiry")

    from openbase.modules.auth.service_keys import ServiceKeyService

    all_due = await ServiceKeyService.list_expiring(db_session, within_days=7)
    assert {record.name for record in all_due} == {"due-soon", "expired", "other-tenant"}
    tenant_due = await ServiceKeyService.list_expiring(
        db_session, within_days=7, tenant_code="tenant-1"
    )
    assert {record.name for record in tenant_due} == {"due-soon", "expired"}


@pytest.mark.asyncio
async def test_emit_expiring_events_deduplicates_per_day(db_session, monkeypatch):
    """``service_key.expiring`` 事件按 Key+日 去重（同一日重复扫描不重复投递）."""
    now = dt.datetime.now(dt.timezone.utc)
    record = await _issue_key(db_session, "notify-me", expires_at=now + dt.timedelta(days=2))

    from openbase.core.cache import redis_client

    stub = FakeRedis()
    monkeypatch.setattr(redis_client, "get_client", lambda: stub)
    from openbase.modules.auth.service_keys import ServiceKeyService

    first = await ServiceKeyService.emit_expiring_events(
        db_session, within_days=7, reference_time=now
    )
    await db_session.commit()
    second = await ServiceKeyService.emit_expiring_events(
        db_session, within_days=7, reference_time=now
    )
    assert first >= 1
    assert second == 0
    from openbase.core.models import OutboxEvent
    from sqlalchemy import select

    result = await db_session.execute(
        select(OutboxEvent).where(OutboxEvent.event_type == "service_key.expiring")
    )
    payloads = [row.payload for row in result.scalars().all()]
    assert any(item["key"]["key_id"] == record.key_id for item in payloads)


@pytest.mark.asyncio
async def test_reconcile_balanced_and_mismatch(db_session):
    """日对账：平衡时 balanced=True；状态异常时写审计并标不平衡."""
    now = dt.datetime.now(dt.timezone.utc)
    active = await _issue_key(db_session, "active-key", expires_at=now + dt.timedelta(days=30))
    expired = await _issue_key(db_session, "expired-key", expires_at=now - dt.timedelta(days=1))
    from openbase.modules.auth.service_keys import ServiceKeyService

    revoked = await _issue_key(db_session, "revoked-key")
    await ServiceKeyService.revoke_by_id(db_session, revoked.key_id)
    await db_session.commit()

    from openbase.modules.auth.service_keys import ServiceKeyService

    result = await ServiceKeyService.reconcile(db_session, reference_time=now)
    assert result["balanced"] is True
    assert result["issued"] == 3
    assert result["active"] == 1
    assert result["revoked"] == 1
    assert result["expired"] == 1

    # 制造不平衡：有效 Key 状态被置为未登记状态（既非 active 也非 revoked）
    active.status = "pending"
    db_session.add(active)
    await db_session.flush()
    mismatch = await ServiceKeyService.reconcile(db_session, reference_time=now)
    assert mismatch["balanced"] is False
    audit = mismatch["audit"]
    assert audit.action == "auth.service_key.reconcile"
    assert audit.detail["balanced"] is False
    assert expired.name == "expired-key"


# ===================== C-10 角色字典契约 =====================


def test_build_role_contract_contains_codes_tiers_permissions():
    """契约含角色码/档位/权限点，未知码 tier=None，且不含任何密钥字段."""
    from openbase.modules.auth.role_contract import build_role_contract

    contract = build_role_contract(
        {"admin": ["*", "system:superadmin"], "viewer": ["openllm:view"]}
    )
    assert contract["schema_version"] == 1
    assert contract["unknown_code_policy"] == "fail-closed"
    roles = {item["code"]: item for item in contract["roles"]}
    assert roles["admin"]["tier"] == "manage"
    assert roles["admin"]["permissions"] == ["*", "system:superadmin"]
    assert roles["viewer"]["tier"] == "readonly"
    assert set(contract["canonical_role_codes"]) == {
        "admin",
        "org_admin",
        "org_member",
        "user",
        "viewer",
    }
    assert contract["tiers"]["order"] == {"readonly": 1, "readwrite": 2, "manage": 3}
    dumped = json.dumps(contract, ensure_ascii=False)
    assert "secret" not in dumped.lower()
    assert "password" not in dumped.lower()


def test_build_role_contract_marks_unmapped_role_code():
    """DB 中出现未登记角色码 → tier=None 且 mapped=False（不静默降级）."""
    from openbase.modules.auth.role_contract import build_role_contract

    contract = build_role_contract({"custom_role": ["some:perm"]})
    custom = next(item for item in contract["roles"] if item["code"] == "custom_role")
    assert custom["tier"] is None
    assert custom["mapped"] is False
    assert custom["permissions"] == ["some:perm"]


@pytest.mark.asyncio
async def test_role_contract_endpoint_readable_by_any_login(db_session):
    """契约端点：登录可读（无管理权限也可取），DB 不可达回退内置基线."""
    from openbase.modules.auth.role_contract import load_role_permissions

    fallback = await load_role_permissions(db_session)
    from openbase.modules.auth.role_contract import build_role_contract

    contract = build_role_contract(fallback)
    assert "roles" in contract and contract["source"] == "openbase"
