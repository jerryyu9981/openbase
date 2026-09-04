"""llm-proxy 模块：OpenLLM API Key Bearer 注入转发（v1.4.3 R-379）.

统一前端/调用方经 OpenBase 访问 OpenLLM 8001，无需持有 OpenLLM 密钥：

- 认证：OpenBase JWT（get_current_user），未认证返回 401。
- 转发注入：Authorization: Bearer <llm_api_key>（OpenBase 持有，OpenLLM 服务
  API Key 通道；OpenLLM 不支持 X-API-Key 头，必须 Bearer 传递）。
- 外部身份归属注入（P0-2 / Q4 最小档 / M3）：登录态下注入
  X-User-ID(sub)/X-Org-ID(org_id)/X-Proxy-Source(openbase-llm-proxy)，
  供 OpenLLM 侧 TRUSTED_PROXY_SOURCES 白名单解析到审计与请求上下文；
  匿名/服务级内部调用（无法解析到身份）不携带身份头，避免误标。
- 响应适配：统一 {code, message, data, timestamp}；上游错误码透传
  （1001 未认证 / 1003 限流 / 1004 无可用模型 / 2001 资源不存在 / 5001 内部错误）。
- SSE 透传：/chat/stream 逐事件转发（event: routing → chunk×N → done），
  不缓冲、不包装，Content-Type: text/event-stream。
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.settings import get_settings

logger = logging.getLogger("openbase.llm_proxy")

router = APIRouter(prefix="/api/v1/llm-proxy", tags=["llm-proxy"])

__version__ = "1.0.0"

# P0-2（Q4 最小档 / M3 归属打通）：本 proxy 来源标识，供 OpenLLM 侧
# TRUSTED_PROXY_SOURCES 白名单（config）校验身份头是否可信（防伪造）。
PROXY_SOURCE_IDENTIFIER = "openbase-llm-proxy"

__all__ = ["router"]


def _now_iso() -> str:
    """生成 ISO 8601 时间戳（UTC）."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _upstream_config() -> tuple[str, str, float, float]:
    """读取上游 OpenLLM 配置（settings，支持 .env 覆盖）."""
    settings = get_settings()
    return (
        settings.llm_api_key,
        settings.llm_upstream_base,
        settings.llm_upstream_timeout,
        settings.llm_stream_timeout,
    )


