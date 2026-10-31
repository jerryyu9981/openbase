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
import threading
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import AuditLog, ServiceApiKey
from openbase.core.timeutil import as_utc, utc_now

logger = logging.getLogger("openbase.auth.service_keys")

SERVICE_KEY_PREFIX = "ob_k_"
SERVICE_KEY_STATUS_ACTIVE = "active"
SERVICE_KEY_STATUS_REVOKED = "revoked"
# E1-1：last_used_at 写入节流（同一 Key 60s 内重复校验不重复落库，降低边缘写放大）
SERVICE_KEY_TOUCH_INTERVAL_SECONDS = 60

# E0-4（R4/P0-4）：Key 生命周期审计动作码（审计表 action 列）
ACTION_SERVICE_KEY_ISSUE = "auth.service_key.issue"
ACTION_SERVICE_KEY_REVOKE = "auth.service_key.revoke"
# E1-1（R9/P1-2）：轮换审计动作码
ACTION_SERVICE_KEY_ROTATE = "auth.service_key.rotate"
# C-09（P2）：Key 侧日对账审计动作码
ACTION_SERVICE_KEY_RECONCILE = "auth.service_key.reconcile"
AUDIT_RESOURCE_SERVICE_KEY = "service_api_keys"

# C-08（P2）：到期提醒默认提前量（天）与事件去重窗口（Key+日，36h 覆盖跨时区重扫）
SERVICE_KEY_EXPIRING_WITHIN_DAYS = 7
_EXPIRING_DEDUPE_TTL_SECONDS = 36 * 3600
_expiring_claimed_local: set[tuple[str, str]] = set()
_expiring_claim_lock = threading.Lock()


def _audit_request_id(request_id: str | None) -> str:
    """审计记录 request_id（未透传时生成内部标识；列不可空）."""
    return request_id or f"internal-{uuid.uuid4().hex[:12]}"


def _audit_detail(record: ServiceApiKey, operator_id: int | None, request_id: str | None) -> dict[str, Any]:
    """审计明细（仅元数据；禁止明文/哈希）."""
    expires_at = as_utc(record.expires_at)
    return {
        "key_id": record.key_id,
        "name": record.name,
        "scope": record.scope,
        "tenant_code": record.tenant_code,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "operator_id": operator_id,
        "request_id": request_id,
    }


DEFAULT_SCOPE: dict[str, list[str]] = {"system": ["*"], "tenants": ["*"]}


