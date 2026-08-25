"""core/db/init.py 初始化逻辑测试（覆盖率补充：NFR-006 ≥85%）.

通过捕获执行的 SQL 验证 schema 建表与种子数据逻辑（不依赖真实 PG）。
"""


def test_ensure_schema_sql(monkeypatch):
    """ensure_schema 生成 CREATE SCHEMA IF NOT EXISTS 语句."""
    from openbase.core.db import init as db_init

    captured = []

    class FakeConn:
        async def execute(self, stmt):
            captured.append(str(stmt))

    class FakeEngine:
        def begin(self):
            return _FakeCtx(FakeConn())

    class _FakeCtx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *a):
            return False

    import asyncio

    asyncio.run(db_init.ensure_schema(FakeEngine(), "openbase"))
    assert any("CREATE SCHEMA IF NOT EXISTS" in s and '"openbase"' in s for s in captured)


def test_init_database_seed_sql(monkeypatch):
    """init_database 种子 SQL 带 schema 前缀且幂等（WHERE NOT EXISTS）."""
    from openbase.core.db import init as db_init

    captured = []

    class FakeConn:
        async def execute(self, stmt):
            captured.append(str(stmt))

    class FakeEngine:
        def begin(self):
            return _Ctx(FakeConn())

    class _Ctx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *a):
            return False

    import asyncio

    async def fake_create_tables(engine, schema="openbase", metadata=None):
        captured.append("create_tables")

    monkeypatch.setattr(db_init, "create_tables", fake_create_tables)

    asyncio.run(db_init.init_database(FakeEngine(), "openbase"))
    sql_all = "\n".join(captured)
    # 角色种子：显式 schema 前缀 + 幂等
    assert "openbase.roles" in sql_all
    assert "WHERE NOT EXISTS (SELECT 1 FROM openbase.roles WHERE code = 'admin')" in sql_all
    # 权限种子：显式 schema 前缀 + 通配权限
    assert "openbase.permissions" in sql_all
    assert "WHERE NOT EXISTS (SELECT 1 FROM openbase.permissions WHERE code = '*')" in sql_all
