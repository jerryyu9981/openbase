# OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S6-v1.0.0 |
| 版本 | v1.1.1 |
| 状态 | [Approved]（2026-09-10 立项评审批准进入设计开发；Q-FE-1~Q-FE-8 已一次性定案并登记于《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md》§1.1，本文档 §3.2/§9 的「建议/待人工批准」表述以设计草案 §1.1 定案表为准，不再重议；**v1.1.1 追加 S6 段门禁结论注记（T1~T6 实施完成，非沙箱项 PENDING）**） |
| 日期 | 2026-09-10 |
| 作者 | AD（跨项目分析）+ AI（openbase-ui 侧现状盘点与起草） |
| 版本主题 | **S6 = 前端段（FE-JT 收官）**，主题命名为「**统一前端隔离展示与段门禁收口**」：唯一维护面 = `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`（已入库跟踪，实测 107 文件）；S6 = 在 openbase-ui 内落地 **FE-3 模块导航壳** + **FE-R1-1/FE-R1-2 全量回归** + **L3-2 贯通冒烟**；门禁 UI-E2E 画像/对话/知识/记忆关键页 PASS 均在统一前端执行；不含各子系统独立前端维护（DPS/OpenLLM/OpenMemory/OpenRAG 的 `frontend/` 冻结、不再构建/发布、后端不再挂载其产物） |
| 适用范围 | OpenBase 仓（唯一维护面 = 仓内 `openbase-ui/`）；对 DPS/OpenLLM/OpenMemory/OpenRAG 四仓的 `frontend/` 与 CI/部署配置仅作**只读盘点与口径收口**（不在 S6 内改动其仓文件）。本方案自身为新建未跟踪文档（`git status` 显示 OpenBase 工作树仅 `dogfood-output/` 噪音，见 §2.1） |
| 上游依据 | 规划 v1.3.1（S6 段定义修订/统一前端定案）：`OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md`；JT 归集 v1.2.0（§1/§3.6/§4/§5、统一前端定案段）：`OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md`；清点总清单 v1.0.2（§1.4 统一前端口径/§5.5 S5 门禁登记/五仓清点口径）：`doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md`；放行清单 v1.0.5（§0 通用红线第 5 条统一前端口径/§3.3 S5 段门禁登记）：`doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`；升级路线规划（OB-10 前端壳/UI-E2E P3/R4 体验与收尾行）：`OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md`；P2-1 设计草案 v1.0.0 §9.3/§11.1（OB-10 外移说明）：`OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md`；U1 设计草案 v1.0.0（登录态/吊销 semantics：token 失效、deactivated 阻断与前端呈现、OIDC 回调）：`OpenBase-U1-统一身份收口设计草案-v1.0.0.md`；身份最小集与隔离模型设计 v1.3.0（隔离与跨域呈现语义、R-H1-2 跨域 403/R-H2 吊销即时性）：`OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md`；真实联调冒烟清单 v1.1.0（S5 主链路端到端/S6 旁路与双链路）：`OpenBase-真实联调冒烟清单-v1.0.0.md`；先例立项范式：DPS-S5 / OpenLLM-S4 / OpenRAG-S3 / OpenMemory-S2 立项方案 |

> **注记（v1.1.0，2026-09-10）**：**2026-09-10 立项评审批准进入设计开发**。Q-FE-1~8 已一次性定案，登记见《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md》**§1.1**（唯一事实源）；本方案 §3.2/§9 的「建议 ✅ / 待人工批准」表述以该定案表为准，不再重议。本方案 22 条验收断言（S6-T1-1~S6-T6-3）口径不变，作为 Step 1 设计的追溯基线。

> **注记（v1.1.1，2026-09-10）**：**S6 段 T1~T6 实施完成并回写段门禁结论**。设计草案已由 [Draft] 升 [Approved]（v1.0.1）；四批提交入库（批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 = `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`）。段门禁结论：**已达成** FE-3（S6-T2）、FE-R1-1 前端侧回归（S6-T3）、FE-R1-2 前端侧回归（S6-T4）、覆盖率/Lint 门禁（97.08/90/88.46/97.08；lint 0 problem）、3 处改造口径闭环；**PENDING（非沙箱）** UI-E2E 关键页 PASS（B1）、L3-2 真实受信通道双签（B2）、物理闭环（B5 交 S7）。**本方案 22 条验收断言口径与 §2~§10 正文不变**，结论证据见 `doc/development/OpenBase-S6-…-DevLogReport-v1.0.0.md`、`doc/test/OpenBase-S6-…-测试报告-v1.0.0.md` 与 `doc/test/evidence/s6/**`。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-10 | AD + AI（openbase-ui 侧起草） | 初始版本：S6 段（前端段，FE-JT 收官）立项方案。内容含背景与目标（承接 S6 段门禁：统一前端唯一维护面、UI-E2E 画像/对话/知识/记忆关键页 PASS、FE-R1-1/2 回归、L3-2 贯通）、现状盘点与差距实证（openbase-ui 事实清单含行号、FE-1/FE-2 已完成证据与缺口、子系统 frontend 冻结现状与 3 处待改造点、差距表）、范围与定案（Q-FE-1~Q-FE-6 建议定案；Q-FE-7/8 新增识别项）、任务分解（S6-T1~S6-T6，含落点文件与验收断言编号）、验收标准（断言式，22 条 + 段门禁聚合）、非目标与边界、影响面与兼容、风险与依赖、里程碑与五步流程衔接、遗留待评审问题、附录（引用清单/openbase-ui 统计/待改造点行号） |
| v1.1.0 | 2026-09-10 | 项目负责人（评审批准）/ AD + AI（定案登记回写） | **立项评审批准与定案登记**：注记「**2026-09-10 立项评审批准进入设计开发**」；状态 **[Draft] → [Approved]**；**Q-FE-1~8 一次性定案**（含设计级补充定案 Q-FE-2b/3b/4b/7b）登记于《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md》§1.1（唯一事实源）；本文 §3.2/§9 的「建议 ✅ / 待人工批准」表述随之收敛，**22 条验收断言（S6-T1-1~S6-T6-3）口径不变**；批准口径：2026-09-10 S6 段立项评审人工批准（评审人 = 项目负责人经 AI 开发会话人工确认）。本次仅回写本文档元信息与修订历史，未改动 §2~§10 正文口径 |
| v1.1.1 | 2026-09-10 | AI（S6 批次 4 开发会话） | **S6 段门禁结论注记**：T1~T6 实施完成，设计草案升 [Approved]（v1.0.1）；四批提交入库（`2abe52a`/`aa6c5bd`/`72b19da`/批 4）并回写段门禁结论（已达成 FE-3/FE-R1-1/FE-R1-2、覆盖率 97.08-90-88.46-97.08、lint 0 problem、3 处改造口径闭环；非沙箱 PENDING：B1 UI-E2E、B2 L3-2 双签、B5 物理闭环）。**仅追加状态注记与修订历史，未改动 §1~§10 正文与 22 条断言口径** |

---

## 1. 背景与目标

### 1.1 承接 S6 段门禁（规划 v1.3.1）

- **S6 = 前端段（FE-JT 收官）**：主要任务 `FE-3、FE-R1-1/2、L3-2 贯通冒烟`（规划 v1.3.1 §2/§3 S6 行、§5 任务分布核对表）。
- **前置**：S2（OpenMemory 段）、S3（OpenRAG 段）、S4（OpenLLM 段）、S5（DPS 收口段）均已段门禁批准或收官（S2/S3/S4 见放行清单 v1.0.1~v1.0.3；S5 于 2026-09-10 人工批准，见清点总清单 §5.5 与放行清单 v1.0.5）；各子系统数据面/身份面的隔离与受信通道契约已就绪，S6 方可对统一前端做端到端回归。
- **统一前端定案（规划 v1.3.1 / JT 归集 v1.2.0）**：唯一维护面 = `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`（Git 仓在 OpenBase 项目目录下、已入库跟踪，`git ls-files openbase-ui` 实测 107 文件）；各子系统自带 `frontend/`（DPS/OpenLLM/OpenMemory/OpenRAG）**暂时冻结、不再维护**（保留目录不删除、不再构建/发布、后端不再挂载其产物）。
- **门禁（UI-E2E）**：画像/对话/知识/记忆关键页 PASS **均在统一前端 openbase-ui 内执行**（画像=portrait/DPS、对话=openllm+knowledge、知识=knowledge/OpenRAG、记忆=memory/OpenMemory）（规划 v1.3.1 §3 S6 行）。
- **相邻段边界**：S6 不含各子系统独立前端维护；S7（总收官段）承接 L3-1 Agent 端到端、L2-1 主备切换演练、L2-2 通道矩阵终验、RA-06 终验、K07 终验与稽核（见 §5/§9）。
- 本立项即 **S6 段「需求」环节交付物**（五步流程 Step 0/需求，见 §8），人工批准后进入 Step 1 设计。