def service_key_hash(raw_key: str) -> str:
    """哈希明文 Key（sha256 hexdigest，与历史内存版同构，便于平滑迁移）."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def public_record(record: ServiceApiKey) -> dict[str, Any]:
    """对外记录（不回显明文与哈希；时间沿用历史 float 契约）."""
    expires_at = as_utc(record.expires_at)
    last_used_at = as_utc(record.last_used_at)
    return {
        "id": record.key_id,
        "name": record.name,
        "scope": record.scope,
        "description": record.description,
        "created": record.created_at.timestamp() if record.created_at else 0.0,
        "revoked": record.status == SERVICE_KEY_STATUS_REVOKED,
        # E1-1：过期/最近使用/轮换来源/归属租户（仅元数据）
        "expires_at": expires_at.timestamp() if expires_at else None,
        "last_used_at": last_used_at.timestamp() if last_used_at else None,
        "rotated_from": record.rotated_from,
        "tenant_code": record.tenant_code,
    }


def _default_expires_at() -> dt.datetime | None:
    """默认有效期（E1-1：settings.service_key_ttl_days，0 = 不过期）."""
    from openbase.settings import get_settings

    try:
        ttl_days = int(getattr(get_settings(), "service_key_ttl_days", 0) or 0)
    except (TypeError, ValueError):
        ttl_days = 0
    if ttl_days <= 0:
        return None
    return utc_now() + dt.timedelta(days=ttl_days)


def _rotate_grace_hours() -> int:
    """轮换宽限期（小时；settings.service_key_rotate_grace_hours，负值按 0 处理）."""
    from openbase.settings import get_settings

    try:
        hours = int(getattr(get_settings(), "service_key_rotate_grace_hours", 0) or 0)
    except (TypeError, ValueError):
        hours = 0
    return max(hours, 0)


def _claim_expiring_notification(key_id: str, day: str) -> bool:
    """抢占「Key + 日」到期提醒（C-08）：Redis ``SET NX EX``，不可用回退进程内."""
    token = f"openbase:service_key:expiring:{key_id}:{day}"
    try:
        from openbase.core.cache.redis_client import get_client

        client = get_client()
        if client is not None:
            return bool(
                client.set(token, "1", nx=True, ex=_EXPIRING_DEDUPE_TTL_SECONDS)
            )
    except Exception as exc:  # noqa: BLE001 - Redis 异常回退进程内去重
        logger.warning(
            "expiring notification dedupe redis failed; fallback to process set",
            extra={"key_id": key_id, "error": str(exc) or exc.__class__.__name__},
        )
    with _expiring_claim_lock:
        marker = (key_id, day)
        if marker in _expiring_claimed_local:
            return False
        if len(_expiring_claimed_local) >= 20000:
            _expiring_claimed_local.clear()
        _expiring_claimed_local.add(marker)
        return True


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
    """服务 Key 生命周期操作（发放/校验/轮换/吊销/列表）."""

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
        expires_at: dt.datetime | None = None,
        rotated_from: str | None = None,
        tenant_code: str | None = None,
    ) -> tuple[str, ServiceApiKey]:
        """签发服务 Key，返回明文（仅此一次）+ 落库记录.

        E0-4（R4/P0-4）：同一事务内写 ``AuditLog``（key_id/name/scope/操作人/
        request_id；**不含明文与哈希**）。E1-1（R9）：默认有效期
        ``settings.service_key_ttl_days``（90 天，0=不过期）；E1-2（R10）：同事务写
        ``service_key.issued`` 事件到 outbox。

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
            expires_at=as_utc(expires_at) if expires_at is not None else _default_expires_at(),
            rotated_from=rotated_from,
            tenant_code=tenant_code,
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
        await cls._emit_event(
            session,
            "service_key.issued",
            record,
            previous_state="none",
            current_state="active",
            reason="issue",
            operator_id=created_by,
            request_id=request_id,
        )
        await session.flush()
        logger.info(
            "service api key issued",
            extra={"api_key_name": name, "api_key_id": record.key_id},
        )
        return raw_key, record

    @classmethod
    async def list_keys(
        cls, session: AsyncSession, *, tenant_code: str | None = None
    ) -> list[ServiceApiKey]:
        """列出签发记录（按创建顺序；E1-4/R3：非超管按归属租户过滤）."""
        statement = select(ServiceApiKey).order_by(ServiceApiKey.id)
        if tenant_code is not None:
            statement = statement.where(ServiceApiKey.tenant_code == tenant_code)
        result = await session.execute(statement)
        return list(result.scalars().all())

    @classmethod
    async def list_expiring(
        cls,
        session: AsyncSession,
        *,
        within_days: int = SERVICE_KEY_EXPIRING_WITHIN_DAYS,
        tenant_code: str | None = None,
    ) -> list[ServiceApiKey]:
        """到期清单（C-08）：有效且 ``expires_at <= now + within_days``（含已过期）.

        只读；按租户过滤与列表端口径一致。时间比较在应用层完成（SQLite/存量库
        naive datetime 归一后再比较，避免方言时区差异）。
        """
        deadline = utc_now() + dt.timedelta(days=max(int(within_days), 0))
        statement = (
            select(ServiceApiKey)
            .where(
                ServiceApiKey.status == SERVICE_KEY_STATUS_ACTIVE,
                ServiceApiKey.expires_at.is_not(None),
            )
            .order_by(ServiceApiKey.expires_at)
        )
        if tenant_code is not None:
            statement = statement.where(ServiceApiKey.tenant_code == tenant_code)
        result = await session.execute(statement)
        records = list(result.scalars().all())
        return [
            record
            for record in records
            if as_utc(record.expires_at) is not None
            and as_utc(record.expires_at) <= deadline
        ]

    @classmethod
    async def emit_expiring_events(
        cls,
        session: AsyncSession,
        *,
        within_days: int = SERVICE_KEY_EXPIRING_WITHIN_DAYS,
        reference_time: dt.datetime | None = None,
        request_id: str | None = None,
    ) -> int:
        """为到期/即将到期 Key 写入 ``service_key.expiring`` 事件（C-08）.

        去重：同一 Key 同一日只投递一次（Redis ``SET NX EX`` 跨实例共享；
        Redis 不可用回退进程内集合）。只提醒不阻断，不修改 Key 状态。

        Returns:
            本次实际新投递的事件数。
        """
        now = as_utc(reference_time) or utc_now()
        day = now.date().isoformat()
        records = await cls.list_expiring(session, within_days=within_days)
        emitted = 0
        for record in records:
            if not _claim_expiring_notification(record.key_id, day):
                continue
            expires_at = as_utc(record.expires_at)
            days_remaining = int(
                (expires_at - now).total_seconds() // 86400
            ) if expires_at else 0
            await cls._emit_event(
                session,
                "service_key.expiring",
                record,
                previous_state="active",
                current_state="active",
                reason="expiring",
                operator_id=None,
                request_id=request_id,
                extra={
                    "days_remaining": days_remaining,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                },
            )
            emitted += 1
        if emitted:
            await session.flush()
        return emitted

    @classmethod
    async def reconcile(
        cls,
        session: AsyncSession,
        *,
        reference_time: dt.datetime | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Key 侧日对账（C-09）：``签发数 = 有效数 + 吊销数 + 过期数``.

        差异写审计（``auth.service_key.reconcile``）并 WARN/ERROR 留痕；
        仅本仓 Key 台账自洽校验，不做跨系统比对（下游拒绝数归 K-03）。

        Returns:
            计数快照（issued/active/revoked/expired/balanced/reference_time/audit）。
        """
        now = as_utc(reference_time) or utc_now()
        result = await session.execute(select(ServiceApiKey))
        records = list(result.scalars().all())
        issued = len(records)
        revoked = sum(
            1 for record in records if record.status == SERVICE_KEY_STATUS_REVOKED
        )
        active = 0
        expired = 0
        for record in records:
            if record.status != SERVICE_KEY_STATUS_ACTIVE:
                continue
            expires_at = as_utc(record.expires_at)
            if expires_at is not None and expires_at <= now:
                expired += 1
            else:
                active += 1
        balanced = issued == active + revoked + expired
        audit = AuditLog(
            user_id=None,
            action=ACTION_SERVICE_KEY_RECONCILE,
            resource=AUDIT_RESOURCE_SERVICE_KEY,
            resource_id="reconciliation",
            request_id=_audit_request_id(request_id),
            detail={
                "issued": issued,
                "active": active,
                "revoked": revoked,
                "expired": expired,
                "balanced": balanced,
                "reference_time": now.isoformat(),
            },
        )
        session.add(audit)
        await session.flush()
        log = logger.info if balanced else logger.error
        log(
            "service api key reconciliation",
            extra={
                "issued": issued,
                "active": active,
                "revoked": revoked,
                "expired": expired,
                "balanced": balanced,
            },
        )
        return {
            "issued": issued,
            "active": active,
            "revoked": revoked,
            "expired": expired,
            "balanced": balanced,
            "reference_time": now.isoformat(),
            "audit": audit,
        }

    @classmethod
    async def rotate(
        cls,
        session: AsyncSession,
        key_id: str,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
        grace_hours: int | None = None,
        expires_at: dt.datetime | None = None,
        tenant_code: str | None = None,
    ) -> tuple[str, ServiceApiKey, ServiceApiKey] | None:
        """轮换服务 Key（E1-1/R9）：签发新 Key + 旧 Key 进入宽限期后自动失效.

        旧 Key 不立即吊销（双 Key 并存零中断），到期时间被收紧为
        ``min(原到期, now + grace)``；宽限期默认 ``settings.service_key_rotate_grace_hours``。

        Returns:
            (new_raw_key, new_record, old_record)；未命中返回 None；
            旧 Key 非 active → BIZ_CONFLICT。
        """
        result = await session.execute(
            select(ServiceApiKey).where(ServiceApiKey.key_id == key_id)
        )
        old_record = result.scalar_one_or_none()
        if old_record is None:
            return None
        if old_record.status != SERVICE_KEY_STATUS_ACTIVE:
            raise BaseError(ErrorCode.BIZ_CONFLICT, "api key is not active; rotate rejected")

        grace = _rotate_grace_hours() if grace_hours is None else max(int(grace_hours), 0)
        grace_expiry = utc_now() + dt.timedelta(hours=grace)
        current_expiry = as_utc(old_record.expires_at)
        old_record.expires_at = (
            min(current_expiry, grace_expiry) if current_expiry else grace_expiry
        )

        raw_key, new_record = await cls.issue(
            session,
            name=old_record.name,
            scope=old_record.scope,
            description=old_record.description,
            created_by=operator_id,
            request_id=request_id,
            expires_at=expires_at,
            rotated_from=old_record.key_id,
            tenant_code=(
                old_record.tenant_code if tenant_code is None else tenant_code
            ),
        )
        session.add(
            AuditLog(
                user_id=operator_id,
                action=ACTION_SERVICE_KEY_ROTATE,
                resource=AUDIT_RESOURCE_SERVICE_KEY,
                resource_id=old_record.key_id,
                request_id=_audit_request_id(request_id),
                detail={
                    "old_key_id": old_record.key_id,
                    "new_key_id": new_record.key_id,
                    "name": old_record.name,
                    "grace_hours": grace,
                    "operator_id": operator_id,
                    "request_id": request_id,
                },
            )
        )
        await cls._emit_event(
            session,
            "service_key.rotated",
            old_record,
            previous_state="active",
            current_state="rotated",
            reason="rotate",
            operator_id=operator_id,
            request_id=request_id,
            extra={"new_key_id": new_record.key_id},
        )
        await session.flush()
        logger.info(
            "service api key rotated",
            extra={
                "old_api_key_id": old_record.key_id,
                "new_api_key_id": new_record.key_id,
                "grace_hours": grace,
            },
        )
        return raw_key, new_record, old_record

    @classmethod
    async def revoke_by_id(
        cls,
        session: AsyncSession,
        key_id: str,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> ServiceApiKey | None:
        """按稳定标识吊销；未命中返回 None（路由层转 404）."""
        result = await session.execute(
            select(ServiceApiKey).where(ServiceApiKey.key_id == key_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        await cls._mark_revoked(
            session,
            record,
            operator_id=operator_id,
            request_id=request_id,
        )
        await session.flush()
        return record

    @classmethod
    async def revoke_by_raw(
        cls,
        session: AsyncSession,
        raw_key: str,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> ServiceApiKey | None:
        """按明文吊销（兼容历史接口 `DELETE /api/v1/auth/api-keys/{raw_key}`）."""
        result = await session.execute(
            select(ServiceApiKey).where(
                ServiceApiKey.key_hash == service_key_hash(raw_key)
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        await cls._mark_revoked(
            session,
            record,
            operator_id=operator_id,
            request_id=request_id,
        )
        await session.flush()
        return record

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
            通过返回凭据 dict（不含 key_hash）；无效/吊销/过期/越 scope 返回 None。
        """
        credential = await cls.lookup(session, raw_key)
        if credential is None:
            return None
        return credential if scope_allows(credential["scope"], system, tenant_id) else None

    @classmethod
    async def lookup(cls, session: AsyncSession, raw_key: str) -> dict[str, Any] | None:
        """按明文取有效凭据（校验存在性/吊销/过期，不校验 scope）."""
        result = await session.execute(
            select(ServiceApiKey).where(
                ServiceApiKey.key_hash == service_key_hash(raw_key)
            )
        )
        record = result.scalar_one_or_none()
        if record is None or record.status != SERVICE_KEY_STATUS_ACTIVE:
            return None
        expires_at = as_utc(record.expires_at)
        if expires_at is not None and expires_at <= utc_now():
            return None
        return public_record(record)

    @classmethod
    async def touch_last_used(cls, session: AsyncSession, key_id: str) -> None:
        """记录最近一次校验通过时间（尽力而为；失败不阻断认证）.

        使用痕迹属独立遥测写入，显式提交以免随请求会话关闭回滚；
        单条 UPDATE 完成，避免先读后写。
        """
        from sqlalchemy import update

        try:
            await session.execute(
                update(ServiceApiKey)
                .where(ServiceApiKey.key_id == key_id)
                .values(last_used_at=utc_now())
            )
            await session.commit()
        except Exception as exc:  # noqa: BLE001 - 使用痕迹写入失败不阻断认证
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001 - rollback 失败仅记录
                pass
            logger.warning(
                "service key last_used_at persist failed",
                extra={"key_id": key_id, "error": str(exc) or exc.__class__.__name__},
            )

    @staticmethod
    async def _emit_event(
        session: AsyncSession,
        event_type: str,
        record: ServiceApiKey,
        *,
        previous_state: str,
        current_state: str,
        reason: str,
        operator_id: int | None,
        request_id: str | None,
        extra: dict | None = None,
    ) -> None:
        """写 Key 事件到 outbox（E1-2；局部导入避免 auth ↔ identity 循环依赖）."""
        from openbase.modules.identity.events import enqueue_key_event

        await enqueue_key_event(
            session,
            event_type=event_type,
            key_kind="service",
            key_id=record.key_id,
            key_name=record.name,
            subject_id=operator_id or 0,
            subject_type="service",
            tenant_code=record.tenant_code,
            previous_state=previous_state,
            current_state=current_state,
            reason=reason,
            operator=operator_id,
            request_id=request_id,
            scope=record.scope,
            extra=extra,
        )

    @classmethod
    async def _mark_revoked(
        cls,
        session: AsyncSession,
        record: ServiceApiKey,
        *,
        operator_id: int | None = None,
        request_id: str | None = None,
    ) -> None:
        """吊销并留痕（幂等：已吊销不重复写审计/事件）."""
        if record.status == SERVICE_KEY_STATUS_REVOKED:
            return
        record.status = SERVICE_KEY_STATUS_REVOKED
        record.revoked_at = utc_now()
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
        await cls._emit_event(
            session,
            "service_key.revoked",
            record,
            previous_state="active",
            current_state="revoked",
            reason="revoke",
            operator_id=operator_id,
            request_id=request_id,
        )
        logger.info(
            "service api key revoked",
            extra={"api_key_name": record.name, "api_key_id": record.key_id},
        )
