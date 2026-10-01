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
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.protocol_headers import TARGET_SYSTEM_LLM, build_outbound_headers
from openbase.modules.proxy.upstream_observe import (
    UPSTREAM_SYSTEM_OPENLLM,
    content_type_of,
    elapsed_ms,
    publish_upstream_response,
)
from openbase.settings import get_settings

logger = logging.getLogger("openbase.llm_proxy")

router = APIRouter(prefix="/api/v1/llm-proxy", tags=["llm-proxy"])

__version__ = "1.0.0"

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


def _build_upstream_headers(request: Request, user: dict | None) -> dict[str, str]:
    """构造转发上游的请求头（OpenLLM API Key Bearer + 外部身份归属注入）.

    OpenLLM 认证契约：API Key 仅经 Authorization: Bearer 传递，不支持
    X-API-Key 头（代码核验 auth_service.get_api_key_user 只读 Authorization）。

    P2-1 T1（K01）：删除 ``_extract_identity`` 二次 JWT 解码，统一经
    ``protocol_headers.inject.build_outbound_headers`` 装配（§3.5 llm-proxy 行）：
    X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role 取统一主体上下文；X-Proxy-Source 改读
    ``PROXY_SOURCE_LLM``（值不变 = ``openbase-llm-proxy``，下游白名单零迁移）；
    委托场景出站四头取委托域值 + X-Agent-Id。匿名/服务级内部调用（user=None）不携带
    身份头，避免误标。
    """
    api_key, _, _, _ = _upstream_config()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    settings = get_settings()
    return build_outbound_headers(
        request,
        user,
        target_system=TARGET_SYSTEM_LLM,
        extra_headers=headers,
        enforce_org_alias=settings.enforce_org_alias,
    )


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
    request: Request | None = None,
) -> JSONResponse:
    """转发请求至 OpenLLM 并适配响应（非 SSE；C-16 上游专段同请求汇聚）.

    headers 必须由调用方经 _build_upstream_headers(request, _user) 构造
    （含身份归属头），禁止省略。

    ``request`` 缺省 None 时仅跳过上游观测（专段挂 ``request.state``），**转发语义不变**。
    """
    _, base_url, timeout, _ = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    upstream_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url,
                json=json_body, params=params,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        publish_upstream_response(
            request,
            system=UPSTREAM_SYSTEM_OPENLLM,
            reached=False,
            duration_ms=elapsed_ms(upstream_start),
            error=str(exc),
        )
        logger.warning(
            "llm-proxy upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"OpenLLM upstream unreachable: {exc}"
        ) from exc
    publish_upstream_response(
        request,
        system=UPSTREAM_SYSTEM_OPENLLM,
        reached=True,
        duration_ms=elapsed_ms(upstream_start),
        status_code=upstream.status_code,
        content_type=content_type_of(upstream),
        payload=getattr(upstream, "content", None),
    )
    return _adapt_response(upstream)


