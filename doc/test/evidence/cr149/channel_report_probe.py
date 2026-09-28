"""W4 探针：**双通道健康/降级统一上报**判定表（含结尾自检）

**用途**：把 W4 的三条纪律落成可复现的判定表 —— 逐例打印「三视角事实 / 降级证据 / 单一结论 /
理由」，并在结尾**自检**（逐例期望一致）：任一不符即 `FAIL` 且**返回码非 0**。

**本探针锁定的三条契约**：

  1. **只聚合、不立新判据** —— 报告字段全部可由 `ChannelStateManager` 事实 ＋ 组件探测推出；
     与 `channel_status()` / `b_health()` / `a_health()` **逐项相等**（对照断言）。
  2. **单一决策规则** —— `bypass_orchestration` 当且仅当「**主通道已为 A**」**或**
     「主通道为 B **且** 最终 LLM 不可达」；穷举组合恒等。
  3. **观测与决策分离** —— 组件降级**如实列入** `degraded_dimensions`，但**结论仍是走主通道**
     —— **不因噪声误切通道，也不隐瞒劣化事实**；A 侧失败亦不改变 B 主时的结论。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.identity.channel import (  # noqa: E402
    CHANNEL_A,
    CHANNEL_B,
    ROUTING_USE_A_DIRECT,
    ROUTING_USE_PRIMARY,
    ChannelStateManager,
    describe_channel_report,
)

REASON = "RuntimeError: OpenLLM 端点不可达"


def _manager(threshold: int = 3) -> ChannelStateManager:
    return ChannelStateManager(
        "b-primary",
        consecutive_failure_threshold=threshold,
        drill_window_seconds=300.0,
        auto_failover_enabled=True,
    )


def _components(**statuses: str) -> dict:
    return {name: {"status": status, "channel": CHANNEL_B} for name, status in statuses.items()}


def _case(
    name: str,
    *,
    manager: ChannelStateManager,
    components: dict | None = None,
    expect_bypass: bool,
    expect_degraded: list[str] | None = None,
    expect_reason_contains: str = "",
) -> dict:
    """跑一个组合；用例**自带期望**"""
    report = describe_channel_report(manager, components=components)
    status = manager.channel_status()
    health_b = manager.b_health()

    checks = {
        # ① 只聚合：与事实源逐项相等（防暗增判据）
        "fallback_action_same_source": report["fallback_action"] == status["fallback_action"],
        "b_consecutive_matches": (
            report["channels"][CHANNEL_B]["consecutive_failures"] == health_b["consecutive_failures"]
        ),
        "llm_consecutive_matches": (
            report["channels"][CHANNEL_B]["llm_consecutive_failures"]
            == health_b["llm_consecutive_failures"]
        ),
        "a_healthy_matches": (
            report["channels"][CHANNEL_A]["healthy"] == manager.a_health()["healthy"]
        ),
        "primary_matches": report["primary_channel"] == manager.primary_channel,
        # ② 单一决策规则
        "bypass_matches_rule": report["bypass_orchestration"] is expect_bypass,
        "recommendation_matches": report["routing_recommendation"]
        == (ROUTING_USE_A_DIRECT if expect_bypass else ROUTING_USE_PRIMARY),
        # ③ 观测与决策分离：**降级事实必须如实列入**（不得隐瞒）
        #    **逐项严格相等**（非「包含」）—— 防「多列」或「漏列」被静默放过。
        "degraded_matches": (
            expect_degraded is None
            or list(report["degraded_dimensions"]) == list(expect_degraded)
        ),
        "reason_present": (
            expect_reason_contains == ""
            or any(expect_reason_contains in reason for reason in report["reasons"])
        ),
    }
    return {
        "case": name,
        "threshold": manager.consecutive_failure_threshold,
        "primary_channel": report["primary_channel"],
        "channels": report["channels"],
        "degraded_dimensions": report["degraded_dimensions"],
        "bypass_orchestration": report["bypass_orchestration"],
        "routing_recommendation": report["routing_recommendation"],
        "fallback_action": report["fallback_action"],
        "reasons": report["reasons"],
        "expect_bypass": expect_bypass,
        "checks": checks,
        "ok": all(checks.values()),
    }


def _build() -> list[dict]:
    cases: list[dict] = []

    # ① 基线：双通道无异常 ⇒ 走主通道
    cases.append(
        _case(
            "① 基线（B 主、无失败、组件全 ok）⇒ **走主通道**、无降级维度",
            manager=_manager(),
            components=_components(openrag="ok", openmemory="ok", dps="ok"),
            expect_bypass=False,
            expect_degraded=[],
            expect_reason_contains="双通道无异常",
        )
    )

    # ② 组件降级（观测与决策分离的**核心契约**）
    degraded_manager = _manager(threshold=2)
    for _ in range(2):
        degraded_manager.record_b_component_failure("rag", reason="x")
    cases.append(
        _case(
            "② B 组件降级 ⇒ **如实列入证据**但**结论仍走主通道**（可用但劣化）",
            manager=degraded_manager,
            components=_components(openrag="unavailable", openmemory="ok"),
            expect_bypass=False,
            expect_degraded=[f"{CHANNEL_B}.components", f"{CHANNEL_B}.component.openrag"],
            expect_reason_contains="仍走主通道",
        )
    )

    # ③ A 侧达阈值失败（B 主时**不**改变结论）
    a_failed = _manager(threshold=3)
    for _ in range(3):
        a_failed.record_a_failure(reason="A 侧探活失败")
    cases.append(
        _case(
            "③ A 侧达阈值失败 ⇒ 列入证据，但 **B 主时不改变主通道**",
            manager=a_failed,
            expect_bypass=False,
            expect_degraded=[f"{CHANNEL_A}.components"],
            expect_reason_contains="A 侧有失败记录",
        )
    )

    # ④ 终点不可达（达阈值）⇒ **改走 A 直连**
    unreachable = _manager(threshold=3)
    for _ in range(3):
        unreachable.record_b_llm_unavailable(reason=REASON)
    cases.append(
        _case(
            "④ 最终 LLM 不可达（达阈值）⇒ **改走 A 直连**（Q12 口径）",
            manager=unreachable,
            expect_bypass=True,
            expect_degraded=[f"{CHANNEL_B}.llm"],
            expect_reason_contains="最终 LLM 不可达",
        )
    )

    # ⑤ 终点未达阈值 ⇒ **不**改走（阈值语义与 W1 同源）
    below = _manager(threshold=3)
    below.record_b_llm_unavailable(reason=REASON)
    cases.append(
        _case(
            "⑤ 终点失败未达阈值 ⇒ **不**改走、**不列降级**（状态判定按阈值）",
            manager=below,
            expect_bypass=False,
            expect_degraded=[],
        )
    )

    # ⑥ 主通道已为 A（接管后）⇒ 走 A 直连
    a_primary = _manager(threshold=1)
    a_primary.trigger_failover_to_a(source="manual", reason="演练", actor="ops")
    cases.append(
        _case(
            "⑥ 主通道已为 A（演练接管）⇒ **走 A 直连**",
            manager=a_primary,
            expect_bypass=True,
            expect_reason_contains="主通道已是 A",
        )
    )

    # ⑦ 阈值 0（退化配置）⇒ 与 W1 同源：**不**宣告终点不可达 ⇒ 结论仍为主通道
    #    **如实记录既有退化行为**（非本批引入、亦非本批掩盖）：`*_health()["healthy"]` 判据为
    #    `consecutive < threshold` ⇒ 阈值 0 时 `0 < 0` 为假 ⇒ **两条通道均报「不健康」**，
    #    尽管**无任何失败**。故此处降级证据为 `b.components` ＋ `a.components` —— 本探针
    #    **照实锁定**（期望值与实际一致），并同时验证**结论仍为主通道**（观测与决策分离）。
    zero = _manager(threshold=0)
    for _ in range(5):
        zero.record_b_llm_unavailable(reason=REASON)
    cases.append(
        _case(
            "⑦ 阈值 0（未配置）⇒ **不**宣告不可达（与 W1 阈值口径同源）；"
            "健康判据 `0<0` 使两通道均报不健康 ⇒ **如实列入证据**但**结论仍为主通道**",
            manager=zero,
            expect_bypass=False,
            expect_degraded=[f"{CHANNEL_B}.components", f"{CHANNEL_A}.components"],
        )
    )

    return cases


def _exhaustive_bypass_check() -> dict:
    """穷举（主通道 × 终点状态）⇒ `bypass` 恒等于单一决策规则"""
    mismatches: list[str] = []
    for primary in (CHANNEL_B, CHANNEL_A):
        for llm_failures in (0, 3):
            manager = _manager(threshold=3)
            if primary == CHANNEL_A:
                manager.trigger_failover_to_a(source="manual", reason="演练", actor="ops")
            for _ in range(llm_failures):
                manager.record_b_llm_unavailable(reason=REASON)
            report = describe_channel_report(manager)
            expected = primary == CHANNEL_A or (primary == CHANNEL_B and llm_failures >= 3)
            if report["bypass_orchestration"] is not expected:
                mismatches.append(f"primary={primary} llm_failures={llm_failures}")
            if report["routing_recommendation"] != (
                ROUTING_USE_A_DIRECT if expected else ROUTING_USE_PRIMARY
            ):
                mismatches.append(f"primary={primary} llm_failures={llm_failures}（推荐值不符）")
    return {
        "combinations": 4,
        "mismatches": mismatches,
        "ok": not mismatches,
    }


def main() -> int:
    cases = _build()
    exhaustive = _exhaustive_bypass_check()

    payload = {
        "probe": "channel_report",
        "ruling": (
            "W4：**双通道健康/降级统一上报** —— 一份事实源（通道 ＋ 终点 ＋ 组件）＋ 单一结论；"
            "`bypass_orchestration` 当且仅当「主通道已为 A」或「主通道为 B 且最终 LLM 不可达」；"
            "**组件降级如实列入 `degraded_dimensions` 但不改变结论**（观测与决策分离）；"
            "`fallback_action` 与 `channel_status()` **同源**（永不冲突）"
        ),
        "cases": cases,
        "exhaustive_bypass": exhaustive,
    }
    failures = [item["case"] for item in cases if not item["ok"]]
    payload["summary"] = {
        "total": len(cases),
        "failed": len(failures),
        "failed_cases": failures,
        "exhaustive_ok": exhaustive["ok"],
        "verdict": "PASS" if (not failures and exhaustive["ok"]) else "FAIL",
    }

    if "--json" in sys.argv:
        target = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "channel_report_probe-result.json"
        )
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"已落盘：{target}")

    for item in cases:
        print(
            f"{'OK ' if item['ok'] else 'BAD'} {item['case']} ⇒ "
            f"primary={item['primary_channel']} "
            f"bypass={item['bypass_orchestration']} "
            f"recommend={item['routing_recommendation']} "
            f"degraded={item['degraded_dimensions']} "
            f"fallback_action={item['fallback_action']}"
        )
    print(
        f"\n穷举（主通道 × 终点状态）：{exhaustive['combinations']} 组合 / "
        f"不符 {len(exhaustive['mismatches'])}"
    )
    print(f"\n判定: {payload['summary']['verdict']}（{len(cases)} 例 / 不符 {len(failures)}）")
    return 0 if (not failures and exhaustive["ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
