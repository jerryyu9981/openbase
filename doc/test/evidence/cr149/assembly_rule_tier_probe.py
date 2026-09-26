"""方案 §3.4 规则档余项 ＋ §3.5 稳定引用编号 —— 运行态证据探针

对应方案 v1.12.0 §10 待登记项 7 的 (a)~(d)（v1.13.0 已实施）：

  (a) 元数据噪声剥离：平铺字段的 `None`/空值与链路元数据键不进入 Prompt；
  (b) 相邻记忆条目同义重复行合并：仅 memory 段、仅相邻，保留较长者、信息不丢失；
  (c) `refine` 回执字段：`{mode, model, in_tokens, out_tokens, elapsed_ms, fallback}`；
  (d) 稳定引用编号 `[M1]`/`[K1]`：与归因 A 片段下标对齐，且裁剪/去重后**不重排**。

**口径**：全部走**真实实现**（`PromptAssembler` / `build_prompt` / 真实策略），
仅 token 计数器用 1 字符 = 1 token 的确定性替身（与既有预算护栏同口径），
便于逐项给出可复核的数值。

用法：``python doc/test/evidence/cr149/assembly_rule_tier_probe.py``（cwd = OpenLLM/backend）
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from typing import Any

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.assembler import PromptAssembler  # noqa: E402
from app.edgerouter.orchestration.prompt_pipeline import (  # noqa: E402
    BudgetPolicy,
    build_prompt,
)


def _chars(text: str) -> int:
    return len(text or "")


@contextmanager
def _temp(**overrides: Any):
    previous = {key: getattr(settings, key, None) for key in overrides}
    for key, value in overrides.items():
        setattr(settings, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            setattr(settings, key, value)


def _policy(**overrides: Any) -> BudgetPolicy:
    params: dict[str, Any] = {
        "enabled": True,
        "window_tokens": 1000,
        "output_reserve_tokens": 0,
        "quota_ratios": {"system": 0.05, "profile": 0.10, "memory": 0.10, "rag": 0.10, "history": 0.10},
        "single_item_max_tokens": 0,
        "dedup_enabled": True,
    }
    params.update(overrides)
    return BudgetPolicy(**params)


def probe_metadata_noise() -> dict[str, Any]:
    """(a) 元数据噪声剥离：噪声键/空值被丢弃，依据性字段保留"""
    payload = {
        "trace_id": None,
        "request_id": "req-abc-123",
        "session_id": "sess-1",
        "score": 0.87,
        "source": "kb-1",
        "summary": "知识库摘要内容",
        "empty_note": "   ",
    }
    assembler = PromptAssembler()
    with _temp(CONTEXT_STRIP_METADATA_ENABLED=True):
        stripped = assembler.format_context("rag", payload)
    with _temp(CONTEXT_STRIP_METADATA_ENABLED=False):
        raw = assembler.format_context("rag", payload)
    return {
        "switch_on_text": stripped,
        "switch_off_text": raw,
        "noise_removed": all(key not in stripped for key in ("trace_id", "request_id", "session_id", "empty_note")),
        "basis_fields_kept": all(key in stripped for key in ("score", "source", "summary")),
        "tokens_saved": _chars(raw) - _chars(stripped),
        "all_noise_yields_empty": PromptAssembler().format_context("rag", {"trace_id": None}) == "",
    }


def probe_adjacent_merge() -> dict[str, Any]:
    """(b) 相邻同义合并：memory 段生效、rag 段不生效、保留较长者、信息不丢失"""
    memory = "\n".join(
        [
            "1. 用户偏好简洁回答",
            "2. 用户偏好简洁回答，不喜欢冗长解释",
            "3. 项目使用 Python 与 FastAPI",
        ]
    )
    same_in_rag = "\n".join(["1. 知识甲内容", "2. 知识甲内容，补充说明"])
    _prompt, merged_comp = build_prompt(
        query="问", memory_ctx=memory, count_tokens=_chars, budget=_policy()
    )
    prompt_off, comp_off = build_prompt(
        query="问",
        memory_ctx=memory,
        count_tokens=_chars,
        budget=_policy(adjacent_merge_enabled=False),
    )
    _p, rag_comp = build_prompt(
        query="问", rag_ctx=same_in_rag, count_tokens=_chars, budget=_policy()
    )
    with _temp(CONTEXT_BUDGET_ENABLED=True):
        from app.edgerouter.orchestration.prompt_pipeline import load_budget_policy

        default_policy = load_budget_policy()
    return {
        "memory_report": merged_comp.truncated.get("memory"),
        "rag_report": rag_comp.truncated.get("rag"),
        "merged_items": (merged_comp.truncated.get("memory") or {}).get("merged_items", 0),
        "longer_text_kept": "不喜欢冗长解释" in _prompt,
        "dedup_counter_untouched": (merged_comp.truncated.get("memory") or {}).get("dropped_items", 0) == 0,
        "rag_not_merged": "merged_items" not in (rag_comp.truncated.get("rag") or {}),
        "switch_off_keeps_both": prompt_off.count("用户偏好简洁回答") == 2
        and "merged_items" not in (comp_off.truncated.get("memory") or {}),
        "default_enabled": default_policy.adjacent_merge_enabled,
        "default_similarity": default_policy.adjacent_merge_similarity,
    }


def probe_refine_receipt() -> dict[str, Any]:
    """(c) `refine` 回执：规则档落痕、只计四类素材、裁剪后 out < in"""
    memory = "\n".join(["1. " + "甲" * 400, "2. " + "乙" * 400])
    _prompt, comp = build_prompt(
        query="这段查询很长" * 20,
        system_prompt="系统指令" * 20,
        memory_ctx=memory,
        count_tokens=_chars,
        budget=_policy(),
    )
    _p2, off_comp = build_prompt(
        query="问", memory_ctx="1. 甲", count_tokens=_chars, budget=BudgetPolicy(enabled=False)
    )
    _p3, noc_comp = build_prompt(query="问", memory_ctx="1. 甲", budget=_policy())
    material_only = len(memory)
    return {
        "receipt": comp.refine,
        "mode_is_rule": comp.refine.get("mode") == "rule",
        "fallback_false": comp.refine.get("fallback") is False,
        "counts_material_only": comp.refine.get("in_tokens") == material_only,
        "out_lt_in": comp.refine.get("out_tokens", 0) < comp.refine.get("in_tokens", 0),
        "no_receipt_when_disabled": off_comp.refine == {},
        "no_receipt_without_counter": noc_comp.refine == {},
    }


def probe_ref_numbers() -> dict[str, Any]:
    """(d) 稳定引用编号：对齐归因下标、去重/裁剪后不重排、保底守配额"""
    with _temp(CONTEXT_REF_NUMBERS_ENABLED=True):
        labeled_memory = PromptAssembler().format_context(
            "memory", {"results": [{"content": "甲"}, {"content": "乙"}]}
        )
        labeled_rag = PromptAssembler().format_context(
            "rag", {"results": [{"content": "一"}, {"content": "二"}, {"content": "三"}]}
        )
        dedup_prompt, dedup_comp = build_prompt(
            query="问",
            memory_ctx="[M1] 甲\n[M2] 甲\n[M3] 丙",
            count_tokens=_chars,
            budget=_policy(),
        )
        floor_prompt, floor_comp = build_prompt(
            query="问",
            memory_ctx="[M7] " + "甲" * 400,
            count_tokens=_chars,
            budget=_policy(),
        )
    default_text = PromptAssembler().format_context(
        "memory", {"results": [{"content": "甲"}, {"content": "乙"}]}
    )
    return {
        "default_numbering": default_text,
        "labeled_memory": labeled_memory,
        "labeled_rag": labeled_rag,
        "dedup_report": dedup_comp.truncated.get("memory"),
        "dedup_keeps_m1_m3": "[M1]" in dedup_prompt and "[M3]" in dedup_prompt,
        "dedup_drops_m2": "[M2]" not in dedup_prompt,
        "floor_keeps_label": "[M7]" in floor_prompt,
        "floor_within_quota": floor_comp.budget["memory"]["used"]
        <= floor_comp.budget["memory"]["quota"],
    }


def main() -> int:
    report = {
        "probe": "assembly_rule_tier",
        "design_ref": "方案 §3.4 规则档（元数据噪声剥离 / 相邻同义合并 / refine 回执）＋ §3.5 稳定引用编号",
        "(a) 元数据噪声剥离": probe_metadata_noise(),
        "(b) 相邻同义合并": probe_adjacent_merge(),
        "(c) refine 回执": probe_refine_receipt(),
        "(d) 稳定引用编号": probe_ref_numbers(),
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assembly_rule_tier_probe-result.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n结果已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
