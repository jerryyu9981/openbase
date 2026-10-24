"""跨仓源码编码契约（UTF-8 BOM）回归。

判据单一事实源 = `scripts/scan_source_encoding.py`（跨仓扫描器，零第三方依赖）。

契约（policy 见扫描器模块常量）：
- `required_no_bom`（默认 `.py`）：**不得**带 UTF-8 BOM —— 违规即 FAIL（BOM 会使 `ast.parse(文本)`
  等源码扫描工具报 `SyntaxError: invalid non-printable character`）；
- `bom_expected`（默认 `.ps1`）：**允许/期望**带 BOM —— Windows PowerShell 5.1 对无 BOM 的 UTF-8
  按 GBK 解码（中文注释致解析失败），故豁免；
- 其余文本扩展名：仅统计上报（WARN，不计失败）。

本文件含**正控/负控**（反例自证）：在临时目录注入带 BOM 的 `.py` 必须被判违规、带 BOM 的 `.ps1`
必须被豁免 —— 以证明契约具备真实判别力，而非空跑通过。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCANNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "scan_source_encoding.py"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("scan_source_encoding", SCANNER_PATH)
    assert spec and spec.loader, f"扫描器不可加载: {SCANNER_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scanner_exists_and_is_stdlib_only():
    """契约工具必须存在且可加载（零第三方依赖：仅 stdlib）"""
    assert SCANNER_PATH.exists(), f"缺少跨仓扫描器: {SCANNER_PATH}"
    module = _load_scanner()
    assert hasattr(module, "scan") and hasattr(module, "iter_files")


def test_no_python_source_has_utf8_bom_across_repos():
    """契约主体：参与扫描的**全部仓**的 `.py` 源码均不得带 UTF-8 BOM"""
    report = _load_scanner().scan()
    assert report["scanned_files"] > 0, "未扫描到文件（仓路径推断有误）"
    assert report["violations"] == [], (
        "以下 Python 源码带 UTF-8 BOM，违反跨仓源码编码契约:\n"
        + "\n".join(
            f"  {item['repo']}/{item['path']}" for item in report["violations"]
        )
    )


def test_scanner_flags_bom_python_source(tmp_path):
    """正控（反例自证）：注入带 BOM 的 `.py` 必须被判为违规"""
    target = tmp_path / "bom_probe.py"
    target.write_bytes(b"\xef\xbb\xbfprint('probe')\n")

    report = _load_scanner().scan(roots=[tmp_path])

    assert [item["path"] for item in report["violations"]] == ["bom_probe.py"], report


def test_scanner_exempts_powershell_bom(tmp_path):
    """负控：`.ps1` 带 BOM 属**期望**行为 → 不得判违规（PowerShell 5.1 兼容）"""
    (tmp_path / "bom_probe.ps1").write_bytes(
        b"\xef\xbb\xbf" + "Write-Host '探针'\n".encode()
    )

    report = _load_scanner().scan(roots=[tmp_path])

    assert report["violations"] == [], report
    assert report["bom_hits_by_kind"].get("ps1", 0) == 1, report


def test_scanner_flags_non_ascii_powershell_without_bom(tmp_path):
    """正控（反例自证）：含非 ASCII 的 `.ps1` **无 BOM** 必须被判违规

    PowerShell 5.1（Windows 默认）对无 BOM 的 UTF-8 源文件按 GBK 解码 → 中文注释会致解析失败。
    """
    (tmp_path / "no_bom.ps1").write_text("Write-Host '探针'\n", encoding="utf-8")

    report = _load_scanner().scan(roots=[tmp_path])

    assert [item["kind"] for item in report["violations"]] == [
        "ps1_bom_required_non_ascii"
    ], report
    assert report["pass"] is False, report
