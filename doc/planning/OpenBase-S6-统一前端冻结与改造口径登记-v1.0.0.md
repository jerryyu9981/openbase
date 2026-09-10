# OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S6-T1-FRONTEND-FREEZE-v1.0.0 |
| 版本 | v1.0.3 |
| 状态 | [Approved]（**v1.0.x 修订：S6 段门禁批准（挂起口径）**——2026-09-11 S6 段门禁人工批准，本登记随批准生效；**口径闭环已批准 ✅**；**物理闭环 B5 PENDING** 交各子系统对话 / S7 按 Q-S6-D7 复核） |
| 日期 | 2026-09-10 |
| 作者 | AI（S6 批次 1/2 开发会话，沙箱内只读盘点 + 口径登记 + 发布形态参数化） |
| 文档主题 | S6 段 **T1 边界收口**口径登记：统一前端唯一维护面声明、四仓 `frontend/` 冻结声明文案与落点、3 处待改造点逐条登记（四元组 + 状态）、口径闭环与物理闭环两级判定（Q-S6-D7） |
| 上游依据 | ①《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》（OB-S6-DESIGN-v1.0.0，[Draft]）§1.1 Q-FE-1/Q-FE-2b、§3.4、§4.1（S6-T1-1~4）、§6.2/§6.3、§7 R-3、§10.2 Q-S6-D1/Q-S6-D5/Q-S6-D7、附录 D；②《OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0》（内部 v1.1.0，[Approved]，2026-09-10）§2.3/§2.4/§4；③《OpenBase-联调产物清点核对总清单-v1.0.0》（OB-INTG-CLEARANCE-v1.0.0）§1.3/§1.4；④《OpenBase-多系统联调-跨仓提交放行清单-v1.0.0》（OB-INTG-CROSSREPO-RELEASE-v1.0.0）§0 通用红线第 5 条 |
| 适用范围 | S6 段 T1 的**口径与登记面**。本文档**只登记不改动**：对 DPS / OpenLLM / OpenMemory / OpenRAG 四仓的 `frontend/` 目录与 CI/部署配置仅做只读盘点与处置口径登记，**S6 内不改动任何子系统仓文件**（Q-FE-1）；四仓的物理改造动作归属其各自后续批次 |
| 证据面 | 沙箱内可执行面（A 系列）：只读盘点（grep/Read）、静态断言测试 `tests/test_s6_t1_frontend_boundary.py`、OpenBase 仓 git 提交；非沙箱复核面（B5）：四仓物理改造与 CI 收敛，**PENDING 交 S7 复核**（Q-S6-D7） |
| 纪律 | 所有未在本环境真实执行的动作一律标注 `PENDING（未执行）`，**禁止以「预期通过」代替证据，禁止编造 hash**（对齐设计草案 §1.4 纪律与 R-4） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-10 | AI（S6 批次 1 开发会话） | 初始版本：S6-T1-1 交付物。含 §1 统一前端唯一维护面声明；§2 四仓 `frontend/` 冻结统一文案；§3 3 处改造点逐条登记（归属仓 / 证据行号 / 建议动作 / 状态）；§4 各仓冻结声明落点待执行清单（Q-S6-D5）；§5 口径闭环与物理闭环两级判定（Q-S6-D7）；§6 核验命令与证据；§7 遗留与边界 |
| v1.0.1 | 2026-09-10 | AI（S6 批次 2 开发会话） | 补做并闭环 §7-1 遗留的 **S6-T1-3「发布形态」四小项**：① `scripts/build_release.ps1` 版本目录参数化（由 `openbase-ui/package.json.version` 派生 `dist-v$Version`，消除 `dist-v1.2.0` 硬编码，保留 Lint/测试/覆盖率门禁）；② `.gitignore` 增补 `dist-v*`（实测 `git check-ignore` 命中）；③ `package.json`/`package-lock.json` 版本 1.2.0 → **1.3.0**（S6 承载版本）；④ `nginx.conf.example` 同域 `/ui/`（alias 指向版本目录）+ `/api/` 反代 + SSE `proxy_buffering off` 口径核对一致。新增 §8 参数化片段与忽略规则证据、§9 批次 2 硬门禁实测值（覆盖率已由 51.52% 提升至 96.37% 达标） |
| v1.0.2 | 2026-09-10 | AI（S6 批次 4 开发会话） | 追加 **§10 S6 批次 4（T5/T6）结论登记**：① T5 L3-2 贯通冒烟基座落地（`playwright.config.ts` + `tests/e2e/*` 9 页 + Q-S6-D6 同源 fixture + 零依赖 `scripts/smoke_l3_2_ui.mjs` + 静态旁路检查），沙箱可执行面通过、真实双签与浏览器级 PASS **PENDING（B1/B2）**；② T6 段门禁聚合与台账回写（evidence `doc/test/evidence/s6/**`）；③ **3 处改造闭环两级判定复核**：口径闭环 ✅ 保持、物理闭环 **PENDING**（B5，交 S7 按 Q-S6-D7）；④ 新增批次 4 硬门禁实测值（lint 0 / 137 tests / 覆盖率 97.08-90-88.46-97.08 / pytest S6-T1 9 passed）。**仅追加登记，不改变 §1~§9 既有口径与四仓处置结论** |
| v1.0.3 | 2026-09-11 | 项目负责人（段门禁人工批准）/ AI（批准注记回写） | **v1.0.x 修订：S6 段门禁批准（挂起口径）**。状态 [Draft] → **[Approved]**；批准口径（统一逐字登记）：`2026-09-11 S6 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认；前端侧门禁全绿（覆盖率 97.08/90/88.46/97.08 达标、lint 0 problem、FE-R1-1/FE-R1-2 前端侧通过、FE-3 达成、3 处改造口径闭环）；UI-E2E 关键页 PASS（B1）与 L3-2 真实受信通道双签（B2）按挂起口径处理（PENDING 登记不阻断本次批准，交非沙箱环境复核）；遗留=无阻断项`。**3 处改造两级闭环判定**：**口径闭环 ✅ 已批准**；**物理闭环 PENDING（B5）** 交各子系统对话与 S7 按 Q-S6-D7 复核。本文档 §1~§10 口径与四仓处置结论**不变**，仅回写状态/内部版本与批准注记 |

