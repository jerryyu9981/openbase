# OpenBase 全栈后端能力缺口清单 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）统一前端 |
| 文档版本 | v1.16.0 |
| 状态 | **[Review]** |
| 适用范围 | 统一前端 `openbase-ui`（OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS 五服务页面） |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-10-22 |
| 上游依据 | 《OpenBase-前端架构设计文档-v1.4.11》v1.21.0 §8.19；《OpenBase-DevLogReport-v1.4.11》v2.13.0 §2.22；《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》 |
| 证据 | `doc/test/evidence/s6/ui-func-audit-v190.json`、`ui-func-audit-v190-summary.md`、`proxy-reachability-v190.json` |
| 存放 | `doc/planning/` |

---

## 1. 目的与口径

### 1.1 目的

1. 回答「全栈运行时，前端所有页面/功能的错误在哪里」；
2. 把「页面已存在、但后端不具备能力」的部分**单列成账**，作为后续迭代的派单依据；
3. 明确本轮已闭环项与后续轮次路线，避免「页面看起来能用、实际是假数据」的误判。

### 1.2 审计口径

| 层级 | 覆盖内容 | 判定 |
|------|----------|------|
| L1 加载级 | 77 页逐页导航 | 未跳登录/未退回 dashboard/未触发渲染兜底/无 console·page error/无 API 5xx |
| L2 交互级 | 每页非破坏性动作（页签切换、查询、刷新、详情、连通性检测、测试连接等，**不执行删除/保存/提交/发布/回滚/导入导出**） | 动作后无新增 console/page error、无新增 API 失败 |
| L3 API 面 | 逐页记录实际发出的 `/api/**` 请求 | 有/无后端调用、端点状态码、是否 4xx/5xx |
| L4 通道级 | 对候选聚合端点做 GET 探测（admin JWT） | 200 / 401 / 405 / 502，用于区分「前端没接」与「后端没有」 |

> 说明：写操作（新增/删除/状态切换）除「提供商管理」做过一次**等值 PUT** 验证外，未在审计中批量执行，避免污染运行态数据。

### 1.3 环境

- 五服务全部在线：OpenBase `:8000`、OpenLLM `:8001`、OpenRAG `:8010`、OpenMemory `:8020`、DPS `:8030`；前端 Vite `:5173`。
- 登录身份：`admin`（`permissions=["*"]`）。

---

## 2. 审计结果

| 指标 | 结果 |
|------|------|
| 页面总数 | **77**（OpenBase 44 / OpenLLM 11 / OpenRAG 2 / OpenMemory 6 / DPS 14） |
| L1+L2 结果 | **PASS 76 / FAIL 1**（唯一 FAIL 为 `net::ERR_NO_BUFFER_SPACE`，Chromium 在沙箱内写 `debug.log` 受限导致的资源加载抖动；该页单页复跑 0 错误，判为环境噪声，非应用缺陷） |
| 首轮基线 | PASS 77 / FAIL 0（同一套探针，服务全部预热后） |
| API 失败次数（4xx/5xx/请求失败） | **0** |
| 无后端调用的页面 | **24**（R1 3 页、R2 2 页、R3 2 页、R4 6 页、R5 8 路由、R6 2 页、R7 5 页收口后：52 − 28） |
| 其中「无调用且无可交互动作」的静默页 | 28（初始审计口径，未随 R1~R7 重采样） |

> 采样口径说明：无后端调用按「首屏 1.2s 稳定窗口内是否发出 `/api/**`」判定；记忆图谱/衰减、模板包导出、血缘、措施建议等**按需触发**页在该窗口内可能尚无请求，属测量假阴性。已在 §4 逐页以源码接线与实测复核，避免误判。

**结论**：运行时不存在「页面报错」类缺陷；真正的缺口是**大量页面没有接后端**——数据来自前端硬编码（源码注释标注为「契约 mock」），用户看到的数字、列表、开关均为演示值。

---

## 3. 缺口分类

| 类别 | 定义 | 处置方向 |
|------|------|----------|
| **A 前端未接线** | OpenBase 已有可用端点（实测 200），页面仍用 mock | 前端补 API 封装与页面接线，成本最低 |
| **B 上游仅 JWT 通道** | OpenLLM 有该能力，但路由依赖 `get_current_active_user`（只认 OpenLLM 自签 JWT），经 OpenBase 聚合返回 **401** | 上游改双通道依赖 `get_current_active_user_or_api_key`，或新增 `/openllm/v1/*` 网关端点 |
| **C 缺列表/定位接口** | OpenBase 侧端点仅支持写/单条读（实测 **405**），或缺少按 id 操作所需的标识（如服务 Key 列表无 id） | 补 `GET` 列表端点与稳定标识（分页 + 过滤 + id 化吊销）——**R2 已闭环 3 项** |
| **D 上游超时** | 能力存在，但 10s 代理超时内未返回（实测 **502**） | 上游性能治理或按端点调整超时 |
| **E 无后端能力** | 三仓均无对应接口，属纯前端形态 | 需产品裁定：建设后端能力，或页面降级为「未交付」说明页 |

---

## 4. 逐页缺口清单

> **排期口径（v1.8.0）**：本表只保留「能力现状与缺口」，不再逐行标注轮次；所有未闭环项（含跨仓/运维/QA）的排期统一收敛至《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》，以该计划为唯一排期源。