def _extract_identity(request: Request) -> dict[str, str]:
    """从当前请求 JWT 提取身份值（sub/org_id），供上游归属头注入.

    get_current_user 只返回精简字段（id/username/tenant_id/permissions），
    外部身份归属需要 org_id（与现 JWT claim 同源），故从 Authorization
    头解码 JWT 补取（与 memory_proxy/dps_proxy 同模式）。解码失败或缺失
    返回空 dict：匿名/服务级内部调用不发身份头（Q4/M3：避免误标）。
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return {}
    from openbase.modules.auth.jwt import decode_access_token

    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    if payload is None:
        return {}
    identity: dict[str, str] = {}
    subject = payload.get("sub")
    if subject is not None and subject != "":
        identity["sub"] = str(subject)
    org_id = payload.get("org_id")
    if org_id is not None and org_id != "":
        identity["org_id"] = str(org_id)
    return identity


def _build_upstream_headers(request: Request) -> dict[str, str]:
    """构造转发上游的请求头（OpenLLM API Key Bearer + 外部身份归属注入）.

    OpenLLM 认证契约：API Key 仅经 Authorization: Bearer 传递，不支持
    X-API-Key 头（代码核验 auth_service.get_api_key_user 只读 Authorization）。

    P0-2（Q4 最小档 / M3 归属打通）：身份头仅在能解析到当前登录身份时注入——
    X-User-ID=JWT sub、X-Org-ID=JWT org_id（与现 JWT claim 同源）、
    X-Proxy-Source=PROXY_SOURCE_IDENTIFIER（OpenLLM TRUSTED_PROXY_SOURCES
    白名单据此防伪造）。匿名/服务级内部调用不携带身份头，避免误标。
    """
    api_key, _, _, _ = _upstream_config()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    identity = _extract_identity(request)
    if not identity:
        return headers
    headers["X-User-ID"] = identity["sub"]
    headers["X-Proxy-Source"] = PROXY_SOURCE_IDENTIFIER
    if identity.get("org_id"):
        headers["X-Org-ID"] = identity["org_id"]
    return headers


def _adapt_response(upstream: httpx.Response) -> JSONResponse:
    """统一响应适配 {code, message, data, timestamp}.

    2xx：code=0, message="success"，data 为上游完整响应体（OpenLLM 网关
    统一 {code,message,data,request_id} 结构，data 字段再透传）。

    非 2xx：透传上游业务码。OpenLLM 网关错误体形如
    {"code": 1001, "message": "...", "request_id": "..."}、
    {"detail": {"error": "...", "code": ...}}（FastAPI 包装）或
    OpenAI 风格 {"error": {message, type, code}}。
    提取顺序：body.code > body.error > detail.error/code > HTTP 状态码。
    retry_after 透传（1003 限流）。
    """
    try:
        payload = upstream.json()
    except ValueError:
        payload = {"raw": upstream.text[:2000]}

    if 200 <= upstream.status_code < 300:
        # data 取上游业务 data（OpenLLM 网关 {code,message,data} 结构），
        # 上游非网关结构时透传完整响应体。
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        return JSONResponse(
            status_code=upstream.status_code,
            content={
                "code": 0,
                "message": "success",
                "data": data,
                "timestamp": _now_iso(),
            },
        )

    # 错误码透传（OpenLLM 网关数值码 1001/1003/1004/2001/5001/4001~4005）
    code = payload.get("code") or payload.get("error")
    message = payload.get("message")
    if code is None:
        detail = payload.get("detail")
        if isinstance(detail, dict):
            code = detail.get("code") or detail.get("error") or detail.get("status")
            message = detail.get("message") or message
        elif isinstance(detail, str):
            message = detail
    if code is None and isinstance(payload.get("error"), dict):
        code = payload["error"].get("code")
        message = payload["error"].get("message") or message
    if code is None:
        code = upstream.status_code
    data: Any = None
    retry_after = payload.get("retry_after")
    if retry_after is None and isinstance(payload.get("data"), dict):
        retry_after = payload["data"].get("retry_after")
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
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> JSONResponse:
    """转发请求至 OpenLLM 并适配响应（非 SSE）.

    headers 必须由调用方经 _build_upstream_headers(request) 构造
    （含身份归属头），禁止省略。
    """
    _, base_url, timeout, _ = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url,
                json=json_body, params=params,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "llm-proxy upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"OpenLLM upstream unreachable: {exc}"
        ) from exc
    return _adapt_response(upstream)


async def _forward_sse(
    upstream_path: str,
    json_body: dict[str, Any],
    headers: dict[str, str],
) -> StreamingResponse:
    """SSE 逐事件透传（对话流式端点）.

    以 httpx AsyncClient stream 读取上游事件流，逐事件写回下游：
    event: routing → event: chunk（重复） → event: done。
    不缓冲、不包装、保序；上游中断时关闭下游流并记录日志。
    """
    _, base_url, _, stream_timeout = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=stream_timeout) as client:
                async with client.stream(
                    "POST", target_url, json=json_body, headers=headers
                ) as upstream:
                    if upstream.status_code >= 400:
                        body_bytes = await upstream.aread()
                        body: dict[str, Any] = {}
                        try:
                            body = json.loads(body_bytes.decode("utf-8"))
                        except ValueError:
                            body = {"message": body_bytes.decode("utf-8", "replace")[:500]}
                        yield f"event: error\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"
                        logger.warning(
                            "llm-proxy sse upstream error",
                            extra={"path": upstream_path, "status": upstream.status_code},
                        )
                        return
                    async for line in upstream.aiter_lines():
                        if line:
                            yield f"{line}\n"
        except httpx.HTTPError as exc:
            logger.warning(
                "llm-proxy sse stream interrupted",
                extra={"path": upstream_path, "error": str(exc)},
            )
            yield 'event: error\ndata: {"message": "stream interrupted"}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _gateway_models() -> str:
    """OpenLLM 网关模型列表上游路径（统一响应 {code,message,data:{models}}）."""
    return "/openllm/v1/models"


# ---------------------------------------------------------------------------
# 业务端点
# ---------------------------------------------------------------------------


@router.get("/models")
async def llm_models(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模型列表（GET /openllm/v1/models，API Key 通道）."""
    return await _forward("GET", _gateway_models(), headers=_build_upstream_headers(request))


