# OpenBase 本版本 Backlog - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-24 |
| 最后更新 | 2026-08-25 |
| 前身版本 | v0.1.0（已并入本版本，见版本范围变更记录 VC-001） |

---

## 1. Backlog 概览

| 优先级 | 条目数 | 说明 |
|--------|--------|------|
| P0 | 20 | 必须完成，阻断版本发布 |
| P1 | 11 | 应该完成，影响版本质量 |
| P2 | 0 | 可选，不阻断 |
| **合计** | **31** | |

## 2. 版本优先级评估记录

### 2.1 评估方法

采用 **MoSCoW + 价值/成本/风险三维评估**：
- **MoSCoW**：Must (P0) / Should (P1) / Could (P2) / Won't (不包含)
- **价值**：高/中/低 — 对"抽取验证"版本目标的贡献度
- **成本**：高/中/低 — 实现工作量（人天）
- **风险**：高/中/低 — 技术不确定性、依赖不确定性

### 2.2 P0 定义

v1.0.0 的核心目标是"首个可用底座"，因此框架内核、6 核心模块抽取、5 补齐模块、CLI/CRUD/脚手架、PyPI 发布均为 P0。三系统审计是抽取的前提，也列为 P0。

### 2.3 评估结果

详见第 3 节 Backlog 条目。

## 3. Backlog 条目

### 3.1 P0 — 必须完成

| ID | 需求ID | 条目名称 | 来源系统 | 抽取内容（文件级） | 改动量 | Phase | 价值 | 成本 | 风险 | 验收标准 |
|----|--------|----------|----------|-------------------|--------|-------|------|------|------|----------|
| BL-001 | - | 三系统成熟度审计 | OpenLLM/OpenMemory/OpenRAG | 后端 6 模块 × 3 系统 = 18 项五维度评分（功能/代码/测试/文档/生产验证） | 新建 | Phase 1 | 高 | 中 | 低 | 审计报告覆盖 18 项评估，每项有五维度评分和来源标注 |
| BL-002 | - | 模块抽取来源决策 | - | 6 核心模块逐模块来源标注 + 抽取范围 + 改动量 | 新建 | Phase 1 | 高 | 低 | 低 | 决策记录覆盖 6 模块，每模块有来源系统、抽取文件清单、改动量（复制级/中等/改写迁移） |
| BL-003 | C-001 | 框架内核 - base models | 新建（对齐三系统） | core/models/user.py, role.py, permission.py, tenant.py, audit_log.py | 新建 | Phase 2 | 高 | 中 | 低 | 模型可 import，字段与三系统对齐，SQLAlchemy 映射正确，可 create_all 建表 |
| BL-004 | C-002 | 框架内核 - DB session | 新建 | core/db/session.py, migrations/ | 新建 | Phase 2 | 高 | 中 | 低 | session 可创建/关闭，Alembic 迁移模板可用 |
| BL-005 | C-003 | 框架内核 - 通用 deps | 新建 | core/deps/database.py (get_db), auth.py (get_current_user) | 新建 | Phase 2 | 高 | 低 | 低 | deps 可在 FastAPI 路由中作为 Depends 使用 |
| BL-006 | C-004 | 框架内核 - 统一 errors | 新建 | core/errors/base.py (BaseError), codes.py (错误码定义) | 新建 | Phase 2 | 高 | 低 | 低 | 异常可被 FastAPI 捕获并返回统一 JSON 格式响应 |
| BL-007 | C-005 | 框架内核 - settings 配置驱动 | 新建 | settings.py (enable_module/disable_module/init_app) | 新建 | Phase 2 | 高 | 低 | 低 | settings.enable_module("xxx") 可执行；init_app(settings) 自动装配可用 |
| BL-008 | M-001 | API 服务框架模块抽取 | OpenLLM `middleware/audit.py`, `rate_limit.py`, `metrics.py`, `otel.py`, `health_service` | modules/audit/middleware.py (审计中间件), rate_limit.py (限流), metrics.py (指标采集), health.py (health_service) | 抽取后包化 | Phase 3.2 | 高 | 中 | 低 | 模块独立启用后中间件生效，限流和审计功能正常，中间件附加延迟 <5ms |
| BL-009 | M-002 | 鉴权 RBAC 模块抽取 | OpenLLM `api/auth.py` + `services/auth_service.py` + `edgerouter/auth/`(rbac, jwt_handler) + OpenMemory abac/oidc | modules/auth/jwt.py (JWT签发验证), rbac.py (RBAC权限矩阵), oidc.py (OIDC增强) | 中等 | Phase 4.1 | 高 | 高 | 中 | 模块独立启用后 JWT 鉴权可用，RBAC+ABAC 双层权限矩阵正确 |
| BL-010 | M-003 | 多租户隔离模块抽取 | OpenMemory `multitenancy/`(edge_router, quota, rate_limiter) + OpenLLM `models/tenant*`, `services/tenant_isolation.py` | modules/tenant/edge_router.py (EdgeRouter租户路由), quota.py (配额管理), rate_limiter.py (限流) | 复制级 | Phase 4.2 | 高 | 高 | 中 | 模块独立启用后多租户隔离生效，数据不串租户，路由延迟 <1ms |
| BL-011 | M-004 | MCP 封装模块抽取 | FastMCP + OpenRAG/OpenMemory 工具定义 + OpenLLM `mcp/rag_mcp.py` | modules/mcp/__init__.py (FastMCP实例), decorator.py (工具注册decorator), auth.py (MCP鉴权) | 改写迁移 | Phase 3.4 | 高 | 中 | 中 | 模块独立启用后工具可注册和调用，MCP 协议适配正确 |
| BL-012 | M-005+M-006 | 可观测性 + 配置中心模块抽取 | OpenLLM `core/otel.py`, `services/trace_service.py`, `monitoring.py` + OpenMemory business_metrics + OpenRAG `core/config.py`, `api/config.py`, `config_backup_service.py` | modules/observability/otel.py, langfuse.py, business_metrics.py, dashboards/ + modules/config/manager.py, hot_reload.py, watcher.py | 改写迁移+复制级 | Phase 3.1+3.3 | 高 | 中 | 中 | 可观测模块追踪/指标可用；配置中心热加载和回滚功能正常 |

