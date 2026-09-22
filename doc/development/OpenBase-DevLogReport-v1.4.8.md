# OpenBase DevLogReport - v1.4.8

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.8（会话编排前置与回写闭环 · **跨仓 + 文档型交付**） |
| 文档版本 | v1.7.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-09-21 |
| 更新日期 | 2026-09-21 |
| 存放 | doc/development/ |

---

## 1. 版本记录与入场检查（3.0）

| 项 | 内容 |
|----|------|
| 开发范围（**本仓侧**） | ① 设计契约交付（14 项，Step 2 已产出并经人工批准）；② **跨仓分发**：向 OpenLLM 仓分发《会话编排派单-OpenLLM-v1.0.0》v1.2.0（第零段 / 前置零 / 第一批），向 openbase-ui 仓出具《会话标识提交派单-v1.0.0》（D2）；③ 开发阶段记录与审计移交材料 |
| 明确排除 | BL-148-01~06 的**代码实现**（属 OpenLLM 仓，`VC-014` 本仓不实施）；BL-148-07 的**实际测量**（受 D3 约束，挂起）；v1.4.9 第二批 / 第三批 |
| 版本性质 | 承接型小版本（1.4.x 承接线）；主体施工在 OpenLLM 仓，本仓为**文档型交付阶段** |
| 设计输入 | 《需求设计追溯矩阵-v1.4.8》（[Approved]）、《系统架构设计文档-v1.4.8》（[Approved]，AD-01~15）、《数据库设计文档-v1.4.8》、《API接口设计文档-v1.4.8》、《安全设计说明-v1.4.8》、《非功能设计说明-v1.4.8》、《会话编排派单-OpenLLM-v1.0.0》v1.2.0、《设计基线及开发测试移交说明-v1.4.8》 |
| 入场确认 | Step 1 需求（[Approved]，2026-09-21）→ Step 2 设计（设计评审 / 需求架构对比审计 / Stage2 阶段审计**全部通过**，[Approved]，2026-09-21）✅ |
| 设计门禁证据 | Stage2 六项门禁全过 + 强制规则 7/7 + 产物真实性 13/13（《阶段审计报告-Stage2-v1.4.8》） |
| 基线 | v1.4.7（已发布，Step 5 已闭环） |
| 变更面约束 | 本仓**无 DB schema 变更、无接口契约变更、无新增依赖**；**跨仓代码改动**（OpenLLM 仓）见 §13（`VC-017` 前为「本仓无代码改动」，该表述已失效） |
| 回滚方式 | 本仓无代码改动，文档回退按 `git revert`；**跨仓改动回退**：OpenLLM 仓以登记在案的 12 个源文件为单位 `git revert`（当前**未提交**，可整体丢弃） |

---

## 2. 任务拆解与追溯（3.1 / 3.2）

| # | 子任务 | 关联 BL / TD | 交付物 | 状态 |
|:-:|-------|--------------|--------|:----:|
| 1 | 建立设计开发追溯矩阵（DT→TD→BL→落点） | TD-148-01~13 | `doc/development/OpenBase-设计开发追溯矩阵-v1.4.8.md` | ✅ |
| 2 | 跨仓分发（OpenLLM 仓，v1.4.8 三段） | BL-148-01~06 / TD-148-14 | `doc/planning/OpenBase-会话编排派单分发清单-v1.4.8.md` | ✅ |
| 3 | 前端配合派单（openbase-ui，D2） | BL-148-04 / TD-148-14 | `doc/planning/OpenBase-会话标识提交派单-openbase-ui-v1.0.0.md` | ✅ |
| 4 | 文档型实际运行验证（L1/L2/L3）与证据落盘 | 支撑全部 TD | `doc/test/evidence/v148/*` | ✅ |
| 5 | 变更一致性自检（3.9b） | 支撑全部 TD | 本报告 §8 + 证据 `step3-v148-consistency-20260921.txt` | ✅ |
| 6 | 开发审计移交材料 | 支撑 Step 3 门禁 | `doc/development/OpenBase-开发审计移交材料-v1.4.8.md` | ✅ |
| 7 | 设计/审计状态流转获批（17 项） | 支撑 Step 3 入场 | 17 项设计/审计文档状态 → [Approved] | ✅ |
| 8 | `state.json` 阶段流转 | 支撑 DevFlow | `currentPhase = v1_4_8_step_3_development`；`completedPhases += v1_4_8_step_2_design` | ✅ |

**范围可追溯性**：8 项子任务全部可回溯至 Backlog（BL-148-04/08）、设计项（DT-148-*）或门禁要求 ✅；未出现隐式扩项 ✅。

---

## 3. 实现内容（3.3，文档型）

### 3.1 交付物分类

| 类别 | 数量 | 说明 |
|------|:----:|------|
| 设计契约（Step 2 产出，本阶段归档确认） | 14 | 系统架构 / 数据库 / API / 安全 / 非功能 / 部署 / DSL 边界 / B0B1 框架 / 追溯矩阵 / 入场检查 / 后端覆盖 / API 对齐 / 设计评审 / 移交说明 |
| 跨仓分发件（本阶段新增） | 2 | 派单分发清单（OpenLLM）、会话标识提交派单（openbase-ui） |
| 开发阶段记录（本阶段新增） | 2 | 本报告、开发审计移交材料 |
| 证据文件（本阶段新增） | 2 | 产物清点、变更一致性自检 |

