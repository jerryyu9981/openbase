# OpenBase 开发需求文档 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 关联输入 | 单版本规划文档 v1.0.0、本版本 Backlog v1.0.0（BL-001~BL-031）、候选需求池 v0.6.0、统一前端需求设计说明 v0.2.0 |

---

## 1. 需求概述

### 1.1 业务目标

OpenBase v1.0.0 交付**首个可用底座**：从 OpenLLM / OpenMemory / OpenRAG 三系统抽取公共能力，建设完整公共底座包（框架内核 core + 6 核心模块 + 5 补齐模块 + CLI/CRUD/脚手架），发布 PyPI v1.0，实现"`pip install openbase` 即获全部公共能力"的独立可用闭环。

### 1.2 需求编号规则

| 前缀 | 类别 | 说明 |
|------|------|------|
| FR-CORE-xxx | 框架内核需求 | core 5 组件 |
| FR-MOD-xxx | 核心模块需求 | 6 核心模块 |
| FR-SUP-xxx | 补齐模块需求 | 5 补齐模块 |
| FR-TOOL-xxx | 工具链需求 | CLI/CRUD/脚手架/发布 |
| FR-PRO-xxx | 流程活动需求 | 审计/定源/验证等过程活动 |
| NFR-xxx | 非功能需求 | 性能/安全/兼容/质量 |
| DR-xxx | 数据需求 | 数据实体与生命周期 |
| SR-xxx | 安全需求 | 权限与安全 |
| IF-xxx | 接口需求 | 接口契约 |
| AC-xxx | 验收标准 | 每条需求的验收条件 |

## 2. 功能需求

### 2.1 框架内核（FR-CORE）

#### FR-CORE-001 base models

**用户故事**：As a 开发工程师，I want openbase 提供统一的 User/Role/Permission/Tenant/AuditLog 基础模型，so that 各模块可复用统一数据实体，避免各系统模型漂移。

**功能描述**：
- core/models 提供 User、Role、Permission、Tenant、AuditLog 五个基础模型
- 字段与三系统现有模型对齐（抽取审计后确认）
- SQLAlchemy 映射正确，支持 create_all 建表
- 模型定义统一继承 Base（声明式基类）

**验收标准**（AC-CORE-001）：
1. 5 个模型可正常 import，字段与三系统对齐
2. 可 create_all 建表，表结构正确
3. 模型间关联关系（用户-角色-权限、用户-租户）正确

**优先级**：P0（Phase 2） | **Backlog**：BL-003 | **需求 ID**：C-001

#### FR-CORE-002 DB session 管理

**用户故事**：As a 开发工程师，I want openbase 提供统一的 DB session 工厂与 Alembic 迁移模板，so that 各模块数据库操作一致且可迁移。

**功能描述**：
- core/db 提供 session 工厂（依赖注入式，FastAPI 生命周期管理）
- Alembic 迁移模板（autogenerate 可用）
- session 创建/关闭正确，支持多模块共用同一引擎

**验收标准**（AC-CORE-002）：
1. session 可创建/关闭，无泄漏
2. Alembic 迁移模板可用，autogenerate 可生成迁移
3. 多模块共用同一引擎无冲突

**优先级**：P0（Phase 2） | **Backlog**：BL-004 | **需求 ID**：C-002

#### FR-CORE-003 通用依赖注入

**用户故事**：As a 开发工程师，I want openbase 提供 get_db / get_current_user 等通用 deps，so that 各模块可直接复用鉴权与数据库依赖。

**功能描述**：
- core/deps 提供 get_db（数据库会话依赖）
- 提供 get_current_user（当前用户依赖，基于 JWT）
- 可在 FastAPI 路由中作为 Depends 使用

**验收标准**（AC-CORE-003）：
1. get_db 可作为 Depends 使用，会话生命周期正确
2. get_current_user 可解析当前用户，未认证时返回 401
3. 依赖注入与 FastAPI 兼容

**优先级**：P0（Phase 2） | **Backlog**：BL-005 | **需求 ID**：C-003

#### FR-CORE-004 统一异常处理

**用户故事**：As a 开发工程师，I want openbase 提供统一异常基类与错误码体系，so that 所有模块错误返回格式一致。

