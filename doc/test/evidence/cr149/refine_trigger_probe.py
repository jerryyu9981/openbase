"""方案 §5.2 精炼触发条件 ＋ §5.3 输出护栏 —— 运行态证据探针

**审计背景**：全仓检索 `should_refine` / `CONTEXT_REFINE` / `validate_refine` **零命中**
⇒ §5.2 触发条件表与 §5.3 护栏**未实施**；后果是第三批接模型档时**缺少「何时该调模型」**
与「模型输出是否可用」两道闸门（§2 原则 3「精炼按需触发、有硬预算、可降级」）。
本探针验证 2026-09-27 落地的**判定部分**（纯函数、进程内可判）：

  - §5.2 行 1：memory/rag 段 token > 配额 × **1.5**（严格大于 ⇒ 恰为 1.5 倍**不触发**）；
  - §5.2 行 2：单段条目数 > **8**（恰为 8 **不触发**）；
  - §5.2 行 3：段内相似度 > **0.85** 的条目占比 > **30%**（4 条中 2 条近重复 ⇒ 50% 触发）；
  - §5.2 行 4：**多源冲突 = 未实施**（需语义判定）⇒ `unimplemented` 显式列出，**不伪实现**；
  - §5.3 护栏：逐条可定位 / 不得引入新数值 / 须编号列表 / 空输出非法 ⇒ 违规即弃；
  - §2 原则 6：判定为**只读观测**，开关两态下注入文本**逐字相同**。

用法：``python doc/test/evidence/cr149/refine_trigger_probe.py``（cwd = OpenLLM/backend）
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from typing import Any

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration import refine as refine_module  # noqa: E402
from app.edgerouter.orchestration.prompt_pipeline import (  # noqa: E402
    BudgetPolicy,
    build_prompt,
)

SOURCES = [
    "项目预算上限为 120 万元，由财务部在 3 月核定。",
    "用户偏好简洁回答，不喜欢冗长解释。",
    "部署环境使用 Docker Compose，端口 8080。",
]


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


def _policy() -> BudgetPolicy:
    return BudgetPolicy(
        enabled=True,
        window_tokens=1000,
        output_reserve_tokens=0,
        quota_ratios={
            "system": 0.05,
            "profile": 0.10,
            "memory": 0.10,
            "rag": 0.10,
            "history": 0.10,
        },
        single_item_max_tokens=0,
    )


def _items(*bodies: str) -> str:
    return "\n".join(f"{index}. {body}" for index, body in enumerate(bodies, start=1))


def _trigger(segments: dict[str, str]) -> dict[str, Any]:
    return refine_module.refine_triggers(segments, policy=_policy(), count_tokens=_chars)


def probe_triggers() -> dict[str, Any]:
    return {
        "row1_over_quota": {
            "memory_160_over_100": _trigger({"memory": _items("甲" * 157)}),
            "exactly_1_5x_150_over_100": _trigger({"memory": _items("甲" * 147)}),
            "history_over_quota_ignored": _trigger({"history": _items("历" * 300)}),
        },
        "row2_item_count": {
            "nine_items": _trigger({"memory": _items(*[f"条目{index}" for index in range(9)])}),
            "eight_items": _trigger({"memory": _items(*[f"条目{index}" for index in range(8)])}),
        },
        "row3_duplication": {
            "two_of_four_similar": _trigger(
                {
                    "memory": _items(
                        "用户偏好简洁回答",
                        "用户偏好简洁回答风格",
                        "项目用 Python",
                        "部署用 Docker",
                    )
                }
            ),
            "two_of_eight_similar": _trigger(
                {
                    "memory": _items(
                        "用户偏好简洁回答",
                        "用户偏好简洁回答风格",
                        *[f"第{index}条截然不同的内容" for index in range(6)],
                    )
                }
            ),
        },
        "row4_multi_source_conflict": {
            "unimplemented_marker": _trigger(
                {"memory": _items("预算代号 A1"), "rag": _items("预算代号 A2")}
            ),
            "reason_vocabulary": list(refine_module.TRIGGER_REASONS),
            "no_conflict_reason_faked": not any(
                "conflict" in reason for reason in refine_module.TRIGGER_REASONS
            ),
        },
    }


def probe_guard() -> dict[str, Any]:
    valid = refine_module.validate_refine_output(
        [
            "1. 项目预算上限为 120 万元，由财务部在 3 月核定。",
            "2. 用户偏好简洁回答，不喜欢冗长解释。",
        ],
        sources=SOURCES,
    )
    return {
        "verbatim_extraction": valid,
        "rewrite_unlocatable": refine_module.validate_refine_output(
            ["1. 项目预算由财务部每月复核一次。"], sources=SOURCES
        ),
        "new_number": refine_module.validate_refine_output(
            ["1. 部署环境使用 Docker Compose，端口 9090。"], sources=SOURCES
        ),
        "existing_number": refine_module.validate_refine_output(
            ["1. 部署环境使用 Docker Compose，端口 8080。"], sources=SOURCES
        ),
        "empty_output": refine_module.validate_refine_output([], sources=SOURCES),
        "not_numbered": refine_module.validate_refine_output(
            ["项目预算上限为 120 万元，由财务部在 3 月核定。"], sources=SOURCES
        ),
    }


def probe_observation_separation() -> dict[str, Any]:
    """§2 原则 6：触发判定只读，开关两态注入文本逐字相同"""
    memory = _items("甲" * 200)
    with _temp(CONTEXT_REFINE_TRIGGER_ENABLED=False):
        prompt_off, comp_off = build_prompt(
            query="问", memory_ctx=memory, count_tokens=_chars, budget=_policy()
        )
    with _temp(CONTEXT_REFINE_TRIGGER_ENABLED=True):
        prompt_on, comp_on = build_prompt(
            query="问", memory_ctx=memory, count_tokens=_chars, budget=_policy()
        )
    return {
        "prompt_identical": prompt_on == prompt_off,
        "tokens_identical": comp_on.prompt_total_tokens == comp_off.prompt_total_tokens,
        "trigger_off_empty": comp_off.refine_trigger == {},
        "trigger_on": comp_on.refine_trigger,
        "default_switch": settings.CONTEXT_REFINE_TRIGGER_ENABLED,
        "thresholds": {
            "over_quota_ratio": settings.CONTEXT_REFINE_OVER_QUOTA_RATIO,
            "max_items": settings.CONTEXT_REFINE_MAX_ITEMS,
            "dup_similarity": settings.CONTEXT_REFINE_DUP_SIMILARITY,
            "dup_share": settings.CONTEXT_REFINE_DUP_SHARE,
        },
    }


def main() -> int:
    report = {
        "probe": "refine_trigger",
        "design_ref": "方案 §5.2 触发条件（行 1~3 已实施 / 行 4 未实施）＋ §5.3 输出护栏（判定部分）",
        "triggers": probe_triggers(),
        "guard": probe_guard(),
        "observation_separation": probe_observation_separation(),
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "refine_trigger_probe-result.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n结果已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