### 3.2 关键实现决策

| # | 决策 | 说明 |
|:-:|------|------|
| 1 | **本仓零代码改动** | 依 `VC-014`：不实施 OpenLLM 侧代码改动；本版本本仓交付形态为「设计契约 + 跨仓派单 + 开发记录」 |
| 2 | **派单自包含分发** | 派单文档自含契约 / 落点 / 验收判据，接收仓独立评审与发布；本仓以回执验收 |
| 3 | **开工前置核实 5 项** | 明确要求接收仓回填（会话标识命名 / 历史窗口来源 / 工装落点 / 幂等键历史兼容 / 流式回写可行性）；冲突须先更正契约（对齐闭环） |
| 4 | **硬判据显式化** | 「重启后回写丢失数 = 0」「两路径行为一致」写入分发清单验收判据，并声明**不依赖阈值**、D3 未确认期间同样必须判定 |
| 5 | **D2 单列派单** | 前端会话标识提交独立成单（接口层配合、不含界面改造），避免与 OpenLLM 派单混淆边界 |

### 3.3 文件级变更表（本仓）

| 文件 | 变更 | 说明 |
|------|------|------|
| `doc/development/OpenBase-设计开发追溯矩阵-v1.4.8.md` | **新建** | DT→TD→BL→落点追溯 + Subtask CheckList + 版本控制记录 |
| `doc/planning/OpenBase-会话编排派单分发清单-v1.4.8.md` | **新建** | 分发总览 / 分发内容 / 前置核实 / 10 项验收判据 / 风险 / 回执登记 |
| `doc/planning/OpenBase-会话标识提交派单-openbase-ui-v1.0.0.md` | **新建** | 契约 / 落点 / 行为要求 / 5 项验收判据 / 边界风险 |
| `doc/development/OpenBase-DevLogReport-v1.4.8.md` | **新建** | 本报告 |
| `doc/development/OpenBase-开发审计移交材料-v1.4.8.md` | **新建** | Step 3 门禁移交 |
| `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.8.md` | **新建** | Step 3 阶段审计 |
| `doc/test/evidence/v148/*.txt` | **新建** | 验证证据 2 份 |
| `doc/design/**/*-v1.4.8.md`（14 项）、`doc/audit/**`（3 项） | 修改 | 状态 `[Review]` → `[Approved]`（2026-09-21 人工批准）；3 份门禁件补批准修订记录 |
| `.devflow/state.json` | 修改 | 阶段流转至 `v1_4_8_step_3_development`；补 `design_v1.4.8` 文档登记 |

**代码文件变更：0 个**（`VC-014`）；**测试文件变更：0 个**；**文档新增 6 个、修改 18 个、删除 0 个**。

---

## 4. 静态质量检查（3.4，文档型等价检查）

> 本仓**文档型交付**部分按 `code-static-quality-check` 的 12 类检查项**等价项**执行；
> 跨仓代码改动（OpenLLM 仓，`VC-017` 后直接实施）的静态检查见 §13.3。

| 检查维度 | 等价检查项 | 结果 |
|----------|-----------|:----:|
| 语法 | Markdown 结构合法（标题层级 / 表格语法 / 代码块闭合） | ✅ 22/22 |
| 引用一致性 | 跨文档章节引用（如「架构 §4.4」「API §2」）与目标文档实际章节一致 | ✅ 首轮发现 5 处漂移，已修复（见《设计阶段自检记录-v1.4.8》） |
| 命名合规 | 文件名符合 `{项目名}-{文档类型}-v{版本号}.md` | ✅ 22/22 |
| 编号一致 | DT / TD / RT / AC / AD 编号跨文档一致 | ✅ |
| 计数一致 | AC = 27、需求 = 8、P0 = 7（6 无条件 + 1 条件）、P2 = 1 | ✅ |
| 状态一致 | 设计/审计交付物无遗留 `[Review]`（review_left_count = 0） | ✅ |
| 契约覆盖 | 5 大关键契约（`session_id` / `max_seq` / `o200k_base` / 最长键优先 / 仅观测）与 2 条硬约束（`VC-014` / 重启后回写丢失数）无孤点 | ✅ |
| 敏感信息 | 交付物无令牌 / 密码 / 密钥 / 完整请求体 | ✅（脱敏红线扫描 0 命中） |
| 修订历史 | Step 3 新增 3 份交付物均含「修订历史」章节 | ✅ |

**技术债务增长率检查**：

| 项 | 阈值 | 实际 | 判定 |
|----|:----:|:----:|:----:|
| 新增 TODO 数 | ≤5 | **0**（无代码交付） | ✅ |
| 新增高复杂度函数数 | ≤3 | **0** | ✅ |
| 代码重复率增量 | ≤2% | **0%** | ✅ |

**结论**：静态质量检查通过，无 P0/P1 问题。

---

## 5. 实际运行验证（3.5，文档型三层模型）

> 依 `coding-stage-execution` §3.5c「脚本/文档型验证」：L1 语法/格式检查 → L2 执行/打开验证 → L3 走查验证。

### 5.1 L1 构建验证（格式校验）

| 项 | 内容 |
|----|------|
| 命令 | `Get-ChildItem doc\design,doc\development,doc\audit,doc\planning -File \| ? { $_.Name -match "v1\.4\.8" } \| 逐项输出 lines/bytes` |
| 输出摘要 | **TOTAL FILES: 22**；**EMPTY FILES: 0** |
| 证据 | `doc/test/evidence/v148/step3-v148-doc-inventory-20260921.txt` |
| 判定 | ✅ 零错误、22 份产物均正常生成 |

