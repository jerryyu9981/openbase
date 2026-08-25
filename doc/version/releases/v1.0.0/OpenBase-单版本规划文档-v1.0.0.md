# OpenBase 单版本规划文档 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-24 |
| 最后更新 | 2026-08-25 |
| 前身版本 | v0.1.0（已并入本版本，见版本范围变更记录 VC-001） |

---

## 1. 版本目标

### 1.1 业务目标

从 OpenLLM、OpenMemory、OpenRAG 三系统抽取公共能力，形成 openbase 完整底座包（框架内核 core + 6 核心模块 + 5 补齐模块 + CLI/CRUD/脚手架），发布 PyPI v1.0，实现"`pip install openbase` 即获全部公共能力"的首个可用闭环。

> 本版本由原 v0.1.0（抽取验证）与原 v1.0.0（补齐发布）合并而成（VC-001），四系统回灌移至 v1.1.0。

### 1.2 用户目标

- 四系统开发者可通过 `pip install openbase` 引入全部公共能力
- 单模块可独立启用/禁用（配置驱动 `settings.enable_module()`）
- 新系统可通过 `openbase-cli create-project` 一键初始化工程
- 抽取后的模块功能与原系统等价

### 1.3 技术目标

- 建立 openbase 包目录结构（core/ + modules/ + cli/ + crud/）
- 完成 6 核心模块从三系统抽取 + 5 补齐模块（org/dict/scheduler/storage/notify）建设
- 交付 openbase-cli / BaseCRUDRouter / 模板脚手架
- 验证单模块独立启用可用（弱依赖）
- PyPI v1.0 发布 + Quickstart + 模块使用指南

### 1.4 成功指标

| 指标 ID | 指标名称 | 目标值 | 验证方法 |
|---------|----------|--------|----------|
| KPI-001 | 核心模块抽取完成数 | 6/6 | 逐一验证模块可独立 import 和启用 |
| KPI-002 | 补齐模块建设完成数 | 5/5 | org/dict/scheduler/storage/notify 可独立启用 |
| KPI-003 | 单元测试覆盖率 | ≥85% | pytest coverage 报告 |
| KPI-004 | 模块独立启用验证 | 11/11 通过 | 每模块独立 settings.enable_module 后功能正常 |
| KPI-005 | 三系统成熟度审计完成 | 100% | 审计报告覆盖后端 6 模块 × 3 系统 = 18 项五维度评分 |
| KPI-006 | 多租户路由延迟 | <1ms | 基准测试 |
| KPI-007 | 中间件附加延迟 | <5ms | 基准测试 |
| KPI-008 | ruff 静态检查 | 零错误 | ruff check |
| KPI-009 | PyPI v1.0 发布 | 成功 | pip install openbase 可安装并使用 |
| KPI-010 | CLI 工具链 | 3/3 命令可用 | create-project / create-module / create-crud 执行通过 |

## 2. 包目录结构设计

### 2.1 目标目录结构

