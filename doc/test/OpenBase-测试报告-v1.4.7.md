# OpenBase 测试报告 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓） |
| 文档版本 | v1.5.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Test |
| 创建日期 | 2026-09-19 |
| 存放 | doc/test/ |
| 测试范围 | **BL-147-05 端到端串联与接入验收**（专项验收口径，见 §1 偏差声明） |
| **测试结论** | **通过（限定口径：BL-147-05 专项验收）**——依据 **§7.6 复测 4（2026-09-20 14:39:33~14:46:56 `-PerFamily 10` 强化重跑＝最终权威口径，40 次抽样；五方服务 + OIDC IdP，经编排器启动；第一轮 14:20:16~14:28:41 的 24 次抽样记为中间态、已按同口径重跑取代）**：① 串联一致性（**业务路径**）**22 / 命中 22 / 未命中 0 / 命中率 1.0（100%）**（探活/豁免路径 18 次另列，命中 11，按契约不计入串联判据）；② 四仓应用日志行 JSONL 契约合法率 **100%**（dps 391 / openrag 348 / openmemory 422 / openllm 2786；`status_code` 全为数字，非数字计数 0）；③ `source=repo_log` + `module` 可检索四仓覆盖 **4/4**（dps 391 / rag 493 / memory 422 / llm 5200）且 40 个 `request_id` 反查命中（其中 7 个 0 命中，均属探活/豁免样本）；④ 校验器**退出码 0（= 通过）**；⑤ 本仓 `ruff` 0 错误、全量回归 **passed=996 / failed=0 / skipped=4**；⑥ 缺陷 **5/5 全闭环**（DEF-BE-147-001~005）。<br>**限定声明（不得超范围引用）**：本结论**仅为 BL-147-05 专项验收结论**；v1.4.7 **完整 Step 4 门禁结论**须与 **Step 3 门禁材料（`code-logic-review` / Stage3 阶段审计，已于 2026-09-20 产出）**、**本报告**、**《OpenBase-测试回溯对比审计报告-v1.4.7》**三者齐备后判定；v1.4.6 Phase 6 门禁（M10/M11）登记与 TD-新增-020「已偿还」登记**须经人工批准**；**TT-147-009（四仓 R-384 专项单测独立复跑）已于 2026-09-20 补跑通过——四仓合计 36/36 passed（DPS 10 / OpenLLM 7 / OpenMemory 12 / OpenRAG 7，与四仓回执基线逐仓逐例一致）**，见 §7.7 与证据 `doc/test/evidence/v147/bl147-05-tt009-four-repo-rerun.txt`；**《测试计划》§2.1 四项判据至此全部达成，本轮 10 条用例全部执行、无未执行项**<br>**Step 4 收口状态（v1.5.0）**：Step 3 门禁材料（静态质量检查记录 / 代码逻辑审查记录 / Stage3 阶段审计报告）与 Step 4 材料（本报告 / 测试回溯对比审计报告 v1.0.2 / Stage4 阶段审计报告 v1.0.0）**均已产出** |

**上游依据**：《OpenBase-测试计划-v1.4.7》《OpenBase-测试用例-v1.4.7》；《OpenBase-R384四仓施工派单-v1.0.0》§8；《OpenBase-DevLogReport-v1.4.7》§5.1（判据口径裁定）；《OpenBase-问题跟踪记录-v1.4.7》。

---

## 1. 入场检查与偏差声明

| 门禁项 | 实际 | 判定 |
|--------|------|:----:|
| DevLogReport（Step 3 移交） | 《OpenBase-DevLogReport-v1.4.7》v1.1.0 存在 | ✅ |
| `code-logic-review` / Stage3 开发审计 | **已产出（2026-09-20 补齐入库）**：`doc/development/OpenBase-静态质量检查记录-v1.4.7.md`、`doc/development/OpenBase-代码逻辑审查记录-v1.4.7.md`、`doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.7.md`（v1.0.0） | ✅（首轮入场时的偏差已消除） |
| 环境就绪 | 五方服务 + OIDC IdP + 前端全部健康；共享 PG/Redis/Qdrant 可达；四仓 R-384 装配点就位 | ✅ |
| 自测证据抽查（4.0b） | 抽中 ① `tests/test_r384_repo_log_naming.py`（13 例）② `-Action namecheck` 三段实测；测试侧**独立重跑**，与开发记录一致 | ✅ |

**环境与工具坑（实测踩坑，供后续复用）**：

| # | 现象 | 根因 | 处置 |
|:-:|------|------|------|
| 1 | 新增的 `.ps1`（含中文）执行报 `ParserError UnexpectedToken` | Windows PowerShell 5 对**无 BOM 的 UTF-8** 脚本按 ANSI 解析 → 中文与引号错位 | 脚本须以 **UTF-8 BOM** 保存（本次已改） |
| 2 | 验收脚本在调用 Python 校验器时中断（校验器 stderr 有适配器 WARN） | `$ErrorActionPreference='Stop'` 下 PS5 将 native stderr 视为终止性错误 | 调用处临时降为 `Continue`（本次已改） |
| 3 | OpenMemory 首轮健康检查超时（300s）后被编排器记为「超时」 | complete 模式预载模型实测 ≈ 410s | 本轮改用 `-HealthTimeout 600`，健康检查通过 |

## 2. 测试执行结果（TT-ID）

> **版本说明**：下表为**首轮（2026-09-19）执行结果，历史留存供追溯**；其 TT-147-004/005「不通过」已被后续修复与重跑取代，**本轮（2026-09-20）全量重跑结果见 §7.6**（TT-147-004/005 均已通过）。

