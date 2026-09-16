"""日志中心 Service 层（ADR-146-01）。

负责查询参数归一化、跨适配器编排、分页切片与导出（CSV/JSON）。
排序口径由适配器统一（ts 倒序 + 稳定次序，见 repository.BaseRepository._slice），
本层仅做分页与汇总，不重复实现过滤逻辑。

执行面（INT-146-001）：本层对外提供成对的入口——
``search/facets/export``（同步，供文件/内存类源与非 HTTP 调用方）与
``search_async/facets_async/export_async``（HTTP 端点入口，统一经 :func:`_fetch_async`
按适配器执行面在「主事件循环 async 会话」与「线程池同步扫描」之间选择，
**禁止**在工作线程内自建事件循环复用进程级 async 连接池）。

导出契约（《OpenBase-API接口设计文档-v1.4.6》§3.3 / 需求 §4.6）：
文件名 ``logs-<source>-<ts>.<ext>``、CSV 带 ``\\ufeff`` BOM、命中 > 10000 → 400
``PARAM_400``、每次成功导出写 1 条 ``audit_logs(action="log.export")`` 留痕
（不记录检索关键字与导出内容，见 ADR-146-04 与非功能 §3）。
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.mask import mask_sensitive
from openbase.modules.logs.repository import (
    FetchResult,
    Filters,
    LogEntry,
    LogRepository,
    get_adapter,
)
from openbase.modules.logs.schemas import (
    LOG_MODULES,
    LOG_OPERATIONS,
    LOG_RESULTS,
    LOG_SOURCES,
    LogExportParams,
    LogQueryParams,
    LogSearchParams,
)

logger = logging.getLogger("openbase.logs")

# 导出条数上限（需求 §4.6「条数上限 10000」/ API §3.3「命中数 > 10000 → 400 PARAM_400」）
EXPORT_ROW_LIMIT: int = 10000

# CSV BOM（API §3.3 CSV 细节：UTF-8 + 含 \ufeff BOM，Excel 兼容）
CSV_BOM: str = "\ufeff"

# 文件名时间戳格式（API §3.3 只写 `<ts>`，未定义具体格式）。取**最保守解释**：
# 文件系统安全（不含 `:` 等 Windows 非法字符）且可按字典序排序的 YYYYMMDD-HHMMSS。
EXPORT_TIMESTAMP_FORMAT: str = "%Y%m%d-%H%M%S"

# 导出留痕动作码（API §3.3 / ADR-146-04）
ACTION_LOG_EXPORT: str = "log.export"

# 留痕开关：审计落库通道（与 audit / testing / frontend 模块同源同开关）
ENV_AUDIT_DB_PERSIST: str = "OPENBASE_AUDIT_DB_PERSIST"

# 导出 CSV 固定列序（与 API 设计文档 §3 对齐）
CSV_COLUMNS: tuple[str, ...] = (
    "ts",
    "source",
    "module",
    "operation",
    "result",
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "operator_id",
    "tenant_id",
    "ip_address",
    "case_id",
    "step_id",
    "run_id",
    "action",
    "summary",
)


@dataclass(frozen=True)
class ExportPayload:
    """导出产物（媒体类型 / 附件名 / 内容 / 导出条数）."""

    media_type: str
    filename: str
    content: str
    row_count: int


def _parse_datetime(value: str | None, field: str) -> datetime | None:
    """解析 ``from`` / ``to`` 时间边界；非法输入 → 400 ``PARAM_400``.

    v1.4.6 Step 4 裁定（DEF-BE-146-006）：设计 §3.1 将 ``from``/``to`` 定义为
    string(ISO8601)，非法输入**不得静默忽略为全量结果**，须显式拒绝（``detail.field``
    标注出错字段），与「参数校验失败 → 400 ``PARAM_400``」同口径。
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BaseError(
            ErrorCode.PARAM_VALIDATION_ERROR,
            f"invalid '{field}' time format: expected ISO8601",
            {"field": field},
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_window(from_dt: datetime | None, to_dt: datetime | None) -> None:
    """时间窗语义校验：``from > to`` → 400 ``PARAM_400``（设计 §5「时间窗非法」）."""
    if from_dt is not None and to_dt is not None and from_dt > to_dt:
        raise BaseError(
            ErrorCode.PARAM_VALIDATION_ERROR,
            "invalid time window: 'from' must not be later than 'to'",
            {"field": "from/to"},
        )


def _build_filters(
    params: LogQueryParams, limit: int, item_cap: int | None = None
) -> Filters:
    """把请求参数归一到供适配器消费的 Filters（``item_cap`` 仅分页检索传入）."""
    from_dt = _parse_datetime(params.from_, "from")
    to_dt = _parse_datetime(params.to, "to")
    _validate_window(from_dt, to_dt)
    return Filters(
        source=params.source,
        modules=list(params.module),
        operations=list(params.operation),
        results=list(params.result),
        operators=list(params.operator),
        q=(params.q or "").strip() if params.q else None,
        from_=from_dt,
        to=to_dt,
        case_id=params.case_id,
        run_id=params.run_id,
        step_id=params.step_id,
        limit=limit,
        item_cap=item_cap,
    )


def _page_end(page: int, page_size: int) -> int:
    """本页末尾下标（含）：适配器按该值收口，避免为一个分页请求物化整片命中集。"""
    return page * page_size


def _pagination(
    page: int, page_size: int
) -> tuple[int, int]:
    start = (page - 1) * page_size
    return start, start + page_size


def _page_of(result: FetchResult, params: LogSearchParams) -> dict[str, Any]:
    """把取数结果按分页参数切片为响应体（``total`` / ``truncated`` 原样透传）."""
    start, end = _pagination(params.page, params.page_size)
    items = result.items[start:end]
    return {
        "items": [item.model_dump() for item in items],
        "total": result.total,
        "page": params.page,
        "page_size": params.page_size,
        "truncated": result.truncated,
    }


async def _fetch_async(adapter: LogRepository, filters: Filters) -> FetchResult:
    """统一取数入口：按适配器执行面选择「主事件循环 async 会话」或「线程池同步扫描」.

    设计依据（INT-146-001）：进程级 async 连接池**不可跨事件循环复用**，故 DB 类源
    （``async_source=True``）必须在主事件循环内取数；文件类源的阻塞 I/O 则下沉线程池，
    避免阻塞事件循环。
    """
    if getattr(adapter, "async_source", False):
        return await adapter.fetch_async(filters)  # type: ignore[attr-defined]
    return await asyncio.to_thread(adapter.fetch, filters)


async def _facets_async(adapter: LogRepository, filters: Filters) -> dict[str, dict[str, int]]:
    """统一维度聚合入口（执行面选择同 :func:`_fetch_async`）."""
    if getattr(adapter, "async_source", False):
        agg = await adapter.facets_async(filters)  # type: ignore[attr-defined]
    else:
        agg = await asyncio.to_thread(adapter.facets, filters)
    return {dimension: dict(counter) for dimension, counter in agg.items()}


def search(params: LogSearchParams) -> dict[str, Any]:
    """单源检索（**同步入口**：文件/内存类源；DB 类源请用 :func:`search_async`）.

    适配器取满足条件的已排序集合 → 分页切片 + 截断标注；分页收口 ``item_cap`` 只影响
    ``items`` 物化条数，``total`` 仍为扫描范围内的精确命中数。
    """
    adapter = get_adapter(params.source)
    filters = _build_filters(
        params,
        limit=adapter.limits["max_lines"],
        item_cap=_page_end(params.page, params.page_size),
    )
    return _page_of(adapter.fetch(filters), params)


async def search_async(params: LogSearchParams) -> dict[str, Any]:
    """单源检索（HTTP 端点入口：DB 类源在主事件循环内取数，文件类源下沉线程池）."""
    adapter = get_adapter(params.source)
    filters = _build_filters(
        params,
        limit=adapter.limits["max_lines"],
        item_cap=_page_end(params.page, params.page_size),
    )
    return _page_of(await _fetch_async(adapter, filters), params)


def facets(params: LogQueryParams) -> dict[str, dict[str, int]]:
    """单源维度聚合（**同步入口**；DB 类源请用 :func:`facets_async`）。"""
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    agg = adapter.facets(filters)
    return {dimension: dict(counter) for dimension, counter in agg.items()}


async def facets_async(params: LogQueryParams) -> dict[str, dict[str, int]]:
    """单源维度聚合（HTTP 端点入口）。"""
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    return await _facets_async(adapter, filters)


def _entry_row(entry: LogEntry) -> list[Any]:
    summary = entry.model_dump().get("summary") if entry.summary else None
    return [
        entry.ts,
        entry.source,
        entry.module,
        entry.operation,
        entry.result,
        entry.request_id,
        entry.method,
        entry.path,
        entry.status_code,
        entry.duration_ms,
        entry.operator_id,
        entry.tenant_id,
        entry.ip_address,
        entry.case_id,
        entry.step_id,
        entry.run_id,
        entry.action,
        # API §3.3 CSV 细节：summary 序列化为**紧凑** JSON 字符串
        json.dumps(summary, ensure_ascii=False, separators=(",", ":")) if summary else None,
    ]


def export_filename(source: str, export_format: str, *, moment: datetime | None = None) -> str:
    """构造导出附件名 ``logs-<source>-<ts>.<ext>``（API §3.3 原文命名）.

    Args:
        source: 数据源（``l1_file`` / ``audit_db`` / ``test_record`` / ``repo_log``）。
        export_format: ``csv`` 或 ``json``。
        moment: 时间戳取值时刻（缺省取当前时刻；供测试注入）。

    Returns:
        形如 ``logs-l1_file-20260915-120102.csv`` 的附件名（不含路径分隔符）。
    """
    timestamp = (moment or datetime.now()).strftime(EXPORT_TIMESTAMP_FORMAT)
    return f"logs-{source}-{timestamp}.{export_format}"


def export_filter_summary(params: LogQueryParams) -> dict[str, Any]:
    """导出留痕的「筛选摘要」（API §3.3 ``detail.filters``）.

    口径：
    - 仅落**非空**维度（module/operation/result/operator/时间窗/测试三元组）；
    - **不含检索关键字 ``q``**：AC-146-03-3 与系统架构 §6「检索词不落盘」明令查询关键字
      不得写入 L1 与 ``audit_logs``（故此处既不落原值也不落摘要值）；
    - 落库前由 :func:`record_export_audit` 统一走 ``mask_sensitive`` 脱敏。

    Returns:
        供写入 ``audit_logs.detail.filters`` 的筛选摘要字典。
    """
    summary: dict[str, Any] = {}
    for dimension in ("module", "operation", "result", "operator"):
        values = list(getattr(params, dimension))
        if values:
            summary[dimension] = values
    if params.from_:
        summary["from"] = params.from_
    if params.to:
        summary["to"] = params.to
    if params.case_id:
        summary["case_id"] = params.case_id
    if params.run_id:
        summary["run_id"] = params.run_id
    if params.step_id is not None:
        summary["step_id"] = params.step_id
    return summary


def _assert_audit_channel_available() -> None:
    """校验留痕通道可用；``OPENBASE_AUDIT_DB_PERSIST=0`` = 显式不可用 → 拒绝导出.

    Raises:
        BaseError: ``BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE``（503）。
    """
    if os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
        raise BaseError(
            ErrorCode.BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE,
            "log export rejected: audit trail unavailable",
            detail={"reason": "audit persist disabled"},
        )


async def _persist_export_audit(*, actor: str | None, detail: dict[str, Any], request_id: str) -> None:
    """写 1 条 ``audit_logs(action=log.export)``（复用既有 AuditLog 模型，不新增表）."""
    from openbase.core.db.session import get_session_factory
    from openbase.core.models import AuditLog

    actor_text = str(actor) if actor is not None else ""
    session = None
    try:
        async with get_session_factory()() as session:
            session.add(
                AuditLog(
                    user_id=int(actor_text) if actor_text.isdigit() else None,
                    tenant_id=None,
                    action=ACTION_LOG_EXPORT,
                    resource="logs:export",
                    resource_id=str(detail.get("source") or "")[:64] or None,
                    request_id=request_id,
                    detail=detail,
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001 - 交由调用方按降级语义处置
        if session is not None:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
        raise


async def record_export_audit(
    *,
    actor: str | int | None,
    source: str,
    filters: dict[str, Any],
    row_count: int,
    export_format: str,
    request_id: str,
) -> bool:
    """导出留痕（API §3.3：``detail={actor, source, filters, row_count, format}``）.

    语义（ADR-146-04）：留痕**失败不得导致导出失败** —— 落库异常仅 ``WARN`` 后返回
    ``False``（降级），文件照常返回；``OPENBASE_AUDIT_DB_PERSIST=0``（通道显式不可用）
    由 :func:`_assert_audit_channel_available` 在导出前 fail-closed 拦截，不走本函数。

    Returns:
        是否成功落库。
    """
    detail = {
        "actor": str(actor) if actor is not None else None,
        "source": source,
        "filters": mask_sensitive(filters),
        "row_count": row_count,
        "format": export_format,
    }
    try:
        await _persist_export_audit(actor=actor, detail=detail, request_id=request_id)
    except Exception:  # noqa: BLE001 - 留痕降级：WARN 不阻断导出
        logger.warning(
            "log.export audit persist failed (degraded); export continues",
            extra={"source": source, "row_count": row_count, "request_id": request_id},
        )
        return False
    return True


def _render_export(result: FetchResult, params: LogExportParams) -> ExportPayload:
    """把取数结果渲染为导出产物（上限校验 + CSV/JSON；文件名与列序契约见 API §3.3）.

    Raises:
        BaseError: 命中数超上限（``PARAM_EXPORT_LIMIT_EXCEEDED`` = ``PARAM_400``，400，
            detail 含 ``{matched, limit}``）。
    """
    if result.total > EXPORT_ROW_LIMIT:
        raise BaseError(
            ErrorCode.PARAM_EXPORT_LIMIT_EXCEEDED,
            f"export matched rows exceed limit: matched={result.total}, limit={EXPORT_ROW_LIMIT}",
            detail={"matched": result.total, "limit": EXPORT_ROW_LIMIT},
        )

    if params.format == "json":
        payload = json.dumps(
            [entry.model_dump() for entry in result.items], ensure_ascii=False
        )
        return ExportPayload(
            media_type="application/json",
            filename=export_filename(params.source, "json"),
            content=payload,
            row_count=result.total,
        )

    buffer = io.StringIO()
    buffer.write(CSV_BOM)  # 首字符 BOM（Excel 兼容，API §3.3 CSV 细节）
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for entry in result.items:
        writer.writerow(_entry_row(entry))
    return ExportPayload(
        media_type="text/csv; charset=utf-8",
        filename=export_filename(params.source, "csv"),
        content=buffer.getvalue(),
        row_count=result.total,
    )


def export(params: LogExportParams) -> ExportPayload:
    """导出为 CSV 或 JSON（**同步入口**：文件/内存类源；DB 类源请用 :func:`export_async`）.

    Raises:
        BaseError: 留痕通道不可用（``BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE``，503）；命中数
            超上限（``PARAM_EXPORT_LIMIT_EXCEEDED`` = ``PARAM_400``，400）。
    """
    _assert_audit_channel_available()
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    return _render_export(adapter.fetch(filters), params)


async def export_async(params: LogExportParams) -> ExportPayload:
    """导出为 CSV / JSON（HTTP 端点入口）.

    执行面（INT-146-001）：取数按适配器执行面选择（DB 源主循环 async / 文件源下沉线程池）；
    渲染（≤10000 行的 CSV/JSON 序列化）同样下沉线程池，避免阻塞事件循环。

    Raises:
        BaseError: 留痕通道不可用（``BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE``，503）；命中数
            超上限（``PARAM_EXPORT_LIMIT_EXCEEDED`` = ``PARAM_400``，400）。
    """
    _assert_audit_channel_available()
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    result = await _fetch_async(adapter, filters)
    return await asyncio.to_thread(_render_export, result, params)


def build_facets_presets() -> dict[str, dict[str, list[str]]]:
    """供前端渲染筛选器的候选枚举（维度 → 可选值）。"""
    return {
        "source": {"values": list(LOG_SOURCES)},
        "module": {"values": list(LOG_MODULES)},
        "operation": {"values": list(LOG_OPERATIONS)},
        "result": {"values": list(LOG_RESULTS)},
    }
