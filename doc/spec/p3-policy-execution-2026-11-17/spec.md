# OpenBase P3 画像治理收口 Spec（策略执行与孤儿模板治理）

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.1.0 |
| 状态 | [Final]（已批准并执行完成，验收结论见治理方案 v1.3.0 §14） |
| 适用环境 | Dev（OpenBase 8000 + DPS 8030 + 前端 5173，PostgreSQL 主库） |
| 作者 | AI 编码代理 |
| 评审人 | 需求方 / 技术负责人 |
| 创建日期 | 2026-11-17 |
| 上游依据 | 《OpenBase-画像模板-标注模板-评分项对应关系与治理方案》v1.2.0 §6 问题清单与 §12.7 遗留 |

### 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-17 | 首版：P0/P1/P2 缺口盘点结论 + P3 策略执行层方案 | AI 编码代理 |
| v1.1.0 | 2026-11-17 | 执行完成：补 §4.1 第 6 项落地的 4 条审核路径单测（写路径落库 / 409 门禁 / 通过响应 / 驳回跳过）；测试结论、E2E 证据与 AC 对照见治理方案 v1.3.0 §14 | AI 编码代理 |

---

## 1. 缺口盘点结论（P3 输入）

治理方案只规划到 P2；对 §6 问题清单与 §12.7 遗留逐项复核后，现状如下：

| 编号 | 问题 | 现状 | P3 处置 |
|---|---|---|---|
| G-01 | 模板权重/规则不参与计算 | ✅ P0 已闭环（模板规则为唯一事实源） | — |
| G-02 | 标签 code 前缀与规则 key 不匹配 | ✅ P0 已闭环（去前缀匹配 + 兼容） | — |
| G-03 | 两套命名空间 0 交集 | ✅ P0/P1 已闭环（迁移 8 模板 tag_key/score_map） | — |
| G-04 | 未知维度被静默跳过 | ✅ P0 已闭环（显式错误） | — |
| G-05 | `tag_bindings` 不校验引用 | ⚠️ 部分：P0 升级了结构/归属校验，但"未绑定"仅页面提示 | P3-3 治理报告 |
| G-06 | 2 个孤儿标注模板、存量格式 | ⚠️ P1 已归一格式；孤儿模板仍未被任何画像模板绑定 | P3-3 治理报告 |
| G-07 | 同名标签后写覆盖 | ✅ P1 已闭环（来源列 + 读侧择优） | — |
| G-08 | `social`/`crime` 无标注来源 | ⚠️ P1/P2 已页面提示；**业务未确认字段** | P3 仅文档化，待业务裁定 |
| G-09 | 枚举评分方向写死 | ✅ P0 已闭环（`_score_for_tag` 消费 `score_map`/`score_direction`） | — |
| G-10 | `evidence_policy` / `anomaly_rules` 仅校验不执行 | ❌ 未闭环：全仓仅持久化与结构校验，无消费方 | **P3-1 / P3-2 核心** |

补充事实（已核对代码）：

1. `annotation` 表列：`id/profile_id/author_id/content/annotation_type/template_id/payload/review_status/reviewer_id/review_comment/created_at/updated_at`，**无证据来源列**。
2. 审核状态机为单级：`REVIEW_TRANSITIONS` 仅 `pending → approved/rejected/modified`，`evidence_policy.review_levels` 无落点。
3. 异常规则条件存在两种形态：结构化条件组（`{all|any: [{field,op,value}]}`，已有 `engines/portrait/conditions.py` 求值器）与字符串表达式（如 `psychology:crisis_level == '紧急'`，**不能安全求值**）。
4. 标注写路径：`POST /portrait/annotations`（`action=create` + `annotation_template` + `fields`）→ `AnnotationTemplateEngine.create_structured_annotation` → `annotation.payload` 存校验后的字段。
5. 既有幂等列演进范式：`database._ensure_profile_tag_source_columns()`（P1 落地），P3 沿用。

---

## 2. P3 目标与边界

**目标**：让模板上已声明但从未执行的两类策略真正生效，并给出孤儿标注模板的治理入口；全过程可解释、可回滚、不改变既有默认行为。

**范围内**：

