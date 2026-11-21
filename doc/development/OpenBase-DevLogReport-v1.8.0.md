# OpenBase-DevLogReport-v1.8.0

## 文档信息

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-DEVLOG-v1.8.0 |
| 版本 | v1.0.0 |
| 状态 | [Implemented]（2026-11-21） |
| 对应需求 | 《OpenBase-开发需求文档-v1.8.0》 |
| 版本冻结 | DPS 2.16.0；OpenBase 1.7.0；openbase-ui 1.8.0 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 后端/前端工程师 | 首版：A7/A1/A2 实现与 A5/A8/A13 验证 |

## 1. 交付摘要

| 项 | DPS v2.16.0 | OpenBase v1.7.0 | 前端 v1.8.0 |
|---|---|---|---|
| A7 模板服务端筛选 | `list_templates` ＋ Query | 透传＋docstring | `load()` 服务端参数、删除本地过滤 |
| A1 队列统计 | `annotation_stats` ＋ `GET /annotations/stats` | `GET /annotations/stats` | 队列状态 KPI |
| A2 审核人/领取 | reviewer/level ＋ `POST /{id}/claim` ＋ 权限覆盖 | `POST /{id}/claim` | 只看我的/级数/归属/领取 |
| A5/A8/A13 | — | — | 源码核对＋既有用例验证，未改码 |

## 2. 变更文件

### DPS（2.15.0 → 2.16.0）
- `src/engines/template_engine.py`：LIKE 转义工具＋3 个过滤参数。
- `src/engines/annotation_template_engine.py`：`annotation_stats`、`claim_annotation`、`query_annotations` 扩展。
- `src/rest_api/routes/routes_profiles.py`：模板三参数、统计路由、reviewer/level、claim 路由。
- `src/middleware/permission_middleware.py`：`("POST","/claim") → update`。
- `src/__init__.py`、`src/config.py`、`src/mcp_server/constants.py`：版本 2.16.0。
- 测试：`tests/test_template_filter_v2_16.py`、`tests/test_annotation_stats_v2_16.py`、`tests/test_annotation_claim_v2_16.py`、`tests/test_v2_9_1_permission_mapping.py`。

### OpenBase（1.6.0 → 1.7.0）
- `openbase/modules/dps_proxy/__init__.py`：`dps_annotations_stats`、`dps_annotation_claim`、docstring 更新。
- `openbase/__init__.py`：版本 1.7.0。
- 测试：`tests/test_dps_proxy.py` 新增 5 条。

### 前端（1.7.0 → 1.8.0）
- `src/core/api/dps.ts`：类型与 3 个方法。
- `src/modules/portrait/pages/DpsTemplateListView.vue`：服务端筛选。
- `src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue`：KPI、筛选、归属列、领取。
- `package.json`：1.8.0。
- 测试：`tests/dps-template-filter-v180.spec.ts`、`dps-annotation-stats-v180.spec.ts`、`dps-annotation-claim-v180.spec.ts`。

## 3. 关键实现说明

1. **A7**：`LOWER(name)/LOWER(code)` ＋ `_escape_like` ＋ `ESCAPE '\'`，保证跨库一致与通配符安全。
2. **A1**：统计与列表复用同一 `base_sql`；排序在 Python 侧完成；静态段先注册。
3. **A2**：`reviewer=me` 由 `get_user_id()` 解析；claim 用条件 UPDATE 影响行数裁决并发；`/claim` 权限动作为 update。
4. **A5/A8/A13**：仅补验证证据（草稿键、health.ts、dry-run 抽屉），未新增代码。

## 4. 自检

- 仅 stage 本任务文件；`git diff --cached --stat` 核对。
- 无数据库迁移；无新增权限点；无路由增删（仅新增端点）。
- 文档同步：需求/矩阵/评审、三份设计、设计总文档 §9/§12/§14.9、测试与部署报告。
