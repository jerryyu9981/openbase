# OpenBase-U1-统一身份收口设计草案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-U1-DESIGN-v1.0.0 |
| 版本 | v1.1.0 |
| 状态 | [Approved]（2026-09-07 经人工批准：按草案进入开发阶段；T1~T6 已实施完成，T7/T8 收口） |
| 日期 | 2026-09-07 |
| 作者 | U1 设计组（TS/AD） |
| 版本主题 | U1 设计草案：Principal 统一身份收口落地到 OpenBase 主仓真实代码面——数据模型增量演进（W1-4 不重建）、生命周期状态机、token 版本号吊销（方案 a）、login/refresh/OIDC 签发全量闭环 tenant_code、on_behalf_of 委托不跨界、L1-1 跨系统级联事件契约与事件源、L1-2 purge 任务（Q-5=A）、接口清单、TDD 用例清单、风险与里程碑 |
| 适用范围 | OpenBase 主仓（身份面全部改造点）；对外契约面（DPS / OpenMemory / OpenRAG 消费端适配接口，供 S2/S3/S5 段落地） |
| 上游依据 | 《OpenBase-U1-统一身份收口立项方案》v1.0.0（OB-INTG-U1-v1.0.0，任务 T1~T8、§4 验收）；《统一身份最小特征集与隔离模型设计》v1.3.0（§4.5 Principal、§5 隔离键、§10.2 Q2、§11 on_behalf_of、§12.2 R-H2 吊销、§12.7 R-M4 委托）；《多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1a 范围与门禁、Q-4/Q-5 定案） |

> 设计输入纪律：本草案为五步流程「② 架构与设计」阶段的 U1 设计产出（立项方案 §8 步骤②）。内容以「OpenBase 仓真实代码盘点结果」为落点基线（§1），与需求文档（立项方案 T1~T8 及 §4 验收标准）逐项比对，保证响应无遗漏；经人工批准后方进入开发阶段。

> **批准注记（v1.1.0）**：日期 2026-09-07；批准内容「按草案进入开发阶段」；状态由 [Draft] 更新为 [Approved]。T1~T6 已按本草案 §11 TDD 用例清单（RED→GREEN）实施完成并提交（c1869bf → 52a4792）；§11 T7/T8 断言由 U1 T7（兼容回归，含 T7-1~T7-5）/T8（文档与段门禁，含 T8-1~T8-3）收口登记（见 U1 DevLogReport v1.0.0 与测试报告 v1.0.0）。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-07 | U1 设计组 | 初始版本：现状盘点落点清单（真实代码文件+行号）、数据模型增量设计、生命周期状态机、token 吊销（方案 a）、签发闭环、on_behalf_of、L1-1/L1-2、接口清单、TDD 用例清单、风险依赖与里程碑 |
| v1.1.0 | 2026-09-07 | U1 开发组 | 状态回写（批准注记）：2026-09-07 经人工批准「按草案进入开发阶段」；[Draft] → [Approved]；登记 T1~T6 提交链（c1869bf → 52a4792）与 T7/T8 收口引用 |

---

## 1. OpenBase 仓身份面现状盘点（代码落点清单）

> 本节为 U1 设计前置的「风险 1（代码盘点）」消解产物（立项方案 §7），登记为设计阶段的**落点清单**。所有路径均为本仓相对路径（仓库根：`D:\Trae CN\myproject\Dev\OpenBase`），行号以本草案撰写时 `HEAD=0597548` 代码为准。

### 1.1 users / tenants / roles / permissions 数据表模型

模型统一收口在 `openbase/core/models/`（业务模型与其共用 `Base.metadata`，建表经 `openbase/core/db/init.py:init_database` 的 `create_all` 幂等创建）：

| 模型/表 | 文件与位置 | 关键字段与约束 | 现状要点 |
|---------|-----------|----------------|---------|
| `User` → `users` | `openbase/core/models/base.py:79-97` | `id`(BIGINT PK 自增)、`username`(String64 **unique**)、`password_hash`(String255)、`display_name`、`email`、`phone`、`status`(int，**1=启用 0=禁用**)、`tenant_id`(BIGINT **FK tenants.id**，nullable)；继承 `TimestampMixin`+`SoftDeleteMixin`（`is_deleted/deleted_at`）；`roles` 关系经 `user_role` | **无 subject 抽象**：无 `subject_type`/`credential_type`/`token_version`/`on_behalf_of`；状态为二元 int，无状态机 |
| `Role` → `roles` | `base.py:100-116` | `id`、`name`(String64 unique)、`code`(String64 **unique**)、`description`、`is_system`(bool)；`users`↔`permissions` 多对多 | RBAC 授权面；`code` 为稳定授权键（admin/org_admin/org_member/viewer 等），**无 tenant 域字段（全局角色表）** |
| `Permission` → `permissions` | `base.py:119-132` | `code`(String128 unique)、`name`、`module`、`type`(int) | 权限点表 |
| `Tenant` → `tenants` | `base.py:135-145` | `id`、`name`(String128 unique)、`code`(String64 **unique**，对外隔离键)、`status`(int 1/0)、`isolation_level`(int，1=Schema 2=行级)、`quota`(JSON) | 语义不变；`tenants.code` 即最小集 §5 唯一隔离键 |
| `OidcIdentity` → `oidc_identity` | `base.py:148-170` | `user_id`(FK users.id **unique**)、`sub`(String128)、`issuer`(String255)、复合唯一 `(issuer, sub)` | OIDC 外部身份↔用户映射（OB-AUTH-OIDC JIT 建号） |
| `Department` → `departments` | `base.py:173-186` | 树形（`parent_id`/`path`）、`tenant_id` FK | org 模块；本立项不触碰 |
| `AuditLog` → `audit_logs` | `base.py:189-206` | `user_id/tenant_id/action/resource/ip/user_agent/request_id/detail(JSON)` | 审计面；L1-1/L1-2 事件审计可复用 |
| 关联表 | `base.py:54-76` | `user_role(user_id,role_id)`、`role_permission(role_id,permission_id)`、`user_department(user_id,department_id)` | `user_role` 供 user 与 agent 通用挂载角色的复用点 |

业务表（dict/config/scheduler/storage/notify/ai_apps/frontend）在 `openbase/core/models/business.py`，均带可选 `tenant_id` FK；本立项**不改**，仅 L1-2 purge 执行器需按其属主/租户口径物理清除（见 §9）。

### 1.2 认证面现状

