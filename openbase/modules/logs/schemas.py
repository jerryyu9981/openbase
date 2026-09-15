"""logs 模块查询视图实体与请求契约（v1.4.6）.

LogEntry 为**查询视图实体**（非持久化实体），18 字段 × 多源映射见
《OpenBase-API接口设计文档-v1.4.6》§2。前 5 字段为必需字段，任何源不得返回 null。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LogSource = Literal["l1_file", "audit_db", "test_record", "repo_log"]
LogModule = Literal["identity", "dps", "rag", "memory", "llm", "gateway", "testing", "other"]
LogOperation = Literal["auth_login", "read", "write", "delete", "config", "proxy"]
LogResult = Literal["success", "client_error", "server_error", "unknown"]

LOG_SOURCES: tuple[str, ...] = ("l1_file", "audit_db", "test_record", "repo_log")
LOG_MODULES: tuple[str, ...] = ("identity", "dps", "rag", "memory", "llm", "gateway", "testing", "other")
LOG_OPERATIONS: tuple[str, ...] = ("auth_login", "read", "write", "delete", "config", "proxy")
LOG_RESULTS: tuple[str, ...] = ("success", "client_error", "server_error", "unknown")


class LogEntry(BaseModel):
    """统一日志条目（18 字段，契约唯一事实源由后端返回）。"""

    ts: str
    source: LogSource
    module: LogModule
    operation: LogOperation
    result: LogResult
    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    status_code: int | None = None
    duration_ms: int | None = None
    operator_id: str | None = None
    tenant_id: str | None = None
    ip_address: str | None = None
    case_id: str | None = None
    step_id: int | str | None = None
    run_id: str | None = None
    action: str | None = None
    summary: dict | None = None


class LogQueryParams(BaseModel):
    """/logs/search、/logs/facets、/logs/export 共享的筛选参数（snake_case）。"""

    source: LogSource
    module: list[LogModule] = Field(default_factory=list)
    operation: list[LogOperation] = Field(default_factory=list)
    result: list[LogResult] = Field(default_factory=list)
    operator: list[str] = Field(default_factory=list)
    q: str | None = Field(default=None, max_length=200)
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    case_id: str | None = None
    run_id: str | None = None
    step_id: int | str | None = None


class LogSearchParams(LogQueryParams):
    """/logs/search 分页参数。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class LogExportParams(LogQueryParams):
    """/logs/export 导出参数。"""

    format: Literal["csv", "json"] = "csv"