| TT-ID | 用例 | 命令/方式 | 结果 | 证据 |
|-------|------|-----------|:----:|------|
| TT-147-001 | 环境就绪核验 | `bl147_05_e2e_check.ps1` §环境段 | **通过**（PG/Redis/Qdrant 可达；四仓装配点 2/2/2/3/3；五方健康） | `bl147-05-env.txt` |
| TT-147-002 | 采集命名契约实测 | `-Action namecheck` | **通过**（① 可见 16/不可见 0；② 在盘 可见/不可见=17/0；③ 归档自检 8/8） | `bl147-05-namecheck.txt` |
| TT-147-003 | 网关串联抽样（≥20） | 4 族 × 6 = **24 次真实请求** | **通过（抽样成立）**：24/24 HTTP 200 且均带回 `X-Request-Id`（`req-{12hex}`） | `bl147-05-sampling.json` |
| TT-147-004 | 应用日志行 JSONL 契约 | `bl147_05_verify_chain.py` | **不通过**：DPS/OpenLLM/OpenMemory 合法率 100%，但 **OpenRAG 应用日志行为 0**（其请求日志为 structlog 控制台文本） | `bl147-05-jsonl-contract.json` |
| TT-147-005 | 串联一致性（核心 P0） | 同上（逐条检索应用日志行并比对取值） | **不通过**：命中 **8/24 = 33.3%**（判据要求 100%） | `bl147-05-chain-consistency.json` |
| TT-147-006 | 日志中心四仓可检索 | `repo_log` + `module` 维度 + `request_id` 反查 | **通过**：dps 103 / rag 60 / memory 112 / llm 1189（合计 1464），四仓覆盖 4/4 | `bl147-05-retrieval.json` |
| TT-147-007 | 兜底健壮（`request_id="-"`） | 采集行统计 | **通过**：无上下文路径输出 `"-"`，无异常与中断（DPS 97 / OpenLLM 568 / OpenMemory 100 行） | `bl147-05-jsonl-contract.json` |
| TT-147-008 | 本仓全量回归 + 静态检查 | `ruff` + `pytest`（代码自 `e6452b1` 起未变更，复用 Step 3 证据） | **通过**：`ruff` 0 错误；`pytest` 992 收集 / 988 通过 / 4 环境性失败（asyncpg 连接）/ 4 跳过 / errors=0 | `step3-regression-junit.xml`、`step3-stale-test-ab-20260919.txt` |
| TT-147-009 | 四仓 R-384 专项单测独立复跑 | 逐仓 pytest | **未执行（首轮口径，历史留存）**：TT-147-005 已判定不通过并按流程回退 Step 3，四仓复跑与重测一并进行（说明见 §5 跳过项）；**2026-09-20 补跑通过（36/36，见 §7.7）** | `bl147-05-tt009-four-repo-rerun.txt` |
| TT-147-010 | 采集抽样披露 | 同上 | **通过（披露完整）**：非应用行（框架自身输出）占比如实统计，未静默降级 | `bl147-05-jsonl-contract.json` |

### 2.1 串联一致性逐仓归因（核心证据）

对 24 个网关 `X-Request-Id` 在四仓采集目录做**原文命中**检索（不受行格式影响）：

| 抽样族 | dps | openllm | openmemory | openrag |
|--------|:---:|:-------:|:----------:|:-------:|
| dps（6 次） | **0/6** | 0/6 | 0/6 | 0/6 |
| rag（6 次） | 0/6 | 0/6 | 0/6 | **0/6** |
| memory（6 次） | 0/6 | 0/6 | **3/6**（仅 `/health` 路径命中） | 0/6 |
| llm（6 次） | 0/6 | **6/6** | 0/6 | 0/6 |

- **OpenLLM 6/6 命中** → 证明**网关侧注入正确**（出站 `X-Request-Id` 与响应头一致），问题不在本仓网关；
- **DPS 0/6**：其采集日志仅含**本地生成** id（如 `req-3c03a15df62f`、`req-6e10ee726a30`），未见网关 id；
- **OpenMemory 3/6**：`/api/v1/memory-proxy/health` 透传成功，业务路径 `/api/v1/memory-proxy/monitor`（上游 `/api/v1/monitor`）未命中，日志中为本地生成 id（如 `req-acdef423badb`）；
- **OpenRAG 0/6**：日志中为本地生成 id（如 `req-ee563e4877e0`），且其请求日志为**纯文本**形态：`2026-09-19T14:10:31.879814Z [info     ] request_completed duration_ms=175.455 method=GET path=/api/v1/system/health request_id=req-ee563e4877e0 status_code=200`（structlog 控制台渲染器，未启用 `JSONRenderer`）。

## 3. 缺陷与闭环

| 缺陷 ID | 级别 | 归属 | 问题 | 证据 | 状态 |
|---------|:----:|------|------|------|:----:|
| **DEF-BE-147-001** | **P0** | DPS 仓（跨仓） | 未透传网关 `X-Request-Id`：6/6 抽样原文未命中，仅记录本地生成 id | `bl147-05-chain-consistency.json`、§2.1 矩阵 | 待修复（回退 Step 3） |
| **DEF-BE-147-002** | **P0** | OpenRAG 仓（跨仓） | ① 未透传 `X-Request-Id`（6/6 未命中）② 请求日志非 JSONL（structlog 控制台文本）→ 采集文件应用日志行为 **0**，JSONL 契约不满足 | 同上 + `bl147-05-jsonl-contract.json` | 待修复（回退 Step 3） |
| **DEF-BE-147-003** | **P1** | OpenMemory 仓 / memory-proxy（待定位） | 部分路径透传：`/health` 3/3 命中，业务路径 `/api/v1/monitor` 0/3 命中 | §2.1 矩阵 | 待定位与修复 |
| **DEF-BE-147-004** | P2（工具链） | 本仓 | 验收脚本首轮 `ParserError` / native stderr 中断（详见 §1 环境坑） | 本轮修复记录 | **已闭环**（脚本已修正，本轮复跑通过） |

> **版本说明**：上表「待修复 / 待定位」为首轮（2026-09-19）登记状态，**历史留存**；DEF-BE-147-001/002/003 的修复与复测见 §7.1/§7.2/§7.4，DEF-BE-147-005 见 §7.5，**五项缺陷（DEF-BE-147-001~005）现已全部闭环**（闭环依据同步登记于《OpenBase-问题跟踪记录-v1.4.7》§1）。

> 按《testing-stage-execution》：**P0/P1 未关闭不得进入下一阶段**，须回退 Step 3 修复 → 更新 DevLogReport → 重跑相关用例（必要时全量）。跨仓缺陷（001/002）须以**跨仓派单项**形式分发四仓。

## 4. 覆盖率

