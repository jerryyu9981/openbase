# OpenBase-OIDC网关统一认证集成说明-v1.7.0

| 属性   | 值                                                                         |
| ---- | ------------------------------------------------------------------------- |
| 文档编号 | OB-AUTH-OIDC-v1.7.0                                                       |
| 版本   | v1.7.0                                                                    |
| 状态   | \[Review]                                                                 |
| 日期   | 2026-09-02                                                                |
| 作者   | AD-OpenBase-Dev                                                           |
| 版本主题 | 生产密钥替换：JWT 共享密钥无弱默认 + 生产强校验（fail-fast）+ 双密钥轮换宽限 + 生成工具（详见 JWT 密钥管理说明 v1.0.0）               |
| 适用范围 | OpenBase（8000）+ openbase-ui（5173）+ Keycloak（8080）+ 本地 IdP（8090）+ OpenMemory/OpenLLM/OpenRAG/DPS |

> 本文档定义 OpenBase 统一网关 OIDC 认证集成方案与各下游服务消费方式。授权码（§3）、OpenMemory 网关模式（§4）、IdP（§5）、用户体系绑定（§7）、Keycloak profile（§8）、真实 Keycloak realm（§9）、前端 OIDC 登录（§10）均已实现验证；JWT 共享密钥生产化管理（§11）详见独立文档 OB-AUTH-JWTKEY-v1.0.0。

## 修订历史

