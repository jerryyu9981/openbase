"""ABAC 策略运行期存储与写操作（E3-1 写端点，闭合 ER-24）.

设计约束：

- **判定语义不变**：DB 规则与 ``OPENBASE_ABAC_POLICIES`` 配置基线合并参与判定，
  ``deny`` 覆盖 ``allow``、跨租户默认拒绝、无命中仍返回 ``not_applicable`` 回落 RBAC；
- **默认零行为变化**：表内无规则时判定结果与仅用配置完全一致；``enabled=False``
  的行不参与判定（停用即失效，无需删除）；
- **可追溯**：新增/更新/删除与 ``AuditLog`` 在同一事务提交，审计失败即整体回滚，
  不产生「策略已改但无留痕」的漂移；
- **字段校验同源**：复用 ``parse_abac_rules`` 的解析规则（effect/permission/roles/
  tenant/cross_tenant），避免管理面与启动门禁出现两套口径。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AbacPolicyRule, AuditLog
from openbase.modules.auth.access_control import AbacRule, parse_abac_rules

logger = logging.getLogger("openbase.auth.abac_policy_store")

# 审计动作名（管理面可见的变更留痕）
ACTION_ABAC_POLICY_CREATE = "access.abac_policy.create"
ACTION_ABAC_POLICY_UPDATE = "access.abac_policy.update"
ACTION_ABAC_POLICY_DELETE = "access.abac_policy.delete"
AUDIT_RESOURCE_ABAC_POLICY = "abac_policy"

__all__ = [
    "ACTION_ABAC_POLICY_CREATE",
    "ACTION_ABAC_POLICY_DELETE",
    "ACTION_ABAC_POLICY_UPDATE",
    "create_policy_rule",
    "delete_policy_rule",
    "list_policy_rules",
    "load_effective_rules",
    "update_policy_rule",
    "validate_policy_payload",
]


def validate_policy_payload(payload: Mapping[str, Any]) -> AbacRule:
    """按配置解析口径校验策略字段.

    Args:
        payload: 策略字段映射（至少含 ``effect``）。

    Returns:
        规范化后的 :class:`AbacRule`。

    Raises:
        BaseError: ``PARAM_INVALID``（effect 非 allow/deny、roles 非数组等）。
    """
    try:
        parsed = parse_abac_rules(json.dumps([dict(payload)]))
    except ValueError as exc:
        raise BaseError(ErrorCode.PARAM_INVALID, str(exc)) from exc
    return parsed[0]


def _rule_from_row(row: AbacPolicyRule) -> AbacRule:
    """把持久化行还原为判定用规则."""
    return AbacRule(
        effect=row.effect,
        permission=row.permission or "*",
        roles=tuple(row.roles or ()),
        tenant=row.tenant or None,
        cross_tenant=bool(row.cross_tenant),
    )


def _audit_detail(row: AbacPolicyRule) -> dict[str, Any]:
    """审计明细（策略不含密钥，可整体留痕；不含请求体原文）."""
    return {
        "policy_id": row.id,
        "name": row.name,
        "effect": row.effect,
        "permission": row.permission,
        "roles": list(row.roles or []),
        "tenant": row.tenant,
        "cross_tenant": bool(row.cross_tenant),
        "enabled": bool(row.enabled),
        "version": row.version,
    }


async def list_policy_rules(
    session: AsyncSession, *, include_disabled: bool = False
) -> list[AbacPolicyRule]:
    """列出策略行（默认仅启用的行），按 id 升序."""
    statement = select(AbacPolicyRule).order_by(AbacPolicyRule.id.asc())
    if not include_disabled:
        statement = statement.where(AbacPolicyRule.enabled.is_(True))
    result = await session.execute(statement)
    return list(result.scalars().all())


async def load_effective_rules(
    session: AsyncSession, *, baseline: Iterable[AbacRule] = ()
) -> tuple[AbacRule, ...]:
    """合并判定规则：DB 启用行在前，配置基线在后（判定语义与顺序无关）.

    Args:
        session: 数据库会话。
        baseline: 配置基线规则（``parse_abac_rules(settings.abac_policies)``）。

    Returns:
        参与判定的规则元组。
    """
    rows = await list_policy_rules(session)
    return tuple(_rule_from_row(row) for row in rows) + tuple(baseline)


async def _require_policy(session: AsyncSession, policy_id: int) -> AbacPolicyRule:
    """按主键取策略行（不存在即 404）."""
    row = await session.get(AbacPolicyRule, policy_id)
    if row is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"abac policy not found: {policy_id}")
    return row


async def _ensure_name_available(
    session: AsyncSession, name: str, *, exclude_id: int | None = None
) -> None:
    """策略名唯一性校验（重复即 409，不依赖数据库异常措辞）."""
    statement = select(AbacPolicyRule.id).where(AbacPolicyRule.name == name)
    if exclude_id is not None:
        statement = statement.where(AbacPolicyRule.id != exclude_id)
    existing = await session.execute(statement)
    if existing.first() is not None:
        raise BaseError(
            ErrorCode.BIZ_CONFLICT,
            f"abac policy name already exists: {name}",
            detail={"name": name},
        )


def _append_audit(
    session: AsyncSession,
    *,
    action: str,
    row: AbacPolicyRule,
    actor_id: int | None,
    request_id: str,
) -> None:
    """同事务写入变更审计（失败即随事务回滚）."""
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            resource=AUDIT_RESOURCE_ABAC_POLICY,
            resource_id=str(row.id),
            request_id=request_id,
            detail=_audit_detail(row),
        )
    )


async def create_policy_rule(
    session: AsyncSession,
    *,
    name: str,
    fields: Mapping[str, Any],
    enabled: bool,
    actor_id: int | None,
    request_id: str,
) -> AbacPolicyRule:
    """新增策略（名称唯一 + 字段校验 + 审计留痕）."""
    rule = validate_policy_payload(fields)
    await _ensure_name_available(session, name)
    row = AbacPolicyRule(
        name=name,
        effect=rule.effect,
        permission=rule.permission,
        roles=list(rule.roles) or None,
        tenant=rule.tenant,
        cross_tenant=rule.cross_tenant,
        enabled=bool(enabled),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(row)
    await session.flush()
    _append_audit(
        session,
        action=ACTION_ABAC_POLICY_CREATE,
        row=row,
        actor_id=actor_id,
        request_id=request_id,
    )
    await session.commit()
    await session.refresh(row)
    logger.info("abac policy created", extra={"policy_id": row.id, "name": name})
    return row


async def update_policy_rule(
    session: AsyncSession,
    *,
    policy_id: int,
    name: str,
    fields: Mapping[str, Any],
    enabled: bool,
    actor_id: int | None,
    request_id: str,
) -> AbacPolicyRule:
    """更新策略（版本自增，审计留痕）."""
    rule = validate_policy_payload(fields)
    row = await _require_policy(session, policy_id)
    await _ensure_name_available(session, name, exclude_id=policy_id)
    row.name = name
    row.effect = rule.effect
    row.permission = rule.permission
    row.roles = list(rule.roles) or None
    row.tenant = rule.tenant
    row.cross_tenant = rule.cross_tenant
    row.enabled = bool(enabled)
    row.version = int(row.version or 1) + 1
    row.updated_by = actor_id
    _append_audit(
        session,
        action=ACTION_ABAC_POLICY_UPDATE,
        row=row,
        actor_id=actor_id,
        request_id=request_id,
    )
    await session.commit()
    await session.refresh(row)
    logger.info("abac policy updated", extra={"policy_id": policy_id, "name": name})
    return row


async def delete_policy_rule(
    session: AsyncSession,
    *,
    policy_id: int,
    actor_id: int | None,
    request_id: str,
) -> None:
    """删除策略（审计留痕先于删除生效，同事务）."""
    row = await _require_policy(session, policy_id)
    _append_audit(
        session,
        action=ACTION_ABAC_POLICY_DELETE,
        row=row,
        actor_id=actor_id,
        request_id=request_id,
    )
    await session.delete(row)
    await session.commit()
    logger.info("abac policy deleted", extra={"policy_id": policy_id})
