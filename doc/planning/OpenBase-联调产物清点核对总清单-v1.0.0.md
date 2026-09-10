# OpenBase-联调产物清点核对总清单-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-CLEARANCE-v1.0.0 |
| 版本 | v1.0.5 |
| 状态 | [Review]（**v1.0.x 修订：S6 段门禁批准（挂起口径）**——v1.0.5 追加 S6 段门禁**批准**登记小节 §5.8，仅加注不改既有计数与归类） |
| 日期 | 2026-09-10 |
| 作者 | AD（跨项目分析 / 只读盘点整合） |
| 文档主题 | 四仓（OpenMemory / OpenRAG / OpenLLM / DPS）+ OpenBase 自身联调产物清点结果的总汇总：五仓对照、与跨仓放行清单的差异与回写建议、逐仓入仓操作指引、会签核验流程与残余风险 |
| 上游依据 | ①《OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》（文档内版本 **v1.0.2**，[Draft]，文档编号 OB-INTG-CROSSREPO-RELEASE-v1.0.0，路径 `doc/development/`）；②四份子系统只读清点清单：`D:\Trae CN\myproject\Dev\OpenMemory\doc\planning\OpenMemory-联调产物待提交清单-v1.0.0.md`（OB-OM-CLEARANCE-v1.0.0）、`D:\Trae CN\myproject\Dev\OpenRAG\doc\planning\OpenRAG-联调产物待提交清单-v1.0.0.md`（OB-RG-CLEARANCE-v1.0.0）、`D:\Trae CN\myproject\Dev\OpenLLM\doc\planning\OpenLLM-联调产物待提交清单-v1.0.0.md`（OB-LL-CLEARANCE-v1.0.0）、`D:\Trae CN\myproject\Dev\DPS\doc\planning\DPS-联调产物待提交清单-v1.0.0.md`（OB-DPS-CLEARANCE-v1.0.0）；③四仓 2026-09-10 实测摘要（HEAD/分支/status 分类计数）与 OpenBase 仓 2026-09-10 实测 |
| 适用范围 | 五个 git 仓工作树的「联调产物入仓」决策面；本文档为**只读盘点总清单**，不代为执行任何提交；四子系统仓命令须由用户在沙箱外执行（沙箱内 git 仅允许操作 OpenBase 仓） |
| 说明 | 本文档为**只读盘点总清单（consolidated read-only inventory）**，汇总四仓子系统清单的结论并与跨仓放行清单 v1.0.2 交叉核对，供各子系统对话入仓与后续跨仓会签使用。编制过程**禁止 `git add` / `git commit`，禁止改动任何代码与其他文档**，仅新建本文档一个文件。分类口径统一为：**A = 联调产物**（本次联调段待提交面）／**B = 子系统自身在途开发**（须隔离）／**C = 噪音/排除项**（不提交）／**需人工判定**（归属或提交范围待人工裁定） |
| 采集口径 | 引用四仓子系统清单的只读实测口径：`git status --porcelain -uall`（全量、含未跟踪展开）＋`git rev-parse --short HEAD`／`--abbrev-ref HEAD`＋`git diff --stat`／`git diff --cached --stat`＋`git ls-files`（判定跟踪态）＋`git status --porcelain --ignored`（噪音分类佐证）。**本文档不重复清点**，仅对子系统清单的关键计数做存在性与一致性校验 |

---

## §1 清点结论总览

### 1.1 五仓对照表（2026-09-10 实测汇总）

> 「status 总条数」统一以 `git status --porcelain -uall` 全量展开口径为准；OpenLLM 因工作树含第三方解包产物，另标注其 `git status --porcelain`（目录折叠）口径，两口径**不矛盾**（仅粒度不同，见 §2.2）。

| 仓 | 版本基线 HEAD / 分支 | status 总条数 | A 联调产物 | B 自身在途（隔离） | C 噪音（排除） | 需人工判定 | 建议提交批次 | 子系统清单文件路径 |
|----|----------------------|--------------:|-----------:|------------------:|---------------:|-----------:|:---:|------|
| **OpenMemory** | `6cbfb71`（v6.9.0 发布闭环）/ `release/v6.9.0` | **364**（75 M + 289 ??，无 D/R，无暂存） | **70**（基线批 29 + S2 段批 41） | **197**（v7.0~v7.2 子系统自身在途开发） | **89** | **8** | **4**（批 0 基线 / 批 1 文档 / 批 2 源码·迁移·脚本 / 批 3 测试·CI） | `D:\Trae CN\myproject\Dev\OpenMemory\doc\planning\OpenMemory-联调产物待提交清单-v1.0.0.md` |
| **OpenRAG** | `959ef83`（v1.9.1 发布闭环）/ `master` | **67**（22 M + 45 ??）；含本文档自身为 68 | **67**（S3-B1 文档 6 / S3-B2 identity 25 / S3-B3 storage 12 / S3-B4 scripts+tests 24） | **0** | **0** | **0** | **4**（S3-B1 文档 / S3-B2 identity·中间件·配置 / S3-B3 storage·迁移·路由 / S3-B4 scripts·tests·CI） | `D:\Trae CN\myproject\Dev\OpenRAG\doc\planning\OpenRAG-联调产物待提交清单-v1.0.0.md` |
| **OpenLLM** | `a552cbf`（v2.14.3 发布闭环）/ `feature/v2.13.0-openrag` | 折叠口径 **430**（登记一致）；`-uall` 展开 **1555** = `??` 1235 + `D` 211 + `M` 109 | **75**（批 1 基线 15 / 批 2 文档 7 / 批 3 identity+中间件+配置 15 / 批 4 客户端与网关 15 / 批 5 scripts 8 / 批 6 tests 15） | **13**（need-star 统一编排 v0.4.0~v0.6.0 在途） | **1455**（= 展开 `?D` 211 + `?M` 71 + `.pylib` 未跟踪 1157 + 已跟踪元数据 4 + data/backup 等 12） | **12** | **6**（基线 1 + S4 5；批 5+批 6 合批即 5 批） | `D:\Trae CN\myproject\Dev\OpenLLM\doc\planning\OpenLLM-联调产物待提交清单-v1.0.0.md` |
| **DPS** | `6b39dd4`（S0 门禁补充）/ `main` | **57**（11 M + 46 ??） | **52**（S5-B1 内核·配置·装配 19 / S5-B2 路由·权限·审计·测试 17 / S5-B3 脚本·门禁·证据 8 / S5-B4 联调文档 8） | **3**（v2.9.0 画像/标注模板扩展在途） | **2** | **3**（⊂ A，不重复计入合计） | **4**（S5-B1 → B4；上游放行清单登记为 1 批，建议细化） | `D:\Trae CN\myproject\Dev\DPS\doc\planning\DPS-联调产物待提交清单-v1.0.0.md` |
| **OpenBase** | `cdfbd5b`（docs(intg): S4 台账回写与跨仓放行清单更新）/ `main` | **7**（全部 `??`） | **0**（本次联调 OpenBase **无联调产物待提交**） | **0** | **7**（`dogfood-output/` 走查产物，**全部未跟踪、不提交**） | **0** | **0**（无需放行） | 本文档（总清单）；OpenBase 自身无子系统清单 |

### 1.2 对照表要点

1. **联调产物（A 类）总量**：四仓合计 **264** 项（OpenMemory 70 + OpenRAG 67 + OpenLLM 75 + DPS 52），OpenBase 0 项。按批次口径合计 **18 个提交**（OpenMemory 4 + OpenRAG 4 + OpenLLM 6 + DPS 4），OpenLLM 合并 scripts+tests 后为 **17 个提交**。
2. **必须隔离的在途开发（B 类）**：OpenMemory **197**（v7.x 自建，量最大）、OpenLLM **13**（need-star 统一编排）、DPS **3**（v2.9.0 文档）；OpenRAG/OpenBase 为 0。B 类**严禁与 A 类混批**。
3. **噪音（C 类）**：OpenLLM **1455**（占其 `-uall` 全量的 93.6%，主体为 `backend/.pylib/` 第三方解包 1157 与 `.pyc` 282）、OpenMemory **89**（敏感文件 1 + 临时误落 4 + 一次性证据 57 + 运行期图像 27）、OpenBase **7**（dogfood-output）；OpenRAG/DPS 分别为 0/2。
4. **需人工裁定项合计 23 项**：OpenMemory 8 + OpenLLM 12 + DPS 3（OpenRAG/OpenBase 为 0）。其中 OpenLLM 4 项为**混合文件 hunk 拆分**（`git add -p` 人工裁定），1 项为分类冲突（4 个 need-star 测试文件），7 项为清单外待裁定项。
5. **OpenBase 自身如实说明**：本仓本次联调**无任何联调产物**待提交，`git status --porcelain` 的 7 条全部为 `dogfood-output/` 走查产物（`evidence/*.json` 5 个 + `report.md` + `screenshots/`），**全部未跟踪、明确不提交**，与放行清单 v1.0.2 §5「`dogfood-output/` 不属放行范围」口径一致。

