"""OpenBase - 统一基础设施公共底座框架.

OpenBase 是四系统（OpenLLM / OpenRAG / OpenMemory / DPS）及未来类似系统的统一
基础设施公共底座：框架内核 core + 插件模块 modules + 工具链 cli/crud + 模板脚手架。

示例::

    from openbase import init_app, settings

    settings.enable_module("auth")
    settings.enable_module("tenant")

    app = init_app(settings)
"""

from openbase.settings import Settings, get_settings

settings = get_settings()

__version__ = "1.0.0"

__all__ = ["init_app", "settings", "Settings", "__version__"]


def init_app(settings: Settings) -> object:
    """根据配置自动装配 FastAPI 应用并挂载已启用模块.

    Args:
        settings: 已配置启用模块的 Settings 实例.

    Returns:
        装配完成的 FastAPI 应用实例.
    """
    from fastapi import FastAPI

    from openbase.core.errors import install_exception_handlers

    app = FastAPI(title=settings.app_name, version=__version__, docs_url="/docs")

    # 统一异常处理
    install_exception_handlers(app)

    # 统一鉴权中间件（SR-001：管理接口 JWT 门禁；白名单路径公开）
    from openbase.core.deps.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)

    # 中间件（审计/租户等按启用顺序注册）
    if settings.is_enabled("audit"):
        from openbase.modules.audit.middleware import AuditMiddleware

        app.add_middleware(AuditMiddleware)

    if settings.is_enabled("tenant"):
        from openbase.modules.tenant.middleware import TenantMiddleware

        app.add_middleware(TenantMiddleware)

    # 模块路由挂载
    for module_name in settings.enabled_modules:
        try:
            module = __import__(f"openbase.modules.{module_name}", fromlist=["router"])
            if hasattr(module, "router"):
                app.include_router(module.router)
        except ImportError:
            # 模块存在但未实现时跳过，不阻塞装配
            continue

    return app
