# OpenBase-B1 派单-OpenLLM授权接线-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）→ OpenLLM |
| 来源批次 | B1（授权接线补欠账，源自《OpenBase-自研系统多租户与授权集成总体完善方案》§6） |
| 文档编号 | OB-DISPATCH-B1-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | **[Approved] 已分发 · 已回执**（2026-10-08 接线收口；2026-10-09 播种制品交付，见 §6.2/§6.3） |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-10-08 |
| 存放 | doc/planning/ |
| 分发状态 | **已分发**（2026-10-08）→ **已回执**（2026-10-08 接线收口见 §6.2；2026-10-09 播种制品交付见 §6.3） |
| 上游依据 | 《OpenBase-B1-OpenLLM授权接线收口立项方案-v1.0.0》；《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§2.4/§5/§6 |
| 证据 | 逐行只读取证结论（见立项方案 §3 的 `文件:行号` 清单） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| **v1.0.5** | **2026-10-09** | **PM/AT-OpenBase-Dev** | **强制期灰度机制回执（收口未决项 1）**：OpenLLM 新增 **`RBAC_PERMISSION_ENFORCE_MODULES`** 灰度白名单（默认空=全部模块；非空=仅列出的 module 强制，其余走影子期）+ `enforced_modules()` / `module_of()` / `is_module_enforced()`；`app/core/config.py`、`app/identity/rbac_guard.py` 落点；新增 `TestEnforceModuleGrayscale` **4 例**，`test_b1_rbac_wiring.py` 实测 **20 passed**；commit **`6f06198`**（v2.16.2），三远程一致；DevLogReport 升 **v1.1.2** 新增 §14。**遗留**：实际翻转未执行（无运行服务与影子期观测数据）。详见 §6.3 |
| **v1.0.4** | **2026-10-09** | **PM/AT-OpenBase-Dev** | **执行闭环回执**：① **测试环境修复并执行**——启用 OpenLLM 既有机制 `OPENLLM_TEST_EXTRAS`（`backend/extras/.venv/Lib/site-packages`，cp313 `psycopg2-binary`）后，`test_b1_rbac_wiring.py` 实测 **16 passed**（D2-A 验收闭环）；② **播种制品已在共享库执行完成**——`192.168.0.151:5432/nuct` 按「结构先行、数据后行」执行：预检（四表存在/计数 0/重复行 0/缺唯一索引/具 `CREATE` 权限）→ DDL（建 `uq_role_permissions_role_permission`）→ DML（roles=5/permissions=27/role_permissions=34/user_roles=0）→ **幂等复跑新增 0 行**（跳过 66）；③ 附带发现：`roles.code`/`permissions.code` 唯一性由**索引型唯一约束**承载（`pg_constraint` 不含，勿误判）；④ OpenLLM commit **`1075e37`**（v2.16.1）、DevLogReport 升 **v1.1.1**，三远程一致；⑤ `RBAC_PERMISSION_ENFORCE` 前置已具备但**本批未开启、未重启服务**。详见 §6.3 |
| **v1.0.3** | **2026-10-09** | **PM/AT-OpenBase-Dev** | **播种制品跨仓交付回执**：依人工指令「立即跨仓执行」，将 B1 配套播种制品（`rbac_seed_ddl.sql` 前置结构变更 / `rbac_seed.sql` 纯 DML / `rbac_seed_manifest.json`）**照抄落位** OpenLLM `backend/scripts/rbac_seed/`，目标仓成为执行责任方；同批交付 D2 裁定 A 接线侧复核结论（`has_permission_code` 已支持 `*` 通配、G3 优先于 G1）与 3 例通配护栏用例；OpenLLM commit **`9feeec8`**（version.json → 2.16.0），三远程 origin/backup/github 哈希一致；该仓 3 例用例**未在本机执行**（环境不可用）已登记遗留。详见 §6.3 |
| **v1.0.2** | **2026-10-08** | **PM/AT-OpenBase-Dev** | **实施回执**：依人工指令「直接跨仓修复」由本仓代为实施并复核——新增 `app/identity/rbac_guard.py`（`require_permission` + 写类档位守卫 + 两段开关）、15 端点接入权限码判定、EdgeRouter 配置式 RBAC 显式 deprecated；档位锚点对齐 `role_tier_anchors.json`；TDD 13 例、本仓独立复核 33 passed、仓内 unit 3679 passed/22 failed（均为既有基线）；状态 → **已闭环**。未重启服务、未推送 |
| **v1.0.1** | **2026-10-08** | **PM-OpenBase-Dev** | **状态回写：正式分发**。依据 DevFlow 纪律（派单交付后直接推进本仓回填）：人工批准分发；状态 `[Draft] 待分发` → `[Approved] 已分发`；补 §6 分发记录与回执登记模板 |
| v1.0.0 | 2026-10-08 | PM-OpenBase-Dev | 初始创建（待分发）：登记 OpenLLM 授权接线的 P0/P1/P2 缺陷清单、交付要求、验收标准与回执要求 |

