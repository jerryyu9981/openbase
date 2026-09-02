# OpenBase-OIDC网关统一认证集成说明-v1.4.0

| 属性   | 值                                                                         |
| ---- | ------------------------------------------------------------------------- |
| 文档编号 | OB-AUTH-OIDC-v1.4.0                                                       |
| 版本   | v1.4.0                                                                    |
| 状态   | \[Review]                                                                 |
| 日期   | 2026-09-02                                                                |
| 作者   | AD-OpenBase-Dev                                                           |
| 版本主题 | 生产 IdP claims 适配：Keycloak profile（realm\_access/resource\_access 角色聚合 + access token 兜底）已实现并端到端验证              |
| 适用范围 | OpenBase（8000）+ OpenMemory（8020）+ OpenLLM（8001）+ OpenRAG（8010）+ DPS（8030） |

> 本文档定义 OpenBase 统一网关 OIDC 认证集成方案与各下游服务的消费方式。网关侧授权码流程（§3）、OpenMemory 网关模式（§4）、真实 IdP 接入（§5）、用户体系绑定策略（§7）与生产 IdP claims 适配（§8，Keycloak profile）均已实现并验证。

## 修订历史

| 版本     | 日期         | 修改人             | 修改内容                                                                                                           |
| ------ | ---------- | --------------- | -------------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：OIDC 网关统一认证架构、OpenMemory gateway 模式落地、OpenBase 网关 OIDC 集成设计草案                                             |
| v1.1.0 | 2026-09-02 | AD-OpenBase-Dev | OpenBase 网关 OIDC 授权码流程实现落地（settings/oidc.py/白名单）+ mock IdP 端到端验证 + get\_current\_user/MeResponse OIDC sub 兼容修复 |
| v1.2.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 IdP 接入：本地标准 OIDC IdP（scripts/oidc-idp/idp\_server.py，8090）落地 + 13/13 端到端验证 + 统一 JWT 联通 OpenMemory 网关模式 |
| v1.3.0 | 2026-09-02 | AD-OpenBase-Dev | OIDC 用户体系绑定策略：OidcIdentity 映射表 + 角色种子 + JIT 自动建号 + 复用路径 user\_role 幂等补绑（显式 commit 修复）+ 绑定单测 5/5 与 E2E 10/10 |
| v1.4.0 | 2026-09-02 | AD-OpenBase-Dev | 生产 IdP claims 适配（Keycloak profile）：realm\_access/resource\_access 嵌套角色聚合 + ID Token 无角色时 access token 验签兜底；OidcIdentity 改 (issuer, sub) 复合唯一；绑定降级日志补异常堆栈；IdP 支持 OIDC\_IDP\_PROFILE=keycloak 模拟；单测 8/8 + Keycloak E2E 9/9 + generic 回归 10/10 + auth 回归 51/51 |

***

## 1. 背景与目标

OpenBase 统一网关（8000）当前以 JWT 门禁 + 四 proxy（llm-proxy/rag-proxy/memory-proxy/dps-proxy）聚合下游服务，认证为本地 HS256 共享密钥签发（modules/auth login）。计划引入 OIDC 统一认证（外部 IdP）后，需明确：

1. OIDC 只在 OpenBase 网关单点集成（授权码流程、IdP 交互、令牌签发）。
2. 下游服务（OpenMemory/OpenLLM/OpenRAG/DPS）**不再各自直连 IdP**，以"网关模式"消费网关签发的 JWT（共享密钥验签或信任网关仅解析 claims）。
3. 避免双身份源与重复 OIDC 客户端凭据。

## 2. 目标架构

```
浏览器/客户端
    │  OIDC 授权码流程（登录 IdP）
    ▼
OpenBase 统一网关（8000）
    │  ① OIDC 登录 → 换取 IdP ID Token/access token
    │  ② claims 适配（§8 profile）→ JIT 建号/复用绑定 → 签发统一 JWT
    │  ③ proxy 转发下游，携带 JWT（Authorization: Bearer）+ X-API-Key + 身份头
    ├──▶ OpenMemory (8020)：oidc_mode=gateway（本地密钥双保险 或 仅解析 claims）
    ├──▶ OpenLLM   (8001)：JWT 通道（get_current_active_user 已支持共享密钥验签）
    ├──▶ OpenRAG   (8010)：X-API-Key 透传（网关代签，OIDC 不影响）
    └──▶ DPS      (8030)：身份头注入（X-User-ID/X-Org-ID，OIDC claims 映射）
```