**功能描述**：
- core/errors 提供 BaseError 基类与错误码定义
- 统一 JSON 错误响应格式：`{code, message, request_id}`
- FastAPI 全局异常处理器捕获

**验收标准**（AC-CORE-004）：
1. 异常可被 FastAPI 捕获并返回统一 JSON 格式响应
2. 错误码定义完整（鉴权/参数/业务/系统分级）
3. 响应含 request_id 便于排查

**优先级**：P0（Phase 2） | **Backlog**：BL-006 | **需求 ID**：C-004

#### FR-CORE-005 settings 配置驱动

**用户故事**：As a 开发工程师，I want openbase 提供 enable_module/disable_module 配置驱动机制与 init_app 自动装配，so that 各系统按需启用模块、最小改动接入。

**功能描述**：
- settings.py 提供 enable_module / disable_module
- core/__init__.py 提供 init_app(settings) 自动装配入口
- 模块启停不互相影响（弱依赖）

**验收标准**（AC-CORE-005）：
1. settings.enable_module("xxx") 可执行
2. settings.disable_module("xxx") 可执行且不影响其他模块
3. init_app(settings) 自动装配可用

**优先级**：P0（Phase 2） | **Backlog**：BL-007 | **需求 ID**：C-005

### 2.2 核心模块（FR-MOD）

#### FR-MOD-001 API 服务框架（audit 模块）

**用户故事**：As a 开发工程师，I want openbase 提供审计中间件/限流/指标/健康检查能力，so that 各系统 API 服务具备统一的服务治理能力。

**功能描述**：
- modules/audit 提供审计中间件、限流（rate_limit）、指标采集（metrics）、健康检查（health_service）
- 从 OpenLLM middleware/ 抽取后包化
- 中间件可独立启用

**验收标准**（AC-MOD-001）：
1. 审计中间件生效，记录请求审计日志
2. 限流功能正常，超限返回 429
3. 健康检查 /health 返回 200
4. 中间件附加延迟 < 5ms

**优先级**：P0（Phase 3） | **Backlog**：BL-008 | **需求 ID**：M-001

#### FR-MOD-002 鉴权认证 RBAC（auth 模块）

**用户故事**：As a 平台管理员，I want openbase 提供 JWT 鉴权 + RBAC 权限矩阵 + OIDC 增强，so that 四系统用户/角色/权限统一管理。

**功能描述**：
- modules/auth 提供 jwt.py（JWT 签发/验证）、rbac.py（RBAC 权限矩阵）、oidc.py（OIDC 增强）
- 从 OpenLLM edgerouter/auth + OpenMemory abac/oidc 合并抽取
- 支持登录/刷新/找回密码接口

**验收标准**（AC-MOD-002）：
1. JWT 签发与验证正确，Token 过期拒绝访问
2. RBAC+ABAC 双层权限矩阵正确
3. 登录/刷新接口可用，未认证返回 401
4. 密码存储加密（bcrypt 或等价）

**优先级**：P0（Phase 4） | **Backlog**：BL-009 | **需求 ID**：M-002

#### FR-MOD-003 多租户隔离（tenant 模块）

**用户故事**：As a 平台管理员，I want openbase 提供多租户隔离（EdgeRouter/配额/限流），so that 多租户数据不串租户。

**功能描述**：
- modules/tenant 提供 edge_router（租户路由）、quota（配额）、rate_limiter（限流）
- 从 OpenMemory multitenancy/ 复制级抽取
- 支持租户上下文传递

**验收标准**（AC-MOD-003）：
1. 多租户隔离生效，数据不串租户
2. 租户路由延迟 < 1ms
3. 配额限制生效
4. 租户上下文在请求链中正确传递

**优先级**：P0（Phase 4） | **Backlog**：BL-010 | **需求 ID**：M-003

#### FR-MOD-004 MCP 封装（mcp 模块）

**用户故事**：As a 开发工程师，I want openbase 提供基于 FastMCP 的统一 MCP 工具封装，so that 各系统工具以 decorator 声明方式注册。

**功能描述**：
- modules/mcp 提供 FastMCP 实例、工具注册 decorator、MCP 鉴权
- 从 FastMCP（实现层）+ OpenRAG/OpenMemory（工具定义迁移）改写迁移
- 遵循 2026-07 MCP 规范（可缓存 list 结果）