```
openbase/                      # PyPI 包：pip install openbase
├── core/                      # 框架内核（强绑定，所有模块依赖）
│   ├── __init__.py            # init_app(settings) 自动装配入口
│   ├── models/                # base models（User/Role/Permission/Tenant/AuditLog）
│   │   ├── __init__.py
│   │   ├── user.py            # User 模型
│   │   ├── role.py            # Role 模型
│   │   ├── permission.py      # Permission 模型
│   │   ├── tenant.py          # Tenant 模型
│   │   └── audit_log.py       # AuditLog 模型
│   ├── db/                    # session 管理 + 迁移模板
│   │   ├── __init__.py
│   │   ├── session.py         # DB session 工厂
│   │   └── migrations/        # Alembic 迁移模板
│   ├── deps/                  # 通用依赖注入
│   │   ├── __init__.py
│   │   ├── database.py        # get_db()
│   │   └── auth.py            # get_current_user()
│   └── errors/                # 统一异常处理
│       ├── __init__.py
│       ├── base.py            # BaseError 基类
│       └── codes.py           # 错误码定义
├── modules/                   # 插件模块（可挂载，弱依赖，配置驱动）
│   ├── auth/                  # 鉴权 RBAC（JWT/OIDC/权限矩阵）
│   │   ├── __init__.py        # router + init_app
│   │   ├── jwt.py             # JWT 签发/验证
│   │   ├── rbac.py            # RBAC 权限矩阵
│   │   └── oidc.py            # OIDC 增强（来自 OpenMemory）
│   ├── tenant/                # 多租户（路由/隔离/配额/限流）
│   │   ├── __init__.py        # router + init_app
│   │   ├── edge_router.py     # EdgeRouter 租户路由
│   │   ├── quota.py           # 配额管理
│   │   └── rate_limiter.py    # 限流
│   ├── audit/                 # 审计日志 + API 服务框架
│   │   ├── __init__.py        # middleware 注册
│   │   ├── middleware.py      # 审计中间件
│   │   ├── rate_limit.py      # 限流
│   │   ├── metrics.py         # 指标采集
│   │   └── health.py          # health_service
│   ├── observability/         # 可观测（otel/trace/metrics）
│   │   ├── __init__.py        # init_app
│   │   ├── otel.py            # OpenTelemetry 追踪
│   │   ├── langfuse.py        # Langfuse 评测对接
│   │   ├── business_metrics.py # 业务指标（来自 OpenMemory）
│   │   └── dashboards/        # Grafana 仪表盘 JSON
│   ├── config/                # 配置中心（热加载/版本回滚）
│   │   ├── __init__.py        # init_app
│   │   ├── manager.py         # 三级配置合并
│   │   ├── hot_reload.py      # 热加载
│   │   └── watcher.py         # 配置监听
│   └── mcp/                   # MCP 工具封装
│       ├── __init__.py        # FastMCP 实例
│       ├── decorator.py       # 工具注册 decorator
│       └── auth.py            # MCP 鉴权
├── modules/org/               # 组织架构（部门树/用户部门关联/按部门授权）
├── modules/dict/              # 数据字典（枚举/选项配置）
├── modules/scheduler/         # 定时任务（APScheduler 封装/任务 CRUD/执行日志）
├── modules/storage/           # 统一文件存储（本地/MinIO/S3 适配）
├── modules/notify/            # 通知中心（SSE 推送/站内信/已读管理）
├── cli/                       # openbase-cli（create-project / create-module / create-crud）
├── crud/                      # BaseCRUDRouter 通用 CRUD 生成
├── settings.py                # 配置驱动开关
├── pyproject.toml             # 包定义
├── conftest.py                # 测试基座
└── tests/                     # 测试目录
    ├── test_core/
    └── test_modules/
```

### 2.2 模块启用机制

```python
from openbase import init_app, settings

settings.enable_module("auth")          # 鉴权 RBAC
settings.enable_module("tenant")        # 多租户隔离
settings.enable_module("audit")         # 审计日志 + API 框架
settings.enable_module("observability") # 可观测性
settings.enable_module("config")        # 配置中心
settings.enable_module("mcp")           # MCP 封装

app = init_app(settings)                # 框架内核自动装配
app.include_router(auth.router)        # 插件挂载（FastAPI 原生）
```

### 2.3 模块依赖关系

```
core/（强绑定 - 所有模块基础依赖）
  ├── models/      ← User/Role/Permission/Tenant/AuditLog
  ├── db/          ← session、迁移模板
  ├── deps/        ← get_db, get_current_user
  └── errors/      ← 统一异常

modules/（弱依赖 - 可插拔，配置驱动）
  ├── auth/           ← 依赖 core.models (User/Role/Permission)
  ├── tenant/         ← 依赖 core.models (Tenant)
  ├── audit/          ← 依赖 core.models (AuditLog)
  ├── observability/  ← 无模块间依赖（仅依赖 core）
  ├── config/         ← 无模块间依赖（仅依赖 core）
  └── mcp/            ← 可选依赖 auth（工具鉴权）
```

**依赖规则**：
- core 层是强绑定，所有模块必须依赖 core
- modules 层是弱依赖，单模块禁用不影响其他模块
- modules 间通过 FastAPI 原生挂载：`add_middleware` / `include_router` / `Depends`
- mcp 模块可选用 auth 模块的鉴权能力，但 auth 禁用时 mcp 仍可独立运行（降级为无鉴权）

## 3. 版本范围

### 3.1 包含范围