### 3.2 P1 — 应该完成

| ID | 需求ID | 条目名称 | 来源 | 描述 | Phase | 价值 | 成本 | 风险 | 验收标准 |
|----|--------|----------|------|------|-------|------|------|------|----------|
| BL-013 | - | FastMCP 预研验证 | FastMCP 库 | 验证 FastMCP 协议/传输/生命周期是否满足 MCP 封装需求 | Phase 1 | 高 | 低 | 中 | 预研报告输出，明确可行或需备选方案（直接实现 MCP 协议） |
| BL-014 | - | Langfuse 集成预研 | Langfuse SDK | 验证 Langfuse OTLP 对接可行性和 SDK 集成方式 | Phase 1 | 中 | 低 | 中 | 预研报告输出，明确可行或需备选方案（仅用 OTel+Prometheus） |
| BL-015 | - | 模块弱依赖验证 | - | 逐模块独立启用测试，验证模块间无强依赖 | Phase 4.3 | 高 | 低 | 低 | 6 模块逐一独立启用（禁用其他 5 个），功能正常 6/6 通过 |
| BL-016 | - | Git 历史保留验证 | - | 确认抽取过程中 Git 历史完整保留，可追溯原系统来源 | Phase 4.3 | 中 | 低 | 低 | git log 可查每个抽取文件的原始来源系统和提交记录 |
| BL-017 | - | 框架级测试基座雏形 | 新建 | conftest.py、基础 fixture、coverage 配置（≥60% 门槛） | Phase 2 | 中 | 低 | 低 | pytest 可运行，coverage 可统计，覆盖率门槛 60% 配置 |
| BL-018 | - | FastMCP 组件集成验证 | OpenLLM 方案 §2.4（P0 组件） | 验证 FastMCP 进程内库集成：decorator 风格 API、工具注册/鉴权/协议适配，遵循 2026-07 MCP 规范（可缓存 list 结果） | Phase 1 | 高 | 中 | 中 | FastMCP 实例可创建，工具可注册和调用，MCP 协议适配正确，list 结果可缓存 |
| BL-019 | - | Langfuse OTLP 对接验证 | OpenLLM 方案 §2.4（P0 组件） | 验证 Langfuse 独立服务集成：OTLP 直接对接、链路追踪 + 会话级评测、Deploy 环境可关闭 UI 只跑核心追踪 | Phase 1 | 高 | 中 | 中 | Langfuse OTLP 端点可对接，追踪数据可上报，UI 可独立关闭/开启 |
| BL-020 | - | OpenTelemetry GenAI 语义约定集成 | OpenLLM 方案 §2.4 + 复用报告 §3.7 | 验证 OTel GenAI 语义约定（gen_ai.operation.name 等 span 规范）统一埋点标准，避免厂商锁定 | Phase 1 | 中 | 低 | 低 | OTel SDK 可集成，GenAI span 规范可用，Langfuse/Phoenix 均可消费 |
| BL-021 | - | 双接口体系设计验证 | OpenLLM 方案 §3.2 | 验证 AI 服务接口（服务级 API Key）与管理接口（用户级 JWT/RBAC）双套接口的认证隔离和共享基础设施设计 | Phase 4.3 | 高 | 中 | 中 | 两套接口认证模型独立，共享网关/底座/鉴权体系/可观测，前端不直连 AI 接口 |

