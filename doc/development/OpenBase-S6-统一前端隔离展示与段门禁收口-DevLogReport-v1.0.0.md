# OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S6-DEVLOG-v1.0.0 |
| 版本 | v1.0.1 |
| 状态 | [Approved]（**v1.0.x 修订：S6 段门禁批准（挂起口径）**——2026-09-11 S6 段门禁人工批准；UI-E2E 关键页 PASS（B1）与 L3-2 真实受信通道双签（B2）按挂起口径处理，PENDING 登记不阻断本次批准，交非沙箱环境复核） |
| 日期 | 2026-09-10 |
| 作者 | AI（S6 批次 1~4 开发会话：沙箱内实现、实测与证据归档） |
| 文档主题 | S6 段（前端段，FE-JT 收官）**开发记录报告**：T1 边界收口 → T2 FE-3 模块导航壳 → T3/T4 FE-R1-1/FE-R1-2 回归 → **T5 L3-2 贯通冒烟基座** → **T6 段门禁与台账收口**；含逐任务 RED→GREEN、改动清单（批 1~4 提交号）、版本处置（Q-FE-2b 承载 v1.3.0）、回归结果、遗留与非沙箱复核清单 |
| 上游依据 | ①《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》（OB-S6-DESIGN-v1.0.0）§1.1 Q-FE-1~8、§4 逐任务设计（S6-T1-1~S6-T6-3）、§5 契约与呈现规范、§6 迁移与兼容、§9 里程碑、§10 遗留；②《OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0》（内部 v1.1.0，[Approved]，2026-09-10）§4（22 条验收断言）；③《OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0》§3.6 FE-JT；④《OpenBase-联调产物清点核对总清单-v1.0.0》§1.4；⑤《OpenBase-多系统联调-跨仓提交放行清单-v1.0.0》§0 通用红线第 5 条 |
| 适用范围 | **唯一代码改造面 = 仓内 `openbase-ui/`**；文档面 = 仓根与 `doc/**`。对 DPS/OpenLLM/OpenMemory/OpenRAG 四仓 `frontend/` 与 CI/部署配置**仅只读盘点与口径登记，本批不改动任何子系统仓文件**（Q-FE-1） |
| 证据面 | 沙箱可执行面：`npm run lint` / `npm test` / `npm run test:coverage` / 仓根 `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` / 静态旁路检查 / `npx playwright test --list`；非沙箱复核面：B1~B6（PENDING，禁止伪造） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-10 | AI（S6 批次 1~4 开发会话） | 初始版本：S6 段开发记录报告。含 §1 交付范围与批次划分；§2 逐任务 RED→GREEN（T1~T6）；§3 改动清单（批 1~4 提交号）；§4 版本处置（Q-FE-2b 承载 v1.3.0）；§5 回归结果；§6 遗留与非沙箱复核清单（B1~B6）；§7 提交面纪律与证据归档 |
| v1.0.1 | 2026-09-11 | 项目负责人（段门禁人工批准）/ AI（批准注记回写） | **v1.0.x 修订：S6 段门禁批准（挂起口径）**。状态 [Review] → **[Approved]**；批准口径（统一逐字登记）：`2026-09-11 S6 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认；前端侧门禁全绿（覆盖率 97.08/90/88.46/97.08 达标、lint 0 problem、FE-R1-1/FE-R1-2 前端侧通过、FE-3 达成、3 处改造口径闭环）；UI-E2E 关键页 PASS（B1）与 L3-2 真实受信通道双签（B2）按挂起口径处理（PENDING 登记不阻断本次批准，交非沙箱环境复核）；遗留=无阻断项`。本文档 §1~§7 内容与 §6 B1~B6 挂起登记口径**不变**（未新增/删除实测值），仅回写状态/内部版本与批准注记 |

---

## §1 交付范围与批次划分

S6 = 前端段（FE-JT 收官），任务依赖 `T1 → T2 → {T3 ∥ T4} → T5 → T6`（设计草案 §9）。四批提交：