| 项 | 结论 |
|----|------|
| 白盒覆盖率 | 本版本本仓新增/修改代码：`scripts/verify_repo_log_naming.py`（新增，13 例单测覆盖判据与反例）、`openbase/modules/logs/repository.py`（仅注释 + 公开常量导出，无行为变更）；未单独出覆盖率报告（BL-147-04 无业务逻辑新增） |
| 黑盒覆盖差异 | BL-147-05 为**跨仓端到端**验收，其覆盖对象为四仓运行态行为（本仓白盒覆盖率不适用），已以 24 次真实请求 + 四仓原文命中矩阵覆盖（**首轮口径，历史留存**；最终权威口径为 `-PerFamily 10` 的 **40 次抽样（4 族 × 10）**，见 §7.6） |

## 5. 测试跳过项说明

| 跳过项 | 原因 | 影响 | 补测计划 | 批准 |
|--------|------|------|---------|------|
| TT-147-009 四仓 R-384 专项单测独立复跑 | **已闭合（2026-09-20 补跑执行）**：原跳过原因（首轮 TT-147-005 不通过 → 按门禁回退 Step 3；2026-09-20 全量重跑轮验收脚本不含该动作）已消除——本轮按本节「补测计划」**第 ① 方案（逐仓补跑专项单测文件）**执行 | 无（原「覆盖缺口」已闭合）：本轮取得四仓专项单测**独立复跑证据**，并通过四仓回执基线比对 | 已执行：2026-09-20 逐仓复跑（DPS **10** / OpenLLM **7** / OpenMemory **12** / OpenRAG **7** ＝ **36/36 passed**、失败 0，与四仓回执基线 10/7/12/7 **逐仓逐例一致**）；OpenLLM 因沙箱下 `tests/conftest.py` 前置依赖（pgAdmin py313 组合的 `jwt`/`cryptography` DLL 冲突）不可用，按 pytest 官方选项 `--noconftest` 执行（该用例不依赖 `conftest` fixture，已回读源码核验），标准口径失败原文同文件留证。详见 §7.7 | **已补跑留证；Step 4 放行仍须人工批准**（见《OpenBase-测试回溯对比审计报告-v1.4.7》v1.0.2 §4/§9） |
| v1.4.7 T3a 全页面巡检 / T4 UAT | 本版本无前端功能改动；BL-147-04 为采集侧脚本 | 无 | 沿用 v1.4.6 前端走查结论；若后续引入前端改动再补 | 《测试计划》§2.3 范围外声明 |
| 性能/压测 | 无性能面变更 | 无 | 不需要 | 同上 |

## 6. 遗留风险

| # | 风险 | 级别 | 说明 |
|:-:|------|:----:|------|
| 1 | 四仓「受信来源」判定口径不一致导致透传行为分化 | **P0** | 实测 4 仓表现三种（全通 / 部分通 / 全不通）→ 与《施工派单》§3 核实项③「四仓受信来源判定口径对齐」的落地程度相关，需四仓按同一口径复核 |
| 2 | OpenRAG 结构化未生效（`json_format` 未开） | **P0** | 其请求日志为控制台文本；即使透传修复，JSONL 契约仍不满足 |
| 3 | v1.4.6 Phase 6 门禁（M10/M11）登记未闭合 | **P0** | 首轮口径：BL-147-05 未通过 → TD-新增-020 仍不可置「已偿还」。**2026-09-20 更新**：本轮全量重跑 BL-147-05 **验收通过**（§7.6）→ 门禁与 TD-新增-020 偿还的**条件已满足**；但登记**须经人工批准**，且须与 **Step 3 门禁材料**、**本报告**、**《OpenBase-测试回溯对比审计报告-v1.4.7》**三者齐备后判定（**仍不得径行置为「已偿还」**） |
| 4 | v1.4.7 Step 3 / Step 4 审计材料 | — | **已闭合（2026-09-20）**：Step 3 材料（`doc/development/OpenBase-静态质量检查记录-v1.4.7.md`、`doc/development/OpenBase-代码逻辑审查记录-v1.4.7.md`、`doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.7.md`）与 Step 4 材料（本报告 v1.5.0、`doc/audit/verification/OpenBase-测试回溯对比审计报告-v1.4.7.md` v1.0.2、`doc/audit/review/OpenBase-阶段审计报告-Stage4-v1.4.7.md`）**均已产出**；首轮「Step 3 材料缺失」的入场偏差已消除 |

## 7. 结论（首轮，2026-09-19）

> **留存声明**：本节为**首轮结论原文，作为历史记录保留，不作删改**；其内容已被后续修复与多轮复测（§7.1~§7.6）取代。**最终结论以本报告元信息「测试结论」与 §7.6（2026-09-20 全量重跑）为准。**

1. **BL-147-05 判定：不通过**。可检索性（4/4）与本仓回归通过；**串联一致性 8/24（33.3%）** 与 **OpenRAG JSONL 契约**两项 P0 判据未达成。
2. **处置**：按门禁回退 **Step 3**（跨仓缺陷以派单项分发 DPS / OpenRAG / OpenMemory），修复后重跑 TT-147-003~TT-147-009；本仓侧无需代码修复（网关注入已由 OpenLLM 6/6 命中证伪）。
3. **不得**据此报告宣称 v1.4.6 Phase 6 门禁或 M10/M11 达成，也不得将 TD-新增-020 置为「已偿还」。

## 7. BL-147-05 修复与复测记录（2026-09-19，v1.1.0 增补）

### 7.1 本轮修复（Step 3 回退后，**未派单、直接修复**）

| 缺陷 | 修复位置 | 修复内容 |
|------|---------|---------|
| DEF-BE-147-001（DPS） | **本仓** `scripts/service-orchestrator.ps1`（dps `Env`） | 注入 `TRUSTED_PROXY_SOURCES='openbase-dps-proxy,openbase-orchestrator'`（DPS 侧无需改码；其 `src/config.py:194` 已给出该取值示例） |
| DEF-BE-147-002（OpenRAG） | **本仓** 同上（openrag `Env`） | ① 注入 `OPENRAG_LOG_JSON='true'`（OpenRAG 已内置该开关，默认 False）；② 注入 `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES='["openbase-rag-proxy"]'`（**必须 JSON 数组形态**：pydantic-settings 对 `list[str]` 字段先按 JSON 解码 EnvSettingsSource 值，逗号串会导致 `SettingsError` 且服务启动即崩 → 首轮实测 rag-proxy 全 502） |
| 护栏 | 本仓 `tests/test_bl147_trust_env_wiring.py`（新增 3 例，TDD：先 RED 后 GREEN） | 断言编排器为 dps/openrag 注入上述键，且白名单值与 `protocol_headers.constants.PROXY_SOURCE_*`（网关来源单一事实源）一致 |
| 判据细化 | 本仓 `scripts/bl147_05_verify_chain.py` | 按《施工派单》§4 兜底条款，**探活/豁免路径**（`*/health`、`openapi.json`）契约上不可能携带 request_id → 单列 `probe_totals`、**不计入串联判据**（避免把契约豁免误记为缺陷）；业务路径判据不变（100%） |

