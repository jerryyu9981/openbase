# OpenBase-多系统联调-跨仓提交放行清单-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-CROSSREPO-RELEASE-v1.0.0 |
| 版本 | v1.0.7 |
| 状态 | [Draft]（供用户沙箱外执行；每条命令执行前请以「第 0 步核对」实核各仓 git 状态；v1.0.4 依据统一前端定案补「统一前端口径」红线与各仓 frontend 冻结注记；v1.0.5 依据 S5（DPS）段门禁 2026-09-10 人工批准在 §3.3 登记「S5 段门禁已批准、可进入入仓」；v1.0.6 S6-T1 统一前端冻结口径闭环加注；**v1.0.7 S6 段门禁结论回写（前端段收官）：OpenBase 仓 S6 提交批次（批 1~4 提交号）与段门禁结论登记，仅加注不改变四仓放行口径**） |
| 日期 | 2026-09-10 |
| 作者 | AD（跨项目分析） |
| 版本主题 | S2（OpenMemory 段）+ S3（OpenRAG 段）+ S4（OpenLLM 段）段门禁批准后的跨仓放行清单：OpenMemory v7.2 基线先行 + S2（v7.3 拟）五份文档与源码/迁移/测试分批提交；OpenRAG S3（v1.10.0 拟，§4）六份文档 + identity/中间件/配置 + storage/迁移/路由 + scripts/tests/CI 分批提交；OpenLLM 仓 S4（v2.15.0 拟，§2 改写）：先按基线收口登记清单 A~E 落基线（S0 探活 + 版本对齐 v2.14.3），再按「文档 / identity 包 / 客户端与网关 / scripts / tests」4~6 批提交 S4；DPS S0 探活等既有待提交分批核对提交；OpenBase 侧已全部提交无需放行；**v1.0.3 修订**：依据《OpenBase-联调产物清点核对总清单-v1.0.0》§2 的 7 条差异与 §2.8 回写建议，对 §1~§5 登记口径与批次做差异回写（OpenRAG 54→67、OpenLLM 折叠 430≈展开 1555 与 4 项 need-star 移出、DPS 47→57 且批次 1→4、OpenMemory 364/B 类 197 隔离、OpenBase HEAD cdfbd5b），并新增「各仓清点清单索引」「通用提交红线」小节 |
| 上游依据 | OpenMemory S2 立项方案 v1.1.0 / 设计草案 v1.0.3 / DevLogReport v1.0.1 / 测试报告 v1.0.1 / doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1（[Approved]，2026-09-09 S2 段门禁人工批准五项全绿）；OpenRAG S3 立项方案 v1.1.0 / 设计草案 v1.0.1（[Approved]）/ DevLogReport v1.0.1（[Approved]，2026-09-09 S3 段门禁人工批准五项全绿）/ 测试报告 v1.0.0（[Final]）/ doc/design/OpenRAG-K07-端点过滤矩阵填报 v1.0.0（[Final]，121 行=豁免 10/覆盖 111）；OpenBase-数据隔离实现任务卡 v1.4.0（S2 段回写）、v1.5.0（S3 段回写）与 v1.6.0（S4 段回写）；OpenLLM S4 立项方案 v1.1.0 / 设计草案 v1.0.1（[Approved]）/ DevLogReport v1.0.1（[Approved]，2026-09-10 S4 段门禁人工批准五项全绿）/ 测试报告 v1.0.1（[Approved]）/ doc/test/OpenLLM-JT-台账-S4（[Approved]）/ doc/design/OpenLLM-K07-端点过滤矩阵填报 v1.0.0 / doc/planning/OpenLLM-S4-批次1基线收口登记清单 v1.0.0（基线 A~E 分类）；OpenBase commit 0713ec1=事件列表契约端点 GET /api/v1/identity/events（2026-09-09 冻结，仍为单据参考锚点；2026-09-10 实测当前 HEAD=cdfbd5b，见 §5 与 §7） |
| 适用范围 | 本清单涉及 OpenMemory / OpenLLM / DPS / OpenRAG 四个子系统 git 仓的放行提交作业，须由用户在沙箱外执行（沙箱内 git 仅允许操作 OpenBase 仓）；OpenBase 仓本次回写已在沙箱内提交（见 §5） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-09 | AD（跨项目分析） | 初始版本：S2（OpenMemory）段收口跨仓放行清单（OpenMemory v7.2 基线 + S2 v7.3 批次；OpenLLM/DPS/OpenRAG S0 探活等既有待提交；OpenBase 无需放行），含逐仓建议分支、提交顺序、git add/commit 模板与提交后回归命令 |
| v1.0.1 | 2026-09-09 | AD（跨项目分析） | S3（OpenRAG）段门禁批准（2026-09-09 五项全绿）后新增 OpenRAG 仓 S3 放行批次：§4 改写为 release/v1.10.0（拟）四批放行（文档 / identity·中间件·配置 / storage·迁移·路由 / scripts·tests·CI），含文件清单、git add/commit 模板与提交后回归命令；总览表 OpenRAG 行建议提交 0→4；OpenMemory/OpenLLM/DPS 原批次不变；同步任务卡 v1.4.0→v1.5.0（S3 段回写），本清单保持 [Draft] 供沙箱外执行 |
| v1.0.2 | 2026-09-10 | AD（跨项目分析） | S4（OpenLLM）段门禁批准（2026-09-10 五项全绿）后新增 OpenLLM 仓 S4 放行批次：§2 改写为「基线批次（按 doc/planning/OpenLLM-S4-批次1基线收口登记清单 A~E：S0 探活 + 版本对齐 v2.14.3）+ S4 4~6 批（文档 / identity 包·中间件·配置 / 客户端与网关 / scripts / tests）」，含现状核对基线、文件清单、逐步 git add/commit 模板与提交后回归命令（pytest tests/unit + ruff + 扫描 + k07 + verify-env + smoke_l3_2）；总览表 OpenLLM 行建议提交 2~3→6（可 5~7）；§6 增补 OpenLLM L3-2 真实 HTTP 双签联调窗口提示；同步任务卡 v1.5.0→v1.6.0（S4 段回写），本清单保持 [Draft] 供沙箱外执行 |
| v1.0.3 | 2026-09-10 | AD（跨项目分析） | 依据《OpenBase-联调产物清点核对总清单-v1.0.0》（OB-INTG-CLEARANCE-v1.0.0，[Review]，2026-09-10 四仓只读清点核对）§2 的 7 条差异与 §2.8 的 10 条回写建议做跨仓差异回写：①§4 OpenRAG 登记条数 54 → 实测 **67**（22 M + 45 ??），净增 13 项全部为 S3 批次 3（T8~T11）产物并附文件名摘要，批次数 4（B1~B4）明确；②§2 OpenLLM 清点口径修正（折叠 430 ≈ `-uall` 展开 1555 = ??1235 + D211 + M109，差额主体 `.pylib` 1157 + `.pyc` 282 + data/backup 等，均不提交；已入库 `.pyc` 用 `git rm -r --cached` 处置 13 个 `__pycache__` 目录共 211 项且禁止恢复；批次数维持 6，基线 1 + S4 5，可合 5）；③§2 分类冲突修正：4 项 need-star 测试文件从基线批 1 / 批 6 移出、改归 B 类隔离（`OB-INTG-LLM-NEEDSTAR`，建议独立分支 `feature/need-star-orchestration` + 独立批次与段门禁）；④§3 DPS 实测 57（11 M + 46 ??）≠ 预估 47，批次口径 1 → **4**（S5-B1~B4），补 v2.9.0 在途 3 项隔离清单与噪音提示，另登记 `.gitignore` 末尾无效绝对路径规则待修（不入本次提交面）；⑤§1 OpenMemory 登记口径更新为实测 **364**（75 M + 289 ??），A 联调 70（基线批 29 + S2 段批 41，共 4 批），B 类 197 项 v7.0~v7.2 自身在途开发必须隔离（原「`git add -A` + `git reset`」模板改为逐清单显式 `git add`、禁止兜底 add），敏感项 `.env.shared-infra`【不提交】并建议补 `.gitignore`；⑥§5 OpenBase HEAD `0713ec1` → 实测 **`cdfbd5b`**（S4 台账回写提交；`0713ec1` 仍为单据参考锚点），自身仅 7 项 `dogfood-output` 噪音（不提交、无联调产物）；⑦新增「§7 各仓清点清单索引」（总清单 + 四仓分清单共 5 份）并明确入仓-回填-勾稽-会签-回写流程；⑧新增「通用提交红线」4 条；⑨§0 前置门禁引用本次清点结论（清点核对已闭环、可进入各仓入仓），S0~S7 段顺序语义不变。本次仅回写本文档，未执行任何 git 写操作，未改动任何代码与其他文档；状态保持 [Draft] 待跨仓会签 |
| v1.0.4 | 2026-09-10 | AD（跨项目分析） | **v1.0.x 修订：统一前端定案**。项目负责人定案：唯一维护面 = `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`（Git 仓在 OpenBase 项目目录下、已入库跟踪，`git ls-files openbase-ui` 实测 107 文件）；各子系统自带 `frontend/`（DPS/OpenLLM/OpenMemory/OpenRAG）暂时冻结、不再维护。①§0 通用红线新增第 5 条「统一前端口径」：禁止将各子系统 `frontend/` 改动纳入联调提交批（其修改不属联调提交面、归 B/C 类），统一前端改动仅在 OpenBase 仓 `openbase-ui/` 内维护与提交；②各仓小节加 frontend 冻结注记——§1.5 OpenMemory（59 文件、在途 8 项已归 B 类、`deploy/nginx/conf.d/openmemory.conf:90,93` 待改造）、§2.5 OpenLLM（214 文件、`docker-compose.yml:141-172` 与 `docker-compose.prod.yml:19` 及 `frontend/Dockerfile`、`frontend/nginx.conf` 待改造）、§3.3 DPS（63 文件、CI `ci.yml:73-237` 构建链待改造、后端无挂载）、§4.5 OpenRAG（125 文件、`frontend-ci.yml` 待改造、后端无挂载）；③核实结论：四仓后端均**未**以 StaticFiles 挂载 frontend 产物，各仓分清单均**未**将 frontend 列入 A 类联调产物（误列 A 类 0 项），OpenBase 工作树无 `openbase-ui` 未提交改动（不增加提交面）。本次仅回写本文档，未执行任何 git 写操作，未改动任何代码；状态保持 [Draft] 待跨仓会签 |
| v1.0.5 | 2026-09-10 | AD（跨项目分析） | **S5（DPS）段门禁批准后放行登记**：依据 DPS S5 段门禁 2026-09-10 人工批准（批准口径=`2026-09-10 S5 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认、段门禁自检五项全绿（Pull 真实 HTTP 双签 PENDING 挂起登记不阻断）、遗留=无阻断项`；DPS 侧 DevLogReport/测试报告/K07 端点-过滤矩阵填报/设计草案四项文档已随批准回写至内部版本 v1.0.1），在 **§3.3「命令模板」** 增补登记行「**S5 段门禁已于 2026-09-10 人工批准、可进入入仓**」并引用《DPS-联调产物待提交清单-v1.0.0》（OB-DPS-CLEARANCE-v1.0.0，`D:\Trae CN\myproject\Dev\DPS\doc\planning\DPS-联调产物待提交清单-v1.0.0.md`）为逐文件执行依据；§3.1/§3.2 现状核对与 S5-B1~B4 四批口径**不变**（57 = A 52 + B 3 + C 2；HEAD 6b39dd4 / main）。本次仅回写本文档与 OpenBase 侧台账，未执行任何 git 写操作，未改动任何代码；状态保持 [Draft] 待跨仓会签 |
| v1.0.6 | 2026-09-10 | AI（S6 批次 1 开发会话） | **S6-T1 统一前端冻结口径闭环加注**：依据《OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md》（OB-S6-T1-FRONTEND-FREEZE-v1.0.0，`doc/planning/`）在 **§0 通用红线第 5 条之后**追加「S6-T1 口径闭环 + 物理闭环待各子系统执行（PENDING 交 S7）」注记，与《OpenBase-联调产物清点核对总清单-v1.0.0》§5.6（v1.0.3）同口径。**仅加注，不改变 §0 既有红线文本与 §1~§5 任何计数与批次口径**；本次仅回写本文档，未执行任何 git 写操作、未改动任何代码；状态保持 [Draft] 待跨仓会签 |
| v1.0.7 | 2026-09-10 | AI（S6 批次 4 开发会话） | **S6 段门禁结论回写（前端段收官）**：依据《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》§4.6/§9 与 `doc/test/evidence/s6/**`，①在 **§0** 追加「S6 段门禁结论」注记（前端侧回归 FE-R1-1/FE-R1-2/FE-3 达成、覆盖率 97.08/90/88.46/97.08 与 lint 0 problem 达标、3 处改造口径闭环完成；UI-E2E 关键页 PASS 与 L3-2 真实通道 **PENDING 非沙箱 B1/B2**、物理闭环 **PENDING B5 交 S7**）；②在 **§5 OpenBase 仓** 登记 **S6 提交批次**（批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 `477eb80`）与证据索引。**仅加注**：§0 红线第 5 条原文与 §1~§4 四仓计数/批次口径均不变；未执行任何跨仓 git 写操作、未改动任何代码；状态保持 [Draft] 待跨仓会签 |

