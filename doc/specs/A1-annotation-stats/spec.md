# Spec：A1 标注队列统计（DPS 2.16.0 / OpenBase 1.7.0 / 前端 1.8.0）

| 项 | 内容 |
|---|---|
| 状态 | **[Implemented]**（2026-11-21 已批准并交付） |
| 日期 | 2026-11-21 |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》v2.6.0 §9 A1（L337）、§12 首页 KPI（L527）；用户 2026-11-21 指令 |
| 版本冻结 | DPS `2.15.0 → 2.16.0`；OpenBase 后端 `1.6.0 → 1.7.0`；前端 `1.7.0 → 1.8.0` |
| 交付链 | DPS `GET /api/v2/portrait/annotations/stats` → OpenBase `GET /api/v1/dps-proxy/annotations/stats` → 标注工作台队列概览 |

## 1. 目标与范围

**目标**：提供标注队列聚合计数（按模板 / 状态 / 级数 / 审核人），供工作台队列头部与首页 KPI 使用，避免前端对当前页数据自行汇总造成口径错误。

**范围内**
1. DPS 引擎新增 `annotation_stats`（参数化聚合 ＋ 租户过滤）。
2. DPS 新增只读端点 `GET /portrait/annotations/stats?group_by=...`。
3. OpenBase 代理新增同名 GET 端点（静态段必须先于 `/annotations/{annotation_id}` 注册）。
4. 前端 `getAnnotationStats` ＋ 工作台队列头部 KPI（按状态）。
5. 测试、版本、文档与设计回填。

**范围外**
- 不做时间区间/趋势统计；不落统计缓存；不改审核状态机。
- 不新增权限点（沿用 `annotation_template:read`，由 `SUBPATH_RESOURCE_MAP[("portrait","annotations")]` 归一）。

## 2. 源码事实（已核对）

| # | 事实 | 位置 |
|:-:|---|---|
| F1 | 队列查询 `query_annotations` 已建立 `annotation a LEFT JOIN annotation_template t LEFT JOIN profile p` 与租户列守卫 | `DPS/src/engines/annotation_template_engine.py` L893-973 |
| F2 | 列集合由 `_annotation_columns()` 提供，`review_level/review_levels_required/reviewer_id` 可能缺失（存量库） | 同上 L944、L1004、L1110 |
| F3 | 列表路由位于 `/portrait/annotations`，详情动态段为 `/portrait/annotations/{annotation_id}`，静态 `stats` 必须先行注册 | `routes_profiles.py` L1220、L1253 |
| F4 | 代理同样存在动态段 `/annotations/{annotation_id}`，静态 `stats` 必须在其前注册 | `openbase/modules/dps_proxy/__init__.py` L1991、L2010 |
| F5 | 工作台队列卡头部已展示「共 N 条」，可按状态补充 KPI | `DpsAnnotationWorkbenchView.vue` L28-34 |
| F6 | 审核完成后 `reloadQueue()` 会刷新队列，可复用为统计刷新触发点 | 同上 L1136-1142 |

## 3. 契约

### 3.1 DPS `GET /api/v2/portrait/annotations/stats`

| 参数 | 类型 | 默认 | 语义 |
|---|---|---|---|
| `group_by` | enum | `status` | `template` / `status` / `level` / `reviewer`；其他值 → 400 |
| `annotation_template` | string 可选 | — | 过滤标注模板 code |
| `review_status` | string 可选 | — | 过滤审核状态（枚举同列表） |
| `person_id` | string 可选 | — | 过滤主体 |

