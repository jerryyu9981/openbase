# OpenBase-B1-播种SQL评审与执行预检说明

## 文档元信息

| 项 | 值 |
|----|----|
| 版本 | v1.1.0 |
| 状态 | [Approved]（OpenBase 侧已裁定 D1/D2；D2 的最终实现口径以接线复核为准） |
| 作者 | AA/AT-OpenBase-Dev |
| 适用 | B1 权限播种受控执行的评审与执行前预检 |
| 关联制品 | `doc/design/generated/rbac_seed_ddl.sql`（前置结构变更，独立交付）、`rbac_seed.sql`（纯 DML）、`rbac_seed_manifest.json`、`rbac_seed_diff.json`；`scripts/rbac_permission_seed.py`（生成器） |
| 修订历史 | v1.0.0 2026-10-09 初稿；v1.1.0 2026-10-09 按 D1/D2 裁定升版：前置 DDL 与数据播种**解耦为两步交付**（结构先行、数据后行）；通配符口径**取 A**；补充「局域网共享库为唯一数据库」的落点与影响面口径 |

## 1. 背景与目的

B1（OpenLLM 授权接线）强制期前置条件之一是**权限矩阵播种**。生成器已重修（数据模型来源改为目标系统自身表结构，并新增生成期目标校验与落点断言）。本说明供评审与执行前预检使用，同时作为 OpenBase 侧的执行约束声明。

## 2. 目标与制品形态

| 项 | 值 |
|----|----|
| 目标库 / schema | **局域网内共享基础设施的唯一数据库** `192.168.0.151:5432/nuct` 的 `public` schema（四系统同实例、按 schema 区分：`openbase` / `platform` / `public`）。**非** `localhost:5432/openllm`，也**非** `openbase` schema |
| 目标表 | `roles`、`permissions`、`role_permissions`、`user_roles` |
| 计数（待播种） | roles=5、permissions=27、role_permissions=34、user_roles=0 |
| 交付 A1 | `rbac_seed_ddl.sql` —— 前置结构变更（`role_permissions` 唯一索引），**独立于数据播种** |
| 交付 A2 | `rbac_seed.sql` —— **纯 DML** 幂等播种（`INSERT ... ON CONFLICT DO NOTHING`） |
| 幂等 | roles/permissions 冲突键 `(code)`；role_permissions 冲突键 `(role_id, permission_id)` |
| 主键 | uuid5（固定命名空间 + 稳定键）→ 重跑内容逐字节一致（SQL 头部生成时间戳除外），`rbac_seed_diff.json` diff=0 |
| 生成器防护 | 生成期档案校验（schema/键类型/表集合与档案不符即硬失败）+ 落点断言（SQL 中出现 `openbase`/`platform` 的 INSERT 即硬失败）；**永远 dry-run**，不提供 `--apply`，脚本内不 import 任何数据库驱动 |

执行责任：**由共享基础设施的受控变更流程执行**（结构变更走迁移/DBA，数据播种走受控窗口）；OpenBase 侧只生成文本、不连库不写库。

## 3. 前置 DDL 的处置（D1 裁定）

### 3.1 前置 DDL 是什么

即 `role_permissions` 上的唯一索引：

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permissions_role_permission
  ON "public"."role_permissions" ("role_id", "permission_id");
