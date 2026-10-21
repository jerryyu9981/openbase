# OpenBase 开发记录报告（DevLogReport） - v1.4.11

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.11**（统一前端信息架构 ＋ 首屏/接口耗时治理） |
| 文档 | 开发记录报告（Step 3 产出） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-10-21 |
| 编制 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-前端架构设计文档-v1.4.11》v1.4.0（含 §8 公共功能域重组、§8.4.1 首屏治理、§8.8 后端耗时收口）；用户口径「公共功能归集 + 模块开关联动 + 商用生产系统级排布」 |
| 开发方式 | 结构先行（骨架/路由/状态）→ 页面上收 → 首屏治理 → 后端耗时排查 → 静态与用例门禁 → 留痕 |

---

## 1. 版本目标与增量范围

| # | 目标 | 交付结果 |
|:-:|------|----------|
| 1 | 不属于任何业务模块的前端功能，按实际情况归集到**公共功能** | 公共功能五域（平台身份/配置与策略/可观测性/开发者与集成/AI 能力治理），15 个页面 `git mv` 上收至 `src/pages/platform/**` |
| 2 | 公共模块中的业务开关与业务模块页面**联动**（开则显示、关则隐藏） | 模块开关切换后前端**即时生效**：`moduleRegistry.reload` → `syncModuleRoutes` 卸载/重装路由；治理页新增 `meta.dependsOn` 双门禁 |
| 3 | 全部前端功能按**商用生产系统级**统一划分与排布 | 统一页面骨架 `components/page/` 四件套 + 统一排布规范（页头 → 筛选 → 内容 → 分页，16px 节奏） |
| 4 | 首屏不再白屏、不再等 8s 接口 | 启动骨架 + 预热 2.5s 上限 + 模块清单并行预取 + `loadMe/init` 在途去重 + 清单缓存 |
| 5 | **排查后端接口耗时**（用户阶段二指令） | 定位 5 项成分并处置 3 项；同机热态 `/auth/me` P50 91ms、`/modules` P50 81ms |

**明确不做**：新增业务功能、改设计系统 `tokens.css`、引入新前端依赖、改后端接口契约（本轮仅做性能相关实现调整，不改出参出参结构）。

---

## 2. 实现清单

### 2.1 统一页面骨架（前端）

| 文件 | 职责 |
|---|---|
| `src/components/page/PageContainer.vue` | 页面外壳：`ob-page` 纵向间距 + `PageHeader` + 默认插槽 |
| `src/components/page/PageHeader.vue` | 标题/描述/返回 + `#actions`（页级主操作）/`#meta` |
| `src/components/page/FilterBar.vue` | 筛选区：左条件 + 右操作 |
| `src/components/page/EmptyState.vue` | 统一空态 + `#action` |

### 2.2 信息架构与路由

- `src/pages/platform/routes.ts`：新增 `governanceRoutes`（11 条，均声明 `dependsOn: 'openllm'`）；`configRoutes` 补 `rate-limits`、`observabilityRoutes` 补 `dps-monitor`、`identityRoutes` 补 `dps-permissions`、`developerRoutes` 补 `dps-api`/`knowledge-admin`/`knowledge-console`。
- `src/core/layouts/AppLayout.vue`：「平台管理」→「公共功能」，四域扩为五域；`dependencyEnabled()` 按注册表过滤 `dependsOn` 叶子。
- `src/core/router/legacyRedirects.ts`：17 条旧路径 → 新落点（保留 query/hash）。
- 15 个页面 `git mv` 上收：`openllm/{Providers,GenericPage,Categories,Routing,DownloadManagerView,ToolCallMonitorView,AbTestView,PromptTemplatesView,PromptExperimentsView}` → `pages/platform/governance/`；`portrait/Dps{Permission,RateLimit,Monitor,ApiManage}View` → `pages/platform/{identity,config,observability,developers}/`；`knowledge/Knowledge{Admin,Console}View` → `pages/platform/developers/`。
- 模块路由表收敛：`modules/openllm` 仅保留 12 条业务页；`modules/portrait` 8 条、`modules/knowledge` 3 条。

### 2.3 模块开关即时生效

- `src/core/router/index.ts`：`mountModuleRoutes(only?: Set<string>)` 支持精确装载；新增 `syncModuleRoutes()`（先 `removeRoute` 再重装）；守卫新增 `meta.dependsOn` 拦截 → `/forbidden`；`registry.init` 失败降级不阻断导航。
- `src/core/stores/moduleRegistry.ts`：`prefetch(force)` + `listCache` + 模块级在途 Promise；`reload()` 重建注册表并调用 `syncModuleRoutes`。
- `src/pages/platform/config/ModuleSwitchView.vue`：切换成功后 `await registry.reload(auth.permissions)`；失败仅 `warn` + 提示刷新（不回滚后端结果）；抽屉补「前端生效」「审计口径」两项。

