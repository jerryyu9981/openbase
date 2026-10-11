# OpenBase-DEF-MTAUTH-001-全量回归PG连接瞬态缺陷登记-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-TEST-DEF-MTAUTH-001-v1.0.0 |
| 缺陷编号 | **DEF-MTAUTH-001**（批次作用域：多租户与授权集成工作流，编号体系对齐既有 DEF-<批次>-<序号> 惯例） |
| 优先级 | **P1**（不影响功能代码正确性，但持续污染全量回归门禁可信度；同现象已在 v1.4.10 发布期出现一次，本批再次出现 ⇒ 已满足「连续影响 ≥2 个版本」升级条件） |
| 状态 | **[Open]**（登记待修复；修复方向已定，待排期实施） |
| 登记日期 | 2026-10-11 |
| 作者 | AT-OpenBase-Dev（测试视图）／AU-OpenBase-Dev（审计视图） |
| 上游依据 | 《OpenBase-自研系统多租户与授权集成总体完善方案》v1.9.15（修订历史④ 全量回归终跑记录）；`doc/tmp/pytest-fullrun-final-20261011.log`（终跑日志，42 分钟全量） |
| 关联历史 | 《OpenBase-发布复盘与问题跟踪记录-v1.4.10》§1.2-1（共享 PG 稳定性待改进项）；台账 §10.3 B4 行「5 项为既有 pg 抖动」 |

## 1. 现象与证据

全量回归终跑（2026-10-11，约 42 分钟持续负载，桥接运行器 `doc/tmp/pyrun.py` + `.venv` 依赖注入 + 本机 PG17 `localhost:5432`）结果：

**1185 passed / 4 failed / 10 errors / 4 skipped**

| 类别 | 用例 | 错误 |
|------|------|------|
| FAILED | `tests/test_tenant_admin.py::test_tenant_crud_flow` | `sqlalchemy.exc.DBAPIError: (asyncpg.Error) connection was closed in the middle of operation` |
| FAILED | `tests/test_tenant_admin.py::test_tenant_quota_readwrite` | 同上 |
| FAILED | `tests/test_users_admin.py::test_user_crud_flow` | 同上 |
| FAILED | `tests/test_users_admin.py::test_new_user_can_login` | 同上 |
| ERROR ×10 | `tests/test_s7_t6_gate.py` 全部 10 例（`test_ra06_five_items_present` 等） | 门禁聚合断言失败——聚合中「双租户隔离回归 / 吊销即时性」两项 **PG 依赖检查 exit=1**（子进程同样命中 PG 连接中断），gate 报告状态非全 PASS |

底层证据（终跑日志）：

- `ConnectionResetError: [WinError 10054] 远程主机强迫关闭了一个现有的连接。`（`asyncio\selector_events.py:1009`）
- `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`
- 伴随业务降级留痕：`openbase.auth` `user query failed, fallback to memory` / `role query failed, fallback to default`、`openbase.audit` `request failed`（均为既有降级设计按预期工作）

## 2. 根因分析

**根因：42 分钟持续负载下，测试进程持有的空闲 PG 连接被服务端/网络中断，而测试引擎连接池未启用存活预检，后续用例从池中取到已死连接即失败。**

| 环节 | 分析 |
|------|------|
| 触发条件 | 全量回归单进程连续运行约 42 分钟，PG 连接长时间处于用例间空闲；本机/网络层（WinError 10054 为对端强制断开）在空闲期重置了既有连接 |
| 失效机理 | conftest 建立的 SQLAlchemy async 引擎**未启用 `pool_pre_ping`**：用例从池中复用已被对端关闭的连接，首个 SQL 往返即抛 `ConnectionDoesNotExistError`；s7_t6_gate 的 PG 依赖检查子进程同理 |
| 非缺陷排除 | ① 两文件**隔离复跑全绿**（`test_tenant_admin.py`+`test_users_admin.py` 42 passed；`test_s7_t6_gate.py` 10 passed），证明用例与被测代码本身正确；② 同现象在 v1.4.10 发布期（2026-10-02）与 B4 批次（「既有 pg 抖动」）均出现过，**与本次代码改动无因果**；③ 降级链路（memory/default fallback、audit 留痕）按设计工作，未产生错误扩散 |

## 3. 影响范围

| 维度 | 影响 |
|------|------|
| 功能正确性 | **无影响**——4 failed + 10 errors 均为环境瞬态，被测代码零改动即复跑通过 |
| 门禁可信度 | **受污染**——全量回归无法以单次终跑作为「全绿」门禁证据，需隔离复跑佐证，增加审计成本 |
| 复现条件 | 仅长时全量跑（≥30 分钟）触发；单文件/短批次不触发 |
| 波及面 | 本仓全量回归；台账 v1.9.15 登记的终跑结论；后续所有长时回归批次 |

## 4. 修复方案（方向已定，待排期）

| # | 动作 | 落点 |
|:-:|------|------|
| 1 | **启用 `pool_pre_ping=True`**：PG 测试引擎创建处统一加存活预检，取连接前先 ping，死连接自动重建（首选，改动最小） | `tests/conftest.py` 引擎工厂处 |
| 2 | **模块级引擎处置**：`asyncio_default_fixture_loop_scope = "module"` 下按模块结束 dispose 引擎，避免跨模块复用陈旧池（与方案 1 二选一或叠加） | `tests/conftest.py` |
| 3 | 门禁子进程同口径：s7_t6_gate 派生的 PG 依赖检查使用同一 conftest 引擎配置，确保预检生效 | `scripts/cross_repo_auth_gate.py` 相应检查 |

## 5. 验收标准

| # | 标准 | 验证方式 |
|:-:|------|---------|
| AC-1 | 全量回归终跑（≥40 分钟）**0 failed / 0 errors**（不含显式 skip） | `doc/tmp/pyrun.py pytest tests` 全量跑一次，日志留档 `doc/test/evidence/manual/` |
| AC-2 | 修复后连续 2 次全量跑均无 PG 瞬态失败（对应「连续影响 ≥2 版本」升级条件的对称退出判据） | 两次日志对比 |
| AC-3 | 单文件隔离复跑行为不回归 | `pytest tests/test_tenant_admin.py tests/test_users_admin.py` 与 `pytest tests/test_s7_t6_gate.py` 全绿 |
| AC-4 | 新增配置有测试覆盖（引擎工厂参数断言） | TDD：先写测试后实现，覆盖率不劣于基线 |

## 6. 闭环路径

1. 本登记文档入库（随 docs 提交，台账 v1.9.15 修订历史④ 已含同现象描述，互为引用）
2. 修复排期：随下一回归批次前置实施（方案 1 优先）
3. 按 §5 验收后本状态改 **[Closed]**，并回填台账修订历史

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-11 | AT/AU-OpenBase-Dev | 初始登记：现象与证据（终跑日志行号级引用）、根因分析（空闲连接中断 + 无 pre_ping）、影响范围、修复方案三动作、验收标准 AC-1~AC-4、闭环路径。状态 [Open] |
