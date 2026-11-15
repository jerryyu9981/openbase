# OpenBase 画像业务全流程与前端易用性分析

- 版本：v1.1.0
- 状态：[Implemented]（P0 + 画像 360 + 审核服务端补全已交付，2026-11-15；见 §13 实施回填）
- 适用环境：Dev / Test / Pro
- 作者：AI 编码代理
- 评审：产品/业务负责人、DPS 技术负责人、前端负责人
- 日期：2026-11-15

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-15 | 首版：DPS 标注→模板→打分→画像→证据全链路梳理、前端可达性盘点、优势与不足、P0/P1/P2 完善方案与验收标准 | AI 编码代理 |
| v1.1.0 | 2026-11-15 | 决策确认并实施：范围 = P0 + 画像 360；审核未带 fields 由服务端补全；规则引擎页改只读总览。回填 9 项改动、验证结果与遗留项 | AI 编码代理 |

---

## 1. 文档目的与范围

本文回答三个问题：

1. **DPS 到底怎么用**：标注、标注模板、画像模板、规则引擎、画像计算、证据/血缘、版本与预检，各自是什么、谁在什么时候用、彼此如何咬合。
2. **前端现在能不能走通**：每个能力在 OpenBase 前端有没有入口、入口是否顺畅、断在哪一步。
3. **下一步怎么改**：按「见效快 / 补断链 / 做体验」三档给出可执行方案与验收口径。

范围：DPS 画像域（`/api/v2/portrait/**`）+ OpenBase 代理（`/api/v1/dps-proxy/**`）+ 前端画像模块（`openbase-ui/src/modules/portrait/**`）。
不在范围：数据源接入、标签加工调度、算法模型训练。

---

## 2. 系统全景

### 2.1 角色与诉求

| 角色 | 诉求 | 主要动作 |
|---|---|---|
| 模板管理员 | 定义「怎么算分」 | 建画像模板 → 配维度/规则/权重 → 校验/试算 → 激活 |
| 标注模板设计者 | 定义「采集什么」 | 建标注模板（强归属某画像模板）→ 配字段 → 挂目标维度 |
| 采集/录入员 | 把事实变成结构化数据 | 按标注模板填单 → 提交（pending） |
| 审核员 | 把关数据质量 | 单条/批量通过、驳回、要求修改 |
| 业务使用者 | 看结果 | 查画像 → 看维度分/标签/证据 → 触发重算 |
| 治理/运维 | 变更可控 | 预检、影响面、版本对比、回滚、血缘反查 |

### 2.2 核心实体关系

```
画像模板 portrait_template (code, version, status, extends)
  ├─ dimension_config  → 维度[code,name,weight] → 规则[{key,type,weight,mapping|intervals|when}]
  ├─ attributes_schema → {分组: [字段key]}
  ├─ tag_bindings      → [{dimensions:[...], annotation_template}]
  ├─ evidence_policy   → 证据保留策略
  └─ anomaly_rules     → {规则名:{condition,action}}
        ▲ 强归属（必须 active）
标注模板 annotation_template (code, template_code, scenario, field_schema[], version)
        ▲ 按 schema 校验 + 归属门禁
标注 annotation (person_id, payload, review_status: pending/approved/rejected/modified)
        │ approved 且带 fields
        ├─→ profile_tag（标签联动，人工优先）
        └─→ tag_lineage（来源谱系，只读旁路）
                 ▲ 参与打分
画像 profile（六维列 = 默认模板；attributes_json[template_code] = 其他模板命名空间）
```

### 2.3 数据流（一次完整闭环）

```
① 模板管理员配模板(dimension/rule/weight) ──save──> portrait_template(vN, history 快照)
② 激活 active ──> TemplateRegistry 预热（只加载 active）
③ 设计标注模板(字段+target_dimension) ──强归属校验──> annotation_template
④ 录入结构化标注 ──归属门禁+schema 校验──> annotation(pending)
⑤ 审核通过(+回传 fields) ──> profile_tag + tag_lineage
⑥ 触发计算 ──> 维度分(规则加权) → 总分(维度加权) → confidence/completeness → profile
⑦ 查看画像 ──> 维度分/标签/证据（缺省 50 分、partial 状态需可解释）
```

---

## 3. 端到端使用流程（含每步断点）

### 3.1 步骤 1：创建画像模板

