"""identity 模块：生命周期状态迁移服务（U1 T2，RA-02/OB-2 状态机；设计草案 §4/§5/§8）.

状态迁移（activate/suspend/restore/deactivate）统一经 ``_apply``：
- validate_transition 拦截非法路径（0 非法路径，400 BIZ_STATE_TRANSITION_INVALID）；
- 变更写 status_state/status_reason/status(int 兼容读视图)；
- 吊销类迁移（suspend/restore/deactivate）递增 token_version（方案 a，草案 §5）：
  restore 后旧 token 不复活（tvn 落后由 T3 版本强校验拦截，此处已递增+清缓存）；
- agent 主体 suspend/deactivate → 联动吊销全部 sk-agent-* 密钥（Q2-S5）；
- 审计留痕（action=identity.lifecycle.<to>）+ L1-1 事件同事务写 outbox（草案 §8.2）；
- 清理进程/Redis 缓存键（principal:{id} / user:{username}），保证下一请求命中新状态。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AgentApiKey, AuditLog, Role, User, user_role
from openbase.modules.identity.agent_keys import AGENT_KEY_STATUS_ACTIVE, AGENT_KEY_STATUS_REVOKED
from openbase.modules.identity.events import (
    enqueue_lifecycle_event,
    event_type_for_transition,
)
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    STATUS_STATE_DEACTIVATED,
    STATUS_STATE_SUSPENDED,
    SUBJECT_TYPE_AGENT,
    SUBJECT_TYPE_USER,
    status_int_from_state,
    validate_transition,
)

logger = logging.getLogger("openbase.identity.lifecycle")

# 吊销类迁移（触发 token_version += 1 / 旧凭据失效）
_REVOKING_TARGETS = frozenset({STATUS_STATE_SUSPENDED, STATUS_STATE_DEACTIVATED})


@dataclass
class LifecycleTransition:
    """状态迁移结果（服务返回，供路由组响应/断言）."""

    subject: User
    previous_state: str
    target_state: str
    role_codes: list[str]


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


class IdentityLifecycleService:
    """生命周期状态迁移服务（admin/受权操作，写路径统一走本服务）."""

    @classmethod
    async def activate(
        cls,
        session: AsyncSession,
        subject_id: int,
        *,
        subject_type: str = SUBJECT_TYPE_USER,
        reason: str | None = None,
        operator: int | None = None,
        request_id: str | None = None,
    ) -> LifecycleTransition:
        """provisioned → active（管理员启用；无吊销副作用）. """
        return await cls._apply(
            session,
            subject_id,
            STATUS_STATE_ACTIVE,
            subject_type=subject_type,
            reason=reason or "activated by operator",
            operator=operator,
            request_id=request_id,
        )

    @classmethod
    async def suspend(
        cls,
        session: AsyncSession,
        subject_id: int,
        *,
        subject_type: str = SUBJECT_TYPE_USER,
        reason: str | None = None,
        operator: int | None = None,
        request_id: str | None = None,
    ) -> LifecycleTransition:
        """active → suspended（即时拒签 + 版本递增 + 发 user.suspended；agent 联动吊销密钥）."""
        return await cls._apply(
            session,
            subject_id,
            STATUS_STATE_SUSPENDED,
            subject_type=subject_type,
            reason=reason or "suspended by operator",
            operator=operator,
            request_id=request_id,
        )

    @classmethod
    async def restore(
        cls,
        session: AsyncSession,
        subject_id: int,
        *,
        subject_type: str = SUBJECT_TYPE_USER,
        reason: str | None = None,
        operator: int | None = None,
        request_id: str | None = None,
    ) -> LifecycleTransition:
        """suspended → active（恢复；token_version 再次递增，旧 token 不复活）."""
        return await cls._apply(
            session,
            subject_id,
            STATUS_STATE_ACTIVE,
            subject_type=subject_type,
            reason=reason or "restored by operator",
            operator=operator,
            request_id=request_id,
        )

    @classmethod
    async def deactivate(
        cls,
        session: AsyncSession,
        subject_id: int,
        *,
        subject_type: str = SUBJECT_TYPE_USER,
        reason: str | None = None,
        operator: int | None = None,
        request_id: str | None = None,
    ) -> LifecycleTransition:
        """active/suspended → deactivated（注销：全部凭据失效 + 发 user.deactivated，数据保留）."""
        return await cls._apply(
            session,
            subject_id,
            STATUS_STATE_DEACTIVATED,
            subject_type=subject_type,
            reason=reason or "deactivated by operator",
            operator=operator,
            request_id=request_id,
        )

    @classmethod
    async def _apply(
        cls,
        session: AsyncSession,
        subject_id: int,
        target_state: str,
        *,
        subject_type: str,
        reason: str | None,
        operator: int | None,
        request_id: str | None,
    ) -> LifecycleTransition:
        """状态迁移统一执行链（校验 → 变更 → 版本递增 → 吊销联动 → 审计 → 事件 → 清缓存）."""
        request_id = request_id or _new_request_id()
        subject = await session.get(User, subject_id)
        if subject is None or subject.is_deleted:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"subject not found: {subject_id}")
        # 路由地址 subject_type 与行 subject_type 不一致 → 视为资源不存在（404）
        if (subject.subject_type or SUBJECT_TYPE_USER) != subject_type:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"subject not found: {subject_type}/{subject_id}")

        previous_state = subject.status_state or STATUS_STATE_ACTIVE
        validate_transition(previous_state, target_state)

        # 1) 状态字段 + 兼容读视图 status(int)
        subject.status_state = target_state
        subject.status_reason = reason
        subject.status = status_int_from_state(target_state)

        # 2) 吊销类迁移 → token_version += 1（suspend/deactivate/restore 后旧 token 不复活）
        is_restore = previous_state == STATUS_STATE_SUSPENDED and target_state == STATUS_STATE_ACTIVE
        if target_state in _REVOKING_TARGETS or is_restore:
            subject.token_version = (subject.token_version or 0) + 1

        role_codes = await cls._role_codes_for(session, subject.id)

        # 3) agent 主体停用/注销 → 联动吊销全部 sk-agent-* 密钥（Q2-S5）
        if subject_type == SUBJECT_TYPE_AGENT and target_state in _REVOKING_TARGETS:
            await cls._revoke_all_agent_keys(session, subject.id)

        # 4) 审计留痕（action=identity.lifecycle.<to>，草案 §4.1；批次 3/T8 并入
        #    §8.2 identity 块：principal/delegated/effective/…/request_id 六键）
        from openbase.modules.protocol_headers.identity_audit import (
            build_identity_section,
        )

        session.add(
            AuditLog(
                user_id=operator,
                tenant_id=subject.tenant_id,
                action=f"identity.lifecycle.{target_state}",
                resource="users",
                resource_id=str(subject.id),
                request_id=request_id,
                detail={
                    "from": previous_state,
                    "to": target_state,
                    "reason": reason,
                    "operator": operator,
                    "subject_type": subject_type,
                    "tenant_code": subject.tenant_code,
                    "request_id": request_id,
                    "identity": build_identity_section(
                        subject_id=operator,
                        subject_type="user",
                        tenant_code=subject.tenant_code,
                        auth_method="internal",
                        request_id=request_id,
                    ),
                },
            )
        )

        # 5) L1-1 级联事件：同事务写 outbox（T5 事件源本体前的骨架，草案 §8.2）
        event_type = event_type_for_transition(previous_state, target_state)
        if event_type is not None:
            await enqueue_lifecycle_event(
                session,
                subject=subject,
                event_type=event_type,
                previous_state=previous_state,
                current_state=target_state,
                reason=reason,
                role_codes=role_codes,
                operator=operator,
            )

        # 6) 清缓存：状态/tvn 变更立即失效 principal/user 缓存键
        cls._invalidate_caches(subject)

        logger.info(
            "identity lifecycle transition",
            extra={
                "subject_id": subject.id,
                "subject_type": subject_type,
                "from": previous_state,
                "to": target_state,
                "token_version": subject.token_version,
                "operator": operator,
                "request_id": request_id,
            },
        )
        return LifecycleTransition(
            subject=subject,
            previous_state=previous_state,
            target_state=target_state,
            role_codes=role_codes,
        )

    @staticmethod
    async def _role_codes_for(session: AsyncSession, user_id: int) -> list[str]:
        result = await session.execute(
            select(Role.code)
            .join(user_role, user_role.c.role_id == Role.id)
            .where(user_role.c.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def _revoke_all_agent_keys(session: AsyncSession, agent_id: int) -> None:
        result = await session.execute(
            update(AgentApiKey)
            .where(AgentApiKey.agent_id == agent_id, AgentApiKey.status == AGENT_KEY_STATUS_ACTIVE)
            .values(status=AGENT_KEY_STATUS_REVOKED)
        )
        logger.info(
            "agent keys revoked by lifecycle transition",
            extra={"agent_id": agent_id, "revoked_count": max(int(result.rowcount or 0), 0)},
        )

    @staticmethod
    def _invalidate_caches(subject: User) -> None:
        """失效 principal/user 缓存键（与主体验证器共用同一失效函数，T3 一致性）.

        状态/版本变更后 principal:{id} 缓存键必须失效，下一请求命中新状态/新版本
        （设计草案 §5.1/§11 T3-7；Redis 不可用时静默降级）。
        """
        from openbase.modules.identity.verification import invalidate_principal_cache

        invalidate_principal_cache(subject.id, subject.username)


__all__ = ["IdentityLifecycleService", "LifecycleTransition"]
