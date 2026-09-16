# OpenBase v1.4.6 · T3a 全页面巡检报告（Step 4 测试 · 前端轨道）

| 项目 | 内容 |
|------|------|
| 文档编号 | OB-TEST-EVIDENCE-T3A-PAGE-SCAN-v1.4.6 |
| 版本号 | v1.4.6 |
| 状态 | [Draft]（证据文件） |
| 执行角色 | AT-OpenBase-Test（测试工程师） |
| 执行日期 | 2026-09-15 |
| 静态服务 | `npm run build` + `npx vite preview --port 4173`（`/api` → `127.0.0.1:8000`） |
| 原始数据 | `doc/test/evidence/v146/t3a-page-scan.json` |
| 逐页截图 | `doc/test/evidence/v146/screenshots/`（110 张） |
| 复测数据 | `doc/test/evidence/v146/t3a-flagged-recheck.json` |

## 1. 扫描范围与来源（程序化提取，非人工转写）

| 项 | 数值 | 说明 |
|----|------|------|
| 路由清单来源 | 源码三处 + 重定向单一事实源 | `src/core/router/index.ts` + `src/pages/platform/routes.ts` + `src/pages/personal/routes.ts` + `src/modules/*/index.ts` + `src/core/router/legacyRedirects.ts`（提取逻辑与 `scripts/gen_ownership_matrix.mjs` 同源，临时脚本 `work/extract-routes.mjs`，**未改动仓库任何文件**） |
| 声明路由（非参数化） | 76 | |
| 旧路径承接条目 | 32 | `LEGACY_REDIRECTS` |
| 矩阵行数 | 106 | 与 `doc/design/OpenBase-路径归属矩阵-v1.4.6.md` 逐行比对 |
| 与矩阵差异 | **0**（两个方向均为 0） | `only_in_code_source=[]`、`only_in_matrix_doc=[]` |
| 参数化路由（矩阵外，纳入巡检） | 4 | `/openllm/apps/:id`、`/knowledge/:id`、`/memory/:id`、`/portrait/:id`（样本 ID 取自 `tests/e2e/fixtures/key-pages.json`） |
| **实际巡检页数** | **110** | 106 + 4 |

## 2. 采集方法与判据

每页采集 8 类信号：① HTTP 4xx（含响应体前 200 字符）② HTTP ≥500（含响应体前 200 字符）③ `requestfailed` ④ `console.error` ⑤ `pageerror` ⑥ 接口 200 但主区域空 ⑦ 关键按钮静默失败（安全按钮探测）⑧ 表单/非 GET 提交响应。

- 登录态：`POST /api/v1/auth/login`（仓库演示账号，经 preview 同域代理）→ `context.addInitScript` 注入 `localStorage.ob_access_token`，**令牌仅内存使用、未落盘未打印**。
- 主内容区解析：`.ob-main`（平台/个人页）→ `.module-content`（业务模块页，顶层 ModuleLayout）→ `#app`（全局静态页）。
- 挂载判据（关键修正）：先 `waitForFunction(#app 有子节点, 25s)`，再 best-effort `networkidle(4s)` + 700ms 稳定期。**仅依赖 networkidle 会在长请求页面产生「尚未挂载即测量」的假空页**（首轮/次轮巡检已识别并修正；修正后 110/110 页均完成挂载，`app-not-mounted` 与 `api-200-empty-main` 均为 0）。
- 预热：扫描前完整加载一次应用外壳（21.5s），使大 chunk 进入浏览器缓存。
- 按钮探测：每页至多 1 个白名单安全按钮（刷新/查询/检索/搜索/导出/新建/展开/更多），观测「已发起 API 请求数 / DOM 变更数 / 新增报错」；请求增量按**已发起请求**统计（首轮实现按「已完成响应」统计，会把「请求挂起」误判为「无请求」，已修正并复测）。
- L4 网络层断言：同源范围内 A/B/C/D/E 全部为 0（H 环境类、I 噪声类排除）。

## 3. 逐页问题表（分类统计 A~I）

