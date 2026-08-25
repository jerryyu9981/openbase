# OpenBase 设计开发追溯矩阵 - v1.2.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.2.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/development/ |

> 本矩阵为 Step 3 编码实现的逐项指引（TD-ID），映射设计项（DT-ID）到实际文件。涉及文件列以实际编码为准，未完成项必须记录推迟版本。

## 1. TD-ID 追溯矩阵

| TD-ID | 设计项（DT-ID） | 实现内容 | 涉及文件 | 状态 |
|-------|----------------|---------|---------|------|
| TD-12-01 | DT-12-01/02 前端工程与底座 | Vite 工程搭建、布局（侧边栏/顶栏/内容区）、设计 token、路由、状态、组件库、响应式 | openbase-ui/package.json、vite.config.ts、tsconfig.json、src/core/** | ✅ 完成 |
| TD-12-02 | DT-12-03 动态模块机制 | 模块注册表 manifest、懒加载路由注入、权限指令 | openbase-ui/src/core/stores/moduleRegistry.ts、src/core/router/index.ts | ✅ 完成 |
| TD-12-03 | DT-12-04 统一鉴权契约 | 登录/刷新、Axios 拦截器、ErrorResponse 映射、openapi 客户端类型 | openbase-ui/src/core/api/**、src/core/stores/auth.ts | ✅ 完成 |
| TD-12-04 | DT-12-05 OpenLLM 模块 | 模型中心/AI 应用/对话监控/平台联动页面（26 路由，核心页完整） | openbase-ui/src/modules/openllm/** | ✅ 完成 |
| TD-12-05 | DT-12-06 知识库模块 | 列表/详情/上传/检索测试台页面 | openbase-ui/src/modules/knowledge/** | ✅ 完成 |
| TD-12-06 | DT-12-07 记忆模块 | 列表/详情/搜索/会话/图谱/衰减配置页面 | openbase-ui/src/modules/memory/** | ✅ 完成 |
| TD-12-07 | DT-12-08 画像模块 | 列表/详情/标签/搜索/报表/批量页面 | openbase-ui/src/modules/portrait/** | ✅ 完成 |
| TD-12-08 | DT-12-04/05 AI 应用后端增量 | ai_apps 三表模型 + CRUD/publish/calls API + 模块注册 | openbase/modules/ai_apps/、openbase/core/models/business.py | ✅ 完成 |
| TD-12-09 | DT-12-04 四系统代理 | /api/v1/proxy/{system}/* 路由表转发 | openbase/modules/proxy/ | ✅ 完成 |
| TD-12-10 | DT-12-03 动态模块 API | dynamic_modules 表 + /api/v1/modules API + 种子 | openbase/modules/frontend/、openbase/core/db/init.py | ✅ 完成 |
| TD-12-11 | DT-12-09 前端测试 | 单元/组件测试（25 用例，覆盖率 96%） | openbase-ui/tests/** | ✅ 完成 |
| TD-12-12 | DT-12-10 部署配置 | 构建脚本、nginx 配置示例 | openbase-ui/scripts/、openbase-ui/nginx.conf.example | ✅ 完成 |
| TD-12-13 | DT-12-11 响应式 | 三断点栅格/侧边栏折叠/表格横滚/图表自适应（内置组件） | openbase-ui/src/core/components/**、src/core/styles/** | ✅ 完成 |

## 2. 范围确认

| 项 | 内容 |
|----|------|
| 实现项 | 上述 TD-12-01~13（P0 优先：底座/动态模块/鉴权/OpenLLM 核心/AI 应用/后端增量） |
| 排除项 | 语义路由/A-B 测试/插件/配置中心/Webhook/计费深度对接（backlog，依赖四系统 API） |
| 优先级 | P0：TD-12-01~04/08~10；P1：TD-12-05~07/11~13 |
| 验收 | 对齐 AC-12-01~11：构建 0 错误、Lint 0、测试 100%、覆盖率 ≥80%、三端无溢出 |

## 3. Subtask CheckList（子任务状态表）

| TD-ID | 子任务 | 完成 | 推迟版本（如未完成） |
|-------|--------|------|---------------------|
| TD-12-01 | 工程初始化/布局/token/路由/状态/组件 | ✅ | - |
| TD-12-02 | 注册表/懒加载/权限 | ✅ | - |
| TD-12-03 | 登录/拦截器/错误映射 | ✅ | - |
| TD-12-04 | OpenLLM 26 页面（核心页完整+次级页模板） | ✅ | - |
| TD-12-05~07 | 知识库/记忆/画像页面（核心页完整） | ✅ | - |
| TD-12-08 | ai_apps 模型+API | ✅ | - |
| TD-12-09 | proxy 代理 | ✅ | - |
| TD-12-10 | dynamic_modules 模型+API+种子 | ✅ | - |
| TD-12-11 | 前端测试（25 用例/覆盖率 96.13%） | ✅ | - |
| TD-12-12 | 部署配置 | ✅ | - |
| TD-12-13 | 响应式组件 | ✅ | - |

**Subtask CheckList：13/13 完成，无推迟项。**

## 4. 版本控制记录（分支策略与提交约定）

| 项 | 约定 |
|----|------|
| 分支策略 | trunk-based（单主干 main 直接开发，v1.2.0 阶段无需 feature 分支，与 v1.0.0/v1.1.0 一致） |
| Commit 格式 | `type(scope): subject`（feat/fix/docs/style/refactor/test/chore） |
| RT-ID footer | 提交信息末尾引用 RT-ID：`Refs: RT-201, RT-205`（追溯需求） |
| TDD 合规 | feat/fix 提交必须包含对应测试文件变更；测试先于生产代码 |
| 双远端 | origin（openbase.git）+ backup（openbase-backup.git），post-push 自动镜像 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | AD-OpenBase-Dev | 初始创建：TD-ID 13 项映射 + 范围确认 + Subtask CheckList + 版本控制约定 |
