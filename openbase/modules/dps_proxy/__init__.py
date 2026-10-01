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

v1.4.10 Step 3 P1（模板化能力对接深化，契约《OpenBase-API接口设计文档-v1.4.10》
§1／§1.1／§3.1／§3.2／§3.4）：在**保持既有 12 条路由行为与对外路径不变**的前提下，
新增 **22 条路由**（10 新增端点 #1~#10 ＋ 12 条补代理端点 #11~#22）：

- 本仓路由 ``/api/v1/dps-proxy/{path}`` → 上游 ``{dps_upstream_base}/api/v2/portrait/{path}``；
- **路由注册顺序（DT-04 强制）**：静态段／列表路由先于同名动态段；
- 分页／幂等（``package_hash``）／时间格式／**错误体（4xx／5xx）语义保真透传**，
  不在本仓做权限判定（BR-1410-02：仅注入身份 ＋ 透传上游 403）；
- 身份头沿用 :func:`_build_identity_headers`（四头 ＋ ``X-Proxy-Source``／``X-Request-Id``）。
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
from openbase.modules.protocol_headers import (
    TARGET_SYSTEM_DPS,
    build_outbound_headers,
    load_role_map,
)
from openbase.modules.protocol_headers.dps_code_map import build_compat_value_maps
from openbase.modules.proxy.upstream_observe import (
    UPSTREAM_SYSTEM_DPS,
    content_type_of,
    elapsed_ms,
    publish_upstream_response,
)
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


def _parse_map_json(map_json: str) -> dict[str, str]:
    """解析 dps 值映射 JSON（dps_org_map/dps_tenant_map；非法/空 → 空表）."""
    if not map_json:
        return {}
    try:
        mapping = json.loads(map_json)
    except ValueError:
        return {}
    return mapping if isinstance(mapping, dict) else {}


def _build_identity_headers(user: dict, request: Request) -> dict[str, str]:
    """构造注入 DPS 的身份头（经共享 builder 唯一装配点，P2-1 §3.5）.

    P2-1 T1（K01）：删除二次 JWT 解码（原 ``_jwt_payload``），出站头取值**只来自
    ``get_current_user`` 返回的统一主体上下文**（已含 tenant_code/subject_type/role/
    on_behalf_of/delegated），委托场景由 ``resolve_identity`` 完成委托覆盖。

    - X-User-ID ← 有效主体 sub（委托时为 delegated.subject_id）
    - X-Tenant-ID ← tenant_code 优先链 → dps_default_tenant_id 显式兜底 → 值映射
    - X-Org-ID ← 兼容别名（值域=tenant 语义；显式别名 org 头随批次 2/T7 收敛）
    - X-User-Role ← 有效角色（缺省 dps 历史语义 "user"）；目标系统配置了互译表
      （settings.role_intertranslate，OB-12/T6）时经表翻译为 DPS 角色码
    - X-Proxy-Source ← PROXY_SOURCE_DPS（新增）；X-Request-Id ← request_id 透传
    """
    settings = get_settings()
    entries = settings.dps_code_map_entries()
    org_value_map, tenant_value_map = build_compat_value_maps(
        _parse_map_json(settings.dps_org_map),
        _parse_map_json(settings.dps_tenant_map),
        entries,
    )
    return build_outbound_headers(
        request,
        user,
        target_system=TARGET_SYSTEM_DPS,
        default_tenant=settings.dps_default_tenant_id,
        default_org=settings.dps_default_org_id,
        default_role="user",
        tenant_value_map=tenant_value_map,
        org_value_map=org_value_map,
        role_map=load_role_map(settings.role_intertranslate),
        enforce_org_alias=settings.enforce_org_alias,
    )


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

