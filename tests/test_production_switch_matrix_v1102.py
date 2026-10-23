"""v1.10.2（XR-OPS-06 S4）：生产必需开关矩阵发布核验脚本用例.

覆盖：矩阵结构、env 解析、carrier 通过/取值漂移/载体缺失、env-file 实际下发核验、
``--only`` 过滤。全部基于临时目录，不依赖兄弟仓真实文件。
"""
from __future__ import annotations

import json

import pytest

from scripts.verify_production_switches import (
    FAIL,
    PASS,
    check_carrier_repo,
    check_env_file,
    load_matrix,
    parse_env_assignments,
    run_carrier_check,
)

OPENLLM_SWITCHES = (
    "ENFORCE_INBOUND_IDENTITY_HEADERS",
    "RBAC_PERMISSION_ENFORCE",
    "TENANT_SCOPE_ENFORCE",
    "TENANT_HEADER_CONSISTENCY_ENFORCE",
    "QUOTA_MISSING_FAIL_CLOSED",
)


def _matrix(repo_switches: dict[str, str] | None = None, carriers: list[str] | None = None) -> dict:
    return {
        "version": "1.0.0",
        "repos": {
            "OpenLLM": {
                "carriers": carriers or [".env.example"],
                "switches": repo_switches or {key: "true" for key in OPENLLM_SWITCHES},
            },
            "OpenBase": {"carriers": [], "switches": {}},
        },
    }


def _write_repo(tmp_path, name: str, files: dict[str, str]):  # noqa: ANN001
    repo_root = tmp_path / name
    repo_root.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return repo_root


def test_repo_matrix_contains_openllm_five_switches():
    """仓库内矩阵为唯一事实源：OpenLLM 5 组启动门禁必须在内。"""
    matrix = load_matrix(__import__("pathlib").Path("config/production_switch_matrix.json"))
    switches = matrix["repos"]["OpenLLM"]["switches"]
    for key in OPENLLM_SWITCHES:
        assert switches.get(key) == "true"
    assert matrix["repos"]["OpenMemory"]["switches"]["OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE"] == "true"
    assert matrix["repos"]["DPS"]["switches"]["TENANT_CONTEXT_REQUIRED"] == "true"


def test_parse_env_assignments_handles_comments_exports_and_quotes():
    text = """
# comment
export TENANT_SCOPE_ENFORCE=true
QUOTA_MISSING_FAIL_CLOSED = "true"
OTHER=1  # inline
BAD_LINE
"""
    values = parse_env_assignments(text)
    assert values["TENANT_SCOPE_ENFORCE"] == "true"
    assert values["QUOTA_MISSING_FAIL_CLOSED"] == "true"
    assert values["OTHER"] == "1"
    assert "BAD_LINE" not in values


def test_carrier_pass_when_all_switches_true(tmp_path):
    repo_root = _write_repo(
        tmp_path,
        "OpenLLM",
        {".env.example": "\n".join(f"{key}=true" for key in OPENLLM_SWITCHES)},
    )
    results = check_carrier_repo("OpenLLM", repo_root, _matrix()["repos"]["OpenLLM"])
    assert all(item.status == PASS for item in results)
    assert len(results) == 5


def test_carrier_fail_when_value_drifts(tmp_path):
    repo_root = _write_repo(
        tmp_path,
        "OpenLLM",
        {".env.example": "TENANT_SCOPE_ENFORCE=false\n" + "\n".join(
            f"{key}=true" for key in OPENLLM_SWITCHES if key != "TENANT_SCOPE_ENFORCE"
        )},
    )
    results = check_carrier_repo("OpenLLM", repo_root, _matrix()["repos"]["OpenLLM"])
    failed = [item for item in results if item.status == FAIL]
    assert len(failed) == 1
    assert failed[0].key == "TENANT_SCOPE_ENFORCE"
    assert "false" in failed[0].detail


def test_carrier_fail_when_missing(tmp_path):
    repo_root = _write_repo(tmp_path, "OpenLLM", {"README.md": "no carrier"})
    results = check_carrier_repo("OpenLLM", repo_root, _matrix()["repos"]["OpenLLM"])
    assert all(item.status == FAIL for item in results)
    assert "载体缺失" in results[0].detail


def test_doc_carrier_matches_table_style(tmp_path):
    """DPS 无 .env.example，文档表格中登记生产值也应判 PASS。"""
    repo_root = _write_repo(
        tmp_path,
        "DPS",
        {"doc/operation/DPS-部署文档-v2.1.0.md": "| `TENANT_CONTEXT_REQUIRED` | 必填 | true |\n"},
    )
    spec = {"carriers": ["doc/operation/DPS-部署文档-v2.1.0.md"], "switches": {"TENANT_CONTEXT_REQUIRED": "true"}}
    results = check_carrier_repo("DPS", repo_root, spec)
    assert results[0].status == PASS


def test_env_file_mode_detects_missing_and_mismatch(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text("TENANT_SCOPE_ENFORCE=false\n", encoding="utf-8")
    results = check_env_file(
        "OpenLLM", env_file, {"TENANT_SCOPE_ENFORCE": "true", "RBAC_PERMISSION_ENFORCE": "true"}
    )
    by_key = {item.key: item for item in results}
    assert by_key["TENANT_SCOPE_ENFORCE"].status == FAIL
    assert "false" in by_key["TENANT_SCOPE_ENFORCE"].detail
    assert by_key["RBAC_PERMISSION_ENFORCE"].status == FAIL
    assert "未下发" in by_key["RBAC_PERMISSION_ENFORCE"].detail


def test_env_file_mode_passes_when_complete(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text("TENANT_SCOPE_ENFORCE=true\nRBAC_PERMISSION_ENFORCE=true\n", encoding="utf-8")
    results = check_env_file(
        "OpenLLM", env_file, {"TENANT_SCOPE_ENFORCE": "true", "RBAC_PERMISSION_ENFORCE": "true"}
    )
    assert all(item.status == PASS for item in results)


def test_run_carrier_check_supports_only_filter(tmp_path):
    _write_repo(tmp_path, "OpenLLM", {".env.example": "\n".join(
        f"{key}=true" for key in OPENLLM_SWITCHES
    )})
    _write_repo(tmp_path, "OpenMemory", {".env.example": "OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=false\n"})
    matrix = _matrix()
    matrix["repos"]["OpenMemory"] = {
        "carriers": [".env.example"],
        "switches": {"OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE": "true"},
    }

    only_openllm = run_carrier_check(matrix, tmp_path, only="openllm")
    assert only_openllm.failed == []
    assert {item.repo for item in only_openllm.results} == {"OpenLLM"}

    all_repos = run_carrier_check(matrix, tmp_path)
    assert len(all_repos.failed) == 1
    assert all_repos.failed[0].repo == "OpenMemory"


def test_matrix_rejects_missing_repos(tmp_path):
    path = tmp_path / "matrix.json"
    path.write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_matrix(path)