| 批次 | 提交（hash） | 主题 | 覆盖任务 |
|:---:|------|------|---------|
| 批 1 | `2abe52a` | `feat(ui): S6-T1 统一前端冻结与改造口径登记 + lint 转绿` | S6-T1-1~4 |
| 批 2 | `aa6c5bd` | `feat(ui): S6-T2 模块导航壳与 S6-T3 隔离呈现回归 + 发布形态参数化` | S6-T2-1~4、S6-T3-1~4、Q-FE-2b |
| 批 3 | `72b19da` | `feat(ui): S6-T4 登录态与吊销回归（安全回跳/单飞刷新/403 无白屏/OIDC 清理）` | S6-T4-1~4 |
| 批 4 | `477eb80` | `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写` | S6-T5-1~3、S6-T6-1~3 |

> 批 1~4 提交 hash 均为本仓已入库实测值（批 4 `477eb80` = `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`）。**未产真实结果的项一律 PENDING，禁止伪造 hash 与通过**（对齐设计草案 §1.4 纪律与立项 R-4）。

## §2 逐任务 RED→GREEN

### 2.1 T1 边界收口（批 1，`2abe52a`）

| 项 | 内容 |
|----|------|
| RED | 新增仓根静态断言 `tests/test_s6_t1_frontend_boundary.py` 时：① OpenBase 后端 `StaticFiles`/`mount(`/`dist-v` 扫描断言缺登记文档与白名单；② `npm run lint` 退出码 1（`PortraitDetail.vue` `vue/no-use-v-if-with-v-for`） |
| GREEN | ① 登记文档 + 白名单落地，静态断言 **9 passed**；② `PortraitDetail.vue` 模板修复（`v-if` 提到 wrapper）→ `npm run lint` 0 problem；③ 冻结声明落点 `openbase-ui/docs/frontend-frozen.md` |
| 证据 | `tests/test_s6_t1_frontend_boundary.py`（9 passed）；`doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md` |
| 非沙箱 | B5（四仓物理改造）、B6（`/ui/` 切换实测） |

### 2.2 T2 FE-3 模块导航壳（批 2，`aa6c5bd`）

| 项 | 内容 |
|----|------|
| RED | `tests/router-nav.spec.ts` 复现「注册表已初始化但未装载 → 深链 `/portrait/list` 回 `/dashboard`（丢上下文）」与「顶层模块项在子页不高亮」 |
| GREEN | `router/index.ts` 装载**幂等必达**（守卫内无条件 `mountModuleRoutes()`；`router.hasRoute` + `module.loaded` 双条件跳过）；`moduleRegistry.loadRoutes` 收敛为委托真实装载；`AppLayout.vue` `activeMenu` 计算属性 + `iconMap` 补齐；`ModuleLayout.vue` 空态兜底；`nav-consistency.spec.ts` 5 模块菜单↔路由一致性（含显式白名单） |
| 证据 | `openbase-ui/tests/router-nav.spec.ts`、`tests/nav-consistency.spec.ts`（全绿）；`npm test` 11 files / 104 tests（批后） |
| 非沙箱 | B1（浏览器层 `console.warn = 0` 复核） |

### 2.3 T3 FE-R1-1 UI 隔离回归（批 2，`aa6c5bd`）

| 项 | 内容 |
|----|------|
| RED | `tests/isolation-presentation.spec.ts` 先断言四类判定（空/403/404/5xx）与「无白屏/无堆栈泄漏」，初版页面分类缺失 → 失败 |
| GREEN | 新增 `src/core/api/error.ts`（`classifyError`/`describeError`，§5.1/§5.2 判定表）+ 各关键页按 `kind` 渲染（`isolation-empty` / `isolation-forbidden` / `isolation-not-found` / `isolation-error-bar` + 重试）+ `AppLayout.vue` `onErrorCaptured` 渲染兜底（防白屏）+ `request_id` 仅详情展示、不落 URL/localStorage |
| 证据 | `tests/isolation-presentation.spec.ts`（画像/记忆/知识/对话分支 + 停用主体分支 + 渲染兜底） |
| 非沙箱 | B3（真实双租户数据面复核） |

### 2.4 T4 FE-R1-2 登录态/吊销回归（批 3，`72b19da`）

