"""业务模块模型：dict/config/scheduler/storage/notify（数据库落库用）.

与 base.py 共用 Base.metadata，保证 init_db 建表与 schema 绑定覆盖全部表。
对齐数据库设计文档 §3.9~3.14。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from openbase.core.models.base import Base, TimestampMixin

# SQLite 兼容：BigInteger 主键在 SQLite 下不自增，降级为 Integer
BIGINT = BigInteger().with_variant(Integer, "sqlite")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ---- dict 模块（数据库设计 §3.9） ----


class DictType(Base, TimestampMixin):
    """数据字典类型."""

    __tablename__ = "dict_types"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


class DictItem(Base, TimestampMixin):
    """数据字典项."""

    __tablename__ = "dict_items"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    type_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("dict_types.id"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


# ---- config 模块（数据库设计 §3.14） ----


class ConfigKV(Base, TimestampMixin):
    """配置项（三级：system/tenant/user）."""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    config_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


class ConfigVersion(Base, TimestampMixin):
    """配置版本（保留 ≥10 个版本）."""

    __tablename__ = "config_versions"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    config_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


# ---- scheduler 模块（数据库设计 §3.10） ----


class ScheduleTask(Base, TimestampMixin):
    """定时任务."""

    __tablename__ = "schedule_tasks"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cron_expr: Mapped[str] = mapped_column(String(64), nullable=False)
    func_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=启用 0=禁用
    last_run_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


class ScheduleLog(Base):
    """任务执行日志."""

    __tablename__ = "schedule_logs"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("schedule_tasks.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # success/failed
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---- storage 模块（数据库设计 §3.11） ----


class FileRecord(Base, TimestampMixin):
    """文件记录."""

    __tablename__ = "file_records"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int] = mapped_column(BIGINT, default=0, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    backend: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    uploader_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


# ---- notify 模块（数据库设计 §3.12） ----


class Notification(Base, TimestampMixin):
    """站内通知."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


# ---- ai_apps 模块（数据库设计文档 v1.2.0 §2.1~2.3，全新补建） ----


class AiApp(Base, TimestampMixin):
    """AI 应用主表."""

    __tablename__ = "ai_apps"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt_template_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    current_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_by: Mapped[int | None] = mapped_column(BIGINT, nullable=True)


class AiAppVersion(Base, TimestampMixin):
    """AI 应用版本."""

    __tablename__ = "ai_app_versions"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("ai_apps.id"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published_by: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiAppCall(Base, TimestampMixin):
    """AI 应用调用记录."""

    __tablename__ = "ai_app_calls"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("ai_apps.id"), nullable=False, index=True
    )
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(20), nullable=True)


# ---- frontend 模块（数据库设计文档 v1.2.0 §2.4，动态模块注册表） ----


class DynamicModule(Base, TimestampMixin):
    """动态模块注册表."""

    __tablename__ = "dynamic_modules"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    route_prefix: Mapped[str] = mapped_column(String(50), nullable=False)
    entry: Mapped[str] = mapped_column(String(200), nullable=False)
    permission: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="enabled", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


__all__ = [
    "DictType",
    "DictItem",
    "ConfigKV",
    "ConfigVersion",
    "ScheduleTask",
    "ScheduleLog",
    "FileRecord",
    "Notification",
    "AiApp",
    "AiAppVersion",
    "AiAppCall",
    "DynamicModule",
]
