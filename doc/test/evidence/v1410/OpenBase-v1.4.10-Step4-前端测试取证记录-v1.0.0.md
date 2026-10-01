# OpenBase v1.4.10 Step 4 前端测试取证记录

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-EVID-V1410-STEP4-FE-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 日期 | 2026-10-01 |
| 范围 | OpenBase v1.4.10 Step 4 测试（前端轨道）：vitest 单元/组件、覆盖率门禁、生产构建、Playwright 关键页 E2E、T3a 全页面巡检（12 条 `/dps/*` 新增 ＋ 既有路由）、软断言静态计数 |
| 执行环境 | Windows；Node v22.16.0；npm 10.9.4；vitest 2.1.8；vite 6.4.3；@playwright/test 1.63.0（chromium-1228）；Python 3.10.11；uvicorn 0.51.0；fastapi 0.139.2 |
| 被测位 | HEAD `9bf2d18`（feat(v1.4.10-step3) dps-proxy 22 端点扩展 + 前端 12 页面/数据层/路由） |
| 前端工程 | `openbase-ui/`（Vue 3 + Vite + Vitest + Playwright），工作区无未提交改动 |
| 后端代理目标 | `127.0.0.1:8000`（`openbase.demo_app:app`，DB 降级内存；vite `server.proxy['/api']` 目标同源） |
| 前端运行面 | Vite dev server `http://127.0.0.1:5173`（`npx vite --host 127.0.0.1 --port 5173 --strictPort`） |
| 存放 | `doc/test/evidence/v1410/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-01 | AT-OpenBase-Test（Step 4 前端执行） | 初始版本：记录 vitest 单测、覆盖率门禁、生产构建、Playwright E2E（9 关键页）、T3a 全页面巡检（122 页）、软断言计数的原始命令、结果与缺陷/阻塞 |

> 说明：本文件为 **Step 4 取证记录**（原始输出索引 ＋ 结论），非正式《测试报告》；正式测试报告待收尾时按项目文档管理规范另行产出并做版本管理。后端轨道取证另见 `OpenBase-v1.4.10-Step4-后端与集成测试取证记录-v1.0.0.md`。

---

## 1. 执行命令（逐字）

| # | 命令 | 工作目录 |
|:-:|------|----------|
| 1 | `npm run test`（`vitest run`） | `openbase-ui/` |
| 2 | `npx vitest run tests/dps-ui-v1410.spec.ts`（失败用例隔离复跑） | `openbase-ui/` |
| 3 | `npm run test:coverage`（`vitest run --coverage`） | `openbase-ui/` |
| 4 | `npm run build`（`vue-tsc --noEmit && vite build`） | `openbase-ui/` |
| 5 | `npm run test:e2e`（`playwright test`；先启动 vite dev server） | `openbase-ui/` |
| 6 | `node doc/test/evidence/v1410/step4-t3a-page-scan-20261001.mjs`（T3a 巡检） | `openbase-ui/`（脚本绝对路径；浏览器依赖从 `openbase-ui/node_modules` 解析） |
| 7 | 软断言 grep：`if.*is_visible.*else.*assert` / `expect\.soft`（`openbase-ui/tests`）；`except…: pass` / `else: pass` / `assert True`（`tests/`） | 仓库根 / `openbase-ui/` |

### 1.1 运行面准备（真实联调链路）

```
# 后端（vite /api 代理目标；本机 DB 连接被重置 → demo_app 降级内存）
python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000    # GET /health -> 200

# 前端 dev server（E2E 与 T3a 的页面承载面）
npx vite --host 127.0.0.1 --port 5173 --strictPort                     # http://127.0.0.1:5173 -> 200

