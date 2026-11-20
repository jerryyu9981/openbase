"""AI 标注候选持久化存储（v1.5.0 A14）.

候选由 DPS 生成并强制 pending；本模块只负责把候选批次落到 OpenBase 库，
使前端刷新后可按 ``batch_id`` / 最近批次恢复。**不记录** fields_json 原文到日志。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError

from openbase.core.db.session import get_session_factory
from openbase.core.models import Base

logger = logging.getLogger(__name__)

_TABLE_READY = False


async def _ensure_table(session) -> None:
    """幂等建表（应用初始化早于模块导入时兜底；``checkfirst`` 保证可重复执行）."""
    global _TABLE_READY
    if _TABLE_READY:
        return
    await session.run_sync(
        lambda sync_session: DpsAnnotationCandidate.__table__.create(
            bind=sync_session.get_bind(), checkfirst=True
        )
    )
    _TABLE_READY = True


class DpsAnnotationCandidate(Base):
    """AI 标注候选（按批次持久化；租户隔离）."""

    __tablename__ = "dps_annotation_candidate"

    id = Column(String(36), primary_key=True)
    batch_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    operator = Column(String(128), nullable=False, default="")
    adapter_id = Column(String(128), nullable=False)
    annotation_template = Column(String(128), nullable=False, default="")
    upstream_annotation_id = Column(String(64), nullable=False)
    review_status = Column(String(32), nullable=False, default="pending")
    person_id = Column(String(64), nullable=True)
    profile_id = Column(String(64), nullable=True)
    fields_json = Column(Text, nullable=False, default="{}")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "upstream_annotation_id",
            name="uq_dps_candidate_tenant_upstream",
        ),
    )


def _serialize(row: DpsAnnotationCandidate) -> dict[str, Any]:
    """行对象 → 响应字典（fields 解码为对象）."""
    try:
        fields = json.loads(row.fields_json or "{}")
    except (TypeError, ValueError):
        fields = {}
    return {
        "id": row.id,
        "batch_id": row.batch_id,
        "adapter_id": row.adapter_id,
        "annotation_template": row.annotation_template,
        "upstream_annotation_id": row.upstream_annotation_id,
        "review_status": row.review_status,
        "person_id": row.person_id,
        "profile_id": row.profile_id,
        "fields": fields,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


async def save_candidate(
    *,
    tenant_id: str,
    operator: str,
    adapter_id: str,
    annotation_template: str,
    upstream_annotation_id: str,
    review_status: str,
    fields: dict[str, Any],
    person_id: str | None = None,
    profile_id: str | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """幂等保存候选；同租户同 upstream_annotation_id 返回既有记录."""
    session_factory = get_session_factory()
    resolved_batch_id = batch_id or str(uuid.uuid4())
    async with session_factory() as session:
        await _ensure_table(session)
        existing = await session.scalar(
            select(DpsAnnotationCandidate).where(
                DpsAnnotationCandidate.tenant_id == tenant_id,
                DpsAnnotationCandidate.upstream_annotation_id == upstream_annotation_id,
            )
        )
        if existing is not None:
            return _serialize(existing)

        row = DpsAnnotationCandidate(
            id=str(uuid.uuid4()),
            batch_id=resolved_batch_id,
            tenant_id=tenant_id,
            operator=operator,
            adapter_id=adapter_id,
            annotation_template=annotation_template,
            upstream_annotation_id=upstream_annotation_id,
            review_status=review_status,
            person_id=person_id,
            profile_id=profile_id,
            fields_json=json.dumps(fields, ensure_ascii=False),
        )
        session.add(row)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await session.scalar(
                select(DpsAnnotationCandidate).where(
                    DpsAnnotationCandidate.tenant_id == tenant_id,
                    DpsAnnotationCandidate.upstream_annotation_id == upstream_annotation_id,
                )
            )
            if existing is None:
                raise
            return _serialize(existing)
        await session.refresh(row)
        logger.info(
            "dps candidate persisted",
            extra={
                "batch_id": resolved_batch_id,
                "adapter_id": adapter_id,
                "annotation_template": annotation_template,
                "tenant_id": tenant_id,
            },
        )
        return _serialize(row)


async def list_by_batch(tenant_id: str, batch_id: str) -> list[dict[str, Any]]:
    """按批次查询（租户隔离，创建时间升序）."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await _ensure_table(session)
        rows = (
            await session.scalars(
                select(DpsAnnotationCandidate)
                .where(
                    DpsAnnotationCandidate.tenant_id == tenant_id,
                    DpsAnnotationCandidate.batch_id == batch_id,
                )
                .order_by(DpsAnnotationCandidate.created_at.asc())
            )
        ).all()
        return [_serialize(row) for row in rows]


async def latest_batch(
    tenant_id: str,
    adapter_id: str | None = None,
    annotation_template: str | None = None,
) -> tuple[str | None, list[dict[str, Any]]]:
    """最近批次（可叠加 adapter / 模板过滤）."""
    session_factory = get_session_factory()
    conditions = [DpsAnnotationCandidate.tenant_id == tenant_id]
    if adapter_id:
        conditions.append(DpsAnnotationCandidate.adapter_id == adapter_id)
    if annotation_template:
        conditions.append(
            DpsAnnotationCandidate.annotation_template == annotation_template
        )
    async with session_factory() as session:
        await _ensure_table(session)
        latest = await session.scalar(
            select(DpsAnnotationCandidate)
            .where(*conditions)
            .order_by(DpsAnnotationCandidate.created_at.desc())
            .limit(1)
        )
        if latest is None:
            return None, []
        rows = (
            await session.scalars(
                select(DpsAnnotationCandidate)
                .where(
                    DpsAnnotationCandidate.tenant_id == tenant_id,
                    DpsAnnotationCandidate.batch_id == latest.batch_id,
                )
                .order_by(DpsAnnotationCandidate.created_at.asc())
            )
        ).all()
        return latest.batch_id, [_serialize(row) for row in rows]
