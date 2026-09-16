# 4.0b 自测证据抽查 —— L1 分片扫描方向缺陷及修复闭环

> 归属本版测试阶段 Step 4 子步骤 4.0b「自测证据抽查（证据真实性门禁）」；
> 纳入本版测试回溯审计及缺陷闭环（4.9）证据链。

## 元信息

| 项 | 值 |
|----|-----|
| 结论 | **发现 1 个真实缺陷并修复，复验通过** |
| 抽查时间 | 2026-09-16（DEV 环境） |
| 抽查对象 | Step 3 日志中心（R-382）L1 自测单元套件 `tests/test_logs_service.py` |
| 抽查方式 | 独立复现执行 + 根因定位 + 代码修复 + 回归复验 |
| 涉及文件 | `openbase/modules/logs/repository.py`、`tests/test_logs_service.py`（未改动） |

## 1. 抽查发现的缺陷

| 项 | 值 |
|----|-----|
| 缺陷编号 | `D-146-4.0b-01`（沿用版本内缺陷编号体系） |
| 复现用例 | `test_l1_item_cap_keeps_truncated_semantics`（PERF-146-001 分页收口截断口径） |
| 表现 | `assert result.items[0].request_id == "req-bulk-0007"` 失败，实际返回 `req-bulk-0002` |
| 影响面 | L1 源在 `limit` 触顶截断时，返回的窗口为**最旧**命中组而非最新窗口，与「分片倒序」契约及 `item_cap=全量倒序前缀` 语义相悖 |

## 2. 根因定位

- `_slice_documents` 已按「新分片优先」倒序（符合契约），但 `_iter_raw_lines` 在每个分片**内部**仍按文件自上而下（旧→新）逐行输出。
- 当 `limit` 触顶提前 `break`（`total >= filters.limit`）时，命中的是分片内**最旧**的 `limit` 组；`item_cap` 在其中取 `ts` 倒序首条，故得到 `req-bulk-0002`，而非全局最新 `req-bulk-0007`。
- 兄弟用例 `test_l1_item_cap_returns_prefix_of_full_scan`（`limit` 默认不截断）已通过，证明排序本身正确，差异仅在**截断边界的扫描方向**——印证这是扫描方向缺陷而非排序缺陷。

## 3. 修复方案

`L1FileAdapter._iter_raw_lines` 分批片读取行后按「新→旧」行序倒转再产出：
- 日志按时间追加、新行位于文件末尾，倒转后与「分片倒序流式扫描」口径一致；
- `limit` 偶发截断时收敛到最新窗口，`item_cap` 返回 `ts` 倒序结果前缀的语义得以保持；
- 同步更正 `L1FileAdapter` 类 docstring 中「流式逐行读取（不整片载入内存）」为「逐分片读取（分片内行序倒转，newest-first）」，维护单一事实源。

## 4. 复验证据

| 门禁项 | 命令 | 结果 |
|--------|------|------|
| 缺陷用例复验 | `pytest tests/test_logs_service.py::test_l1_item_cap_keeps_truncated_semantics` | **PASS**（返回 `req-bulk-0007`） |
| 日志模块全量 | `pytest tests/test_logs_service.py` | **16 passed** |
| service + 端点 API | `pytest tests/test_logs_service.py tests/test_logs_endpoints_api.py` | **50 passed** |
| 静态检查 | `ruff check openbase/modules/logs/repository.py` | **All checks passed!** |

## 5. 结论

- Step 3 自测证据中该用例声称的预期与实现存在不一致（属自测证据真实性命中项）；经修复后实现与文档契约及测试预期一致。
- 修复为行为收敛（分片内扫描方向），不改变既有过滤/排序/分页/导出契约；对全量回归无外溢影响（详见 4.6 全量回归证据）。
- 缺陷状态：**已修复并闭环**（纳入 4.9 缺陷闭环）。