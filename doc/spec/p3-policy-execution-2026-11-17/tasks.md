# OpenBase P3 画像治理收口 Tasks

- 对应 Spec：`doc/spec/p3-policy-execution-2026-11-17/spec.md` v1.1.0
- 状态：[Completed]（T1~T8 全部完成并验证）

## 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-17 | 首版任务拆解（证据策略 / 异常规则 / 孤儿治理） | AI 编码代理 |
| v1.1.0 | 2026-11-17 | 全部任务执行完成并勾选；补 T4.4（审核路径 4 条单测）与验证结论 | AI 编码代理 |

## T1 数据模型（幂等演进）

- [x] T1.1 `src/ddl/schema_profile_dependents.py`：新增 `annotation.evidence_source` PG/SQLite ALTER 常量（单一来源）。
- [x] T1.2 `src/database.py`：新增 `_ensure_annotation_evidence_source()` 并接入启动装配链；SQLite PRAGMA 探测。
- [x] T1.3 补双后端幂等用例（重复执行无副作用）。

## T2 DPS 策略引擎

- [x] T2.1 新建 `src/engines/p3_policies.py`：`build_rule_context` / `evaluate_anomaly_rules` / `check_evidence_policy` / `collect_orphan_annotation_templates`。
- [x] T2.2 同文件：`build_portrait_anomaly_alerts`（聚合最近已审核标注）。
- [x] T2.3 条件求值复用 `engines/portrait/conditions.py`；字符串条件标记 `evaluable=false`。

## T3 DPS 写路径与接口

- [x] T3.1 `create_structured_annotation(..., evidence_source)`：列存在则落库，缺失降级并标注。
- [x] T3.2 `POST /portrait/annotations` 接受 `evidence_source` 并回显。
- [x] T3.3 `_apply_annotation_review`：approved 前证据门禁（409）、响应 `evidence`；approved 后异常规则求值（`anomaly_alerts`）。
- [x] T3.4 新增 `GET /portrait/{person_id}/anomaly-alerts`（画像不存在 404）。
- [x] T3.5 新增 `GET /portrait/governance/orphan-annotation-templates`（静态段先于动态段）。

## T4 DPS 测试

- [x] T4.1 新建 `src/tests/test_p3_policies_v3.py`（≥10 条，覆盖 Spec §4.1）。
- [x] T4.2 新测 + P0/P1/P2 定向回归全通过。
- [x] T4.3 新增模块覆盖率 ≥90%；`ruff check` 新增文件 0 错误。
- [x] T4.4 补审核路径用例 4 条（写路径落库、409 门禁、审核通过响应装配、驳回跳过策略）。

## T5 OpenBase 代理

- [x] T5.1 `openbase/modules/dps_proxy/__init__.py`：新增 2 条代理路由。
- [x] T5.2 `tests/test_dps_proxy_routes_v1410.py`：追加 2 条注册断言 + 静态段遮蔽断言。
- [x] T5.3 路由测试全通过；`ruff check` 0 错误。

## T6 前端

- [x] T6.1 `core/api/dps.ts`：新增 5 个类型 + 2 个方法；创建标注载荷补 `evidence_source`。
- [x] T6.2 `DpsAnnotationWorkbenchView.vue`：证据来源输入 + 必填提示 + 409 文案展示。
- [x] T6.3 `PortraitDetail.vue`：异常预警区块（规则/动作/未执行警示）。
- [x] T6.4 `DpsTemplateListView.vue`：评分项页签策略摘要 + 多级审核未支持警示。
- [x] T6.5 `vue-tsc` / `eslint` 0 错误。

## T7 E2E 与验收

- [x] T7.1 新增 `tests/e2e/portrait-policies.spec.ts`（3 个断点）。
- [x] T7.2 重启 DPS/OpenBase 后实跑 E2E，PASS 并截图 `p3-evidence-source.png`、`p3-anomaly-alerts.png`。
- [x] T7.3 回归 `portrait-lineage.spec.ts` / `portrait-scoring-sources.spec.ts`。
- [x] T7.4 AC-P3-01~AC-P3-07 逐项对照（结论见治理方案 §14.7）。

## T8 文档与交付

- [x] T8.1 治理方案升版 v1.3.0：新增 §14 P3 实施与验证、修订历史。
- [x] T8.2 DevLogReport 升版 v1.7.0。
- [x] T8.3 DPS 仓提交并推送 origin / backup / github。
- [x] T8.4 OpenBase 仓提交并推送 origin / backup / github（排除无关改动）。

## 门禁

- 需人工批准本 Spec 后方可进入 T1；T4/T5/T6 全绿且 T7 全 PASS 方可判定 P3 完成。
- 若业务确认需要多级审核或 social/crime 字段，另立 P4 需求，不在本 P3 扩围。