---

## 0. 使用说明与放行总原则

- 本文件为 **[Draft]** 放行指引，不是自动执行指令：沙箱仅允许提交 OpenBase 仓，其余四仓命令需用户人工在沙箱外执行。
- **放行顺序总体建议**：OpenMemory 先行（v7.2 基线 → S2 批次，四提交）→ OpenRAG（S3 批次，release/v1.10.0 拟，四提交，见 §4）→ OpenLLM（基线批次 → S4 批次 4~6 提交，见 §2）→ DPS（S0 探活等既有待提交，按仓分批）→ OpenBase（无需放行，S2/S3/S4 台账回写已在沙箱内提交）。
- 每个提交前必做：`git status --porcelain` 核对、`git diff --cached --stat` 复查暂存内容仅含预期路径；**只 add 预期路径，一律不用 `git add -A` / `git add .` 兜底**（**v1.0.3 修订**：原「基线提交可 `git add -A`」的例外口径作废——四仓清点证实 OpenMemory 存在 B 类 197 项、OpenLLM 存在 C 类 1455 项未跟踪噪音，兜底 add 误纳风险极高；改为按各仓清点清单逐项显式 `git add`，详见 §1.4 与 §7）。
- **前置门禁（v1.0.3 引用清点结论）**：本次《OpenBase-联调产物清点核对总清单-v1.0.0》四仓只读清点核对**已闭环**（各仓 A + B + C + 需人工判定恒等于其 `git status --porcelain -uall` 全量条数，差异 0，子系统清单均存在且计数自洽），临时口径为**清点核对完成、可进入各仓入仓执行**；本清单仍为 [Draft]，四仓入仓与跨仓会签完成后按文档版本管理规范升版。S0~S7 段顺序语义（本清单 §1~§6 段批次与联调窗口）不变。
- 中文文件名路径在 PowerShell 中一律用**单引号**包裹。
- 每个仓库「提交后回归」若失败：停止后续批次，修正后再继续；回归通过后再进行下一仓。
- 提交后回填：OpenMemory 实际 commit hash 需回填《OpenBase-数据隔离实现任务卡 v1.4.0》卡尾 S2 段执行摘要；OpenRAG 实际 commit hash 需回填任务卡 v1.5.0 卡尾 S3 段执行摘要；OpenLLM 实际 commit hash 需回填任务卡 v1.6.0 卡尾 S4 段执行摘要；DPS 实际 commit hash 需回填 DPS JT 台账与 S5 段任务卡卡尾；并同步各仓文档状态登记（本文档升版为 [Approved] 时一并登记，遵循文档版本管理规范）。

### 通用提交红线（v1.0.3 新增，四仓通用）

1. **禁止兜底暂存**：任何批次禁用 `git add -A` / `git add .`，一律按各仓清点清单显式路径 add；提交前以 `git diff --cached --stat` 复查暂存面仅含预期路径。
2. **禁止提交敏感文件**：`.env`、`.env.shared-infra`、`.env.e2e`、`data/edge_tokens.jsonl`（含 OpenLLM `backend/.env` / `backend/.env.shared-infra`、DPS `.env.shared-infra`、OpenMemory `.env.shared-infra`）等一律不入任何批次；并推动各仓补齐 `.gitignore` 规则。
3. **OpenRAG 禁止 `git add repository`**：该路径为 gitlink 子仓（`160000 0ed102a…`），任何批次不得 add，如需提交须在内嵌仓自身会话内独立作业。
4. **OpenLLM 4 个混合文件须 `git add -p` 按 hunk 拆分**：`backend/app/api/openllm_gateway.py`、`backend/app/api/writeback.py`、`backend/app/core/config.py`、`backend/main.py`（S4 增量与 need-star 增量同文件叠加）；未拆分而整体提交时，**须在 commit message 显式声明混入 need-star**（不推荐）。
5. **统一前端口径（v1.0.4 新增；v1.0.x 修订：统一前端定案）**：**禁止将各子系统 `frontend/`（DPS / OpenLLM / OpenMemory / OpenRAG）改动纳入联调提交批**——各子系统自带前端已冻结（保留目录、不再构建/发布、后端不再挂载其产物），其改动一律不属联调提交面（归 B/C 类）；**统一前端改动仅在 OpenBase 仓 `openbase-ui/` 内维护与提交**（唯一维护面 = `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`，已入库跟踪，`git ls-files openbase-ui` 实测 107 文件；本次实测无未提交改动，不增加提交面）。

> **S6-T1 口径闭环加注（v1.0.6 新增，2026-09-10）**：统一前端冻结的 **S6-T1 口径闭环已完成**（2026-09-10，S6 批次 1）——统一前端唯一维护面 = `OpenBase/openbase-ui`；四仓 `frontend/` 冻结声明（保留不删 / 不再构建/发布 / 后端不挂载产物）；3 处改造点（OpenMemory nginx `deploy/nginx/conf.d/openmemory.conf:90,93`；OpenLLM `docker-compose.yml:141-172` 与 `docker-compose.prod.yml:19`；DPS `.github/workflows/ci.yml` 与 OpenRAG `.github/workflows/frontend-ci.yml`）逐条登记四元组齐备，证据锚点 = 《OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md》+ `tests/test_s6_t1_frontend_boundary.py` + `openbase-ui/docs/frontend-frozen.md`。**物理闭环（四仓实际改造/CI 收敛）待各子系统执行（PENDING 交 S7 按 Q-S6-D7 口径复核）**，需各子系统仓写权限，本清单不代为执行、不伪造。本条**仅加注**：§0 红线第 5 条原文不变，§1~§5 各仓计数与批次口径均不变（详见清点总清单 §5.6 同口径注记）。

> **S6 段门禁结论加注（v1.0.7 新增，2026-09-10）**：S6（前端段）段门禁结论 = **未达最终通过（非沙箱项 PENDING）**：① **已达成**——FE-3（S6-T2）、FE-R1-1 前端侧回归（S6-T3）、FE-R1-2 前端侧回归（S6-T4）；`npm run lint` 0 problem；`npm test` 13 files/137 tests；覆盖率 All files **97.08% / 90% / 88.46% / 97.08%**（阈值 80/80/80/70，未放宽）；仓根 `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` 9 passed；② **PENDING**——UI-E2E 关键页 PASS（B1：Playwright 浏览器二进制沙箱受限）与 L3-2 真实受信通道双签（B2：通道不可达 → `doc/test/evidence/s6/l3-2-smoke.json` `status=PENDING`）；③ **3 处改造**：口径闭环 ✅、物理闭环 **PENDING（B5，交 S7 按 Q-S6-D7 复核）**。证据索引 `doc/test/evidence/s6/`（`l3-2-smoke.json` / `ui-e2e/{results.json,status.json}` / `coverage-summary.json` / `segment-gate.json`）。本条**仅加注**：§0 红线原文不变，§1~§4 各仓计数与批次口径均不变（详见清点总清单 §5.7 同口径注记）。

## 1. OpenMemory 仓（D:\Trae CN\myproject\Dev\OpenMemory）

### 1.1 现状核对基线（2026-09-09 实测）

| 项目 | 值 |
|------|-----|
| HEAD | `6cbfb71`（6cbfb719b19846eebc068b2b36f31071efc23e1f，chore: v6.9.0 全流程闭环登记 closureComplete） |
| 当前分支 | `release/v6.9.0` |
| 工作树 | v7.0~v7.2 未提交基线 + S2 段产物（初版登记口径 **69 M + 207 ?? = 276**；2026-09-09 实测 75 M + 235 ??；**v1.0.3 修订：2026-09-10 实测 `git status --porcelain -uall` = 364（75 M + 289 ??，无 D/R、无暂存）**——其中 **A 联调 70**（基线批 29 + S2 段批 41，共 4 批）、**B 类自身在途 197**（v7.0~v7.2 子系统自身开发，须隔离）、C 类噪音 89、需人工判定 8；以第 0 步实核为准） |
| S2（v7.3 拟）产物 | 全部位于未跟踪/已修改工作树，因 git 沙箱受限尚未提交 |
| 放行批次（v1.0.3 修订） | **4 批**：批 0 基线（29）/ 批 1 S2 五份文档（5）/ 批 2 S2 源码·迁移·脚本（21）/ 批 3 S2 测试·CI（15） |

**第 0 步核对命令**（执行任何提交前先跑）：

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git log -1 --format='%H %s'                        # 期望 6cbfb71...（v6.9.0 发布闭环）
git branch --show-current                          # 期望 release/v6.9.0
(git status --porcelain).Count                     # 核对总行数（v1.0.3 修订：2026-09-10 实测 364 = 75 M + 289 ??；可用 -uall 复核，本仓无折叠差分）
git status --porcelain -uall | Select-String '^\?\?' | Measure-Object -Line   # 可选：核对未跟踪 289 项
git diff --cached --stat                           # 应无输出（无已暂存内容）
```

### 1.2 建议分支与提交顺序

- **提交 1（v7.2 基线）**：自 `release/v6.9.0` 切出 `release/v7.2.0`，在此分支提交基线。
- **提交 2~4（S2 批次）**：自基线提交切出 `release/v7.3.0`，在此分支按「五份文档 → 源码/迁移/脚本 → 测试/CI」三批提交（S2 规划承载版本 v7.3 拟，随版本规划批准）。
- 提交顺序总览：

| 序号 | 分支 | 提交内容 | 建议 commit 主题 |
|------|------|---------|-----------------|
| 1 | release/v7.2.0 | v7.0~v7.2 工作树基线（剔除 S2 专属文件） | chore: OpenMemory v7.2 基线收口 |
| 2 | release/v7.3.0 | S2 五份文档 | docs(s2): OpenMemory S2 五份文档入库 |
| 3 | release/v7.3.0 | S2 源码 + 中间件 + 迁移 v702~v704 + 脚本 | feat(s2): S2 协议头/行控/复合唯一/存量回填/事件消费端/矩阵校验 源码与迁移 |
| 4 | release/v7.3.0 | S2 测试用例 + CI s2-k07-matrix-gate job | test(s2): S2 T1~T13 RED 断言与段门禁自检用例 |

> 如需按 T 顺序拆更多提交：T1~T13 的逐卡提交仅对「新增测试文件」可按文件分组（test_s2_tN_*.py）；源码模块（identity/*、中间件）与迁移、脚本跨任务复用，不建议再按 T 拆分。本清单采用「合并」方案（用户可选项：或合并）。

### 1.3 S2（v7.3）专属文件清单（基线剔除清单，提交 2~4 的 add 集合）

```text
# 五份文档
OpenMemory-S2-过滤行控与身份接入立项方案-v1.0.0.md
OpenMemory-S2-过滤行控与身份接入设计草案-v1.0.0.md
doc/development/OpenMemory-S2-过滤行控与身份接入-DevLogReport-v1.0.0.md
doc/test/OpenMemory-S2-过滤行控与身份接入-测试报告-v1.0.0.md
doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md

