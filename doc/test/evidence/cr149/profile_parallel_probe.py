"""CR-149 第一批第 6 项运行态探针：两条路径取数顺序统一与画像并行

在**真实执行器（`PipelineExecutor` + `run_components`）**下验证（非 monkeypatch）：

  1. **并发收益**：画像取数与组件执行**重叠** —— 同参数下并发墙钟 ≈ max(两段)，
     而改动前的串行写法墙钟 ≈ 两段之和；
  2. **组装前收割**：画像内容确实进入 Prompt（否则等于未注入），且 `timeline` 落
     `profile_fetch` 步骤（耗时 = 启动 → 完成差值）；
  3. **两路径接线时序**：同步「先启动句柄 → 后交编排层」、流式「首包之后启动 →
     组装之前收割」（源码位置证据，含 P-4 约束）。

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import inspect
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.api import openllm_gateway as gateway  # noqa: E402
from app.edgerouter.orchestration.deferred_fetch import DeferredFetch  # noqa: E402
from app.edgerouter.orchestration.executor import PipelineExecutor  # noqa: E402

PROFILE_TEXT = "用户画像：张三，偏好简洁、关注会话编排"
WORK_SECONDS = 0.15


async def _slow_profile() -> str:
    """画像取数替身（模拟 DPS 外部调用耗时）"""
    await asyncio.sleep(WORK_SECONDS)
    return PROFILE_TEXT


async def _slow_memory(_name: str, _params: dict) -> dict:
    """memory 组件替身（模拟外部检索耗时）"""
    await asyncio.sleep(WORK_SECONDS)
    return {"text": "记忆条目一：上一轮讨论了回写闭环"}


async def _llm(_name: str, params: dict) -> dict:
    return {"content": "ok", "prompt_has_profile": PROFILE_TEXT in params["prompt"], "usage": {}}


async def _run(profile_ctx, timeline: list[dict]) -> tuple[float, dict]:
    executor = PipelineExecutor()
    started = time.monotonic()
    result = await executor.execute(
        [
            {"name": "memory", "params": {"top_k": 3}},
            {"name": "llm", "params": {"model": "auto"}},
        ],
        {"memory": _slow_memory, "llm": _llm},
        query="请结合我的画像说明会话编排的前置与回写闭环",
        profile_ctx=profile_ctx,
        timeline=timeline,
    )
    return time.monotonic() - started, result.llm_response or {}


async def _round(concurrent: bool) -> tuple[float, list[dict], dict]:
    """单轮取数：concurrent=False 为改动前写法（先 await 画像，再交执行器）"""
    timeline: list[dict] = []
    started = time.monotonic()
    if concurrent:
        profile_ctx = DeferredFetch(
            "profile_fetch",
            timeline=timeline,
            awaitable=_slow_profile(),
        )
    else:
        profile_ctx = await _slow_profile()
    wall, llm_response = await _run(profile_ctx, timeline)
    return time.monotonic() - started, timeline, llm_response


async def _measure(repeats: int = 3) -> dict:
    # 预热：消除惰性导入 / 真实 tokenizer / 组装器首次构建的一次性开销
    # （否则首轮被高估，串行与并发的差值不可比）
    await _round(concurrent=False)

    serial_rounds = [await _round(concurrent=False) for _ in range(repeats)]
    concurrent_rounds = [await _round(concurrent=True) for _ in range(repeats)]

    serial_wall = min(item[0] for item in serial_rounds)
    concurrent_wall = min(item[0] for item in concurrent_rounds)
    _, concurrent_timeline, llm_response = concurrent_rounds[-1]

    return {
        "work_seconds_per_stage": WORK_SECONDS,
        "repeats": repeats,
        "serial_wall_seconds_all": [round(item[0], 3) for item in serial_rounds],
        "concurrent_wall_seconds_all": [round(item[0], 3) for item in concurrent_rounds],
        "serial_wall_seconds_best": round(serial_wall, 3),
        "concurrent_wall_seconds_best": round(concurrent_wall, 3),
        "overlap_saving_seconds": round(serial_wall - concurrent_wall, 3),
        "concurrent_prompt_has_profile": llm_response.get("prompt_has_profile"),
        "concurrent_timeline": concurrent_timeline,
        "serial_timeline": serial_rounds[-1][1],
    }


def _gateway_order() -> dict:
    """两路径接线时序（源码位置证据）"""
    source = inspect.getsource(gateway)
    routing_yield_at = source.index('f"event: routing')
    stream_start_at = source.index("DeferredFetch(", routing_yield_at)
    stream_resolve_at = source.index("await profile_slot.resolve()", stream_start_at)
    stream_assemble_at = source.index("prompt, composition = build_prompt(", stream_resolve_at)
    sync_start_at = source.index("DeferredFetch(")
    sync_pipeline_at = source.index("await _run_orchestrated_chat(", sync_start_at)
    return {
        "sync_handle_before_pipeline": sync_start_at < sync_pipeline_at,
        "sync_passes_handle_to_pipeline": "profile_ctx=profile_slot," in source,
        "stream_handle_after_first_packet": routing_yield_at < stream_start_at,
        "stream_resolve_before_assembly": stream_resolve_at < stream_assemble_at,
        "handle_call_sites": source.count("DeferredFetch("),
    }


def main() -> int:
    report = asyncio.run(_measure())
    report["gateway_order"] = _gateway_order()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
