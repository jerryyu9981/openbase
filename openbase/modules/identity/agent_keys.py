"""agent 服务密钥服务（U1 T1，RA-01/OB-1；设计草案 §3.2/Q2-S2/S5）.

- 前缀 `sk-agent-*`（可辨识），服务端只存 sha256 `key_hash`（明文仅生成响应展示一次）；
- 多密钥并存、可轮换（新签）、可吊销（revoked_at 语义以 status=revoked 表达，即时失效）；
- 与既有 `ApiKeyStore`（ob_k_*，内存态）不重叠：sk-agent-* 为 DB 持久化的主体化凭据面。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AgentApiKey, Role, User, user_role
from openbase.modules.identity.state_machine import (
    STATUS_STATE_ACTIVE,
    SUBJECT_TYPE_AGENT,
)

logger = logging.getLogger("openbase.identity.agent_keys")

AGENT_KEY_PREFIX = "sk-agent-"
AGENT_KEY_STATUS_ACTIVE = "active"
AGENT_KEY_STATUS_REVOKED = "revoked"


def agent_key_hash(raw_key: str) -> str:
    """哈希明文密钥（sha256 hexdigest，与 ApiKeyStore._hash 同构算法）."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def secrets_token_urlsafe() -> str:
    """生成随机段（独立函数便于测试/替换）."""
    return secrets.token_urlsafe(24)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class AgentKeyService:
    """agent 密钥生命周期操作（发放/轮换/吊销/列表/校验）."""

    @classmethod
    async def issue_key(
        cls,
        session: AsyncSession,
        *,
        agent_id: int,
        name: str | None = None,
        expires_at: dt.datetime | None = None,
        created_by: int | None = None,
    ) -> tuple[str, AgentApiKey]:
        """签发新 sk-agent-* 密钥，返回明文（仅此一次）+ 落库记录.

        Returns:
            (raw_key, record)；raw_key 仅在此返回，服务端不落明文。
        """
        raw_key = f"{AGENT_KEY_PREFIX}{secrets_token_urlsafe()}"
        record = AgentApiKey(
            agent_id=agent_id,
            key_prefix=AGENT_KEY_PREFIX,
            key_hash=agent_key_hash(raw_key),
            key_suffix=raw_key[-6:],
            name=name,
            status=AGENT_KEY_STATUS_ACTIVE,
            expires_at=expires_at,
            created_by=created_by,
        )
        session.add(record)
        await session.flush()
        logger.info("agent api key issued", extra={"agent_id": agent_id, "key_id": record.id})
        return raw_key, record

    @classmethod
    async def revoke_key(
        cls,
        session: AsyncSession,
        *,
        agent_id: int,
        key_id: int,
    ) -> AgentApiKey:
        """吊销单条密钥（即时失效：校验按 status/expires 拒绝）."""
        record = await cls._get_key(session, agent_id=agent_id, key_id=key_id)
        record.status = AGENT_KEY_STATUS_REVOKED
        await session.flush()
        logger.info("agent api key revoked", extra={"agent_id": agent_id, "key_id": key_id})
        return record

    @classmethod
    async def list_keys(cls, session: AsyncSession, *, agent_id: int) -> list[AgentApiKey]:
        """列出某 agent 的全部密钥记录（不回显明文/哈希）. """
        result = await session.execute(
            select(AgentApiKey)
            .where(AgentApiKey.agent_id == agent_id)
            .order_by(AgentApiKey.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def _get_key(session: AsyncSession, *, agent_id: int, key_id: int) -> AgentApiKey:
        result = await session.execute(
            select(AgentApiKey).where(
                AgentApiKey.id == key_id, AgentApiKey.agent_id == agent_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"agent api key not found: {key_id}")
        return record


async def resolve_agent_principal(session: AsyncSession, raw_key: str) -> dict[str, Any]:
    """agent 密钥校验 → 主体 principal（供 get_current_user 等认证依赖使用）.

    Raises:
        BaseError: AUTH_API_KEY_INVALID（无效/已吊销/过期/非 agent 绑定）；
            AUTH_PRINCIPAL_DISABLED（agent 主体非 active）。
    """
    result = await session.execute(
        select(AgentApiKey, User)
        .join(User, User.id == AgentApiKey.agent_id)
        .where(AgentApiKey.key_hash == agent_key_hash(raw_key))
    )
    row = result.first()
    if row is None:
        raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "invalid agent api key")
    record, user = row

    if record.status != AGENT_KEY_STATUS_ACTIVE:
        raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "agent api key revoked")
    if record.expires_at is not None and record.expires_at < _now():
        raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "agent api key expired")
    if user.subject_type != SUBJECT_TYPE_AGENT:
        raise BaseError(ErrorCode.AUTH_API_KEY_INVALID, "api key not bound to agent subject")
    if user.status_state != STATUS_STATE_ACTIVE:
        raise BaseError(ErrorCode.AUTH_PRINCIPAL_DISABLED, "agent subject is not active")

    record.last_used_at = _now()
    role_result = await session.execute(
        select(Role.code)
        .join(user_role, user_role.c.role_id == Role.id)
        .where(user_role.c.user_id == user.id)
    )
    role_codes = list(role_result.scalars().all())
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "subject_type": user.subject_type,
        "credential_type": user.credential_type,
        "tenant_id": user.tenant_id,
        "tenant_code": user.tenant_code,
        "status_state": user.status_state,
        "token_version": user.token_version,
        "roles": role_codes,
        "permissions": [],
        "auth_method": "sk-agent",
    }
