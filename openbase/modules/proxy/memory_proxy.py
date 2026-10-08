"""memory-proxy 模块：OpenMemory 双层认证转发（v1.4.2 R-378）.

统一前端/调用方经 OpenBase 访问 OpenMemory 8020，无需持有 OpenMemory 密钥：

- 认证：OpenBase JWT（get_current_user），未认证返回 401。
- 转发注入：X-API-Key（OpenBase 持有）+ 透传原 JWT（Bearer）+ X-Org-ID/X-User-ID
  （供 OpenMemory RBAC/租户上下文识别）。
- 响应适配：统一 {code, message, data, timestamp}；错误码透传
  （200005 缺少 Key / 200001 JWT 无效 等 OpenMemory 语义）。
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.protocol_headers import TARGET_SYSTEM_MEMORY, build_outbound_headers
from openbase.modules.protocol_headers.code_space import get_target_code_space
from openbase.modules.proxy.upstream_observe import (
    UPSTREAM_SYSTEM_OPENMEMORY,
    content_type_of,
    elapsed_ms,
    publish_upstream_response,
)
from openbase.settings import get_settings

logger = logging.getLogger("openbase.memory_proxy")

router = APIRouter(prefix="/api/v1/memory-proxy", tags=["memory-proxy"])

__all__ = ["router"]


def _now_iso() -> str:
    """生成 ISO 8601 时间戳（UTC）."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _upstream_config() -> tuple[str, str, float]:
    """读取上游 OpenMemory 配置（settings，支持 .env 覆盖）."""
    settings = get_settings()
    return (
        settings.memory_api_key,
        settings.memory_upstream_base,
        settings.memory_upstream_timeout,
    )


