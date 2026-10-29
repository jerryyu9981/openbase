"""agent 服务密钥服务（U1 T1，RA-01/OB-1；设计草案 §3.2/Q2-S2/S5）.

- 前缀 `sk-agent-*`（可辨识），服务端只存 sha256 `key_hash`（明文仅生成响应展示一次）；
- 多密钥并存、可轮换（新签）、可吊销（revoked_at 语义以 status=revoked 表达，即时失效）；
- 与既有服务 Key（`ob_k_*`，v1.5 起由 `service_api_keys` 表持久化）不重叠：
  sk-agent-* 为 DB 持久化的主体化凭据面。
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
from openbase.core.models import AgentApiKey, AuditLog, Role, User, user_role
from openbase.modules.identity.state_machine import SUBJECT_TYPE_AGENT

logger = logging.getLogger("openbase.identity.agent_keys")

AGENT_KEY_PREFIX = "sk-agent-"
AGENT_KEY_STATUS_ACTIVE = "active"
AGENT_KEY_STATUS_REVOKED = "revoked"

# E0-4（R4/P0-4）：agent Key 生命周期审计动作码（审计表 action 列）
ACTION_AGENT_KEY_ISSUE = "identity.agent_key.issue"
ACTION_AGENT_KEY_REVOKE = "identity.agent_key.revoke"
AUDIT_RESOURCE_AGENT_KEY = "agent_api_keys"


def _audit_request_id(request_id: str | None) -> str:
    """审计记录 request_id（未透传时生成内部标识；列不可空）."""
    return request_id or f"internal-{secrets.token_hex(6)}"


def _audit_detail(
    record: AgentApiKey,
    operator_id: int | None,
    request_id: str | None,
) -> dict[str, Any]:
    """审计明细（仅元数据；禁止明文/哈希）."""
    return {
        "key_id": record.id,
        "agent_id": record.agent_id,
        "name": record.name,
        "key_suffix": record.key_suffix,
        "operator_id": operator_id,
        "request_id": request_id,
    }


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
        request_id: str | None = None,
    ) -> tuple[str, AgentApiKey]:
        """签发新 sk-agent-* 密钥，返回明文（仅此一次）+ 落库记录.

        E0-4（R4/P0-4）：同一事务内写 ``AuditLog``（key_id/agent_id/name/
        key_suffix/操作人/request_id；**不含明文与哈希**）。

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
        session.add(
            AuditLog(
                user_id=created_by,
                action=ACTION_AGENT_KEY_ISSUE,
                resource=AUDIT_RESOURCE_AGENT_KEY,
                resource_id=str(record.id),
                request_id=_audit_request_id(request_id),
                detail=_audit_detail(record, created_by, request_id),
            )
        )
        await session.flush()
        logger.info("agent api key issued", extra={"agent_id": agent_id, "key_id": record.id})
        # E0-1（边缘设备身份化）：终端应按设备签发独立 sk-agent-* 凭据并设置有效期；
        # 未设置 expires_at 时给出运维提示（不阻断签发，便于存量流程平滑）。
        if expires_at is None:
            logger.warning(
                "agent api key issued without expires_at; "
                "edge device credentials should set expiry and never share service keys",
                extra={"agent_id": agent_id, "key_id": record.id},
            )
        return raw_key, record

    @classmethod
    async def revoke_key(
        cls,
        session: AsyncSession,
        *,
        agent_id: int,
        key_id: int,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> AgentApiKey:
        """吊销单条密钥（即时失效：校验按 status/expires 拒绝）.

        E0-4（R4/P0-4）：同一事务内写 ``AuditLog``（不含明文）。
        """
        record = await cls._get_key(session, agent_id=agent_id, key_id=key_id)
        record.status = AGENT_KEY_STATUS_REVOKED
        session.add(
            AuditLog(
                user_id=operator_id,
                action=ACTION_AGENT_KEY_REVOKE,
                resource=AUDIT_RESOURCE_AGENT_KEY,
                resource_id=str(record.id),
                request_id=_audit_request_id(request_id),
                detail=_audit_detail(record, operator_id, request_id),
            )
        )
        await session.flush()
        logger.info("agent api key revoked", extra={"agent_id": agent_id, "key_id": key_id})
        # E0-7（一键吊销）：吊销即失效（校验按 status 拒绝），并清理该主体可能存在的
        # principal 快照缓存，确保在线 ≤60s 内不因缓存残留继续放行。
        from openbase.modules.identity.verification import invalidate_principal_cache

        invalidate_principal_cache(agent_id)
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
            AUTH_PRINCIPAL_DISABLED（agent 主体非 active）；
            AUTH_UNAUTHORIZED（DB 不可达 → fail-closed 401，P2-1 T2 D-V7）。
    """
    try:
        result = await session.execute(
            select(AgentApiKey, User)
            .join(User, User.id == AgentApiKey.agent_id)
            .where(AgentApiKey.key_hash == agent_key_hash(raw_key))
        )
    except Exception as exc:  # noqa: BLE001 - DB 不可达 → fail-closed（D-V7）
        # agent 密钥校验依赖 DB（按 key_hash 查库）；DB 不可达无法证明密钥有效 →
        # 拒绝，不降级放行（与 D-V1 JWT 场景的 fail-open 刻意不同）。
        logger.warning(
            "agent principal verify db read failed; fail-closed",
            extra={"error": str(exc) or exc.__class__.__name__},
        )
        raise BaseError(
            ErrorCode.AUTH_UNAUTHORIZED,
            "agent principal verification unavailable: database degraded",
        ) from exc
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
    # U1 T3（K04）：agent 请求与 user JWT 共用同一状态门禁（assert_principal_active），
    # key 校验含主体状态门禁（设计草案 §5.3「agent suspend → 全部 key 校验失败」）。
    from openbase.modules.identity.verification import assert_principal_active

    assert_principal_active(user.status_state)

    role_result = await session.execute(
        select(Role.code)
        .join(user_role, user_role.c.role_id == Role.id)
        .where(user_role.c.user_id == user.id)
    )
    role_codes = list(role_result.scalars().all())
    principal = {
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
    # E0-7（P0-7）：last_used_at 必须提交才可见（get_db 请求会话关闭即回滚）。
    # 先组装返回体再提交，避免 expire_on_commit=True 的会话在提交后触发异步懒加载；
    # 使用痕迹写入失败不影响本次认证（尽力而为 + WARN 留痕）。
    record.last_used_at = _now()
    try:
        await session.commit()
    except Exception as exc:  # noqa: BLE001 - 使用痕迹落库失败不阻断认证
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 - rollback 失败仅记录
            pass
        logger.warning(
            "agent key last_used_at persist failed",
            extra={"agent_id": user.id, "key_id": record.id, "error": str(exc) or exc.__class__.__name__},
        )
    return principal
