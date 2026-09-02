# OpenBase 运维手册 - v1.1.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 配套代码版本 | v1.4.5+（含 OIDC/密钥管理系列 v1.7.0 能力） |
| 文档版本 | v1.1.0 |
| 状态 | [Review] |
| 作者 | OP-OpenBase-Dev |
| 创建日期 | 2026-09-02 |
| 存放 | doc/operation/ |

---

## 1. 服务清单

| 服务 | 端口 | 启动命令 | 健康检查 |
|------|:---:|----------|----------|
| OpenBase 后端 | 8000 | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | 登录 API / /openapi.json |
| DPS 后端 | 8030 | `$env:API_PORT='8030'; $env:SQLITE_FALLBACK='true'; python -m uvicorn rest_api.app:app --app-dir src` | /health/liveness（经 dps-proxy） |
| OpenBase 前端 | 5173 | `npm run dev`（openbase-ui） | GET / |
| Keycloak（OIDC 联调，可选） | 8080 | `powershell -File scripts/keycloak/start-keycloak.ps1` | /health（见 OB-AUTH-OIDC） |

## 2. 关键配置（settings / .env）

| 配置 | 默认值 | 说明 |
|------|--------|------|
| env | development | 运行环境：development \| production（`OPENBASE_ENV`） |
| jwt_secret | ""（无内置弱默认） | JWT 共享签名密钥；production 必须 ≥32 字符强随机且非弱值（详见 §3） |
| jwt_secret_previous | "" | 密钥轮换宽限旧密钥（仅验签） |
| jwt_algorithm | HS256 | 不变 |
| dps_upstream_base | http://127.0.0.1:8030 | DPS 上游地址 |
| dps_upstream_timeout | 20.0 | 上游超时（秒） |
| dps_default_org_id / dps_default_tenant_id | "" | 身份头兜底值（JWT 缺字段时） |
| dps_org_map / dps_tenant_map | "" | 组织/租户映射表（JSON，OpenBase 值 → DPS 值） |

## 3. JWT 共享密钥管理（v1.1.0 新增）

OpenBase 网关 JWT（HS256）为共享签名密钥：OpenBase auth 签发，OpenMemory/OpenLLM 等下游
同密钥验签。密钥管理完整说明见设计文档 **OB-AUTH-JWTKEY-v1.0.0**（doc/design/OpenBase-JWT密钥管理说明-v1.0.0.md）。

### 3.1 配置约束

- 无内置弱默认：`jwt_secret` 默认空；未配置/过弱时**签发直接失败（fail-closed）**。
- 生产强制：`OPENBASE_ENV=production` 时 `OPENBASE_JWT_SECRET` 必须为 ≥32 字符强随机值，
  且不得为已知弱值（空 / change-me-in-production / test-jwt-secret-for-v680），否则**启动失败**。
- 开发环境弱值仅告警，但 `.env` 仍建议使用生成的随机密钥。

### 3.2 生成与校验

```powershell
# 生成新密钥（URL-safe 64 字符）并打印配置指引
python scripts/gen_jwt_secret.py

# 校验当前 .env 密钥强度（exit 0/1）
python scripts/gen_jwt_secret.py --check
```

### 3.3 共享密钥同步范围

| 消费方 | 配置键 | 说明 |
|--------|--------|------|
| OpenBase | `OPENBASE_JWT_SECRET`（.env） | 签发/验签 |
| OpenMemory | `OPENMEMORY_GATEWAY__JWT_SECRET`（OpenMemory .env） | 网关验签（同源密钥） |
| OpenLLM/OpenRAG/DPS proxy | 经 OpenBase 网关转发 | 消费网关签发 JWT，无需单独配置 |

### 3.4 密钥轮换（零中断）

```powershell
# 1) 生成新密钥
$new = (python -c "import secrets;print(secrets.token_urlsafe(48))")

# 2) OpenBase .env：新密钥作为当前签发、旧密钥保留为 previous（验签宽限）
#    OPENBASE_JWT_SECRET=$new
#    OPENBASE_JWT_SECRET_PREVIOUS=<旧密钥>

# 3) 重启 OpenBase 网关（过渡期新旧 token 均有效，旧会话不登出）

# 4) 同步下游：OpenMemory .env 的 OPENMEMORY_GATEWAY__JWT_SECRET=$new 并重启

# 5) 过渡期结束：移除 OPENBASE_JWT_SECRET_PREVIOUS 并重启（旧 token 失效）
```

## 4. 常见故障与排障

| 故障 | 现象 | 排障 |
|------|------|------|
| 生产启动失败 | 启动报 `OPENBASE_JWT_SECRET 必须为强随机密钥`（ValidationError） | 用 gen_jwt_secret.py 生成强密钥后注入（§3.2） |
| 登录签发失败 | 登录接口 500 `JWT 签发密钥未配置或过弱` | `.env` 缺 `OPENBASE_JWT_SECRET` 或过短；配置强密钥后重启（§3.1） |
| 下游 401（轮换后） | OpenMemory 等验签失败 | 共享密钥未同步（§3.3）或未重启消费方（§3.4 步骤 4） |
| DPS 上游不可达 | dps-proxy 返回 502 SYS_502 "unreachable" | 检查 DPS 8030 是否启动 |
| 401 未认证 | dps-proxy 全部端点 401 | 检查 OpenBase JWT 是否过期（前端重新登录） |
| 身份头缺 org/tenant | 上游 403（组织/租户无效） | 检查 JWT payload 是否含 org_id/tenant_id；配置 dps_default_* / 映射表 |
| 前端画像页 502 | 画像列表/详情错误提示 502 | DPS 未就绪（H 类）；DPS 就绪后刷新 |

## 5. 日志与监控

| 项 | 说明 |
|----|------|
| 日志 | 结构化日志（logging + extra）；dps_proxy logger "openbase.dps_proxy"（path/upstream_status/duration_ms） |
| 指标 | observability 模块（http 指标挂 path 标签） |
| 审计 | proxy 转发关键操作记录审计日志 |

## 6. 告警（Pro 部署时）

| 级别 | 规则 | 通道 |
|------|------|------|
| P0 | dps-proxy 错误率 >1% 或健康检查失败 | 15 分钟电话 |
| P1 | 上游不可达 502 持续 >5 分钟 | 1 小时 IM |
| P2 | 画像接口 P99 超基线 50% | 24 小时 IM |

## 7. 版本升级指引

| 步骤 | 操作 |
|------|------|
| 1 | `git pull origin main` + `git checkout <目标版本 tag>` |
| 2 | 核对 .devflow/project-config.json 版本号 |
| 3 | 重启服务（后端 + 前端 build；涉及密钥轮换按 §3.4 顺序执行） |
| 4 | 上线验证（对照上线检查报告清单；密钥变更后执行 `gen_jwt_secret.py --check`） |

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-01 | OP-OpenBase-Dev | 初始创建：服务清单/配置/故障排障（含 M4）/日志监控/告警/升级指引 |
| v1.1.0 | 2026-09-02 | OP-OpenBase-Dev | 新增 §3 JWT 共享密钥管理（无弱默认/生产强校验/生成工具/同步范围/零中断轮换）；配置表与故障/升级指引同步更新（对应 OB-AUTH-JWTKEY-v1.0.0、OB-AUTH-OIDC-v1.7.0） |