# 源码与中间件（新增）
src/openmemory/identity/                    # agent_principal/audit_identity/blocklist/event_consumer/inbound_gate/protocol_headers/role_map/scope_exemption/verdict/__init__
src/openmemory/api/middleware/identity_gate.py
src/openmemory/api/middleware/block_subject_gate.py

# 迁移（S2：v702=T5 复合唯一、v703=T6 存量回填、v704=T7 事件阻断集）
alembic/versions/v702_session_registry_meta.py
alembic/versions/v703_backfill_scope_ownership.py
alembic/versions/v704_identity_blocklist.py

# 脚本与资产
scripts/k07_endpoint_matrix.py
scripts/scope_backfill_report.py
scripts/scan_auto_purge.py
scripts/smoke_l3_2.py
scripts/api_baseline.json
scripts/verify-env/                          # contract.json / verify_env_report.py 等

# 测试
tests/unit/test_s2_t*.py                     # t1~t13（含 test_s2_t1_protocol_gate.py ... test_s2_t12_m1_m2_modes.py）
tests/unit/test_l3_2_smoke.py
tests/unit/test_s2_segment_gate_selfcheck.py
```

> 混合文件说明：`.github/workflows/ci.yml` 同时含 v7.0 性能基线 job（TD-v7.0-010）与 S2 s2-k07-matrix-gate job；`src/openmemory/api/controllers.py`、`utils/config.py`、`utils/exceptions.py`、`api/middleware/structured_log.py`、`error_handler.py`、`memory/session_persistent.py` 等已跟踪文件内同时叠有 v7.2 基线改动与 S2 增量，git 无法按文件拆分。默认方案：**ci.yml 收入 S2 批次（提交 4），其余混合文件随基线（提交 1）**，避免基线提交引入引用缺失文件（s2-k07 job 依赖 scripts/k07_endpoint_matrix.py 与矩阵 doc）导致 CI 失败。若需严格拆分，见 §1.5 备注的 `git add -p` 做法。

### 1.4 放行步骤与命令模板

**提交 1 — v7.2 基线（release/v7.2.0）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git switch -c release/v7.2.0                      # 自 release/v6.9.0(6cbfb71) 切基线分支
# v1.0.3 修订：删除原「git add -A 全量暂存 + 逐项 git reset」模板——
# 在 B 类 197 项未跟踪在途开发存在时误纳风险极高；改为按《OpenMemory-联调产物待提交清单-v1.0.0》
# §2 批 0「A-基线批 29 项」逐项显式 add（下为摘要，完整 29 项见子系统清单 §6.2）：
git add '.env.example' 'scripts/run_lightweight.py' 'scripts/start_openmemory.py' 'run_api.py' 'src/openmemory/__init__.py' '.devflow/project-config.json'
git add 'src/openmemory/api/controllers.py' 'src/openmemory/api/server.py' 'src/openmemory/api/middleware/tenant_context.py' 'src/openmemory/api/middleware/structured_log.py'
# ...（其余 A-基线批文件逐项 add；含 error_handler.py / memory/session_persistent.py / utils/* 等混合文件，混合文件口径见 §1.5）
git status --short                                 # 复核：暂存区仅含 A-基线批 29 项；B 类 197 项、C 类 89 项与 S2 专属文件（§1.3）均为未暂存
git commit -m "chore: OpenMemory v7.2 基线收口（A 类联调前置 29 项；B 类 v7.0~v7.2 自身在途开发 197 项隔离不提交）"
git tag v7.2.0                                     # 可选：基线打 tag
```

> **v1.0.3 修订注记（禁止兜底 add）**：原模板的 `git add -A` 已在 v1.0.3 删除；B 类 197 项（v7.0~v7.2 子系统自身在途开发）与 C 类 89 项（含敏感文件 `.env.shared-infra`）**一律不得进入暂存区**。执行前须以 `git status --porcelain -uall` 复核并入参子系统清单 §6.2 的 29 项模板逐项 add。

**提交 2 — S2 五份文档（release/v7.3.0）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git switch -c release/v7.3.0                       # 自 v7.2 基线提交切 S2 分支
git add 'OpenMemory-S2-过滤行控与身份接入立项方案-v1.0.0.md' 'OpenMemory-S2-过滤行控与身份接入设计草案-v1.0.0.md' 'doc/development/OpenMemory-S2-过滤行控与身份接入-DevLogReport-v1.0.0.md' 'doc/test/OpenMemory-S2-过滤行控与身份接入-测试报告-v1.0.0.md' 'doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md'
git commit -m "docs(s2): OpenMemory S2 五份文档入库（立项方案 v1.1.0/设计草案 v1.0.3/DevLogReport v1.0.1/测试报告 v1.0.1/K07 矩阵填报 v1.0.1，[Approved] 段门禁全绿）"
```

**提交 3 — S2 源码、迁移与脚本**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git add 'src/openmemory/identity' 'src/openmemory/api/middleware/identity_gate.py' 'src/openmemory/api/middleware/block_subject_gate.py'
git add 'alembic/versions/v702_session_registry_meta.py' 'alembic/versions/v703_backfill_scope_ownership.py' 'alembic/versions/v704_identity_blocklist.py'
git add 'scripts/k07_endpoint_matrix.py' 'scripts/scope_backfill_report.py' 'scripts/scan_auto_purge.py' 'scripts/smoke_l3_2.py' 'scripts/api_baseline.json' 'scripts/verify-env'
git commit -m "feat(s2): S2 协议头入站/行控收口/复合唯一/存量回填/事件消费端/矩阵校验 源码与迁移（T1~T13，alembic v702~v704）"
```

