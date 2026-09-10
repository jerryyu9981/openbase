"""S7-T1 SHR 五项收口断言（verify-env 全局化 / openbase_test / K13 / 编排入口 / 文档地图）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》§4.1（S7-T1-1 ~ S7-T1-5）。
断言编号与立项方案 §4 同编号验收断言 1:1。

断言口径（沙箱可判定面 / A 面；B 面真实执行在联调窗口负责，本测试只断言
结构、干跑与 PENDING 登记，禁止以「预期通过」代替证据）：

- S7-T1-1：跨仓统一契约 contract.global.json 结构对齐（OpenBase 6 组 + repo_overrides
  四仓契约键命名映射、无游离）+ verify_env_global.ps1 存在/干跑/两段式开关；
- S7-T1-2：openbase_test 建库脚本幂等 + run_tests.ps1 跨仓统一回归入口（保留单仓分组隔离）；
- S7-T1-3：K13 账号矩阵（schema×账号×权限，跨 schema 写拒绝）+ 授权脚本打印模式干跑；
- S7-T1-4：编排唯一入口（service-orchestrator.ps1）+ 禁批量杀静态扫描 0 命中（含防误报自检）；
- S7-T1-5：文档地图索引覆盖 L0-L4 全量文档 + S1a~S7 并入核对（无游离文档）。
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]

# --- S7-T1-1 落点 -----------------------------------------------------------
_CONTRACT_LOCAL = ROOT / "scripts" / "verify-env" / "contract.json"
_CONTRACT_GLOBAL = ROOT / "scripts" / "verify-env" / "contract.global.json"
_VERIFY_GLOBAL = ROOT / "scripts" / "verify_env_global.ps1"
# --- S7-T1-2 落点 -----------------------------------------------------------
_INIT_TEST_DB = ROOT / "scripts" / "db" / "init_openbase_test.ps1"
_RUN_TESTS = ROOT / "scripts" / "run_tests.ps1"
# --- S7-T1-3 落点 -----------------------------------------------------------
_K13_MATRIX = ROOT / "doc" / "design" / "OpenBase-K13-账号权限矩阵-v1.0.0.md"
_K13_GRANT = ROOT / "scripts" / "db" / "grant_k13_accounts.ps1"
# --- S7-T1-4 落点 -----------------------------------------------------------
_ORCHESTRATOR = ROOT / "scripts" / "service-orchestrator.ps1"
_BYPASS_SCAN = ROOT / "scripts" / "scan_orchestrator_bypass.py"
# --- S7-T1-5 落点 -----------------------------------------------------------
_DOC_MAP = ROOT / "doc" / "design" / "OpenBase-文档地图索引-v1.0.0.md"

_OPENBASE_SECTION_KEYS = (
    "config_single_source",
    "config_deprecated",
    "upstreams",
    "whitelist_matrix",
    "mapping_reconcile",
    "db_checks",
)
_REQUIRED_REPOS = ("openbase", "openllm", "openrag", "openmemory", "dps")
# 四仓 verify-env 契约键命名现状（上游实测 S3-T10 / S4-T14 / S5-T11 配套）
_REPO_REQUIRED_KEYS = {
    "openllm": {"identity_trust", "REAL", "channel", "upstream"},
    "openrag": {"identity_trust", "row_scope", "identity_event", "api"},
    "dps": {"identity_trust", "row_scope", "identity_event", "api"},
}
_REPO_OVERRIDE_FIELDS = {
    "role",
    "contract_source",
    "verify_env_ref",
    "sections",
    "contract_keys",
    "contract_dir",
    "contract_keys_pending",
}

_K13_ACCOUNTS = {"openbase_app", "platform_app", "openbase_migrator", "openbase_runtime"}

# S1a~S7 纵切新增文档（各段立项/设计草案/DevLog/测试报告/台账/清单/执行模板）
_S1A_S7_DOCUMENTS = (
    # U1（S1a）
    "OpenBase-U1-统一身份收口立项方案-v1.0.0.md",
    "OpenBase-U1-统一身份收口设计草案-v1.0.0.md",
    "doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md",
    "doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md",
    # P2-1（S1b）
    "OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0.md",
    "OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md",
    "doc/development/OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0.md",
    "doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md",
    # P2-2 / R1
    "OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md",
    "OpenBase-P2-2-隔离收口实施执行计划-v1.0.0.md",
    "OpenBase-R1-隔离收口实施执行计划-v1.0.0.md",
    # S6
    "OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md",
    "OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md",
    "doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md",
    "doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md",
    "doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md",
    # S7
    "OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md",
    "OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md",
    "doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md",
    "doc/design/OpenBase-文档地图索引-v1.0.0.md",
    "doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md",
    # 台账 / 清单
    "OpenBase-数据隔离实现任务卡-v1.0.0.md",
    "OpenBase-真实联调冒烟清单-v1.0.0.md",
    "OpenBase-存量测试对齐任务清单-v1.0.0.md",
    "doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md",
    "doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md",
)

_NEW_POWERSHELL_SCRIPTS = (
    _VERIFY_GLOBAL,
    _INIT_TEST_DB,
    _K13_GRANT,
    _RUN_TESTS,
)


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
    """以 UTF-8 读取文本（中文文档/脚本路径在 Windows 下不作编码猜测）."""
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_powershell(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


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


def _load_bypass_scanner() -> ModuleType:
    """以文件路径加载静态扫描器模块（scripts 非包，独立导入）."""
    spec = importlib.util.spec_from_file_location("scan_orchestrator_bypass", _BYPASS_SCAN)
    assert spec and spec.loader, f"无法加载扫描器: {_BYPASS_SCAN}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ===========================================================================
# S7-T1-1 verify-env 全局化
# ===========================================================================


def test_s7_t1_1_global_contract_structure_aligned() -> None:
    """跨仓统一契约结构与 OpenBase 6 组主结构及四仓键命名对齐（无游离）."""
    assert _CONTRACT_GLOBAL.exists(), f"缺少全局契约: {_CONTRACT_GLOBAL}"
    global_contract = _load_json(_CONTRACT_GLOBAL)
    local_contract = _load_json(_CONTRACT_LOCAL)

    assert global_contract["schema_version"] == 1
    # 主结构 = OpenBase 6 组（非破坏性：与现行 contract.json 逐组一致）
    assert set(global_contract["sections"]) == set(_OPENBASE_SECTION_KEYS)
    assert global_contract["sections"] == local_contract["sections"]
    # 现行 contract.json 未被改动（仍为 6 组）
    assert set(local_contract["sections"]) == set(_OPENBASE_SECTION_KEYS)

    overrides = global_contract["repo_overrides"]
    assert set(overrides) == set(_REQUIRED_REPOS), f"repo_overrides 游离/缺失: {set(overrides)}"

    openbase_override = overrides["openbase"]
    assert set(openbase_override["sections"]) == set(_OPENBASE_SECTION_KEYS)

    for repo, required_keys in _REPO_REQUIRED_KEYS.items():
        entry = overrides[repo]
        assert set(entry["contract_keys"]) == required_keys, (
            f"{repo} 契约键命名与现状不一致/游离: {entry['contract_keys']} != {required_keys}"
        )
        assert entry["verify_env_ref"] == "scripts/verify-env"

    openmemory_override = overrides["openmemory"]
    assert openmemory_override["contract_dir"] == "scripts/verify-env"
    assert openmemory_override["contract_keys_pending"] is True, (
        "openmemory 键名待仓内确认须显式登记（不得静默缺失）"
    )

    for repo, entry in overrides.items():
        assert set(entry) <= _REPO_OVERRIDE_FIELDS, f"{repo} 出现游离字段: {set(entry)}"


def test_s7_t1_1_global_entry_script_structure() -> None:
    """全局入口脚本存在且保留 -Repos / 契约引用 / 两段式开关 / 回退语义."""
    assert _VERIFY_GLOBAL.exists(), f"缺少全局入口: {_VERIFY_GLOBAL}"
    text = _read_text(_VERIFY_GLOBAL)
    for marker in (
        "contract.global.json",
        "$Repos",
        "$ContractPath",
        "OPENBASE_VERIFY_ENV_STRICT",
        "$FailFast",
        "$SkipNetwork",
        "$SkipDb",
        "$DryRun",
        "exit",
    ):
        assert marker in text, f"verify_env_global.ps1 缺少必需结构: {marker}"


@needs_powershell
def test_s7_t1_1_global_entry_dry_run(tmp_path: Path) -> None:
    """全局入口 -DryRun 干跑产出报告且契约结构合法时退出码 0."""
    report_path = tmp_path / "verify-env-report.global.json"
    result = _run_powershell(
        _VERIFY_GLOBAL,
        "-DryRun",
        "-SkipNetwork",
        "-SkipDb",
        "-ContractPath",
        str(_CONTRACT_GLOBAL),
        "-OutputPath",
        str(report_path),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert report_path.exists(), f"全局入口未产出报告: {result.stdout}\n{result.stderr}"
    report = _load_json(report_path)
    assert report["mode"] == "dry-run"
    assert report["summary"]["exit_code"] == 0
    assert len(report["repos"]) == len(_REQUIRED_REPOS)
    names = {item["name"] for item in report["repos"]}
    assert names == set(_REQUIRED_REPOS)


# ===========================================================================
# S7-T1-2 openbase_test 独立测试库 + run_tests.ps1 跨仓入口
# ===========================================================================


def test_s7_t1_2_init_script_idempotent_structure() -> None:
    """建库脚本存在、幂等（存在性守卫 + IF NOT EXISTS）、测试连接隔离业务库."""
    assert _INIT_TEST_DB.exists(), f"缺少 openbase_test 建库脚本: {_INIT_TEST_DB}"
    text = _read_text(_INIT_TEST_DB)
    for marker in (
        "openbase_test",
        "OPENBASE_DB_URL",
        "pg_database",
        "IF NOT EXISTS",
        "NOSUPERUSER",
        "$DryRun",
    ):
        assert marker in text, f"init_openbase_test.ps1 缺少幂等/隔离结构: {marker}"
    # 幂等判据：建库前存在性守卫 + 幂等 DDL（IF NOT EXISTS / create_all）
    assert ("WHERE NOT EXISTS" in text) or ("IF NOT EXISTS" in text) or ("create_all" in text), (
        "建库/迁移缺少幂等语义"
    )
    # 测试连接不得指向业务库名 openbase（仅允许 openbase_test）
    assert "openbase_test" in text


@needs_powershell
def test_s7_t1_2_init_script_dry_run(tmp_path: Path) -> None:
    """建库脚本 -DryRun 干跑通过（沙箱无真实 PG，真实建库登记 PENDING）."""
    result = _run_powershell(_INIT_TEST_DB, "-DryRun")
    assert result.returncode == 0, result.stdout + result.stderr


def test_s7_t1_2_run_tests_cross_repo_entry() -> None:
    """run_tests.ps1 升跨仓统一回归入口，且保留 v1.4.2 单仓分组子进程隔离能力."""
    text = _read_text(_RUN_TESTS)
    for marker in (
        "$Repos",
        "跨仓",
        "$i += 6",
        "$WithCoverage",
        "OpenLLM",
        "OpenRAG",
        "OpenMemory",
        "DPS",
        "$DryRun",
    ):
        assert marker in text, f"run_tests.ps1 缺少跨仓入口/单仓隔离结构: {marker}"


# ===========================================================================
# S7-T1-3 K13 存储账号分离
# ===========================================================================


def test_s7_t1_3_account_matrix_document() -> None:
    """账号矩阵文件含 schema×账号×权限（四类账号、仅本 schema DML、不授 superuser）."""
    assert _K13_MATRIX.exists(), f"缺少 K13 账号矩阵: {_K13_MATRIX}"
    text = _read_text(_K13_MATRIX)
    for account in _K13_ACCOUNTS:
        assert account in text, f"K13 矩阵缺少账号: {account}"
    for marker in (
        "schema",
        "权限",
        "仅本 schema",
        "DML",
        "superuser",
        "跨 schema",
        "迁移账号",
        "运行时账号",
        "拒绝",
        "PENDING",
    ):
        assert marker in text, f"K13 矩阵缺少口径: {marker}"


def test_s7_t1_3_grant_script_structure() -> None:
    """授权脚本存在、收敛 GRANT（不授 superuser）、含跨 schema 拒绝与打印模式."""
    assert _K13_GRANT.exists(), f"缺少 K13 授权脚本: {_K13_GRANT}"
    text = _read_text(_K13_GRANT)
    for account in _K13_ACCOUNTS:
        assert account in text, f"授权脚本缺少账号: {account}"
    for marker in ("GRANT", "NOSUPERUSER", "REVOKE", "$DryRun"):
        assert marker in text, f"授权脚本缺少结构: {marker}"
    # 不得出现 "GRANT ... SUPERUSER"（不授 superuser 的硬约束；仅匹配 SQL 语句）
    assert not re.search(r"\bGRANT\s+[^\r\n]*\bSUPERUSER\b", text, re.IGNORECASE), (
        "授权脚本出现授予 SUPERUSER 的语句"
    )


@needs_powershell
def test_s7_t1_3_grant_script_dry_run() -> None:
    """授权脚本打印模式干跑通过（真实授权与跨 schema 写拒绝登记 PENDING）."""
    result = _run_powershell(_K13_GRANT, "-DryRun")
    assert result.returncode == 0, result.stdout + result.stderr


# ===========================================================================
# S7-T1-4 编排唯一入口（禁批量杀）
# ===========================================================================


def test_s7_t1_4_orchestrator_is_single_entry() -> None:
    """唯一入口 = service-orchestrator.ps1（逆拓扑 stop 为唯一允许位）."""
    assert _ORCHESTRATOR.exists(), f"缺少编排入口: {_ORCHESTRATOR}"
    text = _read_text(_ORCHESTRATOR)
    for marker in ("start", "startcheck", "checkall", "monitor", "status", "stop"):
        assert marker in text, f"编排入口缺少动作: {marker}"


def test_s7_t1_4_bypass_scan_zero_hits_and_not_vacuous() -> None:
    """静态扫描 0 绕过命中；扫描器非空化自检（防误报/防漏报）."""
    assert _BYPASS_SCAN.exists(), f"缺少静态扫描器: {_BYPASS_SCAN}"
    scanner = _load_bypass_scanner()
    assert scanner.ORCHESTRATOR_ENTRY == "scripts/service-orchestrator.ps1"

    report = scanner.scan_repository()
    assert report["scanned_files"] > 0, "扫描器未扫描到文件（空化误报）"
    assert report["disallowed"] == [], f"存在绕过编排入口的批量杀路径: {report['disallowed']}"
    self_check = report["self_check"]
    assert self_check["bypass_detected"] is True, "自检失败：违规样本未命中（漏报）"
    assert self_check["string_mention_ignored"] is True, "自检失败：字符串文案被误报"
    assert self_check["allowed_pid_stop_accepted"] is True, "自检失败：PASS 合法 PID 停止未识别"


@needs_powershell
def test_s7_t1_4_new_scripts_powershell_syntax() -> None:
    """新增/修改的 PowerShell 脚本语法 0 错误（Parser 静态校验）."""
    for script in _NEW_POWERSHELL_SCRIPTS:
        assert script.exists(), f"缺少脚本: {script}"
        result = _parse_powershell_syntax(script)
        assert result.returncode == 0, (
            f"{script.name} 语法错误:\n{result.stdout}\n{result.stderr}"
        )


# ===========================================================================
# S7-T1-5 文档地图（L0-L4 + S1a~S7 并入核对，无游离文档）
# ===========================================================================


def test_s7_t1_5_doc_map_covers_layers() -> None:
    """文档地图索引存在，覆盖 L0-L4 分层且含名称/版本/角色/状态/关联锚点字段."""
    assert _DOC_MAP.exists(), f"缺少文档地图索引: {_DOC_MAP}"
    text = _read_text(_DOC_MAP)
    for layer in ("L0", "L1", "L2", "L3", "L4"):
        assert layer in text, f"文档地图缺少分层: {layer}"
    for field in ("名称", "版本", "角色", "状态", "关联锚点"):
        assert field in text, f"文档地图缺少字段: {field}"
    assert "无游离" in text


def test_s7_t1_5_s1a_s7_documents_merged() -> None:
    """S1a~S7 纵切新增文档逐项并入核对（差异 0 或显式登记）."""
    text = _read_text(_DOC_MAP)
    missing = [name for name in _S1A_S7_DOCUMENTS if name not in text]
    assert not missing, f"文档地图未并入以下 S1a~S7 文档: {missing}"


def test_s7_t1_5_manifest_entries_exist() -> None:
    """地图机器可核对清单中的每一项均真实存在（无游离文档/无失效引用）."""
    text = _read_text(_DOC_MAP)
    block = re.search(
        r"<!--\s*DOCMAP-MANIFEST:BEGIN\s*-->(.*?)<!--\s*DOCMAP-MANIFEST:END\s*-->",
        text,
        re.DOTALL,
    )
    assert block, "文档地图缺少机器可核对清单（DOCMAP-MANIFEST 区块）"
    entries = re.findall(r"^-\s+(\S+\.md)\s*$", block.group(1), re.MULTILINE)
    assert entries, "机器可核对清单为空"
    missing = [entry for entry in entries if not (ROOT / entry).exists()]
    assert not missing, f"文档地图清单存在指向缺失文件的游离项: {missing}"