| 项 | 内容 |
|----|------|
| RED | `tests/http.spec.ts` / `tests/auth-redirect.spec.ts`：既有实现 401 刷新失败用 `window.location.href` 整页跳转（丢 `redirect`、丢 SPA 上下文）；403 走统一 `ElMessage.error` 兜底 |
| GREEN | `src/core/api/redirect.ts`（`safeRedirect()` 站内回跳校验 + 注册式 SPA 导航）；`http.ts` 401 单飞刷新单飞 Promise 复位、失败 `clear()` + `router.replace('/auth/login?redirect=…')`；403/404 分类为页面级、不触发刷新风暴、不弹全局 toast；`OidcCallback.vue` 落 token 后清 `hash` 防残留；`stores/auth.ts` `loadMe` 失败可观测 |
| 证据 | `tests/http.spec.ts`、`tests/auth-redirect.spec.ts`、`tests/oidc-auth.spec.ts`（全绿）；批后 `npm test` 12 files / 129 tests |
| 非沙箱 | B4（真实 IdP 回调/吊销链路） |

### 2.5 T5 L3-2 贯通冒烟（批 4，本批次）

| 断言 | RED（先测） | GREEN（后实现） | 证据 | 执行面 |
|------|------------|----------------|------|--------|
| **S6-T5-1** | 先新增 `tests/l3-2-smoke.spec.ts`（引用 `tests/e2e/fixtures/key-pages.json` 与 `scripts/smoke_l3_2_ui.mjs`）→ `npx vitest run tests/l3-2-smoke.spec.ts` **退出码 1**：`Failed to resolve import "./e2e/fixtures/key-pages.json"` | 落地①`tests/e2e/fixtures/key-pages.json`（Q-S6-D6 同源清单）；②`scripts/smoke_l3_2_ui.mjs`（零依赖 Node 原生 fetch，仅 `OPENBASE_BASE_URL` 入口，携带 `X-Proxy-Source`，输出 `doc/test/evidence/s6/l3-2-smoke.json`）；③静态旁路检查（端口字面量白名单外=0 + API 客户端零绝对地址 + `baseURL=/api/v1`）→ 用例 **8 passed**；`npm run smoke:l3-2`：静态检查 PASS、受信通道不可达 → `status=PENDING`（**退出码 2**） | `tests/l3-2-smoke.spec.ts`；`doc/test/evidence/s6/l3-2-smoke.json` | 沙箱（静态面）/ B2（真实双签 PENDING） |
| **S6-T5-2** | 无 `playwright.config.ts` 与 `tests/e2e/*.spec.ts` → `npm run test:e2e` 无测试可跑 | 落地 `playwright.config.ts`（证据落 `doc/test/evidence/s6/ui-e2e/`）+ 4 个 spec（chat/knowledge/memory/portrait，共 **9 页**）+ `tests/e2e/support/key-page.ts`（渲染/关键元素可见/无渲染兜底/无 console error/warn 断言）→ `npx playwright test --list` **9 tests in 4 files（退出码 0）**；`npm run test:e2e` → 9 failed（浏览器二进制未安装，**非断言失败**） | `doc/test/evidence/s6/ui-e2e/status.json`、`results.json` | 沙箱（配置/用例）/ B1（执行 PENDING） |
| **S6-T5-3** | 无证据 JSON | 冒烟脚本输出 `pending` 数组与 `reason`（受信通道不可达），失败项按 PENDING 挂起登记、不伪造 | `doc/test/evidence/s6/l3-2-smoke.json` | 沙箱（登记）/ B2 |

> **静态旁路检查实测（2026-09-10）**：端口字面量命中 **8/8 白名单**（`Conversations.vue`/`Models.vue`/`Playground.vue` 错误提示文案；`ConfigManageView.vue`/`AuditLogsView.vue`/`EdgeRouterView.vue`/`GatewayServicesView.vue` mock/表单数据）；绝对 URL 命中 **10/10 白名单**（示例域名/占位/mock base_url）；`src/core/api/**` 绝对地址 **0**；`http.ts` `baseURL = /api/v1`。**白名单外命中 = 0**（口径：设计草案仅示例 `Conversations.vue` 文案；本批实测补齐其余 7 类展示/mock 命中并逐条登记理由，为**如实扩展**而非放宽）。

### 2.6 T6 段门禁与台账收口（批 4，本批次）

