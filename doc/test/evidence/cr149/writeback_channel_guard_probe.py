"""方案 §4.3「写路径与通道一致」—— 运行态证据探针

**审计背景**：`ChannelStateManager.assert_write_channel_is_primary` 虽早已实现，
但此前**仅被单测与脚本引用**（`app/` 内零调用点、状态机从未实例化）
⇒「通道切换期间双写」无防护。本探针验证接线后的三态语义：

  - 默认主通道（`CHANNEL_PREFERENCE=b-primary`）⇒ 三路正常入队（**行为不变**）；
  - 切换期间（`a-primary`，经 B 写属非主通道）⇒ **暂停本轮回写**（`skipped`、不入队）；
  - 开关关闭（`WRITEBACK_CHANNEL_GUARD_ENABLED=false`）⇒ 逐字回退（不看通道状态）；
  - 配置非法（未知 preference）⇒ WARN + **放行**（fail-open，避免笔误静默停库）。

**口径**：走**真实** `_build_writeback_callback`（真实通道断言）＋ 队列替身（不入库）。

用法：``python doc/test/evidence/cr149/writeback_channel_guard_probe.py``（cwd = OpenLLM/backend）
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import contextmanager
from typing import Any

sys.path.insert(0, os.getcwd())

import app.api.openllm_gateway as gateway  # noqa: E402
import app.services.writeback_queue as queue_module  # noqa: E402
from app.core.config import settings  # noqa: E402


class _QueueStub:
    def __init__(self) -> None:
        self.submitted: list[str] = []

    def register_handler(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def next_seq(self, _session_id: str) -> int:
        return 1

    async def submit(self, request_id, session_id, seq, target, payload) -> bool:
        self.submitted.append(target)
        return True


class _IdentityStub:
    user_id = "u-probe"
    organization_id = "org-probe"
    role = "org_member"


@contextmanager
def _temp(**overrides: Any):
    previous = {key: getattr(settings, key, None) for key in overrides}
    for key, value in overrides.items():
        setattr(settings, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            setattr(settings, key, value)


def _run_round(**overrides: Any) -> tuple[list[str], dict[str, Any]]:
    queue = _QueueStub()
    original = queue_module.get_writeback_queue
    queue_module.get_writeback_queue = lambda: queue
    try:
        with _temp(WRITEBACK_DECISION_ENABLED=False, **overrides):
            memory_cb, rag_cb, profile_cb, _kwargs = gateway._build_writeback_callback(
                _IdentityStub(), "req-probe-chan", session_id="sess-probe", rag_kb_id="kb-probe"
            )
            returns: dict[str, Any] = {}
            for road, callback in (
                ("memory", memory_cb),
                ("rag", rag_cb),
                ("profile", profile_cb),
            ):
                returns[road] = asyncio.run(callback(query="请记住：我偏好简洁", response="好的"))
    finally:
        queue_module.get_writeback_queue = original
    return queue.submitted, returns


def main() -> int:
    default_submitted, default_returns = _run_round()
    guarded_submitted, guarded_returns = _run_round(CHANNEL_PREFERENCE="a-primary")
    off_submitted, _off_returns = _run_round(
        WRITEBACK_CHANNEL_GUARD_ENABLED=False, CHANNEL_PREFERENCE="a-primary"
    )
    invalid_submitted, _invalid_returns = _run_round(CHANNEL_PREFERENCE="b_primary_typo")

    report = {
        "probe": "writeback_channel_guard",
        "design_ref": "方案 §4.3 表「写路径与通道一致」＋ §8 风险回退（写路径校验 + 切换期间暂停回写）",
        "default_primary": {
            "submitted": default_submitted,
            "returns": default_returns,
            "unchanged": sorted(default_submitted) == ["memory", "profile", "rag"],
        },
        "channel_switch_a_primary": {
            "submitted": guarded_submitted,
            "returns": guarded_returns,
            "paused": guarded_submitted == []
            and all(value == "skipped" for value in guarded_returns.values()),
        },
        "guard_switch_off": {
            "submitted": off_submitted,
            "verbatim": "memory" in off_submitted,
        },
        "invalid_preference_fail_open": {
            "submitted": invalid_submitted,
            "allowed": "memory" in invalid_submitted,
        },
        "config_defaults": {
            "WRITEBACK_CHANNEL_GUARD_ENABLED": settings.WRITEBACK_CHANNEL_GUARD_ENABLED,
            "CHANNEL_PREFERENCE": getattr(settings, "CHANNEL_PREFERENCE", None),
        },
    }
    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "writeback_channel_guard_probe-result.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n结果已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
