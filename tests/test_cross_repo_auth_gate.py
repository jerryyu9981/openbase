"""D 批 D2 门禁回归：跨系统授权一致性门禁不得出现 FAIL.

复用 `scripts/cross_repo_auth_gate.py` 的检查函数（同一实现，避免两处漂移）。
若同级仓（OpenLLM/OpenRAG/OpenMemory/DPS）不可达，则**跳过**（本仓独立可测的检查仍执行）——
故本用例在无兄弟仓的 CI 环境中不会误报失败。

判定口径：**FAIL 视为回归**；WARN 为「静态解析限制，需人工核对或由该仓自有用例覆盖」，不算失败。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_gate_module():
    spec = importlib.util.spec_from_file_location(
        "cross_repo_auth_gate", ROOT / "scripts" / "cross_repo_auth_gate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_matrix_artifact_is_complete() -> None:
    """D1 一致性矩阵须结构完整（覆盖全部系统与不变式，每格齐备）."""
    gate = _load_gate_module()
    report = gate.Report()

    gate.check_matrix(report)

    failures = [r for r in report.results if r.status == "FAIL"]
    assert not failures, f"矩阵完整性不合格：{[r.detail for r in failures]}"


def test_code_space_registration_invariant_holds() -> None:
    """C1-a 固化防线：各目标兜底码非自身保留码，且已被目标登记."""
    gate = _load_gate_module()
    report = gate.Report()

    gate.check_code_space(report)

    failures = [r for r in report.results if r.status == "FAIL"]
    assert not failures, f"码空间登记不一致：{[r.detail for r in failures]}"


def test_reserved_codes_not_relaxed() -> None:
    """保留码防护未被静默放宽（OpenBase/OpenRAG/DPS 仍显式声明）."""
    gate = _load_gate_module()
    report = gate.Report()

    gate.check_reserved_not_relaxed(report)

    failures = [r for r in report.results if r.status == "FAIL"]
    assert not failures, f"保留码声明缺失：{[r.detail for r in failures]}"


def test_error_code_map_literals_exist_in_targets() -> None:
    """错误码映射表的每个目标字面量须可在该仓源码中检索到（防「表里写了、码不存在」）."""
    gate = _load_gate_module()
    if not (gate.REPO_DIRS["openrag"]).exists():
        pytest.skip("同级仓不可达，跳过跨仓检索")
    report = gate.Report()

    gate.check_error_codes(report)

    failures = [r for r in report.results if r.status == "FAIL"]
    assert not failures, f"错误码映射与目标仓不一致：{[r.detail for r in failures]}"
