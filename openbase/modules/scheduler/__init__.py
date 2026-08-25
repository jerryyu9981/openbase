"""scheduler 模块：定时任务（APScheduler 封装 + 任务 CRUD + 执行日志）."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("openbase.scheduler")

router = APIRouter(prefix="/api/v1/schedules", tags=["scheduler"])

# 内存任务存储（v1.0.0 最小实现，生产接数据库）
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


@router.post("", response_model=ScheduleOut)
async def create_schedule(req: ScheduleCreate) -> ScheduleOut:
    """创建定时任务."""
    global _next_task_id
    task = {
        "id": _next_task_id,
        "name": req.name,
        "cron_expr": req.cron_expr,
        "func_path": req.func_path,
        "status": 1,
        "last_run_at": None,
        "next_run_at": None,
    }
    _tasks[_next_task_id] = task
    _logs.setdefault(_next_task_id, [])

    scheduler = get_scheduler()
    if scheduler is not None and req.func_path:
        try:
            scheduler.add_job(
                _run_task,
                trigger="cron",
                hour=int(req.cron_expr.split()[1]),
                minute=int(req.cron_expr.split()[0]),
                args=[_next_task_id, req.func_path],
                id=f"task-{_next_task_id}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to schedule job", extra={"task": req.name, "error": str(exc)})

    _next_task_id += 1
    return ScheduleOut(**task)


def _run_task(task_id: int, func_path: str) -> None:
    """任务执行包装（记录日志）."""
    try:
        module_name, _, func_name = func_path.rpartition(".")
        if module_name:
            module = __import__(module_name, fromlist=[func_name])
            getattr(module, func_name)()
        _logs.setdefault(task_id, []).append({"status": "success", "message": "ok"})
    except Exception as exc:  # noqa: BLE001
        _logs.setdefault(task_id, []).append({"status": "failed", "message": str(exc)})


@router.get("", response_model=list[ScheduleOut])
async def list_schedules() -> list[ScheduleOut]:
    """任务列表."""
    return [ScheduleOut(**t) for t in _tasks.values()]


@router.post("/{task_id}/start", response_model=ScheduleOut)
async def start_schedule(task_id: int) -> ScheduleOut:
    """启动任务."""
    task = _tasks.get(task_id)
    if task:
        task["status"] = 1
    return ScheduleOut(**task)


@router.post("/{task_id}/stop", response_model=ScheduleOut)
async def stop_schedule(task_id: int) -> ScheduleOut:
    """停止任务."""
    task = _tasks.get(task_id)
    if task:
        task["status"] = 0
    return ScheduleOut(**task)


@router.delete("/{task_id}")
async def delete_schedule(task_id: int) -> dict:
    """删除任务."""
    _tasks.pop(task_id, None)
    return {"deleted": task_id}


@router.get("/{task_id}/logs", response_model=list[dict])
async def schedule_logs(task_id: int) -> list[dict]:
    """任务执行日志."""
    return _logs.get(task_id, [])
