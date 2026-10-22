# OpenBase 开发记录报告（DevLogReport） - v1.4.11

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.11**（统一前端信息架构 ＋ 首屏/接口耗时治理） |
| 文档 | 开发记录报告（Step 3 产出） |
| 文档版本 | v1.7.0 |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-10-22 |
| 编制 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-前端架构设计文档-v1.4.11》v1.10.0（含 §8 公共功能域重组、§8.4.1 首屏治理、§8.8 后端耗时收口、§8.9 收口记录 14 项）；用户口径「公共功能归集 + 模块开关联动 + 商用生产系统级排布」 |
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
| 12 | **全页面走查发现**：业务模块页丢失全局侧栏（模块路由以顶层路由挂载，进入模块后无法回到公共功能） | 模块路由改挂 `root`（AppLayout）之下，模块子导航进入内容区，侧栏/顶栏常驻 | `core/router/index.ts` |
| 13 | **全页面走查发现**：知识库 API 控制台首屏 ECharts 警告（未激活页签内初始化，容器 0 尺寸） | 尺寸守卫 + `watch(activeTab)` 切到「性能监控」后再渲染 | `pages/platform/developers/KnowledgeConsoleView.vue` |

**批量套用方式**：`doc/tmp/adopt_page_container.py`（公共域）与 `doc/tmp/adopt_module_pages.py`（业务模块）两个一次性脚本，
只做根节点包裹 + 闭合标签 + 补 import；`Routing.vue` 按 `route.meta.title` 动态取标题、`AppForm.vue`（根为 `el-form`）与
`KnowledgeDetail.vue`（自带 `el-page-header`）手工处理。

**测试夹具同步**：`tests/platform-ia.spec.ts` 的模块夹具由「仅 openllm」扩为 openllm/memory/portrait/knowledge，
否则新增的 `dependsOn` 会在 403 用例之前先行拦截，导致断言口径失真。

### 2.8 请求超时兜底与本地基础设施编排（本轮补齐）

补齐 §5 遗留第 5、7 项，均为「观察项转闭环」，不改变页面与接口契约。

| # | 项 | 处置 | 文件 |
|:-:|----|------|------|
| 1 | 代理类端点沿用 15s 默认超时，上游挂起时列表页长时间停留 loading | 新增 `PROXY_TIMEOUT_MS = 8000` + `PROXY_PREFIXES`（`/memory-proxy/`、`/rag-proxy/`、`/dps-proxy/`、`/llm-proxy/`、`/gateway/`），请求拦截器仅在**未显式指定超时**时改写为 8s；流式调用（`llm.ts` / `rag.ts` 显式 120s）不受影响 | `core/api/http.ts` |
| 2 | `Redis(6380)` 原为手工启动，重启后需人工拉起 | 纳入 `start-all-services.ps1` 常驻编排：新增 `infra-redis`（`--requirepass` 本机口令、关闭 RDB/AOF）、`infra-qdrant` 两个服务条目 | `doc/tmp/start-all-services.ps1` |
| 3 | Redis 无 HTTP health 端点，原 `Test-HealthUrl` 判定恒为不健康 | 新增 `Test-TcpPort` 与 `Test-SvcHealthy`，服务条目支持 `TcpProbe=$true`（2s 建连即视为健康） | 同上 |
| 4 | local 模式下起 `openmemory` 时若 Redis/Qdrant 未起会直接失败 | 新增依赖连带：`local` 模式下 `openmemory → {infra-redis, infra-qdrant}`、`openrag → {infra-qdrant}`，已监听则自动 skip | 同上 |

**实测**（`-Only infra-redis,infra-qdrant`，`InfraMode=local`）：

```
===== final status =====
infra-redis   6380  HEALTHY  PID=28288
infra-qdrant  6333  HEALTHY  PID=20076
```

`OpenMemory` 仍需 **Neo4j(7687)**（本机未安装），本条如实保留为环境前置。

### 2.9 本地 Neo4j 社区版服务化（补齐环境前置）

原 `D:\infra\neo4j` 只有 `Neo4jStandbyServer.java` + `neo4j-harness` jar（嵌入式启动器），没有发行目录与 `bin\neo4j.bat`，且 harness 每次启动新建随机 store 目录（数据不持久）、脱离会话易被回收。现已改为**社区版内核 + 发行布局 + Windows 服务**：

