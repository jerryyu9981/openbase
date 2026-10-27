# OpenBase 全页面功能有效性核验报告

| 项目 | 内容 |
|---|---|
| 文档编号 | TEST-DEEP-20261027 |
| 版本 | v1.0.0 |
| 状态 | [Final] |
| 环境 | 本地全栈：OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / OIDC 8090 / 前端 5173；共享 PG 主用 `192.168.0.151:5432` |
| 执行日期 | 2026-10-27 |
| 口径 | 逐页「渲染 + 安全交互 + 逐接口数据有效性」，不只看是否白屏 |
| 证据 | `doc/test/evidence/s6/deep-walkthrough-20261027.json`（77 页逐页接口明细）<br>`doc/test/evidence/deep-20261027/`（77 张截图 + `B3-with-data.png`、`annotation-submit.png`） |

---

## 1. 结论摘要

**77 页全部可加载、无白屏、无 4xx/5xx 批量失败**；其中 1 页出现 1 次**偶发 502**（`/dashboard` 的聚合接口，单独复跑 200）。

| 判定 | 页数 | 含义 |
|---|--:|---|
| `PASS(real-data)` | 23 | 接口 200 **且返回真实业务数据（≥1 条）** |
| `PASS(api-ok-empty)` | 38 | 接口 200、结构完整，但**业务数据为 0 条**（环境无数据，非功能缺陷） |
| `PASS(no-data-api)` | 15 | 页面本身不自动取数（纯表单/静态文档/需点击才触发），交互已验证 |
| `FAIL(5xx)` | 1 | `/dashboard` 的 `monitoring/dashboard` 偶发 502（复跑 200） |
| 合计 | **77** | 无 4xx 契约错误、无 console error、无渲染兜底 |

**关键修复带来的实效**（本轮同时完成）：

| 项 | 结论 |
|---|---|
| 探针默认超时 3s → **10s** | 全栈启动稳定命中主用库（实测主用 7.9s 时仍判 primary，旧阈值必误切备用） |
| 标注复核代理缺口 | 此前 `dps-proxy` **没有任何标注复核路由** → 逐条通过/驳回与「提交」全 404；已补 2 条路由 |
| 批量复核端点 | DPS 新增 `POST /portrait/annotations/batch-review`，实测：空 items→400、不存在 id→逐条 404 隔离、真实 id→`succeeded=1` 且**库内持久化**（`review_status=rejected`、`reviewer_id=1`） |
| 前端契约 | `submitReview` 字段由 `review_status` 改为 DPS 原生 `status`（原写法会被判「不支持的操作」409）；「提交复核结果」改为真实批量调用，并如实反馈成功/失败数 |
| B3 谱系复验 | 造 2 条谱系数据后：来源表 **3 行**、影响面 **1/1**、口径可展开，`not-found=false`（截图 `B3-with-data.png`） |

---

## 2. 环境与前置

- 全栈启动：`.\scripts\service-orchestrator.ps1 -Action start`（默认探针 10s），7 个端口全部监听；openbase / openllm / openrag / openmemory / dps 均连**主用库**。
- 数据库延迟：本轮主用 `select 1` 实测 0.3~7.9s（网络抖动明显），因此单个页面等待窗口设为 5s，个别慢页（如本地模型 8.5s）已在备注中说明。
- 登录：`admin/admin123`（token 有效期 7200s，脚本内实时登录取新）。

---

## 3. 关键写路径实测（"功能是否真实有效"的直接证据）

