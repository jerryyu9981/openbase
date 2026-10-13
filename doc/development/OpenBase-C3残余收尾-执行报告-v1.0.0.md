# OpenBase-C3残余收尾-执行报告-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-C3-CLOSURE-EXEC-v1.0.0 |
| 文档名称 | C3 豁免治理残余收尾——跨仓执行报告 |
| 版本 | v1.0.0 |
| 状态 | [Review]（待人工批准） |
| 作者 | AA/AT/PM-OpenBase-Dev（跨仓推进组） |
| 创建日期 | 2026-10-13 |
| 适用环境 | Dev / Test |
| 关联台账 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》v1.16.19（§9.3 C3 / §10.3 C3） |
| 关联契约 | `config/identity_exemptions.json`（schema_version 2；revisions v4~v7） |
| 涉及仓 | OpenRAG（主）、OpenMemory、OpenBase（协调/台账） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-13 | AA/AT/PM-OpenBase-Dev | 首次成稿：C3 残余项（契约一致性 + OpenRAG 三项 + OpenMemory 消费侧）逐项执行、验证、留痕与推送汇总 |

---

## 1. 摘要（执行结论）

**C3 豁免治理在 OpenRAG / OpenMemory 两仓的登记残余项已全部清零。** 本轮共闭合 **5 项**（1 项契约一致性 + OpenRAG 三项 + OpenMemory 一项），全部遵循
**TDD（RED→GREEN）→ 静态检查（ruff 0）→ 文档留痕（版本 + 修订历史）→ 三远程推送** 闭环纪律：

| # | 残余项 | 仓 | 提交 | 版本 | 用例 | 状态 |
|:-:|--------|----|------|------|------|:----:|
| C3-1 | 契约一致性校正（三仓字段命名归一 rename 状态与台账对齐） | OpenBase | `428ac13`（台账 v1.16.17） | 契约 revision **v4** | JSON 合法性 | ✅ |
| C3-2 | `scope_exemption` 表补 `ticket` 列（R1 合规） | OpenRAG | `23b3cc8` | v1.8.4 | 4 例 | ✅ |
| C3-3 | 行控豁免**运行时接线**（中间件 → 请求级令牌 → 存储层放宽） | OpenRAG | `4937c90` | v1.8.5 | 6 例 | ✅ |
| C3-4 | `scope_exemption` **DB 行读取器**（双落点、DB 为准） | OpenRAG | `5e76dc1` | v1.8.6 | 4 例 | ✅ |
| C3-5 | 行控豁免注册表**消费侧接线**（`evaluate_row_scope_grant` 调用点） | OpenMemory | `3f1fa5f` | v7.1.3 | 5 例 | ✅ |

> **同批交付（非 C3，另见台账）**：B2 P2 另一半「A 直连白名单显式登记」（OpenRAG `23b3cc8`）；B1 D4 phase 4「过渡期兼容层退役（裁定方案 A，安全耦合）」（OpenLLM `298fe7d`）。本报告仅就 **C3** 项作收尾汇总，上述两项不在 C3 范围。

---

## 2. 背景与范围

### 2.1 C3 目标

C3（台账 §6 C 批）目标：**把「豁免治理」统一为一个通用机制**——统一必填字段
（`target`/`ticket`/`approver`/`expires_at`）、生效/过期语义（规则 R1~R5）、审计要求与分阶段强制路径，
供各仓豁免实现（OpenBase k03 / OpenMemory 行控 / OpenLLM 入站头 / OpenRAG 行控）对账消费。

### 2.2 本轮残余范围

台账 §9.3 / §10.3 登记的 C3 残余项：

- **OpenMemory**：注册表**消费侧**（`evaluate_row_scope_grant` 调用点）无调用者；
- **OpenRAG**：① DB 表缺 `ticket` 列（违反 R1）；② 运行时未接线（`main.py` 无 `ExemptionRegistry` 消费点）；③ DB 行读取器缺失；
- **契约制品**：`normalization_plan`（字段命名归一 rename）状态与台账 v1.16.3~5 存在漂移。

---

## 3. 逐项执行明细

### C3-1 契约一致性校正

