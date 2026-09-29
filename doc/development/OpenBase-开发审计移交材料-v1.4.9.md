# OpenBase 开发审计移交材料 - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（编排与回写代码所在仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量，承接型小版本） |
| 文档 | 开发审计移交材料（Step 3 产出 5，`coding-stage-execution` §3.10） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（待人工批准后进入 Step 4） |
| 作者 | AD-OpenLLM-Dev |
| 移交对象 | AU-OpenBase-Dev（审计师，Step 3 阶段审计） |
| 创建/更新日期 | 2026-09-29 |
| 存放 | `doc/development/` |
| 上游依据 | 设计基线 **v1.6.3**（[Approved] 基线 ＋ 批次 7/8 澄清）；追溯矩阵 **v1.9.1**；DevLogReport **v1.1.2** |

---

## 1. 移交范围与结论

| 项 | 内容 |
|----|------|
| 本阶段范围 | **Step 3 开发**：按 7 个批次（含收尾补漏与 I-2 生产落线）实现 v1.4.9 增量 I-1／I-2／I-3／I-5／I-6／I-7／I-8／I-9；完成静态质量门、**实际运行验证三层**、逻辑审查、债务增长率检查、变更一致性自检与阶段审计 |
| 明确排除 | I-4（`used_fragments` 跨仓运行态，受 **D4**）；画像 LLM 提炼**生效**（受 **D3**）；I-1／I-6／I-8 的**运行态**统计；Step 4 测试结论；Step 5 部署与灰度 |
| 是否具备进入开发审计条件 | ✅ 具备（**未闭环 P0/P1 = 0**） |
| 开发设计对比覆盖率 | **100%（20/20）**：设计 §3.2~§3.19 全部条目均有实现落点或**显式登记态**（§3.12／I-10 按设计**不实施**） |
| 判据可执行证据 | 判据探针 **6/6 PASS**（AC-149-05/09/10/11/12 ＋ 结构护栏）；增量执行器 **离线 7/7**（运行态 4 项**如实未覆盖**） |
| 移交材料齐备性 | ✅ 追溯矩阵／DevLogReport／静态质量检查记录／逻辑审查记录／本材料／Stage3 审计／证据 12 份（见 §4） |

**结论**：**具备进入开发审计**（Step 3 → Stage3 审计 → Step 4 测试）；4 项受限项与 4 项遗留项已如实登记（§5／§6），**不以「已修」覆盖「未覆盖」**。

---

## 2. 变更集清单（Deliverable Inventory）

### 2.1 代码与测试（落点仓 **OpenLLM**）

| 项 | 数量 | 说明 |
|----|:----:|------|
| 生产代码 | **13 个文件**（新增 **0** / 修改 **13**） | `prompt_pipeline.py`／`context_metrics.py`／`assembler.py`／`component_pipeline.py`／`executor.py`／`channel.py`／`channel_audit.py`／`evaluate.py`／`profile_refine_gate.py`／`core/config.py`／`api/openllm_gateway.py`／`services/writeback_queue.py`／`main.py` |
| 测试代码 | **11 个文件**（新增 **10** / 修改 **1**） | 新增：`test_context_trim_markers`／`test_context_cross_segment_competition`／`test_context_dropped_detail`／`test_context_over_window_verifier`／`test_component_channel_routing`／`test_channel_audit_action_codes`／`test_component_channel_audit_wiring`／`test_profile_delta_and_precheck_wiring`／`test_context_receipt_fields`／`test_segment_items_production_wiring`；修改：`test_channel_failover_audit`（随动作码**定稿**更正） |
| 删除文件 | **0** | — |
| 代码行增量（`git diff --shortstat`，基线 `d7742c7`→`2f5364d`） | **25 files changed, 2927 insertions(+), 89 deletions(-)** | 工具实测，非估算 |
| 提交 | **9 笔代码提交**（＋1 笔 OpenLLM 侧文档提交） | `2d1aa85`／`a1021c4`／`33c4009`／`9b36160`／`9782f48`／`1651e42`／`333188a`／`a9914e6`／`2f5364d` |
| 推送状态 | **均未推送** | 按用户口径：推送需单独确认 |

### 2.2 文档产物（文档仓 **OpenBase**）

