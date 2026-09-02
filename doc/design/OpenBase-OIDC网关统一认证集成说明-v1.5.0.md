# OpenBase-OIDC网关统一认证集成说明-v1.5.0

| 属性   | 值                                                                         |
| ---- | ------------------------------------------------------------------------- |
| 文档编号 | OB-AUTH-OIDC-v1.5.0                                                       |
| 版本   | v1.5.0                                                                    |
| 状态   | \[Review]                                                                 |
| 日期   | 2026-09-02                                                                |
| 作者   | AD-OpenBase-Dev                                                           |
| 版本主题 | 真实 Keycloak realm 实配：本地部署官方 Keycloak 26.7.3 + openbase realm（provision 脚本化）+ 真实授权码端到端验证               |
| 适用范围 | OpenBase（8000）+ OpenMemory（8020）+ OpenLLM（8001）+ OpenRAG（8010）+ DPS（8030） |

> 本文档定义 OpenBase 统一网关 OIDC 认证集成方案与各下游服务的消费方式。网关授权码流程（§3）、OpenMemory 网关模式（§4）、真实 IdP 接入（§5）、用户体系绑定（§7）、Keycloak profile（§8）与真实 Keycloak realm 实配（§9）均已实现并验证。

## 修订历史

| 版本     | 日期         | 修改人             | 修改内容                                                                                                           |
| ------ | ---------- | --------------- | -------------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：OIDC 网关统一认证架构、OpenMemory gateway 模式落地、OpenBase 网关 OIDC 集成设计草案                                             |
| v1.1.0 | 2026-09-02 | AD-OpenBase-Dev | OpenBase 网关 OIDC 授权码流程实现落地 + mock IdP 端到端验证 + OIDC sub 兼容修复                                              |
| v1.2.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 IdP 接入：本地标准 OIDC IdP（8090）落地 + 13/13 端到端验证 + 统一 JWT 联通 OpenMemory                                   |
| v1.3.0 | 2026-09-02 | AD-OpenBase-Dev | OIDC 用户体系绑定策略：OidcIdentity 映射表 + 角色种子 + JIT 自动建号 + 复用路径补绑修复 + E2E 10/10                             |
| v1.4.0 | 2026-09-02 | AD-OpenBase-Dev | Keycloak profile：realm\_access/resource\_access 聚合 + access token 角色兜底；(issuer, sub) 复合唯一；单测 8/8 + Keycloak 形状 E2E 9/9 |
| v1.5.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 Keycloak realm 实配：本地部署 Keycloak 26.7.3 + openbase realm（provision 幂等脚本）+ audience/tenant mapper + 伪角色白名单过滤 + at\_hash 校验 + 真实浏览器授权码 E2E（org\_admin/user 落库断言） |

***

## 1. 背景与目标

OpenBase 统一网关（8000）以 JWT 门禁 + 四 proxy 聚合下游服务。引入 OIDC 统一认证（外部 IdP）后：

1. OIDC 只在 OpenBase 网关单点集成（授权码流程、IdP 交互、令牌签发）。
2. 下游服务不再各自直连 IdP，以"网关模式"消费网关签发 JWT。
3. 避免双身份源与重复 OIDC 客户端凭据。

## 2. 目标架构

```
浏览器/客户端
    │  OIDC 授权码流程（登录 IdP：真实 Keycloak 26.7.3 / 本地 IdP）
    ▼
OpenBase 统一网关（8000）
    │  ① 授权码 → ID Token/access token
    │  ② claims 适配（§8 profile）→ JIT 绑定（§7）→ 签发统一 JWT
    │  ③ proxy 转发下游（JWT + X-API-Key + 身份头）
    ├──▶ OpenMemory (8020) / OpenLLM (8001) / OpenRAG (8010) / DPS (8030)
```

## 3. OpenBase 网关 OIDC 集成（已实现）

### 3.1 配置项（openbase/settings.py）

