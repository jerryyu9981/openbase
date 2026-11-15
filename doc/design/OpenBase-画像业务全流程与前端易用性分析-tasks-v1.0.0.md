# OpenBase 画像易用性完善 · 任务分解（tasks）

- 版本：v1.3.0
- 状态：[Implemented]（T-01~T-12、T-18 部分、T-23 已交付；其余待排期）
- 日期：2026-11-15
- 作者：AI 编码代理

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-15 | 首版：P0/P1/P2 任务拆解（文件级改动、验证命令、依赖与门禁） | AI 编码代理 |
| v1.1.0 | 2026-11-15 | 回填首批交付状态：P0 全部完成、T-12 审核补全完成、T-18 画像 360（雷达/分组标签/证据抽屉）完成；时间线与 T-13 起顺延 | AI 编码代理 |
| v1.2.0 | 2026-11-16 | T-09（标注列表接口）、T-10（代理通路）、T-11（标注工作台）完成；标注链路闭环 | AI 编码代理 |
| v1.3.0 | 2026-11-16 | T-23 完成：详情页对接异步任务查询、重算结果卡片；DPS 修复模板命名空间 PG 落点并补 2 条单测 | AI 编码代理 |

## 交付状态（v1.3.0）

| 任务 | 状态 |
|---|---|
| T-01 规则引擎页去 mock（改只读总览） | 已完成 |
| T-02 画像详情维度可视化（雷达 + 维度条 + 完整度） | 已完成 |
| T-03 标签按维度分组 | 已完成 |
| T-04 模板口径切换 | 已完成（`template_code` 透传 + 404 空态） |
| T-05 计算弹窗模板下拉（active 模板）+ 错误原文 + 去激活引导 | 已完成 |
| T-06 保存后下一步引导（含激活按钮） | 已完成 |
| T-07 旧路径跳转修正 | 已完成 |
| T-08 标注字段 `target_dimension` 维度下拉 | 已完成 |
| T-12 审核 `fields` 服务端补全 | 已完成（`fields_backfilled`） |
| T-09 标注列表接口 | 已完成（`GET /portrait/annotations`） |
| T-10 代理标注通路 | 已完成（`/annotate`、`/annotations`） |
| T-11 标注工作台页 | 已完成（`/portrait/dps/annotations`） |
| T-18 画像 360 | 部分完成：雷达/分组标签/证据抽屉已交付；时间线与版本对照顺延 |
| T-23 详情页重算结果（任务查询对接） | 已完成（`GET /portraits/tasks/{task_id}` 轮询 + 结果卡片） |
| T-13 ~ T-17、T-19 ~ T-22 | 未开始 |

> 说明：本文件是分析稿的**执行侧附录**。所有任务在需求文档获批前**不进入编码**。

## 0. 门禁

- G0：分析文档 + 本任务表获批（人工门禁）。
- G1：每批任务完成须通过 `ruff` / `pytest`（DPS）、`vue-tsc` / `eslint`（前端）。
- G2：文档同步升版并写修订历史；DPS 与 OpenBase 两仓分别提交并推送三远程。

## 1. P0（纯前端为主，建议首批）

| ID | 任务 | 主要文件 | 具体改动 | 验证 |
|---|---|---|---|---|
| T-01 | 规则引擎页去 mock | `openbase-ui/src/modules/portrait/pages/Rules.vue` | 删除 `rules`/`tasks` 本地 mock；改为读取 active 模板（`dpsApi.listTemplates({status:'active'})` + `getTemplate`）渲染维度/规则/权重只读摘要；每行「去编排」跳 `/portrait/dps/templates/{code}/edit` | 页面无 mock 常量；点击可跳转；`eslint` 0 错 |
| T-02 | 画像详情维度可视化 | `pages/PortraitDetail.vue` | 维度 JSON `<pre>` 替换为：总分/置信度/完整度/状态徽标 + 每维度进度条（分值取自 `dimensions`，缺失灰显并标「未采集」，50 分标「缺省值」） | 手动构造 `partial` 画像验证文案；`vue-tsc` 通过 |
| T-03 | 标签分组展示 | `pages/PortraitDetail.vue` | 标签按维度前缀（`dim:key`）分组折叠；无前缀归「其他」 | 有/无标签两种空态正确 |
| T-04 | 模板口径切换 | `core/api/dps.ts`、`pages/PortraitDetail.vue` | `getPortrait(personId, templateCode?)` 增加 query 透传；页面右上加模板下拉（来自 active 列表），切换后重新拉取；无命名空间 → 空态「该模板尚未计算」 | 切换后请求 URL 含 `template_code`；404 显示空态而非错误 |
| T-05 | 计算弹窗模板下拉 | `pages/PortraitList.vue` | `templateCode` 文本框改 `el-select`（active 模板），仅一个 active 时默认选中；catch 中展示 `describeDpsError` 的 `detail`；未激活提示附「去激活」链接 | 无法手填；400 文案与后端 `detail` 一致 |
| T-06 | 保存后下一步引导 | `pages/DpsTemplateWorkbenchView.vue` | 保存成功后展示下一步卡片：`status!=='active'` → 「激活模板」（调 `activateTemplate`）；已 active → 「创建标注模板」跳 `/portrait/dps/annotation-templates` | 保存→激活 1 次点击完成 |
| T-07 | 旧路径跳转修正 | `DpsTemplateListView.vue`、`DpsAnnotationTemplateView.vue` | `/dps/...` → `/portrait/dps/...`（3 处） | 全仓 grep `/dps/` 无路由硬编码 |
| T-08 | 标注字段维度下拉 | `pages/DpsAnnotationFieldView.vue` | `target_dimension` 由自由输入改为所属画像模板维度下拉（`getTemplate(template_code).dimension_config.dimensions[].code`）；为空的行标「不进入画像」 | 无法输入非法维度；提示可见 |

