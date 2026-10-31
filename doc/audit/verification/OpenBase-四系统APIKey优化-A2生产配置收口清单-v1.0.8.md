# OpenBase 四系统 API Key 与授权优化 —— A2 生产配置收口清单

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0.8 |
| 文档状态 | [Review] |
| 适用环境 | 生产环境（Pro）/ 准生产（Pre-Pro） |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.20.0.md`（§10.7~§10.23） |
| 关联清单 | `doc/audit/verification/OpenBase-四系统APIKey优化-A1生产验收清单-v1.0.1.md`（A1-01/02/04/11/12 为本清单的执行验收） |
| 适用对象 | OpenBase（控制面，唯一事实源）/ OpenLLM / OpenRAG / OpenMemory / DPS（下游消费方） |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 首版：将五仓「API Key 与授权」相关配置收敛为单一部署基线，给出 OpenBase 控制面基线矩阵、四仓镜像矩阵、11 项启动门禁、密钥管理、漂移自检与签核口径 |
| v1.0.1 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.13.0（§10.16）：ABAC 除 `OPENBASE_ABAC_POLICIES` 配置基线外，新增运行期策略表与 `/api/v1/auth/access/policies` 写端点（判定为两者合并，缺省零行为变化）；关联方案版本号更新 |
| v1.0.2 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.14.0（§10.17 OIDC P1 安全硬化）：§2.5 新增 `OPENBASE_OIDC_STATE_TTL_SECONDS` / `OPENBASE_OIDC_PKCE_ENABLED` / `OPENBASE_OIDC_SIGNING_ALGORITHMS` 三项基线；§4 启动门禁由 11 项增至 12 项（新增 OIDC 硬化门禁）；§6.3 增加算法白名单负向样例；关联方案版本号更新 |
| v1.0.3 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.15.0（§10.18 多 Provider 登录路由）：`OPENBASE_IDP_PROVIDERS` 行补充登录路由接入说明（`authorize?provider=`、state 记录 Provider、未知 Provider 400），关联方案版本号更新 |
| v1.0.4 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.16.0（§10.19 IdP 登出联动）：§2.5 新增「登出联动」行（强校验与 IdP `end_session_endpoint` 前置条件），关联方案版本号更新 |
| v1.0.5 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.17.0（§10.20 token 端点认证方式扩展）：§2.5 新增 `OPENBASE_OIDC_TOKEN_AUTH_METHOD` 与 mTLS 证书三项基线；§4 启动门禁由 12 项增至 13 项（新增 token 认证门禁）；§6.3 增加 mTLS 缺证书路径负向样例；关联方案版本号更新 |
| v1.0.6 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.18.0（§10.21 private_key_jwt 客户端断言）：§2.5 新增 `OPENBASE_OIDC_CLIENT_PRIVATE_KEY_PATH` / `_ASSERTION_KID` 基线，`TOKEN_AUTH_METHOD` 可选值扩至四项；§4 门禁 #6 增补 private_key_jwt 缺私钥条件（总数仍 13 项）；§6.3 将原「private_key_jwt 取值非法」样例替换为「缺私钥路径拒启」并新增「未实现方式拒启」样例；关联方案版本号更新 |
| v1.0.7 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.19.0（§10.22 tls_client_auth 客户端认证）：§2.5 新增 `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` 基线，`TOKEN_AUTH_METHOD` 可选值扩至五项，证书项适用方式扩为 `mtls` / `tls_client_auth`；§4 门禁 #6 增补证书非 PEM 与 subject 不匹配条件（总数仍 13 项）；§6.3 新增 subject 不匹配/非 PEM 负向样例；关联方案版本号更新 |
| v1.0.8 | 2026-10-31 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.20.0（§10.23 OIDC 残余闭合 P1 C-01~C-05）：§2.5 新增 `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS` / `_URI` / `_IP` / `_EMAIL` 与 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM` 基线（全部缺省零行为变化）；§4 门禁 #6 增补 SAN 期望值不匹配与断言算法/私钥类型错配条件（总数仍 13 项）；§6.3 新增 SAN 不匹配、断言算法与私钥类型错配负向样例；关联方案与残余项方案版本号更新 |

---

## 1. 目的与范围

**目的**：回答上线前的三个问题——**必须配什么**、**漏配会怎样**、**如何证明配对了**，把散落在 `settings.py`、各仓 `config.py` 与环境变量中的授权配置收敛成一份可对照的基线。

**收口原则**

