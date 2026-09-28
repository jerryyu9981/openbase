# OpenBase 开发记录报告（DevLogReport） - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（本版本全部代码改动落于该仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量） |
| 文档 | 开发记录报告（Step 3 产出 1） |
| 文档版本 | v1.1.1 |
| 状态 | [Review]（Step 3 收尾，待人工批准） |
| 日期 | 2026-09-29 |
| 作者 | AD-OpenLLM-Dev |
| 上游依据 | 需求 v1.4.9（29 项）｜设计基线 **v1.6.1（[Approved]）＋ 设计补充至 v1.6.3**｜追溯矩阵 v1.9.1｜需求与设计更正记录 v1.2.0 |
| 开发方式 | 批次化 TDD（RED → GREEN → 相关面回归 → 全量回归 → 文档同步 → 提交） |

## 1. 版本目标与增量范围

**版本级原则**（用户口径）：v1.4.8 与 v1.4.9 均以「**主备通道畅通** ＋ **主通道上下文合理装配**」为目标，**已做过的不重复**。

**真实增量 I-1~I-10**（基线＝v1.4.8 ＋ CR-149 已实施批次）：

| 增量 | 内容 | 批次 | 状态 |
|:----:|------|:----:|:----:|
| I-1 | 跨段配额竞争（共享剩余额度池） | 2 | ✅ |
| I-2 | 逐条丢弃原因明细 `dropped[{source,id,reason}]` | 2′ | ✅ |
| I-3 | 显式标记 `hard_truncated`／`degraded=empty_guard` | 1 | ✅ |
| I-4 | 使用反馈 `used_fragments`（跨仓 D4） | — | ⏳ **运行态未覆盖**（受 D4） |
| I-5 | 仍超窗的二次校验与显式失败标记 | 3 | ✅ |
| I-6 | 取数层逐组件通道路由 | 4 | ✅ |
| I-7 | 审计动作码定稿（含组件级事件） | 4 | ✅ |
| I-8 | 画像增量与频控预检接线 | 5 | ✅ |
| I-9 | 评测集与判据扩展 | 6 | ✅ |
| I-10 | 判别式重排器（条件项） | — | ✅ **按设计仅登记不实施** |

## 2. 逐批次实现内容（含「为什么」）

### 批次 1／I-3：段报告显式标记（`prompt_pipeline.py`）
`_trim_segment` 报告新增 **`hard_truncated`**（恒有）与 **`degraded="empty_guard"`**（仅**保底一条被触发**时出现）。**理由**：此前的裁剪降级不可观测 ⇒ 无法回答「这段为何只剩一条」。

### 批次 2／I-1：跨段竞争池
`BudgetPolicy.cross_segment_competition_enabled`（**默认关闭**）＋ `apply_context_budget` 末尾竞争池：`pool = min(available − Σused, Σdropped_tokens)` → 逐段**放大比例**重跑同一 `_trim_segment` 回填 → 观测 `competition_filled`／`refilled_items`。**理由**：静态分段配额下「某段闲置、另一段丢弃」属预算浪费。**编期澄清**：池只承载**预算闲置额度**，**质量规则**（去重/合并/截断）的丢弃**不可回填**（结构性由「复用同一 `_trim_segment`」保证）；删除死参数 `quota_override`。

### 批次 2′／I-2：逐条丢弃原因明细
`_trim_segment` 新增**只读** `items`（与单元行行序对齐；缺省/长度不符 ⇒ 按无明细）→ 段级 `dropped` ＋ 顶层 `dropped`（按 `QUOTA_SEGMENTS` 展平，**恒有**）。原因码冻结为 `dedup`／`profile_field`／`quota`。**顺带修正既有缺陷**：画像字段级预丢与配额阶段**重复计数**（翻倍）⇒ 配额阶段改用独立收集。

### 批次 3／I-5：仍超窗的二次校验与显式失败标记
`_verify_window`：`prompt_total_tokens > window` ⇒ 超窗；**校正至多一次**（按 `Σratio(有素材的段)` 反算，**实减**素材预算）；仍超 ⇒ `over_window`／`over_window_tokens` 置位 ＋ **ERROR 日志**（不静默）；**不新增对外错误码**（API §1）。新增 `over_window`／`over_window_tokens`／`over_window_recovered` 三标记恒有。**组装顺序**调整为「渲染 → 校验 → refine/计量」使观测同源。

