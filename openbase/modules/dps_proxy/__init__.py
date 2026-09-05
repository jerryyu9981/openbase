"""dps-proxy 模块：DPS JWT 门禁 + 身份头注入转发（v1.4.5 R-381）.

统一前端/调用方经 OpenBase 访问 DPS（上游默认对齐 DPS 源码 api_port=8000，
P0-3 评审 Q5 修正；真实部署由 OPENBASE_DPS_UPSTREAM_BASE 覆盖），
OpenBase 为唯一认证入口：

- 认证：OpenBase JWT（get_current_user），未认证返回 401。
- 身份头注入：DPS HTTP API 采用 Header 身份直传 + RBAC 中间件
  （X-Org-ID/X-Tenant-ID/X-User-ID 必传，组织/租户须预存在库），
  proxy 从 OpenBase JWT/用户上下文构造四头注入上游
  （X-User-ID←sub、X-Tenant-ID←tenant_id、X-Org-ID←org_id、X-User-Role←role），
  缺失时 dps_default_* 兜底，dps_org_map/dps_tenant_map 支持值转换。
- 上游健康探活（P0-3）：首次转发前与每 dps_health_interval 秒探测 DPS /health，
  失败仅 WARN 降级提示并继续转发（转发自身失败仍归一为 502）。
- 响应适配：统一 {code, message, data, timestamp}；错误归一化提取顺序
  body.code（非 0）> body.detail（str/dict/list）> HTTP 状态码
  （覆盖 DPS 网关 {code,message,data} 与 FastAPI {detail} 双格式）。
- 无 SSE 端点（DPS 无 HTTP 流式能力）。
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.settings import get_settings

logger = logging.getLogger("openbase.dps_proxy")

router = APIRouter(prefix="/api/v1/dps-proxy", tags=["dps-proxy"])

__version__ = "1.0.0"

__all__ = ["router"]


def _now_iso() -> str:
    """生成 ISO 8601 时间戳（UTC）."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _upstream_config() -> tuple[str, float]:
    """读取上游 DPS 配置（settings，支持 .env 覆盖；无 dps_api_key）."""
    settings = get_settings()
    return (
        settings.dps_upstream_base,
        settings.dps_upstream_timeout,
    )


def _jwt_payload(request: Request) -> dict[str, Any] | None:
    """解码当前请求的 JWT payload（获取 org_id/role 等 extra 字段）.

    get_current_user 只返回精简字段（id/username/tenant_id/permissions），
    DPS 身份头需要 org_id/role，故此处从 Authorization 头解码 JWT 补取。
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    from openbase.modules.auth.jwt import decode_access_token

    return decode_access_token(authorization.removeprefix("Bearer ").strip())


def _apply_map(map_json: str, value: str) -> str:
    """映射表值转换（dps_org_map/dps_tenant_map：OpenBase 值 → DPS 值）.

    未配置映射表、映射表非法或未命中时返回原值。
    """
    if not map_json or not value:
        return value
    try:
        mapping = json.loads(map_json)
    except ValueError:
        return value
    if isinstance(mapping, dict):
        return str(mapping.get(value, value))
    return value


def _build_identity_headers(user: dict, jwt_payload: dict[str, Any] | None) -> dict[str, str]:
    """构造注入 DPS 的四头（X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role）.

    映射规则（需求 §3 / API 设计 §2）：
    - X-User-ID：get_current_user().id（JWT sub）
    - X-Tenant-ID：user.tenant_id → jwt org_id → dps_default_tenant_id → 映射表
    - X-Org-ID：jwt org_id → user.org_id → dps_default_org_id → 映射表
    - X-User-Role：jwt role（缺省 "user"）
    """
    settings = get_settings()
    jwt_payload = jwt_payload or {}
    # P3.1：tenant_code claim（新签发令牌）优先 → 兼容旧令牌数值链回退。
    # X-Tenant-ID 与 X-Org-ID 在 code 存在时同形（治理 Q2：org 头退役为兼容别名）。
    tenant_raw = (
        jwt_payload.get("tenant_code")
        or user.get("tenant_id")
        or jwt_payload.get("org_id")
        or settings.dps_default_tenant_id
    )
    org_raw = (
        jwt_payload.get("tenant_code")
        or jwt_payload.get("org_id")
        or user.get("org_id")
        or settings.dps_default_org_id
    )
    return {
        "X-User-ID": str(user.get("id", "")),
        "X-Tenant-ID": _apply_map(settings.dps_tenant_map, str(tenant_raw or "")),
        "X-Org-ID": _apply_map(settings.dps_org_map, str(org_raw or "")),
        "X-User-Role": jwt_payload.get("role") or "user",
    }


def _adapt_response(upstream: httpx.Response) -> JSONResponse:
    """统一响应适配 {code, message, data, timestamp} + {detail} 归一化.

    2xx：code=0, message="success"，data 为上游业务 data 字段（DPS 网关
    {code:200,message,data} 结构）或完整响应体（非网关结构，如 /health）。

    非 2xx：错误归一化提取顺序：
    1. body.code（非 0）→ DPS 网关错误体（如 5000 内部错误）；
    2. body.detail（str/dict/list）→ FastAPI detail；
    3. 兜底：HTTP 状态码。
    上游错误码/消息透传，不映射为 OpenBase 错误码表（契约 §5）。
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
        if candidate is not None and candidate != 0 and candidate != 200:
            code = candidate
        detail = payload.get("detail")
        if code is None and isinstance(detail, dict):
            code = detail.get("code") or detail.get("error")
            message = detail.get("message") or message
        elif code is None and isinstance(detail, str):
            message = detail
        elif isinstance(detail, list):
            msgs = [
                str(item.get("msg", ""))
                for item in detail
                if isinstance(item, dict) and item.get("msg")
            ]
            if msgs:
                message = "; ".join(msgs)
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