---

## §1 统一前端唯一维护面声明（S6-T1-1 ①）

**声明**：自 2026-09-10 S6 段起，本项目前端**唯一维护面 = `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`**（Git 仓在 OpenBase 项目目录下、已入库跟踪）。前端需求变更、缺陷修复、依赖升级、构建与发布形态调整，**一律且仅在 `openbase-ui/` 内进行**。

| 项 | 口径 | 核验命令 |
|----|------|---------|
| 唯一维护面 | `OpenBase/openbase-ui` | `git ls-files openbase-ui`（2026-09-10 基线实测 **107** 个文件） |
| 唯一提交面 | OpenBase 仓 `openbase-ui/**` | `git status --porcelain -uall` 白名单对照（S6-T1-4） |
| 唯一交付形态 | `dist-vX.Y.Z` 版本目录 + nginx 同域 `/ui/` 静态 + `/api/` 反代（SSE `proxy_buffering off`） | `openbase-ui/nginx.conf.example:9-30`；Q-FE-2b（发布形态参数化归属后续批次，见 §7） |
| 与 JT 线关系 | 前端产品版本线与 OpenBase 仓版本线解耦，与 JT 线以**提交号**桥接（Q-FE-8） | 设计草案 §4.6 S6-T6-3 |
| 计数口径说明 | §1.4 的 **107** 为 2026-09-10 清点时点基线值；S6 自身新增文件（如本批次静态断言测试与前端侧冻结声明）会使 `git ls-files openbase-ui` 计数**按新增数递增**，该增量属 S6 提交面的**显式登记项**，**不改变清点总清单 §1.1 五仓对照表的任何 A/B/C 计数与归类** | `git ls-files openbase-ui \| Measure-Object -Line` |

**三处表述一致性**（设计要求：同一条计数口径，表述必须一致）：

