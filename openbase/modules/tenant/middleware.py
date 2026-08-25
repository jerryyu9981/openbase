"""tenant 模块：租户中间件（兼容 init_app 引用路径）."""

from openbase.modules.tenant import TenantMiddleware

__all__ = ["TenantMiddleware"]