| 断言 | RED | GREEN | 证据 |
|------|-----|-------|------|
| **S6-T6-1** | 无段门禁聚合与 UI-E2E 逐页结论 | 新增 `doc/test/evidence/s6/segment-gate.json`（7 项门禁 + 22 断言矩阵）、`ui-e2e/status.json`（9 页逐页 PENDING + 实际尝试命令与失败原因） | `doc/test/evidence/s6/segment-gate.json`、`ui-e2e/status.json` |
| **S6-T6-2** | 无覆盖率/Lint 最终值归档 | 新增 `doc/test/evidence/s6/coverage-summary.json`；重跑三门禁：`npm run lint`（0 problem/退出 0）、`npm test`（13 files / 137 tests/退出 0）、`npm run test:coverage`（97.08/90/88.46/97.08，阈值 80/80/80/70/退出 0）；**未放宽 thresholds 与 include** | `coverage-summary.json`、`segment-gate.json` |
| **S6-T6-3** | 台账无 S6 段门禁行 | 回写 JT 归集 §3.6（v1.2.0→v1.3.0）、放行清单（v1.0.6→v1.0.7）、清点总清单（v1.0.3→v1.0.4）、S6 冻结口径登记（v1.0.1→v1.0.2）；状态回写立项方案（v1.1.0→v1.1.1）与设计草案（v1.0.0→v1.0.1，[Draft]→[Approved]）；evidence 含 `openbase_commit`/`ui_version` | 各台账 diff；evidence JSON 字段 |

## §3 改动清单（批 4；含批 1~3 提交号桥接）

### 3.1 新增文件（批 4）

| 文件 | 类型 | 说明 |
|------|------|------|
| `openbase-ui/playwright.config.ts` | E2E 配置 | 关键页 E2E 引擎配置；证据落 `../doc/test/evidence/s6/ui-e2e/`（report/、artifacts/ 已 gitignore） |
| `openbase-ui/tests/e2e/fixtures/key-pages.json` | 同源 fixture | Q-S6-D6：9 关键页清单 + 页面断言要素 + 静态旁路白名单（端口/绝对 URL） |
| `openbase-ui/tests/e2e/support/key-page.ts` | E2E 支持 | 关键页 PASS 断言（渲染/关键元素/无渲染兜底/无 console error·warn）+ 登录态注入 |
| `openbase-ui/tests/e2e/portrait.spec.ts` | E2E 用例 | 画像 3 页（list/overview/:id） |
| `openbase-ui/tests/e2e/memory.spec.ts` | E2E 用例 | 记忆 2 页（list/sessions） |
| `openbase-ui/tests/e2e/knowledge.spec.ts` | E2E 用例 | 知识 2 页（list/:id） |
| `openbase-ui/tests/e2e/chat.spec.ts` | E2E 用例 | 对话 2 页（/knowledge/chat、/openllm/conversations） |
| `openbase-ui/scripts/smoke_l3_2_ui.mjs` | 冒烟脚本 | 零依赖 L3-2 贯通冒烟（受信通道 + 来源标识 + 越权/空态 + 静态旁路检查 + evidence JSON） |
| `openbase-ui/tests/l3-2-smoke.spec.ts` | vitest 用例 | T5 基座断言（fixture 同源/受信通道约束/静态旁路检查），8 用例 |
| `doc/test/evidence/s6/l3-2-smoke.json` | 证据 | 冒烟结果（`status=PENDING`、`pending` 原因、静态检查明细、commit/version/时间戳） |
| `doc/test/evidence/s6/ui-e2e/results.json` | 证据 | Playwright JSON 报告（9 failed：浏览器二进制缺失） |
| `doc/test/evidence/s6/ui-e2e/status.json` | 证据 | UI-E2E PENDING 说明（含 4 条实际尝试命令与失败原因） |
| `doc/test/evidence/s6/coverage-summary.json` | 证据 | 覆盖率/Lint 最终值 |
| `doc/test/evidence/s6/segment-gate.json` | 证据 | 段门禁聚合（7 项 + 22 断言矩阵） |
| `doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md` | 文档 | 本文件 |
| `doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md` | 文档 | S6 测试报告 v1.0.0 |

### 3.2 修改文件（批 4）