| 表述落点 | 现行文本要点 | 状态 |
|---------|-------------|------|
| 本登记文档 §1 | 唯一维护面 = `OpenBase/openbase-ui`；基线 107 | ✅ 本批次落地 |
| 清点总清单 §1.4 | 「只维护统一前端 = …openbase-ui…；各子系统自带 `frontend/` 暂时冻结、不再维护」；计数口径不变 | ✅ 已存在（v1.0.2）；本批次追加 S6-T1 口径闭环注记（v1.0.3） |
| 跨仓提交放行清单 §0 通用红线第 5 条 | 「统一前端口径」：禁止将各子系统 `frontend/` 改动纳入联调提交批；统一前端改动仅在 `openbase-ui/` 内维护与提交 | ✅ 已存在（v1.0.5）；本批次追加 S6-T1 口径闭环注记（v1.0.6） |

---

## §2 四仓 `frontend/` 冻结声明（S6-T1-1 ②）

### 2.1 统一声明文案（推荐逐仓照抄）

> **前端冻结声明（统一口径）**：本仓自带 `frontend/`（子系统独立前端）自 2026-09-10 起**冻结**——**保留目录不删除**、**不再构建/发布**、**后端不再挂载其产物**。本系统前端的唯一维护面为统一前端 `OpenBase/openbase-ui`，经 nginx 同域 `/ui/` 提供访问；本仓后端仅提供 API。历史代码保留以供追溯与回滚。

### 2.2 冻结声明落点（四仓现状，只读盘点）

| 仓 | 冻结处置 | `README.md` 存在性 | 现行落点 | 说明 |
|----|---------|------------------|---------|------|
| OpenMemory | 保留不删 / 不再构建/发布 / 后端不挂载 | ✅ 存在 | `README.md` | 冻结声明待各仓后续批次写入 |
| DPS | 同上 | ✅ 存在 | `README.md` | 同上 |
| OpenRAG | 同上 | ✅ 存在 | `README.md` | 同上 |
| OpenLLM | 同上 | ✗ **不存在**（仓根仅有 `OpenLLM_完整方案文档.html`、`version.json`、`docker-compose*.yml` 等） | 候选：`docker-compose.yml` 服务注释（随改造点 2 移除 `frontend` 服务时一并落地）或新建 `docs/frontend-frozen.md` | 按 **Q-S6-D5** 建议随改造点 2 写服务注释（零新增文件），最终由 OpenLLM 仓自行决定 |

---

## §3 3 处待改造点逐条登记（S6-T1-1 ③，覆盖 4 仓）

> 登记口径：**3 处改造点 / 4 个仓**。改造点 1 与 2 为「运行时静态承载」；改造点 3 为「CI 构建链」，合并登记 DPS 与 OpenRAG 两仓。**所有行号均为 2026-09-10 只读实测值**（设计草案 §3.4/附录 D 复核），S6 内不修改上述任何文件。

### 3.1 四元组总表

| # | 归属仓 | 证据行号（2026-09-10 复核） | 建议动作 | 状态 |
|---|--------|---------------------------|---------|------|
| 1 | **OpenMemory** | `deploy/nginx/conf.d/openmemory.conf:90`（`root /app/frontend/dist;`）、`openmemory.conf:93-101`（`location / { try_files … /index.html; }`，含 `openmemory.conf:97-100` 静态缓存） | 下线 SPA 承载：移除 `openmemory.conf:90` 与 `openmemory.conf:93-101`；保留 `/api/` 反代 `openmemory.conf:106-124`（`proxy_buffering off` 保 SSE）与 `/health` `openmemory.conf:129-133`；`/` 改 301 → 统一前端 `/ui/` | 口径闭环：✅ S6 已登记；物理闭环：**PENDING（待 OpenMemory 后续批次执行，交 S7 按 Q-S6-D7 复核）** |
| 2 | **OpenLLM** | `docker-compose.yml:141-172`（`frontend` 服务：`build.context ./frontend`、3000/5173 端口、热加载卷、`develop.watch`）；`docker-compose.prod.yml:19`（`./frontend/dist:/usr/share/nginx/html:ro`）；`frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` | 移除 `frontend` 服务与 `frontend/dist` 挂载；`frontend/Dockerfile`/`Dockerfile.dev`/`nginx.conf` **保留不删**但不再被编排引用 | 口径闭环：✅ S6 已登记；物理闭环：**PENDING（待 OpenLLM 后续批次执行，交 S7 按 Q-S6-D7 复核）** |
| 3 | **DPS + OpenRAG**（CI 构建链，合并登记） | **DPS** `.github/workflows/ci.yml`：前端 Lint `L68-79`、Coverage `L114-129`、Build `L164-195`、E2E `L213-230`；**OpenRAG** `.github/workflows/frontend-ci.yml`（共 **65** 行：`paths: ['frontend/**']` L6/L9；quality L12-41；e2e L43-65） | 前端 job/step 收敛为「冻结校验 / 跳过」（触发路径移除或 job 收敛）；**后端 CI 与后端门禁不变** | 口径闭环：✅ S6 已登记；物理闭环：**PENDING（待 DPS / OpenRAG 后续批次执行，交 S7 按 Q-S6-D7 复核）** |

