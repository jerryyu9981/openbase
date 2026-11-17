# OpenBase P-01/P-02 首屏冷启动与图投影编排优化 — 技术规格

| 项目 | 内容 |
| --- | --- |
| 文档版本 | 1.0.1 |
| 状态 | [Review] |
| 适用环境 | Dev（本机四系统联调：Windows PowerShell 5+） |
| 需求来源 | 《OpenBase-前端全站走查报告-v1.0.0》P-01 / P-02 |
| 作者 | 架构师 / 开发者 |
| 评审 | 技术负责人 |
| 批准 | 项目负责人 |

## 修订历史

| 版本 | 日期 | 修订人 | 说明 |
| --- | --- | --- | --- |
| 1.0.0 | 2026-11-18 | 架构师 | 初稿：P-02 worker 纳入编排（单实例锁 + 心跳）、P-01 启动预热（编排器 + DPS 进程内） |
| 1.0.1 | 2026-11-18 | 开发者 | 修正预热端点：Dashboard 走通用代理通道 `/api/v1/proxy/openllm/api/v1/monitoring/dashboard`（实测旧路径 404） |

## 1. 背景与问题

### P-01 首屏冷启动慢（3~12s）

走查实测：前端登录后首屏 KPI（Dashboard）与画像/模板页首屏在服务刚拉起时需 3~12s 才有数据。

已确认的根因：

1. DPS 模板注册表（`TemplateRegistry`）为**请求路径惰性单例**：`routes_profiles._get_template_registry()` 首次请求才 `TemplateRegistry()`，随后首次 `load()` 才执行 `SELECT ... FROM portrait_template`；冷启动时叠加 PG/Python 首次查询开销。
2. 服务健康探针只覆盖 `/health/liveness`、`/openapi.json` 等轻端点，**不覆盖**前端首屏真正依赖的重查询端点（`/dps-proxy/templates`、`/dps-proxy/portraits`、`/llm-proxy/monitoring/dashboard`）。编排器宣告"启动完成"时，这些链路仍处冷态。
3. Dashboard 的 `monitoring/dashboard` 为 OpenLLM 跨表聚合（实测冷态 4s+，偶发 502，已由 `SLOW_PATH_TIMEOUT=30s` 兜底），首次访问需建立连接与执行计划缓存。

### P-02 图投影 worker 未纳入编排

走查实测：编排器 `-Action start` 只拉起 openmemory 服务本体（`scripts/start_openmemory.py`），**未启动** `scripts/graph_projection_worker.py`。结果 `graph_outbox` 只增不减（pending 3057；人工 `--once` 后降至 2860，节点 5/边 3），记忆图谱长期空图。

同时 worker 自身缺少：

- 单实例互斥：重复启动会产生多个消费者（虽投影幂等，但放大 Neo4j 写压与轮询开销）；
- 存活心跳：编排器无法判断 worker 存活/卡死。

## 2. 目标与范围

### 目标

| 编号 | 目标 | 可验证指标 |
| --- | --- | --- |
| G1 | 编排器一键启动即拉起图投影 worker，且全局仅一个实例 | `status` 出现 `openmemory-graph-worker` 健康；重复启动第二实例在 30s 内退出并记录锁冲突日志 |
| G2 | worker 可被编排器启停/自愈/体检 | `stop` 后无 `graph_projection_worker.py` 残留进程；`monitor` 能在心跳失效后拉起 |
| G3 | 图投影积压持续下降 | 启动后 60s 与 120s 两次采样 `openmemory_graph_outbox_pending` 单调下降 |
| G4 | 服务"启动完成"时首屏依赖链路已预热 | 预热后首次 `templates` < 3s、`portraits` < 2s、`monitoring/dashboard` < 3s |
| G5 | DPS 启动即完成模板注册表加载 | DPS 启动日志出现 `画像模板注册表预热完成`；首请求命中已加载缓存 |

### 非目标（本轮不做）

- 不做代理层（OpenBase → OpenLLM）Dashboard 聚合结果缓存：涉及跨租户缓存键与失效语义，收益低于风险；仅在预热后仍不达标（`monitoring/dashboard` 首访 > 3s）时另立任务。
- 不做主备库数据面同步（走查已挂起项）。
- 不改变现有端口分配、健康端点语义与 A/B 通道契约。
- 不引入新依赖、不改数据库 Schema。

## 3. 方案设计

