# 真实 Keycloak realm 实配（scripts/keycloak/，OB-AUTH-OIDC v1.5.0）

本地部署官方 Keycloak 26.7.3（真实 IdP），配置 `openbase` realm，OpenBase 网关以
`oidc_profile=keycloak` 对接，完成真实授权码端到端验证（含 PG 绑定落库）。

## 组件

| 文件 | 说明 |
| ---- | ---- |
| `start-keycloak.ps1` | 启动 Keycloak 26.7.3（Java 21，dev 模式，端口 8080，admin/admin） |
| `provision_realm.py` | Admin REST API 幂等配置 realm（roles/client/mapper/用户） |
| `assert_binding.py` | PG 落库断言（oidc_identity issuer=8080 映射 + user_role） |
| `start-gateway-keycloak.ps1` | 以 keycloak profile 启动 OpenBase 网关（进程级 env 覆写，不改 .env） |

## 快速开始

```powershell
# 1) 启动 Keycloak（首次约 30-60s 就绪）
powershell -ExecutionPolicy Bypass -File scripts/keycloak/start-keycloak.ps1

# 2) 配置 realm（幂等，可重复执行）
python scripts/keycloak/provision_realm.py

# 3) 启动 OpenBase 网关（keycloak profile）
powershell -ExecutionPolicy Bypass -File scripts/keycloak/start-gateway-keycloak.ps1

# 4) 浏览器走真实授权码：打开下述地址 → Keycloak 登录页 → oidc-admin/oidc-pass-2026
#    http://127.0.0.1:8000/api/v1/auth/oidc/authorize
#    登录后自动回跳 callback 返回统一 JWT（sub=绑定用户 int、role=org_admin、tenant_id=default）

# 5) 落库断言
python scripts/keycloak/assert_binding.py
```

## Realm 配置要点（provision_realm.py）

| 项 | 值 | 说明 |
| ---- | ---- | ---- |
| realm | `openbase` | issuer `http://127.0.0.1:8080/realms/openbase` |
| realm roles | `org_admin`/`user`/`viewer` | 对齐 OpenBase 角色白名单 |
| client | `openbase-gw` | confidential + 授权码；secret `openbase-kc-secret-20260902` |
| audience mapper | `openbase-audience` | access token aud 含 client id（默认仅 `account`） |
| tenant mapper | `openbase-tenant-id` | 用户属性 `tenant_id` → token claim（id/access/userinfo） |
| 用户 | `oidc-admin`→org_admin、`oidc-user`→user | 密码见 provision；tenant_id=default |

## 关键适配事实（真实 Keycloak 与本地 IdP 的差异）

1. **角色位置**：realm 角色在 `realm_access.roles`（嵌套）；默认仅进 access token（官方默认 mapper），
   ID Token 不含 —— OpenBase 以 access token 验签兜底聚合。
2. **伪角色污染**：realm_access 含 `default-roles-openbase`/`offline_access`/`uma_authorization` 等默认伪角色，
   OpenBase 按白名单过滤（`OIDC_ROLE_WHITELIST`）后再映射统一 JWT role。
3. **aud 默认 `account`**：需 client audience mapper 使 access token aud 含 `openbase-gw`，
   否则网关 `verify_access_token` 的 audience 校验失败（角色兜底降级）。
4. **at_hash**：Keycloak ID Token 携带 `at_hash`，网关验签须传入 access_token 比对（python-jose 默认校验）。
5. **首次登录 VERIFY_PROFILE**：新用户默认触发资料完善页，打断授权码流程；provision 预置
   firstName/lastName/emailVerified 并清空 requiredActions 规避。
6. **Admin API PUT 为全量替换**：更新用户须带全字段（email/enabled/attributes 等），否则丢失。

## 回切本地 IdP（8090/generic）

关闭当前网关后按既有方式启动（.env 默认指向本地 IdP 8090、generic profile）即恢复；
本地 IdP 与真实 Keycloak 为两套互斥演示环境。
