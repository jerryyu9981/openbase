# OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-S7-SIGNOFF-TPL-v1.0.0 |
| 版本 | v1.0.1 |
| 状态 | [Review]（v1.0.1 修订：**OpenRAG 侧填报位已填写**——§2.2 四批 hash/回归、§4.1 勾稽行、§5 hash 回填行 + §2.5 OpenBase 基线回写 `cdfbd5b`→`f360cef`；其余三仓填报与跨仓会签完成后按文档版本管理规范升版） |
| 日期 | 2026-09-11 |
| 作者 | AD（跨项目分析） |
| 用途 | **供四仓（OpenMemory / OpenRAG / OpenLLM / DPS）入仓与会签填报**：统一承载「前置裁断 → 分批入仓 → hash 回填 → 勾稽会签」全流程的空白填报位，使各子系统对话按同一表格口径执行并回填证据；本模板本身**不代为执行四仓 git 命令**，仅提供可套用结构与命令模板 |
| 上游依据 | ①《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md》（仓根，OB-S7-v1.0.0）§2.2 四仓入仓状态与工作树清点口径 / §3.2 Q-S7-1（各仓入仓与会签闭环口径）、Q-S7-2（B1~B6 非沙箱回填与验收口径）/ §4 S7-T7-1~S7-T7-4（跨仓入仓核验与会签断言）/ 附录 C 提交号索引；②《OpenBase-联调产物清点核对总清单-v1.0.0.md》（`doc/planning/`，内部 v1.0.5，OB-INTG-CLEARANCE-v1.0.0）§1.1 五仓对照表 / §4.1 会签五步流程 / §5.2 待人工判定 23 项 / §5.3 边界确认 7 项 / §5.5~§5.8（S5/S6 段门禁批准登记）；③《OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》（`doc/development/`，内部 v1.0.8，OB-INTG-CROSSREPO-RELEASE-v1.0.0）§0 通用红线、各仓小节（§1 OpenMemory / §2 OpenLLM / §3 DPS / §4 OpenRAG / §5 OpenBase）、§7 清单索引与流程；④四仓分清单：《OpenMemory-联调产物待提交清单-v1.0.0.md》《OpenRAG-联调产物待提交清单-v1.0.0.md》《OpenLLM-联调产物待提交清单-v1.0.0.md》《DPS-联调产物待提交清单-v1.0.0.md》（各仓 `doc/planning/` 下，批次划分与计数取自分清单） |
| 适用范围 | S7 段 S7-T7「跨仓入仓核验与会签」执行面（四仓入仓、hash 回填、四仓勾稽、跨仓会签、清单升版）；**沙箱仅允许操作 OpenBase 仓**，四仓入仓/回填/勾稽命令须由用户在**沙箱外**执行 |
| 执行面登记 | **A 面（沙箱可判定）**：清单结构对账、OpenBase 侧会签汇总与清单升版、本模板文档维护；**B 面（联调窗口/沙箱外必需）**：四仓分批 `git add`/`git commit`、四仓 `git status` 回读、hash 回填、四仓回归——凡 B 面未真实执行项一律登记 `PENDING`，**禁止伪造通过、禁止伪造 hash**（立项方案 §3.2 Q-S7-1、§4 S7-T7-1） |

### 使用说明（四步）

本模板按 **① 前置裁断 → ② 分批入仓 → ③ hash 回填 → ④ 勾稽会签** 四步推进，各子系统对话按下列对应章节填报：

1. **前置裁断**（§1）：各子系统负责人先对本仓「待人工判定项」（合计 23 项）与「边界确认项」（合计 7 项）逐项裁定归属（A/B/C）与结论；裁断完成是入仓的前置门禁（总清单 §6 后续动作清单第 1 项）。
2. **分批入仓**（§2）：各子系统按本仓分清单**逐批**执行「逐项显式 `git add`（**禁用 `git add -A` / `git add .`**）+ `git commit`」，每批提交前 `git diff --cached --stat` 复查暂存面，每批提交后按 §3 红线自检、按 §2 回归命令回填结果。
3. **hash 回填**（§5）：各子系统将实际 commit hash 回填至各自 JT 台账与《OpenBase-数据隔离实现任务卡》对应版本卡尾（受限则如实登记 `PENDING`）。
4. **勾稽会签**（§4、§6、§7、§8）：以总清单 §1.1 为基准逐仓回读 `git status --porcelain -uall` 确认 A 类差异为 0；OpenBase 侧汇总 hash 形成会签记录（总清单 §4.1 五步），并按 S7-T7 断言登记证据与结论。

> **填报纪律**：表格中以「（示例）」标注的值为**示例**，填报时必须替换为本仓实测值；所有计数与上游文档（总清单 §1.1、各仓分清单）保持一致，**不得编造**；`待填` 单元格由各子系统对话/会签人填写。

---

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AD（跨项目分析） | 初始版本：S7 跨仓入仓与会签执行模板（可填报）。含 §1 前置裁断表（1.1 待人工判定 23 项 / 1.2 边界确认 7 项）、§2 逐仓入仓执行表（OpenMemory/OpenRAG/OpenLLM/DPS 四子表，批次与计数取各仓分清单）、§3 入仓红线检查清单（勾选式，逐仓一列）、§4 逐仓勾稽核对表（含核对命令模板与判定规则）、§5 hash 回填表、§6 跨仓会签记录表（五步）、§7 S7-T7 断言对照表（S7-T7-1~4）、§8 遗留与 PENDING 登记。**本次仅新建本模板一个文件，未执行任何四仓 git 写操作、未改动任何代码与其他文档** |
| v1.0.1 | 2026-09-11 | AI（S3 入仓会话）/ 项目负责人（入仓批准） | **OpenRAG 侧填报**：§2.2 表四批「提交 hash / 回归结果」由待填改为实测（`9e93c1c` / `0bda158` / `f48ea08` / `5fafc0a`；S3 组 144 passed、四静态扫描/K07/L3-2 退出码 0）；§4.1 勾稽表 OpenRAG 行回读 = 1、A 类差异 = 0；§5 hash 回填表 OpenRAG 行登记完成；§2.5 与 §4.1 的 OpenBase 行基线由 `cdfbd5b` 回写为 **`f360cef`**（工作树 7 → 10 项）。**其余三仓填报位、§3 红线勾选、§6 会签记录、§7 S7-T7 断言结论保持待填**，随各子系统入仓与 OpenBase 会签完成；本次未执行任何 git 提交 |

---

## §1 前置裁断表

> 本章为入仓前置门禁：**裁断未完成不得进入批量入仓**（总清单 §6 动作 1）。裁定结果回写各仓分清单 §5，并作为 §2 批次 `git add` 集合的最终依据。

### 1.1 待人工判定 23 项（逐仓列出，留「裁定」栏）

> 明细取自《联调产物清点核对总清单-v1.0.0》§5.2（OpenMemory 8 + OpenLLM 12 + DPS 3 = 23；OpenRAG / OpenBase 为 0）。「建议处置」为分清单/放行清单既有建议，供裁断参考；「裁定」栏须填写 **纳入 A / B / C** 及批次号。

