"""基础模型：声明式 Base + 公共字段 + 5 个核心模型."""

from __future__ import annotations

import datetime as dt
from typing import Optional  # noqa: F401 - 用于 future annotations 字符串注解求值

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# SQLite 兼容：BigInteger 主键/外键在 SQLite 下不自增，降级为 Integer
BIGINT = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类."""


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class TimestampMixin:
    """公共时间戳字段."""

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class SoftDeleteMixin:
    """软删除公共字段."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# 用户-角色关联表
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", BIGINT, ForeignKey("users.id"), primary_key=True),
    Column("role_id", BIGINT, ForeignKey("roles.id"), primary_key=True),
)

# 角色-权限关联表
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", BIGINT, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", BIGINT, ForeignKey("permissions.id"), primary_key=True),
)

# 用户-部门关联表
user_department = Table(
    "user_department",
    Base.metadata,
    Column("user_id", BIGINT, ForeignKey("users.id"), primary_key=True),
    Column("department_id", BIGINT, ForeignKey("departments.id"), primary_key=True),
)


class User(Base, TimestampMixin, SoftDeleteMixin):
    """用户."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[int] = mapped_column(default=1, nullable=False)  # 1=启用 0=禁用
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_role, back_populates="users"
    )


class Role(Base, TimestampMixin):
    """角色."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list[User]] = relationship(
        secondary=user_role, back_populates="roles"
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permission, back_populates="roles"
    )


class Permission(Base, TimestampMixin):
    """权限点."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[int] = mapped_column(default=1, nullable=False)  # 1=菜单 2=按钮 3=接口

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permission, back_populates="permissions"
    )


class Tenant(Base, TimestampMixin):
    """租户."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[int] = mapped_column(default=1, nullable=False)  # 1=启用 0=禁用
    isolation_level: Mapped[int] = mapped_column(default=1, nullable=False)  # 1=Schema 2=行级
    quota: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Department(Base, TimestampMixin):
    """部门（org 模块，树形结构）."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("departments.id"), nullable=True
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("tenants.id"), nullable=True
    )


class AuditLog(Base):
    """审计日志."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


__all__ = [
    "Base",
    "User",
    "Role",
    "Permission",
    "Tenant",
    "AuditLog",
    "user_role",
    "role_permission",
    "user_department",
    "TimestampMixin",
    "SoftDeleteMixin",
]
