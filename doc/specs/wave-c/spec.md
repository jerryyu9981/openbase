# 波次 C（2.20.0）进度与调度 —— 实施规格

| 项 | 内容 |
|---|---|
| 文档编号 | OB-SPEC-PORTRAIT-WAVE-C |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 上游文档 | 《OpenBase-画像优化升级三波次发布实施计划 v1.0.3》§5、《DPS-画像波次B引入与权限-DevLogReport v1.0.0》 |
| 目标版本 | DPS 2.20.0 / OpenBase 前端随版本 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：C-01~C-10 决策级规格、文件清单、验收与回滚 | AI 编码代理 |

## 1. 范围与不变量

**范围**：业务进度事项与周期快照、进度引擎、business 模板族种子、`profile_history` 周期快照、常驻调度 worker、任务补偿与熔断、审计 enforce、进度/调度/审计前端。

**不变量**：
1. 默认开关保持关闭：`DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false`；关闭时新增接口返回 409（`progress disabled`），既有接口行为与 2.19.0 一致。
2. DDL 只增不删，迁移幂等：PG 用 `IF NOT EXISTS`，SQLite 先探测 `PRAGMA table_info` 再补列（复用 `ddl/upgrade_utils.py`）。
3. 多租户：新增表读写均带 `tenant_id` 谓词；缺失上下文沿用既有 fail-closed 口径。
4. 进度计算与画像计算互不干扰：复用 `portrait_template.profile_type='business'` 筛选，不改 `persona` 口径。
5. 审计读取/导出/删除/范围变更全覆盖；审计 detail 不落 PII（沿用 B 波 `SENSITIVE_KEYWORDS` 与身份块）。
6. `profile_history` 写入只使用「建表保证列 + v2.20 新增列」，不依赖 `version_manager` 的历史扩展列（该 INSERT 与 DDL 列集不一致，属存量缺陷，本波不修）。

## 2. C-01 v2.20 增量 DDL

新增 `DPS/src/ddl/schema_v2_20_upgrade.py`：
- `SCHEMA_VERSION = "2.20.0"`
- `TABLES_V2_20`：`business_item`、`progress_snapshot`、`datasource_schedule`、`worker_heartbeat`
- `TABLE_COLUMNS_V2_20`：`profile_history` 增 `period_type / period_key / snapshot_type / template_code`
- `ensure_v2_20_upgrade(database) -> dict`：建表 → 补列 → 建索引；返回 `schema_version/dialect/tables/columns_added` 摘要并 INFO 留痕
- `DPS/src/database.py`：`ensure_v2_19_upgrade(self)` 之后调用 `ensure_v2_20_upgrade(self)`
- `DPS/src/engines/migration_engine.py`：`_MIGRATIONS` 增 `"2.20.0"` 记账项（`up_sql=""`，口径同 2.18.0/2.19.0）

### 2.1 business_item（业务事项）

| 列 | PG | SQLite | 说明 |
|---|---|---|---|
| id | UUID PK default gen_random_uuid() | TEXT PK | |
| person_id | VARCHAR(100) NOT NULL | TEXT NOT NULL | 主体 |
| item_type | VARCHAR(50) NOT NULL | TEXT NOT NULL | 学习/劳动/报到/走访/心理/就业 |
| item_code | VARCHAR(64) | TEXT | 幂等键组成 |
| item_name | VARCHAR(200) | TEXT | 事项名 |
| owner_id | VARCHAR(100) | TEXT | 责任人 |
| planned_at | TIMESTAMPTZ | TEXT | 应完成时间 |
| completed_at | TIMESTAMPTZ | TEXT | 实际完成时间 |
| status | VARCHAR(20) DEFAULT 'pending' | TEXT DEFAULT 'pending' | pending/done/cancelled |
| quality_score | NUMERIC(5,2) | REAL | 0–100 |
| workload_hours | NUMERIC(6,2) | REAL | 工作量 |
| source | VARCHAR(20) DEFAULT 'manual' | TEXT DEFAULT 'manual' | manual/ingest |
| org_id | UUID | TEXT | |
| tenant_id | UUID | TEXT | |
| data_json | JSONB DEFAULT '{}' | TEXT DEFAULT '{}' | 扩展字段 |
| created_at / updated_at | TIMESTAMPTZ DEFAULT NOW() | TEXT DEFAULT CURRENT_TIMESTAMP | |

