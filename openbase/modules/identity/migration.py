"""U1 T1 幂等增量迁移（W1-4：不重建、create_all + WHERE NOT EXISTS/列存在性检查）.

迁移目标（设计草案 §3.1/§3.4）：
- users 表补 Principal 语义列：subject_type / credential_type / status_state /
  status_reason / token_version / tenant_code / on_behalf_of（既有行主键/FK 不动）；
- 存量行回填：subject_type=user、status_state（status=1→active，0→suspended 保守）、
  token_version=0、tenant_code（tenant_id→tenants.code）、credential_type
  （oidc_identity 映射→oidc，其余→password）；
- 新表（agent_api_keys 等）经 metadata.create_all 幂等创建；
- identity:* 权限点幂等种子（WHERE NOT EXISTS）。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

logger = logging.getLogger("openbase.identity.migration")

# users 需补的列 → (DDL 类型与约束)。NOT NULL 列带常量默认，保证存量行添加即合法；
# status_state 不加默认（可空）以便按存量 status(int) 回填映射（1→active / 0→suspended）。
_USERS_NEW_COLUMNS: dict[str, str] = {
    "subject_type": "VARCHAR(16) NOT NULL DEFAULT 'user'",
    "credential_type": "VARCHAR(16)",
    "status_state": "VARCHAR(24)",
    "status_reason": "VARCHAR(255)",
    "token_version": "INTEGER NOT NULL DEFAULT 0",
    "tenant_code": "VARCHAR(64)",
    "on_behalf_of": "JSON",
}

_IDENTITY_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("identity:view", "主体查看"),
    ("identity:manage", "主体管理"),
    ("identity:lifecycle", "生命周期管理"),
    ("identity:purge", "数据清除"),
)


def _qualify(schema: str | None, table: str) -> str:
    return f'"{schema}".{table}' if schema else table


def _users_columns(sync_conn: Any, schema: str | None) -> set[str]:
    """读取 users 现有列名（缺表返回空集）. """
    from sqlalchemy import inspect

    inspector = inspect(sync_conn)
    if not inspector.has_table("users", schema=schema):
        return set()
    return {col["name"] for col in inspector.get_columns("users", schema=schema)}


async def apply_identity_migration(
    engine: Any, schema: str | None = None
) -> dict[str, Any]:
    """执行幂等增量迁移，返回摘要（可重放，无副作用）.

    Args:
        engine: SQLAlchemy 异步引擎。
        schema: PG 场景目标 schema；SQLite 传 None。

    Returns:
        {"columns_added": [...], "permissions_seeded": int}。
    """
    from openbase.core.models import Base

    summary: dict[str, Any] = {"columns_added": [], "permissions_seeded": 0}
    users_ref = _qualify(schema, "users")
    permissions_ref = _qualify(schema, "permissions")

    async with engine.begin() as conn:
        # 1) 新表/缺失表幂等创建（agent_api_keys 等；users 已存在则跳过）
        if schema is not None:
            await conn.execute(text(f'SET search_path TO "{schema}"'))
        await conn.run_sync(Base.metadata.create_all)
        if schema is not None:
            await conn.execute(text("SET search_path TO public"))

        # 2) users 增量列（W1-4：ALTER ADD COLUMN，已存在则跳过）
        existing = await conn.run_sync(_users_columns, schema)
        for column_name, column_ddl in _USERS_NEW_COLUMNS.items():
            if column_name in existing:
                continue
            await conn.execute(
                text(f"ALTER TABLE {users_ref} ADD COLUMN {column_name} {column_ddl}")
            )
            summary["columns_added"].append(column_name)

        # 3) 存量行回填（幂等：仅补 NULL；主键/FK 不动）
        await conn.execute(
            text(
                f"UPDATE {users_ref} SET subject_type = 'user' "
                "WHERE subject_type IS NULL OR subject_type = ''"
            )
        )
        await conn.execute(
            text(
                f"UPDATE {users_ref} SET status_state = "
                "CASE WHEN status = 1 THEN 'active' ELSE 'suspended' END "
                "WHERE status_state IS NULL"
            )
        )
        await conn.execute(
            text(f"UPDATE {users_ref} SET token_version = 0 WHERE token_version IS NULL")
        )
        await conn.execute(
            text(
                f"UPDATE {users_ref} SET tenant_code = "
                f"(SELECT code FROM {_qualify(schema, 'tenants')} "
                f"WHERE {_qualify(schema, 'tenants')}.id = {users_ref}.tenant_id) "
                "WHERE tenant_code IS NULL AND tenant_id IS NOT NULL"
            )
        )
        await conn.execute(
            text(
                f"UPDATE {users_ref} SET credential_type = 'oidc' "
                "WHERE credential_type IS NULL AND id IN "
                f"(SELECT user_id FROM {_qualify(schema, 'oidc_identity')})"
            )
        )
        await conn.execute(
            text(
                f"UPDATE {users_ref} SET credential_type = 'password' "
                "WHERE credential_type IS NULL"
            )
        )

        # 4) identity:* 权限点种子（幂等 WHERE NOT EXISTS）
        for code, name in _IDENTITY_PERMISSIONS:
            result = await conn.execute(
                text(
                    f"INSERT INTO {permissions_ref} (code, name, module, type, created_at, updated_at) "
                    "SELECT :code, :name, 'identity', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {permissions_ref} WHERE code = :code)"
                ).bindparams(code=code, name=name)
            )
            summary["permissions_seeded"] += max(int(result.rowcount or 0), 0)

    logger.info(
        "identity migration applied",
        extra={"columns_added": summary["columns_added"], "permissions_seeded": summary["permissions_seeded"]},
    )
    return summary
