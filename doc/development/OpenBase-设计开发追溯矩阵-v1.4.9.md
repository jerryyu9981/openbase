# OpenBase 设计开发追溯矩阵 - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（编排与回写代码所在仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量） |
| 文档 | 设计开发追溯矩阵（Step 3 产出 2，TD-ID ↔ 设计项 ↔ 代码落点） |
| 文档版本 | v1.9.5 |
| 状态 | [Review]（Step 3 收尾，待人工批准后进入 Step 4） |
| 日期 | 2026-09-29 |
| 上游依据 | 设计基线 **v1.2.0**（[Approved]）＋ 设计补充至 **v1.6.3**；《需求设计追溯矩阵-v1.4.9》v1.2.0 |
| 代码仓 | `d:\Trae CN\myproject\Dev\OpenLLM\backend`（OpenBase 仓仅承载文档） |

## 1. TD-ID 追溯（设计项 → 代码落点 → 状态）

| TD-ID | 设计项（DT） | 需求 | 代码落点（OpenLLM） | 判据 | Phase | 状态 |
|-------|-------------|------|---------------------|:----:|:-----:|:----:|
| **TD-14901** | DT-149-03（回执扩展）／I-3 显式标记 | FR-149-06 | `app/edgerouter/orchestration/prompt_pipeline.py`（`_trim_segment` 报告 ＋ 文档同步） | **AC-149-03/04** | P1 | ✅ **已完成（本批）** |
| TD-14902 | DT-149-03（回执扩展）／I-2 逐条丢弃原因 | FR-149-06 | `prompt_pipeline.py`（`segment_items` 透传 ＋ `dropped` 明细 ＋ 单元三元组）＋ `context_metrics.py`（顶层 `dropped` ＋ **预算四项 ＋ 裁剪前后 token ＋ 聚合标记导出**，批次 7 补齐）＋ **批次 8 生产落线：`assembler.py`（`format_context_with_items` 同源产出身份）／`component_pipeline.py`（落 `segment_items`）／`executor.py` 与 `api/openllm_gateway.py`（双路径同口径传入）** | AC-149-05 | P1 | ✅ **已完成（批次 2 收尾 ＋ 批次 7 齐备率补齐 ＋ 批次 8 生产落线）** |
| TD-14903 | DT-149-01／I-1 跨段配额竞争 | FR-149-03 | `prompt_pipeline.py`（预算池）＋ `BudgetPolicy` | AC-149-01/02 | P2 | ✅ **已完成（批次 2）** |
| TD-14904 | DT-149-02／I-5 仍超窗显式失败标记 | FR-149-05 | `prompt_pipeline.py`（`_verify_window` 二次校验 ＋ 三标记）＋ `context_metrics.py`（标记导出） | **AC-149-12** | P2 | ✅ **已完成（批次 3）** |
| TD-14905 | DT-149-15／I-6 取数层逐组件通道路由 | FR-149-09 | `component_pipeline.py`（逐组件裁决/标签/回写）＋ `channel.py`（逐组件状态）＋ `executor.py`/网关（轨迹落痕） | AC-149-13 | P5 | ✅ **已完成（批次 4）** |
| TD-14906 | DT-149-16／I-7 审计动作码定稿 | FR-149-10 | `channel_audit.py`（定稿 ＋ 组件级事件）＋ 网关调用点 | AC-149-14 | P5 | ✅ **已完成（批次 4）** |
| TD-14907 | DT-149-17／I-8 画像增量与频控预检接线 | FR-149-11 | `evaluate.py`（两条公开预检）＋ `profile_refine_gate.py`（启动注入位）＋ `writeback_queue.py`（补齐缺失依赖）＋ 网关回写回调 ＋ `main.py` lifespan | AC-149-15 | P6 | ✅ **已完成（批次 5）** |
| TD-14908 | DT-149-18／I-9 评测集与判据扩展 | FR-149-12 | `doc/test/evidence/cr149/`（`v149-increment-eval-set.json` ＋ `v149_increment_runner.py` ＋ `-result.json`） | AC-149-16 | P6 | ✅ **已完成（批次 6）** |
| TD-14909 | DT-149-19／I-10 重排器条件项 | FR-149-13 | 仅登记（无代码变更） | AC-149-17（条件） | — | ✅ **按设计不实施** |

## 2. Subtask CheckList（文件级；命名与设计规划一致）

| # | 文件 | 操作 | 命名与设计一致 | 状态 |
|:-:|------|------|:--------------:|:----:|
| 1 | `app/edgerouter/orchestration/prompt_pipeline.py` | 修改（`_trim_segment` 报告 ＋ docstring） | ✅（设计 §3.6／API §2 指向该模块） | ✅ 完成 |
| 2 | `tests/unit/test_context_trim_markers.py` | **新建** | ✅（测试命名遵循仓内 `test_context_*` 约定） | ✅ 完成 |
| 3 | `prompt_pipeline.py` 预算池（跨段竞争）＋ `tests/unit/test_context_cross_segment_competition.py` | 修改／**新建测试** | ✅ | ✅ 完成（批次 2） |
| 4 | `component_pipeline.py` ＋ `channel.py`（取数层路由） | 修改 | ✅ | ✅ 完成（批次 4） |
| 5 | `channel_audit.py`（动作码定稿） | 修改 | ✅ | ✅ 完成（批次 4） |
| 6 | `tests/unit/test_context_dropped_detail.py` | **新建** | ✅（沿用仓内 `test_context_*` 约定） | ✅ 完成（批次 2 收尾） |
| 7 | `context_metrics.py`（顶层 `dropped` 导出） | 修改 | ✅（设计 §3.16 两级落点） | ✅ 完成（批次 2 收尾） |
| 8 | `tests/unit/test_context_over_window_verifier.py` | **新建** | ✅（沿用仓内 `test_context_*` 约定） | ✅ 完成（批次 3） |
| 9 | `tests/unit/test_component_channel_routing.py` ＋ `test_channel_audit_action_codes.py` ＋ `test_component_channel_audit_wiring.py` | **新建** | ✅（沿用仓内 `test_component_*` / `test_channel_*` 约定） | ✅ 完成（批次 4） |
| 10 | `executor.py`（通道标签上抛）＋ `core/config.py`（`COMPONENT_CHANNEL_ROUTING_ENABLED`）＋ 网关（裁决器/轨迹/审计调用点） | 修改 | ✅ | ✅ 完成（批次 4） |
| 11 | `tests/unit/test_profile_delta_and_precheck_wiring.py` | **新建** | ✅（沿用仓内 `test_*` 约定） | ✅ 完成（批次 5） |
| 12 | `evaluate.py`（两条公开预检）＋ `profile_refine_gate.py`（启动注入位）＋ `writeback_queue.py`（补齐 `compute_message_hash`/`exists_message`）＋ 网关回写回调 ＋ `main.py` lifespan | 修改 | ✅ | ✅ 完成（批次 5） |

