# OpenBase-数据画像领域模型与标签/标注/评分关联关系设计说明-v1.1.0

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-DESIGN-DM-v1.1.0 |
| 版本 | v1.1.0 |
| 状态 | **[Review]** 统一升级（领域模型 + 前端概念分区；后端改造项待排期） |
| 日期 | 2026-11-21 |
| 编制 | 架构/后端（BE） |
| 适用范围 | DPS 标签体系、标注模板、画像（评分）模板、重算与画像快照；前端五类对象的概念分区与导航 |
| 关联文档 | 《OpenBase-DPS 统一前端页面功能设计》v2.7.0 §9；《DPS 画像模板与标注模板扩展设计文档 v2.10.0》 |
| 结论摘要 | 方向正确；需把“标签归属于标注模板”修正为“标注模板生产、标签实例归属人/档案、画像模板消费”，并补三项治理能力；前端同步按五类对象分区呈现 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | BE | 首版：领域模型分层、画像模板与标注模板三条关联通道、生命周期联动、6 项改造任务清单 |
| v1.0.1 | 2026-11-21 | BE | 依据代码审计修正两处表述：补充 `tag_bindings` 跨归属仅告警；明确维度词表校验为“标注侧已做、画像侧缺失” |
| v1.1.0 | 2026-11-21 | BE/FE | 统一升级：新增 §3.6 前端五类对象概念分区与呈现契约、G7 问题项、T-DM-07 任务；前端导航与五类落地页纳入同一设计包 |

---

## 1. 背景与结论

### 1.1 待确认的命题

> 标签归属于标注模板，标注模板关联评分（画像）模板，评分模板经过重算得出最终画像。

### 1.2 结论

1. **大方向正确**：数据画像本质是“标签驱动评分”，标注模板→画像模板→重算→画像快照的链路成立。
2. **一处需修正**：标签不是“归属于标注模板”，而是：
   - 标签**定义**归属于标签分类/维度（`tag_category` → `dimension_code`、`tag_value` 词表）；
   - 标签**实例**归属于人/档案（`profile_tag.profile_id/person_id`）；
   - 标注模板只是标签的**生产者之一**，通过 `source` 与 `annotation_template_code` 留痕；
   - 画像模板是标签的**消费者**，通过 `dimension_config.rules[].tag_code` 消费。
3. **不需要推翻现有架构**：DPS 当前实现已基本符合修正后的“生产者—消费者＋标签词表解耦”模型；需要补的是重算触发、版本失效、绑定单一事实源等治理能力。

## 2. 领域模型分层

```
L0 维度 / 标签词表    tag_category(dimension_code) + tag_value
        ↑ 共享语义层（跨模板复用，真正的“定义归属”）
L1 标签实例          profile_tag(person, tag_code, value/score, source, annotation_template_code)
        ↑ 生产者写入                     ↑ 消费者读取
L2 标注模板          field_schema: target_dimension + tag_key + score_map/score_direction
        │ template_code（强归属）
L3 画像（评分）模板   dimension_config.dimensions[].rules[tag_code, weight, type]
        │             + tag_bindings（治理/证据） + evidence_policy + anomaly_rules
L4 重算              resolve_dimensions → 读取 L1 → ScoringDispatcher 按 rule.type 打分 → 维度加权
L5 画像快照/版本      portrait + attributes_json[template_code] + portrait_template_history
```

三个易混概念必须拆开：

| 概念 | 归属对象 | 载体 | 说明 |
|---|---|---|---|
| 标签定义 | 标签分类/维度 | `tag_category`、`tag_value` | 全局语义，跨标注/画像模板复用 |
| 标签实例 | 人 / 画像档案 | `profile_tag` | 多来源并存，按规则择优 |
| 标签来源 | 标注模板 / AI / 人工 / 导入 | `source`、`annotation_template_code` | 用于溯源与优先级，不构成归属 |

## 3. 画像模板与标注模板的关联关系

两者之间存在**三条通道**：归属主链、治理反链、运行时软链。真正决定画像结果的是软链，不是外键。

### 3.1 通道 1：归属主链（强绑定、行政关系）