### 4.1 OpenBase 公共域（44 页）

| # | 页面 | 路由 | 现状 | 类别 | 目标/缺口接口 | 状态 |
|:-:|------|------|------|:----:|----------------|------|
| 1 | 仪表盘 | `/dashboard` | **真实（v1.9.7 R7）** | — | `/users` + `/proxy/openllm/api/v1/monitoring/dashboard`（客户端聚合） | **已闭环** |
| 2 | 租户管理 | `/platform/identity/tenants` | 真实 | — | `/tenants` | 已接 |
| 3 | 角色与权限 | `/platform/identity/roles` | **真实（v1.9.5 R5）** | — | `/roles`（CRUD）、`/roles/{id}`、`/roles/{id}/permissions`、`/roles/permissions/catalog`（新增，双通道后 200） | **已闭环** |
| 4 | 组织/团队/用户 | `/platform/identity/org` | 真实 | — | `/users`、`/org/departments` | 已接 |
| 5 | 工作空间 | `/platform/identity/workspaces` | **真实（v1.9.5 R5）** | — | `/workspaces`、`/workspaces/{id}/members`、`/workspaces/{id}/resources`、`/virtual-keys`（列表/创建/轮换，双通道后 200） | **已闭环** |
| 6 | 用户管理 | `/platform/identity/users` | **真实（v1.9.1 R1）** | — | `/users` | **已闭环** |
| 7 | 记忆管理席位 | `/platform/identity/memory-admin` | 真实 | — | `/memory-proxy/monitor`、`/memories` | 已接 |
| 8 | 注册/找回密码 | `/platform/identity/auth-ext` | mock | E | 无 `/auth/register`、无找回密码 | **不建设（2026-10-23 裁定）** |
| 9 | 画像数据权限 | `/platform/identity/dps-permissions` | mock | E | 无对应端点 | **只读建设（v1.12.0）**：接 `/permissions/roles` + `/permissions/check`；写面不建设 |
| 10 | 全局配置 | `/platform/config/general` | **真实（v1.9.2 R2）** | — | `GET /configs`（新增）、`POST /configs`、`GET /configs/{key}/versions`、`POST /configs/{key}/rollback` | **已闭环** |
| 11 | 模块开关 | `/platform/config/modules` | 真实 | — | `/modules` | 已接 |
| 12 | API 密钥 | `/platform/config/api-keys` | **真实（v1.9.2 R2）** | — | `/auth/api-keys`；新增 `id` 回显与 `DELETE /auth/api-keys/by-id/{id}` | **已闭环（含 id 化吊销）** |
| 13 | 画像接口限流 | `/platform/config/rate-limits` | mock | E | 无对应端点 | **只读建设（v1.12.0）**：接 `/rate-limits/status`（只读） |
| 14 | 日志中心 | `/platform/observability/logs` | 真实 | — | `/logs/search`、`/logs/facets` | 已接 |
| 15 | 测试记录 | `/platform/observability/test-records` | **真实（v1.9.2 R2）** | — | `GET /test-records`、`GET /test-runs`（新增）+ 既有开轮/记录/改判/summary | **已闭环** |
| 16 | 统一监控 | `/platform/observability/monitoring` | **真实（v1.9.7 R7）** | — | `/monitoring/dashboard`、`/alerts?status=firing`（双通道后 200） | **已闭环** |
| 17 | 成本分析 | `/platform/observability/monitoring/costs` | **真实（v1.9.4 R4）** | — | `/monitoring/costs`、`/monitoring/costs/optimization-suggestions`、`/budgets`（双通道后 200） | **已闭环** |
| 18 | 告警中心 | `/platform/observability/monitoring/alerts` | **真实（v1.9.4 R4）** | — | `/alerts/rules`（增删改查）、`/alerts`、`/alerts/{id}/resolve|acknowledge`（双通道后 200） | **已闭环** |
| 19 | 链路追踪 | `/platform/observability/monitoring/traces` | **真实（v1.9.4 R4）** | — | `/monitoring/traces`、`/monitoring/traces/statistics`、`/monitoring/traces/{id}`（双通道后 200） | **已闭环（新建页面替换占位）** |
| 20 | 预算管理 | `/platform/observability/monitoring/budgets` | **真实（v1.9.4 R4）** | — | `/budgets`、`/budgets/{id}/status`（双通道后 200） | **已闭环（新建页面替换占位）** |
| 21 | GPU 资源 | `/platform/observability/gpu` | **真实（v1.9.6 R6）** | — | `/local-models/gpu-allocation/status`、`/local-models/gpu-info`；探测短超时（connect 2s/read 5s） | **已闭环** |
| 22 | 用量统计 | `/platform/observability/usage` | **真实（v1.9.4 R4）** | — | `/usage/summary`、`/usage/trends`、`/usage/detail`（双通道后 200） | **已闭环** |
| 23 | 计费 | `/platform/observability/billing` | **真实（v1.9.4 R4）** | — | `/billing/usage/statistics`、`/billing/quotas`、`/billing/bills`（双通道后 200） | **已闭环** |
| 24 | 服务发现与编排 | `/platform/observability/service-discovery` | 真实 | — | `/services`、`/gateway/ping` | 已接 |
| 25 | 聚合网关测试 | `/platform/observability/gateway-test` | 表单页 + 交互用例 | — | `/gateway/aggregate`（200；审计未自动提交） | **已补用例（v1.10.2）**：成功/部分失败/超时/重置 4 例 |
| 26 | 应用调用记录 | `/platform/observability/app-calls` | **真实（v1.12.0）** | — | `GET /ai-apps/calls`（跨应用聚合 + 筛选 + 分页） | **已闭环** |
| 27 | 画像系统监控 | `/platform/observability/dps-monitor` | **部分真实（v1.9.7 R7）** | — | `/dps-proxy/health`；指标/告警规则无上游端点，页面显式说明未开放 | **已收敛（仅健康）** |
| 28 | 提供商管理 | `/platform/governance/providers` | **真实（本轮）** | — | `/proxy/openllm/api/v1/providers` | **已闭环** |
| 29 | 模型分类 | `/platform/governance/model-categories` | **真实（v1.9.3 R3）** | — | `/model-categories`、`/model-categories/tree`、`/model-categories/{id}/models`（双通道后 200） | **已闭环** |
| 30 | 路由策略 | `/platform/governance/routing` | **真实（v1.9.5 R5）** | — | `/routing/semantic`（CRUD/测试/缓存）、`/routing/cascade`（双通道后 200） | **已闭环** |
| 31 | 熔断器 | `/platform/governance/circuit-breakers` | **真实（v1.9.5 R5）** | — | `/routing/circuit-breakers`（列表/重置/配置/事件） | **已闭环** |
| 32 | 模型部署 | `/platform/governance/deploy` | **真实（v1.9.7 R7）** | — | `/open-models`（列表）、`/{id}/deploy|deploy-status|logs|stop` | **已闭环（新建页面替换占位）** |
| 33 | 下载管理 | `/platform/governance/downloads` | **真实（v1.9.6 R6）** | — | `/open-models/downloads`、`pause|resume|cancel-download`、`download`、`deploy`（双通道后 200） | **已闭环** |
| 34 | 工具调用监控 | `/platform/governance/tool-calls` | **真实（v1.9.5 R5）** | — | `/tool-calls`、`/tool-calls/{id}`（双通道后 200） | **已闭环** |
| 35 | A/B 测试 | `/platform/governance/ab-tests` | **真实（v1.9.5 R5）** | — | `/routing/ab-tests`（列表/创建/暂停/恢复/完成/报表） | **已闭环** |
| 36 | Prompt 模板 | `/platform/governance/prompt-templates` | **真实（v1.9.5 R5）** | — | `/prompt-templates`（CRUD/版本/回滚/导入） | **已闭环** |
| 37 | Prompt 实验 | `/platform/governance/prompt-experiments` | **真实（v1.9.5 R5）** | — | `/prompt-experiments`（列表/创建/启动/完成/报表） | **已闭环** |
| 38 | 文档中心 | `/platform/developers/docs` | 静态文档 | E | 无端点（内容型页面，可保留） | 保留 |
| 39 | EdgeRouter 与适配器 | `/platform/developers/edgerouter` | **真实（v1.9.1 R1）** | — | `/edge/status`、`/edge/health`、`/edge/adapters`、`/edge/organizations`、`/edge/quotas/{org}`、`/edge/audit/logs`（均 200） | **已闭环** |
| 40 | 插件管理 | `/platform/developers/plugins` | **真实（v1.9.3 R3）** | — | `/plugins`、`/plugins/tools`、`/plugins/{id}/health|enable|disable`、`/plugins/register`（双通道后 200） | **已闭环** |
| 41 | 画像 API 管理 | `/platform/developers/dps-api` | mock | E | 无对应端点 | **只读建设（v1.12.0）**：接 `/api-registry` + `/error-codes` |
| 42 | 知识库管理后台 | `/platform/developers/knowledge-admin` | 真实 | — | `/rag-proxy/collections` | 已接 |
| 43 | 知识库 API 控制台 | `/platform/developers/knowledge-console` | **真实（v1.12.0）** | — | `rag-proxy/collections`、`/health`、`/collections/{id}/query/retrieve` | **已闭环** |
| 44 | 个人设置 | `/personal/settings` | **真实（v1.9.7 R7 + v1.10.1）** | — | `GET/PUT /auth/me`、`POST /auth/change-password`、`GET/PUT /auth/notification-preferences`（v1.10.1 新增） | **已闭环（资料+密码+通知偏好）** |

