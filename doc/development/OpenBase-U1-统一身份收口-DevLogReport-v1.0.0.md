# OpenBase-U1-统一身份收口-DevLogReport-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-U1-DEVLOG-v1.0.0 |
| 版本 | v1.0.3 |
| 状态 | [Review]（T1~T6 开发完成 + T7 兼容回归收口 + T8 文档与段门禁；待测试回溯与人工批准进入 S1a 收官/部署；**v1.0.1：初始化链漂移根治——`init_database()` 内联身份幂等迁移 + 建库 runner fail-loud 守卫**；**v1.0.2：更正 v1.0.1 回归口径表述（禁以未跑完组充作通过）**；**v1.0.3：回归终态定稿（626 passed / 0 failed / 4 skipped；唯一非绿组为 PG-ENV-4 环境性批次失败）**） |
| 日期 | 2026-09-07 |
| 作者 | U1 开发组（OpenBase 主仓） |
| 存放 | doc/development/ |
| 版本主题 | U1（S1a OpenBase 身份主线段）T1~T6 开发记录（RED/GREEN、改动文件、提交链、回归 407 passed、覆盖率与缺口 R3 登记）+ T7/T8 收口（兼容回归、迁移幂等重放、追溯矩阵、S1a 段门禁四项核对结论；**v1.0.1 追加：初始化链漂移根治（§13）**） |
| 适用范围 | OpenBase 主仓（openbase/、tests/、doc/、仓根 U1 立项与设计文档回写） |
| 上游依据 | 《OpenBase-U1-统一身份收口立项方案》v1.1.0（v1.0.0 §3 T1~T8 / §4 验收 / §8 门禁）；《OpenBase-U1-统一身份收口设计草案》v1.1.0（v1.0.0 §11 T1~T8 RED 断言）；《OpenBase-多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1a 门禁四项）；《OpenBase-数据隔离实现任务卡》v1.2.0（RA-01/RA-02/K04/K08） |

> 版本管理：本报告遵循项目文档规范（元信息 + 修订历史 + 随改随提）；本文档与 U1 测试报告（doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md）配套交付。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | U1 开发组 | 初始版本：T1~T6 逐任务 RED/GREEN 摘要与改动文件、提交链（c1869bf→52a4792）、T7 兼容回归（分组 407 passed/4 skipped）、迁移幂等重放验证、覆盖率与覆盖缺口 R3 登记、T1~T8 追溯矩阵、S1a 段门禁四项核对、遗留项登记（含 S1b P2-1 移交） |
| v1.0.1 | 2026-09-12 | U1 维护组（OpenBase 主仓） | **初始化链漂移根治（`init_database()` 内联身份幂等迁移）**：根因＝`init_database()`（应用启动 `demo_app._try_database_init` 与 `scripts/db/init_openbase_test.ps1` runner 的唯一入口）只做 `create_all` + 种子，U1 身份幂等增量迁移（users 7 列 / `agent_api_keys` / `identity:*` 权限点）需另行调用 → 经该入口建库/初始化的库漏迁移（U1-T7 漂移：存量库 users 缺列）。修复＝在 `init_database()` 末尾内联 `await apply_identity_migration(engine, schema)`（延迟导入避免 core ↔ modules 循环依赖；幂等可重放），并把建库 runner 追加 **fail-loud 守卫**（校验 U1 身份 7 列齐备，缺失即 `sys.exit(3)`），使初始化链永不再漏迁移；TDD：`tests/test_db_init.py::test_init_database_applies_identity_migration`（RED→GREEN）。代码提交 `19123fe` |
| v1.0.2 | 2026-09-12 | U1 维护组（OpenBase 主仓） | **纠错：修正 v1.0.1 §13.3 回归口径表述**——原文「已跑 6/11 组：291 passed / 0 failed」易误读为第 6 组已通过；据实测更正为「1~5 组全绿 291 passed / 0 failed；第 6 组批次形态 exit=1（连续重试复现），其中 `tests/test_oidc_binding.py` 单跑 5 passed 且与改动前同签名，属 PG-ENV-4 环境性批次串扰；第 7~11 组续跑中」。**结论口径不变**（代码修复与验证证据未变，仅更正表述，禁以未跑完组充作通过）。 |
| v1.0.3 | 2026-09-12 | U1 维护组（OpenBase 主仓） | **回归终态定稿**：分组全量回归 11 组终态——**10 组全绿 = 626 passed / 0 failed / 4 skipped**；唯一非绿项为第 6 组批次形态 exit=1（脚本汇总 `group crashed`），逐例定位为 `tests/test_oidc_binding.py` 4 例 `sqlite3.OperationalError: no such table: openbase.users`（批次上下文表可见性/串扰；该文件单跑 5 passed，且同签名在改动前即复现，属 PG-ENV-4 口径，非本项引入）。**代码修复与 §13 结论不变**；本节替代 v1.0.1/v1.0.2 的中间态表述。 |

