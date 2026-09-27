"""记忆载荷形态探针（CR-149 §9 问题 4「记忆写入语义」裁定的取证）

**用途**：把裁定的**护栏行为**落成可复现的判定表 —— 对 `verbatim` / `summary` 各分支
打印「是否改写载荷 / 回退原因 / 是否保留原文」，供人工核对「启用摘要后会发生什么」。

**裁定口径（2026-09-27）**：默认 `verbatim`（整轮全文）；摘要路径**可选、可配置、可回退**，
且**当前不启用**（模型档未过 §5.6 门槛）；五条护栏任一不满足即回退 `verbatim`。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.memory_payload import (  # noqa: E402
    build_memory_payload,
    reset_memory_summarizer,
)

QUERY = "用户的提问"
RESPONSE = "回答正文。" * 40  # 200 字符（800 字节）

# 「摘要生效」用例的样例摘要：必须 ≥ MIN_CHARS 且严格短于 RESPONSE（否则探针自身失效）
SUMMARY_OK = (
    "提炼结论：用户询问上下文装配在超时情况下的降级路径，"
    "回答给出三条口径（取数/预算/组装）并附验证方式，末尾提示人工复核。"
)


def _case(
    name: str,
    *,
    mode: str,
    summarizer,
    min_chars: int = 40,
    keep: bool = True,
    expect_applied: bool = False,
) -> dict:
    previous_mode = settings.WRITEBACK_MEMORY_PAYLOAD_MODE
    previous_min = settings.WRITEBACK_SUMMARY_MIN_CHARS
    previous_keep = settings.WRITEBACK_SUMMARY_KEEP_ORIGINAL
    settings.WRITEBACK_MEMORY_PAYLOAD_MODE = mode
    settings.WRITEBACK_SUMMARY_MIN_CHARS = min_chars
    settings.WRITEBACK_SUMMARY_KEEP_ORIGINAL = keep
    try:
        reset_memory_summarizer()
        fields, meta = build_memory_payload(QUERY, RESPONSE, summarizer=summarizer)
        applied = bool(meta["applied"])
        return {
            "case": name,
            "payload_response_chars": len(str(fields.get("response") or "")),
            "payload_response_is_verbatim": fields.get("response") == RESPONSE,
            "memory_type": fields.get("memory_type"),
            "origin_kept": "metadata" in fields,
            "applied": applied,
            "reason": meta["reason"],
            "expect_applied": expect_applied,
            "ok": applied == expect_applied,
        }
    finally:
        settings.WRITEBACK_MEMORY_PAYLOAD_MODE = previous_mode
        settings.WRITEBACK_SUMMARY_MIN_CHARS = previous_min
        settings.WRITEBACK_SUMMARY_KEEP_ORIGINAL = previous_keep
        reset_memory_summarizer()


def _boom(_query: str, _text: str) -> str:
    raise RuntimeError("模型不可用")


def main() -> int:
    cases = [
        _case("① 默认 verbatim", mode="verbatim", summarizer=lambda _q, _t: "不该被用到"),
        _case("② summary 但未注入提炼器", mode="summary", summarizer=None),
        _case("③ summary 且提炼器异常", mode="summary", summarizer=_boom),
        _case("④ summary 返回空", mode="summary", summarizer=lambda _q, _t: "   "),
        _case("⑤ summary 过短（< 40）", mode="summary", summarizer=lambda _q, _t: "太短"),
        _case("⑥ summary 未压缩（返回原文）", mode="summary", summarizer=lambda _q, _t: _t),
        _case(
            "⑦ summary 生效（保留原文）",
            mode="summary",
            summarizer=lambda _q, _t: SUMMARY_OK,
            expect_applied=True,
        ),
        _case(
            "⑧ summary 生效（不保留原文）",
            mode="summary",
            summarizer=lambda _q, _t: SUMMARY_OK,
            keep=False,
            expect_applied=True,
        ),
        _case("⑨ 配置非法 ⇒ fail-safe", mode="summarise_typo", summarizer=lambda _q, _t: "x" * 60),
    ]
    report = {
        "probe": "memory_payload_mode",
        "ruling": "§9 问题 4：默认 verbatim（整轮全文）；摘要可选、可配置、可回退，当前不启用",
        "source_response_chars": len(RESPONSE),
        "sample_summary_chars": len(SUMMARY_OK),
        "cases": cases,
        "guardrail_summary": (
            "改写**仅在**以下五条全部满足时发生：已注入提炼器 / 未抛异常 / 非空 / "
            "≥ MIN_CHARS / 严格短于原文；任一不满足 ⇒ 回退 verbatim（默认路径零改动）"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 探针自检：样例摘要必须真的能触发「生效」，否则用例名与实际行为不符（判据保真度）
    sample_ok = 40 <= len(SUMMARY_OK) < len(RESPONSE)
    failed = [item["case"] for item in cases if not item["ok"]]
    verdict_ok = sample_ok and not failed
    verdict = "PASS" if verdict_ok else "FAIL"
    print(
        f"probe self-check: {verdict}（样例摘要 {len(SUMMARY_OK)} 字，"
        f"需 40 ≤ n < {len(RESPONSE)}；用例不符 {len(failed)} 个）"
    )
    for name in failed:
        print(f"  ! 用例期望与实测不符: {name}")
    report["self_check"] = {"ok": verdict_ok, "sample_summary_chars": len(SUMMARY_OK), "mismatched": failed}

    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "memory_payload_probe-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