### 1.2 目标（本段要达成什么）

1. **统一前端唯一维护面收口**：确立 `OpenBase/openbase-ui` 为前端唯一交付面与提交面；各子系统 `frontend/` 冻结口径落地（保留不删、不再构建/发布、后端不挂载其产物），并完成 3 处「仍在构建/发布子系统前端」待改造点的归属与处置登记（§2.3/§3.4 S6-T1）。
2. **FE-3 模块导航壳**：修复「模块内导航覆盖」问题，落地模块页统一导航壳——顶层统一壳（AppLayout）承载模块导航 + 模块内二级导航（ModuleLayout）层级清晰、权限驱动模块挂载、导航与路由一致性闭环（消除 `No match → /dashboard` 丢上下文与 Vue Router 父路由告警）。
3. **FE-R1-1 UI 隔离回归**：R1 隔离收口后，在统一前端执行画像/记忆/知识关键页数据正确性回归；跨域数据在前端呈现为**为空 / 403 提示**（无 500、无白屏），配合 RA-06 门禁。
4. **FE-R1-2 登录态/吊销回归**：token 失效后正确跳登录；401/403 处理无白屏（静默刷新失败收敛、权限拒绝提示规范）；OIDC 回调链路（fragment 解析、缺令牌错误页、回调后 `me` 加载）回归通过；deactivated/suspended 主体（U1 吊销语义）在前端呈现阻断而非空白。
5. **L3-2 贯通冒烟（统一前端侧）**：段末执行「统一前端 → OpenBase gateway → 子系统」端到端冒烟，关键页 PASS（经 OpenBase 受信通道，来源标识符合协议头规范）。
6. **段门禁与台账回写**：聚合 UI-E2E 关键页 PASS + FE-R1-1/2 回归通过 + FE-3 达成 + L3-2 冒烟通过 + 3 处改造闭环；回写 FE-JT 台账（v1.0.0/R1 与 v1.3.0/R4 行）、同步放行清单与清点总清单口径、归档 evidence（不得伪造 hash）。

### 1.3 段门禁（成功标准，规划 v1.3.1 + 本方案 §4/§8 收敛）

S6 段门禁 = **UI-E2E 画像/对话/知识/记忆关键页 PASS（均在统一前端执行）+ FE-R1-1/FE-R1-2 全量回归通过 + FE-3 模块导航壳达成 + L3-2 贯通冒烟通过 + 3 处待改造点闭环**（对齐 S2/S3/S4/S5 段门禁范式），并完成 FE-JT 台账回写（JT v1.0.0(R1) 与 v1.3.0(R4) 行状态与提交号）。

---

## 2. 现状盘点与差距实证

> 盘点基线：OpenBase 仓 `main` 分支 HEAD `5830b8095995317041a08ca8f473de1e6e4ae446`（`docs(intg): S5 段门禁批准回写与清点/放行清单同步`）；`git status --porcelain -uall` 实测仅 `dogfood-output/` 噪音（不提交，见 §2.1）。openbase-ui 计数由 `git ls-files openbase-ui` 与逐目录实测得出（只读，未改动任何仓文件）。

### 2.1 openbase-ui 事实清单（含行号）

**仓与版本基线**

| 项 | 现状（实证） | 证据 |
|----|-------------|------|
| 入库跟踪文件数 | **107** | `git ls-files openbase-ui`（实测 107）；与规划 v1.3.1 / JT 归集 v1.2.0 记载一致 |
| `src/` 文件数 | **90** | 逐目录实测（core 13 + modules 71 + pages 4 + App.vue/main.ts 2） |
| 工程版本 | `package.json` `version`=**1.2.0** | `openbase-ui/package.json:3` |
| 脚本 | `dev` / `build`(`vue-tsc --noEmit && vite build`) / `preview` / `lint` / `test`(`vitest run`) / `test:coverage` | `openbase-ui/package.json:6-13` |
| 框架与依赖 | Vue 3.5 / vue-router 4.5 / pinia 2.3 / element-plus 2.9 / axios 1.7 / echarts 5.6 / d3 7.9；测试框架 **vitest 2.1 + @vue/test-utils + jsdom** | `openbase-ui/package.json:14-39` |

**核心层（`src/core/`）**

| 文件 | 行号/要点 | 结论 |
|------|----------|------|
| `src/core/router/index.ts` | 静态路由 `staticRoutes` **L7-28**；模块路由装载表 `moduleRouteLoaders`（5 模块：openllm/knowledge/memory/portrait/gateway）**L31-37**；`mountModuleRoutes()`（顶层挂载 + ModuleLayout 承载 + navItems 注入）**L45-65**；全局前置守卫 `router.beforeEach`（public/token/permission/module 四重判定）**L67-94**；父路由告警修复注记 **L52-53** | 已具备「静态路由 + 动态模块挂载 + 权限门」骨架 |
| `src/core/stores/moduleRegistry.ts` | 状态 `modules`/`initialized` **L13-16**；`enabledModules` getter **L18**；`init(permissions)` 依后端 `/modules` 清单 + 权限过滤 **L21-29**（过滤 L24-27）；`loadRoutes` **L34-41**；`unregister` **L42-44** | 权限驱动模块挂载已存在；`loadRoutes` 为占位（真实路由由 `router/index.ts` 装载，见 L38 注释） |
| `src/core/api/http.ts` | `ErrorResponse` 契约 `{code,message,detail,request_id}` **L7-12**；`tokenStore`（localStorage）**L23-34**；统一客户端 `baseURL='/api/v1'`/`timeout=15000` **L36**；请求拦截 JWT 注入 **L38-42**；`refreshAccessToken` **L46-53**；响应拦截器 **L55-90**；401 静默刷新（仅一次，失败 `clear()` + 跳 `/auth/login`）**L71-84** | 契约映射与 401 刷新基座已具备；403 目前走统一 `ElMessage.error`（无页面级规范） |
| `src/core/api/auth.ts` | `AuthUser`/`ModuleInfo` 契约 **L6-22**；`parseOidcHash` **L25-31**；`authApi.login/me` **L33-48**；`modulesApi.list`（`/modules`）**L50-54** | 登录/OIDC 解析/模块清单 API 已具备 |
| `src/core/api/*.ts`（6 个） | `auth.ts` / `dps.ts` / `gateway.ts` / `http.ts` / `llm.ts` / `rag.ts` | 六个 API 客户端覆盖身份、画像、网关、会话底层、编排、知识面 |
| `src/core/layouts/AppLayout.vue` | 统一壳：侧边模块导航 `menuItems`（仪表盘/租户管理 + `registry.enabledModules`）**L59-68**；顶栏用户/登出 **L25-32**；响应式折叠 **L77-85** | 顶层统一壳已承载模块导航 |
| `src/core/layouts/ModuleLayout.vue` | 模块内二级导航：水平 `el-menu` 由 `route.meta.navItems` 分组渲染 **L1-32** | 模块内导航由 navItems 驱动（与统一壳并存的层级/上下文来源） |
| `src/core/stores/` | `auth.ts` / `moduleRegistry.ts` / `ui.ts` | 身份态、模块注册、UI 态三类 store |

**模块与页面（`src/modules/`、`src/pages/`）**