| 项 | 内容 |
|---|---|
| 字段 | `annotation_template.template_code` → `portrait_template.code` |
| 基数 | 画像模板 1 : N 标注模板；标注模板 N : 1 画像模板 |
| 约束强度 | 应用层强约束（`NOT NULL` ＋ `(template_code, scenario)` 索引），**非数据库外键** |
| 创建校验 | `template_code` 必填，父模板必须存在且 `status=active`，否则 400 |
| 变更校验 | 改挂时重新校验目标父模板存在且 active |
| 提交门禁 | 标注提交时校验 `annotation_template.template_code == 当前档案画像模板 code`，不匹配拒绝 |
| 业务含义 | 标注模板是画像模板的“采集契约”；同一画像模板可用 `scenario` 拆多个采集场景 |

代码依据：
- DDL：`DPS/src/ddl/schema_portrait.py` `annotation_template`（v2.10.0 段）
- 创建/更新：`DPS/src/engines/annotation_template_engine.py::create_template / update_template`
- 提交门禁：`DPS/src/engines/annotation_template_engine.py::validate_annotation_submission`

### 3.2 通道 2：治理反链（可选、证据与血缘）

| 项 | 内容 |
|---|---|
| 字段 | `portrait_template.tag_bindings[].annotation_template` → `annotation_template.code` |
| 基数 | 画像模板 1 : N 绑定（可为 0）；单条绑定指向 1 个标注模板 |
| 校验 | 引用标注模板必须存在且 active，否则模板保存被拒绝 |
| 跨归属 | 若引用的标注模板归属其他画像模板（或父模板），**仅记录 WARN，不阻断保存**（允许跨模板复用采集契约） |
| 用途 | 治理、预检、证据策略、可解释性、影响面分析 |
| 边界 | **不参与评分主流程**；评分只认 `dimension_config.rules[].tag_code` |

代码依据：`DPS/src/engines/template_engine.py` 中 `tag_bindings` 引用校验段（`annotation_template` 必填、存在性、active 校验）。

> 注意：`tag_bindings` 与 `dimension_config.rules[].tag_code` 是两套表达。当前一致性依赖预检/一致性扫描，不是保存期强约束（见 T-DM-03）。

### 3.3 通道 3：运行时软链（真正决定画像）

| 环节 | 机制 |
|---|---|
| 标签编码 | 标注字段声明 `target_dimension` ＋ `tag_key`，产出 `tag_code = "{dimension}:{tag_key}"` |
| 来源溯源 | 写入 `profile_tag` 时带 `source`（`manual_annotation`/`ai`）与 `annotation_template_code`，不建外键 |
| 多来源并存 | P1 唯一键包含 `source` 与 `annotation_template_code`，同一 `tag_code` 可由多个模板/AI 产出 |
| 择优 | 读取时 `manual_annotation > 其他来源 > legacy`，同优先级取最新 |
| 消费 | 画像模板按 `dimension_config.dimensions[].rules[].tag_code` 读取标签；`rule.type` 分派打分器；维度加权汇总 |
| 结果落库 | 默认模板写六维列；非默认模板写 `attributes_json[template_code]` 命名空间，互不覆盖 |

代码依据：
- 标签提取/来源：`DPS/src/engines/annotation_template_engine.py::build_tag_sync_entries` / `_insert_profile_tag`
- 多来源择优：`DPS/src/engines/portrait/crud.py::pick_preferred_tags`
- 模板解析与计算：`DPS/src/rest_api/routes/routes_profiles.py::api_calculate_portrait`、`DPS/src/engines/portrait/core.py::calculate_portrait`
- 打分分派：`DPS/src/engines/portrait/scoring.py`

**推论**：
1. 标注模板与画像模板解绑后，历史标签仍可被新画像模板消费（评分靠 `tag_code`）。
2. 同一批标签可用不同画像模板重算，得到不同画像快照（模板命名空间隔离）。
3. 标签缺失不会报错，按规则回退（`N/A` → 50 分或 `missing_score`），需在可解释性中如实呈现。

### 3.4 关联基数与约束汇总