| # | 项 | 结果 |
|:-:|----|------|
| 1 | 官方 zip 通道 | `dist.neo4j.org` 对本机返回 **403**（含 UA/Referer 伪装、`artifact.php` 302 落地、`versions/v1` 清单均不可达）；无 Docker / Chocolatey / NSSM；Maven Central 仅发布 jar 不发布发行包 |
| 2 | 安装形态 | 用 **Maven Central 官方 jar（225 个，排除 junit/mockito/harness 等测试依赖）** 装配发行布局 `D:\infra\neo4j-community-5.26.16\{bin,conf,lib,data,logs,import,plugins,run}`，启动器为官方 `org.neo4j.server.startup.Neo4jCommand`（与发行包 `neo4j.bat` 同一入口） |
| 3 | 配置 | `conf/neo4j.conf` 仅 ASCII 无 BOM（UTF8-BOM 会触发 `strict_validation` 报 `Unrecognized setting`）；仅监听 `127.0.0.1`，Bolt `:7687` / HTTP `:7474`；`dbms.security.auth_enabled=true`；堆 512m~1g、pagecache 512m（宿主资源紧张） |
| 4 | 认证 | `neo4j-admin dbms set-initial-password` 在首次启动前写入，口令对齐 `.env.shared-infra` 的 `NEO4J_PASSWORD` |
| 5 | 服务化 | 官方 `windows-service install` 依赖 `bin\tools\prunsrv-amd64.exe`（发行包内置，装配布局缺失）→ 从 `archive.apache.org` 取 **Apache Commons Daemon 1.4.1** 的 `prunsrv.exe` 落地为该文件；注册服务名 **`neo4j`**，启动类型 **Automatic**，运行账户 LocalSystem |
| 6 | 验证 | 服务 `Running`、`StartMode=Auto`；`7687/7474` 均监听；HTTP 事务端点写读各 1 行成功（探针节点已删）；Python `neo4j` 驱动 Bolt 登录返回 `Neo4j Kernel 5.26.16 **community**` |
| 7 | 数据持久性 | store 固定在 `data\databases\{neo4j,system}`，不再每次新建随机目录 |

**已知坑（后续重装可复用）**：WMI 脱离会话拉起时环境 `PATH` 极简，Neo4j `WindowsBootloaderOs` 需调用 `powershell.exe`，必须显式补 `C:\Windows\System32` 与 `WindowsPowerShell\v1.0`，否则报 `Cannot run program "powershell.exe": CreateProcess error=2`。

### 2.10 OpenMemory 启动失败根因与修复（跨仓）

现象：Neo4j 修好后，`openmemory` 仍起不来（8020 不监听，进程秒退）。

| # | 项 | 结论与证据 |
|:-:|----|-----------|
| 1 | 直接原因 | `VectorStoreError: Failed to initialize Qdrant` ← `httpx.ReadTimeout`。日志时序：`GET /collections` **200 OK**（06:36:18）→ 6s 后读响应头超时（06:36:24）→ 启动中止 |
| 2 | 机制 | qdrant-client **1.7.3** 默认超时 **5s**；本机建一个 payload 索引实测 **0.6~1.4s**，冷建集合叠加宿主满载超过 5s。失败后复查集合**已存在但无 payload 索引**，证明服务端建集合成功、客户端先放弃 |
| 3 | 放大因素（脚本 bug） | `start-all-services.ps1` 的 `$targets = if (...) { $Only }` 在**只指定 1 个服务**时把单元素数组坍缩成字符串，`-notcontains` 全部不匹配 → 静默不启动任何服务（打印 `openmemoryinfra-redisinfra-qdrant` 即证据）。已改为 `@(if (...) {...})` |
| 4 | 处置 A（运维侧） | 预建 `openmemory` 集合（384/cosine）+ 5 个 payload 索引（`user_id`/`session_id`/`agent_id`/`memory_type`/`is_active`），使启动期 `initialize()` 走幂等快路径 |
| 5 | 处置 B（代码侧） | OpenMemory `VectorStoreConfig` 新增 `timeout: float = 30.0`（env `OPENMEMORY_VECTOR_TIMEOUT`），`AsyncQdrantClient(..., timeout=...)` 显式传入；新增单测 `test_initialize_passes_configured_timeout`；**OpenMemory 提交 `c73b7c1`**（release/v7.3.0）。子集回归 `182 passed / 8 skipped`（`-k "vector or config"`，排除缺 `respx` 的 `test_sdk.py`） |
| 6 | 验证 | `/health` → `{"status":"healthy","dependencies":{"vector_store":"healthy","metadata_store":"healthy","session_store":"healthy"}}`；经 OpenBase 代理 `readiness` **200 / 407ms**、`memories` **200 / 1160ms**；`remember` → `forget(hard)` 全链路成功，`forgotten_count=1`、`residuals=[]`、剩余 `total=0` |
| 7 | 图库行为说明（**已更正**） | `build_service()` 第 4 步 `graph_store.initialize()` 是强依赖（失败即中止），服务 healthy ⇒ Neo4j 连接/初始化成功。**但「persistent 不写图」是实现覆盖缺口，不是设计行为**：默认写入路径完全不经过图库，`GraphSearch` 又只用 `properties CONTAINS` 全表扫描 —— 结论是图检索实际不可用。已立跨仓迭代方案并启动 P1，见 §2.11 |
| 8 | 走查复跑 | `node scripts/ui_e2e_all_services.mjs --service openmemory --shots ../doc/test/evidence/ui-preview-memory` → **6 页 PASS / FAIL 0**，降级态消失 |

