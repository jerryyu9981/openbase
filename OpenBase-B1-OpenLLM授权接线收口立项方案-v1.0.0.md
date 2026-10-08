# OpenBase-B1-OpenLLM授权接线收口立项方案-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／OpenLLM（大模型网关） |
| 文档编号 | OB-PLAN-B1-v1.0.0 |
| 批次 | **B1**（承接《OpenBase-自研系统多租户与授权集成总体完善方案》§6 B 批第 1 项） |
| 文档版本 | v1.0.0 |
| 状态 | **[Draft] 待确认**（立项与设计输入；**未执行任何代码改动**） |
| 作者 | AA-OpenBase-Dev（架构）/ PM-OpenBase-Dev（立项） |
| 创建日期 | 2026-10-08 |
| 存放 | 仓库根目录（与既有 P2-1/P2-2/U1/R1/R2 等立项方案同级） |
| 上游依据 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§2.4 / §5（OpenLLM 差距清单）/ §6 B1；《OpenBase-统一身份与主备双通道贯通总体方案》；配套派单《OpenBase-B1派单-OpenLLM授权接线-v1.0.0》 |
| 范围边界 | 本方案为**立项与设计输入**，实施须在 OpenLLM 仓按其自身五步流程（需求→设计→开发→测试→部署）推进；OpenBase 侧仅出派单、登记制品与后续验证 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-08 | AA/PM-OpenBase-Dev | 初始版本：基于逐行只读取证，登记 OpenLLM 授权的 **P0 级「双套 RBAC 均未接线」** 与 3 项 P1/P2 差距；给出「接线哪一套」的三方案对比与推荐（保留 DB RBAC + 弃用/改造 EdgeRouter 配置式）；列出实施步骤、验收标准（含负向用例）、风险与回滚、与 B1/C1 派单的关系 |

---

## §1 背景与来源

统一分析（《总体完善方案》§2.4）逐仓取证后得出：**四套后端系统里，OpenLLM 的授权实现落后于设计最多**——它同时存在两套 RBAC，但**都没有接入请求路径**，实际生效的只有「是否管理员」的粗粒度判定。这构成典型**设计-实现偏差**：审计与文档会认为系统已有 RBAC，实际路由不做权限码判定。

本批次即为收口该偏差，属 B 批最高优先级（P0）。

## §2 立项范围与目标

| 项 | 内容 |
|----|------|
| 目标 | 让 OpenLLM 的授权**真实生效**：路由级权限判定可被端点用例证明（正向 + 负向） |
| 范围 | OpenLLM 仓：`app/models/{role,permission,role_permission,user_role}.py`、`app/api/*`（路由依赖）、`app/identity/role_map.py`（档位）、`app/edgerouter/auth/*`（配置式 RBAC） |
| 非目标 | 不改 OpenBase 出站装配（`build_outbound_headers`）；不改 RAG/Memory/DPS 任何文件；不在本批次做租户注册表对齐（属 C1） |
| 交付物 | OpenLLM 侧设计文档 + 代码 + 用例 + 回归证据；OpenBase 侧登记回执与一致性验证 |

## §3 现状缺陷清单（取证：`文件:行号`）

| # | 级别 | 缺陷 | 证据 |
|:-:|:----:|------|------|
| G1 | **P0** | **DB 模型 RBAC 未接入路由**：`Role`/`Permission`/`RolePermission`/`UserRole` 与权限码格式（`resource:action`）、`Role.has_permission` 均存在，但路由侧只用「角色 ∈ {platform_admin, org_admin}」的管理员判定，**未检索到按权限码判定的路由调用** | `backend/app/models/role.py:22-103`、`backend/app/models/permission.py:20-138`、`backend/app/models/user_role.py:22-58`、`backend/app/api/user.py:79-81` |
| G2 | **P0** | **EdgeRouter 配置式 RBAC 未装配**：`RBACManager.check_permission`、`PERMISSION_MAP`（路径→资源/动作）、`RBACMiddleware` 均已实现，但主 `main.py` **未装配**该中间件（仅装配 IdentityGate/Audit/RateLimit/Metrics） | `backend/app/edgerouter/auth/rbac.py:161-333`、`backend/app/edgerouter/config/permissions.yaml:12-54`、`backend/app/edgerouter/auth/edge_auth.py:163-287`、`backend/main.py:478-500` |
| G3 | P1 | **角色档位守卫未接线**：`require_write_access_from_state` 全仓仅定义、**无调用点**；写权限依赖缺失 | `backend/app/identity/role_map.py:153-159` |
| G4 | P1 | **主应用 JWT 不含租户 claim**：access token 仅 `sub/role/type/exp`，租户只能靠受信入站头；主体与租户在令牌层不绑定 | `backend/app/services/auth_service.py:76` |
| G5 | P1 | **无租户标识不拒绝**：`resolve_tenant_request_scope` 缺 `tenant_code` 时回退 org 别名或空串（放行） | `backend/app/identity/namespace.py:190-199` |
| G6 | P2 | **API Key 走 `Authorization` 而非 `X-API-Key`**：与 JWT 同头承载，易与其他三仓（`X-API-Key`）混淆；主 JWT 无吊销 | `backend/app/services/external_identity.py:72-75`、`backend/app/services/auth_service.py:58-97` |
| G7 | P2 | **三轨隔离并存**：行级 `tenant_id` + PG schema（`tenant_<uuid8>`）+ 命名空间前缀，语义边界不清，易漏过滤 | `backend/app/services/tenant_isolation.py:17,37-99`、`backend/app/identity/namespace.py:106-199` |

## §4 设计方案（接线哪一套）

| 方案 | 内容 | 优点 | 代价/风险 | 结论 |
|:----:|------|------|----------|:----:|
| **① 保留 DB RBAC 并接线**（推荐） | 以 `Role/Permission/UserRole` 为准，新增路由依赖（等价于 OpenBase 的 `require_permission(code)`），把现有管理员判定替换为权限码判定；EdgeRouter 配置式 RBAC **明确弃用**（保留代码并标注 deprecated，或删除） | 与 OpenBase 的权限码体系统一（P4 两段式职责）；天然支持租户/团队绑定与有效期（`user_roles.organization_id/team_id/expires_at`）；与 C1 租户治理天然衔接 | 需定义权限码清单与角色映射并补种子；需把管理员判定改为兼容层（旧行为 → 新权限码）避免破坏 | ✅ **推荐** |
| ② 启用 EdgeRouter 配置式 RBAC | 装配 `RBACMiddleware`，以 `permissions.yaml` 为权限源 | 改动小（装配 + yaml） | 与 OpenBase 权限码体系**割裂**（配置式 vs DB 型）；无租户/团队绑定；`RBACManager` 路径未命中即**放行（fail-open）**，与 P5 冲突 | ❌ 不采纳 |
| ③ 两套并存且都接线 | 双引擎 | 无 | 判定顺序/覆盖语义不明，维护成本翻倍，审计无法定性 | ❌ 不采纳 |

**推荐 ① 的关键要求**：

1. 权限码命名统一为 `module:action`（与 OpenBase 一致，如 `openllm:model:write`）。
2. 档位守卫接线（G3）：写类方法要求 ≥ `readwrite`，未映射角色 **fail-closed 403 `ROLE_UNMAPPED`**（禁止静默降级）。
3. 档位/角色锚点消费 OpenBase 的登记制品 `config/role_tier_anchors.json`（A 批 A3），**不得在仓内另立一套**。
4. 弃用件的显式登记：被弃用的一套须在代码与文档中标注 deprecated 并写明替代路径（消除「有引擎未用」的假象）。
5. 分两段推进：**影子期**（只审计不拒绝，输出「将被拒」的观测）→ **强制期**（真正 403），避免一次性打断存量调用方。

## §5 实施步骤与验收标准

| 步 | 内容 |
|:--:|------|
| S1 | 需求：在 OpenLLM 仓登记「授权接线收口」需求与验收标准（引用本方案 §3 缺陷清单） |
| S2 | 设计：权限码清单 + 角色→权限映射 + 与 OpenBase 锚点表的对齐说明 + 弃用件处置 + 影子期开关设计 |
| S3 | 开发：路由依赖接线、档位守卫接线、种子数据、弃用标注（TDD：先写端点级正/负用例） |
| S4 | 测试：端点级正负用例、跨租户用例、回归与覆盖率 |
| S5 | 部署：影子期上线 → 观测 → 强制期切换（含回滚开关） |

| # | 验收项 | 通过标准 |
|:-:|--------|---------|
| 1 | 权限码判定生效 | 对每个受保护端点：具备权限码 → 2xx；**缺该权限码 → 403**（负向用例可复现） |
| 2 | 档位守卫生效 | `readonly` 主体写类方法 → **403 `PERM_FORBIDDEN`**；未映射角色 → **403 `ROLE_UNMAPPED`** |
| 3 | 弃用登记 | 被弃用的一套有 deprecated 标注与替代说明；无「未接线的引擎」残留 |
| 4 | 锚点一致 | 角色→档位映射与 `config/role_tier_anchors.json` 逐项一致（由 D 批门禁脚本校验） |
| 5 | 与 OpenBase 出站一致 | 网关出站的 `X-User-Role` 值可被 OpenLLM 正确解释，无 `ROLE_UNMAPPED` 误拒 |
| 6 | 租户语义收紧（G5） | 缺租户标识的业务请求按设计处置（拒绝或显式缺省），**不再静默回退** |

## §6 风险与回滚

| # | 风险 | 等级 | 缓解 |
|:-:|------|:----:|------|
| R1 | 强制期暴露存量「无权限码」调用方，造成可用性中断 | **高** | 影子期（只审计不拒绝）→ 观测清单 → 强制期；保留一键回滚开关 |
| R2 | 权限码体系与 OpenBase 割裂导致双重维护 | 中 | 以 OpenBase 权限码为唯一拼写口径；由 D 批门禁校验一致性 |
| R3 | 弃用 EdgeRouter RBAC 影响其既有边缘链路 | 中 | 先确认无线上依赖；保留代码仅标注 deprecated（不物理删除），删除另立批次 |
| R4 | 主 JWT 补租户 claim（G4）会改变令牌结构 | 中 | 与 C1 同批；令牌增字段为向后兼容变更，旧令牌仍可解析 |

**回滚**：影子期开关置回「只审计」即恢复既有行为；不涉及数据迁移。

## §7 前置依赖与派单关系

| 项 | 内容 |
|----|------|
| 依赖 1 | A 批 A3 产出 `config/role_tier_anchors.json`（档位锚点表）——**已完成**（本仓） |
| 依赖 2 | A 批 A4 产出 `config/error_code_map.json`（错误码映射，供排障与归因）——**已完成**（本仓） |
| 派单 | 本方案配套《OpenBase-B1派单-OpenLLM授权接线-v1.0.0》：交付对象为 OpenLLM 仓 |
| 关联 | C1（租户注册表对齐，G4/G5 与本批次部分重叠，建议同窗口推进） |
