# Spec：A4 标注详情接口（DPS v2.15.0 ＋ OpenBase v1.6.0）

| 项 | 内容 |
|---|---|
| 状态 | **[Draft]** 待人工批准 |
| 日期 | 2026-11-20 |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》v2.4.0 §9 A4／§14.3 P0；用户 2026-11-20 指令「先处理优先级最高的 A4 标注详情接口」 |
| 版本冻结 | DPS `2.15.0`（`src/__init__.py`）；OpenBase 后端 `1.6.0`（`openbase/__init__.py`）；前端 `1.6.0`（`openbase-ui/package.json`） |
| 交付链 | DPS 上游端点 → OpenBase `dps-proxy` 透传 → 前端审核收件箱接入 |

## 1. 目标与范围

**目标**：补齐 P0 缺口 A4——审核/复核时一次拿到标注全量详情（证据、字段、审核进度、审核人/意见、时间戳、主体与模板归属），替代当前「队列摘要 ＋ 画像详情」拼接。

**范围内**
1. DPS 新增 `GET /api/v2/portrait/annotations/{annotation_id}`。
2. OpenBase 新增代理 `GET /api/v1/dps-proxy/annotations/{annotation_id}`。
3. 前端 `dpsApi.getAnnotationDetail()` ＋ 审核对照面板接入，保留 404 回退。
4. 两仓测试、版本文档、DevLog/测试/部署报告。

**范围外**
- 不新增 A1/A2/A3/A5/A7/A8/A13 能力。
- 不改变审核状态机、标签联动、RBAC 与租户中间件语义。
- 不新增页面路由、不改导航 IA。

## 2. 源码事实（已核对）

| # | 事实 | 位置 |
|:-:|---|---|
| F1 | 标注队列仅返回摘要：`id/profile_id/person_id/person_name/content/payload/review_status/author_id/created_at/template code/name/template_code/review_level(s)`，不含 reviewer/comment/evidence 的完整详情 | `DPS src/engines/annotation_template_engine.py` `query_annotations`（L893-973） |
| F2 | 已有 `GET /portrait/annotations`、`POST /annotations/{id}/review`、`GET /annotations/{id}/review-log`，无详情 GET | `DPS src/rest_api/routes/routes_profiles.py` L1220/L1549/L1570 |
| F3 | 标注表实际列：`id/profile_id/author_id/content/annotation_type/template_id/payload/review_status/reviewer_id/review_comment/created_at/updated_at`，迁移后追加 `evidence_source/review_level/review_levels_required/tenant_id` | `DPS src/ddl/schema_portrait.py`、`src/engines/annotation_template_engine.py` `_annotation_columns` |
| F4 | OpenBase 已代理 `/annotations`、`/annotations/export`、`/annotations/batch-review`、`/annotations/{id}/review`、`/annotations/{id}/review-log`；`quote` 已导入 | `openbase/modules/dps_proxy/__init__.py` L950/L1991/L2030/L2054/L2077 |
| F5 | 前端审核对照现取 `getPortrait + getAnnotationFieldMapping + getAnnotationReviewLog`，字段来自队列行 `row.fields` | `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue` `loadReviewContext`（L1243）/`reviewFields`（L1203） |
| F6 | 前端已有 `submitReview/getAnnotationReviewLog/listAnnotations` 封装与 404 回退习惯 | `openbase-ui/src/core/api/dps.ts` L1546-1599；`DpsAnnotationWorkbenchView.vue` L1258-1276 |

## 3. 接口契约

### 3.1 DPS：`GET /api/v2/portrait/annotations/{annotation_id}`

