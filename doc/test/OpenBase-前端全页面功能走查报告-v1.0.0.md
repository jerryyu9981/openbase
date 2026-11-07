# OpenBase 前端全页面功能走查报告 - v1.0.0

## 文档元信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | OB-TEST-FE-WALKTHROUGH-v1.0.0 |
| 文档版本 | v1.0.0 |
| 文档状态 | [Review]（待人工批准） |
| 适用环境 | Dev（本机 127.0.0.1；共享基础设施 192.168.0.151） |
| 走查日期 | 2026-11-07 |
| 编制角色 | QA（测试工程师）／Dev（开发工程师） |
| 上游依据 | 《OpenBase-基础设施子系统全生命周期走查报告-v2.0.0》[Final]；《OpenBase-API接口设计文档-v1.4.10》 |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 | 状态 |
| --- | --- | --- | --- | --- |
| v1.0.0 | 2026-11-07 | QA／Dev | 首版：全栈 7 服务拉起、79 个前端页面逐页走查、字典/Agent/配置三类 CRUD 闭环验证、日志异常扫描与发现项登记 | [Review] |

---

## 1. 概述

### 1.1 走查目标

验证 OpenBase 全栈服务拉起后，**前端全部页面与核心功能在真实环境中可用**：页面可渲染、无运行时错误、核心 CRUD 形成闭环、跨服务链路真实连通。

### 1.2 走查范围

- 服务范围：openllm(8001)、openrag(8010)、openmemory(8020)、oidc-idp(8090)、dps(8030)、openbase(8000)、frontend(5173)。
- 页面范围：平台域、模型中心、知识库、记忆管理、画像/DPS、个人设置，共 **79 个静态可直达页面**（不含 `:id` 动态详情页）。
- 功能范围：登录鉴权、列表/详情渲染、字典类型与字典项 CRUD、Agent 主体 CRUD（含密钥吊销）、配置读写删除、OIDC 授权页。

### 1.3 走查方法

1. 通过 `scripts/service-orchestrator.ps1 -Action start` 按拓扑序拉起全栈，采集健康检查与冷启动耗时。
2. 以 Playwright（Chromium）登录 `admin` 后**逐页导航**，采集 HTTP 状态、`console.error`、`pageerror`、页面错误文案与正文渲染长度。
3. 对内容较短页面做**二次抽查**（等待 4~8s 后读取主区域文本与空态组件），区分「空态合理」与「白屏异常」。
4. 以真实 API 调用验证字典、Agent、配置三类资源的**创建 → 读取 → 删除 → 删除后确认**闭环。
5. 扫描服务日志中的 `Traceback`／`ERROR`／`500`，区分阻断项与非阻断观察项。

---

## 2. 全栈服务拉起结果

所有服务由统一编排器启动，最终状态 **7/7 健康**：

| 服务 | 端口 | 健康 | PID | 冷启动耗时 |
| --- | --- | --- | --- | --- |
| openllm | 8001 | ✅ | 26524 | 24s |
| openrag | 8010 | ✅ | 17864 | 26s |
| openmemory | 8020 | ✅ | 34936 | 32s |
| oidc-idp | 8090 | ✅ | 13840 | 22s |
| dps | 8030 | ✅ | 45396 | 8s |
| openbase | 8000 | ✅ | 20996 | 22s |
| frontend | 5173 | ✅ | 5248 | 21s |

数据面前置校验全部通过：PostgreSQL（primary 192.168.0.151:5432，424ms）、Redis(6380)、Qdrant(6333)、Neo4j(7687)、MinIO(9000)。

`GET /api/v1/auth/login`（admin）登录成功并签发 access_token；前端 `http://127.0.0.1:5173` 返回 200。

---

## 3. 页面走查结果

### 3.1 总体结果