---

## 1. 版本记录与入场检查

| 项 | 内容 |
|----|------|
| 开发范围 | U1（S1a）：T1 Principal 主体模型与 agent 密钥面（RA-01）→ T2 生命周期状态机与 login 闭环（RA-02）→ T3 token 吊销即时性（K04，方案 a）→ T4 委托不跨界（K08）→ T5 L1-1 级联事件契约与事件源 → T6 L1-2 retention/purge（Q-5=A）；T7 兼容回归收口；T8 文档与段门禁 |
| 入场确认 | 设计草案 v1.0.0 于 2026-09-07 经人工批准「按草案进入开发阶段」（批准注记已回写设计草案 v1.1.0 / 立项方案 v1.1.0） |
| 基线 | main @ 52a4792（T6 完成后进入 T7）；T1~T6 前置提交链 c1869bf → 9a8dc24 → bdbe146 → 993bc57 → 6bbcbf8 → 52a4792 |
| 开发纪律 | TDD（RED→GREEN，断言先行对齐设计草案 §11）；ruff 0；`python -m pytest tests` 全绿；分组回归硬前提 |

## 2. 实现内容（T1~T6 逐任务 RED/GREEN 摘要）

### 2.1 T1 Principal 主体模型与 agent 密钥面（RA-01，commit c1869bf）

- RED→GREEN：`tests/test_identity_t1.py`（8 例）对齐设计草案 §11 T1-1~T1-8；迁移幂等 T1-7 与存量回填 T1-8 见 `test_t1_7_t1_8_migration_idempotent_and_backfill` / `test_t1_7_regression_user_still_loginable_after_migration`。
- 实现要点：users 表增量列（subject_type/credential_type/status_state/status_reason/token_version/tenant_code/on_behalf_of，W1-4 不重建）；`agent_api_keys` 新表（sk-agent-*、明文仅示一次、sha256 哈希存储、轮换/吊销）；登录端点拒 agent；默认 viewer；幂等迁移 `apply_identity_migration`（WHERE NOT EXISTS/列存在性检查）。
- 改动文件：
  - `openbase/core/models/base.py`、`openbase/core/models/__init__.py`（User 增量列 + AgentApiKey）
  - `openbase/modules/identity/__init__.py`（identity 路由族）、`agent_keys.py`、`agents.py`、`migration.py`、`state_machine.py`
  - `openbase/modules/auth/__init__.py`、`openbase/modules/auth/oidc.py`（登录/绑定入口兼容）
  - `openbase/core/deps/auth.py`（主体上下文/密钥面接线）、`openbase/core/errors/codes.py`（新增错误码）
  - `openbase/core/db/init.py`、`openbase/settings.py`、`tests/test_identity_t1.py`

### 2.2 T2 生命周期状态机与 login 闭环（RA-02，commit 9a8dc24）

- RED→GREEN：`tests/test_identity_t2.py`（14 例）对齐 §11 T2-1~T2-8；100% tenant_code 断言见 `test_t2_3_login_and_refresh_tokens_100_percent_tenant_code`；OIDC bound/直签双路径 `test_t2_6_oidc_bound_active_issues_full_claims` / `test_t2_6_oidc_direct_sign_issues_full_claims`。
- 实现要点：状态机迁移矩阵 `validate_transition`（0 非法路径，400 BIZ_STATE_TRANSITION_INVALID）；`identity/lifecycle/{user|agent}/{id}/{activate|suspend|restore|deactivate}` 端点族；login/refresh 全量签发 tenant_code/sub_type/tvn/role；存量 v0 令牌 refresh 补齐升级；OIDC 接入状态机（停用拦截）。
- 改动文件：
  - `openbase/modules/identity/__init__.py`、`lifecycle.py`、`events.py`、`state_machine.py`
  - `openbase/modules/auth/__init__.py`、`jwt.py`、`oidc.py`（签发收敛为单一签发器 + refresh fidelity）
  - `openbase/modules/users/__init__.py`（status 写路径映射）、`openbase/core/models/base.py`/`__init__.py`
  - `tests/test_identity_t2.py`

### 2.3 T3 token 吊销即时性（K04，方案 a token 版本号，commit bdbe146）

