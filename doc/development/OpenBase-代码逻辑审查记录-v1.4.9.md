# OpenBase 代码逻辑审查记录 - v1.4.9

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **OpenLLM** |
| 版本号 | **v1.4.9**（上下文预算与回写质量） |
| 文档 | 代码逻辑审查记录（Step 3 产出 4） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（Step 3 收尾） |
| 日期 | 2026-09-28 |
| 审查人 | AD-OpenLLM-Dev（自审）／待人工复核 |
| 审查对象 | 本版本 6 批次全部逻辑改动（I-1~I-9） |
| 对照基线 | 需求 v1.4.9（29 项）／设计基线 **v1.6.1（[Approved]）**／追溯矩阵 v1.8.0 |

## 1. 审查方法与覆盖

**方法**：以「**判据 → 代码落点 → 测试用例 → 实测证据**」四栏逐项回溯（追溯矩阵 §1/§3bis~§3octies 已固化），并对**每条不变量**单独指出「为何结构性成立」，不以用例通过代替不变量论证。

| 增量 | 需求 | 设计落点 | 代码落点 | 判据 | 结论 |
|:----:|------|----------|----------|------|------|
| I-1 | FR-149-03 | 架构 §3.4／§3.14＋ADR-149-07／§3.15 | `_trim_segment`／`apply_context_budget` 竞争池 | AC-149-01/02 | ✅ |
| I-2 | FR-149-06 | 架构 §3.13／§3.16 | `_trim_segment(items)`／`PromptComposition.dropped`／`ContextReceipt.to_record` | AC-149-05 | ✅ |
| I-3 | FR-149-06 | 架构 §3.6 | `_trim_segment` 报告 `hard_truncated`／`degraded` | AC-149-03/04 | ✅ |
| I-5 | FR-149-05 | 架构 §3.6／§3.17 | `_verify_window` ＋ 三标记 | AC-149-04/12 | ✅ |
| I-6 | FR-149-09 | 架构 §3.9＋ADR-149-06／§3.18 | `channel.py` 逐组件状态／`component_pipeline` 裁决与标签／`executor`＋网关落痕 | AC-149-13 | ✅ |
| I-7 | FR-149-10 | 架构 §3.10 | `channel_audit` 定稿＋组件级事件＋网关调用点 | AC-149-14 | ✅ |
| I-8 | FR-149-11 | 架构 §3.11 | `evaluate` 两条预检／`profile_refine_gate` 启动注入位／`writeback_queue` 依赖补齐／网关回写回调 | AC-149-15 | ✅ |
| I-9 | FR-149-12 | — | `doc/test/evidence/cr149/` 样本集＋执行器 | AC-149-16 | ✅ |
| I-10 | FR-149-13 | 架构 §3.12 | 仅登记（无代码） | AC-149-17（条件） | ✅（按设计不实施） |

## 2. 不变量专项论证（关键：为何结构性成立）

| 不变量 | 论证 | 反例护栏 |
|--------|------|----------|
| **T1（Σ 素材 used ≤ available）** | 池上界 `pool = min(available − Σused, Σdropped)` ⇒ 修正后总量 ≤ `available − used_i + base_i + pool ≤ available`（因 `used_i ≥ base_i`）；**一阶项 `available − Σused` 直接封顶**，故**即使池估值偏大也不超窗** | `test_context_cross_segment_competition.py::TestCompetitionRefillsDroppedItems`（含 T1 断言） |
| **T2（保底一条）** | 保底**先于**竞争执行；回填只可能**增加**条目 ⇒ 不破坏「有素材的段 used > 0」 | 同上 `test_floor_is_preserved_for_segments_with_text` ＋ I-5 用例 |
| **T10（段内取舍单位不变）** | 单元仍是 `(编号前缀, 正文)`（身份只读旁挂）⇒ 画像字段级／整条丢弃语义不变 | 相关面 238 passed（含 `test_profile_dimension_priority.py`） |
| **质量规则不可被池绕过** | 回填**复用同一** `_trim_segment`，而**去重/合并/单条截断先于配额执行** ⇒ 结构性不可绕过（非约定） | `TestQualityDropsAreNotReclaimed` |
| **明细只读** | `identity` 只参与 `dropped` 落痕；不进入排序/配额/渲染；缺省或长度不符 ⇒ `identities=None` ⇒ 段级明细整体缺席 | `test_context_dropped_detail.py::TestReadOnly` |
| **超窗率 0（AC-149-12）** | 判定＝`prompt_total_tokens > window`；T1 已保证素材侧不超；非配额开销顶出时**校正一次**（按 `Σratio` 反算实减）或**显式判失败**（绝不静默） | `test_context_over_window_verifier.py`（11 例） |
| **逐组件隔离** | 逐组件计数与请求级 `_b_consecutive_failures` **物理分离**（两个字段）⇒ 单组件故障不放大为全链路切换 | `test_component_state_is_independent_from_request_level_counter` |
| **拓扑身份不被伪造** | 本仓**不**改 `X-Proxy-Source`（恒 `openbase-orchestrator`）⇒ K07 与 AB 等价断言不被破坏 | 相关面 `test_external_identity`／`test_ab_equivalence` 等全绿 |
| **默认零变化** | 4 个开关（`CONTEXT_CROSS_SEGMENT_COMPETITION_ENABLED`／`COMPONENT_CHANNEL_ROUTING_ENABLED`／`WRITEBACK_DECISION_ENABLED`／`PROFILE_LLM_REFINE_ENABLED`）**默认关闭**；关闭路径的落痕字段为空 dict/缺席 | 各批次「关闭 ⇒ 逐字一致」用例 |
| **fail-open / fail-safe** | 裁决器异常⇒回落整体偏好；频控预检**函数级＋调用级双层**兜底；审计投递 `disabled`/`no_loop`；画像增量异常⇒空增量 | 各批次 fail-open 用例（8 例） |

