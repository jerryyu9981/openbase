"""notify 模块分支补充测试（覆盖率提升至 90%）."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.models import Base


@pytest.fixture()
def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _setup():
        Base.metadata.schema = None
        for table in Base.metadata.tables.values():
            table.schema = None
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    asyncio.run(engine.dispose())


def test_notify_service_full_flow(session_factory):
    """notify 服务全流程：创建(type=1) → 列表 → 已读 → 全部已读."""
    from openbase.modules.notify import NotificationService

    async def main():
        async with session_factory() as s:
            n1 = await NotificationService.create(s, 7, "站内信", "内容", 1)
            assert n1["id"] is not None
            rows = await NotificationService.list_by_user(s, 7)
            assert len(rows) == 1 and rows[0]["is_read"] is False
            marked = await NotificationService.mark_read(s, n1["id"])
            assert marked["is_read"] is True
            cnt = await NotificationService.mark_all_read(s, 7)
            assert cnt == 1
            # 不存在通知 → None
            assert await NotificationService.mark_read(s, 9999) is None

    asyncio.run(main())


def test_notify_memory_fallback():
    """notify 内存回退路径（DB 异常降级）."""
    from openbase.modules import notify as notify_mod
    from openbase.modules.notify import NotificationService

    async def main():
        notify_mod._notifications.clear()
        notify_mod._next_id = 1
        n = await NotificationService.create_mem(1, "t", "c", 1)
        assert n["id"] == 1
        assert len(await NotificationService.list_by_user_mem(1)) == 1
        assert (await NotificationService.mark_read_mem(n["id"]))["is_read"] is True
        assert await NotificationService.mark_read_mem(999) is None
        assert await NotificationService.mark_all_read_mem(1) == 1

    asyncio.run(main())
