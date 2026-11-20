# OpenBase-DevLogReport-v1.6.0

| 项 | 内容 |
|---|---|
| 版本 | v1.6.0 |
| 状态 | [Implemented] |
| 日期 | 2026-11-20 |
| 需求基线 | 《OpenBase-开发需求文档-v1.6.0》v1.0.0（RT-160-001~012） |
| 设计依据 | 《OpenBase-A4 标注详情接口-设计文档-v1.0.0》 |
| 作者 | 开发（AD）／前端（FD） |

## 修订历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0.0 | 2026-11-20 | A4 代理透传与审核收件箱接入 |

## 1. 交付内容

| # | 文件 | 变更 |
|:-:|---|---|
| 1 | `openbase/modules/dps_proxy/__init__.py` | 新增 `dps_annotation_detail`（GET `/annotations/{annotation_id}`，`quote` 编码） |
| 2 | `openbase/__init__.py` | `__version__` 1.5.0 → 1.6.0 |
| 3 | `tests/test_a4_annotation_detail_v160.py` | 新增 4 条代理用例 |
| 4 | `openbase-ui/src/core/api/dps.ts` | 新增 `DpsAnnotationDetail(Annotation)` 与 `getAnnotationDetail` |
| 5 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue` | 并行加载详情、`reviewTask` 合并、字段/证据/审核结论展示、失败回退 |
| 6 | `openbase-ui/package.json` | 1.5.0 → 1.6.0 |
| 7 | `openbase-ui/tests/dps-backend-v160.spec.ts` | 新增前端 API 用例 |

## 2. 关键实现

### 后端
- 路由注册于 `dps_annotations_list` 之后；`/annotations/export` 已在前，动态段不抢占静态路径。
- 透传查询参数与身份头，状态码/错误体由 `_adapt_response` 保真。

### 前端
- `loadReviewContext` 使用 `Promise.allSettled([detail, portrait, mapping, logs])`。
- `reviewTask = reviewDetail?.annotation ?? currentTask`；`reviewFields` 与证据来源优先详情。
- 详情失败（404/5xx）静默回退，不阻断画像/映射/留痕。

## 3. 自测

| 用例 | 结果 |
|---|---|
| `test_detail_route_registered` | PASS |
| `test_static_export_precedes_dynamic_detail` | PASS |
| `test_detail_forwards_encoded_path_and_identity` | PASS |
| `test_detail_upstream_404_passthrough` | PASS |
| `dps-backend-v160.spec.ts` | PASS |
| `npm run build` | PASS |

## 4. 设计一致性

| 设计项 | 落地 |
|---|---|
| 端到端链路 | 与设计 §1 一致 |
| 错误/降级 | 与设计 §5 一致 |
| 不新增页面路由 | 未改路由与导航 |

## 5. 已知限制

- 详情与画像/映射/留痕为并行四次请求，未做服务端聚合（保持职责边界）。
- 详情仅在审核视图加载；录入视图保持原行为。
