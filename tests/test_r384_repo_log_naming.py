"""R-384 / BL-147-04 采集文件命名白名单一致性测试（TDD：先 RED，后实现）.

被测：``scripts/verify_repo_log_naming.py``

判据唯一来源：``openbase/modules/logs/repository.py::REPO_LOG_NAME_RE``
（即 :class:`RepoLogAdapter` 的文件名白名单——采集文件必须被适配器「看得见」才算命名对齐）。

覆盖：
- 四仓**结构化流**命名（stdout 结构化：``openrag``；stderr 结构化：``dps`` / ``openllm`` /
  ``openmemory``）与其**归档**命名（``{svc}-YYYYMMDD-HHmmss`` + 原扩展名后缀）；
- 旧命名反例（时间戳位于 ``.err`` 之后 → 适配器白名单不匹配 = BL-147-04 修复的缺陷）；
- ``--logs-root`` 实测扫描（按真实目录判定「可见 / 不可见」）；
- 非 repo_log 源目录（``openbase`` / ``frontend``）不纳入判据（skipped，不误报）。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_repo_log_naming.py"
ORCHESTRATOR = ROOT / "scripts" / "service-orchestrator.ps1"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_repo_log_naming", SCRIPT)
    assert spec and spec.loader, f"无法加载校验脚本: {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_repo_log_naming"] = module
    spec.loader.exec_module(module)
    return module


def _status_by_entry(report: dict) -> dict[str, str]:
    return {row["entry"]: row["status"] for row in report["results"]}


# ---------------------------------------------------------------------------
# 契约内命名：四仓结构化流 + 归档变体（BL-147-04 目标口径）
# ---------------------------------------------------------------------------


def test_accepts_stdout_structured_stream_names() -> None:
    """OpenRAG（stdout 结构化）：``{svc}-YYYYMMDD.jsonl`` 与其归档均应为可见。"""
    module = _load_script()

    report = module.verify_entries(
        [
            "openrag/openrag-20260919.jsonl",
            "openrag/openrag-20260919-155700.jsonl",
            "openrag/openrag-20260919.err.log",
        ]
    )

    assert report["failed"] == 0, report["results"]
    assert _status_by_entry(report) == {
        "openrag/openrag-20260919.jsonl": "ok",
        "openrag/openrag-20260919-155700.jsonl": "ok",
        "openrag/openrag-20260919.err.log": "ok",
    }


def test_accepts_stderr_structured_stream_names() -> None:
    """DPS/OpenLLM/OpenMemory（stderr 结构化）：``{svc}-YYYYMMDD.err.jsonl`` 及其归档均应为可见。"""
    module = _load_script()

    report = module.verify_entries(
        [
            "dps/dps-20260919.err.jsonl",
            "dps/dps-20260919-155700.err.jsonl",
            "openllm/openllm-20260919.err.jsonl",
            "openmemory/openmemory-20260919.err.jsonl",
        ]
    )

    assert report["failed"] == 0, report["results"]
    assert all(row["status"] == "ok" for row in report["results"])


def test_accepts_legacy_plain_text_stream_names() -> None:
    """非结构化流（``.log`` / ``.err.log``）仍在白名单内（兼容历史采集文件，不倒退）。"""
    module = _load_script()

    report = module.verify_entries(
        [
            "dps/dps-20260914.log",
            "dps/dps-20260914.err.log",
            "dps/dps-20260914-155700.log",
            "dps/dps-20260914-155700.err.log",
        ]
    )

    assert report["failed"] == 0, report["results"]


# ---------------------------------------------------------------------------
# 反例：适配器「看不见」的命名（BL-147-04 修复点）
# ---------------------------------------------------------------------------


def test_rejects_timestamp_after_err_marker() -> None:
    """旧归档命名 ``{svc}-YYYYMMDD.err-HHmmss.log`` → 白名单不匹配（时间戳须在 ``.err`` 之前）。"""
    module = _load_script()

    report = module.verify_entries(["dps/dps-20260914.err-220336.log"])

    assert report["failed"] == 1
    assert report["results"][0]["status"] == "failed"


def test_rejects_mismatched_svc_segment() -> None:
    """文件名 svc 段与目录不一致 → 适配器按目录过滤会漏读该文件。"""
    module = _load_script()

    report = module.verify_entries(["openrag/dps-20260919.jsonl"])

    assert report["failed"] == 1
    assert "svc" in report["results"][0]["reason"]


def test_rejects_unknown_extension_and_bad_date() -> None:
    """扩展名越界（``.txt``）与非法日期段均判失败（不静默放过）。"""
    module = _load_script()

    report = module.verify_entries(["dps/dps-20260919.txt", "dps/dps-99999999.jsonl"])

    assert report["failed"] == 2, report["results"]


def test_rejects_entry_without_svc_dir() -> None:
    """条目必须形如 ``<svc>/<basename>``；裸文件名判失败（调用侧口径错误要暴露）。"""
    module = _load_script()

    report = module.verify_entries(["dps-20260919.jsonl"])

    assert report["failed"] == 1


# ---------------------------------------------------------------------------
# 非 repo_log 源目录：跳过而非误报
# ---------------------------------------------------------------------------


def test_skips_non_repo_source_dirs() -> None:
    """``openbase`` / ``frontend`` / ``oidc-idp`` 不属 repo_log 源 → skipped（不影响退出码）。"""
    module = _load_script()

    report = module.verify_entries(
        [
            "openbase/openbase-20260919.jsonl",
            "frontend/frontend-20260919.log",
            "oidc-idp/oidc-idp-20260919.jsonl",
        ]
    )

    assert report["failed"] == 0
    assert report["skipped"] == 3


# ---------------------------------------------------------------------------
# --logs-root 实测扫描（命名实测证据）
# ---------------------------------------------------------------------------


def _write_repo_logs(root: Path) -> None:
    (root / "dps").mkdir(parents=True, exist_ok=True)
    (root / "dps" / "dps-20260919.err.jsonl").write_text('{"ts":"x"}\n', encoding="utf-8")
    (root / "dps" / "dps-20260919.err-155700.log").write_text("legacy\n", encoding="utf-8")
    (root / "openrag").mkdir(parents=True, exist_ok=True)
    (root / "openrag" / "openrag-20260919.jsonl").write_text('{"ts":"x"}\n', encoding="utf-8")
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    (root / "frontend" / "frontend-20260919.log").write_text("VITE ready\n", encoding="utf-8")


def test_scan_logs_root_reports_visibility(tmp_path: Path) -> None:
    """实测扫描：按真实目录产出「可见 / 不可见」清单，并区分非 repo_log 源。"""
    module = _load_script()
    _write_repo_logs(tmp_path)

    report = module.scan_logs_root(tmp_path)

    status = _status_by_entry(report)
    assert status["dps/dps-20260919.err.jsonl"] == "ok"
    assert status["dps/dps-20260919.err-155700.log"] == "failed"
    assert status["openrag/openrag-20260919.jsonl"] == "ok"
    assert status["frontend/frontend-20260919.log"] == "skipped"


def test_scan_logs_root_marks_missing_dirs(tmp_path: Path) -> None:
    """缺失的四仓目录如实登记（不得静默当作通过）。"""
    module = _load_script()

    report = module.scan_logs_root(tmp_path)

    assert set(report["missing_dirs"]) == {"dps", "openllm", "openmemory", "openrag"}
    assert report["failed"] == 0


def test_scan_logs_root_tolerates_legacy_archive_names(tmp_path: Path) -> None:
    """在盘历史文件：旧归档命名可显式降为 ``legacy``（默认仍严格记 failed）。"""
    module = _load_script()
    _write_repo_logs(tmp_path)

    strict = module.scan_logs_root(tmp_path)
    tolerant = module.scan_logs_root(tmp_path, tolerate_legacy=True)

    assert strict["failed"] == 1
    assert tolerant["failed"] == 0
    assert tolerant["legacy"] == 1


def test_main_exit_codes(tmp_path: Path, capsys) -> None:
    """CLI：全部可见 → 0；存在不可见 → 1；并打印逐条结论。"""
    module = _load_script()

    clean_exit = module.main(["--file", "dps/dps-20260919.jsonl"])
    assert clean_exit == 0

    dirty_exit = module.main(["--file", "dps/dps-20260919.err-220336.log"])
    assert dirty_exit == 1
    assert "dps-20260919.err-220336.log" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 编排器结构护栏（命名来源在 PS1，须声明结构化流并暴露 namecheck 动作）
# ---------------------------------------------------------------------------


def test_orchestrator_declares_structured_streams_and_namecheck() -> None:
    """编排器须声明四仓结构化流并暴露命名实测动作（防人工漏配 / 名称漂移）。"""
    text = ORCHESTRATOR.read_text(encoding="utf-8")

    assert "namecheck" in text
    for svc in ("dps", "openllm", "openmemory", "openrag"):
        assert f"Name    = '{svc}'" in text
    assert text.count("JsonStream = 'stderr'") == 3
    assert text.count("JsonStream = 'stdout'") == 1
