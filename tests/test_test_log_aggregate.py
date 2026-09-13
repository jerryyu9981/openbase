"""C-7 日志聚合脚本测试（TDD：先 RED，后实现）.

被测：``scripts/test_log_aggregate.py``（方案 §5 批 1 C-7）
- 输入：``logs/**/*.jsonl``（C-1 落盘 + C-3 用例上下文字段）
- 输出：``doc/test/evidence/manual/<run_id>.json`` + 同名 ``.md``
- 统一退出码：``0`` = PASS；``1`` = FAIL（存在失败步骤）；``2`` = PENDING（无记录）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test_log_aggregate.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_log_aggregate", SCRIPT)
    assert spec and spec.loader, f"无法加载聚合脚本: {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_log_aggregate"] = module
    spec.loader.exec_module(module)
    return module


def _line(
    *,
    request_id: str,
    run_id: str,
    case_id: str,
    step_id: int,
    status_code: int = 200,
    method: str = "GET",
    path: str = "/api/v1/dps-proxy/portraits",
    duration_ms: int = 12,
    channel: str = "B",
) -> str:
    return json.dumps(
        {
            "ts": "2026-09-14T01:00:00.000+00:00",
            "level": "INFO",
            "service": "openbase",
            "module": "openbase.audit",
            "message": "api.request",
            "env": "dev",
            "version": "abc1234",
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "channel": channel,
            "case_id": case_id,
            "step_id": step_id,
            "run_id": run_id,
        },
        ensure_ascii=False,
    )


def _write_logs(root: Path) -> None:
    """构造两份服务日志：run-1（含 1 个失败步骤）/ run-2。"""
    openbase_dir = root / "openbase"
    openbase_dir.mkdir(parents=True, exist_ok=True)
    (openbase_dir / "openbase-20260914.jsonl").write_text(
        "\n".join(
            [
                _line(request_id="req-1", run_id="run-1", case_id="UI-DPS-0007", step_id=1),
                _line(
                    request_id="req-2",
                    run_id="run-1",
                    case_id="UI-DPS-0007",
                    step_id=2,
                    status_code=500,
                    method="POST",
                ),
                _line(request_id="req-3", run_id="run-1", case_id="S7-T2-1", step_id=1),
                "",
            ]
        ),
        encoding="utf-8",
    )
    other_dir = root / "openrag"
    other_dir.mkdir(parents=True, exist_ok=True)
    (other_dir / "openrag-20260914.jsonl").write_text(
        "\n".join(
            [
                _line(
                    request_id="req-4",
                    run_id="run-2",
                    case_id="UI-RAG-0001",
                    step_id=1,
                    path="/api/v1/rag-proxy/collections",
                ),
                "not-a-json-line",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # 非 jsonl 文件不得被聚合（C-6 采集的纯文本日志）
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    (root / "frontend" / "frontend-20260914.log").write_text("VITE ready\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 聚合分组（C-7）
# ---------------------------------------------------------------------------


def test_aggregate_groups_by_run_and_case(tmp_path: Path) -> None:
    """按 run_id → case_id 分组，统计步骤数与失败数。"""
    module = _load_script()
    _write_logs(tmp_path)

    report = module.aggregate(tmp_path, run_id="run-1")

    assert report["run_id"] == "run-1"
    assert report["totals"]["records"] == 3
    assert report["totals"]["cases"] == 2
    assert report["totals"]["failed_steps"] == 1

    by_case = {case["case_id"]: case for case in report["cases"]}
    assert set(by_case) == {"UI-DPS-0007", "S7-T2-1"}
    assert by_case["UI-DPS-0007"]["status"] == "FAIL"
    assert by_case["UI-DPS-0007"]["steps"][1]["status_code"] == 500
    assert by_case["UI-DPS-0007"]["steps"][1]["request_id"] == "req-2"
    assert by_case["S7-T2-1"]["status"] == "PASS"

    assert report["sources"] == ["logs/openbase/openbase-20260914.jsonl"]


def test_aggregate_filters_other_runs(tmp_path: Path) -> None:
    """run_id 过滤：其他轮次记录不得混入。"""
    module = _load_script()
    _write_logs(tmp_path)

    report = module.aggregate(tmp_path, run_id="run-2")

    assert report["totals"]["records"] == 1
    assert [case["case_id"] for case in report["cases"]] == ["UI-RAG-0001"]


def test_aggregate_skips_malformed_lines_and_non_jsonl(tmp_path: Path) -> None:
    """健壮性：非法 JSON 行跳过；``.log`` 纯文本文件不参与聚合。"""
    module = _load_script()
    _write_logs(tmp_path)

    report = module.aggregate(tmp_path)

    assert report["totals"]["records"] == 4
    assert report["skipped_lines"] == 1
    assert all(not source.endswith(".log") for source in report["sources"])


def test_aggregate_marks_pending_without_records(tmp_path: Path) -> None:
    """无任何记录（无真实数据）→ PENDING 语义（status=PENDING, 无用例）。"""
    module = _load_script()

    report = module.aggregate(tmp_path)

    assert report["status"] == "PENDING"
    assert report["totals"]["records"] == 0
    assert report["cases"] == []


# ---------------------------------------------------------------------------
# 输出与退出码
# ---------------------------------------------------------------------------


def test_main_writes_json_and_markdown(tmp_path: Path, capsys) -> None:
    """CLI：产出 ``<run_id>.json`` + ``<run_id>.md``，退出码 0（无失败步骤）。"""
    module = _load_script()
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "evidence"
    _write_logs(logs_root)

    exit_code = module.main(
        [
            "--logs-root",
            str(logs_root),
            "--out-dir",
            str(out_dir),
            "--run-id",
            "run-2",
        ]
    )

    assert exit_code == 0
    json_path = out_dir / "run-2.json"
    md_path = out_dir / "run-2.md"
    assert json_path.exists() and md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run-2"
    assert payload["status"] == "PASS"

    markdown = md_path.read_text(encoding="utf-8")
    assert "UI-RAG-0001" in markdown
    assert "req-4" in markdown

    assert "PASS" in capsys.readouterr().out


def test_main_returns_fail_when_failed_step_present(tmp_path: Path) -> None:
    """含失败步骤 → 退出码 1（供门禁/人工复核使用）。"""
    module = _load_script()
    logs_root = tmp_path / "logs"
    _write_logs(logs_root)

    exit_code = module.main(
        ["--logs-root", str(logs_root), "--out-dir", str(tmp_path / "ev"), "--run-id", "run-1"]
    )

    assert exit_code == 1
    payload = json.loads((tmp_path / "ev" / "run-1.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAIL"
    assert payload["totals"]["failed_steps"] == 1


def test_main_returns_pending_when_no_records(tmp_path: Path) -> None:
    """无记录 → 退出码 2（PENDING：尚无真实人工测试数据）。"""
    module = _load_script()

    exit_code = module.main(
        ["--logs-root", str(tmp_path / "empty"), "--out-dir", str(tmp_path / "ev")]
    )

    assert exit_code == 2


def test_markdown_contains_evidence_columns(tmp_path: Path) -> None:
    """Markdown 报告含双证据列（用例/步骤/状态码/request_id/耗时）。"""
    module = _load_script()
    logs_root = tmp_path / "logs"
    _write_logs(logs_root)

    module.main(
        ["--logs-root", str(logs_root), "--out-dir", str(tmp_path / "ev"), "--run-id", "run-1"]
    )
    markdown = (tmp_path / "ev" / "run-1.md").read_text(encoding="utf-8")

    for expected in ("case_id", "step_id", "status_code", "request_id", "duration_ms"):
        assert expected in markdown, f"Markdown 缺少列 {expected}"
    assert "run-1" in markdown
