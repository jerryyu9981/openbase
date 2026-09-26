"""P-4 计量判定：SSE 首包**本仓额外开销**（单飞档，逐样本可观测）

用途：为 `P-4`（`POST /openllm/v1/chat/stream` 的**首包（routing 首事件）本仓额外开销**
**P95 ≤ 100 ms**）出判定值。此前为**口径缺口**（性能测试记录 §6 #2：无法逐样本分离）。

接线（本次改动）：认证依赖处打点 → 流式端点在 `yield … event: routing` 之前把
`{"step": "sse_first_packet", "ms": …}` 落入 `timeline`（即「请求进入 → 首包产出」的服务器侧耗时；
首包之前只有本仓工作，首个外部调用在首包之后）。

判定口径：取 `trace.timeline` 的 `sse_first_packet` 步骤；P95 ≤ 100 ms 为达标
（依据《非功能设计说明-v1.4.8》v1.2.0 §1.1 `P-4`；分位数用最近秩，与 `run_perf_batch.py` 同口径）。

测量要点：
* 语义缓存规避：每样本 query 注入唯一 nonce（命中样本剔除）；
* 流式 `max_tokens=200`（避免 `max_tokens=32` 偶发无 chunk）；
* 禁用 HTTP keep-alive（规避服务端超时关连接导致的 `RemoteProtocolError`，`CR-148-020` 轮已实测）；
* 回读 trace 404 时短暂重试（落库竞态）；仍失败记 `missing`，不计入分位；
* `sse_first_packet` 缺失的样本单独计数（用于验证接线是否逐样本生效）。

用法::

    python p4-first-packet-20260926.py --tag single-flight --count 200 --rate 0.75
    python p4-first-packet-20260926.py --tag conc8 --count 200 --rate 0 --concurrency 8 --defer-readback

退出码：0＝批次完成（达标与否见输出与 JSON `verdict`）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "password": "Perf#148aB"}
CHAT_PROMPT = "请用一句话说明什么是向量数据库"
TARGET_P95_MS = 100.0
STEP_NAME = "sse_first_packet"
TRACE_RETRIES = 3
TRACE_RETRY_INTERVAL = 0.5
OUT_DIR = r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148"


class _Pacer:
    """全局节流器：整体发送速率 ≤ rate（req/s）"""

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


def _stats(values: list[float]) -> dict[str, Any]:
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


async def _stream_sample(
    client: httpx.AsyncClient,
    headers: dict,
    pacer: _Pacer,
    index: int,
    defer_readback: bool = False,
) -> dict[str, Any]:
    """流式单样本：收集 request_id → 回读 trace 提取 sse_first_packet

    ``defer_readback=True`` 时**不在流式阶段回读**（回读负载会与测量窗口交叠，
    污染并发档下「本仓」首包计量），仅返回 request_id，由调用方在流式阶段后统一回读。
    """
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"采样 {nonce}：{CHAT_PROMPT}"}],
        "max_tokens": 200,
        "session_id": f"p4-stream-{index % 8}",
        "mode": "auto",
    }
    await pacer.wait()
    request_id = ""
    cache_hit = False
    events: list[str] = []
    try:
        async with client.stream(
            "POST", "/openllm/v1/chat/stream", json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                await response.aread()
                return {"ok": False, "status": response.status_code, "error": f"status={response.status_code}"}
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
                        if parsed.get("request_id"):
                            request_id = str(parsed["request_id"])
                        if "cache_hit" in json.dumps(parsed):
                            cache_hit = cache_hit or bool(parsed.get("cache_hit"))
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    steps = None
    if not defer_readback:
        steps = await _trace_steps(client, headers, request_id, pacer) if request_id else None
        if steps is None:
            return {"ok": False, "error": "trace 未取到", "request_id": request_id, "events": events}
    return {
        "ok": True,
        "status": 200,
        "request_id": request_id,
        "events": events,
        "cache_hit": cache_hit,
        "steps": steps,
        "first_packet_ms": None if steps is None else steps.get(STEP_NAME),
    }


async def _run_path(
    client: httpx.AsyncClient,
    headers: dict,
    pacer: _Pacer,
    count: int,
    concurrency: int,
    defer_readback: bool = False,
) -> dict[str, Any]:
    """并发执行 count 个流式样本（Semaphore 限并发；concurrency=1 即单飞串行）。

    流式阶段结束后（defer_readback）统一回读 trace，避免回读的 DB 负载
    与测量窗口交叠污染并发档下的首包计量。
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _runner(index: int) -> dict[str, Any]:
        async with semaphore:
            return await _stream_sample(client, headers, pacer, index, defer_readback)

    samples = list(await asyncio.gather(*(_runner(index) for index in range(count))))

    if defer_readback:
        for sample in samples:
            if not sample.get("ok") or not sample.get("request_id"):
                continue
            steps = await _trace_steps(client, headers, sample["request_id"], pacer)
            sample["steps"] = steps
            sample["first_packet_ms"] = None if steps is None else steps.get(STEP_NAME)
            if steps is None:
                sample["ok"] = False
                sample["error"] = "trace 未取到"

    values: list[float] = []
    errors: list[str] = []
    missing_step = 0
    cache_hits = 0
    ok = 0
    for result in samples:
        if not result.get("ok"):
            errors.append(str(result.get("error")))
            continue
        if result.get("cache_hit"):
            cache_hits += 1
            continue
        ok += 1
        value = result.get("first_packet_ms")
        if value is None:
            missing_step += 1
            continue
        values.append(float(value))
    stats = _stats(values)
    return {
        "samples": count,
        "ok": ok,
        "errors": len(errors),
        "error_samples": errors[:5],
        "cache_hits": cache_hits,
        "missing_steps": missing_step,
        "n_effective": len(values),
        "sse_first_packet": stats,
        "all_within_target": all(v <= TARGET_P95_MS for v in values) if values else False,
    }