### 1.3 子系统清单文件存在性与关键计数校验（本次读取核验）

| 子系统清单文件 | 存在性 | 行数 | 字节数 | 关键计数（文中自述） | 与四仓实测摘要一致性 |
|---------------|:---:|----:|------:|------|------|
| `OpenMemory-联调产物待提交清单-v1.0.0.md` | **存在** | 578 | 53,250 | status 364 = A 70 + B 197 + C 89 + 人工 8 | **一致**（A 70 = 基线 29 + 段批 41） |
| `OpenRAG-联调产物待提交清单-v1.0.0.md` | **存在** | 361 | 41,967 | status 67 = A 67 + B 0 + C 0 + 人工 0 | **一致**（A 67 = B1 6 + B2 25 + B3 12 + B4 24） |
| `OpenLLM-联调产物待提交清单-v1.0.0.md` | **存在** | 408 | 40,958 | `-uall` 1555 = A 75 + B 13 + C 1455 + 人工 12 | **一致**（A 75 = 15+7+15+15+8+15） |
| `DPS-联调产物待提交清单-v1.0.0.md` | **存在** | 310 | 22,383 | status 57 = A 52 + B 3 + C 2（人工 3 ⊂ A） | **一致**（A 52 = 19+17+8+8） |

> 校验结论：四份子系统清单**均存在**，行数分别为 578 / 361 / 408 / 310；各自 A+B+C+（人工判定）合计恒等于其 `git status --porcelain -uall` 全量条数（差异 0），与本次四仓实测摘要**逐一吻合**，无冲突、无缺件。总清单**不重复清点**，直接引用上述结论。

### 1.4 统一前端口径与清点影响（**v1.0.x 修订：统一前端定案**）

项目负责人 2026-09-10 定案：**只维护统一前端 = `D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`**（Git 仓在 OpenBase 项目目录下、**已入库跟踪**；`git ls-files openbase-ui` 实测 **107** 个文件）；各子系统自带 `frontend/`（DPS / OpenLLM / OpenMemory / OpenRAG）**暂时冻结、不再维护**。对本次清点的直接影响：

1. **各子系统 `frontend/` 改动一律不属联调提交面**——即不进入任何 A 类批次，按现状归 **B/C 类**（隔离/排除），不得纳入 `docs(sN)` / `feat(sN)` / `test(sN)` 联调提交。逐仓核对：
   - **OpenMemory**：在途 8 项 `frontend/**`（4 `M` + 4 `??`），分清单已归 **B 类**（§3.2 已修改 4 项 + §3.3(l) 前端新增 4 项）——归类正确，**不属 A 类联调产物**；
   - **DPS**：`frontend/` 63 个已跟踪源文件，分清单 §4.4 **C-11** 登记为历史卫生债（「无需动作」，非 A 类）；
   - **OpenLLM / OpenRAG**：`frontend/` 未出现在各自分清单 A/B/C/需人工判定任一张表（`git status` 无 `frontend` 条目）。
2. **openbase-ui 属 OpenBase 仓维护面**：其改动仅在 OpenBase 仓 `openbase-ui/` 内维护与提交；本次清点实测 OpenBase 工作树**无 `openbase-ui` 未提交改动**（`git status` 7 项全部为 `dogfood-output/` 噪音），故**不增加任何提交面**，OpenBase A 类仍为 **0**。
3. **计数口径不变**：各仓 A + B + C +（需人工判定）恒等于其 `git status --porcelain -uall` 全量条数（差异 0）的前提**不变**；本节仅新增统一前端口径说明，**不改变任何既有计数与归类**。

---

## §2 与放行清单 v1.0.2 的差异与回写建议

> 上游放行清单（`doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`，文档内版本 **v1.0.2**，[Draft]）登记时点为 2026-09-09（OpenLLM 段为 2026-09-10 补），四仓清点为 2026-09-10。以下为两口径的**全部差异条目（共 7 条）**。**本次不修改放行清单**，仅给出 v1.0.2 → v1.0.3 的回写建议条目（见 §2.8）。

### 2.1 差异-1｜OpenRAG：实测净增 13 项（S3 批次 3 产物）

放行清单 v1.0.2 §4.1 登记 OpenRAG 为 **22 M + 32 ?? = 54 项**（2026-09-09 实测）；2026-09-10 实测为 **22 M + 45 ?? = 67 项**，**净增 13 项未跟踪文件**，全部为 S3 **批次 3（S3-T8~T11）** 产物，与 S3 DevLogReport「改动清单（批次 3）」逐项对齐，**无清单外新增**。文件名清单摘要：

| 序号 | 新增文件（相对上游 54 项） | 归属 |
|:---:|------|------|
| 1 | `OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md` | S3 立项（文档） |
| 2 | `OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md` | S3 设计（文档） |
| 3 | `doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md` | S3-T8 / K07 |
| 4 | `doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json` | S3-T8 / K07 |
| 5 | `doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md` | S3 开发记录 |
| 6 | `doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md` | S3 测试报告 |
| 7 | `scripts/k07_endpoint_matrix.py` | S3-T8 |
| 8 | `scripts/smoke_l3_2.py` | S3-T11 |
| 9 | `scripts/tenant_backfill_report.py` | S3-T2 |
| 10 | `scripts/verify_env_contract.py` | S3-T10 |
| 11 | `scripts/verify-env/contract.json` | S3-T10 |
| 12 | `tests/unit/test_isolation_matrix_endpoints.py` | S3-T8 / K07 |
| 13 | `tests/unit/test_s3_t11_l3_2_smoke.py` | S3-T11 |

> 回写影响：放行清单 §4.3 的四批 add 集合须增补上述 13 项（其中第 3/4 项归批 1，第 7~11 项归批 4，第 12/13 项归批 4，第 1/2/5/6 项归批 1）；§4.1「第 0 步核对命令」中的 `(git status --porcelain).Count` 期望值由 **54 改为 67**（若 `-uall` 亦为 67，因本仓无折叠差分）。

### 2.2 差异-2｜OpenLLM：清点口径修正（折叠 430 与登记一致；`-uall` 展开 1555）

放行清单 v1.0.2 §2.1 登记 OpenLLM 工作树「**约 430 项**」（目录折叠近似口径）。子系统清单实测确认：

- **折叠口径** `git status --porcelain` = **430**（与放行清单登记**一致**）。
- **展开口径** `git status --porcelain -uall` = **1555** = `??` **1235** + `?D` **211** + `?M` **109**。
- 差额来源：`backend/.pylib/` 第三方库解包产物 **1157 项**（未跟踪、须展开）+ `backend/data/*` 5 项 + `backup/` 6 项被 `-uall` 展开。
- 噪音归属复核（均属 C 类，**不提交**）：`.pyc` 合计 282（= 删除 211 + 修改 71，全部为 `__pycache__` 字节码，属**历史误入库**）；`backend/.pylib` 未跟踪 1157；已跟踪元数据修改 4；`backend/data` 与 `backup` 等其余项。

> 回写影响：放行清单 §2.1 工作树行建议补注「折叠 430 ≈ `-uall` 1555，差额主体为 `backend/.pylib/` 第三方解包 1157，属噪音不提交」，避免下轮清点误判为「新增遗漏」。**两口径不矛盾**。

### 2.3 差异-3｜OpenLLM：4 个 need-star 测试文件分类冲突（须纠正）

放行清单 v1.0.2 §2.3 批 6 与《OpenLLM-S4-批次1基线收口登记清单》将以下 **4 个文件误登记为 A 类基线/批 1**，实为 **need-star 统一编排 v0.4.0~v0.6.0 在途产物**，应归 **B 类隔离**：

| 文件 | 上游误登记 | 正确归属 | 依据 |
|------|-----------|---------|------|
| `backend/tests/unit/test_profile_component_phase1.py` | 批 1（A 类） | **B 类**（need-star 读侧 Phase 1，R1~R8） | 内容为 profile 组件化编排用例 |
| `backend/tests/unit/test_writeback_w1_phase1.py` | 批 1（A 类） | **B 类**（need-star W1-1~W1-6） | 写侧幂等在途 |
| `backend/tests/unit/test_writeback_w2_phase1.py` | 批 1（A 类） | **B 类**（need-star v0.5.0 W2-1/W2-2） | 质量化在途 |
| `backend/tests/unit/test_writeback_w3_phase1.py` | 批 1（A 类） | **B 类**（need-star v0.6.0 W3-1） | 流式会话级在途 |

> 回写影响：放行清单 §2.4「提交 1 — 基线批次」的 `git add` 模板中须**移除**这 4 个文件（否则将 need-star 在途开发混入 S4 基线批）；§2.3 批 6 亦不得收录。need-star 建议**独立分支（如 `feature/need-star-orchestration`）+ 独立批次 + 独立 commit**，提交信息显式标注 `need-star` 而非 `s4`。

