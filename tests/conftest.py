"""pytest 全局配置：Windows 事件循环策略修复（TD-新增-009）.

背景：Windows 默认 ProactorEventLoop 在 pytest-asyncio auto 模式 + 多个
starlette TestClient（anyio portal 线程）组合执行时，跨线程创建/关闭
event loop 触发 C 层 access violation / Segmentation fault（全量 pytest
本机崩溃）。切换 SelectorEventLoopPolicy 为线程安全实现修复。

注：仅影响本机测试运行，不影响应用运行时（uvicorn 独立进程）。
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# C-1（日志落盘）测试隔离：默认不装配文件日志，避免向仓库 logs/ 落盘并干扰 caplog 断言。
# 需要验证真实装配的用例显式调用 setup_logging(force=True) 并自行清理 handler。
os.environ.setdefault("OPENBASE_LOG_SETUP", "0")

# C-4（审计落库）测试隔离：默认关闭请求期 DB 落库，避免每个 TestClient 请求都尝试连库
# （拖慢全量且受共享 PG 抖动影响）。需要验证落库/降级的用例显式置 1 并注入假会话工厂。
os.environ.setdefault("OPENBASE_AUDIT_DB_PERSIST", "0")


def reset_db_singletons() -> None:
    """重置 core.db.session 全局 engine/session 单例（T2 隔离修复 2026-09-06）.

    OIDC E2E 族以"DB 不可达 → 降级直签"为断言语义：autouse fixture 会把
    OPENBASE_DB_URL 指为不可达以模拟空库。但全量 pytest 中前序用例可能已按
    真实库创建全局 engine 单例（core/db/session._engine），OIDC 用例再走
    get_db 会复用该 engine 直连真实库 → 固定 sub 命中历史 OidcIdentity 行
    复用旧用户（'3'/'4'），env 隔离被绕过。本函数先 dispose 再置空两个单例，
    使后续 get_db 按当前（不可达）env 重建。
    """
    from openbase.core import db as db_pkg

    session_mod = db_pkg.session
    engine = session_mod._engine
    if engine is not None:
        try:
            asyncio.run(engine.dispose())
        except Exception:
            # dispose 失败仅告警：置空后旧引擎由 GC 回收（进程级测试可容忍）
            pass
    session_mod._engine = None
    session_mod._session_factory = None


def _clear_identity_cache_keys() -> None:
    """清理 identity 主体缓存键（principal:*/user:*；Redis 不可用时静默跳过）.

    背景：启用 Redis 缓存后，主体快照（``principal:{id}``）与用户按名缓存
    （``user:{username}``，TTL 内）会跨用例残留；用例既复用确定性用户名、又
    直接改写库中主体状态，残留快照会造成跨用例脏读（示例：
    tests/test_identity_t4.py::test_t4_4_nested_chain_same_domain_ok_cross_hop_rejected
    与 tests/test_identity_t3.py::test_t3_1_suspend_immediately_invalidates_existing_access
    在共享 Redis 下单独运行通过、连续运行失败）。生产为同一库同一 Redis 实例，
    不存在该语义差异；此处仅做用例间隔离。

    性能：复用 ``redis_client`` 全局单例（不逐用例重建连接），仅对身份键做
    SCAN + DEL，避免全量测试因远端往返显著变慢。
    """
    try:
        from openbase.core.cache import redis_client

        client = redis_client.get_client()
        if client is None:
            return
        keys: list[str] = []
        for pattern in ("openbase:principal:*", "openbase:user:*"):
            keys.extend(client.scan_iter(pattern, count=500))
        if keys:
            client.delete(*keys)
    except Exception:  # noqa: BLE001 - 缓存隔离尽力而为，不阻断用例
        return


@pytest.fixture(autouse=True)
def isolate_identity_cache() -> None:
    """用例级缓存隔离：清理身份缓存键（Redis 不可用时为无操作）.

    覆盖全部用例：主体快照缓存污染不限于身份用例文件——例如
    ``tests/test_verdict_k03.py`` 以「DB 不可达」模拟降级，若命中上一用例残留的
    ``principal:{id}`` 快照（状态非 active），会走 AUTH_PRINCIPAL_DISABLED 分支而
    非预期降级分支，造成误判。清理成本为 2 次 SCAN + 1 次 DEL（复用全局连接）。
    """
    _clear_identity_cache_keys()
    yield


@pytest.fixture()
def api_key_client(tmp_path):
    """最小 auth 应用 + SQLite：服务 Key 端点回归不依赖外部 PG.

    背景（2026-10-28）：服务 Key 由内存态改为 ``service_api_keys`` 表持久化后，
    原先基于 ``openbase.demo_app.app`` 的端点用例会经 ``get_db`` 连接共享 PG，
    跨网抖动时表现为 ``connection was closed in the middle of operation``。
    该 fixture 只挂载 auth 路由并覆写 ``get_db``/``get_current_user``，
    保证服务 Key 用例与外部数据面解耦（建表仍走真实 ``Base.metadata``）。
    """
    import asyncio

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from openbase.core.db.session import get_db
    from openbase.core.deps.auth import get_current_user
    from openbase.core.errors import install_exception_handlers
    from openbase.core.models import Base
    from openbase.modules.auth import router as auth_router

    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api_keys.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())

    async def _override_get_db():
        async with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(auth_router)
    # 统一错误契约（{code,message,detail,request_id}）：BaseError → 对应 HTTP 状态
    install_exception_handlers(app)
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "1",
        "username": "admin",
        "permissions": ["*"],
    }
    client = TestClient(app)
    yield client
    asyncio.run(engine.dispose())

