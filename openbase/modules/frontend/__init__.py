"""frontend 模块：统一前端动态模块注册 API（v1.2.0）.

提供 /api/v1/modules 供前端 ModuleRegistry 获取模块注册表
（模块 ID/名称/路由前缀/入口/权限标识/状态）。
默认内存注册表，dynamic_modules 表（core.models.business）可持久化。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from openbase.core.deps.auth import get_current_user

logger = logging.getLogger("openbase.frontend")

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])

__all__ = ["ModuleService", "router"]

# 模块注册表（对齐系统架构设计文档 §6：模块ID/路由前缀/权限标识）
DEFAULT_MODULES: list[dict] = [
    {
        "id": "openllm",
        "name": "OpenLLM",
        "icon": "chat",
        "route_prefix": "/openllm",
        "entry": "modules/openllm",
        "permission": "openllm:view",
        "status": "enabled",
        "sort_order": 10,
    },
    {
        "id": "knowledge",
        "name": "知识库",
        "icon": "collection",
        "route_prefix": "/knowledge",
        "entry": "modules/knowledge",
        "permission": "openrag:view",
        "status": "enabled",
        "sort_order": 20,
    },
    {
        "id": "memory",
        "name": "记忆",
        "icon": "memo",
        "route_prefix": "/memory",
        "entry": "modules/memory",
        "permission": "openmemory:view",
        "status": "enabled",
        "sort_order": 30,
    },
    {
        "id": "portrait",
        "name": "画像",
        "icon": "user",
        "route_prefix": "/portrait",
        "entry": "modules/portrait",
        "permission": "dps:view",
        "status": "enabled",
        "sort_order": 40,
    },
]


class ModuleService:
    """动态模块注册服务（内存实现，dynamic_modules 表可持久化）."""

    def list_modules(self) -> list[dict]:
        return [dict(item) for item in DEFAULT_MODULES]

    def get_module(self, module_id: str) -> dict | None:
        for item in DEFAULT_MODULES:
            if item["id"] == module_id:
                return dict(item)
        return None


@router.get("")
def list_modules(user: dict = Depends(get_current_user)) -> dict:
    """模块注册表."""
    items = ModuleService().list_modules()
    return {"code": 0, "message": "ok", "data": {"items": items, "total": len(items)}}


@router.get("/{module_id}")
def get_module(module_id: str, user: dict = Depends(get_current_user)) -> dict:
    """模块详情."""
    item = ModuleService().get_module(module_id)
    if item is None:
        from openbase.core.errors import BaseError, ErrorCode

        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"module not found: {module_id}")
    return {"code": 0, "message": "ok", "data": item}


__version__ = "1.2.0"
