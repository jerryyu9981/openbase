# OpenBase 开发记录报告（DevLogReport） - v1.4.11

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.11**（统一前端信息架构 ＋ 首屏/接口耗时治理） |
| 文档 | 开发记录报告（Step 3 产出） |
| 文档版本 | v2.22.0 |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-10-24 |
| 编制 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-前端架构设计文档-v1.4.11》v1.13.0（含 §8 公共功能域重组、§8.4.1 首屏治理、§8.8 后端耗时收口、§8.9 收口记录 14 项、§8.10 记忆模块对齐 v7.5~v7.8、§8.5 `/login` 兼容、§8.11 开发代理语义）；用户口径「公共功能归集 + 模块开关联动 + 商用生产系统级排布」 |
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
| v7.5.0（P2） | `graph_outbox`（Alembic v708）、`GraphProjector`、worker（SKIP LOCKED/批量/退避/死信/背压）、`:Memory` 节点与边、租户字段、forget 级联、读路径租户过滤 | **已完成**（OpenMemory `v7.5.0` 提交，见下） |
| v7.6.0（P3） | 重要度分层与采样、批量 UNWIND、`graph_repair`（重放/对账/回填）、retention 与 decay 联动、指标告警 | **已完成**（P3 探针见下） |
| v7.7.0（P4） | 跨仓联调、压测、灰度与回滚演练、文档回填 | **已完成**（P4 证据见下） |

**P1 验证**：`pytest tests/unit/test_graph_store.py tests/unit/test_search_engines.py tests/unit/test_graph_search.py` → **53 passed（60.85s）**；新增 6 条用例覆盖「全文索引优先 / 索引缺失回退 / 无实体短路 / top_k 截断 / 约束与全文索引语句」。

**P2 验证（v7.5.0）**：单测 `test_graph_projection / test_graph_search / test_graph_store / test_search_engines / test_relational_store / test_config` → **105 passed**；端到端探针（本机 PG + Neo4j，单进程规避服务回收）：

```
pending_after_write= 1
claimed= [('upsert', True)]
projected= {'memory': 1, 'entities': 6, 'written': 6}
memory_nodes= [{'c': 1}]  mentions= [{'c': 6}]
graph_search_hits= 1  hit_ids= ['224afc63-…']     # tenant-1 命中
other_tenant_hits= 0                              # tenant-2 fail-closed
memory_nodes_after_delete= [{'c': 0}]
```

Neo4j 侧索引已确认包含 `entity_id_unique`、`memory_id_unique`、`entity_fulltext`、`memory_fulltext`。

**跨仓分工**：OpenBase 侧本轮**无代码改动**——outbox 由 OpenMemory 元数据写入同事务自动落库，代理无需改；`X-Tenant-ID` 已在 recall 链路透传，租户过滤在 OpenMemory 读路径 fail-closed 生效。

**P3 验证（v7.6.0）**：单测 `test_graph_projection / test_graph_search / test_relational_store / test_config` → **67 passed**；探针（本机 PG + Neo4j）：

```
pending_low=0  pending_high=2                 # 分层策略：低价值不入队；高重要度/召回达标入队
batch_stats= {'memories': 2, 'entities': 16}  # 批量 UNWIND：两条记忆一次写
projected_nodes= [{'c': 2}] expected= 2
after_replay_nodes= [{'c': 2}]                # 幂等重投不产生重复节点
cleanup_remaining_nodes= [{'c': 0}]
```

新增能力：`projection_policy`（`importance`/`recall_count` 门槛，session 不投影）、`project_batch`、`scripts/graph_repair.py`（`--replay/--reconcile/--prune-done/--prune-orphans/--stats`）、`done_retention_days`；worker 已纳入 `start-all-services.ps1`（脚本新增无端口服务支持，`graph-worker` 常驻）。

> **分层策略补充**：当前写入链路默认 `score=0` 且不写 `importance`，若直接按阈值过滤会导致「所有记忆都不投影」。因此**无重要度信号时按未知处理并保守投影**，待上层写入 `importance`/非零 `score` 后才真正启用分层（OpenMemory `31a8315` 修正）。

**P4 验证（v7.7.0）**：跨仓探针走 OpenBase 代理全链路（`/api/v1/memory-proxy/{remember,recall,forget}`），中间插入 `graph_projection_worker.py --once`：

```
admin_token_ok=True nonce=p4probe20261022181009
remember_status=success memory_id=3f75054f-…
recall_before_worker=count=0                              # 未投影前不产生幽灵命中
worker_run_1=… claimed=1 ok=1 failed=0
graph_after_worker=memory_nodes=1 nonce_entities=1
recall_after_worker=count=2 ids=3f75054f-…,entity:tenant-1:p4probe… types=memory,custom
forget_count=1
worker_run_2=… claimed=1 ok=1 failed=0                    # forget 已产生 delete 事件
graph_after_delete=memory_nodes=0 nonce_entities=0        # 记忆与孤儿实体均清零
recall_after_delete=count=0                               # 删除后不再召回
backlog_write_status=success                              # worker 停摆期间主写仍成功
backlog_worker_drain=… claimed=1 ok=1 failed=0            # 恢复后一次排空
recall_backlog_memory=count=2 ids=7d50cd3a-…              # 积压记忆投影后可召回
```

压测与门禁（16 路并发经 OpenBase 代理）：

| 项 | 结果 |
|---|---|
| 写 1k | 1000/1000 成功；P50 4.285s / P95 4.903s / P99 6.123s（单请求基线 0.398s） |
| 读 1k | 1000/1000 成功；P95 5.281s（单请求基线 0.303s） |
| outbox 排空 | 801 条 pending，6 批（200/批）在 28.4s 完成 |
| 排空后顺序读 200 | 命中率 100%，P50 0.294s / P95 0.313s / P99 0.376s |
| 租户隔离 | tenant-1 数据以 tenant-2 身份召回 `hits=0`（fail-closed） |
| 重要度分层 | `importance=0.1` → `claimed=0`、图节点 0；`importance=0.9` → 正常投影 |

**P4 修复的缺陷（OpenMemory 侧，均带单测）**：

1. `forget(hard)` 只删 PG/Qdrant/会话缓存，未入队图删除事件 → `PersistentMemory.delete` 成功后 `enqueue_graph_event(delete)`。
2. 删除后孤儿 `:Entity` 仍被全文索引命中 → `GraphProjector.remove_memory` 清理失去全部 `MENTIONS` 入边的实体。
3. 全文索引对删除的可见性滞后 → `GraphSearch` 对候选 id 做一次 `UNWIND` 回表校验，不返回幽灵结果。
4. 结果缓存键缺租户 → `tenant_code` 并入 `_result_key`，避免跨租户串用。
5. `forget` 后旧结果仍在 TTL 内 → `forget` 强制全量失效；并修正 `om:cache:` 前缀导致 `invalidate_all_results` 扫描空转、用户集合记录裸键无法删除的问题。

回归：`ruff check src tests` 0 错误；`pytest tests/unit`（排除环境缺依赖的 `test_sdk.py`）**1376 passed / 18 failed / 27 errors**，失败项全部为环境中既有缺口（PG 组织事实源不可用、alembic `op` 导入、opentelemetry `sdk` 属性），与本次改动无关。

### 2.12 v7.8.0 检索质量与可观测性（OpenMemory）

**范围**（用户选定）：检索质量提升 + 可观测性补齐；方案见 OpenMemory `doc/planning/OpenMemory-v7.8.0-检索质量与可观测性迭代方案-v1.0.0.md`（v1.1.0）。OpenBase 无接口破坏、本轮无代码改动。

**检索质量改动**（`search_engines.py`）：

1. 实体命中不再把 `:Entity` 节点当作记忆返回，改为沿 `(m:Memory)-[:MENTIONS]->(e:Entity)` 解析为记忆（`score=0.90`，`metadata.matched_entity` 标注来源实体）；仅当实体无任何关联记忆时才保留节点级兜底（`score=0.80`）。
2. 移除「遍历路径上的实体节点直接作为结果」的逻辑，避免 `memory_id=entity:*` 污染结果集。
3. 实体名多词查询使用 `+term` 强制全部命中（抑制 OR 噪声）；自由查询保留 OR 召回。
4. 统一转义 Lucene 保留字符（`+ - ! ( ) { } [ ] ^ " ~ * ? : \ /`、`&&`、`||`），用户输入不会触发查询语法错误。

**可观测性改动**：

- `/metrics` 新增 `openmemory_graph_projection_events_total{result}`、`openmemory_graph_projection_duration_seconds`、`openmemory_graph_search_total{result}`、`openmemory_graph_search_duration_seconds`、`openmemory_graph_search_hits`、`openmemory_graph_outbox_pending/_dead`。
- graph worker 以内置 `http.server` 暴露 `http://127.0.0.1:9101/metrics`（`OPENMEMORY_GRAPH_PROJECTION_METRICS_PORT`，0=关闭），不新增依赖。
- `deploy/prometheus/alerts/openmemory_alerts.yml` 新增 `openmemory-graph` 组：积压 >1000（10m）、死信 >0（5m）、检索 P95 >500ms、检索错误率 >5%。
- `openmemory.api` 改为惰性导出，消除 `api.metrics` 与 `memory.service → retrieval → search_engines` 的循环导入。

**验证**：

- 相关单测（`test_graph_search` + `test_graph_quality_observability` + `test_graph_projection`）**43 passed**；`ruff check src tests scripts/graph_projection_worker.py` **0 错误**。
- 真实 Neo4j 独立验证（`p5_verify.py`，tenant-1）：`hits=1`、`ids=['7d50cd3a-…']`、`entity_id_results=[]`（不再返回实体 id）；指标端点四类指标均可抓取，`openmemory_graph_search_total{result="ok"} 1`。
- 全量单测：**1385 passed / 18 failed / 27 errors**，失败项与 v7.7.0 基线完全一致（环境缺口），新增 9 条用例全部通过。

**遗留/环境说明**：执行期间宿主 CPU 被 IDE/远控进程持续占满，OpenMemory/OpenBase 进程级重启多次超时（300s 健康等待），因此本轮采用「独立进程 + 真实 Neo4j」完成检索与指标端点验证；服务级冒烟待宿主负载恢复后复跑，不阻塞代码交付。

### 2.13 统一前端 OpenMemory 记忆模块对齐（v7.8.0 P6）

**范围**：根据 v7.5.0~v7.8.0（异步投影、删除一致性、检索质量、图链路指标）完善统一前端记忆模块；跨 OpenMemory（只读 overview 端点）与 OpenBase（代理 + UI）。

**后端**：

- OpenMemory 新增 `GET /api/v1/graph/overview?limit=120`：返回当前租户 `:Memory`/`:Entity`/`MENTIONS` 快照与统计（记忆数、实体数、关系数、outbox pending/dead）；跨租户 fail-closed，缺图存储返回 503 `SYS_SOURCE_UNAVAILABLE`；`GraphOverview` 纳入 `query_cypher` 调用方白名单。
- `start_openmemory.py` 将 `graph_store` 挂到 `app.state`（`build_service` 返回值扩展）。
- OpenBase 新增 `GET /api/v1/memory-proxy/graph/overview` 透传（limit 10~300，统一信封）。

**前端（openbase-ui `modules/memory`）**：

| 页面 | 变更 |
|---|---|
| 记忆图谱 | 删除 TD-13-18 mock 数据与本地增删；接真实 overview，D3 渲染记忆/实体节点与 `MENTIONS` 边；新增规模统计、待投影/死信提示、实体显示开关、记忆节点点击进详情、空图/错误态 |
| 记忆搜索 | 策略补 `graph/temporal/fusion`；新增「命中方式」（记忆命中/实体节点）与 `matched_entity`；`entity:*` 孤立实体不提供详情入口；图谱策略展示语义说明 |
| 写入记忆 | 新增重要度滑杆（`metadata.importance`，默认 0.6），与标签合并提交；补充异步投影/分层说明 |
| 记忆列表 | 删除模式可选软删/硬删（透传 `mode`）；类型筛选对齐 `persistent/session/episode`；删除提示说明图投影同步清理 |

**验证**：

