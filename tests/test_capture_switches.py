"""C-19 响应采集三开关测试（settings + 审计留痕）.

覆盖方案《OpenBase-人工端到端测试日志记录方案》§11.2 红线与 §11.3 三开关设计：

- 三个开关默认**全关**（``OPENBASE_CAPTURE_RESPONSE`` /
  ``OPENBASE_CAPTURE_UPSTREAM`` / ``OPENBASE_CAPTURE_FIELD_ALLOWLIST``）；
- 关时**零采集**（``capture_response_enabled`` / ``capture_upstream_enabled`` 均为 False）；
- **生产永久关闭**：``env=production`` 时即使开关置 1 也不生效（红线 4）；
- 允许清单按逗号解析（默认空 = 全脱敏）；
- **开关变更记审计**：启动快照经结构化日志留痕，开启时 best-effort 落 ``audit_logs``
  （action ``capture.switch``），落库失败仅 WARN 不阻断启动。
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from openbase.core.models import AuditLog
from openbase.modules.audit.capture_switches import (
    CAPTURE_SWITCH_ACTION,
    capture_switch_state,
    record_capture_switch_state,
)
from openbase.settings import Settings

# ---- 默认与解析 ----


def test_capture_switches_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认全关：三开关均为关，允许清单为空. """
    for name in (
        "OPENBASE_CAPTURE_RESPONSE",
        "OPENBASE_CAPTURE_UPSTREAM",
        "OPENBASE_CAPTURE_FIELD_ALLOWLIST",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings()
    assert settings.capture_response is False
    assert settings.capture_upstream is False
    assert settings.capture_field_allowlist == ""
    assert settings.capture_field_allowlist_list == []
    assert settings.capture_response_enabled is False
    assert settings.capture_upstream_enabled is False


def test_capture_switches_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """环境变量置 1 → 开关生效（默认 environment=development）."""
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    monkeypatch.setenv("OPENBASE_CAPTURE_UPSTREAM", "true")
    monkeypatch.setenv("OPENBASE_CAPTURE_FIELD_ALLOWLIST", "error.code, error.message , ")
    settings = Settings()
    assert settings.capture_response_enabled is True
    assert settings.capture_upstream_enabled is True
    assert settings.capture_field_allowlist_list == ["error.code", "error.message"]


def test_capture_is_permanently_off_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """红线 4：生产永久关闭——即使显式置 1 也不生效. """
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    monkeypatch.setenv("OPENBASE_CAPTURE_UPSTREAM", "1")
    settings = Settings(env="production", jwt_secret="x" * 40, enforce_token_version=True)
    assert settings.capture_response is True
    assert settings.capture_response_enabled is False
    assert settings.capture_upstream_enabled is False


# ---- 开关状态的审计留痕 ----


def test_capture_switch_state_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """快照载荷：三个开关 + 是否任一开启（供审计与排查）. """
    monkeypatch.setenv("OPENBASE_CAPTURE_UPSTREAM", "1")
    state = capture_switch_state(Settings())
    assert state["capture_response"] is False
    assert state["capture_upstream"] is True
    assert state["capture_field_allowlist"] == []
    assert state["capture_enabled"] is True


def test_record_switch_state_off_logs_without_db(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """全关时：只留日志、不落库（生产默认零写入）. """
    monkeypatch.delenv("OPENBASE_CAPTURE_RESPONSE", raising=False)
    monkeypatch.delenv("OPENBASE_CAPTURE_UPSTREAM", raising=False)
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")
    with caplog.at_level(logging.INFO, logger="openbase.audit"):
        state = asyncio.run(record_capture_switch_state(Settings()))
    assert state["capture_enabled"] is False
    assert any(record.message == "capture.switch.state" for record in caplog.records)


class _FakeDbSession:
    """最小 DB 会话替身（add/commit/rollback 均为内存行为）."""

    def __init__(
        self, commit_error: Exception | None = None, rollback_error: Exception | None = None
    ) -> None:
        self.commit_error = commit_error
        self.rollback_error = rollback_error
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self.commit_error is not None:
            raise self.commit_error

    async def rollback(self) -> None:
        if self.rollback_error is not None:
            raise self.rollback_error


class _FakeSessionCM:
    """async 上下文管理器：包装 ``get_session_factory()()`` 的返回."""

    def __init__(
        self, commit_error: Exception | None = None, rollback_error: Exception | None = None
    ) -> None:
        self.session = _FakeDbSession(commit_error, rollback_error)

    async def __aenter__(self) -> _FakeDbSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _install_fake_db(
    monkeypatch: pytest.MonkeyPatch,
    commit_error: Exception | None = None,
    rollback_error: Exception | None = None,
) -> _FakeDbSession:
    """替换 DB 会话工厂为内存替身，返回替身以便断言. """
    shared_cm = _FakeSessionCM(commit_error, rollback_error)

    def fake_factory():
        def make_cm_factory():
            return shared_cm

        return make_cm_factory

    monkeypatch.setattr("openbase.core.db.session.get_session_factory", fake_factory)
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "1")
    return shared_cm.session


def test_record_switch_state_on_persists_audit_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """开关开启 → 落 ``audit_logs``（action=capture.switch，detail 记三开关状态）. """
    fake_session = _install_fake_db(monkeypatch)
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    state = asyncio.run(record_capture_switch_state(Settings(env="development")))
    assert state["capture_enabled"] is True
    assert len(fake_session.added) == 1
    row = fake_session.added[0]
    assert isinstance(row, AuditLog)
    assert row.action == CAPTURE_SWITCH_ACTION
    assert row.detail["capture_response"] is True


def test_record_switch_state_db_failure_is_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    """落库失败仅降级（WARN），不阻断启动. """
    _install_fake_db(monkeypatch, commit_error=RuntimeError("db down"))
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    state = asyncio.run(record_capture_switch_state(Settings(env="development")))
    assert state["capture_enabled"] is True


def test_record_switch_state_tolerates_rollback_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """落库失败后 rollback 亦失败 → 仍仅降级（不抛出，不阻断启动）. """
    _install_fake_db(
        monkeypatch,
        commit_error=RuntimeError("db down"),
        rollback_error=RuntimeError("rollback down"),
    )
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    state = asyncio.run(record_capture_switch_state(Settings(env="development")))
    assert state["capture_enabled"] is True


def test_record_switch_state_db_disabled_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """落库总开关关闭 → 不触发任何 DB 访问（测试环境默认）. """
    monkeypatch.setenv("OPENBASE_CAPTURE_RESPONSE", "1")
    monkeypatch.setenv("OPENBASE_AUDIT_DB_PERSIST", "0")
    state = asyncio.run(record_capture_switch_state(Settings(env="development")))
    assert state["capture_enabled"] is True
