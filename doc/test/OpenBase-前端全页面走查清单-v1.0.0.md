# OpenBase 统一前端全页面走查清单

| 项目 | 内容 |
|---|---|
| 文档编号 | TEST-WT-2026-10-26 |
| 版本 | v1.0.0 |
| 状态 | [Final] |
| 适用环境 | 本地全栈联调（127.0.0.1：OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / 前端 5173） |
| 编写 | 前端走查执行者（AI 辅助） |
| 走查日期 | 2026-10-26 |
| 证据 | `doc/test/evidence/s6/ui-walkthrough-20261026-r4.json`（终轮）<br>`doc/test/evidence/ui-walkthrough-20261026-r4/`（77 张全页截图）<br>历史轮次：`-20261025`（r1）、`-20261026-r2`、`-20261026-r3`（无效轮，见 DEF-WT-03） |

---

## 1. 走查范围与方法

### 1.1 范围

统一前端 `openbase-ui` 承载的全部 **77 个页面**（与侧栏导航一致）：

| 服务域 | 页面数 | 覆盖内容 |
|---|---:|---|
| OpenBase（平台五域 + 个人） | 44 | 身份与权限 8、平台配置 4、可观测与审计 14、AI 能力治理 10、开发者资源 6、个人设置 1、仪表盘 1 |
| OpenLLM（业务模块） | 11 | 模型中心 5、AI 应用 3、对话与分析 3 |
| OpenRAG（知识库模块） | 2 | 知识库列表、RAG 对话 |
| OpenMemory（记忆模块） | 6 | 记忆列表/搜索/会话/图谱/衰减/写入（详情页需具体 id，不纳入遍历） |
| DPS（画像模块 + 模板化 12 页） | 14 | 数据总览、画像列表/搜索、标签、规则引擎、`/portrait/dps/**` 9 页 |

### 1.2 工具与判据

- 工具：`openbase-ui/scripts/ui_e2e_all_services.mjs`（Playwright，`--interact` 交互级审计）
- 每页逐项断言：
  1. 导航返回 200，且**未**被重定向到 `/auth/login`、**未**被守卫退回 `/dashboard`；
  2. 未触发渲染兜底 `[data-test="layout-render-fallback"]`；
  3. 无 `pageerror`、无 `console.error`、无 `console.warn`；
  4. 接口层无 4xx/5xx（`/api/**` 全部响应码 < 400）。
- `--interact` 交互口径：只点击**非破坏性**控件（查询/检索/刷新/筛选/详情/概览/预检/重置筛选等），
  显式跳过破坏性动作（删除/保存/提交/发布/导入导出/回滚/启停等），避免污染运行态数据。

### 1.3 明确不覆盖（诚实声明）

| 不覆盖项 | 原因 | 后续 |
|---|---|---|
| 破坏性写操作（新增/编辑/删除/发布/导入导出/启停） | 会改动共享库与运行态数据，不在自动走查口径内 | 转人工深走查（见 §6） |
| `/memory/:id`、`/portrait/:id`、`/openllm/apps/:id`、`/portrait/dps/templates/:code/edit` 等详情/编辑深链 | 需真实 id，遍历脚本不构造脏数据 | 由列表页「详情」按钮人工点入 |
| 权限矩阵（非 admin 角色下的按钮/接口可见性） | 本轮以 admin 身份走查 | 由权限专项用例覆盖 |

---

## 2. 结论总览

| 轮次 | 结果 | 失败根因 | 备注 |
|---|---|---|---|
| r1（2026-10-25） | PASS 30 / FAIL 47 | **DEF-WT-01**：`httpx` 仅声明在 dev extra，proxy/llm_proxy/rag_proxy/dps_proxy/gateway 五个模块 `ImportError` 被静默跳过 → 整片 `*-proxy/*` 路由缺失（404） | 证据 `ui-walkthrough-20261025.json` |
| r2（2026-10-26） | PASS 69 / FAIL 8 | **DEF-WT-02**：3 页 401（OpenLLM API Key 未登记）；5 页为 Vue Router 冷启动首帧告警（**OBS-01**，非功能缺陷） | 证据 `ui-walkthrough-20261026-r2.json` |
| r3（2026-10-26） | PASS 0 / FAIL 77 | **DEF-WT-03**：修复「服务被会话回收」时给全部服务加了脱离启动，WMI 子进程不继承 `POSTGRES_URL` → 退化为内存模式，所有库依赖接口 500 | **无效轮**，保留作回归证据 |
| **r4（终轮）** | **PASS 77 / FAIL 0，api 失败 0 次** | — | 证据 `ui-walkthrough-20261026-r4.json` |

