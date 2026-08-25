# OpenBase Phase 迭代计划 - v1.0.0

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

## 1. Phase 概览

v1.0.0 分为 6 个 Phase，顺序推进，对应方案文档五步流程的 S0 审计 + S1 抽取 + S2 补齐 + S4 发布（S3 回灌移至 v1.1.0）：

```
Phase 1: 审计定源     Phase 2: 内核搭建       Phase 3: 核心模块抽取(一批)
  S0 审计五维度评分     core/ 5 组件实现         audit/observability/config/mcp
  (2 天)              (5 天)                  (2 周)
  2026-08-25~08-26    2026-08-27~08-31       2026-09-01~09-12
      │                    │                       │
      ▼                    ▼                       ▼
   M1: 审计完成         M2: 内核可用            M3: 模块一批完成

Phase 4: 核心模块抽取(二批)  Phase 5: 补齐+工具链     Phase 6: 发布
  auth/tenant + 弱依赖验证    补齐 5 模块+CLI/CRUD/脚手架  PyPI v1.0+文档
  (1 周)                    (2-3 周)                (1 周)
  2026-09-13~09-19         2026-09-22~10-09      2026-10-05~10-12
      │                        │                       │
      ▼                        ▼                       ▼
   M4: 模块抽取完成          M5: 底座完整            M6: v1.0 发布
```

## 2. Phase 明细

### Phase 1: 审计定源（S0 审计）

| 维度 | 内容 |
|------|------|
| **目标** | 完成三系统 6 核心模块成熟度审计，确定抽取来源 |
| **时间窗口** | 2026-08-25 ~ 2026-08-26（2 天） |
| **Backlog 条目** | BL-001, BL-002, BL-013, BL-014 |
| **负责人** | AA-OpenBase-Dev（审计）, AD-OpenBase-Dev（预研） |

**输入**：
- 三系统代码库访问权限（D-001~D-003）
- 方案文档 §4.2 抽查评估矩阵（初步评分）
- 方案文档 §4.3 抽取清单（抽取范围参考）

**活动**：

| 步骤 | 活动 | 产出 | 负责人 |
|------|------|------|--------|
| 1.1 | 对 OpenLLM 后端 6 模块做五维度评分（功能/代码/测试/文档/生产验证） | OpenLLM 审计评分表 | AA |
| 1.2 | 对 OpenMemory 后端 6 模块做五维度评分 | OpenMemory 审计评分表 | AA |
| 1.3 | 对 OpenRAG 后端 6 模块做五维度评分 | OpenRAG 审计评分表 | AA |
| 1.4 | 逐模块选定最佳来源，标注抽取范围和改动量 | 模块抽取来源决策记录 | AA |
| 1.5 | FastMCP 预研：验证协议/传输/生命周期是否满足 MCP 封装需求 | FastMCP 预研报告 | AD |
| 1.6 | Langfuse 预研：验证 OTLP 对接可行性和 SDK 集成方式 | Langfuse 预研报告 | AD |

**输出**：
- 三系统成熟度审计报告（6 模块 × 3 系统 = 18 项，五维度评分）
- 模块抽取来源决策记录（6 模块来源标注 + 抽取范围 + 改动量）
- FastMCP 预研报告（可行/需备选方案）
- Langfuse 预研报告（可行/需备选方案）

**验证点**：
- [ ] 每模块有明确的最佳来源系统
- [ ] 抽取范围和改动量已评估（复制级/中等/改写迁移）
- [ ] 来源决策与方案文档 §4.2 成熟度矩阵一致或有合理调整说明
- [ ] FastMCP 预研有明确结论（可行/需备选方案）
- [ ] Langfuse 预研有明确结论（可行/需备选方案）

**里程碑 M1**：审计报告评审通过

### Phase 2: 内核搭建（S1 抽取 - core 部分）

| 维度 | 内容 |
|------|------|
| **目标** | 建立 openbase 包骨架，完成框架内核 core 5 组件实现 |
| **时间窗口** | 2026-08-27 ~ 2026-08-31（5 天） |
| **Backlog 条目** | BL-003, BL-004, BL-005, BL-006, BL-007, BL-017 |
| **负责人** | AD-OpenBase-Dev（实现）, AA-OpenBase-Dev（设计） |

**输入**：
- Phase 1 审计报告（base models 字段对齐依据）
- 包目录结构设计（单版本规划文档 §2）

**活动**：