1. **单一事实源**：策略值（令牌算法/有效期、租户绑定、主体降级、审计留存、ABAC、IdP）只在 OpenBase 配置；四仓只配置「如何消费 OpenBase」（JWKS 地址、吊销地址、服务 Key、身份权威开关）。
2. **缺配即拒启**：安全相关配置一律 fail-fast，不允许「运行时才降级」；本清单第 5 节逐条列出启动门禁。
3. **秘密不落明文配置**：私钥用只读挂载文件，服务 Key 由密钥管理系统注入，MCP 静态 Key 只存摘要或宿主文件。
4. **可核对**：每项配置有唯一校验落点（`文件:行号`），可逐条复核，不依赖口头约定。

**不在本清单范围**：SM2 真实签名原语、IdP 生产联调、集中审计平台、信创/灾备基础设施、终端宿主项（TPM/安全启动/本地落盘加密/远程擦除）——与 A1 清单边界一致。

---

## 2. OpenBase 控制面基线矩阵

> 变量名 = `OPENBASE_` + 字段名大写；`env` 指 `OPENBASE_ENV`。行号对应当前分支源码。

### 2.1 运行环境、数据库与 Redis

| 变量 | 默认 | 生产基线 | 缺失/违规后果 | 校验落点 |
|---|---|---|---|---|
| `OPENBASE_ENV` | `development` | 必须 `production` | 非 production 时大量生产门禁不生效（弱密钥/明文 MCP Key 可通过） | `settings.py:300-301` |
| `OPENBASE_DB_URL` | 解析 `POSTGRES_URL` 或默认 | 生产 PG 连接串；审计链写入必须**同一 PG 实例** | 多实例指向不同库 → 审计链分叉（v1.10.0 已限同实例） | `settings.py:266-271` |
| `OPENBASE_DB_SCHEMA` | `openbase` | 保持 `openbase`（与迁移/DDL 前缀一致） | 改 schema 后既有 DDL 与权限种子指向错位 | `settings.py:317-318` |
| `OPENBASE_REDIS_URL` | 解析 `REDIS_URL` 或默认 | 生产必配（离线宽限时间标记、吊销缓存清理依赖） | 不可用时视为未命中直读 DB，性能与宽限判定退化 | `settings.py:280-281` |

### 2.2 令牌、签名与 JWKS

| 变量 | 默认 | 生产基线 | 缺失/违规后果 | 校验落点 |
|---|---|---|---|---|
| `OPENBASE_JWT_REQUIRE_RS256` | `false` | **`true`** | 缺 RS256 私钥/kid 仍可启动 → 签发退回 HS256（下游无法只验公钥） | `settings.py:600-634` |
| `OPENBASE_JWT_RSA_PRIVATE_KEY_PATH` | 空 | PEM **只读挂载**（0600）；禁止内联私钥 | 置 `require_rs256=true` 而缺失 → **拒绝启动** | `settings.py:600-634` |
| `OPENBASE_JWT_SIGNING_KID` | 空 | 与新签发令牌 `kid` 一致；`JWKS` 以该 kid 发布 | 配私钥但缺 kid → 拒绝启动；换钥时新旧 kid 需并存过渡 | `settings.py:600-634` |
| `OPENBASE_JWT_ALGORITHM` | `HS256` | `RS256`（须在签名算法注册表内且可用） | 未知算法或不可用算法（含 `SM2` 预留）→ 拒绝启动 | `settings.py:637-649` |
| `OPENBASE_JWT_ISSUER` | `openbase` | `openbase`（与四仓期望值一致） | 四仓 `iss` 校验失败 → 全部 401 | `settings.py:338` |
| `OPENBASE_JWT_AUDIENCE` | `openbase-api` | `openbase-api` | 同上 | `settings.py:339` |
| `OPENBASE_JWT_JWKS_PUBLIC_KEYS` | 空 | 换钥过渡期登记旧/对端 kid（JSON `{"kid":"<PEM>"}` 或 `"@<公钥文件>"`） | JSON 非法 → 拒绝启动；不登记则旧 kid 令牌无法验签 | `settings.py:340-342, 631` |
| `OPENBASE_JWT_EXPIRE_SECONDS` | `7200` | ≤7200（边缘终端建议更短） | 过长放大吊销前窗口 | `settings.py:329` |
| `OPENBASE_JWT_REFRESH_EXPIRE_SECONDS` | `604800` | 按安全基线收窄 | 同上 | `settings.py:330` |
| `OPENBASE_JWT_SECRET` | 空 | production 强随机 ≥32 字符（`scripts/gen_jwt_secret.py`） | 弱/占位/缺失 → **拒绝启动** | `settings.py:575-597` |
| `OPENBASE_JWT_SECRET_PREVIOUS` | 空 | 仅轮换窗口填写，仅参与验签 | 轮换期未填 → 旧令牌立即失效（可用但会打断会话） | `settings.py:327` |
| `OPENBASE_JWT_REVOCATIONS_PAGE_LIMIT` | `500` | 正整数（下游增量拉取单页上限） | 非正 → 拒绝启动 | `settings.py:633` |