### 4.2 OpenLLM（11 页）

| # | 页面 | 路由 | 现状 | 类别 | 说明 |
|:-:|------|------|------|:----:|------|
| 1 | 模型管理 | `/openllm/models` | 真实 | — | `/llm-proxy/models` |
| 2 | 本地模型 | `/openllm/models/local` | **真实（v1.10.0）** | — | `/local-models` 列表/仓库/状态/GPU + 启停/更新/删除/拉取；R6 短超时修复后 502 消除 |
| 3 | 模型对比 | `/openllm/models/comparison` | **真实（v1.10.0）** | — | 模型池 `/open-models` + 对比 `/models/compare`（`comparison.advantages`） |
| 4 | 开源模型市场 | `/openllm/models/market` | **真实（v1.10.0）** | — | `/open-models` 列表 + `/open-models/{id}/download` |
| 5 | 我的收藏 | `/openllm/favorites` | **真实（v1.10.0）** | — | `/models/favorites`、`/models/favorite-folders`、取消收藏 |
| 6 | AI 应用 | `/openllm/apps` | 真实 | — | `/ai-apps` |
| 7 | 创建应用 | `/openllm/apps/new` | 真实（提交时） | — | `POST /ai-apps` |
| 8 | Playground | `/openllm/playground` | 真实 | — | `/llm-proxy/models`、`/llm-proxy/chat` |
| 9 | 对话管理 | `/openllm/conversations` | 真实 | — | `/llm-proxy/conversations` |
| 10 | 模型对比推荐 | `/openllm/recommend` | mock | E | 无推荐端点 | **冻结（2026-10-23 裁定）**：无标注/评分数据基础 |
| 11 | 报表趋势 | `/openllm/reports-trend` | **真实（v1.12.0）** | — | `/usage/trends` + `/monitoring/dashboard` + `/monitoring/costs`（不新增端点） | **已闭环** |

