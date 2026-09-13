"""OpenBase 结构化日志配置（C-1 日志落盘）.

设计依据：《OpenBase-人工端到端测试日志记录方案-v1.0.0》v1.1.0 §4（字段与事件字典）、
§11.2（响应采集红线，本模块不含响应体采集）、§6（验收标准）。规范依据：
`observability-standards`（结构化 JSON、必填字段、禁止记录项）。

能力：

- **JSON Lines 落盘**：``logs/<service>/<service>-YYYYMMDD.jsonl``（按日切分）
- **控制台同步输出**：同一 JSON formatter，便于编排器重定向采集（C-6）
- **必填字段注入**：``ts/level/service/module/message/env/version``（+ ``request_id`` 兜底 ``"-"``）
- **结构化字段保留**：``logger.info("...", extra={...})`` 的键值原样落盘
- **脱敏与截断**：敏感键（password/token/secret/authorization…）→ ``"***"``；
  超长值截断并标记 ``[truncated]``（不记录完整请求/响应体）
- **日志上下文**：``bind_log_context`` 注入 request_id/case_id/step_id/run_id（C-3 接线用）

不变量约束（重要）：

- 本模块**不包含任何按保留期自动清理/自动删除日志的实现**，也不注册任何定时清理任务。
  这是对既有测试不变量 T6-1（「全仓 0 条按保留期限自动清除代码路径」，
  `tests/test_identity_t6.py::test_t6_1_no_auto_retention_purge_path_static_scan`）的遵循：
  历史证据只能由**运维策略人工执行**清理，不得由进程内代码自动执行。

环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| ``OPENBASE_LOG_LEVEL`` | ``INFO`` | 日志级别 |
| ``OPENBASE_LOG_DIR`` | ``logs`` | 日志根目录 |
| ``OPENBASE_ENV`` | ``dev`` | 环境标识（写入 ``env`` 字段） |
| ``OPENBASE_SERVICE_VERSION`` | ``0.0.0`` | 服务版本（写入 ``version`` 字段） |
| ``OPENBASE_LOG_MAX_VALUE`` | ``1024`` | 单字段值最大长度（超出截断） |
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "DailyFileHandler",
    "JsonFormatter",
    "LoggingSetup",
    "SensitiveFilter",
    "bind_log_context",
    "clear_log_context",
    "get_log_context",
    "setup_logging",
]

# 敏感键片段（小写匹配，命中即整体遮蔽）
SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "authorization",
    "credential",
    "cookie",
    "session_id",
)

# LogRecord 内置属性（不视为业务 extra）
_STANDARD_RECORD_ATTRS: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "asctime",
        "message",
    }
)

_MASKED: str = "***"
_TRUNCATED_SUFFIX: str = "[truncated]"
_MAX_DEPTH: int = 5

_log_context: ContextVar[dict[str, Any] | None] = ContextVar("openbase_log_context", default=None)


def bind_log_context(**fields: Any) -> None:
    """绑定日志上下文（request_id/case_id/step_id/run_id 等），随记录自动落盘。"""
    merged = dict(_log_context.get() or {})
    for key, value in fields.items():
        if value is not None:
            merged[key] = value
    _log_context.set(merged)


def clear_log_context() -> None:
    """清空日志上下文（请求结束/reset 用）。"""
    _log_context.set(None)


def get_log_context() -> dict[str, Any]:
    """读取当前日志上下文（只读快照）。"""
    return dict(_log_context.get() or {})


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _sanitize(value: Any, key: str = "", depth: int = 0, max_value_length: int = 1024) -> Any:
    """脱敏与截断：敏感键遮蔽、超长值截断、容器限深递归。"""
    if _is_sensitive_key(key):
        return _MASKED
    if depth >= _MAX_DEPTH:
        return "<max-depth>"
    if isinstance(value, dict):
        return {
            str(item_key): _sanitize(item_value, str(item_key), depth + 1, max_value_length)
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, "", depth + 1, max_value_length) for item in value]
    if isinstance(value, str) and len(value) > max_value_length:
        return value[:max_value_length] + _TRUNCATED_SUFFIX
    return value


class JsonFormatter(logging.Formatter):
    """把 LogRecord 渲染为单行 JSON（含必填字段与结构化 extra）。"""

    def __init__(
        self,
        service: str = "openbase",
        env: str = "dev",
        version: str = "0.0.0",
        max_value_length: int = 1024,
    ) -> None:
        super().__init__()
        self.service = service
        self.env = env
        self.version = version
        self.max_value_length = max_value_length

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "service": self.service,
            "module": record.name,
            "message": record.getMessage(),
            "env": self.env,
            "version": self.version,
        }

        for key, value in get_log_context().items():
            payload[key] = _sanitize(value, key, max_value_length=self.max_value_length)

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = _sanitize(value, key, max_value_length=self.max_value_length)

        payload.setdefault("request_id", "-")

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


class SensitiveFilter(logging.Filter):
    """注入日志上下文并把 ``request_id`` 兜底为 ``"-"``（豁免路径不产生 KeyError）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in get_log_context().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        if not getattr(record, "request_id", None):
            record.request_id = "-"
        return True


