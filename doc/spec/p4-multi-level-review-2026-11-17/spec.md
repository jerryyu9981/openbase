# OpenBase P4 多级审核落地 Spec

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.1.0 |
| 状态 | [Final]（已批准并执行完成，验收结论见治理方案 v1.4.0 §15） |
| 适用环境 | Dev（OpenBase 8000 + DPS 8030 + 前端 5173，PostgreSQL 主库） |
| 作者 | AI 编码代理 |
| 评审人 | 需求方 / 技术负责人 |
| 创建日期 | 2026-11-17 |
| 上游依据 | 《OpenBase-画像模板-标注模板-评分项对应关系与治理方案》v1.3.0 §14.8（多级审核登记为后续需求）；P3 Spec v1.1.0 |

### 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-17 | 首版：`evidence_policy.review_levels` 真实生效（逐级审核 + 审核留痕 + 前端进度） | AI 编码代理 |
| v1.1.0 | 2026-11-17 | 执行完成：补 DDL 契约冻结列修复；E2E 采用 page.route 固定标注响应（trace 大响应超时）；测试/E2E/AC 结论见治理方案 v1.4.0 §15 | AI 编码代理 |

---

## 1. 现状与缺口

| 编号 | 事实 | 影响 |
|---|---|---|
| G-11 | 审核状态机单级：`REVIEW_TRANSITIONS = {pending: (approved, rejected, modified), ...}` | `review_levels=2/3` 的模板（实测 `cor-persona-*` 均为 2~3 级）声明无效 |
| G-12 | `check_evidence_policy` 固定 `review_levels_supported = review_levels <= 1` | 审核响应与页面始终提示"当前仅支持单级审核" |
| G-13 | `annotation` 表只有 `review_status/reviewer_id/review_comment`，无"已通过级数"与"应审级数" | 无法区分"待第 2 级"与"待第 1 级" |
| G-14 | 每次审核覆盖 `reviewer_id/review_comment`，无审核历史 | 多级审核无法留痕，责任链断裂 |
| G-15 | 标注队列不返回审核进度 | 前端只能显示"待审核/已通过" |

补充事实（已核对代码）：

1. 创建结构化标注固定落 `review_status=pending`（rich 形态）。
2. 标签联动与异常规则求值仅在 `new_status == "approved"` 时执行（`_apply_annotation_review`）。
3. 证据门禁在 `action == "approved"` 前执行，作用于标注记录的 `evidence_source`。
4. 批量复核逐条复用 `_apply_annotation_review`，单条失败不影响其余条目。
5. `annotation` 列演进已有幂等范式（P1 `_ensure_profile_tag_source_columns`、P3 `_ensure_annotation_evidence_source`）。

---

## 2. 目标与边界

**目标**：让 `evidence_policy.review_levels` 真正生效——标注需逐级审核通过后才终审通过并触发标签联动；全过程留痕、可查询、默认行为不变。

**范围内**：

1. **P4-1 数据模型**：`annotation.review_level`（已通过级数）、`annotation.review_levels_required`（创建时快照）；新增只追加的 `annotation_review_log` 审核留痕表。
2. **P4-2 引擎**：逐级审核状态机（非末级通过仍为 `pending`）、末级通过才 `approved` 并触发标签联动/异常规则；每次动作写留痕。
3. **P4-3 接口**：审核响应返回进度；标注队列返回进度；新增审核留痕只读接口。
4. **P4-4 前端**：标注工作台显示"第 N/M 级"进度、按钮文案、终审提示与审核记录查看。
5. **P4-5 策略提示收敛**：`review_levels_supported` 按上限（1~5）判定；移除"当前仅支持单级审核"警示，改为进度展示。

**范围外（明确不做）**：

| 项 | 理由 |
|---|---|
| 强制"同一审核人不得连续审两级" | DPS 无分级角色模型，强制会阻断单一管理员场景；P4 仅留痕，登记后续按需 |
| 按角色/部门路由审核任务 | 需 IAM 与组织模型配合，属独立需求 |
| 审核超时/催办/转交 | 需任务调度与通知通道，另行评审 |
| 历史 `pending` 行按多级补审 | 存量行 `required=1` 按单级收口，避免追溯改变既有语义 |
| `modified` 语义扩展 | 保持既有终态语义，不纳入多级链路 |

**默认行为不变**：`review_levels<=1` 或模板无策略时，创建/审核与 P3 完全一致（单次通过即 `approved`）。

---

## 3. 方案设计

### 3.1 数据模型（幂等演进）

