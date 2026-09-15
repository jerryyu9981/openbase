"""日志中心 Service 层（ADR-146-01）。

负责查询参数归一化、跨适配器编排、分页切片与导出（CSV/JSON）。
排序口径由适配器统一（ts 倒序 + 稳定次序，见 repository.BaseRepository._slice），
本层仅做分页与汇总，不重复实现过滤逻辑。

导出契约（《OpenBase-API接口设计文档-v1.4.6》§3.3 / 需求 §4.6）：
文件名 ``logs-<source>-<ts>.<ext>``、CSV 带 ``\\ufeff`` BOM、命中 > 10000 → 400
``PARAM_400``、每次成功导出写 1 条 ``audit_logs(action="log.export")`` 留痕
（不记录检索关键字与导出内容，见 ADR-146-04 与非功能 §3）。
"""

from __future__ import annotations

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
from openbase.modules.logs.repository import Filters, LogEntry, get_adapter
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


def _parse_datetime(value: str | None) -> datetime | None:
    """解析 ``from`` / ``to`` 时间边界；非法输入返回 None（交由上层参数校验兜底）。"""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _build_filters(params: LogQueryParams, limit: int) -> Filters:
    """把请求参数归一到供适配器消费的 Filters。"""
    return Filters(
        source=params.source,
        modules=list(params.module),
        operations=list(params.operation),
        results=list(params.result),
        operators=list(params.operator),
        q=(params.q or "").strip() if params.q else None,
        from_=_parse_datetime(params.from_),
        to=_parse_datetime(params.to),
        case_id=params.case_id,
        run_id=params.run_id,
        step_id=params.step_id,
        limit=limit,
    )


def _pagination(
    page: int, page_size: int
) -> tuple[int, int]:
    start = (page - 1) * page_size
    return start, start + page_size


def search(params: LogSearchParams) -> dict[str, Any]:
    """单源检索：适配器取满足条件的已排序集合 → 分页切片 + 截断标注。"""
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    result = adapter.fetch(filters)
    start, end = _pagination(params.page, params.page_size)
    items = result.items[start:end]
    return {
        "items": [item.model_dump() for item in items],
        "total": result.total,
        "page": params.page,
        "page_size": params.page_size,
        "truncated": result.truncated,
    }


def facets(params: LogQueryParams) -> dict[str, dict[str, int]]:
    """单源维度聚合：module / operation / result / operator。"""
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    agg = adapter.facets(filters)
    return {dimension: dict(counter) for dimension, counter in agg.items()}


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


def export(params: LogExportParams) -> ExportPayload:
    """导出为 CSV 或 JSON（全集有序，受导出上限与适配器扫描上限双重约束）.

    Raises:
        BaseError: 留痕通道不可用（``BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE``，503）；命中数
            超上限（``PARAM_EXPORT_LIMIT_EXCEEDED`` = ``PARAM_400``，400，detail 含
            ``{matched, limit}``）。

    Returns:
        :class:`ExportPayload`（媒体类型 / 附件名 / 内容 / 导出条数）。
    """
    _assert_audit_channel_available()
    adapter = get_adapter(params.source)
    filters = _build_filters(params, limit=adapter.limits["max_lines"])
    result = adapter.fetch(filters)

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


def build_facets_presets() -> dict[str, dict[str, list[str]]]:
    """供前端渲染筛选器的候选枚举（维度 → 可选值）。"""
    return {
        "source": {"values": list(LOG_SOURCES)},
        "module": {"values": list(LOG_MODULES)},
        "operation": {"values": list(LOG_OPERATIONS)},
        "result": {"values": list(LOG_RESULTS)},
    }
