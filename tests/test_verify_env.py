"""P2-1 T9 RED 断言：OB-9 verify-env 雏形（§9.2/§10 T9）.

对齐草案 §10 T9：
- T9-1  `scripts/verify-env/contract.json` 存在且 schema 校验通过（含本批新键 +
        映射对账 + 契约轨标记）
- T9-2  `scripts/verify-env.ps1` 可执行：缺键/端口不可达/白名单不一致 → WARN +
        退出码区分；`--fail-fast` 置错即失败
- T9-3  白名单矩阵对账：trusted_proxy_sources 与 contract 不一致 → 报告可定位
- T9-4  映射对账：dps_code_map 冲突/校验错误 → 报告冲突项（ERROR）
- T9-5  DB 检查位：连接 + schema（openbase）可探（配合 OB-7 登记）
- T9-6  报告输出 `verify-env-report.json` 且含 WARN/ERROR 清单

执行依赖：Windows PowerShell 5+（powershell.exe）；契约/快照经文件注入，
不依赖真实 DB/服务（连通性结果由快照预置，离线可测）。每场景单次 spawn
（本机 powershell 冷启动约 10s，故按场景聚合 spawn）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify-env.ps1"
CONTRACT = ROOT / "scripts" / "verify-env" / "contract.json"

# contract config_single_source 中非 deprecated 且非明文密钥的必检键
_REQUIRED_SINGLE_SOURCE_KEYS = {
    "trusted_proxy_sources",
    "role_intertranslate",
    "dps_code_map",
    "service_account_subject_map",
    "enforce_org_alias",
    "enforce_token_version",
    "k03_bypass_whitelist",
    "strip_inbound_identity_headers",
    "enforce_inbound_identity_headers",
    "enforce_proxy_identity_headers",
    "db_url",
    "redis_url",
}

_EXPECTED_WHITELIST = [
    "openbase-dps-proxy",
    "openbase-llm-proxy",
    "openbase-rag-proxy",
    "openbase-memory-proxy",
    "openbase-generic-proxy",
]


def _powershell_executable() -> str | None:
    """解析 powershell.exe（Windows PowerShell 5+）. """
    candidate = shutil.which("powershell")
    if candidate:
        return candidate
    standard = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    return str(standard) if standard.exists() else None


POWERSHELL = _powershell_executable()

needs_powershell = pytest.mark.skipif(
    POWERSHELL is None, reason="Windows PowerShell 5+ not available"
)


def _load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _write_json(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _read_report(tmp_path: Path) -> dict:
    # PS5 Out-File -Encoding utf8 输出带 BOM，用 utf-8-sig 解码
    return json.loads(
        (tmp_path / "verify-env-report.json").read_text(encoding="utf-8-sig")
    )


def _issue_codes(tmp_path: Path) -> list[str]:
    return [issue["code"] for issue in _read_report(tmp_path)["issues"]]


def _clean_snapshot() -> dict:
    """合法快照：全部必检键存在、白名单与契约一致、无网络/DB 告警."""
    return {
        "schema_version": 1,
        "config": {key: "" for key in _REQUIRED_SINGLE_SOURCE_KEYS},
        "trusted_proxy_sources_list": list(_EXPECTED_WHITELIST),
        "deprecated_configured": {},
        "jwt_secret_ok": True,
        "upstreams_reachability": {},
        "db_checks": {
            "reachable": True,
            "probed": True,
            "schema": "openbase",
            "note": "tenants.code 唯一事实源对账",
        },
        "dps_code_map": {
            "entries_count": 0,
            "validation_errors": [],
            "conflicts": [],
            "known_tenant_codes_from_db": True,
        },
    }


def _run_verify_env(
    tmp_path: Path,
    snapshot: dict,
    *,
    fail_fast: bool = False,
) -> subprocess.CompletedProcess[str]:
    """以注入快照运行 verify-env.ps1（离线；返回 completed + 落盘报告）."""
    snapshot_path = _write_json(tmp_path, "snapshot.json", snapshot)
    report_path = tmp_path / "verify-env-report.json"
    command = [
        POWERSHELL,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-ContractPath",
        str(CONTRACT),
        "-SnapshotPath",
        str(snapshot_path),
        "-OutputPath",
        str(report_path),
    ]
    if fail_fast:
        command.append("-FailFast")
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert report_path.exists(), (
        f"report missing: {report_path}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _warn_mix_snapshot() -> dict:
    """WARN 场景集：缺键 + deprecated 已配置 + 白名单不一致 + 端口不可达 + DB 检查位不可达."""
    snapshot = _clean_snapshot()
    del snapshot["config"]["dps_code_map"]
    snapshot["deprecated_configured"] = {"dps_default_tenant_id": "tenant-1"}
    snapshot["trusted_proxy_sources_list"] = ["openbase-dps-proxy", "rogue-source"]
    snapshot["upstreams_reachability"] = {"dps_upstream_base": False}
    snapshot["db_checks"]["reachable"] = False
    return snapshot


# ---------------------------------------------------------------------------
# T9-1：contract.json 契约清单（存在 + schema 校验通过 + 契约轨标记）
# ---------------------------------------------------------------------------


def test_t9_1_contract_exists_and_schema_valid() -> None:
    """契约清单存在、schema 合法、含本批全部新键与契约轨标记."""
    assert CONTRACT.exists(), f"契约清单缺失: {CONTRACT}"
    contract = _load_contract()
    assert contract["schema_version"] == 1
    sections = contract["sections"]
    for section_name in (
        "config_single_source",
        "config_deprecated",
        "upstreams",
        "whitelist_matrix",
        "mapping_reconcile",
        "db_checks",
    ):
        assert section_name in sections, f"契约 sections 缺少 {section_name}"
    keys = set(sections["config_single_source"])
    assert _REQUIRED_SINGLE_SOURCE_KEYS <= keys, (
        f"config_single_source 缺键: {_REQUIRED_SINGLE_SOURCE_KEYS - keys}"
    )
    assert "dps_default_org_id" in sections["config_deprecated"]
    assert "dps_default_tenant_id" in sections["config_deprecated"]
    assert sections["whitelist_matrix"]["trusted_proxy_sources"] == _EXPECTED_WHITELIST
    assert sections["mapping_reconcile"] == ["dps_code_map"]
    assert sections["db_checks"][0]["schema"] == "openbase"
    assert "tracking" in contract, "契约缺少 tracking.contract_rail 标记"
    assert contract["tracking"]["contract_rail"]


def test_t9_1_artifacts_present() -> None:
    """verify-env 雏形产物齐备（脚本 + 契约 + snapshot 采集助手）. """
    assert SCRIPT.exists(), f"verify-env.ps1 缺失: {SCRIPT}"
    assert (ROOT / "scripts" / "verify-env" / "snapshot.py").exists()
    script = (ROOT / "scripts" / "audit_dps_code_map.py").read_text(encoding="utf-8")
    assert "dps_code_map_conflicts" in script
    assert "validate_dps_code_map" in script


# ---------------------------------------------------------------------------
# T9-1（可执行）：clean snapshot → exit 0
# ---------------------------------------------------------------------------


@needs_powershell
def test_t9_1_script_clean_run_exit_zero(tmp_path: Path) -> None:
    """契约 schema 校验通过（clean snapshot → verify-env 退出 0 无 finding）."""
    result = _run_verify_env(tmp_path, _clean_snapshot())
    assert result.returncode == 0, result.stdout + result.stderr
    report = _read_report(tmp_path)
    assert report["summary"]["warnings"] == 0
    assert report["summary"]["errors"] == 0
    assert report["issues"] == []


# ---------------------------------------------------------------------------
# T9-2/T9-3/T9-5：缺键/端口不可达/白名单不一致/DB 检查位 → WARN + 退出码 1
# ---------------------------------------------------------------------------


@needs_powershell
def test_t9_2_3_5_warn_scenarios_reported(tmp_path: Path) -> None:
    """WARN 场景集：缺键/端口不可达/白名单不一致/DB 检查位 → WARN + 退出码 1."""
    result = _run_verify_env(tmp_path, _warn_mix_snapshot())
    assert result.returncode == 1, result.stdout + result.stderr
    report = _read_report(tmp_path)
    codes = [issue["code"] for issue in report["issues"]]
    for expected_code in (
        "CONFIG_KEY_MISSING",  # T9-2 缺键
        "UPSTREAM_UNREACHABLE",  # T9-2 端口不可达
        "WHITELIST_MISMATCH",  # T9-2/T9-3 白名单矩阵对账（可定位）
        "DEPRECATED_KEY_USED",  # T7-6 deprecated 提示
        "DB_CHECK_UNREACHABLE",  # T9-5 DB 检查位
    ):
        assert expected_code in codes, f"报告缺少 {expected_code}: {codes}"
    assert report["summary"]["warnings"] >= 5
    assert report["summary"]["errors"] == 0
    assert report["summary"]["exit_code"] == 1
    # T9-3：白名单不一致报告可定位（含 expected/actual 与 rogue-source）
    whitelist_issues = [
        issue["message"]
        for issue in report["issues"]
        if issue["section"] == "whitelist_matrix"
        and issue["code"] == "WHITELIST_MISMATCH"
    ]
    assert whitelist_issues
    assert "expected=" in whitelist_issues[0]
    assert "rogue-source" in whitelist_issues[0]


# ---------------------------------------------------------------------------
# T9-2：--fail-fast 置错即失败
# ---------------------------------------------------------------------------


@needs_powershell
def test_t9_2_fail_fast_aborts_nonzero(tmp_path: Path) -> None:
    """--fail-fast：WARN 场景即失败（退出非 0）且报告已落盘."""
    result = _run_verify_env(tmp_path, _warn_mix_snapshot(), fail_fast=True)
    assert result.returncode != 0, result.stdout + result.stderr
    report = _read_report(tmp_path)
    assert report["summary"]["fail_fast"] is True
    assert report["summary"]["exit_code"] != 0
    assert report["issues"], "fail-fast 应至少携带首个 finding"


# ---------------------------------------------------------------------------
# T9-4/T9-6：映射对账 ERROR + 报告 WARN/ERROR 清单
# ---------------------------------------------------------------------------


@needs_powershell
def test_t9_4_6_mapping_errors_and_report_lists(tmp_path: Path) -> None:
    """映射对账冲突/校验错误 → ERROR + exit 2；报告含 WARN/ERROR 两类清单."""
    snapshot = _warn_mix_snapshot()
    snapshot["dps_code_map"] = {
        "entries_count": 2,
        "validation_errors": ["entries[0].dps_tenant_id is required and non-empty"],
        "conflicts": [
            {
                "tenant_code": "acme",
                "mappings": [
                    {"tenant_code": "acme", "dps_org_id": "u-1", "dps_tenant_id": "u-1"},
                    {"tenant_code": "acme", "dps_org_id": "u-2", "dps_tenant_id": "u-2"},
                ],
                "reason": "same tenant_code maps different dps org/tenant ids",
            }
        ],
        "known_tenant_codes_from_db": True,
    }
    result = _run_verify_env(tmp_path, snapshot)
    assert result.returncode == 2, result.stdout + result.stderr
    report = _read_report(tmp_path)
    codes = [issue["code"] for issue in report["issues"]]
    assert "DPS_CODE_MAP_CONFLICT" in codes, f"缺冲突项: {codes}"
    assert "DPS_CODE_MAP_INVALID" in codes, f"缺校验错误: {codes}"
    assert report["summary"]["errors"] >= 2
    assert report["summary"]["warnings"] >= 1  # WARN 与 ERROR 并存
    severities = {issue["severity"] for issue in report["issues"]}
    assert "WARN" in severities and "ERROR" in severities
    assert report["summary"]["exit_code"] == 2
    assert report["schema_version"] == 1