- 前端入口：`/portrait/dps/templates` → 「新建模板」→ `/portrait/dps/templates/new`（模板工作台）。
- 后端接口：`POST /dps-proxy/templates`（→ `POST /api/v2/portrait/templates`）。
- 关键约束（`engines/template_engine.py`）：
  - `code` 全局唯一、创建后不可改；重复 → 409。
  - `status` 默认 `draft`；**只有 `active` 才会被 `TemplateRegistry` 加载**，非 active 模板无法用于计算。
  - `extends` 深度 ≤ 2、禁自指/成环；解析规则为「父维度先入 → 子覆盖同名 → 追加新维度」。
  - 规则 `type` 必须命中 `ScoringDispatcher` 白名单（6 类），否则不可激活。
- 断点：
  - 保存成功后**没有「下一步」引导**，用户不知道必须激活。
  - 「激活」按钮只在列表页操作列，工作台内无激活动作，需退出再进。

### 3.2 步骤 2：配置维度 / 规则 / 属性 / 绑定 / 证据 / 异常

- 前端入口：模板工作台 6 段（基础信息 / 维度与权重 / 属性字段 / 标签绑定 / 证据策略 / 异常规则），右侧常驻问题清单。
- 后端接口：`POST /dps-proxy/templates/{code}/validate`（可校验未保存草稿）、`POST /dps-proxy/templates/{code}/preview`（样例试算）、`GET /dps-proxy/meta/schema`（算子/规则参数模式）。
- 能力现状：分段导航 + 权重合计实时校验 + 问题清单点击定位 + 6 类规则表单 + 嵌套条件组 + 试运行抽屉（scored/skipped/missing/error 四态）。
- 断点：
  - `attributes_schema` 真实契约是 `{分组: [字段key]}`，字段没有类型/必填/选项等元信息 —— 而**标注模板**里的字段才有 `type/required/options`。两套字段模型语义不同却都叫「字段」，用户极易混淆。
  - `tag_bindings` 真实契约是 `[{dimensions, annotation_template}]`，没有「tag_code → 维度」的行级映射；用户在维度规则里用的 `key`（如 `basic:age_stage`）与标注字段 `key` 是否同源，界面没有任何校验或提示。
  - `evidence_policy` 是自由对象，只做到「已知键可视化 + 未知键透传」，业务人员看不懂保留策略的实际效果。

### 3.3 步骤 3：创建标注模板

- 前端入口：`/portrait/dps/annotation-templates`（列表 + 新建弹窗）→ `/portrait/dps/annotation-templates/{code}/fields`（字段与归属）。
- 后端接口：`POST/PUT/GET/DELETE /dps-proxy/annotation-templates[/{code}]`。
- 关键约束（`engines/annotation_template_engine.py`）：
  - `template_code` 必填，且**必须指向状态为 active 的画像模板**；未激活 → 400。
  - `scenario ∈ {intake, assess, check, general}`。
  - `field_schema` 非空数组，`key` 唯一；`type ∈ {string, enum, number, date, list}`；`enum` 必须给 `options`。
  - 每次更新 `version` 自动 +1（v1→v2…）。
  - 字段的 `target_dimension` 是「标注 → 标签联动」的唯一挂钩；**不填则该字段只落库、不产生标签、不影响画像**。
- 断点：
  - 界面对 `target_dimension` 的取值无候选下拉（应来自所属模板的维度 code），属高风险自由文本。
  - 字段表未提示「哪些字段会进入画像」——用户无法判断配了有没有用。

### 3.4 步骤 4：录入标注

- 前端入口：**不存在**。`dpsApi` 只有 `submitReview` / `batchReviewAnnotations`，没有创建标注的方法；OpenBase 代理也**未暴露** `POST /portrait/annotate` 与标注查询接口。
- 后端能力：`POST /api/v2/portrait/annotate`（`action=create`）支持两支：
  - 结构化：带 `annotation_template` + `fields` → 归属门禁 + 字段 schema 校验（未知字段、必填缺失直接 400）→ 落 `annotation(pending)`。
  - 自由文本：仅 `content`，不参与标签联动。
- 结论：**标注链路在 UI 上是断的**。管理员能配标注模板、能复核 AI 候选，但业务人员无法录入人工标注。

### 3.5 步骤 5：审核与标签联动

- 前端入口：`/portrait/dps/annotation-adapters`（AI 标注候选与复核），可单条提交复核、可批量复核。
- 后端接口：`POST /dps-proxy/annotations/{id}/review`、`POST /dps-proxy/annotations/batch-review`。
- 关键规则（`routes_profiles.py::_apply_annotation_review` / `_sync_tags_after_approval`）：
  - 状态机：`pending → approved | rejected | modified`；`rejected → pending`；`approved/modified` 为终态。
  - **只有 approved 且请求体同时带 `annotation_template` + `fields` 时才触发标签联动**；未带则 `tag_sync = null`，静默不生效。
  - AI 候选必须先人工复核，否则 `assert_portrait_eligible` → 409。
  - 联动评分：枚举按选项**逆序**线性映射（首项 100、末项 0）；数值裁剪 0~100；其他有值类型固定 80。
  - 联动成功后写 `tag_lineage`（失败不影响主链路）。
