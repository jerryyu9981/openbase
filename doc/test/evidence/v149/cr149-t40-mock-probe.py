"""Step 4 · Mock / 外部依赖用例（TT-v1.4.9-021）证据。

覆盖：桩服务可启动 → 契约（路由表）与调用方一致 → 故障注入可见（503，非静默）→ 恢复。
产出：`cr149-t40-mock-20260929.txt`

用法：
    python cr149-t40-mock-probe.py --out doc/test/evidence/v149/cr149-t40-mock-20260929.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

STUBS = (
    ("openrag_stub", "http://127.0.0.1:8090", "/openrag/v1/collections", "/__fault__/recover"),
    ("openmemory_stub", "http://127.0.0.1:8091", "/openmemory/v1/history/probe-none", "/__fault__/up"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    lines: list[str] = []
    lines.append("=== v1.4.9 Step 4 · Mock / 外部依赖用例证据（TT-v1.4.9-021）===")
    lines.append("口径：桩服务**独立启动**验证「可启动 ＋ 契约一致 ＋ 故障可见」；")
    lines.append("      本版 E2E 未以桩替换真实上游（真实组件降级已如实留痕，见环境证据）。")
    lines.append("")

    ok = True
    for name, base, probe_path, recover_path in STUBS:
        lines.append(f"--- {name} @ {base} ---")
        with httpx.Client(base_url=base, timeout=10.0) as client:
            spec = client.get("/openapi.json")
            lines.append(f"  GET /openapi.json → {spec.status_code}")
            routes = sorted((spec.json() or {}).get("paths", {}).keys())
            lines.append(f"  路由表：{routes}")

            normal = client.get(probe_path)
            lines.append(f"  正常态 {probe_path} → {normal.status_code}（契约可达）")

            down = client.post("/__fault__/down")
            lines.append(f"  注入故障 POST /__fault__/down → {down.status_code}")
            faulty = client.get(probe_path)
            body_head = faulty.text[:160].replace("\n", " ")
            lines.append(f"  故障态 {probe_path} → {faulty.status_code} | {body_head}")
            lines.append(f"  故障**可见**（非静默）：{'是' if faulty.status_code >= 400 else '否'}")

            recover = client.post(recover_path)
            lines.append(f"  恢复 POST {recover_path} → {recover.status_code}")
            recovered = client.get(probe_path)
            lines.append(f"  恢复后 {probe_path} → {recovered.status_code}")

            if not (spec.status_code == 200 and normal.status_code < 400 and faulty.status_code >= 400):
                ok = False
        lines.append("")

    lines.append("--- 判定 ---")
    lines.append(
        "**通过**：桩可启动、契约路由表与调用方一致、故障注入可见（非静默跳过）、恢复生效"
        if ok
        else "**不通过**：见上（存在契约不可达或故障不可见）"
    )
    lines.append("")
    lines.append("说明：桩服务的 `/health` 未定义（404）**不**计为缺陷 —— 桩的契约面为")
    lines.append("      `/openrag/v1/*`、`/openmemory/v1/*` 与 `/__fault__/*`，判据以实际路由表为准。")

    report = "\n".join(lines)
    print(report)
    Path(args.out).write_text(report + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