---

## §1 背景与来源

统一分析（五系统逐仓取证）显示：OpenLLM **同时存在两套 RBAC 但均未接入请求路径**，实际仅有「是否管理员」粗粒度判定——属**设计-实现偏差**（P0）。本派单为收口该偏差的正式跨仓交付。

## §2 派单范围

| 序号 | 需求 | 性质 | 优先级 |
|:----:|------|------|:------:|
| 1 | **DB RBAC 接线**（`Role/Permission/RolePermission/UserRole` → 路由依赖） | 授权实现 | **P0** |
| 2 | **弃用或改造 EdgeRouter 配置式 RBAC**（二选一并显式登记） | 架构清理 | **P0** |
| 3 | **档位守卫接线**（写类方法 ≥ `readwrite`；未映射角色 fail-closed） | 授权实现 | P1 |
| 4 | **主 JWT 补租户 claim**（主体与租户在令牌层绑定） | 契约 | P1 |
| 5 | **缺租户标识不再静默回退** | 租户语义 | P1 |
| 6 | 三轨隔离语义澄清（行级/schema/命名空间边界与优先级） | 设计澄清 | P2 |

**明确不做（本轮边界）**：① 不物理删除 EdgeRouter RBAC（仅标注 deprecated，删除另立批次）；② 不在本派单做租户注册表对齐（属 C1）；③ 不改 OpenBase 出站装配与协议头契约。

## §3 交付要求

1. **接线可证**：以**端点级正负用例**证明权限判定真实生效（有权限码 2xx / 缺权限码 403），断言不得为软断言。
2. **权限码口径**：统一 `module:action` 拼写（与 OpenBase 一致），给出完整权限码清单与角色→权限映射。
3. **档位锚点对齐**：角色→档位映射须与 OpenBase 交付制品 `config/role_tier_anchors.json` 逐项一致，**不得另立一套**。
4. **弃用登记**：被弃用的一套须在代码与文档中标注 deprecated + 替代路径 + 迁移说明。
5. **两段推进**：先**影子期**（只审计不拒绝，输出「将被拒」清单）→ 再**强制期**；两段均须有开关。
6. **设计文档同步**：把权限码清单、映射表、弃用决策、风险与回滚写入 OpenLLM 仓对应设计文档。

## §4 验收标准

| # | 验收项 | 通过标准 |
|:-:|--------|---------|
| 1 | 权限判定生效 | 每个受保护端点：具备权限码 → 2xx；缺权限码 → **403**（用例可复现） |
| 2 | 档位守卫生效 | `readonly` 写 → **403 `PERM_FORBIDDEN`**；未映射角色 → **403 `ROLE_UNMAPPED`** |
| 3 | 弃用无残留 | 无「已实现但未接线」的授权引擎；弃用件有标注与替代说明 |
| 4 | 锚点一致 | 角色→档位与 `role_tier_anchors.json` 逐项一致（供 D 批门禁脚本校验） |
| 5 | 与网关协同 | OpenBase 出站的 `X-User-Role` 可被正确解释，无 `ROLE_UNMAPPED` 误拒 |
| 6 | 回归 | 该仓单测与回归通过；影子期观测清单留存 |
| 7 | 回执留痕 | 按 §5 回执字段登记 |

## §5 分发与回执要求

1. **分发对象**：OpenLLM 仓（实施方）。
2. **回执字段**：commit hash、改动文件清单、权限码清单与角色映射、端点级正负用例结果、影子期观测摘要、单测/回归结果、三远程推送与 `ls-remote` 一致性自检结果。
3. **回执落点**：本派单项 §6 增「回执登记」段 + OpenBase 侧《总体完善方案》§5 OpenLLM 差距行状态列。
4. **状态流转**：`待分发` → `已分发` → `已回执` → `已验收（D 批门禁通过）`。

## §6 分发记录与回执登记

### 6.1 分发记录

