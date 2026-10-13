# OpenBase-B2 派单-OpenRAG授权细粒度接线-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）→ OpenRAG |
| 来源批次 | B2（授权接线补欠账，源自《OpenBase-自研系统多租户与授权集成总体完善方案》§6） |
| 文档编号 | OB-DISPATCH-B2-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | **[Approved] 已分发 · 已回执**（2026-10-12 分发；2026-10-12 回执，见 §6.2） |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-10-12 |
| 存放 | doc/planning/ |
| 分发状态 | **已分发**（2026-10-12）→ **已回执**（2026-10-12，见 §6.2） |
| 上游依据 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§2.4/§5/§6；A 批制品（`config/role_tier_anchors.json`、`config/error_code_map.json`、`config/auth_consistency_matrix.json`） |
| 证据 | 本轮逐行只读取证（见 §7 `文件:行号` 清单） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.1 | 2026-10-12 | PM/AT-OpenBase-Dev | **实施回执**：依人工指令「直接跨仓实施 B2」由本仓代为实施并复核——OpenRAG `src/openrag/identity/permission_codes.py` 新增（G1 权限码判定）+ `role_gate.py` 在 G3 后接 G1（两段开关）+ `settings.py` 两开关 + 弃用件四处复核（两处补标记）+ 锚点制品照抄落位；验证 **42/42 PASS**（本机环境 `jieba` 阻断 → 按台账口径模块直接加载 + AST 断言）；commit **`d718f33`**（v1.8.0），origin/backup 齐平、**github 网络不可达待补推**；状态 → **已回执**。详见 §6.2 |
| v1.0.0 | 2026-10-12 | PM-OpenBase-Dev | 初始创建并正式分发：**依本轮实证重新界定 B2 范围**——OpenRAG 已装配 `RoleGateMiddleware` 档位守卫（G3 已闭环）且 `RBACEngine` 已显式弃用，故 B2 收敛为「**权限码级判定（G1）在 RoleGate 体系内补齐 + 锚点/契约对齐 + 弃用件登记复核**」，并登记台账 §5.1 原表述（「RBACEngine 未接线」）之偏差修正 |

---

## §1 背景与来源

统一分析（五系统逐仓取证）曾将 OpenRAG 登记为「无租户注册表、`RBACEngine` 未接线」，其中**租户注册表项已由 C1-b 闭环**（2026-10-08，21 passed）。

**本轮（2026-10-12）复核取证发现原表述已不准确**：

1. OpenRAG **已具备请求级授权** —— `RoleGateMiddleware`（档位守卫）已在 `main.py` 装配，对受信主体（user/agent）按 `X-User-Role` 经 `role_map` 本地解释为 `readonly/readwrite/manage`，读端点最低 readonly、写端点最低 readwrite，未知/缺省角色 **fail-closed 403 `ROLE_UNMAPPED`**、档位不足 **403 `PERM_FORBIDDEN`**；
2. `security/rbac_engine.py::RBACEngine` **已被显式弃用**，其 `REPLACEMENT_PATH` 指向 `api/middleware/role_gate.py`，且模块 docstring 明确「**权限码应在 `RoleGate` 体系内扩展，而非复活 `RBACEngine`**」；
3. **真实缺口**为**权限码级（`module:action`）判定未接线**——`security/middleware.py::require_permission` 定义存在但**全仓无调用点**；即 A/B1 体系的 **G1（权限码）** 在 OpenRAG 缺失，仅 **G3（档位）** 生效。

故本派单**不要求**「激活 `RBACEngine`」（那将与既有弃用决策冲突、并形成双引擎并存），而是**在与 OpenRAG 既有架构一致的前提下补齐 G1**。

## §2 派单范围

| 序号 | 需求 | 性质 | 优先级 |
|:----:|------|------|:------:|
| 1 | **权限码级判定接线**（`module:action`）——在 **RoleGate 体系内**扩展（不复活 `RBACEngine`），受保护端点具备权限码→放行 / 缺权限码→403 | 授权实现 | **P0** |
| 2 | **档位锚点对齐**——角色→档位映射须与 OpenBase 制品 `config/role_tier_anchors.json` **逐项一致**，不得另立一套 | 契约对齐 | **P0** |
| 3 | **弃用件登记复核**——`RBACEngine` / `security/models.py` / `security/middleware.py::require_permission` / `router/rbac_adapter.py` 四处（**已实现但未接线**）逐项确认：保留弃用并标注替代路径，或按需求 1 改造 | 架构清理 | **P1** |
| 4 | **两段推进**——先**影子期**（只审计不拒绝，输出「将被拒」清单）→ 再**强制期**；两段均须有开关 | 风险控制 | **P1** |
| 5 | **错误码对齐**——`PERM_FORBIDDEN` / `ROLE_UNMAPPED` 语义与 `config/error_code_map.json` 一致（含 `detail.reason`） | 契约对齐 | P2 |
| 6 | **设计文档同步**——权限码清单、角色→权限映射、弃用决策、风险与回滚写入 OpenRAG 仓对应设计文档 | 留痕 | P2 |