### 2.4 首屏治理

| 改动 | 文件 |
|---|---|
| 启动骨架（`route.matched` 为空时渲染 `data-test="app-boot"`，替代白屏） | `src/App.vue` |
| 预热与 `/auth/me` 并行、最多等 2500ms、先挂载 | `src/main.ts` |
| `loadMe` 在途去重 + `loaded` 短路 | `src/core/stores/auth.ts` |

### 2.5 阶段二页面套用（本轮）

| 页面 | 改动 |
|---|---|
| `pages/platform/observability/Monitoring.vue` | 根节点改 `PageContainer`（标题/描述/`test-id`），时间范围切换上移 `#actions` |
| `pages/platform/observability/LogsView.vue` | 根节点改 `PageContainer`，数据源切换上移 `#actions`，删除失效的 `.logs-toolbar` 样式 |

### 2.6 后端改动（性能相关，不改契约）

| 文件 | 改动 | 理由 |
|---|---|---|
| `openbase/core/cache/redis_client.py` | 新增 `_mark_unavailable()` 熔断冷却（默认 300s，`OPENBASE_REDIS_COOLDOWN_SECONDS` / `OPENBASE_REDIS_SOCKET_TIMEOUT` 可调）；`cache_get/set/delete/publish/pub` 失败分支统一走熔断 | Redis 不可达时，每次缓存调用都要付出 socket 超时（1s 级），多调用叠加成 8s |
| `openbase/core/deps/auth.py` | 中间件验证后标注 `request.state.verified_principal_subject`；`get_current_user` 对**同一主体**跳过重复 `verify_principal` | 原实现同一请求内主体验证**双读**；Redis 熔断后每次都要读库 |
| `openbase/core/db/session.py` | PG 显式池参数 `pool_size=10 / max_overflow=20 / pool_timeout=10 / pool_recycle=1800 / pool_pre_ping=True` | 长连接失效后缺省行为不明确，易在请求路径重建连接 |

> 安全口径未变：主体验证仍是每请求执行一次（中间件统一执行），仅消除**同请求内**的重复；`/proxy` 等中间件白名单路径仍由依赖层完整校验。

### 2.7 公共域收口（阶段三，人工批准后执行）

按「先补门禁缺口 → 再清死代码 → 再逐域套骨架」顺序推进，逐项如下：

| # | 缺口 | 处置 | 文件 |
|:-:|------|------|------|
| 1 | `记忆管理席位` 只声明权限、未声明模块依赖 → 关闭记忆模块后页面仍显示 | 路由 `meta.dependsOn='memory'` + 菜单叶子 `dependsOn`（双门禁） | `pages/platform/routes.ts`、`core/layouts/AppLayout.vue` |
| 2 | `gateway` 已迁公共功能，模块开关仍可切换（对前端无效果） | 开关页把 `gateway` 从可切换列表剔除，改为「已迁入公共功能、页面常驻」提示 | `pages/platform/config/ModuleSwitchView.vue` |
| 3 | `providers/register` 独立占位页冗余（新增已是列表页内嵌对话框） | 删除路由；旧直达链接 `→ /platform/governance/providers` | `routes.ts`、`legacyRedirects.ts` |
| 4 | `/portrait/reports`、`/portrait/batch` 复用列表组件（假页面） | 删除路由与菜单项；旧链接 `→ /portrait/list`；E2E 页面清单同步 | `modules/portrait/index.ts`、`legacyRedirects.ts`、`scripts/ui_e2e_all_services.mjs` |
| 5 | `modules/memory/pages/ApiGateway.vue`、`MemoryMonitorView.vue` 为死文件 | 删除 | `modules/memory/pages/` |
| 6 | 占位页文案停留在「v1.2.0 已规划」，且 3 条占位路由无入口 | 改为统一结果页（未交付 + 上游依赖 + 返回）；统一监控页补链路追踪/预算管理/应用调用记录入口 | `pages/platform/governance/GenericPage.vue`、`observability/Monitoring.vue` |
| 7 | 公共域 34 页仍用各自 `*-page` 私有布局 | 批量套用 `PageContainer`（五域合计 37 页），标题/描述集中定义 | `pages/platform/**` |
| 8 | DPS 模板化 12 页挂在顶部 `/dps/**`：无菜单入口、不受模块开关约束 | 归位为画像模块 `dps/*` 子路由（`/portrait/dps/**`），新增「画像模板化（DPS）」导航组；旧前缀重定向（含 `/dps/:pathMatch(.*)*` 兜底） | `modules/portrait/index.ts`、`core/router/index.ts`、`legacyRedirects.ts` |
| 9 | `.page-toolbar` 在 20+ 页面各写一份 scoped 样式 | 收敛为 `core/styles/layout.css` 单份全局类；纵向间距交给 `PageContainer` 的 16px gap | `core/styles/layout.css`、各页面 `<style>` |
| 10 | `modules/knowledge/pages/Settings.vue` 无路由引用（死文件） | 删除 | `modules/knowledge/pages/` |
| 11 | 业务模块 39 页仍用私有布局 | 全部套用 `PageContainer`（openllm 11 / portrait 18 / memory 7 / knowledge 3）；记忆四页去掉重复的页内标题，`key-pages` 夹具同步改指向页级 `test-id` | `modules/*/pages/**`、`tests/e2e/fixtures/key-pages.json` |