| 范围项 | 来源系统 | 抽取内容 | 改动量 |
|--------|----------|----------|--------|
| core/models | 新建 | User/Role/Permission/Tenant/AuditLog 基础模型 | 新建（对齐三系统字段） |
| core/db | 新建 | session 管理 + Alembic 迁移模板 | 新建 |
| core/deps | 新建 | 通用依赖注入（get_db, get_current_user 等） | 新建 |
| core/errors | 新建 | 统一异常处理类与错误码体系 | 新建 |
| settings.py | 新建 | 配置驱动开关（enable_module/disable_module） | 新建 |
| modules/audit | OpenLLM | middleware/audit、rate_limit、metrics、otel、health_service | 抽取后包化 |
| modules/auth | OpenLLM + OpenMemory | edgerouter/auth（rbac/jwt）+ OpenMemory abac/oidc 增强 | 中等 |
| modules/tenant | OpenMemory | multitenancy/（edge_router、quota、rate_limiter、适配器） | 复制级 |
| modules/mcp | FastMCP + OpenRAG/OpenMemory | FastMCP 协议/传输/生命周期 + 工具定义迁移为 decorator | 改写迁移 |
| modules/observability | OTel/Langfuse + OpenMemory | OTel+Langfuse 实现层 + OpenMemory business_metrics/仪表盘JSON/告警规则 | 改写迁移 |
| modules/config | OpenRAG | config_center/（manager、hot_reload、watcher） | 复制级 |
| modules/org | OpenLLM 雏形完善 | 部门树、用户-部门关联、按部门授权 | 新建 |
| modules/dict | 新建（对标 Nuct） | 枚举/选项配置、前端字典组件联动 | 新建 |
| modules/scheduler | 新建（对标 Nuct） | APScheduler 封装、任务 CRUD、执行日志 | 新建 |
| modules/storage | 新建 | 本地/MinIO/S3 适配、上传下载预览 | 新建 |
| modules/notify | 复用 OpenLLM sse_adapter | SSE 推送、站内信、已读管理 | 新建 |
| openbase-cli | 新建 | create-project / create-module / create-crud | 新建 |
| BaseCRUDRouter | 新建（参考 fastapi-crudrouter） | FastAPI 通用 CRUD 路由自动生成 | 新建 |
| 模板脚手架 | 新建 | 标准工程结构 + 初始化脚本 | 新建 |
| PyPI 发布 + 文档 | v1.0 | pip install openbase + Quickstart + 模块使用指南 | 发布 |
| 三系统成熟度审计 | - | 后端 6 模块 × 3 系统完整审计（五维度评分） | 新建 |
| 抽取来源决策 | - | 逐模块选定最成熟来源，标注抽取范围 | 新建 |

### 3.2 不包含范围

| 排除项 | 说明 | 延期至 |
|--------|------|--------|
| 四系统回灌接入 | S3 阶段（依赖四系统团队配合，灰度验证周期不可控） | v1.1.0 |
| AI 规则适配 | .cursor/rules（或 AGENTS.md），回灌时生成规范代码才有意义 | v1.1.0 |
| 统一前端（公共模块 + 动态业务模块） | 前端完整化独立成版 | v1.2.0 |
| 国际化 / 测试基座 / 文档站点 / 示例项目 | 生态完善阶段 | v1.3+ |

## 4. 三系统成熟度矩阵

基于方案文档 §4.2 抽查评估（正式抽取前需按五维度完整评分确认）：

| 公共模块 | OpenLLM | OpenMemory | OpenRAG | 最佳来源 | 抽取方式 |
|----------|:-------:|:----------:|:-------:|----------|----------|
| API 服务框架 | **5.0** | 4.0 | 4.0 | OpenLLM | 抽取后包化 |
| 鉴权 RBAC | **5.0** | **5.0** | 3.0 | OpenLLM + OpenMemory | RBAC/JWT 从 OpenLLM，ABAC/OIDC 从 OpenMemory |
| 多租户隔离 | 4.0 | **5.0** | 3.0 | OpenMemory | 复制级（EdgeRouter 全栈） |
| MCP 封装 | 3.0 | 3.0 | **4.5** | FastMCP + OpenRAG | 改写迁移（协议层用 FastMCP，工具定义从 OpenRAG/OpenMemory） |
| 可观测性 | 4.0 | **5.0** | 3.0 | OpenMemory + OTel/Langfuse | 改写迁移（平台不复制，内容复用） |
| 配置中心 | 4.0 | 4.0 | **5.0** | OpenRAG | 复制级（三级合并+回滚） |

**评分口径**：基于目录结构与关键文件抽查（OpenLLM rbac/tenant_isolation、OpenMemory edge_router/auth、OpenRAG config_center/mcp_server）。正式抽取前按五维度（功能/代码/测试/文档/生产验证）做完整评分确认。

## 5. 版本依赖清单

