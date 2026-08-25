"""demo_app 启动与降级回退测试（覆盖率补充：NFR-006 ≥85%）."""


def test_demo_app_starts_and_falls_back():
    """无真实数据库时 demo_app 降级内存演示用户并可装配应用."""
    import os

    # 确保不携带真实 DB 配置（隔离环境变量）
    os.environ.pop("OPENBASE_DB_URL", None)
    os.environ.pop("POSTGRES_URL", None)

    from openbase import demo_app
    from openbase.modules.auth import UserService

    # 测试环境默认 DB（localhost:5432）不可达 → 降级内存
    assert demo_app._DB_READY is False
    assert "admin" in UserService._memory_users
    # 应用可正常装配（init_app 含鉴权/审计/租户中间件 + 11 模块路由）
    assert demo_app.app is not None
    # 登录路径（内存用户）可用
    from fastapi.testclient import TestClient

    client = TestClient(demo_app.app)
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


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
