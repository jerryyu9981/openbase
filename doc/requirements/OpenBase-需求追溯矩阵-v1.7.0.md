# OpenBase-需求追溯矩阵-v1.7.0

| 需求编号 | 需求摘要 | 设计/实现 | 用例 | 验收 |
|---|---|---|---|---|
| RT-170-001 | 仅 pending 可勾选 | `isRowSelectable`（Workbench selection 列） | 代码审查＋构建 | AC-01 |
| RT-170-002 | 跨页选择保持 | `reserve-selection` ＋ `useDpsListView.selection` | 既有 `dps-list-view` | AC-01 |
| RT-170-003 | 批量通过二次确认 | `batchApprove`／`runBatch` | `dps-batch-review-v170.spec.ts` | AC-02 |
| RT-170-004 | 批量驳回统一意见 | `batchReject`（必填校验） | 同上 | AC-02 |
| RT-170-005 | 汇总文案 | `batchReviewSummary` | `dps-batch-review-v170.spec.ts` | AC-02 |
| RT-170-006 | 末级/非末级结果 | `toBatchReviewRow` | 同上 | AC-02 |
| RT-170-007 | 失败原因与状态码 | `toBatchReviewRow`（error/status） | 同上 | AC-02 |
| RT-170-008 | 结果弹窗 | `annotation-batch-result-dialog` | 前端构建 | AC-02 |
| RT-170-009 | 类型补全 | `DpsBatchReviewItemResult.review` | `vue-tsc --noEmit` | AC-03 |
| RT-170-010 | 零回归 | 代理与既有前端 spec | `tests/test_dps_proxy.py`（44 passed） | AC-03 |