| 依赖 ID | 依赖类型 | 依赖项 | 负责人 | 状态 | 风险 | 确认方式 |
|---------|----------|--------|--------|------|------|----------|
| D-001 | 代码库 | OpenLLM 仓库（rbac/tenant_isolation/middleware） | AD-OpenBase-Dev | 待确认 | 低 | 申请 GitLab 仓库访问权限 |
| D-002 | 代码库 | OpenMemory 仓库（edge_router/auth/business_metrics） | AD-OpenBase-Dev | 待确认 | 低 | 申请 GitLab 仓库访问权限 |
| D-003 | 代码库 | OpenRAG 仓库（config_center/mcp_server） | AD-OpenBase-Dev | 待确认 | 低 | 申请 GitLab 仓库访问权限 |
| D-004 | 技术栈 | Python 3.11+ 环境 | AD-OpenBase-Dev | 已确认 | 无 | 本地已验证 |
| D-005 | 技术栈 | FastAPI 当前稳定版本 | AD-OpenBase-Dev | 已确认 | 无 | pip list 确认 |
| D-006 | 技术栈 | PostgreSQL 14+ / Redis 6+ | AD-OpenBase-Dev | 已确认 | 低 | 本地环境已有 |
| D-007 | 外部库 | FastMCP 库可用性与版本兼容 | AD-OpenBase-Dev | 待验证 | 中 | Phase 1 预研验证 |
| D-008 | 外部库 | OpenTelemetry Python SDK | AD-OpenBase-Dev | 已确认 | 低 | pip install 验证 |
| D-009 | 外部库 | Langfuse SDK 可用性与 OTLP 对接 | AD-OpenBase-Dev | 待验证 | 中 | Phase 1 预研验证 |
| D-010 | 人力 | 后端开发工程师 ≥1 人 | PM-OpenBase-Dev | 待确认 | 中 | 团队分配 |

## 6. 版本风险清单

| 风险 ID | 风险描述 | 级别 | 概率 | 影响 | 缓解措施 | 负责人 |
|---------|----------|------|------|------|----------|--------|
| R-001 | 抽取破坏现有系统稳定性 | P0 | 中 | 高 | 灰度迁移、Git 历史保留、逐系统验证后下线重复件 | AD-OpenBase-Dev |
| R-002 | 模块强耦合（共享模型） | P1 | 中 | 中 | base models 稳定化 + 模块独立版本 + 兼容性测试 | AA-OpenBase-Dev |
| R-003 | 框架抽象过度 | P2 | 低 | 中 | 内核最小化、插件独立演进、避免过度设计 | AA-OpenBase-Dev |
| R-004 | FastMCP 库不满足需求 | P1 | 低 | 高 | Phase 1 预研验证；备选方案：直接实现 MCP 协议 | AD-OpenBase-Dev |
| R-005 | Langfuse OTLP 对接复杂度高 | P2 | 中 | 中 | Phase 1 预研验证；备选方案：仅使用 OTel + Prometheus | AD-OpenBase-Dev |
| R-006 | 三系统代码访问受限 | P1 | 低 | 高 | 提前申请权限；备选：基于文档抽取 | PM-OpenBase-Dev |
| R-007 | OpenMemory ABAC/OIDC 与 OpenLLM RBAC 合并冲突 | P1 | 中 | 中 | 接口适配层设计，保持两种模式可独立启用 | AA-OpenBase-Dev |

## 7. 技术债务清单

| 债务 ID | 分类 | 级别 | 描述 | 本版本偿还计划 |
|---------|------|------|------|----------------|
| TD-001 | 架构债务 | P1 | 抽取破坏现有系统稳定性 | 采用灰度迁移策略，不删除原实现（Git 历史保留） |
| TD-002 | 架构债务 | P1 | 模块强耦合（共享模型） | 设计阶段 base models 稳定化方案 |
| TD-003 | 架构债务 | P2 | 框架抽象过度风险 | 内核最小化设计原则 |
| TD-004 | 文档债务 | P2 | 团队学习成本 | 延期至 v1.0.0（Quickstart + 示例） |

**还债占比**：4/17 = 23.5% ≥ 15% ✅

## 8. 版本成功指标说明

| 指标类别 | 指标 | 目标值 | 测量方法 | 上线门槛 |
|----------|------|--------|----------|----------|
| 功能完整性 | 核心模块抽取完成 | 6/6 | 模块独立启用验证 | 必须达到 |
| 功能完整性 | 补齐模块建设完成 | 5/5 | org/dict/scheduler/storage/notify 独立启用 | 必须达到 |
| 功能完整性 | 三系统审计完成 | 100%（18 项） | 审计报告覆盖检查 | 必须达到 |
| 功能完整性 | CLI 工具链可用 | 3/3 命令 | create-project/module/crud 执行 | 必须达到 |
| 发布 | PyPI v1.0 发布 | 成功 | pip install openbase | 必须达到 |
| 性能 | 多租户路由延迟 | <1ms | 基准测试 | 必须达到 |
| 性能 | 中间件附加延迟 | <5ms | 基准测试 | 必须达到 |
| 质量 | 单元测试覆盖率 | ≥85% | pytest coverage | 必须达到 |
| 质量 | 模块弱依赖验证 | 11/11 通过 | 逐模块独立启用测试 | 必须达到 |
| 代码质量 | ruff 静态检查 | 零错误 | ruff check | 必须达到 |