### 3.1 P-02-A：worker 单实例锁 + 心跳

#### 3.1.1 `OpenMemory/src/openmemory/storage/relational_store.py`

1. 在 `sqlalchemy` 导入清单中补充 `text`。
2. 在 `close()` 之后新增方法（数据访问留在存储层，脚本不直连 SQL）：

```python
async def try_acquire_session_lock(self, lock_key: str) -> Any | None:
    """尝试获取 PostgreSQL 会话级 advisory lock（worker 单实例互斥）。

    成功返回**持锁连接**；调用方必须保持连接打开（关闭即释放）。
    锁被其它连接持有时返回 None；非 PostgreSQL 方言/执行失败抛异常，由调用方降级。
    """
    if self._engine is None:
        raise RelationalStoreError("Store not initialized. Call initialize() first.")
    connection = await self._engine.connect()
    try:
        result = await connection.execute(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": lock_key},
        )
        if bool(result.scalar()):
            return connection
    except Exception:
        await connection.close()
        raise
    await connection.close()
    return None
```

#### 3.1.2 `OpenMemory/scripts/graph_projection_worker.py`

1. 新增导入：`json`、`os`、`datetime.datetime/datetime.timezone`。
2. 新增常量：

```python
DEFAULT_HEARTBEAT_PATH = Path(__file__).resolve().parent.parent / "logs" / "graph-worker.heartbeat"
DEFAULT_LOCK_KEY = "openmemory.graph_projection_worker"
```

3. 新增 `HeartbeatWriter`（原子写，避免编排器读到半截 JSON）：

```python
class HeartbeatWriter:
    """worker 存活心跳（仅由持锁实例写入）。"""

    def __init__(self, path: Path, *, interval_seconds: float): ...
    def write(self, **fields: object) -> None:
        # payload 固定字段：service/pid/started_at/updated_at/interval_seconds
        # 写法：<path>.tmp 写入后 os.replace 原子替换；OSError 只告警不抛出
```

4. `ProjectionWorker.__init__` 新增关键字参数 `heartbeat: HeartbeatWriter | None = None`；新增私有方法 `_publish_heartbeat(*, state, pending, stats, totals)`。
5. `run_forever` 每轮（含空闲轮）在计算 `pending` 后调用 `_publish_heartbeat(state="running", pending=..., stats=..., totals=...)`；异常路径不改变既有语义。
6. `_async_main` 调整：

- `--once` 模式：**不取锁、不写心跳**（避免覆盖常驻实例心跳）；
- 常驻模式：
  1. `store.initialize()` / `graph_store.initialize()` 之后取锁
     `lock_connection = await store.try_acquire_session_lock(args.lock_key)`；
  2. 取锁异常（如非 PostgreSQL）→ `logger.warning` 后**降级继续**（不阻断投影）；
  3. 取锁返回 `None` → `logger.error("another graph projection worker holds lock ...")`，`return 0`；
  4. 取锁成功 → 创建 `HeartbeatWriter`（路径 `args.heartbeat` 或 `DEFAULT_HEARTBEAT_PATH`），先写 `state="starting"`，再注入 `ProjectionWorker`；
- `finally` 中先 `await lock_connection.close()`（释放锁），再关闭 `graph_store`/`store`。
7. CLI 新增：

```
--heartbeat PATH   心跳文件路径（常驻模式默认 <OpenMemory>/logs/graph-worker.heartbeat）
--lock-key KEY     单实例锁键（默认 openmemory.graph_projection_worker）
```

### 3.2 P-02-B：编排器支持 worker 类型

文件：`OpenBase/scripts/service-orchestrator.ps1`（不改变现有服务行为，仅新增分支）。

1. `$services` 新增条目（紧随 `openmemory`，拓扑依赖保证后启）：

```powershell
@{
    Name       = 'openmemory-graph-worker'
    Kind       = 'worker'
    Detach     = $true
    HealthWait = 60
    Cwd        = 'D:\Trae CN\myproject\Dev\OpenMemory'
    Command    = 'python'
    Args       = @('scripts\graph_projection_worker.py', '--interval', '2',
                   '--heartbeat', (Join-Path $ServiceLogDir 'openmemory-graph-worker\graph-worker.heartbeat'))
    Env        = @{ PYTHONDONTWRITEBYTECODE = '1'; PYTHONUNBUFFERED = '1' }
    Heartbeat  = (Join-Path $ServiceLogDir 'openmemory-graph-worker\graph-worker.heartbeat')
    HeartbeatMaxAgeSec = 120
    Depends    = @('openmemory')
    DepType    = 'hard'
    Desc       = 'OpenMemory 图投影 worker（graph_outbox → Neo4j）'
}
```