### 7.2 复测结果（40 次真实请求：4 族 × 10；服务全健康，40/40 带回 `X-Request-Id`）

| 判据 | 目标 | 首轮（未修复） | **复测（修复后）** | 判定 |
|------|------|:-------------:|:-----------------:|:----:|
| 串联一致性（**业务路径**） | 100% | 8/24（33.3%，未区分探活） | **17/22 = 77.3%** | 未达标（受 DEF-003 阻塞） |
| └ 逐族（业务路径） | — | — | **dps 7/7 ✅、rag 5/5 ✅、llm 5/5 ✅、memory 0/5 ❌** | — |
| └ 探活/豁免路径（单列） | — | — | 18 次 / 命中 11（不计入判据） | 证据性 |
| 应用日志行 JSONL 契约 | 100% 合法 | openrag 应用行 0 | **dps 217 / rag 41 / memory 240 / llm 1473，合法率均 100%**，`status_code` 非数字 0 | ✅ |
| 四仓可检索（`repo_log`+`module`） | 4/4 | 4/4 | 4/4 | ✅ |
| 本仓回归 + 静态检查 | 无新增失败 | ✅ | ✅（`ruff` 0；`pytest` 992/988/4 环境性） | ✅ |

**结论**：DPS（DEF-001）与 OpenRAG（DEF-002）两项缺陷**已修复并验证闭环**（OpenRAG 同时达成 JSONL 与透传）；整体仍**不通过**，剩余阻塞为：

| 缺陷 ID | 级别 | 归属 | 现状 |
|---------|:----:|------|------|
| DEF-BE-147-003 | P1 | OpenMemory（+ 边界待定位） | 仍开放：业务路径 `/api/v1/memory-proxy/monitor` 0/5 命中（探活 5/5 命中）；**proxy 侧 `/monitor` 与 `/health` 走同一 `_proxy_json` 装配点（本仓无差异）→ 差异在 OpenMemory 侧** |
| **DEF-BE-147-005**（新） | **P1** | 本仓/OpenRAG 边界 | **本轮修复引入的副作用**：启用 M2 后 `rag-proxy/collections` 由 200 → **400**（响应 171 B、耗时 5 ms；OpenRAG 仅记 `api_key_authed` + `request_completed 400`，无拒绝原因日志）。已排除网关注入缺失（DPS 用同一装配点且业务全通）；判据证据：首轮 `bl147-05-sampling.json`（提交 `bb78e77`）rag `/collections` = **200**，复测 = **400**。定向复现未完成（OpenRAG 冷启需 >60s，本次 60s 超时窗口内未监听） |

### 7.3 复测证据

`doc/test/evidence/v147/`：`bl147-05-env.txt`（环境 + 40 次抽样逐条）、`bl147-05-sampling.json`、`bl147-05-chain-consistency.json`（含 `totals` 业务判据与 `probe_totals` 探活单列）、`bl147-05-jsonl-contract.json`、`bl147-05-retrieval.json`、`bl147-05-namecheck.txt`。

### 7.4 复测 2（2026-09-20）：OpenMemory 修复后（DEF-BE-147-003）

**修复**：编排器为 `openmemory` 注入 `OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES='["openbase-memory-proxy"]'`（本仓单点，未改 OpenMemory 代码；护栏用例扩至 4 例）。

**根因（本次定位）**：`/health` 等探针路径在 OpenMemory `IdentityTrustConfig.whitelist_paths` 内 → 身份门**直接放行、不裁决 `request_id`**，由 `StructuredLogMiddleware` 回退复用合规入站头 → **表现为"探活路径命中"的假象**；业务路径（`/api/v1/monitor`）走门裁决，受信白名单为空 → `allow_reuse=False` → 忽略网关 id 并本地重生成（`identity_gate.py:104-121`、`structured_log.py:119-125`）。

| 判据 | 目标 | 复测 1（DPS/OpenRAG 修复后） | **复测 2（+OpenMemory 修复）** | 判定 |
|------|------|:---------------------------:|:-----------------------------:|:----:|
| 串联一致性（**业务路径**） | 100% | 17/22 = 77.3% | **22/22 = 100%** | **✅ 达标** |
| └ 逐族 | — | dps 7/7、rag 5/5、llm 5/5、memory 0/5 | **dps 7/7、rag 5/5、memory 5/5、llm 5/5** | ✅ |
| 探活/豁免路径（单列） | — | 11/18 | **18/18**（同样全部命中） | 证据性 |
| 应用日志行 JSONL 契约 | 100% 合法 | 100%（四仓） | **100%**（dps 277 / rag 87 / memory 302 / llm 1936；`status_code` 非数字 0） | ✅ |
| 四仓可检索（`repo_log`+`module`） | 4/4 | 4/4 | **4/4**（dps 277 / rag 166 / memory 302 / llm 3610），`request_id` 反查命中 | ✅ |
| 本仓回归 + 静态检查 | 无新增失败 | ✅ | ✅（`ruff` 0；4 例护栏全绿） | ✅ |

**结论**：**BL-147-05 的串联一致性核心判据已达成 100%**；DEF-BE-147-001/002/003 三项缺陷全部修复并复测通过（修复方式均为**本仓编排器 env 注入**，未改他仓代码）。

