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
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.dps_proxy.candidate_store import (
    latest_batch,
    list_by_batch,
    save_candidate,
)
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
    keyword: str | None = Query(None),
    external_id: str | None = Query(None),
    template_code: str | None = Query(None),
    stale: bool | None = Query(None),
    org_code: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像列表（GET /api/v2/portrait/list；v1.5.0 A6 透传 keyword/external_id）.

    v1.8.0 T-DM-02：新增 ``template_code`` / ``stale`` 透传，供上层按模板口径
    筛选过期画像；两参数缺省时上游行为不变。
    """
    headers = _build_identity_headers(_user, request)
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if keyword:
        params["keyword"] = keyword
    if external_id:
        params["external_id"] = external_id
    if template_code:
        params["template_code"] = template_code
    if stale is not None:
        params["stale"] = "true" if stale else "false"
    # v2.19.0（波次 B）：组织编码筛选透传
    if org_code:
        params["org_code"] = org_code
    return await _forward(
        "GET", "/api/v2/portrait/list",
        params=params,
        headers=headers,
        request=request,
    )


@router.get("/portraits/export")
async def dps_portraits_export(
    request: Request,
    keyword: str | None = Query(None),
    external_id: str | None = Query(None),
    org_code: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """画像 CSV 导出（v1.5.0 A11；本仓生成，最多 10000 行）.

    注册顺序必须早于 ``/portraits/{person_id}``，否则会被动态段捕获。
    """
    headers = _build_identity_headers(_user, request)
    params: dict[str, Any] = {}
    if keyword:
        params["keyword"] = keyword
    if external_id:
        params["external_id"] = external_id
    if org_code:
        params["org_code"] = org_code
    return await _export_response(
        "/api/v2/portrait/list",
        params,
        headers,
        _PORTRAIT_COLUMNS,
        _portrait_value,
        "portraits",
    )


@router.get("/portraits/by-external/{external_id}")
async def dps_portrait_by_external(
    external_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """按外部身份标识查询画像（GET /api/v2/portrait/by-external/{external_id}，R9）.

    静态段 ``by-external`` 必须先于 ``/portraits/{person_id}`` 注册，避免被动态段
    捕获；上游 404 原样透传（不泄露存在性）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", f"/api/v2/portrait/by-external/{external_id}",
        headers=headers,
        request=request,
    )


