"""L3 冒烟：CR-148-018 回写派发计量接线（`writeback_dispatch` 步骤，P-10 口径）

用法::

    python cr148-018-smoke-20260926.py

判定（L3 冒烟，非性能正式分位）：

* 全部对话 200；
* **同步路径**（`/openllm/v1/chat`）：timeline 步骤集合含 `writeback_dispatch`，
  且该步耗时 ≤ 5 ms（P-10 目标：请求路径内回写派发的同步新增耗时 P99 ≤5 ms）；
* **流式路径**（`/openllm/v1/chat/stream`）：同上（流式路径在请求路径内**同步**入队）；
* 步骤集合由 `['auth','llm','profile_fetch',…]` 扩展为含 `writeback_dispatch`，
  使「未计量差额」可继续收敛（P-1 残留 ≈1110 ms 的归因面）。
"""
import asyncio
import json
import sys
import time
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
OUT_JSON = (
    r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148"
    r"\cr148-018-smoke-20260926.json"
)
SYNC_SAMPLES = 3
STREAM_SAMPLES = 2
TARGET_MS = 5.0


async def _login(client: httpx.AsyncClient) -> str:
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": ACCOUNT["username"], "password": ACCOUNT["password"]},
    )
    if login.status_code != 200:
        raise SystemExit(f"登录失败: {login.status_code} {login.text[:200]}")
    body = login.json()
    token = body.get("access_token") or (body.get("data") or {}).get("access_token")
    if not token:
        raise SystemExit("登录响应无 access_token")
    return str(token)


async def _timeline_of(client: httpx.AsyncClient, headers: dict, request_id: str) -> dict:
    detail = await client.get(f"/openllm/v1/trace/{request_id}", headers=headers)
    if detail.status_code != 200:
        return {}
    timeline = ((detail.json() or {}).get("data") or {}).get("timeline") or []
    return {str(item.get("step")): float(item.get("ms") or 0) for item in timeline}


async def _chat_sync(client: httpx.AsyncClient, headers: dict, index: int) -> dict:
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"冒烟 {nonce}：请用一句话说明什么是向量数据库"}],
        "max_tokens": 32,
        "session_id": f"smoke-cr148018-sync-{index}",
        "mode": "auto",
    }
    started = time.perf_counter()
    response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    wall_ms = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        return {"ok": False, "status": response.status_code, "error": response.text[:200]}
    data = (response.json() or {}).get("data") or {}
    steps = await _timeline_of(client, headers, str(data.get("request_id") or ""))
    return {
        "ok": True,
        "status": 200,
        "wall_ms": round(wall_ms, 1),
        "steps": steps,
        "steps_seen": sorted(steps),
        "writeback_dispatch_ms": steps.get("writeback_dispatch"),
        "has_writeback_dispatch": "writeback_dispatch" in steps,
        "unaccounted_ms": round(wall_ms - sum(steps.values()), 1),
    }


async def _chat_stream(client: httpx.AsyncClient, headers: dict, index: int) -> dict:
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"流式冒烟 {nonce}：请用一句话说明什么是向量数据库"}],
        # max_tokens 取 200：32 时本环境出现过「无 chunk 事件」的空流（stream_answer_text 为空
        # → 触发既有「空响应不回写」语义 → 回写块不执行），会掩盖计量存在性判定
        "max_tokens": 200,
        "session_id": f"smoke-cr148018-stream-{index}",
        "mode": "auto",
    }
    request_id = ""
    events: list[str] = []
    delta_count = 0
    started = time.perf_counter()
    async with client.stream(
        "POST", "/openllm/v1/chat/stream", json=payload, headers=headers
    ) as response:
        if response.status_code != 200:
            body = (await response.aread()).decode("utf-8", "replace")
            return {"ok": False, "status": response.status_code, "error": body[:200]}
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
                events.append(event)
                if event == "chunk":
                    delta_count += 1
            elif line.startswith("data:"):
                raw = line.split(":", 1)[1].strip()
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict) and parsed.get("request_id"):
                    request_id = str(parsed["request_id"])
    wall_ms = (time.perf_counter() - started) * 1000
    steps = await _timeline_of(client, headers, request_id)
    return {
        "ok": bool(request_id),
        "status": 200,
        "wall_ms": round(wall_ms, 1),
        "events": events,
        "delta_count": delta_count,
        "steps": steps,
        "steps_seen": sorted(steps),
        "writeback_dispatch_ms": steps.get("writeback_dispatch"),
        "has_writeback_dispatch": "writeback_dispatch" in steps,
    }


