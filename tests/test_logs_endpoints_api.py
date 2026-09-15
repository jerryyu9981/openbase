"""日志中心三端点 HTTP 层覆盖（ADR-146-01 / AC-146-06）.

覆盖面（此前仅有 service/repository 单测，无 HTTP 层断言）：

- 正常路径：``GET /api/v1/logs/search``（分页 / 关键字 / 时间窗各 ≥1 例）、
  ``GET /api/v1/logs/facets``（维度计数与列表同口径）、
  ``GET /api/v1/logs/export``（CSV 附件 / JSON 两种格式）；
- 权限红线：无令牌 → 401（AuthMiddleware 门禁）；令牌无 ``log:read`` → 403。

导出判据（BL-146-06 / AC-146-06-1~4，逐条取自
《OpenBase-API接口设计文档-v1.4.6》§3.3 与《OpenBase-需求追溯矩阵-v1.4.6》原文）：

- AC-146-06-1（可导出且字段与列表一致）：两种 ``format`` 的
  ``Content-Disposition: attachment; filename="logs-<source>-<ts>.<ext>"``、
  CSV ``text/csv; charset=utf-8`` + ``\\ufeff`` BOM + §2 表头、``summary`` 紧凑 JSON；
- AC-146-06-2（超限）：命中 > 10000 → 400 ``PARAM_400``，``detail={matched, limit}``；
- AC-146-06-3（脱敏红线）：导出物无明文敏感值；
- AC-146-06-4（留痕）：每次导出落 1 条 ``audit_logs(action="log.export")``，
  ``detail={actor, source, filters, row_count, format}``，且**不含检索关键字**。

环境隔离：日志源为 ``tmp_path`` 构造的 L1 文件（``OPENBASE_LOG_DIR`` 注入），
留痕写入走「记录型假会话」注入（``openbase.core.db.session.get_session_factory``），
不连真实 PG / Redis / 外部服务。
"""

from __future__ import annotations

import importlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openbase.core.errors import ErrorCode
from openbase.core.models import AuditLog
from openbase.demo_app import app
from openbase.modules.auth.jwt import create_access_token

client = TestClient(app)

TODAY = datetime.now().strftime("%Y%m%d")
NOW = datetime.now(timezone.utc).replace(microsecond=0)

# 三行数据：模块/操作/结果/时间各异，覆盖分页、时间窗与关键字过滤
L1_ROWS = (
    {
        "ts": (NOW - timedelta(hours=3)).isoformat(),
        "path": "/api/v1/dps-proxy/forward",
        "method": "POST",
        "status_code": 200,
        "request_id": "req-old",
    },
    {
        "ts": (NOW - timedelta(hours=2)).isoformat(),
        "path": "/api/v1/rag-proxy/chat",
        "method": "POST",
        "status_code": 500,
        "request_id": "req-mid",
    },
    {
        "ts": (NOW - timedelta(hours=1)).isoformat(),
        "path": "/api/v1/auth/login",
        "method": "POST",
        "status_code": 200,
        "request_id": "req-kw-1",
    },
)

READ_HEADERS = {
    "Authorization": "Bearer "
    + create_access_token("7", username="logviewer", extra={"permissions": ["log:read"]})
}
NO_PERMISSION_HEADERS = {
    "Authorization": "Bearer " + create_access_token("8", username="no-log-read")
}

# 三个端点的最小合法查询串（source 必填）
ENDPOINT_QUERIES = (
    "/api/v1/logs/search?source=l1_file",
    "/api/v1/logs/facets?source=l1_file",
    "/api/v1/logs/export?source=l1_file",
)

# ---- 导出设计判据（API §3.3 / 需求 §4.6 原文，逐条可验证）----

# 需求 §4.6 / API §3.3：条数上限 10000（命中 > 10000 → 400）
DESIGN_EXPORT_ROW_LIMIT = 10000