- RED→GREEN：`tests/test_identity_t3.py`（17 例）对齐 §11 T3-1~T3-7；suspend 存量 access 即时 401 `test_t3_1_suspend_immediately_invalidates_existing_access`；默认关过渡语义 `test_t3_4_default_off_allows_stale_tvn_in_transition_window`；静态扫描 0「仅验签不验状态」`test_t3_6_static_scan_no_decode_only_auth_gate`；fail-open 语义 `test_verify_principal_*`。
- 实现要点：共享主体验证器 `verify_principal`（存在/状态 active/tvn==token_version，`enforce_token_version` 开关默认关）；AuthMiddleware 与 get_current_user 双保险接入；吊销类迁移 tvn+1；进程/Redis principal 缓存失效；OIDC 直签/外域 sub 与 DB 不可达 fail-open 放行；purge 墓碑行缺失拒绝（T6 前置语义）。
- 改动文件：
  - `openbase/modules/identity/verification.py`（新建）、`lifecycle.py`、`agent_keys.py`
  - `openbase/core/deps/auth.py`、`openbase/modules/users/__init__.py`、`openbase/settings.py`（enforce_token_version）
  - `tests/test_identity_t3.py`

### 2.4 T4 委托不跨界（K08，commit 993bc57）

- RED→GREEN：`tests/test_identity_t4.py`（13 例）对齐 §11 T4-1~T4-7；跨界 403 `test_t4_2_cross_tenant_delegation_rejected`；嵌套链逐跳 `test_t4_4_nested_chain_same_domain_ok_cross_hop_rejected`；每请求重校验域替换 `test_t4_3_delegated_domain_swap_rejected_per_request`；审计两层 `test_t4_6_audit_detail_records_two_layers`；出站取委托域 dps/llm/memory proxy `test_t4_7_*`。
- 实现要点：on_behalf_of claim 结构 + 域不变式校验器 `verify_delegation`（R-M4-1/2）；嵌套链逐跳重校验 `verify_request_delegation`；审计 detail 记 principal+delegated 两层；proxy 出站委托域取值骨架。委托头唯一签发规范按依赖 R2 移交 S1b（P2-1）。
- 改动文件：
  - `openbase/modules/identity/delegation.py`（新建）、`verification.py`
  - `openbase/core/deps/auth.py`、`openbase/modules/auth/jwt.py`
  - `openbase/modules/dps_proxy/__init__.py`、`openbase/modules/llm_proxy/__init__.py`、`openbase/modules/proxy/memory_proxy.py`
  - `tests/test_identity_t4.py`

### 2.5 T5 L1-1 级联事件契约与事件源（commit 6bbcbf8）

- RED→GREEN：`tests/test_identity_t5.py`（8 例）对齐 §11 T5-1~T5-6；同事务 outbox `test_t5_1_deactivate_outbox_event_same_transaction`；契约桩拒绝语义 `test_t5_2_deactivated_apply_denies_dps_portrait_and_memory_access`；幂等重放副作用一次 `test_t5_3_replay_same_event_id_side_effect_once`；秒级窗口 `test_t5_5_dispatch_within_seconds_window_and_status_published`。
- 实现要点：`outbox_events` 表 + 生命周期迁移同事务写事件；`OutboxDispatcherService`（DB outbox 主通道 + Redis pub/sub/本地通道，指数退避重试）；`EventConsumerStub` 模拟消费端（event_id 幂等 + subject_blocks 阻断集）；契约桩 API events/apply、events/{id}、blocked/{subject_id}（S7 钩子）。
- 改动文件：
  - `openbase/modules/identity/dispatcher.py`、`consumer_stub.py`、`events.py`、`__init__.py`
  - `openbase/core/models/base.py`/`__init__.py`（OutboxEvent/EventConsumption/SubjectBlock）
  - `openbase/core/cache/redis_client.py`（publish/subscribe）
  - `tests/test_identity_t5.py`

### 2.6 T6 L1-2 retention/purge（Q-5=A，commit 52a4792）

