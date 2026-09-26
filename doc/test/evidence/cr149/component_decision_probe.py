"""CR-149 第二批运行态证据：组件决策三余项（方案 §4.2）

在**真实组件路由器 / 网关构造入口**下取证：

  1. **阈值与单次命中语义对齐**：同一批查询在「旧语义（单次命中 0.8）」与
     「对齐语义（0.86）」下的 `decide_sync` 结果对比，以及 `candidate_report`
     的 `qualified` 变化 —— 证明「达标判定」与「最终决策」不再隐性分叉；
  2. **规则集可配置**：把 `COMPONENT_ROUTER_RULES_PATH` 指向临时规则文件后，
     自定义关键词即可路由（免改代码）；
  3. **LLM 兜底接线**：开关关闭 ⇒ 不注入分类器（零副作用）；开启 ⇒ 注入带
     300ms 预算的分类器，超时/非法输出一律回落规则引擎。

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.api import openllm_gateway as gateway  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.component_router import ComponentRouter  # noqa: E402

# 覆盖三类代表场景：单次记忆命中 / 单次知识命中 / 复合意图（R005）
CASES = {
    "single_memory_hit": ("我的资料在哪里", {}),
    "single_rag_hit": ("帮我查一下产品手册", {"kb_id": "kb-1"}),
    "composite_intent": ("接着上次说的，帮我看下知识库里的文档", {"kb_id": "kb-1"}),
    "two_hits": ("我的偏好，我的习惯", {}),
    "no_candidate": ("请说明一下这个系统在大规模并发场景下的表现如何", {}),
}

RULES_FILE = {
    "rules": {
        "X001": {
            "type": "memory_keyword",
            "keywords": ["专有词"],
            "decision": {"need_memory": True, "need_rag": False},
        }
    }
}


class _IdentityStub:
    user_id = "u-probe"


def _compare(query: str, options: dict) -> dict:
    legacy = ComponentRouter(single_hit_confidence=0.8, composite_confidence=0.8)
    aligned = ComponentRouter()
    legacy_decision = legacy.decide_sync(query, options)
    aligned_decision = aligned.decide_sync(query, options)
    return {
        "legacy_0.8_decides": legacy_decision is not None,
        "aligned_0.86_decides": aligned_decision is not None,
        "aligned_decision": aligned_decision,
        "legacy_qualified_flags": sorted(
            {entry["rule_id"]: entry["qualified"] for entry in legacy.candidate_report(query, options)}.items()
        ),
        "aligned_qualified_flags": sorted(
            {entry["rule_id"]: entry["qualified"] for entry in aligned.candidate_report(query, options)}.items()
        ),
    }


async def _probe_classification_cache() -> dict:
    """④ 兜底分类缓存（方案 §5.8）：同题只付一次、异题各付一次、容量 0 逐字回退"""
    from app.edgerouter.orchestration.component_router import (
        clear_llm_decision_cache,
        llm_decision_cache_size,
    )

    class _CountingClassifier:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def __call__(self, query: str, _prompt: str) -> str:
            self.calls.append(query)
            return '{"need_memory": true, "need_rag": false, "reason": "分类器判定"}'

    unmatched = CASES["no_candidate"][0]
    other = "顺便说一下那边的进展如何"
    clear_llm_decision_cache()
    counter = _CountingClassifier()
    router = ComponentRouter(llm_classifier=counter)
    first = await router.decide(unmatched)
    second = await router.decide(unmatched)
    same_query_calls = len(counter.calls)
    await router.decide(other)
    distinct_calls = len(counter.calls)
    entries_after = llm_decision_cache_size()

    clear_llm_decision_cache()
    off_counter = _CountingClassifier()
    off_router = ComponentRouter(llm_classifier=off_counter, llm_cache_size=0)
    await off_router.decide(unmatched)
    await off_router.decide(unmatched)
    capacity_zero_calls = len(off_counter.calls)
    clear_llm_decision_cache()

    return {
        "same_query_calls": same_query_calls,
        "same_query_hits_cache": same_query_calls == 1,
        "distinct_query_calls": distinct_calls,
        "distinct_queries_each_pay": distinct_calls == 2,
        "cached_decision_equal": first == second,
        "cache_entries_after_two_distinct": entries_after,
        "capacity_zero_calls": capacity_zero_calls,
        "capacity_zero_disables": capacity_zero_calls == 2,
        "default_capacity": ComponentRouter(llm_classifier=_CountingClassifier()).llm_cache_size,
    }


async def main() -> dict:
    original_rules_path = settings.COMPONENT_ROUTER_RULES_PATH
    original_enabled = settings.COMPONENT_ROUTER_LLM_FALLBACK_ENABLED

    decisions = {name: _compare(query, options) for name, (query, options) in CASES.items()}

    # ② 规则集可配置
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "rules.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(RULES_FILE, handle, ensure_ascii=False)
        settings.COMPONENT_ROUTER_RULES_PATH = path
        configured = ComponentRouter()
        rules_configured = {
            "rules_loaded": sorted(configured.rules),
            "custom_keyword_routes": configured.decide_sync("这里有个专有词"),
        }
        settings.COMPONENT_ROUTER_RULES_PATH = "/definitely/not/exists.json"
        rules_configured["invalid_path_falls_back"] = sorted(ComponentRouter().rules)

    settings.COMPONENT_ROUTER_RULES_PATH = original_rules_path

    # ③ LLM 兜底接线
    settings.COMPONENT_ROUTER_LLM_FALLBACK_ENABLED = False
    off_router = gateway._build_component_router(db=object(), identity=_IdentityStub())
    settings.COMPONENT_ROUTER_LLM_FALLBACK_ENABLED = True

    async def _timeout_call_llm(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise TimeoutError("classification budget exceeded")

    original_call_llm = gateway._call_llm
    gateway._resolve_model_code = lambda _comp: "probe-model"  # type: ignore[assignment]
    gateway._call_llm = _timeout_call_llm  # type: ignore[assignment]
    on_router = gateway._build_component_router(db=object(), identity=_IdentityStub())
    timeout_decision = await on_router.decide(CASES["no_candidate"][0])
    gateway._call_llm = original_call_llm  # type: ignore[assignment]
    settings.COMPONENT_ROUTER_LLM_FALLBACK_ENABLED = original_enabled

    # ④ 兜底分类缓存（方案 §5.8「路由分类按 query 归一化缓存」，v1.16.0 接线）
    cache_report = await _probe_classification_cache()

    return {
        "config": {
            "single_hit_confidence": settings.COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE,
            "composite_confidence": settings.COMPONENT_ROUTER_COMPOSITE_CONFIDENCE,
            "rules_path_default": original_rules_path,
            "llm_fallback_default": original_enabled,
            "llm_timeout_seconds": settings.COMPONENT_ROUTER_LLM_TIMEOUT_SECONDS,
            "llm_cache_size_default": settings.COMPONENT_ROUTER_LLM_CACHE_SIZE,
        },
        "threshold_alignment": decisions,
        "rules_configurable": rules_configured,
        "llm_fallback": {
            "switch_off_classifier_injected": off_router._llm_classifier is not None,
            "switch_on_classifier_injected": on_router._llm_classifier is not None,
            "timeout_decision": timeout_decision,
        },
        "classification_cache": cache_report,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), ensure_ascii=False, indent=2))
