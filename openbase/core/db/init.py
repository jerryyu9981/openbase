"""数据库初始化：schema 创建 + 建表 + 基础种子数据."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("openbase.db")


async def ensure_schema(engine: AsyncEngine, schema: str = "openbase") -> None:
    """确保 openbase schema 存在（共享库内隔离，不污染 public）.

    Args:
        engine: 异步引擎。
        schema: schema 名（默认 openbase）。
    """
    async with engine.begin() as conn:
        await conn.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        )
    logger.info("schema ensured", extra={"schema": schema})


async def create_tables(
    engine: AsyncEngine,
    schema: str = "openbase",
    metadata: Any = None,
) -> None:
    """在指定 schema 中创建全部表.

    Args:
        engine: 异步引擎。
        schema: schema 名。
        metadata: SQLAlchemy MetaData（默认使用 core.models.Base.metadata）。
    """
    from openbase.core.models import Base

    metadata = metadata or Base.metadata
    await ensure_schema(engine, schema)

    # 设置 search_path 后建表（使表落在 openbase schema 内）
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        await conn.run_sync(metadata.create_all)
        await conn.execute(text("SET search_path TO public"))
    logger.info("tables created", extra={"schema": schema})


async def init_database(engine: AsyncEngine, schema: str = "openbase") -> None:
    """初始化数据库（建 schema + 建表 + 基础种子数据）.

    Args:
        engine: 异步引擎。
        schema: schema 名。
    """
    await create_tables(engine, schema)

    # 基础种子数据：内置管理员角色与权限（幂等，SQL 显式带 schema 前缀）
    async with engine.begin() as conn:
        await conn.execute(
            text(
                f"INSERT INTO {schema}.roles "
                "(id, name, code, description, is_system, created_at, updated_at) "
                "SELECT 1, '系统管理员', 'admin', '内置管理员角色', true, now(), now() "
                f"WHERE NOT EXISTS (SELECT 1 FROM {schema}.roles WHERE code = 'admin')"
            )
        )
        # 全部权限通配
        await conn.execute(
            text(
                f"INSERT INTO {schema}.permissions "
                "(id, code, name, module, type, created_at, updated_at) "
                "SELECT 1, '*', '全部权限', 'system', 3, now(), now() "
                f"WHERE NOT EXISTS (SELECT 1 FROM {schema}.permissions WHERE code = '*')"
            )
        )
    logger.info("database initialized", extra={"schema": schema})
