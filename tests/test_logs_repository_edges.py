"""logs/repository 覆盖率边角补测（覆盖率治理 v1.8.0）.

以**真实四仓日志目录布局**（``logs/openbase`` + ``dps``/``openrag``/``openmemory``/``openllm``）
驱动 L1 分片推导、廉价预筛否定分支、测试记录过滤、四仓日分片筛选与坏行/空行跳过。
"""

from __future__ import annotations

from datetime import date, timedelta

from openbase.modules.logs.repository import (
    Filters,
    L1FileAdapter,
    RepoLogAdapter,
)
from openbase.modules.logs.repository import TestRecordAdapter as RecordAdapter

_TODAY = date.today()


def _four_repo_layout(tmp_path):
    """真实四仓 + L1 目录布局（仅创建目录，文件由用例按需写入）."""
    root = tmp_path / "logs"
    for svc in ("openbase", "dps", "openrag", "openmemory", "openllm"):
        (root / svc).mkdir(parents=True)
    return root


def test_l1_slice_documents_skips_unsafe_candidates(tmp_path, monkeypatch):
    root = _four_repo_layout(tmp_path)
    (root / "openbase" / f"openbase-{_TODAY:%Y%m%d}.jsonl").write_text(
        '{"ts": "2026-11-14T10:00:00+00:00"}\n', encoding="utf-8"
    )
    adapter = L1FileAdapter(log_root=root)
    assert len(adapter._slice_documents(Filters(source="l1"))) == 1

    monkeypatch.setattr(adapter, "_safe_path", lambda base, target: False)
    assert adapter._slice_documents(Filters(source="l1")) == []


def test_l1_prefilter_negative_branches():
    adapter = L1FileAdapter(log_root=".")
    raw = '{"path": "/api/v1/auth/login", "operator_id": "bob"}'

    # 操作人取值含空格 → 放弃该维度预筛（all False）
    assert adapter._prefilter_hits(
        raw, Filters(source="l1", q="bob", operators=["bob", "bad value"])
    )

    # q 已建立 lowered → 操作人分支复用，不再重复小写化
    assert adapter._prefilter_hits(raw, Filters(source="l1", q="auth", operators=["bob"]))

    # 操作人任一命中 → 不否定
    assert adapter._prefilter_hits(raw, Filters(source="l1", operators=["alice", "bob"]))

    # modules 含 other → 不启用前缀预筛
    assert adapter._prefilter_hits(raw, Filters(source="l1", modules=["other"]))


def test_test_record_fetch_skips_non_matching(monkeypatch):
    adapter = RecordAdapter()
    monkeypatch.setattr(
        adapter,
        "_records",
        lambda: [
            {
                "created_at": "2026-11-14T10:00:00+00:00",
                "request_id": "req-tr-1",
                "title": "登录用例",
                "result": "passed",
                "run_id": "run-1",
            }
        ],
    )
    assert adapter.fetch(Filters(source="test_record", run_id="run-1")).total == 1
    assert adapter.fetch(Filters(source="test_record", q="absent-token")).total == 0


def test_repo_day_files_filters_by_date_and_name(tmp_path):
    root = _four_repo_layout(tmp_path)
    svc_dir = root / "dps"
    current = svc_dir / f"dps-{_TODAY:%Y%m%d}.log"
    current.write_text("2026-11-14T10:00:00Z INFO started\n", encoding="utf-8")
    stale = svc_dir / f"dps-{(date.today() - timedelta(days=30)):%Y%m%d}.log"
    stale.write_text("2026-10-01T10:00:00Z INFO old\n", encoding="utf-8")
    (svc_dir / "dps-99999999.log").write_text("bad date name\n", encoding="utf-8")
    (svc_dir / "other-20260101.log").write_text("foreign svc\n", encoding="utf-8")

    adapter = RepoLogAdapter(log_root=root)
    files = adapter._day_files(svc_dir, Filters(source="repo_log"))
    assert files == [current]


def test_repo_parse_line_invalid_json_returns_none():
    adapter = RepoLogAdapter(log_root=".")
    assert adapter._parse_line("dps", '{"broken": ') is None
    assert adapter._parse_line("dps", "{not-json}") is None


def test_repo_fetch_skips_blank_and_non_matching_lines(tmp_path):
    root = _four_repo_layout(tmp_path)
    log_file = root / "dps" / f"dps-{_TODAY:%Y%m%d}.log"
    log_file.write_text(
        "\n"
        "2026-11-14T10:00:00Z INFO service started\n"
        '2026-11-14 10:01:00 1.2.3.4 - - "GET /api/v1/dps-proxy/health HTTP/1.1" 200\n',
        encoding="utf-8",
    )
    adapter = RepoLogAdapter(log_root=root)

    matched = adapter.fetch(Filters(source="repo_log", modules=["dps"], q="dps-proxy"))
    assert matched.total == 1

    # 全部不命中 → 仅解析不收集（覆盖预筛/匹配否定分支）
    empty = adapter.fetch(Filters(source="repo_log", modules=["dps"], q="absent-token"))
    assert empty.total == 0
