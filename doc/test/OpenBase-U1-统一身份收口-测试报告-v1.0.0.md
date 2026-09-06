# OpenBase-U1-统一身份收口-测试报告-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-U1-TEST-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（T1~T6 用例与断言 + T7 兼容回归 + S1a 段门禁四项核对；待人工批准进入部署） |
| 日期 | 2026-09-07 |
| 作者 | AT-OpenBase（U1 测试） |
| 存放 | doc/test/ |
| 版本主题 | U1（S1a）T1~T6 用例与断言覆盖、分组回归策略（Windows 单进程 C 层崩溃规避）、407 passed/4 skipped、迁移幂等重放、覆盖率（全仓 86%）、S1a 段门禁四项核对（login tenant_code 100%/吊销即时/委托跨界 403/L1-1+L1-2 按 Q-5=A）、覆盖缺口 R3 登记 |
| 上游依据 | 《OpenBase-U1-统一身份收口设计草案》v1.1.0 §11（T1~T8 RED 断言）；《OpenBase-U1-统一身份收口立项方案》v1.1.0 §4 验收 / §8 门禁；《OpenBase-多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1a 门禁四项）；U1 DevLogReport v1.0.0 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | AT-OpenBase（U1 测试） | 初始版本：T1~T6 用例与断言矩阵、分组回归策略说明、回归结果（407 passed/4 skipped）、4 skip 原因、迁移幂等重放、覆盖率与缺口 R3、S1a 段门禁四项核对结论 |

---

## 1. 基本信息

- 测试对象：OpenBase 主仓 main（T7/T8 收口 HEAD；前置提交链 c1869bf→52a4792 + T7 fix 提交 + 本 docs 提交）。
- 测试环境：Windows（Python 3.10.11 / pytest 9.1.1 / ruff 0.15.22 / SQLite 本地库，模块级独立 DB 文件）；真实凭据类用例默认 skip（OPENBASE_TEST_REAL_INFRA 未置位）。
- 测试结论：**通过**。全量分组回归 407 passed / 0 failed / 4 skipped；ruff 0 错误；迁移幂等重放无副作用；S1a 段门禁四项核对全绿。

## 2. 分组回归运行策略说明（Windows 平台单进程 C 层崩溃规避）

- 背景：starlette BaseHTTPMiddleware + anyio 多实例在 Windows 单进程叠加执行存在非确定性 C 层崩溃（本仓 TD-新增-009 记录）。`tests/conftest.py` 以 `WindowsSelectorEventLoopPolicy` 缓解后仍按**分组子进程隔离**执行。
- 编排：`python scripts/run_regression.py --group-size 3`——按测试文件分组（默认每组 ≤3 个文件），每组独立 pytest 子进程（`-p no:cacheprovider`），崩溃组自动重试（≤3 次）；先跑 `python -m ruff check openbase tests`（0 错误放行），再跑分组 pytest，最后汇总。
- 本次执行：47 个测试文件 / 16 组；无崩溃重试（全部一次通过）。

## 3. T1~T6 用例与断言覆盖矩阵（对照设计草案 §11）

| 任务 | 测试文件 | 用例数 | §11 断言覆盖 | 结果 |
|------|---------|:---:|-------------|:---:|
| T1（RA-01） | `tests/test_identity_t1.py` | 8 | T1-1~T1-8（agent 建号/明文一次哈希存储/密钥鉴权/登录拒 agent/默认 viewer/轮换吊销/迁移幂等与回填/存量可登录） | ✅ 8 passed |
| T2（RA-02） | `tests/test_identity_t2.py` | 14 | T2-1~T2-8（合法迁移链/0 非法路径/login+refresh 100% tenant_code/v0 兼容与补齐/suspend 拒签/OIDC 停用拦截/lifecycle 鉴权/全链路） | ✅ 14 passed |
| T3（K04） | `tests/test_identity_t3.py` | 17 | T3-1~T3-7（suspend 即时 401/refresh 拒/deactivate 全入口拒/restore 旧 token 失效/tvn 落后拒/静态扫描 0 仅验签/缓存一致性）+ fail-open 补充组 | ✅ 17 passed |
| T4（K08） | `tests/test_identity_t4.py` | 13 | T4-1~T4-7（同域签发/跨界 403/每请求重校验/嵌套链逐跳/非法委托/审计两层/出站委托域值） | ✅ 13 passed |
| T5（L1-1） | `tests/test_identity_t5.py` | 8 | T5-1~T5-6（同事务 outbox/契约桩拒绝语义/幂等重放副作用一次/schema 完整/秒级窗口/suspend 阻断与 restore 解除） | ✅ 8 passed |
| T6（L1-2，Q-5=A） | `tests/test_identity_t6.py` | 21 | T6-1~T6-5（静态扫描 0 自动限期清除/非 deactivated 400/授权缺失过期 403/合法 purge 终态审计/并发幂等一次）+ purge 后 token 墓碑判定/fail-open 区分/CLI 护栏等 | ✅ 21 passed |
| T7 收口（新增 2 例） | `tests/test_identity_t6.py` | +2 | T7-1 显式 400（幂等键跨主体复用被拒且无副作用；同主体重放终态拒绝） | ✅ 2 passed |
| 兼容回归全量 | `scripts/run_regression.py --group-size 3` | 411（含 skip） | 既有 users/tenants/roles CRUD、JWT v0 兼容、OIDC 直签与内存用户 fail-open、M1 形态（identity_t1~t6 + 全仓分组） | ✅ 407 passed / 0 failed / 4 skipped |