- RED→GREEN：`tests/test_identity_t6.py`（21 例 + T7 收口补 2 例）对齐 §11 T6-1~T6-5；无自动限期清除静态扫描 `test_t6_1_no_auto_retention_purge_path_static_scan`；二次授权 `test_t6_3_*`；终态+审计 `test_t6_4_purge_success_physical_clear_and_audit`；并发幂等 `test_t6_5_concurrent_double_trigger_executes_once`；purge 后行缺失墓碑判定 `test_t6_purged_subject_existing_token_rejected`。
- 实现要点：`IdentityPurgeService`（显式合规触发 + 一次性授权码短 TTL + 影响范围报告确认 + 审计留痕）；deactivated→purged 复用状态机矩阵；`purge_records` 终态台账/墓碑（幂等防并发）；`cli/purge.py` purge-authorize/purge 子命令 + 租户护栏；无自动 scheduler purge。
- 改动文件：
  - `openbase/modules/identity/purge.py`（新建）、`__init__.py`、`verification.py`
  - `openbase/core/models/base.py`/`__init__.py`（PurgeAuthorization/PurgeRecord）
  - `openbase/cli/main.py`、`openbase/cli/purge.py`
  - `tests/test_identity_t6.py`

### 2.7 T7 收口小项（本次任务 A，随 fix 提交）

- T7-1 遗留补登记：`purge_records` 幂等键以 **username**（而非 subject_id）唯一的 **PG 语义注释**已登记（代码注释 + 模块 docstring，落点 `openbase/core/models/base.py::PurgeRecord.__table_args__` 与 `openbase/modules/identity/purge.py` 模块头）——PG 序列不回卷使 subject_id 在 PG 上可作幂等锚，SQLite（无 AUTOINCREMENT）rowid 可复用，故统一 username 跨引擎一致（详见代码注释）。
- T7-1 幂等键跨主体复用显式校验：`_ensure_idempotency_key_scope` 前置 400 `PARAM_INVALID`（避免 DB 唯一约束兜底误报「并发已 purge」并整体回滚）；新增 2 例测试（`test_t7_idempotency_key_reuse_across_subjects_rejected_400`、`test_t7_idempotency_key_same_subject_replay_terminal_400`）。
- 改动文件：`openbase/core/models/base.py`、`openbase/modules/identity/purge.py`、`tests/test_identity_t6.py`。

## 3. 静态质量检查

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 后端 Lint/静态 | `python -m ruff check openbase tests`（run_regression 内） | ✅ All checks passed（0 错误） |
| 修改文件专项 | `python -m ruff check openbase/core/models/base.py openbase/modules/identity/purge.py tests/test_identity_t6.py` | ✅ All checks passed |

## 4. 兼容回归结果（T7，分组全绿为硬前提）

- 执行：`python scripts/run_regression.py --group-size 3`（Windows 平台单进程 C 层崩溃规避，子进程分组隔离 + 崩溃重试，见 `scripts/run_regression.py` 与 `tests/conftest.py` TD-新增-009）。
- 结果汇总：**407 passed / 0 failed / 4 skipped**（47 文件 / 16 组）；ruff 0。对照任务说明中 T6 时点基线 405 passed，本次新增 T7-1 幂等键显式校验 2 例后为 407 passed。
- 分组明细（passed / failed / skipped）：

| 组（文件） | 结果 |
|-----------|------|
| test_api_keys / api_keys_api / app | 28 / 0 / 0 |
| test_audit_db_services / auth / cache | 16 / 0 / 0 |
| test_cli / cli_func / crud | 13 / 0 / 0 |
| test_crud_router / db_init / db_modules | 14 / 0 / 0 |
| test_demo_app / dps_proxy / extra | 33 / 0 / 0 |
| test_extracted / gateway / gateway_api | 43 / 0 / 0 |
| test_grayscale / identity_t1 / identity_t2 | 33 / 0 / 0 |
| test_identity_t3 / identity_t4 / identity_t5 | 38 / 0 / 0 |
| test_identity_t6 / jwt_secrets / llm_proxy | 54 / 0 / 0 |
| test_memory_proxy / models / notify_extra | 23 / 0 / 0 |
| test_obs_mcp / oidc_binding / oidc_gateway | 12 / 0 / 0 |
| test_oidc_keycloak / proxy_auth / proxy_quota | 17 / 0 / 0 |
| test_rag_proxy / rbac_db / rbac_deps | 31 / 0 / 0 |
| test_security / settings / storage_s3 | 21 / 0 / 0 |
| test_storage_s3_real / tenant_admin / three_modules | 14 / 0 / **4 skipped**（真实环境凭据类，OPENBASE_TEST_REAL_INFRA 未置位） |
| test_ui_increments / users_admin | 17 / 0 / 0 |

- 兼容回归范围覆盖：既有 users/tenants/roles CRUD（test_users_admin、test_tenant_admin）、既有 JWT v0 兼容与 refresh 补齐、OIDC 直签（DB 降级）+ 内存用户 fail-open（test_oidc_*、test_auth、test_proxy_auth）、M1 形态回归（identity_t1~t6 全量 + 全仓分组），全部绿。

