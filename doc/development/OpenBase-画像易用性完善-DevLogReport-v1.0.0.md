# OpenBase 画像易用性完善 · 开发记录（DevLogReport）

- 版本：v1.4.0
- 状态：[Implemented]
- 对应设计：`doc/design/OpenBase-画像业务全流程与前端易用性分析-v1.0.0.md`（v1.4.1）
- 任务清单：`doc/design/OpenBase-画像业务全流程与前端易用性分析-tasks-v1.0.0.md`（v1.3.1）
- 日期：2026-11-16
- 作者：AI 编码代理

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-15 | 首批交付：P0（8 项）+ 画像 360（雷达/分组标签/证据抽屉）+ 审核 fields 服务端补全；记录验证证据与遗留项 | AI 编码代理 |
| v1.1.0 | 2026-11-16 | 第二批：标注录入闭环（DPS 标注队列接口 + 代理 /annotate、/annotations + 前端标注工作台），补 3 条单测 | AI 编码代理 |
| v1.2.0 | 2026-11-16 | 服务重启后实跑验证；修复 3 处 PG 适配（annotation.template_id、profile_tag tenant+upsert、tag_lineage.profile_id），补 2 条单测；浏览器走查 PASS | AI 编码代理 |
| v1.3.0 | 2026-11-16 | 详情页对接异步任务查询（重算 + 结果卡片）；修复 `_persist_template_namespace` 的 PG TIMESTAMPTZ 写入并补存完整度/置信度，补 2 条单测；实跑与浏览器走查通过 | AI 编码代理 |
| v1.3.1 | 2026-11-16 | 补强重算交互：等待计时与进度条、轮询状态实时刷新、维度变化列、失败重试、完成后自动滚动、口径锁定与按钮说明 | AI 编码代理 |
| v1.4.0 | 2026-11-16 | P0 落地：模板规则/权重成为评分事实源、标签契约归一、标注字段扩展、`tag_bindings` 校验、评分项接口与前端弹窗；补 10 条单测并完成运行态与浏览器验证 | AI 编码代理 |

## 1. 变更范围

| 仓库 | 模块 | 说明 |
|---|---|---|
| DPS | `engines/annotation_template_engine.py` | 新增 `get_structured_annotation`，读取标注模板 code / 归属画像模板 / 结构化字段 |
| DPS | `rest_api/routes/routes_profiles.py` | 新增 `_backfill_review_fields`；审核通过缺参时服务端补全，响应新增 `fields_backfilled`；修复 `_persist_template_namespace` 的 PG `updated_at` 类型并补存 `confidence` / `data_completeness` |
| DPS | `tests/test_annotation_review_backfill_v2_13.py` | 新增 5 条单测 |
| DPS | `tests/test_template_namespace_persist_v2_13.py` | 新增 2 条单测（datetime 落库 + 命名空间字段 + 画像缺失降级） |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | 画像详情透传 `template_code` 查询参数 |
| OpenBase | `core/api/dps.ts` | `getPortrait(personId, templateCode?)`；`DpsPortrait` 补齐六维分 / attributes / tags 行类型 |
| OpenBase | `pages/Rules.vue` | 由本地 mock 重写为 active 模板规则只读总览 |
| OpenBase | `pages/PortraitDetail.vue` | 360 视图：身份卡 / 完整度 / 雷达 / 维度条 / 分组标签 / 证据抽屉 / 模板口径切换；新增「重算」与重算结果卡片（轮询任务查询接口） |
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

## 5. 第二批（v1.1.0，标注闭环）

| 仓库 | 模块 | 说明 |
|---|---|---|
| DPS | `engines/annotation_template_engine.py` | 新增 `query_annotations`：跨主体分页查询（模板/状态/主体过滤、租户列存在时过滤、payload→fields、缺列降级） |
| DPS | `rest_api/routes/routes_profiles.py` | 新增 `GET /portrait/annotations`（枚举校验 400、分页收敛） |
| DPS | `tests/test_annotation_queue_v2_13.py` | 3 条单测：过滤分页、存量缺列、page_size 收敛 |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | 新增 `GET /annotations`（查询参数透传）、`POST /annotate` |
| OpenBase | `core/api/dps.ts` | 新增 `listAnnotations` / `createAnnotation` 与队列类型 |
| OpenBase | `pages/DpsAnnotationWorkbenchView.vue` | 标注录入（按 schema 动态字段、必填前置校验）+ 待办队列（筛选/分页/通过/驳回） |
| OpenBase | `modules/portrait/index.ts` | 路由 `/portrait/dps/annotations` + 导航「标注录入与审核」 |