| 模块 | 页面数 | 路由/导航入口 | 说明 |
|------|-------|--------------|------|
| `openllm`（OpenLLM 编排面） | **37** | `modules/openllm/index.ts`：`routes` **L7-51**、`navItems` **L53-106** | 含 `GenericPage.vue` 占位页；P2-3（UI-E2E #3）补注册菜单指向缺失子路由 **L47-50** |
| `knowledge`（OpenRAG 知识面） | **7** | `modules/knowledge/index.ts`（26 行） | 含 `ChatView.vue` 对话关键页 |
| `memory`（OpenMemory 记忆面） | **10** | `modules/memory/index.ts`（31 行） | 记忆关键页（list/search/sessions 等） |
| `portrait`（DPS 画像面） | **10** | `modules/portrait/index.ts`（38 行） | 画像关键页（list/detail/search/overview 等） |
| `gateway`（统一网关管理） | **2** | `modules/gateway/index.ts`（20 行） | 服务列表 + 聚合测试 |
| **合计** | **66** | 5 模块 | 各模块 `index.ts` 均导出 `routes` + `navItems` |
| 静态页 `src/pages/` | 4 | `Dashboard.vue`(50) / `Login.vue`(73) / `OidcCallback.vue`(60) / `SystemTenants.vue`(192) | 仪表盘/登录/OIDC 回调/租户管理 |

**测试（`tests/`，7 个 vitest spec，合计 573 行）**

| 文件 | 行数 | 覆盖要点 |
|------|------|---------|
| `tests/core.spec.ts` | 80 | 核心（router/store 基础） |
| `tests/core-extra.spec.ts` | 124 | 核心补充 |
| `tests/http.spec.ts` | 127 | 统一客户端（JWT 注入/401 刷新/契约映射） |
| `tests/gateway-api.spec.ts` | 83 | 网关 API |
| `tests/module-pages.spec.ts` | 52 | 模块页面挂载 |
| `tests/oidc-auth.spec.ts` | 23 | OIDC 回调解析 |
| `tests/portrait-list-error.spec.ts` | 84 | 画像列表错误态回归（ISSUE-002） |

**构建与发布（脚本/部署示例）**

| 文件 | 现状（实证） | 证据 |
|------|-------------|------|
| `scripts/build_release.ps1` | v1.2.0；`dist` → **`dist-v1.2.0`** 版本目录（保留上一版本用于回滚）；门禁前置 **Lint 0 + 测试 100% + 覆盖率 ≥80%** → build → 版本目录 | `scripts/build_release.ps1:5,7-14,20-24` |
| `nginx.conf.example` | 同域部署：`/ui/` 静态（alias dist + `try_files` + 1h 缓存）**L9-14**；`/api/` 反代 `127.0.0.1:8000`（含 `Authorization` 透传、`proxy_buffering off`、`proxy_read_timeout 300s`）**L17-27**；`/` → 301 `/ui/` **L30** | `nginx.conf.example:9-30` |
| 覆盖率门禁 | 脚本内为 **≥80%**（对齐 `package.json` 的 `test:coverage`） | `scripts/build_release.ps1:7,13-14` |

> **未被 FE-1/FE-2 覆盖的现状缺口**：`mountModuleRoutes` 仅在 `registry.initialized` 首次为真时挂载一次（`router/index.ts:76-84`）；`loadRoutes` 为占位未实现懒挂载（`moduleRegistry.ts:34-41`）；模块内导航与统一壳的层级关系与「模块内导航覆盖」问题尚未收口（见 §2.2/§2.4）。

### 2.2 FE-1/FE-2 已完成的证据与缺口

| 项 | 内容 | 完成证据（实证） | S6 缺口 |
|----|------|-----------------|---------|
| **FE-1 唯一入口** | 前端唯一经 OpenBase 入口；模块路由告警清零 | `staticRoutes` + `moduleRouteLoaders` 统一装载（`router/index.ts:7-37`）；`beforeEach` 权限门（`L67-94`）；父路由告警修复注记（`L52-53`） | 统一壳与模块内导航的「覆盖」问题未收口（FE-3）；路由告警需在 S6 全量复验 |
| **FE-2 画像数据面** | P1-1 修复后画像 list/detail/overview 已通 | portrait 模块 10 页；`dps.ts` API；`portrait-list-error.spec.ts` 错误态回归（84 行，含「点击重试」与 KPI 独立降级） | 画像关键页需在 R1 隔离收口后按「跨域为空/403」重跑（FE-R1-1）；记忆/知识关键页同批回归 |
| 模块挂载 | 依后端 `/modules` 与权限动态挂载 | `moduleRegistry.init`（`L21-29`）；`modulesApi.list`（`auth.ts:50-54`） | 需补「禁用模块不可达/无权模块回 /dashboard」的端到端断言（FE-3） |
| 登录态/吊销 | 401 静默刷新基座 | `http.ts:71-84`；`OidcCallback.vue:30-42`；`oidc-auth.spec.ts`（23 行） | token 失效跳登录、401/403 无白屏、吊销阻断呈现需全量回归（FE-R1-2） |

### 2.3 各子系统 frontend 冻结现状与待改造点

**冻结现状（只读，引用放行清单 v1.0.4 结论）**

- 四仓后端均**未**以 `StaticFiles` 等方式挂载 frontend 产物（放行清单 v1.0.4 §1.5/§2.5/§3.3/§4.5）；四仓分清单均**未**将 `frontend/` 列入 A 类联调产物（误列 A 类 0 项）。
- 各仓 `frontend/` 文件规模与在途改动：OpenMemory（59 文件、在途 8 项已归 B 类）、OpenLLM（214 文件）、DPS（63 文件）、OpenRAG（125 文件）（放行清单 v1.0.4 各仓小节注记）。

**仍「在构建/发布子系统前端」的待改造点（3 处，覆盖 4 仓；只读盘点，S6 内不改动其仓文件）**

| # | 仓 | 待改造点（文件:行号） | 现状语义 | S6 处置归属 |
|---|----|----------------------|---------|------------|
| **改造点 1** | **OpenMemory** | `deploy/nginx/conf.d/openmemory.conf:90`（`root /app/frontend/dist;`）、`:93`（`location / { try_files $uri $uri/ /index.html; }`） | 运行态以 SPA 方式承载子系统前端产物 | S6-T1（冻结/停止承载；前端面改由 openbase-ui 经 `/ui/` 提供） |
| **改造点 2** | **OpenLLM** | `docker-compose.yml:141-172`（`frontend` 服务：`build.context ./frontend` + 热加载卷）；`docker-compose.prod.yml:19`（`./frontend/dist:/usr/share/nginx/html:ro`）；`frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` | 开发/生产均构建并服务子系统前端 | S6-T1（不再构建/发布；不再挂载产物） |
| **改造点 3** | **DPS + OpenRAG（CI 构建链）** | DPS `.github/workflows/ci.yml`（前端三段：Lint `L68-79`、Coverage `L114-125`、Build `L164-195`、E2E setup `L213-218`；文件共 212 行）；OpenRAG `.github/workflows/frontend-ci.yml`（`paths: ['frontend/**']`、pnpm `lint/test/build/audit` + Playwright，共 62 行） | CI 仍对子系统前端执行 lint/test/build/e2e | S6-T1（CI 收敛口径：随 `frontend/` 冻结停用/移除相关 job；**具体改动在对应子系统仓后续批次执行**，S6 仅产出收口口径与登记） |

> **口径说明**：本方案按「3 处」登记（运行时静态挂载/服务 2 处 = OpenMemory + OpenLLM；CI 构建链 1 处 = DPS + OpenRAG 两仓合并登记），逐仓文件与行号见附录 C。所有改造点均为**只读盘点**；其代码/CI 改动归属对应子系统仓，S6 内只做口径收口与台账登记（Q-FE-1）。

### 2.4 差距总表（FE-JT 任务 → 现状 → S6 动作）

