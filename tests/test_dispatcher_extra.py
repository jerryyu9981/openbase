"""identity outbox dispatcher 分支补测（覆盖率治理）.

覆盖：非 pending 跳过、发布成功/重试/超阈值失败三种推进、按 event_id 投递、
run_once 汇总计数、后台轮询任务的启动/异常告警/取消停止。
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from openbase.core.models import Base, OutboxEvent


@pytest.fixture()
def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _setup() -> None:
        Base.metadata.schema = None
        for table in Base.metadata.tables.values():
            table.schema = None
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        asyncio.run(engine.dispose())


def _event(event_id: str, status: str = "pending", attempts: int = 0) -> OutboxEvent:
    return OutboxEvent(
        event_id=event_id,
        event_type="identity.user.deactivated",
        payload={"event_id": event_id},
        status=status,
        publish_attempts=attempts,
    )


def test_dispatch_event_row_outcomes(session_factory, monkeypatch) -> None:
    """published / skipped / retry / failed 四条推进分支."""
    from openbase.modules.identity import dispatcher as dispatcher_module

    service = dispatcher_module.OutboxDispatcherService

    async def _run() -> None:
        async with session_factory() as session:
            published = _event("e-published")
            skipped = _event("e-skipped", status="published")
            retry = _event("e-retry", attempts=2)
            failed = _event("e-failed", attempts=dispatcher_module.MAX_PUBLISH_ATTEMPTS - 1)
            session.add_all([published, skipped, retry, failed])
            await session.flush()

            monkeypatch.setattr(dispatcher_module, "publish", lambda channel, payload: True)
            published_result = await service.dispatch_event_row(session, published)
            assert published_result["outcome"] == "published"
            assert published.published_at is not None
            assert published.next_retry_at is None

            monkeypatch.setattr(dispatcher_module, "publish", lambda channel, payload: False)
            skipped_result = await service.dispatch_event_row(session, skipped)
            assert skipped_result["outcome"] == "skipped"

            retry_result = await service.dispatch_event_row(session, retry)
            assert retry_result["outcome"] == "retry"
            assert retry.next_retry_at is not None

            failed_result = await service.dispatch_event_row(session, failed)
            assert failed_result["outcome"] == "failed"
            assert failed.status == "failed"
            assert failed_result["next_retry_at"] is None

    asyncio.run(_run())


def test_dispatch_by_event_id_missing_and_existing(session_factory, monkeypatch) -> None:
    """按 event_id 投递：不存在返回 None；存在则推进状态."""
    from openbase.modules.identity import dispatcher as dispatcher_module

    service = dispatcher_module.OutboxDispatcherService
    monkeypatch.setattr(dispatcher_module, "publish", lambda channel, payload: True)

    async def _run() -> None:
        async with session_factory() as session:
            session.add(_event("e-by-id"))
            await session.flush()

            assert await service.dispatch_by_event_id(session, "missing-id") is None
            result = await service.dispatch_by_event_id(session, "e-by-id")
            assert result is not None
            assert result["outcome"] == "published"

    asyncio.run(_run())


def test_run_once_summary_counts(session_factory, monkeypatch) -> None:
    """run_once 汇总：成功/重试/超阈值失败分别计数并按状态过滤."""
    from openbase.modules.identity import dispatcher as dispatcher_module

    service = dispatcher_module.OutboxDispatcherService

    async def _run() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    _event("e-ok"),
                    _event("e-retry-1"),
                    _event("e-retry-2", attempts=1),
                    _event("e-fail", attempts=dispatcher_module.MAX_PUBLISH_ATTEMPTS - 1),
                    _event("e-done", status="published"),
                ]
            )
            await session.flush()

            delivered = {"done": False}

            def _publish(channel: str, payload: dict) -> bool:
                return delivered["done"]

            monkeypatch.setattr(dispatcher_module, "publish", _publish)
            summary = await service.run_once(session)
            assert summary == {"scanned": 4, "published": 0, "retry": 3, "failed": 1, "skipped": 0}

            # 第二轮：仅到期 pending 参与；新增一条并恢复发布能力 → 成功计数
            delivered["done"] = True
            session.add(_event("e-late"))
            await session.flush()
            summary_second = await service.run_once(session)
            assert summary_second == {
                "scanned": 1,
                "published": 1,
                "retry": 0,
                "failed": 0,
                "skipped": 0,
            }

    asyncio.run(_run())


def test_background_loop_warns_and_stops(session_factory, monkeypatch) -> None:
    """后台轮询：单轮异常仅告警不中断；stop 取消任务；重复 stop 幂等."""
    import openbase.core.db.session as session_module
    from openbase.modules.identity.dispatcher import OutboxDispatcherService

    monkeypatch.setattr(session_module, "get_session_factory", lambda: session_factory)
    calls = {"total": 0}

    async def _flaky(cls, session) -> None:
        calls["total"] += 1
        if calls["total"] == 1:
            raise RuntimeError("db blip")

    monkeypatch.setattr(OutboxDispatcherService, "run_once", classmethod(_flaky))

    async def _run() -> None:
        OutboxDispatcherService.stop_background_loop()  # 空任务幂等
        await OutboxDispatcherService.start_background_loop(interval_seconds=0.01)
        await asyncio.sleep(0.05)
        OutboxDispatcherService.stop_background_loop()
        await asyncio.sleep(0.01)

    asyncio.run(_run())
    assert calls["total"] >= 2