## 9. 发布策略草案

| 维度 | 策略 |
|------|------|
| 发布方式 | PyPI 正式发布 v1.0.0（pip install openbase） |
| 发布渠道 | PyPI + Git 仓库 tag v1.0.0 |
| 灰度策略 | 不适用（本版本未接入生产系统，四系统回灌在 v1.1.0 灰度） |
| 回滚策略 | 发布前充分测试；发布后如发现问题发布修订版（1.0.x） |
| 发布窗口 | 2026-10-12（预计） |
| 文档配套 | Quickstart + 模块使用指南（v1.0 随包发布） |

## 10. 抽取策略与原则

> 来源：OpenLLM 方案 §1.9（v1.4.1）

### 10.1 三不原则

公共底座不是从零开发，而是从现有四系统中逐模块抽取最成熟实现汇聚而成，遵循"三不"原则：

| 原则 | 说明 |
|------|------|
| **不删除原实现** | 抽取后原系统代码冻结保留在 Git 历史，可回溯 |
| **不急于替换** | 先建公共底座 → 新功能走底座 → 旧系统灰度迁移 → 稳定后下线重复部分 |
| **不回退特色** | 各系统特色功能（对话监控、知识库管理、记忆管理、画像管理）完全不动 |

### 10.2 单一事实源

公共底座成为四系统公共能力的唯一实现（单一事实源），各系统仅保留特色功能实现，从根本上消除重复开发与实现漂移。

### 10.3 成熟度审计方法

确定"哪个系统最成熟"需执行一次公共能力成熟度审计（1-2 天），按以下维度对 6 模块 × 4 系统打分：

| 评估维度 | 权重 | 说明 |
|----------|------|------|
| 功能完整性 | 30% | 覆盖场景是否全面（如鉴权是否含刷新/找回/多端） |
| 代码质量 | 20% | 分层清晰、命名规范、错误处理 |
| 测试覆盖 | 20% | 单测/集成测试覆盖率 |
| 文档完善度 | 15% | 接口文档、部署文档、使用说明 |
| 生产验证 | 15% | 是否经真实环境验证、稳定性记录 |

**审计输出**：模块 × 系统成熟度矩阵，每个模块标注"最佳来源系统"与抽取范围。

## 11. OpenLLM 模块替换清单

> 来源：OpenLLM 方案 §1.10.1（v1.4.4）

下表列出 OpenLLM 系统接入 OpenBase 时的模块替换映射（其余系统 OpenRAG/OpenMemory/DPS 类似接入）：

| OpenLLM 现有实现 | 处理方式 | 替换为 OpenBase 模块 |
|------------------|----------|---------------------|
| `middleware/audit.py`、`rate_limit.py`、`metrics.py`、`otel.py` | 移除（Git 历史保留） | modules/audit、modules/observability |
| `api/auth.py` + `services/auth_service.py` + `edgerouter/auth/`（rbac、jwt_handler） | 替换 | modules/auth（RBAC + OIDC） |
| `models/tenant*`、`services/tenant_isolation.py` | 替换（Schema 隔离） | modules/tenant（EdgeRouter 全栈） |
| `core/config.py`、`api/config.py`、`config_backup_service.py` | 替换 | modules/config（三级合并 + 回滚） |
| `mcp/rag_mcp.py` | 替换 | modules/mcp（统一封装） |
| `core/otel.py`、`services/trace_service.py`、`monitoring.py` | 替换 | modules/observability（业务指标 + Grafana） |
| `edgerouter/`（编排）、`gateway/`（模型路由）、`services/`（semantic_router、writeback_queue、fallback_chain 等） | **保留（OpenLLM 特色）** | — |

**接入示例**：

```python
# pyproject.toml
dependencies = ["openbase>=1.0", ...]

# app/main.py —— 启用 OpenBase 模块
from openbase import init_app, settings
from openbase.modules import auth, tenant, audit, observability, config, mcp

settings.enable_module("rbac")
settings.enable_module("tenant")
settings.enable_module("audit")
settings.enable_module("observability")
settings.enable_module("config")
settings.enable_module("mcp")

app = init_app(settings)
app.include_router(auth.router)
app.include_router(tenant.router)
# ... 保留 OpenLLM 特色路由（编排 / 模型路由 / 回写 / 双通道）
```

**改造后分层架构**：