@router.get("/portraits/{person_id}")
async def dps_portrait_detail(
    person_id: str,
    request: Request,
    template_code: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像详情（GET /api/v2/portrait/{person_id}）.

    ``template_code`` 透传上游：指定时返回该模板命名空间（``attributes_json[template_code]``）
    的计算结果，缺省行为不变（默认口径）。
    """
    headers = _build_identity_headers(_user, request)
    params = {"template_code": template_code} if template_code else None
    return await _forward(
        "GET", f"/api/v2/portrait/{person_id}",
        params=params,
        headers=headers,
        request=request,
    )


@router.post("/portraits/calculate")
async def dps_portrait_calculate(
    payload: dict[str, Any],
    request: Request,
    async_: bool | None = Query(None, alias="async"),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像计算（POST /api/v2/portrait/calculate）.

    R3 长期：上游 ``async`` 是 **query 参数**（``Query(False, alias="async")``），
    非请求体字段；此处以 query 透传，缺省按 ``dps_calc_async_default`` 决定。
    上游异步返回 202 + task_id，同步返回计算结果。
    """
    headers = _build_identity_headers(_user, request)
    body = dict(payload)
    # 兼容历史调用方把 async 放在 body 的写法：剔除后统一走 query，避免上游忽略
    body.pop("async", None)
    effective_async = (
        async_ if async_ is not None else get_settings().dps_calc_async_default
    )
    return await _forward(
        "POST", "/api/v2/portrait/calculate",
        json_body=body,
        params={"async": "true" if effective_async else "false"},
        headers=headers,
        request=request,
    )


@router.get("/portraits/tasks/{task_id}")
async def dps_portrait_calc_task(
    task_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像异步计算任务查询（GET /api/v2/portrait/tasks/{task_id}，R3 长期）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", f"/api/v2/portrait/tasks/{task_id}",
        headers=headers,
        request=request,
    )


@router.get("/governance/orphan-annotation-templates")
async def dps_orphan_annotation_templates(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """孤儿标注模板治理报告（P3，GET；只读）.

    返回未被任何画像模板绑定的 active 标注模板及建议动作（不自动改数据）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/governance/orphan-annotation-templates"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/governance/scoring-consistency")
async def dps_scoring_consistency_governance(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """评分口径一致性治理报告（v2.13.0，GET；只读）.

    透传上游 ``/api/v2/portrait/governance/scoring-consistency``：返回
    ``scanned/summary/issues/basis/pagination``；本仓不做问题判定与过滤改写。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/governance/scoring-consistency"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/portraits/{person_id}/anomaly-alerts")
async def dps_portrait_anomaly_alerts(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像异常预警聚合（P3，GET；只读）.

    对最近已审核标注按模板 ``anomaly_rules`` 求值并返回命中规则；
    字符串条件以 ``unevaluated_rules`` 显式标注，不执行任意表达式。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", f"/api/v2/portrait/{person_id}/anomaly-alerts",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/portraits/{person_id}/dimension-details")
async def dps_portrait_dimension_details(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像维度规则级明细（GET /api/v2/portrait/{person_id}/dimension-details，P2）.

    返回本维度参与评分的标签、实际得分与缺值兜底标记（只读解释性接口）；
    ``template_code`` 缺省为默认口径。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", f"/api/v2/portrait/{person_id}/dimension-details",
        params=_forward_query_params(request),
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


@router.patch("/portraits/{person_id}")
async def dps_portrait_patch(
    person_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像增量更新（PATCH /api/v2/portrait/{person_id}，R1 深合并）.

    与 PUT 整体覆盖不同，上游按 dict 递归 / list 去重追加 / 标量覆盖 /
    null 删除合并 attributes；可选透传 ``If-Match: <version>`` 触发 409
    ``BIZ_VERSION_CONFLICT``。
    """
    headers = _build_identity_headers(_user, request)
    if_match = request.headers.get("If-Match")
    if if_match:
        headers = {**headers, "If-Match": if_match}
    return await _forward(
        "PATCH", f"/api/v2/portrait/{person_id}",
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.delete("/portraits/{person_id}")
async def dps_portrait_delete(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """画像删除（DELETE /api/v2/portrait/{person_id}，批次 5.1）.

    上游为软删除（``status='deleted'``，保留历史与标注审计），删除后
    GET/列表/检索不可见；重复删除幂等（``already_deleted=true``），
    不存在或跨租户不可见返回 404（原样透传）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "DELETE", f"/api/v2/portrait/{person_id}",
        headers=headers,
        request=request,
    )


# ---------------------------------------------------------------------------
# 标签/报表族（AC-145-03-1）
# ---------------------------------------------------------------------------


@router.get("/tags")
async def dps_tags_search(
    request: Request,
    keyword: str | None = Query(None),
    category_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标签检索（GET /api/v2/tags；v1.5.0 A9）."""
    headers = _build_identity_headers(_user, request)
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if keyword:
        params["keyword"] = keyword
    if category_id:
        params["category_id"] = category_id
    return await _forward(
        "GET", "/api/v2/tags", params=params, headers=headers, request=request
    )


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
    """审计日志（GET /api/v2/audit/logs；查询参数含 resource_id 原样透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/audit/logs",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/audit")
async def dps_audit_timeline(
    request: Request,
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order: str = Query("desc"),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """实体审计时间线（GET /api/v2/audit；v1.5.0 A10）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/audit",
        params={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "page": page,
            "page_size": page_size,
            "order": order,
        },
        headers=headers,
        request=request,
    )


# ---------------------------------------------------------------------------
# CSV 导出（v1.5.0 A11）与 AI 候选持久化（A14）
# ---------------------------------------------------------------------------

_CSV_MAX_ROWS = 10000
_CSV_PAGE_SIZE = 100
_ANNOTATION_COLUMNS = (
    "annotation_id",
    "person_id",
    "profile_id",
    "annotation_template",
    "review_status",
    "review_level",
    "review_levels_required",
    "created_at",
    "updated_at",
    "fields_json",
)
_PORTRAIT_COLUMNS = (
    "person_id",
    "name",
    "status",
    "person_type",
    "region",
    "external_id",
    "created_at",
    "updated_at",
)


def _csv_cell(value: Any) -> str:
    """RFC4180 单元格：转义双引号；防 CSV 注入（= + - @ 与制表/回车前缀）."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        text = "'" + text
    return '"' + text.replace('"', '""') + '"'


def _csv_line(values: list[Any]) -> str:
    return ",".join(_csv_cell(value) for value in values) + "\r\n"


async def _fetch_upstream_json(
    path: str,
    params: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    """拉取上游 JSON（错误映射 502；不返回半截数据）."""
    await _maybe_probe_dps_health()
    base_url, timeout = _upstream_config()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}{path}", params=params, headers=headers
            )
    except httpx.HTTPError as exc:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"DPS upstream unreachable: {exc}"
        ) from exc
    if response.status_code >= 400:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR,
            f"DPS upstream returned {response.status_code}",
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, "DPS upstream returned non-JSON"
        ) from exc
    if isinstance(body, dict) and body.get("code") not in (None, 0, 200):
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR,
            str(body.get("message") or body.get("detail") or "DPS upstream error"),
        )
    return body if isinstance(body, dict) else {"code": 200, "data": body}


