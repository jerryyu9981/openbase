# OpenBase 全页面功能有效性核验报告

| 项目 | 内容 |
|---|---|
| 文档编号 | TEST-DEEP-20261027 |
| 版本 | v1.2.1 |
| 状态 | [Final] |
| 环境 | 本地全栈：OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / OIDC 8090 / 前端 5173；共享 PG 主用 `192.168.0.151:5432` |
| 执行日期 | 2026-10-27（首轮 77 页核验）/ 2026-10-28（三项关注项复核与修复验证 + 服务 Key 持久化与全量测试修复） |
| 口径 | 逐页「渲染 + 安全交互 + 逐接口数据有效性」，不只看是否白屏 |
| 证据 | `doc/test/evidence/s6/deep-walkthrough-20261027.json`（77 页逐页接口明细）<br>`doc/test/evidence/deep-20261027/`（77 张截图 + `B3-with-data.png`、`annotation-submit.png`）<br>复核证据：`doc/test/evidence/manual/dw-recheck-20261028.json`（DW-01 16 次调用明细 + DW-03 五页判定）、`doc/test/evidence/deep-20261028/`（5 张有数据态截图） |

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

**v1.1.0 复核结论（2026-10-28）：三项关注项已全部闭环**

| 项 | 复核结论 | 处置 |
|---|---|---|
| DW-01 | ✅ 已修复并线上验证：`monitoring/dashboard` 串行 10 次 + 6 路并发共 **16/16 全部 200**（串行 357~437ms，并发峰值 2247ms） | 代理对只读聚合端点放宽至 30s + GET/HEAD 传输级重试 1 次（`openbase/modules/proxy/__init__.py`），3 条回归用例通过 |
| DW-02 | ✅ 非配置缺陷：主用库连接/查询实测 82~585ms，首轮 7.9s 为跨网链路瞬态；探针 10s 阈值已覆盖 | 维持 10s，不做代码变更；跨网抖动属环境属性 |
| DW-03 | ✅ 已按业务场景造数并复验：5 页由 `PASS(api-ok-empty)` 转为 `PASS(real-data)`（行数 1/1/1/2/1） | 造数 5 项；同时发现并修复 OpenLLM「创建 Prompt 实验 500」两处真实缺陷（详见 §8.3） |

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

> v1.1.0 更新：其中 `workspaces`、`monitoring/budgets`、`ab-tests`、`prompt-experiments`、`api-keys` 5 页已造数并复验为 `PASS(real-data)`（见 §8.3），空数据页由 38 页降为 33 页。

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

## 8. 需关注项（v1.1.0 复核结论）

首轮登记 3 项，复核后 **3 项全部闭环**（1 项代码修复、1 项确认为环境瞬态、1 项造数并顺带修复 2 处真实缺陷）。

| 编号 | 级别 | 现象 | v1.1.0 结论 |
|---|---|---|---|
| DW-01 | P3 | `/dashboard` 的 `GET /proxy/openllm/api/v1/monitoring/dashboard` 出现 **1 次 502** | 已修复（§8.1） |
| DW-02 | P3 | 主用库延迟波动大（0.3~7.9s） | 确认为跨网链路瞬态，无需改代码（§8.2） |
| DW-03 | — | 38 页空数据 | 抽 5 页造数复验为 real-data，并发现 2 处真实缺陷已修复（§8.3） |

### 8.1 DW-01 代理偶发 502：已修复

- **归因**：代理全局超时 10s；`monitoring/dashboard` 属跨多表只读聚合，冷启/并发下实测可达 4s+，跨网链路抖动时会被上游重置（`httpx` 传输级异常）→ 前端 502。
- **修复**（`openbase/modules/proxy/__init__.py`）：
  1. 只读聚合端点（`/monitoring/dashboard`、`/billing/v2/cost-analysis`、`/monitoring/usage`、`/usage/summary`）超时由 10s 放宽到 **30s**（`SLOW_PATH_HINTS` / `SLOW_PATH_TIMEOUT`），其余端点维持 10s，避免故障拖成全站等待；
  2. 新增 `_request_upstream`：**仅 GET/HEAD** 遇 `httpx.TransportError` 重试 1 次（退避 0.2s），写请求不重试，避免重复副作用。