```
┌──────────────────────────────────────────────────┐
│ 各系统特色层（保留）                                │
│ OpenLLM: 编排/模型路由/三路回写/双通道输出          │
│ OpenRAG: 检索管线/知识库管理                        │
│ OpenMemory: 记忆存取/分层记忆                      │
│ DPS: 画像维度模型/画像提炼策略                      │
├──────────────────────────────────────────────────┤
│ OpenBase 底座层（替换，本项目建设）                 │
│ 鉴权 / 多租户 / 审计 / 限流 / 可观测 / 配置 / MCP   │
├──────────────────────────────────────────────────┤
│ FastAPI + PostgreSQL + Redis + Qdrant             │
└──────────────────────────────────────────────────┘
```

## 12. 组件化集成设计

> 来源：OpenLLM 方案 §2.4（v1.4.5）+ 复用框架研究报告 §4/§5

OpenBase 内部采用成熟开源组件替换自研适配器实现，对外契约零变化。组件按"进程内库 / 独立服务"区分。

| 组件 | 优先级 | 形态 | 集成位置 | 说明 |
|------|--------|------|----------|------|
| **FastMCP** | P0 | 进程内库 | modules/mcp/ | MCP Server 封装，decorator 风格 API，遵循 2026-07 规范 |
| **Langfuse** | P0 | 独立服务（可关 UI） | modules/observability/ | OTLP 直接对接；链路追踪 + 会话级评测；Deploy 环境可关闭 UI 只跑核心追踪 |
| **OpenTelemetry** | P0 | 进程内库 | modules/observability/ | GenAI 语义约定，统一埋点标准 |
| Qdrant | P1 | 独立服务 | 向量存储（OpenRAG/OpenMemory 共用） | 三系统向量库统一；多租户 collection 隔离 |
| GPTCache | P1 | 进程内库 | 语义缓存 | 缓存键策略、命中率指标、一致性控制 |
| Mem0 | P2 可选 | 进程内库 | OpenMemory 适配器 | 按业务复杂度按需引入，不阻塞主线 |
| LlamaIndex | P2 可选 | 进程内库 | OpenRAG 适配器 | 按业务复杂度按需引入 |

**集成原则**：
- 组件全部封装于模块内部，OpenBase 对外接口保持不变
- 组件升级或替换不影响上层调用方
- 遵循"直接采用 / 封装采用 / 自研保留"三级复用策略

| 复用级别 | 定义 | 对应组件 |
|----------|------|----------|
| 直接采用 | 成熟度高、直接引入即用 | FastMCP、Langfuse、OTel、Qdrant、GPTCache |
| 封装采用 | 框架之上加一层薄适配 | Mem0（包一层记忆接口）、LlamaIndex（包一层检索接口） |
| 自研保留 | 差异化核心，框架无法替代 | 统一鉴权审计、配置中心管理逻辑 |

## 13. 双接口体系

> 来源：OpenLLM 方案 §3.2（v1.4.2）

OpenBase 后端接口分为两套，共享统一底座但职责、调用者、认证与性能特征完全不同。

| 维度 | AI 服务接口（Agent 对接） | 管理接口（前端对接） |
|------|--------------------------|---------------------|
| 用途 | 对话、推理、检索、回写 | 配置、监控、CRUD、服务发现 |
| 调用者 | Agent / DHAP（机器） | 人类用户（经 Vue 前端） |
| 典型端点 | MCP 工具、AI 编排接口 | 登录/鉴权、用户/租户/权限管理、知识库/画像/模型管理等 CRUD |
| 协议 | REST + SSE + MCP | REST |
| 认证 | 服务级 API Key（机器对机器） | 用户级 JWT（RBAC） |
| 性能特征 | 高吞吐、流式、低延迟 | 交互式、低频、管理型 |
| 归属 | 四系统运行时能力 | 统一网关管理面 |

**共享基础设施**：
- **统一网关**：两套接口都经统一网关（鉴权、限流、审计、服务发现、多租户）
- **公共底座 6 模块**：API 服务框架、鉴权 RBAC、多租户、MCP 封装、可观测、配置中心
- **统一鉴权体系**：Agent 用服务级 Key、用户用 JWT，同一签发体系（token 类型/scope 隔离）
- **可观测统一**：两套接口的调用都进 Langfuse + OTel，同一链路追踪

**设计原则**：两套接口不可合并——调用者身份、认证模型、性能要求、生命周期均不同。前端管理页面可间接调用 AI 服务接口（经管理接口代理转发），但前端不直连 AI 接口，保持权限边界清晰。

## 14. 前端模块归属与必启约束

> 来源：OpenLLM 方案 §15.7（v1.4.5）
> **需求设计索引**：统一前端的详细需求设计（FR-UF-001~018 功能需求、非功能/接口/数据/权限/UI-UX 需求、追溯矩阵）见《OpenBase-统一前端需求设计说明-v0.1.0.md》（doc/requirements/）。

### 14.1 前端定位：一套统一前端 + 动态业务模块

