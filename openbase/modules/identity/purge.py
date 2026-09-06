"""identity 模块：L1-2 purge 显式合规任务执行器（U1 T6，Q-5=A；设计草案 §9/§11 T6-1~T6-5）.

Q-5=A（保留 + 全链阻断；purge 仅显式合规触发，无自动限期清除）：
- purge 属**罕见合规操作**：仅 deactivated 主体可 purge（非 deactivated → 400
  ``BIZ_NOT_PURGEABLE``）；须一次性授权码二次授权（缺失/无效/过期 → 403
  ``BIZ_PURGE_AUTH_REQUIRED``）+ 影响范围报告确认（scope_report_hash 对账）；
- 授权码由受权管理员签发（CLI/服务函数），短 TTL 单次有效，服务端只存哈希；
- 执行器（``IdentityPurgeService.execute_purge``）：
  ① ``deactivated → purged`` 迁移复用状态机矩阵（state_machine.validate_transition）；
  ② 物理清除主体主行与关联数据：users / agent_api_keys / user_role /
     user_department / oidc_identity / 业务表 owner 行（Notification/FileRecord/
     AiApp/AiAppCall 按 owner 口径，设计草案 §1.1 行 43 + §9.2「审计之外各业务表」）；
  ③ 保留 audit_logs（purge 事件留痕）、subject_blocks（阻断行指向 subject_id
     持续拒绝）、event_consumptions（幂等历史）与 outbox_events（投递历史）；
  ④ 写 ``purge_records`` 终态台账（墓碑）：终态语义、令牌拒绝判定与并发幂等基座；
- 幂等防并发（T7 收口语义登记，U1 T7-1）：``purge_records`` 唯一幂等键取 **username**
  （而非 subject_id，PG/SQLite 跨引擎语义见 ``core/models/base.py::PurgeRecord.__table_args__``
  注释）+ ``idempotency_key`` 全局唯一 —— 并发双触发仅一次执行；重复触发对已 purged
  主体 400 终态拒绝（设计 §9.2 二选一取后者）；幂等键**跨主体复用** → 400
  ``PARAM_INVALID`` 显式拦截（DB 唯一约束仅作并发兜底）。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from openbase.core.errors import BaseError, ErrorCode
from openbase.core.models import (
    AgentApiKey,
    AuditLog,
    OidcIdentity,
    PurgeAuthorization,
    PurgeRecord,
    User,
    user_department,
    user_role,
)
from openbase.core.models.business import AiApp, AiAppCall, FileRecord, Notification
from openbase.modules.identity.state_machine import (
    STATUS_STATE_DEACTIVATED,
    STATUS_STATE_PURGED,
    SUBJECT_TYPE_USER,
    validate_transition,
)

logger = logging.getLogger("openbase.identity.purge")

# ---- 二次授权码参数（设计草案 §9.2：短 TTL 单次有效） ----
PURGE_AUTHORIZATION_TTL_SECONDS = 600
_PURGE_CODE_BYTES = 24  # token_urlsafe(24) ≈ 32 字符


def _now() -> dt.datetime:
    """当前时间（UTC，可被测试 monkeypatch 冻结）."""
    return dt.datetime.now(dt.timezone.utc)


def _to_utc(value: dt.datetime) -> dt.datetime:
    """SQLite 读回的 DateTime(timezone=True) 为 naive —— 统一补 UTC，保证跨库比较."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def _new_authorization_code() -> str:
    """生成一次性 purge 授权码（明文仅签发响应返回一次）."""
    return secrets.token_urlsafe(_PURGE_CODE_BYTES)


