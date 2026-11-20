# OpenBase-A3批量审核-设计文档-v1.0.0

| 项 | 内容 |
|---|---|
| 文档类型 | UI/前端详细设计 |
| 版本 | v1.0.0 |
| 状态 | [Implemented]（2026-11-21） |
| 适用范围 | `openbase-ui/src/modules/portrait/**` 审核收件箱（`?view=review`） |
| 上游依据 | 《OpenBase-开发需求文档-v1.7.0》；《OpenBase-DPS 统一前端页面功能设计》v2.5.0 §9 A3／§11 AC-AN-7、AC-RV-3／§14.3 |
| 作者 | 前端工程师（FD） |
| 日期 | 2026-11-21 |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 首版：A3 批量选择、统一意见、逐条结果呈现与失败隔离 | FD |

## 1. 设计目标

在不改后端契约的前提下，把既有批量端点（逐条 `comment`、逐条结果）接入审核收件箱，满足：

1. 只对待审核记录批量操作；
2. 批量通过/驳回有明确确认与统一意见；
3. 结果逐条可见，失败不阻断；
4. 与单条复核的级别语义一致。

## 2. 组件与状态

| 状态 | 类型 | 说明 |
|---|---|---|
| `selection` | `string[]` | 来自 `useDpsListView`，跨页按 `row-key=id` 保留 |
| `batchLoading` | `boolean` | 批量请求进行中，禁用按钮 |
| `batchResultVisible` | `boolean` | 结果弹窗开关 |
| `batchResultRows` | `BatchReviewRow[]` | 逐条结果行（`annotationId/ok/resultLabel/detail`） |
| `batchResultSummary` | `string` | 汇总文案 |
| `batchResultFailed` | `boolean` | 是否含失败（决定 alert 样式） |

## 3. 交互流程

```text
勾选（仅 pending）
  → 批量操作条显示「已选 N 条」
  → 批量通过：二次确认（提示末级/非末级）
     批量驳回：弹窗必填统一意见
  → POST /dps-proxy/annotations/batch-review
      body: {items:[{annotation_id,status,current_status:"pending",comment?}]}
  → 结果弹窗（汇总 alert + 逐条表格）
  → 清空选择 + 刷新队列
```

## 4. 结果映射（`annotation/batchReview.ts`）

| 条件 | `resultLabel` | `detail` |
|---|---|---|
| `ok=false` | 失败 | `{上游原因}（{status}）` |
| `ok=true` 且 `action=rejected` | 成功 | `已驳回` |
| `ok=true` 且 `review.finalized=true` | 成功 | `终审通过（第 k/N 级）` |
| `ok=true` 且 `review.finalized=false` | 成功 | `已通过第 k/N 级，待第 k+1 级` |
| `ok=true` 且无 `review` | 成功 | `status` 原文或 `已通过` |

- `annotation_id` 缺失显示 `(未知)`。
- `items` 缺失/非数组 → 返回空数组，弹窗空态「上游未返回逐条结果」，汇总计数仍以 `total/succeeded/failed` 展示。

## 5. 失败与边界

| 场景 | 处置 |
|---|---|
| 单条 404/409/500 | 该条标记失败，其余条目继续；原因与状态码入表格 |
| 整批网络/400 错误 | `pageError` 提示，不打开结果弹窗，选择保留供重试 |
| 非 pending 行 | 勾选不可用；后端仍为最终裁决 |
| 跨页残留选择 | 批量完成/切换视图/刷新队列清空 |
| 旧上游无 `review` | 成功行退化为状态原文，不推测级数 |

## 6. 与单条复核的一致性

- 级别口径复用 `reviewRequired/reviewLevel`；批量结果直接采用上游 `review`。
- 驳回意见语义一致：统一意见写入每条 `comment`。
- 审核留痕、标签联动仍由后端逐条执行，前端不重复计算。

## 7. 测试设计

| 层 | 用例 |
|---|---|
| 单元 | `tests/dps-batch-review-v170.spec.ts`：末级、非末级、驳回、失败、缺 ID、空 items |
| API | `tests/api-dps-v1410.spec.ts`：批量端点路径与请求体（既有） |
| 构建 | `npm run build`（`vue-tsc --noEmit`＋`vite build`） |
| 回归 | `tests/test_dps_proxy.py`（代理透传，44 passed） |

## 8. 前端禁则遵循

- 不直连 DPS，全部走 `/api/v1/dps-proxy/*`；
- 不构造身份头、不做权限判定；
- 不假设 `tag_bindings`/`review` 之外的内部结构。