### 2.3 登录租户、主体状态与降级策略

| 变量 | 默认 | 生产基线 | 缺失/违规后果 | 校验落点 |
|---|---|---|---|---|
| `OPENBASE_REQUIRE_TENANT_ON_LOGIN` | `false` | **`true`** | 生产未开启 → **拒绝启动**（未绑定租户仍可签出无 `org_id` 令牌） | `settings.py:1091-1112` |
| `OPENBASE_DEFAULT_TENANT_CODE` | 空 | **必须为空** | 生产配置了显式兜底 → **拒绝启动**（掩盖未绑定主体） | `settings.py:1113-1117` |
| `OPENBASE_ENFORCE_TOKEN_VERSION` | `false` | **`true`** | 生产未开启 → **拒绝启动**（令牌版本（`tvn`）降权无法即时生效） | `settings.py:677-694` |
| `OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY` | 空（按环境推导：production→reject） | 留空或 `reject` | 生产设为 `allow` → **拒绝启动**（回退 fail-open） | `settings.py:696-719` |
| `OPENBASE_PRINCIPAL_DB_DEGRADED_ALLOWLIST` | 空 | 留空；确需应急只填十进制主体 id | 含通配/前缀项不被采信（视同未列名，仍拒绝） | `settings.py:367-373` |
| `OPENBASE_PRINCIPAL_ROW_MISSING_POLICY` | 空（按环境推导：production→reject） | 留空或 `reject` | 生产设为 `allow` → **拒绝启动** | `settings.py:721-743` |
| `OPENBASE_PRINCIPAL_ROW_MISSING_ALLOWLIST` | 空 | 留空 | 同上（仅接受十进制 id） | `settings.py:381-388` |
| `OPENBASE_PRINCIPAL_CACHE_TTL_SECONDS` | `900` | 900（边缘终端可维持；缩短则回源更频繁） | 过长放大状态变更生效延迟 | `settings.py:398` |
| `OPENBASE_PRINCIPAL_OFFLINE_GRACE_HOURS` | `72` | 按现场网络中断预算核定（默认 72） | 超期后写操作 503、只读降级放行（留痕） | `settings.py:399-403` |

### 2.4 Key 生命周期、MCP 与异常告警

| 变量 | 默认 | 生产基线 | 缺失/违规后果 | 校验落点 |
|---|---|---|---|---|
| `OPENBASE_SERVICE_KEY_TTL_DAYS` | `90` | 90（`0` 仅过渡期，不建议生产） | 不过期 Key 无法自动退役，放大泄漏窗口 | `settings.py:407` |
| `OPENBASE_SERVICE_KEY_ROTATE_GRACE_HOURS` | `24` | 24（按调用方改造窗口可缩短） | 过短打断调用方；过长延长新旧并存期 | `settings.py:409` |
| `OPENBASE_MCP_API_KEYS` | `dev-mcp-key` | 生产**必须为空**（明文仅开发） | 生产含内置/任何明文 Key → **拒绝启动** | `settings.py:771-807` |
| `OPENBASE_MCP_API_KEY_HASHES` | 空 | 生产推荐：逗号分隔 SHA-256（64 位小写十六进制） | 格式非法 → 拒绝启动；与文件均缺 → 生产拒绝启动 | `settings.py:771-807` |
| `OPENBASE_MCP_API_KEYS_FILE` | 空 | 生产可选：宿主注入明文 Key 文件（每行一个，建议 0600） | 不可读时降级为无 Key（日志/审计留痕） | `settings.py:771-807` |
| `OPENBASE_KEY_ANOMALY_ENABLED` | `true` | `true`（只告警不阻断） | 关闭等于放弃多 IP/突增探测 | `settings.py:419-430` |
| `OPENBASE_KEY_ANOMALY_WINDOW_SECONDS` | `900` | 正整数 | 非正 → 拒绝启动 | `settings.py:808-811` |
| `OPENBASE_KEY_ANOMALY_MAX_IPS` | `3` | 3（`0` 关闭该维度） | 过高漏报 | `settings.py:423-424` |
| `OPENBASE_KEY_ANOMALY_RATE_PER_MINUTE` | `600` | 按业务基线核定（`0` 关闭） | 过低误告警洪泛 | `settings.py:425-426` |
| `OPENBASE_KEY_ANOMALY_ALERT_COOLDOWN_SECONDS` | `300` | 正整数 | 非正 → 拒绝启动 | `settings.py:427-428` |
| `OPENBASE_KEY_ANOMALY_TRUST_FORWARDED_FOR` | `false` | 仅反代部署且已固定代理链时开启 | 直连部署开启会被伪造 `XFF` 误导 | `settings.py:429-430` |

