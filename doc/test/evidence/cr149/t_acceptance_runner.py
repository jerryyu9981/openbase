"""CR-149 §7 验收判据执行器（T1~T12）

**用途**：把《OpenBase-上下文精装配与组件通道优化技术方案》§7 的 T1~T12 判据做成
**一键可复跑**的判定器 —— 人工批准开关开启值后，只需运行本脚本即可拿到逐条
`PASS / FAIL / SKIP / BLOCKED` 与**原始测量数据**（不依赖人工肉眼比对）。

**设计约束（重要）**：

* **不改生产配置**：脚本只**读取** `settings` 的当前值；需要开关开启才能判定的判据
  （T1/T2/T3/T8/T9），若开关为关则返回 `SKIP` 并给出**需要置哪些键**；
  `--simulate` 模式会在**本进程内**临时置位（退出前恢复），用于证明"开启后即达标"，
  **不写任何配置文件、不影响运行中的服务**；
* **可判定性分级**：`SKIP`（开关未开）≠ `FAIL`（能力不达标）；`BLOCKED` 表示
  **环境/前置条件缺失**（如 T4 需要运行态故障注入），
  也**不计入失败**，但会在报告里显式列出，避免"没做"被误读成"通过"；
* **分段判定（T5，v1.18.0）**：T5 拆为两段 —— ① **网关决策闸门**（开关
  `WRITEBACK_DECISION_ENABLED`，默认关闭）＝ `SKIP` 口径同前；② **执行层价值闸门**
  （**无开关、恒生效**）＝ **进程内恒可判**，故 T5 不再整条 `SKIP`：段② 不达标即 `FAIL`；
* **判据与既有护栏的关系**：T1/T2/T5/T7/T8/T9 在 `tests/unit` 已有细粒度护栏；
  本执行器是**跨判据的验收汇总**（含数值测量），并非替代单测。

用法（在 OpenLLM/backend 下）::

    python <此脚本>                    # 按当前配置判定
    python <此脚本> --simulate         # 临时置位开关，判定"开启后是否达标"
    python <此脚本> --json out.json    # 同时落盘完整报告

退出码：`0` = 无 FAIL（允许 SKIP/BLOCKED）；`1` = 存在 FAIL。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class Verdict:
    """单条判据结论"""

    criterion: str
    title: str
    status: str
    requires: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------- 工具

def _char_counter(text: str) -> int:
    """1 字符 = 1 token 的确定性计数器（与既有单测口径一致，便于断言）"""
    return len(text or "")


def _float_or_none(value: Any) -> float | None:
    """宽松取浮点：`None` / 不可解析一律返回 `None`（判据用，不抛异常）"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _settings_snapshot(keys: list[str]) -> dict[str, Any]:
    from app.core.config import settings

    return {key: getattr(settings, key, None) for key in keys}


def _switch_off_verdict(
    criterion: str, title: str, keys: list[str], detail: dict[str, Any] | None = None
) -> Verdict:
    state = _settings_snapshot(keys)
    return Verdict(
        criterion=criterion,
        title=title,
        status=STATUS_SKIP,
        requires=[f"{key}={state[key]}" for key in keys],
        detail=detail or {},
        reason="所需开关未开启：开启后复跑本判据（--simulate 可先行验证开启态）",
    )


