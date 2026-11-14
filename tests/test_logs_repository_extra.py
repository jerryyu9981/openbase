"""日志中心 repository 分支补测（覆盖率治理：logs/repository.py）.

补齐范围：
- 时间/时间戳归一（``_iso`` / ``_parse_ts``）与过滤匹配的否定分支；
- L1 分片时间窗推导、路径校验 OSError、分片读取异常、文本预筛、堆收口；
- 审计库适配器的 SQL 条件组装、异步失败透传、同步入口显式失败；
- 测试记录适配器的降级、run/case/step 过滤与 items 截断；
- 四仓采集适配器的 svc 目录识别、日分片筛选、JSON/纯文本解析、丢弃告警与扫描上限。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.logs.repository import (
    AuditDbAdapter,
    Filters,
    L1FileAdapter,
    RepoLogAdapter,
    _iso,
    _parse_ts,
    _safe_int,
    _ScannedEntry,
)
from openbase.modules.logs.repository import (
    TestRecordAdapter as RecordAdapter,
)
from openbase.modules.testing import TestRecordService

_NOW = datetime.now(timezone.utc)
# 与 Filters 的时间窗（UTC）同口径，避免本地/UTC 跨零点导致日分片选择漂移
_TODAY = _NOW.strftime("%Y%m%d")


def _entry(**overrides) -> SimpleNamespace:
    base = {
        "ts": "2026-09-15T10:00:00+00:00",
        "module": "identity",
        "operation": "auth_login",
        "result": "success",
        "request_id": "req-1",
        "path": "/api/v1/auth/login",
        "operator_id": "u1",
        "ip_address": "127.0.0.1",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _scanned(sequence: int, ts: str) -> _ScannedEntry:
    return _ScannedEntry(
        ts=ts,
        module="other",
        operation="other",
        result="unknown",
        request_id=None,
        method=None,
        path=None,
        status_code=None,
        duration_ms=None,
        operator_id=None,
        tenant_id=None,
        ip_address=None,
        case_id=None,
        step_id=None,
        run_id=None,
        action=None,
        summary_props=None,
        sequence=sequence,
    )


# ---- 时间归一与安全整数 ----


def test_iso_and_parse_ts_edges() -> None:
    assert _iso(None) is None
    assert _iso("not-a-timestamp") == "not-a-timestamp"
    assert _iso("2026-09-15T10:00:00").endswith("+00:00")

    assert _parse_ts(None) is None
    assert _parse_ts("bad") is None
    parsed = _parse_ts("2026-09-15T10:00:00")
    assert parsed is not None and parsed.tzinfo is not None

    assert _safe_int(None) is None
    assert _safe_int("abc") is None
    assert _safe_int("12") == 12


# ---- BaseRepository 过滤 ----


def test_entry_matches_negative_paths() -> None:
    adapter = L1FileAdapter(log_root=Path("."))
    entry = _entry()

    assert adapter._entry_matches(entry, Filters(source="x", modules=["rag"])) is False
    assert adapter._entry_matches(entry, Filters(source="x", operations=["proxy"])) is False
    assert adapter._entry_matches(entry, Filters(source="x", results=["failed"])) is False
    assert adapter._entry_matches(entry, Filters(source="x", operators=["someone"])) is False
    assert adapter._entry_matches(entry, Filters(source="x", q="absent-keyword")) is False
    # 操作人命中（operator_id 或 request_id）→ 通过
    assert adapter._entry_matches(entry, Filters(source="x", operators=["req-1"])) is True


# ---- L1 适配器 ----


def _l1_root(tmp_path: Path, name: str | None = None) -> Path:
    base = tmp_path / "logs" / "openbase"
    base.mkdir(parents=True, exist_ok=True)
    target = base / (name or f"openbase-{_TODAY}.jsonl")
    target.write_text(
        json.dumps(
            {
                "ts": "2026-09-15T10:00:00+00:00",
                "path": "/api/v1/auth/login",
                "method": "POST",
                "status_code": 200,
                "actor": "u1",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path / "logs"


def test_l1_slice_documents_to_only_and_timestamped_glob(tmp_path: Path) -> None:
    root = _l1_root(tmp_path)
    # 历史时间戳命名文件：白名单只认 openbase-YYYYMMDD.jsonl，不被纳入
    (root / "openbase" / f"openbase-{_TODAY}-120000.jsonl").write_text("{}", encoding="utf-8")

    adapter = L1FileAdapter(log_root=root)
    # from_ 为空、to 有值 → start 取 min(to.date, today)
    documents = adapter._slice_documents(Filters(source="l1_file", to=_NOW))
    assert [path.name for path in documents] == [f"openbase-{_TODAY}.jsonl"]


def test_l1_safe_path_and_read_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = L1FileAdapter(log_root=tmp_path)

    original_resolve = Path.resolve

    def _resolve(self: Path, *args, **kwargs):
        if self.name == "openbase-99999999.jsonl":
            raise OSError("boom")
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", _resolve)
    assert adapter._safe_path(tmp_path, tmp_path / "openbase-99999999.jsonl") is False
    monkeypatch.undo()

    # 目录被当作分片打开 → OSError，返回空迭代
    assert list(adapter._iter_raw_lines(tmp_path)) == []

    # 非法 UTF-8 字节 → UnicodeDecodeError，记录告警并中止分片
    broken = tmp_path / "broken.jsonl"
    broken.write_bytes(b"\xff\xfe\x00")
    assert list(adapter._iter_raw_lines(broken)) == []


def test_l1_prefilter_and_heap_cap(tmp_path: Path) -> None:
    adapter = L1FileAdapter(log_root=_l1_root(tmp_path))
    raw = json.dumps(
        {"ts": "2026-09-15T10:00:00+00:00", "path": "/api/v1/auth/login", "actor": "u1"}
    )
    assert adapter._prefilter_hits(raw, Filters(source="l1_file", operators=["zzz"])) is False
    assert adapter._prefilter_hits(raw, Filters(source="l1_file", modules=["rag"])) is False
    assert adapter._prefilter_hits(raw, Filters(source="l1_file", q="absent")) is False
    assert adapter._prefilter_hits(raw, Filters(source="l1_file", q="auth")) is True

    kept: list = []
    adapter._keep_candidate(kept, _scanned(1, "2026-09-15T10:00:00Z"), 1)
    adapter._keep_candidate(kept, _scanned(2, "2026-09-15T11:00:00Z"), 1)
    # 更小的键被丢弃（堆内保持最大键）
    adapter._keep_candidate(kept, _scanned(3, "2026-09-15T09:00:00Z"), 1)
    assert len(kept) == 1
    assert kept[0][1].ts == "2026-09-15T11:00:00Z"


def test_l1_scan_non_dict_and_parse_entry() -> None:
    adapter = L1FileAdapter(log_root=Path("."))
    assert adapter._scan_entry_from_data(["not", "a", "dict"]) is None
    assert adapter._parse_entry_from_data("still-not-dict") is None


# ---- 审计库适配器 ----


def test_audit_db_filters_and_explicit_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = AuditDbAdapter()
    conditions = adapter._filters_to_orm(
        Filters(source="audit_db", from_=_NOW - timedelta(days=1), to=_NOW, q="token")
    )
    assert len(conditions) == 3

    with pytest.raises(BaseError) as sync_error:
        adapter.fetch(Filters(source="audit_db"))
    assert sync_error.value.code == ErrorCode.SYS_SOURCE_UNAVAILABLE
    with pytest.raises(BaseError):
        adapter.facets(Filters(source="audit_db"))

    async def _boom(filters: Filters) -> list:
        raise BaseError(ErrorCode.SYS_SOURCE_UNAVAILABLE, "source down")

    monkeypatch.setattr(adapter, "_fetch_rows", _boom)
    with pytest.raises(BaseError):
        asyncio.run(adapter.fetch_async(Filters(source="audit_db")))


# ---- 测试记录适配器 ----


def test_test_record_adapter_filters_and_degradation(monkeypatch: pytest.MonkeyPatch) -> None:
    records = [
        {
            "id": 1,
            "title": "登录用例",
            "result": "pass",
            "run_id": "run-1",
            "case_id": "case-1",
            "step_id": 1,
            "created_at": "2026-09-15T10:00:00+00:00",
            "request_id": "req-1",
        },
        {
            "id": 2,
            "title": "代理用例",
            "result": "fail",
            "run_id": "run-2",
            "case_id": "case-2",
            "step_id": 2,
            "created_at": "2026-09-15T11:00:00+00:00",
        },
    ]
    monkeypatch.setattr(TestRecordService, "_records", records)
    adapter = RecordAdapter()
    assert len(adapter._records()) == 2

    assert adapter.fetch(Filters(source="test_record", run_id="run-1")).total == 1
    assert adapter.fetch(Filters(source="test_record", case_id="case-2")).total == 1
    assert adapter.fetch(Filters(source="test_record", step_id="999")).total == 0
    capped = adapter.fetch(Filters(source="test_record", limit=1))
    assert len(capped.items) == 1 and capped.truncated is True
    assert adapter.facets(Filters(source="test_record"))["module"]["testing"] == 2

    def _unavailable() -> list:
        raise RuntimeError("record store down")

    monkeypatch.setattr(adapter, "_records", _unavailable)
    degraded = adapter.fetch(Filters(source="test_record"))
    assert degraded.total == 0


# ---- 四仓采集适配器 ----


def _repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo-logs"
    (root / "openrag").mkdir(parents=True)
    (root / "openrag" / f"openrag-{_TODAY}.log").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-09-15T10:00:00+00:00",
                        "method": "POST",
                        "path": "/api/v1/rag-proxy/search",
                        "status": 200,
                    }
                ),
                '127.0.0.1 - - "GET /api/v1/rag-proxy/chat HTTP/1.1" 500 12',
                "vendor banner without timestamp",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root


def test_repo_log_svc_dir_and_day_file_selection(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    # 同名文件（非目录）→ 未知 svc 目录告警分支
    (root / "dps").write_text("not-a-dir", encoding="utf-8")

    adapter = RepoLogAdapter(log_root=root)
    svc_dirs = adapter._svc_dirs()
    assert "openrag" in svc_dirs
    assert "dps" not in svc_dirs

    assert RepoLogAdapter(log_root=tmp_path / "missing")._svc_dirs() == {}
    assert adapter._module_to_svc(Filters(source="repo_log", modules=["rag"])) == ["openrag"]
    assert adapter._module_to_svc(Filters(source="repo_log", modules=["other"])) == []

    svc_dir = svc_dirs["openrag"]
    (svc_dir / "notes.txt").write_text("x", encoding="utf-8")
    (svc_dir / "openrag-99999999.log").write_text("x", encoding="utf-8")
    (svc_dir / f"dps-{_TODAY}.log").write_text("x", encoding="utf-8")
    (svc_dir / "archive").mkdir()

    filters = Filters(source="repo_log", from_=_NOW - timedelta(days=2), to=_NOW)
    selected = [path.name for path in adapter._day_files(svc_dir, filters)]
    assert selected == [f"openrag-{_TODAY}.log"]


def test_repo_log_parse_line_variants() -> None:
    adapter = RepoLogAdapter(log_root=Path("."))
    assert adapter._parse_line("openrag", "   ") is None
    assert adapter._parse_line("unknown-svc", "2026-09-15T10:00:00Z x") is None
    # JSON 无时间戳 → 丢弃（不得让整源崩坏）
    assert adapter._parse_line("openrag", '{"method":"GET","path":"/x"}') is None
    structured = adapter._parse_line(
        "openrag", '{"timestamp":"2026-09-15T10:00:00Z","url":"/api/v1/rag-proxy/x","status_code":404}'
    )
    assert structured is not None and structured.result == "client_error"
    text_access = adapter._parse_line(
        "openrag", '2026-09-15T10:00:00Z 127.0.0.1 - - "GET /api/v1/rag-proxy/chat HTTP/1.1" 200 1'
    )
    assert text_access is not None and text_access.status_code == 200
    text_plain = adapter._parse_line("openrag", "2026-09-15T10:00:00Z service started")
    assert text_plain is not None and text_plain.method is None
    assert adapter._parse_line("openrag", "no timestamp here") is None


def test_repo_log_fetch_limit_warn_and_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo_root(tmp_path)
    adapter = RepoLogAdapter(log_root=root)
    filters = Filters(source="repo_log", modules=["rag"])

    capped = adapter.fetch(Filters(source="repo_log", modules=["rag"], limit=1))
    assert len(capped.items) == 1 and capped.truncated is True
    assert adapter.facets(filters)["module"]["rag"] >= 1

    adapter._warn_dropped(3, 3)  # 无丢弃 → 直接返回
    adapter._warn_dropped(5, 2)  # 丢弃 → 汇总告警

    original_read_text = Path.read_text

    def _read_text(self: Path, *args, **kwargs):
        if self.name.startswith("openrag-"):
            raise OSError("disk gone")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read_text)
    assert adapter.fetch(filters).total == 0