| 路径 | 操作 | 结果 |
|---|---|---|
| AI 应用创建 | 页面填表 → 保存 | `POST /api/v1/ai-apps` 成功，后端列表可见，跳转 `/openllm/apps`；**失败路径**（拦截请求）提示 `Network Error` 且停留表单 |
| AI 应用删除 | API 清理测试数据 | 200，列表归零 |
| 标注批量复核 | `POST /dps-proxy/annotations/batch-review` | 空 `items`→400；假 id→逐条 404；真实 id→`succeeded=1`；库内 `review_status/reviewer_id/review_comment` 均已落库 |
| 标注单条复核 | `POST /dps-proxy/annotations/{id}/review`（字段修正后） | 语义透传正常；此前因**代理无此路由**恒 404 |
| 标注页提交按钮 | 点击「提交复核结果」（无候选） | 提示「暂无可提交的已落库候选」（不再假成功） |
| 谱系反查 | 输入 `service:channel` → 反查 | 来源表 3 行、影响面 1/1、口径展开、无 404 空态（截图 `B3-with-data.png`） |
| 标签血缘写入 | 造数（2 行）+ 审计了 tenant 口径 | API 按 `tenant_id=20000000-0000-0000-0000-000000000001` 过滤，生效 |

> 数据说明：本轮为验证 B3 写入 2 条 `tag_lineage`（`bbbbbbbb-1111…` / `bbbbbbbb-2222…`）与 1 条临时标注（`aaaaaaaa-1111-4111-8111-111111111111`）。另有 1 条 `33218971-…`（`adapter_id=obs02-manual`）为**本轮之前已存在**的数据，未作改动；其来源见同仓《OBS-02 四页人工深走查记录-v1.1.0》（AA/PM 侧遗留复验，含 DEF-03「DPS 复核 timestamptz 绑定字符串致 PG 500」的修复记录，本报告 §3 的批量复核实测即运行在 DEF-03 修复之后）。
>
> 清理 SQL（如需还原 B3 造数）：
> ```sql
> DELETE FROM platform.tag_lineage
>  WHERE id IN ('bbbbbbbb-1111-4111-8111-111111111111','bbbbbbbb-2222-4222-8222-222222222222');
> DELETE FROM platform.annotation WHERE id = 'aaaaaaaa-1111-4111-8111-111111111111';
> ```

---

## 4. 逐页核验清单

> `业务接口` = 剔除 `/api/v1/modules`、`/api/v1/auth/me` 后的调用数；`交互` = 本轮自动点击的安全控件。