class DailyFileHandler(logging.Handler):
    """按日切分的 JSON Lines 文件 handler（``<service>-YYYYMMDD.jsonl``）。

    只做「按日切换文件」，**不做任何自动清理/自动删除**（见模块 docstring 的不变量约束）。
    """

    def __init__(
        self,
        log_dir: str | Path,
        service: str,
        date_provider: Callable[[], date] | None = None,
        formatter: logging.Formatter | None = None,
    ) -> None:
        super().__init__()
        self.log_dir = Path(log_dir)
        self.service = service
        self._date_provider = date_provider or date.today
        self._stream: Any = None
        self._current_date: date | None = None
        if formatter is not None:
            self.setFormatter(formatter)

    @property
    def service_dir(self) -> Path:
        """服务日志目录：``<log_dir>/<service>``。"""
        return self.log_dir / self.service

    @property
    def current_path(self) -> Path:
        """当日日志文件路径。"""
        return self.service_dir / f"{self.service}-{self._date_provider():%Y%m%d}.jsonl"

    def _open_stream(self, target_date: date) -> None:
        self.service_dir.mkdir(parents=True, exist_ok=True)
        path = self.service_dir / f"{self.service}-{target_date:%Y%m%d}.jsonl"
        self._stream = path.open("a", encoding="utf-8")
        self._current_date = target_date

    def emit(self, record: logging.LogRecord) -> None:
        try:
            today = self._date_provider()
            if self._stream is None or self._current_date != today:
                if self._stream is not None:
                    self._stream.close()
                self._open_stream(today)
            self._stream.write(self.format(record) + "\n")
            self._stream.flush()
        except Exception:  # noqa: BLE001 - 日志失败不得影响主流程
            self.handleError(record)

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        super().close()


@dataclass
class LoggingSetup:
    """一次日志配置的结果（供调用方查询路径与关闭）。"""

    service: str
    env: str
    version: str
    level: int
    log_dir: Path
    file_handler: DailyFileHandler
    console_handler: logging.Handler = field(repr=False, default=None)  # type: ignore[assignment]

    @property
    def current_path(self) -> Path:
        """当日 JSONL 文件路径。"""
        return self.file_handler.current_path

    def close(self) -> None:
        """从 root logger 摘除并关闭本配置注册的 handler。"""
        root = logging.getLogger()
        for handler in (self.file_handler, self.console_handler):
            if handler is None:
                continue
            root.removeHandler(handler)
            handler.close()


_active_setup: LoggingSetup | None = None


def _resolve_level(level: int | str | None) -> int:
    if isinstance(level, int):
        return level
    raw = level or os.getenv("OPENBASE_LOG_LEVEL", "INFO")
    resolved = logging.getLevelName(str(raw).upper())
    return resolved if isinstance(resolved, int) else logging.INFO


def setup_logging(
    service: str = "openbase",
    log_dir: str | Path | None = None,
    level: int | str | None = None,
    force: bool = False,
) -> LoggingSetup:
    """装配结构化日志（幂等：重复调用不产生重复 handler）。

    Args:
        service: 服务名（决定目录与文件名前缀，写入 ``service`` 字段）。
        log_dir: 日志根目录，默认取 ``OPENBASE_LOG_DIR`` 或 ``logs``。
        level: 级别（int 或名称），默认取 ``OPENBASE_LOG_LEVEL`` 或 ``INFO``。
        force: 为 ``True`` 时先摘除上一次配置（测试/重载用）。

    Returns:
        LoggingSetup: 配置结果。
    """
    global _active_setup

    if _active_setup is not None and not force:
        return _active_setup

    if _active_setup is not None:
        _active_setup.close()
        _active_setup = None

    env = os.getenv("OPENBASE_ENV", "dev")
    version = os.getenv("OPENBASE_SERVICE_VERSION", "0.0.0")
    max_value_length = int(os.getenv("OPENBASE_LOG_MAX_VALUE", "1024"))
    resolved_level = _resolve_level(level)
    resolved_dir = Path(log_dir or os.getenv("OPENBASE_LOG_DIR", "logs"))

    formatter = JsonFormatter(
        service=service, env=env, version=version, max_value_length=max_value_length
    )

    file_handler = DailyFileHandler(
        log_dir=resolved_dir,
        service=service,
        formatter=formatter,
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(resolved_level)
    root.addFilter(SensitiveFilter())
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _active_setup = LoggingSetup(
        service=service,
        env=env,
        version=version,
        level=resolved_level,
        log_dir=resolved_dir,
        file_handler=file_handler,
        console_handler=console_handler,
    )
    return _active_setup