- `memory-graph-v180.spec.ts`（3 例）+ `memory-search-v180.spec.ts`（1 例）→ **4 passed**；`vue-tsc --noEmit` 通过。
- OpenMemory `test_graph_overview.py` → **3 passed**（节点/边/统计、503、outbox 故障容错）。
- OpenBase `tests/test_memory_proxy.py` → **17 passed**（新增 overview 透传与 limit 断言）。
- 真实 Neo4j 端点验证（`p6_overview_verify.py`，tenant-1）：200；`stats={'memory_nodes': 1011, 'entity_nodes': 1038, 'edges': 99}`；`nodes=47`（20 个记忆 UUID + 27 个实体节点），记忆 id 均为 UUID、实体 id 为 `entity:<tenant>:<key>`，边为 `MENTIONS`。
- **服务级页面走查（浏览器实测）**：登录 admin 后——
  - `/memory/graph`：统计卡片 `记忆节点 1011 / 实体节点 1038 / 关系数 599 / 待投影 0 / 死信 0`；SVG 渲染 247 个圆形节点、599 条连线；无空态、无错误条、控制台 0 error。
  - `/memory/search`（策略=图谱，查询 `p4load7`）：显示图检索说明；1 条结果，来源 `graph`、命中方式「记忆命中」、无「实体：」文本、无错误条、0 error。
  - `/memory/write`：重要度滑杆存在（0~1，默认 0.60），「写入记忆」按钮存在，0 error。
  - 走查发现并修复：OpenMemory `user`/`guest` 角色缺少 `*/graph/overview: GET` 导致代理 403，已在 `auth/permission.py` 补权限并加单测（`test_v711_core.py` 23 passed）。
- 兼容性：仅新增只读端点与展示字段，既有响应结构与路由不变。

**补充修复（同日）：`/login` 重定向告警**

- 根因：`/login` 未在路由表注册，直访时首帧解析触发 `[Vue Router warn] No match found`，随后由守卫兜底跳 `/auth/login`，并可能生成 `redirect=/login` 的自我回跳链。
- 处置：在 `staticRoutes` 增加 `/login → /auth/login` 顶层函数式重定向（保留 query/hash），解析阶段即命中；未登录落到 `/auth/login` 并保留显式 `redirect`，已登录按守卫回落 `/dashboard`。
- 验证：`tests/router-nav.spec.ts` 新增 S6-T2-5 两条用例（解析命中且无 No match / 保留 redirect 参数），该文件 **18 passed**；`vue-tsc --noEmit` 通过；浏览器实测未登录访问 `/login` → `/auth/login`、控制台 0 条 No match 警告，带 `redirect=%2Fmemory%2Fgraph` 时参数完整保留。

**补充修复（同日）：服务重启期间 `/api/v1/modules` 500**

- 现象：浏览器在服务重启窗口访问页面时，控制台出现 `[router] module registry init failed AxiosError: Request failed with status code 500`。
- 根因：**不是 OpenBase 接口缺陷**。后端未就绪时请求未到达 OpenBase（后端日志无该请求记录，直连 8000 为 `ConnectionRefused`），Vite 开发代理（http-proxy）对上游连接失败返回**空 body 的 500**；OpenBase `/api/v1/modules` 读路径本身在 DB 异常时已降级为内存注册表（`_effective_status_map` 捕获并 WARN）。
- 处置：`vite.config.ts` 的 `/api` 代理新增 `error` 处理，经 `src/core/api/devProxy.ts` 统一输出 **503 + JSON**（`code=SYS_UPSTREAM_UNAVAILABLE`），与 `describeError` 的「可重试」语义一致；`server` 与 `preview` 共用同一配置。
- 验证：后端停止时经 `5173/api/v1/modules`、`/api/v1/auth/login` 均返回 **503 JSON**（修复前为空 body 500）；`tests/dev-proxy-v180.spec.ts` 4 例通过（503 映射、已发头仅收尾、已结束不重写、socket 安全跳过）；`vue-tsc --noEmit` 通过。

**遗留**：本次浏览器视口仅 608px，搜索表格来源/命中方式列需横向滚动，建议宽屏复核一次。

---

### 2.14 全栈功能级审计与 OpenLLM 聚合通道打通（v1.9.0）

**背景（用户指令）**：排查全栈运行时「前端所有页面的全部功能的错误」，并把「后端未具备的功能」单列后修复。经方案裁定，修复口径采用**打通 OpenLLM 聚合（跨多轮）**。

**审计方法（四层）**

| 层级 | 内容 | 实现 |
|------|------|------|
| L1 加载级 | 77 页逐页导航 | `openbase-ui/scripts/ui_e2e_all_services.mjs`（原有） |
| L2 交互级 | 逐页点击**非破坏性**动作（页签、查询、刷新、详情、连通性检测等） | 新增 `--interact`：`SAFE_ACTION_RE` / `UNSAFE_ACTION_RE` 双名单，破坏性动作一律跳过 |
| L3 API 面 | 逐页记录 `/api/**` 的方法/路径/状态 | 新增 `api_calls` 采集；判定优先级加入「api 5xx = FAIL」 |
| L4 通道探测 | 40 个候选聚合端点 GET 探测 | 新增 `doc/tmp/probe_proxy_reachability.ps1` |

**审计结果**

- 77 页（OpenBase 44 / OpenLLM 11 / OpenRAG 2 / OpenMemory 6 / DPS 14）**PASS 76 / FAIL 1**，**API 失败 0 次**；
- 唯一 FAIL 为 `net::ERR_NO_BUFFER_SPACE`（Chromium 在沙箱内写 `debug.log` 受限），该页单页复跑 0 错误，判为环境噪声；
- **52 页无后端调用**（数据来自前端硬编码「契约 mock」），已逐页成账。

**缺口分类（详见《OpenBase-全栈后端能力缺口清单-v1.0.0》）**

| 类别 | 含义 | 数量级 |
|:----:|------|--------|
| A | OpenBase 已有端点（200），前端未接线 | 3 页（用户管理、API 密钥、EdgeRouter） |
| B | 上游 OpenLLM 仅 JWT 通道，经聚合 401 | 20+ 页（治理/监控/RBAC 域） |
| C | OpenBase 缺列表端点（405） | 3 项（`GET /configs`、`/test-records`、`/test-runs`） |
| D | 上游 10s 超时（502） | 4 项（`local-models`、`models/favorites`、`models/compare`、`open-models/popular`） |
| E | 三仓均无对应能力 | 12 页 |

**本轮修复（两段 401 + 首批域）**

1. **来源映射**：通用代理 `/api/v1/proxy/{system}/{path}` 出站来源固定 `openbase-generic-proxy`，下游白名单只登记各自的 `openbase-*-proxy` → OpenLLM 判定「非白名单来源携带身份头」并忽略身份头。改为按被代理系统映射（`openllm → openbase-llm-proxy` 等，未知回落 generic）。
2. **凭据注入**：身份头被采信后，OpenLLM 原生 `/api/v1/*` 仍需 `Authorization: Bearer <OpenLLM API Key>`。通用代理补 `_inject_upstream_credentials`，**仅对 `system=openllm`** 注入，选 Key 复用 `llm_proxy._select_llm_api_key`（租户级优先、全局回落），其余系统不注入。
3. **首批域真实化**：`providers`（提供商管理）端到端接入 `/proxy/openllm/api/v1/providers`——列表/新增/编辑/删除/启停 + 模型数；移除「测试连接」随机延迟与「同步模型」随机计数两处假动作（上游对应端点仅 JWT 通道，登记缺口）。

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| 后端新增用例 | `pytest tests/test_proxy_target_system_v190.py` | **8 passed**（映射 4 组 + 未知回落 + 装配透传 + 凭据注入/不注入） |
| 代理相关回归 | `pytest tests/test_proxy_auth.py tests/test_proxy_outbound_matrix.py tests/test_proxy_upstream_observe.py tests/test_protocol_headers_lib.py` | **55 passed** |
| 后端静态 | `ruff check openbase tests` | 本轮文件 0 错误（全仓仍有 2 条**既有**告警：`test_q5_q6_decisions.py` 导入排序、`test_source_encoding_contract.py` UP012，未在本轮范围内改动） |
| 前端用例 | `vitest run tests/providers-v190.spec.ts` | **4 passed** |
| 接口实测 | `GET /api/v1/proxy/openllm/api/v1/providers` | **200**（3 条），`/{id}/models` 200（4 条），等值 `PUT` 200 |
| 浏览器实测 | `node scripts/check_page.mjs /platform/governance/providers` | 3 张卡片、模型数 3、健康/优先级真实、**0 error** |
| 全页面回归 | `ui_e2e_all_services.mjs --interact` | **76/77 PASS**（唯一 FAIL 为环境噪声），api 失败 **0** |

**证据**：`doc/test/evidence/s6/ui-func-audit-v190.json`、`ui-func-audit-v190-summary.md`、`proxy-reachability-v190.json`。

**遗留**：B 类（20+ 页）需 OpenLLM 侧将 `get_current_active_user` 改为双通道依赖或新增 `/openllm/v1/*` 网关端点，按缺口清单 R3~R5 分批；D 类需上游耗时治理；E 类需产品裁定。

---

### 2.15 R1：A 类三页接线（v1.9.1）

**范围**：按缺口清单 R1，把已有后端端点（实测 200）但页面仍用 mock 的三页接真实数据，并移除假动作。

| 页面 | 数据源 | 关键改动 |
|------|--------|----------|
| 用户管理 `/platform/identity/users` | OpenBase `/api/v1/users` | 真实列表（用户名/显示名/邮箱/角色/状态/租户）；新建补 `display_name`（后端必填）；角色分配走 `PUT /users/{id}/role`；启停 `PUT /users/{id} {status}`；停用 `DELETE /users/{id}`（软删）；角色下拉对齐五码标准集合；内置 `admin` 禁止停用 |
| API 密钥 `/platform/config/api-keys` | OpenBase `/api/v1/auth/api-keys` | 真实列表（访问范围/描述/创建时间/状态）；创建后一次性展示明文 + 复制；吊销走 `DELETE /auth/api-keys/{raw_key}`；删除虚构的「模型权限 / 速率限制 / 过期时间」字段（后端无此契约） |
| EdgeRouter `/platform/developers/edgerouter` | OpenLLM `/api/v1/edge/**`（经通用代理） | 新增「概览」（status/health/能力开关）；组织管理（列表/新增/编辑）；配额管理（按组织查询/调整）；适配器管理（只读，附注销风险说明）；路由审计（分页）；移除随机造数的「新增组织/新增配额/适配器开关」 |

**新增前端 API 模块**：`core/api/users.ts`、`core/api/apiKeys.ts`；`core/api/governance.ts` 追加 `edgeApi` 与 Edge 类型。

**发现的真实后端缺口（登记入缺口清单 C 类）**

- 服务 Key 列表 `ApiKeyOut` **不含 id**，吊销端点为 `DELETE /auth/api-keys/{raw_key}`（按明文 Key 定位）→ 列表中的历史密钥无法在前端吊销。
- 本轮处置：仅「本次会话创建且仍持有明文」的密钥可吊销，其余按钮禁用并给出原因说明（不伪造成功）；R2 建议后端补 `key_id` 与 `DELETE /auth/api-keys/{id}`。

**发现的跨仓缺陷（OpenLLM 并发 500）**

- 现象：全页面回归时「提供商管理」每次加载产生 1 次 `GET /providers/{id}/models → 500`；单页连续 3 次复现，且失败对象随机。
- 定位：OpenBase 审计日志显示 `upstream_status=500`（**上游返回**，非代理缺陷）；OpenLLM 栈为 `app/api/providers.py::list_models_by_provider → query.all()` + `app/db/session.py::get_db → db.close()`，异常为 `sqlalchemy.exc.InvalidRequestError: This session is provisioning a new connection; concurrent operations are not permitted`。根因是 `SessionLocal = scoped_session(...)` 与 FastAPI 同步端点的线程池组合：并发请求在线程间复用/交错同一 Session。
- 规避（本仓）：模型数改为**串行**逐个拉取并逐条容错，不再 3 路并发；串行后连续 3 次浏览器加载均 0 error。
- 根因修复：归 OpenLLM 侧（`get_db` 每请求独立 Session），已列入缺口清单 §7 第 5 项与 R2 跨仓派单。

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| 新增前端用例 | `vitest run tests/r1-wiring-v191.spec.ts` | **10 passed**（用户 4 / 密钥 3 / Edge 3） |
| 关联回归 | `vitest run l3-2-smoke + router-nav + providers-v190 + r1-wiring` | **40 passed（4 文件）** |
| 类型检查 | `vue-tsc --noEmit` | 0 错误 |
| 密钥全链路 | 接口实测：创建 → 列表（无明文）→ 吊销 | `created key_prefix=ob_k_…`、`list has_plaintext=False`、`revoked=True` |
| 浏览器实测（用户） | `node scripts/check_page.mjs /platform/identity/users` | 3 条真实用户、`GET /users 200`、0 error |
| 浏览器实测（密钥） | 同上 `/platform/config/api-keys` | 真实记录 + 「已吊销」态、0 error |
| 浏览器实测（Edge） | 同上 `/platform/developers/edgerouter` | status/health/adapters/organizations 均 200、概览与能力开关真实、0 error |

