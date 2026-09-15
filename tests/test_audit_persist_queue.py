"""审计落库异步化（TT-056 性能整改）——TDD：先 RED，后实现.

整改依据（实测，见 ``doc/test/evidence/manual/t4-perf-tt056-verdict.json``）：
- 审计落库 ``INSERT+COMMIT`` = **6.43 ms/行**（p95 8.37ms），代理请求落 2 行
  （``api.request`` + ``proxy.outbound``）→ 请求路径内**同步 await ≈12.9 ms**；
- 方案 §6 要求「日志写入不阻塞主请求；P99 增量 < 5ms」→ 严格口径未达标；
- 整改口径：请求路径**零 await DB**（改为进程内队列提交，µs 级），由 writer 协程
  **批量单次提交**落库；保留「尽力留痕 + 失败降级不阻断 + 既有 WARN 文案」语义。

测试策略：DB 用「记录型假会话」（确定性、免外部依赖），与
``tests/test_audit_db_persist.py`` 同法；请求路径零等待用 TestClient + 慢写桩验证。
"""

from __future__ import annotations

import asyncio
import logging

import pytest
from starlette.requests import Request as StarletteRequest

from openbase.modules.audit import (
    ACTION_API_REQUEST,
    ENV_AUDIT_DB_PERSIST,
    APICallRecord,
    AuditMiddleware,
    AuditPersistQueue,
    audit_persist_queue,
)


class _RecordingSession:
    """记录 add/commit/rollback 的假会话（含 commit 计数，用于验证批量化）."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commit_count = 0
        self.rolled_back = False

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rolled_back = True

    @property
    def committed(self) -> bool:
        return self.commit_count > 0


class _FailingSession(_RecordingSession):
    async def commit(self) -> None:
        raise RuntimeError("db down")


def _patch_session_factory(monkeypatch: pytest.MonkeyPatch, session: object) -> None:
    import importlib

    session_mod = importlib.import_module("openbase.core.db.session")

    class _SessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc: object) -> bool:
            return False

    class _FakeFactory:
        def __call__(self) -> _SessionCM:
            return _SessionCM()

    monkeypatch.setattr(session_mod, "get_session_factory", lambda: _FakeFactory())


def _payload(request_id: str = "req-queue-1") -> dict:
    return {
        "request_id": request_id,
        "operator_id": "42",
        "method": "GET",
        "path": "/api/v1/dps-proxy/portraits",
        "status_code": 200,
        "duration_ms": 12,
        "ip_address": "127.0.0.1",
        "user_agent": "pytest",
        "detail": {"case_id": "UI-DPS-0007", "step_id": 3, "run_id": "run-queue"},
    }


# ---------------------------------------------------------------------------
# 1) 提交侧：同步、零 DB
# ---------------------------------------------------------------------------


def test_submit_does_not_touch_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """``submit`` 只入队：即使在 DB 不可用时也不访问 DB（请求路径零 await）。"""
    import importlib

    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session_mod = importlib.import_module("openbase.core.db.session")

    def _boom() -> None:
        raise AssertionError("submit 阶段不得访问 DB")

    monkeypatch.setattr(session_mod, "get_session_factory", _boom)
    queue = AuditPersistQueue()

    async def _run() -> bool:
        return queue.submit("api_request", _payload())

    assert asyncio.run(_run()) is True
    assert queue.stats()["pending"] == 1


# ---------------------------------------------------------------------------
# 2) 落库侧：批量单次提交
# ---------------------------------------------------------------------------


def test_drain_once_persists_batch_in_single_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """3 条入队 → 一次 drain 落库：3 行 + **仅 1 次 commit**（批量提交）。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)
    queue = AuditPersistQueue()

    async def _run() -> int:
        for i in range(3):
            queue.submit("api_request", _payload(f"req-queue-{i}"))
        return await queue.drain_once()

    drained = asyncio.run(_run())
    assert drained == 3
    assert len(session.added) == 3
    assert session.commit_count == 1
    assert session.added[0].action == ACTION_API_REQUEST
    assert session.added[0].detail["case_id"] == "UI-DPS-0007"


