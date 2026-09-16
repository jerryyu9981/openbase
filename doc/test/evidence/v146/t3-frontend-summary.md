# OpenBase v1.4.6 · Step 4 测试 · 前端轨道结构化摘要（T3a + T3b + 单测/覆盖率 + 构建）

| 项目 | 内容 |
|------|------|
| 文档编号 | OB-TEST-EVIDENCE-T3-FRONTEND-SUMMARY-v1.4.6 |
| 版本号 | v1.4.6 |
| 状态 | [Draft]（证据文件，待人工批准） |
| 执行角色 | AT-OpenBase-Test（测试工程师） |
| 执行日期 | 2026-09-15 |
| 仓库根 | `d:/Trae CN/myproject/Dev/OpenBase`（前端 `openbase-ui/`） |
| 写入门禁 | 仅新增 `doc/test/evidence/v146/**`；`git status --porcelain` 实测输出 **仅 1 条**：`?? doc/test/evidence/v146/` → **未改动任何仓库源码/测试文件** |

## 1. 环境就绪（真实命令 + 真实结果）

| 命令 | 结果 |
|------|------|
| `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8011` | PID 2756；`GET /health` → **200** `{"status":"ok"}` |
| 同命令 `--port 8000` | PID 2460；`GET /health` → **200**（用于复用 `vite.config.ts` 既有 `preview.proxy['/api'] → 127.0.0.1:8000`，**未改配置**） |
| `npm run build`（`vue-tsc --noEmit && vite build`） | 退出码 **0**，`✓ built in 30.99s` |
| `npx vite preview --port 4173 --host 127.0.0.1` | PID 18584 / 监听 2060；`GET /` → **200**（475 B） |
| 端口实测 | 监听：4173、5432（`postgres` PID 5024）、8000、8011；未监听：6379（Redis）、8001/8002/8020（上游四服务） |

启动日志摘要（后端持续出现，每 1s 一条）：
`WARNING openbase.identity.dispatcher "outbox dispatcher loop iteration failed" error="connection was closed in the middle of operation"`

环境阻塞根因（可复核）：`settings.db_url → localhost:5432/openbase`，raw asyncpg 直连 **2/2 次** 报 `ConnectionDoesNotExistError`；同脚本直连共享库 `192.168.0.151:5432/nuct` **2/2 次成功**（PostgreSQL 14.23）。→ 详见 `env-frontend.md`。

## 2. 六项执行结果总表

| # | 项 | 命令 | 关键数字 | 产出 |
|:-:|----|------|----------|------|
| 1 | 环境就绪 | 见 §1 | 后端 200 / 前端 200 / DB 异常 | `doc/test/evidence/v146/env-frontend.md` |
| 2 | T3a 全页面巡检 | `node scan-pages.mjs`（临时脚本，Playwright） | **110 页**（106 矩阵行 + 4 参数化）；L4 原始 **FAIL 4 页**（裁定后 PASS）；`console.warn=0`；渲染兜底 0 | `t3a-page-scan.json`、`t3a-page-scan.md`、`t3a-flagged-recheck.json`、`screenshots/`（110 张） |
| 3 | T3b 深度用例 | `node t3b-deep-cases.mjs`（Playwright，L1 硬断言） | **19 条：18 PASS / 1 FAIL**；每条末尾执行 `assert_network_clean()`（未登记违规 0） | `t3b-deep-cases.json`、`t3b-deep-cases.md`、`screenshots/t3b-*.png` |
| 4 | 软断言清零检查 | `rg "if.*(is_visible|isVisible).*else.*assert" openbase-ui/tests` 等等价检索（Grep 工具） | **命中 0**（另一条 `catch` 检索仅 1 处，为 `isVisible().catch(()=>false)` 布尔探测，末态 `.toBe(true)` 硬断言） | 见 §4 |
| 5 | 前端单测 | `npx vitest run --reporter=dot` | **157/157 通过**，14 文件，253.07s，退出码 0 | 见 §5 |
| 5b | 覆盖率 | `npx vitest run --coverage` | 默认 5s 超时：**7 failed / 150 passed**（全部 `Test timed out in 5000ms`），退出码 1；`--testTimeout=30000`：**157/157 通过**，但**阈值不达标**：lines/statements **77.76% < 80%**（branches 88.47%、functions 90.47%） | `openbase-ui/coverage/`（v8，含 `coverage-final.json`） |
| 6 | 构建验证 | `npm run build` | 退出码 **0**，30.99s；`dist` **157 文件 / 3,061,075 B ≈ 2.92 MB**（最大：`echarts-*.js` 1012 KB、`element-plus-*.js` 1010 KB） | 见 §6 |

