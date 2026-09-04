"""settings 配置驱动测试."""

import pytest

from openbase.settings import AVAILABLE_MODULES, Settings


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
