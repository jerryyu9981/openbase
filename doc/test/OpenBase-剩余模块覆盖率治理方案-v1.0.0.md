# OpenBase 剩余模块覆盖率治理方案（v1.0.0）

| 项目 | 内容 |
|---|---|
| 文档名称 | OpenBase 剩余模块覆盖率治理方案 |
| 版本 | v1.1.0 |
| 状态 | [Final]（补测与全量回归已执行，全局覆盖率 91%，待人工验收） |
| 文档类型 | 测试阶段专项补测方案（`doc/test`，归属 Step 4 测试阶段） |
| 编写角色 | 测试负责人 |
| 适用环境 | 开发环境（Dev）/ 测试环境（Test）通用 |
| 编写日期 | 2026-11-13 |
| 关联文档 | 《OpenBase-users模块补测方案-v1.0.0.md》v1.1.0（方法与验收标准同源）、AGENTS.md（验证命令与覆盖率门禁） |
| 代码基线 | 全量 `pytest tests --cov=openbase`（`concurrency=greenlet,thread` + `branch=true` 修正口径）：TOTAL 89% |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.0 | 2026-11-13 | 测试负责人 | 首次编制：剩余缺口模块清单、30 条补测用例设计、scheduler 缺陷登记与验收标准 |
| v1.1.0 | 2026-11-13 | 测试负责人 | 回填执行结果：30 条用例落地、6 个目标模块覆盖率 98%~100%、全量 1681 用例仅 1 项共享 PG 瞬态失败（已登记）、全局 TOTAL 由 89% 提升至 91% |

---

## 1. 背景与目标

### 1.1 背景

《OpenBase-users模块补测方案》已完成 P0 覆盖率口径修正（`[tool.coverage.run] concurrency = ["greenlet","thread"]` + `branch = true`），users 模块覆盖率由 58% 提升至 **100%**，全量回归 1651 用例 0 失败，全局 `TOTAL 89%`。

AGENTS.md §8 与 §7 要求后端覆盖率 ≥90%。当前距门禁仍差 1 个百分点，缺口集中在 users 之外的历史模块（users 方案 §1.3 已明确另行立项）。本方案承接该治理项。

### 1.2 目标

1. 按「缺口行 → 用例」映射补齐剩余模块的异常分支与边界契约，使**全局语句/分支覆盖率 ≥90%**。
2. 优先治理 `mcp/stdio`（0%）与 `identity/dispatcher`（61%）等**零/低覆盖模块**，避免为追指标而堆砌冗余断言。
3. 补测中发现的真实缺陷按缺陷流程修复（本项目为 TDD RED→GREEN 直接修复并留痕）。
4. 全量回归零失败、`ruff check openbase tests` 零告警。

### 1.3 非目标

- 不改动被测模块的业务语义（除缺陷修复外不重构）。
- 不治理 `logs/repository`（77%，470 语句 / 88 未覆盖）、`auth/oidc`（87%）、`llm_proxy`（82%）、`proxy/memory_proxy`（83%）等大模块——作为**达标余量储备**，仅当本轮后全局仍 <90% 时启动。
- 不改动前端代码与前端覆盖率（本轮为后端治理）。

---

## 2. 缺口清单（修正口径全量实测）

数据来源：全量 `pytest tests --cov=openbase --cov-report=term-missing`（2026-11-13，users 补测后）。

