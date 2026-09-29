"""把 T3a 巡检结果渲染为「逐链路问题表」（Step 4 证据，TT-v1.4.9-024 输出物标准）。

输入：`cr149-t40-t2t3e2e-result.json`（由 `cr149-t40-t2t3e2e-20260929.py` 产出）
输出：UTF-8（无 BOM）逐链路问题表，含状态码分布 / 网络失败清单 / 环境类清单 / 问题分类 / 排除项登记。

用法：
    python cr149-t40-render-t3a.py --result <result.json> --out <table.txt>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.result).read_text(encoding="utf-8"))
    case = data["cases"]["TT-v1.4.9-024"]

    lines: list[str] = []
    lines.append("=== v1.4.9 Step 4 · T3a 服务间集成巡检 · 逐链路问题表（TT-v1.4.9-024）===")
    lines.append(f"实例：{data['open_url']}（生成时刻：{data['started_at']}）")
    lines.append("")
    lines.append("--- 覆盖口径 ---")
    lines.append(f"路由总数（全方法）：{case['total_routes']}")
    lines.append(f"GET 路由数：{case['get_routes']}")
    lines.append(f"实际探测：{case['probed']}（覆盖 {case['coverage_pct']}%）")
    lines.append(f"排除：{len(case['excluded'])}（理由：{case['exclude_reason']}）")
    for path in case["excluded"]:
        lines.append(f"  - 排除 {path}")
    lines.append("")
    lines.append("--- 状态码分布 ---")
    for key, value in case["status_distribution"].items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("--- 网络层门禁 ---")
    lines.append(f"代码类 HTTP≥500（B 类）：{len(case['code_5xx'])}")
    for item in case["code_5xx"]:
        lines.append(f"  [B] {item['route']} → {item['status']} | {item.get('body_head', '')[:160]}")
    lines.append(f"环境类 HTTP≥500（H 类，登记环境遗留，不进缺陷闭环）：{len(case['env_5xx'])}")
    for item in case["env_5xx"]:
        lines.append(f"  [H] {item['route']} → {item['status']} | {item.get('body_head', '')[:160]}")
    lines.append(f"requestfailed（网络失败）：{len(case['requestfailed'])}")
    for item in case["requestfailed"]:
        lines.append(f"  [FAIL] {item['route']} → {item.get('error', '')[:160]}")
    lines.append("")
    lines.append("--- 逐链路明细（路由 / 状态码 / 耗时ms / 分类）---")
    for item in case["details"]:
        status = item["status"] if item["status"] is not None else "FAILED"
        lines.append(f"  {status:<6} {item['elapsed_ms'] if item['elapsed_ms'] is not None else '-':>8}  "
                     f"{item['class']:<13} {item['route']}")
    lines.append("")
    lines.append("--- 判定 ---")
    lines.append(
        "P0/P1 链路无阻塞性问题（代码类 5xx = 0、requestfailed = 0）"
        if case["ok"]
        else "**未通过**：存在代码类 5xx 或网络失败（见上）"
    )

    report = "\n".join(lines)
    print(report)
    Path(args.out).write_text(report + "\n", encoding="utf-8")
    return 0 if case["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
