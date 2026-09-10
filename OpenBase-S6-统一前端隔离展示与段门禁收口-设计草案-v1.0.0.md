# OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S6-DESIGN-v1.0.0 |
| 版本 | v1.0.1 |
| 状态 | **[Approved]**（2026-09-10 设计评审人工批准进入开发 T1~T6；Q-FE-1~8 已于 2026-09-10 立项评审定案并登记 §1.1，本设计不再重议） |
| 日期 | 2026-09-10 |
| 作者 | AD（跨项目分析）+ AI（openbase-ui 侧设计起草与沙箱实测） |
| 版本主题 | **S6 段（前端段，FE-JT 收官）设计草案**：在唯一维护面 `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui` 内落地 **T1 边界收口** → **T2 FE-3 模块导航壳** → **T3/T4 FE-R1-1/FE-R1-2 回归** → **T5 L3-2 贯通冒烟** → **T6 段门禁与台账收口**；本文给出逐任务设计说明、文件落点、22 条设计断言（S6-T1-1~S6-T6-3）与验收锚点、契约与呈现规范、迁移兼容、风险、边界、里程碑与遗留登记 |
| 适用范围 | OpenBase 仓（唯一代码改造面 = 仓内 `openbase-ui/`；文档面 = 仓根与 `doc/**`）；对 DPS/OpenLLM/OpenMemory/OpenRAG 四仓的 `frontend/` 与 CI/部署配置**仅只读盘点与口径登记**，S6 内不改动其仓文件（Q-FE-1） |
| 上游依据（需求基线） | ①《OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md》（内部 v1.1.0，[Approved]，2026-09-10 立项评审批准，22 条验收断言 + Q-FE-1~8）；②分阶段版本规划 v1.3.1（S6 段：统一前端壳 + FE-3 + FE-R1-1/2 + L3-2）；③JT 归集 v1.2.0 §3.6 FE-JT（FE-1/FE-2 基线、FE-R1-1、FE-R1-2、FE-3）；④清点总清单 v1.0.2 §1.4（统一前端口径）；⑤放行清单 v1.0.5 §0 通用红线第 5 条；⑥U1 设计草案 v1.0.0（§5 吊销即时性、§6 签发闭环/OIDC 回调、§10 接口清单）；⑦统一身份最小特征集与隔离模型设计 v1.3.0（§4.2 隔离键、§12.1 跨域 403/404、§12.2 吊销即时性）；⑧P2-1 设计草案 v1.0.0（§9.3 OB-10 外移、§11.1 落点台账、§3 协议头规范）；⑨真实联调冒烟清单 v1.1.0（S5 主链路端到端、S6 旁路与双链路一致性） |
| 实测基线（2026-09-10） | OpenBase 仓 HEAD `be7a8aaa2e113527db71ec5e47d0297a9fbf4af2`（`docs(intg): S6 统一前端段立项方案 v1.0.0`）；工作树仅 `dogfood-output/` 噪音（不提交）；`git ls-files openbase-ui` = **107**、`openbase-ui/src` = **90**；node **v22.16.0** / npm **10.9.4**；`openbase-ui/node_modules` 已存在（离线可跑 vitest，见 §1.4） |
| 设计原则 | ①需求可追溯（22 断言 → 设计条目 1:1）；②只做前端呈现与收口，不新增旁路、不改子系统语义；③可回滚（版本目录承载）；④证据可核（沙箱可执行面 / 非沙箱复核面分离，**禁止伪造 hash 与通过**） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-10 | AD + AI（openbase-ui 侧设计起草与沙箱实测） | 初始版本：S6 段设计草案。内容含 §1 设计输入与 Q-FE-1~8 定案登记（含 4 条设计级补充定案 Q-FE-2b/3b/4b/7b）、需求覆盖矩阵（22 断言 1:1）、运行环境核实与「沙箱可执行面 vs 非沙箱复核面」清单；§2 总体改造与 5 项关键机制（模块路由装载幂等化、导航一致性、统一错误呈现、E2E 证据链、发布形态参数化）；§3 现状代码落点（行号 2026-09-10 复核，含与立项方案的行号/行数差异与新发现缺口）；§4 逐任务设计（T1~T6，设计说明/文件落点/设计断言/验收锚点）+ 22 条断言汇总表；§5 契约与呈现规范（ErrorResponse→UI 映射、403/404 空态、无白屏兜底、SSE/网关错误面）；§6 迁移与兼容；§7 风险；§8 边界（S7 项不终验）；§9 里程碑；§10 遗留与定案登记；附录 A~D（引用清单、沙箱实测记录、断言-落点索引、3 处改造点行号复核） |
| v1.0.1 | 2026-09-10 | 项目负责人（设计评审批准）/ AI（批准注记回写） | **设计评审人工批准**：状态 **[Draft] → [Approved]**，注记「**2026-09-10 设计评审人工批准进入开发 T1~T6**」（批准口径：评审人 = 项目负责人经 AI 开发会话人工确认）；开发四批提交入库（批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 = `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`），段门禁结论见 `doc/test/evidence/s6/segment-gate.json`。**22 条断言口径与 §1~§10 设计内容不变**（仅状态与批准注记回写） |

---

## 1. 设计输入与 Q 定案登记

### 1.1 Q-FE-1~8 定案登记（2026-09-10 立项评审批准，设计不再重议）

> 批准口径：**2026-09-10 S6 段立项评审人工批准：评审人 = 项目负责人经 AI 开发会话人工确认；Q-FE-1~8 一次性定案；本表为唯一事实源，后续设计/开发/测试/收口引用本表，不得跨步反复。**

| # | 事项 | 定案结论 | 设计落点 | 状态 |
|---|------|---------|---------|------|
| **Q-FE-1** | 子系统前端冻结处置口径（含 3 处改造点归属） | **保留目录不删除 + 不再构建/发布 + 后端不再挂载产物**；3 处改造点（附录 D）归属对应子系统仓后续批次执行，**S6 仅产出收口口径与登记**，不将任何 `frontend/` 改动纳入联调提交批（归 B/C 类）。3 处处置口径细化：**改造点 1（OpenMemory nginx）**：定案「**下线 SPA 承载**」——子系统仓后续批次移除 `deploy/nginx/conf.d/openmemory.conf:90`（`root /app/frontend/dist;`）与 `:93`（`location / { try_files … /index.html; }`），站点仅保留 `/api/` 反代、`/health` 与 301 → 统一前端 `/ui/`；**改造点 2（OpenLLM 编排）**：移除 `docker-compose.yml:141-172` 的 `frontend` 服务与 `docker-compose.prod.yml:19` 的 `./frontend/dist:/usr/share/nginx/html:ro` 挂载；**改造点 3（CI 构建链）**：DPS `.github/workflows/ci.yml` 前端四段与 OpenRAG `.github/workflows/frontend-ci.yml` 收敛为「冻结校验/跳过」，收敛动作在对应仓执行 | §4 T1；附录 D；放行清单 §0-5；清点总清单 §1.4 | ✅ 已定案 |
| **Q-FE-2** | 统一前端承载版本与发布形态 | `dist-vX.Y.Z` 版本目录承载 + nginx 同域 `/ui/` 静态 + `/api/` 反代 + SSE `proxy_buffering off`；**统一前端产品版本线与 OpenBase 仓版本线解耦**，与 JT 线以提交号桥接。**设计级补充定案 Q-FE-2b**：S6 承载版本号定为 **v1.3.0**（`openbase-ui/package.json:3` 由 1.2.0 → 1.3.0，在 T6 前完成）；`scripts/build_release.ps1:5` 版本目录参数化（由 `package.json.version` 派生 `dist-v$Version`，消除 `dist-v1.2.0` 硬编码）；`openbase-ui/.gitignore` 增补 `dist-v*`（当前仅忽略 `dist`，实测 `dist-v*` 未忽略 → 版本目录存在误入提交面风险） | §2.6；§4 T6；§6.1 | ✅ 已定案 |
| **Q-FE-3** | FE-R1-1/2 与 RA-06 配合门禁点与跨域呈现规范 | 配合点 = **R1 收官门禁**（FE-R1-1/FE-R1-2 为 RA-06 的前端侧验收面）；跨域呈现统一为**为空 / 403 提示（无 500、无白屏）**；401 → 静默刷新（仅一次）失败则 `clear()` + 跳 `/auth/login`；403 → 页面级提示、不触发刷新风暴。**设计级细分判据 Q-FE-3b（空 vs 403 判定表）**：①HTTP 200 且 `items=[]`/`total=0`（他域数据不可见）→ **空态**（有明确空态文案，不得渲染为错误栈）；②HTTP 403 或 `body.code` 前缀 `PERM_`/`AUTH_`（定向越权）→ **403 页面级提示**；③HTTP 404 → 「资源不存在」空态；④HTTP 5xx → 可观测错误条 + 重试（沿用 `tests/portrait-list-error.spec.ts` 范式） | §5.1/§5.2；§4 T3/T4 | ✅ 已定案 |
| **Q-FE-4** | UI-E2E 工具与范围 | **分层**：① 组件/单元回归沿用 **vitest**（现有 7 spec / 44 用例，沙箱实测全绿，保持覆盖率门禁）；② 关键页 PASS 由**浏览器级 E2E 承载，定案引入 `@playwright/test`** 为 S6 E2E 引擎（devDependency，T2 前置）。**设计级补充定案 Q-FE-4b（关键页清单与脚本落点）**：关键页下限 = **画像**（`/portrait/list`、`/portrait/overview`、`/portrait/:id`）、**对话**（`/openllm/conversations`、`/knowledge/chat`）、**知识**（`/knowledge/list`、`/knowledge/:id`）、**记忆**（`/memory/list`、`/memory/sessions`）共 9 页；用例落点 `openbase-ui/tests/e2e/*.spec.ts` + `openbase-ui/playwright.config.ts`；evidence 落点 `doc/test/evidence/s6/ui-e2e/`；**OpenLLM 全模块 PASS 为增强项**（不阻塞 S6 段门禁） | §4 T2/T5；§5.4 | ✅ 已定案 |
| **Q-FE-5** | L3-2 前端侧门禁口径 | L3-2 = **经 OpenBase 受信通道（gateway/proxy，来源标识符合协议头规范如 `X-Proxy-Source`）端到端**：统一前端 → OpenBase gateway → 子系统（画像/记忆/知识/对话）；**关键页 PASS** 为通过标准；跨域/越权 → 空或 403；**不新增旁路直连**（不得由前端直连子系统端口）。**要求真实 HTTP 双签**；不可达时按 S5 范式登记 **PENDING 挂起不阻断**，但 S6-T5 段门禁判定为「**未达成/待复核**」，不得以组件层断言替代 | §4 T5；§5.3 | ✅ 已定案 |
| **Q-FE-6** | 与 S7 边界 | **S7 承接**：L3-1 Agent 端到端、L2-1 主备切换演练、L2-2 通道覆盖矩阵终验、RA-06 终验聚合、K07 终验、冒烟 S0-S6 聚合与会签；**S6 只产出前端侧回归与冒烟证据、不终验**；S6→S7 移交接口 = UI-E2E evidence 索引 + FE-JT 台账回写行 + L3-2 冒烟记录，以**提交号**桥接 | §8；§9 | ✅ 已定案 |
| **Q-FE-7** | 前端覆盖率门禁口径 | **保持 `vite.config.ts:48-53` 全局 thresholds 80/80/80/70 不变**（全局口径），同时对 **S6 新增/改动代码行要求 ≥90%**（增量口径，对齐 AGENTS.md §7）。**设计级补充定案 Q-FE-7b（覆盖率范围与前置缺口）**：①`coverage.include` 维持 `src/core/stores|router|api`（`vite.config.ts:47`），**不扩大 include**（避免门禁口径漂移），模块页覆盖由 Playwright 关键页 PASS 承载；②登记**门禁前置缺口**：2026-09-10 沙箱实测 `npm run test:coverage` 退出码 1（All files：stmts 51.52% / lines 51.52% / funcs 50.66% / branches 85.84%，低于 80/80/80/70）→ T3/T4 补测后须使全局达标，否则 T6 段门禁**如实登记为未达成** | §1.4；§4 T3/T4/T6；§7 R-2 | ✅ 已定案 |
| **Q-FE-8** | 承载版本与 JT 版本的双向标注 | **不新建独立 JT 版本线**；沿用 JT 归集 §3.6 行口径（**v1.0.0 (R1)** = FE-R1-1/FE-R1-2；**v1.3.0 (R4)** = FE-3）；统一前端产品版本（v1.3.0，Q-FE-2b）与 JT 行以**提交号**桥接（双向标注：JT 行注明 OpenBase 提交号；OpenBase 文档注明 JT 行） | §4 T6；§9 | ✅ 已定案 |

> **定案计数**：Q-FE-1~8 共 8 项全部 ✅ 已定案（其中 Q-FE-2b/3b/4b/7b 为设计阶段细化的 4 条补充定案，均属原定案内的口径落地，不构成新议题）。

### 1.2 设计输入（上游语义依据 → 设计承接）