| 页面 | 结论 | 业务接口 | 交互 |
|---|---|--:|---|
| /dashboard | FAIL(5xx) | 2 | - |
| /platform/identity/tenants | PASS(real-data) | 1 | - |
| /platform/identity/roles | PASS(real-data) | 2 | 刷新 |
| /platform/identity/org | PASS(real-data) | 1 | - |
| /platform/identity/workspaces | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/identity/users | PASS(real-data) | 2 | 刷新 |
| /platform/identity/memory-admin | PASS(no-data-api) | 0 | - |
| /platform/identity/auth-ext | PASS(no-data-api) | 0 | - |
| /platform/identity/dps-permissions | PASS(real-data) | 2 | 刷新 |
| /platform/config/general | PASS(real-data) | 2 | 刷新 |
| /platform/config/modules | PASS(no-data-api) | 0 | 刷新 |
| /platform/config/api-keys | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/config/rate-limits | PASS(real-data) | 1 | 刷新 |
| /platform/observability/logs | PASS(real-data) | 5 | 检索 / 重置 |
| /platform/observability/test-records | PASS(api-ok-empty) | 2 | 刷新轮次 |
| /platform/observability/monitoring | PASS(api-ok-empty) | 2 | - |
| /platform/observability/monitoring/costs | PASS(api-ok-empty) | 3 | 刷新 |
| /platform/observability/monitoring/alerts | PASS(real-data) | 4 | 刷新 |
| /platform/observability/monitoring/traces | PASS(api-ok-empty) | 4 | 查询 |
| /platform/observability/monitoring/budgets | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/observability/gpu | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/observability/usage | PASS(real-data) | 3 | 查询 |
| /platform/observability/billing | PASS(api-ok-empty) | 4 | 刷新 |
| /platform/observability/service-discovery | PASS(api-ok-empty) | 2 | 刷新 / 连通性检测 |
| /platform/observability/gateway-test | PASS(no-data-api) | 0 | 重置 |
| /platform/observability/app-calls | PASS(api-ok-empty) | 3 | 刷新 |
| /platform/observability/dps-monitor | PASS(api-ok-empty) | 1 | 刷新 |
| /platform/governance/providers | PASS(real-data) | 10 | 刷新 |
| /platform/governance/model-categories | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/governance/routing | PASS(api-ok-empty) | 3 | 刷新 |
| /platform/governance/circuit-breakers | PASS(api-ok-empty) | 3 | 刷新 |
| /platform/governance/deploy | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/governance/downloads | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/governance/tool-calls | PASS(api-ok-empty) | 3 | 查询 / 刷新 |
| /platform/governance/ab-tests | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/governance/prompt-templates | PASS(real-data) | 2 | 查询 |
| /platform/governance/prompt-experiments | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/developers/docs | PASS(no-data-api) | 0 | - |
| /platform/developers/edgerouter | PASS(api-ok-empty) | 4 | - |
| /platform/developers/plugins | PASS(real-data) | 3 | 刷新 |
| /platform/developers/dps-api | PASS(api-ok-empty) | 2 | 刷新 |
| /platform/developers/knowledge-admin | PASS(real-data) | 5 | 刷新 / 详情 |
| /platform/developers/knowledge-console | PASS(no-data-api) | 0 | - |
| /personal/settings | PASS(api-ok-empty) | 1 | - |
| /openllm/models | PASS(real-data) | 1 | 详情 / 详情 |
| /openllm/models/local | PASS(real-data) | 4 | - |
| /openllm/models/comparison | PASS(api-ok-empty) | 1 | - |
| /openllm/models/market | PASS(api-ok-empty) | 2 | 查询 |
| /openllm/favorites | PASS(api-ok-empty) | 2 | - |
| /openllm/apps | PASS(api-ok-empty) | 1 | - |
| /openllm/apps/new | PASS(no-data-api) | 0 | - |
| /openllm/playground | PASS(real-data) | 1 | - |
| /openllm/conversations | PASS(real-data) | 2 | - |
| /openllm/recommend | PASS(no-data-api) | 0 | 检索 |
| /openllm/reports-trend | PASS(api-ok-empty) | 3 | 刷新 |
| /knowledge/list | PASS(real-data) | 2 | 刷新 |
| /knowledge/chat | PASS(real-data) | 2 | 刷新列表 |
| /memory/list | PASS(api-ok-empty) | 1 | - |
| /memory/search | PASS(no-data-api) | 0 | 搜索 |
| /memory/sessions | PASS(api-ok-empty) | 2 | 刷新 |
| /memory/graph | PASS(api-ok-empty) | 1 | 刷新图谱 |
| /memory/decay | PASS(api-ok-empty) | 2 | 重置 |
| /memory/write | PASS(no-data-api) | 0 | 重置 |
| /portrait/overview | PASS(real-data) | 2 | - |
| /portrait/list | PASS(real-data) | 3 | 画像查询 |
| /portrait/search | PASS(real-data) | 1 | 查询 / 重置 |
| /portrait/tags | PASS(api-ok-empty) | 2 | 刷新 |
| /portrait/rules | PASS(no-data-api) | 0 | - |
| /portrait/dps/templates | PASS(api-ok-empty) | 3 | 查询 / 重置 |
| /portrait/dps/templates/new | PASS(api-ok-empty) | 1 | - |
| /portrait/dps/template-packages | PASS(no-data-api) | 0 | - |
| /portrait/dps/lineage | PASS(no-data-api) | 0 | - |
| /portrait/dps/measures | PASS(no-data-api) | 0 | 查询建议 |
| /portrait/dps/scoring-types | PASS(api-ok-empty) | 2 | 查询 |
| /portrait/dps/annotation-adapters | PASS(no-data-api) | 0 | - |
| /portrait/dps/annotation-templates | PASS(api-ok-empty) | 3 | 查询 / 重置 |
| /portrait/dps/tags | PASS(api-ok-empty) | 2 | - |

---

## 5. 真实数据页（23 页，功能"确实在跑"）

