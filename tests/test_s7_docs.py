"""S7 段 DevLogReport / 测试报告文档一致性断言（轻量）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》§4（34 断言 S7-T1-1~S7-T8-5）、
§5.5 报告落点、§8 里程碑交付物清单；《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0》§4/§8。

断言口径（纯文档面 A 面；禁止伪造）：
- 两份文档（DevLogReport / 测试报告）存在且状态 [Review]；
- 两文档合集含 **34 条断言 ID 全集**（逐 ID 检查），且测试报告单独含全部 34 条；
- 测试报告含「段门禁六项」小节（① RA-06 ② 冒烟 S0-S6 ③ 对齐清单 ④ 三原则 ⑤ 会签 ⑥ 24 卡）；
- 两文档合集含 PENDING 登记与提交链（`402ff8e` / `2235229` / `d3faa7f` / `2d97d1a` / `a5020fa`）；
- 文档地图索引已含这两份新文档条目（v1.0.2）且 MANIFEST 逐项真实存在。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_DEVLOG = (
    ROOT
    / "doc"
    / "development"
    / "OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md"
)
_TEST_REPORT = ROOT / "doc" / "test" / "OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md"
_DOC_MAP = ROOT / "doc" / "design" / "OpenBase-文档地图索引-v1.0.0.md"

# 34 条断言 ID 全集（S7-T1-1 ~ S7-T8-5，与设计草案 §4.9 1:1）
_ASSERTION_IDS = (
    *(f"S7-T1-{index}" for index in range(1, 6)),
    *(f"S7-T2-{index}" for index in range(1, 5)),
    *(f"S7-T3-{index}" for index in range(1, 5)),
    *(f"S7-T4-{index}" for index in range(1, 5)),
    *(f"S7-T5-{index}" for index in range(1, 5)),
    *(f"S7-T6-{index}" for index in range(1, 5)),
    *(f"S7-T7-{index}" for index in range(1, 5)),
    *(f"S7-T8-{index}" for index in range(1, 6)),
)
# 段门禁六项标记
_GATE_SIX_ITEMS = ("RA-06", "冒烟 S0-S6", "对齐清单", "三原则", "会签", "24 卡")
# OpenBase S7 段提交链
_COMMIT_CHAIN = ("402ff8e", "2235229", "d3faa7f", "2d97d1a", "a5020fa")
# 两份新文档在文档地图索引中的路径
_DOC_MAP_ENTRIES = (
    "doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md",
    "doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md",
)

_MANIFEST = re.compile(
    r"<!--\s*DOCMAP-MANIFEST:BEGIN\s*-->(.*?)<!--\s*DOCMAP-MANIFEST:END\s*-->",
    re.DOTALL,
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_devlog_and_test_report_exist_with_review_status() -> None:
    """两份文档存在，含文档编号、修订历史，状态均为 [Review]."""
    assert _DEVLOG.exists(), f"缺少 DevLogReport: {_DEVLOG}"
    assert _TEST_REPORT.exists(), f"缺少测试报告: {_TEST_REPORT}"

    devlog_text = _read_text(_DEVLOG)
    report_text = _read_text(_TEST_REPORT)

    assert "OB-S7-DEVLOG-v1.0.0" in devlog_text, "DevLogReport 缺少文档编号"
    assert "OB-S7-TEST-v1.0.0" in report_text, "测试报告缺少文档编号"
    assert re.search(r"\|\s*状态\s*\|\s*\[Review\]", devlog_text), "DevLogReport 状态非 [Review]"
    assert re.search(r"\|\s*状态\s*\|\s*\[Review\]", report_text), "测试报告状态非 [Review]"
    assert "修订历史" in devlog_text and "修订历史" in report_text


def test_assertion_ids_complete_across_docs() -> None:
    """两文档合集含 34 条断言 ID 全集（逐 ID 检查，无游离/无缺失）."""
    combined = _read_text(_DEVLOG) + _read_text(_TEST_REPORT)
    missing = [assertion_id for assertion_id in _ASSERTION_IDS if assertion_id not in combined]
    assert not missing, f"两文档合集缺少断言 ID: {missing}"
    assert len(_ASSERTION_IDS) == 34, "断言 ID 清单应为 34 条"


def test_test_report_contains_full_assertion_matrix() -> None:
    """测试报告单独含 34 条断言 ID 全集（逐条状态矩阵）."""
    text = _read_text(_TEST_REPORT)
    missing = [assertion_id for assertion_id in _ASSERTION_IDS if assertion_id not in text]
    assert not missing, f"测试报告缺少断言 ID: {missing}"


def test_test_report_contains_six_gate_items() -> None:
    """测试报告含「段门禁六项」小节与六项标记（① RA-06 ② 冒烟 S0-S6 ③ 对齐清单 ④ 三原则 ⑤ 会签 ⑥ 24 卡）."""
    text = _read_text(_TEST_REPORT)
    assert "段门禁六项" in text, "测试报告缺少「段门禁六项」小节"
    for marker in _GATE_SIX_ITEMS:
        assert marker in text, f"段门禁六项缺少标记: {marker}"
    for evidence in ("gate-aggregate.json", "writeback-check.json"):
        assert evidence in text, f"段门禁六项缺少证据索引: {evidence}"


def test_docs_contain_pending_register_and_commit_chain() -> None:
    """两文档合集含 PENDING 登记与 S7 段提交链（402ff8e/2235229/d3faa7f/2d97d1a/a5020fa）."""
    combined = _read_text(_DEVLOG) + _read_text(_TEST_REPORT)
    assert "PENDING" in combined, "文档缺少 PENDING 登记"
    for digest in _COMMIT_CHAIN:
        assert digest in combined, f"文档缺少提交链 hash: {digest}"


def test_doc_map_index_includes_new_docs() -> None:
    """文档地图索引已含两份新文档条目（升版 v1.0.2）且 MANIFEST 逐项真实存在."""
    assert _DOC_MAP.exists(), f"缺少文档地图索引: {_DOC_MAP}"
    text = _read_text(_DOC_MAP)
    assert "v1.0.2" in text, "文档地图索引未升版 v1.0.2"
    missing = [entry for entry in _DOC_MAP_ENTRIES if entry not in text]
    assert not missing, f"文档地图索引未含新文档条目: {missing}"

    block = _MANIFEST.search(text)
    assert block, "文档地图缺少 DOCMAP-MANIFEST 区块"
    entries = re.findall(r"^-\s+(\S+\.(?:md|json|ps1|py))\s*$", block.group(1), re.MULTILINE)
    assert entries, "机器清单为空"
    for entry in _DOC_MAP_ENTRIES:
        assert entry in entries, f"MANIFEST 缺少新文档条目: {entry}"
    manifest_missing = [entry for entry in entries if not (ROOT / entry).exists()]
    assert not manifest_missing, f"文档地图清单存在游离项: {manifest_missing}"