| 输入源 | 关键语义 | 本设计承接处 |
|--------|---------|-------------|
| U1 设计草案 v1.0.0 §5/§6/§10 | token 吊销即时性；login/refresh/OIDC 签发闭环；deactivated 主体任何入口 401/403 | §4 T4（S6-T4-1~4）；§5.1（401/403 映射） |
| 身份最小特征集与隔离模型设计 v1.3.0 §4.2/§12.1/§12.2 | 隔离键 `tenant_code`；入口同构与跨域 403/404 呈现语义；吊销即时性验收要点 | §4 T3（S6-T3-4）；§5.2（空态/403/404 呈现表） |
| P2-1 设计草案 v1.0.0 §3/§9.3/§11.1 | 协议头规范（`X-Proxy-Source` 等）；OB-10 前端壳外移 S6；落点台账登记范式 | §4 T1（受信通道口径）；§4 T5（来源标识断言）；§10（登记范式） |
| 真实联调冒烟清单 v1.1.0 §3.5/§3.6 | S5 主链路端到端（OpenBase 入口）；S6 旁路与双链路一致性 | §4 T5（L3-2 冒烟用例矩阵） |
| 规划 v1.3.1 §2/§3 S6 行 | S6 = FE-3 + FE-R1-1/2 + L3-2 贯通冒烟；UI-E2E 门禁在统一前端执行 | §1.3（覆盖矩阵）；§4 全任务 |
| JT 归集 v1.2.0 §3.6 | FE-R1-1/FE-R1-2（v1.0.0 R1）、FE-3（v1.3.0 R4） | §4 T6（台账回写） |
| 清点总清单 v1.0.2 §1.4 / 放行清单 v1.0.5 §0-5 | 统一前端唯一维护面；`frontend/` 冻结不进提交面 | §4 T1（边界收口）；§6.2 |

### 1.3 需求覆盖矩阵（立项 22 条验收断言 → 设计条目 1:1）

| 断言 ID | 设计条目（本文） | 实现落点 | 证据形式 | 沙箱可执行 |
|---------|-----------------|---------|---------|-----------|
| S6-T1-1 | §4.1 设计说明 1~3 + §5.1 | 本设计 §附录 D；放行清单 §0-5；清点 §1.4 | 口径核对表（文档） | ✅ |
| S6-T1-2 | §4.1 设计说明 4（后端不挂载确认） | OpenBase 仓 `openbase/**`（grep 实证）；四仓后端只读 | grep/StaticFiles 扫描记录 | ✅（只读） |
| S6-T1-3 | §4.1 设计说明 5 + §2.6 | `scripts/build_release.ps1`（参数化）、`nginx.conf.example`、`.gitignore` | 脚本/配置 diff + 版本目录实测 | ✅（构建可跑；发布切换需运行态） |
| S6-T1-4 | §4.1 设计说明 6 | 放行清单 §0-5；清点 §1.4 | 提交面核对（git status 白名单） | ✅ |
| S6-T2-1 | §4.2 设计说明 1~2（缺陷根因与修复） | `router/index.ts:45-65,76-94`、`ModuleLayout.vue:31` | vitest 回归 + 路由告警侦测 | ✅ |
| S6-T2-2 | §4.2 设计说明 3（权限驱动挂载） | `moduleRegistry.ts:21-29`、`router/index.ts:86-92` | vitest（mock `/modules` + permissions） | ✅ |
| S6-T2-3 | §4.2 设计说明 4（导航一致性） | `AppLayout.vue:55-68`、5 模块 `index.ts` | 一致性断言（菜单↔routes↔权限矩阵） | ✅ |
| S6-T2-4 | §4.2 设计说明 5（告警清零） | `router/index.ts:52-53` 既有修复 + 全量复验 | console warn 侦测（vitest spy / E2E） | 部分（无浏览器层需 E2E 复核） |
| S6-T3-1 | §4.3 设计说明 1 | `modules/portrait/pages/*`、`core/api/dps.ts` | vitest 组件回归 + E2E 关键页 | 部分 |
| S6-T3-2 | §4.3 设计说明 2 | `modules/memory/pages/*` | 同上 | 部分 |
| S6-T3-3 | §4.3 设计说明 3 | `modules/knowledge/pages/*`、`core/api/rag.ts` | 同上 | 部分 |
| S6-T3-4 | §5.2 呈现规范（Q-FE-3b 判定表） | 各关键页空态组件 + `http.ts` | 空/403 用例（双租户需真实数据） | 部分（需真实双租户） |
| S6-T4-1 | §4.4 设计说明 1 | `http.ts:71-84`、`router/index.ts:67-73` | vitest（axios mock + router） | ✅ |
| S6-T4-2 | §4.4 设计说明 2 + §5.3 | `http.ts:55-90` | vitest（403/连续 401） | ✅ |
| S6-T4-3 | §4.4 设计说明 3 | `pages/OidcCallback.vue:30-42`、`api/auth.ts:25-31` | vitest（fragment 解析/缺令牌） | ✅ |
| S6-T4-4 | §4.4 设计说明 4 | `http.ts`、`stores/auth.ts:19-31` | vitest + 真实吊销（IdP/网关） | 部分（真实吊销需运行态） |
| S6-T5-1 | §4.5 设计说明 1 | `openbase-ui/scripts/smoke_l3_2_ui.mjs`（新增） | 冒烟 JSON/日志（真实双签） | ❌ 非沙箱 |
| S6-T5-2 | §4.5 设计说明 2 | Playwright 关键页用例 | E2E report + 截图 | ❌ 非沙箱 |
| S6-T5-3 | §4.5 设计说明 3 | 冒烟脚本 + evidence JSON | 失败项 PENDING 登记 | ❌ 非沙箱 |
| S6-T6-1 | §4.6 设计说明 1 | UI-E2E 门禁聚合表 | 门禁自检表 | 部分（聚合可写、执行非沙箱） |
| S6-T6-2 | §4.6 设计说明 2 | 段门禁 6 项映射 | 门禁自检表 | 部分 |
| S6-T6-3 | §4.6 设计说明 3 + §2.6 | JT §3.6、放行 §0-5/§5、清点 §1.4/§5.5、`doc/test/**` | 台账回写 + 提交号回填（**禁伪造**） | ✅（文档回写）/ ❌（子系统提交） |

**覆盖结论**：22 条验收断言 **1:1 全覆盖**（无游离断言、无新增断言，计数与立项 §4 一致，规避立项 R-7 口径风险）。

### 1.4 运行环境核实结论与「沙箱可执行面 vs 非沙箱复核面」

| 核实项 | 命令/方式 | 实测结论 |
|--------|----------|---------|
| Node 版本 | `node -v` | **v22.16.0** ✅ |
| npm 版本 | `npm -v` | **10.9.4** ✅ |
| `node_modules` 是否已装 | `Test-Path openbase-ui/node_modules`、`node_modules\.bin\vitest.cmd` | **均存在（True）** ✅ → 离线可跑 |
| 锁文件 | `openbase-ui/package-lock.json` | 存在（已入库跟踪） ✅ |
| vitest 是否在 devDependencies | `package.json:24-39` | **vitest ^2.1.8 + @vitest/coverage-v8 ^2.1.8 + @vue/test-utils + jsdom** ✅ |
| Playwright 是否在 devDependencies | `package.json:24-39` | **不在**（无 `@playwright/test`；仅 DPS/OpenRAG 子系统 CI 使用 Playwright）→ Q-FE-4 引入需新增依赖 |
| `npm test` 可否在沙箱跑 | `npm test`（= `vitest run`） | **可跑且全绿**：Test Files **7 passed (7)**、Tests **44 passed (44)**、Duration 38.15s（含 jsdom `Not implemented: navigation` 与 `AggregateError` 的 stderr 噪音，**不影响退出码 0**） |
| `npm run test:coverage` 可否在沙箱跑 | `npm run test:coverage` | **可跑，但门禁不通过（退出码 1）**：All files stmts **51.52%** / lines **51.52%** / funcs **50.66%** / branches **85.84%**，thresholds 80/80/80/70（Q-FE-7b 登记为前置缺口） |
| `npm run lint` 可否在沙箱跑 | `npm run lint` | **可跑，但当前失败（退出码 1）**：`✖ 9 problems (1 error, 8 warnings)`；error = `src/modules/portrait/pages/PortraitDetail.vue:40:18 vue/no-use-v-if-with-v-for` → `build_release.ps1` 的「Lint 0」门禁当前不绿 |
| `npm run build` 可否在沙箱跑 | 依赖齐备 + vite/vue-tsc 在 devDependencies | **可跑（离线）**；产物 `dist/`（Q-FE-2b 版本目录 `dist-vX.Y.Z` 由 T1/T6 参数化后生成） |
| 版本目录现状 | `Get-ChildItem openbase-ui -Directory` | 仅 `coverage / dist / node_modules / scripts / src / tests`；**无 `dist-v1.2.0`**（未执行过 release 脚本）→ 立项 §4 S6-T1-3/S6-T6-3 的「dist-vX.Y.Z」为**目标态**，须在 S6 内产出 |

**沙箱可执行面（S6 内可直接执行并作为证据，禁止伪造）**

| # | 可执行项 | 命令/方式 | 用途（断言） |
|---|---------|----------|-------------|
| A1 | 组件/单元回归 | `npm test`（openbase-ui） | S6-T2-1/2、S6-T3-1~3（组件层）、S6-T4-1~3 |
| A2 | 覆盖率采集 | `npm run test:coverage` | Q-FE-7b 门禁达标判定（S6-T6-2） |
| A3 | 静态检查 | `npm run lint`（须先修 1 error） | S6-T6-2（门禁前置） |
| A4 | 类型检查与构建 | `npm run build`（`vue-tsc --noEmit && vite build`） | S6-T1-3、S6-T6-3（产物形态） |
| A5 | 路由/导航一致性（无浏览器） | 新增 vitest 用例：`createMemoryHistory` + `router.push` 驱动 `router/index.ts`/`moduleRegistry.ts` | S6-T2-1~4（日志告警以 spy 侦测、深链匹配、权限门） |
| A6 | HTTP 契约与 401/403 分支 | 扩展 `tests/http.spec.ts`（axios mock） | S6-T4-1/2、S6-T3-4（契约映射断言） |
| A7 | 文档与台账回写 | OpenBase 仓 git 提交（沙箱许可范围） | S6-T6-3（回写 FE-JT/放行/清点口径 + 提交号） |
| A8 | 只读盘点 | grep/Read 各仓文件（不改动） | S6-T1-1~4、S6-T5-1（旁路直连检查） |

**非沙箱复核面（须由用户在沙箱外/受控环境执行；S6 内只登记 PENDING，不得伪造结果）**

| # | 复核项 | 前置条件 | 阻塞断言 | 处置 |
|---|--------|---------|---------|------|
| B1 | Playwright 浏览器级关键页 PASS（画像/对话/知识/记忆 9 页） | `@playwright/test` 安装 + 浏览器二进制 + 运行态（nginx `/ui/` + 后端 + 四子系统） | S6-T5-2、S6-T6-1 | 沙箱内产出用例与配置，**执行结果由用户复核回填**；未执行 → 登记「环境待办/挂起」 |
| B2 | L3-2 真实受信通道端到端（统一前端 → gateway → 子系统） | 四子系统运行态 + 真实 HTTP 双签 | S6-T5-1/2/3 | 冒烟脚本 `scripts/smoke_l3_2_ui.mjs` 可在沙箱内编写与干跑（mock），真实双签须沙箱外 |
| B3 | 跨域 403/空 的真实数据面复核 | 双租户真实数据（他域数据不可见/定向越权 403） | S6-T3-4 | 组件层断言（mock）在沙箱内做；真实数据面复核沙箱外 |
| B4 | OIDC 真实 IdP 回调链路 | IdP/网关可达 | S6-T4-3（真实链路部分） | fragment 解析与缺令牌错误页在沙箱内可验；真实回调沙箱外 |
| B5 | 四仓 `frontend/` 改造与 CI 收敛 | 各子系统仓 git 写权限（沙箱仅允许 OpenBase 仓） | S6-T1-1/4 | S6 内只登记口径；改造动作由用户在对应仓执行 |
| B6 | nginx `/ui/` 发布/回滚实测 | nginx + 运行态 + 两个版本目录 | S6-T1-3（运行态部分） | 版本目录与脚本在沙箱内产出；切换实测沙箱外 |

> **纪律（写入测试与收口报告口径）**：任何未在沙箱/受控环境真实执行的项目，一律标注 `PENDING（未执行）` 或 `沙箱受限`，**禁止以「预期通过」代替证据**，禁止编造 hash、截图、报告（对齐立项 R-4 与 S6-T6-3）。

---

## 2. 总体改造与关键机制

### 2.1 目标架构（单壳三层 + 单一路由装载面 + 单一权限事实源）

```
AppLayout（顶层统一壳：品牌/折叠 + 模块导航 + 用户/登出/顶栏标题）
  └─ ModuleLayout（模块内二级导航：route.meta.navItems 分组水平菜单）
        └─ 模块页面（5 模块 66 页：openllm 37 / memory 10 / portrait 10 / knowledge 7 / gateway 2）
路由装载面：router/index.ts（staticRoutes 静态 + mountModuleRoutes 动态模块装载，幂等）
权限事实源：GET /modules（后端清单）+ auth.permissions（前端过滤）→ moduleRegistry.enabledModules
数据面：http.ts（baseURL /api/v1）→ OpenBase gateway（受信通道）→ 子系统
发布面：dist-vX.Y.Z（版本目录）→ nginx 同域 /ui/ 静态 + /api/ 反代（SSE 不缓冲）
```

**设计不变式（Invariants）**
- INV-1：模块路由**只为 `enabledModules` 且权限允许的模块**装载（`moduleRegistry.ts:21-29` 过滤为唯一入口）。
- INV-2：任一模块的**菜单项集合 ⊆ 该模块 routes 可匹配集合**（菜单不得指向缺失路由）；详情/表单类路由可显式白名单排除。
- INV-3：**任何 HTTP 失败都不得导致整页空白**：401 收敛到登录页、403/404 收敛到页面级空态/提示、5xx 收敛到错误条+重试。
- INV-4：前端**只经 OpenBase 受信通道**访问子系统数据（`/api/v1/proxy/*` 或 gateway 聚合端点），不新增旁路直连。
- INV-5：发布与回滚**只切版本目录**，不涉及数据库迁移与后端语义。