### 5.2 L2 启动/打开验证（存在性与可读性）

| 项 | 内容 |
|----|------|
| 检查 | 逐份读取文件行数与字节数；空文件计数 |
| 输出摘要 | 22 份文件全部 `lines > 0` 且 `bytes > 0`；最小 47 行 / 3072 B（部署架构草案），最大 172 行 / 16291 B（系统架构设计文档） |
| 证据 | 同上 |
| 判定 | ✅ 全部可打开、非空（`EMPTY FILES: 0`） |

### 5.3 L3 走查验证（按文档流程模拟执行）

| # | 走查路径 | 结果 |
|:-:|----------|------|
| 1 | 追溯链走查：需求 RT-148-xx → 设计 DT-148-xx → 开发 TD-148-xx → BL-148-xx → 落点 | ✅ 全链闭合，无断链（追溯矩阵 §1） |
| 2 | 派单自包含走查：派单件是否含契约 / 落点 / 前置核实 / 验收判据 | ✅ 齐备（分发清单 §2~§4 + openbase-ui 派单 §2~§4） |
| 3 | 门禁状态走查：Step 0/1/2 文档状态是否为 [Approved] | ✅ 0 处残留 |
| 4 | 硬判据走查：2 条硬判据是否在派单与验收中被显式声明 | ✅ 「重启后回写丢失数 = 0」「两路径行为一致」均已声明且不依赖阈值 |
| 5 | 契约关键词走查：关键契约是否在交付物集合中无孤点 | ✅ 7 项关键词命中 62/16/3/7/18/26/7 |
| 6 | 边界走查：`VC-014` 是否全链一致声明本仓不改 OpenLLM 代码 | ✅ 26 处命中，覆盖 11 份交付物 |
| 证据 | `doc/test/evidence/v148/step3-v148-consistency-20260921.txt` |

**三层验证结论**：L1 + L2 + L3 **全部通过**，证据新鲜（2026-09-21，对应当前变更集）。

---

## 6. 开发自测（3.6）

| 项 | 内容 |
|----|------|
| 自测方式 | 文档型交付以**走查自查 + 门禁复核**替代单元测试 |
| 自查项 1 | 命名与存放符合 `project-document-management`（`doc/development/` / `doc/planning/` / `doc/audit/review/`） | ✅ |
| 自查项 2 | 文档头元信息（项目 / 版本号 / 文档版本 / 状态 / 作者 / 日期 / 存放）齐备 | ✅ 22/22 |
| 自查项 3 | 每份文档含「修订历史」 | ✅ Step 3 新增件 3/3（历史件沿用既有） |
| 自查项 4 | 与设计基线对比无偏差（B0B1 框架 / DSL 边界条款与设计定稿一致） | ✅ |
| 自查项 5 | `state.json` 合法 JSON 且阶段值正确 | ✅（`ConvertFrom-Json` 校验通过） |
| 未执行项 | 单元测试 / pytest | **N/A**：本仓本版本无代码改动（`VC-014`），无被测对象 |

---

## 7. 文档逻辑审查（3.7，`code-logic-review` 等价）

> 本仓**文档型交付**部分以 `code-logic-review` 的 11 个维度做等价评审；
> 跨仓代码改动的逻辑审查见 §13.4（以单元用例与源码护栏为证据）。

| # | 审查维度 | 结论 |
|:-:|----------|------|
| 1 | 需求覆盖 | ✅ 8/8 需求、27/27 AC 均有落点（追溯矩阵） |
| 2 | 设计一致性 | ✅ 交付物与设计基线（AD-01~15）逐项一致 |
| 3 | 业务流程 | ✅ 派单开工流程（前置核实 → 实施 → 回执 → 本仓验收）闭环 |
| 4 | 状态流转 | ✅ 文档状态机（Draft→Review→Approved）与 state.json 阶段机一致 |
| 5 | API 契约 | ✅ `session_id` 契约在前端派单、API 设计、分发清单三处一致 |
| 6 | 可维护性 | ✅ 编号体系（RT/DT/TD/AC/AD/BL）可续期，无编号冲突 |
| 7 | 数据一致性 | ✅ 幂等键口径（会话维度 + `max_seq+1`）跨 3 份文档一致 |
| 8 | 权限安全 | ✅ 脱敏红线与「无新权限码」声明一致 |
| 9 | 异常与降级 | ✅ 失败隔离 / 降级 / 流式不可行的显式声明路径已定义 |
| 10 | 可测试性 | ✅ 10 项派单验收判据 + 27 条 AC 均可验证 |
| 11 | 静态证据 | ✅ 证据文件齐备且新鲜 |

**审查结论：[通过]**，无未解决 P0/P1 问题。

---

## 8. 变更一致性自检（3.9b）

| 自检项 | 结果 |
|--------|------|
| ① 命名合规（`validate-naming` 等价：文件名 = `{项目名}-{类型}-v{版本号}.md`） | ✅ 22/22 |
| ② 文件头版本号与修订历史底部版本号一致 | ✅（Step 3 新增件均为 v1.0.0 / 单条 v1.0.0 记录） |
| ③ 新创建文件路径与命名规范匹配 | ✅ |
| ④ `[Review]` 残留复扫 | ✅ `review_left_count = 0`（首轮 2 处已修正） |
| 证据 | `doc/test/evidence/v148/step3-v148-consistency-20260921.txt` |

