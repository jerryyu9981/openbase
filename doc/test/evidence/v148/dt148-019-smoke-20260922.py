"""L3 冒烟：DT-148-019 画像拉取失败负缓存 / 关闭画像注入开关（真机）

用法::

    python smoke_dt148019.py            # 默认档：验证失败负缓存（短路）
    python smoke_dt148019.py --switch-off   # 开关档：验证 PROFILE_INJECTION_ENABLED=false

判定（L3 冒烟，非性能正式分位）：
* 全部对话 200；
* **负缓存档**：第 1 次 `profile_fetch` ≈ 2.0s（DPS 不可用），第 2/3 次 ≈ 0ms（短路）；
  `P-1 = 墙钟 − llm` 由 ≈2.6s 降至 ≈0.6s；
* **开关档**：全部对话 `profile_fetch` ≈ 0ms。
"""
import asyncio
import json
import sys
import time
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8041"
ACCOUNT = {"username": "v148-perf", "email": "v148-perf@local.dev", "password": "Perf#148aB"}
SWITCH_OFF = "--switch-off" in sys.argv


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


async def _chat(client: httpx.AsyncClient, headers: dict, index: int) -> dict:
    nonce = uuid.uuid4().hex[:12]
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": f"冒烟 {nonce}：请用一句话说明什么是向量数据库"}],
        "max_tokens": 32,
        "session_id": f"smoke-dt148019-{index}",
        "mode": "auto",
    }
    started = time.perf_counter()
    response = await client.post("/openllm/v1/chat", json=payload, headers=headers)
    wall_ms = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        return {"ok": False, "status": response.status_code, "error": response.text[:200], "wall_ms": wall_ms}
    data = (response.json() or {}).get("data") or {}
    request_id = data.get("request_id")
    steps: dict[str, float] = {}
    if request_id:
        detail = await client.get(f"/openllm/v1/trace/{request_id}", headers=headers)
        if detail.status_code == 200:
            timeline = ((detail.json() or {}).get("data") or {}).get("timeline") or []
            steps = {str(item.get("step")): float(item.get("ms") or 0) for item in timeline}
    llm_ms = steps.get("llm")
    return {
        "ok": True,
        "status": 200,
        "wall_ms": round(wall_ms, 1),
        "steps": steps,
        "p1_repo_overhead_ms": round(wall_ms - llm_ms, 1) if llm_ms is not None else None,
        "unaccounted_ms": round(wall_ms - sum(steps.values()), 1),
    }


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        health = await client.get("/openllm/v1/health")
        health_data = (health.json() or {}).get("data") or {}
        print("[L2] health:", health.status_code, health_data.get("status"), health_data.get("version"))

        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        receipts = await client.get("/openllm/v1/writeback/receipts", headers=headers, params={"limit": 5})
        print("[冒烟] 回执查询:", receipts.status_code)

        samples = []
        for index in range(3):
            sample = await _chat(client, headers, index)
            samples.append(sample)
            print(
                f"[对话 #{index + 1}] status={sample.get('status')} 墙钟={sample.get('wall_ms')}ms "
                f"步骤={sample.get('steps')} P-1(墙钟−llm)={sample.get('p1_repo_overhead_ms')}ms "
                f"未计量差额={sample.get('unaccounted_ms')}ms"
            )

    result = {
        "mode": "switch-off" if SWITCH_OFF else "negative-cache",
        "health": {"status": health.status_code, "data": health_data.get("status")},
        "receipts_status": receipts.status_code,
        "samples": samples,
    }
    verdict = _verdict(samples, SWITCH_OFF)
    result["verdict"] = verdict
    print("判定:", json.dumps(verdict, ensure_ascii=False))
    out = (
        r"D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\v148\dt148-019-smoke-"
        + ("switch-off" if SWITCH_OFF else "negative-cache")
        + "-20260922.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("证据:", out)
    return 0 if verdict.get("pass") else 1


def _verdict(samples: list[dict], switch_off: bool) -> dict:
    ok = all(sample.get("ok") for sample in samples)
    profile_ms = [float((sample.get("steps") or {}).get("profile_fetch") or 0) for sample in samples]
    p1 = [sample.get("p1_repo_overhead_ms") for sample in samples]
    if switch_off:
        passed = ok and all(value <= 50 for value in profile_ms)
        return {
            "pass": passed,
            "check": "开关关闭时全部 profile_fetch ≤50ms（完全跳过画像拉取）",
            "profile_fetch_ms": profile_ms,
            "p1_ms": p1,
        }
    passed = (
        ok
        and profile_ms[0] >= 1000
        and all(value <= 50 for value in profile_ms[1:])
        and p1[0] is not None
        and p1[1] is not None
        and float(p1[1]) < float(p1[0]) * 0.5
    )
    return {
        "pass": passed,
        "check": "首次 profile_fetch ≥1000ms（真实失败）；其后 ≤50ms（短路）；P-1 降幅 >50%",
        "profile_fetch_ms": profile_ms,
        "p1_ms": p1,
    }


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