- 断点：
  - 「必须回传 fields」是隐性契约，前端若只提交 `status` 就通过，标签不会写入且无任何提示 —— 这是最容易被误判为「系统坏了」的坑。
  - 无人工标注列表页，review 只能对 AI 候选操作。

### 3.6 步骤 6：计算画像

- 前端入口：`/portrait/list` → 「计算画像」弹窗（`PortraitList.vue`）。
- 后端接口：`POST /dps-proxy/portraits/calculate`（支持 `?async=true` → 202 + task_id，幂等键 `sha256(tenant:person:template:data_version)`）。
- 计算口径（`engines/portrait/core.py` + `scoring.py`）：
  - 维度集合 = 指定模板经 `TemplateRegistry.resolve_dimensions` 解析（含 extends 继承）；缺省为六维常量。
  - 规则 `when` 前置求值（18 算子、最大嵌套深度限制），条件非法按**不命中**处理并告警。
  - 单规则 → 0~100 分；缺值按 **50 分**；维度分 = 规则加权；总分 = 维度加权。
  - `confidence` 为维度均值；`data_completeness < 0.8` 或存在缺失维度 → `status = partial`。
  - 非默认模板结果写 `attributes_json[template_code]` 命名空间；`GET /portrait/{id}?template_code=` 读取。
- 断点：
  - 模板 code 是**手填文本框**，无 active 模板下拉；未激活时报 400「模板不存在或未激活」，前端只显示「画像计算失败」。
  - 计算完成后只刷新列表，没有「查看刚算出的画像」直达。
  - `partial` / 缺省 50 分在详情页没有任何解释（详情页把维度当 JSON 原样打印）。

### 3.7 步骤 7：查看画像

- 前端入口：`/portrait/{id}`（画像详情）、`/portrait/search`（画像搜索）、`/portrait/overview`（数据总览）。
- 现状：
  - 详情页「画像维度」区块是 `<pre>{{ JSON.stringify(dimValue) }}</pre>` 原样输出；标签是字符串数组平铺。
  - 「编辑属性」是裸 JSON textarea（PATCH 语义：对象递归合并、数组去重追加、标量覆盖、null 删除键）。
  - 搜索页实为 `listPortraits(page=1,page_size=100)` 拉全量后前端过滤，未使用 DPS 的 `/portraits/search`。
- 断点：无法回答「这个分数怎么来的」「哪些标注贡献了这个标签」「模板改了之后分数变了吗」。

### 3.8 步骤 8：治理（预检 / 影响面 / 版本 / 回滚 / 血缘 / 措施）

| 能力 | 前端入口 | 后端 | 现状问题 |
|---|---|---|---|
| 预检 | `/portrait/dps/templates/{code}/preflight` | `GET /templates/{code}/preflight` | 只统计「标注模板数 / 标注数 / 标签数」，**不告诉你会影响多少个画像** |
| 影响面 | 同上 + 血缘页 | `GET /lineage/impact` | `field_key` 维度不支持 → 400 |
| 版本对比 | `/portrait/dps/templates/{code}/versions` | `GET /templates/{code}/diff?from=&to=` | **无版本列表接口**，from/to 需手填或猜 |
| 回滚 | 同上 | `POST /templates/{code}/rollback` | 无「回滚将覆盖哪些内容」的预览 |
| 血缘反查 | `/portrait/dps/lineage` | `GET /lineage/tags/{tag_code}` | 无谱系直接 404，空态与失败态未区分 |
| 措施建议 | `/portrait/dps/measures` | `GET /measures/suggest?person_id=` | 需手填 person_id，无主体选择器 |
| 模板包 | `/portrait/dps/template-packages` | `export` / `import(dry_run)` | 与工作台割裂，无法「从包新建模板」 |

---

## 4. 功能地图：后端能力 → 前端可达性

