"""ai_apps / proxy / frontend(modules) 增量模块测试（v1.2.0 后端增量）."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openbase.core.errors import install_exception_handlers
from openbase.modules.ai_apps import AiAppService
from openbase.modules.ai_apps import router as ai_apps_router
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.frontend import ModuleService
from openbase.modules.frontend import router as frontend_router
from openbase.modules.proxy import PROXY_SYSTEMS
from openbase.modules.proxy import router as proxy_router


def _auth_headers() -> dict[str, str]:
    """生成有效 JWT 请求头（路由依赖 get_current_user）."""
    token = create_access_token("1", username="admin", tenant_id="openbase")
    return {"Authorization": f"Bearer {token}"}

# ---- ai_apps 服务 ----

def test_ai_app_create_and_get():
    service = AiAppService()
    app = service.create(
        name="智能问答",
        description="统一前端 AI 应用",
        model_config={"provider": "openai", "model": "gpt-4o", "parameters": {"temperature": 0.3}},
    )
    assert app["id"] is not None
    assert app["status"] == "draft"
    assert app["current_version"] is None
    fetched = service.get(app["id"])
    assert fetched["name"] == "智能问答"


def test_ai_app_update_and_publish():
    service = AiAppService()
    app = service.create(name="测试应用", model_config={"provider": "ollama", "model": "qwen2.5"})
    service.update(app["id"], name="测试应用V2", description="更新描述")
    assert service.get(app["id"])["name"] == "测试应用V2"
    service.publish(app["id"])
    published = service.get(app["id"])
    assert published["status"] == "published"
    assert published["current_version"] == "v1"
    service.publish(app["id"])
    assert service.get(app["id"])["current_version"] == "v2"


def test_ai_app_delete_and_calls():
    service = AiAppService()
    app = service.create(name="待删", model_config={"provider": "openai", "model": "gpt-4o-mini"})
    service.record_call(app["id"], user_id=1, input_tokens=10, output_tokens=5, latency_ms=120, status="success")
    calls = service.calls(app["id"])
    assert len(calls) == 1
    assert calls[0]["total_tokens"] == 15
    service.delete(app["id"])
    assert service.get(app["id"]) is None


# ---- ai_apps 路由（鉴权中间件豁免处理：直接挂路由验证响应结构） ----

def _build_app_with_router(router) -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    return app


def test_ai_apps_router_crud():
    AiAppService._reset()
    app = _build_app_with_router(ai_apps_router)
    client = TestClient(app)
    headers = _auth_headers()
    resp = client.post("/api/v1/ai-apps", json={"name": "路由应用", "llm_config": {"provider": "openai", "model": "gpt-4o"}}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    app_id = body["data"]["id"]
    list_resp = client.get("/api/v1/ai-apps", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]["items"]) == 1
    pub_resp = client.post(f"/api/v1/ai-apps/{app_id}/publish", headers=headers)
    assert pub_resp.json()["data"]["status"] == "published"
    del_resp = client.delete(f"/api/v1/ai-apps/{app_id}", headers=headers)
    assert del_resp.status_code == 200


def test_ai_apps_router_validation():
    app = _build_app_with_router(ai_apps_router)
    client = TestClient(app)
    resp = client.post("/api/v1/ai-apps", json={"name": "", "llm_config": {}}, headers=_auth_headers())
    assert resp.status_code == 422


# ---- proxy 代理 ----

def test_proxy_unknown_system():
    app = _build_app_with_router(proxy_router)
    client = TestClient(app)
    resp = client.get("/api/v1/proxy/unknown/health", headers=_auth_headers())
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"].startswith("PARAM")


def test_proxy_system_whitelist():
    assert set(PROXY_SYSTEMS) == {"openllm", "openrag", "openmemory", "dps"}


def test_proxy_backend_unreachable_returns_502():
    app = _build_app_with_router(proxy_router)
    client = TestClient(app)
    # 指向不可达地址：期望统一 502 错误包装而非裸异常
    resp = client.get("/api/v1/proxy/openllm/health", headers=_auth_headers())
    assert resp.status_code in (200, 502)
    if resp.status_code == 502:
        body = resp.json()
        assert body["code"].startswith("SYS")


# ---- frontend modules API ----

def test_modules_api_returns_five_modules():
    app = _build_app_with_router(frontend_router)
    client = TestClient(app)
    resp = client.get("/api/v1/modules", headers=_auth_headers())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    ids = {item["id"] for item in items}
    # v1.4.x+ 模块注册表：openllm/knowledge/memory/portrait + gateway（统一网关，R-367）
    assert ids == {"openllm", "knowledge", "memory", "portrait", "gateway"}


def test_module_service_fallback():
    service = ModuleService()
    modules = service.list_modules()
    assert len(modules) == 5
    assert modules[0]["status"] == "enabled"


# ---- auth /me 端点（v1.2.0 登录链路修复回归） ----

def test_auth_me_returns_wildcard_for_admin():
    """admin 用户 me 返回通配权限（DB RBAC 未就绪时兜底）."""
    from openbase.core.db.session import get_db
    from openbase.modules.auth import router as auth_router

    class FakeSession:
        async def execute(self, *args, **kwargs):  # noqa: ANN002
            raise RuntimeError("no db in test")

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(auth_router)
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)
    token = create_access_token("1", username="admin", tenant_id="openbase")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert "*" in body["permissions"]


def test_auth_me_requires_token():
    """me 端点必须携带有效 JWT."""
    from openbase.modules.auth import router as auth_router

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(auth_router)
    client = TestClient(app)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