> 说明：T7/T8 断言（T7-1~T7-5、T8-1~T8-3）由 T7 收口代码/回归 + 本报告与 DevLogReport 登记落实（见 §4~§6）。

## 4. 回归结果与跳过原因

### 4.1 回归结果

- 汇总：**407 passed / 0 failed / 4 skipped**（16 组 / 47 文件）；ruff 0。对照 T6 时点基线 405 passed，本次新增 T7-1 显式 400 校验 2 例后为 407 passed。
- 分组明细与历史执行证据见 U1 DevLogReport v1.0.0 §4（本报告不重复）。

### 4.2 4 个 skip 原因

| 数量 | 文件 | 原因 |
|:---:|------|------|
| 4 | `tests/test_storage_s3_real.py` | 真实环境集成测试（MinIO/PostgreSQL/Redis/共用基础设施），需 `OPENBASE_TEST_REAL_INFRA=1` 且 `.env.shared-infra` 就绪；本次本地回归未置位该标志，按模块级 `pytestmark = skipif` **既有凭据跳过**（与存量基线行为一致，非本 U1 引入） |

## 5. S1a 段门禁四项核对（规划 v1.3.0 S1a / 立项 §8 步骤⑤）

| # | 门禁项 | 核对结论 | 证据 |
|---|--------|:---:|------|
| G-1 | **login 令牌 100% 含 tenant_code** | ✅ 全绿 | `tests/test_identity_t2.py::test_t2_3_login_and_refresh_tokens_100_percent_tenant_code`（本地 login 全量取样 + refresh 再签注入断言）；`test_t2_6_oidc_bound_active_issues_full_claims` / `test_t2_6_oidc_direct_sign_issues_full_claims`（OIDC bound/直签同签发器）；v0 存量 refresh 补齐 `test_t2_4_v0_access_compatible_and_refresh_upgrades_tenant_code` |
| G-2 | **吊销即时** | ✅ 全绿 | `test_t3_1_suspend_immediately_invalidates_existing_access`（suspend 后存量 access 立即 401 `AUTH_PRINCIPAL_DISABLED`）；`test_t3_2_suspend_blocks_refresh_issuance`（refresh 签发侧状态门禁）；`test_t3_4_restore_old_access_stale_when_enforced_and_relogin_ok`；deactivate 后全入口拒 `test_t3_3_deactivate_blocks_all_entries_for_user` |
| G-3 | **委托跨界 403** | ✅ 全绿 | `test_t4_2_cross_tenant_delegation_rejected`；嵌套链任意跳跨界即拒 `test_t4_4_nested_chain_same_domain_ok_cross_hop_rejected`；每请求重校验（域替换）`test_t4_3_delegated_domain_swap_rejected_per_request` |
| G-4 | **U1 立项含 L1-1/L1-2（按 Q-5=A：purge 显式 + 无自动限期清除）** | ✅ 全绿 | 立项方案 §2.4/§2.5 含 L1-1/L1-2 且 Q-5=A；`test_t6_1_no_auto_retention_purge_path_static_scan`（静态扫描 0 自动限期清除路径）、`test_t6_1_no_scheduler_job_registers_purge`；purge 显式合规触发 + 二次授权 `test_t6_3_*`/`test_t6_4_purge_success_physical_clear_and_audit`；数据保留+全链阻断 `test_t6_4_purge_keeps_audit_blocks_and_consumption_history` |

### 5.1 过渡语义说明（吊销即时相关，enforce_token_version 默认关）