OpenLLM/OpenRAG/OpenMemory/DPS 四系统共用**一套统一前端**，不存在五套独立前端。前端整体基于 vue-vben-admin 构建，OpenBase 公共模块是必启基础模块，各业务系统的特色功能是统一前端中的**动态业务模块**（按服务发现动态显隐）。

```
┌─────────────────────────────────────────────────┐
│            统一前端（vue-vben-admin）             │
├───────────┬─────────────────────────────────────┤
│           │  工作台首页（聚合概览）               │
│  公共模块  │  系统管理（用户/角色/权限/租户…）   │ ← OpenBase 必启
│ (OpenBase) │  数据字典 / 定时任务 / 文件 / 通知   │
│           │  登录 / 鉴权                         │
├───────────┼─────────────────────────────────────┤
│           │  OpenLLM 模块（对话监控/模型/路由）  │
│ 动态模块  │  OpenRAG 模块（文档/知识库/检索）    │ ← 服务发现驱动
│ (业务域)  │  OpenMemory 模块（记忆/会话管理）    │   动态显隐
│           │  DPS 模块（画像/标签维护）           │
└───────────┴─────────────────────────────────────┘
```

### 14.2 前端实现策略：择优抽取 + 公共底座重设计

统一前端不从零新建，采用**"择优抽取 + 重设计"**策略：

| 策略 | 说明 | 适用范围 |
|------|------|---------|
| **择优抽取** | 从四系统现有前端中逐模块挑选最完整、最成熟的实现，作为统一前端对应模块的基础 | 公共模块（登录/鉴权、用户/角色/权限、租户管理等）、公共组件库、请求层、各业务域特色页面 |
| **公共底座重设计** | 整体布局、Design Token、风格体系、路由架构重新统一设计，不直接照搬任一系统，确保全新的设计质量 | 布局壳（侧边栏/顶栏/响应式）、Design Token、全局风格体系、路由架构 |
| **动态业务模块** | 各业务系统的特色功能是统一前端中的动态模块，前端代码统一维护，不分拆到各系统；按后端服务发现动态显隐 | OpenLLM 对话监控/模型管理、OpenRAG 知识库管理/检索测试、OpenMemory 记忆管理、DPS 画像管理等 |

**抽取优先级**：登录/鉴权页 → 用户/角色/权限 → 租户管理 → 公共组件 → 请求层 → 布局壳 → Design Token → 各业务域特色页面

### 14.3 模块归属划分

| 分类 | 模块 | 后端 API 提供方 | 前端来源 | 显隐方式 |
|------|------|----------------|---------|---------|
| **公共模块（OpenBase 必启）** | 登录、用户/角色/权限、租户、数据字典、定时任务、文件、通知 | OpenBase 服务 | 四系统择优抽取 + 统一设计 | 常显 |
| **动态模块 - OpenLLM 域** | 对话监控、模型管理、路由配置 | OpenLLM 服务 | 从 OpenLLM 前端择优抽取后纳入统一前端 | 服务发现驱动 |
| **动态模块 - OpenRAG 域** | 文档管理、知识库配置、检索测试 | OpenRAG 服务 | 从 OpenRAG 前端择优抽取后纳入统一前端 | 服务发现驱动 |
| **动态模块 - OpenMemory 域** | 记忆管理、会话管理 | OpenMemory 服务 | 从 OpenMemory 前端择优抽取后纳入统一前端 | 服务发现驱动 |
| **动态模块 - DPS 域** | 画像管理、标签维护 | DPS 服务 | 从 DPS 前端择优抽取后纳入统一前端 | 服务发现驱动 |

### 14.4 布局响应调整

- **菜单分组**："系统管理"分组（OpenBase 公共模块，常显）+ 各业务域分组（动态，服务发现驱动）
- **工作台首页**：聚合工作台（各在线业务模块状态概览卡片，未启动的模块显示"未启动"）
- **公共模块常显**：OpenBase 公共模块菜单不随服务发现隐藏；各业务域模块随服务状态动态显示
- **主题 Token**：基于四系统现有主题重新设计全站统一 Design Token，所有模块统一使用
- **多端适配**：沿用 vue-vben-admin 响应式断点；移动端统一抽屉菜单
- **公共组件**：从四系统中挑选成熟度最高的表格/表单/弹窗/图表组件，统一封装为公共组件库，所有模块直接引用

### 14.5 共用 / 独立两种使用模式

| 模式 | 场景 | 前端包含内容 |
|------|------|-------------|
| **共用模式（默认）** | 四系统整体部署 | 统一前端 = 公共模块（OpenBase） + 全部业务域动态模块（OpenLLM/OpenRAG/OpenMemory/DPS） |
| **独立模式** | 单系统单独部署 | 统一前端 = 公共模块（OpenBase） + 对应业务域动态模块（如仅 OpenLLM 模块） |