# 登录态（令牌仅经环境变量注入，未落盘、未打印）
POST http://127.0.0.1:8000/api/v1/auth/login  {"username":"admin","password":"admin123"} -> 200（扁平 TokenResponse）
$env:OPENBASE_ACCESS_TOKEN / $env:OPENBASE_REFRESH_TOKEN / $env:OPENBASE_BASE_URL=http://127.0.0.1:5173
```

> 进程卫生要求（见 §6 ENV-FE-1410-03）：执行前须确认 8000/5173 端口**仅一个**监听者；残留进程会导致登录间歇 401。

---

## 2. 结果汇总

| # | 命令 | 总数 | 通过 | 失败 | 跳过 | 结论 |
|:-:|------|:----:|:----:|:----:|:----:|------|
| 1 | `npm run test` | 21 文件 / 239 用例 | 20 文件 / **238** 用例 | **1** 用例 | 0 | 1 项失败（见 §6 FL-FE-1410-01，环境级超时，隔离复跑与覆盖率全量复跑均通过） |
| 2 | `npx vitest run tests/dps-ui-v1410.spec.ts` | 14 用例 | **14** | 0 | 0 | 隔离复跑全通过（P-01 用例 1170ms，远低于 5000ms 上限） |
| 3 | `npm run test:coverage` | 21 文件 / 239 用例 | **21 文件 / 239 用例** | 0 | 0 | 覆盖率门禁**达标**（见 §3），exit 0 |
| 4 | `npm run build` | — | — | — | — | `✓ built in 1m 26s`，exit 0（含 1 条非阻断告警） |
| 5 | `npm run test:e2e` | 9 | **9** | 0 | 0（flaky 0 / unexpected 0） | 9 关键页 PASS，`9 passed (1.3m)`，exit 0 |
| 6 | T3a 全页面巡检 | 122 页 | — | — | — | 代码类 5xx = **0**、requestfailed = **0**、pageerror = **0**；15 条 5xx 全部登记为环境类（H） |
| 7 | 软断言 grep | — | — | — | — | 前端软断言 **0**（后端等价模式 3 命中，逐条裁定非软断言） |

---

## 3. 覆盖率门禁核对（`npm run test:coverage`）

阈值（`openbase-ui/vite.config.ts` `test.coverage.thresholds`）：**lines 80 / functions 80 / statements 80 / branches 70**（全局口径）。

```
-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines |
-------------------|---------|----------|---------|---------|-------------------
All files          |   97.84 |    90.93 |    89.4 |   97.84 |
 api               |   98.94 |    92.02 |   99.07 |   98.94 |
  auth.ts          |     100 |      100 |     100 |     100 |
  dps.ts           |     100 |      100 |     100 |     100 |
  error.ts         |   97.77 |    85.07 |     100 |   97.77 |
  gateway.ts       |   90.62 |      100 |   85.71 |   90.62 |
  http.ts          |     100 |    89.39 |     100 |     100 |
  llm.ts           |   96.73 |       88 |     100 |   96.73 |
  logs.ts          |     100 |    95.23 |     100 |     100 |
  modules.ts       |     100 |      100 |     100 |     100 |
  rag.ts           |     100 |      100 |     100 |     100 |
  redirect.ts      |     100 |     90.9 |     100 |     100 |
  testing.ts       |     100 |      100 |     100 |     100 |
 router            |   94.28 |    85.48 |      50 |   94.28 |
  index.ts         |   92.48 |       85 |   48.14 |   92.48 |
  legacyRedirects.ts|    100 |      100 |     100 |     100 |
 stores            |   95.65 |    91.17 |   93.33 |   95.65 |
  auth.ts          |   90.69 |    88.23 |   85.71 |   90.69 |
  moduleRegistry.ts|     100 |     92.3 |     100 |     100 |
  ui.ts            |     100 |      100 |     100 |     100 |
-------------------|---------|----------|---------|---------|-------------------
```

`clover.xml` 全量口径（交叉校验）：statements 1001/1023 = **97.85%**、conditionals 361/397 = **90.93%**、methods 135/151 = **89.40%**。

| 指标 | 实测 | 阈值 | 判定 |
|------|:----:|:----:|:----:|
| Statements | 97.84% | 80% | ✅ |
| Branches | 90.93% | 70% | ✅ |
| Functions | 89.40% | 80% | ✅ |
| Lines | 97.84% | 80% | ✅ |

> `src/core/router/index.ts` 函数覆盖 48.14%（低于 80），但以**全局聚合**（All files 89.4%）过阈值；`router` 组内 `bare 分支`（模块装载守卫的异常路径）为主要未覆盖来源。整体达标。

---

## 4. Playwright 关键页 E2E（`npm run test:e2e`）

- 清单同源：`openbase-ui/tests/e2e/fixtures/key-pages.json`（Q-FE-4b 9 关键页）；执行面 `tests/e2e/{chat,knowledge,memory,portrait}.spec.ts`。
- 判据：页面渲染（非白屏）＋ 关键元素/受控空态可见 ＋ 渲染兜底未触发 ＋ **无 console.error / pageerror / console.warn**。

```
Running 9 tests using 1 worker
  ok 1  /openllm/conversations   (3.4s)
  ok 2  /knowledge/chat          (2.6s)
  ok 3  /knowledge/list          (1.9s)
  ok 4  /knowledge/kb-1          (2.0s)
  ok 5  /memory/list             (3.5s)
  ok 6  /memory/sessions         (3.1s)
  ok 7  /portrait/list           (10.8s)
  ok 8  /portrait/overview       (18.1s)
  ok 9  /portrait/dps-tenant-001_admin1_001  (13.9s)
  9 passed (1.3m)