### 2.5 政务与审计治理（E3）

| 变量 | 默认 | 生产基线 | 缺失/违规后果 | 校验落点 |
|---|---|---|---|---|
| `OPENBASE_ABAC_POLICIES` | 空 | 空 = 无属性策略（回落 RBAC）；启用须合法 JSON 数组。运行期新增策略走 `POST /api/v1/auth/access/policies`（`security:admin`，落 `abac_policy_rules` 表并同步审计），判定为「表内启用行 ∪ 本配置基线」，缺省零行为变化 | 非法 JSON/字段 → **所有环境拒绝启动** | `settings.py:651-675`；`modules/auth/abac_policy_store.py` |
| `OPENBASE_AUDIT_RETENTION_DAYS` | `0` | `0`（不清理）或 **≥30** | 1~29 → 拒绝启动（避免误删责任期数据） | `settings.py:651-675` |
| `OPENBASE_AUDIT_EXPORT_MAX_ROWS` | `10000` | 正整数（导出单次上限） | 非正 → 拒绝启动 | `settings.py:651-675` |
| `OPENBASE_IDP_PROVIDERS` | 空 | 空 = 仅既有单 IdP；启用须合法 JSON 数组（名称唯一、必填齐全）。已接入登录路由：`GET /api/v1/auth/oidc/authorize?provider=<name>` 按 Provider 声明发起授权，callback 依 state 记录的 Provider 还原客户端（未登记/未知 Provider → 400 `PARAM_INVALID`） | 非法 → 拒绝启动 | `settings.py:651-675`；`modules/auth/oidc.py` |
| `OPENBASE_OIDC_ENABLED` 及 `OPENBASE_OIDC_*` | 关闭 / 见 `settings.py:452-471` | 按实际 IdP 填写；未映射租户默认 `tenant-1`（非保留码） | 保留码会导致下游 400 | `settings.py:452-471` |
| `OPENBASE_OIDC_STATE_TTL_SECONDS` | `600` | 600（多实例经 Redis 共享一次性 state；Redis 不可用回退进程内） | 非正整数 → **所有环境拒绝启动** | `settings.py:574, 854-968` |
| `OPENBASE_OIDC_PKCE_ENABLED` | `true` | `true`（授权码流 S256；IdP 不支持时方可显式关闭） | 关闭即失去授权码拦截防护（不阻断启动，须记录例外） | `settings.py:576` |
| `OPENBASE_OIDC_SIGNING_ALGORITHMS` | `RS256` | `RS256`（须与 IdP discovery 声明取交集；交集为空即登录失败） | 空值 / 未接线算法（如 `SM2`）→ **所有环境拒绝启动** | `settings.py:578, 748-771` |
| `OPENBASE_OIDC_TOKEN_AUTH_METHOD` | `client_secret_post` | 按 IdP 要求选择 `client_secret_post` / `client_secret_basic` / `mtls` / `tls_client_auth` / `private_key_jwt`（取值归一为小写；Provider 模式共用同一方式） | 非法值 → **所有环境拒绝启动** | `settings.py:582, 854-968` |
| `OPENBASE_OIDC_CLIENT_CERT_PATH` / `_KEY_PATH` / `_CA_PATH` | 空 | 仅 `mtls` / `tls_client_auth` 必填证书与私钥（PEM 只读挂载，禁止入库/入日志）；CA 可选，留空用系统信任库 | 缺证书/私钥路径或文件不存在 → **拒绝启动**；CA 配置后文件不存在 → 拒绝启动 | `settings.py:584-586, 854-968` |
| `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` | 空 | 可选：`tls_client_auth` 期望的证书 subject DN（RFC 4514，如 `CN=openbase-gateway,O=Example`）；配置后启动期比对，留空跳过本地预检 | subject 不匹配或证书非 PEM → **拒绝启动** | `settings.py:589, 854-968` |
| `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS` / `_URI` / `_IP` / `_EMAIL` | 空 | 可选：`tls_client_auth` 期望的证书 SAN 值（DNS/EMAIL 大小写不敏感、IP 归一、URI 精确）；配置后逐项比对，四项全空跳过本地预检 | 任一期望值在证书对应类型 SAN 中不存在 → **拒绝启动** | `settings.py:592-595, 854-968` |
| `OPENBASE_OIDC_CLIENT_PRIVATE_KEY_PATH` / `_ASSERTION_KID` | 空 | 仅 `private_key_jwt` 必填断言签名私钥（PEM 只读挂载，禁止入库/入日志）；`_ASSERTION_KID` 可选（写入断言 JWT header，IdP 多公钥轮换时使用） | `private_key_jwt` 缺私钥路径或文件不存在 → **拒绝启动** | `settings.py:597-598, 854-968` |
| `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM` | `RS256` | 仅 `private_key_jwt` 生效：断言签名算法，可选 `RS256` / `ES256` / `ES384`（须与私钥类型/曲线匹配）；断言与 ID Token 验签白名单解耦 | 取值非法，或私钥类型/曲线错配，或私钥非 PEM → **拒绝启动** | `settings.py:600, 854-968` |
| 登出联动（无新增配置） | — | 生产须启用 `OPENBASE_ENFORCE_TOKEN_VERSION=true`（已为启动门禁），登出端点 `POST /api/v1/auth/oidc/logout` 的 `token_version` 递增才会即时吊销存量令牌；IdP 侧需在 discovery 声明 `end_session_endpoint` 才能返回登出 URL | 未启用强校验 → 登出仅清前端凭据（不作为启动门禁） | `modules/auth/oidc.py` |

