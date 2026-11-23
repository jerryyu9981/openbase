# OpenBase 画像优化升级三波次生产发布执行计划

| 项 | 内容 |
|---|---|
| 文档编号 | OB-OPS-PORTRAIT-WAVES-PROD-PLAN |
| 文档版本 | v1.0.1 |
| 状态 | [Review]（待发布负责人与项目负责人批准后转 [Approved]） |
| 发布对象 | DPS 2.20.2 @ `80e8837`（tag `v2.20.2`）＋ OpenBase 主线 @ `8985875` ＋ openbase-ui 构建产物 |
| 适用环境 | Pro（生产；Dev/Test 已验证） |
| 存放位置 | `doc/release/`（对应文档规范生产环境 `doc/operation/OpenBase-发布计划-v{版本号}.md` 映射） |
| 上游依据 | 《OpenBase-画像优化升级三波次发布与回滚 Runbook v1.0.0》、《OpenBase-画像优化升级三波次发布实施计划 v1.0.3》（内版 v1.0.8）、《OpenBase-画像三波次全栈端到端走查报告 v1.0.0》（内版 v1.1.0）、《DPS-画像波次C-PG迁移演练与压测报告 v1.0.0》 |
| 关联文档 | 《OpenBase-导出留痕修复变更摘要 v1.0.0》、`doc/specs/wave-c/checklist.md`（内版 v1.0.6）、P13/P14/P15 验证证据 `doc/test/evidence/portrait-waves/prod-gates/` |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：版本矩阵、15 项入场门禁、分阶段执行步骤、开关灰度、冒烟、分级回滚、监控、交付物与批准点 | AI 编码代理 |
| v1.0.1 | 2026-11-23 | P13/P14/P15 真机验证通过（隔离库 12/12），门禁状态与结论同步更新，新增 §7.4 验证结论与证据 | AI 编码代理 |

## 0. 结论摘要

> **当前判定（v1.0.1）：入场门禁 15 项中 9 项已具备、6 项待执行或待裁定 ⇒ 尚不可进入生产发布窗口。**
>
> 已具备：DPS 版本与标签、三远程同步（DPS）、测试门禁、PG 迁移演练、压测基线、开关基线（Dev 口径）、worker 真机验证（P13）、越权矩阵（P14）、并发压测（P15）。
> 待闭合：生产库备份、上一版本回滚制品、发布窗口与值守、生产副本迁移预演、OpenBase 版本号与 tag 裁定、文档终审。

**发布顺序（强约束）**：

```
冻结与备份 → 生产库迁移（只增） → DPS API 2.20.2 → OpenBase 后端 → 前端
→ (可选) dps-worker → 冒烟 S1~S11 → 开关灰度（单租户试点） → 全量 → 24h 观察 → 收口
```

**总门禁 6 道**：G0 入场 → G1 备份 → G2 迁移校验 → G3 API 健康 → G4 应用金丝雀（10%→50%→100%）→ G5 开关灰度 → G6 收口与留痕。

## 1. 发布范围与版本矩阵

| 组件 | 版本/提交 | 本波发布能力 |
|---|---|---|
| DPS | **2.20.2** @ `80e88374806a6b90e1957456cc25068c5e147a0b`（tag `v2.20.2`，三远程已推送） | 组织/数据范围、PII enforce、引入落库与标注自动生成、进度模型与引擎、周期快照、调度 worker、补偿熔断、审计 enforce、画像计算任务列表与重试、E2E 修复（`retry_count` 补列/PG 删除/报表方言/JSON 掩码） |
| OpenBase 后端 | 主线 `main` @ `8985875`（`__version__=1.8.0`） | dps-proxy 新增 `orgs`/`ingest`/`progress`/`business-items`/`schedules`/`audit`/`tasks` 透传；导出补写 `log.export` 留痕（含 `total/exported_rows/truncated`） |
| OpenBase 前端 | `openbase-ui` 随 OpenBase 构建（`npm run build`） | 命名中文化、引入任务中心、任务中心四页签（引入/画像计算/数据源调度/审计日志）、画像详情业务进度 |
| 数据库 | schema `platform`（DPS）＋ `openbase`（OpenBase） | 增量 DDL：`ensure_v2_18/19/20`，**只增不删、不回退** |

变更面原则：新增能力默认关闭或 `warn`；关闭时行为与升级前一致；不做破坏性重命名；`person_id` 语义不变。

