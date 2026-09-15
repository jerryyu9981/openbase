# OpenBase API 接口设计文档 - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.2.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev（后端）/ FA-OpenBase-Dev（前端契约） |
| 创建日期 | 2026-09-15 |
| 存放 | doc/design/ |

---

## 1. 设计范围与依据

| 项 | 内容 |
|----|------|
| 范围 | **（v1.1.0 修订）**本版本新增 **4 个端点**：①~③ 只读三端点（`/logs/search`、`/logs/facets`、`/logs/export`）；④ **模块状态写端点（`PATCH /api/v1/modules/{id}`）**；`/logs/*` 的 `source` 枚举新增 **`repo_log`（四仓日志，第四类源）**；复用 1 个既有端点；**不修改任何既有端点契约**（`GET /api/v1/modules` 保持只读语义） |
| 依据 | 需求文档 §6.2/§6.3（接口规范与错误码）；《系统架构设计文档-v1.4.6》§2/§3；`api-design`；`AGENTS.md`（错误码与分层） |
| 统一前缀 | `/api/v1`（经网关；前端 `http.ts` 的 `baseURL='/api/v1'`） |
| 统一响应体 | `{code, message, detail, request_id}`（错误）；成功端点直接返回业务对象 |
| 认证/授权 | 三端点统一 `Depends(require_permission("log:read"))` |

---

## 2. 统一数据契约 `LogEntry`

> **契约唯一事实源**：前端不自行派生分类字段，全部以后端返回为准。

| # | 字段 | 类型 | 必需 | 说明 | `l1_file` 来源 | `audit_db` 来源 | `test_record` 来源 |
|:-:|------|------|:----:|------|---------------|----------------|-------------------|
| 1 | `ts` | string(ISO8601) | ✅ | 发生时间 | `ts` | `created_at` | 记录时间 |
| 2 | `source` | enum | ✅ | 数据源标识 | 固定 `l1_file` | 固定 `audit_db` | 固定 `test_record`｜（**v1.1.0 新增** 固定 `repo_log`，含四仓） |
| 3 | `module` | enum | ✅ | 业务模块（派生） | path 派生 | path/`action` 派生 | 固定 `testing` |
| 4 | `operation` | enum | ✅ | 操作类型（派生） | method+path | method+path | 结果动作映射 |
| 5 | `result` | enum | ✅ | 结果状态 | `status_code` 区间 | `status_code` 或 `detail.status` | `result` |
| 6 | `request_id` | string\|null | — | 请求 ID | ✅ | ✅ | 关联 `run_id` |
| 7 | `method` | string\|null | — | HTTP 方法 | ✅ | ✅ | `null` |
| 8 | `path` | string\|null | — | 路径/动作 | ✅ | ✅ | 端点或动作名 |
| 9 | `status_code` | int\|null | — | 状态码 | ✅ | ✅ | `null` |
| 10 | `duration_ms` | int\|null | — | 耗时 | ✅ | 折算或 `null` | ✅ |
| 11 | `operator_id` | string\|null | — | 操作人 | `actor` | `user_id` | 记录人 |
| 12 | `tenant_id` | string\|null | — | 租户 | ✅ | ✅ | `null` |
| 13 | `ip_address` | string\|null | — | 客户端 IP | ✅ | ✅ | `null` |
| 14 | `case_id` | string\|null | — | 测试用例号 | ✅ | `detail.case_id` | ✅ |
| 15 | `step_id` | int\|string\|null | — | 测试步骤 | ✅ | `detail.step_id` | ✅ |
| 16 | `run_id` | string\|null | — | 测试轮次 | ✅ | `detail.run_id` | ✅ |
| 17 | `action` | string\|null | — | 审计动作 | `null` | ✅（`api.request`/`proxy.outbound`/`identity.purge`/`log.export`） | `null` |
| 18 | `summary` | object\|null | — | 摘要（**脱敏后**） | `resp_*`/`upstream_*` 裁剪 | `detail` 裁剪 | 记录字段 |

**字段齐备约束**：1~5 为**必需字段**，任何源不得返回 `null`（无法判定时按派生规则落 `other`/`unknown`）→ AC-146-01-2 以三源 schema 断言锁定。

---

## 3. 端点规范

### 3.1 `GET /api/v1/logs/search`

| 项 | 内容 |
|----|------|
| 权限 | `log:read` |
| 用途 | 统一检索（分类 + 关键字 + 时间窗 + 三元组 + 分页） |