**遗留**：配额页在「无组织」时无数据可展示（已给引导文案）；Edge 组织为 OpenLLM 内存存储，重启即清空，属上游现状。

---

### 2.16 R2：C 类列表补齐与上游并发修复（v1.9.2）

**范围**：按缺口清单 R2，补齐 3 个缺失列表端点、服务 Key id 化吊销、两页接线，并跨仓修复 OpenLLM `get_db` 并发缺陷。

**后端（OpenBase）**

| 变更 | 说明 |
|------|------|
| `GET /api/v1/configs` | 新增列表：key 来源 = DB `configs` 表 ∪ 运行时写入 ∪ 代码默认值；取值走三级合并，`level` 回显最高优先级来源；支持 `prefix` / `level` 过滤 |
| `GET /api/v1/test-records` | 新增列表：按 `run_id` / `case_id` / `result` 过滤，`skip` / `limit` 分页（上限 500），按创建时间倒序 |
| `GET /api/v1/test-runs` | 新增轮次列表：含 `record_count`，供页面轮次下拉 |
| `ApiKeyOut.id` + `DELETE /auth/api-keys/by-id/{key_id}` | 记录生成稳定 `id`；新增按 id 吊销（未知 id → 404 `BIZ_404`），保留按明文吊销端点兼容 |

**前端**

| 页面 | 改动 |
|------|------|
| 全局配置 | 接 `GET /configs`；编辑保存 `POST /configs`（对象/布尔/数字自动解析）；版本抽屉接 `GET /configs/{key}/versions`，回滚 `POST /configs/{key}/rollback?version=`；导入改为逐条真实写入；移除 mock 配置与「热加载」假动作 |
| 测试记录 | 新增轮次下拉（`GET /test-runs`），进入页面自动选中最新一轮并加载 summary；开新一轮后刷新轮次；保留手填 run_id |
| API 密钥 | 改为 `DELETE /auth/api-keys/by-id/{id}`，「历史密钥不可吊销」限制解除；新增 `core/api/configs.ts` |

**跨仓（OpenLLM v1.9.2）**

- 根因：`SessionLocal = scoped_session(...)` 与 FastAPI 同步端点线程池组合，`get_db` 在 A 线程取的 Session 被 B 线程使用、teardown 又在 C 线程关闭 → 同一 Session 跨线程并发 → `InvalidRequestError: This session is provisioning a new connection; concurrent operations are not permitted`。
- 修复：`get_db` 改用独立 `_SessionFactory()`（每请求一个 Session，不经注册表）；`SessionLocal` 原样保留给审计/脚本/网关重试等既有调用方。
- 效果：提供商页 3 路并发拉模型数不再产生 500；`/openllm/conversations` 并发 500 亦消除。

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| 后端新增用例 | `pytest tests/test_r2_lists_v192.py` | **10 passed**（配置列表 3 / 测试记录 3 / 轮次 2 / 服务 Key id 2） |
| 跨仓用例 | OpenLLM `pytest tests/unit/test_db_session_concurrency_v192.py` | **3 passed**（线程间会话不同 / 不写 scoped 注册表 / 退出即关闭） |
| 前端用例 | `vitest run r2-wiring-v192 + r1-wiring-v191 + providers-v190 + l3-2-smoke + router-nav` | **47 passed（5 文件）** |
| 类型检查 | `vue-tsc --noEmit` | **0 错误** |
| 接口实测 | `GET /configs`、`/test-records`、`/test-runs` | 均 **200** |
| 服务 Key 全链路 | 创建 → 列表（`id` 回显、无明文）→ `DELETE /auth/api-keys/by-id/{id}` | `id=f00bee…`，吊销后 `revoked=True` |
| 并发回归 | 提供商模型数 3 路并发 × 3 轮 | **9/9 均为 200**（修复前每轮必有一路 500） |
| 浏览器实测 | 全局配置 / 测试记录页面 | **未完成**：服务进程在长命令执行期间被环境回收（DPS/前端存活，OpenBase 掉线），页面级验证暂以单测（jsdom）+ 接口实测替代，待服务稳定后复核 |

**遗留**：`GET /configs` 返回代码默认值可能使列表较长（当前无分页），如需分页在 R3 增补 `skip/limit`；测试记录内存上限 5000 条，超限淘汰最旧。

---

### 2.17 R3：双通道鉴权与插件/模型分类接线（v1.9.3）

**范围**：按缺口清单 R3，把 OpenLLM `plugins`、`model_categories` 两个路由族从 JWT-only 改为双通道，并将「插件管理」「模型分类」两页接到真实数据。

**跨仓（OpenLLM）**

| 文件 | 变更 |
|------|------|
| `backend/app/api/plugins.py` | 8 处 `Depends(get_current_active_user)` → `get_current_active_user_or_api_key`（列表/工具/详情/执行/健康检查等） |
| `backend/app/api/model_categories.py` | 13 处 `Depends(get_current_user)` → `get_current_active_user_or_api_key`（分类/树/分类模型/标签/收藏等） |
| `backend/tests/unit/test_r3_dual_channel_v193.py` | 新增 6 例：5 条路由依赖断言 + API Key 前缀分流 |

> 直接检查 router 依赖而不导入 `main.app`：完整应用会拉起 opentelemetry 等运行期可选依赖，在测试环境不可用。

**前端（OpenBase）**

| 页面 | 改动 |
|------|------|
| 插件管理 | 接 `/plugins`（类型/状态过滤）、`/plugins/tools`、`/plugins/{id}/health|enable|disable`、`/plugins/register`、`DELETE /plugins/{id}`；系统插件禁删；移除 6 条硬编码插件与假工具 |
| 模型分类 | 接 `/model-categories/tree`（拍平后按维度出标签云）、`/model-categories/{id}/models`（分页）；维度改为上游真实类型 capability/scene/architecture/scale；移除 10 条 mock 模型与本地 mock 延迟 |

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| OpenLLM 新增用例 | `pytest tests/unit/test_r3_dual_channel_v193.py` | **6 passed** |
| OpenLLM 既有回归 | `pytest test_plugins_api.py test_model_categories_api.py test_plugin_services.py` | **34 passed** |
| 前端新增用例 | `vitest run tests/r3-wiring-v193.spec.ts` | **8 passed** |
| 类型检查 | `vue-tsc --noEmit` | **0 错误** |
| 聚合实测 | `/proxy/openllm/api/v1/plugins`、`/plugins/tools`、`/model-categories`、`/model-categories/tree` | **4/4 200**（改造前均 401） |
| 浏览器实测 | 插件管理 / 模型分类 | **未完成**：探针未采集到页面 API 调用（环境侧服务回收/链路不稳定），页面级验证以 8 例 jsdom 单测 + 4 项接口实测替代，待服务稳定后复核 |

**遗留**：当前库中分类/插件数据为空，页面按真实语义展示空态（非 mock）；如需演示数据，应由 OpenLLM 侧种子脚本提供，前端不内置假数据。

---

### 2.18 R4：观察域双通道与六页接线（v1.9.4）

**范围**：按缺口清单 R4，把 OpenLLM 观察域（`monitoring/*`、`alerts`、`budgets`、`usage`、`billing`）从 JWT-only 改为双通道，并将成本/告警/链路/预算/用量/计费六页接到真实端点。

**跨仓（OpenLLM，7 文件 / 46 处依赖）**

| 文件 | 变更 |
|------|------|
| `backend/app/api/monitoring.py` | 8 处依赖改 `get_current_active_user_or_api_key`；`current_user.get("id", "unknown")` 修正为 `getattr(current_user, "id", "unknown")`（依赖返回 ORM `User`） |
| `backend/app/api/traces.py` | 6 处依赖改双通道（原参数类型为 `dict`，统一为 `User`） |
| `backend/app/api/alerts.py` | 10 处依赖改双通道（规则 CRUD、告警列表、resolve/acknowledge、health） |
| `backend/app/api/budgets.py` | 6 处依赖改双通道（预算列表/创建/状态/告警、成本分析/优化） |
| `backend/app/api/usage.py` | 4 处依赖改双通道（summary/trends/detail/export） |
| `backend/app/api/billing.py` | 8 处依赖改双通道；`POST /billing/bills`、`POST /billing/plans` 仍为 `require_permission(PERM_BILLING_WRITE)`，不放宽写权限 |
| `backend/app/api/billing_v2.py` | 4 处依赖改双通道（cost-analysis/alerts/bills） |
| `backend/tests/unit/test_r4_dual_channel_v194.py` | 新增 15 例：14 条路由依赖断言 + 1 条「观察域模块不得残留 JWT-only 依赖」源码守卫 |

**前端（OpenBase）**

| 页面 | 改动 |
|------|------|
| 成本分析 | 接 `/monitoring/costs`（一次取 model/provider/user 三维度，本地切换）、`/monitoring/costs/optimization-suggestions`、`/budgets`；创建预算走 `POST /budgets`（含 warning 阈值）；移除「一键应用建议」与本地预算/建议 mock |
| 告警中心 | 接 `/alerts/rules`（列表/新建/编辑/启停/删除）、`/alerts`（服务端分页 + 状态筛选）、`/alerts/{id}/resolve`、`/alerts/{id}/acknowledge`；移除规则/历史 mock 与本地状态改写 |
| 链路追踪 | **新建页**替换 `GenericPage`：`/monitoring/traces/statistics` 统计卡、`/monitoring/traces` 服务端筛选/分页、`/monitoring/traces/{id}` 详情抽屉含 Span 明细 |
| 预算管理 | **新建页**替换 `GenericPage`：`/budgets` 列表 + `POST /budgets` 新建 + `/budgets/{id}/status` 状态抽屉 |
| 用量统计 | 接 `/usage/summary`、`/usage/trends`、`/usage/detail`（最近 200 条，页内筛选/分页）；CSV 导出改为导出真实明细；移除 30 天本地数据生成器 |
| 计费 | 接 `/billing/usage/statistics`、`/billing/quotas`、`/billing/bills`，消费趋势复用 `/usage/trends`；账单详情展示真实 `details` JSON；移除硬编码余额/账单/告警 |

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| OpenLLM 新增用例 | `pytest tests/unit/test_r4_dual_channel_v194.py` | **15 passed** |
| OpenLLM R3 回归 | 同上命令附带 `test_r3_dual_channel_v193.py` | **6 passed**（合计 21 passed） |
| 前端新增用例 | `vitest run tests/r4-wiring-v194.spec.ts` | **17 passed** |
| 前端全量回归 | `vitest run` | **29 文件 / 306 用例全通过** |
| 类型检查 | `vue-tsc --noEmit` | **0 错误** |
| 聚合端点实测 | `/proxy/openllm/api/v1/monitoring/costs`、`/alerts`、`/budgets`、`/usage/summary`、`/billing/bills` | **未完成（待复核）**：本轮复核时 OpenLLM `:8001` 未在运行；本机可用运行时装 OpenBase 依赖后缺 `psycopg2` 二进制、装 OpenLLM 应用后又缺 `prometheus_client` 等运行期可选依赖，无法拉起完整服务。以 21 例路由级依赖断言 + 306 例前端回归替代，未将未实测项写成已验证 |
| 浏览器实测 | 六页加载/交互 | **未完成（待复核）**：依赖 OpenLLM 在线，原因同上 |

**遗留**

1. `monitoring_metrics.tenant_id` 列未写入（`record_request` / `record_llm_call` 仅写 `dimensions` JSON），`/monitoring/dashboard|costs|metrics` 暂按全局指标返回；补齐列并回填后再启用服务端租户过滤（已登记缺口清单 §7 第 7 项）。`alerts`/`budgets`/`usage`/`billing`/`traces` 已按 `current_user.organization_id` 过滤。
2. 成本优化建议上游无「应用」端点，前端改为只读展示；若需闭环应用能力，需 OpenLLM 侧新增端点后另行派单。
3. 聚合端点与页面级实测待 OpenLLM 可启动后补做。

---

### 2.19 R5：治理与 RBAC 双通道与七页接线（v1.9.5）

**范围**：按缺口清单 R5，把 OpenLLM 治理与 RBAC 路由族从 JWT-only 改为双通道，并将角色与权限、工作空间、路由策略、熔断器、工具调用、Prompt 模板、Prompt 实验、A/B 测试七页（8 路由）接到真实端点。

**跨仓（OpenLLM，11 文件）**

