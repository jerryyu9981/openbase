# OpenBase 系统架构设计文档 - v1.0.0

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
| 关联需求 | OpenBase-开发需求文档-v1.0.0.md（FR-CORE/MOD/SUP/TOOL/PRO） |

---

## 1. 设计入场检查与轨道选择

| 检查项 | 输入 | 结果 |
|--------|------|------|
| Step 1 需求批准 | 需求评审记录 v1.0.0（批准） | ✅ |
| 需求追溯矩阵 | OpenBase-需求追溯矩阵-v1.0.0.md（39 条） | ✅ |
| 单版本规划 | OpenBase-单版本规划文档-v1.0.0.md | ✅ |
| Phase 计划 | OpenBase-Phase迭代计划-v1.0.0.md | ✅ |
| 技术栈基线 | 路线图 §5 技术选型基线 | ✅ |

**激活轨道**：

| 轨道 | 激活 | 说明 |
|------|------|------|
| 整体 🎯 | ✅ 始终激活 | 系统架构/性能/可观测/部署 |
| 后端 ⚙️ | ✅ 始终激活 | 数据模型/API/安全/缓存 |
| 前端 🎨 | ➖ 不激活 | v1.0.0 纯后端底座，无前端页面（前端归属 v1.2.0） |
| 第三方集成 🔗 | ✅ 激活 | FastMCP / Langfuse / OTel / APScheduler |

## 2. 总体架构

### 2.1 架构定位

OpenBase 是代码级复用底座（Python 发行包），四系统内嵌集成，非独立部署服务。采用"框架内核 core + 插件模块 modules + 工具链 cli/crud + 模板脚手架"四位一体形态。

### 2.2 分层架构

```
┌────────────────────────────────────────────────────────────┐
│ 使用方：OpenLLM / OpenRAG / OpenMemory / DPS / New System  │
│ （特色功能层，各自保留）                                     │
├────────────────────────────────────────────────────────────┤
│ OpenBase 接入层：init_app(settings) + include_router(router)│
├────────────────────────────────────────────────────────────┤
│ 工具链：openbase-cli（create-project/module/crud）          │
│         BaseCRUDRouter（CRUD 自动生成）                     │
│         模板脚手架（标准工程结构）                           │
├────────────────────────────────────────────────────────────┤
│ 插件模块层 modules（配置驱动、弱依赖、可插拔）               │
│  auth │ tenant │ audit │ observability │ config │ mcp      │
│  org  │ dict   │ scheduler │ storage │ notify              │
├────────────────────────────────────────────────────────────┤
│ 框架内核 core（强绑定）                                     │
│  models（User/Role/Permission/Tenant/AuditLog）             │
│  db（session + Alembic）· deps（get_db/get_current_user）  │
│  errors（统一异常+错误码）· settings（配置驱动）             │
├────────────────────────────────────────────────────────────┤
│ 基础设施：PostgreSQL / Redis / Langfuse / OTLP Collector    │
└────────────────────────────────────────────────────────────┘
```

### 2.3 模块依赖关系

```
core/（强绑定，所有模块依赖）
  └── models ← auth/tenant/audit/org 依赖
  └── db     ← 全部模块依赖
  └── deps   ← auth（get_current_user）
  └── errors ← 全部模块依赖
  └── settings ← 全部模块依赖

modules/（弱依赖，配置驱动）
  auth ← 可选被 mcp 依赖（工具鉴权）
  tenant ← 独立
  audit ← 独立（中间件）
  observability ← 独立
  config ← 独立
  mcp ← 可选依赖 auth
  org/dict/scheduler/storage/notify ← 独立（依赖 core）
```

**依赖规则**：core 层强绑定；modules 层弱依赖，单模块禁用不影响其他模块；模块间通过 FastAPI 原生挂载（add_middleware/include_router/Depends）。

## 3. 技术选型与 ADR

### 3.1 技术选型总览

| 领域 | 选型 | 版本约束 | 决策依据 |
|------|------|---------|---------|
| 语言 | Python | 3.11+ | 与四系统技术栈统一 |
| Web 框架 | FastAPI | 当前稳定版 | 异步原生、OpenAPI 自动生成 |
| ORM | SQLAlchemy 2.x | 当前稳定版 | 与三系统一致 |
| 迁移 | Alembic | 当前稳定版 | 模板化迁移 |
| 数据库 | PostgreSQL | 14+ | 多租户 Schema 隔离 |
| 缓存/会话 | Redis | 6+ | 缓存/会话/SSE |
| 任务调度 | APScheduler | 当前稳定版 | scheduler 模块 |
| MCP | FastMCP | 当前稳定版 | decorator API、2026-07 规范 |
| 可观测-追踪 | OpenTelemetry Python SDK | 当前稳定版 | OTLP 协议标准 |
| 可观测-评测 | Langfuse | 当前稳定版 | 自托管、OTLP 对接 |
| 可观测-指标 | Prometheus + Grafana | 当前稳定版 | 指标/告警 |
| 密码哈希 | bcrypt（passlib） | 当前稳定版 | 安全哈希 |
| JWT | python-jose 或 PyJWT | 当前稳定版 | 鉴权签发 |

