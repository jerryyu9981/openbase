"""审计日志链式哈希（E2 防篡改）：统一写入监听器 + 链式校验.

设计要点：
- **不逐处改插入点**：全仓 ``AuditLog(...)`` 插入点有 17 处，链式计算改为在
  ``Session`` 的 ``before_flush`` 事件里统一完成（本模块导入即注册监听器，
  由 ``openbase.core.models`` 末尾导入触发，覆盖所有写入路径）。
- ``prev_hash`` 取「同批次上一条新记录的 entry_hash」；批次首条取数据库中 id 最大的
  已落库记录的 ``entry_hash``（空表 → ``None``，即链起点）。
- ``entry_hash = sha256(f"{prev_hash or ''}|{canonical_payload}")``：业务字段被改 →
  该行重算值不等（断点可定位）；中间行被删 → 后继行 ``prev_hash`` 与前一已哈希行
  ``entry_hash`` 不匹配。
- 存量库兼容：启用前写入的历史行两列为 NULL（链前遗留），校验时跳过。

并发控制（v1.10.0 闭合）：链式计算是「先读末条哈希、再插入」的读后写语义，多实例
并发写入时可能读到同一末条哈希而形成链分叉（fork）。为此在 flush 前对写入会话加
PostgreSQL **事务级** advisory lock（``pg_advisory_xact_lock``，随事务提交/回滚自动
释放），使「读末条哈希 + 插入」在同一把锁下串行，多实例/多进程写入仍保持单链。
非 PostgreSQL 方言（SQLite 为单写者模型）不取锁，直接放行。

存量库 DDL（本仓无 alembic 目录，升级时手工执行一次，历史行 entry_hash 为 NULL
不参与校验）：
    ALTER TABLE openbase.audit_logs ADD COLUMN IF NOT EXISTS prev_hash varchar(64);
    ALTER TABLE openbase.audit_logs ADD COLUMN IF NOT EXISTS entry_hash varchar(64);
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
from typing import Any

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from openbase.core.models.base import AuditLog

logger = logging.getLogger("openbase.audit.chain")

# 链校验分批大小（流式遍历，避免一次载入全表）
VERIFY_BATCH_SIZE = 200

# 链写入串行化锁键（PostgreSQL advisory lock，全实例取同一常量值；"AUDI" 助记）
AUDIT_CHAIN_LOCK_KEY = 0x41554449

# 参与哈希的稳定字段（顺序固定；JSON 亦按 sort_keys 序列化，双重保证可复现）
STABLE_FIELD_NAMES: tuple[str, ...] = (
    "id",
    "tenant_id",
    "user_id",
    "action",
    "resource",
    "resource_id",
    "ip",
    "user_agent",
    "request_id",
    "detail",
    "created_at",
)

__all__ = [
    "AUDIT_CHAIN_LOCK_KEY",
    "STABLE_FIELD_NAMES",
    "VERIFY_BATCH_SIZE",
    "canonical_payload",
    "compute_entry_hash",
    "verify_audit_chain",
]


def _utc_isoformat(value: dt.datetime) -> str:
    """datetime → UTC ISO8601 字符串（naive 视为 UTC）.

    SQLite 的 ``DateTime`` 不带时区，读回为 naive（实际存的是 UTC），
    统一按 UTC 归一，保证「写入侧 aware」与「校验侧 naive」产出同一字符串。
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    else:
        value = value.astimezone(dt.timezone.utc)
    return value.isoformat()


def canonical_payload(record: AuditLog) -> str:
    """把审计行的稳定字段序列化为规范化 JSON（哈希输入）.

    规范化口径：字段固定顺序 + ``sort_keys`` + 紧凑分隔符 + ``ensure_ascii=False``，
    保证同一内容在任何进程/任何时刻序列化结果一致。

    说明：``id`` 固定为空串——自增主键由数据库在 INSERT 时分配，写入前不可知
    （``None``），校验侧重算必然拿到具体 id，两侧取值不同会导致链必然断裂；
    行序完整性由 ``prev_hash`` 链承担（改/删行均会破坏链）。

    Args:
        record: 审计行（可处于未 flush 状态，缺 ``created_at`` 时按当前 UTC 补齐）。

    Returns:
        规范化 JSON 字符串。
    """
    created_at = record.created_at or dt.datetime.now(dt.timezone.utc)
    payload = {
        "id": "",
        "tenant_id": record.tenant_id,
        "user_id": record.user_id,
        "action": record.action,
        "resource": record.resource,
        "resource_id": record.resource_id,
        "ip": record.ip,
        "user_agent": record.user_agent,
        "request_id": record.request_id,
        "detail": record.detail,
        "created_at": _utc_isoformat(created_at),
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def compute_entry_hash(prev_hash: str | None, payload: str) -> str:
    """计算链式哈希：``sha256(f"{prev_hash or ''}|{payload}")``.

    Args:
        prev_hash: 上一条已哈希行的 ``entry_hash``（链起点为 None）。
        payload: ``canonical_payload`` 产出的规范化 JSON。

    Returns:
        64 位十六进制摘要。
    """
    material = f"{prev_hash or ''}|{payload}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _acquire_write_lock(session: Session) -> bool:
    """取链写入串行化锁（PostgreSQL 事务级 advisory lock）.

    「读末条哈希 + 插入新行」必须在同一把锁内完成，否则多实例并发写入会读到
    同一末条哈希而形成链分叉。``pg_advisory_xact_lock`` 随事务结束（commit /
    rollback）自动释放，无需显式解锁，也不会跨请求泄漏。

    非 PostgreSQL 方言（SQLite 单写者模型）不取锁，返回 ``False``。

    Args:
        session: 当前 flush 所在会话。

    Returns:
        是否实际取锁（PostgreSQL 为 True）。
    """
    bind = session.get_bind()
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect_name != "postgresql":
        return False
    # 参数化绑定锁键，不拼接 SQL
    with session.no_autoflush:
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": AUDIT_CHAIN_LOCK_KEY},
        )
    return True