- 鉴权：沿用现有路由中间件（租户/权限），不新增判定。
- 查询参数：无（可选 Header `X-Tenant-ID`，存在且表有 `tenant_id` 列时追加过滤）。
- 200 响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "annotation": {
      "id": "a-1",
      "profile_id": "prof-1",
      "person_id": "PERSON0000001",
      "person_name": "张三",
      "annotation_template": "ann-assess-v1",
      "annotation_template_name": "入矫评估标注",
      "profile_template_code": "cc-persona-v1",
      "annotation_type": "structured",
      "content": "…",
      "fields": {"behavior": "良好"},
      "evidence_source": "WS-1",
      "review_status": "pending",
      "review_level": 1,
      "review_levels_required": 3,
      "author_id": "u1",
      "reviewer_id": "u2",
      "review_comment": "证据充分",
      "created_at": "2026-11-20 10:00:00",
      "updated_at": "2026-11-20 11:00:00",
      "structured": true,
      "evidence_source_persisted": true,
      "review_progress_persisted": true
    }
  }
}
```

- 404：`{"detail": "标注记录不存在: {id}"}`（与 `review-log` 一致）。
- 兼容：`payload` 列缺失（存量库）→ `fields={}`、`structured=false`，不抛错；缺 `evidence_source`/进度列 → 对应值 `None`/`0`/`1` 且 `*_persisted=false`。
- 租户隔离：`tenant_id` 非空且列存在时 `AND a.tenant_id = ?`，不匹配按 404 处理（不泄露存在性）。

### 3.2 OpenBase 代理：`GET /api/v1/dps-proxy/annotations/{annotation_id}`

- 身份头沿用 `_build_identity_headers`；上游路径 `/api/v2/portrait/annotations/{id}`。
- 状态码与错误体语义保真（`_forward`/`_adapt_response` 既有逻辑）。
- `annotation_id` 经 `quote(..., safe="")` 编码。
- 路由注册位置：`dps_annotations_list` 之后；静态 `/annotations/export` 已在前，动态段不会抢占。

### 3.3 前端

- `DpsAnnotationDetail`：`{ annotation: DpsAnnotationRow & { profile_id?, reviewer_id?, review_comment?, evidence_source?, updated_at?, structured? } }`
- `dpsApi.getAnnotationDetail(annotationId)` → `GET /dps-proxy/annotations/{encoded}`。
- 审核面板：`loadReviewContext` 并行增加详情请求；详情成功时字段/证据/审核人/意见以详情为准，失败（含 404）保持现有行数据，不阻断画像/映射/留痕加载。

## 4. 实现清单（精确到文件/函数）

### DPS
1. `src/engines/annotation_template_engine.py`
   - 新增 `async def get_annotation_detail(self, annotation_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]`：
     - 复用 `_annotation_columns()` 探测列；动态拼 SELECT 可空列；
     - `LEFT JOIN annotation_template t ON CAST(t.id AS TEXT)=CAST(a.template_id AS TEXT)`、`LEFT JOIN profile p ON CAST(p.id AS TEXT)=CAST(a.profile_id AS TEXT)`；
     - `WHERE a.id = ?`（＋租户条件）；无行返回 `None`；
     - `payload` 经 `_load` 解析为 `fields`（非 dict → `{}`）。
2. `src/rest_api/routes/routes_profiles.py`
   - 新增 `@router.get("/portrait/annotations/{annotation_id}") async def api_annotation_detail(annotation_id, x_org_id=Header(None), x_tenant_id=Header(None))`；
   - `AnnotationTemplateEngine(db=global_db).get_annotation_detail(...)`；`None` → `HTTPException(404, f"标注记录不存在: {annotation_id}")`；
   - 返回 `{"code":200,"message":"success","data":{"annotation": detail}}`。
3. `src/__init__.py`：`__version__ = "2.15.0"`。
4. 新增 `src/tests/test_v2_15_annotation_detail.py`（真实 SQLite，不 mock 引擎）：
   - 详情含字段/模板/主体/证据/审核进度/审核人意见；
   - 不存在 → `None` ＋ 路由 404；
   - legacy 库（无 payload/evidence/进度列）→ `fields={}`、`structured=false`、不抛错；
   - 租户不匹配 → `None`。

### OpenBase 后端
5. `openbase/modules/dps_proxy/__init__.py`：新增 `dps_annotation_detail` 路由（`/annotations/{annotation_id}`，GET）。
6. `openbase/__init__.py`：`__version__ = "1.6.0"`。
7. 新增 `tests/test_a4_annotation_detail_v160.py`：路由注册与顺序、路径/身份头转发、上游 404 语义保真（monkeypatch `_forward`）。

### 前端
8. `openbase-ui/src/core/api/dps.ts`：新增 `DpsAnnotationDetail` 类型与 `getAnnotationDetail`。
9. `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue`：
   - 新增 `reviewDetail` 状态；
   - `loadReviewContext` 并行请求详情并容错；
   - `reviewFields` 优先使用详情字段；
   - 审核对照展示「审核人／审核意见」（有值才显示）。
10. `openbase-ui/package.json` → `1.6.0`。
11. 新增 `openbase-ui/tests/dps-backend-v160.spec.ts`：方法路径、参数、详情字段透传。

## 5. 验证步骤

```powershell
# DPS 定向 + 全量
D:\Python\python.exe -m pytest src/tests/test_v2_15_annotation_detail.py -q --no-cov
D:\Python\python.exe -m pytest src/tests -q --no-cov
D:\Python\python.exe -m ruff check src

