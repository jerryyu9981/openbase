# OpenBase-A4 标注详情接口-设计文档-v1.0.0

| 项 | 内容 |
|---|---|
| 文档类型 | 详细设计（跨仓：DPS → OpenBase → 前端） |
| 版本 | v1.0.0 |
| 状态 | [Approved]（2026-11-20，随 Spec 批准） |
| 日期 | 2026-11-20 |
| 上游依据 | 《OpenBase-开发需求文档-v1.6.0》v1.0.0；DPS《开发需求文档-v2.15.0》v1.0.0 |
| 作者 | 架构组（AA）／前端（FA） |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | 首版：A4 端到端设计、字段映射、错误语义与回退 | 架构组 |

---

## 1. 端到端时序

```
前端 DpsAnnotationWorkbenchView（审核收件箱）
   │  选中队列行
   ├─→ GET /api/v1/dps-proxy/annotations/{id}        （OpenBase JWT）
   │        └─ 身份头注入 → GET {DPS}/api/v2/portrait/annotations/{id}
   │                └─ AnnotationTemplateEngine.get_annotation_detail
   │                        └─ SELECT annotation ⟕ annotation_template ⟕ profile
   ├─→ GET /dps-proxy/portraits/{person_id}           （画像快照，可失败）
   ├─→ GET /dps-proxy/annotation-templates/{code}/field-mapping（映射，可失败）
   └─→ GET /dps-proxy/annotations/{id}/review-log     （留痕，可失败）
   ↓ Promise.allSettled 合并渲染
```

## 2. DPS 设计

### 2.1 数据访问

- 主表 `annotation a`，`LEFT JOIN annotation_template t`，`LEFT JOIN profile p`。
- 列探测 `_annotation_columns()` 决定可选列：
  - `payload`：存在则解析为 `fields`；缺失 → `{}`。
  - `evidence_source` / `reviewer_id` / `review_comment` / `updated_at`：存在才 SELECT。
  - `review_level/review_levels_required`：同时存在才启用进度。
  - `template_id`：缺失则跳过模板 JOIN，模板三字段为 `NULL`。
  - `review_status`：缺失时输出 `NULL`。
- 租户：`tenant_id` 非空且列存在 → `AND a.tenant_id = ?`。

### 2.2 方法签名

```python
async def get_annotation_detail(
    self, annotation_id: str, tenant_id: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

### 2.3 路由

`@router.get("/portrait/annotations/{annotation_id}")`，返回 `data.annotation`；`None` → 404。

## 3. OpenBase 代理设计

| 项 | 设计 |
|---|---|
| 路径 | `/api/v1/dps-proxy/annotations/{annotation_id}` |
| 上游 | `/api/v2/portrait/annotations/{quote(id, safe="")}` |
| 注册顺序 | `dps_annotations_list` 之后；`/annotations/export` 已在前 |
| 错误 | `_adapt_response` 原样透传状态码与错误体 |
| 权限 | 仅 JWT 门禁＋身份头，不做权限判定 |

## 4. 前端设计

| 项 | 设计 |
|---|---|
| API | `getAnnotationDetail(id)` → `GET /dps-proxy/annotations/{encoded}` |
| 类型 | `DpsAnnotationDetailAnnotation` 继承队列行，补充 reviewer/comment/evidence/updated_at/structured |
| 状态 | `reviewDetail: Ref<DpsAnnotationDetail \| null>` |
| 合并 | `reviewTask = reviewDetail?.annotation ?? currentTask` |
| 字段表 | `reviewFields` 读取 `reviewTask.fields` |
| 描述区 | 证据来源取 `reviewTask.evidence_source`；有审核人/意见时显示「审核结论」 |
| 回退 | 详情请求失败 → `reviewDetail=null`，其余请求继续 |

## 5. 错误与降级

| 场景 | DPS | 代理 | 前端 |
|---|---|---|---|
| 标注不存在 | 404 | 404 透传 | 回退队列摘要 |
| 跨租户 | 404 | 404 透传 | 回退队列摘要 |
| DPS 未升级（无路由） | 404/405 | 404/405 | 回退队列摘要 |
| 上游 5xx/超时 | 5xx | 502/503 | 回退队列摘要，其余面板可用 |

## 6. 测试设计

| 层 | 用例 |
|---|---|
| DPS 引擎/路由 | rich 全字段、404、legacy 降级、租户不匹配 |
| OpenBase 代理 | 路由注册/顺序、路径编码与头/参数、404 保真 |
| 前端 | API 路径与方法、详情字段、既有 DPS UI 回归 |

## 7. 部署顺序

1. DPS 2.15.0 上线并验证 `GET /api/v2/portrait/annotations/{id}`。
2. OpenBase 1.6.0 上线，验证代理。
3. 前端 1.6.0 发布；未升级代理时自动回退，无阻断。

## 8. 回滚

- DPS 回滚至 2.14.0：详情 404 → 前端回退，审核不受阻。
- OpenBase 回滚至 1.5.0：前端详情 404 → 回退。
- 前端回滚至 1.5.0：审核使用队列摘要，功能可用。
