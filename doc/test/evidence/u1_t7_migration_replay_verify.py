"""U1 T7-5 迁移幂等重放验证证据脚本（生产库形态样本）.

对应《OpenBase-U1-统一身份收口-测试报告》v1.0.0 §7 与
《OpenBase-U1-统一身份收口-DevLogReport》v1.0.0 §5。

构造存量库形态（users 无 U1 新列 + tenants + oidc_identity 迁移前表），灌入
多租户/多用户（含禁用、OIDC 绑定、无租户行）样本后，将 identity migration
（openbase.modules.identity.migration.apply_identity_migration）连续执行两次并断言：
- 第一次补齐 7 个 U1 新列并回填正确（status=1→active / 0→suspended 保守、
  credential_type=password|oidc、tenant_code join tenants、token_version=0）；
- 第二次 columns_added=[] 且 permissions_seeded=0（幂等，无副作用）；
- 行数/内容/既有 id 与 FK 不迁移；agent_api_keys 等新表幂等存在。

运行：python doc/test/evidence/u1_t7_migration_replay_verify.py
（仅依赖 openbase 包与本机临时库，不连外部服务。）
"""
from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import text

from openbase.core.db.session import get_engine, init_db

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_u1_t7_migration_replay.db"

_LEGACY_USERS_DDL = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(128), phone VARCHAR(32),
    status INTEGER NOT NULL DEFAULT 1,
    tenant_id INTEGER,
    is_deleted BOOLEAN NOT NULL DEFAULT 0, deleted_at DATETIME,
    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
);"""

_LEGACY_TENANTS_DDL = """
CREATE TABLE tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL UNIQUE, code VARCHAR(64) NOT NULL UNIQUE,
    status INTEGER NOT NULL DEFAULT 1, isolation_level INTEGER NOT NULL DEFAULT 1,
    quota JSON, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
);"""

_LEGACY_OIDC_IDENTITY_DDL = """
CREATE TABLE oidc_identity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    sub VARCHAR(128) NOT NULL,
    issuer VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
    UNIQUE (issuer, sub),
    FOREIGN KEY (user_id) REFERENCES users (id)
);"""


def _build_legacy_sample_db() -> None:
    """构造「生产库样本」：迁移前形态 + 3 租户 + 6 用户（含禁用/OIDC 绑定/无租户）. """
    if _DB_PATH.exists():
        _DB_PATH.unlink()

    async def _setup() -> None:
        init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text(_LEGACY_USERS_DDL))
            await conn.execute(text(_LEGACY_TENANTS_DDL))
            await conn.execute(text(_LEGACY_OIDC_IDENTITY_DDL))
            await conn.execute(
                text(
                    "INSERT INTO tenants (id, name, code, status, isolation_level, created_at, updated_at) VALUES "
                    "(1, 'Acme', 'acme', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(2, 'Globex', 'globex', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(3, 'Initech', 'initech', 0, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO users (id, username, password_hash, display_name, email, status, tenant_id, is_deleted, created_at, updated_at) VALUES "
                    "(1, 'legacy-alice', 'x', '存量启用A', NULL, 1, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(2, 'legacy-bob', 'x', '存量启用B', NULL, 1, 2, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(3, 'legacy-carol', 'x', '存量禁用C', NULL, 0, 3, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(4, 'legacy-oidc-dave', 'x', 'OIDC 绑定D', NULL, 1, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(5, 'legacy-orphan', 'x', '无租户E', NULL, 1, NULL, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),"
                    "(6, 'legacy-disabled-f', 'x', '存量禁用F', NULL, 0, NULL, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO oidc_identity (id, user_id, sub, issuer, created_at, updated_at) VALUES "
                    "(1, 4, 'idp-sub-123', 'https://idp.example', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
        await engine.dispose()

    asyncio.run(_setup())


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH)


def _verify_invariants() -> dict:
    """迁移后数据不变量核对：新列存在、回填正确、无重复行、FK 未迁移."""
    conn = _conn()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        expected_cols = {
            "subject_type", "credential_type", "status_state", "status_reason",
            "token_version", "tenant_code", "on_behalf_of",
        }
        assert expected_cols <= cols, f"missing columns: {expected_cols - cols}"
        row_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert row_count == 6, f"users 行数不应变化: {row_count}"
        assert conn.execute("SELECT COUNT(*) FROM oidc_identity").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0] == 3
        rows = conn.execute(
            "SELECT username, subject_type, credential_type, status_state, "
            "token_version, tenant_code FROM users ORDER BY id"
        ).fetchall()
        expected = {
            "legacy-alice": ("user", "password", "active", 0, "acme"),
            "legacy-bob": ("user", "password", "active", 0, "globex"),
            "legacy-carol": ("user", "password", "suspended", 0, "initech"),
            "legacy-oidc-dave": ("user", "oidc", "active", 0, "acme"),
            "legacy-orphan": ("user", "password", "active", 0, None),
            "legacy-disabled-f": ("user", "password", "suspended", 0, None),
        }
        actual = {r[0]: tuple(r[1:]) for r in rows}
        assert actual == expected, f"回填不一致:\n{actual}"
        perm_counts = conn.execute(
            "SELECT code, COUNT(*) FROM permissions WHERE code LIKE 'identity:%' GROUP BY code"
        ).fetchall()
        assert all(c == 1 for _, c in perm_counts), f"权限种子重复: {perm_counts}"
        assert conn.execute("SELECT COUNT(*) FROM agent_api_keys").fetchone()[0] == 0
        return {"users": row_count, "identity_permission_codes": len(perm_counts)}
    finally:
        conn.close()


async def _replay() -> dict:
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)
    engine = get_engine()
    from openbase.modules.identity.migration import apply_identity_migration

    try:
        first = await apply_identity_migration(engine, schema=None)
        second = await apply_identity_migration(engine, schema=None)
        return {"first": first, "second": second}
    finally:
        await engine.dispose()


def main() -> int:
    _build_legacy_sample_db()
    result = asyncio.run(_replay())
    print("first pass :", result["first"])
    print("second pass:", result["second"])
    assert result["first"]["columns_added"] == [
        "subject_type", "credential_type", "status_state", "status_reason",
        "token_version", "tenant_code", "on_behalf_of",
    ], result["first"]
    assert result["first"]["permissions_seeded"] == 4, result["first"]
    assert result["second"]["columns_added"] == [], result["second"]
    assert result["second"]["permissions_seeded"] == 0, result["second"]
    summary = _verify_invariants()
    print(f"invariants OK: {summary}")
    print("REPLAY_VERIFY_OK: 重放无副作用（生产库样本，连续两次执行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