**仍开放（本轮不在范围内）**：**DEF-BE-147-005（P1）** —— 复测 2 中 `rag-proxy/collections` 仍为 **400**（其响应 `request_id` 与网关一致，说明**串联正常、功能异常**，属 OpenRAG M2 模式下的校验副作用）。因此本报告结论仍为**不通过（第 2 项门禁未闭合）**：需 DEF-005 闭环后重跑 TT-147-003~TT-147-009 并补齐测试回溯审计。

### 7.5 复测 3（2026-09-20）：DEF-BE-147-005 闭环（定向复测）

> **范围声明**：本节为 **DEF-BE-147-005 的定向复测**（最小服务集 openrag + openbase）。**全量重跑**（TT-147-003~009，五方服务 + ≥20 次抽样）与**报告总结论刷新**见 §7.6（待执行）；本节不改变 §1/§7 的总结论。

**修复内容**（本仓单点，未改他仓代码）：

| 项 | 位置 | 内容 |
|----|------|------|
| 新增显式开关 | `openbase/settings.py` | `rag_inject_identity_headers: bool = True`（默认保持既有四维身份透传；`False`＝不注入身份头） |
| 策略消费 | `openbase/modules/rag_proxy/__init__.py` | 关闭时以 `user_ctx=None` 走同一装配点（仍产出 `X-Proxy-Source` + `X-Request-Id`） |
| 联调口径声明 | `scripts/service-orchestrator.ps1`（openbase `Env`） | `OPENBASE_RAG_INJECT_IDENTITY_HEADERS = 'false'`（显式声明，非静默降级） |
| 护栏 | `tests/test_rag_proxy_identity_policy.py`（新增 3 例）、`tests/test_bl147_trust_env_wiring.py`（+1 例） | 默认注入 / 关闭不注入 / 关闭仍携带 request_id / 编排器声明 |

**决策证据（方案 A/B 实测，`doc/test/evidence/v147/def005-multiprobe-20260920.json`）**：

| 方案 | 直连 OpenRAG 状态 | 数据可见性 | 采纳 |
|:----:|:----------------:|-----------|:----:|
| A（非保留租户码 `openbase`/`openbase-demo`） | 200 | **`items=[]`（租户隔离致既有知识库不可见）** | ✗ |
| **B（不注入身份头）** | **200** | **`items=12` 完整可见** | **✓** |

**复测结果（2026-09-20 13:11，`def005-gateway-retest-20260920.json`）**：

| 判据 | 目标 | 修复前 | **定向复测（修复后）** | 判定 |
|------|------|:------:|:---------------------:|:----:|
| 经网关 `GET /api/v1/rag-proxy/collections` | 200 | **400**（`BIZ_RESERVED_TENANT_CODE_COLLISION`） | **200** | **✅** |
| 数据完整可见 | `items > 0` | —（400 无数据） | **`items=12`、`total=12`** | **✅** |
| 跨系统串联（同一请求内） | 响应头 `X-Request-Id` == 上游应用日志行 `request_id` | —（400 时亦一致） | **一致**（`req-2ebfcfc04552`：网关响应头 ↔ OpenRAG `request_started`/`api_key_authed`/`request_completed(status_code=200)` 三行同值） | **✅** |
| 非 2xx 响应体完整性（口径复核） | 非空 envelope | 曾记「空体」 | **400 + 190 字节完整 envelope**（`PARAM_400` + `detail` + `request_id`）→ 证伪「空体」假阳性 | ✅ |

**证据口径纠错（本轮同步）**：原 `def005-rag400-probe-20260920.md` §4 派生发现「400 响应体为空 → 可排障性缺陷」经**原始 socket + httpx** 双口径复核判定为 **PowerShell 5.1 测量假阳性**（上游 400 实发 385 字节完整 envelope），已**撤回**并把证据文档升 **v1.1.0**（依据《测试计划-v1.4.7》§2.4 四口径规则）。

**本仓回归与静态检查（增量 2）**：`ruff` **0 错误**；新增/受影响用例 **41 passed**（`test_rag_proxy_identity_policy.py` 3 + `test_bl147_trust_env_wiring.py` 4 + `test_proxy_outbound_matrix.py` + `test_rag_proxy.py`）；全量回归见《DevLogReport-v1.4.7》§4.5。

### 7.6 复测 4（2026-09-20 全量重跑：BL-147-05 通过）

> **口径**：本节为 **BL-147-05 端到端串联与接入验收的全量重跑**（覆盖 TT-147-001~008、010；**TT-147-009 已于 2026-09-20 补跑通过，见 §7.7**），服务启动方式唯一（编排器，未旁路起停）；**最终权威口径为 `-PerFamily 10` 强化重跑轮（2026-09-20 14:39:33~14:46:56，每族 10 次＝40 次抽样）**——第一轮 `-PerFamily 6`（2026-09-20 14:20:16~14:28:41，每族 6 次＝24 次抽样）因业务路径样本 13 < 20（审计观察项 O-1）记为**中间态**，已按同口径重跑强化并取代；证据取自 `doc/test/evidence/v147/`（本轮 2026-09-20 14:3x~14:4x 刷新）与 `logs/v147-bl147-05-rerun-perfamily10.txt`（第一轮日志 `logs/v147-bl147-05-rerun.txt` 为中间态，仅作历史引用）。

**执行概况**

| 项 | 内容 |
|----|------|
| 执行时段 | **2026-09-20 14:39:33 ~ 14:46:56**（`-PerFamily 10` 强化重跑＝最终权威口径，40 次抽样；校验器完成于 14:46:56，`E2E10_DONE exit=0`）；第一轮中间态为 14:20:16 ~ 14:28:41（`-PerFamily 6`，24 次抽样，校验器完成于 14:28:41） |
| 编排入口 | `scripts/service-orchestrator.ps1`（单一事实源） |
| 服务集 | 五方服务 + OIDC IdP：openllm 8001 / openrag 8010 / openmemory 8020 / oidc-idp 8090 / dps 8030 / openbase 8000（+ frontend 5173）**全部健康**（OpenMemory complete 模式健康检查 ≈125 s，超时窗口 600 s） |
| 共享基础设施 | PG `192.168.0.151:5432` / Redis `192.168.0.151:6380` / Qdrant `192.168.0.151:6333` **均可达** |
| 四仓 R-384 装配点（工作树） | DPS `app.py←setup_dps_logging`=2；OpenLLM `main.py←setup_openllm_logging`=2；OpenMemory `server.py←configure_logging`=2；OpenRAG `main.py←LoggingMiddleware`=3、`logging.py←X-Request-Id`=3 |
| 抽样规模 | **40 次真实请求（4 族 × 10）**，**40/40 均带回 `X-Request-Id`**（`req-{12hex}`）；第一轮中间态为 24 次（4 族 × 6）、24/24 带回 |
| 校验器退出码 | **0（0 = 通过，1 = 未通过）** |