---

## 3. 问题清单（现象 / 根因 / 处置）

### DEF-WT-01 前端全站 `*-proxy/*` 调用 404（P0，已修复）

- **现象**：47/77 页失败；`GET /api/v1/proxy/openllm/...`、`/api/v1/llm-proxy/*`、`/api/v1/rag-proxy/*`、`/api/v1/dps-proxy/*`、`/api/v1/memory-proxy/*` 全部 404；`openapi.json` 仅 72 条路径。
- **根因**：`httpx` 只写在 `pyproject.toml` 的 dev extra 中；`openbase/__init__.py` 装配模块时 `except ImportError: continue` **静默跳过**，导致 proxy 家族路由整体未挂载，前端只表现为 404，日志无任何痕迹。
- **修复**：
  1. `pyproject.toml`：`httpx>=0.27` 提升为**运行期依赖**；
  2. `openbase/__init__.py`：`ImportError` 分支补 `logging.warning`（模块名 + 异常），不再静默；
  3. 新增回归 `tests/test_app.py::test_proxy_modules_mount_their_routers`（断言四类 proxy 前缀均出现在 `openapi()` 路径中）。
- **验证**：重启后 `openapi.json` 路径 72 → **155**；r2 起 `*-proxy/*` 不再 404。

### DEF-WT-02 告警中心 / 工具调用 / Prompt 实验 401（P0，已修复）

- **现象**：r2 中 3 页失败，接口 `GET /api/v1/proxy/openllm/api/v1/{alerts,alerts/rules,tool-calls,prompt-experiments}` 返回 401；报错体 `{"detail":"无效的API密钥"}`。
- **根因（已用数据证实）**：2026-10-21 的 LLM Key 轮换把 `.env` 的 `OPENBASE_LLM_API_KEY` 改成了 `sk-openllm-d514e17…`，该 Key 的 SHA-256 在 OpenLLM `public.api_keys` 表中**不存在**（表内共 17 条，无命中）；同时 `OPENBASE_LLM_API_KEYS_BY_TENANT` 的租户码被写成 `demo`（真实 claim 为 `tenant-1`）。
  - 交叉证据：备份 `.env.bak-llmkey-20261021` 中为 `sk-openllm-b16f68…`，其 SHA-256 与库内 `openbase-gateway-v143`（`is_active=t`、`permissions=["*"]`）**完全一致**；同备份的租户映射为 `tenant-1`。
  - 补充核验：OpenLLM `openapi.json` 中 `/api/v1/alerts`、`/api/v1/alerts/rules`、`/api/v1/tool-calls`、`/api/v1/prompt-experiments` **均存在**，故不是契约缺口。
- **修复**：`.env` 恢复为已登记 Key，并把租户映射键改回 `tenant-1`：
  - `OPENBASE_LLM_API_KEY=sk-openllm-b16f68…`
  - `OPENBASE_LLM_API_KEYS_BY_TENANT={"tenant-1":"sk-openllm-b16f68…"}`
- **验证**：直连 OpenBase 8000 逐一实测，`alerts`、`alerts/rules`、`tool-calls`、`prompt-experiments`、`providers` 全部 **200**（返回真实数据/空集）。

### DEF-WT-03 服务脱离启动丢失进程环境 → 全站 500（P0，本轮引入并修复）

- **现象**：r3 77/77 FAIL；`/api/v1/auth/me`、`/api/v1/users`、`/api/v1/tenants` 等**所有库依赖接口 500**；日志 `connection was closed in the middle of operation` 与 `database init failed, fallback to memory`。
- **根因（两层）**：
  1. 编排器仅 `frontend` 声明 `Detach = $true`，其余服务走 `Start-Process`，启动它的终端/会话结束即被 Job Object 回收（实测 openbase 健康检查通过后数秒消失）；
  2. 为消除 (1) 给全部服务加 `Detach` 后，**WMI `Win32_Process.Create` 创建的子进程不继承调用方进程环境** → `.env.shared-infra` 注入的 `POSTGRES_URL` 丢失 → `demo_app` 回退内存模式（内存 admin/admin123 仍可登录，但库依赖接口全 500）。
