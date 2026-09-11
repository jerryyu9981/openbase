#!/usr/bin/env python
"""S7-T4 L2-2 通道矩阵终验（骨架 + 干跑）.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》
- §4.4 S7-T4-1~4：每子系统 × A/B × 状态/头语义矩阵「行全覆盖、缺口 0」；管理面/探活
  **A 直连豁免行显式标注**（与 K07 端点矩阵 A 直连豁免行对账）；读路径 B 主全绿 + A 备
  covered；写路径 A/B 等价 + K14 幂等；
- §5.2 evidence JSON 字段规范（``schema_version`` / ``status`` / ``reason`` /
  ``execution_face`` / ``openbase_commit`` / ``checked_at`` / ``evidence_ref``）；
- Q-S7-5：以 S4-T8 产出 ``matrix_rows`` 通道覆盖矩阵为基座，**复用其语义口径，不引入新语义**。

执行面（禁伪造）：
- 骨架 + 干跑：无真实 PG/Redis/IdP/四仓运行态 → 四项检查一律 ``PENDING``，退出码 ``2``；
- 真实执行路径代码齐备（``--matrix`` 基座加载 / ``--check-read-ab`` / ``--check-write-ab``
  + ``--k14`` + ``--base-url`` 探活），不可达一律 ``PENDING``，**禁伪造 PASS**。

用法::

    python scripts/finalize_l2_2_matrix.py --dry-run
    python scripts/finalize_l2_2_matrix.py --matrix <S4-T8 matrix_rows.json> --out <...>
    python scripts/finalize_l2_2_matrix.py --check-read-ab --base-url <GATEWAY_BASE>
    python scripts/finalize_l2_2_matrix.py --check-write-ab --k14 --base-url <GATEWAY_BASE>

统一退出码：``0`` = PASS；``1`` = FAIL；``2`` = PENDING（无真实环境 / 不可达）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
K07_SCRIPT = ROOT / "scripts" / "k07_endpoint_matrix.py"
K07_TEMPLATE = ROOT / "doc" / "design" / "OpenBase-端点过滤矩阵模板-v1.0.md"
DEFAULT_OUT = (
    ROOT / "doc" / "test" / "evidence" / "s7" / "l2-2" / "matrix-finalize.json"
)
SCHEMA_VERSION = 1
TOOL = "finalize_l2_2_matrix.py"
EVIDENCE_REF = "S7-T4"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_PENDING = 2

# 子系统 × 通道（A/B）× 路径语义（读 / 写 / 管理面·探活）
SUBSYSTEMS: tuple[str, ...] = ("OpenMemory", "OpenRAG", "OpenLLM", "DPS")
CHANNELS: tuple[str, ...] = ("A", "B")
PATH_SEMANTICS: tuple[str, ...] = ("read", "write", "health-management")
# 头语义（四头；复用 K07 端点矩阵口径，不引入新语义）
_DEFAULT_HEADER_SEMANTICS: tuple[str, ...] = (
    "X-User-ID",
    "X-Tenant-ID",
    "X-User-Role",
    "X-Proxy-Source",
)


def _load_k07_module() -> Any | None:
    """加载 K07 端点矩阵模块以复用「四头 / 状态 / 子系统」语义口径（失败返回 None）."""
    if not K07_SCRIPT.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("k07_endpoint_matrix", K07_SCRIPT)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, OSError, ValueError):
        return None


def _header_semantics() -> tuple[str, ...]:
    module = _load_k07_module()
    fields = getattr(module, "IDENTITY_HEADER_FIELDS", None)
    return tuple(fields) if fields else _DEFAULT_HEADER_SEMANTICS


def _git_head() -> str:
    """读取 OpenBase HEAD（真实；失败返回空串，不伪造）."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except OSError:
        return ""


def _planned_matrix_rows() -> list[dict[str, Any]]:
    """矩阵骨架行：子系统 × 通道 × 路径语义（含头语义），状态统一 PENDING."""
    headers = _header_semantics()
    rows: list[dict[str, Any]] = []
    for subsystem in SUBSYSTEMS:
        for channel in CHANNELS:
            for path_semantic in PATH_SEMANTICS:
                rows.append(
                    {
                        "subsystem": subsystem,
                        "channel": channel,
                        "path_semantic": path_semantic,
                        "header_semantics": list(headers),
                        "status": "PENDING",
                    }
                )
    return rows


