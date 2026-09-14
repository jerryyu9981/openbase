"""C-17 错误归因分析器测试（TDD：先 RED，后实现）.

被测：``scripts/test_log_analyze.py``（方案 §5 批 4 C-17、§11.5 归因矩阵、§11.6 输出口径）
- 输入：``logs/**/*.jsonl``（C-1 落盘 + C-3 用例上下文 + C-15/C-16 观测字段）
- 输出：``doc/test/evidence/manual/<run_id>-analysis.md``（**不含响应明文**）
- 统一退出码：``0`` = 无失败；``1`` = 存在失败步骤；``2`` = PENDING（无记录）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test_log_analyze.py"

SENSITIVE_PHONE = "13812345678"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_log_analyze", SCRIPT)
    assert spec and spec.loader, f"无法加载分析脚本: {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_log_analyze"] = module
    spec.loader.exec_module(module)
    return module


def _line(
    *,
    request_id: str,
    run_id: str = "run-analyze-1",
    case_id: str,
    step_id: int,
    status_code: int,
    path: str = "/api/v1/proxy/dps/api/v2/portrait/list",
    **extra: Any,
) -> str:
    """构造一行 L1 记录（JSONL），可叠加 C-15/C-16 观测字段."""
    payload: dict[str, Any] = {
        "ts": "2026-09-14T03:00:00.000+00:00",
        "level": "INFO",
        "service": "openbase",
        "module": "openbase.audit",
        "message": "api.request",
        "env": "dev",
        "version": "abc1234",
        "request_id": request_id,
        "method": "GET",
        "path": path,
        "status_code": status_code,
        "duration_ms": 15,
        "channel": "B",
        "case_id": case_id,
        "step_id": step_id,
        "run_id": run_id,
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def _write_logs(root: Path, lines: list[str]) -> None:
    directory = root / "openbase"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "openbase-20260914.jsonl").write_text("\n".join(lines), encoding="utf-8")


# ---- 归因矩阵（§11.5） ----


def test_attribute_matrix_covers_design_rows() -> None:
    """归因矩阵逐行核对：鉴权/信任链/K03/网络/上游/契约. """
    module = _load_script()
    cases = [
        ({"status_code": 401, "resp_error_code": "AUTH_401"}, "网关鉴权"),
        (
            {"status_code": 403, "resp_error_code": "PERM_UNTRUSTED_IDENTITY_HEADER"},
            "网关信任链",
        ),
        (
            {"status_code": 403, "resp_error_code": "PERM_SERVICE_KEY_WRITE_DENIED"},
            "网关 K03",
        ),
        ({"status_code": 502, "resp_error_code": "SYS_UPSTREAM_ERROR"}, "网络/上游不可达"),
        (
            {"status_code": 500, "upstream_status": 500, "upstream_error_code": "UPSTREAM_500"},
            "上游子系统",
        ),
        ({"status_code": 200}, "无错误"),
    ]
    for record, expected_layer in cases:
        layer, suggestion = module.attribute(record)
        assert layer == expected_layer, f"{record} 应归因 {expected_layer}，实际 {layer}"
        assert suggestion, "每行必须给出可执行建议"


def test_attribute_prefers_upstream_over_gateway_5xx() -> None:
    """上游 5xx 透传为网关 5xx 时，应归因到**上游子系统**（而非网关系统错误）. """
    module = _load_script()
    layer, suggestion = module.attribute(
        {"status_code": 500, "resp_error_code": "SYS_INTERNAL_ERROR", "upstream_status": 503}
    )
    assert layer == "上游子系统"
    assert "request_id" in suggestion or "上游日志" in suggestion


# ---- 端到端：报告产出与退出码 ----


def _mixed_logs(root: Path) -> None:
    _write_logs(
        root,
        [
            _line(request_id="req-1", case_id="UI-DPS-0007", step_id=3, status_code=403,
                  resp_error_code="PERM_UNTRUSTED_IDENTITY_HEADER"),
            _line(request_id="req-2", case_id="UI-DPS-0007", step_id=5, status_code=200),
            _line(request_id="req-3", case_id="UI-DPS-0011", step_id=2, status_code=502,
                  resp_error_code="SYS_UPSTREAM_ERROR"),
            _line(request_id="req-4", case_id="UI-DPS-0014", step_id=5, status_code=500,
                  upstream_system="dps", upstream_status=500, upstream_error_code="UPSTREAM_500",
                  upstream_duration_ms=88, upstream_digest="sha256:abcdef0123456789"),
        ],
    )


def test_analyze_writes_report_with_attribution(tmp_path: Path) -> None:
    """存在失败 → 退出码 1，报告含归因表与首现标记. """
    module = _load_script()
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "out"
    _mixed_logs(logs_root)

    exit_code = module.main(["--logs-root", str(logs_root), "--out-dir", str(out_dir)])

    assert exit_code == 1
    report = out_dir / "run-analyze-1-analysis.md"
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "UI-DPS-0007" in content
    assert "网关信任链" in content
    assert "网络/上游不可达" in content
    assert "上游子系统" in content
    assert "req-4" in content
    # 首现标记：每个用例仅首个失败步骤为「是」
    assert content.count("| 是 |") >= 1
    # 证据引用列：digest 引用（不含响应明文）
    assert "sha256:abcdef0123456789" in content


def test_analyze_never_prints_response_plaintext(tmp_path: Path) -> None:
    """红线：报告只含状态/摘要/request_id，不含响应摘要原文（隐私不入证据）. """
    module = _load_script()
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "out"
    _write_logs(
        logs_root,
        [
            _line(
                request_id="req-pii",
                case_id="UI-DPS-0020",
                step_id=1,
                status_code=403,
                resp_error_code="PERM_UNTRUSTED_IDENTITY_HEADER",
                resp_summary={"message": f"联系人 {SENSITIVE_PHONE} 无权限"},
            )
        ],
    )
    module.main(["--logs-root", str(logs_root), "--out-dir", str(out_dir)])
    content = (out_dir / "run-analyze-1-analysis.md").read_text(encoding="utf-8")
    assert SENSITIVE_PHONE not in content


def test_analyze_all_pass_returns_zero(tmp_path: Path) -> None:
    """全部步骤成功 → 退出码 0（无失败）. """
    module = _load_script()
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "out"
    _write_logs(
        logs_root,
        [
            _line(request_id="req-a", case_id="S0-1", step_id=1, status_code=200),
            _line(request_id="req-b", case_id="S0-1", step_id=2, status_code=200),
        ],
    )
    assert module.main(["--logs-root", str(logs_root), "--out-dir", str(out_dir)]) == 0


def test_analyze_no_records_is_pending(tmp_path: Path) -> None:
    """无记录 → 退出码 2 且**不产出**报告（避免证据污染）. """
    module = _load_script()
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "out"
    logs_root.mkdir(parents=True, exist_ok=True)

    assert module.main(["--logs-root", str(logs_root), "--out-dir", str(out_dir)]) == 2
    assert not out_dir.exists() or not list(out_dir.glob("*.md"))


def test_analyze_run_id_filter(tmp_path: Path) -> None:
    """``--run-id`` 只分析指定轮次（其他 run 的同名用例不混入）. """
    module = _load_script()
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "out"
    _write_logs(
        logs_root,
        [
            _line(request_id="req-x", run_id="run-A", case_id="S0-1", step_id=1, status_code=403,
                  resp_error_code="PERM_UNTRUSTED_IDENTITY_HEADER"),
            _line(request_id="req-y", run_id="run-B", case_id="S0-1", step_id=1, status_code=200),
        ],
    )
    assert module.main(
        ["--logs-root", str(logs_root), "--out-dir", str(out_dir), "--run-id", "run-B"]
    ) == 0
    report = out_dir / "run-B-analysis.md"
    assert report.exists()
    assert "req-y" in report.read_text(encoding="utf-8")