### 批次 4／I-6＋I-7：逐组件通道路由 ＋ 动作码定稿
- **I-6**：`ChannelStateManager` 新增逐组件状态（失败累加/成功清零/裁决/视图），与请求级计数**完全隔离**；`run_components` 取数**前**逐组件裁决、标签经 `channels`／`_channel` 发布、按组件回写成败；门控 `COMPONENT_CHANNEL_ROUTING_ENABLED` **默认关闭**；两路径轨迹落 `per_component_channels`。**边界**：本仓**不**切出站拓扑（保 K07/AB 等价）。
- **I-7**：动作码 `channel_failover_b_to_a` **由暂定转定稿**（移除暂定标注）＋ 新增组件级 `channel_component_failover`（`detail` 记 `component`）＋ `AUDIT_ACTION_CODES` 单一事实源；网关补**调用点**（同故障期去重）。

### 批次 5／I-8：画像增量与频控预检接线
两条公开预检（`profile_delta_precheck`／`message_precheck`）接入回写回调（profile 路携带 `updates`；入队前消息级预检）；`install_profile_refine_on_startup()` 并在 `main.py` lifespan 调用。**顺带补齐既有缺陷**：`compute_message_hash`／`WritebackStore.exists_message` **均不存在** ⇒ 补齐（后者以**有界回看＋指纹比对**实现，**不改表结构**）。

### 批次 6／I-9：评测集与判据扩展
新增 `v149-increment-eval-set.json`（7 项离线用例 ＋ 4 项运行态 `not_covered`）与执行器 `v149_increment_runner.py`；离线 **7/7 通过**。

### 批次 7／**收尾补漏**：预算安全余量 ＋ 回执字段齐备率（Step 3 完成度审计发现）
**动因**：初版收尾审计以「交付物清单 ＋ 陈述核对」为主；按 **AC-149-05／10／11** 追加索取**可执行证据**后，发现两处**实现—设计不一致**：
1. **预算公式漏安全余量** —— 实现 `available = 窗口 − 输出预留`，设计 §3.3 为 `− **安全余量**`，且配置键缺失 ⇒ 新增 `CONTEXT_SAFETY_MARGIN_TOKENS`（缺省 256）＋ `BudgetPolicy.safety_margin_tokens`（直接构造默认 0 ⇒ 夹具口径不变）＋ `load_budget_policy` 接线；`available_tokens` 扣余量。
2. **回执缺 6 个必填字段**（`model_window`/`output_reserve`/`safety_margin`/`available_budget`/`prompt_tokens_before`/`prompt_tokens_after`）⇒ AC-149-05 齐备率不达 100% ⇒ `PromptComposition` 新增预算四项 ＋ 裁剪前后**同口径** token（`system ＋ query ＋ 素材`，不含段标记）＋ Prompt 级聚合 `hard_truncated`/`degraded`，`to_record()` **恒有**导出。
3. 另自纠 1 处**探针缺陷**（把计量字段名 `prompt_total_tokens` 误判为敏感串）⇒ 改为「精确敏感键名 ＋ 凭据值形态」双规则。

**顺序偏差（如实登记）**：本批为**实现先行、设计澄清在后**（口径回写架构 §3.19／v1.6.2），**偏离**「先补设计再实施」的既有纪律。

## 3. 变更统计与影响文件

**落点仓（OpenLLM）生产代码**（12 个文件；批次 7 收尾补漏仅改其中 `prompt_pipeline.py`／`context_metrics.py`／`core/config.py` 三个）：
`prompt_pipeline.py`、`context_metrics.py`、`channel.py`、`channel_audit.py`、`component_pipeline.py`、`executor.py`、`core/config.py`、`api/openllm_gateway.py`、`edgerouter/orchestration/evaluate.py`、`profile_refine_gate.py`、`services/writeback_queue.py`、`main.py`

**测试**（新建 9 个 ＋ 更正 1 个既有）：
`test_context_trim_markers.py`、`test_context_cross_segment_competition.py`、`test_context_dropped_detail.py`、`test_context_over_window_verifier.py`、`test_component_channel_routing.py`、`test_channel_audit_action_codes.py`、`test_component_channel_audit_wiring.py`、`test_profile_delta_and_precheck_wiring.py`、`test_context_receipt_fields.py`；`test_channel_failover_audit.py`（随定稿更正）

