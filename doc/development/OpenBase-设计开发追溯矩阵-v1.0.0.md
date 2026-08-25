# OpenBase 设计开发追溯矩阵 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 关联设计 | 系统架构设计文档/API 接口设计文档/数据库设计文档（v1.0.0） |

---

## 1. 追溯链说明

追溯链：**DT-ID（设计项）→ TD-ID（开发项）→ 涉及文件 → 完成状态**。编码实现以本矩阵为逐项指引，每项对应设计评审记录 §3 的 DT-ID。

## 2. TD-ID 追溯矩阵

| TD-ID | 设计项（DT-ID） | 开发任务 | 涉及文件 | 状态 |
|-------|----------------|---------|---------|------|
| TD-01-01 | DT-001 框架内核 core | 包结构 + init_app 装配 | openbase/__init__.py | ✅ 完成 |
| TD-01-02 | DT-001 框架内核 core | settings 配置驱动 | openbase/settings.py | ✅ 完成 |
| TD-01-03 | DT-001 框架内核 core | base models（5 模型 + Department） | openbase/core/models/base.py | ✅ 完成 |
| TD-01-04 | DT-001 框架内核 core | DB session 管理 | openbase/core/db/session.py | ✅ 完成 |
| TD-01-05 | DT-001 框架内核 core | 通用 deps（get_current_user/tenant） | openbase/core/deps/auth.py | ✅ 完成 |
| TD-01-06 | DT-001 框架内核 core | 统一错误码与异常处理器 | openbase/core/errors/*.py | ✅ 完成 |
| TD-02-01 | DT-002 auth 模块 | JWT 签发/验证 | openbase/modules/auth/jwt.py | ✅ 完成 |
| TD-02-02 | DT-002 auth 模块 | RBAC 权限检查 | openbase/modules/auth/rbac.py | ✅ 完成 |
| TD-02-03 | DT-002 auth 模块 | 登录/刷新路由 | openbase/modules/auth/__init__.py | ✅ 完成 |
| TD-03-01 | DT-003 tenant 模块 | 租户中间件 + 上下文 | openbase/modules/tenant/__init__.py | ✅ 完成 |
| TD-04-01 | DT-004 audit 模块 | 审计中间件 + /health | openbase/modules/audit/__init__.py | ✅ 完成 |
| TD-05-01 | DT-005 observability | OTel 初始化 + Langfuse 配置 | openbase/modules/observability/__init__.py | ✅ 完成 |
| TD-06-01 | DT-006 config 模块 | 配置中心（三级合并/版本/回滚） | openbase/modules/config/__init__.py | ✅ 完成 |
| TD-07-01 | DT-007 mcp 模块 | FastMCP 封装 + 工具注册 | openbase/modules/mcp/__init__.py | ✅ 完成 |
| TD-08-01 | DT-008 org 模块 | 部门树 CRUD | openbase/modules/org/__init__.py | ✅ 完成 |
| TD-09-01 | DT-009 dict 模块 | 数据字典 CRUD | openbase/modules/dict/__init__.py | ✅ 完成 |
| TD-10-01 | DT-010 scheduler | APScheduler 封装 + 任务 CRUD | openbase/modules/scheduler/__init__.py | ✅ 完成 |
| TD-11-01 | DT-011 storage | 文件上传/下载/删除 | openbase/modules/storage/__init__.py | ✅ 完成 |
| TD-12-01 | DT-012 notify | SSE + 站内信 + 已读 | openbase/modules/notify/__init__.py | ✅ 完成 |
| TD-13-01 | DT-013 openbase-cli | create-project/module/crud | openbase/cli/main.py | ✅ 完成 |
| TD-14-01 | DT-014 BaseCRUDRouter | 通用 CRUD 路由生成 | openbase/crud/__init__.py | ✅ 完成 |
| TD-16-01 | DT-016 发布 | pyproject + README + demo_app | pyproject.toml, README.md, openbase/demo_app.py | ✅ 完成 |
| TD-25-01 | DT-025 数据模型 | 建表验证 | tests/test_models.py | ✅ 完成 |
| TD-26-01 | DT-006 config 增强 | 抽取 OpenRAG 三级配置/事件通知 | openbase/modules/config/__init__.py | ✅ 完成 |
| TD-26-02 | DT-003 tenant 增强 | 抽取 OpenMemory EdgeRouter/配额 | openbase/modules/tenant/__init__.py | ✅ 完成 |
| TD-26-03 | DT-005 observability 增强 | 抽取 OpenMemory 业务指标 | openbase/modules/observability/__init__.py | ✅ 完成 |
| TD-26-04 | DT-001 errors 增强 | 抽取 DPS 错误码注册机制 | openbase/core/errors/registry.py | ✅ 完成 |
| TD-26-05 | FR-PRO-001/002 | 四系统成熟度审计 + 来源决策 | doc/development/OpenBase-模块成熟度审计与来源决策-v1.0.0.md | ✅ 完成 |
| TD-26-06 | DT-002 auth 增强 | 抽取 OpenLLM RBACManager 配置驱动权限管理 | openbase/modules/auth/rbac.py | ✅ 完成 |
| TD-26-07 | DT-004 audit 增强 | 抽取 OpenLLM AuditMiddleware 路径排除/脱敏/IP 提取 | openbase/modules/audit/__init__.py | ✅ 完成 |
| TD-26-08 | DT-007 mcp 增强 | 抽取 OpenRAG MCPServer 协议分发/工具注册 | openbase/modules/mcp/__init__.py | ✅ 完成 |
| TD-26-09 | DT-001 数据库接入 | settings 增加 DB/Redis URL 解析 + db_schema 字段 | openbase/settings.py | ✅ 完成 |
| TD-26-10 | DT-001 数据库接入 | schema 隔离（metadata 绑定）+ 引擎访问入口 + 连接超时 | openbase/core/db/session.py | ✅ 完成 |
| TD-26-11 | DT-001 数据库接入 | 数据库初始化（ensure_schema/create_tables/种子数据） | openbase/core/db/init.py | ✅ 新增 |
| TD-26-12 | DT-002 数据库接入 | UserService 数据库优先登录（OpenLLM 用户校验模式） | openbase/modules/auth/__init__.py | ✅ 完成 |
| TD-26-13 | DT-016 数据库接入 | demo_app 启动自动初始化数据库 + seed admin + 降级回退 | openbase/demo_app.py | ✅ 完成 |
| TD-26-14 | DT-025 数据库接入 | 测试适配（schema 重置 + 登录用例更新） | tests/test_models.py, tests/test_app.py | ✅ 完成 |

## 3. Subtask CheckList（子任务状态表）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 设计文档规划的新建文件全部落地 | ✅ | 22 个开发项对应文件全部存在 |
| 实际文件名与设计命名一致 | ✅ | 模块目录/文件命名与系统架构设计一致 |
| 未完成项推迟记录 | ✅ 无 | 全部完成 |

## 4. 版本控制记录

| 项 | 约定 |
|----|------|
| 分支策略 | git-flow（project-config.json 配置） |
| Commit 模板 | `type(scope): subject` + footer 引用 RT-ID |
| 提交类型 | feat/fix/docs/style/refactor/test/chore |
| RT-ID 引用 | footer 如 `Refs: RT-001, RT-002` |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AD-OpenBase-Dev | 初始创建：22 个开发项（TD-01~TD-25）全部完成，Subtask CheckList 全通过，版本控制约定记录 |
| v1.0.1 | 2026-08-25 | AD-OpenBase-Dev | 共享基础设施数据库接入：新增 TD-26-09~TD-26-14（DB/Redis URL 解析、schema 隔离、数据库初始化、UserService 用户落库、demo_app 启动初始化、测试适配） |
