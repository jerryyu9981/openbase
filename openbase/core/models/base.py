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
    UniqueConstraint,
    text,
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

    # ---- U1 统一身份收口（RA-01/OB-1，设计草案 §3.1；W1-4 增量演进不重建） ----
    # 字面量默认与 openbase/modules/identity/state_machine.py 常量保持一致
    # （core.models 不反向依赖 modules，故在此内联同步值）。
    subject_type: Mapped[str] = mapped_column(
        String(16),
        default="user",
        server_default=text("'user'"),
        nullable=False,
        comment="Principal 具象：user/agent（agent 必带）",
    )
    credential_type: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="凭据面约束：user=password/oidc；agent=api_key（禁登录面）",
    )
    status_state: Mapped[str] = mapped_column(
        String(24),
        default="active",
        server_default=text("'active'"),
        nullable=False,
        comment="生命周期状态机：provisioned/active/suspended/deactivated/purged",
    )
    status_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="状态迁移原因（审计/合规）"
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="token 吊销版本号（设计草案 §5 方案 a）",
    )
    tenant_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="租户唯一隔离键冗余列（与 tenants.code 对齐；键不迁移）",
    )
    on_behalf_of: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="委托声明（agent 场景，设计草案 §7；缺省 NULL=自身域）"
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_role, back_populates="users"
    )


class AgentApiKey(Base, TimestampMixin):
    """agent 服务密钥表（U1 T1，设计草案 §3.2：sk-agent-*、哈希存储、多密钥可轮换/吊销）.

    明文密钥仅生成响应展示一次；服务端只存 sha256 key_hash（与 ApiKeyStore._hash 同构）。
    agent_id → users.id（subject_type=agent 主体行），不新增独立 agents 表。
    """

    __tablename__ = "agent_api_keys"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("users.id"), nullable=False, index=True
    )
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="sk-agent-")
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    key_suffix: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="明文尾部 6 位指纹（展示/人工核对，非可逆）"
    )
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active"
    )  # active/revoked（吊销即时失效）
    expires_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(BIGINT, nullable=True)


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


class OidcIdentity(Base, TimestampMixin):
    """OIDC 外部身份 ↔ OpenBase 用户映射（OB-AUTH-OIDC v1.3.0，JIT 自动建号）.

    IdP 主体（sub）唯一映射一个 OpenBase 用户（user_id 唯一）；
    (issuer, sub) 复合唯一——同一 sub 可来自不同 IdP/realm（生产多 IdP 场景），
    首次 OIDC 登录自动建号并落映射；后续登录按 sub+issuer 直查复用。
    """

    __tablename__ = "oidc_identity"
    __table_args__ = (
        # (issuer, sub) 复合唯一：取代 v1.3.0 的 sub 单列唯一（多 IdP 相同 sub 冲突）
        UniqueConstraint("issuer", "sub", name="oidc_identity_issuer_sub_key"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("users.id"), unique=True, nullable=False
    )
    sub: Mapped[str] = mapped_column(String(128), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # IdP 侧最新身份信息（快照，供审计/重绑）
    idp_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idp_email: Mapped[str | None] = mapped_column(String(128), nullable=True)


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