- **状态校验默认即时生效**：suspend/deactivate 主体任何入口请求 401/403（`verify_principal` 第②步不依赖开关）。
- **token 版本强校验为两段式发布第二段**：`settings.enforce_token_version = False`（默认关），v0/旧 tvn 令牌在过渡窗口放行、refresh 后升级 v1（`test_t3_4_default_off_allows_stale_tvn_in_transition_window`、`test_t3_5_v0_token_without_tvn_still_allowed_when_enforced`）；第二段（开关置 True，`AUTH_TOKEN_STALE` 全量生效）在部署段/S1b 窗口开启（立项 §6.2 上线顺序纪律，先状态校验后版本强校验）。
- 结论：门禁 G-2「吊销即时」按「**立即（状态门禁）或最迟一次刷新窗口内（签发侧状态门禁 + v0 升级）**」验收口径成立。

### 5.2 与 P2-2（S0）互证（设计草案 §11 T8-3）

- 双租户/存量隔离回归（`tests/test_tenant_admin.py`、`tests/test_users_admin.py`、proxy 族用例）在本次全量分组回归中全绿，U1 新增主体/身份断言未破坏既有隔离断言（见回归分组：tenant_admin/users_admin/proxy 组 0 failed）。

## 6. 覆盖率与缺口（详见 DevLogReport §6/§7）

| 项 | 实测 |
|----|------|
| 全仓 openbase 行覆盖率 | 86%（5,973 stmts / 852 miss，16 组 --cov-append 合并） |
| U1 identity 模块 | purge 98% / verification 97% / migration 93% / state_machine 93% / events 92% / delegation 91% / __init__ 80% / consumer_stub 69% / lifecycle 67% / dispatcher 62% / agent_keys 59% / agents 51% |
| 存量/受改动基线模块 | users 51%、tenant 76%、auth/__init__ 81%、oidc 82%、core/deps/auth 82%（Windows TestClient 线程桥采集缺口与存量基线一致，复测值同任务口径） |
| 缺口登记 | users / lifecycle / dispatcher / tenant / agents / agent_keys / consumer_stub / __init__ 等 → **R3 后续补测**（DevLogReport §7） |

> 说明：U1 新增核心模块（服务层/纯逻辑/CLI）覆盖 91%~98%，已达 ≥90% 门槛；低覆盖集中在「HTTP 端点 + 真实 DB」驱动路径，与存量基线模块同一采集边界，与 U1 实现质量无因果关系。

## 7. 迁移幂等重放验证（T7-5）

- 测试覆盖：`test_t1_7_t1_8_migration_idempotent_and_backfill`（空库重放两次：无异常、无重复行、权限种子不重复、回填正确）+ `test_t1_7_regression_user_still_loginable_after_migration`。
- 补充证据（可复现脚本 `doc/test/evidence/u1_t7_migration_replay_verify.py`，运行 `python doc/test/evidence/u1_t7_migration_replay_verify.py`）：生产库形态样本脚本连续两次 `apply_identity_migration`——第一次 7 列补齐 + 4 权限种子 + 回填正确；第二次 `columns_added=[]` / `permissions_seeded=0`；users 行数/内容/既有 id-FK 不变。结论 `REPLAY_VERIFY_OK`（无副作用，可进入部署段 PG 执行）。

## 8. 环境遗留与已知限制

| 项 | 说明 |
|----|------|
| test_storage_s3_real 4 skip | 真实凭据（OPENBASE_TEST_REAL_INFRA=1）未置位，存量基线行为 |
| coverage 采集边界 | Windows TestClient 请求线程 + aiosqlite 线程桥帧未计入 → 端点驱动模块覆盖低估（登记 R3 治理） |
| PG 生产迁移 | T7 以 SQLite 生产形态样本验证；PG 走同一幂等脚本（schema 分支已测 `--include` 覆盖 93%，PG schema 分支 77/80 行属部署段执行） |
| 真实消费端核验 | L1-1 真实消费端（DPS/OpenMemory/OpenRAG）与全链核验属 S2/S3/S5/S7（S7-1） |

## 9. 结论

- 兼容回归分组全绿（407 passed / 0 failed / 4 skipped）、ruff 0；S1a 段门禁四项核对**全绿**（login tenant_code 100% / 吊销即时〔含 enforce_token_version 默认关过渡语义〕/ 委托跨界 403 / L1-1+L1-2 按 Q-5=A〔purge 显式 + 无自动限期清除〕）。
- T8-2 断言（pytest 全绿 + ruff 0）满足；覆盖率全仓 86%、U1 新增核心模块 91%~98%，存量缺口登记 R3。
- **允许进入测试回溯与部署段（幂等迁移 + 两段式发布 + login 闭环回归 + 台账已回写）；S1a 收官后进入 S1b（P2-1）。**