**请求参数**

| 参数 | 类型 | 必需 | 默认 | 约束 |
|------|------|:----:|------|------|
| `source` | enum | ✅ | — | `l1_file` \| `audit_db` \| `test_record` \| **`repo_log`**；非法 → 400 `PARAM_400` |
| `module` | enum | — | 全部 | `identity`/`dps`/`rag`/`memory`/`llm`/`gateway`/`testing`/`other`（可重复=多选，OR；与其它维度 AND） |
| `operation` | enum | — | 全部 | `auth_login`/`read`/`write`/`delete`/`config`/`proxy` |
| `result` | enum | — | 全部 | `success`/`client_error`/`server_error`/`unknown` |
| `operator` | string | — | 全部 | 操作人 ID（可重复=多选） |
| `q` | string | — | — | 关键字；对 `path`/`request_id`/`operator_id`/`ip_address` 包含匹配（大小写不敏感）；**≤200 字符** |
| `from` / `to` | string(ISO8601) | — | 近 24h | `from > to` → 400 |
| `case_id` / `run_id` | string | — | — | 三元组过滤 |
| `step_id` | int\|string | — | — | 三元组过滤（兼容 int/str，对齐既有口径） |
| `page` | int | — | 1 | ≥1 |
| `page_size` | int | — | 20 | 1~100；`>100` → 400 |

**响应 200**

```json
{
  "items": [ /* LogEntry[]，见 §2 */ ],
  "total": 137,
  "page": 1,
  "page_size": 20,
  "source": "l1_file",
  "truncated": false
}
```

| 字段 | 说明 |
|------|------|
| `total` | 当前筛选条件下的**命中总数**（用于分页）；受扫描上限影响时标注为"已扫描范围内" |
| `truncated` | `true` = 触及扫描上限（≤2 分片 / ≤200,000 行），结果**不完整**，UI 必须显著提示（AC-146-04-3） |

**排序**：`ts` **倒序**；`ts` 相同按 `request_id` 升序（`request_id` 缺失时按 `source`+`path` 稳定次序）→ 保证跨页不重不漏（AC-146-04-2）。

**降级**：单源不可用时该源返回 `items=[]` + 错误提示，**不影响其他源**（AC-146-01-4；由前端按 `source` 单值请求天然隔离）。

### 3.2 `GET /api/v1/logs/facets`

| 项 | 内容 |
|----|------|
| 权限 | `log:read` |
| 用途 | 返回当前筛选条件下的分类计数，驱动左侧分类导航 |
| 请求参数 | 与 `/logs/search` **同集合**（除 `page`/`page_size`） |

**响应 200**

```json
{
  "source": "l1_file",
  "module":   { "identity": 12, "memory": 41, "other": 3 },
  "operation":{ "read": 30, "write": 18, "config": 8 },
  "result":   { "success": 48, "client_error": 6, "server_error": 2 },
  "operator": { "7": 22, "42": 34 },
  "truncated": false
}
```

**一致性约束**：`module`/`operation`/`result` 各取值计数之和必须等于同条件 `/logs/search` 的 `total`（AC-146-02-4，审计互证口径）。

### 3.3 `GET /api/v1/logs/export`

| 项 | 内容 |
|----|------|
| 权限 | `log:read`（仅管理员） |
| 用途 | 按筛选条件导出，**留痕** |
| 请求参数 | 与 `/logs/search` 同集合（除 `page`/`page_size`）+ `format` |

| 参数 | 类型 | 必需 | 默认 | 约束 |
|------|------|:----:|------|------|
| `format` | enum | — | `csv` | `csv` \| `json` |

**响应**