### 1.1 版本号裁定（门禁项 P11）

| 候选 | 说明 | 建议 |
|---|---|---|
| A. OpenBase 1.9.0 / openbase-ui 1.9.0 | 本波新增 7 组代理端点与多个前端页面，属功能新增 | **推荐** |
| B. 沿用 1.8.0 + 提交号 | 与既有 1.8.0（DPS 2.16.0 列车）同名，易混淆 | 不建议 |

裁定后须同步：`openbase/__init__.py`、`.devflow/project-config.json`（当前仍为 `1.4.10`，与实际不符，必须修正）、tag 与 Release Note。

## 2. 入场门禁（G0，15 项）

> 判定规则：**全部通过方可进入发布窗口**；任一未通过则不得开始阶段 E0。

| # | 检查项 | 通过标准 | 当前状态（2026-11-23 核查） |
|---|---|---|---|
| P1 | DPS 版本与标签 | `v2.20.2` 存在且三远程一致 | ✅ `refs/tags/v2.20.2` 已确认 |
| P2 | 三远程同步 | 两仓 origin/backup/github 无落后；工作区干净 | ⏳ DPS ✅（工作区 0 项）；OpenBase 有 107 项未提交/未跟踪，需分类处置 |
| P3 | 测试门禁 | 波次 A/B/C 回归、代理用例、flake8 0、前端 build 通过 | ✅ 见实施计划内版 v1.0.8 与走查报告 |
| P4 | PG 迁移演练 | 隔离库全量 3.18 s / 幂等 1.15 s；2.19→2.20 增量 0.56 s | ✅ PG 演练报告 §2 |
| P5 | 压测基线 | 36k 行、240 次单周期 P50 69 ms / P95 113 ms（跨机 LAN） | ✅ PG 演练报告 §3 |
| P6 | 开关基线 | `PII=enforce`、`DATA_SCOPE=off`、`INGEST_PERSIST=false`、`PROGRESS=false`、`SCHEDULER=false`、`AUDIT_RETENTION_DAYS=180` | ✅ Dev 口径；生产下发后用 `verify_production_switches.py --env-file` 复核 |
| P7 | 生产库备份 | 全量备份完成且可恢复校验通过，记录时间点 | ⛔ 窗口内执行（E0） |
| P8 | 回滚制品 | DPS 2.20.1 / 2.19.0 与 OpenBase 上一版本制品可用，旧实例未被覆盖 | ⛔ 待准备 |
| P9 | 窗口与值守 | 低峰窗口、通知已发、值守人就位 | ⛔ 待定（现场参数见附录 C） |
| P10 | 迁移预演（生产副本） | 副本执行 v2.18/v2.19/v2.20 增量，记录耗时与锁等待 | ⛔ 待执行（可复用 P4 方法） |
| P11 | OpenBase 版本号与 tag | 版本号裁定（§1.1）＋ tag 创建并推送三远程 | ⛔ 待裁定 |
| P12 | 文档终审 | 实施计划/Runbook/走查报告 `[Review]` → `[Approved]` | ⛔ 未终审 |
| P13 | worker 真机验证 | 心跳、正常触发、双实例 advisory lock、失败熔断、重启续跑、保留期清理 | ✅ 2026-11-23 隔离库 7/7 通过（§7.4） |
| P14 | 越权矩阵 | `DPS_DATA_SCOPE_MODE=warn` 下 self/org/org_subtree/all 用例矩阵通过 | ✅ 2026-11-23 warn 4 例 + enforce 6 例 + 接线 3 例通过（§7.4） |
| P15 | 并发压测 | 生产口径并发（多租户、真实数据量）无 5xx、P95 达标 | ✅ 2026-11-23 8 路并发 240 次进度计算 P95 30.5 ms、40 次列表查询 P95 17.75 ms（§7.4） |

## 3. 发布组织与职责

| 角色 | 职责 | 门禁签署 |
|---|---|---|
| 发布负责人 | 指挥窗口、决策回滚、对外沟通 | G0/G4/G6 |
| DBA | 备份、迁移执行、SQL 校验、连接数与锁监控 | G1/G2 |
| DPS 后端 | DPS 制品替换、健康检查、worker 启停 | G3 |
| OpenBase 后端/前端 | 应用部署、金丝雀放量、代理链路核验 | G4 |
| 测试 | 冒烟 S1~S11、页面走查、证据留档 | G5 前复核 |
| 业务验收 | 试点租户功能确认 | G5 结束 |
| 值守 | 24h 指标观察、告警响应 | G6 |