| 优先级 | 模块 | 语句 | 未覆盖 | 覆盖率 | 未覆盖行 |
|---|---|---|---|---|---|
| P0 | `openbase/modules/mcp/stdio.py` | 32 | 32 | 0% | 全文（stdio 线性会话无测试） |
| P0 | `openbase/modules/identity/dispatcher.py` | 90 | 31 | 61% | skip/retry/failed 推进、按 event_id 投递、后台轮询 |
| P1 | `openbase/modules/scheduler/__init__.py` | 152 | 46 | 67% | 53->62, 59-61, 67, 99, 108, 118->121, 127-132, 136, 140, 144-148, 152-154, 162-164, 167-170, 179-181, 190-192, 194-196, 205-207, 209-211, 224-228 |
| P1 | `openbase/modules/dict/__init__.py` | 177 | 43 | 72% | 65->68, 83-85, 102, 107, 130->144, 136->138, 140->144, 176-178, 182, 187-190, 194, 198-200, 205-216, 224-226, 234-236, 248-250, 261-263, 274-276, 291-293 |
| P1 | `openbase/modules/notify/__init__.py` | 157 | 34 | 78% | 60-67, 140->139, 153-155, 157, 168-170, 181-194, 204-206, 208-210, 219-221, 241-242 |
| P1 | `openbase/modules/org/__init__.py` | 108 | 30 | 70% | 42-46, 60->62, 82->85, 91-95, 99, 103-104, 128-130, 137-142, 150-152, 161-165 |
| P1 | `openbase/modules/storage/__init__.py` | 179 | 29 | 83% | 59, 109-112, 228, 238-242, 246, 250, 254, 268-270, 282-284, 295-300, 308-310, 313-314 |

> 说明：以上 6 个模块合计未覆盖 245 行，占全局未覆盖（1096 行）的 22%；其中约 80% 为**数据库不可用的内存回退分支**与**业务边界（404/409）**，属可稳定构造的确定性路径，不含外部网络依赖。

---

## 3. 补测用例设计

### 3.1 文件与用例清单

| 编号 | 文件 | 用例数 | 覆盖目标 |
|---|---|---|---|
| UT-REM-01 ~ 09 | `tests/test_scheduler_api.py`（新增） | 9 | scheduler：CRUD 主路径、启停 404、apscheduler 缺失降级、缓存实例、`_run_task` 日志、`add_job` 成功/异常、服务层空结果、DB 异常全内存回退 |
| UT-REM-10 ~ 21 | `tests/test_module_fallbacks.py`（新增） | 12 | org/dict/storage/notify：DB 分支补位、缓存命中、孤儿数据、S3 客户端懒加载、SSE 发布与流取消、Redis 处理器、全端点内存回退 |
| UT-REM-22 ~ 25 | `tests/test_mcp_stdio.py`（新增） | 4 | mcp/stdio：白名单映射、非法 JSON 容错、默认流分支、`main()` 入口 |
| UT-REM-26 ~ 29 | `tests/test_dispatcher_extra.py`（新增） | 4 | identity/dispatcher：四条推进分支、按 event_id 投递、`run_once` 汇总、后台轮询告警/停止 |
| UT-REM-30 | `tests/test_scheduler_api.py` | 1 | 启停不存在任务的 404 契约（缺陷回归） |

### 3.2 关键用例设计要点