# ---------------------------------------------------------------------------
# DPS 上游健康探活（P0-3：端口对齐守护；settings.dps_upstream_base 默认 8000）
#
# OpenBase 采用同步 init_app 装配（无模块 lifespan），故沿用惰性接入点：
# 首次 dps-proxy 请求前探测一次，此后每 dps_health_interval 秒至多一次。
# 失败仅 WARN 降级提示（fail-open，不改写既有"转发不可达→502"语义）；
# 通过"探测前置时间戳占位"天然去重并发首请求，无需额外锁。
# ---------------------------------------------------------------------------

# 探活目标路径：DPS main.py（8000）与 rest_api.app/MCP（8013）两个入口均提供 /health
# （/health/liveness 仅 rest_api.app 存在，不作为通用探活路径）。
DPS_HEALTH_PATH = "/health"
# 探活短超时：仅判定连通性，不占用 dps_upstream_timeout 业务预算
DPS_HEALTH_PROBE_TIMEOUT = 3.0

# 进程级惰性探活状态（时间戳单位：time.monotonic 秒；None=尚未探测）
_last_dps_health_probe_at: float | None = None
_dps_health_ok: bool | None = None


async def _probe_dps_health_once() -> bool:
    """执行一次 DPS /health 探测（2xx 视为健康）.

    Returns:
        探活是否成功；失败（连接异常/非 2xx）仅记录日志，不抛出。
    """
    base_url, _timeout = _upstream_config()
    health_url = f"{base_url.rstrip('/')}{DPS_HEALTH_PATH}"
    try:
        async with httpx.AsyncClient(timeout=DPS_HEALTH_PROBE_TIMEOUT) as client:
            response = await client.request("GET", health_url)
        ok = 200 <= response.status_code < 300
    except httpx.HTTPError as exc:
        logger.warning(
            "DPS upstream health probe failed (degraded, proxying still attempted)",
            extra={"url": health_url, "error": str(exc)},
        )
        return False
    if not ok:
        logger.warning(
            "DPS upstream health probe non-2xx (degraded, proxying still attempted)",
            extra={"url": health_url, "status": response.status_code},
        )
    return ok


async def _maybe_probe_dps_health() -> None:
    """按开关与 interval 节流触发一次 DPS /health 探活（惰性、不阻断）."""
    global _last_dps_health_probe_at, _dps_health_ok
    settings = get_settings()
    if not settings.dps_health_check_enabled:
        return
    now = time.monotonic()
    if (
        _last_dps_health_probe_at is not None
        and now - _last_dps_health_probe_at < settings.dps_health_interval
    ):
        return
    # 先占位再探测：并发首请求共享同一次探活，无需进程锁
    _last_dps_health_probe_at = now
    previous_ok = _dps_health_ok
    ok = await _probe_dps_health_once()
    _dps_health_ok = ok
    if ok and previous_ok is False:
        logger.info("DPS upstream health probe recovered")


