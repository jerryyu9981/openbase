"""上线验证脚本单元测试（T4-2）.

被测：``scripts/verify_release.py``（Step 5 上线验证自动化）。

覆盖其**纯函数**判定逻辑（无网络依赖）：
- 健康检查、鉴权门禁、统一错误契约、参数校验契约的通过与失败分支；
- 版本可见性三态（PASS / WARN / INFO）；
- 汇总计数与切流门禁退出码（存在 FAIL 即 1）；
- 本地发布基线读取（正常 / 配置缺失）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_release.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_release", SCRIPT)
    assert spec and spec.loader, f"无法加载上线验证脚本: {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_release"] = module
    spec.loader.exec_module(module)
    return module


verify_release = _load_script()

OK_BODY = '{"status":"ok"}'
AUTH_BODY = json.dumps(
    {"code": "AUTH_401", "message": "missing bearer token", "detail": None, "request_id": "req-abc123"}
)
PARAM_BODY = json.dumps(
    {
        "code": "PARAM_400",
        "message": "parameter validation error",
        "detail": [{"field": "username", "msg": "Field required", "input": {}}],
        "request_id": "req-def456",
    }
)


# ---- 健康检查 -----------------------------------------------------------------


def test_health_pass():
    assert verify_release.check_health(200, OK_BODY)[0] == verify_release.PASS


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (500, OK_BODY),
        (200, "not-json"),
        (200, '{"status":"degraded"}'),
    ],
)
def test_health_fail_branches(status, body):
    assert verify_release.check_health(status, body)[0] == verify_release.FAIL


# ---- 错误契约 -----------------------------------------------------------------


def test_error_contract_pass():
    state, detail = verify_release.check_error_contract(AUTH_BODY)
    assert state == verify_release.PASS
    assert "req-abc123" in detail


@pytest.mark.parametrize(
    "body",
    [
        "not-json",
        json.dumps({"code": "AUTH_401", "message": "x"}),  # 缺 detail / request_id
        json.dumps({"code": "AUTH_401", "message": "x", "detail": None, "request_id": "trace-1"}),
    ],
)
def test_error_contract_fail_branches(body):
    assert verify_release.check_error_contract(body)[0] == verify_release.FAIL


def test_auth_gate_pass_and_fail():
    assert verify_release.check_auth_gate(401, AUTH_BODY)[0] == verify_release.PASS
    assert verify_release.check_auth_gate(200, AUTH_BODY)[0] == verify_release.FAIL


# ---- 参数校验契约 -------------------------------------------------------------


def test_param_error_pass():
    state, detail = verify_release.check_param_error(400, PARAM_BODY)
    assert state == verify_release.PASS
    assert "1 项字段错误" in detail


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, PARAM_BODY),
        (400, json.dumps({"code": "BIZ_400", "message": "x", "detail": [], "request_id": "req-1"})),
        (400, json.dumps({"code": "PARAM_400", "message": "x", "detail": [], "request_id": "req-1"})),
    ],
)
def test_param_error_fail_branches(status, body):
    assert verify_release.check_param_error(status, body)[0] == verify_release.FAIL


# ---- 版本可见性 ---------------------------------------------------------------


def test_version_states():
    assert verify_release.check_version("1.4.7", "1.4.7")[0] == verify_release.PASS
    mismatch_state, mismatch_detail = verify_release.check_version("1.0.0", "1.4.7")
    assert mismatch_state == verify_release.WARN
    assert "openbase.__version__" in mismatch_detail
    assert verify_release.check_version("1.0.0", "")[0] == verify_release.INFO


# ---- 汇总与门禁 ---------------------------------------------------------------


def test_summarize_and_exit_code():
    results = [
        verify_release.Result("a", verify_release.PASS, ""),
        verify_release.Result("b", verify_release.WARN, ""),
        verify_release.Result("c", verify_release.INFO, ""),
    ]
    counts = verify_release.summarize(results)
    assert counts == {"PASS": 1, "WARN": 1, "FAIL": 0, "INFO": 1}
    assert verify_release.exit_code(results) == 0

    results.append(verify_release.Result("d", verify_release.FAIL, ""))
    assert verify_release.exit_code(results) == 1


# ---- 本地发布基线 -------------------------------------------------------------


def test_local_release_baseline_reads_config(tmp_path):
    config = tmp_path / "project-config.json"
    config.write_text(
        json.dumps({"project": {"version": "1.4.7", "lastRelease": "v1.4.7"}}), encoding="utf-8"
    )
    version, last_release = verify_release.local_release_baseline(config)
    assert version == "1.4.7"
    assert last_release == "v1.4.7"


def test_local_release_baseline_accepts_str_path(tmp_path):
    """CLI 传入的是字符串路径（现场运行发现的缺陷回归）."""
    config = tmp_path / "project-config.json"
    config.write_text(
        json.dumps({"project": {"version": "1.4.7", "lastRelease": "v1.4.7"}}), encoding="utf-8"
    )
    version, last_release = verify_release.local_release_baseline(str(config))
    assert version == "1.4.7"
    assert last_release == "v1.4.7"


def test_local_release_baseline_missing_file(tmp_path):
    version, last_release = verify_release.local_release_baseline(tmp_path / "absent.json")
    assert version == ""
    assert "读取失败" in last_release