| 类 | 含义 | 计数 | 明细去向 |
|:--:|------|:----:|----------|
| A | HTTP 4xx（同源接口/资源） | **3** | 全部为 `/api/v1/services` → 403 `AUTH_403 missing permission: gateway:view`（`/platform/observability/service-discovery` 1 条、`/memory/api-gateway` 2 条）；根因与 H 类同源（DB 不可用→RBAC 不可查），见 §6 复测裁定 |
| B | HTTP ≥500（非环境根因） | **0** | — |
| C | `requestfailed` / 导航失败 / 接口长时间无响应 | **2** | `/api/v1/modules`、`/api/v1/services` 在测量时仍挂起（`api-request-hung`） |
| D | `console.error`（非网络镜像） | **0** | — |
| E | `pageerror` / 渲染兜底触发 | **0** | `render_fallback_pages=[]`（未触发 `layout-render-fallback`） |
| F | 接口 200 但主区域空 | **0** | （修正测量口径后为 0） |
| G | 关键按钮静默失败（候选） | **4** | 经复测 + 源码复核全部裁定为非缺陷，见 §6 |
| H | 环境类（L4 排除） | **41** | 见 §4 |
| I | 噪声/弃用（L4 排除） | **0** | `console.warn` 总数 = 0（Q-FE-4b 判据满足）；无 favicon 404 记录 |

### 3.1 状态码分布（含环境类）

| 状态码 | 出现页数 | 说明 |
|:------:|:--------:|------|
| 401 | 1 | `/api/v1/dps-proxy/portraits/{person_id}`（画像详情页） |
| 403 | 3 | `/api/v1/logs/search`（日志中心）、`/api/v1/services`（服务发现与编排、记忆 API 网关） |
| 502 | 4 | `*-proxy` 上游不可达（OpenLLM/OpenRAG/OpenMemory） |

## 4. H 类（环境类）清单与归因

| 子类 | 计数 | 归因 |
|------|:----:|------|
| `upstream-request-hung` | 18 | 上游四服务未启动，`*-proxy` 请求长时间无响应 |
| `console-network-mirror` | 10 | 浏览器对 4xx/5xx 的自动 console.error（与上表同源，不重复计缺陷） |
| `db-request-hung` | 6 | `/api/v1/tenants`、`/api/v1/users`、`/api/v1/logs/search`（DB 依赖路径挂起） |
| `upstream-unavailable-5xx` | 4 | `SYS_502 ... upstream unreachable: All connection attempts failed` |
| `db-unavailable-4xx` | 2 | 403 `missing permission: log:read`（RBAC 查库失败 → 回退内存 `PermissionStore`（空）） |
| `upstream-unavailable-4xx` | 1 | 401（DPS 上游自有错误信封，见 §6 需复核项） |

共同根因与实测证据见 `doc/test/evidence/v146/env-frontend.md` §3/§4（本机 `localhost:5432/openbase` 连接被立即重置；同一凭据直连共享库 `192.168.0.151:5432/nuct` 正常）。

## 5. 其他可核对结论

| 项 | 结果 |
|----|------|
| 旧路径重定向落点 | **32/32 全部落到预期新路径**（`redirect_mismatch=[]`，AC-146-14-1 前端侧可达性成立） |
| 平台四域目标页 | 26 页全部停留在自身路径（无意外重定向） |
| 渲染兜底（防白屏） | 0 次触发 |
| `console.warn` 总数 | 0（跨 110 页） |
| 前端直连端口 | 0 次（无 `:8001/:8002/:8020` 直连） |
| 非 GET API 请求 | 0 次（巡检未触发写操作，符合设计：写路径由 T3b 专项覆盖） |
| 页面挂载耗时 | min 287ms / max 约 25s（DB 挂起页）/ 均值约 8s（受环境 DB 降级拖累，非前端缺陷） |

## 6. 标记页复测与裁定（`t3a-flagged-recheck.json`）

复测修正项：按钮探测请求增量改为「已发起 API 请求数」，并记录 DOM 前后快照。复测结论：