### 2.4 差异-4｜DPS：实测 57 ≠ 上游预估 47

上游任务口径预估为「约 47 项」，2026-09-10 实测 `git status --porcelain -uall` = **57**（11 M + 46 ??），**差 10 项**。实测归类：A **52** + B **3** + C **2** = 57（需人工判定 3 ⊂ A，不重复计数）。其中：

- 上游放行清单 §3.1 仅登记 **3 ?? 文档**（v2.9.0 三份），实为 **B 类隔离项**，**不属 S5 联调**——B 类 3 项与上游「DPS 放行 = 3 份 v2.9.0 文档」的表述**语义不同**，须澄清：S5 联调产物 52 项**均未被上游放行清单登记**（因 OpenRAG/OpenLLM/OpenMemory 段先行，DPS S5 段当时尚未收口）。
- C 类 2 项为 `.ruff_cache/CACHEDIR.TAG` 与 `src/dps.db-journal`，须从任何提交中排除。

> 回写影响：放行清单 §3（DPS 仓）须**整体改写**——由「3 份 v2.9.0 文档、1 批」改为「S5 联调产物 52 项、**4 批（S5-B1~B4）**；v2.9.0 三份文档属 B 类隔离、另起独立批」；附「建议提交批次与命令数汇总」表 DPS 行由 **1 改为 4**。

### 2.5 差异-5｜OpenMemory：实测 364 且 197 项 v7.x 在途须隔离

放行清单 v1.0.2 §1.1 登记「69 M + 207 ?? = 276」（2026-09-09 实测 75 M + 235 ??）。2026-09-10 实测 **364**（75 M + 289 ??），较 2026-09-09 增 54 项未跟踪。

- **已跟踪 M 集合与放行清单无差异**（均 75），增量全部为未跟踪新文件。
- 增量主体为 **B 类 v7.x 在途开发 197 项**（子系统自身功能/SDK/e2e/运维/模块文档等）与 **C 类运行期产物**。
- 关键风险：放行清单 §1.4「提交 1 — v7.2 基线」采用 `git add -A` + 逐项 `git reset` 的模板，在 197 项 B 类未跟踪文件存在时**极易误纳**。子系统清单已把「非联调 v7.x 自建内容」**单列为 B 并隔离**，并明确「严禁使用 `git add -A` 兜底」。

> 回写影响：放行清单 §1.4 提交 1 的 `git add -A` 模板须**改为按 A 类 29 项显式路径 `git add`**（见子系统清单 §6.2 批 0 模板）；§1.1 期望值由 276 更新为 **364**；并补登记 B 类 197 项隔离说明与 C 类 89 项排除说明。

### 2.6 差异-6｜OpenBase：HEAD 漂移与状态登记口径差异

放行清单 v1.0.2 §5 登记 OpenBase「当前分支 `main`、HEAD `0713ec1`」。2026-09-10 实测：

| 项目 | 放行清单 v1.0.2 登记 | 2026-09-10 实测 | 说明 |
|------|--------------------|----------------|------|
| 分支 | `main` | `main` | 一致 |
| HEAD | `0713ec1` | **`cdfbd5b`**（`docs(intg): S4 台账回写与跨仓放行清单更新`） | **漂移**：`0713ec1` 为事件契约端点冻结提交，其后已有 `1a6f3d4`（S2 回写）、`a5dcd2b`（S3 回写）、`cdfbd5b`（S4 回写）三次 docs(intg) 提交 |
| 工作树 | 未登记 | 7 项 `dogfood-output/` 走查产物（全部 `??`、不提交） | 须补登记 |

> 回写影响：放行清单 §5 表 HEAD 由 `0713ec1` 更新为 `cdfbd5b`（或表述为「`0713ec1` 契约冻结 → 后续 docs(intg) 回写链，当前 HEAD `cdfbd5b`」），并补登 `dogfood-output/` 7 项不提交说明。**此为唯一涉及 OpenBase 自身的差异，不影响四仓放行结论。**

### 2.7 差异-7｜批次口径细化（DPS 1 → 4；其余三仓与登记一致）

| 仓 | 放行清单 v1.0.2 建议批次 | 子系统清单建议批次 | 差异 |
|----|:---:|:---:|------|
| OpenMemory | 4 | 4（批 0 基线 / 批 1 文档 / 批 2 源码·迁移·脚本 / 批 3 测试·CI） | 一致（仅批次命名细化） |
| OpenRAG | 4 | 4（S3-B1~B4） | 一致 |
| OpenLLM | 6（可 5~7） | 6（可合并 5） | 一致 |
| DPS | **1**（3 份文档） | **4**（S5-B1~B4，A 类 52 项） | **差异**：上游按 v2.9.0 文档口径登记，实为 S5 联调 4 批 |

### 2.8 放行清单 v1.0.2 → v1.0.3 回写条目建议（本次不修改放行清单）

| 序号 | 回写位置 | 建议条目 | 依据 |
|:---:|------|------|------|
| 1 | §4.1 第 0 步核对 | `(git status --porcelain).Count` 期望值 `54` → **`67`** | §2.1 |
| 2 | §4.3 清单 | 增补 13 项 S3 批次 3 产物（文档 6 + scripts 5 + tests 2 归相应批次） | §2.1 |
| 3 | §2.1 工作树行 | 补注「折叠 430 ≈ `-uall` 1555；差额主体 `backend/.pylib/` 1157 + `.pyc` 282 + data/backup 等，均 C 类不提交」 | §2.2 |
| 4 | §2.4 提交 1 模板 | 从 `git add` 模板**移除** 4 个 need-star 测试文件；新增 need-star 独立隔离批（独立分支 + 独立 commit） | §2.3 |
| 5 | §2.3 批 6 清单 | 同步移除 4 个 need-star 测试文件；批 6 条目数 15 → **11**（仅 test_s4_t1~t15 共 15 项中剔除 4 项 need-star 后为 11，另 `test_real_contract_profile.py` S0 修订保留） | §2.3 |
| 6 | §3 全章（DPS） | 改写为 S5 联调 52 项、4 批（S5-B1~B4）；v2.9.0 三份文档改列 B 类隔离独立批 | §2.4、§2.7 |
| 7 | §1.1 / §1.4 | 期望值 276 → **364**；提交 1 模板由 `git add -A` 改为 A 类 29 项显式路径；补 B 类 197 / C 类 89 登记 | §2.5 |
| 8 | §5（OpenBase） | HEAD `0713ec1` → **`cdfbd5b`**；补登 `dogfood-output/` 7 项不提交 | §2.6 |
| 9 | 附：批次汇总表 | DPS 行「1」→ **「4」**；OpenMemory/OpenRAG/OpenLLM 行批次命名对齐子系统清单 | §2.7 |
| 10 | 文档元信息/修订历史 | 版本 v1.0.2 → **v1.0.3**，修订内容登记本表 1~9 条 | 文档版本管理规范 |

---

## §3 各子系统入仓操作指引

> **统一纪律（四仓通用）**：
> 1. **只 add 预期路径**，**严禁 `git add -A` 与 `git add .` 兜底**；每批提交前先 `git diff --cached --stat` 复查暂存内容仅含预期路径。
> 2. 中文/含空格路径在 PowerShell 中一律用**单引号**包裹。
> 3. **严禁提交敏感文件**：`.env`、`.env.shared-infra`、`.env.e2e`、`data/edge_tokens.jsonl`（及 OpenLLM `backend/.env`／`backend/.env.shared-infra`、DPS `.env.shared-infra`、OpenMemory `.env.shared-infra`）——凡出现一律标注「不提交」。
> 4. 每仓提交后回归**失败即停止后续批次**；回归通过再进入下一仓。总体顺序建议：**OpenMemory → OpenRAG → OpenLLM → DPS → OpenBase 会签**。
> 5. 本次为只读盘点，**上述命令均为模板，本文档不代为执行**（沙箱仅允许操作 OpenBase 仓）。

### 3.1 OpenMemory 仓（`D:\Trae CN\myproject\Dev\OpenMemory`）

