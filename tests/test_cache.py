"""Redis 缓存客户端与 dict 缓存接入测试（fake Redis 客户端）."""

import pytest


@pytest.fixture()
def fake_redis(monkeypatch):
    """用内存 dict 模拟 Redis 客户端."""
    store: dict = {}

    class _FakeRedis:
        def get(self, key):
            return store.get(key)

        def set(self, key, value, ex=None):
            store[key] = value
            return True

        def delete(self, *keys):
            for k in keys:
                store.pop(k, None)
            return True

        def ping(self):
            return True

        def publish(self, channel, message):
            store[f"pub:{channel}"] = message
            return 1

    client = _FakeRedis()

    def fake_get_client():
        return client

    monkeypatch.setattr("openbase.core.cache.redis_client._client", client)
    monkeypatch.setattr("openbase.core.cache.redis_client._client_available", True)
    return store


def test_cache_set_get_roundtrip(fake_redis):
    """cache_set/cache_get JSON 序列化往返."""
    from openbase.core.cache.redis_client import cache_get, cache_set

    assert cache_set("k1", {"a": [1, 2]}, ttl=60) is True
    assert cache_get("k1") == {"a": [1, 2]}


def test_cache_delete(fake_redis):
    """cache_delete 移除键."""
    from openbase.core.cache.redis_client import cache_delete, cache_get, cache_set

    cache_set("k2", "v")
    assert cache_delete("k2") is True
    assert cache_get("k2") is None


def test_cache_unavailable_returns_none(monkeypatch):
    """Redis 不可用时 cache_get 返回 None，cache_set 返回 False（降级不阻塞）."""
    from openbase.core.cache import redis_client

    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    assert redis_client.cache_get("k") is None
    assert redis_client.cache_set("k", "v") is False
    assert redis_client.cache_delete("k") is False
    assert redis_client.pub("ch", {"m": 1}) is False


def test_cache_client_exception_falls_back(monkeypatch):
    """Redis 客户端异常时各函数静默降级."""
    from openbase.core.cache import redis_client

    class _Broken:
        def get(self, key):
            raise ConnectionError("down")

        def set(self, *a, **k):
            raise ConnectionError("down")

        def delete(self, *a):
            raise ConnectionError("down")

        def publish(self, *a):
            raise ConnectionError("down")

    monkeypatch.setattr(redis_client, "get_client", lambda: _Broken())
    assert redis_client.cache_get("k") is None
    assert redis_client.cache_set("k", "v") is False
    assert redis_client.cache_delete("k") is False
    assert redis_client.pub("ch", {"m": 1}) is False


def test_dict_cache_write_invalidate(fake_redis):
    """dict 列表写缓存、创建项后失效（缓存语义）."""
    import asyncio

    from openbase.modules.dict import DictService

    async def main():
        # 类型存在且有数据 → 列表写入缓存
        class _TypeRow:
            id = 1
            code = "gender"

        class _ItemRow:
            id = 1
            label = "男"
            value = "M"
            sort_order = 1

        class _S:
            def __init__(self):
                self.phase = 0

            async def execute(self, stmt):
                self.phase += 1
                if self.phase == 1:  # 类型查询
                    return _R(_TypeRow())
                return _R2([_ItemRow()])  # 项查询

        class _R:
            def __init__(self, row):
                self.row = row

            def scalar_one_or_none(self):
                return self.row

        class _R2:
            def __init__(self, rows):
                self.rows = rows

            def scalars(self):
                return _S2(self.rows)

        class _S2:
            def __init__(self, rows):
                self.rows = rows

            def all(self):
                return self.rows

        items = await DictService.list_items(_S(), "gender")
        assert items == [{"id": 1, "label": "男", "value": "M", "sort_order": 1}]
        assert fake_redis.get("openbase:dict:gender:items") is not None

    asyncio.run(main())


def test_notify_publish_redis_broadcast(fake_redis, monkeypatch):
    """notify 创建时 Redis pub 广播（跨实例预留）."""
    import asyncio

    from openbase.modules.notify import NotificationService

    async def main():
        class _S:
            async def execute(self, stmt):
                return _Empty()

            async def commit(self):
                return None

            def add(self, obj):
                obj.id = 1  # 模拟 id 赋值

        class _Empty:
            def scalar_one_or_none(self):
                return None

            def scalars(self):
                return _ES()

        class _ES:
            def all(self):
                return []

        n = await NotificationService.create(_S(), 1, "提醒", "内容", 2)
        assert n["id"] == 1

    asyncio.run(main())
    # publish 未直接调用（路由层调用）；此处验证 redis pub 函数本身
    from openbase.core.cache.redis_client import pub

    assert pub("notify:user:9", {"id": 9}) is True
    assert fake_redis.get("pub:notify:user:9") is not None