## 2. P1（需代理 + DPS 只读接口）

| ID | 任务 | 主要文件 | 具体改动 | 验证 |
|---|---|---|---|---|
| T-09 | DPS 标注列表接口 | `DPS/src/rest_api/routes/routes_profiles.py` | 新增 `GET /portrait/annotations`（分页、`template_code`、`review_status`、`person_id` 过滤；租户限定；只读） | 新增 pytest：过滤/分页/租户隔离 |
| T-10 | 代理标注通路 | `openbase/modules/dps_proxy/__init__.py` | 新增 `/annotate`（POST）、`/annotations`（GET）；注意静态段先于 `/annotations/{id}/review` 注册 | 代理 pytest：200 透传、上游 4xx 保真 |
| T-11 | 标注工作台页 | 新增 `pages/DpsAnnotationWorkbenchView.vue` + `index.ts` 路由与菜单 | 左：按标注模板渲染表单（enum/number/date/list/string）；右：待办队列（pending）+ 审核动作；复用时回传 `annotation_template` 与 `fields` | 走查：录入→审核→标签联动成功 |
| T-12 | 审核 fields 兜底 | `routes_profiles.py::_apply_annotation_review` | 未带 `fields` 时从 `annotation.payload` 补全；仍取不到 → 400 明确文案；响应增加 `tag_sync.status` | pytest：三种情形（带/可补/不可补） |
| T-13 | 版本列表接口 | DPS `template_engine.py` + `routes_profiles.py`；代理；`DpsTemplateVersionView.vue` | `GET /templates/{code}/versions` 读 `portrait_template_history`（version/时间/操作人/摘要）；前端 from/to 改下拉 | pytest + 版本下拉可选 |
| T-14 | 影响面扩展 | `DPS/src/engines/template_preflight.py::impact`；`DpsTemplatePreflightView.vue` | 新增 `affected_profile_count` / `affected_subject_count`，响应保留 `basis` | pytest：口径有数据；前端展示口径说明 |
| T-15 | 服务端检索 | 代理 `/portraits/search`；`pages/PortraitSearch.vue` | 改用 `POST /portraits/search`，支持关键词/标签/维度分数区间/模板 | 结果总数与后端一致 |
| T-16 | 空态/失败态分离 | `DpsLineageView.vue`、`DpsMeasureView.vue` 等 | 404 → 「暂无记录」空态；5xx → 错误 + `request_id`；措施页主体改选择器 | 404/500 两态走查 |
| T-17 | 血缘主体选择器 | `DpsLineageView.vue`、`DpsMeasureView.vue` | 复用画像列表选择器替代手填 ID | 无法手填非法 ID |
| T-23 | 详情页重算结果 | `pages/PortraitDetail.vue`；DPS `routes_profiles.py::_persist_template_namespace` | 工具栏「重算」→ `POST /portraits/calculate`；有 `task_id` 时轮询 `GET /portraits/tasks/{task_id}`，卡片展示任务 ID/口径/完成时间/综合评分（含增减）/完整度/存储落点/维度明细；完成后刷新 360。DPS 侧修复 PG `updated_at` 类型并补存 `confidence`/`data_completeness` | 任务终态 `succeeded` 且 `storage.persisted=true`；浏览器走查卡片字段齐全、无红错 |

## 3. P2（体验升级）

| ID | 任务 | 主要文件 | 说明 |
|---|---|---|---|
| T-18 | 画像 360 视图 | `pages/PortraitDetail.vue` 或新增 `Portrait360View.vue` | 身份卡 + 维度雷达/条 + 分组标签 + 证据抽屉 + 时间线；先复用现有 `attributes` |
| T-19 | 端到端向导 | 新增 `PortraitSetupWizardView.vue` | 4 步 stepper：模板 → 标注模板 → 采集 → 看画像，保留上下文 |
| T-20 | 示例模板与术语中心 | `doc/` + `modules/portrait/templates/` | 3 个示例模板一键套用；`glossary` 内联提示 |
| T-21 | 权限与角色 | OpenBase 权限模块 + DPS 角色映射 | 模板管理员/录入员/审核员/只读 + 审批流 |
| T-22 | 性能治理 | 工作台组件 | 分区懒渲染、虚拟滚动、试运行分页、默认 async 计算 |

## 4. 验证命令

```bash
# DPS
python -m ruff check src tests
python -m pytest src/tests -k "template or annotation or portrait"
python -m pytest --cov=src --cov-report=term-missing

# 前端（openbase-ui）
npm run type-check
npm run lint
```

## 5. 交付留痕

- 设计文档：`doc/design/OpenBase-画像业务全流程与前端易用性分析-v1.0.0.md`（本批升 v1.1.0 回填实施结论）。
- 开发记录：`doc/development/OpenBase-画像易用性完善-DevLogReport-v1.0.0.md`（实施后新建）。
- 提交：OpenBase 与 DPS 分别提交，推送 `origin` / `backup` / `github`。
