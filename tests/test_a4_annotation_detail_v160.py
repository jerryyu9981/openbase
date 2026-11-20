"""v1.6.0 A4：标注详情代理用例。

覆盖：
    - 路由注册与静态段顺序（``/annotations/export`` 先于动态详情段）；
    - 路径编码与身份头/查询参数透传；
    - 上游 404 语义保真（不改写为 OpenBase 错误码）。
"""

from __future__ import annotations

import pytest
from fastapi.responses import JSONResponse
from starlette.requests import Request

from openbase.modules import dps_proxy

PREFIX = "/api/v1/dps-proxy"


def _route_index(full_path: str, method: str) -> int:
    for index, route in enumerate(dps_proxy.router.routes):
        if getattr(route, "path", None) != full_path:
            continue
        if method in (getattr(route, "methods", None) or set()):
            return index
    raise AssertionError(f"route not registered: {method} {full_path}")


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"{PREFIX}/annotations/a-1",
            "headers": [],
            "query_string": b"verbose=1",
        }
    )


def test_detail_route_registered() -> None:
    _route_index(f"{PREFIX}/annotations/{{annotation_id}}", "GET")


def test_static_export_precedes_dynamic_detail() -> None:
    export_index = _route_index(f"{PREFIX}/annotations/export", "GET")
    detail_index = _route_index(f"{PREFIX}/annotations/{{annotation_id}}", "GET")
    assert export_index < detail_index


@pytest.mark.asyncio
async def test_detail_forwards_encoded_path_and_identity(monkeypatch) -> None:
    captured: dict = {}

    async def fake_forward(method, upstream_path, **kwargs):
        captured.update(method=method, upstream_path=upstream_path, **kwargs)
        return JSONResponse({"code": 0, "message": "success", "data": {"annotation": {"id": "a/1"}}})

    monkeypatch.setattr(dps_proxy, "_forward", fake_forward)
    monkeypatch.setattr(dps_proxy, "_build_identity_headers", lambda user, req: {"X-User-ID": "u1"})

    response = await dps_proxy.dps_annotation_detail("a/1", _request(), {"sub": "u1"})

    assert response.status_code == 200
    assert captured["method"] == "GET"
    assert captured["upstream_path"] == "/api/v2/portrait/annotations/a%2F1"
    assert captured["params"] == {"verbose": "1"}
    assert captured["headers"] == {"X-User-ID": "u1"}


@pytest.mark.asyncio
async def test_detail_upstream_404_passthrough(monkeypatch) -> None:
    async def fake_forward(method, upstream_path, **kwargs):
        return JSONResponse(
            {"code": 404, "message": "标注记录不存在: a-x", "data": None},
            status_code=404,
        )

    monkeypatch.setattr(dps_proxy, "_forward", fake_forward)
    monkeypatch.setattr(dps_proxy, "_build_identity_headers", lambda user, req: {})

    response = await dps_proxy.dps_annotation_detail("a-x", _request(), {"sub": "u1"})
    assert response.status_code == 404