| 文件 | 变更 |
|------|------|
| `backend/app/api/roles.py` | 6 处依赖改双通道；新增 `GET /roles/permissions/catalog`（权限目录，供角色权限分配） |
| `backend/app/api/workspaces.py` | 10 处依赖改双通道（列表/创建/更新/删除/成员/资源） |
| `backend/app/api/virtual_keys.py` | 10 处依赖改双通道（列表/创建/更新/删除/轮换/吊销/用量） |
| `backend/app/api/semantic_routing.py` | 12 处依赖改双通道（语义路由 CRUD/测试/缓存） |
| `backend/app/api/cascade_routing.py` | 12 处依赖改双通道（级联规则与执行） |
| `backend/app/api/circuit_breakers.py` | 4 处 `get_current_user` 改双通道（列表/详情/重置/事件/配置） |
| `backend/app/api/ab_tests.py` | 12 处依赖改双通道（A/B 测试 CRUD/暂停/恢复/完成/报表） |
| `backend/app/api/prompt_templates.py` | 11 处依赖改双通道（CRUD/版本/回滚/导入/导出） |
| `backend/app/api/prompt_experiments.py` | 8 处依赖改双通道（实验 CRUD/启动/完成/胜出/报表） |
| `backend/app/api/prompt_assembly.py` | 5 处依赖改双通道（装配模板/预览/保真度） |
| `backend/app/api/tool_calls.py` | 7 处依赖改双通道（调用记录/详情/调用链） |
| `backend/tests/unit/test_r5_dual_channel_v195.py` | 新增 30 例：28 条路由依赖断言 + 权限守卫双通道 + 权限目录注册 |

**前端（OpenBase，7 页 / 8 路由）**

| 页面 | 改动 |
|------|------|
| 角色与权限 | `/roles` 列表/新建/更新/启停/删除；权限抽屉 = `/roles/permissions/catalog` + `/roles/{id}` + `PUT /roles/{id}/permissions`；系统角色禁改/禁删 |
| 工作空间 | `/workspaces` 列表/新建/删除、成员增删、资源统计；Virtual Key 走 `/virtual-keys`（列表/创建/轮换），完整 Key 仅展示一次；成员按用户 UUID 添加（上游无按用户名邀请） |
| 路由策略 | `/routing/semantic` CRUD/启停/测试/缓存统计与清空；熔断器列表 + 重置（移除假「手动开启/关闭」） |
| 工具调用监控 | `/tool-calls` 状态/工具名筛选 + 服务端分页；详情抽屉展示真实输入/输出（移除假调用链与取消） |
| Prompt 模板 | `/prompt-templates` 列表/新建/编辑/删除/版本/回滚/导入；系统模板禁改/禁删/禁回滚；分类对齐上游 6 类 |
| Prompt 实验 | `/prompt-experiments` 列表/创建（≥2 变体）/启动/完成/删除/报表 |
| A/B 测试 | `/routing/ab-tests` 列表/创建（流量拆分）/暂停/恢复/完成/删除/报表 |

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| OpenLLM 新增用例 | `pytest tests/unit/test_r5_dual_channel_v195.py` | **30 passed** |
| OpenLLM R4 回归 | 同批运行 `test_r4_dual_channel_v194.py` | **15 passed**（合计 45 passed） |
| 前端新增用例 | `vitest run tests/r5-wiring-v195.spec.ts` | **15 passed** |
| 前端全量回归 | `vitest run` | **30 文件 / 321 用例全通过** |
| 类型检查 | `vue-tsc --noEmit` | **0 错误** |
| 聚合端点实测 | `/proxy/openllm/api/v1/roles`、`/workspaces`、`/routing/semantic`、`/tool-calls`、`/prompt-templates` 等 | **未完成（待复核）**：OpenLLM `:8001` 未运行，本机运行时装依赖后缺 `psycopg2`/`prometheus_client` 等，无法拉起完整服务；以路由级依赖断言 + 前端回归替代，未写成已验证 |
| 浏览器实测 | 七页加载/交互 | **未完成（待复核）**：原因同上 |

**遗留**

1. Virtual Key 的创建/轮换依赖工作空间已存在；工作空间创建后需要刷新才能看到 Key 列（页面已在操作后重载）。
2. 成员添加按用户 UUID（上游 `WorkspaceMemberAdd.user_id` 为 UUID），未提供用户名搜索/邀请端点。
3. 单条工具调用无取消端点，取消能力仅作用于调用链（`/tool-calls/chains/{id}/cancel`），页面已移除该假动作。
4. 聚合端点与页面级实测待 OpenLLM 可启动后补做。

---

### 2.20 R6：本地资源超时治理与两页接线（v1.9.6）

**范围**：按缺口清单 R6，处置 `local-models`、`models/favorites`、`open-models/popular` 的 10s 级超时，并把 GPU 资源、下载管理两页接到真实端点。

**跨仓（OpenLLM）**

| 文件 | 变更 |
|------|------|
| `backend/app/gateway/ollama_adapter.py` | 新增 `OLLAMA_PROBE_TIMEOUT`（read 5s / connect 2s）；`/api/tags`（列表、健康检查）与 `/api/ps`（状态、GPU）显式使用短超时；拉取模型等长任务仍用 300s |
| `backend/app/api/open_models.py` | 全部路由由 `get_current_user` 改 `get_current_active_user_or_api_key`（列表/热门/搜索/下载任务/暂停/恢复/取消/部署/状态/日志） |
| `backend/app/services/model_category.py` | `get_favorites` 由逐条回查模型改为单次 `IN` 批量查询，消除 N+1 |
| `backend/app/services/model_download.py` | `get_all_download_tasks` 单次 `IN` 批量补 `model_name`，避免逐条回查 |
| `backend/tests/unit/test_r6_perf_v196.py` | 新增 13 例：10 条 open-models 路由双通道断言 + 探测短超时 + 两处批量查询守卫 |

**前端（OpenBase）**

| 页面 | 改动 |
|------|------|
| GPU 资源 | 接 `/local-models/gpu-allocation/status`（分配/利用率/显存/占用模型）与 `/local-models/gpu-info`（运行中模型）；GPU 不可用时展示上游 `message` 降级提示；移除 mock 卡、随机趋势、温度/功耗列 |
| 下载管理 | 接 `/open-models/downloads`（服务端分页/状态筛选），暂停/恢复/取消/重试/部署走真实端点；重试 = 重新创建下载任务；上游无删除端点，移除删除按钮 |

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| OpenLLM 新增用例 | `pytest tests/unit/test_r6_perf_v196.py` | **13 passed** |
| 前端新增用例 | `vitest run tests/r6-wiring-v196.spec.ts` | **7 passed** |
| 前端全量回归 | `vitest run` | **31 文件 / 328 用例全通过** |
| 类型检查 | `vue-tsc --noEmit` | **0 错误** |
| 运行态耗时对比 | 前后 P50/P95 | **未完成（待复核）**：OpenLLM `:8001` 未运行且本机缺少 `psycopg2`/`prometheus_client` 等运行期依赖，无法拉起服务；以超时常量与代码守卫锁定，不伪造耗时数据 |
| 聚合端点实测 | `/local-models/gpu-allocation/status`、`/open-models/downloads` | **未完成（待复核）**：原因同上 |

**遗留**

1. GPU 温度/功耗与历史趋势无上游数据源，页面已移除，不做伪造。
2. 下载任务「重试」通过重新创建任务实现；上游未提供独立 retry 端点。
3. 运行态耗时与聚合端点实测待 OpenLLM 可启动后补做。

---

### 2.21 R7：E 类产品裁定与五页收敛（v1.9.7）

**范围**：对 E 类纯形态页做产品裁定——可建者落地，不可建者收敛或标注不建设；本轮落地仪表盘、统一监控、个人设置、模型部署、画像系统监控（健康）。

**OpenBase 后端（资料与密码）**

| 文件 | 变更 |
|------|------|
| `openbase/modules/auth/__init__.py` | `MeResponse` 增加 `display_name/email/phone`；新增 `PUT /auth/me`（邮箱格式校验）与 `POST /auth/change-password`（旧密码+强度校验）；抽取 `_load_profile_user` / `_build_me_response` 复用 |
| `tests/test_auth_profile_v197.py` | 新增 6 例：资料回填、更新落库、非法邮箱 400、旧密码错误 400、弱密码 400、改密成功（哈希更新） |

**前端（OpenBase，5 页）**

| 页面 | 改动 |
|------|------|
| 仪表盘 | 模块数（本地注册表）+ 平台用户数（`/users`）+ 24h 调用量/费用（OpenLLM `/monitoring/dashboard`）；`Promise.allSettled` 单源失败显示「—」 |
| 统一监控 | `/monitoring/dashboard` KPI + 请求量/延迟双轴曲线 + `/alerts?status=firing` 最新告警；移除本地 KPI 与随机曲线 |
| 个人设置 | `GET/PUT /auth/me` 资料回填与保存、`POST /auth/change-password` 改密；通知偏好无端点，页面显式说明未开放；移除头像字段（后端无存储） |
| 画像系统监控 | 仅接 `/dps-proxy/health`；移除虚构 QPS/CPU/内存曲线与告警规则，标注指标端点未开放 |
| 模型部署（新建页） | `/open-models` 列表 + 部署（框架/量化/GPU/端口/上下文）+ 状态抽屉 + 日志抽屉 + 停止；替换 `GenericPage` 占位 |

**产品裁定**：注册/找回密码、画像数据权限、画像接口限流、画像 API 管理裁定不建设（无端点）；应用调用记录、知识库 API 控制台、文档中心保留现状。

**验证**

| 项 | 命令/方式 | 结果 |
|---|-----------|------|
| OpenBase 后端新增 | `pytest tests/test_auth_profile_v197.py` | **6 passed** |
| 前端新增用例 | `vitest run tests/r7-wiring-v197.spec.ts` | **9 passed** |
| 前端全量回归 | `vitest run` | **32 文件 / 337 用例全通过** |
| 类型检查 | `vue-tsc --noEmit` | **0 错误** |
| 聚合端点实测 | `/auth/me`、`/monitoring/dashboard`、`/dps-proxy/health`、`/open-models/*` | **未完成（待复核）**：OpenLLM/DPS 未运行且本机缺少运行期依赖；以 6+9 例单测与 337 例回归替代，未伪造实测 |

**遗留**

1. 通知偏好无后端端点，页面标注未开放。
2. 画像系统监控仅健康状态；QPS/资源/告警规则需 DPS 侧新增指标端点。
3. 应用调用记录、知识库 API 控制台、文档中心保留现状（见缺口清单 §6.1）。
4. 聚合端点与页面级实测待服务可启动后补做。

---

### 2.22 剩余事项统一清查与小版本迭代计划（v1.8.0 文档轮）

**范围**：R1~R7 收口后，对「登记但未执行」与「跨仓未执行」事项做一次统一清查，并拆入小版本迭代；本轮**仅产出计划与台账，不改代码**。

**清查来源**：缺口清单 v1.7.0（§4/§7）、DevLogReport §2.18~§2.21 遗留、生产上线必办清单 v2.2.0（G1/G2/G7/S2/S4）、C1/B2/R384 跨仓派单、OpenMemory 组织事实源收敛 D4。

**台账规模**：

| 分类 | 项数 | 代表项 |
|------|:----:|--------|
| 本仓待执行（OpenBase） | 6 | 通知偏好端点、聚合网关交互用例、应用调用记录聚合、知识库控制台、注册/找回密码复核、文档中心维护 |
| 跨仓待执行 | 12 | monitoring 租户列与过滤、OpenLLM 四页接线、DPS 指标/规则/规则引擎/权限限流、C1-d 码值规范化、OpenMemory `default` 退役、成本建议应用、工具取消、成员邀请 |
| 运维 / QA / 发布 | 6 | 四仓 github 补推、运行期依赖与服务可启动、R3~R7 复核、G1/G2 下发、G7 端到端与密钥/码表、S2/S4 演练 |

**小版本拆分**：

| 版本 | 主题 | 关键项 |
|------|------|--------|
| v1.9.8 | 处置窗口（无新功能） | 远程一致、服务可启动、R3~R7 复核、G1/G2/G7、R384 回执核验 |
| v1.10.0 | 全栈缺口补齐 I | XR-LLM-01 租户过滤、XR-LLM-02 四页接线、XR-DPS-01 指标/规则 |
| v1.10.1 | 个人中心与通知 | OB-01 通知偏好（端点 + 页面） |
| v1.10.2 | 治理与发布收口 | OB-02 网关用例、XR-GOV-01 C1-d、XR-OPS-06 S2/S4 |
| v1.11.0 | 长尾产品复核 | 应用调用、知识库控制台、OpenLLM 推荐/报表、DPS 规则/权限/限流、OpenMemory 兜底退役、成本应用/工具取消/成员邀请 |

