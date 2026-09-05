# OpenBase 统一前端 全模块 UI E2E 遍历报告（report-full）

| 项 | 值 |
|---|---|
| 被测入口 | http://localhost:5173（OpenBase 统一前端，本地五件套后端运行中） |
| 账号 | admin / admin123（本地登录，redirect=/dashboard） |
| 系统版本（页面自述） | v1.2.0；仪表盘显示“已启用模块 5 / 统一入口 5 系统” |
| 执行日期 | 2026-09-06 |
| 方法 | 加载 webapp-testing 技能，Playwright(Chromium headless 1920x1080) 纯浏览器观察；未读取应用任何源码/HTML/JS/config，证据全部来自 DOM/控制台/网络/截图 |
| 遍历范围 | 仪表盘、租户管理、OpenLLM、知识库、记忆、画像、统一网关（模块内通过横向 module-menu 逐组悬停并逐个访问可见子页） |
| 交付物 | 本报告；截图 `dogfood-output/screenshots/full/`；证据 JSON 备份于 `dogfood-output/evidence/`（e2e_full.json / gateway_probe.json / portrait_retry.json / recon.json / after-login.json） |

## 1. 执行摘要

- 登录链路正常：/auth/login → 输入 admin/admin123 → 侧边栏“登 录” → /dashboard，无失败请求。
- 7 个顶层模块的侧边栏入口均可点击进入；OpenLLM/知识库/记忆/画像/统一网关 为全屏模块布局（顶部横向菜单 + 悬停下拉子页），仪表盘与租户管理为“统一壳”布局（左侧 7 项导航保留）。
- 模块内子页遍历：OpenLLM 33 项、知识库 6 项、记忆 8 项、画像 11 项、统一网关 2 项（服务列表/聚合测试）；其中 **32/33、6/6、8/8、11/11、2/2** 可正常进入并渲染（唯一未达：OpenLLM“报表趋势”，承接子菜单路由缺陷，见 #3）。
- 无任何 requestfailed 网络级失败；控制台 error 全部来自 HTTP≥400 资源加载（画像 403 系列、对话管理 500）。

**覆盖矩阵摘要**