唯一键：`(tenant_id, person_id, item_type, item_code, planned_at)`（upsert 幂等）。
索引：`(person_id, planned_at)`、`(tenant_id, status, planned_at)`。

### 2.2 progress_snapshot（进度周期快照）

列：`id, person_id, org_id, tenant_id, period_type(day/week/month), period_key, template_code, total_items, completed_items, overdue_items, on_time_rate NUMERIC(5,2), quality_score NUMERIC(5,2), workload_hours NUMERIC(8,2), dimensions_json JSONB, computed_at`。
唯一键：`(tenant_id, person_id, period_type, period_key, template_code)`；索引 `(person_id, period_type, period_key)`。

`period_key` 口径：`day=YYYY-MM-DD`、`week=YYYY-Www`（ISO 周，周一为起点）、`month=YYYY-MM`。

### 2.3 datasource_schedule（数据源调度）

列：`id, datasource_id, schedule_type(cron|interval), cron_expr, interval_seconds, enabled, next_run_at, last_run_at, last_status, failure_count, max_failures, org_id, tenant_id, created_at, updated_at`。
索引：`(enabled, next_run_at)`。

### 2.4 worker_heartbeat（worker 心跳）

列：`worker_name VARCHAR(64) PK`、`last_seen_at`、`meta_json`、`tenant_id`。用于运维观测与单实例判定。

## 3. C-02 进度引擎

新增 `DPS/src/engines/progress_engine.py`：

- `normalize_period(period_type, moment) -> tuple[str, datetime, datetime]`：返回 `period_key` 与周期起止（左闭右开）。
- `aggregate_items(items) -> dict`：
  - `total_items`、`completed_items`、`overdue_items`（`status != 'done'` 且 `planned_at < now`）；
  - `on_time_rate = 按时完成数 / 已到期数 * 100`（已到期数 0 → 100）；
  - `quality_score = 已完成事项 quality_score 均值`（无值 → 0）；
  - `workload_hours = 已完成事项 workload_hours 之和`；
  - `dimensions_json = {item_type: {total, completed, overdue, hours}}`。
- `async compute_progress(person_id, template_code, period_type, period_key, tenant_id=None, org_id=None) -> dict`：
  1. 校验 `settings.progress_enabled`；
  2. 按周期取 `business_item`；
  3. `aggregate_items` 后 **upsert** `progress_snapshot`（唯一键冲突走 UPDATE）；
  4. 写 `profile_history` 一条：`snapshot_type='progress'`、`period_type/period_key/template_code` 落新列，`snapshot` 存聚合结果 JSON，`change_reason='progress_snapshot'`；版本号取该 profile 现有 `MAX(version)+1`；
  5. 返回快照字典。
- `async get_trend(person_id, period_type, limit=12, tenant_id=None) -> list[dict]`：按 `period_key` 倒序取最近 N 条。
- `async list_overdue(person_id=None, org_id=None, tenant_id=None) -> list[dict]`。
- `async upsert_item(payload: dict) -> dict`：唯一键冲突 UPDATE；`status='done'` 时补 `completed_at`。
- 所有 SQL 参数化；不记录 PII 到日志。

责任人映射：`owner_id` 支持 `person_id` 或 `user_id`；统计按 `owner_id` 直取，不引入新映射表（B 波 `org_member` 仅用于组织归属）。

## 4. C-03 business 模板族种子

新增 `DPS/src/ddl/seed_business_templates.py`：
- `ensure_business_templates(database, tenant_id=None) -> dict`（幂等，`WHERE NOT EXISTS` / 存在即跳过）：
  - 复合模板 `business_progress`：`profile_type='business'`、`subject_type='person'`、`template_kind='composite'`、`version='1.0.0'`；
  - `dimension_config.dimensions` 五维：`punctuality`(按时率)、`completion`(完成率)、`quality`(质量)、`workload`(工作量)、`compliance`(合规)；
  - 子模板 `business_progress_detail`：`template_kind='component'`，挂载 `portrait_template_component(parent_code='business_progress', child_code='business_progress_detail', sort_order=1, required=true)`；
  - 返回 `created/skipped/template_codes` 摘要。
- 由 `ensure_v2_20_upgrade` 末尾调用（失败仅 WARN，不阻断迁移，避免种子阻塞 DDL）。
- 既有 `portrait_template` 列表接口按 `profile_type` 过滤即可区分两类画像，无需新增 `profile_family`。

## 5. C-04 profile_history 周期快照

