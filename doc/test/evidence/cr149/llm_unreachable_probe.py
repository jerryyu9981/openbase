"""W1 / Q12 探针：**最终 LLM 不可达的判定与告知**判定表（含结尾自检）

**用途**：把 Q12 裁定（「A 通道降级接管的触发条件＝最终 LLM 不可达；此时**由调用方**改走
A 直连」）落成可复现的判定表 —— 逐例打印「是否判不可达 / 给什么动作 / 是否污染既有触发链」，
并在结尾**自检**（逐例期望一致）：任一不符即 `FAIL` 且**返回码非 0**。

**本探针锁定的两条关键口径**：

  1. **告警即时、状态判定按阈值** —— 单次失败即给出 `fallback_action="use_a_direct"`
     （调用方当次拿不到回答，须立刻知道改走哪条路），但 `llm_unreachable` 仍为 False。
  2. **不污染既有触发链** —— 终点失败**独立计数**，不计入组件连续失败，
     故 `evaluate_auto_failover` 语义**不变**（既有 v1.22.0 行为受保护）。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.identity.channel import (  # noqa: E402
    FALLBACK_ACTION_NONE,
    FALLBACK_ACTION_USE_A_DIRECT,
    ChannelStateManager,
)

REASON = "RuntimeError: OpenLLM 端点不可达"


def _case(
    name: str,
    *,
    failures: int,
    threshold: int,
    expect_reached: bool,
    expect_action: str,
    recover: bool = False,
    expect_component_failures: int = 0,
    expect_auto_failover: bool = False,
    expect_primary: str = "b",
) -> dict:
    """跑一个组合；用例**自带期望**"""
    manager = ChannelStateManager(
        "b-primary",
        consecutive_failure_threshold=threshold,
        drill_window_seconds=300.0,
        auto_failover_enabled=True,
    )
    for _ in range(failures):
        manager.record_b_llm_unavailable(reason=REASON)
    if recover:
        manager.record_b_llm_success()

    hint = manager.llm_unreachable_hint(reason=REASON)
    health = manager.b_health()
    failover = manager.evaluate_auto_failover()

    state_action = manager.channel_status()["fallback_action"]
    checks = {
        "reached_matches": hint["llm_unreachable"] == expect_reached,
        "state_action_matches": state_action == expect_action,
        "notify_scope_is_per_failure": hint["action_scope"] == "per_failure",
        "notify_advises_a_direct": hint["fallback_action"] == FALLBACK_ACTION_USE_A_DIRECT,
        "component_counter_clean": health["consecutive_failures"] == expect_component_failures,
        "auto_failover_matches": failover == expect_auto_failover,
        "primary_matches": manager.primary_channel == expect_primary,
    }
    return {
        "case": name,
        "failures": failures,
        "threshold": threshold,
        "llm_unreachable": hint["llm_unreachable"],
        "state_fallback_action": state_action,
        "notify_fallback_action": hint["fallback_action"],
        "component_consecutive_failures": health["consecutive_failures"],
        "auto_failover_triggered": failover,
        "expect_reached": expect_reached,
        "expect_action": expect_action,
        "checks": checks,
        "ok": all(checks.values()),
    }


def main() -> int:
    cases = [
        _case(
            "① 单次失败 ⇒ **即时告知**但**不**宣告不可达（状态动作 none）",
            failures=1,
            threshold=3,
            expect_reached=False,
            expect_action=FALLBACK_ACTION_NONE,
        ),
        _case(
            "② 达阈值（3 次）⇒ 宣告不可达",
            failures=3,
            threshold=3,
            expect_reached=True,
            expect_action=FALLBACK_ACTION_USE_A_DIRECT,
        ),
        _case(
            "③ 超阈值（5 次）⇒ 仍不可达，且**组件计数保持 0**（独立计数）",
            failures=5,
            threshold=3,
            expect_reached=True,
            expect_action=FALLBACK_ACTION_USE_A_DIRECT,
        ),
        _case(
            "④ 达阈值后恢复 ⇒ 判定复原、**状态动作收回**（通知仍为 per_failure 作用域）",
            failures=3,
            threshold=3,
            expect_reached=False,
            expect_action=FALLBACK_ACTION_NONE,
            recover=True,
        ),
        _case(
            "⑤ 阈值 0（未配置）⇒ 永不宣告（状态动作 none）；**告知仍给出**（不因缺配置而沉默）",
            failures=9,
            threshold=0,
            expect_reached=False,
            expect_action=FALLBACK_ACTION_NONE,
            # 阈值 0 属**退化配置**：既有 `evaluate_auto_failover` 判据为「连续失败 ≥ 阈值」
            # ⇒ 0 次即满足 ⇒ **既有自动接管即在此时触发、主通道转 a**（**W1 之前即如此**，
            # 非本批引入；此处如实锁定现状而非掩盖）。
            expect_auto_failover=True,
            expect_primary="a",
        ),
        _case(
            "⑥ 阈值 1 ⇒ 单次即达（边界）",
            failures=1,
            threshold=1,
            expect_reached=True,
            expect_action=FALLBACK_ACTION_USE_A_DIRECT,
        ),
    ]

    payload = {
        "probe": "llm_unreachable",
        "ruling": (
            "W1 / Q12：**最终 LLM 不可达**的判定按**连续次数达阈值**，"
            "对调用方的指示**即时**（单次失败即给 `use_a_direct`）；"
            "终点维度**独立计数** ⇒ **不触发**既有 B→A 自动接管（两机制分工不同）；"
            "`b_health().healthy` **并入**终点维度（不可达即 B 不可用）"
        ),
        "cases": cases,
    }
    failures = [item["case"] for item in cases if not item["ok"]]
    payload["summary"] = {
        "total": len(cases),
        "failed": len(failures),
        "failed_cases": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }

    if "--json" in sys.argv:
        target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_unreachable_probe-result.json")
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"已落盘：{target}")

    for item in cases:
        print(
            f"{'OK ' if item['ok'] else 'BAD'} {item['case']} ⇒ "
            f"unreachable={item['llm_unreachable']} "
            f"state_action={item['state_fallback_action']} "
            f"notify_action={item['notify_fallback_action']} "
            f"component_failures={item['component_consecutive_failures']} "
            f"auto_failover={item['auto_failover_triggered']}"
        )
    print(f"\n判定: {payload['summary']['verdict']}（{len(cases)} 例 / 不符 {len(failures)}）")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
