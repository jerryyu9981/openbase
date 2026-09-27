"""通道自动回落触发链探针（CR-149 §9 问题 5「通道切换触发权」裁定的取证）

**用途**：把裁定的**契约行为**落成可复现的判定表 —— 对「自动回落触发链」各分支
打印「是否切换 / 是否单主 / 审计事件 / 写路径联动」，供人工核对「开启自动接管后会发生什么」。

**裁定口径（2026-09-27）**：触发权**以人工/运维显式为主**（`CHANNEL_AUTO_FAILOVER_ENABLED`
**默认 False ⇒ 只登记不切换**）；组件级连续失败自动接管为**显式可选**。**显式开启**后
连续失败达阈值 ⇒ 自动回落 A，且须满足：**保持单主**（禁双主双写）／**审计 actor=auto
可区分**／**阈值配置键驱动**／**幂等**／**A 接管期间写暂停**（T11 联动）／**回切仍人工门禁**。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.api import openllm_gateway as gw  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.identity import channel as channel_module  # noqa: E402


def _case(name: str, expect: dict, actual: dict) -> dict:
    """汇总单个用例（expect/actual 均为判定键 ⇒ 自检可逐项比对）"""
    mismatched = [key for key in expect if expect[key] != actual.get(key)]
    return {
        "case": name,
        "expect": expect,
        "actual": actual,
        "ok": not mismatched,
        "mismatched": mismatched,
    }


def _reach_b_failures(times: int) -> None:
    """经生产接线点（源 1：组件级降级）连续失败 N 次"""
    for _ in range(times):
        gw._note_component_channel_health(
            type("Run", (), {"degraded": ["rag"], "rag_source": "external", "builtin_fallback_reason": ""})()
        )


def main() -> int:
    report: dict = {
        "probe": "channel_auto_failover",
        "ruling": "§9 问题 5：触发权以人工/运维显式为主；自动接管为显式可选（默认 False 只登记不切换）",
    }
    cases: list[dict] = []

    def snapshot() -> dict:
        return {
            "CHANNEL_PREFERENCE": settings.CHANNEL_PREFERENCE,
            "CHANNEL_AUTO_FAILOVER_ENABLED": settings.CHANNEL_AUTO_FAILOVER_ENABLED,
            "CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD": settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD,
            "WRITEBACK_CHANNEL_GUARD_ENABLED": settings.WRITEBACK_CHANNEL_GUARD_ENABLED,
        }

    def restore(previous: dict) -> None:
        for key, value in previous.items():
            setattr(settings, key, value)
        channel_module.reset_channel_state_manager()

    # ① 关态达阈值 ⇒ 只登记不切换（不代行裁定）
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = False
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        health = manager.b_health()
        cases.append(
            _case(
                "① 关态达阈值 ⇒ 只登记不切换且健康如实",
                {"primary_channel": "b", "healthy_b": False, "switched": False},
                {
                    "primary_channel": manager.primary_channel,
                    "healthy_b": health["healthy"],
                    "switched": any(
                        event["action"] == "failover_b_to_a"
                        for event in manager.audit_trail()
                    ),
                },
            )
        )
    finally:
        restore(previous)

    # ② 开态未达阈值 ⇒ 不切换
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(2)
        cases.append(
            _case(
                "② 开态未达阈值（2/3）⇒ 不切换",
                {"primary_channel": "b"},
                {"primary_channel": manager.primary_channel},
            )
        )
    finally:
        restore(previous)

    # ③ 开态达阈值 ⇒ 自动回落 A 且单主（不双主）
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        status = manager.channel_status()
        cases.append(
            _case(
                "③ 开态达阈值 ⇒ 自动回落 A 且单主",
                {"primary_channel": "a", "single_primary": True},
                {
                    "primary_channel": status["primary_channel"],
                    "single_primary": status["single_primary"],
                },
            )
        )
    finally:
        restore(previous)

    # ④ 回落审计：恰一次 / actor=auto / source=component_degrade / reason 含阈值证据
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        failovers = [
            event
            for event in manager.audit_trail()
            if event["action"] == "failover_b_to_a"
        ]
        evidence = (
            len(failovers) == 1
            and failovers[0]["actor"] == "auto"
            and failovers[0]["source"] == channel_module.DEGRADE_SOURCE_COMPONENT
            and "连续失败" in failovers[0]["reason"]
            and "阈值" in failovers[0]["reason"]
        )
        cases.append(
            _case(
                "④ 回落审计可复盘（actor=auto / 含阈值证据）",
                {"audit_ok": True},
                {"audit_ok": evidence, "audit_count": len(failovers)},
            )
        )
    finally:
        restore(previous)

    # ⑤ 阈值配置键驱动（threshold=5 ⇒ 3 次不切、5 次切）
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 5
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        primary_three = manager.primary_channel
        _reach_b_failures(2)
        primary_five = manager.primary_channel
        cases.append(
            _case(
                "⑤ 阈值配置键驱动（5 ⇒ 3 次不切、5 次切）",
                {"primary_three": "b", "primary_five": "a"},
                {"primary_three": primary_three, "primary_five": primary_five},
            )
        )
    finally:
        restore(previous)

    # ⑥ 幂等：A 已主时再达阈值 ⇒ 评估返回 False 且不重复审计
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        audit_before = len(manager.audit_trail())
        evaluation = manager.evaluate_auto_failover()
        cases.append(
            _case(
                "⑥ 幂等（A 已主再达阈值 ⇒ False 且不重复审计）",
                {"evaluation": False, "audit_unchanged": True},
                {
                    "evaluation": evaluation,
                    "audit_unchanged": len(manager.audit_trail()) == audit_before,
                },
            )
        )
    finally:
        restore(previous)

    # ⑦ 与 T11 联动：自动回落 A 后写路径暂停（不双写）
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        settings.WRITEBACK_CHANNEL_GUARD_ENABLED = True
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        allowed, reason = gw._writeback_channel_primary()
        cases.append(
            _case(
                "⑦ A 接管期间写路径暂停（T11 联动）",
                {"allowed": False, "reason": "channel_not_primary"},
                {"allowed": allowed, "reason": reason},
            )
        )
    finally:
        restore(previous)

    # ⑧ 回切不代行：无演练窗口 ⇒ ChannelSwitchError
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = True
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        blocked = False
        try:
            manager.switch_back_to_b(actor="ops")
        except channel_module.ChannelSwitchError:
            blocked = True
        cases.append(
            _case(
                "⑧ 自动接管不代行回切（无演练窗口 ⇒ 拒绝）",
                {"blocked": True},
                {"blocked": blocked},
            )
        )
    finally:
        restore(previous)

    # ⑨ 显式 vs 自动在审计上可区分（actor=ops vs auto）
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        manager.trigger_failover_to_a(
            source=channel_module.DEGRADE_SOURCE_MANUAL, reason="演练"
        )
        failover = next(
            event
            for event in manager.audit_trail()
            if event["action"] == "failover_b_to_a"
        )
        cases.append(
            _case(
                "⑨ 显式接管 actor=ops（与自动 actor=auto 可区分）",
                {"actor": "ops", "source": "manual"},
                {"actor": failover["actor"], "source": failover["source"]},
            )
        )
    finally:
        restore(previous)

    # ⑩ 关态 evaluate 返回 False 且无切换审计
    previous = snapshot()
    try:
        settings.CHANNEL_PREFERENCE = "b-primary"
        settings.CHANNEL_AUTO_FAILOVER_ENABLED = False
        settings.CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD = 3
        channel_module.reset_channel_state_manager()
        manager = gw._get_channel_manager()
        _reach_b_failures(3)
        evaluation = manager.evaluate_auto_failover()
        cases.append(
            _case(
                "⑩ 关态评估返回 False 且不产生切换审计",
                {"evaluation": False, "switched": False},
                {
                    "evaluation": evaluation,
                    "switched": any(
                        event["action"] == "failover_b_to_a"
                        for event in manager.audit_trail()
                    ),
                },
            )
        )
    finally:
        restore(previous)

    report["cases"] = cases
    report["contract_summary"] = (
        "自动回落**仅在**显式开启且达阈值时发生：保持单主（禁双主双写）／审计 actor=auto 可区分／"
        "阈值配置键驱动／幂等／A 接管期间写暂停（T11 联动）／回切仍人工门禁；"
        "默认关态只登记不切换（不代行裁定）"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

    failed = [item["case"] for item in cases if not item["ok"]]
    verdict_ok = not failed
    verdict = "PASS" if verdict_ok else "FAIL"
    print(
        f"probe self-check: {verdict}（{len(cases)} 例 / 不符 {len(failed)} 个）"
    )
    for name in failed:
        print(f"  ! 用例期望与实测不符: {name}")
    report["self_check"] = {"ok": verdict_ok, "mismatched": failed}

    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "channel_auto_failover_probe-result.json",
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
