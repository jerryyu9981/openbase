# OpenBase P2 模板—标注—评分可解释性 Tasks

- 对应 Spec：`doc/spec/p2-template-explainability-2026-11-17/spec.md` v1.0.0
- 状态：[Draft]（待批准后执行）

## 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-17 | 首版任务拆解 | AI 编码代理 |

## T1 DPS 引擎（纯函数 + 装配）

- [x] T1.1 新建 `src/engines/p2_explainability.py`：`build_lineage_chain` / `field_tag_contract` / `resolve_scoring_hits` / `build_field_mappings`。
- [x] T1.2 同文件：`build_annotation_views` / `build_gap_items` / `build_template_lineage`。
- [x] T1.3 同文件：`build_annotation_field_mapping` / `build_portrait_dimension_details`（`engine` 可注入）。
- [x] T1.4 维度规则适配：`resolve_dimensions()` 的 `rules` → `calculate_dimension_score` 所需 `tags` 转换。

## T2 DPS 路由

- [x] T2.1 `src/rest_api/routes/routes_profiles.py`：新增 `GET /portrait/templates/{code}/lineage`（scoring-items 之后、模板详情之前）。
- [x] T2.2 同文件：新增 `GET /portrait/annotation-templates/{code}/field-mapping`（标注模板详情之前）。
- [x] T2.3 同文件：新增 `GET /portrait/{person_id}/dimension-details`（`/portrait/{person_id}` 之前）。
- [x] T2.4 错误映射：模板/标注模板不存在 404；模板无该维度 400。

## T3 DPS 测试

- [x] T3.1 新建 `src/tests/test_p2_explainability_v3.py`（15 条用例）。
- [x] T3.2 运行 `pytest src/tests/test_p2_explainability_v3.py` → 15 passed。
- [x] T3.3 定向回归 P0/P1/registry（55 passed）。
- [x] T3.4 `ruff check` 新增文件 → 0 错误（91 项自动修复）；新增模块覆盖率 94%。

## T4 OpenBase 代理

- [ ] T4.1 `openbase/modules/dps_proxy/__init__.py`：新增 3 条逐端点转发路由。
- [ ] T4.2 `tests/test_dps_proxy_routes_v1410.py`：追加 3 条注册断言 + 动态段遮蔽断言。
- [ ] T4.3 `pytest tests/test_dps_proxy_routes_v1410.py -q` → 全通过；`ruff check` 新增文件 0 错误。

## T5 前端 API 与页面

- [ ] T5.1 `openbase-ui/src/core/api/dps.ts`：新增 7 个类型 + 3 个方法。
- [ ] T5.2 `DpsTemplateListView.vue`：详情抽屉四联视图（族谱/标注模板/标签产出/评分项）+ 缺口警示标签。
- [ ] T5.3 `DpsAnnotationWorkbenchView.vue`：字段旁映射提示（写入标签/计分摘要/影响评分项）。
- [ ] T5.4 `PortraitDetail.vue`：维度展开规则级明细（标签值/得分/缺值→50）。
- [ ] T5.5 `vue-tsc --noEmit` 0 错误；新增/修改文件 `eslint` 0 错误。

## T6 E2E 走查与证据

- [ ] T6.1 新增 `openbase-ui/tests/e2e/portrait-lineage.spec.ts`（四页签 + 维度展开 + 缺值标记）。
- [ ] T6.2 实跑 `node node_modules\@playwright\test\cli.js test tests/e2e/portrait-lineage.spec.ts --reporter=list` → PASS。
- [ ] T6.3 截图留存 `doc/test/evidence/s6/ui-e2e/p2-template-lineage.png`、`p2-dimension-details.png`。
- [ ] T6.4 复跑 `portrait-scoring-sources.spec.ts` 确认无回归。

## T7 文档与交付

- [ ] T7.1 治理方案升版 v1.2.0：§7 阶段三标 ✅、新增 §13 P2 实施与验证、修订历史。
- [ ] T7.2 DevLogReport 升版 v1.6.0（实施记录 + 验证证据 + 版本历史）。
- [ ] T7.3 DPS 仓提交（仅 P2 相关文件）并推送 origin / backup / github。
- [ ] T7.4 OpenBase 仓提交（排除 `llm.ts` / `Playground.vue` / `service-orchestrator.ps1`）并推送三远程。
- [ ] T7.5 输出验收结论（AC-01~AC-07 逐项对照）。

## 门禁

- 需人工批准本 Spec 后方可进入 T1。
- T3 / T4 / T5 全绿且 T6 全 PASS 方可判定 P2 完成。