### 3.2 改造点 1（OpenMemory nginx）明细

| 项 | 内容 |
|----|------|
| 归属仓 | OpenMemory（`D:\Trae CN\myproject\Dev\OpenMemory`） |
| 证据行号 | `deploy/nginx/conf.d/openmemory.conf:90`、`openmemory.conf:93-101`（含 `openmemory.conf:97-100`）；佐证保留面 `openmemory.conf:106-124`（`/api/` 反代）、`openmemory.conf:129-133`（`/health`） |
| 现状语义 | 以子系统前端产物为站点根 + SPA 兜底（运行态承载子系统前端） |
| 建议动作 | 按 Q-FE-1 定案「**下线 SPA 承载**」：移除 `:90` 的 `root /app/frontend/dist;` 与 `:93-101` 的 `location / { try_files $uri $uri/ /index.html; }`；站点仅保留 `/api/` 反代、`/health`，并把 `/` 改为 301 → 统一前端 `/ui/` |
| 回滚性 | 完全可回滚（还原 nginx 配置即恢复；`frontend/` 目录保留不删） |
| S6 动作 | **登记**（本文档）；不改文件 |
| 状态 | 口径闭环 S6 ✅ / 物理闭环 **PENDING** 交 S7（Q-S6-D7） |

### 3.3 改造点 2（OpenLLM 编排）明细

| 项 | 内容 |
|----|------|
| 归属仓 | OpenLLM（`D:\Trae CN\myproject\Dev\OpenLLM`） |
| 证据行号 | `docker-compose.yml:141-172`（`frontend` 服务：`build.context ./frontend` L142-144、端口 L147-149、热加载卷 L154-160、`develop.watch` L166-172）；`docker-compose.prod.yml:19`；`frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` |
| 现状语义 | 开发/生产均构建并服务子系统前端（含热加载与 `develop.watch`） |
| 建议动作 | 删除 `docker-compose.yml:141-172` 的 `frontend` 服务与 `docker-compose.prod.yml:19` 的 `frontend/dist` 挂载；镜像与 nginx 配置文件**保留不删**、不再被编排引用；冻结声明按 **Q-S6-D5** 随本次改动以服务注释或 `docs/frontend-frozen.md` 落地（OpenLLM 无 `README.md`） |
| 回滚性 | 完全可回滚（还原 compose 即恢复构建/发布能力） |
| S6 动作 | **登记**（本文档）；不改文件 |
| 状态 | 口径闭环 S6 ✅ / 物理闭环 **PENDING** 交 S7（Q-S6-D7） |

### 3.4 改造点 3（DPS + OpenRAG CI 构建链）明细

