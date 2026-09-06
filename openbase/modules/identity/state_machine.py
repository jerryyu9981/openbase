"""identity 模块：Principal（user/agent）语义常量与登录面判定（U1 T1，RA-01/OB-1）.

常量与核心模型（openbase/core/models/base.py）内联值保持一致；
生命周期迁移矩阵完整版属 T2（RA-02），此处先沉淀 T1 所需面。
"""

from __future__ import annotations

# ---- Principal 具象 ----
SUBJECT_TYPE_USER = "user"
SUBJECT_TYPE_AGENT = "agent"

# ---- 凭据面（credential_type）----
CREDENTIAL_TYPE_PASSWORD = "password"
CREDENTIAL_TYPE_OIDC = "oidc"
CREDENTIAL_TYPE_API_KEY = "api_key"

# ---- 生命周期状态机状态（status_state）----
STATUS_STATE_PROVISIONED = "provisioned"
STATUS_STATE_ACTIVE = "active"
STATUS_STATE_SUSPENDED = "suspended"
STATUS_STATE_DEACTIVATED = "deactivated"
STATUS_STATE_PURGED = "purged"

# ---- 合法状态集合 ----
VALID_STATUS_STATES = frozenset(
    {
        STATUS_STATE_PROVISIONED,
        STATUS_STATE_ACTIVE,
        STATUS_STATE_SUSPENDED,
        STATUS_STATE_DEACTIVATED,
        STATUS_STATE_PURGED,
    }
)


def assert_loginable(subject_type: str, status_state: str = STATUS_STATE_ACTIVE) -> bool:
    """登录面判定：agent 一律不可人工登录（0 可达登录路径，RA-01 断言）.

    Args:
        subject_type: 主体具象（user/agent）。
        status_state: 生命周期状态（当前状态机完整门禁由 T2 接入，T1 仅做 subject_type 分叉）。

    Returns:
        user → True；agent → False。
    """
    if subject_type == SUBJECT_TYPE_AGENT:
        return False
    return subject_type == SUBJECT_TYPE_USER


def status_state_from_int(status_int: int) -> str:
    """存量二元 status(int 1/0) → 状态机语义映射（迁移回填默认保守）.

    1 → active；0 → suspended（保守语义：存量停用不等同 deactivated）。
    """
    return STATUS_STATE_ACTIVE if status_int == 1 else STATUS_STATE_SUSPENDED


def status_int_from_state(status_state: str) -> int:
    """状态机语义 → 兼容读视图 status(int 1/0)."""
    return 1 if status_state in (STATUS_STATE_PROVISIONED, STATUS_STATE_ACTIVE) else 0


__all__ = [
    "SUBJECT_TYPE_USER",
    "SUBJECT_TYPE_AGENT",
    "CREDENTIAL_TYPE_PASSWORD",
    "CREDENTIAL_TYPE_OIDC",
    "CREDENTIAL_TYPE_API_KEY",
    "STATUS_STATE_PROVISIONED",
    "STATUS_STATE_ACTIVE",
    "STATUS_STATE_SUSPENDED",
    "STATUS_STATE_DEACTIVATED",
    "STATUS_STATE_PURGED",
    "VALID_STATUS_STATES",
    "assert_loginable",
    "status_state_from_int",
    "status_int_from_state",
]