## 3. T3a 逐页问题表分类统计（A~I）

| 类 | 计数 | 内容 |
|:--:|:----:|------|
| A | **3** | `/api/v1/services` → 403 `AUTH_403 missing permission: gateway:view`（服务发现与编排 1 + 记忆 API 网关 2）；裁定为环境根因（DB 不可用→RBAC 不可查；`core/db/init.py:114` 已种子 `admin → '*'`） |
| B | **0** | — |
| C | **2** | `/api/v1/modules`、`/api/v1/services` 测量时仍挂起（`api-request-hung`） |
| D | **0** | — |
| E | **0** | 渲染兜底 0 次触发 |
| F | **0** | 空主区 0（修正测量口径后） |
| G | **4** | 按钮无可观测反馈候选：`/platform/config/modules`（复测证实为「请求挂起」误报）、`/openllm/models/market`、`/openllm/tool-calls`、`/openllm/recommend`（经源码复核为本地过滤型按钮，空条件无差异）→ 全部裁定**非缺陷** |
| H | **41** | 上游未启动 18（挂起）+ 4（502）+ 1（DPS 401）；DB 异常 6（挂起）+ 2（403）；console 网络镜像 10 |
| I | **0** | `console.warn` 全站 0、无 favicon 噪声 |

状态码分布：401 × 1、403 × 3、502 × 4（均见上归类）。
其他核对：**旧路径重定向落点 32/32 全部正确**；平台四域 26 页均停留自身；无前端直连端口；无非 GET 写请求。

## 4. 软断言清零检查

| 检索式（等价 `rg`） | 命中 |
|---------------------|:----:|
| `if.*(is_visible|isVisible).*else.*assert`（`openbase-ui/tests`） | **0** |
| 多行：`(is_visible|isVisible)\(\)[\s\S]{0,120}else\s*\{?[\s\S]{0,80}assert` | **0** |
| `expect\.soft|if\s*\(await.*isVisible` | **0** |
| `catch\s*\(|catch\s*\{` | 1（`tests/e2e/support/key-page.ts:72` 的 `isVisible().catch(() => false)`：poll 谓词内布尔探测，非断言吞异常；最终 `.toBe(true)` 为硬断言） |

结论：**软断言 = 0**（达标）。

## 5. 单测与覆盖率明细

### 5.1 正常单测（`npx vitest run --reporter=dot`）

```
 Test Files  14 passed (14)
      Tests  157 passed (157)
   Duration  253.07s
EXIT=0
```

### 5.2 覆盖率（`npx vitest run --coverage`）

- **默认 5s 超时下失败**：`3 failed | 11 passed (14)`、`7 failed | 150 passed (157)`，时长 1187.65s，失败原因统一为 `Error: Test timed out in 5000ms`（失败用例：`isolation-presentation.spec.ts` 5 条、`portrait-list-error.spec.ts` 1 条、`router-nav.spec.ts` 1 条）→ 覆盖率插桩使耗时增大约 4.7 倍（1187s vs 253s），触发默认 5s 用例超时；属**环境性能 + 测试超时配置**问题。
- **`--coverage --testTimeout=30000`（重跑）**：`Test Files 14 passed (14)`、`Tests 157 passed (157)`，时长 729.38s，但覆盖率阈值拦截 → 退出码 1：

