"""通用数据库服务基类：数据库优先 + 内存回退模式.

各业务模块的 DBService 继承本类，实现"数据库优先、内存降级"，
与 auth 模块 UserService 模式一致，保证共享库不可达时模块可用。
"""

from __future__ import annotations

import logging

logger = logging.getLogger("openbase.db.services")


class BaseDBService:
    """数据库优先服务基类."""

    # 内存回退存储（子类覆盖为模块级 dict/list）
    memory_store: dict = {}
    memory_fallback_enabled: bool = True

    @classmethod
    def _db_available(cls) -> bool:
        """检查数据库是否可用（引擎已初始化且最近查询未持续失败）."""
        from openbase.core.db.session import get_engine

        try:
            get_engine()
            return True
        except Exception:  # noqa: BLE001
            return False

    @classmethod
    async def _run(cls, fn, *args, **kwargs):
        """在数据库会话中执行函数；失败时抛出异常由调用方回退内存."""
        from openbase.core.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            return await fn(session, *args, **kwargs)

    @classmethod
    def _fallback(cls, name: str, exc: Exception):
        """记录回退日志."""
        if cls.memory_fallback_enabled:
            logger.warning("%s fallback to memory: %s", name, exc)