闭环：录入（pending）→ 队列通过（服务端补全 fields 并联动标签/血缘）→ 计算后画像可见。

验证：DPS 定向 60 passed；代理回归 44 passed；`ruff` / `vue-tsc` / `eslint` 均 0 错误。

## 6. 运行验证与 PG 适配修复（v1.2.0）

| # | 现象 | 根因 | 修复文件 |
|---|---|---|---|
| 1 | 录入标注 500 | `annotation_template.id` 为 UUID，`annotation.template_id` 为 TEXT，asyncpg 拒绝隐式转换 | `engines/annotation_template_engine.py::_insert_annotation_row`（`str(template_id)`） |
| 2 | 审核 `synced=1` 但画像标签为 0 | `profile_tag` 未写 `tenant_id`（详情按 person_id+tenant_id 过滤），且唯一键导致重复联动冲突 | `sync_tags_to_profile` / `_insert_profile_tag`（补 tenant、`ON CONFLICT DO UPDATE`） |
| 3 | 血缘 `recorded=0` | `tag_lineage.profile_id` 为 TEXT，传入 UUID 对象 | `routes_profiles.py::_sync_tags_after_approval`（`str(profile_id)`） |

实跑证据（重启后）：
- 录入 200 → 队列 pending total=1 → 审核 200 / `backfilled=true` / `synced=1` / `lineage.recorded=1`
- 画像详情 `tags count=1`（`behavior:signin_compliance_rate`）
- 浏览器走查 `/portrait/dps/annotations` PASS：标题正确、模板渲染 19 个字段、队列 3 行、无报错

单测：新增 `test_insert_annotation_casts_uuid_template_id_to_text`、`test_insert_profile_tag_writes_tenant_and_upserts`；定向 10 passed。

## 7. 详情页重算结果对接任务查询（v1.3.0）

**目标**：详情页可直接重算，并通过任务查询接口展示本次重算结果，不必回列表或猜测是否成功。

**实现**
- 前端 `PortraitDetail.vue`：工具栏新增「重算」，按当前口径提交 `POST /portraits/calculate`；响应含 `task_id` 时复用 `dpsApi.waitPortraitTask` 轮询 `GET /portraits/tasks/{task_id}`（2s/60s），终态后渲染「重算结果」卡片（任务 ID、口径、完成时间、综合评分及增减、完整度、存储落点、维度明细），并自动刷新 360 视图；同步返回（无 `task_id`）时直接展示结果体。
- DPS `routes_profiles.py::_persist_template_namespace`：修复 PostgreSQL 下 `updated_at` 必须为 `datetime` 对象（原 ISO 字符串被 asyncpg 拒绝，`persisted=false` 静默丢结果）；命名空间补存 `confidence`、`data_completeness`，详情页口径视图可直接展示。

**验证**
- 实跑：任务 `1547706…` → `succeeded`，`storage.persisted=true namespace=cor-persona-risk-v1`；`GET /portraits/61?template_code=…` 回读命名空间含 `overall_score`/`data_completeness`/`confidence`/`dimensions`。
- 浏览器走查 `/portrait/61`：卡片「已完成」，任务 ID `a3afeba5…`、综合评分 `50.0（+13.4）`、完整度 `7%`、存储落点「默认口径（六维列）」、维度表 6 行，无红色报错。
- 单测：`test_template_namespace_persist_v2_13.py` 2 条；与既有标注回归合计定向 12 passed；`vue-tsc --noEmit`、`eslint` 0 错误。

## 8. 重算交互细节补强（v1.3.1）

在 §7 基础上补齐“用户能直观看到结果”的交互反馈：