**自检结论：通过**（首轮发现 2 处状态写法不规范，已修正后复扫归零）。

---

## 9. 技术债务与风险

### 9.1 本版本新增债务

**无**。本仓为文档型交付；跨仓（OpenLLM）改动（`VC-017` 后，见 §13）亦未引入 TODO、废弃标记或架构偏离，其静态质量与验证见 §13.3。

### 9.2 已归还债务（本版本计划内）

| 债务 ID | 级别 | 内容 | 归还载体 | 状态 |
|---------|:----:|------|----------|:----:|
| TD-新增-022 | P1 | 三路回写未接线（F-09） | BL-148-05（OpenLLM 仓） | 契约就绪，待跨仓实施 |
| TD-新增-023 | P1 | 回写幂等键缺陷（F-08，已实测复现） | BL-148-06（OpenLLM 仓） | 契约就绪，待跨仓实施 |
| TD-新增-024 | P2 | 编排双路径分叉（F-01） | BL-148-03（OpenLLM 仓） | 契约就绪，待跨仓实施 |
| TD-新增-025 | P2 | 窗口前缀匹配缺陷（F-02，低估 15.6 倍） | BL-148-01/02（OpenLLM 仓） | 契约就绪，待跨仓实施 |

> **口径说明**：上述 4 项债务的**代码归还在 OpenLLM 仓**；本仓 Step 3 完成的是设计契约与派单分发，**不据此判定债务已归还**——判定依据为接收仓回执（AC-148-06-3 等）。

### 9.3 风险归集检查

> 本章节为必填项，用于确认本版本所有 P1+ 风险/问题已归集到技术债务总表。

| 检查项 | 结果 | 说明 |
|:-------|:----:|:-----|
| 本阶段 P1+ 风险是否已归集 | ✅ | **TD-新增-022**（P1，承载 R3「流式回写可行性未确认」子项）、**TD-新增-023**（P1，F-08）。两项已在 v1.4.8 Step 0 归集并落定版本归属 |
| 未归集风险 ID 及原因 | **无** | R1（跨仓排期不可控，P0）为**版本执行风险**非技术债务，已登记于《单版本规划文档-v1.4.8》风险清单与《分发清单》§5；R2（D3 暂缓）已条件化并在需求文档声明，不构成新债务 |
| 归集日期 | 2026-09-21 | 最近一次归集操作日期 |
| 技术债务总表版本 | v0.5.5（含 TD-新增-022~026） | 归集时总表最新版本；本阶段**无新增条目需求**（已核实 §1.6 存在对应条目） |

---

## 10. 测试移交说明（Step 4 输入）

| 项 | 内容 |
|----|------|
| 移交范围 | 本仓文档型交付（设计契约 14 项 + 派单 2 项 + 开发记录）；**不含** OpenLLM 仓代码测试 |
| 测试环境 | 本仓无新增服务 / 端口 / 配置 / 依赖；跨仓测试由接收仓在其环境执行 |
| 测试数据 | 本仓无新增测试数据；跨仓 F-08 回归复用 `doc/test/evidence/f08/f08-seq-restart-repro-20260921.txt` 用例形态 |
| Mock | 不涉及 |
| 建议回归范围 | ① F-02 日期化模型名用例（3 个模型名）；② F-08 跨进程重启零丢写；③ 两路径一致性（路由 / 注入片段集合 / 缓存命中）；④ 三路回写两路径均产生记录且回执可查；⑤ 回写失败注入不影响主链路 |
| 硬判据（测试不得豁免） | 重启后回写丢失数 = 0；两路径行为一致；第零段同输入前后输出一致 |
| 已知风险 | R1 跨仓排期未定（阻塞 P0 落地）；R2 D3 未确认（B0/B1 报告挂起）；R3 流式回写可行性待回填（不可行须显式声明写入契约） |
| 跳过项 | 本仓无跳过项；BL-148-07 测量按条件挂起（非跳过） |

---

## 11. 变更统计与影响文件清单

### 11.1 统计口径

本轮统计**仅覆盖 2026-09-21 本会话实际创建/修改的文件**，不含历史遗留未提交文件。

### 11.2 分类统计

| 类别 | 新增 | 修改 | 删除 |
|------|:----:|:----:|:----:|
| 本仓：生产 / 脚本 / 配置代码 | 0 | 0 | 0 |
| **跨仓（OpenLLM）源代码**（`VC-017` 后直接实施，见 §13） | **3** | **9** | **0** |
| **跨仓（OpenLLM）测试代码** | **10** | **2** | **0** |
| 本仓：文档产物 | 6 | 18 | 0 |
| 本仓：证据 / 校验清单 | 2 | 0 | 0 |
| 配置文件（`.devflow/state.json` 等） | 0 | 1 | 0 |
| **合计** | **21** | **30** | **0** |

> **代码增删行统计**：本仓为文档型交付，无本仓代码增量；**跨仓（OpenLLM）代码增量见 §13.2**。
> 本轮受环境约束未执行 `git diff --numstat`，按文件逐一登记变更性质与影响，不以推测替代实测。

### 11.3 影响文件清单（文档产物）