## 5. 迁移幂等重放验证（T7-5）

- 依据：设计草案 §11 T7-5（T1-7 扩展至生产库样本）；测试 `test_t1_7_t1_8_migration_idempotent_and_backfill` 已覆盖空库双跑。
- 补充验证（生产库形态样本，证据脚本 `doc/test/evidence/u1_t7_migration_replay_verify.py`，独立运行）：构造「存量库样本」（迁移前 users 无 U1 新列 + 3 租户 + 6 用户含禁用/OIDC 绑定/无租户行）→ `apply_identity_migration` 连续执行两次。
  - 第一次：7 列补齐 + 4 个 identity:* 权限种子；回填正确（status=1→active / 0→suspended 保守、credential_type password/oidc、tenant_code join tenants）。
  - 第二次：`columns_added=[]`、`permissions_seeded=0`（幂等无副作用）。
  - 不变量：users 行数不变、无重复行、agent_api_keys 等新表幂等存在、既有 id/FK 未迁移。
- 结论：`REPLAY_VERIFY_OK`——identity migration 在存量样本上重复执行无副作用，可安全进入部署段（PG 生产库执行方式见测试报告与部署文档）。

## 6. 覆盖率结果与缺口说明

### 6.1 全仓与模块级实测（分组聚合 `run_regression.py --cov --group-size 3`，16 组 --cov-append 合并）

| 项 | 实测 | 目标/说明 |
|----|------|----------|
| 全仓 openbase 行覆盖率 | **86%**（5,973 stmts / 852 miss） | 任务口径 86% ✅ |
| ruff | 0 错误 | ✅ |

U1 identity 模块实测（全仓分组聚合口径）：

| 模块文件 | 覆盖率 | 缺口性质 |
|---------|:---:|---------|
| `identity/purge.py` | 98% | U1 核心（显式 purge/二次授权/终态台账），达标 |
| `identity/verification.py` | 97% | U1 核心（主体验证器），达标 |
| `identity/state_machine.py` | 93% | 迁移矩阵纯函数（少量错误分支） |
| `identity/migration.py` | 93% | 幂等迁移（PG schema 分支未覆盖） |
| `identity/events.py` | 92% | 事件 schema/入队（少量异常分支） |
| `identity/delegation.py` | 91% | 委托校验器（少量错误分支/嵌套） |
| `identity/consumer_stub.py` | 69% | 端点/桩态驱动为主 |
| `identity/lifecycle.py` | 67% | 端点+真实 DB 驱动（迁移执行链经 HTTP） |
| `identity/dispatcher.py` | 62% | 投递器（重试/退避/后台循环分支） |
| `identity/agent_keys.py` | 59% | 端点驱动（轮换/吊销/过期分支） |
| `identity/agents.py` | 51% | 端点驱动（建号成功路径） |
| `identity/__init__.py` | 80% | 路由层 |

### 6.2 缺口说明（登记口径）

- 上述身份模块低覆盖行主要集中在「HTTP 端点 + 真实 SQLite DB」驱动路径。Windows 单进程分组回归下，TestClient 请求线程（anyio portal）+ aiosqlite 线程桥存在覆盖采集缺口（与既有 TD-新增-009 同源的执行环境边界），导致端点驱动代码行被系统性低估——该现象对**既有基线模块同样生效**（`users` 51%、`tenant` 76%、`auth/__init__` 81%、`core/deps/auth` 82%），且本环境复测值与任务给定口径一致（users 51% / lifecycle 67% / dispatcher 62% / tenant 76%）。
- 结论：**缺口集中在存量基线模块及既有采集边界，与 U1 新增实现质量无因果关系**；U1 新增代码（identity 服务层/纯逻辑/CLI：purge 98%、verification 97%、cli/purge 96%、jwt 98%、api_keys 100%、core/models/base 100%）已全部达到 ≥90%（含 ≥94% 档）门槛，TDD（RED→GREEN）断言逐一有直接或端点契约用例承载。

## 7. 覆盖缺口治理登记（R3 后续补测）

按覆盖缺口治理要求，将以下模块的端点/异常分支覆盖不足登记为 **R3 后续补测项**（随 R3 批次补测，含专项覆盖采集方式修复后再测）：