**批量套用方式**：`doc/tmp/adopt_page_container.py`（公共域）与 `doc/tmp/adopt_module_pages.py`（业务模块）两个一次性脚本，
只做根节点包裹 + 闭合标签 + 补 import；`Routing.vue` 按 `route.meta.title` 动态取标题、`AppForm.vue`（根为 `el-form`）与
`KnowledgeDetail.vue`（自带 `el-page-header`）手工处理。

**测试夹具同步**：`tests/platform-ia.spec.ts` 的模块夹具由「仅 openllm」扩为 openllm/memory/portrait/knowledge，
否则新增的 `dependsOn` 会在 403 用例之前先行拦截，导致断言口径失真。

---

## 3. 后端接口耗时排查（阶段二核心）

### 3.1 现象

前端首屏卡顿，审计日志显示 `/api/v1/auth/me`、`/api/v1/modules` 单次 8s 级，并发时可达 15~35s；同一时间 `/health` 仅数百毫秒。

### 3.2 证据链

| 观测 | 方法 | 结果 | 结论 |
|---|---|---|---|
| 是否仅鉴权路径慢 | 直连 8000 端口分段计时（TCP/首字节/总） | `/health` 3~48ms；`/auth/me`、`/modules`、`/tenants` 均 8s 级 | 慢在鉴权链路，不在框架/网络接入 |
| 是否 DB 查询慢 | `probe_auth.py`（应用同口径 engine） | `fetch_user` 28ms、`permissions` 80ms；`load_principal_snapshot` 首次 6630ms、二次 32ms | 非查询本身；**首次**含连接/缓存代价 |
| 是否 Redis | `probe_redis.py` + socket 直连探测 | `127.0.0.1:6380` 与 `192.168.0.151:6380` 均 connect 超时 | Redis 全程不可达，缓存层每次调用都在付超时 |
| 是否 DB 建连慢 | NullPool/池化对比、`psql --version` 对照 | 新建 PG 连接 0.6~6s；`psql --version`（不联网）0.9~5.1s | **宿主级**：进程/连接创建都很慢 |
| 是否登录慢 | `verify_password` 计时 | bcrypt 1.1~1.9s/次 | `rounds=12` 的固有成本（CPU 满载放大） |
| 是否重复读库 | 代码走查 `AuthMiddleware` → `get_current_user` | 同一请求 `verify_principal` 执行 2 次 | 双读，白付一次 RTT |

### 3.3 根因分解

| # | 成分 | 性质 | 处置 |
|:-:|------|------|------|
| R1 | Redis 不可达 → 每次缓存调用阻塞 1s 级 | 环境 + 应用缺熔断 | **已处置**（熔断冷却 300s） |
| R2 | 主体验证同请求内双读 | 应用缺陷 | **已处置**（`verified_principal_subject` 复用） |
| R3 | 连接池未显式配置 | 应用加固项 | **已处置**（池参数 + pre_ping/recycle） |
| R4 | bcrypt `rounds=12` | 设计取舍 | **保留**（安全强度优先；仅登录路径，不在热路径） |
| R5 | 宿主 CPU 100%、可用内存 668MB/12GB、安全软件常驻 | 环境 | **未处置（需用户侧清理）**；表现为秒级离群值、服务启动耗时 286s |

### 3.4 复测（同机，改造后，连续 8 次采样）