- **问题**：`config/identity_exemptions.json` 的 `known_gaps` 仍写「三仓字段命名归一 rename 随各仓版本窗口执行」，而台账 v1.16.3~5 记载 rename 已完成 → 记载漂移。
- **取证**：实测三仓运行码字段为 `target`/`reason`（OM `scope_exemption.py` 用 `target`/`reason`；OpenRAG 用 `target`/`ticket`/`approver`；OpenLLM `exemptions.py` 用 `target`/`reason`）；OM 另有 alembic `v707_scope_exemption_target_rename`；残留命中仅注释/子串（如 `TRUSTED_PROXY_SOURCES` 含 `proxy_source` 子串）误报。
- **处置**：同步 `known_gaps`、`normalization_plan.status`、`stage_3` 内容项、`field_mapping`（`target`/`reason` 归一态），新增 **revision v4**。
- **验证**：JSON 解析合法。
- **留痕**：OpenBase `428ac13`（台账 v1.16.17）。

### C3-2 OpenRAG `scope_exemption` 补 `ticket` 列（R1 合规）

- **问题**：OpenRAG 豁免代码模型有 `ticket`，但 DB 表（SQLite/PG 建表 DDL）**无该列** → 落库丢失审批凭据，**违反 R1**。
- **实施**（`src/openrag/storage/migrations.py`）：SQLite/PG 建表 DDL 增 `ticket` 列；新增**幂等历史表迁移** `ensure_scope_exemption_ticket_column_sqlite`（`PRAGMA table_info` 判存 → `ADD COLUMN`）/ `plan_scope_exemption_ticket_column_postgres`（`ADD COLUMN IF NOT EXISTS`）。
- **TDD**：`tests/unit/test_c3_openrag_ticket_column.py`（4 例：PG DDL 声明 ticket / PG 迁移 DDL 幂等 / SQLite 新表含 ticket 且迁移 no-op / SQLite 历史表补列）。
- **验证**：4 passed；`ruff` 0。
- **留痕**：OpenRAG `23b3cc8`（v1.8.4；DevLogReport §12）。

### C3-3 OpenRAG 行控豁免运行时接线（授权落地）

- **问题**：豁免注册表**无任何运行时消费点** → 登记的豁免不会在任何请求路径生效。
- **实施**（三段链路，语义对齐 S3-T3「豁免只放宽 scope 过滤、不触及身份信任」）：

  | 段 | 文件 | 内容 |
  |---|---|---|
  | ① 请求级令牌 | `identity/context.py` | contextvar `_current_scope_exemption` + `current_scope_exemption_id()` / `set_scope_exemption_id()` |
  | ② 消费中间件 | `api/middleware/scope_exemption.py`（新增） | `ScopeExemptionMiddleware`：对 `(path, method)` 执行 `ExemptionRegistry.assess(path, method, principal.subject_id)`——命中则写令牌并落审计（`scope_exemption_granted`）；未命中/无配置 → **逐字放行** |
  | ③ 装配 | `main.py` | 装载 `ExemptionRegistry.from_env()`（`OPENRAG_SCOPE_EXEMPTIONS`）+ `add_middleware(ScopeExemptionMiddleware, …)` 置于 IdentityGate **之前**（运行时在其后执行，可读已裁决 principal） |
  | ④ 放宽点 | `storage/postgres.py` / `sqlite.py` | `_scope_tenant`：`enforce_scope` 且缺 `tenant_code` 时，若请求级令牌存在 → 返回 `None`（放宽）；否则仍 `TenantScopeRequiredError`（fail-closed） |

- **约束（授权附条件）**：目标面显式登记（`target` 正则 + `method`）；`expires_at` 到期校验；命中/拒绝均审计；**匿名（无 `subject_id`）不豁免**。
- **TDD**：`tests/unit/test_c3_scope_exemption_wiring.py`（6 例：PG/SQLite 层缺域 fail-closed 与豁免放宽 / 中间件命中授予 / 无注册表不授予 / 匿名不授予）。**contextvar 穿透**（中间件→路由→存储层）已实测。
- **验证**：6 passed；相关回归 51 passed；`ruff` 0；`create_app()` OK。
- **留痕**：OpenRAG `4937c90`（v1.8.5；DevLogReport §13）。