> **无新增/重命名/删除文件未落地项被隐藏**：已落地新建测试文件为 **10 个**（批次 1：`test_context_trim_markers.py`；批次 2：`test_context_cross_segment_competition.py`、`test_context_dropped_detail.py`；批次 3：`test_context_over_window_verifier.py`；批次 4：`test_component_channel_routing.py`、`test_channel_audit_action_codes.py`、`test_component_channel_audit_wiring.py`；批次 5：`test_profile_delta_and_precheck_wiring.py`；**批次 7：`test_context_receipt_fields.py`；批次 8：`test_segment_items_production_wiring.py`**），其余均为既有文件修改（含 1 项既有护栏随定稿更正）；后续批次项已在上表逐项标注批次。
>
> **Step 3 文档交付物（非代码，对照 `coding-stage-execution` §3.10 与 `project-document-management` 阶段 3）**：`DevLogReport`／`设计开发追溯矩阵`／`静态质量检查记录`／`代码逻辑审查记录`／**`开发审计移交材料`**／**`测试移交说明`** —— 均已产出（后两项为独立文件，见 `doc/development/`）。

## 3. 本批实施记录（批次 1＝I-3）与推迟说明

**已完成**：
- `_trim_segment` 段报告新增 **`hard_truncated`**（恒有：本段是否发生文本级截断）与 **`degraded="empty_guard"`**（仅在**保底一条被触发**时出现，即该段本会被裁剪清空 ⇒ 显式降级）；`report` 类型标注随值域扩展；模块 docstring 同步（文档-实现一致）。
- **零变化保证**：无需裁剪时报告**仍缺失**（`composition.truncated` 无该段）⇒ 与既有实现逐字一致。
- **不误报**：整条丢弃（`truncated_items=0`）时 `hard_truncated=False` 且**不出现** `degraded` 键。

**推迟说明（如实）**：**I-2（逐条丢弃原因明细 `dropped[{source,id,reason}]`）本批未做** —— 原因：`_trim_segment` 当前只接触**文本单元**（`(编号前缀, 正文)`），**不持有条目身份**（source/id/score）；要让「原因明细」成立必须先**从取数层把条目元数据透传进段内裁剪**（属管道改造，非观测增量）。⇒ 按「先做最小可验证增量」原则，I-2 顺延至**批次 2 前置**（与 I-1 同批或紧前），并已在 TD-14902 标注。

## 3bis. 批次 2 前置定位（2026-09-28，本批续记）

**① I-3 第三标记 `enabled`：结论＝无需新增字段（已收口）**
- 代码事实：`ContextReceipt.to_record()` 仅在 `composition.budget` **非空**时导出 `budget` 段落（`context_metrics.py` 第 95~98 行）；而 `budget` 恰在**预算/裁剪生效**时按 `QUOTA_SEGMENTS` 逐段落入（`prompt_pipeline.build_prompt` 第 660~671 行），关闭时该 dict 为空 ⇒ **`budget` 段落的出现与否已等价表达开关状态**。
- 处置：**取消新增 `enabled` 字段**（同义字段属重复造字段），并把该语义写入设计文档。

**② I-2（逐条丢弃原因明细）：前置＝先补设计（上游契约变更），不得以代码隐式改契约**
- 代码事实：`_trim_segment(segment, text, *, policy, count_tokens)` **只接收已渲染文本**（`prompt_pipeline.py` 第 499~505 行）；其内部用 `_parse_items(text)` 还原 `(编号前缀, 正文)` 二元组 ⇒ **条目身份（source/id/score）在进入裁剪前已丢失**；上游 `segments` 亦为 `{段: 文本}`（第 660~668 行）。
- 影响面：要产出 `dropped[{source,id,reason}]`，必须让 `build_prompt` 的 `segments` **并行携带条目元数据**，并由**网关侧**（取数层）提供身份 —— 属**跨模块契约变更**，会触及调用方。
- 处置（按 Step 3 规则 2「不得以代码实现替代设计确认」）：**先在 Step 2 设计侧补一条接口约定/ADR**（`segments` 携带元数据的最小形态与缺省兼容），评审后再实施；本批**不写未经验证的契约改造代码**。

## 3ter. 批次 2 实施记录（I-1 跨段竞争池，2026-09-28 续记）

**已完成**：
- `BudgetPolicy` 新增 **`cross_segment_competition_enabled`**（**默认 False**；`load_budget_policy` 对应 `CONTEXT_CROSS_SEGMENT_COMPETITION_ENABLED`）⇒ 关闭时与既有实现**逐字一致**。
- `apply_context_budget` 末尾新增**竞争池**：`pool = min(available − Σ used, Σ dropped_tokens)`（**硬上界**，T1 结构性不破）→ 逐段按放大后的配额重跑**同一套** `_trim_segment` 回填 → 观测落 `budget.<段>.competition_filled` 与 `truncated.<段>.refilled_items`；任何异常按 **fail-safe「视为未启用」** 处理并标记 `degraded="competition_skipped"`。
- **取消配额旁路参数** `_trim_segment(..., quota_override=...)`（经全仓检索**无任何调用方** ⇒ 死参数）：回填一律以「放大该段比例」单一口径表达，避免两套配额表述破坏 T1/T2 同源性（设计 §3.15②）。
- 新增测试 `tests/unit/test_context_cross_segment_competition.py`（**先建后改**，TDD）。

**根因定位（如实，含两类缺陷）**：
| # | 缺陷 | 性质 | 证据 | 处置 |
|:-:|------|------|------|------|
| ① | 测试夹具：history 8 行**正文完全相同**（仅序号不同）⇒ 段内**去重先于配额**丢掉 7 条，池内**根本没有「配额丢弃」可回填**（`dropped_items=7` 全为质量规则丢弃） | **测试缺陷** | 直调 `_trim_segment` 在 `quota=190/610/2000` 三档下**返回完全相同**（`used=63, dropped=7`）⇒ 丢弃与配额无关 | 夹具改为逐行正文不同；并把该语义固化为**新护栏用例** `TestQualityDropsAreNotReclaimed` |
| ② | 生产代码：回填后 `_trim_segment` 返回**空报告**（放宽后已无丢弃）时，`new_report.get("dropped_items")` 抛 `AttributeError`，被 fail-safe **静默吞掉** ⇒ 现象为「池已到达（实测第三次调用配额 190→550、`used` 127→511）但结果不变」 | **实现缺陷** | 插桩看到 `degraded='competition_skipped'` 与 `'NoneType' object has no attribute 'get'` | 改为 `(new_report or {})`，并澄清观测口径为**最终状态**（§3.15③） |

> **更正前一记录**：上一轮排障中出现的 `local variable 'pool' referenced before assignment` **并非模块缺陷**，系**探针自身插桩**造成（探针在 `try` 外引用了 `pool`）⇒ 该线索作废，不作为缺陷登记。

**批次边界（如实）**：**I-2（逐条丢弃原因明细）仍待做** —— 本批已完成其**设计前置**（架构 §3.13 条目元数据最小契约）与 **I-1 落地**，I-2 的代码改造（`segment_items` 透传 ＋ 5 个丢弃点携带原因）进入**批次 2 收尾**（下一动作）。

## 3quater. 批次 2 收尾实施记录（I-2 逐条丢弃原因明细，2026-09-28 续记）

