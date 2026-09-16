"""日志中心 Repository 适配器层（ADR-146-01 / ADR-146-06）.

四个数据源（L1 文件 / 审计库 / 测试记录 / 四仓 repo_log）实现**同一协议**，
使上层 Service 无需分支判断源形态：

- ``fetch(filters, *, limit, offset) -> (items, total, truncated)``
- ``facets(filters) -> {dimension: Counter}``

排序与过滤在适配器内完成（ts 倒序 + 稳定次序）；分类派生统一走 ``derivation``。

两类源的执行面（INT-146-001）：
- **文件/内存类源**（``l1_file`` / ``repo_log`` / ``test_record``）→ 同步扫描，由 Service 经
  ``asyncio.to_thread`` 下沉线程池（阻塞 I/O 不占用事件循环）；
- **DB 类源**（``audit_db``）→ 只能由主事件循环执行 ``fetch_async``（``async_source=True``）；
  进程级 async 连接池不可跨事件循环复用，同步入口显式 ``SYS_503`` 而非静默降级。
"""

from __future__ import annotations

import heapq
import json
import logging
import os
import re
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.mask import mask_sensitive
from openbase.modules.logs.derivation import (
    REPO_LOG_SOURCES,
    derive_module_from_path,
    derive_operation,
    derive_result_from_status,
    derive_result_from_test,
    module_path_prefixes,
    module_to_svc_dir,
    svc_dir_to_module,
)
from openbase.modules.logs.schemas import (
    LogEntry,
    LogModule,
    LogOperation,
    LogResult,
)

logger = logging.getLogger("openbase.logs")


def _default_log_root() -> Path:
    """日志根目录：每次调用实时读 ``OPENBASE_LOG_DIR``，便于测试注入与配置切换（不缓存）。"""
    return Path(os.getenv("OPENBASE_LOG_DIR", "logs")).resolve()

# 文件名白名单（防路径穿越，AC-146-07-3）：openbase-YYYYMMDD.jsonl
_L1_NAME_RE = re.compile(r"^openbase-\d{8}\.jsonl$")
# 四仓采集文件名（orchestrator C-6 输出）：<svc>-YYYYMMDD.log / .err.log / -HHmmss.log
_REPO_NAME_RE = re.compile(
    r"^(?P<svc>[a-zA-Z][a-zA-Z0-9_-]*)-(?P<date>\d{8})(?:-\d{6})?(?:\.err)?\.(?:jsonl|log)$"
)
_TAG_RE = re.compile(r"\[[^]]*\]|\s+")
_ACCESS_RE = re.compile(
    r"(?P<ip>[\d.:]+)\s+-\s+-\s+\"(?P<method>[A-Z]+)\s+(?P<path>\S+)[^\"]*\".*?(?P<code>\d{3})"
)
# 可用作**原始文本预筛**的过滤值字符集：这些字符不会被 JSON 序列化转义，
# 故「原文包含该值」与「解析后取值包含该值」等价（预筛只做保守的否定判定）。
_RAW_FILTER_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:/@+\-]+$")

# 脱敏 allowlist：result/level 等非敏感键保留，summary 内含敏感键会被 mask_sensitive 遮蔽
MASK_ALLOWLIST: tuple[str, ...] = (
    "result",
    "level",
    "status_code",
    "duration_ms",
    "method",
    "path",
)


def _raw_filter_token(value: str | None) -> str | None:
    """把过滤值转换为可用于原始文本预筛的形式（不适合预筛时返回 None = 放弃该维度预筛）."""
    if not value:
        return None
    return value if _RAW_FILTER_TOKEN_RE.match(value) else None


@dataclass
class Filters:
    """归一化后的查询过滤条件。"""

    source: str
    modules: list[LogModule] = field(default_factory=list)
    operations: list[LogOperation] = field(default_factory=list)
    results: list[LogResult] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    q: str | None = None
    from_: datetime | None = None
    to: datetime | None = None
    case_id: str | None = None
    run_id: str | None = None
    step_id: int | str | None = None
    limit: int = 200000
    # 分页收口（PERF-146-001）：仅返回排序前 ``item_cap`` 条（``None`` = 全量返回）。
    # ``total`` / ``truncated`` 语义**不变**（仍为扫描范围内的精确命中数与截断标注），
    # 供分页检索按「本页末尾下标」收口，避免为一个分页请求物化整片命中集。
    item_cap: int | None = None