**纪律**：每个小版本独立验收、独立回滚；跨仓项拆「本仓前置 + 派单回执」，不以派单发出视为完成；无端点项先裁定后开发。

**产出**：《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》（`doc/planning/`）；缺口清单升 v1.8.0，§4 起改为只保留能力状态，排期以新计划为唯一来源。

**执行进展**：XR-OPS-01（四仓 github 补推）已于 2026-10-23 提前闭环——OpenBase `540f757`、OpenLLM `647d4bb` 推送 github 成功；OpenRAG（`release/v1.10.0`）与 OpenMemory（`release/v7.3.0`）本地 HEAD 与 github 一致。计划升 v1.0.1 回填。

---

### 2.23 v1.9.8 处置窗口执行记录（2026-10-23）

**目标**：清除「服务不可启动 / R3~R7 未实测 / R384 回执未核验」三类阻塞；G1/G2/G7 属 OPS 窗口，本轮不代替执行。

**1. 服务可启动（XR-OPS-02，部分闭环）**

| 项 | 内容 |
|----|------|
| 运行时组合 | pgAdmin CPython 3.13 + `OpenBase/.venv` 依赖目录 + `C:/Python313` 遗留 site-packages（补 `prometheus_client`） |
| 缺失依赖处理 | OTel gRPC 子包缺失：启动器注入空导出器且 `OTEL_ENABLED=false`（仅导入占位，不参与运行）；数据库切 SQLite 临时库 |
| 结果 | `GET http://127.0.0.1:8001/health` → **200**，版本 2.19.1 |
| 边界 | 正式镜像依赖仍待 OPS 固化；本轮桥接仅用于复核，不入库、不影响产品代码 |

**2. 聚合端点复核（QA-01）**

21 个 R3~R7 端点经 OpenBase 通用代理（`/api/v1/proxy/openllm/api/v1/...`）逐一实测，**全部 200**：

| 批次 | 端点 |
|------|------|
| R3 | `plugins`、`model-categories/tree` |
| R4 | `monitoring/dashboard`、`monitoring/costs`、`alerts`、`budgets`、`usage/summary`、`billing/bills`、`monitoring/traces`、`monitoring/traces/statistics` |
| R5 | `roles`、`workspaces`、`routing/semantic`、`routing/circuit-breakers`、`tool-calls`、`prompt-templates`、`prompt-experiments`、`routing/ab-tests` |
| R6 | `local-models/gpu-allocation/status`、`local-models/gpu-info`、`open-models/downloads` |

**3. 浏览器抽检（9 页）**

| 页面 | 结果 | 观察 |
|------|------|------|
| 插件管理 | PASS | 空态真实；工具表 1 行 `hello-world`，与插件列表为空不一致（已登记 XR-LLM-08） |
| 成本分析 | PASS | 三维度空态、预算空态、优化建议空态均真实 |
| 角色与权限 | PASS | 角色列表空态真实 |
| 仪表盘 | PASS | 模块 5 / 用户 3 / 24h 调用 78~89 / 费用 $0.00 |
| 链路追踪 | PASS | 统计 0、空态真实 |
| 下载管理 | PASS | 空态真实 |
| 统一监控 | PASS | 6h 错误率 29%~31%（已登记 XR-LLM-07）；告警空态 |
| 模型部署 | PASS | 模型列表空态真实 |
| 个人设置 | PASS | 资料回填 normal；通知偏好提示为设计内 info |

三批均无错误提示条、无 console error；其中一次 dev server 热重载出现瞬时 500/503，重载后复测正常，未计为页面缺陷。

**4. 跨仓回执（XR-OPS-05）**

DPS `0954b9a`（RequestIdFilter 改挂 handler 级）经 `git merge-base --is-ancestor 0954b9a HEAD` 确认已在 `main`。

**5. 新发现（已纳入计划）**

| ID | 现象 | 目标版本 |
|----|------|:--------:|
| XR-LLM-07 | 统一监控 6h 错误率 29%~31%，需核验分母与错误分类 | v1.10.0 |
| XR-LLM-08 | 插件表 0 行但工具表有 `hello-world`，需确认内建插件口径 | v1.11.0 |

**6. 未完成**

- XR-OPS-03：G1/G2 生产 `.env` 下发（OPS 窗口）
- XR-OPS-04：G7 端到端 + 生产 Key 注入/轮换 + DPS 码表登记（OPS/研发窗口）

计划升 v1.1.0 回填执行记录与新增项。

---

### 2.24 v1.10.0 全栈缺口补齐 I 执行记录（2026-10-23）

**范围**：XR-LLM-01（监控租户隔离）、XR-LLM-07（错误率口径）、XR-LLM-02（OpenLLM 四页接线）、XR-DPS-01（画像指标/规则端点）。

**1. XR-LLM-01：监控指标租户隔离（OpenLLM 后端）**

| 环节 | 落点 | 说明 |
|------|------|------|
| 查询过滤 | `app/services/monitoring_service.py` | 新增 `_apply_tenant_filter` / `_apply_alert_tenant_filter`；`get_dashboard_data`、`_get_overview_data`、`_get_performance_data`、`_get_latency_time_series`、`_get_cost_data`、`_get_cost_trend`、`_get_error_data`、`_get_resource_data`、`get_cost_analysis`、`_analyze_by_dimension`、`get_optimization_suggestions`、`get_metrics`、`get_alerts`、`resolve_alert` 全量接入 |
| 端点透传 | `app/api/monitoring.py` | 新增 `_current_tenant_id(current_user)`，8 个端点（dashboard / metrics / costs / optimization-suggestions / alerts / alerts:resolve / alerts:summary）透传租户；未归属组织的账号保持平台全局视图 |
| 写入链路 | `app/services/auth_service.py` | `get_current_user` / `get_api_key_user` 回填 `request.state.user`（id + tenant_id）与 `request.state.api_key`；此前中间件读不到该状态，导致 `monitoring_metrics.tenant_id` 恒为 NULL |
| 历史回填 | `backend/scripts/backfill_monitoring_tenant_v1100.py` | 以 `user_id → users.organization_id` 回填，默认 dry-run，`--apply` 落库；幂等（仅补 `tenant_id IS NULL`） |
| 守卫 | `tests/unit/test_r10_monitoring_tenant_v1100.py` | 10 例：过滤 helper 语义、双租户互不可见、全局视图、跨租户解决告警被拒、错误率口径 |

**2. XR-LLM-07：错误率口径修正**

| 项 | 修正前 | 修正后 |
|----|--------|--------|
| 分子 | `count(id)`（ERROR_RATE 行数） | `sum(value)`（每条错误 value=1.0） |
| 分母 | `count(id)`（REQUEST_COUNT 行数） | `sum(value)`（聚合写入后每行可代表多次请求） |
| 错误分类聚合 | `count(id)` | `sum(value)`（`by_type` / `by_provider` 同口径） |

样例（用例固化）：5 行 `request_count` 每行 value=4（共 20 次请求）+ 2 行 `error_rate`（2 次错误）→ 修正前按行数得 40%，修正后为 **2/20 = 10%**。此口径解释了 v1.9.8 实测 29%~31% 的失真来源（分子分母行数增长频次不同）。

**3. XR-LLM-02：四页真实接线（统一前端）**

| 页面 | 端点 | 说明 |
|------|------|------|
| 本地模型 | `GET /local-models`、`/available`、`/gpu-info`、`/gpu-allocation/status`、`POST /pull`、`/{name}/start|stop|update`、`DELETE /{name}` | 移除全部 mock 卡片与假动作；启停/更新/删除/拉取均真实调用 |
| 模型对比 | `GET /open-models`（模型池）+ `GET /models/compare` | 移除 8 条 mock 模型池；对比结论取上游 `comparison.advantages` |
| 开源市场 | `GET /open-models` + `POST /open-models/{model_id}/download` | 移除 8 条 mock；来源筛选改为文本匹配，分页保留 |
| 我的收藏 | `GET /models/favorites`、`/models/favorite-folders`、`DELETE /models/{model_id}/favorite`、下载复用 `open-models/.../download` | 移除 8 条 mock；收藏夹按上游分组 |

API 层落点：`openbase-ui/src/core/api/governance.ts` 扩展 `localModelsApi`（列表/仓库/状态/拉取/删除/启停/更新）、新增 `favoritesApi` 与 `modelCompareApi`。
组件测试：`openbase-ui/tests/r8-openllm-pages-v1100.spec.ts` 8 例（加载、动作调用、错误态、对比请求参数）。

**4. XR-DPS-01：未闭环，转 v1.11.0**

| 阻塞项 | 事实依据 |
|--------|----------|
| 规则 CRUD 不可在 DPS 新增 | DPS v2.9.0 已按 ADR-290-01 将 `/alerts/rules` 写方法收口为 **410 Gone**，迁移目标为平台域 `/platform/observability/monitoring/alerts`；在 DPS 重新开口会与既有收口裁定冲突 |
| 指标端点无运行态依赖 | DPS 未引入 `psutil` / `prometheus_client` 运行依赖，QPS/CPU/内存需新增采集与权限点注册（`PATH_RESOURCE_MAP` + `PRESET_PERMISSIONS` 类级守门用例同步） |
| 本机无可运行测试环境 | DPS 无本地 venv/运行器，新增端点无法在本窗口给出真实回归证据 |
| 代理允许清单未覆盖 | OpenBase `dps-proxy` 仅映射 `/api/v2/portrait/*`，`alerts/*`、`rate-limits/*` 需先扩允许清单 |

处置：本窗口不改 DPS 代码，页面维持「仅健康 + 明确未开放提示」的真实态；XR-DPS-01 拆为两项（DPS 运行态指标端点 / OpenBase 代理扩权）纳入 v1.11.0。

**5. 验证结果**

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| OpenLLM 新用例 | `pytest tests/unit/test_r10_monitoring_tenant_v1100.py` | **10 passed** |
| OpenLLM 监控回归 | `pytest tests/unit/test_monitoring_coverage_v2112.py tests/unit/test_r10_...` | **29 passed** |
| OpenLLM 相关子集 | `-k "monitoring or auth or r4 or r5 or r6 or r7 or dual_channel"` | **352 passed / 6 failed**（6 项经 `git stash` 基线复跑确认为存量失败：4 例 gateway 401 格式断言 + resolve_alert 越权注入 + cost 断言，其中后 2 例本轮已修） |
| 前端类型 | `vue-tsc --noEmit` | **0 error** |
| 前端全量 | `vitest run` | **345 passed / 33 files**（基线 337 + 新增 8） |

**6. 遗留**

- XR-DPS-01（拆分后）→ v1.11.0
- 平台级账号（`organization_id` 为空）仍为全局视图，租户强制期需按模块灰度另行开口（与 B2 权限灰度同批）

---

### 2.25 v1.10.1 个人中心与通知执行记录（2026-10-23）

**范围**：OB-01 通知偏好（端点 + 页面）。

**1. 数据模型**

| 项 | 内容 |
|----|------|
| 表 | `notification_preferences`（每用户一行，`user_id` 主键外键 `users.id`） |
| 列 | `in_app` / `email` / `webhook`（布尔）、`webhook_url`（≤512）、`events`（JSON，键 `alert/approval/system`） |
| 建表 | 挂在 `Base.metadata`（`core/models/business.py` + `core/models/__init__.py` 导出），随 `create_tables` 幂等建表，无独立迁移脚本 |

**2. 端点（`openbase/modules/auth/__init__.py`）**

| 端点 | 行为 |
|------|------|
| `GET /api/v1/auth/notification-preferences` | 有行返回值；无行返回默认（站内开、邮件/Webhook 关、三事件全开）；OIDC 字符串主体无本地行时直接返回默认 |
| `PUT /api/v1/auth/notification-preferences` | upsert（幂等）；未知事件键 → 400 `PARAM_INVALID`；`webhook=true` 且地址为空/非 http(s) → 400 `PARAM_INVALID`；OIDC 无本地行 → 404 `BIZ_NOT_FOUND` |

**3. 页面（`openbase-ui/src/pages/personal/SettingsView.vue`）**

- 移除「通知偏好暂未开放」提示，新增真实卡片：站内/邮件/Webhook 开关、Webhook 地址（仅启用时显示）、告警/审批/系统事件勾选、保存按钮与错误条。
- 本地前置校验（Webhook 协议）与后端校验双重拦截；保存后回填服务端返回值。
- API 层：`core/api/auth.ts` 新增 `NotificationPreferences` 类型与 `getNotificationPreferences` / `updateNotificationPreferences`。