| 序号 | 仓 | 文件路径 | 建议处置（上游） | 裁定（纳入 A/B/C） | 裁定人/日期 |
|:---:|----|----------|------------------|:---:|------|
| 1 | OpenMemory | `.devflow/state.json` | 建议不入库并补 `.gitignore`（判 C 类） | 待填 | 待填 |
| 2 | OpenMemory | `scripts/extract_backend_routes.py` | 按引用关系并批（判 A/B） | 待填 | 待填 |
| 3 | OpenMemory | `api/middleware/degradation.py` | 建议并入批 0（A 类） | 待填 | 待填 |
| 4 | OpenMemory | `npm-fix.js` | 建议判 C 类排除 | 待填 | 待填 |
| 5 | OpenMemory | `npm-wrapper.js` | 建议判 C 类排除 | 待填 | 待填 |
| 6 | OpenMemory | `test_authz_trust_cr008.py` | 建议并入批 0（A 类） | 待填 | 待填 |
| 7 | OpenMemory | `test_degradation_v71.py` | 按引用关系并批 | 待填 | 待填 |
| 8 | OpenMemory | `test_server_middleware_cr009_012.py` | 建议并入批 0（A 类） | 待填 | 待填 |
| 9 | OpenLLM | `backend/app/api/openllm_gateway.py`（J-1） | `git add -p` 按 hunk 拆分：S4 hunk → 批 4；need-star hunk → B 类 | 待填 | 待填 |
| 10 | OpenLLM | `backend/app/api/writeback.py`（J-2） | 同 J-1（S4 → 批 4；need-star → B 类） | 待填 | 待填 |
| 11 | OpenLLM | `backend/app/core/config.py`（J-3） | 同 J-1（S4 → 批 3；need-star → B 类） | 待填 | 待填 |
| 12 | OpenLLM | `backend/main.py`（J-4） | 同 J-1（S4 → 批 4） | 待填 | 待填 |
| 13 | OpenLLM | `backend/app/edgerouter/schemas/router.py`（J-5） | 清单外；判 A 类批 1 或批 4 | 待填 | 待填 |
| 14 | OpenLLM | `backend/tests/unit/test_billing_v2_api.py`（J-6） | 判 B 类，不得混入批 4/6 | 待填 | 待填 |
| 15 | OpenLLM | `backend/tests/unit/test_debug_gateway_ollama.py`（J-7） | 含本机绝对路径，建议排除出库 | 待填 | 待填 |
| 16 | OpenLLM | `backend/app/mcp/__init__.py`（J-8） | 判 A 类批 1 | 待填 | 待填 |
| 17 | OpenLLM | `doc/planning/OpenLLM-OpenRAG接入迭代规划-v1.0.0.md`（J-9） | B 类或批 1，需负责人裁定 | 待填 | 待填 |
| 18 | OpenLLM | `doc/design/OpenLLM-DPS实例Pro化部署架构演进设计文档-v1.1.0.md`（J-10） | B 类或批 1 | 待填 | 待填 |
| 19 | OpenLLM | 同 J-10 归档旧版（J-11） | B 类或随 J-10 | 待填 | 待填 |
| 20 | OpenLLM | `OpenLLM_完整方案文档.html`（J-12） | 随 J-9 同批 | 待填 | 待填 |
| 21 | DPS | `src/engines/permission_engine.py` | 判 S5-T3 → B2，须确认无 v2.9.0 混入 | 待填 | 待填 |
| 22 | DPS | `src/tests/test_portrait_update_route.py` | 判 S5-T4/K14 → B2，与 `routes_profiles.py` 同批 | 待填 | 待填 |
| 23 | DPS | `doc/testing/evidence/s5_gate_self_check.json` | 含 `pending: true`，推荐随 B3 入库并标注 `evidence(pending: Q-DPS-5)` | 待填 | 待填 |
| — | OpenRAG | （无） | 本仓 status 内无归属未明项 | — | — |
| — | OpenBase | （无） | 仅 `dogfood-output/` 7 项，全部不提交 | — | — |
| 合计 | — | **23（OpenMemory 8 + OpenLLM 12 + DPS 3）** | — | — | — |

> **裁断结论汇总（待填）**：纳入 A 类 ____ 项 / 纳入 B 类 ____ 项 / 纳入 C 类 ____ 项；裁断人 ______；日期 ______。

### 1.2 边界确认 7 项（含「结论」栏）

> 事项取自《联调产物清点核对总清单-v1.0.0》§5.3（7 项）。其中 OpenRAG `repository` gitlink 禁 add、OpenRAG `version.json`/`.env.example` 口径、OpenMemory `.gitignore` 补 `.env.*` 与 `.devflow/state.json`、OpenLLM `.pyc` 用 `git rm -r --cached`、名单外待裁定项为**会签前须裁定项**（立项方案 §7 R-4）。

| # | 事项 | 现状（上游） | 结论 | 结论人/日期 |
|:---:|------|------|------|------|
| 1 | **OpenRAG `version.json` 版本对齐** | 已跟踪、内容 `version=1.7.0`（`devflowVersion=2.10.0`），本次 status 无改动；S3 承载版本 v1.10.0（拟，Q-RG-1）。当前不作为提交项 | 待填（如需对齐，另立独立小批，不计入 S3 四批） | 待填 |
| 2 | **OpenRAG `.env.example` 键未回写** | 已跟踪、status 无改动；S3 env 键实际落在 `src/openrag/config/settings.py`（`OPENRAG_IDENTITY_*` 等） | 待填（若补示例键，随 S3-B2 独立 hunk 或单独小批；**不得写入真实密钥**） | 待填 |
| 3 | **OpenRAG `repository` gitlink 子仓** | `git ls-files -s repository` → `160000 0ed102a…` | 待填（**任何批次不得 `git add repository`**；如需提交须在内嵌仓自身会话内独立作业） | 待填 |
| 4 | **OpenMemory `.env.example` 配置键补齐** | 仅新增空密钥门禁两键；S2 所需 `trusted_proxy_sources` / `strip_inbound_identity_headers` / `enforce_inbound_identity_headers` 未出现 | 待填（若补，并入批 0 的 `.env.example`） | 待填 |
| 5 | **OpenMemory `.gitignore` 增补与敏感文件历史核查** | `.env.shared-infra` 出现在工作树（C 类）；建议补 `.gitignore` 规则 **`.env.*`（保留 `!.env.example`）** 与 **`.devflow/state.json`** | 待填（另须 `git log --all -- .env.shared-infra` 核查历史是否泄露） | 待填 |
| 6 | **DPS 已入库历史卫生债** | 仓根 `1.0.0`（pip 输出）、`新建位图图像.bmp` 已被跟踪；`.gitignore` 含无效绝对路径规则 | 待填（另起卫生提交 `git rm --cached` + 修正忽略规则，**不在本次执行**） | 待填 |
| 7 | **OpenLLM `.pyc` 卫生债** | `.pyc` 已入库且被删除/修改（211 D + 71 M） | 待填（独立「噪音清理批次」：**`git rm -r --cached`** 处置 211 删除项 + `.gitignore` 增补；**不要恢复**已删 `.pyc`；不与 S4 混提） | 待填 |
| — | （名单外待裁定项） | OpenLLM J-5/J-9/J-10/J-11/J-12 等清单外项（见 §1.1 序号 13、17~20） | 待填（清单外路径先确认归属再并入批次，禁兜底 add） | 待填 |

