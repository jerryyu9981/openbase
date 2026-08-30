"""BaseCRUDRouter：通用 CRUD 路由自动生成（v1.4.1 R-372，对齐完整方案 3.3 工具链）.

以 Service 层为适配目标（保持分层架构约束），Pydantic 模式驱动。
自动生成 5 个端点：GET list / GET {id} / POST / PUT {id} / DELETE {id}。
"""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

T = TypeVar("T")


class BaseCRUDRouter(APIRouter):
    """通用 CRUD 路由工厂（fastapi-crudrouter 模式）.

    Args:
        prefix: 路由前缀（如 /api/v1/items）。
        service: 数据服务（须实现 list/get/create/update/delete）。
        create_schema: 创建请求模式。
        update_schema: 更新请求模式。
        out_schema: 响应模式。
    """

    def __init__(
        self,
        prefix: str,
        service: Any,
        create_schema: type[BaseModel],
        update_schema: type[BaseModel],
        out_schema: type[BaseModel],
        tags: list[str] | None = None,
    ) -> None:
        super().__init__(prefix=prefix, tags=tags or [prefix.strip("/").split("/")[-1]])

        @self.get("", response_model=list[out_schema])
        def _list(
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000),
        ) -> list[Any]:
            """列表（分页）."""
            items = service.list()
            return items[skip : skip + limit]

        @self.get("/{item_id}", response_model=out_schema)
        def _get(item_id: int) -> Any:
            """单条查询."""
            record = service.get(item_id)
            if record is None:
                raise HTTPException(status_code=404, detail="item not found")
            return record

        @self.post("", response_model=out_schema, status_code=200)
        def _create(payload: Any) -> Any:
            """创建."""
            return service.create(payload.model_dump())

        _create.__annotations__["payload"] = create_schema  # FastAPI 需具体类注解

        @self.put("/{item_id}", response_model=out_schema)
        def _update(item_id: int, payload: Any) -> Any:
            """更新（部分字段）."""
            record = service.update(item_id, payload.model_dump(exclude_unset=True))
            if record is None:
                raise HTTPException(status_code=404, detail="item not found")
            return record

        _update.__annotations__["payload"] = update_schema

        @self.delete("/{item_id}", response_model=dict[str, str])
        def _delete(item_id: int) -> dict[str, str]:
            """删除."""
            if not service.delete(item_id):
                raise HTTPException(status_code=404, detail="item not found")
            return {"deleted": str(item_id)}
