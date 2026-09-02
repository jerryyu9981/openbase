# OpenBase-OIDC网关统一认证集成说明-v1.1.0

| 属性   | 值                                                                         |
| ---- | ------------------------------------------------------------------------- |
| 文档编号 | OB-AUTH-OIDC-v1.1.0                                                       |
| 版本   | v1.1.0                                                                    |
| 状态   | \[Review]                                                                 |
| 日期   | 2026-09-02                                                                |
| 作者   | AD-OpenBase-Dev                                                           |
| 版本主题 | OIDC 统一认证：OpenBase 网关授权码流程已实现并端到端验证；OpenMemory gateway 模式已落地                 |
| 适用范围 | OpenBase（8000）+ OpenMemory（8020）+ OpenLLM（8001）+ OpenRAG（8010）+ DPS（8030） |

> 本文档定义 OpenBase 统一网关 OIDC 认证集成方案与各下游服务的消费方式，避免各服务重复直连 IdP。OpenBase 网关侧授权码流程（§3）与 OpenMemory 侧网关模式（§4）均已实现并验证。

## 修订历史

| 版本     | 日期         | 修改人             | 修改内容                                                               |
| ------ | ---------- | --------------- | ------------------------------------------------------------------ |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：OIDC 网关统一认证架构、OpenMemory gateway 模式落地、OpenBase 网关 OIDC 集成设计草案 |
| v1.1.0 | 2026-09-02 | AD-OpenBase-Dev | OpenBase 网关 OIDC 授权码流程实现落地（settings/oidc.py/白名单）+ mock IdP 端到端验证 + get\_current\_user/MeResponse OIDC sub 兼容修复 |

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
    │  ① OIDC 登录 → 换取 IdP ID Token/访问令牌
    │  ② 签发统一 JWT（HS256 共享密钥，claims: sub/role/tenant_id/org_id）
    │  ③ proxy 转发下游，携带 JWT（Authorization: Bearer）+ X-API-Key + 身份头
    ├──▶ OpenMemory (8020)：oidc_mode=gateway（本地密钥双保险 或 仅解析 claims）
    ├──▶ OpenLLM   (8001)：JWT 通道（get_current_active_user 已支持共享密钥验签）
    ├──▶ OpenRAG   (8010)：X-API-Key 透传（网关代签，OIDC 不影响）
    └──▶ DPS      (8030)：身份头注入（X-User-ID/X-Org-ID，OIDC claims 映射）
```

原则：

- **单点 IdP 交互**：仅 OpenBase 网关持有 OIDC client\_id/secret 与 discovery 配置。

- **统一令牌语义**：网关签发 HS256 JWT（与现共享密钥体系兼容，`test-jwt-secret-for-v680` 为测试密钥，生产替换）。

- **租户/角色传递**：OIDC claims（sub/org/role）由网关映射进 JWT（sub/tenant\_id/role），下游按既有解析链路消费。

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
oidc_claim_role: str = "roles"      # 角色 claim 名（IdP 特定，可配置）
oidc_default_tenant: str = "default"  # 未映射租户时的默认值
```

### 3.2 流程（已实现）

1. `GET /api/v1/auth/oidc/authorize`：返回 IdP 授权 URL（含 state；前端跳转）。
2. IdP 回调 `GET /api/v1/auth/oidc/callback`：code 换 token（token\_endpoint，表单提交 client 凭据）、JWKS 公钥验签 ID Token（issuer/aud/exp）。
3. 网关映射 claims（sub/username/tenant\_id/org\_id/role，role 取 `oidc_claim_role`）→ 签发统一 JWT（复用 `create_access_token`）。
4. 后续请求与现有 JWT 门禁完全一致（proxy 转发、身份头注入不变）。

**实现位置**：`openbase/modules/auth/oidc.py`（OIDCClient + authorize/callback 路由，extra\_routers 挂载 `/api/v1/auth/oidc/*`）；`AuthMiddleware` 白名单放行 OIDC 端点；`oidc_enabled=false` 时端点返回 404（路由保留、客户端禁用）。

### 3.3 与现有认证的关系

- `oidc_enabled=false`（默认）：现状不变（本地账号登录签发 JWT）；OIDC 端点 404。
- `oidc_enabled=true`：OIDC 通道启用，签发的统一 JWT 与本地账号登录同语义（sub/username/tenant\_id/org\_id/role/type=access）。
- 兼容修复：`get_current_user` 与 `MeResponse.id` 支持 OIDC 非数字 sub（保留字符串主体，避免 ValueError/序列化失败）。

### 3.4 实施与验证结果（v1.1.0 回填）

- `tests/test_oidc_gateway.py` 3 用例全绿（mock IdP：discovery/token/jwks RS256）：禁用 404、authorize 返回 URL、授权码全流程（callback → 统一 JWT claims 断言 → `/api/v1/auth/me` 200）。
- auth 相关回归（test\_ui\_increments/test\_three\_modules/test\_rbac\_deps）27 用例无破坏。
- 修复过程中发现的真实缺陷：`get_current_user` 对 OIDC 字符串 sub 抛 ValueError（int 转换）、`MeResponse.id` 仅 int 无法序列化——均已修复。