> **边界结论汇总（待填）**：确认执行 ____ 项 / 另立独立批 ____ 项 / 维持现状 ____ 项；结论人 ______；日期 ______。

---

## §2 逐仓入仓执行表

> **通用纪律（四仓通用，引用放行清单 §0 与总清单 §3）**：① 只 add 预期路径，**严禁 `git add -A` / `git add .` 兜底**；每批提交前 `git diff --cached --stat` 复查暂存面仅含预期路径。② 中文/含空格路径在 PowerShell 中一律用**单引号**包裹。③ **严禁提交敏感文件**（`.env` / `.env.shared-infra` / `.env.e2e` / `data/edge_tokens.jsonl` 等）。④ 每仓提交后回归**失败即停止后续批次**；总体顺序建议 **OpenMemory → OpenRAG → OpenLLM → DPS → OpenBase 会签**。⑤ 下表 `git add` 命令模板为**占位路径示例**（`<仓根>/...` 表示相对本仓根路径，须替换为本仓实际测试结果与分清单 §2/§6 的完整逐项路径）；`提交 hash` 与 `回归结果` 列由各子系统对话填报。

### 2.1 OpenMemory（A 类 70，4 批；B 类 197 隔离 / C 类 89 排除 / 需人工判定 8）

| 批次号 | 批次主题 | 文件数（A 类） | git add 命令模板（逐项显式，禁 -A） | commit message 模板 | 提交 hash（待填） | 提交后回归命令 | 回归结果（待填） | 备注 |
|:---:|------|:---:|------|------|:---:|------|:---:|------|
| 批 0 | 基线批：S0 探活/前置 + 联调承载（版本对齐 / K05 / K06 / RA-05） | 29 | `git add '<仓根>/.env.example' '<仓根>/run_api.py' '<仓根>/src/openmemory/__init__.py' '<仓根>/src/openmemory/api/controllers.py' ...`（按分清单 §6.2 批 0 逐项 add 29 项） | `chore(om-baseline): OpenMemory 联调前置基线（S0 探活/启动门禁 + 版本对齐 + K05/K06/RA-05 承载）` | 待填 | `python -m pytest tests/unit tests/integration -q -p no:cacheprovider`（期望 1330 passed, 36 skipped） | 待填 | 混合文件（controllers.py/config.py 等）随基线落库；严格拆分须 `git add -p` |
| 批 1 | S2 五份文档 | 5 | `git add '<仓根>/OpenMemory-S2-…立项方案-v1.0.0.md' '<仓根>/OpenMemory-S2-…设计草案-v1.0.0.md' '<仓根>/doc/development/OpenMemory-S2-…-DevLogReport-v1.0.0.md' '<仓根>/doc/test/OpenMemory-S2-…-测试报告-v1.0.0.md' '<仓根>/doc/design/OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md'` | `docs(s2): OpenMemory S2 五份文档入库（立项/设计草案/DevLogReport/测试报告/K07 矩阵填报）` | 待填 | 同上（本批为纯文档，随终批全量回归） | 待填 | 全程未跟踪（??） |
| 批 2 | S2 源码 / 迁移 / 脚本 | 21 | `git add '<仓根>/src/openmemory/identity' '<仓根>/src/openmemory/api/middleware/identity_gate.py' '<仓根>/src/openmemory/api/middleware/block_subject_gate.py' '<仓根>/alembic/versions/v702_session_registry_meta.py' ...`（按分清单 §2 批 2 逐项 add） | `feat(s2): S2 协议头入站/行控收口/复合唯一/存量回填/事件消费端/矩阵校验 源码与迁移（T1~T13，alembic v702~v704）` | 待填 | `python -m ruff check src scripts` + `python scripts/k07_endpoint_matrix.py --verify --matrix '<仓根>/doc/design/OpenMemory-K07-…md' --openapi '<仓根>/scripts/api_baseline.json'` | 待填 | identity 包 + 中间件 + alembic + 脚本 |
| 批 3 | S2 测试与 CI | 15 | `git add '<仓根>/tests/unit/test_s2_t1_protocol_gate.py' ... '<仓根>/tests/unit/test_l3_2_smoke.py' '<仓根>/tests/unit/test_s2_segment_gate_selfcheck.py' '<仓根>/.github/workflows/ci.yml'`（按分清单 §2 批 3 逐项 add 15 项） | `test(s2): S2 T1~T13 RED 断言与段门禁自检用例 + CI s2-k07-matrix-gate job` | 待填 | `python scripts/smoke_l3_2.py` + 全量回归（同批 0 命令） | 待填 | `ci.yml` 为混合文件（含 v7.0 性能基线 job），严格拆分见分清单 §1.5 |
| **小计** | **4 批** | **70** | — | — | — | — | — | A+B+C+人工 = 70+197+89+8 = **364** |

> OpenMemory 分支建议：基线批自 `release/v6.9.0`（`6cbfb71`）切 `release/v7.2.0`；S2 批次切 `release/v7.3.0`。**B 类 197（v7.0~v7.2 自身在途）与 C 类 89（含敏感 `.env.shared-infra`）严禁进入批 0~批 3**；若先落 B 类基线，须保证 A 类批 0 引用完整（分清单 §3.1 依赖提示）。

### 2.2 OpenRAG（A 类 67，4 批；B/C 均为 0）