**已完成**：
- `_trim_segment` 新增可选 `items`（条目元数据，**只读**）→ 段级观测新增增量字段 **`dropped: [{source,id,reason}]`**；单元内部表示升为**三元组** `(编号前缀, 正文, 身份或 None)`（`_merge_adjacent_synonyms`/`_profile_drop_order`/`_drop_empty_profile_sections`/`render` 同步；三者均**仅**本模块内部使用，无外部调用方）。
- `apply_context_budget(..., segment_items=...)` 与 `build_prompt(..., segment_items=...)` 透传身份；`PromptComposition` 新增顶层 **`dropped`**，由段级明细按 `QUOTA_SEGMENTS` 段序**展平**；`ContextReceipt.to_record()` 导出顶层 `dropped`（**恒有**，`[]` 兜底）⇒ **AC-149-05 齐备率 100%**。
- 设计前置：架构 **§3.16（设计补充 C）** 冻结原因码取值域、两级落点、排序与字段存在性（v1.5.0）。

**根因/缺陷记录（如实）**：
| # | 项 | 性质 | 处置 |
|:-:|----|------|------|
| ① | **口径缺陷（既有实现，非本批引入）**：②' 画像字段级预丢项被③配额阶段**重复计数**（两者复用同一 `popped`）⇒ `dropped_items`/`dropped_tokens` 在「字段级预丢生效」时**翻倍** | 实现缺陷（既有断言均为 `>= 1` 故未被发现） | 配额阶段改用**独立** `quota_popped`；保底候选按「配额阶段优先、字段级兜底」取用；新增**精确计数**护栏（`test_profile_field_drop_reason_and_exact_count`） |
| ② | 排序在编期调整：初版按**弹出顺序**（自尾部）落 `dropped` ⇒ 回执可读性差 | 观测口径编期收敛（未改任何取舍） | 冻结为「**处置阶段先后 + 阶段内段内呈现序**」，同步写入设计 §3.16 |
| ③ | 段级 `dropped` 与 I-3「无裁剪 ⇒ 报告缺失」潜在冲突 | 契约边界澄清 | 冻结：**完全未裁剪 ⇒ 段级报告整体缺席**（但顶层 `dropped` 仍为 `[]`）⇒ 两条不变量同时成立 |

**批次 2 收官状态**：I-1 ✅ ＋ I-2 ✅ ⇒ 批次 2 **全部完成**；下一动作＝**批次 3（I-5 仍超窗显式失败标记 / TD-14904）**。

**本批测试**：`test_context_dropped_detail.py` **先建（RED 10 failed / 1 passed）→ 实现后 GREEN 12 passed**；与 I-1/I-3 双护栏合跑 **22 passed**；相关面 14 文件 **238 passed**；`ruff` 全绿。

## 3quinquies. 批次 3 实施记录（I-5 仍超窗显式失败标记，2026-09-28 续记）

**已完成**：
- `build_prompt` 组装后新增**二次校验**（`_verify_window`）：`prompt_total_tokens > window_tokens` ⇒ **超窗**；校正**至多一次**（按 `Σratio(有素材的段)` 反算收紧额度并并入输出预留，**实减**素材预算后重组装）；仍超窗 ⇒ 置 `over_window`/`over_window_tokens` 并记 **ERROR**（**不静默**）。
- 观测：`PromptComposition.over_window` / `over_window_tokens` / `over_window_recovered` **三字段恒有**；`ContextReceipt.to_record()` 同步导出（AC-149-12「实测统计」依据）。
- 组装顺序调整：`render → 二次校验 → refine 观测/分项计量` ⇒ 校正后的 `segments` 才是「最终状态」，三类观测**同源**（不再出现「refine 记首次、计量记校正后」的不一致）。
- 设计前置：架构 **§3.17（设计补充 D，v1.6.0）** 冻结判定口径、校正次数、失败表达方式（**不新增对外错误码**）与层级区分。

**编期决策（如实登记，均已回写设计 §3.17）**：
| # | 决策点 | 结论 |
|:-:|--------|------|
| ① | 校正额度是否直接并入输出预留 | **否**：配额＝`available × ratio`，直接并入 `overflow` 会**欠校正**（实测 history-only 场景仅回收 ≈19%）⇒ 改为按 `overflow / Σratio` 反算 |
| ② | 可用预算不足以吸收溢出时 | **直接判失败**，不做校正 —— 因 `quota=0` 语义为**不限（不裁剪）**，强行收紧会「越校正越宽」 |
| ③ | 是否新增错误码中断请求 | **否**（API §1「本版本不新增对外错误码」）⇒ 失败以**回执标记**表达，并按 AC-149-12 计入超窗率 |
| ④ | 标记字段层级 | **Prompt 级**新字段，**不**复用段级 `degraded`（后者语义为裁剪降级） |

**本批测试**：`test_context_over_window_verifier.py` **先建（RED 7 failed / 3 passed）→ GREEN 11 passed**；四护栏合跑 **33 passed**；相关面 16 文件 **269 passed**；`ruff` 全绿。

## 3sexies. 批次 4 实施记录（I-6 逐组件通道路由 ＋ I-7 审计动作码定稿，2026-09-28 续记）

**已完成（I-6）**：
- `channel.py`：新增**逐组件**状态与裁决 —— `record_component_outcome`（失败累加 / 成功清零）/ `component_switched` / `resolve_component_channel`（**永不抛出**）/ `component_channels()` 视图；**与请求级 `_b_consecutive_failures` 完全隔离**（单组件故障不放大为全链路切换）。
- `component_pipeline.py`：`ComponentRunResult` 新增 `channels` / `channel_sources`；取数**前**逐组件裁决并把标签经 `_channel` 下发给取数方；调用后**按组件**回写成败；新增门控默认裁决器 `_default_channel_router()`（`COMPONENT_CHANNEL_ROUTING_ENABLED` 默认关闭 ⇒ 不裁决/不注入/不落痕）。
- 接线与观测：`executor.ExecuteResult` 上抛通道标签 → `routing_trace["components"].per_component_channels`（同步路径）；流式路径组合同口径落痕（AC-149-13③）。
- **边界（设计 §3.18）**：本仓**不**切换出站拓扑（`X-Proxy-Source` 恒为编排侧身份）⇒ 不破坏 K07 与 AB 等价契约。

**已完成（I-7）**：
- `channel_audit.py`：动作码 `channel_failover_b_to_a` **由暂定转定稿**（移除 `ACTION_PROVISIONAL_NOTE`）；新增组件级 `channel_component_failover`；新增 `AUDIT_ACTION_CODES` 作为**检索口径单一事实源**；新增 `build_component_failover_record` / `emit_component_failover_audit`（`detail` 记 `component` 维度）；统一投递路径 `_emit`（门控 / `no_loop` / fail-open 语义不变）。
- **调用点**（避免「有能力零调用点」）：网关 `_emit_component_switch_audit` 在 `_note_component_channel_health` 内投递，**同故障期每组件只投递一次**（恢复后自动复位）。
- 既有护栏 `test_channel_failover_audit.py::test_action_code_is_declared_provisional` **随定稿更正**为 `test_action_code_is_finalized`（口径变更，非绕过）。

**本批测试**：`test_component_channel_routing.py`（RED 12 failed → GREEN 12）＋ `test_channel_audit_action_codes.py`（RED 9 failed → GREEN 9）＋ `test_component_channel_audit_wiring.py`（接线护栏 4）⇒ 相关面 15 文件 **202 passed**；`ruff` 全绿。

## 3septies. 批次 5 实施记录（I-8 画像增量与频控预检接线，2026-09-28 续记）

