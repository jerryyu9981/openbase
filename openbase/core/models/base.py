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


class OutboxEvent(Base, TimestampMixin):
    """L1-1 跨系统级联事件 outbox 表（U1 T2 事件源骨架，设计草案 §8.2）.

    生命周期迁移与状态更新在同一 DB 事务内写入本表（保证事件不丢），
    由投递器（T5 outbox_dispatcher）置 published；消费端以 event_id 幂等去重。
    载荷（payload）遵循 §8.1 事件 schema v1（event_type/subject/tenant_code/
    previous_state/current_state/reason 等）。
    """

    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="全局唯一事件 id（幂等消费键）"
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    # pending/published/failed（投递器按此推进；Redis 故障时 DB outbox 兜底）
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    publish_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EventConsumption(Base, TimestampMixin):
    """L1-1 契约桩消费端幂等表（U1 T5，设计草案 §8.2/§8.3/§11 T5-3）.

    模拟消费端（EventConsumerStub，代表 DPS/OpenMemory/OpenRAG）对某 event_id 的
    一次实际执行记录；(event_id, consumer) 唯一 —— 同一事件重放不产生重复阻断副作用
    （消费端以 event_id 去重，幂等消费契约）。consumer 取值：dps/openmemory/openrag。
    """

    __tablename__ = "event_consumptions"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "consumer",
            name="uq_event_consumptions_event_consumer",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="全局唯一事件 id（幂等消费键）"
    )
    consumer: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="模拟消费端：dps/openmemory/openrag"
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    tenant_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 本次执行的副作用摘要（如 {"domain":"dps","action":"portrait.read","state":"blocked"}）
    side_effect: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    consumed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class SubjectBlock(Base, TimestampMixin):
    """L1-1 契约桩数据面阻断集（U1 T5，设计草案 §8.2/§8.3 桩态）.

    模拟消费端按事件将目标主体写入阻断集：(domain, subject_id) 唯一；
    state=blocked 表示数据面阻断（拒绝语义），state=allowed 表示已解除（restored）。
    阻断保留数据（Q-5=A），仅影响访问判定，不物理删除。
    """

    __tablename__ = "subject_blocks"
    __table_args__ = (
        UniqueConstraint(
            "domain",
            "subject_id",
            name="uq_subject_blocks_domain_subject",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="数据面域：dps/openmemory/openrag"
    )
    subject_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    tenant_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # blocked=阻断 / allowed=已解除（解除不删行，保留审计语义）
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="blocked")
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="触发本状态的事件 id（幂等溯源）"
    )
    blocked_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unblocked_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PurgeAuthorization(Base, TimestampMixin):
    """L1-2 purge 一次性二次授权码（U1 T6，设计草案 §9.2/§11 T6-3）.

    purge 属罕见合规操作：须由受权管理员（identity:purge）对 deactivated 主体签发
    短 TTL 单次有效的授权码（等价确认令牌）。服务端只存 sha256 code_hash（明文仅
    签发响应返回一次，与 sk-agent-* 密钥同构语义）；验证命中即置 consumed
    （单次有效），过期（expires_at < now）/未命中 → 403 BIZ_PURGE_AUTH_REQUIRED。
    同主体仅允许一张 active 授权码（新签发自动作废旧码，防码复用扩散）。
    """

    __tablename__ = "purge_authorizations"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    code_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="sha256(授权码)，不存明文"
    )
    code_suffix: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="授权码尾部 6 位指纹（审计/人工核对，非可逆）"
    )
    # active/consumed（单次有效；过期不再放行，消费记录留痕）
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scope_report_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    consumed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PurgeRecord(Base, TimestampMixin):
    """L1-2 purge 终态台账/墓碑（U1 T6，设计草案 §9.2/§11 T6-4/T6-5）.

    主体主行（users）被物理清除后，本表保留终态记录（status_state=purged），职责：
    - 终态语义留痕：deactivated→purged 迁移结果持久化（矩阵复用，purged 无出边）；
    - 令牌拒绝判定：主体验证器对「行缺失」主体按本表区分「曾存在后被 purge」→
      401 AUTH_PRINCIPAL_DISABLED（存量 token 请求拒绝），与 OIDC 直签/内存用户
      （无行亦无墓碑）fail-open 放行兼容区分（T6 行缺失处置）；
    - 幂等防并发：username 唯一 + 幂等键唯一 —— 并发双触发仅一次执行，
      重复触发对已 purged 主体 400 BIZ_NOT_PURGEABLE 终态拒绝（设计 §9.2 取后者）。
    """

    __tablename__ = "purge_records"
    __table_args__ = (
        # 幂等防并发收敛点：username 全局唯一且永不重发（users.username 唯一约束），
        # 以 username 而非 subject_id 作唯一键可兼容 SQLite 无 AUTOINCREMENT 的 rowid 复用
        # （测试/小型部署物理清除后新行可能复用 rowid）；并登记幂等键唯一。
        UniqueConstraint("username", name="uq_purge_records_username"),
        UniqueConstraint("idempotency_key", name="uq_purge_records_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    tenant_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    tenant_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_state: Mapped[str] = mapped_column(String(24), nullable=False, default="deactivated")
    status_state: Mapped[str] = mapped_column(String(24), nullable=False, default="purged")
    scope_report_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    authorization_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purged_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
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
    "AgentApiKey",
    "OutboxEvent",
    "EventConsumption",
    "SubjectBlock",
    "PurgeAuthorization",
    "PurgeRecord",
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
