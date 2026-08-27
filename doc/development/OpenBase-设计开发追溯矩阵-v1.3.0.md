# OpenBase 设计开发追溯矩阵 - v1.3.0（TD-ID）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.3.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-27 |
| 存放 | doc/development/ |

---

## 1. TD-ID 追溯矩阵（DT-ID → TD-ID → 涉及文件 → 状态）

> Phase 1（OpenLLM 模型中心 + 402 错误码）已完成；Phase 2~6 后续 Phase 编码时追加。

| TD-ID | 设计项 | DT-ID | 涉及文件 | 状态 |
|-------|--------|-------|---------|------|
| TD-13-28 | 代理层 402 错误码统一处理 | DT-13-28 | `openbase/core/errors/codes.py`、`openbase/modules/proxy/__init__.py`、`tests/test_proxy_quota.py` | ✅ 完成 |
| TD-13-01 | 提供商管理 CRUD | DT-13-01 | `openbase-ui/src/modules/openllm/pages/Providers.vue` | ✅ 完成 |
| TD-13-02 | 模型管理 CRUD + 定价 | DT-13-02 | `openbase-ui/src/modules/openllm/pages/Models.vue` | ✅ 完成 |
| TD-13-03 | 本地模型（仓库/GPU 调度/更新） | DT-13-03 | `openbase-ui/src/modules/openllm/pages/LocalModels.vue` | ✅ 完成 |
| TD-13-04 | 注册/找回密码 | DT-13-04 | `openbase-ui/src/modules/openllm/pages/AuthExt.vue` | ✅ 完成 |
| TD-13-05 | 个人设置 | DT-13-05 | `openbase-ui/src/modules/openllm/pages/Settings.vue` | ✅ 完成 |
| TD-13-06 | 用量统计（趋势/导出/明细） | DT-13-06 | `openbase-ui/src/modules/openllm/pages/Usage.vue` | ✅ 完成 |
| TD-13-29 | 我的收藏 | DT-13-29 | `openbase-ui/src/modules/openllm/pages/Favorites.vue` | ✅ 完成 |
| TD-13-30 | 模型分类/对比 | DT-13-30 | `openbase-ui/src/modules/openllm/pages/Categories.vue`、`Comparison.vue` | ✅ 完成 |
| TD-13-路由 | 新页面路由注册 | DT-13-01~06/29/30 | `openbase-ui/src/modules/openllm/index.ts` | ✅ 完成 |
| TD-13-07 | 对话管理（新建/归档/聊天窗口） | DT-13-07 | `openbase-ui/src/modules/openllm/pages/Conversations.vue` | ✅ 完成 |
| TD-13-08 | 监控仪表盘补全（成本/错误率/告警列表/时间范围） | DT-13-08 | `openbase-ui/src/modules/openllm/pages/Monitoring.vue` | ✅ 完成 |
| TD-13-09 | API 密钥管理 | DT-13-09 | `openbase-ui/src/modules/openllm/pages/ApiKeys.vue` | ✅ 完成 |
| TD-13-10 | 告警管理 | DT-13-10 | `openbase-ui/src/modules/openllm/pages/Alerts.vue` | ✅ 完成 |
| TD-13-11 | 成本分析 + 预算管理 | DT-13-11 | `openbase-ui/src/modules/openllm/pages/Costs.vue` | ✅ 完成 |
| TD-13-12 | 路由策略 + 熔断器 | DT-13-12 | `openbase-ui/src/modules/openllm/pages/Routing.vue` | ✅ 完成 |
| TD-13-27 | 基座与后端调试（登录/鉴权/RBAC/动态模块 E2E + 代理链路） | DT-13-27 | 后端 uvicorn + 前端 vite + 浏览器 E2E | ✅ 完成 |
| TD-13-13 | RAG 对话（流式/来源引用/重新生成） | DT-13-13 | `openbase-ui/src/modules/knowledge/pages/ChatView.vue` | ✅ 完成 |
| TD-13-14 | 知识库列表补全（搜索/删除/分页） | DT-13-14 | `openbase-ui/src/modules/knowledge/pages/KnowledgeList.vue` | ✅ 完成 |
| TD-13-15 | 知识库详情补全（分块/进度/删除文档） | DT-13-15 | `openbase-ui/src/modules/knowledge/pages/KnowledgeDetail.vue` | ✅ 完成 |
| TD-13-16 | 用户管理 | DT-13-16 | `openbase-ui/src/modules/knowledge/pages/Users.vue` | ✅ 完成 |
| TD-13-17 | 系统配置 | DT-13-17 | `openbase-ui/src/modules/knowledge/pages/Settings.vue` | ✅ 完成 |
| TD-13-18 | 记忆图谱（d3 力导向） | DT-13-18 | `openbase-ui/src/modules/memory/pages/MemoryGraph.vue` | ✅ 完成 |
| TD-13-19 | 会话记忆列表补全（过滤/分页） | DT-13-19 | `openbase-ui/src/modules/memory/pages/MemoryList.vue` | ✅ 完成 |
| TD-13-20 | 知识库记忆详情补全（关联记忆） | DT-13-20 | `openbase-ui/src/modules/memory/pages/MemoryDetail.vue` | ✅ 完成 |
| TD-13-21 | API 网关（密钥/审计日志） | DT-13-21 | `openbase-ui/src/modules/memory/pages/ApiGateway.vue` | ✅ 完成 |
| TD-13-31 | 管理后台（存储/监控/配置） | DT-13-31 | `openbase-ui/src/modules/memory/pages/Admin.vue` | ✅ 完成 |
| TD-13-22 | 画像列表补全（过滤/分页/删除） | DT-13-22 | `openbase-ui/src/modules/portrait/pages/PortraitList.vue` | ✅ 完成 |
| TD-13-23 | 画像详情补全（特征分布/关联画像） | DT-13-23 | `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue` | ✅ 完成 |
| TD-13-24 | 画像查询（多条件组合） | DT-13-24 | `openbase-ui/src/modules/portrait/pages/PortraitSearch.vue` | ✅ 完成 |
| TD-13-25 | 标签管理 | DT-13-25 | `openbase-ui/src/modules/portrait/pages/Tags.vue` | ✅ 完成 |
| TD-13-26 | 数据总览（KPI/图表） | DT-13-26 | `openbase-ui/src/modules/portrait/pages/Overview.vue` | ✅ 完成 |
| TD-13-32 | 规则引擎 | DT-13-32 | `openbase-ui/src/modules/portrait/pages/Rules.vue` | ✅ 完成 |