| 项目 | 内容 |
|------|------|
| 建议分支 | `release/v6.9.0`（现分支）→ 切 **`release/v7.2.0`**（基线批）→ 再切 **`release/v7.3.0`**（S2 段批） |
| 提交批次与顺序 | **批 0 基线（29 项）** → **批 1 S2 五份文档（5）** → **批 2 S2 源码/迁移/脚本（21）** → **批 3 S2 测试/CI（15）**；合计 4 提交 |
| git add 模板（批 0 摘要） | `git add '.env.example' 'scripts/run_lightweight.py' 'scripts/start_openmemory.py' 'run_api.py' 'src/openmemory/__init__.py' '.devflow/project-config.json'`；再分批 add `api/*` `auth/*` `core/models.py` `memory/session_persistent.py` `storage/*` `utils/*` 等混合文件与联调承载用例（完整 29 项见子系统清单 §6.2） |
| 提交信息模板 | 批 0：`chore(om-baseline): OpenMemory 联调前置基线（S0 探活/启动门禁 + 版本对齐 + K05/K06/RA-05 承载）`；批 1：`docs(s2): OpenMemory S2 五份文档入库（立项/设计草案/DevLogReport/测试报告/K07 矩阵填报）`；批 2：`feat(s2): S2 协议头入站/行控收口/复合唯一/存量回填/事件消费端/矩阵校验 源码与迁移（T1~T13，alembic v702~v704）`；批 3：`test(s2): S2 T1~T13 RED 断言与段门禁自检用例 + CI s2-k07-matrix-gate job` |
| 提交前排除清单 | **B 类 197 项**（v7.0~v7.2 子系统自身在途开发，隔离）；**C 类 89 项**（`.env.shared-infra` 敏感 1、`doc/test/_temp_test.txt`/`get-pip.py`/`json`/`markdown` 临时误落 4、一次性证据 57、`storage/images/**` 运行期图像 27）；**8 项需人工判定**（`.devflow/state.json`、`scripts/extract_backend_routes.py`、`api/middleware/degradation.py`、`npm-fix.js`、`npm-wrapper.js`、`test_authz_trust_cr008.py`、`test_degradation_v71.py`、`test_server_middleware_cr009_012.py`） |
| 提交后回归命令 | `python -m pytest tests/unit tests/integration -q -p no:cacheprovider`（期望 1330 passed, 36 skipped）；`python -m ruff check src scripts`（0 错误）；`python scripts/k07_endpoint_matrix.py --verify --matrix 'doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md' --openapi scripts/api_baseline.json`（退出码 0）；`python scripts/smoke_l3_2.py` |
| hash 回填位 | 《OpenBase-数据隔离实现任务卡》**v1.4.0 卡尾 S2 段执行摘要**（4 个 commit hash） |
| 专项叮嘱 | ① 建议补 `.gitignore` 规则 **`.env.*`**（保留 `!.env.example`）与 **`.devflow/state.json`**；② `.env.shared-infra` 若确含凭据，须先核查是否曾进入历史（`git log --all -- .env.shared-infra`）；③ 混合文件（`controllers.py`/`utils/config.py`/`utils/exceptions.py`/`structured_log.py`/`error_handler.py`/`session_persistent.py`）随基线批，S2 增量随之落库；严格拆分须 `git add -p`（人工） |

### 3.2 OpenRAG 仓（`D:\Trae CN\myproject\Dev\OpenRAG`）

| 项目 | 内容 |
|------|------|
| 建议分支 | 自 `master`（`959ef83`）切 **`release/v1.10.0`**（拟） |
| 提交批次与顺序 | **S3-B1 文档（6）** → **S3-B2 identity/中间件/配置（25）** → **S3-B3 storage/迁移/路由（12）** → **S3-B4 scripts/tests/CI（24）**；合计 4 提交（可合并 3） |
| git add 模板（示例） | B1：`git add 'OpenRAG-S3-数据隔离与身份接入收口立项方案-v1.0.0.md' 'OpenRAG-S3-数据隔离与身份接入收口设计草案-v1.0.0.md' 'doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md' 'doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json' 'doc/development/OpenRAG-S3-数据隔离与身份接入收口-DevLogReport-v1.0.0.md' 'doc/test/OpenRAG-S3-数据隔离与身份接入收口-测试报告-v1.0.0.md'`；B2：`git add 'src/openrag/identity' 'src/openrag/api/middleware/identity_gate.py' ...`（完整见子系统清单 §2.4~§2.6） |
| 提交信息模板 | B1：`docs(s3): OpenRAG S3 六份文档入库（立项 v1.1.0/设计草案 v1.0.1 [Approved]；DevLog v1.0.1 [Approved]/测试报告 v1.0.0/K07 填报 v1.0.0）`；B2：`feat(s3): 身份接入收口 identity/中间件/配置`；B3：`feat(s3): 数据隔离 storage/迁移/路由`；B4：`test(s3): S3 T1~T11 RED 断言/K07 矩阵隔离用例/四静态扫描与 L3-2 冒烟脚本 + CI s3-static-gates job` |
| 提交前排除清单 | B/C 类均为 **0**；**严禁 `git add repository`**（该路径为 gitlink 子仓 `160000 0ed102a…`，任何批次不得 add）；`.env`/`.env.e2e`/`.env.shared-infra` **严禁提交**；`__pycache__/*.pyc`（764 个）、日志 `*.log`（9）等被忽略项不计入 67、不得提交 |
| 提交后回归命令 | `python -B -m pytest tests/unit -p no:cacheprovider`（S3 组 144 用例恒绿；既有 3 项枚举大小写登记项除外）；`python -m ruff check src scripts tests/unit`；四静态扫描 `scan_no_edgerouter_assembly.py`/`scan_no_identity_header_bypass.py`/`scan_tenant_scope.py`/`scan_auto_purge.py`（逐条退出码 0）；`python scripts/k07_endpoint_matrix.py`；`python scripts/smoke_l3_2.py` |
| hash 回填位 | 《OpenBase-数据隔离实现任务卡》**v1.5.0 卡尾 S3 段执行摘要**（4 个 commit hash） |
| 专项叮嘱 | ① `repository` 子仓（gitlink）**禁止 add**；② `.env.example` 与 `version.json` 口径待人工裁定（见 §5.3）；③ 6 项「建议人工复核」项（`api/responses.py`、`api/exception_handlers.py`、`ci-cd.yml`、`run_tests.py`、`router/middleware.py`、`api/routes/documents.py` 既有回归）入仓前复核 diff；④ 文档名版本 ≠ 文档内版本（4~5 份），按现文件名登记，改名须同步升版 |

### 3.3 OpenLLM 仓（`D:\Trae CN\myproject\Dev\OpenLLM`）

| 项目 | 内容 |
|------|------|
| 建议分支 | 基线批留在 **`feature/v2.13.0-openrag`**；S4 批次切 **`feature/s4-identity-channel-b`**（当前仓内**尚不存在**该本地分支，需新建；亦可留在现分支叠加） |
| 提交批次与顺序 | **批 1 基线（15）** → **批 2 S4 文档（7）** → **批 3 identity 包/中间件/配置（15）** → **批 4 客户端与网关/装配（15）** → **批 5 scripts（8）** → **批 6 tests（11）**；合计 6 提交（批 5+6 合批即 5） |
| git add 模板（批 1 示例） | `git add 'version.json' 'backend/app/__init__.py' 'doc/release/DevFlow-Release-Note-v2.14.3.md'`；`git add 'backend/app/services/external_identity.py' 'backend/app/edgerouter/orchestration/evaluate.py'`；`git add 'backend/tests/unit/test_dps_probe_real_health.py' 'backend/tests/unit/test_external_identity.py' 'backend/tests/unit/test_real_contract_profile.py' 'backend/tests/unit/test_real_contract_memory.py' 'backend/tests/unit/test_real_contract_rag.py' 'backend/tests/unit/test_v213_writeback_queue.py' 'backend/tests/unit/test_v213_profile.py' 'backend/tests/unit/test_v213_rag_mcp.py' 'backend/tests/e2e/e2e_v213_integration.py' 'backend/tests/e2e/e2e_v213_security.py'`。**注意：不得 add 4 个 need-star 测试文件** |
| 提交信息模板 | 批 1：`chore: OpenLLM 基线收口（S0 探活 + 版本对齐 v2.14.3，按 S4-批次1基线收口登记清单 A~B）`；批 2：`docs(s4): OpenLLM S4 文档入库（立项/草案/DevLog/测试报告/JT 台账/K07 填报/基线登记清单）`；批 3：`feat(s4): 身份接入收口 identity 包/中间件/配置`；批 4：`feat(s4): 编排出站透传与网关装配`；批 5：`chore(s4): S4 静态扫描/K07/verify-env/L3-2 脚本`；批 6：`test(s4): S4 T1~T15 RED 断言与段门禁自检用例 + test_real_contract_profile S0 修订` |
| 提交前排除清单 | **B 类 13 项**（need-star 统一编排：`orchestration/auto.py`/`executor.py`/`explicit.py`、`services/writeback_queue.py`/`profile_drift.py`/`profile_refine.py`、4 个 need-star 测试 + `test_stream_profile_routing.py` + `test_coverage_boost_v2112.py` + `test_v2142_memory_writeback.py`）；**C 类 1455 项**（`.pyc` 删除 211 + `.pyc` 修改 71 + `backend/.pylib` 1157 + 已跟踪元数据 4 + data/backup 等）；**严禁提交 `backend/.env` / `backend/.env.shared-infra` / `data/edge_tokens.jsonl`** |
| 提交后回归命令 | `python -B -m pytest tests/unit -p no:cacheprovider`（306 passed 口径）；`python -m ruff check app scripts tests/unit`；`python scripts/scan_real_fallback_business_usage.py`（0 命中）；`python scripts/scan_identity_bypass.py`（0 绕过）；`python scripts/k07_endpoint_matrix.py --verify`（退出码 0）；`python scripts/verify-env/verify_env.py --fail-fast`；`python scripts/smoke_l3_2.py` |
| hash 回填位 | 《OpenBase-数据隔离实现任务卡》**v1.6.0 卡尾 S4 段执行摘要**（6 个 commit hash） |
| 专项叮嘱 | ① **已入库 `.pyc` 用 `git rm -r --cached` 处置且不要恢复**（属历史误入库卫生债，211 D + 71 M 走独立「噪音清理批次」，不与 S4 混提）；② `.pylib` 建议补 `.gitignore`；③ 4 项混合文件（`api/openllm_gateway.py`、`api/writeback.py`、`core/config.py`、`main.py`）须 `git add -p` 人工拆分（见 §5.1）；④ `backend/tests/unit/test_debug_gateway_ollama.py`（含本机绝对路径）建议排除出库；⑤ `version.json`/`backend/app/__init__.py` 版本对齐 v2.14.3 属批 1 |

