# OpenBase-A1标注队列统计-设计文档-v1.0.0

| 项 | 内容 |
|---|---|
| 文档类型 | 后端＋前端详细设计 |
| 版本 | v1.0.0 |
| 状态 | [Implemented]（2026-11-21） |
| 适用范围 | DPS `GET /portrait/annotations/stats`；OpenBase `dps-proxy`；标注工作台队列 |
| 上游依据 | 《OpenBase 开发需求文档 v1.8.0》FR-180-02；《DPS 统一前端页面功能设计》v2.7.0 §9 A1 |
| 作者 | 后端工程师（BE）＋前端工程师（FD） |
| 日期 | 2026-11-21 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 首版：四维聚合统计端点、代理与工作台状态 KPI | BE/FD |

## 1. 设计目标

- 以服务端口径提供队列聚合，避免前端按当前页汇总。
- 与列表查询共用 JOIN/过滤，保证 `stats.total` 与列表 `total` 同源。
- 存量库缺列可降级，不 500。

## 2. 契约

`GET /api/v2/portrait/annotations/stats?group_by=status&annotation_template=&review_status=&person_id=`

```json
{"code":200,"message":"success","data":{"group_by":"status","total":12,
 "items":[{"key":"pending","label":"待审核","count":8}],"degraded":false}}
```

- `group_by` ∈ `template|status|level|reviewer`；非法 400。
- `items` 按 `count` 降序、`key` 升序；`template` 用模板中文名，`level` 用「未开始/第 N 级」，`reviewer` 空值归并 `unassigned`（未指派）。
- 缺 `payload` 列 → 空集合；缺 `review_level`/`reviewer_id` → 单桶＋`degraded=true`。

## 3. 实现

| 层 | 位置 | 变更 |
|---|---|---|
| 引擎 | `annotation_template_engine.py::annotation_stats` | 复用 `base_sql` 条件；分组 SQL 常量拼接（无用户输入） |
| 路由 | `routes_profiles.py::api_annotation_stats` | 静态段先于 `{annotation_id}` |
| 代理 | `dps_proxy::dps_annotations_stats` | 静态段先于动态段 |
| 前端 | `dps.ts::getAnnotationStats` | 新增方法 |
| 前端 | `DpsAnnotationWorkbenchView.vue` | 队列卡 KPI 条；队列/模板筛选/审核后刷新；失败隐藏 |

## 4. 关键决策

1. **路由顺序**：静态 `stats` 必须注册在动态 `{annotation_id}` 之前（DT-04），两侧各加顺序断言。
2. **排序在 Python 侧**：避免不同数据库对 NULL/文本排序差异，保证口径一致。
3. **统计不含状态过滤联动**：前端固定 `group_by=status` 且只带模板过滤，避免"按状态筛选后其他状态计数消失"。
4. **KPI 失败静默**：统计为增强信息，失败不阻断队列主流程。

## 5. 测试与验证

- `tests/test_annotation_stats_v2_16.py`：6 passed（4 分组、过滤、legacy、路由顺序与 400）。
- `tests/test_dps_proxy.py`（stats 3 条）：通过。
- `tests/dps-annotation-stats-v180.spec.ts`：2 passed。
- `npm run build`：成功。

## 6. 风险与回滚

| 风险 | 处置 |
|---|---|
| 统计与列表口径漂移 | 复用同一 JOIN/过滤；单测断言 total |
| 缺列 500 | 列守卫＋`degraded` |
| 路由被动态段吞掉 | 注册顺序断言 |
| 回滚 | 移除端点与 KPI 条即可，无迁移 |