| 落点 | 文件与位置 | 现状关键行为 |
|------|-----------|-------------|
| **login 签发** | `openbase/modules/auth/__init__.py:213-249` | 账密校验（bcrypt，`_password_ctx` L80-95）→ `UserService.get_by_username`（DB 优先 + Redis 缓存 TTL300 + 内存降级，L142-180）→ `get_roles`（L182-207，查 `user_role→roles.code`，DB 失败回退 admin/viewer）→ 签发。**JWT claims 现状：** `sub=user.id(字符串)、username、iat/exp、type=access`，`tenant_id=users.tenant_id`（若为非空），`extra={"org_id": tenant_id值, "role": roles[0]}`。**缺 `tenant_code` claim（G-2 未闭环）**；`org_id` 写入的是 **tenant_id 数值**而非 code |
| **refresh 端点** | `auth/__init__.py:283-315` | `decode_refresh_token` → `_resolve_tenant_code(tenant_value, session)`（**L252-280**：数值→查 `tenants.code`；非数字原样透传；DB 不可达/未匹配返回 None）→ `extra={org_id: payload.org_id, role: payload.role or viewer}` → **仅当 tenant_code 解析成功才补 `claims["tenant_code"]`**。**存量 refresh token 只含 sub/tenant_id/type（无 username/role/org_id/tenant_code）**，故经 refresh 再签发时 username 丢失、org_id 为空、role 回落 viewer——这是需要收口的 fidelity 缺口 |
| **签发原语** | `openbase/modules/auth/jwt.py:38-135` | `create_access_token(subject, username, tenant_id, extra)`（L38-68）：默认有效期 **7200s**，`type=access`，有 tenant_id 才加 `claims["tenant_id"]`；`create_refresh_token`（L71-87）仅 sub/tenant_id/type，有效期 **604800s**；验签 `_decode_any`（L90-104）按 `jwt_secret` + `jwt_secret_previous`（轮换宽限）HS256 解码；`decode_access_token/decode_refresh_token` 校验 type |
| **token 校验中间件** | `openbase/core/deps/auth.py:49-108` | `AuthMiddleware`：`PUBLIC_PREFIXES`（L57-73）白名单含 `/health /docs /api/v1/auth/login /api/v1/auth/refresh /api/v1/auth/oidc /observability/status /mcp/server/info /mcp/tools /api/v1/proxy`；其余路径要求 `Bearer`，仅 `decode_access_token` **验签 + sub 非空即放行**——**无主体状态校验、无 token 版本校验（「仅验签不验状态」路径 = R-H2-3 待消灭点）** |
| **FastAPI 依赖** | `core/deps/auth.py:111-173` | `get_current_user`（L111-151）：解析 Bearer → payload → 返回 `{id, username, tenant_id, permissions}`；`get_current_tenant`（L154-173）：**优先取入站 `X-Tenant-Id` 头，其次 JWT tenant_id**（入站头高于 JWT，属 P2-1 信任链议题，本草案只登记不动） |
| **四维身份上下文** | `core/deps/auth.py:178-231` | `IdentityContext{user_id, tenant_id, team_id, agent_id}` + `get_identity_context(request)`：读 `X-User-Id/X-Tenant-Id/X-Team-Id/X-Agent-Id`，JWT 回退 user_id/tenant_id；`audit` 中间件（`openbase/modules/audit/__init__.py`）以 `extra={"team_id":…, "agent_id":…}` 记录。**已具备 agent 维度头占位（X-Agent-Id），但无 agent 实体与密钥面（§1.4）** |
| **OIDC 路径** | `openbase/modules/auth/oidc.py`（router 前缀 `/api/v1/auth/oidc`，经 auth 模块 `extra_routers` 挂载） | `map_claims`（L151-171）→ `_bind_or_create_user`（L281-399：OidcIdentity 命中复用 / JIT 建号 / **DB 异常返回 None**）；callback（L417-549）：绑定成功 `sub=users.id`，否则**降级以 IdP sub 直签**（L488-500，即「OIDC 降级直签路径」）；两分支汇合后统一 `extra={org_id: tenant_id, role}` + **P3.1 起已补 `tenant_code`**（L502-518，bound 数值 id→查 code；未绑定 code 串直传）后走同一 `create_access_token`。**结论：直签路径与正常签发已共享同一签发函数（满足立项 §6.3「同路径」），但未接入状态机/版本号**；OIDC 签发 refresh token 亦仅含 tenant_id |
| **RBAC** | `openbase/modules/auth/rbac.py` | `PermissionService`/`has_permission`：payload permissions 通配 `*` + DB 兜底 |

### 1.3 proxy 族与 service_key 鉴权

| 落点 | 文件 | 入站认证 | 出站身份注入（现状） |
|------|------|---------|---------------------|
| 通用 proxy | `openbase/modules/proxy/__init__.py:67-120`（`/api/v1/proxy/{system}/{path}`，system=openllm/openrag/openmemory/dps） | `get_proxy_identity`（`core/deps/auth.py:288-300`）：**JWT 优先 + 服务 Key 回退**（`X-API-Key` 头或 `Bearer ob_k_*` 判定为服务 Key，走 `require_api_key` L236-285，scope=system/tenants 校验） | **不注入身份头**（Content-Type/Accept 透传）——纯转发 |
| llm-proxy | `openbase/modules/llm_proxy/__init__.py`（`/api/v1/llm-proxy/*`） | JWT（`get_current_user`） | `_build_upstream_headers`(L88-112)：注入上游 `Authorization: Bearer <llm_api_key>`（OpenBase 持有）；登录态另注入 **`X-User-ID=sub`、`X-Org-ID=org_id`、`X-Proxy-Source=openbase-llm-proxy`**（L108-111）；**无 X-Tenant-ID/X-User-Role**；匿名/服务调用不带身份头 |
| rag-proxy | `openbase/modules/rag_proxy/__init__.py`（`/api/v1/rag-proxy/*`） | JWT | `_build_upstream_headers`(L82-96)：注入 `X-API-Key=<rag_api_key>`；**无任何身份/租户头** |
| dps-proxy | `openbase/modules/dps_proxy/__init__.py`（`/api/v1/dps-proxy/*`） | JWT | `_build_identity_headers`(L89-119)：注入 **四头 `X-User-ID=sub`、`X-Tenant-ID`、`X-Org-ID`、`X-User-Role=role`**；取值链：`tenant_code`(新 JWT) → `user.tenant_id` → `org_id` → `dps_default_*` → 映射表 `dps_tenant_map/dps_org_map`（L100-113，P3.1 已识别 tenant_code 优先） |
| memory-proxy | `openbase/modules/proxy/memory_proxy.py`（`/api/v1/memory-proxy/*`，R-378 OpenMemory 双层认证） | JWT | `_build_upstream_headers`(L72-93)：注入 `X-API-Key=<memory_api_key>` + **透传原 `Authorization: Bearer <原JWT>`** + `X-Org-ID=org_id|openbase-default`、`X-User-ID=sub`、`X-Tenant-ID=tenant_id|default`（无 X-User-Role） |
| **service_key 面** | `openbase/modules/auth/api_keys.py`（`ApiKeyStore`）+ `/api/v1/auth/api-keys` 三端点（`auth/__init__.py:392-449`） | — | **内存存储** + sha256 哈希（`_hash` L117-120），前缀 **`ob_k_`**（KEY_PREFIX L19），scope=`{"system":[…],"tenants":[…]}`,支持 create/revoke(软吊销)/verify/list；**非 DB 持久化、非 `sk-agent-*` 前缀、无轮换族管理（一次一明文）**。密钥服务于：`/proxy` 双通道、MCP 层（`mcp/__init__.py` X-API-Key 白名单） |

**四头（X-User-ID / X-Tenant-ID / X-Org-ID / X-User-Role）注入点汇总**：dps-proxy `_build_identity_headers`（四头齐）、memory-proxy `_build_upstream_headers`（前三头）、llm-proxy（X-User-ID/X-Org-ID/X-Proxy-Source，无 X-User-Role）、rag-proxy（无身份头）。出站取值均源自 JWT claims（sub/tenant_id/org_id/role/tenant_code）+ settings 默认值/映射表。**统一收口诉求（P2-1 委托给 S1b）**：本草案只保证 U1 范围内「claims 源（tenant_code/sub/role/sub_type/tvn）正确、可注入」，头唯一签发/信任链规范不在此列。

### 1.4 agents / 服务账号现状（结论：不存在独立身份面）

| 检查项 | 结论（实证） |
|--------|-------------|
| agents 表 / service_accounts 表 | **不存在**。`openbase/core/models/*` 全部表已列出（§1.1），无 agent 实体、无 `sk-agent-*` 密钥哈希表 |
| agent 登录/认证代码 | **不存在**。登录端点（login）仅校验 `users.password_hash`；`UserService` 无 subject_type 分叉 |
| 服务账号形态 | 仅两点雏形：① `ApiKeyStore`（`ob_k_` 前缀服务 Key，命名示例含 `gateway-agent`，供 /proxy 双通道与 MCP）；② 四维身份上下文 `IdentityContext.agent_id` 读 `X-Agent-Id` 头并进入审计 extra。两者**均无主体语义**（不挂 sub/域/角色/状态/吊销联动），即最小集 §4.5「agent=Principal 具象」的空缺实证（G-1） |
| 上游持钥（非主体） | settings 中 `llm_api_key`（前缀 `sk-openllm-*`）、`rag_api_key`、`memory_api_key` 为**上游服务 API Key（OpenBase 代持出站）**，非 OpenBase 侧 agent 凭据，语义勿混淆 |
| openbase-agent-chat-flow 目录 | 前端 HTML 产物包（`openbase-agent-chat-flow.html.zip`），非身份面代码 |