### 3.4 DPS 仓（`D:\Trae CN\myproject\Dev\DPS`）

| 项目 | 内容 |
|------|------|
| 建议分支 | 留在 **`main`**（HEAD `6b39dd4`） |
| 提交批次与顺序 | **S5-B1 身份内核/配置/装配（19）** → **S5-B2 路由/权限/审计/测试（17）** → **S5-B3 脚本/门禁/证据（8）** → **S5-B4 联调文档（8）**；合计 4 提交。B3 的 `ci.yml` 门禁依赖 `scripts/k07_endpoint_matrix.py`，须与之**同批或后于**脚本提交 |
| git add 模板（B1 示例） | `Set-Location 'D:\Trae CN\myproject\Dev\DPS'`；`git add 'src/identity' 'src/middleware/identity_gate_middleware.py' 'src/middleware/block_subject_gate_middleware.py' 'src/engines/identity_event_engine.py'`；`git add 'src/config.py' 'src/database.py' 'src/main.py' 'src/rest_api/app.py' 'src/rest_api/error_handlers.py'`（完整见子系统清单 §2） |
| 提交信息模板 | B1：`feat(s5): 身份内核/配置/装配（S5-T1 门禁、T3/T4 write guard、T6 事件双通道、T8 审计、T9 角色映射）`；B2：`feat(s5): 路由/权限/审计与 S5 T1~T12 用例`；B3：`chore(s5): K07 门禁脚本/对账报告/verify-env 契约/门禁自检证据`；B4：`docs(s5): DPS S5 立项/设计/K07 填报/裁定映射/建模评审/DevLog/测试报告入库` |
| 提交前排除清单 | **B 类 3 项**（v2.9.0 三份文档：`DPS-画像模板与标注模板扩展设计文档-v2.9.0.md`、`DPS-设计评审记录-v2.9.0.md`、`DPS-功能需求清单-v2.9.0.md`）；**C 类 2 项**（`.ruff_cache/CACHEDIR.TAG`、`src/dps.db-journal`）；**严禁提交 `data/dps.db` / `.env` / `.env.shared-infra` 等** |
| 提交后回归命令 | `python -m pytest tests -q`（以仓内 pytest 配置为准）；K07 门禁 `python scripts/k07_endpoint_matrix.py --check`；可选 `python scripts/smoke_l3_2.py --quick` |
| hash 回填位 | DPS **JT 台账**与**任务卡卡尾**（S5 段执行摘要，4 个 commit hash） |
| 专项叮嘱 | ① 3 项需人工裁定（`src/engines/permission_engine.py`、`src/tests/test_portrait_update_route.py`、`doc/testing/evidence/s5_gate_self_check.json`）已计入 A 类 52，**提交范围须人工确认**（见 §5.2）；② `s5_gate_self_check.json` 含 `"pending": true`（Q-DPS-5 Pull 真实 HTTP 挂起），推荐随 B3 入库并在提交信息标注 `evidence(pending: Q-DPS-5)`；③ v2.9.0 三份文档须**独立分支/独立批次**（`docs(v2.9.0): ...`），提交信息显式区分版本域 |

### 3.5 OpenBase 仓（`D:\Trae CN\myproject\Dev\OpenBase`）

| 项目 | 内容 |
|------|------|
| 建议分支 | `main`（HEAD `cdfbd5b`） |
| 建议批次 | **0**（本次联调 OpenBase 无联调产物待提交） |
| 提交前排除清单 | `dogfood-output/` **7 项全部不提交**：`dogfood-output/evidence/after-login.json`、`evidence/e2e_full.json`、`evidence/gateway_probe.json`、`evidence/portrait_retry.json`、`evidence/recon.json`、`dogfood-output/report.md`、`dogfood-output/screenshots/` |
| 提交后回归命令 | `python -m pytest tests` + `python -m ruff check openbase tests`（以 AGENTS.md 为准） |
| hash 回填位 | 无（OpenBase 侧无联调产物提交；如需登记会签结论，追加至任务卡卡尾或本文档 §4） |
| 专项叮嘱 | 本文档（总清单）为 OpenBase 侧新增计划文档；是否随仓提交由人工批准后决定（状态 [Review]，遵循文档版本管理规范） |

### 3.6 提交后 hash 回填位汇总

| 仓 | 回填载体 | 回填内容 |
|----|---------|---------|
| OpenMemory | 《OpenBase-数据隔离实现任务卡》**v1.4.0 卡尾（S2 段执行摘要）** | 4 个 commit hash + 批次结论 |
| OpenRAG | 《OpenBase-数据隔离实现任务卡》**v1.5.0 卡尾（S3 段执行摘要）** | 4 个 commit hash + 批次结论 |
| OpenLLM | 《OpenBase-数据隔离实现任务卡》**v1.6.0 卡尾（S4 段执行摘要）** | 6 个 commit hash（或 5 个合批）+ 批次结论 |
| DPS | DPS **JT 台账** + 任务卡卡尾（S5 段） | 4 个 commit hash + 批次结论 |
| OpenBase | 本文档 §4 或任务卡卡尾 | 会签结论（无联调产物 hash） |

---

## §4 会签与核验流程

### 4.1 会签流程（五步）

1. **各子系统入仓**：按 §3.1~§3.4 逐仓切分支、分批 `git add` + `git commit`（禁止 `git add -A`/`git add .`），每批提交前 `git diff --cached --stat` 复查。
2. **各子系统回填 hash**：提交后将实际 commit hash 回填至各自 JT 台账（OpenMemory / OpenRAG / OpenLLM / DPS 的 JT 台账）与《OpenBase-数据隔离实现任务卡》对应版本卡尾（v1.4.0 / v1.5.0 / v1.6.0 / DPS S5 卡）。
3. **四仓清单勾稽**：以本总清单 §1.1 对照表为基准，逐仓回读 `git status --porcelain`，确认**仅剩 B 类隔离项 + C 类噪音 + 清单文档自身**，A 类差异为 0；四份子系统清单 §7 双向核对自检结论与实测一致。
4. **OpenBase 侧跨仓会签**：在 OpenBase 仓汇总四仓 hash 与本总清单，形成会签记录（建议追加至本文档修订历史或任务卡卡尾），状态由 [Review] → [Approved]。
5. **更新放行清单与 JT 台账**：按 §2.8 回写放行清单 v1.0.2 → v1.0.3，并同步各仓文档状态登记（遵循文档版本管理规范）。

### 4.2 逐仓核验命令（提交后应仅剩 B/C 类与清单文档本身）

```powershell
# OpenMemory —— 期望仅剩 B 类 197 + C 类 89 + 人工判定 8 + 本仓清单文档
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
git log -1 --format='%h %s'
(git status --porcelain -uall).Count          # 期望 = 364 - (A 类已提交数) + 清单文档
git status --porcelain -uall                  # 与子系统清单 §2 比对：A 类条目应归零

# OpenRAG —— 期望仅剩清单文档自身（A 类 67 全部提交后）
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
git log -1 --format='%h %s'
(git status --porcelain -uall).Count          # 期望 = 1（仅清单文档；B/C/人工均为 0）

# OpenLLM —— 期望仅剩 B 类 13 + C 类 1455 + 人工判定 12 + 清单文档
cd 'D:\Trae CN\myproject\Dev\OpenLLM'
git log -1 --format='%h %s'
(git status --porcelain).Count                # 折叠口径，与 -uall 双口径复核
git status --porcelain -uall | Select-String 'test_s4_'   # 期望无输出（A 类已提交）

# DPS —— 期望仅剩 B 类 3 + C 类 2 + 清单文档
cd 'D:\Trae CN\myproject\Dev\DPS'
git log -1 --format='%h %s'
(git status --porcelain -uall).Count          # 期望 = 5 + 清单文档

# OpenBase —— 期望仅剩 dogfood-output 7 项（不提交）
cd 'D:\Trae CN\myproject\Dev\OpenBase'
git status --porcelain                        # 期望 7 条 dogfood-output/
python -m pytest tests
python -m ruff check openbase tests
```

