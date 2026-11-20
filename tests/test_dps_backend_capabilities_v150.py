"""v1.5.0 后端能力用例：A6/A9/A10/A11/A14.

覆盖：
- 新路由注册与静态段顺序（``/portraits/export`` 必须先于 ``/portraits/{person_id}``）；
- CSV 单元格转义与注入防护（A11）；
- CSV 流式生成器 BOM／分页（A11）；
- 候选行序列化（A14，fields_json → 对象）。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from openbase.modules import dps_proxy
from openbase.modules.dps_proxy import candidate_store

PREFIX = "/api/v1/dps-proxy"

NEW_ROUTES: list[tuple[str, str]] = [
    ("/tags", "GET"),
    ("/audit", "GET"),
    ("/annotations/export", "GET"),
    ("/portraits/export", "GET"),
    ("/annotation-candidates", "POST"),
    ("/annotation-candidates", "GET"),
    ("/annotation-candidates/latest", "GET"),
]


def _route_index(full_path: str, method: str) -> int:
    for index, route in enumerate(dps_proxy.router.routes):
        if getattr(route, "path", None) != full_path:
            continue
        if method in (getattr(route, "methods", None) or set()):
            return index
    raise AssertionError(f"route not registered: {method} {full_path}")


@pytest.mark.parametrize(("path", "method"), NEW_ROUTES)
def test_v150_routes_registered(path: str, method: str) -> None:
    _route_index(f"{PREFIX}{path}", method)


def test_portraits_export_registered_before_dynamic_segment() -> None:
    """静态导出路由必须先注册，否则会被 ``/portraits/{person_id}`` 捕获."""
    export_index = _route_index(f"{PREFIX}/portraits/export", "GET")
    dynamic_index = _route_index(f"{PREFIX}/portraits/{{person_id}}", "GET")
    assert export_index < dynamic_index


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("plain", '"plain"'),
        ('a"b', '"a""b"'),
        ("a,b", '"a,b"'),
        ("=1+2", "\"'=1+2\""),
        ("@cmd", "\"'@cmd\""),
        ("-2", "\"'-2\""),
        ("+1", "\"'+1\""),
        (None, '""'),
    ],
)
def test_csv_cell_escapes_and_guards(raw, expected) -> None:
    assert dps_proxy._csv_cell(raw) == expected


def test_csv_line_uses_crlf() -> None:
    assert dps_proxy._csv_line(["a", "b"]) == '"a","b"\r\n'


@pytest.mark.asyncio
async def test_stream_export_emits_bom_and_pages(monkeypatch) -> None:
    pages = {
        1: {"data": {"items": [{"person_id": "p1", "name": "张三"}], "total": 200}},
        2: {"data": {"items": [{"person_id": "p2", "name": "李四"}], "total": 200}},
    }

    async def fake_fetch(path, params, headers):
        return pages[params["page"]]

    monkeypatch.setattr(dps_proxy, "_fetch_upstream_json", fake_fetch)

    chunks = [
        chunk
        async for chunk in dps_proxy._stream_export(
            "/api/v2/portrait/list",
            {},
            {},
            ("person_id", "name"),
            dps_proxy._portrait_value,
        )
    ]
    assert chunks[0].startswith("\ufeff")
    body = "".join(chunks)
    assert '"p1","张三"' in body
    assert '"p2","李四"' in body


def test_candidate_serialize_decodes_fields() -> None:
    row = SimpleNamespace(
        id="c1",
        batch_id="b1",
        adapter_id="a1",
        annotation_template="t1",
        upstream_annotation_id="up1",
        review_status="pending",
        person_id="p1",
        profile_id=None,
        fields_json=json.dumps({"behavior": 1}, ensure_ascii=False),
        created_at=None,
    )
    serialized = candidate_store._serialize(row)
    assert serialized["fields"] == {"behavior": 1}
    assert serialized["review_status"] == "pending"
    assert serialized["created_at"] == ""


@pytest.mark.asyncio
async def test_stream_export_emits_header_only_when_empty(monkeypatch) -> None:
    async def fake_fetch(path, params, headers):
        return {"data": {"items": [], "total": 0}}

    monkeypatch.setattr(dps_proxy, "_fetch_upstream_json", fake_fetch)
    chunks = [
        chunk
        async for chunk in dps_proxy._stream_export(
            "/api/v2/portrait/list", {}, {}, ("person_id",), dps_proxy._portrait_value
        )
    ]
    body = "".join(chunks)
    assert body == "\ufeff" + dps_proxy._csv_line(["person_id"])


@pytest.mark.asyncio
async def test_stream_export_truncates_at_max_rows(monkeypatch) -> None:
    async def fake_fetch(path, params, headers):
        items = [{"person_id": f"p{index}"} for index in range(5)]
        return {"data": {"items": items, "total": 5}}

    monkeypatch.setattr(dps_proxy, "_fetch_upstream_json", fake_fetch)
    monkeypatch.setattr(dps_proxy, "_CSV_MAX_ROWS", 2)
    chunks = [
        chunk
        async for chunk in dps_proxy._stream_export(
            "/api/v2/portrait/list", {}, {}, ("person_id",), dps_proxy._portrait_value
        )
    ]
    body = "".join(chunks)
    assert body.count("\r\n") == 3  # 表头 + 2 行
    assert '"p0"' in body and '"p1"' in body
    assert '"p2"' not in body


@pytest.mark.asyncio
async def test_candidate_save_idempotent_and_tenant_scoped(tmp_path, monkeypatch) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'candidate.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(candidate_store, "get_session_factory", lambda: factory)
    monkeypatch.setattr(candidate_store, "_TABLE_READY", False)

    async def save(tenant_id: str) -> dict:
        return await candidate_store.save_candidate(
            tenant_id=tenant_id,
            operator="tester",
            adapter_id="adapter-1",
            annotation_template="tpl-1",
            upstream_annotation_id="up-1",
            review_status="pending",
            fields={"behavior": 1},
            person_id="p1",
        )

    first = await save("tenant-1")
    again = await save("tenant-1")
    assert again["id"] == first["id"]

    other = await save("tenant-2")
    assert other["id"] != first["id"]

    rows = await candidate_store.list_by_batch("tenant-1", first["batch_id"])
    assert [row["id"] for row in rows] == [first["id"]]
    assert await candidate_store.list_by_batch("tenant-2", first["batch_id"]) == []

    batch_id, latest_rows = await candidate_store.latest_batch("tenant-1")
    assert batch_id == first["batch_id"]
    assert [row["id"] for row in latest_rows] == [first["id"]]

    await engine.dispose()
