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
