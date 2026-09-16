# OpenBase v1.4.6 · T3b 深度用例报告（日志中心 / 模块开关，L1 硬断言）

| 项目 | 内容 |
|------|------|
| 文档编号 | OB-TEST-EVIDENCE-T3B-DEEP-CASES-v1.4.6 |
| 版本号 | v1.4.6 |
| 状态 | [Draft]（证据文件） |
| 执行角色 | AT-OpenBase-Test（测试工程师） |
| 执行日期 | 2026-09-15 |
| 被测页面 | `/platform/observability/logs`（日志中心）、`/platform/config/modules`（模块开关） |
| 执行方式 | Playwright（chromium headless）临时脚本 `work/t3b-deep-cases.mjs`，`npm run build` + `npx vite preview --port 4173` 提供静态服务 |
| 原始数据 | `doc/test/evidence/v146/t3b-deep-cases.json` |
| 截图 | `doc/test/evidence/v146/screenshots/t3b-*.png` |

## 1. 断言纪律（本套用例遵守的硬约束）

| 纪律 | 落地方式 |
|------|----------|
| L1 硬断言 | 自研 `assertTrue/assertEqual/assertMatches/assertIncludes`，不满足即抛错 → 用例判 FAIL |
| 禁止 if-else 软断言 | 无「条件为真才断言」分支；环境分支以**互斥前置断言**表达（如 `assertEqual(envBlocked, true, ...)`） |
| 禁止 try-catch 吞异常 | 用例体内无异常捕获；`runCase` 仅记录失败（FAIL）并置非零退出码 |
| 每条用例末尾 `assert_network_clean()` | 全部 19 条均执行；**用例中途 FAIL 时也在捕获后补执行**（记录 `checked_after_failure: true`） |
| 洁净断言白名单 | 仅含已登记环境类：DB 派生 403/500、`*-proxy` 502/503/504、浏览器网络镜像 console.error；**未登记违规必须为 0** |

## 2. 执行环境前提（不可静默跳过的登记项）

| 项 | 实测 | 判定 |
|----|------|------|
| `GET /api/v1/logs/search`（admin） | **403 `AUTH_403 "missing permission: log:read"`** | `env_blocked=true`；根因为本机 DB 不可用 → RBAC 路径回退内存 store（空），见 `env-frontend.md` §3/§4 |
| `PATCH /api/v1/modules/{id}`（admin） | **403 `AUTH_403`**（同源根因） | 启停成功路径改以**契约一致的受控桩**覆盖（桩响应体 = 后端真实 `{code,message,data}` 信封） |
| 无数据（上游未启动 + DB 不可用） | 全部数据源 0 条 | 成功态/空态/分页/导出 以 `page.route` 受控桩构造，**不依赖后端数据**，不阻塞也不跳过 |

> 说明：受控桩仅作用于浏览器运行时的网络层（`page.route`），**未修改仓库源码与测试文件**；桩响应体严格对齐后端契约，非「迎合实现」的弱化桩。

## 3. 用例清单与结果（19 条：18 PASS / 1 FAIL）