### C3-4 OpenRAG `scope_exemption` DB 行读取器（双落点、DB 为准）

- **问题**：C3-3 后注册表仍**仅由 env 装载**；`scope_exemption` DB 表无读取器 → 表内登记不可达。
- **实施**：

  | 段 | 文件 | 内容 |
  |---|---|---|
  | ① 存储层读取器 | `storage/postgres.py` / `sqlite.py` | `async def scope_exemption_list()`：读 `status='active'` 行 → 统一字段；表缺/无行/失败 → 空列表（降级不阻断） |
  | ② 注册表合并 | `identity/scope_exemption.py` | 抽出 `entry_from_dict()`；新增 `merge_entries(payload)`（**同 `exemption_id` 以 DB 行为准**）+ `__len__` |
  | ③ 启动装配 | `main.py::lifespan` | `init_dependencies()` 后 `registry.merge_entries(await store.scope_exemption_list())`（DB 覆盖 env 种子）；失败降级 WARN |

- **双落点语义**（对齐 OpenMemory `build_scope_exemption_registry`）：env 种子先行、DB 行覆盖；DB 无该 id 则新增。
- **TDD**：`tests/unit/test_c3_scope_exemption_db.py`（4 例：merge DB 覆盖种子 / PG 无会话空 / SQLite 读 active 排除 inactive / SQLite 未初始化空）。
- **验证**：4 passed；相关回归 55 passed；`ruff` 0。
- **留痕**：OpenRAG `5e76dc1`（v1.8.6；DevLogReport §14）。

### C3-5 OpenMemory 行控豁免注册表消费侧接线

- **问题**（台账登记）：豁免注册表**装配已接线**（`server.py` lifespan，`6ecc420`/v7.1.1），但**消费侧**（`evaluate_row_scope_grant` 调用点）无调用者。
- **实施**（`src/openmemory/api/controllers.py`）：新增 `_apply_row_scope_grant(request, scope)` 并于 `_memory_scope` 调用（消费 `evaluate_row_scope_grant`）：

  - **仅在 IdentityGate 已裁决主体（M2 受信面）时生效**；无 `state.identity`/无 principal（M1、直连测试面）**逐字保持既有兼容语义**；
  - 命中「票据 + 审批人 + 未到期」豁免 → 放宽 `org_wide` + 审计 `scope.exempt`；
  - owner 缺失且未命中豁免 → 按 `row_scope.enforce` fail-closed（400 `SCOPE_REQUIRED`）。

- **TDD**：`tests/unit/test_c3_scope_consumer_wiring.py`（5 例：owner 存在=scoped 不变 / owner 缺失+无豁免=400 / owner 缺失+命中豁免=org_wide / 无 identity=no-op / 无 principal=no-op）。
- **验证**：5 passed；相关回归 71 passed；全量 unit+integration **1437 passed**（13 failed + 17 errors 全为 `test_s2_org_fact_source` / `test_org_routes` 的 `OrgFactSourceError: SYS_SOURCE_UNAVAILABLE` **DB 不可达环境项**，该模块不 import controllers，与本改动无因果）；`ruff` 0。
- **留痕**：OpenMemory `3f1fa5f`（v7.1.3；DevLogReport《OpenMemory-C3-消费侧接线-DevLogReport-v1.0.0》）。

---

## 4. 验证汇总

| 类别 | 结果 |
|---|---|
| 新增用例 | OpenRAG **14 例**（4 + 6 + 4）+ OpenMemory **5 例** = **19 例** |
| 定向回归 | OpenRAG §13/§14 相关 **55 passed**；OpenMemory 相关 **71 passed** |
| OpenMemory 全量（unit+integration） | **1437 passed**；13 failed + 17 errors 全为 `org_fact_source` DB 环境项（非本改动） |
| 静态检查 | 三仓变更文件 `ruff` **All checks passed** |
| 应用可构建 | OpenRAG `create_app()` OK（中间件 9，含 `ScopeExemptionMiddleware`） |
| 契约制品 | `identity_exemptions.json` JSON 合法（revisions v4~v7） |

---

## 5. 契约与台账留痕