| 批次号 | 批次主题 | 文件数（A 类） | git add 命令模板（逐项显式，禁 -A） | commit message 模板 | 提交 hash（待填） | 提交后回归命令 | 回归结果（待填） | 备注 |
|:---:|------|:---:|------|------|:---:|------|:---:|------|
| B0 | 基线批（S0） | 0 | （无——本仓实测 0 条，HEAD `959ef83` 已为干净基线，无需基线提交） | — | — | — | — | 不产生提交 |
| S3-B1 | 文档 | 6 | `git add '<仓根>/OpenRAG-S3-…立项方案-v1.0.0.md' '<仓根>/OpenRAG-S3-…设计草案-v1.0.0.md' '<仓根>/doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.md' '<仓根>/doc/design/OpenRAG-K07-端点过滤矩阵填报-v1.0.0.matrix.json' '<仓根>/doc/development/OpenRAG-S3-…-DevLogReport-v1.0.0.md' '<仓根>/doc/test/OpenRAG-S3-…-测试报告-v1.0.0.md'` | `docs(s3): OpenRAG S3 六份文档入库（立项 v1.1.0/设计草案 v1.0.1 [Approved]；DevLog v1.0.1/测试报告 v1.0.0/K07 填报 v1.0.0）` | **`9e93c1c`** | （文档批，随终批全量回归） | **完成**（6 files, +3429） | 全部未跟踪 |
| S3-B2 | identity / 中间件 / 配置 / 装配 / 审计 | 25 | `git add '<仓根>/src/openrag/identity' '<仓根>/src/openrag/api/middleware/identity_gate.py' '<仓根>/src/openrag/api/middleware/block_subject_gate.py' '<仓根>/src/openrag/api/middleware/role_gate.py' '<仓根>/src/openrag/config/settings.py' ...`（按分清单 §2.4 逐项 add 25 项） | `feat(s3): 身份接入收口 identity/中间件/配置（协议头四态+B1、级联阻断、角色档位、审计六键、事件消费端、M1/M2）` | **`0bda158`** | （源码批，随终批全量回归） | **完成**（25 files, +3386 −22） | 17 ?? + 8 M；`repository` gitlink 禁 add |
| S3-B3 | storage / 迁移 / 模型 / 路由 / 编排 | 12 | `git add '<仓根>/src/openrag/storage/migrations.py' '<仓根>/src/openrag/storage/postgres.py' '<仓根>/src/openrag/storage/sqlite.py' '<仓根>/src/openrag/models/collection.py' ...`（按分清单 §2.5 逐项 add 12 项） | `feat(s3): 数据隔离 storage/迁移/路由（归属列幂等迁移+保留码回填+B2 碰撞防护、行控强制注入、复合唯一 409）` | **`f48ea08`** | （源码批，随终批全量回归） | **完成**（12 files, +1441 −247） | 1 ?? + 11 M |
| S3-B4 | scripts / tests / CI | 24 | `git add '<仓根>/scripts/k07_endpoint_matrix.py' '<仓根>/scripts/tenant_backfill_report.py' '<仓根>/scripts/scan_auto_purge.py' ... '<仓根>/tests/unit/test_s3_t1_identity_gate.py' ... '<仓根>/run_tests.py' '<仓根>/.github/workflows/ci-cd.yml'`（按分清单 §2.6 逐项 add 24 项） | `test(s3): S3 T1~T11 RED 断言/K07 矩阵隔离用例/四静态扫描与 L3-2 冒烟脚本 + CI s3-static-gates job` | **`5fafc0a`** | `python -B -m pytest tests/unit -p no:cacheprovider`（S3 组 144 用例恒绿）+ 四静态扫描逐条退出码 0 + `python scripts/k07_endpoint_matrix.py` + `python scripts/smoke_l3_2.py` | **完成**（S3 组 144 passed；四静态扫描/K07/L3-2 逐条退出码 0） | 21 ?? + 3 M；`ci-cd.yml` 为混合 CI 文件 |
| **小计** | **4 批（B0 无提交）** | **67** | — | — | — | — | — | A+B+C+人工 = 67+0+0+0 = **67**（+本文档自身为 68） |

> OpenRAG 分支建议：自 `master`（`959ef83`）切 `release/v1.10.0`（拟）。**严禁 `git add repository`**（gitlink `160000 0ed102a…`）。

### 2.3 OpenLLM（A 类 75，6 批（批 5+6 可合为 5）；B 类 13 隔离 / C 类 1455 排除 / 需人工判定 12）

| 批次号 | 批次主题 | 文件数（A 类） | git add 命令模板（逐项显式，禁 -A） | commit message 模板 | 提交 hash（待填） | 提交后回归命令 | 回归结果（待填） | 备注 |
|:---:|------|:---:|------|------|:---:|------|:---:|------|
| 批 1 | 基线批（S0 探活 + 版本对齐 v2.14.3 + v2.13/v2.14 既有基线） | 15 | `git add '<仓根>/version.json' '<仓根>/backend/app/__init__.py' '<仓根>/doc/release/DevFlow-Release-Note-v2.14.3.md' '<仓根>/backend/tests/unit/test_dps_probe_real_health.py' '<仓根>/backend/app/services/external_identity.py' ...`（按分清单 §2.1 逐项 add 15 项；**不得 add 4 个 need-star 测试文件**） | `chore: OpenLLM 基线收口（S0 探活 + 版本对齐 v2.14.3，按 S4-批次1基线收口登记清单 A~B）` | 待填 | `python -B -m pytest tests/unit -p no:cacheprovider`（306 passed 口径） | 待填 | 12 ?? + 3 M；基线可含原样落库，S4 增量后续以 M 形态再提交 |
| 批 2 | S4 文档（7 份） | 7 | `git add '<仓根>/OpenLLM-S4-…立项方案-v1.0.0.md' '<仓根>/OpenLLM-S4-…设计草案-v1.0.0.md' '<仓根>/doc/planning/OpenLLM-S4-批次1基线收口登记清单-v1.0.0.md' '<仓根>/doc/development/OpenLLM-S4-…-DevLogReport-v1.0.0.md' '<仓根>/doc/test/OpenLLM-S4-…-测试报告-v1.0.0.md' '<仓根>/doc/test/OpenLLM-JT-台账-S4.md' '<仓根>/doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.0.0.md'` | `docs(s4): OpenLLM S4 文档入库（立项 v1.1.0/设计草案 v1.0.1 [Approved]；DevLog v1.0.1/测试报告 v1.0.1/JT 台账 [Approved]；K07 填报；基线收口登记清单）` | 待填 | （文档批，随终批全量回归） | 待填 | 全部未跟踪 |
| 批 3 | identity 包 / 中间件 / 配置 | 15 | `git add '<仓根>/backend/app/identity' '<仓根>/backend/app/middleware/identity_gate.py' '<仓根>/backend/app/middleware/audit.py' '<仓根>/backend/app/core/config.py' '<仓根>/backend/app/services/external_identity.py' '<仓根>/backend/.env.example'`（`core/config.py` 含 need-star 增量须 `git add -p`，见 §1.1 J-3） | `feat(s4): 身份接入收口 identity 包/中间件/配置（S4-T2 透传基座、S4-T9 强校验、S4-T10 审计六键、S4-T12 角色档位、S4-T13 M1/M2、S4-T14 配置键）` | 待填 | （源码批，随终批全量回归） | 待填 | 13 ?? + 2 M；`config.py` 为 4 混合文件之一 |
| 批 4 | 客户端与网关 / 装配 | 15 | `git add '<仓根>/backend/app/edgerouter/adapters/dps_client.py' '<仓根>/backend/app/edgerouter/adapters/openmemory_client.py' '<仓根>/backend/app/edgerouter/adapters/openrag_client.py' '<仓根>/backend/app/edgerouter/adapters/profile.py' '<仓根>/backend/app/api/openllm_gateway.py' '<仓根>/backend/app/api/writeback.py' '<仓根>/backend/main.py' ...`（`openllm_gateway.py`/`writeback.py`/`main.py` 须 `git add -p`，见 §1.1 J-1/J-2/J-4） | `feat(s4): 编排出站透传与网关装配（S4-T3 出站头统一/REAL 收口、S4-T4 REAL 双义拆分全启用、S4-T6 服务账号写守卫、S4-T7/T8 通道 B 主 A 备接线）` | 待填 | （源码批，随终批全量回归） | 待填 | 全部 M（混合文件须 hunk 拆分） |
| 批 5 | scripts（scan / K07 / verify-env / smoke） | 8 | `git add '<仓根>/backend/scripts/scan_real_fallback_business_usage.py' '<仓根>/backend/scripts/scan_identity_bypass.py' '<仓根>/backend/scripts/k07_endpoint_matrix.py' '<仓根>/backend/scripts/k07_isolation_registry.py' '<仓根>/backend/scripts/smoke_l3_2.py' '<仓根>/backend/scripts/verify-env'` | `chore(s4): S4 静态扫描/K07 矩阵与注册表/verify-env 契约键/L3-2 冒烟脚本（S4-T11/T14/T15）` | 待填 | `python scripts/scan_real_fallback_business_usage.py`（0 命中）+ `python scripts/scan_identity_bypass.py`（0 绕过）+ `python scripts/k07_endpoint_matrix.py --verify` + `python scripts/verify-env/verify_env.py --fail-fast` | 待填 | 全部未跟踪；`scripts+tests` 合批则为 S4 四批 |
| 批 6 | tests（S4 T1~T15） | 15 | `git add '<仓根>/backend/tests/unit/test_s4_t1_baseline_probe.py' ... '<仓根>/backend/tests/unit/test_s4_t15_l3_2_smoke.py' '<仓根>/backend/tests/unit/test_real_contract_profile.py'`（按分清单 §2.6 逐项 add 15 项；**不得 add 4 个 need-star 测试文件**） | `test(s4): S4 T1~T15 RED 断言与段门禁自检用例 + test_real_contract_profile S0 修订（306 passed 口径）` | 待填 | `python -B -m pytest tests/unit -p no:cacheprovider` + `python scripts/smoke_l3_2.py`（段门禁自检五项） | 待填 | 全部未跟踪；批 5+批 6 合批即 5 批 |
| **小计** | **6 批（可合 5）** | **75** | — | — | — | — | — | A+B+C+人工 = 75+13+1455+12 = **1555**（`-uall`） |