1. **P3-1 证据策略（`evidence_policy.require_source`）**：标注落库可携带证据来源；审核通过前按模板策略强制校验。
2. **P3-2 异常规则（`anomaly_rules`）**：结构化条件在标注审核通过后求值，结果随审核响应返回；新增画像级只读查询接口并在画像详情呈现。
3. **P3-3 孤儿标注模板治理报告**：只读接口列出未被任何画像模板绑定的 active 标注模板及建议归属，供业务裁定。

**范围外（明确不做）**：

| 项 | 理由 |
|---|---|
| 多级审核（`review_levels>1`） | 需重做审核状态机与审核 UI；P3 仅做显式告警，登记为后续需求 |
| 字符串条件表达式求值 | 任意表达式执行存在注入风险；P3 标记 `not_evaluable` 并提示改为结构化条件 |
| `social`/`crime` 新增标注字段 | 字段名/选项属业务语义，须业务裁定后另行配置 |
| 同名标签优先级策略变更 | P1 已用"来源隔离 + 最新审核择优"闭环；改策略需业务确认 |
| 批量画像维度明细性能优化 | 单画像场景无性能问题；避免过度设计 |

**默认行为不变**：模板 `evidence_policy` / `anomaly_rules` 为空时，标注创建/审核行为与现状完全一致。

---

## 3. 方案设计

### 3.1 数据模型（幂等演进）

| 对象 | 变更 | 单一来源 | 幂等策略 |
|---|---|---|---|
| `annotation.evidence_source` | 新增 `VARCHAR(200) DEFAULT NULL` | `src/ddl/schema_profile_dependents.py`（PG/SQLite 各一条 ALTER 常量） | PG `ADD COLUMN IF NOT EXISTS`；SQLite PRAGMA 探测后 ALTER |
| 启动装配 | `database._ensure_annotation_evidence_source()` | `src/database.py` | 在既有 `_ensure_*` 调用链中执行，重复启动无副作用 |

不新增表、不改既有列、不做数据回填（存量行 `evidence_source=NULL`，策略未要求时不受影响）。

### 3.2 DPS 新引擎 `src/engines/p3_policies.py`

纯函数（可单测）+ 异步装配：

| 函数 | 职责 |
|---|---|
| `build_rule_context(field_schema, fields)` | 生成异常规则上下文：`{field_key: value}` ∪ `{dimension:tag_key: value}`（复用 `p2_explainability.field_tag_contract`） |
| `evaluate_anomaly_rules(anomaly_rules, context)` | 逐条求值：结构化 `condition` 用 `conditions.evaluate_condition_group`；字符串 `condition` 返回 `evaluable=false`；异常结构捕获为 `evaluable=false` + `reason`，**不抛出** |
| `check_evidence_policy(policy, evidence_source)` | 返回 `{required, provided, satisfied, review_levels, review_levels_supported}`；`require_source=true` 且来源为空 → `satisfied=false` |
| `collect_orphan_annotation_templates(templates, annotations)` | 返回 `[{code,name,status,owned_by,suggested_action,reason}]`；建议动作仅"绑定到归属模板 / 停用"，**不自动改数据** |
| `async def build_portrait_anomaly_alerts(db, person_id, template_code=None, limit=20)` | 取画像最近 N 条已审核结构化标注 → 逐条求值 → 聚合返回 |

求值上下文归一规则：字段有 `target_dimension` 时同时写入 `"<dim>:<tag_key>"` 键，使 `psychology:crisis_level` 形式条件可直接命中。

### 3.3 写路径与审核路径改动

#### A. 标注创建携带证据来源

- `AnnotationTemplateEngine.create_structured_annotation(..., evidence_source=None)`：
  - 列存在时写入 `annotation.evidence_source`；列缺失（迁移未执行）时**降级为不落库**并在返回体 `evidence_source_persisted=false` 标注，不阻断创建。
- `POST /portrait/annotations`：接受可选 `evidence_source`（字符串，≤200），透传引擎；响应 `annotation` 内回显。

#### B. 审核通过前执行证据策略

`_apply_annotation_review` 在 `new_status == "approved"` 分支增加**前置门禁**（在标签联动之前）：