---

## §5 防遗漏结论与残余风险

### 5.1 仍需人工裁定：混合文件 `git add -p` 拆分（OpenLLM 4 项）

| # | 文件 | 混合内容 | 建议 |
|:---:|------|------|------|
| J-1 | `backend/app/api/openllm_gateway.py` | S4 身份解析（IDENTITY 命中 5）＋ need-star 编排增量（NEEDSTAR 命中 12），+633 行 | `git add -p` 按 hunk 拆分：S4 hunk → 批 4，need-star hunk → B 类批次；工期优先可整体并入批 4 并在 commit message 显式声明混入（不推荐） |
| J-2 | `backend/app/api/writeback.py` | S4 REAL 收口 ＋ need-star W2（`_profile_writeback`），+330 行 | 同 J-1（S4 → 批 4，need-star → B 类） |
| J-3 | `backend/app/core/config.py` | S4 配置键（IDENTITY 5）＋ need-star 开关（NEEDSTAR 7），+178 行 | 同 J-1（S4 → 批 3；need-star → B 类） |
| J-4 | `backend/main.py` | S4 中间件装配 ＋ need-star 组件/提炼接线（IDENTITY 2 / NEEDSTAR 3） | 同 J-1（S4 → 批 4） |

> 同类风险（OpenMemory）：`controllers.py`、`utils/config.py`、`utils/exceptions.py`、`api/middleware/structured_log.py`、`error_handler.py`、`memory/session_persistent.py`、`api/server.py`、`api/middleware/tenant_context.py` 等**混合文件**内同时叠有 v7.x 基线与 S2 增量，git 无法按文件拆分；默认随**批 0 基线**落库，严格拆分须 `git add -p`（人工）。

### 5.2 仍需人工裁定：status 内「需人工判定」项（合计 23 项）

| 仓 | 项数 | 明细 | 建议 |
|----|:---:|------|------|
| **OpenMemory** | 8 | `.devflow/state.json`；`scripts/extract_backend_routes.py`；`api/middleware/degradation.py`；`npm-fix.js`；`npm-wrapper.js`；`test_authz_trust_cr008.py`；`test_degradation_v71.py`；`test_server_middleware_cr009_012.py` | 逐项按子系统清单 §5 建议裁定：`degradation.py`/`test_authz_trust_cr008.py`/`test_server_middleware_cr009_012.py` 建议并入批 0；`npm-fix.js`/`npm-wrapper.js` 建议判 C 类排除；`.devflow/state.json` 建议不入库并补 `.gitignore`；其余按引用关系并批 |
| **OpenLLM** | 12 | J-1~J-4 混合文件（4）；J-5 `edgerouter/schemas/router.py`（清单外，判 A 类批 1 或批 4）；J-6 `test_billing_v2_api.py`（判 B 类，不得混入批 4/6）；J-7 `test_debug_gateway_ollama.py`（含本机绝对路径，建议排除出库）；J-8 `backend/app/mcp/__init__.py`（判 A 类批 1）；J-9 `doc/planning/OpenLLM-OpenRAG接入迭代规划-v1.0.0.md`（B 类或批 1，需负责人裁定）；J-10 `doc/design/OpenLLM-DPS实例Pro化部署架构演进设计文档-v1.1.0.md`（B 类或批 1）；J-11 同 J-10 归档旧版；J-12 `OpenLLM_完整方案文档.html`（随 J-9 同批） | J-1~J-4 须 `git add -p`；J-6/J-7 严禁混入联调批；J-5/J-8 建议并入批 1 |
| **DPS** | 3 | `src/engines/permission_engine.py`（判 S5-T3 → B2，须确认无 v2.9.0 混入）；`src/tests/test_portrait_update_route.py`（判 S5-T4/K14 → B2，与 `routes_profiles.py` 同批）；`doc/testing/evidence/s5_gate_self_check.json`（含 `pending: true`，推荐随 B3 入库并标注） | 3 项均已计入 A 类 52，提交范围须人工确认，不可全自动放行 |
| **OpenRAG** | 0 | status 内无归属未明项 | — |
| **OpenBase** | 0 | 仅 `dogfood-output/` 7 项，全部不提交 | — |
| **合计** | **23** | — | — |

### 5.3 仍需人工裁定：清单外/边界确认项

| # | 事项 | 现状 | 建议 |
|:---:|------|------|------|
| 1 | **OpenRAG `version.json` 版本对齐** | 已跟踪、内容 `version=1.7.0`（`devflowVersion=2.10.0`），本次 status **无改动**；S3 承载版本为 v1.10.0（拟，Q-RG-1），上游未对 OpenRAG 设「版本欠档对齐」批 | 当前**不作为提交项**；若需对齐，另立一次独立小批提交，不计入 S3 四批 |
| 2 | **OpenRAG `.env.example` 键未回写** | `.env.example` 已跟踪、status 无改动；S3 env 键实际落在 `src/openrag/config/settings.py`（`OPENRAG_IDENTITY_*`、`OPENRAG_IDENTITY_EVENT_*`、`OPENRAG_ROW_SCOPE_*`） | 确认是否补写示例键；若补，随 S3-B2 独立 hunk 或单独小批提交；**不得写入真实密钥** |
| 3 | **OpenRAG `repository` gitlink 子仓** | `git ls-files -s repository` → `160000 0ed102a…` | 任何批次**不得 `git add repository`**；如需提交须在内嵌仓自身会话内独立作业 |
| 4 | **OpenMemory `.env.example` 配置键补齐** | 仅新增空密钥门禁两键；S2 所需 `trusted_proxy_sources` / `strip_inbound_identity_headers` / `enforce_inbound_identity_headers` **未出现**在增量中 | 人工确认是否补示例键；若补，并入批 0 的 `.env.example` |
| 5 | **OpenMemory 敏感文件历史核查** | `.env.shared-infra` 出现在工作树（C 类） | 除不提交外，建议 `git log --all -- .env.shared-infra` 核查历史泄露，必要时按安全流程处置；并补 `.gitignore` 规则 `.env.*` 与 `.devflow/state.json` |
| 6 | **DPS 已入库历史卫生债** | 仓根 `1.0.0`（pip 输出）、`新建位图图像.bmp` 已被跟踪；`.gitignore` 含无效绝对路径规则 | 另起卫生提交 `git rm --cached` + 修正忽略规则（**不在本次执行**） |
| 7 | **OpenLLM `.pyc` 卫生债** | `.pyc` 已入库且被删除/修改（211 D + 71 M） | 独立「噪音清理批次」：`git rm -r --cached` 处置 211 删除项 + `.gitignore` 增补；**不要恢复**已删 `.pyc`；不与 S4 混提 |

### 5.4 防遗漏结论

1. **四份子系统清单均存在且计数自洽**（§1.3）：A+B+C+（人工判定）恒等于 `status -uall` 全量条数，双向核对差异 0；总清单结论可直接引用，无需重复清点。
2. **A 类 264 项已全覆盖**：四仓联调产物逐文件登记至子系统清单 §2，无「仅汇总未列文件」的遗漏面。
3. **敏感文件零进入提交面**：四仓清单均明确 `.env` / `.env.shared-infra` / `.env.e2e` / `data/edge_tokens.jsonl` 等**不在任何批次**（OpenLLM 另测 `data/edge_tokens.jsonl` 属 C 类敏感噪音）。
4. **B 类隔离边界清晰**：OpenMemory 197 / OpenLLM 13 / DPS 3，均给出隔离批建议；OpenLLM 4 项分类冲突已显式标注须回写上游。
5. **残余风险集中在「人工裁定」与「提交卫生」两处**：23 项 status 内需人工判定 + 7 项边界确认；以及四仓各自的 `.gitignore`/历史卫生债（属可选清理批，不影响本次放行）。

### 5.5 S5（DPS）段门禁批准登记（v1.0.2 新增，2026-09-10）

> 登记口径：**S5（DPS）段门禁已批准**（2026-09-10 人工批准），DPS 仓据此**可进入入仓**（S5-B1~B4 四批，逐文件依据见 DPS 分清单）。

