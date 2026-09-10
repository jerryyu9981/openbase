# OpenBase-K13-账号权限矩阵-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-K13-ACCOUNT-MATRIX-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft]（S7-T1-3 产出；随 S7 段门禁批准回写 [Approved]） |
| 日期 | 2026-09-11 |
| 作者 | AI（沙箱侧现状实测与矩阵编制） |
| 用途 | **K13 存储账号权限分离矩阵（schema×账号×权限）**：定义 `openbase` 应用账号 / `platform`（DPS 等）账号 / 迁移账号 / 运行时账号的权限收敛口径，作为授权脚本 `scripts/db/grant_k13_accounts.ps1` 的单一事实源 |
| 上游依据 | ①《OpenBase-数据隔离实现任务卡-v1.0.0.md》§K13（规则 §12.6 R-M3-1/2 → OB-7；改动点：账号分离 / 各自仅授本 schema DML / 迁移与运行时账号分离 / 不授 superuser）；②《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md》§2.2 / §4.1（Q-S7-D4） |
| 执行面 | **A 面（沙箱可判定）**：矩阵结构与授权脚本打印模式干跑；**B 面（联调窗口必需）**：真实授权 + 跨 schema 写拒绝验证（需真实 PG + 授权权限）——未执行一律登记 `PENDING`，禁伪造 |

### 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AI（沙箱侧现状实测与矩阵编制） | 初始版本：K13 账号权限矩阵（schema×账号×权限）。含 §1 账号矩阵、§2 权限收敛规则、§3 跨 schema 写拒绝判据、§4 复核命令与 PENDING 登记、§5 回滚。**本次仅新建本矩阵一个文档，未改动其他正文** |

---

## 1. 账号矩阵（schema × 账号 × 权限）

| 账号 | 归属 schema | 角色定位 | 授予权限 | 禁止权限 |
|------|------------|---------|---------|---------|
| `openbase_app` | `openbase` | OpenBase 应用账号（运行时） | 仅本 schema `USAGE` + DML（SELECT/INSERT/UPDATE/DELETE） | 跨 schema 写、DDL、superuser |
| `platform_app` | `platform` | platform（DPS 等）应用账号（运行时） | 仅本 schema `USAGE` + DML（SELECT/INSERT/UPDATE/DELETE） | 跨 schema 写、DDL、superuser |
| `openbase_migrator` | `openbase` | 迁移账号（迁移窗口使用） | 本 schema `USAGE` + `CREATE`（DDL）+ DML | 跨 schema 写、superuser |
| `openbase_runtime` | `openbase` | 受限运行时账号 | 仅本 schema `USAGE` + DML（SELECT/INSERT/UPDATE/DELETE） | DDL、跨 schema 写、superuser |

**矩阵判据**：
1. **账号分离**：`openbase` 应用账号（`openbase_app`）与 `platform`（DPS 等）账号（`platform_app`）物理分离，各自仅授本 schema；
2. **迁移与运行时账号分离**：`openbase_migrator`（DDL）与 `openbase_runtime` / `openbase_app`（DML）分离，运行时不持有 DDL；
3. **仅本 schema DML**：任一账号不得对非本 schema 对象持有写权限；
4. **不授 superuser**：所有账号 `ALTER ROLE ... NOSUPERUSER`，且无 `GRANT ... SUPERUSER` 语句。

---

## 2. 权限收敛规则

| # | 规则 | 落地 |
|---|------|------|
| R1 | 仅授本 schema | `GRANT USAGE ON SCHEMA <own_schema>`，`GRANT ... ON ALL TABLES IN SCHEMA <own_schema>` |
| R2 | 运行时账号无 DDL | `openbase_app` / `openbase_runtime` / `platform_app` 不授 `CREATE` |
| R3 | 迁移账号 DDL/DML | `openbase_migrator` 授 `USAGE, CREATE` + DML（迁移窗口使用） |
| R4 | 不授 superuser | `ALTER ROLE <account> NOSUPERUSER NOCREATEDB NOCREATEROLE` |
| R5 | 跨 schema 写拒绝 | 显式 `REVOKE ALL ON SCHEMA`：`platform` 收回 `openbase_app` / `openbase_migrator` / `openbase_runtime`；`openbase` 收回 `platform_app` |

---

## 3. 跨 schema 写拒绝判据（DB 级，0 成功路径）

**判据**：跨 schema 写 0 成功路径由数据库级拒绝保证（非应用层约定）。

| 场景 | 期望结果 | 证据形态 |
|------|---------|---------|
| `openbase_app` 向 `platform.*` 写入（INSERT/UPDATE/DELETE） | **权限拒绝**（`permission denied for schema platform` / `42501`） | 真实 PG 执行响应码 + `request_id` |
| `platform_app` 向 `openbase.*` 写入 | **权限拒绝** | 同上 |
| `openbase_runtime` 执行 DDL（CREATE TABLE） | **权限拒绝** | 同上 |
| 任一账号 `SELECT` 非本 schema 敏感对象 | 拒绝或为空（按对象授权） | 同上 |

`has_schema_privilege(account, schema, 'CREATE'/'USAGE')` 复核为 `false`（对非本 schema）。

---

## 4. 复核命令与 PENDING 登记

**沙箱可判定（A 面，已执行）**：
- 矩阵结构核对：本文件 §1/§2 与授权脚本 `scripts/db/grant_k13_accounts.ps1` 的账号集合/权限矩阵一致；
- 授权脚本打印模式干跑：`powershell -File scripts/db/grant_k13_accounts.ps1 -DryRun`（退出码 0，输出收敛语句，不含 `GRANT ... SUPERUSER`）。

**联调窗口必需（B 面，未执行 → PENDING）**：

| 项 | 前置条件 | 复核命令（示例） | 状态 |
|----|---------|-----------------|------|
| 真实建账号与授权 | 真实 PG + 建账号权限 | `powershell -File scripts/db/grant_k13_accounts.ps1 -AdminUrl <admin_dsn>` | PENDING |
| 跨 schema 写拒绝验证 | 真实 PG + 授权完成 | `psql <openbase_app_dsn> -c "INSERT INTO platform.xxx ..."`（期望 42501 拒绝） | PENDING |
| 运行账号无法 DDL | 真实 PG + 授权完成 | `psql <openbase_runtime_dsn> -c "CREATE TABLE ..."`（期望拒绝） | PENDING |
| `has_schema_privilege` 复核 | 真实 PG | `SELECT has_schema_privilege('openbase_app','platform','CREATE');`（期望 false） | PENDING |

> **纪律**：B 面未真实执行项一律 `PENDING`，其结果由联调窗口回填 `doc/test/evidence/s7/shr/k13/`，**禁止以「预期通过」代替证据，禁止编造响应码**。

---

## 5. 回滚

- 授权收敛为**增量**（账号分离 / 仅本 schema DML），不涉及数据迁移；
- 回滚 = 还原授权（`GRANT`/`REVOKE` 反向执行），并停用 `grant_k13_accounts.ps1` 的强约束；
- 账号本身保留（仅回收权限），不影响既有连接。