| 项 | 内容 |
|----|------|
| 分发批次 | B1（授权接线补欠账） |
| 分发对象 | OpenLLM 仓 |
| 分发日期 | 2026-10-08 |
| 分发依据 | 人工批准（用户对话确认「按 DevFlow 纪律，直接执行 B1/C1 属跨仓事项」） |
| 随单交付物 | 本派单项 + 《OpenBase-B1-OpenLLM授权接线收口立项方案-v1.0.0》+ A 批制品（`config/role_tier_anchors.json`、`config/error_code_map.json`） |
| 本仓回填 | 《OpenBase-自研系统多租户与授权集成总体完善方案》§5 OpenLLM 差距行已回填「B1 已分发」 |
| 待回执 | OpenLLM 仓按 §5 回执字段登记（commit / 权限码清单 / 正负用例 / 影子期观测 / 回归 / 三远程一致性） |

### 6.2 回执登记（**已回执**，2026-10-08）

| 回执字段 | 值 |
|---------|-----|
| 实施方式 | 人工指令「直接跨仓修复」→ 由本仓代为实施（子代理执行 + 本仓独立复核） |
| 改动文件清单 | **新增** `backend/app/identity/rbac_guard.py`（`require_permission` + 写类档位守卫 + 两段开关）、`backend/tests/unit/test_b1_rbac_wiring.py`（13 例）、`doc/development/OpenLLM-B1-授权接线收口-DevLogReport-v1.0.0.md`；**修改** `app/identity/role_map.py`（档位锚点对齐）、`app/core/config.py`（两个开关）、`app/api/users.py`·`roles.py`·`knowledge_bases.py`·`conversations.py`（挂权限码依赖）、`app/edgerouter/auth/rbac.py`·`edge_auth.py`（G2 弃用登记）、`tests/conftest.py`、`tests/unit/test_s4_t12_role_tiers.py` |
| 权限码清单与角色映射 | 权限码 `user:read/write/delete`、`role:read/write/delete/admin`、`knowledge_base:read/write/delete`、`conversation:read/write`、`*`；`admin→*`（manage）、`org_admin→readwrite 集合`、`user/org_member/viewer→readonly 集合`。**档位锚点与 `config/role_tier_anchors.json` 逐项一致** |
| 端点覆盖 | **15 个**（users/roles/knowledge-bases/conversations），其中 10 个写类叠加档位守卫；判定链 JWT `permissions` → DB 矩阵（`*` 通配），管理员判定保留为兼容叠加层 |
| 端点级正负用例结果 | RED：5 failed（缺码 201≠403、readonly 写 201≠403、未映射 201≠403、影子期无 would-deny 日志）；GREEN：**33 passed**（本仓独立复核：`pytest tests/unit/test_b1_rbac_wiring.py tests/unit/test_s4_t12_role_tiers.py -q` → **33 passed**）+ `ruff` 新增文件 **All checks passed!** |
| 弃用登记 | `edgerouter/auth/rbac.py`（`DEPRECATED=True` + `REPLACEMENT_PATH="app/identity/rbac_guard.require_permission"`）、`edge_auth.py::RBACMiddleware` docstring；DevLogReport §7 说明选 DB RBAC 之因 |
| 两段开关 | `RBAC_PERMISSION_SHADOW`（默认 **True**，只审计不拒绝，日志 `rbac_decision=would_deny`）、`RBAC_PERMISSION_ENFORCE`（默认 **False**） |
| 回归 | 该仓 `pytest tests/unit -q`：**3679 passed / 22 failed**；22 项失败与仓内既有基线日志（`cr149-*`）逐字一致，**不含本轮改动模块** |
| 已知风险 | ① 角色→权限映射为**推荐基线、未写库**——强制期开启前须播种 DB 权限矩阵或经 JWT `permissions` 下发，否则非管理员会被拒；② 仅覆盖 15 个端点（providers/tenants/billing 未纳入）；③ 未收录角色码走 fail-closed `ROLE_UNMAPPED`，需与 OpenBase 码集并集确认 |
| 三远程推送 | **已推送**（`081c5d5`；origin/backup/github 三项哈希一致，见《总体完善方案》v1.9.0） |

### 6.3 播种制品交付回执（**已回执**，2026-10-09）