@dataclass
class FetchResult:
    items: list[LogEntry]
    total: int
    truncated: bool


class LogRepository(Protocol):
    """适配器统一协议。"""

    def fetch(self, filters: Filters) -> FetchResult: ...

    def facets(self, filters: Filters) -> dict[str, Counter]: ...


def _iso(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(timespec="milliseconds")


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class MatchableLogRow(Protocol):
    """过滤所需的字段子集（``LogEntry`` 与 :class:`_ScannedEntry` 共同满足）.

    适配器可在**不物化 Pydantic 实体**的前提下复用同一套过滤口径（避免口径分叉）。
    """

    ts: str | None
    module: str
    operation: str
    result: str
    request_id: str | None
    path: str | None
    operator_id: str | None
    ip_address: str | None


class BaseRepository:
    """共享的 filter 匹配与 facets 归集（按同口径供各适配器复用）。"""

    #: 取数是否**必须**在主事件循环内执行（DB 类源为 True：进程级 async 连接池不可
    #: 跨事件循环复用，见 :class:`AuditDbAdapter`）；文件/内存类源为 False（同步扫描，
    #: 由 Service 经 ``asyncio.to_thread`` 下沉线程池）。
    async_source: bool = False

    def _entry_matches(self, entry: MatchableLogRow, filters: Filters) -> bool:
        if filters.modules and entry.module not in filters.modules:
            return False
        if filters.operations and entry.operation not in filters.operations:
            return False
        if filters.results and entry.result not in filters.results:
            return False
        if filters.operators and bool(
            set(filters.operators) & {entry.operator_id or "", entry.request_id or ""}
        ):
            pass
        elif filters.operators:
            return False
        if filters.q:
            haystack = " ".join(
                [
                    entry.path or "",
                    entry.request_id or "",
                    entry.operator_id or "",
                    entry.ip_address or "",
                ]
            ).lower()
            if filters.q.lower() not in haystack:
                return False
        return True

    def _time_window(self, entry_ts: str | None, filters: Filters) -> bool:
        ts = _parse_ts(entry_ts)
        if filters.from_ and (ts is None or ts < filters.from_):
            return False
        if filters.to and (ts is None or ts > filters.to):
            return False
        return True

    def _matches(self, entry: MatchableLogRow, filters: Filters) -> bool:
        return self._time_window(entry.ts, filters) and self._entry_matches(entry, filters)

    def _aggregate(
        self, entries: list[LogEntry]
    ) -> dict[str, Counter]:
        module = Counter()
        operation = Counter()
        result = Counter()
        operator = Counter()
        for entry in entries:
            module[entry.module] += 1
            operation[entry.operation] += 1
            result[entry.result] += 1
            operator[entry.operator_id or "other"] += 1
        return {
            "module": module,
            "operation": operation,
            "result": result,
            "operator": operator,
        }

    def _slice(self, entries: list[LogEntry], filters: Filters) -> FetchResult:
        """扫描上限内稳定排序 + 截断语义（ADR-146-03，禁止静默截断）。"""
        truncated = len(entries) >= filters.limit
        sorted_entries = sorted(
            entries,
            key=lambda e: (e.ts or "", e.request_id or e.source, e.path or ""),
            reverse=True,
        )
        return FetchResult(items=sorted_entries, total=len(sorted_entries), truncated=truncated)


@dataclass(slots=True)
class _ScannedEntry:
    """L1 分片扫描的轻量候选（PERF-146-001：**延迟物化** LogEntry）.

    字段与 :class:`LogEntry` 的过滤/排序相关字段逐一对应，使 ``_matches`` 与排序口径
    零分叉复用；Pydantic 校验与脱敏（``mask_sensitive``）推迟到真正对外返回时执行——
    分页请求只需「排序前 N 条」，scan 阶段不做整片物化。
    """

    ts: str | None
    module: LogModule
    operation: LogOperation
    result: LogResult
    request_id: str | None
    method: str | None
    path: str | None
    status_code: int | None
    duration_ms: int | None
    operator_id: str | None
    tenant_id: str | None
    ip_address: str | None
    case_id: str | None
    step_id: int | str | None
    run_id: str | None
    action: str | None
    summary_props: dict[str, Any] | None
    sequence: int = 0
    source: str = "l1_file"

    def heap_key(self) -> tuple[str, str, str, int]:
        """排序键（与既有 ``_slice`` 口径一致：ts → request_id → path 倒序；同键按扫描序）."""
        return (self.ts or "", self.request_id or self.source, self.path or "", -self.sequence)

    def to_log_entry(self) -> LogEntry:
        """物化为对外契约实体（此处才脱敏：summary 必经 :func:`mask_sensitive`）."""
        return LogEntry(
            ts=self.ts,
            source="l1_file",
            module=self.module,
            operation=self.operation,
            result=self.result,
            request_id=self.request_id,
            method=self.method,
            path=self.path,
            status_code=self.status_code,
            duration_ms=self.duration_ms,
            operator_id=self.operator_id,
            tenant_id=self.tenant_id,
            ip_address=self.ip_address,
            case_id=self.case_id,
            step_id=self.step_id,
            run_id=self.run_id,
            action=self.action,
            summary=_mask_props(self.summary_props) if self.summary_props else None,
        )


class L1FileAdapter(BaseRepository):
    """读取 L1 结构化日志 ``logs/openbase/openbase-YYYYMMDD.jsonl``.

    三重路径校验（AC-146-07-3）：时间窗推导文件名（非用户拼接）+ 白名单正则 + Path.resolve 确认在目录内。

    扫描实现（PERF-146-001）：
    ① **逐分片**读取（分片内按行序倒转，newest-first；上限 ``limits["max_lines"]`` 兜底）；
    ② ``json.loads`` 前做**廉价文本预筛**（关键字 / module 前缀 / 操作人；仅做保守否定判定）；
    ③ 匹配判定在轻量候选上完成，仅对需要返回的条目物化 ``LogEntry`` + 脱敏；
    ④ ``filters.item_cap`` 允许分页检索只保留「排序前 N 条」，``total`` / ``truncated`` 语义不变。
    """

    name_re: Callable[[], re.Pattern[str]] = staticmethod(lambda: _L1_NAME_RE)

    def __init__(self, log_root: Path | None = None) -> None:
        self.log_root = Path(log_root or _default_log_root()).resolve()
        self.limits = {"max_days": 2, "max_lines": 200000}

    def _slice_documents(self, filters: Filters) -> list[Path]:
        """由时间窗推导需扫描的日分片（倒序），含白名单与解析确认。"""
        today = date.today()
        max_days = self.limits["max_days"]
        start = filters.from_.date() if filters.from_ else today - timedelta(days=max_days)
        if filters.from_ is None and filters.to is not None:
            start = min(filters.to.date(), today)
        days: list[date] = []
        current = today
        while current >= start and len(days) < max_days:
            days.append(current)
            current -= timedelta(days=1)
        target_dir = self.log_root / "openbase"
        files: list[Path] = []
        for day in days:
            path = target_dir / f"openbase-{day:%Y%m%d}.jsonl"
            if not self._safe_path(target_dir, path):
                continue
            if path.exists():
                files.append(path)
            # 兼容历史时间戳命名的当日文件（openbase-YYYYMMDD-HHMMSS.jsonl）
            for candidate in target_dir.glob(f"openbase-{day:%Y%m%d}-*.jsonl"):
                if self._safe_path(target_dir, candidate):
                    files.append(candidate)
        return files

    def _safe_path(self, base: Path, target: Path) -> bool:
        try:
            resolved = target.resolve()
        except OSError:
            return False
        return resolved.is_relative_to(base.resolve()) and bool(self.name_re().match(target.name))

    def fetch(self, filters: Filters) -> FetchResult:
        """分片倒序流式扫描 → 命中计数 + 排序 + 按 ``item_cap`` 收口（禁止静默截断）."""
        item_cap = None if filters.item_cap is None else max(1, filters.item_cap)
        kept: list[tuple[tuple[str, str, str, int], _ScannedEntry]] = []
        total = 0
        for path in self._slice_documents(filters):
            for raw in self._iter_raw_lines(path):
                if total >= filters.limit:
                    break
                if not self._prefilter_hits(raw, filters):
                    continue
                data = json.loads(raw) if _looks_json(raw) else None
                if data is None:
                    continue
                candidate = self._scan_entry_from_data(data)
                if candidate is None or not self._matches(candidate, filters):
                    continue
                total += 1
                candidate.sequence = total
                self._keep_candidate(kept, candidate, item_cap)
        return FetchResult(
            items=self._materialize(kept),
            total=total,
            truncated=total >= filters.limit,
        )

    def _iter_raw_lines(self, path: Path) -> Iterator[str]:
        """读取某日分片为「新→旧」行序（去掉行尾换行与空白）.

        分片内按行序倒转：日志按时间追加、新行在文件末尾，倒转后与「分片倒序流式扫描」
        （`_slice_documents` 新分片优先）口径一致——`limit` 触顶提前 break 时命中最新一组，
        保证偶发截断不吞掉最新窗口。不可读/编码异常 → 中止该分片（不中断整体检索）。
        """
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError:
            return
        try:
            with handle:
                lines = [line.strip() for line in handle if line.strip()]
        except (OSError, UnicodeDecodeError):
            logger.warning("l1 shard read aborted", extra={"shard": path.name})
            return
        yield from reversed(lines)

    def _prefilter_hits(self, raw: str, filters: Filters) -> bool:
        """廉价字符串预筛：仅在**必然不可能命中**时返回 False（保守否定，不做正判定）.

        仅覆盖过滤条件中与「解析后取值」同形的维度（关键字 / module path 前缀 / 操作人）；
        取值含 JSON 转义字符时自动放弃该维度预筛（回退全量解析），保证不误杀。
        """
        lowered: str | None = None
        keyword = _raw_filter_token(filters.q)
        if keyword is not None:
            lowered = raw.lower()
            if keyword.lower() not in lowered:
                return False
        if filters.operators:
            operator_tokens = [_raw_filter_token(value) for value in filters.operators]
            if all(token is not None for token in operator_tokens):
                if lowered is None:
                    lowered = raw.lower()
                if not any(str(token).lower() in lowered for token in operator_tokens):
                    return False
        if filters.modules:
            prefixes = tuple(
                prefix for module in filters.modules for prefix in module_path_prefixes(module)
            )
            if prefixes and "other" not in filters.modules:
                if not any(prefix in raw for prefix in prefixes):
                    return False
        return True

    def _keep_candidate(
        self,
        kept: list[tuple[tuple[str, str, str, int], _ScannedEntry]],
        candidate: _ScannedEntry,
        item_cap: int | None,
    ) -> None:
        """维护「排序键倒序前 ``item_cap`` 条」（``None`` = 全量保留，次序由物化阶段统一排序）."""
        entry = (candidate.heap_key(), candidate)
        if item_cap is None:
            kept.append(entry)
        elif len(kept) < item_cap:
            heapq.heappush(kept, entry)
        elif entry[0] > kept[0][0]:
            heapq.heapreplace(kept, entry)

    def _materialize(
        self, kept: list[tuple[tuple[str, str, str, int], _ScannedEntry]]
    ) -> list[LogEntry]:
        """按排序键倒序物化（``total`` 已由扫描阶段精确计数，与返回条数解耦）."""
        ordered = sorted(kept, key=lambda pair: pair[0], reverse=True)
        return [candidate.to_log_entry() for _, candidate in ordered]

    def _scan_entry_from_data(self, data: Any) -> _ScannedEntry | None:
        """把单行 JSON 解析为轻量候选（不做 Pydantic 校验与脱敏）."""
        if not isinstance(data, dict):
            return None
        method = data.get("method")
        status = data.get("status_code")
        summary = {k: data[k] for k in ("resp_status", "resp_headers", "upstream_status") if k in data}
        return _ScannedEntry(
            ts=_iso(data.get("ts")),
            module=derive_module_from_path(data.get("path")),
            operation=derive_operation(method, data.get("path"), data.get("action")),
            result=derive_result_from_status(status),
            request_id=data.get("request_id"),
            method=method,
            path=data.get("path"),
            status_code=status,
            duration_ms=_safe_int(data.get("duration_ms")),
            operator_id=data.get("actor"),
            tenant_id=data.get("tenant"),
            ip_address=data.get("ip") or data.get("ip_address"),
            case_id=data.get("case_id"),
            step_id=data.get("step_id"),
            run_id=data.get("run_id"),
            action=data.get("action"),
            summary_props=summary or None,
        )

    def _parse_entry_from_data(self, data: Any) -> LogEntry | None:
        """把单行 JSON 解析为对外契约实体（候选物化，summary 必经脱敏）."""
        candidate = self._scan_entry_from_data(data)
        return None if candidate is None else candidate.to_log_entry()

    def facets(self, filters: Filters) -> dict[str, Counter]:
        return self._aggregate(self.fetch(filters).items)


class AuditDbAdapter(BaseRepository):
    """查询 ``audit_logs`` 表（SQL 参数化，detail JSON 取值，分页由 limit 收口）.

    取数**必须**在主事件循环内执行（:meth:`fetch_async`）：进程级 async 连接池
    （``core.db.session.get_session_factory``）不可跨事件循环复用——原实现在工作线程内
    ``asyncio.run()`` 复用主循环的连接池，线程内报
    ``AttributeError: 'NoneType' object has no attribute 'send'``，并反向污染主循环
    （``InterfaceError: cannot perform operation: another operation is in progress``）；
    且该异常被吞成「200 + total=0」的**静默降级**。

    当前口径（INT-146-001 / 非功能设计 §5）：
    - 正常路径 → 真实返回库内行；
    - 源不可用 → :class:`BaseError` ``SYS_503``（HTTP 503，``detail={"source":"audit_db"}``），
      不静默返回空集、不跨源兜底；
    - **同步入口显式失败**（不自行驱动事件循环），保证任何调用方都不会再踩跨循环复用。
    """

    #: DB 源取数须在主事件循环执行（见类文档）
    async_source: bool = True

    def __init__(self) -> None:
        self.limits = {"max_days": 2, "max_lines": 200000}

    def _session(self):
        from openbase.core.db.session import get_session_factory

        return get_session_factory()()

    def _filters_to_orm(self, filters: Filters):
        import sqlalchemy as sa

        from openbase.core.models import AuditLog

        conditions = []
        if filters.from_:
            conditions.append(AuditLog.created_at >= filters.from_)
        if filters.to:
            conditions.append(AuditLog.created_at <= filters.to)
        if filters.q:
            conditions.append(
                sa.or_(
                    AuditLog.request_id.ilike(f"%{filters.q}%"),
                    AuditLog.resource.ilike(f"%{filters.q}%"),
                    AuditLog.action.ilike(f"%{filters.q}%"),
                )
            )
        return conditions

    async def _fetch_rows(self, filters: Filters) -> list:
        from sqlalchemy import select

        from openbase.core.models import AuditLog

        async with self._session() as session:
            stmt = (
                select(AuditLog)
                .where(*self._filters_to_orm(filters))
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .limit(filters.limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    def _to_entry(self, row) -> LogEntry:
        detail = row.detail or {}
        status = detail.get("status_code")
        method = detail.get("method")
        path = detail.get("path")
        return LogEntry(
            ts=row.created_at.isoformat(timespec="milliseconds") if row.created_at else None,
            source="audit_db",
            module=derive_module_from_path(path) if path else "other",
            operation=derive_operation(method, path, row.action),
            result=derive_result_from_status(status) if status is not None else "unknown",
            request_id=row.request_id,
            method=method,
            path=path,
            status_code=status,
            duration_ms=_safe_int(detail.get("duration_ms")),
            operator_id=str(row.user_id) if row.user_id is not None else None,
            tenant_id=str(row.tenant_id) if row.tenant_id is not None else None,
            ip_address=row.ip,
            case_id=detail.get("case_id"),
            step_id=detail.get("step_id"),
            run_id=detail.get("run_id"),
            action=row.action,
            summary=_mask_props(detail) if detail else None,
        )

    async def fetch_async(self, filters: Filters) -> FetchResult:
        """主事件循环内取数；源不可用 → ``SYS_503``（不静默降级）.

        Raises:
            BaseError: ``SYS_SOURCE_UNAVAILABLE``（``SYS_503``，503），
                ``detail={"source": "audit_db"}``。
        """
        try:
            rows = await self._fetch_rows(filters)
        except BaseError:
            raise
        except Exception as exc:  # noqa: BLE001 - 单源不可用 → 显式 503（不静默）
            logger.warning(
                "audit_db source unavailable",
                extra={"source": "audit_db", "error": type(exc).__name__},
            )
            raise BaseError(
                ErrorCode.SYS_SOURCE_UNAVAILABLE,
                "audit_db source unavailable",
                detail={"source": "audit_db"},
            ) from exc
        return self._slice([self._to_entry(row) for row in rows], filters)

    def fetch(self, filters: Filters) -> FetchResult:
        """同步入口：显式失败（禁止在工作线程内自建事件循环复用进程级连接池）.

        Raises:
            BaseError: ``SYS_SOURCE_UNAVAILABLE``（``SYS_503``）。调用方应改用
                :meth:`fetch_async`（由 Service/Router 在主事件循环内调用）。
        """
        raise BaseError(
            ErrorCode.SYS_SOURCE_UNAVAILABLE,
            "audit_db source requires the async query path",
            detail={"source": "audit_db"},
        )

    async def facets_async(self, filters: Filters) -> dict[str, Counter]:
        return self._aggregate((await self.fetch_async(filters)).items)

    def facets(self, filters: Filters) -> dict[str, Counter]:
        """同步入口：同 :meth:`fetch`（显式失败，不静默）."""
        raise BaseError(
            ErrorCode.SYS_SOURCE_UNAVAILABLE,
            "audit_db source requires the async query path",
            detail={"source": "audit_db"},
        )


class TestRecordAdapter(BaseRepository):
    """复用既有测试记录服务（只读），按 run/case/step 检索。"""

    def __init__(self) -> None:
        self.limits = {"max_days": 2, "max_lines": 200000}

    def _records(self) -> list[dict[str, Any]]:
        from openbase.modules.testing import TestRecordService

        return list(TestRecordService._records)

    def _to_entry(self, record: dict[str, Any]) -> LogEntry:
        result_raw = record.get("result")
        return LogEntry(
            ts=record.get("created_at"),
            source="test_record",
            module="testing",
            operation="read",
            result=derive_result_from_test(result_raw),
            request_id=record.get("request_id"),
            method=None,
            path=record.get("title") or record.get("endpoint"),
            status_code=None,
            duration_ms=_safe_int(record.get("duration_ms")),
            operator_id=record.get("operator"),
            tenant_id=None,
            ip_address=None,
            case_id=record.get("case_id"),
            step_id=record.get("step_id"),
            run_id=record.get("run_id"),
            action=None,
            summary=_mask_props(
                {
                    "id": record.get("id"),
                    "title": record.get("title"),
                    "expected": record.get("expected"),
                    "observed": record.get("observed"),
                    "reason": record.get("reason"),
                }
            ),
        )

    def fetch(self, filters: Filters) -> FetchResult:
        matched: list[LogEntry] = []
        try:
            records = self._records()
        except Exception:  # noqa: BLE001
            logger.warning("test_record source fetch degraded", extra={"exc": "TestRecordAdapter"})
            records = []
        for record in records:
            if filters.run_id and record.get("run_id") != filters.run_id:
                continue
            if filters.case_id and record.get("case_id") != filters.case_id:
                continue
            if filters.step_id is not None and str(record.get("step_id")) != str(filters.step_id):
                continue
            entry = self._to_entry(record)
            if self._matches(entry, filters):
                matched.append(entry)
            if len(matched) >= filters.limit:
                break
        return self._slice(matched, filters)

    def facets(self, filters: Filters) -> dict[str, Counter]:
        return self._aggregate(self.fetch(filters).items)


class RepoLogAdapter(BaseRepository):
    """第四类源：四仓采集日志 ``logs/<svc>/<svc>-YYYYMMDD.log``（+ JSONL 优先）.

    ADR-146-06：单源 ``repo_log`` + ``module`` 维度；svc↔module 显式映射（derivation）；
    JSONL 优先 + 纯文本回退（兼容未完成结构化的仓）；扫描上限按**目标 svc 目录独立计算**；
    未知 svc 不纳入检索；上游字段统一脱敏（不得因新源放宽口径）。
    """

    def __init__(self, log_root: Path | None = None) -> None:
        self.log_root = Path(log_root or _default_log_root()).resolve()
        self.limits = {"max_days": 2, "max_lines": 200000}

    def _svc_dirs(self) -> dict[str, Path]:
        """仅纳入已知 svc 目录（未知 svc 不纳入检索并 WARN）。"""
        result: dict[str, Path] = {}
        base = self.log_root
        if not base.exists():
            return result
        for svc in REPO_LOG_SOURCES:
            path = base / svc
            if path.is_dir() and svc_dir_to_module(svc) is not None:
                result[svc] = path
            elif path.exists():
                logger.warning("repo_log unknown svc dir skipped", extra={"svc": svc, "path": str(path)})
        return result

    def _module_to_svc(self, filters: Filters) -> list[str]:
        if filters.modules:
            svcs: list[str] = []
            for module in filters.modules:
                svc = module_to_svc_dir(module)
                if svc is not None and svc in self._svc_dirs():
                    svcs.append(svc)
            return svcs
        return list(self._svc_dirs().keys())

    def _day_files(self, svc_dir: Path, filters: Filters) -> list[Path]:
        today = date.today()
        max_days = self.limits["max_days"]
        end = filters.to.date() if filters.to else today
        start = filters.from_.date() if filters.from_ else end - timedelta(days=max_days)
        candidates: list[Path] = []
        for candidate in svc_dir.iterdir():
            if not candidate.is_file():
                continue
            match = _REPO_NAME_RE.match(candidate.name)
            if not match:
                continue
            if match.group("svc") != svc_dir.name:
                continue
            try:
                file_day = datetime.strptime(match.group("date"), "%Y%m%d").date()
            except ValueError:
                continue
            if start <= file_day <= end:
                candidates.append(candidate)
        return candidates

    def _parse_line(self, svc: str, line: str) -> LogEntry | None:
        line = line.strip()
        if not line:
            return None
        module = svc_dir_to_module(svc)
        if module is None:
            return None
        timestamps: list[str] = []
        match = re.match(r"^([\d\-T:\.+Z ]{19,32})", line)
        if match:
            timestamps.append(match.group(1).strip())
        if _looks_json(line):
            try:
                data = json.loads(line)
            except ValueError:
                data = None
            if isinstance(data, dict):
                ts = _iso(data.get("ts") or data.get("timestamp") or data.get("time") or (timestamps[0] if timestamps else None))
                if ts is None:
                    # DEF-BE-146-001：无法解析时间戳的行不能进入 LogEntry（ts 为必填 str），
                    # 否则整源以容器级异常崩坏；按既有「坏行跳过」口径丢弃（由 fetch 汇总告警）。
                    return None
                method = data.get("method")
                path = data.get("path") or data.get("url")
                status = data.get("status") or data.get("status_code")
                return LogEntry(
                    ts=ts,
                    source="repo_log",
                    module=module,
                    operation=derive_operation(method, path, data.get("action") if isinstance(data.get("action"), str) else None),
                    result=derive_result_from_status(status) if status is not None else "unknown",
                    request_id=data.get("request_id") or data.get("requestId") or data.get("trace_id"),
                    method=method if method is not None and isinstance(method, str) else None,
                    path=path if path is not None and isinstance(path, str) else None,
                    status_code=status if isinstance(status, int) else None,
                    duration_ms=_safe_int(data.get("duration") or data.get("duration_ms")),
                    operator_id=data.get("operator_id") or data.get("operator"),
                    tenant_id=data.get("tenant_id"),
                    ip_address=data.get("ip") or data.get("ip_address"),
                    case_id=data.get("case_id"),
                    step_id=data.get("step_id"),
                    run_id=data.get("run_id"),
                    action=data.get("action") if isinstance(data.get("action"), str) else None,
                    summary=_mask_props(
                        {k: data[k] for k in ("level", "service", "message", "event") if k in data}
                    ),
                )
        # 纯文本回退：解析时间戳 + 接入访问日志（method/path/code）
        if not timestamps:
            # DEF-BE-146-001：厂商横幅 / 堆栈续行等无时间戳行丢弃，不得使整源崩坏。
            return None
        ts = timestamps[0]
        access = _ACCESS_RE.search(line)
        if access:
            method = access.group("method")
            path = access.group("path")
            status = _safe_int(access.group("code"))
            operation = derive_operation(method, path)
        else:
            method = path = status = None
            operation = derive_operation(None, None)
        return LogEntry(
            ts=ts,
            source="repo_log",
            module=module,
            operation=operation,
            result=derive_result_from_status(status) if status is not None else "unknown",
            request_id=None,
            method=method,
            path=path,
            status_code=status,
            duration_ms=None,
            operator_id=None,
            tenant_id=None,
            ip_address=None,
            case_id=None,
            step_id=None,
            run_id=None,
            action=None,
            summary={"raw": _mask_props({"line": line[:200]})} if line else None,
        )

    def _warn_dropped(self, scanned: int, parsed: int) -> None:
        """丢弃行汇总告警（DEF-BE-146-001 可观测性）：不静默降级，丢弃量可追溯."""
        dropped = scanned - parsed
        if dropped <= 0:
            return
        logger.warning(
            "repo_log unscannable lines dropped",
            extra={"source": "repo_log", "scanned": scanned, "parsed": parsed, "dropped": dropped},
        )

    def fetch(self, filters: Filters) -> FetchResult:
        matched: list[LogEntry] = []
        scanned = 0
        parsed = 0
        for svc in self._module_to_svc(filters):
            svc_dir = self.log_root / svc
            svc_counter = 0
            for path in sorted(self._day_files(svc_dir, filters), reverse=True):
                try:
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    lines = []
                for line in lines:
                    if svc_counter >= filters.limit:
                        break
                    if not line.strip():
                        continue
                    scanned += 1
                    entry = self._parse_line(svc, line)
                    if entry is None:
                        continue
                    parsed += 1
                    if self._matches(entry, filters):
                        svc_counter += 1
                        matched.append(entry)
        self._warn_dropped(scanned, parsed)
        return self._slice(matched, filters)

    def facets(self, filters: Filters) -> dict[str, Counter]:
        return self._aggregate(self.fetch(filters).items)


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _looks_json(line: str) -> bool:
    return line.startswith("{") and line.endswith("}")


def _mask_props(props: dict | None) -> dict | None:
    if not props:
        return props
    masked = mask_sensitive(props, allowlist=MASK_ALLOWLIST)
    return masked if isinstance(masked, dict) else props


ADAPTERS: dict[str, Callable[[], LogRepository]] = {
    "l1_file": L1FileAdapter,
    "audit_db": AuditDbAdapter,
    "test_record": TestRecordAdapter,
    "repo_log": RepoLogAdapter,
}


def get_adapter(source: str) -> LogRepository:
    factory = ADAPTERS.get(source)
    if factory is None:
        raise KeyError(f"unknown log source: {source}")
    return factory()


__all__ = [
    "ADAPTERS",
    "AuditDbAdapter",
    "Filters",
    "FetchResult",
    "L1FileAdapter",
    "LogRepository",
    "RepoLogAdapter",
    "TestRecordAdapter",
    "get_adapter",
]
