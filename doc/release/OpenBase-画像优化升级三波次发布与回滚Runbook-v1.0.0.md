# OpenBase 画像优化升级三波次发布与回滚 Runbook

| 项 | 内容 |
|---|---|
| 文档编号 | OB-OPS-PORTRAIT-WAVES-RUNBOOK |
| 版本 | v1.0.0 |
| 状态 | [Draft]（待发布负责人批准后转 [Approved]） |
| 上游文档 | 《OpenBase-画像优化升级三波次发布实施计划 v1.0.5》、《DPS-画像波次C进度与调度-DevLogReport v1.0.2》、《DPS-画像波次C-PG迁移演练与压测报告 v1.0.0》 |
| 发布对象 | DPS 2.20.1 + OpenBase 主线（提交 `6d6f884` 起） |
| 适用环境 | Dev → Test → Pro（蓝绿/金丝雀） |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：三波次发布步骤、冒烟清单、回滚演练、监控项与命令附录 | AI 编码代理 |

## 1. 发布范围与版本矩阵

| 组件 | 版本/提交 | 本波包含能力 |
|---|---|---|
| DPS | 2.20.1（`f90b768`） | 组织/数据范围、PII enforce、引入落库、进度模型与引擎、调度 worker、补偿熔断、审计 enforce、画像任务列表与重试 |
| OpenBase 后端 | 主线（`6d6f884`） | dps-proxy 新增 orgs/ingest/progress/business-items/schedules/audit/tasks 透传 |
| OpenBase 前端 | 随 OpenBase 构建产物 | 命名中文化、引入任务中心、任务中心（引入/画像计算/调度/审计）、画像详情业务进度 |

发布顺序：**数据库迁移 → DPS API → OpenBase 后端/前端（蓝绿或金丝雀）→ dps-worker → 冒烟 → 单租户灰度 → 全量**。

> 原则：每波能力默认关闭或 `warn`；关闭时行为与升级前一致；DDL 只增不删、不回退。

## 2. 前置检查（全部通过才可进入发布窗口）

| # | 检查项 | 通过标准 | 证据 |
|---|---|---|---|
| P1 | 代码与标签 | DPS `2.20.1` 已打 tag；OpenBase 目标提交已在 origin | `git tag -l v2.20.1`、`git log -1` |
| P2 | 三远程同步 | origin / backup / github 均无落后 | `git status`、三远程 `git log` |
| P3 | 测试门禁 | 波次 A/B/C 回归 82+ 通过、代理用例通过、flake8 0、前端 build 通过 | DevLogReport §6 |
| P4 | PG 演练 | 隔离库全量 3.18 s / 幂等 1.15 s；2.19→2.20 增量 0.56 s | PG 演练报告 §2 |
| P5 | 压测基线 | 36k 行、240 次单周期 P50 69 ms / P95 113 ms（跨机 LAN） | PG 演练报告 §3 |
| P6 | 开关基线 | `DPS_PII_MODE=enforce`、`DPS_DATA_SCOPE_MODE=off`、`DPS_INGEST_PERSIST_ENABLED=false`、`DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false`、`DPS_AUDIT_RETENTION_DAYS=180` | 环境配置核对 |
| P7 | 备份 | 生产库全量备份完成且可恢复校验通过；记录备份时间点 | DBA 回执 |
| P8 | 回滚路径 | 上一版本 OpenBase/DPS 制品与配置可用；上一版本实例未被覆盖 | 制品库/部署记录 |
| P9 | 变更窗口 | 低峰窗口、通知已发、值守人就位 | 发布单 |
| P10 | 迁移演练 | 在数据库副本执行 v2.18/v2.19/v2.20 增量并记录耗时与锁等待 | 演练记录（可复用 P4 方法） |

## 3. 发布步骤

### 阶段 0：冻结与备份

1. 冻结两仓 main 分支（禁止发布窗口内合并）。
2. 对生产库做全量备份；对 OpenBase 与 DPS 记录当前运行制品版本与配置快照。

### 阶段 1：数据库迁移（DPS）

1. 在副本库按 P10 演练一次，确认耗时与锁等待可接受。
2. 生产库执行 DPS `2.20.1` 启动时的幂等迁移（`init_schema` 内 `ensure_v2_18/19/20`）。
3. 校验：

```sql
-- 期望 4 行
SELECT table_name FROM information_schema.tables
WHERE table_schema='platform'
  AND table_name IN ('business_item','progress_snapshot','datasource_schedule','worker_heartbeat');

-- 期望 4 行
SELECT column_name FROM information_schema.columns
WHERE table_schema='platform' AND table_name='profile_history'
  AND column_name IN ('period_type','period_key','snapshot_type','template_code');

-- 期望 2 行：business_progress / business_progress_detail
SELECT code FROM platform.portrait_template WHERE profile_type='business';
```

