"""rag-proxy 模块：OpenRAG JWT 门禁 + 上游认证注入转发（v1.4.4 R-380 / 任务书 M1）.

统一前端/调用方经 OpenBase 访问 OpenRAG 8010，OpenBase 为唯一认证入口：

- 认证：OpenBase JWT（get_current_user），未认证返回 401。
- 转发：OpenRAG 服务级 API Key（任务书 M1 落地）由 rag-proxy 持有同密钥，
  通过 X-API-Key 请求头注入上游；无 key 配置时不注入（向后兼容）。
- 响应适配：统一 {code, message, data, timestamp}；错误归一化提取顺序
  body.code（非 0）> body.detail.error/code（dict）> body.detail（str）>
  body.error.code > HTTP 状态码（覆盖 OpenRAG 网关 {code,message,data} 与
  FastAPI {detail} 双格式）。
- SSE 透传：/query/stream 逐事件转发（event: start → token×N → done），
  不缓冲、不包装，Content-Type: text/event-stream。
- 文档上传：multipart 原始体透传（不解析，保持边界/编码原样）。
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
from pydantic import BaseModel, Field

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.settings import get_settings

logger = logging.getLogger("openbase.rag_proxy")

router = APIRouter(prefix="/api/v1/rag-proxy", tags=["rag-proxy"])

__version__ = "1.0.0"

__all__ = ["router"]


class CollectionCreate(BaseModel):
    """创建知识库请求体（AC-144-03 契约：name 必填，重复 409）."""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    chunk_strategy: str | None = None
    chunk_size: int | None = Field(default=512, ge=1, le=4096)
    chunk_overlap: int | None = Field(default=50, ge=0, le=1024)


class RagQuery(BaseModel):
    """RAG 查询请求体（query 必填；stream 端点在代理层强制 true）.

    collection_ids：OpenRAG 上游 query 契约要求的多集合目标（可选，
    联调确认上游单集合路径也接受 collection_ids 数组）。
    """

    query: str = Field(min_length=1, max_length=8192)
    top_k: int | None = Field(default=None, ge=1, le=100)
    filters: dict[str, Any] | None = None
    collection_ids: list[str] | None = None
    stream: bool = False


def _now_iso() -> str:
    """生成 ISO 8601 时间戳（UTC）."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _upstream_config() -> tuple[str, float, float, str]:
    """读取上游 OpenRAG 配置（settings，支持 .env 覆盖；任务书 M1 含服务级 API Key）."""
    settings = get_settings()
    return (
        settings.rag_upstream_base,
        settings.rag_upstream_timeout,
        settings.rag_stream_timeout,
        settings.rag_api_key,
    )


def _build_upstream_headers() -> dict[str, str]:
    """构造转发上游的请求头（任务书 M1：注入 OpenRAG 服务级 API Key）.

    OpenRAG v1.8.0 APIKeyMiddleware 配置 service_api_key 后强制鉴权：
    无 X-API-Key 直连返回 401。rag-proxy 持有同密钥（settings.rag_api_key）
    注入上游；未配置 key 时保持无认证转发（向后兼容）。
    """
    _, _, _, rag_api_key = _upstream_config()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if rag_api_key:
        headers["X-API-Key"] = rag_api_key
    return headers