> **OpenLLM 计数口径附注**：本表批次与计数**取自《OpenLLM-联调产物待提交清单-v1.0.0》§1.3 与 §2**（批 1~批 6 = 15/7/15/15/8/15 = **75**）。《清点总清单》§2.8-5 另有一处「批 6 条目数 15 → 11」的回写建议（针对放行清单 v1.0.2 中误登记的 4 个 need-star 测试文件）；该 4 项在分清单中**已归 B 类隔离、不在 §2 批 6 的 15 项之内**。填报时以**分清单实测逐文件表为准**，如现场 `git status` 与分清单不符，须按 §4 判定规则先裁定再入仓并回写差异。
>
> OpenLLM 分支建议：基线批留在 `feature/v2.13.0-openrag`；S4 批次切 `feature/s4-identity-channel-b`（本地尚不存在，需新建；亦可留现分支叠加）。**B 类 need-star 13 项须独立分支 `feature/need-star-orchestration` + 独立批次隔离**。

### 2.4 DPS（A 类 52，4 批；B 类 3 隔离 / C 类 2 排除 / 需人工判定 3 ⊂ A）

| 批次号 | 批次主题 | 文件数（A 类） | git add 命令模板（逐项显式，禁 -A） | commit message 模板 | 提交 hash（待填） | 提交后回归命令 | 回归结果（待填） | 备注 |
|:---:|------|:---:|------|------|:---:|------|:---:|------|
| S5-B1 | 身份内核 / 配置 / 装配 | 19 | `git add '<仓根>/src/identity' '<仓根>/src/middleware/identity_gate_middleware.py' '<仓根>/src/middleware/block_subject_gate_middleware.py' '<仓根>/src/engines/identity_event_engine.py' '<仓根>/src/config.py' '<仓根>/src/database.py' '<仓根>/src/main.py' '<仓根>/src/rest_api/app.py' '<仓根>/src/rest_api/error_handlers.py'`（按分清单 §2 逐项 add 19 项） | `feat(s5): 身份内核/配置/装配（S5-T1 门禁、T3/T4 write guard、T6 事件双通道、T8 审计、T9 角色映射）` | 待填 | `python -m pytest src/tests/test_s5_t1_identity_gate.py … src/tests/test_s5_t12_l3_2_smoke.py -p no:randomly` | 待填 | 12 ?? + 7 M |
| S5-B2 | 路由 / 权限 / 审计 / 测试 | 17 | `git add '<仓根>/src/middleware/audit_middleware.py' '<仓根>/src/middleware/permission_middleware.py' '<仓根>/src/engines/permission_engine.py' '<仓根>/src/rest_api/routes/routes_profiles.py' '<仓根>/src/tests/test_s5_t1_identity_gate.py' … '<仓根>/src/tests/test_portrait_update_route.py'`（2 项需人工判定，见 §1.1 序号 21/22） | `feat(s5): 路由/权限/审计与 S5 T1~T12 用例` | 待填 | 同上（S5 隔离组独立进程回归） | 待填 | 含 `permission_engine.py`/`test_portrait_update_route.py` 待裁定项 |
| S5-B3 | 脚本 / 门禁 / 证据 | 8 | `git add '<仓根>/scripts/k07_endpoint_matrix.py' '<仓根>/scripts/tenant_code_reconcile.py' '<仓根>/scripts/person_key_backfill_report.py' '<仓根>/scripts/scan_auto_purge.py' '<仓根>/scripts/smoke_l3_2.py' '<仓根>/scripts/verify-env/contract.json' '<仓根>/.github/workflows/ci.yml' '<仓根>/doc/testing/evidence/s5_gate_self_check.json'` | `chore(s5): K07 门禁脚本/对账报告/verify-env 契约/门禁自检证据`（证据件含 `pending: true`，建议标注 `evidence(pending: Q-DPS-5)`） | 待填 | `python -m ruff check src` + `python scripts/k07_endpoint_matrix.py --check` + `python scripts/smoke_l3_2.py --quick` | 待填 | `ci.yml` 门禁依赖 k07 脚本，须与之同批或后于脚本提交 |
| S5-B4 | 联调文档 | 8 | `git add '<仓根>/DPS-S5-…立项方案-v1.0.0.md' '<仓根>/DPS-S5-…设计草案-v1.0.0.md' '<仓根>/doc/design/DPS-K07-端点过滤矩阵填报-v1.0.0.md' '<仓根>/doc/design/DPS-S5-failopen-DV裁定映射-v1.0.0.md' '<仓根>/doc/design/DPS-S5-person_key建模评审-v1.0.0.md' '<仓根>/doc/development/DPS-S5-写链幂等盘点-v1.0.0.md' '<仓根>/doc/development/DPS-S5-…-DevLogReport-v1.0.0.md' '<仓根>/doc/test/DPS-S5-…-测试报告-v1.0.0.md'` | `docs(s5): DPS S5 立项/设计/K07 填报/裁定映射/建模评审/DevLog/测试报告入库` | 待填 | （文档批，随终批全量回归） | 待填 | 全部未跟踪；文档内部版本 v1.0.1 |
| **小计** | **4 批** | **52** | — | — | — | — | — | A+B+C = 52+3+2 = **57**（人工 3 ⊂ A） |