4. 重复执行一次迁移，确认 `columns_added` 为空（幂等）。

### 阶段 2：DPS API

1. 按现行 DPS 部署流程替换为 2.20.1 制品并启动 API。
2. 健康检查：`GET /health` 返回 2xx。
3. 只读验证：画像列表、画像详情、模板列表、标注队列各取一页，确认响应与升级前一致。
4. 观察 5 分钟：错误率、P95、数据库连接数无异常上升。

### 阶段 3：OpenBase 后端 + 前端

1. 确认环境变量（禁止默认/弱密钥）：
   - `OPENBASE_DB_URL`、`OPENBASE_ENV=production`；
   - `OPENBASE_JWT_SECRET` ≥32 字符强随机；
   - `OPENBASE_DPS_UPSTREAM_BASE` 指向阶段 2 的 DPS 实例。
2. 打 tag 后执行部署脚本（蓝绿或金丝雀）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_pro.ps1 -Env pro -Strategy canary -Port 8765 -Version <OpenBase 版本>
```

3. 验证顺序：登录 → 画像列表 → 画像详情 → 模板 → 标注 → 引入任务 → 任务中心 → 审计日志。
4. 金丝雀放量 10% → 观察 15 分钟 → 50% → 全量。

### 阶段 4：dps-worker（默认不启动）

> 仅当 `DPS_PROGRESS_ENABLED=true` 且调度数据已配置时启动；否则保持关闭。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 start dps-worker
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 status dps-worker
```

心跳校验：`SELECT * FROM platform.worker_heartbeat WHERE worker_name='dps-worker';` 应持续更新。

### 阶段 5：能力开关灰度（按波次）

| 顺序 | 开关 | 灰度值 | 观察 |
|---|---|---|---|
| 1 | `DPS_DATA_SCOPE_MODE` | `off` → `warn`（单租户） | 越权空集与日志，无 500 |
| 2 | `DPS_INGEST_PERSIST_ENABLED` | `false` → `true`（单租户） | 引入任务成功率、错误行脱敏 |
| 3 | `DPS_PROGRESS_ENABLED` | `false` → `true`（试点 1–2 类事项） | 进度 P95、快照行数、任务中心 |
| 4 | `DPS_SCHEDULER_ENABLED` | `false` → `true` | 触发次数、`failure_count`、心跳 |

每次开启观察不少于 30 分钟，异常即回退该开关（见 §5）。

## 4. 冒烟清单

### 4.1 接口级

| # | 检查 | 期望 |
|---|---|---|
| S1 | `GET /health`（DPS） | 2xx |
| S2 | OpenBase 登录 | 200 + token |
| S3 | `GET /api/v1/dps-proxy/portrait/list` | 200，`code=0` |
| S4 | 画像详情 | 200，字段与升级前一致 |
| S5 | `GET /dps-proxy/progress/{person_id}`（开关关闭） | 409 `progress disabled` |
| S6 | 开关开启后同接口 | 200，`items` 数组 |
| S7 | `GET /dps-proxy/portraits/tasks` | 200，分页结构 |
| S8 | `POST /dps-proxy/portraits/tasks/{id}/retry`（失败任务） | 200，`retried=true` |
| S9 | `GET /dps-proxy/audit/logs?action=EXPORT` | 200，仅导出动作 |
| S10 | `GET /dps-proxy/schedules/preview?expr=0+3+*+*+*` | 200，5 个递增时间 |

### 4.2 页面级

- 画像列表：中文名优先、编码展示、筛选正常；
- 画像详情：「业务进度」卡片在开关关闭时显示提示、开启后展示趋势与事项；
- 引入任务：列表、详情、映射、错误 CSV（脱敏）；
- 任务中心：引入任务 / 画像计算任务（列表+重试）/ 数据源调度（编辑+立即执行）/ 审计日志（动作筛选）；
- 组织树选择与数据范围切换（灰度租户）。

### 4.3 运维级

- worker 心跳持续更新；`datasource_schedule.last_status` 正常；
- 连续失败达阈值时调度自动停用且可见；
- 审计保留期任务每日执行一次（日志含 `removed=`）。

## 5. 回滚演练与步骤

> 原则：**先关开关 → 再停 worker → 再回切应用版本 → 最后才考虑数据修复**；DDL 不回退。

### 5.1 分级回滚