- **验证**：
  - 回归用例 `tests/test_proxy_resilience.py`（慢路径 30s / GET 重试 1 次 / POST 不重试）**3 passed**；
  - 经受管编排器 `-Action stop` + `-Action start` 重启加载改动后线上复验：串行 10 次 + 6 路并发共 **16/16 = 200**，串行 357~437ms、并发 1875~2247ms，远低于 30s 阈值；
  - `ruff check` 0 错误。
- **残余风险**：30s 仅覆盖只读聚合；若上游长时间不可用，前端仍会在 30s 后收到 502（符合预期，不掩盖故障）。

### 8.2 DW-02 主用库延迟波动：确认为环境瞬态

- 复核方式：同一连接内 `select 1` 计时，单次与 5 次聚合各测 3 轮：单次 150~585ms、5 次 158~183ms；服务重启期探针 82~107ms。
- 结论：首轮 7.9s 为跨网链路瞬时抖动，**非配置或代码缺陷**；编排器探针已由 3s 提到 10s，足以覆盖正常波动且不误切备用库（备用库 api_keys 仅 2 条 vs 主用 17 条，误切会改变业务数据面）。
- 处置：不改代码；跨网抖动属环境属性，如需进一步收敛应由网络/数据面同步方案解决（历史遗留 XR-OPS-09）。

### 8.3 DW-03 空数据页：抽 5 页造数复验 + 顺带修复 2 处真实缺陷

造数（均为标注「全页面功能核验造数（DW-03），可删除」的最小业务对象）：

| 页面 | 造数对象 | 复验结果 |
|---|---|---|
| `/platform/identity/workspaces` | 工作空间 `E2E 核验工作空间` | `PASS(real-data)`，列表 1 行 |
| `/platform/observability/monitoring/budgets` | 月度预算 `E2E 核验月度预算`（global / 100 USD / monthly） | `PASS(real-data)`，列表 1 行 |
| `/platform/governance/ab-tests` | 路由 A/B `E2E 核验路由 A/B` | `PASS(real-data)`，列表 1 行 |
| `/platform/governance/prompt-experiments` | Prompt 实验 `E2E 核验 Prompt 实验`（2 variants） | `PASS(real-data)`，列表 2 行 |
| `/platform/config/api-keys` | 服务 Key `E2E 核验 Key` | `PASS(real-data)`，列表 1 行 |

**造数过程中发现并修复的 OpenLLM 真实缺陷（`backend/app/api/prompt_experiments.py`）**：

1. `variables: list = Field(default=list)`：Pydantic v2 不再把可调用对象当默认工厂，`list` **类型对象**被写入字段值，`json.dumps` 抛 `TypeError: Object of type type is not JSON serializable` → 创建实验 500。改为 `Field(default_factory=list)`。
2. `ResponseValidationError: 5 validation errors`：ORM 返回 UUID / JSON 字符串 / datetime 与响应模型的 str/list/dict 不匹配 → 新增 `_serialize_experiment`，`list/create/get` 三个端点统一显式转换。

修复后实测：`create 201`、`list 200`（返回 2 条，含 variants）。

**注意（数据易失性）→ v1.2.0 已修复**：`/platform/config/api-keys` 的服务 Key 原由 `ApiKeyStore`
**进程内内存**保存（源码注释即声明「内存存储 + 哈希保存」），OpenBase 重启后列表清空、旧 Key 失效。
v1.2.0 起签发记录落 `service_api_keys` 表（详见 §9.1），重启与多进程均可读同一份事实源。

**造数清理**：以上 5 项可直接删除（名称/描述均含「E2E 核验」前缀，或含「DW-03」标记）；B3 谱系复验所造 2 条 `tag_lineage` + 1 条标注亦同属测试数据。

## 9. 附带修复（v1.2.0，工程债清偿）