### 2.6 上游代理与出站凭证（与 Key 授权直接相关）

| 变量 | 默认 | 生产基线 | 缺失/违规后果 | 校验落点 |
|---|---|---|---|---|
| `OPENBASE_MEMORY_API_KEY` | 内置联调值 | 生产必须替换为真实 Key（密钥管理注入） | 沿用默认值等于公开凭证 | `settings.py:474` |
| `OPENBASE_LLM_API_KEY` | 内置联调值 | 生产必须替换 | 同上 | `settings.py:479` |
| `OPENBASE_LLM_API_KEYS_BY_TENANT` | 空 | 多租户写通道时配置 JSON `{"<tenant>":"<sk-...>"}` | JSON/密钥含空白 → 拒绝启动 | `settings.py:761-768` |
| `OPENBASE_RAG_API_KEY` | 内置联调值 | 生产必须替换（与 OpenRAG 服务 Key 同源） | 同上 | `settings.py:504` |
| `OPENBASE_PROXY_CODE_MAP` | 内置登记 | 仅覆盖确有差异的目标；兜底码不得命中该目标保留码 | 结构非法/兜底码非法 → 拒绝启动 | `settings.py:746-758` |
| `OPENBASE_CAPTURE_RESPONSE` / `OPENBASE_CAPTURE_UPSTREAM` | `false` | 生产**永久关闭**（生产环境开关不生效） | 开启会采集响应摘要（已脱敏）但违背最小化原则 | `settings.py:459-467` |

---

## 3. 四仓镜像矩阵（下游消费方）

> 四仓只配置「如何消费 OpenBase」，**不得复制**策略值（有效期/租户策略/审计留存等）。各仓默认留空 = 不启用，升级零行为变化；启用即需按下表配齐。