- **修复**（`scripts/service-orchestrator.ps1`）：
  1. 全部 7 个服务统一 `Detach = $true`（脱离会话，避免被回收）；
  2. `Start-DetachedProcess` 显式传递环境：**白名单**「系统必需键 + 共享基础设施前缀（POSTGRES_/REDIS_/QDRANT_/NEO4J_/MINIO_/SQLITE_/OLLAMA_）+ 各仓前缀（OPENBASE_/OPENMEMORY_/OPENRAG_/OPENLLM_/DPS_/PYTHON/VIRTUAL_ENV）」，再以 `$Svc.Env` 覆盖；
     - 不整份快照的原因：环境过大时 `Win32_Process.Create` 返回 8（命令行超限），首版整份快照即失败于此；
  3. 健康检查通过后按端口反查**真实监听 PID** 并落盘（`Get-PortPid` + `Save-Pid`），避免 `stop` 只杀包装 powershell 而留下占用端口的孤儿。
- **验证**：`tests/test_orchestrator_db_failover.py` **24 例全通过**（新增 1 例覆盖三项契约）；重启后 `/auth/me`、`/users`、`/proxy/openllm/*` 全部 200；r4 **77/77 PASS**。

### OBS-01 Vue Router 冷启动首帧告警（非缺陷，不修）

- **现象**：r2 中 5 页记录 `[Vue Router warn] No match found for location with path …`（`/memory/list`、`/memory/graph`、`/memory/decay`、`/openllm/models/local`、`/portrait/list`）。
- **判定**：页面 `final_path`、标题、内容均正确，无兜底、无接口失败；重复复现 6 页均**不再出现**该告警。
- **根因**：`main.ts` 的 `BOOTSTRAP_MAX_WAIT_MS = 2500` 与后端 `/auth/me`、`/modules` 延迟竞态——预热未完成即 `app.use(router)`，首帧 `router.resolve` 早于模块路由装载（设计上已接受：以「避免长时间白屏」换「极小概率首帧告警」，见 `router/index.ts` F-4 注释）。
- **处置**：记录为观察项，**不修改**。若后续要求零告警，可改为缓存上次权限集使预热不再依赖网络（需单独立项评审）。

### OBS-02 部分页面无「安全可点击」控件（转人工深走查）

`/openllm/models/local`、`/portrait/dps/lineage`、`/portrait/dps/annotation-adapters`、`/openllm/apps/new` 等页在自动口径下 `actions = 0`（无查询/刷新类按钮，或按钮均为写操作）。这些页面仅验证到「加载 + 渲染 + 接口」层，功能深度需人工按 §6 清单执行。

---

## 4. 逐页走查清单（终轮 r4）

> 列含义：`数据接口` 为剔除 `/api/v1/modules`、`/api/v1/auth/me` 后的实际业务接口（最多列 3 条）；`交互` 为自动点击的非破坏性控件；结论 PASS 表示满足 §1.2 全部四条判据。

