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

    async def fake_apply_identity_migration(engine, schema=None):
        # 本用例只校验种子 SQL；身份迁移由 test_init_database_applies_identity_migration 覆盖
        captured.append("apply_identity_migration")
        return {"columns_added": [], "permissions_seeded": 0}

    monkeypatch.setattr(db_init, "create_tables", fake_create_tables)
    monkeypatch.setattr(
        "openbase.modules.identity.migration.apply_identity_migration",
        fake_apply_identity_migration,
    )

    asyncio.run(db_init.init_database(FakeEngine(), "openbase"))
    sql_all = "\n".join(captured)
    # 角色种子：显式 schema 前缀 + 幂等
    assert "openbase.roles" in sql_all
    assert "WHERE NOT EXISTS (SELECT 1 FROM openbase.roles WHERE code = 'admin')" in sql_all
    # 权限种子：显式 schema 前缀 + 通配权限
    assert "openbase.permissions" in sql_all
    assert "WHERE NOT EXISTS (SELECT 1 FROM openbase.permissions WHERE code = '*')" in sql_all


def test_init_database_applies_identity_migration(monkeypatch):
    """init_database 末尾必须内联 U1 身份幂等迁移（根治初始化链漏迁移漂移）.

    根因：init_database 此前只做 create_all + 种子，U1 身份增量迁移
    （users 7 列 / agent_api_keys / identity:* 权限点）需另行调用，
    导致经本初始化链建库/初始化的库漏迁移（U1-T7 漂移）。
    """
    from openbase.core.db import init as db_init

    order = []
    calls = []

    class FakeConn:
        async def execute(self, stmt):
            order.append("seed_sql")

    class _Ctx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *a):
            return False

    class FakeEngine:
        def begin(self):
            return _Ctx(FakeConn())

    async def fake_create_tables(engine, schema="openbase", metadata=None):
        order.append("create_tables")

    async def fake_apply_identity_migration(engine, schema=None):
        calls.append({"engine": engine, "schema": schema})
        order.append("apply_identity_migration")
        return {"columns_added": [], "permissions_seeded": 0}

    monkeypatch.setattr(db_init, "create_tables", fake_create_tables)
    monkeypatch.setattr(
        "openbase.modules.identity.migration.apply_identity_migration",
        fake_apply_identity_migration,
    )

    import asyncio

    engine = FakeEngine()
    asyncio.run(db_init.init_database(engine, "openbase"))

    assert len(calls) == 1, "init_database 未内联调用 apply_identity_migration（初始化链会漏迁移）"
    assert calls[0]["schema"] == "openbase", "身份迁移未透传 schema"
    assert calls[0]["engine"] is engine, "身份迁移未复用同一 engine"
    assert order[0] == "create_tables", "建表应在身份迁移之前"
    assert order[-1] == "apply_identity_migration", "身份迁移应在种子数据之后（初始化链末尾）"


# ---- v1.4.6 权限点补种（ADR-146-07 / AC-146-15：log:read / module:manage） ----


def _capture_init_statements(monkeypatch) -> list[tuple[str, dict]]:
    """执行 init_database（假 engine + 假身份迁移）并返回 ``[(SQL 文本, 绑定参数)]``."""
    import asyncio

    from openbase.core.db import init as db_init

    captured: list[tuple[str, dict]] = []

    class FakeConn:
        async def execute(self, stmt):
            bound = getattr(stmt, "_bindparams", {}) or {}
            params = {name: getattr(param, "value", None) for name, param in bound.items()}
            captured.append((str(stmt), params))

    class _Ctx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *a):
            return False

    class FakeEngine:
        def begin(self):
            return _Ctx(FakeConn())

    async def fake_create_tables(engine, schema="openbase", metadata=None):
        return None

    async def fake_apply_identity_migration(engine, schema=None):
        return {"columns_added": [], "permissions_seeded": 0}

    monkeypatch.setattr(db_init, "create_tables", fake_create_tables)
    monkeypatch.setattr(
        "openbase.modules.identity.migration.apply_identity_migration",
        fake_apply_identity_migration,
    )

    asyncio.run(db_init.init_database(FakeEngine(), "openbase"))
    return captured


def test_init_database_seeds_log_read_and_module_manage_permissions(monkeypatch):
    """log:read 与 module:manage 权限行入库（幂等，WHERE NOT EXISTS）.

    背景：两权限码此前仅存在于受权点（logs/router.py、frontend/__init__.py），
    未登记进权限种子 → 非 admin 角色（含 org_admin）经 user→role→permission 链
    查询为空，日志中心与模块开关页对其不可用。
    """
    statements = _capture_init_statements(monkeypatch)
    permission_rows = {
        params["code"]: (sql, params)
        for sql, params in statements
        if "INSERT INTO openbase.permissions" in sql and params.get("code")
    }
    for code, module in (("log:read", "logs"), ("module:manage", "frontend")):
        assert code in permission_rows, f"权限种子缺失: {code}"
        sql, params = permission_rows[code]
        assert params["module"] == module, f"{code} 的 module 归属错误: {params['module']}"
        assert params["name"], f"{code} 缺少名称"
        # 幂等：WHERE NOT EXISTS 守卫（可重放）
        assert "WHERE NOT EXISTS (SELECT 1 FROM openbase.permissions WHERE code = :code)" in sql


def test_init_database_grants_log_and_module_permissions_to_org_admin(monkeypatch):
    """授权口径：仅 org_admin 获 log:read / module:manage；user/viewer 不授.

    admin 持 '*' 通配（既有种子），日志读取与模块启停属平台级操作，
    不外扩到 user/viewer（与 auth:api-keys:* 既有口径一致）。
    """
    statements = _capture_init_statements(monkeypatch)
    role_permission_sql = [
        sql for sql, _ in statements if "INSERT INTO openbase.role_permission" in sql
    ]

    org_admin_grant = [
        sql
        for sql in role_permission_sql
        if "r.code = 'org_admin'" in sql
        and "'log:read'" in sql
        and "'module:manage'" in sql
    ]
    assert org_admin_grant, "org_admin 未获得 log:read / module:manage 授权"
    assert all("AND NOT EXISTS" in sql for sql in org_admin_grant), "授权须幂等"

    # 参数化角色循环（user/viewer/org_admin 的模块查看权限）不得包含新权限码
    parameterized_grants = [sql for sql in role_permission_sql if "r.code = :role" in sql]
    assert not any(
        "log:read" in sql or "module:manage" in sql for sql in parameterized_grants
    ), "user/viewer 不得持有 log:read / module:manage"

