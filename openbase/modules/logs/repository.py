"""日志中心 Repository 适配器层（ADR-146-01 / ADR-146-06）.

四个数据源（L1 文件 / 审计库 / 测试记录 / 四仓 repo_log）实现**同一协议**，
使上层 Service 无需分支判断源形态：

- ``fetch(filters, *, limit, offset) -> (items, total, truncated)``
- ``facets(filters) -> {dimension: Counter}``

排序与过滤在适配器内完成（ts 倒序 + 稳定次序）；分类派生统一走 ``derivation``。
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from openbase.core.mask import mask_sensitive
from openbase.modules.logs.derivation import (
    REPO_LOG_SOURCES,
    derive_module_from_path,
    derive_operation,
    derive_result_from_status,
    derive_result_from_test,
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

# 脱敏 allowlist：result/level 等非敏感键保留，summary 内含敏感键会被 mask_sensitive 遮蔽
MASK_ALLOWLIST: tuple[str, ...] = (
    "result",
    "level",
    "status_code",
    "duration_ms",
    "method",
    "path",
)


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


class BaseRepository:
    """共享的 filter 匹配与 facets 归集（按同口径供各适配器复用）。"""

    def _entry_matches(self, entry: LogEntry, filters: Filters) -> bool:
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

    def _matches(self, entry: LogEntry, filters: Filters) -> bool:
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


class L1FileAdapter(BaseRepository):
    """读取 L1 结构化日志 ``logs/openbase/openbase-YYYYMMDD.jsonl``.

    三重路径校验（AC-146-07-3）：时间窗推导文件名（非用户拼接）+ 白名单正则 + Path.resolve 确认在目录内。
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
        matched: list[LogEntry] = []
        for path in self._slice_documents(filters):
            for raw in self._safe_read_lines(path):
                if len(matched) >= filters.limit:
                    break
                if not raw.strip():
                    continue
                data = json.loads(raw) if _looks_json(raw) else None
                if data is None:
                    continue
                entry = self._parse_entry_from_data(data)
                if entry is not None and self._matches(entry, filters):
                    matched.append(entry)
        return self._slice(matched, filters)

    def _parse_entry_from_data(self, data: dict[str, Any]) -> LogEntry | None:
        if not isinstance(data, dict):
            return None
        method = data.get("method")
        status = data.get("status_code")
        summary = {k: data[k] for k in ("resp_status", "resp_headers", "upstream_status") if k in data}
        return LogEntry(
            ts=_iso(data.get("ts")),
            source="l1_file",
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
            summary=_mask_props(summary) if summary else None,
        )

    def _safe_read_lines(self, path: Path) -> list[str]:
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return []

    def facets(self, filters: Filters) -> dict[str, Counter]:
        entries = self._fetch_all(filters)
        return self._aggregate(entries)

    def _fetch_all(self, filters: Filters) -> list[LogEntry]:
        matched: list[LogEntry] = []
        for path in self._slice_documents(filters):
            for raw in self._safe_read_lines(path):
                if not raw.strip():
                    continue
                data = json.loads(raw) if _looks_json(raw) else None
                if data is None:
                    continue
                entry = self._parse_entry_from_data(data)
                if entry is not None and self._matches(entry, filters):
                    matched.append(entry)
        return matched


class AuditDbAdapter(BaseRepository):
    """查询 ``audit_logs`` 表（SQL 参数化，detail JSON 取值，COUNT + 分页两步）。"""

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

    async def _fetch_async(self, filters: Filters) -> list:
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

    def fetch(self, filters: Filters) -> FetchResult:
        try:
            import asyncio

            rows = asyncio.run(self._fetch_async(filters))
        except Exception:  # noqa: BLE001 -> 单源降级
            logger.warning("audit_db source fetch degraded", extra={"exc": "AuditDbAdapter"})
            return FetchResult(items=[], total=0, truncated=False)
        entries = [self._to_entry(r) for r in rows]
        return self._slice(entries, filters)

    def facets(self, filters: Filters) -> dict[str, Counter]:
        fetch = self.fetch(filters)
        return self._aggregate(fetch.items)


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
        ts = timestamps[0] if timestamps else None
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

    def fetch(self, filters: Filters) -> FetchResult:
        matched: list[LogEntry] = []
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
                    entry = self._parse_line(svc, line)
                    if entry is not None and self._matches(entry, filters):
                        svc_counter += 1
                        matched.append(entry)
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
