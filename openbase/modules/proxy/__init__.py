"""proxy 模块：四系统特色 API 代理（v1.2.0）.

统一前端只与 openbase 后端通信；本模块提供 /api/v1/proxy/{system}/{path}
代理转发到四系统（OpenLLM/OpenRAG/OpenMemory/DPS）原生 API。
后端校验 JWT 后按路由表转发，响应统一包装为 ErrorResponse 契约。

system 映射与 base_url 可通过 config 模块配置覆盖（默认指向 Dev 示例端口）。
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.proxy")

router = APIRouter(prefix="/api/v1/proxy", tags=["proxy"])

__all__ = ["PROXY_SYSTEMS", "router"]

# 四系统代理路由表（base_url 可由 config 模块覆盖；此处为 Dev 默认）
PROXY_SYSTEMS: dict[str, dict] = {
    "openllm": {"base_url": "http://127.0.0.1:8001", "timeout": 10.0},
    "openrag": {"base_url": "http://127.0.0.1:8010", "timeout": 10.0},
    "openmemory": {"base_url": "http://127.0.0.1:8020", "timeout": 10.0},
    "dps": {"base_url": "http://127.0.0.1:8030", "timeout": 10.0},
}


def _resolve_base_url(system: str) -> str:
    """解析系统 base_url（优先 config 模块配置，其次默认表）.

    配置键：proxy.{system}.base_url（system 级）。
    """
    try:
        from openbase.modules.config import ConfigStore

        value = ConfigStore.get(f"proxy.{system}.base_url")
        if value:
            return str(value)
    except Exception:  # noqa: BLE001
        pass
    return PROXY_SYSTEMS[system]["base_url"]


def _timeout(system: str) -> float:
    return PROXY_SYSTEMS[system]["timeout"]


@router.api_route("/{system}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(
    system: str,
    path: str,
    request: Request,
    user: dict = Depends(get_current_user),
) -> JSONResponse:
    """代理转发：JWT 校验后转发四系统原生 API.

    支持路径参数透传；上游不可达时返回统一 SYS_502 错误包装。
    """
    if system not in PROXY_SYSTEMS:
        raise BaseError(ErrorCode.PARAM_NOT_FOUND, f"unknown proxy system: {system}")

    base_url = _resolve_base_url(system)
    target_url = f"{base_url.rstrip('/')}/{path}"
    method = request.method
    headers = {
        "Content-Type": request.headers.get("Content-Type", "application/json"),
        "Accept": request.headers.get("Accept", "application/json"),
    }
    body = await request.body() if method in ("POST", "PUT", "PATCH") else None

    try:
        async with httpx.AsyncClient(timeout=_timeout(system)) as client:
            upstream = await client.request(
                method, target_url, headers=headers, content=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("proxy upstream unreachable", extra={"system": system, "path": path, "error": str(exc)})
        raise BaseError(ErrorCode.SYS_UPSTREAM_ERROR, f"upstream {system} unreachable") from exc

    # 上游 402（模型提供商余额不足）→ 统一包装 BIZ_MODEL_QUOTA，不暴露上游原始响应
    if upstream.status_code == 402:
        logger.info(
            "proxy upstream payment required",
            extra={"system": system, "path": path, "status": upstream.status_code},
        )
        return JSONResponse(
            status_code=402,
            content={
                "code": ErrorCode.BIZ_MODEL_QUOTA.value,
                "message": "模型服务余额不足，请联系管理员充值",
                "detail": "upstream payment required",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    # 透传上游状态码与数据（响应体保持 JSON 透传，错误已由上游契约保证）
    try:
        payload = upstream.json()
    except ValueError:
        payload = {"raw": upstream.text[:2000]}
    return JSONResponse(status_code=upstream.status_code, content=payload)


__version__ = "1.3.0"