### 3.3 P0 — 补齐模块与工具链（v1.0.0 新增，VC-001）

| ID | 需求ID | 条目名称 | 来源 | 描述 | Phase | 价值 | 成本 | 风险 | 验收标准 |
|----|--------|----------|------|------|-------|------|------|------|----------|
| BL-022 | S-001 | 组织架构 org 模块 | OpenLLM organizations 雏形完善 | 部门树、用户-部门关联、按部门授权 | Phase 5.1 | 中 | 中 | 低 | 模块独立启用后部门树 CRUD 可用，用户-部门关联正确，按部门授权生效 |
| BL-023 | S-002 | 数据字典 dict 模块 | 新建（对标 Nuct） | 枚举/选项配置、前端字典组件联动 | Phase 5.2 | 中 | 低 | 低 | 字典 CRUD 可用，选项配置保存后联动刷新 |
| BL-024 | S-003 | 定时任务 scheduler 模块 | 新建（对标 Nuct） | APScheduler 封装、任务 CRUD、执行日志 | Phase 5.3 | 中 | 中 | 低 | 任务可创建/启停，执行日志可查询，APScheduler 集成正常 |
| BL-025 | S-004 | 统一文件存储 storage 模块 | 新建 | 本地/MinIO/S3 适配、上传下载预览 | Phase 5.4 | 中 | 中 | 低 | 上传/下载/预览全流程可用，三种后端适配可切换 |
| BL-026 | S-005 | 通知中心 notify 模块 | 复用 OpenLLM sse_adapter | SSE 推送、站内信、已读管理 | Phase 5.5 | 中 | 中 | 低 | SSE 实时推送可用，站内信/已读状态持久化 |
| BL-027 | T-001 | openbase-cli 工具 | 新建 | create-project / create-module / create-crud | Phase 5.6 | 高 | 中 | 中 | 三命令执行通过，生成工程可运行 |
| BL-028 | T-002 | BaseCRUDRouter | 新建（参考 fastapi-crudrouter） | FastAPI 通用 CRUD 路由自动生成 | Phase 5.7 | 高 | 中 | 中 | 生成路由与手写等价（延迟差 <5%），支持分页/搜索/排序 |
| BL-029 | T-005 | 模板脚手架 | 新建 | 标准工程结构 + 初始化脚本 | Phase 5.8 | 高 | 中 | 低 | create-project 生成标准工程结构，初始化脚本可运行 |
| BL-030 | - | 11 模块集成联调 | - | 全部模块整体装配 + CLI 生成项目运行验证 | Phase 5.9 | 高 | 中 | 低 | 11 模块整体启用互不冲突，CLI 生成项目可运行 |
| BL-031 | - | PyPI v1.0 发布 + 文档 | v1.0 | pip install openbase + Quickstart + 模块使用指南 | Phase 6 | 高 | 低 | 低 | 全新环境 pip install openbase 成功，按文档三步启用模块可用 |

## 4. Backlog 与需求池映射