**已完成（两条**只接线**，门控三条件不变）**：
- **画像增量**：`evaluate.profile_delta_precheck`（公开入口）→ 网关回写回调在 **profile 路**携带提炼增量，**契约键为 `updates`**（`_profile_writeback_updates` 读 `kwargs["updates"]` ⇒ **嵌套挂载**，不平铺）；门控未就绪 / 无增量 ⇒ **不新增载荷键**（零变化）。
- **频控/去重预检**：`evaluate.message_precheck`（公开入口）→ 网关回写回调在入队**前**预检「同消息已存在」⇒ 命中即 `skipped`；**fail-open**（存储异常按未命中）。
- **提炼器注入位接线**：新增 `profile_refine_gate.install_profile_refine_on_startup()`（fail-open、幂等），并在 **`backend/main.py` lifespan** 调用 —— 此前 `install_profile_refiner_if_enabled` **全仓零调用点**（「有能力但零调用点」）。

**缺陷发现与补齐（如实登记；由「接线」暴露）**：
| # | 缺陷 | 性质 | 证据 | 处置 |
|:-:|------|------|------|------|
| ① | `evaluate._message_exists` 依赖的 `writeback_queue.compute_message_hash` **不存在** ⇒ 该预检一旦接线即 `ImportError` | **既有实现缺陷**（零调用点掩盖） | `python -c "from app.services.writeback_queue import compute_message_hash"` ⇒ `ImportError` | 补齐 **`compute_message_hash`**（纯函数，六段 `U+241F` 分隔的 sha256） |
| ② | 同处依赖的 `WritebackStore.exists_message` **不存在**（且表结构**无内容哈希列**） | **既有实现缺陷**（同上） | `WritebackStore` 方法清单无该方法 | 补齐 **`exists_message(...)`**：**不改表结构**，以**有界回看**（最近 `MESSAGE_PRECHECK_LOOKBACK=200` 行）＋进程内指纹比对实现；**只读 / fail-open** |
| ③ | 编期自测发现：增量若**平铺**进载荷，画像路契约键 `updates` 取不到（`person` 变顶层键） | 编期缺陷（本批自纠） | 探针实测载荷 `{... 'person': {...}}`（缺 `updates`） | 改为 `{"updates": <增量>}` 嵌套挂载 |

**边界（如实登记）**：① 频控预检为**有界**去重（回看窗口外不拦截），**强幂等仍由队列 `UNIQUE(session_id, seq, target)` 兜底**；② 画像 LLM 提炼的真正生效需评测支撑（受 **D3**），本版只交付**接线**（默认纯规则路径）。

**本批测试**：`test_profile_delta_and_precheck_wiring.py` **先建（RED 11 failed / 2 passed）→ GREEN 13 passed**（含启动接线**结构护栏**）；相关面 8 文件 **134 passed**；`ruff` 全绿。

## 3octies. 批次 6 实施记录（I-9 评测集与判据扩展，2026-09-28 续记）

**已完成**（落点＝`doc/test/evidence/cr149/`，与既有证据体系同构）：
- **判据样本集** `v149-increment-eval-set.json`（v1.0.0）：I-1／I-2／I-3／I-5／I-6／I-7／I-8 **七项离线用例**（各带 `ac` 判据号、样本、期望），**外加** `runtime_pending` 四项（I-4 跨仓 D4、I-1-runtime、I-8-runtime 受 D3、I-6-runtime 跨仓通道归属），**逐项标注 `not_covered=true` 并给出所需运行态输入**。
- **执行器** `v149_increment_runner.py`：加载并结构校验样本集 → 逐项执行 → 输出**样本/期望/实际/问题列表**，并输出 `-result.json`；`--self-check` 可单独做结构自检；**存在失败项即非 0 退出码**。
- 实测：**离线用例 7/7 通过**；运行态 **4 项未覆盖**（如实标注，不以夹具结论冒充运行态结论）。
- 附带修正（由本批判据暴露）：`evaluate.message_precheck` 由「调用方 fail-open」升级为**函数自身亦 fail-open**（双层保险），并把该口径写入断言。

**判据映射（AC-149-16）**：新判据**各有样本且执行器可判**（7/7）；运行态段**如实标注未覆盖**（4 项）。

## 3novies. 批次 7 收尾补漏（Step 3 完成度审计发现的两处实现—设计不一致，2026-09-28 续记）

**审计方法**：按 AC-149-05／10／11 逐条索取**可执行证据**（而非以文档陈述为证）⇒ 发现两处差距。

| # | 差距（**实现 vs 设计**） | 性质 | 证据 | 处置 |
|:-:|--------------------------|------|------|------|
| G1 | 预算公式**漏掉安全余量**：实现 `available = 窗口 − 输出预留`，设计 §3.3 为 `− **安全余量**`；且 `CONTEXT_SAFETY_MARGIN*` 配置键**不存在** | **实现—设计不一致**（Step 3 内应闭合） | 全仓无 `safety_margin` 读取点；`config.py` 无该键 | 新增 `CONTEXT_SAFETY_MARGIN_TOKENS`（缺省 256）＋ `BudgetPolicy.safety_margin_tokens`（直接构造默认 0，夹具口径不变）＋ `load_budget_policy` 接线；`available_tokens` 扣余量 |
| G2 | 回执**缺 6 个必填字段**（`model_window`/`output_reserve`/`safety_margin`/`available_budget`/`prompt_tokens_before`/`prompt_tokens_after`）⇒ **AC-149-05 齐备率 ≠ 100%** | **实现—设计不一致** | 探针首轮实测缺字段；代码内无这些字段名 | `PromptComposition` 新增预算四项 ＋ 裁剪前后同口径 token ＋ Prompt 级聚合 `hard_truncated`/`degraded`；`to_record()` **恒有**导出 |
| G3 | 取证探针首版把计量字段名（`prompt_total_tokens`）误判为敏感串 | **探针缺陷**（自纠） | 探针输出「回执出现敏感串：token」 | 口径更正为「**精确敏感键名** ＋ **凭据值形态**」双规则 |
| G4 | **关闭总开关时回执仍新增扩展字段**（扩展字段组共 **12** 项：`dropped`／`over_window`×3／预算四项／裁剪前后 token×2／聚合标记×2）⇒ 破坏 **NFR-149-02／AC-149-09「关闭即逐字回退」** | **不变量破缺（高）** | 探针实测：关闭态回执字段集合含扩展字段（对照探针 `closed_path_keys`） | 扩展字段组改为**与计量组同门**（`budget` 非空才落）⇒ 关闭态**零新增字段**（探针 `leaked_extension_fields: []`）；齐备率 100% 的统计对象＝**预算生效的请求**（口径已写入 §3.19 与 §3.16） |
| G5 | **I-1 开关未在 `Settings` 声明**（仅 `getattr` 读取）⇒ 本仓 `Settings` 为 `extra=forbid`，该键**无法经配置开启**＝**死开关/功能生产不可达** | **实现缺陷（高）** | 探针断言 `Settings.model_fields` 时 `KeyError` ⇒ 首次暴露 | `config.py` **显式声明** `CONTEXT_CROSS_SEGMENT_COMPETITION_ENABLED`（默认 False）；**并新增结构护栏**（扫描全 `app/` 的 `getattr(settings, "KEY"` 与声明集合比对，白名单为空）⇒ 该类缺陷**不可能再静默** |
| G6 | 取证探针判据**「键在即齐备」过弱** ⇒ `{"model": null}` 亦判 PASS（不足以证明「齐备率 100%」） | **取证缺陷（中，自纠）** | 探针首轮 `observed.model = null` 却 PASS | 判定升为**「键在且取值非 null」**（仅 `degraded` 按设计允许 null）＋ 样本显式提供 `model`；**并去除 cwd 依赖**（**判据探针 ＋ 增量执行器**均按 backend 根自动定位，失败显式报错而非静默漏扫/漏判）⇒ 任意 cwd 下探针 **6/6 PASS**、执行器 **7/7 PASS** |