响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "group_by": "status",
    "total": 12,
    "items": [
      {"key": "pending", "label": "待审核", "count": 8},
      {"key": "approved", "label": "已通过", "count": 4}
    ]
  }
}
```

- `items` 按 `count` 降序、`key` 升序；`key` 为空的 reviewer 归并为 `unassigned`，`label` 为「未指派」。
- `template` 分组 `label` 取 `annotation_template.name`（为空回落 code）。
- `level` 分组 `key` 为字符串数字（`"0"`…`"5"`），`label` 为「第 N 级」/「未开始」。
- 存量库缺 `payload` 列时与列表同口径返回空集合（`items: []`，`total: 0`）。
- 缺 `review_level` / `reviewer_id` 列时对应分组退化为单桶（`level` 全为 `0`；`reviewer` 全为 `unassigned`），`degraded: true` 如实标注。

### 3.2 OpenBase 代理

`GET /api/v1/dps-proxy/annotations/stats`，查询参数原样透传；上游错误码/消息保真。

### 3.3 前端

- `dps.ts` 新增 `DpsAnnotationStats` 类型与 `getAnnotationStats(params)`。
- 工作台队列卡头部下方增加 `data-test="annotation-stats"` 的 KPI 条：
  - 固定 `group_by=status`，展示「待审核 / 已通过 / 已驳回 / 已修改」计数；
  - 随 `templateFilter` 变化重新拉取（不带 status 过滤，保持全集口径）；
  - 请求失败仅隐藏 KPI（不阻断队列）。

## 4. 实现清单（精确到文件/函数）

1. `DPS/src/engines/annotation_template_engine.py`：新增 `async def annotation_stats(self, *, group_by, annotation_template_code=None, review_status=None, person_id=None, tenant_id=None) -> Dict[str, Any]`。
2. `DPS/src/rest_api/routes/routes_profiles.py`：在 `api_list_annotations` 与 `api_annotation_detail` 之间新增 `api_annotation_stats`。
3. `DPS/src/__init__.py` → `2.16.0`。
4. `OpenBase/openbase/modules/dps_proxy/__init__.py`：在 `dps_annotations_list` 之后、`dps_annotation_detail` 之前新增 `dps_annotations_stats`。
5. `OpenBase/openbase/__init__.py` → `1.7.0`。
6. `OpenBase/openbase-ui/src/core/api/dps.ts`：新增类型与方法。
7. `DpsAnnotationWorkbenchView.vue`：新增 `stats` 状态、`loadStats()`，在 `loadQueue()` 后与 `reloadQueue()` 时刷新；模板筛选变化时刷新。
8. `OpenBase/openbase-ui/package.json` → `1.8.0`。

## 5. 测试

| 层 | 用例 | 断言 |
|---|---|---|
| DPS 引擎 | `test_annotation_stats_v2_16.py` 6 条 | status/template/level/reviewer 分组正确；过滤条件生效；空库返回空；缺列降级 |
| DPS 路由 | 同上 3 条 | 默认 group_by=status；非法 group_by → 400；`stats` 不被 `{annotation_id}` 吞掉 |
| 代理 | `tests/test_dps_proxy_stats_v170.py` 3 条 | 路径映射正确；查询参数透传；上游 400 保真 |
| 前端 | `tests/dps-annotation-stats-v180.spec.ts` 4 条 | 请求参数；KPI 渲染；失败隐藏；刷新触发 |
| 构建 | `npm run build` | 成功 |

## 6. 验证命令

```powershell
cd "d:\Trae CN\myproject\Dev\DPS\src"
D:\Python\python.exe -m pytest tests/test_annotation_stats_v2_16.py tests/test_portrait_list_route.py -q -o addopts=""

cd "d:\Trae CN\myproject\Dev\OpenBase"
D:\Python\python.exe -m pytest tests/test_dps_proxy_stats_v170.py tests/test_dps_proxy.py -q -o addopts=""

cd "d:\Trae CN\myproject\Dev\OpenBase\openbase-ui"
node node_modules/vitest/vitest.mjs run tests/dps-annotation-stats-v180.spec.ts
npm run build
```

## 7. 文档交付

同 A7：v1.8.0 需求/矩阵/评审，`doc/design/OpenBase-A1标注队列统计-设计文档-v1.0.0.md`，开发/测试/部署 v1.8.0，设计总文档回填 v2.7.0（§9 A1、§12 KPI 依赖解除）。

## 8. 风险与决策

| 风险 | 处置 |
|---|---|
| 静态路由被动态段捕获 | DPS 与代理两侧均将 `stats` 注册在 `{annotation_id}` 之前，并各加一条路由顺序用例 |
| 存量库缺列导致 500 | 按 `_annotation_columns()` 守卫降级，响应 `degraded:true` |
| 统计与列表口径漂移 | 统计复用与列表一致的 JOIN/过滤条件，并单测对照 total |
| 频繁请求 | 仅在队列加载/筛选变化/审核后刷新，不做轮询 |
| 提交夹带既有改动 | 仅 stage 本任务文件 |
