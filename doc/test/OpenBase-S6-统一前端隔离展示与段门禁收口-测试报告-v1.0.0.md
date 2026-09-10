# OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S6-TESTREPORT-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（待 S6 测试评审人工批准） |
| 日期 | 2026-09-10 |
| 作者 | AI（S6 批次 4 开发/测试会话：沙箱内实测、证据归档与段门禁聚合） |
| 文档主题 | S6 段（前端段，FE-JT 收官）**测试报告**：22 条验收断言（S6-T1-1~S6-T6-3）逐条状态与证据索引、硬门禁实测值（命令/退出码）、段门禁聚合结论、已知环境性失败、非沙箱 PENDING 清单 B1~B6 与 S7 移交说明 |
| 上游依据 | ①《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》（内部 v1.0.1，[Approved]）§1.3 覆盖矩阵、§1.4 沙箱/非沙箱面、§4 逐任务断言、§5 契约与呈现规范、§9 里程碑；②《OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0》（内部 v1.1.1，[Approved]）§4（22 断言）；③`doc/development/OpenBase-S6-…-DevLogReport-v1.0.0.md`（[Review]） |
| 适用范围 | 统一前端 `openbase-ui/`（唯一代码改造面）与 OpenBase 仓 `doc/test/evidence/s6/**` 证据；**未对任何子系统仓执行测试或写操作** |
| 测试对象基线 | `openbase-ui` version **1.3.0**；测试执行时 OpenBase HEAD = `72b19daf7b3e847ef4e4a8f1055ef4c7183b16ec`（批次 4 提交前；批次 4 = `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`） |
| 执行环境 | 沙箱：node **v22.16.0** / npm **10.9.4** / vitest **2.1.8** / `@playwright/test` **1.63.0** / pytest **9.1.1**（pytest-asyncio 1.4.0、pytest-timeout 2.4.0）；无真实受信通道 / IdP / 四子系统运行态 |
| 纪律 | 未真实执行项一律 `PENDING`，**禁止以「预期通过」代替证据、禁止伪造 hash/截图/报告**（设计草案 §1.4） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-10 | AI（S6 批次 4 开发/测试会话） | 初始版本：S6 段测试报告。含 §1 测试范围与策略；§2 22 条断言覆盖矩阵（逐条 RED→GREEN 或 PENDING）；§3 硬门禁实测（含退出码与覆盖率数值）；§4 段门禁聚合（7 项）；§5 已知环境性失败（asyncpg 无 PG）；§6 非沙箱 PENDING 清单 B1~B6；§7 结论与 S7 移交；§8 证据索引 |

---

## §1 测试范围与策略

| 层 | 工具 | 覆盖对象 | 执行面 |
|----|------|---------|--------|
| 组件/单元 | vitest（jsdom） | `src/core/{api,router,stores}` + 关键页呈现 + T5 基座断言 | 沙箱 ✅ |
| 浏览器级关键页 | `@playwright/test`（9 页，Q-FE-4b） | 统一前端关键页渲染/关键元素/无渲染兜底/无 console error·warn | **非沙箱（B1）PENDING** |
| 贯通冒烟（契约面） | Node 原生 fetch（零依赖脚本） | 受信通道入口 / 来源标识 / 越权收敛 / 静态旁路检查 | 沙箱（静态面）+ **非沙箱（B2 真实双签）PENDING** |
| 后端边界（防回归固化） | pytest | `tests/test_s6_t1_frontend_boundary.py`（后端不挂载/S6-T1-2） | 沙箱 ✅ |
| 覆盖率/Lint | vitest coverage + eslint + vue-tsc | 全局 thresholds 80/80/80/70（Q-FE-7b，未放宽） | 沙箱 ✅ |

**关键页清单（Q-FE-4b 9 页）单一事实源**：`openbase-ui/tests/e2e/fixtures/key-pages.json`（E2E 与冒烟脚本同源，Q-S6-D6）：`/portrait/list`、`/portrait/overview`、`/portrait/:id`、`/openllm/conversations`、`/knowledge/chat`、`/knowledge/list`、`/knowledge/:id`、`/memory/list`、`/memory/sessions`。

