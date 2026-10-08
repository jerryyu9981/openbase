# OpenBase B1 生产化配套：权限播种脚本 + 影子期观测聚合

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase-B1-生产化配套-权限播种与影子期观测 |
| 文档版本 | v1.0.0 |
| 状态 | **[Draft] 待评审批准** |
| 适用环境 | OpenBase 仓库（工具脚本）；产物面向 OpenLLM 生产库 |
| 作者 | Dev-OpenBase（AI 辅助编码，人工过目） |
| 创建日期 | 2026-10-08 |
| 存放 | doc/design/ |
| 上游依据 | 《OpenBase-B1派单-OpenLLM授权接线-v1.0.0》（§3 交付要求 5/§4 验收 6）；`config/rbac_permission_model.json`（人工裁定唯一输入）；`config/role_tier_anchors.json` |
| 输入（只读，勿改） | `config/rbac_permission_model.json` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-08 | Dev-OpenBase | 初始创建：落地「交付 A 播种脚本」与「交付 B 影子期观测聚合」，按 TDD 最小改动实现；登记验证证据、五条校验触发结果、产物形态与执行责任结论、风险与未覆盖项 |

---

## §1 背景与目标

B1 派单回执已登记一项关键**已知风险**：角色→权限映射为**推荐基线、未写库**——强制期开启前
须播种 DB 权限矩阵（或经 JWT `permissions` 下发），否则非管理员会被误拒。配套两件工具：

- **交付 A**：把人工裁定的权限模型转成**可审阅、幂等**的播种产物（清单 + SQL + 差异报告），
  **默认不写库**；
- **交付 B**：把影子期 `rbac_decision=would_deny` 观测聚合为可消化的清单，支撑影子期出口门禁
  「消化率 100% 且无未归类调用方」（模型 `rollout.phase_1_shadow.exit_gate`）。

目标（均落地为测试用例）：
1. 播种产物齐备且含幂等 SQL；2. 默认 dry-run 不连库/不写库；3. 三条强制校验 fail-fast；
4. 影子期观测按「端点 × 角色 × 权限码」聚合 + 消化率；5. 脏行/缺字段容错。

---

## §2 交付物清单（新增文件）

| 类型 | 路径 | 说明 |
|------|------|------|
| 脚本 A | `scripts/rbac_permission_seed.py` | 权限播种：声明式清单 + 幂等 SQL + 差异报告（默认 dry-run） |
| 脚本 B | `scripts/rbac_shadow_observe.py` | 影子期 `would_deny` 观测聚合（只读） |
| 测试 A | `tests/test_rbac_permission_seed.py` | 6 例（含差异报告） |
| 测试 B | `tests/test_rbac_shadow_observe.py` | 5 例 |
| 样例 fixture | `tests/fixtures/rbac_shadow_sample.jsonl` | 内置样例日志（不依赖现场日志） |
| 生成产物 | `doc/design/generated/rbac_seed_manifest.json` | 种子清单（dry-run 产物） |
| 生成产物 | `doc/design/generated/rbac_seed.sql` | 幂等 SQL（供目标仓执行） |
| 生成产物 | `doc/design/generated/rbac_seed_diff.json` | 差异报告（重跑 = 0） |
| 生成产物 | `doc/design/generated/rbac_shadow_observe_sample.json` | 样例日志的观测证据 |

**未改动**：`config/rbac_permission_model.json` 及其它仓库；未新增第三方依赖；未启动/停止任何服务。

---

## §3 交付 A：播种脚本设计

### 3.1 输入与产物形态

输入：`config/rbac_permission_model.json`（唯一，只读）。产出落 `--out-dir`（默认
`doc/design/generated/`）：

- **种子清单 JSON**（声明式四段，可直接人工审阅）：
  - `roles`：`{code, name, description, is_system}`（5 角色，元信息对齐 `init.py`/`role_tier_anchors.json`）；
  - `permissions`：`{code, name, module, type}`（`*` 通配 + `modules[*].codes`，共 27 条）；
  - `role_permissions`：`{role_code, permission_code}`（对齐模型授予，共 34 条）；
  - `user_role`：用户→角色**绑定意图**（默认空；绑定属环境相关，由目标仓补充）。
- **可执行 SQL**：PostgreSQL 方言、事务包裹（`BEGIN; ... COMMIT;`）。
- **差异报告 JSON**：逐段 `added / removed / changed` + 计数。

### 3.2 DDL 方言结论与依据

先探查本仓既有落库方式后确定方言：`openbase/core/db/init.py`（roles/permissions 种子）、
`openbase/core/models/base.py`（`roles.code` / `permissions.code` 唯一；`role_permission` /
`user_role` 复合主键）、`openbase/modules/identity/migration.py`（`WHERE NOT EXISTS` 幂等）——
生产库为 **PostgreSQL（asyncpg）+ schema=openbase**。故：