| 用例 ID | 断言级别 | 标题 | 结果 |
|---------|:--------:|------|:----:|
| E2E-LOGS-01 | L1 | 页面可达 + 检索区/表格/分页骨架渲染 | PASS |
| E2E-LOGS-02 | L1 | 检索请求契约（URL/方法/query）+ 环境阻断口径登记 | PASS |
| E2E-LOGS-03 | L1 | 四维分类筛选器（关键字/模块/操作/结果/时间）枚举完整 | PASS |
| E2E-LOGS-04 | L1 | 数据源切换重置分页并改发 `source=audit_db` | PASS |
| E2E-LOGS-05 | L1 | 加载态（请求在途时 loading 呈现并消失） | PASS |
| E2E-LOGS-06 | L1 | 错误态渲染（error 提示 + 重试可用 + 导出禁用） | PASS |
| E2E-LOGS-07 | L1 | 空态（桩 200 + `items=[]`：空文案/计数/导出禁用/facets 不渲染） | PASS |
| E2E-LOGS-08 | L1 | 成功态 + facets 四维分类 + 详情抽屉（桩 2 行数据） | PASS |
| E2E-LOGS-09 | L1 | 分页交互（桩 total=25 → 第 2 页请求 `page=2`） | PASS |
| E2E-LOGS-10 | L1 | 导出 CSV（桩 total>0 → `/logs/export?format=csv` + 文件名） | PASS |
| E2E-LOGS-11 | L1 | 关键字防抖自动检索（400ms 防抖 → 仅 1 次请求且带 `q`） | PASS |
| E2E-LOGS-12 | L1 | 权限门禁：无 `log:read` 的用户直访 → `/forbidden`（含 `from` 保留） | PASS |
| E2E-MOD-01 | L1 | 模块列表加载（表头 6 列 + 行数 ≥4 + 字段渲染 + 开关数=行数） | PASS |
| E2E-MOD-02 | L1 | 启停写请求契约 + 环境阻断 + 失败回滚 | PASS |
| E2E-MOD-03 | L1 | 启停成功路径 → 抽屉呈现 `request_id` 与「下次登录/刷新」 | **FAIL（真实缺陷 DEF-FE-146-001）** |
| E2E-MOD-04 | L1 | 空态（桩 `items=[]` → 「暂无模块」） | PASS |
| E2E-MOD-05 | L1 | 错误态（计数桩：启动轮 200 → 刷新轮 500 → 「加载失败」+ 保留旧数据） | PASS |
| E2E-MOD-06 | L1 | 权限门禁：无 `module:manage` → `/forbidden`（含 `from` 保留） | PASS |
| E2E-MOD-07 | L1 | 权限提示（菜单级同源）：`模块开关`/`测试记录` 不渲染、`日志中心`/`全局配置` 渲染 | PASS |

## 4. 关键断言事实（真实观测值）

### 4.1 日志中心

| 用例 | 观测 |
|------|------|
| LOGS-02 | 请求 `GET /api/v1/logs/search?source=l1_file&page=1&page_size=20`；响应 `403 AUTH_403`（=已登记环境阻断） |
| LOGS-03 | 模块枚举 8 项（身份/数据处理/检索/记忆/大模型/网关/测试/其他）、操作 6 项、结果 4 项；高级筛选 case_id/run_id/step_id 三输入齐备；时间控件可见（`.el-date-editor--datetimerange` 340×32） |
| LOGS-04 | 切「审计库」→ 1 次请求且含 `source=audit_db`、`page=1` |
| LOGS-05 | 在途时 `.el-loading-mask` 可见且检索按钮 `is-loading`；响应后遮罩数 = 0 |
| LOGS-06 | `logs-error` 可见、文本含 `403`、数据行 0、计数「共 0 条」、导出禁用；点「重试」再次发出 1 次检索请求 |
| LOGS-07 | 空态文案「暂无匹配日志」、计数「共 0 条」、导出禁用、facets 卡片不渲染 |
| LOGS-08 | 2 行数据、facets 标签 5 个（模块2+操作1+结果2）、`request-id-req-t3b-1` 渲染；点行后抽屉摘要含 `t3b-sample-1`、含 `req-t3b-1`、模块标签映射「数据处理」正确 |
| LOGS-09 | 首页 20 行；翻第 2 页 → 1 次请求且含 `page=2`、`page_size=20`；第 2 页 1 行 |
| LOGS-10 | 导出文件名 `logs-csv-l1_file.csv`；请求含 `format=csv`、`source=l1_file` |
| LOGS-11 | 输入 `req-t3b` → 1 次请求且含 `q=req-t3b`、`page=1`（防抖生效） |
| LOGS-12 | 桩 `me.permissions=['openllm:view']` → 最终路径 `/forbidden`，`from=/platform/observability/logs` |

### 4.2 模块开关

| 用例 | 观测 |
|------|------|
| MOD-01 | 表头 6 列齐全；行数 ≥4；首行含 `/openllm`、`openllm:view`；开关数=行数；初始全部启用 |
| MOD-02 | 点击开关 → 恰好 1 次 `PATCH /api/v1/modules/{id}` → **403**（已登记环境阻断）；`.el-message--error` 可见（非静默失败）；失败后重新 `GET /api/v1/modules` 回滚，开关视觉恢复启用态 |
| MOD-03 | **失败**：抽屉「修改详情」仅渲染标签，字段值全空（`模块/新状态/生效方式/请求号` 均无值）→ 见 §5 |
| MOD-04 | 空态文案「暂无模块」，数据行 0 |
| MOD-05 | 桩调用 ≥3 轮；刷新轮 500 → `el-alert` 含「加载失败」；表格保留上一轮 2 行（不清表） |
| MOD-06 | 桩 `me.permissions=['log:read']` → 最终路径 `/forbidden`，`from=/platform/config/modules` |
| MOD-07 | 侧栏 DOM 菜单项：**含** 日志中心/全局配置/统一监控…，**不含** 模块开关、测试记录（权限过滤与路由 `meta.permission` 同源） |

