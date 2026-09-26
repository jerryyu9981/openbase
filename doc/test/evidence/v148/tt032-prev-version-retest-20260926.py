"""TT-032 复测（v1.4.8 Step 4 剩余项 ⑤）—— 上一版本（v1.4.7）失败项 / 跳过项逐项复测

对应 v1.4.7 报告条目：

* **TT-147-009（跳过项 → 已补跑）**：四仓 R-384 专项单测逐仓复跑 —— 本轮复跑见
  `tt032-four-repo-rerun-20260926.json`（与基线 10 / 7 / 12 / 7 逐仓对照）。
* **TT-147-005（失败项 → 已修复）**：四仓串联一致性 —— 其**运行态**复测需
  OpenBase 代理（8001）+ DPS + OpenRAG 运行态（本环境三者均未运行）→ 记为 **H 类**；
  本脚本复测其**可运行责任面**：OpenLLM 网关的 `X-Request-Id` **受信透传复用 /
  非受信防伪造**语义（`app/identity/request_id.py`，v1.4.7 串联链的一环）。
* **TT-147-004（失败项 → 已修复）**：OpenRAG 应用日志 JSONL 契约 —— 运行态需 OpenRAG
  服务；本轮以**仓内实现静态复核**（`json_format=settings.is_production or settings.log_json`）留证。
* **跳过项（v1.4.7 T3a 全页面巡检 / T4 UAT、性能压测）**：v1.4.7 声明为范围外；v1.4.8 由
  自身用例承接（T3a→`TT-028`、T3b→`TT-029`、UAT→`TT-041~044`、性能→`TT-038/039`），已闭合。

本脚本判据（逐条可复算）：

1. **非受信来源防伪造 100%（可判定）**：仅携入站 `X-Request-Id`（无受信来源）时，网关**忽略**
   该值并自行生成 —— 响应体 `request_id` ≠ 入站值。
2. **受信来源复用（本轮不可经 HTTP 判定，如实登记）**：关联 id `req-{12hex}`
   （`app/identity/request_id.py`）**只落应用日志与出站头**，不经响应体 / trace 暴露
   （实测：响应体与 trace 仅含网关自有 `openllm-…` id）→ 其复用语义须以**应用日志原文命中**
   或**代理运行态**验证（OpenBase 代理 8001 + 采集目录），本环境不可达 → 记为**受限项**，
   以四仓 R-384 专项单测复跑（36/36）作单元级回归证据。

用法::

    python tt032-prev-version-retest-20260926.py

退出码：0＝批次完成（达标与否见输出与 JSON `verdict`）。
"""
from __future__ import annotations

import json
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
TRUSTED_SOURCE = "openbase-llm-proxy"
OUT_DIR = r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148"
SAMPLES = 5


def _login(client: httpx.Client) -> str:
    resp = client.post("/api/v1/auth/login", json=ACCOUNT)
    if resp.status_code != 200:
        raise SystemExit(f"登录失败: {resp.status_code} {resp.text[:200]}")
    token = resp.json().get("access_token")
    if not token:
        raise SystemExit("登录响应无 access_token")
    return str(token)


def _chat(client: httpx.Client, headers: dict[str, str], query: str) -> httpx.Response:
    return client.post(
        "/openllm/v1/chat",
        headers=headers,
        json={"query": query, "mode": "auto", "output_mode": "llm_response"},
    )


