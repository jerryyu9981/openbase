# OpenBase P4 多级审核 Tasks

- 对应 Spec：`doc/spec/p4-multi-level-review-2026-11-17/spec.md` v1.1.0
- 状态：[Completed]（T1~T8 全部完成并验证）

## 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-17 | 首版任务拆解（数据模型 / 引擎 / 接口 / 前端 / 验证） | AI 编码代理 |
| v1.1.0 | 2026-11-17 | 全部任务执行完成并勾选；补 T1.4（修复 DDL 契约冻结列）与 E2E 执行说明 | AI 编码代理 |

## T1 数据模型（幂等演进）

- [x] T1.1 `src/ddl/schema_profile_dependents.py`：新增 `annotation.review_level` / `review_levels_required` 列常量与 `annotation_review_log` 建表/索引（PG/SQLite 双后端，单一来源）。
- [x] T1.2 `src/database.py`：新增 `_ensure_annotation_review_progress()`，接入启动装配链；SQLite PRAGMA 探测。
- [x] T1.3 双后端幂等断言（DDL 常量/重复执行无副作用）。
- [x] T1.4 修复 `test_v2_11_ddl_profile_dependents.py` 的 `annotation` 冻结列（补齐 P3 `evidence_source` 与 P4 两列）。

## T2 DPS 引擎

- [x] T2.1 `review_annotation`：逐级状态机（非末级通过保持 `pending`）、返回 `review_level/review_levels_required/finalized`；列缺失降级。
- [x] T2.2 `create_structured_annotation`：模板 `review_levels` 夹取 1~5 快照写入 `review_levels_required`；响应补进度字段。
- [x] T2.3 `record_review_log`（旁路、失败不阻断）与 `query_review_logs`（按级升序）。
- [x] T2.4 `query_annotations` / `get_structured_annotation` 增补进度列。
- [x] T2.5 `check_evidence_policy.review_levels_supported` 改为 1~5 支持。

## T3 DPS 接口

- [x] T3.1 `_apply_annotation_review`：终审才标签联动/异常规则；响应新增 `review` 块；成功后写留痕。
- [x] T3.2 `GET /portrait/annotations/{annotation_id}/review-log`（不存在 404）。
- [x] T3.3 批量复核结果透传 `review` 块。

## T4 DPS 测试

- [x] T4.1 新建 `src/tests/test_p4_multi_level_review.py`（35 条，覆盖 Spec §4.1）。
- [x] T4.2 新测 + P3/P2/P1/P0 + 标注链 + DDL 契约定向回归全通过（173 passed）。
- [x] T4.3 新增路径单测覆盖；`ruff check`（新测/策略文件）与 `--select F,E9`（存量改动）0 错误。

## T5 OpenBase 代理

- [x] T5.1 `openbase/modules/dps_proxy/__init__.py`：新增 `GET /annotations/{annotation_id}/review-log`。
- [x] T5.2 `tests/test_dps_proxy_routes_v1410.py`：追加注册断言（含不与 `GET /annotations`/`POST .../review` 冲突）。
- [x] T5.3 路由测试全通过（52 passed）；`ruff check` 0 错误。

## T6 前端

- [x] T6.1 `core/api/dps.ts`：队列行补进度字段；新增进度/留痕类型与 `getAnnotationReviewLog`。
- [x] T6.2 `DpsAnnotationWorkbenchView.vue`：队列「审核进度」列、按钮文案（本级/终审）、通过后提示、审核记录弹窗。
- [x] T6.3 `DpsTemplateListView.vue`：移除多级审核未支持警示，保留级数摘要。
- [x] T6.4 `vue-tsc` / `eslint` 0 错误。

## T7 E2E 与验收

- [x] T7.1 新增 `tests/e2e/portrait-multilevel-review.spec.ts`（进度+按钮文案 / 留痕弹窗）。
- [x] T7.2 重启服务后实跑 E2E，PASS 并截图 `p4-review-progress.png`、`p4-review-log.png`。
- [x] T7.3 回归 `portrait-policies.spec.ts`（3 passed）、`portrait-lineage.spec.ts`（2 passed，`--trace=off`）。
- [x] T7.4 AC-P4-01~AC-P4-07 逐项对照（结论见治理方案 §15.7）。

## T8 文档与交付

- [x] T8.1 治理方案升版 v1.4.0：新增 §15 P4 实施与验证、修订历史。
- [x] T8.2 DevLogReport 升版 v1.8.0。
- [x] T8.3 DPS 仓提交并推送 origin / backup / github。
- [x] T8.4 OpenBase 仓提交并推送 origin / backup / github（排除无关改动）。

## 门禁

- 需人工批准本 Spec 后方可进入 T1；T4/T5/T6 全绿且 T7 全 PASS 方可判定 P4 完成。
- 角色分级审核、审核超时/转交不在本 P4 扩围，另行评审。
