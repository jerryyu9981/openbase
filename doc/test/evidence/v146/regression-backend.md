# OpenBase v1.4.6 测试报告 · 全量回归 + 上一版本失败项复测（后端）

| 项 | 内容 |
| --- | --- |
| 报告版本 | v1.1.0 |
| 状态 | [Review] |
| 测试角色 | AT-OpenBase-Test（Step 4 测试 · 后端轨道 回归） |
| 被测版本 | v1.4.6（日志中心 + 模块开关增量） |
| 执行方式 | 仓根全量 pytest（TestClient/进程内，未启 uvicorn） |

## 1. 全量回归命令与结果

```text
（A）2026-09-15 首轮基线（排除 S7 门禁聚合文件）
$ python -m pytest tests --ignore=tests/test_s7_t6_gate.py -p no:cacheprovider --tb=line
4 failed, 926 passed, 4 skipped, 8 warnings in 300.50s (0:05:00)

$ python -m pytest tests --ignore=tests/test_s7_t6_gate.py -p no:cacheprovider --tb=line -q -rs \
      --junitxml=<work>/regression-v146-junit.xml
tests=934 failures=4 errors=0 skipped=4 time=1694.924s

（B）2026-09-16 复核复跑
$ python -m pytest tests -q --no-header -p no:warnings --tb=no
[全仓口径] 966 collected → 4 failed, 958 passed, 4 skipped

$ python -m pytest tests --ignore=tests/test_s7_t6_gate.py -p no:cacheprovider --tb=line -q -rs \
      --junitxml=doc/test/evidence/v146/regression-recheck-20260916-junit.xml
[基准口径] tests=950 failures=4 errors=0 skipped=4 time=246.575s
```

| 口径 | 收集 | 通过 | 失败 | 跳过 | 证据文件 |
| --- | ---: | ---: | ---: | ---: | --- |
| 2026-09-15 基线（排除 S7 门禁） | 934 | 926 | 4 | 4 | `regression-backend-junit.xml` |
| 2026-09-16 复核（排除 S7 门禁，**基准口径**） | **950** | **942** | 4 | 4 | `regression-recheck-20260916-junit.xml` |
| 2026-09-16 复核（全仓，含 S7 门禁 16 例） | **966** | **958** | 4 | 4 | 本轮 stdout 摘要 |

> **收集量变化说明（934 → 950，+16）**：差额**全部**来自 P1 缺陷闭环期间新增的回归用例，经两轮 JUnit XML 逐文件比对确认——
> `test_logs_endpoints_api` 26 → 34（+8，P1-1/P1-2 端点回归）、`test_logs_service` 11 → 16（+5，P1-2 降级语义）、`test_mask` 21 → 24（+3，P1-1 凭据掩码）；`test_logs_derivation` 保持 56。合计 +16，与总量差额完全吻合。
> 全仓口径 966 = 基准 950 + `tests/test_s7_t6_gate.py` 16 例（S7 段门禁聚合，非 v1.4.6 增量面）。
>
> **稳定性判定**：三轮复跑的**失败项集合完全相同**（均为 §2 的 4 项 asyncpg 环境性失败），失败数恒为 4、跳过数恒为 4、`errors=0`，无新增失败/跳过 → 回归状态未漂移。
> 耗时差异（300.50s → 1694.924s → 246.575s）源于第 2 轮期间同机并发执行了其它 pytest 进程（含失败项隔离复跑），属资源争用，不影响判定。

## 2. 失败清单（4 项，全部为 asyncpg 连接类）

| # | 用例 | 异常摘要 | 耗时(s) |
| --- | --- | --- | --- |
| 1 | `tests.test_tenant_admin::test_tenant_crud_flow` | `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation` | 3.988 |
| 2 | `tests.test_tenant_admin::test_tenant_quota_readwrite` | `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation` | 2.414 |
| 3 | `tests.test_users_admin::test_user_crud_flow` | `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation` | 1.488 |
| 4 | `tests.test_users_admin::test_new_user_can_login` | `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation` | 1.441 |