| # | DPS 能力 | 接口 | 前端页面 | 可达 |
|---|---|---|---|---|
| 1 | 画像模板 CRUD + 启停 | `/portrait/templates**` | 模板族管理 / 工作台 / JSON 编辑 | ✅ |
| 2 | 模板校验（草稿可校验） | `/templates/{code}/validate` | 工作台「校验」 | ✅ |
| 3 | 样例试算 | `/templates/{code}/preview` | 工作台「试运行」 | ✅ |
| 4 | 元数据（算子/规则参数） | `/meta/schema` | 工作台（内部消费） | ✅ |
| 5 | 深度 2 继承 | `extends` | 工作台基础信息 | ✅ |
| 6 | 版本 diff / 回滚 | `/templates/{code}/diff|rollback` | 版本对比与回滚 | ⚠️ 无版本列表 |
| 7 | 预检 + 影响面 | `/templates/{code}/preflight` | 预检与影响面 | ⚠️ 口径不足 |
| 8 | 标注模板 CRUD | `/annotation-templates**` | 标注模板管理 / 字段与归属 | ✅ |
| 9 | 标注录入（结构化/文本） | `POST /portrait/annotate` | — | ❌ 未接入 |
| 10 | 标注查询 | `POST /portrait/annotate(action=query)` | — | ❌ 未接入 |
| 11 | 审核状态机 | `/annotations/{id}/review` | AI 候选与复核 | ⚠️ 仅 AI 候选 |
| 12 | 批量复核 | `/annotations/batch-review` | AI 候选与复核 | ✅ |
| 13 | 标签联动 + 谱系 | review 内嵌 | 血缘反查（只读） | ⚠️ 隐式触发 |
| 14 | 画像计算（同步/异步/幂等） | `/portrait/calculate` | 画像列表「计算画像」 | ⚠️ 手填模板 |
| 15 | 画像查询（按模板口径） | `GET /portrait/{id}?template_code=` | 画像详情 | ❌ 未用 template_code |
| 16 | 高级检索 | `POST /portraits/search` | 画像搜索（前端过滤替代） | ❌ 未接入 |
| 17 | 检索建议 | `GET /portraits/suggestions` | — | ❌ |
| 18 | 版本/对比/趋势 | `/portrait/version|compare|trend` | — | ❌ |
| 19 | 风险 / 关联 / 统计 / 轨迹 | `/portrait/risk-assess|associate|statistics|track` | — | ❌ |
| 20 | AI 分析/检测/预测 | `/portrait/ai/*` | — | ❌ |
| 21 | 措施建议 | `/measures/suggest` | 措施建议 | ⚠️ 手填 ID |
| 22 | 评分类型 | `/scoring-types` | 评分类型 | ✅ |
| 23 | 标签体系 | `/tags/**` | 标签管理 / 标签体系查看 | ✅ |
| 24 | 模板包 | `/template-packages/*` | 模板包导出/导入 | ⚠️ 与工作台割裂 |

> 结论：**24 项能力中，完全可达 9 项、部分可达 9 项、前端完全不可达 6 项**。不可达集中在「标注录入」与「画像深读」，恰好是业务闭环的两端。

---

## 5. 现状优势

1. **后端能力完整且契约稳定**：模板继承（深度 2）、版本快照（`portrait_template_history.snapshot` 可重建任一版本）、6 类打分白名单分派、`when` 条件组（18 算子）、标签联动 + 血缘、AI 复核门禁、租户隔离、双后端（SQLite/PG）适配均已落地并有测试覆盖。
2. **「零 JSON 配置」已具备技术前提**：`/meta/schema` 把算子、规则参数模式、示例下发前端；`/validate` 支持未保存草稿；`/preview` 可 dry-run 逐规则得分 —— 表单驱动 + 即时反馈的闭环是通的。
3. **工作台交互模型正确**：左侧分区 + 中间编辑 + 右侧问题清单，权重合计实时校验、问题可点击定位、未知键透传不丢配置。这套模型应作为后续所有配置页的统一范式。
4. **安全边界清晰**：前端从不直连 DPS，OpenBase 代理统一注入身份头（`X-Org-Id`/`X-Tenant-Id`/`X-Proxy-Source`/`X-Request-Id`），前端不可伪造。
5. **可观测与留痕到位**：变更写 history、联动写 lineage、审核留 reviewer/comment、批量复核逐条返回、错误带 `request_id`。

---

## 6. 现状不足

### A. 信息架构与术语（用户找不到、看不懂）

| # | 问题 | 证据 |
|---|---|---|
| A1 | 导航「画像管理」下的**「规则引擎」页是本地 mock**（`const rules = ref([...])`、注释「本地画像规则数据，不调用真实 API」），与 DPS 真实规则（模板内 `dimension_config.rules`）无关，用户会误以为在此配置的规则生效 | `pages/Rules.vue:154,163-171` |
| A2 | 两套「字段」概念同名不同义：画像模板 `attributes_schema = {分组:[key]}`（无类型）；标注模板 `field_schema = [{key,type,required,options,target_dimension}]`。界面均称「字段」 | `templates/model.ts`、`pages/DpsAnnotationFieldView.vue` |
| A3 | 术语直接暴露：`extends`、`tag_bindings`、`evidence_policy`、`anomaly_rules`、`scenario`、`coverage`、`instance`、`dimension_config` 无解释层 | 工作台各分区表单 |
| A4 | 模板配置、标注模板配置、采集、审核、查看画像分布在 5 个菜单项，无统一入口或向导 | `modules/portrait/index.ts:55-78` |
| A5 | 路径双写：列表/详情抽屉仍硬编码 `/dps/...`（旧路径），依赖 `legacyRedirects` 兜底 | `DpsTemplateListView.vue:48-49,81-84`、`DpsAnnotationTemplateView.vue:34` |

