"""画像提炼器形态与门控探针（CR-149 §9 问题 7 裁定的取证）

**用途**：把裁定的**契约行为**落成可复现的判定表 —— 对「形态判定」与「三条件就绪门控」
各分支打印「是否注入 / 是否走 LLM / 理由 / 提炼结果」，供人工核对
「开启画像 LLM 提炼后会发生什么、不满足条件时会不会被静默放行」。

**裁定口径（2026-09-27）**：提炼器**形态＝独立同步客户端**（部署进程级注入），
**不放行**网关同步桥；**三条件就绪**（门控开 ＋ 提炼器已注入 ＋ 模型已声明）缺一即
**不注入**（纯规则路径，**不臆造能力**）；**默认关闭** ⇒ 线上零变化。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration import profile_refine_gate as gate  # noqa: E402
from app.services import profile_refine  # noqa: E402

DIALOGUE = {"query": "怎么优化检索速度？", "response": "可以考虑建立索引与缓存策略。"}
TONE_ASSERTIVE = {"person": {"tone": "assertive"}}


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


def _boom(_dialogue):
    raise RuntimeError("client down")


def _slow(_dialogue):
    time.sleep(0.4)
    return TONE_ASSERTIVE


def _run_case(name: str, *, enabled, model, refiner, timeout_ms=2000, form=None) -> dict:
    """临时改配置跑一个分支（返回判定键；含「是否注入」与「实际提炼结果」）"""
    previous_enabled = settings.PROFILE_LLM_REFINE_ENABLED
    previous_model = settings.PROFILE_LLM_REFINE_MODEL
    previous_timeout = settings.PROFILE_LLM_REFINE_TIMEOUT_MS
    settings.PROFILE_LLM_REFINE_ENABLED = enabled
    settings.PROFILE_LLM_REFINE_MODEL = model
    settings.PROFILE_LLM_REFINE_TIMEOUT_MS = timeout_ms
    profile_refine.set_active_profile_refiner(None)
    try:
        plan = gate.describe_profile_refine_plan(refiner=refiner, form=form)
        installed = gate.install_profile_refiner_if_enabled(refiner, form=form)
        result = profile_refine.refine_profile_delta(
            dialogue=DIALOGUE, extract_targets=["person"], updates=None
        )
        return {
            "case": name,
            "form": plan["form"],
            "will_use_llm": plan["will_use_llm"],
            "reason": plan["reason"],
            "installed": installed,
            "tone": (result.get("person") or {}).get("tone"),
        }
    finally:
        settings.PROFILE_LLM_REFINE_ENABLED = previous_enabled
        settings.PROFILE_LLM_REFINE_MODEL = previous_model
        settings.PROFILE_LLM_REFINE_TIMEOUT_MS = previous_timeout
        gate.reset_profile_refine_gate()


def main() -> int:
    report: dict = {
        "probe": "profile_refiner_gate",
        "ruling": "§9 问题 7：提炼器形态＝独立同步客户端（不放行网关同步桥）；三条件就绪门控，默认关闭",
    }
    cases: list[dict] = []

    # ① 默认（门控关）⇒ 不注入、纯规则
    cases.append(
        _case(
            "① 默认关态（有提炼器亦不注入）",
            {"will_use_llm": False, "installed": False, "tone": "inquisitive", "form": "standalone_sync_client"},
            _run_case("① 默认关态（有提炼器亦不注入）", enabled=False, model="qwen3:0.6b", refiner=lambda _d: TONE_ASSERTIVE),
        )
    )
    # ② 门控开但未注入提炼器 ⇒ 不注入（不信「应该有」）
    cases.append(
        _case(
            "② 开态 + 提炼器缺失 ⇒ 不注入（refiner_absent）",
            {"will_use_llm": False, "installed": False, "tone": "inquisitive"},
            _run_case("② 开态 + 提炼器缺失 ⇒ 不注入（refiner_absent）", enabled=True, model="qwen3:0.6b", refiner=None),
        )
    )
    # ③ 门控开 + 提炼器 + 模型未声明 ⇒ 不注入（model_absent）
    cases.append(
        _case(
            "③ 开态 + 模型未声明 ⇒ 不注入（model_absent）",
            {"will_use_llm": False, "installed": False, "tone": "inquisitive"},
            _run_case("③ 开态 + 模型未声明 ⇒ 不注入（model_absent）", enabled=True, model="", refiner=lambda _d: TONE_ASSERTIVE),
        )
    )
    # ④ 三条件齐备 ⇒ 注入且 provider 产出生效
    cases.append(
        _case(
            "④ 三条件齐备 ⇒ 注入且 LLM 产出生效",
            {"will_use_llm": True, "installed": True, "tone": "assertive"},
            _run_case("④ 三条件齐备 ⇒ 注入且 LLM 产出生效", enabled=True, model="qwen3:0.6b", refiner=lambda _d: TONE_ASSERTIVE),
        )
    )
    # ⑤ 注入后提炼器异常 ⇒ 规则兜底
    cases.append(
        _case(
            "⑤ 注入后提炼器异常 ⇒ 规则兜底",
            {"installed": True, "tone": "inquisitive"},
            _run_case("⑤ 注入后提炼器异常 ⇒ 规则兜底", enabled=True, model="qwen3:0.6b", refiner=_boom),
        )
    )
    # ⑥ 注入后提炼器超时 ⇒ 规则兜底
    cases.append(
        _case(
            "⑥ 注入后提炼器超时（50ms < 400ms）⇒ 规则兜底",
            {"installed": True, "tone": "inquisitive"},
            _run_case("⑥ 注入后提炼器超时（50ms < 400ms）⇒ 规则兜底", enabled=True, model="qwen3:0.6b", refiner=_slow, timeout_ms=50),
        )
    )
    # ⑦ 显式传「网关同步桥」形态 ⇒ 仍按独立客户端口径
    cases.append(
        _case(
            "⑦ 显式传 gateway_sync_bridge ⇒ 回退独立客户端",
            {"will_use_llm": True, "form": "standalone_sync_client"},
            _run_case("⑦ 显式传 gateway_sync_bridge ⇒ 回退独立客户端", enabled=True, model="qwen3:0.6b", refiner=lambda _d: TONE_ASSERTIVE, form="gateway_sync_bridge"),
        )
    )
    # ⑧ 门控非法值 ⇒ 关（fail-safe）
    cases.append(
        _case(
            "⑧ 门控非法值 ⇒ 回退关闭",
            {"will_use_llm": False, "installed": False, "tone": "inquisitive"},
            _run_case("⑧ 门控非法值 ⇒ 回退关闭", enabled="maybe", model="qwen3:0.6b", refiner=lambda _d: TONE_ASSERTIVE),
        )
    )

    report["cases"] = cases
    report["guardrail_summary"] = (
        "形态**恒为** standalone_sync_client（任何候选，含 gateway_sync_bridge）；"
        "**三条件就绪**（门控开 ＋ 提炼器已注入 ＋ 模型已声明）缺一即不注入 ⇒ 纯规则；"
        "注入后异常/超时 ⇒ 无产出 ⇒ 规则兜底（绝不丢标签）"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # ---- 探针自检 ----
    failed = [item["case"] for item in cases if not item["ok"]]
    # 核心契约独立复核：任何候选形态都不得解析为网关同步桥
    candidates = ["gateway_sync_bridge", "GATEWAY_SYNC_BRIDGE", "call_llm", "", None, "standalone_sync_client"]
    bridge_leaked = [
        candidate
        for candidate in candidates
        if gate.resolve_profile_refiner_form(candidate) == gate.PROFILE_REFINER_FORM_GATEWAY_SYNC_BRIDGE
    ]
    verdict_ok = not failed and not bridge_leaked
    verdict = "PASS" if verdict_ok else "FAIL"
    print(
        f"probe self-check: {verdict}（{len(cases)} 例 / 不符 {len(failed)} 个 / "
        f"误判网关桥 {len(bridge_leaked)} 个）"
    )
    for name in failed:
        print(f"  ! 用例期望与实测不符: {name}")
    for candidate in bridge_leaked:
        print(f"  ! 候选被误判为网关同步桥: {candidate!r}")
    report["self_check"] = {
        "ok": verdict_ok,
        "cases": len(cases),
        "mismatched": failed,
        "bridge_leaked": bridge_leaked,
    }

    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "profile_refiner_gate_probe-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
