# Tasks：A3 批量审核（OpenBase v1.7.0）

| 项 | 内容 |
|---|---|
| 需求基线 | 《OpenBase-开发需求文档-v1.7.0》 |
| 设计依据 | 《OpenBase-A3批量审核-设计文档-v1.0.0》 |
| 状态 | [Done] 2026-11-21 |

## T1 类型与结果映射

- [x] T1.1 `dps.ts` `DpsBatchReviewItemResult` 增加 `review` 字段与索引签名
- [x] T1.2 新增 `annotation/batchReview.ts`（逐条结果映射＋汇总文案）
- [x] T1.3 新增 `tests/dps-batch-review-v170.spec.ts`（6 条，覆盖末级/非末级/驳回/失败/缺 ID/空 items）

## T2 工作台接入

- [x] T2.1 勾选列 `:selectable` 仅允许 pending 行
- [x] T2.2 `runBatch` 写入逐条结果并打开结果弹窗
- [x] T2.3 结果弹窗：汇总 alert ＋ 逐条表格（成功/失败标签、详情、空态）
- [x] T2.4 批量完成/切换视图清空选择

## T3 验证

- [x] T3.1 定向 vitest：`dps-batch-review-v170`＋`api-dps-v1410`＋`dps-backend-v160`（29 passed）
- [x] T3.2 `npm run build`（vue-tsc ＋ vite，成功）
- [x] T3.3 代理回归：`tests/test_dps_proxy.py`（44 passed）

## T4 文档与留痕

- [x] T4.1 需求文档/追溯矩阵/评审记录 v1.7.0
- [x] T4.2 A3 设计文档 v1.0.0
- [x] T4.3 DevLog/测试/部署报告 v1.7.0
- [x] T4.4 设计文档回填 v2.6.0（§9 A3、§14.3 回填、修订历史）
- [x] T4.5 仅 stage 本任务文件，提交并推送 origin/backup/github