# P6 连续失败计数（用于达阈值后 503 显式降级）。
# 缺陷修复（AD-20260914-01）：原实现仅在 `_forward` 的异常分支内以 `global` 自增，
# 全仓无模块级初值 → **上游首次不可达即 NameError**（降级/502 路径在真实故障下不可用，
# 且此前无用例覆盖该分支）。此处补齐模块级初值，语义与 settings.dps_degrade_threshold
# 一致（`_forward` 成功路径与探活恢复时归零）。
_dps_consecutive_failures: int = 0


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
    request: Request | None = None,
) -> JSONResponse:
    """转发请求至 DPS 并适配响应（非 SSE，身份头注入；C-16 上游专段同请求汇聚）.

    ``request`` 缺省 None 时仅跳过上游观测（专段挂 ``request.state``），**转发语义不变**，
    便于脚本/工具链直调 ``_forward``。
    """
    await _maybe_probe_dps_health()
    base_url, timeout = _upstream_config()
    target_url = f"{base_url.rstrip('/')}{upstream_path}"
    upstream_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method, target_url,
                json=json_body, params=params,
                headers=headers or {},
            )
    except httpx.HTTPError as exc:
        publish_upstream_response(
            request,
            system=UPSTREAM_SYSTEM_DPS,
            reached=False,
            duration_ms=elapsed_ms(upstream_start),
            error=str(exc),
        )
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
    publish_upstream_response(
        request,
        system=UPSTREAM_SYSTEM_DPS,
        reached=True,
        duration_ms=elapsed_ms(upstream_start),
        status_code=upstream.status_code,
        content_type=content_type_of(upstream),
        payload=getattr(upstream, "content", None),
    )
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
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/portrait/list",
        params={"page": page, "page_size": page_size},
        headers=headers,
        request=request,
    )


@router.get("/portraits/{person_id}")
async def dps_portrait_detail(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像详情（GET /api/v2/portrait/{person_id}）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", f"/api/v2/portrait/{person_id}",
        headers=headers,
        request=request,
    )