### 2.11 记忆图谱跨仓迭代（异步可靠投影方案）

**方案文档**：OpenMemory 仓 `doc/planning/OpenMemory-记忆图谱异步投影跨仓迭代方案-v1.0.0.md`（状态 [Approved]）。
选定方案：**PG 事务性 outbox + 幂等 worker 异步投影 ＋ 重要度分层 ＋ 读路径索引与租户过滤**（拒绝同步双写，理由：主写延迟耦合、写放大、Neo4j 单写者瓶颈）。

| 小版本 | 范围 | 状态 |
|---|---|---|
| **v7.4.0（P1）** | 读路径加固：`:Entity` 唯一约束、`entity_fulltext` 全文索引、`label` 索引修正、`GraphSearch` 全文检索 + 精确 label 回退、`LIMIT`/深度收紧、`caller="GraphSearch"` 审计 | **已完成**，OpenMemory 提交 `17cba89` |
| v7.5.0（P2） | `graph_outbox`（Alembic v708）、`GraphProjector`、worker（SKIP LOCKED/批量/退避/死信/背压）、`:Memory` 节点与边、租户字段、forget 级联、读路径租户过滤 | 待实施（核心） |
| v7.6.0（P3） | 重要度分层与采样、批量 UNWIND、`graph_repair`（重放/对账/回填）、retention 与 decay 联动、指标告警 | 待实施 |
| v7.7.0（P4） | 跨仓联调、压测、灰度与回滚演练、文档回填 | 待实施 |

**P1 验证**：`pytest tests/unit/test_graph_store.py tests/unit/test_search_engines.py tests/unit/test_graph_search.py` → **53 passed（60.85s）**；新增 6 条用例覆盖「全文索引优先 / 索引缺失回退 / 无实体短路 / top_k 截断 / 约束与全文索引语句」。