## 5. 缺陷：DEF-FE-146-001（P1）

| 项 | 内容 |
|----|------|
| 现象 | 模块开关页启停成功后，「修改详情」抽屉 `模块 / 新状态 / 生效方式 / 请求号` 四项**值全空**（仅标签渲染） |
| 复现 | `page.route` 桩返回**后端真实 PATCH 契约** `{"code":0,"message":"ok","data":{id,status,previous_status,effective,request_id}}` → 点击任意模块开关 |
| 观测原文 | `"修改详情\n模块\t\n新状态\t\n生效方式\t\n请求号\t"` |
| 根因 | `src/core/api/modules.ts:41-43`：`const { data } = await http.patch<ModuleSwitchResult>(...)` 后 **直接 `return data`**，而 `data` 是 axios body 即 `{code,message,data}` 信封；页面 `ModuleSwitchView.vue:54-60` 却按扁平字段 `lastResult.id/status/effective/request_id` 读取 → 全部 `undefined` |
| 旁证 | 同仓 `src/core/api/logs.ts` 全部使用 `data.data` 解包（正确口径）；`ModuleSwitchResult` 类型注释声称「后端 PATCH 返回 data，扁平字段」，与实现不一致 |
| 影响 | v1.4.6 AC-146-15「生效语义可见」不成立（用户看不到 `request_id` 与「下次登录/刷新」），且状态回写 `target.status = result.status` 被写成 `undefined`（表格状态字段失真） |
| 修复方向 | `modules.ts` 改 `return data.data`（与 logs.ts 对齐）；或页面改读 `lastResult.data.*` |
| 证据 | `t3b-deep-cases.json#cases[E2E-MOD-03]`、`screenshots/t3b-modules-03-success-drawer.png` |

## 6. 网络洁净断言结果（`assert_network_clean`）

| 用例 | 受判定违规数 | 命中白名单（已登记环境类） | 未登记违规 |
|------|:-----------:|:--------------------------:|:----------:|
| LOGS-01 / 07 / 08 / 09 / 10 / 12、MOD-01 / 04 / 06 / 07 | 0 | 0 | **0** |
| LOGS-02 / 03 / 04 / 05 / 06 / 11 | 2~4 | 2~4（DB 403 + 网络镜像） | **0** |
| MOD-02 | 2 | 2（DB 403 + 网络镜像） | **0** |
| MOD-05 | 1 | 1（桩自造 500 已剔除后仍余网络镜像） | **0** |
| MOD-03 | 见 JSON（用例中途 FAIL，末尾补执行） | — | — |

全部用例「未登记违规 = 0」，说明除已登记环境类外，被测页面在用例执行期间**无 console.error / pageerror / 网络失败 / 前端直连端口**。

## 7. 未执行项与补救计划（不静默跳过）

| 项 | 状态 | 原因 | 补救计划 |
|----|------|------|----------|
| 日志中心真实数据检索/四维分类筛选结果校验 | **未执行**（形态已覆盖） | 403 环境阻断（RBAC 依赖 DB） | 修复 DB 后重跑 `t3b-deep-cases.mjs`；届时 `env_blocked=false`，LOGS-02/06 自动切换为 200 口径真实断言（脚本已内置两态互斥前置断言） |
| 日志中心真实导出内容校验 | **未执行**（请求契约与文件名已覆盖） | 同上（403） | 同上；补断言导出 CSV 表头与行数 |
| 模块启停真实成功路径（含审计留痕） | **未执行**（契约与 UI 反馈已覆盖） | `module:manage` 403（RBAC 依赖 DB） | 修复 DB 后重跑 MOD-02/03；届时断言 200 + 抽屉字段 + 审计留痕 |
| 非管理员账号的真实登录态权限提示 | **部分覆盖**（以 `/auth/me` 受控桩构造权限集） | 环境无第二账号且 DB 不可用无法造角色 | 环境可用后补「真实非管理员账号 + 菜单/接口双向门禁」用例 |

## 8. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
|------|------|--------|------|
| v1.4.6 | 2026-09-15 | AT-OpenBase-Test | 首版：19 条 L1 硬断言用例（18 PASS / 1 FAIL）、缺陷 DEF-FE-146-001、网络洁净断言与未执行项登记 |