## 4. 发布窗口与时间轴（相对 T0）

| 时点 | 动作 | 责任人 |
|---|---|---|
| T-1 天 | 入场门禁 15 项复核；生产副本迁移预演；回滚制品确认 | 发布负责人/DBA |
| T0-60 min | 冻结两仓 main；发布通知；值守就位 | 发布负责人 |
| T0 | 生产库全量备份 + 配置快照（G1） | DBA |
| T0+15 min | DPS 迁移执行与校验（G2） | DBA |
| T0+30 min | DPS API 2.20.2 替换与健康检查（G3） | DPS 后端 |
| T0+50 min | OpenBase 后端部署 + 前端制品发布 | OpenBase 后端/前端 |
| T0+70 min | 金丝雀 10% 放量（G4） | OpenBase 后端 |
| T0+100 min | 冒烟 S1~S11 全量执行 | 测试 |
| T0+120 min | 50% → 全量 | 发布负责人 |
| T0+150 min | 开关灰度第 1 步（单租户） | 发布负责人 |
| T+24 h | 观察结论 → 继续灰度或回滚 | 值守/发布负责人 |
| T+72 h | 收口：文档、tag、复盘（G6） | 发布负责人 |

> 以上时长为建议值，实际以现场发布单为准；任一门禁未通过则就地停止并按 §8 处置。

## 5. 分阶段执行步骤

### 阶段 E0：冻结与备份（G1）

1. 冻结 DPS 与 OpenBase 的 `main`，禁止窗口内合并。
2. 生产库全量备份，记录备份文件、时间点与校验值；执行一次恢复校验。
3. 记录当前运行制品版本与配置快照（DPS `2.20.1`、OpenBase 上一版本、前端制品哈希）。

### 阶段 E1：数据库迁移（G2）

1. 确认生产 DSN 与 schema（`platform` / `openbase`）指向正确实例。
2. 由 DPS 2.20.2 启动时执行幂等迁移（`ensure_v2_18/19/20`），不手工拼 DDL。
3. 结构校验（附录 B-1~B-3），期望行数一致。
4. 再次执行迁移，确认 `columns_added` 为空（幂等）。
5. 记录耗时、锁等待、连接数。

### 阶段 E2：DPS API（G3）

1. 替换为 DPS 2.20.2 制品并启动 API。
2. `GET /health` 2xx；`GET /health/readiness` 数据库健康。
3. 只读验证：画像列表、画像详情、模板列表、标注队列各取一页，响应与升级前一致。
4. 观察 5 分钟：错误率、P95、数据库连接数无异常上升。

### 阶段 E3：OpenBase 后端 + 前端（G4）

1. 生产环境变量核验（禁止默认/弱密钥）：

```powershell
python scripts/verify_production_switches.py --env-file .env.production --repo OpenBase
```

必须满足：`OPENBASE_ENV=production`、`OPENBASE_JWT_SECRET` ≥32 字符强随机、`OPENBASE_DB_URL` 正确、`OPENBASE_DPS_UPSTREAM_BASE` 指向 E2 实例。

2. 构建并校验制品：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1
python -m compileall openbase
cd openbase-ui; npm run build
```

3. 金丝雀部署（默认端口 8765，按现场覆盖）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_pro.ps1 -Env pro -Strategy canary -Port 8765 -Version <OpenBase 版本>
```

4. 验证顺序：登录 → 画像列表 → 画像详情 → 模板 → 标注 → 引入任务 → 任务中心 → 审计日志。
5. 放量：10% → 观察 15 分钟 → 50% → 观察 15 分钟 → 100%。

### 阶段 E4：dps-worker（默认不启动）

> 仅当 `DPS_PROGRESS_ENABLED=true` 且调度数据已配置时启动。
> **注意：worker 启停脚本位于 DPS 仓**（`DPS/scripts/service-orchestrator.ps1`），不在 OpenBase 仓。

```powershell
# 工作目录：DPS 仓根
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 start  dps-worker
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 status dps-worker
```

心跳校验：`platform.worker_heartbeat` 中 `worker_name='dps-worker'` 持续更新（附录 B-4）。