| 版本     | 日期         | 修改人             | 修改内容                                                                                                           |
| ------ | ---------- | --------------- | -------------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：OIDC 网关统一认证架构、OpenMemory gateway 模式落地、OpenBase 网关 OIDC 集成设计草案                                             |
| v1.1.0 | 2026-09-02 | AD-OpenBase-Dev | OpenBase 网关 OIDC 授权码流程实现落地 + mock IdP 端到端验证 + OIDC sub 兼容修复                                              |
| v1.2.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 IdP 接入：本地标准 OIDC IdP（8090）落地 + 13/13 端到端验证 + 统一 JWT 联通 OpenMemory                                   |
| v1.3.0 | 2026-09-02 | AD-OpenBase-Dev | OIDC 用户体系绑定策略：OidcIdentity 映射表 + 角色种子 + JIT 自动建号 + 复用路径补绑修复 + E2E 10/10                             |
| v1.4.0 | 2026-09-02 | AD-OpenBase-Dev | Keycloak profile：realm\_access/resource\_access 聚合 + access token 角色兜底；(issuer, sub) 复合唯一                              |
| v1.5.0 | 2026-09-02 | AD-OpenBase-Dev | 真实 Keycloak realm 实配：官方 26.7.3 本地部署 + openbase realm 脚本化 + 真实授权码端到端验证                                            |
| v1.6.0 | 2026-09-02 | AD-OpenBase-Dev | 前端 OIDC 登录：callback Accept 分流 + 登录页按钮 + OidcCallback 路由；真实浏览器全链路验证                                             |
| v1.7.0 | 2026-09-02 | AD-OpenBase-Dev | 生产密钥替换：JWT 共享密钥无弱默认（settings env 校验 fail-fast）+ 双密钥轮换宽限（jwt\_secret\_previous）+ gen\_jwt\_secret 工具 + 本地 .env 真实替换 |

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
OpenBase 统一网关（8000）〔JWT 共享密钥：见 OB-AUTH-JWTKEY-v1.0.0〕
    │  授权码 → IdP（Keycloak 8080 / 本地 IdP 8090）
    │  claims 适配（§8）→ JIT 绑定（§7）→ 签发统一 JWT
    │  浏览器（Accept: text/html）302 → 前端回调路由（fragment 令牌）；API（*/*）→ JSON
    ├──▶ OpenMemory (8020) / OpenLLM (8001) / OpenRAG (8010) / DPS (8030)
```

## 3. OpenBase 网关 OIDC 集成（已实现）

### 3.1 配置项（openbase/settings.py）

```python
env: str = "development"              # development | production（v1.7.0）
jwt_secret: str = ""                  # 无弱默认；production 强校验（≥32 字符、非弱值）
jwt_secret_previous: str = ""         # 轮换宽限旧密钥（仅验签）
jwt_algorithm: str = "HS256"
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
oidc_frontend_redirect: str = "/auth/oidc/callback"
```

### 3.2 流程

1. `GET /api/v1/auth/oidc/authorize`：返回 IdP 授权 URL（含 state）。
2. 回调 `GET /api/v1/auth/oidc/callback`：code 换令牌 → JWKS RS256 验签 ID Token
   （issuer/aud/exp/at\_hash）→ profile 角色适配（§8）→ 用户体系绑定（§7）→ 签发统一 JWT。
3. **响应分流（v1.6.0）**：请求 `Accept` 含 `text/html` → `302` 至 `oidc_frontend_redirect`
   （fragment 携带令牌）；否则返回 JSON（脚本/API 契约不变）。
4. 后续请求与现有 JWT 门禁一致（签发/验签密钥管理见 §11）。

## 4. OpenMemory 侧集成（已实现）

`oidc_mode` 双模式（local 默认 / gateway）；`OPENMEMORY_GATEWAY__JWT_SECRET` 与网关共享同源密钥。

## 5. IdP 形态（已实现）

- 本地标准 IdP（8090，generic；`OIDC_IDP_PROFILE=keycloak` 切 Keycloak 形状）。
- 真实 Keycloak 26.7.3（8080，realm openbase，见 §9 与 scripts/keycloak/）。
- 演示账号：oidc-admin / oidc-pass-2026（org\_admin）、oidc-user / user-pass-2026（user）。

## 6. 验收标准

| 项 | 验收 |
| ---- | ---- |
| 网关 OIDC 登录 | 授权码流程登录成功返回统一 JWT |
| 用户体系绑定 | JIT 建号 / 复用 / user\_role 落库 |
| Keycloak profile | 嵌套角色聚合 + 兜底 + 伪角色过滤 |
| 前端 OIDC 登录 | 按钮 → IdP → 前端回调 → Dashboard（真实浏览器） |
| 生产密钥（v1.7.0） | production 弱/缺密钥启动失败；双密钥轮换旧 token 宽限；本地新密钥链路正常 |

## 7. OIDC 用户体系绑定策略（已实现，v1.3.0+）

OidcIdentity `(issuer, sub)` 复合唯一；角色种子 + 白名单过滤（`OIDC_ROLE_WHITELIST`）；
JIT 建号 / 复用幂等补绑 / DB 异常降级直签（ERROR+堆栈）。

## 8. Keycloak profile 适配（已实现，v1.4.0+）

角色聚合 `_roles_from_keycloak` + access token 兜底（audience mapper）+ 归一化白名单过滤。

## 9. 真实 Keycloak realm 实配（已实现，v1.5.0）

见 `scripts/keycloak/`：start-keycloak.ps1、provision\_realm.py、start-gateway-keycloak.ps1、
assert\_binding.py、README.md。

## 10. 前端 OIDC 登录（已实现，v1.6.0）

登录页"OIDC 统一登录"按钮 → authorize → IdP → 后端 callback（Accept 分流 302）→
`/auth/oidc/callback`（OidcCallback.vue 解析 fragment 存 token）→ Dashboard。

## 11. JWT 共享密钥生产化管理（已实现，v1.7.0）

详见独立文档 **[OpenBase-JWT密钥管理说明-v1.0.0](OpenBase-JWT密钥管理说明-v1.0.0.md)**：

- settings：`env` 字段 + `jwt_secret` 无弱默认 + `jwt_secret_previous`；production 弱/缺密钥启动失败（fail-fast）。
- jwt：签发恒用当前密钥（fail-closed）；验签遍历当前+旧密钥（轮换宽限）。
- 工具 `scripts/gen_jwt_secret.py`（生成 + `--check` 校验）。
- 本地 `.env` 已替换为生成的强随机密钥；OpenMemory 侧 `.env` 已同步同一值并重启验证联通（200）。

## 12. 风险与注意事项

- fragment 令牌传递为演示方案（生产建议一次性 code 交换）。
- Keycloak 角色/租户依赖 mapper 配置；共享 HS256 仅限内网，长期建议 RS256+JWKS。
- 默认 generic + `oidc_enabled=false`，现有链路零影响。

## 13. 实施待办

| 待办 | 说明 |
| ---- | ---- |
| 企业 Keycloak 实配 | 真实企业 realm 复跑 §9/§10 |
| 前端登出回跳 | OIDC 会话登出联动 IdP |
| 一次性 code 交换 | 前端回调由 fragment 令牌升级为后端短期 code 交换 |
| RS256+JWKS（可选演进） | 网关签发 RS256 + JWKS，消除共享密钥分发 |
| 其他 IdP profile（可选） | Azure AD / Okta 等扩展 profile 解析器 |
