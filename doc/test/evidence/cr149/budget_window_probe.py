"""预算窗口基准探针（CR-149 §9 问题 3「预算目标」裁定的取证与配额标定）

**用途**：把裁定口径落到**可核对数字**上 —— 对若干代表模型打印
「有效窗口 / 来源 / 可分配 token / 各段绝对配额 / 历史段预算」，并给出
**4096（知识库样本宣称） vs 部署生效窗口**两档的**配额对照**，供运维核对与容量规划。

**裁定口径（2026-09-27）**：有效窗口 ＝ `min(模型声明窗口, 部署生效窗口)`；
未识别模型 ⇒ **部署窗口兜底**（**不取** 128000 架构上限）。

用法（cwd = OpenLLM/backend）：

    python <此脚本> [--deployment 8192] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.services.context_manager import resolve_effective_window_tokens  # noqa: E402

MODELS: tuple[tuple[str, str], ...] = (
    ("qwen3:0.6b", "本工作区 deployed（`DEFAULT_LLM_MODEL`）"),
    ("qwen3:32b", "本工作区可选（更大规格）"),
    ("llama-2-7b", "声明窗口小于部署窗口（4096）"),
    ("llama-3-8b", "声明窗口等于部署窗口（8192）"),
    ("gpt-4-turbo", "声明窗口大于部署窗口（128000）"),
    ("totally-unknown-model", "完全未识别（模型表零命中）"),
)

SEGMENTS = ("system", "profile", "memory", "rag", "history")


def _quota_table(deployment_window: int, model: str | None, reserve: int, ratios: dict) -> dict:
    window, source = resolve_effective_window_tokens(
        model, deployment_window=deployment_window
    )
    available = max(0, window - reserve)
    return {
        "model": model,
        "effective_window": window,
        "window_source": source,
        "available_tokens": available,
        "quotas": {segment: int(available * float(ratios.get(segment, 0.0))) for segment in SEGMENTS},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reserve = int(getattr(settings, "CONTEXT_OUTPUT_RESERVE_TOKENS", 1024) or 0)
    ratios = {
        "system": getattr(settings, "CONTEXT_QUOTA_SYSTEM_RATIO", 0.05),
        "profile": getattr(settings, "CONTEXT_QUOTA_PROFILE_RATIO", 0.05),
        "memory": getattr(settings, "CONTEXT_QUOTA_MEMORY_RATIO", 0.28),
        "rag": getattr(settings, "CONTEXT_QUOTA_RAG_RATIO", 0.37),
        "history": getattr(settings, "CONTEXT_QUOTA_HISTORY_RATIO", 0.19),
    }
    deployment = int(
        args.deployment
        or getattr(settings, "CONTEXT_MODEL_WINDOW_TOKENS", 8192)
        or 8192
    )

    current = [_quota_table(deployment, model, reserve, ratios) for model, _note in MODELS]
    # **裁定对照**：若沿用知识库样本宣称的 4096 会得到什么配额（用于说明「为何不取 4096」）
    sample = _quota_table(4096, "qwen3:0.6b", reserve, ratios)
    # **未采纳的架构上限口径**：若按模型表 default=128000（仅作对照，非裁定口径）
    architecture = _quota_table(128000, "totally-unknown-model", reserve, ratios)

    report = {
        "probe": "budget_window_basis",
        "ruling": "§9 问题 3：按真实窗口 = min(模型声明窗口, 部署生效窗口)；未识别 ⇒ 部署兜底",
        "deployment_window": deployment,
        "output_reserve_tokens": reserve,
        "quota_ratios": ratios,
        "current_ruling": current,
        "comparison_kb_sample_4096": sample,
        "comparison_architecture_cap_128000": architecture,
        "history_safety_margin": 0.2,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "budget_window_probe-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