| 任务/卡 | 现状（实证） | 差距 | S6 动作 | 验收断言 |
|---------|-------------|------|---------|---------|
| 统一前端唯一维护面（范围定案） | openbase-ui 已入库 107 文件；四仓 frontend 冻结 | 3 处仍构建/发布；冻结声明未在前端侧落地复核 | S6-T1 | S6-T1-1~4 |
| **FE-3 模块导航壳**（OB-10/UI-E2E P3，JT v1.3.0/R4） | 顶层壳 AppLayout + 模块内 ModuleLayout 并存；存在「模块内导航覆盖」问题（OB-10 登记）；`loadRoutes` 占位 | 导航层级/上下文一致性未收口；权限驱动与菜单一致性缺端到端断言 | S6-T2 | S6-T2-1~4 |
| **FE-R1-1 UI 隔离回归**（JT v1.0.0/R1，配合 RA-06） | FE-2 画像数据面已通；记忆/知识关键页未按 R1 隔离口径回归 | 跨域呈现（空/403）无规范与回归 | S6-T3 | S6-T3-1~4 |
| **FE-R1-2 登录态/吊销回归**（JT v1.0.0/R1） | 401 刷新基座 + OIDC 回调已具备 | token 失效跳登录/401·403 无白屏/吊销阻断呈现缺全量回归 | S6-T4 | S6-T4-1~4 |
| **L3-2 贯通冒烟**（规划 §3 统一段门禁） | 另四段 L3-2 已完成；统一前端侧未执行 | 统一前端 → gateway → 子系统端到端未贯通验证 | S6-T5 | S6-T5-1~3 |
| 段门禁与台账回写 | FE-JT 台账 v1.0.0(R1)/v1.3.0(R4) 待回写；清点/放行清单待同步 | 门禁与台账未收口 | S6-T6 | S6-T6-1~3 |

> 覆盖结论：规划 v1.3.1 S6 段定义（FE-3 + FE-R1-1/2 + L3-2）+ JT 归集 v1.2.0 §3.6 FE-JT 全部任务均唯一入本方案任务（§3.3），无游离任务、不重复 S2-S5 侧工作。

---

## 3. 范围与定案

### 3.1 范围

**本段范围内（OpenBase 仓 `openbase-ui/`）**：统一前端壳与导航（FE-3）、关键页隔离/登录态回归（FE-R1-1/2）、统一前端侧 L3-2 贯通冒烟、段门禁聚合与台账回写，以及前端发布形态（`dist-vX.Y.Z` + nginx 同域 `/ui/`）确认。

**本段范围外（仅口径收口与登记，不改动他仓文件）**：DPS/OpenLLM/OpenMemory/OpenRAG 的 `frontend/` 目录及其 CI/部署配置（§2.3 三处改造点）；S7 终验项（L3-1/L2-1/L2-2/RA-06 终验/K07 终验）；各子系统后端语义。

**实施主线**：S6-T1（现状与边界收口，先铺）→ S6-T2（FE-3 导航壳）→ S6-T3/S6-T4（FE-R1-1/2 回归，可并行）→ S6-T5（L3-2 贯通冒烟）→ S6-T6（段门禁与台账回写，聚合）。

### 3.2 Q-FE 定案建议（Q-FE-1~Q-FE-6 建议定案；Q-FE-7/8 新增项见 §9，全部待人工批准）

| # | 事项 | 建议定案 | 理由/依据 | 状态 |
|---|------|---------|----------|------|
| **Q-FE-1** | 子系统前端冻结处置口径（含 3 处改造点归属） | **保留目录不删除 + 不再构建/发布 + 后端不再挂载产物**；3 处改造点（§2.3）归属对应子系统仓的后续批次执行，S6 仅产出**收口口径与登记**（本方案 + 放行清单 §0 红线第 5 条 + 清点总清单 §1.4），不将 `frontend/` 改动纳入任何联调提交批 | 规划 v1.3.1 / JT 归集 v1.2.0「统一前端定案」；放行清单 v1.0.4 §0-5；清点总清单 §1.4 | 建议 ✅ |
| **Q-FE-2** | 统一前端承载版本与发布形态 | 统一前端以 **`dist-vX.Y.Z` 版本目录**承载（脚本已置 1.2.0，`build_release.ps1:5`），nginx **同域 `/ui/` 静态 + `/api/` 反代 + SSE `proxy_buffering off`**（`nginx.conf.example:9-30`）；统一前端产品版本线与 OpenBase 仓版本线**解耦**（前端版本可独立递增），与 JT 线以提交号桥接 | 升级路线规划 R4「前端导航壳」；JT 归集 §1「JT 线独立于产品版本，以提交号桥接」 | 建议 ✅（S6 承载版本号口径见 Q-FE-6/§9） |
| **Q-FE-3** | FE-R1-1/2 与 RA-06 的配合门禁点与跨域呈现规范 | **配合点在 R1 收官门禁**：FE-R1-1（UI 隔离回归）与 FE-R1-2（登录态/吊销回归）作为 RA-06 门禁的**前端侧验收面**；跨域呈现规范统一为**为空 / 403 提示（无 500、无白屏）**；401 → 静默刷新（仅一次）失败则 `clear()` + 跳 `/auth/login`；403 → 页面级提示，不触发刷新风暴 | JT 归集 §3.6（FE-R1-1/2 联动 RA-06）、§4-2；身份最小集 §12.1（跨域 403/404）、§12.2（吊销即时性）；`http.ts:71-84` | 建议 ✅ |
| **Q-FE-4** | UI-E2E 工具与范围（现有 vitest spec 与是否引入 Playwright） | **分层**：① 组件/单元回归沿用现有 **vitest 7 spec**（`package.json:11-12`，保持覆盖率门禁）；② **关键页 PASS 由浏览器级 UI-E2E 承载**——是否引入 Playwright 作为 S6 E2E 引擎待设计阶段定案（建议引入，用于「关键页 PASS + 跨域空/403 + 无白屏」可观测断言）；关键页清单：**画像 / 对话 / 知识 / 记忆** | 规划 v1.3.1 §3 UI-E2E 门禁；升级路线规划 R4「UI-E2E 全模块 PASS」；DT-14 走查产物经验（`dogfood-output/`） | 建议 ✅（工具最终选型见 §9） |
| **Q-FE-5** | L3-2 前端侧门禁口径 | L3-2 = **经 OpenBase 受信通道（gateway/proxy，来源标识符合协议头规范）端到端**：统一前端 → OpenBase gateway → 子系统（画像/记忆/知识/对话）；**关键页 PASS** 为通过标准；跨域/越权 → 空或 403；不新增旁路直连 | 规划 v1.3.1 §3（S2-S6 统一段门禁 L3-2）；冒烟清单 S5「主链路端到端（OpenBase 入口）」/S6「旁路与双链路一致性」；P2-1 §3 协议头规范 | 建议 ✅ |
| **Q-FE-6** | 与 S7 边界 | **S7 承接**：L3-1 Agent 端到端、L2-1 主备切换演练、L2-2 通道覆盖矩阵终验、RA-06 终验聚合、K07 终验、冒烟 S0-S6 聚合与会签；S6 **只产出前端侧回归与冒烟证据、不终验**；S6 承载版本号口径（Q-FE-2）与 S7 全链核验的接口在 §9 待评审 | 规划 v1.3.1 §3 S7 行/§5；JT 归集 §4-2 | 建议 ✅ |

### 3.3 任务分解总表（S6-T1~S6-T6）