```

**为什么是"前置"**：只读探查证实目标库 `public.role_permissions` **仅有 `id` 主键、无 `(role_id, permission_id)` 唯一约束**，而 `role_permissions` 的幂等冲突键 `ON CONFLICT (role_id, permission_id) DO NOTHING` 依赖该唯一索引——缺则 SQL 直接失败，故须先于数据插入存在。

### 3.2 D1 裁定：**保留索引语义，但与数据播种解耦交付（结构先行、数据后行）**

- **保留该唯一约束**：`(role_id, permission_id)` 唯一本身语义正确（角色-权限关联天然唯一），且是幂等基础；删索引将连带推翻 `ON CONFLICT` 口径。
- **拆两步交付**：唯一索引 DDL 独立成文 `rbac_seed_ddl.sql`；`rbac_seed.sql` 退化为**纯 DML**。理由：DDL 与 DML 的权限、责任、回滚粒度不同——DDL 需 `CREATE INDEX` 权限、需先消重、需能单独 `DROP INDEX` 回滚；混在一个事务里会让"数据失败"与"结构变更"相互纠缠。
- **因共享库、跨系统影响面**：该唯一索引落在**局域网唯一共享库**上，四系统同实例共担影响面，故须经**受控结构变更流程**执行，不得随数据播种顺带执行。

### 3.3 风险 1：重复行导致 DDL 失败（硬门禁）

若目标库已存在重复的 `(role_id, permission_id)` 行，该 DDL 会直接失败。执行前必须运行**只读预检**（结果 0 行才可继续）：

```sql
SELECT role_id, permission_id, COUNT(*) AS dup_count
FROM "public"."role_permissions"
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;
```

非 0 时须先消重（建议保留 `is_active=true` 且 `created_at` 最早的一行，消重 SQL 由目标库所有者按其数据口径提供，OpenBase 不代拟）。

### 3.4 风险 2：执行账号需 DDL 权限

执行账号须具备 `CREATE INDEX` 权限。若无，须由共享库 DBA 协调授权或由其代执行该 DDL。

## 4. 通配符语义处置（D2 裁定：**取 A**）

OpenLLM 的 `Role.has_permission` 为**精确码匹配，无 `*` 通配展开**。权限模型定稿中 `admin=["*"]`，而播种对 admin 产出的是 `*` 权限行。

- **选项 A（裁定采纳）**：B1 接线在 `rbac_guard.py` 补通配语义（`*` → 放行全部）。与权限模型 `admin=["*"]` 一致，播种不变。
- 选项 B（未采纳）：生成器将 admin 改为逐码授予全部 27 个具体权限码。零运行时改动，但清单随权限码增删而膨胀、需同步更新。

**采纳 A 的理由**：让 `*` 的语义只有**一个解释点**（接线侧），与权限模型这一单一事实源保持一致；否则同一语义要在"生成器清单"和"权限模型"两处维护，权限码增删时必然漂移。B 仅作为接线未落地前的**短期兜底**（可立即开强制段、不误伤 admin），应收敛到 A。

采纳 A 时须同时确认：
1. `*` 只作"放行全部"，不参与 `*:write/*:delete/*:admin` 的只读角色校验；
2. `forbidden_grants`（`role:admin/write/delete`）只约束非 admin，admin 持 `*` 仍应放行。

> 说明：本文档所列"无 `*` 展开"为 OpenBase 侧结论，**建议接线评审时由其最终复核一次**；B1 强制段须在 A/B 实现口径落地后方可开启（否则 admin 可能拿不到任何具体权限，误伤管理员）。

## 5. 约定值说明（可调）

`roles.role_type/level/scope` 与 `permissions.scope=platform` 为按 `role_tier_anchors.json` 档位推导的**约定值**，非目标库既有基线；评审时可调整，调整仅影响新增行。

## 6. user_roles 绑定（环境相关）

`user_roles=0` 表示默认**不绑定任何既有用户**，依赖目标库现有 `users` 行。若需在播种时一并绑定现有用户，须由目标库所有者提供 user id 清单后补充生成；否则可后续经其管理流程授予。

## 7. 执行清单（受控执行；结构先行、数据后行）

1. 运行 §3.3 预检 SQL，确认 **0 重复行**；确认执行账号具备 DDL 权限（否则由 DBA 代执行）。
2. 执行前置结构变更：`rbac_seed_ddl.sql`。
3. 执行数据播种：`rbac_seed.sql`（纯 DML）。
4. 执行后验证：`roles` / `permissions` / `role_permissions` 计数符合 §2；重跑一次 `rbac_seed.sql`，`rbac_seed_diff.json` diff=0（幂等）。
5. 确认 §4 通配口径（A）已在接线侧实现。
6. 开启 B1 影子期观测 → 消化率 100% → 按模块灰度 → 生产强制。

## 8. 回滚

| 对象 | 回滚方式 |
|------|---------|
| 数据行 | 基于 uuid5 稳定主键，按 `rbac_seed_manifest.json` 记录的 id 集合精确 `DELETE`（不误删既有行） |
| 前置 DDL | 若该唯一索引此前不存在：`DROP INDEX IF EXISTS "public"."uq_role_permissions_role_permission"`（执行前应确认该索引确实由本次创建） |

> 回滚亦须经共享库的受控流程执行（同 §3.2 影响面口径）。

## 9. 决策点清单（已裁定）

| # | 决策点 | 裁定 | 影响 |
|:-:|--------|------|------|
| D1 | 前置 DDL（唯一索引）与数据播种的处置 | **采纳**：保留索引语义 + 拆两步交付（`rbac_seed_ddl.sql` 先行、`rbac_seed.sql` 后行），经共享库受控变更执行 | 阻塞执行（须先完成预检与 DDL） |
| D2 | 通配符口径 | **采纳 A**：B1 接线补 `*` 通配语义；播种不变 | 阻塞强制段（须接线落地） |
| D3 | `role_type/level/scope` 与 `scope=platform` 约定值是否可调 | 待评审，仅影响新增行 | 不阻塞 |
| D4 | 是否在播种时补充绑定现有用户（`user_roles`） | 默认空，按环境补充 | 不阻塞 |
