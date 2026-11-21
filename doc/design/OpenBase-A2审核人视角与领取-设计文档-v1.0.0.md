# OpenBase-A2审核人视角与领取-设计文档-v1.0.0

| 项 | 内容 |
|---|---|
| 文档类型 | 后端＋前端详细设计 |
| 版本 | v1.0.0 |
| 状态 | [Implemented]（2026-11-21） |
| 适用范围 | DPS 标注队列/领取；OpenBase `dps-proxy`；审核收件箱（`?view=review`） |
| 上游依据 | 《OpenBase 开发需求文档 v1.8.0》FR-180-03/04；《DPS 统一前端页面功能设计》v2.7.0 §9 A2 |
| 作者 | 后端工程师（BE）＋前端工程师（FD） |
| 日期 | 2026-11-21 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 首版：reviewer/level 过滤、幂等领取、权限动作覆盖与前端收件箱接入 | BE/FD |

## 1. 设计目标

- 审核人可按「我的 / 级数」查看队列，并在开始审核前锁定任务。
- 身份只由服务端按 `X-User-ID` 解析，前端不构造身份头。
- 并领取不双写，重复领取幂等。

## 2. 契约

### 2.1 列表扩展

`GET /annotations?reviewer=me&level=2`

- `reviewer=me` → `get_user_id()`；无身份 401；其他值按 `reviewer_id` 精确匹配。
- `level` 0~5（FastAPI `ge/le` 校验）。
- 列缺失且请求对应过滤 → 空页（`total=0`），不抛错。
- 行内新增 `reviewer_id`（列存在时）。

### 2.2 领取

`POST /annotations/{annotation_id}/claim`，body 可选（忽略）。

| 场景 | 结果 |
|---|---|
| 成功 | 200 `{annotation_id,reviewer,claimed:true,already:false}` |
| 本人重复 | 200 `already:true` |
| 不存在/跨租户 | 404 |
| 非 pending | 409 |
| 他人已领 | 409 |
| 无身份 | 401 |
| 审核列未迁移 | 409 |

## 3. 并发与状态机

```text
读取 (status, reviewer_id)
  ├─ 非 pending → 409
  ├─ owner 为他人 → 409
  ├─ owner 为本人 → 200 already
  └─ 未领取 → UPDATE ... WHERE id=? AND (reviewer_id IS NULL OR reviewer_id=本人)
                ├─ affected=1 → 200
                └─ affected=0 → 重读；本人则 already，否则 409
```

- 领取只写 `reviewer_id`，不改变 `review_status`/`review_level`；审核时仍写实际操作人。
- 不做跨库 `FOR UPDATE`；以条件 UPDATE 的影响行数作为并发裁决。

## 4. 权限

- `ENDPOINT_ACTION_OVERRIDES[("POST","/claim")] = "update"`（对既有记录的更新，非 create）。
- 补断言：`/claim` 后缀仅标注领取使用，避免误伤其他业务面。

## 5. 前端

| 项 | 行为 |
|---|---|
| 只看我的 | `reviewer=me` 回写 URL，深链/刷新保持 |
| 级数筛选 | 0~5，空值不过滤 |
| 审核人列 | 未领取 / 我 / 他人 ID 三态 |
| 领取按钮 | `pending` 可见；未领取可点；本人显示「已领取」；他人禁用「他人已领取」 |
| 成功后 | 更新当前任务归属并刷新队列（统计同步刷新） |

## 6. 测试与验证

- `tests/test_annotation_claim_v2_16.py`：6 passed（过滤、成功/幂等/冲突/非 pending/缺失/缺列、路由 401/404/409）。
- `tests/test_v2_9_1_permission_mapping.py`：通过（含 `/claim` 唯一性）。
- `tests/test_dps_proxy.py`（claim 2 条）：通过。
- `tests/dps-annotation-claim-v180.spec.ts`：3 passed。
- `npm run build`：成功。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| 并发双领 | 条件 UPDATE ＋影响行数裁决 |
| 前端伪造身份 | 只传 `me`；代理注入身份头 |
| 缺列 | 过滤空页；claim 409 明确文案 |
| 回滚 | 回退 claim 路由与前端按钮；领取字段为既有列，无迁移 |