| 级别 | 触发条件 | 动作 | 验证 |
|---|---|---|---|
| L1 能力回退 | 进度/调度/引入单点异常 | `DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false`、`DPS_INGEST_PERSIST_ENABLED=false` | 对应接口 409；既有画像功能正常 |
| L2 权限回退 | 数据范围误伤/越权 | `DPS_DATA_SCOPE_MODE=off`；必要时 `DPS_PII_MODE=warn` | 列表恢复全量口径；导出恢复 |
| L3 调度停机 | worker 异常/重复执行 | 停止 `dps-worker` | 调度停摆但 API 正常；无重复任务 |
| L4 应用回切 | API/前端严重故障 | OpenBase 蓝绿回切上一版本；DPS 回退 2.19.0 制品 | 登录与核心页面可用 |

### 5.2 演练脚本（发布前在 Test 环境执行并留痕）

1. 开启 `DPS_PROGRESS_ENABLED=true`，调用 `GET /dps-proxy/progress/{person_id}` 记录 200。
2. 关闭开关，重复调用 → 期望 409，且画像列表/详情不受影响。
3. 启动 worker，确认心跳；制造一条失败调度（错误数据源），观察 `failure_count` 递增至阈值后 `enabled=false`。
4. 手动重试一条失败画像任务 → 期望 `retried=true` 且任务回到 `pending`。
5. 执行 L1→L3 组合回退，确认无残留写入（`progress_snapshot` 行数不再增长）。
6. 记录每步耗时与现象，附发布单。

### 5.3 数据处置

- 已写入的 `progress_snapshot` / `profile_history(snapshot_type='progress')` 默认保留；
- 如确需清理，按 `tenant_id + person_id + period_key` 定点删除，须双人复核并留审计。

## 6. 监控与观察项（发布后 24 小时）

| 指标 | 阈值/期望 | 处置 |
|---|---|---|
| HTTP 5xx 比例 | 不高于发布前基线 | 超阈值触发 L4 |
| 画像列表/详情 P95 | 无明显劣化 | 定位慢查询/索引 |
| 进度计算 P95（开关开启） | ≤ 200 ms（跨机 LAN） | 超阈值关闭进度开关并排查 |
| worker 心跳延迟 | ≤ 3 个轮询周期 | 重启 worker / 查日志 |
| `datasource_schedule.failure_count` | 不持续增长 | 达阈值自动停用，人工修复后再启用 |
| 审计表增长 | 日增量可预期 | 核对 `DPS_AUDIT_RETENTION_DAYS` |
| 数据库连接数/锁等待 | 无持续升高 | 检查迁移/长事务 |

## 7. 值守与交付物

| 交付物 | 位置 |
|---|---|
| 发布实施计划 | `doc/design/OpenBase-画像优化升级三波次发布实施计划-v1.0.3.md`（内版 v1.0.5） |
| DPS 开发与运维记录 | `DPS/doc/development/DPS-画像波次C进度与调度-DevLogReport-v1.0.0.md`（内版 v1.0.2，§7 worker 手册） |
| PG 演练与压测 | `DPS/doc/development/DPS-画像波次C-PG迁移演练与压测报告-v1.0.0.md` |
| 验收核对单 | `doc/specs/wave-c/checklist.md`（v1.0.4） |
| 本 Runbook | 本文档 |

## 8. 附录：命令速查

```powershell
# OpenBase 部署（金丝雀/蓝绿）
powershell -ExecutionPolicy Bypass -File scripts/deploy_pro.ps1 -Env pro -Strategy canary -Port 8765 -Version <版本>

# DPS worker 启停与状态
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 start  dps-worker
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 stop   dps-worker
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 status dps-worker

# 三远程同步核对（两仓分别执行）
git status
git log --oneline -3
git log --oneline -1 origin/main; git log --oneline -1 backup/main; git log --oneline -1 github/main
```

```sql
-- 迁移后结构校验
SELECT table_name FROM information_schema.tables
WHERE table_schema='platform'
  AND table_name IN ('business_item','progress_snapshot','datasource_schedule','worker_heartbeat');

-- worker 心跳
SELECT worker_name, last_seen_at FROM platform.worker_heartbeat;

-- 调度状态
SELECT id, datasource_id, enabled, last_status, failure_count, next_run_at
FROM platform.datasource_schedule ORDER BY updated_at DESC LIMIT 20;

-- 进度快照规模
SELECT period_type, COUNT(*) FROM platform.progress_snapshot GROUP BY period_type;
```

> 未验证项：本次尚未在 Pro 环境实际部署；本 Runbook 中的部署命令沿用现行脚本，执行前须由发布负责人按现场端口与制品版本复核。