def _original_bearer_token(request: Request) -> str | None:
    """读取入站 Authorization Bearer token（user JWT 双层认证第二层透传用）.

    sk-agent 场景由调用方判断不传（D-OB6-3：agent 无原 JWT，不构造伪 JWT）。
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


def _effective_subject_id(user: dict) -> str:
    """有效主体 sub（委托时 = delegated.subject_id；否则 principal id）."""
    delegated = user.get("delegated")
    if isinstance(delegated, dict) and delegated.get("subject_id") is not None:
        return str(delegated["subject_id"])
    return str(user.get("id", ""))


def _is_service_agent(user: dict) -> bool:
    """sk-agent 服务账号判定（agent 无原 JWT，不参与双层认证第二层透传）."""
    return str(user.get("auth_method") or "") == "sk-agent"


def _build_upstream_headers(request: Request, user: dict | None) -> dict[str, str]:
    """构造转发上游的请求头（双层认证 + 身份/租户注入，P2-1 §3.5 memory 行）.

    P2-1 T1（K01）：删除 ``_extract_identity`` 二次 JWT 解码，统一经
    ``protocol_headers.inject.build_outbound_headers`` 装配：
    - X-API-Key：OpenBase 持有（服务 Key 通道，第一层认证）
    - Authorization: Bearer <原 JWT>（第二层认证；**仅 user JWT 场景**——agent 场景
      无原 JWT，不再构造伪 JWT 透传，D-OB6-3）
    - X-Org-ID / X-User-ID / X-Tenant-ID / X-User-Role / X-Proxy-Source / X-Request-Id：
      取值只来自统一主体上下文；OB-8/T7 别名收敛后 X-Org-ID == X-Tenant-ID
      （org 不再读独立 org_id/openbase-default 默认链参与隔离键）。
    - 租户兜底（A 批 A1/A2 统一登记入口 `protocol_headers/code_space.py`）：主体无租户
      声明时使用该目标登记的兜底码（memory=``tenant-1``；原为写死字面量 ``"default"``）。
      该值受**上游组织登记**约束：OpenMemory 按组织策略 fail-closed，仅接受已登记组织码。
      修复前其仅登记 ``default``（``tenant-1`` 实测 403「组织不存在或未配置策略」）；
      **已由 C1-a 跨仓修复**（编排器显式登记 ``OPENMEMORY_RBAC__ORG_POLICIES`` 含
      ``tenant-1``/``tenant-2``），故兜底码随统一码空间终态切换为 ``tenant-1``。
    """
    api_key, _, _ = _upstream_config()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": api_key,
    }
    if user is not None and not _is_service_agent(user):
        token = _original_bearer_token(request)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    settings = get_settings()
    space = get_target_code_space(TARGET_SYSTEM_MEMORY)
    return build_outbound_headers(
        request,
        user,
        target_system=TARGET_SYSTEM_MEMORY,
        extra_headers=headers,
        default_tenant=space.default_tenant_code,
        default_role="viewer",
        tenant_value_map=space.reserved_map() or None,
        org_value_map=space.reserved_map() or None,
        enforce_org_alias=settings.enforce_org_alias,
    )


def _adapt_response(upstream: httpx.Response) -> JSONResponse:
    """统一响应适配 {code, message, data, timestamp}.

    2xx：code=0, message="success"，data 为上游完整响应体（核心 API 直接
    返回模型对象，管理/错误为 E 码结构，均透传）。

    非 2xx：透传上游业务码。OpenMemory 错误体形如
    {"code": "E300005", "message": "...", "data": null, "request_id": "..."}、
    {"error": "NOT_FOUND", "message": "..."}（详情 404）、
    {"detail": {"error": "...", "message": "..."}}（pydantic 包装）或
    网关层 {"error": "AUTHENTICATION_ERROR", "message": "..."}。
    提取顺序：body.error > body.code > detail.error/status/code > HTTP 状态码。
    429/5xx 携带 retry_after 时透传到 data 供调用方退避。
    """
    try:
        payload = upstream.json()
    except ValueError:
        payload = {"raw": upstream.text[:2000]}

    if 200 <= upstream.status_code < 300:
        return JSONResponse(
            status_code=upstream.status_code,
            content={
                "code": 0,
                "message": "success",
                "data": payload,
                "timestamp": _now_iso(),
            },
        )

    # 错误码透传
    code = payload.get("error") or payload.get("code")
    message = payload.get("message")
    if code is None:
        detail = payload.get("detail")
        if isinstance(detail, dict):
            code = detail.get("error") or detail.get("code") or detail.get("status")
            message = detail.get("message") or message
        elif isinstance(detail, str):
            message = detail
    if code is None:
        code = upstream.status_code
    data: Any = None
    retry_after = payload.get("retry_after") or (
        (payload.get("data") or {}).get("retry_after")
        if isinstance(payload.get("data"), dict) else None
    )
    if retry_after is not None:
        data = {"retry_after": retry_after}
    return JSONResponse(
        status_code=upstream.status_code,
        content={
            "code": code,
            "message": message or "upstream error",
            "data": data,
            "timestamp": _now_iso(),
        },
    )


async def _forward(
    method: str,
    upstream_path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    form_data: dict[str, str] | None = None,
    headers: dict[str, str],
    request: Request | None = None,
) -> JSONResponse:
    """转发请求至 OpenMemory 并适配响应（C-16 上游专段同请求汇聚）.

    files/form_data 用于 multipart/form-data 透传（多模态/语音上传端点）。
    ``request`` 缺省 None 时仅跳过上游观测（专段挂 ``request.state``），**转发语义不变**。
    """
    _, base_url, timeout = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    upstream_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url,
                json=json_body, params=params, files=files, data=form_data,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        publish_upstream_response(
            request,
            system=UPSTREAM_SYSTEM_OPENMEMORY,
            reached=False,
            duration_ms=elapsed_ms(upstream_start),
            error=str(exc),
        )
        logger.warning(
            "memory-proxy upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"OpenMemory upstream unreachable: {exc}"
        ) from exc
    publish_upstream_response(
        request,
        system=UPSTREAM_SYSTEM_OPENMEMORY,
        reached=True,
        duration_ms=elapsed_ms(upstream_start),
        status_code=upstream.status_code,
        content_type=content_type_of(upstream),
        payload=getattr(upstream, "content", None),
    )
    return _adapt_response(upstream)


async def _forward_raw(
    method: str,
    upstream_path: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str],
    request: Request | None = None,
) -> tuple[int, dict[str, Any]]:
    """转发请求，返回 (上游状态码, 适配后的统一响应体)（C-16 专段随请求汇聚）.

    供需要二次加工（如列表分页）的端点复用。
    """
    _, base_url, timeout = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    upstream_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url, json=json_body, headers=headers,
            )
    except httpx.HTTPError as exc:
        publish_upstream_response(
            request,
            system=UPSTREAM_SYSTEM_OPENMEMORY,
            reached=False,
            duration_ms=elapsed_ms(upstream_start),
            error=str(exc),
        )
        logger.warning(
            "memory-proxy upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"OpenMemory upstream unreachable: {exc}"
        ) from exc
    publish_upstream_response(
        request,
        system=UPSTREAM_SYSTEM_OPENMEMORY,
        reached=True,
        duration_ms=elapsed_ms(upstream_start),
        status_code=upstream.status_code,
        content_type=content_type_of(upstream),
        payload=getattr(upstream, "content", None),
    )
    adapted = _adapt_response(upstream)
    return adapted.status_code, json.loads(adapted.body.decode("utf-8"))


# ---------------------------------------------------------------------------
# 业务端点
# ---------------------------------------------------------------------------


@router.post("/remember")
async def memory_remember(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """存储记忆（POST /api/v1/remember）."""
    return await _forward(
        "POST", "/api/v1/remember",
        json_body=payload, headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.post("/recall")
async def memory_recall(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """召回记忆（POST /api/v1/recall）."""
    return await _forward(
        "POST", "/api/v1/recall",
        json_body=payload, headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.post("/forget")
async def memory_forget(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """删除记忆（POST /api/v1/forget）."""
    return await _forward(
        "POST", "/api/v1/forget",
        json_body=payload, headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.get("/memories/{memory_id}")
async def memory_detail(
    memory_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """记忆详情（GET /api/v1/memories/{id}）."""
    response = await _forward(
        "GET", f"/api/v1/memories/{memory_id}",
        headers=_build_upstream_headers(request, _user),
        request=request,
    )
    # 字段归一化：metadata.tags 提升为顶层 tags（前端消费）
    if response.status_code < 400:
        try:
            body = json.loads(response.body.decode("utf-8"))
            data = body.get("data")
            if isinstance(data, dict) and "metadata" in data:
                meta = data.get("metadata") or {}
                if "tags" not in data:
                    data["tags"] = meta.get("tags") or []
                body["data"] = data
                response = JSONResponse(status_code=response.status_code, content=body)
        except (ValueError, TypeError):
            pass
    return response


@router.get("/memories")
async def memory_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    memory_type: str | None = Query(None),
    tag: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """记忆列表（分页/类型/标签过滤）.

    OpenMemory v6.8.0 无原生持久化列表端点，以 recall 召回适配：
    按当前用户召回全部持久记忆（auto 策略 + 泛化查询），
    proxy 侧完成类型/标签过滤与分页。
    """
    user_id = _effective_subject_id(_user)
    payload: dict[str, Any] = {
        "query": "全部记忆",
        "user_id": user_id,
        "top_k": 500,
        "strategy": "semantic",
    }
    status_code, body = await _forward_raw(
        "POST", "/api/v1/recall",
        json_body=payload, headers=_build_upstream_headers(request, _user),
        request=request,
    )
    if status_code >= 400:
        return JSONResponse(
            status_code=status_code,
            content={"code": body.get("code", status_code),
                     "message": body.get("message", "upstream error"),
                     "data": None, "timestamp": _now_iso()},
        )
    data = body.get("data") or {}
    results = data.get("results") or []
    # 字段归一化：OpenMemory 将 tags/created_at 存入 metadata，提升为顶层
    normalized: list[dict[str, Any]] = []
    for row in results:
        meta = row.get("metadata") or {}
        normalized.append({
            **row,
            "tags": row.get("tags") or meta.get("tags") or [],
            "created_at": row.get("created_at") or meta.get("created_at"),
        })
    results = normalized
    # 本地过滤：类型 / 标签
    if memory_type:
        results = [r for r in results if r.get("memory_type") == memory_type]
    if tag:
        results = [r for r in results if tag in (r.get("tags") or [])]
    total = len(results)
    start = (page - 1) * page_size
    items = results[start:start + page_size]
    return JSONResponse(
        status_code=status_code,
        content={
            "code": body.get("code", 0),
            "message": body.get("message", "success"),
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
            "timestamp": _now_iso(),
        },
    )


async def _proxy_json(
    method: str,
    upstream_path: str,
    request: Request,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    user: dict | None = None,
) -> JSONResponse:
    """认证 + 透传 JSON 类端点的通用入口（v1.4.2 R-379 完善对接）."""
    return await _forward(
        method, upstream_path,
        json_body=json_body, params=params,
        headers=_build_upstream_headers(request, user),
        request=request,
    )


async def _proxy_multipart(
    upstream_path: str,
    request: Request,
    file: UploadFile,
    form_fields: dict[str, str] | None = None,
    *,
    user: dict | None = None,
) -> JSONResponse:
    """认证 + multipart/form-data 透传（多模态/语音上传端点，R-380）.

    读取上传文件内容，构造 httpx files={"file": (filename, content, content_type)}
    透传上游；可选表单字段（metadata/description 等）经 data 透传。
    注意：Content-Type 由 httpx 按 multipart 边界自动生成，勿手动设置。
    """
    content = await file.read()
    headers = _build_upstream_headers(request, user)
    headers.pop("Content-Type", None)  # multipart 边界由 httpx 生成
    files: dict[str, Any] = {
        "file": (file.filename or "upload.bin", content,
                 file.content_type or "application/octet-stream"),
    }
    return await _forward(
        "POST", upstream_path,
        files=files, form_data=form_fields,
        headers=headers,
        request=request,
    )


@router.post("/improve")
async def memory_improve(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """优化记忆（promote/compress/merge，POST /api/v1/improve）."""
    return await _proxy_json("POST", "/api/v1/improve", request, user=_user, json_body=payload)


@router.get("/sessions")
async def memory_sessions(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """会话列表（GET /api/v1/sessions）."""
    return await _proxy_json("GET", "/api/v1/sessions", request, user=_user)


@router.get("/sessions/{session_id}")
async def memory_session_detail(
    session_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """会话详情（GET /api/v1/sessions/{session_id}）."""
    return await _proxy_json("GET", f"/api/v1/sessions/{session_id}", request, user=_user)


@router.post("/sessions/{session_id}/terminate")
async def memory_session_terminate(
    session_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """终止并清空会话（POST /api/v1/sessions/{session_id}/terminate）."""
    return await _proxy_json("POST", f"/api/v1/sessions/{session_id}/terminate", request, user=_user)


@router.get("/decay/config")
async def memory_decay_get(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """获取衰减配置（GET /api/v1/decay/config）."""
    return await _proxy_json("GET", "/api/v1/decay/config", request, user=_user)


@router.put("/decay/config")
async def memory_decay_put(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """更新衰减配置（PUT /api/v1/decay/config）."""
    return await _proxy_json("PUT", "/api/v1/decay/config", request, user=_user, json_body=payload)


@router.get("/recall/traces/{trace_id}")
async def memory_recall_trace(
    trace_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """召回路径追踪（GET /api/v1/recall/traces/{trace_id}）."""
    return await _proxy_json("GET", f"/api/v1/recall/traces/{trace_id}", request, user=_user)


@router.get("/monitor")
async def memory_monitor(
    request: Request,
    range_: str = Query("24h", alias="range"),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """运行监控（GET /api/v1/monitor?range=24h）."""
    return await _proxy_json("GET", "/api/v1/monitor", request, user=_user, params={"range": range_})


@router.get("/health")
async def memory_health(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """OpenMemory 健康状态透传（GET /health，供运维/前端监控）."""
    return await _proxy_json("GET", "/health", request, user=_user)


@router.get("/health/readiness")
async def memory_health_readiness(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """OpenMemory 就绪检查透传（GET /health/readiness，需上游 API Key）."""
    return await _proxy_json("GET", "/health/readiness", request, user=_user)


@router.get("/health/liveness")
async def memory_health_liveness(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """OpenMemory 存活检查透传（GET /health/liveness，需上游 API Key）."""
    return await _proxy_json("GET", "/health/liveness", request, user=_user)


# ---------------------------------------------------------------------------
# 多模态 / 语音端点（指南 5.4/5.5，R-380）
# ---------------------------------------------------------------------------


@router.post("/memories/image")
async def memory_image_upload(
    request: Request,
    file: UploadFile = File(...),
    metadata: str | None = Form(None),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """上传图像记忆（multipart；POST /api/v1/memories/image，≤10MB）."""
    form_fields = {"metadata": metadata} if metadata is not None else None
    return await _proxy_multipart("/api/v1/memories/image", request, file, form_fields, user=_user)


@router.post("/memories/image/search")
async def memory_image_search(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """文本搜索图像记忆（JSON；POST /api/v1/memories/image/search）."""
    return await _proxy_json("POST", "/api/v1/memories/image/search", request, user=_user, json_body=payload)


@router.post("/multimodal/image-embed")
async def memory_image_embed(
    request: Request,
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """图像嵌入（multipart；POST /api/v1/multimodal/image-embed，CLIP）."""
    return await _proxy_multipart("/api/v1/multimodal/image-embed", request, file, user=_user)


@router.post("/audio/transcribe")
async def memory_audio_transcribe(
    request: Request,
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """语音转写（multipart；POST /api/v1/audio/transcribe，mp3/wav/ogg ≤30MB）."""
    return await _proxy_multipart("/api/v1/audio/transcribe", request, file, user=_user)


@router.post("/memories/remember-with-audio")
async def memory_remember_with_audio(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """语音记忆存储（JSON；POST /api/v1/memories/remember-with-audio）."""
    return await _proxy_json(
        "POST", "/api/v1/memories/remember-with-audio", request, user=_user, json_body=payload
    )
