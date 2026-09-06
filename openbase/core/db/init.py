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
        # OB-AUTH-OIDC（v1.3.0）：基础业务角色，供 OIDC claims roles 映射与常规授权
        for _code, _name, _desc in (
            ("viewer", "只读用户", "只读访问角色"),
            ("user", "普通用户", "标准业务用户角色"),
            ("org_admin", "组织管理员", "组织级管理角色"),
        ):
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.roles (name, code, description, is_system, created_at, updated_at) "
                    "SELECT :name, :code, :desc, true, now(), now() "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {schema}.roles WHERE code = :code)"
                ).bindparams(name=_name, code=_code, desc=_desc)
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
        # admin 用户 → admin 角色关联（RBAC 矩阵；依赖 admin 用户已由 demo_app 种子）
        await conn.execute(
            text(
                f"INSERT INTO {schema}.user_role (user_id, role_id) "
                f"SELECT u.id, r.id FROM {schema}.users u, {schema}.roles r "
                f"WHERE u.username = 'admin' AND r.code = 'admin' "
                f"AND NOT EXISTS (SELECT 1 FROM {schema}.user_role ur "
                f"WHERE ur.user_id = u.id AND ur.role_id = r.id)"
            )
        )
        # admin 角色 → 全部权限关联
        await conn.execute(
            text(
                f"INSERT INTO {schema}.role_permission (role_id, permission_id) "
                f"SELECT r.id, p.id FROM {schema}.roles r, {schema}.permissions p "
                f"WHERE r.code = 'admin' AND p.code = '*' "
                f"AND NOT EXISTS (SELECT 1 FROM {schema}.role_permission rp "
                f"WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
            )
        )
        # v1.4.6+（统一前端模块查看权限点种子）：openllm/openrag/openmemory/dps/gateway。
        # 根因修复（走查发现 ①/网关权限缺失）：此前仅 admin 角色拥有 '*' 通配，
        # OIDC/本地非 admin 用户（含 org_admin）经 user→role→permission 链查询为空
        # → 前端模块不可见；gateway 域（gateway:view 等）亦未种入 DB 权限矩阵。
        # 注：历史版本显式插入 id=1（'*'）未推进 PG 自增序列，后续无 id 插入会撞主键，
        # 故先同步 permissions/roles 序列（幂等）。
        for _table in ("permissions", "roles"):
            await conn.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('\"{schema}\".{_table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM \"{schema}\".{_table}), 1))"
                )
            )
        for _code, _name, _module in (
            ("openllm:view", "OpenLLM 查看", "openllm"),
            ("openrag:view", "知识库查看", "openrag"),
            ("openmemory:view", "记忆查看", "openmemory"),
            ("dps:view", "画像查看", "dps"),
            ("gateway:view", "统一网关查看", "gateway"),
        ):
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.permissions "
                    "(code, name, module, type, created_at, updated_at) "
                    "SELECT :code, :name, :module, 1, now(), now() "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {schema}.permissions WHERE code = :code)"
                ).bindparams(code=_code, name=_name, module=_module)
            )
        # 业务角色（org_admin/user/viewer）→ 模块查看权限（admin 持 * 通配）。
        # 映射与架构文档模块矩阵一致：各角色可浏览统一前端全部模块，深层写操作
        # 仍由各自 *_manage/*:write 权限点管控（如 auth:api-keys:manage）。
        for _role_code in ("org_admin", "user", "viewer"):
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.role_permission (role_id, permission_id) "
                    f"SELECT r.id, p.id FROM {schema}.roles r, {schema}.permissions p "
                    f"WHERE r.code = :role AND p.code IN "
                    "('openllm:view','openrag:view','openmemory:view','dps:view','gateway:view') "
                    f"AND NOT EXISTS (SELECT 1 FROM {schema}.role_permission rp "
                    f"WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
                ).bindparams(role=_role_code)
            )
        # 服务密钥权限点种子（v1.4.6+，网关/API 控制台页走查修复）：
        # auth:api-keys:* 行入库供 RBAC 分配；org_admin 获得查看+管理（组织接入需签发
        # 下游服务密钥）；user/viewer 不授（仅浏览模块，密钥属平台级写操作）。
        for _code, _name, _module in (
            ("auth:api-keys:view", "服务密钥查看", "auth"),
            ("auth:api-keys:manage", "服务密钥管理", "auth"),
        ):
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.permissions "
                    "(code, name, module, type, created_at, updated_at) "
                    "SELECT :code, :name, :module, 1, now(), now() "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {schema}.permissions WHERE code = :code)"
                ).bindparams(code=_code, name=_name, module=_module)
            )
        await conn.execute(
            text(
                f"INSERT INTO {schema}.role_permission (role_id, permission_id) "
                f"SELECT r.id, p.id FROM {schema}.roles r, {schema}.permissions p "
                f"WHERE r.code = 'org_admin' AND p.code IN "
                "('auth:api-keys:view','auth:api-keys:manage') "
                f"AND NOT EXISTS (SELECT 1 FROM {schema}.role_permission rp "
                f"WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
            )
        )
        # U1 统一身份收口（RA-01/OB-1）：identity 面权限点种子（幂等）。
        # 仅登记权限行；分配面：admin 持 '*' 通配，其余角色由 identity/lifecycle 授权显式分配。
        for _code, _name in (
            ("identity:view", "主体查看"),
            ("identity:manage", "主体管理"),
            ("identity:lifecycle", "生命周期管理"),
            ("identity:purge", "数据清除"),
        ):
            await conn.execute(
                text(
                    f"INSERT INTO {schema}.permissions "
                    "(code, name, module, type, created_at, updated_at) "
                    "SELECT :code, :name, 'identity', 1, now(), now() "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {schema}.permissions WHERE code = :code)"
                ).bindparams(code=_code, name=_name)
            )
    logger.info("database initialized", extra={"schema": schema})