- v2.20 补 4 列：`period_type VARCHAR(10)`、`period_key VARCHAR(20)`、`snapshot_type VARCHAR(20) DEFAULT 'version'`、`template_code VARCHAR(100)`；
- 索引 `(profile_id, snapshot_type, period_key)`；
- 写入方：`progress_engine.compute_progress`（`snapshot_type='progress'`）；
- 读取方：`GET /progress/{person_id}` 优先读 `progress_snapshot`，`profile_history` 作为审计轨迹（不参与趋势主查询，避免两套口径漂移）。

## 6. C-05 调度 worker

新增 `DPS/src/worker/__init__.py`、`DPS/src/worker/cron.py`、`DPS/src/worker/scheduler.py`、`DPS/scripts/service-orchestrator.ps1`。

### 6.1 cron 解析（`worker/cron.py`）
- `parse_cron(expr) -> CronSpec`：5 段（分/时/日/月/周），支持 `*`、`*/n`、`a-b`、`a,b`、单值；非法抛 `ValueError("PARAM_INVALID_CRON")`。
- `next_run(expr, base: datetime) -> datetime`：按分钟步进上限 366 天，返回严格大于 base 的最近触发时刻。
- `preview(expr, base=None, count=5) -> list[datetime]`：连续 5 次预览（前端用）。

### 6.2 调度循环（`worker/scheduler.py`）
- `async run_once(database, now=None) -> dict`：扫描 `datasource_schedule WHERE enabled=true AND next_run_at <= now`，逐条：
  1. 抢占：`UPDATE datasource_schedule SET next_run_at=<下次>, last_run_at=now WHERE id=? AND next_run_at=<原值>`，`rowcount=0` 视为被其他实例抢占，跳过（等价 advisory lock 语义）；
  2. 执行：调用 `datasource_engine.execute_sync(datasource 对应任务)`；PG 额外先尝试 `pg_try_advisory_lock(hashtext(id))`，拿不到即跳过，结束 `pg_advisory_unlock`；
  3. 回写 `last_status`（success/failed）、成功清零 `failure_count`，失败 `failure_count+1`；`failure_count >= max_failures` 置 `enabled=false` 并 WARN（熔断可见）；
  4. 每轮更新 `worker_heartbeat('dps-worker')`。
- `async run_forever(poll_seconds=10)`：`settings.scheduler_enabled` 为假直接返回；捕获 `CancelledError` 优雅退出；单轮异常仅 ERROR 不退出。
- `main()`：`asyncio.run` 装配 `db.initialize()/init_schema()` 后 `run_forever()`；入口 `python -m worker.scheduler`。
- `scripts/service-orchestrator.ps1`：`start|stop|status dps-worker`，PID 落 `scripts/.run/dps-worker.pid`；仅启动 worker，不改 API 启停。

### 6.3 调度 API（`routes_progress.py` 内）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/schedules` | 调度列表（含 `next_run_at/last_status/failure_count`） |
| POST | `/schedules` | 创建（cron 或 interval，非法 cron 400） |
| PUT | `/schedules/{id}` | 启停/改表达式/改阈值 |
| POST | `/schedules/{id}/run` | 立即执行一次 |
| GET | `/schedules/{id}/preview` | 未来 5 次触发时间 |

## 7. C-06 补偿与熔断

新增 `DPS/src/engines/task_recovery.py`：
- `async requeue_stale_tasks(database=None, now=None, stale_seconds=None) -> dict`：
  - 条件：`status='running'` 且 `started_at < now - stale_seconds`（默认取 `settings.tag_change_recalc_task_timeout_seconds`，缺省 600）；
  - 动作：`status='pending'`、`started_at=NULL`、`retry_count+1`、`error='stale_requeue'`；`retry_count >= max_retries` 直接置 `failed`；
  - 返回 `requeued/failed` 摘要。
- `async circuit_breaker_open(person_id, template_code, threshold=3, window_minutes=30) -> bool`：最近 N 条任务连续 `failed` 达阈值即视为熔断；`recalc_scheduler.enqueue_tag_change_recalc` 在入队前调用，熔断时返回 `{"enqueued": False, "reason": "circuit_open"}`。
- 由 `worker.scheduler.run_once` 每轮调用 `requeue_stale_tasks`。

## 8. C-07 审计 enforce