**明确不做（本轮边界）**：① **不复活** `RBACEngine`（弃用决策维持）；② 不改 OpenBase 出站装配与协议头契约；③ 不新增租户注册表能力（C1-b 已闭环）；④ 不引入新依赖。

## §3 交付要求

1. **接线可证**：以**端点级正负用例**证明权限码判定真实生效（有权限码 → 2xx / 缺权限码 → 403），断言不得为软断言。
2. **与既有 RoleGate 协同**：新判定须与 RoleGate 档位判定**同层或同体系**，明确判定顺序（建议档位守卫**优先于**权限码判定，与 B1/OpenLLM 的 G3 优先于 G1 口径一致）。
3. **权限码口径**：统一 `module:action` 拼写，给出完整权限码清单与角色→权限映射，且与 OpenBase 口径一致。
4. **锚点单一事实源**：角色→档位不得另立；须可直接被 D 批门禁脚本（`scripts/cross_repo_auth_gate.py`）校验。
5. **弃用登记**：四处未接线件须逐一给出「保留弃用 + 替代路径」或「改造后接线」的明确结论与理由。
6. **两段推进开关**：影子期默认开启、强制期显式开启，**默认不改变现场可用性**。
7. **测试环境与执行**：给出用例执行证据（本仓测试环境若受阻断，须说明并采用可复现的替代验证口径，逐条留痕）。

## §4 验收标准

| # | 验收项 | 通过标准 |
|:-:|--------|---------|
| 1 | 权限码判定生效 | 每个受保护端点：具备权限码 → 2xx；缺权限码 → **403**（用例可复现） |
| 2 | 档位守卫保持 | `readonly` 写 → **403 `PERM_FORBIDDEN`**；未映射角色 → **403 `ROLE_UNMAPPED`**（既有 RoleGate 行为零退化） |
| 3 | 锚点一致 | 角色→档位与 `role_tier_anchors.json` 逐项一致（D 批门禁可校验，0 FAIL） |
| 4 | 无未接线残留 | 不存在「已实现但未接线」的授权件；弃用件均有标注 + 替代路径 |
| 5 | 与网关联通 | OpenBase 出站 `X-User-Role` 可被正确解释，无 `ROLE_UNMAPPED` 误拒 |
| 6 | 回归 | 该仓单测与回归通过；**失败数不劣于基线**（须给出改动前后对比） |
| 7 | 回执留痕 | 按 §5 回执字段登记 |

## §5 分发与回执要求

1. **分发对象**：OpenRAG 仓（实施方）。
2. **回执字段**：commit hash、改动文件清单、权限码清单与角色映射、端点级正负用例结果、影子期观测摘要、单测/回归结果（改动前后对比）、三远程推送与 `ls-remote` 一致性自检结果。
3. **回执落点**：本派单项 §6 增「回执登记」段 + OpenBase 侧《总体完善方案》§5 OpenRAG 差距行状态列。
4. **状态流转**：`待分发` → `已分发` → `已回执` → `已验收（D 批门禁通过）`。

## §6 分发记录与回执登记

### 6.1 分发记录

| 项 | 内容 |
|----|------|
| 分发批次 | B2（授权接线补欠账） |
| 分发对象 | OpenRAG 仓 |
| 分发日期 | 2026-10-12 |
| 分发依据 | 人工指令「先派单 B2 OpenRAG RBACEngine 接线」（2026-10-12）；本派单据实证将范围修正为「RoleGate 体系内补齐 G1」 |
| 随单交付物 | 本派单项 + A 批制品（`config/role_tier_anchors.json`、`config/error_code_map.json`、`config/auth_consistency_matrix.json`） |
| 本仓回填 | 《OpenBase-自研系统多租户与授权集成总体完善方案》§5.1 OpenRAG 行已回填「B2 已分发」 |
| 待回执 | OpenRAG 仓按 §5 回执字段登记 |

### 6.2 回执登记（**已回执**，2026-10-12）

