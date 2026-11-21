# OpenBase-需求追溯矩阵-v1.8.0

## 文档信息

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-RTM-v1.8.0 |
| 版本 | v1.0.0 |
| 状态 | [Approved] |
| 日期 | 2026-11-21 |
| 上游 | 《OpenBase-开发需求文档-v1.8.0》 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | BA-OpenBase-Dev | 首版：A1/A2/A7 与 A5/A8/A13 验证追溯 |

## 追溯矩阵

| 需求编号 | 需求 | 设计文档 | 实现位置 | 测试用例 | 验收 |
|---|---|---|---|---|---|
| RT-180-001 | 模板 keyword 服务端筛选 | A7 设计 §2/§3 | `DPS/src/engines/template_engine.py::list_templates` | `tests/test_template_filter_v2_16.py::test_keyword_*` | AC-180-01 |
| RT-180-002 | category/kind 精确过滤 | A7 设计 §2/§3 | 同上；`routes_profiles.py::api_list_portrait_templates` | `test_category_and_kind_filters`、`test_combined_conditions_are_and` | AC-180-01 |
| RT-180-003 | 前端改服务端筛选 | A7 设计 §3 | `DpsTemplateListView.vue`、`core/api/dps.ts` | `tests/dps-template-filter-v180.spec.ts` | AC-180-01 |
| RT-180-004 | 统计 4 分组 | A1 设计 §2/§3 | `annotation_template_engine.py::annotation_stats` | `test_annotation_stats_v2_16.py::test_*_group` | AC-180-02 |
| RT-180-005 | 统计过滤与路由顺序 | A1 设计 §2/§4 | `routes_profiles.py::api_annotation_stats` | `test_filters_match_list_scope`、`test_route_validation_and_order` | AC-180-02 |
| RT-180-006 | 工作台 KPI | A1 设计 §5 | `DpsAnnotationWorkbenchView.vue`、`dps.ts::getAnnotationStats` | `tests/dps-annotation-stats-v180.spec.ts` | AC-180-02 |
| RT-180-007 | reviewer=me / level 过滤 | A2 设计 §2.1 | `query_annotations`、`api_list_annotations` | `test_query_filters_by_reviewer_and_level`、路由 401 用例 | AC-180-03 |
| RT-180-008 | 前端只看我的/级数/归属列 | A2 设计 §5 | `DpsAnnotationWorkbenchView.vue` | `tests/dps-annotation-claim-v180.spec.ts` | AC-180-03 |
| RT-180-009 | 幂等领取 | A2 设计 §2.2/§3 | `claim_annotation`、`api_claim_annotation` | `test_claim_success_and_idempotent` | AC-180-03 |
| RT-180-010 | 冲突/不存在/非 pending | A2 设计 §2.2 | 同上 | `test_claim_rejects_other_owner_and_non_pending`、路由映射用例 | AC-180-03 |
| RT-180-011 | 领取权限动作 | A2 设计 §4 | `middleware/permission_middleware.py` | `test_v2_9_1_permission_mapping.py` | AC-180-03 |
| RT-180-012 | A5/A8/A13 验证 | 设计总文档 §14.9 | 既有前端实现 | `dps-template-health.spec.ts`、`r5-wiring-v195.spec.ts`、`api-dps-v1410.spec.ts` | AC-180-04 |
| RT-180-013 | 零回归与构建 | 各设计 §6 | — | `tests/test_dps_proxy.py`、`npm run build` | AC-180-05 |

## 覆盖结论

- 13 条需求全部有设计、实现与用例对应；无孤立需求、无未追溯实现。
- 范围外项（分页、统计缓存、领取释放、权限点新增）明确不在本版。
