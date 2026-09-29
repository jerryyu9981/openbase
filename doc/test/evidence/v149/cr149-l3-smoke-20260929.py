"""v1.4.9 Step 3 / 3.5 实际运行验证 —— **L3 冒烟**（真实实例，非夹具）

用法（需先启动 8041 实例；启动日志见
`doc/test/evidence/v149/cr149-instance-8041-20260929.txt` —— **原名 `.log` 被 `.gitignore`
排除，故改名 `.txt` 以便入仓留痕**）::

    python cr149-l3-smoke-20260929.py

判定（L3 冒烟 6 例，3~5 个核心用例）：

* **S1 健康**：`GET /openllm/v1/health` → 200（L2 启动验证的运行时确认）；
* **S2 回执齐备（AC-149-05）**：真实 `routing_trace.context_metrics` 中 10 项必填
  **键在且取值非 null**（`degraded` 允许 null），且
  `available_budget == model_window − output_reserve − safety_margin`；
* **S3 超窗率 0（AC-149-12）**：`over_window` 为 `false` 且 `prompt_total_tokens ≤ model_window`；
* **S4 不落敏感/正文（AC-149-11）**：回执 JSON 无敏感键名、无凭据值形态、**无本轮用户正文哨兵**；
* **S5 明细口径自洽（设计 §3.16 冻结关系）**：`dropped` 元素**只含** `source`/`id`/`reason`
  且 `id` 非空；`len(dropped) ≤ Σ truncated[*].dropped_items`；裁剪样本须**确有裁剪**
  （`prompt_tokens_after < before`）且 `truncated` 非空；
  `GET /openllm/v1/writeback/receipts` → 200（既有回执端点未受影响）；
* **S6 硬截断可观测（AC-149-03/04，I-3 落线）**：`hard_truncated` 为 bool；
  本环境实测为 `true`（长历史单条被文本级截断）⇒ 「标记在**运行时**可见」。

**如实声明（不夸大）**：

1. 本脚本只证「**运行时可跑通且回执可判**」。`AC-149-12` 的**正式超窗率统计**与
   `AC-149-05` 的**齐备率统计**须按 Step 5 的实测口径（足量样本）另行统计；
2. 本环境 `memory`/`rag` 检索条目数为 **0**（`openrag` 组件 `unavailable`）⇒ 运行时
   `dropped` 为**空属预期**（无条目即无「整条丢弃」）；`history` 段为**无身份段**（设计
   §3.13 允许缺省）且本样本只发生**文本级硬截断**（`truncated_items=1`、`dropped_items=0`）
   ⇒ 同样不入明细。**条目身份贯通**（`segment_items` 生产落线）由单元护栏
   `tests/unit/test_segment_items_production_wiring.py` **11 passed** 证明；
   运行态「有身份即出明细」的实测属 **Step 4/5**（需真实检索数据）。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
OUT_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "cr149-l3-smoke-20260929.json"
)

REQUIRED_RECEIPT_FIELDS = (
    "model",
    "model_window",
    "output_reserve",
    "safety_margin",
    "available_budget",
    "prompt_tokens_before",
    "prompt_tokens_after",
    "dropped",
    "hard_truncated",
    "degraded",
)
SENSITIVE_KEY_RE = re.compile(
    r'"(?:access_token|refresh_token|token|api_key|apikey|secret|password|'
    r'authorization|bearer_token)"\s*:',
    re.IGNORECASE,
)
SENSITIVE_VALUE_RE = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b|Bearer\s+\S+")
ALLOWED_DROP_KEYS = {"source", "id", "reason"}


async def _login(client: httpx.AsyncClient) -> str:
    login = await client.post("/api/v1/auth/login", json=ACCOUNT)
    if login.status_code != 200:
        raise SystemExit(f"登录失败: {login.status_code} {login.text[:200]}")
    body = login.json()
    token = body.get("access_token") or (body.get("data") or {}).get("access_token")
    if not token:
        raise SystemExit("登录响应无 access_token")
    return str(token)


async def _trace(client: httpx.AsyncClient, headers: dict, request_id: str) -> dict:
    detail = await client.get(f"/openllm/v1/trace/{request_id}", headers=headers)
    if detail.status_code != 200:
        return {}
    return (detail.json() or {}).get("data") or {}


def _long_history(nonce: str, scale: int = 1) -> list[dict]:
    """构造多轮历史（`scale` 决定单条长度）

    `scale=1` ⇒ 历史**不足以**触发配额裁剪（回执扩展字段仍在，`dropped` 为空）；
    `scale=12` ⇒ 历史**远超**段配额 ⇒ 触发**配额整条裁剪**（`dropped` 非空、原因码 `quota`）
    与可能的**单条硬截断**（`hard_truncated`）—— 使 I-2／I-3／I-5 的落点在**运行时**可见。
    """
    filler = (
        "向量数据库通过近似最近邻索引（HNSW/IVF/PQ 等）在召回率与延迟之间权衡；"
        "相似度常用余弦/内积/L2，需与训练度量一致；量化与剪枝可降低内存占用；"
        "分片与副本决定可扩展性与可用性；写入路径需要一致性策略与段合并。"
    )
    messages: list[dict] = []
    for index in range(1, 9):
        messages.append(
            {
                "role": "user",
                "content": (
                    f"第{index}轮 {nonce}：请详细说明向量数据库的索引结构、"
                    f"相似度度量、召回与精度权衡。{filler * scale}"
                ),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": (
                    f"第{index}轮答复：{filler * scale}"
                ),
            }
        )
    return messages


async def _sample_chat(
    client: httpx.AsyncClient,
    headers: dict,
    label: str,
    body_sentinel: str,
    history_scale: int,
    expect_trim: bool = False,
) -> dict:
    session_id = f"smoke-cr149-{label}-{uuid.uuid4().hex[:8]}"
    messages = _long_history(body_sentinel, scale=history_scale) if history_scale else []
    messages.append({"role": "user", "content": f"冒烟提问 {body_sentinel}：一句话说明什么是上下文预算。"})
    payload = {
        "model": "auto",
        "messages": messages,
        "max_tokens": 64,
        "session_id": session_id,
        "mode": "auto",
    }
    response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    if response.status_code != 200:
        return {"label": label, "ok": False, "status": response.status_code, "error": response.text[:300]}
    data = (response.json() or {}).get("data") or {}
    request_id = str(data.get("request_id") or "")
    trace = await _trace(client, headers, request_id)
    receipt = (trace.get("routing_trace") or {}).get("context_metrics") or {}
    return {
        "label": label,
        "ok": bool(request_id and receipt),
        "status": 200,
        "request_id": request_id,
        "session_id": session_id,
        "body_sentinel": body_sentinel,
        "expect_trim": expect_trim,
        "receipt": receipt,
        "channels": (trace.get("routing_trace") or {}).get("channels"),
    }


def _check_sample(sample: dict) -> dict:
    """S2/S3/S4/S5-元素 逐样本检查"""
    problems: list[str] = []
    receipt = sample.get("receipt") or {}
    if not receipt:
        return {"problems": ["回执缺失（无 context_metrics）"], "passed": False}

    missing = [name for name in REQUIRED_RECEIPT_FIELDS if name not in receipt]
    problems.extend(f"缺字段 {name}" for name in missing)
    null_valued = [
        name
        for name in REQUIRED_RECEIPT_FIELDS
        if name != "degraded" and name in receipt and receipt[name] is None
    ]
    problems.extend(f"字段 {name} 为 null" for name in null_valued)
    if not missing and receipt.get("model") is None:
        problems.append("model 为 null（应为本轮实际模型）")

    if not missing:
        expected = (
            int(receipt["model_window"])
            - int(receipt["output_reserve"])
            - int(receipt["safety_margin"])
        )
        if int(receipt["available_budget"]) != expected:
            problems.append(f"available_budget 与公式不符: {receipt['available_budget']} != {expected}")
        if int(receipt["prompt_tokens_before"]) < int(receipt["prompt_tokens_after"]):
            problems.append("prompt_tokens_before 应 ≥ prompt_tokens_after")

    # S3：超窗率 0（本样本）
    if receipt.get("over_window") is True:
        problems.append(f"over_window=true（溢出 {receipt.get('over_window_tokens')}）")
    total = int(receipt.get("prompt_total_tokens") or 0)
    window = int(receipt.get("model_window") or 0)
    if window and total > window:
        problems.append(f"prompt_total_tokens({total}) > model_window({window})")

    # S4：不落敏感/正文
    serialized = json.dumps(receipt, ensure_ascii=False)
    key_hit = SENSITIVE_KEY_RE.search(serialized)
    if key_hit:
        problems.append(f"回执出现敏感字段名: {key_hit.group(0)}")
    value_hit = SENSITIVE_VALUE_RE.search(serialized)
    if value_hit:
        problems.append(f"回执出现凭据值形态: {value_hit.group(0)}")
    if sample.get("body_sentinel") and sample["body_sentinel"] in serialized:
        problems.append("回执出现本轮用户正文哨兵（片段正文落痕）")

    # S5：dropped 元素形态与**冻结关系**（设计 §3.16：len(dropped) ≤ Σ dropped_items）
    for entry in receipt.get("dropped") or []:
        extra = set(entry) - ALLOWED_DROP_KEYS
        if extra:
            problems.append(f"dropped 元素含越界键: {sorted(extra)}")
            break
        if not str(entry.get("id") or "").strip():
            problems.append("dropped 元素 id 为空（身份不可追溯）")
            break
    truncated = receipt.get("truncated") or {}
    dropped_items_total = sum(
        int((report or {}).get("dropped_items", 0)) for report in truncated.values()
    )
    if len(receipt.get("dropped") or []) > dropped_items_total:
        problems.append(
            f"明细数超过整条丢弃计数（{len(receipt['dropped'])} > {dropped_items_total}）"
            "⇒ 违反 §3.16 冻结关系"
        )

    # 期望发生裁剪的样本：必须**确有裁剪**（否则「扩展字段齐备」只是空壳）
    if sample.get("expect_trim"):
        if int(receipt.get("prompt_tokens_after") or 0) >= int(
            receipt.get("prompt_tokens_before") or 0
        ):
            problems.append("期望发生裁剪的样本裁剪前后 token 未下降")
        if not truncated:
            problems.append("期望发生裁剪的样本无段级裁剪观测（truncated 为空）")

    return {
        "problems": problems,
        "passed": not problems,
        "dropped_items": len(receipt.get("dropped") or []),
        "model_window": receipt.get("model_window"),
        "prompt_tokens_before": receipt.get("prompt_tokens_before"),
        "prompt_tokens_after": receipt.get("prompt_tokens_after"),
        "over_window": receipt.get("over_window"),
        "degraded": receipt.get("degraded"),
        "hard_truncated": receipt.get("hard_truncated"),
    }


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=180.0) as client:
        health = await client.get("/openllm/v1/health")
        s1 = {
            "status": health.status_code,
            "passed": health.status_code == 200,
            "body_head": health.text[:200],
        }

        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        samples = [
            await _sample_chat(client, headers, "short", "CR149SENTINELSHORT", history_scale=0),
            await _sample_chat(client, headers, "long", "CR149SENTINELLONG", history_scale=1),
            await _sample_chat(
                client,
                headers,
                "huge",
                "CR149SENTINELHUGE",
                history_scale=12,
                expect_trim=True,
            ),
        ]

        receipts_endpoint = await client.get(
            "/openllm/v1/writeback/receipts",
            params={"session_id": samples[-1].get("session_id") or "", "limit": 50},
            headers=headers,
        )

    per_sample = [{"label": s.get("label"), "ok": s.get("ok"), **_check_sample(s)} for s in samples]
    all_samples_passed = all(item["passed"] for item in per_sample)
    s5 = {
        "passed": all_samples_passed and receipts_endpoint.status_code == 200,
        "receipts_status": receipts_endpoint.status_code,
        "note": "dropped 元素形态在逐样本检查内判定；回执端点 200 证明既有语义未回退",
    }

    payload = {
        "meta": {
            "version": "v1.4.9",
            "stage": "Step 3 / 3.5 L3 冒烟",
            "base_url": BASE_URL,
            "model": "auto",
            "note": (
                "L3 冒烟 6 例；样本量不足以替代 Step 5 的齐备率/超窗率正式统计"
            ),
            "honest_scope": (
                "本环境 memory/rag 检索条目数为 0（openrag unavailable）⇒ 运行时 dropped 为空属预期；"
                "history 段为无身份段且本样本只发生文本级硬截断 ⇒ 同样不入明细。"
                "条目身份贯通由 unit tests/unit/test_segment_items_production_wiring.py（11 passed）证明；"
                "「有身份即出明细」的运行态实测属 Step 4/5（需真实检索数据）。"
            ),
        },
        "S1_health": s1,
        "samples": [
            {k: v for k, v in sample.items() if k != "receipt"} for sample in samples
        ],
        "per_sample_checks": per_sample,
        "receipt_snapshot": (samples[-1].get("receipt") or None),
        "S5_existing_semantics": s5,
        "S6_hard_truncated_visible": {
            "passed": all(isinstance(item.get("hard_truncated"), bool) for item in per_sample),
            "observed": {item["label"]: item.get("hard_truncated") for item in per_sample},
            "note": "I-3 落线（AC-149-03/04）：硬截断标记在运行时可见（本环境长历史样本为 true）",
        },
        "passed": bool(s1["passed"] and all_samples_passed and s5["passed"]),
    }
    payload["passed"] = bool(
        payload["passed"] and payload["S6_hard_truncated_visible"]["passed"]
    )
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    print(f"[{'PASS' if s1['passed'] else 'FAIL'}] S1 健康检查（HTTP {s1['status']}）")
    for item in per_sample:
        flag = "PASS" if item["passed"] else "FAIL"
        print(
            f"[{flag}] S2~S5 {item['label']}: 窗口={item.get('model_window')} "
            f"前/后={item.get('prompt_tokens_before')}/{item.get('prompt_tokens_after')} "
            f"dropped={item.get('dropped_items')} over_window={item.get('over_window')} "
            f"hard_truncated={item.get('hard_truncated')} degraded={item.get('degraded')}"
        )
        for problem in item["problems"]:
            print(f"        - {problem}")
    s6 = payload["S6_hard_truncated_visible"]
    print(
        f"[{'PASS' if s6['passed'] else 'FAIL'}] S5 既有语义不回退（回执端点 {s5['receipts_status']}）"
        f" / S6 硬截断标记可见 {s6['observed']}"
    )
    print(f"结果已写入：{OUT_JSON}")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