| Backlog ID | 候选需求 ID | 说明 |
|------------|------------|------|
| BL-003 | C-001 | base models |
| BL-004 | C-002 | DB session |
| BL-005 | C-003 | 通用 deps |
| BL-006 | C-004 | 统一 errors |
| BL-007 | C-005 | settings 配置驱动 |
| BL-008 | M-001 | API 服务框架 |
| BL-009 | M-002 | 鉴权 RBAC |
| BL-010 | M-003 | 多租户隔离 |
| BL-011 | M-004 | MCP 封装 |
| BL-012 | M-005+M-006 | 可观测性 + 配置中心 |
| BL-001~BL-002 | - | 新增：审计/定源 |
| BL-013~BL-014 | - | 新增：预研验证 |
| BL-015~BL-016 | - | 新增：弱依赖/Git 历史 |
| BL-017 | - | 新增：测试基座 |
| BL-018~BL-020 | - | 新增：组件化集成验证（FastMCP/Langfuse/OTel，来源 OpenLLM 方案 §2.4） |
| BL-021 | - | 新增：双接口体系设计验证（来源 OpenLLM 方案 §3.2） |
| BL-022 | S-001 | 组织架构 org（v1.0.0 新增） |
| BL-023 | S-002 | 数据字典 dict（v1.0.0 新增） |
| BL-024 | S-003 | 定时任务 scheduler（v1.0.0 新增） |
| BL-025 | S-004 | 统一文件存储 storage（v1.0.0 新增，从 v1.1.0 提前） |
| BL-026 | S-005 | 通知中心 notify（v1.0.0 新增，从 v1.1.0 提前） |
| BL-027 | T-001 | openbase-cli（v1.0.0 新增） |
| BL-028 | T-002 | BaseCRUDRouter（v1.0.0 新增） |
| BL-029 | T-005 | 模板脚手架（v1.0.0 新增） |
| BL-030 | - | 11 模块集成联调（v1.0.0 新增） |
| BL-031 | - | PyPI v1.0 发布 + 文档（v1.0.0 新增） |

**P0 覆盖率检查**：候选需求池中 v1.0.0 的 P0 需求（C-001~C-005, M-001~M-006, S-001~S-003, T-001~T-002）共 13 条，全部有对应 Backlog 条目 ✅（BL-003~012, BL-022~024, BL-027~028）

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v0.1.0 | 2026-08-24 | RA-OpenBase-Dev | 初始创建：17 条 Backlog（12×P0 + 5×P1），P0 覆盖率 100% |
| v0.2.0 | 2026-08-25 | RA-OpenBase-Dev | 细化：每条 Backlog 补充来源系统、抽取文件级内容、改动量（复制级/中等/改写迁移）、对应 Phase 编号、量化验收标准（路由 <1ms / 中间件 <5ms） |
| v0.3.0 | 2026-08-25 | RA-OpenBase-Dev | 从 OpenLLM 方案 v1.4.5 抽取：更新 P0 条目文件路径（对齐 §1.10.1 模块替换清单，补充 api/auth.py、services/auth_service.py、mcp/rag_mcp.py 等）；新增 4 条 P1 条目（BL-018~BL-021：FastMCP/Langfuse/OTel 组件集成验证 + 双接口体系设计验证） |
| v0.4.0 | 2026-08-25 | RA-OpenBase-Dev | 命名澄清：Phase 列从 P1/P2/P3.x 简写改为 Phase 1/Phase 2/Phase 3.x 全称，避免与需求优先级 P0/P1/P2 混淆 |
| v1.0.0 | 2026-08-25 | RA-OpenBase-Dev | 版本规划整体调整（VC-001）：文档由 v0.1.0 升级为 v1.0.0——新增 BL-022~BL-031（补齐模块 org/dict/scheduler/storage/notify 5 条 + CLI/CRUD/脚手架 3 条 + 集成联调 1 条 + PyPI 发布 1 条）；BL-009/010 移至 Phase 4.1/4.2，BL-015/016/021 移至 Phase 4.3；P0 覆盖率检查更新为 v1.0.0（13 条 P0 需求全部有 Backlog）；总计 31 条（20×P0 + 11×P1） |
