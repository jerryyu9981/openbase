"""S7 联调窗口工具脚本骨架断言（L1-1 / L2-1 / L2-2 / L3-1 / L3-2）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》§4.2~§4.5（S7-T2-1~4 /
S7-T3-1~4 / S7-T4-1~4 / S7-T5-1~4）、§5 证据与报告规范（``doc/test/evidence/s7/**``
目录结构、PENDING 登记、禁伪造）。

工具脚本（骨架 + 干跑形态；真实执行仍需联调窗口）：
- ``scripts/verify_l1_1_cascade.ps1``   → S7-T2（``doc/test/evidence/s7/l1-1/cascade-result.json``）
- ``scripts/drill_l2_1_failover.ps1``   → S7-T3（``doc/test/evidence/s7/l2-1/failover-drill.json``）
- ``scripts/finalize_l2_2_matrix.py``   → S7-T4（``doc/test/evidence/s7/l2-2/matrix-finalize.json``）
- ``scripts/verify_l3_1_agent.ps1``     → S7-T5（``doc/test/evidence/s7/l3-1/agent-e2e.json``）
- ``scripts/smoke_l3_2.py``             → L3-2 贯通冒烟（``doc/test/evidence/s7/l3-2/smoke-result.json``）

断言口径（沙箱可判定面；禁伪造）：
- 五脚本存在，PowerShell 脚本 Parser 语法 0 错误；
- 干跑可执行（PowerShell ``-DryRun`` / Python ``--dry-run``）；
- 干跑产出结构化证据 JSON，必含 ``schema_version`` / ``tool`` / ``mode`` / ``status`` /
  ``checks`` / ``exit_code`` / ``generated_at`` / ``commit`` 字段；
- 无真实环境（PG/Redis/IdP/四仓运行态）时 ``status=PENDING``，且退出码符合统一约定
  （``0=PASS`` / ``1=FAIL`` / ``2=PENDING``）；
- 每脚本 ``checks`` 内 ``id`` 字段须与设计断言编号一一映射；
- 仓内默认证据落点已登记 ``PENDING``（B 面未真实执行项不写假 hash / 不写假响应码）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
_DOC_MAP = ROOT / "doc" / "design" / "OpenBase-文档地图索引-v1.0.0.md"
_EXECUTION_ORDER = ROOT / "doc" / "planning" / "OpenBase-S7-沙箱外执行单-v1.0.0.md"

# 统一退出码约定（0=PASS / 1=FAIL / 2=PENDING）
_EXIT_PASS = 0
_EXIT_FAIL = 1
_EXIT_PENDING = 2
_STATUS_TO_EXIT = {"PASS": _EXIT_PASS, "FAIL": _EXIT_FAIL, "PENDING": _EXIT_PENDING}
_VALID_STATUS = frozenset(_STATUS_TO_EXIT)

_REQUIRED_FIELDS = (
    "schema_version",
    "tool",
    "mode",
    "status",
    "checks",
    "exit_code",
    "generated_at",
    "commit",
)

# 五脚本规格（脚本 / 形态 / 关联任务 / 断言编号映射 / 证据落点 / 干跑参数）
_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "key": "l1_1",
        "kind": "powershell",
        "script": "verify_l1_1_cascade.ps1",
        "task": "S7-T2",
        "check_ids": ("S7-T2-1", "S7-T2-2", "S7-T2-3", "S7-T2-4"),
        "evidence_rel": "doc/test/evidence/s7/l1-1/cascade-result.json",
        "evidence_name": "cascade-result.json",
    },
    {
        "key": "l2_1",
        "kind": "powershell",
        "script": "drill_l2_1_failover.ps1",
        "task": "S7-T3",
        "check_ids": ("S7-T3-1", "S7-T3-2", "S7-T3-3", "S7-T3-4"),
        "evidence_rel": "doc/test/evidence/s7/l2-1/failover-drill.json",
        "evidence_name": "failover-drill.json",
    },
    {
        "key": "l2_2",
        "kind": "python",
        "script": "finalize_l2_2_matrix.py",
        "task": "S7-T4",
        "check_ids": ("S7-T4-1", "S7-T4-2", "S7-T4-3", "S7-T4-4"),
        "evidence_rel": "doc/test/evidence/s7/l2-2/matrix-finalize.json",
        "evidence_name": "matrix-finalize.json",
    },
    {
        "key": "l3_1",
        "kind": "powershell",
        "script": "verify_l3_1_agent.ps1",
        "task": "S7-T5",
        "check_ids": ("S7-T5-1", "S7-T5-2", "S7-T5-3", "S7-T5-4"),
        "evidence_rel": "doc/test/evidence/s7/l3-1/agent-e2e.json",
        "evidence_name": "agent-e2e.json",
    },
    {
        "key": "l3_2",
        "kind": "python",
        "script": "smoke_l3_2.py",
        "task": "L3-2",
        "check_ids": ("S7-T6-2", "S7-T7-3"),
        "evidence_rel": "doc/test/evidence/s7/l3-2/smoke-result.json",
        "evidence_name": "smoke-result.json",
    },
)

_TOOL_KEYS = tuple(tool["key"] for tool in _TOOLS)
_TOOL_BY_KEY = {tool["key"]: tool for tool in _TOOLS}


def _powershell_executable() -> str | None:
    """解析 powershell.exe（Windows PowerShell 5+，含 System32 兜底路径）."""
    candidate = shutil.which("powershell")
    if candidate:
        return candidate
    standard = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    return str(standard) if standard.exists() else None


POWERSHELL = _powershell_executable()

needs_powershell = pytest.mark.skipif(
    POWERSHELL is None, reason="Windows PowerShell 5+ not available"
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_dry_run_command(spec: dict[str, Any], base: Path) -> tuple[list[str], Path]:
    """构造五脚本干跑命令与期望证据路径（PowerShell ``-DryRun`` / Python ``--dry-run``）."""
    script = _SCRIPTS / spec["script"]
    if spec["kind"] == "powershell":
        evidence_dir = base / spec["key"]
        evidence_dir.mkdir(parents=True, exist_ok=True)
        args = [
            "-DryRun",
            "-BaseUrl",
            "http://127.0.0.1:1",
            "-EvidenceDir",
            str(evidence_dir),
        ]
        if spec["key"] == "l1_1":
            args += ["-SubjectId", "smoke_l1_1_skeleton"]
        elif spec["key"] == "l2_1":
            args += ["-Scenario", "b-down"]
        elif spec["key"] == "l3_1":
            args += ["-AgentKey", "sk-agent-skeleton"]
        assert POWERSHELL is not None
        command = [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *args,
        ]
        return command, evidence_dir / spec["evidence_name"]

    out_path = base / f"{spec['key']}-{spec['evidence_name']}"
    if spec["key"] == "l3_2":
        args = ["--dry-run", "--base-url", "http://127.0.0.1:1", "--out", str(out_path)]
    else:
        args = ["--dry-run", "--out", str(out_path)]
    return [sys.executable, str(script), *args], out_path


def _parse_powershell_syntax(script: Path) -> subprocess.CompletedProcess[str]:
    """以 PowerShell Parser 静态校验语法（0 token 错误）."""
    assert POWERSHELL is not None
    program = (
        "$errors = $null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{script}',"
        " [ref]$null, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Output $_.Message };"
        " exit 1 } exit 0"
    )
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


@pytest.fixture(scope="module")
def dry_run_results(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, Any]]:
    """五脚本干跑一次（PowerShell 不可用时跳过 PS 脚本），返回命令结果与证据路径."""
    base = tmp_path_factory.mktemp("s7_tools")
    results: dict[str, dict[str, Any]] = {}
    for spec in _TOOLS:
        if spec["kind"] == "powershell" and POWERSHELL is None:
            continue
        command, evidence_path = _build_dry_run_command(spec, base)
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results[spec["key"]] = {
            "spec": spec,
            "completed": completed,
            "evidence_path": evidence_path,
        }
    return results


# ===========================================================================
# 存在性与 PowerShell 语法
# ===========================================================================


def test_all_tools_present() -> None:
    """五脚本按设计草案落点齐备."""
    missing = [tool["script"] for tool in _TOOLS if not (_SCRIPTS / tool["script"]).exists()]
    assert not missing, f"缺少 S7 联调窗口工具脚本: {missing}"


@needs_powershell
def test_powershell_tools_syntax_clean() -> None:
    """PowerShell 三脚本 Parser 语法 0 错误（UTF-8 + BOM 解析要求）."""
    for tool in _TOOLS:
        if tool["kind"] != "powershell":
            continue
        script = _SCRIPTS / tool["script"]
        assert script.exists(), f"缺少脚本: {script}"
        assert script.read_bytes()[:3] == b"\xef\xbb\xbf", f"{tool['script']} 缺少 UTF-8 BOM"
        result = _parse_powershell_syntax(script)
        assert result.returncode == 0, (
            f"{tool['script']} 语法错误:\n{result.stdout}\n{result.stderr}"
        )


def test_tools_declare_assertion_ids_in_source() -> None:
    """脚本源码内声明各自断言编号（与设计 §4.2~§4.5 映射，便于静态追溯）."""
    for tool in _TOOLS:
        script = _SCRIPTS / tool["script"]
        assert script.exists(), f"缺少脚本: {script}"
        text = _read_text(script)
        missing = [check_id for check_id in tool["check_ids"] if check_id not in text]
        assert not missing, f"{tool['script']} 源码缺少断言编号: {missing}"


# ===========================================================================
# 干跑可执行性与统一退出码约定
# ===========================================================================


@pytest.mark.parametrize("key", _TOOL_KEYS)
def test_dry_run_executable_with_pending_exit_code(
    dry_run_results: dict[str, dict[str, Any]], key: str
) -> None:
    """无真实环境时干跑可执行，status=PENDING 且退出码 2（统一约定）."""
    if key not in dry_run_results:
        pytest.skip("Windows PowerShell 5+ not available")
    entry = dry_run_results[key]
    completed: subprocess.CompletedProcess[str] = entry["completed"]
    assert completed.returncode == _EXIT_PENDING, (
        f"{entry['spec']['script']} 干跑退出码应为 {_EXIT_PENDING}（PENDING），"
        f"实际 {completed.returncode}\n{completed.stdout}\n{completed.stderr}"
    )
    evidence_path: Path = entry["evidence_path"]
    assert evidence_path.exists(), (
        f"{entry['spec']['script']} 干跑未产出证据 {evidence_path}\n"
        f"{completed.stdout}\n{completed.stderr}"
    )


# ===========================================================================
# 证据 JSON schema 合法性
# ===========================================================================


@pytest.mark.parametrize("key", _TOOL_KEYS)
def test_evidence_schema_valid(
    dry_run_results: dict[str, dict[str, Any]], key: str
) -> None:
    """证据 JSON 必含规定字段；status ∈ {PASS,FAIL,PENDING} 且与 exit_code 一致."""
    if key not in dry_run_results:
        pytest.skip("Windows PowerShell 5+ not available")
    entry = dry_run_results[key]
    spec = entry["spec"]
    payload = _load_json(entry["evidence_path"])

    for field in _REQUIRED_FIELDS:
        assert field in payload, f"{spec['script']} 证据缺少字段: {field}"
    assert payload["schema_version"] == 1
    assert payload["tool"] == spec["script"]
    assert payload["mode"] == "dry-run"
    assert payload["generated_at"]
    assert payload["commit"], f"{spec['script']} 证据缺少提交号（禁伪造：须为真实 HEAD）"
    assert payload["status"] in _VALID_STATUS, payload["status"]
    assert payload["exit_code"] == _STATUS_TO_EXIT[payload["status"]], (
        f"{spec['script']} status 与 exit_code 不一致: {payload['status']} / {payload['exit_code']}"
    )

    checks = payload["checks"]
    assert isinstance(checks, list) and checks, f"{spec['script']} checks 为空"
    for check in checks:
        assert check.get("id"), f"{spec['script']} check 缺少 id"
        assert check.get("status") in _VALID_STATUS, check
        assert check.get("execution_face") in {"A", "A+B", "B"}, check
        if check["status"] in {"PENDING", "FAIL"}:
            assert check.get("reason"), f"{spec['script']} {check['id']} 缺少 reason"


@pytest.mark.parametrize("key", _TOOL_KEYS)
def test_checks_mapped_to_assertions(
    dry_run_results: dict[str, dict[str, Any]], key: str
) -> None:
    """每脚本 checks 内 id 与设计断言编号一一映射，且无游离/无缺失."""
    if key not in dry_run_results:
        pytest.skip("Windows PowerShell 5+ not available")
    entry = dry_run_results[key]
    spec = entry["spec"]
    payload = _load_json(entry["evidence_path"])
    ids = [check["id"] for check in payload["checks"]]
    assert len(ids) == len(set(ids)), f"{spec['script']} checks id 重复: {ids}"
    assert set(ids) == set(spec["check_ids"]), (
        f"{spec['script']} 断言映射不符: {sorted(ids)} != {sorted(spec['check_ids'])}"
    )


@pytest.mark.parametrize("key", _TOOL_KEYS)
def test_no_fake_pass_without_real_environment(
    dry_run_results: dict[str, dict[str, Any]], key: str
) -> None:
    """无真实环境时不得伪造 PASS：顶层与各 check 均为 PENDING 且附原因."""
    if key not in dry_run_results:
        pytest.skip("Windows PowerShell 5+ not available")
    entry = dry_run_results[key]
    spec = entry["spec"]
    payload = _load_json(entry["evidence_path"])
    assert payload["status"] == "PENDING", payload["status"]
    assert payload.get("reason"), f"{spec['script']} 顶层 PENDING 缺少 reason"
    for check in payload["checks"]:
        assert check["status"] == "PENDING", check
        assert check.get("reason"), check


# ===========================================================================
# 仓内 PENDING 登记（默认证据落点）
# ===========================================================================


def test_default_evidence_registered_as_pending() -> None:
    """仓内默认证据落点已登记且状态自洽（禁伪造：PENDING 必附原因，PASS 必全项 PASS）.

    说明：三脚本已由「骨架 + 干跑一律 PENDING」升级为委派真实运行器
    （``verify_l1_1_cascade.py`` / ``drill_l2_1_failover.py`` / ``verify_l3_1_agent.py``），
    默认落点因此可能是真实联调结果（PASS/PENDING）。本断言保证状态与退出码自洽、
    PENDING 附原因、PASS 不得含未闭合项（禁伪造口径不放松）。
    """
    for tool in _TOOLS:
        evidence_path = ROOT / tool["evidence_rel"]
        assert evidence_path.exists(), f"缺少证据: {tool['evidence_rel']}"
        payload = _load_json(evidence_path)
        for field in _REQUIRED_FIELDS:
            assert field in payload, f"{tool['evidence_rel']} 缺少字段: {field}"
        assert payload["status"] in _VALID_STATUS, payload["status"]
        assert payload["exit_code"] == _STATUS_TO_EXIT[payload["status"]], (
            f"{tool['evidence_rel']} status 与 exit_code 不一致: "
            f"{payload['status']} / {payload['exit_code']}"
        )
        if payload["status"] == "PENDING":
            assert payload.get("reason"), f"{tool['evidence_rel']} PENDING 缺少 reason"
        if payload["status"] == "PASS":
            unresolved = [
                item["id"] for item in payload.get("checks", [])
                if item.get("status") != "PASS"
            ]
            assert not unresolved, (
                f"{tool['evidence_rel']} 标 PASS 但存在未闭合项: {unresolved}"
            )


# ===========================================================================
# 文档同步（文档地图索引 / 沙箱外执行单）
# ===========================================================================


def test_doc_map_index_bumped_with_tools() -> None:
    """文档地图索引升版 v1.0.3，新增五脚本条目且 MANIFEST 逐项存在."""
    assert _DOC_MAP.exists(), f"缺少文档地图索引: {_DOC_MAP}"
    text = _read_text(_DOC_MAP)
    assert "v1.0.3" in text, "文档地图索引未升版 v1.0.3"
    for tool in _TOOLS:
        script_rel = f"scripts/{tool['script']}"
        assert script_rel in text, f"文档地图索引缺少脚本条目: {script_rel}"
    block = text.split("<!-- DOCMAP-MANIFEST:BEGIN -->")[1].split("<!-- DOCMAP-MANIFEST:END -->")[0]
    for tool in _TOOLS:
        script_rel = f"scripts/{tool['script']}"
        assert script_rel in block, f"文档地图 MANIFEST 缺少脚本条目: {script_rel}"


def test_execution_order_updated_to_skeleton_ready() -> None:
    """沙箱外执行单升版 v1.0.1，§0.2 由「待实现」更新为「骨架已就绪」，退出码约定一致."""
    assert _EXECUTION_ORDER.exists(), f"缺少沙箱外执行单: {_EXECUTION_ORDER}"
    text = _read_text(_EXECUTION_ORDER)
    assert "v1.0.1" in text, "执行单未升版 v1.0.1"
    assert "骨架已就绪" in text, "执行单 §0.2 未更新为「骨架已就绪」"
    for marker in ("-EvidenceDir", "-DryRun", "finalize_l2_2_matrix.py", "smoke_l3_2.py"):
        assert marker in text, f"执行单缺少命令参数/脚本: {marker}"
    for marker in ("0=PASS", "1=FAIL", "2=PENDING"):
        assert marker in text, f"执行单缺少退出码约定: {marker}"
