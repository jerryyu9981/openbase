"""v1.4.10 Step 3 P1 路由映射断言测试（TD-1410-04／TD-1410-33；22 条逐条断言）.

契约事实源：
- 《OpenBase-API接口设计文档-v1.4.10》§1（10 新增端点 #1~#10）／§1.1（12 条补代理
  端点 #11~#22）／§1 路由注册顺序（DT-04 强制条款）；
- 《OpenBase-设计开发追溯矩阵-v1.4.10》§2.1（TD-1410-04 路由顺序 22 条断言／
  TD-1410-33 通道边界）／§3（Subtask CheckList）。

断言分层：
1. **22 条 v1.4.10 端点**逐条存在（路径 ＋ 方法精确匹配）—— 参数化 22 用例；
2. **路由注册顺序**：静态段／列表路由先于同名动态段；
3. **既有 12 条路由**路径与方法未变（回归，TD-21 兼容性）；
4. **通道边界**：新增端点仅挂 dps_proxy 专用路由，通用代理
   ``/api/v1/proxy/{system}/{path}`` 不承载本版新增端点（TD-33）。

本测试只做**静态路由表断言**（不发起请求、不依赖上游），故无需 mock 上游。
"""

from __future__ import annotations

import pytest

from openbase.modules import dps_proxy, proxy

PREFIX = "/api/v1/dps-proxy"

