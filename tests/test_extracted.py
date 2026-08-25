"""抽取增强模块测试：config 三级配置 / tenant 配额 / errors registry / observability 业务指标."""

from openbase.core.errors import (
    ErrorCode,
    get_error_definition,
    list_error_codes,
    register_error_code,
)
from openbase.modules.config import ConfigLevel, ConfigStore
from openbase.modules.observability import BusinessMetrics
from openbase.modules.tenant import QuotaChecker

# ---- config 三级配置（来源: OpenRAG config_center） ----


def test_config_level_precedence_user_over_tenant():
    """USER 级覆盖 TENANT 级覆盖 SYSTEM 级."""
    ConfigStore.set("theme", {"color": "blue"}, ConfigLevel.SYSTEM)
    ConfigStore.set("theme", {"color": "red"}, ConfigLevel.TENANT)
    ConfigStore.set("theme", {"color": "green"}, ConfigLevel.USER)
    assert ConfigStore.get("theme") == {"color": "green"}
    assert ConfigStore.get("theme", ConfigLevel.TENANT) == {"color": "red"}
    assert ConfigStore.get("theme", ConfigLevel.SYSTEM) == {"color": "blue"}


def test_config_level_scoped_get():
    """指定级别取值不合并."""
    ConfigStore.set("scoped.key", "tenant-value", ConfigLevel.TENANT)
    assert ConfigStore.get("scoped.key", ConfigLevel.TENANT) == "tenant-value"
    assert ConfigStore.get("scoped.key", ConfigLevel.SYSTEM) is None


def test_config_change_event_notification():
    """配置变更触发监听器（热加载）."""
    events = []

    def listener(key: str, value) -> None:
        events.append((key, value))

    ConfigStore.on_change(listener)
    ConfigStore.set("event.key", {"on": True})
    assert ("event.key", {"on": True}) in events


def test_config_rollback_system_level():
    """回滚写入 SYSTEM 级，可被合并取值读到."""
    ConfigStore.set("rb.key", 1)
    ConfigStore.set("rb.key", 2)
    ConfigStore.rollback("rb.key", 1)
    assert ConfigStore.get("rb.key") == 1


# ---- tenant 配额检查（来源: OpenMemory quota_checker） ----


def test_quota_checker_allow_within_limit():
    QuotaChecker.set_quota("t1", "users", 3)
    assert QuotaChecker.check("t1", "users")
    assert QuotaChecker.consume("t1", "users")
    assert QuotaChecker.consume("t1", "users")
    assert QuotaChecker.consume("t1", "users")
    # 超限
    assert not QuotaChecker.consume("t1", "users")
    assert QuotaChecker.usage("t1", "users") == 3


def test_quota_checker_unlimited():
    QuotaChecker.set_quota("t2", "storage", -1)
    assert QuotaChecker.consume("t2", "storage")
    assert QuotaChecker.check("t2", "storage")


def test_quota_checker_no_config_allowed():
    assert QuotaChecker.check("t-unknown", "users")


# ---- errors registry（来源: DPS error_code_registry） ----


def test_register_and_query_extension_code():
    register_error_code("BIZ_CUSTOM_FAIL", "custom business failure", 400)
    definition = get_error_definition("BIZ_CUSTOM_FAIL")
    assert definition == {"message": "custom business failure", "status_code": 400}


def test_builtin_code_queryable():
    definition = get_error_definition(ErrorCode.AUTH_UNAUTHORIZED.value)
    assert definition is not None
    assert definition["status_code"] == 401


def test_list_error_codes_contains_builtin_and_extension():
    register_error_code("BIZ_CUSTOM_FAIL2", "custom2", 400)
    codes = list_error_codes()
    assert "AUTH_401" in codes
    assert "BIZ_CUSTOM_FAIL2" in codes


# ---- observability 业务指标（来源: OpenMemory business_metrics） ----


def test_business_metrics_incr_and_snapshot():
    BusinessMetrics.incr("auth.login.success")
    BusinessMetrics.incr("auth.login.success")
    BusinessMetrics.incr("mcp.tools.called")
    snapshot = BusinessMetrics.snapshot()
    assert snapshot["counters"]["auth.login.success"] == 2
    assert snapshot["counters"]["mcp.tools.called"] == 1


def test_business_metrics_latency():
    BusinessMetrics.observe_latency("auth.login.duration", 0.12)
    BusinessMetrics.observe_latency("auth.login.duration", 0.08)
    snapshot = BusinessMetrics.snapshot()
    assert snapshot["latency_samples"]["auth.login.duration"] == 2
