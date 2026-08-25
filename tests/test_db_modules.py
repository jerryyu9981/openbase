"""六模块数据库服务测试（SQLite）：验证数据库优先路径（落库/查询/删除）.

覆盖 dict/org/config/scheduler/storage/notify 的 DBService DB 分支，
与内存回退路径共同构成完整存储语义验证。
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.models import Base


@pytest.fixture()
def session_factory():
    """SQLite 内存库会话工厂（每个用例独立 schema）."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _setup():
        # SQLite 无 schema 概念，重置全局 schema 绑定
        Base.metadata.schema = None
        for table in Base.metadata.tables.values():
            table.schema = None
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    asyncio.run(engine.dispose())


def _run(coro):
    return asyncio.run(coro)


# ---- dict ----
def test_dict_service_db_crud(session_factory):
    from openbase.modules.dict import DictService

    async def main():
        async with session_factory() as s:
            await DictService.create_type(s, "gender", "性别")
            assert (await DictService.list_types(s))[0]["code"] == "gender"
            item = await DictService.create_item(s, "gender", "男", "M", 1)
            items = await DictService.list_items(s, "gender")
            assert items[0]["label"] == "男"
            await DictService.delete_item(s, item["id"])
            assert (await DictService.list_items(s, "gender")) == []

    _run(main())


# ---- org ----
def test_org_service_db_crud(session_factory):
    from openbase.modules.org import DepartmentService

    async def main():
        async with session_factory() as s:
            root = await DepartmentService.create(s, "研发部", None)
            child = await DepartmentService.create(s, "后端组", root["id"])
            assert child["path"].startswith(root["path"])
            rows = await DepartmentService.list_all(s)
            assert len(rows) == 2
            await DepartmentService.delete(s, child["id"])
            assert len(await DepartmentService.list_all(s)) == 1

    _run(main())


# ---- config ----
def test_config_store_db_persist_hydrate(session_factory):
    from openbase.modules.config import ConfigLevel, ConfigStore

    async def main():
        async with session_factory() as s:
            await ConfigStore.persist(s, "feature.flag", {"on": True}, ConfigLevel.SYSTEM, 1)
            # 重新 hydrate（模拟重启恢复）
            ConfigStore._runtime.clear()
            ConfigStore._versions.clear()
            await ConfigStore.hydrate(s)
            assert ConfigStore.get("feature.flag") == {"on": True}
            versions = await ConfigStore.versions_db(s, "feature.flag")
            assert versions[0]["version"] == 1

    _run(main())


# ---- scheduler ----
def test_scheduler_service_db_crud(session_factory):
    from openbase.modules.scheduler import ScheduleService

    async def main():
        async with session_factory() as s:
            task = await ScheduleService.create(s, "daily", "0 8 * * *", "")
            assert task["status"] == 1
            rows = await ScheduleService.list_all(s)
            assert len(rows) == 1
            stopped = await ScheduleService.set_status(s, task["id"], 0)
            assert stopped["status"] == 0
            assert (await ScheduleService.get(s, task["id"]))["status"] == 0
            await ScheduleService.delete(s, task["id"])
            assert (await ScheduleService.list_all(s)) == []

    _run(main())


# ---- storage ----
def test_storage_service_db_crud(session_factory):
    from openbase.modules.storage import FileService

    async def main():
        async with session_factory() as s:
            rec = await FileService.create(s, "a.txt", "/tmp/a.txt", "local", "text/plain", 5)
            got = await FileService.get(s, rec["id"])
            assert got["file_name"] == "a.txt"
            assert len(await FileService.list_all(s)) == 1
            await FileService.delete(s, rec["id"])
            assert await FileService.get(s, rec["id"]) is None

    _run(main())


# ---- notify ----
def test_notify_service_db_crud(session_factory):
    from openbase.modules.notify import NotificationService

    async def main():
        async with session_factory() as s:
            n = await NotificationService.create(s, 1, "提醒", "内容", 1)
            rows = await NotificationService.list_by_user(s, 1)
            assert len(rows) == 1
            assert rows[0]["is_read"] is False
            marked = await NotificationService.mark_read(s, n["id"])
            assert marked["is_read"] is True
            await NotificationService.mark_all_read(s, 1)

    _run(main())