### 2.2 关键机制 1：模块路由装载幂等化（T2 核心，修复「丢上下文」根因）

**现状根因（2026-09-10 实测）**
- `router/index.ts:76-84`：`mountModuleRoutes()` **只在 `!registry.initialized` 分支内调用一次**；而 `moduleRegistry.init()`（`moduleRegistry.ts:21-29`）一旦被任何先行路径（如组件内调用/后续新增初始化入口）置 `initialized = true`，守卫将**跳过装载**；
- 此时深链/刷新访问模块页 → `to.matched.length === 0` → `router/index.ts:85` 直接 `return { path: '/dashboard' }` → **模块上下文丢失**（现象即 OB-10 登记的「模块内导航覆盖 → 丢上下文」）；
- `moduleRegistry.loadRoutes`（`moduleRegistry.ts:34-41`）为**占位实现**（仅置 `loaded = true`，不装载真实路由），与实际装载逻辑（`router/index.ts:45-65`）**双轨**，是上述不一致的结构性来源。

**目标设计（改「只跑一次」为「幂等必达」）**
1. `mountModuleRoutes()` 改为**幂等**：以 `module.loaded`（`moduleRegistry.ts:9`）与新增的 `router.hasRoute(module.info.id)` 双条件判定跳过，重复调用安全；
2. 守卫改造为：`if (!registry.initialized) { await registry.init(auth.permissions) }` → **紧随其后无条件** `await mountModuleRoutes()`（不再内嵌于同一 `if` 块）；
3. `registry.loadRoutes(moduleId)` 由占位改为**委托真实装载**：内部调用 `mountModuleRoutes()`（单一实现，消除双轨），返回值语义 = 「模块路由当前已装载」；
4. 装载失败（`router/index.ts:61-63` 的 catch）保持 `console.error('[module:%s] route load failed')` + 标记 `loaded = false`（可重试），**不得**吞错后继续以空路由表运行；
5. 深链兜底保留 `L80-83` 的「重导」逻辑，并补充：若 `resolved.matched.length > 0` 且当前 `to.matched.length === 0`，一律 `replace` 重导（当前已有，扩到幂等装载后仍成立）。

### 2.3 关键机制 2：导航一致性（顶层壳 ↔ 模块内导航 ↔ 路由 ↔ 权限）

| 子机制 | 现状缺口（实测） | 设计决策 |
|--------|-----------------|---------|
| 顶层菜单高亮 | `AppLayout.vue:6` `:default-active="route.path"`，而模块菜单项 `index = m.info.route_prefix`（`:65`，如 `/portrait`），子页路径为 `/portrait/list` → **模块子页时顶层模块项不高亮** | 顶层 `el-menu` 增加 `:default-active="activeMenu"` 计算属性：精确匹配 `route.path`，否则回退到 `route.meta.module` 对应的 `route_prefix` |
| 模块图标映射 | `AppLayout.vue:55-57` `iconMap` 仅 5 个图标，且缺 `portrait`/`gateway` 等键 → 全部回退 `ChatDotRound`（图标与模块语义不符） | `iconMap` 按 `ModuleInfo.icon` 补齐（至少 `Odometer/ChatDotRound/Collection/Memo/User/OfficeBuilding/Connection`），并加「未命中回退 + 单测断言」 |
| 模块内导航来源 | `ModuleLayout.vue:31` 读 `route.meta.navItems`；Vue Router 的 `route.meta` 为 matched 链 **shallow merge（后者覆盖）**，子路由若声明同名 `navItems` 将**覆盖父级**（当前 5 模块子路由未声明，属隐性风险） | ① 保持 `navItems` **唯一来源 = 模块 `index.ts` 导出**（由 `router/index.ts:57` 注入父路由）；② 新增**构建/测试期一致性检查**：任一子路由 `meta` 出现 `navItems` 即告警（防覆盖）；③ `ModuleLayout` 增加空态兜底（`navItems` 缺失时不渲染空菜单条） |
| 菜单 ↔ 路由一致性 | portrait `reports/batch` 复用 `PortraitList.vue`、memory `:id`/`monitor` 未入菜单、openllm `apps/new`/`apps/:id`/`auth-ext` 未入菜单（**合法**，属详情/表单） | 建立**显式白名单**（不入菜单的详情/表单/重定向路由），测试断言：`菜单项 ⊆ routes` 且 `routes − 菜单 ⊆ 白名单`；5 模块全覆盖 |
| 父路由告警 | `router/index.ts:52-53` 注记「此前 `addRoute('', record)` 以空串为父名触发 `Parent route "" not found`（5 模块 × 5 条）」；当前代码已改为顶层挂载（`L54-59`，无父名） | 保留修复；新增**回归侦测**：vitest spy `console.warn` + Playwright `page.on('console')` 断言 `warn = 0` |

### 2.4 关键机制 3：统一错误呈现（无白屏）

**现状（`http.ts:55-90`）**：401 静默刷新（单飞 `refreshing`，仅一次）已具备；**403/404/5xx 一律走 `L86-88` 的统一 `ElMessage.error`**，无页面级分类、无「空态 vs 错误」区分；`L79-83` 刷新失败 `clear()` + `window.location.href = '/auth/login'`（**整页跳转、丢失 SPA 上下文与 `redirect` 回跳参数**）。

**目标设计（分层收敛 + 可被页面消费）**
1. 拦截器按 status 分类（`error.response?.status`）：
   - `401`：单飞刷新（仅一次）→ 成功重放原请求；失败 → `tokenStore.clear()` + **`router.replace({ path: '/auth/login', query: { redirect: currentFullPath } })`**（SPA 内跳转，保留回跳；避免 `window.location.href` 整页刷新丢上下文）；
   - `403`：标记 `error.bizKind = 'forbidden'`，**默认不弹全局 toast**（由页面渲染页面级提示），仅在无页面消费者时回退 `ElMessage.warning`；
   - `404`：标记 `bizKind = 'not-found'`；
   - `5xx`：标记 `bizKind = 'server-error'` + 全局 `ElMessage.error`（可观测）+ 页面可渲染错误条与重试；
   - 取消（`L62-64`）：保持透传不提示；
2. 新增**轻量错误分类工具**（`src/core/api/error.ts`）：把 `ErrorResponse{code,message,detail,request_id}` 映射为 `{ kind: 'forbidden'|'not-found'|'server-error'|'unknown', codePrefix, message, requestId }`，`codePrefix` 取 `code` 的分段前缀（`AUTH_/PERM_/PARAM_/BIZ_/SYS_/STORAGE_`）；
3. 页面级兜底：`App.vue`/`AppLayout.vue` 挂 `onErrorCaptured` + `router.onError`，渲染「页面加载失败 + 重试」空态（防渲染异常导致白屏）；
4. 401 刷新**并发/重试边界**：单飞 Promise 复用（现 `L74-76` 已有 `refreshing` 复用，补「`refreshing` 完成后必须置空（成功/失败两分支都置空）」——当前失败分支 `L80` 置空、成功分支 `L76` 置空，**但 await 异常时 `L79-83` 分支已覆盖**；补断言：并发 3 个 401 只触发 1 次刷新）。

### 2.5 关键机制 4：E2E 证据链（可核、可回填）

```
用例层：tests/e2e/{portrait,memory,knowledge,chat}.spec.ts   （Playwright，Q-FE-4b 9 页）
配置层：playwright.config.ts（baseURL = http://127.0.0.1:5173 或 http://<host>/ui/）
执行层：npm run e2e:ui（新增 script，串 smoke_l3_2_ui.mjs 前置探活）
证据层：doc/test/evidence/s6/ui-e2e/{report.html,results.json,<page>.png}
聚合层：doc/test/OpenBase-S6-…-测试报告-v1.0.0.md（逐断言结论 + 证据索引 + hash 回填位）
```
- **hash 回填位**：evidence JSON 内记录 `openbase_commit`（OpenBase 仓提交号）、`ui_version`（package.json version）、`started_at/finished_at`、`base_url`；未执行 → 明确写 `status: PENDING`、`reason`，**不写假 hash**。
- 冒烟脚本与 E2E 报告**不入 `dogfood-output/`**（该目录为噪音、不提交）；证据统一落 `doc/test/evidence/s6/`。

### 2.6 关键机制 5：发布形态参数化（Q-FE-2b）

| 项 | 现状 | 目标 |
|----|------|------|
| 版本目录 | `build_release.ps1:5` 硬编码 `dist-v1.2.0` | 由 `openbase-ui/package.json` 的 `version` 派生：`$Version = (Get-Content package.json \| ConvertFrom-Json).version; $ReleaseDir = Join-Path $Root "dist-v$Version"` |
| 忽略规则 | `.gitignore:1-3` 仅 `node_modules/dist/coverage` | **增补 `dist-v*`**（版本目录不入提交面）；`coverage/` 保持忽略 |
| 版本号 | `package.json:3` = `1.2.0` | S6 承载版本 **1.3.0**（T6 前完成；发布物 `dist-v1.3.0`） |
| 门禁前置 | `build_release.ps1:7-14`：Lint 0 + 测试 100% + 覆盖率 ≥80% | 保持门禁语义不变；**当前 Lint 与覆盖率两项基线不达标**（§1.4）→ T3/T4 补测 + 修 lint 后复跑，未达标则 T6 如实登记 |
| 发布/回滚 | `L20-24` 保留上一版本目录；nginx 切 `/ui/` 指向 | 保持；补「切换/回滚实测」为非沙箱项 B6 |

---

## 3. 现状代码落点（行号 2026-09-10 复核）

> 复核基线：OpenBase HEAD `be7a8aa`；`openbase-ui` 107 tracked / src 90；本文所有行号均为**当日实测**。标注「Δ」者为与立项方案 §2 记载不一致或新增的落点。

### 3.1 核心层

| 文件 | 复核行号与要点 | 与立项方案差异 | S6 用途 |
|------|---------------|---------------|---------|
| `openbase-ui/src/core/router/index.ts` | `staticRoutes` **L7-28**（含 `system/*` 8 条：L18-25）；`moduleRouteLoaders` **L31-37**（5 模块）；`mountModuleRoutes` **L45-65**；父路由告警修复注记 **L52-53**；`beforeEach` **L67-94**；**装载单次门 L76-84**；`L85` 兜底 `/dashboard`；`L86-92` 模块权限门 | Δ 新增：**L76-84 单次装载门**与 **L85 丢上下文**为 OB-10 现象的结构性根因（立项方案仅登记现象） | T2 核心改造点 |
| `openbase-ui/src/core/stores/moduleRegistry.ts` | `state` **L13-16**；`enabledModules` **L18**；`init` 权限过滤 **L21-29**（过滤体 L24-27）；`loadRoutes` **L34-41（占位）**；`unregister` **L42-44** | 一致（立项方案 L21-29/L34-41 复核成立） | T2（loadRoutes 收敛） |
| `openbase-ui/src/core/api/http.ts` | `ErrorResponse` **L7-12**；`ApiSuccess` **L14-18**；`tokenStore` **L23-34**；`http.create` **L36**（`baseURL='/api/v1'`、`timeout=15000`）；JWT 注入 **L38-42**；`refreshAccessToken` **L46-53**；`refreshing` 单飞 **L44**；响应拦截器 **L55-90**；取消透传 **L62-64**；401 静默刷新 **L71-84**；**统一 `ElMessage.error` L86-88**；`isApiError` **L92-94** | Δ 新增：`L86-88` 为「403/404/5xx 不分类」的唯一出口；`L79-83` 用 `window.location.href` 整页跳转（丢 `redirect`） | T3/T4 改造点 |
| `openbase-ui/src/core/api/auth.ts` | `AuthUser` **L6-11**；`ModuleInfo` **L13-22**；`parseOidcHash` **L25-31**；`authApi` **L33-48**；`modulesApi.list` **L50-54** | 一致 | T4 |
| `openbase-ui/src/core/api/{dps,gateway,llm,rag}.ts` | 6 个客户端（auth/dps/gateway/http/llm/rag） | 一致 | T3 |
| `openbase-ui/src/core/stores/auth.ts` | `state` **L6-9**；getters **L11-13**；`login` **L15-18**；`loadMe` **L19-31**（**吞错 L26-27**）；`hasPermission` **L32-35**；`logout` **L36-39** | Δ 新增行号（立项方案未记）；`L26-27` 吞错需在 T4 补「失败可观测」 | T4 |
| `openbase-ui/src/core/layouts/AppLayout.vue` | 模板 `el-menu` **L5-15**（`:router` L8）；菜单项 **L11-14**；顶栏标题 **L23**；用户/登出 **L25-32**；图标导入 **L44**；`iconMap` **L55-57**；`menuItems` **L59-68**（模块项 path = `route_prefix` **L65**）；resize **L77-85** | Δ 新增：`iconMap` 仅 5 键（模块图标不全）；顶层 `:default-active="route.path"`（**L6**）与 `route_prefix` 不一致 → 子页不高亮 | T2 |
| `openbase-ui/src/core/layouts/ModuleLayout.vue` | 水平 `el-menu` **L3-16**；`groups` 取自 `route.meta.navItems` **L31**；空态无兜底 | Δ 新增：`route.meta` shallow merge 覆盖风险（同 §2.3） | T2 |
| `openbase-ui/src/core/styles/tokens.css` | 设计令牌（颜色/圆角/头部高） | 立项方案未记 | T2/T3 呈现样式 |
| `openbase-ui/vite.config.ts` | `build.outDir='dist'` **L12-13**；`manualChunks` **L15-22**；dev/preview proxy **L24-41**；**test 配置 L42-55**；`coverage.include` **L47**；`thresholds` **L48-53（lines/funcs/stmts 80、branches 70）** | Δ 新增（立项方案未记 vite 配置） | Q-FE-7b 覆盖率口径 |
| `openbase-ui/.gitignore` | **L1-3**：`node_modules`/`dist`/`coverage` | Δ 新增：**未忽略 `dist-v*`** → 版本目录误纳风险 | T1/T6 |

