"""org / dict / storage / notify 模块分支补测（覆盖率治理）.

补齐范围：
- org：父子路径计算、部门树、DB 异常全端点内存回退；
- dict：类型幂等创建、隐式建类型、缓存命中、删除 404/409、全端点内存回退；
- storage：本地后端读取、S3 客户端懒加载、删除不存在记录、全端点内存回退；
- notify：SSE 本地发布、流生成器取消、Redis 订阅处理器、已读 404、全端点内存回退。

数据落库（SQLite 临时文件库），不依赖外部 PostgreSQL；路由以裸 FastAPI 挂载，
不经过鉴权中间件（本文件聚焦模块内部分支）。
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import types
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from openbase.core.db.session import get_engine, get_session_factory, init_db
from openbase.core.errors import install_exception_handlers
from openbase.core.models import Base
from openbase.modules import dict as dict_module
from openbase.modules import notify as notify_module
from openbase.modules import org as org_module
from openbase.modules import storage as storage_module
from openbase.modules.dict import DictService
from openbase.modules.notify import NotificationService
from openbase.modules.org import DepartmentService
from openbase.modules.storage import FileService, LocalStorageBackend, S3StorageBackend

_DB_PATH = Path(tempfile.gettempdir()) / "openbase_test_module_fallbacks.db"
_session_factory: async_sessionmaker | None = None


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _build_client() -> TestClient:
    global _session_factory

    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    init_db(f"sqlite+aiosqlite:///{_DB_PATH}", schema=None)
    _session_factory = get_session_factory()

    async def _create_tables() -> None:
        async with get_engine().begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    app = FastAPI()
    install_exception_handlers(app)
    for module_router in (
        org_module.router,
        dict_module.router,
        storage_module.router,
        notify_module.router,
    ):
        app.include_router(module_router)
    return TestClient(app)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """模块级应用装配 + 全局 DB 工厂硬隔离（同 test_users_admin 口径）."""
    global _session_factory

    from conftest import reset_db_singletons

    import openbase.core.db.session as session_module

    test_client = _build_client()
    assert _session_factory is not None
    patch = pytest.MonkeyPatch()
    patch.setattr(session_module, "get_session_factory", lambda: _session_factory)
    try:
        yield test_client
    finally:
        patch.undo()
        reset_db_singletons()


def _run_sql(statement: str, params: dict | None = None) -> None:
    """在专用库执行写语句（构造孤儿行等边界数据）."""
    from sqlalchemy import text

    async def _run() -> None:
        assert _session_factory is not None
        async with _session_factory() as session:  # type: ignore[call-arg]
            await session.execute(text(statement), params or {})
            await session.commit()

    asyncio.run(_run())


def _raise(*args, **kwargs):
    raise RuntimeError("db unavailable")


# ---- org ----


def test_org_db_path_covers_tree_and_missing_parent(client: TestClient) -> None:
    """DB 主路径：父部门 + 子部门树 + 不存在父节点（前缀为空）+ 删除幂等."""
    parent = client.post("/api/v1/org/departments", json={"name": "研发部"}).json()
    child = client.post(
        "/api/v1/org/departments",
        json={"name": "后端组", "parent_id": parent["id"]},
    ).json()
    assert child["path"] == f"/{parent['id']}/{child['id']}"

    # 父节点不存在 → 不取前缀，仅自身 id
    orphan = client.post(
        "/api/v1/org/departments",
        json={"name": "孤立组", "parent_id": 999999},
    ).json()
    assert orphan["path"] == f"/{orphan['id']}"

    listing = client.get("/api/v1/org/departments").json()
    assert {row["id"] for row in listing} >= {parent["id"], child["id"]}

    tree = client.get("/api/v1/org/departments/tree").json()
    root = next(node for node in tree if node["id"] == parent["id"])
    assert any(node["id"] == child["id"] for node in root["children"])

    # 删除存在部门 → 真实删除路径
    assert client.delete(f"/api/v1/org/departments/{orphan['id']}").json() == {
        "deleted": orphan["id"]
    }
    # 删除不存在部门 → 幂等成功
    assert client.delete("/api/v1/org/departments/999999").json() == {"deleted": 999999}


def test_org_memory_fallback_all_endpoints(client: TestClient, monkeypatch) -> None:
    """DB 异常 → 创建（含父子路径）/列表/树/删除全部回退内存."""
    org_module._memory_departments.clear()
    org_module._next_id = 1
    for name in ("create", "list_all", "delete"):
        monkeypatch.setattr(DepartmentService, name, classmethod(_raise))

    former = client.post("/api/v1/org/departments", json={"name": "内存母公司"}).json()
    assert former["path"] == "/1"
    junior = client.post(
        "/api/v1/org/departments",
        json={"name": "内存子公司", "parent_id": former["id"]},
    ).json()
    assert junior["path"] == "/1/2"
    # 父节点不在内存存储 → 回退为单层路径
    lonely = client.post(
        "/api/v1/org/departments",
        json={"name": "内存孤立部", "parent_id": 12345},
    ).json()
    assert lonely["path"] == f"/{lonely['id']}"

    rows = client.get("/api/v1/org/departments").json()
    assert len(rows) == 3

    tree = client.get("/api/v1/org/departments/tree").json()
    # 两个根：内存母公司（含子节点）与父节点缺失的孤立部门
    assert len(tree) == 2
    parent_node = next(node for node in tree if node["id"] == former["id"])
    assert parent_node["children"][0]["id"] == junior["id"]

    assert client.delete(f"/api/v1/org/departments/{junior['id']}").json() == {
        "deleted": junior["id"]
    }
    org_module._memory_departments.clear()


# ---- dict ----


def test_dict_db_path_branches(client: TestClient, monkeypatch) -> None:
    """DB 主路径：类型幂等创建、隐式建类型、缓存命中、未知类型、删除边界."""
    code = _unique("dict")
    first = client.post("/api/v1/dicts", json={"code": code, "name": "字典"}).json()
    twice = client.post("/api/v1/dicts", json={"code": code, "name": "字典改名"}).json()
    assert first["code"] == twice["code"]

    # 类型不存在时创建字典项 → 隐式建类型
    implicit_code = _unique("implicit")
    item = client.post(
        f"/api/v1/dicts/{implicit_code}/items",
        json={"label": "甲", "value": "a", "sort_order": 1},
    ).json()
    assert item["value"] == "a"
    # 同类型再建一项（类型已存在分支）
    second_item = client.post(
        f"/api/v1/dicts/{implicit_code}/items",
        json={"label": "丁", "value": "d", "sort_order": 0},
    ).json()
    assert second_item["id"] != item["id"]

    # 类型列表（DB 路径）与字典项列表（缓存未命中 → 查库并按 sort_order 排序）
    assert any(row["code"] == implicit_code for row in client.get("/api/v1/dicts").json())
    assert [row["value"] for row in client.get(f"/api/v1/dicts/{implicit_code}/items").json()] == [
        "d",
        "a",
    ]

    # 未知类型 → 空列表
    assert client.get(f"/api/v1/dicts/{_unique('ghost')}/items").json() == []

    # 删除不存在字典项 → 幂等
    assert client.delete("/api/v1/dicts/items/999999").json() == {"deleted": 999999}

    # 类型不存在 → 404；存在字典项 → 409
    assert client.delete(f"/api/v1/dicts/{_unique('absent')}").status_code == 404
    blocked = client.delete(f"/api/v1/dicts/{implicit_code}")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "BIZ_CONFLICT"

    # 删除字典项后类型可删（缓存失效分支）
    assert client.delete(f"/api/v1/dicts/items/{item['id']}").json() == {
        "deleted": item["id"]
    }
    assert client.delete(f"/api/v1/dicts/items/{second_item['id']}").json() == {
        "deleted": second_item["id"]
    }
    removed = client.delete(f"/api/v1/dicts/{implicit_code}")
    assert removed.status_code == 200
    assert removed.json()["deleted"] is True

    # 缓存命中：直接返回缓存内容，不读库
    import openbase.core.cache.redis_client as redis_client

    cached_payload = [{"id": 1, "label": "缓存", "value": "c", "sort_order": 0}]
    monkeypatch.setattr(redis_client, "cache_get", lambda key: cached_payload)
    assert client.get(f"/api/v1/dicts/{code}/items").json() == cached_payload


def test_dict_delete_item_with_orphan_type(client: TestClient) -> None:
    """字典项所属类型行缺失 → 删除项跳过缓存失效（孤儿数据边界）."""
    code = _unique("orphan")
    created = client.post(
        f"/api/v1/dicts/{code}/items",
        json={"label": "乙", "value": "b", "sort_order": 0},
    ).json()
    _run_sql("DELETE FROM dict_types WHERE code = :code", {"code": code})
    assert client.delete(f"/api/v1/dicts/items/{created['id']}").json() == {
        "deleted": created["id"]
    }


def test_dict_memory_fallback_all_endpoints(client: TestClient, monkeypatch) -> None:
    """DB 异常 → 字典类型/项全部端点回退内存，业务错误（404/409）不被吞."""
    dict_module._memory_types.clear()
    dict_module._memory_items.clear()
    dict_module._next_item_id = 1
    for name in (
        "create_type",
        "list_types",
        "create_item",
        "list_items",
        "delete_item",
        "delete_type",
    ):
        monkeypatch.setattr(DictService, name, classmethod(_raise))

    code = _unique("mem")
    created = client.post("/api/v1/dicts", json={"code": code, "name": "内存字典"}).json()
    assert created["code"] == code
    assert any(row["code"] == code for row in client.get("/api/v1/dicts").json())

    item = client.post(
        f"/api/v1/dicts/{code}/items",
        json={"label": "丙", "value": "c", "sort_order": 2},
    ).json()
    assert client.get(f"/api/v1/dicts/{code}/items").json()[0]["id"] == item["id"]

    # 内存类型存在项 → 409；不存在 → 404
    conflict = client.delete(f"/api/v1/dicts/{code}")
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "BIZ_CONFLICT"
    assert client.delete(f"/api/v1/dicts/{_unique('mem-absent')}").status_code == 404

    assert client.delete(f"/api/v1/dicts/items/{item['id']}").json() == {
        "deleted": item["id"]
    }
    assert client.delete(f"/api/v1/dicts/{code}").json() == {"code": code, "deleted": True}
    assert client.get(f"/api/v1/dicts/{code}/items").json() == []
    dict_module._memory_types.clear()
    dict_module._memory_items.clear()


def test_dict_fallback_exception_branch(client: TestClient, monkeypatch) -> None:
    """非 BaseError 异常（DB 不可用）仍走内存回退（delete_type 的 except Exception）."""
    dict_module._memory_types.clear()
    dict_module._memory_items.clear()
    monkeypatch.setattr(DictService, "delete_type", classmethod(_raise))
    dict_module._memory_types[_unique("noop")] = {"code": "noop", "name": "占位"}
    code = next(iter(dict_module._memory_types))
    dict_module._memory_items[code] = []
    assert client.delete(f"/api/v1/dicts/{code}").json() == {"code": code, "deleted": True}
    dict_module._memory_types.clear()


# ---- storage ----


def test_storage_local_load_and_missing_delete(client: TestClient, tmp_path) -> None:
    """本地后端读取落盘内容；删除不存在记录不触发存储删除."""
    backend = LocalStorageBackend(str(tmp_path))
    storage_module._backend = backend
    try:
        uploaded = client.post(
            "/api/v1/files",
            files={"file": ("note.txt", b"hello-storage", "text/plain")},
        ).json()
        assert uploaded["size"] == len(b"hello-storage")
        assert backend.load(uploaded["storage_path"]) == b"hello-storage"

        assert client.delete("/api/v1/files/999999").json() == {"deleted": 999999}
    finally:
        storage_module._backend = None


def test_storage_memory_fallback_all_endpoints(
    client: TestClient, monkeypatch, tmp_path
) -> None:
    """DB 异常 → 上传/列表/详情/删除回退内存；缺失详情 → 404."""
    storage_module._records.clear()
    storage_module._next_id = 1
    storage_module._backend = LocalStorageBackend(str(tmp_path / "fallback"))
    for name in ("create", "get", "list_all", "delete"):
        monkeypatch.setattr(FileService, name, classmethod(_raise))

    try:
        uploaded = client.post(
            "/api/v1/files",
            files={"file": ("mem.txt", b"payload", "text/plain")},
        ).json()
        assert uploaded["backend"] == "local"

        listing = client.get("/api/v1/files").json()
        assert [row["id"] for row in listing] == [uploaded["id"]]

        detail = client.get(f"/api/v1/files/{uploaded['id']}")
        assert detail.status_code == 200
        assert detail.json()["file_name"] == "mem.txt"

        missing = client.get("/api/v1/files/999999")
        assert missing.status_code == 404
        assert missing.json()["code"] == "STORAGE_404"

        assert client.delete(f"/api/v1/files/{uploaded['id']}").json() == {
            "deleted": uploaded["id"]
        }
        assert client.get("/api/v1/files").json() == []
    finally:
        storage_module._backend = None
        storage_module._records.clear()


def test_storage_s3_client_lazy_loading(monkeypatch) -> None:
    """S3 适配器 boto3 客户端懒加载并缓存（s3v4 签名 + 超时配置）."""
    created: dict = {}

    class _FakeClient:
        pass

    fake_boto3 = types.ModuleType("boto3")

    def _client(service: str, **kwargs):
        created["service"] = service
        created.update(kwargs)
        return _FakeClient()

    fake_boto3.client = _client  # type: ignore[attr-defined]

    class _Config:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    fake_config_module = types.ModuleType("botocore.config")
    fake_config_module.Config = _Config  # type: ignore[attr-defined]
    fake_botocore = types.ModuleType("botocore")
    fake_botocore.config = fake_config_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_config_module)

    backend = S3StorageBackend(endpoint="http://minio:9000", bucket="bucket-a")
    client_instance = backend.client
    assert isinstance(client_instance, _FakeClient)
    assert backend.client is client_instance  # 二次访问命中缓存
    assert created["service"] == "s3"
    assert created["endpoint_url"] == "http://minio:9000"
    assert created["config"].kwargs["signature_version"] == "s3v4"


# ---- notify ----


def test_notify_db_path_and_missing_read(client: TestClient) -> None:
    """DB 主路径：创建/列表/已读/全部已读；不存在的通知 → 404."""
    created = client.post(
        "/api/v1/notifications",
        json={"user_id": 1001, "title": "站内信", "content": "正文", "type": 1},
    ).json()
    rows = client.get("/api/v1/notifications?user_id=1001").json()
    assert [row["id"] for row in rows] == [created["id"]]

    read = client.post(f"/api/v1/notifications/{created['id']}/read").json()
    assert read["is_read"] is True
    assert client.post("/api/v1/notifications/read-all?user_id=1001").json() == {
        "read_all": True
    }

    missing = client.post("/api/v1/notifications/999999/read")
    assert missing.status_code == 404
    assert missing.json()["code"] == "PARAM_404"


def test_notify_publish_and_stream_generator() -> None:
    """本地订阅者收到 publish 消息；SSE 生成器首帧 + 取消清理订阅."""
    async def _run() -> None:
        notify_module._subscribers.clear()
        queue: asyncio.Queue = asyncio.Queue()
        notify_module._subscribers["user:42"] = [queue]
        await notify_module.publish("user:42", {"user_id": 42, "title": "推送"})
        assert json.loads(queue.get_nowait())["title"] == "推送"

        notify_module._subscribers.clear()
        response = await notify_module.stream(77)
        iterator = response.body_iterator
        assert await iterator.__anext__() == ": connected\n\n"
        await notify_module.publish("user:77", {"user_id": 77, "title": "流消息"})
        chunk = await iterator.__anext__()
        assert chunk.startswith("data: ")
        with pytest.raises(asyncio.CancelledError):
            await iterator.athrow(asyncio.CancelledError)
        assert notify_module._subscribers.get("user:77") == []
        notify_module._subscribers.clear()

    asyncio.run(_run())


def test_notify_redis_message_handler_paths() -> None:
    """Redis 广播处理器：缺 user_id 忽略；正常入队；队列异常仅调试日志."""
    notify_module._subscribers.clear()
    notify_module._redis_message_handler("openbase:notify:user:5", {})
    assert notify_module._subscribers == {}

    queue: asyncio.Queue = asyncio.Queue()
    notify_module._subscribers["user:5"] = [queue]
    notify_module._redis_message_handler(
        "openbase:notify:user:5", {"user_id": 5, "title": "广播"}
    )
    assert json.loads(queue.get_nowait())["title"] == "广播"

    class _BrokenQueue:
        def put_nowait(self, message: str) -> None:
            raise RuntimeError("queue closed")

    notify_module._subscribers["user:6"] = [_BrokenQueue()]  # type: ignore[list-item]
    notify_module._redis_message_handler("openbase:notify:user:6", {"user_id": 6})
    notify_module._subscribers.clear()


def test_notify_memory_fallback_all_endpoints(client: TestClient, monkeypatch) -> None:
    """DB 异常 → 创建（含 SSE 推送）/列表/已读/全部已读回退内存."""
    notify_module._notifications.clear()
    notify_module._next_id = 1
    notify_module._subscribers.clear()
    for name in ("create", "list_by_user", "mark_read", "mark_all_read"):
        monkeypatch.setattr(NotificationService, name, classmethod(_raise))

    queue: asyncio.Queue = asyncio.Queue()
    notify_module._subscribers["user:2002"] = [queue]

    created = client.post(
        "/api/v1/notifications",
        json={"user_id": 2002, "title": "SSE 通知", "content": None, "type": 2},
    ).json()
    assert created["type"] == 2
    assert json.loads(queue.get_nowait())["title"] == "SSE 通知"

    rows = client.get("/api/v1/notifications?user_id=2002").json()
    assert [row["id"] for row in rows] == [created["id"]]

    assert client.post(f"/api/v1/notifications/{created['id']}/read").json()["is_read"] is True
    assert client.post("/api/v1/notifications/read-all?user_id=2002").json() == {
        "read_all": True
    }
    assert client.post("/api/v1/notifications/999999/read").status_code == 404

    notify_module._notifications.clear()
    notify_module._subscribers.clear()
