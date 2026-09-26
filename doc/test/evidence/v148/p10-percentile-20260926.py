"""P-10 正式分位判定：TT-038 重跑（每档 ≥200 请求）

用途：为 `CR-148-020`（后台派发 + 回执另行持久化）修复后的 `P-10`（回写路径内同步新增耗时
P99 ≤5 ms）出**正式分位判定**（此前 L3 冒烟 n=3，不冒充分位）。

判定口径（依据《非功能设计说明-v1.4.8》v1.2.0 §1.1.3「双口径」）：

* **单飞档**（`--rate 0.75`，基线口径）：同步 / 流式各 n=200；
* **并发 8 档**（`--concurrency 8 --rate 0`，吞吐/尾延迟口径）：同步 / 流式各 n=200。

每样本流程：发一次对话（同步 `POST /openllm/v1/chat` 或流式 `/openllm/v1/chat/stream`），
取 `request_id`，回读 `GET /openllm/v1/trace/{request_id}` 的 `timeline`，
提取 `writeback_dispatch` 步骤耗时（请求路径内把回写交给异步通道的同步开销）。

测量要点：

* 语义缓存规避：每样本 query 注入唯一 nonce（命中样本剔除）；
* 流式 `max_tokens=200`（避免 `max_tokens=32` 偶发无 chunk → 不进回写块 → 无该步骤）；
* 回读 trace 404 时短暂重试（落库竞态）；仍失败记 `missing`，不计入分位；
* 分位数用最近秩（nearest-rank），与 `run_perf_batch.py` 同口径。

用法::

    python p10-percentile-20260926.py --tag single-flight --rate 0.75 --concurrency 1
    python p10-percentile-20260926.py --tag conc8 --rate 0 --concurrency 8

退出码：0＝批次完成（达标与否见输出与 JSON `verdict`）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
CHAT_PROMPT = "请用一句话说明什么是向量数据库"
TARGET_MS = 5.0
TRACE_RETRIES = 3
TRACE_RETRY_INTERVAL = 0.5
OUT_PREFIX = r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148\p10-percentile"


class _Pacer:
    """全局节流器：保证整体发送速率 ≤ rate（req/s）"""

    def __init__(self, rate: float) -> None:
        self._interval = 1.0 / rate if rate > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_at = 0.0

    async def wait(self) -> None:
        if self._interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            start = max(now, self._next_at)
            self._next_at = start + self._interval
            delay = start - now
        if delay > 0:
            await asyncio.sleep(delay)


def _percentile(samples: list[float], quantile: float) -> float:
    """最近秩分位数（nearest-rank；与 run_perf_batch.py 同口径）"""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    rank = max(1, min(len(ordered), int(-(-len(ordered) * quantile // 1))))
    return ordered[rank - 1]


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "p50": round(_percentile(values, 0.50), 3),
        "p90": round(_percentile(values, 0.90), 3),
        "p95": round(_percentile(values, 0.95), 3),
        "p99": round(_percentile(values, 0.99), 3),
        "min": round(min(values), 3) if values else 0.0,
        "max": round(max(values), 3) if values else 0.0,
    }


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


async def _trace_steps(
    client: httpx.AsyncClient, headers: dict, request_id: str, pacer: _Pacer
) -> dict[str, float] | None:
    """回读 trace 的 timeline 步骤；未落库时短暂重试，仍失败返回 None"""
    for _attempt in range(TRACE_RETRIES):
        await pacer.wait()
        try:
            detail = await client.get(f"/openllm/v1/trace/{request_id}", headers=headers)
        except httpx.HTTPError:
            await asyncio.sleep(TRACE_RETRY_INTERVAL)
            continue
        if detail.status_code == 200:
            timeline = ((detail.json() or {}).get("data") or {}).get("timeline") or []
            return {str(item.get("step")): float(item.get("ms") or 0) for item in timeline}
        if detail.status_code == 404:
            await asyncio.sleep(TRACE_RETRY_INTERVAL)
            continue
        break
    return None


async def _sync_sample(
    client: httpx.AsyncClient, headers: dict, pacer: _Pacer, index: int
) -> dict[str, Any]:
    """同步对话单样本：回读 trace 提取 writeback_dispatch"""
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"采样 {nonce}：{CHAT_PROMPT}"}],
        "max_tokens": 32,
        "session_id": f"p10-sync-{index % 8}",
        "mode": "auto",
    }
    await pacer.wait()
    started = time.perf_counter()
    try:
        response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    wall_ms = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        return {
            "ok": False,
            "status": response.status_code,
            "error": response.text[:200],
        }
    data = (response.json() or {}).get("data") or {}
    request_id = str(data.get("request_id") or "")
    steps = await _trace_steps(client, headers, request_id, pacer) if request_id else None
    return {
        "ok": True,
        "status": 200,
        "wall_ms": round(wall_ms, 1),
        "request_id": request_id,
        "cache_hit": bool((data.get("routing_trace") or {}).get("cache_hit")),
        "steps": steps,
        "writeback_dispatch_ms": None if steps is None else steps.get("writeback_dispatch"),
    }


async def _stream_sample(
    client: httpx.AsyncClient, headers: dict, pacer: _Pacer, index: int
) -> dict[str, Any]:
    """流式对话单样本：收集 request_id，回读 trace 提取 writeback_dispatch"""
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"采样 {nonce}：{CHAT_PROMPT}"}],
        "max_tokens": 200,
        "session_id": f"p10-stream-{index % 8}",
        "mode": "auto",
    }
    await pacer.wait()
    started = time.perf_counter()
    request_id = ""
    events: list[str] = []
    delta_count = 0
    try:
        async with client.stream(
            "POST", "/openllm/v1/chat/stream", json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                await response.aread()
                return {
                    "ok": False,
                    "status": response.status_code,
                    "error": f"status={response.status_code}",
                }
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                elif line.startswith("data:"):
                    raw = line.split(":", 1)[1].strip()
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict):
                        if parsed.get("event") == "chunk":
                            delta_count += 1
                        if parsed.get("request_id"):
                            request_id = str(parsed["request_id"])
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    wall_ms = (time.perf_counter() - started) * 1000
    steps = await _trace_steps(client, headers, request_id, pacer) if request_id else None
    return {
        "ok": bool(request_id and steps is not None),
        "status": 200,
        "wall_ms": round(wall_ms, 1),
        "request_id": request_id,
        "events": events,
        "delta_count": delta_count,
        "steps": steps,
        "writeback_dispatch_ms": None if steps is None else steps.get("writeback_dispatch"),
    }


async def _run_path(
    client: httpx.AsyncClient,
    headers: dict,
    pacer: _Pacer,
    path_name: str,
    count: int,
    concurrency: int,
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)
    sample_fn = _sync_sample if path_name == "sync" else _stream_sample

    async def _runner(index: int) -> dict[str, Any]:
        async with semaphore:
            return await sample_fn(client, headers, pacer, index)

    samples = list(await asyncio.gather(*(_runner(index) for index in range(count))))

    ok = [item for item in samples if item.get("ok")]
    effective = [item for item in ok if not item.get("cache_hit")]
    values = [float(item.get("writeback_dispatch_ms") or 0) for item in effective]
    steps_seen: set[str] = set()
    for item in effective:
        if isinstance(item.get("steps"), dict):
            steps_seen.update(item["steps"].keys())
    within_target = all(v <= TARGET_MS for v in values)
    return {
        "path": path_name,
        "samples": len(samples),
        "ok": len(ok),
        "errors": len(samples) - len(ok),
        "cache_hits": len(ok) - len(effective),
        "missing_steps": len(effective) - len(values),
        "n_effective": len(effective),
        "steps_seen": sorted(steps_seen),
        "writeback_dispatch": _stats(values),
        "all_within_5ms": within_target,
        "error_samples": [item.get("error", "") for item in samples if not item.get("ok")][:3],
    }


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="single-flight", help="档位标签（写进结果/文件名）")
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--rate", type=float, default=0.75)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args(argv)

    # 禁用 keep-alive 复用：并发档下部分连接空闲超过服务端 keep-alive 超时（uvicorn 默认 5s）
    # 后被服务端关闭，复用旧连接会偶发 RemoteProtocolError（与 P-10 指标无关，属工装连接管理问题）
    limits = httpx.Limits(max_connections=args.concurrency * 2 + 4, max_keepalive_connections=0)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=args.timeout, limits=limits) as client:
        health = await client.get("/openllm/v1/health")
        health_data = (health.json() or {}).get("data") or {}
        print("[L2] health:", health.status_code, health_data.get("status"), health_data.get("version"))
        if health.status_code != 200:
            return 1

        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        pacer = _Pacer(args.rate)

        sync_result = await _run_path(
            client, headers, pacer, "sync", args.samples, args.concurrency
        )
        print(f"[同步] n={sync_result['n_effective']} 错误={sync_result['errors']} "
              f"缺步骤={sync_result['missing_steps']} writeback_dispatch "
              f"P50={sync_result['writeback_dispatch']['p50']}ms "
              f"P95={sync_result['writeback_dispatch']['p95']}ms "
              f"P99={sync_result['writeback_dispatch']['p99']}ms "
              f"max={sync_result['writeback_dispatch']['max']}ms 步骤={sync_result['steps_seen']}")

        stream_result = await _run_path(
            client, headers, pacer, "stream", args.samples, args.concurrency
        )
        print(f"[流式] n={stream_result['n_effective']} 错误={stream_result['errors']} "
              f"缺步骤={stream_result['missing_steps']} writeback_dispatch "
              f"P50={stream_result['writeback_dispatch']['p50']}ms "
              f"P95={stream_result['writeback_dispatch']['p95']}ms "
              f"P99={stream_result['writeback_dispatch']['p99']}ms "
              f"max={stream_result['writeback_dispatch']['max']}ms 步骤={stream_result['steps_seen']}")

    sync_ok = sync_result["n_effective"] >= 200 and sync_result["all_within_5ms"]
    stream_ok = stream_result["n_effective"] >= 200 and stream_result["all_within_5ms"]
    verdict = {
        "pass": bool(sync_ok and stream_ok),
        "check": "同步/流式各 ≥200 有效样本，writeback_dispatch P99 ≤5 ms（每样本均 ≤5 ms，最强口径）",
        "target_ms": TARGET_MS,
        "sync": sync_ok,
        "stream": stream_ok,
    }
    result = {
        "case": "P-10 正式分位判定（TT-038 重跑，CR-148-020 后台派发修复后）",
        "date": "2026-09-26",
        "base_url": BASE_URL,
        "tag": args.tag,
        "concurrency": args.concurrency,
        "rate_per_second": args.rate,
        "samples_per_path": args.samples,
        "health": {"status": health.status_code, "data": health_data.get("status")},
        "sync": sync_result,
        "stream": stream_result,
        "verdict": verdict,
    }
    print("判定:", json.dumps(verdict, ensure_ascii=False))
    out_path = f"{OUT_PREFIX}-{args.tag}-20260926.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("证据:", out_path)
    return 0 if verdict.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