```python
oidc_enabled: bool = False
oidc_discovery_url: str = ""
oidc_client_id: str = ""
oidc_client_secret: str = ""
oidc_redirect_uri: str = ""
oidc_scopes: str = "openid profile email"
oidc_claim_role: str = "roles"        # generic：平铺角色 claim 名
oidc_default_tenant: str = "default"
oidc_profile: str = "generic"         # generic | keycloak（v1.4.0）
oidc_keycloak_client_roles: bool = True  # keycloak：聚合 resource_access.<client_id>.roles
```

### 3.2 流程

1. `GET /api/v1/auth/oidc/authorize`：返回 IdP 授权 URL（含 state）。
2. 回调 `GET /api/v1/auth/oidc/callback`：code 换令牌 → JWKS RS256 验签 ID Token
   （issuer/aud/exp/at\_hash，access token 传入比对，v1.5.0）→ profile 角色适配 →
   用户体系绑定（§7）→ 签发统一 JWT。
3. 后续请求与现有 JWT 门禁一致。

## 4. OpenMemory 侧集成（已实现）

`oidc_mode` 双模式（local 默认 / gateway）。切换：`OPENMEMORY_GATEWAY__OIDC_MODE=gateway`；TestOidcMode 9 用例全绿。

## 5. 本地 IdP 与 Keycloak 形状模拟（已实现，v1.2.0/v1.4.0）

- `scripts/oidc-idp/idp_server.py`（8090，generic 平铺 roles 进 ID Token）；
  `OIDC_IDP_PROFILE=keycloak` 切换为角色仅进 access token 的 Keycloak 形状（用于 §8 早期联调）。
- 演示账号：oidc-admin / oidc-pass-2026（org\_admin）、oidc-user / user-pass-2026（user）。

## 6. 验收标准

| 项 | 验收 |
| ---- | ---- |
| 网关 OIDC 登录 | 经 IdP 授权码流程登录成功，返回统一 JWT |
| 本地认证回归 | `oidc_enabled=false` 行为不变；generic profile 行为不变 |
| 用户体系绑定 | 首次 JIT 建号、二次复用、user\_role 持久化落库 |
| Keycloak profile | 嵌套角色聚合 + access token 兜底 + 伪角色过滤生效 |
| 真实 Keycloak（v1.5.0） | 官方发行版授权码登录 → role=org\_admin/user、tenant 透传、PG 落库断言 |

## 7. OIDC 用户体系绑定策略（已实现，v1.3.0+）

- **OidcIdentity 映射表**：`(issuer, sub)` 复合唯一（v1.4.0），user\_id 唯一；idp 快照字段。
- **角色种子**：viewer/user/org\_admin（+admin）幂等。
- **策略**：首次 JIT 建号（随机密码、租户按 claims 匹配 Tenant.code、角色白名单绑定）；
  复用按 sub+issuer 命中并幂等补绑（显式 commit）；DB 异常降级以 IdP sub 直签（ERROR+堆栈日志）。
- **白名单**：`OIDC_ROLE_WHITELIST=(admin, org_admin, user, viewer)`（v1.5.0 提升为常量并用于
  claims 归一化过滤，剔除 Keycloak 伪角色 default-roles-\*/offline\_access/uma\_authorization）。

## 8. Keycloak profile 适配（已实现，v1.4.0）

| 能力 | 说明 |
| ---- | ---- |
| 角色聚合 | `_roles_from_keycloak`：平铺 roles > realm\_access.roles > resource\_access.<client\_id>.roles（去重） |
| access token 兜底 | ID Token 无角色时 `verify_access_token`（同 JWKS 验签）聚合；audience 校验要求 access token aud 含 client id（Keycloak 需 audience mapper） |
| 归一化 | 聚合结果白名单过滤后写回 `claims["roles"]`（v1.5.0 过滤），下游绑定零改动 |
| generic 不变 | 默认 profile 完全保持 v1.3.0 行为 |

## 9. 真实 Keycloak realm 实配（已实现，v1.5.0）

### 9.1 部署

- 官方 Keycloak 26.7.3 发行版（Quarkus）解压于 `.runtime/keycloak-26.7.3/`（.gitignore 排除）；
  Java 21 运行：`kc.bat start-dev --http-port 8080`（dev 模式 h2 持久；admin/admin 由 KC\_BOOTSTRAP\_ADMIN\_* 预设）。
