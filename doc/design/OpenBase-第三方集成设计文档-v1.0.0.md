# OpenBase 第三方集成设计文档 - v1.0.0

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
| 关联需求 | FR-MOD-004/005、FR-PRO-003/004、CI-001~CI-003 |
| 关联轨道 | 第三方集成 🔗（激活） |

---

## 1. 外部依赖盘点

| 依赖 | 类型 | 用途 | 集成形态 | 版本基线 | License |
|------|------|------|---------|---------|---------|
| FastMCP | 进程内库 | MCP Server 封装 | modules/mcp 直接采用 | 当前稳定版 | MIT |
| Langfuse | 独立服务 | LLM 追踪/评测 | modules/observability OTLP 对接 | 自托管稳定版 | MIT |
| OpenTelemetry Python | 进程内库 | 追踪/指标 | modules/observability 直接采用 | 当前稳定版 | Apache 2.0 |
| APScheduler | 进程内库 | 任务调度 | modules/scheduler 直接采用 | 当前稳定版 | MIT |
| SQLAlchemy 2.x | 进程内库 | ORM | core/db | 当前稳定版 | MIT |
| Alembic | 进程内库 | 迁移 | core/db | 当前稳定版 | MIT |
| asyncpg | 进程内库 | PG 驱动 | core/db | 当前稳定版 | Apache 2.0 |
| redis-py | 进程内库 | Redis 客户端 | 缓存/SSE | 当前稳定版 | MIT |
| passlib/bcrypt | 进程内库 | 密码哈希 | modules/auth | 当前稳定版 | BSD |
| PyJWT | 进程内库 | JWT 签发 | modules/auth | 当前稳定版 | MIT |

## 2. 集成设计（按模块）

### 2.1 modules/mcp + FastMCP

| 项 | 设计 |
|----|------|
| 封装方式 | 直接采用：FastMCP 实例统一封装于 mcp 模块 |
| 工具注册 | decorator 声明（@mcp.tool()），工具定义从 OpenRAG/OpenMemory 迁移为 decorator 写法 |
| 协议 | 遵循 2026-07 MCP 规范（list 结果可缓存） |
| 鉴权 | 服务级 API Key 校验（auth 模块启用时） |
| 降级 | auth 禁用时 mcp 仍可运行（无鉴权模式，FR-CORE-005 弱依赖） |
| 预研 | Phase 1 FastMCP 预研（BL-013/018）；未通过回退自研协议 |

### 2.2 modules/observability + Langfuse + OTel

| 项 | 设计 |
|----|------|
| 追踪 | OTel Python SDK（OTLP exporter），GenAI 语义约定（gen_ai.operation.name 等） |
| 评测 | Langfuse 独立服务，OTLP 端点对接；会话级评测 |
| 指标 | Prometheus 指标导出（business_metrics 从 OpenMemory 迁移内容） |
| 仪表盘 | Grafana dashboards JSON（OpenMemory 迁移） |
| 降级 | Langfuse 不可用时仅 OTel+Prometheus（RQ-002 备选） |
| 预研 | Phase 1 Langfuse 预研（BL-014/019） |

### 2.3 modules/scheduler + APScheduler

| 项 | 设计 |
|----|------|
| 封装 | APScheduler BackgroundScheduler 封装于 scheduler 模块 |
| 任务 | cron 表达式 + func_path 注册 + 执行日志 |
| 分布式锁 | Redis SETNX 防止多副本重复执行 |

## 3. 版本兼容矩阵

| 组件 | Python 3.11 | 说明 |
|------|:-----------:|------|
| FastAPI | ✅ | 当前稳定版 |
| SQLAlchemy 2.x | ✅ | async 支持 |
| FastMCP | ✅ | 2026-07 规范 |
| OTel SDK | ✅ | GenAI 语义约定 |
| APScheduler | ✅ | BackgroundScheduler |
| redis-py | ✅ | asyncio 支持 |
| asyncpg | ✅ | 异步 PG 驱动 |

## 4. License 合规检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| MIT 类 | ✅ | FastMCP/Langfuse/APScheduler/SQLAlchemy/Alembic/redis-py/PyJWT |
| Apache 2.0 | ✅ | OTel/asyncpg |
| BSD | ✅ | passlib |
| AGPL 传染性 | ✅ 未引入 | 避免 LLM Gateway 等 AGPL 组件（复用报告 §6 风险缓解） |
| 商业闭源 | ✅ 未引入 | 全部自托管可部署（数据主权） |

## 5. 依赖升级策略

| 策略 | 说明 |
|------|------|
| 版本锁定 | pyproject 锁定主版本，修订版本通过 CI 自动更新 |
| 依赖审计 | CI 集成 pip-audit，高危漏洞阻断发布（SR-009） |
| 升级窗口 | 组件主版本升级需独立评审（适配层隔离，对外契约不变） |
| 适配层 | 组件均封装于模块内部，升级不影响上层调用方 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：外部依赖盘点（11 项）、按模块集成设计（mcp/observability/scheduler）、版本兼容矩阵、License 合规检查、依赖升级策略 |