**设计澄清（后补，如实登记顺序偏差）**：两处口径均回写架构 **§3.19（设计补充 F，v1.6.2）** —— 但本批为**实现先行、设计澄清在后**（非「先补设计再实施」），**该顺序偏差在此显式登记**，不掩盖。

**续记（2026-09-29，批次 7 收尾一致性）**：① 架构升 **v1.6.3** —— §3.16「顶层 `dropped` **恒有**」补入**精确论域**（恒有**仅限预算生效的请求**；总开关关闭 ⇒ 该字段**不出现**，与 v1.4.8 逐字一致），消除其与 §3.19「关闭即零新增字段」的**字面冲突**；**判据口径不变**（AC-149-05 统计对象＝预算生效请求）。② 取证探针**去除 cwd 依赖**（backend 根按 `OPENLLM_BACKEND` → cwd → 同级 `OpenLLM/backend` 自动定位；定位失败**显式报错**而非静默漏扫）⇒ 任意 cwd 下 **六项全 PASS** 可复现（此前在非 backend 目录运行会因相对路径失配而**假失败**）。③ 本续记**不含实现改动**。

**本批测试**：`test_context_receipt_fields.py` **先建（RED 8 failed / 1 passed）→ GREEN 12 passed**（含「关闭态零新增字段」与「开关声明默认」两组护栏）；相关面 17 文件 **247 passed**；新增判据探针 `v149_receipt_and_purity_probe.py` ⇒ **六项全 PASS**（AC-149-05／AC-149-09／AC-149-10／AC-149-11／AC-149-12 ＋ 结构护栏 `config_keys_declared`，`-result.json` 落盘）。

## 3decies. 批次 8：I-2 生产落线 ＋ 三项门禁补齐（2026-09-29）

**动因（真实缺陷 G7）**：设计 §3.13「**提供方**」要求「由**网关侧（取数层）**在组装 `segments` 时**并行提供**（条目身份）」，但生产四处调用点（`assembler` 渲染、`component_pipeline` 执行、`executor` 同步组装、流式端点组装）**均未传入** `segment_items` ⇒ 真实请求 `PromptComposition.dropped` **恒为 `[]`** —— 回执字段「被丢弃片段及原因」**有字段无内容**，I-2（P0 增量）在生产**价值不可得**。**暴露方式**：L3 冒烟实测剪切确实发生（`prompt_tokens_before=1611 → after=910`）而 `dropped=[]`。

| # | 缺口 | 处置 |
|:-:|------|------|
| G7 | I-2 身份**无生产提供点** | `assembler.format_context_with_items`（文本与身份**同源同一 `_ordered_items` 排序** ⇒ 对齐由构造保证）＋ `ComponentRunResult.segment_items` ＋ 同步/流式**同口径**传入；上游字段名归一（`chunk_id`/`document_id`/`memory_id` → `id`）＋ 无标识 `{component}#{原下标}` 兜底；平铺 dict／字符串**不产出身份**（设计允许缺省） |
| M1 | **3.4a 技术债务增长率**未做 | `ruff C901` ＋ `pylint duplicate-code`，**HEAD 与基线 `git worktree` 两侧比对** ⇒ **0 / 3 / 0**（3 个新跨阈函数逐项登记成因） |
| M2 | **3.5 实际运行验证（L1/L2/L3）**未做 | 真实启动 8041 ＋ 6 例 L3 冒烟；证据 `doc/test/evidence/v149/` |
| M3 | **3.9b 变更一致性自检**未做 | 文档版本一致性（32 份）＋ 命名/路径规范核对；登记 `validate-naming.ps1` **不存在** |
| M4 | **3.10 开发审计移交材料**缺件 | 补出《开发审计移交材料-v1.4.9》v1.0.0 |

**如实定性**：M1~M4 为**门禁材料缺失**（前两轮审计口径不足，非实现缺陷）；**G7 为真实实现缺陷**且已闭合。**残留边界**：`history`／`profile` 段本版未提供身份；**内存/知识库身份的运行态实测**受环境约束（`openrag` 不可用、`memory` 召回 0 条目）⇒ 移交 Step 4/5。

## 4. 版本控制记录

| 项 | 约定 |
|----|------|
| 分支策略 | **github-flow**（沿用仓内现状：`feature/s4-identity-channel-b` 为编排/通道路线特性分支） |
| commit 模板 | `type(scope): subject`，footer 引用 **TD-ID / RT-ID** |
| 本批提交 ① | `feat(orchestration): 段报告显式标记 hard_truncated / degraded=empty_guard（I-3）` ＋ footer `TD-14901 / RT-149-10 / AC-149-03,04` |
| 本批提交 ② | `feat(orchestration): 跨段竞争池回填与回填观测（I-1）` ＋ footer `TD-14903 / DT-149-01 / RT-149-01 / AC-149-01,02` |
| 本批提交 ③ | `feat(orchestration): 逐条丢弃原因明细 dropped[{source,id,reason}]（I-2）` ＋ footer `TD-14902 / DT-149-03 / RT-149-03 / AC-149-05` |
| 本批提交 ④ | `feat(orchestration): 仍超窗二次校验与显式失败标记（I-5）` ＋ footer `TD-14904 / DT-149-02 / RT-149-02 / AC-149-04,12` |
| 本批提交 ⑤ | `feat(identity): 逐组件通道路由与审计动作码定稿（I-6＋I-7）` ＋ footer `TD-14905,14906 / DT-149-15,16 / RT-149-11,RT-149-12 / AC-149-13,14` |
| 本批提交 ⑥ | `feat(writeback): 画像增量与频控预检接线（I-8）` ＋ footer `TD-14907 / DT-149-17 / RT-149-13 / AC-149-15` |
| 本批提交 ⑦ | `test(evidence): v1.4.9 增量判据执行器与样本集（I-9）` ＋ footer `TD-14908 / DT-149-18 / RT-149-14 / AC-149-16`（OpenBase 仓）＋ `fix(orchestration): 频控预检函数自身 fail-open`（OpenLLM 仓） |
| 本批提交 ⑧ | `fix(orchestration): 补齐预算安全余量与回执必填字段、显式声明竞争池开关（收尾补漏）` ＋ footer `TD-14902 / AC-149-05,09,10,11`（OpenLLM 提交 **`a9914e6`**） |
| **本批提交 ⑨** | `feat(orchestration): 条目身份自取数层贯通到裁剪明细（I-2 生产落线）` ＋ footer `TD-14902 / AC-149-05`（OpenLLM 提交 **`2f5364d`**） |
| **本批提交 ⑩** | `fix(orchestration): 条目身份改为可选增量（向后兼容退回），修复全量回归新增 11 项失败` ＋ footer `TD-14902 / AC-149-05`（OpenLLM 提交 **`d4bff29`**；Stage3 审计 G8） |
| TDD 合规 | 测试先于生产代码提交（批次 1：`test_context_trim_markers.py` 先建并 RED，后实现 GREEN 5 passed；批次 2／I-1：`test_context_cross_segment_competition.py` **先建**，本批修复夹具与实现后 GREEN 5 passed，并**补 1 例反例护栏**；批次 2 收尾／I-2：`test_context_dropped_detail.py` **先建**并 **RED（10 failed / 1 passed）**，实现后 **GREEN 12 passed**） |
| 备份 | 双远程（origin ＋ backup，非 `--mirror`） |