### B. 流程断点（走不通、走一半）

| # | 问题 | 影响 |
|---|---|---|
| B1 | **无标注录入页**，代理未暴露 `POST /portrait/annotate`，`dpsApi` 无创建标注方法 | 人工标注无法入库，画像只能依赖存量标签与 AI 候选 |
| B2 | **无标注列表/待办页**，review 只能对 AI 候选调用 | 审核员无法处理人工标注队列 |
| B3 | 审核「必须回传 `fields` 才触发标签联动」是隐性契约，前端不传则静默不生效 | 审核显示成功但画像分数不变，被误判为系统缺陷 |
| B4 | 模板保存后无「激活」引导，工作台内无激活操作；未激活 → 计算 400 | 首次使用者 100% 卡在第 6 步 |
| B5 | 标注模板字段的 `target_dimension` 无候选下拉，且未提示「不填则不进画像」 | 配了一堆字段但不产生标签 |
| B6 | 计算入口模板 code 为手填文本框 | 拼错即失败，且报错信息被统一为「计算失败」 |
| B7 | 措施建议需手填 `person_id` | 业务人员不知道 ID 从哪来 |

### C. 结果可读性（看不到、看不懂）

| # | 问题 | 证据 |
|---|---|---|
| C1 | 画像详情「画像维度」以 `<pre>{{ JSON.stringify(dimValue) }}</pre>` 原样输出 | `PortraitDetail.vue:73-81` |
| C2 | 无维度分/总分/置信度/完整度/`partial` 状态的语义化展示，缺省 50 分无标注 | `PortraitDetail.vue` |
| C3 | 无证据链、无时间线、无版本对照、无「分数怎么来的」下钻 | 全站缺失 |
| C4 | 标签为字符串平铺，未按维度分组、无来源/置信度 | `PortraitDetail.vue:67-72` |
| C5 | 「编辑属性」为裸 JSON textarea | `PortraitDetail.vue:85-104` |
| C6 | 搜索为前端过滤前 100 条，超量漏检 | `PortraitSearch.vue:177` |

### D. 契约与一致性（技术债）

| # | 问题 |
|---|---|
| D1 | **无模板版本列表接口**（只有 diff/rollback），前端无法列出所有版本号 |
| D2 | 预检影响面仅「标注模板数/标注数/标签数」，缺「受影响画像数/受影响主体数」 |
| D3 | `lineage/impact` 不支持 `field_key` 维度（400），与「影响面三层」设计不完全一致 |
| D4 | 同一个 DPS 能力存在两套实现（工作台 vs 旧 JSON 编辑页 vs 旧规则页 mock），维护面扩大 |
| D5 | 代理未暴露 `/portrait/list`、`/portrait/{id}/tasks`、`/version`、`/compare`、`/trend`、`/statistics`、`/risk-assess`、`/portraits/search` 等只读能力 |

### E. 性能与健壮性

| # | 问题 |
|---|---|
| E1 | 同步计算为长请求；前端虽有异步任务轮询，但计算入口未默认走 async |
| E2 | 大模板（>200 节点）工作台未做虚拟滚动/分区懒渲染 |
| E3 | 试运行结果无「保存为测试用例」留痕能力（设计稿曾提出） |
| E4 | 部分页面错误只弹 toast，无 request_id 呈现，不利于定位 |

---

## 7. 目标体验原则

1. **一条主线**：模板 → 标注模板 → 采集 → 审核 → 成像 → 看结果，主线上的每一步都有「下一步」按钮，用户不需要靠记忆找菜单。
2. **术语不裸奔**：每个配置项旁边有「这是什么/举个例/不填会怎样」三段式说明；内部键名只在 JSON 视图中出现。
3. **结果可解释**：任何分数都能下钻到「哪条规则、哪个标签、哪个标注、哪次采集」。
4. **错误可自救**：后端 `detail` 原文展示 + 一键修复动作（去激活、去补字段、去配维度）。
5. **危险操作先看影响**：激活/回滚/停用前必须看到「影响多少模板/标注/画像」。

---

## 8. 完善方案

### 8.1 P0：消除误导与首个卡点（纯前端为主，可快速交付）