| 任务 | 名称 | 落点（OpenBase 仓） | 验收断言 | 依赖 |
|------|------|--------------------|---------|------|
| **S6-T1** | 现状与边界收口（3 处改造点 + 后端不挂载确认 + 冻结声明落地） | 本方案；放行清单/清点清单口径同步；各子系统仓**只读** | S6-T1-1~4 | 无（先铺） |
| **S6-T2** | FE-3 模块导航壳（修复「模块内导航覆盖」+ 权限驱动模块挂载 + 导航一致性） | `openbase-ui/src/core/router/index.ts`、`src/core/layouts/AppLayout.vue`、`src/core/layouts/ModuleLayout.vue`、`src/core/stores/moduleRegistry.ts`、各模块 `index.ts` | S6-T2-1~4 | S6-T1 |
| **S6-T3** | FE-R1-1 UI 隔离回归（关键页数据正确 + 跨域呈现空/403） | `openbase-ui/src/modules/{portrait,memory,knowledge}/**`、`src/core/api/{dps,rag}.ts`、`tests/**`、UI-E2E 用例 | S6-T3-1~4 | S6-T2（导航可定位关键页） |
| **S6-T4** | FE-R1-2 登录态/吊销回归（token 失效跳登录、401/403 无白屏、OIDC 回调） | `src/core/api/http.ts`、`src/pages/{Login,OidcCallback}.vue`、`tests/{http,oidc-auth}.spec.ts`、UI-E2E 用例 | S6-T4-1~4 | S6-T2 |
| **S6-T5** | L3-2 贯通冒烟（统一前端 → gateway → 子系统，关键页 PASS） | 统一前端 + OpenBase 后端受信通道（运行态）；冒烟脚本/记录 | S6-T5-1~3 | S6-T3、S6-T4 |
| **S6-T6** | 段门禁与台账回写（UI-E2E 门禁 + FE-JT 台账 + 放行/清点清单同步 + evidence） | 本方案回写；JT 归集 §3.6；放行清单 §0/§5；清点总清单 §1.4/§5.5；`doc/test/**` | S6-T6-1~3 | S6-T1~T5 |

**任务间依赖**：T1 → T2 → {T3 ∥ T4} → T5 → T6；T3/T4 可在 T2 完成后并行；T6 为聚合收口，须待 T1~T5 全绿。

### 3.4 任务详述

#### S6-T1 现状与边界收口（3 处构建/部署改造 + 后端不挂载确认 + 冻结声明落地）

- **设计意图**：把「统一前端唯一维护面」从文档定案落到**可核验的边界口径**：统一前端只在 `OpenBase/openbase-ui` 维护；子系统 `frontend/` 冻结（保留不删、不再构建/发布、后端不再挂载产物）；3 处仍「在构建/发布子系统前端」的待改造点（§2.3）逐项登记归属与处置口径。
- **落点文件**：本方案 §2.3 与附录 C；放行清单 §0 通用红线第 5 条与各仓 frontend 冻结注记；清点总清单 §1.4；各子系统仓相关文件**仅只读引用行号**（`OpenMemory deploy/nginx/conf.d/openmemory.conf:90,93`；`OpenLLM docker-compose.yml:141-172`、`docker-compose.prod.yml:19`、`frontend/Dockerfile`、`frontend/nginx.conf`；`DPS .github/workflows/ci.yml`；`OpenRAG .github/workflows/frontend-ci.yml`）。
- **交付物**：统一前端口径核对表（唯一维护面 / 冻结矩阵 / 3 处改造点归属 / 后端不挂载确认）；冻结声明在本方案与相关清单同步登记。
- **验收断言**：§4 S6-T1-1~4。

#### S6-T2 FE-3 模块导航壳（修复「模块内导航覆盖」+ 权限驱动模块挂载 + 导航一致性）

- **设计意图**：修复 OB-10 登记的「模块页统一导航壳（当前被模块内导航覆盖问题）」，确立**顶层统一壳（AppLayout 侧边模块导航）+ 模块内二级导航（ModuleLayout 水平菜单）**的清晰层级与上下文；权限驱动模块挂载端到端可验（禁用/无权模块不可达）；导航与路由一致（消除 `No match → /dashboard` 丢上下文与 Vue Router 父路由告警）。
- **落点文件**：
  - `src/core/layouts/AppLayout.vue`（统一壳模块导航 `menuItems`，`L59-68`）；
  - `src/core/layouts/ModuleLayout.vue`（模块内导航由 `route.meta.navItems` 渲染，`L1-32`）；
  - `src/core/router/index.ts`（`mountModuleRoutes` 顶层挂载 `L45-65`；守卫与模块可匹配判定 `L67-94`；父路由告警修复注记 `L52-53`）；
  - `src/core/stores/moduleRegistry.ts`（`init` 权限过滤 `L21-29`；`enabledModules` `L18`；`loadRoutes` 占位 `L34-41` 的收敛或落地）；
  - 各模块 `index.ts`（`routes` 与 `navItems` 一致性，覆盖 5 模块）。
- **交付物**：导航壳层级规范（顶层/模块内）+ 权限驱动模块挂载端到端行为 + 路由/菜单一致性用例；「模块内导航覆盖」缺陷修复注记（回归用例）。
- **验收断言**：§4 S6-T2-1~4。

#### S6-T3 FE-R1-1 UI 隔离回归（关键页数据正确 + 跨域呈现空/403）

- **设计意图**：R1 隔离收口后，在统一前端执行画像/记忆/知识关键页数据正确性回归；跨域数据前端呈现统一为**为空 / 403 提示**（无 500、无白屏）；作为 RA-06 门禁的前端侧验收面。
- **落点文件**：`src/modules/portrait/pages/**`（画像 list/detail/overview）、`src/modules/memory/pages/**`（记忆 list/search/sessions）、`src/modules/knowledge/pages/**`（知识 list/detail/chat）；`src/core/api/dps.ts`、`src/core/api/rag.ts`；`tests/**`（组件回归）+ UI-E2E 用例。
- **缺陷回归锚点**：`tests/portrait-list-error.spec.ts`（画像列表错误态，84 行）为「错误可观测、非静默空白」的既有范式，S6 据此把**隔离语义**（空/403）纳入同类断言。
- **交付物**：关键页（画像/记忆/知识）数据正确性回归记录 + 跨域呈现规范与用例 + UI-E2E 证据。
- **验收断言**：§4 S6-T3-1~4。

#### S6-T4 FE-R1-2 登录态/吊销回归（token 失效跳登录、401/403 无白屏、OIDC 回调）

- **设计意图**：回归登录态与吊销语义在前端的呈现——token 失效后正确跳登录；401/403 处理无白屏；OIDC 回调链路完整；deactivated/suspended 主体（U1 吊销语义）在前端呈现阻断而非空白。
- **落点文件**：`src/core/api/http.ts`（401 静默刷新与失败收敛 `L71-84`；`ErrorResponse` 契约 `L7-12`；请求 JWT 注入 `L38-42`）、`src/pages/Login.vue`、`src/pages/OidcCallback.vue`（fragment 解析与错误页 `L30-42`）、`src/core/api/auth.ts`（`parseOidcHash` `L25-31`）、`tests/http.spec.ts`（127 行）、`tests/oidc-auth.spec.ts`（23 行）+ UI-E2E 用例。
- **语义锚**：U1 设计草案（token 失效/deactivated 阻断/OIDC 回调，§5 吊销即时性、§6 签发闭环）；身份最小集 §12.2（吊销即时性验收要点：被停用主体任何入口请求返回 401/403）。
- **交付物**：登录态/吊销前端回归记录 + 无白屏用例 + OIDC 回调回归。
- **验收断言**：§4 S6-T4-1~4。

#### S6-T5 L3-2 贯通冒烟（统一前端 → gateway → 子系统，关键页 PASS）

- **设计意图**：段末执行统一前端侧 L3-2 端到端贯通冒烟——经 OpenBase 受信通道（gateway/proxy，来源标识符合协议头规范）到各子系统，关键页（画像/对话/知识/记忆）PASS；跨域/越权呈现空或 403，不新增旁路直连。
- **落点**：运行态统一前端（`openbase-ui` 构建产物 `dist-vX.Y.Z` 经 nginx `/ui/` 服务）+ OpenBase 后端受信通道；冒烟记录归档 `doc/test/**`（evidence 不得伪造，须为真实执行结果）。
- **交付物**：L3-2 贯通冒烟记录（关键页 PASS 清单 + 请求/响应证据 + 失败项处理）+ 与另四段 L3-2 结论的一致性核对。
- **验收断言**：§4 S6-T5-1~3。

#### S6-T6 段门禁与台账回写（UI-E2E 门禁 + FE-JT 台账 + 放行/清点清单同步 + evidence）