## 5. 验证证据（本批）

| 项 | 结果 |
|----|------|
| RED | `tests/unit/test_context_trim_markers.py` → **3 failed, 2 passed**（标记缺失，符合预期） |
| GREEN | 同文件 → **5 passed** |
| 相关面回归 | 预算/裁剪/排序/画像 4 文件 → **62 passed** |
| 静态检查 | `ruff check`（生产 ＋ 测试文件）→ **All checks passed** |
| 全量回归 | 见 DevLogReport（与基线逐项对比，零新增失败） |

**批次 2（I-1）验证**：

| 项 | 结果 |
|----|------|
| RED（夹具/实现定位后） | `test_context_cross_segment_competition.py` → **1 failed / 3 passed**（根因：夹具正文重复致去重先于配额；实现：空报告 `AttributeError` 被 fail-safe 吞掉） |
| GREEN | 同文件 → **5 passed**（含新增反例护栏 `TestQualityDropsAreNotReclaimed`） |
| 相关面回归 | 预算/裁剪/排序/画像/精炼/保真度 14 文件 → **220 passed** |
| 静态检查 | `ruff check`（生产 ＋ 测试，含 `context_metrics.py`）→ **All checks passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3684 passed / 21 failed**；与既有基线 `cr149-t36-full.txt`（21 failed）**逐项一致 ⇒ 零新增失败** |

**批次 2 收尾（I-2）验证**：

| 项 | 结果 |
|----|------|
| **RED**（先建测试） | `test_context_dropped_detail.py` → **10 failed / 1 passed**（`segment_items` 参数不存在、`PromptComposition.dropped` 不存在、回执无 `dropped`） |
| **GREEN** | 同文件 → **12 passed** |
| 三护栏合跑 | I-1 ＋ I-2 ＋ I-3 三文件 → **22 passed** |
| 相关面回归 | 14 文件 → **238 passed** |
| 静态检查 | `ruff check`（`prompt_pipeline.py`/`context_metrics.py`/新测试）→ **All checks passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3696 passed / 21 failed**；与基线 **逐项一致 ⇒ 零新增失败**（新增 12 例即本批测试） |

**批次 3（I-5）验证**：

| 项 | 结果 |
|----|------|
| **RED**（先建测试） | `test_context_over_window_verifier.py` → **7 failed / 3 passed**（三标记字段不存在、无 ERROR 记录） |
| **GREEN** | 同文件 → **11 passed**（含「校正成功可观测」「预算不足直接判失败」「标记不污染段级 degraded」） |
| 四护栏合跑 | I-1 ＋ I-2 ＋ I-3 ＋ I-5 四文件 → **33 passed** |
| 相关面回归 | 预算/裁剪/排序/画像/精炼/装配/模板 16 文件 → **269 passed** |
| 静态检查 | `ruff check` → **All checks passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3707 passed / 21 failed**；与基线 **逐项一致 ⇒ 零新增失败**（新增 11 例即本批测试） |

**批次 4（I-6＋I-7）验证**：

| 项 | 结果 |
|----|------|
| **RED**（先建测试） | `test_component_channel_routing.py` → **12 failed**（逐组件 API 与 `channels` 落痕缺失）；`test_channel_audit_action_codes.py` → **9 failed**（组件级动作码/定稿取值域/组件级记录与投递缺失） |
| **GREEN** | 两文件 → **12 ＋ 9 passed**；接线护栏 `test_component_channel_audit_wiring.py` → **4 passed** |
| 既有护栏更正 | `test_channel_failover_audit.py::test_action_code_is_declared_provisional` → 随定稿更名为 `test_action_code_is_finalized`（口径变更，非绕过）；该文件其余用例全通过 |
| 相关面回归 | 通道/组件/网关/身份/配置 15 文件 → **202 passed** |
| 静态检查 | `ruff check`（6 生产文件 ＋ 3 新测试）→ **All checks passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3735 passed / 21 failed**；与基线 **逐项一致 ⇒ 零新增失败** |

**批次 5（I-8）验证**：

| 项 | 结果 |
|----|------|
| **RED**（先建测试） | `test_profile_delta_and_precheck_wiring.py` → **11 failed / 2 passed**（两条公开预检入口、启动注入位、频控拦截与 `updates` 挂载均缺失） |
| **GREEN** | 同文件 → **13 passed**（含启动接线**结构护栏**：`main.py` lifespan 必须引用注入位） |
| 缺陷取证 | `compute_message_hash` 与 `WritebackStore.exists_message` **均不存在**（ImportError／方法缺失）⇒ 已补齐；⑥ 探针实测「增量平铺」⇒ 已改嵌套挂载 |
| 相关面回归 | 回写/画像/队列 8 文件 → **134 passed** |
| 静态检查 | `ruff check`（5 生产文件 ＋ 1 新测试）＋ `py_compile main.py` → **All checks passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3748 passed / 21 failed**；与基线 **逐项一致 ⇒ 零新增失败**（新增 13 例即本批测试） |

**批次 6（I-9）验证**：

| 项 | 结果 |
|----|------|
| 样本集结构自检 | `v149_increment_runner.py --self-check` → **通过**（缺字段／无执行函数即拒绝） |
| **判据执行** | `v149_increment_runner.py --json …` → **离线用例 7/7 通过**；运行态 **4 项未覆盖**（`not_covered=true`，如实标注） |
| 判据映射 | I-1↔AC-149-01/02、I-2↔AC-149-05、I-3↔AC-149-03/04、I-5↔AC-149-04/12、I-6↔AC-149-13、I-7↔AC-149-14、I-8↔AC-149-15 **各有样本** |
| 附带回改 | `message_precheck` 升级为**函数自身 fail-open**（双层保险）⇒ 单测复跑 **13 passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3748 passed / 21 failed**；与基线 **逐项一致 ⇒ 零新增失败** |

**批次 7（收尾补漏：预算余量 ＋ 回执齐备率）验证**：