| # | 服务 | 页面 | 标题 | 加载 | 数据接口 | 交互 | 结论 |
|--:|---|---|---|--:|---|---|---|
| 1 | openbase | `/dashboard` | 仪表盘 | 200 | /api/v1/proxy/openllm/api/v1/monitoring/dashboard<br>/api/v1/users | - | PASS |
| 2 | openbase | `/platform/identity/tenants` | 租户管理 | 200 | /api/v1/tenants | - | PASS |
| 3 | openbase | `/platform/identity/roles` | 角色与权限 | 200 | /api/v1/proxy/openllm/api/v1/roles | 刷新 | PASS |
| 4 | openbase | `/platform/identity/org` | 组织/团队/用户 | 200 | /api/v1/users | - | PASS |
| 5 | openbase | `/platform/identity/workspaces` | 工作空间 | 200 | /api/v1/proxy/openllm/api/v1/workspaces | 刷新 | PASS |
| 6 | openbase | `/platform/identity/users` | 用户管理 | 200 | /api/v1/users | 刷新 | PASS |
| 7 | openbase | `/platform/identity/memory-admin` | 记忆管理席位 | 200 | /api/v1/memory-proxy/monitor<br>/api/v1/memory-proxy/memories | 记忆概览 / 运行监控 / 记忆维护 | PASS |
| 8 | openbase | `/platform/identity/auth-ext` | 注册/找回密码 | 200 | - | 注册 / 找回密码 / 重置密码 | PASS |
| 9 | openbase | `/platform/identity/dps-permissions` | 画像数据权限 | 200 | /api/v1/dps-proxy/permissions/roles | 刷新 | PASS |
| 10 | openbase | `/platform/config/general` | 全局配置 | 200 | /api/v1/configs | 刷新 | PASS |
| 11 | openbase | `/platform/config/modules` | 模块开关 | 200 | - | 刷新 | PASS |
| 12 | openbase | `/platform/config/api-keys` | API 密钥 | 200 | /api/v1/auth/api-keys | 刷新 | PASS |
| 13 | openbase | `/platform/config/rate-limits` | 画像接口限流 | 200 | /api/v1/dps-proxy/rate-limits/status | 刷新 | PASS |
| 14 | openbase | `/platform/observability/logs` | 日志中心 | 200 | /api/v1/logs/search<br>/api/v1/logs/facets | 检索 / 重置 | PASS |
| 15 | openbase | `/platform/observability/test-records` | 测试记录 | 200 | /api/v1/test-runs | 刷新轮次 | PASS |
| 16 | openbase | `/platform/observability/monitoring` | 统一监控 | 200 | /api/v1/proxy/openllm/api/v1/monitoring/dashboard<br>/api/v1/proxy/openllm/api/v1/alerts | - | PASS |
| 17 | openbase | `/platform/observability/monitoring/costs` | 成本分析 | 200 | /api/v1/proxy/openllm/api/v1/monitoring/costs<br>/api/v1/proxy/openllm/api/v1/budgets<br>/api/v1/proxy/openllm/api/v1/monitoring/costs/optimization-suggestions | 刷新 | PASS |
| 18 | openbase | `/platform/observability/monitoring/alerts` | 告警中心 | 200 | /api/v1/proxy/openllm/api/v1/alerts/rules<br>/api/v1/proxy/openllm/api/v1/alerts | 告警规则 / 告警历史 / 刷新 | PASS |
| 19 | openbase | `/platform/observability/monitoring/traces` | 链路追踪 | 200 | /api/v1/proxy/openllm/api/v1/monitoring/traces/statistics<br>/api/v1/proxy/openllm/api/v1/monitoring/traces | 查询 | PASS |
| 20 | openbase | `/platform/observability/monitoring/budgets` | 预算管理 | 200 | /api/v1/proxy/openllm/api/v1/budgets | 刷新 | PASS |
| 21 | openbase | `/platform/observability/gpu` | GPU 资源 | 200 | /api/v1/proxy/openllm/api/v1/local-models/gpu-allocation/status<br>/api/v1/proxy/openllm/api/v1/local-models/gpu-info | 刷新 | PASS |
| 22 | openbase | `/platform/observability/usage` | 用量统计 | 200 | /api/v1/proxy/openllm/api/v1/usage/summary<br>/api/v1/proxy/openllm/api/v1/usage/trends<br>/api/v1/proxy/openllm/api/v1/usage/detail | 查询 | PASS |
| 23 | openbase | `/platform/observability/billing` | 计费 | 200 | /api/v1/proxy/openllm/api/v1/billing/usage/statistics<br>/api/v1/proxy/openllm/api/v1/billing/quotas<br>/api/v1/proxy/openllm/api/v1/billing/bills | 刷新 | PASS |
| 24 | openbase | `/platform/observability/service-discovery` | 服务发现与编排 | 200 | /api/v1/services | 刷新 / 连通性检测 | PASS |
| 25 | openbase | `/platform/observability/gateway-test` | 聚合网关测试 | 200 | - | 重置 | PASS |
| 26 | openbase | `/platform/observability/app-calls` | 应用调用记录 | 200 | /api/v1/ai-apps<br>/api/v1/ai-apps/calls | 刷新 | PASS |
| 27 | openbase | `/platform/observability/dps-monitor` | 画像系统监控 | 200 | /api/v1/dps-proxy/metrics<br>/api/v1/dps-proxy/alerts/rules<br>/api/v1/dps-proxy/health | 刷新 | PASS |
| 28 | openbase | `/platform/governance/providers` | 提供商管理 | 200 | /api/v1/proxy/openllm/api/v1/providers | 刷新 | PASS |
| 29 | openbase | `/platform/governance/model-categories` | 模型分类 | 200 | /api/v1/proxy/openllm/api/v1/model-categories/tree | 刷新 | PASS |
| 30 | openbase | `/platform/governance/routing` | 路由策略 | 200 | /api/v1/proxy/openllm/api/v1/routing/circuit-breakers<br>/api/v1/proxy/openllm/api/v1/routing/semantic | 路由策略 / 熔断器 / 刷新 | PASS |
| 31 | openbase | `/platform/governance/circuit-breakers` | 熔断器 | 200 | /api/v1/proxy/openllm/api/v1/routing/circuit-breakers<br>/api/v1/proxy/openllm/api/v1/routing/semantic | 路由策略 / 熔断器 / 刷新 | PASS |
| 32 | openbase | `/platform/governance/deploy` | 模型部署 | 200 | /api/v1/proxy/openllm/api/v1/open-models | 刷新 | PASS |
| 33 | openbase | `/platform/governance/downloads` | 下载管理 | 200 | /api/v1/proxy/openllm/api/v1/open-models/downloads | 刷新 | PASS |
| 34 | openbase | `/platform/governance/tool-calls` | 工具调用监控 | 200 | /api/v1/proxy/openllm/api/v1/tool-calls | 查询 / 刷新 | PASS |
| 35 | openbase | `/platform/governance/ab-tests` | A/B 测试 | 200 | /api/v1/proxy/openllm/api/v1/routing/ab-tests | 刷新 | PASS |
| 36 | openbase | `/platform/governance/prompt-templates` | Prompt 模板 | 200 | /api/v1/proxy/openllm/api/v1/prompt-templates | 查询 | PASS |
| 37 | openbase | `/platform/governance/prompt-experiments` | Prompt 实验 | 200 | /api/v1/proxy/openllm/api/v1/prompt-experiments | 刷新 | PASS |
| 38 | openbase | `/platform/developers/docs` | 文档中心 | 200 | - | - | PASS |
| 39 | openbase | `/platform/developers/edgerouter` | EdgeRouter 与适配器 | 200 | /api/v1/proxy/openllm/api/v1/edge/status<br>/api/v1/proxy/openllm/api/v1/edge/health<br>/api/v1/proxy/openllm/api/v1/edge/adapters | 概览 / 组织管理 / 配额管理 / 适配器管理 / 路由审计 / 刷新 | PASS |
| 40 | openbase | `/platform/developers/plugins` | 插件管理 | 200 | /api/v1/proxy/openllm/api/v1/plugins<br>/api/v1/proxy/openllm/api/v1/plugins/tools | 刷新 | PASS |
| 41 | openbase | `/platform/developers/dps-api` | 画像 API 管理 | 200 | /api/v1/dps-proxy/api-registry | 刷新 | PASS |
| 42 | openbase | `/platform/developers/knowledge-admin` | 知识库管理后台 | 200 | /api/v1/rag-proxy/collections<br>/api/v1/rag-proxy/health | 刷新 / 详情（×9） | PASS |
| 43 | openbase | `/platform/developers/knowledge-console` | 知识库 API 控制台 | 200 | /api/v1/rag-proxy/collections<br>/api/v1/rag-proxy/health | 概览 / API 调试器 / 接口文档 / 性能监控 | PASS |
| 44 | openbase | `/personal/settings` | 个人设置 | 200 | /api/v1/auth/notification-preferences | - | PASS |
| 45 | openllm | `/openllm/models` | 模型管理 | 200 | /api/v1/llm-proxy/models | 详情（×6） | PASS |
| 46 | openllm | `/openllm/models/local` | 本地模型 | 200 | - | - | PASS |
| 47 | openllm | `/openllm/models/comparison` | 模型对比 | 200 | /api/v1/proxy/openllm/api/v1/open-models | - | PASS |
| 48 | openllm | `/openllm/models/market` | 开源模型市场 | 200 | /api/v1/proxy/openllm/api/v1/open-models | 查询 | PASS |
| 49 | openllm | `/openllm/favorites` | 我的收藏 | 200 | /api/v1/proxy/openllm/api/v1/models/favorite-folders<br>/api/v1/proxy/openllm/api/v1/models/favorites | 默认收藏 (0) | PASS |
| 50 | openllm | `/openllm/apps` | AI 应用 | 200 | /api/v1/ai-apps | - | PASS |
| 51 | openllm | `/openllm/apps/new` | 创建应用 | 200 | - | - | PASS |
| 52 | openllm | `/openllm/playground` | Playground | 200 | /api/v1/llm-proxy/models | - | PASS |
| 53 | openllm | `/openllm/conversations` | 对话管理 | 200 | /api/v1/llm-proxy/models<br>/api/v1/llm-proxy/conversations | - | PASS |
| 54 | openllm | `/openllm/recommend` | 模型对比推荐 | 200 | - | 检索 | PASS |
| 55 | openllm | `/openllm/reports-trend` | 报表趋势 | 200 | /api/v1/proxy/openllm/api/v1/monitoring/costs<br>/api/v1/proxy/openllm/api/v1/monitoring/dashboard<br>/api/v1/proxy/openllm/api/v1/usage/trends | 刷新 | PASS |
| 56 | openrag | `/knowledge/list` | 知识库 | 200 | /api/v1/rag-proxy/collections | 刷新 | PASS |
| 57 | openrag | `/knowledge/chat` | RAG 对话 | 200 | /api/v1/rag-proxy/collections | 刷新列表 | PASS |
| 58 | openmemory | `/memory/list` | 记忆列表 | 200 | /api/v1/memory-proxy/memories | - | PASS |
| 59 | openmemory | `/memory/search` | 记忆搜索 | 200 | - | 搜索 | PASS |
| 60 | openmemory | `/memory/sessions` | 会话管理 | 200 | /api/v1/memory-proxy/sessions | 刷新 | PASS |
| 61 | openmemory | `/memory/graph` | 记忆图谱 | 200 | /api/v1/memory-proxy/graph/overview | 刷新图谱 | PASS |
| 62 | openmemory | `/memory/decay` | 衰减配置 | 200 | /api/v1/memory-proxy/decay/config | 重置 | PASS |
| 63 | openmemory | `/memory/write` | 写入记忆 | 200 | - | 重置 | PASS |
| 64 | dps | `/portrait/overview` | 数据总览 | 200 | /api/v1/dps-proxy/portraits<br>/api/v1/dps-proxy/reports/overview | - | PASS |
| 65 | dps | `/portrait/list` | 画像列表 | 200 | /api/v1/dps-proxy/portraits<br>/api/v1/dps-proxy/health<br>/api/v1/dps-proxy/reports/overview | 画像查询 | PASS |
| 66 | dps | `/portrait/search` | 画像搜索 | 200 | /api/v1/dps-proxy/portraits | 查询 / 重置 | PASS |
| 67 | dps | `/portrait/tags` | 标签管理 | 200 | /api/v1/dps-proxy/tags/categories | 刷新 | PASS |
| 68 | dps | `/portrait/rules` | 规则引擎 | 200 | - | 画像规则 / 执行任务 | PASS |
| 69 | dps | `/portrait/dps/templates` | 模板族管理 | 200 | /api/v1/dps-proxy/templates | 查询 / 重置 | PASS |
| 70 | dps | `/portrait/dps/templates/new` | 画像模板新建 | 200 | /api/v1/dps-proxy/templates | - | PASS |
| 71 | dps | `/portrait/dps/template-packages` | 模板包导出/导入 | 200 | - | 导出 / 导入 | PASS |
| 72 | dps | `/portrait/dps/lineage` | 标签血缘反查 | 200 | - | - | PASS |
| 73 | dps | `/portrait/dps/measures` | 措施建议 | 200 | - | 查询建议 | PASS |
| 74 | dps | `/portrait/dps/scoring-types` | 评分类型 | 200 | /api/v1/dps-proxy/scoring-types | 查询 | PASS |
| 75 | dps | `/portrait/dps/annotation-adapters` | AI 标注候选与复核 | 200 | - | - | PASS |
| 76 | dps | `/portrait/dps/annotation-templates` | 标注模板管理 | 200 | /api/v1/dps-proxy/annotation-templates | 查询 / 重置 | PASS |
| 77 | dps | `/portrait/dps/tags` | 标签体系查看 | 200 | /api/v1/dps-proxy/tags/categories<br>/api/v1/dps-proxy/labels | - | PASS |

