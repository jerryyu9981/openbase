"""S7-T6 门禁聚合断言（RA-06 五项 / 冒烟 S0-S6 / 对齐清单关闭 / K07+SYS-1 终验）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》§2.4 机制 4 与 §4.6
（S7-T6-1 ~ S7-T6-4），以及 §1.2 Q-S7-D7（聚合脚本语言 = Python）、Q-S7-D8
（evidence 目录 `doc/test/evidence/s7/**`）。

断言口径（沙箱可判定面 / A 面 + 联调窗口必需面 / B 面；禁止以「预期通过」代替证据）：
- S7-T6-1：RA-06 五项聚合（双租户隔离回归 / fail-closed / OIDC 批次隔离 /
  委托跨界 403 / 吊销即时性）；沙箱内可执行子项真实运行并按退出码汇总，
  真实双租户数据面 B 面登记 PENDING；
- S7-T6-2：冒烟 S0-S6 聚合（结构对账完成、P0/P1 分列；真实服务面 PENDING）；
- S7-T6-3：存量测试对齐清单关闭（doc 状态升版 + 分批门禁复跑记录）；
- S7-T6-4：K07 + SYS-1 矩阵终验对账（存在性与计数；真实 openapi 全量导出 PENDING）；
- SHR：引用批 1 SHR 五项产物（verify-env 全局化 / openbase_test / K13 / 编排 / 文档地图）。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_GATE_SCRIPT = ROOT / "scripts" / "gate_aggregate.py"
_GATE_EVIDENCE = ROOT / "doc" / "test" / "evidence" / "s7" / "gate" / "gate-aggregate.json"
_ALIGN_CHECKLIST = ROOT / "OpenBase-存量测试对齐任务清单-v1.0.0.md"
_SMOKE_CHECKLIST = ROOT / "OpenBase-真实联调冒烟清单-v1.0.0.md"
_K07_TEMPLATE = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
_SHR_EVIDENCE_DIR = ROOT / "doc" / "test" / "evidence" / "s7" / "shr"

_SECTION_IDS = ("RA-06", "SMOKE-S0-S6", "TEST-ALIGN-CLOSE", "K07-SYS-1", "SHR")
_RA06_ITEM_KEYS = {
    "tenant_isolation_regression",
    "fail_closed",
    "oidc_batch_isolation",
    "delegation_cross_tenant_403",
    "revocation_immediacy",
}
# 沙箱内可执行的 RA-06 子项（既有 pytest 选择器；应真实运行并按退出码判定）
_SANDBOX_EXECUTABLE_RA06 = (
    "tenant_isolation_regression",
    "fail_closed",
    "oidc_batch_isolation",
    "delegation_cross_tenant_403",
    "revocation_immediacy",
)
_STATUS_VALUES = {"PASS", "FAIL", "PENDING"}
_SMOKE_GROUPS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6")
_SHR_ITEMS = {
    "verify_env_global",
    "openbase_test",
    "k13",
    "orchestrator",
    "doc_map",
}
_K07_REPOS = {"openbase", "openllm", "openrag", "openmemory", "dps"}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GATE_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _find_section(report: dict[str, Any], section_id: str) -> dict[str, Any]:
    for section in report["sections"]:
        if section["id"] == section_id:
            return section
    raise AssertionError(f"聚合证据缺少分项: {section_id}")


def _find_item(section: dict[str, Any], key: str) -> dict[str, Any]:
    for item in section.get("items", []):
        if item.get("key") == key:
            return item
    raise AssertionError(f"分项 {section['id']} 缺少子项: {key}")


@pytest.fixture(scope="module")
def gate_report(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """沙箱干跑门禁聚合一次（跳过大批量主批次以控制耗时）并返回结构化证据."""
    assert _GATE_SCRIPT.exists(), f"缺少门禁聚合脚本: {_GATE_SCRIPT}"
    out_path = tmp_path_factory.mktemp("gate") / "gate-aggregate.json"
    result = _run_gate("--dry-run", "--skip-main-batch", "--out", str(out_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert out_path.exists(), f"门禁聚合未产出证据: {result.stdout}\n{result.stderr}"
    return _load_json(out_path)


# ===========================================================================
# 脚本形态（单命令 / 单批 / 结构化 JSON / 清晰退出码）
# ===========================================================================


def test_gate_script_present_and_cli_structure() -> None:
    """聚合脚本存在，argparse 单命令入口，含 dry-run/输出/子项关键词."""
    assert _GATE_SCRIPT.exists(), f"缺少门禁聚合脚本: {_GATE_SCRIPT}"
    text = _read_text(_GATE_SCRIPT)
    for marker in (
        "argparse",
        "--dry-run",
        "--out",
        "RA-06",
        "S0-S6",
        "K07",
        "SYS-1",
        "PENDING",
        "openbase_commit",
        "json",
    ):
        assert marker in text, f"gate_aggregate.py 缺少必需结构: {marker}"


def test_gate_script_help_exit_zero() -> None:
    """--help 可用且退出码 0（可被 CI 调用）."""
    result = _run_gate("--help")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dry-run" in (result.stdout + result.stderr)


# ===========================================================================
# S7-T6-1 RA-06 五项聚合
# ===========================================================================


def test_ra06_five_items_present(gate_report: dict[str, Any]) -> None:
    """RA-06 分项含五项（双租户/fail-closed/OIDC/委托跨界/吊销即时性）."""
    section = _find_section(gate_report, "RA-06")
    keys = {item["key"] for item in section["items"]}
    assert keys == _RA06_ITEM_KEYS, f"RA-06 子项游离/缺失: {keys}"
    assert section["execution_face"] == "A+B"


def test_ra06_sandbox_executable_subset_runs_and_passes(gate_report: dict[str, Any]) -> None:
    """沙箱可执行子项真实运行并按退出码汇总为 PASS（含用例数与选择器）."""
    section = _find_section(gate_report, "RA-06")
    for key in _SANDBOX_EXECUTABLE_RA06:
        item = _find_item(section, key)
        assert item["status"] == "PASS", f"{key} 沙箱执行未通过: {item}"
        assert item["exit_code"] == 0, f"{key} 退出码非 0: {item}"
        assert item["cases"] >= 1, f"{key} 未记录用例数: {item}"
        assert item["selector"], f"{key} 未记录 pytest 选择器: {item}"
        assert any("tests/" in path for path in item["selector"]), item


def test_ra06_real_face_marked_pending(gate_report: dict[str, Any]) -> None:
    """RA-06 五项真实双租户数据面（B 面）登记 PENDING 且附原因（不得伪造通过）."""
    section = _find_section(gate_report, "RA-06")
    for item in section["items"]:
        assert item["real_face_status"] == "PENDING", item
        assert item["reason"], f"{item['key']} PENDING 缺少原因"


# ===========================================================================
# S7-T6-2 冒烟 S0-S6 聚合（结构对账 + P0/P1 分列）
# ===========================================================================


def test_smoke_s0_s6_structure_reconciled(gate_report: dict[str, Any]) -> None:
    """冒烟分项覆盖 S0-S6，P0/P1 分列，结构对账 PASS，真实面 PENDING."""
    section = _find_section(gate_report, "SMOKE-S0-S6")
    matrix = section["matrix"]
    assert tuple(matrix["groups"]) == _SMOKE_GROUPS, matrix["groups"]
    assert matrix["p0_count"] >= 25, matrix
    assert matrix["p1_count"] >= 2, matrix
    assert section["structure_status"] == "PASS"
    assert section["real_face_status"] == "PENDING"
    assert section["reason"]
    for case_id in matrix["p0_cases"]:
        assert case_id.startswith("S"), case_id
    for case_id in matrix["p1_cases"]:
        assert case_id.startswith("S"), case_id


def test_smoke_cases_traceable_to_checklist() -> None:
    """冒烟用例矩阵锚定冒烟清单 v1.1.0 §3（P0 全绿 / P1 登记语义可核对）."""
    assert _SMOKE_CHECKLIST.exists(), _SMOKE_CHECKLIST
    text = _read_text(_SMOKE_CHECKLIST)
    for marker in ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "P0", "P1"):
        assert marker in text, f"冒烟清单缺少 {marker}"
    for case_id in ("S0-1", "S2-1", "S4-4", "S5-1", "S6-3"):
        assert case_id in text, f"冒烟清单缺少用例 {case_id}"


# ===========================================================================
# S7-T6-3 存量测试对齐清单关闭
# ===========================================================================


def test_alignment_checklist_doc_closed() -> None:
    """对齐清单 doc 侧状态升版（[Draft]→[Approved]）并登记复跑结论与 PENDING."""
    assert _ALIGN_CHECKLIST.exists(), _ALIGN_CHECKLIST
    text = _read_text(_ALIGN_CHECKLIST)
    assert "| 状态 | [Approved] |" in text, "对齐清单状态未升版为 [Approved]"
    assert "[Draft]→[Approved]" in text or "[Draft] →[Approved]" in text or "[Draft] → [Approved]" in text
    assert "分批门禁复跑结论" in text
    assert "asyncpg" in text and "PENDING" in text


def test_alignment_close_section_records_batches(gate_report: dict[str, Any]) -> None:
    """对齐清单关闭分项记录 OIDC 独立批次 + 主批次复跑（退出码与用例数）."""
    section = _find_section(gate_report, "TEST-ALIGN-CLOSE")
    assert section["doc_status"] == "Approved"
    oidc_batch = section["oidc_batch"]
    assert oidc_batch["status"] == "PASS" and oidc_batch["exit_code"] == 0
    assert oidc_batch["cases"] >= 12, oidc_batch
    main_batch = section["main_batch"]
    assert main_batch["status"] in {"PASS", "PENDING"}, main_batch
    if main_batch["status"] == "PASS":
        assert main_batch["exit_code"] == 0
    else:
        assert main_batch["reason"]
    pending_ids = {item["id"] for item in section["pending_items"]}
    assert any("PG" in item or "asyncpg" in item for item in pending_ids), section["pending_items"]


# ===========================================================================
# S7-T6-4 K07 + SYS-1 矩阵终验（存在性与计数对账）
# ===========================================================================


def test_k07_sys1_repos_reconciled(gate_report: dict[str, Any]) -> None:
    """K07/SYS-1 分项覆盖 OpenBase 模板 + 四仓已填报矩阵，结构对账 PASS."""
    section = _find_section(gate_report, "K07-SYS-1")
    repos = section["repos"]
    assert set(repos) == _K07_REPOS, f"K07 对账仓游离/缺失: {set(repos)}"
    assert repos["openbase"]["status"] == "PASS", repos["openbase"]
    for repo in ("openllm", "openrag", "openmemory", "dps"):
        assert repos[repo]["status"] in _STATUS_VALUES, repos[repo]
        if repos[repo]["status"] == "PASS":
            assert repos[repo]["gap_count"] == 0, repos[repo]


def test_k07_template_present_and_gap_zero_semantics() -> None:
    """OpenBase 侧模板存在且含缺口清零/未覆盖清零/豁免有效期终验语义."""
    assert _K07_TEMPLATE.exists(), _K07_TEMPLATE
    text = _read_text(_K07_TEMPLATE)
    for marker in ("缺口清零", "未覆盖清零", "豁免", "隔离测试注册位"):
        assert marker in text, f"K07 模板缺少终验语义: {marker}"


def test_k07_real_face_pending(gate_report: dict[str, Any]) -> None:
    """K07/SYS-1 真实 openapi 全量导出与终验属 B 面 → PENDING 且附原因."""
    section = _find_section(gate_report, "K07-SYS-1")
    assert section["real_face_status"] == "PENDING"
    assert section["reason"]


# ===========================================================================
# SHR 五项（调用批 1 产物）
# ===========================================================================


def test_shr_section_references_batch1_artifacts(gate_report: dict[str, Any]) -> None:
    """SHR 分项引用批 1 五项收口产物，且证据目录真实存在."""
    section = _find_section(gate_report, "SHR")
    keys = {item["key"] for item in section["items"]}
    assert keys == _SHR_ITEMS, f"SHR 子项游离/缺失: {keys}"
    for item in section["items"]:
        assert item["status"] in _STATUS_VALUES, item
        assert item["evidence"], item
    assert (_SHR_EVIDENCE_DIR / "verify-env-global" / "contract-align.json").exists()
    assert (_SHR_EVIDENCE_DIR / "openbase-test" / "init-check.json").exists()
    assert (_SHR_EVIDENCE_DIR / "k13" / "account-matrix-check.json").exists()
    assert (_SHR_EVIDENCE_DIR / "orchestrator" / "bypass-scan.json").exists()
    assert (_SHR_EVIDENCE_DIR / "doc-map" / "orphan-check.json").exists()


# ===========================================================================
# 证据规范（§5.2 / §5.4：字段齐备 / 禁伪造）
# ===========================================================================


def test_gate_report_top_level_fields(gate_report: dict[str, Any]) -> None:
    """证据顶层字段齐备：schema_version / mode / openbase_commit / sections / exit_code."""
    assert gate_report["schema_version"] == 1
    assert gate_report["mode"] == "dry-run"
    assert gate_report["openbase_commit"], "缺少 OpenBase HEAD 提交号"
    assert len(gate_report["openbase_commit"]) >= 7
    assert gate_report["generated_at"]
    assert gate_report["overall_status"] in {"PASS", "PENDING", "FAIL"}
    assert gate_report["exit_code"] in {0, 1}
    ids = [section["id"] for section in gate_report["sections"]]
    assert ids == list(_SECTION_IDS), ids


def test_no_b_face_pass_and_pending_has_reason(gate_report: dict[str, Any]) -> None:
    """禁伪造：B 面子项不得填 PASS；任一 PENDING 项必须附原因."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            status = node.get("status")
            face = node.get("execution_face")
            if status == "PASS":
                assert face != "B", f"B 面出现 PASS（禁伪造）: {node}"
            if status == "PENDING":
                assert node.get("reason"), f"PENDING 缺少 reason: {node}"
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(gate_report["sections"])
    assert gate_report["pending_items"], "全局 PENDING 登记不得为空"


def test_committed_evidence_file_exists_and_valid() -> None:
    """仓内留存证据 `doc/test/evidence/s7/gate/gate-aggregate.json` 存在且结构合法."""
    assert _GATE_EVIDENCE.exists(), f"缺少聚合证据: {_GATE_EVIDENCE}"
    report = _load_json(_GATE_EVIDENCE)
    assert report["schema_version"] == 1
    assert report["openbase_commit"]
    ids = [section["id"] for section in report["sections"]]
    assert ids == list(_SECTION_IDS), ids
    assert report["pending_items"]
    assert _read_text(_GATE_EVIDENCE).count("PENDING") >= 1