| 编号 | 方案 | 落点 | 验收 |
|---|---|---|---|
| P0-1 | 「规则引擎」页改造为**规则总览**：读取 active 模板的维度/规则/权重只读摘要 + 「去工作台编排」按钮；删除本地 mock 数据 | `pages/Rules.vue` | 页面不再出现与真实配置无关的规则；任一规则可点击跳转到工作台对应维度 |
| P0-2 | 画像详情「可用化」：维度分数改为进度条 + 总分/置信度/完整度/状态徽标；标签按维度分组；`partial` 与「缺省 50 分」就地解释 | `pages/PortraitDetail.vue` | 不看 JSON 即可读懂分数构成；`partial` 有明确原因文案 |
| P0-3 | 详情页支持**模板口径切换**：`GET /portraits/{id}?template_code=`（代理已存在，加 query 透传） | `core/api/dps.ts` + 详情页 | 切换模板后展示该模板命名空间结果，无结果给空态 |
| P0-4 | 计算弹窗模板改为 **active 模板下拉**（默认唯一 active）；错误按后端 `detail` 原文展示，未激活时给「去激活」链接 | `pages/PortraitList.vue` | 无法手填错误 code；400 文案与后端一致 |
| P0-5 | 工作台保存成功后出现**下一步卡片**：「激活模板」/「创建标注模板」 | `DpsTemplateWorkbenchView.vue` | 保存后 1 次点击完成激活 |
| P0-6 | 修正硬编码 `/dps/...` 跳转为 `/portrait/dps/...` | 3 处（见 A5） | 全站无 `/dps/` 硬编码 |
| P0-7 | 标注字段 `target_dimension` 改为**所属模板维度下拉**，并对未填字段标注「不进入画像」 | `DpsAnnotationFieldView.vue` | 无法输入非法维度；未填字段有显式提示 |

### 8.2 P1：补齐断链（需代理 + 少量 DPS 只读接口）

| 编号 | 方案 | 落点 | 验收 |
|---|---|---|---|
| P1-1 | 新增**标注工作台**页 `/portrait/dps/annotations`：按标注模板渲染结构化表单（enum→下拉、number→数字、date→日期、list→多值），提交进 pending 队列；同页支持待办列表与单条/批量复核 | 新增 `pages/DpsAnnotationWorkbenchView.vue`；DPS 新增 `GET /portrait/annotations`（只读，分页/按模板/按状态）；代理新增 `/annotate`、`/annotations` | 从「配好标注模板」到「标注入库并生成标签」全程不离开 UI |
| P1-2 | 复核请求**服务端兜底回传 fields**：审核时若未带 `fields`，后端从标注记录取 `payload` 补全（或返回 400 明确告知），杜绝对「静默不联动」 | `routes_profiles.py::_apply_annotation_review` | 不带 fields 通过审核时，行为是「联动成功」或「明确报错」，不存在第三种 |
| P1-3 | 新增 `GET /portrait/templates/{code}/versions`（读 history）：返回版本号、时间、操作人、变更摘要 | DPS + 代理 + `DpsTemplateVersionView.vue` | 版本下拉可选，无需手填 |
| P1-4 | 预检影响面扩展：增加 `affected_profile_count`（按 `template_code` 命名空间 / lineage 去重主体）、`affected_subject_count` | `template_preflight.py::impact` + 前端预检页 | 预检页展示「将影响 N 个主体」 |
| P1-5 | 画像搜索改服务端：代理 `/portraits/search`，支持标签、维度分数区间、模板过滤、关键词 | 代理 + `PortraitSearch.vue` | 结果总数与后端一致，不再截断 100 条 |
| P1-6 | 血缘/措施页主体选择器：从画像列表选人，替代手填 ID | `DpsLineageView.vue`、`DpsMeasureView.vue` | 无法手填非法 ID |
| P1-7 | 空态与失败态分离：404（无数据）与 5xx（故障）分别给文案与动作 | 全 DPS 页面 | 血缘「无记录」不再显示成「查询失败」 |

### 8.3 P2：体验升级（画像 360 与向导）

| 编号 | 方案 | 验收 |
|---|---|---|
| P2-1 | **画像 360 视图**：身份卡（模板版本/更新时间/完整度）+ 维度雷达/条形 + 分组标签（值/来源/置信度）+ 证据抽屉（命中规则、原始值、来源标注模板、采集时间）+ 时间线（标签变化/分数跃迁） | 任一分数可下钻到规则与标注 |
| P2-2 | **端到端向导**：单页 4 步 stepper（配模板 → 配标注模板 → 采集 → 看画像），每步可跳转对应工作台并保留上下文 | 新用户 10 分钟内完成一次完整闭环 |
| P2-3 | 示例模板与术语中心：内置 3 个示例模板一键套用；`glossary` 内嵌提示 | 配置页无未解释术语 |
| P2-4 | 权限与角色：模板管理员 / 录入员 / 审核员 / 只读，配审批流 | 角色间职责边界清晰 |
| P2-5 | 性能：工作台分区懒渲染 + 虚拟滚动；试运行结果分页；默认走 async 计算 | 200 节点模板编辑 < 100ms；试算 < 2s |

