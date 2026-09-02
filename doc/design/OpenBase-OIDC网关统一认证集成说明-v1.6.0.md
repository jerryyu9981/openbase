# OpenBase-OIDC网关统一认证集成说明-v1.6.0

| 属性   | 值                                                                         |
| ---- | ------------------------------------------------------------------------- |
| 文档编号 | OB-AUTH-OIDC-v1.6.0                                                       |
| 版本   | v1.6.0                                                                    |
| 状态   | \[Review]                                                                 |
| 日期   | 2026-09-02                                                                |
| 作者   | AD-OpenBase-Dev                                                           |
| 版本主题 | 前端 OIDC 登录：登录页"OIDC 统一登录"按钮 + 前端回调路由（fragment 令牌）+ 真实浏览器全链路验证               |
| 适用范围 | OpenBase（8000）+ openbase-ui（5173）+ Keycloak（8080）+ 本地 IdP（8090）+ OpenMemory/OpenLLM/OpenRAG/DPS |

> 本文档定义 OpenBase 统一网关 OIDC 认证集成方案与各下游服务消费方式。网关授权码（§3）、OpenMemory 网关模式（§4）、本地 IdP（§5）、用户体系绑定（§7）、Keycloak profile（§8）、真实 Keycloak realm（§9）与前端 OIDC 登录（§10）均已实现并验证。

## 修订历史

| 版本     | 日期         | 修改人             | 修改内容                                                                                                           |
| ------ | ---------- | --------------- | -------------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：OIDC 网关统一认证架构、OpenMemory gateway 模式落地、OpenBase 网关 OIDC 集成设计草案                                             |
| v1.1.0 | 2026-09-02 | AD-OpenBase-Dev | OpenBase 网关 OIDC 授权码流程实现落地 + mock IdP 端到端验证 + OIDC sub 兼容修复                                              |
| v1.2.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 IdP 接入：本地标准 OIDC IdP（8090）落地 + 13/13 端到端验证 + 统一 JWT 联通 OpenMemory                                   |
| v1.3.0 | 2026-09-02 | AD-OpenBase-Dev | OIDC 用户体系绑定策略：OidcIdentity 映射表 + 角色种子 + JIT 自动建号 + 复用路径补绑修复 + E2E 10/10                             |
| v1.4.0 | 2026-09-02 | AD-OpenBase-Dev | Keycloak profile：realm\_access/resource\_access 聚合 + access token 角色兜底；(issuer, sub) 复合唯一                              |
| v1.5.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 Keycloak realm 实配：官方 26.7.3 本地部署 + openbase realm 脚本化 + 真实授权码端到端验证                                            |
| v1.6.0 | 2026-09-02 | AD-OpenBase-Dev | 前端 OIDC 登录：后端 callback Accept 分流（浏览器 302 前端回调 + fragment 令牌 / API 保持 JSON）+ 登录页按钮 + OidcCallback 路由；真实浏览器全链路（5173→Keycloak→Dashboard）验证 |

***

## 1. 背景与目标

OpenBase 统一网关（8000）以 JWT 门禁 + 四 proxy 聚合下游服务。引入 OIDC 统一认证后：

1. OIDC 只在 OpenBase 网关单点集成（授权码流程、IdP 交互、令牌签发）。
2. 下游服务以"网关模式"消费网关签发 JWT。
3. 避免双身份源与重复 OIDC 客户端凭据。

## 2. 目标架构