def _code_hash(code: str) -> str:
    """授权码哈希（sha256 hexdigest，服务端不存明文）."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _scope_report_hash(report: dict[str, Any]) -> str:
    """影响范围报告规范哈希（canonical JSON sha256，供确认对账）."""
    canonical = json.dumps(
        report,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# 物理清除的 owner 口径业务表（删除条件：owner 列 == subject_id）
_PURGE_OWNER_SCOPE: tuple[tuple[Any, str], ...] = (
    (Notification, "user_id"),
    (FileRecord, "uploader_id"),
    (AiApp, "created_by"),
    (AiAppCall, "user_id"),
)

# 物理清除的关联绑定表（删除条件：user/agent 列 == subject_id）
_PURGE_BINDING_SCOPE: tuple[tuple[Any, str], ...] = (
    (AgentApiKey, "agent_id"),
    (OidcIdentity, "user_id"),
)


def _table_key(table: Any) -> str:
    """表名（供影响范围报告 dict 键）. """
    return table.__tablename__ if hasattr(table, "__tablename__") else str(table.name)


async def build_scope_report(
    session: AsyncSession, subject: User
) -> dict[str, Any]:
    """生成影响范围报告（将清除的关联数据清单按表计数，audit/阻断/幂等历史不计）.

    audit_logs / subject_blocks / event_consumptions / outbox_events 保留，不入报告；
    tenant 级业务表（dict/config/schedule 等）不按 owner 归属本主体（§9.3 租户级 purge
    属 U2），不在报告内。

    Args:
        session: 数据库会话。
        subject: 待 purge 主体行。

    Returns:
        报告 dict：{subject_id, subject_type, username, tenant_code, tables: {表: 计数},
        total}。
    """
    subject_id = subject.id
    table_counts: dict[str, int] = {}

    binding_counts = await session.execute(
        select(func.count(user_role.c.user_id)).where(user_role.c.user_id == subject_id)
    )
    table_counts["user_role"] = int(binding_counts.scalar() or 0)
    department_counts = await session.execute(
        select(func.count(user_department.c.user_id)).where(
            user_department.c.user_id == subject_id
        )
    )
    table_counts["user_department"] = int(department_counts.scalar() or 0)

    for model, owner_column in _PURGE_BINDING_SCOPE:
        counts = await session.execute(
            select(func.count()).select_from(model).where(
                getattr(model, owner_column) == subject_id
            )
        )
        table_counts[_table_key(model)] = int(counts.scalar() or 0)

    for model, owner_column in _PURGE_OWNER_SCOPE:
        counts = await session.execute(
            select(func.count()).select_from(model).where(
                getattr(model, owner_column) == subject_id
            )
        )
        table_counts[_table_key(model)] = int(counts.scalar() or 0)

    report: dict[str, Any] = {
        "subject_id": subject_id,
        "subject_type": subject.subject_type or SUBJECT_TYPE_USER,
        "username": subject.username,
        "tenant_code": subject.tenant_code,
        "tables": dict(sorted(table_counts.items())),
        "total": sum(table_counts.values()),
    }
    return report


async def purge_record_exists(session: AsyncSession, subject_id: int) -> bool:
    """purge_records 终态台账是否已存在（墓碑判定：该主体曾存在后被 purge）.

    Args:
        session: 数据库会话。
        subject_id: 主体 id。

    Returns:
        存在返回 True。
    """
    result = await session.execute(
        select(PurgeRecord.subject_id).where(PurgeRecord.subject_id == subject_id).limit(1)
    )
    return result.first() is not None


async def _ensure_idempotency_key_scope(
    session: AsyncSession, subject_id: int, idempotency_key: str | None
) -> None:
    """幂等键**跨主体复用**显式校验：命中他人已用键 → 400 ``PARAM_INVALID``.

    purge_records.idempotency_key 带全局唯一约束；对**不同 subject** 复用同一幂等键
    属调用方错误（每个逻辑请求应使用各自生成的键）。若交由 DB 唯一约束兜底，会整体
    回滚事务并误报「并发双触发已 purge」（400 ``BIZ_NOT_PURGEABLE``，语义误导）——
    故在消耗二次授权码之前前置显式校验，给出清晰 400。同 subject 的重复触发（重放）
    在更早的墓碑预检（``_load_purgeable_subject``/``purge_record_exists``）即 400 终态
    拒绝，不会到达本校验；并发双触发仍由 DB 唯一约束兜底收敛（本校验为尽力而为预检）。

    Args:
        session: 数据库会话。
        subject_id: 本次 purge 目标主体 id。
        idempotency_key: 调用方幂等键（None 表示未启用幂等键，直接放行）。

    Raises:
        BaseError: PARAM_INVALID（幂等键已被另一主体使用）。
    """
    if not idempotency_key:
        return
    result = await session.execute(
        select(PurgeRecord.subject_id, PurgeRecord.username).where(
            PurgeRecord.idempotency_key == idempotency_key
        )
    )
    existing = result.first()
    if existing is not None and int(existing[0]) != subject_id:
        raise BaseError(
            ErrorCode.PARAM_INVALID,
            "idempotency_key already used by another subject",
            detail={
                "idempotency_key": idempotency_key,
                "subject_id": subject_id,
                "existing_subject_id": existing[0],
                "existing_username": existing[1],
            },
        )


async def _load_purgeable_subject(
    session: AsyncSession, subject_id: int, subject_type: str
) -> User:
    """主体前置校验：存在且 deactivated（否则 400/404；已 purge 终态拒绝）.

    Raises:
        BaseError: BIZ_NOT_FOUND（未知主体）；BIZ_NOT_PURGEABLE（非 deactivated
            或已 purged 终态重复触发 —— 400 终态拒绝，设计 §9.2）。
    """
    subject = await session.get(User, subject_id)
    if subject is None or subject.is_deleted:
        if await purge_record_exists(session, subject_id):
            raise BaseError(
                ErrorCode.BIZ_NOT_PURGEABLE,
                f"subject already purged: {subject_id}",
                detail={"subject_id": subject_id, "status_state": STATUS_STATE_PURGED},
            )
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"subject not found: {subject_id}")
    if (subject.subject_type or SUBJECT_TYPE_USER) != subject_type:
        raise BaseError(ErrorCode.BIZ_NOT_FOUND, f"subject not found: {subject_type}/{subject_id}")
    if subject.status_state != STATUS_STATE_DEACTIVATED:
        raise BaseError(
            ErrorCode.BIZ_NOT_PURGEABLE,
            f"only deactivated subject is purgeable, got {subject.status_state}",
            detail={
                "subject_id": subject_id,
                "status_state": subject.status_state,
            },
        )
    return subject


async def _consume_authorization(
    session: AsyncSession, subject: User, authorization_code: str
) -> PurgeAuthorization:
    """校验并消费一次性授权码（命中 → consumed；缺失/无效/过期 → 403）.

    Raises:
        BaseError: BIZ_PURGE_AUTH_REQUIRED（无码/错码/已消费/过期）。
    """
    result = await session.execute(
        select(PurgeAuthorization).where(
            PurgeAuthorization.subject_id == subject.id,
            PurgeAuthorization.status == "active",
        )
    )
    active_records = list(result.scalars().all())
    matched = None
    for record in active_records:
        if record.code_hash == _code_hash(authorization_code):
            matched = record
            break
    if matched is None:
        raise BaseError(
            ErrorCode.BIZ_PURGE_AUTH_REQUIRED,
            "purge authorization code missing or invalid",
            detail={"subject_id": subject.id},
        )
    now = _now()
    expires_at = _to_utc(matched.expires_at) if matched.expires_at is not None else None
    if expires_at is None or expires_at < now:
        raise BaseError(
            ErrorCode.BIZ_PURGE_AUTH_REQUIRED,
            "purge authorization code expired",
            detail={"subject_id": subject.id, "expires_at": matched.expires_at.isoformat()},
        )
    matched.status = "consumed"
    matched.consumed_at = now
    await session.flush()
    return matched


async def _delete_subject_data(session: AsyncSession, subject_id: int) -> dict[str, int]:
    """物理清除主体关联数据（agent 密钥/绑定/映射/业务 owner 行），返回删除计数.

    保留 audit_logs / subject_blocks / event_consumptions / outbox_events。
    """
    counts: dict[str, int] = {}

    result = await session.execute(
        delete(user_role).where(user_role.c.user_id == subject_id)
    )
    counts["user_role"] = max(int(result.rowcount or 0), 0)
    result = await session.execute(
        delete(user_department).where(user_department.c.user_id == subject_id)
    )
    counts["user_department"] = max(int(result.rowcount or 0), 0)

    for model, owner_column in _PURGE_BINDING_SCOPE:
        result = await session.execute(
            delete(model).where(getattr(model, owner_column) == subject_id)
        )
        counts[_table_key(model)] = max(int(result.rowcount or 0), 0)

    for model, owner_column in _PURGE_OWNER_SCOPE:
        result = await session.execute(
            delete(model).where(getattr(model, owner_column) == subject_id)
        )
        counts[_table_key(model)] = max(int(result.rowcount or 0), 0)

    return counts


@dataclass
class PurgeAuthorizationIssue:
    """签发结果（授权码明文仅此处返回一次）. """

    subject_id: int
    subject_type: str
    username: str
    tenant_code: str | None
    authorization_code: str
    code_suffix: str
    expires_at: dt.datetime
    scope_report: dict[str, Any]
    scope_report_hash: str
    operator: int | None = None


@dataclass
class PurgeExecution:
    """purge 执行结果（响应/审计组装用）. """

    subject_id: int
    subject_type: str
    username: str
    tenant_code: str | None
    previous_state: str
    status_state: str
    scope_report: dict[str, Any]
    scope_report_hash: str
    authorization_ref: str | None
    operator: int | None = None
    request_id: str | None = None
    audit_log_id: int | None = None
    deleted_counts: dict[str, int] = field(default_factory=dict)


class IdentityPurgeService:
    """L1-2 purge 任务服务（签发授权码 + 显式执行；仅 CLI/受权端点触发）.

    设计草案 §9.2：执行器物理清除主体主行与关联业务数据 → purged 终态（矩阵复用）→
    撤销全部密钥/映射；幂等防并发经 purge_records 唯一约束收敛；全程审计留痕。
    """

    # ---- 二次授权：签发（CLI/服务层调用；短 TTL 单次有效） ----

    @classmethod
    async def issue_authorization(
        cls,
        session: AsyncSession,
        *,
        subject_id: int,
        subject_type: str = SUBJECT_TYPE_USER,
        operator: int | None = None,
        request_id: str | None = None,
        ttl_seconds: int = PURGE_AUTHORIZATION_TTL_SECONDS,
    ) -> PurgeAuthorizationIssue:
        """对 deactivated 主体签发一次性 purge 授权码 + 影响范围报告.

        Args:
            session: 数据库会话（提交由调用方负责）。
            subject_id: 主体 id。
            subject_type: user/agent。
            operator: 签发操作者 id。
            request_id: 请求关联 id。
            ttl_seconds: 授权码有效期（短 TTL；默认 600s）。

        Returns:
            PurgeAuthorizationIssue（authorization_code 明文仅此一次）。

        Raises:
            BaseError: BIZ_NOT_FOUND / BIZ_NOT_PURGEABLE（主体校验失败，
                与执行器同前置校验，保证签发即代表可 purge）。
        """
        request_id = request_id or _new_request_id()
        subject = await _load_purgeable_subject(session, subject_id, subject_type)
        report = await build_scope_report(session, subject)
        report_hash = _scope_report_hash(report)
        code = _new_authorization_code()
        now = _now()
        record = PurgeAuthorization(
            subject_id=subject.id,
            subject_type=subject.subject_type or SUBJECT_TYPE_USER,
            code_hash=_code_hash(code),
            code_suffix=code[-6:],
            status="active",
            expires_at=now + dt.timedelta(seconds=max(ttl_seconds, 1)),
            scope_report=report,
            scope_report_hash=report_hash,
            created_by=operator,
        )
        session.add(record)
        await session.flush()
        # 同主体仅允许一张 active 授权码（新签发自动作废旧码）
        await session.execute(
            update(PurgeAuthorization)
            .where(
                PurgeAuthorization.subject_id == subject.id,
                PurgeAuthorization.status == "active",
                PurgeAuthorization.id != record.id,
            )
            .values(status="consumed", consumed_at=now)
        )
        logger.info(
            "purge authorization issued",
            extra={
                "subject_id": subject.id,
                "subject_type": subject.subject_type,
                "operator": operator,
                "expires_at": record.expires_at.isoformat(),
                "request_id": request_id,
            },
        )
        return PurgeAuthorizationIssue(
            subject_id=subject.id,
            subject_type=subject.subject_type or SUBJECT_TYPE_USER,
            username=subject.username,
            tenant_code=subject.tenant_code,
            authorization_code=code,
            code_suffix=code[-6:],
            expires_at=record.expires_at,
            scope_report=report,
            scope_report_hash=report_hash,
            operator=operator,
        )

    # ---- purge 执行器（显式合规触发；幂等防并发） ----

    @classmethod
    async def execute_purge(
        cls,
        session: AsyncSession,
        *,
        subject_id: int,
        subject_type: str = SUBJECT_TYPE_USER,
        authorization_code: str,
        scope_report_hash: str,
        operator: int | None = None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> PurgeExecution:
        """执行 purge：前置校验 → 授权码二次授权 → 范围确认 → 物理清除 → 审计留痕.

        Args:
            session: 数据库会话（提交由调用方负责；失败整体回滚）。
            subject_id: 主体 id。
            subject_type: user/agent。
            authorization_code: 一次性 purge 授权码。
            scope_report_hash: 影响范围报告确认哈希（与签发时报告一致）。
            operator: 操作者 id。
            request_id: 请求关联 id。
            idempotency_key: 幂等键（可选；purge_records 唯一约束防并发双跑）。

        Returns:
            PurgeExecution（purged=True 的终态执行结果）。

        Raises:
            BaseError: BIZ_NOT_FOUND（未知主体）；BIZ_NOT_PURGEABLE（非 deactivated
                或已 purged 终态重复/并发触发 —— 400 终态拒绝）；BIZ_PURGE_AUTH_REQUIRED
                （授权码缺失/无效/过期或范围报告未确认）。
        """
        request_id = request_id or _new_request_id()
        # ① 主体前置校验：存在 + deactivated（状态机矩阵前的人工语义门禁）
        subject = await _load_purgeable_subject(session, subject_id, subject_type)
        previous_state = subject.status_state

        # ② 状态机矩阵复用：deactivated → purged（非法迁移一律 400，防御性兜底）
        validate_transition(previous_state, STATUS_STATE_PURGED)

        # ②′ 幂等键跨主体复用显式 400（T7 收口；同主体重放由墓碑预检先行拒绝）
        await _ensure_idempotency_key_scope(session, subject_id, idempotency_key)

        # ③ 二次授权：一次性授权码校验并消费（缺失/无效/过期 → 403）
        authorization = await _consume_authorization(session, subject, authorization_code)

        # ④ 影响范围报告确认：当前报告与授权签发时报告一致（确认的即执行的）
        current_report = await build_scope_report(session, subject)
        current_report_hash = _scope_report_hash(current_report)
        if (
            current_report_hash != authorization.scope_report_hash
            or current_report_hash != scope_report_hash
        ):
            raise BaseError(
                ErrorCode.BIZ_PURGE_AUTH_REQUIRED,
                "purge scope report confirmation mismatch; re-issue authorization",
                detail={"subject_id": subject.id},
            )

        # ⑤ 终态台账 + 幂等键唯一约束（并发双触发仅一次执行的收敛点）
        authorization_ref = f"purge_auth#{authorization.id}"
        tombstone = PurgeRecord(
            subject_id=subject.id,
            subject_type=subject.subject_type or SUBJECT_TYPE_USER,
            username=subject.username,
            tenant_id=subject.tenant_id,
            tenant_code=subject.tenant_code,
            previous_state=previous_state,
            status_state=STATUS_STATE_PURGED,
            scope_report_hash=current_report_hash,
            authorization_ref=authorization_ref,
            operator=operator,
            request_id=request_id,
            idempotency_key=idempotency_key,
            purged_at=_now(),
        )
        session.add(tombstone)
        try:
            await session.flush()
        except IntegrityError as exc:
            # 并发另一触发已抢先落终态 → 400 终态拒绝（整体回滚，授权码不消耗）
            await session.rollback()
            raise BaseError(
                ErrorCode.BIZ_NOT_PURGEABLE,
                f"subject already purged by concurrent trigger: {subject_id}",
                detail={"subject_id": subject_id, "status_state": STATUS_STATE_PURGED},
            ) from exc

        # ⑥ 物理清除主体关联数据（audit/阻断/幂等历史保留）
        deleted_counts = await _delete_subject_data(session, subject.id)

        # ⑦ 审计留痕（action=identity.purge，detail 按草案 §9.2 schema）
        audit_log = AuditLog(
            user_id=operator,
            tenant_id=subject.tenant_id,
            action="identity.purge",
            resource="users",
            resource_id=str(subject.id),
            request_id=request_id,
            detail={
                "subject": {
                    "subject_id": subject.id,
                    "subject_type": subject.subject_type or SUBJECT_TYPE_USER,
                    "username": subject.username,
                },
                "tenant_code": subject.tenant_code,
                "scope_report_hash": current_report_hash,
                "scope_report": current_report,
                "authorization_ref": authorization_ref,
                "operator": operator,
                "request_id": request_id,
                "from": previous_state,
                "to": STATUS_STATE_PURGED,
            },
        )
        session.add(audit_log)
        await session.flush()
        audit_log_id = audit_log.id

        # ⑧ 删除主体主行（终态已由 purge_records 承载）
        username = subject.username
        tenant_id = subject.tenant_id
        tenant_code = subject.tenant_code
        subject_type_value = subject.subject_type or SUBJECT_TYPE_USER
        await session.delete(subject)
        await session.flush()

        # ⑨ 清进程/Redis 缓存键（principal:{id} / user:{username}），防止脏缓存放行
        cls._invalidate_caches(subject_id, username)

        logger.info(
            "identity purge executed",
            extra={
                "subject_id": subject_id,
                "subject_type": subject_type_value,
                "tenant_id": tenant_id,
                "tenant_code": tenant_code,
                "from": previous_state,
                "to": STATUS_STATE_PURGED,
                "deleted_counts": deleted_counts,
                "operator": operator,
                "request_id": request_id,
                "audit_log_id": audit_log_id,
            },
        )
        return PurgeExecution(
            subject_id=subject_id,
            subject_type=subject_type_value,
            username=username,
            tenant_code=tenant_code,
            previous_state=previous_state,
            status_state=STATUS_STATE_PURGED,
            scope_report=current_report,
            scope_report_hash=current_report_hash,
            authorization_ref=authorization_ref,
            operator=operator,
            request_id=request_id,
            audit_log_id=audit_log_id,
            deleted_counts=deleted_counts,
        )

    @staticmethod
    def _invalidate_caches(subject_id: int, username: str | None = None) -> None:
        """失效 principal/user 缓存键（与 lifecycle 共用同一失效函数）."""
        from openbase.modules.identity.verification import invalidate_principal_cache

        invalidate_principal_cache(subject_id, username)


__all__ = [
    "PURGE_AUTHORIZATION_TTL_SECONDS",
    "PurgeAuthorizationIssue",
    "PurgeExecution",
    "IdentityPurgeService",
    "build_scope_report",
    "purge_record_exists",
]