### 4.3 OpenRAG（2 页）

| # | 页面 | 路由 | 现状 | 类别 |
|:-:|------|------|------|:----:|
| 1 | 知识库 | `/knowledge/list` | 真实 | — |
| 2 | RAG 对话 | `/knowledge/chat` | 真实 | — |

### 4.4 OpenMemory（6 页）

| # | 页面 | 路由 | 现状 | 类别 |
|:-:|------|------|------|:----:|
| 1 | 记忆列表 | `/memory/list` | 真实 | — |
| 2 | 记忆搜索 | `/memory/search` | 真实（按需触发） | — |
| 3 | 会话管理 | `/memory/sessions` | 真实 | — |
| 4 | 记忆图谱 | `/memory/graph` | 真实 | — |
| 5 | 衰减配置 | `/memory/decay` | 真实 | — |
| 6 | 写入记忆 | `/memory/write` | 真实（提交时） | — |

### 4.5 DPS（14 页）

| # | 页面 | 路由 | 现状 | 类别 |
|:-:|------|------|------|:----:|
| 1 | 数据总览 | `/portrait/overview` | 真实 | — |
| 2 | 画像列表 | `/portrait/list` | 真实 | — |
| 3 | 画像搜索 | `/portrait/search` | 真实 | — |
| 4 | 标签管理 | `/portrait/tags` | 真实 | — |
| 5 | 规则引擎 | `/portrait/rules` | mock | E | **冻结（2026-10-23 裁定）**：写面已按 ADR-290-01 收口 410 |
| 6 | 模板族管理 | `/portrait/dps/templates` | 真实 | — |
| 7 | 画像模板新建 | `/portrait/dps/templates/new` | 真实（提交时） | — |
| 8 | 模板包导出/导入 | `/portrait/dps/template-packages` | 真实（按需触发） | — |
| 9 | 标签血缘反查 | `/portrait/dps/lineage` | 真实（按需触发） | — |
| 10 | 措施建议 | `/portrait/dps/measures` | 真实（按需触发） | — |
| 11 | 评分类型 | `/portrait/dps/scoring-types` | 真实 | — |
| 12 | AI 标注候选与复核 | `/portrait/dps/annotation-adapters` | 真实（按需触发） | — |
| 13 | 标注模板管理 | `/portrait/dps/annotation-templates` | 真实 | — |
| 14 | 标签体系查看 | `/portrait/dps/tags` | 真实 | — |

---

## 5. 本轮已闭环

