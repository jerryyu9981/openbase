"""隔离探针：量化 DPS(127.0.0.1:8030) 不可用时的连接代价

不接触被压测实例（8041），只统计到 8030 的连接/请求耗时，用于解释
「画像拉取」步骤实测 ~2.0s 的成因。
"""
import asyncio
import time

import httpx

DPS_BASE_URL = "http://127.0.0.1:8030"
DPS_TIMEOUT = 5.0
ROUNDS = 3


async def _raw_connect() -> None:
    for index in range(ROUNDS):
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=DPS_TIMEOUT) as client:
            try:
                await client.get(f"{DPS_BASE_URL}/profile/v1/get")
            except Exception as exc:  # noqa: BLE001
                elapsed = (time.perf_counter() - started) * 1000
                print(f"[raw#{index + 1}] {type(exc).__name__}: {exc} | {elapsed:.1f} ms")


async def _via_dps_client() -> None:
    import sys

    sys.path.insert(0, r"D:\Trae CN\myproject\Dev\OpenLLM\backend")
    from app.edgerouter.adapters.dps_client import DPSClient

    client = DPSClient(base_url=DPS_BASE_URL, timeout=DPS_TIMEOUT, real_mode=False)
    for index in range(ROUNDS):
        started = time.perf_counter()
        try:
            await client.get_profile(user_id="probe-user")
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - started) * 1000
            print(f"[DPSClient#{index + 1}] {type(exc).__name__}: {exc} | {elapsed:.1f} ms")


async def main() -> None:
    print(f"DPS_BASE_URL={DPS_BASE_URL} timeout={DPS_TIMEOUT}s")
    await _raw_connect()
    await _via_dps_client()


if __name__ == "__main__":
    asyncio.run(main())