# 22 条 v1.4.10 端点（编号，本仓相对路径，HTTP 方法）—— 契约 §1 表 #1~#10 ＋ §1.1 表 #11~#22
V1410_ROUTES: list[tuple[str, str, str]] = [
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

# 既有 12 条路由（v1.4.5 R-381 起；本版**行为与对外路径不变**）
EXISTING_ROUTES: list[tuple[str, str, str]] = [
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


def _matched_routes(full_path: str) -> list[object]:
    """返回 router 中路径等于 ``full_path`` 的全部路由对象."""
    return [
        route
        for route in dps_proxy.router.routes
        if getattr(route, "path", None) == full_path
    ]


def _methods_of(routes: list[object]) -> set[str]:
    """合并多个路由对象的方法集合（Starlette GET 路由会自动补 HEAD）."""
    methods: set[str] = set()
    for route in routes:
        methods.update(getattr(route, "methods", None) or set())
    return methods


def _route_index(full_path: str, method: str) -> int:
    """返回 ``(full_path, method)`` 在 router 中的注册序号（找不到即断言失败）."""
    for index, route in enumerate(dps_proxy.router.routes):
        if getattr(route, "path", None) != full_path:
            continue
        if method in (getattr(route, "methods", None) or set()):
            return index
    raise AssertionError(f"route not registered: {method} {full_path}")


# ---------------------------------------------------------------------------
# 1. 22 条 v1.4.10 端点逐条断言（DT-04）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("route_id", "path", "method"),
    V1410_ROUTES,
    ids=[f"{route_id}-{method}-{path}" for route_id, path, method in V1410_ROUTES],
)
def test_v1410_endpoint_route_registered(route_id: str, path: str, method: str) -> None:
    """每条 v1.4.10 端点均以精确路径 ＋ 方法注册于 dps_proxy router."""
    full_path = f"{PREFIX}{path}"
    matched = _matched_routes(full_path)
    assert matched, f"{route_id} 路由未注册: {full_path}"
    assert method in _methods_of(matched), (
        f"{route_id} 方法缺失: {method} {full_path}（实际={sorted(_methods_of(matched))}）"
    )


def test_v1410_route_objects_count_is_22() -> None:
    """v1.4.10 新增路由对象恰为 22 个（10 新增 ＋ 12 补代理，无重复／无遗漏）.

    注：同路径多方法（如 ``/templates`` GET＋POST）各计一个路由对象，合计 22。
    """
    v1410_paths = {f"{PREFIX}{path}" for _rid, path, _method in V1410_ROUTES}
    new_route_objects = [
        route
        for route in dps_proxy.router.routes
        if getattr(route, "path", None) in v1410_paths
    ]
    assert len(new_route_objects) == 22, (
        f"v1.4.10 路由对象数应为 22，实际={len(new_route_objects)}"
    )


# ---------------------------------------------------------------------------
# 2. 路由注册顺序（DT-04：静态段／列表路由先于同名动态段）
# ---------------------------------------------------------------------------


def test_static_lineage_impact_before_dynamic_tag_lineage() -> None:
    """/lineage/impact（静态）先于 /lineage/tags/{tag_code}（动态）."""
    assert _route_index(f"{PREFIX}/lineage/impact", "GET") < _route_index(
        f"{PREFIX}/lineage/tags/{{tag_code}}", "GET"
    )


def test_templates_list_before_template_dynamic_segment() -> None:
    """/templates（列表）先于 /templates/{code}（详情）注册."""
    assert _route_index(f"{PREFIX}/templates", "GET") < _route_index(
        f"{PREFIX}/templates/{{code}}", "GET"
    )


def test_templates_list_before_template_subresources() -> None:
    """/templates（列表）先于 /templates/{code}/diff 等子资源路由注册."""
    list_index = _route_index(f"{PREFIX}/templates", "GET")
    subresources = (
        ("/templates/{code}/diff", "GET"),
        ("/templates/{code}/rollback", "POST"),
        ("/templates/{code}/preflight", "GET"),
    )
    for sub_path, method in subresources:
        assert list_index < _route_index(f"{PREFIX}{sub_path}", method)


def test_annotation_templates_list_before_dynamic_segment() -> None:
    """/annotation-templates（列表）先于 /annotation-templates/{code} 注册."""
    assert _route_index(f"{PREFIX}/annotation-templates", "GET") < _route_index(
        f"{PREFIX}/annotation-templates/{{code}}", "GET"
    )


def test_list_routes_precede_dynamic_segments() -> None:
    """列表路由 /templates、/annotation-templates、/labels 均先于同名动态段注册（DT-04）."""
    assert _route_index(f"{PREFIX}/templates", "GET") < _route_index(
        f"{PREFIX}/templates/{{code}}", "GET"
    )
    assert _route_index(f"{PREFIX}/annotation-templates", "GET") < _route_index(
        f"{PREFIX}/annotation-templates/{{code}}", "GET"
    )
    # /labels 先于全部动态段
    labels_index = _route_index(f"{PREFIX}/labels", "GET")
    assert labels_index < _route_index(f"{PREFIX}/templates/{{code}}/diff", "GET")
    assert labels_index < _route_index(f"{PREFIX}/annotation-templates/{{code}}", "GET")


def test_labels_and_scoring_types_registered_once() -> None:
    """/labels、/scoring-types 均为静态列表路由，注册在 router 内且各恰一条."""
    assert "GET" in _methods_of(_matched_routes(f"{PREFIX}/labels"))
    assert "GET" in _methods_of(_matched_routes(f"{PREFIX}/scoring-types"))
    assert len(_matched_routes(f"{PREFIX}/labels")) == 1
    assert len(_matched_routes(f"{PREFIX}/scoring-types")) == 1


# ---------------------------------------------------------------------------
# 3. 既有 12 条路由回归（保持行为与对外路径不变）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "path", "method"),
    EXISTING_ROUTES,
    ids=[f"{name}-{method}" for name, path, method in EXISTING_ROUTES],
)
def test_existing_route_unchanged(name: str, path: str, method: str) -> None:
    """既有 12 条路由仍以原路径 ＋ 原方法注册（v1.4.10 不改行为）."""
    full_path = f"{PREFIX}{path}"
    matched = _matched_routes(full_path)
    assert matched, f"既有路由丢失: {name} {full_path}"
    assert method in _methods_of(matched), f"既有路由方法变更: {name} {method}"


# ---------------------------------------------------------------------------
# 4. 通道边界（TD-33：通用代理不承载本版新增端点）
# ---------------------------------------------------------------------------


def test_generic_proxy_has_only_catch_all_route() -> None:
    """通用代理仅保留 catch-all 透传路由，未新增本版 22 端点声明（可审计边界）."""
    routes = list(proxy.router.routes)
    assert len(routes) == 1, "通用代理不应新增逐端点声明路由"
    assert getattr(routes[0], "path", None) == "/api/v1/proxy/{system}/{path:path}"


def test_new_endpoints_not_declared_on_generic_proxy() -> None:
    """本版 22 端点相对路径不得出现在通用代理路由表中（避免'路由未声明但可达'）."""
    generic_paths = {getattr(route, "path", None) for route in proxy.router.routes}
    for _route_id, path, _method in V1410_ROUTES:
        assert path not in generic_paths
        assert f"/api/v1/proxy/dps{path}" not in generic_paths