- **方言 = PostgreSQL**；目标 schema 默认 `openbase`（`--schema` 可覆盖）。
- **幂等语义**：`INSERT ... ON CONFLICT (code) DO NOTHING`（角色/权限点）、
  `INSERT ... SELECT ... ON CONFLICT DO NOTHING`（关联表，按 code 解析 id）。重复执行结果一致。

### 3.3 执行责任结论（为何本脚本不写库）

**结论：播种 SQL 由目标仓（OpenLLM）执行，本脚本默认且始终 dry-run，不提供 `--apply`。**

理由（跨系统写库属高影响动作）：
1. 权限变更影响目标系统**授权面**，须人工过目、评审与回滚预案后执行（派单 §4 验收 6 要求
   影子期观测清单留存，先审后执行）；
2. 本脚本**不导入任何数据库驱动**、不建连接、不写库——从依赖面杜绝"误写库"；
3. 与派单《OpenBase-B1派单-OpenLLM授权接线》"权限码清单与角色映射"交付口径一致：
   OpenBase 侧交付**清单/SQL**，OpenLLM 侧在其受控流程内执行。

> 该"更安全做法（只产出产物 + 说明由目标仓执行）"即需求中"优先选"的方案。

### 3.4 强制校验（fail-fast，缺一即报错退出、不落盘任何文件）

| # | 校验 | 判定 | 违规信息样例 |
|:-:|------|------|--------------|
| 1 | 无悬空码 | 授予引用的权限码必须 ∈ `modules[*].codes`（`*` 除外） | `悬空权限码：角色 org_admin 授予了 modules[*].codes 中不存在的 'unknown_module:read'` |
| 2 | 只读角色约束 | `user/org_member/viewer` 不得持有 `*:write`/`*:delete`/`*:admin`（含 `*`） | `只读角色违规：user 持有写类权限码 'user:write'（契约 *:write/*:delete/*:admin）` |
| 3 | 禁授约束 | `forbidden_grants` 的码不得出现在除 `admin` 外任何角色的授予里 | `禁授违规：非 admin 角色 org_admin 持有 forbidden_grants 权限码 'role:admin'` |

---

## §4 交付 B：影子期观测聚合设计

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

**消化率定义**：
- `digestion_rate = classified_events / total_events`（可归入模型已知角色的比例，对应门禁
  "消化率 100%"）；`unclassified_events` 即"未归类调用方"（对应门禁"无未归类调用方"）；
- `model_allows_events` = 归类后按模型**本应被允许**（授予含该码或 `*`）——**需消化的阻塞项**
  （播种矩阵或补角色绑定）；`model_denies_events` = 本应被拒绝（符合模型预期，无需动作）。

### 4.3 只读保证

脚本不连库、不改任何服务、不写库；`--json` 可将报告落盘为 JSON 证据，其余仅打印 stdout。

---

## §5 验证证据（实际输出）

### 5.1 TDD RED（实现前，脚本缺失）

```
$ python -m pytest tests/test_rbac_permission_seed.py tests/test_rbac_shadow_observe.py -q
... FileNotFoundError: ... 'scripts\rbac_permission_seed.py'
... FileNotFoundError: ... 'scripts\rbac_shadow_observe.py'
FAILED tests/test_rbac_permission_seed.py::test_seed_generates_artifacts_with_idempotent_sql
... （共 6 项）
FAILED tests/test_rbac_shadow_observe.py::test_aggregate_counts_by_endpoint_role_permission
... （共 5 项）
11 failed in ...s
```

### 5.2 TDD GREEN（实现后）

```
$ python -m pytest tests/test_rbac_permission_seed.py tests/test_rbac_shadow_observe.py -q
...........                                                              [100%]
11 passed in ...s
```

### 5.3 静态检查

```
$ python -m ruff check scripts tests
All checks passed!
```

### 5.4 实机 dry-run（播种脚本）

```
$ python scripts/rbac_permission_seed.py
[rbac_permission_seed.py] mode=dry-run applied=False target=openllm roles=5 permissions=27 role_permissions=34 user_role=0
  清单：D:\Trae CN\myproject\Dev\OpenBase\doc\design\generated\rbac_seed_manifest.json
  SQL ：D:\Trae CN\myproject\Dev\OpenBase\doc\design\generated\rbac_seed.sql（幂等，由目标仓执行）
  差异：（无既有清单，未生成差异报告）

$ python scripts/rbac_permission_seed.py          # 二次运行：幂等 → 差异 0
  ... 差异：doc\design\generated\rbac_seed_diff.json（变更项合计 0；0 = 与既有清单一致）
```

产物 SQL 片段（幂等语义）：