| # | 文件 | 变更 | 版本 |
|:-:|------|------|:----:|
| 1 | `doc/development/OpenBase-开发审计移交材料-v1.4.9.md` | **新建（本材料）** | v1.0.0 |
| 2 | `doc/design/OpenBase-系统架构设计文档-v1.4.9.md` | 修改（§3.19 设计补充 F ＋ §3.16 论域澄清） | **v1.6.3** |
| 3 | `doc/design/OpenBase-API接口设计文档-v1.4.9.md` | 修改（回执契约与实现对齐） | **v1.3.0** |
| 4 | `doc/development/OpenBase-设计开发追溯矩阵-v1.4.9.md` | 修改（批次 1~8 记录；TD-14901~14909） | **v1.9.1** |
| 5 | `doc/development/OpenBase-DevLogReport-v1.4.9.md` | 修改（逐批次实现／验证／债务／运行验证） | **v1.1.2** |
| 6 | `doc/development/OpenBase-静态质量检查记录-v1.4.9.md` | 修改（7＋7′ 批次 ＋ 债务增长率） | **v1.1.2** |
| 7 | `doc/development/OpenBase-代码逻辑审查记录-v1.4.9.md` | 修改（16 项发现／一致性核对） | **v1.3.0** |
| 8 | `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.9.md` | 修改（G1~G7 ＋ 门禁补 3.4a/3.5/3.9b） | **v1.3.0** |
| 14~18 | `doc/test/evidence/cr149/`：`v149-increment-eval-set.json`／`v149_increment_runner.py`／`v149_increment_runner-result.json`／`v149_receipt_and_purity_probe.py`／`v149_receipt_and_purity_probe-result.json` | 新建（批次 6/7 证据） | — |
| 19~25 | `doc/test/evidence/v149/`：`cr149-l1-compile-20260929.txt`／`cr149-instance-8041-20260929.log`／`cr149-l3-smoke-20260929.py`／`cr149-l3-smoke-20260929.json`／`cr149-debt-growth-20260929.txt`／`cr149-consistency-selfcheck-20260929.txt`／`cr149-deliverable-inventory-20260929.txt` | 新建（本批 3.4a／3.5／3.9b／3.10 证据） | — |

### 2.3 既有文档状态流转

| 范围 | 变更 |
|------|------|
| Step 0/1/2 产出（单版本规划／需求／设计各件） | 无内容变更（本阶段仅 Step 3 产出与上文 2.2 所列 6 份同步件） |
| `doc/design/OpenBase-系统架构设计文档-v1.4.9.md` | 新增 §3.19（设计补充 F）；§3.16 补入 `dropped` 恒有的**精确论域** ⇒ **消除其与 §3.19 的字面冲突**（判据口径不变） |
| `.devflow/state.json` | 阶段位 `v1_4_9_step_3_pending_approval`（待批准后推进 Step 4） |

---

## 3. 门禁证据摘要

| 门禁（skill 条目） | 证据 | 结果 |
|-------------------|------|:----:|
| 入场确认（需求 ＋ 设计已批准） | 《Stage2 阶段审计报告-v1.4.9》v1.0.4（[Approved]） | ✅ |
| 3.4a 语法与一致性检查 | 《静态质量检查记录-v1.4.9》v1.1.2 §1／§2（改动面 `ruff` 0 告警 ＋ `compileall` 通过） | ✅ |
| **3.4a 技术债务增长率** | 《DevLogReport-v1.4.9》§7 ＋ `cr149-debt-growth-20260929.txt`（**工具实测 ＋ 两侧比对**）：新增 TODO **0**（≤5）／新增高复杂度函数 **3**（≤3，**达阈值上限**，已逐函数登记）／重复块增量 **0**（≤2%） | ✅（附注） |
| **3.5 实际运行验证 L1/L2/L3** | `cr149-l1-compile-20260929.txt`（L1：`compileall` exit 0 ＋ `import main` OK）／`cr149-instance-8041-20260929.log`（L2：`Application startup complete.` ＋ `Uvicorn running on 127.0.0.1:8041`，健康检查 200）／`cr149-l3-smoke-20260929.json`（L3：**6 例全 PASS**） | ✅ |
| 3.6 开发自测 | 相关面 14 文件 **208 passed**；全量 `pytest tests/unit tests/integration` → **3760 passed / 21 failed**（与基线逐 node id 一致 ⇒ **零新增失败**） | ✅ |
| 3.7a 代码逻辑审查 | 《代码逻辑审查记录-v1.4.9》v1.3.0（9 条 TD 全收口；10 项不变量有结构性论证 ＋ 反例护栏；**17 项**发现**均已闭合**） | ✅ |
| **3.9b 变更一致性自检** | `cr149-consistency-selfcheck-20260929.txt`：① 命名合规（**如实登记**：本仓**无** `validate-naming.ps1` ⇒ 以规范核对等价执行）② 文件头 vs 修订历史版本 **33 份全一致** ③ 新增文件路径全落规范目录 ⇒ **通过** | ✅ |
| 3.10 产出物存在性验证 | §4 ＋ `cr149-deliverable-inventory-20260929.txt`（**TOTAL 20 / EMPTY 0 / MISSING 0**） | ✅ |
| 判据可执行证据（本版本验收） | `v149_receipt_and_purity_probe-result.json`（6/6）／`v149_increment_runner-result.json`（离线 7/7，运行态 4 项未覆盖） | ✅ |