```

Playwright JSON（`step4-playwright-e2e-results-20261001.json`）：`expected=9 / skipped=0 / unexpected=0 / flaky=0 / duration=76670ms`。

---

## 5. T3a 全页面巡检（`/dps/*` 新增 ＋ 既有路由）

- 脚本：`step4-t3a-page-scan-20261001.mjs`；原始数据：`step4-t3a-page-scan-20261001.json`；汇总：`step4-t3a-page-scan-20261001.txt`。
- 采集：① HTTP ≥ 500（逐条 URL/状态码）② `requestfailed` ③ `console.error` ④ `pageerror`；观测窗口 = `domcontentloaded` ＋ `networkidle`（上限 6s）＋ 800ms 稳定期（避免长/挂起请求漏采）。
- 覆盖：**122 页** = `/dps/*` 新增 **13 条 route record**（设计 §2 的 12 行，P-09 由 `new` 与 `:code/edit` 两条路径承载）＋ static 4 ＋ platform 26 ＋ 业务模块 49 ＋ legacy 重定向 32。

### 5.1 网络层门禁

| 指标 | 计数 | 说明 |
|------|:----:|------|
| HTTP ≥ 500 —— 代码类（B） | **0** | 无 OpenBase 代码缺陷派生 5xx |
| HTTP ≥ 500 —— 环境类（H） | 15 | 上游不可达 502（11）＋ DB 不可用 500（4） |
| `requestfailed` | **0** | 无网络失败/导航失败 |
| `console.error` | 36 | 均为 4xx/5xx 的浏览器网络镜像（含 DPS 上游 401），无 pageerror |
| `pageerror` | **0** | 无未捕获渲染异常 |
| 页面文档状态 | 122/122 → 200 | 全部页面成功加载（含 13 条 `/dps/*`） |

### 5.2 环境类 5xx（H，均源自已登记环境根因，不进缺陷闭环）

| 类 | 端点 | 涉及页面 | 状态 |
|----|------|----------|:----:|
| 上游未启动（OpenLLM） | `/api/v1/llm-proxy/models`、`/api/v1/llm-proxy/conversations` | `/openllm/models`、`/openllm/playground`、`/openllm/conversations` | 502 |
| 上游未启动（OpenRAG） | `/api/v1/rag-proxy/collections` | `/knowledge/list`、`/knowledge/chat`、`/knowledge/admin` | 502 |
| 上游未启动（OpenMemory） | `/api/v1/memory-proxy/{memories,sessions,decay/config,memories/1}` | `/memory/list`、`/memory/sessions`、`/memory/decay`、`/memory/1` | 502 |
| DB 不可用（持久层查询） | `/api/v1/tenants`、`/api/v1/users` | `/platform/identity/tenants`、`/platform/identity/org`、`/system/tenants`、`/system/org` | 500 |

### 5.3 `/dps/*` 新增页结论

- 13 条 `/dps/*` 页面文档状态均 **200**，无 pageerror、无 requestfailed、无 5xx。
- 4 条页面（`/dps/scoring-types`、`/dps/annotation-templates`、`/dps/annotation-templates/cc-annot/fields`、`/dps/tags`）出现 `console.error`（共 5 条），内容均为 `Failed to load resource: the server responded with a status of 401 (Unauthorized)` —— DPS 上游未接入/未鉴权时的浏览器网络镜像（环境类），**前端已按受控态呈现（非白屏、非异常堆栈）**。

### 5.4 判定

**PASS（排除已登记环境类）**：代码类 5xx = 0、requestfailed = 0、pageerror = 0；122 页全部可达。

---

## 6. 缺陷 / 环境限制登记

| 编号 | 级别 | 类型 | 描述 | 证据 |
|------|:----:|------|------|------|
| FL-FE-1410-01 | P3（测试可靠性） | 稳定性/超时 | `npm run test` 中 `tests/dps-ui-v1410.spec.ts › P-01 模板族列表：真实 API 渲染 + 空态` 报 `Test timed out in 5000ms`（实测 8233ms）。**非确定性**：隔离复跑 PASS（1170ms）；`npm run test:coverage` 全量复跑 239/239 全通过。归因：全 21 文件并行时，Element Plus 表格 + 抽屉的首次挂载超出默认 5000ms（本机 collect 537s / environment 1134s，整体偏慢）。**建议**：对该重挂载用例设 `testTimeout`（如 15000）或提高全局 `testTimeout`；无需改产品代码。 | `step4-vitest-run-20261001.txt`；`step4-vitest-dps-isolated-20261001.txt`；`step4-vitest-coverage-20261001.txt` |
| ENV-FE-1410-01 | P1（环境限制） | 环境 | 本机 PostgreSQL `localhost:5432` 连接被重置（`database init failed ... connection was closed in the middle of operation`）→ `demo_app` 降级内存；依赖持久层的 `/api/v1/tenants`、`/api/v1/users` 返回 500，RBAC 走内存回退。与 v1.4.6 `ENV-FE-01` 同源。 | `step4-backend-uvicorn-8000-20261001.log`；T3a §5.2 |
| ENV-FE-1410-02 | P2（环境限制） | 环境 | 上游四服务（OpenLLM/OpenRAG/OpenMemory/DPS）未启动 → `/api/v1/{llm,rag,memory}-proxy/*` 502；DPS 上游 401。与 v1.4.6 `ENV-FE-03` 同源。 | T3a §5.2/§5.3 |
| ENV-FE-1410-03 | P2（环境/可复现） | 进程卫生 | 首次 E2E 运行前，端口 8000 存在**残留 Python 进程**与当次后端并存（监听者 PID ≠ uvicorn 自报 PID），导致 `POST /api/v1/auth/login` 间歇返回 `AUTH_401 invalid username or password`（`OPENBASE_ACCESS_TOKEN` 空 → 9 页全部未渲染）。**处置**：终止 8000 端口全部监听者并重启**单一**后端后，登录与 E2E 恢复正常。登记以提示后续执行前做端口独占检查。 | `step4-playwright-e2e-20261001.txt`（首轮失败/二轮通过）；`step4-backend-uvicorn-8000-20261001.log` |
| OBS-FE-1410-01 | P3（可观测） | 观察 | Playwright 触发沙箱受限文件告警（`nvAppTimestamps`、`chromium_headless_shell ... debug.log`），不影响用例执行（浏览器正常启动、用例正常判定）。 | 命令 stderr |

> 无 **代码级 P0/P1 缺陷**；`/dps/*` 新增页面未见代码类缺陷。

---

## 7. 证据索引（均位于 `doc/test/evidence/v1410/`）

| 命令/产物 | 证据文件 |
|-----------|----------|
| `npm run test` 原始输出 | `step4-vitest-run-20261001.txt` |
| 失败用例隔离复跑 | `step4-vitest-dps-isolated-20261001.txt` |
| `npm run test:coverage` 原始输出 | `step4-vitest-coverage-20261001.txt` |
| 覆盖率明细（clover / final） | `step4-vitest-coverage-clover-20261001.xml`、`step4-vitest-coverage-final-20261001.json` |
| `npm run build` 原始输出 | `step4-vite-build-20261001.txt` |
| `npm run test:e2e` 原始输出 | `step4-playwright-e2e-20261001.txt` |
| Playwright JSON 结果 | `step4-playwright-e2e-results-20261001.json` |
| T3a 脚本 / 原始 JSON / 汇总 TXT / 控制台日志 | `step4-t3a-page-scan-20261001.mjs`、`step4-t3a-page-scan-20261001.json`、`step4-t3a-page-scan-20261001.txt`、`step4-t3a-page-scan-20261001.console.txt` |
| 软断言静态计数 | `step4-soft-assert-scan-20261001.txt` |
| 运行面日志 | `step4-backend-uvicorn-8000-20261001.log`、`step4-vite-dev-5173-20261001.log` |

---

## 8. 结论

- **构建**：`vue-tsc --noEmit` ＋ `vite build` 通过（exit 0）。
- **单测/组件**：239 用例，稳定口径（覆盖率全量运行）**239/239 通过**；唯一 1 次失败为环境级超时（隔离与全量复跑均通过，非代码缺陷）。
- **覆盖率**：全局 97.84% / 90.93% / 89.40% / 97.84%，**全部达标**。
- **E2E**：9 关键页 **9/9 通过**，无 console error/warn/pageerror。
- **T3a**：122 页（含 13 条 `/dps/*` 新增）全部可达；代码类 5xx = 0、requestfailed = 0、pageerror = 0（PASS，排除已登记环境类）。
- **软断言**：前端 **0**。
- **阻塞**：无硬阻塞；4 项环境/观察类登记（DB 不可用、上游未启动、端口残留进程、沙箱告警）。