**验收标准**（AC-MOD-004）：
1. FastMCP 实例可创建，工具可注册和调用
2. MCP 协议适配正确，list 结果可缓存
3. 工具鉴权生效（auth 模块启用时）

**优先级**：P0（Phase 3） | **Backlog**：BL-011 | **需求 ID**：M-004

#### FR-MOD-005 可观测性（observability 模块）

**用户故事**：As a 运维人员，I want openbase 提供链路追踪/指标/评测能力，so that 各系统调用可观测、可评测。

**功能描述**：
- modules/observability 提供 otel（OpenTelemetry 追踪）、langfuse（评测对接）、business_metrics（业务指标）、dashboards（Grafana 仪表盘 JSON）
- 实现层用 OTel + Langfuse（OTLP 对接），内容复用 OpenMemory 业务指标
- 支持 GenAI 语义约定（gen_ai.operation.name 等 span 规范）

**验收标准**（AC-MOD-005）：
1. OTel 追踪可用，span 上报 OTLP 端点
2. Langfuse OTLP 端点可对接，追踪数据可上报
3. 业务指标定义迁移完成，Grafana 仪表盘 JSON 可用
4. GenAI span 规范正确

**优先级**：P0（Phase 3） | **Backlog**：BL-012 | **需求 ID**：M-005

#### FR-MOD-006 配置密钥中心（config 模块）

**用户故事**：As a 运维人员，I want openbase 提供三级配置合并/热加载/版本回滚，so that 配置变更可审计、可回滚。

**功能描述**：
- modules/config 提供 manager（三级配置合并）、hot_reload（热加载）、watcher（配置监听）
- 从 OpenRAG config_center/ 复制级抽取
- 支持配置版本回滚

**验收标准**（AC-MOD-006）：
1. 三级配置合并正确（默认<环境<运行时）
2. 热加载生效，配置变更无需重启
3. 版本回滚 100% 可用

**优先级**：P0（Phase 3） | **Backlog**：BL-012 | **需求 ID**：M-006

### 2.3 补齐模块（FR-SUP）

#### FR-SUP-001 组织架构（org 模块）

**用户故事**：As a 平台管理员，I want openbase 提供部门树/用户部门关联/按部门授权，so that 组织架构管理标准化。

**验收标准**（AC-SUP-001）：部门树 CRUD 可用，用户-部门关联正确，按部门授权生效。
**优先级**：P0（Phase 5） | **Backlog**：BL-022 | **需求 ID**：S-001

#### FR-SUP-002 数据字典（dict 模块）

**用户故事**：As a 平台管理员，I want openbase 提供枚举/选项配置，so that 各系统枚举管理统一且前端可联动。

**验收标准**（AC-SUP-002）：字典 CRUD 可用，选项配置保存后联动刷新。
**优先级**：P0（Phase 5） | **Backlog**：BL-023 | **需求 ID**：S-002

#### FR-SUP-003 定时任务（scheduler 模块）

**用户故事**：As a 平台管理员，I want openbase 提供 APScheduler 封装/任务 CRUD/执行日志，so that 定时任务统一管理。

**验收标准**（AC-SUP-003）：任务可创建/启停，执行日志可查询，APScheduler 集成正常。
**优先级**：P0（Phase 5） | **Backlog**：BL-024 | **需求 ID**：S-003

#### FR-SUP-004 统一文件存储（storage 模块）

**用户故事**：As a 平台管理员，I want openbase 提供本地/MinIO/S3 适配，so that 各系统文件存储统一。

**验收标准**（AC-SUP-004）：上传/下载/预览全流程可用，三种后端适配可切换。
**优先级**：P1（Phase 5） | **Backlog**：BL-025 | **需求 ID**：S-004

#### FR-SUP-005 通知中心（notify 模块）

**用户故事**：As a 平台管理员，I want openbase 提供 SSE 推送/站内信/已读管理，so that 各系统通知能力统一。

**验收标准**（AC-SUP-005）：SSE 实时推送可用，站内信/已读状态持久化。
**优先级**：P1（Phase 5） | **Backlog**：BL-026 | **需求 ID**：S-005