- **设计意图**：聚合 S6 段门禁（UI-E2E 关键页 PASS + FE-R1-1/2 回归通过 + FE-3 达成 + L3-2 冒烟通过 + 3 处改造闭环），回写 FE-JT 台账（JT v1.0.0/R1 与 v1.3.0/R4 行状态与提交号），同步放行清单与清点总清单口径，归档 evidence。
- **落点**：本方案（回写）；JT 归集 §3.6 FE-JT、§4-2 门禁聚合；放行清单 §0-5/§5（OpenBase 侧）；清点总清单 §1.4/§5.5；`doc/test/**`（测试/冒烟报告）。
- **交付物**：段门禁自检表（逐项结论）+ FE-JT 台账回写 + 清单同步 + evidence 索引。
- **验收断言**：§4 S6-T6-1~3。

---

## 4. 验收标准（逐任务断言式）

| ID | 验收断言（通过标准） | 归属 |
|----|----------------------|------|
| **S6-T1-1** | 统一前端唯一维护面口径落地：唯一维护面 = `OpenBase/openbase-ui`（`git ls-files openbase-ui` 实测 107 文件）；各子系统 `frontend/` 冻结声明（保留不删、不再构建/发布、后端不再挂载产物）在本方案与相关清单同步登记；3 处改造点（§2.3/附录 C）逐项登记归属仓与处置口径 | S6-T1 |
| **S6-T1-2** | 后端不挂载确认：OpenBase 主仓无 openbase-ui 产物（`dist-vX.Y.Z`）的 `StaticFiles`/`mount` 挂载（仅有 scaffold CLI 的目标目录引用 `openbase/cli/main.py:194`）；四仓后端亦无 frontend 产物挂载（引用放行清单 v1.0.4 结论，结论与实测一致） | S6-T1 |
| **S6-T1-3** | 发布形态确认：统一前端 `dist-vX.Y.Z` 版本目录 + nginx 同域 `/ui/` 静态 + `/api/` 反代 + SSE `proxy_buffering off` 口径确认（`nginx.conf.example:9-30`、`scripts/build_release.ps1:5,20-24`） | S6-T1 |
| **S6-T1-4** | `frontend/` 改动不进入联调提交面：核对放行清单 §0 通用红线第 5 条与清点总清单 §1.4 一致；S6 内不将任何子系统 `frontend/` 改动纳入提交批（归 B/C 类） | S6-T1 |
| **S6-T2-1** | FE-3「模块内导航覆盖」缺陷闭环：顶层统一壳（AppLayout）与模块内二级导航（ModuleLayout）层级清晰、模块上下文不丢失；缺陷复现用例在修复后全绿 | S6-T2 |
| **S6-T2-2** | 权限驱动模块挂载端到端：模块由后端 `/modules` 清单 + 权限过滤（`moduleRegistry.ts:21-29`）挂载；**禁用模块不出导航且不可达**；无权模块访问 → 回 `/dashboard`（`router/index.ts:86-92`） | S6-T2 |
| **S6-T2-3** | 导航一致性：统一壳模块项 `path = module.info.route_prefix`（`AppLayout.vue:59-68`）与模块路由可匹配；模块内 `navItems` 与模块 `routes` 一致（5 模块），无「菜单指向缺失路由 `No match → /dashboard` 丢上下文」 | S6-T2 |
| **S6-T2-4** | 路由告警清零：浏览器控制台 Vue Router warn = 0（含 `Parent route "" not found` 父路由告警，参考 `router/index.ts:52-53` 既有修复）；模块路由懒装载无失败（`T2` 回归用例） | S6-T2 |
| **S6-T3-1** | 画像关键页（portrait/DPS）数据正确：list/detail/overview 在 R1 隔离收口后返回本域正确数据；错误态可观测（沿用 `portrait-list-error.spec.ts` 范式：错误条 + 重试 + 非静默空白） | S6-T3 |
| **S6-T3-2** | 记忆关键页（memory/OpenMemory）数据正确：list/search/sessions 等关键页返回本域正确数据，隔离键过滤生效 | S6-T3 |
| **S6-T3-3** | 知识关键页（knowledge/OpenRAG）数据正确：list/detail/chat 等关键页返回本域正确数据，隔离键过滤生效 | S6-T3 |
| **S6-T3-4** | 跨域呈现规范：他域数据在前端呈现为**为空 / 403 提示**（无 500、无白屏、无静默误导空态）；该回归作为 RA-06 门禁前端侧验收面通过（对齐身份最小集 §12.1 跨域 403/404 语义） | S6-T3 |
| **S6-T4-1** | token 失效后正确跳登录：401 → 静默刷新（仅一次，`http.ts:71-84`）失败 → `tokenStore.clear()` + 跳 `/auth/login`，回跳 `redirect` 参数保留 | S6-T4 |
| **S6-T4-2** | 401/403 处理无白屏：403 走页面级提示（统一 `ErrorResponse` 契约 `{code,message,detail,request_id}` 映射），不触发刷新风暴、不整页空白；连续 401 不产生无限刷新循环 | S6-T4 |
| **S6-T4-3** | OIDC 回调链路回归：`#access_token` fragment 解析正确（`parseOidcHash`）；缺令牌 → 错误页 + 「返回登录页」；回调落 token 后经守卫 `loadMe` 正确进入目标页（`OidcCallback.vue:30-42`） | S6-T4 |
| **S6-T4-4** | 吊销语义前端呈现：suspended/deactivated 主体 token 失效 → 跳登录或阻断提示（非空白）；deactivated 主体数据面读被拒 → 空/403 呈现（对齐 U1 §5/§6 与身份最小集 §12.2：被停用主体任何入口 401/403） | S6-T4 |
| **S6-T5-1** | L3-2 贯通冒烟（统一前端 → OpenBase gateway → 子系统）经受信通道端到端连通；来源标识符合协议头规范（X-Proxy-Source 等），**无新增旁路直连** | S6-T5 |
| **S6-T5-2** | 关键页（画像/对话/知识/记忆）在统一前端内 PASS；与另四段 L3-2 结论一致 | S6-T5 |
| **S6-T5-3** | 越权/跨域端到端 → 空或 403（无 500、无白屏）；失败项如实记录（含挂起登记不阻断项），evidence 为真实执行结果 | S6-T5 |
| **S6-T6-1** | UI-E2E 段门禁 = 画像/对话/知识/记忆关键页 PASS（均在统一前端 openbase-ui 内执行） | S6-T6 |
| **S6-T6-2** | 段门禁聚合通过：FE-R1-1 回归通过 + FE-R1-2 回归通过 + FE-3 达成 + L3-2 冒烟通过 + 3 处改造闭环 | S6-T6 |
| **S6-T6-3** | 台账与清单回写：FE-JT 台账（JT v1.0.0/R1 与 v1.3.0/R4 行状态与提交号）回写；放行清单 §0-5/§5 与清点总清单 §1.4/§5.5 口径同步；evidence 归档；**hash 一律不得伪造**（未提交/未执行则如实登记「沙箱受限/未执行」） | S6-T6 |

**断言合计：22 条**（S6-T1：4 / S6-T2：4 / S6-T3：4 / S6-T4：4 / S6-T5：3 / S6-T6：3）。

**段门禁聚合**：S6-T1~S6-T6 断言全绿 + **S6 段门禁**（① UI-E2E 画像/对话/知识/记忆关键页 PASS；② FE-R1-1 UI 隔离回归通过；③ FE-R1-2 登录态/吊销回归通过；④ FE-3 模块导航壳达成；⑤ L3-2 贯通冒烟通过；⑥ 3 处改造闭环）+ FE-JT 台账回写与清单同步（§8）。

---

## 5. 非目标与边界