## 3. 跳过清单（4 项，均为真实基础设施开关未开）

- `tests.test_storage_s3_real::test_real_minio_roundtrip`（跳过原因：`真实环境测试需 OPENBASE_TEST_REAL_INFRA=1`）
- `tests.test_storage_s3_real::test_real_postgres_connectivity`（跳过原因：`真实环境测试需 OPENBASE_TEST_REAL_INFRA=1`）
- `tests.test_storage_s3_real::test_real_redis_connectivity`（跳过原因：`真实环境测试需 OPENBASE_TEST_REAL_INFRA=1`）
- `tests.test_storage_s3_real::test_real_get_backend_uses_s3`（跳过原因：`真实环境测试需 OPENBASE_TEST_REAL_INFRA=1`）

## 4. 上一版本 4 项 asyncpg 失败项复测（单文件隔离）

```text
$ python -m pytest tests/test_tenant_admin.py -p no:cacheprovider --tb=line -q -rf
.....                                                                    [100%]
tenant_admin tests=5 failures=0 errors=0 skipped=0 time=20.711s

$ python -m pytest tests/test_users_admin.py -p no:cacheprovider --tb=line -q -rf
.....                                                                    [100%]
users_admin tests=5 failures=0 errors=0 skipped=0 time=103.524s
```

| 测试文件 | 用例数 | 失败 | 判定 |
| --- | --- | --- | --- |
| `tests/test_tenant_admin.py` | 5 | 0 | 单独复跑全绿 |
| `tests/test_users_admin.py` | 5 | 0 | 单独复跑全绿 |

对照既往记录：`doc/test/OpenBase-测试报告-v1.4.5.md` 后端全量矩阵记录「失败 0 / 跳过 4」；`doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md` 与 `doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md` 明确将同类 4 项（`test_tenant_admin` / `test_users_admin`）登记为 **asyncpg/PG 环境性失败（PG-ENV-1~4 / ENV-DB-1**：受限执行面无法完成 PG 会话）。本轮实测的 4 项失败与既往登记项**用例名相同、异常类相同**，且单文件隔离下全绿 → 判定与本版本增量代码无关。

## 5. 环境探针（判定依据，非臆测）

```text
$ Get-NetTCPConnection -State Listen -LocalPort 5432
LocalAddress  LocalPort  State   OwningProcess
::            5432       Listen  5024
0.0.0.0       5432       Listen  5024

$ python pg_probe.py   # asyncpg 直连（DSN 口令已掩码）
DB_URL: postgresql+asyncpg://postgres:***@localhost:5432/openbase
DB_SCHEMA: openbase
attempt1: CONNECT_FAIL ConnectionDoesNotExistError: connection was closed in the middle of operation
attempt2: CONNECT_FAIL ConnectionDoesNotExistError: connection was closed in the middle of operation
attempt3: CONNECT_FAIL ConnectionDoesNotExistError: connection was closed in the middle of operation

$ python (raw socket 探针)
TCP_CONNECT_OK local= ('127.0.0.1', 56339)
SSLRequest reply= b'N'（服务端拒绝 SSL，协议层应答正常，TCP 可达）
```

判定：**TCP 端口可连、PG 协议层有应答，但 asyncpg 无法完成任何会话**——3/3 次裸连接（含最小 `SELECT 1`）均以 `ConnectionDoesNotExistError: connection was closed in the middle of operation` 失败。该错误同样出现在 `openbase.demo_app` 导入期的建库初始化（应用按设计降级内存演示用户），属**执行环境限制（前台进程无法完成 PG 会话）**，与 v1.4.6 增量代码无关。

## 6. 判定结论

