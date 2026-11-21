# OpenBase-A7模板服务端筛选-设计文档-v1.0.0

| 项 | 内容 |
|---|---|
| 文档类型 | 后端＋前端详细设计 |
| 版本 | v1.0.0 |
| 状态 | [Implemented]（2026-11-21） |
| 适用范围 | DPS `GET /portrait/templates`；OpenBase `dps-proxy`；模板中心 |
| 上游依据 | 《OpenBase 开发需求文档 v1.8.0》FR-180-01；《DPS 统一前端页面功能设计》v2.7.0 §9 A7 |
| 作者 | 后端工程师（BE）＋前端工程师（FD） |
| 日期 | 2026-11-21 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 首版：模板列表 keyword/category_id/template_kind 服务端筛选与前端接入 | BE/FD |

## 1. 设计目标

- 大数据量下列表筛选由上游执行，前端不再只过滤已加载集合。
- 保持既有响应结构与权限点不变，零回归。

## 2. 契约

`GET /api/v2/portrait/templates?status=&profile_type=&subject_type=&keyword=&category_id=&template_kind=`

| 参数 | 规则 |
|---|---|
| keyword | 去空白后 `LOWER(name)/LOWER(code)` 模糊匹配；`%`/`_`/`\` 转义并 `ESCAPE '\'` |
| category_id | 精确匹配 |
| template_kind | `composite`/`component`；其他 400 |

## 3. 实现

| 层 | 位置 | 变更 |
|---|---|---|
| 引擎 | `template_engine.py::list_templates` | 3 个可选参数；条件数组参数化追加 |
| 路由 | `routes_profiles.py::api_list_portrait_templates` | 3 个 Query；`template_kind` 白名单校验 |
| 代理 | `dps_proxy::dps_templates_list` | 无逻辑改动，参数透传＋docstring |
| 前端 | `dps.ts::DpsTemplateFilter` | 增加 3 字段 |
| 前端 | `DpsTemplateListView.vue` | `load()` 传参；删除本地过滤；分类点击/清除触发 `load()` |

## 4. 关键决策

1. **通配符转义**：避免用户输入 `%` 导致全表命中；`ESCAPE` 同时兼容 SQLite/PG。
2. **大小写不敏感**：统一 `LOWER()`，不依赖 SQLite 默认排序规则。
3. **空白关键字忽略**：避免 `%%` 全量匹配。
4. **分类点击即请求**：分类是离散筛选，无需再点「查询」；关键字仍需按钮触发，减少输入抖动。

## 5. 降级

- 上游 <2.16.0 时未知参数被 FastAPI 忽略，前端显示全量（不报错），文档标注依赖版本。
- 无租户上下文时沿用 `TENANT_VISIBLE_CLAUSE` 既有语义。

## 6. 测试与验证

- `tests/test_template_filter_v2_16.py`：6 passed（name/code、转义、分类、类型、AND、空白、路由 400）。
- `tests/test_dps_proxy.py::test_templates_server_filters_forwarded`：通过。
- `tests/dps-template-filter-v180.spec.ts`：3 passed。
- `npm run build`：成功。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| LIKE 注入 | 参数化＋转义＋ESCAPE |
| 代理裁剪参数 | 回归用例固定四参数透传 |
| 回滚 | 回退三处代码即可；上游参数可选，无数据迁移 |