**判据逐项结果（对照《测试计划》§2.1）**

| # | 判据 | 目标 | 本轮实测 | 判定 |
|:-:|------|------|----------|:----:|
| 1 | 串联一致性（**业务路径**） | 100% 命中且取值逐字相等 | **22 / 命中 22 / 未命中 0 / 命中率 1.0（100%）**；逐族 dps 7/7、rag 5/5、memory 5/5、llm 5/5 | **通过** |
| 1b | 探活/豁免路径（单列，**不计入判据**） | — | 18 次（命中 11，其余按 §4 兜底条款输出 `-`） | 证据性 |
| 2 | 四仓可检索（`source=repo_log` + `module`） | 四仓各 ≥1 命中 | **4/4**：dps 391 / rag 493 / memory 422 / llm 5200；40 个 `request_id` 逐条反查留证（其中 7 个 0 命中，均属探活/豁免样本） | **通过** |
| 3 | 应用日志行 JSONL 契约 | 合法率 100% | **100%**：dps 391 / openrag 348 / openmemory 422 / openllm 2786；`status_code` 非数字计数 **0** | **通过** |
| 4 | 本仓回归 + 静态检查 | `ruff` 0、无新增失败 | `ruff` **0 错误**；全量回归 **passed=996 / failed=0 / skipped=4**（85 文件 / 29 组，子进程隔离） | **通过** |

**分项用例结果（本轮）**

| TT-ID | 用例 | 本轮结果 | 证据 |
|-------|------|----------|------|
| TT-147-001 | 环境就绪核验 | **通过**（共享 PG/Redis/Qdrant 可达；四仓装配点就位；五方 + IdP 健康） | `bl147-05-env.txt` |
| TT-147-002 | 采集命名契约实测（`-Action namecheck`，退出码 0） | **通过**：① 编排器命名校验 可见 16 / 跳过 12 / **不可见 0** / 历史旧命名 0；② 在盘实测 可见 85 / 跳过 104 / **不可见 0** / 历史旧命名 1（修复前旧归档）；③ 归档自检 **8/8** 全被白名单接受 | `bl147-05-namecheck.txt` |
| TT-147-003 | 网关串联抽样（≥20） | **通过**：40 次请求（4 族 × 10），**40 次带回 `X-Request-Id`** | `bl147-05-sampling.json` |
| TT-147-004 | 应用日志行 JSONL 契约 | **通过**（四仓合法率 100%；`status_code` 非数字 0） | `bl147-05-jsonl-contract.json` |
| TT-147-005 | 串联一致性（核心 P0） | **通过**：业务路径 **22/22 = 100%**（4 族 × 10 ＝ 40 次抽样） | `bl147-05-chain-consistency.json` |
| TT-147-006 | 日志中心四仓可检索 | **通过**：四仓覆盖 4/4 且 `request_id` 反查命中 | `bl147-05-retrieval.json` |
| TT-147-007 | 兜底健壮（`request_id="-"`） | **通过**：无上下文路径输出 `-`（dps 340 / openmemory 348 / openllm 2220 行；openrag 0），无异常与中断 | `bl147-05-jsonl-contract.json` |
| TT-147-008 | 本仓全量回归 + 静态检查 | **通过**：`ruff` 0 错误；`passed=996 / failed=0 / skipped=4` | `logs/v147-def005-regression.txt` |
| TT-147-009 | 四仓 R-384 专项单测独立复跑 | **通过（36/36，2026-09-20 补跑）**——DPS 10 / OpenLLM 7 / OpenMemory 12 / OpenRAG 7，逐仓逐例与回执基线一致，详见 §7.7 | `bl147-05-tt009-four-repo-rerun.txt` |
| TT-147-010 | 采集抽样披露 | **通过（披露完整）**：非应用行（框架自身输出）占比如实统计（框架行 dps 2885 / openrag 385 / openmemory 548 / openllm 12910），未静默降级 | `bl147-05-jsonl-contract.json` |

**缺陷闭环（本轮覆盖确认）**：DEF-BE-147-001~005 **全部闭环**。其中 **DEF-BE-147-005 定向复测**：经网关 `GET /api/v1/rag-proxy/collections` → **200 且 `data.items=12`**，响应头 `X-Request-Id` 与 OpenRAG 应用日志行 `request_id` **完全一致**；本轮抽样中 `collections` 五次（seq 11/13/15/17/19）亦**均 200** 且业务路径命中 **5/5**。

**结论**：**BL-147-05（专项验收口径）判定：通过**——判据 1/2/3 全达成；判据 4 的**本仓侧**达成，其「四仓专项回归」项（**TT-147-009**）于 **2026-09-20 补跑通过（四仓 36/36，逐仓逐例与回执基线一致，见 §7.7）**，**《测试计划》§2.1 四项判据至此全部达成**（原 §5「跳过项」已闭合）。

**口径提示（交测试回溯审计与人工门禁确认，非隐藏项）**：① 串联判据的**计入样本数**为业务路径 **22** 条（抽样总数 40 条，其中 18 条为按契约豁免、天然无请求上下文的探活路径）——**已满足「≥20 业务路径样本」**（第一轮中间态为业务路径 13 条 / 抽样总数 24 条，因 13 < 20 触发审计观察项 O-1，故按同口径强化重跑，见修订历史 v1.4.1）；② `bl147-05-jsonl-contract.json` 中 `missing_required` 计数非零（dps 309 / openrag 348 / openmemory 348 / openllm 2732，经查为不携带请求上下文的生命周期类应用行），校验器实际判据为「合法 JSON + `status_code` 非数字计数 0」。两项口径差异已如实登记于《OpenBase-测试回溯对比审计报告-v1.4.7》§8。

### 7.7 TT-147-009 补跑（2026-09-20）：四仓 R-384 专项单测独立复跑

