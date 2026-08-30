"""OpenBase 演示应用（启动验证用）.

启动方式::

    uvicorn openbase.demo_app:app --reload

数据库接入：优先连接共享基础设施 PostgreSQL（.env.shared-infra 的 POSTGRES_URL），
建 openbase schema 与全部表并种子 admin 用户（admin123）；数据库不可达时
降级为内存演示用户。
"""

import asyncio
import logging

from openbase import init_app
from openbase.core.db.init import init_database
from openbase.core.db.session import get_engine, get_session_factory
from openbase.core.models import User
from openbase.modules.auth import UserService, hash_password
from openbase.settings import Settings

logger = logging.getLogger("openbase.demo")

settings = Settings()
for module in (
    "auth",
    "tenant",
    "audit",
    "config",
    "observability",
    "mcp",
    "org",
    "dict",
    "scheduler",
    "storage",
    "notify",
    # v1.2.0 统一前端增量
    "ai_apps",
    "proxy",
    "frontend",
    # v1.4.0 统一网关增强（服务发现 + 聚合编排，阶段一零依赖）
    "gateway",
    # v1.4.2 四维身份管理（R-375 用户管理，R-374 租户已在上方启用）
    "users",
):
    settings.enable_module(module)


async def _seed_admin(session) -> None:
    """种子数据库 admin 用户（幂等）."""
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.username == "admin"))
    if result.scalar_one_or_none() is None:
        session.add(
            User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="系统管理员",
                status=1,
            )
        )
        await session.commit()
        logger.info("admin user seeded to database")


def _try_database_init() -> bool:
    """尝试初始化数据库（建 schema/表 + 种子用户）.

    Returns:
        数据库初始化是否成功。
    """
    try:
        engine = get_engine()
        async def _init() -> None:
            await init_database(engine, settings.db_schema)
            # 种子 admin 用户
            async with get_session_factory()() as session:
                await _seed_admin(session)
                # 恢复持久化配置（config 模块落库数据）
                from openbase.modules.config import ConfigStore

                await ConfigStore.hydrate(session)
            # 释放连接池：避免初始化循环与请求循环不一致导致连接复用异常
            await engine.dispose()

        asyncio.run(_init())
        logger.info("database initialized via shared infra", extra={"schema": settings.db_schema})
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("database init failed, fallback to memory: %s", exc)
        return False


_DB_READY = _try_database_init()
if not _DB_READY:
    # 降级：内存演示用户
    UserService.seed_memory_user("admin", "admin123")
    logger.info("fallback: memory demo user seeded (admin/admin123)")

app = init_app(settings)