---

## 9. 契约变更清单（实施前需冻结）

| 类型 | 变更 | 兼容性 |
|---|---|---|
| 新增（只读） | `GET /api/v2/portrait/annotations`（分页 + `template_code`/`review_status` 过滤） | 纯新增 |
| 新增（只读） | `GET /api/v2/portrait/templates/{code}/versions` | 纯新增 |
| 扩展（只读） | `impact` 增加 `affected_profile_count` / `affected_subject_count` | 追加字段，不破坏 |
| 语义修正 | 审核未带 `fields` 时从记录补全（或 400） | 需回归现有「静默成功」调用方 |
| 代理新增 | `/annotate`、`/annotations`、`/versions`、`/portraits/search`、`/portrait/{id}?template_code=` | 纯新增 |
| 不改 | 库表结构、现有模板 JSONB 键名、打分算法、白名单 | — |

---

## 10. 验收标准

- **流程完整性**：新用户可在 UI 内完成「建模板 → 激活 → 建标注模板 → 录入标注 → 审核 → 生成标签 → 计算 → 查看画像」全部 8 步，无一手工调接口。
- **误导消除**：全站不存在与实际配置无关的规则/数据展示；`/dps/` 硬编码跳转为 0。
- **可解释性**：画像详情任一维度分可展开看到构成规则与得分；`partial`、缺省 50 分、跳过的 `when` 规则均有显式文案。
- **错误自救**：所有 4xx 展示后端 `detail` 原文 + 至少一个修复动作；5xx 展示 `request_id`。
- **契约稳定**：现有模板 JSON 结构、API 路径与库表零破坏；存量模板打开保存无字段丢失。
- **工程质量**：`python -m pytest tests`（DPS 定向用例）、`python -m ruff check`、`npm run type-check`（vue-tsc）、`eslint` 全通过；新增代码覆盖率 ≥ 90%。

---

## 11. 风险与回滚

| 风险 | 影响 | 措施 |
|---|---|---|
| 审核语义修正影响存量调用方 | 下游依赖「静默不联动」 | 灰度：先返回 `tag_sync.status = "skipped_no_fields"` 并告警，一个版本后改为补全 |
| 新增标注页与 AI 候选页职责重叠 | 用户困惑 | 统一入口，AI 候选作为标注工作台的一个来源 Tab |
| 影响面统计口径偏差 | 误导决策 | 报告返回 `basis`（统计口径说明），前端同屏展示 |
| 360 视图依赖新聚合接口 | 工期拉长 | 先用现有 `GET /portrait/{id}` 的 `attributes` 渲染，聚合接口就绪后替换 |

回滚：所有新增接口只读；前端按路由灰度（新页面与旧页面并存一个版本周期）。

---

## 12. 已确认决策（2026-11-15）

1. **本轮范围：P0 + 画像 360**。P0 交付误导消除与首个卡点修复；画像 360 交付维度雷达 + 分组标签 + 证据抽屉（时间线后置）。
2. **审核未带 `fields`：服务端补全**。审核通过时以库中结构化标注为准补全 `annotation_template` / `fields` / `template_code`；自由文本标注保持既有「不联动」语义，不报错。
3. **「规则引擎」页：改为只读总览**，保留导航位置，展示 active 模板的维度/权重/规则并可跳转工作台。

---

## 13. 实施回填（v1.1.0）

### 13.1 交付清单

