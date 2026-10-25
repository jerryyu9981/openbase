"""编排入口「启动期共享库主备探测」守门用例（P0，2026-10-25）.

需求：每次启动服务前先检测**主用共享库**（PostgreSQL `192.168.0.151:5432`）；
异常时自动切换到**备用库通道**（本机 `127.0.0.1:5432`）；主备均不可达则拒绝启动。

口径（与《OpenBase-本地备用基础设施安装与主备切换记录-v1.9.0》§16 一致）：
- 单一决策点 = `scripts/service-orchestrator.ps1`（受管编排入口）；
- `start` / `startcheck` / `monitor` 启动前必探测；`-Action dbcheck` 为只探测入口；
- 备用以**子进程环境变量**覆盖生效，**不改写** `.env`；主用恢复后重启回主用；
- 主备均不可达 ⇒ 退出码 2，且**不启动任何服务**；
- 证据落 `doc/test/evidence/ops/**`，DSN 一律脱敏。

本文件分三层：
1) 静态契约（无需 PowerShell/数据库）：标记、默认值、编码读取方式、文档登记；
2) 行为契约（需 Windows PowerShell）：`-DbMode off` 直接放行；强制备用指向不可达端口时
   退出码 2 且不监听 8000。行为用例用临时 LogRoot/EvidenceRoot，避免污染仓库；
3) Phase 2（P1，2026-10-25）：`dbcheck -Json` 机器可读输出、monitor 周期复检
   （主用恢复只提示不回切）、公共设施探测仅提示不阻断；
4) Phase 3（P0，2026-10-25，用户决策）：判定升级为**数据面探针**
   （`scripts/infra_probe.py`），主用不通即切备用（含四设施），数据面同步问题挂起并告警。
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "service-orchestrator.ps1"
PROBE_SCRIPT = ROOT / "scripts" / "infra_probe.py"
OPERATION_DOC = ROOT / "doc" / "operation" / "OpenBase-本地备用基础设施安装与主备切换记录-v1.12.0.md"

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
    """运维记录升 v1.12.0 并登记 §16 / §16.7 / §16.8 / §16.9。"""
    assert OPERATION_DOC.exists(), f"缺少运维记录: {OPERATION_DOC}"
    text = OPERATION_DOC.read_text(encoding="utf-8-sig")
    assert "v1.12.0" in text
    assert "## 16. 启动期自动探测与主备切换" in text
    assert "### 16.7 周期复检与公共设施探测" in text
    assert "### 16.8 数据面探针与四设施切换" in text
    assert "### 16.9 每次启动前的数据库校验" in text
    for marker in (
        "-Action dbcheck",
        "-DbMode",
        "127.0.0.1:5432",
        "退出码 2",
        "-DbRecheckSec",
        "-ProbeLevel",
        "-ProbeTtlSec",
        "db-monitor-recheck-",
        "不自动回切",
        "数据面同步",
        "启动前数据面校验",
    ):
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


# ---------------------------------------------------------------------------
# 3. Phase 2（P1）：JSON 输出 / 周期复检 / 公共设施探测
# ---------------------------------------------------------------------------


def test_phase2_contract_declared() -> None:
    """Phase 2 契约标记齐备（JSON 输出、复检间隔、公共设施探测、复检证据）。"""
    text = _text()
    for marker in (
        "[switch]$Json",
        "[int]$DbRecheckSec = 0",
        "Invoke-DbChannelRecheck",
        "Test-TcpEndpoint",
        "Get-InfraTargets",
        "dependencies",
        "db-monitor-recheck-",
        "不自动回切",
    ):
        assert marker in text, f"缺少 Phase 2 契约标记: {marker}"


def test_infra_probe_is_advisory_only() -> None:
    """公共设施探测只提示不阻断（PG 为唯一硬门禁），且仅在可启动动作下执行。"""
    text = _text()
    assert "不阻断启动" in text
    assert "@('start', 'startcheck', 'monitor', 'dbcheck')" in text


def test_monitor_recheck_default_interval_at_least_60s() -> None:
    """周期复检默认不小于 60s（避免探测拖慢自愈循环），且可显式缩短。"""
    text = _text()
    assert "[Math]::Max(60, $Interval)" in text
    assert "if ($DbRecheckSec -gt 0)" in text


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@needs_powershell
def test_dbcheck_json_off_mode(tmp_path: Path) -> None:
    """`dbcheck -Json -DbMode off` ⇒ 退出码 0，stdout 为纯 JSON（resolved_mode=off）。"""
    completed = _run(tmp_path, "-Action", "dbcheck", "-DbMode", "off", "-Json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout.strip())
    assert payload["ok"] is True
    assert payload["resolved_mode"] == "off"


@needs_powershell
def test_dbcheck_json_reports_unavailable_and_dependencies(tmp_path: Path) -> None:
    """强制备用但不可达 ⇒ 退出码 2；stdout 为纯 JSON，含 dependencies 字段。"""
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
            "dbcheck",
            "-DbMode",
            "standby",
            "-Json",
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
    payload = json.loads(completed.stdout.strip())
    assert payload["ok"] is False
    assert payload["resolved_mode"] == "unavailable"
    assert "dependencies" in payload
    assert "data_plane" in payload
    assert payload["evidence_path"]


@needs_powershell
def test_monitor_recheck_notices_primary_recovery(tmp_path: Path) -> None:
    """monitor 周期复检：运行在备用通道且主用恢复 ⇒ 仅提示 + 落证据，不启动任何服务。"""
    if not _port_open("127.0.0.1", 5432):
        pytest.skip("本机备用库 127.0.0.1:5432 不可达，跳过周期复检用例")
    if not _port_open("192.168.0.151", 5432):
        pytest.skip("主用共享库 192.168.0.151:5432 不可达，跳过主用恢复提示用例")
    assert POWERSHELL is not None

    proc = subprocess.Popen(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ORCHESTRATOR),
            "-Action",
            "monitor",
            "-Only",
            "__none__",          # 不匹配任何服务 ⇒ 不启动、不重启
            "-Interval",
            "1",
            "-DbRecheckSec",
            "1",
            "-DbMode",
            "standby",
            "-LogRoot",
            str(tmp_path / "logs"),
            "-ServiceLogRoot",
            str(tmp_path / "svc-logs"),
        ],
        cwd=ROOT,
        env=_base_env(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    evidence: list[Path] = []
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            evidence = list((tmp_path / "evidence").glob("db-monitor-recheck-*.json"))
            if evidence:
                break
            time.sleep(0.5)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)

    assert evidence, "monitor 未产生周期复检证据（db-monitor-recheck-*.json）"
    payload = json.loads(evidence[0].read_text(encoding="utf-8-sig"))
    assert payload["action"] == "monitor-recheck"
    assert payload["current_mode"] == "standby"
    assert payload["desired_mode"] == "primary"
    assert "主用共享库已恢复" in payload["notice"]
    # 只提示不回切：`-Only __none__` 下不应产生任何服务日志目录
    svc_log_root = tmp_path / "svc-logs"
    assert not svc_log_root.exists() or not any(svc_log_root.iterdir())


# ---------------------------------------------------------------------------
# 4. Phase 3（P0）：数据面探针 + 主用不通切备用（含四设施）
# ---------------------------------------------------------------------------


def test_data_plane_contract_declared() -> None:
    """编排侧数据面契约标记齐备（探针脚本、层级开关、切换函数、证据字段）。"""
    text = _text()
    for marker in (
        "scripts\\infra_probe.py",
        "[string]$ProbeLevel = 'auto'",
        "Get-ProbePython",
        "New-InfraProbeSpec",
        "Invoke-DataPlaneProbe",
        "Set-InfraStandbyOverrides",
        "OPENBASE_INFRA_STANDBY_HOST",
        "data_plane",
        "数据面同步问题暂时挂起",
        "Assert-ServiceDataPlane",
        "Get-ServiceInfraDeps",
        "Update-DataPlaneProbe",
        "[int]$ProbeTtlSec = 60",
    ):
        assert marker in text, f"缺少数据面契约标记: {marker}"


def test_every_service_start_checks_data_plane() -> None:
    """每次真正启动服务前都做数据面校验（全量 / -Only 单服务 / monitor 自愈统一入口）。"""
    text = _text()
    start_idx = text.index("function Start-Service")
    check_idx = text.index("if (-not (Assert-ServiceDataPlane -Svc $Svc))", start_idx)
    dep_idx = text.index("# 3) 依赖健康检查", start_idx)
    assert check_idx < dep_idx, "数据面校验必须早于依赖健康检查"

    # 服务 → 设施依赖映射必须覆盖全部带数据库依赖的服务
    for mapping in (
        "openbase   = @('pg', 'redis')",
        "dps        = @('pg')",
        "openllm    = @('pg', 'redis')",
        "openrag    = @('pg', 'qdrant')",
        "openmemory = @('pg', 'redis', 'qdrant', 'neo4j')",
        "frontend   = @()",
    ):
        assert mapping in text, f"缺少服务依赖映射: {mapping}"

    # 共享库不可用必须拒绝该服务启动（不能静默继续）
    assert "启动前数据面校验失败" in text
    assert "拒绝启动该服务" in text


def test_probe_script_is_stdlib_only() -> None:
    """探针脚本不得引入第三方依赖（本机 .venv 不保证有 redis/qdrant/psycopg）。"""
    text = PROBE_SCRIPT.read_text(encoding="utf-8")
    for banned in ("import requests", "import redis", "import qdrant_client", "import psycopg", "import minio"):
        assert banned not in text, f"探针脚本不得依赖: {banned}"
    assert "def main(" in text


def _run_probe(tmp_path: Path, spec: dict, env: dict[str, str] | None = None) -> tuple[dict, str]:
    spec_path = tmp_path / "spec.json"
    out_path = tmp_path / "out.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-S", "-B", str(PROBE_SCRIPT), "--spec", str(spec_path), "--out", str(out_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **(env or {})},
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    raw = out_path.read_text(encoding="utf-8")
    return json.loads(raw), raw


def test_probe_reports_closed_ports_as_unhealthy(tmp_path: Path) -> None:
    """全端点不可达 ⇒ 全部 ok=false；psql 缺失时 PG 明确降级为 TCP 并写入 degraded。"""
    spec = {
        "timeout_sec": 1,
        "psql": str(tmp_path / "missing-psql.exe"),
        "targets": {
            "pg": {"primary": {"host": "127.0.0.1", "port": 1, "user": "u", "password": "p", "database": "d"}},
            "redis": {"primary": {"host": "127.0.0.1", "port": 1, "password": ""}},
            "qdrant": {"primary": {"url": "http://127.0.0.1:1"}},
            "neo4j": {"primary": {"host": "127.0.0.1", "http_port": 1, "user": "u", "password": "p"}},
            "minio": {"primary": {"host": "127.0.0.1", "port": 1}},
        },
    }
    payload, _ = _run_probe(tmp_path, spec)
    assert payload["schema_version"] == 1
    assert set(payload["targets"]) == {
        "pg.primary",
        "redis.primary",
        "qdrant.primary",
        "neo4j.primary",
        "minio.primary",
    }
    assert all(entry["ok"] is False for entry in payload["targets"].values())
    assert payload["targets"]["pg.primary"]["layer"] == "tcp"
    assert any(item.startswith("pg.primary") for item in payload["degraded"])


def test_probe_never_emits_credentials(tmp_path: Path) -> None:
    """口令只经环境变量读取，输出中不得出现明文。"""
    secret = "SuperSecret-9f3c"
    spec = {
        "timeout_sec": 1,
        "targets": {
            "redis": {"primary": {"host": "127.0.0.1", "port": 1, "password_env": "PROBE_TEST_SECRET"}},
        },
    }
    payload, raw = _run_probe(tmp_path, spec, env={"PROBE_TEST_SECRET": secret})
    assert secret not in raw
    assert payload["targets"]["redis.primary"]["ok"] is False


@needs_powershell
def test_primary_infrastructure_outage_switches_to_standby(tmp_path: Path) -> None:
    """主用设施数据面不通 ⇒ 切本机备用、覆盖环境键并留痕（以 MinIO 为主备均在线的实例）。"""
    if not _port_open("127.0.0.1", 9000):
        pytest.skip("本机备用 MinIO 127.0.0.1:9000 未运行，跳过切换用例")
    assert POWERSHELL is not None

    env = _base_env(tmp_path)
    env["MINIO_HOST"] = "127.0.0.1"
    env["MINIO_PORT"] = "1"          # 主用数据面不可达（连接拒绝）
    completed = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ORCHESTRATOR),
            "-Action",
            "dbcheck",
            "-Json",
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
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout.strip())

    minio = payload["dependencies"]["minio"]
    assert minio["Switched"] is True
    assert minio["Host"] == "127.0.0.1"
    assert int(minio["Port"]) == 9000
    assert "minio" in payload["data_plane"]["switched"]
    assert "MINIO_HOST" in payload["data_plane"]["applied"]["minio"]
    assert payload["data_plane"]["probe_mode"] == "data-plane"