### 3.2 页面与模块

| 文件 | 复核行号与要点 | S6 用途 |
|------|---------------|---------|
| `src/pages/Login.vue` | 表单/`data-test` 锚点 **L7-12**；OIDC 按钮 **L15-17**；`onOidcLogin` **L38-48**；`onSubmit` **L50-67**（回跳 `route.query.redirect` **L59**） | T4（登录态回归、回跳安全） |
| `src/pages/OidcCallback.vue` | 模板 `processing/error` **L4-8**；`goLogin` **L26-28**；`onMounted` 解析 fragment **L30-42**；缺令牌错误页 **L32-36**；落 token + `replace` 回跳 **L37-41** | T4（S6-T4-3） |
| `src/pages/Dashboard.vue` | 仪表盘 50 行（`v-for` 属性序 lint warning `L4`） | T2/T3（落地页） |
| `src/pages/SystemTenants.vue` | 租户管理 192 行（lint warning `L12`、`L68`；`ElMessage.error` L187） | T3（受信通道/租户上下文旁证） |
| `src/modules/openllm/index.ts` | `routes` **L7-51**（36 条 + redirect；P2-3 补注册 `recommend`/`reports-trend` **L47-50**）；`navItems` **L54-108**（4 组共 33 项） | T2/T3（对话关键页 conversations L38） |
| `src/modules/memory/index.ts` | `routes` **L4-16**（10 条 + redirect）；`navItems` **L19-33**（8 项；`monitor`/`:id` 不在菜单） | T3（记忆关键页 list/search/sessions） |
| `src/modules/knowledge/index.ts` | `routes` **L4-13**（7 条 + redirect）；`navItems` **L16-28**（6 项） | T3（知识关键页 list/detail/chat） |
| `src/modules/portrait/index.ts` | `routes` **L4-20**（14 条 + redirect；`:id` 声明顺序修复注记 L7-8）；`navItems` **L23-40**（11 项） | T3（画像关键页 list/detail/overview） |
| `src/modules/gateway/index.ts` | `routes` **L8-11**（2 条 + redirect）；`navItems` **L14-22**（2 项） | T2（导航一致性样本） |

### 3.3 测试、构建与部署

| 文件 | 复核要点 | S6 用途 |
|------|---------|---------|
| `openbase-ui/tests/*.spec.ts`（7 个） | 合计 **573 行**：`core.spec.ts` 80 / `core-extra.spec.ts` 124 / `http.spec.ts` 127 / `gateway-api.spec.ts` 83 / `module-pages.spec.ts` 52 / `oidc-auth.spec.ts` 23 / `portrait-list-error.spec.ts` 84；**沙箱实测 44 用例全绿** | T2/T3/T4 回归基座 |
| `openbase-ui/scripts/build_release.ps1` | 头部版本注记 **L1**；`$ReleaseDir` 硬编码 **L5**（`dist-v1.2.0`）；门禁文案 **L7**；lint **L9-10**；test **L11-12**；coverage **L13-14**；build **L16-18**；版本目录 **L20-24** | T1（参数化）/T6（门禁聚合） |
| `openbase-ui/nginx.conf.example` | `/ui/` 静态 **L9-14**（`alias …/dist/`、`try_files`、`expires 1h`）；`/api/` 反代 **L17-27**（`Authorization` 透传 L21、`proxy_buffering off` L25、`proxy_read_timeout 300s` L26）；`/` → 301 `/ui/` **L30** | T1（发布形态） |
| `openbase-ui/package.json` | `version` **L3**；scripts **L6-13**（`lint` L10 = `eslint src --ext .ts,.vue && vue-tsc --noEmit`；`test` L11；`test:coverage` L12）；deps **L14-23**；devDeps **L24-39** | T1（版本号）/Q-FE-4（Playwright 引入位） |
| `openbase-ui/tsconfig.json` / `tsconfig.node.json` / `eslint.config.js` | 构建与 lint 配置（`npm run lint` 实测 1 error，见 §1.4） | T3/T6 门禁前置 |

### 3.4 三处待改造点（只读复核，S6 不改动其仓文件）

| # | 仓 | 文件:行号（2026-09-10 复核） | 复核结论 | Δ |
|---|----|------------------------------|---------|---|
| 1 | OpenMemory | `deploy/nginx/conf.d/openmemory.conf:90`（`root /app/frontend/dist;`）、`:93-101`（`location / { try_files $uri $uri/ /index.html; }` + 嵌套静态缓存 `:97-100`） | 与立项方案一致；另实测 `:106-124` `/api/` 反代、`:129-133` `/health` | 补充 `:97-100`、`:106-133` |
| 2 | OpenLLM | `docker-compose.yml:141-172`（`frontend` 服务：`build.context ./frontend` L142-144、端口 L147-149、热加载卷 L154-160、`develop.watch` L166-172）；`docker-compose.prod.yml:19`（`./frontend/dist:/usr/share/nginx/html:ro`）；`frontend/Dockerfile` / `Dockerfile.dev` / `nginx.conf` | 与立项方案一致（prod.yml:19 已复核原文） | — |
| 3 | DPS | `.github/workflows/ci.yml`：前端 lint 段 **L68-79**（Setup Node L68-73 + `npm ci`/`npm run lint` L75-79）；前端覆盖率段 **L114-129**；前端构建段 **L164-195**；E2E 段 **L213-230**（Setup Node L213-218、Playwright 安装 L220-224、`npm run e2e` L226-230） | 立项方案记「Lint L68-79 / Coverage L114-125 / Build L164-195 / E2E setup L213-218」→ **复核细化**：覆盖率段实为 L114-129（含 diff-cover L127-129）；E2E 段实为 L213-230 | Δ 行号细化 |
| 3 | OpenRAG | `.github/workflows/frontend-ci.yml`：`paths: ['frontend/**']` **L6/L9**；`quality` job **L12-41**（pnpm install L28-29、lint L30-31、format L32-33、tsc L34-35、test L36-37、build L38-39、audit L40-41）；`e2e` job（Playwright smoke）**L43-65** | 立项方案记「共 62 行」→ 复核文件共 **65 行**（差异为文末空行口径） | Δ 行数 62→65 |

> **冻结声明落点（T1 交付物）**：四仓需各落一行注记（具体路径**按各仓实际**，2026-09-10 实测 README 存在性）：OpenMemory ✅ `README.md`；DPS ✅ `README.md`；OpenRAG ✅ `README.md`；**OpenLLM ✗ 无 `README.md`**（实测仓根仅有 `OpenLLM_完整方案文档.html`、`version.json`、`docker-compose*.yml` 等）→ 落点候选：`docker-compose.yml` 服务注释（随 T1 移除 `frontend` 服务一并落地）或新建 `docs/frontend-frozen.md`。**该注记的落地动作属各子系统仓，S6 内只登记候选落点与核验命令。**

---

## 4. 逐任务设计（T1~T6）

### 4.1 S6-T1 边界收口（3 处改造点 + 后端不挂载确认 + 4 仓冻结声明落点）

**设计说明**

1. **唯一维护面口径**：确立 `OpenBase/openbase-ui` 为前端唯一交付面与提交面；口径落点 = 本设计 §3.4/附录 D + 放行清单 §0 通用红线第 5 条（v1.0.5 现行文本已含「统一前端口径」）+ 清点总清单 §1.4（统一前端口径与清点影响）。三者表述必须一致（同一条计数口径：`git ls-files openbase-ui` = 107）。
2. **改造点 1（OpenMemory nginx）**：按 Q-FE-1 定案「**下线 SPA 承载**」。目标态（子系统仓后续批次）：移除 `openmemory.conf:90` 的 `root /app/frontend/dist;` 与 `:93` 的 `location / { try_files $uri $uri/ /index.html; }`，站点保留 `/api/`（`:106-124`，`proxy_buffering off` 保 SSE）与 `/health`（`:129-133`），并把 `/` 改为 301 → 统一前端 `/ui/`。**S6 内动作 = 登记**（本设计 §3.4 + 附录 D），不改文件。
3. **改造点 2（OpenLLM 编排）**：目标态：删除 `docker-compose.yml:141-172` 的 `frontend` 服务（含 `build.context ./frontend`、3000/5173 端口、热加载卷、`develop.watch`）与 `docker-compose.prod.yml:19` 的 `frontend/dist` 挂载；`frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` 保留不删但不再被编排引用。**S6 内动作 = 登记**。
4. **后端不挂载确认**：对 OpenBase 主仓与四仓后端做**只读核验**——`grep -n "StaticFiles\|mount(\|dist-v" openbase/**` 实测 **0 命中**（无 `StaticFiles`、无 `mount(` 挂载前端产物）；`openbase/cli/main.py:194` 仅为 scaffold CLI 的**目标目录字符串**（`openbase/modules` 或 `openbase-ui/src/modules`），不是产物挂载。四仓结论引用放行清单 v1.0.4 §1.5/§2.5/§3.3/§4.5「均未以 StaticFiles 挂载 frontend 产物」。
5. **发布形态确认（含 Q-FE-2b 落地）**：`build_release.ps1` 版本目录参数化（§2.6）；`nginx.conf.example:9-30` 口径确认；`.gitignore` 增补 `dist-v*`；S6 承载版本 v1.3.0。
6. **提交面纪律**：`frontend/` 改动归 B/C 类；S6 的提交面 = 仓根与 `doc/**` 文档 + `openbase-ui/` 代码/配置 + `doc/test/evidence/s6/**` 证据；**排除** `dogfood-output/`（实测 7 项噪音：`report.md`、`evidence/*.json`、`screenshots/`）与 `dist-v*`/`coverage`/`node_modules`。

**文件落点**

| 类型 | 路径 | 动作 |
|------|------|------|
| 文档（本仓） | `OpenBase-S6-…-设计草案-v1.0.0.md`（本文 §3.4/附录 D） | 新增/维护 |
| 文档（本仓） | `doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`（§0-5、§5 OpenBase 行） | 口径同步（T6 统一回写） |
| 文档（本仓） | `doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md`（§1.4、§3.5） | 口径同步（T6） |
| 代码（本仓 openbase-ui） | `openbase-ui/scripts/build_release.ps1`（版本目录参数化）、`openbase-ui/.gitignore`（`dist-v*`）、`openbase-ui/package.json:3`（1.2.0→1.3.0） | 改造 |
| 只读（他仓） | OpenMemory `deploy/nginx/conf.d/openmemory.conf`；OpenLLM `docker-compose.yml`/`docker-compose.prod.yml`；DPS `.github/workflows/ci.yml`；OpenRAG `.github/workflows/frontend-ci.yml` | **不改动** |
| 只读（他仓） | 冻结声明落点：OpenMemory/DPS/OpenRAG `README.md`；OpenLLM 无 README（候选 `docker-compose.yml` 注释或新建 `docs/frontend-frozen.md`） | **不改动**（登记候选） |

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 |
|----|----------------------|---------|
| **S6-T1-1** | ① 唯一维护面表述三处一致（本设计附录 D、放行清单 §0-5、清点 §1.4），且计数口径 `git ls-files openbase-ui` = 107 实测可复现；② 3 处改造点逐项登记为「仓 / 文件:行号 / 现状语义 / 处置归属仓 / S6 动作=登记」四元组齐备（附录 D）；③ 冻结声明 4 仓落点清单给出「已存在 README 的 3 仓 + OpenLLM 候选落点」，并注明按各仓实际 | 附录 D 四元组；`git ls-files openbase-ui \| Measure-Object -Line` = 107；四仓 `Test-Path README.md` 结果 |
| **S6-T1-2** | ① OpenBase 主仓 `openbase/**` 中 `StaticFiles`/`mount(`/`dist-v` 命中 = **0**；② `openbase/cli/main.py:194` 为 CLI 目标目录文案（非挂载）可引用；③ 四仓「后端未挂载 frontend 产物」结论与放行清单 v1.0.4 一致（引用 + 复核命令给出） | grep 输出（0 命中）；`openbase/cli/main.py:194` 原文；放行清单 §1.5/§2.5/§3.3/§4.5 |
| **S6-T1-3** | ① `build_release.ps1` 版本目录由 `package.json.version` 派生（无硬编码 `dist-v1.2.0`）；② `.gitignore` 含 `dist-v*`；③ `nginx.conf.example:9-30` 口径（`/ui/` 静态 + `/api/` 反代 + `proxy_buffering off`）与本设计一致；④ 发布产物形态为 `dist-v1.3.0`（沙箱内 `npm run build` 可产 `dist`，版本目录生成脚本可验；`/ui/` 切换实测为非沙箱 B6） | `Select-String 'dist-v' build_release.ps1` 无硬编码；`.gitignore` diff；`nginx.conf.example` 行号引用；`get-content package.json \| ConvertFrom-Json .version` = 1.3.0 |
| **S6-T1-4** | ① `git status --porcelain` 中提交面仅含白名单路径（文档 + `openbase-ui/**` 代码配置 + `doc/test/evidence/s6/**`）；② `dogfood-output/` 未被 add（逐项显式 add，禁 `git add -A`）；③ 无任何子系统 `frontend/` 文件出现在本仓提交面 | `git status --porcelain -uall` 与提交面白名单对照；`git show --stat <commit>` 路径清单 |

### 4.2 S6-T2 FE-3 模块导航壳

**设计说明**