| 对象 | 变更 | 单一来源 | 幂等策略 |
|---|---|---|---|
| `annotation.review_level` | `INTEGER DEFAULT 0`（0=未通过任何级） | `src/ddl/schema_profile_dependents.py` | PG `ADD COLUMN IF NOT EXISTS`；SQLite PRAGMA 探测后 ALTER |
| `annotation.review_levels_required` | `INTEGER DEFAULT 1`（创建时快照，1~5） | 同上 | 同上 |
| `annotation_review_log` | 新表：`id / annotation_id / review_level / action / reviewer / comment / created_at` | 同上 | `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` |

不变式：

- 留存记录的 `review_levels_required` 不随模板后续修改而变（创建时快照）。
- 存量行迁移后 `review_level=0 / required=1` → 继续单级收口，不追溯补审。
- 留痕表只追加，不更新、不删除；审核失败（409/400）不写留痕。

### 3.2 引擎改动（`engines/annotation_template_engine.py`）

`create_structured_annotation(..., review_levels=None)`：

- 以归属画像模板 `evidence_policy.review_levels` 取整并夹取 `[1, 5]`，缺省 1；写入 `review_levels_required`（列存在时）。
- 响应新增 `review_level=0`、`review_levels_required`。

`review_annotation(..., review_level=0, review_levels_required=1)`：

| 动作 | 条件 | 新 `review_status` | 新 `review_level` |
|---|---|---|---|
| `approved` | `review_level + 1 < required` | `pending`（待下一级） | `review_level + 1` |
| `approved` | `review_level + 1 >= required` | `approved`（终审） | `required` |
| `rejected` | 任意级 | `rejected` | 不变 |
| `modified` | 任意级 | `modified` | 不变 |

返回新增 `{review_level, review_levels_required, finalized}`；列缺失时按单级降级并 `persisted=false`。

`record_review_log(...)`（同引擎）：追加一行留痕，失败 `logger.warning` 不阻断主链路（留痕为旁路）。

`query_review_logs(annotation_id)`：按 `review_level, created_at` 升序返回。

`query_annotations(...)`：SELECT 增补 `review_level` / `review_levels_required`（列存在时）。

### 3.3 审核编排（`routes_profiles._apply_annotation_review`）

1. 读取记录（含 `review_level` / `review_levels_required`，缺失视为 0/1）。
2. `approved` 前执行证据门禁（沿用 P3；来源缺失且列已持久化 → 409，状态不变）。
3. 调用 `review_annotation` 得到新状态与进度。
4. **仅终审通过**（`finalized=true` 且 `status=approved`）才做标签联动与异常规则求值；非末级通过不写标签、不求值。
5. 成功后写留痕（level=本次通过级数）；响应新增 `review` 块：
   ```json
   "review": {"level": 1, "required": 3, "finalized": false}
   ```
6. `review_levels_supported` 语义改为"是否在支持上限内"（1~5 恒 true），保留字段以兼容旧前端。

### 3.4 接口

| 接口 | 变更/新增 | 关键返回 |
|---|---|---|
| `POST /api/v2/portrait/annotations/{id}/review` | 扩展 | 新增 `review{level,required,finalized}`；非末级通过时 `status` 仍为 `pending` |
| `POST /api/v2/portrait/annotations/batch-review` | 继承 | 每条结果含 `review` 块；单条失败不影响其余 |
| `GET /api/v2/portrait/annotations` | 扩展 | 行内新增 `review_level` / `review_levels_required` |
| `GET /api/v2/portrait/annotations/{id}/review-log` | 新增（只读） | `{annotation_id, items:[{review_level,action,reviewer,comment,created_at}], total}`；标注不存在 404 |

### 3.5 OpenBase 代理（1 条）

- `GET /api/v1/dps-proxy/annotations/{annotation_id}/review-log` → 上游 `/annotations/{id}/review-log`，沿用 `_build_identity_headers` + `_forward`，错误体保真。

### 3.6 前端

#### ① `DpsAnnotationWorkbenchView.vue`

- 队列新增「审核进度」列：`第 {review_level}/{review_levels_required} 级`；未开始显示 `0/M`；`approved` 显示 `已完成`。
- 操作按钮文案：`required>1 && level+1<required` → 「通过本级（N/M）」；末级 → 「终审通过」；单级保持「通过」。
- 审核成功后按响应提示：非末级「已通过第 N 级，待第 N+1 级审核」；末级「终审通过」。
- 新增「审核记录」入口（行内 link），弹窗按 `getAnnotationReviewLog` 展示历史。

#### ② `DpsTemplateListView.vue`

- 移除 `review_levels>1` 的「当前仅支持单级审核」警示；策略摘要保留「审核级数：N 级」。

#### ③ `core/api/dps.ts`

- 队列行类型补 `review_level?` / `review_levels_required?`。
- 新增类型 `DpsAnnotationReviewProgress`、`DpsAnnotationReviewLogItem`；新增方法 `getAnnotationReviewLog(annotationId)`。
- 审核响应类型补 `review?`。

