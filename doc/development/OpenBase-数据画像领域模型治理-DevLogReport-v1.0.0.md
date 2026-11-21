# OpenBase-数据画像领域模型治理-开发记录报告-v1.0.0

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-DEV-DM-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | **[Final]** |
| 日期 | 2026-11-21 |
| 适用版本 | DPS v2.17.0；OpenBase v1.8.0；openbase-ui v1.9.1 |
| 依据 | 《OpenBase-数据画像领域模型与关联关系设计说明》v1.1.1 §6（T-DM-01~06） |
| 关联规格 | `doc/spec/dm-domain-model-2026-11-21/spec.md`、`tasks.md` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | BE/FE | 首版：T-DM-01~06 后端治理、OpenBase 代理与前端最小适配的开发记录 |

## 1. 交付范围

| 任务 | 交付 |
|---|---|
| T-DM-01 | 父画像模板停用后的采集门禁；停用响应返回受影响标注模板数与门禁状态 |
| T-DM-02 | 画像命名空间写入 `template_version`；详情/列表派生 `stale` 并支持过滤 |
| T-DM-03 | `tag_bindings` 与评分规则一致性保存期/预检校验（off/warn/reject） |
| T-DM-04 | 模板级 `source_precedence` 驱动多来源择优，默认行为不变 |
| T-DM-05 | 标签变更后按 `person+template` 时间桶去抖自动重算，失败重试与告警 |
| T-DM-06 | 画像模板维度 code 与 `tag_category.dimension_code` 跨层校验（off/warn/reject） |
| 跨仓 | OpenBase `dps-proxy` 列表透传 `template_code`/`stale`；前端 stale 列与筛选、停用影响面提示 |

## 2. 关键实现

### 2.1 DPS 后端

| 文件 | 变更 |
|---|---|
| `src/config.py` | 新增 `enforce_active_parent`、`tag_binding_consistency`、`dimension_vocabulary_check`、`tag_change_recalc_enabled`、`tag_change_recalc_debounce_seconds`、`tag_change_recalc_max_retries`；版本 2.17.0 |
| `src/engines/annotation_template_engine.py` | `validate_annotation_submission` 增加父模板 active 校验（受开关控制）；`sync_tags_to_profile` 结果回传 `person_id` |
| `src/engines/template_engine.py` | 新增 `count_active_annotation_templates`、`check_binding_rule_alignment`、`collect_binding_alignment`、`collect_dimension_vocabulary_gaps`、保存期策略裁决；create/update 返回 `warnings` |
| `src/engines/portrait/crud.py` | `pick_preferred_tags(rows, precedence)`；选中行附 `preferred_source`/`preferred_reason` |
| `src/engines/portrait/core.py` | `calculate_portrait` / `calculate_dimension_score` 透传 `source_precedence`（未配置时不传参，保持既有调用契约） |
| `src/engines/portrait/recalc_scheduler.py`（新增） | `enqueue_tag_change_recalc`：时间桶去抖 + 幂等键复用 + 失败任务重置 |
| `src/ddl/schema_portrait.py` | `portrait_calc_task` 新增 `retry_count`（PG/SQLite） |
| `src/rest_api/routes/routes_profiles.py` | 停用影响面、stale 派生/过滤、来源优先级校验与回显、预检追加两类差异、审核后自动重算入队、任务失败重试 |

### 2.2 OpenBase 代理与前端

| 文件 | 变更 |
|---|---|
| `openbase/modules/dps_proxy/__init__.py` | `GET /portraits` 透传 `template_code`、`stale` |
| `openbase/__init__.py` | 版本 1.8.0 |
| `openbase-ui/src/core/api/dps.ts` | `DpsPortrait` 增加 stale 字段；模板停用响应字段；列表参数扩展 |
| `openbase-ui/src/modules/portrait/pages/PortraitList.vue` | 「口径状态」列与「仅看过期」筛选 |
| `openbase-ui/src/modules/portrait/pages/DpsTemplateListView.vue` | 停用后提示受影响标注模板数与门禁状态 |
| `openbase-ui/package.json` | 版本 1.9.1 |

## 3. 接口与数据契约

- `POST /portrait/templates/{code}/deactivate` 响应 `data` 追加 `affected_annotation_templates`、`parent_gate_enforced`（仅停用）。
- `GET /portrait/{person_id}?template_code=`、`GET /portrait/by-external/{external_id}?template_code=` 追加 `stale`、`stale_reason`、`template_version`、`current_template_version`。
- `GET /portrait/list` 新增 `template_code`、`stale`；仅传 `stale` 返回 400。
- 模板 create/update/预检：warn 模式返回 `warnings`；预检追加 `binding_rule_alignment`、`dimension_vocabulary_gaps`。
- 审核响应 `data.recalc`：`{enqueued, reused, task_id, reason}`（无标签联动时为 `null`）。

## 4. 兼容与回滚

| 任务 | 回滚开关 |
|---|---|
| T-DM-01 | `DPS_ENFORCE_ACTIVE_PARENT=false` |
| T-DM-03 | `DPS_TAG_BINDING_CONSISTENCY=warn|off` |
| T-DM-05 | `DPS_TAG_CHANGE_RECALC_ENABLED=false` |
| T-DM-06 | `DPS_DIMENSION_VOCABULARY_CHECK=warn|off` |
| T-DM-02/04 | 派生字段/模板配置；移除配置即恢复默认 |

## 5. 追溯

| 设计条目 | 代码 | 用例 |
|---|---|---|
| T-DM-01 | `annotation_template_engine.validate_annotation_submission`、`template_engine.count_active_annotation_templates` | `test_dm_domain_model_v2_17.py::TestTdm01ParentGate` |
| T-DM-02 | `routes_profiles._mark_namespace_stale`、`_persist_template_namespace`、`api_list_portraits` | `TestTdm02Stale` |
| T-DM-03 | `template_engine.check_binding_rule_alignment` 等 | `TestTdm03BindingAlignment` |
| T-DM-04 | `portrait/crud.pick_preferred_tags`、`core.calculate_portrait` | `TestTdm04SourcePrecedence` |
| T-DM-05 | `portrait/recalc_scheduler.enqueue_tag_change_recalc`、`_run_calc_task` | `TestTdm05AutoRecalc` |
| T-DM-06 | `template_engine.collect_dimension_vocabulary_gaps` | `TestTdm06DimensionVocabulary` |
| 跨仓 | `dps_proxy`、`PortraitList.vue`、`DpsTemplateListView.vue` | `tests/test_dps_proxy_list_stale.py`、前端 2 个 spec |
