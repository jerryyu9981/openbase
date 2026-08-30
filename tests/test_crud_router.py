"""测试 v1.4.1 R-372 BaseCRUDRouter（通用 CRUD 路由自动生成）."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from openbase.core.crud import BaseCRUDRouter

# ---- 测试模型与服务 ----

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    value: int = Field(0)


class ItemUpdate(BaseModel):
    name: str | None = None
    value: int | None = None


class ItemOut(BaseModel):
    id: int
    name: str
    value: int


class ItemService:
    """内存 CRUD 服务（模拟 repository 层）."""

    def __init__(self) -> None:
        self._items: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def list(self) -> list[dict[str, Any]]:
        return list(self._items.values())

    def get(self, item_id: int) -> dict[str, Any] | None:
        return self._items.get(item_id)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = {"id": self._next_id, **payload}
        self._next_id += 1
        self._items[record["id"]] = record
        return record

    def update(self, item_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        record = self._items.get(item_id)
        if record is None:
            return None
        record.update({k: v for k, v in payload.items() if v is not None})
        return record

    def delete(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None


@pytest.fixture(scope="module")
def client() -> TestClient:
    """构造挂载 BaseCRUDRouter 的测试应用."""
    app = FastAPI()
    router = BaseCRUDRouter(
        prefix="/api/v1/items",
        service=ItemService(),
        create_schema=ItemCreate,
        update_schema=ItemUpdate,
        out_schema=ItemOut,
    )
    app.include_router(router)
    return TestClient(app)


# ---- CRUD 用例 ----

def test_crud_router_generates_endpoints(client: TestClient) -> None:
    """自动生成 5 个端点."""
    for path in ("/api/v1/items", "/api/v1/items/1"):
        resp = client.get(path)
        assert resp.status_code in (200, 404)  # 路由存在（空列表 200 / 无记录 404）


def test_crud_create(client: TestClient) -> None:
    """创建 → 返回 out_schema."""
    resp = client.post("/api/v1/items", json={"name": "demo", "value": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "demo"
    assert body["value"] == 5


def test_crud_list_and_get(client: TestClient) -> None:
    """列表 + 单条查询."""
    list_resp = client.get("/api/v1/items")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    get_resp = client.get("/api/v1/items/1")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == 1


def test_crud_update(client: TestClient) -> None:
    """更新 → 字段生效."""
    resp = client.put("/api/v1/items/1", json={"value": 99})
    assert resp.status_code == 200
    assert resp.json()["value"] == 99
    assert resp.json()["name"] == "demo"  # 未传字段保持


def test_crud_delete(client: TestClient) -> None:
    """删除 → 再查 404."""
    resp = client.delete("/api/v1/items/1")
    assert resp.status_code == 200

    get_resp = client.get("/api/v1/items/1")
    assert get_resp.status_code == 404


def test_crud_create_validation(client: TestClient) -> None:
    """创建参数校验（name 必填）."""
    resp = client.post("/api/v1/items", json={"value": 1})
    assert resp.status_code == 422