| 场景 | 响应 |
|------|------|
| 成功 | 200；`Content-Type: text/csv; charset=utf-8` 或 `application/json`；`Content-Disposition: attachment; filename="logs-<source>-<ts>.<ext>"`；**列/字段与 §2 一致** |
| CSV 细节 | 首行表头（§2 字段名）；UTF-8；含 `\ufeff` BOM（Excel 兼容）；`summary` 序列化为紧凑 JSON 字符串 |
| 文件名 `ts` 格式（v1.2.0 定案） | `<ts>` 取 `YYYYMMDD-HHMMSS`，**本地时区**；保证 ASCII、无 Windows 非法字符、可按字典序排序（Step 3 定案） |
| 超限 | 命中数 > 10000 → 400 `PARAM_400`，`detail` 含 `{matched, limit}` 供前端提示收窄 |
| 留痕 | 每次导出写 1 条 `audit_logs(action="log.export")`，`detail={actor, source, filters, row_count, format}`（**不记录导出内容**）→ AC-146-06-4 |
| 留痕失败 | **不影响导出**：`WARN` 记录并继续返回文件（降级语义，见系统架构 ADR-146-04） |
| 留痕通道**被显式关闭**（v1.2.0 定案） | `OPENBASE_AUDIT_DB_PERSIST=0` 语义为「审计留痕通道不可用」→ 导出**拒绝执行**并返回 503 `BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE`（fail-closed，避免「导出已发生 + 留痕缺失」）。与 §3.4 模块开关口径对称（Step 3 定案） |

### 3.4 `PATCH /api/v1/modules/{id}`（v1.1.0 新增）

| 项 | 内容 |
|----|------|
| 权限 | **`module:manage`**（仅管理员） |
| 用途 | 模块启用/停用（模块开关管理页 `/platform/config/modules`） |
| 路径参数 | `id`（模块标识，取值来自 `GET /api/v1/modules` 返回的 `id`） |

**请求体**

```json
{ "status": "enabled" }
```

| 字段 | 类型 | 必需 | 约束 |
|------|------|:----:|------|
| `status` | enum | ✅ | `enabled` \| `disabled`；非法 → 400 `PARAM_400` |

**响应 200**

```json
{
  "id": "openllm",
  "status": "disabled",
  "previous_status": "enabled",
  "effective": "next_login",
  "request_id": "req-a19f2c3d4e5f"
}
```

| 字段 | 说明 |
|------|------|
| `status` | 变更后的状态 |
| `previous_status` | 变更前状态（供前端展示与留痕核对） |
| `effective` | **固定 `next_login`** —— **不承诺热生效**（前端模块路由在下次登录/刷新后按新状态装载；见系统架构 ADR-146-07） |

**副作用（强制）**

| 项 | 要求 |
|----|------|
| 留痕 | 每次变更写 1 条 `audit_logs(action="module.switch")`，`detail={operator_id, module_id, previous_status, status}` → AC-146-15-3 |
| 幂等 | 目标状态与当前状态相同 → **200 且不重复留痕**（或留痕标注 `no_change=true`，二者在 Step 3 择一并写入实现说明）→ **v1.2.0 定案：采用「200 且不重复留痕」** |
| 留痕失败处置（v1.2.0 定案） | **变更失败并回滚**（fail-closed）：路径改为**先写留痕、后变更状态**；留痕写失败（含 `OPENBASE_AUDIT_DB_PERSIST=0` 通道不可用）→ 模块状态**保持原值**并返回 503 `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE`。理由：平台级高危变更若「状态已变 + 审计缺失」则不可回溯（与 §3.3 导出留痕通道口径对称） |
| 状态持久化（v1.2.0 定案） | 启停状态持久化至 `dynamic_modules`（`status` 字段，幂等 upsert）；读取优先 DB、缺行回退出厂值；DB 不可用时回退内存并 `WARN`（不改变 `effective=next_login` 语义） |
| 语义不变 | **不改动模块 `id`/`route_prefix`/`permission` 语义**；不新增模块；不改变"按权限过滤模块"的既有口径 → AC-146-15-4 |
| 降级路径 | 若注册表为**纯配置驱动**且改动成本过高 → 本端点**降级为不提供**，页面改为只读展示，并在交付说明显式标注（系统架构 ADR-146-07 ②）。**v1.2.0 实测结论：不适用**（`dynamic_modules` 表随既有 `create_all` 初始化链建表，改造风险可控，故按完整实现交付） |

---

## 4. 分类枚举与派生规则（契约化）

> 由后端 `derivation.py` 单点实现（ADR-146-02）；**前端不得重复实现**。以下为契约表，Step 3 以单元测试锁定。

### 4.1 `module`（按 path 前缀）