> 双模式通过构建配置控制，前端代码库是同一套，仅按需加载对应业务域模块。

### 14.6 OpenBase 必启约束

登录与基础权限依赖 OpenBase 服务的 auth API，因此 **OpenBase 视为必启服务**；其余业务服务未启动仅隐藏对应动态模块，不影响登录和公共模块使用。部署编排中 OpenBase 需先行启动并纳入健康检查。

> **v1.0.0 范围说明**：前端模块归属与必启约束为架构设计输入，统一前端实际开发在 v1.2.0 进行。v1.0.0 仅产出后端底座，前端规划先行明确以指导后端 API 设计（登录/鉴权、RBAC、租户等管理接口需与 OpenBase 模块 API 对齐）。

## 15. 范围变更记录

| 变更 ID | 日期 | 变更类型 | 描述 | 影响 |
|---------|------|----------|------|------|
| VC-001 | 2026-08-25 | 合并/延期/移出 | 版本规划整体调整：v0.1.0（抽取验证）并入本版本，范围扩大为"首个可用底座"（补齐模块 + storage/notify + CLI/CRUD/脚手架 + PyPI 发布）；四系统回灌移出至 v1.1.0；统一前端移出至 v1.2.0；生态类移出至 v1.3+ | 本版本范围为后端底座完整交付，详见版本范围变更总记录 |

## 16. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v0.1.0 | 2026-08-24 | PM-OpenBase-Dev | 初始创建：v0.1.0 抽取验证版本规划 |
| v0.2.0 | 2026-08-25 | PM-OpenBase-Dev | 细化：补充包目录结构设计（含文件级映射）、模块依赖关系图、三系统成熟度矩阵、抽取来源映射表（含改动量）、非功能性能指标（路由<1ms/中间件<5ms）、新增风险 R-007 |
| v0.3.0 | 2026-08-25 | PM-OpenBase-Dev | 从 OpenLLM 方案 v1.4.5 和复用框架研究报告抽取 OpenBase 相关内容：新增 §10 抽取策略与原则（三不原则/单一事实源/成熟度审计方法）、§11 OpenLLM 模块替换清单（含文件级路径/接入示例/分层架构）、§12 组件化集成设计（P0/P1/P2 分级/三级复用策略）、§13 双接口体系（AI服务接口/管理接口对比/共享基础设施）、§14 前端页面归属与必启约束（页面归属/布局调整/共用独立双模式/必启约束） |
| v0.4.0 | 2026-08-25 | PM-OpenBase-Dev | 命名澄清：演进阶段 P2/P3 改为 S2/S3（Stage），避免与需求优先级 P0/P1/P2 混淆；"P2 阶段"统一改为"S2 阶段"，"P3 阶段"统一改为"S3 阶段" |
| v0.5.0 | 2026-08-25 | PM-OpenBase-Dev | 前端策略调整：openbase-ui 从"完全新建"改为"择优抽取+公共底座重设计"，新增 §14.1 前端实现策略章节，明确四系统择优抽取范围、公共底座重设计范围、特色功能保留原则和抽取优先级；页面归属表补充"前端来源"列 |
| v0.6.0 | 2026-08-25 | PM-OpenBase-Dev | 前端架构澄清：四系统共用一套统一前端，不存在五套独立前端；各业务系统特色功能是统一前端中的动态业务模块（服务发现驱动显隐），而非各系统独立维护；新增 §14.1 前端定位章节含架构图；页面归属表改为模块归属表，新增"显隐方式"列；章节从"页面归属"改为"模块归属" |
| v0.7.0 | 2026-08-25 | PM-OpenBase-Dev | 需求设计索引：§14 补充统一前端需求设计说明引用（《OpenBase-统一前端需求设计说明-v0.1.0.md》，FR-UF-001~018），与候选需求池 F-001~F-015 建立追溯 |
| v1.0.0 | 2026-08-25 | PM-OpenBase-Dev | 版本规划整体调整（VC-001）：文档由 v0.1.0 升级为 v1.0.0——范围扩大为"首个可用底座"（并入补齐模块 org/dict/scheduler/storage/notify、CLI/CRUD/脚手架、PyPI 发布）；成功指标更新（覆盖率 ≥85%、11/11 模块、CLI 3/3、PyPI 发布）；发布策略由"内部验证版"改为"PyPI v1.0 正式发布"；不包含范围更新（回灌→v1.1.0、前端→v1.2.0、生态→v1.3+）；§14 范围说明同步 |