| # | 文件 | 类型 | 性质 |
|:-:|------|------|------|
| 1 | `doc/development/OpenBase-设计开发追溯矩阵-v1.4.8.md` | 开发 | 新增 |
| 2 | `doc/development/OpenBase-DevLogReport-v1.4.8.md` | 开发 | 新增 |
| 3 | `doc/development/OpenBase-开发审计移交材料-v1.4.8.md` | 开发 | 新增 |
| 4 | `doc/planning/OpenBase-会话编排派单分发清单-v1.4.8.md` | 派单 | 新增 |
| 5 | `doc/planning/OpenBase-会话标识提交派单-openbase-ui-v1.0.0.md` | 派单 | 新增 |
| 6 | `doc/audit/review/OpenBase-阶段审计报告-Stage3-v1.4.8.md` | 审计 | 新增 |
| 7 | `doc/test/evidence/v148/step3-v148-doc-inventory-20260921.txt` | 证据 | 新增 |
| 8 | `doc/test/evidence/v148/step3-v148-consistency-20260921.txt` | 证据 | 新增 |
| 9-22 | `doc/design/**`（14 项 v1.4.8 设计交付物） | 设计 | 修改（状态 → [Approved]） |
| 23-25 | `doc/audit/assessment/OpenBase-设计评估报告-v1.4.8.md`、`OpenBase-设计阶段自检记录-v1.4.8.md`、`doc/audit/review/OpenBase-阶段审计报告-Stage2-v1.4.8.md` | 审计 | 修改（状态 + 批准记录） |
| 26 | `.devflow/state.json` | 配置 | 修改 |

---

## 12. 产出物存在性验证

| 产出 | 存在 | 非空 |
|------|:----:|:----:|
| 设计开发追溯矩阵-v1.4.8 | ✅ | ✅ 66 行 / 7854 B |
| 派单分发清单-v1.4.8 | ✅ | ✅ 73 行 / 6252 B |
| 会话标识提交派单-openbase-ui-v1.0.0 | ✅ | ✅ 76 行 / 5022 B |
| DevLogReport-v1.4.8（本报告） | ✅ | ✅ |
| 开发审计移交材料-v1.4.8 | ✅ | ✅ |
| 阶段审计报告-Stage3-v1.4.8 | ✅ | ✅ |
| 证据文件 2 份 | ✅ | ✅ |

**验证方法**：文件系统清点（`Get-ChildItem` + 行数/字节数统计），输出见 `doc/test/evidence/v148/step3-v148-doc-inventory-20260921.txt`（TOTAL 22 / EMPTY 0）。

---

## 13. 跨仓直接实施登记（`VC-017` 后补记）

> **本节为 `VC-017`（约束反转）后的补记。** 原「本仓不实施 OpenLLM 侧代码改动，一律走跨仓派单」的施工约束已由用户决策「直接修改其他四仓」取消；v1.4.8 的 OpenLLM 侧改动由本会话**直接实施**并自测。§1「变更面约束」、§2 任务拆解、§3.3、§4、§7、§11 中「本仓无代码改动 / 无代码交付」的表述**以本节为准**。

### 13.1 实施批次与交付（八批）

| 批次 | 主题 | 关联 TD | 关键改动 | 证据文件（`doc/test/evidence/v148/`） |
|:----:|------|---------|----------|--------------------------------------|
| 1 | F-02 窗口匹配 + F-08 序号持久化 | TD-148-02、TD-148-06 | `context_manager` 最长键优先匹配；`WritebackQueue.next_seq`（`max_seq+1`），**删除进程内计数器** | `openllm-crossrepo-f02-f08-20260921.txt` |
| 2 | session_id 与会话轴接入 | TD-148-04 | `OpenLLMChatRequest.session_id`（可选）；`history.py` 历史构建；assembler 历史槽位；回写取真实会话标识 | `openllm-crossrepo-session-axis-20260921.txt` |
| 3 | 历史注入 + 双路径素材一致 | TD-148-03、TD-148-04 | 历史贯通 编排器→执行器→组装器；流式组装点同套素材；AST 护栏 | `openllm-crossrepo-history-injection-20260921.txt` |
| 4 | 共用组装步骤 + 第零段计量 | TD-148-03、TD-148-01 | `prompt_pipeline.build_prompt`（两路径共用）；`PromptComposition` 计量；**删除流式自建组装副本** | `openllm-crossrepo-shared-step-20260921.txt` |
| 5 | 第零段工装 2/3/4 | TD-148-01 | `context_metrics`：检索快照 / 回执 / 归因 A；同步路径落 `routing_trace` | `openllm-crossrepo-metrics-20260921.txt` |
| 6 | 流式回执 + 批量导出 | TD-148-01 | 流式路径落回执；`GET /openllm/v1/trace/metrics/export` + `extract_metrics_records` | `openllm-crossrepo-metrics-export-20260921.txt` |
| 7 | 三路回写接齐 | TD-148-05 | profile 第三路；流式三路回写（**F-09 闭环**）；回调返回 submit 结果 | `openllm-crossrepo-three-roads-20260921.txt` |
| 8 | 同步逐路回执 + 回执查询 | TD-148-05 | `ExecuteResult.writeback_receipt`；`WritebackStore.list_rows`；`GET /openllm/v1/writeback/receipts` | `openllm-crossrepo-receipts-20260921.txt` |
| 9 | 会话标识口径收尾 + 会话落库对齐 | TD-148-04 | `session_scope.py`（口径单一来源）；`conversation_service` 落库写入会话标识/口径 + 历史按会话筛选；`conversations` API 透传可选 `session_id`；网关回写与回执统一改用 `normalize_session_id` | `openllm-crossrepo-session-scope-20260921.txt` |
| 10 | **第零段工装 5/6/7**（归因 B 工具 / 固定集与评分表 / 汇总脚本） | TD-148-01 | `attribution_b.py`（去标识、打乱可还原、三标签解析、≥30 抽样、漏检率校准）；`golden_set.py` + `data/golden_set_v1.json`（35 条 / 7 场景 / 5 条每组 / 2 组负例 + 四维量表 + 记录模板）；`baseline_report.py`（WCR 三分 + 漏检率区间 + 判定三要素 + 不可判定） | `openllm-crossrepo-baseline-tooling-20260921.txt` |
| 11 | **前端会话标识提交（D2）** | TD-148-04、TD-148-14 | `openbase-ui/src/core/session.ts`（会话标识模块：读取/新建/重置/注入，sessionStorage + 内存兜底）；`openbase-ui/src/core/api/llm.ts`（`sendChat` / `sendChatStream` 经 `withSessionId` 注入可选 `session_id`） | `openbase-ui-session-id-20260921.txt` |
| 12 | **组件执行全链共用（双路径收敛收口）** | TD-148-03 | 新增 `component_pipeline.py`（共用组件执行步骤 + `ComponentRunResult`）；**同步路径删除私有 `_run_component`（81 行）**、流式路径删除私有 `_run_one` 与调度循环（约 60 行），两路径改调 `run_components` | `openllm-crossrepo-component-pipeline-20260921.txt` |
| 13 | **四仓 DevFlow 登记**（非代码批次） | TD-148-14 | 四仓 `state.json` 写入 `standaloneEntries`（**不推进各仓阶段状态**，遵循审计报告硬门禁）；出具登记文档 4 份（OpenLLM 实施记录 + 三仓契约登记回执单） | `crossrepo-devflow-registration-20260921.txt` |