| 项 | 登记内容 |
|----|---------|
| 段 | **S5 = DPS 收口段（DPS-JT 收官）** |
| 门禁结论 | **S5（DPS）段门禁已批准**（2026-09-10 人工批准；评审人=项目负责人经 AI 开发会话人工确认） |
| 批准口径 | `2026-09-10 S5 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认、段门禁自检五项全绿（Pull 真实 HTTP 双签 PENDING 挂起登记不阻断）、遗留=无阻断项` |
| 门禁五项（全绿） | ① 画像隔离用例全绿 ② 协议头入站校验生效（enforce）③ 级联阻断生效 ④ person 复合唯一（存量回填 0 孤儿）⑤ L3-2 贯通冒烟通过；证据 `doc/testing/evidence/s5_gate_self_check.json`（`passed=true`、`pending=true`=Pull 双签挂起位） |
| **DPS 四项文档新版本号** | **v1.0.1**——设计草案（DPS-S5-…-设计草案）、DevLogReport（DPS-S5-…-DevLogReport）、测试报告（DPS-S5-…-测试报告）、K07 端点-过滤矩阵填报（DPS-K07-端点过滤矩阵填报）；四项均为「文件名版本不变 + 内部版本随段门禁批准回写 v1.0.0 → v1.0.1」，按现文件名登记入仓 |
| 入仓执行依据 | 《DPS-联调产物待提交清单-v1.0.0》（OB-DPS-CLEARANCE-v1.0.0，`D:\Trae CN\myproject\Dev\DPS\doc\planning\DPS-联调产物待提交清单-v1.0.0.md`）§2 逐文件表与 §6.1 分批 `git add` 模板；跨仓放行清单 §3.3 已同步登记「S5 段门禁已于 2026-09-10 人工批准、可进入入仓」（放行清单内部版本 **v1.0.5**） |
| 本仓 DPS 清点口径（不变） | status `-uall` **57** = A 联调 **52**（S5-B1 19 / B2 17 / B3 8 / B4 8）+ B 类在途 **3**（v2.9.0 文档，隔离）+ C 类噪音 **2**；需人工判定 3（⊂ A）；基线 HEAD `6b39dd4` / `main` |
| 遗留（非阻断） | ① Pull 真实 HTTP 双签 PENDING（Q-DPS-5，配置 `IDENTITY_EVENTS_BASE_URL` 指向 OpenBase commit 0713ec1 事件端点后补跑）；② 非沙箱复核清单（真实 PG/Redis 复核等）；③ DPS 仓 S5 提交 hash 待沙箱外放行后回填 DPS-JT 台账与任务卡卡尾（v1.7.0 S5 段执行摘要） |

> 影响面：本条为**段门禁批准状态登记**，不改变 §1.1 五仓对照表任何计数与 A/B/C 归类（DPS A 类仍为 52、B 类 3、C 类 2）；DPS 仓 S5 四批入仓后按 §4.1 会签流程回填 hash 并使 A 类差异归零。

### 5.6 S6-T1 统一前端冻结口径闭环登记（v1.0.3 新增，2026-09-10）

> 加注口径：本次仅**追加一行 S6-T1 口径闭环与物理闭环 PENDING 移交注记**，**不改变 §1.1 五仓对照表任何既有计数与 A/B/C 归类，也不改动任何既有红线**（本仓 OpenBase A 类仍为 0、工作树噪音口径不变；§1.4 的 107 仍为其时点基线口径）。

| 项 | 登记内容 |
|----|---------|
| 段/任务 | **S6 段 T1 边界收口**（S6-T1-1~4） |
| 口径闭环结论 | ✅ **S6-T1 口径闭环完成**（2026-09-10，S6 批次 1）：统一前端唯一维护面 = `OpenBase/openbase-ui`；四仓 `frontend/` 冻结声明（保留不删 / 不再构建/发布 / 后端不挂载产物）；3 处改造点（OpenMemory nginx `:90,93`、OpenLLM `docker-compose.yml:141-172` 与 `docker-compose.prod.yml:19`、DPS/OpenRAG CI）逐条登记四元组齐备 |
| 物理闭环结论 | ⏳ **物理闭环待各子系统执行（PENDING 交 S7 按 Q-S6-D7 口径复核）**：四仓实际改造需各子系统仓写权限，沙箱内不执行、不伪造 |
| 证据锚点 | 登记文档《OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md》（OB-S6-T1-FRONTEND-FREEZE-v1.0.0，`doc/planning/`）；后端不挂载静态断言 `tests/test_s6_t1_frontend_boundary.py`；前端侧冻结声明落点 `openbase-ui/docs/frontend-frozen.md` |
| 引用位（本清单） | 本条（§5.6）；与跨仓提交放行清单 §0「统一前端口径」同口径，见其 v1.0.6 加注 |

---

### 5.7 S6 段门禁登记（v1.0.4 新增，2026-09-10）

> 加注口径：本次仅**追加 S6（前端段）段门禁结论登记**，**不改变 §1.1 五仓对照表任何既有计数与 A/B/C 归类**（本仓 OpenBase A 类仍为 0、工作树噪音口径不变；§1.4 的 107 仍为其时点基线口径）。

| 项 | 登记内容 |
|----|---------|
| 段/任务 | **S6 段 = 前端段（FE-JT 收官）**：T1 边界收口 → T2 FE-3 → T3/T4 FE-R1-1/FE-R1-2 → T5 L3-2 贯通冒烟 → T6 段门禁收口 |
| 段门禁结论 | **未达最终通过（非沙箱项 PENDING）**——① 已达成：FE-3（S6-T2）、FE-R1-1 前端侧回归（S6-T3）、FE-R1-2 前端侧回归（S6-T4）、覆盖率与 Lint 门禁（97.08/90/88.46/97.08；lint 0 problem）、3 处改造口径闭环；② PENDING：UI-E2E 关键页 PASS（B1）、L3-2 真实受信通道双签（B2）；③ 物理闭环 PENDING（B5 交 S7） |
| 前端侧提交批次 | 批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 `477eb80`（`feat(ui): S6-T5 L3-2 贯通冒烟基座与 S6-T6 段门禁回写`）（承载版本 `openbase-ui` **1.3.0**，`dist-v1.3.0`） |
| 证据锚点 | `doc/test/evidence/s6/l3-2-smoke.json`（`status=PENDING`）、`doc/test/evidence/s6/ui-e2e/{results.json,status.json}`、`doc/test/evidence/s6/coverage-summary.json`、`doc/test/evidence/s6/segment-gate.json`；开发/测试文档 `doc/development/OpenBase-S6-…-DevLogReport-v1.0.0.md`、`doc/test/OpenBase-S6-…-测试报告-v1.0.0.md` |
| 对清点的影响 | **无**：OpenBase A 类仍为 **0**（S6 提交面为 `openbase-ui/**` + 仓根/`doc/**` 文档 + `doc/test/evidence/s6/**` 证据，均属 OpenBase 自身维护面，不改变四仓 A/B/C 计数）；`git ls-files openbase-ui` 计数随 S6 新增文件**递增**（属 S6 提交面显式登记项，见 §1.4 计数口径说明） |
| 引用位（本清单） | 本条（§5.7）；与跨仓提交放行清单 §0「S6 段门禁结论加注」、其 §5 OpenBase 行「S6 前端段提交批次登记」同口径 |

---

### 5.8 S6 段门禁批准登记（v1.0.5 新增，2026-09-11）

> 加注口径：本次仅**追加 S6（前端段）段门禁「人工批准」结论登记**（**v1.0.x 修订：S6 段门禁批准（挂起口径）**），**不改变 §1.1 五仓对照表任何既有计数与 A/B/C 归类**（本仓 OpenBase A 类仍为 0；§1.4 的 107 仍为其时点基线口径），亦**不改动 §5.7 既有登记内容**。