| 关系 | 基数 | 强制 | 载体 |
|---|---|---|---|
| 画像模板 → 标注模板（归属） | 1:N | 必填、父模板 active | `annotation_template.template_code` |
| 标注模板 → 画像模板（被归属） | N:1 | 唯一 | 同上 |
| 画像模板 → 标注模板（治理绑定） | 1:N（可 0） | 可选、引用须 active | `portrait_template.tag_bindings[]` |
| 标注模板 → 标注记录 | 1:N | 运行期 | `annotation.template_id/code` |
| 标注模板 → 标签实例（来源） | 1:N | 溯源，非归属 | `profile_tag.source + annotation_template_code` |
| 标签实例 → 画像模板（消费） | N:M（按 tag_code/维度） | 软链 | `dimension_config.rules[].tag_code` |

### 3.5 生命周期联动

| 操作 | 现状 | 风险/说明 |
|---|---|---|
| 创建标注模板 | 父模板存在且 active | 否则 400 |
| 修改归属 | 重新校验目标父模板 active | 不校验历史标注与新父模板的一致性 |
| 停用画像模板 | 只改状态并写历史，不级联、不阻断 | 标注模板若仍 active，提交仍可能通过（见 T-DM-01） |
| 删除画像模板 | 存在子模板 / 标注模板 / `tag_lineage` 引用即拒绝 | 安全，但需前置提示引用明细 |
| 版本 | 两者版本独立 | 画像模板升级不会自动失效标注模板或历史画像（见 T-DM-02） |
| 继承/复合 | 归属只校验 active，不校验 `template_kind` | 标注可挂 composite/component；建议挂 component，composite 只做汇总 |
| 分类树 | 与归属无关 | 模板分类只影响治理检索，不改变 `template_code` |

### 3.6 前端概念分区与呈现契约（v1.1.0 新增）

> 目标：在菜单与页面上让使用者一眼区分五类对象，避免「标注模板 / 标注」「画像模板 / 画像」混用。

| 对象 | 业务角色 | 前端入口 | 页面标题 | 页面说明（职责边界） |
|---|---|---|---|---|
| 标签 | 语义定义与词表 | `/portrait/dps/tags`、`/portrait/tags` | 标签体系 / 标签分类与词表 | 被标注模板按维度引用、被画像模板按 `tag_code` 消费 |
| 标注模板 | 采集契约 | `/portrait/dps/annotation-templates` | 标注模板 | 定义字段与标签产出，必须归属一个画像模板 |
| 标注 | 采集记录 | `/portrait/dps/annotations` | 标注记录与审核 | 对具体对象录入、领取与审核；不含模板定义 |
| 画像模板 | 评分契约 | `/portrait/dps/templates` | 画像模板 | 定义维度、权重与打分规则，激活后参与计算 |
| 画像 | 计算结果 | `/portrait/list` | 画像结果 | 按画像模板重算生成的画像快照与版本 |

**导航分区**（顺序即业务链路）：

```
概览
标签 → 标注模板 → 标注 → 画像模板 → 画像
```

**统一概念组件 `ConceptNav`**：

| 项 | 约定 |
|---|---|
| 位置 | 五类对象落地页内容区首屏（`PageContainer` 默认插槽顶部） |
| 内容 | 五类对象＋一句话角色＋当前项高亮（`aria-current="page"`） |
| 跳转 | 标签 → 标注模板 → 标注 → 画像模板 → 画像 |
| 一致性 | 五个落地页必须出现且当前项唯一高亮；跳转目标与导航、路由三处一致 |

**文案与命名规则**：

1. 「模板」单独出现时必须带定语：**标注模板**（采集契约）或 **画像模板**（评分契约）。
2. 「标注」专指采集记录与审核动作；「标注模板」专指字段与标签产出的定义。
3. 「画像」专指计算结果的快照与版本；「画像模板」专指评分口径。
4. 「标签」为定义与实例的统称，页面说明需注明是词表维护还是实例查看。
5. 页面标题禁用模糊词（如「模板中心」「标注作业台」「标签管理」），统一使用五类对象名词。

**验收标准**：

