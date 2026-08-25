"""数据库会话管理：异步 session 工厂 + get_db 依赖."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(url: str, echo: bool = False, schema: str = "openbase") -> AsyncEngine:
    """初始化全局异步引擎与 session 工厂.

    连接建立时自动设置 search_path 指向 openbase schema，
    保证共享库（public 为其他系统使用）内表隔离。

    Args:
        url: 数据库连接串（asyncpg 驱动）。
        echo: 是否打印 SQL 日志。
        schema: 目标 schema（默认 openbase）。

    Returns:
        全局 AsyncEngine 实例。
    """
    global _engine, _session_factory
    # 模型元数据绑定 schema：所有 SQL 显式带 "{schema}." 前缀，
    # 不依赖连接级 search_path，保证共享库内表隔离（最可靠方案）
    from openbase.core.models import Base

    Base.metadata.schema = schema
    for table in Base.metadata.tables.values():
        if table.schema is None:
            table.schema = schema

    _engine = create_async_engine(url, echo=echo, connect_args={"timeout": 5})

    from sqlalchemy import event

    @event.listens_for(_engine.sync_engine, "connect")
    def _set_search_path(dbapi_conn, _record) -> None:
        # 隐式事务中的 SET 会在连接回收时回滚，必须显式 commit 持久到连接
        cursor = dbapi_conn.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()
        dbapi_conn.commit()

    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取全局 session 工厂（未初始化时按默认配置懒初始化）. """
    global _session_factory
    if _session_factory is None:
        from openbase.settings import get_settings

        settings = get_settings()
        init_db(settings.db_url, settings.db_echo, settings.db_schema)
    assert _session_factory is not None
    return _session_factory


def get_engine() -> AsyncEngine:
    """获取全局异步引擎（未初始化时按默认配置懒初始化）.

    Returns:
        全局 AsyncEngine 实例。
    """
    global _engine
    if _engine is None:
        get_session_factory()
    assert _engine is not None
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：请求级数据库会话.

    Yields:
        AsyncSession: 会话；请求结束后自动关闭。
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
