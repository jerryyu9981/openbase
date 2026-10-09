# OpenBase B1 生产化配套：权限播种脚本 + 影子期观测聚合

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase-B1-生产化配套-权限播种与影子期观测 |
| 文档版本 | v1.2.0 |
| 状态 | **[Approved]**（D1/D2 裁定已采纳；D2 的接线实现口径以其复核为准） |
| 适用环境 | OpenBase 仓库（工具脚本）；产物面向共享基础设施（局域网唯一共享库）的 OpenLLM 权限表 |
| 作者 | Dev-OpenBase（AI 辅助编码，人工过目） |
| 创建日期 | 2026-10-08 |
| 更新日期 | 2026-10-09 |
| 存放 | doc/design/ |
| 上游依据 | 《OpenBase-B1派单-OpenLLM授权接线-v1.0.0》（§3 交付要求 5/§4 验收 6）；`config/rbac_permission_model.json`（人工裁定唯一输入）；`config/role_tier_anchors.json`；《OpenBase-B1-播种SQL评审与执行预检说明-v1.1.0》 |
| 输入（只读，勿改） | `config/rbac_permission_model.json` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-08 | Dev-OpenBase | 初始创建：落地「交付 A 播种脚本」与「交付 B 影子期观测聚合」，按 TDD 最小改动实现；登记验证证据、五条校验触发结果、产物形态与执行责任结论、风险与未覆盖项 |
| v1.1.0 | 2026-10-09 | Dev-OpenBase | **落点更正 + 新增护栏**：经只读探查证实 B1 真实落点为**目标库 public schema 的目标系统自身权限表**（主键 uuid），v1.0.0 误写 `"openbase"."roles"` 属目标错配。本版改数据模型来源为**目标系统自身表结构**，新增**目标档案表**与生成期校验、**落点护栏**，roles/permissions 用 `(code)`、role_permissions 用 `(role_id, permission_id)` 冲突键，行主键改由 `uuid5` 生成；保持永远 dry-run/不 import 数据库驱动；TDD 扩至 10 例并重生成制品 |
| v1.2.0 | 2026-10-09 | Dev-OpenBase | **前置 DDL 与数据播种解耦（D1 裁定）+ 通配口径取 A（D2 裁定）**：(1) 前置唯一索引 DDL 从数据种子中拆出，独立产出于 `rbac_seed_ddl.sql`，`rbac_seed.sql` 退化为**纯 DML**；交付与执行按「结构先行、数据后行」两步走；(2) 明确落点为**局域网共享基础设施的唯一数据库**（四系统同实例、按 schema 区分），结构变更须经受控流程执行；(3) D2 采纳 A（B1 接线补 `*` 通配语义），播种不变；(4) TDD 扩至 11 例（新增「前置 DDL 与数据播种解耦」用例，并修正重跑确定性用例对生成时间戳的依赖）|

---

## §1 背景与目标

B1 派单回执已登记一项关键**已知风险**：角色→权限映射为**推荐基线、未写库**——强制期开启前
须播种 DB 权限矩阵（或经 JWT `permissions` 下发），否则非管理员会被误拒。配套两件工具：

- **交付 A**：把人工裁定的权限模型转成**可审阅、幂等**的播种产物（前置 DDL + 清单 + 纯 DML 播种 SQL + 差异报告），**默认不写库**；
- **交付 B**：把影子期 `rbac_decision=would_deny` 观测聚合为可消化的清单，支撑影子期出口门禁
  「消化率 100% 且无未归类调用方」（模型 `rollout.phase_1_shadow.exit_gate`）。

目标（均落地为测试用例）：
1. 播种产物齐备且含幂等 SQL，**落点 = 目标系统自身表结构**；2. 默认 dry-run 不连库/不写库；
3. **目标档案一致 + 落点护栏** + 三条业务强制校验 fail-fast；4. 影子期观测按「端点 × 角色 ×
权限码」聚合 + 消化率；5. 脏行/缺字段容错。

### 1.1 落点更正（v1.1.0 起）

只读探查（`192.168.0.151:5432/nuct`，2026-10-09）确认目标库含三个 schema：
`openbase`（本仓自身，bigint 主键、单列 code+module 模型）、`platform`、`public`（**目标系统
OpenLLM 自身**，uuid 主键、`code` 与 `resource_type/action` 四字段并存模型）。B1 要播种的是
**`public`**，而 v1.0.0 生成器把数据模型来源与落点都错配成了 `openbase`。本版起改为**目标系统
自身表结构**为数据模型来源，并引入护栏令该缺陷不可能重犯。

