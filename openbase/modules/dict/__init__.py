"""dict 模块：数据字典（类型 + 项，数据库优先 + 内存回退）."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.db.services import BaseDBService
from openbase.core.db.session import get_db
from openbase.core.models import DictItem, DictType

logger = logging.getLogger("openbase.dict")

router = APIRouter(prefix="/api/v1/dicts", tags=["dict"])

# 内存回退存储（数据库不可用时降级）
_memory_types: dict[str, dict] = {}
_memory_items: dict[str, list[dict]] = {}
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


class DictService(BaseDBService):
    """字典服务：数据库优先 + 内存回退 + Redis 缓存."""

    CACHE_TTL = 300  # 对齐设计文档 dict 缓存 TTL 5min

    @classmethod
    def _cache_key(cls, type_code: str) -> str:
        return f"dict:{type_code}:items"

    @classmethod
    async def create_type(cls, session: AsyncSession, code: str, name: str) -> dict:
        existing = (
            await session.execute(select(DictType).where(DictType.code == code))
        ).scalar_one_or_none()
        if existing is None:
            session.add(DictType(code=code, name=name))
            await session.commit()
        return {"code": code, "name": name}

    @classmethod
    async def list_types(cls, session: AsyncSession) -> list[dict]:
        rows = (await session.execute(select(DictType).order_by(DictType.id))).scalars().all()
        return [{"code": r.code, "name": r.name} for r in rows]

    @classmethod
    async def create_item(
        cls, session: AsyncSession, type_code: str, label: str, value: str, sort_order: int
    ) -> dict:
        t = (
            await session.execute(select(DictType).where(DictType.code == type_code))
        ).scalar_one_or_none()
        if t is None:
            t = DictType(code=type_code, name=type_code)
            session.add(t)
            await session.flush()
        item = DictItem(type_id=t.id, label=label, value=value, sort_order=sort_order)
        session.add(item)
        await session.commit()
        # 缓存失效（写入后旧缓存不可用）
        from openbase.core.cache.redis_client import cache_delete

        cache_delete(cls._cache_key(type_code))
        return {"id": item.id, "label": label, "value": value, "sort_order": sort_order}

    @classmethod
    async def list_items(cls, session: AsyncSession, type_code: str) -> list[dict]:
        # Redis 缓存优先（读高频路径）
        from openbase.core.cache.redis_client import cache_get

        cached = cache_get(cls._cache_key(type_code))
        if cached is not None:
            return cached
        t = (
            await session.execute(select(DictType).where(DictType.code == type_code))
        ).scalar_one_or_none()
        if t is None:
            return []
        rows = (
            await session.execute(
                select(DictItem)
                .where(DictItem.type_id == t.id)
                .order_by(DictItem.sort_order)
            )
        ).scalars().all()
        result = [
            {"id": r.id, "label": r.label, "value": r.value, "sort_order": r.sort_order}
            for r in rows
        ]
        # 写缓存（Redis 不可用时静默跳过，不影响返回）
        from openbase.core.cache.redis_client import cache_set

        cache_set(cls._cache_key(type_code), result, ttl=cls.CACHE_TTL)
        return result

    @classmethod
    async def delete_item(cls, session: AsyncSession, item_id: int) -> dict:
        row = (
            await session.execute(select(DictItem).where(DictItem.id == item_id))
        ).scalar_one_or_none()
        if row is not None:
            type_code = None
            # 查 type_code 用于缓存失效
            type_row = (
                await session.execute(select(DictType).where(DictType.id == row.type_id))
            ).scalar_one_or_none()
            if type_row is not None:
                type_code = type_row.code
            await session.delete(row)
            await session.commit()
            if type_code:
                from openbase.core.cache.redis_client import cache_delete

                cache_delete(cls._cache_key(type_code))
        return {"deleted": item_id}

    # ---- 内存回退路径 ----
    @classmethod
    async def create_type_mem(cls, code: str, name: str) -> dict:
        _memory_types[code] = {"code": code, "name": name}
        _memory_items.setdefault(code, [])
        return {"code": code, "name": name}

    @classmethod
    async def list_types_mem(cls) -> list[dict]:
        return list(_memory_types.values())

    @classmethod
    async def create_item_mem(cls, type_code: str, label: str, value: str, sort_order: int) -> dict:
        global _next_item_id
        item = {"id": _next_item_id, "label": label, "value": value, "sort_order": sort_order}
        _memory_items.setdefault(type_code, []).append(item)
        _next_item_id += 1
        return item

    @classmethod
    async def list_items_mem(cls, type_code: str) -> list[dict]:
        return sorted(_memory_items.get(type_code, []), key=lambda x: x["sort_order"])

    @classmethod
    async def delete_item_mem(cls, item_id: int) -> dict:
        for items in _memory_items.values():
            items[:] = [i for i in items if i["id"] != item_id]
        return {"deleted": item_id}


@router.post("", response_model=dict)
async def create_dict_type(req: DictTypeCreate, session: AsyncSession = Depends(get_db)) -> dict:
    """创建字典类型."""
    try:
        return await DictService.create_type(session, req.code, req.name)
    except Exception as exc:  # noqa: BLE001
        DictService._fallback("dict.create_type", exc)
        return await DictService.create_type_mem(req.code, req.name)


@router.get("", response_model=list[dict])
async def list_dict_types(session: AsyncSession = Depends(get_db)) -> list[dict]:
    """字典类型列表."""
    try:
        return await DictService.list_types(session)
    except Exception as exc:  # noqa: BLE001
        DictService._fallback("dict.list_types", exc)
        return await DictService.list_types_mem()


@router.post("/{type_code}/items", response_model=DictItemOut)
async def create_dict_item(
    type_code: str, req: DictItemCreate, session: AsyncSession = Depends(get_db)
) -> DictItemOut:
    """创建字典项."""
    try:
        item = await DictService.create_item(
            session, type_code, req.label, req.value, req.sort_order
        )
    except Exception as exc:  # noqa: BLE001
        DictService._fallback("dict.create_item", exc)
        item = await DictService.create_item_mem(type_code, req.label, req.value, req.sort_order)
    return DictItemOut(**item)


@router.get("/{type_code}/items", response_model=list[DictItemOut])
async def list_dict_items(
    type_code: str, session: AsyncSession = Depends(get_db)
) -> list[DictItemOut]:
    """字典项列表（按 sort_order 排序，前端联动用）."""
    try:
        items = await DictService.list_items(session, type_code)
    except Exception as exc:  # noqa: BLE001
        DictService._fallback("dict.list_items", exc)
        items = await DictService.list_items_mem(type_code)
    return [DictItemOut(**i) for i in items]


@router.delete("/items/{item_id}")
async def delete_dict_item(
    item_id: int, session: AsyncSession = Depends(get_db)
) -> dict:
    """删除字典项."""
    try:
        return await DictService.delete_item(session, item_id)
    except Exception as exc:  # noqa: BLE001
        DictService._fallback("dict.delete_item", exc)
        return await DictService.delete_item_mem(item_id)

__version__ = "1.1.0"