```
浏览器/客户端（openbase-ui 5173）
    │  登录页"OIDC 统一登录"按钮 → GET /api/v1/auth/oidc/authorize
    ▼
OpenBase 统一网关（8000）
    │  授权码 → IdP（Keycloak 8080 / 本地 IdP 8090）
    │  claims 适配（§8）→ JIT 绑定（§7）→ 签发统一 JWT
    │  v1.6.0：浏览器（Accept: text/html）302 → 前端回调路由（fragment 令牌）；API（*/*）→ JSON
    ├──▶ OpenMemory (8020) / OpenLLM (8001) / OpenRAG (8010) / DPS (8030)（proxy 转发）
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
oidc_claim_role: str = "roles"
oidc_default_tenant: str = "default"
oidc_profile: str = "generic"                 # generic | keycloak
oidc_keycloak_client_roles: bool = True
oidc_frontend_redirect: str = "/auth/oidc/callback"  # v1.6.0：浏览器授权成功 302 前端回调（生产同源相对路径；开发跨源配前端源 URL，如 http://localhost:5173/auth/oidc/callback）
```

### 3.2 流程

1. `GET /api/v1/auth/oidc/authorize`：返回 IdP 授权 URL（含 state）。
2. 回调 `GET /api/v1/auth/oidc/callback`：code 换令牌 → JWKS RS256 验签 ID Token
   （issuer/aud/exp/at\_hash）→ profile 角色适配（§8）→ 用户体系绑定（§7）→ 签发统一 JWT。
3. **响应分流（v1.6.0）**：请求 `Accept` 含 `text/html`（浏览器导航）→ `302` 至
   `oidc_frontend_redirect`，令牌经 **URL fragment**（`#access_token=..&refresh_token=..`，
   不落服务端日志/URL 历史）；否则返回 JSON（脚本/API/既有测试契约不变）。
4. 后续请求与现有 JWT 门禁一致。

## 4. OpenMemory 侧集成（已实现）

`oidc_mode` 双模式（local 默认 / gateway）。切换：`OPENMEMORY_GATEWAY__OIDC_MODE=gateway`。

## 5. IdP 形态（已实现）

- 本地标准 IdP（8090，generic；`OIDC_IDP_PROFILE=keycloak` 切换 Keycloak 形状）。
- 真实 Keycloak 26.7.3（8080，realm `openbase`，见 §9 与 scripts/keycloak/）。
- 演示账号：oidc-admin / oidc-pass-2026（org\_admin）、oidc-user / user-pass-2026（user）。

## 6. 验收标准

| 项 | 验收 |
| ---- | ---- |
| 网关 OIDC 登录 | 授权码流程登录成功返回统一 JWT |
| 用户体系绑定 | 首次 JIT 建号、二次复用、user\_role 落库 |
| Keycloak profile | 嵌套角色聚合 + 兜底 + 伪角色过滤 |
| 前端 OIDC 登录（v1.6.0） | 登录页按钮 → IdP 授权 → 回前端回调路由存令牌 → Dashboard（真实浏览器） |
| API 兼容（v1.6.0） | 非浏览器 Accept 回调仍返回 JSON（既有脚本/测试契约不变） |

## 7. OIDC 用户体系绑定策略（已实现，v1.3.0+）

- OidcIdentity 映射表 `(issuer, sub)` 复合唯一；角色种子 viewer/user/org\_admin(+admin)。
- JIT 建号（随机密码、租户按 claims、角色白名单绑定）；复用幂等补绑（显式 commit）；DB 异常降级直签（ERROR+堆栈）。
- 白名单 `OIDC_ROLE_WHITELIST`（v1.5.0 用于归一化过滤，剔除 Keycloak 伪角色）。

## 8. Keycloak profile 适配（已实现，v1.4.0+）

角色聚合 `_roles_from_keycloak`（realm\_access/resource\_access/平铺）；ID Token 无角色时
access token 验签兜底（audience mapper 保证 aud 含 client id）；归一化白名单过滤后写回 claims。

## 9. 真实 Keycloak realm 实配（已实现，v1.5.0）

见 `scripts/keycloak/`：start-keycloak.ps1（26.7.3，8080）、provision\_realm.py（openbase realm
幂等配置）、start-gateway-keycloak.ps1（keycloak profile 网关）、assert\_binding.py（PG 落库断言）、README.md。

## 10. 前端 OIDC 登录（已实现，v1.6.0）

