"""E1-7 服务 Key 异常检测与告警测试."""

import pytest

from openbase.modules.auth.key_anomaly import (
    KIND_IP_PREFIX_CHANGE,
    KIND_MULTI_IP,
    KIND_RATE_SPIKE,
    KeyAnomalyTracker,
    ip_prefix,
    report_anomalies,
)


@pytest.fixture(autouse=True)
def _clean_tracker():
    """每个用例前后清理全局检测器状态."""
    from openbase.modules.auth.key_anomaly import get_tracker

    get_tracker().reset()
    yield
    get_tracker().reset()


def _kinds(alerts: list[dict]) -> list[str]:
    """提取告警类型列表."""
    return [item["kind"] for item in alerts]


def test_ip_prefix_normalization():
    """IPv4 取前两段、IPv6 取前四组（异地近似键）."""
    assert ip_prefix("10.20.30.40") == "10.20"
    assert ip_prefix("fd00:1:2:3:4:5:6:7") == "fd00:1:2:3"
    assert ip_prefix("") == ""


def test_multi_ip_threshold_alert():
    """窗口内不同 IP 数超阈值 → multi_ip 告警."""
    tracker = KeyAnomalyTracker()
    alerts = []
    for index, ip in enumerate(["10.10.0.1", "10.10.0.2", "10.10.0.3", "10.10.0.4"]):
        alerts.extend(tracker.observe("key-1", ip, now=1000.0 + index))
    assert KIND_MULTI_IP in _kinds(alerts)


def test_prefix_change_alert_marks_remote_login():
    """来源网段跳变 → ip_prefix_change（异地登录近似判定）."""
    tracker = KeyAnomalyTracker()
    first = tracker.observe("key-1", "10.1.2.3", now=1000.0)
    second = tracker.observe("key-1", "192.168.5.6", now=1001.0)
    assert first == []
    assert _kinds(second) == [KIND_IP_PREFIX_CHANGE]


def test_rate_spike_alert_and_cooldown(monkeypatch):
    """单分钟调用量超阈值 → rate_spike；冷却窗口内不重复告警."""
    from openbase.settings import get_settings

    monkeypatch.setattr(get_settings(), "key_anomaly_rate_per_minute", 2)
    tracker = KeyAnomalyTracker()
    alerts = []
    for offset in range(3):
        alerts.extend(tracker.observe("key-1", "10.1.0.1", now=1000.0 + offset))
    assert _kinds(alerts).count(KIND_RATE_SPIKE) == 1

    # 冷却期内继续超阈值不再重复（同窗口计数继续增长）
    for offset in range(3, 6):
        tracker.observe("key-1", "10.1.0.1", now=1000.0 + offset)
    assert tracker._states["key-1"]["alerts"][KIND_RATE_SPIKE] == 1002.0


def test_disabled_switch_returns_no_alert(monkeypatch):
    """关闭检测开关 → 不产生任何告警."""
    from openbase.settings import get_settings

    monkeypatch.setattr(get_settings(), "key_anomaly_enabled", False)
    tracker = KeyAnomalyTracker()
    assert tracker.observe("key-1", "10.1.0.1", now=1000.0) == []


class _FakeSession:
    """记录 add/commit/rollback 的最小会话桩."""

    def __init__(self, fail: bool = False) -> None:
        self.added: list = []
        self.committed = False
        self.rolled_back = False
        self._fail = fail

    def add(self, record) -> None:
        self.added.append(record)

    async def commit(self) -> None:
        if self._fail:
            raise RuntimeError("commit failed")
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_report_anomalies_writes_audit_log():
    """告警落审计（动作码 + Key 元数据，不含明文）."""
    session = _FakeSession()
    await report_anomalies(
        session,
        credential={"id": "key-1", "name": "edge", "tenant_code": "tenant-1"},
        anomalies=[{"kind": KIND_MULTI_IP, "key_id": "key-1", "ip": "10.1.0.1", "detail": {}}],
        request_id="req-1",
    )
    assert session.committed is True
    record = session.added[0]
    assert record.action == "auth.service_key.anomaly"
    assert record.resource_id == "key-1"
    assert record.detail["anomalies"][0]["kind"] == KIND_MULTI_IP


@pytest.mark.asyncio
async def test_report_anomalies_swallows_persist_failure():
    """审计写入失败 → 回滚且不抛出（不阻断认证）."""
    session = _FakeSession(fail=True)
    await report_anomalies(
        session,
        credential={"id": "key-2"},
        anomalies=[{"kind": KIND_RATE_SPIKE, "key_id": "key-2", "ip": "10.2.0.1", "detail": {}}],
    )
    assert session.rolled_back is True
