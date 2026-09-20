"""settings 配置驱动测试."""

import importlib
import json
import logging

import pytest

from openbase.settings import AVAILABLE_MODULES, Settings

# 注意：`openbase.settings` 模块名在包 __init__ 中被 Settings 实例遮蔽
# （openbase/__init__.py: settings = get_settings()），故用 importlib 显式取模块对象，
# 以便直接测试模块级私有解析函数（_resolve_db_url / _resolve_redis_url）。
settings_module = importlib.import_module("openbase.settings")


def test_enable_module():
    s = Settings()
    s.enable_module("auth")
    assert s.is_enabled("auth")
    assert "auth" in s.enabled_modules


def test_disable_module():
    s = Settings()
    s.enable_module("auth")
    s.enable_module("tenant")
    s.disable_module("auth")
    assert not s.is_enabled("auth")
    assert s.is_enabled("tenant")


def test_unknown_module_raises():
    s = Settings()
    with pytest.raises(ValueError, match="未知模块"):
        s.enable_module("not_exists")


def test_enabled_modules_order_follows_registry():
    s = Settings()
    s.enable_module("notify")
    s.enable_module("auth")
    # 保持 AVAILABLE_MODULES 注册顺序
    assert s.enabled_modules.index("auth") < s.enabled_modules.index("notify")


def test_dps_upstream_defaults_aligned_to_source_port():
    """P0-3（DPS 端口对齐）：dps_upstream_base 默认对齐 DPS 源码 api_port=8000.

    DPS 源码 src/config.py：API_PORT 默认 8000（main.py REST 入口）；
    rest_api.app/MCP 部署入口为 8013（Dockerfile/docker-compose），
    真实部署端口由 OPENBASE_DPS_UPSTREAM_BASE 环境变量覆盖。
    """
    s = Settings()
    assert s.dps_upstream_base == "http://127.0.0.1:8000"
    # 健康探活默认开启（interval 秒内仅探测一次，防止端口错配静默转发失败）
    assert s.dps_health_check_enabled is True
    assert s.dps_health_interval == 30.0


def test_dps_upstream_base_overridable_by_env(monkeypatch):
    """真实部署（如本地编排将 DPS 置于 8030）经环境变量覆盖默认 8000."""
    monkeypatch.setenv("OPENBASE_DPS_UPSTREAM_BASE", "http://127.0.0.1:8030")
    s = Settings()
    assert s.dps_upstream_base == "http://127.0.0.1:8030"


def test_available_modules_cover_design():
    assert "auth" in AVAILABLE_MODULES
    assert "tenant" in AVAILABLE_MODULES
    assert "audit" in AVAILABLE_MODULES
    assert "observability" in AVAILABLE_MODULES
    assert "config" in AVAILABLE_MODULES
    assert "mcp" in AVAILABLE_MODULES
    assert "org" in AVAILABLE_MODULES
    assert "dict" in AVAILABLE_MODULES
    assert "scheduler" in AVAILABLE_MODULES
    assert "storage" in AVAILABLE_MODULES
    assert "notify" in AVAILABLE_MODULES


# ---- v1.4.7 覆盖率补测（O-3 后续：settings.py 分支补齐，2026-09-20）----


def test_resolve_db_url_precedence_and_asyncpg_normalization(monkeypatch):
    """_resolve_db_url：OPENBASE_DB_URL > POSTGRES_URL > 默认；裸 postgresql:// 规范化 +asyncpg."""
    monkeypatch.delenv("OPENBASE_DB_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    assert (
        settings_module._resolve_db_url()
        == "postgresql+asyncpg://postgres:postgres@localhost:5432/openbase"
    )

    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pwd@127.0.0.1:5432/db")
    assert (
        settings_module._resolve_db_url()
        == "postgresql+asyncpg://user:pwd@127.0.0.1:5432/db"
    )

    # 已带驱动后缀时不重复替换（幂等）
    monkeypatch.setenv("OPENBASE_DB_URL", "postgresql+asyncpg://u:p@h:5432/db")
    assert settings_module._resolve_db_url() == "postgresql+asyncpg://u:p@h:5432/db"

    # OPENBASE_DB_URL 优先于 POSTGRES_URL
    monkeypatch.setenv("OPENBASE_DB_URL", "postgresql://u2:p@h2:5432/db2")
    assert settings_module._resolve_db_url() == "postgresql+asyncpg://u2:p@h2:5432/db2"


