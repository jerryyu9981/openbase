# OpenBase-DevLogReport-v1.7.0

| 项 | 内容 |
|---|---|
| 版本 | v1.7.0（前端） |
| 状态 | [Implemented] |
| 日期 | 2026-11-21 |
| 需求基线 | 《OpenBase-开发需求文档-v1.7.0》v1.0.0（RT-170-001~010） |
| 设计依据 | 《OpenBase-A3批量审核-设计文档-v1.0.0》 |
| 作者 | 开发（AD）／前端（FD） |

## 修订历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0.0 | 2026-11-21 | A3 批量审核选择约束、统一意见、逐条结果呈现 |

## 1. 交付内容

| # | 文件 | 变更 |
|:-:|---|---|
| 1 | `openbase-ui/src/core/api/dps.ts` | `DpsBatchReviewItemResult` 增加 `review`（level/required/finalized）与索引签名 |
| 2 | `openbase-ui/src/modules/portrait/annotation/batchReview.ts` | 新增：逐条结果映射、汇总文案（纯函数） |
| 3 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue` | 勾选列仅 pending；`runBatch` 写入逐条结果；新增「批量复核结果」弹窗 |
| 4 | `openbase-ui/package.json` | 1.6.0 → 1.7.0 |
| 5 | `openbase-ui/tests/dps-batch-review-v170.spec.ts` | 新增 6 条单元用例 |

后端与 DPS **无代码变更**（A3 复用既有 `POST /portrait/annotations/batch-review`）。

## 2. 关键实现

### 选择约束
- 选择列 `:selectable="isRowSelectable"`，仅 `review_status === 'pending'` 可勾选；`reserve-selection` 保持跨页选择。
- 批量完成、切换视图、刷新队列均清空选择。

### 批量动作
- 通过：`ElMessageBox.confirm` 提示末级/非末级差异。
- 驳回：`ElMessageBox.prompt` 必填统一意见，逐条写入 `comment`。
- 请求体：`{items:[{annotation_id,status,current_status:'pending',comment?}]}`。

### 结果呈现
- 新增弹窗 `annotation-batch-result-dialog`：
  - 顶部 summary alert（有失败为 warning）；
  - 表格列：标注 ID / 结果标签 / 详情；
  - 空态：「上游未返回逐条结果」。
- 映射规则见设计文档 §4；失败条目不阻断，队列随后刷新。

## 3. 与设计的差异

无。实现与《OpenBase-A3批量审核-设计文档-v1.0.0》一致。

## 4. 自测

- `dps-batch-review-v170.spec.ts`：6 passed；
- 定向前端：`api-dps-v1410`（22）＋`dps-backend-v160`（1）＋新增（6）＝29 passed；
- `npm run build`：成功；
- `tests/test_dps_proxy.py`：44 passed。
