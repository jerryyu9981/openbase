"""agent 主体服务（U1 T1，RA-01/OB-1；设计草案 §3.1/§3.3/Q2-S3）.

Agent 不是独立实体、亦非 User 子类型：以 users.subject_type='agent' 行承载，
共享 roles（user_role 通用挂载）与状态/域语义；凭据面仅 api_key（禁登录面）。
创建时默认挂最低角色 viewer，显式提权由调用方在受控角色枚举内指定。
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import Role, User, user_role
from openbase.modules.identity.state_machine import (
    CREDENTIAL_TYPE_API_KEY,
    STATUS_STATE_ACTIVE,
    SUBJECT_TYPE_AGENT,
)

logger = logging.getLogger("openbase.identity.agents")

DEFAULT_AGENT_ROLE = "viewer"
# 受控角色枚举（与 users 模块 ALLOWED_ROLES 同源；提权须显式指定）
ALLOWED_AGENT_ROLES = ("admin", "org_admin", "org_member", "viewer")


async def create_agent_subject(
    session: AsyncSession,
    *,
    username: str,
    display_name: str,
    tenant_id: int | None = None,
    role: str = DEFAULT_AGENT_ROLE,
    created_by: int | None = None,
    credential_type: str = CREDENTIAL_TYPE_API_KEY,
) -> User:
    """创建 agent 主体行（subject_type=agent + 默认 viewer 角色挂载）.

    Args:
        session: 数据库会话（提交由调用方负责，保证与首条密钥同事务）。
        username: 平台唯一用户名（建议可辨识前缀如 ``agent:``，不强制）。
        display_name: 展示名。
        tenant_id: 归属租户（按域隔离，可选）。
        role: 初始角色码（默认 viewer 最低权限；显式提权须管理员授权）。
        created_by: 创建操作者 id。
        credential_type: 凭据面，强制恒为 api_key。

    Raises:
        BaseError: PARAM_INVALID（凭据面/角色非法）、BIZ_CONFLICT（用户名重复）、
            BIZ_NOT_FOUND（角色未就绪）。
    """
    if credential_type != CREDENTIAL_TYPE_API_KEY:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            f"agent credential_type must be {CREDENTIAL_TYPE_API_KEY}, got {credential_type!r}",
        )
    if role not in ALLOWED_AGENT_ROLES:
        raise BaseError(ErrorCode.PARAM_INVALID, f"invalid agent role: {role}")

    existing = await session.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        raise BaseError(ErrorCode.BIZ_CONFLICT, f"username already exists: {username}")

    tenant_code = await _resolve_tenant_code(session, tenant_id)
    agent = User(
        username=username,
        password_hash="",
        display_name=display_name,
        status=1,
        tenant_id=tenant_id,
        subject_type=SUBJECT_TYPE_AGENT,
        credential_type=CREDENTIAL_TYPE_API_KEY,
        status_state=STATUS_STATE_ACTIVE,
        status_reason="agent provisioned via identity/agents",
        token_version=0,
        tenant_code=tenant_code,
    )
    session.add(agent)
    await session.flush()

    role_row = await session.execute(select(Role).where(Role.code == role))
    role_record = role_row.scalar_one_or_none()
    if role_record is None:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"role not found: {role}")
    await session.execute(
        user_role.insert().values(user_id=agent.id, role_id=role_record.id)
    )

    logger.info(
        "agent subject created",
        extra={"agent_id": agent.id, "username": username, "tenant_id": tenant_id, "operator": created_by},
    )
    return agent


async def ensure_agent_subject(session: AsyncSession, agent_id: int) -> User:
    """确认主体存在且为 agent（否则 404）."""
    row = await session.get(User, agent_id)
    if row is None or row.subject_type != SUBJECT_TYPE_AGENT:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"agent subject not found: {agent_id}")
    return row


async def _resolve_tenant_code(session: AsyncSession, tenant_id: int | None) -> str | None:
    """租户冗余派生列 tenant_code 回填（复用 auth.resolve_tenant_code 共享函数语义）."""
    if tenant_id is None:
        return None
    from openbase.modules.auth import resolve_tenant_code

    return await resolve_tenant_code(tenant_id, session)
