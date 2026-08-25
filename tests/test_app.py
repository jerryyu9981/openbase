"""init_app 装配 + 核心模块集成冒烟测试."""

from fastapi.testclient import TestClient

from openbase import init_app
from openbase.settings import Settings


def build_test_app() -> TestClient:
    settings = Settings()
    for module in ("auth", "tenant", "audit", "config", "org", "dict", "scheduler", "storage", "notify"):
        settings.enable_module(module)
    # 种子内存演示用户（数据库不可用时登录校验降级）
    from openbase.modules.auth import UserService

    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    client = TestClient(app)
    # 统一鉴权中间件（SR-001）：登录获取 token 并默认携带（业务接口需 JWT）
    login = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    if login.status_code == 200:
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client


def test_health_endpoint():
    client = build_test_app()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_login_endpoint():
    client = build_test_app()
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    body = resp.json()
    # 成功响应直接返回资源（response_model 序列化）
    assert body["access_token"]


def test_login_wrong_password():
    client = build_test_app()
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_401"


def test_refresh_endpoint():
    client = build_test_app()
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()
    refresh_token = login["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_unified_error_format_on_unknown_route():
    client = build_test_app()
    resp = client.get("/api/v1/not-exist")
    # 404 由 FastAPI 默认处理，但格式统一
    assert resp.status_code == 404
    body = resp.json()
    assert "request_id" in body or "detail" in body


def test_dict_crud_flow():
    client = build_test_app()
    # 创建字典类型
    r1 = client.post("/api/v1/dicts", json={"code": "gender", "name": "性别"})
    assert r1.status_code == 200
    # 创建字典项
    r2 = client.post("/api/v1/dicts/gender/items", json={"label": "男", "value": "M", "sort_order": 1})
    assert r2.status_code == 200
    assert r2.json()["label"] == "男"
    # 列表联动
    r3 = client.get("/api/v1/dicts/gender/items")
    assert r3.status_code == 200
    assert len(r3.json()) == 1


def test_org_department_flow():
    client = build_test_app()
    r1 = client.post("/api/v1/org/departments", json={"name": "研发部"})
    assert r1.status_code == 200
    dep_id = r1.json()["id"]
    r2 = client.post("/api/v1/org/departments", json={"name": "后端组", "parent_id": dep_id})
    assert r2.status_code == 200
    assert r2.json()["path"] == f"/{dep_id}/{dep_id + 1}"
    r3 = client.get("/api/v1/org/departments/tree")
    assert r3.status_code == 200
    assert len(r3.json()) == 1
    assert len(r3.json()[0]["children"]) == 1


def test_config_rollback_flow():
    client = build_test_app()
    r1 = client.post("/api/v1/configs", json={"key": "feature.flag", "value": {"on": True}})
    assert r1.status_code == 200
    r2 = client.post("/api/v1/configs", json={"key": "feature.flag", "value": {"on": False}})
    assert r2.status_code == 200
    versions = client.get("/api/v1/configs/feature.flag/versions").json()
    assert len(versions) == 2
    rollback = client.post("/api/v1/configs/feature.flag/rollback?version=1")
    assert rollback.status_code == 200
    assert rollback.json()["value"] == {"on": True}


def test_storage_upload_flow():
    client = build_test_app()
    resp = client.post(
        "/api/v1/files",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["size"] == 11
    assert body["backend"] == "local"
    # 元数据可查
    detail = client.get(f"/api/v1/files/{body['id']}")
    assert detail.status_code == 200
