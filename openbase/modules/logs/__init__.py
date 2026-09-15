"""logs 模块：日志中心（四源统一检索，v1.4.6）。

入口：
- ``router``：受权 ``log:read`` 的检索/聚合/导出端点（见 router.py）。
- service 层函数：``search`` / ``facets`` / ``export`` / ``build_facets_presets``。
"""

from __future__ import annotations

from openbase.modules.logs.router import router

__all__ = ["router"]

# 模块独立版本（TD-11-01）：与同批新增模块（gateway/testing/users）一致取 1.0.0
__version__ = "1.0.0"