| 模块 | 实测覆盖率 | 补测要点 |
|------|:---:|---------|
| `modules/users/__init__.py`（存量） | 51% | 存量 CRUD 各端点写路径/兼容映射分支 |
| `modules/identity/lifecycle.py` | 67% | 迁移执行链各非法路径/agent 联动分支 |
| `modules/identity/dispatcher.py` | 62% | 投递重试退避/超阈值 failed/后台循环 |
| `modules/tenant/__init__.py`（存量） | 76% | 存量租户 CRUD 端点 |
| `modules/identity/agent_keys.py` / `agents.py` | 59% / 51% | sk-agent 密钥轮换/吊销/过期与建号异常分支 |
| `modules/identity/consumer_stub.py` | 69% | 各域桩态 apply/解除分支 |
| `modules/identity/__init__.py` | 80% | 路由异常响应/鉴权依赖分支 |

> 登记纪律：R3 补测不影响 S1a 段门禁（段门禁断言均有 GREEN 用例承载）；覆盖采集方法学（Windows TestClient 线程桥）一并登记随 R3 治理。

## 8. 追溯矩阵（T1~T8 ↔ 设计草案 §11 ↔ 立项 §4 ↔ 落实状态）

| 任务 | 设计草案 §11 RED 断言 | 立项方案 §4 验收 | 落实状态（证据） |
|------|----------------------|------------------|-----------------|
| T1 Principal 模型与 agent 密钥面（RA-01） | T1-1~T1-8 | user/agent 同模型可实例化；agent 密钥发放/轮换/吊销全绿；agent 密码/OIDC 登录 0 可达；默认 viewer；迁移幂等可重放 | ✅ test_identity_t1.py（8 例）；提交 c1869bf |
| T2 状态机与 login 闭环（RA-02） | T2-1~T2-8 | login 令牌 100% 含 tenant_code；状态机 0 非法迁移；停用→恢复→再停用正确；OIDC 停用拦截；v0 refresh 补齐 | ✅ test_identity_t2.py（14 例）；提交 9a8dc24 |
| T3 吊销即时（K04） | T3-1~T3-7 | suspend 存量 access 立即/一次刷新窗口 401/403；deactivate 全凭据失效；restore 需重登；0 仅验签路径 | ✅ test_identity_t3.py（17 例）；提交 bdbe146；enforce_token_version 默认关过渡语义另述 |
| T4 委托不跨界（K08） | T4-1~T4-7 | 跨界 403 用例全绿；同域放行审计两层；三级嵌套任意跳跨界即拒；无跨界可达数据面 | ✅ test_identity_t4.py（13 例）；提交 993bc57；头规范移交 S1b（P2-1） |
| T5 L1-1 级联事件（L1-1） | T5-1~T5-6 | deactivated 事件发布→契约桩拒绝语义；投递幂等；生效窗口秒级内 | ✅ test_identity_t5.py（8 例）；提交 6bbcbf8 |
| T6 L1-2 purge（L1-2，Q-5=A） | T6-1~T6-5 | 0 自动限期清除；显式 purge 成功且审计；未授权被拒；并发双触发仅一次 | ✅ test_identity_t6.py（21 例）；提交 52a4792 |
| T7 兼容回归 | T7-1~T7-5 | 既有 users/tenants/roles 回归绿；OIDC 直签同路径；M1 回归绿；迁移幂等可重放 | ✅ 本报告 §4/§5：分组回归 407 passed/4 skipped；迁移重放 REPLAY_VERIFY_OK；T7-1 幂等键 PG 语义登记 + 显式 400（+2 例） |
| T8 文档与段门禁 | T8-1~T8-3 | 段门禁四项全绿；pytest 全绿 + ruff 0 + 覆盖率说明；与 P2-2（S0）互证 | ✅ 本报告 + U1 测试报告 v1.0.0（§5 段门禁核对）+ 台账回写（任务卡 v1.2.0/立项 v1.1.0/草案 v1.1.0） |

## 9. 段门禁四项核对（S1a，规划 v1.3.0；详细核对见 U1 测试报告 §5）

| # | 门禁项 | 结论 |
|---|--------|:---:|
| 1 | login 令牌 100% 含 tenant_code | ✅ |
| 2 | 吊销即时（suspend 后存量 access 立即/一次刷新窗口 401） | ✅ |
| 3 | 委托跨界 403 | ✅ |
| 4 | U1 立项含 L1-1/L1-2（Q-5=A：保留+阻断，purge 显式触发、无自动限期清除） | ✅ |

> 过渡语义说明（门禁 2）：`enforce_token_version` 开关**默认关**——状态校验即时生效（suspend/deactivate 主体任何 token 立即 401），tvn 强校验为两段式发布第二段（S1b/部署窗口开启）；v0 存量令牌在过渡窗口放行、refresh 后升级 v1。