| 文件 | 变更 |
|------|------|
| `openbase-ui/package.json` | devDependency 增 `@playwright/test ^1.63.0`；scripts 增 `test:e2e`（`playwright test`）、`smoke:l3-2`（`node scripts/smoke_l3_2_ui.mjs`）；版本保持 **1.3.0** |
| `openbase-ui/package-lock.json` | 随 `@playwright/test` 依赖解析更新 |
| `openbase-ui/vite.config.ts` | 引入 `vitest/config` 的 `configDefaults`；`test.exclude` 增 `tests/e2e/**`（避免 Playwright 用例被 vitest 误收集） |
| `.gitignore`（仓根） | 增补 `doc/test/evidence/s6/ui-e2e/report/`、`doc/test/evidence/s6/ui-e2e/artifacts/`（运行期产物不入库） |
| `doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md` | 内部 v1.0.1 → **v1.0.2**（登记 T5/T6 结论与 3 处改造物理闭环 PENDING） |
| `doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md` | 内部 v1.0.3 → **v1.0.4**（新增 §5.7 S6 段门禁登记，仅加注不改计数） |
| `doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md` | 内部 v1.0.6 → **v1.0.7**（登记 S6 结论与 OpenBase 仓 S6 提交批次，仅加注） |
| `OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md` | 内部 v1.2.0 → **v1.3.0**（§3.6 FE-JT 行状态回写 + 提交号桥接 + 修订历史） |
| `OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md` | 内部 v1.1.0 → **v1.1.1**（段门禁结论注记） |
| `OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md` | 内部 v1.0.0 → **v1.0.1**（状态 [Draft] → [Approved]，注记 2026-09-10 人工批准进入开发 T1~T6） |

### 3.3 批 1~3 主要落点（已入库，提交号桥接）

| 批次 | 主要落点 |
|:---:|---------|
| 批 1（`2abe52a`） | `tests/test_s6_t1_frontend_boundary.py`、`openbase-ui/docs/frontend-frozen.md`、`doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md`（v1.0.0/v1.0.1）、`src/modules/portrait/pages/PortraitDetail.vue`（lint 修复） |
| 批 2（`aa6c5bd`） | `src/core/router/index.ts`、`src/core/stores/moduleRegistry.ts`、`src/core/layouts/{AppLayout,ModuleLayout}.vue`、5 模块 `index.ts`、`src/core/api/error.ts`、关键页呈现改造、`tests/{router-nav,nav-consistency,isolation-presentation}.spec.ts`、`scripts/build_release.ps1`、`.gitignore`（openbase-ui）、`nginx.conf.example`、`package.json` 1.3.0 |
| 批 3（`72b19da`） | `src/core/api/{http,redirect}.ts`、`src/core/stores/auth.ts`、`src/pages/{Login,OidcCallback}.vue`、`tests/{http,auth-redirect,oidc-auth}.spec.ts` |

> 未纳入提交面（Q-FE-1 / R-10）：`dogfood-output/`、`coverage/`、`node_modules/`、`dist-v*`、Playwright 运行期产物（`ui-e2e/report/`、`ui-e2e/artifacts/`）；**不含任何子系统 `frontend/` 文件**。

## §4 版本处置（Q-FE-2 / Q-FE-2b）

| 项 | 结论 |
|----|------|
| 承载版本 | `openbase-ui/package.json` version = **1.3.0**（S6 承载版本；批 2 完成，Q-S6-D1「T6 前升」） |
| 版本目录 | `scripts/build_release.ps1` 由 `package.json.version` 派生 `dist-v$Version`（无硬编码） |
| 忽略规则 | `openbase-ui/.gitignore` 含 `dist-v*`（`git check-ignore` 命中） |
| nginx | `nginx.conf.example` 同域 `/ui/`（alias → `dist-v1.3.0/`）+ `/api/` 反代 + SSE `proxy_buffering off` |
| 与 JT 线桥接 | 统一前端产品版本线（v1.3.0）与 OpenBase 仓版本线解耦，与 JT 行以**提交号**桥接（Q-FE-8） |
| 回滚 | 仅切 nginx alias 至上一版本目录；无数据库迁移（INV-5） |

## §5 回归结果（2026-09-10，沙箱内实测）