### 2.4 工具链（FR-TOOL）

#### FR-TOOL-001 openbase-cli

**用户故事**：As a 开发工程师，I want openbase-cli 提供 create-project / create-module / create-crud 命令，so that 新系统/新模块一键初始化。

**验收标准**（AC-TOOL-001）：三命令执行通过，生成工程可运行。
**优先级**：P0（Phase 5） | **Backlog**：BL-027 | **需求 ID**：T-001

#### FR-TOOL-002 BaseCRUDRouter

**用户故事**：As a 开发工程师，I want openbase 提供通用 CRUD 路由自动生成，so that 标准增删改查接口零手写。

**验收标准**（AC-TOOL-002）：生成路由与手写等价（延迟差 <5%），支持分页/搜索/排序。
**优先级**：P0（Phase 5） | **Backlog**：BL-028 | **需求 ID**：T-002

#### FR-TOOL-003 模板脚手架

**用户故事**：As a 开发工程师，I want openbase 提供标准工程结构 + 初始化脚本，so that 新项目标准化创建。

**验收标准**（AC-TOOL-003）：create-project 生成标准工程结构，初始化脚本可运行。
**优先级**：P0（Phase 5） | **Backlog**：BL-029

#### FR-TOOL-004 PyPI 发布与文档

**用户故事**：As a 开发工程师，I want openbase v1.0.0 发布到 PyPI 并提供 Quickstart + 模块使用指南，so that 各系统可 pip 安装使用。

**验收标准**（AC-TOOL-004）：全新环境 pip install openbase 成功，按文档三步启用模块可用。
**优先级**：P0（Phase 6） | **Backlog**：BL-031

### 2.5 流程活动需求（FR-PRO）

#### FR-PRO-001 三系统成熟度审计（BL-001）
**验收标准**：审计报告覆盖后端 6 模块 × 3 系统 = 18 项五维度评分，每项有评分与来源标注。**P0（Phase 1）**

#### FR-PRO-002 模块抽取来源决策（BL-002）
**验收标准**：6 模块逐模块来源标注 + 抽取范围 + 改动量（复制级/中等/改写迁移）。**P0（Phase 1）**

#### FR-PRO-003 FastMCP/Langfuse 预研（BL-013/014）
**验收标准**：预研报告输出，明确可行或需备选方案。**P1（Phase 1）**

#### FR-PRO-004 组件集成验证（BL-018/019/020）
**验收标准**：FastMCP 实例可创建、Langfuse OTLP 可对接、OTel GenAI span 规范可用。**P1（Phase 1）**

#### FR-PRO-005 弱依赖与 Git 历史验证（BL-015/016）
**验收标准**：6 模块逐一独立启用 6/6 通过；git log 可查抽取文件来源。**P1（Phase 4）**

#### FR-PRO-006 双接口体系设计验证（BL-021）
**验收标准**：两套接口认证模型独立，共享网关/底座/鉴权体系/可观测，前端不直连 AI 接口。**P1（Phase 4）**

## 3. 非功能需求

| ID | 类别 | 指标 | 目标值 | 验证方法 |
|----|------|------|--------|---------|
| NFR-001 | 性能 | 多租户路由延迟 | < 1ms | 基准测试 |
| NFR-002 | 性能 | 中间件附加延迟 | < 5ms | 基准测试 |
| NFR-003 | 性能 | CRUD 生成接口与手写等价 | 延迟差 < 5% | 对比测试 |
| NFR-004 | 可靠性 | 单模块故障不影响整体 | 6/6 通过 | 逐模块禁用验证 |
| NFR-005 | 可靠性 | 配置变更可回滚 | 100% | 配置中心回滚测试 |
| NFR-006 | 质量 | 单元测试覆盖率 | ≥ 85% | pytest coverage |
| NFR-007 | 质量 | 静态检查 | ruff 零错误 | ruff check |
| NFR-008 | 兼容性 | Python 版本 | 3.11+ | CI 矩阵测试 |
| NFR-009 | 兼容性 | FastAPI 版本 | 当前稳定版 | pip 依赖验证 |
| NFR-010 | 安全 | JWT 鉴权 | RBAC+ABAC 双层 | 安全测试 |
| NFR-011 | 安全 | 密钥存储 | 加密存储 | 安全审计 |
| NFR-012 | 可维护性 | 模块弱依赖 | 模块间无强耦合 | Code Review |
| NFR-013 | 可观测性 | 日志/追踪/指标 | OTel + Langfuse + Prometheus | 集成验证 |

