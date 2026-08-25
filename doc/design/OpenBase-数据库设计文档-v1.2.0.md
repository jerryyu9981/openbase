# OpenBase 数据库设计文档 - v1.2.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.2.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/design/ |

> 本版本数据库设计为**增量**：后端底座表（users/audit_logs/notifications/mcp_tools 等 v1.0.0~v1.1.0 已建，openbase schema）保持不变；新增 AI 应用（全新补建）与动态模块注册所需表。四系统特色数据（对话/知识库/记忆/画像）仍存于各系统自有库，经代理访问，不入 openbase。

## 1. 增量表清单

| 表 | 用途 | 归属 |
|----|------|------|
| ai_apps | AI 应用主表（全新补建） | openbase schema |
| ai_app_versions | 应用版本 | openbase schema |
| ai_app_calls | 应用调用记录 | openbase schema |
| dynamic_modules | 动态模块注册表 | openbase schema |

## 2. 数据字典

### 2.1 ai_apps（AI 应用）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 应用 ID |
| tenant_id | UUID | FK tenants | 租户隔离（必带过滤） |
| name | varchar(100) | NOT NULL | 应用名称 |
| description | varchar(500) | - | 描述 |
| model_config | JSONB | NOT NULL | {provider, model, parameters{temperature,top_p,max_tokens}} |
| prompt_template_id | UUID | FK prompt_templates（如建） | Prompt 模板关联 |
| status | varchar(20) | NOT NULL | draft / published / offline |
| current_version | varchar(20) | - | 当前发布版本 |
| created_by | UUID | FK users | 创建人 |
| created_at / updated_at | timestamptz | NOT NULL | 时间戳 |

索引：idx_ai_apps_tenant（tenant_id）、idx_ai_apps_status（status）。

### 2.2 ai_app_versions（应用版本）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 版本 ID |
| app_id | UUID | FK ai_apps | 所属应用 |
| version | varchar(20) | NOT NULL | 版本号（如 v1） |
| model_config_snapshot | JSONB | NOT NULL | 发布时模型配置快照 |
| prompt_snapshot | JSONB | - | Prompt 快照 |
| published_by / published_at | UUID / timestamptz | - | 发布人/时间 |

### 2.3 ai_app_calls（调用记录）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| app_id | UUID | FK ai_apps | 应用 |
| version | varchar(20) | - | 调用版本 |
| user_id | UUID | FK users | 调用人 |
| input_tokens / output_tokens / total_tokens | int | - | Token 统计 |
| latency_ms | int | - | 延迟 |
| status | varchar(20) | NOT NULL | success / error |
| error_code | varchar(20) | - | 错误码 |
| created_at | timestamptz | NOT NULL | 调用时间 |

索引：idx_ai_app_calls_app_time（app_id, created_at desc）。

### 2.4 dynamic_modules（动态模块注册表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | varchar(50) | PK | 模块 ID（openllm/knowledge/memory/portrait） |
| name | varchar(100) | NOT NULL | 模块名称 |
| icon | varchar(50) | - | 菜单图标 |
| route_prefix | varchar(50) | NOT NULL | 路由前缀 |
| entry | varchar(200) | NOT NULL | 懒加载入口文件 |
| permission | varchar(50) | NOT NULL | 权限标识（如 openllm:view） |
| status | varchar(20) | NOT NULL | enabled / disabled |
| sort_order | int | - | 菜单排序 |
| created_at / updated_at | timestamptz | NOT NULL | 时间戳 |

种子数据：openllm / knowledge / memory / portrait 四条 enabled。

## 3. 迁移与幂等

| 项 | 规则 |
|----|------|
| 迁移 | SQLAlchemy create_all 幂等（WHERE NOT EXISTS / IF NOT EXISTS），openbase schema 内建表 |
| 回滚 | 新表可安全 drop（仅本版本新增，无下游依赖） |
| 多租户 | 业务表均带 tenant_id 且查询强制过滤 |

## 4. 不纳入 openbase 的数据

| 数据 | 归属 | 访问方式 |
|------|------|---------|
| 对话/用量/模型（OpenLLM） | OpenLLM 库 | 代理 API |
| 知识库/文档/分块（OpenRAG） | OpenRAG 库（Qdrant/ES/PG） | 代理 API |
| 记忆/衰减/图谱（OpenMemory） | OpenMemory 库（Qdrant/Neo4j/PG） | 代理 API |
| 画像/标签/批量（DPS） | DPS 库 | 代理 API |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：v1.2.0 增量表（AI 应用三表 + 动态模块注册表）与数据字典 |
