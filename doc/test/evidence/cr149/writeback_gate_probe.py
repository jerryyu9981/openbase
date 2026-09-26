"""CR-149 第二批运行态探针：写侧价值闸门 + rag 分级入库（方案 §4.3，判据 T5）

在**真实网关回写回调**（`_build_writeback_callback` + 真实 `evaluate` 决策器）下验证：

  1. **开关关闭**（默认）：三路回调无条件入队，`rag` 载荷不被改写（与既有实现一致）；
  2. **开关开启 + 低价值轮次**（空 / 过短响应）：三路均返回 `"skipped"` 且**零入队**；
  3. **开关开启 + 高价值轮次**（明确记忆意图 / 响应足够长）：三路入队，`rag` **全文**入库；
  4. **开关开启 + 普通轮次**：`memory`/`profile` 入队，`rag` **跳过**（遏制知识库自产膨胀）。

回写队列以**替身**注入（不触碰真实 SQLite），其余走真实实现。

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import app.services.writeback_queue as queue_module  # noqa: E402
from app.api.openllm_gateway import _build_writeback_callback  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.evaluate import grade_writeback_targets  # noqa: E402


class _IdentityStub:
    """最小身份替身（回写参数派生所需标量）"""

    user_id = "u-probe"
    organization_id = "org-probe"
    role = "org_member"


class _QueueStub:
    """回写队列替身：只记录 submit，不落库"""

    def __init__(self) -> None:
        self.submitted: list[dict] = []

    def register_handler(self, *_args, **_kwargs) -> None:
        return None

    async def next_seq(self, _session_id: str) -> int:
        return 1

    async def submit(self, request_id, session_id, seq, target, payload) -> bool:
        self.submitted.append({"target": target, "response": payload.get("response")})
        return True


ROUNDS = {
    "low_value": {"query": "你好", "response": ""},
    "high_value": {"query": "请记住：我偏好简洁的回答", "response": "好的，已记住。"},
    "ordinary": {"query": "今天天气如何", "response": "今天晴，气温 25 度。"},
    "long_response": {"query": "介绍一下你", "response": "好的，" + "详细说明结论，" * 20},
}


async def _probe_rounds(switch_on: bool) -> dict:
    settings.WRITEBACK_DECISION_ENABLED = switch_on
    results: dict[str, dict] = {}
    for name, turn in ROUNDS.items():
        queue = _QueueStub()
        queue_module.get_writeback_queue = lambda q=queue: q
        memory_cb, rag_cb, profile_cb, _kwargs = _build_writeback_callback(
            _IdentityStub(), f"req-{name}", session_id="sess-probe", rag_kb_id="kb-probe"
        )
        returns = {}
        for road, callback in (("memory", memory_cb), ("rag", rag_cb), ("profile", profile_cb)):
            returns[road] = await callback(query=turn["query"], response=turn["response"])
        results[name] = {
            "returns": returns,
            "submitted": [item["target"] for item in queue.submitted],
            "rag_response_unchanged": all(
                item["response"] == turn["response"]
                for item in queue.submitted
                if item["target"] == "rag"
            ),
        }
    return results


def main() -> int:
    default_switch = settings.WRITEBACK_DECISION_ENABLED
    off = asyncio.run(_probe_rounds(False))
    on = asyncio.run(_probe_rounds(True))
    settings.WRITEBACK_DECISION_ENABLED = default_switch

    print(json.dumps({
        "switch_key": "WRITEBACK_DECISION_ENABLED",
        "switch_default": default_switch,
        "rag_full_min_chars": settings.WRITEBACK_RAG_FULL_MIN_CHARS,
        "switch_off": off,
        "switch_on": on,
        "decisions": {
            name: grade_writeback_targets(turn) for name, turn in ROUNDS.items()
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