- 菜单为六组（概览＋五类对象），五类对象各自成组；
- 五个落地页均渲染 `ConceptNav`，当前项唯一高亮；
- 页面标题不含模糊词，说明文案明确“契约 / 记录 / 结果”边界；
- 路由、权限与接口契约不变，仅调整分组、标题与说明。

## 4. 端到端数据流

```
① 模板准备
   画像模板（维度/规则/权重/证据策略） → 发布 active
   标注模板（template_code 归属、field_schema、target_dimension） → 发布 active
   校验：target_dimension ∈ 标签分类 dimension_code（保存期）
   校验：tag_bindings.annotation_template 存在且 active（保存期）

② 采集与审核
   标注提交 → 归属门禁（template_code 匹配）→ 字段 schema 校验
   审核通过 → build_tag_sync_entries → upsert profile_tag
              （tag_code, score, source=manual_annotation, annotation_template_code）

③ 重算
   POST /portrait/calculate（可 template_code、async=true 幂等）
   resolve_dimensions（支持继承/复合）→ 按维度读取标签 → 择优 → 打分 → 加权
   → portrait 快照 / attributes_json[template_code]

④ 查看与治理
   画像详情按模板展示；历史版本、变更 diff、一致性扫描、可解释性
```

**当前链路断点**：第②步审核通过后**不会自动触发**第③步重算，需要显式调用计算接口（见 T-DM-05）。

## 5. 设计评价

### 5.1 保留项（设计合理）

| 项 | 理由 |
|---|---|
| 标注模板强归属画像模板 | 采集契约服务于评分契约，便于治理与责任划分 |
| 标签实例与人/档案绑定 | 支持跨模板复用、多来源证据、历史追溯 |
| 评分规则可插拔 | `ScoringDispatcher` 扩展不改主流程 |
| 多模板结果命名空间隔离 | 六维列保留默认模板语义，非默认模板不互相覆盖 |
| 删除保护 | 下游引用检查覆盖子模板、标注模板、标签血缘 |

### 5.2 问题项（需改造）

| 编号 | 问题 | 影响 | 对应任务 |
|---|---|---|---|
| G1 | 停用画像模板不阻断采集 | “画像已停用但仍在产出标签” | T-DM-01 |
| G2 | 模板版本升级后画像无失效标记 | 读到旧口径画像且无提示 | T-DM-02 |
| G3 | `tag_bindings` 与 `dimension_config.rules` 双处表达 | 治理与评分口径漂移 | T-DM-03 |
| G4 | 多来源择优规则硬编码 | AI/人工优先级不可按模板调整 | T-DM-04 |
| G5 | 标签变更不自动重算 | 审核后画像滞后，依赖人工操作 | T-DM-05 |
| G6 | 维度词表在画像侧保存期未校验（标注侧已有条件强校验） | 画像维度与标签分类编码漂移，运行时才暴露 | T-DM-06 |
| G7 | 前端菜单与页面命名混用五类对象（模板中心 / 标注作业台 / 标签管理） | 使用者无法区分契约、记录与结果 | T-DM-07 |

### 5.3 非目标（明确不做）

- 不把标签实例改为标注模板子表（破坏复用与多来源）。
- 不反转“标注模板 → 画像模板”的归属方向。
- 不改默认六维画像的存量口径与结果存储位置。
- 不引入跨服务消息中间件（T-DM-05 采用进程内任务/任务表即可）。

## 6. 改造任务清单

> 优先级：P1＝本迭代建议完成；P2＝下一迭代。所有任务均须遵循五步流程与文档版本管理。

### T-DM-01 停用画像模板的采集门禁（P1）

| 项 | 内容 |
|---|---|
| 目标 | 父画像模板非 `active` 时，禁止新标注提交与新标签产出 |
| 实现点 | `validate_annotation_submission` 增加父模板状态校验（按 `template_code` 查询 `portrait_template.status`）；`deactivate` 响应返回受影响标注模板数量 |
| 兼容 | 历史标注只读展示不受影响；已提交数据不回滚 |
| 验收 | 父模板 inactive ＋ 标注模板 active → 提交 400/409 且文案明确；停用接口返回引用数；单测覆盖 |
| 测试 | `test_annotation_template_v2_10.py` 增补；新增停用后提交用例 |
| 风险/回滚 | 可能影响既有自动化脚本；提供开关 `enforce_active_parent`，默认开启，异常时可临时关闭 |