def _adapt_response(upstream: httpx.Response) -> JSONResponse:
    """统一响应适配 {code, message, data, timestamp} + {detail} 归一化.

    2xx：code=0, message="success"，data 为上游业务 data 字段（网关
    {code,message,data,timestamp} 结构）或完整响应体（非网关结构）。

    非 2xx：错误归一化提取顺序（覆盖 OpenRAG 双格式）：
    1. body.code（非 0）→ 网关错误体（如 5000 内部错误）；
    2. body.detail.error/code（dict）→ FastAPI detail 字典包装；
    3. body.detail（str）→ FastAPI 字符串 detail（如 "知识库不存在: xxx"）；
    4. body.error.code → OpenAI 风格错误体；
    5. 兜底：HTTP 状态码。
    上游错误码/消息透传，不映射为 OpenBase 错误码表（契约 §2.2/§4）。
    """
    try:
        payload = upstream.json()
    except ValueError:
        payload = {"raw": upstream.text[:2000]}

    if 200 <= upstream.status_code < 300:
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

    code: Any = None
    message: Any = payload.get("message") if isinstance(payload, dict) else None
    if isinstance(payload, dict):
        candidate = payload.get("code")
        if candidate is not None and candidate != 0:
            code = candidate
        detail = payload.get("detail")
        if code is None and isinstance(detail, dict):
            code = detail.get("code") or detail.get("error")
            message = detail.get("message") or message
        elif code is None and isinstance(detail, str):
            message = detail
        elif isinstance(detail, list):
            # FastAPI 422 validation error：detail 为对象数组，提取各元素 msg
            msgs = [
                str(item.get("msg", ""))
                for item in detail
                if isinstance(item, dict) and item.get("msg")
            ]
            if msgs:
                message = "; ".join(msgs)
        if code is None and isinstance(payload.get("error"), dict):
            error = payload["error"]
            code = error.get("code")
            message = error.get("message") or message
    if code is None:
        code = upstream.status_code
    return JSONResponse(
        status_code=upstream.status_code,
        content={
            "code": code,
            "message": message or "upstream error",
            "data": None,
            "timestamp": _now_iso(),
        },
    )


async def _forward(
    method: str,
    upstream_path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> JSONResponse:
    """转发请求至 OpenRAG 并适配响应（非 SSE，任务书 M1 注入上游 API Key）."""
    base_url, timeout, _, _ = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url,
                json=json_body, params=params,
                headers=_build_upstream_headers(),
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "rag-proxy upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"OpenRAG upstream unreachable: {exc}"
        ) from exc
    return _adapt_response(upstream)


async def _forward_multipart(
    upstream_path: str,
    request: Request,
) -> JSONResponse:
    """multipart 原始体透传（文档上传，不解析表单保持边界/编码原样）.

    FastAPI 端不声明 UploadFile（避免预解析消费流），直接读取原始 body 与
    Content-Type（含 boundary）转发上游，文件字节流完整透传。
    """
    body_bytes = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")
    base_url, timeout, _, _ = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 任务书 M1：multipart 透传同样注入上游 API Key（保留原始 Content-Type/boundary）
            upstream_headers = _build_upstream_headers()
            upstream_headers["Content-Type"] = content_type
            upstream = await client.request(
                "POST", target_url,
                content=body_bytes,
                headers=upstream_headers,
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "rag-proxy multipart upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"OpenRAG upstream unreachable: {exc}"
        ) from exc
    return _adapt_response(upstream)