| 回执字段 | 值 |
|---------|-----|
| 交付批次 | B1 配套（权限播种受控执行前置制品） |
| 交付依据 | 人工指令「立即跨仓执行」；上游《OpenBase-B1-播种SQL评审与执行预检说明-v1.1.0》（[Approved]，D1 拆两步 / D2 取 A） |
| 目标仓 commit | **`9feeec8`**（`feat(rbac): B1 播种制品跨仓交付与执行口径登记 + D2-A 通配复核（v2.16.0）`，Refs: OB-DISPATCH-B1） |
| 随单交付物 | `rbac_seed_ddl.sql`（前置结构变更，独立交付）、`rbac_seed.sql`（纯 DML 幂等播种）、`rbac_seed_manifest.json`（计数与 id 集合）→ 落位 OpenLLM `backend/scripts/rbac_seed/` |
| 交付形态 | **照抄落位**（逐字节复制，本仓不转写、不改写），使 OpenLLM 成为**执行责任方**；制品头部内嵌目标档案声明与落点断言 |
| 目标落点口径 | 局域网共享基础设施**唯一数据库** `192.168.0.151:5432/nuct` 的 `public` schema（四系统同实例按 schema 区分）；**非**本仓本地库、**非** `openbase` schema |
| 执行口径 | **结构先行、数据后行**：①只读预检重复行为 0 → ②执行 `rbac_seed_ddl.sql`（须 `CREATE INDEX` 权限）→ ③执行 `rbac_seed.sql` → ④计数核验 + 重跑 diff=0；回滚按 manifest 的 uuid5 id 精确 `DELETE` / `DROP INDEX`。**（已执行，2026-10-09）** 预检：四表存在、计数均 0、重复行 0、缺该唯一索引、账号具 `public` 的 `CREATE` 权限 → 执行 DDL（`uq_role_permissions_role_permission` 已建）→ 执行 DML（**roles=5 / permissions=27 / role_permissions=34 / user_roles=0**，与 manifest 一致）→ **幂等复跑新增 0 行**（跳过 66） |
| D2 裁定 A 复核（接线侧） | **已实现**：`app/identity/rbac_guard.py:137-139 has_permission_code()` 支持 `*` 通配；G3 档位守卫**优先于** G1（`rbac_guard.py:246-253`），`*` **不参与**档位校验（readonly 持 `*` 写仍 403 `PERM_FORBIDDEN`） |
| 新增护栏用例 | `tests/unit/test_b1_rbac_wiring.py::TestWildcardPermissionSemantics`（3 例：纯函数通配 / DB `*` 放行写类 / `*` 不越权档位守卫） |
| 验证状态 | **已执行（2026-10-09）**：经启用该仓既有机制 `OPENLLM_TEST_EXTRAS`（`backend/extras/.venv/Lib/site-packages`，cp313 `psycopg2-binary`）修复测试环境后，`pytest tests/unit/test_b1_rbac_wiring.py -q -p no:cacheprovider` → **16 passed**（原 13 + 新增 3），**D2-A 验收闭环**。备注：`ruff` 本机未安装，本批未出具其结论 |
| 设计文档同步 | OpenLLM `doc/development/OpenLLM-B1-授权接线收口-DevLogReport-v1.0.0.md` 升 **v1.1.1 [Approved]**，含 **§13 播种制品接收与执行口径**（§13.2 执行记录 / §13.3 用例执行记录 / §13.4 强制期前置已具备） |
| 版本 | OpenLLM `version.json` → **2.16.2** |
| 三远程推送 | **已推送** `6f06198`（本回执批次，含 `9feeec8` 交付批次与 `1075e37`）；`ls-remote` 复核 origin/backup/github **三项哈希与本地一致** |
| 附带发现 | `roles.code` / `permissions.code` 的唯一性由**索引型唯一约束**（`ix_roles_code` / `ix_permissions_code`）承载而**非**表级约束——`pg_constraint` 查询不含索引型唯一约束，勿误判为缺失；故 `ON CONFLICT (code)` 前提成立 |
| 遗留 | ①**已闭环**：测试 **20 passed**（16+新增 4）；②**已闭环**：播种制品已在共享库执行完成；③**灰度机制已就位**：`RBAC_PERMISSION_ENFORCE_MODULES`（默认空=全部模块；非空=仅列出的 module 强制）→ 可按 `user → role → knowledge_base → conversation` 逐模块开强制、**单模块独立回滚**；**实际翻转仍未执行**（本机无运行服务与影子期 `would_deny` 日志，出口门禁无法判定）；④`ruff` 未安装，OpenLLM 侧未出具静态检查结论 |
