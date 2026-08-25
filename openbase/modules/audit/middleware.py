"""audit 模块：中间件独立路径（兼容 init_app 引用）."""

from openbase.modules.audit import AuditMiddleware

__all__ = ["AuditMiddleware"]