async def _forward(
    method: str,
    upstream_path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """转发请求至 DPS 并适配响应（非 SSE，身份头注入）."""
    await _maybe_probe_dps_health()
    base_url, timeout = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url,
                json=json_body, params=params,
                headers=headers or {},
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "dps-proxy upstream unreachable",
            extra={"path": upstream_path, "error": str(exc)},
        )
        global _dps_consecutive_failures
        _dps_consecutive_failures += 1
        threshold = get_settings().dps_degrade_threshold
        if _dps_consecutive_failures >= max(1, threshold):
            # P6：连续失败达阈值 → 503 显式降级（fail-open 语义保持：
            # 后续探活恢复自动归零并恢复正常转发）
            logger.error(
                "DPS upstream degraded (consecutive=%d threshold=%d)",
                _dps_consecutive_failures,
                threshold,
                extra={"path": upstream_path, "error": str(exc)},
            )
            return JSONResponse(
                status_code=503,
                content={
                    "code": 503,
                    "message": "DPS 上游持续不可用（降级）",
                    "data": {
                        "degraded": True,
                        "consecutive_failures": _dps_consecutive_failures,
                        "last_error": str(exc)[:200],
                    },
                    "timestamp": _now_iso(),
                },
                headers={"X-DPS-Upstream-Degraded": "true"},
            )
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"DPS upstream unreachable: {exc}"
        ) from exc
    _dps_consecutive_failures = 0
    return _adapt_response(upstream)


# ---------------------------------------------------------------------------
# 画像族（AC-145-03-1/2）
# ---------------------------------------------------------------------------


@router.get("/portraits")
async def dps_portraits_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像列表（GET /api/v2/portrait/list?page=&page_size=）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "GET", "/api/v2/portrait/list",
        params={"page": page, "page_size": page_size},
        headers=headers,
    )


@router.get("/portraits/{person_id}")
async def dps_portrait_detail(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像详情（GET /api/v2/portrait/{person_id}）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "GET", f"/api/v2/portrait/{person_id}",
        headers=headers,
    )


@router.post("/portraits/calculate")
async def dps_portrait_calculate(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像计算（POST /api/v2/portrait/calculate，请求体透传上游契约）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "POST", "/api/v2/portrait/calculate",
        json_body=payload,
        headers=headers,
    )


@router.put("/portraits/{person_id}")
async def dps_portrait_update(
    person_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像更新（PUT /api/v2/portrait/{person_id}，Phase C1 契约 body 透传）.

    承接真实契约落地立项方案 Phase C2（决策 D3 建议 A）：ProfileAdapter 写/漂移的
    持久化落点 PUT /api/v2/portrait/{person_id}（body {person: {name?, status?,
    scores?}, business: {attributes}}）；复用 _forward + 四头注入，请求体原样透传。
    """
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "PUT", f"/api/v2/portrait/{person_id}",
        json_body=payload,
        headers=headers,
    )


# ---------------------------------------------------------------------------
# 标签/报表族（AC-145-03-1）
# ---------------------------------------------------------------------------


@router.get("/tags/categories")
async def dps_tags_categories(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标签分类（GET /api/v2/tags/categories）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward("GET", "/api/v2/tags/categories", headers=headers)


@router.post("/tags/categories")
async def dps_tag_category_create(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """创建标签分类（POST /api/v2/tags/categories，透传上游契约）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "POST", "/api/v2/tags/categories",
        json_body=payload,
        headers=headers,
    )


@router.put("/tags/categories/{category_id}")
async def dps_tag_category_update(
    category_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """更新标签分类（PUT /api/v2/tags/categories/{id}）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "PUT", f"/api/v2/tags/categories/{category_id}",
        json_body=payload,
        headers=headers,
    )


@router.delete("/tags/categories/{category_id}")
async def dps_tag_category_delete(
    category_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """删除标签分类（DELETE /api/v2/tags/categories/{id}）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "DELETE", f"/api/v2/tags/categories/{category_id}",
        headers=headers,
    )


@router.get("/reports/overview")
async def dps_reports_overview(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """报表概览（GET /api/v2/reports/overview）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward("GET", "/api/v2/reports/overview", headers=headers)


# ---------------------------------------------------------------------------
# 批量/审计族（AC-145-03-1）
# ---------------------------------------------------------------------------


@router.get("/batch/tasks/{task_id}")
async def dps_batch_task_status(
    task_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """批量任务状态（GET /api/v2/batch/import/{task_id}/status）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward(
        "GET", f"/api/v2/batch/import/{task_id}/status",
        headers=headers,
    )


@router.get("/audit/logs")
async def dps_audit_logs(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """审计日志（GET /api/v2/audit/logs）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward("GET", "/api/v2/audit/logs", headers=headers)


# ---------------------------------------------------------------------------
# 健康（AC-145-01-1 透传）
# ---------------------------------------------------------------------------


@router.get("/health")
async def dps_health(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 上游健康透传（GET /health/liveness，DPS 白名单免鉴权）."""
    headers = _build_identity_headers(_user, _jwt_payload(request))
    return await _forward("GET", "/health/liveness", headers=headers)