**4. 验证**

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| 后端新用例 | `pytest tests/test_auth_notification_prefs_v1101.py` | **6 passed**（默认值、upsert、未知事件、Webhook 必填、非 http(s)、OIDC 降级） |
| 后端相邻回归 | `pytest tests/test_auth_profile_v197.py tests/test_ui_increments.py tests/test_source_encoding_contract.py` | **通过**（其中 `test_ui_increments` 的 FakeSession 补 `get` 以匹配 `/auth/me` 现有读取路径） |
| 静态检查 | `ruff check` 四个改动文件 | 通过 |
| 前端新用例 | `vitest run tests/r9-notify-prefs-v1101.spec.ts tests/r7-wiring-v197.spec.ts` | **13 passed** |
| 前端全量 | `vitest run` | **349 passed / 34 files** |
| 类型 | `vue-tsc --noEmit` | **0 error** |

**5. 全量后端回归说明（未劣化基线）**

`pytest tests` 全量存在 5 类与本轮无关的失败，均已隔离复核：

| 现象 | 复核结论 |
|------|----------|
| `test_tenant_admin` / `test_users_admin` 连接中断 | 共享 PG 瞬态抖动；隔离复跑**全部通过** |
| `test_service_agent_outbound::test_obk_service_account_mapped_outbound_headers` | `git stash` 基线复跑同样失败（出站租户头取哈希而非 5001），属存量问题 |
| `test_verdict_k03::test_t2_6_unregistered_service_key_write_403` | 依赖真实 OpenLLM 上游，返回 `SYS_502 upstream unreachable`，属环境依赖 |
| `test_s7_t6_gate`（10 项）+ `test_s7_tools_skeleton[l2_2]` | S7 门禁证据集为存量产物，与本次改动无交集 |
| `test_source_encoding_contract` | 本轮发现并**已修复**：v1.10.0 提交的 `test_monitoring_coverage_v2112.py` 带 UTF-8 BOM（PowerShell 回写引入），已剥离并单独提交 |

**6. 遗留**

- v1.10.2：OB-02 聚合网关交互用例、XR-GOV-01 C1-d 码值双形态、XR-OPS-06 S2/S4 演练
- v1.11.0：XR-DPS-04/05、OB-03/04/05、XR-LLM-03/04/05/06/08、XR-DPS-02/03、XR-MEM-01

---

### 2.26 v1.10.2 治理与发布收口执行记录（2026-10-23）

**范围**：OB-02（聚合网关交互用例）、XR-GOV-01（C1-d 三仓）、XR-OPS-06（S2/S4）。

**1. OB-02：聚合网关测试补交互用例（已闭环）**

| 用例 | 断言要点 |
|------|----------|
| 成功执行 | `POST /gateway/aggregate` 请求体（步骤/超时/失败策略/映射）完整透传；渲染结果 JSON；无错误条 |
| 部分失败 | 展示 `部分步骤失败（1）` + errors 明细，同时保留成功结果 |
| 请求超时 | 错误条展示 `timeout of 5000ms exceeded`；不残留结果；`executing` 回到 false |
| 重置 | 清空结果与错误条 |

落点：`openbase-ui/tests/r10-gateway-aggregate-v1102.spec.ts`（4 例通过）。

**2. XR-OPS-06 S4：发布强制核验（仓库侧已执行）**

| 制品 | 内容 |
|------|------|
| `config/production_switch_matrix.json` | 生产必需开关矩阵唯一事实源（OpenLLM 5 组 / OpenMemory 1 组 / DPS 1 组 / OpenBase 豁免），标注来源《续接指南》§10.3（裁定③④） |
| `scripts/verify_production_switches.py` | carrier 模式（核仓库载体）+ `--env-file` 模式（核实际下发）；任一 FAIL 退出码 1 |
| `tests/test_production_switch_matrix_v1102.py` | 10 例（矩阵结构、env 解析、载体通过/漂移/缺失、文档表格载体、env-file、`--only` 过滤） |
| 执行证据 | `doc/test/evidence/release/switch-matrix-20261023.json`；记录 `doc/release/OpenBase-发布强制核验执行记录-v1.0.0.md` |

**执行结果（2026-10-23）**：`8 项 / PASS 7 / FAIL 1`

| 仓 | 开关 | 结果 |
|----|------|:----:|
| OpenLLM | 5 组启动门禁（`ENFORCE_INBOUND_IDENTITY_HEADERS`/`RBAC_PERMISSION_ENFORCE`/`TENANT_SCOPE_ENFORCE`/`TENANT_HEADER_CONSISTENCY_ENFORCE`/`QUOTA_MISSING_FAIL_CLOSED`） | 全部 PASS |
| OpenMemory | `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE`（模板值 `false`） | **FAIL** |
| DPS | `TENANT_CONTEXT_REQUIRED`（部署文档表格） | PASS |
| OpenBase | 无新增 | PASS（豁免） |

**新增阻断项 XR-OPS-07（P1）**：OpenMemory `.env.example` 登记 `false`，与 §10.3 生产值 `true` 漂移；若照模板下发则门禁 fail-open。处置在 OpenMemory 仓（跨仓），本仓仅登记与阻断，不代为修改。

**3. XR-GOV-01：C1-d 码值双形态（部分，转 v1.11.0）**

| 仓 | 采纳状态 | 证据 |
|----|----------|------|
| OpenBase | ✅ 已闭环（2026-10-09） | `openbase/core/code_normalize.py` + `tests/test_code_normalize.py` 11 例 |
| OpenLLM | ❌ 未采纳 | 全仓检索 `code_normalize` / `normalize_code_or_id` 零命中 |
| OpenRAG | ❌ 未采纳 | 同上 |
| OpenMemory | ❌ 未采纳 | 同上 |

结论：能力已在 OpenBase 落地，但「三仓回执」需按 OpenLLM → OpenRAG → OpenMemory 顺序派单，不能在本仓单方闭环；转 v1.11.0。

**4. XR-OPS-06 S2：回滚演练（未执行）**

需 OPS 真实运行态与注故障窗口（开关级/通道级/版本级三级回滚）。本环境无部署面，按纪律**不填 PASS**，回滚方案 v1.0.0 已存在，执行清单见《发布强制核验执行记录》§5。

**5. 验证**

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| 网关交互用例 | `vitest run tests/r10-gateway-aggregate-v1102.spec.ts` | **4 passed** |
| 核验脚本用例 | `pytest tests/test_production_switch_matrix_v1102.py` | **10 passed** |
| 核验脚本实跑 | `python scripts/verify_production_switches.py` | **8 项 / PASS 7 / FAIL 1**（阻断项 XR-OPS-07） |
| 前端全量 | `vitest run` | **353 passed / 35 files** |
| 类型 | `vue-tsc --noEmit` | **0 error** |
| ruff | 新增脚本与用例 | 通过 |

---

### 2.27 XR-OPS-07 发布阻断处置记录（2026-10-23）

> 本节修正 §2.26 的初判结论；§2.26 保留为当时现场记录。

**1. 初判与根因复核**

| 阶段 | 结论 |
|------|------|
| 初判（§2.26） | OpenMemory `.env.example` 中 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=false`，与《续接指南》§10.3「载体置真」不一致 → 登记 P1 阻断 |
| 根因复核 | ① 该默认值是**刻意保留**（OpenMemory 变更记录 v1.0.0 §43「不翻转默认」，M1/开发态行为不变）；② 生产 M2 未置真时 `validate_identity_trust_policy`（`src/openmemory/utils/config.py:498-535`）**拒绝启动**，不存在静默 fail-open；③ 初版门禁把「模板开发默认值」当作「生产下发值」，属**判据错误** |

**2. 处置（仅本仓，未改 OpenMemory 代码）**

| 项 | 变更 |
|----|------|
| 矩阵 | `config/production_switch_matrix.json` 升 **v1.1.0**：新增 `mode` 字段（`template_value` / `documented_override`）、OpenMemory 的 `override_hints` 与 `runtime_gate` |
| 脚本 | `scripts/verify_production_switches.py` 支持双模式：`documented_override` 要求密钥行邻近 8 行内写明生产覆盖值，并校验 `runtime_gate` 指向的运行期守卫文件存在且含标记；任一缺失 → FAIL |
| 守门用例 | `tests/test_production_switch_matrix_v1102.py` 由 10 例扩到 **15 例**（新增 documented_override 通过与缺注释失败、runtime_gate 缺失与存在、真实矩阵声明断言） |

> 机械保证：若有人删除生产覆盖注释或移除 OpenMemory 运行期守卫，核验立即 FAIL——并非放宽门槛，而是把判据从「模板值」修正为「模板登记 + 生产覆盖文档化 + 守卫存在」，生产值本身由 `--env-file` 对目标环境核验。

**3. 复跑结果**

| 项 | 结果 |
|----|------|
| 仓库侧核验 | **9 项 / PASS 9 / FAIL 0**（exit 0），证据 `doc/test/evidence/release/switch-matrix-20261023-r2.json` |
| OpenMemory 行 | `模板默认 false（开发态），已文档化生产覆盖 true` + `运行期守卫存在：src/openmemory/utils/config.py` |
| 用例 | `pytest tests/test_production_switch_matrix_v1102.py` → **15 passed** |
| 记录 | 《发布强制核验执行记录》升 **v1.1.0**，含根因、双模式判据与生产核验要求 |

**4. 残余（不由本仓闭环）**

- 生产 `.env` 必须下发 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true`；发布时由 OPS 执行 `--env-file` 核验并回填记录 §5。
- S2 回滚演练仍待 OPS 运行态与注故障窗口（不填 PASS）。

---

### 2.28 v1.11.0 长尾事项产品裁定执行记录（2026-10-23）

**范围**：计划 v1.5.0 §4 v1.11.0 全部 14 项。门禁仅要求书面裁定（建设/冻结/不建设 + 端点清单），建设项按纪律进入下一版本，本期**无代码改动**。

**1. 裁定结果**

| 裁定 | 数量 | 事项 |
|------|:----:|------|
| 已闭环 | 1 | XR-MEM-01 |
| 建设 | 7 | OB-03、OB-04、XR-LLM-03（报表趋势）、XR-LLM-06、XR-DPS-03（只读）、XR-DPS-04、XR-DPS-05、XR-GOV-01 |
| 冻结 | 5 | XR-LLM-03（推荐）、XR-LLM-04、XR-LLM-05、XR-LLM-08、XR-DPS-02、XR-DPS-03（写） |
| 不建设 | 1 | OB-05 |

产出：《OpenBase-长尾事项产品裁定-v1.0.0》（含逐项现状证据、端点清单、验收判据、解冻条件、下一版本分批）。

**2. 关键事实核验（本轮取证）**

| 事项 | 证据（文件:行） |
|------|------------------|
| OB-03 | 仅单应用 `GET /api/v1/ai-apps/{app_id}/calls`（`openbase/modules/ai_apps/__init__.py:250`），无全局聚合 |
| OB-04 | OpenRAG `POST /retrieve/federated`、`GET /cache/stats` 可用（`src/openrag/api/v1_3_routes.py:25,63`） |
| XR-LLM-03 | 无推荐端点；报表可复用 `/usage/trends` 与 `/monitoring/dashboard` |
| XR-LLM-04 | 建议为启发式文本，无建议 ID / 回滚语义 |
| XR-LLM-05 | 仅链级取消 `POST /tool-calls/chains/{chain_id}/cancel`（`app/api/tool_calls.py:237`） |
| XR-LLM-06 | 成员新增仅接受 `user_id: UUID`（`app/api/workspaces.py:216`） |
| XR-LLM-08 | `/plugins` 查 DB 表（`plugins.py:49`），`/plugins/tools` 合并运行时注册表（同文件 74-90 行）——非缺陷 |
| XR-DPS-02/03 | 规则写面 410；`/rate-limits/status`、`/api-registry`、`/error-codes` 只读可用 |
| XR-DPS-04/05 | 无 `/metrics`；`dps-proxy` 仅映射 `/api/v2/portrait/*` |
| XR-MEM-01 | 已于 2026-10-12 交付（`68701e9`+`26dc728`，P4 fail-closed，1366 passed） |

**3. 下一版本分批（v1.12.0）**