async def _forward_sse(
    upstream_path: str,
    json_body: dict[str, Any],
    headers: dict[str, str],
    request: Request | None = None,
) -> StreamingResponse:
    """SSE 逐事件透传（对话流式端点；C-16 头部级专段）.

    以 httpx AsyncClient stream 读取上游事件流，逐事件写回下游：
    event: routing → event: chunk（重复） → event: done。
    不缓冲、不包装、保序；上游中断时关闭下游流并记录日志。

    C-16 观测口径：**仅记头部级字段**（状态/首字节耗时/Content-Type）——流式体
    预读会消费事件流、破坏透传语义，故 2xx 路径传 ``payload=None``（无 digest）。
    """
    _, base_url, _, stream_timeout = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"

    async def event_stream() -> AsyncGenerator[str, None]:
        upstream_start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=stream_timeout) as client:
                async with client.stream(
                    "POST", target_url, json=json_body, headers=headers
                ) as upstream:
                    if upstream.status_code >= 400:
                        body_bytes = await upstream.aread()
                        publish_upstream_response(
                            request,
                            system=UPSTREAM_SYSTEM_OPENLLM,
                            reached=True,
                            duration_ms=elapsed_ms(upstream_start),
                            status_code=upstream.status_code,
                            content_type=content_type_of(upstream),
                            payload=body_bytes,
                        )
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
                    publish_upstream_response(
                        request,
                        system=UPSTREAM_SYSTEM_OPENLLM,
                        reached=True,
                        duration_ms=elapsed_ms(upstream_start),
                        status_code=upstream.status_code,
                        content_type=content_type_of(upstream),
                    )
                    async for line in upstream.aiter_lines():
                        if line:
                            yield f"{line}\n"
        except httpx.HTTPError as exc:
            publish_upstream_response(
                request,
                system=UPSTREAM_SYSTEM_OPENLLM,
                reached=False,
                duration_ms=elapsed_ms(upstream_start),
                error=str(exc),
            )
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
    return await _forward(
        "GET", _gateway_models(),
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


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
        "GET", _gateway_models(), headers=_build_upstream_headers(request, _user),
        request=request,
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
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.post("/chat/stream")
async def llm_chat_stream(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """对话流式（POST /openllm/v1/chat/stream，SSE 逐事件透传）."""
    return await _forward_sse(
        "/openllm/v1/chat/stream", payload,
        _build_upstream_headers(request, _user),
        request=request,
    )


@router.get("/health")
async def llm_health(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """OpenLLM 网关健康透传（GET /openllm/v1/health，供运维/前端监控）."""
    return await _forward(
        "GET", "/openllm/v1/health",
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


# ---------------------------------------------------------------------------
# 装配模板与保真度对比（统一前端「提示词模板」/「对比」两块功能；v1.34.0）
# ---------------------------------------------------------------------------
# 链路：**统一前端** → **本代理**（注入 OpenLLM API Key ＋ 身份头）→ OpenLLM 网关
#      `/openllm/v1/prompt/assembly/*` ⇒ 前端**不接触** OpenLLM 管理面（无本仓 JWT）。
#
# **写模板（PUT）暂不经本代理开放**（如实登记）：需先确定 OpenBase 侧的**管理员权限位**
#   （本仓角色模型与 OpenLLM 管理面不同源，贸然放行等于把「全局装配行为」交给任意登录用户）。
#   OpenLLM 网关侧**已备**该入口（`CONTEXT_ASSEMBLY_TEMPLATE_REMOTE_EDIT_ENABLED` 默认关闭
#   ＋ `X-Proxy-Source` 受信来源双门禁）；待权限位确认后，在本模块加一条带校验的路由即可。


@router.get("/prompt-assembly/template")
async def llm_assembly_template(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """装配模板现状透传（GET /openllm/v1/prompt/assembly/template）."""
    return await _forward(
        "GET", "/openllm/v1/prompt/assembly/template",
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.post("/prompt-assembly/preview")
async def llm_assembly_preview(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """试装配预览透传（POST /openllm/v1/prompt/assembly/preview；**不调 LLM**）."""
    return await _forward(
        "POST", "/openllm/v1/prompt/assembly/preview",
        json_body=payload,
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.get("/prompt-assembly/compare")
async def llm_assembly_compare(
    request: Request,
    _user: dict = Depends(get_current_user),
    request_id: str | None = Query(None),
    session_id: str | None = Query(None),
    request_text: str | None = Query(None),
    final_prompt: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> JSONResponse:
    """保真度对照透传（GET /openllm/v1/prompt/assembly/compare；在线按 request_id/session_id、离线直传两端文本）."""
    params = {
        key: value
        for key, value in {
            "request_id": request_id,
            "session_id": session_id,
            "request_text": request_text,
            "final_prompt": final_prompt,
            "limit": limit,
        }.items()
        if value is not None
    }
    return await _forward(
        "GET", "/openllm/v1/prompt/assembly/compare",
        params=params,
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


@router.get("/prompt-assembly/compare/records")
async def llm_assembly_compare_records(
    request: Request,
    _user: dict = Depends(get_current_user),
    session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> JSONResponse:
    """对照记录列表透传（GET /openllm/v1/prompt/assembly/compare/records）."""
    params = {
        key: value
        for key, value in {"session_id": session_id, "limit": limit}.items()
        if value is not None
    }
    return await _forward(
        "GET", "/openllm/v1/prompt/assembly/compare/records",
        params=params,
        headers=_build_upstream_headers(request, _user),
        request=request,
    )


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
        headers=_build_upstream_headers(request, _user),
        request=request,
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
        headers=_build_upstream_headers(request, _user),
        request=request,
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
        headers=_build_upstream_headers(request, _user),
        request=request,
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
        headers=_build_upstream_headers(request, _user),
        request=request,
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
        headers=_build_upstream_headers(request, _user),
        request=request,
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
        json_body=payload, headers=_build_upstream_headers(request, _user),
        request=request,
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
        headers=_build_upstream_headers(request, _user),
        request=request,
    )