### 1.2 单一共享库口径（v1.2.0 起）

**局域网内共享基础设施（`192.168.0.151:5432/nuct`）是唯一的数据库**：四系统（OpenBase /
OpenLLM / OpenRAG / OpenMemory / DPS）同实例、按 schema 区分。因此 B1 的前置结构变更与数据
播种均落在该共享库上，**影响面跨系统共担**——结构变更须经共享库的受控流程执行（DBA / 迁移
窗口），数据播种须在受控窗口内执行。

---

## §2 交付物清单（本版改动文件）

| 类型 | 路径 | 说明 |
|------|------|------|
| 脚本 A（改） | `scripts/rbac_permission_seed.py` | 目标档案表 + 目标表结构模型 + 落点护栏 + uuid5 幂等；**前置 DDL 与 DML 拆分产出**；默认 dry-run |
| 测试 A（改） | `tests/test_rbac_permission_seed.py` | 11 例（含目标档案不符、禁用 schema、前置 DDL 解耦、重跑确定性等） |
| 生成产物（新增） | `doc/design/generated/rbac_seed_ddl.sql` | **前置结构变更**（`role_permissions` 唯一索引），独立交付、结构先行 |
| 生成产物（重生成） | `doc/design/generated/rbac_seed_manifest.json` | 种子清单（字段对齐目标表列） |
| 生成产物（重生成） | `doc/design/generated/rbac_seed.sql` | **纯 DML** 幂等 SQL（落点 `public.*`，供目标仓执行） |
| 生成产物（重生成） | `doc/design/generated/rbac_seed_diff.json` | 差异报告（重跑 = 0） |
| 本文档（改） | `doc/design/OpenBase-B1-生产化配套-权限播种与影子期观测-v1.2.0.md` | 本文件（自 v1.1.0 升级） |

**未改动**：`config/rbac_permission_model.json`（人工裁定唯一输入，只读）；`config/role_tier_anchors.json`；
交付 B 的 `scripts/rbac_shadow_observe.py`、`tests/test_rbac_shadow_observe.py`、
`tests/fixtures/rbac_shadow_sample.jsonl`、`doc/design/generated/rbac_shadow_observe_sample.json`；
未新增第三方依赖；**未对任何数据库执行任何 SQL（含只读探针已用后删除）**。

---

## §3 交付 A：播种脚本设计（v1.2.0）

### 3.1 数据模型来源 = 目标系统自身表结构

数据模型来源为**目标系统（OpenLLM）自身表结构**（列清单经只读探查
`information_schema` 与 OpenLLM ORM 模型双向核对）：

| 目标表 | 关键列（生成器写入的子集） | 主键 |
|--------|---------------------------|------|
| `public.roles` | `id, code, name, description, role_type, level, scope, is_active, is_system, created_at, updated_at` | uuid |
| `public.permissions` | `id, code, name, resource_type, action, scope, is_active, is_system, created_at, updated_at` | uuid |
| `public.role_permissions` | `id, role_id, permission_id, constraints, is_active, created_at` | uuid |
| `public.user_roles` | `id, user_id, role_id, is_active, created_at`（默认不播种绑定） | uuid |

映射口径：`code=module:action`；`resource_type=code` 前缀、`action=code` 后缀（四字段并存）；
`permissions.scope=platform`（系统内置口径）；`*` 通配行以 `resource_type='*', action='*'` 落库；
角色补齐 `role_type/level/scope`（对齐 `config/role_tier_anchors.json` 档位：admin=platform/100，
org_admin=org/50，其余只读角色=org/10 或 5）。清单 JSON 逐字段即目标表列。

### 3.2 目标档案表与生成期校验（护栏）

**目标档案表**（`TARGET_PROFILES`，脚本内唯一事实源）登记 `target → (库名, schema, 主键类型, 表集合)`：

| target | 库(schema) | 键类型 | 表集合 | 禁用 schema |
|--------|-----------|:------:|--------|-------------|
| `openllm`（B1 落点） | `nuct(public)` | uuid | roles / permissions / role_permissions / user_roles | openbase / platform |
| `openbase`（对照，非落点） | `nuct(openbase)` | bigint | roles / permissions / role_permission / user_role | public / platform |