> DPS 分支建议：留在 `main`（HEAD `6b39dd4`）。**B 类 3 项（v2.9.0 三份文档）须独立分支/独立批次（`docs(v2.9.0): …`），严禁混入 S5-B1~B4**。

### 2.5 四仓批次与计数汇总（预填，与分清单一致）

| 仓 | 基线 HEAD / 分支 | 建议批次 | A 类合计 | B 类 | C 类 | 需人工判定 | status 全量（-uall） | 提交数（合批后） |
|----|------------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| OpenMemory | `6cbfb71` / `release/v6.9.0` | 4（批 0=29 / 批 1=5 / 批 2=21 / 批 3=15） | **70** | 197 | 89 | 8 | **364** | 4 |
| OpenRAG | `959ef83` / `master` | 4（B0=0 / S3-B1=6 / S3-B2=25 / S3-B3=12 / S3-B4=24） | **67** | 0 | 0 | 0 | **67** | 4（可合 3） |
| OpenLLM | `a552cbf` / `feature/v2.13.0-openrag` | 6（15/7/15/15/8/15） | **75** | 13 | 1455 | 12 | **1555** | 6（可合 5） |
| DPS | `6b39dd4` / `main` | 4（S5-B1=19 / B2=17 / B3=8 / B4=8） | **52** | 3 | 2 | 3（⊂A） | **57** | 4 |
| **合计** | — | **18（合批后 17）** | **264** | 213 | 1546 | 23 | — | 18（合批 17） |
| OpenBase（本仓） | **`f360cef`** / `main`（2026-09-11 实测；原登记 `cdfbd5b`） | 0（无需放行） | 0 | 0 | 7（`dogfood-output/` 不提交） | 0 | **10**（3 `M` + 7 `??`） | 0 |

> 计数核对：A 类合计 **264** = 70+67+75+52；建议提交 **18** 个（OpenLLM 合批后 **17** 个）；需人工判定 **23** = 8+12+3；边界确认 **7**。以上与《清点总清单》§1.1 与本模板 §1 完全一致。

---

## §3 入仓红线检查清单（勾选式，逐仓一列）

> 每批提交前逐项自检，**任一红线触碰即停止该批**；「√」= 已确认满足，「×」= 违反（须回退并整改），「—」= 不适用。填报人/日期填于末行。

| # | 红线项 | 判定要点 | OpenMemory | OpenRAG | OpenLLM | DPS |
|:---:|------|------|:---:|:---:|:---:|:---:|
| 1 | **禁 `git add -A` / `git add .`** | 全程仅按分清单逐项显式 `git add`；提交前 `git diff --cached --stat` 复查 | 待填 | 待填 | 待填 | 待填 |
| 2 | **敏感文件零进入** | `.env` / `.env.shared-infra` / `.env.e2e` / `data/edge_tokens.jsonl`（含各仓 backend 变体）**不在任何批次** | 待填 | 待填 | 待填 | 待填 |
| 3 | **OpenRAG 禁 add `repository`（gitlink）** | `git ls-files -s repository` = `160000 0ed102a…`；任何批次不得 add | — | 待填 | — | — |
| 4 | **OpenLLM 4 混合文件 `git add -p`** | `api/openllm_gateway.py`、`api/writeback.py`、`core/config.py`、`main.py` 按 hunk 拆分（S4 hunk 入批，need-star hunk → B 类） | — | — | 待填 | — |
| 5 | **need-star 13 项独立分支隔离** | 4 need-star 测试 + `orchestration/auto.py`/`executor.py`/`explicit.py` 等 13 项 → 独立分支 `feature/need-star-orchestration` + 独立批次，commit message 标注 `need-star` | — | — | 待填 | — |
| 6 | **已入库 `.pyc` 用 `git rm -r --cached`** | 13 个 `__pycache__` 目录共 211 删除项，走独立噪音清理批；**禁止用 `git checkout`/`git restore` 恢复** | — | — | 待填 | — |
| 7 | **B 类自身在途不混批** | OpenMemory v7.x 197 项 / OpenLLM need-star 13 项 / DPS v2.9.0 3 项 不得与联调批混提 | 待填 | — | 待填 | 待填 |
| 8 | **C 类噪音不提交** | OpenMemory 89 / OpenLLM 1455 / DPS 2 一律排除 | 待填 | 待填 | 待填 | 待填 |
| 9 | **回归失败即停止后续批次** | 每批回归失败 → 停止，修正后重跑；通过再进入下一批/下一仓 | 待填 | 待填 | 待填 | 待填 |
| 10 | （附加）统一前端冻结口径 | 各子系统 `frontend/` 改动一律不入联调批（归 B/C 类） | 待填 | 待填 | 待填 | 待填 |
| — | **填报人 / 日期** | — | 待填 | 待填 | 待填 | 待填 |

---

## §4 逐仓勾稽核对表

> **核对方法（引用总清单 §4.1 第 3 步）**：以《清点总清单》§1.1 五仓对照表为**基准**，逐仓入仓完成后回读 `git status --porcelain -uall`，确认**仅剩 B 类隔离项 + C 类噪音 + 清单文档自身**，**A 类差异 = 0**；四份分清单 §7 双向核对自检结论须与实测一致。

### 4.1 勾稽核对表（基线计数预填，回读待填）

| 仓 | 清点基线 A/B/C 计数（预填实测值） | 入仓后 `git status --porcelain -uall` 回读 A/B/C 计数（待填） | A 类差异（须 0，待填） | 残余条目说明（仅 B/C + 清单文档自身） | 核对人/日期 |
|----|------|------|:---:|------|------|
| OpenMemory | A **70** / B **197** / C **89**（+人工 8；总 364） | 待填（期望 ≈ B197 + C89 + 人工8 + 清单文档自身） | 待填 | 待填（B 类 v7.x 在途 + C 类噪音 + 本仓清单文档） | 待填 |
| OpenRAG | A **67** / B **0** / C **0**（总 67；+清单文档 1 = 68） | **1**（入仓后实测，仅清单文档自身） | **0**（A 类差异归零） | 仅本仓清单文档自身（内部版本 v1.0.1，保持未跟踪） | AI（S7 入仓会话）/ 2026-09-11 |
| OpenLLM | A **75** / B **13** / C **1455**（+人工 12；`-uall` 总 1555） | 待填（期望 ≈ B13 + C1455 + 人工12 + 清单文档自身） | 待填 | 待填（B 类 need-star + C 类噪音 + 本仓清单文档） | 待填 |
| DPS | A **52** / B **3** / C **2**（总 57；人工 3 ⊂ A） | 待填（期望 ≈ B3 + C2 + 清单文档自身） | 待填 | 待填（B 类 v2.9.0 + C 类噪音 + 本仓清单文档） | 待填 |
| OpenBase（本仓） | A **0** / B **0** / C **7**（`dogfood-output/` 不提交） | 待填（期望 = 7，全部 dogfood-output） | 待填 | 待填（`dogfood-output/` 走查产物，不提交） | 待填 |