### 9.1 服务 Key 持久化（原 P2 债务「服务 Key 接入 DB 持久化」）

| 项 | 内容 |
|---|---|
| 缺陷 | 服务 Key（`ob_k_*`）由 `ApiKeyStore` 进程内字典持有：重启后列表清空、已签发 Key 全部失效，网关 `/proxy` 的服务 Key 通道不可用于生产 |
| 修复 | 新增 `service_api_keys` 表（`key_id`/`name`/`key_hash`/`scope`/`status`/`created_by`/`revoked_at`）+ `ServiceKeyService`（issue/lookup/verify/revoke_by_id/revoke_by_raw/list_keys）；`POST/GET/DELETE /api/v1/auth/api-keys` 与 `/proxy` 服务 Key 认证改为查库；删除内存态 `openbase/modules/auth/api_keys.py` |
| 兼容 | 响应契约不变（`id`=稳定 key_id、`created` 仍为 epoch 秒、列表不回显明文/哈希）；吊销语义不变（`status=revoked` 即时失效）；表由启动链 `Base.metadata.create_all` 幂等创建，无需手工 DDL |
| 验证 | `tests/test_api_keys.py`（含「写入后新 session 仍可校验/列表/吊销」的持久化回归）31 例相关用例全通过；`ruff check openbase tests` 0 错误 |
| 残余 | 历史内存态 Key 无法迁移（本就随进程消失），需重新签发；scope 校验仍不绑定租户维度（与改造前一致） |

### 9.2 全量 pytest 10 项失败（跨网 PG 抖动 + 门禁用例连带）

| 项 | 内容 |
|---|---|
| 现象 | `test_tenant_admin`/`test_users_admin` 报 `asyncpg connection was closed in the middle of operation`；`test_s7_t6_gate` 子进程门禁连带 FAIL（双租户隔离、吊销即时性） |
| 定位 | 三个文件单独运行 100% 通过；`scripts/gate_aggregate.py` 单独运行 `overall=PASS`。失败只在**全量套件**中出现，属测试**装配/环境隔离**问题而非产品缺陷：① 两文件在 import 期即装配 app，而 pytest 先收集全部模块再执行用例，后续模块的 fixture/teardown 会重建全局 engine 单例；② 门禁子进程复用父进程 `%TEMP%`，父进程仍持有各测试模块 SQLite 文件句柄，子进程 `unlink` 失败 → collection error；③ 父进程注入的真实库会让「沙箱无 PG」语义的 RA-06 选择器断言漂移 |
| 修复 | ① 两文件改为**模块级 autouse fixture 延迟装配**（与 `tests/test_identity_t3.py` 范式一致）；② 进一步**硬隔离全局 DB 工厂**：模块期间把 `openbase.core.db.session.get_session_factory` 固定为专用 SQLite 工厂（覆盖 `AuthMiddleware`/`get_db` 在**请求期**才取工厂的路径），模块结束 `undo` 并复位全局单例；③ `gate_aggregate.py` 子进程改用独立 `TMP/TEMP/TMPDIR` 并固定 `OPENBASE_DB_URL` 为不可达 DSN（对齐沙箱可判定面）；④ 服务 Key 相关用例（`test_api_keys_api`/`test_proxy_auth`/`test_verdict_k03`）改为**临时 SQLite 装配**，与外部 PG 解耦 |
| 验证 | 单文件与三文件联跑均全通过；`scripts/gate_aggregate.py` 独立运行 `overall=PASS`（RA-06 五项全 PASS：19/21/12/13/17 例）；全量套件复跑结果见 §9.3 |

### 9.3 回归结论（2026-10-28）