# API §3.3 错误码表：导出超限 → `PARAM_400`（统一错误体 {code, message, detail, request_id}）
DESIGN_EXPORT_LIMIT_CODE = "PARAM_400"

# API §3.3：`Content-Disposition: attachment; filename="logs-<source>-<ts>.<ext>"`。
# 文档未定义 `<ts>` 的具体格式 → 本用例取证最保守解释：文件系统安全 + 可排序的
# `YYYYMMDD-HHMMSS`（Windows 文件名非法字符 `:` 不可用，故不做 ISO8601 直出）。
DESIGN_EXPORT_FILENAME_RE = re.compile(
    r'^attachment; filename="logs-(?P<source>[a-z0-9_]+)-(?P<ts>\d{8}-\d{6})\.(?P<ext>csv|json)"$'
)

# API §3.3 CSV 细节：UTF-8 + 含 \ufeff BOM（Excel 兼容）
DESIGN_CSV_BOM = b"\xef\xbb\xbf"

# API §2 字段名与顺序（CSV 首行表头判据，18 字段）
DESIGN_CSV_HEADER = (
    "ts,source,module,operation,result,request_id,method,path,status_code,"
    "duration_ms,operator_id,tenant_id,ip_address,case_id,step_id,run_id,action,summary"
)

# 导出留痕动作码（API §3.3 / ADR-146-04）
DESIGN_ACTION_LOG_EXPORT = "log.export"


def _write_l1(log_root: Path, rows: list[dict]) -> None:
    """写入 L1 日志分片 logs/openbase/openbase-YYYYMMDD.jsonl."""
    directory = log_root / "openbase"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"openbase-{TODAY}.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8"
    )


def _assert_export_filename(header: str, *, source: str, extension: str) -> datetime:
    """断言 Content-Disposition 命名格式（设计 §3.3）并返回文件名中的时间戳.

    时间戳时区文档未定义 → 本地时区与 UTC 任一在 5 分钟容差内即视为「导出时刻」。
    """
    matched = DESIGN_EXPORT_FILENAME_RE.match(header)
    assert matched is not None, f"Content-Disposition 不符设计 §3.3：{header!r}"
    assert matched.group("source") == source, header
    assert matched.group("ext") == extension, header
    stamp = datetime.strptime(matched.group("ts"), "%Y%m%d-%H%M%S")
    local_now = datetime.now()
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert min(abs(stamp - local_now), abs(stamp - utc_now)) < timedelta(minutes=5), (
        f"文件名时间戳非导出时刻：{matched.group('ts')}"
    )
    return stamp


