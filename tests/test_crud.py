"""BaseCRUDRouter 通用 CRUD 生成测试."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from openbase.crud import BaseCRUDRouter


class BookCreate(BaseModel):
    name: str


class BookOut(BaseModel):
    id: int
    name: str


def _build_client() -> TestClient:
    from openbase.core.errors import install_exception_handlers

    app = FastAPI()
    install_exception_handlers(app)
    store: dict[int, dict] = {}
    router = BaseCRUDRouter(
        prefix="/api/v1/books",
        create_schema=BookCreate,
        out_schema=BookOut,
        store=store,
        search_fields=["name"],
        require_auth=False,
    )
    app.include_router(router)
    return TestClient(app)


def test_crud_list_create():
    client = _build_client()
    r = client.post("/api/v1/books", json={"name": "设计模式"})
    assert r.status_code == 200
    assert r.json()["id"] == 1
    r2 = client.post("/api/v1/books", json={"name": "重构"})
    assert r2.status_code == 200
    lst = client.get("/api/v1/books").json()
    assert lst["total"] == 2


def test_crud_search_and_pagination():
    client = _build_client()
    for name in ("a1", "a2", "b1"):
        client.post("/api/v1/books", json={"name": name})
    search = client.get("/api/v1/books?search=a&page=1&page_size=10").json()
    assert search["total"] == 2
    page = client.get("/api/v1/books?page=1&page_size=2").json()
    assert len(page["items"]) == 2
    assert page["total"] == 3


def test_crud_get_update_delete():
    client = _build_client()
    created = client.post("/api/v1/books", json={"name": "x"}).json()
    book_id = created["id"]
    detail = client.get(f"/api/v1/books/{book_id}")
    assert detail.status_code == 200
    updated = client.put(f"/api/v1/books/{book_id}", json={"name": "y"})
    assert updated.json()["name"] == "y"
    deleted = client.delete(f"/api/v1/books/{book_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/books/{book_id}").status_code == 404


def test_crud_404_on_missing():
    client = _build_client()
    resp = client.get("/api/v1/books/999")
    assert resp.status_code == 404