| 项 | 内容 |
|----|------|
| 归属仓 | DPS（`D:\Trae CN\myproject\Dev\DPS`）、OpenRAG（`D:\Trae CN\myproject\Dev\OpenRAG`） |
| 证据行号 | **DPS** `.github/workflows/ci.yml`：前端 Lint `L68-79`（Setup Node L68-73 + `npm ci`/`npm run lint` L75-79）、Coverage `L114-129`（含 diff-cover L127-129）、Build `L164-195`、E2E `L213-230`（Setup Node L213-218、Playwright 安装 L220-224、`npm run e2e` L226-230）；**OpenRAG** `.github/workflows/frontend-ci.yml`：共 **65** 行，`paths: ['frontend/**']` L6/L9，quality job L12-41，e2e job L43-65 |
| 现状语义 | CI 仍对子系统前端执行 lint / test / build / e2e（与前端冻结口径冲突） |
| 建议动作 | 前端 job/step 收敛为「冻结校验 / 跳过」：DPS 四段前端 step 收敛或整体跳过；OpenRAG 触发路径移除或 job 收敛；**后端 CI 与后端门禁不变**。收敛形式（可开关 job / 直接跳过）在各子系统仓执行时定 |
| 回滚性 | 可回滚（还原 workflow 即恢复；建议以可开关形式落地） |
| S6 动作 | **登记**（本文档）；不改文件 |
| 状态 | 口径闭环 S6 ✅ / 物理闭环 **PENDING** 交 S7（Q-S6-D7） |

### 3.5 发布顺序约束（Q-FE-1 / 设计草案 §6.2）

> **先发布统一前端（`dist-v1.3.0` + nginx `/ui/` 可用）→ 再在下游子系统仓收敛前端承载**。若「后端不再挂载」先于统一前端可用，前端面将不可访问。该约束为四仓改造的执行前置，在 S7 全链核验中复核。

---

## §4 各仓冻结声明落点待执行清单（S6-T1-1 ③ / Q-S6-D5）

| # | 仓 | 落点（建议） | 待执行动作 | 是否新增文件 | 状态 |
|---|----|-------------|-----------|-------------|------|
| 1 | OpenMemory | `README.md` | 追加 §2.1 统一声明文案 | 否 | PENDING（待 OpenMemory 后续批次） |
| 2 | DPS | `README.md` | 追加 §2.1 统一声明文案 | 否 | PENDING（待 DPS 后续批次） |
| 3 | OpenRAG | `README.md` | 追加 §2.1 统一声明文案 | 否 | PENDING（待 OpenRAG 后续批次） |
| 4 | OpenLLM | `docker-compose.yml` 服务注释（推荐，随改造点 2 一并落地）**或** 新建 `docs/frontend-frozen.md` | 二选一，由 OpenLLM 仓自行决定（**Q-S6-D5**） | 推荐否（注释零新增文件） | PENDING（待 OpenLLM 后续批次） |
| 5 | **OpenBase（S6 侧）** | `openbase-ui/docs/frontend-frozen.md` | **本批次已落地**：声明唯一维护面 + 四仓冻结口径 + 3 处改造指引 | 是（S6 提交面显式登记） | ✅ 已执行（S6-T1-3） |

---

## §5 两级闭环判定（S6-T1-1 ④ / Q-S6-D7）

| 层级 | 判据 | 判定主体 | 本批次结论 |
|------|------|---------|-----------|
| **口径闭环** | 3 处改造点逐项登记完成（仓 / 文件:行号 / 现状语义 / 归属仓 / 建议动作 / 状态 四元组齐备）+ 唯一维护面口径三处一致 + 前端侧冻结声明落点落地 | S6（本批次） | ✅ **已闭环** |
| **物理闭环** | 四仓实际完成 nginx 下线 / compose 移除 / CI 收敛，且统一前端 `/ui/` 已先发布可用 | 各子系统后续批次 + S7 复核 | ⏳ **PENDING**（未执行；不伪造；由 S7 按 Q-S6-D7 复核物理闭环） |

> **纪律**：S6 段门禁对「3 处改造闭环」的判定 = **口径闭环完成**（本表上行）；「物理闭环」项记 `PENDING（交 S7 复核）`，不得以「已登记」冒充「已改造」。

---

## §6 核验命令与证据（S6-T1-2 / S6-T1-4）

### 6.1 后端不挂载确认（S6-T1-2）