@contextmanager
def _temporary_settings(**overrides: Any):
    """临时置位开关（退出即恢复；不触碰配置文件、不影响运行中服务）"""
    from app.core.config import settings

    previous = {key: getattr(settings, key, None) for key in overrides}
    for key, value in overrides.items():
        setattr(settings, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            setattr(settings, key, value)


def _is_on(key: str) -> bool:
    from app.core.config import settings

    return bool(getattr(settings, key, False))


# ---------------------------------------------------------------- T1 / T2 预算与裁剪

_BUDGET_WINDOW = 1200
_BUDGET_RESERVE = 200


def _build_budget_prompt(*, item_chars: int, items: int) -> tuple[str, Any, Any]:
    """构造一个"素材明显超配额"的装配场景（真实 `build_prompt`，非替身）"""
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    policy = BudgetPolicy(
        enabled=True,
        window_tokens=_BUDGET_WINDOW,
        output_reserve_tokens=_BUDGET_RESERVE,
    )
    memory_ctx = "\n".join(
        f"{index}. " + "记" * item_chars for index in range(1, items + 1)
    )
    rag_ctx = "\n".join(
        f"{index}. " + "知" * item_chars for index in range(1, items + 1)
    )
    prompt, composition = build_prompt(
        query="请结合我的记忆与知识库回答",
        memory_ctx=memory_ctx,
        rag_ctx=rag_ctx,
        profile_ctx="画像：偏好简洁",
        history_ctx="\n".join(
            f"{index}. " + "史" * item_chars for index in range(1, items + 1)
        ),
        count_tokens=_char_counter,
        budget=policy,
    )
    return prompt, composition, policy


def _build_filled_prompt() -> tuple[str, Any, Any]:
    """构造「各段**填满配额**」的最坏场景（真实 `build_prompt`）

    T1 的关键是**结构性**保证：若配额比例之和为 1.00，则各段满额时
    `prompt_total_tokens = available + 查询 + 模板开销 > available`。
    故 T1 必须用**能填满配额**的素材（单条尺寸按各段配额定制），否则
    条目粒度会留下偶然空隙、把结构性溢出掩盖成"通过"。
    """
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    policy = BudgetPolicy(
        enabled=True,
        window_tokens=_BUDGET_WINDOW,
        output_reserve_tokens=_BUDGET_RESERVE,
    )

    def _fill(segment: str, char: str) -> str:
        quota = policy.quota(segment)
        return f"1. {char * max(1, quota - 3)}"  # 编号前缀 `1. ` 占 3 字符

    prompt, composition = build_prompt(
        query="请结合我的记忆与知识库回答",
        system_prompt="系统指令",
        memory_ctx=_fill("memory", "记"),
        rag_ctx=_fill("rag", "知"),
        profile_ctx=_fill("profile", "像"),
        history_ctx=_fill("history", "史"),
        count_tokens=_char_counter,
        budget=policy,
    )
    return prompt, composition, policy


def check_t1() -> Verdict:
    """T1：各段 used ≤ quota，且 prompt_total_tokens 在窗口（扣输出预留）内"""
    title = "预算：各段 used ≤ quota；prompt 总长不超窗口扣减输出预留"
    keys = ["CONTEXT_BUDGET_ENABLED"]
    from app.core.config import settings
    from app.edgerouter.orchestration.prompt_pipeline import QUOTA_HEADROOM_CEILING

    if not _is_on("CONTEXT_BUDGET_ENABLED"):
        return _switch_off_verdict("T1", title, keys)

    _prompt, composition, policy = _build_filled_prompt()
    window = int(getattr(settings, "CONTEXT_MODEL_WINDOW_TOKENS", 0) or 0)
    effective_window = policy.window_tokens
    available = policy.available_tokens
    ratio_sum = sum(
        float(value or 0.0) for value in policy.quota_ratios.values()
    )
    segments_over = {
        name: values
        for name, values in composition.budget.items()
        if values["quota"] > 0 and values["used"] > values["quota"]
    }
    sum_used = sum(values["used"] for values in composition.budget.values())
    detail = {
        "window_tokens": effective_window,
        "output_reserve_tokens": policy.output_reserve_tokens,
        "available_tokens": available,
        "quota_ratio_sum": round(ratio_sum, 4),
        "quota_headroom_ceiling": QUOTA_HEADROOM_CEILING,
        "sum_segment_used": sum_used,
        "prompt_total_tokens": composition.prompt_total_tokens,
        "headroom_tokens": available - composition.prompt_total_tokens,
        "segment_budget": composition.budget,
        "configured_window_tokens": window,
        "fixture": "filled_quota(worst_case)",
    }
    failures = []
    if ratio_sum > QUOTA_HEADROOM_CEILING:
        failures.append(
            f"配额比例之和 {ratio_sum:.2f} 未留出查询与模板开销余量（须 ≤ {QUOTA_HEADROOM_CEILING}）"
        )
    if segments_over:
        failures.append(f"存在超出配额的段（quota>0）：{list(segments_over)}")
    if composition.prompt_total_tokens > available:
        failures.append(
            "prompt_total_tokens（含查询与模板开销）超过窗口扣减输出预留"
            f"（{composition.prompt_total_tokens} > {available}）"
        )
    return Verdict(
        criterion="T1",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        requires=[f"CONTEXT_BUDGET_ENABLED={_is_on('CONTEXT_BUDGET_ENABLED')}"],
        detail=detail,
        reason="；".join(failures),
    )


def check_t2() -> Verdict:
    """T2：超配额时 truncated 有值、dropped_items > 0，且保留条目非空（归因可用）"""
    title = "裁剪：超配额场景 truncated 有值、dropped_items > 0、保留条目非空"
    keys = ["CONTEXT_BUDGET_ENABLED"]
    if not _is_on("CONTEXT_BUDGET_ENABLED"):
        return _switch_off_verdict("T2", title, keys)

    _prompt, composition, _policy = _build_budget_prompt(item_chars=200, items=6)
    trimmed_with_drops = {
        name: report
        for name, report in composition.truncated.items()
        if report.get("dropped_items", 0) > 0
    }
    kept_non_empty = {
        name: values["used"]
        for name, values in composition.budget.items()
        if name in ("memory", "rag", "history")
    }
    failures = []
    if not trimmed_with_drops:
        failures.append("未观察到任何 dropped_items > 0 的裁剪")
    if not all(used > 0 for used in kept_non_empty.values()):
        failures.append(f"存在保留条目为空的段：{kept_non_empty}")
    return Verdict(
        criterion="T2",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        requires=[f"CONTEXT_BUDGET_ENABLED={_is_on('CONTEXT_BUDGET_ENABLED')}"],
        detail={
            "truncated": composition.truncated,
            "kept_segments_used": kept_non_empty,
            "prompt_total_tokens": composition.prompt_total_tokens,
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T3 重排与阈值

def _run_eval_set() -> dict[str, Any]:
    """调用同目录的评测集执行器（`eval_set_runner.py`；供 T3 段③ 使用）

    以**文件位置**动态加载（不依赖 cwd / `sys.path`）—— 执行器属仓内证据脚本，
    非应用模块。
    """
    import importlib.util

    directory = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(directory, "eval_set_runner.py")
    spec = importlib.util.spec_from_file_location("cr149_eval_set_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载评测集执行器：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate(
        module.load_eval_set(os.path.join(directory, module.EVAL_SET_NAME))
    )


def check_t3() -> Verdict:
    """T3：rerank / score_threshold 透传与低分过滤（**v1.18.1 起分两段**）

    **订正动因（判据保真度缺陷，与 T10 ④ 同源思路）**：本判据原**只**在**条目级**
    传参（`rerank=True` / `score_threshold=0.5`）下断言「透传 ＋ 过滤后条目数下降、
    score 单调」，**全程未触及全局开关**，却在**开关默认关闭**时判 `PASS` —— 而 §7 的
    T3 原文是「**启用 rerank 后** rag 条目的 score 单调性成立、低分条目被
    `score_threshold` 过滤」。即：**判据被实现成了「透传契约」，却挂着「启用后生效」的名字**
    ⇒ 会把「开关关着时透传口径正确」误读为「rerank 已达标可用」。

    现拆两段（与 T4 / T5 / T6 同一写法）：

      ① **口径段（无开关，恒可判）**：条目级参数优先级、`0/负值 ⇒ 不过滤`、
         非法值不抛异常、阈值过滤后条目数下降且 score 单调；
      ② **生效段（需开关）**：`RAG_RERANK_ENABLED=True` 且 `RAG_SCORE_THRESHOLD>0` 时，
         **未传条目参数**的检索其解析结果须确实带上重排与阈值 ⇒ 证明「开关开启即生效」；
         开关未开 ⇒ 本段 `SKIP`（口径同 T5 段①）。**真实检索侧重排效果**（服务端
         rerank 质量）仍属运行态，如实留 `runtime_pending`。
    """
    title = "检索：rerank / score_threshold 透传、低分过滤与「开启即生效」"
    from app.api.openllm_gateway import _rag_search_params
    from app.core.config import settings

    failures: list[str] = []

    # ---- 段① 口径（恒可判） ----
    item_level = _rag_search_params(
        {
            "rerank": True,
            "score_threshold": 0.5,
            "kb_id": "kb-probe",
            "query": "q",
            "top_k": 5,
        }
    )
    global_level = _rag_search_params({"kb_id": "kb-probe", "query": "q"})
    zero_threshold = _rag_search_params({"score_threshold": 0})
    bad_threshold = _rag_search_params({"score_threshold": "not-a-number"})

    scored_items = [
        {"id": "a", "score": 0.91},
        {"id": "b", "score": 0.62},
        {"id": "c", "score": 0.31},
        {"id": "d", "score": 0.05},
    ]
    threshold = float(item_level["score_threshold"] or 0.0)
    filtered = [item for item in scored_items if item["score"] >= threshold]
    scores = [item["score"] for item in filtered]
    monotonic = all(
        left >= right for left, right in zip(scores, scores[1:], strict=False)
    )

    if item_level.get("rerank") is not True:
        failures.append("条目级 rerank 未透传")
    if _float_or_none(item_level.get("score_threshold")) != 0.5:
        failures.append(f"条目级 score_threshold 未透传：{item_level.get('score_threshold')}")
    if len(filtered) >= len(scored_items):
        failures.append("低分条目未被阈值过滤（条目数未下降）")
    if not monotonic:
        failures.append("过滤后 score 非单调递减")
    if zero_threshold.get("score_threshold") is not None:
        failures.append(f"阈值 0 应视为「不过滤」（None）：{zero_threshold!r}")
    if bad_threshold.get("score_threshold") is not None:
        failures.append(f"非法阈值应归零（None）且不抛异常：{bad_threshold!r}")
    if bool(global_level.get("rerank")) != bool(
        getattr(settings, "RAG_RERANK_ENABLED", False)
    ):
        failures.append(
            f"未传条目参数时未按全局配置取 rerank：{global_level!r}"
        )

    # ---- 段② 生效（需开关；关闭时以临时置位证明「开启后即达标」，口径同 T8） ----
    switch_on = bool(getattr(settings, "RAG_RERANK_ENABLED", False))
    threshold_on = float(getattr(settings, "RAG_SCORE_THRESHOLD", 0.0) or 0.0) > 0
    with _temporary_settings(RAG_RERANK_ENABLED=True, RAG_SCORE_THRESHOLD=0.15):
        capability = _rag_search_params({"kb_id": "kb-probe", "query": "q"})
    capability_ok = bool(capability.get("rerank")) and (
        _float_or_none(capability.get("score_threshold")) == 0.15
    )
    if not capability_ok:
        failures.append(f"临时置位后重排/阈值仍未生效：{capability!r}")

    effective_detail: dict[str, Any] = {
        "capability_probe": capability,
        "capability_verified": capability_ok,
        "switch_on_now": switch_on,
        "threshold_on_now": threshold_on,
    }
    if switch_on and threshold_on:
        effective_detail["resolved_without_item_params"] = global_level
        if not global_level.get("rerank"):
            failures.append("开关已开但重排未生效")
        if _float_or_none(global_level.get("score_threshold")) is None:
            failures.append("开关已开但阈值未生效（解析为 None）")

    # ---- 段③ 评测集开 / 关聚合对照（检索侧口径；进程内可复跑） ----
    #      v1.27.0（A5 / 题 9）：把「条目数下降但质量不降」从**运行态待办**推进为
    #      **可复跑判据** —— 以 `cr149-eval-set.json` 的 `assert` 组做开 / 关对照。
    #      **边界（不得混淆）**：本段覆盖**检索侧**聚合口径（相关项保留率 / 噪声剔除率），
    #      **不覆盖** `used_ratio`（依赖 LLM 回答，仍属运行态 ⇒ `evaluation_pending`）。
    eval_result: dict[str, Any] | None = None
    try:
        eval_result = _run_eval_set()
    except Exception as exc:  # noqa: BLE001 - 执行器缺失/异常须落为判据失败，不静默
        failures.append(f"评测集执行器调用失败：{exc}")
    if eval_result is not None:
        if eval_result["verdict"] != "PASS":
            failures.append(f"评测集开/关对照未达标：{eval_result['failures']}")
        _on = eval_result["rerank_on"]["aggregate"]
        _off = eval_result["rerank_off"]["aggregate"]
        if not _on["items"] < _off["items"]:
            failures.append(f"评测集：开态条目数未下降（{_on['items']} vs {_off['items']}）")
        if _on["relevant_recall"] < _off["relevant_recall"]:
            failures.append(
                f"评测集：相关项保留率下降（{_on['relevant_recall']} vs {_off['relevant_recall']}）"
            )
        if not _on["noise_rejection"] > _off["noise_rejection"]:
            failures.append(
                f"评测集：噪声剔除率未上升（{_on['noise_rejection']} vs {_off['noise_rejection']}）"
            )

    detail: dict[str, Any] = {
        "item_level_params": item_level,
        "global_fallback_params": global_level,
        "zero_threshold_params": zero_threshold,
        "bad_threshold_params": bad_threshold,
        "items_before": len(scored_items),
        "items_after": len(filtered),
        "filtered_scores": scores,
        "effective_segment": effective_detail,
        "evaluation_set": eval_result,
        "evaluation_pending": (
            "**仍属运行态的只有 `used_ratio` 部分** —— T3 原文第三条子句中的 "
            "`used_ratio` 是**归因 A** 的指标（`attribution_a()`：回答引用了多少条注入片段），"
            "**取值依赖 LLM 回答内容**，其自身 docstring 明确「只能纵向对比、不得作绝对值"
            "解读」⇒ **不能**用构造回答在进程内做成确定性判据。"
            "**v1.27.0（A5 / 题 9）已收窄该待办**：评测集与执行器**已就位**"
            "（`cr149-eval-set.json` ＋ `eval_set_runner.py`），其**检索侧**聚合对照已由"
            "**本判据段③**成为可复跑判据（条目数下降 / 相关项保留率不降 / 噪声剔除率上升）；"
            "**唯一缺口＝运行态数据**（真实检索端点 ＋ LLM 回答），执行器已在其 "
            "`runtime_pending` 中逐项声明所需输入。"
            "**本判据如实不覆盖 `used_ratio`**，而非以近似断言冒充覆盖。"
        ),
        "runtime_pending": (
            "真实检索侧重排质量（服务端 rerank 排序效果）须在有 OpenRAG 数据面的"
            "运行态复核；本判据只覆盖网关侧口径与「开启即生效」"
        ),
    }

    if failures:
        return Verdict(
            criterion="T3",
            title=title,
            status=STATUS_FAIL,
            requires=[
                f"RAG_RERANK_ENABLED={switch_on}",
                f"RAG_SCORE_THRESHOLD={getattr(settings, 'RAG_SCORE_THRESHOLD', None)}",
            ],
            detail=detail,
            reason="；".join(failures),
        )
    if not (switch_on and threshold_on):
        verdict = _switch_off_verdict(
            "T3",
            title,
            ["RAG_RERANK_ENABLED", "RAG_SCORE_THRESHOLD"],
        )
        verdict.detail = detail
        verdict.reason = (
            "段①口径（无开关，恒可判）已达标：条目级透传优先、阈值 0/非法 ⇒ 不过滤、"
            "过滤后条目数下降且 score 单调；段②能力已用**临时置位**验证通过"
            "（rerank=true / threshold=0.15，进程内退出恢复）—— 待开关开启后复跑即为 PASS"
        )
        return verdict
    return Verdict(
        criterion="T3",
        title=title,
        status=STATUS_PASS,
        requires=[
            f"RAG_RERANK_ENABLED={switch_on}",
            f"RAG_SCORE_THRESHOLD={getattr(settings, 'RAG_SCORE_THRESHOLD', None)}",
        ],
        detail=detail,
    )


# ---------------------------------------------------------------- T4 备通道轨迹

class _T4FailingRagAdapter:
    """桩：RAG 适配器调用即抛「外部检索失败」（非装配缺失 / 非超时）"""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def search(  # noqa: ANN001
        self,
        request_context,
        kb_id=None,
        query="",
        top_k=5,
        rerank=False,
        score_threshold=None,
    ):
        raise self._exc


def _t4_identity():
    from types import SimpleNamespace

    return SimpleNamespace(
        user_id="u-t4",
        organization_id="org-t4",
        role="user",
        external_tenant_id=None,
        external_user_id=None,
        external_org_id=None,
    )


async def _t4_sync_trace(exc: Exception) -> tuple[dict[str, Any], bool]:
    """同步路径：handler **如实上抛**（不再回退）→ 经单一落痕函数并入轨迹

    **W3 / Q11（v1.28.0）**：内置 RAG 自建数据面已废弃 ⇒ 不再注入回退桩、不再覆盖回退开关；
    handler 失败**如实上抛**（由组件层如实降级）。本函数返回 `(轨迹, 是否上抛)`。
    """
    from unittest.mock import patch

    import app.api.openllm_gateway as gateway

    adapter = _T4FailingRagAdapter(exc)
    raised = False
    with patch.object(gateway, "_get_component_adapters", return_value=(None, adapter)):
        handlers, _errors, shared = gateway._build_component_handlers(
            db=None,
            identity=_t4_identity(),
            request_id="req-t4",
            query="q",
            timeline=[],
        )
        try:
            await handlers["rag"]("rag", {"kb_id": "kb"})
        except Exception:  # noqa: BLE001 - 新契约：不再回退 ⇒ 应如实上抛
            raised = True
    return gateway._merge_rag_trace({}, rag_source=shared.get("rag_source")), raised


async def _t4_stream_trace(exc: Exception) -> tuple[dict[str, Any], Any]:
    """流式路径：共用组件步骤**如实降级**（`degraded` ＋ `errors` 带原因、`executed` 无伪造条目）"""
    import app.api.openllm_gateway as gateway
    from app.edgerouter.orchestration.component_pipeline import run_components

    async def _rag_handler(_name: str, _params: dict) -> dict:
        raise exc

    result = await run_components(
        pipeline=[{"component": "rag", "params": {"kb_id": "kb"}}],
        query="q",
        handlers={"rag": _rag_handler},
        assembler=None,
        enable_parallel=False,
        entry_key="component",
        timeline=[],
    )
    return gateway._merge_rag_trace({}, rag_source=result.rag_source), result


class _T4FakeAuditRecorder:
    """T4 替身审计服务（记录入参；可选模拟落库失败）—— 不触真实审计库"""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.records: list[Any] = []

    async def record_operation(self, record: Any) -> Any:
        self.records.append(record)
        if self.fail:
            raise RuntimeError("模拟落库失败")
        return record


async def _t4_channel_audit() -> dict[str, Any]:
    """采集 B→A 接管**审计落库**的判定证据（A2 / 题 4；进程内可判）

    **关键**：开启态**经真实接管路径**（`trigger_failover_to_a`）触发，故本段同时证明
    **接线成立**（而非只证明「函数本身可用」）。
    """
    from app.identity import channel_audit
    from app.identity.channel import get_channel_state_manager, reset_channel_state_manager

    # ① 门控关 ⇒ 不落库（逐字回退「仅日志」）
    reset_channel_state_manager()
    disabled_recorder = _T4FakeAuditRecorder()
    channel_audit.set_audit_service_factory(lambda: disabled_recorder)
    with _temporary_settings(CHANNEL_AUDIT_ENABLED=False):
        disabled_status = channel_audit.emit_failover_audit(
            source="manual", reason="演练", actor="ops", primary_after="a"
        )
    await asyncio.sleep(0.05)
    disabled_records = len(disabled_recorder.records)

    # ② 门控开 ⇒ **经真实接管路径**落库 1 条，字段完整
    reset_channel_state_manager()
    enabled_recorder = _T4FakeAuditRecorder()
    channel_audit.set_audit_service_factory(lambda: enabled_recorder)
    with _temporary_settings(CHANNEL_AUDIT_ENABLED=True):
        manager = get_channel_state_manager()
        takeover_ok = manager.trigger_failover_to_a(
            source="manual", reason="演练", actor="ops"
        )
        primary_after = manager.primary_channel
    await asyncio.sleep(0.05)
    enabled_records = len(enabled_recorder.records)
    record = enabled_recorder.records[0] if enabled_recorder.records else None
    missing_fields: list[str] = [] if record is not None else ["record"]
    if record is not None:
        for field in ("action", "operator_name", "target_type", "target_id", "detail"):
            if not getattr(record, field, None):
                missing_fields.append(field)
    enabled_status = "scheduled" if record is not None else "missing"

    # ③ 无运行循环（同步上下文）⇒ no_loop 且不抛 —— 用工作线程构造「无循环」环境
    with _temporary_settings(CHANNEL_AUDIT_ENABLED=True):
        no_loop_status = await asyncio.to_thread(
            channel_audit.emit_failover_audit,
            source="manual",
            reason="演练",
            actor="ops",
            primary_after="a",
        )

    # ④ 落库异常 ⇒ fail-open（接管仍成功且通道已切）
    reset_channel_state_manager()
    failing_recorder = _T4FakeAuditRecorder(fail=True)
    channel_audit.set_audit_service_factory(lambda: failing_recorder)
    with _temporary_settings(CHANNEL_AUDIT_ENABLED=True):
        failing_manager = get_channel_state_manager()
        fail_open_ok = failing_manager.trigger_failover_to_a(source="manual", reason="演练")
        fail_open_primary = failing_manager.primary_channel
    await asyncio.sleep(0.05)
    fail_open_ok = bool(fail_open_ok and fail_open_primary == "a")

    # ⑤ 重复接管 ⇒ 不重复落库（幂等）
    reset_channel_state_manager()
    idempotent_recorder = _T4FakeAuditRecorder()
    channel_audit.set_audit_service_factory(lambda: idempotent_recorder)
    with _temporary_settings(CHANNEL_AUDIT_ENABLED=True):
        idempotent_manager = get_channel_state_manager()
        first = idempotent_manager.trigger_failover_to_a(source="manual", reason="首次")
        second = idempotent_manager.trigger_failover_to_a(source="manual", reason="重复")
    await asyncio.sleep(0.05)
    idempotent_records = len(idempotent_recorder.records)

    channel_audit.reset_audit_service_factory()
    reset_channel_state_manager()
    return {
        "disabled_status": disabled_status,
        "disabled_records": disabled_records,
        "enabled_status": enabled_status,
        "enabled_records": enabled_records,
        "takeover_ok_via_real_path": takeover_ok,
        "primary_after": primary_after,
        "record_action": record.action if record is not None else None,
        "record_operator": record.operator_name if record is not None else None,
        "record_target": (
            f"{record.target_type}:{record.target_id}" if record is not None else None
        ),
        "record_detail": dict(record.detail) if record is not None else None,
        "record_missing_fields": missing_fields,
        "no_loop_status": no_loop_status,
        "fail_open_ok": fail_open_ok,
        "idempotent_first": first,
        "idempotent_second": second,
        "idempotent_records": idempotent_records,
        "provisional_note": channel_audit.ACTION_PROVISIONAL_NOTE,
    }


async def check_t4() -> Verdict:
    """T4：组件故障后通道裁决有轨迹 —— **失败如实降级且可观测**（轨迹部分：进程内可判）

    **W3 / Q11（v1.28.0）判据重做**（依《收口方案》v1.5.0 §2.5「连带影响」）：原契约以
    「内置 RAG 接管」为证据（`rag_source=builtin` ＋ `builtin_fallback_reason`）——
    该**自建数据面已按 Q11 裁定整体废弃**（两通道均只调用同一批三基础设施、无自建数据面）
    ⇒ 旧证据**不再成立**，契约重做为「**如实降级且可观测**」：

      1. 同步路径 handler：「外部检索失败」→ **如实上抛**（不再回退本地库）；
      2. 流式路径（共用组件步骤）：**如实降级** —— `degraded` 含 `rag`、`errors` 带**原因**、
         `rag_source` 保持 `skipped`、**`executed` 不含伪造条目**；
      3. 两路径经**同一落痕函数**并入 `routing_trace.components` → **字段逐键一致**。

    端点级（HTTP）故障注入另由单元护栏覆盖（同步端点 200 且轨迹 `skipped` ＋ 记降级、
    **无接管归因字段**、装配缺失同样降级），见 ``detail.endpoint_level_evidence``。

      4. **B→A 接管独立审计落库**（**A2 / 题 4 补入**）：门控关 ⇒ 不落库（逐字回退「仅日志」）；
         开 ⇒ **经真实接管路径**落库且字段完整（动作码 / actor / 目标 / 归因 / 时间）；
         无运行循环 ⇒ `no_loop` 且不抛；落库异常 ⇒ **fail-open**（接管仍成功）；重复接管 ⇒ 不重复落库。

    **仍需运行态**：**真实**停 OpenRAG / 改不可达地址的故障注入、端到端轨迹**实际落库**读取。
    （**已移除**：原「`health.components.builtin_rag.has_base`（接管是否有底座）」一项 ——
    该探针随 Q11 废弃一并删除。）
    """
    title = (
        "备通道：组件故障后**如实降级且可观测**（轨迹 ＋ B→A 接管审计落库=进程内判；无 5xx=运行态）"
    )
    from app.api.openllm_gateway import _merge_rag_trace

    fault = RuntimeError("OpenRAG 不可达: connection refused")
    sync_trace, sync_raised = await _t4_sync_trace(fault)
    stream_trace, stream_result = await _t4_stream_trace(fault)

    failures: list[str] = []
    if not sync_raised:
        failures.append("同步路径 handler 未如实上抛（新契约下**不应有**回退吞异常）")
    if sync_trace.get("rag_source") != "skipped":
        failures.append(f"同步路径失败应如实保持 skipped：{sync_trace}")
    if stream_trace.get("rag_source") != "skipped":
        failures.append(f"流式路径失败应如实保持 skipped：{stream_trace}")
    if sync_trace != stream_trace:
        failures.append(f"两路径轨迹不一致（须同源）：{sync_trace} vs {stream_trace}")
    if "builtin_fallback_reason" in stream_trace:
        failures.append("接管归因字段**不得复活**（Q11 已裁定废弃）")
    if "rag" not in (getattr(stream_result, "degraded", None) or []):
        failures.append(f"流式路径未如实记降级：{getattr(stream_result, 'degraded', None)}")
    if "rag" in (getattr(stream_result, "executed", None) or {}):
        failures.append("失败时**不得**注入伪造的 rag 条目")
    stream_reasons = [
        item
        for item in (getattr(stream_result, "errors", None) or [])
        if item.get("component") == "rag"
    ]
    if not stream_reasons or "connection refused" not in stream_reasons[0].get("error", ""):
        failures.append(f"流式路径失败归因缺失：{getattr(stream_result, 'errors', None)}")
    merged = _merge_rag_trace({})
    if merged.get("rag_source") != "skipped" or "builtin_fallback_reason" in merged:
        failures.append(f"未执行检索时应为 skipped 且不落归因：{merged}")

    # ---- A2 / 题 4：B→A 接管**独立审计落库**（进程内可判） ----
    #     动因：接管此前仅 WARNING 日志 ＋ `routing_trace.components`，`AuditService`
    #     有能力但**零调用点** ⇒ 无法按审计口径统计接管次数 / 时长分布。契约：门控关 ⇒
    #     不落库（逐字回退仅日志）；开 ⇒ **经真实接管路径**落库且字段完整；无运行循环 ⇒
    #     `no_loop` 且不抛；落库异常 ⇒ fail-open；重复接管 ⇒ 不重复落库。
    audit_evidence = await _t4_channel_audit()
    if audit_evidence["disabled_status"] != "disabled":
        failures.append(f"审计门控关时应为 disabled：{audit_evidence['disabled_status']}")
    if audit_evidence["disabled_records"] != 0:
        failures.append("审计门控关时不得落库（须逐字回退「仅日志」）")
    if audit_evidence["takeover_ok_via_real_path"] is not True:
        failures.append("门控开时真实接管路径未成功（接线未生效？）")
    if audit_evidence["enabled_status"] != "scheduled":
        failures.append(f"审计门控开时应投递：{audit_evidence['enabled_status']}")
    if audit_evidence["enabled_records"] != 1:
        failures.append(
            f"审计门控开时应落库 1 条：{audit_evidence['enabled_records']}"
        )
    if audit_evidence["record_action"] != "channel_failover_b_to_a":
        failures.append(f"审计动作码不符：{audit_evidence['record_action']}")
    if audit_evidence["record_missing_fields"]:
        failures.append(f"审计记录缺字段：{audit_evidence['record_missing_fields']}")
    if audit_evidence["no_loop_status"] != "no_loop":
        failures.append(f"无运行循环应为 no_loop：{audit_evidence['no_loop_status']}")
    if audit_evidence["fail_open_ok"] is not True:
        failures.append("落库异常影响了接管主流程（fail-open 被破坏）")
    if audit_evidence["idempotent_records"] != 1:
        failures.append(
            f"重复接管重复落库：{audit_evidence['idempotent_records']} 条"
        )

    detail: dict[str, Any] = {
        "fault_injected": f"{type(fault).__name__}: {fault}",
        "sync_trace_components": sync_trace,
        "stream_trace_components": stream_trace,
        "trace_contract": "FAIL" if failures else "PASS",
        "honest_degradation": {
            "sync_raised": sync_raised,
            "sync_trace": sync_trace,
            "stream_trace": stream_trace,
            "stream_degraded": getattr(stream_result, "degraded", None),
            "stream_errors": getattr(stream_result, "errors", None),
            "stream_executed_keys": sorted(getattr(stream_result, "executed", None) or {}),
        },
        "channel_audit": audit_evidence,
        "channel_audit_contract": (
            "**A2 / 题 4**：B→A 接管**独立审计落库**已接线（`app/identity/channel_audit.py`，"
            "单一落痕点覆盖人工/自动两条触发路径）；`emit_failover_audit` **永不抛出**"
            "（fail-open 到「仅日志」）、有运行循环时后台写入（不阻塞事件循环）、"
            "无循环时记 WARN 并放弃。**门控 `CHANNEL_AUDIT_ENABLED` 出厂默认 False** ⇒ "
            "关闭即逐字回退现行行为。**审计动作码 `channel_failover_b_to_a` 属暂定**"
            "（§10 项 6 建议单独立项审批）⇒ 未扩展 `AuditAction` 枚举、且未审批前不默认写审计库。"
        ),
        "runtime_pending": [
            "真实停 OpenRAG / 改不可达地址的故障注入（本执行器不改外部服务状态）",
            "端到端轨迹**实际落库**读取（本执行器只判到「落库调用入参」层）",
        ],
        "endpoint_level_evidence": (
            "端点级（HTTP，进程内 TestClient）故障注入已由 "
            "`tests/unit/test_rag_honest_degradation_trace.py::TestEndpointLevelFaultInjection` "
            "覆盖 2 例：同步 POST /openllm/v1/chat 返回 **200** 且轨迹 `rag_source=skipped`、"
            "**记 `degraded`（含 rag）**、**无接管归因字段**；装配缺失同样 200 且降级。"
            "该层证明「组件故障时**不返回 5xx** 且**如实降级可复盘**」，**不替代真实停服 E2E**"
        ),
        "historical_e2e_evidence": (
            "CR-148-013 TT-022/TT-023（2026-09-22，mock 桩故障注入）曾在旧提交上验过"
            "`rag_source=builtin` / `degraded=[]` / 主流程 200 —— **该证据口径已随 Q11 废弃而失效**"
            "（内置 RAG 自建数据面不存在）⇒ 若需运行态回归，须按**新契约**重定义期望"
            "（`rag_source=skipped` ＋ `degraded` 含 rag ＋ 端到端 200）后复跑"
        ),
    }
    if failures:
        return Verdict(
            criterion="T4",
            title=title,
            status=STATUS_FAIL,
            detail=detail,
            reason="轨迹契约不达标：" + "；".join(failures),
        )
    return Verdict(
        criterion="T4",
        title=title,
        status=STATUS_BLOCKED,
        requires=[
            "运行态服务（真实停服/改址注入 + 轨迹实际落库读取）",
        ],
        detail=detail,
        reason=(
            "轨迹部分已在进程内验证通过（**失败如实降级且可观测**：同步路径如实上抛、"
            "流式路径落 `degraded` / `errors` 带原因、`rag_source` 保持 `skipped`、"
            "`executed` 无伪造条目、两路径**逐键一致**、单一落痕实现）；"
            "且端点级（HTTP）故障注入 2 例通过（端点均 200、如实降级、**无接管归因字段**）"
            "⇒「无 5xx」已在**进程内**覆盖；剩余**真实停服注入**与**轨迹实际落库读取**需运行态。"
            "**判据重做说明**：原契约以「内置 RAG 接管」（`rag_source=builtin` ＋ `builtin_fallback_reason`）"
            "为证据 —— 该自建数据面已按 **Q11 裁定整体废弃**（两通道均只调用同一批三基础设施、"
            "无自建数据面）⇒ 旧证据失效，故本次按「**如实降级**」重定义契约。"
        ),
    )


# ---------------------------------------------------------------- T5 写侧闸门

class _QueueStub:
    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []

    def register_handler(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def next_seq(self, _session_id: str) -> int:
        return 1

    async def submit(self, request_id, session_id, seq, target, payload) -> bool:
        self.submitted.append({"target": target, "response": payload.get("response")})
        return True


class _IdentityStub:
    user_id = "u-probe"
    organization_id = "org-probe"
    role = "org_member"


async def _run_writeback_round(query: str, response: str) -> tuple[list[str], dict[str, Any]]:
    import app.api.openllm_gateway as gateway
    import app.services.writeback_queue as queue_module

    queue = _QueueStub()
    original = queue_module.get_writeback_queue
    queue_module.get_writeback_queue = lambda: queue
    try:
        memory_cb, rag_cb, profile_cb, _kwargs = gateway._build_writeback_callback(
            _IdentityStub(), "req-t5", session_id="sess-t5", rag_kb_id="kb-t5"
        )
        returns = {}
        for road, callback in (
            ("memory", memory_cb),
            ("rag", rag_cb),
            ("profile", profile_cb),
        ):
            returns[road] = await callback(query=query, response=response)
    finally:
        queue_module.get_writeback_queue = original
    return [item["target"] for item in queue.submitted], returns


async def _rag_value_gate_probe() -> tuple[bool, dict[str, Any], list[str]]:
    """T5 段②：**执行层**价值闸门（`save_if_valuable` 必须是实际判定）

    **为何单列一段**：段①（网关决策闸门）只在 chat 回写路径生效，且需开关开启；
    而**直接调用** `POST /openllm/v1/writeback`（或队列内既有行）**不经**决策层
    —— 若执行层不读该字段，则「显式声明不值得沉淀」仍会入库（v1.18.0 前的实际
    状态：`payload["save_if_valuable"]` **只写不读**）。该段**无开关、恒生效**，
    故进程内恒可判。

    Returns:
        (是否达标, 原始测量, 失败说明列表)
    """
    from unittest.mock import Mock, patch

    import httpx
    from app.edgerouter.adapters.openrag import OpenRAGAdapter
    from app.edgerouter.adapters.openrag_client import OpenRAGClient

    calls: list[Any] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "code": 0,
                "message": "success",
                "data": {
                    "document_id": "doc-t5",
                    "filename": "text-t5.txt",
                    "file_type": "text",
                    "status": "PENDING",
                },
            },
        )

    client = OpenRAGClient(
        base_url="http://openrag.probe",
        timeout=5.0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(_handler), timeout=5.0
        ),
        real_mode=True,
    )
    router = Mock()
    router.isolation_engine = Mock()
    adapter = OpenRAGAdapter(router, client)

    async def _invoke(**kwargs: Any) -> Any:
        from app.api import writeback as writeback_module

        with patch.object(
            writeback_module, "_get_gateway_adapters", lambda: (None, adapter)
        ):
            return await writeback_module._rag_writeback(**kwargs)

    base: dict[str, Any] = {
        "user_id": "probe-user",
        "session_id": "probe-session",
        "kb_id": "kb_probe",
        "query": "q",
        "response": "r",
    }
    off_return = await _invoke(**base, save_if_valuable=False)
    skipped_requests = len(calls)
    await _invoke(**base)  # 缺省（不传该键）⇒ 逐字回退：应仍提交
    default_requests = len(calls) - skipped_requests
    await client.aclose()

    failures: list[str] = []
    if skipped_requests:
        failures.append(f"save_if_valuable=false 仍发起 {skipped_requests} 次入库请求")
    if off_return is not None:
        failures.append(f"save_if_valuable=false 返回值非 None：{off_return!r}")
    if default_requests != 1:
        failures.append(f"缺省（不传该键）应仍提交 1 次，实测 {default_requests}")
    detail = {
        "skipped_requests": skipped_requests,
        "default_requests": default_requests,
        "skipped_return": off_return,
    }
    return (not failures), detail, failures


async def check_t5() -> Verdict:
    """T5：低价值轮次不产生 rag 入库（无该行或 skipped），高价值轮次正常入库

    **v1.18.0 起分两段**：

      ① **网关决策闸门**（`WRITEBACK_DECISION_ENABLED`，默认关闭）—— 开启后低价值
         轮次经 `skipped` 回执拦截、不入队；开关关闭 ⇒ 本段按既有口径 `SKIP`；
      ② **执行层价值闸门**（**无开关、恒生效**）—— `save_if_valuable=false`
         ⇒ `_rag_writeback` **零出站请求**，覆盖**不经决策层**的直接调用路径；
         本段进程内恒可判，**不达标即 `FAIL`**。
    """
    title = "写侧闸门：低价值轮次不入库、高价值轮次正常入库"
    keys = ["WRITEBACK_DECISION_ENABLED"]

    gate_ok, gate_detail, gate_failures = await _rag_value_gate_probe()
    if not gate_ok:
        return Verdict(
            criterion="T5",
            title=title,
            status=STATUS_FAIL,
            requires=["执行层价值闸门（无开关，恒生效）"],
            detail={"rag_value_gate": gate_detail},
            reason="；".join(gate_failures),
        )

    if not _is_on("WRITEBACK_DECISION_ENABLED"):
        verdict = _switch_off_verdict("T5", title, keys)
        verdict.detail = {"rag_value_gate": gate_detail}
        verdict.reason = (
            "段②执行层价值闸门（无开关，恒生效）已达标：save_if_valuable=false ⇒ 零请求、"
            "缺省逐字回退；段①网关决策闸门待开关开启后复跑"
        )
        return verdict

    low_submitted, low_returns = await _run_writeback_round("你好", "")
    high_submitted, high_returns = await _run_writeback_round(
        "请记住：我偏好简洁的回答", "好的，已记住。"
    )
    failures = []
    if low_submitted:
        failures.append(f"低价值轮次产生了回写行：{low_submitted}")
    if low_returns.get("rag") != "skipped":
        failures.append(f"低价值轮次 rag 回执非 skipped：{low_returns.get('rag')}")
    if "rag" not in high_submitted:
        failures.append("高价值轮次 rag 未入库")
    return Verdict(
        criterion="T5",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        requires=[f"WRITEBACK_DECISION_ENABLED={_is_on('WRITEBACK_DECISION_ENABLED')}"],
        detail={
            "rag_value_gate": gate_detail,
            "low_value": {"submitted": low_submitted, "returns": low_returns},
            "high_value": {"submitted": high_submitted, "returns": high_returns},
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T6 精炼

def check_t6() -> Verdict:
    """T6：精炼开启时 fallback=false 且 elapsed_ms ≤ 预算；关闭/超时不降级

    **v1.13.0 起拆分**（与 T4 同思路）：

      ① **规则档**（确定性精炼：去重 / 相邻同义合并 / 单条截断 / 配额裁剪）——
         `refine` 回执已在进程内可判：`mode=rule`、`fallback=false`、
         `elapsed_ms` 远小于在线预算、未启用时不落痕 ⇒ **本执行器判定**；
      ② **模型档**（生成式精炼：`mode=model` 的压缩质量与预算）—— **已裁定整体搁置
         （v1.26.0 方案 B）**：2B/4B 与既有 ≤1B 全部不达 §5.6 门槛（§5.4 复测：
         精度 < 0.90 且 P95 > 30s），不再列为交付目标 ⇒ `model_tier=SHELVED`。

    **v1.22.0 增段①补（位置门禁，进程内恒可判）**：§9 问题 2 裁定「位置由部署显式声明 ＋
    三道门禁（v1.26.0 由四道收窄，探活门禁已删）」⇒ 本判据增判 **在线通道永不放行生成式**
    （红线）、**非法位置值 fail-safe 回退**、**遗留 `gpu_node` 视为非法回退 `disabled`**
    （v1.26.0 回归锁定）、**未声明位置时异步亦不放行且理由非空**、**压缩率目标观测已落
    规则档回执**。
    """
    title = "精炼：规则档回执与位置门禁已可判（进程内）；模型档已搁置（v1.26.0 方案 B）"
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt
    from app.edgerouter.orchestration.refine_placement import (
        REFINE_CHANNEL_ASYNC,
        REFINE_CHANNEL_ONLINE,
        plan_refine_inference,
        resolve_refine_inference_target,
    )

    def _chars(text: str) -> int:
        return len(text or "")

    policy = BudgetPolicy(
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
    memory = "\n".join(["1. " + "甲" * 400, "2. " + "乙" * 400])
    _prompt, comp = build_prompt(
        query="问", memory_ctx=memory, count_tokens=_chars, budget=policy
    )
    _p2, off_comp = build_prompt(
        query="问", memory_ctx="1. 甲", count_tokens=_chars, budget=BudgetPolicy(enabled=False)
    )
    receipt = comp.refine

    failures: list[str] = []
    if receipt.get("mode") != "rule":
        failures.append(f"规则档回执 mode 非 rule：{receipt}")
    if receipt.get("fallback") is not False:
        failures.append(f"规则档回执 fallback 非 False：{receipt}")
    if not isinstance(receipt.get("elapsed_ms"), int):
        failures.append(f"规则档回执缺 elapsed_ms：{receipt}")
    if receipt.get("out_tokens", 0) >= receipt.get("in_tokens", 0):
        failures.append(f"规则档回执 out/in 未反映裁剪：{receipt}")
    if off_comp.refine != {}:
        failures.append(f"未启用精炼时不得落痕：{off_comp.refine}")

    # ---- 段①补：位置门禁（§9 问题 2 裁定；进程内恒可判）----
    from app.core.config import settings

    previous_target = settings.CONTEXT_REFINE_INFERENCE_TARGET
    try:
        settings.CONTEXT_REFINE_INFERENCE_TARGET = "gpu_node"  # 遗留值（v1.26.0 方案 B 回归锁定）
        online = plan_refine_inference(channel=REFINE_CHANNEL_ONLINE)
        async_plan = plan_refine_inference(channel=REFINE_CHANNEL_ASYNC)
        legacy_target, legacy_reason = resolve_refine_inference_target()
        settings.CONTEXT_REFINE_INFERENCE_TARGET = "typo_target"
        typo_target, typo_reason = resolve_refine_inference_target()
    finally:
        settings.CONTEXT_REFINE_INFERENCE_TARGET = previous_target

    placement_rows = {
        "online_channel_allowed": online["allowed"],
        "online_channel_reason": online["reason"],
        "async_channel_reason": async_plan["reason"],
        "legacy_gpu_node_resolved": legacy_target,
        "legacy_gpu_node_reason": legacy_reason,
        "invalid_target_resolved": typo_target,
        "invalid_target_reason": typo_reason,
        "compression_observation": receipt.get("compression", {}),
    }
    if online["allowed"] is not False:
        failures.append(f"在线通道竟放行生成式精炼（红线被破）：{online}")
    if online["reason"] != "online_path_forbids_generative":
        failures.append(f"在线通道理由非红线词：{online['reason']}")
    if not str(async_plan["reason"]).strip():
        failures.append(f"异步通道阻塞未给理由（静默降级）：{async_plan}")
    if legacy_target != "disabled" or not legacy_reason.startswith("invalid_target:"):
        failures.append(
            f"遗留 gpu_node 未视为非法回退 disabled（v1.26.0 方案 B）："
            f"{legacy_target} / {legacy_reason}"
        )
    if typo_target != "disabled" or not typo_reason.startswith("invalid_target:"):
        failures.append(f"非法位置值未 fail-safe 回退：{typo_target} / {typo_reason}")
    compression = receipt.get("compression") or {}
    if "memory" not in compression or compression["memory"].get("ratio") is None:
        failures.append(f"压缩率目标观测未落回执：{compression}")

    detail: dict[str, Any] = {
        "rule_tier_receipt": receipt,
        "rule_tier_evidence": (
            "`tests/unit/test_assembly_refine_rule_tier.py::TestRefineReceipt`（5 例）＋ "
            "运行态探针 `doc/test/evidence/cr149/assembly_rule_tier_probe.py`"
        ),
        "rule_tier": "FAIL" if failures else "PASS",
        "placement_gate": placement_rows,
        "placement_gate_evidence": (
            "`tests/unit/test_refine_placement_policy.py`（41 例）＋ "
            "探针 `doc/test/evidence/cr149/refine_placement_probe.py`（14 例 ＋ 结尾自检）"
        ),
        "model_tier": "SHELVED（v1.26.0 方案 B：2B/4B 与 ≤1B 全部不达 §5.6 门槛，生成式精炼整体搁置）",
        "model_tier_quality_framework": (
            "**A5（题 9）第③子项「T6 模型档质量对比判据**框架**」据 v1.26.0 方案 B 裁定"
            " ⇒ 不建（superseded）**：模型档已**整体搁置** ⇒ 该框架**无消费方**；"
            "若未来解除搁置（出现达标模型 ＋ 合法推理位置），须**重新立判据**，"
            "而非复用空壳框架。**如实登记为「明确保留理由（不建）」**，"
            "不以空壳框架冒充已交付。"
        ),
        "runtime_pending": [
            "生成式精炼已裁定整体搁置（v1.26.0 方案 B）—— 无达标模型（§5.4 复测：精度 < 0.90、"
            "P95 压缩 > 异步档 30s 预算，最慢 134.6s），不再列为第三批交付目标，无运行态遗留项",
        ],
    }
    if failures:
        return Verdict(
            criterion="T6",
            title=title,
            status=STATUS_FAIL,
            detail=detail,
            reason="规则档回执/位置门禁契约不达标：" + "；".join(failures),
        )
    return Verdict(
        criterion="T6",
        title=title,
        status=STATUS_PASS,
        detail=detail,
        reason=(
            "规则档（确定性精炼）的 `refine` 回执＋**位置门禁**（在线红线 / fail-safe 回退 / "
            "遗留 `gpu_node` 视为非法回退 disabled / 阻塞必带理由 / 压缩率目标观测）已在进程内"
            "验证通过（mode=rule、fallback=false、out<in、未启用不落痕）；"
            "**模型档（生成式精炼）已裁定整体搁置（v1.26.0 方案 B）**：2B/4B 复测精度与时延"
            "双不达标（§5.4），不再列为交付目标 ⇒ 本判据无遗留阻塞项，判定 PASS"
        ),
    )


# ---------------------------------------------------------------- T7 画像并发

async def check_t7() -> Verdict:
    """T7：画像取数并发、两路径时序统一且组装前收割"""
    title = "画像：并发取数 + 两路径时序统一 + 组装前收割（含 P-4）"
    import inspect

    import app.api.openllm_gateway as gateway
    from app.edgerouter.orchestration.deferred_fetch import DeferredFetch
    from app.edgerouter.orchestration.executor import PipelineExecutor

    events: list[str] = []
    captured: dict[str, str] = {}

    async def _profile():
        events.append("profile_start")
        await asyncio.sleep(0.05)
        events.append("profile_end")
        return "用户画像：并发验证"

    async def _memory(_name: str, _params: dict) -> dict:
        events.append("components_start")
        await asyncio.sleep(0.05)
        events.append("components_end")
        return {"text": "记忆条目"}

    async def _llm(_name: str, params: dict) -> dict:
        captured["prompt"] = params["prompt"]
        return {"content": "ok", "usage": {}}

    executor = PipelineExecutor()
    started = time.monotonic()
    await executor.execute(
        [{"name": "memory", "params": {}}, {"name": "llm", "params": {}}],
        {"memory": _memory, "llm": _llm},
        query="问题",
        profile_ctx=DeferredFetch("profile_fetch", awaitable=_profile()),
    )
    concurrent_wall = time.monotonic() - started

    source = inspect.getsource(gateway)
    routing_at = source.index('f"event: routing')
    stream_start = source.index("DeferredFetch(", routing_at)
    stream_resolve = source.index("await profile_slot.resolve()", stream_start)
    stream_guard = source.index("prompt, composition = build_prompt(", stream_resolve)
    order_ok = (
        routing_at < stream_start < stream_resolve < stream_guard
        and "profile_ctx=profile_slot," in source
    )
    overlapped = (
        events.index("profile_start") < events.index("components_end")
        and events.index("components_start") < events.index("profile_end")
    )
    failures = []
    if not overlapped:
        failures.append(f"画像与组件未重叠：{events}")
    if not order_ok:
        failures.append("两路径时序契约不成立（首包后构造 / 组装前收割 / 同步交句柄）")
    if "用户画像：并发验证" not in captured.get("prompt", ""):
        failures.append("画像内容未进入 Prompt（组装前未收割）")
    return Verdict(
        criterion="T7",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "events": events,
            "concurrent_components_wall_seconds": round(concurrent_wall, 3),
            "prompt_has_profile": "用户画像：并发验证" in captured.get("prompt", ""),
            "gateway_order_contract_ok": order_ok,
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T8 依赖图调度

async def check_t8() -> Verdict:
    """T8：调度由依赖图决定（无依赖即并行 / 声明保序 / 成环 fail-safe）"""
    title = "调度：无依赖即并行、依赖声明保序、成环 fail-safe"
    keys = ["COMPONENT_DEPENDENCY_SCHEDULING_ENABLED", "OPENLLM_COMPONENT_DEPENDENCIES"]
    from app.edgerouter.orchestration.component_graph import dependency_levels
    from app.edgerouter.orchestration.component_pipeline import run_components
    from app.edgerouter.orchestration.prompt_pipeline import PromptAssembler

    class _Assembler(PromptAssembler):
        def format_context(self, name: str, data: dict) -> str:  # type: ignore[override]
            return str((data or {}).get("text") or "")

    async def _measure(enable_parallel: bool) -> tuple[float, list[str]]:
        events: list[str] = []

        async def _handler(name: str, _params: dict) -> dict:
            events.append(f"{name}_start")
            await asyncio.sleep(0.05)
            events.append(f"{name}_end")
            return {"text": name}

        started = time.monotonic()
        await run_components(
            pipeline=[{"name": "memory", "params": {}}, {"name": "rag", "params": {}}],
            query="q",
            handlers={"memory": _handler, "rag": _handler},
            assembler=_Assembler(),
            enable_parallel=enable_parallel,
        )
        return time.monotonic() - started, events

    switch_on = _is_on("COMPONENT_DEPENDENCY_SCHEDULING_ENABLED")
    # 开关关闭时：以临时置位证明"开启后即达标"（进程内，退出恢复）
    with _temporary_settings(
        COMPONENT_DEPENDENCY_SCHEDULING_ENABLED=True,
        OPENLLM_COMPONENT_DEPENDENCIES="",
    ):
        parallel_wall, parallel_events = await _measure(enable_parallel=False)
    with _temporary_settings(
        COMPONENT_DEPENDENCY_SCHEDULING_ENABLED=True,
        OPENLLM_COMPONENT_DEPENDENCIES="memory:rag",
    ):
        ordered_wall, ordered_events = await _measure(enable_parallel=True)
    cycle_levels = dependency_levels(
        ["memory", "rag"], {"memory": ("rag",), "rag": ("memory",)}
    )
    parallel_ok = (
        parallel_events.index("memory_start") < parallel_events.index("rag_end")
        and parallel_events.index("rag_start") < parallel_events.index("memory_end")
    )
    failures = []
    if not parallel_ok:
        failures.append(f"无依赖未并行：{parallel_events}")
    if ordered_events != ["rag_start", "rag_end", "memory_start", "memory_end"]:
        failures.append(f"依赖声明未保序：{ordered_events}")
    if cycle_levels != [["memory", "rag"]]:
        failures.append(f"成环未 fail-safe：{cycle_levels}")
    detail = {
        "switch_enabled_in_config": switch_on,
        "parallel_wall_seconds": round(parallel_wall, 3),
        "ordered_wall_seconds": round(ordered_wall, 3),
        "parallel_events": parallel_events,
        "ordered_events": ordered_events,
        "cycle_levels": cycle_levels,
        "config_state": _settings_snapshot(keys),
    }
    if failures:
        return Verdict("T8", title, STATUS_FAIL, detail=detail, reason="；".join(failures))
    if not switch_on:
        return Verdict(
            criterion="T8",
            title=title,
            status=STATUS_SKIP,
            requires=[f"{key}={value}" for key, value in detail["config_state"].items()],
            detail=detail,
            reason="能力已达标（临时置位验证），但配置开关仍为关：开启后本判据即为 PASS",
        )
    return Verdict("T8", title, STATUS_PASS, detail=detail)


# ---------------------------------------------------------------- T9 路由一致性

def check_t9() -> Verdict:
    """T9：路由达标判定与最终决策一致；规则集可配置；LLM 兜底超时回落；兜底分类缓存

    ④（v1.16.0 补入，对方案 §5.8「路由分类按 query 归一化缓存」）：同题（归一化后相同）
    重复提问**只付一次**兜底分类；不同 query 各付一次；容量置 0 ⇒ **逐字回退**（每次分类）。
    """
    title = "路由：达标即决策、规则集可配置、LLM 兜底超时回落、兜底分类按 query 归一化缓存"
    from app.api.openllm_gateway import _build_component_router
    from app.edgerouter.orchestration.component_router import ComponentRouter

    single = ComponentRouter().decide_sync("我的资料在哪里")
    composite = ComponentRouter().decide_sync(
        "接着上次说的，帮我看下知识库里的文档", {"kb_id": "kb-1"}
    )
    legacy = ComponentRouter(single_hit_confidence=0.8).decide_sync("我的资料在哪里")

    with tempfile.TemporaryDirectory() as tmp:
        rules_path = os.path.join(tmp, "rules.json")
        with open(rules_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "rules": {
                        "X001": {
                            "type": "memory_keyword",
                            "keywords": ["专有词"],
                            "decision": {"need_memory": True, "need_rag": False},
                        }
                    }
                },
                handle,
                ensure_ascii=False,
            )
        configured = ComponentRouter(rules_path=rules_path)
        rules_loaded = sorted(configured.rules)
        custom_decision = configured.decide_sync("这里有个专有词")
    fallback_router = ComponentRouter(rules_path="/definitely/not/exists.json")
    invalid_path_rules = sorted(fallback_router.rules)

    async def _timeout_call_llm(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise TimeoutError("classification budget exceeded")

    import app.api.openllm_gateway as gateway

    original_call_llm = gateway._call_llm
    original_resolve = gateway._resolve_model_code
    gateway._call_llm = _timeout_call_llm  # type: ignore[assignment]
    gateway._resolve_model_code = lambda _comp: "probe-model"  # type: ignore[assignment]
    try:
        with _temporary_settings(COMPONENT_ROUTER_LLM_FALLBACK_ENABLED=True):
            router = _build_component_router(db=object(), identity=_IdentityStub())
            timeout_decision = asyncio.run(
                router.decide("请说明一下这个系统在大规模并发场景下的表现如何")
            )
    finally:
        gateway._call_llm = original_call_llm  # type: ignore[assignment]
        gateway._resolve_model_code = original_resolve  # type: ignore[assignment]

    from app.core.config import settings

    failures = []
    if single is None or not single.get("need_memory"):
        failures.append("单次命中未直接决策（存在「回落」分叉）")
    if composite is None or not (composite.get("need_memory") and composite.get("need_rag")):
        failures.append("复合意图（R005）未达标")
    if legacy is not None:
        failures.append(f"逃生阀未复现旧语义：{legacy}")
    if rules_loaded != ["X001"] or not (custom_decision or {}).get("need_memory"):
        failures.append(f"规则集配置未生效：{rules_loaded}")
    if invalid_path_rules != ["R001", "R002", "R003", "R004", "R005"]:
        failures.append(f"非法规则路径未退回内置规则：{invalid_path_rules}")
    if "无命中规则" not in (timeout_decision or {}).get("reason", ""):
        failures.append(f"LLM 超时未回落规则：{timeout_decision}")

    # ④ 兜底分类缓存（§5.8「路由分类按 query 归一化缓存」；v1.16.0 补入本判据）
    from app.edgerouter.orchestration.component_router import (
        ComponentRouter as _CacheRouter,
    )
    from app.edgerouter.orchestration.component_router import (
        clear_llm_decision_cache as _clear_cache,
    )

    class _CountingClassifier:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def __call__(self, query: str, _prompt: str) -> str:
            self.calls.append(query)
            return '{"need_memory": true, "need_rag": false, "reason": "分类器判定"}'

    _unmatched = "帮我看看这个东西怎么样"
    _unmatched_other = "顺便说一下那边的进展如何"
    _clear_cache()
    _counter = _CountingClassifier()
    _cache_router = _CacheRouter(llm_classifier=_counter)
    _first = asyncio.run(_cache_router.decide(_unmatched))
    _second = asyncio.run(_cache_router.decide(_unmatched))
    _same_query_calls = len(_counter.calls)
    asyncio.run(_cache_router.decide(_unmatched_other))
    _distinct_calls = len(_counter.calls)
    _copy_ok = _second == _first

    _clear_cache()
    _off_counter = _CountingClassifier()
    _off_router = _CacheRouter(llm_classifier=_off_counter, llm_cache_size=0)
    asyncio.run(_off_router.decide(_unmatched))
    asyncio.run(_off_router.decide(_unmatched))
    _switch_off_calls = len(_off_counter.calls)
    _clear_cache()

    if _same_query_calls != 1:
        failures.append(f"同题重复提问未命中缓存（实测分类 {_same_query_calls} 次）")
    if not _copy_ok:
        failures.append("缓存命中返回的决策与首次不等")
    if _distinct_calls != 2:
        failures.append("不同 query 未各付一次分类（缓存键过宽）")
    if _switch_off_calls != 2:
        failures.append("缓存容量置 0 时未逐字回退（仍应每次分类）")

    return Verdict(
        criterion="T9",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        requires=[
            f"COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE={settings.COMPONENT_ROUTER_SINGLE_HIT_CONFIDENCE}",
            f"COMPONENT_ROUTER_LLM_TIMEOUT_SECONDS={settings.COMPONENT_ROUTER_LLM_TIMEOUT_SECONDS}",
        ],
        detail={
            "single_hit_decision": single,
            "composite_intent_decision": composite,
            "legacy_escape_hatch_returns_none": legacy is None,
            "rules_loaded": rules_loaded,
            "invalid_path_rules": invalid_path_rules,
            "timeout_decision": timeout_decision,
            "classification_cache": {
                "same_query_calls": _same_query_calls,
                "distinct_query_calls": _distinct_calls,
                "capacity_zero_calls": _switch_off_calls,
                "default_capacity": _CacheRouter(llm_classifier=_CountingClassifier()).llm_cache_size,
            },
            "llm_fallback_switch": getattr(
                settings, "COMPONENT_ROUTER_LLM_FALLBACK_ENABLED", None
            ),
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T10 组装规则档契约

def check_t10() -> Verdict:
    """T10：组装侧规则档契约（元数据噪声剥离 / 相邻同义合并 / 稳定引用编号）

    v1.13.0 新增（对应方案 §3.4 规则档 ＋ §3.5 组装；此前的 §10 待登记项 7）。
    全部**进程内可判**，不依赖运行态服务：

      1. **噪声剥离**：平铺字段的 `None`/空值与链路元数据键（`trace_id`/`request_id`）
         不进入上下文；**依据性字段**（`score`/`source`）保留；开关关闭时逐字回退；
      2. **相邻同义合并**：仅 `memory` 段、仅相邻条目、保留较长者；与
         「完全重复即丢弃」**计数分开**（`merged_items` vs `dropped_items`）；
      3. **稳定引用编号**：默认关闭时输出 `N. 内容`（逐字不变）；开启时
         `memory→[M#]`、`rag→[K#]` 且与归因 A 下标对齐；去重/裁剪后**编号不重排**，
         保底一条仍守配额；
      4. **权重排序**（v1.14.0 补入，对方案 §3.2 第三项 / §3.3 memory·rag 行）：
         rag 按 `score` 降序、memory 按**时效衰减**降序（时间戳缺失视为新鲜，fail-open）；
         排序只改**呈现顺序**，引用编号仍取**原始下标**（与归因 A 对齐）；
         开关关闭 / 无排序依据 ⇒ **保持原序**；
      5. **画像字段级优先级**（A1 / 题 8，本版补入，对方案 §3.3 profile 行）：
         在「维度级行」之上再细分到**字段** —— 未列入优先级表的字段**先丢**、
         列入者**声明越靠后越先丢**、保留项**保序**、字段全丢的段头一并移除
         （不留悬挂标签）；`used ≤ quota` 不破；**开关关闭 或 表为空 ⇒ 逐字回退**末位淘汰。
    """
    title = "组装规则档：噪声剥离 / 相邻同义合并 / 稳定引用编号（均进程内可判）"
    from app.edgerouter.orchestration.assembler import PromptAssembler
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    def _chars(text: str) -> int:
        return len(text or "")

    def _policy(**overrides: Any) -> BudgetPolicy:
        params: dict[str, Any] = {
            "enabled": True,
            "window_tokens": 1000,
            "output_reserve_tokens": 0,
            "quota_ratios": {
                "system": 0.05,
                "profile": 0.10,
                "memory": 0.10,
                "rag": 0.10,
                "history": 0.10,
            },
            "single_item_max_tokens": 0,
        }
        params.update(overrides)
        return BudgetPolicy(**params)

    failures: list[str] = []

    # ① 噪声剥离
    noise_payload = {
        "trace_id": None,
        "request_id": "req-abc",
        "score": 0.87,
        "summary": "知识库摘要内容",
    }
    with _temporary_settings(CONTEXT_STRIP_METADATA_ENABLED=True):
        stripped = PromptAssembler().format_context("rag", noise_payload)
    with _temporary_settings(CONTEXT_STRIP_METADATA_ENABLED=False):
        raw = PromptAssembler().format_context("rag", noise_payload)
    if "trace_id" in stripped or "request_id" in stripped:
        failures.append(f"噪声键未剥离：{stripped!r}")
    if "score" not in stripped or "summary" not in stripped:
        failures.append(f"依据性字段被误删：{stripped!r}")
    if "trace_id: None" not in raw:
        failures.append(f"开关关闭未逐字回退：{raw!r}")
    if PromptAssembler().format_context("rag", {"trace_id": None}) != "":
        failures.append("全为噪声时应返回空串（不得注入空壳）")

    # ② 相邻同义合并
    memory = "\n".join(
        ["1. 用户偏好简洁回答", "2. 用户偏好简洁回答，不喜欢冗长解释", "3. 项目使用 Python"]
    )
    merged_prompt, merged_comp = build_prompt(
        query="问", memory_ctx=memory, count_tokens=_chars, budget=_policy()
    )
    memory_report = merged_comp.truncated.get("memory") or {}
    if memory_report.get("merged_items") != 1:
        failures.append(f"相邻同义未合并：{memory_report}")
    if memory_report.get("dropped_items") != 0:
        failures.append(f"合并不得计入 dropped_items：{memory_report}")
    if "不喜欢冗长解释" not in merged_prompt:
        failures.append("合并须保留较长者（信息不得丢失）")
    _p, rag_comp = build_prompt(
        query="问",
        rag_ctx="\n".join(["1. 知识甲内容", "2. 知识甲内容，补充说明"]),
        count_tokens=_chars,
        budget=_policy(),
    )
    if "merged_items" in (rag_comp.truncated.get("rag") or {}):
        failures.append("rag 段不得合并（方案限定「相邻**记忆**条目」)")

    # ③ 稳定引用编号
    default_text = PromptAssembler().format_context(
        "memory", {"results": [{"content": "甲"}, {"content": "乙"}]}
    )
    if default_text != "1. 甲\n2. 乙":
        failures.append(f"默认（开关关闭）编号形态须不变：{default_text!r}")
    with _temporary_settings(CONTEXT_REF_NUMBERS_ENABLED=True):
        labeled_memory = PromptAssembler().format_context(
            "memory", {"results": [{"content": "甲"}, {"content": "乙"}]}
        )
        labeled_rag = PromptAssembler().format_context(
            "rag", {"results": [{"content": "一"}, {"content": "二"}]}
        )
        dedup_prompt, dedup_comp = build_prompt(
            query="问",
            memory_ctx="[M1] 甲\n[M2] 甲\n[M3] 丙",
            count_tokens=_chars,
            budget=_policy(),
        )
    if labeled_memory != "[M1] 甲\n[M2] 乙":
        failures.append(f"memory 引用编号形态不符：{labeled_memory!r}")
    if labeled_rag != "[K1] 一\n[K2] 二":
        failures.append(f"rag 引用编号形态不符：{labeled_rag!r}")
    if "[M3]" not in dedup_prompt or "[M2]" in dedup_prompt:
        failures.append(f"去重后编号被重排（须稳定）：{dedup_prompt!r}")

    # ④ 权重排序（§3.2 第三项 / §3.3 memory·rag 行；v1.14.0 补入本判据）
    # **v1.18.0 订正（本判据自身的缺陷，非生产代码变化）**：原以**硬编码时刻**
    # `datetime(2026, 9, 27, 12, 0, 0)` 作基准 ⇒ 「新记忆」的 age 在壁钟越过该时刻前
    # 被 `max(0.0, …)` 钳为 0（衰减恰 1.0），越过之后变为正值（衰减 < 1.0）
    # ⇒ 断言「新记忆 排在 无时间戳记忆 之前」会**随壁钟自行翻转**（实测同一提交：
    # 12:00 前 PASS、之后 FAIL）。且该断言本身与实现语义不符：任何**严格过去**的
    # 时间戳衰减都 < 1.0，而 fail-open 恰为 1.0 ⇒ fail-open 的语义是「**不劣化**」
    # （等价于「刚刚发生」），不是「排在新记忆之后」。现改为：基准取 `now()`（相对、
    # 不随壁钟翻转），并以**严格单调**（无时间戳 1.0 > 1 天前 > 120 天前）＋
    # **fail-open 取值恰为 1.0** 两条确定性断言替代原歧义断言。
    from datetime import datetime, timedelta

    from app.edgerouter.orchestration.assembler import _item_decay

    _base = datetime.now()

    def _days_ago(days: float) -> str:
        return (_base - timedelta(days=days)).isoformat()

    fail_open_decay = _item_decay({"content": "无时间戳"}, half_life_days=30.0)
    fresh_decay = _item_decay({"content": "一天前", "updated_at": _days_ago(1)}, half_life_days=30.0)
    stale_decay = _item_decay({"content": "很久前", "updated_at": _days_ago(120)}, half_life_days=30.0)

    rag_ranked = PromptAssembler().format_context(
        "rag",
        {
            "results": [
                {"content": "低分", "score": 0.2},
                {"content": "高分", "score": 0.9},
                {"content": "中分", "score": 0.55},
            ]
        },
    )
    memory_ranked = PromptAssembler().format_context(
        "memory",
        {
            "results": [
                {"content": "旧记忆", "updated_at": _days_ago(120)},
                {"content": "新记忆", "updated_at": _days_ago(1)},
                {"content": "无时间戳记忆"},
            ]
        },
    )
    with _temporary_settings(CONTEXT_REF_NUMBERS_ENABLED=True):
        labeled_ranked = PromptAssembler().format_context(
            "rag",
            {
                "results": [
                    {"content": "低分", "score": 0.2},
                    {"content": "高分", "score": 0.9},
                ]
            },
        )
    with _temporary_settings(CONTEXT_RANK_SORT_ENABLED=False):
        rank_off = PromptAssembler().format_context(
            "rag",
            {
                "results": [
                    {"content": "低分", "score": 0.2},
                    {"content": "高分", "score": 0.9},
                ]
            },
        )
    no_rank_key = PromptAssembler().format_context(
        "rag", {"results": [{"content": "甲"}, {"content": "乙"}, {"content": "丙"}]}
    )
    if not (
        rag_ranked.index("高分") < rag_ranked.index("中分") < rag_ranked.index("低分")
    ):
        failures.append(f"rag 未按 score 降序：{rag_ranked!r}")
    if not (
        memory_ranked.index("无时间戳记忆")
        < memory_ranked.index("新记忆")
        < memory_ranked.index("旧记忆")
    ):
        failures.append(f"memory 未按时效降序/未 fail-open：{memory_ranked!r}")
    if fail_open_decay != 1.0:
        failures.append(f"缺失时间戳未按 fail-open 取值（应恰为 1.0）：{fail_open_decay!r}")
    if not (fail_open_decay > fresh_decay > stale_decay):
        failures.append(
            f"衰减未严格单调（无时间戳/一天前/120 天前）："
            f"{fail_open_decay!r}/{fresh_decay!r}/{stale_decay!r}"
        )
    if not labeled_ranked.startswith("[K2] 高分"):
        failures.append(f"排序后引用编号未取原始下标（与归因 A 脱钩）：{labeled_ranked!r}")
    if rank_off != "1. 低分\n2. 高分":
        failures.append(f"权重排序开关关闭未保持原序：{rank_off!r}")
    if no_rank_key != "1. 甲\n2. 乙\n3. 丙":
        failures.append(f"无排序依据时臆造了顺序：{no_rank_key!r}")

    # ⑤ 画像维度白名单与维度级优先级（§3.2 / §3.3 profile 行；v1.15.0 补入本判据）
    from app.api.openllm_gateway import _format_profile_ctx

    _small_profile = {
        "person": {"city": "上海", "preference": "简洁"},
        "business": {"company": "OpenBase"},
    }
    profile_default = _format_profile_ctx(_small_profile)
    with _temporary_settings(PROFILE_DIMENSION_LINES_ENABLED=False):
        profile_single_line = _format_profile_ctx(_small_profile)
    with _temporary_settings(PROFILE_DIMENSION_WHITELIST="preference,company"):
        profile_whitelisted = _format_profile_ctx(_small_profile)
    with _temporary_settings(PROFILE_DIMENSION_WHITELIST="nothing_matches"):
        profile_no_match = _format_profile_ctx(_small_profile)
    _big_profile = _format_profile_ctx(
        {
            "person": {"city": "上海" + "甲" * 20, "preference": "简洁" + "乙" * 20},
            "business": {"company": "OpenBase" + "丙" * 20, "scale": "200" + "丁" * 20},
        }
    )
    profile_prompt, profile_comp = build_prompt(
        query="问", profile_ctx=_big_profile, count_tokens=_chars, budget=_policy()
    )

    if len([x for x in profile_default.splitlines() if x.strip()]) != 5:
        failures.append(f"画像维度未独立成行（应 5 行：2 段头 + 3 维度）：{profile_default!r}")
    if profile_default.index("city") > profile_default.index("company"):
        failures.append(f"person 维度未优先于 business：{profile_default!r}")
    if len([x for x in profile_single_line.splitlines() if x.strip()]) != 2:
        failures.append(f"开关关闭未回退为单段一行：{profile_single_line!r}")
    if not (
        "preference" in profile_whitelisted
        and "company" in profile_whitelisted
        and "city" not in profile_whitelisted
    ):
        failures.append(f"白名单未按列出维度过滤：{profile_whitelisted!r}")
    if profile_no_match != "":
        failures.append(f"白名单无命中应返回空：{profile_no_match!r}")
    if "company" in profile_prompt or "city" not in profile_prompt:
        failures.append("超配额未丢弃低优先（business）维度")
    if profile_comp.budget["profile"]["used"] > profile_comp.budget["profile"]["quota"]:
        failures.append("画像维度裁剪后 used > quota")

    # ⑤' 画像**字段级**优先级（A1 / 题 8，本版补入本判据）
    #     动因：维度级行只把裁剪最小单位降到「维度」，同一 section **内**仍按「后出现先丢」
    #     ⇒ 字段之间无重要性区分。夹具刻意把低优先字段排在**前**：末位淘汰会保留它们，
    #     字段级优先级则保留高优先字段 ⇒ 两个开关态**可判别**（否则本判据形同虚设）。
    _field_profile = _format_profile_ctx(
        {
            "person": {
                "remark": "无",
                "nickname": "小张",
                "name": "张三",
                "occupation": "工程师",
            },
            "business": {"industry": "互联网", "size": "200"},
        }
    )

    def _field_quota_policy(quota: int, **overrides: Any) -> BudgetPolicy:
        """把 profile 段配额**精确设为 `quota`**（其余段 0 = 不限）"""
        return _policy(
            window_tokens=quota,
            quota_ratios={
                "system": 0.0,
                "profile": 1.0,
                "memory": 0.0,
                "rag": 0.0,
                "history": 0.0,
            },
            **overrides,
        )

    _fp_on_prompt, _fp_on_comp = build_prompt(
        query="问",
        profile_ctx=_field_profile,
        count_tokens=_chars,
        budget=_field_quota_policy(
            40,
            profile_field_priority_enabled=True,
            profile_field_priority=("name", "occupation"),
        ),
    )
    _fp_off_prompt, _fp_off_comp = build_prompt(
        query="问",
        profile_ctx=_field_profile,
        count_tokens=_chars,
        budget=_field_quota_policy(
            40,
            profile_field_priority_enabled=False,
            profile_field_priority=("name", "occupation"),
        ),
    )
    if "name: 张三" not in _fp_on_prompt or "occupation: 工程师" not in _fp_on_prompt:
        failures.append(f"字段级优先级未保留高优先字段：{_fp_on_prompt!r}")
    if "remark" in _fp_on_prompt or "nickname" in _fp_on_prompt:
        failures.append(f"字段级优先级未先丢未列入字段：{_fp_on_prompt!r}")
    if "[企业画像]" in _fp_on_prompt:
        failures.append(f"字段全丢的段头未移除（悬挂标签）：{_fp_on_prompt!r}")
    if _fp_on_comp.budget["profile"]["used"] > _fp_on_comp.budget["profile"]["quota"]:
        failures.append("字段级优先级裁剪后 used > quota")
    if "remark: 无" not in _fp_off_prompt:
        failures.append(f"开关关闭未逐字回退末位淘汰（低优先字段反被丢）：{_fp_off_prompt!r}")
    if _fp_off_comp.budget["profile"]["used"] > _fp_off_comp.budget["profile"]["quota"]:
        failures.append("关闭态裁剪后 used > quota")

    detail: dict[str, Any] = {
        "noise_stripped_text": stripped,
        "noise_verbatim_when_off": raw,
        "memory_merge_report": memory_report,
        "labeled_memory": labeled_memory,
        "labeled_rag": labeled_rag,
        "dedup_report": dedup_comp.truncated.get("memory"),
        "rank_order": {
            "rag": rag_ranked,
            "memory": memory_ranked,
            "labeled_ranked": labeled_ranked,
            "switch_off": rank_off,
            "no_rank_key": no_rank_key,
        },
        "rank_decay": {
            "fail_open_no_timestamp": fail_open_decay,
            "one_day_ago": fresh_decay,
            "one_twenty_days_ago": stale_decay,
            "half_life_days": 30.0,
        },
        "profile_dimensions": {
            "dimension_lines": profile_default,
            "single_line_fallback": profile_single_line,
            "whitelisted": profile_whitelisted,
            "whitelist_no_match": profile_no_match,
            "over_quota_report": profile_comp.truncated.get("profile"),
        },
        "profile_field_priority": {
            "priority_table": ["name", "occupation"],
            "enabled_at_quota_40": _fp_on_prompt,
            "disabled_at_quota_40": _fp_off_prompt,
            "over_quota_report": _fp_on_comp.truncated.get("profile"),
            "config_keys": _settings_snapshot(
                [
                    "CONTEXT_PROFILE_FIELD_PRIORITY_ENABLED",
                    "CONTEXT_PROFILE_FIELD_PRIORITY",
                ]
            ),
        },
        "ref_numbers_switch_default": _settings_snapshot(["CONTEXT_REF_NUMBERS_ENABLED"]),
        "evidence": (
            "`tests/unit/test_assembly_refine_rule_tier.py`（27 例）＋ "
            "`tests/unit/test_context_rank_selection.py`（12 例）＋ "
            "`tests/unit/test_profile_dimension_priority.py`（29 例：维度级 9 ＋ "
            "字段级 20）＋ 运行态探针 "
            "`doc/test/evidence/cr149/assembly_rule_tier_probe.py`"
        ),
    }
    return Verdict(
        criterion="T10",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail=detail,
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T11 写路径与通道一致

async def check_t11() -> Verdict:
    """T11：写路径与通道一致（`assert_write_channel_is_primary` 接线；v1.15.0）

    方案 §4.3 表「写路径与通道一致」＋ §8 风险回退：「回写前经
    `assert_write_channel_is_primary` 校验，避免通道切换期间双写」。

    **进程内可判**（真实回写回调 + 队列替身，不依赖运行态服务）：

      1. 默认主通道（`b-primary`）⇒ 三路正常入队（**行为不变**）；
      2. 切换期间（`a-primary`，经 B 写属非主通道）⇒ **暂停本轮回写**
         （三路返回 `"skipped"` 且**不入队**）；
      3. 开关关闭 ⇒ **逐字回退**（不看通道状态）；
      4. 配置非法（未知 preference）⇒ WARN + **放行**（fail-open）；
      5. **自动回落（Q5 触发权 · 可选开态）**：源 1 组件级连续失败达阈值
         ⇒ 自动接管 A ⇒ **同走单主断言**（写路径同样暂停，三路 `"skipped"` 不入队）。
    """
    title = "写路径与通道一致：非主通道期间暂停回写（进程内可判）"
    import app.api.openllm_gateway as gateway
    import app.services.writeback_queue as queue_module

    _queue_stub_ref = _QueueStub
    _identity_ref = _IdentityStub

    async def _run(**overrides: Any) -> tuple[list[str], dict[str, Any]]:
        queue = _queue_stub_ref()
        original = queue_module.get_writeback_queue
        queue_module.get_writeback_queue = lambda: queue
        try:
            with _temporary_settings(WRITEBACK_DECISION_ENABLED=False, **overrides):
                memory_cb, rag_cb, profile_cb, _kwargs = gateway._build_writeback_callback(
                    _identity_ref(), "req-t11", session_id="sess-t11", rag_kb_id="kb-t11"
                )
                returns: dict[str, Any] = {}
                for road, callback in (
                    ("memory", memory_cb),
                    ("rag", rag_cb),
                    ("profile", profile_cb),
                ):
                    returns[road] = await callback(query="请记住：我偏好简洁", response="好的")
        finally:
            queue_module.get_writeback_queue = original
        return [item["target"] for item in queue.submitted], returns

    default_submitted, _default_returns = await _run()
    guarded_submitted, guarded_returns = await _run(CHANNEL_PREFERENCE="a-primary")
    off_submitted, _off_returns = await _run(
        WRITEBACK_CHANNEL_GUARD_ENABLED=False, CHANNEL_PREFERENCE="a-primary"
    )
    invalid_submitted, _invalid_returns = await _run(CHANNEL_PREFERENCE="b_primary_typo")

    # ⑤ Q5 自动回落同走单主断言：源 1 组件级连续失败达阈值 ⇒ 自动接管 A ⇒ 写暂停
    async def _run_auto_failover() -> tuple[list[str], dict[str, Any], str]:
        import app.identity.channel as channel_module

        queue = _queue_stub_ref()
        original = queue_module.get_writeback_queue
        queue_module.get_writeback_queue = lambda: queue
        try:
            with _temporary_settings(
                WRITEBACK_DECISION_ENABLED=False,
                WRITEBACK_CHANNEL_GUARD_ENABLED=True,
                CHANNEL_PREFERENCE="b-primary",
                CHANNEL_AUTO_FAILOVER_ENABLED=True,
                CHANNEL_FAILOVER_CONSECUTIVE_THRESHOLD=3,
            ):
                channel_module.reset_channel_state_manager()
                auto_manager = gateway._get_channel_manager()
                for _ in range(3):
                    gateway._note_component_channel_health(
                        type(
                            "Run",
                            (),
                            {
                                "degraded": ["rag"],
                                "rag_source": "external",
                                "builtin_fallback_reason": "",
                            },
                        )()
                    )
                primary_after = auto_manager.primary_channel
                memory_cb, rag_cb, profile_cb, _kwargs = gateway._build_writeback_callback(
                    _identity_ref(), "req-t11-auto", session_id="sess-t11", rag_kb_id="kb-t11"
                )
                returns: dict[str, Any] = {}
                for road, callback in (
                    ("memory", memory_cb),
                    ("rag", rag_cb),
                    ("profile", profile_cb),
                ):
                    returns[road] = await callback(query="请记住：我偏好简洁", response="好的")
        finally:
            queue_module.get_writeback_queue = original
            channel_module.reset_channel_state_manager()
        return [item["target"] for item in queue.submitted], returns, primary_after

    auto_failover_submitted, auto_failover_returns, auto_failover_primary = (
        await _run_auto_failover()
    )

    failures: list[str] = []
    if sorted(default_submitted) != ["memory", "profile", "rag"]:
        failures.append(f"默认主通道下三路应正常入队，实测 {default_submitted}")
    if guarded_submitted:
        failures.append(f"非主通道期间不得写入，实测入队 {guarded_submitted}")
    if not all(value == "skipped" for value in guarded_returns.values()):
        failures.append(f"非主通道期间三路应返回 skipped，实测 {guarded_returns}")
    if "memory" not in off_submitted:
        failures.append("开关关闭时应逐字回退（不看通道状态）")
    if "memory" not in invalid_submitted:
        failures.append("配置非法时应 fail-open 放行（不得静默停库）")
    if auto_failover_primary != "a":
        failures.append(f"自动回落（开态达阈值）应达 A 主，实测 {auto_failover_primary}")
    if auto_failover_submitted:
        failures.append(
            f"自动接管 A 期间不得写入（同走单主断言），实测入队 {auto_failover_submitted}"
        )
    if not all(value == "skipped" for value in auto_failover_returns.values()):
        failures.append(
            f"自动接管 A 期间三路应返回 skipped，实测 {auto_failover_returns}"
        )

    return Verdict(
        criterion="T11",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "default_primary_submitted": default_submitted,
            "channel_switch_submitted": guarded_submitted,
            "channel_switch_returns": guarded_returns,
            "guard_switch_off_submitted": off_submitted,
            "invalid_preference_submitted": invalid_submitted,
            "auto_failover_primary": auto_failover_primary,
            "auto_failover_submitted": auto_failover_submitted,
            "auto_failover_returns": auto_failover_returns,
            "evidence": (
                "`tests/unit/test_writeback_channel_guard.py`（8 例）＋ 运行态探针 "
                "`doc/test/evidence/cr149/writeback_channel_guard_probe.py`；"
                "Q5 自动回落联动见 `tests/unit/test_channel_wiring_health.py::"
                "TestAutoFailoverTriggerChain`（7 例）＋ 探针 `channel_auto_failover_probe.py`（10 例）"
            ),
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T12 精炼触发与护栏

def check_t12() -> Verdict:
    """T12：精炼触发条件（§5.2 行 1~3）与输出护栏（§5.3 判定部分）—— **纯进程内可判**

    - §5.2 行 1：`memory`/`rag` 段 token > 配额 × **1.5**（**严格大于** ⇒ 恰为 1.5 倍不触发）；
    - §5.2 行 2：单段条目数 > **8**（恰为 8 不触发）；
    - §5.2 行 3：段内相似度 > **0.85** 的条目**占比** > **30%**；
    - §5.2 行 4：**多源冲突 = 未实施** —— 须由 `unimplemented` 显式列出，**不得伪实现**；
    - §5.3：逐条可定位 / 不得引入新数值 / 须编号列表 / 空输出非法 ⇒ 违规即弃；
    - §2 原则 6：触发判定是**只读观测**（开关两态注入文本**逐字相同**）。
    """
    title = "精炼：触发条件（§5.2 行 1~3）与输出护栏（§5.3）进程内可判；行 4 如实标注未实施"
    from app.edgerouter.orchestration import refine as refine_module
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    def _chars(text: str) -> int:
        return len(text or "")

    def _items(*bodies: str) -> str:
        return "\n".join(f"{i}. {body}" for i, body in enumerate(bodies, start=1))

    policy = BudgetPolicy(
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

    def _trigger(segments: dict[str, str]) -> dict[str, Any]:
        return refine_module.refine_triggers(segments, policy=policy, count_tokens=_chars)

    sources = [
        "项目预算上限为 120 万元，由财务部在 3 月核定。",
        "用户偏好简洁回答，不喜欢冗长解释。",
        "部署环境使用 Docker Compose，端口 8080。",
    ]
    row1_hit = _trigger({"memory": _items("甲" * 157)})
    row1_edge = _trigger({"memory": _items("甲" * 147)})
    row1_other = _trigger({"history": _items("历" * 300)})
    row2_hit = _trigger({"memory": _items(*[f"条目{i}" for i in range(9)])})
    row2_edge = _trigger({"memory": _items(*[f"条目{i}" for i in range(8)])})
    row3_hit = _trigger(
        {"memory": _items("用户偏好简洁回答", "用户偏好简洁回答风格", "项目用 Python", "部署用 Docker")}
    )
    row3_edge = _trigger(
        {
            "memory": _items(
                "用户偏好简洁回答",
                "用户偏好简洁回答风格",
                *[f"第{i}条截然不同的内容" for i in range(6)],
            )
        }
    )
    row4_probe = _trigger({"memory": _items("预算代号 A1"), "rag": _items("预算代号 A2")})
    guard_ok = refine_module.validate_refine_output(
        ["1. 项目预算上限为 120 万元，由财务部在 3 月核定。", "2. 用户偏好简洁回答，不喜欢冗长解释。"],
        sources=sources,
    )
    guard_rewrite = refine_module.validate_refine_output(
        ["1. 项目预算由财务部每月复核一次。"], sources=sources
    )
    guard_number = refine_module.validate_refine_output(
        ["1. 部署环境使用 Docker Compose，端口 9090。"], sources=sources
    )
    guard_empty = refine_module.validate_refine_output([], sources=sources)
    guard_unnumbered = refine_module.validate_refine_output(
        ["项目预算上限为 120 万元，由财务部在 3 月核定。"], sources=sources
    )

    memory = _items("甲" * 200)
    with _temporary_settings(CONTEXT_REFINE_TRIGGER_ENABLED=False):
        prompt_off, comp_off = build_prompt(
            query="问", memory_ctx=memory, count_tokens=_chars, budget=policy
        )
    with _temporary_settings(CONTEXT_REFINE_TRIGGER_ENABLED=True):
        prompt_on, comp_on = build_prompt(
            query="问", memory_ctx=memory, count_tokens=_chars, budget=policy
        )

    failures: list[str] = []
    if "over_quota:memory" not in row1_hit["reasons"]:
        failures.append(f"行 1 未触发：{row1_hit['reasons']}")
    if row1_edge["triggered"]:
        failures.append("行 1 阈值语义错误（恰为 1.5 倍不应触发）")
    if row1_other["triggered"]:
        failures.append("行 1 越界（§5.2 仅列 memory/rag）")
    if "too_many_items:memory" not in row2_hit["reasons"]:
        failures.append(f"行 2 未触发：{row2_hit['reasons']}")
    if row2_edge["triggered"]:
        failures.append("行 2 阈值语义错误（恰为 8 条不应触发）")
    if "high_duplication:memory" not in row3_hit["reasons"]:
        failures.append(f"行 3 未触发：{row3_hit['reasons']}")
    if row3_edge["triggered"]:
        failures.append("行 3 阈值语义错误（25% 占比不应触发）")
    if row4_probe["reasons"] or "multi_source_conflict" not in row4_probe["unimplemented"]:
        failures.append("行 4 未如实标注为未实施（或伪实现为理由）")
    if any("conflict" in reason for reason in refine_module.TRIGGER_REASONS):
        failures.append("行 4 被伪实现（触发理由词表不应含 conflict 类）")
    if not guard_ok["valid"] or guard_ok["located"] != [0, 1]:
        failures.append(f"护栏误判合法抽取：{guard_ok}")
    if guard_rewrite["valid"]:
        failures.append("护栏未拦截改写（unlocatable）")
    if guard_number["valid"]:
        failures.append("护栏未拦截新增数值（new_numbers）")
    if guard_empty["valid"]:
        failures.append("护栏未拦截空输出（empty_output）")
    if guard_unnumbered["valid"]:
        failures.append("护栏未拦截非编号输出（not_numbered）")
    if prompt_on != prompt_off or comp_on.prompt_total_tokens != comp_off.prompt_total_tokens:
        failures.append("触发判定改变了注入内容（违反观测与判定分离）")
    if comp_off.refine_trigger != {} or not comp_on.refine_trigger:
        failures.append("触发观测落痕开关语义错误")

    return Verdict(
        criterion="T12",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "row1_over_quota": {"hit": row1_hit, "edge_1_5x": row1_edge, "history_ignored": row1_other},
            "row2_item_count": {"hit": row2_hit, "edge_8": row2_edge},
            "row3_duplication": {"hit_50pct": row3_hit, "edge_25pct": row3_edge},
            "row4_unimplemented": row4_probe,
            "guard": {
                "verbatim": guard_ok,
                "rewrite": guard_rewrite,
                "new_number": guard_number,
                "empty": guard_empty,
                "unnumbered": guard_unnumbered,
            },
            "observation_separation": {
                "prompt_identical": prompt_on == prompt_off,
                "tokens_identical": comp_on.prompt_total_tokens == comp_off.prompt_total_tokens,
            },
            "evidence": (
                "`tests/unit/test_refine_trigger_and_guard.py`（22 例）＋ 运行态探针 "
                "`doc/test/evidence/cr149/refine_trigger_probe.py`"
            ),
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- 执行入口

# ---------------------------------------------------------------- T13 LLM 不可达判定与告知

def check_t13() -> Verdict:
    """T13（**W1 / Q12，v1.29.0 新增**）：最终 LLM 不可达的**判定**与**对调用方的告知**

    **判据原文（Q12 裁定）**：A 通道降级接管的**触发条件＝最终 LLM 不可达**，此时**由调用方
    改走 A 直连**（经 OpenBase 分别单独调用 DPS / OpenMemory / OpenRAG，不经编排）
    ⇒ OpenLLM 的职责是**判定** ＋ **明确告知**（**不静默降级**）。

    **进程内可判的四条契约**：

      1. **告警即时、状态判定按阈值**（两者**语义不同**不得混同）：单次 LLM 全部失败 ⇒
         「失败时通知」（`action_scope="per_failure"`）**立即**给出 `use_a_direct`；
         而**状态判定** `llm_unreachable` 仍 `False`，**连续达阈值**才为 `True`。
      2. **健康口径并入终点**：`b_health()["healthy"]` 在不可达时为 `False`
         —— 「**不可用**」与组件降级的「可用但劣化」有本质区别。
      3. **不污染既有触发链**：终点**独立计数** ⇒ `evaluate_auto_failover()` 语义**不变**
         （LLM 失败**不**触发 OpenLLM 侧 B→A 接管 —— 后者管主通道 designation、前者管
         **Agent 读路径**，两机制分工不同）；`channel_status()` 暴露
         `llm_unreachable` / `llm_consecutive_failures` / `fallback_action`（状态字段）。
      4. **可机读告知**：带指示的错误响应**额外**给出 `data.channel`；**无指示时形态逐字不变**
         （不给所有 5xx 都加该段，避免误导）。
    """
    title = "LLM 不可达：判定按阈值、告知即时可机读、不污染既有触发链（进程内可判）"
    from app.api.openllm_gateway import GatewayError, _error_response
    from app.identity.channel import (
        FALLBACK_ACTION_NONE,
        FALLBACK_ACTION_USE_A_DIRECT,
        ChannelStateManager,
        describe_llm_unreachable_hint,
    )

    def _manager(threshold: int = 3) -> Any:
        return ChannelStateManager(
            "b-primary",
            consecutive_failure_threshold=threshold,
            drill_window_seconds=300.0,
            auto_failover_enabled=True,
        )

    failures: list[str] = []
    reason = "RuntimeError: OpenLLM 端点不可达"

    # ① 告警即时（通知）vs 判定按阈值（状态）
    single = _manager()
    single.record_b_llm_unavailable(reason=reason)
    single_hint = single.llm_unreachable_hint(reason=reason)
    if single_hint["fallback_action"] != FALLBACK_ACTION_USE_A_DIRECT:
        failures.append("单次失败应**立即**给出 use_a_direct（调用方当次即需知道改走哪条路）")
    if single_hint.get("action_scope") != "per_failure":
        failures.append("通知须显式标注作用域 per_failure（与状态字段区分）")
    if single_hint["llm_unreachable"] is not False:
        failures.append("未达阈值不得宣告不可达（避免单次抖动）")
    if single.channel_status()["fallback_action"] != FALLBACK_ACTION_NONE:
        failures.append("未达阈值时**状态**动作应为 none（状态与通知语义不同）")

    # ② 达阈值 ⇒ 判定 + 健康并入
    reached = _manager()
    for _ in range(3):
        reached.record_b_llm_unavailable(reason=reason)
    if not reached.llm_unreachable():
        failures.append("连续达阈值应判 llm_unreachable=True")
    if reached.b_health()["healthy"] is not False:
        failures.append("LLM 不可达即 B **不可用** ⇒ b_health().healthy 须为 False")
    if reached.channel_status()["fallback_action"] != FALLBACK_ACTION_USE_A_DIRECT:
        failures.append("不可达时**状态**动作应为 use_a_direct")

    # ③ 恢复 ⇒ 判定与状态动作复原
    recovered = _manager()
    for _ in range(3):
        recovered.record_b_llm_unavailable(reason=reason)
    recovered.record_b_llm_success()
    if recovered.llm_unreachable() or (
        recovered.channel_status()["fallback_action"] != FALLBACK_ACTION_NONE
    ):
        failures.append("终点恢复后判定与状态动作须复原")

    # ④ 不污染既有触发链
    polluted = _manager()
    for _ in range(5):
        polluted.record_b_llm_unavailable(reason=reason)
    if polluted.b_health()["consecutive_failures"] != 0:
        failures.append("终点失败**不得**并入组件连续失败计数（会改变既有触发语义）")
    if polluted.evaluate_auto_failover() is not False:
        failures.append("LLM 失败**不得**触发既有 B→A 自动接管（两机制分工不同）")
    if polluted.primary_channel != "b":
        failures.append("既有自动接管未触发时主通道应保持 b")

    # ⑤ 可机读告知：带指示 ⇒ 有 data.channel；无指示 ⇒ 形态逐字不变
    with_hint = GatewayError(5001, "模型服务暂时不可用")
    with_hint.channel_hint = describe_llm_unreachable_hint(
        primary_channel="b", consecutive=1, threshold=3, reason=reason
    )
    payload_with = json.loads(_error_response(with_hint, "req-t13").body)
    if payload_with.get("data", {}).get("channel", {}).get("fallback_action") != (
        FALLBACK_ACTION_USE_A_DIRECT
    ):
        failures.append(f"带指示的错误响应须携带 data.channel：{payload_with}")
    payload_without = json.loads(
        _error_response(GatewayError(5001, "RAG 服务不可用"), "req-t13b").body
    )
    if set(payload_without) != {"code", "message", "detail", "request_id"}:
        failures.append(f"无指示的错误响应形态须**逐字不变**：{sorted(payload_without)}")

    return Verdict(
        criterion="T13",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "single_failure_notify_hint": single_hint,
            "single_failure_state_action": single.channel_status()["fallback_action"],
            "reached_health": reached.b_health(),
            "reached_state_action": reached.channel_status()["fallback_action"],
            "unpolluted_health": polluted.b_health(),
            "auto_failover_on_llm_failures": polluted.evaluate_auto_failover(),
            "channel_status_keys": sorted(reached.channel_status()),
            "error_payload_with_hint": payload_with,
            "error_payload_without_hint": payload_without,
            "probe_evidence": (
                "`doc/test/evidence/cr149/llm_unreachable_probe.py`（6 例判定表 ＋ 结尾自检）"
            ),
            "unit_evidence": "`tests/unit/test_channel_llm_unreachable.py`（19 例护栏）",
        },
        reason="；".join(failures),
    )


def check_t14() -> Verdict:
    """T14（**W4 / v1.30.0 新增**）：双通道健康/降级**统一上报** —— 一份事实源 ＋ 单一结论

    **判据（三条纪律，进程内可判）**：

      1. **只聚合、不立新判据** —— `describe_channel_report()` 的全部字段可由
         `ChannelStateManager` 事实（`channel_status` / `b_health` / `a_health` /
         `primary_channel`）＋ 组件探测结果**逐项推出**；不引入任何新阈值/计数。
      2. **单一决策规则** —— `bypass_orchestration` 当且仅当「**主通道已为 A**」**或**
         「主通道为 B **且** 最终 LLM 不可达」；穷举（主通道 × 终点状态）恒等。
      3. **观测与决策分离** —— 组件降级**如实列入** `degraded_dimensions`（不隐瞒劣化），
         但**结论仍是走主通道**（不因噪声误切通道）；`fallback_action` 与
         `channel_status()` **同源**（错误响应里的指示与 health 里的结论**永不冲突**）。
    """
    title = "双通道统一上报：三视角聚合 ＋ 单一结论、观测与决策分离（进程内可判）"
    from app.identity.channel import (
        CHANNEL_A,
        CHANNEL_B,
        ROUTING_USE_A_DIRECT,
        ROUTING_USE_PRIMARY,
        ChannelStateManager,
        describe_channel_report,
    )

    def _manager(threshold: int = 3) -> Any:
        return ChannelStateManager(
            "b-primary",
            consecutive_failure_threshold=threshold,
            drill_window_seconds=300.0,
            auto_failover_enabled=True,
        )

    failures: list[str] = []
    reason = "RuntimeError: OpenLLM 端点不可达"

    # ① 基线：三视角齐备 ＋ 单一结论
    base = describe_channel_report(_manager(), components={"openrag": {"status": "ok", "channel": CHANNEL_B}})
    if set(base["channels"]) != {CHANNEL_A, CHANNEL_B}:
        failures.append(f"报告须含两条通道视角：{sorted(base['channels'])}")
    if base["bypass_orchestration"] is not False or (
        base["routing_recommendation"] != ROUTING_USE_PRIMARY
    ):
        failures.append("无异常时结论应为走主通道")
    if base["degraded_dimensions"] != []:
        failures.append(f"无异常时不得有降级维度：{base['degraded_dimensions']}")

    # ② 只聚合：与事实源逐项相等（防暗增判据）
    facts = _manager(threshold=2)
    facts.record_b_component_failure("dps", reason="x")
    facts.record_b_llm_unavailable(reason=reason)
    report = describe_channel_report(facts)
    status = facts.channel_status()
    if report["fallback_action"] != status["fallback_action"]:
        failures.append("fallback_action 须与 channel_status() 同源（不得复制判定逻辑）")
    if report["channels"][CHANNEL_B]["consecutive_failures"] != (
        facts.b_health()["consecutive_failures"]
    ):
        failures.append("B 组件连续失败须与 b_health() 一致")
    if report["channels"][CHANNEL_B]["llm_consecutive_failures"] != (
        facts.b_health()["llm_consecutive_failures"]
    ):
        failures.append("终点连续失败须与 b_health() 一致")
    if report["channels"][CHANNEL_A]["healthy"] != facts.a_health()["healthy"]:
        failures.append("A 侧健康须与 a_health() 一致")
    if report["primary_channel"] != facts.primary_channel:
        failures.append("主通道须与 manager 一致")

    # ③ 观测与决策分离（**核心契约**）：组件降级如实列入但**不改变结论**
    degraded = _manager(threshold=2)
    for _ in range(2):
        degraded.record_b_component_failure("rag", reason="x")
    degraded_report = describe_channel_report(
        degraded, components={"openrag": {"status": "unavailable", "channel": CHANNEL_B}}
    )
    if f"{CHANNEL_B}.components" not in degraded_report["degraded_dimensions"]:
        failures.append("B 组件维度降级须如实列入 degraded_dimensions（不得隐瞒劣化）")
    if f"{CHANNEL_B}.component.openrag" not in degraded_report["degraded_dimensions"]:
        failures.append("组件级劣化须逐名列入 degraded_dimensions")
    if degraded_report["bypass_orchestration"] is not False:
        failures.append("组件降级＝**可用但劣化** ⇒ **不得**因组件噪声切走编排")

    # ④ A 侧达阈值失败：列入证据，但 B 主时**不**改变决策
    a_failed = _manager(threshold=3)
    for _ in range(3):
        a_failed.record_a_failure(reason="A 侧探活失败")
    a_report = describe_channel_report(a_failed)
    if f"{CHANNEL_A}.components" not in a_report["degraded_dimensions"]:
        failures.append("A 侧达阈值失败须如实列入 degraded_dimensions")
    if a_report["bypass_orchestration"] is not False:
        failures.append("B 主时 A 断不改变主通道")

    # ⑤ 终点不可达（达阈值）⇒ 改走 A 直连；未达阈值 ⇒ 不改走
    unreachable = _manager(threshold=3)
    for _ in range(3):
        unreachable.record_b_llm_unavailable(reason=reason)
    unreachable_report = describe_channel_report(unreachable)
    if unreachable_report["bypass_orchestration"] is not True or (
        unreachable_report["routing_recommendation"] != ROUTING_USE_A_DIRECT
    ):
        failures.append("最终 LLM 不可达 ⇒ 结论须为改走 A 直连（Q12 口径）")
    if f"{CHANNEL_B}.llm" not in unreachable_report["degraded_dimensions"]:
        failures.append("终点不可达须如实列入 degraded_dimensions")

    below = _manager(threshold=3)
    below.record_b_llm_unavailable(reason=reason)
    below_report = describe_channel_report(below)
    if below_report["bypass_orchestration"] is not False or (
        below_report["degraded_dimensions"] != []
    ):
        failures.append("终点失败未达阈值 ⇒ 不得改走、不得列降级（状态判定按阈值）")

    # ⑥ 穷举（主通道 × 终点状态）⇒ bypass 恒等于单一决策规则
    exhaustive_mismatch: list[str] = []
    for primary in (CHANNEL_B, CHANNEL_A):
        for llm_failures in (0, 3):
            manager = _manager(threshold=3)
            if primary == CHANNEL_A:
                manager.trigger_failover_to_a(source="manual", reason="演练", actor="ops")
            for _ in range(llm_failures):
                manager.record_b_llm_unavailable(reason=reason)
            combo = describe_channel_report(manager)
            expected = primary == CHANNEL_A or (primary == CHANNEL_B and llm_failures >= 3)
            if combo["bypass_orchestration"] is not expected:
                exhaustive_mismatch.append(f"primary={primary}/llm={llm_failures}")
    if exhaustive_mismatch:
        failures.append(f"穷举组合与单一决策规则不符：{exhaustive_mismatch}")

    return Verdict(
        criterion="T14",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "baseline_report": base,
            "facts_report": report,
            "degraded_report": degraded_report,
            "a_side_report": a_report,
            "unreachable_report": unreachable_report,
            "below_threshold_report": below_report,
            "exhaustive_mismatch": exhaustive_mismatch,
            "probe_evidence": (
                "`doc/test/evidence/cr149/channel_report_probe.py`（7 例判定表 ＋ 4 组合穷举 ＋ 结尾自检）"
            ),
            "unit_evidence": "`tests/unit/test_channel_report.py`（16 例护栏）",
        },
        reason="；".join(failures),
    )


def check_t15() -> Verdict:
    """T15（**W2 / v1.31.0 新增**）：**A 直连三组件取数** —— 三组件均可经 A 直连**取到数据**

    **判据（W2；《收口方案》v1.5.0 §1.1.4 题 14）**：A ＝ **直连拓扑**（**不经编排**，单独调用
    三基础设施）⇒ 三组件（DPS 画像 / OpenMemory 记忆 / OpenRAG 知识库）经 A 直连**均确实取到
    数据**（Q8 **内容口径**：「回落 / 回退后**必须确实能取到数据**」），而非「调用成功但为空」。

    **四条子句**：

      1. **取数非空** —— 种入后经 A 直连接读**确实取到数据**。
      2. **空态如实** —— 未种入时**如实返回 0 条**（不以空充数、不伪造数据）。
      3. **写读闭环** —— 「组件自身写入接口 → A 直连读取」闭环一致。
      4. **直连拓扑身份面完整** —— A 直连来源＝`openbase-llm-proxy`（B 为 `openbase-orchestrator`，
         **拓扑不同是设计允许的**），且与 B 通道**身份四头等价**（AC-T13-2）。

    **承载与边界（如实登记，不伪 PASS）**：本判据由**同一份探针**驱动
    （`a_direct_component_probe.build_cases()`，**避免判据与探针分叉**），本地以三组件
    `mock_services/*_stub` **进程内**承载（`TestClient`，零网络）⇒ 证明「**A 直连取数链路结构
    贯通且确实取到数据**」；**真实外部服务联调**（生产 DPS / OpenMemory / OpenRAG ＋
    `OPENLLM_*_REAL=true`）仍属**运行态复核项**，在 `detail.runtime_pending` **显式列出**。
    """
    title = "A 直连三组件取数：三组件均可经 A 直连取到数据（进程内承载；真实服务联调留运行态）"
    evidence_dir = os.path.dirname(os.path.abspath(__file__))
    if evidence_dir not in sys.path:
        sys.path.insert(0, evidence_dir)
    try:
        import a_direct_component_probe as probe  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return Verdict(
            criterion="T15",
            title=title,
            status=STATUS_BLOCKED,
            detail={"blocked_reason": f"探针不可加载：{type(exc).__name__}: {exc}"},
            reason="A 直连探针依赖（httpx/TestClient 或三组件 stub）不可用 ⇒ 属环境前置缺失",
        )

    try:
        cases = probe.build_cases()
    except Exception as exc:  # noqa: BLE001
        return Verdict(
            criterion="T15",
            title=title,
            status=STATUS_BLOCKED,
            detail={"blocked_reason": f"探针执行失败：{type(exc).__name__}: {exc}"},
            reason="A 直连取数不可在进程内执行（承载不可用）⇒ 属环境前置缺失",
        )

    failures: list[str] = []
    by_component: dict[str, dict] = {}
    for item in cases:
        by_component[item["component"]] = {
            "endpoint_read": item.get("endpoint_read"),
            "endpoint_seed": item.get("endpoint_seed"),
            "empty_total": item.get("empty_total"),
            "retrieved_total": item.get("retrieved_total"),
            "checks": item["checks"],
            "ok": item["ok"],
        }
        bad = [name for name, ok in item["checks"].items() if not ok]
        if bad:
            failures.append(f"{item['component']} 子句不符：{bad}")

    # 三组件**逐个**须齐备（缺一即不达标）
    for required in ("OpenMemory（记忆）", "OpenRAG（知识库）", "DPS（画像）"):
        if required not in by_component:
            failures.append(f"缺 {required} 的 A 直连接读证据")

    return Verdict(
        criterion="T15",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "components": by_component,
            "carrier": "mock_services/{openmemory,openrag,profile}_stub（进程内 TestClient，零网络）",
            "runtime_pending": (
                "真实外部服务（生产 DPS / OpenMemory / OpenRAG）联调与真实契约路由"
                "（`OPENLLM_*_REAL=true`）仍属运行态复核项 —— 本判据不据此宣称生产已贯通"
            ),
            "probe_evidence": (
                "`doc/test/evidence/cr149/a_direct_component_probe.py`"
                "（4 例判定表 ＋ 结尾自检；本判据**复用同一 `build_cases()`** 防分叉）"
            ),
        },
        reason="；".join(failures),
    )


def check_t16() -> Verdict:
    """T16（**装配保真度对照 / v1.33.0 新增**）：智能体原文 ⇄ 最终投喂上下文**两端可对照**

    **判据（用户口径，2026-09-28）**：需要对比「智能体发起的对话原文」与「最终投喂给 LLM 的
    上下文」的异同，据此调整装配流程与装配方案，**确保不失真地反馈用户真实意图**。

    **七条子句（同一份探针驱动，防判据与探针分叉）**：

      ① **逐字保留即 `intact`**（无注入/裁剪时信号为空）；
      ② **被改写 ⇒ `mutated` ＋ `query_rewritten`**（**意图失真信号**）；
      ③ **缺 `[用户问题]` 段 ⇒ `missing` ＋ `query_absent`**（装配丢问题，最严重失真）；
      ④ **历史裁剪可见** ⇒ `turns_dropped > 0` ＋ `history_truncated`（设计行为，但**必须可见**）；
      ⑤ **凭据不出模块** ⇒ 落库文本中敏感串不出现（掩码生效）；
      ⑥ **有界** ⇒ 超长截断并标注 `truncated_for_capture`；
      ⑦ **开关两态** ⇒ 关闭返回 `None`（**逐字回退**，回执不新增字段）、开启返回完整记录。

    **边界（如实登记）**：判定基于**原文**（真值）；落库文本**掩码 ＋ 有界** ⇒ 默认关闭时
    既有安全红线 AC-148-01-5 的默认形态**逐字不变**；本判据**不据此宣称真实链路的对照已抽样**。
    """
    title = "装配保真度对照：两端可对照 ＋ 失真可判（默认关闭、掩码有界；进程内可判）"
    evidence_dir = os.path.dirname(os.path.abspath(__file__))
    if evidence_dir not in sys.path:
        sys.path.insert(0, evidence_dir)
    try:
        import fidelity_capture_probe as probe  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return Verdict(
            criterion="T16",
            title=title,
            status=STATUS_BLOCKED,
            detail={"blocked_reason": f"探针不可加载：{type(exc).__name__}: {exc}"},
            reason="保真度对照探针依赖不可用 ⇒ 属环境前置缺失",
        )

    try:
        cases = [*probe.build_cases(), probe._switch_case()]
    except Exception as exc:  # noqa: BLE001
        return Verdict(
            criterion="T16",
            title=title,
            status=STATUS_BLOCKED,
            detail={"blocked_reason": f"探针执行失败：{type(exc).__name__}: {exc}"},
            reason="保真度对照不可在进程内执行 ⇒ 属环境前置缺失",
        )

    failures: list[str] = []
    details: list[dict] = []
    for item in cases:
        bad = [name for name, ok in item["checks"].items() if not ok]
        details.append(
            {"case": item["case"], "verdict": item["verdict"], "flags": item["flags"], "bad": bad}
        )
        if bad:
            failures.append(f"{item['case']} 子句不符：{bad}")

    # 七条子句须**逐条齐备**（数量不足即视为覆盖缺失，不放过）
    if len(cases) < 7:
        failures.append(f"判定表例数不足（{len(cases)} < 7）⇒ 子句覆盖缺失")

    return Verdict(
        criterion="T16",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        detail={
            "cases": details,
            "switch_off_returns_none": "见 ⑦（关闭 ⇒ None，逐字回退）",
            "masked_and_bounded": "见 ⑤（掩码）／⑥（有界截断）",
            "runtime_pending": (
                "**真实链路**的两端对照抽样（开启开关后发请求 → 导出 → 出报告）属**运行态复核项**；"
                "本判据只证明契约与判定在进程内成立，**不据此宣称已对真实流量抽样**"
            ),
            "tooling": (
                "对照报告工具 `doc/test/evidence/cr149/fidelity_diff_report.py`"
                "（`--capture` 读导出产物 / `--demo` 合成样本 / `--strict` 门禁）"
            ),
            "probe_evidence": (
                "`doc/test/evidence/cr149/fidelity_capture_probe.py`"
                "（7 例判定表 ＋ 结尾自检；本判据**复用同一 `build_cases()`** 防分叉）"
            ),
            "unit_evidence": "`tests/unit/test_fidelity_capture.py`（**20 例**护栏）",
        },
        reason="；".join(failures),
    )


SYNC_CHECKS: list[tuple[str, Callable[[], Verdict]]] = [
    ("T1", check_t1),
    ("T2", check_t2),
    ("T3", check_t3),
    ("T6", check_t6),
    ("T9", check_t9),
    ("T10", check_t10),
    ("T12", check_t12),
    ("T13", check_t13),
    ("T14", check_t14),
    ("T15", check_t15),
    ("T16", check_t16),
]

ASYNC_CHECKS: list[tuple[str, Callable[[], Any]]] = [
    ("T4", check_t4),
    ("T5", check_t5),
    ("T7", check_t7),
    ("T8", check_t8),
    ("T11", check_t11),
]


def run_all() -> list[Verdict]:
    verdicts: list[Verdict] = []
    for _criterion, check in SYNC_CHECKS:
        try:
            verdicts.append(check())
        except Exception as exc:  # noqa: BLE001 - 单条判据异常不得中断整轮
            verdicts.append(
                Verdict(
                    criterion=_criterion,
                    title="(检查异常)",
                    status=STATUS_FAIL,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
    for criterion, check in ASYNC_CHECKS:
        try:
            verdicts.append(asyncio.run(check()))
        except Exception as exc:  # noqa: BLE001 - 单条判据异常不得中断整轮
            verdicts.append(
                Verdict(
                    criterion=criterion,
                    title="(检查异常)",
                    status=STATUS_FAIL,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
    order = {f"T{index}": index for index in range(1, 17)}
    verdicts.sort(key=lambda verdict: order.get(verdict.criterion, 99))
    return verdicts


def main() -> int:
    parser = argparse.ArgumentParser(description="CR-149 §7 验收判据执行器（T1~T9）")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="临时置位所需开关（进程内，退出恢复），用于验证「开启后即达标」",
    )
    parser.add_argument("--json", default="", help="把完整报告写入该路径（JSON）")
    args = parser.parse_args()

    simulated = (
        _temporary_settings(
            CONTEXT_BUDGET_ENABLED=True,
            WRITEBACK_DECISION_ENABLED=True,
            # v1.18.1：把另两项开关门控的判据一并纳入模拟置位，使 `--simulate` 能一次
            # 证明「全部开关开启后即达标」（T3 检索侧重排 / T8 依赖图调度）。
            RAG_RERANK_ENABLED=True,
            RAG_SCORE_THRESHOLD=0.15,
            COMPONENT_DEPENDENCY_SCHEDULING_ENABLED=True,
        )
        if args.simulate
        else None
    )
    if simulated is not None:
        simulated.__enter__()
    try:
        verdicts = run_all()
    finally:
        if simulated is not None:
            simulated.__exit__(None, None, None)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "simulate": bool(args.simulate),
        "summary": {
            status: sum(1 for verdict in verdicts if verdict.status == status)
            for status in (STATUS_PASS, STATUS_FAIL, STATUS_SKIP, STATUS_BLOCKED)
        },
        "verdicts": [verdict.to_dict() for verdict in verdicts],
    }

    print(f"{'判据':<4}{'状态':<9}说明")
    print("-" * 96)
    for verdict in verdicts:
        note = verdict.reason or "达标"
        print(f"{verdict.criterion:<4}{verdict.status:<9}{note[:78]}")
    print("-" * 96)
    print(json.dumps(report["summary"], ensure_ascii=False))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.json}")

    return 1 if report["summary"][STATUS_FAIL] else 0


if __name__ == "__main__":
    raise SystemExit(main())