1. **缺陷复现（先 RED）**：新增 `tests/router-nav.spec.ts`，用 `createMemoryHistory` 驱动真实 `router/index.ts` + pinia（mock `modulesApi.list` 返回 5 模块），复现两条现象：① `registry.initialized` 预置为 `true`（模拟「已初始化但未装载」）时 `router.push('/portrait/list')` → `matched.length === 0` → 重定向 `/dashboard`（**上下文丢失**）；② `AppLayout` 的 `default-active` 计算在 `/portrait/list` 下不等于菜单项 `index`（**顶层高亮丢失**）。
2. **修复（GREEN）**：按 §2.2 幂等化装载（守卫内无条件 `mountModuleRoutes()`；`loadRoutes` 委托真实装载；`loaded` 双条件判定）；按 §2.3 修 `activeMenu` 计算属性、补 `iconMap`、加 `navItems` 覆盖防护与空态兜底。
3. **权限驱动挂载端到端**：mock `/modules` 返回 5 模块（其中 1 个 `status: 'disabled'`）+ 权限矩阵（`*` / 部分 permission），断言：**禁用模块不进 `enabledModules`、不进顶层菜单、路由不可达**；无权模块访问 → `/dashboard`（`router/index.ts:86-92` 语义保留）。
4. **导航一致性**：新增 `tests/nav-consistency.spec.ts`：遍历 5 模块的 `routes` 与 `navItems`，断言 `菜单路径集合 ⊆ 路由可匹配路径集合`，且 `routes − 菜单 ⊆ 显式白名单`（白名单常量集中声明：redirect 空路径、`*:id` 详情、`*/new` 表单、`*/calls` 等；逐模块登记差异项——portrait `reports`/`batch` 复用 `PortraitList.vue`、memory `monitor` 未入菜单、openllm `apps/new`/`apps/:id`/`auth-ext` 未入菜单）。
5. **路由告警清零**：vitest spy `console.warn`，全量导航 5 模块 × 全部子路由后断言 warn = 0（重点侦测 `Parent route "" not found`）；非沙箱层由 Playwright `page.on('console')` 复核（B1）。

**文件落点**：`src/core/router/index.ts`（幂等装载 L45-65、守卫 L67-94）、`src/core/stores/moduleRegistry.ts`（L34-41 收敛）、`src/core/layouts/AppLayout.vue`（L6/L55-68）、`src/core/layouts/ModuleLayout.vue`（L31 + 空态）、`src/modules/{openllm,knowledge,memory,portrait,gateway}/index.ts`（一致性）/新增 `tests/router-nav.spec.ts`、`tests/nav-consistency.spec.ts`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 |
|----|----------------------|---------|
| **S6-T2-1** | ① 缺陷复现用例（`registry.initialized=true` 且未装载 + 深链）在修复前 **RED**、修复后 **GREEN**；② 深链/刷新直达 `/portrait/list`、`/memory/sessions`、`/knowledge/chat`、`/openllm/conversations` 均命中目标页（`to.matched.length > 0`、`route.meta.module` 正确），**不再回 `/dashboard`**；③ 顶层壳（AppLayout）与模块内二级导航（ModuleLayout）同时渲染且模块上下文（`route.meta.module`/`navItems`）不丢失 | `tests/router-nav.spec.ts`（修复前 RED 记录 + 修复后全绿）；`git diff` 行号 |
| **S6-T2-2** | ① 模块来源唯一：仅 `moduleRegistry.init`（`moduleRegistry.ts:21-29`）依 `/modules` + `permissions` 过滤；② `status: 'disabled'` 模块：不在 `enabledModules`、不进顶层菜单、其 `route_prefix` 不可匹配（访问 → `/dashboard`）；③ 无 `permission` 用户访问对应模块 → `/dashboard`；④ `permissions.includes('*')` 全放行 | `tests/router-nav.spec.ts`（mock 5 模块含 1 disabled + 3 组权限矩阵） |
| **S6-T2-3** | ① 5 模块「菜单 ↔ 路由」一致性断言全绿（含显式白名单，白名单内条目逐条有理由注释）；② 顶层菜单项路径 = `route_prefix`，与模块父路由 `path` 严格相等；③ 模块项 `activeMenu` 在模块子页正确高亮；④ `iconMap` 覆盖 5 模块 `ModuleInfo.icon` 取值，未命中回退有单测 | `tests/nav-consistency.spec.ts`；5 模块 `index.ts` 导出比对 |
| **S6-T2-4** | ① vitest 全量导航后 `console.warn` 调用次数 = 0（含 `Parent route "" not found`）；② 模块路由懒装载无失败（无 `[module:%s] route load failed`）；③ 幂等性：`mountModuleRoutes()` 连续调用 3 次不重复注册（`router.getRoutes()` 数量稳定）；④ 非沙箱层：Playwright `page.on('console')` 断言 warn = 0（B1 复核，未执行则 PENDING） | `tests/router-nav.spec.ts`（spy 断言）；Playwright console 断言（B1） |

### 4.3 S6-T3 FE-R1-1 UI 隔离回归

**设计说明**

1. **画像关键页（portrait/DPS）**：`/portrait/list`（`PortraitList.vue`）、`/portrait/:id`（`PortraitDetail.vue`）、`/portrait/overview`（`Overview.vue`）。断言「本域数据正确渲染 + 错误可观测」：沿用 `tests/portrait-list-error.spec.ts`（84 行）范式——错误条 + 重试按钮 + **非静默空白**，并扩展「空态 ≠ 错误态」用例（`items: []` → 空态文案；`403` → 权限提示；`500` → 错误条 + 重试）。
2. **记忆关键页（memory/OpenMemory）**：`/memory/list`、`/memory/search`、`/memory/sessions`；断言隔离键过滤生效（mock 返回本域数据 + 他域数据不出现）；空态/403 呈现同范式。
3. **知识关键页（knowledge/OpenRAG）**：`/knowledge/list`、`/knowledge/:id`、`/knowledge/chat`；`ChatView.vue` 为对话关键页（SSE 流式，错误面见 §5.3）。
4. **契约映射**：数据面统一经 `http.ts`（`baseURL=/api/v1`），错误体统一 `ErrorResponse{code,message,detail,request_id}`（`http.ts:7-12`）；页面消费 `kind`（§2.4）。**断言 `request_id` 可在错误提示中透出（便于联调定位）但不得落入日志/URL**。
5. **跨域呈现**：按 Q-FE-3b 判定表（§5.2）实现空态/403/404/5xx 四类渲染，禁止把「空数据」渲染为「错误」或反之（**不得静默误导空态**——他域数据不可见与真实无数据必须区分：前者由后端 403/过滤语义决定，前端以「当前租户无数据 / 无权查看」文案区分）。

**文件落点**：`src/modules/portrait/pages/*`、`src/modules/memory/pages/*`、`src/modules/knowledge/pages/*`、`src/core/api/{dps,rag}.ts`、`src/core/api/error.ts`（新增）、`tests/{portrait-list-error,module-pages}.spec.ts` 扩展 + 新增 `tests/isolation-presentation.spec.ts`；E2E：`tests/e2e/{portrait,memory,knowledge,chat}.spec.ts`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 |
|----|----------------------|---------|
| **S6-T3-1** | ① 画像 list/detail/overview 三分支（200 有数据 / 200 空 / 403 / 5xx）渲染符合 §5.2；② 错误态含错误条 + 重试且**无静默空白**；③ 受信通道调用路径为 `/api/v1/**`（无直连子系统地址） | `tests/isolation-presentation.spec.ts`（画像分支）+ `tests/portrait-list-error.spec.ts` 回归 |
| **S6-T3-2** | ① 记忆 list/search/sessions 三分支渲染符合 §5.2；② 隔离键过滤生效（他域数据不出现在渲染结果，mock 交叉数据验证）；③ 会话终止/批量删除等写操作失败走统一错误呈现（非白屏） | `tests/isolation-presentation.spec.ts`（记忆分支） |
| **S6-T3-3** | ① 知识 list/detail/chat 三分支渲染符合 §5.2；② `ChatView` 流式失败（断流/5xx）呈现错误条 + 可重试，**不断流成白屏**；③ 他域知识库不可见（空态/403） | `tests/isolation-presentation.spec.ts`（知识分支） |
| **S6-T3-4** | ① 判定表四类（空/403/404/5xx）逐类有对应用例且通过；② **无 500 泄漏栈**（页面不显示堆栈/原始 JSON）、**无白屏**（容器内有可见文案）；③ 真实双租户数据面复核（B3）：他域列表为空、定向越权 403，作为 RA-06 前端侧验收面回填（未执行 → PENDING） | `tests/isolation-presentation.spec.ts`；B3 复核记录 |

### 4.4 S6-T4 FE-R1-2 登录态 / 吊销回归

**设计说明**

1. **token 失效 → 跳登录且回跳安全**：401 → 单飞刷新（`http.ts:71-84`）；刷新失败 → `clear()` + **SPA 内 `router.replace({ path:'/auth/login', query:{ redirect: 当前 fullPath } })`**（替换现有 `window.location.href`，§2.4）；登录成功后 `Login.vue:59` 用 `route.query.redirect` 回跳，**安全约束**：`redirect` 必须为站内路径（以 `/` 开头且不以 `//` 开头，拒绝 `http(s)://`、`javascript:`、`//evil`），否则回落 `/dashboard`（新增 `safeRedirect()` 工具 + 单测）。
2. **401 静默刷新边界**：① 并发 3 个 401 → 仅 1 次 `/auth/refresh` 调用（单飞 `refreshing` 复用）；② 刷新成功 → 原请求重放 `_retry=true` 仅一次（防无限循环）；③ 刷新失败 → 全部收敛到登录页且不再重试；④ 无 refresh token 时 401 → 直接收敛登录（不尝试刷新）。
3. **403 无白屏**：403 不再走 `ElMessage.error` 兜底（`http.ts:86-88`），改为 `kind='forbidden'` + 页面级提示；**不触发刷新风暴**（403 不触发 refresh）；连续 401/403 交替不发生请求风暴（断言 refresh 调用次数上限）。
4. **OIDC 回调与状态清理**：`OidcCallback.vue:30-42` — `#access_token` fragment 解析（`parseOidcHash`，`api/auth.ts:25-31`）；缺令牌 → 错误页 + 「返回登录页」（`:32-36`）；落 token 后**清空 `auth.user`/`auth.loaded` 并 `replace` 目标页**，由守卫 `loadMe` 重新加载（`:37-41`）；**状态清理**：回调完成后清空 `window.location.hash`（防令牌残留于地址栏/历史）、登出（`AppLayout.vue:70-75` → `stores/auth.ts:36-39`）清空 token 与用户态。
5. **吊销/停用语义呈现**：deactivated/suspended 主体：token 失效 → 跳登录或阻断提示（非空白）；数据面读被拒 → 空/403 呈现（对齐 U1 §5/§6、身份最小集 §12.2「被停用主体任何入口 401/403」）。

**文件落点**：`src/core/api/http.ts`（`L79-83` 跳转方式、`L86-88` 分类、错误分类工具 `src/core/api/error.ts`）、`src/core/stores/auth.ts`（`L26-27` 失败可观测）、`src/pages/Login.vue`（`L59` 安全回跳）、`src/pages/OidcCallback.vue`（`L37-41` hash 清理）、`src/core/router/index.ts`（守卫 `L67-73` 与 `loadMe` 协同）；测试：`tests/http.spec.ts` 扩展 + 新增 `tests/auth-redirect.spec.ts`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 |
|----|----------------------|---------|
| **S6-T4-1** | ① 401 + 刷新失败 → `tokenStore.clear()` 且跳 `/auth/login?redirect=<当前路径>`（**站内 SPA 跳转**，非整页刷新）；② 回跳参数保留且经 `safeRedirect()` 校验（非法值回落 `/dashboard`）；③ 登录成功后正确回到 `redirect` 目标页 | `tests/http.spec.ts` + `tests/auth-redirect.spec.ts` |
| **S6-T4-2** | ① 并发 3 个 401 仅触发 1 次 refresh，请求重放各 1 次（无风暴）；② 403 走页面级 `kind='forbidden'`，不触发 refresh、不弹全局兜底 toast（有页面消费者时）；③ 连续 401（刷新成功但持续 401）不产生无限循环（`_retry` 限一次）；④ 任一分支下 `document.body` 存在可见内容（无白屏断言） | `tests/http.spec.ts`（mock axios，计数断言）+ 渲染断言 |
| **S6-T4-3** | ① `parseOidcHash` 正确解析 `#access_token=..&refresh_token=..`（含仅 access 场景）；② 缺令牌 → 错误页文案 + 「返回登录页」可点击；③ 回调落 token 后 `auth.user=null && auth.loaded=false` 并经守卫 `loadMe` 进入目标页；④ 回调后 `window.location.hash` 被清理（无令牌残留）；⑤ 真实 IdP 回调链路（B4）未执行则 PENDING | `tests/oidc-auth.spec.ts` 扩展 + `tests/auth-redirect.spec.ts` |
| **S6-T4-4** | ① suspended/deactivated 主体 token 失效 → 跳登录或阻断提示（**非空白**）；② 其数据面读被拒 → 空/403 呈现（符合 §5.2）；③ 与 U1 §5/§6、身份最小集 §12.2 语义一致（被停用主体任何入口 401/403）；④ 真实吊销链路复核（B4/B2）未执行则 PENDING | `tests/auth-redirect.spec.ts` + `tests/isolation-presentation.spec.ts`（停用分支） |

### 4.5 S6-T5 L3-2 贯通冒烟（统一前端 → gateway → 子系统）

**设计说明**