async def _forward_sse(
    upstream_path: str,
    json_body: dict[str, Any],
) -> StreamingResponse:
    """SSE 逐事件透传（RAG 流式端点）.

    以 httpx AsyncClient stream 读取上游事件流，逐事件写回下游：
    event: start → event: token（重复） → event: done。
    不缓冲、不包装、保序；上游中断时关闭下游流并记录日志。
    """
    base_url, _, stream_timeout, _ = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    json_body = {**json_body, "stream": True}

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=stream_timeout) as client:
                async with client.stream(
                    "POST", target_url, json=json_body,
                    headers=_build_upstream_headers(),
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
                            "rag-proxy sse upstream error",
                            extra={"path": upstream_path, "status": upstream.status_code},
                        )
                        return
                    async for line in upstream.aiter_lines():
                        if line:
                            yield f"{line}\n"
        except httpx.HTTPError as exc:
            logger.warning(
                "rag-proxy sse stream interrupted",
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


# ---------------------------------------------------------------------------
# 知识库族（AC-144-03-1）
# ---------------------------------------------------------------------------


@router.get("/collections")
async def rag_collections_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """知识库列表（GET /api/v1/collections?page=&page_size=）."""
    return await _forward(
        "GET", "/api/v1/collections",
        params={"page": page, "page_size": page_size},
    )


@router.post("/collections")
async def rag_collection_create(
    payload: CollectionCreate,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """创建知识库（POST /api/v1/collections，重复名称上游 409 透传）."""
    return await _forward(
        "POST", "/api/v1/collections",
        json_body=payload.model_dump(exclude_none=True),
    )


@router.get("/collections/{collection_id}")
async def rag_collection_detail(
    collection_id: str,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """知识库详情（GET /api/v1/collections/{id}）."""
    return await _forward("GET", f"/api/v1/collections/{collection_id}")


@router.delete("/collections/{collection_id}")
async def rag_collection_delete(
    collection_id: str,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """删除知识库（DELETE /api/v1/collections/{id}）."""
    return await _forward("DELETE", f"/api/v1/collections/{collection_id}")


# ---------------------------------------------------------------------------
# 文档族（AC-144-03-1，上传 multipart 异步 PENDING）
# ---------------------------------------------------------------------------


@router.post("/collections/{collection_id}/documents")
async def rag_document_upload(
    collection_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """文档上传（POST /collections/{cid}/documents，multipart 原始体透传）.

    上游返回 {status: PENDING, document_id}，前端轮询状态直至完成。
    """
    return await _forward_multipart(
        f"/api/v1/collections/{collection_id}/documents", request
    )


@router.get("/collections/{collection_id}/documents")
async def rag_documents_list(
    collection_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """文档列表（GET /collections/{cid}/documents?page=&page_size=&status_filter=）."""
    return await _forward(
        "GET", f"/api/v1/collections/{collection_id}/documents",
        params={"page": page, "page_size": page_size, "status_filter": status_filter},
    )


@router.get("/collections/{collection_id}/documents/{document_id}")
async def rag_document_detail(
    collection_id: str,
    document_id: str,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """文档详情（GET /collections/{cid}/documents/{did}，上传异步 PENDING→轮询用）.

    需求 §4.3 轮询契约：GET 单文档返回 status: PENDING/PROCESSING/COMPLETED/FAILED。
    设计文档 11 端点清单遗漏本端点，按需求补足（新增端点，向后兼容）。
    """
    return await _forward(
        "GET", f"/api/v1/collections/{collection_id}/documents/{document_id}"
    )


@router.delete("/collections/{collection_id}/documents/{document_id}")
async def rag_document_delete(
    collection_id: str,
    document_id: str,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """删除文档（DELETE /collections/{cid}/documents/{did}）."""
    return await _forward(
        "DELETE", f"/api/v1/collections/{collection_id}/documents/{document_id}"
    )


# ---------------------------------------------------------------------------
# 查询族（AC-144-03-1/4：RAG 查询 / SSE 流式 / 纯检索）
# ---------------------------------------------------------------------------


def _query_body(payload: RagQuery) -> dict[str, Any]:
    """构造查询请求体：排除 None，非流式端点不携带 stream 字段."""
    body = payload.model_dump(exclude_none=True)
    body.pop("stream", None)
    return body


@router.post("/collections/{collection_id}/query")
async def rag_query(
    collection_id: str,
    payload: RagQuery,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """RAG 查询（POST /collections/{cid}/query，检索 + 生成）."""
    return await _forward(
        "POST", f"/api/v1/collections/{collection_id}/query",
        json_body=_query_body(payload),
    )


@router.post("/collections/{collection_id}/query/stream")
async def rag_query_stream(
    collection_id: str,
    payload: RagQuery,
    _user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """RAG 流式（POST /collections/{cid}/query/stream，SSE start/token/done 逐事件透传）."""
    return await _forward_sse(
        f"/api/v1/collections/{collection_id}/query/stream",
        payload.model_dump(exclude_none=True),
    )


@router.post("/collections/{collection_id}/query/retrieve")
async def rag_query_retrieve(
    collection_id: str,
    payload: RagQuery,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """纯检索（POST /collections/{cid}/query/retrieve，返回 items 数组）."""
    return await _forward(
        "POST", f"/api/v1/collections/{collection_id}/query/retrieve",
        json_body=_query_body(payload),
    )


# ---------------------------------------------------------------------------
# 健康（AC-144-01-1 透传）
# ---------------------------------------------------------------------------


@router.get("/health")
async def rag_health(
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """OpenRAG 上游健康透传（GET /api/v1/system/health，供运维/前端监控）."""
    return await _forward("GET", "/api/v1/system/health")
