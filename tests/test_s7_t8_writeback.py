"""S7-T8 台账全量回写与总收官报告断言（24 卡 / 七线 JT / 文档地图 / 总收官报告）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》§1.2（Q-S7-D6 文档地图落点、
Q-S7-D9 收官报告单文件形态、Q-S7-D10 会签汇总表落点）、§4.8（S7-T8-1 ~ S7-T8-5）、
§5（证据与报告规范）、§6/§7。

断言口径（沙箱可判定面 / A 面 + 联调窗口必需面 / B 面；禁止以「预期通过」代替证据）：
- S7-T8-1：任务卡 24 卡（K01-K18 + RA-01~RA-06）状态全量回写，每卡含 S7 回写口径
  （已完成 / 已闭环 / 待联调窗口 PENDING 三者之一），PENDING 项显式标注关联断言或挂起编号；
- S7-T8-2：JT 台账七线（OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS / 前端 / SHR）
  状态与提交号全量回写归集文档，逐线含提交号或 PENDING 说明；
- S7-T8-3：文档地图 L0-L4 索引维护（S7 新增条目 + 机器清单无游离）；
- S7-T8-4：《S7-全域门禁与总收官报告》产出（段门禁六项聚合结论 / PENDING 挂起登记 /
  跨仓会签记录 / 遗留事项）；
- S7-T8-5：段门禁六项聚合自检（① RA-06 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ 三原则总验证
  ⑤ 跨仓会签 ⑥ 24 卡/JT 回写）+ gate-aggregate.json 引用 + t8 回写核对证据。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_TASK_CARD = ROOT / "OpenBase-数据隔离实现任务卡-v1.0.0.md"
_JT_BACKLOG = ROOT / "OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md"
_DOC_MAP = ROOT / "doc" / "design" / "OpenBase-文档地图索引-v1.0.0.md"
_REPORT = ROOT / "doc" / "development" / "OpenBase-S7-全域门禁与总收官报告-v1.0.0.md"
_GATE_EVIDENCE = ROOT / "doc" / "test" / "evidence" / "s7" / "gate" / "gate-aggregate.json"
_T8_EVIDENCE = ROOT / "doc" / "test" / "evidence" / "s7" / "t8" / "writeback-check.json"

# 24 卡（K01-K18 + RA-01~RA-06）
_CARD_IDS = tuple(f"K{index:02d}" for index in range(1, 19)) + tuple(
    f"RA-{index:02d}" for index in range(1, 7)
)
# 七线 JT
_JT_SUBSYSTEMS = (
    "OpenBase-JT",
    "OpenLLM-JT",
    "OpenRAG-JT",
    "OpenMemory-JT",
    "DPS-JT",
    "FE-JT",
    "SHR-JT",
)
# 段门禁六项自检顺序锚点
_GATE_SIX_ITEMS = (
    "RA-06",
    "冒烟 S0-S6",
    "对齐清单",
    "三原则",
    "会签",
    "24 卡",
)
# S7 段新增文档地图条目（SHR 脚本与契约 / K13 矩阵 / 门禁聚合脚本与证据 / S7 立项·设计·执行模板·收官报告）
_S7_DOCMAP_NEW_ENTRIES = (
    "scripts/verify-env/contract.global.json",
    "scripts/verify_env_global.ps1",
    "scripts/db/init_openbase_test.ps1",
    "scripts/db/grant_k13_accounts.ps1",
    "scripts/scan_orchestrator_bypass.py",
    "scripts/gate_aggregate.py",
    "doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md",
    "doc/design/OpenBase-文档地图索引-v1.0.0.md",
    "doc/test/evidence/s7/gate/gate-aggregate.json",
    "doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md",
    "doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md",
    "OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md",
    "OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md",
)
# 已入仓两仓（S7-T7-1/2）
_ARCHIVED_REPO_HASHES = ("9e93c1c", "a2eb92b", "8333650", "e772c01")
# OpenBase S7 段提交链
_OPENBASE_S7_HASHES = ("402ff8e", "2235229", "d3faa7f")
# 前端 S6 提交链
_FE_S6_HASHES = ("2abe52a", "aa6c5bd", "72b19da", "477eb80")
# 存量测试对齐 PG 环境性挂起
_PG_ENV_IDS = ("PG-ENV-1", "PG-ENV-2", "PG-ENV-3", "PG-ENV-4")

_CARD_HEADING = re.compile(r"^### (K\d{2}|RA-\d{2})\s", re.MULTILINE)
_JT_ROW = re.compile(
    r"^\|\s*(OpenBase-JT|OpenLLM-JT|OpenRAG-JT|OpenMemory-JT|DPS-JT|FE-JT|SHR-JT)\s*\|(.*)$",
    re.MULTILINE,
)
_MANIFEST = re.compile(
    r"<!--\s*DOCMAP-MANIFEST:BEGIN\s*-->(.*?)<!--\s*DOCMAP-MANIFEST:END\s*-->", re.DOTALL
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _task_card_blocks() -> dict[str, str]:
    """按 24 卡标题切分任务卡正文（含每卡全文块）."""
    text = _read_text(_TASK_CARD)
    matches = list(_CARD_HEADING.finditer(text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.start() : end]
    return blocks


def _writeback_line(block: str) -> str | None:
    """取卡内「S7 回写口径」行."""
    for line in block.splitlines():
        if "S7 回写口径" in line:
            return line
    return None


# ===========================================================================
# S7-T8-1：任务卡 24 卡全量回写
# ===========================================================================


def test_task_card_version_bumped_to_v180() -> None:
    """任务卡内部版本升 v1.8.0 并在修订历史登记."""
    assert _TASK_CARD.exists(), _TASK_CARD
    text = _read_text(_TASK_CARD)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.8\.0\s*\|", text), "任务卡版本未升 v1.8.0"
    assert re.search(r"\|\s*v1\.8\.0\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.8.0 条目"


def test_task_card_has_all_24_cards() -> None:
    """任务卡含 K01-K18 + RA-01~RA-06 共 24 卡（无游离/无缺失）."""
    blocks = _task_card_blocks()
    assert set(blocks) == set(_CARD_IDS), f"24 卡游离/缺失: {set(blocks) ^ set(_CARD_IDS)}"
    assert len(blocks) == 24


def test_each_card_status_non_empty_with_s7_writeback() -> None:
    """每卡状态非空且含 S7 回写口径（已完成 / 已闭环 / 待联调窗口 PENDING 三者之一）."""
    blocks = _task_card_blocks()
    for card_id, block in blocks.items():
        assert "状态" in block, f"{card_id} 缺少状态字段"
        line = _writeback_line(block)
        assert line, f"{card_id} 缺少「S7 回写口径」行"
        allowed = (
            ("已完成" in line)
            or ("已闭环" in line)
            or ("待联调窗口" in line and "PENDING" in line)
        )
        assert allowed, f"{card_id} S7 回写口径不含允许状态词: {line}"


def test_pending_cards_annotate_assertion_or_hang_id() -> None:
    """PENDING 项必须显式标注关联断言（S7-T*-*）或挂起编号（PG-ENV-*）."""
    blocks = _task_card_blocks()
    for card_id, block in blocks.items():
        line = _writeback_line(block)
        if not line or "PENDING" not in line:
            continue
        has_assertion = re.search(r"S7-T\d+-\d+", line)
        has_hang = re.search(r"PG-ENV-\d+", line)
        assert has_assertion or has_hang, f"{card_id} PENDING 未标注关联断言/挂起编号: {line}"


def test_writeback_stats_completed_22_pending_2() -> None:
    """24 卡回写统计：22 已完成/已闭环 + 2 待联调窗口 PENDING（RA-06 / K13）."""
    blocks = _task_card_blocks()
    completed: list[str] = []
    pending: list[str] = []
    for card_id, block in blocks.items():
        line = _writeback_line(block) or ""
        if "待联调窗口" in line:
            pending.append(card_id)
        elif "已完成" in line or "已闭环" in line:
            completed.append(card_id)
    assert set(pending) == {"RA-06", "K13"}, f"待联调窗口 PENDING 卡不匹配: {pending}"
    assert len(completed) == 22, f"已完成/已闭环卡数异常: {len(completed)}"
    assert len(completed) + len(pending) == 24


def test_task_card_appends_s7_summary_section() -> None:
    """卡尾追加「附：S7 段（总收官）回写摘要（2026-09-11）」并登记 S7 结论."""
    text = _read_text(_TASK_CARD)
    assert "附：S7 段（总收官）回写摘要（2026-09-11）" in text
    for marker in ("S7-T8-1", "S7-T8-5", "S7-T7-1", "PG-ENV-1"):
        assert marker in text, f"S7 回写摘要缺少 {marker}"


# ===========================================================================
# S7-T8-2：七线 JT 台账全量回写
# ===========================================================================


def test_jt_backlog_version_bumped_to_v140() -> None:
    """归集文档内部版本升 v1.4.0 并登记修订历史."""
    assert _JT_BACKLOG.exists(), _JT_BACKLOG
    text = _read_text(_JT_BACKLOG)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.4\.0\s*\|", text), "归集文档版本未升 v1.4.0"
    assert re.search(r"\|\s*v1\.4\.0\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.4.0 条目"


def test_jt_seven_lines_have_status_and_hash_or_pending() -> None:
    """七线（OpenBase/OpenLLM/OpenRAG/OpenMemory/DPS/前端/SHR）均有状态行与提交号或 PENDING 说明."""
    assert _JT_BACKLOG.exists(), _JT_BACKLOG
    text = _read_text(_JT_BACKLOG)
    rows = {match.group(1): match.group(2) for match in _JT_ROW.finditer(text)}
    assert set(rows) == set(_JT_SUBSYSTEMS), f"七线汇总行游离/缺失: {set(rows)}"
    for line_name, body in rows.items():
        assert ("✅" in body) or ("⏳" in body) or ("🚧" in body), f"{line_name} 状态缺失: {body}"
        has_hash = re.search(r"[0-9a-f]{7}", body)
        has_pending = "PENDING" in body
        assert has_hash or has_pending, f"{line_name} 无提交号且无 PENDING 说明: {body}"


def test_jt_unarchived_repos_marked_pending() -> None:
    """OpenMemory / OpenLLM 两仓登记「未入仓 PENDING」；OpenRAG / DPS 附入仓 hash."""
    text = _read_text(_JT_BACKLOG)
    rows = {match.group(1): match.group(2) for match in _JT_ROW.finditer(text)}
    assert "未入仓 PENDING" in rows["OpenMemory-JT"], rows["OpenMemory-JT"]
    assert "未入仓 PENDING" in rows["OpenLLM-JT"], rows["OpenLLM-JT"]
    for archived in ("OpenRAG-JT", "DPS-JT"):
        assert re.search(r"[0-9a-f]{7}", rows[archived]), rows[archived]
    assert "PENDING" not in rows["OpenRAG-JT"] or "已入仓" in rows["OpenRAG-JT"]


def test_jt_openbase_and_frontend_submit_chain() -> None:
    """OpenBase S7 提交链、前端 S6 提交号、已入仓两仓 hash 均可追溯."""
    text = _read_text(_JT_BACKLOG)
    for digest in _OPENBASE_S7_HASHES + _FE_S6_HASHES + _ARCHIVED_REPO_HASHES:
        assert digest in text, f"归集文档缺少提交号 {digest}"


# ===========================================================================
# S7-T8-3：文档地图维护（S7 新增条目 + 无游离）
# ===========================================================================


def test_doc_map_bumped_and_s7_entries_added() -> None:
    """文档地图索引升版并增补 S7 新增条目（SHR 脚本/契约、K13 矩阵、门禁聚合脚本与证据、S7 文档）."""
    assert _DOC_MAP.exists(), _DOC_MAP
    text = _read_text(_DOC_MAP)
    assert "v1.0.1" in text, "文档地图索引未升版"
    missing = [entry for entry in _S7_DOCMAP_NEW_ENTRIES if entry not in text]
    assert not missing, f"文档地图未增补 S7 条目: {missing}"


def test_doc_map_manifest_entries_exist_no_orphan() -> None:
    """机器清单（DOCMAP-MANIFEST）同步更新且逐项真实存在（无游离文档/无失效引用）."""
    text = _read_text(_DOC_MAP)
    block = _MANIFEST.search(text)
    assert block, "文档地图缺少 DOCMAP-MANIFEST 区块"
    entries = re.findall(r"^-\s+(\S+\.(?:md|json|ps1|py))\s*$", block.group(1), re.MULTILINE)
    assert entries, "机器清单为空"
    missing = [entry for entry in entries if not (ROOT / entry).exists()]
    assert not missing, f"文档地图清单存在游离项: {missing}"
    assert "doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md" in entries
    assert "doc/test/evidence/s7/gate/gate-aggregate.json" in entries


# ===========================================================================
# S7-T8-4：总收官报告
# ===========================================================================


def test_report_exists_with_metadata() -> None:
    """总收官报告存在，单文件形态，状态 [Review]，含元信息与修订历史."""
    assert _REPORT.exists(), f"缺少总收官报告: {_REPORT}"
    text = _read_text(_REPORT)
    assert "OpenBase-S7-全域门禁与总收官报告-v1.0.0" in text
    assert re.search(r"\|\s*状态\s*\|\s*\[Review\]", text), "报告状态非 [Review]"
    assert re.search(r"\|\s*版本\s*\|\s*v1\.0\.0\s*\|", text)
    assert "修订历史" in text


def test_report_has_six_item_aggregated_selfcheck() -> None:
    """报告含段门禁六项聚合自检表（① RA-06 ② 冒烟 S0-S6 ③ 对齐清单 ④ 三原则 ⑤ 会签 ⑥ 24 卡/JT）."""
    text = _read_text(_REPORT)
    assert "段门禁六项聚合自检" in text
    for marker in _GATE_SIX_ITEMS:
        assert marker in text, f"六项自检缺少 {marker}"
    for evidence in ("gate-aggregate.json", "doc/test/evidence/s7"):
        assert evidence in text, f"六项自检缺少证据索引 {evidence}"


def test_report_pending_register_merges_all_sources() -> None:
    """PENDING 挂起登记合并段级 10 条 + S7 自身 + PG-ENV-1~4."""
    text = _read_text(_REPORT)
    assert "PENDING" in text
    for marker in _PG_ENV_IDS:
        assert marker in text, f"挂起登记缺少 {marker}"
    for marker in ("段级", "10 条", "B1", "B6"):
        assert marker in text, f"段级挂起登记缺少 {marker}"
    for marker in ("S7-T2-1", "S7-T3-1", "S7-T4-1", "S7-T5-1", "S7-T7-1"):
        assert marker in text, f"S7 自身挂起缺少 {marker}"


def test_report_signoff_record_with_hashes_and_pending() -> None:
    """跨仓会签记录含已入仓两仓 hash + 未入仓两仓 PENDING + 五步流程状态."""
    text = _read_text(_REPORT)
    for digest in _ARCHIVED_REPO_HASHES:
        assert digest in text, f"会签记录缺少已入仓 hash {digest}"
    assert text.count("未入仓 PENDING") >= 2, "未入仓两仓 PENDING 登记不足"
    for marker in ("五步", "会签"):
        assert marker in text, f"会签记录缺少 {marker}"


def test_report_legacy_and_conclusion() -> None:
    """报告含遗留事项，且结论如实（段门禁整体未达最终通过）."""
    text = _read_text(_REPORT)
    assert "遗留事项" in text
    assert "段门禁整体未达最终通过" in text


# ===========================================================================
# S7-T8-5：证据引用同步 + t8 回写核对证据
# ===========================================================================


def test_gate_evidence_references_report_and_t8() -> None:
    """gate-aggregate.json 同步 SHR/报告引用（设计草案 §5 报告落点口径）."""
    assert _GATE_EVIDENCE.exists(), _GATE_EVIDENCE
    evidence = _load_json(_GATE_EVIDENCE)
    assert evidence.get("s7_report_ref") == (
        "doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md"
    ), "gate 证据缺少 S7 报告引用"
    assert evidence.get("t8_evidence_ref") == (
        "doc/test/evidence/s7/t8/writeback-check.json"
    ), "gate 证据缺少 t8 证据引用"
    assert evidence.get("shr_ref"), "gate 证据缺少 SHR 引用"


def test_t8_evidence_file_valid_with_coverage_counts() -> None:
    """t8 回写核对证据 JSON 存在且含 24 卡覆盖数 / 七线覆盖数 / 无游离数 / 报告章节齐备性."""
    assert _T8_EVIDENCE.exists(), f"缺少 t8 回写核对证据: {_T8_EVIDENCE}"
    evidence = _load_json(_T8_EVIDENCE)
    assert evidence["schema_version"] == 1
    assert evidence["evidence_ref"] == "S7-T8"
    assert evidence["status"] in {"PASS", "PENDING", "FAIL"}
    assert evidence["execution_face"] == "A"
    assert evidence["generated_at"]
    assert evidence["openbase_commit"] and len(evidence["openbase_commit"]) >= 7
    coverage = evidence["coverage"]
    assert coverage["task_cards_total"] == 24
    assert coverage["task_cards_completed"] + coverage["task_cards_pending"] == 24
    assert coverage["task_cards_pending"] >= 1
    assert coverage["jt_lines_total"] == 7
    assert coverage["jt_lines_with_hash_or_pending"] == 7
    assert coverage["doc_map_new_entries"] >= len(_S7_DOCMAP_NEW_ENTRIES)
    assert coverage["doc_map_orphan_count"] == 0
    assert coverage["report_sections_total"] >= 6
    assert coverage["report_pending_register_items"] >= 4
