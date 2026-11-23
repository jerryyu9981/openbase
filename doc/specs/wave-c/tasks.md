# 波次 C（2.20.0）任务清单

| 项 | 内容 |
|---|---|
| 文档编号 | OB-TASKS-PORTRAIT-WAVE-C |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 规格 | [spec.md](./spec.md) v1.0.0 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：C-01~C-10 可执行任务与验证 | AI 编码代理 |

## 执行顺序

> 原则：DDL/开关先行 → 进度引擎与模板 → 快照 → 调度/补偿 → 审计 → 代理/前端 → 测试 → 留痕推送。

| ID | 任务 | 主要文件 | 验证 |
|---|---|---|---|
| [x] C-01 | v2.20 增量 DDL | `src/ddl/schema_v2_20_upgrade.py`；`src/database.py`；`migration_engine.py` | 连续执行两次幂等；四表四列存在 |
| [x] C-02 | 进度引擎 | `src/engines/progress_engine.py` | 聚合口径单测（按时率/逾期/质量/工作量） |
| [x] C-03 | business 模板族种子 | `src/ddl/seed_business_templates.py` | 幂等；`profile_type='business'` 可筛 |
| [x] C-04 | profile_history 快照列 | `schema_v2_20_upgrade.py`；`progress_engine` | 新列可写；`snapshot_type='progress'` |
| [x] C-05a | cron 解析 | `src/worker/cron.py` | next_run/preview/非法表达式 |
| [x] C-05b | 调度 worker | `src/worker/scheduler.py`；`scripts/service-orchestrator.ps1` | run_once 抢占/心跳/熔断 |
| [x] C-05c | 调度 API | `src/rest_api/routes/routes_progress.py`；路由注册 | 列表/创建/改/立即执行/预览 |
| [x] C-06 | 补偿与熔断 | `src/engines/task_recovery.py`；`recalc_scheduler.py` | 过期回队、超限 failed、熔断不入队 |
| [x] C-07 | 审计 enforce | `middleware/audit_middleware.py`；`engines/audit_enforce_engine.py` | READ/EXPORT/DELETE/SCOPE_CHANGE；保留期清理 |
| [x] C-08 | 进度前端 | `ProgressTrend.vue`、`BusinessItemTable.vue`、`PortraitDetail.vue` | build 通过；页签可用 |
| [x] C-09 | 任务中心与调度前端 | `TaskCenterView.vue`、`ScheduleEditor.vue`、`CronInput.vue`、`core/api/dps.ts`、`openbase/modules/dps_proxy/__init__.py` | 类型编译；代理透传 |
| [x] C-10 | 测试与回归 | `src/tests/test_v2_20_wave_c.py` 等 | pytest/flake8/build/代理测试 |
| [x] C-11 | 版本与留痕 | `config.py`、`src/__init__.py`、`mcp_server/constants.py`；DevLogReport；计划 v1.0.4 | 版本一致；修订历史 |
| [x] C-12 | 提交与推送 | DPS / OpenBase | origin/backup/github 均成功 |

## 门禁

1. `python -m pytest src/tests/test_v2_20_wave_c.py -q --no-cov -p no:cacheprovider` 全绿。
2. 回归：`test_v2_18_wave_a.py`、`test_v2_19_wave_b.py`、`test_portrait_list_route.py`、`test_tenant_isolation.py`、`test_batch_async.py` 全绿。
3. 变更文件 `flake8 --max-line-length=120 --extend-ignore=E203,W503` 0 错误。
4. `openbase-ui` `npm run build` 通过；OpenBase 代理测试通过。
5. 两仓提交并推送 origin/backup/github 三远程。

## 风险与处置

| 风险 | 处置 |
|---|---|
| 调度重复执行 | `next_run_at` 条件更新抢占 + PG advisory lock + 幂等键 |
| 重启后任务悬挂 | `requeue_stale_tasks` 按 `started_at` 超时回队 |
| 连续失败刷屏 | `failure_count` 达阈值自动停用调度；画像任务熔断不入队 |
| profile_history 列集不一致 | 本波写入只用 DDL 保证列 + v2.20 新列，不触碰 `version_manager` 扩展列 |
| cron 表达式非法 | 解析即校验，API 返回 400，不落库 |
| 审计膨胀 | worker 每日 `purge_expired`，保留期可配 |
| 进度口径分歧 | 口径字典先落在 spec §3，试点 1–2 类事项 |