| 项 | 内容 | 证据 |
|---|------|------|
| 通用代理来源映射 | `/api/v1/proxy/{system}/{path}` 出站来源由固定 `openbase-generic-proxy` 改为按系统映射 `openbase-llm-proxy` / `-rag-` / `-memory-` / `-dps-`，使下游 `TRUSTED_PROXY_SOURCES` 能采信身份头 | `tests/test_proxy_target_system_v190.py` 6 例；OpenLLM 日志由 `identity_headers_ignored` 转为采信 |
| OpenLLM 凭据注入 | 通用代理在 `system=openllm` 时注入 `Authorization: Bearer <OpenLLM API Key>`（复用 `llm_proxy` 的租户级选 Key 规则），打通原生 `/api/v1/*` 的 API Key 通道 | 同上 2 例；实测 `GET /providers` 200 |
| 提供商管理真实化 | 页面接 `/proxy/openllm/api/v1/providers`，真实渲染名称/类型/Base URL/健康/优先级/模型数；新增/编辑/删除/启停走真实上游 | `tests/providers-v190.spec.ts` 4 例；浏览器实测 3 张卡片 + 模型数 3；等值 PUT 200 |
| 提供商模型数并发 500 的规避（v1.9.1） | 页面并发拉取 3 个提供商的模型数时，OpenLLM 必有一路 500（`scoped_session` 跨线程并发）；改为**串行**拉取并逐条容错，单条失败仅该行显示「—」 | 串行后连续 3 次浏览器加载均 0 error；根因登记为 OpenLLM 跨仓缺陷（§7 第 5 项） |
| **R1 用户管理**（v1.9.1） | 接 `/users`：真实列表（显示名/角色/状态/租户）、新建（含 `display_name`）、角色分配 `/users/{id}/role`、启停 `PUT`、停用 `DELETE`；角色下拉对齐五码标准集合；内置 admin 禁止停用 | `tests/r1-wiring-v191.spec.ts` 用户 4 例；浏览器实测 3 条真实用户、0 error |
| **R1 API 密钥**（v1.9.1） | 接 `/auth/api-keys`：真实列表（访问范围/描述/创建时间/状态）、创建（一次性明文 + 复制）、吊销；移除虚构的模型权限/速率/过期字段；对「列表无 id、吊销需明文」的后端约束做显式降级提示 | 同上 3 例；接口实测创建 → 列表（无明文）→ 吊销（`revoked=true`）全链路通过 |
| **R1 EdgeRouter**（v1.9.1） | 接 `/edge/**`：概览（status/health/能力开关）、组织（列表/新增/编辑）、配额（按组织查询/调整）、适配器（只读）、路由审计（分页）；移除「随机新增组织/配额/适配器开关」等假动作 | 同上 3 例；浏览器实测 6 个端点均 200（status/health/adapters/organizations）、0 error |
| **R2 列表端点**（v1.9.2） | OpenBase 新增 `GET /configs`（并集：DB ∪ 运行时 ∪ 默认值，支持 prefix/level 过滤）、`GET /test-records`（轮次/用例/结论过滤 + 分页）、`GET /test-runs`（含记录数） | `tests/test_r2_lists_v192.py` 9 例 |
| **R2 服务 Key id 化**（v1.9.2） | `ApiKeyOut` 增加 `id`；新增 `DELETE /auth/api-keys/by-id/{key_id}`（保留按明文吊销端点兼容）；前端改为按 id 吊销，解除「历史密钥不可吊销」限制 | 同上（含未知 id → 404）；`r1-wiring-v191` 吊销用例改为断言 by-id 端点 |
| **R2 两页接线**（v1.9.2） | 全局配置：列表/搜索/级别过滤/编辑（值 JSON 解析）/版本抽屉/回滚/导入导出全部走真实端点；测试记录：轮次下拉自动选中最新一轮并加载汇总、开新一轮 | `tests/r2-wiring-v192.spec.ts` 7 例；浏览器实测见 DevLogReport §2.16 |
| **R2 上游并发修复**（OpenLLM v1.9.2） | `get_db` 由 `scoped_session` 改为每请求独立 Session（`SessionFactory()`），从根因消除跨线程复用；`SessionLocal` 保留给既有直接调用方 | OpenLLM `test_db_session_concurrency_v192.py` 3 例；提供商页并发模型数不再 500 |
| **R3 双通道鉴权**（OpenLLM v1.9.3） | `plugins.py` 与 `model_categories.py` 全部路由由 `get_current_active_user` / `get_current_user` 改为 `get_current_active_user_or_api_key` | OpenLLM `test_r3_dual_channel_v193.py` 6 例；插件/分类既有 34 例回归通过 |
| **R3 两页接线**（v1.9.3） | 插件管理：真实列表/工具清单/启停/注册/删除/健康检查；模型分类：分类树标签云 + 分类下模型分页 + 维度切换；移除全部契约 mock | `tests/r3-wiring-v193.spec.ts` 8 例；聚合端点实测 4/4 200 |
| **R4 双通道鉴权**（OpenLLM v1.9.4） | `monitoring.py` / `traces.py` / `alerts.py` / `budgets.py` / `usage.py` / `billing.py` / `billing_v2.py` 共 46 处依赖改为 `get_current_active_user_or_api_key`；`monitoring.py` 的 `current_user.get("id")` 修正为 `getattr`；账单/计划写端点保持 `require_permission(PERM_BILLING_WRITE)` 不放宽 | OpenLLM `test_r4_dual_channel_v194.py` 15 例（14 条路由依赖断言 + 1 条「模块不得残留 JWT-only 依赖」守卫）+ R3 6 例回归，21 passed |
| **R4 六页接线**（v1.9.4） | 成本分析：三维度成本分布 + 预算列表 + 优化建议（只读，移除上游不存在的「一键应用」）；告警中心：规则增删改查/启停 + 告警确认/解决 + 服务端分页；链路追踪：统计卡 + 筛选列表 + Span 详情抽屉（新建页替换 `GenericPage`）；预算管理：列表/新建/状态抽屉（新建页替换 `GenericPage`）；用量统计：总览/趋势/明细/CSV 导出；计费：用量统计/配额/账单/消费趋势 | `tests/r4-wiring-v194.spec.ts` 17 例；`vue-tsc --noEmit` 通过；前端全量回归 306 passed |
| **R5 双通道鉴权**（OpenLLM v1.9.5） | `roles` / `workspaces` / `virtual_keys` / `semantic_routing` / `cascade_routing` / `circuit_breakers` / `ab_tests` / `prompt_templates` / `prompt_experiments` / `prompt_assembly` / `tool_calls` 共 11 文件依赖改 `get_current_active_user_or_api_key`；新增 `GET /roles/permissions/catalog` 权限目录端点 | OpenLLM `test_r5_dual_channel_v195.py` 28 条路由断言 + 2 条守卫（30 passed） |
| **R5 七页接线**（v1.9.5） | 角色与权限：角色 CRUD + 权限目录勾选保存 + 系统角色保护；工作空间：列表/新建/删除 + 成员增删 + 资源统计 + Virtual Key 创建/轮换；路由策略：语义路由 CRUD/启停/测试/缓存统计 + 熔断器列表/重置（移除假「手动开闭」）；工具调用：列表筛选/分页 + 输入输出详情（移除假调用链/取消）；Prompt 模板：CRUD/版本/回滚/导入/系统模板保护；Prompt 实验：创建/启动/完成/报表；A/B 测试：创建/暂停/恢复/完成/报表 | `tests/r5-wiring-v195.spec.ts` 15 例；`vue-tsc --noEmit` 通过；前端全量回归 321 passed |
| **R6 超时治理**（OpenLLM v1.9.6） | Ollama 轻量探测（`/api/tags`、`/api/ps`）由 300s 读/10s 连接改为 `OLLAMA_PROBE_TIMEOUT`（read 5s / connect 2s），拉取模型长任务超时不变；`open-models` 全部路由改双通道；收藏列表与下载任务列表改为单次 `IN` 批量查询（消除 N+1），下载任务列表批量补 `model_name` | OpenLLM `test_r6_perf_v196.py` 13 例（10 条路由断言 + 3 条性能守卫） |
| **R6 两页接线**（v1.9.6） | GPU 资源：接 `/local-models/gpu-allocation/status` + `/local-models/gpu-info`，展示分配/利用率/显存/占用模型与运行中模型；移除 mock 卡、随机趋势、温度/功耗列；下载管理：接 `/open-models/downloads` + 暂停/恢复/取消/重试/部署，移除本地 mock 与假删除 | `tests/r6-wiring-v196.spec.ts` 7 例；`vue-tsc --noEmit` 通过；前端全量回归 328 passed |
| **R7 资料端点**（OpenBase v1.9.7） | `/auth/me` 扩展 `display_name/email/phone`；新增 `PUT /auth/me`（邮箱格式校验）与 `POST /auth/change-password`（旧密码/强度校验） | `tests/test_auth_profile_v197.py` 6 例 |
| **R7 五页收敛**（v1.9.7） | 仪表盘：模块数 + `/users` + OpenLLM 24h 概览聚合，单源失败显示「—」；统一监控：接 `/monitoring/dashboard` + 未解决告警，移除 mock KPI/曲线；个人设置：资料回填/保存/改密走真实端点，通知偏好显式未开放；画像系统监控：仅保留 `/dps-proxy/health`，移除虚构指标与告警规则；模型部署：新建页接 `/open-models` 列表与部署/状态/日志/停止 | `tests/r7-wiring-v197.spec.ts` 9 例；`vue-tsc --noEmit` 通过；前端全量回归 337 passed |