| 回执字段 | 值 |
|---------|-----|
| 实施方式 | 人工指令「直接跨仓实施 B2」→ 由本仓代为实施（沿用 B1 口径），并独立复核验证 |
| 目标仓 commit | **`d718f33`**（`feat(rbac): B2 授权细粒度接线（G1 权限码判定，RoleGate 体系内扩展）（v1.8.0）`，Refs: OB-DISPATCH-B2；分支 `release/v1.10.0`） |
| 改动文件清单 | **新增** `src/openrag/identity/permission_codes.py`、`config/role_tier_anchors.json`（制品照抄落位）、`tests/unit/test_b2_permission_codes.py`（14 例）、`doc/development/OpenRAG-B2-授权细粒度接线-DevLogReport-v1.0.0.md`；**修改** `src/openrag/api/middleware/role_gate.py`、`src/openrag/config/settings.py`、`src/openrag/security/middleware.py`（弃用标记）、`src/openrag/router/rbac_adapter.py`（弃用标记）、`version.json` |
| 权限码清单与角色映射 | 权限码 `module:action`（14 module：document / knowledge_base / conversation / user / organization / evaluation / dataset / connector / plugin / governance / config / tenant 等）；action 由方法映射（GET/HEAD→read；POST/PUT/PATCH→write；DELETE→delete）。角色映射由档位推导：`readonly`={`*:read`}、`readwrite`={`*:read`,`*:write`}、`manage`={`*:read`,`*:write`,`*:delete`,`*:admin`}；**无 `*` 通配**；未映射码 → 空集（fail-closed） |
| 端点覆盖 | RoleGate 覆盖的 **M2 受信主体**全路径（M1 独立模式恒跳过）；路径无已知资源段 → 不判 G1（交既有 G3） |
| 判定顺序 | **G3 档位守卫优先 → G1 权限码判定**（与 B1/OpenLLM 口径一致） |
| 两段推进开关 | `OPENRAG_IDENTITY_RBAC_PERMISSION_SHADOW`（默认 **True**，只审计不拒绝，日志 `rbac_decision=would_deny`）、`OPENRAG_IDENTITY_RBAC_PERMISSION_ENFORCE`（默认 **False**，命中即 403 `PERM_FORBIDDEN`）；有效模式 enforce > shadow > off |
| 弃用件复核 | ① `security/rbac_engine.py::RBACEngine` **保留弃用**（既有 `DEPRECATED=True` + `REPLACEMENT_PATH`），B2 **未复活**；② `security/models.py` 保留既有弃用标注；③ `security/middleware.py::require_permission` **B2 补标记**（原无标记且无调用点）；④ `router/rbac_adapter.py::RBACPermissionChecker` **B2 补标记** + 类级 `__deprecated__` |
| 锚点一致性 | `ROLE_TIER_ANCHORS` 与制品 `config/role_tier_anchors.json · anchors` **逐项一致**（admin=manage / org_admin=readwrite / user·org_member·viewer=readonly）+ 规范码集合一致（验证脚本断言通过） |
| 验证证据 | 本机以 TRAE Python 导入 `openrag` 包被 `jieba`（`preprocessing/analyzer.py`）**语法级阻断**，无法执行仓内 pytest（与台账 v1.16.4 记录一致）→ 按**台账既有口径**执行 `doc/tmp/b2_verify.py`（模块按路径直接加载 + 源码/AST 断言）：**42/42 PASS**；仓内 `tests/unit/test_b2_permission_codes.py`（14 例）已入仓供 CI 执行 |
| 回归 | 未改动 `identity/role_map.py` 档位逻辑（G3 行为零变化）；`ruff` 本机未安装（未出具结论）；仓内 pytest 待具备完整环境的流水线补出 |
| 三远程推送 | origin / backup **已推送一致**（`b73d835..d718f33`，`ls-remote` 同哈希）；**github 网络不可达**（`Failed to connect to github.com:443` / `Connection was reset`，重试 2 次失败）→ **登记 github-backfill 待补推** |
| 版本 | OpenRAG `version.json` **1.7.1 → 1.8.0** |
| 已知风险 | ① 强制期未开启（默认影子期），现场可用性零变化；翻转需运行服务 + 影子观测窗口；② 路径资源段映射为首版登记集（14 module），未登记资源段不判 G1；③ M1 独立模式下 G1 不生效（沿用既有语义） |

## §7 证据清单（本轮只读取证，2026-10-12）

| # | 结论 | 落点 |
|:-:|------|------|
| 1 | `RoleGateMiddleware` 类定义（档位/写守卫；M1 跳过、M2 激活；读 readonly / 写 readwrite；fail-closed） | `src/openrag/api/middleware/role_gate.py:53`、`:7-18` |
| 2 | **RoleGate 已装配**（置于 IdentityGate/BlockSubjectGate 之前的 add → 运行时在其后执行） | `src/openrag/main.py:123-132` |
| 3 | `RBACEngine` **已弃用**，`REPLACEMENT_PATH` = RoleGate + `identity/role_map` 档位；docstring 明确「权限码应在 RoleGate 体系内扩展，而非复活 RBACEngine」 | `src/openrag/security/rbac_engine.py:10-20`、`:29-35` |
| 4 | `require_permission(permission)` **定义存在但全仓无调用点**（G1 缺位实证） | `src/openrag/security/middleware.py:13` |
| 5 | `RBACEngine` 仍有实例化点（适配器/中间件），需在需求 3 中逐项裁决 | `src/openrag/router/rbac_adapter.py:37`、`src/openrag/security/middleware.py:62`、`src/openrag/security/routes.py:23` |
| 6 | 档位/写方法口径与错误码映射已存在（`WRITE_METHODS` / `min_tier_for_method` / `require_tier` / `RG_ERROR_CODE_BY_LITERAL`） | `src/openrag/identity/role_map.py`、`src/openrag/identity/error_codes.py` |
| 7 | 租户注册表项已由 **C1-b 闭环**（本派单不含） | 台账 §5.1 OpenRAG 行 |

> **偏差修正登记**：台账 §5.1 原表述「`RBACEngine` 未接线」易被误读为「应激活 RBACEngine」；经本轮取证，正确表述为「**G1 权限码判定缺位（G3 档位已闭环），弃用件待登记复核**」。已随本派单在台账 v1.16.10 回填修正。
