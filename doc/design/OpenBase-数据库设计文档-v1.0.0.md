# OpenBase 数据库设计文档 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 关联需求 | FR-CORE-001/002、FR-MOD-002/003、FR-SUP-001~005、DR-001~DR-010 |

---

## 1. 数据库设计总则

| 项 | 约定 |
|----|------|
| 数据库 | PostgreSQL 14+ |
| 多租户 | Schema 隔离（每租户一个 Schema）+ 公共 Schema（public） |
| ORM | SQLAlchemy 2.x（Mapped/mapped_column 声明式） |
| 迁移 | Alembic（autogenerate + 迁移模板） |
| 主键 | BigInt 自增（或 UUID，按模块需求） |
| 时间字段 | created_at / updated_at（ISO 8601 UTC） |
| 软删除 | 用户/租户支持软删（is_deleted + deleted_at） |
| 审计 | AuditLog 单独表，保留 ≥180 天 |

## 2. 实体关系总览（ER）

```
public Schema（公共）
User 1─* UserRole *─1 Role 1─* RolePermission *─1 Permission
User *─1 Tenant（归属租户）
Tenant 1─* Department（部门树，parent_id 自关联）
Department *─* User（user_department 关联）
DictType 1─* DictItem
AuditLog（独立）
ConfigVersion（配置版本）

租户 Schema（每租户）
ScheduleTask 1─* ScheduleLog
FileRecord
Notification
```

## 3. 数据字典（表设计）

### 3.1 users（用户）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 用户 ID |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录名 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 哈希 |
| display_name | VARCHAR(128) | NOT NULL | 显示名 |
| email | VARCHAR(128) | NULL | 邮箱 |
| phone | VARCHAR(32) | NULL | 手机号 |
| status | SMALLINT | NOT NULL, DEFAULT 1 | 1=启用 0=禁用 |
| tenant_id | BIGINT | FK→tenants.id | 归属租户 |
| is_deleted | BOOLEAN | NOT NULL, DEFAULT false | 软删标记 |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | 时间戳 |

**索引**：uk_username(username)、idx_users_tenant(tenant_id)

### 3.2 roles（角色）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 角色 ID |
| name | VARCHAR(64) | UNIQUE, NOT NULL | 角色名 |
| code | VARCHAR(64) | UNIQUE, NOT NULL | 角色编码 |
| description | VARCHAR(255) | NULL | 描述 |
| is_system | BOOLEAN | NOT NULL, DEFAULT false | 系统内置角色不可删 |

### 3.3 permissions（权限点）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 权限 ID |
| code | VARCHAR(128) | UNIQUE, NOT NULL | 权限编码（如 user:create） |
| name | VARCHAR(128) | NOT NULL | 权限名 |
| module | VARCHAR(64) | NOT NULL | 所属模块 |
| type | SMALLINT | NOT NULL | 1=菜单 2=按钮 3=接口 |

### 3.4 user_role（用户-角色关联）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| user_id | BIGINT | FK→users.id, PK(复合) | 用户 |
| role_id | BIGINT | FK→roles.id, PK(复合) | 角色 |

### 3.5 role_permission（角色-权限关联）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| role_id | BIGINT | FK→roles.id, PK(复合) | 角色 |
| permission_id | BIGINT | FK→permissions.id, PK(复合) | 权限 |

### 3.6 tenants（租户）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 租户 ID |
| name | VARCHAR(128) | UNIQUE, NOT NULL | 租户名 |
| code | VARCHAR(64) | UNIQUE, NOT NULL | 租户编码（Schema 名） |
| status | SMALLINT | NOT NULL, DEFAULT 1 | 1=启用 0=禁用 |
| isolation_level | SMALLINT | NOT NULL, DEFAULT 1 | 1=Schema 隔离 2=行级 |
| quota | JSONB | NULL | 配额（用户数/存储等） |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | 时间戳 |

### 3.7 departments（部门，org 模块）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 部门 ID |
| name | VARCHAR(128) | NOT NULL | 部门名 |
| parent_id | BIGINT | FK→departments.id, NULL | 父部门（树） |
| path | VARCHAR(512) | NOT NULL | 层级路径（/1/2/3） |
| tenant_id | BIGINT | FK→tenants.id | 租户 |