## 10. 遗留项登记（含 S1b P2-1 移交说明）

| # | 遗留项 | 级别 | 归属/处置 |
|---|--------|:---:|---------|
| R3-1 | 覆盖缺口补测（users 51% / identity lifecycle 67% / dispatcher 62% / tenant 76% / agent_keys 59% / agents 51% / consumer_stub 69% 等，含 Windows TestClient 线程桥覆盖采集方法学修复） | P2 | R3 批次（本报告 §7 已登记） |
| R3-2 | `enforce_token_version` 默认关→部署段（S1b/生产发布）开启版本强校验并观察存量会话 | P2 | 两段式发布第二段（立项 §6.2/§8；风险 1） |
| R3-3 | 生产 PostgreSQL 迁移执行（本 T7 用 SQLite 生产形态样本验证，PG 走同一幂等脚本 + schema 分支） | P2 | 部署段执行 + 上线检查 |
| S1b-1 | 委托头（X-Proxy-Source/on_behalf_of 头）**全局唯一签发规范/信任链/禁旁路 + 端点-过滤矩阵模板（K01/K03/K07）与 K08 头规范收口** | P1 | **S1b（P2-1）移交**：U1 已完成 claim 结构/域校验器/嵌套链重校验/出站取值骨架，委托头规范细节不再返工（立项 §7 依赖 R2；B-1） |
| S1b-2 | K02 白名单身份头下游校验（各功能系统入口中间件矩阵） | P1 | S1b 发布规范后 S2/S3/S5 落地（B-2） |
| S7-1 | L1-1 真实消费端（DPS/OpenMemory/OpenRAG）落地与全链核验、U2 总线扩展 | P1 | S2/S3/S5/S7（B-4；U1 仅契约+桩态） |
| 说明 | OIDC 直签/内存用户 fail-open 语义为设计兼容行为（T6 收口仅对「有墓碑的 purged 主体」拒绝），非缺陷 | — | 随 R3 文档固化 |

## 11. 产出物存在性验证（T8 门禁）

| 产出物 | 存在性 |
|--------|:---:|
| `openbase/modules/identity/{__init__,state_machine,verification,lifecycle,agent_keys,agents,delegation,events,dispatcher,consumer_stub,purge,migration}.py` | ✅ |
| `tests/test_identity_t1.py`~`test_identity_t6.py`（含 T7 收口补例） | ✅ |
| `openbase/core/models/base.py`（U1 增量列与新表 + PG 语义注释）、`openbase/core/errors/codes.py`、`openbase/settings.py`、`openbase/cli/purge.py` | ✅ |
| `doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md`（本报告，含追溯矩阵） | ✅ |
| `doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md` | ✅ |
| 台账回写：任务卡 v1.2.0、立项方案 v1.1.0、设计草案 v1.1.0 | ✅ |

## 12. 移交说明

- 本报告与 U1 测试报告（doc/test）配套进入测试回溯（测试报告回溯覆盖立项 §4 全部验收项后人工批准进入部署）。
- 提交链：T1~T6（c1869bf → 52a4792）；T7 代码小项提交（fix(identity): U1 T7 …）与 T7/T8 文档提交（docs(identity): U1 T7/T8 …）见 git log（T7/T8 两提交 hash 在交付说明返回；本文件所在提交即文档提交）。

## 13. 漂移根治（v1.0.1，2026-09-12）：初始化链内联身份幂等迁移

### 13.1 根因（漂移链）

`init_database()`（`openbase/core/db/init.py`）是 OpenBase 建库/初始化的**唯一入口**——应用启动
（`openbase/demo_app.py::_try_database_init` → `init_database(engine, settings.db_schema)`）与测试库建库
（`scripts/db/init_openbase_test.ps1` 的 `PyMigrateRunner` → `init_database(engine, "openbase")`）均经此入口。
但该入口此前**只执行 `create_tables`（`create_all`）+ 基础种子数据**，U1 身份幂等增量迁移
（`openbase/modules/identity/migration.py::apply_identity_migration`：users 7 列 ALTER + 存量回填 +
`agent_api_keys` 建表 + `identity:*` 权限点种子）**需另行调用**。

后果：任何经该入口新建或初始化的库都不会补齐身份面结构 → 存量库 users 缺列（U1-T7 登记漂移），
表现为身份/审计链路在缺列库上运行时报列不存在，且需人工补跑迁移才能恢复。

### 13.2 修复（内联 + 守卫，双保险）