| 项 | 登记内容 |
|----|---------|
| 段/任务 | **S6 段 = 前端段（FE-JT 收官）**（同 §5.7） |
| **批准口径（统一逐字登记）** | `2026-09-11 S6 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认；前端侧门禁全绿（覆盖率 97.08/90/88.46/97.08 达标、lint 0 problem、FE-R1-1/FE-R1-2 前端侧通过、FE-3 达成、3 处改造口径闭环）；UI-E2E 关键页 PASS（B1）与 L3-2 真实受信通道双签（B2）按挂起口径处理（PENDING 登记不阻断本次批准，交非沙箱环境复核）；遗留=无阻断项` |
| **挂起口径（B1~B6）** | B1（UI-E2E 关键页 PASS 9 页）与 B2（L3-2 真实受信通道双签）**按挂起口径 PENDING 登记，不阻断本次批准**，交非沙箱环境复核；B3（真实双租户数据面）/ B4（真实 IdP 回调与吊销）/ B6（nginx `/ui/` 发布回滚实测）为非沙箱复核项；**B5（四仓 `frontend/` 物理改造与 CI 收敛）归各子系统对话 / S7** 按 Q-S6-D7 复核。逐条挂起原因/复核动作/归属见《OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md》§4.1② |
| **S6 相关文档新版本号** | ① DevLogReport（文件名 v1.0.0）→ 内部 **v1.0.1**（[Review] → [Approved]）；② 测试报告（文件名 v1.0.0）→ 内部 **v1.0.1**（[Review] → [Approved]）；③ S6 冻结与改造口径登记（文件名 v1.0.0）→ 内部 **v1.0.3**（[Draft] → [Approved]）；④ 设计草案（仓根，文件名 v1.0.0）→ 内部 **v1.0.2**（[Approved] 保持）；⑤ 立项方案（仓根，文件名 v1.0.0）→ 内部 **v1.1.2**（[Approved] 保持）；⑥ 本文档（清点总清单）→ 内部 **v1.0.5**；⑦ 跨仓提交放行清单（`doc/development/`）→ 内部 **v1.0.8** |
| **S6 提交号链（五提交号）** | `2abe52a`（批 1 统一前端冻结与改造口径登记 + lint 转绿）/ `aa6c5bd`（批 2 模块导航壳与隔离呈现回归 + 发布形态参数化）/ `72b19da`（批 3 登录态与吊销回归）/ `477eb80`（批 4 L3-2 贯通冒烟基座与段门禁回写）/ `5a1b17d`（S6 台账批次 4 提交号回填）；承载版本 `openbase-ui` **1.3.0**（`dist-v1.3.0`） |
| 证据锚点 | 《OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md》§4.1（批准结论登记）；`doc/test/evidence/s6/**`；§5.7 原有证据索引不变 |
| 对清点的影响 | **无**：仅加注，§1.1 五仓对照表计数与 A/B/C 归类、§1.4 统一前端口径与计数说明均不变（OpenBase A 类仍为 0） |
| 引用位（本清单） | 本条（§5.8）；与跨仓提交放行清单 §0「S6 段门禁批准与挂起口径加注」、其 §5 OpenBase 行「S6 提交批次列表（五提交号）」同口径 |

---

## §6 后续动作清单

| # | 动作 | 责任方 | 前置条件 | 交付物/状态回写 |
|:---:|------|--------|---------|----------------|
| 1 | 人工裁断 23 项「需人工判定」（§5.2）与 7 项边界确认（§5.3） | 各子系统负责人 / 项目负责人 | 本文档 [Approved] | 裁定结论回写子系统清单 §5 |
| 2 | 按 §3 逐仓分批入仓提交（OpenMemory 4 / OpenRAG 4 / OpenLLM 6 / DPS 4） | 用户在沙箱外人工执行 | 裁定完成 + 分支就绪 | 各仓 commit hash |
| 3 | 4 项混合文件 `git add -p` 拆分（§5.1） | OpenLLM 子系统 | 提交前 | hunk 拆分记录 |
| 4 | 提交后逐仓回归（§4.2 命令） | 各子系统 | 各仓提交完成 | 回归结果 |
| 5 | 回填各仓 hash 至 JT 台账与任务卡卡尾（§3.6） | 各子系统 | 提交 + 回归通过 | 任务卡 v1.4.0/v1.5.0/v1.6.0 与 DPS S5 卡尾 |
| 6 | 四仓清单勾稽 + OpenBase 跨仓会签（§4.1 步骤 3~4） | OpenBase（AD） | 5 完成 | 会签记录；本文档 [Review] → [Approved] |
| 7 | 放行清单 v1.0.2 → v1.0.3 回写（§2.8 共 10 条） | OpenBase（AD） | 6 完成 | `doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md` 升版 |
| 8 | 进入真实 HTTP 双签联调窗口（放行清单 §6） | 部署/联调窗口 + S7 | 6 完成 | 联调记录 |
| 9 | 可选卫生批：各仓 `.gitignore` 增补与历史卫生债清理（§5.3-6/7、§3.1 专项叮嘱①） | 各子系统 | 放行主体完成后 | 独立卫生 commit |

---

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-10 | AD（跨项目分析 / 只读盘点整合） | 初始版本：汇总四仓（OpenMemory 364 / OpenRAG 67 / OpenLLM 折叠 430≈展开 1555 / DPS 57）与 OpenBase 自身（7 项 dogfood-output 噪音、无联调产物）联调产物清点结果，建立 A/B/C + 需人工判定四类口径的五仓对照表；逐仓列出与跨仓放行清单 v1.0.2 的 **7 条差异**及 v1.0.3 回写建议（10 条）；给出四仓入仓操作指引（分支/批次/git add 模板/排除清单/回归命令/hash 回填位）、会签与核验流程、23 项人工裁定与 7 项边界确认的残余风险清单及后续动作清单。**本次仅新建本文档，未执行任何 git 写操作，未改动任何代码与其他文档** |
| v1.0.1 | 2026-09-10 | AD（跨项目分析 / 只读盘点整合） | **v1.0.x 修订：统一前端定案**——新增 §1.4「统一前端口径与清点影响」：各子系统 `frontend/` 改动一律不属联调提交面（归 B/C 类，逐仓核对 OpenMemory 8 项 B 类 / DPS C-11 / OpenLLM·OpenRAG 无 status 条目，被误列 A 类 0 项）；openbase-ui 属 OpenBase 仓维护面且本次无未提交改动（不增加提交面）；既有 A/B/C/人工判定计数与归类**不变**。仅回写本文档，未执行任何 git 写操作，未改动任何代码 |
| v1.0.2 | 2026-09-10 | AD（跨项目分析 / 只读盘点整合） | **S5（DPS）段门禁批准登记**：新增 **§5.5「S5（DPS）段门禁批准登记」**——登记「**S5（DPS）段门禁已批准**」（2026-09-10 人工批准，评审人=项目负责人经 AI 开发会话人工确认），含批准口径原文、门禁五项逐条（① 画像隔离用例全绿 ② 协议头入站校验生效 ③ 级联阻断生效 ④ person 复合唯一存量回填 0 孤儿 ⑤ L3-2 贯通冒烟通过；证据 `s5_gate_self_check.json`）、**DPS 四项文档新版本号 v1.0.1**（设计草案 / DevLogReport / 测试报告 / K07 端点-过滤矩阵填报，随段门禁批准内部版本回写）、入仓执行依据（《DPS-联调产物待提交清单-v1.0.0》§2 与 §6.1；跨仓放行清单 §3.3 同步登记，放行清单内部版本 v1.0.5）与遗留（Pull 真实 HTTP 双签 PENDING / 非沙箱复核 / DPS hash 待回填）；**不改变** §1.1 五仓对照表任何计数与 A/B/C 归类（DPS A 52 / B 3 / C 2 口径不变）。本次仅回写本文档与 OpenBase 侧台账，未执行任何 git 写操作，未改动任何代码 |
| v1.0.4 | 2026-09-10 | AI（S6 批次 4 开发会话） | **S6 段门禁登记**：新增 **§5.7「S6 段门禁登记」**——登记 S6（前端段）段门禁结论（已达成：FE-3/FE-R1-1/FE-R1-2 前端侧回归、覆盖率 97.08/90/88.46/97.08、lint 0 problem、3 处改造口径闭环；PENDING：UI-E2E 关键页 PASS B1、L3-2 真实受信通道双签 B2、物理闭环 B5 交 S7）、前端侧提交批次（批 1 `2abe52a` / 批 2 `aa6c5bd` / 批 3 `72b19da` / 批 4 `477eb80`；承载版本 1.3.0）与证据锚点（`doc/test/evidence/s6/**`）。**仅加注**：§1.1 五仓对照表计数与 A/B/C 归类、§1.4 统一前端口径与计数说明均不变（OpenBase A 类仍为 0）；未执行任何 git 写操作，未改动任何代码 |
| v1.0.5 | 2026-09-11 | 项目负责人（段门禁人工批准）/ AI（批准注记回写） | **v1.0.x 修订：S6 段门禁批准（挂起口径）**：新增 **§5.8「S6 段门禁批准登记」**——登记 2026-09-11 S6 段门禁**人工批准**结论，含批准口径（统一逐字登记）、**挂起口径（B1~B6 逐条归属：B1/B2 挂起不阻断、B3/B4/B6 非沙箱复核、B5 归各子系统对话/S7）**、S6 相关文档新版本号（DevLogReport/测试报告 v1.0.1；冻结与改造口径登记 v1.0.3；设计草案 v1.0.2；立项方案 v1.1.2；清点总清单 v1.0.5；放行清单 v1.0.8）与 **S6 提交号链（`2abe52a`/`aa6c5bd`/`72b19da`/`477eb80`/`5a1b17d`，五提交号）**。**仅加注**：§1.1 五仓对照表计数与 A/B/C 归类、§1.4 统一前端口径与 §5.7 原文均不变（OpenBase A 类仍为 0）；未执行任何 git 写操作，未改动任何代码 |
