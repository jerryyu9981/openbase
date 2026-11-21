# Tasks：A1 标注队列统计

| 项 | 内容 |
|---|---|
| 需求基线 | 《OpenBase-开发需求文档-v1.8.0》 |
| 设计依据 | 《OpenBase-A1标注队列统计-设计文档-v1.0.0》 |
| 状态 | [Done] 已验收（2026-11-21） |

## T1 DPS 聚合与端点

- [x] T1.1 `annotation_template_engine.py::annotation_stats`（4 种分组 ＋ 过滤 ＋ 缺列降级）
- [x] T1.2 `routes_profiles.py::api_annotation_stats`（静态段先于 `{annotation_id}`）
- [x] T1.3 新增 `src/tests/test_annotation_stats_v2_16.py`（引擎 6 条 ＋ 路由 3 条）
- [x] T1.4 DPS 版本 `2.15.0 → 2.16.0`

## T2 OpenBase 代理

- [x] T2.1 新增 `dps_annotations_stats`（静态段先于动态段）
- [x] T2.2 新增 `tests/test_dps_proxy_stats_v170.py`（3 条）
- [x] T2.3 OpenBase 版本 `1.6.0 → 1.7.0`

## T3 前端

- [x] T3.1 `dps.ts` 新增 `DpsAnnotationStats`／`getAnnotationStats`
- [x] T3.2 工作台队列 KPI 条（`data-test="annotation-stats"`）
- [x] T3.3 队列加载/模板筛选/审核后刷新统计
- [x] T3.4 新增 `tests/dps-annotation-stats-v180.spec.ts`（4 条）
- [x] T3.5 前端版本 `1.7.0 → 1.8.0`

## T4 验证与留痕

- [x] T4.1 DPS 定向 pytest 全绿
- [x] T4.2 代理回归全绿
- [x] T4.3 前端定向 vitest ＋ `npm run build` 成功
- [x] T4.4 文档 v1.8.0 与设计回填 v2.7.0
- [x] T4.5 仅 stage 本任务文件，提交并推送三远程