| 项 | 结果 |
|----|------|
| **RED**（先建测试） | `test_context_receipt_fields.py` → **8 failed / 1 passed**（`safety_margin_tokens` 不存在、配置键不存在、回执缺 `hard_truncated` 等） |
| **GREEN** | 同文件 → **12 passed**（含关闭态零新增字段、开关声明默认两组；与配置键离线护栏 4 例合跑 **16 passed**） |
| 相关面回归 | 预算/裁剪/排序/画像/精炼/计量/配置键 17 文件 → **247 passed** |
| **判据探针** | `v149_receipt_and_purity_probe.py` → **AC-149-05 PASS**（10 项必填**键在且取值非 null**，`available_budget` 与公式自洽）／**AC-149-09 PASS**（开关声明默认 False ＋ 关闭态**零新增字段**）／**AC-149-10 PASS**（新链路对 `manage_context`/`_prune_recent` **零命中**）／**AC-149-11 PASS**（无敏感键名/凭据形态/正文哨兵）／**AC-149-12 PASS**（16 组可容纳输入超窗率 0 ＋ 不可容纳显式标记）／**结构护栏 PASS**（全 `app/` 无「读取但未声明」的配置键） |
| 静态检查 | `ruff check`（3 生产文件 ＋ 1 新测试）→ **All checks passed** |
| 全量回归 | `pytest tests/unit tests/integration` → **3760 passed / 21 failed**；与基线 **逐项一致 ⇒ 零新增失败**（＝既有基线 3748 ＋ 本批 12 例） |
| **收尾一致性复验（2026-09-29）** | 取证探针**任意 cwd** 下重跑 → **6/6 PASS**（`backend_root` 自动定位生效）；增量执行器**任意 cwd** 下重跑 → **离线 7/7 通过**（运行态 4 项如实未覆盖）；全量回归**重跑** → **21 failed / 3760 passed**，与基线 `cr149-t36-full.txt` 的 21 项**逐 node id 比对零差异**（`Compare-Object` 双向空）；两个取证脚本 `ruff check` → **All checks passed** |

**批次 8（I-2 生产落线）验证**：