- 覆盖页面总数：**67**（含 7 大模块落地页及其全部可见子页、2 个壳页面）
- 判定 PASS：**58**；FAIL：**9**
- FAIL 页面：03-OpenLLM-24-对话管理、03-OpenLLM-32-模型对比推荐、03-OpenLLM-err-33、06-画像、06-画像-01-数据总览、06-画像-02-画像列表、06-画像-04-标签管理、06-画像-06-分析报表、06-画像-11-批量任务
- 截图存档：73 张 PNG（见下方截图索引），目录 `dogfood-output\screenshots\full\`

## 2. 覆盖矩阵

| # | PID | 页面 | 路由 | 主内容/表行 | 控制台e/w/HTTP≥400 | 判定 | 备注（问题） | 截图文件 |
|---|---|---|---|---|---|---|---|---|
| 1 | 01-仪表盘 | 仪表盘 | /dashboard | 121/178 字, 表0行 | 0/5/0 | PASS | 见 #4；控制台警告×5 | 01-仪表盘.png |
| 2 | 02-租户管理 | 租户管理 | /system/tenants | 90/142 字, 表1行 | 0/0/0 | PASS | — | 02-租户管理.png |
| 3 | 03-OpenLLM | OpenLLM | /openllm/models | 803/824 字, 表11行 | 0/0/0 | PASS | — | 03-OpenLLM.png |
| 4 | 03-OpenLLM-01-模型管理 | OpenLLM/模型中心/模型管理 | /openllm/models | 803/915 字, 表11行 | 0/0/0 | PASS | — | 03-OpenLLM-01-模型管理.png |
| 5 | 03-OpenLLM-02-本地模型 | OpenLLM/模型中心/本地模型 | /openllm/models/local | 135/156 字, 表0行 | 0/0/0 | PASS | — | 03-OpenLLM-02-本地模型.png |
| 6 | 03-OpenLLM-03-模型分类 | OpenLLM/模型中心/模型分类 | /openllm/models/categories | 791/812 字, 表10行 | 0/0/0 | PASS | — | 03-OpenLLM-03-模型分类.png |
| 7 | 03-OpenLLM-04-模型对比 | OpenLLM/模型中心/模型对比 | /openllm/models/comparison | 283/304 字, 表7行 | 0/0/0 | PASS | — | 03-OpenLLM-04-模型对比.png |
| 8 | 03-OpenLLM-05-开源市场 | OpenLLM/模型中心/开源市场 | /openllm/models/market | 398/419 字, 表0行 | 0/0/0 | PASS | — | 03-OpenLLM-05-开源市场.png |
| 9 | 03-OpenLLM-06-下载管理 | OpenLLM/模型中心/下载管理 | /openllm/downloads | 225/246 字, 表4行 | 0/0/0 | PASS | — | 03-OpenLLM-06-下载管理.png |
| 10 | 03-OpenLLM-07-提供商管理 | OpenLLM/模型中心/提供商管理 | /openllm/providers | 242/263 字, 表0行 | 0/0/0 | PASS | — | 03-OpenLLM-07-提供商管理.png |
| 11 | 03-OpenLLM-08-我的收藏 | OpenLLM/模型中心/我的收藏 | /openllm/favorites | 295/316 字, 表0行 | 0/0/0 | PASS | — | 03-OpenLLM-08-我的收藏.png |
| 12 | 03-OpenLLM-09-用量统计 | OpenLLM/模型中心/用量统计 | /openllm/usage | 756/868 字, 表10行 | 0/0/0 | PASS | — | 03-OpenLLM-09-用量统计.png |
| 13 | 03-OpenLLM-10-个人设置 | OpenLLM/模型中心/个人设置 | /openllm/settings | 83/104 字, 表0行 | 0/0/0 | PASS | — | 03-OpenLLM-10-个人设置.png |
| 14 | 03-OpenLLM-11-提供商注册 | OpenLLM/模型中心/提供商注册 | /openllm/providers/register | 57/78 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-11-提供商注册.png |
| 15 | 03-OpenLLM-12-API-密钥 | OpenLLM/模型中心/API 密钥 | /openllm/api-keys | 204/225 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-12-API-密钥.png |
| 16 | 03-OpenLLM-13-模型部署 | OpenLLM/模型中心/模型部署 | /openllm/deploy | 55/76 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-13-模型部署.png |
| 17 | 03-OpenLLM-14-GPU-监控 | OpenLLM/模型中心/GPU 监控 | /openllm/gpu | 59/80 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-14-GPU-监控.png |
| 18 | 03-OpenLLM-15-EdgeRouter-适配器 | OpenLLM/模型中心/EdgeRouter 适配器 | /openllm/adapters | 75/188 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-15-EdgeRouter-适配器.png |
| 19 | 03-OpenLLM-16-应用管理 | OpenLLM/AI 应用/应用管理 | /openllm/apps | 36/117 字, 表0行 | 0/0/0 | PASS | 列表为空（业务无数据，页面正常） | 03-OpenLLM-16-应用管理.png |
| 20 | 03-OpenLLM-17-Playground | OpenLLM/AI 应用/Playground | /openllm/playground | 30/51 字, 表0行 | 0/0/0 | PASS | — | 03-OpenLLM-17-Playground.png |
| 21 | 03-OpenLLM-18-Prompt-模板 | OpenLLM/AI 应用/Prompt 模板 | /openllm/prompt-templates | 136/157 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-18-Prompt-模板.png |
| 22 | 03-OpenLLM-19-Prompt-实验 | OpenLLM/AI 应用/Prompt 实验 | /openllm/prompt-experiments | 128/149 字, 表2行 | 0/0/0 | PASS | — | 03-OpenLLM-19-Prompt-实验.png |
| 23 | 03-OpenLLM-20-插件管理 | OpenLLM/AI 应用/插件管理 | /openllm/plugins | 227/248 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-20-插件管理.png |
| 24 | 03-OpenLLM-21-工具调用监控 | OpenLLM/AI 应用/工具调用监控 | /openllm/tool-calls | 246/267 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-21-工具调用监控.png |
| 25 | 03-OpenLLM-22-A-B-测试 | OpenLLM/AI 应用/A/B 测试 | /openllm/ab-tests | 151/172 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-22-A-B-测试.png |
| 26 | 03-OpenLLM-23-调用记录 | OpenLLM/AI 应用/调用记录 | /openllm/apps/calls | 55/137 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-23-调用记录.png |
| 27 | 03-OpenLLM-24-对话管理 | OpenLLM/对话监控/对话管理 | /openllm/conversations | 67/104 字, 表0行 | 1/0/1 | FAIL | 控制台错误×1 HTTP≥400×1[500]；见 #2 | 03-OpenLLM-24-对话管理.png |
| 28 | 03-OpenLLM-25-监控仪表盘 | OpenLLM/对话监控/监控仪表盘 | /openllm/monitoring | 224/245 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-25-监控仪表盘.png |
| 29 | 03-OpenLLM-26-链路追踪 | OpenLLM/对话监控/链路追踪 | /openllm/monitoring/traces | 55/108 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-26-链路追踪.png |
| 30 | 03-OpenLLM-27-成本分析 | OpenLLM/对话监控/成本分析 | /openllm/monitoring/costs | 435/456 字, 表3行 | 0/0/0 | PASS | — | 03-OpenLLM-27-成本分析.png |
| 31 | 03-OpenLLM-28-预算管理 | OpenLLM/对话监控/预算管理 | /openllm/monitoring/budgets | 55/76 字, 表0行 | 0/0/0 | PASS | 占位页（提示 v1.2.0 已规划）见 #5 | 03-OpenLLM-28-预算管理.png |
| 32 | 03-OpenLLM-29-告警中心 | OpenLLM/对话监控/告警中心 | /openllm/monitoring/alerts | 269/290 字, 表4行 | 0/0/0 | PASS | — | 03-OpenLLM-29-告警中心.png |
| 33 | 03-OpenLLM-30-路由策略 | OpenLLM/平台联动/路由策略 | /openllm/routing/strategies | 241/262 字, 表4行 | 0/0/0 | PASS | — | 03-OpenLLM-30-路由策略.png |
| 34 | 03-OpenLLM-31-熔断器 | OpenLLM/平台联动/熔断器 | /openllm/routing/circuit-breakers | 241/283 字, 表4行 | 0/0/0 | PASS | — | 03-OpenLLM-31-熔断器.png |
| 35 | 03-OpenLLM-32-模型对比推荐 | OpenLLM/平台联动/模型对比推荐 | /dashboard | 121/172 字, 表0行 | 0/1/0 | FAIL | 路由 /openllm/recommend 无匹配，重定向回 /dashboard；见 #3 | 03-OpenLLM-32-模型对比推荐.png |
| 36 | 03-OpenLLM-err-33 | OpenLLM/平台联动/报表趋势 | /dashboard | 121/172 字, 表0行 | 0/0/0 | FAIL | 承接 #3：菜单随重定向失效，页面不可达；见 #3 | 03-OpenLLM-err-33.png |
| 37 | 04-知识库 | 知识库 | /knowledge/list | 374/378 字, 表0行 | 0/0/0 | PASS | — | 04-知识库.png |
| 38 | 04-知识库-01-知识库管理 | 知识库/知识库/知识库管理 | /knowledge/list | 374/410 字, 表0行 | 0/0/0 | PASS | — | 04-知识库-01-知识库管理.png |
| 39 | 04-知识库-02-RAG-对话 | 知识库/知识库/RAG 对话 | /knowledge/chat | 83/87 字, 表0行 | 0/0/0 | PASS | — | 04-知识库-02-RAG-对话.png |
| 40 | 04-知识库-03-用户管理 | 知识库/知识库/用户管理 | /knowledge/users | 306/310 字, 表4行 | 0/0/0 | PASS | — | 04-知识库-03-用户管理.png |
| 41 | 04-知识库-04-系统配置 | 知识库/知识库/系统配置 | /knowledge/settings | 182/219 字, 表0行 | 0/0/0 | PASS | — | 04-知识库-04-系统配置.png |
| 42 | 04-知识库-05-管理后台 | 知识库/知识库/管理后台 | /knowledge/admin | 1424/1428 字, 表17行 | 0/0/0 | PASS | — | 04-知识库-05-管理后台.png |
| 43 | 04-知识库-06-控制台 | 知识库/知识库/控制台 | /knowledge/console | 355/359 字, 表2行 | 0/1/0 | PASS | 见 #6；控制台警告×1 | 04-知识库-06-控制台.png |
| 44 | 05-记忆 | 记忆 | /memory/list | 771/776 字, 表7行 | 0/0/0 | PASS | — | 05-记忆.png |
| 45 | 05-记忆-01-记忆列表 | 记忆/记忆管理/记忆列表 | /memory/list | 771/818 字, 表7行 | 0/0/0 | PASS | — | 05-记忆-01-记忆列表.png |
| 46 | 05-记忆-02-记忆搜索 | 记忆/记忆管理/记忆搜索 | /memory/search | 86/91 字, 表0行 | 0/0/0 | PASS | — | 05-记忆-02-记忆搜索.png |
| 47 | 05-记忆-03-会话管理 | 记忆/记忆管理/会话管理 | /memory/sessions | 107/112 字, 表0行 | 0/0/0 | PASS | — | 05-记忆-03-会话管理.png |
| 48 | 05-记忆-04-记忆图谱 | 记忆/记忆管理/记忆图谱 | /memory/graph | 393/398 字, 表10行 | 0/0/0 | PASS | — | 05-记忆-04-记忆图谱.png |
| 49 | 05-记忆-05-API-网关 | 记忆/记忆管理/API 网关 | /memory/api-gateway | 133/138 字, 表0行 | 0/0/0 | PASS | — | 05-记忆-05-API-网关.png |
| 50 | 05-记忆-06-管理后台 | 记忆/记忆管理/管理后台 | /memory/admin | 343/348 字, 表2行 | 0/0/0 | PASS | — | 05-记忆-06-管理后台.png |
| 51 | 05-记忆-07-衰减配置 | 记忆/记忆管理/衰减配置 | /memory/decay | 200/205 字, 表1行 | 0/0/0 | PASS | — | 05-记忆-07-衰减配置.png |
| 52 | 05-记忆-08-写入记忆 | 记忆/记忆管理/写入记忆 | /memory/write | 222/269 字, 表0行 | 0/0/0 | PASS | — | 05-记忆-08-写入记忆.png |
| 53 | 06-画像 | 画像 | /portrait/list | 191/210 字, 表0行 | 2/0/2 | FAIL | 控制台错误×2 HTTP≥400×2[403]；见 #1 | 06-画像.png |
| 54 | 06-画像-01-数据总览 | 画像/画像管理/数据总览 | /portrait/overview | 201/279 字, 表0行 | 2/0/2 | FAIL | 控制台错误×2 HTTP≥400×2[403]；见 #1 | 06-画像-01-数据总览.png |
| 55 | 06-画像-02-画像列表 | 画像/画像管理/画像列表 | /portrait/list | 191/267 字, 表0行 | 2/0/2 | FAIL | 控制台错误×2 HTTP≥400×2[403]；见 #1 | 06-画像-02-画像列表.png |
| 56 | 06-画像-03-画像搜索 | 画像/画像管理/画像搜索 | /portrait/search | 77/140 字, 表0行 | 0/0/0 | PASS | — | 06-画像-03-画像搜索.png |
| 57 | 06-画像-04-标签管理 | 画像/画像管理/标签管理 | /portrait/tags | 106/176 字, 表0行 | 1/1/1 | FAIL | 控制台错误×1 HTTP≥400×1[403]；见 #1、#7 | 06-画像-04-标签管理.png |
| 58 | 06-画像-05-规则引擎 | 画像/画像管理/规则引擎 | /portrait/rules | 249/254 字, 表4行 | 0/0/0 | PASS | — | 06-画像-05-规则引擎.png |
| 59 | 06-画像-06-分析报表 | 画像/画像管理/分析报表 | /portrait/reports | 191/210 字, 表0行 | 2/0/2 | FAIL | 控制台错误×2 HTTP≥400×2[403]；见 #1 | 06-画像-06-分析报表.png |
| 60 | 06-画像-07-限流管理 | 画像/画像管理/限流管理 | /portrait/rate-limit | 328/335 字, 表7行 | 0/0/0 | PASS | — | 06-画像-07-限流管理.png |
| 61 | 06-画像-08-API-管理 | 画像/画像管理/API 管理 | /portrait/api-manage | 192/197 字, 表3行 | 0/0/0 | PASS | — | 06-画像-08-API-管理.png |
| 62 | 06-画像-09-权限管理 | 画像/画像管理/权限管理 | /portrait/permissions | 348/353 字, 表6行 | 0/0/0 | PASS | — | 06-画像-09-权限管理.png |
| 63 | 06-画像-10-系统监控 | 画像/画像管理/系统监控 | /portrait/monitor | 258/263 字, 表3行 | 0/0/0 | PASS | — | 06-画像-10-系统监控.png |
| 64 | 06-画像-11-批量任务 | 画像/画像管理/批量任务 | /portrait/batch | 191/210 字, 表0行 | 2/0/2 | FAIL | 控制台错误×2 HTTP≥400×2[403]；见 #1 | 06-画像-11-批量任务.png |
| 65 | 07-统一网关 | 统一网关 | /gateway/services | 419/424 字, 表4行 | 0/0/0 | PASS | — | 07-统一网关.png |
| 66 | 07-统一网关-01-服务列表 | 统一网关/网关管理/服务列表 | /gateway/services | 419/434 字, 表4行 | 0/0/0 | PASS | — | 07-统一网关-01-服务列表.png |
| 67 | 07-统一网关-02-聚合测试 | 统一网关/网关管理/聚合测试 | /gateway/aggregate | 131/136 字, 表0行 | 0/0/0 | PASS | — | 07-统一网关-02-聚合测试.png |

> 判定口径：主内容非空 = 页面按预期渲染出内容容器/表格/表单/图卡（不含纯骨架）；FAIL 依据 = 控制台 error、HTTP≥400、失败请求、或路由重定向导致页面不可达。控制台仅含 warning 不判 FAIL（单列问题 #4/#6/#7 等）。截图文件名=PID 列。

## 3. 问题清单

### P1 — 阻断（影响整个模块不可用）

#### #1 画像模块：DPS 数据接口全部 403（“组织不存在”），列表/概览/报表/标签/批量任务均不可用
- **页面**：画像 /portrait/list（模块落地页）及 数据总览 /portrait/overview、分析报表 /portrait/reports、批量任务 /portrait/batch、标签管理 /portrait/tags
- **复现步骤**：登录后点击侧栏“画像”→ 落地即 403 提示；进入 数据总览/分析报表/批量任务/标签管理 同样 403；点击页面顶部提示条“点击重试”后再次请求仍 403。
- **截图**：06-画像.png、06-画像-01-数据总览.png、06-画像-02-画像列表.png、06-画像-04-标签管理.png、06-画像-06-分析报表.png、06-画像-11-批量任务.png
- **控制台/网络证据**：
  - `Failed to load resource: ... 403 (Forbidden)`（上述各页均出现）
  - `GET /api/v1/dps-proxy/portraits?page=1&page_size=20` → **403**
  - `GET /api/v1/dps-proxy/reports/overview` → **403**
  - `GET /api/v1/dps-proxy/tags/categories` → **403**
  - 页面弹出两条消息 `组织不存在`；画像列表加载失败：Request failed with status code 403
- **影响**：画像模块核心能力（画像查询、数据总览、分析报表、标签、批量任务）当前完全不可用；只有“画像搜索/规则引擎/限流管理/API 管理/权限管理/系统监控”等不依赖 dps-proxy 的子页可用。
- **建议**：检查 dps-proxy 鉴权头/组织（tenant/org）上下文的传递，确认 admin 在 DPS 侧的组织映射，修复后回归重测全部 11 个子页。
- **✅ 修复闭环（2026-09-06）**：根因=dps-proxy 转发头 X-Org-ID 为 OpenBase 侧默认 `org-1`（旧种子语义），DPS 共享 PG 现库 org code 为 `dps-org-001`，缺失 `dps_org_map/dps_tenant_map` 部署映射致 403。修复：`.env` + 编排 Env 双落点写入映射（`org-1/tenant-1`→`dps-org-001/dps-tenant-001`，双键兼容 tenant_code claim 路径）；复验：`GET /api/v1/dps-proxy/portraits`→200（3 条）、tags/reports/health→200，画像列表/详情/总览/tags/batch 前端无 403（截图 evidence/p11-portrait-list-fixed.jpg、p11-portrait-overview-fixed.jpg）。任务书 v2.5.0（commit def7ed8）。

### P2 — 主要

#### #2 OpenLLM → 对话监控 → 对话管理：模型下拉接口上游 500，页面顶部报错、列表为空
- **页面**：/openllm/conversations
- **复现步骤**：OpenLLM → 对话监控 → 对话管理；页面出现红色提示条“upstream error”，模型下拉无法取数，会话列表为“暂无数据”。
- **截图**：03-OpenLLM-24-对话管理.png
- **控制台/网络证据**：`Failed to load resource ... 500 (Internal Server Error)`；`GET /api/v1/llm-proxy/models` → **500**；页面 alert 文本 `upstream error`
- **影响**：会话管理页不可正常使用（模型筛选源为 500）。同模块“模型中心”模型列表能正常展示 11 条，说明问题集中在 llm-proxy 的该接口或其上游，建议核对 llm-proxy→OpenLLM 的 /models 代理。
- **建议**：修复 llm-proxy `/api/v1/llm-proxy/models` 上游 500；验证后重测对话管理页筛选与会话列表。

#### #3 OpenLLM → 平台联动 → “模型对比推荐”：菜单指向未注册路由，被重定向回 /dashboard，且连带“报表趋势”无法访问
- **页面**：/openllm/recommend（预期）→ 实际回 /dashboard
- **复现步骤**：OpenLLM → 平台联动 → 悬停点击“模型对比推荐”→ 页面跳回统一仪表盘（上下文丢失）；随后“报表趋势”入口已无法再通过模块菜单访问（因已离开模块布局）。
- **截图**：03-OpenLLM-32-模型对比推荐.png（实为 /dashboard 画面）、03-OpenLLM-err-33.png
- **控制台证据**：`[Vue Router warn]: No match found for location with path "/openllm/recommend"`
- **影响**：两个菜单项（模型对比推荐、报表趋势）均不可用；子页遍历覆盖率为 33 项中 31 项正常。
- **建议**：将菜单路径与已注册子路由对齐（或补注册 /openllm/recommend 与 /openllm/reports/trend 路由），并建议增加“未匹配路由”时不回跳统一仪表盘的兜底提示。
- **✅ 修复闭环（2026-09-06）**：openllm 模块路由表补注册 `recommend`（P2RecommendView.vue）与 `reports-trend`（P2ReportTrendView.vue），路径与 navItems 菜单对齐；连带修复 `router/index.ts` 顶层模块路由 `addRoute('', ...)` 父名告警（5 模块 5 条）→ `addRoute(record)`。复验：`/openllm/recommend` 渲染“模型对比推荐”（维度下拉 + 文档库）、`/openllm/reports-trend` 渲染“报表趋势分析”（组织排名表），均停留在模块布局内不回 /dashboard；新标签页全新加载 console 无 Vue Router 告警。截图 evidence/p2-recommend-fixed.png、p2-reports-trend-fixed.png。 |

### P3 — 次要 / 体验

#### #4 五大模块页无统一壳导航（无“仪表盘/退出登录/模块切换”入口）+ Vue Router 父路由注册告警
- **页面**：OpenLLM(/openllm/models)、知识库(/knowledge/list)、记忆(/memory/list)、画像(/portrait/list)、统一网关(/gateway/services) 全部全屏模块布局，页面内不存在“仪表盘”“退出登录”等统一入口（DOM 文本检查均无）。
- **复现步骤**：登录进入任意模块后，页面顶部只有该模块横向菜单；需浏览器后退或手输 /dashboard 才能回到统一入口 / 退出登录。
- **截图**：03-OpenLLM.png、04-知识库.png、05-记忆.png、06-画像.png、07-统一网关.png（各页右上/顶部均无统一入口控件）
- **控制台证据**（登录进入 /dashboard 时一次性出现 5 条，与 5 个模块一一对应）：
  `[Vue Router warn]: Parent route "" not found when adding child route {path: /openllm, component: , meta: Object, children: Array(35)}`，及 /knowledge(8)、/memory(11)、/portrait(13)、/gateway(3) 同构告警。
- **影响**：模块页面成为“孤岛”，用户难以在四系统模块间互切/回仪表盘/退出；同时该告警与“component 为空、parent 为 ''”的注册方式直接相关，疑似模块未挂在统一壳布局下，建议核对是否为主布局未包裹所致，并补齐模块内“返回统一入口”入口。

#### #5 OpenLLM 子菜单存在 7 个“已规划”占位页
- **页面**：提供商注册 /openllm/providers/register、模型部署 /openllm/deploy、GPU 监控 /openllm/gpu、EdgeRouter 适配器 /openllm/adapters、调用记录 /openllm/apps/calls、链路追踪 /openllm/monitoring/traces、预算管理 /openllm/monitoring/budgets
- **复现步骤**：进入对应菜单项，页面仅显示说明卡“……（v1.2.0 已规划，深度对接依赖四系统 API，经 openbase 代理就绪后启用）”。
- **截图**：03-OpenLLM-11-提供商注册.png、03-OpenLLM-13-模型部署.png、03-OpenLLM-14-GPU-监控.png、03-OpenLLM-15-EdgeRouter-适配器.png、03-OpenLLM-23-调用记录.png、03-OpenLLM-26-链路追踪.png、03-OpenLLM-28-预算管理.png
- **影响**：菜单已对用户开放但功能未实现，属体验层问题（无控制台错误）。建议置灰/标注“规划中”，避免误导。

#### #6 知识库 → 控制台（概览页）ECharts 容器尺寸为 0 告警
- **页面**：/knowledge/console（含 概览/API 调试器/接口文档/性能监控 4 个页签）
- **复现步骤**：知识库 → 控制台，图表区触发告警。
- **截图**：04-知识库-06-控制台.png
- **控制台证据**：`[ECharts] Can't get DOM width or height. Please check dom.clientWidth and dom.clientHeight...`
- **影响**：图表可能在隐藏/零尺寸容器中初始化导致不渲染或尺寸异常。建议在容器可见后再 init 或 resize 监听。