### 阶段 E5：开关灰度（G5）

按 §6 矩阵逐项开启，每步观察不少于 30 分钟，异常即回退该开关。

### 阶段 E6：冒烟（§7）

S1~S11 全量执行；导出审计用 `scripts/verify_export_audit.py` 真机复核（10/10）。

### 阶段 E7：观察与收口（G6）

24h 指标观察（§9）；72h 内完成 §11 交付物与三远程推送。

## 6. 开关灰度矩阵

| 顺序 | 开关 | 灰度值 | 试点范围 | 观察指标 | 回退动作 |
|---|---|---|---|---|---|
| 1 | `DPS_DATA_SCOPE_MODE` | `off` → `warn` | 单租户 | 越权空集、无 500、日志可定位 | 置 `off` |
| 2 | `DPS_INGEST_PERSIST_ENABLED` | `false` → `true` | 单租户 | 引入成功率、错误行脱敏、幂等 | 置 `false` |
| 3 | `DPS_PROGRESS_ENABLED` | `false` → `true` | 试点 1–2 类事项 | 进度 P95 ≤200 ms、快照行数 | 置 `false`（接口回 409） |
| 4 | `DPS_SCHEDULER_ENABLED` | `false` → `true` | 全部 | 触发次数、`failure_count`、心跳 | 置 `false` 并停 worker |

前置约束：第 3 步前须完成 P13 worker 验证；第 1 步前须完成 P14 越权矩阵。

## 7. 冒烟与验证清单

### 7.1 接口级

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
| S11 | 导出后查 OpenBase `audit_logs(action='log.export')` | 1 条，`request_id` 对齐，`row_count/total/truncated` 齐全 |

### 7.2 页面级

- 画像列表：中文名优先、编码展示、筛选正常；
- 画像详情：「业务进度」卡片关闭时提示、开启后展示趋势与事项；
- 引入任务：列表、详情、映射、错误 CSV（脱敏）；
- 任务中心：引入任务 / 画像计算任务（列表+重试）/ 数据源调度（编辑+立即执行）/ 审计日志（动作筛选）；
- 组织树选择与数据范围切换（试点租户）。

### 7.3 运维级与脚本

```powershell
# 导出审计真机验证（发布后冒烟 S11）
$env:OPENBASE_BASE_URL = "http://<生产 OpenBase>"
$env:DATABASE_URL = $env:POSTGRES_URL
python scripts/verify_export_audit.py
```

- worker 心跳持续更新；`datasource_schedule.last_status` 正常；
- 连续失败达阈值时调度自动停用且可见；
- 审计保留期任务每日执行一次（日志含 `removed=`）。

### 7.4 P13~P15 真机验证结论（2026-11-23）

环境：一次性隔离库 `dps_prod_gate_probe_20261123`（局域网共享 PG 14.23），DPS 2.20.2，验证结束已删除；证据 `doc/test/evidence/portrait-waves/prod-gates/prod-gates-20261123-225535.json`（**12/12 PASS**）。

| # | 验证项 | 实测结果 |
|---|---|---|
| P13-1 | 心跳 | `last_seen_at` 00:05:00 → 00:05:10 持续更新 |
| P13-2 | 正常触发 | `executed=1`，`last_status=success`，`next_run_at` 推进至 01:00 |
| P13-3 | 双实例并发 | 两次并发 `run_once`：`executed_total=1`、执行器调用 1 次，无重复执行 |
| P13-4 | advisory lock | 持有连接时他连接获取失败；连接归还后锁释放、可再获取 |
| P13-5 | 失败熔断 | `failure_count` 1→2，`enabled` true→false，之后轮次 `scanned=0` |
| P13-6 | 重启续跑 | 超时 `running` 任务 `requeued=1` → `pending`、`retry_count=1` |
| P13-7 | 保留期清理 | 过期审计行删除，新行保留 |
| P14-1 | warn 矩阵 | all/org/org_subtree/self 均 4/4 不拦截，逐范围产生 `DATA_SCOPE_WOULD_LIMIT` |
| P14-2 | enforce 反证 | all=4、org A=2、subtree A=3、org B=1、self=1、越权组织=0 |
| P14-3 | 身份头接线 | operator→`org_subtree`、admin→`all`、未知角色→`org` |
| P15-1 | 并发进度计算 | 36,000 行造数 5.4 s；8 路并发 240 次：P50 17.43 / P95 30.5 / P99 96.2 / max 113.94 ms，错误 0，快照 240 行 |
| P15-2 | 并发列表查询 | 8 路并发 40 次：P50 7.36 / P95 17.75 / max 18.85 ms，错误 0 |