## 3. 逐项逻辑审查发现（如实登记，含遗留）

| # | 类别 | 发现 | 严重度 | 处置 |
|:-:|------|------|:------:|------|
| 1 | **既有实现缺陷** | 画像字段级预丢项被③配额阶段**重复计数**（复用 `popped`）⇒ `dropped_items`/`dropped_tokens` **翻倍**；既有断言均为 `>= 1` 故未被发现 | 中（观测失真，不影响取舍） | 批次 2′ **已修** ＋ 精确计数护栏 |
| 2 | **既有实现缺陷** | `_message_exists` 依赖的 `compute_message_hash` **不存在** ⇒ 一旦接线即 `ImportError`（被零调用点掩盖） | 高（接线即挂） | 批次 5 **已补齐** |
| 3 | **既有实现缺陷** | `WritebackStore.exists_message` **不存在**且表**无内容哈希列** | 高（同上） | 批次 5 以**有界回看＋指纹比对**补齐（**不改表结构**） |
| 4 | **既有实现缺陷** | `install_profile_refiner_if_enabled` **全仓零调用点**（有能力不接线） | 中 | 批次 5 **已接线**（lifespan）＋ 结构护栏 |
| 5 | **编期缺陷（自纠）** | `dropped` 排序初版为「弹出顺序」⇒ 回执可读性差 | 低 | 冻结为「处置阶段先后＋段内呈现序」 |
| 6 | **编期缺陷（自纠）** | 画像增量**平铺**致契约键 `updates` 取不到 | 中（功能不生效） | 改嵌套挂载（探针实测收口） |
| 7 | **编期缺陷（自纠）** | I-1 首轮「池不生效」根因一度误判为模块缺陷（实为**探针插桩**所致） | 低（过程） | **已在追溯矩阵更正**，避免错误结论入档 |
| 8 | **契约边界** | 段级 `dropped` 与 I-3「无裁剪 ⇒ 报告缺失」潜在冲突 | 低 | 冻结：完全未裁剪 ⇒ 段级缺席、顶层 `[]` |
| 9 | **遗留（登记，不在本版范围）** | 池上界仍用**汇总** `Σdropped_tokens`（含质量规则丢弃 ⇒ 估值偏大）；收窄需再扩「按原因分桶的 token 观测」 | 低（T1 已封顶） | 设计 §3.15 登记为**后续可选项** |
| 10 | **遗留（受 D3/D4）** | 画像 LLM 提炼**真正生效**（受 D3）、`used_fragments` 跨仓往返（受 D4）、A 直连真实通道归属 | — | 判据执行器 `runtime_pending` **逐项标注未覆盖**（4 项） |

## 4. 完整性与一致性核对（对照设计基线 v1.6.1）

| 设计条目 | 实现落点 | 一致性 |
|----------|----------|:------:|
| §3.13 `segment_items` 最小契约（可选/行序对齐/缺省按无明细/只读/不落正文） | `_align_identities`／`_item_identity`／`to_record` | ✅ 逐条对齐 |
| §3.14＋ADR-149-07 竞争池（池上界/段序/段内序/默认关闭/fail-safe/回填观测） | `apply_context_budget` 池代码块 | ✅（段序按 `QUOTA_SEGMENTS` 稳定序，因无身份 ⇒ 与设计「无 score 排最后」一致） |
| §3.15 池语义边界与单一口径 | 死参数 `quota_override` 已删；质量规则结构性不可绕过 | ✅ |
| §3.16 原因码取值域／两级落点／排序／字段存在性／不变量 | `dropped` 实现与用例 | ✅ |
| §3.17 二次校验（判定口径／校正至多一次／不新增错误码／三标记） | `_verify_window` ＋ `to_record` | ✅ |
| §3.10 定稿取值域（两码／组件维度／不并入枚举） | `AUDIT_ACTION_CODES`／`build_component_failover_record` | ✅ |
| §3.18 逐组件路由落点语义（裁决/发布/回写；不切拓扑） | `channel.py`／`component_pipeline`／网关 | ✅ |
| §3.11 只接线（两条；门控不变；默认零变化；fail-open） | `evaluate` 两条预检／`profile_refine_gate`／`main.py` | ✅ |
| **实现偏离设计之处** | — | **无**（3 处设计补充均为**先补设计后实施**，非事后追认） |

## 5. 结论

**通过（自审）**：9 条 TD-ID 全部收口；10 项不变量均有**结构性论证 ＋ 反例护栏**；对照设计基线 **无未解释偏离**；发现并处置 **4 项既有实现缺陷 ＋ 3 项编期缺陷**；**遗留项 2 类已如实登记**（池上界收窄属后续可选项；运行态 4 项受 D3/D4）。

**待人工复核项**：① 池上界是否本版收窄（当前登记为后续项）；② §3.18 「本仓不切出站拓扑」是否与 OpenBase 侧 A 直连实现口径一致（跨仓）。

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-28 | AD-OpenLLM-Dev | 初始创建：矩阵 2 的判据↔落点四栏回溯、**10 项不变量结构性论证**、**发现与处置 7 项缺陷**、对照设计基线一致性核对、**遗留与待复核项如实登记**。状态 [Review] |