---

## 6. 后续轮次路线图（建议）

| 轮次 | 主题 | 范围 | 关键依赖 |
|:----:|------|------|----------|
| R1 | A 类收口（低成本） | 用户管理、API 密钥、EdgeRouter 三页接真实端点 | **已完成（v1.9.1）** |
| R2 | C 类补列表 | `GET /configs`、`GET /test-records`、`GET /test-runs` + 两页接线；服务 Key 改 id 化吊销 | **已完成（v1.9.2）**；同时修复 OpenLLM `get_db` 并发缺陷 |
| R3 | B 类第一批 | OpenLLM `plugins`、`model-categories` 改双通道依赖；插件管理、模型分类两页接真实 | **已完成（v1.9.3）** |
| R4 | B 类第二批 | `monitoring/*`、`alerts`、`budgets`、`usage`、`billing` → 成本/告警/链路/预算/用量/计费六页 | **已完成（v1.9.4）**；指标表租户过滤见 §7 第 7 项 |
| R5 | B 类第三批 | `routing/*`、`prompt-*`、`tool-calls`、`roles`、`workspaces` → 治理与 RBAC 页 | **已完成（v1.9.5）**；新增权限目录端点 |
| R6 | D 类性能 | `local-models`、`models/favorites|compare`、`open-models/popular` 的 10s 超时治理 | **已完成（v1.9.6）**：探测短超时 + 双通道 + N+1 批量化 |
| R7 | E 类立项 | 仪表盘/统一监控/画像系统监控/个人设置等纯形态页 | **已完成（v1.9.7）**：可建 5 页落地，其余裁定不建设/保留 |
| R8 | 剩余事项处置与小版本迭代 | 通知偏好、DPS 指标/规则、OpenLLM 四页、租户过滤、跨仓/运维收口 | **已排期**：见《剩余事项统一清查与小版本迭代计划-v1.0.0》（v1.9.8 ~ v1.11.0）；其中通知偏好（OB-01）已于 v1.10.1 闭环 |

> 纪律：每轮完成「后端 + 前端 + 单测 + 浏览器实测 + 文档留痕 + 三远程推送」闭环，不跨轮混提交。

### 6.1 R7 产品裁定（E 类）

| 页面 | 裁定 | 依据 |
|------|------|------|
| 仪表盘 | **建设** | 已有 `/users` 与 OpenLLM `/monitoring/dashboard`，客户端可聚合 |
| 统一监控 | **建设** | `/monitoring/dashboard` + `/alerts` 已具备（R4 双通道） |
| 个人设置 | **建设（资料+密码+通知偏好）** | v1.9.7 新增 `PUT /auth/me`、`POST /auth/change-password`；v1.10.1 新增 `GET/PUT /auth/notification-preferences`（站内/邮件/Webhook + 事件开关） |
| 模型部署 | **建设** | `/open-models/{id}/deploy|deploy-status|logs|stop` 已具备 |
| 画像系统监控 | **收敛为健康页** | 仅 `/dps-proxy/health`；无指标/告警规则端点，移除虚构数据 |
| 注册/找回密码 | **不建设** | 无自助注册/找回端点；由管理员开户与重置 |
| 画像数据权限 | **只读建设（v1.12.0）** | 2026-10-23 裁定刷新：只读接 `/permissions/roles` + `/permissions/check`；写面不建设（ADR-290-01 已收口 410） |
| 画像接口限流 | **只读建设（v1.12.0）** | `/rate-limits/status` 已具备只读指标（含 `source` 标注） |
| 画像 API 管理 | **只读建设（v1.12.0）** | `/api-registry` + `/error-codes` 只读可用 |
| 应用调用记录 | **✅ 已闭环（v1.12.0）** | `GET /ai-apps/calls` 全局聚合 + `AppCallsView` |
| 知识库 API 控制台 | **✅ 已闭环（v1.12.0）** | `rag-proxy` 真实检索链路 + 真实性能指标 |
| 文档中心 | **保留** | 内容型页面，无需后端 |

