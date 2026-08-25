"""org 模块：组织架构（部门树）."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/org/departments", tags=["org"])

# 内存部门树（v1.0.0 最小实现，生产接数据库）
_departments: dict[int, dict] = {}
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
        parent = _departments.get(dep["parent_id"])
        if parent:
            return f"{parent['path']}/{dep['id']}"
    return f"/{dep['id']}"


@router.post("", response_model=DepartmentOut)
async def create_department(req: DepartmentCreate) -> DepartmentOut:
    """创建部门."""
    global _next_id
    dep = {
        "id": _next_id,
        "name": req.name,
        "parent_id": req.parent_id,
        "path": "",
    }
    _departments[_next_id] = dep
    dep["path"] = _make_path(dep)
    _next_id += 1
    return DepartmentOut(**dep)


@router.get("", response_model=list[DepartmentOut])
async def list_departments() -> list[DepartmentOut]:
    """部门列表（平铺，含 path 层级）."""
    return [DepartmentOut(**d) for d in _departments.values()]


@router.get("/tree", response_model=list[dict])
async def department_tree() -> list[dict]:
    """部门树（按 parent_id 组装）."""
    nodes = {i: {**d, "children": []} for i, d in _departments.items()}
    roots: list[dict] = []
    for node in nodes.values():
        pid = node["parent_id"]
        if pid and pid in nodes:
            nodes[pid]["children"].append(node)
        else:
            roots.append(node)
    return roots


@router.delete("/{dep_id}")
async def delete_department(dep_id: int) -> dict:
    """删除部门."""
    _departments.pop(dep_id, None)
    return {"deleted": dep_id}