| 编号 | 用例名称 | 步骤 | 预期 |
|---|---|---|---|
| UT-REM-02 | scheduler-启停不存在任务 | `POST /api/v1/schedules/999999/{start,stop}` | 404 `BIZ_404`（**补测发现的缺陷，见 §4**） |
| UT-REM-03 | scheduler-apscheduler 缺失 | monkeypatch `builtins.__import__` 对 `apscheduler*` 抛 ImportError 后调用 `get_scheduler()` | 返回 None 且 WARN 日志 |
| UT-REM-07 | scheduler-add_job 异常 | FakeScheduler.add_job 抛 RuntimeError | 创建仍 200，仅告警 |
| UT-REM-09 | scheduler-DB 不可用 | monkeypatch `ScheduleService` 四个 DB 方法抛异常 | 创建/列表/启停/删除全部走内存实现且 200 |
| UT-REM-10 | org-父子路径与树 | 建父/子部门 + 不存在父节点 + 删除不存在部门 | 路径 `/父/子`、父缺失时 `/自身`、删除幂等 |
| UT-REM-11 | org-内存回退 | monkeypatch 服务方法抛异常 | 创建（含嵌套路径）/列表/树/删除全部回退且树结构正确 |
| UT-REM-12 | dict-DB 分支 | 类型幂等创建、隐式建类型、缓存命中、未知类型、删除 404/409 | 契约与缓存短路均成立 |
| UT-REM-13 | dict-孤儿类型 | 直接删除 `dict_types` 行后删字典项 | 跳过缓存失效，删除幂等 |
| UT-REM-14 | dict-内存回退 | monkeypatch 六个 DB 方法抛异常 | 全端点回退；409/404 业务错误不被吞 |
| UT-REM-16 | storage-本地读取 | 上传后 `LocalStorageBackend.load` | 内容与上传字节一致；删除不存在记录不触碰存储 |
| UT-REM-17 | storage-内存回退 | monkeypatch 四个 DB 方法抛异常 | 上传/列表/详情/删除回退；缺失详情 404 `STORAGE_404` |
| UT-REM-18 | storage-S3 懒加载 | 注入 fake `boto3`/`botocore.config` | 客户端只建一次，`s3v4` 签名与 endpoint 透传 |
| UT-REM-19 | notify-DB 与 404 | 创建/列表/已读/全部已读 + 不存在已读 | 404 `PARAM_404` |
| UT-REM-20 | notify-SSE 发布与流 | 本地订阅者收 publish；`stream()` 首帧、收消息、取消清理 | 队列收到消息；取消后订阅者移除 |
| UT-REM-21 | notify-内存回退 | 含 `type=2` 创建（触发 SSE 推送） | 全端点回退，404 保持 |
| UT-REM-22 | mcp-stdio 会话 | 空行/非法 JSON/initialize/tools-list 混合输入 | 非法 JSON 返回 -32700；合法请求有响应；退出码 0 |
| UT-REM-23 | mcp-stdio 默认流 | 未注入流时回落 `sys.stdin/stdout` | 输出可解析协议响应 |
| UT-REM-26 | dispatcher-推进分支 | pending+成功 / 非 pending / 失败未超阈值 / 超阈值 | published / skipped / retry（写入退避时间）/ failed |
| UT-REM-27 | dispatcher-run_once | 4 条到期 pending + 1 条 published | `{scanned:4, retry:3, failed:1}`，二轮扫描 0 |
| UT-REM-28 | dispatcher-后台轮询 | 首轮抛异常、次轮正常，随后 stop | 告警不中断；stop 幂等且任务取消 |

---

## 4. 补测发现的缺陷与修复

| 编号 | 模块 | 现象 | 根因 | 修复 | 回归用例 |
|---|---|---|---|---|---|
| DEF-REM-001 | `scheduler` | 启停不存在的任务返回 **500**（`AttributeError`），而非 404 | `raise BaseError(ErrorCode.NOT_FOUND, ...)`，但 `ErrorCode` 无 `NOT_FOUND` 成员（正确成员为 `BIZ_NOT_FOUND`），`start_schedule` / `stop_schedule` 两处 | 改为 `ErrorCode.BIZ_NOT_FOUND`（404 映射不变） | UT-REM-02 |

> 该缺陷为 TDD RED 阶段由 `test_schedule_start_stop_missing_task` 直接暴露，属真实运行期缺陷（非测试瑕疵），已按最小改动修复。

---

## 5. 执行步骤与命令

```bash
# 1) 定向补测 + 覆盖率（统一 --cov=openbase 口径）
python -m pytest tests/test_scheduler_api.py tests/test_module_fallbacks.py \
  --cov=openbase --cov-report=term-missing -q

# 2) 新增零覆盖模块定向验证
python -m pytest tests/test_mcp_stdio.py tests/test_dispatcher_extra.py -q

# 3) 全量回归 + 全局覆盖率门禁
python -m pytest tests -q --cov=openbase --cov-report=term-missing \
  --junitxml=reports/pytest-coverage-governance.xml

# 4) 静态检查
python -m ruff check openbase tests
```

