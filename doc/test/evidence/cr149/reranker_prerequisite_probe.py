"""题 10 探针：**判别式重排器前置判定**（收口方案 §8 收口判据 #4 —— B 类「明确判定」）

**判据原文（收口方案 §8 #4）**：「B 类前置给出**明确判定** —— 达标 ⇒ 实施；**不达标 ⇒ 如实登记并维持
OpenRAG 服务端 rerank**」。技术方案 §5.5 明确重排器为 **0.6B 判别式模型**、§5.8 明确**在线预算 ≤100ms**。

**本探针做两件事**（**判定规则与事实采集分离**，使判定规则本身可被验证）：

  1. **判定规则**（纯函数 `decide_reranker_prerequisite`）—— 由「**模型是否在位**」「**是否已实测 P95**」
     「**服务端 rerank 是否启用**」三事实推出结论；**四分支**（前置未满足 / 未实测 / 达标 / 不达标）**逐一自检**，
     确保判定**不是「恒判不达标」的空转规则**。
  2. **事实采集**（本机真实环境）—— 运行库（`sentence_transformers` / `transformers`）是否可用、
     本地是否已有**判别式（cross-encoder 类）重排器模型**缓存、服务端 rerank 配置是否启用。

**本探针的诚实边界**：**不伪造任何实测数值** —— 本地无模型 ⇒ `measured_p95_ms = None`（**如实记为
「未实测」**，并把「为何不可测」写成可复现的事实，而非断言）。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())

#: 技术方案 §5.8：重排**在线档**预算（ms）—— 判据引用值，禁本地改写
REFERENCE_ONLINE_BUDGET_MS = 100.0

#: 判别式（cross-encoder 类）重排器模型**名称特征**（保守口径：命中即视为「可能是重排器」，仍须人工确认）
RERANKER_NAME_RE = re.compile(r"reranker|cross[-_]?encoder|bge-reranker|gte-reranker|mxbai-rerank", re.I)


def decide_reranker_prerequisite(
    *,
    model_available: bool,
    measured_p95_ms: float | None,
    online_budget_ms: float,
    server_rerank_enabled: bool,
) -> dict:
    """**纯函数**：判别式重排器前置判定（DoD #4）

    **四分支**（**不得**退化为「恒判不达标」）：

      * `prerequisite_unmet` —— **模型不在位** ⇒ 前置未满足 ⇒ **不实施**，**维持服务端 rerank**；
      * `measurement_missing` —— 模型在位但**未实测 P95** ⇒ **禁「未测先上」** ⇒ 不实施、维持服务端；
      * `qualified` —— 实测 P95 ≤ 在线预算 ⇒ **达标** ⇒ 可实施（并可撤服务端 rerank）；
      * `not_qualified` —— 实测 P95 > 在线预算 ⇒ **不达标** ⇒ 不实施、维持服务端。

    `server_rerank_enabled=False` 且最终不实施 ⇒ 追加 `action_required`（**服务端 rerank 应启用**，
    否则「维持服务端 rerank」实为**空话**）。
    """
    if not model_available:
        verdict, implement = "prerequisite_unmet", False
        reason = "本地无可用的判别式（cross-encoder 类）重排器模型 / 运行库 ⇒ **前置未满足**"
    elif measured_p95_ms is None:
        verdict, implement = "measurement_missing", False
        reason = "模型在位但**未实测 P95** ⇒ **不得未测先上**（§5.6 门槛须以实测为据）"
    elif measured_p95_ms <= online_budget_ms:
        verdict, implement = "qualified", True
        reason = (
            f"实测 P95 {measured_p95_ms}ms ≤ 在线预算 {online_budget_ms}ms ⇒ **达标**，可实施"
        )
    else:
        verdict, implement = "not_qualified", False
        reason = (
            f"实测 P95 {measured_p95_ms}ms > 在线预算 {online_budget_ms}ms ⇒ **不达标**，维持服务端 rerank"
        )

    outcome = {
        "verdict": verdict,
        "implement_reranker": implement,
        "keep_server_rerank": not implement,
        "reason": reason,
    }
    if not implement and not server_rerank_enabled:
        outcome["action_required"] = (
            "服务端 rerank 当前**未启用** ⇒ 须启用 `RAG_RERANK_ENABLED=true` 且 "
            "`RAG_SCORE_THRESHOLD>0`（否则「维持服务端 rerank」为空话）"
        )
    return outcome


def _importable(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _hf_cache_models() -> list[str]:
    """本地 HF 缓存中的模型目录名（无缓存 ⇒ 空列表）"""
    hub = os.path.expanduser(os.path.join("~", ".cache", "huggingface", "hub"))
    if not os.path.isdir(hub):
        return []
    return sorted(
        name
        for name in os.listdir(hub)
        if name.startswith("models--") and os.path.isdir(os.path.join(hub, name))
    )


def collect_facts() -> dict:
    """本机真实事实（**只读**，不做任何安装 / 下载）"""
    runtime = {
        "sentence_transformers": _importable("sentence_transformers"),
        "transformers": _importable("transformers"),
    }
    cached = _hf_cache_models()
    candidates = [name for name in cached if RERANKER_NAME_RE.search(name)]

    try:
        import torch

        gpu_available = bool(torch.cuda.is_available())
        torch_version = getattr(torch, "__version__", "unknown")
    except Exception as exc:  # noqa: BLE001
        gpu_available, torch_version = False, f"unavailable: {type(exc).__name__}"

    from app.core.config import settings

    server_rerank_enabled = bool(
        getattr(settings, "RAG_RERANK_ENABLED", False)
    ) and float(getattr(settings, "RAG_SCORE_THRESHOLD", 0.0) or 0.0) > 0.0

    return {
        "runtime": runtime,
        "runtime_usable_for_reranker": all(runtime.values()),
        "hf_cached_models": cached,
        "reranker_model_candidates": candidates,
        "reranker_model_available": bool(candidates) and all(runtime.values()),
        "gpu_available": gpu_available,
        "torch_version": torch_version,
        "server_rerank_enabled": server_rerank_enabled,
        "server_rerank_config": {
            "RAG_RERANK_ENABLED": getattr(settings, "RAG_RERANK_ENABLED", None),
            "RAG_SCORE_THRESHOLD": getattr(settings, "RAG_SCORE_THRESHOLD", None),
        },
        # **未实测**（本地无模型、无运行库 ⇒ 不可测）—— 如实记为 None，**不伪造数值**
        "measured_p95_ms": None,
        "measurement_note": (
            "本机无判别式重排器模型缓存且 `sentence_transformers` / `transformers` **均未安装** ⇒ "
            "**无法实测**；§5.4 既有复测另证**生成式**模型做重排不可行（4B `select` P95 ≈ 35.7s，"
            "远超 100ms 在线预算），生成式路线不作为判别式替代"
        ),
    }


def _self_check() -> list[dict]:
    """**判定规则自检**：四分支逐一验证（**防「恒判不达标」的空转规则**）"""
    checks: list[dict] = []

    def _case(name: str, *, expect_verdict: str, expect_implement: bool, **kwargs) -> None:
        outcome = decide_reranker_prerequisite(**kwargs)
        ok = (
            outcome["verdict"] == expect_verdict
            and outcome["implement_reranker"] is expect_implement
            and outcome["keep_server_rerank"] is (not expect_implement)
        )
        checks.append(
            {"case": name, "expect": expect_verdict, "got": outcome["verdict"], "ok": ok}
        )

    _case(
        "① 模型不在位 ⇒ 前置未满足（不实施、维持服务端）",
        expect_verdict="prerequisite_unmet",
        expect_implement=False,
        model_available=False,
        measured_p95_ms=None,
        online_budget_ms=REFERENCE_ONLINE_BUDGET_MS,
        server_rerank_enabled=True,
    )
    _case(
        "② 模型在位但未实测 ⇒ 禁未测先上",
        expect_verdict="measurement_missing",
        expect_implement=False,
        model_available=True,
        measured_p95_ms=None,
        online_budget_ms=REFERENCE_ONLINE_BUDGET_MS,
        server_rerank_enabled=True,
    )
    _case(
        "③ 实测 P95 ≤ 预算 ⇒ **达标**（可实施）—— 证明规则非「恒不达标」",
        expect_verdict="qualified",
        expect_implement=True,
        model_available=True,
        measured_p95_ms=88.0,
        online_budget_ms=REFERENCE_ONLINE_BUDGET_MS,
        server_rerank_enabled=True,
    )
    _case(
        "④ 实测 P95 > 预算 ⇒ 不达标",
        expect_verdict="not_qualified",
        expect_implement=False,
        model_available=True,
        measured_p95_ms=35729.9,
        online_budget_ms=REFERENCE_ONLINE_BUDGET_MS,
        server_rerank_enabled=True,
    )

    # ⑤ 不实施 ＋ 服务端 rerank 未启用 ⇒ 须给出 action_required（防「维持」成空话）
    outcome = decide_reranker_prerequisite(
        model_available=False,
        measured_p95_ms=None,
        online_budget_ms=REFERENCE_ONLINE_BUDGET_MS,
        server_rerank_enabled=False,
    )
    checks.append(
        {
            "case": "⑤ 不实施且服务端未启用 ⇒ 须 action_required",
            "expect": "action_required 存在",
            "got": "present" if outcome.get("action_required") else "missing",
            "ok": bool(outcome.get("action_required")),
        }
    )
    return checks


def main() -> int:
    facts = collect_facts()
    decision = decide_reranker_prerequisite(
        model_available=facts["reranker_model_available"],
        measured_p95_ms=facts["measured_p95_ms"],
        online_budget_ms=REFERENCE_ONLINE_BUDGET_MS,
        server_rerank_enabled=facts["server_rerank_enabled"],
    )
    self_checks = _self_check()
    failed = [item for item in self_checks if not item["ok"]]

    payload = {
        "probe": "reranker_prerequisite",
        "criterion": "收口方案 §8 收口判据 #4（B 类「明确判定」）",
        "facts": facts,
        "decision": decision,
        "self_check": {
            "cases": self_checks,
            "failed": [item["case"] for item in failed],
            "verdict": "PASS" if not failed else "FAIL",
        },
    }
    payload["summary"] = {
        "verdict": decision["verdict"],
        "verdict_label": {
            "prerequisite_unmet": "**前置未满足 ⇒ 不实施判别式重排器，维持 OpenRAG 服务端 rerank**",
            "measurement_missing": "模型在位但未实测 ⇒ 暂不实施（禁未测先上）",
            "qualified": "**达标 ⇒ 可实施判别式重排器**",
            "not_qualified": "**不达标 ⇒ 不实施，维持服务端 rerank**",
        }[decision["verdict"]],
        "self_check": payload["self_check"]["verdict"],
    }

    if "--json" in sys.argv:
        target = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "reranker_prerequisite_probe-result.json",
        )
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"已落盘：{target}")

    print("== 事实（本机只读） ==")
    print(f"  运行库 sentence_transformers={facts['runtime']['sentence_transformers']} "
          f"transformers={facts['runtime']['transformers']}")
    print(f"  HF 缓存模型={facts['hf_cached_models']} 判别式重排器候选={facts['reranker_model_candidates']}")
    print(f"  GPU 可用={facts['gpu_available']}（torch {facts['torch_version']}）")
    print(f"  服务端 rerank 已启用={facts['server_rerank_enabled']} "
          f"（{facts['server_rerank_config']}）")
    print(f"  实测 P95={facts['measured_p95_ms']}（**未实测**：{facts['measurement_note'][:60]}…）")
    print("\n== 判定（DoD #4） ==")
    print(f"  verdict={decision['verdict']} implement={decision['implement_reranker']} "
          f"keep_server_rerank={decision['keep_server_rerank']}")
    print(f"  理由：{decision['reason']}")
    if decision.get("action_required"):
        print(f"  **须动作**：{decision['action_required']}")
    print("\n== 判定规则自检 ==")
    for item in self_checks:
        print(f"  {'OK ' if item['ok'] else 'BAD'} {item['case']} ⇒ {item['got']}")
    print(
        f"\n判定: {decision['verdict']}｜自检: {payload['self_check']['verdict']}"
        f"（{len(self_checks)} 例 / 不符 {len(failed)}）"
    )
    print(f"结论：{payload['summary']['verdict_label']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