| 仓 | 变量 | 默认 | 生产基线 | 校验/落点 |
|---|---|---|---|---|
| OpenLLM | `OPENBASE_JWKS_URL` | 空 | `http://openbase:8000/.well-known/jwks.json` | `backend/app/core/config.py:37-40` |
| OpenLLM | `OPENBASE_JWKS_CACHE_TTL_SECONDS` / `_TIMEOUT_SECONDS` | `300` / `3.0` | 300 / 3.0（未知 kid 强制刷新一次） | `config.py:41-46` |
| OpenLLM | `OPENBASE_JWT_ISSUER` / `_AUDIENCE` / `_LEEWAY_SECONDS` | `openbase` / `openbase-api` / `30` | 与 OpenBase 同值 | `config.py:47-55` |
| OpenLLM | `OPENBASE_SUBJECT_MAP` / `OPENBASE_TRUST_LOCAL_SUBJECT` | 空 / `false` | 映射 JSON；同库部署方可开 `trust=true`，否则未命中即拒绝 | `config.py:56-63` |
| OpenLLM | `OPENBASE_REVOCATIONS_URL` / `OPENBASE_SERVICE_KEY` | 空 / 空 | 吊销端点 + 服务 Key（`X-API-Key`，`scope.system` 含 `auth`） | `config.py:64-71` |
| OpenLLM | `OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` / `_STRICT` | `60` / `false` | 60；严格模式按离线容忍度裁定 | `config.py:72-78` |
| OpenLLM | `IDENTITY_AUTHORITY` | `local` | 生产建议 `openbase`（关闭本地开户/登录/换发） | `config.py:84-87, 1046-1049` |
| OpenRAG | `OPENRAG_API_OPENBASE_JWKS_URL` | 空 | OpenBase JWKS 地址 | `.env.example:110` |
| OpenRAG | `OPENRAG_API_OPENBASE_JWKS_CACHE_TTL_SECONDS` / `_TIMEOUT_SECONDS` | `300` / `3.0` | 同上 | `.env.example:111-112` |
| OpenRAG | `OPENRAG_API_OPENBASE_JWT_ISSUER` / `_AUDIENCE` / `_LEEWAY_SECONDS` | `openbase` / `openbase-api` / `30` | 同上 | `.env.example:113-115` |
| OpenRAG | `OPENRAG_API_OPENBASE_REVOCATIONS_URL` / `_SERVICE_KEY` | 空 / 空 | 同上（服务 Key 同源） | `.env.example:118-119` |
| OpenRAG | `OPENRAG_API_OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` / `_STRICT` | `60` / `false` | 同上 | `.env.example:120-121` |
| OpenRAG | `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` / `OPENRAG_IDENTITY_ROLE_FAIL_CLOSED` | `[]` / `true` | 生产必须登记受信来源并保持 fail-closed | `.env.example:134, 138` |
| OpenMemory | `OPENMEMORY_GATEWAY_JWKS_URL` | 空 | OpenBase JWKS 地址 | `.env.example:15` |
| OpenMemory | `OPENMEMORY_GATEWAY_JWKS_CACHE_TTL_SECONDS` / `_TIMEOUT_SECONDS` | `300` / `3.0` | 同上 | `.env.example:16-17` |
| OpenMemory | `OPENMEMORY_GATEWAY_JWT_ISSUER` / `_AUDIENCE` / `_LEEWAY_SECONDS` | `openbase` / `openbase-api` / `30` | 同上 | `.env.example:18-20` |
| OpenMemory | `OPENMEMORY_GATEWAY_REVOCATIONS_URL` / `_SERVICE_KEY` | 空 / 空 | 同上 | `.env.example:23-24` |
| OpenMemory | `OPENMEMORY_GATEWAY_REVOCATION_SYNC_INTERVAL_SECONDS` / `_STRICT` | `60` / `false` | 同上 | `.env.example:25-26` |
| OpenMemory | `OPENMEMORY_GATEWAY_OIDC_MODE` / `ALLOW_UNVERIFIED_GATEWAY_TOKEN` | `local` / `false` | 生产保持 `false`（来源未验签令牌一律拒绝） | `.env.example:33-34` |
| DPS | `DPS_OPENBASE_JWKS_URL` | 空 | OpenBase JWKS 地址 | `src/config.py:197` |
| DPS | `DPS_OPENBASE_JWKS_CACHE_TTL_SECONDS` / `_TIMEOUT_SECONDS` | `300` / `3.0` | 同上 | `src/config.py:198-199` |
| DPS | `DPS_OPENBASE_JWT_ISSUER` / `_AUDIENCE` / `_LEEWAY_SECONDS` | `openbase` / `openbase-api` / `30` | 同上 | `src/config.py:200-202` |
| DPS | `DPS_OPENBASE_SUBJECT_MAP` / `_TRUST_LOCAL_SUBJECT` | 空 / `false` | 未命中映射即拒绝；仅同库部署可开 `trust` | `src/config.py:203-205` |
| DPS | `DPS_OPENBASE_REVOCATIONS_URL` / `_SERVICE_KEY` | 空 / 空 | 同上 | `src/config.py:208-209` |
| DPS | `DPS_OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` / `_STRICT` | `60` / `false` | 同上 | `src/config.py:211-214` |

---

## 4. 启动门禁清单（缺配即拒启）

OpenBase 侧 13 项 `@model_validator(mode="after")` / 装配期门禁，按 `settings.py` 顺序：