原则：

- **单点 IdP 交互**：仅 OpenBase 网关持有 OIDC client\_id/secret 与 discovery 配置。

- **统一令牌语义**：网关签发 HS256 JWT（与现共享密钥体系兼容，测试密钥生产替换）。

- **租户/角色传递**：OIDC claims 由网关按 profile 适配并绑定后映射进 JWT（sub=用户 id/role/tenant\_id/org\_id），下游按既有解析链路消费。

## 3. OpenBase 网关 OIDC 集成（已实现，v1.1.0）

### 3.1 配置项（openbase/settings.py 扩展，已落地）

```python
# OIDC 集成（OB-AUTH-OIDC，已实现，默认关闭）
oidc_enabled: bool = False          # 启用开关（默认关闭，不影响现有本地认证）
oidc_discovery_url: str = ""        # IdP discovery 端点
oidc_client_id: str = ""
oidc_client_secret: str = ""
oidc_redirect_uri: str = ""         # 如 http://<host>:8000/api/v1/auth/oidc/callback
oidc_scopes: str = "openid profile email"  # 空格分隔
oidc_claim_role: str = "roles"      # generic profile：角色 claim 名（平铺）
oidc_default_tenant: str = "default"  # 未映射租户时的默认值
oidc_profile: str = "generic"       # claims 适配 profile：generic | keycloak（v1.4.0）
oidc_keycloak_client_roles: bool = True  # keycloak：聚合 resource_access.<client_id>.roles（False 仅 realm 角色）
```

### 3.2 流程（已实现）

1. `GET /api/v1/auth/oidc/authorize`：返回 IdP 授权 URL（含 state；前端跳转）。
2. IdP 回调 `GET /api/v1/auth/oidc/callback`：code 换令牌（token\_endpoint）、JWKS 公钥验签 ID Token（issuer/aud/exp）。
3. 网关按 `oidc_profile` 适配角色 claims（§8）→ 用户体系绑定（§7）→ 签发统一 JWT。
4. 后续请求与现有 JWT 门禁完全一致。

**实现位置**：`openbase/modules/auth/oidc.py`（OIDCClient + authorize/callback 路由 + profile 适配 + 绑定逻辑）；`AuthMiddleware` 白名单放行 OIDC 端点；`oidc_enabled=false` 时端点返回 404。

### 3.3 与现有认证的关系

- `oidc_enabled=false`（默认）：现状不变；OIDC 端点 404。
- `oidc_enabled=true`：统一 JWT 与本地账号登录同语义（sub=用户 id/username/tenant\_id/org\_id/role）。
- 兼容修复：`get_current_user` 与 `MeResponse.id` 支持 OIDC 非数字 sub。

## 4. OpenMemory 侧集成（已实现）

OpenMemory 网关中间件支持 `oidc_mode` 双模式（`src/openmemory/gateway/gateway.py`）：

| oidc\_mode  | 行为                                                  | 适用           |
| ----------- | --------------------------------------------------- | ------------ |
| `local`（默认） | 本地 HS256 共享密钥校验（现状不变）                                 | 当前对接         |
| `gateway`   | 信任外部 OIDC 网关验签：配本地密钥双保险；无密钥仅解析 claims（保留 exp/nbf/iat 校验） | OpenBase 网关 OIDC 就绪后切换 |

切换：`OPENMEMORY_GATEWAY__OIDC_MODE=gateway`。验证：TestOidcMode 9 用例全绿。

## 5. 真实 IdP 接入（已实现，v1.2.0）

### 5.1 本地标准 OIDC IdP

`scripts/oidc-idp/idp_server.py`（FastAPI，默认监听 8090）实现标准端点：discovery / jwks / authorize（真实 HTML 登录页）/ token / userinfo。内置联调账号（roles 即角色 claim）：

| 账号 | 密码 | roles | tenant\_id |
| ---- | ---- | ---- | ---- |
| oidc-admin | oidc-pass-2026 | \[org\_admin] | default |
| oidc-user | user-pass-2026 | \[user] | default |