```
-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
-------------------|---------|----------|---------|---------|-------------------
All files          |   77.76 |    88.47 |   90.47 |   77.76 |
 api               |      72 |    88.88 |   89.33 |      72 |
  auth.ts          |     100 |      100 |     100 |     100 |
  dps.ts           |     100 |      100 |     100 |     100 |
  error.ts         |   97.14 |    82.14 |     100 |   97.14 |
  gateway.ts       |   90.62 |      100 |   85.71 |   90.62 |
  http.ts          |     100 |    89.39 |     100 |     100 |
  llm.ts           |   96.73 |       88 |     100 |   96.73 |
  logs.ts          |   26.92 |      100 |       0 |   26.92 |
  modules.ts       |       0 |        0 |       0 |       0 |
  rag.ts           |     100 |      100 |     100 |     100 |
  redirect.ts      |     100 |    90.9 |     100 |     100 |
  testing.ts       |       0 |        0 |       0 |       0 |
 router            |   93.71 |    85.48 |   93.33 |   93.71 |
  index.ts         |   91.45 |       85 |   92.85 |   91.45 |
  legacyRedirects.ts|    100 |      100 |     100 |     100 |
 stores            |   95.65 |    91.17 |   93.33 |   95.65 |
  auth.ts          |   90.69 |    88.23 |   85.71 |   90.69 |
  moduleRegistry.ts|     100 |     92.3 |     100 |     100 |
  ui.ts            |     100 |      100 |     100 |     100 |
-------------------|---------|----------|---------|---------|-------------------
ERROR: Coverage for lines (77.76%) does not meet global threshold (80%)
ERROR: Coverage for statements (77.76%) does not meet global threshold (80%)
```

**不达标主因**：v1.4.6 新增前端 API 模块缺少单测 —— `src/core/api/logs.ts` 26.92%、`modules.ts` 0%、`testing.ts` 0%（`modules.ts` 恰为缺陷 DEF-FE-146-001 所在文件）。既有的 router/stores 面已达标（93.71% / 95.65%）。

## 6. 构建验证

```
> npm run build       # vue-tsc --noEmit && vite build
✓ built in 30.99s
EXIT_CODE=0
```
`dist`：**157 个文件 / 3,061,075 字节 / 2.92 MB**。
构建期非阻断告警：`src/core/router/index.ts` 同时被静态与动态导入 → `dynamic import will not move module into another chunk`。

## 7. 缺陷与环境限制（前端轨道汇总）

| 编号 | 级别 | 类型 | 描述 | 证据 |
|------|:----:|:----:|------|------|
| DEF-FE-146-001 | **P1** | 代码缺陷 | 模块开关「修改详情」抽屉字段全空：`src/core/api/modules.ts:41-43` 未解包 ApiSuccess 信封（`return data`），页面按扁平字段读取 → `id/status/effective/request_id` 全 `undefined` | `t3b-deep-cases.json` E2E-MOD-03 |
| DEF-FE-146-002 | **P1** | 质量门禁 | 覆盖率门禁不达标：lines/statements `77.76% < 80%`（`logs.ts 26.92%`、`modules.ts 0%`、`testing.ts 0%`） | §5.2 |
| DEF-FE-146-003 | P2 | 测试工程 | `vitest run --coverage` 在默认 5s 用例超时下 7 条失败（插桩后耗时 ×4.7）；建议覆盖运行时显式提高 `testTimeout` 或拆分重负载用例 | §5.2 |
| ENV-FE-01 | **P1** | 环境限制 | 本机 DB `localhost:5432/openbase` 连接被立即重置 → `/api/v1/tenants`、`/api/v1/users` 500/挂起；RBAC 查库失败 → `log:read`/`module:manage`/`gateway:view` 403（admin 亦如此，而 `/auth/me` 有 `*` 兜底 → 「菜单可见/接口 403」） | `env-frontend.md` §3/§4、`t3a-page-scan.json` |
| ENV-FE-02 | P2 | 环境限制 | 上游 OpenLLM/OpenRAG/OpenMemory 未启动 → `*-proxy` 502/挂起（OpenLLM/OpenRAG/OpenMemory 错误文案明确） | `t3a-page-scan.json` §H |
| ENV-FE-03 | P2 | 需复核 | `/api/v1/dps-proxy/portraits/{id}` 返回 401，响应体为**上游自有信封**（`{"code":"AUTH_401","message":"missing bearer token","data":null,"timestamp":...}`）→ 说明存在应答的上游；需在明确 DPS 运行态的联调环境复核「dps-proxy 是否应注入上游凭据」 | `t3a-page-scan.json` → `/portrait/:id` |
| OBS-FE-01 | P3 | 可测性 | `data-test="logs-time"` 落在 `el-date-picker` 内部隐藏节点（宽高 0），可见控件为 `.el-date-editor--datetimerange` → 建议 `data-test` 落到可见 wrapper | `t3b-deep-cases.json` E2E-LOGS-03 |