- `DPS/src/middleware/audit_middleware.py`：
  - `_resolve_action`：路径以 `/export` 结尾 → `EXPORT`；含 `/scope` 或 `/members` 的 PUT → `SCOPE_CHANGE`；
  - `_resolve_resource_id`：`/portrait/{person_id}`、`/portrait/{person_id}/tasks`、`/business-items/{id}`、`/schedules/{id}` 提取末段（`export`/`tasks` 等静态段跳过）；
  - 审计记录带 `resource_id`（现有 `record` 已支持）。
- 新增 `DPS/src/engines/audit_enforce_engine.py`：
  - `async record_data_access(user_id, action, resource_type, resource_id, *, org_id, tenant_id, request_id, row_count=None, scope=None)`：detail 仅含计数与范围枚举，不含数据；
  - `async purge_expired(retention_days=None) -> int`：`DELETE FROM audit_logs WHERE timestamp < cutoff`，默认 `settings.audit_retention_days`；由 worker 每日触发一次（内存标记去重）。
- `/audit/logs` 增加 `result` 过滤；导出端点记录 `EXPORT` 审计。

## 9. C-08 进度前端（OpenBase）

- `openbase-ui/src/modules/portrait/components/ProgressTrend.vue`：SVG 折线（按时率/完成率双线）+ 周期切换（日/周/月），空态文案「暂无进度快照」；
- `openbase-ui/src/modules/portrait/components/BusinessItemTable.vue`：事项列表（类型/计划时间/状态/质量/工作量/逾期高亮），支持按状态筛选；
- `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue`：新增「业务进度」页签，挂载上述两组件；
- `openbase/modules/dps_proxy/__init__.py`：白名单透传 `/progress/*`、`/business-items/*`、`/schedules/*`。

## 10. C-09 任务中心与调度前端

- `openbase-ui/src/modules/portrait/pages/TaskCenterView.vue`：三类任务（引入/画像计算/调度）Tab，支持状态筛选与重试按钮；
- `openbase-ui/src/modules/portrait/components/ScheduleEditor.vue`：调度表单（cron/interval、启用、最大失败次数）；
- `openbase-ui/src/modules/portrait/components/CronInput.vue`：cron 输入 + 未来 5 次预览（调用 `/schedules/preview` 或本地校验）；
- `openbase-ui/src/core/api/dps.ts`：新增 `DpsBusinessItem`、`DpsProgressSnapshot`、`DpsSchedule`、`DpsAuditLog` 类型与 12 个方法；
- 路由与菜单：`modules/portrait/index.ts` 注册 `task-center` 路由（沿用现有模块路由表）。

## 11. C-10 测试与门禁

新增 `DPS/src/tests/test_v2_20_wave_c.py`，覆盖：
1. v2.20 DDL 连续执行两次幂等；四表存在；`profile_history` 四新列存在；
2. business 模板种子幂等（第二次 `created=0`）；
3. 聚合口径（按时率/逾期/质量/工作量/维度明细）；
4. 快照 upsert 幂等（同周期不重复行）；
5. `profile_history` 写入 `snapshot_type='progress'` 且列值正确；
6. cron：`next_run` 边界（跨日/跨周）、非法表达式 400 级异常、`preview` 5 条递增；
7. `run_once`：到点执行、未到点跳过、失败计数与熔断停用；
8. `requeue_stale_tasks`：过期 running 回队、超限置 failed；熔断判定；
9. `purge_expired` 删除旧审计、保留新审计；
10. 接口：`progress_enabled=false` → 409；开启后 `GET /progress/{person_id}` 返回趋势。

门禁：
- `python -m pytest src/tests/test_v2_20_wave_c.py -q --no-cov -p no:cacheprovider` 全绿；
- 回归：`test_v2_18_wave_a.py`、`test_v2_19_wave_b.py`、`test_portrait_list_route.py`、`test_tenant_isolation.py`、`test_batch_async.py`；
- 变更文件 `flake8 --max-line-length=120 --extend-ignore=E203,W503` 0 错误；
- `openbase-ui` `npm run build` 通过；OpenBase 代理测试通过。

## 12. 回滚

1. `DPS_PROGRESS_ENABLED=false`：进度接口 409，进度计算不执行；表保留。
2. `DPS_SCHEDULER_ENABLED=false` + 停止 `dps-worker`：API 不受影响，调度停摆。
3. 审计保留期调整 `DPS_AUDIT_RETENTION_DAYS`，不删表。
4. DDL 不回退（只增列/表）。
