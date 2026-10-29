"""安全专项测试：统一鉴权中间件（SR-001）行为验证."""

from fastapi.testclient import TestClient

from openbase import init_app
from openbase.settings import Settings


def _build(login: bool) -> TestClient:
    settings = Settings()
    for module in ("auth", "tenant", "audit", "config", "org", "dict", "scheduler", "storage", "notify", "mcp", "observability"):
        settings.enable_module(module)
    from openbase.modules.auth import UserService

    UserService.seed_memory_user("admin", "admin123")
    client = TestClient(init_app(settings))
    if login:
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client


def test_anonymous_business_api_401():
    """匿名访问业务接口 → 401 统一错误格式."""
    client = _build(login=False)
    for path in ("/api/v1/dicts", "/api/v1/configs/feature.flag", "/api/v1/org/departments", "/audit/records"):
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} → {resp.status_code}"
        body = resp.json()
        assert body["code"] == "AUTH_401"
        assert "request_id" in body


def test_forged_token_401():
    """伪造 token → 401."""
    client = _build(login=False)
    resp = client.get("/api/v1/dicts", headers={"Authorization": "Bearer fake.token.here"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_401"


def test_authenticated_business_api_200():
    """有效 token 访问业务接口 → 200."""
    client = _build(login=True)
    resp = client.get("/api/v1/dicts")
    assert resp.status_code == 200


def test_public_paths_anonymous_ok():
    """白名单路径匿名可访问."""
    client = _build(login=False)
    assert client.get("/health").status_code == 200
    assert client.get("/observability/status").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_unknown_route_with_token_404():
    """带 token 访问不存在路由 → 404（非 401，中间件放行后由路由层处理）."""
    client = _build(login=True)
    resp = client.get("/api/v1/not-exist")
    assert resp.status_code == 404


# ---- E0-5（R5/P0-5）：超管判定改为显式权限点，不再按用户名 ----


class _NoDbSession:
    """DB 不可用会话桩：权限查询异常 → 回退内存 PermissionStore（空）."""

    async def execute(self, _statement):  # noqa: ANN001 - 桩方法
        raise RuntimeError("database unavailable")


def _permission_granted(user: dict, permission_code: str = "tenant:manage") -> bool:
    """调用统一权限门禁，返回是否放行."""
    import asyncio

    from openbase.core.errors import BaseError
    from openbase.modules.auth.rbac import ensure_user_permission

    async def _run() -> bool:
        try:
            await ensure_user_permission(_NoDbSession(), user, permission_code)
        except BaseError:
            return False
        return True

    return asyncio.run(_run())


def test_superadmin_permission_point_replaces_username_hardcode():
    """用户名 admin 不再自动放行；超管来自 system:superadmin / * / 内置 admin 角色."""
    base = {"id": 1, "permissions": [], "role": "viewer"}
    # 仅用户名 admin（无权限点、非 admin 角色）→ 拒绝（原有硬编码已被移除）
    assert _permission_granted({**base, "username": "admin"}) is False
    # 显式超管权限点 → 放行（任意用户名）
    assert _permission_granted({**base, "username": "ops-a", "permissions": ["system:superadmin"]}) is True
    # 持有目标权限点 → 放行
    assert _permission_granted({**base, "username": "ops-b", "permissions": ["tenant:manage"]}) is True
    # 内存降级（DB 无矩阵）：内置 admin 角色锚点 → 放行（改名/多管理员场景不再失效）
    assert _permission_granted({**base, "username": "renamed-admin", "role": "admin"}) is True