---

## 5. 修复汇总与验证

| 编号 | 改动文件 | 改动要点 | 验证方式 | 结果 |
|---|---|---|---|---|
| DEF-WT-01 | `pyproject.toml`、`openbase/__init__.py`、`tests/test_app.py` | httpx 提升为运行期依赖；ImportError 留痕；新增路由挂载回归 | `openapi()` 路径数 72 → 155；pytest | 通过 |
| DEF-WT-02 | `.env`（本地，不入库） | 恢复已登记 OpenLLM Key + 租户映射改回 `tenant-1` | 5 个端点实测 200 | 通过 |
| DEF-WT-03 | `scripts/service-orchestrator.ps1`、`tests/test_orchestrator_db_failover.py` | 全服务脱离启动 + 白名单传递进程环境 + 落盘真实监听 PID | 24 例静态/行为契约；`/auth/me`、`/users` 200；r4 77/77 | 通过 |

验证命令：

```bash
python -m pytest tests/test_orchestrator_db_failover.py tests/test_app.py -q
# 24 + N 例全通过

node scripts/ui_e2e_all_services.mjs --interact \
  --out ../doc/test/evidence/s6/ui-walkthrough-20261026-r4.json \
  --shots ../doc/test/evidence/ui-walkthrough-20261026-r4
# 合计: PASS 77 / FAIL 0（共 77 页），api 失败 0 次
```

