"""demo_app 启动与降级回退测试（覆盖率补充：NFR-006 ≥85%）."""


def test_demo_app_falls_back_to_memory_when_db_unavailable(monkeypatch):
    """数据库初始化失败 → `_try_database_init()` 返回 False，并降级种子内存演示用户.

    背景（2026-10-29）：原用例断言 import 期 ``_DB_READY is False``，在全量套件中
    ``openbase.demo_app`` 可能已被更早的模块导入并成功连库（``_DB_READY=True``），
    结果随环境漂移。改为直接驱动降级分支，不依赖 import 时序与外部 DB 可用性。
    """
    import openbase.demo_app as demo
    from openbase.modules.auth import UserService

    def _unavailable():
        raise RuntimeError("database unavailable (simulated)")

    monkeypatch.setattr(demo, "get_engine", _unavailable)
    assert demo._try_database_init() is False

    # 覆盖模块级降级分支（原 import 期执行，现可确定性复现）
    demo._fallback_to_memory()
    assert "admin" in UserService._memory_users

    # 应用可正常装配（init_app 含鉴权/审计/租户中间件 + 模块路由）
    assert demo.app is not None


def test_demo_app_db_init_success_path(monkeypatch):
    """数据库初始化成功路径（_DB_READY=True，覆盖 demo_app DB 分支）."""

    # mock 数据库初始化成功
    class _FakeEngine:
        async def dispose(self):
            return None

    async def fake_init_database(engine, schema):
        return None

    async def fake_seed_admin(session):
        return None

    async def fake_hydrate(session):
        return None

    monkeypatch.setattr("openbase.modules.config.ConfigStore.hydrate", fake_hydrate)

    class _FakeCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _FakeFactory:
        def __call__(self):
            return _FakeCtx()

    monkeypatch.setattr("openbase.demo_app.get_engine", lambda: _FakeEngine())
    monkeypatch.setattr("openbase.demo_app.init_database", fake_init_database)
    monkeypatch.setattr("openbase.demo_app._seed_admin", fake_seed_admin)
    monkeypatch.setattr("openbase.demo_app.get_session_factory", lambda: _FakeFactory())

    import openbase.demo_app as demo

    assert demo._try_database_init() is True