---

## 4. 测试设计

### 4.1 DPS 单测（新建 `src/tests/test_p4_multi_level_review.py`，≥12 条）

1. `review_transition`/新状态机：1 级直接 `approved`；3 级第 1/2 次通过仍 `pending` 且 level 递增；第 3 次 `approved` 且 `finalized=true`。
2. `rejected` 在任意级 → `rejected` 且 `finalized=true`；`modified` 保持终态。
3. 非法动作/未知状态仍抛 `AnnotationValidationError`。
4. `review_levels` 夹取：0/负数→1，7→5，非数字→1。
5. `create_structured_annotation` 写入 `review_levels_required`（列存在）与响应字段；列缺失降级。
6. `review_annotation` 列缺失降级 `persisted=false` 且不抛错。
7. `record_review_log` 追加一行；写入异常不抛出（旁路）。
8. `query_review_logs` 排序与空结果。
9. `check_evidence_policy.review_levels_supported` 对 1~5 为 true、6 为 false。
10. `_apply_annotation_review`：非末级通过不调用标签联动；末级通过调用一次；证据缺失仍 409。

### 4.2 OpenBase 单测

`tests/test_dps_proxy_routes_v1410.py` 追加 1 条注册断言（`P4_ROUTES`），并确认 `GET /annotations/{id}/review-log` 不与 `GET /annotations` 冲突。

### 4.3 前端校验与 E2E

- `vue-tsc --noEmit`、改动文件 `eslint`。
- 新增 `openbase-ui/tests/e2e/portrait-multilevel-review.spec.ts`：
  1. 标注队列出现「审核进度」列，进度文案符合 `第 N/M 级` 或 `已完成`；
  2. 存在多级模板时按钮为「通过本级（N/M）」或「终审通过」（无数据时断言列头存在）；
  3. 审核记录弹窗可打开（无留痕显示空态）；
  4. 无 pageerror / 非受控 4xx。
- 证据截图：`doc/test/evidence/s6/ui-e2e/p4-review-progress.png`、`p4-review-log.png`。

### 4.4 回归

- DPS：P4 新测 + P3/P2/P1/P0 + 标注链。
- OpenBase：`pytest tests/test_dps_proxy_routes_v1410.py -q`。
- 前端：`portrait-policies.spec.ts`（P3 策略警示已改，需同步断言）+ `portrait-lineage.spec.ts`。

---

## 5. 验收标准

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| AC-P4-01 | 多级逐级生效 | `required=3` 的标注：第 1/2 次通过后 `status=pending` 且 `review.level` 递增；第 3 次 `approved` 且 `finalized=true` |
| AC-P4-02 | 终审才联动 | 非末级通过不写标签、不求值异常规则；末级通过执行一次标签联动并返回 `anomaly_alerts` |
| AC-P4-03 | 审核留痕 | 每次成功审核写一行 `annotation_review_log`；`GET .../review-log` 按级返回；失败动作不写 |
| AC-P4-04 | 证据门禁保持 | 缺来源时任一级通过均被拒（409），状态与级数不变 |
| AC-P4-05 | 进度可见 | 队列与审核响应返回 `review_level/review_levels_required`；前端显示「第 N/M 级」与终审按钮 |
| AC-P4-06 | 默认行为不变 | `required=1` 时创建/审核与 P3 一致；存量 `pending` 行按单级收口 |
| AC-P4-07 | 无回归 | DPS 定向回归 + OpenBase 路由测试全通过；`vue-tsc`/`eslint` 0 错误；E2E PASS 并留证 |

---

## 6. 风险与约束

| 风险 | 处置 |
|---|---|
| 存量 pending 行被误按多级卡住 | 存量行 `required` 默认 1，按单级收口；不追溯补审 |
| 模板级数后续被修改导致判定漂移 | 创建时快照 `review_levels_required`，审核只读快照 |
| 留痕写失败影响审核 | 留痕为旁路，失败仅 WARN；主链路以 `review_status/review_level` 为准 |
| 多级审核被理解为"必须不同人" | 页面与文档显式标注：P4 不强制不同审核人，仅留痕 |
| 并发重复审核 | 审核基于 `current_status` 校验流转；重复通过会因状态/级数不匹配被拒（409） |

---

## 7. 交付物

1. DPS：DDL/启动演进（2 列 + 1 表）、引擎逐级审核与留痕、队列/审核响应扩展、1 个只读接口、单测。
2. OpenBase：1 条代理路由 + 路由测试。
3. 前端：队列进度与终审按钮、审核记录弹窗、策略摘要收敛、API 类型 + E2E。
4. 文档：治理方案 v1.4.0（新增 §15）、DevLog v1.8.0、tasks 勾选。
5. 双仓提交并推送 `origin` / `backup` / `github`。
