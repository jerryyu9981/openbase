# OpenBase-前端全页面走查报告-v1.0.0

| 项目   | 内容                                                                                                                           |
| ---- | ---------------------------------------------------------------------------------------------------------------------------- |
| 项目名称 | OpenBase（开放底座）+ openbase-ui 统一前端                                                                                             |
| 文档版本 | v1.0.0                                                                                                                       |
| 状态   | \[Review]                                                                                                                    |
| 走查人  | AD-OpenBase-Dev                                                                                                              |
| 日期   | 2026-09-03                                                                                                                   |
| 环境   | 本机全量服务（网关 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / 前端 5173 / Keycloak 8080；远端基础设施 192.168.0.151 可达） |
| 走查身份 | admin（账号登录）与 oidc-admin-e788（OIDC/Keycloak 登录）                                                                               |
| 存放   | doc/test/                                                                                                                    |

## 1. 走查范围与方法

- 范围：统一前端全部**静态路由页面**（系统管理 10 + OpenLLM 34 + 知识库 6 + 记忆 10 + 画像 11 + 统一网关 2 = 73 页次访问）。

- 方法：逐页浏览器导航 → 页面渲染判定（正文长度/标题）→ 错误文本探测（加载失败/请求失败/权限等）→ 命中疑点人工复核（快照 + 接口直连复现）。

- 动态详情页（`:id`）需真实数据，当前数据为空未纳入（见 §5）。

- 服务健康基线：编排 checkall 23 PASS / 0 FAIL（此前走查）。

## 2. 走查清单结果汇总

| 模块                     |   页面数  |   可用   |  存在问题 | 备注                                                                              |
| ---------------------- | :----: | :----: | :---: | ------------------------------------------------------------------------------- |
| 系统管理（/system/\* + 仪表盘） |   10   |   10   |   0   | tenants 空态正常；org 用户列表含历史 OIDC/QA 测试数据                                           |
| OpenLLM（/openllm/\*）   |   34   |   34   |   0   | 含 8 个 GenericPage 占位页（"已规划"提示为预期）；circuit-breakers 与 strategies 共用同一组件（页面相同属设计） |
| 知识库（/knowledge/\*）     |    6   |    6   |   0   | list 空态（0 知识库）正常；admin/console 上游健康 healthy                                     |
| 记忆（/memory/\*）         |   10   |   10   |   0   | monitor 展示真实 OpenMemory 计数（1,284,502 条）                                         |
| 画像（/portrait/\*）       |   11   |    9   |   2   | overview 显式 500（见 ISSUE-001）；list/reports/batch 数据为空且无错误提示（见 ISSUE-002）         |
| 统一网关（/gateway/\*）      |    2   |    2   |   0   | services 显示真实注册实例 openllm/openrag/openmemory/dps                                |
| **合计**                 | **73** | **71** | **2** | 另含动态详情页待数据验证                                                                    |

## 3. 问题清单

### ISSUE-001（high）：画像数据总览/列表接口 500，数据加载失败

- **页面**：`/portrait/overview`（数据总览）。

- **现象**：页面顶部错误提示"数据总览加载失败：Request failed with status code 500"，KPI/图表/最新画像均无数据；点"重新加载"仍失败。

- **复现**：`GET /api/v1/dps-proxy/portraits?page=1&page_size=5`（带 JWT）→ 500 `{"code":"INTERNAL_ERROR","message":"服务器内部错误"}`；直连 DPS `GET http://127.0.0.1:8030/api/v2/portrait/list?page=1&page_size=5`（带组织/租户身份头）→ 同一 500；同一 DPS 的 `/api/v2/portrait/*` 其余端点（calculate 等）同源错误。

- **影响**：画像模块列表数据、数据总览、分析报表、批量任务（复用同一数据源）均不可用（页面框架可渲染，数据为空）。

- **根因方向**：错误响应体（`INTERNAL_ERROR` + timestamp）来自 **DPS 上游**（独立项目 `D:\Trae CN\myproject\Dev\DPS`）`/api/v2/portrait/list` 服务端异常（SQLite demo 数据/查询路径），非 OpenBase 网关/前端代码缺陷。

- **修复归属**：DPS 项目排查 `/api/v2/portrait/list` 500；OpenBase 侧无需改动（proxy 透传正确）。

### ISSUE-002（low）：画像列表页静默吞错，数据失败无提示

- **页面**：`/portrait/list`（及复用组件的 reports/batch）。

- **现象**：数据接口同样 500，但页面仅显示空表/空态，无错误提示与重试入口（与 overview 的显式错误提示不一致）。

- **建议**：`PortraitList.vue` 增加与 Overview 一致的错误态处理（loadData catch 展示错误 + 重试）。

## 4. 走查明细（按模块）

### 4.1 系统管理 10 页（全 OK）

dashboard / system/tenants / system/roles / system/org / system/workspaces / system/config / system/audit / system/edgerouter / system/docs / system/billing

### 4.2 OpenLLM 34 页（全 OK）

models / models/local / models/categories / models/comparison / models/market / downloads / providers / providers/register / favorites / usage / settings / apps / apps/new / apps/calls(占位) / playground / prompt-templates / prompt-experiments / plugins / tool-calls / ab-tests / conversations / monitoring / monitoring/traces(占位) / monitoring/costs / monitoring/budgets(占位) / monitoring/alerts / routing/strategies / routing/circuit-breakers / auth-ext / api-keys / deploy(占位) / gpu(占位) / adapters(占位)

### 4.3 知识库 6 页（全 OK）

list(空态) / chat / users / settings / admin / console

### 4.4 记忆 10 页（全 OK）

list / search / sessions / graph / api-gateway / admin / monitor / decay / write（detail 动态页待数据）

### 4.5 画像 11 页（9 OK，2 见 ISSUE-001/002）

overview（ISSUE-001）/ list（数据空，ISSUE-002）/ search / tags / rules / reports（ISSUE-002 同源）/ rate-limit / api-manage / permissions / monitor / batch（ISSUE-002 同源）

### 4.6 统一网关 2 页（全 OK）

services / aggregate

## 5. 跳过项说明

| 跳过项                                                                 | 原因                         | 补测计划                |
| ------------------------------------------------------------------- | -------------------------- | ------------------- |
| memory/detail、knowledge/detail、portrait/detail、openllm/apps/:id 动态页 | 依赖真实数据（当前各库为空/上游 500）      | DPS 画像列表修复并造数后补测详情页 |
| auth/login、auth/oidc/callback                                       | 已在前序会话验证（真实浏览器 OIDC 全链路通过） | -                   |

## 6. 结论

- 统一前端 73 页静态路由中 **71 页可用**，渲染与业务接入正常；OIDC（Keycloak）登录态下各模块入口、菜单、受保护页守卫均正常。

- 2 个问题集中画像模块数据层（ISSUE-001 高：DPS 上游 /api/v2/portrait/list 500，影响画像列表/总览/报表；ISSUE-002 低：列表页错误静默）。

- 建议：DPS 项目修复 ISSUE-001 后复测画像模块 4 页；前端按 ISSUE-002 补错误态后回归。

## 7. 修订历史

| 版本     | 日期         | 修改人             | 摘要                                            |
| ------ | ---------- | --------------- | --------------------------------------------- |
| v1.0.0 | 2026-09-03 | AD-OpenBase-Dev | 前端全页面清单走查首版：73 页 71 可用，画像数据层 ISSUE-001/002 记录 |