def _body_request_id(resp: httpx.Response) -> str | None:
    try:
        data = resp.json().get("data") or {}
        return data.get("request_id")
    except Exception:
        return None


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        health = client.get("/openllm/v1/health")
        token = _login(client)
        auth = {"Authorization": f"Bearer {token}"}

        trusted_records = []
        untrusted_records = []

        # 受信档：仅作观测（关联 id 不经 HTTP 暴露 → 本项不可经 HTTP 判定）
        for _ in range(SAMPLES):
            rid = f"req-{uuid.uuid4().hex[:12]}"
            resp = _chat(
                client,
                {**auth, "X-Proxy-Source": TRUSTED_SOURCE, "X-Request-Id": rid},
                f"TT032 受信透传观测 {rid}",
            )
            trusted_records.append(
                {
                    "inbound_request_id": rid,
                    "chat_status": resp.status_code,
                    "body_request_id": _body_request_id(resp),
                    "evaluable": False,
                    "note": "关联 id(req-…) 只落应用日志与出站头；响应体仅含网关自有 openllm-… id → 须日志/代理运行态判定",
                }
            )

        for _ in range(SAMPLES):
            rid = f"req-{uuid.uuid4().hex[:12]}"
            resp = _chat(client, {**auth, "X-Request-Id": rid}, f"TT032 非受信防伪造探针 {rid}")
            body_rid = _body_request_id(resp)
            untrusted_records.append(
                {
                    "inbound_request_id": rid,
                    "chat_status": resp.status_code,
                    "body_request_id": body_rid,
                    "ignored_inbound": body_rid is not None and body_rid != rid,
                }
            )

        echo_header = client.get("/openllm/v1/health").headers.get("X-Request-Id")

    untrusted_ok = sum(1 for r in untrusted_records if r["ignored_inbound"])

    failures = []
    if untrusted_ok != SAMPLES:
        failures.append({"rule": "untrusted-forgery-rejected-100%", "reason": f"{untrusted_ok}/{SAMPLES}"})

    verdict = {
        "pass": not failures,
        "scope": "有限口径（含受限项，见 limited_items）",
        "rules_checked": ["untrusted-forgery-rejected-100%"],
        "untrusted_rejected_ok": f"{untrusted_ok}/{SAMPLES}",
        "limited_items": [
            "受信来源复用入站 X-Request-Id（关联 id 仅落应用日志/出站头，HTTP 不可观测；须 OpenBase 代理 8001 + 应用日志运行态）",
            "四仓应用日志原文命中 100%（TT-147-005 跨仓部分；须四仓运行态与采集目录）",
            "X-Request-Id 响应回带（OpenBase 代理责任面；8001 未运行）",
            "OpenRAG 应用日志 JSONL 契约运行态（TT-147-004；本环境 OpenRAG 不可达）",
        ],
        "failures": failures,
    }

    for rec in trusted_records:
        print(f".. [trusted/观测]  in={rec['inbound_request_id']} chat={rec['chat_status']} "
              f"body={rec['body_request_id']}")
    for rec in untrusted_records:
        flag = "OK " if rec["ignored_inbound"] else "!! "
        print(f"{flag}[untrusted] in={rec['inbound_request_id']} chat={rec['chat_status']} "
              f"body={rec['body_request_id']}")
    print()
    print(f"健康端点 X-Request-Id 回带: {echo_header!r}（回带责任面在 OpenBase 代理，8001 未运行 → 受限项）")
    print(f"判定: {json.dumps(verdict, ensure_ascii=False)}")

    out = {
        "case": "TT-032 上一版本（v1.4.7）失败项 / 跳过项复测",
        "date": "2026-09-26",
        "base_url": BASE_URL,
        "health": {"status": health.status_code, "body": health.text[:400]},
        "gateway_request_id_semantics": {
            "trusted_source_header": TRUSTED_SOURCE,
            "samples": SAMPLES,
            "trusted_records": trusted_records,
            "untrusted_records": untrusted_records,
            "health_echo_header": echo_header,
            "verdict": verdict,
        },
        "limited_scope_items": [
            "TT-147-005 受信来源复用入站 X-Request-Id（关联 id 仅落应用日志/出站头，HTTP 不可观测；须 OpenBase 代理 8001 + 应用日志运行态）",
            "TT-147-005 跨仓「四仓应用日志原文命中 100%」（运行态需 OpenBase 代理 8001 + DPS + OpenRAG；本环境均未运行）→ 以四仓 R-384 专项单测复跑作单元级回归证据（不等价于运行态复测）",
            "X-Request-Id 响应回带（OpenBase 代理责任面；8001 未运行）",
            "TT-147-004 OpenRAG 应用日志 JSONL 契约运行态（本环境 OpenRAG 不可达）→ 已以仓内实现静态复核留证",
        ],
    }
    path = f"{OUT_DIR}/tt032-prev-version-retest-20260926.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(f"证据: {path}")


if __name__ == "__main__":
    main()