1. **脚本形态（Q-FE-4b 定案）**：新增 `openbase-ui/scripts/smoke_l3_2_ui.mjs`（Node 驱动，零新依赖；用 Node 原生 `fetch` 打受信通道端点），职责：① 探活（`/health`、`/api/v1/health`）；② 登录取 token（或读取环境变量注入的 token）；③ 逐关键页调用其**数据端点**（画像/记忆/知识/对话），断言 200 + 数据形状 + **响应头来源标识**（`X-Proxy-Source` 等符合协议头规范，P2-1 §3）；④ 跨域/越权用例断言空或 403；⑤ 输出 evidence JSON（`doc/test/evidence/s6/l3-2-smoke.json`）。
   - **不做旁路直连断言（静态）**：脚本内**只允许**配置 `OPENBASE_BASE_URL`（网关/nginx 同域入口）；另加**静态检查**：`grep -rn "8001\|8002\|8080\|localhost:3" openbase-ui/src` 结果必须为 0（或仅存在于 dev proxy 配置说明），以证明前端不直连子系统端口。**实测现状**：`src/` 无子系统端口硬编码直连（命中的仅 `Conversations.vue` 的错误文案「请确认 OpenLLM 服务（8001）可用」为**提示文案**，非直连）→ 列入白名单并在报告中注明。
   - **浏览器级关键页 PASS 与脚本的分工**：脚本负责通道/契约/越权（可脚本化）；**页面级 PASS 由 Playwright 承载**（B1，`tests/e2e/*`），两者 evidence 分别归档、互相引用。
2. **真实受信通道前置条件**：nginx（`/ui/` + `/api/`）→ OpenBase 后端（gateway/proxy）→ 四子系统运行态；真实 HTTP 双签（Q-FE-5）。**前置不可达时**：登记 `PENDING（环境待办）`，S6-T5 判定为未达成、不阻断已在沙箱内达成的 T2/T3/T4 组件层结论（对齐 S5 Pull 双签 PENDING 范式）。
3. **交叉核对**：与另四段（S2~S5）已移交的 L3-2 结论做一致性核对（同一入口、同一来源标识语义），差异登记。

**文件落点**：`openbase-ui/scripts/smoke_l3_2_ui.mjs`（新增）、`openbase-ui/package.json`（新增 `"smoke:l3-2": "node scripts/smoke_l3_2_ui.mjs"`）、`doc/test/evidence/s6/l3-2-smoke.json`（产物）、`doc/test/OpenBase-S6-…-测试报告-v1.0.0.md`（Step 3 产出）。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 |
|----|----------------------|---------|
| **S6-T5-1** | ① 冒烟脚本 `scripts/smoke_l3_2_ui.mjs` 仅以网关/同域入口（`OPENBASE_BASE_URL` 或 `/ui/` 同域 `/api/`）发起请求，**无任何子系统端口直连**；② 响应来源标识符合协议头规范（`X-Proxy-Source` 等，P2-1 §3）；③ 静态旁路检查（`grep` 端口）结果 = 0（白名单外）；④ 真实双签执行结果如实记录（未执行 → PENDING，不伪造） | `scripts/smoke_l3_2_ui.mjs` 源码；`doc/test/evidence/s6/l3-2-smoke.json`（含 `status`/`base_url`/时间戳/提交号）；grep 输出 |
| **S6-T5-2** | ① 关键页 9 页（Q-FE-4b）在统一前端内 PASS（Playwright，B1；或运行时不可得则逐页登记 PENDING 与原因）；② 关键页数据来自受信通道（请求日志显示 `/api/v1/**`）；③ 与另四段 L3-2 结论一致性核对完成（差异 0 或有登记） | Playwright report + 截图（`doc/test/evidence/s6/ui-e2e/`）；四段 L3-2 结论对照表 |
| **S6-T5-3** | ① 越权/跨域端到端 → 空或 403（无 500、无白屏）逐例记录；② 失败项按 PENDING 挂起登记（含原因、复现命令、责任段），**不阻断**非依赖项；③ evidence 为真实执行结果（含原始响应码/request_id），**禁伪造** | `doc/test/evidence/s6/l3-2-smoke.json`；PENDING 登记表 |

### 4.6 S6-T6 段门禁与台账收口

**设计说明**

1. **UI-E2E 门禁聚合**：门禁自检表（6 项 × 结论 × 证据路径 × 证据 hash/commit）——① UI-E2E 画像/对话/知识/记忆关键页 PASS；② FE-R1-1 通过；③ FE-R1-2 通过；④ FE-3 达成；⑤ L3-2 冒烟通过；⑥ 3 处改造闭环（口径登记完成）。**执行面判定**：沙箱可执行面（A1~A8）与 B1/B2/B6 复核面分列，未执行项写 PENDING。
2. **覆盖率口径处置（Q-FE-7b）**：登记「`npm run test:coverage` 基线 51.52% / 门槛 80%」的前置缺口；T3/T4 补测后复跑并登记最终值；**若仍不达标** → 段门禁自检表该项如实记「未达成」，并列出已补测试与剩余缺口（不得改 thresholds 以「达标」）。
3. **FE-JT 台账回写**（`OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md` §3.6）：v1.0.0 (R1) 行（FE-R1-1、FE-R1-2）与 v1.3.0 (R4) 行（FE-3）→ 状态由 `⏳/📋` 更新为结论 + **提交号**（OpenBase 仓 commit）+ 证据索引；同步 §3.6 下方「统一前端定案」注记（如需）。
4. **放行/清点清单同步**：放行清单 §0-5（统一前端口径不变、追加 S6 段门禁登记）、§5 OpenBase 行（S6 提交号与产物）；清点总清单 §1.4（口径复核，计数不变）、§5.5 后追加「S6 段门禁批准登记」位（待批准时回写）。
5. **evidence 落点与 hash 回填位**：`doc/test/evidence/s6/{ui-e2e/, l3-2-smoke.json, coverage-summary.json}`；**含 `openbase_commit` / `ui_version` / 执行时间 / `status`**；未执行 → `PENDING` + `reason`。**不得伪造 hash**——若沙箱内无法提交，则登记「沙箱受限未提交」。
6. **一致性核验**：T6 收口前重跑 `git status --porcelain -uall`，确认 `dogfood-output/` 未入提交面、`dist-v*` 未入库。

**文件落点**：本文档（§10 回写）；JT 归集 §3.6；放行清单 §0-5/§5；清点总清单 §1.4/§5.5；`doc/test/**`（测试报告与 evidence）。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 |
|----|----------------------|---------|
| **S6-T6-1** | ① UI-E2E 段门禁 = 画像/对话/知识/记忆关键页 PASS，**均在统一前端 openbase-ui 内执行**，逐页结论 + 证据路径齐备；② 未执行页明确 PENDING（原因/前置/责任），不出现「无证据的 PASS」 | 门禁自检表；Playwright report（B1） |
| **S6-T6-2** | ① 段门禁 6 项（UI-E2E / FE-R1-1 / FE-R1-2 / FE-3 / L3-2 / 3 处改造闭环）与 22 条断言逐项映射，无悬空项；② 覆盖率口径产出最终值（沙箱实测）与缺口登记；③ Lint 0 门禁最终状态（含已修项清单）；④ 任一未达成项如实登记 | 门禁自检表；`npm run test:coverage`/`npm run lint` 实际输出 |
| **S6-T6-3** | ① FE-JT 台账 v1.0.0 (R1) 与 v1.3.0 (R4) 行状态与提交号回写；② 放行清单 §0-5/§5 与清点 §1.4/§5.5 口径同步；③ evidence 归档含 `openbase_commit` 与 `ui_version`；④ **hash 一律真实**：未提交/未执行则写「沙箱受限未提交/未执行」，不得伪造 | JT 归集 diff；清单 diff；evidence JSON 字段；`git log -n 1` 输出 |

### 4.7 断言汇总表（22 条，与立项 §4 1:1）

| 任务 | 断言 ID 区间 | 条数 | 沙箱内可判定 | 非沙箱复核项 |
|------|-------------|------|-------------|-------------|
| S6-T1 边界收口 | S6-T1-1 ~ S6-T1-4 | 4 | 4/4（T1-3 的运行态切换部分为 B6） | B5、B6 |
| S6-T2 FE-3 导航壳 | S6-T2-1 ~ S6-T2-4 | 4 | 3.5/4（T2-4 浏览器层告警侦测需 B1） | B1 |
| S6-T3 FE-R1-1 | S6-T3-1 ~ S6-T3-4 | 4 | 3/4（T3-4 真实双租户需 B3） | B3 |
| S6-T4 FE-R1-2 | S6-T4-1 ~ S6-T4-4 | 4 | 3/4（T4-3/T4-4 真实 IdP/吊销需 B4） | B4 |
| S6-T5 L3-2 冒烟 | S6-T5-1 ~ S6-T5-3 | 3 | 0/3（脚本可写、真实执行需 B2/B1） | B1、B2 |
| S6-T6 段门禁收口 | S6-T6-1 ~ S6-T6-3 | 3 | 2/3（T6-1 依赖 B1） | B1、B5 |
| **合计** | — | **22** | **约 16/22 可在沙箱内判定** | B1~B6 |

> 说明：上表「沙箱内可判定」为**能力口径**（该断言存在沙箱内可执行的判定方式），非「已通过」；最终结论一律以 Step 3 测试报告的真实执行证据为准。

---

## 5. 契约与呈现规范

### 5.1 ErrorResponse → UI 映射（前端唯一错误契约）

| 后端错误契约 | 示例 code 前缀 | HTTP | 拦截器 `kind` | UI 呈现 | 是否触发刷新 | 是否全局 toast |
|-------------|---------------|------|--------------|--------|-------------|---------------|
| `ErrorResponse{code,message,detail,request_id}` | `AUTH_` | 401（无 refresh 或刷新失败） | `unauthorized` | 收敛到 `/auth/login?redirect=<站内路径>`；页面不残留半渲染内容 | 是（仅一次单飞） | 否（跳转即反馈） |
| 同上 | `AUTH_` | 401（有 refresh） | — | 拦截器静默重放，页面无感 | 是（单飞复用） | 否 |
| 同上 | `PERM_`/`AUTH_` | 403 | `forbidden` | 页面级提示（`el-result`/空态区）：标题「无权限访问」+ 后端 `message` + `request_id`（折叠详情） | 否 | 默认否（无页面消费者时回退 warning） |
| 同上 | `BIZ_`/`PARAM_` | 400/422 | `business`/`invalid-param` | 表单域/操作区错误提示 | 否 | 是（操作类） |
| 同上 | —（资源不存在） | 404 | `not-found` | 空态：「资源不存在或已被移除」+ 返回列表入口 | 否 | 否 |
| 同上 | `SYS_`/`STORAGE_` | 5xx | `server-error` | 页面错误条 + 「重试」；**不显示堆栈、不显示原始 JSON** | 否 | 是 |
| —（网络/超时） | — | — | `network` | 错误条 + 重试（`timeout=15000`，`http.ts:36`） | 否 | 是 |
| —（主动取消） | — | — | `canceled` | **不提示、不呈现为错误**（保持既有语义 `http.ts:62-64`） | 否 | 否 |

**约束**：① 页面**必须**消费 `kind` 决定渲染，不得自行解析 `error.message` 字符串；② `request_id` 只在「详情」内展示，**不得**写入 URL query、`localStorage` 或日志（AGENTS.md §3 禁记敏感信息）；③ 任何 4xx/5xx 组合都不得造成整页空白（INV-3）。

### 5.2 空态 / 403 / 404 呈现规范（Q-FE-3b 判定表）

| 场景 | 判据 | 呈现 | 文案基线 | 禁止 |
|------|------|------|---------|------|
| 本域有数据 | 200 且 `items.length > 0` | 正常列表 | — | — |
| **他域数据不可见（隔离生效）** | 200 且 `items.length === 0` / `total === 0` | **空态**（`el-empty`） | 「当前租户暂无数据」/「当前租户下无匹配结果」 | 渲染为错误、给出无意义的重试、显示 500 |
| **定向越权** | 403 或 `code` 前缀 `PERM_`/`AUTH_` | **403 页面级提示**（`el-result` error 图标） | 「无权限访问该资源」+ 后端 `message` | 全屏白屏；静默跳 `/dashboard` 吞掉；仅 toast 无页面内容 |
| 资源不存在 | 404 | 空态（非错误态） | 「资源不存在或已被移除」+ 返回入口 | 显示服务端堆栈 |
| 服务端异常 | 5xx | 错误条 + 重试 | 「加载失败，请稍后重试」 | 显示原始 JSON/堆栈 |
| 停用/吊销主体 | 401/403（身份语义） | 401 → 登录页；403 → 403 提示 | 「账号已停用或登录已失效，请重新登录」 | 空白页、无限重试 |

> **「不得静默误导空态」判据**：他域不可见与本域真实无数据**必须在文案上区分语义**（前者「当前租户暂无数据/无权查看」，后者「暂无数据，可前往创建」）；无法区分来源时**保守呈现空态并附加「如为权限问题请联系管理员」提示**，不得呈现为「数据正常为空」而无任何提示。

### 5.3 SSE / 网关错误面（对话与聚合）

| 层 | 失败形态 | 前端呈现与收敛 |
|----|---------|---------------|
| 连接建立 | 网关 401 | 走 §5.1（401 分支），不进入流式渲染 |
| 连接建立 | 网关 403/404 | 页面级 403/404 提示（§5.2），**不残留加载骨架** |
| 流中 | 断流（网络中断/`ERR_ABORTED`） | 保留已产出内容 + 错误条「响应中断」+ 重试；用户主动停止（`CanceledError`）**不显示错误** |
| 流中 | 5xx（HTTP 错误或 SSE 内错误事件） | 错误条 + 重试；保留已产出内容 |
| 配置面 | `proxy_buffering off` 缺失 | 由 `nginx.conf.example:25` 保证；冒烟脚本断言流式首字节行为（B2） |
| 网关聚合 | 部分子服务不可用（聚合降级） | 呈现部分数据 + 「部分数据不可用」提示，**不整页失败**（`gateway` 模块 2 页） |