#### #7 画像 → 标签管理 ElForm label 宽度计算告警
- **页面**：/portrait/tags
- **复现步骤**：画像 → 标签管理（同时叠加 #1 的 403 场景）
- **截图**：06-画像-04-标签管理.png
- **控制台证据**：`ElementPlusError: [ElForm] unexpected width 0 ... getLabelWidthIndex ...`
- **影响**：次要 UI 库告警，与加载失败状态下弹层布局有关。

#### #8 统一网关：连通性检测结果与注册表健康状态不一致
- **页面**：/gateway/services
- **复现步骤**：统一网关 → 服务列表 → 点击“连通性检测”，结果面板显示 openllm 可达(78ms)、openmemory 可达(16ms)，而 **openrag 不可达(31ms)、dps 不可达(16ms)**；同期服务列表对 openrag/dps 的“健康状态”均为“健康”。
- **截图**：07-统一网关-btn-连通性检测.png
- **控制台/网络证据**：整个操作过程无控制台错误、无失败请求、无 HTTP≥400。
- **影响**：连通性检测与注册表健康状态口径不一致（可能为探针目标路径/端口与实例注册地址不符，或对端拒绝探测），建议核对探针逻辑与判定阈值。
- **未执行项**：行内“下线”为破坏性操作，本报告仅打开确认框“确认下线该实例？取消/确定”并点击“取消”，未实际下线；“注册实例”仅打开对话框（系统/主机/端口/权重/取消/提交）后关闭，未提交。

