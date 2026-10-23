# OpenBase 全栈后端能力缺口清单 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）统一前端 |
| 文档版本 | v1.2.0 |
| 状态 | **[Review]** |
| 适用范围 | 统一前端 `openbase-ui`（OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS 五服务页面） |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-10-22 |
| 上游依据 | 《OpenBase-前端架构设计文档-v1.4.11》v1.14.0 §8.12；《OpenBase-DevLogReport-v1.4.11》v2.5.0 §2.14 |
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
| 无后端调用的页面 | **47**（R1 收口 3 页、R2 收口 2 页后：52 − 5） |
| 其中「无调用且无可交互动作」的静默页 | 28 |

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

### 4.1 OpenBase 公共域（44 页）

| # | 页面 | 路由 | 现状 | 类别 | 目标/缺口接口 | 状态 |
|:-:|------|------|------|:----:|----------------|------|
| 1 | 仪表盘 | `/dashboard` | 静态 KPI 卡 | E | 无聚合总览端点 | 待立项 |
| 2 | 租户管理 | `/platform/identity/tenants` | 真实 | — | `/tenants` | 已接 |
| 3 | 角色与权限 | `/platform/identity/roles` | mock | B | OpenLLM `/roles`（401） | 后续轮次 |
| 4 | 组织/团队/用户 | `/platform/identity/org` | 真实 | — | `/users`、`/org/departments` | 已接 |
| 5 | 工作空间 | `/platform/identity/workspaces` | mock | B | OpenLLM `/workspaces`（401） | 后续轮次 |
| 6 | 用户管理 | `/platform/identity/users` | **真实（v1.9.1 R1）** | — | `/users` | **已闭环** |
| 7 | 记忆管理席位 | `/platform/identity/memory-admin` | 真实 | — | `/memory-proxy/monitor`、`/memories` | 已接 |
| 8 | 注册/找回密码 | `/platform/identity/auth-ext` | mock | E | 无 `/auth/register`、无找回密码 | 待立项 |
| 9 | 画像数据权限 | `/platform/identity/dps-permissions` | mock | E | 无对应端点 | 待立项 |
| 10 | 全局配置 | `/platform/config/general` | **真实（v1.9.2 R2）** | — | `GET /configs`（新增）、`POST /configs`、`GET /configs/{key}/versions`、`POST /configs/{key}/rollback` | **已闭环** |
| 11 | 模块开关 | `/platform/config/modules` | 真实 | — | `/modules` | 已接 |
| 12 | API 密钥 | `/platform/config/api-keys` | **真实（v1.9.2 R2）** | — | `/auth/api-keys`；新增 `id` 回显与 `DELETE /auth/api-keys/by-id/{id}` | **已闭环（含 id 化吊销）** |
| 13 | 画像接口限流 | `/platform/config/rate-limits` | mock | E | 无对应端点 | 待立项 |
| 14 | 日志中心 | `/platform/observability/logs` | 真实 | — | `/logs/search`、`/logs/facets` | 已接 |
| 15 | 测试记录 | `/platform/observability/test-records` | **真实（v1.9.2 R2）** | — | `GET /test-records`、`GET /test-runs`（新增）+ 既有开轮/记录/改判/summary | **已闭环** |
| 16 | 统一监控 | `/platform/observability/monitoring` | mock 概览 | E | 无聚合概览端点 | 待立项 |
| 17 | 成本分析 | `/platform/observability/monitoring/costs` | mock | B | OpenLLM `/monitoring/costs`（401） | 后续轮次 |
| 18 | 告警中心 | `/platform/observability/monitoring/alerts` | mock | B | `/alerts`、`/alerts/rules`（401） | 后续轮次 |
| 19 | 链路追踪 | `/platform/observability/monitoring/traces` | mock | B | `/monitoring/traces`（401） | 后续轮次 |
| 20 | 预算管理 | `/platform/observability/monitoring/budgets` | mock | B | `/budgets`（401） | 后续轮次 |
| 21 | GPU 资源 | `/platform/observability/gpu` | mock | D | `/local-models/gpu`（502 超时） | 待性能治理 |
| 22 | 用量统计 | `/platform/observability/usage` | mock | B | `/usage/summary`（401） | 后续轮次 |
| 23 | 计费 | `/platform/observability/billing` | mock | B | `/billing/bills`（401） | 后续轮次 |
| 24 | 服务发现与编排 | `/platform/observability/service-discovery` | 真实 | — | `/services`、`/gateway/ping` | 已接 |
| 25 | 聚合网关测试 | `/platform/observability/gateway-test` | 表单页（提交时触发） | A | `/gateway/aggregate`（200；审计未自动提交） | 待补充交互用例 |
| 26 | 应用调用记录 | `/platform/observability/app-calls` | mock | E | `/ai-apps/{id}/calls` 需先选应用，缺全局聚合 | 待立项 |
| 27 | 画像系统监控 | `/platform/observability/dps-monitor` | mock | E | 无对应端点 | 待立项 |
| 28 | 提供商管理 | `/platform/governance/providers` | **真实（本轮）** | — | `/proxy/openllm/api/v1/providers` | **已闭环** |
| 29 | 模型分类 | `/platform/governance/model-categories` | mock | B | `/model-categories`（401） | 后续轮次 |
| 30 | 路由策略 | `/platform/governance/routing` | mock | B | `/routing/*`（401） | 后续轮次 |
| 31 | 熔断器 | `/platform/governance/circuit-breakers` | mock | B | `/routing/circuit-breakers`（401） | 后续轮次 |
| 32 | 模型部署 | `/platform/governance/deploy` | mock | B/D | `/open-models/*`（401；部分 502） | 后续轮次 |
| 33 | 下载管理 | `/platform/governance/downloads` | mock | B | `/open-models/downloads`（401） | 后续轮次 |
| 34 | 工具调用监控 | `/platform/governance/tool-calls` | mock | B | `/tool-calls`（401） | 后续轮次 |
| 35 | A/B 测试 | `/platform/governance/ab-tests` | mock | B | `/routing/ab-tests`（401） | 后续轮次 |
| 36 | Prompt 模板 | `/platform/governance/prompt-templates` | mock | B | `/prompt-templates`（401） | 后续轮次 |
| 37 | Prompt 实验 | `/platform/governance/prompt-experiments` | mock | B | `/prompt-experiments`（401） | 后续轮次 |
| 38 | 文档中心 | `/platform/developers/docs` | 静态文档 | E | 无端点（内容型页面，可保留） | 保留 |
| 39 | EdgeRouter 与适配器 | `/platform/developers/edgerouter` | **真实（v1.9.1 R1）** | — | `/edge/status`、`/edge/health`、`/edge/adapters`、`/edge/organizations`、`/edge/quotas/{org}`、`/edge/audit/logs`（均 200） | **已闭环** |
| 40 | 插件管理 | `/platform/developers/plugins` | mock | B | `/plugins`、`/plugins/tools`（401） | 后续轮次 |
| 41 | 画像 API 管理 | `/platform/developers/dps-api` | mock | E | 无对应端点 | 待立项 |
| 42 | 知识库管理后台 | `/platform/developers/knowledge-admin` | 真实 | — | `/rag-proxy/collections` | 已接 |
| 43 | 知识库 API 控制台 | `/platform/developers/knowledge-console` | 静态控制台 | E | 调试器为本地演示，未打通真实调用 | 待立项 |
| 44 | 个人设置 | `/personal/settings` | mock | E | 无用户资料更新端点（仅 `/auth/me`） | 待立项 |