**口径说明**：

1. worker 的“同步执行器”为替身（stub），但数据库状态机、条件更新抢占、advisory lock、心跳、任务恢复与审计清理均执行真实代码。
2. 双实例互斥实测由 `UPDATE ... WHERE next_run_at = ?` 条件更新保证；advisory lock 在连接归还连接池时被 asyncpg 会话重置释放，因此**不得把 advisory lock 作为唯一互斥依据**（P13-3 证明当前实现无重复执行）。
3. 隔离库已删除，共享库既有库未写入；脚本为一次性验证脚本，未纳入仓库。

## 8. 回滚决策

> 原则：**先关开关 → 再停 worker → 再回切应用版本 → 最后才考虑数据修复**；DDL 不回退。

| 级别 | 触发条件 | 动作 | 验证 |
|---|---|---|---|
| L1 能力回退 | 进度/调度/引入单点异常 | 对应开关置 `false` | 对应接口 409；既有画像功能正常 |
| L2 权限回退 | 数据范围误伤/越权 | `DATA_SCOPE=off`；必要时 `PII=warn` | 列表恢复全量口径；导出恢复 |
| L3 调度停机 | worker 异常/重复执行 | 停止 `dps-worker`（DPS 仓脚本） | 调度停摆但 API 正常；无重复任务 |
| L4 应用回切 | API/前端严重故障 | OpenBase 蓝绿回切上一版本；DPS 回退 2.20.1 或 2.19.0 制品 | 登录与核心页面可用 |

数据处置：`progress_snapshot` / `profile_history(snapshot_type='progress')` 默认保留；确需清理时按 `tenant_id + person_id + period_key` 定点删除，双人复核并留审计。

回滚决策人：发布负责人；L4 需项目负责人共同签字。

## 9. 监控与观察（发布后 24/72 小时）

| 指标 | 阈值/期望 | 处置 |
|---|---|---|
| HTTP 5xx 比例 | 不高于发布前基线 | 超阈值触发 L4 |
| 画像列表/详情 P95 | 无明显劣化 | 定位慢查询/索引 |
| 进度计算 P95（开启后） | ≤200 ms | 超阈值关闭进度开关并排查 |
| worker 心跳延迟 | ≤3 个轮询周期 | 重启 worker / 查日志 |
| `datasource_schedule.failure_count` | 不持续增长 | 达阈值自动停用，人工修复后再启用 |
| 审计表增长 | 日增量可预期 | 核对 `DPS_AUDIT_RETENTION_DAYS=180` |
| 数据库连接数/锁等待 | 无持续升高 | 检查迁移/长事务 |

## 10. 风险登记

| # | 风险 | 影响 | 应对 |
|---|---|---|---|
| R1 | 生产副本迁移预演未做，锁等待未知 | 迁移阻塞业务 | P10 必须先行；超时则延窗 |
| R2 | worker 首次真机运行 | 调度异常/重复执行 | 已由 P13 验证（心跳/触发/熔断/续跑/无重复）；异常仍走 L3 |
| R3 | `data_scope=warn` 越权误判 | 越权或误伤可见性 | 已由 P14 验证（warn 4 例 + enforce 6 例）；异常走 L2 |
| R4 | 生产并发高于压测口径 | P95 劣化 | 已由 P15 验证（P95 30.5 ms / 列表 17.75 ms）；生产窗口按 §9 继续观察 |
| R5 | OpenBase 工作区 107 项未提交混入制品 | 制品不可复现 | 发布前分类处置并打 tag |
| R6 | 版本号与 project-config 不一致 | 追溯混乱 | P11 裁定并修正 |
| R7 | 回滚制品缺失 | 无法回切 | P8 逐项确认并记录路径 |
| R8 | 开关下发遗漏（fail-closed 启动被拒） | 发布失败 | `verify_production_switches.py` 前置校验 |

## 11. 交付物与留痕（发布后）