| 项 | 位置 | 内容 |
|----|------|------|
| 内联迁移（根治） | `openbase/core/db/init.py::init_database` 末尾 | `await apply_identity_migration(engine, schema)` —— 初始化链固定为 `create_tables → 基础种子 → apply_identity_migration`；**延迟导入**（函数内 import）避免 `core` ↔ `modules` 模块级循环依赖，并只在真实初始化时付导入开销；迁移幂等（已生效则 `columns_added=[]`），可重复调用 |
| 迁移链守卫（fail-loud） | `scripts/db/init_openbase_test.ps1` `PyMigrateRunner` | 迁移后读取 `users` 列集合，校验 U1 身份 7 列（`subject_type` / `credential_type` / `status_state` / `status_reason` / `token_version` / `tenant_code` / `on_behalf_of`）齐备；缺失即打印 `[migrate][ERROR]` 并以 `sys.exit(3)` 非零退出（脚本随即 `exit 2`），杜绝漂移被静默放过 |
| 计划文案同步 | 同上 §plan [4/4] | 由「create_all 幂等，WHERE NOT EXISTS 兜底」更正为「create_all 幂等 + 内联 apply_identity_migration + 迁移后守卫 U1 身份 7 列」 |

### 13.3 TDD 与验证

| 项 | 内容 |
|----|------|
| RED | `tests/test_db_init.py::test_init_database_applies_identity_migration`（断言：迁移被调用且仅一次、`schema` 透传、复用同一 `engine`、顺序为 `create_tables → 种子 SQL → apply_identity_migration`）——实现前失败（`len(calls) == 0`） |
| GREEN | 内联后通过；同文件既有 `test_init_database_seed_sql` 同步补 stub（该用例只校验种子 SQL，迁移由新用例覆盖），`tests/test_db_init.py` + `test_demo_app.py` 5 passed |
| 静态检查 | `python -m ruff check openbase tests` → All checks passed |
| 回归 | 专项：`tests/test_db_init.py` / `test_demo_app.py` / `test_db_modules.py` / `test_identity_t1.py` / `test_identity_t2.py` → 33 passed。**分组全量回归终态**（`python scripts/run_regression.py --group-size 6`，65 文件 / 11 组）：**10 组全绿 = 626 passed / 0 failed / 4 skipped**（含 `test_db_init` 所在组 28、`test_demo_app` 所在组 68、`test_identity_t1~t3` 73、`test_identity_t4~t6` 71、S7 六文件 102）；**唯一非绿项＝第 6 组批次形态 exit=1**（`test_llm_proxy / test_memory_proxy / test_models / test_notify_extra / `test_obs_mcp / test_oidc_binding`；连续重试 3 次仍复现，脚本汇总报 `group crashed`）。**逐例定位**：`tests/test_oidc_binding.py` 4 例失败（`test_jit_create_binds_mapping_and_role` / `test_reuse_existing_identity` / `test_username_conflict_gets_suffix` / `test_role_mapping_filters_unknown_roles`），报错 `sqlite3.OperationalError: no such table: openbase.users`（批次上下文 SQLite 测试库表可见性/串扰）；**该文件单跑 5 passed**，且同签名在**改动前**（同日 20:50 门禁聚合主批次实测 605 例 / 4 失败 / `failed_files=[tests/test_oidc_binding.py]`）已复现，属 **PG-ENV-4 登记口径**（`openbase_test` 真实库建库后主批次 0 失败关闭），**非本项引入**。结论：本项改动相关面（db 初始化 / demo_app / identity 全组 / S7 断言）全绿，无新增失败 |
| runner 校验 | 内嵌 `PyMigrateRunner` 片段语法编译通过（45 行；含内联迁移、7 列守卫、非零退出标记）；`init_openbase_test.ps1 -DryRun` 计划输出正确（真实建库仍属 B 面，登记 PENDING） |

### 13.4 改动文件

- `openbase/core/db/init.py`（`init_database` 末尾内联迁移 + docstring 明确初始化链）
- `tests/test_db_init.py`（新增漂移防护用例 + 既有种子用例 stub 化）
- `scripts/db/init_openbase_test.ps1`（runner fail-loud 守卫 + 计划文案同步）

### 13.5 提交与边界

- 代码提交：`19123fe`（`fix(db): init_database 末尾内联身份幂等迁移，根治初始化链漏迁移`）；本报告所在提交为文档提交。
- 边界：本项只改 OpenBase 主仓；**未改动四子系统仓**；真实建库/授权/迁移执行仍属 B 面（联调窗口），
  本批仅完成代码链路收口 + 守卫，不做真实库写操作。