---

## 7. 风险与假设

| # | 风险/假设 | 影响 | 缓解 |
|:-:|-----------|------|------|
| 1 | OpenLLM 原生 `/api/v1/*` 的 API Key 通道返回的是 **Key 所属用户**身份，不是终端用户 | 审计/权限粒度以服务账号为准，非真实操作者 | 身份头（`X-User-*`）已透传，供下游审计；如需终端级权限，改走 `/openllm/v1/*` 网关 |
| 2 | 通用代理注入 OpenLLM Key 属新增出站凭据面 | 若代理权限判定失效，可能放大影响 | 代理入口仍强制 JWT + 权限校验；Key 仅对 `system=openllm` 注入 |
| 3 | ~~上游 `local-models` 等端点 10s 超时~~ | 页面 502 | **已处置（R6 / v1.9.6）**：轻量探测改短超时（connect 2s/read 5s）；拉取模型长任务不变；页面降级展示 |
| 4 | 服务进程（DPS/OpenRAG）在长时间无人访问后被回收 | 审计出现 503 假失败 | 审计前统一健康检查；服务编排侧增加守护（运维项） |
| 5 | ~~**OpenLLM `scoped_session` + 线程池并发缺陷**~~ | 同步端点并发访问同一 Session → `InvalidRequestError` → 上游 500 | **已修复（R2 / OpenLLM v1.9.2）**：`get_db` 改为每请求独立 Session；前端串行化保留为额外防护 |
| 6 | 「契约 mock」页面继续对外可见 | 用户误以为是真实数据 | 本清单作为派单依据；接线前不建议对外演示这些页面 |
| 7 | ~~R4 观察域中 `monitoring_metrics` 的 `tenant_id` **列未被写入**（`record_request` / `record_llm_call` 仅把 `tenant_id` 放进 `dimensions` JSON）~~ | `/monitoring/dashboard`、`/monitoring/costs`、`/monitoring/metrics` 曾按全局指标返回 | **已处置（v1.10.0 / XR-LLM-01）**：鉴权依赖回填 `request.state.user` → 中间件写 `tenant_id`；查询侧 `_apply_tenant_filter` 全量接入；历史数据用 `backfill_monitoring_tenant_v1100.py` 幂等回填（默认 dry-run） |

---

## 8. 附录

### 8.1 证据文件

| 文件 | 内容 |
|------|------|
| `doc/test/evidence/s6/ui-func-audit-v190.json` | 77 页逐页：导航、API 调用面、交互动作、console/page 错误 |
| `doc/test/evidence/s6/ui-func-audit-v190-summary.md` | 由 JSON 生成的汇总表（失败端点聚合、无后端调用页清单） |
| `doc/test/evidence/s6/proxy-reachability-v190.json` | 40 个候选聚合端点的 GET 探测（200/401/405/502） |

### 8.2 复现命令

```powershell
# 1) 起全栈（五服务 + 前端）
& doc\tmp\start-all-services.ps1 -Only infra-redis,infra-qdrant,openllm,openrag,openmemory,openbase,graph-worker,dps -InfraMode local

# 2) 登录并跑逐页「加载 + 交互」审计
$env:OPENBASE_ACCESS_TOKEN = (Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
  -ContentType 'application/json' -Body '{"username":"admin","password":"admin123"}').access_token
$env:OPENBASE_BASE_URL = 'http://127.0.0.1:5173'
node openbase-ui\scripts\ui_e2e_all_services.mjs --interact --out doc\test\evidence\s6\ui-func-audit-v190.json

# 3) 生成汇总
node doc\tmp\audit_summary.mjs doc\test\evidence\s6\ui-func-audit-v190.json doc\test\evidence\s6\ui-func-audit-v190-summary.md

# 4) 聚合端点可达性
& doc\tmp\probe_proxy_reachability.ps1
```

---