class _RecordingSession:
    """记录 add/commit/rollback 的假会话（导出留痕字段断言，DB 免依赖）."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FailingSession(_RecordingSession):
    """commit 抛错的假会话（留痕降级路径断言）."""

    async def commit(self) -> None:
        raise RuntimeError("db down")


def _patch_session_factory(monkeypatch: pytest.MonkeyPatch, session: object) -> None:
    """注入假会话工厂（与 tests/test_audit_db_persist.py 同法，函数内延迟导入可注入）."""
    session_module = importlib.import_module("openbase.core.db.session")

    class _SessionContext:
        async def __aenter__(self) -> object:
            return session

        async def __aexit__(self, *exc: object) -> bool:
            return False

    class _FakeSessionFactory:
        def __call__(self) -> _SessionContext:
            return _SessionContext()

    monkeypatch.setattr(session_module, "get_session_factory", lambda: _FakeSessionFactory())


@pytest.fixture
def export_audit_channel(monkeypatch: pytest.MonkeyPatch) -> _RecordingSession:
    """开启导出留痕通道：``OPENBASE_AUDIT_DB_PERSIST=1`` + 记录型假会话.

    隔离说明：本夹具开启开关后，``AuditMiddleware`` 也会把 ``api.request`` 审计项投入
    **进程级**落库队列（测试内无 writer 消费）；残留条目会被后续 drain 类用例（如
    ``tests/test_modules_switch_api.py`` 的行数断言）观察到，故此处一并阻断入队——
    本用例只断言 logs 模块自身的 ``log.export`` 留痕写入。
    """
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")
    monkeypatch.setattr(
        "openbase.modules.audit.submit_audit_persist", lambda kind, payload: True
    )
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)
    return session


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """构造 L1 日志目录（logs/openbase/openbase-YYYYMMDD.jsonl）并注入 OPENBASE_LOG_DIR."""
    _write_l1(tmp_path / "logs", list(L1_ROWS))
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(tmp_path / "logs"))
    return tmp_path / "logs"


def _search(params: dict | None = None) -> dict:
    query = {"source": "l1_file", **(params or {})}
    resp = client.get("/api/v1/logs/search", params=query, headers=READ_HEADERS)
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()["data"]


# ---- 正常路径：search ----

def test_search_pagination(log_dir: Path) -> None:
    """分页：page_size=2 → 首页 2 条、次页 1 条；ts 倒序（最新在前）. """
    first = _search({"page": 1, "page_size": 2})
    assert first["total"] == 3
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert first["truncated"] is False
    assert [item["request_id"] for item in first["items"]] == ["req-kw-1", "req-mid"]

    second = _search({"page": 2, "page_size": 2})
    assert [item["request_id"] for item in second["items"]] == ["req-old"]


def test_search_keyword_filter(log_dir: Path) -> None:
    """关键字（q）按 request_id/path/operator/ip 命中. """
    data = _search({"q": "req-kw-1"})
    assert data["total"] == 1
    assert data["items"][0]["request_id"] == "req-kw-1"
    assert data["items"][0]["module"] == "identity"  # 派生口径：/auth/login → identity


def test_search_time_window(log_dir: Path) -> None:
    """时间窗（from）只返回窗内条目. """
    window_start = (NOW - timedelta(hours=2, minutes=30)).isoformat()
    data = _search({"from": window_start})
    assert data["total"] == 2
    assert [item["request_id"] for item in data["items"]] == ["req-kw-1", "req-mid"]

    upper = (NOW - timedelta(hours=1, minutes=30)).isoformat()
    narrowed = _search({"from": window_start, "to": upper})
    assert [item["request_id"] for item in narrowed["items"]] == ["req-mid"]


def test_search_module_filter(log_dir: Path) -> None:
    """模块维度过滤（module 可重复传参）. """
    data = _search({"module": "rag"})
    assert data["total"] == 1
    assert data["items"][0]["request_id"] == "req-mid"
    assert data["items"][0]["result"] == "server_error"  # 500 → server_error


# ---- 正常路径：facets / presets ----

def test_facets_dimension_counts(log_dir: Path) -> None:
    """维度聚合与列表同口径（module / result / operation）. """
    resp = client.get(
        "/api/v1/logs/facets", params={"source": "l1_file"}, headers=READ_HEADERS
    )
    assert resp.status_code == 200, resp.text[:300]
    data = resp.json()["data"]
    assert data["module"] == {"identity": 1, "dps": 1, "rag": 1}
    assert data["result"] == {"success": 2, "server_error": 1}
    assert data["operation"]["auth_login"] == 1


def test_facets_presets_enumerates_dimensions(log_dir: Path) -> None:
    """筛选器候选枚举可供前端渲染下拉（同源维度口径）. """
    resp = client.get("/api/v1/logs/facets/presets", headers=READ_HEADERS)
    assert resp.status_code == 200, resp.text[:300]
    data = resp.json()["data"]
    assert data["source"]["values"] == ["l1_file", "audit_db", "test_record", "repo_log"]
    assert set(data["module"]["values"]) >= {"identity", "dps", "rag"}


# ---- 正常路径：export（AC-146-06-1）----

def test_export_csv_attachment(log_dir: Path, export_audit_channel: _RecordingSession) -> None:
    """CSV 导出：200 + `logs-<source>-<ts>.csv` 附件名 + BOM + §2 表头 + 3 行数据. """
    resp = client.get(
        "/api/v1/logs/export", params={"source": "l1_file"}, headers=READ_HEADERS
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.headers["content-type"].startswith("text/csv")
    assert "charset=utf-8" in resp.headers["content-type"]
    _assert_export_filename(
        resp.headers["content-disposition"], source="l1_file", extension="csv"
    )
    assert resp.content.startswith(DESIGN_CSV_BOM), "CSV 首部缺少 \\ufeff BOM（Excel 兼容）"
    rows = resp.content.decode("utf-8-sig").strip().splitlines()
    assert rows[0] == DESIGN_CSV_HEADER
    assert len(rows) == 4  # 1 表头 + 3 数据行


def test_export_json_format(log_dir: Path, export_audit_channel: _RecordingSession) -> None:
    """JSON 导出：application/json + `logs-<source>-<ts>.json` + 全量已排序条目. """
    resp = client.get(
        "/api/v1/logs/export",
        params={"source": "l1_file", "format": "json"},
        headers=READ_HEADERS,
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.headers["content-type"].startswith("application/json")
    _assert_export_filename(
        resp.headers["content-disposition"], source="l1_file", extension="json"
    )
    payload = json.loads(resp.text)
    assert [item["request_id"] for item in payload] == ["req-kw-1", "req-mid", "req-old"]


@pytest.mark.parametrize(
    ("export_format", "extension", "media_prefix"),
    (("csv", "csv", "text/csv"), ("json", "json", "application/json")),
)
def test_export_filename_carries_source_and_timestamp(
    log_dir: Path,
    export_audit_channel: _RecordingSession,
    export_format: str,
    extension: str,
    media_prefix: str,
) -> None:
    """两种 format 文件名均为 `logs-<source>-<ts>.<ext>`（源名 + 导出时刻时间戳）. """
    resp = client.get(
        "/api/v1/logs/export",
        params={"source": "l1_file", "format": export_format},
        headers=READ_HEADERS,
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.headers["content-type"].startswith(media_prefix)
    _assert_export_filename(
        resp.headers["content-disposition"], source="l1_file", extension=extension
    )


def test_export_csv_header_and_summary_cells(
    log_dir: Path, export_audit_channel: _RecordingSession
) -> None:
    """AC-146-06-1：CSV 首行表头 = §2 字段名与顺序；`summary` 为紧凑 JSON 字符串. """
    import csv
    import io as io_module

    _write_l1(
        log_dir,
        [
            {
                "ts": NOW.isoformat(),
                "path": "/api/v1/dps-proxy/forward",
                "method": "POST",
                "status_code": 200,
                "request_id": "req-summary",
                "resp_status": 200,
            }
        ],
    )
    resp = client.get(
        "/api/v1/logs/export", params={"source": "l1_file"}, headers=READ_HEADERS
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.content.decode("utf-8-sig")
    reader = csv.DictReader(io_module.StringIO(body))
    assert reader.fieldnames == DESIGN_CSV_HEADER.split(",")
    rows = list(reader)
    assert len(rows) == 1
    summary_cell = rows[0]["summary"]
    assert json.loads(summary_cell) == {"resp_status": 200}
    # 「紧凑 JSON」：分隔符不含多余空格
    assert summary_cell == json.dumps(
        {"resp_status": 200}, ensure_ascii=False, separators=(",", ":")
    )


def test_export_invalid_format_rejected(log_dir: Path) -> None:
    """format 非法 → 422（schema 枚举白名单，不落文件）. """
    resp = client.get(
        "/api/v1/logs/export",
        params={"source": "l1_file", "format": "xml"},
        headers=READ_HEADERS,
    )
    assert resp.status_code == 422


# ---- 超限保护：AC-146-06-2（命中 > 10000 → 400 PARAM_400）----

def test_export_over_limit_rejected_with_param_error(
    log_dir: Path, export_audit_channel: _RecordingSession
) -> None:
    """命中 10005 条（> 上限 10000）→ 400 `PARAM_400` + `detail={matched, limit}` 提示收窄. """
    _write_l1(
        log_dir,
        [
            {
                "ts": (NOW - timedelta(seconds=index)).isoformat(),
                "path": "/api/v1/logs/search",
                "method": "GET",
                "status_code": 200,
                "request_id": f"req-bulk-{index}",
            }
            for index in range(DESIGN_EXPORT_ROW_LIMIT + 5)
        ],
    )
    resp = client.get(
        "/api/v1/logs/export", params={"source": "l1_file"}, headers=READ_HEADERS
    )
    assert resp.status_code == 400, resp.text[:300]
    body = resp.json()
    assert body["code"] == DESIGN_EXPORT_LIMIT_CODE
    assert body["code"].startswith("PARAM")
    assert body["detail"]["limit"] == DESIGN_EXPORT_ROW_LIMIT
    assert body["detail"]["matched"] > DESIGN_EXPORT_ROW_LIMIT
    assert str(DESIGN_EXPORT_ROW_LIMIT) in body["message"]  # 上限提示（前端文案来源）
    assert body.get("request_id"), "统一错误体必须含 request_id"
    assert "content-disposition" not in resp.headers, "超限不得返回附件"


def test_export_at_limit_allowed(
    log_dir: Path, export_audit_channel: _RecordingSession
) -> None:
    """边界：命中恰为 10000 条（不超限）→ 200 且导出全部 10000 行. """
    _write_l1(
        log_dir,
        [
            {
                "ts": (NOW - timedelta(seconds=index)).isoformat(),
                "path": "/api/v1/logs/search",
                "method": "GET",
                "status_code": 200,
                "request_id": f"req-limit-{index}",
            }
            for index in range(DESIGN_EXPORT_ROW_LIMIT)
        ],
    )
    resp = client.get(
        "/api/v1/logs/export", params={"source": "l1_file"}, headers=READ_HEADERS
    )
    assert resp.status_code == 200, resp.text[:300]
    assert len(resp.content.decode("utf-8-sig").strip().splitlines()) == (
        DESIGN_EXPORT_ROW_LIMIT + 1
    )  # 1 表头 + 10000 数据行


# ---- 脱敏红线：AC-146-06-3（导出物无明文敏感值）----

def test_export_masks_sensitive_plaintext(
    log_dir: Path, export_audit_channel: _RecordingSession
) -> None:
    """导出内容同样脱敏：`token` 明文不出现在文件字节中（服务端脱敏，前端不承担）. """
    import csv
    import io as io_module

    service_directory = log_dir / "dps"
    service_directory.mkdir(parents=True, exist_ok=True)
    (service_directory / f"dps-{TODAY}.log").write_text(
        json.dumps(
            {
                "ts": NOW.isoformat(),
                "path": "/api/v1/dps-proxy/forward",
                "method": "POST",
                "status": 200,
                "request_id": "dps-secret-1",
                "event": {"token": "SECRET-TOKEN-VALUE"},
            }
        ),
        encoding="utf-8",
    )
    resp = client.get(
        "/api/v1/logs/export", params={"source": "repo_log"}, headers=READ_HEADERS
    )
    assert resp.status_code == 200, resp.text[:300]
    assert b"SECRET-TOKEN-VALUE" not in resp.content
    rows = list(csv.DictReader(io_module.StringIO(resp.content.decode("utf-8-sig"))))
    assert len(rows) == 1
    assert json.loads(rows[0]["summary"])["event"]["token"] == "***"


# ---- 留痕：AC-146-06-4（每次导出落 1 条 audit_logs(action=log.export)）----

def test_export_writes_log_export_audit_trail(
    log_dir: Path, export_audit_channel: _RecordingSession
) -> None:
    """每次导出写 1 条 `log.export` 行：含操作人/筛选摘要/条数/格式，且不含检索关键字. """
    resp = client.get(
        "/api/v1/logs/export",
        params={"source": "l1_file", "module": "dps", "q": "req-old"},
        headers=READ_HEADERS,
    )
    assert resp.status_code == 200, resp.text[:300]

    assert export_audit_channel.committed is True
    assert len(export_audit_channel.added) == 1, "每次导出仅落 1 条留痕"
    row = export_audit_channel.added[0]
    assert isinstance(row, AuditLog)
    assert row.action == DESIGN_ACTION_LOG_EXPORT
    assert row.user_id == 7  # 操作人（令牌 sub=7）
    assert row.request_id == resp.headers["x-request-id"]
    assert set(row.detail) == {"actor", "source", "filters", "row_count", "format"}
    assert row.detail["actor"] == "7"
    assert row.detail["source"] == "l1_file"
    assert row.detail["format"] == "csv"
    assert row.detail["row_count"] == 1
    assert row.detail["filters"]["module"] == ["dps"]
    serialized = json.dumps(row.detail, ensure_ascii=False)
    # AC-146-03-3 / 设计 §6：检索关键字不落 audit_logs
    assert "req-old" not in serialized
    # ADR-146-04：不记录导出内容（表头/数据行不入留痕）
    assert "ts,source,module" not in serialized


def test_export_rejected_when_audit_channel_disabled(
    log_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """留痕通道显式不可用（开关=0）→ 拒绝导出，不返回未留痕的文件. """
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "0")
    resp = client.get(
        "/api/v1/logs/export", params={"source": "l1_file"}, headers=READ_HEADERS
    )
    assert resp.status_code == 503, resp.text[:300]
    assert resp.json()["code"] == ErrorCode.BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE.value
    assert "content-disposition" not in resp.headers


def test_export_survives_audit_persist_failure(
    log_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """设计 §3.3「留痕失败不影响导出」：落库异常 → WARN + 继续返回文件（ADR-146-04）. """
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")
    monkeypatch.setattr(
        "openbase.modules.audit.submit_audit_persist", lambda kind, payload: True
    )
    failing_session = _FailingSession()
    _patch_session_factory(monkeypatch, failing_session)

    with caplog.at_level(logging.WARNING, logger="openbase.logs"):
        resp = client.get(
            "/api/v1/logs/export", params={"source": "l1_file"}, headers=READ_HEADERS
        )

    assert resp.status_code == 200, resp.text[:300]
    assert resp.content.startswith(DESIGN_CSV_BOM)
    assert len(resp.content.decode("utf-8-sig").strip().splitlines()) == 4
    assert failing_session.rolled_back is True
    assert any(record.levelno == logging.WARNING for record in caplog.records), "缺少降级 WARN"


def test_search_unknown_source_rejected(log_dir: Path) -> None:
    """source 非法 → 422（枚举白名单，防任意源探测）. """
    resp = client.get(
        "/api/v1/logs/search", params={"source": "no_such_source"}, headers=READ_HEADERS
    )
    assert resp.status_code == 422


# ---- 权限红线 ----

@pytest.mark.parametrize("path", ENDPOINT_QUERIES)
def test_logs_endpoints_require_token(path: str) -> None:
    """无令牌 → 401（AuthMiddleware 门禁，不进入路由）. """
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ENDPOINT_QUERIES)
def test_logs_endpoints_forbidden_without_log_read(path: str) -> None:
    """令牌有效但无 log:read → 403（受权点失败，响应走统一错误契约）. """
    resp = client.get(path, headers=NO_PERMISSION_HEADERS)
    assert resp.status_code == 403, resp.text[:300]
    assert resp.json()["code"] == ErrorCode.AUTH_FORBIDDEN.value


def test_logs_endpoints_require_valid_token() -> None:
    """无效令牌 → 401（伪造签名不接受）. """
    resp = client.get(
        "/api/v1/logs/search",
        params={"source": "l1_file"},
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert resp.status_code == 401