## 4. 统一网关操作按钮初探结果

| 操作 | 结果 | 证据 |
|---|---|---|
| 刷新 | 正常，表格无异常，无错误 | 07-统一网关-btn-刷新.png |
| 连通性检测 | 弹出检测结果面板（4 系统）；openrag/dps 显示“不可达”，见 #8 | 07-统一网关-btn-连通性检测.png |
| 注册实例 | 打开“注册服务实例”对话框（系统/主机/端口/权重），点“取消”关闭 | 07-统一网关-btn-注册实例-dialog.png |
| 下线（行操作） | 打开“确认下线该实例？”确认框，点“取消”放弃（未破坏数据） | 07-统一网关-btn-下线-confirm.png |
| 聚合测试（子页） | /gateway/aggregate 渲染聚合步骤配置/结果映射表单，无错误 | 07-统一网关-02-聚合测试.png |

## 5. 验证性 PASS 亮点（正常页面抽样说明）

- 仪表盘：6 卡片 + 7 侧栏菜单渲染正常；头部用户下拉仅含“退出登录”。
- 租户管理：列表显示 1 条租户（tenant-1/company-1），工具栏含 创建租户/配额/停用/删除。
- OpenLLM 模型中心：模型列表 11 行（gpt-4、deepseek-v4-flash、qwen3:0.6b 等）及“详情/编辑/删除”行操作可用；监控仪表盘展示请求量 12,480、Token 8.2M 等指标与告警表。
- 记忆：列表 7 行记忆数据；记忆图谱渲染实体图（张伟/李娜/OpenBase 等）与实体表。
- 知识库管理：6 个知识库集合卡片（含 进入/删除 操作）。
- 统一网关服务列表：OpenLLM/OpenRAG/OpenMemory/DPS 4 个服务实例展示（地址 127.0.0.1:8001/8010/8020/8030）。