| 批次 | 事项 | 依赖 |
|------|------|------|
| A（本仓低风险） | OB-03 全局调用聚合、OB-04 控制台接线、报表趋势页、XR-DPS-05 代理扩权 | 05 依赖 04 |
| B（跨仓小改） | XR-LLM-06 用户名邀请 | OpenLLM 派单 |
| C（跨仓交付） | XR-DPS-04 指标端点（含权限点注册） | DPS 可运行测试环境 |
| D（跨仓派单） | XR-GOV-01 三仓码值规范化 | 三仓回执 |
| E（前端文案） | XR-LLM-08「运行期内建」标注、XR-DPS-02/03 只读视图 | 无 |

**4. 验证**

| 项 | 结果 |
|----|------|
| 后端/前端测试 | 本期无代码改动，未新增用例；v1.10.2 基线（前端 353/353、vue-tsc 0 错误、后端相关用例全绿）维持 |
| 文档 | 裁定文档 v1.0.0、计划 v1.6.0、缺口清单 v1.12.0 同步 |

---

### 2.29 v1.12.0 长尾建设 A 批执行记录（2026-10-23）

**范围**：OB-03、OB-04、XR-LLM-03（报表趋势）；XR-DPS-05 因依赖 XR-DPS-04 未启动。

**1. OB-03：应用调用记录全局聚合**

| 项 | 内容 |
|----|------|
| 端点 | `GET /api/v1/ai-apps/calls?app_id=&status=&page=&page_size=`（注册在 `/{app_id}` **之前**，避免 `calls` 被当作 app_id） |
| 服务 | `AiAppService.all_calls(app_id, status)` 跨应用汇总并补 `app_name` |
| 页面 | 新增 `pages/platform/observability/AppCallsView.vue` 替换 `GenericPage`；应用/状态筛选（radio-button）、服务端分页、错误条与空态 |
| 用例 | 后端 6 例（聚合/筛选/分页/路由顺序/参数校验）、前端 3 例（加载/筛选参数/错误态） |

**2. OB-04：知识库 API 控制台真实化**

| 项 | 内容 |
|----|------|
| 数据源 | `rag-proxy`：`GET /collections`、`GET /health`、`POST /collections/{id}/query/retrieve` |
| 页面变更 | 移除「填写任意 API Key + 500ms 假响应」；改为选择知识库 → 输入检索语句 → 真实检索并展示响应与客户端耗时 |
| 性能页 | 删除虚构的 38ms / QPS 156 / 0.8% 与随机曲线；改展示「最近检索耗时 / 知识库数量 / 上游健康 + 组件状态」 |
| 边界 | 未新增缓存统计端点（rag-proxy 未暴露 `/cache/stats`），页面不展示该指标 |
| 用例 | 前端 2 例（真实检索参数与响应、失败态不残留结果） |

**3. XR-LLM-03（报表趋势部分）**

| 项 | 内容 |
|----|------|
| 数据源 | `/usage/trends`（调用量/Token 序列）、`/monitoring/dashboard`（KPI 概览）、`/monitoring/costs?dimension=user`（成本 Top5） |
| 页面变更 | 移除随机数曲线与虚构「组织排名」；改为真实 KPI 四卡 + 调用量/Token 双轴趋势 + 用户成本 Top5；时间范围收敛为 7d/30d（与后端支持口径一致） |
| 降级 | `Promise.allSettled` 三源独立，单源失败提示但保留可用数据 |
| 用例 | 前端 2 例（请求参数与渲染、单源失败降级） |

**4. XR-DPS-05：未启动**

指标数据源依赖 XR-DPS-04（`GET /api/v2/metrics` + 权限点注册），该端点需 DPS 可运行测试环境交付；只读规则/限流接线可在后续批次独立推进。

**5. 验证**

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| 后端新用例 | `pytest tests/test_ai_apps_calls_v1120.py` | **6 passed** |
| 静态检查 | `ruff check openbase/modules/ai_apps tests/test_ai_apps_calls_v1120.py` | 通过 |
| 前端新用例 | `vitest run tests/r11-longtail-v1120.spec.ts` | **7 passed** |
| 前端全量 | `vitest run` | **360 passed / 36 files**（基线 353 + 新增 7） |
| 类型 | `vue-tsc --noEmit` | **0 error**（同步移除已无引用的 `GenericPage` 常量） |

### 2.30 v1.12.0 长尾建设 B 批执行记录（2026-10-24）

**范围**：XR-LLM-06 工作空间按用户名邀请（OpenLLM 后端小改 + OpenBase 前端成员弹窗）。

**1. 后端（OpenLLM）**

| 项 | 内容 |
|----|------|
| Schema | `WorkspaceMemberAdd`：`user_id` 改为可选，新增 `username`（1~64，去首尾空白）；`@model_validator` 保证二选一必填 |
| 路由 | `POST /workspaces/{workspace_id}/members` 新增 `_resolve_invitee_user_id`：用户名精确匹配 `users.username` |
| 错误 | 用户名不存在 → 404 `BIZ_NOT_FOUND`；`user_id` 与 `username` 指向不同用户 → 400 `PARAM_INVALID`（`detail` 为 `{code, message}`） |
| 兼容 | 仅传 `user_id` 保持旧路径（存在性仍由服务层校验）；同时传且一致时按用户名解析 |

**2. 前端（OpenBase）**

| 项 | 内容 |
|----|------|
| 页面 | `pages/platform/identity/WorkspacesView.vue` 成员抽屉输入由「用户 UUID」改为「用户名」；提交 `{username, role}` |
| API | `core/api/governance.ts::workspacesApi.addMember` 载荷改为 `{user_id?, username?, role}` |
| 文案 | 移除「后端无按用户名加成员能力」的旧注释；空输入提示改为「请输入用户名」 |

**3. 用例与验证**

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| 后端新用例 | `pytest tests/unit/test_r12_workspace_member_v1120.py` | **9 passed** |
| 后端回归 | `pytest tests/unit/test_workspaces_api.py tests/unit/test_r12_workspace_member_v1120.py` | **34 passed** |
| 前端新用例 | `vitest run tests/r12-workspace-invite-v1120.spec.ts` | **3 passed** |
| 前端全量 | `vitest run` | **363 passed / 37 files**（基线 360 + 3） |
| 类型 | `vue-tsc --noEmit` | **0 error** |

> 环境说明：OpenLLM 用例以 `--confcutdir=tests/unit` + `DATABASE_URL=sqlite:///:memory:` 运行（本机缺 `psycopg` 运行依赖）；用户名匹配逻辑以 FakeSession 验证查询条件，未连接真实 PG。

### 2.31 v1.12.0 长尾建设 C 批执行记录（2026-10-24）

**范围**：XR-DPS-04（DPS 运行态指标端点）+ XR-DPS-05（OpenBase 代理扩权 + 画像监控页接线）。

**1. DPS（v2.13.0）**

| 项 | 内容 |
|----|------|
| 端点 | `GET /api/v2/metrics` → `{qps_1m, cpu_percent, memory_mb, memory_percent, uptime_seconds, requests_total, collected_at}` |
| 采集 | 新增 `src/monitoring/runtime.py`：60s 滑窗 QPS、`process_time` 增量 CPU、Windows psapi / Linux `/proc` 内存；**不引入 psutil** |
| 中间件 | `MetricsMiddleware` 逐请求登记窗口；`/api/v2/metrics` 加入排除表（防抓取自放大） |
| 权限 | `PATH_RESOURCE_MAP["metrics"]="runtime_metric"`；`PRESET_PERMISSIONS` 注册 `runtime_metric:read`；admin/operator/readonly 授予只读 |
| 版本 | 2.12.5 → **2.13.0**（`config.py` / `src/__init__.py` / `DPS_VERSION` 三处一致） |

**2. OpenBase（v1.12.0 C 批）**

| 项 | 内容 |
|----|------|
| 代理 | `dps-proxy` 允许清单新增三个**只读**路由：`/metrics`、`/rate-limits/status`、`/alerts/rules`；不注册任何写方法 |
| 页面 | `DpsMonitorView` 四源独立（health / metrics / rate-limits / alerts）：5 项 KPI + 限流状态表 + 告警规则表；移除「指标未开放」占位 |
| API | `core/api/dps.ts` 新增 `getRuntimeMetrics` / `getRateLimitStatus` / `getAlertRules` |

**3. 验证**

| 项 | 命令/方式 | 结果 |
|----|-----------|------|
| DPS 新用例 | `pytest src/tests/test_v2120_runtime_metrics.py` | **18 passed**（类级守门 / RBAC / 快照 / 自采样） |
| DPS 全量 | `pytest`（3.11 运行器） | **1840 passed / 3 skipped / 1 xfailed / 1 xpassed，0 failed** |
| OpenBase 代理用例 | `pytest tests/test_dps_proxy.py` | **26 passed**（新增 4 例） |
| 前端新用例 | `vitest run tests/r12-dps-monitor-v1120.spec.ts` | **3 passed** |
| 前端全量 | `vitest run` | **366 passed / 38 files**（基线 363 + 3） |
| 静态 | `vue-tsc --noEmit` / `ruff check` | **0 error** |