| 场景 | 交互 | 实现要点 |
|---|---|---|
| 提交后等待 | 卡片立即出现进度条 +「已等待 Ns」 | 1s 计时器；`onBeforeUnmount` 清理 |
| 轮询过程 | 状态实时刷新「排队中 → 计算中 → 已完成」 | `waitPortraitTask` 新增 `onStatus(task)` 回调 |
| 完成定位 | 结果卡片平滑滚入视口，避免误判无响应 | `nextTick` + `scrollIntoView` |
| 结果解读 | 综合评分增减、维度「变化」列（绿升红降）、计算耗时 | 提交前快照基线分，结果返回后逐维对比 |
| 失败处理 | 错误信息内嵌「重试」按钮 | 复用 `recalculate()`，重置卡片状态 |
| 防误操作 | 计算中锁定口径下拉；「重算」按钮 tooltip 说明语义 | `:disabled="recalcRunning"` + tooltip |

验证：`vue-tsc --noEmit`（TSC_OK）、`eslint`（0 错误）通过；浏览器走查 `/portrait/61`：点击重算后出现「排队中」与「已等待 1s」，完成态卡片显示任务 ID、耗时 `0.13 s`、综合评分 `50.0（+13.4）`、完整度 `7%`，维度表为「维度/得分/变化/置信度」四列且变化值如 `基础属性 -22.5`，无红色报错。

## 10. P0：模板规则成为评分事实源（v1.4.0）

依据《OpenBase-画像模板-标注模板-评分项对应关系与治理方案》v1.0.1 阶段一实施。

| 仓库 | 模块 | 说明 |
|---|---|---|
| DPS | `engines/portrait/core.py` | `calculate_portrait`/`calculate_dimension_score` 新增 `dimension_rules`/`dimension_weights`/`dimension_names`；规则 key 带/不带维度前缀均可命中；模板维度缺规则显式 `ValueError` |
| DPS | `engines/portrait/validation.py` | 综合分改用模板权重；完整度按模板规则统计（后缀兼容） |
| DPS | `rest_api/routes/routes_profiles.py` | `_execute_calc` 由 `TemplateRegistry.resolve_dimensions()` 驱动；新增 `GET /portrait/templates/{code}/scoring-items` |
| DPS | `engines/annotation_template_engine.py` | 字段支持 `tag_key`/`score_map`/`score_direction`；标签 code 用 `tag_key`；打分支持 score_map 优先与 `lower_better` |
| DPS | `engines/template_engine.py` | `tag_bindings` 对象→数组归一；引用校验（不存在/未激活报错，跨归属告警） |
| DPS | `engines/portrait/template_preview.py` | 存量对象格式兼容（warning 提示迁移）+ 维度元素类型校验 |
| DPS | `tests/test_p0_template_scoring_v3.py` | 新增 10 条单测 |
| OpenBase | `modules/dps_proxy/__init__.py` | 新增评分项字典代理 |
| OpenBase | `core/api/dps.ts` | 新增评分项类型与 `getTemplateScoringItems` |
| OpenBase | `pages/PortraitDetail.vue` | 工具栏「查看评分项」+ 弹窗（维度权重与规则明细） |

验证：

| 项 | 结果 |
|---|---|
| `pytest src/tests/test_p0_template_scoring_v3.py -q` | 10 passed |
| 模板重算（`cor-persona-intake-v1`，person 61，同步入口） | 6 维 basic/crime/psychology/behavior/social/intervention，规则 key 为模板 key，`storage.persisted=true` |
| 默认口径回归（不传 `template_code`） | 6 维 basic/behavior/psychology/social/correction/risk 不变 |
| 评分项接口（DPS 直连 + OpenBase 代理） | 6 维 / 32 规则 / `source=template` / `extends=cor-persona-root-v1` |
| 浏览器走查 `/portrait/tenant-1_1` | 弹窗显示「共 6 个维度 / 32 条规则；继承自 cor-persona-root-v1」，无错误提示 |

> 说明：排查中“重算仍只有 4 维”系 2026-11-15 历史任务被幂等键复用所致，非代码问题；详见治理方案 §11.2。

## 11. 未覆盖 / 后续

1. 模板版本列表接口（P1-3）、影响面「受影响画像数」（P1-4）、服务端检索（P1-5）、血缘主体选择器（P1-6）。
2. 画像 360 的时间线与版本对照（P2-1 后半）。
3. P1 数据治理：存量标注模板补 `tag_key`/`score_map`、同名标签来源隔离（D-04）、`social`/`crime` 标注来源、risk 模板 `tag_bindings` 迁移。