## 9. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.16.0 | 2026-10-24 | FA-OpenBase-Dev | **v1.12.0 D 批回填**：C1-d 码值双形态三仓接入（OpenLLM 租户明细 / OpenRAG 注册表 / OpenMemory 域解析），各仓新增单测并回归；RAG/OM 码→UUID 需主数据接入，已登记解冻条件。 |
| v1.15.0 | 2026-10-24 | FA-OpenBase-Dev | **v1.12.0 C 批回填**：DPS 运行态指标端点（`GET /api/v2/metrics`）与 OpenBase 代理三只读路由闭环，画像监控页由「仅健康」→ 指标/限流/告警只读视图（0 mock）。 |
| v1.14.0 | 2026-10-24 | FA-OpenBase-Dev | **v1.12.0 B 批回填**：工作空间成员邀请由「仅 UUID」→「用户名 / UUID 二选一」，对应缺口（成员管理可用性）闭环。 |
| v1.13.0 | 2026-10-23 | FA-OpenBase-Dev | **v1.12.0 A 批回填**：应用调用记录、知识库 API 控制台、报表趋势三页由 mock → 真实并标闭环。 |
| v1.12.0 | 2026-10-23 | FA-OpenBase-Dev | **v1.11.0 长尾裁定回填**：9 个页面能力状态按裁定刷新（建设 6 / 只读建设 3 / 冻结 2 / 不建设 1），与《OpenBase-长尾事项产品裁定-v1.0.0》一致。 |
| v1.11.0 | 2026-10-23 | FA-OpenBase-Dev | **v1.10.2 能力状态回填**：聚合网关测试由「待补交互用例」→ 已覆盖成功/部分失败/超时/重置 4 类。 |
| v1.10.0 | 2026-10-23 | FA-OpenBase-Dev | **v1.10.1 能力状态回填**：个人设置「通知偏好」由未开放 → 真实读写（`GET/PUT /auth/notification-preferences`，含事件开关与 Webhook 校验）；§6 R8 标注 OB-01 已闭环。 |
| v1.9.0 | 2026-10-23 | FA-OpenBase-Dev | **v1.10.0 能力状态回填**：OpenLLM 四页（本地模型/模型对比/开源市场/我的收藏）由 mock → 真实；§7 #7 监控 `tenant_id` 写入与过滤缺口标记已处置（XR-LLM-01）。 |
| v1.8.0 | 2026-10-23 | FA-OpenBase-Dev | **剩余事项统一清查**：新增《剩余事项统一清查与小版本迭代计划-v1.0.0》，登记本仓 6 项、跨仓 12 项、运维/QA 6 项，排入 v1.9.8 / v1.10.0 / v1.10.1 / v1.10.2 / v1.11.0；本清单 §4 起改为只保留能力状态，排期以新计划为唯一来源。 |
| v1.7.0 | 2026-10-23 | FA-OpenBase-Dev | **R7 收口**：新增 `PUT /auth/me`、`POST /auth/change-password` 并扩展 `/auth/me` 资料字段；仪表盘、统一监控、个人设置、模型部署四页接真实端点，画像系统监控收敛为健康页；新增 §6.1 E 类产品裁定（5 页建设 / 6 项不建设或保留）；无后端调用页面 29 → 24。 |
| v1.6.0 | 2026-10-23 | FA-OpenBase-Dev | **R6 收口**：Ollama 轻量探测改短超时（connect 2s/read 5s）；`open-models` 改双通道；收藏/下载任务列表批量化（消除 N+1）；GPU 资源与下载管理两页接真实端点并移除 mock；无后端调用页面 31 → 29。 |
| v1.5.0 | 2026-10-23 | FA-OpenBase-Dev | **R5 收口**：OpenLLM 治理与 RBAC 11 个路由文件改双通道；新增 `GET /roles/permissions/catalog`；角色/工作空间/路由策略/熔断器/工具调用/Prompt 模板/Prompt 实验/A-B 测试七页（8 路由）接真实端点并移除配套假动作；无后端调用页面 39 → 31。 |
| v1.4.0 | 2026-10-23 | FA-OpenBase-Dev | **R4 收口**：OpenLLM `monitoring` / `traces` / `alerts` / `budgets` / `usage` / `billing` / `billing_v2` 共 46 处依赖改双通道；成本/告警/链路/预算/用量/计费六页接真实端点（链路、预算由占位页改为真实页）；移除成本页「一键应用建议」假动作；无后端调用页面 45 → 39；新增 §7 第 7 项登记指标表租户过滤缺口。 |
| v1.3.0 | 2026-10-23 | FA-OpenBase-Dev | **R3 收口**：OpenLLM `plugins` / `model-categories` 改为双通道鉴权；插件管理、模型分类两页接真实端点（列表/工具/启停/注册/健康检查、分类树/分类模型分页）；无后端调用页面 47 → 45。 |
| v1.2.0 | 2026-10-23 | FA-OpenBase-Dev | **R2 收口**：新增 `GET /configs`、`GET /test-records`、`GET /test-runs` 并接线两页；服务 Key 增加 `id` 与 `by-id` 吊销端点（解除历史密钥不可吊销限制）；跨仓修复 OpenLLM `get_db` 并发 500；无后端调用页面 49 → 47。 |
| v1.1.0 | 2026-10-23 | FA-OpenBase-Dev | **R1 收口**：用户管理、API 密钥、EdgeRouter 三页接真实端点并移除假动作；新增「服务 Key 列表无 id、吊销需明文」缺口（归 C 类）与 R2 范围；发现并规避 OpenLLM `scoped_session` 并发 500（前端串行化，根因列 R2 跨仓）；无后端调用页面 52 → 49。 |
| v1.0.0 | 2026-10-22 | FA-OpenBase-Dev | 初始创建：77 页全栈功能审计（L1 加载 / L2 交互 / L3 API 面 / L4 通道探测），52 页无后端调用单列；缺口分 A~E 五类并逐页成表；记录本轮闭环（通用代理来源映射 + OpenLLM 凭据注入 + 提供商管理真实化）与 R1~R7 路线图。 |