| 前缀（按最长匹配优先） | module |
|------------------------|--------|
| `/api/v1/auth`、`/api/v1/identity`、`/api/v1/users`、`/api/v1/tenants`、`/oidc` | `identity` |
| `/api/v1/dps-proxy` | `dps` |
| `/api/v1/rag-proxy` | `rag` |
| `/api/v1/memory-proxy` | `memory` |
| `/api/v1/llm-proxy` | `llm` |
| `/api/v1/gateway`、`/api/v1/system`、`/api/v1/modules`、`/api/v1/logs` | `gateway` |
| `/api/v1/test-runs`、`/api/v1/test-records` | `testing` |
| 其他 | `other` |

### 4.2 `operation`

| 判定（顺序优先） | operation |
|------------------|-----------|
| path 命中 `/auth/login` 或 `/oidc/**` | `auth_login` |
| `method == DELETE` | `delete` |
| path 含 `config` \| `settings` \| `switch` | `config` |
| path 含 `-proxy` | `proxy` |
| `method == GET` | `read` |
| `method ∈ {POST, PUT, PATCH}` | `write` |
| 其他 | `read`（兜底；`action` 存在但无 method 时按动作语义映射） |

### 4.3 `result`（状态码区间）

| 状态码 | result |
|--------|--------|
| 200~299 | `success` |
| 400~499 | `client_error` |
| 500~599 | `server_error` |
| 缺失/不可判定 | `unknown` |

> `audit_db` 的 `action=proxy.outbound` 无顶层状态码时取 `detail.status`；测试记录源直接取 `result` 字段（取值 `PASS/FAIL/BLOCKED/SKIPPED` 映射为 `success`/`server_error` 语义 → **按记录语义映射**：`PASS`→`success`，其余→`client_error`（可人工复核））。

### 4.4 `repo_log` 源的 module 派生（v1.1.0 新增）

> 四仓日志的 `module` **不由 path 派生**，而由**采集目录名（svc）显式映射**得出（避免与 §4.1 的 path 前缀规则混淆）。

| svc 目录名（`logs/{svc}/`） | 映射 `module` | `source` | 说明 |
|---------------------------|:------------:|:--------:|------|
| `dps` | `dps` | `repo_log` | DPS 画像 |
| `openrag` | `rag` | `repo_log` | **注意 svc 名为 `openrag`，module 名为 `rag`**（非同名） |
| `openmemory` | `memory` | `repo_log` | svc 名与 module 名不同 |
| `openllm` | `llm` | `repo_log` | svc 名与 module 名不同 |

**契约约束**：① 该映射表为**显式常量表**并置于后端单点（建议与 §4.1 派生规则同址），**禁止硬编码散落**；② 出现未知 svc 目录 → 该目录**不纳入** `repo_log` 检索（避免把无关目录当日志读），并记录 `WARN`；③ `operation`/`result` 仍按 §4.2/§4.3 规则从四仓日志字段派生（四仓 JSONL 已含 `method`/`status_code`）。

---

## 5. 错误码

| 场景 | `code` | HTTP | `detail` 示例 |
|------|--------|:----:|---------------|
| `source` 非法 | `PARAM_400` | 400 | `{"field":"source","allowed":["l1_file","audit_db","test_record"]}` |
| `page_size` 越界 | `PARAM_400` | 400 | `{"field":"page_size","max":100}` |
| 时间窗非法（`from > to`） | `PARAM_400` | 400 | `{"field":"from/to"}` |
| 导出超限 | `PARAM_400` | 400 | `{"matched":15320,"limit":10000}` |
| 关键字超长 | `PARAM_400` | 400 | `{"field":"q","max_length":200}` |
| 未认证 | `AUTH_401` | 401 | — |
| 无 `log:read` | `PERM_403` | 403 | `{"required":"log:read"}` |
| **无 `module:manage`**（v1.1.0） | `PERM_403` | 403 | `{"required":"module:manage"}` |
| **模块 `id` 不存在**（v1.1.0） | `PARAM_404` | 404 | `{"module_id":"unknown","allowed":["openllm","knowledge","memory","portrait","gateway"]}` |
| **`status` 取值非法**（v1.1.0） | `PARAM_400` | 400 | `{"field":"status","allowed":["enabled","disabled"]}` |
| 数据源不可用 | `SYS_503` | 503 | `{"source":"audit_db"}` |
| **导出：留痕通道不可用**（v1.2.0） | `BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE` | 503 | `{"reason":"audit persist disabled"}` |
| **模块开关：留痕失败**（v1.2.0） | `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE` | 503 | `{"module_id":"openllm","reason":"..."}` |
| 未预期 | `SYS_500` | 500 | — |