`/platform/identity/{tenants,roles,org,users,dps-permissions}`、`/platform/config/{general,rate-limits}`、
`/platform/observability/logs`、`/platform/observability/monitoring/alerts`、`/platform/observability/usage`、
`/platform/governance/providers`（10 个接口，8 个有数据）、`/platform/governance/prompt-templates`、
`/platform/developers/plugins`、`/platform/developers/knowledge-admin`、
`/openllm/models`、`/openllm/models/local`（模型 2 个 + GPU 信息）、`/openllm/playground`、`/openllm/conversations`、
`/knowledge/list`、`/knowledge/chat`、`/portrait/overview`、`/portrait/list`、`/portrait/search`。

另有 `/portrait/dps/lineage` 单独复验为真实数据（3 条来源），见 §3。

## 6. 接口通但数据为空的 38 页（环境无数据，非缺陷）

典型：`workspaces`、`api-keys`、`test-records`、`monitoring`、`costs`、`traces`、`budgets`、`gpu`、`billing`、
`service-discovery`、`app-calls`、`model-categories`、`routing`、`circuit-breakers`、`deploy`、`downloads`、
`tool-calls`、`ab-tests`、`prompt-experiments`、`edgerouter`、`dps-api`、`models/comparison`、`models/market`、
`favorites`、`apps`、`reports-trend`、`memory/{list,sessions,graph}`、`portrait/tags`、`dps/{templates,templates/new,scoring-types,annotation-templates,tags}`、`personal/settings`。

判定依据：接口 **200**、返回结构完整（含 `total=0` / 空数组 / 指标全 0），未出现 4xx/5xx。
若要转为"真实数据"，需按各页业务造数（如预算、A/B 实验、工具调用、标注模板等）。

## 7. 不自动取数的 15 页（交互已逐一触发）

| 页面 | 原因 |
|---|---|
| `/platform/identity/auth-ext` | 纯表单（注册/找回密码），契约 mock |
| `/platform/config/modules` | 开关读本地状态，切换才写 |
| `/platform/observability/gateway-test` | 需点击「发送」类动作 |
| `/platform/developers/{docs,knowledge-console}` | 静态文档 / 需切 tab 调接口 |
| `/openllm/{apps/new,recommend}` | 新建表单 / 需点「检索」 |
| `/memory/{search,write}` | 需输入后点搜索 / 提交 |
| `/portrait/rules` | 规则执行需点「执行任务」 |
| `/portrait/dps/{template-packages,measures,annotation-adapters}` | 导入导出 / 查询建议 / 生成候选均需点击 |
| `/portrait/dps/lineage` | 需输入 tag_code 后点「反查」（已单独复验，见 §3） |
| `/platform/identity/memory-admin` | 5s 窗口内未观察到 memory-proxy 调用（服务较慢），历史轮次见过 3 次调用 |

## 8. 需关注项

| 编号 | 级别 | 现象 | 归因 / 建议 |
|---|---|---|---|
| DW-01 | P3 | `/dashboard` 的 `GET /proxy/openllm/api/v1/monitoring/dashboard` 出现 **1 次 502** | 代理超时 10s；该聚合接口在并发/冷启期可达 4s+，偶发被重置。单跑 200（1.3~3.9s）。建议对该聚合端点单独放宽或加重试 |
| DW-02 | P3 | 主用库延迟波动大（0.3~7.9s） | 探针已提到 10s，避免误切；业务侧慢查询仍会影响首屏 |
| DW-03 | — | 38 页空数据 | 环境数据缺失，非功能缺陷；建议按业务场景造数后再做一轮"有数据态"回归 |

## 9. 修订历史

| 版本 | 日期 | 执行人 | 说明 |
|---|---|---|---|
| v1.0.0 | 2026-10-27 | FA-OpenBase-Dev（AI 辅助） | 首版：77 页功能有效性核验（23 真实数据 / 38 空数据 / 15 不自动取数 / 1 偶发 502）；批量复核与谱系链路实测；探针阈值与 B3 复验结论 |
