"""scheduler 模块：定时任务（APScheduler 封装 + 任务 CRUD，数据库优先 + 内存回退）."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.services import BaseDBService
from openbase.core.db.session import get_db
from openbase.core.models import ScheduleTask

logger = logging.getLogger("openbase.scheduler")

router = APIRouter(prefix="/api/v1/schedules", tags=["scheduler"])

# 内存回退存储
_tasks: dict[int, dict] = {}
_logs: dict[int, list[dict]] = {}
_next_task_id = 1
_scheduler = None


class ScheduleCreate(BaseModel):
    """创建任务请求."""

    name: str
    cron_expr: str = "0 0 * * *"
    func_path: str = ""


class ScheduleOut(BaseModel):
    """任务响应."""

    id: int
    name: str
    cron_expr: str
    status: int  # 1=启用 0=禁用
    last_run_at: str | None = None
    next_run_at: str | None = None


def get_scheduler():
    """获取 APScheduler 实例（懒初始化）.

    Returns:
        BackgroundScheduler；apscheduler 不可用时返回 None。
    """
    global _scheduler
    if _scheduler is None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            _scheduler = BackgroundScheduler()
            _scheduler.start()
        except ImportError:
            logger.warning("apscheduler not installed, scheduler disabled")
            return None
    return _scheduler


def _run_task(task_id: int) -> None:
    """任务执行体（占位，生产接入 func_path 动态调用）."""
    logger.info("schedule task executed", extra={"task_id": task_id})


def _to_out(t: dict) -> ScheduleOut:
    return ScheduleOut(
        id=t["id"], name=t["name"], cron_expr=t["cron_expr"], status=t.get("status", 1),
        last_run_at=t.get("last_run_at"), next_run_at=t.get("next_run_at"),
    )


class ScheduleService(BaseDBService):
    """任务服务：数据库优先 + 内存回退."""

    @classmethod
    async def create(cls, session: AsyncSession, name: str, cron_expr: str, func_path: str) -> dict:
        task = ScheduleTask(name=name, cron_expr=cron_expr, func_path=func_path or None, status=1)
        session.add(task)
        await session.commit()
        return {"id": task.id, "name": task.name, "cron_expr": task.cron_expr, "status": 1,
                "last_run_at": None, "next_run_at": None}

    @classmethod
    async def list_all(cls, session: AsyncSession) -> list[dict]:
        rows = (await session.execute(select(ScheduleTask).order_by(ScheduleTask.id))).scalars().all()
        return [{"id": r.id, "name": r.name, "cron_expr": r.cron_expr, "status": r.status,
                 "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                 "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None} for r in rows]

    @classmethod
    async def get(cls, session: AsyncSession, task_id: int) -> dict | None:
        r = (await session.execute(select(ScheduleTask).where(ScheduleTask.id == task_id))).scalar_one_or_none()
        if r is None:
            return None
        return {"id": r.id, "name": r.name, "cron_expr": r.cron_expr, "status": r.status,
                "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None}

    @classmethod
    async def set_status(cls, session: AsyncSession, task_id: int, status: int) -> dict | None:
        r = (await session.execute(select(ScheduleTask).where(ScheduleTask.id == task_id))).scalar_one_or_none()
        if r is None:
            return None
        r.status = status
        await session.commit()
        return {"id": r.id, "name": r.name, "cron_expr": r.cron_expr, "status": r.status,
                "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None}

    @classmethod
    async def delete(cls, session: AsyncSession, task_id: int) -> dict:
        r = (await session.execute(select(ScheduleTask).where(ScheduleTask.id == task_id))).scalar_one_or_none()
        if r is not None:
            await session.delete(r)
            await session.commit()
        return {"deleted": task_id}

    # ---- 内存回退 ----
    @classmethod
    async def create_mem(cls, name: str, cron_expr: str, func_path: str) -> dict:
        global _next_task_id
        task = {"id": _next_task_id, "name": name, "cron_expr": cron_expr,
                "func_path": func_path, "status": 1, "last_run_at": None, "next_run_at": None}
        _tasks[_next_task_id] = task
        _logs.setdefault(_next_task_id, [])
        _next_task_id += 1
        return task

    @classmethod
    async def list_all_mem(cls) -> list[dict]:
        return list(_tasks.values())

    @classmethod
    async def get_mem(cls, task_id: int) -> dict | None:
        return _tasks.get(task_id)

    @classmethod
    async def set_status_mem(cls, task_id: int, status: int) -> dict | None:
        t = _tasks.get(task_id)
        if t is None:
            return None
        t["status"] = status
        return t

    @classmethod
    async def delete_mem(cls, task_id: int) -> dict:
        _tasks.pop(task_id, None)
        _logs.pop(task_id, None)
        return {"deleted": task_id}


@router.post("", response_model=ScheduleOut)
async def create_schedule(req: ScheduleCreate, session: AsyncSession = Depends(get_db)) -> ScheduleOut:
    """创建定时任务."""
    try:
        task = await ScheduleService.create(session, req.name, req.cron_expr, req.func_path)
    except Exception as exc:  # noqa: BLE001
        ScheduleService._fallback("scheduler.create", exc)
        task = await ScheduleService.create_mem(req.name, req.cron_expr, req.func_path)
    scheduler = get_scheduler()
    if scheduler is not None and req.func_path:
        try:
            scheduler.add_job(_run_task, trigger="cron", args=[task["id"]], replace_existing=False)
        except Exception:  # noqa: BLE001
            logger.warning("scheduler add_job failed", extra={"task_id": task["id"]})
    return _to_out(task)


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(session: AsyncSession = Depends(get_db)) -> list[ScheduleOut]:
    """任务列表."""
    try:
        tasks = await ScheduleService.list_all(session)
    except Exception as exc:  # noqa: BLE001
        ScheduleService._fallback("scheduler.list", exc)
        tasks = await ScheduleService.list_all_mem()
    return [_to_out(t) for t in tasks]


@router.post("/{task_id}/start", response_model=ScheduleOut)
async def start_schedule(task_id: int, session: AsyncSession = Depends(get_db)) -> ScheduleOut:
    """启动任务（status=1）."""
    try:
        task = await ScheduleService.set_status(session, task_id, 1)
    except Exception as exc:  # noqa: BLE001
        ScheduleService._fallback("scheduler.start", exc)
        task = await ScheduleService.set_status_mem(task_id, 1)
    if task is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.NOT_FOUND, f"task {task_id} not found")
    return _to_out(task)


@router.post("/{task_id}/stop", response_model=ScheduleOut)
async def stop_schedule(task_id: int, session: AsyncSession = Depends(get_db)) -> ScheduleOut:
    """停止任务（status=0）."""
    try:
        task = await ScheduleService.set_status(session, task_id, 0)
    except Exception as exc:  # noqa: BLE001
        ScheduleService._fallback("scheduler.stop", exc)
        task = await ScheduleService.set_status_mem(task_id, 0)
    if task is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.NOT_FOUND, f"task {task_id} not found")
    return _to_out(task)


@router.get("/{task_id}/logs", response_model=list[dict])
async def task_logs(task_id: int, session: AsyncSession = Depends(get_db)) -> list[dict]:
    """任务执行日志（内存，DB 版本后续接入 schedule_logs 表）."""
    return _logs.get(task_id, [])


@router.delete("/{task_id}")
async def delete_schedule(task_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    """删除任务."""
    try:
        return await ScheduleService.delete(session, task_id)
    except Exception as exc:  # noqa: BLE001
        ScheduleService._fallback("scheduler.delete", exc)
        return await ScheduleService.delete_mem(task_id)

__version__ = "1.1.0"