def _k07_exempt_reconcile() -> dict[str, Any]:
    """与 K07 端点矩阵 A 直连豁免行对账（读取模板，标注豁免行与 A 直连行计数）."""
    if not K07_TEMPLATE.exists():
        return {
            "template": "doc/design/OpenBase-端点过滤矩阵模板-v1.0.md",
            "exists": False,
            "direct_connect_rows": 0,
            "exempt_rows": 0,
            "status": "PENDING",
            "reason": "K07 模板不可达（沙箱仅 OpenBase 写权限）",
        }
    text = K07_TEMPLATE.read_text(encoding="utf-8", errors="replace")
    direct_connect = sum(1 for line in text.splitlines() if "A 直连" in line or "A直连" in line)
    exempt_rows = sum(
        1
        for line in text.splitlines()
        if "豁免?（是/否）=是" in line or line.count("| 豁免 |") >= 1
    )
    return {
        "template": "doc/design/OpenBase-端点过滤矩阵模板-v1.0.md",
        "exists": True,
        "direct_connect_rows": direct_connect,
        "exempt_rows": exempt_rows,
        "status": "PENDING",
        "reason": "豁免行显式标注已对账；真实终验（缺口清零 / 豁免有效期与审批）属联调窗口 B 面",
    }


def _load_matrix(matrix_path: str) -> dict[str, Any]:
    """加载 S4-T8 ``matrix_rows`` 基座（真实执行路径；文件缺失 / 解析失败则登记原因）."""
    if not matrix_path:
        return {
            "loaded": False,
            "rows": [],
            "reason": "未提供 --matrix 基座（S4-T8 matrix_rows）；沙箱无四仓运行态",
        }
    path = Path(matrix_path)
    if not path.exists():
        return {"loaded": False, "rows": [], "reason": f"matrix 基座不存在: {matrix_path}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"loaded": False, "rows": [], "reason": f"matrix 基座解析失败: {matrix_path}"}
    rows = payload.get("matrix_rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {"loaded": False, "rows": [], "reason": "matrix 基座缺少 matrix_rows 数组"}
    return {"loaded": True, "rows": rows, "reason": ""}


def _probe(base_url: str, timeout: float = 3.0) -> bool:
    """探活受信通道（真实执行路径；不可达返回 False，一律登记 PENDING）."""
    if not base_url:
        return False
    try:
        with urllib.request.urlopen(base_url, timeout=timeout) as response:  # noqa: S310
            return 200 <= int(response.status) < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _check_matrix_coverage(matrix: dict[str, Any]) -> dict[str, Any]:
    if not matrix["loaded"]:
        return {
            "id": "S7-T4-1",
            "name": "通道覆盖矩阵（每子系统 × A/B × 状态/头语义）行全覆盖、缺口 0",
            "execution_face": "B",
            "status": "PENDING",
            "reason": matrix["reason"],
            "metrics": {"rows": 0, "covered": 0, "gap": None},
        }
    rows = matrix["rows"]
    covered = sum(1 for row in rows if row.get("status") in {"覆盖", "covered"})
    gap = sum(1 for row in rows if row.get("status") in {"缺口", "未覆盖", "gap"})
    return {
        "id": "S7-T4-1",
        "name": "通道覆盖矩阵（每子系统 × A/B × 状态/头语义）行全覆盖、缺口 0",
        "execution_face": "B",
        "status": "PASS" if gap == 0 and rows else "FAIL",
        "reason": "" if gap == 0 and rows else f"矩阵缺口非 0 或为空: gap={gap}",
        "metrics": {"rows": len(rows), "covered": covered, "gap": gap},
    }


def _check_k07_exempt(reconcile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "S7-T4-2",
        "name": "管理面/探活 A 直连豁免行显式标注（与 K07 端点矩阵对账）",
        "execution_face": "B",
        "status": "PENDING",
        "reason": reconcile["reason"],
        "k07_reconcile": reconcile,
    }


def _check_read_path(base_url: str, enabled: bool) -> dict[str, Any]:
    if enabled and _probe(base_url):
        # 真实通道可达时走真实对账（联调窗口填断言；骨架不伪造 PASS 结论）
        return {
            "id": "S7-T4-3",
            "name": "读路径 B 主全绿 + A 备 covered（同读请求经 A/B 返回一致、四头一致）",
            "execution_face": "B",
            "status": "PENDING",
            "reason": "受信通道可达，读路径 A/B 等价断言需真实四仓响应（联调窗口回填）",
        }
    return {
        "id": "S7-T4-3",
        "name": "读路径 B 主全绿 + A 备 covered（同读请求经 A/B 返回一致、四头一致）",
        "execution_face": "B",
        "status": "PENDING",
        "reason": "--check-read-ab 未开启或受信通道不可达（沙箱无四仓运行态）",
    }


def _check_write_path(base_url: str, enabled: bool, k14: bool) -> dict[str, Any]:
    if enabled and k14 and _probe(base_url):
        return {
            "id": "S7-T4-4",
            "name": "写路径 A/B 等价用例绿 + K14 幂等（重放不双写、DB 行数不变）",
            "execution_face": "B",
            "status": "PENDING",
            "reason": "受信通道可达，写路径等价与 K14 幂等需真实 DB 行数对账（联调窗口回填）",
        }
    return {
        "id": "S7-T4-4",
        "name": "写路径 A/B 等价用例绿 + K14 幂等（重放不双写、DB 行数不变）",
        "execution_face": "B",
        "status": "PENDING",
        "reason": "--check-write-ab/--k14 未开启或受信通道不可达（沙箱无真实 PG/Redis）",
    }


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if statuses == {"PASS"}:
        return "PASS"
    return "PENDING"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    """构造 L2-2 终验证据（分项失败不伪造，如实登记；无真实环境一律 PENDING）."""
    matrix = _load_matrix(args.matrix)
    reconcile = _k07_exempt_reconcile()
    checks = [
        _check_matrix_coverage(matrix),
        _check_k07_exempt(reconcile),
        _check_read_path(args.base_url, args.check_read_ab),
        _check_write_path(args.base_url, args.check_write_ab, args.k14),
    ]
    status = _overall_status(checks)
    exit_code = {"PASS": EXIT_PASS, "FAIL": EXIT_FAIL, "PENDING": EXIT_PENDING}[status]
    head = _git_head()
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "task": "S7-T4",
        "evidence_ref": EVIDENCE_REF,
        "title": "S7-T4 L2-2 通道矩阵终验",
        "mode": "dry-run" if args.dry_run else "run",
        "status": status,
        "exit_code": exit_code,
        "execution_face": "B",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": head[:7],
        "openbase_commit": head,
        "reason": (
            "沙箱无真实 PG/Redis/IdP/四仓运行态：矩阵终验属 B 面 → PENDING；"
            "真实执行需联调窗口（S4-T8 matrix_rows 基座 + 受信通道）"
        ),
        "matrix_plan": {
            "subsystems": list(SUBSYSTEMS),
            "channels": list(CHANNELS),
            "path_semantics": list(PATH_SEMANTICS),
            "header_semantics": list(_header_semantics()),
            "planned_rows": _planned_matrix_rows(),
        },
        "k07_reconcile": reconcile,
        "checks": checks,
        "pending_items": [
            {
                "id": "L2-2-REAL",
                "item": "L2-2 通道矩阵终验（缺口 0 / A 直连豁免对账 / 读写 A/B 等价 / K14 幂等）",
                "precondition": "四仓运行态 + S4-T8 matrix_rows 基座 + 真实受信通道",
                "owner": "联调窗口",
                "action": "真实窗口执行后回填 status=PASS/FAIL",
            }
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S7-T4 L2-2 通道矩阵终验（骨架 + 干跑；真实执行需联调窗口）"
    )
    parser.add_argument("--dry-run", action="store_true", help="干跑：输出计划项并登记 PENDING")
    parser.add_argument("--matrix", default="", help="S4-T8 matrix_rows 基座 JSON 路径")
    parser.add_argument("--base-url", default="", help="受信通道基址（读/写路径对账探活）")
    parser.add_argument("--check-read-ab", action="store_true", help="执行读路径 A/B 等价对账")
    parser.add_argument("--check-write-ab", action="store_true", help="执行写路径 A/B 等价对账")
    parser.add_argument("--k14", action="store_true", help="写路径 K14 幂等（重放不双写）对账")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="证据 JSON 输出路径")
    parser.add_argument("--json", action="store_true", help="同时打印证据 JSON 到 stdout")
    args = parser.parse_args(argv)

    try:
        report = build_report(args)
    except Exception as error:  # noqa: BLE001 - 顶层兜底，登记内部错误
        print(f"[ERROR] L2-2 终验失败: {error}", file=sys.stderr)
        return EXIT_FAIL

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("=== S7-T4 L2-2 通道矩阵终验 ===")
    print(f"  status={report['status']} exit={report['exit_code']} mode={report['mode']}")
    for check in report["checks"]:
        print(f"  [{check['status']}] {check['id']} - {check['name']}")
    print(f"  evidence: {out_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