### 1.5 盘点结论 → 设计改造面映射

| 立项差距 | 实证锚点 | 对应设计章节 |
|---------|---------|-------------|
| G-1 无统一主体 | users 表无 subject 语义；无 agent 表/密钥表 | §3.1 |
| G-2 login 缺 tenant_code | `auth/__init__.py` login L237-243 无 tenant_code；refresh 条件性补齐 | §6 |
| G-3 无生命周期状态机 | `User.status` 二元 int；users DELETE 即 status=0（`users/__init__.py:243-255`）；tenants DELETE 同构 | §4 |
| G-4 状态变化不级联 | 无任何身份事件发布面（audit_logs 为被动记录）；无 outbox | §8 |
| G-5 无 retention/purge | 无 purge 路径（软删状态 + is_deleted 字段闲置） | §9 |
| R-H2 吊销不即时 | `AuthMiddleware` 仅验签（§1.2）；deps.auth `get_current_user` 不查状态 | §5 |
| R-M4 委托不跨界 | 无 on_behalf_of claim/校验器（identity 头仅透传/注入，无域不变式校验） | §7 |

---

## 2. 设计总则与关键决策基线

| 项 | 基线 |
|----|------|
| 演进范式 | **W1-4：增量演进、不重建**（立项 §6.1）：users 表为基座加列/语义扩展；既有行主键、seed、FK 不动；迁移幂等（WHERE NOT EXISTS/create_all）；`tenants`（code 唯一键）与 `roles`（RBAC 授权面）语义不变 |
| 兼容矩阵 | 既有无 tenant_code/无版本 token 按「待升级会话」过渡（§6.2 立项）：不立即拒绝 → 刷新补齐 → 版本升级 v0→v1；先上线「状态校验」、后开启「版本强校验」两段式 |
| 吊销主机制 | **方案 a token 版本号**（立项 §2.3 定案），黑名单（b）仅补充单条 sk-agent 密钥吊销场景；短 TTL 纪律保持（access 7200s→建议 300s 档可配置，不改默认以控回归面） |
| 委托语义 | on_behalf_of = 委托目标 claim；域不变式 `delegated.tenant == principal.tenant`，违例 403（R-M4-1/2）；嵌套链逐跳重校验 |
| L1-1 投递 | Redis pub/sub + DB outbox 双形态骨架；DB outbox 为可靠性主通道（秒级窗口），Redis 为加速通知 |
| L1-2 | Q-5=A：保留+阻断；purge 仅显式合规任务触发、二次授权、全程审计；**无自动限期清除路径** |

代码结构落位（新增文件均入 `openbase/modules/identity/` 模块，按 init_app 机制以 settings.enable_module 装配）：

```
openbase/modules/identity/
├── __init__.py          # router：/api/v1/identity/*（profile/lifecycle/purge/keys 端点）
├── models.py            # 与既有 core.models 合并声明的增量字段/新表（可选：直接并入 core/models）
├── state_machine.py     # 状态枚举 + 迁移矩阵校验器（纯函数，TDD 友好）
├── verifier.py          # 主体验证器：状态 + token_version 每请求校验（R-H2-3 消灭「仅验签」）
├── lifecycle.py         # 停用/恢复/注销/激活服务（写状态 + 联动吊销 + 发事件）
├── agent_keys.py        # sk-agent-* 密钥服务（发放/轮换/吊销，哈希存储）
├── delegation.py        # on_behalf_of claim 构造 + 域不变式校验器 + 嵌套链解析
├── events.py            # L1-1 事件发布（outbox 写 + Redis 通知）+ 幂等骨架
├── purge.py             # L1-2 purge 执行器 + 二次授权
└── db/migration_*.py     # 幂等迁移（create_all/WHERE NOT EXISTS 补齐）
```

## 3. 数据模型设计（增量演进 W1-4，不重建）

### 3.1 `users` 表增量改造（subject 语义 + 状态字段 + token 版本 + 租户键冗余）

在 `openbase/core/models/base.py` 的 `User` 上**新增列**（存量行由幂等迁移回填，列均可空/带默认，不触既有行主键与 FK）：

| 新增列 | 类型/默认 | 语义 | 迁移/兼容要点 |
|--------|-----------|------|---------------|
| `subject_type` | String(16)，default `"user"`，NOT NULL | `user` / `agent`（Principal 具象判别，最小集 §4.5）；agent 必带 | 存量行回填 `user`；查询/签发按此分叉 |
| `credential_type` | String(16)，nullable | 凭据面约束：user=`password`/`oidc`；agent=`api_key`（禁登录面） | 存量本地用户回填 `password`；OIDC 建号（`oidc.py` L353-364）回填 `oidc`；agent 行仅允许 `api_key` |
| `status_state` | String(24)，default `"active"` | 状态机状态：`provisioned/active/suspended/deactivated/purged` | **保留既有 `status`(int 1/0) 列**作为兼容读视图（1↔active，0↔suspended 或 deactivated 由迁移语义表定义）；新增写路径只写 `status_state`；旧读路径（list_users 等 `UserOut.status`）映射输出 |
| `status_reason` | String(255)，nullable | 状态迁移原因（审计/合规） | 可选 |
| `token_version` | Integer，default 0，NOT NULL | 吊销版本号（§5）；签发入 JWT `tvn` claim | 存量行回填 0（无版本 token 视为 v0） |
| `tenant_code` | String(64)，nullable | **租户唯一隔离键冗余列**（与 `tenants.code` 对齐），供数据面过滤与出站注入直读 | 存量行迁移按 `tenant_id → tenants.code` 回填；新建写路径同时写 `tenant_id`(FK) 与 `tenant_code`；**不替换 tenant_id FK**（键不迁移） |
| `on_behalf_of` | JSON/Text，nullable | 委托声明（agent 场景；结构见 §7） | 可选；user 行缺省 NULL = 自身域内操作 |

`roles` 关系（`user_role`）**保持通用**：agent 行亦经 `user_role` 挂角色（默认 `viewer`，S3 最小权限），`ALLOWED_ROLES` 枚举不变；查询角色码的 `UserService.get_roles` 与 `_role_codes_for` 无需按 subject_type 分叉（subject_type 仅约束凭据/登录面，不约束授权面）。

### 3.2 是否新增 `agents` 表：不新增（并列为 users.subject_type=agent），另建密钥哈希表

依据最小集 §11 定案（不建第二身份面、不作 User 子类型），U1 **不新增独立 agents 表**；agent 即 `users.subject_type='agent'` 行。新增一张**服务密钥表**：

`agent_api_keys`（新表，`openbase/core/models/base.py` 增补）：

| 列 | 类型/约束 | 说明 |
|----|-----------|------|
| `id` | BIGINT PK 自增 | |
| `agent_id` | BIGINT **FK users.id**，NOT NULL，index | agent 主体行（subject_type=agent） |
| `key_prefix` | String(16) NOT NULL | 固定 `sk-agent-`（可辨识前缀，Q2-S2） |
| `key_hash` | String(64) **unique** NOT NULL | 明文密钥 sha256 哈希（服务端不存明文；复用 `ApiKeyStore._hash` 同构算法） |
| `key_suffix` | String(16) | 明文尾部 6 位指纹（展示/人工核对用，非可逆） |
| `name` | String(64) | 密钥名（用途备注，如 `dps-profile-writer`） |
| `status` | String(16) default `active` | `active/revoked`（吊销即时失效） |
| `expires_at` | DateTime nullable | 可选到期（不设即长期） |
| `last_used_at` | DateTime nullable | 审计用 |
| `created_by` | BIGINT nullable | 发放操作者 |
| `Timestamps` | TimestampMixin | |

与现有 `ApiKeyStore`（`ob_k_` 服务 Key，内存态）的关系：**U1 不改造 ob_k_ 现有通道**（向后兼容 /proxy 双通道与 MCP）；`sk-agent-*` 是新的主体化凭据面（DB 持久化、挂主体、可多密钥轮换吊销、停用联动全失效）。ob_k_ 服务 Key 向服务账号（S6，P2-1/S1b）迁移不在本范围。

**禁登录面规则落点**：`login`/`refresh`/OIDC callback 入口在解析主体后校验 `subject_type=='user'` 才继续；`subject_type=='agent'` 一律 `AUTH_FORBIDDEN`（agent 0 可达登录路径，RA-01 断言）。判定函数集中在 `identity/state_machine.py`（如 `assert_loginable(subject_type, state)`）。

### 3.3 与既有 tenants/roles 外键关系（保持）

- `users.tenant_id → tenants.id` FK 不变；新增 `tenant_code` 为**冗余派生列**，以 `tenants.code` 为唯一事实源，写路径经 `tenants` 查 code 落列（复用 `_resolve_tenant_code` 语义，抽到共享函数 `resolve_tenant_code(session, tenant_id)`）。
- 全局唯一性照旧：`users.username` unique、`roles.code` unique 不因 subject_type 改变；**agent 用户名**复用 username 列（如 `agent:dps-profile-writer`，可读性前缀），避免与自然人冲突策略沿用 OIDC JIT 冲突加后缀的既有模式（`oidc.py:344-348`）。
- `OidcIdentity` 仅绑定 subject_type=user 主体（OIDC 绑定入口补约束断言）。
- 多租户表操作继续带 tenant 过滤（AGENTS.md §5）；`identity/lifecycle` 等平台管理面按角色门禁（admin/受权），不按行级租户过滤（管理面语义）。

### 3.4 迁移脚本（幂等，W1-4）

- `alter table` 类迁移采用「查询列是否已存在→ADD COLUMN」幂等模式（或 `create_all` 对新表/新列自动补齐 + 显式数据回填脚本）；
- 回填顺序：`tenant_code`（join tenants）→ `subject_type='user'` → `credential_type`（password/oidc 按是否在 `oidc_identity` 有映射判定）→ `status_state`（status=1→active；status=0 存量按运营判定 active/suspended/deactivated，默认 suspended 保守语义）→ `token_version=0`；
- 上线顺序纪律（立项 §8）：先状态校验发布 → 后版本强校验开启，两段式发布可回滚。

## 4. 生命周期状态机

### 4.1 状态枚举与迁移矩阵

状态（`status_state`）与迁移规则编码于 `openbase/modules/identity/state_machine.py`（纯数据/纯函数，供 API 与校验器共用）：

```text
provisioned → active → suspended ⇄ active
                         ↘ deactivated → purged
```

| 迁移 | 触发（API） | 级联动作 | 是否非法（其余组合一律 400 BIZ_STATE_TRANSITION_INVALID） |
|------|------------|---------|------|
| provisioned → active | 管理员启用 / 首次认证通过（login/OIDC/agent key 首验） | 无吊销副作用；发 `user.provisioned`（已激活语义可再发 active 事件） | — |
| active → suspended | `POST /identity/lifecycle/{subject}/suspend`（admin/受权） | **即时拒签**（login/refresh 拒绝）；**token_version += 1**（存量 access 立即失效，§5）；吊销全部 sk-agent-* key（agent）；发 `user.suspended`（L1-1） | — |
| suspended → active | `POST /identity/lifecycle/{subject}/restore`（admin/受权） | **旧 token 不复活**（token_version 再次 += 1，强制重登）；发恢复事件（L1-1，与 `role.assigned` 一致载荷可扩展） | — |
| active / suspended → deactivated | `POST /identity/lifecycle/{subject}/deactivate`（注销/管理员清除） | 全部凭据失效（token_version += 1 + sk-key 全吊销 + OIDC 绑定禁登）；数据**保留 + 全链访问阻断**（L1-2/L1-1）；发 `user.deactivated`（L1-1） | — |
| deactivated → purged | `POST /identity/purge`（显式合规任务，二次授权，§9） | 物理清除数据 + 审计留痕；发 purge 审计事件（不对外广播主体事件） | purged 为终态，无出边 |
| provisioned/suspended/deactivated → provisioned（回落） | — | 不支持 | 非法 |
| purged → 任意 | — | 不支持 | 非法 |

状态机**非法路径 0** 由 `validate_transition(current, target)` 统一拦截（RA-02 验收断言）。状态迁移登记 `audit_logs`（action=`identity.lifecycle.<to>`，resource=`users/<id>`，detail 含 `{from,to,reason,operator}`）。

### 4.2 停用 / 恢复 / 注销 API 端点与鉴权

接口族前缀 `/api/v1/identity`（新模块 `openbase/modules/identity/__init__.py` 的 router）：

| 方法/路径 | 说明 | 鉴权 |
|-----------|------|------|
| `POST /identity/lifecycle/{subject_type}/{subject_id}/activate` | provisioned→active | admin 通配 + RBAC 兜底（`identity:lifecycle`），复用 `_check_permission` 模式（照 `users/__init__.py:_require_user_manage` 写法） |
| `POST /identity/lifecycle/{subject_type}/{subject_id}/suspend` | active→suspended | 同上 |
| `POST /identity/lifecycle/{subject_type}/{subject_id}/restore` | suspended→active | 同上 |
| `POST /identity/lifecycle/{subject_type}/{subject_id}/deactivate` | →deactivated（注销） | 同上 + **本人注销需二次确认参数 `confirm`**（防误触） |
| `GET /identity/profile/{subject_type}/{subject_id}` | 四维身份视图（含状态/域/凭据形态/委托） | `identity:view` |
| 代理族/中间件只读状态 | — | 校验面见 §5 |

事件触发点（§8）：上述迁移成功提交后，在**同一 DB 事务内写 outbox**（发 `user.suspended`/`user.deactivated`/恢复事件），由 outbox 投递器发布。

### 4.3 对既有 users/tenants 管理端点的兼容

- `PUT /api/v1/users/{user_id}`（`users/__init__.py:218-240`）中 `status`(0/1) 写路径改为映射 `status_state`（0→suspended 保守）；`DELETE /users/{id}`（软删语义，L243-255）保持 = status 0（映射 suspended 语义），**不触发 deactivated 级联**（既有行为不破坏）；U1 提供的 deactivated 语义经新的 `identity/lifecycle/deactivate` 端点显式表达。
- `tenants` 状态（0/1）与用户状态机解耦：tenant 停用只影响其下主体「无法访问本域数据」由数据面/入口判定，不在本立项改租户状态机（租户生命周期属 U2 域）。

## 5. token 吊销即时性设计（方案 a：token 版本号）

### 5.1 签发 claim 与校验路径改造点

**签发侧**（`openbase/modules/auth/jwt.py`）：

| 改造点 | 现状 | 目标 |
|--------|------|------|
| `create_access_token` 入参 | `subject, username, tenant_id, extra` | 增加必填 `subject_type`、`token_version`；claim 集：`sub, username, tenant_id, tenant_code, role, org_id(兼容别名=tenant_code), sub_type, tvn, type, iat, exp` |
| `create_refresh_token` 入参 | `subject, tenant_id` | 增加 `username/tenant_code/role/sub_type/token_version`（**解决 §1.2 refresh fidelity 缺口**） |
| 公共 issuer 编排 | login/refresh/oidc 各自拼 extra | 收敛为单一签发器 `issue_token_pair(subject_row, grant_type)`：统一注入 tenant_code/sub_type/tvn/role；**OIDC 降级直签路径与正常签发共用该单一签发器**（立项 §6.3，禁止双路径分叉） |

`claims` 命名：`sub_type`（最小集 §4.1 建议的 agent 可选 claim）、`tvn`（token_version，避免与 refresh 混淆）。版本号语义：**主体每次「吊销类状态迁移 / 恢复」即 `users.token_version += 1`；签发快照写入 `tvn`**。

**校验侧**（消灭「仅验签不验状态」，R-H2-3）：

| 改造点 | 现状 | 目标 |
|--------|------|------|
| `AuthMiddleware.dispatch`（`core/deps/auth.py:75-108`） | 仅 `decode_access_token` | 增加 `verify_principal(payload)` 调用：DB 读主体（可并入 Redis 短缓存 TTL ≤60s）→ 校验 ① 主体存在 ② `status_state==active`（或 agent active）③ `tvn == users.token_version`；任一失败 401 `AUTH_PRINCIPAL_DISABLED`/`AUTH_TOKEN_STALE` |
| `get_current_user`（L111-151） | 仅解码 | 同样接入 `verify_principal`（依赖层与中间件双保险；对白名单放行路径如 `/proxy` 由端点层 `get_proxy_identity→get_current_user` 覆盖） |
| 性能 | — | 主体验证结果进程内缓存 + Redis 失效推送（状态变更即 `token_version+1` 时删缓存键 `principal:{id}`） |

### 5.2 存量无版本 token 兼容（v0）

| 场景 | 处理 |
|------|------|
| 存量 access token 无 `tvn`/`sub_type`/`tenant_code` | 视为 **v0**：兼容放行到首次 refresh（过渡期窗口，立项 §6.2）；但**主体状态校验仍即时生效**（suspend/deactivate 主体 v0 token 同样被拒——预期行为） |
| v0 token 调 refresh | 按 §6 补齐 tenant_code + 签发 tvn=1 新令牌（升级完成，v0 不再续期） |
| 版本强校验上线（第二段） | 静态扫描确保 0 条「仅验签不验状态」路径（`AUTH_TOKEN_STALE` 全量生效） |

### 5.3 吊销即时性验证路径（K04 测试基座）

| 场景 | 断言（秒级窗口） |
|------|------------------|
| suspend 后存量 access token | 立即 401（`AUTH_PRINCIPAL_DISABLED`）或最迟一次 refresh 窗口内 401 |
| suspend 后调 refresh | refresh 拒绝（签发侧校验状态） |
| restore 后 | 旧 access/refresh 均 401（tvn+1 后 token 版本落后）；重新登录可得新令牌 |
| deactivate 后 | access/refresh/agent key/OIDC 重登全入口 401/403 |
| agent suspend | 全部 sk-agent-* key 校验失败（吊销表置 revoked + 主体状态门禁双保险） |
| admin 停用联动 | 停用 API 调用即触发 tvn+1（单事务） |

## 6. login / refresh / OIDC 签发全量闭环改造（tenant_code 100%）

### 6.1 签发矩阵（目标态 claims）

| claim | login（本地） | refresh | OIDC bound | OIDC 降级直签 |
|-------|--------------|---------|-----------|---------------|
| `sub` | users.id | 透传原 sub | users.id | IdP sub（现状保留） |
| `tenant_id` | users.tenant_id | 透传 | 绑定租户 id | IdP code 串（现状保留） |
| `tenant_code` | **补：按 tenant_id 查 tenants.code** | **补：payload 携带即透传，无则 resolve** | 补（已具备，L502-518） | 原样透传（已具备） |
| `role` | roles[0] | **补：payload 透传（修 fidelity）** | bound role | claims role |
| `sub_type` | user | user | user | user |
| `tvn` | users.token_version | 透传（refresh 也带） | token_version | 0/查库后带 |
| `org_id` | =tenant_code（兼容别名） | =tenant_code | =tenant_code | =tenant_code |

**落点**：`login`（`auth/__init__.py:213-249`）改造为调用 `identity` 单一签发器；`_resolve_tenant_code`（L252-280）提升为共享函数供 login/refresh/OIDC/迁移回填复用；`refresh`（L283-315）由「条件性补 tenant_code」改为「refresh token 自身已含全量 claim，直读直签」。login 与 refresh **无条件全量签发 `tenant_code`**（RA-02 断言：注入/抽样 100%）。

### 6.2 存量 token 补齐策略

| 存量形态 | 过渡行为 |
|----------|---------|
| 无 tenant_code access（login 直发、尚未 refresh） | 校验期兼容读（视作待升级会话）；**禁止该会话写新业务域行**（出站身份头缺隔离键时由 proxy 族按现状 default/map 兜底，登记为过渡期已知行为） |
| 无 tenant_code 的 refresh | refresh 时 `_resolve_tenant_code(sub)` → 新 access 携带 tenant_code + tvn=1 |
| OIDC 直签旧令牌 | 同 v0 规则；callback 重登即出全量 claim |

补丁完成判据（T2 验收）：对本地 login 全量取样与注入用例断言 100% 含 `tenant_code`，含 refresh 再签、OIDC bound/直签双路径。

## 7. on_behalf_of 委托（agent 代表执行，不跨界）

### 7.1 claim 结构

U1 以 **JWT claim 内嵌委托块**承载（P2-1 头规范落定前的自洽形态，立项 §2.1/T4 允许）：

```jsonc
{
  "sub": "123",                  // principal 主体（agent 的 users.id）
  "sub_type": "agent",
  "tenant_code": "acme",         // principal 自身域
  "role": "viewer",
  "on_behalf_of": {              // 可选块：缺省 = 自身域内操作
    "subject_id": "88",          // 被代理目标（user/agent sub）
    "subject_type": "user",
    "tenant_code": "acme",       // 委托目标域 —— 不变式：== principal.tenant_code
    "role": "editor",            // 以目标角色执行（≤签发者授权域）
    "iss": "<delegation 签发主体>",
    "exp": "<委托有效截止>"
  }
}
```

### 7.2 域不变式校验器（R-M4-1/2）

校验器 `openbase/modules/identity/delegation.py`：

```text
def verify_delegation(principal, delegated) -> bool:
    1. principal.subject_type == "agent"                      # 仅 agent 可委托
    2. delegated.tenant_code == principal.tenant_code          # 域不变式：不等 → 403 DELEGATION_CROSS_TENANT
    3. delegated.exp 未过期；delegated.subject 存在且 active
    4. delegated.role ⊆ principal 授权域内可代理角色（≤）
    5. 嵌套链：delegated 内部若再嵌 on_behalf_of → 递归逐跳重校验（每跳 2/3/4）
```

**403 场景**（T4/K08 用例）：跨域委托（agent 域 A 代 user 域 B）→ 403；代理目标不存在/非 active → 403；代理角色越权 → 403；三级嵌套链任意一跳跨界 → 403；user 试图挂 on_behalf_of → 403。

### 7.3 注入链改造点与审计

- **签发链**：`issue_token_pair` 收到委托请求时先跑 `verify_delegation` 再签名（归属校验并签名，R-M4-1）。
- **校验链**：`AuthMiddleware`/`get_current_user` 解码后若有 `on_behalf_of` → 每请求重校验域不变式（防止 claim 中途被篡改/换域）。
- **出站注入**：代理族读 claim 时「有效域 = on_behalf_of.tenant_code（委托）否则 tenant_code（自身）」，即：
  - dps-proxy `_build_identity_headers`（`dps_proxy/__init__.py:100-113`）tenant_raw 取值源补 `on_behalf_of.tenant_code`（优先于自身 tenant_code）；
  - memory-proxy `_build_upstream_headers`（`memory_proxy.py:72-93`）与 llm-proxy `_build_upstream_headers` 同步：委托场景 `X-User-ID=delegated.subject_id`、`X-Org-ID/X-Tenant-ID=delegated.tenant_code`、`X-User-Role=delegated.role`；
  - `X-User-Role` 目前仅 dps-proxy 注入——统一出站四头齐全性属 P2-1（B-1），本立项只保证**委托场景下各 proxy 取其委托域值不取错域**。
- **审计记两层**：`audit_logs.detail` 写 `{principal: {id, tenant_code}, delegated: {id, tenant_code, role}}`（联动 `audit/__init__.py` 已支持 extra team/agent 的扩展位）。

## 8. L1-1 跨系统生命周期级联事件契约与事件源

### 8.1 事件类型与载荷

U1 事件集（立项 §2.4：`user.provisioned`/`user.suspended`/`user.deactivated` + 恢复事件；role 事件与反向收敛留 U2）：

| 事件 | 触发状态迁移 | 载荷（v1 冻结） | 消费者语义 |
|------|-------------|----------------|-----------|
| `user.provisioned` | provisioned→active（或 agent key 首验） | 见下方通用字段 | 消费端预建/对齐主体归属 |
| `user.suspended` | active→suspended | 通用字段 | 数据面**读/写阻断**（保留数据） |
| `user.restored` | suspended→active | 通用字段 | 解除阻断（与 `role.assigned` 载荷一致可扩展） |
| `user.deactivated` | active/suspended→deactivated | 通用字段 | 数据面**全链访问拒绝**（保留数据，不物理删除） |

**通用事件字段（事件 schema v1，冻结供 S2/S3/S5 消费端实现）**：

```jsonc
{
  "event_id": "uuid",                 // 全局唯一；幂等消费键
  "event_type": "user.deactivated",   // user.provisioned|user.suspended|user.restored|user.deactivated
  "occurred_at": "2026-09-07T00:00:00Z",
  "source": "openbase",
  "request_id": "req-…",              // 审计透传（U4 预留）
  "subject": {
    "subject_id": 123,                // users.id（sub）
    "subject_type": "user",           // user|agent
    "username": "alice"
  },
  "tenant_code": "acme",              // 唯一隔离键
  "role_codes": ["viewer"],           // 快照（可选）
  "previous_state": "active",
  "current_state": "deactivated",
  "reason": "管理员注销",              // 迁移原因
  "schema_version": 1
}
```

### 8.2 通道：DB outbox + Redis 通知，幂等消费

**双形态骨架**（立项 §2.4/§7 风险 3；DB outbox 为可靠性主通道，秒级窗口内投递）：

1. **outbox 表**（新表 `outbox_events`，`core/models` 增补）：`id PK`、`event_id unique`、`event_type`、`payload JSON`、`status(pending/published/failed)`、`publish_attempts`、`next_retry_at`、`created_at/published_at`。
2. **写**：生命周期迁移在**同一 DB 事务**内写 outbox（与 `status_state` 更新同事务提交，保证不丢事件，§4.2 触发点）。
3. **投递**：后台投递器（复用 `openbase/modules/scheduler` 或独立 asyncio task）轮询 pending → 发 Redis pub/sub（`openbase/core/cache/redis_client.py` 扩展 `publish/subscribe`）→ 成功置 `published`；失败重试退避；Redis 故障时 DB outbox 兜底继续轮询（不丢）。
4. **消费端幂等契约**：消费端以 `event_id` 去重（消费端幂等表 / Redis SETNX），**重放不产生重复阻断副作用**（T5 断言）。OpenBase 侧提供**消费适配接口**：`POST /api/v1/identity/events/apply`（契约桩/测试用，模拟消费端把事件按契约落本地阻断表）与 `POST /api/v1/identity/events/confirm?event_id=`（幂等确认）——S2/S3/S5 真实消费端实现时按同一 schema 对接。

**OpenBase 侧事件源落点**：`openbase/modules/identity/events.py`：`publish(subject, event_type, reason)`（同事务写 outbox）+ `outbox_dispatcher`（投递）+ `EventConsumerStub`（模拟消费端：把 deactivated/suspended 写入内存/DB 阻断集，供测试断言）。

### 8.3 DPS / OpenMemory / OpenRAG 消费适配接口（供子系统段落地）

| 系统 | 消费端形态（S2/S3/S5 实现） | 阻断语义 |
|------|---------------------------|---------|
| DPS | 消费 `user.deactivated/suspended` → 绑定表（user_roles/org 绑定）置失效；数据面入口（portrait 读等）校验主体状态 | DPS 画像读拒绝（绑定失效 → RBAC 中间件 403）；数据保留 |
| OpenMemory | 消费事件 → 归属表/阻断集；sessions/memories 访问前置校验主体 | 记忆/会话访问拒绝；数据保留 |
| OpenRAG | 消费事件 → collection/document 归属行阻断标记 | 归属行访问拒绝；数据保留 |

对接接口以「事件 schema + 幂等消费约定 + 数据面阻断验收接口（`GET /identity/blocked/{subject_id}` 契约桩）」交付，随各段落地并回填本草案附录的联调记录。

### 8.4 S7 全链验证预留钩子

`identity` 模块暴露 `GET /api/v1/identity/events/{event_id}`（状态查询）与阻断状态查询，供 S7「停用 → DPS 画像读 / OpenMemory 记忆数据面阻断」全链核验脚本调用（RA-06 聚合引用）。

## 9. L1-2 retention/purge 任务设计（Q-5=A：保留+阻断，purge 显式触发）

### 9.1 定案行为（回归断言）

- **默认无动作**：deactivated 数据保留，全链阻断（login 拒绝 + L1-1 数据面阻断）；**不存在「保留期到期自动清除」代码路径**（静态扫描 0 自动 purge 路径，T6 断言）。
- purge 属**罕见合规操作**：显式触发、影响范围报告先行、二次授权确认、全程审计。

### 9.2 purge 触发与执行链

| 环节 | 设计 |
|------|------|
| 入口 | CLI（`openbase/cli` 子命令 `identity purge --subject-id … --tenant-code …`）+ 受权端点 `POST /api/v1/identity/purge`（admin，权限点 `identity:purge`） |
| 前置校验 | ① 主体须为 `deactivated`（非 deactivated → 400）；② **影响范围报告**（将清除的关联数据清单：audit 之外各业务表按 owner/tenant 计数）；③ **二次授权**：请求体携带一次性 `purge_authorization_code`（由管理员签发、短 TTL 单次有效，等价确认令牌），未授权/过期 → 403（T6 断言「未授权触发被拒」） |
| 执行 | `identity/purge.py` 执行器：物理清除主体主行 + 关联业务数据（按 §1.1 业务表 owner/tenant 口径；**audit_logs 保留**，purge 事件写入审计）→ `status_state=purged`（终态）→ 撤销其全部密钥/映射 |
| 审计留痕 | `audit_logs` 记录 action=`identity.purge`，detail=`{subject, tenant_code, scope_report_hash, authorization_ref, operator, request_id}` |
| 幂等 | purge 重复触发对已 purged 主体返回幂等成功（不重复物理删除）或 400 终态拒绝（二选一，设计选后者并登记幂等键防并发双跑） |

### 9.3 边界

- 不自动触发（无 scheduler 定时 purge 任务注册）；
- 组织级/租户级 purge（整租户清除）属 U2/合规扩展，不在本立项（仅主体级 purge）。

## 10. 接口清单（新增 / 变更 API）

### 10.1 新增 API（identity 面）

| 方法 | 路径 | 说明 | 鉴权/依赖 |
|------|------|------|----------|
| POST | `/api/v1/identity/lifecycle/{subject_type}/{subject_id}/activate` | provisioned→active（§4.2） | admin/受权（`identity:lifecycle`） |
| POST | `/api/v1/identity/lifecycle/{subject_type}/{subject_id}/suspend` | active→suspended（联动吊销+事件） | 同上 |
| POST | `/api/v1/identity/lifecycle/{subject_type}/{subject_id}/restore` | suspended→active | 同上 |
| POST | `/api/v1/identity/lifecycle/{subject_type}/{subject_id}/deactivate` | →deactivated（注销；body `confirm=true`） | 同上 |
| GET | `/api/v1/identity/profile/{subject_type}/{subject_id}` | 四维视图（域/状态/凭据/委托） | `identity:view` |
| POST | `/api/v1/identity/agents` | 创建 agent 主体（默认 viewer + 首条 sk-agent-* 明文仅示一次） | `identity:manage` |
| GET | `/api/v1/identity/agents/{agent_id}/keys` | 密钥列表（不回显明文） | `identity:view` |
| POST | `/api/v1/identity/agents/{agent_id}/keys` | 轮换/新增 sk-agent-* key | `identity:manage` |
| DELETE | `/api/v1/identity/agents/{agent_id}/keys/{key_id}` | 吊销单条密钥（即时失效） | `identity:manage` |
| POST | `/api/v1/identity/purge` | deactivated→purged（二次授权码 + 范围报告） | admin + `identity:purge` + 一次性授权码 |
| POST | `/api/v1/identity/events/apply` | 模拟消费端应用事件（契约桩/测试/联调） | admin 或测试开关 |
| GET | `/api/v1/identity/events/{event_id}` | 事件投递状态查询（S7 钩子） | `identity:view` |

### 10.2 变更 API（既有面改造）

| 方法 | 路径 | 变更点 |
|------|------|--------|
| POST | `/api/v1/auth/login` | 签发接入单一签发器：全量 `tenant_code`+`sub_type`+`tvn`；agent 主体登录拒绝（401/403） |
| POST | `/api/v1/auth/refresh` | refresh token 全量 claim（修 fidelity）；状态门禁；v0 补齐升级 |
| GET | `/api/v1/auth/me` | 返回状态/域字段扩展（兼容新增字段） |
| GET | `/api/v1/auth/oidc/callback` | 状态机接入：suspended/deactivated 主体经 IdP 重登/JIT 建号被拒；直签路径走单一签发器 |
| — | `AuthMiddleware` / `get_current_user` | 主体验证器（状态+tvn）接入，全量路径（白名单外） |
| PUT/DELETE | `/api/v1/users/{user_id}` | `status` 写路径映射 `status_state`（兼容）；DELETE 软删语义保持 |
| POST | `/api/v1/auth/api-keys` | **不变**（ob_k_ 通道保留） |
| — | dps-proxy/llm-proxy/memory-proxy 出站 | 委托场景取委托域值；tenant_code 优先键已具备（dps-proxy P3.1），llm/memory 补 tenant_code 取值（对齐 §7.3） |

### 10.3 新增错误码（错误码规范：`openbase/core/errors/codes.py` 扩展）

`AUTH_PRINCIPAL_DISABLED`（401，主体非 active）、`AUTH_TOKEN_STALE`（401，tvn 落后/已吊销）、`BIZ_STATE_TRANSITION_INVALID`（400，状态机非法迁移）、`PERM_DELEGATION_CROSS_TENANT`（403，委托跨界）、`PERM_DELEGATION_ROLE`（403，代理角色越权）、`BIZ_PURGE_AUTH_REQUIRED`（403，purge 未二次授权）、`BIZ_NOT_PURGEABLE`（400，非 deactivated 不可 purge）。

## 11. TDD 用例清单（RED 断言示例，对应 T1~T8）

> 执行纪律：每个用例先写测试（RED，断言先行）→ 实现（GREEN）；新增代码覆盖率 ≥90%；文件落 `tests/test_identity_*.py`（沿用现仓 `tests/test_*` 命名），静态检查 `python -m ruff check openbase tests` 0 错误。

### T1 Principal 主体模型与 agent 密钥面（RA-01）

| # | RED 断言（摘录） |
|---|-----------------|
| T1-1 | 创建 `subject_type=agent` 用户行成功；`credential_type` 恒为 `api_key`，拒绝写 `password/oidc` |
| T1-2 | `POST /identity/agents` 返回明文 `sk-agent-*` 一次；DB 只存 `key_hash`（断言 `"sk-agent-" in raw_key` 且 `key_hash != raw_key`） |
| T1-3 | agent 密钥鉴权成功（`Authorization: Bearer sk-agent-…` 经 agent 校验器放行） |
| T1-4 | **登录端点对 agent 拒绝**：`POST /auth/login`（agent username+任意 password）→ 401/403，且 0 条可达 agent 的密码路径（静态扫描断言） |
| T1-5 | agent 默认角色 viewer：`get_roles` 返回含 `viewer`；未显式授权 `users:manage` 等越权调用 → 403 |
| T1-6 | 轮换/吊销：吊销后同密钥请求 → 401；多密钥并存互不影响 |
| T1-7 | 迁移幂等：迁移脚本重放两次无异常、无重复行（`WHERE NOT EXISTS`） |
| T1-8 | 存量行回填：既有 user 行迁移后 `subject_type=user`、`status_state` 映射正确、`token_version=0` |

### T2 生命周期状态机与 login 闭环（RA-02）

| # | RED 断言 |
|---|---------|
| T2-1 | 状态机合法迁移全绿：provisioned→active→suspended→active→suspended→deactivated→purged |
| T2-2 | **非法迁移 0 路径**：`validate_transition('active','purged')`、`('purged',…)`、`('provisioned','deactivated')` 等全量组合断言抛 400 |
| T2-3 | login 新签发 token claims 含 `tenant_code`；**100% 注入断言**：构造 N 用户各签一次，断言全部含 tenant_code（含 refresh 再签、OIDC bound/直签） |
| T2-4 | 存量无 tenant_code 旧 access 兼容通过（不 401），但 refresh 后新 token 补齐 tenant_code |
| T2-5 | suspended 主体 login/refresh 拒绝；restore 后重登成功 |
| T2-6 | OIDC suspended/deactivated 主体经 IdP 重登被拒（callback 401/403） |
| T2-7 | lifecycle API 鉴权：非 admin 无 `identity:lifecycle` → 403 |
| T2-8 | 停用→恢复→再停用全链路正确（状态/版本/token 各自断言） |

### T3 token 吊销即时性（K04，方案 a）

| # | RED 断言 |
|---|---------|
| T3-1 | suspend 后存量 access → 立即 401 `AUTH_PRINCIPAL_DISABLED` |
| T3-2 | suspend 后 refresh → 拒绝（签发侧状态校验） |
| T3-3 | deactivate 后 access/refresh/sk-agent-*/OIDC 重登全部 401/403 |
| T3-4 | restore 后旧 token 401 `AUTH_TOKEN_STALE`；重新 login 成功 |
| T3-5 | tvn 落后任意整数即拒（模拟 token_version=2 但 claim tvn=1） |
| T3-6 | 静态扫描 0 条「仅验签不验状态」路径（对 AuthMiddleware/get_current_user 打桩断言 verify_principal 必被调） |
| T3-7 | 缓存一致性：状态变更后 `principal:{id}` 缓存键失效（下一请求命中新状态） |

### T4 委托不跨界（K08）

| # | RED 断言 |
|---|---------|
| T4-1 | 同域委托（agent 域 A 代 user 域 A）签发成功；claims 含 on_behalf_of |
| T4-2 | 跨域委托（域 A→域 B）签发 403 `PERM_DELEGATION_CROSS_TENANT` |
| T4-3 | 每请求重校验：token 中 on_behalf_of 域被替换后请求 → 403 |
| T4-4 | 三级嵌套链任意一跳跨界 → 403；全同域 → 200 |
| T4-5 | user 挂 on_behalf_of → 403；代理目标非 active → 403；代理角色越权 → 403 |
| T4-6 | 审计 detail 记两层（principal+delegated） |
| T4-7 | dps/memory/llm proxy 委托请求出站头取委托域值（断言 X-Tenant-ID/X-Org-ID=委托 tenant_code、X-User-ID=delegated.subject_id） |

### T5 L1-1 级联事件（契约桩）