| 项 | 命令 | 2026-09-10 实测结论 |
|----|------|-------------------|
| OpenBase 后端挂载扫描 | `grep -rn "StaticFiles\|mount(\|dist-v" openbase/**` | **0 命中**（无 `StaticFiles`、无 `mount(`、无 `dist-v`） |
| CLI 目标目录文案（排除误报） | `grep -rn "openbase-ui" openbase/**` | 仅 `openbase/cli/main.py` 的目标目录文案（`openbase/modules` 或 `openbase-ui/src/modules`，属 scaffold 参数说明、**非产物挂载**） |
| 防漂移固化 | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` | 3 条 S6-T1-2 断言（全量扫描 0 命中 + 白名单 + 扫描器非空化自检） |
| 四仓结论（引用，非本批实测） | 放行清单 §1.5/§2.5/§3.3/§4.5 | 四仓后端均**未**以 `StaticFiles` 等方式挂载 frontend 产物（引用放行清单结论） |

### 6.2 提交面纪律与证据核对（S6-T1-4）

| 项 | 命令 | 口径 |
|----|------|------|
| 提交面白名单 | `git status --porcelain -uall` | 仅含：本登记文档 + `doc/planning`/`doc/development` 两份清单加注 + `openbase-ui/**` 改动 + `tests/test_s6_t1_frontend_boundary.py`；**排除** `dogfood-output/`、`dist-v*`、`coverage`、`node_modules` |
| 禁兜底暂存 | 逐项显式 `git add <path>` | **禁止 `git add -A` / `git add .`**（放行清单 §0 红线第 1 条） |
| 无子系统 frontend 改动 | `git show --stat <commit>` | S6 提交面**不含**任何子系统 `frontend/` 文件 |
| 清单引用位 | 清点总清单 §5.6 / 放行清单 §0 | 各留一行 S6-T1 口径闭环 + PENDING 移交注记（本批次落地） |

---

## §7 遗留与边界

| # | 项 | 说明 | 归属 |
|---|----|------|------|
| 1 | 设计草案 §4.1 **S6-T1-3「发布形态」条目**（`build_release.ps1` 版本目录参数化、`.gitignore` 增补 `dist-v*`、`package.json` 1.2.0 → 1.3.0、`nginx.conf.example` 口径确认） | **✅ 已闭环（S6 批次 2，对齐 Q-FE-2b 与 Q-S6-D1「T6 前升」）**：四小项全部落地——① 版本目录由 `package.json.version` 派生；② `.gitignore` 含 `dist-v*`；③ 承载版本升 **1.3.0**；④ nginx 同域口径核对一致。证据与核验命令见 **§8 / §9** | 已完成（S6 批次 2） |
| 2 | 四仓物理改造（改造点 1~3）与 4 仓冻结声明写入 | 需各子系统仓 git 写权限（沙箱仅允许 OpenBase 仓） | 各子系统后续批次；S7 复核 |
| 3 | 子系统后端挂载结论 | 引用放行清单 §1.5/§2.5/§3.3/§4.5（本批未逐仓重测） | S7 全链核验 |
| 4 | `frontend/` 目录规模与在途项 | OpenMemory 59 文件（在途 8 项归 B 类）、OpenLLM 214 文件、DPS 63 文件、OpenRAG 125 文件 | 引用放行清单 v1.0.4/v1.0.5 各仓小节注记 |

---

## §8 S6-T1-3 发布形态参数化证据（S6 批次 2 补做，Q-FE-2b）

> 口径：统一前端发布形态 = **`dist-vX.Y.Z` 版本目录承载 + nginx 同域 `/ui/` 静态 + `/api/` 反代 + SSE 不缓冲**；版本目录仅切 alias 即可发布/回滚，不涉及数据库迁移与后端语义（设计草案 §6.1、INV-5）。

### 8.1 版本目录参数化（`openbase-ui/scripts/build_release.ps1`）

```powershell
$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root 'dist'
# 版本目录参数化：由 openbase-ui/package.json 的 version 派生，消除 dist-v1.2.0 硬编码
$PackageJson = Get-Content (Join-Path $Root 'package.json') -Raw | ConvertFrom-Json
$Version = $PackageJson.version
$ReleaseDir = Join-Path $Root "dist-v$Version"
...
Write-Host "[1/3] 质量门禁：Lint 0 + 测试 100% + 覆盖率 >=80%（承载版本 v$Version）"
npm run lint   ; if ($LASTEXITCODE -ne 0) { throw 'Lint 失败' }
npm run test   ; if ($LASTEXITCODE -ne 0) { throw '单测失败' }
npm run test:coverage ; if ($LASTEXITCODE -ne 0) { throw '覆盖率门禁失败' }
npm run build  ; if ($LASTEXITCODE -ne 0) { throw '构建失败' }
if (Test-Path $ReleaseDir) { Remove-Item $ReleaseDir -Recurse -Force }
Copy-Item $Dist $ReleaseDir -Recurse
```

| 核验项 | 命令 | 结果 |
|--------|------|------|
| 无硬编码版本目录 | `Select-String -Path scripts\build_release.ps1 -Pattern 'dist-v'` | 仅注释 + `"dist-v$Version"` 参数化行，**无 `dist-v1.2.0` 硬编码** |
| 派生版本号 | `(Get-Content package.json -Raw \| ConvertFrom-Json).version` | **1.3.0**（`package-lock.json` 同步 1.3.0） |
| 门禁语义保持 | 脚本 Lint/测试/覆盖率/build 四段 | 语义不变（Lint 0 + 测试 100% + 覆盖率 ≥80%） |

### 8.2 忽略规则（`openbase-ui/.gitignore`）

```
node_modules
dist
dist-v*
coverage
*.local
.DS_Store
```

| 核验项 | 命令 | 结果 |
|--------|------|------|
| 版本目录被忽略 | `git check-ignore -v openbase-ui/dist-v1.3.0` | `openbase-ui/.gitignore:3:dist-v*` **命中**（此前实测未忽略，R-10 已消除） |

### 8.3 nginx 同域口径（`openbase-ui/nginx.conf.example`）

| 项 | 现行（实测） | 口径 |
|----|-------------|------|
| `/ui/` 静态 | `alias …/dist-v1.3.0/;` + `try_files $uri $uri/ /ui/index.html;` + `expires 1h` | alias 指向**版本目录**，切换/回滚仅改此处 |
| `/api/` 反代 | `proxy_pass http://127.0.0.1:8000;` + `Authorization` 透传 + `proxy_http_version 1.1` | 受信通道口径不变 |
| SSE | `proxy_buffering off;` + `proxy_read_timeout 300s;` | 流式不缓冲（对话/RAG 关键） |
| 根路径 | `location = / { return 301 /ui/; }` | 统一前端承接 |

### 8.4 边界（非沙箱复核，Q-S6-D7 / 设计草案 §1.4 B6）

| 项 | 说明 |
|----|------|
| `/ui/` 发布与回滚实测 | 需 nginx + 运行态 + 两个版本目录，**PENDING（沙箱受限）**，交 S7 按 B6 复核 |
| 生产 alias 指向 | 由发布流程在部署时切换（配置级回滚）；本批仅固化示例口径 |

---

## §9 批次 2 硬门禁实测（2026-09-10，沙箱内，禁止伪造）

| # | 命令（工作目录） | 结果摘要 | 退出码 |
|---|----------------|---------|--------|
| 1 | `npm run lint`（openbase-ui） | `eslint src --ext .ts,.vue && vue-tsc --noEmit` **0 problem** | **0** |
| 2 | `npm test`（openbase-ui） | Test Files **11 passed (11)**、Tests **104 passed (104)**（批前 7 files / 44 tests） | **0** |
| 3 | `npm run test:coverage`（openbase-ui） | All files：stmts **96.37%** / lines **96.37%** / funcs **87.23%** / branches **88.63%**（阈值 80/80/80/70，**全部达标**；批前 51.52/51.52/50.66/85.84） | **0** |
| 4 | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q`（仓根） | **9 passed**（S6-T1 防回归固化） | **0** |

> 说明：覆盖率已按 Q-FE-7b「不改阈值」口径由 51.52% 提升至 96.37%（新增 `tests/api-clients.spec.ts` 打通 `src/core/api/**` 客户端、`tests/router-nav.spec.ts`/`nav-consistency.spec.ts` 覆盖 `src/core/router/**`），**未放宽 `vite.config.ts` thresholds**。

---

## §10 S6 批次 4（T5/T6）结论登记（v1.0.2 新增，2026-09-10）

> 登记口径：本条为批次 4 的**结论追加**，不改变 §1~§9 既有口径；T1 冻结与 3 处改造处置结论保持原样（仅复核两级闭环状态）。

### 10.1 T5 L3-2 贯通冒烟基座（S6-T5-1~3）

| 项 | 结论 |
|----|------|
| 脚本与清单 | `openbase-ui/scripts/smoke_l3_2_ui.mjs`（零依赖、仅 `OPENBASE_BASE_URL` 受信通道入口、携带 `X-Proxy-Source`）+ `openbase-ui/tests/e2e/fixtures/key-pages.json`（Q-S6-D6 同源，9 关键页） |
| 浏览器级用例 | `openbase-ui/playwright.config.ts` + `tests/e2e/{portrait,memory,knowledge,chat}.spec.ts`（9 tests in 4 files，`npx playwright test --list` 退出码 0） |
| 静态旁路检查 | **PASS**：`src/**` 端口字面量 8/8 属白名单（提示文案/mock 数据）、绝对 URL 10/10 属白名单、`src/core/api/**` 绝对地址 0、`http.ts` `baseURL=/api/v1`；**白名单外命中 = 0** |
| 真实执行 | **PENDING**：`OPENBASE_BASE_URL` 受信通道不可达 → `doc/test/evidence/s6/l3-2-smoke.json` `status=PENDING`（退出码 2）；Playwright 浏览器二进制沙箱安装受限（EPERM）→ 9 failed（非断言失败） |
| 阻塞项 | B1（关键页 PASS）、B2（真实双签） |

### 10.2 T6 段门禁聚合与台账回写（S6-T6-1~3）

| 项 | 结论 |
|----|------|
| evidence 归档 | `doc/test/evidence/s6/`：`l3-2-smoke.json`、`ui-e2e/{results.json,status.json}`、`coverage-summary.json`、`segment-gate.json`（含 `openbase_commit`/`ui_version`/时间戳/`status`） |
| 硬门禁 | `npm run lint` 0 problem（退出 0）；`npm test` 13 files/137 tests（退出 0）；`npm run test:coverage` 97.08/90/88.46/97.08（阈值 80/80/80/70，退出 0，**未放宽**）；仓根 `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` **9 passed** |
| 台账回写 | JT 归集 §3.6（v1.3.0）、跨仓放行清单 §0/§5（v1.0.7）、清点总清单 §5.7（v1.0.4）；本登记文档（v1.0.2） |
| 提交号桥接 | 批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 `477eb80`（`feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`） |

### 10.3 3 处改造闭环两级判定（复核）

| 层级 | 判据 | 本批次结论 |
|------|------|-----------|
| **口径闭环** | 3 处改造点逐项登记完成 + 唯一维护面口径一致 + 前端侧冻结声明落点落地 | ✅ **保持闭环**（§1~§5 不变；本批复核无回退） |
| **物理闭环** | 四仓实际完成 nginx 下线 / compose 移除 / CI 收敛，且统一前端 `/ui/` 已先发布可用 | ⏳ **PENDING（B5）**：需各子系统仓写权限，交 S7 按 Q-S6-D7 复核；**不得以「已登记」冒充「已改造」** |

---

> **文档结束**。本文档为 S6 段 **T1 边界收口（口径面）** 交付物（**[Approved]** v1.0.3；**v1.0.x 修订：S6 段门禁批准（挂起口径）**——2026-09-11 人工批准，口径闭环已批准；物理闭环 B5 PENDING 交各子系统对话 / S7）；与 S6-T1-2 静态断言测试、S6-T1-3 前端侧冻结声明落点（批次 1）+ 发布形态参数化（批次 2）、S6-T1-4 清单引用位共同构成 T1 的可核对证据链。
