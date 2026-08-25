"""BaseCRUDRouter：FastAPI 通用 CRUD 路由自动生成."""

from typing import Annotated, Generic, TypeVar

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel

from openbase.core.deps import get_current_user

T = TypeVar("T", bound=BaseModel)


class PageResult(BaseModel, Generic[T]):
    """分页响应."""

    items: list[T]
    total: int
    page: int
    page_size: int


class BaseCRUDRouter(APIRouter, Generic[T]):
    """通用 CRUD 路由生成器.

    用法::

        router = BaseCRUDRouter(
            prefix="/api/v1/books",
            create_schema=BookCreate,
            out_schema=BookOut,
            store=store_dict,
        )

    自动生成: GET list（分页/搜索/排序）、GET detail、POST create、PUT update、DELETE delete。
    生成接口与手写等价（直连数据存储，无额外包装）。
    """

    def __init__(
        self,
        prefix: str,
        create_schema: type[T],
        out_schema: type[T],
        store: dict[int, dict],
        search_fields: list[str] | None = None,
        id_key: str = "id",
        tags: list[str] | None = None,
        require_auth: bool = True,
    ) -> None:
        super().__init__(prefix=prefix, tags=tags or [prefix.strip("/")])
        self.create_schema = create_schema
        self.out_schema = out_schema
        self.store = store
        self.search_fields = search_fields or []
        self.id_key = id_key
        self._seq = max(store.keys(), default=0)
        self._deps = [Depends(get_current_user)] if require_auth else []
        self._register_routes()

    def _register_routes(self) -> None:
        store = self.store
        search_fields = self.search_fields
        id_key = self.id_key
        out_schema = self.out_schema
        create_schema = self.create_schema

        @self.get("", response_model=PageResult[out_schema], dependencies=self._deps)
        async def list_items(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            search: str | None = Query(None),
            sort: str | None = Query(None),
            order: str = Query("desc"),
        ) -> PageResult[out_schema]:
            items = list(store.values())
            if search and search_fields:
                keyword = search.lower()
                items = [
                    it
                    for it in items
                    if any(keyword in str(it.get(f, "")).lower() for f in search_fields)
                ]
            if sort and sort in (next(iter(store.values()), {}) or {}):
                items.sort(key=lambda x: x.get(sort), reverse=(order == "desc"))
            total = len(items)
            start = (page - 1) * page_size
            return PageResult[out_schema](  # type: ignore[valid-type]
                items=[out_schema(**it) for it in items[start : start + page_size]],
                total=total,
                page=page,
                page_size=page_size,
            )

        @self.get("/{item_id}", response_model=out_schema, dependencies=self._deps)
        async def get_item(item_id: int) -> out_schema:
            from openbase.core.errors import BaseError, ErrorCode

            item = store.get(item_id)
            if item is None:
                raise BaseError(ErrorCode.PARAM_NOT_FOUND, "item not found")
            return out_schema(**item)

        @self.post("", response_model=out_schema, dependencies=self._deps)
        async def create_item(payload: Annotated[create_schema, Body()]) -> out_schema:
            data = payload.model_dump()
            self._seq += 1
            data[id_key] = self._seq
            store[self._seq] = data
            return out_schema(**data)

        @self.put("/{item_id}", response_model=out_schema, dependencies=self._deps)
        async def update_item(
            item_id: int, payload: Annotated[create_schema, Body()]
        ) -> out_schema:
            from openbase.core.errors import BaseError, ErrorCode

            if item_id not in store:
                raise BaseError(ErrorCode.PARAM_NOT_FOUND, "item not found")
            data = payload.model_dump()
            data[id_key] = item_id
            store[item_id] = data
            return out_schema(**data)

        @self.delete("/{item_id}", dependencies=self._deps)
        async def delete_item(item_id: int) -> dict:
            store.pop(item_id, None)
            return {"deleted": item_id}