async def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="single-flight")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--rate", type=float, default=0.75)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument(
        "--defer-readback",
        action="store_true",
        help="流式阶段结束后统一回读 trace（隔离回读负载，并发档正式判定使用）",
    )
    args = parser.parse_args()

    limits = httpx.Limits(max_connections=args.concurrency * 2 + 4, max_keepalive_connections=0)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0, limits=limits) as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        health = await client.get("/openllm/v1/health", headers=headers)
        pacer = _Pacer(args.rate)
        started = time.perf_counter()
        result = await _run_path(
            client, headers, pacer, args.count, args.concurrency, args.defer_readback
        )
        elapsed = time.perf_counter() - started

    stats = result["sse_first_packet"]
    # 正式分位口径：≥200 有效样本且 P95 ≤ 100ms（与 P-10 判定口径对齐）
    verdict_pass = bool(result["n_effective"] >= 200 and stats["p95"] <= TARGET_P95_MS)
    report = {
        "case": "P-4 计量判定（SSE 首包本仓额外开销，P95 ≤100ms）",
        "date": "2026-09-26",
        "base_url": BASE_URL,
        "tag": args.tag,
        "rate_per_second": args.rate,
        "concurrency": args.concurrency,
        "defer_readback": args.defer_readback,
        "peak_in_flight": min(args.count, args.concurrency),
        "achieved_rps": round(result["n_effective"] / elapsed, 2) if elapsed > 0 else 0.0,
        "step_name": STEP_NAME,
        "health": {"status": health.status_code},
        "elapsed_s": round(elapsed, 1),
        **result,
        "verdict": {
            "pass": verdict_pass,
            "check": f"n_effective≥200 且 sse_first_packet P95 ≤ {TARGET_P95_MS} ms",
            "target_p95_ms": TARGET_P95_MS,
        },
    }
    out_path = f"{OUT_DIR}\\p4-first-packet-{args.tag}-20260926.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(f"tag={args.tag} concurrency={args.concurrency} n_effective={result['n_effective']} "
          f"errors={result['errors']} missing_steps={result['missing_steps']} "
          f"cache_hits={result['cache_hits']} elapsed={round(elapsed, 1)}s")
    print(f"sse_first_packet: {stats}")
    print(f"verdict: pass={verdict_pass} (P95 ≤ {TARGET_P95_MS} ms)")
    print(f"evidence: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