def _verdict(sync_samples: list[dict], stream_samples: list[dict]) -> dict:
    sync_ok = all(s.get("ok") for s in sync_samples) and all(
        s.get("has_writeback_dispatch") for s in sync_samples
    )
    # 流式：仅统计「有 chunk（stream_answer_text 非空）」的样本 —— 空响应按既有
    # 「空响应不回写」语义本就不进回写块，属预期而非缺陷
    judged_stream = [s for s in stream_samples if int(s.get("delta_count") or 0) > 0]
    empty_stream = [s for s in stream_samples if int(s.get("delta_count") or 0) == 0]
    stream_ok = bool(judged_stream) and all(
        s.get("has_writeback_dispatch") for s in judged_stream
    )
    sync_values = [float(s.get("writeback_dispatch_ms") or 0) for s in sync_samples]
    stream_values = [
        float(s.get("writeback_dispatch_ms") or 0) for s in judged_stream
    ]
    within_target = all(v <= TARGET_MS for v in sync_values + stream_values)
    return {
        "pass": bool(sync_ok and stream_ok),
        "check": (
            "同步与流式两条路径的 timeline 均产出 writeback_dispatch 步骤"
            "（存在性判定；耗时为观测值，P-10 正式判定须按每档 ≥200 请求出分位）"
        ),
        "sync_all_have_step": sync_ok,
        "stream_all_have_step": stream_ok,
        "stream_judged_samples": len(judged_stream),
        "stream_empty_response_samples": len(empty_stream),
        "sync_writeback_dispatch_ms": sync_values,
        "stream_writeback_dispatch_ms": stream_values,
        "observed_max_ms": max(sync_values + stream_values) if (sync_values or stream_values) else None,
        "within_5ms_observed": within_target,
    }


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        health = await client.get("/openllm/v1/health")
        health_data = (health.json() or {}).get("data") or {}
        print(
            "[L2] health:",
            health.status_code,
            health_data.get("status"),
            health_data.get("version"),
        )

        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        sync_samples = []
        for index in range(SYNC_SAMPLES):
            sample = await _chat_sync(client, headers, index)
            sync_samples.append(sample)
            print(
                f"[同步 #{index + 1}] status={sample.get('status')} "
                f"步骤={sample.get('steps_seen')} writeback_dispatch="
                f"{sample.get('writeback_dispatch_ms')}ms"
            )

        stream_samples = []
        for index in range(STREAM_SAMPLES):
            sample = await _chat_stream(client, headers, index)
            stream_samples.append(sample)
            print(
                f"[流式 #{index + 1}] status={sample.get('status')} "
                f"步骤={sample.get('steps_seen')} writeback_dispatch="
                f"{sample.get('writeback_dispatch_ms')}ms"
            )

    verdict = _verdict(sync_samples, stream_samples)
    result = {
        "case": "CR-148-018 回写派发计量接线（writeback_dispatch）",
        "date": "2026-09-26",
        "base_url": BASE_URL,
        "health": {"status": health.status_code, "data": health_data.get("status")},
        "sync_samples": sync_samples,
        "stream_samples": stream_samples,
        "verdict": verdict,
    }
    print("判定:", json.dumps(verdict, ensure_ascii=False))
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("证据:", OUT_JSON)
    return 0 if verdict.get("pass") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