### 13.2 跨仓改动清单（OpenLLM 仓）

**源文件 12 个（新增 3）**：

| # | 文件 | 性质 | 主要改动 |
|:-:|------|:----:|----------|
| 1 | `app/services/context_manager.py` | 修改 | F-02 最长键优先匹配 + `resolve_model_context_key` |
| 2 | `app/services/writeback_queue.py` | 修改 | `next_seq`（持久化序号）、`list_rows`（回执查询） |
| 3 | `app/api/openllm_gateway.py` | 修改 | seq/session_id/历史/回写标识/共用步骤/回执落库/三路回调/两个查询端点 |
| 4 | `app/edgerouter/orchestration/assembler.py` | 修改 | 历史槽位（模板 + `history_ctx` 入参） |
| 5 | `app/edgerouter/orchestration/history.py` | **新增** | 历史素材构建（窗口截取） |
| 6 | `app/edgerouter/orchestration/prompt_pipeline.py` | **新增** | 共用组装步骤 + `PromptComposition` 计量 |
| 7 | `app/edgerouter/orchestration/context_metrics.py` | **新增** | 工装 2/3/4（检索快照 / 回执 / 归因 A）+ 批量提取器 |
| 8 | `app/edgerouter/orchestration/executor.py` | 修改 | 历史注入、共用步骤、`composition`、三路回写、`writeback_receipt` |
| 9 | `app/edgerouter/orchestration/explicit.py` | 修改 | `history_ctx` / `profile_writeback` 透传 |
| 10 | `app/edgerouter/orchestration/auto.py` | 修改 | 同上 |
| 11 | `tests/unit/conftest.py` | 修改 | 环境缺陷修复（pgAdmin/.pylib 由首位遮蔽改为末位兜底） |
| 12 | `app/services/session_scope.py` | **新增** | 会话标识口径单一来源（归一化 / 记账口径 / 元数据构造） |
| 13 | `app/services/conversation_service.py` | 修改 | `send_message` 写入会话标识与记账口径；`get_conversation_history` 按会话标识筛选（缺省不过滤） |
| 14 | `app/api/conversations.py` | 修改 | 消息发送 / 历史查询端点透传**可选** `session_id`（缺省兼容） |
| 15 | `app/edgerouter/orchestration/attribution_b.py` | **新增** | 工装 5：归因 B 工具（去标识 / 打乱可还原 / 判定解析 / 抽样 / 漏检率校准） |
| 16 | `app/edgerouter/orchestration/golden_set.py` | **新增** | 工装 6：固定集加载校验 + 四维评分量表 + 记录模板 |
| 17 | `app/edgerouter/orchestration/baseline_report.py` | **新增** | 工装 7：基线指标汇总 + 报告骨架渲染 |
| 18 | `data/golden_set_v1.json` | **新增**（数据资产） | 固定集：35 条 / 7 场景 / 每组 5 条 / 2 组负例 |
| 19 | `app/edgerouter/orchestration/component_pipeline.py` | **新增** | 共用组件执行步骤（条目解析 / 串并行调度 / 组件级降级 / RAG 回退 / 上下文格式化 / 耗时） |
| 20 | `app/edgerouter/orchestration/executor.py` | 修改 | 同步路径改调共用步骤，**删除私有 `_run_component`** |
| 21 | `openbase-ui/src/core/session.ts` | **新增** | 前端会话标识模块（读取 / 新建 / 重置 / 注入；`sessionStorage` + 内存兜底） |
| 22 | `openbase-ui/src/core/api/llm.ts` | 修改 | `sendChat` / `sendChatStream` 请求体注入**可选** `session_id` |
| 23 | 测试文件 15 个（后端）+ 1 个（前端） | 新增 13 + 1 / 修改 2 | 见下 |

