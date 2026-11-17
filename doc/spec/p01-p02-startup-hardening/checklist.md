# P-01/P-02 验证检查单（checklist）

- 依据：[spec.md](./spec.md) v1.0.1 / [tasks.md](./tasks.md)
- 证据：`doc/test/evidence/ops/startup-warmup-20261118-025109.json`、`doc/test/evidence/ops/p01-p02-verify-20261118.json`

## 目标核对

- [x] G1 一键启动即拉起 worker 且仅一个实例
  - `status`：`openmemory-graph-worker - ... 健康 ✅ PID=11420`
  - 第二实例：退出码 0，日志含 `another graph projection worker holds lock`，未写重复心跳
- [x] G2 worker 可启停/自愈/体检
  - `stop` 后 `graph_projection_worker.py` 残留 **0**；心跳文件删除
  - `monitor`/`CheckAll` 已接入心跳判定（代码分支 + 状态输出验证）
- [x] G3 图投影积压下降并清零
  - `openmemory_graph_outbox_pending`: 2860 → 0；`outbox_dead=0`；`events_total{result=ok}=2860`
- [x] G4 首屏链路预热达标
  - 6 个端点全部 200，单端点最快 281ms、最慢 723ms（均 < 3s），总耗时 3126ms
- [x] G5 DPS 启动完成模板注册表加载
  - `logs/dps/dps-20261118.err.jsonl` @ `2026-11-17T18:49:23.159Z`：`loaded: 5`（5 个 active 模板）

## 单测与静态检查

- [x] OpenMemory：`64 passed`（含新增 4 条锁/心跳用例）；`ruff` All checks passed
- [x] DPS：`test_startup_warmup.py` 3 passed；变更文件 ruff 通过
- [x] OpenBase：编排脚本 PowerShell AST 解析通过（无语法错误）

## 回归确认

- [x] DPS 重启后画像模板/画像列表请求 200（68.95ms / 48.06ms，见 access 日志）
- [x] 未改变端口分配、健康端点语义、A/B 通道契约
- [x] 未新增依赖、未改数据库 Schema