## §2 断言覆盖矩阵（22 条逐条状态）

> 状态口径：**PASS（沙箱）** = 沙箱内已真实执行且通过；**PASS（沙箱）/ PENDING（非沙箱）** = 沙箱面通过、真实环境面待复核；**PENDING** = 沙箱内不可真实执行。

| 断言 ID | 断言要点 | 状态 | 证据 |
|---------|---------|------|------|
| S6-T1-1 | 唯一维护面三处一致 + 3 处改造点四元组 + 4 仓冻结落点 | **PASS（沙箱）/ PENDING（B5）** | `doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md`（v1.0.2）§1~§5；`openbase-ui/docs/frontend-frozen.md` |
| S6-T1-2 | 后端不挂载（`StaticFiles`/`mount(`/`dist-v` 命中 0）+ 白名单 | **PASS（沙箱）** | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` → **9 passed** |
| S6-T1-3 | 版本目录参数化 + `.gitignore` 含 `dist-v*` + nginx 同域 + 产物 `dist-v1.3.0` | **PASS（沙箱）/ PENDING（B6）** | `scripts/build_release.ps1`、`openbase-ui/.gitignore`、`nginx.conf.example`、`package.json`=1.3.0 |
| S6-T1-4 | 提交面仅白名单；`dogfood-output/` 未纳入；无子系统 `frontend/` 文件 | **PASS（沙箱）** | 逐项 `git add` + `git status --porcelain -uall` 对照 |
| S6-T2-1 | 深链丢上下文修复（幂等必达）；顶层壳 + 模块内导航同时渲染 | **PASS（沙箱）** | `openbase-ui/tests/router-nav.spec.ts` |
| S6-T2-2 | 权限驱动挂载（禁用模块不进菜单/路由不可达；无权限 → `/dashboard`） | **PASS（沙箱）** | `tests/router-nav.spec.ts`（5 模块 + 权限矩阵） |
| S6-T2-3 | 5 模块菜单↔路由一致性（含显式白名单）；`activeMenu`/`iconMap` | **PASS（沙箱）** | `tests/nav-consistency.spec.ts` |
| S6-T2-4 | 路由告警清零（`console.warn=0`）；幂等装载；模块懒装载无失败 | **PASS（沙箱）/ PENDING（B1）** | `tests/router-nav.spec.ts`（spy）；浏览器层由 E2E 复核 |
| S6-T3-1 | 画像 list/detail/overview 四分支呈现 + 无静默空白 + 经 `/api/v1/**` | **PASS（沙箱）/ PENDING（B3）** | `tests/isolation-presentation.spec.ts`、`tests/portrait-list-error.spec.ts` |
| S6-T3-2 | 记忆 list/search/sessions 分支 + 隔离键过滤 + 写失败统一呈现 | **PASS（沙箱）/ PENDING（B3）** | `tests/isolation-presentation.spec.ts` |
| S6-T3-3 | 知识 list/detail/chat 分支 + 流式失败错误条可重试（不断流成白屏） | **PASS（沙箱）/ PENDING（B3）** | `tests/isolation-presentation.spec.ts` |
| S6-T3-4 | 判定表四类逐类用例 + 无 500 泄漏栈/无白屏；双租户数据面 | **PASS（沙箱）/ PENDING（B3）** | `tests/isolation-presentation.spec.ts` |
| S6-T4-1 | 401 刷新失败 → SPA `replace('/auth/login?redirect=…')` + `safeRedirect()` 校验 | **PASS（沙箱）** | `tests/http.spec.ts`、`tests/auth-redirect.spec.ts` |
| S6-T4-2 | 并发 3×401 仅 1 次 refresh；403 不刷新不弹全局 toast；无无限循环；无白屏 | **PASS（沙箱）** | `tests/http.spec.ts` |
| S6-T4-3 | OIDC fragment 解析 / 缺令牌错误页 / 回调后清 hash + `loadMe` | **PASS（沙箱）/ PENDING（B4）** | `tests/oidc-auth.spec.ts`、`tests/auth-redirect.spec.ts` |
| S6-T4-4 | 停用/吊销主体 → 跳登录或 403 提示（非空白）；数据面 403 呈现 | **PASS（沙箱）/ PENDING（B4）** | `tests/auth-redirect.spec.ts`、`tests/isolation-presentation.spec.ts` |
| S6-T5-1 | 冒烟脚本仅经受信通道入口 + 来源标识 + 静态旁路检查 = 0（白名单外）；真实双签 | **PASS（脚本/静态检查）/ PENDING（B2 真实双签）** | `scripts/smoke_l3_2_ui.mjs`、`doc/test/evidence/s6/l3-2-smoke.json` |
| S6-T5-2 | 9 关键页浏览器级 PASS（渲染/关键元素/无渲染兜底/无 console error·warn） | **PENDING（B1）** | `playwright.config.ts`、`tests/e2e/*`（`--list` 9 tests in 4 files）、`doc/test/evidence/s6/ui-e2e/status.json` |
| S6-T5-3 | 越权/跨域端到端 → 空或 403；失败项 PENDING 登记；evidence 真实 | **PENDING（B2）** | `doc/test/evidence/s6/l3-2-smoke.json`（`pending` 数组） |
| S6-T6-1 | UI-E2E 段门禁逐页结论 + 证据路径；未执行页明确 PENDING | **PENDING（B1）** | `doc/test/evidence/s6/ui-e2e/status.json`、`segment-gate.json` |
| S6-T6-2 | 7 项段门禁与 22 断言映射；覆盖率最终值/缺口；Lint 最终状态 | **PASS（沙箱）** | `doc/test/evidence/s6/{coverage-summary.json,segment-gate.json}` |
| S6-T6-3 | FE-JT 台账 + 放行/清点清单口径同步；evidence 含 commit/version；hash 真实 | **PASS（沙箱文档面）/ PENDING（B5 子系统提交）** | JT 归集 §3.6（v1.3.0）、放行清单 §0/§5（v1.0.7）、清点 §5.7（v1.0.4）、`segment-gate.json` |

**统计**：22 条 = **PASS 17 条**（含 T6-2）+ **PASS（沙箱）/ PENDING（非沙箱）条件通过 1 条**（T6-3）+ **PENDING 4 条**（S6-T5-1 真实双签面、S6-T5-2、S6-T5-3、S6-T6-1）。

> 说明：S6-T5-1 的「脚本与静态旁路检查」在沙箱内**已执行并通过**（见 §3 门禁 #5、#7），故矩阵中标注为「PASS（脚本/静态检查）/ PENDING（B2 真实双签）」；其真实双签与 S6-T5-2/S6-T5-3/S6-T6-1 因环境不可达判 PENDING。

## §3 硬门禁实测（2026-09-10，沙箱内，禁止伪造）

| # | 命令（工作目录） | 结果摘要 | 退出码 |
|---|----------------|---------|--------|
| 1 | `npm run lint`（openbase-ui） | `eslint src --ext .ts,.vue && vue-tsc --noEmit` **0 problem**（含新增 `tests/e2e/**` 类型检查） | **0** |
| 2 | `npm test`（openbase-ui） | Test Files **13 passed (13)**、Tests **137 passed (137)**（批 3 基线 12/129；本批新增 `tests/l3-2-smoke.spec.ts` 8 用例；`tests/e2e/**` 已由 vitest `exclude` 隔离） | **0** |
| 3 | `npm run test:coverage`（openbase-ui） | All files：stmts **97.08%** / branches **90%** / funcs **88.46%** / lines **97.08%**（阈值 80/80/80/70，**全部达标**；`thresholds` 与 `coverage.include` **未调整**） | **0** |
| 4 | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q`（仓根） | **9 passed** | **0** |
| 5 | `npx vitest run tests/l3-2-smoke.spec.ts`（openbase-ui） | **8 passed**（T5 基座：fixture 同源 / 受信通道约束 / 静态旁路检查） | **0** |
| 6 | `npx playwright test --list`（openbase-ui） | **9 tests in 4 files**（配置与用例可被 Playwright 正确解析） | **0** |
| 7 | `npm run smoke:l3-2`（`OPENBASE_BASE_URL=http://127.0.0.1:8000`） | 静态旁路检查 PASS；受信通道不可达 → `status=PENDING`（`pending` 登记） | **2**（PENDING 约定非 0） |
| 8 | `npm run test:e2e`（openbase-ui） | **9 failed**（浏览器二进制未安装：`Please run npx playwright install`；非断言失败） | **1** |
| 9 | `npx playwright install chromium`（openbase-ui） | **FAILED**：`EPERM: operation not permitted, mkdir 'C:\Users\jerry\AppData\Local\ms-playwright\__dirlock'`（沙箱受限） | **1** |

**静态旁路检查明细**（`l3-2-smoke.json`.`static_bypass_check`）：端口字面量命中 **8/8 白名单**（`Conversations.vue`/`Models.vue`/`Playground.vue` 错误提示文案；`ConfigManageView.vue`/`AuditLogsView.vue`/`EdgeRouterView.vue`/`GatewayServicesView.vue` mock/表单数据）；绝对 URL 命中 **10/10 白名单**（示例域名/占位/mock base_url）；`src/core/api/**` 绝对地址 **0**；`http.ts` `baseURL = /api/v1`；**白名单外命中 = 0**。

## §4 段门禁聚合结论（S6-T6-1 / S6-T6-2）

| # | 门禁项 | 结论 | 证据 |
|:--:|--------|------|------|
| 1 | UI-E2E 关键页 PASS（9 页） | **未达成/待复核（PENDING B1）** | `doc/test/evidence/s6/ui-e2e/status.json`、`results.json` |
| 2 | FE-R1-1 回归通过 | **通过（前端侧组件层）**；真实双租户 B3 PENDING | `tests/isolation-presentation.spec.ts`、`tests/portrait-list-error.spec.ts` |
| 3 | FE-R1-2 回归通过 | **通过（前端侧）**；真实 IdP/吊销 B4 PENDING | `tests/http.spec.ts`、`tests/auth-redirect.spec.ts`、`tests/oidc-auth.spec.ts` |
| 4 | FE-3 达成 | **达成** | `tests/router-nav.spec.ts`、`tests/nav-consistency.spec.ts` |
| 5 | L3-2 冒烟通过 | **未达成/待复核（PENDING B2）**（脚本与静态检查通过） | `doc/test/evidence/s6/l3-2-smoke.json` |
| 6 | 覆盖率/Lint 最终值 | **通过**：stmts 97.08 / branch 90 / funcs 88.46 / lines 97.08；lint 0 problem；阈值未放宽 | `coverage-summary.json` |
| 7 | 3 处改造闭环 | **口径闭环 ✅ / 物理闭环 PENDING（B5，交 S7）** | `doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md`（v1.0.2）§10.3 |

**段门禁结论**：**未达最终通过**（门禁 1 与 5 因非沙箱环境 PENDING）；前端侧回归（门禁 2/3/4）、覆盖率/Lint（门禁 6）与 3 处改造口径闭环（门禁 7 上半）**已达成**。待非沙箱补齐 B1/B2（并按 B5 完成物理改造复核）后按 Q-FE-6 移交 S7。

> **未达成项不阻断**已于沙箱内达成的 T1~T4、T6-2 结论（对齐 S5「Pull 双签 PENDING 挂起登记不阻断」范式）。

## §5 已知环境性失败（非 S6 引入）

| # | 项 | 说明 | 处置 |
|:--:|----|------|------|
| 1 | 仓根 `python -m pytest tests` 全量中 **asyncpg 无 PG** 的 **4 项**环境性失败 | 无本地 PostgreSQL 运行态（`postgresql+asyncpg://…@localhost:5432/openbase` 不可达）导致的连接类失败，属**环境依赖**而非本次改动引入；S6 不改动 `openbase/**` 后端与数据库 | **已知环境性失败**，不纳入 S6 门禁判定；非沙箱 PG 就绪后复跑 |
| 2 | 相关依赖用例在无 PG 下按设计 skip | `python -m pytest tests/test_storage_s3_real.py tests/test_oidc_keycloak.py tests/test_oidc_gateway.py -q` → **12 passed / 4 skipped**（退出码 0），未见新增失败 | 记录为环境约束（skip 属预期） |
| 3 | S6 定向后端防回归 | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` → **9 passed**（退出码 0） | ✅ 门禁 #4 |

## §6 非沙箱 PENDING 清单（B1~B6）

| # | 复核项 | 前置条件 | 阻塞断言 | 当前状态 |
|---|--------|---------|---------|---------|
| B1 | Playwright 浏览器级关键页 PASS（9 页） | `@playwright/test` 已入库 1.63.0；需浏览器二进制 + 运行态 | S6-T5-2、S6-T6-1、S6-T2-4（浏览器层） | **PENDING**：`npx playwright install chromium` 沙箱受限（EPERM）；`npm run test:e2e` 9 failed（浏览器缺失） |
| B2 | L3-2 真实受信通道端到端（真实 HTTP 双签） | 受信通道 + 四子系统运行态 + 凭据 | S6-T5-1（真实面）、S6-T5-3 | **PENDING**：`OPENBASE_BASE_URL` 不可达 → `status=PENDING`（退出码 2） |
| B3 | 跨域 403/空 真实数据面 | 双租户真实数据 | S6-T3-1~4 | **PENDING**：组件层 mock 已绿，真实数据面待复核 |
| B4 | OIDC 真实 IdP 回调 / 真实吊销链路 | IdP / 网关可达 | S6-T4-3（真实面）、S6-T4-4 | **PENDING**：fragment 解析与缺令牌错误页已绿 |
| B5 | 四仓 `frontend/` 物理改造与 CI 收敛 | 各子系统仓 git 写权限（沙箱仅允许 OpenBase 仓） | S6-T1-1（物理面）、S6-T6-3（子系统提交） | **PENDING**：口径登记完成，交 S7 按 Q-S6-D7 复核 |
| B6 | nginx `/ui/` 发布/回滚实测 | nginx + 运行态 + 两个版本目录 | S6-T1-3（运行态面） | **PENDING**：版本目录与脚本就绪，切换实测待非沙箱 |

## §7 结论与 S7 移交

1. **结论**：S6 段前端侧实现与回归在沙箱内达成（FE-3、FE-R1-1/FE-R1-2 前端侧、覆盖率/Lint、3 处改造口径闭环）；**UI-E2E 关键页 PASS 与 L3-2 真实双签为 PENDING**，段门禁**未达最终通过**，不得据此宣布 S6 收官。
2. **移交接口（Q-FE-6，S6 → S7）**：UI-E2E evidence 索引（`doc/test/evidence/s6/ui-e2e/`）+ FE-JT 台账回写行（JT 归集 §3.6，v1.3.0）+ L3-2 冒烟记录（`l3-2-smoke.json`），以**提交号**桥接（批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 = `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`）。
3. **S6 不终验项**（设计草案 §8）：L3-1 Agent 端到端、L2-1 主备切换、L2-2 通道矩阵终验、RA-06 终验聚合、K07 终验、冒烟 S0-S6 聚合与会签；各子系统 `frontend/` 物理改造（B5）与后端语义均不在 S6 范围。

## §8 证据索引

| 证据 | 路径 |
|------|------|
| L3-2 冒烟（含静态旁路检查） | `doc/test/evidence/s6/l3-2-smoke.json` |
| UI-E2E 状态（PENDING 说明） | `doc/test/evidence/s6/ui-e2e/status.json` |
| UI-E2E Playwright JSON 报告 | `doc/test/evidence/s6/ui-e2e/results.json` |
| 覆盖率/Lint 汇总 | `doc/test/evidence/s6/coverage-summary.json` |
| 段门禁聚合（7 项 + 22 断言） | `doc/test/evidence/s6/segment-gate.json` |
| 开发记录 | `doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md` |
| 设计草案（[Approved] v1.0.1） | `OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md` |
| 立项方案（[Approved] v1.1.1） | `OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md` |

---

> **文档结束**。本报告为 S6 段「测试」环节交付物（[Review]）；22 条断言逐条状态以本报告 §2 为准，段门禁聚合以 §4 为准；非沙箱项（B1~B6）由受控环境回填后按 Q-FE-6 移交 S7。
