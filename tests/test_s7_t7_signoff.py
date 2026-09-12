"""S7-T7 跨仓入仓核验与会签汇总断言（执行模板填报 / 七线 JT 入仓口径修正 / 清单升版 / 收官报告修正 / 卡尾 hash 回填）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》（内部 v1.0.1 [Approved]）
§4.7（S7-T7-1 ~ S7-T7-4）、§1.2（Q-S7-D10 会签汇总表落点）、§5；执行件
`doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md`（内部 v1.0.2 [Approved]）；
`doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md`（内部 v1.0.8 [Approved]）§4.1 会签五步；
`doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`（内部 v1.0.9 [Approved]）§0/§7。

四仓入仓实测事实（2026-09-11 本地实测，本批以此为准并修正批次 3 过时口径）：
- OpenRAG：`release/v1.10.0` @ `a2eb92b`（`9e93c1c`/`0bda158`/`f48ea08`/`5fafc0a` + 修复 `b809c04` + 回填 `a2eb92b`），三远端同步，勾稽 A 类差异 0；
- DPS：`main` @ `e772c01`（`8333650`/`45a5ea4`/`1dc5f94`/`14d3111` + 回填 `e772c01`），三远端同步，勾稽 A 类差异 0；
- OpenMemory：`release/v7.3.0` @ `cc7c06f`（`000a154` v7.2 基线 / `fbc8326` S2 五文档 / `90cbe37` S2 源码与迁移 / `a4a0059` 测试与 CI / `1348229` lint 债 / `cc7c06f` .devflow 移出版本控制），origin/backup/github 三端已同步 `cc7c06f`，勾稽 A 类回读完成（差异 0）；
- OpenLLM：`feature/s4-identity-channel-b` @ `be1886d`（批 1 `656d179`/批 2 `6d8b189`/批 3 `2ef6601`/批 4 `640f250`/批 5 `c310c38`/批 6 `24d4484` + 手册留档 `64ef68f`/`e366e50`/`be1886d`；need-star 独立分支 `feature/need-star-orchestration` @ `ce40f90`），origin/backup/github 三端已同步 `be1886d`/`ce40f90`，`jerry.yu` 受限 PENDING，勾稽 A 类差异 0。

断言口径（沙箱可判定面 / A 面 + 联调窗口必需面 / B 面；禁伪造 hash 与通过）：
- S7-T7-1：四仓入仓完成 + 实 hash 回填（远端推送受限则如实登记 PENDING）；
- S7-T7-2：四仓勾稽 A 类差异 = 0（受限则登记 PENDING 并按残余分类说明）；
- S7-T7-3：会签记录形成（总清单 §4.1 五步 + K02/K07/K13 与接口一致性评审）；
- S7-T7-4：放行清单 / 清点总清单升版 [Approved]。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_TEMPLATE = ROOT / "doc" / "planning" / "OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md"
_SUMMARY_TABLE = (
    ROOT / "doc" / "planning" / "OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md"
)
_CLEARANCE = ROOT / "doc" / "planning" / "OpenBase-联调产物清点核对总清单-v1.0.0.md"
_RELEASE = (
    ROOT / "doc" / "development" / "OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md"
)
_REPORT = (
    ROOT / "doc" / "development" / "OpenBase-S7-全域门禁与总收官报告-v1.0.0.md"
)
_JT_BACKLOG = ROOT / "OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md"
_TASK_CARD = ROOT / "OpenBase-数据隔离实现任务卡-v1.0.0.md"
_T7_EVIDENCE = ROOT / "doc" / "test" / "evidence" / "s7" / "t7" / "signoff-check.json"
_GATE_EVIDENCE = ROOT / "doc" / "test" / "evidence" / "s7" / "gate" / "gate-aggregate.json"

# 四仓入仓实测事实（HEAD + 批次 hash + 远端同步 + 勾稽）
_REPO_HEAD = {
    "OpenRAG": "a2eb92b",
    "DPS": "e772c01",
    "OpenMemory": "cc7c06f",
    "OpenLLM": "be1886d",
}
_REPO_BATCH_HASHES = {
    "OpenRAG": ("9e93c1c", "0bda158", "f48ea08", "5fafc0a", "b809c04", "a2eb92b"),
    "DPS": ("8333650", "45a5ea4", "1dc5f94", "14d3111", "e772c01"),
    "OpenMemory": (
        "000a154",
        "fbc8326",
        "90cbe37",
        "a4a0059",
        "1348229",
        "cc7c06f",
    ),
    "OpenLLM": (
        "656d179",
        "6d8b189",
        "2ef6601",
        "640f250",
        "c310c38",
        "24d4484",
        "64ef68f",
        "e366e50",
        "be1886d",
    ),
}
_REPO_BRANCH = {
    "OpenRAG": "release/v1.10.0",
    "DPS": "main",
    "OpenMemory": "release/v7.3.0",
    "OpenLLM": "feature/s4-identity-channel-b",
}
_REMOTE_SYNC = {
    "OpenRAG": "origin/backup/github",
    "DPS": "origin/backup/github",
    "OpenMemory": "origin/backup/github",
    "OpenLLM": "origin/backup/github",
}
# 会签五步锚点（总清单 §4.1）
_SIGNOFF_STEPS = ("①", "②", "③", "④", "⑤")
# S7-T7 断言锚点
_T7_ASSERTIONS = ("S7-T7-1", "S7-T7-2", "S7-T7-3", "S7-T7-4")
# 跨系统卡
_CROSS_CARDS = ("K02", "K07", "K13")
# 模板逐仓填报区（§1 前置裁断为会签前置，非本批填报面；§8 遗留登记）
_FILLED_SECTIONS = ("§2", "§3", "§4", "§5", "§6", "§7")

_SECTION_HEADING = re.compile(r"^## (§\d[^\n]*)$", re.MULTILINE)
_JT_ROW = re.compile(r"^\|\s*(OpenMemory-JT|OpenLLM-JT)\s*\|(.*)$", re.MULTILINE)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _section(text: str, key: str) -> str:
    """按 `## §N ...` 二级标题切分章节正文（含标题行）."""
    marks = list(_SECTION_HEADING.finditer(text))
    for index, match in enumerate(marks):
        if match.group(1).startswith(key):
            start = match.start()
            end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
            return text[start:end]
    raise AssertionError(f"文档缺少章节 {key}")


# ===========================================================================
# ① 执行模板：四仓填报位均已填写（§2 / §3 / §4 / §5 / §6 / §7）
# ===========================================================================


def test_template_version_and_status_bumped() -> None:
    """执行模板内部版本升 v1.0.2、状态 [Approved]，并在修订历史登记."""
    assert _TEMPLATE.exists(), _TEMPLATE
    text = _read_text(_TEMPLATE)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.0\.2\s*\|", text), "执行模板未升 v1.0.2"
    assert re.search(r"\|\s*状态\s*\|\s*\[Approved\]", text), "执行模板状态非 [Approved]"
    assert re.search(r"\|\s*v1\.0\.2\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.2 条目"


def test_template_no_unfilled_cells_in_required_sections() -> None:
    """§2/§3/§4/§5/§6/§7 逐仓填报位全部填写（无残留「待填」占位）."""
    text = _read_text(_TEMPLATE)
    offenders: list[str] = []
    for key in _FILLED_SECTIONS:
        if "待填" in _section(text, key):
            offenders.append(key)
    assert not offenders, f"以下章节仍残留未填占位: {offenders}"


def test_template_batch_hashes_and_regression_filled() -> None:
    """§2 逐仓入仓表填入四仓（含 OpenMemory/OpenLLM）批次 hash 与回归结果."""
    section = _section(_read_text(_TEMPLATE), "§2")
    for repo, hashes in _REPO_BATCH_HASHES.items():
        assert _REPO_HEAD[repo] in section, f"§2 缺少 {repo} HEAD {_REPO_HEAD[repo]}"
        for digest in hashes:
            assert digest in section, f"§2 缺少 {repo} 批次 hash {digest}"
    # OpenLLM 回归结果（含 .env 环境项说明）
    assert "1981 passed" in section, "§2 缺少 OpenLLM 回归结果（1981 passed）"
    assert "11/11" in section, "§2 缺少 OpenLLM .env 环境项覆盖后 11/11 通过说明"


def test_template_redlines_checked_per_repo() -> None:
    """§3 入仓红线逐仓勾选（含 OpenLLM need-star 隔离、OpenMemory .devflow 处置）."""
    section = _section(_read_text(_TEMPLATE), "§3")
    assert "√" in section, "§3 红线未出现勾选标记 √"
    assert "need-star" in section, "§3 缺少 OpenLLM need-star 隔离红线"
    assert ".devflow" in section, "§3 缺少 OpenMemory .devflow 处置红线"


def test_template_reconciliation_rows_filled() -> None:
    """§4.1 勾稽核对表四仓行回填（A 类差异 = 0 / 受限 PENDING）."""
    section = _section(_read_text(_TEMPLATE), "§4")
    for repo in _REPO_HEAD:
        assert _REPO_HEAD[repo] in section, f"§4.1 缺少 {repo} 入仓后 HEAD {_REPO_HEAD[repo]}"
    assert "A 类差异" in section
    assert section.count("0") >= 3, "§4.1 勾稽结果未回填（A 类差异 0 记录不足）"


def test_template_hash_backfill_table_filled() -> None:
    """§5 hash 回填表四仓行填写（含回填位置实际执行状态）."""
    section = _section(_read_text(_TEMPLATE), "§5")
    for repo, hashes in _REPO_BATCH_HASHES.items():
        for digest in hashes:
            assert digest in section, f"§5 回填表缺少 {repo} hash {digest}"
    assert "已回填" in section, "§5 回填表未登记回填完成状态"
    assert "任务卡" in section, "§5 回填表缺少回填位置（任务卡卡尾）"


def test_template_signoff_five_steps_filled() -> None:
    """§6 会签记录五步逐项填写（含 K02/K07/K13 与接口一致性评审、清单升版）."""
    section = _section(_read_text(_TEMPLATE), "§6")
    for step in _SIGNOFF_STEPS:
        assert step in section, f"§6 缺少会签步骤 {step}"
    for card in _CROSS_CARDS:
        assert card in section, f"§6 缺少跨系统卡 {card}"
    assert "gate-aggregate" in section, "§6 第④步缺少 gate-aggregate.json K07 计数对账引用"
    assert "接口一致性" in section, "§6 第④步缺少接口一致性评审"
    assert "清单升版" in section, "§6 第⑤步缺少清单升版"


def test_template_t7_assertions_concluded() -> None:
    """§7 S7-T7-1~4 结论逐条填写（部分达成 / 达成，非「待填」）."""
    section = _section(_read_text(_TEMPLATE), "§7")
    for assertion in _T7_ASSERTIONS:
        assert assertion in section, f"§7 缺少断言 {assertion}"
    assert section.count("部分达成") >= 2, "§7 未登记 T7-1/T7-2 部分达成结论"
    assert "远端" in section and "PENDING" in section, "§7 未登记远端推送 PENDING"


# ===========================================================================
# ② 归集文档 §3.9 七线 JT：OpenMemory/OpenLLM 行更新为「已入仓（本地提交完成）」
# ===========================================================================


def test_jt_backlog_version_bumped() -> None:
    """归集文档内部版本升 v1.6.0 并在修订历史登记."""
    assert _JT_BACKLOG.exists(), _JT_BACKLOG
    text = _read_text(_JT_BACKLOG)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.6\.0\s*\|", text), "归集文档版本未升 v1.6.0"
    assert re.search(r"\|\s*v1\.6\.0\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.6.0 条目"


def test_jt_backlog_section_3_9_all_four_repos_archived() -> None:
    """§3.9 四仓均「已入仓」且携带分支/HEAD/批次 hash；不再有「未入仓」口径."""
    text = _read_text(_JT_BACKLOG)
    section = text[text.index("### 3.9") : text.index("## 4. 执行与版本管理规则")]
    assert "未入仓" not in section, "§3.9 仍残留批次 3 过时「未入仓」口径"
    rows = {match.group(1): match.group(2) for match in _JT_ROW.finditer(section)}
    for repo_row in ("OpenMemory-JT", "OpenLLM-JT"):
        assert repo_row in rows, f"§3.9 缺少 {repo_row} 行"
        assert "已入仓（本地提交完成）" in rows[repo_row], rows[repo_row]
    for repo, head in _REPO_HEAD.items():
        assert head in section, f"§3.9 缺少 {repo} HEAD {head}"
    for repo in _REPO_HEAD:
        assert _REPO_BRANCH[repo] in section, f"§3.9 缺少 {repo} 分支"


def test_jt_backlog_remote_sync_status_per_repo() -> None:
    """§3.9 远端同步状态逐仓登记（OM/LL 三远端已同步；LL jerry.yu 受限 PENDING）."""
    text = _read_text(_JT_BACKLOG)
    section = text[text.index("### 3.9") : text.index("## 4. 执行与版本管理规则")]
    rows = {match.group(1): match.group(2) for match in _JT_ROW.finditer(section)}
    memory_row = rows["OpenMemory-JT"]
    assert "origin" in memory_row and "backup" in memory_row, memory_row
    assert "github" in memory_row and "三端已同步" in memory_row, memory_row
    llm_row = rows["OpenLLM-JT"]
    for remote in ("origin", "backup", "github", "jerry.yu"):
        assert remote in llm_row, f"OpenLLM-JT 行缺少远端 {remote}"
    assert "已同步" in llm_row and "PENDING" in llm_row, llm_row
    assert "ce40f90" in llm_row, "OpenLLM-JT 行缺少 need-star 独立分支提交号"
    assert "A 类差异 0" in memory_row, "OpenMemory 勾稽回读结论未登记（A 类差异 0）"


# ===========================================================================
# ③ 清单升版：[Approved] + 四仓入仓完成登记
# ===========================================================================


def test_release_checklist_approved_with_signoff() -> None:
    """放行清单升 v1.0.9 [Approved]，登记四仓入仓完成与会签结论."""
    assert _RELEASE.exists(), _RELEASE
    text = _read_text(_RELEASE)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.0\.9\s*\|", text), "放行清单版本未升 v1.0.9"
    assert re.search(r"\|\s*状态\s*\|\s*\[Approved\]", text), "放行清单状态非 [Approved]"
    assert re.search(r"\|\s*v1\.0\.9\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.9 条目"
    assert "S7-T7" in text and "会签" in text, "放行清单缺少 S7-T7 会签登记"


def test_clearance_checklist_approved_with_four_repo_registration() -> None:
    """清点总清单升 v1.0.8 [Approved]，新增四仓入仓完成登记（分支/HEAD/勾稽/远端）."""
    assert _CLEARANCE.exists(), _CLEARANCE
    text = _read_text(_CLEARANCE)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.0\.8\s*\|", text), "清点总清单版本未升 v1.0.8"
    assert re.search(r"\|\s*状态\s*\|\s*\[Approved\]", text), "清点总清单状态非 [Approved]"
    assert re.search(r"\|\s*v1\.0\.8\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.8 条目"
    assert "### 5.10" in text, "清点总清单缺少 §5.10 四仓入仓完成登记"
    for repo, head in _REPO_HEAD.items():
        assert head in text, f"清点总清单缺少 {repo} HEAD {head}"
    assert "A 类差异" in text, "清点总清单缺少勾稽 A 类差异口径"


# ===========================================================================
# ④ 总收官报告修正（不再有「未入仓」，改为四仓入仓完成）
# ===========================================================================


def test_report_corrected_four_repos_archived() -> None:
    """总收官报告内部版本升 v1.0.9（DPS 豁免续期入库回填），且不再保留「未入仓」过时口径."""
    assert _REPORT.exists(), _REPORT
    text = _read_text(_REPORT)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.0\.9\s*\|", text), "总收官报告未升内部 v1.0.9"
    assert re.search(r"\|\s*v1\.0\.9\s*\|\s*2026-09-13\s*\|", text), "修订历史缺少 v1.0.9 条目"
    assert re.search(r"\|\s*v1\.0\.8\s*\|\s*2026-09-12\s*\|", text), "修订历史缺少 v1.0.8 条目（历史保留）"
    assert re.search(r"\|\s*v1\.0\.7\s*\|\s*2026-09-12\s*\|", text), "修订历史缺少 v1.0.7 条目（历史保留）"
    assert re.search(r"\|\s*v1\.0\.6\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.6 条目（历史保留）"
    assert re.search(r"\|\s*v1\.0\.5\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.5 条目（历史保留）"
    assert re.search(r"\|\s*v1\.0\.4\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.4 条目（历史保留）"
    assert re.search(r"\|\s*v1\.0\.3\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.0.3 条目（历史保留）"
    assert "未入仓" not in text, "总收官报告仍残留「未入仓」过时口径"


def test_report_records_remote_sync_and_reconciliation() -> None:
    """报告登记四仓入仓完成：OM/LL 三远端已同步、jerry.yu 受限 PENDING + 勾稽差异 0."""
    text = _read_text(_REPORT)
    assert "四仓入仓完成" in text, "报告未登记「四仓入仓完成」"
    assert "github" in text and "三端已同步" in text, "报告未登记 OpenMemory github 三端已同步"
    assert "jerry.yu" in text and "PENDING" in text, "报告未登记 OpenLLM jerry.yu 受限 PENDING"
    assert "勾稽" in text, "报告缺少勾稽状态"
    assert "已入仓（本地提交完成）" in text, "报告未登记两仓「已入仓（本地提交完成）」"
    assert "段门禁整体未达最终通过" in text, "报告结论口径被误改（应保持未达最终通过）"


def test_summary_table_exists_with_four_repos() -> None:
    """Q-S7-D10 会签汇总核对表存在，含四仓 hash 与会签五步结论."""
    assert _SUMMARY_TABLE.exists(), f"缺少会签汇总核对表: {_SUMMARY_TABLE}"
    text = _read_text(_SUMMARY_TABLE)
    for repo in _REPO_HEAD:
        assert repo in text, f"汇总核对表缺少 {repo}"
    for step in _SIGNOFF_STEPS:
        assert step in text, f"汇总核对表缺少会签步骤 {step}"
    assert "[Approved]" in text, "汇总核对表缺少清单升版 [Approved] 登记"


# ===========================================================================
# ⑤ 任务卡卡尾 S2/S3/S4/S5 摘要含入仓 hash 回填
# ===========================================================================


def test_task_card_version_bumped_and_summaries_filled() -> None:
    """任务卡内部版本升 v1.10.0，卡尾 S2/S3/S4/S5 摘要含入仓 hash 回填."""
    assert _TASK_CARD.exists(), _TASK_CARD
    text = _read_text(_TASK_CARD)
    assert re.search(r"\|\s*版本\s*\|\s*v1\.10\.0\s*\|", text), "任务卡版本未升 v1.10.0"
    assert re.search(r"\|\s*v1\.10\.0\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.10.0 条目"
    assert re.search(r"\|\s*v1\.9\.0\s*\|\s*2026-09-11\s*\|", text), "修订历史缺少 v1.9.0 条目（历史保留）"
    # S2（OpenMemory）入仓 hash 回填
    for digest in ("000a154", "fbc8326", "90cbe37", "a4a0059", "1348229", "cc7c06f"):
        assert digest in text, f"任务卡 S2 摘要缺少入仓 hash {digest}"
    assert "release/v7.3.0" in text, "任务卡 S2 摘要缺少 OpenMemory 入仓分支"
    # S3/S4/S5 既有入仓 hash 保持
    for digest in ("9e93c1c", "a2eb92b", "656d179", "be1886d", "8333650", "e772c01"):
        assert digest in text, f"任务卡卡尾摘要缺少入仓 hash {digest}"


def test_task_card_s7_summary_reflects_archived() -> None:
    """任务卡 S7 回写摘要七线 JT 表登记 OpenMemory/OpenLLM 已入仓与远端状态."""
    text = _read_text(_TASK_CARD)
    section = text[text.index("### 2. 七线 JT 状态（S7-T8-2）") : text.index("### 3. 文档地图与证据")]
    assert "未入仓" not in section, "任务卡 S7 摘要仍残留「未入仓」口径"
    assert "OpenMemory-JT" in section and "cc7c06f" in section, "任务卡摘要缺 OpenMemory 入仓"
    assert "OpenLLM-JT" in section and "be1886d" in section, "任务卡摘要缺 OpenLLM 入仓"


# ===========================================================================
# 证据：signoff-check.json + gate-aggregate.json 引用
# ===========================================================================


def test_t7_evidence_file_valid() -> None:
    """t7 会签核对证据 JSON 存在且字段齐备（四仓 / 清单升版 / 会签五步 / T7 断言）."""
    assert _T7_EVIDENCE.exists(), f"缺少 t7 会签核对证据: {_T7_EVIDENCE}"
    evidence = _load_json(_T7_EVIDENCE)
    assert evidence["schema_version"] == 1
    assert evidence["evidence_ref"] == "S7-T7"
    assert evidence["status"] in {"PASS", "PENDING", "FAIL"}
    assert evidence["generated_at"]
    assert len(evidence["openbase_commit"]) >= 7
    repos = evidence["repos"]
    assert set(repos) == set(_REPO_HEAD), f"证据四仓游离/缺失: {set(repos)}"
    for repo, head in _REPO_HEAD.items():
        assert repos[repo]["head"] == head, repos[repo]
        assert repos[repo]["branch"] == _REPO_BRANCH[repo], repos[repo]
        assert repos[repo]["remote_sync"], repos[repo]
        assert "reconciliation" in repos[repo], repos[repo]
    assert evidence["list_upgrade"]["release"] == "v1.0.9 [Approved]"
    assert evidence["list_upgrade"]["clearance"] == "v1.0.7 [Approved]"
    assert len(evidence["signoff_five_steps"]) == 5
    assert len(evidence["t7_assertions"]) == 4


def test_gate_evidence_references_t7() -> None:
    """gate-aggregate.json 增补 t7 会签核对证据引用（保持既有字段不变）."""
    assert _GATE_EVIDENCE.exists(), _GATE_EVIDENCE
    evidence = _load_json(_GATE_EVIDENCE)
    assert evidence.get("t7_evidence_ref") == (
        "doc/test/evidence/s7/t7/signoff-check.json"
    ), "gate 证据缺少 t7 会签核对引用"
    # 既有引用（t8 测试已断言）保持
    assert evidence.get("s7_report_ref") == (
        "doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md"
    )
    assert evidence.get("t8_evidence_ref") == (
        "doc/test/evidence/s7/t8/writeback-check.json"
    )