**claims 形状开关（v1.4.0）**：`OIDC_IDP_PROFILE=generic`（默认，roles 平铺进 ID Token）| `OIDC_IDP_PROFILE=keycloak`（角色仅进 access token：`realm_access.roles` + `resource_access.<client_id>.roles` 嵌套，模拟 Keycloak 官方默认 mapper 行为；ID Token 签发为无角色 RS256 JWT）。用于 `oidc_profile=keycloak` 的真实链路联调。

### 5.2 端到端验证基线

v1.2.0 以 8090 IdP 全链路 13/13 通过（含 OpenMemory gateway 模式消费联通）。

## 6. 验收标准

| 项                     | 验收                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------- |
| 网关 OIDC 登录            | 经 IdP 授权码流程登录成功，返回统一 JWT                                                            |
| 网关本地登录回归              | `oidc_enabled=false` 时本地账号登录行为不变                                                    |
| OpenMemory gateway 模式 | `OPENMEMORY_GATEWAY__OIDC_MODE=gateway` 后，网关签发 JWT 访问 8020 业务端点 200；过期/伪造 token 401 |
| 租户/角色透传               | OIDC 用户的 tenant\_id/role 正确映射，RBAC 判定生效                                             |
| 各服务无重复 IdP 交互         | 仅网关持有 OIDC 凭据；下游无 OIDC discovery 调用                                                 |
| 用户体系绑定（v1.3.0）        | 首次 JIT 建号、二次登录复用同一用户、user\_role 绑定持久化落库                                                |
| Keycloak profile（v1.4.0） | `oidc_profile=keycloak`：ID Token 无角色时 access token（realm\_access/resource\_access）角色兜底聚合生效；generic 行为不变（回归全绿） |

## 7. OIDC 用户体系绑定策略（已实现，v1.3.0）

### 7.1 数据模型

**OidcIdentity 映射表**（`openbase/core/models/base.py`）：

| 字段 | 类型/约束 | 说明 |
| ---- | ---- | ---- |
| user\_id | int, FK users.id, 唯一 | 绑定的 OpenBase 用户 |
| sub | str | IdP 主体标识 |
| issuer | str, 默认空 | IdP issuer |
| (issuer, sub) | 复合唯一（v1.4.0） | 取代 v1.3.0 的 sub 单列唯一；同一 sub 可来自不同 IdP/realm（生产多 IdP 场景），已有库执行幂等迁移：`DROP CONSTRAINT oidc_identity_sub_key; ADD CONSTRAINT oidc_identity_issuer_sub_key UNIQUE (issuer, sub)` |
| idp\_username / idp\_email | str 可空 | IdP 侧身份快照（幂等更新） |

**角色种子**（`openbase/core/db/init.py`）：幂等种子 `viewer / user / org_admin`（`admin` 原有）；角色 code 白名单 = `{admin, org_admin, user, viewer}`。

### 7.2 绑定策略（oidc.py `_bind_or_create_user`）

| 场景 | 策略 |
| ---- | ---- |
| 首次登录（无映射） | **JIT 自动建号**：username 取 preferred\_username > email 前缀 > sub（冲突加随机后缀）；密码置随机 hash（不可密码登录）；租户按 claims 匹配 `Tenant.code`；角色白名单绑定 `user_role`；写 `OidcIdentity` 映射 |
| 二次登录（映射命中） | **复用同一用户**：更新 IdP 侧快照（幂等）→ `_ensure_roles` 幂等补齐角色 → 显式 `session.commit()` |
| DB 异常 | **降级直签**：以 IdP sub 为 JWT 主体签发（可用性优先）；v1.4.0 起日志为 ERROR + 完整异常堆栈（原因可查） |

## 8. 生产 IdP claims 适配（已实现，v1.4.0：Keycloak profile）

### 8.1 适配问题

主流生产 IdP 与本地平铺 claims 形状不同。Keycloak 官方默认 mapper 行为：realm 角色在 `realm_access.roles`（嵌套数组）、client 角色在 `resource_access.<client_id>.roles`，且**默认仅进 access token 与 introspection，ID Token 不含角色**（[$TRAE_REF](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.2/html/server_administration_guide/assembly-managing-clients_server_administration_guide)）。

### 8.2 适配实现（oidc.py）

| 能力 | 说明 |
| ---- | ---- |
| `oidc_profile=keycloak` | callback 角色解析切换为 Keycloak 语义 |
| `_roles_from_keycloak(claims, client_id, include_client_roles)` | 角色聚合（去重保序）：平铺 roles/role（自定义 mapper 兼容）> `realm_access.roles` > `resource_access.<client_id>.roles`（可配置关闭 client 角色） |
| access token 兜底 | ID Token 聚合角色为空且有 access token 时，`verify_access_token`（同 JWKS/issuer/aud 验签，复用 `_verify_token`）解析并聚合；兜底失败仅 WARN 不中断 |
| 归一化 | 聚合结果写回 `claims["roles"]`（平铺），下游 map\_claims/\_bind\_or\_create\_user/\_ensure\_roles 零改动 |
| generic 不变 | 默认 profile=generic 完全保持 v1.3.0 平铺行为（不解析嵌套），向后兼容 |

### 8.3 验证结果（v1.4.0 实测）

- **单测**：`tests/test_oidc_keycloak.py` 8 用例全绿（realm 提取 / client 角色按 client\_id 匹配 / client 角色可关 / 平铺兼容去重 / 无角色空 / 网关链路：access token 兜底 role=org\_admin、ID Token 自带 roles 直接采用、generic 不识嵌套降 viewer）。
- **真实 E2E 9/9**：本地 IdP 以 `OIDC_IDP_PROFILE=keycloak` 起 8092（角色仅进 access token 嵌套形状）→ 网关 `oidc_profile=keycloak` 授权码全链路 → 统一 JWT sub=int（JIT 建号）、role=org\_admin（realm\_access 兜底）→ `/auth/me` 200 → PG 落库断言：`oidc_identity(issuer=8092, sub)` 与 8090 同 sub 共存（复合唯一生效）、`user_role` 含 org\_admin → 二次登录复用同用户。
- **generic 回归**：绑定 E2E 10/10（8090 平铺 claims 行为不变）；auth/RBAC/users/tenant 相关回归 51/51。

## 9. 验证方法

1. OpenMemory gateway 模式：`.env` 切 `OIDC_MODE=gateway` → 重启 8020 → 网关签发 JWT 访问业务端点 200；过期 JWT 401。
2. 单测：`python -m pytest tests/test_oidc_gateway.py tests/test_oidc_binding.py tests/test_oidc_keycloak.py`（网关 OIDC 16 用例）。
3. Keycloak profile 端到端：`OIDC_IDP_PROFILE=keycloak` 起本地 IdP（如 8092）→ 网关 `OPENBASE_OIDC_PROFILE=keycloak` + discovery 指向该 IdP → 走授权码 + PG 落库断言（复跑绑定 E2E 变体）。
4. 静态检查：`python -m ruff check openbase tests`。

## 10. 风险与注意事项

- **Keycloak 角色来源**：`oidc_profile=keycloak` 默认依赖 access token 携带 `realm_access`（官方默认）。若 Keycloak 侧未配置"realm roles"mapper 且 client 使用不透明 access token 模式（无 JWT），角色将无法获取——需启用 JWT access token 或配置 ID Token 角色 mapper。
- **租户映射**：Keycloak 无标准 tenant claim；需在 Keycloak 以自定义 mapper 输出平铺 `tenant_id`/`org`（与 OpenBase `Tenant.code` 对应），或由网关侧配置默认租户。
- **密钥管理**：共享密钥（HS256）仅限内网测试；生产建议网关签发 RS256 + JWKS。
- **令牌时效**：网关 JWT 过期时间与 IdP 会话一致或更短。
- **防伪造**：gateway 模式无本地密钥时信任网关，OpenMemory 不得直接暴露公网。
- **向后兼容**：默认 generic profile 与 `oidc_enabled=false`，现有链路零影响。

## 11. 实施待办

| 待办         | 说明                                                                                     |
| ---------- | -------------------------------------------------------------------------------------- |
| 生产 Keycloak 实配 | 以真实 Keycloak realm discovery/client 配置复跑 §9.3；按 realm 配置 realm roles / client roles / 租户 mapper claims |
| 前端登录入口     | openbase-ui 登录页增加"OIDC 登录"按钮（跳转 authorize，callback 后存 JWT）                                      |
| 生产密钥       | `OPENBASE_JWT_SECRET` 替换测试密钥；共享密钥 HS256 仅限内网                                                    |
| 其他 IdP profile（可选） | Azure AD（roles/groups + tid 租户 claim）、Okta（groups→角色）等如需对接，按 §8 模式扩展 profile 解析器            |
