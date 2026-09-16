"""日志中心 service / repository 层单元测试（ADR-146-01~04 / ADR-146-06）.

覆盖：
- L1FileAdapter：JSONL 解析、派生（module/operation/result）、时间窗+limit 截断、坏行跳过；
- L1 路径穿越防护：白名单 + resolve 校验；
- RepoLogAdapter：JSONL 优先 / 纯文本回退、svc↔module 显式映射（非同名）、未知 svc 跳过、
  脱敏、按 svc 目录独立扫描上限；
- service：search 分页/排序/截断、facets 维度计数（与列表同口径）、export CSV/JSON。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from openbase.core.errors import BaseError
from openbase.modules.logs import service as log_service
from openbase.modules.logs.repository import (
    L1FileAdapter,
    RepoLogAdapter,
    get_adapter,
)
from openbase.modules.logs.schemas import (
    LogExportParams,
    LogSearchParams,
)

# 日期动态生成：适配器时间窗按 OS 当日倒推，文件名须落在窗内
TODAY = datetime.now().strftime("%Y%m%d")

L1_LINES = [
    '{"ts":"2026-09-15T10:00:00+00:00","path":"/api/v1/auth/login","method":"POST","status_code":200,"request_id":"req-1","actor":"u1"}',
    '{"ts":"2026-09-15T10:01:00+00:00","path":"/api/v1/rag-proxy/chat","method":"POST","status_code":500,"request_id":"req-2"}',
    '{"ts":"2026-09-15T10:02:00+00:00","path":"/api/v1/dps-proxy/forward","method":"GET","status_code":200,"request_id":"req-3"}',
    'not-a-json-line',  # 坏行：跳过不中断
]


@pytest.fixture
def l1_root(tmp_path: Path) -> Path:
    """构造 L1 日志目录：logs/openbase/openbase-YYYYMMDD.jsonl. """
    base = tmp_path / "logs" / "openbase"
    base.mkdir(parents=True, exist_ok=True)
    (base / f"openbase-{TODAY}.jsonl").write_text("\n".join(L1_LINES), encoding="utf-8")
    return tmp_path / "logs"


# ---- L1FileAdapter ----

def test_l1_fetch_parses_derives_sorts() -> None:
    adapter = L1FileAdapter(log_root=l1_root_factory())
    filters = _filters(source="l1_file")
    result = adapter.fetch(filters)
    # 坏行跳过 → 3 条；ts 倒序
    assert result.total == 3
    assert [e.request_id for e in result.items] == ["req-3", "req-2", "req-1"]
    # 派生：module / operation / result
    by_req = {e.request_id: e for e in result.items}
    assert by_req["req-1"].module == "identity"
    assert by_req["req-1"].operation == "auth_login"
    assert by_req["req-1"].result == "success"
    assert by_req["req-2"].module == "rag"
    assert by_req["req-2"].result == "server_error"
    assert by_req["req-3"].module == "dps"
    assert by_req["req-3"].operation == "proxy"  # path 含 -proxy → proxy（API §4.2）


def l1_root_factory():
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())
    base = tmp / "logs" / "openbase"
    base.mkdir(parents=True, exist_ok=True)
    (base / f"openbase-{TODAY}.jsonl").write_text("\n".join(L1_LINES), encoding="utf-8")
    return tmp / "logs"


def _filters(source: str, **kw) -> object:
    from openbase.modules.logs.repository import Filters

    return Filters(source=source, **kw)


def test_l1_fetch_module_filter() -> None:
    root = l1_root_factory()
    adapter = L1FileAdapter(log_root=root)
    result = adapter.fetch(_filters(source="l1_file", modules=["rag"]))
    assert result.total == 1
    assert result.items[0].request_id == "req-2"


def test_l1_fetch_limit_truncated() -> None:
    root = l1_root_factory()
    adapter = L1FileAdapter(log_root=root)
    result = adapter.fetch(_filters(source="l1_file", limit=2))
    assert result.truncated is True
    assert result.total == 2  # 触顶截断（仅返回扫描集内已匹配条数）


def test_l1_path_traversal_blocked(tmp_path: Path) -> None:
    """非 `openbase-YYYYMMDD.jsonl` 命名的文件不被扫描（文件名白名单防路径穿越）. """
    base = tmp_path / "logs" / "openbase"
    base.mkdir(parents=True, exist_ok=True)
    # 同目录下放置白名单格式外文件（内容正常），不应被纳入
    (base / f"evil-{TODAY}.jsonl").write_text(L1_LINES[0], encoding="utf-8")
    # 白名单格式文件才能被扫描
    (base / f"openbase-{TODAY}.jsonl").write_text(L1_LINES[1], encoding="utf-8")
    adapter = L1FileAdapter(log_root=tmp_path / "logs")
    result = adapter.fetch(_filters(source="l1_file"))
    assert result.total == 1
    assert result.items[0].request_id == "req-2"  # 仅命中白名单文件


# ---- RepoLogAdapter ----

def test_repolog_jsonl_and_text_fallback(tmp_path: Path) -> None:
    """JSONL 优先 + 纯文本访问日志回退；svc openrag→module rag（非同名）. """
    svc_dir = tmp_path / "logs" / "openrag"
    svc_dir.mkdir(parents=True, exist_ok=True)
    json_line = (
        '{"ts":"2026-09-15T11:00:00+00:00","method":"POST",'
        '"path":"/v1/chat/completions","status":200,"request_id":"rag-r1","token":"SECRET"}'
    )
    (svc_dir / f"openrag-{TODAY}.log").write_text(
        json_line + "\n" + '2026-09-15T11:01:00+00:00 10.0.0.1 - - "GET /v1/models HTTP/1.1" 200 -'
        , encoding="utf-8"
    )
    adapter = RepoLogAdapter(log_root=tmp_path / "logs")
    result = adapter.fetch(_filters(source="repo_log"))
    assert result.total == 2
    by_path = {e.path: e for e in result.items}
    rag_json = by_path.get("/v1/chat/completions")
    assert rag_json is not None
    assert rag_json.module == "rag"  # openrag→rag 显式映射
    assert rag_json.source == "repo_log"
    assert rag_json.request_id == "rag-r1"
    assert rag_json.result == "success"
    text = by_path.get("/v1/models")
    assert text is not None
    assert text.module == "rag"
    assert text.operation == "read"
    assert text.result == "success"


def test_repolog_unknown_svc_skipped(tmp_path: Path) -> None:
    """未知 svc 目录不纳入检索（即使有同名校名文件）. """
    svc_dir = tmp_path / "logs" / "mystery"
    svc_dir.mkdir(parents=True, exist_ok=True)
    (svc_dir / f"mystery-{TODAY}.log").write_text(
        '{"ts":"2026-09-15T11:00:00+00:00","path":"/x","method":"GET","status":200}',
        encoding="utf-8",
    )
    adapter = RepoLogAdapter(log_root=tmp_path / "logs")
    result = adapter.fetch(_filters(source="repo_log"))
    assert result.total == 0


def test_repolog_sensitive_masked(tmp_path: Path) -> None:
    """summary 中 event 内的 token/api_key 敏感键被脱敏遮蔽. """
    svc_dir = tmp_path / "logs" / "dps"
    svc_dir.mkdir(parents=True, exist_ok=True)
    (svc_dir / f"dps-{TODAY}.log").write_text(
        '{"ts":"2026-09-15T11:00:00+00:00","path":"/api/x","method":"POST",'
        '"status":200,"request_id":"dps-1","event":{"token":"abc123","api_key":"k"}}',
        encoding="utf-8",
    )
    adapter = RepoLogAdapter(log_root=tmp_path / "logs")
    result = adapter.fetch(_filters(source="repo_log"))
    summary = result.items[0].summary
    assert summary is not None
    assert summary["event"]["token"] == "***"
    assert summary["event"]["api_key"] == "***"


def test_repolog_text_line_without_timestamp_skipped(tmp_path: Path) -> None:
    """DEF-BE-146-001：纯文本无时间戳行（服务横幅 / 堆栈续行）跳过，不得使整源崩坏.

    现场复现：四仓采集日志 ``logs/<svc>/`` 由编排器按 stdout 原样落盘，含
    ``INFO: Application startup complete.`` 一类无时间戳行 → 旧实现构造
    ``LogEntry(ts=None)`` 触发 pydantic 校验错误 → 接口 500。
    """
    svc_dir = tmp_path / "logs" / "openllm"
    svc_dir.mkdir(parents=True, exist_ok=True)
    (svc_dir / f"openllm-{TODAY}.log").write_text(
        "\n".join(
            [
                "INFO:     Application startup complete.",  # 无时间戳：厂商横幅
                '2026-09-15T11:01:00+00:00 10.0.0.1 - - "GET /v1/models HTTP/1.1" 200 -',
                "    at module.exports (jsdom/browser/not-implemented.js:9:17)",  # 无时间戳：堆栈续行
            ]
        ),
        encoding="utf-8",
    )
    adapter = RepoLogAdapter(log_root=tmp_path / "logs")
    result = adapter.fetch(_filters(source="repo_log"))
    assert result.total == 1  # 仅保留可解析时间戳的行
    assert result.items[0].path == "/v1/models"
    assert isinstance(result.items[0].ts, str) and result.items[0].ts


def test_repolog_json_without_timestamp_skipped(tmp_path: Path) -> None:
    """DEF-BE-146-001：JSON 行缺 ts/timestamp/time 且无行首时间戳时跳过（同一容错口径）."""
    svc_dir = tmp_path / "logs" / "dps"
    svc_dir.mkdir(parents=True, exist_ok=True)
    (svc_dir / f"dps-{TODAY}.log").write_text(
        "\n".join(
            [
                '{"level":"info","message":"no ts here","method":"GET","path":"/x","status":200}',
                '{"ts":"2026-09-15T11:02:00+00:00","method":"GET","path":"/ok","status":200}',
            ]
        ),
        encoding="utf-8",
    )
    adapter = RepoLogAdapter(log_root=tmp_path / "logs")
    result = adapter.fetch(_filters(source="repo_log"))
    assert result.total == 1
    assert result.items[0].path == "/ok"


# ---- service 层 ----

def test_service_search_pagination_and_facets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """service.search：分页/总数/排序；facets 与列表同口径. """
    root = tmp_path / "logs"
    (root / "openbase").mkdir(parents=True, exist_ok=True)
    (root / "openbase" / "openbase-20260915.jsonl").write_text(
        "\n".join(L1_LINES), encoding="utf-8"
    )
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(tmp_path / "logs"))

    params = LogSearchParams(source="l1_file", page=1, page_size=2)
    body = log_service.search(params)
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["truncated"] is False
    assert [i["request_id"] for i in body["items"]] == ["req-3", "req-2"]

    page2 = log_service.search(LogSearchParams(source="l1_file", page=2, page_size=2))
    assert len(page2["items"]) == 1
    assert page2["items"][0]["request_id"] == "req-1"

    facets = log_service.facets(LogSearchParams(source="l1_file"))
    assert facets["module"]["identity"] == 1
    assert facets["module"]["rag"] == 1
    assert facets["module"]["dps"] == 1
    assert facets["result"]["success"] == 2
    assert facets["result"]["server_error"] == 1


def test_service_export_csv_and_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """导出载荷：文件名 `logs-<source>-<ts>.<ext>` + CSV BOM/表头 + JSON 全量有序.

    判据来源：《OpenBase-API接口设计文档-v1.4.6》§3.3（AC-146-06-1）。
    """
    root = tmp_path / "logs"
    (root / "openbase").mkdir(parents=True, exist_ok=True)
    (root / "openbase" / "openbase-20260915.jsonl").write_text(
        "\n".join(L1_LINES), encoding="utf-8"
    )
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(tmp_path / "logs"))
    # 留痕通道需可用（默认测试环境置 0 = 显式不可用 → fail-closed 拒绝导出）；
    # 本用例只断言导出载荷，不触 DB（留痕落库由 HTTP 层用例覆盖）。
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")

    csv_payload = log_service.export(LogExportParams(source="l1_file", format="csv"))
    assert csv_payload.media_type.startswith("text/csv")
    assert re.match(r"^logs-l1_file-\d{8}-\d{6}\.csv$", csv_payload.filename), csv_payload.filename
    assert csv_payload.row_count == 3
    assert csv_payload.content.startswith("\ufeff")  # 设计 §3.3：CSV 含 BOM
    rows = csv_payload.content.lstrip("\ufeff").strip().splitlines()
    assert rows[0] == ",".join(log_service.CSV_COLUMNS)  # 表头 = §2 字段名与顺序
    assert len(rows) == 4  # 1 表头 + 3 行（坏行跳过）

    json_payload = log_service.export(LogExportParams(source="l1_file", format="json"))
    assert json_payload.media_type == "application/json"
    assert re.match(r"^logs-l1_file-\d{8}-\d{6}\.json$", json_payload.filename), json_payload.filename
    assert json_payload.row_count == 3
    rows_json = json.loads(json_payload.content)
    assert len(rows_json) == 3
    assert rows_json[0]["request_id"] == "req-3"


def test_service_export_over_limit_raises_param_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """命中数超上限 → `BaseError(PARAM_* → 400)`，`detail={matched, limit}`（设计 §3.3/§5）.

    说明：真实 10000 阈值由 HTTP 层用例
    （``tests/test_logs_endpoints_api.py::test_export_over_limit_rejected_with_param_error``）
    以真实数据集锁定；本用例仅把常量下调以单测异常分支本身。
    """
    root = tmp_path / "logs"
    (root / "openbase").mkdir(parents=True, exist_ok=True)
    (root / "openbase" / "openbase-20260915.jsonl").write_text(
        "\n".join(L1_LINES), encoding="utf-8"
    )
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")  # 留痕通道可用（超限判定在通道校验之后）
    monkeypatch.setattr(log_service, "EXPORT_ROW_LIMIT", 2)

    with pytest.raises(BaseError) as exc_info:
        log_service.export(LogExportParams(source="l1_file", format="csv"))

    assert exc_info.value.code.value.startswith("PARAM")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == {"matched": 3, "limit": 2}


def test_get_adapter_unknown_source_raises() -> None:

    with pytest.raises(KeyError):
        get_adapter("no_such_source")


# ---- PERF-146-001：分片扫描的「廉价预筛 + 分页收口」不得改变既有语义 ----

def _write_l1_rows(root: Path, rows: list[dict]) -> None:
    directory = root / "openbase"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"openbase-{TODAY}.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8"
    )


def _bulk_rows(count: int) -> list[dict]:
    return [
        {
            "ts": f"2026-09-15T10:{index // 60:02d}:{index % 60:02d}+00:00",
            "path": "/api/v1/dps-proxy/forward",
            "method": "GET",
            "status_code": 200,
            "request_id": f"req-bulk-{index:04d}",
        }
        for index in range(count)
    ]


def test_l1_item_cap_returns_prefix_of_full_scan(tmp_path: Path) -> None:
    """分页收口（``item_cap``）返回的 items 必须是全量倒序结果的前缀，且 total 精确."""
    root = tmp_path / "logs"
    _write_l1_rows(root, _bulk_rows(8))
    adapter = L1FileAdapter(log_root=root)

    full = adapter.fetch(_filters(source="l1_file"))
    capped = adapter.fetch(_filters(source="l1_file", item_cap=3))

    assert capped.total == full.total == 8
    assert capped.truncated == full.truncated is False
    assert [entry.request_id for entry in capped.items] == [
        entry.request_id for entry in full.items[:3]
    ]


def test_l1_item_cap_keeps_truncated_semantics(tmp_path: Path) -> None:
    """扫描上限触顶（``limit``）时 ``truncated=True``，且 total 仍为扫描范围内的命中数."""
    root = tmp_path / "logs"
    _write_l1_rows(root, _bulk_rows(8))
    adapter = L1FileAdapter(log_root=root)

    result = adapter.fetch(_filters(source="l1_file", limit=3, item_cap=1))

    assert result.total == 3  # 触顶截断：仅返回扫描集内已匹配条数（既有口径）
    assert result.truncated is True
    assert len(result.items) == 1
    assert result.items[0].request_id == "req-bulk-0007"  # ts 倒序首条（最新）


def test_l1_search_pages_match_full_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """经 service.search（分页收口开启）逐页结果与全量扫描切片一致（跨页不重不漏）."""
    root = tmp_path / "logs"
    _write_l1_rows(root, _bulk_rows(8))
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(root))
    adapter = L1FileAdapter(log_root=root)
    full_scan = adapter.fetch(_filters(source="l1_file"))
    expected = [entry.request_id for entry in full_scan.items]

    observed: list[str] = []
    for page in (1, 2, 3):
        body = log_service.search(
            LogSearchParams(source="l1_file", page=page, page_size=3)
        )
        assert body["total"] == 8
        assert body["truncated"] is False
        observed.extend(item["request_id"] for item in body["items"])

    assert observed == expected


def test_l1_search_keyword_with_non_simple_chars_still_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """含 JSON 转义字符的关键字（如引号）不得被廉价预筛误杀（回退全量解析）."""
    root = tmp_path / "logs"
    _write_l1_rows(
        root,
        [
            {
                "ts": "2026-09-15T10:00:00+00:00",
                "path": '/api/v1/dps-proxy/forward?q="a"',
                "method": "GET",
                "status_code": 200,
                "request_id": "req-quoted-1",
            }
        ],
    )
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(root))

    body = log_service.search(LogSearchParams(source="l1_file", q='"a"'))

    assert body["total"] == 1
    assert body["items"][0]["request_id"] == "req-quoted-1"


# ---- INT-146-001：audit_db 源的同步入口必须显式失败（不静默、不跨事件循环复用）----


def test_audit_db_sync_fetch_path_rejected_with_sys_503() -> None:
    """同步取数入口（工作线程内自建事件循环复用进程级连接池）→ 显式 503，不静默返回空集."""
    from openbase.core.errors import ErrorCode
    from openbase.modules.logs.repository import AuditDbAdapter

    adapter = AuditDbAdapter()
    with pytest.raises(BaseError) as exc_info:
        adapter.fetch(_filters(source="audit_db"))

    assert exc_info.value.code is ErrorCode.SYS_SOURCE_UNAVAILABLE
    assert exc_info.value.code.value == "SYS_503"
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {"source": "audit_db"}