（不声明 `JsonStream`：worker 日志为 `logging` 文本格式，保持 `.err.log` 命名，避免日志中心按 JSONL 解析失败。）

2. 新增 `Test-WorkerHealth`：读取心跳 JSON，判定
   - 文件存在且 `age <= HeartbeatMaxAgeSec`；
   - 心跳 `pid` 对应进程仍存在；
   返回 `@{Healthy; Detail; LatencyMs; HeartbeatAgeSec; HeartbeatPid}`，`Detail ∈ {ok, no_heartbeat, stale_heartbeat, process_exited}`。
3. `Test-HealthProbe`：`$Svc.Kind -eq 'worker'` 时直接返回 `Test-WorkerHealth`（不访问 HTTP）。
4. `Format-HealthDetail`：补充 `no_heartbeat / stale_heartbeat / process_exited` 的中文文案。
5. `Get-ServiceInfraDeps`：新增 `'openmemory-graph-worker' = @('pg', 'neo4j')`。
6. `Start-Service`：
   - worker 分支跳过端口预检/`Get-PortPid`；若 `Test-WorkerHealth` 健康 → 记录 PID 并返回 `$true`（幂等）；
   - 陈旧 PID 记录（进程不存在）→ `Remove-Pid`；
   - 启动后健康等待改为等待心跳（复用同一 `HealthWait` 循环），`Test-Health` 已由第 3 步分支覆盖；
   - 等待期间若启动 PID（WMI 包装进程）已退出 → `ERROR` + `Remove-Pid` + `return $false`；
   - 超时分支不查端口，直接 WARN。
7. `Stop-Service`：worker 分支
   - 收集并终止：记录的 PID、心跳 PID、`Win32_Process` 中命令行含 `graph_projection_worker.py` 的进程；
   - 删除心跳文件；`Remove-Pid`；其余服务逻辑不变。
8. `Get-AllStatus`：worker 分支输出 `端口=-`，状态取自 `Test-WorkerHealth`（健康/未启动/心跳陈旧/进程已退出），PID 取心跳 PID。
9. `Invoke-Monitor`：worker 的 `$portPid` 视为 `$null`，宕机原因文案改为"心跳失效（<Detail>）"，沿用既有重启计数与 `MaxRestarts`。
10. `Invoke-CheckAll`：worker 分支只做心跳检查（PASS/FAIL 计入总数），不构造 `http://127.0.0.1:0` 请求。

### 3.3 P-01-A：编排器启动预热 `Invoke-StackWarmup`

文件：`OpenBase/scripts/service-orchestrator.ps1`。

1. 新增参数 `[switch]$SkipWarmup`（默认执行）。
2. `Invoke-Start`：所有目标服务启动完成后调用 `Invoke-StackWarmup -Targets $targets`（在 `Get-AllStatus` 之前）。
3. `Invoke-StackWarmup` 行为：

- 守门：`$Targets` 不含 `openbase` → 跳过；`-Only` 场景下同理跳过（避免预热未启动依赖）。
- 登录：`POST http://127.0.0.1:8000/api/v1/auth/login`，默认凭据 `admin/admin123`，可用环境变量 `OPENBASE_WARMUP_USER` / `OPENBASE_WARMUP_PASSWORD` 覆盖；失败仅 WARN，不阻断启动。
- 顺序预热（携带 `Authorization: Bearer <token>`，单端点超时 30s，失败不阻断，逐条记录耗时）：

| 序号 | 端点 | 对应首屏 |
| --- | --- | --- |
| 1 | `GET /api/v1/users` | Dashboard 平台用户数 |
| 2 | `GET /api/v1/proxy/openllm/api/v1/monitoring/dashboard?time_range=24h` | Dashboard KPI（最慢，优先） |
| 3 | `GET /api/v1/dps-proxy/templates` | 画像模板族管理 |
| 4 | `GET /api/v1/dps-proxy/portraits` | 画像列表/总览 |
| 5 | `GET /api/v1/rag-proxy/collections` | 知识库控制台 |
| 6 | `GET /api/v1/memory-proxy/memories` | 记忆管理 |

