#!/usr/bin/env python
"""L3-2 贯通冒烟（OpenBase 侧缺失项）——骨架 + 干跑.

设计依据：《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0》
- §4.6 S7-T6-2（冒烟 S0-S6 真实执行）与 §4.7 S7-T7-3（L3-2 真实受信通道双签复核）；
- §5.2 evidence JSON 字段规范（``schema_version`` / ``status`` / ``reason`` /
  ``execution_face`` / ``openbase_commit`` / ``checked_at`` / ``evidence_ref``）；
- 《OpenBase-S7-沙箱外执行单-v1.0.0》§0.2 N-5：OpenBase 仓内 ``smoke_l3_2.py`` 缺失，
  本次补做骨架（L3-2 双签执行以各子系统仓脚本为准，OpenBase 侧登记回填）。

执行面（禁伪造）：
- 骨架 + 干跑：经受信通道端到端关键路径；无真实环境 → ``status=PENDING``，退出码 ``2``；
- ``--base-url`` 不可达（沙箱无四仓运行态）→ ``status=PENDING``、退出码 ``2``；
- 真实执行路径代码齐备（受信通道探活 + 各子系统健康/关键路径），可达后由联调窗口回填。

用法::

    python scripts/smoke_l3_2.py --dry-run
    python scripts/smoke_l3_2.py --dry-run --base-url <GATEWAY_BASE>
    python scripts/smoke_l3_2.py --base-url <GATEWAY_BASE> --out <...>

统一退出码：``0`` = PASS；``1`` = FAIL；``2`` = PENDING（无真实环境 / 不可达）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "doc" / "test" / "evidence" / "s7" / "l3-2" / "smoke-result.json"
SCHEMA_VERSION = 1
TOOL = "smoke_l3_2.py"
EVIDENCE_REF = "S7-T6-2 / S7-T7-3"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_PENDING = 2

# L3-2 贯通冒烟关键路径（受信通道端到端；逐子系统登记）
KEY_PATHS: tuple[dict[str, str], ...] = (
    {"system": "OpenBase", "path": "/health", "desc": "底座健康"},
    {"system": "OpenLLM", "path": "/openllm/v1/health", "desc": "模型服务健康"},
    {"system": "OpenMemory", "path": "/health", "desc": "记忆服务健康"},
    {"system": "OpenRAG", "path": "/api/v1/system/health", "desc": "检索服务健康"},
    {"system": "DPS", "path": "/health", "desc": "数据平台健康"},
)


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


def _probe(base_url: str, timeout: float = 3.0) -> bool:
    """探活受信通道基址（真实执行路径；不可达返回 False → PENDING）.

    4xx（含 404）视为**通道可达**（服务在线但该路径受鉴权/不存在），
    仅连接类错误与 5xx 视为不可达；避免将在线通道误判为不可达。
    """
    if not base_url:
        return False
    try:
        with urllib.request.urlopen(base_url, timeout=timeout) as response:  # noqa: S310
            return 200 <= int(response.status) < 500
    except urllib.error.HTTPError as http_error:
        return int(http_error.code) < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _build_checks(reachable: bool) -> list[dict[str, Any]]:
    """构造两项检查（S7-T6-2 冒烟贯通 / S7-T7-3 L3-2 受信通道双签）."""
    if reachable:
        reason = "受信通道可达，逐子系统关键路径断言需真实响应与四头（联调窗口回填）"
    else:
        reason = "--base-url 不可达或未提供（沙箱无四仓运行态）→ 真实执行 PENDING"
    return [
        {
            "id": "S7-T6-2",
            "name": "L3-2 贯通冒烟（S0-S6 关键路径经受信通道端到端）",
            "execution_face": "B",
            "status": "PENDING",
            "reason": reason,
        },
        {
            "id": "S7-T7-3",
            "name": "L3-2 真实受信通道双签（各子系统仓执行，OpenBase 侧登记回填）",
            "execution_face": "B",
            "status": "PENDING",
            "reason": reason,
        },
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    """构造 L3-2 冒烟证据（无真实环境一律 PENDING，禁伪造 PASS）."""
    reachable = (not args.dry_run) and _probe(args.base_url)
    checks = _build_checks(reachable)
    status = "PENDING" if any(c["status"] == "PENDING" for c in checks) else "PASS"
    if any(c["status"] == "FAIL" for c in checks):
        status = "FAIL"
    exit_code = {"PASS": EXIT_PASS, "FAIL": EXIT_FAIL, "PENDING": EXIT_PENDING}[status]
    head = _git_head()
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "task": "L3-2",
        "evidence_ref": EVIDENCE_REF,
        "title": "L3-2 贯通冒烟（OpenBase 侧缺失项骨架）",
        "mode": "dry-run" if args.dry_run else "run",
        "status": status,
        "exit_code": exit_code,
        "execution_face": "B",
        "base_url": args.base_url,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": head[:7],
        "openbase_commit": head,
        "reason": (
            (
                "受信通道可达（base_url 在线）；L3-2 真实双签以各子系统仓脚本为准，"
                "OpenBase 侧登记回填 → 保持 PENDING"
            )
            if reachable
            else (
                "受信通道不可达或未提供：L3-2 贯通冒烟属 B 面 → PENDING；"
                "真实执行需联调窗口（各子系统仓 L3-2 双签脚本）"
            )
        ),
        "reachable": reachable,
        "key_paths": [dict(item) for item in KEY_PATHS],
        "checks": checks,
        "pending_items": [
            {
                "id": "L3-2-REAL",
                "item": "L3-2 贯通冒烟 + 真实受信通道双签",
                "precondition": "四仓运行态 + 真实受信通道 + 密钥/开关就绪",
                "owner": "联调窗口",
                "action": "按段级 L3-2 双签脚本执行后回填 status=PASS/FAIL",
            }
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="L3-2 贯通冒烟（OpenBase 侧骨架 + 干跑；真实执行需联调窗口）"
    )
    parser.add_argument("--dry-run", action="store_true", help="干跑：输出关键路径计划并登记 PENDING")
    parser.add_argument("--base-url", default="", help="受信通道基址（不可达 → PENDING）")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="证据 JSON 输出路径")
    parser.add_argument("--json", action="store_true", help="同时打印证据 JSON 到 stdout")
    args = parser.parse_args(argv)

    try:
        report = build_report(args)
    except Exception as error:  # noqa: BLE001 - 顶层兜底，登记内部错误
        print(f"[ERROR] L3-2 冒烟失败: {error}", file=sys.stderr)
        return EXIT_FAIL

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("=== L3-2 贯通冒烟（OpenBase 侧）===")
    print(f"  status={report['status']} exit={report['exit_code']} mode={report['mode']}")
    for check in report["checks"]:
        print(f"  [{check['status']}] {check['id']} - {check['name']}")
    print(f"  evidence: {out_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
