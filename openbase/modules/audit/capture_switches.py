"""C-19 响应采集开关的审计留痕（``audit_logs``，action=``capture.switch``）.

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》§11.2 红线 5
——「**开关本身留痕**：响应采集的开启/关闭作为审计事件记录（谁、何时、对哪个服务开启）」。

两段式留痕（防漏记 + 不阻断启动）：

1. **结构化日志**（必做，同步）：每次服务启动记录一行 ``capture.switch.state``，
   含三开关状态与「是否任一实际生效」；
2. **审计落库**（best-effort，异步）：仅当**实际生效**（``capture_enabled``）时落
   ``audit_logs`` 一行（生产默认全关 → 零写入）；落库失败仅 WARN + rollback，
   **绝不阻断服务启动**（复用 C-4 的降级语义）。

注：开关取值来自进程环境变量，故「变更」以**服务启动快照**为观测点；同一进程内不热更。
"""

from __future__ import annotations

import logging
import os
from typing import Any

from openbase.settings import Settings, get_settings

__all__ = [
    "CAPTURE_SWITCH_ACTION",
    "CAPTURE_SWITCH_EVENT",
    "capture_switch_state",
    "record_capture_switch_state",
]

logger = logging.getLogger("openbase.audit")

# 审计动作码与日志事件名（同一语义，双通道留痕）
CAPTURE_SWITCH_ACTION = "capture.switch"
CAPTURE_SWITCH_EVENT = "capture.switch.state"

# 落库总开关（与 audit 模块 C-4 同源：0 = 关闭落库，测试环境默认）
ENV_AUDIT_DB_PERSIST = "OPENBASE_AUDIT_DB_PERSIST"


def capture_switch_state(settings: Settings | None = None) -> dict[str, Any]:
    """采集三开关当前状态（供日志与审计落库共用，避免两处取值漂移）.

    Args:
        settings: 配置对象；None 时取全局单例。

    Returns:
        ``{"capture_response": bool, "capture_upstream": bool,
        "capture_field_allowlist": list[str], "capture_enabled": bool, "env": str}``；
        其中 ``*_enabled`` 为**实际生效值**（已套用「生产永久关闭」红线）。
    """
    resolved = settings if settings is not None else get_settings()
    response_enabled = resolved.capture_response_enabled
    upstream_enabled = resolved.capture_upstream_enabled
    return {
        "capture_response": response_enabled,
        "capture_upstream": upstream_enabled,
        "capture_field_allowlist": resolved.capture_field_allowlist_list,
        "capture_enabled": response_enabled or upstream_enabled,
        "env": resolved.env,
    }


async def record_capture_switch_state(settings: Settings | None = None) -> dict[str, Any]:
    """记录开关状态：结构化日志（必做）+ 审计落库（仅生效时，best-effort）.

    Args:
        settings: 配置对象；None 时取全局单例。

    Returns:
        同 :func:`capture_switch_state` 的状态载荷（便于调用方与测试断言）。
    """
    state = capture_switch_state(settings)
    logger.info(CAPTURE_SWITCH_EVENT, extra=dict(state))
    if state["capture_enabled"]:
        await _persist_capture_switch(state)
    return state


async def _persist_capture_switch(state: dict[str, Any]) -> None:
    """best-effort 落 ``audit_logs``（action=capture.switch，detail=开关快照）.

    失败仅 WARN + rollback，不 re-raise（启动不得因审计失败而中断）。
    """
    if os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
        return

    session = None
    try:
        from openbase.core.db.session import get_session_factory
        from openbase.core.models import AuditLog

        async with get_session_factory()() as session:
            session.add(
                AuditLog(
                    user_id=None,
                    tenant_id=None,
                    action=CAPTURE_SWITCH_ACTION,
                    resource="openbase",
                    resource_id=None,
                    ip=None,
                    user_agent=None,
                    request_id=None,
                    detail=dict(state),
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001 - 审计尽力留痕，不阻断启动
        logger.warning("capture switch audit persist failed (degraded)")
        if session is not None:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
