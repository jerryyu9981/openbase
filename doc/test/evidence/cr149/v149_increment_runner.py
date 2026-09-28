"""v1.4.9 增量 I-1~I-8 **判据执行器**（判据 AC-149-01~15 的离线样本）

**定位（如实登记，不得夸大）**：本执行器把《验收标准清单-v1.4.9》中**可离线复现**的判据
落到**样本 + 期望 + 实际**三栏；**运行态判据**（需 D3/D4 或真实链路）在 `runtime_pending`
段**逐项声明未覆盖**（`not_covered=true`），**不以夹具冒充运行态结论**。

**覆盖**：
  * I-1 跨段竞争池（开关开/关两态；不变量 T1）
  * I-2 逐条丢弃原因明细（原因码取值域 / 长度关系 / 不落正文）
  * I-3 显式标记（`hard_truncated` 恒有；`degraded="empty_guard"` 仅保底触发）
  * I-5 仍超窗（二次校验与显式失败标记；窗口内从不置位）
  * I-6 逐组件通道路由（独立标签 / 按组件隔离 / 裁决器异常回落）
  * I-7 审计动作码定稿（取值域 / 组件级维度 / 门控）
  * I-8 画像增量与频控预检（默认零变化 / fail-open）

**不覆盖**（`runtime_pending`）：I-4（跨仓 D4）、I-1/I-8/I-6 的运行态段。

用法（cwd = OpenLLM/backend，本执行器需导入该仓代码）：

    python <此脚本>            # 打印汇总（非 0 退出码＝存在失败项）
    python <此脚本> --json 输出路径
    python <此脚本> --self-check   # 样本集结构自检
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.getcwd())

_EVIDENCE_DIR = os.path.dirname(os.path.abspath(__file__))
_EVAL_SET = os.path.join(_EVIDENCE_DIR, "v149-increment-eval-set.json")


def _counter(text: str) -> int:
    return len(text or "")


def _history(count: int = 8, distinct: bool = True) -> str:
    if distinct:
        return "\n".join(f"{i}. " + f"史{i}" * 30 for i in range(1, count + 1))
    return "\n".join(f"{i}. " + "史" * 60 for i in range(1, count + 1))


def _items(count: int, source: str) -> list[dict[str, Any]]:
    return [{"source": source, "id": f"{source}-{i:04d}", "score": None} for i in range(1, count + 1)]


def case_i1() -> list[str]:
    """I-1：跨段竞争池（AC-149-01/02）"""
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    def _policy(competition: bool) -> BudgetPolicy:
        return BudgetPolicy(
            enabled=True,
            window_tokens=1200,
            output_reserve_tokens=200,
            cross_segment_competition_enabled=competition,
        )

    arguments = {"count_tokens": _counter, "query": "问题", "memory_ctx": "1. 一条很短的记忆",
                 "history_ctx": _history()}
    _p_off, comp_off = build_prompt(budget=_policy(False), **arguments)
    _p_on, comp_on = build_prompt(budget=_policy(True), segment_items=None, **arguments)

    problems: list[str] = []
    if "competition_filled" in comp_off.budget["history"]:
        problems.append("关闭时不应出现 competition_filled")
    if comp_on.budget["history"].get("competition_filled", 0) <= 0:
        problems.append("开启时应发生回填（competition_filled > 0）")
    if comp_on.truncated["history"].get("refilled_items", 0) < 1:
        problems.append("开启时应可观测回填条目数")
    material = ("profile", "memory", "rag", "history")
    used = sum(int(comp_on.budget.get(name, {}).get("used", 0)) for name in material)
    if used > _policy(True).available_tokens:
        problems.append("不变量 T1 被破坏（Σ素材 used > available）")
    return problems


def case_i2() -> list[str]:
    """I-2：逐条丢弃原因明细（AC-149-05）"""
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    policy = BudgetPolicy(enabled=True, window_tokens=1200, output_reserve_tokens=200)
    _prompt, composition = build_prompt(
        count_tokens=_counter, budget=policy, query="问题",
        history_ctx=_history(), segment_items={"history": _items(8, "history")},
    )
    report = composition.truncated["history"]
    detail = report["dropped"]

    problems: list[str] = []
    if [entry["reason"] for entry in detail] != ["quota"] * report["dropped_items"]:
        problems.append("明细原因码与约定不符（应为 quota）")
    if len(detail) != report["dropped_items"]:
        problems.append("全部条目有身份时 len(dropped) 应等于 dropped_items")
    if any(set(entry) != {"source", "id", "reason"} for entry in detail):
        problems.append("明细元素应仅含 source/id/reason")
    if "史" in json.dumps(composition.dropped, ensure_ascii=False):
        problems.append("明细**不得**落片段正文")
    return problems


def case_i3() -> list[str]:
    """I-3：显式标记（AC-149-03/04）"""
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    problems: list[str] = []
    # ① 整条丢弃（多条超配额）⇒ hard_truncated=False 且无 degraded
    policy = BudgetPolicy(enabled=True, window_tokens=1200, output_reserve_tokens=200)
    _p1, comp1 = build_prompt(count_tokens=_counter, budget=policy, query="问题",
                              history_ctx=_history())
    report1 = comp1.truncated["history"]
    if report1["hard_truncated"] is not False:
        problems.append("整条丢弃时 hard_truncated 应为 False")
    if "degraded" in report1:
        problems.append("未触发保底时不应出现 degraded")
    # ② 保底一条被触发（单条素材大于配额）⇒ hard_truncated=True 且 degraded=empty_guard
    tight = BudgetPolicy(enabled=True, window_tokens=100, output_reserve_tokens=0,
                         single_item_max_tokens=0)
    _p2, comp2 = build_prompt(count_tokens=_counter, budget=tight, query="问题",
                              history_ctx="1. " + "长" * 500)
    report2 = comp2.truncated.get("history") or {}
    if not report2:
        problems.append("保底场景应产出裁剪观测")
    else:
        if report2.get("hard_truncated") is not True:
            problems.append("保底收敛时 hard_truncated 应为 True")
        if report2.get("degraded") != "empty_guard":
            problems.append("保底触发时应标记 degraded=empty_guard")
    return problems


def case_i5() -> list[str]:
    """I-5：仍超窗的二次校验与显式失败标记（AC-149-04/12）"""
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    problems: list[str] = []
    normal = BudgetPolicy(enabled=True, window_tokens=2000, output_reserve_tokens=0)
    prompt, comp_ok = build_prompt(count_tokens=_counter, budget=normal, query="问题",
                                   history_ctx=_history())
    if comp_ok.over_window or comp_ok.over_window_tokens:
        problems.append("窗口内不应置判失败标记")
    if comp_ok.prompt_total_tokens > normal.window_tokens:
        problems.append("AC-149-12：窗口内出现超窗")
    over = BudgetPolicy(enabled=True, window_tokens=100, output_reserve_tokens=0)
    prompt_over, comp_over = build_prompt(count_tokens=_counter, budget=over, query="问" * 10,
                                          system_prompt="系" * 500)
    if not comp_over.over_window:
        problems.append("不可吸收的溢出应置 over_window")
    elif comp_over.over_window_tokens != _counter(prompt_over) - over.window_tokens:
        problems.append("over_window_tokens 应等于溢出额度")
    return problems


def case_i6() -> list[str]:
    """I-6：逐组件通道路由（AC-149-13）"""
    from app.edgerouter.orchestration.component_pipeline import run_components
    from app.identity.channel import CHANNEL_A, CHANNEL_B, ChannelStateManager

    async def _run():
        async def _ok(name: str, params: dict) -> dict:
            return {"items": []}

        handlers = {"memory": _ok, "rag": _ok}
        pipeline = [{"name": "memory"}, {"name": "rag"}]
        plain = await run_components(pipeline=pipeline, query="问题", handlers=handlers,
                                     component_names=("memory", "rag"))
        manager = ChannelStateManager("b-primary", consecutive_failure_threshold=1)
        manager.record_component_outcome("rag", success=False)
        routed = await run_components(pipeline=pipeline, query="问题", handlers=handlers,
                                      component_names=("memory", "rag"),
                                      channel_router=manager.resolve_component_channel)

        def _broken(_component: str) -> str:
            raise RuntimeError("裁决器不可用")

        fallback = await run_components(pipeline=pipeline, query="问题", handlers=handlers,
                                        component_names=("memory", "rag"),
                                        channel_router=_broken, default_channel=CHANNEL_B)
        return plain, routed, fallback

    plain, routed, fallback = asyncio.run(_run())
    problems: list[str] = []
    if plain.channels:
        problems.append("未提供裁决器时应零变化（channels 为空）")
    if routed.channels.get("rag") != CHANNEL_A:
        problems.append("达阈值的组件应切另一通道")
    if routed.channels.get("memory") != CHANNEL_B:
        problems.append("未达阈值的组件不得被牵连（互不覆盖）")
    if fallback.channels != {"memory": CHANNEL_B, "rag": CHANNEL_B}:
        problems.append("裁决器异常应 fail-safe 回落整体偏好")
    return problems


def case_i7() -> list[str]:
    """I-7：审计动作码定稿（AC-149-14）"""
    from app.identity import channel_audit

    problems: list[str] = []
    expected = {channel_audit.ACTION_FAILOVER_TO_A, channel_audit.ACTION_COMPONENT_FAILOVER}
    if set(channel_audit.AUDIT_ACTION_CODES) != expected:
        problems.append("定稿取值域与常量不一致")
    if hasattr(channel_audit, "ACTION_PROVISIONAL_NOTE"):
        problems.append("定稿后不得保留「暂定」标注")
    record = channel_audit.build_component_failover_record(
        component="rag", from_channel="b", to_channel="a", reason="连续失败达阈值", actor="auto"
    )
    if record.detail.get("component") != "rag":
        problems.append("组件级记录须含 component 维度（可检索）")
    if record.action != channel_audit.ACTION_COMPONENT_FAILOVER:
        problems.append("组件级记录动作码不符")
    status = channel_audit.emit_component_failover_audit(
        component="rag", from_channel="b", to_channel="a", reason="连续失败达阈值"
    )
    if status not in ("disabled", "no_loop"):
        problems.append(f"门控关闭（默认）时投递状态应为 disabled/no_loop，实际 {status}")
    return problems


def case_i8() -> list[str]:
    """I-8：画像增量与频控预检接线（AC-149-15）"""
    from app.edgerouter.orchestration import evaluate, profile_refine_gate
    from app.services.writeback_queue import compute_message_hash

    problems: list[str] = []
    if profile_refine_gate.install_profile_refine_on_startup() is not False:
        problems.append("门控默认关闭 ⇒ 注入位应返回 False（纯规则路径）")
    if evaluate.message_precheck(
        None, user_id="u1", session_id="s1", target="memory", query="q", response="r"
    ) is not False:
        problems.append("无持久层 ⇒ 预检不得拦截")
    if evaluate.profile_delta_precheck([], None) != {}:
        problems.append("无对话窗口 ⇒ 画像增量应为空（fail-open）")

    class _Boom:
        def exists_message(self, *_args: Any, **_kwargs: Any) -> bool:
            raise RuntimeError("模拟存储异常")

    try:
        blocked = evaluate.message_precheck(
            _Boom(), user_id="u1", session_id="s1", target="memory", query="q", response="r"
        )
    except Exception:  # noqa: BLE001 - 预检自身抛异常即视为不符合 fail-open 口径
        problems.append("预检不得向上抛异常（由调用方 fail-open 兜底）")
    else:
        if blocked:
            problems.append("存储异常时应按未命中处理")
    if not compute_message_hash("u1", "s1", "memory", "q", "r"):
        problems.append("消息指纹函数应可产出非空哈希")
    return problems


CASES = {
    "I-1": case_i1,
    "I-2": case_i2,
    "I-3": case_i3,
    "I-5": case_i5,
    "I-6": case_i6,
    "I-7": case_i7,
    "I-8": case_i8,
}


def load_eval_set(path: str = _EVAL_SET) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("cases"), list) or not payload["cases"]:
        raise ValueError("评测集缺少 cases")
    for case in payload["cases"]:
        missing = [key for key in ("id", "ac", "kind", "expect") if key not in case]
        if missing:
            raise ValueError(f"用例 {case.get('id')!r} 缺字段：{missing}")
        if case["id"] not in CASES:
            raise ValueError(f"用例 {case['id']!r} 无对应执行函数")
    return payload


def run(json_out: str | None = None) -> int:
    eval_set = load_eval_set()
    results: list[dict[str, Any]] = []
    for case in eval_set["cases"]:
        problems = CASES[case["id"]]()
        results.append(
            {
                "id": case["id"],
                "ac": case["ac"],
                "kind": case["kind"],
                "title": case.get("title", ""),
                "expect": case["expect"],
                "passed": not problems,
                "problems": problems,
            }
        )
    payload = {
        "eval_set": eval_set["id"],
        "eval_set_version": eval_set["version"],
        "offline_total": len(results),
        "offline_passed": sum(1 for item in results if item["passed"]),
        "results": results,
        "runtime_pending": eval_set.get("runtime_pending", []),
        "note": "运行态段**未覆盖**（not_covered=true）；不得以离线夹具结论冒充运行态结论",
    }
    for item in results:
        flag = "PASS" if item["passed"] else "FAIL"
        print(f"[{flag}] {item['id']} ({item['ac']}): {item['title']}")
        for problem in item["problems"]:
            print(f"        - {problem}")
    print(f"离线用例：{payload['offline_passed']}/{payload['offline_total']} 通过；"
          f"运行态未覆盖 {len(payload['runtime_pending'])} 项（如实标注）")
    if json_out:
        with open(json_out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"结果已写入：{json_out}")
    return 0 if payload["offline_passed"] == payload["offline_total"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="v1.4.9 增量判据执行器")
    parser.add_argument("--json", dest="json_out", default=None, help="结果输出路径")
    parser.add_argument("--self-check", action="store_true", help="仅做样本集结构自检")
    args = parser.parse_args()
    if args.self_check:
        load_eval_set()
        print("样本集结构自检通过")
        return 0
    return run(args.json_out)


if __name__ == "__main__":
    raise SystemExit(main())