### 3.8 user_department（用户-部门关联）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| user_id | BIGINT | FK→users.id, PK(复合) | 用户 |
| department_id | BIGINT | FK→departments.id, PK(复合) | 部门 |

### 3.9 dict_types / dict_items（数据字典）

**dict_types**：id、code(UNIQUE)、name、description、tenant_id

**dict_items**：id、type_id(FK)、label、value、sort_order、status、extra(JSONB)、tenant_id

### 3.10 schedule_tasks / schedule_logs（定时任务）

**schedule_tasks**：id、name、cron_expr、func_path、params(JSONB)、status(1=启用 0=禁用)、last_run_at、next_run_at、tenant_id

**schedule_logs**：id、task_id(FK)、status(success/failed)、message、started_at、finished_at

### 3.11 file_records（文件，storage 模块）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 文件 ID |
| file_name | VARCHAR(255) | NOT NULL | 原始文件名 |
| storage_path | VARCHAR(512) | NOT NULL | 存储路径 |
| backend | VARCHAR(32) | NOT NULL | local/minio/s3 |
| content_type | VARCHAR(128) | NULL | MIME |
| size | BIGINT | NOT NULL | 字节数 |
| uploader_id | BIGINT | FK→users.id | 上传者 |
| tenant_id | BIGINT | FK→tenants.id | 租户 |

### 3.12 notifications（通知，notify 模块）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 通知 ID |
| user_id | BIGINT | FK→users.id, NOT NULL | 接收人 |
| title | VARCHAR(255) | NOT NULL | 标题 |
| content | TEXT | NULL | 内容 |
| type | SMALLINT | NOT NULL | 1=站内信 2=SSE 3=系统 |
| is_read | BOOLEAN | NOT NULL, DEFAULT false | 已读 |
| read_at | TIMESTAMPTZ | NULL | 已读时间 |
| created_at | TIMESTAMPTZ | NOT NULL | 创建时间 |

### 3.13 audit_logs（审计日志）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 日志 ID |
| user_id | BIGINT | NULL | 操作人 |
| tenant_id | BIGINT | NULL | 租户 |
| action | VARCHAR(128) | NOT NULL | 操作（login/user.create/...） |
| resource | VARCHAR(128) | NULL | 资源类型 |
| resource_id | VARCHAR(64) | NULL | 资源 ID |
| ip | VARCHAR(64) | NULL | 来源 IP |
| user_agent | VARCHAR(255) | NULL | UA |
| request_id | VARCHAR(64) | NOT NULL | 请求 ID |
| detail | JSONB | NULL | 详情 |
| created_at | TIMESTAMPTZ | NOT NULL | 时间 |

**索引**：idx_audit_user(created_at, user_id)、idx_audit_action(created_at, action)

### 3.14 config_versions（配置版本，config 模块）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 版本 ID |
| config_key | VARCHAR(255) | NOT NULL | 配置键 |
| config_value | JSONB | NOT NULL | 配置值 |
| version | INT | NOT NULL | 版本号（递增） |
| created_by | BIGINT | NULL | 操作人 |
| created_at | TIMESTAMPTZ | NOT NULL | 时间 |

**约束**：uk_config_version(config_key, version)；保留 ≥10 个版本

## 4. 多租户 Schema 隔离设计

| 项 | 设计 |
|----|------|
| 公共 Schema | public：users/roles/permissions/tenants/audit_logs（跨租户共享结构） |
| 租户 Schema | {tenant_code}：departments/dict_*/schedule_*/file_records/notifications（按租户隔离） |
| Schema 切换 | EdgeRouter 中间件解析 X-Tenant-Id → 设置 search_path → 请求结束恢复 |
| 迁移策略 | 公共表迁移走 Alembic；租户表迁移为模板 + 租户创建时执行 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：ER 总览、14 张表数据字典（字段/约束/索引）、多租户 Schema 隔离设计 |