def test_resolve_redis_url_default_and_override(monkeypatch):
    """_resolve_redis_url：OPENBASE_REDIS_URL > REDIS_URL > 默认."""
    monkeypatch.delenv("OPENBASE_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert settings_module._resolve_redis_url() == "redis://localhost:6379/0"

    monkeypatch.setenv("REDIS_URL", "redis://192.168.0.151:6380/1")
    assert settings_module._resolve_redis_url() == "redis://192.168.0.151:6380/1"

    monkeypatch.setenv("OPENBASE_REDIS_URL", "redis://127.0.0.1:6379/2")
    assert settings_module._resolve_redis_url() == "redis://127.0.0.1:6379/2"


def test_jwt_secret_production_weak_is_rejected():
    """production + 弱/占位密钥 → 启动即拒绝（fail-fast）."""
    with pytest.raises(ValueError, match="强随机密钥"):
        Settings(env="production", jwt_secret="change-me-in-production")


def test_jwt_secret_production_strong_is_accepted():
    """production + ≥32 字符非弱值密钥 → 通过校验."""
    strong = "".join(chr(ord("a") + index % 26) for index in range(48))
    assert Settings(env="production", jwt_secret=strong).env == "production"


def test_jwt_secret_development_weak_logs_warning(caplog):
    """development + 弱密钥 → 仅 WARN（不阻断本地联调）."""
    with caplog.at_level(logging.WARNING, logger="openbase.settings"):
        Settings(env="development", jwt_secret="dev-secret")
    assert any("弱/演示 JWT 密钥" in record.getMessage() for record in caplog.records)


def test_jwt_secret_missing_logs_warning(caplog):
    """未配置密钥 → WARN（签发 fail-closed）."""
    with caplog.at_level(logging.WARNING, logger="openbase.settings"):
        Settings(env="development", jwt_secret="")
    assert any("未配置" in record.getMessage() for record in caplog.records)


def test_parse_k03_bypass_whitelist_branches(caplog):
    """K03 白名单解析：空 → []；非法 JSON / 非数组 → [] + WARN；非 dict 条目被过滤."""
    assert Settings(k03_bypass_whitelist="").parse_k03_bypass_whitelist() == []

    with caplog.at_level(logging.WARNING, logger="openbase.settings"):
        assert Settings(k03_bypass_whitelist="{not-json}").parse_k03_bypass_whitelist() == []
        assert (
            Settings(k03_bypass_whitelist='{"path": "/x"}').parse_k03_bypass_whitelist()
            == []
        )
    messages = [record.getMessage() for record in caplog.records]
    assert any("invalid JSON" in message for message in messages)
    assert any("must be a JSON array" in message for message in messages)

    parsed = Settings(
        k03_bypass_whitelist='[{"path": "/x"}, "bad", 3]'
    ).parse_k03_bypass_whitelist()
    assert parsed == [{"path": "/x"}]


def test_parse_service_account_subject_map_branches(caplog):
    """服务账号主体映射解析：空 → []；非法 JSON / 非数组 → [] + WARN；非 dict 条目被过滤."""
    assert (
        Settings(service_account_subject_map="").parse_service_account_subject_map() == []
    )

    with caplog.at_level(logging.WARNING, logger="openbase.settings"):
        assert (
            Settings(service_account_subject_map="{not-json}").parse_service_account_subject_map()
            == []
        )
        assert (
            Settings(service_account_subject_map='"a-string"').parse_service_account_subject_map()
            == []
        )
    messages = [record.getMessage() for record in caplog.records]
    assert any("invalid JSON" in message for message in messages)
    assert any("must be a JSON array" in message for message in messages)

    entries = Settings(
        service_account_subject_map='[{"name": "svc", "subject_id": "s-1"}, "bad"]'
    ).parse_service_account_subject_map()
    assert entries == [{"name": "svc", "subject_id": "s-1"}]


def test_dps_defaults_deprecation_surface():
    """dps_default_* 兼容面：已配置 → 登记项 + 弃用提示；未配置 → 空."""
    configured = Settings(dps_default_org_id="org-1", dps_default_tenant_id="tenant-1")
    assert configured.deprecated_dps_defaults() == {
        "dps_default_org_id": "org-1",
        "dps_default_tenant_id": "tenant-1",
    }
    hints = configured.dps_defaults_deprecation_warnings()
    assert len(hints) == 2
    assert all("dps_default_* deprecated (OB-8)" in hint for hint in hints)
    assert all("register tenant code in dps_code_map instead" in hint for hint in hints)

    empty = Settings(dps_default_org_id="", dps_default_tenant_id="")
    assert empty.deprecated_dps_defaults() == {}
    assert empty.dps_defaults_deprecation_warnings() == []


def test_capture_switches_and_allowlist_parsing():
    """观测三开关辅助：允许清单解析 + 生产永久关闭（红线 4）."""
    development = Settings(
        env="development",
        capture_response=True,
        capture_upstream=True,
        capture_field_allowlist=" prompt , completion ,, ",
    )
    assert development.capture_field_allowlist_list == ["prompt", "completion"]
    assert development.capture_response_enabled is True
    assert development.capture_upstream_enabled is True

    production = Settings(
        env="production",
        jwt_secret="".join(chr(ord("a") + index % 26) for index in range(48)),
        capture_response=True,
        capture_upstream=True,
        capture_field_allowlist="",
    )
    assert production.capture_field_allowlist_list == []
    assert production.capture_response_enabled is False
    assert production.capture_upstream_enabled is False


def test_trusted_proxy_sources_list_parsing():
    """受信来源白名单：逗号分隔 → 去空白与空项（供装配点与护栏比对）."""
    assert Settings(trusted_proxy_sources="").trusted_proxy_sources_list == []
    assert Settings(
        trusted_proxy_sources=" openbase-rag-proxy , openbase-orchestrator ,, "
    ).trusted_proxy_sources_list == ["openbase-rag-proxy", "openbase-orchestrator"]


def test_dps_code_map_entries_parsing():
    """dps_code_map 登记式基线解析：空/非法 → 空表；合法 → 仅保留 dict 条目."""
    assert Settings(dps_code_map="").dps_code_map_entries() == []
    assert Settings(dps_code_map="{not-json}").dps_code_map_entries() == []

    entry = {
        "tenant_code": "acme",
        "dps_org_id": "11111111-1111-1111-1111-111111111111",
        "dps_tenant_id": "22222222-2222-2222-2222-222222222222",
    }
    entries = Settings(dps_code_map=json.dumps({"schema_version": 1, "entries": [entry, "bad"]}))
    assert entries.dps_code_map_entries() == [entry]