统一错误体：`{code, message, detail, request_id}`。

---

## 6. 分页、排序与截断语义（汇总）

| 项 | 契约 |
|----|------|
| 分页 | 服务端分页；`page` 从 1 起；`page_size` 默认 20 / 上限 100 |
| 排序 | `ts` 倒序 → `request_id` 升序（稳定） |
| 总数 | `total` = 当前条件命中数（在扫描上限内） |
| 截断 | `truncated=true` 表示结果不完整；**响应仍为 200**（不是错误），UI 必须提示 |
| 空结果 | `items=[]` + `total=0` + 200（区分"无数据"与"条件未命中"由前端按 `total` 与筛选有无判断） |

---

## 7. 复用与集成

| 项 | 内容 |
|----|------|
| 复用端点 | `GET /api/v1/test-runs/{run_id}/summary`（测试记录源明细，前端"测试记录"页已在用） |
| 前端调用层 | 新增 `openbase-ui/src/core/api/logs.ts`（对标既有 `core/api/*.ts`），封装三端点类型 |
| 既有契约 | **零修改**（不新增/不改动任何既有端点字段与错误码） |
| 外部系统 | 不涉及 |

---

## 8. 前后端契约对齐（2.9 衔接点）

| 检查项 | 结果 |
|--------|:----:|
| 端点路径一致 | ✅ 前端 `core/api/logs.ts` 路径 ↔ 本文档 §3 一致（`/logs/search`、`/logs/facets`、`/logs/export`） |
| 请求参数命名一致 | ✅ 前后端统一使用 `snake_case`（`page_size`、`case_id`、`run_id`、`step_id`） |
| 响应字段一致 | ✅ 前端类型 `LogEntry` ↔ §2 18 字段一一对应 |
| 分类枚举一致 | ✅ 前端下拉/导航选项来自 §4 枚举表（不硬编码额外取值） |
| 错误码一致 | ✅ 前端按 §5 生成提示文案；`PARAM_400` 的 `detail.field` 用于定位表单项 |
| 分页语义一致 | ✅ 前端使用服务端分页；`truncated` 有独立提示位 |

---

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | AD-OpenBase-Dev | 初始版本：3 新端点契约（search/facets/export）+ 统一 `LogEntry` 18 字段 × 三源映射表 + 分类派生契约表（module/operation/result）+ 9 项错误码 + 分页/排序/截断语义 + 前后端契约对齐 6 项；既有端点零修改 |
| v1.1.0 | 2026-09-15 | AD-OpenBase-Dev | **VC-013 + VC-014 回溯重出（设计增补轮）**：① §1 范围由「3 个只读端点」扩为 **4 个端点**（新增模块状态写端点）并声明 `source` 新增 `repo_log`；② §2 `source` 枚举新增 **`repo_log`**（四仓日志）；③ §3.1 `source` 参数约束同步；④ **新增 §3.4 `PATCH /api/v1/modules/{id}`**（权限 `module:manage`、请求体 `status`、响应含 `previous_status` 与 `effective=next_login`、**强制留痕 `module.switch`**、幂等口径、**只读降级路径**）；⑤ **新增 §4.4 `repo_log` 源的 module 派生**（svc↔module **显式映射表**，含 `openrag`→`rag` 等**非同名**提示；未知 svc 不纳入检索）；⑥ §5 错误码新增 3 项（`module:manage` 403 / 模块不存在 404 / `status` 非法 400） |
| v1.2.0 | 2026-09-15 | AD-OpenBase-Dev | **Step 3 定案回写（编码阶段设计-实现对齐）**：① §3.3 新增「文件名 `ts` 格式定案」（`YYYYMMDD-HHMMSS`，本地时区）与「留痕通道被显式关闭」口径（`OPENBASE_AUDIT_DB_PERSIST=0` → fail-closed 503）；② §3.4 三项定案：幂等采用「200 且不重复留痕」、**留痕失败处置=变更失败并回滚**（先留痕后变更，失败返回 503）、**状态持久化至 `dynamic_modules`**，并实测结论「只读降级路径不适用」；③ §5 错误码新增 2 项（`BIZ_LOG_EXPORT_AUDIT_UNAVAILABLE` / `BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE`，均 503）；④ 依据：设计评审记录 §9「带入 Step 3 的必办项 ③」与 Stage2 阶段审计 §7（`module.switch` 留痕失败口径 Step 3 定案） |
