# OpenBase-测试报告-v1.6.0

| 项 | 内容 |
|---|---|
| 版本 | v1.6.0（后端 ＋ 前端） |
| 状态 | [Approved] |
| 日期 | 2026-11-20 |
| 测试对象 | A4 标注详情代理与审核收件箱接入 |
| 需求基线 | 《OpenBase-开发需求文档-v1.6.0》v1.0.0 |
| 环境 | Windows；Python 3.12；pytest；Node/vitest；`-o addopts=""` |

## 修订历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0.0 | 2026-11-20 | 首版：定向、前端与分片全量回归结果 |

## 1. 测试范围

| 层级 | 内容 |
|---|---|
| 代理单元 | `dps_annotation_detail`：路由注册/顺序、路径编码、身份头与参数、404 保真 |
| 前端单元 | `getAnnotationDetail`：路径编码与详情字段 |
| 前端构建 | `vue-tsc` ＋ `vite build` |
| 后端回归 | `tests/` 全量（138 个 `test_*.py`，分三片串行） |

## 2. 定向结果

| 用例 | 结果 |
|---|---|
| `test_detail_route_registered` | PASS |
| `test_static_export_precedes_dynamic_detail` | PASS |
| `test_detail_forwards_encoded_path_and_identity` | PASS |
| `test_detail_upstream_404_passthrough` | PASS |
| `dps-backend-v160.spec.ts` | PASS |
| `dps-ui-v1410.spec.ts`（回归） | PASS |

- 后端定向：**4 passed**。
- 前端：**15 passed**（2 个 spec）。
- `npm run build`：**成功**。

## 3. 后端全量回归（分片）

> 说明：Windows 下两个 pytest 进程并发会争用 `%TEMP%` 同名 SQLite（`WinError 32`），
> 且单进程全量在环境时限内被外部终止；故改为**三片串行**执行，覆盖全部 138 个测试文件。

| 分片 | 文件范围 | 结果 | 耗时 |
|---|---|---|---|
| 1 | 第 1~46 个文件 | 597 passed；`test_identity_events_list.py` 17 个 setup/teardown 错误（并发锁） | 16:24 |
| 1 复跑 | `test_identity_events_list.py`（无并发） | **9 passed** | 0:51 |
| 2 | 第 47~92 个文件 | 737 passed，2 skipped | 12:42 |
| 3 | 第 93~138 个文件 | 526 passed，4 skipped | 21:49 |

**合计：1869 passed，6 skipped，0 failed。**

锁错误定位：并发运行的另一 pytest 进程占用
`C:\Users\jerry\AppData\Local\Temp\openbase_test_identity_events_list.db`；
单独复跑该文件 9/9 通过，属环境并发问题，非代码缺陷。

## 4. 缺陷与处置

| 编号 | 现象 | 根因 | 处置 | 复测 |
|---|---|---|---|---|
| O-160-01 | 分片 1 出现 17 个 ERROR（WinError 32） | 另一 pytest 进程占用同名临时库 | 终止并发进程后单独复跑 | 9 passed |

本版代码自身未发现功能缺陷。

## 5. 追溯与结论

- RT-160-001~012 均有对应用例或构建证据（见追溯矩阵）。
- 结论：**通过**。A4 代理与前端接入可用，既有能力零回归。

## 6. 残余风险

| 风险 | 说明 |
|---|---|
| 分片而非单进程全量 | 三片覆盖全部测试文件且 0 failed；建议后续 CI 在 Linux 单进程跑一次基线 |
| DPS 未升级 | 前端详情 404 自动回退队列摘要，已有设计兜底 |