**测试文件 15 个（后端，新增用例 142 个）**：`test_context_manager_model_window.py`(8)、
`test_writeback_seq_persistence.py`(3)、`test_session_axis_gateway.py`(7)、
`test_session_axis_assembler.py`(5)、`test_session_axis_history.py`(8)、
`test_session_axis_prompt_injection.py`(6)、`test_prompt_pipeline_shared_step.py`(9)、
`test_context_metrics_instrumentation.py`(25)、`test_writeback_three_roads.py`(9)、
`test_writeback_receipts.py`(10)、`test_session_scope_alignment.py`(10)、
`test_attribution_b_tool.py`(13)、`test_golden_set_and_scale.py`(7)、`test_baseline_report_tool.py`(7)、`test_component_pipeline_shared.py`(13)。
**前端（openbase-ui）测试文件 1 个（新增用例 6 个）**：`tests/session-id.spec.ts`(6)。

### 13.3 跨仓静态质量与验证

| 项 | 结果 |
|----|------|
| 后端单元用例 | **151 passed**（16 个测试文件，`--confcutdir=tests/unit`；**含 Step 4 首轮补齐的会话筛选分支 4 例**） |
| **前端单元用例（openbase-ui）** | **204 passed**（19 个测试文件，含本批 6 例）；`vue-tsc --noEmit` **0 errors** |
| 语法编译 | `py_compile` 0 错误（全部改动源文件） |
| 静态检查 | ruff 对本批新增/改动文件 `All checks passed!`（含修复历史遗留 F821 与新增 B905） |
| 环境缺陷修复 | 单元套件收集期 DLL 失败（`test_openllm_gateway.py` 28 errors）→ 修复 conftest 路径遮蔽后归零 |
| 硬判据 | F-08 回归用例断言「重启后首序号续接历史最大值」「重启后首回写未被静默丢弃」 |

### 13.4 跨仓逻辑审查与过程偏差（如实登记）

| 项 | 说明 |
|----|------|
| 逻辑审查方式 | 以**单元用例 + 源码级护栏（AST/字符串）**替代文档等价评审：双路径素材齐备、共用步骤调用、网关禁自建副本、两路径均落回执等均有护栏用例 |
| 过程偏差 1 | 第六批 8 例新用例与实现同批提交，**未单独观察 RED**（已在证据文件登记） |
| 过程偏差 2 | 第四批引入的 `PromptComposition` 字符串注解未导入（ruff F821），第八批修复（`TYPE_CHECKING` 惰性导入） |
| 过程偏差 3 | 编辑过程中曾误删 `ExecuteResult.raw_results` 字段与 `max_seq` docstring 首行，均在下一处编辑前发现并立即修复，未进入测试环节 |
| 测试用例契约漂移 | 回调由 3 元组扩为 4 元组后，第二批 2 例按旧契约解包，已同步适配 |
| 降级错误项键名 | 第十二批用例初写 `errors[0]["reason"]`，与既有契约 `{"component","error"}`（`_record_issue`）不一致 → **以既有契约为准**改用 `error`，未改产品键名 |
| **语义变更（第十二批）** | 流式路径「**RAG 适配器未注册**」由「回退内置 RAG」改为「组件级降级（不触发回退）」：理由为适配器未注册属装配缺陷，且同步路径从不因该情况回退，统一后才满足 AC-148-03-1 的「两路径行为一致」。**回归 147 例全绿，无既有用例依赖旧语义** |
| 一次工具失败尝试 | 第十二批 executor 首次替换因定位偏差未命中（search content not found），重新读取后按实际内容替换，未产生半成品改动 |

### 13.5 未完成（跨仓口径）

1. 第零段工装 5/6/7（归因 B 工具 / 固定集与评分表 / 汇总脚本）。
2. R3（流式回写可行性）端到端实测（真实上游 + 真实队列 + 重启对照），属 Step 4 范围。
3. 「被丢弃项标识」未落回执（当前无丢弃逻辑，属 v1.4.9 第二批裁剪范畴）。
4. `conversations.py` 会话消息落库与检索对齐会话标识口径。
5. openbase-ui 会话标识提交（D2）。
6. 四仓各自 DevFlow 登记（state.json / DevLogReport / 追溯矩阵）。

### 13.6 四仓 DevFlow 登记（批次 13）

按《DevFlow 阶段管理器》**独立模式**登记，**不修改**任何仓的 `currentPhase` / `completedPhases`（审计报告硬门禁：跨仓施工无对应 Stage 审计报告，不得推进各仓阶段）。