## 4. 数据需求

| ID | 数据实体 | 说明 | 来源模块 | 生命周期 |
|----|---------|------|---------|---------|
| DR-001 | User | 用户（账号/密码哈希/状态） | core/models | 常驻，可禁用不可物理删除（建议软删） |
| DR-002 | Role / Permission | 角色/权限点（RBAC 矩阵） | core/models | 常驻 |
| DR-003 | Tenant | 租户（隔离级别/配额） | core/models | 常驻 |
| DR-004 | AuditLog | 审计日志 | core/models + audit 模块 | 保留 ≥ 180 天 |
| DR-005 | Department | 部门树 | org 模块 | 常驻 |
| DR-006 | DictItem | 数据字典项 | dict 模块 | 常驻 |
| DR-007 | ScheduleTask | 定时任务定义/执行日志 | scheduler 模块 | 常驻 + 日志保留 90 天 |
| DR-008 | FileRecord | 文件元数据 | storage 模块 | 随文件生命周期 |
| DR-009 | Notification | 通知/已读状态 | notify 模块 | 已读状态持久化 |
| DR-010 | ConfigVersion | 配置版本（回滚） | config 模块 | 保留 ≥ 10 个版本 |

**数据源**：OpenBase 自身建表（PostgreSQL 多租户 Schema 隔离）；迁移由 Alembic 管理。

## 5. 权限与安全需求

| ID | 需求 | 说明 |
|----|------|------|
| SR-001 | 统一鉴权 | JWT 签发/验证统一；Token 默认 2h，刷新 7d |
| SR-002 | RBAC+ABAC 双层权限 | 角色权限矩阵 + 属性权限（OIDC 增强） |
| SR-003 | 双接口体系 | AI 服务接口（服务级 API Key）与管理接口（用户级 JWT）认证隔离 |
| SR-004 | 密码安全 | bcrypt 加密存储，禁止明文 |
| SR-005 | 密钥管理 | 配置中心密钥加密存储（config 模块） |
| SR-006 | 审计日志 | 登录/权限变更/敏感操作记录审计日志 |
| SR-007 | 多租户隔离 | 数据隔离 + 配额 + 限流，不串租户 |
| SR-008 | MCP 工具鉴权 | 工具调用鉴权（auth 启用时） |
| SR-009 | 依赖安全 | 依赖审计（pip-audit 或等价），无高危漏洞 |

## 6. 接口需求

### 6.1 管理接口（用户级 JWT/RBAC）

| 接口域 | 说明 | 提供方 |
|--------|------|--------|
| /api/v1/auth/* | 登录/刷新/登出/当前用户 | auth 模块 |
| /api/v1/users/roles/permissions | 用户/角色/权限管理 CRUD | auth 模块 |
| /api/v1/tenants | 租户管理 | tenant 模块 |
| /api/v1/org | 部门树 | org 模块 |
| /api/v1/dicts | 数据字典 | dict 模块 |
| /api/v1/schedules | 定时任务 | scheduler 模块 |
| /api/v1/files | 文件上传下载 | storage 模块 |
| /api/v1/notifications | 通知/SSE | notify 模块 |
| /api/v1/configs | 配置中心（含回滚） | config 模块 |
| /health | 健康检查 | audit 模块 |

### 6.2 AI 服务接口（服务级 API Key）

| 接口域 | 说明 | 提供方 |
|--------|------|--------|
| MCP 工具（list/call） | AI 能力经 MCP 暴露 | mcp 模块 |
| 审计/追踪上报 | OTLP 对接 Langfuse | observability 模块 |

### 6.3 接口契约通用约定

- 错误码统一格式：`{code, message, request_id}`（FR-CORE-004）
- 鉴权失败 401、无权限 403、限流 429、参数错误 422、系统错误 500
- 接口文档由 FastAPI 自动生成（OpenAPI /docs）

## 7. 约束、边界与排除项

### 7.1 约束

| 约束 | 说明 |
|------|------|
| 技术栈 | Python 3.11+ / FastAPI / SQLAlchemy / Alembic / PostgreSQL / Redis |
| 组件化 | FastMCP / Langfuse / OpenTelemetry / APScheduler 直接采用 |
| 复用原则 | 择优抽取 + 三不原则（不删除/不急于替换/不回退特色） |
| 单一事实源 | 公共能力唯一实现在 openbase 包 |
| 配置驱动 | 模块弱依赖、可插拔 |

### 7.2 排除项（本版本不做）

| 排除项 | 归属版本 |
|--------|---------|
| 四系统回灌接入 | v1.1.0 |
| AI 规则适配（.cursor/rules） | v1.1.0 |
| 统一前端（登录/RBAC/租户等页面） | v1.2.0（需求已细化于统一前端需求设计说明） |
| 国际化 / 测试基座 / 文档站点 / 示例项目 | v1.3+ |
| Qdrant / GPTCache 集成 | v1.0.0 内按 CI-004/005 候选，正式纳入需评审 |

## 8. 验收标准汇总

### 8.1 版本级成功指标（对齐单版本规划 §1.4）

| 指标 | 目标值 | 对应需求 |
|------|--------|---------|
| 核心模块抽取完成 | 6/6 | FR-MOD-001~006 |
| 补齐模块建设完成 | 5/5 | FR-SUP-001~005 |
| 单元测试覆盖率 | ≥ 85% | NFR-006 |
| 模块独立启用验证 | 11/11 | FR-PRO-005 |
| 三系统审计完成 | 18 项 | FR-PRO-001 |
| 多租户路由延迟 | < 1ms | NFR-001 |
| 中间件附加延迟 | < 5ms | NFR-002 |
| ruff 静态检查 | 零错误 | NFR-007 |
| PyPI v1.0 发布 | 成功 | FR-TOOL-004 |
| CLI 工具链 | 3/3 命令 | FR-TOOL-001 |

### 8.2 验收方法

- 功能验收：自动化测试（pytest）+ 手工验证清单
- 性能验收：基准测试（pytest-benchmark 或等价）
- 安全验收：安全测试 + 依赖审计
- 发布验收：全新环境 pip install + 三步启用验证

## 9. 优先级确认

| 优先级 | 需求数 | 说明 |
|--------|--------|------|
| P0 | 20 | 内核 5 + 核心模块 6 + 补齐模块 3（org/dict/scheduler）+ 工具链 4 + 流程活动 2 |
| P1 | 11 | storage/notify + 预研/验证类 |

> P0/P1 全部有验收标准 ✅；范围与单版本规划 v1.0.0 一致，未扩大 Step 0 范围。

## 10. 风险与开放问题

| ID | 风险/问题 | 等级 | 缓解措施 |
|----|----------|------|---------|
| RQ-001 | 三系统代码访问受限 | P1 | 提前申请权限；备选：基于文档抽取（对齐单版本规划 R-006） |
| RQ-002 | FastMCP/Langfuse 预研未通过 | P1 | 备选方案：直接实现 MCP 协议 / 仅 OTel+Prometheus（对齐 R-004/R-005） |
| RQ-003 | ABAC/OIDC 与 RBAC 合并冲突 | P1 | 接口适配层设计，两种模式可独立启用（对齐 R-007） |
| RQ-004 | 还债占比 12.9% < 15% | P2 | 已记录批准理由；v1.1.0 回灌阶段补充还债计划 |
| RQ-005 | 开放问题：Qdrant/GPTCache（CI-004/005）是否纳入 v1.0.0 | - | 建议 v1.0.0 内先保持候选，Qdrant 供 OpenRAG/OpenMemory 共用场景在 v1.1.0 回灌时评估 |

## 11. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | RA-OpenBase-Dev | 初始创建：基于 Step 0 批准的 Backlog（BL-001~BL-031）细化 28 条功能需求（FR-CORE/MOD/SUP/TOOL/PRO）+ 13 项非功能需求 + 数据/权限/接口需求 + 验收标准；范围与单版本规划 v1.0.0 一致，前端需求归属 v1.2.0 |