### 3.2 ADR 记录

#### ADR-001：采用 FastAPI 作为底座 Web 框架

| 项 | 内容 |
|----|------|
| **上下文** | 四系统后端均基于 FastAPI，底座需与各系统原生集成 |
| **备选方案** | ① FastAPI（异步原生/OpenAPI 自动生成/依赖注入）；② Flask（同步/生态成熟但异步弱）；③ Django REST（重量级/ORM 绑定） |
| **决策** | 采用 FastAPI |
| **理由** | 与四系统技术栈零摩擦、include_router/add_middleware 原生挂载契合插件架构、OpenAPI 文档自动生成降低接口文档成本 |
| **后果/风险** | 依赖注入模式需团队熟悉；异步上下文管理需规范（采用 AsyncSession） |

#### ADR-002：采用 SQLAlchemy 2.x + Alembic

| 项 | 内容 |
|----|------|
| **上下文** | 三系统模型基于 SQLAlchemy，抽取需最大兼容 |
| **备选方案** | ① SQLAlchemy 2.x（三系统一致）；② Tortoise ORM（异步友好但迁移弱）；③ 原生 SQL（无模型层） |
| **决策** | SQLAlchemy 2.x + Alembic |
| **理由** | 与三系统模型对齐成本最低、Alembic autogenerate 支持迁移模板、声明式 Base 支撑 base models |
| **后果/风险** | 2.x 风格（Mapped/mapped_column）需统一规范；异步引擎配置需验证 |

#### ADR-003：模块采用配置驱动弱依赖架构

| 项 | 内容 |
|----|------|
| **上下文** | 四系统需按需启用模块，最小改动接入 |
| **备选方案** | ① 配置驱动 enable_module（弱依赖、可插拔）；② 全量注册（简单但不可裁剪）；③ 动态 import 插件（灵活但调试难） |
| **决策** | settings.enable_module/disable_module + init_app 自动装配 |
| **理由** | 满足"可插拔复用"核心目标、单模块故障隔离、灰度切换按模块粒度 |
| **后果/风险** | 需维护模块注册表与依赖声明；模块间隐藏依赖需弱依赖验证（FR-PRO-005） |

#### ADR-004：采用 FastMCP 作为 MCP 实现层

| 项 | 内容 |
|----|------|
| **上下文** | 三件套 MCP Server 需统一实现，避免重复开发 |
| **备选方案** | ① FastMCP（官方 SDK、decorator API）；② 自研 MCP 协议；③ 其他 SDK（TS 等） |
| **决策** | FastMCP（Phase 1 预研验证后确定） |
| **理由** | 官方 SDK 生产稳定、2026-07 规范对齐（可缓存 list）、decorator 声明契合工具注册 |
| **后果/风险** | 预研未通过则回退自研协议（备选已记录 RQ-002） |

#### ADR-005：采用 Langfuse + OTel 作为可观测方案

| 项 | 内容 |
|----|------|
| **上下文** | 四系统统一可观测，避免厂商锁定 |
| **备选方案** | ① Langfuse + OTel（自托管、OTLP、评测能力）；② 仅 OTel + Prometheus；③ 商业 SaaS（数据出域） |
| **决策** | Langfuse（独立服务，OTLP 对接）+ OTel GenAI 语义约定 |
| **理由** | 可自托管满足数据主权、评测能力（LLM 追踪/评分）、OTel 标准避免锁定 |
| **后果/风险** | 预研未通过则回退仅 OTel+Prometheus（备选已记录 RQ-002） |

## 4. 模块详细设计

### 4.1 框架内核 core

| 组件 | 设计要点 |
|------|---------|
| models | Base = DeclarativeBase；User/Role/Permission/Tenant/AuditLog 五模型；多租户字段（tenant_id）+ 权限关联表（user_role/role_permission） |
| db | async_sessionmaker + AsyncSession；get_db 依赖；Alembic 迁移模板（autogenerate） |
| deps | get_db（会话）、get_current_user（JWT 解析 + 用户加载）、get_current_tenant（租户上下文） |
| errors | BaseError（code/message/request_id）；错误码分级：AUTH_xxx/PARAM_xxx/BIZ_xxx/SYS_xxx；全局异常处理器 |
| settings | Settings 类（enable_module/disable_module/init_app）；模块注册表 dict；app 装配器 |

### 4.2 核心模块

