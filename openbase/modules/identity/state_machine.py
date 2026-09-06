"""identity 模块：Principal（user/agent）语义常量 + 生命周期状态机（U1 T1/T2，RA-01/RA-02）.

常量与核心模型（openbase/core/models/base.py）内联值保持一致。
T2（RA-02/OB-2 状态机 + OB-4）在此落地完整状态机：状态枚举、迁移矩阵校验
（validate_transition，非法路径 0，草案 §4.1/§4.2）、登录面判定收口
（active 才可认证 + agent 无人工登录面）。
"""

from __future__ import annotations

from openbase.core.errors import BaseError, ErrorCode

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

# ---- 迁移矩阵（设计草案 §4.1：非法组合一律 400 BIZ_STATE_TRANSITION_INVALID） ----
# provisioned → active → suspended ⇄ active；suspended/active → deactivated → purged
TRANSITION_MATRIX: dict[str, frozenset[str]] = {
    STATUS_STATE_PROVISIONED: frozenset({STATUS_STATE_ACTIVE}),
    STATUS_STATE_ACTIVE: frozenset({STATUS_STATE_SUSPENDED, STATUS_STATE_DEACTIVATED}),
    STATUS_STATE_SUSPENDED: frozenset({STATUS_STATE_ACTIVE, STATUS_STATE_DEACTIVATED}),
    STATUS_STATE_DEACTIVATED: frozenset({STATUS_STATE_PURGED}),
    STATUS_STATE_PURGED: frozenset(),
}


def is_transition_allowed(current: str, target: str) -> bool:
    """迁移矩阵查询（纯函数）：current→target 是否合法（含状态合法性与自环拦截）.

    Args:
        current: 当前 status_state。
        target: 目标 status_state。

    Returns:
        合法返回 True；非法/未知状态/自环返回 False。
    """
    if current not in TRANSITION_MATRIX or target not in VALID_STATUS_STATES:
        return False
    return target in TRANSITION_MATRIX[current]


def validate_transition(current: str, target: str) -> None:
    """校验状态迁移合法性，非法路径统一抛 400 BIZ_STATE_TRANSITION_INVALID（RA-02 验收）.

    Args:
        current: 当前 status_state。
        target: 目标 status_state。

    Raises:
        BaseError: 迁移非法（0 非法路径由本函数拦截，草案 §4.1/§4.2）。
    """
    if not is_transition_allowed(current, target):
        raise BaseError(
            ErrorCode.BIZ_STATE_TRANSITION_INVALID,
            f"illegal state transition: {current} -> {target}",
            detail={"from": current, "to": target},
        )


def assert_loginable(subject_type: str, status_state: str = STATUS_STATE_ACTIVE) -> bool:
    """登录面判定（T2 完整门禁）：仅 user + active 可认证（草案 §4.1「active 才可认证」）.

    agent 一律不可人工登录（0 可达登录路径，RA-01 断言）；user 亦须 active
    （suspended/deactivated/purged/provisioned 均不可登录，签发侧状态门禁）。

    Args:
        subject_type: 主体具象（user/agent）。
        status_state: 生命周期状态。

    Returns:
        user + active → True；其余一律 False。
    """
    return subject_type == SUBJECT_TYPE_USER and status_state == STATUS_STATE_ACTIVE


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
    "TRANSITION_MATRIX",
    "is_transition_allowed",
    "validate_transition",
    "assert_loginable",
    "status_state_from_int",
    "status_int_from_state",
]