| 编号 | 改动 | 文件 |
|---|---|---|
| 1 | 审核通过时服务端补全联动入参（`fields_backfilled` 如实回传） | `DPS/src/rest_api/routes/routes_profiles.py`（`_backfill_review_fields`、`_apply_annotation_review`） |
| 2 | 新增结构化标注读取（标注模板 code / 归属画像模板 / fields） | `DPS/src/engines/annotation_template_engine.py`（`get_structured_annotation`） |
| 3 | 新增 5 条单测（正常读取、自由文本降级、补全、齐备不查库、无内容不误判） | `DPS/src/tests/test_annotation_review_backfill_v2_13.py` |
| 4 | 画像详情支持模板口径查询参数透传 | `openbase/modules/dps_proxy/__init__.py`（`dps_portrait_detail`） |
| 5 | `getPortrait` 支持 `templateCode`；`DpsPortrait` 补齐六维分/attributes/tags 行类型 | `openbase-ui/src/core/api/dps.ts` |
| 6 | 规则引擎页重写为只读总览（active 模板 + 维度权重 + 规则表 + 跳转工作台） | `openbase-ui/src/modules/portrait/pages/Rules.vue` |
| 7 | 画像详情 360 化（身份卡/完整度/雷达/维度条/分组标签/证据抽屉/模板切换） | `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue` |
| 8 | 计算弹窗模板改 active 下拉 + 后端 `detail` 原文 + 「去激活」引导；标签列对象渲染修复 | `openbase-ui/src/modules/portrait/pages/PortraitList.vue` |
| 9 | 保存后「下一步」卡片（激活/建标注模板/看规则/去计算） | `openbase-ui/src/modules/portrait/pages/DpsTemplateWorkbenchView.vue` |
| 10 | 标注字段 `target_dimension` 改维度下拉 + 「留空=不进画像」列头提示 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationFieldView.vue` |
| 11 | 旧路径 `/dps/...` 硬编码修正为 `/portrait/dps/...` | `DpsTemplateListView.vue`、`DpsAnnotationTemplateView.vue` |

### 13.2 与 v1.0.0 判断的差异（实测修正）

| v1.0.0 描述 | 实测结论 |
|---|---|
| 「画像详情把维度当 JSON 打印」 | 更严重：`GET /portrait/{id}` **不返回 `dimensions` 字段**（只有六维列 + tags 行），原详情页实际长期显示「暂无维度数据」 |
| 「标签为字符串平铺」 | 上游返回的是 `profile_tag` **行对象**，原模板 `{{ t }}` 渲染为 `[object Object]` |
| 「`PortraitResult.status` 可展示 partial」 | `models.PortraitResult` 无 `status` 字段，`core.py` 传入的 status 被 Pydantic 丢弃；故前端改由 `data_completeness < 0.8` 派生「部分完成」提示 |

### 13.3 验证结果

| 项 | 命令 | 结果 |
|---|---|---|
| DPS 新增单测 | `python -m pytest src/tests/test_annotation_review_backfill_v2_13.py` | 5 passed（新增文件覆盖率 100%） |
| DPS 标注模板回归 | `python -m pytest src/tests/test_annotation_template_v2_10.py` | 52 passed |
| OpenBase 代理回归 | `python -m pytest tests/test_dps_proxy.py` | 44 passed |
| 代理静态检查 | `ruff check openbase/modules/dps_proxy/__init__.py` | All checks passed |
| 前端类型检查 | `vue-tsc --noEmit` | 0 错误 |
| 前端 lint | `eslint`（8 个改动文件） | 0 错误 |

### 13.4 遗留项（下一批）

1. 标注录入/待办页（P1-1）与 `GET /portrait/annotations`、代理 `/annotate`：本轮未做，UI 仍无法人工录入标注。
2. 模板版本列表接口（P1-3）：版本对比仍需手填 from/to。
3. 影响面「受影响画像数」（P1-4）、服务端检索（P1-5）、血缘主体选择器（P1-6）。
4. 画像 360 的时间线/版本对照（P2-1 后半）。
5. `DpsPortraitTemplate` 类型标注「前端不解析内部结构」已与实现（规则总览解析 `dimension_config`）不一致，后续统一措辞。


---

## 14. 附：本文证据索引

| 主题 | 文件 |
|---|---|
| 模板校验/继承/历史 | `DPS/src/engines/template_engine.py`、`template_registry.py` |
| 打分白名单与 6 类规则 | `DPS/src/engines/portrait/scoring.py` |
| 计算主流程 / 缺省 50 / partial | `DPS/src/engines/portrait/core.py` |
| `when` 条件求值 | `DPS/src/engines/portrait/conditions.py` |
| 校验/试算引擎 | `DPS/src/engines/portrait/template_preview.py` |
| 预检与影响面 | `DPS/src/engines/template_preflight.py` |
| 标注模板/结构化标注/审核/联动 | `DPS/src/engines/annotation_template_engine.py` |
| 画像域全部路由 | `DPS/src/rest_api/routes/routes_profiles.py` |
| 代理白名单与转发 | `openbase/modules/dps_proxy/__init__.py` |
| 前端 API 封装 | `openbase-ui/src/core/api/dps.ts` |
| 前端路由与菜单 | `openbase-ui/src/modules/portrait/index.ts` |
| 工作台与模板组件 | `openbase-ui/src/modules/portrait/pages/DpsTemplateWorkbenchView.vue`、`templates/*` |
| 画像详情/列表/搜索 | `pages/PortraitDetail.vue`、`PortraitList.vue`、`PortraitSearch.vue` |
| 旧规则页（mock） | `pages/Rules.vue` |