| 模块 | 核心设计 |
|------|---------|
| auth | JWT 签发/验证（access 2h/refresh 7d）；RBAC 权限矩阵（user_role/role_permission）；ABAC/OIDC 增强（策略适配层，可与 RBAC 独立启用）；密码 bcrypt |
| tenant | EdgeRouter 中间件（解析 X-Tenant-Id）；Schema 隔离 + 上下文传递；配额（quota）+ 限流（rate_limiter） |
| audit | 审计中间件（请求/响应记录）；限流中间件（429）；指标采集；health_service（/health） |
| observability | OTel 初始化（trace/metrics）；Langfuse 对接（OTLP）；business_metrics（OpenMemory 迁移）；Grafana dashboards JSON |
| config | 三级配置合并（默认<环境<运行时）；hot_reload（watch + 重载）；版本管理（保留 ≥10 版）+ 回滚；密钥加密存储 |
| mcp | FastMCP 实例封装；decorator 工具注册；工具鉴权（可选 auth）；list 缓存 |

### 4.3 补齐模块

| 模块 | 核心设计 |
|------|---------|
| org | Department 树（parent_id 自关联）；user_department 关联；按部门授权（dep 权限点） |
| dict | DictType/DictItem；枚举选项 CRUD；字典缓存（Redis，TTL 5min） |
| scheduler | APScheduler 封装；任务 CRUD；执行日志；启停控制 |
| storage | 本地/MinIO/S3 三种后端适配器（统一接口）；上传/下载/预览；文件元数据表 |
| notify | SSE 推送（Redis pub/sub）；站内信；已读状态持久化 |

### 4.4 工具链

| 工具 | 核心设计 |
|------|---------|
| openbase-cli | create-project（模板脚手架复制）；create-module（模块骨架生成）；create-crud（CRUD 代码生成，对接 BaseCRUDRouter） |
| BaseCRUDRouter | 基于 Pydantic schema 自动生成 list/get/create/update/delete + 分页/搜索/排序 |
| 模板脚手架 | 标准工程结构（core/modules/settings/pyproject/conftest/tests）+ 初始化脚本 |

## 5. 关键设计决策

| # | 决策 | 说明 |
|---|------|------|
| D-001 | 异步优先 | 全部模块使用 AsyncSession/异步路由，与 FastAPI 异步原生一致 |
| D-002 | 双接口体系 | 管理接口（用户级 JWT/RBAC）+ AI 服务接口（服务级 API Key/MCP），认证隔离共享底座（FR-PRO-006） |
| D-003 | 多租户 Schema 隔离 | PG Schema 每租户隔离 + 租户上下文（X-Tenant-Id）传递 |
| D-004 | 统一错误码 | 全站统一 {code, message, request_id} 响应格式 |
| D-005 | 配置驱动启停 | 模块注册表 + enable/disable，弱依赖可插拔 |
| D-006 | 对外接口不变 | 底座化不影响四系统既有对外接口（AI 服务接口与 MCP 工具清单不变） |
| D-007 | 管理接口预留前端契约 | auth/tenant/dict/scheduler/storage/notify 接口设计预留给 v1.2.0 统一前端公共模块调用 |

## 6. 需求设计追溯（DT-ID 摘要）

> 完整追溯见《OpenBase-设计评审记录-v1.0.0.md》§3 需求设计追溯矩阵。

| 设计域 | 覆盖需求 | 覆盖率 |
|--------|---------|--------|
| 框架内核设计 | FR-CORE-001~005 | 5/5 |
| 核心模块设计 | FR-MOD-001~006 | 6/6 |
| 补齐模块设计 | FR-SUP-001~005 | 5/5 |
| 工具链设计 | FR-TOOL-001~004 | 4/4 |
| 流程活动设计 | FR-PRO-001~006 | 6/6 |
| 非功能设计 | NFR-001~013 | 13/13 |
| 数据设计 | DR-001~010 | 10/10 |
| 安全设计 | SR-001~009 | 9/9 |

## 7. 设计风险与偏差

| ID | 风险/偏差 | 等级 | 缓解措施 |
|----|----------|------|---------|
| DS-001 | 三系统代码结构与审计假设不符 | P1 | Phase 1 审计先行，来源决策以实际代码为准 |
| DS-002 | 异步 SQLAlchemy 抽取改造量大 | P1 | 优先采用三系统已验证的异步模式；改写迁移范围在来源决策中明确 |
| DS-003 | 多租户 Schema 隔离 + 公共 Schema 混合 | P2 | 设计 tenant 解析与 schema 切换统一入口 |
| DS-004 | MCP/FastMCP 预研未通过 | P1 | 备选自研协议（RQ-002 缓解） |
| DS-005 | 管理接口契约与 v1.2.0 前端需求偏差 | P2 | 接口设计对齐统一前端需求设计说明（登录/RBAC/租户/字典等） |

## 8. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：入场检查与轨道选择（整体+后端+第三方集成）、总体分层架构、技术选型 5 条 ADR、模块详细设计（内核/核心/补齐/工具链）、关键设计决策 7 条、需求设计追溯摘要 |
