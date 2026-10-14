# OpenBase 权限管理与多租户授权走查报告

| 项 | 内容 |
|----|------|
| 文档编号 | OB-RBAC-TENANT-WALKTHROUGH-v1.0.0 |
| 文档版本 | v1.1.0 |
| 文档状态 | [Final]（v1.1.0：F1/F2/F3 已修复并回归，见 §5） |
| 适用环境 | Dev（本机全栈：OpenBase 8000 / 前端 5173 / 共享 PG） |
| 走查日期 | 2026-10-14 |
| 走查执行 | DevFlow Step 4（测试与质量验证）——权限管理与多租户授权专项走查 |
| 关联文档 | 台账《OpenBase-自研系统多租户与授权集成总体完善方案》(v1.16.26)；《OpenBase-全栈功能走查报告》OB-WALKTHROUGH-v1.0.0 (v1.1.0) |
| 证据制品 | `doc/test/evidence/manual/mtauth-rbac-tenant-walkthrough-20261014.json`；F2 修复回归 `doc/test/evidence/manual/mtauth-f2-role-codes-regression-20261014.json` |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.1.0 | 2026-10-14 | AA-OpenBase-Dev | F1/F2/F3 修复闭环：F1 架构/UI 设计 v1.4.2 文档口径更正（文档版本 v1.0.1，不改实现）；F2 角色种子补 `org_member`、`ALLOWED_ROLES` 补 `user`、新增 `memory:manage` 权限点登记 + 后端 10 例与真实 PG API 回归；F3 前端五叶子补 `meta.permission` 与菜单同源 + 守卫/菜单 34 例单测回归。§5 问题清单补修复状态与证据 |
| v1.0.0 | 2026-10-14 | AI 辅助（测试角色） | 首次产出：四角色 × 端点 × 前端逐页的权限管理与多租户授权走查 |

---

## 1. 走查目标与范围

### 1.1 目标

对 MTAUTH（多租户与授权集成）落位后的 **权限管理** 与 **多租户授权** 两条主线做端到端走查，验证：

- 权限管理：**四角色（admin / org_admin / org_member / viewer）× 关键端点** 的准入判定是否正确、错误码是否规范；前端页面级守卫与菜单可见性是否与权限码同源。
- 多租户授权：租户上下文（JWT 声明 + 受信身份头）是否正确传递；非受信来源身份头是否 fail-closed；跨租户 / 跨系统转发是否符合「空或 403、无 500」口径。

### 1.2 范围与基线

| 维度 | 基线来源 |
|------|---------|
| 端点权限口径 | 《OpenBase-架构设计文档-v1.4.2》§4.1（`/api/v1/tenants*`=admin；`/api/v1/users` POST/GET/PUT=admin/org_admin；`/users/{id}/role`、`DELETE /users/{id}`=admin） |
| 页面权限口径 | 《OpenBase-UI设计文档-v1.4.2》§2.2（用户管理页 admin/org_admin 可操作）、§3（路由守卫页面级权限） |
| 角色档位单一事实源 | `config/role_tier_anchors.json`（`canonical_role_codes.set = {admin, org_admin, org_member, user, viewer}`；档位 readonly<readwrite<manage；`unknown_code_policy=fail-closed`） |
| 隔离口径 | 单版本规划 v1.4.10（跨租户/跨组织 → 空或 403，无 500/无白屏）；AGENTS.md §5/§6 |
| 编码基线 | `openbase/core/db/init.py`（角色/权限种子）、`openbase/modules/users/__init__.py`、`openbase/modules/tenant/__init__.py`、`openbase/core/deps/auth.py`、`openbase-ui/src/core/router/index.ts`、`openbase-ui/src/pages/platform/routes.ts` |

### 1.3 不在本次范围

- 下游三仓（OpenLLM / OpenRAG / OpenMemory）自身业务数据面的隔离走查（各仓自证；本次仅记录 OpenBase 转发侧表现）。
- 真实 IdP（OIDC）/ Redis 依赖面的隔离与吊销走查（沿用既有 S7 门禁台账）。