| # | 命令（工作目录） | 结果摘要 | 退出码 |
|---|----------------|---------|--------|
| 1 | `npm run lint`（openbase-ui） | `eslint src --ext .ts,.vue && vue-tsc --noEmit` **0 problem**（含新增 `tests/e2e/**` 类型检查） | **0** |
| 2 | `npm test`（openbase-ui） | Test Files **13 passed (13)**、Tests **137 passed (137)**（批 3 基线 12/129，本批新增 `tests/l3-2-smoke.spec.ts` 8 用例） | **0** |
| 3 | `npm run test:coverage`（openbase-ui） | All files：stmts **97.08%** / branches **90%** / funcs **88.46%** / lines **97.08%**（阈值 80/80/80/70，全部达标；**未放宽 thresholds 与 include**） | **0** |
| 4 | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q`（仓根） | **9 passed** | **0** |
| 5 | `npx vitest run tests/l3-2-smoke.spec.ts`（openbase-ui） | **8 passed**（T5 基座） | **0** |
| 6 | `npx playwright test --list`（openbase-ui） | **9 tests in 4 files**（配置/用例可解析） | **0** |
| 7 | `npm run smoke:l3-2`（`OPENBASE_BASE_URL=http://127.0.0.1:8000`） | 静态旁路检查 PASS；受信通道不可达 → `status=PENDING` | **2**（PENDING，按约定非 0） |
| 8 | `npm run test:e2e`（openbase-ui） | **9 failed**（浏览器二进制未安装：`Please run npx playwright install`）→ B1 PENDING | **1** |
| 9 | `npx playwright install chromium`（openbase-ui） | **FAILED**：`EPERM: operation not permitted, mkdir 'C:\Users\jerry\AppData\Local\ms-playwright\__dirlock'`（沙箱受限） | **1** |

## §6 遗留与非沙箱复核清单

| # | 项 | 现状 | 处置 |
|---|----|------|------|
| B1 | Playwright 关键页 PASS（9 页） | 用例/配置就绪（`--list` 通过）；浏览器二进制安装被沙箱拒绝 → PENDING | 非沙箱 `npx playwright install chromium` + `OPENBASE_BASE_URL`/token → `npm run test:e2e` 回填 |
| B2 | L3-2 真实受信通道端到端（真实 HTTP 双签） | 静态检查 PASS、脚本就绪；通道不可达 → PENDING | 沙箱外配置受信通道与凭据 → `npm run smoke:l3-2` 回填 `status` |
| B3 | 跨域 403/空 真实数据面 | 组件层四类判定全绿；真实双租户未执行 | 沙箱外双租户数据面复核（RA-06 前端侧面） |
| B4 | OIDC 真实 IdP 回调链路 / 真实吊销 | fragment 解析与缺令牌错误页全绿；真实 IdP/吊销未执行 | 沙箱外 IdP/网关可达时复核 |
| B5 | 四仓 `frontend/` 物理改造与 CI 收敛 | 口径登记完成；物理闭环未执行 | 各子系统仓后续批次 + S7 按 Q-S6-D7 复核 |
| B6 | nginx `/ui/` 发布与回滚实测 | 版本目录与脚本就绪；切换实测未执行 | 沙箱外 nginx + 运行态复核 |
| L1 | 模块页覆盖率度量 | Q-FE-7b：`coverage.include` 不扩大；模块页由关键页 PASS（B1）承载 | 随 B1 完成 |
| L2 | OpenLLM 全模块 UI-E2E PASS | 增强项（不阻塞 S6 段门禁） | S6 增强 / S7 |

## §7 提交面纪律与证据

- **逐项显式 `git add`**（禁用 `git add -A` / `git add .`）；提交前 `git diff --cached --stat` 复查（放行清单 §0 红线第 1 条）。
- 提交面白名单：仓根与 `doc/**` 文档 + `openbase-ui/**` 代码/配置 + `doc/test/evidence/s6/**` 证据；**排除** `dogfood-output/`、`dist-v*`、`coverage/`、`node_modules/`、`ui-e2e/report/`、`ui-e2e/artifacts/`。
- **不含任何子系统仓文件**（Q-FE-1）；未对 DPS/OpenLLM/OpenMemory/OpenRAG 做任何写操作。
- evidence 真实性：`l3-2-smoke.json` 含 `openbase_commit`（执行时 HEAD）、`ui_version`（1.3.0）、`started_at`/`finished_at`、`status`/`reason`/`pending`；不可达项一律 PENDING，**未编造 hash/截图/报告**。

---

> **文档结束**。本文档为 S6 段「开发」环节交付物（**[Approved]** v1.0.1；**v1.0.x 修订：S6 段门禁批准（挂起口径）**——2026-09-11 人工批准，UI-E2E 关键页 PASS（B1）与 L3-2 真实受信通道双签（B2）按挂起口径 PENDING 登记不阻断本次批准）；与设计草案 v1.0.2（[Approved]）、测试报告 v1.0.1（[Approved]）、evidence 归档共同构成 S6 段门禁（T6）的可核对证据链；非沙箱项（B1~B6）待受控环境回填后按 Q-FE-6 移交 S7。