- 脚本：`scripts/keycloak/start-keycloak.ps1`。

### 9.2 openbase realm 配置（provision\_realm.py，Admin REST API 幂等）

| 项 | 值 | 说明 |
| ---- | ---- | ---- |
| realm | openbase | issuer http://127.0.0.1:8080/realms/openbase |
| realm roles | org\_admin/user/viewer | 对齐白名单 |
| client | openbase-gw | confidential + 授权码；secret openbase-kc-secret-20260902 |
| audience mapper | openbase-audience | access token aud 含 client id（默认仅 account） |
| tenant mapper | openbase-tenant-id | 用户属性 tenant\_id → claim（id/access/userinfo） |
| 用户 | oidc-admin→org\_admin、oidc-user→user | 预置资料（规避 VERIFY\_PROFILE） |

### 9.3 真实联调验证中的关键事实（v1.5.0 实测沉淀）

| 事实 | 处理 |
| ---- | ---- |
| realm 角色在 realm\_access.roles，默认仅进 access token | 网关 access token 兜底（§8） |
| access token aud 默认 `account` | client audience mapper；否则网关 audience 校验失败角色降级 |
| ID Token 携带 at\_hash | 网关验签传 access token 比对（parse\_id_token 增参） |
| 伪角色 default-roles-\*/offline\_access 等位于角色列表前部 | 归一化白名单过滤后再映射统一 JWT role |
| 新用户首次登录触发 VERIFY\_PROFILE（资料页） | provision 预置资料 + 清空 requiredActions |
| Keycloak Admin API 用户 PUT 为全量替换 | provision 更新用户带全字段（email/enabled/attributes），避免属性丢失 |
| 登录页表单 action 含 HTML 实体 / KC\_RESTART cookie | 自动化登录需 unescape 与真实浏览器会话（TRAE 浏览器/人工均可） |

### 9.4 验证结果（真实浏览器授权码 + PG 落库）

- oidc-admin 真实 Keycloak 登录 → 统一 JWT sub=绑定用户 int（14）、role=org\_admin、tenant\_id=default → /auth/me 200 → PG：oidc\_identity(issuer=8080/realms/openbase) + user\_role=org\_admin 落库。
- oidc-user 登录（登出后切换账号）→ sub=15、role=user → PG user\_role=user 落库。
- 断言脚本 `scripts/keycloak/assert_binding.py` 3/3 PASS；单测 28/28 全绿（OIDC 16 + auth/rbac）；ruff 0 错误。

### 9.5 环境切换

- 真实 Keycloak：`scripts/keycloak/start-keycloak.ps1` + `provision_realm.py` + `start-gateway-keycloak.ps1`。
- 回切本地 IdP（8090/generic）：按 .env 默认方式启动网关即可（两套互斥演示环境）。

## 10. 风险与注意事项

- **角色来源依赖**：keycloak profile 依赖 access token 为 JWT 且带 realm\_access（官方默认）。
  若 Keycloak 配置为不透明 access token 或移除 roles mapper，角色将不可得。
- **租户映射**：Keycloak 无标准 tenant claim，本实现以用户属性 + client mapper 输出 tenant\_id
  （对齐 Tenant.code）；企业可改为自定义 realm mapper。
- **密钥管理**：共享 HS256 仅限内网测试；生产建议网关 RS256 + JWKS。
- **防伪造**：gateway 模式无本地密钥时信任网关，OpenMemory 不得直接暴露公网。
- **向后兼容**：默认 generic + `oidc_enabled=false`，现有链路零影响。

## 11. 实施待办

| 待办 | 说明 |
| ---- | ---- |
| 前端登录入口 | openbase-ui 登录页增加"OIDC 登录"按钮 |
| 生产密钥 | `OPENBASE_JWT_SECRET` 替换测试密钥 |
| 企业 Keycloak 实配 | 以真实企业 realm（域名/Https/正式 client）复跑 §9；适配其租户 mapper 与角色命名 |
| 其他 IdP profile（可选） | Azure AD / Okta 等按 §8 模式扩展 profile 解析器 |