生成期两道硬校验，**均在生成任何文件之前**完成：

1. **目标档案一致**（`resolve_profile` + `validate_target_profile`）：`target_system` 必须登记在
   档案表；声明 `schema/键类型/表集合` 与档案**逐项一致**，任一不符即 `SeedError`、**不落盘任何文件**；
2. **落点护栏**（`assert_sql_target`）：对渲染后的前置 DDL 与 DML **分别**校验——所有被 schema
   限定的表引用只允许 `档案 schema` 与 `档案表集合 ∪ 引用表`；所有 `INSERT INTO` 目标必须 ∈ 档案
   表集合；出现任何禁用 schema（`"openbase"` / `"platform"`）即硬失败。

### 3.3 幂等与稳定 UUID + 前置结构变更拆分

- **冲突键**：`roles` / `permissions` 用 `ON CONFLICT (code) DO NOTHING`；
  `role_permissions` 用 `ON CONFLICT (role_id, permission_id) DO NOTHING`；
- **稳定行主键**：所有行 `id` 由 `uuid5(固定命名空间, 稳定键)` 生成——
  命名空间 `8f0f6c2a-3b1d-4e57-9a6c-0d2f4b7e1c93`，键前缀 `openbase/rbac-seed/v1`
  （一经登记不得更改）；`role_permissions` 的 `role_id/permission_id` **按 code 解析**
  （`SELECT r.id, p.id ... WHERE r.code=... / p.code=...`），以兼容目标库既有角色行；
- **重跑一致**：同目录二次运行 DDL **逐字节一致**、SQL **忽略头部生成时间戳后**逐字节一致、
  清单（忽略 `generated_at`）一致、差异报告合计为 0。

> **前置结构变更与数据播种解耦（D1 裁定，v1.2.0 核心）**：实测目标库 `public.role_permissions`
> **仅有** `id` 主键、**无** `(role_id, permission_id)` 唯一约束——而 `ON CONFLICT
> (role_id, permission_id)` 依赖该唯一索引。故唯一索引 DDL **独立产出于 `rbac_seed_ddl.sql`**
> （不再内嵌于数据种子），交付与执行按「**结构先行、数据后行**」两步走；`rbac_seed.sql` 为**纯 DML**。
> 该索引落在**局域网唯一共享库**上，须经共享库的**受控结构变更流程**执行；执行前须满足：
> 目标库无重复 `(role_id, permission_id)` 行、执行账号具备 `CREATE INDEX` 权限（详见 §7）。

### 3.4 DDL 方言与执行责任

- **方言 = PostgreSQL**；schema 由目标档案决定（openllm → `public`）；DML 以事务包裹（`BEGIN; … COMMIT;`）；
  前置 DDL 为单条幂等语句（`IF NOT EXISTS`），独立执行、不混入数据事务。
- **执行责任**：前置结构变更走**共享基础设施的受控结构变更流程**（迁移 / DBA）；数据播种由
  **目标仓（OpenLLM）在共享库受控流程内**执行。本脚本默认且始终 dry-run，**不提供 `--apply`**，
  **不 import 任何数据库驱动**（纯文本生成，见 TDD 用例 `test_script_is_pure_text_and_imports_no_db_driver`）。理由（跨系统共享库写属高影响动作）：
  结构与权限变更影响面跨系统，须人工过目、评审与回滚预案后执行。

### 3.5 强制校验（fail-fast，缺一即报错退出、不落盘任何文件）

| # | 校验 | 判定 | 违规信息样例 |
|:-:|------|------|--------------|
| 1 | 目标档案一致 | 声明 schema/键类型/表集合须与档案逐项一致 | `目标档案不符：声明 schema='openbase'，档案 openllm→schema='public'` |
| 2 | SQL 落点护栏 | 声明 target=openllm 时 SQL 只允许 `"public".*`；出现 `"openbase"` 即失败 | `落点护栏：目标 openllm 禁止写入 schema "openbase"，但生成的 SQL 中出现该 schema` |
| 3 | 无悬空码 | 授予引用的权限码必须 ∈ `modules[*].codes`（`*` 除外） | `悬空权限码：角色 org_admin 授予了 modules[*].codes 中不存在的 'unknown_module:read'` |
| 4 | 只读角色约束 | `user/org_member/viewer` 不得持有 `*:write`/`*:delete`/`*:admin`（含 `*`） | `只读角色违规：user 持有写类权限码 'user:write'（契约 *:write/*:delete/*:admin）` |
| 5 | 禁授约束 | `forbidden_grants` 的码不得出现在除 `admin` 外任何角色的授予里 | `禁授违规：非 admin 角色 org_admin 持有 forbidden_grants 权限码 'role:admin'` |