## 8. 未执行项与原因（不静默跳过）

| 项 | 原因 | 补救计划 |
|----|------|----------|
| 仓库既有 Playwright 套件 `openbase-ui/tests/e2e/*.spec.ts`（9 关键页） | ① 用例语义依赖上游四服务运行态与真实隔离态（`key-pages.json` 的 accept_states）；② 其证据目录硬编码为 `doc/test/evidence/s6/ui-e2e/`，运行会覆盖 S6 既有证据，超出本次「仅写入 v146」的门禁 | 环境具备上游后，以 `OPENBASE_BASE_URL` 指向联调环境运行，并将 `--reporter/--output` 重定向至 v146 目录 |
| T3a 真实数据成功态巡检 | 上游未启动 + DB 不可用 → 任一数据源均 0 条 | 环境修复后重跑 `scan-pages.mjs`（脚本可复跑，无需改动） |
| T3a 表单提交（写操作）响应采集 | 巡检不点击提交类按钮，避免污染环境数据；本期实际非 GET API 请求 = 0 | 由 T3b 专项覆盖（真实 PATCH 契约断言 E2E-MOD-02/03） |
| 日志中心真实检索结果/真实导出内容校验 | 403 环境阻断 | 修复 DB 后重跑；脚本已内置「200/403 双态互斥前置断言」，可自动切换口径 |
| 真实非管理员账号权限提示 | 环境无第二账号且 DB 不可用无法造角色 | 环境可用后补真实账号用例（本轮已用 `/auth/me` 受控桩验证菜单/路由/接口三层门禁） |
| 逐页截图人工目视 | 本次执行环境不支持图像内容解析 | 110 张截图按「序号-路由」落盘，供人工目视 |

## 9. 证据文件索引

| 文件 | 说明 |
|------|------|
| `doc/test/evidence/v146/env-frontend.md` | 环境就绪、端口/进程、启动日志摘要、环境阻塞与根因证据 |
| `doc/test/evidence/v146/t3a-page-scan.json` | 110 页逐页原始信号（HTTP/请求失败/console/pageerror/DOM/按钮探测/分类/截图名） |
| `doc/test/evidence/v146/t3a-page-scan.md` | T3a 汇总 + A~I 分类统计 + 复测裁定 |
| `doc/test/evidence/v146/t3a-flagged-recheck.json` | 标记页复测（计数修正 + 抗误报）原始数据 |
| `doc/test/evidence/v146/t3b-deep-cases.json` | 19 条 L1 硬断言用例结果（含断言事实与网络洁净断言） |
| `doc/test/evidence/v146/t3b-deep-cases.md` | T3b 用例清单、关键断言事实、缺陷 DEF-FE-146-001 |
| `doc/test/evidence/v146/t3-frontend-summary.md` | 本文件（结构化摘要） |
| `doc/test/evidence/v146/screenshots/` | 110 张巡检截图 + `t3b-*.png` 深度用例截图 |

## 10. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
|------|------|--------|------|
| v1.4.6 | 2026-09-15 | AT-OpenBase-Test | 首版：Step 4 前端轨道（T3a/T3b/E2E/单测/覆盖率/构建）执行结果与缺陷登记 |
