# Spec：A3 批量审核（OpenBase 前端 v1.7.0）

| 项 | 内容 |
|---|---|
| 状态 | **[Approved]** 用户「继续处理下一个优先级最高的残余项」授权连续推进（2026-11-21） |
| 日期 | 2026-11-21 |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》v2.5.0 §9 A3／§11 AC-AN-7／AC-RV-3／§14.3 P0；用户 2026-11-21 指令 |
| 版本冻结 | 前端 `1.6.0 → 1.7.0`（`openbase-ui/package.json`）；OpenBase 后端与 DPS 不变 |
| 交付链 | OpenBase `dps-proxy` 既有批量端点 → 前端审核收件箱逐条结果呈现 |

## 1. 目标与范围

**目标**：让 A3「批量审核」达到验收口径——勾选多条后批量通过/驳回，**结果逐条反馈**；批量仅对待审核记录生效；驳回统一意见；单条失败不影响其余条目。

**范围内**
1. 审核收件箱勾选列仅允许 `review_status=pending` 行可勾选（跨页 `reserve-selection` 保持）。
2. 批量通过/驳回沿用既有 `dpsApi.batchReviewAnnotations`，驳回必填统一意见。
3. 新增「批量复核结果」弹窗，逐条展示结果与原因；成功条目区分末级/非末级。
4. 前端单测、构建、既有代理回归；版本文档与设计回填。

**范围外**
- 不新增/修改后端与 DPS 接口（A3 属「复用」，`POST /portrait/annotations/batch-review` 已支持逐条 `comment` 与逐条结果）。
- 不改审核状态机、标签联动、RBAC、租户中间件。
- 不新增路由、不改导航 IA。

## 2. 源码事实（已核对）

| # | 事实 | 位置 |
|:-:|---|---|
| F1 | DPS 批量端点为逐条 `comment`，返回 `{total,succeeded,failed,items:[{ok,annotation_id,status,review?,error?}]}`；单条失败不影响其余 | `DPS src/rest_api/routes/routes_profiles.py` L1510-1569 |
| F2 | 成功条目 `review={level,required,finalized}` 与单条复核同口径 | 同上 L1501-1505 |
| F3 | 前端已封装 `batchReviewAnnotations` 与类型 `DpsBatchReview*` | `openbase-ui/src/core/api/dps.ts` L1625-1661 |
| F4 | 工作台已有批量条与 `batchApprove/batchReject/runBatch`，但仅聚合 toast，无逐条结果 | `DpsAnnotationWorkbenchView.vue` L1440-1482（改前） |
| F5 | 勾选列此前不区分状态，非 pending 行可被勾选 | 同上 selection 列（改前） |
| F6 | 单条复核已有失败提示与状态语义，可复用 `describeDpsError` | 同上 `doReview` |

## 3. 交互与契约

### 3.1 选择规则
- 仅 `review_status === 'pending'` 行可勾选；表头全选只覆盖当前页可勾选行。
- 切换视图/队列刷新/批量完成后清空选择。

### 3.2 批量动作
- 批量通过：二次确认（提示非末级仅推进级数，末级才联动标签）。
- 批量驳回：弹窗必填统一意见，作为每条 `comment`。
- 请求体沿用：
  ```json
  {"items":[{"annotation_id":"…","status":"approved|rejected","current_status":"pending","comment":"统一意见"}]}
  ```

### 3.3 结果呈现（AC-AN-7／AC-RV-3）
| 上游条目 | 展示 |
|---|---|
| `ok=true` + `review.finalized=true` | 成功 · `终审通过（第 k/N 级）` |
| `ok=true` + `review.finalized=false` | 成功 · `已通过第 k/N 级，待第 k+1 级` |
| `ok=true` + 驳回 | 成功 · `已驳回` |
| `ok=false` | 失败 · `上游原因（HTTP 状态码）` |
| `annotation_id` 缺失 | 标注 ID 列显示 `(未知)` |

- 顶部汇总：`共 N 条：成功 X 条，失败 Y 条`；有失败为 warning 样式。
- 失败条目不阻断其余条目，队列随后刷新，已处理记录按筛选条件自然移出。

## 4. 实现清单（精确到文件/函数）

1. `openbase-ui/src/core/api/dps.ts`：`DpsBatchReviewItemResult` 增加 `review?: {level,required,finalized}` 与索引签名。
2. `openbase-ui/src/modules/portrait/annotation/batchReview.ts`（新增）：
   - `toBatchReviewRow(item, action)`、`toBatchReviewRows(result, action)`、`batchReviewSummary(result)`。
3. `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue`：
   - 勾选列 `:selectable="isRowSelectable"`；
   - `runBatch` 写入逐条结果并打开结果弹窗；
   - 新增结果弹窗（汇总 alert ＋ 逐条表格）。
4. `openbase-ui/package.json` → `1.7.0`。
5. 新增 `openbase-ui/tests/dps-batch-review-v170.spec.ts`（6 条）。

## 5. 验证步骤

```powershell
cd openbase-ui
node node_modules/vitest/vitest.mjs run tests/dps-batch-review-v170.spec.ts tests/api-dps-v1410.spec.ts tests/dps-backend-v160.spec.ts
npm run build

# OpenBase 后端（本任务不改后端，仅回归代理）
D:\Python\python.exe -m pytest tests/test_dps_proxy.py -q -o addopts=""
```

通过标准：新增用例全绿；前端 `vue-tsc --noEmit`＋构建成功；代理回归 0 failed。

## 6. 文档交付

| 文档 | 路径 |
|---|---|
| 开发需求文档 | `doc/requirements/OpenBase-开发需求文档-v1.7.0.md` |
| 需求追溯矩阵 | `doc/requirements/OpenBase-需求追溯矩阵-v1.7.0.md` |
| 需求评审记录 | `doc/requirements/OpenBase-需求评审记录-v1.7.0.md` |
| 设计文档 | `doc/design/OpenBase-A3批量审核-设计文档-v1.0.0.md` |
| DevLog / 测试 / 部署报告 | `doc/development/…-v1.7.0.md`、`doc/test/…-v1.7.0.md`、`doc/release/…-v1.7.0.md` |
| 设计回填 | `doc/design/OpenBase-DPS统一前端页面功能设计-v1.0.0.md`（内容版本 v2.6.0） |

## 7. 风险与决策

| 风险 | 处置 |
|---|---|
| 误批量通过非待审核记录 | 勾选列仅允许 `pending`；后端状态机仍为最终裁决 |
| 部分失败被聚合提示掩盖 | 结果弹窗逐条展示原因与状态码，失败不阻断 |
| 逐条结果缺失（旧上游） | `items` 缺失时表格空态提示「上游未返回逐条结果」，汇总仍展示计数 |
| 跨页选择残留 | 批量完成/切换视图/刷新队列清空选择 |
| 提交夹带既有改动 | 仅 stage 本任务文件 |
