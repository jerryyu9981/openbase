"""服务级 API Key 持久化服务（ob_k_*；v1.5 服务 Key 接 DB 持久化）.

背景：v1.4.1 的 ``ApiKeyStore`` 为进程内内存存储（登记为 P2 债务），OpenBase 重启
后已签发的服务 Key 全部失效、列表清空，生产不可接受。本模块以 ``service_api_keys``
表为唯一事实源，提供签发/校验/吊销/列表；语义与内存版保持一致：

- 明文仅签发时返回一次，服务端只存 sha256 ``key_hash``；
- ``scope`` = ``{"system": [...], "tenants": [...]}``，``*`` 表示全量；
- 吊销即时失效（``status=revoked``），校验按状态拒绝。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import secrets
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.models import AuditLog, ServiceApiKey

logger = logging.getLogger("openbase.auth.service_keys")

SERVICE_KEY_PREFIX = "ob_k_"
SERVICE_KEY_STATUS_ACTIVE = "active"
SERVICE_KEY_STATUS_REVOKED = "revoked"

# E0-4（R4/P0-4）：Key 生命周期审计动作码（审计表 action 列）
ACTION_SERVICE_KEY_ISSUE = "auth.service_key.issue"
ACTION_SERVICE_KEY_REVOKE = "auth.service_key.revoke"
AUDIT_RESOURCE_SERVICE_KEY = "service_api_keys"


def _audit_request_id(request_id: str | None) -> str:
    """审计记录 request_id（未透传时生成内部标识；列不可空）."""
    return request_id or f"internal-{uuid.uuid4().hex[:12]}"


def _audit_detail(record: ServiceApiKey, operator_id: int | None, request_id: str | None) -> dict[str, Any]:
    """审计明细（仅元数据；禁止明文/哈希）."""
    return {
        "key_id": record.key_id,
        "name": record.name,
        "scope": record.scope,
        "operator_id": operator_id,
        "request_id": request_id,
    }


DEFAULT_SCOPE: dict[str, list[str]] = {"system": ["*"], "tenants": ["*"]}


def service_key_hash(raw_key: str) -> str:
    """哈希明文 Key（sha256 hexdigest，与历史内存版同构，便于平滑迁移）."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def public_record(record: ServiceApiKey) -> dict[str, Any]:
    """对外记录（不回显明文与哈希；`created` 沿用历史 float 契约）."""
    return {
        "id": record.key_id,
        "name": record.name,
        "scope": record.scope,
        "description": record.description,
        "created": record.created_at.timestamp() if record.created_at else 0.0,
        "revoked": record.status == SERVICE_KEY_STATUS_REVOKED,
    }


def scope_allows(scope: dict[str, Any] | None, system: str | None, tenant_id: str | None) -> bool:
    """scope 判定（``*`` 表示全量；None 表示不限定该维度）."""
    scope = scope or {}
    systems = scope.get("system") or ["*"]
    tenants = scope.get("tenants") or ["*"]
    if system is not None and system not in systems and "*" not in systems:
        return False
    if tenant_id is not None and tenant_id not in tenants and "*" not in tenants:
        return False
    return True


class ServiceKeyService:
    """服务 Key 生命周期操作（发放/校验/吊销/列表）."""

    @classmethod
    async def issue(
        cls,
        session: AsyncSession,
        *,
        name: str,
        scope: dict[str, Any] | None = None,
        description: str | None = None,
        created_by: int | None = None,
        request_id: str | None = None,
    ) -> tuple[str, ServiceApiKey]:
        """签发服务 Key，返回明文（仅此一次）+ 落库记录.

        E0-4（R4/P0-4）：同一事务内写 ``AuditLog``（key_id/name/scope/操作人/
        request_id；**不含明文与哈希**）。

        Returns:
            (raw_key, record)；明文不落库、不落日志。
        """
        raw_key = f"{SERVICE_KEY_PREFIX}{secrets.token_urlsafe(24)}"
        record = ServiceApiKey(
            key_id=uuid.uuid4().hex,
            name=name,
            key_hash=service_key_hash(raw_key),
            scope=scope or dict(DEFAULT_SCOPE),
            description=description or "",
            status=SERVICE_KEY_STATUS_ACTIVE,
            created_by=created_by,
        )
        session.add(record)
        await session.flush()
        session.add(
            AuditLog(
                user_id=created_by,
                action=ACTION_SERVICE_KEY_ISSUE,
                resource=AUDIT_RESOURCE_SERVICE_KEY,
                resource_id=record.key_id,
                request_id=_audit_request_id(request_id),
                detail=_audit_detail(record, created_by, request_id),
            )
        )
        await session.flush()
        logger.info(
            "service api key issued",
            extra={"api_key_name": name, "api_key_id": record.key_id},
        )
        return raw_key, record

    @classmethod
    async def list_keys(cls, session: AsyncSession) -> list[ServiceApiKey]:
        """列出全部签发记录（按创建顺序）."""
        result = await session.execute(select(ServiceApiKey).order_by(ServiceApiKey.id))
        return list(result.scalars().all())

    @classmethod
    async def revoke_by_id(
        cls,
        session: AsyncSession,
        key_id: str,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> bool:
        """按稳定标识吊销；未命中返回 False（路由层转 404）."""
        result = await session.execute(
            select(ServiceApiKey).where(ServiceApiKey.key_id == key_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        cls._mark_revoked(
            session,
            record,
            operator_id=operator_id,
            request_id=request_id,
        )
        await session.flush()
        return True

    @classmethod
    async def revoke_by_raw(
        cls,
        session: AsyncSession,
        raw_key: str,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> bool:
        """按明文吊销（兼容历史接口 `DELETE /api/v1/auth/api-keys/{raw_key}`）."""
        result = await session.execute(
            select(ServiceApiKey).where(
                ServiceApiKey.key_hash == service_key_hash(raw_key)
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        cls._mark_revoked(
            session,
            record,
            operator_id=operator_id,
            request_id=request_id,
        )
        await session.flush()
        return True

    @classmethod
    async def verify(
        cls,
        session: AsyncSession,
        raw_key: str,
        *,
        system: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        """校验 Key 有效性 + scope.

        Returns:
            通过返回凭据 dict（不含 key_hash）；无效/吊销/越 scope 返回 None。
        """
        credential = await cls.lookup(session, raw_key)
        if credential is None:
            return None
        return credential if scope_allows(credential["scope"], system, tenant_id) else None

    @classmethod
    async def lookup(cls, session: AsyncSession, raw_key: str) -> dict[str, Any] | None:
        """按明文取有效凭据（仅校验存在性/吊销，不校验 scope）."""
        result = await session.execute(
            select(ServiceApiKey).where(
                ServiceApiKey.key_hash == service_key_hash(raw_key)
            )
        )
        record = result.scalar_one_or_none()
        if record is None or record.status != SERVICE_KEY_STATUS_ACTIVE:
            return None
        return public_record(record)

    @staticmethod
    def _mark_revoked(
        session: AsyncSession,
        record: ServiceApiKey,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> None:
        record.status = SERVICE_KEY_STATUS_REVOKED
        record.revoked_at = dt.datetime.now(dt.timezone.utc)
        session.add(
            AuditLog(
                user_id=operator_id,
                action=ACTION_SERVICE_KEY_REVOKE,
                resource=AUDIT_RESOURCE_SERVICE_KEY,
                resource_id=record.key_id,
                request_id=_audit_request_id(request_id),
                detail=_audit_detail(record, operator_id, request_id),
            )
        )
        logger.info(
            "service api key revoked",
            extra={"api_key_name": record.name, "api_key_id": record.key_id},
        )