| 指标 | 结果 |
| --- | --- |
| 走查页面数 | **79** |
| HTTP 状态 ≥ 400 的页面 | **0** |
| 出现 `console.error` 的页面 | **0** |
| 出现 `pageerror`（未捕获异常）的页面 | **0** |
| 命中「加载失败／请求失败／页面不存在／500」等错误文案的页面 | **0** |
| 登录后访问被错误重定向 | **0** |

### 3.2 分域覆盖

| 域 | 页面数 | 结果 |
| --- | --- | --- |
| platform/observability | 14 | 全部 200，无错误信号 |
| openllm（模型中心/应用/对话分析） | 11 | 全部 200，无错误信号 |
| platform/governance | 10 | 全部 200，无错误信号 |
| portrait/dps | 9 | 全部 200，无错误信号 |
| platform/identity | 9 | 全部 200，无错误信号 |
| memory | 6 | 全部 200，无错误信号 |
| platform/developers | 6 | 全部 200，无错误信号 |
| platform/config | 5 | 全部 200，无错误信号 |
| portrait | 5 | 全部 200，无错误信号 |
| knowledge | 2 | 全部 200，无错误信号 |
| dashboard / personal | 2 | 全部 200，无错误信号 |

### 3.3 渲染真实性抽查

对正文较短（空态或表单页）的页面二次抽查，确认**空态合理、表单完整，无白屏**：

| 页面 | 主区域实际内容 | 判定 |
| --- | --- | --- |
| /dashboard | 「已启用模块 5、平台用户数 114、24h 调用量 164、24h 费用 $0.00」+ 动态模块列表 | 真实数据渲染 |
| /knowledge/list | 真实知识库「社区矫正」（文档 0 · 策略 structured），含「进入／删除」操作 | 真实数据渲染 |
| /personal/settings | 资料编辑、修改密码、通知偏好三组完整表单 | 正常 |
| /openllm/playground | 模型 `qwen2.5:0.5b` 已选中，含发送与空态引导 | 正常 |
| /openllm/models/market | 「无匹配模型，共 0 条」空态 + 查询控件 | 空态合理 |
| /openllm/favorites | 「0 个收藏模型／默认收藏分组为空」 | 空态合理 |
| /portrait/dps/templates | 模板族表格 + 「暂无模板族」空态 + 新建入口 | 空态合理 |
| /platform/observability/app-calls | 表头、筛选、分页与「暂无调用记录」空态 | 空态合理 |
| /memory/search | 查询词/策略/数量控件 + 「输入查询词开始搜索」 | 正常 |
| /platform/config/dicts | 字典类型 `gender`／`status`，字典项表格与删除入口 | 真实数据渲染 |
| /platform/identity/agents | Agent 列表（历史 smoke 主体）与删除/密钥操作 | 真实数据渲染 |

---

## 4. 核心功能闭环验证

### 4.1 字典（类型 + 字典项）

| 步骤 | 调用 | 结果 |
| --- | --- | --- |
| 列表 | `GET /api/v1/dicts` | 返回 2 个类型 |
| 新建类型 | `POST /api/v1/dicts` `{code,name}` | 成功 |
| 新建字典项 | `POST /api/v1/dicts/{code}/items` | 成功，返回 id |
| 列表字典项 | `GET /api/v1/dicts/{code}/items` | 1 条 |
| 删除字典项 | `DELETE /api/v1/dicts/items/{id}` | 成功 |
| 删除类型 | `DELETE /api/v1/dicts/{code}` | 成功 |
| 删除后确认 | `GET /api/v1/dicts/{code}/items` | 已不可用（闭环成立） |

### 4.2 Agent 主体

| 步骤 | 调用 | 结果 |
| --- | --- | --- |
| 列表 | `GET /api/v1/identity/agents?page&page_size` | 返回裸数组，分页正常 |
| 新建 | `POST /api/v1/identity/agents` | 返回 `agent_id` 与 `api_key`（明文仅一次） |
| 删除（软删） | `DELETE /api/v1/identity/agents/{id}` | `status=0`，`revoked_keys=1` |
| 删除后确认 | 列表按 `status` 过滤 | 状态为 0，不再作为有效主体 |

> 走查过程中创建的 2 个临时 Agent 已全部软删并吊销密钥，无残留有效测试主体。

### 4.3 配置中心

| 步骤 | 调用 | 结果 |
| --- | --- | --- |
| 列表 | `GET /api/v1/configs` | 正常返回 |
| 写入 | `POST /api/v1/configs` `{key,value,level}` | 成功 |
| 读取 | `GET /api/v1/configs/{key}` | 返回值与写入一致 |
| 删除 | `DELETE /api/v1/configs/{key}` | `deleted=true`，`restored_default=false` |
| 删除后确认 | `GET /api/v1/configs/{key}` | 返回 `value=null`（覆盖值已清除，非 404） |

结论：配置「删除 = 清除覆盖值并回退默认」，删除真实生效；对不存在键的 GET 返回 200 + `null`，属既有契约（见发现项 OBS-02）。

### 4.4 OIDC 登录

| 步骤 | 调用 | 结果 |
| --- | --- | --- |
| 授权页 | `GET 8090/authorize?client_id=openbase-gw&...` | 200，返回登录表单 |
| 非法 client_id | 同上但 client 错误 | 400 `unknown client_id`（防护生效） |

---

## 5. 质量与可观测性

### 5.1 前端运行时

- 79 页无未捕获异常、无控制台错误、无 4xx/5xx 页面响应。
- 仅登录前访问 `/auth/me` 产生一次预期内 HTTP 401（未登录态），非缺陷。

### 5.2 服务日志扫描（近 40 分钟）

| 服务 | 日志信号 | 判定 |
| --- | --- | --- |
| openbase | `passlib` 读取 bcrypt 版本告警（trapped，登录正常） | 非阻断，建议后续对齐 bcrypt 版本 |
| openbase | 登录前 `/auth/me` 401 审计记录 | 预期行为 |
| dps | 「报表概览真实聚合失败，降级全表：syntax error at or near PRAGMA」 | 跨仓缺陷（DPS），见 OBS-03 |
| openllm | 「Failed to save audit log: value too long for character varying」 | 跨仓缺陷（OpenLLM），见 OBS-04 |
| openrag | 「scope_exemption 表读取失败（降级为空）」 | 降级可接受，建议补表或迁移 |
| oidc-idp / openmemory / frontend | 仅 PowerShell 包装器噪声，无业务错误 | 正常 |

### 5.3 数据质量观察

`gender` 字典存在 **5 条完全相同的字典项**（id=1,2,3,5,6，均为「男/M/1」，其中 id=4 已缺失）。推断为历史联调遗留脏数据，非接口缺陷；页面如实展示。建议清理为 1 条（未在本次走查中删除，避免未经授权改动业务数据）。

---

## 6. 发现项与处置

| 编号 | 类型 | 描述 | 影响 | 处置建议 | 状态 |
| --- | --- | --- | --- | --- | --- |
| OBS-01 | 数据质量 | `gender` 字典 5 条重复项 | 字典下拉出现重复选项 | 清理重复项，保留 1 条 | 待裁定 |
| OBS-02 | 契约观察 | `GET /configs/{key}` 对不存在键返回 200 + `value:null` | 前端需以 null 判断，不能依赖 404 | 明确契约文档；如需 404 语义再改 | 已记录 |
| OBS-03 | 跨仓缺陷 | DPS 报表概览聚合使用 `PRAGMA`（SQLite 语法）打到 PostgreSQL，降级全表 | 报表概览数据不准/降级 | 在 DPS 仓修正方言判断 | 待跨仓处置 |
| OBS-04 | 跨仓缺陷 | OpenLLM 审计日志写入超长（varchar 截断报错） | 审计记录丢失 | 在 OpenLLM 仓扩容字段或截断入参 | 待跨仓处置 |
| OBS-05 | 依赖告警 | passlib 读取 bcrypt `__about__` 失败 | 无功能影响 | 升级/对齐 passlib 与 bcrypt 版本 | 已记录 |

**阻断项：0**。以上均为非阻断发现项，不影响「前端页面与核心功能真实可用」的结论。

---

## 7. 结论

1. 全栈 **7 个服务全部健康**拉起，数据面依赖（PG/Redis/Qdrant/Neo4j/MinIO）探测通过。
2. **79 个前端页面全部可达并正常渲染**，0 个控制台错误、0 个未捕获异常、0 个 4xx/5xx。
3. 字典、Agent、配置三类核心资源的**创建→读取→删除→删除后确认**闭环均真实成立；OIDC 授权页可用且非法参数被拒。
4. 页面展示的是**真实数据**（用户数、调用量、知识库、模型、Agent 列表），空态页面均给出明确引导，无白屏。
5. 登记的 5 项发现均为数据质量、契约观察或跨仓问题，**不阻断**本次前端可用性结论；OBS-03／OBS-04 需在 DPS／OpenLLM 仓另行处置。

---

## 8. 附录

### 8.1 走查页面清单（79）

- dashboard：`/dashboard`
- openllm：`/openllm/models`、`/openllm/models/local`、`/openllm/models/comparison`、`/openllm/models/market`、`/openllm/favorites`、`/openllm/apps`、`/openllm/apps/new`、`/openllm/playground`、`/openllm/conversations`、`/openllm/recommend`、`/openllm/reports-trend`
- knowledge：`/knowledge/list`、`/knowledge/chat`
- memory：`/memory/list`、`/memory/search`、`/memory/sessions`、`/memory/graph`、`/memory/decay`、`/memory/write`
- portrait：`/portrait/overview`、`/portrait/list`、`/portrait/search`、`/portrait/tags`、`/portrait/rules`
- portrait/dps：`/portrait/dps/templates`、`/portrait/dps/template-packages`、`/portrait/dps/lineage`、`/portrait/dps/measures`、`/portrait/dps/scoring-types`、`/portrait/dps/annotation-adapters`、`/portrait/dps/annotation-templates`、`/portrait/dps/tags`、`/portrait/dps/templates/new`
- platform/identity：`/platform/identity/tenants`、`/platform/identity/roles`、`/platform/identity/org`、`/platform/identity/workspaces`、`/platform/identity/auth-ext`、`/platform/identity/users`、`/platform/identity/agents`、`/platform/identity/memory-admin`、`/platform/identity/dps-permissions`
- platform/config：`/platform/config/general`、`/platform/config/dicts`、`/platform/config/modules`、`/platform/config/api-keys`、`/platform/config/rate-limits`
- platform/observability：`/platform/observability/logs`、`/test-records`、`/monitoring`、`/monitoring/costs`、`/monitoring/alerts`、`/monitoring/traces`、`/monitoring/budgets`、`/gpu`、`/usage`、`/billing`、`/service-discovery`、`/gateway-test`、`/app-calls`、`/dps-monitor`
- platform/developers：`/platform/developers/docs`、`/edgerouter`、`/plugins`、`/dps-api`、`/knowledge-admin`、`/knowledge-console`
- platform/governance：`/platform/governance/providers`、`/model-categories`、`/routing`、`/circuit-breakers`、`/deploy`、`/downloads`、`/tool-calls`、`/ab-tests`、`/prompt-templates`、`/prompt-experiments`
- personal：`/personal/settings`

### 8.2 证据与工具

- 编排器启动日志：`logs/` 及各服务 `logs/<service>/<service>-20261107.*`
- 页面走查原始数据：本次走查生成的逐页状态、错误与控制台采集结果（本地临时产物，未入库）
- 复跑方式：以 admin 登录后按 8.1 清单逐页访问；CRUD 验证按 §4 调用序列执行

### 8.3 未覆盖说明

- `:id` 动态详情页（如模型详情、知识库详情、会话详情）需真实实体 ID，本次以列表页与「进入」入口可用性间接验证。
- 需要外部模型推理的对话生成结果未做长文质量评估，仅验证调用链路与页面交互可用。
