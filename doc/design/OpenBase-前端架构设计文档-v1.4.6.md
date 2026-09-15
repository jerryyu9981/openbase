# OpenBase 前端架构设计文档 - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.1.0 |
| 状态 | [Review] |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-09-15 |
| 存放 | doc/design/ |

---

## 1. 范围与依据

| 项 | 内容 |
|----|------|
| 范围 | 统一前端（`openbase-ui`）的**增量设计**：新增 1 个页面、1 个 API 模块、1 条重定向；**不改动既有架构**（目录结构、构建、请求层、样式体系均沿用） |
| 依据 | 需求文档 §10；《UI设计文档-v1.4.6》；《API接口设计文档-v1.4.6》§3/§8；既有 `openbase-ui/src` 结构与 `core/api/*.ts` 约定 |

---

## 2. 前端结构增量（唯一新增面）

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/pages/platform/{identity,config,observability,developers}/**` | **新增目录** | **平台管理四域页面**（ADR-146-05）：承接迁出的 15 项全局组件，使 `modules/*/pages/` 只含本模块特色页 |
| `src/pages/personal/SettingsView.vue` | 新增（迁移） | 个人设置归位（原 `/openllm/settings`） |
| `src/pages/platform/config/ModuleSwitchView.vue` | **新增** | 模块开关管理页（`module:manage`；含启用/停用 + `effective=next_login` 提示 + 留痕说明） |
| `src/pages/platform/observability/LogsView.vue` | 新增（迁移） | 日志中心主页面（原设计于 `src/pages/LogsView.vue`；按新 IA 归入可观测与审计域） |
| `src/core/api/logs.ts` | 新增 | 端点封装 + 类型定义；**`source` 枚举新增 `repo_log`** |
| `src/core/api/modules.ts` | **新增** | `PATCH /api/v1/modules/{id}` 封装（模块开关） |
| `src/core/router/index.ts` | 修改 | 注册平台管理四域 + 个人路由；**全量旧路径重定向**（见 §3.1 映射表）；新增模块开关页路由（`meta.permission='module:manage'`） |
| `src/core/router/legacyRedirects.ts` | **新增（建议）** | **重定向映射表集中定义**（一处维护，便于审计与 E2E 遍历） |
| 侧栏菜单配置（既有菜单来源处） | 修改 | 顶层**三分**（仪表盘 / 业务模块 / 平台管理）+ 平台管理**四域二级分组** + 个人与帮助 |
| `src/modules/openllm/pages/*`（15 项全局组件） | **迁出** | `RolesView`·`OrgTeamsUsersView`·`WorkspacesView`·`ConfigManageView`·`AuditLogsView`(下线)·`EdgeRouterView`·`DocCenterView`·`BillingView`·`Settings`(个人)·`ApiKeys`·`Usage`·`Costs`·`Alerts`·`Monitoring`·`PluginsView` |
| `src/modules/{memory,portrait,knowledge}/pages/*`（上收 4 项） | **迁出** | `memory/Admin`·`memory/MemoryMonitorView`·`memory/ApiGateway`·`portrait/DpsMonitorView`（+ `knowledge/Settings`·`knowledge/Users`） |
| `src/modules/gateway/**` | **归位（待确认）** | `gateway` 模块整体归入平台管理「可观测与审计」域；**其模块注册身份处置**为 §3.4 决策点 |
| `src/modules/openllm/pages/AuditLogsView.vue` | **删除** | mock 页下线（BL-146-09）；清理 `mockLogs` 数据源（AC-146-09-2 静态扫描 0 命中） |

**不新增**：新 store、新公共组件库、新样式体系、新构建配置、新第三方依赖。

> 说明：UI 设计 §5 组件树（`LogFilterBar` / `LogFacetNav` / `LogTruncatedAlert` / `LogTable` / `LogDetailDrawer`）为**逻辑分层**，Step 3 可按复杂度决定是否物理拆分为独立 `.vue` 文件；若页面体量可控，允许内联为单文件内的子组件（**YAGNI**，避免过早拆分）。

---

## 3. 路由与权限

| 路由 | 名称 | 组件 | meta |
|------|------|------|------|
| `/platform/observability/logs` | `platform-observability-logs` | `@/pages/platform/observability/LogsView.vue` | `{ title:'日志中心', icon:'Document', permission:'log:read' }` |
| `/platform/config/modules` | `platform-config-modules` | `@/pages/platform/config/ModuleSwitchView.vue` | `{ title:'模块开关', icon:'Grid', permission:'module:manage' }` |
| `/personal/settings` | `personal-settings` | `@/pages/personal/SettingsView.vue` | `{ title:'个人设置', icon:'User' }`（登录即可） |
| `/platform/{identity,config,observability,developers}/**` | 各域页 | `@/pages/platform/**` | 沿用各页既有权限码 |

### 3.1 旧 → 新 重定向映射表（**全量，禁 404**；ADR-146-08）

| 旧路径（保持可达） | 新路径 | 说明 |
|-------------------|--------|------|
| `/system/logs` | `/platform/observability/logs` | VC-012 新增页按新 IA 归位 |
| `/system/audit` | `/platform/observability/logs` | mock 页下线（BL-146-09） |
| `/system/tenants` | `/platform/identity/tenants` | 身份与权限域 |
| `/system/roles` | `/platform/identity/roles` | 同上 |
| `/system/org` | `/platform/identity/org` | 同上 |
| `/system/workspaces` | `/platform/identity/workspaces` | 同上 |
| `/system/config` | `/platform/config/general` | 平台配置与密钥域 |
| `/system/billing` | `/platform/observability/billing` | 可观测与审计域 |
| `/system/test-records` | `/platform/observability/test-records` | 同上 |
| `/system/docs` | `/platform/developers/docs` | 开发者资源域 |
| `/system/edgerouter` | `/platform/developers/edgerouter` | 同上 |
| `/openllm/settings` | `/personal/settings` | 个人设置归位 |
| `/openllm/api-keys` | `/platform/config/api-keys` | 上收（密钥） |
| `/openllm/usage` | `/platform/observability/usage` | 上收（用量） |
| `/openllm/monitoring`（含 `costs`/`budgets`/`alerts`/`traces` 子路径） | `/platform/observability/monitoring/**` | 上收（监控/成本/预算/告警/链路） |
| `/openllm/gpu` | `/platform/observability/gpu` | 上收（GPU 监控） |
| `/openllm/plugins` | `/platform/developers/plugins` | 上收（扩展集成） |
| `/openllm/auth-ext` | `/platform/identity/auth-ext` | 上收（认证扩展） |
| `/memory/admin` | `/platform/identity/memory-admin` | 上收（管理席位） |
| `/memory/api-gateway` | `/platform/observability/service-discovery` | 上收（服务发现与编排） |
| `/memory/monitor` | `/platform/observability/monitoring` | 上收（统一监控） |
| `/portrait/dps-monitor` | `/platform/observability/monitoring` | 上收（统一监控） |
| `/knowledge/settings` | `/platform/config/general` | 上收（模块级设置 → 全局配置） |
| `/knowledge/users` | `/platform/identity/users` | 上收（统一身份） |

> **注**：上表为**设计基线**；路径字面值以路由表实测为准 —— Step 3 施工前按 UI 设计 §9.1 的**脚本方式**生成全量四列映射表并替换本表（禁止人工转写）。`GenericPage` 承载的路由按 UI 设计 §9.3 规则逐条登记。

### 3.2 权限三处一致（**强制**）

| 处 | 要求 |
|----|------|
| ① 路由 `meta.permission` | 与后端权限码**同名**（如 `log:read`、`module:manage`）；禁止自造别名 |
| ② 菜单可见性 | 由**同一权限码**驱动；无权限即**不渲染**该菜单项与分组（空分组不显示） |
| ③ 路由守卫 | 由**同一权限码**校验；无权限跳 403（不回退 `/dashboard`） |

**反例（禁止）**：菜单用 A 码、守卫用 B 码、后端用 C 码 → 会出现"菜单可见但接口 403"或"有权限但看不到入口"的割裂。

### 3.3 重定向实现约定

| 项 | 设计 |
|----|------|
| 集中定义 | 建议 `src/core/router/legacyRedirects.ts` 单文件维护（便于审计与 E2E 遍历） |
| 参数保留 | 重定向**保留 query 与 hash**（如日志中心带筛选参数的书签） |
| 深链 | 深链直访不回退 `/dashboard`；旧深链按映射表跳转后**不丢参数** |
| 批量校验 | E2E 遍历映射表抽样断言"旧路径可达且落到预期新路径"（AC-146-14-1） |

### 3.4 决策点（Step 3 施工前确认）

| # | 决策点 | 说明 |
|:-:|--------|------|
| 1 | **`gateway` 模块注册身份处置** | 保留其模块注册项（仅前端导航归位）**或**一并迁移；影响 `GET /api/v1/modules` 消费侧与既有 `permission` |
| 2 | **模块注册表持久化形态** | DB 表 vs 配置驱动 → 决定模块开关页「可写」或「降级只读」 |
| 3 | 各模块 `route_prefix` 是否随 IA 调整 | **当前设计：不改**（四模块路径不变，仅顶层归位与系统性能力剥离） |

---

## 4. 数据获取层

```ts
// src/core/api/logs.ts（设计契约）
export type LogSource = 'l1_file' | 'audit_db' | 'test_record'
export type LogModule = 'identity'|'dps'|'rag'|'memory'|'llm'|'gateway'|'testing'|'other'
export type LogOperation = 'auth_login'|'read'|'write'|'delete'|'config'|'proxy'
export type LogResult = 'success'|'client_error'|'server_error'|'unknown'

export interface LogEntry { /* 18 字段，与 API 文档 §2 一一对应 */ }
export interface LogQuery  { source: LogSource; module?: LogModule[]; operation?: LogOperation[]; /* … */ }
export interface LogSearchResponse { items: LogEntry[]; total: number; page: number; page_size: number; source: LogSource; truncated: boolean }
export interface LogFacetsResponse { source: LogSource; module: Record<string, number>; operation: Record<string, number>; result: Record<string, number>; operator: Record<string, number>; truncated: boolean }
```

| 项 | 约定 |
|----|------|
| 请求层 | 复用既有 `core/api/http.ts`（`baseURL='/api/v1'`，经 vite 代理 → 网关 8000）；**不新建 axios 实例** |
| 参数风格 | 与后端一致使用 `snake_case` 查询参数（`page_size`/`case_id`/`run_id`/`step_id`） |
| 多选传参 | `module`/`operation`/`result`/`operator` 多选以**重复同名参数**传递（后端按其 OR 语义解析） |
| 导出 | 通过 `http.get(..., { responseType:'blob' })` 触发浏览器下载；`Content-Disposition` 提供文件名 |
| 错误处理 | 复用既有错误契约映射（`{code,message,detail,request_id}`）；`PARAM_400` 的 `detail.field` 用于定位表单项 |
| 测试模式头 | 复用既有 `http.ts` 测试模式注入（三测试头）→ 日志中心自身操作可在日志中按用例归属（AC-146-08-4） |

---

## 5. 状态管理与组件通信

| 项 | 决策 |
|----|------|
| 全局 store | **不使用**（不引入 Pinia 模块）；筛选条件、分页、加载态、`truncated`、详情选中项均为 `LogsView` 本地 `ref` 状态 |
| 组件通信 | `props` 下行 + `emit` 上行（与既有 `SystemTestRecords.vue` 风格一致） |
| 请求时序 | 分类点选/关键字回车/时间窗变更/分页变更 → **单一 `load()` 编排**（并行拉取 `search` 与 `facets`，保证两者同参数——AC-146-02-4 口径互证） |
| 竞态处理 | 以请求序号（自增 token）丢弃过期响应，避免快速点选导致的旧结果覆盖新结果 |
| 数据源切换 | 保留 `q`/时间窗，清空分类选择并 `el-message` 提示（需求 §5.2） |

---

## 6. 与既有架构的一致性

| 既有面 | 本版本影响 |
|--------|-----------|
| 目录结构 / 构建（Vite）/ 组件库（Element Plus） | **未改动** |
| 请求层与测试头注入 | **未改动**（复用） |
| 既有页面 | 仅新增 1 页、删除 1 个 mock 页、1 条重定向 |
| 样式体系 | 复用既有 Token 与公共类（`ob-table-scroll`/`page-toolbar`）；**不新增全局样式** |
| 独立前端 / 统一前端双模式 | 未涉及（本页仅存在于统一前端 `openbase-ui`） |

---

## 7. 构建与产物

| 项 | 说明 |
|----|------|
| 构建命令 | 沿用既有（`npm run build` / `npm test`（vitest）/ Playwright E2E） |
| 产物 | 随既有前端产物一并构建；**无新增构建配置** |
| 单测 | 建议覆盖：`core/api/logs.ts` 参数序列化（多选重复参数）、`LogsView` 的 `truncated` 与空态渲染、路由重定向断言 |
| E2E | 按《UI设计文档-v1.4.6》§4 八项状态编写（AC-146-08-1~4、AC-146-09-1） |
| **chunk 边界核验**（v1.1.0） | 构建后核验 **openllm chunk 不再包含全局页**（AC-146-13-2）；核验方法：产物分析 + 组件路径反查 |
| **迁移分批**（v1.1.0） | **按域分批提交**（identity → config → observability → developers），每批跑一次构建 + 类型检查 + E2E，避免一次性大规模移动难以定位回归（需求评估报告 §6#4） |
| **引用检索存证**（v1.1.0） | 删除/移动前须全局检索 `AuditLogsView` / `system-audit` / 各迁出组件名，**结果写入 DevLogReport**（承 Stage2 审计发现 #6） |
| **构建/类型门槛**（v1.1.0） | `npm run build` 通过 + 类型检查 0 错（AC-146-13-3）；`console.warn = 0`（AC-146-14-3） |

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | FA-OpenBase-Dev | 初始版本：前端增量设计（3 新增 + 1 修改 + 1 删除）、路由与权限、`core/api/logs.ts` 契约与多选传参约定、无全局 store 决策与竞态处理、一致性核对、构建与测试建议 |
| v1.1.0 | 2026-09-15 | FA-OpenBase-Dev | **VC-013 + VC-014 回溯重出（设计增补轮）**：① §2 文件清单重写为**大规模迁移视图**（新增 `pages/platform/**` 四域目录 + `pages/personal/**` + `ModuleSwitchView` + `core/api/modules.ts` + `legacyRedirects.ts`；迁出 openllm 15 项 / memory·portrait·knowledge 4 项；`gateway` 模块归位待确认）；② §3 路由表重写为**目标路由**（四域 + 个人）；③ **新增 §3.1 旧→新重定向映射表（24 条，禁 404）**；④ **新增 §3.2 权限三处一致（强制）** 与 §3.3 重定向实现约定（集中定义/参数保留/深链/批量校验）；⑤ **新增 §3.4 决策点三项**；⑥ §7 新增 chunk 边界核验 / 迁移分批 / 引用检索存证 / 构建类型门槛四项 |
