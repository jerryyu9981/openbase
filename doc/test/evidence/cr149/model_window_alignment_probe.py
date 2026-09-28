"""模型窗口两表对齐 · 影响面探针（CR-149 A3 / 题 5）

**两张表**：

  * `app/core/supported_models.py::SUPPORTED_MODELS` —— **对外声明**窗口（qwen3 家族 `context_window=131072`）；
  * `app/services/context_manager.py::MODEL_CONTEXT_LIMITS` —— **解析表**（窗口 ＋ 编码器）。

**缺陷（A3 现状）**：`SUPPORTED_MODELS` 已声明 qwen3 家族，而 `MODEL_CONTEXT_LIMITS`
**无 qwen3 族键** ⇒

  * `resolve_model_context_key("qwen3:*")` ⇒ `None` ⇒ 预算窗口走 `deployment_fallback`
    —— 值虽同为 8192，但**来源标识丢失「已识别模型」这一事实**（可观测性缺陷）；
  * `get_model_context_limit("qwen3:*")` 落到 `default`（**128000**），**与声明值 131072 不一致**；
  * `_get_encoding_name("qwen3:*")` 同样落 `default` 的编码器。

**本探针做什么**：以**模拟补表**（显式构造「含 qwen3 族键 / 不含」两态）给出**补表前后**对照，
并断言四项：

  1. **两表对齐** —— `qwen3` 族键的声明窗口须 **== `SUPPORTED_MODELS` 中 qwen3 家族的
     `context_window`**（本探针直接从源码文本提取该值，不依赖硬编码，避免「两处一起写错」）；
  2. **§9 问题 3 裁定结论不变** —— `min(声明, 部署)` 在两态**同为 8192**
     （「预算基准取有效窗口」的结论不因补表而变）；
  3. **对照模型不受影响** —— `gpt-4o-*`（最长键命中）与未知名（`deployment_fallback`）两态一致；
  4. **真实表状态** —— 打印 `aligned`（真实 `MODEL_CONTEXT_LIMITS` 是否已含 qwen3 族键），
     使「补表前 / 补表后」各跑一次的对照**可复现**。

用法（cwd = OpenLLM/backend）：

    python <此脚本> [--json 输出路径] [--self-check]     # --self-check 不符即退出码非 0
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())

from app.services import context_manager as cm  # noqa: E402

QWEN3_FAMILY_KEY = "qwen3"
QWEN3_ENCODING = "cl100k_base"
PROBE_MODELS = ("qwen3:0.6b", "qwen3:1.7b", "qwen3:8b", "qwen3:235b-a22b")
CONTROL_MODELS = ("gpt-4o-2024-08-06", "totally-unknown-model-x")


def _declared_qwen3_window() -> int:
    """从 `supported_models.py` **源码文本**提取 qwen3 家族的 `context_window`

    刻意**不硬编码** 131072：两表对齐的正确性须由**声明侧的真实取值**来判定，
    否则「两处一起写错」也会被判为对齐。
    """
    path = os.path.join("app", "core", "supported_models.py")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    windows = {
        int(match.group("window"))
        for match in re.finditer(
            r'"id":\s*"qwen3:[^"]+",(?:[^}]*?)"context_window":\s*(?P<window>\d+)',
            text,
            re.DOTALL,
        )
    }
    if not windows:
        raise RuntimeError("未从 supported_models.py 提取到 qwen3 家族的 context_window")
    if len(windows) > 1:
        raise RuntimeError(f"qwen3 家族声明窗口不一致（两表对齐的前提被破坏）：{sorted(windows)}")
    return windows.pop()


def _consumer_view(model: str) -> dict[str, object]:
    """采集一个模型名在**各消费点**的取值（补表影响面的观测量）"""
    manager = cm.ContextManager(db=None)  # type: ignore[arg-type]
    window, source = cm.resolve_effective_window_tokens(model)
    return {
        "model": model,
        "matched_key": cm.resolve_model_context_key(model),
        "effective_window_tokens": window,
        "window_source": source,
        "get_model_context_limit": manager.get_model_context_limit(model),
        "encoding_name": manager._get_encoding_name(model),
    }


def _with_table(include_qwen3: bool, *, window: int) -> dict[str, dict[str, object]]:
    """在「含 / 不含 qwen3 族键」两态下采集全部观测模型（采集后**还原真实表**）"""
    original = dict(cm.MODEL_CONTEXT_LIMITS)
    try:
        if include_qwen3:
            cm.MODEL_CONTEXT_LIMITS[QWEN3_FAMILY_KEY] = cm.ModelContextLimit(
                QWEN3_FAMILY_KEY, window, QWEN3_ENCODING
            )
        else:
            cm.MODEL_CONTEXT_LIMITS.pop(QWEN3_FAMILY_KEY, None)
        return {
            model: _consumer_view(model)
            for model in (*PROBE_MODELS, *CONTROL_MODELS)
        }
    finally:
        cm.MODEL_CONTEXT_LIMITS.clear()
        cm.MODEL_CONTEXT_LIMITS.update(original)


def main() -> int:
    parser = argparse.ArgumentParser(description="模型窗口两表对齐影响面探针（A3 / 题 5）")
    parser.add_argument("--json", default="", help="把完整报告写入该路径（JSON）")
    parser.add_argument("--self-check", action="store_true", help="断言不符即退出码非 0")
    args = parser.parse_args()

    declared = _declared_qwen3_window()
    before = _with_table(False, window=declared)
    after = _with_table(True, window=declared)
    aligned = QWEN3_FAMILY_KEY in cm.MODEL_CONTEXT_LIMITS

    failures: list[str] = []
    # ① 两表对齐：补表后 qwen3 系列的 max_tokens 须等于声明窗口
    for model in PROBE_MODELS:
        if after[model]["matched_key"] != QWEN3_FAMILY_KEY:
            failures.append(f"补表后 {model} 未命中 qwen3 族键：{after[model]['matched_key']}")
        if after[model]["get_model_context_limit"] != declared:
            failures.append(
                f"补表后 {model} 的 get_model_context_limit="
                f"{after[model]['get_model_context_limit']} ≠ 声明 {declared}"
            )
    # ② §9 问题 3 裁定结论不变：min(声明, 部署) 两态同为 8192
    for model in PROBE_MODELS:
        if before[model]["effective_window_tokens"] != after[model]["effective_window_tokens"]:
            failures.append(
                f"补表改变了预算窗口（裁定结论被破坏）：{model} "
                f"{before[model]['effective_window_tokens']} → {after[model]['effective_window_tokens']}"
            )
        if after[model]["effective_window_tokens"] != 8192:
            failures.append(f"补表后预算窗口 ≠ 8192：{after[model]['effective_window_tokens']}")
    # ②' 来源标识应因「已识别」而变（可观测性改善，须如实记录）
    for model in PROBE_MODELS:
        if before[model]["window_source"] != "deployment_fallback":
            failures.append(f"补表前来源标识异常：{model} {before[model]['window_source']}")
        if after[model]["window_source"] != f"deployment_cap:{QWEN3_FAMILY_KEY}":
            failures.append(f"补表后来源标识异常：{model} {after[model]['window_source']}")
    # ③ 对照模型不受影响
    for model in CONTROL_MODELS:
        if before[model] != after[model]:
            failures.append(f"对照模型受影响：{model} {before[model]} → {after[model]}")

    print(f"声明侧（supported_models.py，qwen3 家族 context_window）: {declared}")
    print(f"解析侧（MODEL_CONTEXT_LIMITS）已含 qwen3 族键: {aligned}")
    print("")
    header = f"{'模型':<26}{'补表前 key/窗口/来源/limit/编码':<58}{'补表后 key/窗口/来源/limit/编码'}"
    print(header)
    for model in (*PROBE_MODELS, *CONTROL_MODELS):
        left = before[model]
        right = after[model]
        fmt = lambda view: (  # noqa: E731 - 局部小工具，仅用于打印
            f"{view['matched_key']}/{view['effective_window_tokens']}/"
            f"{view['window_source']}/{view['get_model_context_limit']}/{view['encoding_name']}"
        )
        print(f"{model:<26}{fmt(left):<58}{fmt(right)}")
    print("")
    print(f"**断言: {'全部通过' if not failures else f'{len(failures)} 项不符'}**")
    for failure in failures:
        print(f"  [FAIL] {failure}")

    report = {
        "probe": "model_window_alignment",
        "declared_qwen3_window": declared,
        "aligned_in_real_table": aligned,
        "qwen3_family_key": QWEN3_FAMILY_KEY,
        "before": before,
        "after": after,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
        "ruling_note": (
            "**§9 问题 3 裁定结论（预算基准取有效窗口）不因补表而变** —— "
            "两态的 `effective_window_tokens` 同为 8192（`min(声明 131072, 部署 8192)`）；"
            "**仅来源标识**由 `deployment_fallback` 变为 `deployment_cap:qwen3`，"
            "这是**可观测性改善**（如实记录，不得当作「行为变更」）。"
        ),
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.json}")
    if args.self_check:
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