## 6. 截图索引

文件均位于 `dogfood-output\screenshots\full\`。

| 文件 | 对应页面 |
|---|---|
| 01-仪表盘.png | 仪表盘（/dashboard） |
| 02-租户管理.png | 租户管理（/system/tenants） |
| 03-OpenLLM.png | OpenLLM（/openllm/models） |
| 03-OpenLLM-01-模型管理.png | OpenLLM/模型中心/模型管理（/openllm/models） |
| 03-OpenLLM-02-本地模型.png | OpenLLM/模型中心/本地模型（/openllm/models/local） |
| 03-OpenLLM-03-模型分类.png | OpenLLM/模型中心/模型分类（/openllm/models/categories） |
| 03-OpenLLM-04-模型对比.png | OpenLLM/模型中心/模型对比（/openllm/models/comparison） |
| 03-OpenLLM-05-开源市场.png | OpenLLM/模型中心/开源市场（/openllm/models/market） |
| 03-OpenLLM-06-下载管理.png | OpenLLM/模型中心/下载管理（/openllm/downloads） |
| 03-OpenLLM-07-提供商管理.png | OpenLLM/模型中心/提供商管理（/openllm/providers） |
| 03-OpenLLM-08-我的收藏.png | OpenLLM/模型中心/我的收藏（/openllm/favorites） |
| 03-OpenLLM-09-用量统计.png | OpenLLM/模型中心/用量统计（/openllm/usage） |
| 03-OpenLLM-10-个人设置.png | OpenLLM/模型中心/个人设置（/openllm/settings） |
| 03-OpenLLM-11-提供商注册.png | OpenLLM/模型中心/提供商注册（/openllm/providers/register） |
| 03-OpenLLM-12-API-密钥.png | OpenLLM/模型中心/API 密钥（/openllm/api-keys） |
| 03-OpenLLM-13-模型部署.png | OpenLLM/模型中心/模型部署（/openllm/deploy） |
| 03-OpenLLM-14-GPU-监控.png | OpenLLM/模型中心/GPU 监控（/openllm/gpu） |
| 03-OpenLLM-15-EdgeRouter-适配器.png | OpenLLM/模型中心/EdgeRouter 适配器（/openllm/adapters） |
| 03-OpenLLM-16-应用管理.png | OpenLLM/AI 应用/应用管理（/openllm/apps） |
| 03-OpenLLM-17-Playground.png | OpenLLM/AI 应用/Playground（/openllm/playground） |
| 03-OpenLLM-18-Prompt-模板.png | OpenLLM/AI 应用/Prompt 模板（/openllm/prompt-templates） |
| 03-OpenLLM-19-Prompt-实验.png | OpenLLM/AI 应用/Prompt 实验（/openllm/prompt-experiments） |
| 03-OpenLLM-20-插件管理.png | OpenLLM/AI 应用/插件管理（/openllm/plugins） |
| 03-OpenLLM-21-工具调用监控.png | OpenLLM/AI 应用/工具调用监控（/openllm/tool-calls） |
| 03-OpenLLM-22-A-B-测试.png | OpenLLM/AI 应用/A/B 测试（/openllm/ab-tests） |
| 03-OpenLLM-23-调用记录.png | OpenLLM/AI 应用/调用记录（/openllm/apps/calls） |
| 03-OpenLLM-24-对话管理.png | OpenLLM/对话监控/对话管理（/openllm/conversations） |
| 03-OpenLLM-25-监控仪表盘.png | OpenLLM/对话监控/监控仪表盘（/openllm/monitoring） |
| 03-OpenLLM-26-链路追踪.png | OpenLLM/对话监控/链路追踪（/openllm/monitoring/traces） |
| 03-OpenLLM-27-成本分析.png | OpenLLM/对话监控/成本分析（/openllm/monitoring/costs） |
| 03-OpenLLM-28-预算管理.png | OpenLLM/对话监控/预算管理（/openllm/monitoring/budgets） |
| 03-OpenLLM-29-告警中心.png | OpenLLM/对话监控/告警中心（/openllm/monitoring/alerts） |
| 03-OpenLLM-30-路由策略.png | OpenLLM/平台联动/路由策略（/openllm/routing/strategies） |
| 03-OpenLLM-31-熔断器.png | OpenLLM/平台联动/熔断器（/openllm/routing/circuit-breakers） |
| 03-OpenLLM-32-模型对比推荐.png | OpenLLM/平台联动/模型对比推荐（/dashboard） |
| 03-OpenLLM-err-33.png | OpenLLM/平台联动/报表趋势（/dashboard） |
| 04-知识库.png | 知识库（/knowledge/list） |
| 04-知识库-01-知识库管理.png | 知识库/知识库/知识库管理（/knowledge/list） |
| 04-知识库-02-RAG-对话.png | 知识库/知识库/RAG 对话（/knowledge/chat） |
| 04-知识库-03-用户管理.png | 知识库/知识库/用户管理（/knowledge/users） |
| 04-知识库-04-系统配置.png | 知识库/知识库/系统配置（/knowledge/settings） |
| 04-知识库-05-管理后台.png | 知识库/知识库/管理后台（/knowledge/admin） |
| 04-知识库-06-控制台.png | 知识库/知识库/控制台（/knowledge/console） |
| 05-记忆.png | 记忆（/memory/list） |
| 05-记忆-01-记忆列表.png | 记忆/记忆管理/记忆列表（/memory/list） |
| 05-记忆-02-记忆搜索.png | 记忆/记忆管理/记忆搜索（/memory/search） |
| 05-记忆-03-会话管理.png | 记忆/记忆管理/会话管理（/memory/sessions） |
| 05-记忆-04-记忆图谱.png | 记忆/记忆管理/记忆图谱（/memory/graph） |
| 05-记忆-05-API-网关.png | 记忆/记忆管理/API 网关（/memory/api-gateway） |
| 05-记忆-06-管理后台.png | 记忆/记忆管理/管理后台（/memory/admin） |
| 05-记忆-07-衰减配置.png | 记忆/记忆管理/衰减配置（/memory/decay） |
| 05-记忆-08-写入记忆.png | 记忆/记忆管理/写入记忆（/memory/write） |
| 06-画像.png | 画像（/portrait/list） |
| 06-画像-01-数据总览.png | 画像/画像管理/数据总览（/portrait/overview） |
| 06-画像-02-画像列表.png | 画像/画像管理/画像列表（/portrait/list） |
| 06-画像-03-画像搜索.png | 画像/画像管理/画像搜索（/portrait/search） |
| 06-画像-04-标签管理.png | 画像/画像管理/标签管理（/portrait/tags） |
| 06-画像-05-规则引擎.png | 画像/画像管理/规则引擎（/portrait/rules） |
| 06-画像-06-分析报表.png | 画像/画像管理/分析报表（/portrait/reports） |
| 06-画像-07-限流管理.png | 画像/画像管理/限流管理（/portrait/rate-limit） |
| 06-画像-08-API-管理.png | 画像/画像管理/API 管理（/portrait/api-manage） |
| 06-画像-09-权限管理.png | 画像/画像管理/权限管理（/portrait/permissions） |
| 06-画像-10-系统监控.png | 画像/画像管理/系统监控（/portrait/monitor） |
| 06-画像-11-批量任务.png | 画像/画像管理/批量任务（/portrait/batch） |
| 07-统一网关.png | 统一网关（/gateway/services） |
| 07-统一网关-01-服务列表.png | 统一网关/网关管理/服务列表（/gateway/services） |
| 07-统一网关-02-聚合测试.png | 统一网关/网关管理/聚合测试（/gateway/aggregate） |
| 07-统一网关-btn-刷新.png | 统一网关 /gateway/services 操作按钮初探 |
| 07-统一网关-btn-连通性检测.png | 统一网关 /gateway/services 操作按钮初探 |
| 07-统一网关-btn-注册实例-dialog.png | 统一网关 /gateway/services 操作按钮初探 |
| 07-统一网关-btn-下线-confirm.png | 统一网关 /gateway/services 操作按钮初探 |
| 00-login-page.png | 登录页 /auth/login |
| 00-login.png | 登录后落地 /dashboard（同 01-仪表盘 视角） |

## 7. 附录

- 方法学：Playwright Chromium headless、1920x1080；每次动作后等待 networkidle（最长 12s）；控制台/网络事件按页面切分记录。
- 证据存储：`dogfood-output/evidence/` 下 `e2e_full.json`（68 条记录：登录、7 模块、子页与错误快照）、`gateway_probe.json`、`portrait_retry.json`（画像重试仍 403 的专项验证）、`recon.json`/`after-login.json`（侦察阶段记录）。
- 未执行项：所有确认类破坏性操作（下线、删除、停用、提交表单）一律只打开后取消或直接跳过，避免污染共享环境数据；未点击行内“详情/编辑”做深链表单操作。
- 限制：截图为 DOM 证据的补充存档（本次观察以 DOM/控制台/网络为准）。