def _annotation_value(item: dict[str, Any], column: str) -> Any:
    if column == "annotation_id":
        return item.get("annotation_id") or item.get("id") or ""
    if column == "review_levels_required":
        return item.get("review_levels_required") or item.get("required_levels") or ""
    if column == "fields_json":
        fields = item.get("fields")
        if fields is None:
            fields = item.get("fields_json") or {}
        if isinstance(fields, (dict, list)):
            return json.dumps(fields, ensure_ascii=False)
        return fields
    return item.get(column) or ""


def _portrait_value(item: dict[str, Any], column: str) -> Any:
    return item.get(column) or ""


async def _stream_export(
    path: str,
    params: dict[str, Any],
    headers: dict[str, str],
    columns: tuple[str, ...],
    mapper: Any,
):
    """逐页拉取并流式输出 CSV（UTF-8 BOM；最多 _CSV_MAX_ROWS 行）."""
    yield "\ufeff" + _csv_line(list(columns))
    fetched = 0
    page = 1
    while fetched < _CSV_MAX_ROWS:
        body = await _fetch_upstream_json(
            path,
            {**params, "page": page, "page_size": _CSV_PAGE_SIZE},
            headers,
        )
        data = body.get("data") or {}
        items = data.get("items") or []
        if not items:
            break
        for item in items:
            if fetched >= _CSV_MAX_ROWS:
                return
            yield _csv_line([mapper(item, column) for column in columns])
            fetched += 1
        total = int(data.get("total") or 0)
        if page * _CSV_PAGE_SIZE >= total:
            break
        page += 1


async def _export_response(
    path: str,
    params: dict[str, Any],
    headers: dict[str, str],
    columns: tuple[str, ...],
    mapper: Any,
    filename_prefix: str,
) -> StreamingResponse:
    preflight = await _fetch_upstream_json(
        path, {**params, "page": 1, "page_size": 1}, headers
    )
    total = int((preflight.get("data") or {}).get("total") or 0)
    truncated = total > _CSV_MAX_ROWS
    filename = f"{filename_prefix}-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    logger.info(
        "dps export started",
        extra={
            "path": path,
            "total": total,
            "truncated": truncated,
            "max_rows": _CSV_MAX_ROWS,
        },
    )
    return StreamingResponse(
        _stream_export(path, params, headers, columns, mapper),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Truncated": "true" if truncated else "false",
        },
    )


