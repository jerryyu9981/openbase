"""方案 §3.2 选择（权重排序）＋ §3.4 规则档余项 ＋ §3.5 稳定引用编号 —— 运行态证据探针

对应方案 §10 待登记项 7 的 (a)~(d)（v1.13.0 实施）与 v1.14.0 新增的 (e) 权重排序：

  (a) 元数据噪声剥离：平铺字段的 `None`/空值与链路元数据键不进入 Prompt；
  (b) 相邻记忆条目同义重复行合并：仅 memory 段、仅相邻，保留较长者、信息不丢失；
  (c) `refine` 回执字段：`{mode, model, in_tokens, out_tokens, elapsed_ms, fallback}`；
  (d) 稳定引用编号 `[M1]`/`[K1]`：与归因 A 片段下标对齐，且裁剪/去重后**不重排**；
  (e) 权重排序 `rank_score`（§3.2 第三项 / §3.3 memory·rag 行）：来源分数 × 时效衰减
      （仅 memory）降序**呈现**，编号仍取原始下标；无依据 / 开关关 ⇒ 原序。

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
from datetime import datetime, timedelta
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


def probe_rank_selection() -> dict[str, Any]:
    """(e) 权重排序：来源分数 + 时效衰减；编号取原始下标；预算只吃尾部

    **v1.18.0 订正**：原基准为**硬编码时刻** `2026-09-27 12:00:00` ⇒ 「新记忆」
    （`_days_ago(0)`）的 age 在壁钟越过该时刻前被钳为 0（衰减恰 1.0）、越过之后
    变为正值（衰减 < 1.0）⇒ 输出的 `memory_order` 会**随壁钟自行翻转**
    （与 T10 ④ 同源缺陷）。现基准改取 `now()`，且把「零龄」样本改为「一天前」，
    使排序结论**确定性可复现**：无时间戳（fail-open 1.0）> 一天前 > 120 天前。
    """
    base = datetime.now()

    def _days_ago(days: float) -> str:
        return (base - timedelta(days=days)).isoformat()

    assembler = PromptAssembler()
    rag_text = assembler.format_context(
        "rag",
        {
            "results": [
                {"content": "低分", "score": 0.2},
                {"content": "高分", "score": 0.9},
                {"content": "中分", "score": 0.55},
            ]
        },
    )
    memory_text = assembler.format_context(
        "memory",
        {
            "results": [
                {"content": "旧记忆", "updated_at": _days_ago(120)},
                {"content": "新记忆", "updated_at": _days_ago(1)},
                {"content": "无时间戳记忆"},
            ]
        },
    )
    with _temp(CONTEXT_REF_NUMBERS_ENABLED=True):
        labeled_ranked = assembler.format_context(
            "rag",
            {
                "results": [
                    {"content": "低分", "score": 0.2},
                    {"content": "高分", "score": 0.9},
                ]
            },
        )
    with _temp(CONTEXT_RANK_SORT_ENABLED=False):
        switch_off = assembler.format_context(
            "rag",
            {
                "results": [
                    {"content": "低分", "score": 0.2},
                    {"content": "高分", "score": 0.9},
                ]
            },
        )
    no_key = assembler.format_context(
        "rag", {"results": [{"content": "甲"}, {"content": "乙"}, {"content": "丙"}]}
    )
    ranked_memory = assembler.format_context(
        "memory",
        {
            "results": [
                {"content": "旧" * 60, "updated_at": _days_ago(300)},
                {"content": "新" * 60, "updated_at": _days_ago(1)},
            ]
        },
    )
    _prompt, comp = build_prompt(
        query="问", memory_ctx=ranked_memory, count_tokens=_chars, budget=_policy()
    )
    return {
        "rag_order": rag_text,
        "rag_sorted_by_score": rag_text.index("高分")
        < rag_text.index("中分")
        < rag_text.index("低分"),
        "memory_order": memory_text,
        "memory_newest_first": memory_text.index("新记忆") < memory_text.index("旧记忆"),
        "memory_missing_timestamp_not_demoted": memory_text.index("无时间戳记忆")
        < memory_text.index("旧记忆"),
        "labeled_ranked": labeled_ranked,
        "labels_keep_original_index": labeled_ranked.startswith("[K2] 高分"),
        "switch_off_order": switch_off,
        "switch_off_keeps_original": switch_off == "1. 低分\n2. 高分",
        "no_key_order": no_key,
        "no_key_keeps_original": no_key == "1. 甲\n2. 乙\n3. 丙",
        "tail_drop_report": comp.truncated.get("memory"),
        "tail_drop_keeps_top_ranked": comp.budget["memory"]["used"] > 0,
        "switch_default": {
            "CONTEXT_RANK_SORT_ENABLED": settings.CONTEXT_RANK_SORT_ENABLED,
            "CONTEXT_RANK_DECAY_HALF_LIFE_DAYS": settings.CONTEXT_RANK_DECAY_HALF_LIFE_DAYS,
        },
    }


def probe_profile_dimensions() -> dict[str, Any]:
    """(f) 画像维度白名单与维度级优先级（§3.2 / §3.3 profile 行）"""
    from app.api.openllm_gateway import _format_profile_ctx

    payload = {
        "person": {
            "city": "上海" + "甲" * 20,
            "preference": "简洁" + "乙" * 20,
        },
        "business": {
            "company": "OpenBase" + "丙" * 20,
            "scale": "200" + "丁" * 20,
        },
    }
    small = {"person": {"city": "上海", "preference": "简洁"}, "business": {"company": "OpenBase"}}
    default_text = _format_profile_ctx(small)
    with _temp(PROFILE_DIMENSION_LINES_ENABLED=False):
        single_line_text = _format_profile_ctx(small)
    with _temp(PROFILE_DIMENSION_WHITELIST="preference,company"):
        whitelisted = _format_profile_ctx(small)
    with _temp(PROFILE_DIMENSION_WHITELIST="nothing_matches"):
        no_match = _format_profile_ctx(small)
    trimmed_profile = _format_profile_ctx(payload)
    prompt, comp = build_prompt(
        query="问", profile_ctx=trimmed_profile, count_tokens=_chars, budget=_policy()
    )
    return {
        "dimension_lines": default_text,
        "one_line_per_dimension": len([x for x in default_text.splitlines() if x.strip()]) == 5,
        "person_before_business": default_text.index("city") < default_text.index("company"),
        "single_line_fallback": single_line_text,
        "switch_off_single_line": len([x for x in single_line_text.splitlines() if x.strip()]) == 2,
        "whitelist_text": whitelisted,
        "whitelist_keeps_only_listed": "preference" in whitelisted
        and "company" in whitelisted
        and "city" not in whitelisted
        and "scale" not in whitelisted,
        "whitelist_no_match_empty": no_match == "",
        "low_priority_dimension_dropped": "company" not in prompt and "city" in prompt,
        "profile_report": comp.truncated.get("profile"),
        "profile_within_quota": comp.budget["profile"]["used"] <= comp.budget["profile"]["quota"],
    }


def probe_refine_in_metrics() -> dict[str, Any]:
    """(g) `refine` 回执落 `context_metrics`（§3.3 产出物 / §5.8 观测行）"""
    from app.edgerouter.orchestration.context_metrics import ContextReceipt

    memory = "\n".join(["1. " + "甲" * 400, "2. " + "乙" * 400])
    _prompt, comp = build_prompt(
        query="问", memory_ctx=memory, count_tokens=_chars, budget=_policy()
    )
    record = ContextReceipt(request_id="probe-refine", composition=comp).to_record()
    _p2, off_comp = build_prompt(
        query="问", memory_ctx="1. 甲", count_tokens=_chars, budget=BudgetPolicy(enabled=False)
    )
    off_record = ContextReceipt(request_id="probe-refine-off", composition=off_comp).to_record()
    return {
        "refine_in_record": record.get("refine"),
        "refine_field_present": "refine" in record,
        "refine_equals_composition": record.get("refine") == comp.refine,
        "absent_when_disabled": "refine" not in off_record,
        "other_fields_intact": all(
            key in record for key in ("segment_tokens", "budget", "truncated", "contexts_tokens")
        ),
    }


def main() -> int:
    report = {
        "probe": "assembly_rule_tier",
        "design_ref": (
            "方案 §3.2 选择（权重排序 / 画像维度白名单）＋ §3.3 预算（维度级优先级 / refine 落 metrics）"
            "＋ §3.4 规则档（元数据噪声剥离 / 相邻同义合并 / refine 回执）＋ §3.5 稳定引用编号"
        ),
        "(a) 元数据噪声剥离": probe_metadata_noise(),
        "(b) 相邻同义合并": probe_adjacent_merge(),
        "(c) refine 回执": probe_refine_receipt(),
        "(d) 稳定引用编号": probe_ref_numbers(),
        "(e) 权重排序": probe_rank_selection(),
        "(f) 画像维度优先级": probe_profile_dimensions(),
        "(g) refine 落 context_metrics": probe_refine_in_metrics(),
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assembly_rule_tier_probe-result.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n结果已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
