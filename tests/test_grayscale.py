"""v1.1.0 灰度验证测试（TD-11-09，BL-112）+ 兼容层测试（TD-11-07）.

覆盖：兼容层字段映射/函数别名、模块版本文件、AI 规则存在性、告警规则文件。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---- 兼容层 ----
def test_compat_field_map():
    """字段映射：旧字段 → openbase 标准字段（未知字段保留）."""
    from openbase.compat import map_fields, register_field_map

    register_field_map("openllm", {"created_time": "created_at"})
    data = map_fields("openllm", {"created_time": 1, "keep_me": 2})
    assert data == {"created_at": 1, "keep_me": 2}
    # 未注册系统 → 原样返回
    assert map_fields("unknown_sys", {"a": 1}) == {"a": 1}


def test_compat_func_alias():
    """函数别名：旧名 → openbase 实现."""
    from openbase.compat import get_alias, register_func_alias

    def _impl():
        return "openbase-impl"

    register_func_alias("openllm", "old_fn", _impl)
    assert get_alias("openllm", "old_fn")() == "openbase-impl"
    assert get_alias("openllm", "missing") is None


def test_compat_rollback_hint():
    """回滚提示可获取."""
    from openbase.compat import rollback_hint

    assert "git revert" in rollback_hint()


# ---- 模块独立版本（TD-11-01） ----
def test_modules_versions_json():
    """versions.json 存在且覆盖全部 11 模块."""
    versions_file = ROOT / "openbase" / "modules" / "versions.json"
    assert versions_file.exists(), "versions.json missing - run scripts/gen_versions.py"
    data = json.loads(versions_file.read_text(encoding="utf-8"))
    modules = data.get("modules", {})
    expected = {
        "auth", "tenant", "audit", "observability", "config", "mcp",
        "org", "dict", "scheduler", "storage", "notify",
    }
    assert expected.issubset(set(modules.keys())), f"missing: {expected - set(modules)}"
    for info in modules.values():
        assert info.get("version"), f"module version missing: {info}"


def test_modules_init_version_present():
    """各模块 __init__.py 含 __version__（独立版本字段）."""
    modules_dir = ROOT / "openbase" / "modules"
    missing = []
    for init in modules_dir.glob("*/__init__.py"):
        if "__version__" not in init.read_text(encoding="utf-8"):
            missing.append(init.parent.name)
    assert not missing, f"modules missing __version__: {missing}"


# ---- AI 规则（TD-11-02） ----
def test_ai_rules_exist():
    """AGENTS.md 与 .cursor/rules 存在."""
    assert (ROOT / "AGENTS.md").exists()
    assert (ROOT / ".cursor" / "rules" / "backend.mdc").exists()


# ---- 告警规则（TD-11-03） ----
def test_alert_rules_exist():
    """告警规则文件存在且含关键规则."""
    rules_file = ROOT / "config" / "alerting" / "alert-rules.yml"
    assert rules_file.exists()
    content = rules_file.read_text(encoding="utf-8")
    assert "APILatencyHigh" in content
    assert "LoginFailureSpike" in content
    assert "ServiceDown" in content


# ---- 多实例 SSE（TD-11-04） ----
def test_redis_subscribe_unavailable(monkeypatch):
    """Redis 不可用时订阅返回 False（单实例本地队列回退）."""
    from openbase.core.cache import redis_client
    from openbase.modules.notify import start_redis_subscriber

    monkeypatch.setattr(redis_client, "get_client", lambda: None)
    assert start_redis_subscriber() is False


def test_redis_subscribe_pattern_started(monkeypatch):
    """subscribe_pattern 启动后台订阅线程并处理 pmessage."""
    import threading

    from openbase.core.cache import redis_client

    handled = []

    class _FakePubSub:
        def psubscribe(self, *a):
            return True

        def listen(self):
            # 返回一条 pmessage 后结束（覆盖 handler 分支）
            return [
                {
                    "type": "subscribe",
                    "data": 1,
                },
                {
                    "type": "pmessage",
                    "channel": "openbase:notify:user:1",
                    "data": '{"user_id": 1, "title": "x"}',
                },
            ]

        def close(self):
            return None

    class _FakeClient:
        def pubsub(self):
            return _FakePubSub()

    def handler(channel, payload):
        handled.append((channel, payload))

    monkeypatch.setattr(redis_client, "get_client", lambda: _FakeClient())
    assert redis_client.subscribe_pattern("openbase:notify:user:*", handler) is True
    threading.Event().wait(0.3)
    assert handled, "pmessage handler should be called"
    assert handled[0][1]["title"] == "x"


def test_redis_subscribe_listen_error_tolerated(monkeypatch):
    """订阅线程 listen 异常时静默终止（不抛出，daemon 线程）."""
    import threading

    from openbase.core.cache import redis_client

    class _FakePubSub:
        def psubscribe(self, *a):
            return True

        def listen(self):
            raise ConnectionError("down")

        def close(self):
            return None

    class _FakeClient:
        def pubsub(self):
            return _FakePubSub()

    monkeypatch.setattr(redis_client, "get_client", lambda: _FakeClient())
    assert redis_client.subscribe_pattern("openbase:notify:user:*", lambda c, p: None) is True
    # 线程在后台运行，异常被捕获；等待短暂时间确认不崩溃
    threading.Event().wait(0.2)


def test_notify_redis_message_handler(monkeypatch):
    """Redis 广播消息处理器：按 user_id 推送到本地 SSE 队列."""
    import asyncio

    from openbase.modules.notify import _redis_message_handler, _subscribers

    # 构造本地订阅者队列
    queue = asyncio.Queue()
    _subscribers.setdefault("user:42", []).append(queue)
    try:
        _redis_message_handler("openbase:notify:user:42", {"user_id": 42, "title": "hi"})
        msg = queue.get_nowait()
        assert '"title": "hi"' in msg
        # 无订阅者/无 user_id 不报错
        _redis_message_handler("openbase:notify:user:99", {})
        _redis_message_handler("x", {})
    finally:
        _subscribers["user:42"].remove(queue)