| 交付物 | 位置/动作 | 责任人 |
|---|---|---|
| 部署执行报告 | `doc/release/OpenBase-部署执行与上线检查报告-v{版本}.md` | OpenBase 后端 |
| 上线检查报告 | 同上（含监控与告警配置） | 值守 |
| 发布复盘与问题跟踪记录 | `doc/release/OpenBase-发布复盘与问题跟踪记录-v{版本}.md` | 发布负责人 |
| Release Note（单版＋汇总） | `doc/release/OpenBase-Release-Note-v{版本}.md`、`-All.md` | 发布负责人 |
| 版本控制记录 | tag 创建/推送（origin/backup/github）、回滚操作留痕 | 发布负责人 |
| `.devflow/project-config.json` | `version`/`lastRelease` 更新为本次版本 | 发布负责人 |
| 运维审计报告 | `doc/audit/comprehensive/`（按技能要求） | 审计 |
| 三远程推送 | 两仓文档与 tag 全部同步 | 发布负责人 |

## 12. 人工门禁批准点

| 门禁 | 时点 | 批准人 | 未通过处理 |
|---|---|---|---|
| GL-0 | 入场 15 项复核后 | 发布负责人 + 项目负责人 | 补齐后重审 |
| GL-1 | 备份与配置快照后 | DBA + 发布负责人 | 重做备份 |
| GL-2 | 迁移校验后 | DBA + DPS 后端 | 停止，评估数据修复 |
| GL-3 | DPS 健康检查后 | DPS 后端 + 发布负责人 | 回退 DPS 制品 |
| GL-4 | 金丝雀 10% 观察后 | 发布负责人 | 回切上一版本 |
| GL-5 | 每次开关灰度后 | 发布负责人 + 业务验收 | 关闭该开关 |
| GL-6 | 72h 收口 | 项目负责人 | 延期观察/回滚 |

## 附录 A：命令速查

```powershell
# OpenBase 构建与部署（金丝雀/蓝绿）
powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1
powershell -ExecutionPolicy Bypass -File scripts/deploy_pro.ps1 -Env pro -Strategy canary -Port 8765 -Version <版本>

# 生产开关矩阵核验（env-file 模式，禁止发布前必须 0 FAIL）
python scripts/verify_production_switches.py --env-file .env.production --repo OpenBase

# DPS worker 启停与状态（工作目录：DPS 仓根）
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 start  dps-worker
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 status dps-worker
powershell -ExecutionPolicy Bypass -File scripts/service-orchestrator.ps1 stop   dps-worker

# 导出审计真机验证（S11）
python scripts/verify_export_audit.py

# 三远程同步核对（两仓分别执行）
git status
git log --oneline -1 origin/main; git log --oneline -1 backup/main; git log --oneline -1 github/main
```

## 附录 B：SQL 校验

```sql
-- B-1 迁移表存在（期望 4 行）
SELECT table_name FROM information_schema.tables
WHERE table_schema='platform'
  AND table_name IN ('business_item','progress_snapshot','datasource_schedule','worker_heartbeat');

-- B-2 profile_history 周期快照列（期望 4 行）
SELECT column_name FROM information_schema.columns
WHERE table_schema='platform' AND table_name='profile_history'
  AND column_name IN ('period_type','period_key','snapshot_type','template_code');

-- B-3 业务进度模板（期望 2 行：business_progress / business_progress_detail）
SELECT code FROM platform.portrait_template WHERE profile_type='business';

-- B-4 worker 心跳
SELECT worker_name, last_seen_at FROM platform.worker_heartbeat;

-- B-5 调度状态
SELECT id, datasource_id, enabled, last_status, failure_count, next_run_at
FROM platform.datasource_schedule ORDER BY updated_at DESC LIMIT 20;

-- B-6 进度快照规模
SELECT period_type, COUNT(*) FROM platform.progress_snapshot GROUP BY period_type;

-- B-7 导出留痕（OpenBase schema）
SELECT action, source, row_count, request_id, created_at
FROM openbase.audit_logs WHERE action='log.export' ORDER BY created_at DESC LIMIT 10;
```

## 附录 C：现场待填参数（发布负责人填写后才能开窗）

| 参数 | 值 |
|---|---|
| 生产 OpenBase 地址/端口 | |
| 生产 DPS 地址/端口 | |
| 生产库 DSN 与 schema | |
| 制品仓库路径/版本号 | |
| 备份路径与校验值 | |
| 发布窗口（开始/结束） | |
| 试点租户 | |
| 值守名单与联络方式 | |
| 回滚制品存放路径 | |