| 边界 | 说明 | 归属段 |
|------|------|--------|
| 各子系统独立前端维护 | 不维护 DPS/OpenLLM/OpenMemory/OpenRAG 的 `frontend/`（不新增功能、不构建/发布、不修复其缺陷）；其 3 处改造点由对应子系统仓后续批次执行，S6 仅口径收口与登记 | 各子系统仓（S6 范围外） |
| S7 终验项 | L3-1 Agent 端到端、L1-1 级联全链核验、L2-1 主备切换演练、L2-2 通道覆盖矩阵终验、RA-06 终验聚合、K07 终验、冒烟 S0-S6 聚合与会签——S6 只产出前端侧回归/冒烟证据，不终验 | S7 |
| 子系统后端语义 | 不改动各子系统后端业务语义与数据面实现；S6 仅做前端呈现与受信通道冒烟 | S1a~S5（已完成） |
| 统一身份/协议头实现 | U1/P2-1 已落地；S6 不重复实现（仅消费登录态/吊销 semantics 与受信通道口径） | S1a/S1b |
| 通道主备（Q-4） | L2-1 切换演练与 L2-2 终验在 S7；S6 冒烟以受信通道端到端为准，不设切换演练 | S4/S7 |
| deactivated 数据处置（Q-5=A） | 保留 + 全链阻断；purge 显式触发在 S1a/S7；S6 仅回归前端对阻断的呈现 | S1a/S7 |
| 关键页之外的模块 | 门禁聚焦画像/对话/知识/记忆四类关键页；OpenLLM 全模块 PASS 属 R4「UI-E2E 全模块」（可作 S6 增强项，见 §9） | S6/S7 |

---

## 6. 影响面与兼容

- **部署形态**：统一前端以 `dist-vX.Y.Z` 版本目录承载，nginx 同域 `/ui/` 提供服务、`/api/` 反代至 OpenBase 后端（`nginx.conf.example:9-30`）；版本目录切换即发布/回滚（`build_release.ps1:20-24`），对存量子系统部署无侵入（各子系统后端不改挂载）。
- **CI 收敛**：子系统前端 CI（DPS `.github/workflows/ci.yml` 前端三段 + OpenRAG `.github/workflows/frontend-ci.yml`）随 `frontend/` 冻结在对应仓后续批次收敛；S6 仅产出收敛口径，不影响 S6 段门禁执行（S6 门禁在统一前端侧执行）。
- **子系统前端冻结影响**：保留目录不删，历史可追溯；不再构建/发布，`frontend/` 改动不进入联调提交面（归 B/C 类，放行清单 §0-5）；接口契约面不依赖前端产物。
- **统一壳/导航变更影响**：`AppLayout.vue`/`ModuleLayout.vue`/`router/index.ts` 的调整影响所有模块的导航与路由；以「路由告警清零 + 权限门回归 + 关键页可达」用例兜底（S6-T2）。
- **http 客户端变更影响**：`http.ts` 401/403 行为调整影响所有 API 调用；以 `http.spec.ts`（127 行）+ UI-E2E 无白屏用例兜底（S6-T4）。
- **回滚**：前端回滚 = nginx `/ui/` 指回上一版本目录（`dist-vX.Y.Z`）；行为回滚 = 保留上一版本构建产物；不涉及数据库迁移与后端语义变更（`build_release.ps1:20-24`）。

---

## 7. 风险与依赖

| # | 风险/依赖 | 类型 | 影响 | 缓解/说明 |
|---|----------|------|------|----------|
| R-1 | **E2E 环境依赖**：关键页 PASS 需统一前端 + 后端 + nginx 运行态与真实数据 | 依赖 | 关键页断言无法在纯单测层完成 | S6-T2/T3/T4 以 vitest 组件层回归兜底；关键页 PASS 由浏览器级 UI-E2E 在受控环境执行（Q-FE-4） |
| R-2 | **OIDC/受信通道可用性**：OIDC 回调与受信通道冒烟依赖身份服务与网关可达 | 依赖 | S6-T4-3/S6-T5-1 阻塞 | 环境不可达时如实登记「环境待办/挂起不阻断」（对齐 S5 的 Pull 双签 PENDING 登记范式），不伪造结果 |
| R-3 | **子系统接口就绪度**：四段（S2-S5）已收官，但运行态接口契约仍需真实环境验证 | 依赖 | L3-2 冒烟失败 | 复用各段已移交的 L3-2 结论与冒烟脚本；失败项定位到子系统侧并登记（不阻断前端侧已达成项） |
| R-4 | **沙箱限制**：沙箱内仅允许提交 OpenBase 仓；无法自动执行多仓/浏览器级 E2E | 约束 | 3 处改造点无法在 S6 内直接落地；E2E 需用户协助 | 本方案只读盘点 + 口径收口；改造点归属对应仓；E2E 由用户在沙箱外/受控环境执行，结果如实登记（S6-T6-3） |
| R-5 | **「模块内导航覆盖」缺陷根因未完全定位**：OB-10 仅登记现象 | 技术 | FE-3 修复范围不确定 | S6-T2 先做缺陷复现（S6-T2-1），设计阶段定夺修复面；以「层级清晰 + 路由告警清零 + 权限门回归」为客观判据 |
| R-6 | **UI-E2E 工具未定**（vitest vs Playwright） | 决策 | 影响关键页 PASS 的可观测性 | Q-FE-4 建议分层：vitest 兜底组件回归，浏览器级 E2E 承载关键页 PASS；最终选型在设计阶段定案（§9） |
| R-7 | **断言计数与门禁口径一致性** | 质量 | 段门禁收口争议 | 22 条断言与段门禁 6 项一一映射（§4 聚合行），设计/测试阶段逐条登记 |

---

## 8. 里程碑与五步流程衔接

S6 段按五步流程执行（需求 → 设计 → 开发 → 测试 → 段门禁收口），每步强制「文档输出 + 内容核对 + 人工批准」，且调用项目角色管理规范与项目文档管理规范（用户规则）：

| 步骤 | 交付物 | 与上一步对比 | 门禁 |
|------|--------|-------------|------|
| Step 0/需求 | **本立项方案 v1.1.0**（[Approved]，2026-09-10 批准） | 回溯规划 v1.3.1 S6 段定义、JT 归集 v1.2.0 §3.6、清点/放行清单口径，覆盖无遗漏 | ✅ 立项评审人工批准（Q-FE-1~8 定案） |
| Step 1/设计 | 《S6-统一前端隔离展示与段门禁收口-设计草案 v1.0.0》（导航壳层级设计、跨域呈现规范、UI-E2E 用例设计、发布形态确认） | 与需求逐条对应（22 条断言 → 设计决策/落点） | 设计评审人工批准 |
| Step 2/开发 | 《S6-…-DevLogReport v1.0.0》（T1~T4 编码：导航壳、隔离回归支撑、登录态/吊销处理；含源码清单与改动行号） | 与设计逐条对应（实现一致） | 开发自检 + 人工批准 |
| Step 3/测试 | 《S6-…-测试报告 v1.0.0》（22 条断言逐条结果 + UI-E2E 关键页 PASS 证据 + L3-2 冒烟记录） | 回溯需求（22 断言）、设计、开发（覆盖） | 测试评审人工批准 |
| Step 4/段门禁收口 | 段门禁自检表 + FE-JT 台账回写 + 放行/清点清单同步 + evidence 归档 | 与测试报告对比验证 | **段门禁 = UI-E2E 关键页 PASS + FE-R1-1/2 回归通过 + FE-3 达成 + L3-2 冒烟通过 + 3 处改造闭环**，人工批准后 S6 收官、移交 S7 |

**里程碑映射**：S6 段内 FE-R1-1/FE-R1-2 对应 JT **v1.0.0 (R1)**（验证回归）；FE-3 对应 JT **v1.3.0 (R4)**（体验收尾）。段门禁批准后回写 JT 归集 §3.6 两行状态与提交号。

---

## 9. 遗留待评审问题（Q-FE 清单状态与待定项）

