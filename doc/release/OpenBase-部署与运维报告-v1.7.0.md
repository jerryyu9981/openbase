# OpenBase-部署与运维报告-v1.7.0

| 项 | 内容 |
|---|---|
| 版本 | v1.7.0（前端） |
| 状态 | [Ready for Release] |
| 日期 | 2026-11-21 |
| 变更范围 | 审核收件箱批量审核结果闭环（A3） |
| 回滚目标 | v1.6.0 |

## 1. 制品与依赖

| 项 | 说明 |
|---|---|
| 前端 | `openbase-ui/src/core/api/dps.ts`、`modules/portrait/annotation/batchReview.ts`、`DpsAnnotationWorkbenchView.vue`、`package.json` |
| 后端 | **无变更** |
| DPS | **无变更**（复用既有批量端点） |
| 数据库 | **无**迁移 |
| 依赖 | **无**新增 npm/pip 依赖 |
| 配置 | **无**新增环境变量 |

## 2. 上线步骤

1. 确认 OpenBase 后端 ≥ v1.6.0、DPS 已提供批量端点（≥ v1.5.0 基线）。
2. 发布前端制品 `openbase-ui/dist`（v1.7.0）。
3. 冒烟 `/portrait/dps/annotations?view=review`：
   - 勾选多条待审核记录 → 批量通过/驳回；
   - 驳回时统一意见必填；
   - 结果弹窗逐条展示成功/失败与原因；
   - 非待审核行不可勾选。

## 3. 构建与验证

| 检查 | 结果 |
|---|---|
| 前端定向 spec | 29 passed（3 spec） |
| `npm run build`（vue-tsc + vite） | 成功，dist 生成 |
| 代理回归 | `tests/test_dps_proxy.py` 44 passed |

## 4. 监控

- 代理沿用既有上游观测与 request_id 日志。
- 关注 `/dps-proxy/annotations/batch-review` 的 4xx/5xx 与逐条 `failed` 比例。

## 5. 回滚

| 场景 | 操作 | 影响 |
|---|---|---|
| 前端异常 | 回退 dist 至 1.6.0 | 批量仅聚合提示（旧行为），审核可用 |
| 后端/DPS 异常 | 无需回滚（本版未改） | — |

无数据回滚需求（前端仅读取/提交既有批量端点）。

## 6. 上线顺序

**OpenBase 后端（不变）→ 前端 1.7.0**。DPS 无需配合发布。