def test_writer_task_persists_queued_records(monkeypatch: pytest.MonkeyPatch) -> None:
    """writer 协程路径（生产实际路径）：``start()`` 后入队即由后台任务批量落库。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)
    queue = AuditPersistQueue()

    async def _run() -> None:
        queue.start()
        started = queue.stats()["writer_running"]
        assert started == 1
        for i in range(3):
            queue.submit("api_request", _payload(f"req-w{i}"))
        for _ in range(100):
            if session.commit_count:
                break
            await asyncio.sleep(0.01)
        await queue.stop()

    asyncio.run(_run())
    assert session.commit_count >= 1, "writer 协程未落库"
    assert len(session.added) == 3
    assert queue.stats()["pending"] == 0
    assert queue.stats()["writer_running"] == 0


def test_start_is_idempotent_and_stop_on_idle_queue() -> None:
    """``start`` 幂等（重复调用不新建任务）；空闲队列 ``stop`` 安全排空。"""
    queue = AuditPersistQueue()

    async def _run() -> tuple[int, int]:
        queue.start()
        first = queue.stats()["writer_running"]
        queue.start()  # 幂等：不应新建第二个 writer
        second = queue.stats()["writer_running"]
        await queue.stop()
        return first, second

    first, second = asyncio.run(_run())
    assert first == 1 and second == 1
    assert queue.stats()["writer_running"] == 0
    assert queue.stats()["pending"] == 0


def test_stop_without_start_is_safe() -> None:
    """未启动 writer 时 ``stop`` 直接排空（task None 分支），不抛出。"""
    queue = AuditPersistQueue()
    asyncio.run(queue.stop())
    assert queue.stats()["pending"] == 0


def test_write_batch_records_edge_paths(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """批量写库边界：开关关闭 / 未知 kind / 出站审计失败降级（含回滚、不抛出到调用方之外）."""
    import importlib

    audit_mod = importlib.import_module("openbase.modules.audit")

    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "0")
    assert asyncio.run(audit_mod._write_batch_records([("api_request", _payload())])) == 0

    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    assert asyncio.run(audit_mod._write_batch_records([("unknown-kind", _payload())])) == 0

    session = _FailingSession()
    _patch_session_factory(monkeypatch, session)
    hop = {
        "identity": {"principal": {"subject_id": 7}},
        "system": "dps",
        "method": "GET",
        "path": "/api/v1/dps-proxy/portraits",
        "request_id": "req-hop-1",
    }
    with caplog.at_level(logging.WARNING, logger="openbase.audit"):
        with pytest.raises(RuntimeError):
            asyncio.run(audit_mod._write_batch_records([("proxy_hop", hop)]))
    assert session.rolled_back is True
    assert any(
        "proxy outbound audit persist failed (degraded)" in rec.message for rec in caplog.records
    )


# ---------------------------------------------------------------------------
# 3) 队列满：丢弃 + WARN，不抛出
# ---------------------------------------------------------------------------


def test_queue_full_drops_with_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    queue = AuditPersistQueue(maxsize=1)

    async def _run() -> tuple[bool, bool]:
        first = queue.submit("api_request", _payload("req-a"))
        second = queue.submit("api_request", _payload("req-b"))
        return first, second

    with caplog.at_level(logging.WARNING, logger="openbase.audit"):
        first, second = asyncio.run(_run())
    assert first is True and second is False
    assert queue.stats()["dropped"] == 1
    assert any("audit persist queue full" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# 4) 落库失败：降级 WARN，不抛出（保留既有语义与文案）
# ---------------------------------------------------------------------------


def test_write_failure_degrades_without_raising(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _FailingSession()
    _patch_session_factory(monkeypatch, session)
    queue = AuditPersistQueue()

    async def _run() -> int:
        queue.submit("api_request", _payload())
        return await queue.drain_once()

    with caplog.at_level(logging.WARNING, logger="openbase.audit"):
        drained = asyncio.run(_run())
    assert drained == 1
    assert queue.stats()["failed"] == 1
    assert session.rolled_back is True
    assert any("audit db persist failed (degraded)" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# 5) 停止：排空在途记录（不丢最近审计行）
# ---------------------------------------------------------------------------


def test_stop_drains_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)
    queue = AuditPersistQueue()

    async def _run() -> None:
        queue.submit("api_request", _payload("req-s1"))
        queue.submit("api_request", _payload("req-s2"))
        await queue.stop()

    asyncio.run(_run())
    assert len(session.added) == 2
    assert session.committed is True
    assert queue.stats()["pending"] == 0


# ---------------------------------------------------------------------------
# 6) 开关关闭：完全不落库（保持既有开关语义）
# ---------------------------------------------------------------------------


def test_persist_disabled_env_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "0")
    import importlib

    session_mod = importlib.import_module("openbase.core.db.session")

    def _boom() -> None:
        raise AssertionError("开关关闭时不得访问 DB")

    monkeypatch.setattr(session_mod, "get_session_factory", _boom)
    queue = AuditPersistQueue()

    async def _run() -> int:
        queue.submit("api_request", _payload())
        return await queue.drain_once()

    assert asyncio.run(_run()) == 0


# ---------------------------------------------------------------------------
# 7) 中间件接线：落库从「请求内同步」改为「入队后异步」
# ---------------------------------------------------------------------------


def _scope() -> dict:
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/dps-proxy/portraits",
        "raw_path": b"/api/v1/dps-proxy/portraits",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }


def _sample_record() -> APICallRecord:
    return APICallRecord(
        method="GET",
        path="/api/v1/dps-proxy/portraits",
        status_code=200,
        duration_ms=12,
        request_id="req-queue-1",
        operator_id="42",
        tenant_id="acme",
        ip_address="127.0.0.1",
        user_agent="pytest",
        extra={"case_id": "UI-DPS-0007", "step_id": 3, "run_id": "run-queue", "channel": "B"},
    )


def test_middleware_defers_write_to_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    """中间件调用后**不立即落库**（请求路径零 await DB）；drain 后才写库。"""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    session = _RecordingSession()
    _patch_session_factory(monkeypatch, session)
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = StarletteRequest(_scope())
    request.state.request_id = "req-queue-1"

    async def _run() -> None:
        await middleware._persist_audit_record(request, _sample_record())

    asyncio.run(_run())
    assert session.commit_count == 0, "请求路径内不得同步落库"

    asyncio.run(audit_persist_queue.drain_once())
    assert session.committed is True
    assert session.added[0].request_id == "req-queue-1"


# ---------------------------------------------------------------------------
# 8) 请求路径零等待：慢落库不影响响应返回
# ---------------------------------------------------------------------------


def test_dispatch_returns_while_audit_write_is_slow(monkeypatch: pytest.MonkeyPatch) -> None:
    """请求路径零等待：落库变慢（0.5s）时 ``dispatch`` 仍在 0.2s 内返回.

    说明：直测中间件 ``dispatch``（不经 TestClient），避免真实 DB 初始化对
    ``Base.metadata.schema`` 的全局副作用污染同进程内的既有 sqlite 用例。
    """
    import importlib
    import time as _time
    import types

    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    audit_mod = importlib.import_module("openbase.modules.audit")
    queue = audit_mod.audit_persist_queue
    real_write = audit_mod._write_batch_records

    async def _slow_write(items) -> int:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0.5)
        return len(items)

    monkeypatch.setattr(audit_mod, "_write_batch_records", _slow_write)
    middleware = AuditMiddleware(app=object())  # type: ignore[arg-type]
    request = StarletteRequest(_scope())
    request.state.request_id = "req-slow-1"

    async def _call_next(_request: StarletteRequest) -> types.SimpleNamespace:
        return types.SimpleNamespace(status_code=200, headers={})

    async def _run() -> tuple[object, float]:
        queue.start()
        t0 = _time.perf_counter()
        response = await middleware.dispatch(request, _call_next)
        elapsed = _time.perf_counter() - t0
        await queue.stop()
        return response, elapsed

    try:
        response, elapsed = asyncio.run(_run())
    finally:
        monkeypatch.setattr(audit_mod, "_write_batch_records", real_write)
    assert response.status_code == 200  # type: ignore[attr-defined]
    assert elapsed < 0.2, f"审计落库变慢不得拖慢响应：实测 {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# 9) 异常与降级边界：回滚失败抑制 / 无循环启动 / 排空超时 / writer 消费降级
# ---------------------------------------------------------------------------


class _RollbackFailingSession(_FailingSession):
    """commit 与 rollback 均失败的假会话（验证回滚异常被抑制）."""

    async def rollback(self) -> None:
        raise RuntimeError("rollback down")


def test_start_without_running_loop_is_noop() -> None:
    """同步上下文（无运行事件循环）调用 ``start`` 静默跳过，不创建 task."""
    queue = AuditPersistQueue()
    queue.start()
    assert queue.stats()["writer_running"] == 0


def test_write_batch_rollback_failure_is_suppressed(monkeypatch: pytest.MonkeyPatch) -> None:
    """落库失败且**回滚亦失败**时：仍向上抛出原始错误（回滚异常被吞掉，不掩盖原因）."""
    import importlib

    audit_mod = importlib.import_module("openbase.modules.audit")
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    _patch_session_factory(monkeypatch, _RollbackFailingSession())

    with pytest.raises(RuntimeError, match="db down"):
        asyncio.run(audit_mod._write_batch_records([("api_request", _payload())]))


def test_stop_swallows_drain_failure_and_counts_dropped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """关闭排空超时/失败：不阻断关闭，剩余在途条目登记为 dropped 并 WARN."""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    queue = AuditPersistQueue()

    async def _boom() -> int:
        raise TimeoutError("drain timed out")

    monkeypatch.setattr(queue, "drain_once", _boom)

    async def _run() -> None:
        queue.submit("api_request", _payload("req-timeout"))
        await queue.stop(timeout=0.01)

    with caplog.at_level(logging.WARNING, logger="openbase.audit"):
        asyncio.run(_run())
    assert queue.stats()["dropped"] == 1
    assert any("drain on shutdown timed out" in rec.message for rec in caplog.records)


def test_writer_degrades_on_write_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """writer 协程遇到落库失败：登记 failed、继续消费（不因单批失败退出）."""
    monkeypatch.setenv(ENV_AUDIT_DB_PERSIST, "1")
    _patch_session_factory(monkeypatch, _FailingSession())
    queue = AuditPersistQueue()

    async def _run() -> None:
        queue.start()
        queue.submit("api_request", _payload("req-wf"))
        for _ in range(100):
            if queue.stats()["failed"]:
                break
            await asyncio.sleep(0.01)
        await queue.stop()

    with caplog.at_level(logging.WARNING, logger="openbase.audit"):
        asyncio.run(_run())
    assert queue.stats()["failed"] >= 1
    assert queue.stats()["writer_running"] == 0
    assert any("audit db persist failed (degraded)" in rec.message for rec in caplog.records)
