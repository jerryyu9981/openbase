"""auth 侧边小模块分支补测（覆盖率治理）.

覆盖：
- ``oidc_state``：Redis 读写异常回退进程内、非法 JSON、过期清理；
- ``oidc_logout``：hint/sid/idp-sub 写入降级、非法 JSON、清理异常、jti 一次性；
- ``key_anomaly``：来源 IP 解析、进程内三态告警与冷却/窗口裁剪、Redis 降级、告警落库失败；
- ``role_contract``：锚点配置缺失/损坏回落、权限查询异常与成功映射。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import openbase.modules.auth.key_anomaly as key_anomaly_module
import openbase.modules.auth.oidc_logout as oidc_logout
import openbase.modules.auth.oidc_state as oidc_state
import openbase.modules.auth.role_contract as role_contract
from openbase.core.cache import redis_client
from openbase.modules.auth.key_anomaly import (
    KeyAnomalyTracker,
    report_anomalies,
    resolve_client_ip,
)
from openbase.modules.auth.oidc_logout import OidcLogoutStore
from openbase.modules.auth.oidc_state import OidcStateStore

# 注意：``openbase.settings`` 包属性被 ``openbase/__init__.py`` 覆盖为 Settings 实例，
# 直接用 import-as 会绑定到实例，必须按模块名从 sys.modules 取真实模块对象。
settings_module = importlib.import_module("openbase.settings")


class FakeRedis:
    """可配置故障的最小 Redis 替身."""

    def __init__(self, **behavior: bool | str) -> None:
        self.behavior = behavior
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        if self.behavior.get("set_raises"):
            raise RuntimeError("redis down")
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def get(self, key: str):
        if self.behavior.get("get_raises"):
            raise RuntimeError("redis down")
        return self.store.get(key)

    def getdel(self, key: str):
        if self.behavior.get("getdel_raises"):
            raise RuntimeError("redis down")
        if "getdel_value" in self.behavior:
            return self.behavior["getdel_value"]
        return self.store.pop(key, None)

    def delete(self, *keys: str) -> None:
        if self.behavior.get("delete_raises"):
            raise RuntimeError("redis down")
        for key in keys:
            self.store.pop(key, None)


class FakeAggRedis:
    """Key 异常检测所需的 Redis 聚合替身（计数/集合/冷却）."""

    def __init__(
        self,
        *,
        counters: dict[str, int] | None = None,
        sets: dict[str, set[str]] | None = None,
        cooldown_allowed: bool = True,
    ) -> None:
        self.counters = dict(counters or {})
        self.sets = {key: set(values) for key, values in (sets or {}).items()}
        self.cooldown_allowed = cooldown_allowed

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    def sadd(self, key: str, value: str) -> int:
        self.sets.setdefault(key, set()).add(value)
        return 1

    def scard(self, key: str) -> int:
        return len(self.sets.get(key, set()))

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool | None:
        return True if self.cooldown_allowed else None


# ---- oidc_state ----


def test_oidc_state_redis_failure_fallback_and_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcStateStore(ttl_seconds=60)
    failing = FakeRedis(set_raises=True, getdel_raises=True)
    monkeypatch.setattr(oidc_state.redis_client, "get_client", lambda: failing)

    store.issue("s1", {"nonce": "n1"})
    assert store.consume("s1") == {"nonce": "n1"}
    assert store.consume("s1") is None  # 一次性

    # 过期条目在下次写入前被清理
    store._local["expired"] = (time.monotonic() - 5, {"x": 1})
    store.issue("s2", {"nonce": "n2"})
    assert "expired" not in store._local


def test_oidc_state_invalid_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcStateStore()
    monkeypatch.setattr(
        oidc_state.redis_client,
        "get_client",
        lambda: FakeRedis(getdel_value="not-a-json"),
    )
    assert store.consume("broken") is None


def test_oidc_state_redis_success_and_local_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcStateStore(ttl_seconds=60)
    working = FakeRedis()
    monkeypatch.setattr(oidc_state.redis_client, "get_client", lambda: working)

    store.issue("s1", {"nonce": "n1"})
    assert working.store[oidc_state.STATE_KEY_PREFIX + "s1"]
    assert store.consume("s1") == {"nonce": "n1"}

    # Redis 不可用（None）→ 纯进程内路径
    monkeypatch.setattr(oidc_state.redis_client, "get_client", lambda: None)
    store.issue("s2", {"nonce": "n2"})
    assert store.consume("s2") == {"nonce": "n2"}

    # 进程内过期条目 → 视为未命中
    store._local["expired"] = (time.monotonic() - 5, {"x": 1})
    assert store.consume("expired") is None

    store.clear()
    assert store._local == {}

    # 单例（首次创建 / 复用）
    monkeypatch.setattr(oidc_state, "_state_store", None)
    first = oidc_state.get_state_store()
    assert oidc_state.get_state_store() is first


# ---- oidc_logout ----


def test_oidc_logout_redis_write_failure_and_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcLogoutStore(ttl_seconds=60)
    failing = FakeRedis(set_raises=True, delete_raises=True)
    monkeypatch.setattr(oidc_logout.redis_client, "get_client", lambda: failing)

    store.save_id_token_hint(
        client_id="cid",
        subject="sub-1",
        issuer="https://idp",
        id_token="token-1",
        sid="sid-1",
        idp_subject="idp-1",
    )
    assert store.id_token_hint(client_id="cid", subject="sub-1") == "token-1"
    assert store.id_token_hint(client_id="cid", subject="sub-1", issuer="https://other") == ""
    assert store.subject_for_sid(client_id="cid", sid="sid-1") == "sub-1"
    assert store.subject_for_idp_sub(client_id="cid", idp_subject="idp-1") == "sub-1"

    # 过期条目在写入前被清理
    store._local[f"{oidc_logout.HINT_KEY_PREFIX}expired:expired"] = (
        time.monotonic() - 5,
        "stale",
    )
    store.save_id_token_hint(
        client_id="cid", subject="sub-2", issuer="https://idp", id_token="token-2"
    )
    assert f"{oidc_logout.HINT_KEY_PREFIX}expired:expired" not in store._local

    # 清理：Redis delete 异常仅告警，进程内仍删除
    store.clear(client_id="cid", subject="sub-1", sid="sid-1")
    assert store.id_token_hint(client_id="cid", subject="sub-1") == ""


def test_oidc_logout_invalid_json_and_read_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcLogoutStore()
    monkeypatch.setattr(oidc_logout.redis_client, "get_client", lambda: FakeRedis(get_raises=True))

    key = f"{oidc_logout.HINT_KEY_PREFIX}cid:sub"
    store._local[key] = (time.monotonic() + 60, "not-json")
    assert store.id_token_hint(client_id="cid", subject="sub") == ""

    store._local[key] = (time.monotonic() + 60, json.dumps([1, 2]))
    assert store.id_token_hint(client_id="cid", subject="sub") == ""


def test_oidc_logout_jti_fallback_is_one_time(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcLogoutStore(ttl_seconds=60)
    monkeypatch.setattr(oidc_logout.redis_client, "get_client", lambda: FakeRedis(set_raises=True))

    assert store.consume_jti(client_id="cid", jti="j1") is True
    assert store.consume_jti(client_id="cid", jti="j1") is False

    # 已过期记录 → 视为首次
    key = f"{oidc_logout.JTI_KEY_PREFIX}cid:old"
    store._local[key] = (time.monotonic() - 1, "1")
    assert store.consume_jti(client_id="cid", jti="old") is True


def test_oidc_logout_redis_success_and_local_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    store = OidcLogoutStore(ttl_seconds=60)
    working = FakeRedis()
    monkeypatch.setattr(oidc_logout.redis_client, "get_client", lambda: working)

    # Redis 写入成功直接返回；读取命中 Redis 值
    store.save_id_token_hint(
        client_id="cid", subject="sub", issuer="https://idp", id_token="token", sid="sid"
    )
    assert store.id_token_hint(client_id="cid", subject="sub") == "token"
    assert store.subject_for_sid(client_id="cid", sid="sid") == "sub"

    # Redis 不可用（None）→ 纯进程内路径
    monkeypatch.setattr(oidc_logout.redis_client, "get_client", lambda: None)
    store.clear_all()
    store.save_id_token_hint(
        client_id="cid", subject="sub-2", issuer="https://idp", id_token="token-2"
    )
    assert store.id_token_hint(client_id="cid", subject="sub-2") == "token-2"

    # 无 sid 清理
    store.clear(client_id="cid", subject="sub-2")
    assert store.id_token_hint(client_id="cid", subject="sub-2") == ""

    # 进程内过期条目 → 视为未命中
    expired_key = f"{oidc_logout.HINT_KEY_PREFIX}cid:old"
    store._local[expired_key] = (time.monotonic() - 1, "stale")
    assert store.id_token_hint(client_id="cid", subject="old") == ""

    assert store.consume_jti(client_id="cid", jti="j2") is True
    assert store.consume_jti(client_id="cid", jti="j2") is False

    # 单例
    monkeypatch.setattr(oidc_logout, "_logout_store", None)
    first = oidc_logout.get_logout_store()
    assert oidc_logout.get_logout_store() is first


# ---- key_anomaly ----


def _settings(**overrides) -> SimpleNamespace:
    values = {
        "key_anomaly_enabled": True,
        "key_anomaly_window_seconds": 60.0,
        "key_anomaly_alert_cooldown_seconds": 0.0,
        "key_anomaly_max_ips": 1,
        "key_anomaly_rate_per_minute": 1,
        "key_anomaly_trust_forwarded_for": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_key_anomaly_resolve_client_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings_module, "get_settings", lambda: _settings(key_anomaly_trust_forwarded_for=True)
    )
    request = SimpleNamespace(
        headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
        client=SimpleNamespace(host="9.9.9.9"),
    )
    assert resolve_client_ip(request) == "1.2.3.4"

    # 采信 XFF 但头为空 → 回落到连接层
    empty_forwarded = SimpleNamespace(
        headers={"X-Forwarded-For": ""}, client=SimpleNamespace(host="9.9.9.9")
    )
    assert resolve_client_ip(empty_forwarded) == "9.9.9.9"

    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())
    assert resolve_client_ip(request) == "9.9.9.9"

    # 无 client 属性 → 空串
    assert resolve_client_ip(SimpleNamespace(headers={})) == ""


def test_key_anomaly_ip_prefix_edges() -> None:
    assert key_anomaly_module.ip_prefix("") == ""
    assert key_anomaly_module.ip_prefix("192.168.1.10") == "192.168"
    assert key_anomaly_module.ip_prefix("2001:db8:85a3:1:2:3:4:5") == "2001:db8:85a3:1"


def test_key_anomaly_disabled_and_empty_key(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = KeyAnomalyTracker()
    monkeypatch.setattr(
        settings_module, "get_settings", lambda: _settings(key_anomaly_enabled=False)
    )
    assert tracker.observe("k1", "10.0.0.1", now=1.0) == []

    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())
    assert tracker.observe("", "10.0.0.1", now=1.0) == []


def test_key_anomaly_redis_aggregation_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())
    tracker = KeyAnomalyTracker()
    rate_key = f"{key_anomaly_module._REDIS_PREFIX}:rate:k1"
    ips_key = f"{key_anomaly_module._REDIS_PREFIX}:ips:k1"
    agg = FakeAggRedis(counters={rate_key: 1}, sets={ips_key: {"10.0.0.1"}})
    monkeypatch.setattr(redis_client, "get_client", lambda: agg)

    alerts = tracker.observe("k1", "11.1.1.1")
    assert {item["kind"] for item in alerts} == {
        "rate_spike",
        "ip_prefix_change",
        "multi_ip",
    }
    assert agg.sets[ips_key] == {"10.0.0.1", "11.1.1.1"}
    assert tracker._states == {}  # Redis 路径不写进程内状态


def test_key_anomaly_redis_cooldown_and_empty_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())
    tracker = KeyAnomalyTracker()
    rate_prefix = f"{key_anomaly_module._REDIS_PREFIX}:rate:"

    # 冷却窗口内（SET NX 返回 None）→ 同类告警被抑制
    cooldown_agg = FakeAggRedis(counters={f"{rate_prefix}k1": 5}, cooldown_allowed=False)
    monkeypatch.setattr(redis_client, "get_client", lambda: cooldown_agg)
    assert tracker.observe("k1", "10.0.0.1") == []

    # 空 IP 仅参与速率计数，不做 IP 维度判定
    no_ip_agg = FakeAggRedis(counters={f"{rate_prefix}k2": 1})
    monkeypatch.setattr(redis_client, "get_client", lambda: no_ip_agg)
    alerts = tracker.observe("k2", "")
    assert [item["kind"] for item in alerts] == ["rate_spike"]


def test_key_anomaly_first_redis_count_and_disabled_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings_module,
        "get_settings",
        lambda: _settings(key_anomaly_rate_per_minute=0, key_anomaly_max_ips=0),
    )
    agg = FakeAggRedis()
    monkeypatch.setattr(redis_client, "get_client", lambda: agg)
    rate_key = f"{key_anomaly_module._REDIS_PREFIX}:rate:k1"

    # 首次计数触发 EXPIRE；限速关闭 → 不判定 rate_spike
    assert KeyAnomalyTracker().observe("k1", "10.0.0.1") == []
    assert agg.counters[rate_key] == 1


def test_key_anomaly_redis_absent_and_process_empty_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())

    # get_client 返回 None → 直接走进程内窗口（无 Redis 可用）
    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    tracker = KeyAnomalyTracker()
    assert tracker.observe("k1", "10.0.0.1") == []

    # 空 IP：进程内窗口仅计数，不做 IP 维度判定
    other = KeyAnomalyTracker()
    assert other.observe("k2", "", now=100.0) == []
    tracker.reset()
    assert tracker._states == {}
    assert key_anomaly_module.get_tracker() is key_anomaly_module._tracker


def test_key_anomaly_process_window_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())
    tracker = KeyAnomalyTracker()

    assert tracker.observe("k1", "10.0.0.1", now=100.0) == []
    alerts = tracker.observe("k1", "11.1.1.1", now=100.5)
    kinds = {item["kind"] for item in alerts}
    assert {"rate_spike", "ip_prefix_change", "multi_ip"} <= kinds

    # 冷却窗口内同类告警被抑制
    assert tracker.observe("k1", "12.2.2.2", now=100.6) == []

    # 越过窗口/速率窗口后：状态裁剪与速率重置
    assert tracker.observe("k1", "12.2.2.2", now=200.0) == []


def test_key_anomaly_capacity_guard_and_redis_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module, "get_settings", lambda: _settings())
    monkeypatch.setattr(key_anomaly_module, "_MAX_TRACKED_KEYS", 1)
    tracker = KeyAnomalyTracker()
    tracker.observe("k1", "10.0.0.1", now=100.0)
    tracker.observe("k2", "10.0.0.2", now=100.1)
    assert list(tracker._states) == ["k2"]

    def _redis_down():
        raise RuntimeError("redis down")

    monkeypatch.setattr(redis_client, "get_client", _redis_down)
    assert tracker.observe("k3", "10.0.0.3") == []


def test_report_anomalies_skips_empty_and_survives_db_failure() -> None:
    class _BrokenSession:
        def add(self, obj) -> None:
            self.obj = obj

        async def commit(self) -> None:
            raise RuntimeError("db down")

        async def rollback(self) -> None:
            raise RuntimeError("rollback down")

    asyncio.run(
        report_anomalies(_BrokenSession(), credential={"id": "k1"}, anomalies=[])
    )
    asyncio.run(
        report_anomalies(
            _BrokenSession(),
            credential={"id": "k1", "name": "n", "tenant_code": "t"},
            anomalies=[{"kind": "multi_ip", "ip": "1.1.1.1"}],
        )
    )


# ---- role_contract ----


def test_role_contract_anchor_config_fallbacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "absent.json"
    monkeypatch.setattr(role_contract, "_CONFIG_PATH", missing)
    assert role_contract._load_anchor_config() == {}

    broken = tmp_path / "broken.json"
    broken.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(role_contract, "_CONFIG_PATH", broken)
    assert role_contract._load_anchor_config() == {}

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[1, 2]", encoding="utf-8")
    monkeypatch.setattr(role_contract, "_CONFIG_PATH", malformed)
    assert role_contract._load_anchor_config() == {}
    assert role_contract.build_role_contract()["source"] == "openbase"

    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps({"anchors": {"admin": "manage"}}), encoding="utf-8")
    monkeypatch.setattr(role_contract, "_CONFIG_PATH", valid)
    assert role_contract._load_anchor_config() == {"anchors": {"admin": "manage"}}
    contract = role_contract.build_role_contract({"admin": ["user.read"]})
    assert contract["roles"][0]["permissions"] == ["user.read"]


def test_role_contract_permission_query_paths() -> None:
    class _BrokenSession:
        async def execute(self, statement):
            raise RuntimeError("db down")

    assert asyncio.run(role_contract.load_role_permissions(_BrokenSession())) is None

    class _Result:
        def all(self):
            return [("admin", "user.read"), ("admin", "user.write"), ("viewer", "user.read")]

    class _Session:
        async def execute(self, statement):
            return _Result()

    mapping = asyncio.run(role_contract.load_role_permissions(_Session()))
    assert mapping == {"admin": ["user.read", "user.write"], "viewer": ["user.read"]}
