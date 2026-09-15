"""日志中心路由层（ADR-146-01）.

统一检索三端点：``GET /logs/search`` / ``GET /logs/facets`` / ``GET /logs/export``。
全部受权 ``log:read``；筛选参数经 Pydantic 校验（list 长度上限在 schema 约束内）。
响应信封 ``{code, message, data}`` 与项目统一契约对齐。

导出端点（ADR-146-04）在返回附件前完成两件事，顺序固定：
① 上限/通道校验（``log_service.export`` 抛 ``PARAM_400`` / 留痕通道不可用 503）；
② 写 1 条 ``audit_logs(action="log.export")`` 留痕（落库异常仅 WARN，不阻断导出）。

接线口径（缺陷修复，HTTP 层用例 tests/test_logs_endpoints_api.py 暴露）：
查询参数模型必须用 ``Annotated[Model, Query()]``（FastAPI「Query Parameter Models」），
**不能**用 ``Depends()``——后者按字段类型分派，``list[...]`` 字段会被判为 Body 参数：
① 请求未带该参数时把 ``default_factory`` 哨兵当作取值 → 422/500；
② 请求带了重复查询参数也不会被读取（过滤条件静默失效）。

导出的阻塞式多源扫描（含 L1 文件读与适配器 ``asyncio.run``）经 ``asyncio.to_thread``
下沉到线程池：既不阻塞事件循环，也让留痕写入复用**同一事件循环**的 DB 会话工厂。
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from openbase.modules.auth.rbac import require_permission
from openbase.modules.logs import service as log_service
from openbase.modules.logs.schemas import LogExportParams, LogQueryParams, LogSearchParams

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

__all__ = ["router"]


def _ok(data: object) -> dict:
    return {"code": 0, "message": "success", "data": data}


def _request_id(request: Request) -> str:
    """请求关联 ID（审计中间件已注入；缺失时兜底生成，与统一错误体同构）."""
    existing = getattr(request.state, "request_id", None)
    return existing or f"req-{uuid.uuid4().hex[:12]}"


@router.get(
    "/search",
    dependencies=[Depends(require_permission("log:read"))],
)
def search_logs(params: Annotated[LogSearchParams, Query()]) -> dict:
    """多源统一检索（分页 + 截断标注）。"""
    return _ok(log_service.search(params))


@router.get(
    "/facets",
    dependencies=[Depends(require_permission("log:read"))],
)
def facets_logs(params: Annotated[LogQueryParams, Query()]) -> dict:
    """维度聚合（module / operation / result / operator）。"""
    return _ok(log_service.facets(params))


@router.get(
    "/facets/presets",
    dependencies=[Depends(require_permission("log:read"))],
)
def facets_presets() -> dict:
    """筛选器候选枚举（供前端渲染下拉）。"""
    return _ok(log_service.build_facets_presets())


@router.get("/export")
async def export_logs(
    params: Annotated[LogExportParams, Query()],
    request: Request,
    user: dict = Depends(require_permission("log:read")),
) -> Response:
    """导出 CSV / JSON（附件命名 / BOM / 上限 400 / 导出留痕，见 API §3.3）.

    - 权限：``log:read``（仅管理员）；
    - 失败路径：命中数 > 10000 → 400 ``PARAM_400``（``detail={matched, limit}``）；
      留痕通道显式不可用 → 503 ``BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE``（不产出无留痕文件）；
    - 留痕失败（通道可用但落库异常）→ WARN 后照常返回文件（ADR-146-04 降级语义）。
    """
    payload = await asyncio.to_thread(log_service.export, params)
    await log_service.record_export_audit(
        actor=user.get("id"),
        source=params.source,
        filters=log_service.export_filter_summary(params),
        row_count=payload.row_count,
        export_format=params.format,
        request_id=_request_id(request),
    )
    return Response(
        content=payload.content,
        media_type=payload.media_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )
