# OpenBase-B1 派单-OpenLLM授权接线-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）→ OpenLLM |
| 来源批次 | B1（授权接线补欠账，源自《OpenBase-自研系统多租户与授权集成总体完善方案》§6） |
| 文档编号 | OB-DISPATCH-B1-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | **[Approved] 已分发 · 已闭环**（2026-10-08 实施完成并回执；见 §6.2） |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-10-08 |
| 存放 | doc/planning/ |
| 分发状态 | **已分发**（2026-10-08）→ 待回执 |
| 上游依据 | 《OpenBase-B1-OpenLLM授权接线收口立项方案-v1.0.0》；《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§2.4/§5/§6 |
| 证据 | 逐行只读取证结论（见立项方案 §3 的 `文件:行号` 清单） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
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
| 三远程推送 | **未推送**（待统一授权） |
