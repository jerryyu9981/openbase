# OpenBase 开发记录报告（DevLogReport） - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM**（本版本全部代码改动落于该仓） |
| 版本号 | **v1.4.9**（上下文预算与回写质量） |
| 文档 | 开发记录报告（Step 3 产出 1） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（Step 3 收尾，待人工批准） |
| 日期 | 2026-09-28 |
| 作者 | AD-OpenLLM-Dev |
| 上游依据 | 需求 v1.4.9（29 项）｜设计基线 **v1.6.1（[Approved]）**｜追溯矩阵 v1.8.0｜需求与设计更正记录 v1.2.0 |
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

## 3. 变更统计与影响文件

**落点仓（OpenLLM）生产代码**（12 个文件）：
`prompt_pipeline.py`、`context_metrics.py`、`channel.py`、`channel_audit.py`、`component_pipeline.py`、`executor.py`、`core/config.py`、`api/openllm_gateway.py`、`edgerouter/orchestration/evaluate.py`、`profile_refine_gate.py`、`services/writeback_queue.py`、`main.py`

**测试**（新建 8 个 ＋ 更正 1 个既有）：
`test_context_trim_markers.py`、`test_context_cross_segment_competition.py`、`test_context_dropped_detail.py`、`test_context_over_window_verifier.py`、`test_component_channel_routing.py`、`test_channel_audit_action_codes.py`、`test_component_channel_audit_wiring.py`、`test_profile_delta_and_precheck_wiring.py`；`test_channel_failover_audit.py`（随定稿更正）

**文档仓（OpenBase）**：架构设计文档 v1.6.1、追溯矩阵 v1.8.0、静态质量检查记录 v1.0.0、代码逻辑审查记录 v1.0.0、本报告 v1.0.0、Stage3 审计报告 v1.0.0、证据（`v149-increment-eval-set.json`／`v149_increment_runner.py`／`-result.json`）

**提交（本版本累计 7 笔，均**未推送**）**：OpenLLM `2d1aa85`（I-3）、`a1021c4`（I-1）、`33c4009`（I-2）、`9b36160`（I-5）、`9782f48`（I-6＋I-7）、`1651e42`（I-8）、`333188a`（I-9 配套）；OpenBase `81fee6f`（I-9 证据＋文档）

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

**基线对照口径（重要）**：全量**21 项失败**与仓内既有基线 `cr149-t36-full.txt`（同 21 项、同 node id）**逐项一致** ⇒ **零新增失败**；该 21 项为**环境/配置性既有失败**（401 统一格式、模型路由接线、real-contract 默认值开关、流式收尾等），**与本版本改动面无交集**。

**静态检查**：`ruff check` 改动面 **0 告警**；`py_compile main.py` 通过。

## 5. 偏差、语义变更与风险（如实登记）

| 项 | 说明 |
|----|------|
| 过程偏差 1 | I-1 首轮排障曾把**探针自身插桩**导致的 `local variable 'pool'` 误判为模块缺陷；已在追溯矩阵 §3ter **显式更正**，不作为缺陷入档 |
| 过程偏差 2 | I-1 首轮测试**夹具缺陷**（history 8 行正文相同 ⇒ 去重先于配额 ⇒ 池内无可回填项）：夹具已修，并把该语义固化为**反例护栏** |
| 语义变更 1 | I-7 使动作码**由暂定转定稿** ⇒ 既有护栏 `test_action_code_is_declared_provisional` **随契约更正**为 `test_action_code_is_finalized`（**非绕过**，设计 §3.10 已冻结） |
| 语义变更 2 | 画像字段级预丢的 `dropped_items`/`dropped_tokens` 由**翻倍**更正为**真实值**（口径更正，取舍结果不变） |
| 风险 1（受 D3） | 画像 LLM 提炼**接线**完成但**生效**需评测支撑 ⇒ 不在本版承诺内（判据执行器标注未覆盖） |
| 风险 2（受 D4） | `used_fragments` 跨仓回写契约未确认 ⇒ I-4 运行态未覆盖 |
| 风险 3（低） | 池上界仍用汇总 `Σdropped_tokens`（估值偏大）；T1 由一阶项封顶，不产生超窗 ⇒ 登记为后续可选项 |
| 未提交/未推送 | 本版本 7 笔提交**均已提交、均未推送**（按用户口径：推送需单独确认） |

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
| v1.0.0 | 2026-09-28 | AD-OpenLLM-Dev | 初始创建：版本目标与 I-1~I-10 范围、**6 批次逐项实现内容与理由**、变更统计（12 生产文件／8 新建测试／7 笔提交）、**逐批次 RED-GREEN-相关面-全量验证记录**（含基线对照口径）、偏差/语义变更/风险如实登记、Step 4/5 移交清单。状态 [Review] 待人工批准 |