### T-DM-02 模板版本对齐与画像 stale 标记（P1）

| 项 | 内容 |
|---|---|
| 目标 | 画像模板版本变更（update/rollback）后，既有画像标记 `stale`，重算成功后清除 |
| 实现点 | portrait/attributes_json 增加 `template_version`；新增 `stale` 判定（对比当前模板版本）；列表/详情返回 `stale` 与 `template_version`；重算写入新版本 |
| 验收 | 升级模板后既有画像 stale=true；重算后 false；接口可过滤 stale；历史版本仍可查 |
| 测试 | 模板升级→查询→重算→再查询的链路用例 |
| 风险/回滚 | 只增量字段，无迁移破坏；stale 为派生标记，可随时重算修正 |

### T-DM-03 标签→维度绑定单一事实源（P1）

| 项 | 内容 |
|---|---|
| 目标 | 明确 `dimension_config.rules[].tag_code` 为评分唯一事实源；`tag_bindings` 仅治理/证据 |
| 实现点 | 模板保存时校验：`tag_bindings` 引用的 `tag_code` 必须出现在规则或显式 allowlist；将一致性扫描前移到保存/预检；文档与 UI 标注字段语义 |
| 验收 | 不一致保存返回 400 或明确 warn（按策略）；预检展示差异清单；存量数据迁移 dry-run 可查 |
| 测试 | 模板保存一致性用例；预检差异用例 |
| 风险/回滚 | 存量模板可能不合规，先以 warn 模式上线，再切拒绝 |

### T-DM-04 来源优先级显式化（P2）

| 项 | 内容 |
|---|---|
| 目标 | 多来源同 `tag_code` 的择优规则可配置，默认保持现状 |
| 实现点 | 画像模板/维度支持 `source_precedence`；`pick_preferred_tags` 接受优先级参数；可解释性记录胜出来源与落选原因 |
| 验收 | 配置 `manual_annotation > ai > import` 生效；未配置时与现状完全一致（向后兼容） |
| 测试 | 多来源冲突用例；默认行为回归 |
| 风险/回滚 | 配置错误会导致画像偏移；提供模板级开关与预检对比 |

### T-DM-05 标签变更自动触发重算（P2）

| 项 | 内容 |
|---|---|
| 目标 | 审核通过、AI 确认、人工改标签后，自动按受影响模板去抖重算 |
| 实现点 | 标签写入后发 `tag.changed(person, dimensions, template_code)`；任务表按 `person+template_code` 去重；复用 `POST /portrait/calculate?async=true` 幂等键；失败重试上限与告警 |
| 验收 | 审核通过后任务可见并在约定时间内完成；重复事件合并；可通过配置关闭 |
| 测试 | 事件合并、幂等复用、失败重试用例 |
| 风险/回滚 | 批量审核可能触发大量重算；默认按模板+人员去抖，并提供批量窗口合并 |

### T-DM-06 维度词表跨层保存期校验（P2）

| 项 | 内容 |
|---|---|
| 目标 | 标注 `target_dimension`、标签分类 `dimension_code`、画像维度 `code` 三层一致 |
| 现状 | 标注侧已实现：`target_dimension` 按标签分类 `dimension_code` 强校验（标签目录至少配置一个维度编码时启用）；画像侧尚未实现 |
| 实现点 | 画像模板保存时校验维度 code 存在于标签分类；标注模板保存保留现有校验；预检输出三层缺口清单 |
| 验收 | 不存在的维度保存被拒绝；预检可列出缺口；存量差异有报告 |
| 测试 | 三层映射正/反用例；预检缺口用例 |
| 风险/回滚 | 存量模板可能缺维度；先告警后阻断，分环境灰度 |

### T-DM-07 前端五类对象概念分区（P1，随本次统一升级实施）