| # | 门禁方法 | 触发条件（生产） | 违规结果 |
|---|---|---|---|
| 1 | `_validate_jwt_secret` | 弱/占位/缺失 JWT 密钥 | 拒绝启动 |
| 2 | `_validate_rs256_configuration` | `jwt_require_rs256=true` 但缺 PEM 或 kid；JWKS JSON 非法 | 拒绝启动 |
| 3 | `_validate_signature_algorithm` | 算法未登记或不可用（含 SM2 预留） | 拒绝启动 |
| 4 | `_validate_e3_governance_configuration` | ABAC/IdP JSON 非法；留存 1~29 天；导出上限非正 | 拒绝启动 |
| 5 | `_validate_oidc_hardening_configuration` | OIDC state TTL 非正；验签算法为空或含未接线算法（如 `SM2`） | 拒绝启动（所有环境） |
| 6 | `_validate_oidc_token_auth_configuration` | token 认证方式非法；`mtls` / `tls_client_auth` 缺证书或私钥路径、文件不存在；`tls_client_auth` 证书非 PEM、subject 与 `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` 不匹配、或任一 `_SAN_*` 期望值在证书 SAN 中不存在；`private_key_jwt` 缺断言私钥路径或文件不存在、私钥非 PEM、私钥类型/曲线与 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM` 错配 | 拒绝启动（所有环境） |
| 7 | `_validate_production_token_version_enforcement` | 未开 `enforce_token_version` | 拒绝启动 |
| 8 | `_validate_principal_db_degraded_policy` | 策略为 `allow` 或取值非法 | 拒绝启动 |
| 9 | `_validate_principal_row_missing_policy` | 同上 | 拒绝启动 |
| 10 | `_validate_outbound_tenant_alignment` | 出站兜底码为空或命中目标保留码 | 拒绝启动 |
| 11 | `_validate_llm_api_keys_by_tenant` | 映射 JSON 非法/密钥含控制字符 | 拒绝启动 |
| 12 | `_validate_mcp_edge_configuration` | 明文/内置 MCP Key；摘要格式非法；摘要与文件均缺；异常参数非正 | 拒绝启动 |
| 13 | `validate_production_login_tenant_policy` | 未开租户强绑定，或配置了显式兜底租户 | 拒绝启动 |

四仓侧生产 fail-closed 门禁（受信来源与角色口径）按各仓配置：OpenRAG `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` / `OPENRAG_IDENTITY_ROLE_FAIL_CLOSED`；OpenLLM `TRUSTED_PROXY_SOURCES` / `ENFORCE_INBOUND_IDENTITY_HEADERS`；OpenMemory / DPS 以各仓受信代理与角色映射配置为准，漏配即拒启或拒绝入站。

---

## 5. 密钥与秘密管理

| 秘密 | 形态要求 | 允许位置 | 禁止 |
|---|---|---|---|
| RS256 私钥 | PEM 只读挂载（0600） | 宿主文件路径 `OPENBASE_JWT_RSA_PRIVATE_KEY_PATH` | 内联环境变量、进 git、进日志 |
| RS256 公钥 | 由私钥派生 + 可登记额外 kid | `OPENBASE_JWT_JWKS_PUBLIC_KEYS`（PEM 或 `@文件`） | 与私钥混放明文 |
| JWT 共享密钥（过渡） | ≥32 字符强随机 | 密钥管理注入 `OPENBASE_JWT_SECRET` / `_PREVIOUS` | 演示值、占位值 |
| 服务 Key（`ob_k_*`） | 摘要落库，明文一次性下发 | 下游 `*_OPENBASE_SERVICE_KEY`（`X-API-Key`，`scope.system` 含 `auth`） | 落日志、写进文档、提交 git |
| MCP 静态 Key | 生产只存摘要或宿主文件 | `OPENBASE_MCP_API_KEY_HASHES` / `OPENBASE_MCP_API_KEYS_FILE` | `OPENBASE_MCP_API_KEYS` 明文（生产拒绝启动） |
| 上游 Key（memory/llm/rag） | 密钥管理注入 | `OPENBASE_MEMORY_API_KEY` / `OPENBASE_LLM_API_KEY` / `OPENBASE_RAG_API_KEY` | 沿用内置联调默认值 |

---

## 6. 配置漂移自检（上线前与每次变更后）

**6.1 变量存在性核对**（逐条对照第 2、3 节，结果存 `evidence/a2/`）：

- OpenBase：确认第 2 节所有「生产基线」非空项已注入；秘密类只记录「已配置/未配置」，不记录值。
- 四仓：确认 JWKS 地址、吊销地址、服务 Key、`IDENTITY_AUTHORITY`/受信来源四项齐备。

**6.2 端点可达与内容核对**：

```powershell
# JWKS 只发公钥，kid 与 OPENBASE_JWT_SIGNING_KID 一致
curl.exe -s "$Env:OPENBASE_URL/.well-known/jwks.json" | jq '.keys | length, .[0].kid'
```

- 吊销增量端点由下游携带服务 Key 拉取（`GET /api/v1/auth/revocations?since=&limit=`），单页上限受 `OPENBASE_JWT_REVOCATIONS_PAGE_LIMIT` 约束。
- 内省端点（`POST /api/v1/auth/introspect`）无缓存，用于排障，不作为常规鉴权路径。

**6.3 负向启动核对**（对应 A1-11）：

- 临时移走 PEM → 重启必须**拒绝启动**；恢复后重启成功。
- 生产置 `OPENBASE_MCP_API_KEYS=dev-mcp-key` → 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_SIGNING_ALGORITHMS=SM2` → 必须**拒绝启动**（未接线算法）。
- 生产置 `OPENBASE_DEFAULT_TENANT_CODE=<任意>` → 必须**拒绝启动**。
- 生产置 `OPENBASE_AUDIT_RETENTION_DAYS=7` → 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_TOKEN_AUTH_METHOD=mtls` 但缺 `OPENBASE_OIDC_CLIENT_CERT_PATH` / `_KEY_PATH` → 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_TOKEN_AUTH_METHOD=private_key_jwt` 但缺 `OPENBASE_OIDC_CLIENT_PRIVATE_KEY_PATH`（或指向文件不存在）→ 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_TOKEN_AUTH_METHOD=tls_client_auth` 且 `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` 与证书 subject 不一致（或证书非 PEM）→ 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_CLIENT_CERT_SAN_DNS=<与证书不符的值>`（证书无该 DNS SAN）→ 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_CLIENT_ASSERTION_ALGORITHM=ES256` 但私钥为 RSA（或私钥非 PEM）→ 必须**拒绝启动**。
- 生产置 `OPENBASE_OIDC_TOKEN_AUTH_METHOD=client_secret_jwt`（未实现方式）→ 必须**拒绝启动**（取值非法）。

---

## 7. 验收项与签核

| 验收项 | 内容 | 判定 | 证据 |
|---|---|---|---|
| A2-01 | OpenBase 第 2 节基线逐项落地（秘密类仅记状态） | Pass/Fail | `a2-01.txt` |
| A2-02 | 13 项启动门禁负向样例各命中一次（第 6.3 节） | Pass/Fail | `a2-02.txt` |
| A2-03 | JWKS 只发公钥、kid 一致（第 6.2 节） | Pass/Fail | `a2-03.txt` |
| A2-04 | 四仓镜像矩阵齐备且 `iss/aud` 一致 | Pass/Fail | `a2-04.txt` |
| A2-05 | 服务 Key 权限面最小化（`scope.system` 仅含 `auth`/`*` 必要项） | Pass/Fail | `a2-05.txt` |
| A2-06 | 秘密未落 git/日志/文档（抽样核查） | Pass/Fail | `a2-06.txt` |

**判定规则**：每项仅 `Pass / Fail / Blocked`；P0（A2-01/02/03）任一 `Fail` 不得上线；`Blocked` 须写明原因与解除条件。

**证据规范**：`doc/audit/verification/evidence/a2/a2-<编号>-<YYYYMMDD>.<ext>`；禁止保存私钥、令牌全文、服务 Key 明文、`client_secret`。

---

## 8. 已知边界

- 本清单只覆盖**配置口径**，不代表配置已生效：实际生效需配合 A1 清单在生产拓扑执行（尤其 A1-01/02/04/11/12）。
- 四仓 JWKS/吊销为**惰性拉取**（无后台线程，请求触发同步），配置正确不等于收敛时延达标，时延验收见 A1-04。
- OpenLLM 的 `.env.example` 未逐项列出 OpenBase 验签变量，以 `backend/app/core/config.py` 字段名为准；部署编排必须显式注入，不能依赖默认空值。
- 留存清理、审计导出为**人工端点**（默认 dry-run / 显式 POST），不构成自动限期清除；平台级集中审计与介质归档仍待基础设施。
- 配置项校验落点行号以当前分支为准，升级后需重新核对；本清单随方案版本同步升版。