- 汇总：日志输出每端点 `elapsed_ms` 与 `status`；写入证据 `doc/test/evidence/ops/startup-warmup-<yyyyMMdd-HHmmss>.json`（字段：`schema_version/action/generated_at/login_ok/items[{name,url,status,elapsed_ms,ok}]/total_elapsed_ms`）。
- 返回值：全部成功 → `$true`；任意失败 → `$false`（仅用于日志/状态，不影响退出码）。

### 3.4 P-01-B：DPS 进程内启动预热

文件：`DPS/src/rest_api/app.py`。

1. 新增函数（紧随 `_warmup_redis`）：

```python
async def _warmup_template_registry(db) -> None:
    """启动预热：DB 连通性 + 画像模板注册表加载（P-01 首屏冷启动）。

    失败仅告警，不阻塞启动：请求路径仍保留 is_loaded() 惰性加载兜底。
    """
    if not db.initialized:
        return
    try:
        await db.fetch_all("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        logger.warning("数据库连通性预热失败（请求路径兜底）: %s", exc)
    try:
        from engines.portrait.template_registry import TemplateRegistry
        from rest_api.routes.routes_profiles import _get_template_registry

        registry = _get_template_registry()
        if not registry.is_loaded():
            result = await registry.load()
            logger.info("画像模板注册表预热完成: %s", result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("画像模板注册表预热失败（请求路径惰性加载兜底）: %s", exc)
```

（`TemplateRegistry` 导入用于显式失败定位；实际实例复用 `routes_profiles` 单例，确保预热结果被请求路径命中。）

2. `lifespan` 在 `_wire_tenant_middleware(db)` 之后、`_warmup_redis()` 之前调用 `await _warmup_template_registry(db)`。

### 3.5 P-01-C：Dashboard 聚合性能口径（本轮仅预热）

- 本轮不引入代理层缓存；以 3.3 的 `monitoring/dashboard` 预热覆盖冷启动。
- 验收后若首访仍 > 3s，另立任务评估：OpenBase 代理层 15s TTL 只读缓存（键含 `path+query+tenant/org+token 摘要`）或 OpenLLM 侧轻量 KPI SQL。

## 4. 契约定义

### 4.1 心跳文件（`graph-worker.heartbeat`，JSON）

```json
{
  "service": "openmemory-graph-worker",
  "pid": 12345,
  "started_at": "2026-11-18T10:00:00+00:00",
  "updated_at": "2026-11-18T10:00:02+00:00",
  "interval_seconds": 2.0,
  "state": "running",
  "pending": 2860,
  "last_batch": {"claimed": 200, "ok": 200, "failed": 0, "memories": 200, "entities": 0},
  "totals": {"ok": 197, "failed": 0, "memories": 197, "entities": 0}
}
```

判定：`updated_at`（以文件 mtime 为准，容忍时钟偏差）≤ 120s 且 `pid` 进程存在 → 健康。

### 4.2 单实例锁

- 键：`openmemory.graph_projection_worker`（可用 `--lock-key` 覆盖）。
- 实现：`pg_try_advisory_lock(hashtext(:lock_key))`，会话级；连接关闭即释放。
- 冲突行为：第二实例记录 ERROR 后以退出码 0 退出（不进入重启风暴）。

### 4.3 预热证据

- 路径：`doc/test/evidence/ops/startup-warmup-<yyyyMMdd-HHmmss>.json`
- 字段：见 3.3；`ok=false` 的条目必须保留 `status` 或 `error`，便于定位失败链路。

## 5. 兼容性与回滚

| 变更 | 兼容性 | 回滚 |
| --- | --- | --- |
| worker 锁/心跳 | `--once` 行为不变；无心跳文件时编排器按"未启动"处理 | 移除服务条目即可回到原状 |
| 编排器 worker 类型 | 现有服务无 `Kind` 字段，全部走原分支 | 删除新条目与分支 |
| 启动预热 | 新增 `-SkipWarmup` 可完全关闭；失败不阻断启动 | 使用 `-SkipWarmup` |
| DPS 预热 | 失败仅 WARN，`is_loaded()` 惰性加载兜底 | 删除 `_warmup_template_registry` 调用 |