```sql
-- 幂等语义：INSERT ... ON CONFLICT DO NOTHING
-- 执行责任：**由目标仓（OpenLLM）执行**；本脚本不连库、不写库（默认 dry-run）。
BEGIN;
INSERT INTO "openbase"."roles" (name, code, description, is_system, created_at, updated_at)
  VALUES ('组织管理员', 'org_admin', '组织级管理角色（不含角色/权限管理，裁定 D2）', true, now(), now())
  ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."permissions" (code, name, module, type, created_at, updated_at)
  VALUES ('user:write', 'users·write', 'users', 1, now(), now())
  ON CONFLICT (code) DO NOTHING;
INSERT INTO "openbase"."role_permission" (role_id, permission_id)
  SELECT r.id, p.id FROM "openbase"."roles" AS r
  JOIN "openbase"."permissions" AS p ON p.code = 'user:write'
  WHERE r.code = 'org_admin'
  ON CONFLICT DO NOTHING;
COMMIT;
```

### 5.5 实机影子期观测（样例日志）

```
$ python scripts/rbac_shadow_observe.py --log tests/fixtures/rbac_shadow_sample.jsonl
[rbac_shadow_observe.py] log=tests\fixtures\rbac_shadow_sample.jsonl would_deny=7 groups=5 digestion_rate=71.43% unclassified=2 skipped_lines=1
  /api/v1/knowledge-bases | user | knowledge_base:write × 2 (model_allows=False, samples=req-4,req-5)
  /api/v1/users | org_admin | user:write × 2 (model_allows=True, samples=req-1,req-2)
  /api/v1/users | unknown_role | user:write × 1 (model_allows=None, samples=req-6)
  /api/v1/users | viewer | user:write × 1 (model_allows=False, samples=req-3)
  <unknown> | <unknown> | <unknown> × 1 (model_allows=None, samples=req-8)
```

（样例中 2 条 `org_admin × user:write` 即"本应允许"的待消化项；`unknown_role` 与缺字段行即
"未归类调用方"2 条。）证据落盘：`doc/design/generated/rbac_shadow_observe_sample.json`。

---

## §6 五条校验的实际触发结果

| 场景 | 实际触发 | 退出码 |
|------|---------|:------:|
| ① 正常模型 | 产物齐备（roles=5/permissions=27/role_permissions=34）+ 幂等 SQL；清单/SQL 落盘 | 0 |
| ② 默认 dry-run | `mode=dry-run applied=False`；无任何库连接/写库副作用（测试以替身断言） | 0 |
| ③ forbidden 授予 org_admin | `禁授违规：非 admin 角色 org_admin 持有 forbidden_grants 权限码 'role:admin'` | 1 |
| ④ 只读角色含写码 | `只读角色违规：user 持有写类权限码 'user:write'（契约 *:write/*:delete/*:admin）` | 1 |
| ⑤ 悬空权限码 | `悬空权限码：角色 org_admin 授予了 modules[*].codes 中不存在的 'unknown_module:read'` | 1 |

（③④⑤ 均在**任何产物落盘之前** fail-fast：`--out-dir` 未生成任何文件。）

---

## §7 风险、假设与未覆盖项

| 项 | 说明 / 影响 | 处置 |
|----|-------------|------|
| OpenLLM 实际日志字段未现场校验 | 观测脚本按多别名容错解析；若目标仓字段名不同，可能漏采 | 上线前用真实日志片段回归；必要时补充别名常量 |
| `user_role` 绑定意图默认空 | 模型未含用户数据；跨环境绑定需目标仓补充 | 清单以 `user_role_note` 显式声明边界 |
| SQL 未在真实 OpenLLM 库执行验证 | 本脚本按约束不写库，无法端到端验证 DDL | 由目标仓在受控流程执行并回执；`ON CONFLICT` 语义与 `init.py` 一致 |
| 消化率口径为主观定义 | "消化率"由脚本定义（可归类比例）；门禁认定以人工为准 | §4.2 明确定义；`model_allows_events` 单列阻塞项 |
| 权限码 `role:write/delete/admin` 亦作为权限行播种 | 仅"播种为权限点"，不授予非 admin（校验 3 拦截） | 符合裁定 D2 |
| 既有 22 项基线失败未清理 | 派单 `production_gates` 项；本轮不涉 | 与本改动无关；本轮新增用例独立全绿 |
| 覆盖率 | 新增脚本为工具脚本（非 `openbase/` 包），未纳入包覆盖率统计 | 由本文件 §5 的 11 例与实机运行佐证 |

---

## §8 复现命令

```powershell
# 测试（RED 记录见 §5.1；GREEN 见 §5.2）
python -m pytest tests/test_rbac_permission_seed.py tests/test_rbac_shadow_observe.py -q

# 静态检查（须全绿）
python -m ruff check scripts tests

# 交付 A：dry-run 播种（不写库；产物落 doc/design/generated/）
python scripts/rbac_permission_seed.py
python scripts/rbac_permission_seed.py --current doc/design/generated/rbac_seed_manifest.json   # 差异报告

# 交付 B：影子期观测（只读；样例日志）
python scripts/rbac_shadow_observe.py --log tests/fixtures/rbac_shadow_sample.jsonl
python scripts/rbac_shadow_observe.py --log tests/fixtures/rbac_shadow_sample.jsonl --json doc/design/generated/rbac_shadow_observe_sample.json
```