### 10.1 交互链路（真实浏览器验证）

```
openbase-ui /auth/login
  └─ 点击"OIDC 统一登录"（data-test=oidc-login）
       → GET /api/v1/auth/oidc/authorize（经 vite proxy /api → 8000）
       → 302 Keycloak 授权页（8080）
       → 登录成功 → 302 redirect_uri（8000 callback，浏览器 Accept: text/html）
       → 302 {oidc_frontend_redirect}#access_token=..&refresh_token=..&expires_in=..
       → openbase-ui /auth/oidc/callback（OidcCallback.vue，public 路由）
       → parseOidcHash 解析 fragment → tokenStore.set → 跳 redirect / /dashboard
       → 路由守卫 loadMe（/auth/me）→ 页面展示 OIDC 用户
```

### 10.2 改动

| 位置 | 内容 |
| ---- | ---- |
| `pages/Login.vue` | 账号表单下新增分割线 + "OIDC 统一登录"按钮；点击拉取 authorize URL 后整页跳转 |
| `pages/OidcCallback.vue` | 前端回调页（public）：解析 hash 令牌 → tokenStore 存储 → 跳目标页；缺令牌提示重试 |
| `core/router/index.ts` | 注册 `/auth/oidc/callback`（name oidc-callback，meta.public） |
| `core/api/auth.ts` | `parseOidcHash(hash)` 纯函数（可单测） |
| `modules/auth/oidc.py`（后端） | callback 响应按 Accept 分流：text/html → 302 fragment；*/* → JSON |
| `settings.py` | `oidc_frontend_redirect` 配置 |

### 10.3 安全说明

- 令牌经 URL fragment 传递：fragment 不随 HTTP 请求发送、不进服务端日志与 URL 历史（同源
  SPA 内读取）；演示环境采用，生产建议升级为一次性 code 交换（后端签发短期 code → 前端换取）。
- 回调页在授权码重放（无 state 校验于前端）场景由后端 state 校验兜底（无效 state 400）。

### 10.4 验证结果

- 后端单测：callback 302 分支（Accept: text/html → 302 + Location 前缀与 fragment 断言）4/4。
- 前端单测：oidc-auth.spec.ts（parseOidcHash 4 场景）39/39 全绿；`vue-tsc --noEmit` 0 错误。
- 真实浏览器全链路：5173 登录页 → 点击 OIDC 按钮 → Keycloak 登录（oidc-admin）→ 自动回跳
  `localhost:5173/dashboard`，顶栏显示绑定用户 `oidc-admin-e788`。
- 兼容：非浏览器 Accept 回调返回 JSON 不变（既有 E2E/脚本/单测契约零破坏）。

## 11. 风险与注意事项

- **fragment 令牌传递**为演示方案：生产建议后端签发一次性 code 交前端换取（避免令牌驻留前端 URL）。
- **开发/生产 redirect 差异**：开发（前后端分离）`oidc_frontend_redirect` 配前端源绝对 URL；
  生产同源（nginx /api → 后端、其余 → SPA）可保持相对路径。
- 角色仅进 access token 依赖 Keycloak 默认 mapper；租户依赖自定义 mapper。
- 共享 HS256 仅限内网；生产建议网关 RS256 + JWKS。
- 默认 generic + `oidc_enabled=false`，现有链路零影响。

## 12. 实施待办

| 待办 | 说明 |
| ---- | ---- |
| 生产密钥 | `OPENBASE_JWT_SECRET` 替换测试密钥 |
| 企业 Keycloak 实配 | 真实企业 realm（域名/Https）复跑 §9/§10 |
| 前端登出回跳 | OIDC 会话登出联动 IdP（back-channel/front-channel logout） |
| 一次性 code 交换 | 前端回调由 fragment 令牌升级为后端短期 code 交换 |
| 其他 IdP profile（可选） | Azure AD / Okta 等扩展 profile 解析器 |