---

## 2. 走查环境与方法

### 2.1 环境

- 全栈 7 服务 UP：openbase:8000、openllm:8001、openrag:8010、openmemory:8020、dps:8030、oidc-idp:8090、frontend:5173。
- OpenBase 数据库：共享 PostgreSQL `192.168.0.151:5432/nuct`，schema=`openbase`。
- 前端走查工具：Playwright 1.63.0（本机 `openbase-ui/node_modules` 复用，`NODE_PATH` 注入）+ 缓存 Chromium，headless。

### 2.2 方法

1. **播种**：以 admin 经 API 创建 2 个走查租户（A/B）与 4 类账号（org_admin@A、org_member@A、viewer@A、org_admin@B），命名带时间戳前缀避免与存量测试数据冲突。
2. **后端矩阵**：四身份登录 → 对 9 个关键端点（读/写）逐一探测，记录 HTTP 状态与业务错误码；补充角色分配枚举、JWT 声明解码、身份头受信判定、负控（无令牌/篡改令牌）。
3. **前端走查**：四身份分别登录 → 遍历 27 条业务路由，记录 `/forbidden` 拦截、渲染态、控制台报错、4xx/5xx 失败请求。
4. **清理**：走查后对临时用户/租户做**停用**（status=0，非破坏），并登记清理清单。

### 2.3 脚本（临时，落 `doc/tmp/mtw/`，被 .gitignore 覆盖，不入库）

`backend_matrix.py`、`probe2.py`、`ui_roles.cjs`、`consolidate.py`。

---

## 3. 权限管理走查结果

### 3.1 后端端点权限矩阵（四角色）

| 端点 | 设计期望 | admin | org_admin | viewer | 实测判定 |
|------|---------|-------|-----------|--------|---------|
| `GET /api/v1/auth/me` | 登录可见 | 200 | 200 | 200 | ✅ |
| `GET /api/v1/users` | admin/org_admin（v1.4.2 旧口径） | 200 | **403 PERM_FORBIDDEN** | **403 PERM_FORBIDDEN** | ⚠️→✅ F1（v1.1.0 裁定现行预期=admin-only，文档已更正，见 §5） |
| `POST /api/v1/users` | admin/org_admin（v1.4.2 旧口径） | 200 | **403 PERM_FORBIDDEN** | **403 PERM_FORBIDDEN** | ⚠️→✅ F1（同上） |
| `GET /api/v1/tenants` | admin | 200 | 403 PERM_FORBIDDEN | 403 PERM_FORBIDDEN | ✅ |
| `POST /api/v1/tenants` | admin | 200 | 403 PERM_FORBIDDEN | 403 PERM_FORBIDDEN | ✅ |
| `GET /api/v1/auth/api-keys` | admin/org_admin | 200 | 200 | 403 AUTH_403 | ✅ |
| `GET /api/v1/logs/search`（`log:read`） | admin/org_admin | 200 | 200 | 403 PERM_403 | ✅ |
| `POST /api/v1/identity/agents`（`identity:manage`） | admin | 400 PARAM_400（缺参，权限层已过） | 403 PERM_FORBIDDEN | 403 PERM_FORBIDDEN | ✅ 权限层正确 |
| `GET /api/v1/memory-proxy/memories` | 登录 + 上游授权 | 200 | **403（上游透传）** | **403（上游透传）** | ⚠️ 见 §4.3 |

- 结论：**主权限边界（admin 全通；org_admin 获授 `log:read` / `module:manage` / `auth:api-keys:*`；viewer 仅模块查看）与现行档位锚点一致**；v1.0.0 记录的 `users:*` 一致性缺口 F1 经裁定为文档滞后，v1.1.0 已改文档闭环（见 §5）。
- 错误码规范性：403 场景分别返回 `PERM_FORBIDDEN` / `PERM_403` / `AUTH_403`，与端点受权点声明同源，无裸 500。

### 3.2 角色分配枚举一致性