### 4.2 核对命令模板（占位路径，须替换）

```powershell
# OpenMemory —— 期望仅剩 B 类 197 + C 类 89 + 人工判定 8 + 本仓清单文档
Set-Location '<仓根>\OpenMemory'
git log -1 --format='%h %s'
(git status --porcelain -uall).Count          # 期望 = 364 - (A 类已提交数) + 清单文档自身
git status --porcelain -uall                  # 与分清单 §2 比对：A 类条目应归零
git status --porcelain -uall | Select-String 'test_s2_t'   # 期望无输出（S2 用例已提交）

# OpenRAG —— 期望仅剩清单文档自身（A 类 67 全部提交后）
Set-Location '<仓根>\OpenRAG'
git log -1 --format='%h %s'
(git status --porcelain -uall).Count          # 期望 = 1（仅清单文档；B/C/人工均为 0）

# OpenLLM —— 期望仅剩 B 类 13 + C 类 1455 + 人工判定 12 + 清单文档
Set-Location '<仓根>\OpenLLM'
git log -1 --format='%h %s'
(git status --porcelain).Count                # 折叠口径，与 -uall 双口径复核
git status --porcelain -uall | Select-String 'test_s4_t'   # 期望无输出（A 类已提交）

# DPS —— 期望仅剩 B 类 3 + C 类 2 + 清单文档
Set-Location '<仓根>\DPS'
git log -1 --format='%h %s'
(git status --porcelain -uall).Count          # 期望 = 5 + 清单文档自身

# OpenBase —— 期望仅剩 dogfood-output 7 项（不提交）
Set-Location '<仓根>\OpenBase'
git status --porcelain                        # 期望 7 条 dogfood-output/
python -m pytest tests
python -m ruff check openbase tests
```

### 4.3 判定规则

1. **A 类差异 = 0（通过）**：回读结果中**不含任何 A 类联调产物路径**（可与分清单 §2 逐文件表做集合差）；残余仅 B 类隔离项、C 类噪音、清单文档自身。
2. **A 类差异 > 0（不通过）**：存在 A 类条目未提交或误分类——须查明原因（漏 add / 归属变更 / 分清单与实测漂移），按 §1 前置裁断口径补正后重跑；**不得以「预期已提交」代替 `git status` 实测证据**。
3. **基线漂移**：若某仓 HEAD/分支与 §2.5 表不一致（例如 OpenBase HEAD 由 `cdfbd5b` 前进），须如实登记漂移并复核是否影响 A/B/C 归类，回写本表与总清单。
4. **残余条目须可解释**：每一条残余条目都应能归入「B 类 / C 类 / 清单文档自身」三类之一；无法解释者登记为遗留（§8）并交会签评审。

---

## §5 hash 回填表

> **纪律**：提交后将**实际 commit hash** 回填至下表与对应台账/卡尾；**禁伪造 hash**，受限（沙箱无写权限/未执行）则**如实登记 `PENDING`** 并注明原因与归属（立项方案 §4 S7-T7-1）。

| 仓 | 提交 hash 清单（待填） | 回填位置 | 回填完成（待填） | 备注 |
|----|------|------|:---:|------|
| OpenMemory | 批 0：____；批 1：____；批 2：____；批 3：____（4 个） | 《OpenBase-数据隔离实现任务卡》**v1.4.0 卡尾（S2 段执行摘要）** | 待填 | 4 个 commit hash + 批次结论；受限则登记 `PENDING` |
| OpenRAG | S3-B1：`9e93c1c`；S3-B2：`0bda158`；S3-B3：`f48ea08`；S3-B4：`5fafc0a`（4 个） | 《OpenBase-数据隔离实现任务卡》**v1.5.0 卡尾（S3 段执行摘要）** | **已回填**（2026-09-11） | 4 个 commit hash + 批次结论；另 `b809c04`（入仓后修复）/ `a2eb92b`（登记回填） |
| OpenLLM | 批 1：____；批 2：____；批 3：____；批 4：____；批 5：____；批 6：____（6 个，或合批 5 个） | 《OpenBase-数据隔离实现任务卡》**v1.6.0 卡尾（S4 段执行摘要）** | 待填 | 6 个（合批则 5 个）+ 批次结论；受限则登记 `PENDING` |
| DPS | S5-B1：____；S5-B2：____；S5-B3：____；S5-B4：____（4 个） | **DPS JT 台账** + 任务卡 **S5 卡尾**（v1.7.0 S5 段执行摘要） | 待填 | 4 个 commit hash + 批次结论；受限则登记 `PENDING` |
| OpenBase（本仓） | 无联调产物 hash（本次联调 OpenBase A 类 = 0） | 会签结论（可追加至总清单 §4 或任务卡卡尾） | 待填 | 仅登记会签结论 |

> **回填完成汇总（待填）**：四仓 hash 全部回填 □ 是 / □ 否（`PENDING` ____ 项）；回填人 ______；日期 ______。

---

## §6 跨仓会签记录表

> 按《清点总清单》§4.1 **会签五步流程**执行；每步留「结论 / 证据 / 会签人 / 日期」栏。会签完成是 S7 段门禁「跨仓会签完成」项（立项方案 §1.3）与 S7-T7-3 断言的直接证据。

| 步骤 | 内容 | 结论 | 证据 | 会签人 | 日期 |
|:---:|------|------|------|------|------|
| ① | **四仓入仓完成**：OpenMemory 4 批 / OpenRAG 4 批 / OpenLLM 6 批（可合 5）/ DPS 4 批，逐项显式 `git add` + `git commit` | 待填 | 各仓 `git log` 批次提交号（§2 表 hash 列）+ `git diff --cached --stat` 复查记录 | 待填 | 待填 |
| ② | **hash 回填**：四仓实际 hash 回填各自 JT 台账与任务卡卡尾（v1.4.0 / v1.5.0 / v1.6.0 / DPS JT 台账 + S5 卡尾） | 待填 | §5 hash 回填表 + 台账/卡尾回填截图或提交号 | 待填 | 待填 |
| ③ | **四仓勾稽 A 类差异 0**：以总清单 §1.1 为基准回读 `git status --porcelain -uall`，仅剩 B/C + 清单文档自身 | 待填 | §4 勾稽核对表 + 逐仓 `git status` 回读记录 | 待填 | 待填 |
| ④ | **跨系统卡完成情况评审**：K02 / K07 / K13 完成情况 + **接口一致性**——`X-Proxy-Source` / 四头（`X-User-ID`/`X-Tenant-ID`/`X-User-Role`/`X-Proxy-Source`）/ 角色互译 / 保留码 / 事件契约 | 待填 | 任务卡 K02/K07/K13 回写 + 各仓接口一致性核对表 + 事件契约锚点 `0713ec1` | 待填 | 待填 |
| ⑤ | **清单升版**：跨仓提交放行清单 **v1.0.8 → [Approved]**；联调产物清点核对总清单 **v1.0.5 → [Approved]**（遵循文档版本管理规范，回写修订历史） | 待填 | 两份清单升版登记 + 修订历史条目 | 待填 | 待填 |