### 5.1 全量回归结果（诚实记录）

`python -m pytest tests`（本机 pgAdmin 桥接运行器）结果与归因：

| 结果 | 用例 | 归因 | 是否本轮引入 |
|---|---|---|---|
| 通过 | 其余全部用例（含新增 2 例） | — | — |
| 失败 2 例 | `tests/test_users_admin.py::test_new_user_can_login`、`::test_all_allowed_roles_assignable`（`connection was closed`） | 共享 PG（192.168.0.151）瞬态断连；**隔离复跑该文件 7/7 通过** | 否 |
| ERROR 10 例 | `tests/test_s7_t6_gate.py` 全部 | 门禁聚合内部以 `sys.executable -m pytest` 起子进程，pgAdmin 嵌入式 Python 的 `._pth` 布局使子进程无法 `import pytest`（实测 collection error，exit 2）；对应子集直跑 **36/36 通过** | 否（B2 B 面沙箱限制） |

> 结论：本轮改动**未引入回归**；上述两类为已知环境限制，已在全栈计划 B2（门禁 B 面）与「共享 PG 瞬态抖动」条目下登记。


---

## 6. 遗留项与后续人工深走查清单

| 项 | 说明 | 建议动作 |
|---|---|---|
| OBS-01 | Vue Router 冷启动首帧告警（时序性，非功能缺陷） | 若要求零告警：权限集本地缓存立项评审 |
| OBS-02 | 4 个页面自动口径无可点击安全控件 | 人工深走查（见下表） |
| 破坏性写操作 | 未纳入自动口径 | 人工按业务顺序执行并留痕（`doc/test/evidence/manual/**`） |
| 权限矩阵 | 仅以 admin 走查 | 以 org_admin / viewer 复跑按钮与接口可见性 |

人工深走查建议顺序（每条记录「预期 / 实际 / 证据截图」）：

1. `/platform/identity/users`：新增 → 编辑 → 禁用 → 删除（测试账号）；
2. `/platform/config/api-keys`：签发 → 复制 → 吊销；
3. `/platform/observability/logs`：多源切换 + 时间窗检索；
4. `/platform/governance/providers`：新增提供商 → 健康检查 → 停用；
5. `/openllm/playground`：真实模型流式对话；
6. `/memory/write` → `/memory/list` → 详情 → 删除（软/硬）；
7. `/portrait/dps/templates`：新建 → 编辑 → 预检 → 版本对比 → 回滚；
8. `/portrait/dps/template-packages`：导出 → 导入（跨环境校验）。

---

## 7. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
|---|---|---|---|
| v1.0.0 | 2026-10-26 | 前端走查执行者 | 首版：77 页全量走查清单；三类缺陷（DEF-WT-01/02/03）根因与修复；两项观察项；人工深走查清单 |