> **性质**：本节为 **Step 4 收口补跑**，用于闭合《测试报告》§5 跳过项（原「四仓 R-384 专项单测独立复跑未执行」）与《OpenBase-测试回溯对比审计报告-v1.4.7》§4 登记的证据缺口。执行方式为**逐仓原地复跑**，**未改动四仓任何文件**；本节不改变 §7.1~§7.6 已定稿的实测数值。

**执行要素**

| 项 | 内容 |
|----|------|
| 判据 | BL-147-05 判据 4 之①（《测试计划》§2.1 目标 4、§5 标准 5）；《R384四仓施工派单》§9 回执要求 |
| 执行时段 | 2026-09-20（补跑执行） |
| 执行角色 | AT-OpenBase-Test（测试执行方） |
| 解释器 | Python 3.10.11（沙箱 tools python）+ pytest 9.1.1 |

**逐仓命令与结果**

| 仓 | 命令（cwd / 关键参数） | 结果 |
|----|------------------------|------|
| DPS | `python -B -m pytest src/tests/test_r384_request_id_filter.py -p no:randomly -p no:cacheprovider -q`（cwd=DPS，`PYTHONPATH=src`） | **10 passed**（failed 0） |
| OpenLLM | `python -B -m pytest tests/unit/test_r384_request_id_filter.py --noconftest -p no:cacheprovider -q`（cwd=OpenLLM/backend） | **7 passed**（failed 0） |
| OpenMemory | `python -B -m pytest tests/unit/test_r384_logging_contract.py -p no:cacheprovider -q`（cwd=OpenMemory） | **12 passed**（failed 0） |
| OpenRAG | `python -B -m pytest tests/unit/test_r384_request_id.py -p no:cacheprovider -q`（cwd=OpenRAG） | **7 passed**（failed 0） |
| **合计** | — | **36/36 passed**，与四仓回执基线 10 / 7 / 12 / 7 **逐仓逐例一致** |

**证据**：`doc/test/evidence/v147/bl147-05-tt009-four-repo-rerun.txt`（含四仓逐仓解释器、命令、原文输出与结论）。

**环境适配说明（环境限制，非仓内缺陷；未改四仓任何文件）**：

1. **DPS**：其测试模块以 `from logging_setup import ...` 导入被测模块，需仓内 `src` 入 `sys.path`，故显式设 `PYTHONPATH=src`。
2. **OpenLLM**：其 `tests/conftest.py` 在收集阶段即导入 `app.api` → `app.edgerouter.auth.jwt_handler` → `jwt` / `cryptography`，本沙箱下解析到 pgAdmin py313 依赖组合，触发 `cryptography ... _rust` DLL 加载失败。该用例文件**不依赖 `conftest` fixture**（仅使用模块内 `autouse` fixture `_restore_root_logging` 与直接导入 `app.core.r384_logging`），故按 pytest 官方选项 `--noconftest` 执行；标准口径的失败原文同文件留证。**该适配不影响 7 例断言的判定对象（纯日志过滤行为）**。
3. **OpenMemory / OpenRAG**：按仓内既有 pytest 配置直跑，无适配。

**未复跑范围（如实标注）**：四仓「仓级全量回归」命令（《施工派单》§6 所列 `ruff` / K07 矩阵 / smoke 等）**不在 TT-147-009 判据范围内**，本轮未复跑；四仓仓级质量由其自身流程与回执负责（《测试计划》§1 偏差声明）。

