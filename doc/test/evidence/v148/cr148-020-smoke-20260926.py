"""L3 冒烟：CR-148-020 流式回写「后台派发 + 回执另行持久化」（P-10 口径）

用法::

    python cr148-020-smoke-20260926.py

判定（L3 冒烟，非性能正式分位）：

* **L2**：`GET /openllm/v1/health` → 200；
* **P-10（流式）**：每次流式对话的 timeline 中 `writeback_dispatch` **≤5 ms**
  （改造前实测 556~728 ms；现请求路径只创建后台任务）；
* **回执另行持久化**：`done` 之后 `GET /openllm/v1/trace/{request_id}` 的
  `routing_trace.writeback` 应包含三路（memory / rag / profile）+ `_dispatch.mode == "async"`
  （由后台任务补写；`done` 时点仅写 `scheduled` 占位）；
* **权威回执（队列表）**：`GET /openllm/v1/writeback/receipts?session_id=…` → 200，
  且能看到本次会话的行（若有可回写通道）；
* **既有语义不回退**：同步路径 `writeback_dispatch` 仍在（CR-148-018 未回退）。
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
    r"\cr148-020-smoke-20260926.json"
)
TARGET_MS = 5.0
STREAM_SAMPLES = 3
RECEIPT_WAIT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.25


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


async def _trace_payload(client: httpx.AsyncClient, headers: dict, request_id: str) -> dict:
    detail = await client.get(f"/openllm/v1/trace/{request_id}", headers=headers)
    if detail.status_code != 200:
        return {}
    return ((detail.json() or {}).get("data") or {})


def _steps(trace_data: dict) -> dict:
    timeline = trace_data.get("timeline") or []
    return {str(item.get("step")): float(item.get("ms") or 0) for item in timeline}


async def _chat_stream(client: httpx.AsyncClient, headers: dict, index: int) -> dict:
    nonce = uuid.uuid4().hex[:12]
    session_id = f"smoke-cr148020-stream-{index}"
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"流式冒烟 {nonce}：请用一句话说明什么是向量数据库"}],
        "max_tokens": 200,
        "session_id": session_id,
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

    # done 时点的 trace（此时回执为 scheduled 占位）
    immediate = await _trace_payload(client, headers, request_id)
    immediate_writeback = (immediate.get("routing_trace") or {}).get("writeback")

    # 等待后台任务补写回执（另行持久化）
    persisted: dict | None = None
    waited = 0.0
    while waited <= RECEIPT_WAIT_SECONDS:
        trace_data = await _trace_payload(client, headers, request_id)
        writeback = (trace_data.get("routing_trace") or {}).get("writeback") or {}
        if isinstance(writeback, dict) and writeback.get("_dispatch", {}).get("status") == "completed":
            persisted = writeback
            break
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        waited += POLL_INTERVAL_SECONDS

    steps = _steps(immediate)
    return {
        "ok": bool(request_id),
        "status": 200,
        "request_id": request_id,
        "session_id": session_id,
        "wall_ms": round(wall_ms, 1),
        "events": events,
        "delta_count": delta_count,
        "steps": steps,
        "steps_seen": sorted(steps),
        "writeback_dispatch_ms": steps.get("writeback_dispatch"),
        "immediate_writeback": immediate_writeback,
        "persisted_writeback": persisted,
        "receipt_wait_seconds": round(waited, 2),
    }


async def _chat_sync(client: httpx.AsyncClient, headers: dict) -> dict:
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"同步冒烟 {nonce}：请用一句话说明什么是向量数据库"}],
        "max_tokens": 32,
        "session_id": f"smoke-cr148020-sync-{nonce}",
        "mode": "auto",
    }
    response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    if response.status_code != 200:
        return {"ok": False, "status": response.status_code, "error": response.text[:200]}
    data = (response.json() or {}).get("data") or {}
    trace_data = await _trace_payload(client, headers, str(data.get("request_id") or ""))
    steps = _steps(trace_data)
    return {
        "ok": True,
        "status": 200,
        "steps_seen": sorted(steps),
        "writeback_dispatch_ms": steps.get("writeback_dispatch"),
    }


def _verdict(streams: list[dict], sync_sample: dict, receipts: dict) -> dict:
    all_ok = all(s.get("ok") for s in streams)
    dispatch_values = [float(s.get("writeback_dispatch_ms") or 0) for s in streams]
    persisted_all = all(
        isinstance(s.get("persisted_writeback"), dict)
        and {"memory", "rag", "profile"} <= set(s["persisted_writeback"])
        for s in streams
    )
    async_mode = all(
        (s.get("persisted_writeback") or {}).get("_dispatch", {}).get("mode") == "async"
        for s in streams
    )
    sync_kept = "writeback_dispatch" in (sync_sample.get("steps_seen") or [])
    within_target = bool(dispatch_values) and all(v <= TARGET_MS for v in dispatch_values)
    return {
        "pass": bool(
            all_ok and within_target and persisted_all and async_mode and sync_kept
            and receipts.get("status") == 200
        ),
        "check": (
            "流式 writeback_dispatch ≤5 ms（P-10 达标）+ 三路回执由后台任务另行持久化"
            "（_dispatch.mode=async）+ 权威回执端点 200 + 同步路径步骤保留"
        ),
        "all_stream_ok": all_ok,
        "stream_writeback_dispatch_ms": dispatch_values,
        "stream_dispatch_within_5ms": within_target,
        "stream_receipt_persisted_all": persisted_all,
        "stream_receipt_async_mode": async_mode,
        "sync_step_kept": sync_kept,
        "receipts_status": receipts.get("status"),
        "receipts_total": receipts.get("total"),
        "note": "本轮为 L3 冒烟（n=3 流式 + 1 同步），P-10 正式分位判定须按每档 ≥200 请求重跑 TT-038",
    }


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        health = await client.get("/openllm/v1/health")
        health_data = (health.json() or {}).get("data") or {}
        print("[L2] health:", health.status_code, health_data.get("status"), health_data.get("version"))

        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        streams: list[dict] = []
        for index in range(STREAM_SAMPLES):
            sample = await _chat_stream(client, headers, index)
            streams.append(sample)
            print(
                f"[流式 #{index + 1}] status={sample.get('status')} "
                f"chunks={sample.get('delta_count')} "
                f"writeback_dispatch={sample.get('writeback_dispatch_ms')}ms "
                f"done时占位={sample.get('immediate_writeback')} "
                f"补写后={sample.get('persisted_writeback')} "
                f"(等待 {sample.get('receipt_wait_seconds')}s)"
            )

        sync_sample = await _chat_sync(client, headers)
        print(
            f"[同步] status={sync_sample.get('status')} 步骤={sync_sample.get('steps_seen')} "
            f"writeback_dispatch={sync_sample.get('writeback_dispatch_ms')}ms"
        )

        session_id = streams[0].get("session_id") if streams else None
        receipts_resp = await client.get(
            "/openllm/v1/writeback/receipts", headers=headers,
            params={"session_id": session_id, "limit": 50},
        )
        receipts_body = receipts_resp.json() if receipts_resp.status_code == 200 else {}
        receipts = {
            "status": receipts_resp.status_code,
            "total": receipts_body.get("total"),
            "items": [
                {"target": row.get("target"), "status": row.get("status"), "seq": row.get("seq")}
                for row in (receipts_body.get("items") or [])
            ],
        }
        print("[权威回执/队列表]", json.dumps(receipts, ensure_ascii=False))

    verdict = _verdict(streams, sync_sample, receipts)
    result = {
        "case": "CR-148-020 流式回写后台派发 + 回执另行持久化",
        "date": "2026-09-26",
        "base_url": BASE_URL,
        "health": {"status": health.status_code, "data": health_data.get("status")},
        "streams": streams,
        "sync": sync_sample,
        "receipts": receipts,
        "verdict": verdict,
    }
    print("判定:", json.dumps(verdict, ensure_ascii=False))
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("证据:", OUT_JSON)
    return 0 if verdict.get("pass") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