1. 读取该标注归属标注模板 → 画像模板 → `evidence_policy`（无模板/无策略视为空策略）；
2. `require_source=true` 且 `annotation.evidence_source` 为空 → 抛出 409，`detail` 含明确文案与缺失项；
3. 响应新增：
   ```json
   "evidence": {"required": true, "provided": false, "satisfied": true,
                "review_levels": 3, "review_levels_supported": false}
   ```
4. `review_levels > 1` 时 `review_levels_supported=false` 且 `logger.warning`，**不阻断**（当前单级状态机）。

#### C. 审核通过后求值异常规则

- 同一分支在标签联动之后求值 `anomaly_rules`，响应新增：
  ```json
  "anomaly_alerts": [
    {"rule": "crisis_alert", "action": "1小时内触发预警并转介",
     "matched": true, "evaluable": true, "reason": null},
    {"rule": "legacy_rule", "action": "...", "matched": false,
     "evaluable": false, "reason": "条件为字符串表达式，需改为结构化条件"}
  ]
  ```
- 求值失败不影响审核成功（fail-open 但显式标注 `evaluable=false`）。

### 3.4 新增只读接口

| 接口 | 用途 | 关键返回 |
|---|---|---|
| `GET /api/v2/portrait/{person_id}/anomaly-alerts?template_code=&limit=` | 画像异常预警聚合 | `{person_id, template_code, scanned, alerts:[{rule, action, matched, evaluable, reason, annotation_id, created_at}]}`；画像不存在 404 |
| `GET /api/v2/portrait/governance/orphan-annotation-templates` | 孤儿标注模板治理报告 | `{items:[{code,name,status,owned_by,suggested_action,reason}], total}` |

路由注册顺序：`/portrait/governance/orphan-annotation-templates` 为静态段，必须注册在 `/portrait/{person_id}` 之前；`/portrait/{person_id}/anomaly-alerts` 与既有 `/portrait/{person_id}/tasks` 同级。

### 3.5 OpenBase 代理（2 条）

- `GET /api/v1/dps-proxy/portraits/{person_id}/anomaly-alerts`
- `GET /api/v1/dps-proxy/governance/orphan-annotation-templates`

沿用 `_build_identity_headers` + `_forward`，错误体保真。

### 3.6 前端

#### ① `DpsAnnotationWorkbenchView.vue`：证据来源输入

- 结构化标注表单新增可选输入「证据来源（文书编号）」，`data-test="annotation-evidence-source"`。
- 当归属画像模板 `evidence_policy.require_source=true` 时显示必填标记与提示（复用 `dpsApi.getTemplate(portrait_template)`）。
- 提交体携带 `evidence_source`；后端 409 时错误文案直接展示。

#### ② `PortraitDetail.vue`：异常预警区块

- 「维度评分」卡片下方新增预警区（`data-test="portrait-anomaly-alerts"`）。
- 有预警时逐条显示规则名 + 动作 + 来源标注时间；`evaluable=false` 显示「规则未执行（需结构化条件）」warning 标签。
- 无预警时显示「暂无异常预警」。

#### ③ `DpsTemplateListView.vue`：策略能力提示

- 「评分项」页签顶部补充策略摘要：`evidence_policy.require_source` / `review_levels`；`review_levels>1` 显示 `当前仅支持单级审核` warning 标签（`data-test="template-review-levels-warning"`）。

### 3.7 前端 API（`core/api/dps.ts`）

新增类型：`DpsAnomalyAlert`、`DpsPortraitAnomalyAlerts`、`DpsOrphanAnnotationTemplate`、`DpsEvidencePolicy`、`DpsEvidenceCheck`。
新增方法：`getPortraitAnomalyAlerts(personId, params?)`、`getOrphanAnnotationTemplates()`；`createAnnotation` 载荷类型补 `evidence_source?: string`。

---

## 4. 测试设计

### 4.1 DPS 单测 `src/tests/test_p3_policies_v3.py`