**结论**：**TT-147-009 通过**——判据 4 的「四仓 R-384 专项单测独立复跑」项达成，原**证据缺口闭合**；《测试计划》§2.1 **四项判据至此全部达成**，本轮 **10/10 用例均取得执行证据**。

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-19 | AT-OpenBase-Test | 初始创建：v1.4.7 BL-147-05 专项验收测试报告。含入场检查与 3 项环境/工具坑、10 条用例结果（8 通过 / 2 不通过 / 1 未执行）、**串联一致性逐仓原文命中矩阵**（openllm 6/6、openmemory 3/6、dps 0/6、openrag 0/6）、4 项缺陷（3 项 P0/P1 待修复 + 1 项 P2 已闭环）、覆盖率说明、3 项跳过项、4 项遗留风险；**结论：不通过 → 回退 Step 3** |
| v1.1.0 | 2026-09-19 | AT-OpenBase-Test | **新增 §7 修复与复测记录**：登记 DPS/OpenRAG 两项缺陷的修复位置与内容（编排器 env 注入 + JSON 数组形态坑 + 3 例 TDD 护栏 + 判据细化）；复测（40 次真实请求）结果——业务路径串联 **17/22（dps 7/7、rag 5/5、llm 5/5、memory 0/5）**、JSONL 契约四仓合法率 **100%**、可检索 4/4、本仓回归通过；**结论仍为不通过**，剩余阻塞为 DEF-BE-147-003（OpenMemory）与新登记 DEF-BE-147-005（M2 副作用：rag `/collections` 200→400） |
| v1.2.0 | 2026-09-20 | AT-OpenBase-Test | **新增 §7.4 复测 2（OpenMemory 修复后）**：注入 `OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES=["openbase-memory-proxy"]`（根因＝探针路径在 `whitelist_paths` 内免门裁决，造成"探活命中"假象；业务路径受信白名单为空 → 本地重生成）；复测结果——**串联一致性业务路径 22/22 = 100%**（四族各 5~7/5~7 全中）、探活路径 18/18、JSONL 契约四仓 100%、可检索 4/4、护栏 4 例全绿；**结论更新为「不通过（仅剩 1 项）」**，唯一残留为 DEF-BE-147-005（rag `/collections` 400，串联正常/功能异常） |
| **v1.3.0** | **2026-09-20** | **AT-OpenBase-Test** | **新增 §7.5 复测 3（DEF-BE-147-005 闭环，定向复测）**：登记修复内容（显式开关 `rag_inject_identity_headers` + 编排器 openbase 声明 + 4 例护栏）、方案 A/B 决策证据（A→200 但 `items=[]`；B→200 且数据完整）、定向复测结果（经网关 `rag-proxy/collections` **200 + `items=12`**，`X-Request-Id` 与 OpenRAG 应用日志行一致，非 2xx 体完整 190 字节）；同步登记证据口径纠错（「400 响应体为空」经双口径复核证伪并撤回）；**总结论标注为「待 §7.6 全量重跑后定稿」**，不改动 §1/§7 既有结论 |
| **v1.4.0** | **2026-09-20** | **AT-OpenBase-Test** | **新增 §7.6 复测 4（2026-09-20 全量重跑：BL-147-05 通过）**：登记执行概况（14:20:16~14:28:41、五方服务 + OIDC IdP、经编排器启动、校验器**退出码 0**）、逐判据实测（业务路径串联 **13/13 = 100%**、探活/豁免路径 11 次单列、四仓应用日志行 JSONL 合法率 **100%**（dps 331 / openrag 307 / openmemory 360 / openllm 2336）、`repo_log` 可检索 **4/4**（dps 331 / rag 446 / memory 360 / llm 4356）、本仓 `ruff` 0 与全量回归 **996 通过 / 0 失败 / 4 跳过**）、10 条用例逐项结果与证据文件名（`bl147-05-env.txt` / `-namecheck.txt` / `-sampling.json` / `-jsonl-contract.json` / `-chain-consistency.json` / `-retrieval.json` / `logs/v147-def005-regression.txt`）；**元信息「测试结论」刷新为「通过（限定口径：BL-147-05 专项验收）」**，并声明完整 Step 4 门禁须与 Step 3 门禁材料 + 本报告 + 测试回溯对比审计报告三者齐备后判定、门禁登记须经人工批准；同步刷新 §2/§3/§6 的历史与现状边界标注、§5 中 **TT-147-009 仍未执行**的如实核对、§7 首轮结论加「历史留存」声明；文档版本 v1.3.0 → **v1.4.0** |
| **v1.4.1** | **2026-09-20** | **AT-OpenBase-Test** | **验收数值同步为最终权威口径（`-PerFamily 10` 强化重跑）**：经 `-PerFamily 10` 重跑强化样本量以满足《测试计划》§2.1/§5 的「**≥20 业务路径样本**」（第一轮 `-PerFamily 6` 抽样 24 次、业务路径 13 条 < 20，记为**中间态**，其日志 `logs/v147-bl147-05-rerun.txt` 仅作历史引用），最终权威口径为 **2026-09-20 14:39:33~14:46:56、4 族 × 10 ＝ 40 次抽样、校验退出码 0**（日志 `logs/v147-bl147-05-rerun-perfamily10.txt`，`E2E10_DONE exit=0`）；§7.6 判据与用例数值全量刷新为——业务路径串联 **22 / 命中 22 / 未命中 0 / 命中率 1.0（100%）**（逐族 dps 7/7、rag 5/5、memory 5/5、llm 5/5；探活/豁免路径 **18** 次、命中 11，单列不计入）、抽样 **40/40** 带回 `X-Request-Id`、四仓应用日志行 JSONL 合法率 **100%**（dps 391 / openrag 348 / openmemory 422 / openllm 2786；`status_code` 非数字 0）、`repo_log` 可检索 **4/4**（dps 391 / rag 493 / memory 422 / llm 5200；`request_id` 反查 40 个 id、其中 7 个 0 命中均为探活/豁免样本）、`collections` 五次（seq 11/13/15/17/19）均 200 且 rag 业务路径 **5/5**；元信息「测试结论」与 §7.6 执行概况/判据表/用例表/口径提示同步刷新，§7.6 口径提示①标注「≥20 业务路径样本已满足」，`missing_required` 计数同步刷新（dps 309 / openrag 348 / openmemory 348 / openllm 2732）；**§2 首轮（2026-09-19）历史结果与 §7.1~§7.5 各轮记录原文保留、不改写**；文档版本 v1.4.0 → **v1.4.1** |
| **v1.5.0** | **2026-09-20** | **AT-OpenBase-Test** | **Step 4 收口：TT-147-009 补跑通过（《测试计划》§2.1 四项判据全达成）**：① 新增 **§7.7 TT-147-009 补跑（2026-09-20）**——逐仓复跑四仓 R-384 专项单测（DPS **10** / OpenLLM **7** / OpenMemory **12** / OpenRAG **7** ＝ **36/36 passed**、失败 0，与四仓回执基线逐仓逐例一致；证据 `doc/test/evidence/v147/bl147-05-tt009-four-repo-rerun.txt`），并如实登记环境适配（DPS `PYTHONPATH=src`；OpenLLM 因沙箱 `tests/conftest.py` 前置 pgAdmin py313 依赖触发 `cryptography ... _rust` DLL 冲突，改用 pytest 官方选项 `--noconftest`，成立条件已回读源码核验——该用例仅模块内 `autouse` fixture + 直接导入 `app.core.r384_logging`、**不依赖 `conftest` fixture**；**未改四仓任何文件**）与未复跑范围（四仓仓级全量回归不属本判据范围，以回执为准）；② **§5 跳过项（TT-147-009）改记「已闭合（2026-09-20 补跑执行）」**，影响列改为「无（原覆盖缺口已闭合）」、批准列标注「已补跑留证；Step 4 放行仍须人工批准」；③ §6 追溯核对 TT-147-009 由「跳过/⚠️」改为「**通过（36/36）/✅**」，层间追溯由「唯一断点」改为「**无断点、无未执行项**（10/10 用例均取得执行证据）」；④ §2 首轮历史表 TT-147-009 行加注「2026-09-20 补跑通过（36/36）」并保留首轮历史口径；⑤ §7.6 口径说明、分项用例结果与结论同步更新为「TT-147-009 已补跑通过 → 四项判据全达成」；⑥ §1 入场检查「`code-logic-review` / Stage3 开发审计」由「本版本未产出 / ⚠️ 偏差」改为「**已产出（2026-09-20 补齐入库）/ ✅（偏差已消除）**」，§6 遗留风险第 4 项改记「**已闭合**」（Step 3 与 Step 4 审计材料均齐备）；⑦ 元信息「测试结论」补充补跑结论与 **Step 4 收口状态**（Step 3 门禁材料 + 本报告 + 测试回溯对比审计报告 v1.0.2 + Stage4 阶段审计报告 v1.0.0 **均已产出**）；文档版本 v1.4.1 → **v1.5.0** |
