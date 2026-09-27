"""装配开销探针：预算开关 开 / 关 下单次 `build_prompt` 成本（§7.1 批准后的时延复核）

**动因**：§7.1 批准把 `CONTEXT_BUDGET_ENABLED` 等开关在生产配置置开后，需回答
「**装配本身是否变慢**」——把「开关代价」与「测试负载/环境噪声」区分开。
本探针直接测**单次装配**的中位/最大耗时（含预热，排除编码器首次初始化）。

**口径**：
  * 素材固定（20 条 × 约 120 字）；
  * 计数器取 `default_token_counter()`（与生产同口径）；
  * 每态**先预热** `load_budget_policy()`（策略装载 ＋ 编码器初始化），再计时；
  * 报告 `median_ms` / `max_ms` 与**开关比**。

用法（cwd = OpenLLM/backend）：

    python <此脚本> [--rounds 50] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.prompt_pipeline import (  # noqa: E402
    build_prompt,
    default_token_counter,
    load_budget_policy,
)

MEMORY = "\n".join(f"{index}. " + "甲" * 120 for index in range(1, 21))


def _measure(rounds: int, *, budget_on: bool) -> dict:
    previous = settings.CONTEXT_BUDGET_ENABLED
    settings.CONTEXT_BUDGET_ENABLED = budget_on
    try:
        counter = default_token_counter()
        load_budget_policy()  # 预热：策略装载 + 编码器初始化（不计入样本）
        samples: list[float] = []
        for _ in range(rounds):
            started = time.perf_counter()
            build_prompt(query="问", memory_ctx=MEMORY, count_tokens=counter)
            samples.append((time.perf_counter() - started) * 1000.0)
        return {
            "budget_enabled": budget_on,
            "rounds": rounds,
            "median_ms": round(statistics.median(samples), 3),
            "max_ms": round(max(samples), 3),
        }
    finally:
        settings.CONTEXT_BUDGET_ENABLED = previous


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    off = _measure(args.rounds, budget_on=False)
    on = _measure(args.rounds, budget_on=True)
    ratio = (
        round(on["median_ms"] / off["median_ms"], 3) if off["median_ms"] else None
    )
    report = {
        "probe": "assembly_cost",
        "material": {"items": 20, "chars_per_item": 120},
        "budget_off": off,
        "budget_on": on,
        "median_ratio_on_over_off": ratio,
        "verdict": (
            "装配本身未显著变慢（比值 < 2）"
            if ratio is not None and ratio < 2
            else "开启预算后单次装配明显变慢（比值 ≥ 2）—— 见 §8 风险行与 §7.1 备注"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "assembly_cost_probe-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