---

## 6. 验收标准

| 维度 | 通过标准 | 验证方式 |
|---|---|---|
| 全局覆盖率 | `TOTAL ≥ 90%`（语句与分支合并口径） | `--cov-report=term-missing` 末行 |
| 模块覆盖率 | 本轮 6 个目标模块各自 ≥90%（`mcp/stdio`、`identity/dispatcher` 目标 100%） | term-missing 输出 |
| 用例 | 新增 30 条用例全部通过 | 定向 pytest 输出 |
| 缺陷 | DEF-REM-001 修复并有回归用例 | UT-REM-02 |
| 回归 | 后端全量 0 失败 0 错误（跳过项说明原因） | JUnit `failures=0 errors=0` |
| 静态质量 | `ruff check openbase tests` 0 错误 | `All checks passed` |
| 文档 | 本方案回填执行结果，版本升至 v1.1.0 | 修订历史 |

---

## 7. 风险与依赖

| 风险 | 影响 | 应对 |
|---|---|---|
| 多文件同进程运行导致全局 DB 工厂串扰 | 用例随机失败 | 各测试文件沿用「模块级 SQLite + `pytest.MonkeyPatch` 固定全局工厂 + `reset_db_singletons`」范式 |
| APScheduler 实例跨用例残留 | add_job 断言互相干扰 | 用例内 monkeypatch `get_scheduler` 为 FakeScheduler，或在断言后复位 `_scheduler` |
| SSE 流生成器用例阻塞 | 测试挂起 | 直接驱动 `body_iterator`：首帧断言后主动 `athrow(CancelledError)` 终止 |
| 伪造 `boto3` 影响其他用例 | 导入缓存污染 | `monkeypatch.setitem(sys.modules, ...)` 自动还原 |
| 全量运行耗时长（本机约 20 分钟，负载高时更久） | 反馈周期长 | 后台执行 + JUnit 统计；定向先绿再全量 |

---

## 8. 影响文件清单

| 文件 | 变更性质 | 说明 |
|---|---|---|
| `tests/test_scheduler_api.py` | 新增 | UT-REM-01 ~ 09、30（9 条） |
| `tests/test_module_fallbacks.py` | 新增 | UT-REM-10 ~ 21（12 条） |
| `tests/test_mcp_stdio.py` | 新增 | UT-REM-22 ~ 25（4 条） |
| `tests/test_dispatcher_extra.py` | 新增 | UT-REM-26 ~ 29（4 条） |
| `openbase/modules/scheduler/__init__.py` | 修改（缺陷修复） | `ErrorCode.NOT_FOUND` → `BIZ_NOT_FOUND`（2 处） |
| `doc/test/OpenBase-剩余模块覆盖率治理方案-v1.0.0.md` | 新增 | 本方案 |

---

## 9. 执行记录（2026-11-13）

### 9.1 变更落地

| 文件 | 变更 | 说明 |
|---|---|---|
| `tests/test_scheduler_api.py` | 新增（9 条） | scheduler 主路径 + 降级 + 服务层边界 |
| `tests/test_module_fallbacks.py` | 新增（13 条） | org/dict/storage/notify 的 DB 分支与内存回退、SSE/S3/缓存边界 |
| `tests/test_mcp_stdio.py` | 新增（4 条） | stdio 线性会话、默认流、入口 `main()` |
| `tests/test_dispatcher_extra.py` | 新增（4 条） | outbox 四态推进、`run_once` 汇总、后台轮询 |
| `openbase/modules/scheduler/__init__.py` | 修改（2 处） | DEF-REM-001 缺陷修复 |

合计新增用例 **30 条**（UT-REM-01 ~ 30）。

### 9.2 定向验证结果