**跨仓分工**：OpenBase 侧本轮**无代码改动**（代理已透传 `X-Tenant-ID`/`X-User-ID`），P2 接入时仅需联调与验收；方案文档已含职责矩阵与回滚口径。

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
| 前端用例（串行全量） | `vitest run --no-file-parallelism` | **21 文件 / 250 用例全通过**，无超时（§2.8 代理超时改动后复跑：`Tests 250 passed (250)`，86.75s） |
| 前端用例（并行） | `vitest run` | 247/250（3 条超时，宿主 CPU 满载所致；串行全量已证 250/250） |
| 前端构建 | `vite build` | 成功（3079 modules transformed）；§2.8 改动后复跑 `✓ built in 39.33s` |
| 后端用例 | `pytest tests -k "auth or principal or permission"` | 103 用例全通过 |
| 后端静态 | `ruff check openbase` | 0 错误 |
| 接口实测 | `doc/tmp/probe_http_timing.py` | 见 §3.4 |
| **全页面走查** | `node scripts/ui_e2e_all_services.mjs --shots ../doc/test/evidence/ui-preview` | **77 页 PASS 77 / FAIL 0**；逐页截图 + `index.html` 预览页（1440×900） |
| **记忆模块走查（复跑）** | `... --service openmemory --shots ../doc/test/evidence/ui-preview-memory` | **6 页 PASS 6 / FAIL 0**（OpenMemory 修复后降级态消失），截图见 `doc/test/evidence/ui-preview-memory/` |
| OpenMemory 单元子集 | `pytest tests/unit -k "vector or config"` | 182 passed / 8 skipped（排除缺 `respx` 的 `test_sdk.py`） |

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
| 4 | OpenMemory 运行前置（Neo4j 7687） | 运维 | **已闭环（v1.5.0 / v1.6.0）**：Neo4j 服务化见 §2.9；OpenMemory 启动故障已修复并复跑（6 页 PASS 6/0），见 §2.10 |
| 5 | ~~记忆列表 loading 兜底~~ | 前端 | **已闭环（v1.4.0）**：代理类端点 8s 硬超时，见 §2.8 第 1 项 |
| 6 | 宿主负载清理（quark 多实例、安全软件） | 运维/用户 | 直接决定连接建立与进程启动耗时 |
| 7 | ~~Redis（6380）需纳入服务编排常驻~~ | 运维 | **已闭环（v1.4.0）**：`infra-redis`/`infra-qdrant` 入 `start-all-services.ps1`，见 §2.8 第 2~4 项 |
| 8 | bcrypt `rounds` 是否下调 | 安全裁定 | 影响登录耗时 1~2s |
| 9 | 本轮改动提交与三远程推送 | 研发 | 见提交清单，按精确文件圈定，禁 `git add -A` |

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.7.0 | 2026-10-22 | 研发（AI 辅助） | 更正 §2.10 第 7 项结论（「persistent 不写图」是实现缺口而非设计行为）；新增 §2.11「记忆图谱跨仓迭代」：登记跨仓方案 v1.0.0 与 v7.4.0~v7.7.0 路线，**v7.4.0（P1 读路径加固）已完成**（OpenMemory `17cba89`，回归 53 passed）。 |
| v1.6.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.10「OpenMemory 启动失败根因与修复」：Qdrant 客户端 5s 默认超时导致 `ReadTimeout`（qdrant-client 1.7.3）+ 编排脚本单服务目标坍缩为字符串的 bug；处置为预建集合/索引 + OpenMemory `VectorStoreConfig.timeout=30`（提交 `c73b7c1`）；§4 增补记忆模块走查 6/6 与 OpenMemory 单测子集；§5 第 4 项闭环。 |
| v1.5.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.9「本地 Neo4j 社区版服务化」：`dist.neo4j.org` 403 → 用官方 jar 装配发行布局 + `Neo4jCommand` 官方入口 + `prunsrv` 注册 Windows 服务 `neo4j`（Auto，LocalSystem），认证与数据持久性验证通过；§5 第 4 项标记闭环。 |
| v1.4.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.8「请求超时兜底与本地基础设施编排」：代理类端点 8s 超时（`core/api/http.ts`）、`Redis/Qdrant` 纳入 `start-all-services.ps1`（`TcpProbe` 探测 + local 模式依赖连带）；§4 复跑 `vitest` 250/250 与 `vite build`；§5 第 5、7 项标记闭环；文档版本号与上游依据同步至架构文档 v1.8.0。 |
| v1.3.0 | 2026-10-22 | 研发（AI 辅助） | 追加「全页面走查」：77 页 PASS 77/FAIL 0，产出逐页截图与预览页；§2.7 增补第 12~13 项走查缺陷（模块页丢失全局侧栏、ECharts 隐藏页签初始化告警）及修复；§4 增补走查门禁行；§5 登记 OpenMemory 依赖 Neo4j 的环境前置。 |
| v1.2.0 | 2026-10-21 | 研发（AI 辅助） | 追加阶段四收口：§2.7 增补第 8~11 项（DPS 12 页归位画像模块并补导航、`.page-toolbar` 全局化、删除 `knowledge/Settings.vue`、业务模块 39 页套骨架并同步 `key-pages` 夹具）；§4 验证更新为全量 250 用例串行通过；§5 遗留收窄为 `useAsyncState`、面包屑与 4 个占位页。 |
| v1.1.0 | 2026-10-21 | 研发（AI 辅助） | 新增 §2.7「公共域收口（阶段三）」：7 项缺口逐条处置（记忆席位 dependsOn、gateway 开关只读化、providers/register 与画像假页下线、2 个死文件删除、占位页统一为结果页并补入口、公共域 37 页套骨架），同步 E2E 页面清单与 `platform-ia` 测试夹具；§5 遗留收窄为业务模块页与占位页上游依赖。 |
| v1.0.0 | 2026-10-21 | 研发（AI 辅助） | 初始创建：记录 v1.4.11 统一前端 IA（阶段一/二）、首屏治理、后端接口 8s 级耗时排查的证据链（6 项观测）、根因分解（R1~R5）、3 项处置与复测数据（`/auth/me` P50 91ms 等），并登记 6 项遗留。 |
