"""三权分立（SoD）与 ABAC 属性判定（E3-1，政务暂缓项的可软件部分）.

设计约束（不改变既有 RBAC 判定路径）：

- 本模块只提供两项**可复用能力**：职责互斥校验（系统管理员 / 安全管理员 /
  审计管理员两两不得兼任）与属性判定（租户 + 角色 + 权限点的 allow/deny）。
- 既有 ``require_permission`` / ``ensure_user_permission`` 行为不变；SoD 由角色
  授予入口调用，ABAC 由试算端点与后续策略接入点调用。
- ABAC 语义：``deny`` 覆盖 ``allow``；跨租户默认拒绝，仅当策略显式声明
  ``cross_tenant`` 时放行；无策略命中返回 ``not_applicable``（由 RBAC 继续判定）。
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from openbase.core.errors import BaseError, ErrorCode

logger = logging.getLogger("openbase.auth.access_control")

# 三权分立角色码（与 JWT ``role`` / 权限矩阵角色码一致，均为 snake_case）
DUTY_SYSTEM_ADMIN = "system_admin"
DUTY_SECURITY_ADMIN = "security_admin"
DUTY_AUDIT_ADMIN = "audit_admin"

# 各职责的权限点基线：系统管理员管配置与账号，安全管理员管密钥与授权，
# 审计管理员管审计读取/导出/链校验。三者不重叠（权限点层面即互斥）。
DUTY_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    DUTY_SYSTEM_ADMIN: ("system:config", "user:list", "tenant:list"),
    DUTY_SECURITY_ADMIN: ("key:issue", "key:revoke", "role:grant"),
    DUTY_AUDIT_ADMIN: ("audit:read", "audit:export", "audit:chain"),
}

# 三权分立访问端点所需权限点（超管 ``system:superadmin`` 亦可通行）
ACCESS_ADMIN_PERMISSION = "security:admin"

__all__ = [
    "ACCESS_ADMIN_PERMISSION",
    "DUTY_AUDIT_ADMIN",
    "DUTY_ROLE_PERMISSIONS",
    "DUTY_SECURITY_ADMIN",
    "DUTY_SYSTEM_ADMIN",
    "AbacEffect",
    "AbacEvaluation",
    "AbacRule",
    "SeparationOfDutiesError",
    "assert_separation_of_duties",
    "conflicting_duty_pairs",
    "ensure_role_grant_allowed",
    "evaluate_abac",
    "parse_abac_rules",
]


class SeparationOfDutiesError(ValueError):
    """三权分立违规：同一主体被同时授予互斥职责."""


# G-03 规模/耗时基线默认值（settings 不可用时的确定性回退；生产由配置覆盖）
DEFAULT_ABAC_RULE_SOFT_LIMIT = 1000
DEFAULT_ABAC_EVALUATION_WARN_MS = 50


def conflicting_duty_pairs(role_codes: Iterable[str]) -> list[tuple[str, str]]:
    """列出互斥职责冲突对（按 ``DUTY_ROLE_PERMISSIONS`` 的声明顺序，去重保序）.

    Args:
        role_codes: 待授予或已持有的角色码集合（可含非职责角色，自动忽略）。

    Returns:
        冲突对列表；空列表表示满足三权分立。
    """
    present = {code for code in role_codes if code in DUTY_ROLE_PERMISSIONS}
    ordered = [code for code in DUTY_ROLE_PERMISSIONS if code in present]
    return [
        (ordered[left], ordered[right])
        for left in range(len(ordered))
        for right in range(left + 1, len(ordered))
    ]


def assert_separation_of_duties(role_codes: Iterable[str]) -> None:
    """校验职责互斥：任一冲突即拒绝（fail-closed）.

    Args:
        role_codes: 拟落入同一主体的角色码集合。

    Raises:
        SeparationOfDutiesError: 存在互斥职责冲突。
    """
    conflicts = conflicting_duty_pairs(role_codes)
    if conflicts:
        raise SeparationOfDutiesError(
            "三权分立违规：同一主体不得兼任互斥职责 "
            + "、".join(f"{left}↔{right}" for left, right in conflicts)
        )


def ensure_role_grant_allowed(
    existing_role_codes: Iterable[str],
    granted_role_codes: Iterable[str],
    *,
    replace: bool = False,
) -> None:
    """角色授予路径的三权分立强制入口（G-02）.

    以「授予后的结果角色集」判定：``replace=True`` 表示授予会替换既有绑定
    （结果集 = 新授予集，可据此整改历史冲突）；``replace=False`` 表示增量授予
    （结果集 = 既有 ∪ 新授予）。冲突统一抛 ``PERM_DUTY_CONFLICT``（HTTP 409）。

    Args:
        existing_role_codes: 主体当前持有的角色码。
        granted_role_codes: 本次拟授予的角色码。
        replace: 是否为替换语义。

    Raises:
        BaseError: ``PERM_DUTY_CONFLICT``（存在互斥职责冲突）。
    """
    granted = tuple(granted_role_codes)
    resulting = granted if replace else tuple(existing_role_codes) + granted
    conflicts = conflicting_duty_pairs(resulting)
    if not conflicts:
        return
    raise BaseError(
        ErrorCode.PERM_DUTY_CONFLICT,
        "三权分立违规：同一主体不得兼任互斥职责 "
        + "、".join(f"{left}↔{right}" for left, right in conflicts),
        detail={"conflicts": [list(pair) for pair in conflicts]},
    )


class AbacEffect(str, Enum):
    """ABAC 判定结果."""

    ALLOW = "allow"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class AbacRule:
    """单条 ABAC 策略规则.

    Attributes:
        effect: ``allow`` / ``deny``。
        permission: 权限点（``*`` 表示任意）。
        roles: 命中所需角色（为空表示不限角色）。
        tenant: 命中所需主体租户（为空表示不限租户）。
        cross_tenant: 是否允许跨租户命中（跨租户默认拒绝）。
    """

    effect: str
    permission: str = "*"
    roles: tuple[str, ...] = ()
    tenant: str | None = None
    cross_tenant: bool = False


@dataclass(frozen=True)
class AbacEvaluation:
    """ABAC 判定输出（含可解释原因，便于审计与试算）. """

    effect: AbacEffect
    reason: str

    @property
    def decision(self) -> str:
        """判定结果的字符串形态（``allow`` / ``deny`` / ``not_applicable``）."""
        return self.effect.value


def _rule_from_object(raw: Any, index: int) -> AbacRule:
    """把 JSON 对象转换为 :class:`AbacRule`（非法项抛 ValueError，带条目号）."""
    if not isinstance(raw, dict):
        raise ValueError(f"ABAC 策略第 {index} 项必须为对象")
    effect = str(raw.get("effect") or "").strip().lower()
    if effect not in ("allow", "deny"):
        raise ValueError(f"ABAC 策略第 {index} 项 effect 必须为 allow/deny")
    permission = str(raw.get("permission") or "*").strip() or "*"
    roles_raw = raw.get("roles") or []
    if not isinstance(roles_raw, list):
        raise ValueError(f"ABAC 策略第 {index} 项 roles 必须为数组")
    roles = tuple(str(role).strip() for role in roles_raw if str(role).strip())
    tenant_raw = raw.get("tenant")
    tenant = str(tenant_raw).strip() if tenant_raw is not None else None
    return AbacRule(
        effect=effect,
        permission=permission,
        roles=roles,
        tenant=tenant or None,
        cross_tenant=bool(raw.get("cross_tenant", False)),
    )


def parse_abac_rules(raw: str) -> tuple[AbacRule, ...]:
    """解析 ABAC 策略 JSON 数组（启动门禁与运行期共用）.

    Args:
        raw: ``OPENBASE_ABAC_POLICIES`` 原始文本；空串表示无策略。

    Returns:
        规则元组（保持声明顺序）。

    Raises:
        ValueError: JSON 非法、顶层非数组或任一规则字段不合法。
    """
    text = (raw or "").strip()
    if not text:
        return ()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OPENBASE_ABAC_POLICIES 不是合法 JSON：{exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("OPENBASE_ABAC_POLICIES 顶层必须为 JSON 数组")
    return tuple(_rule_from_object(item, index) for index, item in enumerate(parsed, start=1))


def _permission_matches(rule: AbacRule, permission: str) -> bool:
    """权限点匹配：``*`` 或精确匹配."""
    return rule.permission == "*" or rule.permission == permission


def _abac_baseline_thresholds() -> tuple[int, int]:
    """取 G-03 基线阈值（settings 不可用时回退模块默认）."""
    try:
        from openbase.settings import get_settings

        settings = get_settings()
        return int(settings.abac_rule_soft_limit), int(settings.abac_evaluation_warn_ms)
    except Exception:  # noqa: BLE001 - 阈值读取失败不阻断判定
        return DEFAULT_ABAC_RULE_SOFT_LIMIT, DEFAULT_ABAC_EVALUATION_WARN_MS


def evaluate_abac(
    rules: Iterable[AbacRule],
    *,
    permission: str,
    subject_tenant: str,
    resource_tenant: str,
    roles: Iterable[str] = (),
    soft_limit: int | None = None,
    warn_ms: int | None = None,
) -> AbacEvaluation:
    """按属性判定访问（deny-overrides + 跨租户默认拒绝）.

    G-03：判定完成后按配置阈值输出结构化 WARN——规则数达软上限提示「需索引/缓存」，
    判定耗时达阈值提示性能退化；告警不改变判定结果。

    Args:
        rules: 策略规则集合。
        permission: 被判定权限点。
        subject_tenant: 主体租户码（空串表示无租户绑定）。
        resource_tenant: 资源租户码（空串表示平台级资源）。
        roles: 主体角色码集合。
        soft_limit: 规则数软上限（None = 读配置，配置不可用回退 1000）。
        warn_ms: 耗时告警阈值毫秒（None = 读配置，配置不可用回退 50）。

    Returns:
        :class:`AbacEvaluation`；``not_applicable`` 表示无策略命中，交由 RBAC 判定。
    """
    started_at = time.perf_counter()
    rule_set = tuple(rules)
    role_set = {role for role in roles if role}
    cross_tenant = bool(subject_tenant) and bool(resource_tenant) and subject_tenant != resource_tenant

    deny_matched = False
    allow_matched = False
    for rule in rule_set:
        if not _permission_matches(rule, permission):
            continue
        if rule.tenant and rule.tenant != subject_tenant:
            continue
        if rule.roles and not role_set.intersection(rule.roles):
            continue
        if cross_tenant and not rule.cross_tenant:
            continue
        if rule.effect == "deny":
            deny_matched = True
        else:
            allow_matched = True

    if deny_matched:
        evaluation = AbacEvaluation(AbacEffect.DENY, "deny_rule_matched")
    elif cross_tenant and not allow_matched:
        evaluation = AbacEvaluation(AbacEffect.DENY, "cross_tenant_without_allow")
    elif allow_matched:
        evaluation = AbacEvaluation(AbacEffect.ALLOW, "allow_rule_matched")
    else:
        evaluation = AbacEvaluation(AbacEffect.NOT_APPLICABLE, "no_policy_matched")

    configured_soft_limit, configured_warn_ms = _abac_baseline_thresholds()
    resolved_soft_limit = configured_soft_limit if soft_limit is None else int(soft_limit)
    resolved_warn_ms = configured_warn_ms if warn_ms is None else int(warn_ms)
    rule_count = len(rule_set)
    if resolved_soft_limit > 0 and rule_count >= resolved_soft_limit:
        logger.warning(
            "abac rule set exceeds soft limit; consider index/cache",
            extra={"rule_count": rule_count, "soft_limit": resolved_soft_limit},
        )
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
    if resolved_warn_ms >= 0 and elapsed_ms >= resolved_warn_ms:
        logger.warning(
            "abac evaluation slow; consider index/cache",
            extra={
                "elapsed_ms": elapsed_ms,
                "rule_count": rule_count,
                "warn_ms": resolved_warn_ms,
            },
        )
    return evaluation