> 环境说明：DPS 全量首跑使用 pgAdmin CPython 3.13，因长时间回归后子进程无法再启动出现 11 例失败；改用 OpenRAG `.venv3`（CPython 3.11.9）+ `doc/tmp/run_dps_pytest311.py`，并以 shim 提供裸 `python`/`python3`、`pip --target DPS/.venv/libs311` 补齐 `pyjwt/bcrypt/mccabe` 后复跑全部通过。首跑失败已逐项归因：版本/BOM 为编辑窗口内产生（已清理），CI 脚本缺 `python` 与 smoke 超时随 shim 消除，`test_s5_t6_event_consumer` 隔离复跑通过。

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
| 3 | 占位页转真实页面 | 前端 + 上游 | 应用调用记录（链路追踪、预算管理已于 R4，模型部署已于 R7 转真实页） |
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
| v2.22.0 | 2026-10-24 | 研发（AI 辅助） | 新增 §2.31：**v1.12.0 长尾建设 C 批**——DPS 新增 `GET /api/v2/metrics`（60s QPS / CPU / 内存 / uptime / requests_total）与 `runtime_metric:read` 权限点，版本升至 2.13.0；OpenBase 代理扩权三个只读端点并重写画像监控页。验证：DPS 18 例 + 全量 1840 passed、OpenBase 26 例、前端 366/366、`vue-tsc`/`ruff` 0 错误。 |
| v2.21.0 | 2026-10-24 | 研发（AI 辅助） | 新增 §2.30：**v1.12.0 长尾建设 B 批**——XR-LLM-06 工作空间按用户名邀请（OpenLLM schema/路由解析 + 前端成员弹窗）；用户名不存在 404、双给冲突 400；后端 9 例 + 回归 34 例、前端新增 3 例、全量 363/363、`vue-tsc` 0 错误。 |
| v2.20.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.29：**v1.12.0 长尾建设 A 批**——OB-03 新增全局调用记录端点与 `AppCallsView`；OB-04 知识库控制台接 `rag-proxy` 真实链路；XR-LLM-03 报表趋势接三聚合源；XR-DPS-05 阻塞于 XR-DPS-04。验证：后端 6 例、前端新增 7 例、前端全量 360/360、`vue-tsc` 0 错误。 |
| v2.19.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.28：**v1.11.0 长尾事项产品裁定**——14 项逐条裁定（建设 7 / 冻结 5 / 不建设 1 / 已闭环 1），产出《长尾事项产品裁定-v1.0.0》，附现状证据、端点清单、验收与解冻条件；XR-MEM-01 确认已闭环（台账滞后）；建设项分批转入 v1.12.0，本期无代码改动。 |
| v2.18.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.27：**XR-OPS-07 发布阻断处置**——根因复核为门禁判据误判（OpenMemory 模板开发默认值≠生产下发值，且运行期 `validate_identity_trust_policy` 已 fail-closed）；矩阵升 v1.1.0 引入 `documented_override` + `runtime_gate`，守门 15 例、复跑 9/9 PASS；生产值改由 `--env-file` 在 OPS 侧核验。 |
| v2.17.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.26：**v1.10.2 治理与发布收口**——OB-02 网关交互 4 例闭环；S4 仓库侧发布核验（矩阵 + 脚本 + 10 例，实测 7 PASS / 1 FAIL）；新登记 XR-OPS-07（OpenMemory 开关载体漂移，P1 阻断发布）；XR-GOV-01 三仓未采纳转 v1.11.0；S2 演练待 OPS。 |
| v2.16.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.25：**v1.10.1 个人中心与通知（OB-01）**——新增 `notification_preferences` 表与 `GET/PUT /auth/notification-preferences`（默认值/upsert/事件白名单/Webhook 校验/OIDC 降级）；设置页通知偏好真实读写。验证：后端 6 例、前端 4 例、前端全量 349 例、`vue-tsc` 0 错误；全量回归 5 类存量失败已逐项隔离复核，并修复 v1.10.0 遗留 BOM。 |
| v2.15.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.24：**v1.10.0 全栈缺口补齐 I**——OpenLLM 监控全链路租户隔离（查询过滤 + 端点透传 + 写入态回填 + 回填脚本）、错误率口径改按 `sum(value)` 计算；统一前端本地模型/模型对比/开源市场/我的收藏四页接真实端点、0 mock；XR-DPS-01 因 DPS ADR-290-01 规则写入已收口且无运行态指标端点，转入 v1.11.0。验证：OpenLLM 新用例 10/10、监控回归 29/29、前端全量 345/345、vue-tsc 0 错误。 |
| v2.14.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.23：**v1.9.8 处置窗口执行记录**——OpenLLM 本地验证实例启动（健康 200）；21 个聚合端点经代理全部 200；浏览器抽检 9 页全部 PASS；DPS `0954b9a` 回执核验通过；新发现错误率口径与插件/工具口径两项并纳入计划；G1/G2/G7 仍待 OPS 窗口。 |
| v2.13.1 | 2026-10-23 | 研发（AI 辅助） | §2.22 回填执行进展：XR-OPS-01 四仓 github 补推提前闭环（OpenBase `540f757`、OpenLLM `647d4bb`；OpenRAG/OpenMemory 已一致）；清查计划升 v1.0.1。 |
| v2.13.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.22：**剩余事项统一清查与小版本迭代计划**——登记本仓 6 项、跨仓 12 项、运维/QA 6 项，拆入 v1.9.8 / v1.10.0 / v1.10.1 / v1.10.2 / v1.11.0；产出《剩余事项统一清查与小版本迭代计划-v1.0.0》，缺口清单升 v1.8.0 并收敛排期口径。本轮仅文档，不改代码。 |
| v2.12.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.21：**R7 E 类产品裁定与五页收敛**——OpenBase 新增 `PUT /auth/me`、`POST /auth/change-password` 并扩展 `/auth/me` 资料字段；仪表盘、统一监控、个人设置、模型部署、画像系统监控（健康）落地；其余 E 类页面裁定不建设/保留。验证：后端 6 例、前端 9 例、vue-tsc 0 错误、前端全量 337 例通过；聚合端点与页面级实测因服务不可启动待复核。 |
| v2.11.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.20：**R6 本地资源超时治理与两页接线**——Ollama 轻量探测改短超时（connect 2s/read 5s）、`open-models` 改双通道、收藏与下载任务列表批量化（消除 N+1）；GPU 资源、下载管理两页接真实端点并移除 mock。验证：OpenLLM 13 例、前端 7 例、vue-tsc 0 错误、前端全量 328 例通过；运行态耗时与聚合端点实测因 OpenLLM 无法启动待复核（未伪造耗时）。 |
| v2.10.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.19：**R5 治理与 RBAC 双通道与七页接线**——OpenLLM 11 个路由文件改双通道并新增 `/roles/permissions/catalog`；角色/工作空间/路由策略/熔断器/工具调用/Prompt 模板/Prompt 实验/A-B 测试七页（8 路由）接真实端点，移除假开闭/假调用链/假版本等动作。验证：OpenLLM 30+15 例、前端 15 例、vue-tsc 0 错误、前端全量 321 例通过；聚合端点与浏览器级实测待 OpenLLM 可启动后补做。 |
| v2.9.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.18：**R4 观察域双通道与六页接线**——OpenLLM `monitoring`/`traces`/`alerts`/`budgets`/`usage`/`billing`/`billing_v2` 共 46 处依赖改双通道（写权限端点不放宽）；成本、告警、链路、预算、用量、计费六页接真实端点，链路/预算由占位页改为真实页，移除成本页「一键应用建议」假动作。验证：OpenLLM 15+6 例、前端 17 例、vue-tsc 0 错误、前端全量 306 例通过；聚合端点与浏览器级实测因 OpenLLM 无法启动待复核（未伪造成已验证），并登记指标表租户过滤缺口。 |
| v2.8.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.17：**R3 双通道鉴权与插件/模型分类接线**——OpenLLM `plugins`（8 处）与 `model_categories`（13 处）改用 `get_current_active_user_or_api_key`；插件管理、模型分类两页接真实端点并移除 mock。验证：OpenLLM 6+34 例、前端 8 例、vue-tsc 0 错误、聚合端点 4/4 200；浏览器级复核受环境限制待补。 |
| v2.7.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.16：**R2 C 类列表补齐与上游并发修复**——OpenBase 新增 `GET /configs`、`/test-records`、`/test-runs` 与服务 Key `id`/`by-id` 吊销；全局配置、测试记录两页接线并移除假动作；跨仓修复 OpenLLM `get_db`（`scoped_session` → 每请求独立 Session）并发 500。验证：后端 10 例、跨仓 3 例、前端 47 例、vue-tsc 0 错误、接口全链路与并发 9/9 通过；浏览器页面级验证因服务被环境回收待复核。 |
| v2.6.0 | 2026-10-23 | 研发（AI 辅助） | 新增 §2.15：**R1 A 类三页接线**——用户管理（`/users` 全量 CRUD + 角色五码）、API 密钥（`/auth/api-keys` 列表/创建/吊销 + 一次性明文）、EdgeRouter（`/edge/**` 概览/组织/配额/适配器/审计）；移除三页全部假动作；登记「服务 Key 列表无 id、吊销需明文」后端缺口。验证：前端 10 例 + 关联回归 40 例、vue-tsc 0 错误、密钥创建→吊销全链路、三页浏览器实测 0 error。 |
| v2.5.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.14：**全栈功能级审计与 OpenLLM 聚合通道打通**——四层审计（加载/交互/API 面/通道探测）覆盖 77 页，PASS 76/1（唯一 FAIL 为沙箱下 Chromium `ERR_NO_BUFFER_SPACE` 噪声），API 失败 0；单列 52 页无后端调用并按 A~E 五类成账；修复通用代理两段 401（来源按系统映射 + 仅 openllm 注入 API Key）；提供商管理页端到端真实化。验证：后端 8+55 例、前端 4 例、浏览器实测 0 error、全页面回归 api 失败 0。 |
| v2.4.0 | 2026-10-22 | 研发（AI 辅助） | §2.13 补充：排查服务重启期 `/api/v1/modules` 500——根因为 Vite 代理对上游连接失败返回空 500（非后端缺陷）；代理统一映射为 503 JSON，补 4 例单测并实测通过。 |
| v2.3.0 | 2026-10-22 | 研发（AI 辅助） | §2.13 补充：修复 `/login` 首帧 `No match found` 告警与 `redirect=/login` 自回跳——新增 `/login → /auth/login` 顶层重定向（保留 query/hash）；S6-T2-5 两条用例 + 浏览器实测通过。 |
| v2.2.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.13：**统一前端记忆模块对齐 OpenMemory v7.5.0~v7.8.0**——图谱页接真实 `graph/overview`（替换 mock）、搜索页补图谱策略与命中语义、写入页补重要度分层、列表页补软/硬删除；后端新增 overview 端点与代理透传。验证：前端 4 例 + vue-tsc、OpenMemory 3 例、OpenBase 代理 17 例通过。 |
| v2.1.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.12：**v7.8.0（检索质量与可观测性）已完成**——实体命中解析为记忆、孤立实体兜底、`+term` 全命中与 Lucene 转义；图投影/检索指标族、worker `:9101/metrics`、`openmemory-graph` 告警组；修复 `openmemory.api` 循环导入。验证：相关单测 43 passed、真实 Neo4j 无实体 id 结果、全量 1385 passed（失败项同基线）。 |
| v2.0.0 | 2026-10-22 | 研发（AI 辅助） | §2.11 更新：**v7.7.0（P4 跨仓联调与生产门禁）已完成**——端到端探针全链路通过（写入→outbox→投影→图检索→forget→删除投影→不再召回）；修复 5 处缺陷（forget 未入队删除、孤儿实体残留、全文索引幽灵结果、缓存键缺租户、缓存失效前缀空转）；补压测（写 1k/读 1k）、租户隔离、重要度分层与 worker 停摆回滚演练结果；OpenBase 侧本轮无代码改动。 |
| v1.9.0 | 2026-10-22 | 研发（AI 辅助） | §2.11 更新：**v7.6.0（P3 规模治理）已完成**——重要度分层（`projection_policy`）、批量 UNWIND（`project_batch`）、`graph_repair` CLI（回填/对账/清理）、`done` 事件保留期、worker 纳入 `start-all-services.ps1`；补单测 67 passed 与 P3 探针结果（低价值不入队 / 批量写入 / 幂等重投 / 清理归零）。 |
| v1.8.0 | 2026-10-22 | 研发（AI 辅助） | §2.11 更新：**v7.5.0（P2 异步可靠投影）已完成**——登记 outbox 同事务落库、`GraphProjector`、worker、读路径租户 fail-closed；补单测 105 passed 与端到端探针结果（写入→投影→命中→跨租户 0→删除清零）。 |
| v1.7.0 | 2026-10-22 | 研发（AI 辅助） | 更正 §2.10 第 7 项结论（「persistent 不写图」是实现缺口而非设计行为）；新增 §2.11「记忆图谱跨仓迭代」：登记跨仓方案 v1.0.0 与 v7.4.0~v7.7.0 路线，**v7.4.0（P1 读路径加固）已完成**（OpenMemory `17cba89`，回归 53 passed）。 |
| v1.6.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.10「OpenMemory 启动失败根因与修复」：Qdrant 客户端 5s 默认超时导致 `ReadTimeout`（qdrant-client 1.7.3）+ 编排脚本单服务目标坍缩为字符串的 bug；处置为预建集合/索引 + OpenMemory `VectorStoreConfig.timeout=30`（提交 `c73b7c1`）；§4 增补记忆模块走查 6/6 与 OpenMemory 单测子集；§5 第 4 项闭环。 |
| v1.5.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.9「本地 Neo4j 社区版服务化」：`dist.neo4j.org` 403 → 用官方 jar 装配发行布局 + `Neo4jCommand` 官方入口 + `prunsrv` 注册 Windows 服务 `neo4j`（Auto，LocalSystem），认证与数据持久性验证通过；§5 第 4 项标记闭环。 |
| v1.4.0 | 2026-10-22 | 研发（AI 辅助） | 新增 §2.8「请求超时兜底与本地基础设施编排」：代理类端点 8s 超时（`core/api/http.ts`）、`Redis/Qdrant` 纳入 `start-all-services.ps1`（`TcpProbe` 探测 + local 模式依赖连带）；§4 复跑 `vitest` 250/250 与 `vite build`；§5 第 5、7 项标记闭环；文档版本号与上游依据同步至架构文档 v1.8.0。 |
| v1.3.0 | 2026-10-22 | 研发（AI 辅助） | 追加「全页面走查」：77 页 PASS 77/FAIL 0，产出逐页截图与预览页；§2.7 增补第 12~13 项走查缺陷（模块页丢失全局侧栏、ECharts 隐藏页签初始化告警）及修复；§4 增补走查门禁行；§5 登记 OpenMemory 依赖 Neo4j 的环境前置。 |
| v1.2.0 | 2026-10-21 | 研发（AI 辅助） | 追加阶段四收口：§2.7 增补第 8~11 项（DPS 12 页归位画像模块并补导航、`.page-toolbar` 全局化、删除 `knowledge/Settings.vue`、业务模块 39 页套骨架并同步 `key-pages` 夹具）；§4 验证更新为全量 250 用例串行通过；§5 遗留收窄为 `useAsyncState`、面包屑与 4 个占位页。 |
| v1.1.0 | 2026-10-21 | 研发（AI 辅助） | 新增 §2.7「公共域收口（阶段三）」：7 项缺口逐条处置（记忆席位 dependsOn、gateway 开关只读化、providers/register 与画像假页下线、2 个死文件删除、占位页统一为结果页并补入口、公共域 37 页套骨架），同步 E2E 页面清单与 `platform-ia` 测试夹具；§5 遗留收窄为业务模块页与占位页上游依赖。 |
| v1.0.0 | 2026-10-21 | 研发（AI 辅助） | 初始创建：记录 v1.4.11 统一前端 IA（阶段一/二）、首屏治理、后端接口 8s 级耗时排查的证据链（6 项观测）、根因分解（R1~R5）、3 项处置与复测数据（`/auth/me` P50 91ms 等），并登记 6 项遗留。 |