| 项 | 命令 | 结果 |
|---|---|---|
| 用例 | `pytest tests/test_scheduler_api.py tests/test_module_fallbacks.py tests/test_mcp_stdio.py tests/test_dispatcher_extra.py` | **30 passed**，0 failed |
| 静态检查 | `ruff check openbase/modules/scheduler/__init__.py tests/test_scheduler_api.py tests/test_module_fallbacks.py tests/test_mcp_stdio.py tests/test_dispatcher_extra.py` | `All checks passed!` |
| 缺陷回归 | `pytest tests/test_scheduler_api.py::test_schedule_start_stop_missing_task` | 404 `BIZ_404`（修复前为 500 `AttributeError`） |

### 9.3 全量回归结果

| 项 | 命令 | 结果 |
|---|---|---|
| 全量用例 | `pytest tests --cov=openbase --cov-report=term-missing --junitxml=...` | **1681 tests / 0 errors / 1 failed / 5 skipped**，1389.83s |
| 全局覆盖率 | 同上（term-missing） | **TOTAL 91%**（12183 语句 / 843 未覆盖；2924 分支 / 392 部分覆盖） |
| 基线对比 | users 补测后基线 | 未覆盖语句 **1096 → 843**（-253）；部分分支 **414 → 392**（-22）；TOTAL **89% → 91%** |

目标模块覆盖率（全量口径）：

| 模块 | 语句 | 未覆盖 | 分支 | 部分 | 覆盖率 | 治理前 |
|---|---|---|---|---|---|---|
| `modules/scheduler/__init__.py` | 152 | 2 | 16 | 1 | **98%**（140、146） | 67% |
| `modules/org/__init__.py` | 108 | 0 | 14 | 0 | **100%** | 70% |
| `modules/dict/__init__.py` | 177 | 0 | 24 | 0 | **100%** | 72% |
| `modules/storage/__init__.py` | 179 | 1 | 20 | 1 | **99%**（314） | 83% |
| `modules/notify/__init__.py` | 157 | 0 | 22 | 1 | **99%**（140->139） | 78% |
| `modules/mcp/stdio.py` | 32 | 0 | 4 | 0 | **100%** | 0% |
| `modules/identity/dispatcher.py` | 90 | 1 | 18 | 1 | **98%**（179） | 61% |
| `modules/users/__init__.py`（参照） | 152 | 0 | 34 | 0 | **100%** | 100% |

### 9.4 全量回归失败项说明

| 用例 | 现象 | 裁定 |
|---|---|---|
| `tests/test_service_agent_outbound.py::test_obk_service_account_mapped_outbound_headers` | `asyncpg ... connection was closed in the middle of operation`（连接 `localhost:5432` 共享 PostgreSQL）；单独复跑同样失败（`WinError 10054 远程主机强迫关闭了一个现有的连接`） | **环境性失败**：本机共享 PG 当前不可用/连接被重置，与本次变更无关；该类瞬态已登记于《OpenBase-DEF-MTAUTH-001-全量回归PG连接瞬态缺陷登记-v1.0.0.md》。本次 30 条新增用例与 6 个目标模块全部通过 |

### 9.5 备注

- 首次全量运行（`-x`）时 `tests/test_orchestrator_db_failover.py::test_standby_unreachable_blocks_startup` 因宿主机高负载导致子进程 PowerShell 启动超过 120s 超时；单跑通过（1 passed），完整重跑亦通过，判定为环境性抖动。
- 统一使用 `--cov=openbase` 口径（`--cov=openbase.modules.*` 子口径仍触发 coverage ctrace 与 SQLAlchemy C 扩展的 `TypeError`，见 users 方案 §10.4）。
- `tests/test_service_agent_outbound.py` 等共享 PG 用例在 PG 恢复后应重跑确认；本方案不修改其代码。
- 存储相关用例使用 `tmp_path` 注入本地后端，不向仓库 `storage/` 写入产物。
