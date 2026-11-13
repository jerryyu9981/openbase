"""scheduler 模块补测（补测方案同源：先修口径、按缺口补测）.

覆盖：任务 CRUD 主路径、404 分支、APScheduler 不可用降级、
add_job 成功/失败、内存回退（DB 异常）、服务层空结果分支。
数据落库（SQLite 文件库），不依赖外部 PostgreSQL。
"""

from __future__ import annotations

import asyncio
import builtins
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from openbase import init_app
from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.models import Base
from openbase.modules import scheduler as scheduler_module
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.scheduler import ScheduleService, _run_task, get_scheduler
from openbase.settings import Settings

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_scheduler_backfill.db"
_session_factory: async_sessionmaker | None = None


def _build_client() -> TestClient:
    global _session_factory

    settings = Settings()
    settings.enable_module("scheduler")
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)
    _session_factory = get_session_factory()

    async def _create_tables() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())
    return TestClient(init_app(settings))


@pytest.fixture(scope="module")
def client() -> TestClient:
    """模块级应用装配 + 全局 DB 工厂硬隔离（同 test_users_admin 口径）."""
    global _session_factory

    from conftest import reset_db_singletons

    import openbase.core.db.session as session_module

    test_client = _build_client()
    assert _session_factory is not None
    patch = pytest.MonkeyPatch()
    patch.setattr(session_module, "get_session_factory", lambda: _session_factory)
    try:
        yield test_client
    finally:
        patch.undo()
        reset_db_singletons()


def _headers() -> dict[str, str]:
    """非数字 sub 的直签令牌：中间件跳过主体验证，端点仅需 JWT 门禁."""
    token = create_access_token(
        "scheduler-caller",
        username="scheduler-caller",
        extra={"permissions": ["*"], "role": "admin"},
    )
    return {"Authorization": f"Bearer {token}"}


def test_schedule_crud_flow(client: TestClient) -> None:
    """创建 → 列表 → 启停 → 日志 → 删除（DB 主路径）。"""
    headers = _headers()
    created = client.post(
        "/api/v1/schedules",
        json={"name": "nightly", "cron_expr": "0 1 * * *", "func_path": ""},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    task = created.json()
    assert task["status"] == 1 and task["name"] == "nightly"

    listing = client.get("/api/v1/schedules", headers=headers)
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [task["id"]]

    stopped = client.post(f"/api/v1/schedules/{task['id']}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["status"] == 0

    started = client.post(f"/api/v1/schedules/{task['id']}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["status"] == 1

    logs = client.get(f"/api/v1/schedules/{task['id']}/logs", headers=headers)
    assert logs.status_code == 200
    assert logs.json() == []

    deleted = client.delete(f"/api/v1/schedules/{task['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": task["id"]}
    assert client.get("/api/v1/schedules", headers=headers).json() == []


def test_schedule_start_stop_missing_task(client: TestClient) -> None:
    """启停不存在的任务 → 404（服务层空结果分支）。"""
    headers = _headers()
    assert client.post("/api/v1/schedules/999999/start", headers=headers).status_code == 404
    assert client.post("/api/v1/schedules/999999/stop", headers=headers).status_code == 404


def test_scheduler_import_error_disables_scheduler(monkeypatch) -> None:
    """apscheduler 不可用 → 返回 None 并告警（降级路径）。"""
    monkeypatch.setattr(scheduler_module, "_scheduler", None)
    real_import = builtins.__import__

    def _fake_import(name: str, *args, **kwargs):
        if name.startswith("apscheduler"):
            raise ImportError("apscheduler not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert get_scheduler() is None
    monkeypatch.setattr(scheduler_module, "_scheduler", None)


def test_get_scheduler_returns_cached_instance(monkeypatch) -> None:
    """已初始化时直接返回缓存实例（不走重建分支）。"""
    sentinel = object()
    monkeypatch.setattr(scheduler_module, "_scheduler", sentinel)
    assert get_scheduler() is sentinel
    monkeypatch.setattr(scheduler_module, "_scheduler", None)


def test_run_task_emits_log(caplog) -> None:
    """任务执行体写入结构化日志。"""
    with caplog.at_level("INFO", logger="openbase.scheduler"):
        _run_task(42)
    assert any("schedule task executed" in record.message for record in caplog.records)


def test_create_registers_job_when_scheduler_available(client: TestClient, monkeypatch) -> None:
    """func_path 非空且调度器可用 → 注册 add_job；注册异常仅告警不阻断。"""

    class _FakeScheduler:
        def __init__(self, raise_on_add: bool = False) -> None:
            self.jobs: list[dict] = []
            self.raise_on_add = raise_on_add

        def add_job(self, func, **kwargs) -> None:
            if self.raise_on_add:
                raise RuntimeError("job registry broken")
            self.jobs.append({"func": func, **kwargs})

    fake = _FakeScheduler()
    monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: fake)
    headers = _headers()
    resp = client.post(
        "/api/v1/schedules",
        json={"name": "with-job", "cron_expr": "0 2 * * *", "func_path": "pkg.mod.fn"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert len(fake.jobs) == 1
    assert fake.jobs[0]["args"] == [resp.json()["id"]]

    broken = _FakeScheduler(raise_on_add=True)
    monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: broken)
    resp = client.post(
        "/api/v1/schedules",
        json={"name": "broken-job", "cron_expr": "0 3 * * *", "func_path": "pkg.mod.fn"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _call_service(coro_func, *args):
    async def _run():
        assert _session_factory is not None
        async with _session_factory() as session:  # type: ignore[call-arg]
            return await coro_func(session, *args)

    return asyncio.run(_run())


def test_service_missing_rows_return_none() -> None:
    """服务层 get/set_status 对不存在的任务返回 None。"""
    assert _call_service(ScheduleService.get, 999999) is None
    assert _call_service(ScheduleService.set_status, 999999, 0) is None


def test_service_delete_missing_row_is_idempotent() -> None:
    """删除不存在的任务仍返回 deleted（幂等）。"""
    assert _call_service(ScheduleService.delete, 999999) == {"deleted": 999999}


def test_memory_fallback_when_db_unavailable(client: TestClient, monkeypatch) -> None:
    """DB 异常时全部端点回退内存实现（创建/列表/启停/删除）。"""

    async def _boom(*args, **kwargs):
        raise RuntimeError("db unavailable")

    for name in ("create", "list_all", "set_status", "delete"):
        monkeypatch.setattr(ScheduleService, name, classmethod(_boom))

    headers = _headers()
    created = client.post(
        "/api/v1/schedules",
        json={"name": "mem-task", "cron_expr": "0 4 * * *", "func_path": ""},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    task = created.json()

    listing = client.get("/api/v1/schedules", headers=headers)
    assert listing.status_code == 200
    assert any(row["id"] == task["id"] for row in listing.json())

    assert client.post(f"/api/v1/schedules/{task['id']}/stop", headers=headers).json()["status"] == 0
    assert client.post(f"/api/v1/schedules/{task['id']}/start", headers=headers).json()["status"] == 1
    assert client.delete(f"/api/v1/schedules/{task['id']}", headers=headers).json() == {
        "deleted": task["id"]
    }