**提交 4 — S2 测试用例与 CI 门禁**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git add 'tests/unit/test_s2_t*.py' 'tests/unit/test_l3_2_smoke.py' 'tests/unit/test_s2_segment_gate_selfcheck.py'
git add '.github/workflows/ci.yml'                 # 含 s2-k07-matrix-gate job（另含 v7.0 性能基线 hunk，见 §1.5 严格模式）
git commit -m "test(s2): S2 T1~T13 RED 断言与段门禁自检用例 + CI s2-k07-matrix-gate job"
git tag v7.3.0-rc.1                                # 可选：S2 收官打候选 tag
```

### 1.5 备注

- **B 类隔离（v1.0.3 修订，关键）**：2026-09-10 实测 364 项中 **B 类 197 项属 OpenMemory v7.0~v7.2 子系统自身在途开发**（自身功能 / 前端 / SDK / e2e / 运维 / 模块文档等），**非本次 S2 联调产物，必须隔离**——不得混入批 0~批 3 任一联调批次。原「`git add -A` 全量暂存 + 逐项 `git reset`」模板在 197 项未跟踪 B 类存在时**极易误纳**，v1.0.3 已改为逐清单显式 `git add`（见 §1.4）并在 §0 统一禁止兜底 add。
- **敏感与噪音排除（v1.0.3 修订）**：C 类 89 项一律排除——含敏感文件 **`.env.shared-infra`【不提交】**（另建议 `git log --all -- .env.shared-infra` 核查历史是否已泄露）、临时误落 4 项、一次性证据 57 项、运行期图像 `storage/images/**` 27 项。建议补 `.gitignore` 规则 **`.env.*`（保留 `!.env.example`）** 与 **`.devflow/state.json`**。
- **基线提交自检**：因混合文件（controllers.py/config.py/exceptions.py/structured_log.py/error_handler.py/session_persistent.py 等）与部分被扩展的既有测试随基线提交，**v7.2 基线提交可能无法独立全绿**；全量回归门禁以提交 4 之后为准（见 §1.6）。基线提交只核对「暂存区不含 §1.3 清单文件、源码可导入」。
- **严格拆分（可选）**：若要求 v7.2 基线不含任何 S2 增量，对混合文件（含 ci.yml）改用 `git add -p` 逐 hunk 选择——在提交 1 中仅收入 v7.2 基线 hunk（性能基线 job / 基线功能），在提交 3/4 用 `git add` 收入剩余 S2 hunk；`git add -p` 为交互式，需人工逐 hunk 确认。
- 若仓内版本发布惯例需同步 CHANGELOG/Release-Note，请在提交 1 前将 v7.2 版本登记纳入（随基线），S2 收官后按发布计划补 v7.3 版本文档。
- **frontend 冻结注记（v1.0.4，v1.0.x 修订：统一前端定案）**：本仓 `frontend/`（59 个已跟踪源文件，另含 `dist/` 构建产物）**已冻结、不再维护**，**不得进入批 0~批 3 任一联调批次**。本次实测在途 8 项 `frontend/**`（4 `M`：`frontend/src/App.tsx`、`frontend/src/api/index.ts`、`frontend/src/pages/Memories/index.tsx`、`frontend/src/pages/index.ts`；4 `??`：`frontend/src/api/orgs.ts`、`frontend/src/pages/AdminAlerts/index.tsx`、`frontend/src/pages/AdminTenantDetail/index.tsx`、`frontend/src/pages/AdminTenants/index.tsx`）已由分清单 §3.2/§3.3(l) 归 **B 类**隔离，**不属联调提交面**。另注：`deploy/nginx/conf.d/openmemory.conf:90` 仍以 `root /app/frontend/dist;` 承载 SPA（第 93 行 `try_files $uri $uri/ /index.html`），属**待改造项**（后端/部署不再挂载 frontend 产物），本次不入提交面。

### 1.6 提交后回归（OpenMemory）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
python -m pytest tests/unit tests/integration -q -p no:cacheprovider   # 期望 1330 passed, 36 skipped（1 项 caplog 顺序敏感 flaky，见 DevLogReport §7）
python -m ruff check src scripts                                       # 期望 0 错误
python scripts/k07_endpoint_matrix.py --verify --matrix 'doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md' --openapi scripts/api_baseline.json   # 期望退出码 0（缺口清零）
python scripts/smoke_l3_2.py                                           # L3-2 冒烟（本地契约桩）
# 可选迁移幂等复核：alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

## 2. OpenLLM 仓（D:\Trae CN\myproject\Dev\OpenLLM）

### 2.1 现状核对基线（2026-09-10 实测）

| 项目 | 值 |
|------|-----|
| HEAD | `a552cbf`（a552cbf41518e1ef17ca229ebe525f2fed481985，docs: v2.14.3 全流程关闭同步——v2.14.3 发布闭环） |
| 当前分支 | `feature/v2.13.0-openrag` |
| 工作树 | **v1.0.3 修订（清点口径修正）**：2026-09-10 实测**折叠口径** `git status --porcelain` = **430 项**（与初版登记一致）；**展开口径** `git status --porcelain -uall` = **1555 项**（`??` 1235 + `D` 211 + `M` 109）——两口径**不矛盾**，仅粒度不同。差额来源：`backend/.pylib/` 未跟踪第三方解包 **1157 项** + `.pyc` **282 项**（= 删除 211 + 修改 71，属历史误入库）+ `backend/data/*` 5 项 + `backup/` 6 项等被 `-uall` 展开；**上述噪音（C 类合计 1455）均不提交**。S0 探活等既有已审查项与 S4 全部产物（A 类 75：批 1 基线 15 / 批 2 文档 7 / 批 3 identity+中间件+配置 15 / 批 4 客户端与网关 15 / 批 5 scripts 8 / 批 6 tests 11）均未提交；另有 B 类 need-star 在途 13 项须隔离、需人工判定 12 项（以第 0 步实核为准） |
| S4 独立分支 | `feature/s4-identity-channel-b`（叠加位，见基线收口登记清单 §1.1；可与现分支二选一承载 S4 批次） |
| 基线登记清单 | `doc/planning/OpenLLM-S4-批次1基线收口登记清单-v1.0.0.md`（S4-T1 产出，文件分类 **A~E** 供引用：A=S0 探活/既有已审查放行项（不改造）、B=版本欠账对齐 v2.14.3、C=S4 承载版本 v2.15.0 拟仅登记不升级、D=S4 批次1 改动、E=未审查/噪音不提交） |

**第 0 步核对命令**（执行任何提交前先跑）：

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git log -1 --format='%H %s'                        # 期望 a552cbf...（v2.14.3 发布闭环）
git branch --show-current                          # 期望 feature/v2.13.0-openrag
(git status --porcelain).Count                     # 折叠口径核对（2026-09-10 实测 430，与初版登记一致）
git status --porcelain -uall | Measure-Object -Line  # v1.0.3 新增：展开口径核对（实测 1555 = ??1235 + D211 + M109）
git diff --cached --stat                           # 应无输出（无已暂存内容）
```

### 2.2 建议分支与提交顺序（基线 1 批 + S4 4~6 批）

- **阶段 1（基线批次）**：按基线收口登记清单 A~E 分类先落基线（S0 探活 + 版本对齐）——业务放行批次 = **A 类**（S0 探活/既有已审查放行项，如 `backend/tests/unit/test_dps_probe_real_health.py`、`test_external_identity.py`、`services/external_identity.py`、`edgerouter/orchestration/evaluate.py`、`test_real_contract_{profile,memory,rag}.py`、v2.13/v2.14 契约与 writeback 用例等，以清单 §1.1 登记为权威清单）＋ **B 类**（版本欠账对齐：仓根 `version.json`→2.14.3/2026-09-02、`backend/app/__init__.py __version__`→2.14.3）＋随行既有文档；**C 类** 仅登记（v2.15.0 拟，不做升级动作）；**E 类** 噪音（**v1.0.3 修订**：`backend/.pylib/` 未跟踪 1157 + `__pycache__` 下 `.pyc` 282 + `backend/data/*.db*` + `backup/` 等，C 类合计 **1455**）**均不提交**，建议独立「噪音清理批次」处理——**已入库 `.pyc` 用 `git rm -r --cached` 处置（13 个 `__pycache__` 目录、共 211 项，属历史误入库卫生债；禁止用 `git checkout`/`git restore` 恢复，否则重新污染版本库）** + `.gitignore` 增补（可选，见子系统清单 §4/§5.3）；该噪音批不得与 S4 批次混提。
- **批次数（v1.0.3 修订）**：维持 **6 批**（基线 1 + S4 5：文档 / identity 包·中间件·配置 / 客户端与网关·装配 / scripts / tests；scripts+tests 合批即 **5 批**）。原「批 6 tests 15 项」按清点总清单 §2.8-5 口径修正为 **11 项**（剔除 4 项 need-star 测试文件后），详见 §2.3 批 6 注记。
- **阶段 2（S4 批次）**：自阶段 1 基线提交切 `feature/s4-identity-channel-b`（或留在现分支叠加），按「**文档 → identity 包/中间件/配置 → 客户端与网关/装配 → scripts → tests**」分 **4~6 批**提交（默认 5 批；scripts+tests 合批即 4 批，文档按 开发/测试 拆开即 6 批）。
- 提交顺序总览：

| 序号 | 阶段/分支 | 提交内容 | 建议 commit 主题 |
|------|-----------|---------|-----------------|
| 1 | 基线（现分支 feature/v2.13.0-openrag） | A 类 S0 探活/既有已审查项 + B 类版本对齐（version.json/`backend/app/__init__.py`→v2.14.3） | chore: OpenLLM 基线收口（S0 探活 + 版本对齐 v2.14.3，按 S4-批次1基线收口登记清单 A~B） |
| 2 | feature/s4-identity-channel-b | S4 文档（仓根立项/草案 2 + doc/planning 基线登记 1 + doc/development DevLog 1 + doc/test 测试报告与 JT 台账 2 + doc/design K07 填报 1，共 7 份） | docs(s4): OpenLLM S4 文档入库（立项 v1.1.0/草案 v1.0.1/DevLog v1.0.1/测试报告 v1.0.1/JT 台账/K07 填报/基线登记清单） |
| 3 | feature/s4-identity-channel-b | `backend/app/identity/`（新包）+ `middleware/identity_gate.py`、`middleware/audit.py` + `core/config.py` + `services/external_identity.py` + `.env.example` | feat(s4): 身份接入收口 identity 包/中间件/配置（S4-T2 透传基座、S4-T9 强校验、S4-T10 审计六键、S4-T12 角色档位、S4-T13 M1/M2、S4-T14 配置键） |
| 4 | feature/s4-identity-channel-b | `edgerouter/adapters/{dps_client,openmemory_client,openrag_client,profile}.py` + `api/{openllm_gateway,writeback}.py` + `main.py` + `mock_services/*_stub.py` | feat(s4): 编排出站透传与网关装配（S4-T3 出站头统一/REAL 收口、S4-T4 REAL 双义拆分、S4-T6 服务账号守卫、S4-T7/T8 通道矩阵接线） |
| 5 | feature/s4-identity-channel-b | `backend/scripts/`（scan_real_fallback_business_usage / scan_identity_bypass / k07_endpoint_matrix / k07_isolation_registry / smoke_l3_2）+ `scripts/verify-env/` | chore(s4): S4 静态扫描/K07/verify-env/L3-2 脚本（S4-T11/T14/T15） |
| 6 | feature/s4-identity-channel-b | `backend/tests/unit/test_s4_t*.py`（t1~t15）+ `test_real_contract_profile.py`（S0 修订） | test(s4): S4 T1~T15 RED 断言与段门禁自检用例 |

> 合批/拆批说明：批 5+批 6 合并即 S4 四批（文档 / identity 包 / 客户端与网关 / scripts+tests+CI）；批 2 拆「开发/测试文档 + JT 台账」与「K07 填报」即 S4 六批。identity 与客户端/网关存在跨文件引用（external_identity/outbound/build_outbound_headers），不建议按 T 再细拆（中间提交可能不可独立回归）。

### 2.3 S4 放行文件清单（各批 add 集合，2026-09-10 实测归类）

```text
# 批 2（S4 文档，7 份，全部未跟踪）
OpenLLM-S4-通道B全面主用与身份接入收口立项方案-v1.0.0.md
OpenLLM-S4-通道B全面主用与身份接入收口设计草案-v1.0.0.md
doc/planning/OpenLLM-S4-批次1基线收口登记清单-v1.0.0.md
doc/development/OpenLLM-S4-通道B全面主用与身份接入收口-DevLogReport-v1.0.0.md
doc/test/OpenLLM-S4-通道B全面主用与身份接入收口-测试报告-v1.0.0.md
doc/test/OpenLLM-JT-台账-S4.md
doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md

# 批 3（identity 包/中间件/配置，新增 + 修改混合）
backend/app/identity/                    # __init__/protocol_headers/error_codes/request_id/role_map/identity_context/outbound/namespace/channel/exemptions/ab_equivalence/audit_identity
backend/app/middleware/identity_gate.py   # 新增
backend/app/middleware/audit.py           # 修改（审计 detail.identity 接线）
backend/app/core/config.py                # 修改（trust_mode/TRUSTED_PROXY_SOURCES 推导）
backend/app/services/external_identity.py # S0 基线既有（A 类登记）→ S4-T2 修订增量
backend/.env.example                      # 修改（S4 配置键示例）

# 批 4（客户端与网关/装配，修改混合；均含 A 类基线先落 + S4 增量）
backend/app/edgerouter/adapters/dps_client.py
backend/app/edgerouter/adapters/openmemory_client.py
backend/app/edgerouter/adapters/openrag_client.py
backend/app/edgerouter/adapters/profile.py
backend/app/api/openllm_gateway.py
backend/app/api/writeback.py
backend/main.py
backend/mock_services/profile_stub.py
backend/mock_services/openmemory_stub.py
backend/mock_services/openrag_stub.py

# 批 5（scripts，新增）
backend/scripts/scan_real_fallback_business_usage.py
backend/scripts/scan_identity_bypass.py
backend/scripts/k07_endpoint_matrix.py
backend/scripts/k07_isolation_registry.py
backend/scripts/smoke_l3_2.py
backend/scripts/verify-env/               # contract.json/verify_env.py/verify-env.ps1

# 批 6（tests，新增；test_real_contract_profile.py 为 S0 修订）
# v1.0.3 修订：4 项 need-star 测试文件已移出批 1 / 批 6，改归 B 类隔离（见 §2.5），不得在本批 add
backend/tests/unit/test_s4_t1_baseline_probe.py
backend/tests/unit/test_s4_t2_identity_base.py
backend/tests/unit/test_s4_t3_outbound_headers.py
backend/tests/unit/test_s4_t4_real_switch.py
backend/tests/unit/test_s4_t5_prefix_normalize.py
backend/tests/unit/test_s4_t6_service_account_profile.py
backend/tests/unit/test_s4_t7_channel_preference.py
backend/tests/unit/test_s4_t8_channel_matrix.py
backend/tests/unit/test_s4_t9_strong_verify.py
backend/tests/unit/test_s4_t10_audit_chain.py
backend/tests/unit/test_s4_t11_k07_matrix.py
backend/tests/unit/test_s4_t12_role_tiers.py
backend/tests/unit/test_s4_t13_m1_m2_modes.py
backend/tests/unit/test_s4_t14_verify_env.py
backend/tests/unit/test_s4_t15_l3_2_smoke.py
backend/tests/unit/test_real_contract_profile.py   # S0 修订
```

> 以上为 2026-09-10 实测工作树（总 430 项 porcelain）归类；基线批的 A/B 类文件以基线收口登记清单 §1.1 分类表为权威清单。执行前以 `git status --porcelain` 复核——清单外路径（含 openmemory.py/openrag.py/orchestration/既有 M 测试等未在本清单列出的文件）先确认归属：若属 S4 增量并入批 4，若属 v2.13/v2.14 既有基线并入批 1，**不要用 `git add -A` 兜底**。CI：2026-09-10 实测无 `.github` 改动；本仓既有 CI 运行 pytest 即天然覆盖 test_s4_t*（K07 注册表门禁由 k07 脚本/用例承载），如需独立 s4-k07-gate job 按仓内惯例补入 tests 批。

> **v1.0.3 修订（分类冲突纠正 + 条目数）**：`test_profile_component_phase1.py`、`test_writeback_w1_phase1.py`、`test_writeback_w2_phase1.py`、`test_writeback_w3_phase1.py` **共 4 项**经四仓清点核对确认属 **need-star 统一编排工作流（文档编号 `OB-INTG-LLM-NEEDSTAR`，v0.4.0~v0.6.0）在途产物**，非 S4 身份接入收口（T1~T15）范围，**已自基线批 1 / 批 6 移出并改归 B 类隔离**（隔离说明见 §2.5）。据此，批 6 条目数由 **15 → 11**（依据清点总清单 §2.8-5 口径；`test_real_contract_profile.py` 的 S0 增量修订仍保留在批 6）。

### 2.4 放行步骤与命令模板

**提交 1 — 基线批次（S0 探活 + 版本对齐）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git status --porcelain                          # 记录留底，核对 A/B 类归属（对照基线收口登记清单 §1.1）
# A 类：S0 探活/既有已审查项（示例，完整集合以清单 A 类登记为准）
git add 'backend/tests/unit/test_dps_probe_real_health.py' 'backend/tests/unit/test_external_identity.py' 'backend/app/services/external_identity.py' 'backend/app/edgerouter/orchestration/evaluate.py' 'backend/tests/unit/test_real_contract_profile.py' 'backend/tests/unit/test_real_contract_memory.py' 'backend/tests/unit/test_real_contract_rag.py' 'backend/tests/unit/test_v213_writeback_queue.py'
# v1.0.3 修订：4 项移出——原模板末尾的 'test_profile_component_phase1.py' 'test_writeback_w1_phase1.py'
#   'test_writeback_w2_phase1.py' 'test_writeback_w3_phase1.py' 已删除，改归 B 类隔离（need-star 统一编排
#   OB-INTG-LLM-NEEDSTAR，见 §2.5），不得在本基线批次 add
# B 类：版本欠账对齐 v2.14.3
git add 'version.json' 'backend/app/__init__.py'
# 随行既有文档（doc/release/Release-Note-v2.14.3 等，以 git status 复核为准）
git add 'doc/release/DevFlow-Release-Note-v2.14.3.md'
git status --short                               # 复核：仅 A/B/随行文档；S4 专属文件（identity 包/scripts/test_s4_*）保持未暂存
git commit -m "chore: OpenLLM 基线收口（S0 探活 + 版本对齐 v2.14.3，按 S4-批次1基线收口登记清单 A~B）"
# 可选：噪音清理批次（E 类：git rm -r --cached .pylib/__pycache__/data 等 + .gitignore 增补，单独一个 commit）
```

**提交 2 — S4 文档（feature/s4-identity-channel-b）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git switch -c feature/s4-identity-channel-b     # 自基线提交切 S4 分支（或留在现分支叠加）
git add 'OpenLLM-S4-通道B全面主用与身份接入收口立项方案-v1.0.0.md' 'OpenLLM-S4-通道B全面主用与身份接入收口设计草案-v1.0.0.md'
git add 'doc/planning/OpenLLM-S4-批次1基线收口登记清单-v1.0.0.md'
git add 'doc/development/OpenLLM-S4-通道B全面主用与身份接入收口-DevLogReport-v1.0.0.md'
git add 'doc/test/OpenLLM-S4-通道B全面主用与身份接入收口-测试报告-v1.0.0.md' 'doc/test/OpenLLM-JT-台账-S4.md'
git add 'doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md'
git commit -m "docs(s4): OpenLLM S4 文档入库（立项 v1.1.0/设计草案 v1.0.1 [Approved]；DevLog v1.0.1/测试报告 v1.0.1/JT 台账 [Approved]；K07 填报；基线收口登记清单）"
```

**提交 3 — identity 包/中间件/配置**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git add 'backend/app/identity'
git add 'backend/app/middleware/identity_gate.py' 'backend/app/middleware/audit.py'
git add 'backend/app/core/config.py' 'backend/app/services/external_identity.py' 'backend/.env.example'
git commit -m "feat(s4): 身份接入收口 identity 包/中间件/配置（S4-T2 透传基座、S4-T9 IdentityGate 强校验+豁免清单、S4-T10 审计六键、S4-T12 角色档位、S4-T13 M1/M2、S4-T14 配置键）"
```

**提交 4 — 客户端与网关/装配**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git add 'backend/app/edgerouter/adapters/dps_client.py' 'backend/app/edgerouter/adapters/openmemory_client.py' 'backend/app/edgerouter/adapters/openrag_client.py' 'backend/app/edgerouter/adapters/profile.py'
git add 'backend/app/api/openllm_gateway.py' 'backend/app/api/writeback.py'
git add 'backend/main.py'
git add 'backend/mock_services/profile_stub.py' 'backend/mock_services/openmemory_stub.py' 'backend/mock_services/openrag_stub.py'
git commit -m "feat(s4): 编排出站透传与网关装配（S4-T3 出站头统一/REAL 收口、S4-T4 REAL 双义拆分全启用、S4-T6 服务账号写守卫、S4-T7/T8 通道 B 主 A 备接线）"
```

**提交 5 — scripts（scan/k07/verify-env/smoke）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git add 'backend/scripts/scan_real_fallback_business_usage.py' 'backend/scripts/scan_identity_bypass.py'
git add 'backend/scripts/k07_endpoint_matrix.py' 'backend/scripts/k07_isolation_registry.py'
git add 'backend/scripts/smoke_l3_2.py' 'backend/scripts/verify-env'
git commit -m "chore(s4): S4 静态扫描/K07 矩阵与注册表/verify-env 契约键/L3-2 冒烟脚本（S4-T11/T14/T15）"
```

**提交 6 — tests（S4 T1~T15 + test_real_contract_profile S0 修订）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git add 'backend/tests/unit/test_s4_t*.py' 'backend/tests/unit/test_real_contract_profile.py'
git commit -m "test(s4): S4 T1~T15 RED 断言与段门禁自检用例 + test_real_contract_profile S0 修订（306 passed 口径）"
```

### 2.5 备注

- **B 类隔离（v1.0.3 修订，分类冲突纠正）**：4 项测试文件 `backend/tests/unit/test_profile_component_phase1.py`、`test_writeback_w1_phase1.py`、`test_writeback_w2_phase1.py`、`test_writeback_w3_phase1.py` 属 **need-star 统一编排工作流（工作流编号 `OB-INTG-LLM-NEEDSTAR`，v0.4.0~v0.6.0；写侧 W1/W2/W3 与读侧 Phase 1）在途产物**，**不属 S4 身份接入收口（T1~T15）**，已自基线批 1 / 批 6 移出并改归 **B 类隔离**。隔离要求：建议**独立分支 `feature/need-star-orchestration` + 独立批次 + 独立段门禁**，提交信息显式标注 `need-star` 而非 `s4`；与 S4 交付物存在跨文件引用（`writeback_queue.py` ↔ `api/writeback.py`、`profile_refine.py` ↔ `api/writeback.py`）时须保证批次内引用闭合，否则中间提交不可独立回归。
- **A 类文件双提交说明**：`backend/tests/unit/test_real_contract_profile.py`、`backend/app/services/external_identity.py` 等在基线收口登记清单登记为 A 类（基线批先落库），S4 段又有增量修订——提交 1 先落基线原样，提交 3/6 再以「修改」形式收 S4 增量（git 会显示为 M），无需在同一批重复 add 原文件。
- **无 CI 文件改动**：2026-09-10 实测工作树无 `.github` 相关路径；K07 隔离注册表门禁（新增端点无隔离用例拒绝）由 k07 脚本与 test_s4_t11 承载，注册独立 CI job 属可选（现场按仓内惯例）。
- **沙箱受限复核提醒（非沙箱清单）**：测试报告 §4 登记——① writeback.db 限写（真实写回链路 E2E）；② pgAdmin jwt→cryptography 原生 DLL 加载失败（全量 app openapi 导出/K07 全量底单/网关-编排顶层 import）；③ REAL 生产全启用部署断言（verify-env production profile）；④ git 提交受限（本清单放行）；⑤ S7 边界（写路径等价/K14/L2-1 演练终验/K07 RA-06/错误面收敛）。K07 全量端点底单导出（`python scripts/k07_endpoint_matrix.py --export-openapi <路径>`）为非沙箱复核面，提交后补导出并回填填报 doc。
- **frontend 冻结注记（v1.0.4，v1.0.x 修订：统一前端定案）**：本仓 `frontend/`（214 个已跟踪源文件，另含 `dist/`）**已冻结、不再维护**，**不得进入批 1~批 6 任一联调批次**（本次实测 `git status` 无 `frontend` 条目）。另注：`docker-compose.yml:141-172` 仍定义 `frontend` 服务（build `./frontend` / `Dockerfile.dev`）、`docker-compose.prod.yml:19` 仍以 `- ./frontend/dist:/usr/share/nginx/html:ro` 挂载产物、`frontend/Dockerfile` 与 `frontend/nginx.conf` 仍构成前端构建-发布链，均属**待改造项**（后端/部署不再挂载其产物、不再构建发布），本次不入提交面。

### 2.6 提交后回归（OpenLLM）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM\backend'
python -B -m pytest tests/unit -p no:cacheprovider        # 期望 S4 全组 + 受影响回归全绿（306 passed 口径，见测试报告 §5）
python -m ruff check app scripts tests/unit               # 期望 0 错误（backend/ruff.toml；以新增/改动文件为准）
python scripts/scan_real_fallback_business_usage.py       # 期望 0 命中（REAL_* 不作为业务身份）
python scripts/scan_identity_bypass.py                    # 期望 0 绕过
python scripts/k07_endpoint_matrix.py --verify            # K07 矩阵/隔离注册表核对（期望退出码 0 = 缺口清零/无漂移）
python scripts/verify-env/verify_env.py --fail-fast       # verify-env 对账（dev 全 pass；production REAL 期望拦截为复核面）
python scripts/smoke_l3_2.py                              # L3-2 冒烟 + 段门禁自检五项（期望退出码 0；真实 HTTP 双签登记非沙箱复核）
```


## 3. DPS 仓（D:\Trae CN\myproject\Dev\DPS）

### 3.1 现状核对（**v1.0.3 修订**：2026-09-10 四仓清点实测）

| 项目 | 值 |
|------|-----|
| HEAD | `6b39dd4`（fix: S0 门禁补充——Tenant 白名单补 /docs /redoc（R1 真实服务验证发现）+ 核对文档 v1.0.1） |
| 当前分支 | `main` |
| 工作树 | **`git status --porcelain -uall` = 57**（11 M + 46 ??）——**非登记预估「约 47 项」**；其中 **A 联调 52**（S5-B1~B4）、**B 类自身在途 3**（v2.9.0 文档，须隔离）、C 类噪音 2；需人工判定 3（⊂ A，不重复计数） |
| 上游登记口径差异 | 初版 §3.1 仅登记 **3 ?? v2.9.0 文档（1 批）**，与实测口径不同：该 3 份 v2.9.0 文档实为 **B 类隔离项、不属 S5 联调**；S5 联调产物 52 项此前未被登记（DPS S5 段当时尚未收口） |

### 3.2 建议分支与提交顺序（**v1.0.3 修订**：1 批 → **4 批**）

留在 `main`，按 S5 四批提交（B1 → B2 → B3 → B4；B3 的 `ci.yml` 门禁依赖 `scripts/k07_endpoint_matrix.py`，须与之**同批或后于**脚本提交）：

| 批次 | 内容 | 条目数 |
|------|------|:---:|
| S5-B1 | 身份内核 / 配置 / 装配（`src/identity/*`、`src/middleware/*_gate_middleware.py`、`src/engines/identity_event_engine.py`、`src/config.py`、`src/database.py`、`src/main.py`、`src/rest_api/app.py`、`src/rest_api/error_handlers.py` 等） | 19 |
| S5-B2 | 路由 / 权限 / 审计 / 测试 | 17 |
| S5-B3 | 脚本 / 门禁 / 证据（`scripts/k07_endpoint_matrix.py`、对账报告、verify-env 契约、门禁自检证据等） | 8 |
| S5-B4 | 联调文档（S5 立项 / 设计 / K07 填报 / 裁定映射 / 建模评审 / DevLog / 测试报告） | 8 |

> 批次措辞对齐子系统清单口径「**B1 内核装配 / B2 路由权限测试 / B3 脚本门禁证据 / B4 联调文档**」；逐文件 `git add` 集合以《DPS-联调产物待提交清单-v1.0.0》§2 为权威清单，**禁止兜底 add**。

### 3.3 命令模板

> **S5 段门禁批准登记（v1.0.5，2026-09-10）**：**S5 段门禁已于 2026-09-10 人工批准、可进入入仓**。批准口径=`2026-09-10 S5 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认、段门禁自检五项全绿（Pull 真实 HTTP 双签 PENDING 挂起登记不阻断）、遗留=无阻断项`。**执行依据**：《DPS-联调产物待提交清单-v1.0.0》（OB-DPS-CLEARANCE-v1.0.0，`D:\Trae CN\myproject\Dev\DPS\doc\planning\DPS-联调产物待提交清单-v1.0.0.md`）§2 逐文件表与 §6.1 分批 `git add` 模板；本清单 §3.2 的 **S5-B1 内核装配 19 / S5-B2 路由权限测试 17 / S5-B3 脚本门禁证据 8 / S5-B4 联调文档 8** 四批与该分清单一致（禁止兜底 add）。DPS 侧四项文档（DevLogReport / 测试报告 / K07 端点-过滤矩阵填报 / 设计草案）已随门禁批准回写至内部版本 **v1.0.1**（文件名版本不变，按现文件名登记入仓）；K07 门禁 `total=169 covered=134 exempt=35 gaps=0` 缺口清零，Pull 真实 HTTP 双签 PENDING 挂起登记（Q-DPS-5）随证据文件如实入仓标注。

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
git status --porcelain -uall                    # 核对 57 项（v1.0.3：11 M + 46 ??）
# S5-B1（示例，完整 19 项见子系统清单 §2）
git add 'src/identity' 'src/middleware/identity_gate_middleware.py' 'src/middleware/block_subject_gate_middleware.py' 'src/engines/identity_event_engine.py'
git add 'src/config.py' 'src/database.py' 'src/main.py' 'src/rest_api/app.py' 'src/rest_api/error_handlers.py'
git commit -m "feat(s5): 身份内核/配置/装配（S5-T1 门禁、T3/T4 write guard、T6 事件双通道、T8 审计、T9 角色映射）"
# S5-B2 / S5-B3 / S5-B4 按子系统清单 §2 分批显式 add + commit（禁止 git add -A / git add . 兜底）
# B 类隔离（独立批次、独立 commit message，不混入 S5 批次）：
# git add 'doc/design/DPS-画像模板与标注模板扩展设计文档-v2.9.0.md' 'doc/design/DPS-设计评审记录-v2.9.0.md' 'doc/requirements/DPS-功能需求清单-v2.9.0.md'
# git commit -m "docs(v2.9.0): DPS 画像/标注模板扩展设计、评审记录与功能需求清单入库（非 S5 联调，隔离）"
```

> **B 类隔离清单（v2.9.0 在途，3 项，不得混入 S5 批次）**：`doc/design/DPS-画像模板与标注模板扩展设计文档-v2.9.0.md`、`doc/design/DPS-设计评审记录-v2.9.0.md`、`doc/requirements/DPS-功能需求清单-v2.9.0.md`。
>
> **噪音提示（C 类 2 项，不提交）**：`.ruff_cache/CACHEDIR.TAG`、`src/dps.db-journal`；另注意 `data/dps.db` 与 `.env.shared-infra` 已在忽略范围，**不提交**。
>
> **历史卫生债（登记待修，不入本次提交面）**：DPS 仓 `.gitignore` **末尾存在无效绝对路径规则**，登记为待修项；另起卫生提交（`git rm --cached` + 修正忽略规则）处理，**不纳入本次 S5 批次**。
>
> **frontend 冻结注记（v1.0.4，v1.0.x 修订：统一前端定案）**：本仓 `frontend/`（63 个已跟踪源文件，React+Vite+TS，无 `dist/`）**已冻结、不再维护**，**不得进入 S5-B1~B4 任一联调批次**（本次实测 `git status` 无 `frontend` 条目，分清单 §4.4 C-11 已登记为非 A 类卫生项）；其构建/测试仅存在于 `.github/workflows/ci.yml`（第 73/76、119/122、169/172、218/221、227、237 行），属**待改造项**（不再构建），本次不入提交面。后端无静态挂载（`Dockerfile` 仅 `COPY src/`，`docker-compose.yml` 仅 `dps`+`redis` 两服务），无后端挂载改造项。

### 3.4 提交后回归（DPS）

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
python -m pytest tests -q        # 以仓内 pytest 配置为准
```

## 4. OpenRAG 仓（D:\Trae CN\myproject\Dev\OpenRAG）

### 4.1 现状核对基线（**v1.0.3 修订**：2026-09-10 四仓清点实测）

| 项目 | 值 |
|------|-----|
| HEAD | `959ef83`（959ef837a814a68d1f0efd03130d58ff251ef0dd，docs(v1.9.1): 发布文档同步——v1.9.1 发布闭环） |
| 当前分支 | `master` |
| 工作树 | **v1.0.3 修订（登记 54 → 实测 67）**：2026-09-09 初版登记为 **22 M + 32 ?? = 54 项**；2026-09-10 实测为 **22 M + 45 ?? = 67 项**（`git status --porcelain -uall`，本仓无折叠差分；identity/ 内 `.pyc`、`__pycache__`、`*.log` 属忽略项不计入 67）；**净增 13 项未跟踪文件全部为 S3 批次 3（T8~T11）产物**，与 S3 DevLogReport「改动清单（批次 3）」逐项对齐、无清单外新增（13 项摘要见下方 §4.1-A）；**无历史未提交基线**（工作树改动全部属 S3 段，无 v1.x 旧版本滞留改动） |
| S3（v1.10.0 拟）产物 | 全部位于已修改/未跟踪工作树，因 git 沙箱受限尚未提交；无 alembic，迁移走 `src/openrag/storage/migrations.py` 幂等迁移器（create_all/DDL） |
| 放行批次（v1.0.3 修订） | **4 批**：S3-B1 文档（6）/ S3-B2 identity·中间件·配置（25）/ S3-B3 storage·迁移·路由（12）/ S3-B4 scripts·tests·CI（24）；合计 4 提交（可合并 3） |

**第 0 步核对命令**（执行任何提交前先跑）：

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git log -1 --format='%H %s'                        # 期望 959ef83...（v1.9.1 发布闭环）
git branch --show-current                          # 期望 master
(git status --porcelain).Count                     # 核对总行数（v1.0.3 修订：2026-09-09 登记 54=22M+32??；2026-09-10 实测 67=22M+45??；本仓 -uall 与折叠口径一致）
git diff --cached --stat                           # 应无输出（无已暂存内容）
```

### 4.1-A v1.0.3 净增 13 项（S3 批次 3：T8~T11）文件名摘要

> 依据《OpenRAG-联调产物待提交清单-v1.0.0》§1.3，2026-09-10 实测相对初版 54 项**净增 13 项未跟踪文件**，全部为 S3 批次 3（T8~T11）产物；**批次数 4（S3-B1~B4）明确**，13 项分别并入下列批次：

| 序号 | 新增文件（相对初版 54 项） | 归属 | 并入批次 |
|:---:|------|------|:---:|
| 1 | `OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md` | S3 立项（文档） | S3-B1 |
| 2 | `OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md` | S3 设计（文档） | S3-B1 |
| 3 | `doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md` | S3-T8 / K07 | S3-B1 |
| 4 | `doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json` | S3-T8 / K07 | S3-B1 |
| 5 | `doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md` | S3 开发记录 | S3-B1 |
| 6 | `doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md` | S3 测试报告 | S3-B1 |
| 7 | `scripts/k07_endpoint_matrix.py` | S3-T8 | S3-B4 |
| 8 | `scripts/smoke_l3_2.py` | S3-T11 | S3-B4 |
| 9 | `scripts/tenant_backfill_report.py` | S3-T2 | S3-B4 |
| 10 | `scripts/verify_env_contract.py` | S3-T10 | S3-B4 |
| 11 | `scripts/verify-env/contract.json` | S3-T10 | S3-B4 |
| 12 | `tests/unit/test_isolation_matrix_endpoints.py` | S3-T8 / K07 | S3-B4 |
| 13 | `tests/unit/test_s3_t11_l3_2_smoke.py` | S3-T11 | S3-B4 |

> 回写影响：§4.3 的四批 add 集合须按上表增补这 13 项（第 1~6 项归批 1；第 7~13 项归批 4）；§4.1 第 0 步 `(git status --porcelain).Count` 期望值 54 → **67**。

### 4.2 建议分支与提交顺序

- **提交 1~4（S3 批次）**：自 `master`（959ef83）切出 `release/v1.10.0`（S3 规划承载版本 v1.10.0 拟，Q-RG-1 定案），在分支上按「文档 → identity/中间件/配置 → storage/迁移/路由 → scripts/tests/CI」四批提交。因**无历史未提交基线**，无需基线提交；`git switch -c` 切分支不丢工作树改动。**v1.0.3 修订**：批次数维持 **4（S3-B1~B4）**，对应实测 67 项 A 类产物（原登记 54 项 + 净增 13 项，见 §4.1-A）；如需合并即 3 批。
- 提交顺序总览：

| 序号 | 分支 | 提交内容 | 建议 commit 主题 |
|------|------|---------|-----------------|
| 1 | release/v1.10.0 | S3 六份文档（仓根立项/设计草案 + doc/design K07 填报 md+matrix.json + doc/development DevLog + doc/test 测试报告） | docs(s3): OpenRAG S3 六份文档入库 |
| 2 | release/v1.10.0 | identity 包 + api/middleware（identity_gate/block_subject_gate/role_gate）+ 配置/装配/错误面/审计（settings/deps/main/router middleware/core exceptions/responses/exception_handlers/audit_logger） | feat(s3): 身份接入收口 identity/中间件/配置（协议头四态+B1、级联阻断、角色档位、审计六键、事件消费端、M1/M2） |
| 3 | release/v1.10.0 | storage（migrations/postgres/sqlite）+ models（collection/document/chunk）+ api/routes（collections/documents/index/pageindex/query）+ orchestrator/rag | feat(s3): 数据隔离 storage/迁移/路由（归属列幂等迁移+保留码回填+B2 碰撞防护、行控强制注入、复合唯一 409） |
| 4 | release/v1.10.0 | scripts（k07_endpoint_matrix/tenant_backfill_report/scan_*×4/smoke_l3_2/verify_env_contract/verify-env）+ tests（test_s3_*、test_isolation_matrix_endpoints、既有文档路由回归）+ run_tests.py + ci-cd.yml | test(s3): S3 T1~T11 RED 断言/K07 矩阵隔离用例/静态门禁与 L3-2 冒烟 + CI s3-static-gates job |

> 如需合并为 **3 批**：将批 2 + 批 3 合并为「源码一批」（文档 → 源码 → scripts/tests/CI）；不建议更细拆分（identity 与 storage/路由跨文件复用，按 T 拆会造成中间提交不可独立回归）。

### 4.3 S3 放行文件清单（四批 add 集合，2026-09-09 实测）

```text
# 批 1：六份文档（全部未跟踪）
OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md
OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md
doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md
doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json
doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md
doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md

# 批 2：identity / 中间件 / 配置 / 装配 / 审计（新增 + 已修改混合）
src/openrag/identity/                    # protocol_headers/verdict/inbound_gate/blocklist/event_consumer/role_map/tenancy/agent_principal/audit_identity/context/delegation_notes/error_codes/scope_exemption/__init__
src/openrag/api/middleware/identity_gate.py
src/openrag/api/middleware/block_subject_gate.py
src/openrag/api/middleware/role_gate.py
src/openrag/config/settings.py
src/openrag/api/deps.py                   # BlockSubjectGate resolver 装配 + store scope 注入入口
src/openrag/main.py                       # 中间件装配顺序
src/openrag/router/middleware.py          # B1：EdgeRouterMiddleware deprecated/不装配
src/openrag/core/exceptions.py            # 错误码扩展
src/openrag/api/responses.py              # 响应信封 request_id/detail
src/openrag/api/exception_handlers.py     # detail/request_id 映射
src/openrag/security/audit_logger.py      # detail.identity 六键注入

# 批 3：storage / 迁移 / 模型 / 路由 / 编排（新增 + 已修改混合）
src/openrag/storage/migrations.py         # s3_tenant_columns/s3_tenant_collision_guard/s3_composite_unique/s3_scope_exemption/s3_identity_blocklist 幂等迁移器
src/openrag/storage/postgres.py
src/openrag/storage/sqlite.py
src/openrag/models/collection.py          # tenant_code 归属位
src/openrag/models/document.py
src/openrag/models/chunk.py
src/openrag/api/routes/collections.py     # 域过滤/复合唯一 409
src/openrag/api/routes/documents.py
src/openrag/api/routes/index.py
src/openrag/api/routes/pageindex.py
src/openrag/api/routes/query.py           # 检索统一入口域过滤
src/openrag/orchestrator/rag.py           # 写链行控/幂等

# 批 4：scripts / tests / CI（新增 + 已修改混合）
scripts/k07_endpoint_matrix.py
scripts/tenant_backfill_report.py
scripts/scan_auto_purge.py
scripts/scan_no_edgerouter_assembly.py
scripts/scan_no_identity_header_bypass.py
scripts/scan_tenant_scope.py
scripts/smoke_l3_2.py
scripts/verify_env_contract.py
scripts/verify-env/                        # contract.json（schema v2，键分组）
tests/unit/test_s3_*.py                    # test_s3_t1~t11、test_s3_b2_backlog_closure
tests/unit/test_isolation_matrix_endpoints.py
tests/unit/api/test_api_routes_documents_text.py   # 既有文档路由回归（9 passed 保持语义）
run_tests.py                               # S3_SCAN_GATE_MODULES + 启动 env setdefault
.github/workflows/ci-cd.yml                # s3-static-gates job
```

> 以上为 2026-09-09 实测工作树（22 M + 32 ??）归类；**v1.0.3 修订：2026-09-10 实测为 22 M + 45 ?? = 67 项，净增 13 项（S3 批次 3：T8~T11）已并入本清单各批（6 项归批 1、7 项归批 4，逐项见 §4.1-A）**；执行前以 `git status --porcelain -uall` 复核，若出现清单外路径先确认归属后再并入对应批次，**不要用 `git add -A` 兜底**。

### 4.4 放行步骤与命令模板

**切分支（提交 1 前）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git switch -c release/v1.10.0                  # 自 master(959ef83) 切 S3 分支（工作树改动原样保留）
```

**提交 1 — S3 六份文档（release/v1.10.0）**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md' 'OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md'
git add 'doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md' 'doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json'
git add 'doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md' 'doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md'
git commit -m "docs(s3): OpenRAG S3 六份文档入库（立项 v1.1.0/设计草案 v1.0.1 [Approved]；DevLog v1.0.1 [Approved]/测试报告 v1.0.0/K07 填报 v1.0.0）"
```

**提交 2 — identity/中间件/配置**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'src/openrag/identity' 'src/openrag/api/middleware/identity_gate.py' 'src/openrag/api/middleware/block_subject_gate.py' 'src/openrag/api/middleware/role_gate.py'
git add 'src/openrag/config/settings.py' 'src/openrag/api/deps.py' 'src/openrag/main.py' 'src/openrag/router/middleware.py' 'src/openrag/core/exceptions.py' 'src/openrag/api/responses.py' 'src/openrag/api/exception_handlers.py' 'src/openrag/security/audit_logger.py'
git commit -m "feat(s3): 身份接入收口 identity/中间件/配置（S3-T1 协议头白名单四态+B1、S3-T5 级联阻断事件消费端、S3-T6 D-V 映射、S3-T7 审计六键、S3-T9 角色档位、S3-T10 M1/M2 trust_mode）"
```

**提交 3 — storage/迁移/路由**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'src/openrag/storage/migrations.py' 'src/openrag/storage/postgres.py' 'src/openrag/storage/sqlite.py'
git add 'src/openrag/models/collection.py' 'src/openrag/models/document.py' 'src/openrag/models/chunk.py'
git add 'src/openrag/api/routes/collections.py' 'src/openrag/api/routes/documents.py' 'src/openrag/api/routes/index.py' 'src/openrag/api/routes/pageindex.py' 'src/openrag/api/routes/query.py' 'src/openrag/orchestrator/rag.py'
git commit -m "feat(s3): 数据隔离 storage/迁移/路由（S3-T2 归属列幂等迁移+保留码 openrag-local 回填+B2 碰撞防护、S3-T3 行控强制注入、S3-T4 复合唯一 409、query 检索域过滤）"
```

**提交 4 — scripts/tests/CI**

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git add 'scripts/k07_endpoint_matrix.py' 'scripts/tenant_backfill_report.py' 'scripts/scan_auto_purge.py' 'scripts/scan_no_edgerouter_assembly.py' 'scripts/scan_no_identity_header_bypass.py' 'scripts/scan_tenant_scope.py' 'scripts/smoke_l3_2.py' 'scripts/verify_env_contract.py' 'scripts/verify-env'
git add 'tests/unit/test_s3_*.py' 'tests/unit/test_isolation_matrix_endpoints.py' 'tests/unit/api/test_api_routes_documents_text.py'
git add 'run_tests.py' '.github/workflows/ci-cd.yml'
git commit -m "test(s3): S3 T1~T11 RED 断言/K07 矩阵隔离用例/四静态扫描与 L3-2 冒烟脚本 + CI s3-static-gates job"
git tag v1.10.0-rc.1                               # 可选：S3 收官打候选 tag
```

### 4.5 备注

- **无基线提交**：HEAD 959ef83=v1.9.1 干净基线，工作树改动全部属 S3（与 OpenMemory 的 v7.0~v7.2 未提交基线不同），无需「基线剔除」步骤；四批只是提交卫生切分。
- **中间批次回归**：批 2/批 3 为跨文件耦合源码（identity 与 storage/路由互相引用、既有测试随行扩展），**单批不一定能独立全绿**；全量回归门禁以批 4 之后为准（见 §4.6），各批提交前只核对「暂存区仅含预期路径」。
- **既有基线失败**：3 个枚举大小写类既有失败与本批无关（测试报告 §5 K-1 登记延续），不作为 S3 门禁口径；如仓内惯例需同步 CHANGELOG/Release-Note，S3 收官后按发布计划补 v1.10.0 版本文档。
- **frontend 冻结注记（v1.0.4，v1.0.x 修订：统一前端定案）**：本仓 `frontend/`（125 个已跟踪源文件，另含 `dist/`）**已冻结、不再维护**，**不得进入 S3-B1~B4 任一联调批次**（本次实测 `git status` 无 `frontend` 条目，分清单 §2 各表亦无 `frontend` 条目）。其独立构建链 `.github/workflows/frontend-ci.yml` 属**待改造项**（不再构建）；后端无静态挂载（`docker/Dockerfile` 仅 `COPY src/` 与 `COPY config/`，`docker/docker-compose.yml` 无 frontend 服务），无后端挂载改造项。文档口径同步：v1.9.0 单版本规划已记「frontend-ci.yml（前端集成随统一前端壳交付）」。

### 4.6 提交后回归（OpenRAG）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
python -B -m pytest tests/unit -p no:cacheprovider            # 期望 S3 组 144 用例恒绿；既有基线除 3 个枚举大小写登记项外全绿
python -m ruff check src scripts tests/unit                   # 期望 0 错误（若含既有噪声，以新增/改动文件为准，见 DevLog §5）
python scripts/scan_no_edgerouter_assembly.py                  # 四静态扫描门禁：期望逐条退出码 0
python scripts/scan_no_identity_header_bypass.py
python scripts/scan_tenant_scope.py
python scripts/scan_auto_purge.py
python scripts/k07_endpoint_matrix.py                          # K07 矩阵核对（默认即核对模式；期望退出码 0 = 缺口清零/无漂移）
python scripts/smoke_l3_2.py                                   # L3-2 冒烟 + 段门禁自检五项（期望退出码 0；真实双签挂起登记不阻断）
python scripts/verify_env_contract.py --fail-fast              # 可选：verify-env 契约键对账（trust_mode 推导一致）
```

## 5. OpenBase 仓（D:\Trae CN\myproject\Dev\OpenBase）

| 项目 | 值 |
|------|-----|
| 当前分支 | `main` |
| HEAD | **v1.0.3 修订**：实测 **`cdfbd5b`**（docs(intg): S4 台账回写与跨仓放行清单更新）；`0713ec1`（feat(identity): 身份事件单向列表契约端点 GET /identity/events，Q-DESIGN-1 冻结）**仍为单据参考锚点**——`0713ec1` 为契约冻结提交，其后已有 `1a6f3d4`（S2 回写）、`a5dcd2b`（S3 回写）、`cdfbd5b`（S4 回写）三次 docs(intg) 提交 |
| 工作树 | **v1.0.3 新增**：2026-09-10 实测 `git status --porcelain` = **7 项，全部为 `??` `dogfood-output/` 走查产物**（`evidence/*.json` 5 个 + `report.md` + `screenshots/`），**不提交、无联调产物** |
| 放行需求 | **已全部提交，无需放行**。跨系统 S2/S3 联调相关 OpenBase 侧改动已随 0713ec1 及此前 S1b（P2-1）链完成；S4（OpenLLM）段 OpenBase 侧为纯台账文档回写（任务卡 v1.5.0 → v1.6.0） |

- 本次沙箱内已完成并提交（docs(intg)：S2 台账回写与跨仓提交放行清单）：`OpenBase-数据隔离实现任务卡-v1.0.0.md`（v1.3.0 → v1.4.0 回写）与本清单文件 v1.0.0，commit hash 见最终执行记录。
- 本次沙箱内再次提交（docs(intg)：S3 台账回写与跨仓提交放行清单更新）：任务卡 v1.4.0 → v1.5.0（S3/OpenRAG 段回写）、本清单 v1.0.0 → v1.0.1（§4 新增 OpenRAG S3 放行批次），commit hash 见最终执行记录。
- 本次沙箱内第三次提交（docs(intg)：S4 台账回写与跨仓提交放行清单更新）：任务卡 v1.5.0 → v1.6.0（S4/OpenLLM 段回写）、本清单 v1.0.1 → v1.0.2（§2 改写为 OpenLLM 基线 + S4 放行批次），commit hash 见最终执行记录。
- 仓库内 `dogfood-output/` 未跟踪文件属走查产物（**v1.0.3 修订：实测 7 项**，即 `evidence/after-login.json`、`evidence/e2e_full.json`、`evidence/gateway_probe.json`、`evidence/portrait_retry.json`、`evidence/recon.json`、`report.md`、`screenshots/`），**不属于放行范围**，请勿误提交。
- **v1.0.3 修订（OpenBase 自身清点结论）**：本仓本次联调**无任何联调产物待提交**（A 联调 = 0），工作树 7 项全部为上述 `dogfood-output/` 噪音（C 类，不提交）；HEAD 已由 `0713ec1` 漂移至 `cdfbd5b`。此为本次唯一涉及 OpenBase 自身的差异，**不影响四仓放行结论**。
- **v1.0.7 新增（S6 前端段提交批次登记）**：S6（统一前端段）已于沙箱内分批提交并入库，提交号如下（**S6 提交面仅 `openbase-ui/**` + 仓根/`doc/**` 文档 + `doc/test/evidence/s6/**` 证据；不含任何子系统 `frontend/` 文件**）：

  | 批次 | 提交 hash | 主题 |
  |:---:|------|------|
  | 批 1 | `2abe52a` | `feat(ui): S6-T1 统一前端冻结与改造口径登记 + lint 转绿` |
  | 批 2 | `aa6c5bd` | `feat(ui): S6-T2 模块导航壳与 S6-T3 隔离呈现回归 + 发布形态参数化` |
  | 批 3 | `72b19da` | `feat(ui): S6-T4 登录态与吊销回归（安全回跳/单飞刷新/403 无白屏/OIDC 清理）` |
  | 批 4 | `477eb80` | `feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写` |

  - 段门禁结论见 §0「S6 段门禁结论加注」；证据索引 `doc/test/evidence/s6/**`；承载版本 `openbase-ui/package.json` = **1.3.0**（`dist-v1.3.0`）。本条**仅加注**：§5 表「放行需求」「HEAD」「工作树」行原文与四仓放行口径均不变；未对四仓执行任何 git 写操作。

## 6. 提交后跨仓联调回归提示

OpenMemory 提交 4、OpenRAG 提交 4 与 OpenLLM 提交 6 就绪后（OpenBase `0713ec1` 契约已就位；**v1.0.3 修订：OpenBase 当前 HEAD 实测 `cdfbd5b`，`0713ec1` 仍为契约参考锚点**），进入**真实 HTTP 双签联调窗口**（移交部署/联调窗口与 S7，依据 S2 设计草案 v1.0.3 / OpenRAG S3 设计草案 v1.0.1 / OpenLLM S4 设计草案 v1.0.1 批准注记）：

1. OpenBase 侧拉起 `GET /api/v1/identity/events`（契约文档 doc/design/OpenBase-事件消费契约-v1.0.md，commit 0713ec1 冻结）。
2. OpenMemory 侧 PullChannel 以真实 HTTP 拉取事件列表，验证事件 `apply`（阻断集落库）、`event_id` 幂等（重复拉取不双写）、`blocked/{subject_id}` 查询生效。
3. 逐仓回归命令汇总：OpenMemory（§1.6）、OpenLLM（§2.6）、DPS（§3.4）、OpenRAG（§4.6），OpenBase 以 AGENTS.md 为准：`python -m pytest tests` + `python -m ruff check openbase tests`。
4. 原则边界①：事件通道属身份权威同步面，**不纳入** S7 主备切换演练矩阵；L3-2 冒烟用例以契约桩回放断言（已绿）为本地基线，真实通道结果作为 S7 级联验证输入。
5. OpenRAG（S3）侧在其 §4.6 回归通过后进入同一联调窗口：配置 `OPENRAG_L3_2_REAL_DOUBLE_SIGN_BASE_URL`，以 OpenBase 0713ec1 契约端点为真实事件源补跑 Pull 真实 HTTP 双签（Q-RG-7 挂起登记，门禁登记项完成前不视为最终通过），并回填 OpenRAG DevLog/测试报告与任务卡 v1.5.0 卡尾 S3 摘要；PG/Redis 实跑补验随部署验证窗口执行。
6. OpenLLM（S4）侧在其 §2.6 回归通过后进入同一联调窗口（登记非沙箱复核，见 OpenLLM S4 测试报告 §4）：配置 REAL 主用/B 主编排相关开关后补跑 `smoke_l3_2.py` 真实 HTTP 双签与 DPS 画像读/OM recall/RG 检索读路径联调（L2-2 矩阵 A/B 等价读路径），并回填 OpenLLM DevLog/测试报告与任务卡 v1.6.0 卡尾 S4 摘要；写路径等价/K14 幂等/L2-1 真实切换演练/L2-2 终验/K07 RA-06 终验引用随 S7 段执行（OpenLLM 不在事件消费端名单，Pull 真实双签不适用，Q-LL-9）。

## 7. 各仓清点清单索引（v1.0.3 新增）

> 依据《OpenBase-联调产物清点核对总清单-v1.0.0》（OB-INTG-CLEARANCE-v1.0.0，[Review]，2026-09-10 四仓只读清点核对）§3 与 §4.1 会签流程，以下**五份清单文件**为本次跨仓入仓执行的**逐文件权威依据**（本清单 §1~§5 的批次与文件集合均应对齐之）：

| 序号 | 清单文件（绝对路径） | 文档编号 | 覆盖范围 | 关键计数 |
|:---:|------|------|------|------|
| 1 | `D:\Trae CN\myproject\Dev\OpenBase\doc\planning\OpenBase-联调产物清点核对总清单-v1.0.0.md` | OB-INTG-CLEARANCE-v1.0.0 | 五仓总汇总 + 差异回写建议 + 逐仓指引 + 会签流程 | 7 条差异 / 10 条回写建议 |
| 2 | `D:\Trae CN\myproject\Dev\OpenMemory\doc\planning\OpenMemory-联调产物待提交清单-v1.0.0.md` | OB-OM-CLEARANCE-v1.0.0 | OpenMemory | status 364 = A 70 + B 197 + C 89 + 人工 8 |
| 3 | `D:\Trae CN\myproject\Dev\OpenRAG\doc\planning\OpenRAG-联调产物待提交清单-v1.0.0.md` | OB-RG-CLEARANCE-v1.0.0 | OpenRAG | status 67 = A 67 + B 0 + C 0 + 人工 0 |
| 4 | `D:\Trae CN\myproject\Dev\OpenLLM\doc\planning\OpenLLM-联调产物待提交清单-v1.0.0.md` | OB-LL-CLEARANCE-v1.0.0 | OpenLLM | `-uall` 1555 = A 75 + B 13 + C 1455 + 人工 12 |
| 5 | `D:\Trae CN\myproject\Dev\DPS\doc\planning\DPS-联调产物待提交清单-v1.0.0.md` | OB-DPS-CLEARANCE-v1.0.0 | DPS | status 57 = A 52 + B 3 + C 2（人工 3 ⊂ A） |

**入仓执行流程（引用总清单 §4.1 会签流程）**：

1. **各子系统按分清单分批入仓**：各子系统按本仓分清单**逐项显式 `git add` + `git commit`**（禁用 `git add -A` / `git add .` 兜底；每批提交前 `git diff --cached --stat` 复查）。
2. **回填 hash**：提交后将实际 commit hash 回填至**各仓 JT 台账与任务卡卡尾**（OpenMemory v1.4.0 / OpenRAG v1.5.0 / OpenLLM v1.6.0 / DPS JT 台账与 S5 段任务卡卡尾）。
3. **四仓清单勾稽**：以总清单 §1.1 对照表为基准，逐仓回读 `git status --porcelain -uall`，确认**仅剩 B 类隔离项 + C 类噪音 + 清单文档自身**，A 类差异为 0。
4. **OpenBase 侧跨仓会签**：在 OpenBase 仓汇总四仓 hash 与总清单，形成会签记录（建议追加至总清单修订历史或任务卡卡尾），总清单状态由 [Review] → [Approved]。
5. **再回写放行清单与台账**：按总清单 §2.8 回写本清单 v1.0.2 → v1.0.3（本次已执行），并同步各仓文档状态登记（遵循文档版本管理规范）。

## 附：建议提交批次与命令数汇总

| 仓 | 建议分支 | 建议提交批次（git commit 数） | 每批约需 git 命令 |
|----|---------|-------------------------------|-------------------|
| OpenMemory | release/v7.2.0 → release/v7.3.0 | **4**（v1.0.3 修订：批 0 基线 29 / 批 1 S2 五份文档 5 / 批 2 S2 源码·迁移·脚本 21 / 批 3 S2 测试·CI 15；B 类 197 项隔离、C 类 89 项排除） | add 2~5 条 + commit 1 条 + 回归 1~3 条/批 |
| OpenLLM | feature/v2.13.0-openrag（基线批）→ feature/s4-identity-channel-b（叠加位） | **6**（基线 1 + S4 5：文档 7 / identity 包 15 / 客户端与网关 15 / scripts 8 / tests 11；scripts+tests 合批即 5；v1.0.3 修订：4 项 need-star 测试移出改归 B 类隔离） | add 1~13 条 + commit 1 条 + 回归 1~7 条/批（§2.6） |
| DPS | main | **4**（v1.0.3 修订：S5-B1 内核装配 19 / S5-B2 路由权限测试 17 / S5-B3 脚本门禁证据 8 / S5-B4 联调文档 8；原登记 1 批 = v2.9.0 三份文档，已改列 B 类隔离） | add 1~5 条 + commit 1 条 + 回归 1~3 条/批 |
| OpenRAG | release/v1.10.0（拟，自 master 959ef83 切出） | **4**（S3-B1 文档 6 / S3-B2 identity·中间件·配置 25 / S3-B3 storage·迁移·路由 12 / S3-B4 scripts·tests·CI 24；v1.0.3 修订：实测 67 项含净增 13 项；可合并为 3） | add 1~4 条 + commit 1 条 + 回归 1~5 条/批（§4.6） |
| OpenBase | main | **0**（无需放行；S2/S3/S4 台账回写由沙箱内 docs(intg) 提交承载；v1.0.3 实测 HEAD cdfbd5b、工作树 7 项 dogfood-output 噪音不提交） | 已执行 |

> **尾注**：本清单当前状态 **[Draft]**（内部版本 **v1.0.5**，2026-09-10 依据四仓只读清点核对、统一前端定案与 S5（DPS）段门禁人工批准登记回写）；**四仓入仓、hash 回填与跨仓会签完成前不予放行**（S5（DPS）段门禁已于 2026-09-10 人工批准、**可进入入仓**，见 §3.3 登记行；Pull 真实 HTTP 双签 PENDING 挂起登记不阻断）。会签通过后按文档版本管理规范升版至 [Approved] 并登记各仓文档状态（引用总清单 §4.1 会签流程第 5 步）。