## 4. OpenMemory 侧集成（已实现，OB-AUTH-OIDC §4）

OpenMemory 网关中间件已支持 `oidc_mode` 双模式（`src/openmemory/gateway/gateway.py`）：

| oidc\_mode  | 行为                                                          | 适用                     |
| ----------- | ----------------------------------------------------------- | ---------------------- |
| `local`（默认） | 本地 HS256 共享密钥校验（现状不变）                                       | 当前对接（网关本地签发）           |
| `gateway`   | 外部 OIDC 网关已验签：配本地密钥则双保险验签；无密钥则仅解析 claims（保留 exp/nbf/iat 校验） | OpenBase 网关 OIDC 就绪后切换 |

**切换方式**：`OPENMEMORY_GATEWAY__OIDC_MODE=gateway`（.env，默认 local）。共享密钥（`OPENMEMORY_GATEWAY__JWT_SECRET`）与网关一致时启用双保险；不想共享密钥可置空，信任网关仅解析 claims。

**验证**（tests/unit/test\_gateway.py TestOidcMode，9 用例全绿）：local 正确/错误密钥、gateway 无密钥解析 claims、gateway 过期拒绝（verify\_exp 显式保留）、gateway 双保险。

**已核实的相关能力**（OIDC 讨论轮核查）：

- `Authenticator`（gateway/auth.py）gateway 模式与 APIGateway 一致语义（备选认证器，未装配）。

- `OIDCClient`（security/oidc.py）远端 JWKS RS256 模式仅用于 OpenMemory 独立对外暴露场景，统一入口下不启用。

- 租户解析 `X-Tenant-ID > JWT claim > default` 已具备；RBAC 角色绑定 `org_admin/user`（.env USER\_ROLES）供权限判定。

## 5. 验收标准

| 项                     | 验收                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------- |
| 网关 OIDC 登录            | 经 IdP 授权码流程登录成功，返回统一 JWT                                                            |
| 网关本地登录回归              | `oidc_enabled=false` 时本地账号登录行为不变                                                    |
| OpenMemory gateway 模式 | `OPENMEMORY_GATEWAY__OIDC_MODE=gateway` 后，网关签发 JWT 访问 8020 业务端点 200；过期/伪造 token 401 |
| 租户/角色透传               | OIDC 用户的 tenant\_id/role 正确映射，RBAC 判定生效                                             |
| 各服务无重复 IdP 交互         | 仅网关持有 OIDC 凭据；下游无 OIDC discovery 调用                                                 |

## 6. 验证方法（v1.1.0 实测回填）

1. OpenMemory gateway 模式：`.env` 切 `OIDC_MODE=gateway` → 重启 8020 → 网关/本地签发的 JWT 访问 `GET /api/v1/decay/config` 200；过期 JWT 401（TestOidcMode 9 用例已覆盖，运行时可复验）。
2. 单测：`python -m pytest tests/unit/test_gateway.py`（OpenMemory 9 用例）；`python -m pytest tests/test_oidc_gateway.py`（OpenBase 3 用例）。
3. 端到端：OpenBase mock IdP（tests/test\_oidc\_gateway.py 内置，uvicorn 9010）已跑通 authorize → callback → 统一 JWT → `/auth/me` 200；真实 IdP 接入只需配置 discovery/client\_id/secret/redirect 后复跑同一链路。

## 7. 风险与注意事项

- **密钥管理**：共享密钥（HS256）仅限内网测试；生产建议网关 OIDC 签发 RS256 并下发 JWKS，下游验签公钥（或保持共享密钥双保险）。

- **claims 映射**：OIDC sub 与现有用户体系（UserService）的绑定需明确（首次登录自动建号 or 绑定已有账号）。

- **令牌时效**：网关 JWT 过期时间（jwt\_expire\_seconds=7200）与 IdP 会话一致或更短，避免下游验签通过但 IdP 已登出。

- **防伪造**：gateway 模式无本地密钥时信任网关，OpenMemory 不得直接暴露公网（须经 OpenBase 网关）；若独立暴露需启用 OIDCClient 远端模式。

- **向后兼容**：默认 oidc\_mode=local 与 oidc\_enabled=false，现有链路零影响。

## 8. 实施待办

| 待办 | 说明 |
| ---- | ---- |
| 真实 IdP 接入 | 配置 `OPENBASE_OIDC_DISCOVERY_URL/CLIENT_ID/CLIENT_SECRET/REDIRECT_URI`（.env）后按 §6.3 复跑端到端；对接真实 IdP 的 claims（tenant/org/role）映射 |
| OIDC 用户体系绑定 | §7.2：首次登录自动建号 or 绑定已有账号（当前统一 JWT 以 IdP sub 为主体，RBAC 角色由 IdP claims 映射） |
| 生产密钥 | `OPENBASE_JWT_SECRET` 替换测试密钥；共享密钥 HS256 仅限内网，生产建议网关签发 RS256 + JWKS |
| 前端登录入口 | openbase-ui 登录页增加"OIDC 登录"按钮（跳转 authorize，callback 后存 JWT） |

