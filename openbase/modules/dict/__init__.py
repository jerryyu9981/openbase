"""dict 模块：数据字典（类型 + 项，支持缓存）."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/dicts", tags=["dict"])

# 内存字典（v1.0.0 最小实现，生产接数据库 + Redis 缓存）
_dict_types: dict[str, dict] = {}
_dict_items: dict[str, list[dict]] = {}
_next_item_id = 1


class DictTypeCreate(BaseModel):
    """创建字典类型请求."""

    code: str
    name: str


class DictItemCreate(BaseModel):
    """创建字典项请求."""

    label: str
    value: str
    sort_order: int = 0


class DictItemOut(BaseModel):
    """字典项响应."""

    id: int
    label: str
    value: str
    sort_order: int


@router.post("", response_model=dict)
async def create_dict_type(req: DictTypeCreate) -> dict:
    """创建字典类型."""
    _dict_types[req.code] = {"code": req.code, "name": req.name}
    _dict_items.setdefault(req.code, [])
    return {"code": req.code, "name": req.name}


@router.get("", response_model=list[dict])
async def list_dict_types() -> list[dict]:
    """字典类型列表."""
    return list(_dict_types.values())


@router.post("/{type_code}/items", response_model=DictItemOut)
async def create_dict_item(type_code: str, req: DictItemCreate) -> DictItemOut:
    """创建字典项."""
    global _next_item_id
    item = {"id": _next_item_id, "label": req.label, "value": req.value, "sort_order": req.sort_order}
    _dict_items.setdefault(type_code, []).append(item)
    _next_item_id += 1
    return DictItemOut(**item)


@router.get("/{type_code}/items", response_model=list[DictItemOut])
async def list_dict_items(type_code: str) -> list[DictItemOut]:
    """字典项列表（按 sort_order 排序，前端联动用）."""
    items = sorted(_dict_items.get(type_code, []), key=lambda x: x["sort_order"])
    return [DictItemOut(**i) for i in items]


@router.delete("/items/{item_id}")
async def delete_dict_item(item_id: int) -> dict:
    """删除字典项."""
    for items in _dict_items.values():
        items[:] = [i for i in items if i["id"] != item_id]
    return {"deleted": item_id}