## 6. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| advisory lock 在非 PG 方言不可用 | worker 无法互斥 | 异常降级为无锁并 WARN（当前生产统一 PG） |
| 心跳文件残留导致误判健康 | 编排器不重启已死 worker | 健康判定同时校验 `pid` 进程存在；`stop` 删除心跳 |
| 预热拖慢启动 | 启动耗时增加（预计 3~6s） | 单端点 30s 超时、失败不阻断、可 `-SkipWarmup` |
| 证据文件频繁写 | 目录膨胀 | 仅在 start/startcheck 写；每轮一个文件 |
| worker 与 openmemory 共用 DB 连接池压力 | 轻微 | 独立进程独立池；批次上限沿用 `worker_batch_size=200` |

## 7. 验证方案

### 7.1 静态与单测

| 仓库 | 命令 | 通过标准 |
| --- | --- | --- |
| OpenMemory | `python -m pytest tests/unit/test_graph_projection.py tests/unit/test_graph_projection_worker_lock.py tests/unit/test_relational_store.py -q` | 全通过 |
| OpenMemory | `python -m ruff check scripts/graph_projection_worker.py src/openmemory/storage/relational_store.py tests/unit/test_graph_projection_worker_lock.py` | 0 error |
| DPS | `python -m pytest src/tests/test_startup_warmup.py -q` | 全通过 |
| OpenBase | `.venv-test\Scripts\python.exe -m ruff check openbase tests` | 0 error |
| OpenBase | `.venv-test\Scripts\python.exe -m pytest tests -q` | 全通过（或与变更前基线一致） |

新增单测：

- `OpenMemory/tests/unit/test_graph_projection_worker_lock.py`
  1. `HeartbeatWriter.write` 产出可解析 JSON 且字段齐全（`pid/updated_at/state/pending`）；
  2. `ProjectionWorker.run_forever` 每轮调用心跳回调（fake store 返回 0 事件，跑 2 轮后停止）；
  3. 锁被占用（fake store 返回 `None`）→ `_async_main` 不进入消费循环并返回 0；
  4. `--once` 不调用 `try_acquire_session_lock`。
- `DPS/src/tests/test_startup_warmup.py`
  1. `_warmup_template_registry` 在 `db.initialized=True` 时执行 `SELECT 1` 并调用注册表 `load()`；
  2. `load()` 抛异常时函数不抛出（只告警）；
  3. `db.initialized=False` 时直接返回。

### 7.2 编排与端到端

1. `. \scripts\service-orchestrator.ps1 -Action stop`
2. `. \scripts\service-orchestrator.ps1 -Action startcheck`（观察预热日志与证据文件）
3. `. \scripts\service-orchestrator.ps1 -Action status` → `openmemory-graph-worker` 显示健康，`端口=-`，PID=心跳 PID
4. 单实例验证：另起终端直接运行 `python scripts\graph_projection_worker.py --interval 2 --heartbeat logs\graph-worker.dup.heartbeat` → 30s 内退出，日志含 `holds lock`
5. 积压验证：间隔 60s 两次读取 `http://127.0.0.1:9101/metrics` 的 `openmemory_graph_outbox_pending`，第二次 < 第一次
6. 停止验证：`-Action stop` 后 `Get-CimInstance Win32_Process` 过滤 `graph_projection_worker.py` 为空
7. 首屏验证（登录后带 token 计时）：
   - `GET /api/v1/dps-proxy/templates` < 3s
   - `GET /api/v1/dps-proxy/portraits` < 2s
   - `GET /api/v1/proxy/openllm/api/v1/monitoring/dashboard?time_range=24h` < 3s
8. DPS 日志含 `画像模板注册表预热完成`，且首访后不出现二次 `模板注册表预热完成`（说明命中缓存，而非每请求 load）

## 8. 交付物

- 代码：`OpenMemory/scripts/graph_projection_worker.py`、`OpenMemory/src/openmemory/storage/relational_store.py`、`OpenMemory/tests/unit/test_graph_projection_worker_lock.py`、`OpenBase/scripts/service-orchestrator.ps1`、`DPS/src/rest_api/app.py`、`DPS/src/tests/test_startup_warmup.py`
- 证据：`OpenBase/doc/test/evidence/ops/startup-warmup-*.json`、图谱 pending 采样与首屏计时
- 回填：走查报告 P-01/P-02 状态更新为"已修复（v1.0.0 实现）"

## 9. 审批

- [ ] 技术负责人：方案与风险认可
- [ ] 项目负责人：批准进入实现