> **会签结论（待填）**：跨仓会签 □ 通过 / □ 不通过；遗留非阻断项 ____ 项（见 §8）；会签主持 ______；日期 ______。

---

## §7 S7-T7 断言对照表

> 断言取自《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0》§3.3 S7-T7 与 §4；执行面 A = 沙箱可判定，A+B = 双面，B = 联调窗口/沙箱外必需。**B 面未真实执行项一律登记 `PENDING`，禁伪造**。

| 断言 ID | 通过标准 | 执行面 | 证据形态 | 证据路径（待填） | 结论（待填） |
|:---:|------|:---:|------|------|:---:|
| **S7-T7-1** | 四仓入仓完成，**实 hash 回填**各仓 JT 台账与任务卡卡尾（OpenMemory v1.4.0 / OpenRAG v1.5.0 / OpenLLM v1.6.0 / DPS JT 台账 + S5 卡尾）；**hash 一律不得伪造**（受限则如实登记） | B | 四仓 commit hash 清单 + 台账/卡尾回填记录 | §5 表 + 台账回填位（待填绝对路径） | 待填 |
| **S7-T7-2** | 四仓清单勾稽：以总清单 §1.1 为基准逐仓回读 `git status --porcelain -uall`，**A 类差异 = 0**（仅剩 B 类隔离 + C 类噪音 + 清单文档自身） | B | 逐仓 `git status --porcelain -uall` 回读记录 | §4.1 表 + 逐仓回读输出（待填） | 待填 |
| **S7-T7-3** | 跨仓会签记录形成（总清单 §4.1 五步流程），四仓 hash 汇总 + 跨系统卡（K02/K07/K13）完成情况与接口一致性评审 | A+B | 会签记录（五步结论/证据/会签人/日期） | §6 表（待填绝对路径或提交号） | 待填 |
| **S7-T7-4** | 放行清单（v1.0.8 → [Approved]）与清点总清单（v1.0.5 → [Approved]）升版登记，遵循文档版本管理规范 | A | 两份清单升版后的修订历史条目 | `doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md`、`doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md`（待填） | 待填 |

> **S7-T7 小结（待填）**：断言 4 条中，通过 ____ 条 / `PENDING` ____ 条；证据索引汇总 ______。

---

## §8 遗留与 PENDING 登记

> 本表登记**本次未能入仓项、受限项、非沙箱待复核项**；对齐 S5/S6 挂起口径范式——**非阻断项 PENDING 登记不阻断会签/批准**，但须如实记录归属与复核动作（立项方案 §3.2 Q-S7-2）。

### 8.1 入仓遗留与受限项

| # | 仓/归属 | 事项 | 类型（未入仓 / 受限 / 待裁定） | 处置/复核动作 | 责任方 | 状态 |
|:---:|------|------|:---:|------|------|:---:|
| 1 | 四仓 | 未能在沙箱内执行的入仓/回填/勾稽（沙箱仅允许操作 OpenBase 仓） | 受限 | 用户在沙箱外执行，结果回填 §2/§4/§5 | 各子系统 + 用户 | PENDING（待填） |
| 2 | OpenMemory | B 类 197 项（v7.x 自身在途）未入联调批 | 已隔离 | 独立基线/版本批处理，不阻断本次放行 | OpenMemory | 待填 |
| 3 | OpenLLM | B 类 need-star 13 项未入联调批 | 已隔离 | 独立分支 `feature/need-star-orchestration` + 独立段门禁 | OpenLLM | 待填 |
| 4 | DPS | B 类 v2.9.0 三份文档未入联调批 | 已隔离 | 独立批次 `docs(v2.9.0): …` | DPS | 待填 |
| 5 | 各仓 | 卫生债（`.pyc` 211 项 / `.gitignore` 无效规则 / 敏感文件历史核查） | 待裁定 | 独立卫生批（`git rm -r --cached` + `.gitignore` 增补），不在本次执行 | 各子系统 | 待填 |
| 6 | （其他） | 待填 | 待填 | 待填 | 待填 | 待填 |

### 8.2 非沙箱待复核项 B1~B6（S6 移交，Q-S7-2）

| 编号 | 事项 | 归属/复核动作 | 状态 |
|:---:|------|------|:---:|
| B1 | UI-E2E 关键页 PASS（Playwright 浏览器级 9 关键页，需真实通道 + 运行态） | 非沙箱环境复核，回填 `doc/test/evidence/s6/**` 后关闭 | PENDING / 待填 |
| B2 | L3-2 真实受信通道双签 | 非沙箱环境复核（`doc/test/evidence/s6/l3-2-smoke.json`） | PENDING / 待填 |
| B3 | 真实双租户数据面 | 非沙箱复核项 | PENDING / 待填 |
| B4 | 真实 IdP 回调与吊销 | 非沙箱复核项 | PENDING / 待填 |
| B5 | 四仓 `frontend/` 物理改造与 CI 收敛 | **归各子系统对话 / S7** 按 Q-S6-D7 复核（需 PG-Redis / IdP / 真实通道 / nginx 就绪） | PENDING / 待填 |
| B6 | nginx `/ui/` 发布回滚实测 | 非沙箱复核项 | PENDING / 待填 |

### 8.3 四仓段级真实通道双签挂起登记

| 段 | 挂起项 | 归属 | 状态 |
|:---:|------|------|:---:|
| S2 | OpenMemory L3-2 记忆数据面真实 HTTP 双签（事件通道，不纳入 S7 主备矩阵） | 部署/联调窗口 + S7 | PENDING / 待填 |
| S3 | OpenRAG Pull 真实 HTTP 双签（Q-RG-7）+ PG/Redis 实跑补验 | 部署/联调窗口 | PENDING / 待填 |
| S4 | OpenLLM 真实 HTTP 双签（写路径等价 / K14 幂等 / L2-1 演练 / L2-2 终验随 S7） | 部署/联调窗口 + S7 | PENDING / 待填 |
| S5 | DPS Pull 真实 HTTP 双签（Q-DPS-5） | 部署/联调窗口 | PENDING / 待填 |

> **遗留总览（待填）**：非阻断遗留合计 ____ 项；阻断项 ____ 项（如存在须回溯 S7 段门禁）；登记人 ______；日期 ______。

---

> **文档结束**。本模板为 S7 段 S7-T7「跨仓入仓核验与会签」的**可填报执行模板**（[Draft] v1.0.0）；批次与计数以各仓分清单为准（OpenMemory 4 批 A70 / OpenRAG 4 批 A67 / OpenLLM 6 批 A75 / DPS 4 批 A52），流程以《清点总清单》§4.1 五步为准，断言以立项方案 §4 S7-T7-1~4 为准。**四仓入仓、hash 回填与会签完成前不得提前宣布放行；未执行项一律 PENDING 登记，禁止伪造 hash 与通过。**