### 5.4 关键页与导航规范（E2E 用例基线，Q-FE-4b 9 页）

| 关键页 | 路径 | 数据端点（受信通道） | E2E 断言要素 |
|--------|------|--------------------|-------------|
| 画像列表 | `/portrait/list` | `/api/v1/**`（dps） | 列表渲染 / 空态 / 403 / 无白屏 / 顶层高亮 |
| 画像总览 | `/portrait/overview` | 同上 | KPI 渲染 + 单卡片失败降级（沿用既有范式） |
| 画像详情 | `/portrait/:id` | 同上 | 详情渲染 + 不存在 → 404 空态 |
| 对话（OpenLLM） | `/openllm/conversations` | llm | 会话列表 + 流式失败错误条 |
| 对话（RAG） | `/knowledge/chat` | rag（SSE） | 流式输出 + 中断呈现 |
| 知识列表 | `/knowledge/list` | rag | 列表 / 空态 / 403 |
| 知识详情 | `/knowledge/:id` | rag | 详情 + 404 |
| 记忆列表 | `/memory/list` | memory | 列表 / 空态 / 403 |
| 记忆会话 | `/memory/sessions` | memory | 会话列表 + 终止操作失败提示 |

---

## 6. 迁移与兼容

### 6.1 发布形态与回滚

| 项 | 现行（实测） | S6 目标 | 回滚方式 |
|----|-------------|--------|---------|
| 产物目录 | `dist`（未版本化；实测**无** `dist-v1.2.0`） | `dist-v1.3.0`（由 `package.json.version` 派生，Q-FE-2b） | nginx `/ui/` alias 指回上一版本目录（`build_release.ps1:20-24` 保留前一版本） |
| 版本号 | `package.json:3` = 1.2.0 | 1.3.0（S6 承载版本） | 改回 1.2.0 + 重新构建（无数据迁移） |
| nginx | `nginx.conf.example:9-30` 同域示例（alias 指向 `dist/`） | alias 指向版本目录；口径不变（`/ui/` + `/api/` + SSE） | 修改 alias 即回滚（配置级） |
| 忽略规则 | `.gitignore:1-3`（无 `dist-v*`） | 增补 `dist-v*` | 规则级，无副作用 |
| 后端挂载 | 无（S6-T1-2 实测 0 命中） | **不变** | — |
| 数据库 | — | **无迁移** | — |

**兼容性结论**：S6 全部改造为**前端呈现层 + 路由层 + 构建脚本层**变更，不改后端接口契约与数据结构；`ErrorResponse` 契约沿用既有（`http.ts:7-12`），对存量后端零影响；对 S2~S5 已移交结论无回归面（各段结论为后端/数据面）。

### 6.2 子系统前端冻结的可回滚性（Q-FE-1）

| 处置 | 可回滚性 | 说明 |
|------|---------|------|
| 保留 `frontend/` 目录不删除 | **完全可回滚** | 代码在仓，随时可恢复构建（撤销 CI/编排改动 + `npm ci && npm run build`） |
| 停止构建/发布（CI 收敛） | **可回滚** | 收敛以「冻结校验/跳过」实现；恢复即还原 job（建议以可开关形式落地，**具体形式在各子系统仓执行时定**） |
| 后端不挂载产物 | **可回滚** | 挂载为部署配置（compose / nginx conf），还原配置即恢复；无数据面影响 |
| 统一前端承接 | **独立可回滚** | 版本目录切换即回滚，与子系统冻结解耦 |

> **冻结与回滚的耦合风险**：若「后端不再挂载」先于统一前端可用，前端面将不可访问。故**发布顺序约束**：**先发布统一前端（`dist-v1.3.0` + nginx `/ui/` 可用）→ 再在下游子系统仓收敛前端承载**（Q-FE-1 三处改造）。该约束在 S6-T1 登记为执行前置，并在 S7 全链核验中复核。

### 6.3 CI 收敛口径（S6 只出口径，不改他仓）

| 仓 | 现行（实测行号） | 收敛口径（他仓执行） | S6 动作 |
|----|-----------------|--------------------|--------|
| DPS | `.github/workflows/ci.yml`：前端 lint `L68-79`、覆盖率 `L114-129`、构建 `L164-195`、E2E `L213-230` | 前端 job/step 收敛为「冻结校验」或整体跳过；后端门禁不变 | 登记 |
| OpenRAG | `.github/workflows/frontend-ci.yml`（65 行；`paths: ['frontend/**']` L6/L9；quality L12-41 + e2e L43-65） | 触发路径移除或 job 收敛为「冻结校验/跳过」；后端 CI 不变 | 登记 |
| OpenMemory | `deploy/nginx/conf.d/openmemory.conf:90,93` | 下线 SPA 承载（见 Q-FE-1 改造点 1） | 登记 |
| OpenLLM | `docker-compose.yml:141-172`、`docker-compose.prod.yml:19` | 移除 `frontend` 服务与 dist 挂载（见 Q-FE-1 改造点 2） | 登记 |

---

## 7. 风险

| # | 风险 | 类型 | 影响 | 缓解/说明（设计层） |
|---|------|------|------|-------------------|
| R-1 | 沙箱内无法执行浏览器级 E2E 与真实双签（B1/B2/B3/B4/B6） | 约束 | S6-T5-1~3、S6-T6-1 无法在沙箱内结论 | 用例/脚本/配置在沙箱内产出；执行结果由用户复核回填；未执行项一律 PENDING（§1.4） |
| R-2 | **覆盖率门禁基线不达标**（实测 51.52% vs 阈值 80%） | 质量 | S6-T6-2 门禁可能不通过 | Q-FE-7b：不改 thresholds，T3/T4 补测 `src/core/**`；仍不达标则如实登记未达成并列缺口 |
| R-3 | **Lint 门禁当前 1 error + 8 warnings**（`src/modules/portrait/pages/PortraitDetail.vue:40` `vue/no-use-v-if-with-v-for` 等） | 质量 | `build_release.ps1` 的「Lint 0」门禁不通过 | T2/T3 改造 Touch 该文件时一并修复（`v-if` 提到 wrapper）；warnings 以 `--fix` 收敛；复跑验证 |
| R-4 | 「模块内导航覆盖」根因（装载单次门 + 顶层高亮 + meta 覆盖）为**推断**，需 RED 实证 | 技术 | T2 修复面可能超出预期 | T2 先写复现用例（RED）；若复现出额外根因，在 DevLogReport 登记并追加修复项（**不改变 22 断言口径**） |
| R-5 | 引入 Playwright 带来依赖与 CI 时间成本 | 决策 | 构建/E2E 时间上升 | Playwright 仅 E2E 用，`build_release.ps1` 门禁不调用；E2E 独立 script（失败不阻断构建门禁，但阻断段门禁判定） |
| R-6 | `route.meta` shallow merge 覆盖风险 | 技术 | 特定路由下模块内导航消失 | 一致性检查（子路由禁声明 `navItems`）+ `ModuleLayout` 空态兜底 + 单测 |
| R-7 | 401 跳转由 `window.location.href` 改为 SPA `router.replace` 改变既有行为 | 技术 | 既有 `http.spec.ts` 断言需同步更新 | 设计已标明改动点与理由；T4 同步更新对应用例断言 |
| R-8 | 覆盖率 `include` 仅 `src/core/**`，模块页无覆盖率度量 | 质量 | 模块页回归依赖 E2E | Q-FE-7b 定案不扩大 include；模块页由关键页 PASS 承载，缺口在报告中声明 |
| R-9 | evidence 与台账回写的「真实性」依赖人工复核 | 流程 | 可能产出无证据的 PASS | 门禁自检表强制「结论 + 证据路径 + 执行面（沙箱/非沙箱）」三列齐备；无证据不得填 PASS |
| R-10 | 版本目录（`dist-v*`）与 evidence 误入提交面 | 合规 | 破坏提交面白名单 | `.gitignore` 增补 `dist-v*`；T6 收口前 `git status --porcelain -uall` 核对白名单（S6-T1-4） |
| R-11 | 前端侧无独立「后端契约冻结」证据 | 依赖 | 契约变更导致前端回归 | 消费既有 `ErrorResponse`（`http.ts:7-12`）与受信通道口径；如后端契约变更，按 P2-1 台账登记流程同步 |

---

## 8. 边界（S7 项不终验）

| 边界项 | 归属 | S6 内动作 |
|--------|------|----------|
| L3-1 Agent 端到端 | S7 | 不做；S6 只做 L3-2 前端侧贯通冒烟 |
| L2-1 主备切换演练 / L2-2 通道覆盖矩阵终验 | S7 | 不做；不设切换演练 |
| RA-06 终验聚合（双租户/fail-closed/OIDC 归档/委托跨界/吊销） | S7 | **只产出前端侧验收面证据**（FE-R1-1/FE-R1-2），不终验 |
| K07 终验 / 冒烟 S0-S6 聚合与会签 | S7 | 不做 |
| 各子系统后端语义与数据面实现 | S1a~S5 已完成 | 不改动 |
| 统一身份 / 协议头实现（U1/P2-1） | S1a/S1b 已完成 | 只消费语义（登录态/吊销/受信通道），不重复实现 |
| 各子系统 `frontend/` 目录与其 CI/部署配置 | 各子系统仓后续批次 | 只读登记（Q-FE-1） |
| deactivated 数据处置（Q-5 = A：保留 + 全链阻断；purge 显式触发） | S1a/S7 | 只回归前端对阻断的呈现 |
| OpenLLM 全模块 UI-E2E PASS（R4「全模块」增强项） | S6 增强 / S7 | 不阻塞 S6；作为增强项登记 |
| 通道主备（Q-4） | S4/S7 | S6 冒烟以受信通道端到端为准 |

---

## 9. 里程碑（五步流程衔接）

| 步骤 | 交付物 | 与上一步对比（连续审计） | 门禁 |
|------|--------|------------------------|------|
| Step 0 / 需求 | 立项方案（内部 **v1.1.0**，[Approved]，2026-09-10 批准；Q-FE-1~8 定案登记） | 回溯规划 v1.3.1 S6 段定义、JT §3.6、清点/放行清单口径，覆盖无遗漏 | ✅ 已批准（人工） |
| **Step 1 / 设计（本文档）** | 《S6-统一前端隔离展示与段门禁收口-设计草案 v1.0.0》（[Draft]） | 与需求 22 条断言 1:1 对应（§1.3 覆盖矩阵）；Q-FE-1~8 定案逐条落到设计条目（§1.1） | 设计评审人工批准（本草案） |
| Step 2 / 开发 | 《S6-…-DevLogReport v1.0.0》（T1~T4 编码：路由幂等化、导航壳、错误分类与呈现、安全回跳；含源码清单与改动行号） | 与本文档逐条对应（实现一致；RED→GREEN 记录） | 开发自检 + 人工批准 |
| Step 3 / 测试 | 《S6-…-测试报告 v1.0.0》（22 断言逐条结果 + UI-E2E 关键页 PASS 证据 + L3-2 冒烟记录 + 覆盖率/Lint 实测值） | 回溯需求（22 断言）、设计（落点）、开发（覆盖） | 测试评审人工批准 |
| Step 4 / 段门禁收口 | 段门禁自检表 + FE-JT 台账回写 + 放行/清点清单同步 + evidence 归档 | 与测试报告对比验证 | **段门禁 = UI-E2E 关键页 PASS + FE-R1-1/2 回归通过 + FE-3 达成 + L3-2 冒烟通过 + 3 处改造闭环**；人工批准后 S6 收官、移交 S7 |

**里程碑映射**：FE-R1-1/FE-R1-2 → JT **v1.0.0 (R1)**（验证回归）；FE-3 → JT **v1.3.0 (R4)**（体验收尾）；统一前端承载版本 **v1.3.0**（`dist-v1.3.0`）；S6 段门禁批准后回写 JT 归集 §3.6 两行状态与**提交号**（Q-FE-8）。

**任务间依赖**：T1 → T2 → {T3 ∥ T4} → T5 → T6（T6 须待 T1~T5 全绿或如实登记未达成项）。

---

## 10. 遗留与定案登记

### 10.1 已定案（不再重议，引用 §1.1）

| # | 结论摘要 | 状态 |
|---|---------|------|
| Q-FE-1 | 保留不删 + 不再构建/发布 + 后端不挂载；3 处改造点归属子系统仓；S6 只登记 | ✅ 已定案（2026-09-10） |
| Q-FE-2 / Q-FE-2b | `dist-vX.Y.Z` + nginx `/ui/`；S6 承载版本 v1.3.0；脚本参数化 + `.gitignore` 补 `dist-v*` | ✅ 已定案 |
| Q-FE-3 / Q-FE-3b | 跨域 = 空/403；401 单飞刷新失败收敛登录；空 vs 403 判定表（§5.2） | ✅ 已定案 |
| Q-FE-4 / Q-FE-4b | vitest 组件层 + Playwright 关键页层；9 页清单与脚本/evidence 落点 | ✅ 已定案 |
| Q-FE-5 | L3-2 经受信通道端到端、关键页 PASS、无旁路直连；真实双签，不可达 PENDING | ✅ 已定案 |
| Q-FE-6 | S7 终验项不入 S6；移交接口 = evidence 索引 + 台账行 + 冒烟记录，提交号桥接 | ✅ 已定案 |
| Q-FE-7 / Q-FE-7b | 全局 80% 不变 + 新增代码 90% 增量；不扩大 include；登记覆盖率前置缺口 | ✅ 已定案 |
| Q-FE-8 | 不新建独立 JT 版本线，沿用 §3.6 行口径 + 提交号桥接 | ✅ 已定案 |

