"""v1.4.9 Step 3 产出物存在性验证（门禁 3.10）。

对 Step 3 的全部交付物（文档 ＋ 证据）逐件核验「存在且非空」，输出可直接入仓的证据报告。
命令可复现：脚本本身已入仓。

用法：
    python cr149-deliverable-inventory.py                 # 打印报告
    python cr149-deliverable-inventory.py --out <文件>     # 同时写入 UTF-8（无 BOM）证据文件
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

# Step 3 交付物清单（文档仓内相对路径）。
# 说明：清单以「追溯矩阵 §2 CheckList 的落点」为准，逐件登记；新增交付物须同步本清单。
DOC_ARTIFACTS: tuple[str, ...] = (
    r"doc\design\OpenBase-系统架构设计文档-v1.4.9.md",
    r"doc\design\OpenBase-API接口设计文档-v1.4.9.md",
    r"doc\development\OpenBase-设计开发追溯矩阵-v1.4.9.md",
    r"doc\development\OpenBase-DevLogReport-v1.4.9.md",
    r"doc\development\OpenBase-静态质量检查记录-v1.4.9.md",
    r"doc\development\OpenBase-代码逻辑审查记录-v1.4.9.md",
    r"doc\development\OpenBase-开发审计移交材料-v1.4.9.md",
    r"doc\development\OpenBase-测试移交说明-v1.4.9.md",
    r"doc\audit\review\OpenBase-阶段审计报告-Stage3-v1.4.9.md",
    # ── Step 4（测试阶段）产出 ─────────────────────────────────────────────
    r"doc\test\OpenBase-测试计划-v1.4.9.md",
    r"doc\test\OpenBase-测试用例-v1.4.9.md",
    r"doc\test\OpenBase-测试报告-v1.4.9.md",
    r"doc\audit\verification\OpenBase-测试回溯对比审计报告-v1.4.9.md",
    r"doc\audit\review\OpenBase-阶段审计报告-Stage4-v1.4.9.md",
    # ── Step 5（部署与运维）产出（本批：入场门禁阻塞，仅产出不依赖发布事实的文档）──
    r"doc\release\OpenBase-发布入场检查记录与发布计划-v1.4.9.md",
    r"doc\release\OpenBase-回滚方案与运维手册-v1.4.9.md",
    r"doc\release\OpenBase-发布复盘与问题跟踪记录-v1.4.9.md",
    r"doc\release\OpenBase-部署执行与上线检查报告-v1.4.9.md",
    r"doc\release\OpenBase-Release-Note-v1.4.9.md",
    r"doc\release\OpenBase-Release-Note-All.md",
    r"doc\release\OpenBase-运维审计报告-v1.4.9.md",
    r"doc\audit\comprehensive\OpenBase-全流程闭环审计报告-v1.4.9.md",
    r"doc\audit\review\OpenBase-阶段审计报告-Stage5-v1.4.9.md",
)

EVIDENCE_ARTIFACTS: tuple[str, ...] = (
    r"doc\test\evidence\cr149\v149-increment-eval-set.json",
    r"doc\test\evidence\cr149\v149_increment_runner.py",
    r"doc\test\evidence\cr149\v149_increment_runner-result.json",
    r"doc\test\evidence\cr149\v149_receipt_and_purity_probe.py",
    r"doc\test\evidence\cr149\v149_receipt_and_purity_probe-result.json",
    r"doc\test\evidence\v149\cr149-l1-compile-20260929.txt",
    r"doc\test\evidence\v149\cr149-instance-8041-20260929.txt",
    r"doc\test\evidence\v149\cr149-l3-smoke-20260929.py",
    r"doc\test\evidence\v149\cr149-l3-smoke-20260929.json",
    r"doc\test\evidence\v149\cr149-debt-growth-20260929.txt",
    r"doc\test\evidence\v149\cr149-consistency-selfcheck.py",
    r"doc\test\evidence\v149\cr149-consistency-selfcheck-20260929.txt",
    r"doc\test\evidence\v149\cr149-deliverable-inventory.py",
    r"doc\test\evidence\v149\cr149-deliverable-inventory-20260929.txt",
    # ── Step 4（测试阶段）证据 ─────────────────────────────────────────────
    r"doc\test\evidence\v149\cr149-t40-env-evidence.py",
    r"doc\test\evidence\v149\cr149-t40-env-20260929.txt",
    r"doc\test\evidence\v149\cr149-t40-t2t3e2e-20260929.py",
    r"doc\test\evidence\v149\cr149-t40-t2t3e2e-result.json",
    r"doc\test\evidence\v149\cr149-t40-render-t3a.py",
    r"doc\test\evidence\v149\cr149-t40-t3a-scan-20260929.txt",
    r"doc\test\evidence\v149\cr149-t40-mock-probe.py",
    r"doc\test\evidence\v149\cr149-t40-mock-20260929.txt",
    r"doc\test\evidence\v149\cr149-t40-regression-20260929.txt",
    r"doc\test\evidence\v149\cr149-t40-coverage-20260929.txt",
    r"doc\test\evidence\v149\cr149-t40-consistency-20260929.txt",
)


def _inspect(repo: Path, relative: str) -> tuple[str, str]:
    path = repo / relative
    if not path.is_file():
        return "MISSING", relative
    raw = path.read_bytes()
    if not raw.strip():
        size_kb = len(raw) / 1024
        return "EMPTY", f"{relative}  ({size_kb:.1f} KB / 0 行)"
    line_count = len(raw.decode("utf-8", errors="replace").splitlines())
    size_kb = len(raw) / 1024
    return "OK", f"{relative}  ({size_kb:.1f} KB / {line_count} 行)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="仓根（默认按脚本位置上溯到含 .git 的目录）")
    parser.add_argument("--out", default=None, help="同时把报告写入该文件（UTF-8 无 BOM）")
    args = parser.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve()
    if args.repo is None:
        for parent in [repo, *repo.parents]:
            if (parent / ".git").exists():
                repo = parent
                break
    if not (repo / ".git").exists():
        print(f"[FATAL] 未定位到 git 仓根：{repo}", file=sys.stderr)
        return 2

    lines: list[str] = []
    lines.append("=== v1.4.9 Step 3 产出物存在性验证（3.10）===")
    lines.append(f"时间：{dt.datetime.now(dt.timezone.utc).isoformat()}")
    lines.append(f"仓库：{repo}")
    lines.append(f"清单脚本：{Path(__file__).name}（已入仓，命令可复现）")
    lines.append("")

    totals = {"OK": 0, "EMPTY": 0, "MISSING": 0}
    for title, artifacts in (("--- 文档产物 ---", DOC_ARTIFACTS), ("--- 证据文件 ---", EVIDENCE_ARTIFACTS)):
        lines.append(title)
        for relative in artifacts:
            status, detail = _inspect(repo, relative)
            totals[status] += 1
            lines.append(f"  {status:<8} {detail}")
        lines.append("")

    lines.append(f"TOTAL FILES: {sum(totals.values())}")
    lines.append(f"EMPTY FILES: {totals['EMPTY']}")
    lines.append(f"MISSING FILES: {totals['MISSING']}")
    lines.append(
        "判定：**通过**（全部存在且非空）"
        if totals["EMPTY"] == 0 and totals["MISSING"] == 0
        else "判定：**不通过**（存在空文件或缺失文件）"
    )

    report = "\n".join(lines)
    print(report)
    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")

    return 0 if totals["EMPTY"] == 0 and totals["MISSING"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
