"""ai_apps 模块：AI 应用管理（v1.2.0 全新补建）.

OpenLLM 无应用管理能力，本模块由 openbase 提供最小 API：
应用 CRUD + 发布（版本递增）+ 调用记录。默认内存存储，
数据库表（ai_apps/ai_app_versions/ai_app_calls）已在 core.models.business 建模，
后续可接入持久化。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.ai_apps")

router = APIRouter(prefix="/api/v1/ai-apps", tags=["ai-apps"])

__all__ = ["AiAppService", "router"]


class ModelConfig(BaseModel):
    """模型配置（应用绑定模型）."""

    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    parameters: dict[str, Any] = Field(default_factory=dict)


class AiAppCreateRequest(BaseModel):
    """创建 AI 应用请求."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    llm_config: ModelConfig
    prompt_template_id: int | None = None


class AiAppUpdateRequest(BaseModel):
    """更新 AI 应用请求."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    llm_config: ModelConfig | None = None
    prompt_template_id: int | None = None


class AiAppService:
    """AI 应用存储服务（内存实现，接口对齐设计文档数据字典）."""

    _apps: dict[str, dict] = {}
    _versions: dict[str, list[dict]] = {}
    _calls: dict[str, list[dict]] = {}
    _seq: int = 0

    @classmethod
    def _reset(cls) -> None:
        cls._apps.clear()
        cls._versions.clear()
        cls._calls.clear()
        cls._seq = 0

    def _next_id(self) -> str:
        cls = type(self)
        cls._seq += 1
        return f"app-{cls._seq}"

    def create(self, name: str, model_config: dict, description: str | None = None,
               prompt_template_id: int | None = None) -> dict:
        app_id = self._next_id()
        app = {
            "id": app_id,
            "name": name,
            "description": description,
            "model_config": model_config,
            "prompt_template_id": prompt_template_id,
            "status": "draft",
            "current_version": None,
            "created_by": None,
            "created_at": None,
        }
        type(self)._apps[app_id] = app
        logger.info("ai app created", extra={"app_id": app_id, "name": name})
        return app

    def get(self, app_id: str) -> dict | None:
        return type(self)._apps.get(app_id)

    def list_apps(self) -> list[dict]:
        return list(type(self)._apps.values())

    def update(self, app_id: str, **changes: Any) -> dict:
        app = self.get(app_id)
        if app is None:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"ai app not found: {app_id}")
        for key in ("name", "description", "model_config", "prompt_template_id"):
            if key in changes and changes[key] is not None:
                app[key] = changes[key]
        return app

    def publish(self, app_id: str) -> dict:
        app = self.get(app_id)
        if app is None:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"ai app not found: {app_id}")
        current = app.get("current_version")
        next_version = self._next_version(current)
        app["current_version"] = next_version
        app["status"] = "published"
        versions = type(self)._versions.setdefault(app_id, [])
        versions.append({
            "version": next_version,
            "model_config_snapshot": app["model_config"],
            "published_at": None,
        })
        logger.info("ai app published", extra={"app_id": app_id, "version": next_version})
        return app

    @staticmethod
    def _next_version(current: str | None) -> str:
        if current is None:
            return "v1"
        try:
            number = int(current.removeprefix("v"))
        except ValueError:
            number = 0
        return f"v{number + 1}"

    def unpublish(self, app_id: str) -> dict:
        app = self.get(app_id)
        if app is None:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"ai app not found: {app_id}")
        app["status"] = "offline"
        return app

    def versions(self, app_id: str) -> list[dict]:
        return type(self)._versions.get(app_id, [])

    def record_call(self, app_id: str, user_id: int | None = None,
                    input_tokens: int = 0, output_tokens: int = 0,
                    latency_ms: int = 0, status: str = "success",
                    error_code: str | None = None) -> dict:
        call = {
            "id": str(uuid.uuid4()),
            "app_id": app_id,
            "version": self.get(app_id).get("current_version") if self.get(app_id) else None,
            "user_id": user_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_ms": latency_ms,
            "status": status,
            "error_code": error_code,
            "created_at": None,
        }
        type(self)._calls.setdefault(app_id, []).append(call)
        return call

    def calls(self, app_id: str) -> list[dict]:
        return type(self)._calls.get(app_id, [])

    def delete(self, app_id: str) -> None:
        if app_id not in type(self)._apps:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"ai app not found: {app_id}")
        del type(self)._apps[app_id]
        type(self)._versions.pop(app_id, None)
        type(self)._calls.pop(app_id, None)
        logger.info("ai app deleted", extra={"app_id": app_id})


def _service() -> AiAppService:
    return AiAppService()


# ---- 路由 ----

@router.get("")
def list_apps(user: dict = Depends(get_current_user)) -> dict:
    """应用列表（分页包装）."""
    items = _service().list_apps()
    return {"code": 0, "message": "ok", "data": {"items": items, "total": len(items)}}


@router.post("")
def create_app(payload: AiAppCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    """创建 AI 应用."""
    app = _service().create(
        name=payload.name,
        description=payload.description,
        model_config=payload.llm_config.model_dump(),
        prompt_template_id=payload.prompt_template_id,
    )
    return {"code": 0, "message": "ok", "data": app}


@router.get("/{app_id}")
def get_app(app_id: str, user: dict = Depends(get_current_user)) -> dict:
    """应用详情."""
    app = _service().get(app_id)
    if app is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"ai app not found: {app_id}")
    return {"code": 0, "message": "ok", "data": app}


@router.put("/{app_id}")
def update_app(app_id: str, payload: AiAppUpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    """更新应用."""
    app = _service().update(
        app_id,
        name=payload.name,
        description=payload.description,
        model_config=payload.llm_config.model_dump() if payload.llm_config else None,
        prompt_template_id=payload.prompt_template_id,
    )
    return {"code": 0, "message": "ok", "data": app}


@router.delete("/{app_id}")
def delete_app(app_id: str, user: dict = Depends(get_current_user)) -> dict:
    """删除应用."""
    _service().delete(app_id)
    return {"code": 0, "message": "ok", "data": None}


@router.post("/{app_id}/publish")
def publish_app(app_id: str, user: dict = Depends(get_current_user)) -> dict:
    """发布应用（版本递增）."""
    app = _service().publish(app_id)
    return {"code": 0, "message": "ok", "data": app}


@router.post("/{app_id}/unpublish")
def unpublish_app(app_id: str, user: dict = Depends(get_current_user)) -> dict:
    """下架应用."""
    app = _service().unpublish(app_id)
    return {"code": 0, "message": "ok", "data": app}


@router.get("/{app_id}/versions")
def list_versions(app_id: str, user: dict = Depends(get_current_user)) -> dict:
    """版本列表."""
    return {"code": 0, "message": "ok", "data": {"items": _service().versions(app_id), "total": 0}}


@router.get("/{app_id}/calls")
def list_calls(app_id: str, user: dict = Depends(get_current_user)) -> dict:
    """调用记录."""
    items = _service().calls(app_id)
    return {"code": 0, "message": "ok", "data": {"items": items, "total": len(items)}}


__version__ = "1.2.0"