| 项 | 内容 |
|---|---|
| 目标 | 菜单与页面明确区分标签、标注模板、标注、画像模板、画像，消除同词混用 |
| 现状 | 已随本次统一升级实施（前端 v1.9.0）：导航改为六组、五类落地页接入 `ConceptNav`、标题与说明统一 |
| 实现点 | `modules/portrait/index.ts` 六分组导航；新增 `modules/portrait/components/ConceptNav.vue`；标签/标注模板/标注/画像模板/画像落地页标题与说明对齐 §3.6；画像结果页、评分规则页、关系总览文案同步 |
| 验收 | 菜单六组；五个落地页 `ConceptNav` 当前项唯一高亮；标题无模糊词；路由/权限不变；`nav-consistency` 通过 |
| 测试 | 新增 `tests/portrait-concept-nav.spec.ts`（五对象、高亮、跳转）；回归 `tests/nav-consistency.spec.ts` |
| 风险/回滚 | 纯前端分组与文案；回滚仅还原导航与组件引用，不影响路由、权限与接口 |

### 6.1 实施顺序与依赖

```text
T-DM-01 停用门禁 ──┐
T-DM-03 单一事实源 ─┼─→ T-DM-06 三层校验（依赖前两者稳定）
T-DM-02 版本 stale ─┼─→ T-DM-05 自动重算（依赖 stale/版本口径）
T-DM-04 来源优先级 ─┘（独立，可与 02/05 并行）
T-DM-07 前端概念分区（已实施，独立）
```

| 优先级 | 任务 | 预估影响面 |
|---|---|---|
| P1 | T-DM-01、T-DM-02、T-DM-03、T-DM-07（已实施） | DPS 引擎＋模板保存/预检＋画像列表字段＋前端导航/页面 |
| P2 | T-DM-04、T-DM-05、T-DM-06 | 评分读取、任务调度、模板校验 |

## 7. 验收与追溯

| 需求 | 设计章节 | 验收 |
|---|---|---|
| 明确标签/标注/画像三者关系 | §2、§3 | 文档评审通过 |
| 修正“标签归属标注模板”表述 | §1.2、§3.3 | 评审确认 |
| 关联关系可落地 | §3.4、§3.5 | 与代码实现逐项对照无冲突 |
| 改造任务可执行 | §6 | 每项含实现点/验收/测试/回滚 |
| 不破坏存量画像口径 | §5.3 | 默认模板六维结果不变 |
| 前端五类对象可区分 | §3.6、T-DM-07 | 菜单六组＋五页 `ConceptNav`＋`nav-consistency` 通过 |

## 8. 附录

### 8.1 术语

| 术语 | 定义 |
|---|---|
| 画像模板 | 定义维度、规则、权重、证据策略的评分模板（`portrait_template`） |
| 标注模板 | 定义采集字段与标签产出的模板（`annotation_template`），强归属画像模板 |
| 标签定义 | 标签分类/词表中的语义项（`tag_category`/`tag_value`） |
| 标签实例 | 某个人在某维度上的标签值（`profile_tag`） |
| 标签来源 | 标签实例的产出方（人工标注/AI/导入等） |
| 软链 | 通过 `tag_code`/维度而非外键建立的消费关系 |
| stale | 画像结果与当前模板版本不一致的派生标记 |

### 8.2 关键代码索引

| 主题 | 位置 |
|---|---|
| 标注模板 DDL / 归属索引 | `DPS/src/ddl/schema_portrait.py` |
| 标注模板创建/更新/归属校验 | `DPS/src/engines/annotation_template_engine.py` |
| 标签提取与来源写入 | 同上 `build_tag_sync_entries` / `_insert_profile_tag` |
| 画像模板 DDL / 维度/绑定 | `DPS/src/ddl/schema_portrait.py` |
| `tag_bindings` 引用校验 | `DPS/src/engines/template_engine.py` |
| 删除引用保护 / 启停 | 同上 `delete_template` / `_set_status` |
| 多来源择优 | `DPS/src/engines/portrait/crud.py::pick_preferred_tags` |
| 打分分派 | `DPS/src/engines/portrait/scoring.py` |
| 画像计算 | `DPS/src/engines/portrait/core.py::calculate_portrait` |
| 计算路由 / 模板命名空间 | `DPS/src/rest_api/routes/routes_profiles.py` |