# OpenBase 定向 + 全量
D:\Python\python.exe -m pytest tests/test_a4_annotation_detail_v160.py -q -o addopts=""
D:\Python\python.exe -m pytest tests -q -o addopts=""
D:\Python\python.exe -m ruff check openbase tests

# 前端
cd openbase-ui
node node_modules/vitest/vitest.mjs run tests/dps-backend-v160.spec.ts tests/dps-ui-v1410.spec.ts
npm run build
```

通过标准：新增用例全绿；两仓全量 0 failed；前端 build 成功；既有标注队列/复核/留痕用例零回归。

## 6. 文档交付（批准后随实现产出）

| 仓 | 文档 |
|---|---|
| DPS | `doc/requirements/DPS-开发需求文档-v2.15.0.md`、`DPS-需求追溯矩阵-v2.15.0.md`、`DPS-需求评审记录-v2.15.0.md`、`doc/development/DPS-DevLogReport-v2.15.0.md`、`doc/test/DPS-测试报告-v2.15.0.md`、`doc/release/DPS-部署与运维报告-v2.15.0.md` |
| OpenBase | `doc/requirements/OpenBase-开发需求文档-v1.6.0.md`、`OpenBase-需求追溯矩阵-v1.6.0.md`、`OpenBase-需求评审记录-v1.6.0.md`、`doc/design/OpenBase-A4标注详情接口-设计文档-v1.0.0.md`、`doc/development/OpenBase-DevLogReport-v1.6.0.md`、`doc/test/OpenBase-测试报告-v1.6.0.md`、`doc/release/OpenBase-部署与运维报告-v1.6.0.md` |
| OpenBase | 回填 `doc/design/OpenBase-DPS统一前端页面功能设计-v1.0.0.md`（内容版本 v2.5.0：A4 已交付） |

## 7. 风险与决策

| 风险 | 处置 |
|---|---|
| 存量库缺列导致 500 | 列探测 ＋ 动态 SELECT ＋ 空值兜底（同 `query_annotations` 策略） |
| 动态路由抢占静态路径 | `/annotations/export` 已在动态段之前注册；详情路由仅单段动态，不与 `/{id}/review-log` 冲突 |
| DPS 未升级（404） | 前端保持现有队列摘要渲染，不阻断审核 |
| 跨租户越权读 | 上游按 `X-Tenant-ID` 过滤，不匹配返回 404 |
| 提交夹带 | 仅 stage 本 spec 涉及文件（两仓），不碰既有未提交改动 |

## 8. 批准项

请确认：
1. 版本冻结 DPS 2.15.0／OpenBase 1.6.0。
2. 契约字段集与 `data.annotation` 包络（与队列行同名字段保持一致）。
3. 前端仅增强审核对照（不改布局与路由），详情失败保持回退。