**文档仓（OpenBase）**：架构设计文档 v1.6.3、追溯矩阵 v1.9.1、静态质量检查记录 v1.1.0、代码逻辑审查记录 v1.2.0、本报告 v1.1.1、Stage3 审计报告 v1.2.0、证据（`v149-increment-eval-set.json`／`v149_increment_runner.py`／`-result.json`／`v149_receipt_and_purity_probe.py`／`-result.json`）

**提交（本版本累计 8 笔，均**未推送**）**：OpenLLM `2d1aa85`／`a1021c4`／`33c4009`／`9b36160`／`9782f48`／`1651e42`／`333188a`／**`a9914e6`（收尾补漏）**；OpenBase `81fee6f`（I-9 证据＋文档）、`a8f9cb2`（Step 3 收尾四件套）、**本笔（批次 7 收尾一致性）**

## 4. 验证记录（逐批次；命令与结果同源可复现）

| 批次 | RED | GREEN | 相关面 | ruff | 全量（`tests/unit tests/integration`） |
|:----:|-----|-------|--------|------|----------------------------------------|
| 1／I-3 | 3 failed / 2 passed | 5 passed | 62 passed | ✅ | 21 failed / 3531 passed（基线一致） |
| 2／I-1 | 1 failed / 3 passed（根因定位后） | 5 passed | 220 passed | ✅ | 21 failed / 3684 passed（基线一致） |
| 2′／I-2 | 10 failed / 1 passed | 12 passed | 238 passed | ✅ | 21 failed / 3696 passed（基线一致） |
| 3／I-5 | 7 failed / 3 passed | 11 passed | 269 passed | ✅ | 21 failed / 3707 passed（基线一致） |
| 4／I-6·I-7 | 12 ＋ 9 failed | 12 ＋ 9 passed（＋接线 4） | 202 passed | ✅ | 21 failed / 3735 passed（基线一致） |
| 5／I-8 | 11 failed / 2 passed | 13 passed | 134 passed | ✅ | 21 failed / 3748 passed（基线一致） |
| 6／I-9 | —（证据） | 判据执行器 7/7 | 13 passed | ✅ | 21 failed / 3748 passed（基线一致） |
| 7／收尾补漏 | 8 failed / 1 passed（9 例）→ 追加 G4／G5 护栏 3 例（关闭态零新增字段、开关声明默认、开启态扩展组齐备） | **12 passed** | 247 passed | ✅ | 21 failed / **3760 passed**（基线一致，21 项**逐 node id 相同**） |

**批次 7 追加取证（判据探针，落盘 `-result.json`）**：**AC-149-05**（回执 10 项必填齐备且 `available_budget` 与 `model_window − output_reserve − safety_margin` 自洽）**PASS**／**AC-149-10**（新预算裁剪链路对 `manage_context`／`_prune_recent` **零命中**）**PASS**／**AC-149-11**（无敏感键名、无凭据值形态、无片段正文哨兵）**PASS**。

**基线对照口径（重要）**：全量**21 项失败**与仓内既有基线 `cr149-t36-full.txt`（同 21 项、同 node id）**逐项一致** ⇒ **零新增失败**；该 21 项为**环境/配置性既有失败**（401 统一格式、模型路由接线、real-contract 默认值开关、流式收尾等），**与本版本改动面无交集**。

**静态检查**：`ruff check` 改动面 **0 告警**；`py_compile main.py` 通过。

## 5. 偏差、语义变更与风险（如实登记）