| 仓 | 角色 | 代码改动 | `state.json` 条目 | 登记文档 |
|----|------|:--------:|-------------------|----------|
| OpenLLM | **实施方** | 19 源文件 + 1 数据资产 + 15 测试文件 | `standaloneEntries.step_3_OpenBase_v1.4.8` | `doc/development/OpenLLM-R396-R398-会话编排前置与回写闭环-DevLogReport-v1.0.0.md`（75 行） |
| OpenMemory | 契约方（未被施工） | 0 | `standaloneEntries.cross_repo_OpenBase_v1.4.8` | `doc/development/OpenMemory-v1.4.8-跨仓契约登记-回执单-v1.0.0.md`（41 行） |
| OpenRAG | 契约方（未被施工） | 0 | 同上 | `doc/development/OpenRAG-v1.4.8-跨仓契约登记-回执单-v1.0.0.md`（42 行） |
| DPS | 契约方（**新增画像回写第三路接收方**） | 0 | 同上 | `doc/development/DPS-v1.4.8-跨仓契约登记-回执单-v1.0.0.md`（42 行） |

- 各仓登记前阶段（**均未变更**）：OpenLLM `step_5_deployment_closed`（2.15.0，已闭环）；OpenMemory `step_0_version_planning`（2.14.0）；OpenRAG `step_4_testing`（2.10.0）；DPS `step_5_operations`（2.15.0）。
- 核验：四仓 `state.json` 经 `ConvertFrom-Json` 全部 **VALID**；4 份登记文档存在且非空。
- 如实登记的限制：三仓回执单中的契约描述源自 OpenLLM 侧已实施代码与 OpenBase 文档，**未逐条核对三仓实际端点实现**（属联调/Step 4 范围），故统一声明为「登记假设」。

## 14. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-21 | AD-OpenBase-Dev | 初始创建。登记 Step 3 开发（本仓侧：设计契约 + 跨仓派单 + 开发记录）：入场检查（Step 1/2 全通过）、8 项任务拆解与追溯、文档型实现、静态质量等价检查（含技术债务增长率 0/0/0%）、实际运行验证 L1/L2/L3（TOTAL 22 / EMPTY 0）、开发自测、文档逻辑审查（11 维通过）、变更一致性自检（review_left_count=0）、技术债务与风险归集检查（无新增，TD-新增-022/023 承载）、测试移交说明、变更统计与影响文件清单、产出物存在性验证。状态 [Review] |
| v1.1.0 | 2026-09-21 | AD-OpenBase-Dev | **按 `VC-017`（约束反转）补记跨仓直接实施**：新增 §13「跨仓直接实施登记」（八批交付与关联 TD、跨仓改动清单 12 源文件 / 10 测试文件、静态质量与验证 99 passed、逻辑审查方式与四项过程偏差、未完成项）；修正 §1 变更面约束、§4 / §7 前置说明、§11.2 分类统计（新增跨仓代码 3/9 与测试代码 10/2，合计 21/30）中「本仓无代码交付」的失效表述；原 §13 修订历史顺延为 §14。状态 [Review] |
| v1.2.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第九批（会话标识口径收尾 + 会话落库对齐）**：§13.1 增批次 9；§13.2 源文件清单扩为 15 个（新增 `services/session_scope.py`；修改 `services/conversation_service.py`、`api/conversations.py`），测试文件 11 个 / 新增用例 100 个；§13.3 跨仓用例 **109 passed**。状态 [Review] |
| v1.3.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十批（第零段工装 5/6/7）**：§13.1 增批次 10；§13.2 新增 `attribution_b.py` / `golden_set.py` / `baseline_report.py` 与数据资产 `data/golden_set_v1.json`（源文件 18 个、测试文件 14 个 / 新增用例 125 个）；§13.3 跨仓用例 **134 passed**；登记 2 处「测试本身」的修正（漏检率期望值、还原映射断言）。状态 [Review] |
| v1.4.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十一批（前端会话标识提交 D2）**：仓库位置经用户确认为本仓 `openbase-ui/`；§13.1 增批次 11；§13.2 新增 `openbase-ui/src/core/session.ts`、修改 `openbase-ui/src/core/api/llm.ts`；§13.3 增前端验证行（**204 passed** / `vue-tsc` 0 errors）。状态 [Review] |
| v1.5.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十二批（组件执行全链共用，TD-148-03 收口）**：§13.1 增批次 12；§13.2 新增 `component_pipeline.py`、修改 `executor.py`（删除私有 `_run_component`）与网关流式路径（删除私有 `_run_one` 与调度循环）；§13.3 后端用例 **147 passed**（16 文件）；§13.4 登记 1 项**语义变更**（RAG 适配器未注册 → 降级而非回退）与 1 次工具失败尝试。状态 [Review] |
| v1.6.0 | 2026-09-21 | AD-OpenBase-Dev | **补记第十三批（四仓 DevFlow 登记）**：§13.1 增批次 13；新增 §13.6「四仓 DevFlow 登记」（独立模式、不推进各仓阶段状态；四仓 `state.json` 写入 `standaloneEntries`；登记文档 4 份，行数 75/41/42/42 实测）；登记证据 `crossrepo-devflow-registration-20260921.txt`。状态 [Review] |
| v1.7.0 | 2026-09-21 | AD-OpenBase-Dev | **按 Step 4 首轮补齐结果更新计数**：`tests/unit/test_session_scope_alignment.py` 追加「会话历史按会话标识筛选」4 例（覆盖率补齐），§13.3 后端用例 **147 → 151 passed**、§13.2 新增用例 **138 → 142 个**；该文件增量行覆盖 37.5% → 100%，见《OpenBase-测试报告-v1.4.8》v1.2.0 §6.1。状态 [Review] |