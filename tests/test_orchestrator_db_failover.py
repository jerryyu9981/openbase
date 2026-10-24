"""编排入口「启动期共享库主备探测」守门用例（P0，2026-10-25）.

需求：每次启动服务前先检测**主用共享库**（PostgreSQL `192.168.0.151:5432`）；
异常时自动切换到**备用库通道**（本机 `127.0.0.1:5432`）；主备均不可达则拒绝启动。

口径（与《OpenBase-本地备用基础设施安装与主备切换记录-v1.9.0》§16 一致）：
- 单一决策点 = `scripts/service-orchestrator.ps1`（受管编排入口）；
- `start` / `startcheck` / `monitor` 启动前必探测；`-Action dbcheck` 为只探测入口；
- 备用以**子进程环境变量**覆盖生效，**不改写** `.env`；主用恢复后重启回主用；
- 主备均不可达 ⇒ 退出码 2，且**不启动任何服务**；
- 证据落 `doc/test/evidence/ops/**`，DSN 一律脱敏。

本文件分两层：
1) 静态契约（无需 PowerShell/数据库）：标记、默认值、编码读取方式、文档登记；
2) 行为契约（需 Windows PowerShell）：`-DbMode off` 直接放行；强制备用指向不可达端口时
   退出码 2 且不监听 8000。行为用例用临时 LogRoot/EvidenceRoot，避免污染仓库。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "service-orchestrator.ps1"
OPERATION_DOC = ROOT / "doc" / "operation" / "OpenBase-本地备用基础设施安装与主备切换记录-v1.9.0.md"

POWERSHELL = shutil.which("powershell") or (
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    if Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe").exists()
    else None
)

needs_powershell = pytest.mark.skipif(POWERSHELL is None, reason="Windows PowerShell 5+ not available")


def _text() -> str:
    return ORCHESTRATOR.read_text(encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# 1. 静态契约
# ---------------------------------------------------------------------------


def test_orchestrator_keeps_utf8_bom() -> None:
    """PowerShell 5 脚本须保留 UTF-8 BOM（否则中文解析异常）。"""
    assert ORCHESTRATOR.read_bytes()[:3] == b"\xef\xbb\xbf"


@needs_powershell
def test_orchestrator_powershell_syntax_clean() -> None:
    """Parser 语法 0 错误。"""
    program = (
        "$errors = $null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{ORCHESTRATOR}',"
        " [ref]$null, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Output $_.Message }; exit 1 } exit 0"
    )
    completed = subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_db_probe_contract_declared() -> None:
    """关键契约标记齐备（动作/参数/函数/失败码/证据目录）。"""
    text = _text()
    for marker in (
        "'dbcheck'",
        "ValidateSet('auto', 'primary', 'standby', 'off')",
        "$DbMode = 'auto'",
        "Test-PostgresEndpoint",
        "Assert-DbReadyOrExit",
        "OPENBASE_PG_STANDBY_HOST",
        "OPENBASE_PG_STANDBY_PORT",
        "OPENBASE_PG_STANDBY_URL",
        "OPENBASE_EVIDENCE_ROOT",
        "db-startup-probe-",
        "exit 2",
    ):
        assert marker in text, f"缺少契约标记: {marker}"


def test_start_and_monitor_are_gated() -> None:
    """start 与 monitor 启动前必须经过共享库门禁。"""
    text = _text()
    assert text.count("Assert-DbReadyOrExit -ActionName 'start'") >= 1
    assert text.count("Assert-DbReadyOrExit -ActionName 'monitor'") >= 1


def test_standby_defaults_to_local_postgres() -> None:
    """备用库通道 = 本机 127.0.0.1:5432；端口默认 5432（不得沿用主用端口）。"""
    text = _text()
    assert "'127.0.0.1'" in text
    assert "} else { 5432 }" in text, "备用端口默认值应为 5432"
    assert "if ($env:OPENBASE_PG_STANDBY_PORT) { [int]$env:OPENBASE_PG_STANDBY_PORT } else { $primaryPort }" not in text


def test_env_file_read_uses_utf8_explicitly() -> None:
    """`.env` 读取必须显式 UTF-8（PS 5.1 默认 ANSI 会导致行错位）。"""
    text = _text()
    assert "[System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8)" in text


def test_operation_doc_records_startup_failover() -> None:
    """运维记录升 v1.9.0 并登记 §16（启动期自动探测与主备切换）。"""
    assert OPERATION_DOC.exists(), f"缺少运维记录: {OPERATION_DOC}"
    text = OPERATION_DOC.read_text(encoding="utf-8-sig")
    assert "v1.9.0" in text
    assert "## 16. 启动期自动探测与主备切换" in text
    for marker in ("-Action dbcheck", "-DbMode", "127.0.0.1:5432", "退出码 2"):
        assert marker in text, f"运维记录缺少: {marker}"


# ---------------------------------------------------------------------------
# 2. 行为契约（不启动真实服务；不依赖数据库）
# ---------------------------------------------------------------------------


def _base_env(tmp_path: Path) -> dict[str, str]:
    """继承宿主环境（勿裁剪 SystemDrive/ProgramData，否则 Windows 会在 cwd 下造伪目录）。"""
    env = os.environ.copy()
    env["OPENBASE_EVIDENCE_ROOT"] = str(tmp_path / "evidence")
    env["TEMP"] = str(tmp_path)
    env["TMP"] = str(tmp_path)
    return env


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ORCHESTRATOR),
            "-LogRoot",
            str(tmp_path / "logs"),
            "-ServiceLogRoot",
            str(tmp_path / "svc-logs"),
            *args,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_base_env(tmp_path),
        timeout=120,
    )


@needs_powershell
def test_dbcheck_off_mode_exits_zero(tmp_path: Path) -> None:
    """-DbMode off：不探测、直接放行（兼容旧行为），且不产生证据文件。"""
    completed = _run(tmp_path, "-Action", "dbcheck", "-DbMode", "off")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    evidence_dir = tmp_path / "evidence"
    assert not evidence_dir.exists() or not list(evidence_dir.glob("*.json"))


@needs_powershell
def test_standby_unreachable_blocks_startup(tmp_path: Path) -> None:
    """强制备用但备用不可达 ⇒ 退出码 2；不启动任何服务（8000 无监听）。"""
    assert POWERSHELL is not None
    env = _base_env(tmp_path)
    env["OPENBASE_PG_STANDBY_PORT"] = "1"
    completed = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ORCHESTRATOR),
            "-Action",
            "start",
            "-Only",
            "openbase",
            "-DbMode",
            "standby",
            "-DbProbeTimeoutSec",
            "1",
            "-LogRoot",
            str(tmp_path / "logs"),
            "-ServiceLogRoot",
            str(tmp_path / "svc-logs"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    assert completed.returncode == 2, completed.stdout + completed.stderr
    assert "拒绝启动" in (completed.stdout + completed.stderr)

    probe = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-Command",
            "(Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet) -as [string]",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=60,
    )
    assert "True" not in probe.stdout, "共享库不可达时不应启动任何服务（8000 不应监听）"

    evidence = list((tmp_path / "evidence").glob("db-startup-probe-*.json"))
    assert evidence, "缺少共享库探测证据 JSON"
    payload = json.loads(evidence[0].read_text(encoding="utf-8-sig"))
    assert payload["ok"] is False
    assert payload["resolved_mode"] == "unavailable"
    assert "***" not in json.dumps(payload.get("primary", {}))
