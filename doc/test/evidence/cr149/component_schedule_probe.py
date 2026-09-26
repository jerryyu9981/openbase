"""CR-149 第二批运行态探针：组件依赖图调度（方案 §3.1 / §4.2「顺序优化」）

在**真实共用组件执行步骤**（`component_pipeline.run_components`）与**真实调度器**
（`component_graph.dependency_levels`）下验证：

  1. **依赖图形**：无依赖 ⇒ 单波次；`memory:rag` ⇒ 两波次（先 rag 后 memory）；
     成环 ⇒ fail-safe 退化为单波次保序（不抛异常）；
  2. **开关关闭**：`enable_parallel=false` 串行、`=true` 并行（与既有实现一致）；
  3. **开关开启「无依赖即并行」**：即使 `enable_parallel=false`，memory/rag 也并发
     （耗时 ≈ max 而非 sum）；
  4. **严格顺序用依赖声明表达**：声明 `memory:rag` 后两组件不重叠且 rag 先完成。

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.component_graph import (  # noqa: E402
    dependency_levels,
    parse_dependencies,
)
from app.edgerouter.orchestration.component_pipeline import (  # noqa: E402
    resolve_schedule_plan,
    run_components,
)

WORK_SECONDS = 0.12
PIPELINE = [{"name": "memory", "params": {}}, {"name": "rag", "params": {}}]


class _Assembler:
    def format_context(self, name: str, data: dict) -> str:
        return str((data or {}).get("text") or "")


async def _run_case(*, switch: bool, enable_parallel: bool, declaration: str) -> dict:
    settings.COMPONENT_DEPENDENCY_SCHEDULING_ENABLED = switch
    settings.OPENLLM_COMPONENT_DEPENDENCIES = declaration
    events: list[str] = []

    async def _handler(name: str, _params: dict) -> dict:
        events.append(f"{name}_start")
        await asyncio.sleep(WORK_SECONDS)
        events.append(f"{name}_end")
        return {"text": name}

    started = time.monotonic()
    result = await run_components(
        pipeline=PIPELINE,
        query="q",
        handlers={"memory": _handler, "rag": _handler},
        assembler=_Assembler(),
        enable_parallel=enable_parallel,
    )
    elapsed = time.monotonic() - started
    waves, concurrent = resolve_schedule_plan(
        ["memory", "rag"], enable_parallel=enable_parallel
    )
    return {
        "switch": switch,
        "enable_parallel": enable_parallel,
        "declaration": declaration,
        "waves": waves,
        "wave_concurrent": concurrent,
        "executed": sorted(result.executed),
        "events": events,
        "wall_seconds": round(elapsed, 3),
        "overlapped": events.index("memory_start") < events.index("rag_end")
        and events.index("rag_start") < events.index("memory_end"),
    }


def main() -> int:
    default_switch = settings.COMPONENT_DEPENDENCY_SCHEDULING_ENABLED
    default_declaration = settings.OPENLLM_COMPONENT_DEPENDENCIES

    async def _measure() -> list[dict]:
        return [
            # 预热：消除惰性导入/首次事件循环启动开销
            await _run_case(switch=False, enable_parallel=False, declaration=""),
            await _run_case(switch=False, enable_parallel=False, declaration=""),
            await _run_case(switch=False, enable_parallel=True, declaration=""),
            await _run_case(switch=True, enable_parallel=False, declaration=""),
            await _run_case(switch=True, enable_parallel=True, declaration="memory:rag"),
            await _run_case(switch=True, enable_parallel=False, declaration="memory:rag"),
        ]

    cases = asyncio.run(_measure())

    graph = {
        "no_dependency": dependency_levels(["memory", "rag"]),
        "memory_depends_on_rag": dependency_levels(["memory", "rag"], {"memory": ("rag",)}),
        "cycle_is_failsafe": dependency_levels(
            ["memory", "rag"], {"memory": ("rag",), "rag": ("memory",)}
        ),
        "parse_empty": parse_dependencies(""),
        "parse_pair": parse_dependencies("memory:rag"),
        "parse_multi": parse_dependencies("a:b,a:c"),
    }

    settings.COMPONENT_DEPENDENCY_SCHEDULING_ENABLED = default_switch
    settings.OPENLLM_COMPONENT_DEPENDENCIES = default_declaration

    print(json.dumps({
        "switch_key": "COMPONENT_DEPENDENCY_SCHEDULING_ENABLED",
        "declaration_key": "OPENLLM_COMPONENT_DEPENDENCIES",
        "switch_default": default_switch,
        "declaration_default": default_declaration,
        "work_seconds_per_component": WORK_SECONDS,
        "cases": cases,
        "graph": graph,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