| # | 问题 | 状态 | 建议/待定 |
|---|------|------|----------|
| Q-FE-1 | 子系统前端冻结处置口径（含 3 处改造点归属） | 建议已给（§3.2） | **待人工批准**；子问题：**是否删除子系统 `frontend/` 目录**——建议「保留不删」（历史可追溯、降低他仓破坏面），删除属子系统仓独立决策 |
| Q-FE-2 | 统一前端承载版本与发布形态 | 建议已给（§3.2） | **待人工批准**；子问题：**S6 承载版本号口径**——统一前端 `package.json` 现为 1.2.0，S6 是否升版本、以及是否与 OpenBase 仓版本线建立映射，建议在 Step 1 定案 |
| Q-FE-3 | FE-R1-1/2 与 RA-06 配合门禁点与跨域呈现规范 | 建议已给（§3.2） | **待人工批准**；跨域「空 vs 403」的细分判据（数据面为空/接口 403）待 Step 1 明确 |
| Q-FE-4 | UI-E2E 工具与范围 | 建议已给（§3.2） | **待人工批准**；**E2E 工具最终选型**（vitest + Playwright 组合 或 仅 vitest 增强）待 Step 1 定案；关键页清单（画像/对话/知识/记忆）确认为下限，是否含 OpenLLM 全模块待定 |
| Q-FE-5 | L3-2 前端侧门禁口径 | 建议已给（§3.2） | **待人工批准**；冒烟是否要求真实 HTTP 双签、失败项挂起登记口径对齐 S5 范式 |
| Q-FE-6 | 与 S7 边界 | 建议已给（§3.2） | **待人工批准**；S6→S7 移交接口（证据/台账）形式待定 |
| Q-FE-7 | 前端覆盖率门禁口径 | **待评审（新增）** | `build_release.ps1:7` 门禁为「覆盖率 ≥80%」，AGENTS.md 测试规则要求「新增代码覆盖率 ≥90%」——两者口径需对齐（建议前端沿用 80% 或按新代码 90% 折中，Step 1 定案） |
| Q-FE-8 | 表格中 S6 承载版本与 JT 版本的双向标注 | **待评审（新增）** | 是否需要为统一前端建立独立 JT 版本线（如 `FE-JT vX.Y.Z`）或沿用 §3.6 行口径，Step 1 定案 |

> Q-FE-1~6 为承接上游「统一前端定案」的定案建议，状态均为「建议 ✅ / 待人工批准」；Q-FE-7/8 为本方案新识别项。全部问题在立项评审时一次性裁定，结论登记于设计草案 §1（不可再议），避免跨步反复。

---

## 10. 附录

### 附录 A：引用清单

**上游依据（OpenBase 仓）**
1. `OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md`（内部 v1.3.1；§2 阶段总表 S6 行、§3 S6 前端段/统一前端定案、§5 任务分布核对表）
2. `OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md`（内部 v1.2.0；§1 归集规则、§2 版本归集总览前端行、§3.6 前端/统一入口 FE-JT、§4 执行与版本管理规则、§5 Q-C）
3. `doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md`（内部 v1.0.2；§1.4 统一前端口径与清点影响、§5.5 S5 门禁批准登记、五仓清点口径）
4. `doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`（内部 v1.0.5；§0 通用红线第 5 条统一前端口径、各仓 frontend 冻结注记、§3.3 S5 门禁登记）
5. `OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md`（OB-10 前端壳登记行、§3.6 前端/统一入口、§4 R4 体验与收尾行）
6. `OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md`（§9.3 OB-10 外移说明、§11.1 落点清单台账登记）
7. `OpenBase-U1-统一身份收口设计草案-v1.0.0.md`（§5 token 吊销即时性、§6 login/refresh/OIDC 签发闭环、§8 L1-1 事件契约、§10 接口清单）
8. `OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md`（内部 v1.3.0；§4.2 隔离键 tenant_code、§12.1 R-H1-1/2 入口同构与跨域 403、§12.2 R-H2 吊销即时性、§12.9 R-L2-1）
9. `OpenBase-真实联调冒烟清单-v1.0.0.md`（内部 v1.1.0；§3.5 S5 主链路端到端（OpenBase 入口）、§3.6 S6 旁路与双链路一致性）

**先例立项范式（各子系统仓）**
10. `D:\Trae CN\myproject\Dev\DPS\DPS-S5-画像数据隔离与身份接入收口-立项方案-v1.0.0.md`
11. `D:\Trae CN\myproject\Dev\OpenLLM\OpenLLM-S4-通道B全面主用与身份接入收口立项方案-v1.0.0.md`
12. `OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md` / `OpenMemory-S2-过滤行控与身份接入立项方案-v1.0.0.md`（引用）

**只读盘点对象（子系统仓，S6 不改动）**
13. `D:\Trae CN\myproject\Dev\OpenMemory\deploy\nginx\conf.d\openmemory.conf`
14. `D:\Trae CN\myproject\Dev\OpenLLM\docker-compose.yml` / `docker-compose.prod.yml` / `frontend/Dockerfile` / `frontend/nginx.conf`
15. `D:\Trae CN\myproject\Dev\DPS\.github\workflows\ci.yml`
16. `D:\Trae CN\myproject\Dev\OpenRAG\.github\workflows\frontend-ci.yml`

### 附录 B：openbase-ui 文件与模块页统计

| 项 | 计数 | 备注 |
|----|------|------|
| `git ls-files openbase-ui` | **107** | 已入库跟踪 |
| `src/` 文件 | **90** | core 13 + modules 71 + pages 4 + 根 2（App.vue/main.ts） |
| `src/core/api/*.ts` | **6** | auth / dps / gateway / http / llm / rag |
| `src/core/layouts/*.vue` | 2 | AppLayout(94) / ModuleLayout(45) |
| `src/core/stores/*.ts` | 3 | auth / moduleRegistry / ui |
| 模块数 | **5** | openllm / knowledge / memory / portrait / gateway |
| 模块页面合计 | **66** | openllm 37 + knowledge 7 + memory 10 + portrait 10 + gateway 2 |
| 静态页 `src/pages/` | 4 | Dashboard(50) / Login(73) / OidcCallback(60) / SystemTenants(192) |
| 模块 `index.ts` 行数 | — | openllm 106 / portrait 38 / memory 31 / knowledge 26 / gateway 20 |
| `tests/*.spec.ts` | **7** | 合计 573 行（core 80 / core-extra 124 / http 127 / gateway-api 83 / module-pages 52 / oidc-auth 23 / portrait-list-error 84） |
| 发布脚本 | 1 | `scripts/build_release.ps1`（v1.2.0，`dist-v1.2.0`） |
| 部署示例 | 1 | `nginx.conf.example`（31 行） |

### 附录 C：3 处待改造点行号（只读盘点）

| 改造点 | 仓 | 文件:行号 | 原文语义 |
|--------|----|----------|---------|
| 1 | OpenMemory | `deploy/nginx/conf.d/openmemory.conf:90` | `root /app/frontend/dist;`（以子系统前端产物为站点根） |
| 1 | OpenMemory | `deploy/nginx/conf.d/openmemory.conf:93` | `location / { try_files $uri $uri/ /index.html; }`（SPA 兜底） |
| 2 | OpenLLM | `docker-compose.yml:141-172` | `frontend` 服务：`build.context ./frontend`、端口 3000/5173、源码卷热加载（开发态构建/服务前端） |
| 2 | OpenLLM | `docker-compose.prod.yml:19` | `./frontend/dist:/usr/share/nginx/html:ro`（生产态挂载子系统前端产物） |
| 2 | OpenLLM | `frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` | 子系统前端镜像构建与 nginx 配置 |
| 3 | DPS | `.github/workflows/ci.yml`（共 212 行） | 前端 Lint `L68-79`；前端 Coverage `L114-125`；前端 Build（Vite 主包 ≤400KB gzip 门禁）`L164-195`；E2E Setup Node `L213-218` |
| 3 | OpenRAG | `.github/workflows/frontend-ci.yml`（共 62 行） | `paths: ['frontend/**']`；pnpm `lint/format:check/tsc/test/build/audit`；Playwright `e2e/smoke.spec.ts` |

> 说明：改造点 3 为「子系统前端 CI 构建链」，合并登记 DPS 与 OpenRAG 两仓（合计 3 处 / 4 仓）。所有行号为 2026-09-10 只读实测值；S6 内**不修改**上述任何文件。

---

> **文档结束**。本方案为 S6 段「需求」环节交付物；**已于 2026-09-10 立项评审人工批准（内部 v1.1.0，[Approved]）**，Q-FE-1~8 定案登记见《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md》§1.1，现进入 Step 1 设计。


