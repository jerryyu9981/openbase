"""TT-032 四仓 R-384 专项单测复跑驱动（v1.4.8 Step 4 剩余项 ⑤）

对应 v1.4.7《测试报告》§7.7 的 TT-147-009 补跑口径（逐仓原地复跑、未改四仓任何文件），
与其基线 **DPS 10 / OpenLLM 7 / OpenMemory 12 / OpenRAG 7 = 36** 逐仓对照。

用法::

    python tt032-four-repo-rerun-20260926.py

产物：`tt032-four-repo-rerun-20260926.json`（含逐仓命令、cwd、退出码、原文输出与基线对照）。
退出码：0＝复跑完成（是否一致见输出与 JSON `verdict`）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

OUT_DIR = r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148"

CASES = [
    {
        "repo": "DPS",
        "cwd": r"d:\Trae CN\myproject\Dev\DPS",
        "env": {"PYTHONPATH": "src"},
        "args": [
            "-B", "-m", "pytest", "src/tests/test_r384_request_id_filter.py",
            "-p", "no:randomly", "-p", "no:cacheprovider", "-q",
        ],
        "baseline_passed": 10,
        "adaptation": "仓内模块以 `from logging_setup import ...` 导入，需 `PYTHONPATH=src`",
    },
    {
        "repo": "OpenLLM",
        "cwd": r"d:\Trae CN\myproject\Dev\OpenLLM\backend",
        "env": {},
        "args": [
            "-B", "-m", "pytest", "tests/unit/test_r384_request_id_filter.py",
            "--noconftest", "-p", "no:cacheprovider", "-q",
        ],
        "baseline_passed": 7,
        "adaptation": "该用例不依赖 conftest fixture；沙箱下 conftest 前置依赖组合不可用，按 pytest 官方选项 --noconftest",
    },
    {
        "repo": "OpenMemory",
        "cwd": r"d:\Trae CN\myproject\Dev\OpenMemory",
        "env": {},
        "args": [
            "-B", "-m", "pytest", "tests/unit/test_r384_logging_contract.py",
            "-p", "no:cacheprovider", "-q",
        ],
        "baseline_passed": 12,
        "adaptation": "按仓内既有 pytest 配置直跑",
    },
    {
        "repo": "OpenRAG",
        "cwd": r"d:\Trae CN\myproject\Dev\OpenRAG",
        "env": {},
        "args": [
            "-B", "-m", "pytest", "tests/unit/test_r384_request_id.py",
            "-p", "no:cacheprovider", "-q",
        ],
        "baseline_passed": 7,
        "adaptation": "按仓内既有 pytest 配置直跑",
    },
]

_PASSED = re.compile(r"(\d+) passed")
_FAILED = re.compile(r"(\d+) failed")
_ERROR = re.compile(r"(\d+) error")


def main() -> None:
    results = []
    for case in CASES:
        env = {**os.environ, **case["env"]}
        proc = subprocess.run(
            [sys.executable, *case["args"]],
            cwd=case["cwd"],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        passed = int(_PASSED.search(output).group(1)) if _PASSED.search(output) else 0
        failed = int(_FAILED.search(output).group(1)) if _FAILED.search(output) else 0
        errors = int(_ERROR.search(output).group(1)) if _ERROR.search(output) else 0
        results.append(
            {
                "repo": case["repo"],
                "cwd": case["cwd"],
                "env": case["env"],
                "command": "python " + " ".join(case["args"]),
                "adaptation": case["adaptation"],
                "exit_code": proc.returncode,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "baseline_passed": case["baseline_passed"],
                "matches_baseline": passed == case["baseline_passed"] and failed == 0 and errors == 0,
                "output_tail": output.strip().splitlines()[-12:],
            }
        )

    total_passed = sum(r["passed"] for r in results)
    baseline_total = sum(r["baseline_passed"] for r in results)
    failures = [
        {"rule": "rerun-matches-baseline", "repo": r["repo"],
         "reason": f"passed={r['passed']}/failed={r['failed']}/errors={r['errors']}，基线={r['baseline_passed']}"}
        for r in results
        if not r["matches_baseline"]
    ]
    verdict = {
        "pass": not failures,
        "rules_checked": ["rerun-matches-baseline（逐仓 passed 一致且 failed=errors=0）"],
        "total_passed": total_passed,
        "baseline_total": baseline_total,
        "failures": failures,
        "note": "本次为单元级复跑（TT-147-009 口径）；四仓仓级全量回归不在本项判据范围（沿 v1.4.7 §7.7 声明）",
    }

    for rec in results:
        flag = "OK " if rec["matches_baseline"] else "!! "
        print(f"{flag}[{rec['repo']:<10}] passed={rec['passed']} failed={rec['failed']} "
              f"errors={rec['errors']} 基线={rec['baseline_passed']} exit={rec['exit_code']}")
    print()
    print(f"合计 passed={total_passed}（基线 {baseline_total}）")
    print(f"判定: {json.dumps({k: v for k, v in verdict.items() if k != 'failures'}, ensure_ascii=False)}")

    out = {
        "case": "TT-032 复测项 · 四仓 R-384 专项单测复跑（TT-147-009 口径）",
        "date": "2026-09-26",
        "interpreter": sys.version.split()[0],
        "source": "v1.4.7《OpenBase-测试报告-v1.4.7》§7.7（补跑口径与基线 10/7/12/7）",
        "results": results,
        "verdict": verdict,
    }
    path = f"{OUT_DIR}/tt032-four-repo-rerun-20260926.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(f"证据: {path}")


if __name__ == "__main__":
    main()