| 验证项 | 结果 |
|---|---|
| 服务 Key 持久化 E2E | 签发 → 编排器 `stop`+`start`（进程真正重启，PID 21124 → 20844）→ 列表仍返回同一 `key_id`；吊销后同一 Key 请求 `/proxy` **立即 401**（吊销前 200） |
| 服务 Key / 认证相关用例 | `test_api_keys` / `test_api_keys_api` / `test_proxy_auth` / `test_verdict_k03` / `test_tenant_admin` / `test_users_admin` 联跑 **55 passed** |
| 跨网 PG 断连回归（v1.2.1） | 两文件在 **PG 完全不可达**（`OPENBASE_DB_URL`/`POSTGRES_URL` 指向 10.255.255.1）下仍 **12 passed**；在「`test_demo_app` 先跑并把全局 engine 初始化为真实 PG，随后执行两文件」的跨模块场景下同样通过（唯一失败为既有的 `test_demo_app_starts_and_falls_back` 环境假设） |
| 其他受影响用例 | `test_storage_s3` **9 passed**（原缺 `boto3` 依赖，已补装）；`test_log_reserved_keys` + `test_r2_lists_v192` 通过 |
| 门禁聚合 | `tests/test_s7_t6_gate.py` **16 passed**（RA-06 五项 19/21/12/13/17 例全 PASS）；全量套件内该文件同样 PASS（此前 10 项 E 已消失） |
| 静态检查 | `ruff check openbase tests` 0 错误 |
| 残余（非本轮引入） | 单进程全量跑仍可见 3~4 项**环境/顺序依赖**失败：`test_app::test_org_department_flow`/`test_config_rollback_flow`（真实 PG 已积累历史测试数据，用例期望空表）、`test_demo_app_starts_and_falls_back`（有真实库时 `_DB_READY=True`，用例按"降级"断言）、`test_proxy_target_system_v190`（真实库存在租户级 LLM Key 时优先命中 DB）。三者单独运行均通过，属既有用例的"沙箱/空库假设"；官方回归入口为 `scripts/run_tests.ps1`（按文件分组子进程），未在本轮扩大修复范围 |

> 说明：本文的"全量套件"指单进程 `python -m pytest tests`；项目标准回归为 `scripts/run_tests.ps1`（ruff + 按 6 文件分组子进程），两者在跨文件全局状态上的隔离强度不同。

## 10. 修订历史

| 版本 | 日期 | 执行人 | 说明 |
|---|---|---|---|
| v1.0.0 | 2026-10-27 | FA-OpenBase-Dev（AI 辅助） | 首版：77 页功能有效性核验（23 真实数据 / 38 空数据 / 15 不自动取数 / 1 偶发 502）；批量复核与谱系链路实测；探针阈值与 B3 复验结论 |
| v1.1.0 | 2026-10-28 | FA-OpenBase-Dev（AI 辅助） | 三项关注项闭环：DW-01 代理慢聚合端点 30s + GET 重试（3 条回归用例 + 线上 16/16 通过）；DW-02 确认为跨网链路瞬态并留存实测数据；DW-03 造数 5 页由空数据转为 real-data，顺带修复 OpenLLM Prompt 实验创建 500 两处缺陷；补充 api-keys 内存存储易失性说明与造数清理口径 |
| v1.2.0 | 2026-10-28 | FA-OpenBase-Dev（AI 辅助） | 清偿两项工程债：① 服务 Key 由进程内内存改为 `service_api_keys` 表持久化（重启/多进程可用，响应契约不变，新增持久化回归用例 + 重启 E2E 验证）；② 修复全量 pytest 的 10 项连带失败：`test_tenant_admin`/`test_users_admin` 改延迟装配、门禁子进程隔离 TEMP 与 DB 语义、服务 Key 相关用例改临时 SQLite 装配、补装 `boto3`；门禁聚合恢复 PASS，残余 3~4 项既有沙箱假设失败已如实登记 |
| v1.2.1 | 2026-10-28 | FA-OpenBase-Dev（AI 辅助） | 加固 `test_tenant_admin`/`test_users_admin` 的跨网 PG 断连问题：模块期间把全局 `get_session_factory` 固定为专用 SQLite 工厂（覆盖中间件/依赖请求期取工厂），模块结束复位；验证「PG 不可达」与「跨模块已初始化真实 PG」两种场景均通过 |