---

## §4 交付 B：影子期观测聚合设计（v1.0.0 起沿用，未改动）

### 4.1 输入与容错解析

输入：OpenLLM 结构化日志（JSON Lines，`--log` 指定）。因 OpenLLM 为独立仓库，采用**容错解析**
（不硬编码单一字段名）：判定字段支持 `rbac_decision`（别名 `decision`/`rbac_result`…），
并支持从 `message` 文本 `rbac_decision=would_deny` 正则提取；端点/角色/主体/权限码/request_id
支持多别名与 `rbac/request/http/headers/user` 嵌套子对象。非 JSON 行、非对象行计入
`skipped_lines`（跳过），合法但非 `would_deny` 的行不计入。

### 4.2 输出结构与消化率定义

按「端点 × 角色 × 权限码」聚合，输出：

- `totals.would_deny`（事件总数）、`totals.groups`（组数）；
- `groups[]`：每项 `{endpoint, role, permission, count, role_known, model_allows,
  permission_known, samples[]}`（`samples` = 代表性 request_id 样例）；
- `skipped_lines`（脏行计数）；
- `digestion`：`{digestion_rate, classified_events, unclassified_events,
  model_allows_events, model_denies_events}`；
- `unclassified_roles`（未归类调用方角色码 → 计数）。

**消化率**：`digestion_rate = classified_events / total_events`；`model_allows_events` =
归类后按模型**本应被允许**（授予含该码或 `*`）——**需消化的阻塞项**。

### 4.3 只读保证

脚本不连库、不改任何服务、不写库；`--json` 可将报告落盘为 JSON 证据，其余仅打印 stdout。

---

## §5 验证证据（实际输出）

### 5.1 TDD 结果

用例共 11 例（`tests/test_rbac_permission_seed.py`）。本机实跑（Python 3.13 + 该环境 SQLAlchemy）为
**10 passed / 1 failed**；失败的唯一用例 `test_default_is_dry_run_and_never_touches_db` 系**环境兼容性**
（Python 3.13 与所装 SQLAlchemy 版本的 `TypingOnly` 断言冲突，导入 `openbase.core.db.session` 时触发），
**与本改动无关**（详见 §7）。

```
$ python -m pytest tests/test_rbac_permission_seed.py -o addopts="" -o pythonpath=. -q
.F.........                                                              [100%]
1 failed, 10 passed
```

用例清单（11）：`test_seed_generates_artifacts_with_idempotent_sql`、
`test_default_is_dry_run_and_never_touches_db`、
`test_script_is_pure_text_and_imports_no_db_driver`、
`test_target_profile_mismatch_fails`、`test_sql_with_forbidden_schema_fails`、
`test_forbidden_grant_to_non_admin_role_fails`、`test_readonly_role_with_write_code_fails`、
`test_dangling_permission_code_fails`、`test_rerun_is_deterministic_and_diff_zero`、
`test_prerequisite_ddl_is_separate_from_dml`、`test_diff_report_lists_added_and_removed`。

### 5.2 静态检查

```
$ python -m ruff check scripts tests
All checks passed!
```

### 5.3 实机 dry-run（播种脚本；两次运行）

```
$ python scripts/rbac_permission_seed.py
[rbac_permission_seed.py] mode=dry-run applied=False target=openllm schema=public roles=5 permissions=27 role_permissions=34 user_role=0
  清单：doc\design\generated\rbac_seed_manifest.json
  DDL ：doc\design\generated\rbac_seed_ddl.sql（前置结构变更；由目标仓结构变更通道先执行）
  SQL ：doc\design\generated\rbac_seed.sql（纯 DML，幂等；由目标仓执行）
  差异：doc\design\generated\rbac_seed_diff.json（变更项合计 0；0 = 与既有清单一致）
```

### 5.4 生成 SQL / DDL 头部（目标库/schema/档案/计数）

`rbac_seed_ddl.sql`（前置结构变更，独立交付）：