| 制品 | 变更 |
|---|---|
| `config/identity_exemptions.json` | **revision v4**（一致性校正）→ **v5**（ticket 列 + B2 A 白名单登记）→ **v6**（OpenRAG 运行时接线）→ **v7**（DB 行读取器）；`consumers.openrag_row_scope.gaps` / `known_gaps` / `field_mapping` / `normalization_plan.status` 同步 |
| 台账（`OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0.md`） | **v1.16.17 / v1.16.18 / v1.16.19**（修订历史 + §5.1 OpenRAG 行 + §10.3 C3 / B2 / B1 行） |
| 开发记录 | OpenRAG DevLogReport **v1.6.0 §12 / v1.7.0 §13 / v1.8.0 §14**；OpenMemory《C3-消费侧接线-DevLogReport-v1.0.0》 |

---

## 6. 提交与推送（三远程一致性）

| 仓 | 分支 | 提交 | 版本 | origin / backup / github |
|---|---|---|---|---|
| OpenRAG | `release/v1.10.0` | `23b3cc8` → `4937c90` → `5e76dc1` | 1.8.4 → 1.8.6 | ✅ / ✅ / ✅（齐平） |
| OpenMemory | `release/v7.3.0` | `3f1fa5f` | 7.1.3 | ✅ / ✅ / ✅（齐平） |
| OpenBase | `main` | `428ac13` / `54374eb` / `3fda224` | 台账 v1.16.17~19 | ✅ / ✅ / ✅（齐平） |

> 期间 OpenRAG / OpenMemory 累计的 **github-backfill** 亦已随本轮推送清零。

---

## 7. 风险与回滚

| 项 | 回滚方式 |
|---|---|
| C3-2 `ticket` 列 | 列可空、仅结构补齐，无数据回滚需求（回退提交即可） |
| C3-3 运行时接线 | 移除中间件装配 + 存储层放宽分支（或回退提交）；未命中/无配置即逐字放行，**默认零行为变化** |
| C3-4 DB 行读取器 | 移除 lifespan 合并块（或回退提交）；`scope_exemption_list` 为纯新增只读方法，无副作用 |
| C3-5 消费侧接线 | 移除 `_memory_scope` 中的消费调用（或回退提交）；**M1/直连语义逐字保留** |

**共性风险控制**：所有改动默认**不改变现场可用性**（OpenRAG 豁免需显式登记方才生效；OpenMemory 需 M2 受信主体），并以「改动前基线 vs 改动后」逐项对比证明**失败数零增长**。

---

## 8. 遗留与结论

- **闭合声明**：C3 在 **OpenRAG** 的登记项（`ticket` 列 / 字段命名归一 / 运行时接线 / DB 行读取器）与 **OpenMemory** 的消费侧接线 **全部清零**；契约层面两仓治理链均达 **装配 + 消费 +（OpenRAG）DB 行读取** 完整态。
- **遗留（非 C3 / 规划项）**：`scope_exemption` 表的**写入/记账**侧未在本轮范围（读取器为只读）；四仓豁免实现的**字段命名归一 rename** 已全部完成；`/system/*` 豁免显式登记已完成（B2 P2）。
- **结论**：C3 残余收尾达到出口门禁——**用例全绿、静态检查零错误、契约与台账留痕一致、三远程齐平**。建议按 DevFlow 纪律**人工批准**后归档。

---

## 附录 A：证据索引

| 类型 | 位置 |
|---|---|
| OpenRAG 用例 | `tests/unit/test_c3_openrag_ticket_column.py` / `test_c3_scope_exemption_wiring.py` / `test_c3_scope_exemption_db.py` |
| OpenMemory 用例 | `tests/unit/test_c3_scope_consumer_wiring.py` |
| OpenRAG 开发记录 | `doc/development/OpenRAG-B2-授权细粒度接线-DevLogReport-v1.0.0.md`（§12/§13/§14） |
| OpenMemory 开发记录 | `doc/development/OpenMemory-C3-消费侧接线-DevLogReport-v1.0.0.md` |
| 契约制品 | `config/identity_exemptions.json`（revisions v4~v7） |
| 台账 | `doc/design/OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0.md`（v1.16.17~v1.16.19） |