1. `build_rule_context`：裸 key + `dim:tag` 双键；无 `target_dimension` 只写裸 key。
2. `evaluate_anomaly_rules`：结构化条件命中/未命中；字符串条件 `evaluable=false`；非法结构 `evaluable=false` 不抛出；空规则返回空数组。
3. `check_evidence_policy`：空策略不受限；`require_source=true` 且来源为空 → 不满足；`review_levels=3` → `review_levels_supported=false`。
4. `collect_orphan_annotation_templates`：识别孤儿、给出建议动作、排除已绑定与 inactive。
5. `build_portrait_anomaly_alerts`：桩 DB + 桩标注/模板数据，断言聚合条数与 `annotation_id`。
6. 审核门禁：`_apply_annotation_review` 证据缺失 → 409；来源齐全 → 通过并返回 `evidence`。

### 4.2 OpenBase 单测

`tests/test_dps_proxy_routes_v1410.py` 追加 2 条路由注册断言 + `governance` 静态段不被 `/portraits/{person_id}` 遮蔽。

### 4.3 前端校验与 E2E

- `vue-tsc --noEmit`、改动文件 `eslint`。
- 新增 `openbase-ui/tests/e2e/portrait-policies.spec.ts`（headless 1440×900）：
  1. 标注工作台出现「证据来源」输入（`annotation-evidence-source`）；
  2. 画像详情出现异常预警区块（`portrait-anomaly-alerts`），有预警时显示规则行；
  3. 模板详情评分项页签出现策略摘要（`template-review-levels-warning` 在 `review_levels>1` 模板上可见）；
  4. 无 pageerror / 非受控 4xx。
- 证据截图：`doc/test/evidence/s6/ui-e2e/p3-evidence-source.png`、`p3-anomaly-alerts.png`。

### 4.4 回归

- DPS：P3 新测 + P0/P1/P2 四个测试文件。
- OpenBase：`pytest tests/test_dps_proxy_routes_v1410.py -q`。
- 服务重启：`scripts/service-orchestrator.ps1 -Action stop -Only dps,openbase` → `-Action start -Only dps,openbase`（Vite 前端 HMR 自动生效）。

---

## 5. 验收标准

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| AC-P3-01 | 证据来源可写入 | 创建结构化标注携带来源 → `annotation.evidence_source` 落库并在响应回显 |
| AC-P3-02 | 证据门禁生效 | `require_source=true` 的模板下，无来源标注审核通过被拒（409，文案明确）；补来源后通过 |
| AC-P3-03 | 异常规则可执行 | 结构化条件命中时审核响应 `anomaly_alerts[].matched=true`；字符串条件返回 `evaluable=false` 且审核不失败 |
| AC-P3-04 | 画像预警可见 | 画像详情显示预警区块与规则/动作，未执行规则有警示标签 |
| AC-P3-05 | 孤儿治理可见 | 治理报告接口返回 2 个孤儿模板及建议动作 |
| AC-P3-06 | 默认行为不变 | 空策略模板的创建/审核响应与 P2 一致（除新增可选字段） |
| AC-P3-07 | 无回归 | DPS 定向回归 + OpenBase 路由测试全通过；`vue-tsc`/`eslint` 0 错误；E2E PASS 并留证 |

---

## 6. 风险与约束

| 风险 | 处置 |
|---|---|
| 新增列在 SQLite/PG 不一致 | DDL 单一来源 + 双后端幂等演进，补 PRAGMA 探测用例 |
| 存量库未迁移导致审核失败 | 写入/读取均按列存在性降级；证据策略仅在列存在时强制（否则 WARN + 放行并标注 `evidence_source_persisted=false`） |
| 字符串条件误执行 | 明确不执行任意表达式，仅结构化条件；返回 `evaluable=false` |
| 多级审核被误解为已支持 | 页面与响应均显式标注 `review_levels_supported=false` |
| 跨仓接口变更 | OpenBase 仅新增代理路由，不改既有路由与响应 |

---

## 7. 交付物

1. DPS：DDL/启动演进、`p3_policies.py`、标注创建与审核改造、2 个只读接口、单测。
2. OpenBase：2 条代理路由 + 路由测试。
3. 前端：工作台证据输入、画像异常预警、模板策略提示、API 类型 + E2E。
4. 文档：治理方案 v1.3.0（新增 §14 P3 实施与验证）、DevLog v1.7.0。
5. 双仓提交并推送 `origin` / `backup` / `github`。
