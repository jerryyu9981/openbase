"""org 模块：组织架构（部门树，数据库优先 + 内存回退）."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.services import BaseDBService
from openbase.core.db.session import get_db
from openbase.core.models import Department

logger = logging.getLogger("openbase.org")

router = APIRouter(prefix="/api/v1/org/departments", tags=["org"])

# 内存回退存储
_memory_departments: dict[int, dict] = {}
_next_id = 1


class DepartmentCreate(BaseModel):
    """创建部门请求."""

    name: str
    parent_id: int | None = None


class DepartmentOut(BaseModel):
    """部门响应."""

    id: int
    name: str
    parent_id: int | None
    path: str


def _make_path(dep: dict) -> str:
    if dep.get("parent_id"):
        parent = _memory_departments.get(dep["parent_id"])
        if parent:
            return f"{parent['path']}/{dep['id']}"
    return f"/{dep['id']}"


class DepartmentService(BaseDBService):
    """部门服务：数据库优先 + 内存回退."""

    @classmethod
    async def create(cls, session: AsyncSession, name: str, parent_id: int | None) -> dict:
        # 计算 path（父路径 + 自身 id）
        prefix = ""
        if parent_id:
            parent = (
                await session.execute(select(Department).where(Department.id == parent_id))
            ).scalar_one_or_none()
            if parent is not None:
                prefix = parent.path
        dep = Department(name=name, parent_id=parent_id, path="")
        session.add(dep)
        await session.flush()
        dep.path = f"{prefix}/{dep.id}"
        await session.commit()
        return {"id": dep.id, "name": dep.name, "parent_id": dep.parent_id, "path": dep.path}

    @classmethod
    async def list_all(cls, session: AsyncSession) -> list[dict]:
        rows = (await session.execute(select(Department).order_by(Department.id))).scalars().all()
        return [
            {"id": r.id, "name": r.name, "parent_id": r.parent_id, "path": r.path}
            for r in rows
        ]

    @classmethod
    async def delete(cls, session: AsyncSession, dep_id: int) -> dict:
        row = (
            await session.execute(select(Department).where(Department.id == dep_id))
        ).scalar_one_or_none()
        if row is not None:
            await session.delete(row)
            await session.commit()
        return {"deleted": dep_id}

    # ---- 内存回退 ----
    @classmethod
    async def create_mem(cls, name: str, parent_id: int | None) -> dict:
        global _next_id
        dep = {"id": _next_id, "name": name, "parent_id": parent_id, "path": ""}
        _memory_departments[_next_id] = dep
        dep["path"] = _make_path(dep)
        _next_id += 1
        return dep

    @classmethod
    async def list_all_mem(cls) -> list[dict]:
        return list(_memory_departments.values())

    @classmethod
    async def delete_mem(cls, dep_id: int) -> dict:
        _memory_departments.pop(dep_id, None)
        return {"deleted": dep_id}


def _build_tree(rows: list[dict]) -> list[dict]:
    """按 parent_id 组装部门树."""
    by_id = {d["id"]: {**d, "children": []} for d in rows}
    roots: list[dict] = []
    for d in rows:
        node = by_id[d["id"]]
        pid = d.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            roots.append(node)
    return roots


@router.post("", response_model=DepartmentOut)
async def create_department(
    req: DepartmentCreate, session: AsyncSession = Depends(get_db)
) -> DepartmentOut:
    """创建部门."""
    try:
        dep = await DepartmentService.create(session, req.name, req.parent_id)
    except Exception as exc:  # noqa: BLE001
        DepartmentService._fallback("org.create", exc)
        dep = await DepartmentService.create_mem(req.name, req.parent_id)
    return DepartmentOut(**dep)


@router.get("", response_model=list[DepartmentOut])
async def list_departments(session: AsyncSession = Depends(get_db)) -> list[DepartmentOut]:
    """部门列表（平铺，含 path 层级）."""
    try:
        rows = await DepartmentService.list_all(session)
    except Exception as exc:  # noqa: BLE001
        DepartmentService._fallback("org.list", exc)
        rows = await DepartmentService.list_all_mem()
    return [DepartmentOut(**d) for d in rows]


@router.get("/tree", response_model=list[dict])
async def department_tree(session: AsyncSession = Depends(get_db)) -> list[dict]:
    """部门树（按 parent_id 组装）."""
    try:
        rows = await DepartmentService.list_all(session)
    except Exception as exc:  # noqa: BLE001
        DepartmentService._fallback("org.tree", exc)
        rows = await DepartmentService.list_all_mem()
    return _build_tree(rows)


@router.delete("/{dep_id}")
async def delete_department(
    dep_id: int, session: AsyncSession = Depends(get_db)
) -> dict:
    """删除部门."""
    try:
        return await DepartmentService.delete(session, dep_id)
    except Exception as exc:  # noqa: BLE001
        DepartmentService._fallback("org.delete", exc)
        return await DepartmentService.delete_mem(dep_id)