| 项 | 结果 |
|----|------|
| **RED**（先建测试） | `test_segment_items_production_wiring.py` → **10 failed / 1 passed**（`format_context_with_items` 不存在；`ComponentRunResult.segment_items` 不存在；真实裁剪未产出明细） |
| **GREEN** | 同文件 → **12 passed**（同源同序对齐／呈现序随行／字段名归一／原下标兜底／平铺与字符串无身份／真实裁剪产出明细／关闭态无明细／**桩组装器缺新接口退回纯文本**） |
| 相关面回归 | 14 文件 → **208 passed** |
| 静态检查 | `ruff check`（4 生产文件 ＋ 1 新测试）→ **All checks passed**（含 `B905` 修） |
| **实际运行验证（3.5）** | L1 `compileall` exit 0 ＋ `import main` OK；L2 真实实例 `Application startup complete.` ＋ 健康 200（`cr149-instance-8041-20260929.txt`，577 行；**原名 `.log` 被 gitignore ⇒ 改名 `.txt` 入仓**）；L3 **6/6 PASS**（`cr149-l3-smoke-20260929.json`） |
| **技术债务增长率（3.4a）** | `ruff C901` ＋ `pylint duplicate-code`，**HEAD 与基线 worktree 两侧比对** ⇒ 新增 TODO **0**／新增高复杂度函数 **3**（达上限，逐函数登记）／重复块增量 **0**（`cr149-debt-growth-20260929.txt`） |
| **变更一致性自检（3.9b）** | **34 份文档版本全一致**；新增文件路径全落规范目录（`cr149-consistency-selfcheck-20260929.txt`） |
| 全量回归 | `pytest tests/unit tests/integration` → **3772 passed / 21 failed**（＝基线 3760 ＋ 本批 **12** 例）；与基线**逐 node id 一致 ⇒ 零新增失败** |
| **回归事故与修复** | 首次全量回归曾**新增 11 项失败**（`test_component_dependency_scheduling` 6 ＋ `test_component_pipeline_shared` 5）：既有**测试桩组装器仅有 `format_context`**，本批改调 `format_context_with_items` ⇒ `AttributeError`。修复＝**向后兼容退回**（`_format_context_with_items`：优先富接口、缺则纯文本且**不产出身份**）＋ 补 1 例护栏（GREEN 11 → **12 passed**）；复测逐 node id 与基线一致 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.9.5 | 2026-09-29 | AD-OpenLLM-Dev | **门禁证据可复现化 ＋ 文档版本对齐（无代码改动）**：① 3.9b／3.10 的**证据生成器入仓**（`cr149-consistency-selfcheck.py`／`cr149-deliverable-inventory.py`）—— 此前两门禁仅留结论、命令不可复现；② 下游文档版本对齐（DevLogReport **v1.1.6**／开发审计移交材料 **v1.0.3**／测试移交说明 **v1.0.1**／Stage3 审计 **v1.3.3**），清点口径 `TOTAL 21 → **23**`；③ 文头状态更正（[Review]（Step 3 进行中）→ **[Review]（Step 3 收尾，待人工批准后进入 Step 4）**）与版本同步（v1.9.4 → **v1.9.5**）。 |
| v1.9.4 | 2026-09-29 | AD-OpenLLM-Dev | **Step 3 交付物口径补齐**：① §2 注 —— 新建测试文件 8 → **10 个**（补批次 7/8 两个），并新增「**Step 3 文档交付物**」清单行（DevLogReport／追溯矩阵／静态质量／逻辑审查／**开发审计移交材料**／**测试移交说明**，后两项为独立文件）；② §5 第 8 批块「变更一致性自检」份数 33 → **34**（新增《测试移交说明-v1.4.9》）；③ 文头版本同步（v1.9.3 → **v1.9.4**）。依据：`project-document-management` 阶段 3 产物与 `coding-stage-execution` §3.10 核对发现**测试移交说明缺件**（M5，跨版本历史缺口）。 |
| v1.9.3 | 2026-09-29 | AD-OpenLLM-Dev | **批次 8 回归事故更正（如实登记）**：① §5 第 8 批块 —— **GREEN 11 → 12 passed**（补 1 例向后兼容护栏）、**全量回归真值 3760 → 3772 passed / 21 failed**（＝基线 3760 ＋ 本批 12 例；21 项逐 node id 与基线一致）；② 新增「**回归事故与修复**」行：首次全量回归曾新增 **11 项失败**（既有测试桩组装器仅有 `format_context`，本批改调 `format_context_with_items` ⇒ `AttributeError`）⇒ 以**向后兼容退回**（`_format_context_with_items`：优先富接口、缺则纯文本且不产出身份）修复；③ §3decies 与 3.9b 自检份数（32 → **33**）同步；④ §4 新增「本批提交 ⑩」（回归修复 `d4bff29`，Stage3 审计 G8）。 |
| v1.9.2 | 2026-09-29 | AD-OpenLLM-Dev | **批次 8 续记（I-2 生产落线）＋ 三项门禁补齐**：① 新增 **§3decies** —— 批次 8 实施记录（**G7**：I-2 条目身份在生产**无提供点** ⇒ `dropped` 恒空；已由组装器**同源**产出身份 ＋ 组件执行落 `segment_items` ＋ 双路径同口径传入 ＋ 上游字段名归一闭合）与 **M1~M4** 门禁/交付物补齐（3.4a／3.5／3.9b／3.10）；② TD-14902 落点补**批次 8 生产落线**四文件、状态补注；③ §4 增「本批提交 ⑨」（`2f5364d`）；④ §5 增「批次 8 验证」块（RED 10/1 → GREEN 11 passed；相关面 208；L1/L2/L3；债务 0/3/0；自检通过；全量 3760/21 逐 node id 一致）；⑤ 文头版本/上游依据同步（v1.9.1→**v1.9.2**）。 |
| v1.9.1 | 2026-09-29 | AD-OpenLLM-Dev | **批次 7 收尾一致性续记 ＋ 新增 G6**：① 架构升 **v1.6.3**（§3.16 顶层 `dropped`「恒有」补入**精确论域＝预算生效请求**，消除与 §3.19 的**字面冲突**，**判据口径不变**）；② **新增 G6（取证缺陷，中，自纠）** —— 探针原判据「键在即齐备」**过弱**（`{"model": null}` 亦 PASS）⇒ 升为「键在且取值非 null」＋ 样本显式提供 `model`；③ 取证探针**去除 cwd 依赖**（backend 根自动定位，定位失败显式报错）⇒ 任意 cwd 下**六项全 PASS** 可复现；④ 文头版本/日期/上游依据同步（v1.9.0→**v1.9.1**、设计补充至 **v1.6.3**）。 |
| v1.9.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3novies：**批次 7 收尾补漏** —— Step 3 完成度审计按 AC-149-05／10／11 索取**可执行证据**，发现并闭合两处**实现—设计不一致**：① 预算公式**漏安全余量**（补齐 `CONTEXT_SAFETY_MARGIN_TOKENS` 与 `BudgetPolicy.safety_margin_tokens`，`available = 窗口 − 预留 − 余量`）；② 回执**缺 6 个必填字段**（补齐预算四项 ＋ 裁剪前后同口径 token ＋ 聚合标记 ⇒ **AC-149-05 齐备率 100%**）；另自纠 1 处**探针缺陷**（把计量字段名误判为敏感串）。**如实登记「实现先行、设计澄清在后」的顺序偏差**（口径已回写架构 §3.19／v1.6.2）。新增判据探针 `v149_receipt_and_purity_probe.py` ⇒ **AC-149-05／10／11 全 PASS**；另**修正本文档头版本号滞后**（此前正文已至 v1.8.0、头仍 v1.4.0）。TD-14902 状态补注「批次 7 齐备率补齐」。 |
| v1.8.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3octies：**批次 6（I-9 评测集与判据扩展）** 实施记录 —— 新增 `v149-increment-eval-set.json`（7 项离线用例 ＋ 4 项运行态 `not_covered`）与执行器 `v149_increment_runner.py`（结构校验／逐项执行／`-result.json`／失败非 0 退出码），实测 **7/7 通过、4 项运行态如实未覆盖**；附带把 `message_precheck` 升级为**函数自身 fail-open**（双层保险）。TD-14908 状态改为「已完成」⇒ **批次 1~6 全部落地，9 条 TD-ID 全部收口**，Step 3 进入收尾（静态质量检查／逻辑审查／DevLogReport／Stage3 审计）。 |
| v1.7.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3septies：**批次 5（I-8 画像增量与频控预检接线）** 实施记录 —— 两条公开预检入口（`profile_delta_precheck`／`message_precheck`）接入回写回调（profile 路携带 `updates`；入队前消息级预检）、新增启动注入位接线并在 `main.py` lifespan 调用；**如实登记 3 项缺陷**：① `compute_message_hash` **不存在**（补齐）② `WritebackStore.exists_message` **不存在**＋表无内容哈希列（以**有界回看＋指纹比对**补齐，不改表结构）③ 增量**平铺**致画像契约键 `updates` 取不到（改为嵌套挂载）。同时登记两条边界（有界去重＋强幂等仍由队列唯一约束兜底；LLM 提炼生效受 D3）。TD-14907 状态改为「已完成」。 |
| v1.6.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3sexies：**批次 4（I-6 逐组件通道路由 ＋ I-7 审计动作码定稿）** 实施记录 —— 逐组件独立状态/裁决/视图（与请求级计数**隔离**）、取数前裁决＋`_channel` 下发＋按组件回写、`channels` 随 `ExecuteResult` 上抛并在两路径轨迹落痕；动作码由暂定**转定稿**（移除暂定标注，新增组件级 `channel_component_failover` 与 `AUDIT_ACTION_CODES` 单一事实源），并在网关补**调用点**（同故障期去重）；边界＝**不**切换出站拓扑（保 K07/AB 等价契约）。TD-14905/14906 状态改为「已完成」。 |
| v1.5.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3quinquies：**批次 3（I-5 仍超窗显式失败标记）** 实施记录 —— `_verify_window` 二次校验（判定口径＝最终 Prompt 总 token > 窗口；校正至多一次，按 `Σratio` 反算**实减**素材预算）、三标记 `over_window`/`over_window_tokens`/`over_window_recovered` 恒有并随回执导出、组装顺序调整为「渲染 → 校验 → refine/计量」使观测同源；**如实登记 4 项编期决策**（不足额反算 / 预算不足直接判失败 / 不新增错误码 / 标记不与段级 `degraded` 混用）。TD-14904 状态改为「已完成」。 |
| v1.4.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3quater：**批次 2 收尾（I-2 逐条丢弃原因明细）** 实施记录 —— 段级 `dropped` ＋ 顶层 `dropped`（恒有，满足 AC-149-05 齐备率）、单元升三元组、`segment_items` 全链透传；**如实登记 3 项**：① 既有实现中**画像字段级预丢被配额阶段重复计数**的口径缺陷（本批修正并加精确计数护栏）；② `dropped` 排序口径编期收敛为「处置阶段先后 ＋ 阶段内呈现序」；③ 段级 `dropped` 与 I-3「无裁剪 ⇒ 报告缺失」的边界澄清。TD-14902 状态改为「已完成」；§2 CheckList 增 2 行；**批次 2（I-1＋I-2）全部完成**。 |
| v1.3.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3ter：**批次 2／I-1（跨段竞争池）** 实施记录 —— 开关默认关闭、池硬上界保 T1、fail-safe、新增 `competition_filled`/`refilled_items`；**如实登记 2 类缺陷**（① 测试夹具因正文重复致去重先于配额、池内无可回填项；② 回填后空报告触发 `AttributeError` 被 fail-safe 静默吞掉）并**更正上一轮**「`local variable 'pool'`」为探针插桩所致的误判；取消死参数 `quota_override`。TD-14903 状态改为「已完成」。 |
| v1.2.0 | 2026-09-28 | AD-OpenLLM-Dev | 设计补充 A/B 已出（架构 §3.13／§3.14＋ADR-149-07）⇒ **I-2 解阻塞、I-1 算法与不变量已定**，批次 2 进入实施。 |
| v1.1.0 | 2026-09-28 | AD-OpenLLM-Dev | 新增 §3bis 批次 2 前置定位：① **I-3 `enabled` 收口＝无需新增字段**（`budget` 存在性已表达开关状态）；② **I-2 阻塞于设计补充**（`_trim_segment` 只收文本、身份在上游丢失 ⇒ 需先补契约约定）。TD-14902 状态改为「阻塞于设计补充」。 |
| v1.0.0 | 2026-09-28 | AD-OpenLLM-Dev | 初始创建：9 条 TD-ID（TD-14901~14909）↔ DT/需求/代码落点/判据/Phase；Subtask CheckList（含命名一致性核对）；**批次 1（I-3）已完成**并如实登记 **I-2 推迟原因**；版本控制记录与验证证据。状态 [Review] |