### 4.2 OpenLLM（11 页）

| # | 页面 | 路由 | 现状 | 类别 | 说明 |
|:-:|------|------|------|:----:|------|
| 1 | 模型管理 | `/openllm/models` | 真实 | — | `/llm-proxy/models` |
| 2 | 本地模型 | `/openllm/models/local` | mock | D | `/local-models` 502（超时，上游耗时 > 10s） |
| 3 | 模型对比 | `/openllm/models/comparison` | mock | D | `/models/compare` 502 |
| 4 | 开源模型市场 | `/openllm/models/market` | mock | D | `/open-models/popular` 502 |
| 5 | 我的收藏 | `/openllm/favorites` | mock | D | `/models/favorites` 502 |
| 6 | AI 应用 | `/openllm/apps` | 真实 | — | `/ai-apps` |
| 7 | 创建应用 | `/openllm/apps/new` | 真实（提交时） | — | `POST /ai-apps` |
| 8 | Playground | `/openllm/playground` | 真实 | — | `/llm-proxy/models`、`/llm-proxy/chat` |
| 9 | 对话管理 | `/openllm/conversations` | 真实 | — | `/llm-proxy/conversations` |
| 10 | 模型对比推荐 | `/openllm/recommend` | mock | E | 无推荐端点 |
| 11 | 报表趋势 | `/openllm/reports-trend` | mock | E | 无报表端点 |

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
| 5 | 规则引擎 | `/portrait/rules` | mock | E |
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

