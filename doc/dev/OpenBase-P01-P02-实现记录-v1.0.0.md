# OpenBase P-01/P-02 实现记录

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.0.0 |
| 状态 | [Approved] |
| 适用环境 | Dev（Windows PowerShell 5+，四系统联调） |
| 关联规格 | `doc/spec/p01-p02-startup-hardening/spec.md` v1.0.1 |
| 任务清单 | `doc/spec/p01-p02-startup-hardening/tasks.md` |
| 关联报告 | `doc/test/OpenBase-前端全站走查报告-v1.0.0.md` v1.1.0 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-18 |

### 修订历史

| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-18 | P-02（worker 纳入编排 + 单实例锁 + 心跳）、P-01（编排器预热 + DPS 进程内预热）实现与验证 | AI 编码代理 |

## 1. 变更清单

### 1.1 OpenMemory

| 文件 | 变更 |
|---|---|
| `src/openmemory/storage/relational_store.py` | 新增 `try_acquire_session_lock(lock_key)`：PG 会话级 advisory lock，成功返回持锁连接，占用返回 `None`，异常关连接后抛出 |
| `scripts/graph_projection_worker.py` | 新增 `HeartbeatWriter`（`tmp` + `os.replace` 原子写）；`ProjectionWorker` 注入心跳并每轮发布；`_prepare_single_instance` 统一处理锁/心跳/`--once`；新增 `--heartbeat`、`--lock-key` |
| `tests/unit/test_graph_projection_worker_lock.py` | 新增 4 条用例：心跳载荷、逐轮心跳、锁冲突退出、`--once` 不取锁 |

### 1.2 DPS

| 文件 | 变更 |
|---|---|
| `src/rest_api/app.py` | 新增 `_warmup_template_registry(db)`；`lifespan` 在 `_wire_tenant_middleware` 后调用（`SELECT 1` + `TemplateRegistry.load()`，复用请求路径单例） |
| `src/tests/test_startup_warmup.py` | 新增 3 条用例：正常预热、加载失败不抛出、DB 未初始化跳过 |

### 1.3 OpenBase

| 文件 | 变更 |
|---|---|
| `scripts/service-orchestrator.ps1` | 新增 `Kind='worker'` 分支（`Test-WorkerHealth`、Start/Stop/Status/Monitor/CheckAll）；新增 `openmemory-graph-worker` 服务与解释器映射；新增 `-SkipWarmup` 与 `Invoke-StackWarmup`（登录 + 6 端点 + 证据 JSON） |
| `doc/spec/p01-p02-startup-hardening/*` | 规格、任务、验证检查单 |
| `doc/test/OpenBase-前端全站走查报告-v1.0.0.md` | 升 v1.1.0，P-01/P-02 标记已修复并附证据 |

## 2. 与规格的偏差

| 项 | 规格 | 实现 | 原因 |
|---|---|---|---|
| 预热 Dashboard 端点 | `/api/v1/llm-proxy/monitoring/dashboard` | `/api/v1/proxy/openllm/api/v1/monitoring/dashboard` | 实测旧路径 404；前端 `OPENLLM = '/proxy/openllm/api/v1'` 走通用代理通道 |
| 锁/心跳准备 | `_async_main` 内直接处理 | 抽出 `_prepare_single_instance` 返回 `(锁连接, 心跳, 是否继续)` | 行为一致且可单测（覆盖锁冲突/`--once`） |
| Dashboard 聚合缓存 | 本轮仅预热 | 同规格 | 6 端点实测均 < 1s，未触发另立缓存任务条件 |

## 3. 验证记录

| 项 | 命令/方式 | 结果 |
|---|---|---|
| OpenMemory 单测 | `D:\venvs\openmemory\Scripts\python.exe -m pytest tests/unit/test_graph_projection_worker_lock.py tests/unit/test_graph_projection.py tests/unit/test_relational_store.py -q` | 64 passed |
| OpenMemory 静态 | `ruff check scripts/graph_projection_worker.py src/openmemory/storage/relational_store.py tests/unit/test_graph_projection_worker_lock.py` | All checks passed |
| DPS 单测 | `.venv\shim311\python.cmd -m pytest src/tests/test_startup_warmup.py -q` | 3 passed |
| 编排脚本语法 | `[Parser]::ParseFile(...)` | 无错误 |
| worker 启动 | `-Action start -Only openmemory-graph-worker` | 心跳就绪 ✅ PID 11420（无端口，6s） |
| 单实例 | 另起常驻实例 | 日志 `another graph projection worker holds lock`，退出码 0，未写重复心跳 |
| 积压 | `http://127.0.0.1:9101/metrics` | pending 2860→0，dead 0，`events_total{ok}=2860` |
| 停止 | `-Action stop -Only openmemory-graph-worker` | 残留 python 进程 0，心跳文件删除 |
| 预热 | 全量 `-Action start` | 6 端点全 200：用户 349ms / Dashboard 723ms / 模板 599ms / 画像 318ms / 知识库 281ms / 记忆 454ms，总 3126ms |
| DPS 预热日志 | `logs/dps/dps-20261118.err.jsonl` @ `2026-11-17T18:49:23.159Z` | `loaded: 5`（codes: `cor-persona-assess/intake/risk/root-v1`、`dps-correction-v1`） |

证据：

- `doc/test/evidence/ops/startup-warmup-20261118-025109.json`
- `doc/test/evidence/ops/p01-p02-verify-20261118.json`

## 4. 风险与后续

- 心跳陈旧但进程存活（事件循环卡死）：`monitor` 会尝试重启，新实例被 advisory lock 拒绝并退出；该场景会体现在重启计数与日志中，需要人工介入排查卡死原因。
- 日志链路中文乱码（`dps-*.err.jsonl` 双重编码）为既有问题，不影响本次预热判定，建议另立任务修复日志编码。
- Dashboard 代理层缓存仍为待评估项，触发条件：预热后首访 > 3s。
