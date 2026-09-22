"""L1 构建/导入验证：应用可导入 + 新增配置项可见"""
import sys

sys.path.insert(0, r"D:\Trae CN\myproject\Dev\OpenLLM\backend")

import main  # noqa: E402,F401  （L1：入口模块可导入）

from app.core.config import settings  # noqa: E402

print("L1 导入 OK")
print("PROFILE_INJECTION_ENABLED =", settings.PROFILE_INJECTION_ENABLED)
print("PROFILE_FAILURE_COOLDOWN_SECONDS =", settings.PROFILE_FAILURE_COOLDOWN_SECONDS)