| 项 | 说明 |
|----|------|
| 过程偏差 1 | I-1 首轮排障曾把**探针自身插桩**导致的 `local variable 'pool'` 误判为模块缺陷；已在追溯矩阵 §3ter **显式更正**，不作为缺陷入档 |
| 过程偏差 2 | I-1 首轮测试**夹具缺陷**（history 8 行正文相同 ⇒ 去重先于配额 ⇒ 池内无可回填项）：夹具已修，并把该语义固化为**反例护栏** |
| 语义变更 1 | I-7 使动作码**由暂定转定稿** ⇒ 既有护栏 `test_action_code_is_declared_provisional` **随契约更正**为 `test_action_code_is_finalized`（**非绕过**，设计 §3.10 已冻结） |
| 语义变更 2 | 画像字段级预丢的 `dropped_items`/`dropped_tokens` 由**翻倍**更正为**真实值**（口径更正，取舍结果不变） |
| 语义变更 3（批次 7） | 预算纳入**安全余量** ⇒ 打开预算开关的部署，可用预算较此前**减少** `CONTEXT_SAFETY_MARGIN_TOKENS`（缺省 256）；**关闭预算（默认）不受影响**；回执新增 8 个恒有字段（齐备率达标） |
| 过程偏差 3（批次 7） | 收尾补漏属**实现先行、设计澄清在后**（架构 §3.19 于实现后补写）⇒ **偏离**「先补设计再实施」纪律，已在追溯矩阵 §3novies、审查记录与 Stage3 审计追加段**显式登记** |
| 过程偏差 4（批次 7） | 初版收尾审计对 AC-149-05／10／11 **未索取可执行证据**（以陈述核对为主）⇒ 追加取证后才发现两处不一致；Stage3 审计报告已**如实更正**该宽松之处 |
| 过程偏差 5（批次 7 续记） | 追加取证所用探针**自身有缺陷**（G6：判定过弱 ——「键在即齐备」使 `{"model": null}` 亦 PASS；且依赖 cwd）⇒ 已加固判定口径并去除 cwd 依赖，**取证工具缺陷不入生产缺陷账**，但在此如实登记（与 G3 同类） |
| 风险 1（受 D3） | 画像 LLM 提炼**接线**完成但**生效**需评测支撑 ⇒ 不在本版承诺内（判据执行器标注未覆盖） |
| 风险 2（受 D4） | `used_fragments` 跨仓回写契约未确认 ⇒ I-4 运行态未覆盖 |
| 风险 3（低） | 池上界仍用汇总 `Σdropped_tokens`（估值偏大）；T1 由一阶项封顶，不产生超窗 ⇒ 登记为后续可选项 |
| 未提交/未推送 | 本版本 **8 笔提交**（OpenLLM 7 ＋ 收尾补漏 1）**均已提交、均未推送**（按用户口径：推送需单独确认）；另有 **1 笔文档收尾提交**（OpenBase）同样未推送 |

## 6. 未完成事项（移交 Step 4 / Step 5）

| 项 | 承接阶段 |
|----|----------|
| 覆盖率门（`--cov`）与测试计划/用例/回归 | Step 4 |
| 接口/集成/E2E/UAT 与判据执行器运行态部分（I-4／I-1-runtime／I-8-runtime／I-6-runtime） | Step 4（需 D3/D4 与运行环境） |
| 部署、灰度与回退、回执齐备率实测、超窗率实测统计（AC-149-12） | Step 5 |
| 还债占比复核（当前约 11% < 15%） | Step 4 复审 |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.1.1 | 2026-09-29 | AD-OpenLLM-Dev | **批次 7 收尾一致性续记（无生产代码改动）**：① §4 第 7 批数据**据实更正**（GREEN 9 → **12 passed**、全量 3757 → **3760 passed**，21 项失败与基线**逐 node id 相同**），并补记 RED 为 9 例 → 追加 G4／G5 护栏 3 例；② §4 探针结论补**齐备性判定已加固**（由「键在即齐备」升为「键在且取值非 null」，修复 **G6 取证缺陷**）与**去 cwd 依赖**；③ 架构升 **v1.6.3**（§3.16 顶层 `dropped` 恒有的**精确论域**＝预算生效请求，消除与 §3.19 的字面冲突，判据口径不变）；④ §3 文档版本清单、§5 提交计数（7→**8 笔**，含 1 笔文档收尾）、文头版本/日期/上游依据同步。 |
| v1.1.0 | 2026-09-28 | AD-OpenLLM-Dev | **批次 7（收尾补漏）并入**：新增 §2「批次 7」段（预算安全余量 ＋ 回执 6 必填字段齐备率 ＋ 探针缺陷自纠）；§3 测试数 8→9、提交数 7→8；§4 新增第 7 批 RED/GREEN/相关面/全量行与**追加取证结论**（AC-149-05/10/11 全 PASS）；§5 新增语义变更 3 与过程偏差 3/4（含「实现先行、澄清后补」与「初版审计未索取可执行证据」两项如实登记）。 |
| v1.0.0 | 2026-09-28 | AD-OpenLLM-Dev | 初始创建：版本目标与 I-1~I-10 范围、**6 批次逐项实现内容与理由**、变更统计（12 生产文件／8 新建测试／7 笔提交）、**逐批次 RED-GREEN-相关面-全量验证记录**（含基线对照口径）、偏差/语义变更/风险如实登记、Step 4/5 移交清单。状态 [Review] 待人工批准 |
