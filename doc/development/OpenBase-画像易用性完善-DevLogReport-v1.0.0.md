# OpenBase 画像易用性完善 · 开发记录（DevLogReport）

- 版本：v1.0.0
- 状态：[Implemented]
- 对应设计：`doc/design/OpenBase-画像业务全流程与前端易用性分析-v1.0.0.md`（v1.1.0）
- 任务清单：`doc/design/OpenBase-画像业务全流程与前端易用性分析-tasks-v1.0.0.md`（v1.1.0）
- 日期：2026-11-15
- 作者：AI 编码代理

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-15 | 首批交付：P0（8 项）+ 画像 360（雷达/分组标签/证据抽屉）+ 审核 fields 服务端补全；记录验证证据与遗留项 | AI 编码代理 |

## 1. 变更范围

| 仓库 | 模块 | 说明 |
|---|---|---|
| DPS | `engines/annotation_template_engine.py` | 新增 `get_structured_annotation`，读取标注模板 code / 归属画像模板 / 结构化字段 |
| DPS | `rest_api/routes/routes_profiles.py` | 新增 `_backfill_review_fields`；审核通过缺参时服务端补全，响应新增 `fields_backfilled` |
| DPS | `tests/test_annotation_review_backfill_v2_13.py` | 新增 5 条单测 |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | 画像详情透传 `template_code` 查询参数 |
| OpenBase | `core/api/dps.ts` | `getPortrait(personId, templateCode?)`；`DpsPortrait` 补齐六维分 / attributes / tags 行类型 |
| OpenBase | `pages/Rules.vue` | 由本地 mock 重写为 active 模板规则只读总览 |
| OpenBase | `pages/PortraitDetail.vue` | 360 视图：身份卡 / 完整度 / 雷达 / 维度条 / 分组标签 / 证据抽屉 / 模板口径切换 |
| OpenBase | `pages/PortraitList.vue` | 计算弹窗改 active 模板下拉、错误原文与「去激活」引导；标签列对象渲染修复 |
| OpenBase | `pages/DpsTemplateWorkbenchView.vue` | 保存后「下一步」卡片（激活 / 建标注模板 / 看规则 / 去计算） |
| OpenBase | `pages/DpsAnnotationFieldView.vue` | `target_dimension` 改归属模板维度下拉，列头提示「留空=不进画像」 |
| OpenBase | `pages/DpsTemplateListView.vue`、`pages/DpsAnnotationTemplateView.vue` | `/dps/...` 旧路径硬编码修正为 `/portrait/dps/...` |

## 2. 关键实现说明

1. **审核联动补全**：历史契约要求调用方在复核请求体回传 `annotation_template` + `fields`，否则标签联动静默失效。现改为：缺参时按 `annotation.id → annotation.payload + annotation_template.{code,template_code}` 补全，并在响应 `fields_backfilled` 告知；自由文本标注（无 payload）保持不联动、不报错。
2. **画像详情取数口径**：`GET /portrait/{id}` 不返回 `dimensions`，仅六维列 + `tags` 行；选择模板时通过 `?template_code=` 取 `result_namespace`，维度/置信度/完整度均从该命名空间渲染。
3. **partial 语义不新增字段**：`PortraitResult` 无 `status` 字段，前端以 `data_completeness < 0.8` 派生「部分完成」提示，避免改动打分契约。
4. **规则总览解析**：`dimension_config` 可能是对象或 JSON 串，统一经 `parseDimensions` 归一；历史 `legacy_map` 规则无 `type` 时标注为「历史兼容映射」。

## 3. 验证证据

| 项 | 命令 | 结果 |
|---|---|---|
| DPS 新增单测 | `python -m pytest src/tests/test_annotation_review_backfill_v2_13.py` | 5 passed，新增文件覆盖率 100% |
| DPS 标注模板回归 | `python -m pytest src/tests/test_annotation_template_v2_10.py` | 52 passed |
| OpenBase 代理回归 | `python -m pytest tests/test_dps_proxy.py` | 44 passed |
| 代理静态检查 | `ruff check openbase/modules/dps_proxy/__init__.py` | All checks passed |
| 前端类型检查 | `vue-tsc --noEmit` | 0 错误 |
| 前端 lint | `eslint`（8 个改动文件） | 0 错误 |

## 4. 未覆盖 / 后续

1. 标注录入与待办页（P1-1）：UI 仍无人工结构化标注入口；需新增 DPS `GET /portrait/annotations` 与代理 `/annotate`。
2. 模板版本列表接口（P1-3）、影响面「受影响画像数」（P1-4）、服务端检索（P1-5）、血缘主体选择器（P1-6）。
3. 画像 360 的时间线与版本对照（P2-1 后半）。
4. 浏览器端到端走查（规则总览 / 画像 360 / 计算弹窗 / 下一步卡片）尚未执行，建议在下一批与 P1 一并回归。