---

## 6. 后续轮次路线图（建议）

| 轮次 | 主题 | 范围 | 关键依赖 |
|:----:|------|------|----------|
| R1 | A 类收口（低成本） | 用户管理、API 密钥、EdgeRouter 三页接真实端点 | **已完成（v1.9.1）** |
| R2 | C 类补列表 | `GET /configs`、`GET /test-records`、`GET /test-runs` + 两页接线；服务 Key 改 id 化吊销 | **已完成（v1.9.2）**；同时修复 OpenLLM `get_db` 并发缺陷 |
| R3 | B 类第一批 | OpenLLM `plugins`、`model-categories` 改双通道依赖；插件管理、模型分类两页接真实 | OpenLLM 授权依赖改造 |
| R4 | B 类第二批 | `monitoring/*`、`alerts`、`budgets`、`usage`、`billing` → 成本/告警/链路/预算/用量/计费六页 | 观察类接口的租户过滤口径 |
| R5 | B 类第三批 | `routing/*`、`prompt-*`、`tool-calls`、`roles`、`workspaces` → 治理与 RBAC 页 | 写权限档位与 `role:write` 语义 |
| R6 | D 类性能 | `local-models`、`models/favorites|compare`、`open-models/popular` 的 10s 超时治理 | 上游耗时剖析 |
| R7 | E 类立项 | 仪表盘/统一监控/画像系统监控/个人设置等纯形态页 | 产品裁定是否建设 |

> 纪律：每轮完成「后端 + 前端 + 单测 + 浏览器实测 + 文档留痕 + 三远程推送」闭环，不跨轮混提交。

---

## 7. 风险与假设

| # | 风险/假设 | 影响 | 缓解 |
|:-:|-----------|------|------|
| 1 | OpenLLM 原生 `/api/v1/*` 的 API Key 通道返回的是 **Key 所属用户**身份，不是终端用户 | 审计/权限粒度以服务账号为准，非真实操作者 | 身份头（`X-User-*`）已透传，供下游审计；如需终端级权限，改走 `/openllm/v1/*` 网关 |
| 2 | 通用代理注入 OpenLLM Key 属新增出站凭据面 | 若代理权限判定失效，可能放大影响 | 代理入口仍强制 JWT + 权限校验；Key 仅对 `system=openllm` 注入 |
| 3 | 上游 `local-models` 等端点 10s 超时 | 页面 502 | 与 D 类一并治理；必要时该组端点单独放宽超时 |
| 4 | 服务进程（DPS/OpenRAG）在长时间无人访问后被回收 | 审计出现 503 假失败 | 审计前统一健康检查；服务编排侧增加守护（运维项） |
| 5 | ~~**OpenLLM `scoped_session` + 线程池并发缺陷**~~ | 同步端点并发访问同一 Session → `InvalidRequestError` → 上游 500 | **已修复（R2 / OpenLLM v1.9.2）**：`get_db` 改为每请求独立 Session；前端串行化保留为额外防护 |
| 6 | 「契约 mock」页面继续对外可见 | 用户误以为是真实数据 | 本清单作为派单依据；接线前不建议对外演示这些页面 |

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
| v1.2.0 | 2026-10-23 | FA-OpenBase-Dev | **R2 收口**：新增 `GET /configs`、`GET /test-records`、`GET /test-runs` 并接线两页；服务 Key 增加 `id` 与 `by-id` 吊销端点（解除历史密钥不可吊销限制）；跨仓修复 OpenLLM `get_db` 并发 500；无后端调用页面 49 → 47。 |
| v1.1.0 | 2026-10-23 | FA-OpenBase-Dev | **R1 收口**：用户管理、API 密钥、EdgeRouter 三页接真实端点并移除假动作；新增「服务 Key 列表无 id、吊销需明文」缺口（归 C 类）与 R2 范围；发现并规避 OpenLLM `scoped_session` 并发 500（前端串行化，根因列 R2 跨仓）；无后端调用页面 52 → 49。 |
| v1.0.0 | 2026-10-22 | FA-OpenBase-Dev | 初始创建：77 页全栈功能审计（L1 加载 / L2 交互 / L3 API 面 / L4 通道探测），52 页无后端调用单列；缺口分 A~E 五类并逐页成表；记录本轮闭环（通用代理来源映射 + OpenLLM 凭据注入 + 提供商管理真实化）与 R1~R7 路线图。 |
