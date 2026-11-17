# P-01/P-02 实现任务清单（tasks）

- 依据：[spec.md](./spec.md) v1.0.0
- 状态：待批准后执行
- 执行纪律：批准后单轮连续推进（实现 → 验证 → 证据 → 回填 → 提交/推送），仅门禁失败才中断回问。

## T1 存储层：会话级 advisory lock

- [x] `OpenMemory/src/openmemory/storage/relational_store.py`
  - 导入 `text`
  - 新增 `try_acquire_session_lock(lock_key)`（成功返回持锁连接，占用返回 `None`，异常关闭连接后抛出）
- 验收：`ruff` 0 error；`tests/unit/test_relational_store.py` 通过

## T2 worker：心跳与单实例

- [x] `OpenMemory/scripts/graph_projection_worker.py`
  - `HeartbeatWriter`（原子写 JSON）
  - `ProjectionWorker` 注入可选 heartbeat，`run_forever` 每轮写心跳
  - `_async_main`：常驻模式取锁；占用则 ERROR + 退出 0；异常降级 WARN；`--once` 不取锁不写心跳
  - CLI：`--heartbeat`、`--lock-key`
- [x] `OpenMemory/tests/unit/test_graph_projection_worker_lock.py`（4 条用例，见 spec §7.1）
- 验收：新增/既有单测通过，`ruff` 0 error（64 passed；ruff All checks passed）

## T3 编排器：worker 类型

- [x] `OpenBase/scripts/service-orchestrator.ps1`
  - `$services` 新增 `openmemory-graph-worker`（`Kind='worker'`、`Heartbeat`、`HeartbeatMaxAgeSec=120`、`Depends=@('openmemory')`）
  - `Get-ServiceInfraDeps`：`openmemory-graph-worker → pg,neo4j`
  - `Test-WorkerHealth` + `Format-HealthDetail` 文案
  - `Test-HealthProbe` worker 分支
  - `Start-Service` worker 分支（幂等/早退/心跳等待/超时）
  - `Stop-Service` worker 分支（含命令行兜底清理与心跳删除）
  - `Get-AllStatus`、`Invoke-Monitor`、`Invoke-CheckAll` worker 分支
- 验收：`-Action status` 正确显示；`start` 后 worker 存活；`stop` 无残留进程

## T4 编排器：启动预热

- [x] `OpenBase/scripts/service-orchestrator.ps1`
  - 新增 `-SkipWarmup`
  - `Invoke-StackWarmup`（登录 + 6 个首屏端点 + 证据 JSON）
  - `Invoke-Start` 在启动完成后调用
- 验收：证据文件生成且字段齐全；预热失败不阻断启动

## T5 DPS：启动预热

- [x] `DPS/src/rest_api/app.py`
  - 新增 `_warmup_template_registry(db)`
  - `lifespan` 在 `_wire_tenant_middleware` 后调用
- [x] `DPS/src/tests/test_startup_warmup.py`（3 条用例，见 spec §7.1）
- 验收：单测通过；启动日志出现"画像模板注册表预热完成"（3 passed；ruff 通过）

## T6 验证（端到端）

- [x] `stop` → `startcheck` → `status`（实际执行 stop → start -Only → 全量幂等 start，status 健康）
- [x] worker 单实例冲突验证（第二实例退出码 0，日志 `holds lock`，未写重复心跳）
- [x] `openmemory_graph_outbox_pending` 采样：2860 → 0（两次采样均为 0，已清零）
- [x] `stop` 后无 `graph_projection_worker.py` 残留（残留 python=0）
- [x] 首屏计时：`templates 599ms`、`portraits 318ms`、`dashboard 723ms`（均 < 3s）
- 产出：`doc/test/evidence/ops/startup-warmup-20261118-025109.json`、`doc/test/evidence/ops/p01-p02-verify-20261118.json`

## T7 回填与交付

- [ ] 更新 `doc/test/OpenBase-前端全站走查报告-v1.0.0.md`：P-01/P-02 标记已修复并附证据路径（版本升次版本 1.1.0，记修订历史）
- [ ] 新增实现记录 `doc/dev/OpenBase-P01-P02-实现记录-v1.0.0.md`（变更清单、命令、结果）
- [ ] 分仓提交并推送三远程：OpenMemory、DPS、OpenBase

## 依赖关系

T1 → T2 → T3 → T4 → T6；T5 可与 T3/T4 并行；T6 完成后进入 T7。

## 备注

- 解释器口径：OpenBase 用 `.venv-test\Scripts\python.exe`；DPS 用 `.venv\shim311\python.cmd`；OpenMemory 用其仓内既有 Python 环境（以实测可用者为准）。
- 不提交无关文件：仅 `git add` 本清单涉及文件。
