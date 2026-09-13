"""C-1 结构化日志配置测试（TDD：先 RED，后实现）.

覆盖《人工端到端测试日志记录方案 v1.1.0》§6 验收项：
- JSON 必填字段齐全率 100%
- 敏感字段 0 命中（脱敏）
- 超限值截断
- 按日落盘到 logs/<service>/<service>-YYYYMMDD.jsonl
- 重复调用不产生重复 handler（幂等）
- 级别可由环境变量控制
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pytest

from openbase.core import logging_setup as logging_setup_module
from openbase.core.logging_setup import (
    DailyFileHandler,
    JsonFormatter,
    SensitiveFilter,
    bind_log_context,
    clear_log_context,
    setup_logging,
)


@pytest.fixture(autouse=True)
def _restore_root_logging():
    """隔离 root logger 状态，避免 setup_logging 影响其他测试。"""
    root = logging.getLogger()
    handlers_before = list(root.handlers)
    filters_before = list(root.filters)
    level_before = root.level
    yield
    for handler in list(root.handlers):
        if handler not in handlers_before:
            root.removeHandler(handler)
            handler.close()
    for filter_obj in list(root.filters):
        if filter_obj not in filters_before:
            root.removeFilter(filter_obj)
    root.setLevel(level_before)
    logging_setup_module._active_setup = None


def _make_record(message: str = "hello", level: int = logging.INFO, extra: dict | None = None):
    """构造一条 LogRecord（不经过 handler，直接测 formatter）。"""
    record = logging.LogRecord(
        name="openbase.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_formatter_emits_required_fields():
    formatter = JsonFormatter(service="openbase", env="test", version="1.0.0")
    payload = json.loads(formatter.format(_make_record()))

    for key in ("ts", "level", "service", "module", "message", "env", "version"):
        assert key in payload, f"缺少必填字段 {key}"

    assert payload["level"] == "INFO"
    assert payload["service"] == "openbase"
    assert payload["module"] == "openbase.test"
    assert payload["message"] == "hello"


def test_formatter_keeps_structured_extras():
    formatter = JsonFormatter(service="openbase", env="test", version="1.0.0")
    payload = json.loads(
        formatter.format(
            _make_record(
                extra={"request_id": "req-abc123", "case_id": "UI-DPS-0007", "step_id": 3}
            )
        )
    )

    assert payload["request_id"] == "req-abc123"
    assert payload["case_id"] == "UI-DPS-0007"
    assert payload["step_id"] == 3


def test_formatter_masks_sensitive_keys_recursively():
    formatter = JsonFormatter(service="openbase", env="test", version="1.0.0")
    payload = json.loads(
        formatter.format(
            _make_record(
                extra={
                    "password": "p@ssw0rd",
                    "Authorization": "Bearer abc.def.ghi",
                    "nested": {"api_key": "sk-live-123", "safe": "keep"},
                    "items": [{"token": "tk-1"}, {"safe": "keep"}],
                }
            )
        )
    )

    assert payload["password"] == "***"
    assert payload["Authorization"] == "***"
    assert payload["nested"]["api_key"] == "***"
    assert payload["nested"]["safe"] == "keep"
    assert payload["items"][0]["token"] == "***"
    assert payload["items"][1]["safe"] == "keep"


def test_formatter_truncates_oversized_values():
    formatter = JsonFormatter(service="openbase", env="test", version="1.0.0")
    oversized = "x" * 4096
    payload = json.loads(formatter.format(_make_record(extra={"detail": oversized})))

    assert len(payload["detail"]) < len(oversized)
    assert payload["detail"].endswith("[truncated]")


def test_formatter_request_id_defaults_to_dash():
    formatter = JsonFormatter(service="openbase", env="test", version="1.0.0")
    payload = json.loads(formatter.format(_make_record()))

    assert payload["request_id"] == "-"


def test_bind_log_context_injects_fields_into_every_record():
    formatter = JsonFormatter(service="openbase", env="test", version="1.0.0")
    bind_log_context(request_id="req-ctx1", case_id="S0-1")
    try:
        payload = json.loads(formatter.format(_make_record()))
    finally:
        clear_log_context()

    assert payload["request_id"] == "req-ctx1"
    assert payload["case_id"] == "S0-1"


def test_sensitive_filter_keeps_non_sensitive_records():
    filter_obj = SensitiveFilter()

    assert filter_obj.filter(_make_record()) is True


def test_daily_file_handler_splits_by_date(tmp_path: Path):
    current = {"day": date(2026, 9, 13)}
    handler = DailyFileHandler(
        log_dir=tmp_path,
        service="openbase",
        date_provider=lambda: current["day"],
        formatter=JsonFormatter(service="openbase", env="test", version="1.0.0"),
    )
    logger = logging.getLogger("openbase.test.daily")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        logger.info("day-one")
        first = Path(handler.current_path)
        assert first.exists(), "当日日志文件未创建"
        assert "openbase-20260913.jsonl" in first.name

        current["day"] = date(2026, 9, 14)
        logger.info("day-two")
        second = Path(handler.current_path)
        assert second.name != first.name
        assert "openbase-20260914.jsonl" in second.name
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_daily_file_handler_never_deletes_historical_logs(tmp_path: Path):
    """历史日志不得被按保留期自动删除（锁定不变量：禁止自动限期清除代码路径）。

    保留期是**运维策略**（人工/运维脚本执行），不得由进程内代码自动执行；
    因此即便存在远超任何保留窗口的旧文件，落盘也不得删除它。
    """
    service_dir = tmp_path / "openbase"
    service_dir.mkdir(parents=True, exist_ok=True)
    ancient = service_dir / "openbase-20200101.jsonl"
    ancient.write_text('{"message": "ancient"}\n', encoding="utf-8")

    handler = DailyFileHandler(
        log_dir=tmp_path,
        service="openbase",
        date_provider=lambda: date(2026, 9, 13),
        formatter=JsonFormatter(service="openbase", env="test", version="1.0.0"),
    )
    logger = logging.getLogger("openbase.test.daily.retention")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        logger.info("today-line")
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert ancient.exists(), "历史日志被自动删除，违反「禁止自动限期清除」不变量"
    assert ancient.read_text(encoding="utf-8") == '{"message": "ancient"}\n'


def test_module_declares_no_auto_purge_path():
    """日志模块自身不得出现「按保留期自动清除」标识（与测试不变量 T6-1 同口径）。"""
    forbidden_tokens = (
        "auto_purge",
        "purge_expired",
        "purge_stale",
        "purge_retention",
        "retention_days",
        "purge_deactivated_expired",
        "_schedule_purge",
    )
    text = Path(logging_setup_module.__file__).read_text(encoding="utf-8")
    hits = [token for token in forbidden_tokens if token in text]
    assert not hits, f"日志模块出现自动限期清除标识：{hits}"


def test_setup_logging_writes_jsonl_and_is_idempotent(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENBASE_LOG_LEVEL", raising=False)
    monkeypatch.setenv("OPENBASE_ENV", "test")
    monkeypatch.setenv("OPENBASE_LOG_DIR", str(tmp_path))

    first = setup_logging(service="openbase", log_dir=tmp_path, force=True)
    handler_count_after_first = len(logging.getLogger().handlers)

    second = setup_logging(service="openbase", log_dir=tmp_path)
    handler_count_after_second = len(logging.getLogger().handlers)

    assert handler_count_after_second == handler_count_after_first, "重复调用产生了重复 handler"
    assert first.level == second.level

    logger = logging.getLogger("openbase.test.setup")
    logger.info("setup-line", extra={"request_id": "req-setup1"})
    for handler in logging.getLogger().handlers:
        handler.flush()

    path = Path(second.current_path)
    assert path.exists(), "日志文件未落盘"

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "日志文件为空"
    payload = json.loads(lines[-1])
    assert payload["message"] == "setup-line"
    assert payload["request_id"] == "req-setup1"
    assert payload["service"] == "openbase"

    assert path.parent.name == "openbase"


def test_setup_logging_level_follows_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENBASE_LOG_LEVEL", "DEBUG")

    config = setup_logging(service="openbase", log_dir=tmp_path, force=True)

    assert config.level == logging.DEBUG
