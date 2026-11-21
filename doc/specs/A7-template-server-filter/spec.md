# Spec：A7 模板列表服务端筛选（DPS 2.16.0 / OpenBase 1.7.0 / 前端 1.8.0）

| 项 | 内容 |
|---|---|
| 状态 | **[Implemented]**（2026-11-21 已批准并交付） |
| 日期 | 2026-11-21 |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》v2.6.0 §9 A7（L343）、§14 风险「模板列表前端过滤大数据量」（L427）；用户 2026-11-21 指令「继续完成 A1/A2/A5/A7/A8/A13」 |
| 版本冻结 | DPS `2.15.0 → 2.16.0`（`DPS/src/__init__.py`）；OpenBase 后端 `1.6.0 → 1.7.0`（`openbase/__init__.py`）；前端 `1.7.0 → 1.8.0`（`openbase-ui/package.json`） |
| 交付链 | DPS `GET /api/v2/portrait/templates` → OpenBase `GET /api/v1/dps-proxy/templates` → 前端模板中心 |

## 1. 目标与范围

**目标**：把模板中心的「关键字 / 分类 / 模板类型」筛选从浏览器端过滤改为上游服务端筛选，避免大数据量下只过滤当前已加载集合、以及分页/统计口径失真。

**范围内**
1. DPS `TemplateEngine.list_templates` 增加 `keyword`、`category_id`、`template_kind` 过滤（参数化 SQL）。
2. DPS 列表路由新增同名 Query 参数，`template_kind` 非法值返回 400。
3. OpenBase `dps-proxy` 列表路由保持查询参数原样透传（代码不改，补契约注释与回归用例）。
4. 前端 `DpsTemplateFilter` 增加三字段；模板中心 `load()` 传服务端参数，删除三处客户端过滤。
5. 版本号、测试、文档与设计回填。

**范围外**
- 不分页（上游列表仍返回全量 `items`）；不改模板分类/子模板引擎；不改健康度采样逻辑（仍取前 30 条）。
- 不新增权限点（沿用 `portrait_template:read`）。

## 2. 源码事实（已核对）

| # | 事实 | 位置 |
|:-:|---|---|
| F1 | DPS 列表路由仅支持 `status/profile_type/subject_type`，直接调 `list_templates` | `DPS/src/rest_api/routes/routes_profiles.py` L526-542 |
| F2 | `list_templates` 已用条件数组 ＋ 参数化 `fetch_all`，租户过滤 `TENANT_VISIBLE_CLAUSE` | `DPS/src/engines/template_engine.py` L409-435 |
| F3 | 代理 GET 路由 `_forward_query_params(request)` 透传全部 query，不在本仓裁剪 | `openbase/modules/dps_proxy/__init__.py` L1234-1236、L1370-1385 |
| F4 | 前端 `filteredItems` 对 `category_id/template_kind/keyword` 做客户端过滤，`load()` 仅传 `status` | `openbase-ui/src/modules/portrait/pages/DpsTemplateListView.vue` L577-590、L722-725 |
| F5 | 分类节点点击/清除只改本地 `categoryFilter`，不触发请求 | 同上 L773-779 |
| F6 | `DpsTemplateFilter` 仅 5 个字段 | `openbase-ui/src/core/api/dps.ts` L~130 |

## 3. 契约

### 3.1 DPS `GET /api/v2/portrait/templates`

| 参数 | 类型 | 语义 |
|---|---|---|
| `status` | string 可选 | 精确匹配（既有） |
| `profile_type` | string 可选 | 精确匹配（既有） |
| `subject_type` | string 可选 | 精确匹配（既有） |
| `keyword` | string 可选 | `name` 或 `code` 模糊匹配（大小写不敏感，`%`/`_`/`\` 转义） |
| `category_id` | string 可选 | 精确匹配 `category_id` |
| `template_kind` | string 可选 | `composite` / `component`；其他值 400 `detail="不支持的模板类型: X"` |

响应结构不变：`{code:200,message:"success",data:{items:[...],total:N}}`。

### 3.2 SQL 约束

- 全部条件参数化，禁止字符串拼接用户输入；`keyword` 先转义再包 `%kw%`，SQL 追加 `ESCAPE '\'`。
- `keyword` 为空白字符串时视为未传。
- 多条件为 AND；租户过滤保持最前置。