**Step 3 全 Phase 完成统计：设计项 33/33（TD-13-01~32 + TD-13-路由）**

## 2. Subtask CheckList

| 子任务 | 设计规划 | 实际完成 | 文件名一致 | 判定 |
|--------|---------|---------|:---:|:---:|
| 402 错误码（错误码表 + 代理包装） | codes.py + proxy 402 分支 | 完成 | ✅ | ✅ |
| 提供商 CRUD 页面 | Providers.vue 补全 | 完成 | ✅ | ✅ |
| 模型 CRUD + 定价页面 | Models.vue 补全 | 完成 | ✅ | ✅ |
| 本地模型页面 | LocalModels.vue 补全 | 完成 | ✅ | ✅ |
| 注册/找回密码页面 | AuthExt.vue 新增 | 完成 | ✅ | ✅ |
| 个人设置页面 | Settings.vue 新增 | 完成 | ✅ | ✅ |
| 用量统计页面 | Usage.vue 新增 | 完成 | ✅ | ✅ |
| 我的收藏页面 | Favorites.vue 新增 | 完成 | ✅ | ✅ |
| 模型分类页面 | Categories.vue 新增 | 完成 | ✅ | ✅ |
| 模型对比页面 | Comparison.vue 新增 | 完成 | ✅ | ✅ |

**未完成项推迟记录**：Phase 2~6 页面按 Phase 计划推进，不在本次 Phase 1 交付内。

## 3. 版本控制记录

| 项 | 内容 |
|----|------|
| 分支策略 | git-flow（main ← develop ← feature） |
| Commit 模板 | `type(scope): subject`，footer 引用 RT-ID |
| 提交类型 | feat/fix/docs/style/refactor/test/chore |
| 本次变更范围 | openbase（codes.py/proxy）+ openbase-ui（9 页面 + 路由）+ tests |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-27 | AD-OpenBase-Dev | 初始创建：Phase 1 追溯矩阵（TD-13-01~06/28/29/30 + 路由，10 项完成）+ Subtask CheckList + 版本控制记录 |
| v1.0.1 | 2026-08-27 | AD-OpenBase-Dev | Phase 2 追加：TD-13-07~12 完成（对话/监控/密钥/告警/成本/路由 6 项），完成项 10→16 |
| v1.0.2 | 2026-08-27 | AD-OpenBase-Dev | Phase 3 追加：TD-13-27 基座调试完成（登录/鉴权/RBAC/动态模块 E2E + 代理链路验证），完成项 16→17 |