@router.get("/annotations/export")
async def dps_annotations_export(
    request: Request,
    annotation_template: str | None = Query(None),
    review_status: str | None = Query(None),
    person_id: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """标注 CSV 导出（v1.5.0 A11；本仓生成，最多 10000 行）."""
    headers = _build_identity_headers(_user, request)
    params: dict[str, Any] = {}
    if annotation_template:
        params["annotation_template"] = annotation_template
    if review_status:
        params["review_status"] = review_status
    if person_id:
        params["person_id"] = person_id
    return await _export_response(
        "/api/v2/portrait/annotations",
        params,
        headers,
        _ANNOTATION_COLUMNS,
        _annotation_value,
        "annotations",
    )


@router.post("/annotation-candidates")
async def dps_annotation_candidates_generate(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """生成 AI 候选并落库（v1.5.0 A14；DPS 仍强制 pending）."""
    adapter_id = str(payload.get("adapter_id") or "").strip()
    text = payload.get("text")
    if not adapter_id or not isinstance(text, str) or not text.strip():
        raise BaseError(
            ErrorCode.PARAM_VALIDATION_ERROR, "adapter_id 与 text 为必填"
        )
    headers = _build_identity_headers(_user, request)
    base_url, timeout = _upstream_config()
    safe_adapter_id = quote(adapter_id, safe="")
    target = f"{base_url.rstrip('/')}/api/v2/portrait/annotation-adapters/{safe_adapter_id}/generate"
    body: dict[str, Any] = {"text": text, "annotation_template": payload.get("annotation_template") or ""}
    if payload.get("person_id"):
        body["person_id"] = payload["person_id"]
    if payload.get("profile_id"):
        body["profile_id"] = payload["profile_id"]
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(target, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, f"DPS upstream unreachable: {exc}"
        ) from exc
    if response.status_code >= 400:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR,
            f"DPS upstream returned {response.status_code}",
        )
    try:
        envelope = response.json()
    except ValueError as exc:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, "DPS upstream returned non-JSON"
        ) from exc
    data = (envelope or {}).get("data") or {}
    annotation = data.get("annotation") or data.get("candidate") or {}
    upstream_id = str(
        annotation.get("id")
        or annotation.get("annotation_id")
        or data.get("annotation_id")
        or ""
    )
    if not upstream_id:
        raise BaseError(
            ErrorCode.SYS_UPSTREAM_ERROR, "DPS 未返回候选 annotation_id，无法持久化"
        )
    fields = annotation.get("fields") or data.get("fields") or {}
    saved = await save_candidate(
        tenant_id=headers.get("X-Tenant-ID") or "",
        operator=headers.get("X-User-ID") or "",
        adapter_id=adapter_id,
        annotation_template=str(body.get("annotation_template") or ""),
        upstream_annotation_id=upstream_id,
        review_status=str(annotation.get("review_status") or "pending"),
        fields=fields if isinstance(fields, dict) else {"value": fields},
        person_id=payload.get("person_id"),
        profile_id=payload.get("profile_id"),
        batch_id=payload.get("batch_id"),
    )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "success", "data": {"batch_id": saved["batch_id"], "candidate": saved}},
    )


@router.get("/annotation-candidates")
async def dps_annotation_candidates_list(
    request: Request,
    batch_id: str = Query(...),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """按批次查询已持久化候选（v1.5.0 A14；租户隔离）."""
    headers = _build_identity_headers(_user, request)
    items = await list_by_batch(headers.get("X-Tenant-ID") or "", batch_id)
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "success",
            "data": {"batch_id": batch_id, "items": items, "total": len(items)},
        },
    )