### 3.3 前端

- `load()` 请求参数：`{status?, keyword?, category_id?, template_kind?}`。
- `filteredItems` 直接等于 `data.items`（删除三处本地过滤）。
- 分类树点击、清除分类、重置筛选、应用保存视图后均调用 `load()`。
- `statusCounts` 仍基于当前返回集合（当前筛选结果的状态分布），不改口径。

## 4. 实现清单（精确到文件/函数）

1. `DPS/src/engines/template_engine.py::list_templates`：新增 3 个 Optional 参数与条件分支。
2. `DPS/src/rest_api/routes/routes_profiles.py::api_list_portrait_templates`：新增 3 个 `Query(None)`，校验 `template_kind`。
3. `DPS/src/__init__.py`：`__version__` → `2.16.0`（docstring 同步）。
4. `OpenBase/openbase/modules/dps_proxy/__init__.py::dps_templates_list`：docstring 补三参数（无逻辑改动）。
5. `OpenBase/openbase-ui/src/core/api/dps.ts::DpsTemplateFilter`：增加 `keyword/category_id/template_kind`。
6. `OpenBase/openbase-ui/src/modules/portrait/pages/DpsTemplateListView.vue`：`load()` 传参；`filteredItems` 简化；分类点击/清除触发 `load()`。
7. `OpenBase/openbase-ui/package.json` → `1.8.0`。

## 5. 测试

| 层 | 用例 | 断言 |
|---|---|---|
| DPS 引擎 | `test_template_filter_v2_16.py` 5 条 | keyword 命中 name/code；通配符 `%` 被转义；category_id 精确；template_kind 精确；组合条件 AND |
| DPS 路由 | 同上 1 条 | 非法 `template_kind` → 400 |
| 代理 | `tests/test_dps_proxy*.py` 1 条 | 三参数原样出现在上游请求 query |
| 前端 | `openbase-ui/tests/dps-template-filter-v180.spec.ts` 4 条 | `listTemplates` 传参；保存视图恢复后传参；重置清空参数；分类点击触发请求 |
| 构建 | `npm run build` | vue-tsc ＋ vite 成功 |

## 6. 验证命令

```powershell
cd "d:\Trae CN\myproject\Dev\DPS\src"
D:\Python\python.exe -m pytest tests/test_template_filter_v2_16.py -q -o addopts=""

cd "d:\Trae CN\myproject\Dev\OpenBase"
D:\Python\python.exe -m pytest tests/test_dps_proxy.py tests/test_dps_proxy_v1410.py -q -o addopts=""

cd "d:\Trae CN\myproject\Dev\OpenBase\openbase-ui"
node node_modules/vitest/vitest.mjs run tests/dps-template-filter-v180.spec.ts tests/api-dps-v1410.spec.ts
npm run build
```

## 7. 文档交付

| 文档 | 路径 |
|---|---|
| 需求 / 矩阵 / 评审 | `doc/requirements/OpenBase-开发需求文档-v1.8.0.md` 等（与 A1/A2 共用 v1.8.0） |
| 设计文档 | `doc/design/OpenBase-A7模板服务端筛选-设计文档-v1.0.0.md` |
| 开发 / 测试 / 部署 | `doc/development/…-v1.8.0.md`、`doc/test/…-v1.8.0.md`、`doc/release/…-v1.8.0.md` |
| 设计回填 | `doc/design/OpenBase-DPS统一前端页面功能设计-v1.0.0.md` 内容版本 v2.6.0 → v2.7.0 |

## 8. 风险与决策

| 风险 | 处置 |
|---|---|
| LIKE 通配符注入导致全表命中 | 转义 `%`/`_`/`\` ＋ `ESCAPE`；参数化绑定 |
| 上游未同步升级时前端传参被忽略 | 参数未知时上游 FastAPI 忽略，前端仍显示全量（降级不报错），文档注明依赖 DPS ≥2.16.0 |
| 分类点击每次请求 | 仅点击/清除触发，输入关键字仍由「查询」按钮触发 |
| 提交夹带既有改动 | 仅 stage 本任务文件 |