### 10.2 遗留待评审问题（本设计新识别，须设计评审裁定）

| # | 问题 | 建议 | 阻塞面 |
|---|------|------|--------|
| Q-S6-D1 | `openbase-ui/package.json` 版本号升到 1.3.0 的**时点**：T1 即升，还是 T6 前升？ | 建议 **T6 前**（避免中间态版本号与产物不一致；T1 只做参数化） | S6-T1-3、S6-T6-3 |
| Q-S6-D2 | 401 跳转由 `window.location.href` 改 `router.replace` 后，`stores/auth.ts:19-31` 的 `loadMe` 吞错行为是否一并改为「失败可观测」 | 建议**一并改**（失败置 `loaded=true` + 记录 `auth.loadError`，供页面呈现阻断提示，对齐 S6-T4-4） | S6-T4-1/4 |
| Q-S6-D3 | `ModuleLayout.vue` 的两级导航在移动端（`<768px`）折叠策略（当前 `ModuleLayout.vue:45-48` 仅简化圆角/高度） | 建议 S6 内**只做最小修复**（保持现状 + 空态兜底），移动端交互优化列 S7/后续体验项 | S6-T2-1/3 |
| Q-S6-D4 | 覆盖率补测的**范围取舍**：优先补 `src/core/api/**` 还是 `src/core/router|stores/**`（当前 include 三目录） | 建议优先 `router/**` 与 `api/**`（S6 改动集中处，性价比最高） | S6-T6-2（R-2） |
| Q-S6-D5 | OpenLLM 冻结声明落点（无 `README.md`）：新建 `docs/frontend-frozen.md` 还是在 `docker-compose.yml` 注释 | 建议随改造点 2 一并写 `docker-compose.yml` 服务注释（零新增文件）+ 由各仓自行决定 | S6-T1-1（B5） |
| Q-S6-D6 | L3-2 冒烟脚本与 Playwright 是否需要**同一套用例数据**（避免两套断言漂移） | 建议共享一份「关键页清单 + 期望契约」JSON（`openbase-ui/tests/e2e/fixtures/key-pages.json`），脚本与 E2E 同源读取 | S6-T5-1/2 |
| Q-S6-D7 | 段门禁自检表中「3 处改造闭环」的判定口径：仅「口径登记完成」是否足以判「闭环」 | 建议**拆两级**：S6 内判「口径闭环（登记完成）」；「物理闭环（他仓改造落地）」记为 B5 PENDING 移交 S7 复核 | S6-T6-2、S6-T1-1 |

### 10.3 设计评审必须核对项（Checklist）

1. §1.3 覆盖矩阵：22 条断言是否 1:1（无新增/无遗漏）；
2. §1.1 Q-FE-1~8 定案是否与立项评审结论一致（含 Q-FE-2b/3b/4b/7b 四条补充定案是否被接受）；
3. §1.4「沙箱可执行面 / 非沙箱复核面」清单是否被接受为 S6 证据口径基线；
4. §5.2 空/403 判定表是否作为「不得静默误导空态」的验收判据（RA-06 前端侧）；
5. §10.2 七项遗留是否需在设计评审当次裁定（Q-S6-D1~D7）。

---

## 附录

### 附录 A：引用清单（实测路径）

**需求基线（已在仓根，[Approved]）**
1. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md`（内部 v1.1.0）
2. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md`（内部 v1.3.1，§2 S6 行、§3 S6 前端段 L80-84）
3. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md`（内部 v1.2.0，§3.6 L107-121）
4. `D:\Trae CN\myproject\Dev\OpenBase\doc\planning\OpenBase-联调产物清点核对总清单-v1.0.0.md`（内部 v1.0.2，§1.4 L53-62、§5.5 L345）
5. `D:\Trae CN\myproject\Dev\OpenBase\doc\development\OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`（内部 v1.0.5，§0 红线 5 L43）

**上游语义依据**
6. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-U1-统一身份收口设计草案-v1.0.0.md`
7. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md`（内部 v1.3.0）
8. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md`
9. `D:\Trae CN\myproject\Dev\OpenBase\OpenBase-真实联调冒烟清单-v1.0.0.md`（内部 v1.1.0，§3.6 S6 L83-86）

**改造对象（OpenBase 仓，S6 唯一维护面）**
10. `openbase-ui/src/core/router/index.ts`、`src/core/stores/moduleRegistry.ts`、`src/core/api/http.ts`、`src/core/api/error.ts`（新增）
11. `openbase-ui/src/core/layouts/AppLayout.vue`、`src/core/layouts/ModuleLayout.vue`
12. `openbase-ui/src/pages/Login.vue`、`src/pages/OidcCallback.vue`
13. `openbase-ui/src/modules/{openllm,memory,knowledge,portrait,gateway}/**`
14. `openbase-ui/scripts/build_release.ps1`、`scripts/smoke_l3_2_ui.mjs`（新增）、`nginx.conf.example`、`.gitignore`、`package.json`、`vite.config.ts`、`playwright.config.ts`（新增）
15. `openbase-ui/tests/**`（现有 7 spec + 新增 router-nav / nav-consistency / isolation-presentation / auth-redirect / e2e/*）

**只读盘点对象（子系统仓，S6 不改动）**
16. `D:\Trae CN\myproject\Dev\OpenMemory\deploy\nginx\conf.d\openmemory.conf`
17. `D:\Trae CN\myproject\Dev\OpenLLM\docker-compose.yml` / `docker-compose.prod.yml` / `frontend/Dockerfile` / `frontend/Dockerfile.dev` / `frontend/nginx.conf`
18. `D:\Trae CN\myproject\Dev\DPS\.github\workflows\ci.yml`
19. `D:\Trae CN\myproject\Dev\OpenRAG\.github\workflows\frontend-ci.yml`
20. 冻结声明候选落点：`OpenMemory\README.md`、`DPS\README.md`、`OpenRAG\README.md`（存在）；OpenLLM（实测无 `README.md`）

### 附录 B：沙箱实测记录（2026-09-10，可复现）

| # | 命令 | 结果摘要 | 退出码 |
|---|------|---------|--------|
| 1 | `node -v` / `npm -v` | v22.16.0 / 10.9.4 | 0 |
| 2 | `Test-Path openbase-ui\node_modules`；`…\.bin\vitest.cmd` | True / True（依赖已装） | 0 |
| 3 | `git -C <root> ls-files openbase-ui \| Measure-Object -Line` | **107** | 0 |
| 4 | `git -C <root> ls-files openbase-ui/src \| Measure-Object -Line` | **90** | 0 |
| 5 | `git -C <root> rev-parse HEAD` | `be7a8aaa2e113527db71ec5e47d0297a9fbf4af2` | 0 |
| 6 | `npm test`（openbase-ui） | **7 files / 44 tests passed**（Duration 38.15s；stderr 含 jsdom `Not implemented: navigation` 与 `AggregateError` 噪音） | **0** |
| 7 | `npm run test:coverage` | All files：stmts **51.52%** / lines **51.52%** / funcs **50.66%** / branches **85.84%**；阈值 80/80/80/70 → `ERROR: Coverage … does not meet global threshold (80%)` ×3 | **1** |
| 8 | `npm run lint` | `✖ 9 problems (1 error, 8 warnings)`；error = `src/modules/portrait/pages/PortraitDetail.vue:40:18 vue/no-use-v-if-with-v-for` | **1** |
| 9 | `Get-ChildItem openbase-ui -Directory` | `coverage / dist / node_modules / scripts / src / tests`（**无 `dist-v*`**） | 0 |
| 10 | `grep -n "StaticFiles\|mount(\|dist-v" openbase/**` | **0 命中**（S6-T1-2 依据） | 0 |
| 11 | `grep -rn "8001\|8002\|8080\|localhost:3" openbase-ui/src` | 仅 `modules/openllm/pages/Conversations.vue` 的**提示文案**（「OpenLLM 服务（8001）可用」），非直连 | 0 |
| 12 | `Test-Path <repo>\README.md`（OpenMemory/OpenLLM/DPS/OpenRAG） | True / **False** / True / True | 0 |

### 附录 C：22 条断言 → 落点 → 证据 索引

| 断言 | 主要落点（OpenBase 仓） | 证据落点（Step 3） | 执行面 |
|------|-----------------------|-------------------|--------|
| S6-T1-1 | 本设计 §3.4/附录 D；放行清单 §0-5；清点 §1.4 | 口径核对表（测试报告 §T1） | 沙箱 |
| S6-T1-2 | `openbase/**`（grep）；放行清单 §1.5/§2.5/§3.3/§4.5 | grep 输出（附录 B#10） | 沙箱 |
| S6-T1-3 | `scripts/build_release.ps1`、`.gitignore`、`package.json`、`nginx.conf.example` | diff + 构建产物清单 | 沙箱（切换 B6） |
| S6-T1-4 | 提交面白名单；`dogfood-output/` 排除 | `git show --stat <commit>` | 沙箱 |
| S6-T2-1 | `router/index.ts`、`ModuleLayout.vue`、`tests/router-nav.spec.ts` | RED→GREEN 记录 | 沙箱 |
| S6-T2-2 | `moduleRegistry.ts`、`router/index.ts` | 用例输出（权限矩阵） | 沙箱 |
| S6-T2-3 | `AppLayout.vue`、5 模块 `index.ts`、`tests/nav-consistency.spec.ts` | 一致性断言输出 | 沙箱 |
| S6-T2-4 | `router/index.ts`、`tests/router-nav.spec.ts`；Playwright console 断言 | warn 计数 = 0 输出 | 沙箱 + B1 |
| S6-T3-1~3 | `modules/{portrait,memory,knowledge}/pages/**`、`tests/isolation-presentation.spec.ts` | 分支渲染用例输出 | 沙箱 |
| S6-T3-4 | `src/core/api/error.ts`、`http.ts`；真实双租户 | 四类判定用例 + B3 复核记录 | 沙箱 + B3 |
| S6-T4-1 | `http.ts:71-84,79-83`、`Login.vue:59`、`tests/auth-redirect.spec.ts` | 用例输出 | 沙箱 |
| S6-T4-2 | `http.ts:55-90`、`tests/http.spec.ts` | 计数断言输出 | 沙箱 |
| S6-T4-3 | `OidcCallback.vue:30-42`、`api/auth.ts:25-31`、`tests/oidc-auth.spec.ts` | 用例输出 | 沙箱 + B4 |
| S6-T4-4 | `stores/auth.ts:19-31`、`http.ts`；真实吊销 | 用例输出 + B4 复核 | 沙箱 + B4 |
| S6-T5-1 | `scripts/smoke_l3_2_ui.mjs`、`doc/test/evidence/s6/l3-2-smoke.json` | 冒烟 JSON | B2 |
| S6-T5-2 | `tests/e2e/*.spec.ts`、`playwright.config.ts` | Playwright report + 截图 | B1 |
| S6-T5-3 | 冒烟脚本 + PENDING 登记表 | 失败项登记 | B2 |
| S6-T6-1 | 门禁自检表；`doc/test/evidence/s6/ui-e2e/` | 自检表 + report | 部分 B1 |
| S6-T6-2 | 门禁自检表；覆盖率/Lint 实测 | 自检表 + 命令输出 | 沙箱 |
| S6-T6-3 | JT §3.6；放行 §0-5/§5；清点 §1.4/§5.5；evidence | diff + JSON 字段 + `git log -n 1` | 沙箱 + B5 |

### 附录 D：三处待改造点登记四元组（S6-T1-1 交付物）

| # | 仓 | 文件:行号（2026-09-10 复核） | 现状语义 | 处置归属 | S6 动作 |
|---|----|------------------------------|---------|---------|---------|
| 1 | OpenMemory | `deploy/nginx/conf.d/openmemory.conf:90`、`:93-101`（含 `:97-100` 静态缓存） | 以子系统前端产物为站点根 + SPA 兜底（运行态承载子系统前端） | OpenMemory 后续批次 | **登记**（下线 SPA 承载；保留 `/api/` `:106-124` 与 `/health` `:129-133`，`/` 改 301 → `/ui/`） |
| 2 | OpenLLM | `docker-compose.yml:141-172`（`frontend` 服务）；`docker-compose.prod.yml:19`；`frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` | 开发/生产均构建并服务子系统前端 | OpenLLM 后续批次 | **登记**（移除 `frontend` 服务与 dist 挂载；镜像文件保留不删） |
| 3 | DPS + OpenRAG | DPS `.github/workflows/ci.yml`：lint `L68-79`、覆盖率 `L114-129`、构建 `L164-195`、E2E `L213-230`；OpenRAG `.github/workflows/frontend-ci.yml`（65 行：`paths` L6/L9、quality L12-41、e2e L43-65） | CI 仍对子系统前端执行 lint/test/build/e2e | DPS / OpenRAG 后续批次 | **登记**（前端段收敛为「冻结校验/跳过」） |

> 说明：改造点 3 为「子系统前端 CI 构建链」，合并登记 DPS 与 OpenRAG 两仓（合计 **3 处 / 4 仓**）；所有行号均为 2026-09-10 只读实测值；**S6 内不修改上述任何文件**。冻结声明的 4 仓落点见 §3.4 末段（3 仓有 `README.md`、OpenLLM 无）。

---

> **文档结束**。本文档为 S6 段「设计」环节交付物（[Draft]），待设计评审人工批准后进入 Step 2 开发；Q-FE-1~8 已定案（§1.1），本文档遗留项（§10.2 Q-S6-D1~D7）须在设计评审当次裁定。
