"""CR-149 评测集执行器（判据 T3 段③：rerank 开 / 关的**聚合对照**）

**定位（如实登记，不得夸大）**：本执行器落地的是方案的**检索侧聚合口径** ——
「条目数下降 且 **相关项保留率不降** 且 **噪声剔除率上升**」。

**它覆盖什么、不覆盖什么（关键，不得混淆）**：

  * **覆盖**：评测集的**加载与校验**、开/关两态的**聚合度量**、口径自检
    （保留项必 ≥ 阈值、按 score 降序）、以及**压力样本**（相关项分数低于阈值）的观测；
  * **不覆盖** `used_ratio`：该指标属**归因 A**（回答引用了多少条注入片段），
    **取值依赖 LLM 回答内容** ⇒ 本执行器**不**对其做任何近似断言；只在
    `runtime_pending` 中**逐项声明所需运行态输入**。理由同 `t_acceptance_runner.py`
    T3 的 `evaluation_pending`（本执行器就位后，该条理由已收窄为「仅缺运行态数据」）。

**两态口径（与网关一致，来源见 T3 段①/②）**：

  * `rerank_on`：按 `score` 降序、过滤 `score < score_threshold`；
  * `rerank_off`：不过滤、保持原序（`score_threshold <= 0` ⇒ 解析为 None ⇒ 网关不过滤）。

**必须明说的局限**：网关**不本地过滤**（`score_threshold` 是**下传检索服务**的，T3 段①
只验「口径」）⇒ 本执行器的开/关过滤是**该口径的夹具仿真**，**不等于真实检索路径**；
真实检索侧的聚合对照须在运行态进行，见 `runtime_pending`。

用法（cwd 任意）：

    python eval_set_runner.py [--json 输出路径]
    python eval_set_runner.py --self-check        # 夹具一致性断言，不符即退出码非 0
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

EVAL_SET_NAME = "cr149-eval-set.json"


def load_eval_set(path: str) -> dict[str, Any]:
    """加载评测集并做**结构校验**（缺字段即拒绝，不静默降级）"""
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("samples"), list) or not payload["samples"]:
        raise ValueError("评测集缺少 samples（或为空）")
    for sample in payload["samples"]:
        missing = [key for key in ("id", "group", "query", "candidates") if key not in sample]
        if missing:
            raise ValueError(f"样本 {sample.get('id')!r} 缺字段：{missing}")
        for candidate in sample["candidates"]:
            if "score" not in candidate or "relevant" not in candidate:
                raise ValueError(f"样本 {sample['id']!r} 候选缺 score/relevant")
    return payload


def measure(
    samples: list[dict[str, Any]], *, threshold: float, rerank_on: bool
) -> dict[str, Any]:
    """按指定态度量一批样本（纯函数，无副作用）"""
    totals = {"items": 0, "relevant_total": 0, "relevant_kept": 0, "noise_total": 0, "noise_kept": 0}
    per_sample: list[dict[str, Any]] = []
    for sample in samples:
        candidates = list(sample["candidates"])
        if rerank_on:
            # 口径同网关下传语义：按 score 降序 + 过滤低于阈值者
            ordered = sorted(candidates, key=lambda item: float(item["score"]), reverse=True)
            kept = [item for item in ordered if float(item["score"]) >= threshold]
        else:
            kept = candidates
        relevant_kept = sum(1 for item in kept if item["relevant"])
        relevant_total = sum(1 for item in candidates if item["relevant"])
        noise_kept = sum(1 for item in kept if not item["relevant"])
        noise_total = sum(1 for item in candidates if not item["relevant"])
        totals["items"] += len(kept)
        totals["relevant_total"] += relevant_total
        totals["relevant_kept"] += relevant_kept
        totals["noise_total"] += noise_total
        totals["noise_kept"] += noise_kept
        per_sample.append(
            {
                "id": sample["id"],
                "items_before": len(candidates),
                "items_after": len(kept),
                "kept_ids": [item["id"] for item in kept],
                "dropped_relevant_ids": [
                    item["id"]
                    for item in candidates
                    if item["relevant"] and item not in kept
                ],
            }
        )
    totals["relevant_recall"] = (
        totals["relevant_kept"] / totals["relevant_total"] if totals["relevant_total"] else None
    )
    totals["noise_rejection"] = (
        1.0 - totals["noise_kept"] / totals["noise_total"] if totals["noise_total"] else None
    )
    return {"aggregate": totals, "per_sample": per_sample}


def _group(samples: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [sample for sample in samples if sample["group"] == name]


def evaluate(eval_set: dict[str, Any]) -> dict[str, Any]:
    """开 / 关两态对照 + 硬断言（仅 `assert` 组）＋ 压力样本观测"""
    threshold = float(eval_set["_meta"]["score_threshold"])
    assert_group = _group(eval_set["samples"], "assert")
    stress_group = _group(eval_set["samples"], "stress")

    off = measure(assert_group, threshold=threshold, rerank_on=False)
    on = measure(assert_group, threshold=threshold, rerank_on=True)

    failures: list[str] = []
    if not on["aggregate"]["items"] < off["aggregate"]["items"]:
        failures.append(
            f"条目数未下降：on={on['aggregate']['items']} off={off['aggregate']['items']}"
        )
    off_recall, on_recall = off["aggregate"]["relevant_recall"], on["aggregate"]["relevant_recall"]
    if off_recall is None or on_recall is None or on_recall < off_recall:
        failures.append(f"相关项保留率下降：on={on_recall} off={off_recall}")
    off_noise, on_noise = off["aggregate"]["noise_rejection"], on["aggregate"]["noise_rejection"]
    if off_noise is None or on_noise is None or not on_noise > off_noise:
        failures.append(f"噪声剔除率未上升：on={on_noise} off={off_noise}")

    # 口径自检：保留项必 ≥ 阈值、且按 score 降序
    for entry in on["per_sample"]:
        sample = next(item for item in assert_group if item["id"] == entry["id"])
        expected = sum(
            1 for item in sample["candidates"] if float(item["score"]) >= threshold
        )
        if expected != entry["items_after"]:
            failures.append(f"样本 {entry['id']} 保留数与阈值口径不一致")
        scores = [
            float(item["score"])
            for item in sample["candidates"]
            if item["id"] in entry["kept_ids"]
        ]
        if scores != sorted(scores, reverse=True):
            failures.append(f"样本 {entry['id']} 保留项未按 score 降序")

    stress_observations: list[dict[str, Any]] = []
    stress = measure(stress_group, threshold=threshold, rerank_on=True) if stress_group else None
    if stress:
        for entry in stress["per_sample"]:
            if entry["dropped_relevant_ids"]:
                stress_observations.append(
                    {
                        "sample": entry["id"],
                        "dropped_relevant_ids": entry["dropped_relevant_ids"],
                        "threshold": threshold,
                        "note": (
                            "**固定阈值剔除了标注为相关、但分数低于阈值的条目** ⇒ 暴露固定阈值的"
                            "适用边界；须评估「下调阈值」或「改用相对阈值（如 top-k 内分位数）」"
                        ),
                    }
                )

    runtime_pending = {
        "status": "pending_runtime",
        "reason": (
            "**真实检索侧聚合对照须运行态**：网关不本地过滤（`score_threshold` 下传检索服务）"
            "⇒ 本执行器的开/关过滤是**口径仿真**，不代表真实检索路径；"
            "且 `used_ratio`（归因 A：回答引用了多少条注入片段）**取值依赖 LLM 回答内容**。"
        ),
        "required_inputs": [
            "运行态检索端点（OpenRAG 数据面）＋ 真实 KB 数据",
            "LLM 回答（用于计算归因 A 的 `used_ratio`）",
            "同一批 query 在 rerank 开 / 关两态下的注入片段与回答",
        ],
    }
    return {
        "eval_set": eval_set["_meta"]["id"],
        "eval_set_version": eval_set["_meta"]["version"],
        "score_threshold": threshold,
        "rerank_on": on,
        "rerank_off": off,
        "failures": failures,
        "verdict": "FAIL" if failures else "PASS",
        "stress_observations": stress_observations,
        "runtime_pending": runtime_pending,
        "coverage_note": (
            "本执行器覆盖**检索侧聚合口径**；**不覆盖** `used_ratio`（依赖 LLM 回答，"
            "见 runtime_pending）—— 不以近似断言冒充覆盖。"
        ),
    }


def _self_check() -> int:
    """夹具一致性断言：口径与聚合结果须可复现（不符即退出码非 0）"""
    here = os.path.dirname(os.path.abspath(__file__))
    result = evaluate(load_eval_set(os.path.join(here, EVAL_SET_NAME)))
    on, off = result["rerank_on"]["aggregate"], result["rerank_off"]["aggregate"]
    checks = [
        ("无硬断言失败项", result["failures"] == []),
        ("判定为 PASS", result["verdict"] == "PASS"),
        ("关态条目数 = 22（夹具锁定）", off["items"] == 22),
        ("开态条目数 = 15（夹具锁定）", on["items"] == 15),
        ("条目数下降", on["items"] < off["items"]),
        ("关态相关项保留率 = 1.0", off["relevant_recall"] == 1.0),
        ("开态相关项保留率不降（= 1.0）", on["relevant_recall"] == 1.0),
        ("关态噪声剔除率 = 0.0", off["noise_rejection"] == 0.0),
        ("开态噪声剔除率 = 0.5", on["noise_rejection"] == 0.5),
        ("压力样本观测非空（固定阈值边界已暴露）", len(result["stress_observations"]) >= 1),
        ("运行态项如实登记为 pending", result["runtime_pending"]["status"] == "pending_runtime"),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[SELF-CHECK] {'PASS' if ok else 'FAIL'}：{name}")
    print(
        f"[SELF-CHECK] 开态 items={on['items']} recall={on['relevant_recall']} "
        f"noise_rejection={on['noise_rejection']}；关态 items={off['items']} "
        f"recall={off['relevant_recall']} noise_rejection={off['noise_rejection']}"
    )
    if failed:
        print(f"[SELF-CHECK] **共 {len(failed)} 项不符 ⇒ 退出码 1**")
        return 1
    print("[SELF-CHECK] 全部通过")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CR-149 评测集执行器（T3 段③）")
    parser.add_argument("--eval-set", default="", help="评测集路径（默认同目录 cr149-eval-set.json）")
    parser.add_argument("--json", default="", help="把完整报告写入该路径（JSON）")
    parser.add_argument("--self-check", action="store_true", help="夹具一致性断言")
    args = parser.parse_args()

    if args.self_check:
        return _self_check()

    path = args.eval_set or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), EVAL_SET_NAME
    )
    result = evaluate(load_eval_set(path))
    on, off = result["rerank_on"]["aggregate"], result["rerank_off"]["aggregate"]
    print(f"评测集: {result['eval_set']}（{result['eval_set_version']}）；阈值 {result['score_threshold']}")
    print(
        f"关态: 条目 {off['items']} / 相关项保留率 {off['relevant_recall']} / "
        f"噪声剔除率 {off['noise_rejection']}"
    )
    print(
        f"开态: 条目 {on['items']} / 相关项保留率 {on['relevant_recall']} / "
        f"噪声剔除率 {on['noise_rejection']}"
    )
    print(f"**判定: {result['verdict']}**")
    for failure in result["failures"]:
        print(f"  [FAIL] {failure}")
    if result["stress_observations"]:
        print(f"压力样本观测（{len(result['stress_observations'])} 项，不作硬断言）：")
        for observation in result["stress_observations"]:
            print(
                f"  [OBS] {observation['sample']} 相关项被剔除："
                f"{observation['dropped_relevant_ids']}"
            )
    print(f"运行态项: {result['runtime_pending']['status']} —— {result['runtime_pending']['reason']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.json}")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