@router.get("/annotation-candidates/latest")
async def dps_annotation_candidates_latest(
    request: Request,
    adapter_id: str | None = Query(None),
    annotation_template: str | None = Query(None),
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """最近候选批次（v1.5.0 A14；无数据返回空集合 200）."""
    headers = _build_identity_headers(_user, request)
    batch_id, items = await latest_batch(
        headers.get("X-Tenant-ID") or "",
        adapter_id=adapter_id,
        annotation_template=annotation_template,
    )
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "success",
            "data": {"batch_id": batch_id, "items": items, "total": len(items)},
        },
    )


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
# v1.12.0（XR-DPS-05 / XR-DPS-03）：运行态观测与治理只读扩权
#
# 允许清单**仅**包含六个只读端点（均无写方法）：
#   GET /api/v2/metrics              运行态指标（QPS/CPU/内存/uptime/requests_total）
#   GET /api/v2/rate-limits/status   限流只读指标
#   GET /api/v2/alerts/rules         告警规则只读
#   GET /api/v2/api-registry         API 注册表只读
#   GET /api/v2/error-codes          错误码只读
#   GET /api/v2/permissions/roles    角色权限只读
# 上游写面已按 ADR-290-01 收口为 410；本仓不提供任何写方法代理，也不做权限判定
# （401/403 语义保真透传）。
# ---------------------------------------------------------------------------


