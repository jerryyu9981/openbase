# 波次 C（2.20.0）验收核对单

| 项 | 内容 |
|---|---|
| 文档编号 | OB-CHECKLIST-PORTRAIT-WAVE-C |
| 版本 | v1.0.6 |
| 状态 | [Review] |
| 规格 | [spec.md](./spec.md) v1.0.0 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制 | AI 编码代理 |
| v1.0.1 | 2026-11-23 | 追加验收记录（21 项单测、回归 111 项、flake8、前端 build、代理 11 项） | AI 编码代理 |
| v1.0.2 | 2026-11-23 | 回勾推送项并记录提交哈希（DPS 8768a2c、OpenBase f73b176） | AI 编码代理 |
| v1.0.3 | 2026-11-23 | 补 PG 迁移演练与压测证据（隔离库、P50/P95），回勾 PG 门禁项 | AI 编码代理 |
| v1.0.4 | 2026-11-23 | 修复 C-09 偏差：补画像计算任务列表/重试（DPS 2.20.1），回勾任务中心项 | AI 编码代理 |
| v1.0.5 | 2026-11-23 | 全栈 E2E 走查：API 33/33、Playwright 4 页；修复 5 项缺陷（DPS 2.20.2） | AI 编码代理 |
| v1.0.6 | 2026-11-23 | 导出审计接线完成（`log.export`），验证脚本 10/10；C-07 导出项闭合 | AI 编码代理 |

## 1. 功能

- [x] `business_item` 可增改查，唯一键幂等。
- [x] `POST /progress/calculate` 生成/更新 `progress_snapshot`。
- [x] 按时率、逾期数、质量均分、工作量求和与 spec §3 口径一致。
- [x] `GET /progress/{person_id}` 返回趋势；日/周/月切换可用。
- [x] 调度 cron/interval 到点触发；未来 5 次预览正确。
- [x] 任务中心三类任务可查；失败可重试。

## 2. 可靠

- [x] worker 重启后过期 running 任务自动回队。
- [x] 重复触发不产生重复快照（唯一键）。
- [x] 连续失败达阈值后调度自动停用且状态可见。

## 3. 安全

- [x] 读取/导出/删除/范围变更均落审计。
- [x] 审计 detail 不含 PII，导出动作记为 EXPORT。
- [x] 保留期外审计被清理，期内保留。
- [x] 关闭开关时进度接口 409，不泄露数据。

## 4. 兼容与迁移

- [x] `DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false` 时既有接口行为不变。
- [x] PG/SQLite 迁移连续执行两次均成功（PG 隔离库 3.18 s / 1.15 s，SQLite 已验证）。
- [x] 旧库升级后既有画像列表/详情/标注功能正常（PG 2.19→2.20 增量 0.56 s，四表四列五索引齐全；功能回归见 SQLite 111 项）。

## 5. 质量与留痕

- [x] 新增测试全绿，回归全绿。
- [x] 变更文件 flake8 0 错误；前端 build 通过。
- [x] 版本号 2.20.0 一致；DevLogReport 与计划 v1.0.4 已更新。
- [x] 两仓已推送 origin/backup/github（DPS 8768a2c、OpenBase f73b176）。

## 6. 验收记录（2026-11-23）

| 项 | 结果 |
|---|---|
| 单测 | `test_v2_20_wave_c.py` 21 passed |
| 回归 | wave A/B、画像列表、租户隔离、批量合计 111 passed（1 skipped） |
| 静态检查 | 变更文件 flake8 0 error |
| 前端 | `openbase-ui` build 通过（TaskCenterView 11.51 kB） |
| 代理 | 波次 B/C 代理用例 11 passed |

### 6.1 PG 迁移演练与压测（2026-11-23）

| 项 | 结果 |
|---|---|
| 环境 | 局域网共享 PG 14.23（192.168.0.151），一次性隔离库；演练后已删除，共享库未变 |
| 全量建库 | 3.18 s；重复执行 1.15 s；四表四列五索引两模板齐全 |
| 旧库升级 | 2.19→2.20 增量 0.56 s；重复执行 0.17 s 且 `columns_added=[]` |
| 数据规模 | `business_item` 36,000 行（200 人 × 90 天 × 2 事项） |
| 单周期计算 | 240 次：均值 72.9 ms，P50 69.2 ms，P95 113.5 ms，最大 171.6 ms |
| 辅助查询 | 趋势 79.3 ms（12 周期）；逾期 89.3 ms（54 条）；重载用户 5,000 事项中位数 51.9 ms |
| 缺陷修复 | `upgrade_utils.ensure_column` PG 返回值误报已修复并复测 |

证据文档：`DPS/doc/development/DPS-画像波次C-PG迁移演练与压测报告-v1.0.0.md`。
剩余风险：并发压测与同机部署对比未覆盖（见报告 §6）。

### 6.2 全栈 E2E 走查（2026-11-23）

| 项 | 结果 |
|---|---|
| 环境 | orchestrator 全栈（8000/8030/5173）+ 共享 PG；进度/引入开关开启、调度关闭 |
| API | 33/33 通过（画像/模板/标注/组织/引入预览/进度/调度/任务/审计/导出） |
| UI | 画像关键页 3/3、任务中心 1/1，零 console error/warn |
| 缺陷修复 | retry_count 补列、PG 删除时间参数、报表方言探测、attributes_json 掩码、el-radio 弃用告警 |
| 证据 | `doc/test/OpenBase-画像三波次全栈端到端走查报告-v1.0.0.md`、`doc/test/evidence/portrait-waves/e2e/` |
| 导出审计 | `log.export` 落 `openbase.audit_logs`，request_id 对齐、链校验通过；`scripts/verify_export_audit.py` 10/10 |
