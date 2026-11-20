# OpenBase-测试报告-v1.7.0

| 项 | 内容 |
|---|---|
| 版本 | v1.7.0（前端） |
| 状态 | [Approved] |
| 日期 | 2026-11-21 |
| 测试对象 | A3 批量审核（选择约束、统一意见、逐条结果） |
| 需求基线 | 《OpenBase-开发需求文档-v1.7.0》v1.0.0 |
| 环境 | Windows；Node/vitest 2.1.8；Python 3.12；pytest；`-o addopts=""` |

## 修订历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0.0 | 2026-11-21 | 首版：单元、前端定向、构建与代理回归结果 |

## 1. 测试范围

| 层级 | 内容 |
|---|---|
| 前端单元 | 结果映射 6 条：末级、非末级、驳回、失败、缺 ID、空 items |
| 前端 API 回归 | `batchReviewAnnotations` 请求体（既有）+ A4 详情（既有） |
| 前端构建 | `vue-tsc --noEmit` ＋ `vite build` |
| 后端回归 | 本任务不改后端；执行 DPS 代理专项 `tests/test_dps_proxy.py` |

## 2. 执行结果

| 用例/命令 | 结果 |
|---|---|
| `dps-batch-review-v170.spec.ts` | **6 passed** |
| `api-dps-v1410.spec.ts` | **22 passed** |
| `dps-backend-v160.spec.ts` | **1 passed** |
| 前端定向合计 | **29 passed**（3 spec） |
| `npm run build` | **成功**（3160 modules，dist 生成） |
| `pytest tests/test_dps_proxy.py` | **44 passed** |

## 3. 验收对照

| 验收 | 证据 | 结论 |
|---|---|---|
| AC-01 仅 pending 可勾选 | `isRowSelectable` ＋ 构建通过 | PASS |
| AC-02 结果逐条反馈 | 6 条单元用例覆盖全部映射分支 | PASS |
| AC-03 零回归 | 代理 44 passed；前端定向 29 passed；构建成功 | PASS |

## 4. 缺陷与处置

本版未发现功能缺陷。

## 5. 残余风险

| 风险 | 说明 |
|---|---|
| 后端未执行全量回归 | 本任务无后端代码变更；代理专项全绿，全量基线见《OpenBase-测试报告-v1.6.0》 |
| 逐条结果依赖上游 `items` | 旧上游缺失时弹窗空态并保留汇总计数，不影响队列刷新 |
| 交互层未新增 E2E | 选择/弹窗逻辑以单元与构建验证为主；后续可在 S6 走查补充批量场景 |