def _latest_entry_hash(session: Session) -> str | None:
    """查询数据库中 id 最大的已落库记录的 ``entry_hash``.

    参数化查询（``select`` + ``order_by`` + ``limit``），不拼接 SQL。
    """
    statement = select(AuditLog.entry_hash).order_by(AuditLog.id.desc()).limit(1)
    # before_flush 内执行 SELECT 必须禁用 autoflush，否则会触发递归 flush
    with session.no_autoflush:
        row = session.execute(statement).first()
    return row[0] if row is not None else None


@event.listens_for(Session, "before_flush")
def _assign_chain_hashes(
    session: Session,
    _flush_context: Any,
    _instances: Any,
) -> None:
    """flush 前统一为新增审计行计算 ``prev_hash`` / ``entry_hash``.

    按 ``session.new`` 的插入顺序逐条链接；批次首条接续库中末条哈希。
    已带 ``entry_hash`` 的行（幂等重放/人工导入）不重算，仅作为后续行的链头。

    取锁顺序固定为「先取串行化锁、再读末条哈希」，保证多实例下读后写不被插入。
    """
    pending = [obj for obj in session.new if isinstance(obj, AuditLog)]
    if not pending:
        return

    if _acquire_write_lock(session):
        logger.debug(
            "audit chain write serialized",
            extra={"pending_records": len(pending)},
        )
    previous_hash = _latest_entry_hash(session)
    for record in pending:
        if record.entry_hash is not None:
            previous_hash = record.entry_hash
            continue
        if record.created_at is None:
            record.created_at = dt.datetime.now(dt.timezone.utc)
        record.prev_hash = previous_hash
        record.entry_hash = compute_entry_hash(previous_hash, canonical_payload(record))
        previous_hash = record.entry_hash


def _broken_result(audit_id: int, checked: int, reason: str) -> dict:
    """构造校验失败结果（``checked`` 含断点行本身）."""
    return {
        "ok": False,
        "checked": checked,
        "first_broken_id": audit_id,
        "reason": reason,
    }


async def verify_audit_chain(
    session: AsyncSession,
    limit: int | None = None,
) -> dict:
    """校验审计链完整性（只读：不修改数据、不触发 flush）.

    按 id 升序流式遍历（``yield_per`` 分批），跳过 ``entry_hash`` 为 NULL 的
    遗留行；对每条已哈希行重算 ``entry_hash`` 并校验与前一已哈希行的链接。

    Args:
        session: 异步会话（只读使用）。
        limit: 最多校验条数（None = 不限）。

    Returns:
        ``{"ok", "checked", "first_broken_id", "reason"}``；
        首条已哈希行的 ``prev_hash`` 允许为 None（链起点）。
    """
    statement = (
        select(AuditLog)
        .where(AuditLog.entry_hash.is_not(None))
        .order_by(AuditLog.id.asc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    statement = statement.execution_options(yield_per=VERIFY_BATCH_SIZE)

    checked = 0
    previous_entry_hash: str | None = None
    # 只读语义：显式关闭 autoflush，避免校验调用顺带把调用方未提交的变更落库
    with session.no_autoflush:
        result = await session.stream(statement)
        async for record in result.scalars():
            expected_hash = compute_entry_hash(
                record.prev_hash, canonical_payload(record)
            )
            if expected_hash != record.entry_hash:
                logger.warning(
                    "audit chain entry hash mismatch",
                    extra={"audit_id": record.id, "reason": "entry_hash_mismatch"},
                )
                return _broken_result(record.id, checked + 1, "entry_hash_mismatch")
            if previous_entry_hash is not None and record.prev_hash != previous_entry_hash:
                logger.warning(
                    "audit chain prev hash not linked",
                    extra={"audit_id": record.id, "reason": "prev_hash_mismatch"},
                )
                return _broken_result(record.id, checked + 1, "prev_hash_mismatch")
            previous_entry_hash = record.entry_hash
            checked += 1

    return {
        "ok": True,
        "checked": checked,
        "first_broken_id": None,
        "reason": None,
    }
