"""OpenBase v1.4.10 Step 3 实际运行验证（L1/L2/L3）冒烟脚本.

运行（仓库根目录任意 cwd 均可，脚本自定位仓库根）::

    python doc/test/evidence/v1410/v1410_l1l2l3_smoke.py

判据：
- **L1 构建**：``compileall`` 零错误 ＋ ``import openbase`` 成功（前端由 ``npm run build`` 另证）。
- **L2 启动**：装配应用（``init_app``）成功；dps-proxy 路由表 **34 条**（既有 12 ＋ 新增 22）；
  ASGI ``TestClient`` 上下文可启动；``/openapi.json`` 可达（应用已就绪）。
- **L3 冒烟**：5 例
  S1 认证门禁：无 token 访问新增端点 → 401（fail-closed）；
  S2 端点契约：带 token 访问 ``GET /api/v1/dps-proxy/templates``（mock 上游 200）→ 200 且透传；
  S3 错误保真：上游 404 ``{detail}``／409 网关错误体 → 本仓同码同 message（不转 500）；
  S4 路由顺序：静态 ``/lineage/impact`` 先于动态 ``/lineage/tags/{tag_code}``；
  S5 兼容性：既有 12 条路由路径／方法不变。

本脚本**只使用 mock 上游**（不依赖真实 DPS），故结论为**夹具级冒烟**；运行态联调另见
《测试移交说明-v1.4.10》。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PREFIX = "/api/v1/dps-proxy"
UPSTREAM_BASE = "http://127.0.0.1:8000"

V1410_ROUTES = [
    ("#1", "/template-packages/export", "POST"),
    ("#2", "/template-packages/import", "POST"),
    ("#3", "/templates/{code}/diff", "GET"),
    ("#4", "/templates/{code}/rollback", "POST"),
    ("#5", "/templates/{code}/preflight", "GET"),
    ("#6", "/lineage/tags/{tag_code}", "GET"),
    ("#7", "/lineage/impact", "GET"),
    ("#8", "/measures/suggest", "GET"),
    ("#9", "/annotation-adapters/{adapter_id}/generate", "POST"),
    ("#10", "/scoring-types", "GET"),
    ("#11", "/templates", "GET"),
    ("#12", "/templates/{code}", "GET"),
    ("#13", "/templates", "POST"),
    ("#14", "/templates/{code}", "PUT"),
    ("#15", "/templates/{code}/activate", "POST"),
    ("#16", "/templates/{code}/deactivate", "POST"),
    ("#17", "/annotation-templates", "GET"),
    ("#18", "/annotation-templates/{code}", "GET"),
    ("#19", "/annotation-templates", "POST"),
    ("#20", "/annotation-templates/{code}", "PUT"),
    ("#21", "/annotation-templates/{code}", "DELETE"),
    ("#22", "/labels", "GET"),
]

EXISTING_ROUTES = [
    ("portraits-list", "/portraits", "GET"),
    ("portrait-detail", "/portraits/{person_id}", "GET"),
    ("portrait-calculate", "/portraits/calculate", "POST"),
    ("portrait-update", "/portraits/{person_id}", "PUT"),
    ("tags-categories-list", "/tags/categories", "GET"),
    ("tags-category-create", "/tags/categories", "POST"),
    ("tags-category-update", "/tags/categories/{category_id}", "PUT"),
    ("tags-category-delete", "/tags/categories/{category_id}", "DELETE"),
    ("reports-overview", "/reports/overview", "GET"),
    ("batch-task-status", "/batch/tasks/{task_id}", "GET"),
    ("audit-logs", "/audit/logs", "GET"),
    ("health", "/health", "GET"),
]


def _say(line: str) -> None:
    print(line, flush=True)


# ---------------------------------------------------------------------------
# L1 构建
# ---------------------------------------------------------------------------


def l1_build() -> bool:
    _say("[L1] 构建验证")
    proc = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "openbase"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    _say(f"  compileall exit_code={proc.returncode}")
    if proc.returncode != 0:
        _say(proc.stdout[-2000:])
        _say(proc.stderr[-2000:])
        return False
    import openbase

    _say(f"  import openbase OK; __version__={openbase.__version__}")
    return True


# ---------------------------------------------------------------------------
# L2 启动
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.request_calls: list[dict] = []
        self.responses: list[FakeResponse] = []

    def set_responses(self, responses: list[FakeResponse]) -> None:
        self.responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.request_calls.append({"method": method, "url": url, **kwargs})
        if self.responses:
            resp = self.responses.pop(0)
            if not self.responses:
                self.responses.append(resp)
            return resp
        return FakeResponse(200, {"code": 200, "message": "success", "data": {}})


def l2_l3() -> tuple[bool, bool]:
    import httpx
    from fastapi.testclient import TestClient

    from openbase import init_app
    from openbase.modules import dps_proxy
    from openbase.modules.auth import UserService
    from openbase.modules.auth.jwt import create_access_token
    from openbase.modules.protocol_headers import PROXY_SOURCE_DPS
    from openbase.settings import Settings

    # ---- L2：装配 + 启动 ----
    _say("[L2] 启动验证")
    settings = Settings()
    for module in ("auth", "proxy", "dps_proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    settings.dps_upstream_base = UPSTREAM_BASE
    settings.dps_health_check_enabled = False
    import importlib

    settings_module = importlib.import_module("openbase.settings")
    settings_module._settings = settings
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)

    dps_paths = {f"{PREFIX}{path}" for _rid, path, _m in V1410_ROUTES}
    dps_route_objects = [r for r in dps_proxy.router.routes if getattr(r, "path", None)]
    new_route_count = len([r for r in dps_route_objects if r.path in dps_paths])
    _say(f"  app assembled: title={app.title!r}")
    _say(f"  dps-proxy 路由对象总数={len(dps_route_objects)}; v1.4.10 新增路由对象={new_route_count}")
    l2_ok = new_route_count == 22
    if not l2_ok:
        _say("  [FAIL] v1.4.10 新增路由对象数应为 22")

    fake = FakeAsyncClient()
    original_client = httpx.AsyncClient
    httpx.AsyncClient = lambda *a, **k: fake  # type: ignore[assignment]
    try:
        with TestClient(app) as client:
            openapi = client.get("/openapi.json")
            _say(f"  TestClient started; GET /openapi.json -> {openapi.status_code}")
            l2_ok = l2_ok and openapi.status_code == 200

            # ---- L3 冒烟 ----
            _say("[L3] 冒烟验证（5 例）")
            results: list[tuple[str, bool, str]] = []

            # S1 认证门禁
            r1 = client.get(f"{PREFIX}/templates")
            s1 = r1.status_code == 401 and r1.json().get("code") == "AUTH_401"
            results.append(("S1 认证门禁 401", s1, f"status={r1.status_code}, code={r1.json().get('code')}"))

            token = create_access_token(
                "42", username="smoke", tenant_id="tenant-001",
                extra={"org_id": "org-001", "role": "admin"},
            )
            auth = {"Authorization": f"Bearer {token}"}

            # S2 端点契约（mock 上游 200）
            fake.set_responses([FakeResponse(200, {"code": 200, "message": "success", "data": {"items": [], "total": 0}})])
            r2 = client.get(f"{PREFIX}/templates?status=active", headers=auth)
            call2 = fake.request_calls[-1]
            proxy_source = call2["headers"].get("X-Proxy-Source")
            s2 = (
                r2.status_code == 200
                and r2.json().get("code") == 0
                and call2["url"] == f"{UPSTREAM_BASE}/api/v2/portrait/templates"
                and proxy_source == PROXY_SOURCE_DPS
            )
            results.append(
                (
                    "S2 端点契约透传 200",
                    s2,
                    f"status={r2.status_code}, body_code={r2.json().get('code')}, "
                    f"upstream={call2['url']}, X-Proxy-Source={proxy_source!r}",
                )
            )

            # S3 错误语义保真（404 detail / 409 网关）
            fake.set_responses([FakeResponse(404, {"detail": "画像模板不存在: tpl-x"})])
            r3a = client.get(f"{PREFIX}/templates/tpl-x", headers=auth)
            fake.set_responses([FakeResponse(409, {"code": 409, "message": "code already exists", "data": None})])
            r3b = client.post(f"{PREFIX}/annotation-templates", json={"code": "at-1"}, headers=auth)
            s3 = (
                r3a.status_code == 404 and r3a.json().get("code") == 404
                and r3b.status_code == 409 and r3b.json().get("message") == "code already exists"
            )
            results.append(("S3 错误语义保真 404/409", s3, f"404->{r3a.status_code}, 409->{r3b.status_code}"))

            # S4 路由顺序：静态先于动态
            def idx(path: str, method: str) -> int:
                for i, route in enumerate(dps_proxy.router.routes):
                    if getattr(route, "path", None) == path and method in (getattr(route, "methods", None) or set()):
                        return i
                raise AssertionError(f"not found: {method} {path}")

            s4 = idx(f"{PREFIX}/lineage/impact", "GET") < idx(f"{PREFIX}/lineage/tags/{{tag_code}}", "GET")
            s4 = s4 and idx(f"{PREFIX}/templates", "GET") < idx(f"{PREFIX}/templates/{{code}}", "GET")
            results.append(("S4 路由顺序（静态先于动态）", s4, "impact<templates-tag; list<detail"))

            # S5 既有 12 路由不变
            s5 = True
            for _name, path, method in EXISTING_ROUTES:
                matched = [r for r in dps_proxy.router.routes if getattr(r, "path", None) == f"{PREFIX}{path}"]
                s5 = s5 and any(method in (getattr(r, "methods", None) or set()) for r in matched)
            results.append(("S5 既有 12 路由不变", s5, f"checked={len(EXISTING_ROUTES)}"))

            l3_ok = True
            for name, ok, detail in results:
                l3_ok = l3_ok and ok
                _say(f"  [{'PASS' if ok else 'FAIL'}] {name} :: {detail}")
    finally:
        httpx.AsyncClient = original_client  # type: ignore[assignment]

    return l2_ok, l3_ok


def main() -> int:
    l1_ok = l1_build()
    l2_ok, l3_ok = l2_l3()
    _say("")
    _say(f"L1 构建: {'PASS' if l1_ok else 'FAIL'}")
    _say(f"L2 启动: {'PASS' if l2_ok else 'FAIL'}")
    _say(f"L3 冒烟: {'PASS' if l3_ok else 'FAIL'}")
    return 0 if (l1_ok and l2_ok and l3_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