以 admin 调用 `POST /api/v1/users` 逐角色探测（`ALLOWED_ROLES = (admin, org_admin, org_member, viewer)` vs 角色表实际种子 `admin / viewer / user / org_admin`）：

| 请求角色码 | 结果 | 说明 |
|-----------|------|------|
| admin | 200 | ✅ |
| org_admin | 200 | ✅ |
| viewer | 200 | ✅ |
| **org_member** | **404 `BIZ_404 role not found: org_member`** | ❌ 角色表未播种 org_member |
| **user** | **400 `PARAM_INVALID invalid role: user`** | ❌ `ALLOWED_ROLES` 未含 user |

→ 见问题 **F2**（v1.1.0 已修复：五码种子/白名单对齐 + 真实 PG API 实测 200，见 §5）。

### 3.3 JWT 身份声明

登录后解码 access_token 载荷（示例，org_admin@租户A）：

```json
{"sub":"96","username":"wa_admin-<ts>","role":"org_admin","tenant_id":"18",
 "tenant_code":"mtw-a-<ts>","org_id":"mtw-a-<ts>","sub_type":"user","tvn":0}
```

- `role` / `tenant_id` / `tenant_code` / `org_id` / `sub_type` / `tvn` 均正确签入 ✅（多租户上下文来源正确）。

### 3.4 负控

| 用例 | 端点 | 结果 |
|------|------|------|
| 无令牌 | `/api/v1/users`、`/api/v1/tenants` | 401 `AUTH_401` ✅ |
| 篡改令牌 | `/api/v1/users` | 401 `AUTH_401` ✅ |

### 3.5 前端页面级守卫（四角色 × 27 路由）

| 角色 | 登录 | 正常渲染 | `/forbidden` 拦截路由 | 失败请求路由 |
|------|------|---------|----------------------|-------------|
| admin | ✅ | 27/27 | 无 | 无 |
| org_admin(A) | ✅ | 26/27 | `/platform/observability/test-records` | tenants、org、memory-admin |
| viewer(A) | ✅ | 24/27 | `config/modules`、`observability/logs`、`observability/test-records` | tenants、org、memory-admin |
| org_admin(B) | ✅ | 26/27 | `/platform/observability/test-records` | tenants、org、memory-admin |

- `meta.permission` 三条路由守卫准确：`module:manage`（模块开关）对 viewer 拦截；`log:read`（日志中心）对 viewer 拦截；`test:record`（测试记录）对 org_admin/viewer 均拦截（`test:record` 未播种，仅 admin 通配可见）。
- 未声明 `meta.permission` 的平台页（tenants/org/memory-admin）对非 admin **可进入但页内接口 403** → 见问题 **F3**（v1.1.0 已修复：五叶子补 `meta.permission` 与菜单同源，低档位直访跳 `/forbidden`，见 §5；修复前的本条观测作为事实保留）。

---

## 4. 多租户授权走查结果

### 4.1 租户上下文传递

- JWT 携带 `tenant_id` + `tenant_code` + `org_id`（§3.3）✅。
- `openbase/core/deps/auth.py::get_current_tenant` 存在于依赖层，但**未发现任何路由消费点**（代码检索仅定义与导出）：OpenBase 自身通过 `TenantMiddleware` 与 JWT 承载租户语义。

### 4.2 身份头受信判定

| 用例（actor=org_admin@A，端点 `/api/v1/auth/me`） | 结果 |
|--------------------------------------------------|------|
| `X-Tenant-Id: B` + `X-Proxy-Source: rogue-client`（非受信） | **403 `PERM_UNTRUSTED_IDENTITY_HEADER`**（`detail.proxy_source=rogue-client`）✅ fail-closed |
| `X-Tenant-Id: B` + `X-Proxy-Source: openbase-orchestrator`（受信） | 200；`/auth/me` 返回 JWT 内租户（该端点不依赖租户头，见 §4.1） |
| `X-Tenant-Id: A` + 受信来源 | 200（同上） |

- 结论：**非受信来源携带身份头 → fail-closed 403**，符合 `.env`（`OPENBASE_ENFORCE_INBOUND_IDENTITY_HEADERS=true`）与安全基线 ✅。

### 4.3 跨租户 / 跨系统转发

| 用例 | 结果 | 判定 |
|------|------|------|
| admin 经 `/api/v1/memory-proxy/memories` | 200（上游 OpenMemory 返回条目） | ✅ 转发链路通 |
| org_admin@A / org_admin@B 经同端点 | 403，响应体 `{code:403,message:"Forbidden",data:null,timestamp}` | ⚠️ 该报文为**上游 OpenMemory 统一响应格式**，即 OpenBase 已成功转发、**上游拒绝**（新播种租户在下游无授权，fail-closed 行为正确） |

- 说明：OpenBase 管理面（users/tenants）为平台级、admin-only，**不含租户过滤**（`list_users` / `list_tenants` 全表），与设计（admin-only 平台管理面）一致；业务数据面的租户隔离由下游三仓承担（本次仅记录转发侧行为，下游隔离归各仓自证）。

---

## 5. 问题清单与修复闭环（v1.1.0）

| # | 问题 | 严重度 | 类型 | 证据 | 处置方案 | 状态 / 修复与回归证据（2026-10-14） |
|---|------|--------|------|------|---------|-----------------------------------|
| **F1** | 架构/UI 设计（v1.4.2）声明 `/api/v1/users` POST/GET/PUT 权限为 admin/org_admin、用户管理页 org_admin 可操作；实测 org_admin 一律 403 `PERM_FORBIDDEN`（`users:manage`/`users:view` 权限点未播种，仅 admin 经 `username=="admin"` 短路放行） | 中 | **文档滞后**（现行 MTAUTH 档位锚点：org_admin=readwrite，平台管理面=manage 档=admin-only，实现与现行锚点一致） | backend-matrix、ui-roles | 更新 v1.4.2 架构/UI 文档相应行；**不改实现**（否则破坏现行档位口径） | **已闭环（改文档）**：《架构设计文档-v1.4.2》§4.1 与《UI设计文档-v1.4.2》§2.2/§3 追加「口径更正（MTAUTH 走查 F1/F2/F3）」blockquote，两文档版本 v1.0.0→v1.0.1 并各加修订行；原表记载保留、不改实现 |
| **F2** | 角色码集合三处不一致：`canonical_role_codes.set` 为五码 `{admin, org_admin, org_member, user, viewer}`，但 (a) 角色表种子缺 `org_member` → 分配 org_member 返回 404 `BIZ_404`；(b) `ALLOWED_ROLES` 缺 `user` → 分配 user 返回 400 `PARAM_INVALID` | 中 | **实现缺陷**（与已批准事实源不一致；违背「角色档位锚点需覆盖全部标准角色码集合，避免 ROLE_UNMAPPED 误拒」既有结论） | probe2 role_matrix | 按五码锚点对齐：`init.py` 幂等补种 `org_member` 角色；`ALLOWED_ROLES` 补 `user`；同步断言用例 | **已闭环（改实现）**：`openbase/core/db/init.py` 新增 `SEEDED_ROLE_CODES` 五码常量并驱动幂等角色播种（admin 显式 id=1 天然跳过），新增 `memory:manage` 权限点登记（不授予，admin 经 `*` 通配）；`openbase/modules/users/__init__.py` 的 `ALLOWED_ROLES` 补 `user` 并注释与种子对齐；模块查看权限同步授予 org_admin/org_member/user/viewer。回归：新增 `tests/test_rbac_role_codes.py`（4 例锚点/种子/白名单锁定）+ `tests/test_users_admin.py` 扩为 6 例（含五码可分配落库），**10 passed**；ruff 0 错误；真实 PG 重启补种后经 API 实测 `org_member`/`user` 创建 200（证据 `mtauth-f2-role-codes-regression-20261014.json`） |
| **F3** | 未声明 `meta.permission` 的平台页（tenants / org / memory-admin）对非 admin 可进入，页内接口 403 → 控制台报错 + 失败请求（与 `router/index.ts` §3.2 ③「权限码与菜单可见性同源，避免菜单可见但接口 403 割裂」的目标不符；`routes.ts` 注释称此类页「仅登录可见」为沿用口径） | 低-中 | **一致性缺口** | ui-roles | 为相关页补 `meta.permission` 声明（与后端权限码/菜单同名同源）；仍无独立权限码的页显式保留「仅登录可见」 | **已闭环（改前端）**：`openbase-ui/src/pages/platform/routes.ts` 五叶子补声明——租户管理 `tenant:view`、组织/团队/用户与用户管理 `users:view`、记忆管理席位 `memory:manage`、API 密钥 `auth:api-keys:view`；`AppLayout.vue` 菜单叶子同步同码（无权限不渲染）；既有全局守卫对无权限者跳 `/forbidden`；角色/工作空间/注册找回/全局配置/可观测/开发者页刻意保持仅登录可见并以用例锁定。回归：`platform-ia.spec.ts` 新增 F3 门禁/契约 8 例（低档位 5 路由→`/forbidden`、admin 通配全可达、meta 五码同源、仅登录页留空锁定），`router-nav.spec.ts` 菜单裁剪断言同步更新，两文件 **34 passed**；eslint+vue-tsc 0 错误 |

> v1.0.0 列「F1/F3 涉及口径与实现孰为基线的判断、F2 涉及契约」的待批准事项，已于 2026-10-14 经人工裁定批准：**F1 改文档（实现正确）、F2 改实现（五码对齐）、F3 采纳「补 `meta.permission` 同源声明」方案**；修复与回归见上表，原始走查观测（§3）作为修复前事实保留不回改。

---

## 6. 结论

- **权限管理**：核心边界正确——admin 全通；org_admin 获授日志/模块/服务密钥管理权限、被拒 users/tenants 管理（符合现行档位锚点）；viewer 仅模块查看；前端 `meta.permission` 三条守卫路由对低档位准确拦截；401/403 错误码规范、无裸 500。**存在 1 处文档滞后（F1）与 1 处角色码一致性缺陷（F2）**。
- **多租户授权**：JWT 租户声明完整；非受信身份头 fail-closed 403；受信来源采纳；跨系统转发对未授权租户由下游 fail-closed 拒绝。**隔离口径符合「空或 403、无 500」**。
- 总体：MTAUTH 权限与多租户授权主线**走查通过**，v1.0.0 发现的 3 项问题（1 文档滞后 + 1 实现缺陷 + 1 一致性缺口）**已在 v1.1.0 全部修复并回归闭环**（F1 文档口径更正；F2 五码对齐 + 真实 PG API 实测；F3 前端三处同源 + 34 例单测），详见 §5。

---

## 7. 证据索引

| 产物 | 路径 |
|------|------|
| 走查证据（脱敏） | `doc/test/evidence/manual/mtauth-rbac-tenant-walkthrough-20261014.json` |
| F2 修复后回归证据（脱敏） | `doc/test/evidence/manual/mtauth-f2-role-codes-regression-20261014.json`（五码创建 200 ＋ JWT 角色声明 ＋ 停用清理） |
| 后端矩阵（原始） | `doc/tmp/mtw/backend-matrix.json`（临时，不入库） |
| 补充探针（原始） | `doc/tmp/mtw/probe2.json`（临时，不入库） |
| 前端逐页（原始） | `doc/tmp/mtw/ui-roles.json`（临时，不入库） |
| 截图（关键页 × 四角色） | `doc/tmp/mtw/shots/`（临时，不入库） |

## 8. 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.1.0 | 2026-10-14 | AA-OpenBase-Dev | F1/F2/F3 修复闭环（见文首修订历史与 §5 修复证据） |
| v1.0.0 | 2026-10-14 | AI 辅助（测试角色） | 首次产出（见文首修订历史，此处为本报告主体章节尾注） |