| 接口 | min | P50 | max |
|------|----:|----:|----:|
| `/health` | 3ms | 12ms | 48ms |
| `/api/v1/auth/me` | 44ms | **91ms** | 124ms |
| `/api/v1/modules` | 38ms | **81ms** | 150ms |
| `/api/v1/tenants` | 23ms | **57ms** | 91ms |
| `POST /api/v1/auth/login` | — | 977ms（含 bcrypt） | 2280ms（宿主抖动） |

### 3.5 边界与未闭环

- 宿主高负载期间仍会出现 **1~5s 离群值**（实测 `/auth/me` 5135ms 单例、`/tenants` 1250ms 单例），与"新建 PG 连接 0.6~6s"一致；待宿主负载恢复后应复测确认。
- Redis 仍不可达，缓存（主体验证快照、用户、模块清单）全部处于降级状态；恢复 Redis 后应复查 P95。
- 登录 1~2s 为 bcrypt 固有成本，若需压到 500ms 内需下调 `rounds`，属安全取舍，需人工裁定。

---

## 4. 验证

| 门禁 | 命令 | 结果 |
|---|---|---|
| 前端类型 | `vue-tsc --noEmit` | 0 错误（收口改动后复跑） |
| 前端用例（串行全量） | `vitest run --no-file-parallelism` | **21 文件 / 250 用例全通过**，无超时 |
| 前端用例（并行） | `vitest run` | 247/250（3 条超时，宿主 CPU 满载所致；串行全量已证 250/250） |
| 前端构建 | `vite build` | 成功（3079 modules transformed） |
| 后端用例 | `pytest tests -k "auth or principal or permission"` | 103 用例全通过 |
| 后端静态 | `ruff check openbase` | 0 错误 |
| 接口实测 | `doc/tmp/probe_http_timing.py` | 见 §3.4 |

### 4.1 超时用例处置说明

并行跑出现的 3 条失败均为**超时**而非断言失败，且含本轮未触碰的 `DpsTemplateList` 用例；同机其他用例单条耗时被拉长到 7~20s（正常应 <1s），判定为**宿主资源饱和**导致。
最终以 `--no-file-parallelism` 跑全量：**21 文件 / 250 用例全通过**，确认非代码缺陷。

---

## 5. 遗留与移交

| # | 项 | 归属 | 说明 |
|:-:|----|------|------|
| 1 | 页面级加载/错误态统一到 `useAsyncState` | 前端 | 与骨架配套，减少各页自写 loading/error |
| 2 | 面包屑与详情页页签规范 | 前端 | 详情页目前用 `el-page-header` 各自实现 |
| 3 | 4 个占位页转真实页面 | 前端 + 上游 | 模型部署、链路追踪、预算管理、应用调用记录；入口已就位 |
| 4 | 宿主负载清理（quark 多实例、安全软件） | 运维/用户 | 直接决定连接建立与进程启动耗时 |
| 5 | Redis（6380）恢复可用 | 运维 | 恢复后复核 P95 与缓存命中 |
| 6 | bcrypt `rounds` 是否下调 | 安全裁定 | 影响登录耗时 1~2s |
| 7 | 本轮改动提交与三远程推送 | 研发 | 见提交清单，按精确文件圈定，禁 `git add -A` |

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.2.0 | 2026-10-21 | 研发（AI 辅助） | 追加阶段四收口：§2.7 增补第 8~11 项（DPS 12 页归位画像模块并补导航、`.page-toolbar` 全局化、删除 `knowledge/Settings.vue`、业务模块 39 页套骨架并同步 `key-pages` 夹具）；§4 验证更新为全量 250 用例串行通过；§5 遗留收窄为 `useAsyncState`、面包屑与 4 个占位页。 |
| v1.1.0 | 2026-10-21 | 研发（AI 辅助） | 新增 §2.7「公共域收口（阶段三）」：7 项缺口逐条处置（记忆席位 dependsOn、gateway 开关只读化、providers/register 与画像假页下线、2 个死文件删除、占位页统一为结果页并补入口、公共域 37 页套骨架），同步 E2E 页面清单与 `platform-ia` 测试夹具；§5 遗留收窄为业务模块页与占位页上游依赖。 |
| v1.0.0 | 2026-10-21 | 研发（AI 辅助） | 初始创建：记录 v1.4.11 统一前端 IA（阶段一/二）、首屏治理、后端接口 8s 级耗时排查的证据链（6 项观测）、根因分解（R1~R5）、3 项处置与复测数据（`/auth/me` P50 91ms 等），并登记 6 项遗留。 |