---

## 4. 产出物存在性验证

| 产出类别 | 清单 | 存在性 |
|----------|------|:------:|
| 生产代码落点 | §2.1 所列 13 文件（OpenLLM） | ✅ 已核（`git diff --name-only`） |
| 测试护栏 | §2.1 所列 11 文件（10 新增 ＋ 1 修改） | ✅ 已核 |
| 设计同步件 | 架构 v1.6.3／API v1.3.0 | ✅ 已核 |
| 开发记录 | 追溯矩阵 v1.9.2／DevLogReport v1.1.2／静态质量 v1.1.2／逻辑审查 v1.3.0／本材料 v1.0.0 | ✅ 已核 |
| 审计 | Stage3 阶段审计 v1.3.0 | ✅ 已核 |
| 证据 | `doc/test/evidence/cr149/` 5 份 ＋ `doc/test/evidence/v149/` 7 份 ＝ **12 份** | ✅ 已核（**TOTAL 20 / EMPTY 0 / MISSING 0**） |

**验证方式**：文件系统清点（`Get-ChildItem` ＋ 字节/行数统计）＋ `git` 变更面核对；**清点证据**：`doc/test/evidence/v149/cr149-deliverable-inventory-20260929.txt`（**TOTAL FILES: 20 / EMPTY FILES: 0 / MISSING FILES: 0**）。

---

## 5. 已知风险与后续动作

| # | 项 | 级别 | 后续动作 |
|:-:|----|:----:|----------|
| 1 | 新增高复杂度函数 **3 个达阈值上限**（`run_components` 26／`_build_writeback_callback` 16／`generate` 16） | P3 | 均为**接线型门控/fail-open 分支**（I-6／I-8／批次 8）；**未超阈值**（≤3）⇒ 不阻断；登记为**下版本重构候选**（抽取辅助函数） |
| 2 | `memory`/`rag` 条目身份的运行态实测未覆盖 | P2 | 本环境 `openrag` 组件 `unavailable`、`memory` 召回 **0 条目** ⇒ 运行态 `dropped` 为空属预期；身份贯通已由单元护栏证明，运行态实测移交 **Step 4/5**（需真实检索数据） |
| 3 | AC-149-05 齐备率 / AC-149-12 超窗率的**正式统计** | P1 | 本版仅**可判性**取证（探针 ＋ L3 冒烟）；足量样本统计移交 **Step 5** 实测 |
| 4 | 全量回归 **21 项既有失败** | P2 | 与改动面无交集（401 统一格式／模型路由接线／real-contract 默认值开关／流式收尾）；不随本版修复（避免扩大范围） |

---

## 6. 遗留项与受限项（如实登记，不以「已修」覆盖「未覆盖」）

| 类别 | 项 | 定性 |
|------|----|------|
| 受限（**D4**） | I-4 `used_fragments` 跨仓回写**运行态** | 字段定义已冻结（API §3）；运行态未覆盖，判据执行器 `runtime_pending` 标注 |
| 受限（**D3**） | 画像 LLM 提炼**生效** | 只交付**接线**；生效需评测支撑 |
| 受限（**运行环境**） | I-1／I-6／I-8 运行态段 | L3 冒烟已证「开关关闭 ⇒ 逐字回退」与「预算生效 ⇒ 回执齐备」；**跨组件竞争/通道切换的真机统计**移交 Step 4/5 |
| 遗留（低风险） | 池上界仍用汇总 `Σdropped_tokens`（估值偏大） | 设计 §3.15 登记为后续可选项（T1 由一阶项封顶） |
| 遗留（可选） | 3 个函数**达复杂度阈值上限** | 见 §5 第 1 项，登记为下版本重构候选 |
| 顺序偏差（已登记） | 批次 7 属「**实现先行、设计澄清在后**」 | 架构 §3.19 于实现后补写 ⇒ 偏离「先补设计再实施」纪律，已在追溯矩阵／逻辑审查／Stage3 审计显式登记，供人工复核 |
| 取证工具缺陷（自纠） | G3／G6 探针误报与判定过弱 | 均为**取证工具**缺陷，不入生产缺陷账；已加固并留痕 |

---

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-29 | AD-OpenLLM-Dev | 初始创建（`coding-stage-execution` §3.10 开发审计移交）：Step 3 范围与结论、变更集清单（OpenLLM 13 生产 ＋ 11 测试＝2927 insertions/89 deletions、9 笔提交；OpenBase 6 份同步件 ＋ 11 份证据）、**10 项门禁证据摘要（含 3.4a 债务增长率 0/3/0、3.5 L1/L2/L3、3.9b 变更一致性自检）**、产出物存在性验证、风险 4 项与遗留/受限项 7 类如实登记（含「实现先行、澄清后补」顺序偏差与 2 项取证工具缺陷自纠）。状态 [Review] |