```sql
-- rbac_seed_ddl — 由 rbac_permission_seed.py 生成（前置结构变更；独立于数据播种执行）
-- 目标系统（逻辑）：openllm；目标库：nuct；schema：public
-- 用途：为 public.role_permissions 的幂等冲突键 (role_id, permission_id) 建唯一索引（rbac_seed.sql 的 ON CONFLICT 依赖之）。
-- 执行责任：**由共享基础设施（局域网唯一共享库）的受控结构变更流程（迁移 / DBA）执行**；本脚本不连库、不写库。
-- 执行前置（缺一不可）：
--   1) 只读预检重复行必须为 0（非 0 须先由目标仓消重）：
--      SELECT role_id, permission_id, COUNT(*) FROM "public"."role_permissions"
--      GROUP BY role_id, permission_id HAVING COUNT(*) > 1;
--   2) 执行账号须具备 CREATE INDEX 权限（否则由其 DBA 代执行本条）。
-- 回滚：DROP INDEX IF EXISTS "uq_role_permissions_role_permission";
CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permissions_role_permission ON "public"."role_permissions" ("role_id", "permission_id");
```

`rbac_seed.sql`（纯 DML，头部节选）：

```sql
-- rbac_seed_manifest — 由 rbac_permission_seed.py 生成（纯 DML；幂等，可重复执行）
-- 目标系统（逻辑）：openllm；目标库：nuct；schema：public；主键类型：uuid
-- 目标档案：表集合 ['roles', 'permissions', 'role_permissions', 'user_roles']（引用表 ['users']）；禁用 schema ['openbase', 'platform']
-- 方言：PostgreSQL；生成时间：<ts>
-- 源模型：…\config\rbac_permission_model.json
-- 计数：roles=5 permissions=27 role_permissions=34 user_roles=0
-- 幂等语义：INSERT ... ON CONFLICT DO NOTHING
--   · roles/permissions 冲突键 = (code)；role_permissions 冲突键 = (role_id, permission_id)
--   · 行主键 id 由 uuid5(固定命名空间 + 稳定键) 生成 → 重跑结果逐字节一致；
--   · 前置结构变更（唯一索引）已拆分为独立交付 rbac_seed_ddl.sql，须先行执行；本文件为纯 DML。
-- 执行责任：**由目标仓（OpenLLM）在共享基础设施（局域网唯一共享库）的受控流程内执行**；本脚本不连库、不写库（默认 dry-run）。
BEGIN;

-- 1) 角色（roles）
INSERT INTO "public"."roles" (...) VALUES (...) ON CONFLICT (code) DO NOTHING;
...
COMMIT;
```

### 5.5 INSERT 目标表计数（证据）

| INSERT 目标 | 条数 |
|-------------|:----:|
| `"public"."roles"` | 5 |
| `"public"."permissions"` | 27 |
| `"public"."role_permissions"` | 34 |
| `"public"."user_roles"` | 0（默认不播种绑定） |
| **含 `"openbase"` 的 INSERT** | **0** |

### 5.6 只读探查证据（2026-10-09 ≤ 目标库，已用后删除探针）

- schema 集合：`information_schema, openbase, pg_catalog, pg_toast, platform, public`（**同一共享库实例**）；
- `public.role_permissions` 约束：仅 `role_permissions_pkey`（`id`）——**无** `(role_id, permission_id)` 唯一索引；
- `public.roles`/`public.permissions` 唯一索引：`ix_roles_code` / `ix_permissions_code`（`code`）；
- 列清单与 OpenLLM ORM 模型（`backend/app/models/{role,permission,role_permission,user_role}.py`）一致。

---

## §6 校验的实际触发结果

| 场景 | 实际触发 | 退出码 |
|------|---------|:------:|
| ① 正常模型（target=openllm/schema=public） | roles=5/permissions=27/role_permissions=34 + 前置 DDL（独立）+ 纯 DML，落点仅 `public.*` | 0 |
| ② 默认 dry-run | `mode=dry-run applied=False`；无任何库连接/写库副作用（测试以替身断言） | 0 |
| ③ 目标档案不符（`--schema openbase`） | `目标档案不符：声明 schema='openbase'，档案 openllm→schema='public'` | 1 |
| ④ SQL 含禁用 schema | `落点护栏：目标 openllm 禁止写入 schema "openbase"…` | 1 |
| ⑤ forbidden 授予 org_admin | `禁授违规：非 admin 角色 org_admin 持有 forbidden_grants 权限码 'role:admin'` | 1 |
| ⑥ 只读角色含写码（user:write） | `只读角色违规：user 持有写类权限码 'user:write'（契约 *:write/*:delete/*:admin）` | 1 |
| ⑦ 悬空权限码 | `悬空权限码：角色 org_admin 授予了 modules[*].codes 中不存在的 'unknown_module:read'` | 1 |
| ⑧ 二次运行 | 差异合计 0；DDL 逐字节一致、SQL（忽略生成时间戳）一致 | 0 |
| ⑨ 前置 DDL 与 DML 拆分 | `rbac_seed_ddl.sql` 只含唯一索引、不含 `INSERT`；`rbac_seed.sql` 不含 `CREATE UNIQUE INDEX` | 0 |