@router.get("/metrics")
async def dps_runtime_metrics(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 运行态指标（GET /api/v2/metrics；上游权限 runtime_metric:read）."""
    headers = _build_identity_headers(_user, request)
    return await _forward("GET", "/api/v2/metrics", headers=headers, request=request)


@router.get("/rate-limits/status")
async def dps_rate_limit_status(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 限流状态（GET /api/v2/rate-limits/status；查询参数原样透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/rate-limits/status",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/alerts/rules")
async def dps_alert_rules(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 告警规则只读（GET /api/v2/alerts/rules；上游带 Deprecation/Sunset 头）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/alerts/rules",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/api-registry")
async def dps_api_registry(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS API 注册表只读（GET /api/v2/api-registry；查询参数原样透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/api-registry",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/error-codes")
async def dps_error_codes(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 错误码只读（GET /api/v2/error-codes；查询参数原样透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/error-codes",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/permissions/roles")
async def dps_permission_roles(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """DPS 角色权限只读（GET /api/v2/permissions/roles；上游带 Deprecation/Sunset 头）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", "/api/v2/permissions/roles",
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


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


# 上游 v2 域前缀（波次 B：组织与引入任务，契约 /api/v2/{path}）
DPS_V2_UPSTREAM_PREFIX = "/api/v2"


def _v2_upstream_path(suffix: str) -> str:
    """拼接上游 v2 域路径（``suffix`` 以 ``/`` 起始）."""
    return f"{DPS_V2_UPSTREAM_PREFIX}{suffix}"


# ---- 波次 B（2.19.0）：组织与引入任务 -------------------------------------


@router.get("/orgs")
async def dps_list_orgs(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """组织平铺列表（GET；只读）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/orgs"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/orgs/tree")
async def dps_org_tree(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """组织树（GET；只读）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/orgs/tree"),
        headers=headers,
        request=request,
    )


@router.get("/orgs/{code}/members")
async def dps_org_members(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """组织成员列表（GET；只读）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/orgs/{code}/members"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.put("/orgs/{code}/members")
async def dps_upsert_org_members(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """批量维护组织成员（PUT；写动作）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT",
        _v2_upstream_path(f"/orgs/{code}/members"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.post("/ingest/preview")
async def dps_ingest_preview(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """引入预览（POST；脱敏，由 DPS 完成）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path("/ingest/preview"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.post("/ingest/execute")
async def dps_ingest_execute(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """执行引入（POST；开关关闭时上游保持模拟路径）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path("/ingest/execute"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.get("/ingest/tasks")
async def dps_ingest_tasks(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """引入任务列表（GET；静态段先于 /ingest/tasks/{task_id}）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/ingest/tasks"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/ingest/tasks/{task_id}")
async def dps_ingest_task_detail(
    task_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """引入任务详情（GET）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/ingest/tasks/{task_id}"),
        headers=headers,
        request=request,
    )


@router.post("/ingest/tasks/{task_id}/retry")
async def dps_ingest_task_retry(
    task_id: str,
    request: Request,
    payload: dict[str, Any] | None = None,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """重试引入任务（POST）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path(f"/ingest/tasks/{task_id}/retry"),
        json_body=payload or {},
        headers=headers,
        request=request,
    )


@router.get("/ingest/tasks/{task_id}/errors")
async def dps_ingest_task_errors(
    task_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """引入任务错误行（GET；上游已脱敏）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/ingest/tasks/{task_id}/errors"),
        headers=headers,
        request=request,
    )


# ---- 波次 C（2.20.0）：进度、业务事项与调度 --------------------------------


@router.post("/progress/calculate")
async def dps_progress_calculate(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """计算进度快照（POST；开关关闭时上游 409 原样透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path("/progress/calculate"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.get("/progress/{person_id}")
async def dps_progress_trend(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """进度趋势（GET；周期类型与条数原样透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/progress/{person_id}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/progress/{person_id}/items")
async def dps_progress_items(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """进度事项列表（GET）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/progress/{person_id}/items"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/progress/{person_id}/overdue")
async def dps_progress_overdue(
    person_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """逾期事项（GET）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/progress/{person_id}/overdue"),
        headers=headers,
        request=request,
    )


@router.get("/business-items")
async def dps_list_business_items(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """业务事项列表（GET；静态段先于 /schedules/{id}）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/business-items"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/business-items")
async def dps_upsert_business_item(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """业务事项写入（POST；唯一键幂等由上游裁决）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path("/business-items"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.get("/schedules/preview")
async def dps_schedule_preview_expression(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """cron 表达式预览（GET；静态段必须先于 /schedules/{id}/preview）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/schedules/preview"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/schedules")
async def dps_list_schedules(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """调度列表（GET）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/schedules"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/schedules")
async def dps_create_schedule(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """创建调度（POST；非法 cron 由上游 400 语义保真）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path("/schedules"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.put("/schedules/{schedule_id}")
async def dps_update_schedule(
    schedule_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """更新调度（PUT）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT",
        _v2_upstream_path(f"/schedules/{schedule_id}"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.get("/schedules/{schedule_id}/preview")
async def dps_preview_schedule(
    schedule_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """既有调度的未来触发预览（GET）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path(f"/schedules/{schedule_id}/preview"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/schedules/{schedule_id}/run")
async def dps_run_schedule(
    schedule_id: str,
    request: Request,
    payload: dict[str, Any] | None = None,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """立即执行一次调度（POST）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _v2_upstream_path(f"/schedules/{schedule_id}/run"),
        json_body=payload or {},
        headers=headers,
        request=request,
    )


@router.get("/audit/logs")
async def dps_audit_logs(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """审计日志查询（GET；DPS 侧按角色/范围裁决，本仓仅透传）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _v2_upstream_path("/audit/logs"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


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

    查询参数 ?status=&profile_type=&subject_type=&keyword=&category_id=&template_kind=
    （均可选）原样透传；服务端筛选依赖 DPS ≥2.16.0（A7）。
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


# ---- v2.12.0 模板分类树（静态段：tree 先于动态段 {category_id}）------------


@router.get("/template-categories/tree")
async def dps_template_category_tree(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板分类树（GET；上游 /api/v2/portrait/template-categories/tree）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/template-categories/tree"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/template-categories")
async def dps_template_category_list(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板分类平铺列表（GET；上游 /api/v2/portrait/template-categories）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/template-categories"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/template-categories")
async def dps_template_category_create(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """新建模板分类（POST；上游 409/400 语义保真）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/template-categories"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.put("/template-categories/{category_id}")
async def dps_template_category_update(
    category_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """编辑模板分类（PUT；code 不可改，由上游裁决）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT", _portrait_upstream_path(f"/template-categories/{category_id}"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.post("/template-categories/{category_id}/move")
async def dps_template_category_move(
    category_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """移动模板分类（POST；层级上限 3 由上游裁决）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/template-categories/{category_id}/move"),
        json_body=payload,
        headers=headers,
        request=request,
    )


# ---- v2.12.0 子模板挂载（须先于动态段 /templates/{code}）-------------------


@router.get("/templates/{code}/components")
async def dps_template_components_list(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """子模板挂载清单（GET；含子模板名称/类型/版本）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/templates/{code}/components"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates/{code}/components")
async def dps_template_component_mount(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """挂载子模板（POST；挂载即升父模板版本并写快照）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/templates/{code}/components"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.put("/templates/{code}/components/order")
async def dps_template_components_reorder(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """子模板排序（PUT；child_codes 须覆盖全部已挂载项）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "PUT", _portrait_upstream_path(f"/templates/{code}/components/order"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.delete("/templates/{code}/components/{child_code}")
async def dps_template_component_unmount(
    code: str,
    child_code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """卸载子模板（DELETE；必挂项由上游 409 拒绝）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "DELETE", _portrait_upstream_path(f"/templates/{code}/components/{child_code}"),
        headers=headers,
        request=request,
    )


# ---- v2.12.0 标注范围预检（单模板 / 模板类）--------------------------------


@router.get("/annotation-scopes/resolve")
async def dps_annotation_scope_resolve(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注范围预检（GET；超阈值返回 requires_confirmation=true）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/annotation-scopes/resolve"),
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


@router.get("/templates/{code}/scoring-items")
async def dps_template_scoring_items(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板实际评分项字典（GET；权限动作 portrait_template:read）.

    返回继承解析后的维度权重与规则明细，与画像计算口径一致。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/templates/{code}/scoring-items"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/templates/{code}/lineage")
async def dps_template_lineage(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板四联视图（P2，GET；权限动作 portrait_template:read）.

    返回族谱 / 标注模板 / 标签产出 / 评分项与实际缺口，
    供前端单一数据源消费；上游 404 语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/templates/{code}/lineage"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


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


# ---- 画像模板可视化（v2.12.0 P1）：元数据 / 校验 / 试算 -------------------
# 契约：《OpenBase-画像模板与标注模板可视化设计》§8.2；三者均**只读、无副作用**。


@router.get("/meta/schema")
async def dps_portrait_meta_schema(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板可视化元数据（GET /api/v2/portrait/meta/schema；权限 portrait_template:read）."""
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/meta/schema"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates/{code}/validate")
async def dps_template_validate(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板服务端全量校验（POST；只读，可校验未保存草稿 ``{template}``）.

    返回字段级 ``[{path, code, message, severity}]``；校验失败仍为 200（``valid=false``），
    由前端按 path 定位节点。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/templates/{code}/validate"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/templates/{code}/preview")
async def dps_template_preview(
    code: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """模板样例试算（POST；dry-run 无副作用）.

    请求体 ``{template?, sample}``；``template`` 缺省取库内模板（未保存草稿可显式传入）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/templates/{code}/preview"),
        json_body=payload,
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


@router.delete("/templates/{code}")
async def dps_template_delete(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """删除画像模板（DELETE /api/v2/portrait/templates/{code}）.

    上游在存在子模板/标注模板/标签血缘引用时返回 409，本层原样透传。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "DELETE", _portrait_upstream_path(f"/templates/{code}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


# ---- 动态段：标注模板详情／更新（改挂）／删除（#18 / #20 / #21）-----------


@router.get("/annotation-templates/{code}/field-mapping")
async def dps_annotation_field_mapping(
    code: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注模板字段映射（P2，GET；权限动作 annotation_template:read）.

    逐字段返回「将写入 dimension:tag_key / 计分规则 / 影响哪个评分项」；
    ``portrait_template`` 查询参数透传，缺省由上游取强归属画像模板。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/annotation-templates/{code}/field-mapping"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


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


# ---- 动态段 6：标注复核（单条 / 批量，OBS-02-DEF-02，2026-10-26）-----------


@router.get("/annotations")
async def dps_annotations_list(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注队列查询（GET；上游 ``/api/v2/portrait/annotations``）.

    查询参数 ``annotation_template`` / ``review_status`` / ``person_id`` /
    ``reviewer`` / ``level`` / ``page`` / ``page_size`` 原样透传（v2.16.0 A2 起
    支持 ``reviewer=me`` 与级数过滤；身份解析在 DPS 侧，本仓不构造身份头）。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/annotations"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/annotations/stats")
async def dps_annotations_stats(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注队列聚合统计（A1，GET；上游 ``/api/v2/portrait/annotations/stats``）.

    静态段先于 ``/annotations/{annotation_id}`` 注册（DT-04）；查询参数
    ``group_by``／``annotation_template``／``review_status``／``person_id`` 原样透传，
    上游 400（非法分组/状态）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path("/annotations/stats"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/annotations/{annotation_id}")
async def dps_annotation_detail(
    annotation_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注详情（A4，GET；上游 ``/api/v2/portrait/annotations/{id}``）.

    一次返回审核对照所需的全量上下文（结构化字段、证据来源、模板与主体归属、
    审核状态/级数/审核人与意见、时间戳）。标注不存在或跨租户不可见 → 上游 404
    语义保真；路径片段经 ``quote(safe="")`` 编码，避免特殊字符改写上游路由。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET",
        _portrait_upstream_path(f"/annotations/{quote(annotation_id, safe='')}"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/annotate")
async def dps_annotate(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注创建/查询（POST；上游 ``/api/v2/portrait/annotate``）.

    结构化分支需 ``annotation_template`` + ``fields``（主体须已有画像）；自由文本分支
    只需 ``content``。请求体原样透传，归属门禁与字段校验以 DPS 为准。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/annotate"),
        json_body=payload,
        headers=headers,
        request=request,
    )


@router.post("/annotations/batch-review")
async def dps_annotations_batch_review(
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """批量复核（POST；上游 ``/api/v2/portrait/annotations/batch-review``）.

    请求体 ``{"items":[{annotation_id,status,current_status?,comment?}]}`` 原样透传；
    上游逐条返回成功/失败（单条失败不影响其余条目），语义保真。

    背景（OBS-02 深走查）：此前 dps-proxy 未登记任何标注复核路由，前端
    ``/dps-proxy/annotations/...`` 一律 404，「提交复核结果」与逐条通过/驳回均未生效。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path("/annotations/batch-review"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/annotations/{annotation_id}/review")
async def dps_annotation_review(
    annotation_id: str,
    payload: dict[str, Any],
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """标注复核状态流转（POST；上游 ``/api/v2/portrait/annotations/{id}/review``）.

    请求体 ``status``/``action``/``current_status``/``comment``/``annotation_template``/
    ``fields`` 原样透传；上游 404（标注不存在）／409（流转非法或未复核候选进入
    标签·画像路径）语义保真。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST", _portrait_upstream_path(f"/annotations/{annotation_id}/review"),
        json_body=payload,
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.post("/annotations/{annotation_id}/claim")
async def dps_annotation_claim(
    annotation_id: str,
    request: Request,
    payload: dict[str, Any] | None = None,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """领取待审核标注（A2，POST；上游 ``/api/v2/portrait/annotations/{id}/claim``）.

    请求体可选且原样透传；上游 401（身份缺失）／404（不存在）／409（非待审核或
    已被他人领取）语义保真。路径片段经 ``quote(safe="")`` 编码。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "POST",
        _portrait_upstream_path(f"/annotations/{quote(annotation_id, safe='')}/claim"),
        json_body=payload or {},
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )


@router.get("/annotations/{annotation_id}/review-log")
async def dps_annotation_review_log(
    annotation_id: str,
    request: Request,
    _user: dict = Depends(get_current_user),
) -> JSONResponse:
    """审核留痕查询（GET；上游 ``/api/v2/portrait/annotations/{id}/review-log``）.

    P4（多级审核）：只读返回逐级审核记录；标注不存在 404，留痕表未迁移返回空列表。
    """
    headers = _build_identity_headers(_user, request)
    return await _forward(
        "GET", _portrait_upstream_path(f"/annotations/{annotation_id}/review-log"),
        params=_forward_query_params(request),
        headers=headers,
        request=request,
    )



# ---- 动态段 7：AI 标注候选生成（#9）--------------------------------------


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