| 日期 | 步骤 | 活动 | 产出文件 |
|------|------|------|----------|
| 08-27 | 2.1 | 创建 openbase 包骨架目录结构 | pyproject.toml, openbase/__init__.py |
| 08-27 | 2.2 | 实现 core/models（User/Role/Permission/Tenant/AuditLog） | core/models/*.py |
| 08-28 | 2.3 | 实现 core/db（session 管理 + Alembic 迁移模板） | core/db/*.py, migrations/ |
| 08-29 | 2.4 | 实现 core/deps（get_db, get_current_user 等） | core/deps/*.py |
| 08-29 | 2.5 | 实现 core/errors（统一异常类 + 错误码体系） | core/errors/*.py |
| 08-30 | 2.6 | 实现 settings.py（enable_module/disable_module 配置驱动） | settings.py |
| 08-30 | 2.7 | 实现 core/__init__.py init_app(settings) 自动装配入口 | core/__init__.py |
| 08-31 | 2.8 | 建立测试基座（conftest.py + fixture + coverage 配置） | conftest.py, tests/ |

**输出**：
- openbase 包目录结构（core/models, core/db, core/deps, core/errors, settings.py）
- base models 定义（5 个模型，字段与三系统对齐）
- DB session 管理与 Alembic 迁移模板
- 通用依赖注入（get_db, get_current_user 等）
- 统一异常处理与错误码体系
- settings.py 配置驱动开关（enable_module/disable_module）
- init_app(settings) 自动装配入口
- conftest.py 与基础 fixture

**验证点**：
- [ ] `from openbase.core import models, db, deps, errors` 可正常 import
- [ ] `from openbase import init_app, settings` 可正常 import
- [ ] `settings.enable_module("test_module")` 可执行
- [ ] `settings.disable_module("test_module")` 可执行
- [ ] base models SQLAlchemy 映射正确（可 create_all 建表）
- [ ] 统一异常可被 FastAPI 捕获并返回统一格式响应
- [ ] get_db() 依赖注入可在 FastAPI 路由中使用
- [ ] pytest 可运行基础测试
- [ ] coverage 可统计

**里程碑 M2**：内核可用性验证通过

### Phase 3: 核心模块抽取 - 第一批（S1 抽取）

| 维度 | 内容 |
|------|------|
| **目标** | 完成 audit / observability / config / mcp 四模块抽取（低风险先行） |
| **时间窗口** | 2026-09-01 ~ 2026-09-12（2 周） |
| **Backlog 条目** | BL-008, BL-011, BL-012, BL-018, BL-019, BL-020 |
| **负责人** | AD-OpenBase-Dev |

**抽取顺序**（低风险→高风险，对应灰度策略）：

| 子阶段 | 模块 | 来源 | 抽取内容 | 改动量 | 周期 | Backlog |
|--------|------|------|----------|--------|------|---------|
| 3.1 | modules/config | OpenRAG config_center/ | manager.py, hot_reload.py, watcher.py | 复制级 | 2 天 (09-01~09-02) | BL-012 |
| 3.2 | modules/audit | OpenLLM middleware/ | audit中间件, rate_limit, metrics, otel, health_service | 抽取后包化 | 3 天 (09-03~09-05) | BL-008 |
| 3.3 | modules/observability | OTel/Langfuse + OpenMemory | otel.py, langfuse.py, business_metrics.py, dashboards/ | 改写迁移 | 4 天 (09-06~09-09) | BL-012, BL-019, BL-020 |
| 3.4 | modules/mcp | FastMCP + OpenRAG/OpenMemory | FastMCP实例, decorator.py, auth.py | 改写迁移 | 3 天 (09-10~09-12) | BL-011, BL-018 |

**每个子阶段的标准流程**（对应方案文档 §4.4 五步流程）：

| 步骤 | 活动 | 输入 | 输出 |
|------|------|------|------|
| ① 审计 | 确认来源系统模块的成熟度评分 | Phase 1 审计报告 | 模块评分确认 |
| ② 定源 | 确认抽取范围和具体文件列表 | Phase 1 来源决策 | 文件级抽取清单 |
| ③ 汇聚 | 抽取代码到 openbase 包，补测试与文档 | 来源系统代码 | openbase 模块代码 + 测试 |
| ④ 验证 | 单模块独立启用验证 | openbase 模块 | 启用验证结果 |
| ⑤ 弱依赖 | 确认模块间无强依赖 | 全部已抽取模块 | 弱依赖验证报告 |

**输出**：
- 4 核心模块代码（modules/audit, modules/observability, modules/config, modules/mcp）
- 每模块独立单元测试
- FastMCP / Langfuse / OTel GenAI 组件集成验证

**验证点**：
- [ ] 每模块 `settings.enable_module()` 后功能正常
- [ ] 中间件附加延迟 < 5ms（modules/audit 基准测试）
- [ ] FastMCP 实例可创建、工具可注册和调用（BL-018）
- [ ] Langfuse OTLP 端点可对接、追踪数据可上报（BL-019）
- [ ] OTel GenAI span 规范可用（BL-020）
- [ ] 配置中心热加载和回滚功能正常（BL-012）

**里程碑 M3**：核心模块第一批抽取完成

### Phase 4: 核心模块抽取 - 第二批（S1 抽取）

| 维度 | 内容 |
|------|------|
| **目标** | 完成 auth / tenant 两模块抽取（高风险后行）+ 全量弱依赖验证 |
| **时间窗口** | 2026-09-13 ~ 2026-09-19（1 周） |
| **Backlog 条目** | BL-009, BL-010, BL-015, BL-016, BL-021 |
| **负责人** | AD-OpenBase-Dev |

**活动**：

| 子阶段 | 模块 | 来源 | 抽取内容 | 改动量 | 周期 | Backlog |
|--------|------|------|----------|--------|------|---------|
| 4.1 | modules/auth | OpenLLM + OpenMemory | jwt.py, rbac.py, oidc.py（ABAC/OIDC 增强） | 中等 | 4 天 (09-13~09-16) | BL-009 |
| 4.2 | modules/tenant | OpenMemory multitenancy/ | edge_router.py, quota.py, rate_limiter.py | 复制级 | 3 天 (09-17~09-19) | BL-010 |
| 4.3 | 验证 | - | 弱依赖验证 6/6 + Git 历史验证 + 双接口体系设计验证 | - | 与 4.1/4.2 并行收尾 | BL-015, BL-016, BL-021 |

**输出**：
- 2 核心模块代码（modules/auth, modules/tenant）
- 模块弱依赖验证报告（6 模块逐一独立启用，BL-015）
- Git 历史保留验证报告（BL-016）
- 双接口体系设计验证（BL-021）

**验证点**：
- [ ] auth 模块 JWT 鉴权可用，RBAC+ABAC 双层权限矩阵正确（BL-009）
- [ ] tenant 模块多租户隔离生效，数据不串租户，路由延迟 < 1ms（BL-010）
- [ ] 模块间无强依赖（逐模块独立启用验证 6/6 通过，BL-015）
- [ ] 抽取代码 Git 历史可追溯（BL-016）
- [ ] 双接口体系认证模型独立、共享底座（BL-021）
- [ ] 单元测试覆盖率 ≥ 85%（截至本 Phase 末全量统计）
- [ ] ruff 静态检查零错误

**里程碑 M4**：6 核心模块全部抽取完成，弱依赖验证通过

### Phase 5: 补齐模块 + 工具链（S2 补齐）

| 维度 | 内容 |
|------|------|
| **目标** | 完成 5 补齐模块（org/dict/scheduler/storage/notify）+ CLI/CRUD/脚手架 |
| **时间窗口** | 2026-09-22 ~ 2026-10-09（2-3 周） |
| **Backlog 条目** | 新增 BL-022~BL-030（补齐模块 5 条 + CLI/CRUD/脚手架 3 条 + 集成联调 1 条） |
| **负责人** | AD-OpenBase-Dev |

**活动**：

| 子阶段 | 模块 | 来源 | 内容 | 周期 |
|--------|------|------|------|------|
| 5.1 | modules/org | OpenLLM organizations 雏形完善 | 部门树、用户-部门关联、按部门授权 | 3 天 |
| 5.2 | modules/dict | 新建（对标 Nuct） | 枚举/选项配置、前端字典组件联动 | 3 天 |
| 5.3 | modules/scheduler | 新建（对标 Nuct） | APScheduler 封装、任务 CRUD、执行日志 | 3 天 |
| 5.4 | modules/storage | 新建 | 本地/MinIO/S3 适配、上传下载预览 | 3 天 |
| 5.5 | modules/notify | 复用 OpenLLM sse_adapter | SSE 推送、站内信、已读管理 | 3 天 |
| 5.6 | openbase-cli | 新建 | create-project / create-module / create-crud | 4 天 |
| 5.7 | BaseCRUDRouter | 新建（参考 fastapi-crudrouter） | FastAPI 通用 CRUD 路由自动生成 | 3 天 |
| 5.8 | 模板脚手架 | 新建 | 标准工程结构 + 初始化脚本 | 3 天 |
| 5.9 | 集成联调 | - | 11 模块整体装配 + CLI 生成项目运行验证 | 3 天 |

**输出**：
- 5 补齐模块（modules/org, dict, scheduler, storage, notify）
- openbase-cli（3 命令）+ BaseCRUDRouter + 模板脚手架
- 11 模块整体装配验证报告

**验证点**：
- [ ] 5 补齐模块可独立启用（5/5）
- [ ] openbase-cli 三命令执行通过（create-project/module/crud）
- [ ] BaseCRUDRouter 生成路由与手写等价（延迟差 <5%）
- [ ] 模板脚手架 create-project 生成工程可运行
- [ ] 11 模块整体启用互不冲突
- [ ] 单元测试覆盖率 ≥ 85%（全量）
- [ ] ruff 静态检查零错误

**里程碑 M5**：底座完整可用（11 模块 + 工具链）

### Phase 6: 发布（S4 发布）

| 维度 | 内容 |
|------|------|
| **目标** | PyPI v1.0.0 发布 + 文档体系 |
| **时间窗口** | 2026-10-05 ~ 2026-10-12（1 周，与 Phase 5 收尾并行） |
| **Backlog 条目** | 新增 BL-031（PyPI 发布 + 文档） |
| **负责人** | AD-OpenBase-Dev, PM-OpenBase-Dev |

**活动**：

| 步骤 | 活动 | 产出 |
|------|------|------|
| 6.1 | PyPI 打包与发布（twine/publish CI） | openbase v1.0.0 发布到 PyPI |
| 6.2 | Quickstart 编写（安装/初始化/启模块三步） | Quickstart 文档 |
| 6.3 | 模块使用指南（11 模块 API + 配置说明） | 模块使用指南 |
| 6.4 | 安装验证（全新环境 pip install openbase + 示例工程） | 安装验证报告 |
| 6.5 | Git tag v1.0.0 + CHANGELOG | 版本标记 |

**输出**：
- PyPI v1.0.0 包（pip install openbase）
- Quickstart + 模块使用指南
- 安装验证报告
- Git tag v1.0.0

**验证点**：
- [ ] 全新环境 `pip install openbase` 成功
- [ ] 安装后可按文档三步启用模块（依赖引入/配置启用/挂载接入）
- [ ] openbase-cli create-project 生成工程可运行
- [ ] Quickstart 与模块使用指南内容与实现一致

**里程碑 M6**：v1.0.0 发布完成，底座独立可用

## 3. 里程碑总览

| 里程碑 | 日期（预计） | 交付物 | 验收人 | 验收标准 |
|--------|-------------|--------|--------|----------|
| M1: 审计完成 | 2026-08-26 | 审计报告 + 来源决策 + 预研报告 | PM + AA | 18 项五维度评分完成，6 模块来源确定 |
| M2: 内核可用 | 2026-08-31 | openbase core 包（5 组件） | AD + AA | import 验证 + 基础测试通过 |
| M3: 模块一批完成 | 2026-09-12 | 4 核心模块（audit/observability/config/mcp） | AD + AA | 组件集成验证 + 中间件延迟 <5ms |
| M4: 模块抽取完成 | 2026-09-19 | 6 核心模块 + 验证报告 | PM + AU | 弱依赖验证 6/6 + 覆盖率 ≥85% + ruff 零错误 |
| M5: 底座完整 | 2026-10-09 | 11 模块 + CLI/CRUD/脚手架 | PM + AU | 5 补齐模块 5/5 + CLI 3/3 + 整体装配验证 |
| M6: v1.0 发布 | 2026-10-12 | PyPI v1.0.0 + 文档 | PM | pip install openbase 安装验证通过 |

## 4. 资源计划

| 角色 | 人数 | 投入周期 | 职责 |
|------|------|----------|------|
| PM-OpenBase-Dev | 1 | 全程（08-25~10-12） | 协调、评审、门禁 |
| AA-OpenBase-Dev | 1 | Phase 1-2（08-25~08-31） | 架构设计、审计、内核设计 |
| AD-OpenBase-Dev | 1 | 全程（08-25~10-12） | 预研、抽取实现、测试、验证、发布 |
| AU-OpenBase-Dev | 1 | Phase 4-5 末（09-18~10-09） | 审计验证 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v0.1.0 | 2026-08-24 | PM-OpenBase-Dev | 初始创建：3 Phase 迭代计划（审计定源 → 内核搭建 → 模块抽取） |
| v0.2.0 | 2026-08-25 | PM-OpenBase-Dev | 细化：补充每 Phase 输入/活动/输出/验证点、Phase 3 子阶段抽取顺序（低风险→高风险）、每子阶段五步标准流程、具体日期和文件级产出、里程碑验收标准 |
| v0.3.0 | 2026-08-25 | PM-OpenBase-Dev | 命名澄清：演进阶段 P0/P1 改为 S0/S1（Stage），避免与需求优先级 P0/P1/P2 混淆 |
| v1.0.0 | 2026-08-25 | PM-OpenBase-Dev | 版本规划整体调整（VC-001）：Phase 计划由 v0.1.0（3 Phase）扩展为 v1.0.0（6 Phase）——Phase 3/4 拆分核心模块抽取（低风险先行/高风险后行），新增 Phase 5 补齐模块+CLI/CRUD/脚手架、Phase 6 PyPI 发布+文档；里程碑扩展至 M6；时间窗口 2026-08-25~10-12（约 6-7 周） |