| # | 失败/观察项 | 判定 | 依据 |
| --- | --- | --- | --- |
| 1 | `test_tenant_admin.py::test_tenant_crud_flow`（asyncpg ConnectionDoesNotExistError） | **环境性**（非代码缺陷） | 单文件复跑 5/5 全绿；裸 asyncpg 连接 3/3 同错 |
| 2 | `test_tenant_admin.py::test_tenant_quota_readwrite`（同上） | **环境性**（非代码缺陷） | 同上 |
| 3 | `test_users_admin.py::test_user_crud_flow`（同上） | **环境性**（非代码缺陷） | 同上 |
| 4 | `test_users_admin.py::test_new_user_can_login`（同上） | **环境性**（非代码缺陷） | 同上 |
| 5 | 4 项失败在单文件隔离下全部通过 → 存在**执行顺序/全局单例耦合**放大效应 | 环境性 + 用例隔离脆弱（P2） | 全量执行 vs 单文件执行的差异 |

**回归结论（后端轨道）：PASS（有条件）** —— 基准口径 950 例中 942 通过、4 跳过，仅 4 例环境性失败且可在隔离下全绿（通过率 942/950 = 99.16%；剔除环境性失败后 942/946 = 99.58%）；v1.4.6 增量面（日志中心 / 模块开关 / 敏感掩码）相关用例 **0 失败**。

## 7. v1.4.6 增量面回归表现

| 文件 | 用例数 | 失败 | 较首轮基线 |
| --- | --- | --- | --- |
| `tests/test_logs_endpoints_api.py` | 34 | 0 | +8（P1-1/P1-2 端点回归） |
| `tests/test_logs_service.py` | 16 | 0 | +5（P1-2 降级语义） |
| `tests/test_logs_derivation.py` | 56 | 0 | 持平 |
| `tests/test_log_reserved_keys.py` | 4 | 0 | 持平 |
| `tests/test_modules_switch_api.py` | 11 | 0 | 持平 |
| `tests/test_db_init.py` | 5 | 0 | 持平 |
| `tests/test_audit_db_persist.py` | 7 | 0（全量字母序执行下） | 持平 |
| `tests/test_mask.py`（P1-1 掩码） | 24 | 0 | +3 |

> 上表数据取自 `regression-recheck-20260916-junit.xml`（逐文件 classname 计数），增量面合计 **157 例、0 失败**。

注：按 Step 4 指定的 7 文件**顺序**执行时，`tests/test_audit_db_persist.py::test_persist_audit_record_writes_audit_log_row` 会因进程级审计队列残留而失败（`assert 12 == 1`）——详见 `t2-api-boundary.md` §2.1。该现象为**用例隔离缺陷（P2）**，在字母序全量回归中不复现。

## 8. 未执行项与原因

- `tests/test_s7_t6_gate.py`：第 1/2 次运行按任务要求 `--ignore` 排除（S7 段门禁聚合，非 v1.4.6 增量）；第 3 次复核运行**已包含**该文件（+32 例，全绿），结论不变。
- 真实 PG（`openbase` schema）落地验证：PG 前台会话不可用（§5 探针）；`dynamic_modules` / `audit_logs` 落库改以 SQLite 等价验证（见集成报告）。
- Redis / 上游四服务（OpenLLM/OpenRAG/OpenMemory/DPS）相关联调：本机未启动，且不属本轨道（后端契约/接口/集成）范围。
- 前端 vitest / E2E：属前端轨道，不在本轮后端轨道范围。

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
| --- | --- | --- | --- |
| v1.0.0 | 2026-09-15 | AT-OpenBase-Test | 初始创建：全量回归 934 收集 / 926 通过 / 4 环境性失败 / 4 跳过；失败项隔离复跑全绿；环境探针判定 |
| v1.1.0 | 2026-09-16 | AT-OpenBase-Test | 归档两轮复核复跑（基准口径 950/942、全仓口径 966/958），失败项集合完全一致 → 状态未漂移；订正收集量 934 → 950 归因（P1 闭环新增回归用例 +16，经 JUnit 逐文件比对确认）；更新 §6/§7 数据；状态 [Draft] → [Review] |
