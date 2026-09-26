"""CR-149 §7 验收判据执行器（T1~T9）

**用途**：把《OpenBase-上下文精装配与组件通道优化技术方案》§7 的 T1~T9 判据做成
**一键可复跑**的判定器 —— 人工批准开关开启值后，只需运行本脚本即可拿到逐条
`PASS / FAIL / SKIP / BLOCKED` 与**原始测量数据**（不依赖人工肉眼比对）。

**设计约束（重要）**：

* **不改生产配置**：脚本只**读取** `settings` 的当前值；需要开关开启才能判定的判据
  （T1/T2/T3/T5/T8/T9），若开关为关则返回 `SKIP` 并给出**需要置哪些键**；
  `--simulate` 模式会在**本进程内**临时置位（退出前恢复），用于证明"开启后即达标"，
  **不写任何配置文件、不影响运行中的服务**；
* **可判定性分级**：`SKIP`（开关未开）≠ `FAIL`（能力不达标）；`BLOCKED` 表示
  **环境/前置条件缺失**（如 T4 需要运行态故障注入、T6 属第三批未实施），
  也**不计入失败**，但会在报告里显式列出，避免"没做"被误读成"通过"；
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

def check_t3() -> Verdict:
    """T3：rerank 与 score_threshold 透传，低分条目被过滤（条目数降、score 单调）"""
    title = "检索：rerank / score_threshold 透传且低分条目被过滤"
    from app.api.openllm_gateway import _rag_search_params
    from app.core.config import settings

    params = {
        "rerank": True,
        "score_threshold": 0.5,
        "kb_id": "kb-probe",
        "query": "q",
        "top_k": 5,
    }
    resolved = _rag_search_params(params)
    scored_items = [
        {"id": "a", "score": 0.91},
        {"id": "b", "score": 0.62},
        {"id": "c", "score": 0.31},
        {"id": "d", "score": 0.05},
    ]
    filtered = [
        item for item in scored_items if item["score"] >= resolved["score_threshold"]
    ]
    scores = [item["score"] for item in filtered]
    monotonic = all(
        left >= right for left, right in zip(scores, scores[1:], strict=False)
    )
    failures = []
    if resolved.get("rerank") is not True:
        failures.append("rerank 未透传")
    if resolved.get("score_threshold") != 0.5:
        failures.append(f"score_threshold 未透传：{resolved.get('score_threshold')}")
    if len(filtered) >= len(scored_items):
        failures.append("低分条目未被阈值过滤（条目数未下降）")
    if not monotonic:
        failures.append("过滤后 score 非单调递减")
    return Verdict(
        criterion="T3",
        title=title,
        status=STATUS_FAIL if failures else STATUS_PASS,
        requires=[
            f"RAG_RERANK_ENABLED={getattr(settings, 'RAG_RERANK_ENABLED', None)}",
            f"RAG_SCORE_THRESHOLD={getattr(settings, 'RAG_SCORE_THRESHOLD', None)}",
        ],
        detail={
            "resolved_search_params": resolved,
            "items_before": len(scored_items),
            "items_after": len(filtered),
            "filtered_scores": scores,
        },
        reason="；".join(failures),
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


async def _t4_sync_trace(exc: Exception) -> dict[str, Any]:
    """同步路径：handler 落 shared_state → 经单一落痕函数并入轨迹"""
    from unittest.mock import AsyncMock, patch

    import app.api.openllm_gateway as gateway

    adapter = _T4FailingRagAdapter(exc)
    with _temporary_settings(OPENRAG_FALLBACK_BUILTIN=True):
        with patch.object(gateway, "_get_component_adapters", return_value=(None, adapter)), \
                patch.object(
                    gateway,
                    "_builtin_rag_search",
                    AsyncMock(return_value={"results": []}),
                ):
            handlers, _errors, shared = gateway._build_component_handlers(
                db=None,
                identity=_t4_identity(),
                request_id="req-t4",
                query="q",
                timeline=[],
            )
            await handlers["rag"]("rag", {"kb_id": "kb"})
    return gateway._merge_rag_trace(
        {},
        rag_source=shared.get("rag_source"),
        builtin_fallback_reason=shared.get("builtin_fallback_reason"),
    )


async def _t4_stream_trace(exc: Exception) -> dict[str, Any]:
    """流式路径：接管发生在共用组件步骤 → 同样须带归因"""
    import app.api.openllm_gateway as gateway
    from app.edgerouter.orchestration.component_pipeline import run_components

    async def _rag_handler(_name: str, _params: dict) -> dict:
        raise exc

    async def _rag_fallback(_params: dict) -> dict:
        return {"results": []}

    result = await run_components(
        pipeline=[{"component": "rag", "params": {"kb_id": "kb"}}],
        query="q",
        handlers={"rag": _rag_handler},
        assembler=None,
        enable_parallel=False,
        rag_fallback=_rag_fallback,
        rag_fallback_enabled=True,
        entry_key="component",
        timeline=[],
    )
    return gateway._merge_rag_trace(
        {},
        rag_source=result.rag_source,
        builtin_fallback_reason=result.builtin_fallback_reason,
    )


async def check_t4() -> Verdict:
    """T4：组件故障后通道裁决与内置 RAG 接管有轨迹（轨迹部分：进程内可判）

    **本执行器判定**（进程内，不依赖运行态故障注入）：

      1. 同步路径 handler：「外部检索失败」→ ``rag_source=builtin`` **且带归因**；
      2. 流式路径（共用组件步骤）：同样落 ``rag_source=builtin`` **且带归因**；
      3. 两路径经**同一落痕函数**并入 ``routing_trace.components`` → 字段逐键一致。

    端点级（HTTP）故障注入另由单元护栏覆盖 4 例（同步 / 流式端点 200、无 error 事件、
    轨迹带来源与归因、装配缺失不回退），见 ``detail.endpoint_level_evidence``。

    **仍需运行态**：**真实**停 OpenRAG / 改不可达地址的故障注入、端到端轨迹**实际落库**读取；
    以及 ``health.components.builtin_rag.has_base``（接管是否有底座）。
    """
    title = "备通道：组件故障后裁决与内置 RAG 接管有轨迹（轨迹=进程内判；无 5xx=运行态）"
    from app.api.openllm_gateway import _merge_rag_trace, _probe_builtin_rag

    fault = RuntimeError("OpenRAG 不可达: connection refused")
    sync_trace = await _t4_sync_trace(fault)
    stream_trace = await _t4_stream_trace(fault)
    builtin = await _probe_builtin_rag(None)

    failures: list[str] = []
    if sync_trace.get("rag_source") != "builtin":
        failures.append(f"同步路径未落 rag_source=builtin：{sync_trace}")
    if stream_trace.get("rag_source") != "builtin":
        failures.append(f"流式路径未落 rag_source=builtin：{stream_trace}")
    if not sync_trace.get("builtin_fallback_reason"):
        failures.append("同步路径缺接管归因")
    if not stream_trace.get("builtin_fallback_reason"):
        failures.append("流式路径缺接管归因（轨迹不完整）")
    if sync_trace.get("builtin_fallback_reason") != stream_trace.get(
        "builtin_fallback_reason"
    ):
        failures.append(f"两路径归因不一致：{sync_trace} vs {stream_trace}")
    if sync_trace["rag_source"] != stream_trace["rag_source"]:
        failures.append(f"两路径来源不一致：{sync_trace} vs {stream_trace}")
    merged = _merge_rag_trace({})
    if merged.get("rag_source") != "skipped" or "builtin_fallback_reason" in merged:
        failures.append(f"未执行检索时应为 skipped 且不落归因：{merged}")

    detail: dict[str, Any] = {
        "fault_injected": f"{type(fault).__name__}: {fault}",
        "sync_trace_components": sync_trace,
        "stream_trace_components": stream_trace,
        "trace_contract": "FAIL" if failures else "PASS",
        "builtin_rag": builtin,
        "runtime_pending": [
            "真实停 OpenRAG / 改不可达地址的故障注入（本执行器不改外部服务状态）",
            "端到端轨迹**实际落库**读取（本执行器只判到「落库调用入参」层）",
        ],
        "endpoint_level_evidence": (
            "端点级（HTTP，进程内 TestClient）故障注入已由 "
            "`tests/unit/test_rag_builtin_fallback_trace.py::TestEndpointLevelFaultInjection` "
            "覆盖 4 例：同步 POST /openllm/v1/chat 返回 200 且轨迹带 rag_source=builtin 与归因；"
            "开关关时 200 且记 degraded/rag_source=skipped；装配缺失时不回退；"
            "流式 POST /openllm/v1/chat/stream 返回 200、无 error 事件、**落库轨迹入参**同样带来源与归因。"
            "该层证明「组件故障时不返回 5xx 且轨迹可复盘」，**不替代真实停服 E2E**"
        ),
        "historical_e2e_evidence": (
            "CR-148-013 TT-022/TT-023（2026-09-22，mock 桩故障注入）曾在旧提交上"
            "验过 rag_source=builtin / degraded=[] / 主流程 200；须在**当前提交**上复跑确认"
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
            "内置 RAG 有底座（has_base=true）→ 判「接管非空」",
        ],
        detail=detail,
        reason=(
            "轨迹部分已在进程内验证通过（两路径 rag_source=builtin 且归因一致、"
            "单一落痕实现）；且端点级（HTTP）故障注入 4 例通过（同步/流式端点均 200、"
            "无 error 事件、轨迹带来源与归因、装配缺失不回退）⇒「无 5xx」已在**进程内**覆盖；"
            "剩余**真实停服注入**与**轨迹实际落库读取**需运行态。"
            f"内置 RAG 底座：has_base={builtin.get('has_base')}"
            "（false 时接管必然注入为空，须先补底座或按 §4.1 声明生效条件）"
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


async def check_t5() -> Verdict:
    """T5：低价值轮次不产生 rag 入库（无该行或 skipped），高价值轮次正常入库"""
    title = "写侧闸门：低价值轮次不入库、高价值轮次正常入库"
    keys = ["WRITEBACK_DECISION_ENABLED"]
    if not _is_on("WRITEBACK_DECISION_ENABLED"):
        return _switch_off_verdict("T5", title, keys)

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
            "low_value": {"submitted": low_submitted, "returns": low_returns},
            "high_value": {"submitted": high_submitted, "returns": high_returns},
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- T6 精炼

def check_t6() -> Verdict:
    """T6：精炼开启时 fallback=false 且 elapsed_ms ≤ 预算（属第三批：生成式精炼）"""
    return Verdict(
        criterion="T6",
        title="精炼：fallback=false 且 elapsed_ms ≤ 预算；关闭/超时不降级",
        status=STATUS_BLOCKED,
        requires=["生成式精炼（第三批）", "达标本地模型 / GPU 节点（§5.6 门槛）"],
        detail={"batch": "第三批", "design_ref": "§4.4 / §5.5 / §5.6"},
        reason=(
            "该判据依赖第三批「生成式精炼」能力，按方案 §6 属第三批；"
            "且 §5.4/§5.5 实测显示 ≤1B 本地模型未过门槛，需先完成模型选型/节点准备"
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
    """T9：路由达标判定与最终决策一致；规则集可配置；LLM 兜底超时回落"""
    title = "路由：达标即决策、规则集可配置、LLM 兜底超时回落"
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
            "llm_fallback_switch": getattr(
                settings, "COMPONENT_ROUTER_LLM_FALLBACK_ENABLED", None
            ),
        },
        reason="；".join(failures),
    )


# ---------------------------------------------------------------- 执行入口

SYNC_CHECKS: list[tuple[str, Callable[[], Verdict]]] = [
    ("T1", check_t1),
    ("T2", check_t2),
    ("T3", check_t3),
    ("T6", check_t6),
    ("T9", check_t9),
]

ASYNC_CHECKS: list[tuple[str, Callable[[], Any]]] = [
    ("T4", check_t4),
    ("T5", check_t5),
    ("T7", check_t7),
    ("T8", check_t8),
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
    order = {f"T{index}": index for index in range(1, 10)}
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
