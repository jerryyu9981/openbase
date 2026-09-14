"""OpenBase 演示应用（启动验证用）.

启动方式::

    uvicorn openbase.demo_app:app --reload

数据库接入：优先连接共享基础设施 PostgreSQL（.env.shared-infra 的 POSTGRES_URL），
建 openbase schema 与全部表并种子 admin 用户（admin123）；数据库不可达时
降级为内存演示用户。
"""

import asyncio
import logging
import os

from openbase import init_app
from openbase.core.db.init import init_database
from openbase.core.db.session import get_engine, get_session_factory
from openbase.core.logging_setup import setup_logging
from openbase.core.models import User
from openbase.modules.auth import UserService, hash_password
from openbase.settings import Settings

logger = logging.getLogger("openbase.demo")

settings = Settings()

# C-1 日志落盘：进程启动即装配（JSONL 落盘 + 控制台 JSON）。
# 测试环境由 tests/conftest.py 置 OPENBASE_LOG_SETUP=0，避免污染仓库日志与干扰 caplog。
if os.getenv("OPENBASE_LOG_SETUP", "1") != "0":
    _logging_setup = setup_logging(service="openbase")
    logger.info(
        "service.start",
        extra={
            "service": "openbase",
            "log_path": str(_logging_setup.current_path),
            "log_level": logging.getLevelName(_logging_setup.level),
        },
    )
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
    # v1.4.3 OpenLLM 对接（R-379：llm-proxy 认证注入 + 转发）
    "llm_proxy",
    # v1.4.4 OpenRAG 对接（R-380：rag-proxy JWT 门禁 + 转发）
    "rag_proxy",
    # v1.4.5 DPS 对接（R-381：dps-proxy JWT 门禁 + 身份头注入）
    "dps_proxy",
    # U1 统一身份收口（RA-01/OB-1/OB-2/L1-1/L1-2）：Principal 主体面 +
    # agent 密钥面（sk-agent-*）+ lifecycle 状态机 + purge 受权 + events/blocked 契约桩。
    # S7 门禁 ④（L1-1 级联 / L3-1 Agent）联调依赖该路由挂载。
    "identity",
    # 批 2 C-10：人工测试结论记录（受权 API test:record）
    "testing",
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


@app.on_event("startup")
async def _start_identity_outbox_dispatcher() -> None:
    """启动 L1-1 outbox 投递后台循环（部署入口按需启动，草案 §8.2）.

    identity.lifecycle.* 迁移在同事务写 outbox_events；投递循环把 pending 事件
    推进为 published，使 ``GET /api/v1/identity/events`` 可观测、消费端可对账。
    无 Redis 时投递失败会走指数退避重试（事件不丢）。
    """
    from openbase.modules.identity.dispatcher import OutboxDispatcherService

    await OutboxDispatcherService.start_background_loop(interval_seconds=1.0)
    logger.info("identity outbox dispatcher started")


@app.on_event("startup")
async def _record_capture_switch_state() -> None:
    """C-19：启动时留痕响应采集三开关状态（方案 §11.2 红线 5「开关本身留痕」）.

    全关（生产默认）→ 只留结构化日志、零落库；任一开启 → best-effort 落
    ``audit_logs``（action=capture.switch）；落库失败仅 WARN，不阻断启动。
    """
    from openbase.modules.audit.capture_switches import record_capture_switch_state

    await record_capture_switch_state(settings)
