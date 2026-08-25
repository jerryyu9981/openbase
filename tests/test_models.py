"""数据模型建表与字段测试."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from openbase.core.models import (
    AuditLog,
    Base,
    Tenant,
    User,
)


@pytest.mark.asyncio
async def test_create_all_tables():
    """验证 5 个核心模型可建表（SQLite 内存库）."""
    # 重置全局 schema（避免 openbase schema 前缀污染 SQLite 建表）
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def test_user_model_fields():
    """验证 User 模型关键字段存在."""
    cols = User.__table__.columns
    for name in ("id", "username", "password_hash", "display_name", "status", "tenant_id", "is_deleted"):
        assert name in cols


def test_tenant_model_fields():
    cols = Tenant.__table__.columns
    for name in ("id", "name", "code", "status", "isolation_level"):
        assert name in cols


def test_audit_log_model_fields():
    cols = AuditLog.__table__.columns
    for name in ("id", "action", "resource", "request_id", "created_at"):
        assert name in cols


def test_role_permission_relationships():
    """验证 RBAC 关联表与关系."""
    assert "user_role" in Base.metadata.tables
    assert "role_permission" in Base.metadata.tables
    assert "users" in Base.metadata.tables
    assert "roles" in Base.metadata.tables
    assert "permissions" in Base.metadata.tables
    assert "tenants" in Base.metadata.tables
    assert "audit_logs" in Base.metadata.tables