| 页面 | 原信号 | 复测事实 | 裁定 |
|------|--------|----------|------|
| `/platform/config/modules` | G 刷新无请求 | 点击后 `requests_started_delta=1`（`GET /api/v1/modules` 挂起） | **非缺陷**（首轮计数口径缺陷导致的误报，已修正） |
| `/openllm/models/market` | G 查询无反馈 | 无请求 + DOM 前后完全一致（`text_len=386/386`、`rows=2/2`） | **非缺陷**：`ModelMarketView.applyFilter()` 为本地过滤（`mockModels.filter`），空筛选条件天然无差异 |
| `/openllm/tool-calls` | G 查询无反馈 | 同上（`text_len=202/202`、`rows=4/4`） | **非缺陷**：`ToolCallMonitorView.applyFilter()` 仅重置 `currentPage=1` |
| `/openllm/recommend` | G 检索无反馈 | 同上（`text_len=136/136`、`rows=4/4`） | **非缺陷**：`P2RecommendView.searchDoc()` 空关键字回落默认 4 条（与当前渲染一致） |
| `/platform/observability/service-discovery`、`/memory/api-gateway`、`/gateway/services` | A/C `/api/v1/services` | 403 `AUTH_403 missing permission: gateway:view`（gateway 模块端点） | **环境根因（归 H）**：`require_permission('gateway:view')` 走 DB 权限矩阵；`core/db/init.py:114` 已种子 `role='admin' → permission='*'`，DB 正常时 admin 必然通过 → 403 由 DB 不可用导致 |

### 6.1 L4 判定（双口径，均如实登记）

| 口径 | 结果 | 未通过页 |
|------|------|----------|
| L4（原始，不排除任何项） | **FAIL** | `/platform/config/modules`、`/platform/observability/service-discovery`、`/gateway/services`、`/memory/api-gateway` |
| L4（排除已证实环境派生项） | **PASS** | —（4 页全部由 DB 不可用/上游未启动派生） |

> 说明：`env_derived` 标记仅用于「由已登记 H 类根因直接导致的渲染类派生信号」；本轮 `env_derived_issue_count=0`，上表两项差异来自 §6 的人工复测裁定，未做任何静默删除。

## 7. 缺陷 / 环境限制清单（前端轨道 T3a）

| 编号 | 级别 | 类型 | 描述 | 证据 |
|------|:----:|------|------|------|
| DEF-FE-146-001 | **P1**（代码缺陷） | 功能 | 模块开关「修改详情」抽屉字段全空（`modulesWriteApi.switch()` 未解包 ApiSuccess 信封） | `t3b-deep-cases.json` E2E-MOD-03 |
| ENV-FE-01 | P1（环境限制） | 环境 | 本机 DB `localhost:5432/openbase` 连接被重置 → `/api/v1/tenants`、`/api/v1/users`、`/api/v1/logs/*` 500/403/挂起 | `env-frontend.md` §4 |
| ENV-FE-02 | P2（环境限制） | 环境 | 上游四服务未启动 → `*-proxy` 502/挂起 | 本报告 §4 |
| ENV-FE-03 | P2（需复核） | 待定 | `/api/v1/dps-proxy/portraits/{id}` 返回 401，响应体为上游自有信封（`{"code":"AUTH_401","message":"missing bearer token","data":null,"timestamp":...}`）→ 说明存在应答的上游；需在明确 DPS 运行态的联调环境复核「dps-proxy 是否应注入上游凭据」 | `t3a-page-scan.json` → `/portrait/:id` |
| OBS-FE-01 | P3（可测性） | 观察 | `data-test="logs-time"` 落在 `el-date-picker` 内部隐藏节点（宽高 0），可见控件为 `.el-date-editor--datetimerange` → 建议将 `data-test` 落到可见 wrapper，便于稳定断言 | `t3b-deep-cases.json` E2E-LOGS-03 |

## 8. 未执行项与原因

| 项 | 原因 | 补救计划 |
|----|------|----------|
| 数据写入类信号（表单提交响应） | 全站无 `非 GET API 请求`（扫描未点击提交按钮，避免污染环境数据） | 由 T3b 对模块开关写路径做真实 PATCH 断言（已完成：E2E-MOD-02/03） |
| 有数据成功态巡检（非受控桩） | 上游未启动 + DB 不可用，任一业务数据源均无数据 | 环境修复后重跑 T3a（脚本可复跑，仅需 `node scan-pages.mjs`） |
| 截图人工目视核对 | 本次执行环境不支持图像内容解析 | 截图已按「序号-路由」命名落盘（110 张），供人工/审计目视复核 |

## 9. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
|------|------|--------|------|
| v1.4.6 | 2026-09-15 | AT-OpenBase-Test | 首版：110 页巡检（106 矩阵 + 4 参数化）、A~I 分类统计、复测裁定、缺陷与环境限制登记 |
