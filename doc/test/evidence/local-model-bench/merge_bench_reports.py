"""把多次基准运行的报告合并为跨端点对比表（Markdown）

用途：同一套评测集在不同 Ollama 端点（本机 CPU / 局域网节点）上分次运行后，
合并为一张对比表，便于按「精度 × 时延」选型。

用法::

    python merge_bench_reports.py --out merged-bench.md
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default=str(HERE / "small-model-bench-*.json"))
    parser.add_argument("--out", default=str(HERE / "merged-bench.md"))
    args = parser.parse_args()

    reports: list[dict] = []
    for path in sorted(glob.glob(args.pattern)):
        try:
            reports.append(json.loads(Path(path).read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            print(f"跳过不可解析报告 {path}: {exc}")
    if not reports:
        print("未找到报告")
        return 1

    tasks: list[str] = []
    for report in reports:
        for task in report.get("tasks") or []:
            if task not in tasks:
                tasks.append(task)

    lines: list[str] = ["# 本地小模型精炼对比（跨端点合并）", ""]
    for report in reports:
        lines.append(
            f"- 批次：{report.get('generated_at')} ｜ 端点 {report.get('base_url')}"
            f" ｜ 模型 {', '.join(report.get('models') or [])}"
            f" ｜ 每任务条数 {report.get('limit_items') or '全部'}"
        )
    lines.append("")
    for task in tasks:
        lines.append(f"## 任务：{task}")
        lines.append("")
        lines.append(
            "| 模型 | 端点 | 主指标 | 值 | P50 (ms) | P95 (ms) | tok/s | 压缩率 | 格式合规 | 推理位置 |"
        )
        lines.append(
            "|------|------|--------|----|----------|----------|-------|--------|----------|----------|"
        )
        rows: list[tuple[float, float, str]] = []
        for report in reports:
            for model, entry in (report.get("results") or {}).items():
                task_entry = (entry.get("tasks") or {}).get(task)
                if not task_entry:
                    continue
                agg = task_entry["aggregate"]
                row = (
                    f"| {model} | {report.get('base_url')} | {agg.get('primary_metric')} | "
                    f"{agg.get('primary_value')} | {agg['latency_ms']['p50']} | "
                    f"{agg['latency_ms']['p95']} | {agg.get('tokens_per_second_p50')} | "
                    f"{agg.get('compression_ratio', '-')} | {agg.get('format_ok_rate', '-')} | "
                    f"{(entry.get('runtime') or {}).get('inference', '-')} |"
                )
                rows.append((float(agg.get("primary_value") or 0.0), float(agg["latency_ms"]["p95"]), row))
        rows.sort(key=lambda item: (-item[0], item[1]))
        lines.extend(row for _value, _p95, row in rows)
        lines.append("")
        if rows:
            lines.append(
                "排序（主指标降序、P95 升序）："
                + "；".join(
                    f"{index + 1}. {row.split('|')[1].strip()}（{value}／{p95}ms）"
                    for index, (value, p95, row) in enumerate(rows)
                )
            )
            lines.append("")
    out_path = Path(args.out)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"合并报告: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
