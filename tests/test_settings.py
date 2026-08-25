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