| # | RED 断言 |
|---|---------|
| T5-1 | deactivate 提交后 outbox 出现 `user.deactivated` 事件（同事务） |
| T5-2 | 模拟消费端 apply 事件后：DPS 画像读契约桩返回拒绝语义；OpenMemory 记忆访问契约桩返回拒绝 |
| T5-3 | 幂等：同 event_id 重放两次 → 阻断副作用仅一次（消费端幂等表断言） |
| T5-4 | 事件 schema 字段完整（subject/tenant_code/previous_state/current_state/reason） |
| T5-5 | 投递秒级窗口：deactivate → Redis 通知消费 ≤5s（契约桩计时断言） |
| T5-6 | suspended 事件阻断；restored 事件解除阻断 |

### T6 L1-2 purge（Q-5=A）

| # | RED 断言 |
|---|---------|
| T6-1 | **无自动限期清除**：全仓静态扫描 0 条「按保留期限自动 purge」路径；无相关 scheduler 任务 |
| T6-2 | purge 非 deactivated 主体 → 400 `BIZ_NOT_PURGEABLE` |
| T6-3 | purge 无二次授权码/过期码 → 403 `BIZ_PURGE_AUTH_REQUIRED` |
| T6-4 | 合法 purge（deactivated + 授权码 + 范围报告确认）→ 主体数据物理清除、状态=purged、audit_logs 留痕 |
| T6-5 | purge 幂等防并发：并发双触发仅一次执行 |

### T7 兼容与回归

| # | RED 断言 |
|---|---------|
| T7-1 | 既有 users/tenants/roles CRUD 用例全绿（`tests/test_users_admin.py`/`test_tenant_admin.py` 等回归） |
| T7-2 | 既有 JWT 兼容：无 tvn/tenant_code token 在过渡窗口不 401（v0 放行） |
| T7-3 | OIDC 降级直签（DB 不可用）令牌含 tenant_code/版本/状态语义与正常签发一致（同一签发器断言） |
| T7-4 | M1 独立模式回归绿（无 OpenBase 时各模块独立行为不受影响） |
| T7-5 | 迁移幂等可重放（T1-7 扩展至生产库样本） |

### T8 文档与段门禁

| # | 断言 |
|---|------|
| T8-1 | 段门禁四项全绿：login token 100% tenant_code + 吊销即时 + 委托跨界 403 + 本设计含 L1-1/L1-2（Q-5=A） |
| T8-2 | `python -m pytest tests` 全绿；`python -m ruff check openbase tests` 0 错误；覆盖率 ≥90% |
| T8-3 | 与 P2-2（S0）互证：双租户回归中新增主体身份用例不破坏既有隔离断言 |

## 12. 风险、依赖与里程碑

### 12.1 风险与缓解（承接立项 §7，落到代码面）

| # | 风险 | 缓解 |
|---|------|------|
| 1 | token 版本强校验上线误杀存量会话 | 两段式发布（先状态校验→后版本强校验）；v0 兼容窗口；回滚开关 `enforce_token_version`（settings 布尔） |
| 2 | 每请求主体验证引入 DB/Redis 读 | 进程内缓存 + Redis 失效推送（tvn+1 清键）；缓存 TTL ≤60s 兜底；中间件与依赖层共用同一验证器避免双读 |
| 3 | 事件投递一致性与 Redis 故障 | DB outbox 主通道 + Redis 加速；投递器重试退避；消费端 event_id 幂等 |
| 4 | refresh fidelity 修改影响刷新链 | 增加 claims 属向后兼容（新增字段）；回归 refresh 用例 + 抽样对比 |
| 5 | sk-agent-* 明文泄露/运营约束 | 明文仅示一次；吊销即时；agent 停用即全 key 失效联动（T3 覆盖）；部署文档固化处置流程 |
| 6 | 迁移回填误判存量 status=0 语义 | status=0 回填 suspended 保守语义 + 运营确认清单；迁移先于状态强校验发布 |
| 7 | login 改动破坏既有调用方 | 兼容矩阵（§6.2）钉死；既有 login 契约只增 claim 不删字段；回归 test_auth/test_proxy_auth |

### 12.2 依赖

- R1：`tenants.code` 唯一键与 P3.1 既有 tenant_code 基建（已具备，实证 `_resolve_tenant_code`/dps-proxy P3.1 注释）。
- R2：K08 委托头完整唯一签发收口依赖 P2-1（S1b）；U1 内完成 claim 结构/校验器/逐跳重校验骨架，头规范移交 S1b（不返工）。
- R3（外部系统配合点）：DPS/OpenMemory/OpenRAG 消费端契约冻结于本草案 §8，S2/S3/S5 段按此实现；S7 全链核验依赖各段完成。
- 与 P2-2（S0）并行：身份面改动不触碰 S0 已收口的 OpenMemory 数据面；段门禁互证（T8-3）。

### 12.3 里程碑（五步流程衔接，立项 §8）

| 步骤 | 活动与产出 | 门禁 |
|------|-----------|------|
| ① 需求 | 立项方案已 [Draft]→ 批准（0597548 已提交） | 人工批准（已完成） |
| ② 设计 | **本草案**（版本 v1.0.0 [Draft]）→ 评审（Principal 表 DDL/状态机矩阵/lifecycle API/吊销详设/L1-1 契约/L1-2 purge/落点清单/迁移脚本） | 与立项方案 T1~T8 比对无遗漏；人工批准进入开发 |
| ③ 开发 | TDD（RED→GREEN）按 T1→T8；`ruff` 0 错误；追溯矩阵 | 实现与设计一致；人工批准进入测试 |
| ④ 测试 | 单测/集成/契约桩（T5）/回归；`pytest` 全绿、覆盖率 ≥90% | 测试回溯覆盖立项 §4 验收；人工批准进入部署 |
| ⑤ 部署 | 幂等迁移（先状态校验、后版本强校验两段式）；login 闭环回归；存量过渡监控；台账回写 | S1a 门禁四项全绿 → 进入 S1b（P2-1） |

**里程碑引用**：本设计属 R1 批次；完成即 S1a 设计收官。修订本草案请按版本规范升级（主.次.修订 + 修订历史登记）。

---

## 附录 A：术语对照（本草案内使用）

| 术语 | 说明 |
|------|------|
| Principal | 统一主体抽象；users 表行经 `subject_type` 区分 user/agent 具象（最小集 §4.5） |
| tenant_code | 唯一数据隔离键（`tenants.code`）；全量进入 JWT（本草案 §6） |
| tvn | JWT 中 token 版本号 claim（`users.token_version` 快照） |
| sk-agent-* | agent 服务密钥明文前缀（哈希存 `agent_api_keys.key_hash`） |
| ob_k_* | 既有服务 Key（内存态，本立项不改造） |
| outbox | 事务内写出的可靠事件队列表（`outbox_events`） |
| v0 token | 存量无 tvn/tenant_code 的令牌（过渡期兼容形态） |

## 附录 B：参考既有文件清单（盘点实证）

- `openbase/core/models/base.py` / `business.py`（表模型）
- `openbase/modules/auth/__init__.py`（login/refresh/me/api-keys）、`jwt.py`、`oidc.py`、`rbac.py`、`api_keys.py`
- `openbase/core/deps/auth.py`（AuthMiddleware/get_current_user/get_identity_context/require_api_key/get_proxy_identity）
- `openbase/modules/proxy/__init__.py`、`proxy/memory_proxy.py`、`llm_proxy/__init__.py`、`rag_proxy/__init__.py`、`dps_proxy/__init__.py`
- `openbase/modules/users/__init__.py`、`tenant/__init__.py`、`org/__init__.py`、`audit/__init__.py`
- `openbase/__init__.py`（init_app 装配）、`openbase/settings.py`、`openbase/demo_app.py`、`openbase/core/db/init.py`
- 基线文档：`OpenBase-U1-统一身份收口立项方案-v1.0.0.md`（0597548）、`OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md`（v1.3.0）、`OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md`（v1.3.0）