（③~⑦ 均在**任何产物落盘之前** fail-fast：`--out-dir` 未生成任何文件。）

---

## §7 风险、假设与未覆盖项

| 项 | 说明 / 影响 | 处置 |
|----|-------------|------|
| 目标库 `public.role_permissions` 无 `(role_id, permission_id)` 唯一约束 | `ON CONFLICT (role_id, permission_id)` 依赖该唯一索引，缺失则 DML 执行失败 | **D1 裁定**：索引 DDL 独立为 `rbac_seed_ddl.sql`，**结构先行、数据后行**；须共享库受控流程执行；**若已有重复行须先消重** |
| 落点为局域网唯一共享库 | 四系统同实例，结构与数据变更影响面跨系统共担 | 结构变更走迁移/DBA；数据播种走受控窗口；执行前预检 + 回滚预案 |
| OpenLLM `Role.has_permission` 为精确码匹配（无 `*` 通配展开） | 播种的 `*` 权限行未必能"授予全部"，取决于 B1 接线是否补通配语义 | **D2 裁定采纳 A**：接线补通配语义；清单已含全部具体码，必要时可回退逐码授予 |
| `role_type/level/scope` 与 `permissions.scope=platform` 为映射取值 | 目标库无现成基线可对齐，属约定值 | §3.1 明示；评审确认后可调 |
| `user_roles` 绑定意图默认空 | 依赖目标库既有 users 行，属环境相关 | 清单以 `user_role_note` 显式声明边界 |
| SQL/DDL 未在真实库执行验证 | 本脚本按约束不写库，无法端到端验证 DDL | 由共享库受控流程执行并回执 |
| 列清单取自探查 + ORM 模型 | 若目标库与模型漂移，可能失配 | 探查命令见 §8；变更后重跑探查与生成 |
| 影子期日志字段未现场校验 | 观测脚本按多别名容错解析；若字段名不同可能漏采 | 上线前用真实日志片段回归 |
| 本机执行环境 Python 3.13 + 旧 SQLAlchemy 不兼容 | `test_default_is_dry_run_and_never_touches_db` 在导入 `openbase.core.db.session` 时因 `TypingOnly` 断言失败；**与本改动无关** | 需在项目兼容解释器（Python 3.10–3.12）下复跑该用例；不影响本交付的其余 10 例与 ruff 全绿 |
| 既有 22 项基线失败未清理 | 派单 `production_gates` 项；本轮不涉 | 与本改动无关 |

---

## §8 复现命令

```powershell
# 测试（本机：10 passed + 1 环境失败；兼容解释器下应 11 passed）
python -m pytest tests/test_rbac_permission_seed.py -q

# 静态检查（须全绿）
python -m ruff check scripts tests

# 交付 A：dry-run 播种（不写库；产物落 doc/design/generated/）
python scripts/rbac_permission_seed.py
python scripts/rbac_permission_seed.py --current doc/design/generated/rbac_seed_manifest.json   # 差异报告

# 负向：目标档案不符（应退出码 1 且不落盘）
python scripts/rbac_permission_seed.py --schema openbase

# 交付 B：影子期观测（只读；样例日志）
python scripts/rbac_shadow_observe.py --log tests/fixtures/rbac_shadow_sample.jsonl
python scripts/rbac_shadow_observe.py --log tests/fixtures/rbac_shadow_sample.jsonl --json doc/design/generated/rbac_shadow_observe_sample.json
```

> 目标库列清单只读探查（如需复核；DSN 从 `.env.shared-infra` 取，**探针仅临时、用后即删、不入库**）：
> 查询 `information_schema.columns` / `table_constraints` / `pg_indexes`（`table_schema='public'`），
> 表 `roles/permissions/role_permissions/user_roles/users`。**严禁执行任何写 SQL。**