@router.get("/models/{model_id}")
async def llm_model_detail(
    model_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模型详情.

    上游 GET /api/v1/providers/models/{model_id} 需管理员 JWT（API Key 通道
    不可用，M2 待完善）。本版本降级：从网关模型列表过滤 model_id 返回，
    保持详情可走查；命中失败返回上游语义 2001 资源不存在。
    """
    response = await _forward(
        "GET", _gateway_models(), headers=_build_upstream_headers(request)
    )
    if response.status_code >= 400:
        return response
    try:
        body = json.loads(response.body.decode("utf-8"))
    except ValueError:
        return response
    models = ((body.get("data") or {}).get("models")) or []
    for model in models:
        if model.get("id") == model_id:
            body["data"] = model
            return JSONResponse(status_code=200, content=body)
    return JSONResponse(
        status_code=404,
        content={
            "code": 2001,
            "message": "model not found",
            "data": None,
            "timestamp": _now_iso(),
        },
    )


@router.post("/chat")
async def llm_chat(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """对话（POST /openllm/v1/chat，非流式聚合端点）."""
    return await _forward(
        "POST", "/openllm/v1/chat", json_body=payload,
        headers=_build_upstream_headers(request),
    )


@router.post("/chat/stream")
async def llm_chat_stream(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """对话流式（POST /openllm/v1/chat/stream，SSE 逐事件透传）."""
    return await _forward_sse(
        "/openllm/v1/chat/stream", payload, _build_upstream_headers(request)
    )


@router.get("/health")
async def llm_health(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """OpenLLM 网关健康透传（GET /openllm/v1/health，供运维/前端监控）."""
    return await _forward("GET", "/openllm/v1/health", headers=_build_upstream_headers(request))


# ---------------------------------------------------------------------------
# 会话端点（对话管理页）
# ---------------------------------------------------------------------------
# 上游 /api/v1/conversations* 为 JWT 通道（M1 待完善：OpenLLM 侧需支持 API Key）。
# 本版本转发端点先行实现，联调时若上游 401 则按设计降级方案处理（模型列表 +
# 对话发起，会话历史缺口登记《OpenLLM 对接完善任务书》M1）。


@router.get("/conversations")
async def llm_conversations(
    request: Request,
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """会话列表（GET /api/v1/conversations?status=&skip=&limit=）."""
    return await _forward(
        "GET", "/api/v1/conversations",
        params={"status": status, "skip": skip, "limit": limit},
        headers=_build_upstream_headers(request),
    )


@router.post("/conversations")
async def llm_conversation_create(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """新建会话（POST /api/v1/conversations）."""
    return await _forward(
        "POST", "/api/v1/conversations", json_body=payload,
        headers=_build_upstream_headers(request),
    )


@router.get("/conversations/{conversation_id}")
async def llm_conversation_detail(
    conversation_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """会话详情（GET /api/v1/conversations/{id}）."""
    return await _forward(
        "GET", f"/api/v1/conversations/{conversation_id}",
        headers=_build_upstream_headers(request),
    )


@router.delete("/conversations/{conversation_id}")
async def llm_conversation_delete(
    conversation_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """软删除会话（DELETE /api/v1/conversations/{id}）."""
    return await _forward(
        "DELETE", f"/api/v1/conversations/{conversation_id}",
        headers=_build_upstream_headers(request),
    )


@router.post("/conversations/{conversation_id}/archive")
async def llm_conversation_archive(
    conversation_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """归档/取消归档会话（POST /api/v1/conversations/{id}/archive）."""
    raw = await request.body()
    json_body: dict[str, Any] | None = None
    if raw:
        try:
            json_body = json.loads(raw.decode("utf-8"))
        except ValueError:
            json_body = None
    return await _forward(
        "POST", f"/api/v1/conversations/{conversation_id}/archive",
        json_body=json_body,
        headers=_build_upstream_headers(request),
    )


@router.post("/conversations/{conversation_id}/messages")
async def llm_conversation_message_create(
    conversation_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """追加会话消息（POST /api/v1/conversations/{id}/messages）."""
    return await _forward(
        "POST", f"/api/v1/conversations/{conversation_id}/messages",
        json_body=payload, headers=_build_upstream_headers(request),
    )


@router.get("/conversations/{conversation_id}/messages")
async def llm_conversation_messages(
    conversation_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """会话消息列表（GET /api/v1/conversations/{id}/messages）."""
    return await _forward(
        "GET", f"/api/v1/conversations/{conversation_id}/messages",
        headers=_build_upstream_headers(request),
    )
