"""CR-149 第一批运行态探针（预算裁剪 / system 段 / 重排参数 / 路由候选）

在**真实配置与真实 token 计数器**下验证第一批改动（非 monkeypatch）：
  1. `CONTEXT_BUDGET_ENABLED=true` → 记忆段按配额整条裁剪，`budget`/`truncated` 回执齐备；
  2. `CONTEXT_SYSTEM_PROMPT_ENABLED=true` → system 段注入统一指令；
  3. `_rag_search_params` 在开关开启时透传 rerank/threshold；
  4. `ComponentRouter.candidate_report` 给出候选明细（含 qualified 标记）。

用法（在 OpenLLM/backend 下）::

    $env:CONTEXT_BUDGET_ENABLED='true'; $env:CONTEXT_SYSTEM_PROMPT_ENABLED='true'
    $env:RAG_RERANK_ENABLED='true'; $env:RAG_SCORE_THRESHOLD='0.15'
    python <此脚本>
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.api.openllm_gateway import _rag_search_params  # noqa: E402
from app.edgerouter.orchestration.component_router import ComponentRouter  # noqa: E402
from app.edgerouter.orchestration.prompt_pipeline import (  # noqa: E402
    build_prompt,
    default_token_counter,
)

# 构造超配额记忆段：12 条 × 约 120 字，总 token 远超 memory 配额
MEMORY_ITEMS = [
    f"{index + 1}. 记忆条目{index + 1}：会话编排前置与回写闭环的判据之一是 "
    + "上下文装配分段计量与归因可追溯；" * 2
    for index in range(12)
]
MEMORY_CTX = "\n".join(MEMORY_ITEMS)
RAG_CTX = "1. 知识库条目：知识库样本标识 AGENT-CTX-KB-20260926，预算代号 CONTEXT-BUDGET-4096。"
QUERY = "请结合我的偏好和知识库资料，说明会话编排的前置与回写闭环？"


def main() -> int:
    counter = default_token_counter()
    prompt, composition = build_prompt(
        query=QUERY,
        memory_ctx=MEMORY_CTX,
        rag_ctx=RAG_CTX,
        profile_ctx="person.tone: 简洁\nbusiness.topics: 会话编排",
        count_tokens=counter,
    )
    print(json.dumps({
        "switch_budget": os.environ.get("CONTEXT_BUDGET_ENABLED"),
        "switch_system": os.environ.get("CONTEXT_SYSTEM_PROMPT_ENABLED"),
        "prompt_total_tokens": composition.prompt_total_tokens,
        "segment_tokens": composition.segment_tokens,
        "contexts_tokens": composition.contexts_tokens,
        "budget": composition.budget,
        "truncated": composition.truncated,
        "memory_items_in_prompt": prompt.count("记忆条目"),
        "rag_search_params": _rag_search_params({}),
        "candidates": ComponentRouter().candidate_report(QUERY, {"kb_id": "kb-1"}),
        "system_injected": prompt.startswith("你是 OpenBase 的智能助手"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
