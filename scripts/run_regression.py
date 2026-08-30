"""OpenBase v1.4.2 回归编排（BL-142-10 TD-新增-009）.

按测试文件分组（每组独立 pytest 进程，默认 6 文件/组），规避 Windows 上
starlette BaseHTTPMiddleware + anyio 多实例叠加的 C 层崩溃（单组不崩），
全量覆盖并汇总通过/失败/跳过。

用法:
    python scripts/run_regression.py [--cov] [--group-size 6]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_group(files: list[Path], with_cov: bool, retries: int = 3) -> tuple[int, int, int, list[str]]:
    """运行一组测试，返回 (passed, failed, skipped, failed_items).

    Windows 上 starlette BaseHTTPMiddleware + anyio 存在非确定性 C 层崩溃
    （TD-新增-009），崩溃组自动重试（子进程隔离，重试通常可过）。
    """
    for attempt in range(1, retries + 1):
        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"]
        cmd += [str(f) for f in files]
        if with_cov:
            cmd += ["--cov=openbase", "--cov-report=term", "--cov-append"]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            failed_items = [
                line for line in output.splitlines() if line.startswith("FAILED ")
            ]
            counts = _parse_counts(output)
            return counts[0], counts[1], counts[2], failed_items
        print(f"    [retry {attempt}/{retries}] 组崩溃（exit={result.returncode}），重试中…")
    # 重试耗尽：按崩溃处理（不重复计数）
    return 0, 0, 0, [f"group crashed: {files[0].name}..."]


def _parse_counts(output: str) -> tuple[int, int, int]:
    """从 pytest 输出解析 (passed, failed, skipped)."""
    import re

    def _count(pattern: str) -> int:
        match = re.search(pattern, output)
        return int(match.group(1)) if match else 0

    return _count(r"(\d+) passed"), _count(r"(\d+) failed"), _count(r"(\d+) skipped")


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenBase 回归编排")
    parser.add_argument("--cov", action="store_true", help="附带覆盖率统计")
    parser.add_argument("--group-size", type=int, default=3, help="每组测试文件数（Windows 组合崩溃临界 >3，默认 3）")
    args = parser.parse_args()

    # 1. ruff
    print("=== 1/3 ruff ===")
    ruff = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "openbase", "tests"], cwd=ROOT
    )
    if ruff.returncode != 0:
        print("[FAIL] ruff")
        return 1
    print("[OK] ruff")

    # 2. 分组 pytest
    files = sorted((ROOT / "tests").glob("test_*.py"))
    groups = [
        files[i:i + args.group_size] for i in range(0, len(files), args.group_size)
    ]
    print(f"=== 2/3 pytest（{len(files)} 文件 / {len(groups)} 组，子进程隔离）===")
    total_pass = total_fail = total_skip = 0
    all_failed: list[str] = []
    for group in groups:
        label = " ".join(p.name for p in group)
        print(f"--- group: {label} ---")
        passed, failed, skipped, failed_items = run_group(group, args.cov)
        print(f"    passed={passed} failed={failed} skipped={skipped}")
        total_pass += passed
        total_fail += failed
        total_skip += skipped
        all_failed.extend(failed_items)

    # 3. 汇总
    print("=== 3/3 汇总 ===")
    print(f"passed={total_pass} failed={total_fail} skipped={total_skip}")
    if all_failed:
        print("[FAIL] 失败项：")
        for item in all_failed:
            print(f"  {item}")
        return 1
    print("[OK] 全量回归通过（TD-新增-009 脚本化回归）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