@router.post("/portraits/calculate")
async def dps_portrait_calculate(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像计算（POST /api/v2/portrait/calculate，请求体透传上游契约）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", "/api/v2/portrait/calculate",
        json_body=payload,
        headers=headers,
        request=request,
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
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT", f"/api/v2/portrait/{person_id}",
        json_body=payload,
        headers=headers,
        request=request,
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
    headers = _build_identity_headers(_user, request)
    return await _forward("GET", "/api/v2/tags/categories", headers=headers, request=request)


@router.post("/tags/categories")
async def dps_tag_category_create(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """创建标签分类（POST /api/v2/tags/categories，透传上游契约）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", "/api/v2/tags/categories",
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.put("/tags/categories/{category_id}")
async def dps_tag_category_update(
    category_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """更新标签分类（PUT /api/v2/tags/categories/{id}）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT", f"/api/v2/tags/categories/{category_id}",
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.delete("/tags/categories/{category_id}")
async def dps_tag_category_delete(
    category_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """删除标签分类（DELETE /api/v2/tags/categories/{id}）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "DELETE", f"/api/v2/tags/categories/{category_id}",
        headers=headers,
        request=request,
    )


@router.get("/reports/overview")
async def dps_reports_overview(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """报表概览（GET /api/v2/reports/overview）."""
    headers = _build_identity_headers(_user, request)
    return await _forward("GET", "/api/v2/reports/overview", headers=headers, request=request)


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
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", f"/api/v2/batch/import/{task_id}/status",
        headers=headers,
        request=request,
    )


@router.get("/audit/logs")
async def dps_audit_logs(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """审计日志（GET /api/v2/audit/logs）."""
    headers = _build_identity_headers(_user, request)
    return await _forward("GET", "/api/v2/audit/logs", headers=headers, request=request)


# ---------------------------------------------------------------------------
# 健康（AC-145-01-1 透传）
# ---------------------------------------------------------------------------


@router.get("/health")
async def dps_health(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 上游健康透传（GET /health/liveness，DPS 白名单免鉴权）."""
    headers = _build_identity_headers(_user, request)
    return await _forward("GET", "/health/liveness", headers=headers, request=request)


# ---------------------------------------------------------------------------
# v1.4.10 Step 3 P1：模板化能力对接（10 新增端点 #1~#10 ＋ 12 补代理端点 #11~#22）
#
# 契约事实源：《OpenBase-API接口设计文档-v1.4.10》§1（路径映射）／§1.1（补代理）／
# §3.1（权限动作映射，仅文档对齐，本仓不做权限判定）／§3.2（新增端点契约）／
# §3.4（补代理端点契约）。
#
# 统一约定（契约 §1）：
# - 本仓路由 ``/api/v1/dps-proxy/{path}`` → 上游 ``{dps_upstream_base}/api/v2/portrait/{path}``；
# - 分页／幂等／时间格式／错误体（4xx／5xx）语义**保真透传**；
# - 查询参数**原样透传**，不在本仓做参数裁剪或语义改写；
# - 身份头沿用 :func:`_build_identity_headers`（唯一装配点），裁决权在上游。
#
# 路由注册顺序（DT-04 强制，源文件物理顺序即注册顺序）：
#   1) 静态段：/template-packages/*、/lineage/*、/measures/*、/scoring-types；
#   2) 列表路由：/templates、/annotation-templates、/labels（无 path 参数）；
#   3) 动态段：/templates/{code}/*、/annotation-templates/{code}。
# ---------------------------------------------------------------------------

# 上游画像模板域前缀（契约 §1：{DPS_BASE_URL}/api/v2/portrait/{path}）
DPS_PORTRAIT_UPSTREAM_PREFIX = "/api/v2/portrait"


def _portrait_upstream_path(suffix: str) -> str:
    """拼接上游画像模板域路径（``suffix`` 以 ``/`` 起始）."""
    return f"{DPS_PORTRAIT_UPSTREAM_PREFIX}{suffix}"


def _forward_query_params(request: Request) -> dict[str, Any]:
    """透传入站查询参数至上游（保真，不在本仓做语义裁剪）."""
    return dict(request.query_params)


# ---- 静态段 1：模板包（#1 导出 / #2 导入）--------------------------------


@router.post("/template-packages/export")
async def dps_template_package_export(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板包导出（#1，POST；权限动作 portrait_template:create，契约 §3.1）.

    请求体 scope{type,codes[]}／include_annotation_templates 原样透传；
    上游 400（依赖缺失）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/template-packages/export"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/template-packages/import")
async def dps_template_package_import(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板包导入（#2，POST；权限动作 portrait_template:create，契约 §3.1）.

    请求体 package{}／conflict_policy／dry_run 原样透传；上游 409／400／422
    语义保真（不本仓去重，幂等由上游 package_hash 裁决）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/template-packages/import"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 静态段 2：血缘（#7 影响面，静态）先于 #6 标签血缘反查（动态）--------


@router.get("/lineage/impact")
async def dps_lineage_impact(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """影响面（#7，GET；权限动作 annotation_template:read，契约 §3.1）.

    查询参数三层：?template_code=｜?annotation_template_code=｜?tag_code=
    （``?field_key=`` 显式不支持，本仓不拦截，透传上游 400 语义）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/lineage/impact"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/lineage/tags/{tag_code}")
async def dps_lineage_tag_sources(
    tag_code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标签血缘反查（#6，GET；权限动作 annotation_template:read，契约 §3.1）.

    上游 404（无谱系）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/lineage/tags/{tag_code}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 静态段 3：措施建议（#8）---------------------------------------------


@router.get("/measures/suggest")
async def dps_measures_suggest(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """措施建议（#8，GET；权限动作 portrait_template:read，契约 §3.1）.

    查询参数 ?person_id= 透传；响应含 disclaimer，本仓原样透传。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/measures/suggest"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 静态段 4：评分类型（#10）--------------------------------------------


@router.get("/scoring-types")
async def dps_scoring_types(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """评分类型列表（#10，GET；权限动作 portrait_template:read，契约 §3.1）.

    分页参数透传；上游 400（未注册评分类型）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/scoring-types"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 列表路由：画像模板（#11 列表 / #13 创建）先于动态段 /templates/{code} -


@router.get("/templates")
async def dps_templates_list(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板列表（#11，GET E-11；权限动作 portrait_template:read）.

    查询参数 ?status=&profile_type=&subject_type=（均可选）原样透传。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/templates"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates")
async def dps_template_create(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板创建（#13，POST E-13；权限动作 portrait_template:create）.

    请求体原样透传；上游 400（字段级校验）／409（code 冲突）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/templates"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 列表路由：标注模板（#17 列表 / #19 创建）先于同名动态段 --------------


@router.get("/annotation-templates")
async def dps_annotation_templates_list(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注模板列表（#17，GET E-16；权限动作 annotation_template:read）.

    查询参数 ?template_code=&scenario=（均可选）原样透传。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/annotation-templates"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/annotation-templates")
async def dps_annotation_template_create(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注模板创建（#19，POST E-18；权限动作 annotation_template:create）.

    请求体透传；强归属校验（归属画像模板存在且 active）由上游裁决；
    上游 409（code 已存在）／400（其余校验）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/annotation-templates"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 列表路由：标签管理（#22）先于同名动态段 ------------------------------


@router.get("/labels")
async def dps_labels_list(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标签列表（#22，GET E-21；权限动作 annotation_template:read）.

    查询参数 ?action=list 透传；上游 400（action ≠ list）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/labels"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 动态段：画像模板版本操作（#3 对比 / #4 回滚 / #5 预检）--------------


@router.get("/templates/{code}/diff")
async def dps_template_diff(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板版本对比（#3，GET；权限动作 portrait_template:read）.

    上游 404（模板／版本不存在）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/templates/{code}/diff"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates/{code}/rollback")
async def dps_template_rollback(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板版本回滚（#4，POST；权限动作 portrait_template:update，契约 §3.1）.

    请求体 target_version／reason 透传；上游 404（目标版本不存在）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/templates/{code}/rollback"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/templates/{code}/preflight")
async def dps_template_preflight(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板预检（#5，GET；权限动作 portrait_template:read）.

    dry-run 语义（不写入）由上游裁决；响应含影响面三项 ＋ ``basis``，本仓透传。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/templates/{code}/preflight"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 动态段：画像模板详情／更新／启停（#12 / #14 / #15 / #16）-------------


@router.get("/templates/{code}")
async def dps_template_detail(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板详情（#12，GET E-12；权限动作 portrait_template:read）.

    上游 404（不存在）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/templates/{code}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.put("/templates/{code}")
async def dps_template_update(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板更新（#14，PUT E-14；权限动作 portrait_template:update）.

    请求体待变更字段透传；``version`` 递增与 history 留痕由上游裁决；
    上游 404／400（含 extends 自指／成环／深度 >2／父模板不存在）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT", _portrait_upstream_path(f"/templates/{code}"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates/{code}/activate")
async def dps_template_activate(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板激活（#15，POST E-15；权限动作 portrait_template:update，契约 §3.1）.

    无请求体；幂等由上游保证；上游 404 语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/templates/{code}/activate"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates/{code}/deactivate")
async def dps_template_deactivate(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像模板停用（#16，POST E-15；权限动作 portrait_template:update，契约 §3.1）.

    无请求体；幂等由上游保证；上游 404 语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/templates/{code}/deactivate"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 动态段：标注模板详情／更新（改挂）／删除（#18 / #20 / #21）-----------


@router.get("/annotation-templates/{code}")
async def dps_annotation_template_detail(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注模板详情（#18，GET E-17；权限动作 annotation_template:read）.

    上游 404 语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/annotation-templates/{code}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.put("/annotation-templates/{code}")
async def dps_annotation_template_update(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注模板更新／改挂（#20，PUT E-19；权限动作 annotation_template:update）.

    请求体含 ``template_code`` 即改挂；强归属校验与 ``version`` 递增由上游裁决；
    上游 404／400（新归属不存在或未 active、scenario 非法、field_schema 非法）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT", _portrait_upstream_path(f"/annotation-templates/{code}"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.delete("/annotation-templates/{code}")
async def dps_annotation_template_delete(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注模板删除（#21，DELETE E-20；权限动作 annotation_template:delete）.

    上游 404／409（存在关联标注数据）语义保真（含消息条数）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "DELETE", _portrait_upstream_path(f"/annotation-templates/{code}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 动态段 5：AI 标注候选生成（#9）--------------------------------------


@router.post("/annotation-adapters/{adapter_id}/generate")
async def dps_annotation_adapter_generate(
    adapter_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """AI 标注候选生成（#9，POST；权限动作 annotation_template:create，契约 §3.1）.

    请求体 text／annotation_template 透传；上游 403（AI 通道未启用）／503
    （适配器不可用，降级非阻塞）／409（未复核候选进入标签·画像路径，门禁 DT-009）
    语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/annotation-adapters/{adapter_id}/generate"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )
