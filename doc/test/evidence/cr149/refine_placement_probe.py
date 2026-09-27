"""精炼推理位置探针（CR-149 §9 问题 2「精炼推理位置」裁定的取证）

**用途**：把裁定的**四道门禁与理由词表**落成可复现的判定表 —— 逐组合打印
「是否放行 / 走哪档 / 位置 / 预算 / 理由」，并在结尾**自检**（逐例期望一致）：
任一不符即 `FAIL` 且**返回码非 0**（探针自身不得「名为判定、实为摆设」）。

**裁定口径（2026-09-27）**：位置**由部署显式声明**（`disabled` 默认 / `gpu_node` /
`local_cpu_async`）；**在线通道永不生成式**；放行须同时满足「位置已声明 + 模型编码已声明 +
档位复测通过（§5.6）+ 端点探活可达」；本机 CPU 档另须「实测耗时 ≤ 超时预算」。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration import refine as refine_module  # noqa: E402
from app.edgerouter.orchestration import refine_placement as rp  # noqa: E402

SOURCES = ["用户偏好简洁回答，不喜欢冗长解释。", "项目预算上限为 120 万元。"]
PROBE_CALLS = {"n": 0}


def _probe_ok() -> dict:
    PROBE_CALLS["n"] += 1
    return {"ok": True, "detail": "gpu node reachable"}


def _probe_boom() -> dict:
    PROBE_CALLS["n"] += 1
    raise RuntimeError("端点不可达")


def _case(
    name: str,
    *,
    expect_allowed: bool,
    expect_reason: str | None = None,
    channel: str = "async",
    triggered: bool = True,
    probe=None,
    expect_probe_calls: int | None = None,
    **settings_overrides,
) -> dict:
    """跑一个组合；用例**自带期望**（`expect_allowed` 必填，理由可选精确匹配）"""
    previous = {
        key: getattr(settings, key, None)
        for key in (
            "CONTEXT_REFINE_INFERENCE_TARGET",
            "CONTEXT_REFINE_INFERENCE_MODEL",
            "CONTEXT_REFINE_INFERENCE_TIMEOUT_MS",
            "CONTEXT_REFINE_TIER_VERIFIED",
            "CONTEXT_REFINE_CPU_MEASURED_MS",
        )
    }
    for key, value in settings_overrides.items():
        setattr(settings, key, value)
    PROBE_CALLS["n"] = 0
    try:
        rp.register_refine_inference_probe(probe)
        decision = rp.plan_refine_inference(channel=channel, triggered=triggered)
    finally:
        rp.reset_refine_inference_probe()
        for key, value in previous.items():
            setattr(settings, key, value)

    ok = decision["allowed"] == expect_allowed
    if expect_reason is not None:
        ok = ok and decision["reason"] == expect_reason
    if expect_probe_calls is not None:
        ok = ok and PROBE_CALLS["n"] == expect_probe_calls
    return {
        "case": name,
        "channel": decision["channel"],
        "target": decision["target"],
        "allowed": decision["allowed"],
        "mode": decision["mode"],
        "placement": decision["placement"],
        "budget_ms": decision["budget_ms"],
        "capacity_risk": decision["capacity_risk"],
        "reason": decision["reason"],
        "probe_calls": PROBE_CALLS["n"],
        "expect_allowed": expect_allowed,
        "expect_reason": expect_reason,
        "ok": ok,
    }


def main() -> int:
    cases = [
        _case(
            "① 默认（未声明位置）",
            expect_allowed=False,
            expect_reason="inference_disabled",
            CONTEXT_REFINE_INFERENCE_TARGET="disabled",
        ),
        _case(
            "② 在线通道 + 位置/模型/复测/探活全部就绪 ⇒ 仍规则档（红线）",
            expect_allowed=False,
            expect_reason="online_path_forbids_generative",
            channel="online",
            probe=_probe_ok,
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
        ),
        _case(
            "③ 非法位置值 ⇒ 回退 disabled",
            expect_allowed=False,
            expect_reason="invalid_target:gpu",
            CONTEXT_REFINE_INFERENCE_TARGET="gpu",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
            probe=_probe_ok,
        ),
        _case(
            "④ 位置就绪但未声明模型编码",
            expect_allowed=False,
            expect_reason="model_absent",
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="",
            CONTEXT_REFINE_TIER_VERIFIED=True,
            probe=_probe_ok,
        ),
        _case(
            "⑤ 模型已声明但档位未复测（§5.6 门槛）",
            expect_allowed=False,
            expect_reason="tier_not_verified",
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=False,
            probe=_probe_ok,
        ),
        _case(
            "⑥ 位置/模型/复测就绪但探活未注入（不臆造能力）",
            expect_allowed=False,
            expect_reason="probe_absent",
            probe=None,
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
        ),
        _case(
            "⑦ 探活异常 ⇒ 视为不可达",
            expect_allowed=False,
            expect_reason="probe_unavailable",
            probe=_probe_boom,
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
        ),
        _case(
            "⑧ GPU 节点就绪 ⇒ 放行（model / 预算 30000ms）",
            expect_allowed=True,
            expect_reason="gpu_node_ready",
            probe=_probe_ok,
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
        ),
        _case(
            "⑨ 本机 CPU 档未声明实测耗时 ⇒ 不放行",
            expect_allowed=False,
            expect_reason="cpu_measurement_absent",
            CONTEXT_REFINE_INFERENCE_TARGET="local_cpu_async",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:0.6b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
            CONTEXT_REFINE_CPU_MEASURED_MS=0,
        ),
        _case(
            "⑩ 本机 CPU 档实测 32600ms > 预算 30000ms（§5.4 实测值）",
            expect_allowed=False,
            expect_reason="cpu_over_budget:32600>30000",
            CONTEXT_REFINE_INFERENCE_TARGET="local_cpu_async",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:0.6b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
            CONTEXT_REFINE_CPU_MEASURED_MS=32600,
        ),
        _case(
            "⑪ 本机 CPU 档实测 9000ms ≤ 预算 ⇒ 放行但标 capacity_risk",
            expect_allowed=True,
            expect_reason="cpu_async_declared_ok",
            CONTEXT_REFINE_INFERENCE_TARGET="local_cpu_async",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:0.6b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
            CONTEXT_REFINE_CPU_MEASURED_MS=9000,
        ),
        _case(
            "⑫ 未触发 ⇒ 不精炼且不调用探活",
            expect_allowed=False,
            expect_reason="not_triggered",
            triggered=False,
            probe=_probe_ok,
            expect_probe_calls=0,
            CONTEXT_REFINE_INFERENCE_TARGET="gpu_node",
            CONTEXT_REFINE_INFERENCE_MODEL="qwen3:1.7b",
            CONTEXT_REFINE_TIER_VERIFIED=True,
        ),
    ]

    # ⑬ 组合口径：**位置放行 ≠ 免检**（放行后输出仍须过 §5.3 护栏）
    rp.register_refine_inference_probe(_probe_ok)
    previous_guard = {
        key: getattr(settings, key, None)
        for key in (
            "CONTEXT_REFINE_INFERENCE_TARGET",
            "CONTEXT_REFINE_INFERENCE_MODEL",
            "CONTEXT_REFINE_TIER_VERIFIED",
        )
    }
    try:
        settings.CONTEXT_REFINE_INFERENCE_TARGET = "gpu_node"
        settings.CONTEXT_REFINE_INFERENCE_MODEL = "qwen3:1.7b"
        settings.CONTEXT_REFINE_TIER_VERIFIED = True
        placement = rp.plan_refine_inference(channel="async")
    finally:
        rp.reset_refine_inference_probe()
        for key, value in previous_guard.items():
            setattr(settings, key, value)
    good = refine_module.validate_refine_output(
        ["1. 用户偏好简洁回答，不喜欢冗长解释。"], sources=SOURCES
    )
    hallucinated = refine_module.validate_refine_output(
        ["1. 用户偏好简洁回答，预算上限为 999 万元。"], sources=SOURCES
    )
    guard_case = {
        "case": "⑬ 位置放行后输出护栏仍拦（串联）",
        "placement_allowed": placement["allowed"],
        "valid_output_accepted": good["valid"],
        "hallucinated_output_rejected": not hallucinated["valid"],
        "violations": hallucinated["violations"],
        "ok": bool(
            placement["allowed"] and good["valid"] and not hallucinated["valid"]
        ),
    }

    # ⑭ 压缩率目标（§5.8，只读观测）
    ratio_cases = [
        ("memory", 1000, 300, True, ""),
        ("memory", 1000, 100, False, "below_target"),
        ("rag", 1000, 800, False, "above_target"),
    ]
    ratio_rows = []
    for segment, in_tokens, out_tokens, within, reason in ratio_cases:
        result = rp.ratio_within_target(segment, in_tokens=in_tokens, out_tokens=out_tokens)
        ratio_rows.append(
            {
                "case": f"⑭ 压缩率目标 {segment} {out_tokens}/{in_tokens}",
                "ratio": result["ratio"],
                "target": result["target"],
                "within": result["within"],
                "reason": result["reason"],
                "ok": result["within"] == within and result["reason"] == reason,
            }
        )

    all_cases = cases + [guard_case] + ratio_rows
    failed = [item["case"] for item in all_cases if not item["ok"]]
    # 阻塞分支**理由必非空**（可审计：不得静默降级）
    silent_blocks = [
        item["case"]
        for item in all_cases
        if item.get("allowed") is False and not str(item.get("reason") or "").strip()
    ]
    verdict_ok = not failed and not silent_blocks

    report = {
        "probe": "refine_placement",
        "ruling": (
            "§9 问题 2：位置由部署显式声明（disabled 默认 / gpu_node / local_cpu_async）；"
            "在线通道永不生成式；放行须过四道门禁"
        ),
        "source_facts": {
            "local_cpu_compress_p50_seconds": {"qwen3:0.6b": 32.6, "llama3.2:1b": 76.8},
            "lan_cpu_compress_p50_seconds": {"qwen2.5:0.5b": 7.1},
            "async_budget_ms": 30000,
            "online_budget_ms": {"cpu": 800, "gpu": 400},
            "fact_retention_gate": 0.9,
        },
        "cases": all_cases,
        "blocked_without_reason": silent_blocks,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    verdict = "PASS" if verdict_ok else "FAIL"
    print(
        f"probe self-check: {verdict}（{len(all_cases)} 例，不符 {len(failed)}，"
        f"静默降级 {len(silent_blocks)}）"
    )
    for name in failed:
        print(f"  ! 用例期望与实测不符: {name}")

    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "refine_placement_probe-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
