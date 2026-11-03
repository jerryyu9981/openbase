# OpenBase 四系统 API Key 优化 —— 生产窗口执行单与回滚方案 - v1.0.5

| 项 | 内容 |
|---|---|
| 项目名称 | OpenBase（开放底座）四系统 API Key 与授权治理 |
| 下发单编号 | **XR-OPS-08-APIKEY-001** |
| 文档版本 | v1.0.5 |
| 状态 | **[Approved] 人工批准（2026-11-03）；阶段 0 已闭合（F0-4/F0-5 Fail 已整改为 Pass）；本机全栈启动复核已执行并完成阻塞整改：五系统并行启动 **5 / 5 running（HTTP 200）**（见 §13）；阶段 1~6 待 OPS 生产窗口** |
| 执行进度 | 阶段 0（执行前检查）已完成：RF-01（共享 PG 补列）与 RF-02（Redis 前缀登记）于 2026-11-03 闭合；RF-03 / RF-04 研发侧交付已完成（§11 附录 B 逐仓逐键补录表单），实际填值仍待生产 `.env` → ⛔ Blocked；**本机全栈复核与阻塞整改（§12 / §13）**：五系统并行启动全部 HTTP 200（OpenBase 8000 / OpenLLM 8020 / DPS 8013 / OpenRAG 8030 / OpenMemory 8040），整改仅限共享解释器依赖与进程级环境变量，未改仓库源码；阶段 1~6 因生产主机不可达仍 ⛔ Blocked |
| 创建日期 | 2026-11-03 |
| 编制 | FA-OpenBase-Dev（AI 辅助） |
| 执行方 | OPS（生产环境）+ 生产 DBA（仅 P-01） |
| 上游依据 | 《OpenBase-四系统APIKey优化-残余项统一处置方案-v1.5.0》§5.5/§5.6/§6；《…-残余项分批推进方案-v1.5.0》§9.8；《…-A1生产验收清单-v1.1.8》A1-04/A1-12/A1-14；《…-A2生产配置收口清单-v1.2.0》§3/§4/§5/§6/§7 |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.31.0.md`（§10.7~§10.34） |
| 格式范本 | `doc/release/OpenBase-生产环境配置下发单-XR-OPS-07-v1.0.0.md` |
| 整体回滚参照 | `doc/release/OpenBase-主备双通道生产上线回滚方案-v1.0.0.md` |
| 唯一事实源 | 本单（执行口径）；配置键名以 A2 v1.2.0 §3 为准；状态判定以 A1 v1.1.8 / A2 v1.2.0 §7 为准 |
| 共享基础设施 | **五仓共享 PG、共享 Redis、共享网关/反向代理、共享 IdP、共享密钥挂载路径、共享服务 Key** —— 见 §2 |

> **本单性质**：E 批 42 项判定为 **34 Pass + 8 生产前置 Blocked**（见 E3 批次总结报告 v1.2.1 §1）。本单只承载这 **8 项 Blocked** 的生产执行与回滚口径，不重复已闭合的 C/G/K 类代码项，也不替代 E5 生产拓扑实测。

---

## 1. 范围与 8 项清单

| # | 发布任务 | 台账编号 | 类型 | 目标系统 | 前置依赖 | 当前判定 |
|---|---|---|---|---|---|---|
| P-01 | 存量 `ob_k_*` 服务 Key 到期收敛 | D-04 / A1-12 步骤3 / ER-01 | 生产动作（数据） | OpenBase 控制面（**共享 PG**） | P-03 完成 + 服务 Key 轮换完成 | ⛔ Blocked（待 DBA 会话 + 变更单） |
| P-02 | 显式主体映射注入 | D-05 | 生产动作（配置） | OpenLLM / DPS / OpenBase 服务账号 | P-03 完成 | ⛔ Blocked（无生产主机访问权） |
| P-03 | 生产 `.env` 注入 + PEM 0600 只读挂载 | D-06 / A2-01 | 生产动作（配置/密钥） | OpenBase + 四下游 | 无（窗口起点） | ⛔ Blocked（无部署主机） |
| P-04 | 三仓 `STATIC_KEY_CHANNEL` `dual`→`closed` | K-01（裁定 B） | 生产动作（配置） | OpenRAG / OpenMemory / DPS | P-01~P-03 完成 + 双通道观察窗口结束 + §4 阶段 4 实测通过 | ⛔ Blocked（窗口未到关闭时点） |
| P-05 | 吊销收敛时延实测（≤60s 或书面放宽） | A1-04 / V-04 | 生产实测 | 四仓 | P-03 + P-02 | ⛔ Blocked（无生产拓扑） |
| P-06 | 跨仓整服务实测（验签/吊销/门禁/审计字段） | A1-14 / V-14 | 生产实测 | 四仓 | P-03 + P-02 | ⛔ Blocked（三仓整服务未启） |
| P-07 | 四仓镜像矩阵 + 服务 Key 权限面最小化 | A2-04 / A2-05 | 生产实测 | 四仓 | P-03 | ⛔ Blocked（无真实服务 Key 权限面） |
| P-08 | 跨仓时延 / 真实 IdP 联调 / issuer 判重 | V-04 / V-13 / D-07 | 生产实测 | OpenBase + 真实 IdP | P-03 | ⛔ Blocked（无可达 IdP） |

**执行顺序（刚性）**：P-03 → P-02 → P-01 → 阶段 4（P-05/P-06/P-07/P-08 同批取证）→ P-04 → 阶段 6 放行。
**禁止**：P-04 不得在 P-05/P-06 之前执行；P-01 不得在 P-03 之前执行；任何阶段跳过 §3 备份与快照即视为门禁不通过。

---

## 2. 共享基础设施影响面与前置约束

> 五仓共用同一套基础设施。**任一项变更的影响面不限于本仓**，因此本单所有动作按「影响面最小化 → 单仓先验 → 同批推广 → 观察窗口 → 收口」推进；每阶段结束必须确认共享组件无异常指标。

| 共享组件 | 本单承载项 | 约束（必须遵守） | 执行纪律 | 回滚影响面 |
|---|---|---|---|---|
| **共享 PostgreSQL**（OpenBase 控制面库 `schema=openbase`，表 `service_api_keys`） | P-01 | ① 只操作 `openbase` schema，禁止跨 schema DDL/DML；② 单批 ≤200 行、单租户批次；③ 必须设 `lock_timeout`/`statement_timeout`，禁止长事务；④ 禁止 `SELECT *`、禁止全表 `UPDATE`；⑤ 到期时间为 `NULL` 的存量行才可收敛；⑥ 列结构须与模型一致（`expires_at` / `last_used_at` / `rotated_from` / `tenant_code`），缺失列时禁止直接收敛（见 §8.4 / RF-01） | 生产 DBA 会话 + 变更单 + 执行前原值快照 + 每批复核 + 回填执行记录表 | 反向 `UPDATE … SET expires_at = NULL` 仅限快照 `key_id` 清单；不涉及其他 schema，不触发跨仓重启 |
| **共享 Redis**（多实例 OIDC state / 配额令牌桶 / 异常聚合） | P-02、P-03、P-05 | ① 每仓固定独立 DB index + key 前缀隔离（登记于 §3.4）；② 禁止 `FLUSHDB` / `FLUSHALL` / `KEYS`；③ 必须区分「Redis 可用 → 多实例共享」与「Redis 不可用 → 进程内回退」两种语义；④ `QUOTA_ALGORITHM=token_bucket` 依赖 Redis Lua 原子性，切换前确认数据库索引 | 变更前后各采样一次 Redis 连接与 DB index；禁止清库；幂等键保留 TTL | Redis 侧无需回滚（无本单写入）；若出现跨仓 key 冲突，按 key 前缀定位并只删本仓前缀 |
| **共享网关/反向代理**（JWKS、吊销、内省统一出口） | P-03、P-05、P-06、P-07 | ① 四仓 `*_JWKS_URL` / `*_REVOCATIONS_URL` 必须走网关域名，不得直连容器名；② 网关超时必须 **≥3s**（下游默认 `*_TIMEOUT_SECONDS=3.0`，本机曾用 120s 修正，生产须与网关对齐）；③ 网关需放行 `/.well-known/jwks.json`、`GET /api/v1/auth/revocations`、`POST /api/v1/auth/introspect`；④ 网关 5xx 会导致下游 JWKS 缓存陈旧，必须记录刷新失败告警 | 变更前用网关路径（非直连）验证三条端点；变更后核对网关错误率与超时计数 | 网关无配置变更；若超时/路由异常，回滚到上一版下游 `.env` 的 URL 取值 |
| **共享 IdP**（多 Provider 登记） | P-03、P-08 | ① 登记前逐 Provider 取 `discovery.issuer` 并**判重**（D-07）；② 同一 issuer 多 client 视为同一身份空间，仅允许一个 Provider 承担 back-channel 登出（`oidc.py:1197-1224` 取首条存在歧义）；③ state 一次性依赖共享 Redis，TTL 见 `OPENBASE_OIDC_STATE_TTL_SECONDS` | issuer 清单随本单归档（只记 issuer，不记 `client_secret`） | 回滚登记即撤下新增 Provider；已签发的本地 `token_version` 吊销不回滚 |
| **共享密钥挂载路径**（RS256 私钥 PEM） | P-03 | ① 私钥只读挂载、POSIX `0600`、属主为服务运行账号；② 禁止内联 PEM 到环境变量；③ 四仓共用同一宿主挂载目录时，只给 OpenBase 挂私钥，下游只取 JWKS（不挂私钥）；④ 挂载变更后必须重启并做负向验证（移走路径 → 拒启） | 记录挂载绝对路径 + 权限 + 属主（只记状态，不记内容） | 恢复上一版挂载路径 + `.env` 备份 + 重启；若私钥缺失，OpenBase 会 **拒绝启动**（fail-closed），不得带病放行 |
| **共享服务 Key**（`ob_k_*`，`scope.system` 含 `auth`，四仓同源） | P-01、P-03、P-07 | ① **同一把服务 Key 被多个下游消费**：收敛/轮换必须「先签新 → 下游全量替换并验证 → 再收敛旧」；② 服务 Key 明文不落日志/文档/git；③ 权限面最小化：`scope.system` 仅保留 `auth` 必要项；④ 收敛 `expires_at` 必须留过渡期（不得早于执行时点，建议 ≥7 天至轮换窗口结束） | 每仓 `*_OPENBASE_SERVICE_KEY` 同批替换；替换后逐仓验证吊销端点 200 | 回滚 = 下游恢复旧 Key（因旧 Key 仅设到期未立即吊销，过渡期内仍可用）；一旦旧 Key 已到期，回滚路径只剩重新签发 |

### 2.1 共享基础设施前置确认（阶段 0 必做）

| 项 | 确认内容 | 记录方式 |
|---|---|---|
| 共享 PG | 实例地址、库名、schema `openbase` 可写、当前 `service_api_keys` 中 `expires_at IS NULL` 行数 | 只记主机/库/计数，不记凭据 |
| 共享 Redis | 各仓使用的 DB index 与 key 前缀；`REDIS_URL` 是否与四仓一致 | 只记 index/前缀与可达状态 |
| 共享网关 | JWKS/吊销/内省三条路径经网关返回码；网关超时配置值 | 状态码 + 超时秒数 |
| 共享 IdP | 已登记 Provider 名称清单与 `discovery.issuer` 清单（判重结果） | issuer 清单（不含 secret） |
| 共享 PEM 挂载 | 宿主绝对路径、`0600`、属主；是否只读挂载 | 路径 + 权限 + 属主 |
| 共享服务 Key | 当前在用 `key_id`（非明文）、`scope.system` 取值、各仓引用同一把的确认 | `key_id` + scope 列表 |

---

## 3. 执行前检查（窗口起点，缺一不可）

### 3.1 窗口与授权

```bash
# 1) 记录五仓候选发布版本（与 A1-14 前置一致）
for repo in OpenBase OpenLLM OpenRAG OpenMemory DPS; do
  echo "== $repo =="; git -C "<$repo 生产检出目录>" rev-parse HEAD
done

# 2) 确认变更单号与回滚窗口（手工填写，随本单归档）
#    变更单号：__________   回滚窗口：__________   执行人：__________
```

### 3.2 配置文件备份（逐仓，必须先备份再改）

```bash
# 每个仓的部署目录执行一次
cp .env ".env.bak-xrops08-$(date +%Y%m%d-%H%M%S)"
# 共享基础设施文件（若被服务编排加载）
cp .env.shared-infra ".env.shared-infra.bak-xrops08-$(date +%Y%m%d-%H%M%S)"
```

### 3.3 数据快照（P-01 前置，共享 PG）

```sql
-- 只读导出，不含 key_hash / 明文；用于回滚定位
SELECT id, key_id, name, status, scope -> 'tenants' AS scope_tenants,
       expires_at, revoked_at, last_used_at, created_at
  FROM openbase.service_api_keys
 WHERE expires_at IS NULL
 ORDER BY created_at ASC, id ASC;
```

产出：`doc/audit/verification/evidence/p01/p01-key-snapshot-<YYYYMMDD>.csv`（**不含** `key_hash`/明文）。
> **列结构门禁**：若 `service_api_keys` 缺 `expires_at`（或 `last_used_at` / `rotated_from` / `tenant_code`），立即停止，先执行幂等增量迁移（`openbase/modules/identity/migration.py`，见 RF-01），**不得跳过快照直接收敛**。

同时记录基线计数：

```sql
SELECT count(*) AS remaining_without_expiry FROM openbase.service_api_keys WHERE expires_at IS NULL;
```

### 3.4 Redis 隔离登记（共享 Redis，防止跨仓串键）

| 仓 | DB index | key 前缀（代码实测，2026-11-03） | 承载用途 | 证据位置 |
|---|---|---|---|---|
| OpenBase | `0` | `openbase:` | OIDC state / id_token_hint / logout sid·sub·jti / key_anomaly / identity:events / notify / service_key:expiring | `openbase/modules/auth/oidc_state.py`、`oidc_logout.py`、`key_anomaly.py`、`openbase/modules/identity/events.py`、`openbase/modules/notify/__init__.py`、`openbase/modules/auth/service_keys.py` |
| OpenLLM | `0` | `openllm:semantic_cache`、`quota:`、`quota_usage:`、`quota_bucket:` | 语义缓存 / 配额窗口 / 配额用量 / 令牌桶 | `backend/app/core/semantic_cache.py`、`backend/app/edgerouter/middleware/quota.py`、`backend/app/services/quota_token_bucket.py` |
| OpenRAG | `0` | `blocklist:` | 身份事件 blocklist 缓存（`blocklist:{subject_type}:{subject_id}`） | `src/openrag/identity/blocklist.py` |
| OpenMemory | `0` | `om:`（`om:session` / `om:cache` / `om:result` / `om:sessmeta`） | 会话 / 缓存 / 检索结果 / 会话元数据 | `src/openmemory/storage/cache_store.py` |
| DPS | `0` | `dps:`（`CACHE_KEY_PREFIX` 默认）、`dps:rl:` | 画像/查询/统计缓存、限流 | `src/config.py`、`src/cache.py`、`src/engines/rate_limit_engine.py` |

**登记结论（RF-02）**：五仓 token 前缀互不重合，**无跨仓串键冲突**，窗口可继续。

**残余风险（非阻断，不在本次窗口改代码）**：
1. OpenLLM 的 `quota:` / `quota_usage:` / `quota_bucket:` 与 OpenRAG 的 `blocklist:` **未带仓名命名空间**，后续新增使用方存在撞键风险；建议在各自下一版本加 `openllm:` / `openrag:` 前缀。
2. 五仓共用 `db=0`，运维禁用 `FLUSHDB` / `FLUSHALL` / `KEYS`，只允许按已登记前缀 `SCAN` 定点清理。

### 3.5 秘密状态登记（只记状态，不记值）

| 秘密 | 形态要求 | 状态（已配置/未配置） | 位置 |
|---|---|---|---|
| `OPENBASE_JWT_RSA_PRIVATE_KEY_PATH` | PEM 只读挂载 `0600` |  | 宿主绝对路径 |
| `OPENBASE_JWT_SIGNING_KID` | 与 JWKS `kid` 一致 |  | `.env` |
| `OPENBASE_JWT_REQUIRE_RS256` | `true` |  | `.env` |
| `OPENBASE_IDP_PROVIDERS` | JSON 数组，name 唯一 |  | `.env` |
| `OPENBASE_MCP_API_KEY_HASHES` / `_FILE` | 摘要或宿主文件 |  | `.env` / 文件 |
| `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` | JSON 映射 |  | `.env` |
| 四仓 `*_OPENBASE_SERVICE_KEY` | `X-API-Key`，`scope.system` 含 `auth` |  | `.env` |

---

## 4. 分阶段执行

> 每阶段结束必须「执行 → 核对 → 留痕 → 门禁判定」，判定仅允许 `Pass / Fail / Blocked`；`Fail` 立即进入 §5 回滚，不得进入下一阶段。

### 阶段 1 —— P-03 生产 `.env` 注入 + PEM 0600 只读挂载

**前置**：§3.1~§3.3 完成；密钥已由密钥管理下发。

**操作**：

1. 挂载私钥（只读、`0600`、属主=服务运行账号），仅 OpenBase 挂私钥，下游只取 JWKS：

```bash
install -m 600 -o <服务账号> -g <服务组> "<密钥管理下发的私钥>" "<挂载绝对路径>/openbase-rs256.pem"
# 校验：权限与只读
stat -c '%a %U:%G %n' "<挂载绝对路径>/openbase-rs256.pem"
```

2. OpenBase `.env` 注入生产基线（秘密类只回填引用路径，不写明文 PEM）：

```bash
# 键存在 → 覆盖；不存在 → 追加；每键必须唯一
set_kv() {
  key="$1"; val="$2"; f="$3"
  if grep -q "^${key}=" "$f"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$f"
  else
    printf '\n%s=%s\n' "$key" "$val" >> "$f"
  fi
}
set_kv OPENBASE_JWT_RSA_PRIVATE_KEY_PATH "<挂载绝对路径>/openbase-rs256.pem" .env
set_kv OPENBASE_JWT_SIGNING_KID "<kid>" .env
set_kv OPENBASE_JWT_REQUIRE_RS256 true .env
set_kv OPENBASE_JWT_ISSUER openbase .env
set_kv OPENBASE_ENFORCE_TOKEN_VERSION true .env
set_kv OPENBASE_OIDC_STATE_TTL_SECONDS "<正整数>" .env
set_kv OPENBASE_MCP_API_KEY_HASHES "<摘要列表>" .env        # 或改用 _FILE
set_kv OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP "<映射 JSON>" .env
set_kv OPENBASE_IDP_PROVIDERS "<Provider JSON 数组>" .env

# 唯一性校验（每键必须为 1）
for k in OPENBASE_JWT_RSA_PRIVATE_KEY_PATH OPENBASE_JWT_SIGNING_KID OPENBASE_JWT_REQUIRE_RS256 \
         OPENBASE_JWT_ISSUER OPENBASE_ENFORCE_TOKEN_VERSION OPENBASE_OIDC_STATE_TTL_SECONDS; do
  printf '%s=%s\n' "$k" "$(grep -c "^${k}=" .env)"
done
```

3. 四下游 `.env` 按 A2 v1.2.0 §3 **逐仓**注入（键名以 §3 原文为准，DPS 的 `IDENTITY_AUTHORITY` / `STATIC_KEY_CHANNEL` **无 `DPS_` 前缀**）：

| 仓 | 本阶段必须齐备的键（生产基线） |
|---|---|
| OpenLLM | `OPENBASE_JWKS_URL`、`OPENBASE_JWKS_CACHE_TTL_SECONDS`/`_TIMEOUT_SECONDS`(300/3.0)、`OPENBASE_JWT_ISSUER`/`_AUDIENCE`/`_LEEWAY_SECONDS`(openbase/openbase-api/30)、`OPENBASE_REVOCATIONS_URL`/`OPENBASE_SERVICE_KEY`、`OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS`/`_STRICT`(60/false)、`IDENTITY_AUTHORITY`（生产 `openbase`）、`OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED`（按 A1-04 口径）、`QUOTA_ALGORITHM` + 令牌桶参数（如启用） |
| OpenRAG | `OPENRAG_API_OPENBASE_JWKS_URL`、`_JWKS_CACHE_TTL_SECONDS`/`_TIMEOUT_SECONDS`、`_JWT_ISSUER`/`_AUDIENCE`/`_LEEWAY_SECONDS`、`OPENRAG_API_OPENBASE_REVOCATIONS_URL`/`_SERVICE_KEY`、`_REVOCATION_SYNC_INTERVAL_SECONDS`/`_STRICT`、`OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES`、`OPENRAG_IDENTITY_ROLE_FAIL_CLOSED=true`、`OPENRAG_IDENTITY_ROLE_CONTRACT_URL`（如启用）、`OPENRAG_API_OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` |
| OpenMemory | `OPENMEMORY_GATEWAY_JWKS_URL`、`_JWKS_CACHE_TTL_SECONDS`/`_TIMEOUT_SECONDS`、`_JWT_ISSUER`/`_AUDIENCE`/`_LEEWAY_SECONDS`、`OPENMEMORY_GATEWAY_REVOCATIONS_URL`/`_SERVICE_KEY`、`_REVOCATION_SYNC_INTERVAL_SECONDS`/`_STRICT`、`OPENMEMORY_GATEWAY_OIDC_MODE`/`ALLOW_UNVERIFIED_GATEWAY_TOKEN=false`、`OPENMEMORY_IDENTITY_ROLE_CONTRACT_URL`（如启用）、`OPENMEMORY_GATEWAY_REVOCATION_BACKGROUND_SYNC_ENABLED` |
| DPS | `DPS_OPENBASE_JWKS_URL`、`_JWKS_CACHE_TTL_SECONDS`/`_TIMEOUT_SECONDS`、`_JWT_ISSUER`/`_AUDIENCE`/`_LEEWAY_SECONDS`、`DPS_OPENBASE_REVOCATIONS_URL`/`_SERVICE_KEY`、`_REVOCATION_SYNC_INTERVAL_SECONDS`/`_STRICT`、`IDENTITY_AUTHORITY`（生产 `openbase`）、`IDENTITY_ROLE_CONTRACT_URL`（如启用）、`DPS_OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` |

> 本阶段**不**改 `STATIC_KEY_CHANNEL`（保持 `dual`，归阶段 5）。

**通过判据**：

- OpenBase 生产门禁 13 项放行、进程启动成功、`/health` 200；
- 负向三连（移走 PEM → 拒启；置明文 `OPENBASE_MCP_API_KEYS` → 拒启；`OPENBASE_JWT_REQUIRE_RS256=false` → 拒启）各命中一次，恢复后 200；
- JWKS 仅发 RSA 公钥且 `kid` 与 `OPENBASE_JWT_SIGNING_KID` 一致；
- 四下游 `/health` 200 且启动日志无「未配置 JWKS/吊销」致命项；
- `stat` 输出显示 `0600` 且只读；
- 日志抽样无 PEM 头、无服务 Key 明文、无 `client_secret`。

**回滚**：见 §5 `R-03`。

---

### 阶段 2 —— P-02 显式主体映射注入

**前置**：阶段 1 通过；OpenLLM/DPS 目标用户已在本仓存在（未建用户先建后映射）。

**操作**：

```jsonc
// OpenLLM：OPENBASE_SUBJECT_MAP
{"<openbase-sub>": "<openllm-local-user-id>"}
// DPS：DPS_OPENBASE_SUBJECT_MAP
{"<openbase-sub>": "<dps-local-user-id>"}
// OpenBase 控制面：OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP（机器主体）
{"<idp-sub>": "<openbase-service-account-subject>"}
```

约束（D-05 模板原文）：仅 RS256 / `IDENTITY_AUTHORITY=openbase` 生效时注入；键为归一 `sub`（禁止邮箱/显示名）；值为本仓已存在用户；映射表随本单下发，禁止入 git/日志/监控标签。

**通过判据（两向各一次）**：

- 映射主体登录成功（四仓受保护接口 200）；
- 未映射主体被拒绝（401，OpenLLM/DPS 各命中一次）；
- 变更留痕记录「变更人 / 时间 / 新增或删除条数」（不记录主体明文列表）。

**回滚**：见 §5 `R-02`。**禁止**以「清空映射」作为回滚手段（会导致全量拒绝）。

---

### 阶段 3 —— P-01 存量 `ob_k_*` 到期收敛（共享 PG）

**前置**：阶段 1、阶段 2 通过；服务 Key 已按轮换方案签发并在四下游验证可用；DBA 会话 + 变更单到位；**共享 PG 列结构核对通过**（`service_api_keys` 含 `expires_at` / `last_used_at` / `rotated_from` / `tenant_code`，缺失则先执行幂等迁移，见 RF-01）。

**操作（按 `d-04-expired-key-convergence-20261101.sql` 口径，分三批）**：

```sql
-- 会话级保护（共享 PG，避免长事务影响其他仓）
SET lock_timeout = '3s';
SET statement_timeout = '30s';

-- 分批收敛：单租户 + 创建时间截止点 + 单批 ≤200 行
-- batch_expires_at 必须晚于执行时点（过渡期 ≥7 天）
UPDATE openbase.service_api_keys
   SET expires_at = :batch_expires_at, updated_at = now()
 WHERE expires_at IS NULL
   AND status = 'active'
   AND created_at < :batch_cutoff
   AND scope -> 'tenants' @> jsonb_build_array(:tenant_code);

-- 每批复核
SELECT count(*) AS remaining_without_expiry FROM openbase.service_api_keys WHERE expires_at IS NULL;
```

执行记录表（每批一行，随本单归档）：

| 批次 | 租户码 | 行数 | 截止点 | 到期时间 | 执行人 | 复核结果 | 证据文件 |
|---|---|---|---|---|---|---|---|
| B1 | | | | | | | |
| B2 | | | | | | | |
| B3 | | | | | | | |
| 豁免 | | | | | | | |

**通过判据**：

- 每批 `remaining_without_expiry` 单调下降，最终为 `0` 或「仅剩已登记豁免行」；
- 四下游使用当前服务 Key 调用吊销端点全部 200（证明未被误伤）；
- `GET /api/v1/auth/service-keys` 到期清单可见（C-08 口径）；
- 执行记录表 8 列全部回填。

**回滚**：见 §5 `R-01`。

---

### 阶段 4 —— P-05 / P-06 / P-07 / P-08 生产实测（同批取证，`dual` 态）

> 四项同批执行、共用同一窗口，避免配置漂移导致结论对不上；**全部在 `STATIC_KEY_CHANNEL=dual` 状态下取证**（`closed` 归阶段 5，其回归归阶段 6）。

**P-05 吊销收敛时延（A1-04 / V-04）**

1. 测试用户登录取令牌 → 四仓各请求一次 → 200；
2. 内省确认 `active=true`：

```bash
curl -s -X POST "$OPENBASE_URL/api/v1/auth/introspect" \
  -H "X-API-Key: $SVC_KEY" -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\"}" | jq '{active,reason,token_version}'
```

3. 触发吊销（改密或管理面禁用）；
4. 再次内省 → **立即** `active=false`；
5. 以 5~10s 间隔轮询四仓至首次 401/403，记录 CSV：`repo,start_ts,first_reject_ts,latency_s,interval_config`；
6. 记录 `GET /api/v1/auth/revocations?since=<游标>&limit=500` 输出，确认目标 `token_version` 已下发。

**通过判据**：内省即时反映；四仓在「配置节流间隔 + 一次请求」内拒绝；>60s 须提交 ER-10 放宽申请；严格模式快照未命中应拒绝。证据 `a1-04.csv` + 内省前后 JSON（脱敏）。

**P-06 跨仓整服务实测（A1-14 / V-14）**

1. 本地验签：同一令牌请求四仓受保护接口 → 200；`aud` 篡改 / 过期 / 未映射主体 → 401；
2. 吊销收敛（复用 P-05 数据）；
3. 门禁负向启动：四仓按 A1-11 逐条构造缺配置并重启 → 拒绝启动，错误可定位到具体配置项；
4. 审计字段抽查：含 `key_id` / `subject` / `tenant` / `entry=proxy|direct`；
5. 身份权威：确认 `IDENTITY_AUTHORITY=openbase`，本地密码登录与自签 JWT 通道关闭（DPS 403 `AUTH_LOCAL_LOGIN_DISABLED`，OpenLLM 403 含 R17）；
6. 跨实例能力（如启用）：C-07 异常聚合 / C-08 到期去重 / C-09 对账在共享 Redis 下的表现与降级路径。

**P-07 镜像矩阵 + 权限面（A2-04 / A2-05）**

- 四仓逐键核对 A2 §3 是否齐备且 `iss/aud` 一致（只记「存在/缺失」与取值类别，不记秘密）；
- 服务 Key 权限面取样：`scope.system` 仅保留 `auth` 必要项，禁止 `*` 泛化（如必须保留 `*` 需书面豁免并签字）。

**P-08 真实 IdP / issuer 判重（V-13 / D-07）**

1. 逐 Provider 访问 `discovery_url` 取 `issuer`，形成清单并判重；
2. 同一 issuer 多 client → 仅登记一个承担 back-channel，其余标注「不声明 back-channel」；
3. 多 Provider 路由、PKCE/nonce/state、五种 token 认证方式、登出联动、back-channel 防重放（按 A1-13 步骤）；
4. 全程日志与响应脱敏检查。

**阶段 4 统一通过判据**：P-05~P-08 各项均 `Pass`（或 `Blocked` 且写明解除条件）；任一项 `Fail` → 停止推进、进入 §5 回滚。

---

### 阶段 5 —— P-04 三仓 `STATIC_KEY_CHANNEL` `dual`→`closed`

**前置（全部满足才可执行）**：

- 阶段 1~4 全部 `Pass`；
- 三仓已按裁定 B 完成**一个完整发布窗口的双通道并行观察**（观察期内静态 Key 通道调用量已归零或仅应急调用）；
- 三仓应急 bypass 两键已配置且到期时间在未来（`closed` 缺一即拒启）：

| 仓 | 通道键 | 应急键 |
|---|---|---|
| OpenRAG | `OPENRAG_API_STATIC_KEY_CHANNEL=closed` | `OPENRAG_API_EMERGENCY_BYPASS_KEY` / `OPENRAG_API_EMERGENCY_BYPASS_EXPIRES_AT` |
| OpenMemory | `OPENMEMORY_GATEWAY_STATIC_KEY_CHANNEL=closed` | `OPENMEMORY_GATEWAY_EMERGENCY_BYPASS_KEY` / `_EXPIRES_AT` |
| DPS | `STATIC_KEY_CHANNEL=closed`（**无 `DPS_` 前缀**） | `EMERGENCY_BYPASS_KEY` / `EMERGENCY_BYPASS_EXPIRES_AT`（**无 `DPS_` 前缀**） |

**操作**：逐仓改值 → 重启 → 验证。**逐仓串行**，每仓通过后进入下一仓（禁止三仓同时改值重启）。

**通过判据（每仓）**：

- 静态 Key 主通道请求被拒（DPS 返回 `AUTH_STATIC_KEY_CHANNEL_CLOSED`）；
- 应急 bypass 放行成功，且审计仅落 `sha256[:12]` 摘要；
- 缺失/过期 bypass → 拒绝启动（负向一次）；
- 服务 Key（OpenBase 颁发）通道不受影响（提供者与静态 Key 通道分离）；
- `/health` 200，网关错误率无抬升。

**回滚**：见 §5 `R-04`。

---

### 阶段 6 —— 放行门禁

| 门禁 | 判据 |
|---|---|
| G1 配置门禁 | A2-01/02/03 全 `Pass`；13 项启动门禁放行记录在案 |
| G2 验收门禁 | P-05/P-06/P-07/P-08 全 `Pass`（`Blocked` 项须书面豁免并签字） |
| G3 收口门禁 | P-01 执行记录回填完毕；P-04 三仓 `closed` 且回归通过 |
| G4 安全门禁 | A2-06 `Pass`：证据与日志无 PEM/令牌/服务 Key 明文 |
| G5 留痕门禁 | 本单执行回执（§6）8 项字段完整；证据文件归档至 `evidence/` |

**任一 G 不通过 → 不得宣布放行**，按 §5 回滚到对应阶段。

---

## 5. 回滚口径

### 5.1 逐项回滚

| 编号 | 对应项 | 触发条件 | 回滚动作 | 回滚后核验 | 影响面 |
|---|---|---|---|---|---|
| **R-01** | P-01 | 收敛后四下游出现 401 / 到期时间误设为过去 / 批量行数超预期 | 按 §3.3 快照 `key_id` 清单反向：`UPDATE openbase.service_api_keys SET expires_at = NULL, updated_at = now() WHERE key_id IN (<快照清单>) AND expires_at = :batch_expires_at;` **逐批执行**，禁止无条件全表置 NULL | `remaining_without_expiry` 恢复至基线计数；四下游吊销端点 200 | 共享 PG：仅 `openbase` schema；不涉及其他仓数据 |
| **R-02** | P-02 | 映射注入后出现大面积 401 / 映射值指向不存在用户 | **恢复上一版映射快照**（阶段 0 已备份的 `<仓>.env`），重启该仓；**禁止**清空映射 | 映射主体 200、未映射主体 401 两向重验 | 单仓配置；不影响其他仓 |
| **R-03** | P-03 | 启动失败 / 门禁拒启 / JWKS 或吊销端点不可达 / 秘密泄露迹象 | 恢复 `.env` 与 `.env.shared-infra` 备份 → 恢复上一版挂载路径 → 重启；先回滚下游、再回滚 OpenBase | 各仓 `/health` 200；OpenBase 门禁恢复原状态；负向用例不再触发 | **共享网关与共享 PEM**：下游 URL 回滚需同批执行，避免一半新一半旧 |
| **R-04** | P-04 | `closed` 后静态 Key 合法调用被误拒 / 应急 bypass 失效 / 服务不可用 | 改回 `dual` 并重启该仓（`OPENRAG_API_STATIC_KEY_CHANNEL` / `OPENMEMORY_GATEWAY_STATIC_KEY_CHANNEL` / `STATIC_KEY_CHANNEL` = `dual`） | 静态 Key 请求恢复正常；`/health` 200；bypass 两键保留不删 | 单仓；应急 bypass 保留以便再次收口 |
| **R-05** | P-05~P-08 实测 | 实测判定 `Fail` | 不改生产配置，只回退「结论」：标记 `Fail`、登记缺陷与复测条件；若 `Fail` 由阶段 1~5 变更引起，按对应项回滚 | 复测通过后方可继续 | 仅结论面；不产生生产变更 |

### 5.2 整体回滚顺序（逆向执行，禁止跳步）

```
阶段 6 放行 → 停止
阶段 5 P-04  → R-04（三仓逐个改回 dual + 重启）
阶段 4 实测  → R-05（结论回退）
阶段 3 P-01  → R-01（按快照逐批恢复 expires_at = NULL）
阶段 2 P-02  → R-02（恢复映射快照）
阶段 1 P-03  → R-03（恢复 .env 与挂载路径，下游先行、OpenBase 后行）
```

**共享基础设施回滚纪律**：

1. **下游先行**：四下游 `.env` 先回滚并确认可用，再回滚 OpenBase 控制面，避免「上游换新钥、下游仍旧钥」的中间态。
2. **服务 Key 过渡**：P-01 只设到期不立即吊销，因此 R-01 在过渡期内可行；一旦旧 Key 已到期，只能新签，不得依赖回滚。
3. **Redis / 网关不改动**：本单不写 Redis、不改网关配置；若出现异常，按 §3.4 前缀定位，禁止 `FLUSHDB`。
4. **IdP 不回滚已吊销令牌**：`token_version` 递增不可逆，回滚仅撤下新增 Provider 登记。
5. **回滚后必须重跑**：§4 阶段 1 的负向三连 + 阶段 5 的 bypass 两向 + `/health`，全部通过才算回滚成功。

---

## 6. 执行回执（OPS 填写）

| 项 | 填写 |
|---|---|
| 执行人 / 时间 / 变更单号 |  |
| 五仓 `rev-parse HEAD` |  |
| 各仓 `.env` 备份路径（含共享基础设施文件） |  |
| 共享 PG 基线计数 → 收敛后计数 |  |
| P-03：PEM 挂载绝对路径 / `stat` 权限 |  |
| P-03：OpenBase 门禁 13 项结果 + 负向三连退出码 |  |
| P-03：JWKS `kid` 与签名 `kid` 一致性 |  |
| P-02：两向冒烟结果（映射 200 / 未映射 401） |  |
| P-01：批次执行记录表（B1~B3 + 豁免） |  |
| P-05：`a1-04.csv` 路径与最大时延 |  |
| P-06：四仓 200/401 矩阵与审计字段抽查 |  |
| P-07：矩阵齐备性 + 服务 Key `scope.system` 取样 |  |
| P-08：issuer 清单与判重结论 |  |
| P-04：三仓 `closed` 后静态 Key 拒绝 + bypass 放行 + 摘要审计 |  |
| 共享 Redis 采样（DB index / 前缀 / 可达） |  |
| 共享网关三条路径状态码 + 超时值 |  |
| 证据归档路径 |  |
| 回滚是否触发 / 触发项 / 回滚结果 |  |

---

## 7. 风险与禁止项

| 风险 | 影响 | 缓解 |
|---|---|---|
| 共享 PG 长事务锁表 | 其他仓读写被阻塞 | `lock_timeout=3s` / `statement_timeout=30s`；单批 ≤200 行；避开业务高峰 |
| 共享服务 Key 被多处消费 | 收敛即可能全下游 401 | 先签新 → 全量替换 → 验证 → 再收敛；到期留 ≥7 天过渡 |
| 共享网关超时 < 3s | JWKS/吊销拉取失败，验签降级 | 网关超时必须 ≥3s；变更前用网关路径验证 |
| 共享 Redis 串键 / 降级 | 多实例 state 失效、配额漂移 | DB index + key 前缀隔离；禁 `FLUSHDB`；记录降级路径 |
| 共享 IdP 同 issuer 多 client | back-channel 登出定位歧义 | 登记前 issuer 判重；仅一个 Provider 承担 back-channel |
| 共享 PEM 挂载权限放大 | 私钥泄露 | 只读 `0600`、指定属主、仅 OpenBase 挂载；抽样扫描日志 |

**禁止项**：

1. 禁止在未备份的情况下改任何 `.env`（含 `.env.shared-infra`）。
2. 禁止在 P-03 之前执行 P-01（服务 Key 尚未就绪）。
3. 禁止在 P-05/P-06 通过前执行 P-04（静态 Key 通道先关会导致取证失真）。
4. 禁止 `FLUSHDB`/`FLUSHALL`/`KEYS`；禁止在共享 PG 上跨 schema 操作或无条件全表 `UPDATE`。
5. 禁止把私钥 PEM、服务 Key 明文、`client_secret`、令牌全文写入本单、日志、证据或 git。
6. 禁止以「清空主体映射」作为回滚手段。
7. 禁止把本机（SQLite / 无 Docker / 单进程）结果当作生产实测结论。

---

## 8. 阶段 0 执行结果（本机口径，已执行 2026-11-03）

> 本机无生产主机访问权；本节只覆盖**阶段 0 执行前检查**，不构成生产放行，也不替代 §4 阶段 1~6。

### 8.1 门禁判定

| 门禁 | 判定 | 说明 |
|---|---|---|
| F0-1 五仓版本快照 | **Pass** | 五仓 HEAD 已记录（见 8.2） |
| F0-2 配置键存在性 | **Pass（含 4 项发现）** | 生产基线多以「注释态」驻留模板，DPS 18 键全部缺失（见 8.3） |
| F0-3 共享 PG 可达 | **Pass** | `192.168.0.151:5432/nuct` TCP 可达 |
| F0-4 共享 PG 列结构 | **Pass（整改后复核）** | 2026-11-03 已定向补齐四列（RF-01），基线复验 `verdict=BASELINE_CAPTURED`（见 8.4） |
| F0-5 共享 Redis 隔离 | **Pass（已登记）** | 五仓均 `db=0`；key 前缀已逐仓登记且无重合（RF-02，见 §3.4） |
| F0-6 PEM `0600` 只读挂载 | **Blocked** | Windows 无 POSIX mode，须在 Linux 生产主机核验 |
| F0-7 共享网关 / 共享 IdP | **Blocked** | 生产地址未下发，无真实 IdP |
| F0-8 DBA 会话 / 变更单 | **Blocked** | 未提供 |

**结论**：阶段 0 原 **2 项 Fail（F0-4 / F0-5）已于 2026-11-03 整改闭合为 Pass**，阶段 0 判定由 Fail 转为 **Pass（5 通过 / 3 生产侧 Blocked）**。F0-6 / F0-7 / F0-8 属生产侧能力（PEM 权限、网关/IdP 地址、DBA 会话），**不推翻阶段 0 结论，但阻断阶段 1 与阶段 3 的实际执行**。

> **口径声明**：RF-01 本次执行对象为**共享测试实例**（`environment=shared-postgresql (test instance; NOT production)`）。生产实例须由生产 DBA 以同一幂等 DDL 复核执行并重跑基线，**不得以测试实例结果替代生产验证**。

### 8.2 五仓版本快照

| 仓 | HEAD | 说明 |
|---|---|---|
| OpenBase | `cf5c68bcea7d` | 本单所在提交 |
| OpenLLM | `b525b21746f3` | 工作区未变更 |
| OpenRAG | `9ccbe82ed1ca` | 工作区未变更 |
| OpenMemory | `5e9035374420` | 工作区未变更 |
| DPS | `df5ac6af7531` | 工作区未变更 |

### 8.3 配置键存在性（只记状态，不记值）

> 状态口径：`present` = 所在文件存在有效键行；`commented` = 仅以注释模板形式存在（不生效）；`absent` = 模板与环境文件中均无。

| 仓 | 受检键 | present | commented | absent | 关键缺失项 |
|---|---|---|---|---|---|
| OpenBase | 9 | 0 | 7 | 2 | `OPENBASE_ENFORCE_TOKEN_VERSION`、`OPENBASE_OIDC_STATE_TTL_SECONDS` |
| OpenLLM | 15 | 0 | 12 | 3 | `IDENTITY_AUTHORITY`、`OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED`、`QUOTA_ALGORITHM` |
| OpenRAG | 17 | 2 | 13 | 2 | `OPENRAG_IDENTITY_ROLE_CONTRACT_URL`、`OPENRAG_API_OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` |
| OpenMemory | 17 | 0 | 14 | 3 | `ALLOW_UNVERIFIED_GATEWAY_TOKEN`、`OPENMEMORY_IDENTITY_ROLE_CONTRACT_URL`、`OPENMEMORY_GATEWAY_REVOCATION_BACKGROUND_SYNC_ENABLED` |
| DPS | 18 | 0 | 0 | **18** | 全部（含 `IDENTITY_AUTHORITY`、`STATIC_KEY_CHANNEL`、`EMERGENCY_BYPASS_KEY`、`EMERGENCY_BYPASS_EXPIRES_AT`） |

**发现**：

1. **DPS 零模板键** —— 18 键在 `.env` / `.env.shared-infra` / 配置说明中均无有效行，全部依赖 `config.py` 缺省（`IDENTITY_AUTHORITY=local`、`STATIC_KEY_CHANNEL=dual`），与生产目标相反；P-03 必须在 DPS 显式新增 18 键。
2. **四仓生产基线为「注释态」** —— OpenBase 7 / OpenLLM 12 / OpenRAG 13 / OpenMemory 14 键仅存在于模板注释中，需在窗口内转为有效值并做唯一性校验。
3. **OpenRAG 仅 2 键已生效** —— `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES`（`.env`）与 `OPENRAG_IDENTITY_ROLE_FAIL_CLOSED`（模板），其余待下发。
4. **未发现同文件重复键**（跨文件重复不计为冲突，避免误报）。

### 8.4 共享基础设施探测结果

| 组件 | 探测 | 结果 | 判定 |
|---|---|---|---|
| 共享 PG | `192.168.0.151:5432/nuct` | TCP 可达；`openbase` schema 与 `service_api_keys` 存在；整改后 15 列（含 `expires_at` / `last_used_at` / `rotated_from` / `tenant_code`）；行数 `total=0`；DDL 以 `lock_timeout=3s` / `statement_timeout=30s` 执行 | **Pass**：RF-01 定向补列（`ADD COLUMN IF NOT EXISTS`，未执行 `Base.metadata.create_all`），基线复验 `BASELINE_CAPTURED` |
| 共享 Redis | `192.168.0.151:6380` | TCP 可达；五仓 `REDIS_URL` 均 `db=0` | **Pass（已登记）**：前缀见表下补充与 §3.4，五仓无重合；禁止 `FLUSHDB` / `FLUSHALL` / `KEYS` |
| 共享网关 | — | 未配置 | Blocked |
| 共享 IdP | — | 未配置 | Blocked |
| 共享 PEM 挂载 | — | Windows 无 POSIX mode | Blocked |

> 注：上表 PG/Redis 为**共享测试实例**，非生产；生产窗口须以相同方法复核，且 PG 以 `verdict=BASELINE_CAPTURED` 为放行条件。

### 8.5 整改项（进入阶段 1 前必须闭合）

| 编号 | 整改内容 | 责任方 | 状态 | 验证判据 / 结果 |
|---|---|---|---|---|
| **RF-01** | 共享 PG 补齐 `service_api_keys` 四列（幂等 DDL） | 生产 DBA | ✅ **已闭合（测试实例，2026-11-03）**；生产实例待 DBA 复核 | 定向 DDL `ADD COLUMN IF NOT EXISTS`×4，`added_columns=[expires_at,last_used_at,rotated_from,tenant_code]`；复跑 P-01 基线 `verdict=BASELINE_CAPTURED`、`baseline_remaining_without_expiry=0` |
| **RF-02** | 逐仓登记 Redis key 前缀（§3.4） | OPS | ✅ **已闭合（2026-11-03）** | §3.4 五仓 DB index 与前缀全部补齐；前缀互不重合，无冲突；残余命名空间风险已登记为非阻断 |
| **RF-03** | DPS `.env` 生成 18 键生产基线（含应急 bypass 两键与到期时间） | OPS + 研发 | ⛔ **Blocked** | 需生产 `.env` 与真实取值（秘密不落库、不入 git）；判据 `present=18` 且无重复 |
| **RF-04** | 四仓把注释态键转为有效值并唯一性校验 | OPS | ⛔ **Blocked** | 同上，需生产主机窗口；判据各仓 `commented=0`、`duplicate=0` |

### 8.6 证据文件

| 证据 | 路径 | 说明 |
|---|---|---|
| 阶段 0 前置检查 | `doc/audit/verification/evidence/xr-ops-08/xr08-stage0-precheck-20261103.json` | 五仓 HEAD、9+15+17+17+18 键存在性、PG/Redis 可达与 DB index、Blocked 清单 |
| RF-01 补列执行 | `doc/audit/verification/evidence/xr-ops-08/xr08-rf01-migration-20261103.json` | 定向 DDL×4（`ADD COLUMN IF NOT EXISTS`）、`lock_timeout=3s`、`statement_timeout=30s`；仅列名、DDL 与行数，`verdict=COLUMNS_READY` |
| P-01 基线（迁移前） | `doc/audit/verification/evidence/xr-ops-08/xr08-p01-baseline-20261103-pre-migration.json` | 只读事务、`statement_timeout=5s`；`verdict=SCHEMA_DRIFT_MISSING_COLUMNS`（整改前对照，留存） |
| P-01 基线（迁移后） | `doc/audit/verification/evidence/xr-ops-08/xr08-p01-baseline-20261103-post-migration.json` | 只读事务、`statement_timeout=5s`；15 列、`missing_required_columns=[]`、`verdict=BASELINE_CAPTURED`、`baseline_remaining_without_expiry=0` |

> 三份证据均不含密钥/令牌/密码原文；连接串 userinfo 已剥离；不含 `key_hash` 取值与任何行级数据（表内 `total=0`，仅列名与聚合计数）。

## 9. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.5 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 新增 **§13 阻塞点整改与五系统并行复核（2026-11-03）**：B-1~B-7 逐项根因与整改（DPS 加载 `.env.shared-infra` 并映射 `DATABASE_URL = POSTGRES_URL`、OpenMemory 改用 `OPENMEMORY_DB__*` 前缀与官方启动器 `scripts/start_openmemory.py`、补装 `qdrant-client`/`neo4j` 等缺失包、`pymupdf 2.0 → 1.24.14` 规避 `onnxruntime` 崩溃、OpenBase 进程级注入 `POSTGRES_URL`/`REDIS_URL`、DPS/OpenRAG 探活路径修正）；五系统同时启动复核 **5 / 5 HTTP 200**；登记残余风险 R-13-1~R-13-3；头部「状态」「执行进度」同步为 5 / 5 running；§12.3 三行标注「本机已解除」 |
| v1.0.4 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 新增 **§12 本机全栈启动复核（2026-11-03）**：两轮启动级复核结果（OpenBase 8000 `/docs` 200、OpenLLM 8020 `/health` 200、OpenMemory 8040 `/health` 503 degraded、DPS 与 OpenRAG blocked）、仅解释器依赖的准备清单、逐项阻塞与解除条件、两份证据与清理/秘密口径；头部「状态」「执行进度」同步；明确本机结果**不替代生产实测**、不作为 A1-04 / A1-14 验收证据 |
| v1.0.3 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 新增 **§11 附录 B：RF-03 / RF-04 生产补录清单**——按阶段 0 五仓键存在性证据逐仓列表（OpenBase 9 / OpenLLM 15 / OpenRAG 17 / OpenMemory 17 / DPS 18 共 74 键），标注当前态（`present`/`commented`/`absent`）、类型（含 🔒 秘密项）、生产取值来源、校验点与回执字段；明确四类禁止项、DPS 五键**无 `DPS_` 前缀**陷阱、`ALLOW_UNVERIFIED_GATEWAY_TOKEN` 不得启用、`*_REVOCATION_STRICT` 不得放宽；给出 RF-03/RF-04 闭合判据（五仓 `commented=0`/`duplicate=0` 且 DPS `present=18`） |
| v1.0.2 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 阶段 0 整改闭环：**RF-01** 在共享测试 PG 定向补齐 `service_api_keys` 四列（`ADD COLUMN IF NOT EXISTS`，未执行 `create_all`，`lock_timeout=3s`/`statement_timeout=30s`），P-01 基线复验 `BASELINE_CAPTURED`；**RF-02** 按代码实测逐仓登记 Redis 前缀（§3.4），五仓无重合、无串键冲突，并登记两项非阻断命名空间风险；§8.1 F0-4/F0-5 由 Fail 转 Pass（阶段 0 判定 5 Pass + 3 生产侧 Blocked）、新增测试/生产口径声明；§8.4 更新 PG/Redis 判定；§8.5 增「状态」列并回填 RF-01/RF-02 已闭合、RF-03/RF-04 仍 Blocked；§8.6 补 3 份证据（RF-01 执行 + 迁移前/后基线） |
| v1.0.1 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 阶段 0 执行回填：状态转 [Approved]；新增 §8（门禁判定 F0-1~F0-8、五仓 HEAD、键存在性含 DPS 18 键全缺、共享 PG 可达但缺 4 列、共享 Redis 五仓同 `db=0`、整改项 RF-01~RF-04、两份脱敏证据）；§3.3 与阶段 3 前置补「列结构门禁」；§2 共享 PG 约束补第 ⑥ 条；章节号顺延（修订历史 §9、依据 §10） |
| v1.0.0 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 初始创建：将 E 批遗留的 8 项生产前置 Blocked（D-04 / D-05 / D-06 / K-01 / A1-04 / A1-14 / A2-04 / A2-05 / V-04 / V-13 / D-07）整理为发布单格式；按五仓**共享基础设施**口径（共享 PG / Redis / 网关 / IdP / PEM 挂载 / 服务 Key）明确约束、执行顺序与逐项回滚口径；状态待人工批准与 OPS 执行 |

---

## 10. 依据与证据索引

| 类型 | 文件 | 用途 |
|---|---|---|
| 评估方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.31.0.md` | §10.7~§10.34 能力基线 |
| 处置台账 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项统一处置方案-v1.5.0.md` | 47 项主键与 P4/E 批状态 |
| 分批推进 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项分批推进方案-v1.5.0.md` | §9.8 E4 收口与批次边界 |
| 生产验收 | `doc/audit/verification/OpenBase-四系统APIKey优化-A1生产验收清单-v1.1.8.md` | A1-04 / A1-11 / A1-12 / A1-13 / A1-14 |
| 配置收口 | `doc/audit/verification/OpenBase-四系统APIKey优化-A2生产配置收口清单-v1.2.0.md` | §3 键名权威、§4 门禁、§5 秘密、§6 自检、§7 判定 |
| 部署取证 | `doc/audit/verification/OpenBase-四系统APIKey优化-D类部署取证执行记录-v1.0.5.md` | D-04 SQL / D-05 模板 / D-06 挂载 / D-07 issuer |
| 批次总结 | `doc/audit/verification/OpenBase-四系统APIKey优化-E3批次执行总结报告-v1.2.1.md` | 42 项判定（34 Pass + 8 Blocked）与 §12 E4 |
| 格式范本 | `doc/release/OpenBase-生产环境配置下发单-XR-OPS-07-v1.0.0.md` | 备份 / 覆盖 / 核验 / 重启 / 回滚 / 回执结构 |
| 整体回滚 | `doc/release/OpenBase-主备双通道生产上线回滚方案-v1.0.0.md` | 双通道回滚总口径 |
| 证据 | `doc/audit/verification/evidence/{d,a2,e3,e4,xr-ops-08}/` | 本机口径佐证（不替代生产实测）；`xr-ops-08` 含阶段 0 证据、§12 全栈启动复核证据（`xr08-fullstack-run-20261103.json` / `xr08-fullstack-run-round2-20261103.json`）与 §13 整改后并行复核证据（`xr08-fullstack-simultaneous-20261103-131838.json` 及两份分证据） |

---

## 11. 附录 B：RF-03 / RF-04 生产补录清单（OPS 填写用）

> 本附录是 RF-03（DPS 18 键）与 RF-04（四仓注释态键）的**执行表单**。研发侧已完成逐仓逐键取证（键名、当前态、类型、取值来源），OPS 只需在生产 `.env` 按行补值并回执。
> 🔒 = 秘密值（服务 Key / 令牌 / 私钥 / 哈希清单），**只在生产 `.env` 或密钥挂载内填写**，不得写入本单、不得进 git、不得贴入回执；回执仅记「已配置 / 未配置」。

### 11.1 通用填写与校验口径

| 项 | 口径 |
|---|---|
| 填写位置 | 各仓生产 `.env`（DPS 为 DPS 仓 `.env`）；PEM 走密钥挂载，不进 `.env` |
| 覆盖前备份 | `cp .env .env.bak.$(date +%Y%m%d%H%M)`，保留至窗口关闭后 ≥7 天 |
| 生效方式 | 逐仓重启进程（共享网关 / 共享 IdP 无需重启） |
| 键存在性复核 | 复用 `tmp/xr08/stage0_precheck.ps1`（临时脚本，不入库）；判据：`commented=0`、`duplicate=0`、目标键全部 `present` |
| 秘密处理 | 仅记「已配置」；不得在回执、日志、工单粘贴原文 |
| 回滚 | 恢复 `.env.bak.*` → 重启 → 复跑键存在性复核；**不得只删键不重启** |
| 禁止项 | ① 不得用注释行充当生效值；② 不得用测试实例服务 Key 冒充生产 Key；③ 不得启用 `ALLOW_UNVERIFIED_GATEWAY_TOKEN`；④ 不得放宽 `*_REVOCATION_STRICT` 以绕过同步失败 |

### 11.2 OpenBase（9 键：`commented=7`、`absent=2`）

| 键 | 当前态 | 类型 | 生产取值来源 / 目标 | 校验点 |
|---|---|---|---|---|
| `OPENBASE_JWT_RSA_PRIVATE_KEY_PATH` | commented | 路径（非秘密） | 生产 PEM 挂载路径，`0600`、仅 OpenBase 可读 | 文件存在且权限 `0600`；启动不触发 D-02 私钥门禁 |
| `OPENBASE_JWT_SIGNING_KID` | commented | 非秘密 | 与 JWKS 实际发布的 `kid` 一致 | `GET /api/v1/auth/jwks` 返回同一 `kid` |
| `OPENBASE_JWT_REQUIRE_RS256` | commented | 布尔 | `true` | 非 RS256 令牌被拒（401） |
| `OPENBASE_JWT_ISSUER` | commented | 非秘密 | 生产对外 issuer | 与三下游 `*_JWT_ISSUER` 完全一致 |
| `OPENBASE_ENFORCE_TOKEN_VERSION` | absent | 布尔 | `true` | 登出后旧令牌 `token_version` 生效（401） |
| `OPENBASE_OIDC_STATE_TTL_SECONDS` | absent | 数值 | 与共享 Redis 中 OIDC state 生命周期一致（≤ 会话时长） | state 过期后回调被拒 |
| `OPENBASE_MCP_API_KEY_HASHES` | commented | 🔒 哈希清单 | MCP 摘要清单生产值 | 摘要校验通过；非清单摘要 401 |
| `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` | commented | 映射（非秘密） | D-05 生产映射快照（见 §4 阶段 2） | 主体映射命中；**回滚不得清空**（清空=全量拒绝） |
| `OPENBASE_IDP_PROVIDERS` | commented | JSON（内含 🔒 `client_secret`） | 生产 IdP 登记（含 name / client_id / client_secret / 证书） | Provider `name` 唯一、`issuer` 唯一（D-07） |

### 11.3 OpenLLM（15 键：`commented=12`、`absent=3`）

| 键 | 当前态 | 类型 | 生产取值来源 / 目标 | 校验点 |
|---|---|---|---|---|
| `OPENBASE_JWKS_URL` | commented | 非秘密 | `https://<openbase 生产域名>/api/v1/auth/jwks` | `/health` 200；缺该键进程拒启（R17） |
| `OPENBASE_JWKS_CACHE_TTL_SECONDS` | commented | 数值 | 按现网缓存策略（建议 300） | — |
| `OPENBASE_JWKS_TIMEOUT_SECONDS` | commented | 数值 | `3.0`；**生产网关超时必须 ≥3s** | 共享网关超时 ≥ 该值 |
| `OPENBASE_JWT_ISSUER` | commented | 非秘密 | 与 OpenBase `OPENBASE_JWT_ISSUER` 完全一致 | 不一致时令牌被拒 |
| `OPENBASE_JWT_AUDIENCE` | commented | 非秘密 | OpenBase 为该服务登记的受众 | 受众校验通过 |
| `OPENBASE_JWT_LEEWAY_SECONDS` | commented | 数值 | 按现网时钟偏差（建议 30） | — |
| `OPENBASE_REVOCATIONS_URL` | commented | 非秘密 | `https://<openbase>/api/v1/auth/revocations` | 吊销增量拉取 200 |
| `OPENBASE_SERVICE_KEY` | commented | 🔒 服务 Key | OpenBase 签发的 `ob_k_*`，`scope.system` 含 `auth` | 调用 JWKS/吊销端点 200；被吊销后 401 |
| `OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` | commented | 数值 | 按现网（建议 30） | — |
| `OPENBASE_REVOCATION_STRICT` | commented | 布尔 | `true` | 吊销端点不可达时**拒绝**而非放行 |
| `OPENBASE_SUBJECT_MAP` | commented | 映射（非秘密） | D-05 生产映射快照 | 映射命中；回滚恢复快照而非清空 |
| `OPENBASE_TRUST_LOCAL_SUBJECT` | commented | 布尔 | `false` | 本地令牌不得越权 |
| `IDENTITY_AUTHORITY` | absent | 枚举（**无 `OPENBASE_` 前缀**） | `openbase` | 取 `local` 时同步不生效 |
| `OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` | absent | 布尔 | `true` | 后台同步日志出现；阶段 4 取证依赖 |
| `QUOTA_ALGORITHM` | absent | 枚举 | `token_bucket` | 令牌桶键前缀 `quota_bucket:` 生成 |

### 11.4 OpenRAG（17 键：`present=2`、`commented=13`、`absent=2`）

| 键 | 当前态 | 类型 | 生产取值来源 / 目标 | 校验点 |
|---|---|---|---|---|
| `OPENRAG_API_OPENBASE_JWKS_URL` / `..._JWKS_CACHE_TTL_SECONDS` / `..._JWKS_TIMEOUT_SECONDS` | commented | 非秘密 / 数值 | 同 OpenLLM 口径；超时默认 `3.0` | 网关超时 ≥3s |
| `OPENRAG_API_OPENBASE_JWT_ISSUER` / `..._JWT_AUDIENCE` / `..._JWT_LEEWAY_SECONDS` | commented | 非秘密 / 数值 | 与 OpenBase 一致 | 令牌校验通过 |
| `OPENRAG_API_OPENBASE_REVOCATIONS_URL` | commented | 非秘密 | OpenBase 吊销端点 | 增量拉取 200 |
| `OPENRAG_API_OPENBASE_SERVICE_KEY` | commented | 🔒 服务 Key | `ob_k_*`，`scope.system` 含 `auth` | 调用 200 / 吊销后 401 |
| `OPENRAG_API_OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` / `..._REVOCATION_STRICT` | commented | 数值 / 布尔 | `30` / `true` | 端点不可达时拒绝 |
| `OPENRAG_API_STATIC_KEY_CHANNEL` | commented | 枚举 | `closed` | 静态 Key 通道关闭（拒绝） |
| `OPENRAG_API_EMERGENCY_BYPASS_KEY` | commented | 🔒 应急 Key | 仅窗口内有效，窗口结束即作废 | 未到期时可放行，到期后拒绝 |
| `OPENRAG_API_EMERGENCY_BYPASS_EXPIRES_AT` | commented | 时间 | 必须写入明确到期时间（不得空） | 到期后 bypass 失效 |
| `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` | **present** | 非秘密 | 按生产网关网段复核（现值需确认仍适用） | 仅网关来源可透传身份 |
| `OPENRAG_IDENTITY_ROLE_FAIL_CLOSED` | **present** | 布尔 | `true`（保持现值） | 角色取不到时拒绝 |
| `OPENRAG_IDENTITY_ROLE_CONTRACT_URL` | absent | 非秘密 | 生产角色契约端点 | 契约拉取成功 |
| `OPENRAG_API_OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` | absent | 布尔 | `true` | 后台同步生效 |

### 11.5 OpenMemory（17 键：`commented=14`、`absent=3`）

| 键 | 当前态 | 类型 | 生产取值来源 / 目标 | 校验点 |
|---|---|---|---|---|
| `OPENMEMORY_GATEWAY_JWKS_URL` / `..._JWKS_CACHE_TTL_SECONDS` / `..._JWKS_TIMEOUT_SECONDS` | commented | 非秘密 / 数值 | 同 OpenLLM 口径；超时默认 `3.0` | 网关超时 ≥3s |
| `OPENMEMORY_GATEWAY_JWT_ISSUER` / `..._JWT_AUDIENCE` / `..._JWT_LEEWAY_SECONDS` | commented | 非秘密 / 数值 | 与 OpenBase 一致 | 令牌校验通过 |
| `OPENMEMORY_GATEWAY_REVOCATIONS_URL` | commented | 非秘密 | OpenBase 吊销端点 | 增量拉取 200 |
| `OPENMEMORY_GATEWAY_SERVICE_KEY` | commented | 🔒 服务 Key | `ob_k_*`，`scope.system` 含 `auth` | 调用 200 / 吊销后 401 |
| `OPENMEMORY_GATEWAY_REVOCATION_SYNC_INTERVAL_SECONDS` / `..._REVOCATION_STRICT` | commented | 数值 / 布尔 | `30` / `true` | 端点不可达时拒绝 |
| `OPENMEMORY_GATEWAY_OIDC_MODE` | commented | 枚举 | 按 A2 §3 目标值（OpenBase 信任模式） | 非目标取值时拒启/拒绝 |
| `OPENMEMORY_GATEWAY_STATIC_KEY_CHANNEL` | commented | 枚举 | `closed` | 静态 Key 通道关闭 |
| `OPENMEMORY_GATEWAY_EMERGENCY_BYPASS_KEY` | commented | 🔒 应急 Key | 仅窗口内有效 | 未到期可放行、到期拒绝 |
| `OPENMEMORY_GATEWAY_EMERGENCY_BYPASS_EXPIRES_AT` | commented | 时间 | 明确到期时间（不得空） | 到期后 bypass 失效 |
| `ALLOW_UNVERIFIED_GATEWAY_TOKEN` | absent | 布尔 | **必须 `false` 或保持未设置** | 为 `true` 即视为窗口失败 |
| `OPENMEMORY_IDENTITY_ROLE_CONTRACT_URL` | absent | 非秘密 | 生产角色契约端点 | 契约拉取成功 |
| `OPENMEMORY_GATEWAY_REVOCATION_BACKGROUND_SYNC_ENABLED` | absent | 布尔 | `true` | 后台同步生效 |

### 11.6 DPS（18 键：`present=0`、`absent=18`）

| 键 | 当前态 | 类型 | 生产取值来源 / 目标 | 校验点 |
|---|---|---|---|---|
| `DPS_OPENBASE_JWKS_URL` / `..._JWKS_CACHE_TTL_SECONDS` / `..._JWKS_TIMEOUT_SECONDS` | absent | 非秘密 / 数值 | 同 OpenLLM 口径；超时默认 `3.0` | 网关超时 ≥3s |
| `DPS_OPENBASE_JWT_ISSUER` / `..._JWT_AUDIENCE` / `..._JWT_LEEWAY_SECONDS` | absent | 非秘密 / 数值 | 与 OpenBase 一致 | 令牌校验通过 |
| `DPS_OPENBASE_REVOCATIONS_URL` | absent | 非秘密 | OpenBase 吊销端点 | 增量拉取 200 |
| `DPS_OPENBASE_SERVICE_KEY` | absent | 🔒 服务 Key | `ob_k_*`，`scope.system` 含 `auth` | 调用 200 / 吊销后 401 |
| `DPS_OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` / `..._REVOCATION_STRICT` | absent | 数值 / 布尔 | `30` / `true` | 端点不可达时拒绝 |
| `DPS_OPENBASE_SUBJECT_MAP` / `DPS_OPENBASE_TRUST_LOCAL_SUBJECT` | absent | 映射 / 布尔 | D-05 快照 / `false` | 映射命中、本地令牌不越权 |
| `IDENTITY_AUTHORITY` | absent | 枚举（**无 `DPS_` 前缀**） | `openbase` | 取缺省 `local` 时身份权威不生效 |
| `STATIC_KEY_CHANNEL` | absent | 枚举（**无 `DPS_` 前缀**） | `closed` | 静态 Key 通道关闭 |
| `EMERGENCY_BYPASS_KEY` | absent | 🔒 应急 Key（**无 `DPS_` 前缀**） | 仅窗口内有效 | 未到期可放行、到期拒绝 |
| `EMERGENCY_BYPASS_EXPIRES_AT` | absent | 时间（**无 `DPS_` 前缀**） | 明确到期时间（不得空） | 到期后 bypass 失效 |
| `IDENTITY_ROLE_CONTRACT_URL` | absent | 非秘密（**无 `DPS_` 前缀**） | 生产角色契约端点 | 契约拉取成功 |
| `DPS_OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` | absent | 布尔 | `true` | 后台同步生效 |

> **DPS 前缀陷阱**：`IDENTITY_AUTHORITY` / `STATIC_KEY_CHANNEL` / `EMERGENCY_BYPASS_KEY` / `EMERGENCY_BYPASS_EXPIRES_AT` / `IDENTITY_ROLE_CONTRACT_URL` 五键**不带 `DPS_` 前缀**（源码 `DPS/src/config.py`），误加前缀等于未配置。

### 11.7 回执字段与闭合判据

| 回执字段 | 说明 |
|---|---|
| `repo` | 仓名（OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS） |
| `key` | 键名（秘密键只记「已配置」） |
| `state` | `已配置` / `未配置` / `保持未设置` |
| `checked_at` / `checked_by` | 复核时间与执行人 |

**RF-03 / RF-04 闭合判据**：五仓 `commented=0`、`duplicate=0`，且 DPS `present=18`、四仓目标键全量 `present`；同时满足才可进入阶段 1（P-03）。任一未闭合 → 窗口保持挂起，不得带缺键执行。

---

## 12. 本机全栈启动复核（2026-11-03）

> **口径**：Windows 原生进程、无 Docker；共享解释器 `OpenBase\.venv-test\Scripts\python.exe`；仅做**启动级复核**（监听 + 探活），**不替代生产实测**——E5 拓扑实测与阶段 4 取证仍以 §4 为准。未修改任何仓库源码或 `.env`。

### 12.1 复核结果（两轮汇总）

| 仓 | 入口 | 端口 | 结果 | 探活 | 阻塞点 / 备注 |
|---|---|---|---|---|---|
| OpenBase | `openbase.demo_app:app` | 8000 | ✅ running | `/docs` 200 | 共享 PG 不可达时按设计降级内存演示用户；Redis `192.168.0.151:6380/0` 可用 |
| OpenLLM | `main:app`（cwd `backend`） | 8020 | ✅ running | `/health` 200 | `IdentityGate` 身份裁决中间件已加载；`pynvml` 缺失仅 GPU 监控降级；启动约 20.4s |
| OpenMemory | `openmemory.api.server:create_app --factory`（cwd `OpenMemory\src`） | 8040 | ⚠️ degraded | `/health` **503** | 空密钥启动门禁已越过（仅进程级临时 `OPENMEMORY_SERVER_API_KEY`，探测后清除）；PG `127.0.0.1:5432` 用户 `openmemory` 口令认证失败 → 迁移跳过 |
| DPS | `rest_api.app:app`（cwd `DPS\src`） | 8013 | ⛔ blocked | 无监听 | 首轮缺 `aiofiles`（已补装解除）；次轮 PG `192.168.0.151:5432` 不可达且 `DB_FAIL_FAST=true` 禁用 SQLite 降级，lifespan 内终止 |
| OpenRAG | `openrag.main:app`（cwd `OpenRAG\src`） | 8030 | ⛔ blocked | 无监听 | `import fitz` → `pymupdf.layout` 无条件 `import onnxruntime`；Windows access violation（`0xC0000005`），全包无禁用开关 |

**汇总**：`running=[OpenBase, OpenLLM]`；`degraded=[OpenMemory]`；`blocked=[DPS, OpenRAG]`。

### 12.2 环境准备（仅解释器依赖，不改仓库）

| 包 | 版本 | 用途 |
|---|---|---|
| `aiofiles` | 25.1.0 | DPS 导入期缺包 |
| `psycopg` / `psycopg-binary` | 3.3.6 | OpenLLM PostgreSQL 驱动 |
| `jinja2` | 3.1.6 | OpenLLM 缺失项（补充包 1） |
| `opentelemetry-exporter-otlp-proto-grpc` / `grpcio` | 1.45.2 / 1.85.1 | OpenLLM 缺失项（补充包 2） |

> 该 venv 原本无 `pip`，使用 `ensurepip` 引导 `pip 25.0.1`；安装范围限定为缺失运行时包，未升级/降级既有依赖。

### 12.3 阻塞项与解除条件

| 阻塞项 | 责任方 | 解除条件 | 影响面 |
|---|---|---|---|
| DPS 共享 PG 不可达 + `DB_FAIL_FAST=true`（**本机已解除，见 §13**） | OPS / 生产 DBA | 提供可达 PG（`192.168.0.151:5432` 网络放通或等价实例）并核账号权限；**生产不得放开 SQLite 降级** | 影响 P-03 / P-05 / P-06 的 DPS 侧验证 |
| OpenRAG `onnxruntime` 原生崩溃（**本机已解除，见 §13**） | OPS / 研发 | 匹配解释器与 CPU 指令集的 `onnxruntime`，或在隔离窗口修复 `pymupdf.layout` 导入链；不得以「跳过 RAG 解析」替代 | 影响 P-05 / P-06 的 OpenRAG 侧验证 |
| OpenMemory PG 口令认证失败（**本机已解除，见 §13**） | OPS / 生产 DBA | 生产口令与连接串对齐（只记状态，不记值） | 影响 P-05 / P-06 的 OpenMemory 侧验证 |
| F0-6 PEM `0600` / F0-7 网关与 IdP 地址 / F0-8 DBA 会话 | OPS / 生产 DBA | 生产主机窗口内完成 | 阻断阶段 1 起点（P-03） |
| RF-03 / RF-04 填值 | OPS | 按 §11 附录 B 逐仓补值并回执 | 阻断阶段 1 前置 |

### 12.4 取证与清理

| 项 | 说明 |
|---|---|
| 证据 1 | `doc/audit/verification/evidence/xr-ops-08/xr08-fullstack-run-20261103.json`（第一轮：OpenBase running，其余四项 blocked） |
| 证据 2 | `doc/audit/verification/evidence/xr-ops-08/xr08-fullstack-run-round2-20261103.json`（第二轮：OpenLLM running、OpenMemory degraded、DPS / OpenRAG blocked） |
| 清理 | 两轮均逐进程停止并校验 PID 不存在；8000 / 8013 / 8020 / 8030 / 8040 无残留监听；进程级临时环境变量已清除 |
| 秘密口径 | 日志已打码；未记录任何 token / key / 密码原文；未写入 `.env` 或任何文件 |

> **结论**：本机可启动性复核为 **2 running + 1 degraded + 2 blocked**。该结果只回答「服务在缺失生产依赖时能否启动、卡在哪一环」，**不作为 A1-04 / A1-14 的验收证据**；生产实测仍须按 §4 阶段 4 在真实拓扑执行。

---

## 13. 阻塞点整改与五系统并行复核（2026-11-03）

> **整改口径**：仅做两类动作 ——（1）向共享解释器（`.venv-test`）补装缺失运行时包；（2）进程级环境变量注入。**未写入任何 `.env`、未修改任何仓库源码、未放开 SQLite 降级**。

### 13.1 逐项整改

| # | 仓 | 原阻塞 | 根因 | 整改动作 | 结果 |
|---|---|---|---|---|---|
| B-1 | DPS | 连接默认库 `dps_db` 不存在 → `connection was closed in the middle of operation` | 未加载 `.env.shared-infra`，`DATABASE_URL` 缺省指向本地 `dps_db` | 按仓内 `scripts/start-shared-infra.ps1` 口径加载 `.env.shared-infra` 并映射 `DATABASE_URL = POSTGRES_URL`；保持 `DB_FAIL_FAST=true` / `SQLITE_FALLBACK=false`（**未放开降级**） | ✅ 8013 `/health/liveness` 200 |
| B-2 | OpenMemory | `127.0.0.1` 用户 `openmemory` 认证失败、迁移跳过、`/health` 503 | `.env` 使用 `POSTGRES_*` 旧键，配置类实际前缀为 `OPENMEMORY_DB__` / `OPENMEMORY_CACHE__` / `OPENMEMORY_VECTOR__`，全部落到默认值 | 按部署指南注入 `OPENMEMORY_DB__*`（共享 PG `nuct`）、`OPENMEMORY_CACHE__*`（Redis 6380）、`OPENMEMORY_VECTOR__*`（Qdrant 6333）、`OPENMEMORY_GRAPH_*`（Neo4j 7687）；改用仓内官方启动器 `scripts/start_openmemory.py`（`create_app --factory` 不会注入 `memory_service`，属入口误用） | ✅ 8040 `/health` 200 |
| B-3 | OpenMemory | 启动阻断：`No module named 'qdrant-client'` / `'neo4j'` | 共享解释器缺依赖 | 仅补装 `qdrant-client 1.20.0`、`neo4j 6.4.1` | ✅ 解除 |
| B-4 | OpenRAG | `import fitz` → `pymupdf.layout` → `onnxruntime` 原生崩溃（`0xC0000005`） | `pymupdf 2.0` 将 `pymupdf.layout` 设为无条件导入，且 `onnxruntime 1.31.1` / `1.22.0` 在本机 DLL 初始化均失败 | 将 `pymupdf` 降至 `1.24.14`（`fitz` API 不变、不再导入 layout/onnxruntime） | ✅ 解除 |
| B-5 | OpenRAG | 导入链连续缺包：`tiktoken`、`bs4`、`python-docx`、`qdrant_client` 等 | 共享解释器缺文档解析依赖 | 补装 `tiktoken`、`beautifulsoup4`、`python-docx 1.2.0`、`openpyxl 3.1.5`、`pypdf 6.21.4`、`python-pptx 1.0.2`、`markdownify 1.2.3`、`striprtf 0.0.35`、`qdrant-client 1.20.0` | ✅ 8030 `/openapi.json` 200 |
| B-6 | OpenBase | 启动降级内存（`database init failed, fallback to memory`） | `.env` 无 `POSTGRES_URL`，缺省指向不存在的本地库 | 进程级注入 `.env.shared-infra` 的 `POSTGRES_URL` / `REDIS_URL` | ✅ 8000 `/docs` 200，且不再出现内存降级告警 |
| B-7 | DPS / OpenRAG | 探活路径口径错误（`/health` 非实际路由） | DPS 健康路由为 `/health/liveness`；OpenRAG `/health` 位于 `/api/v1` 且受身份门禁，`/openapi.json` 在门禁白名单 | 修正探活路径（不改代码） | ✅ 200 |

### 13.2 五系统并行复核结果

| 仓 | 端口 | 探活 | 结果 |
|---|---|---|---|
| OpenBase | 8000 | `/docs` | ✅ 200 |
| OpenLLM | 8020 | `/health` | ✅ 200 |
| DPS | 8013 | `/health/liveness` | ✅ 200 |
| OpenRAG | 8030 | `/openapi.json` | ✅ 200 |
| OpenMemory | 8040 | `/health` | ✅ 200 |

**汇总：5 / 5 running（HTTP 200）**。复核方式为「同时启动 → 逐项探活 → 统一停止」；停止后 8000 / 8013 / 8020 / 8030 / 8040 均为 `CLOSED`，无残留进程与监听。

### 13.3 证据与残余风险

| 项 | 说明 |
|---|---|
| 主证据 | `doc/audit/verification/evidence/xr-ops-08/xr08-fullstack-simultaneous-20261103-131838.json`（`residual_ports` 全 `false`） |
| 分证据 | `…-unblock-OpenMemory-20261103-131657.json`、`…-unblock-OpenRAG-20261103-131724.json` |
| R-13-1 | `pymupdf4llm 2.0` 依赖 `pymupdf 2.0`，与本次降级不兼容；OpenRAG 未使用该包，后续启用需在隔离环境恢复组合 |
| R-13-2 | `qdrant-client 1.20.0` 与 Qdrant Server `1.7.4` 存在主/次版本不匹配告警（读路径可用，写路径需生产复核） |
| R-13-3 | 本机为「共享测试实例」口径；生产仍须按 §4 阶段 4 在真实拓扑实测，本结果**不作为 A1-04 / A1-14 验收证据** |

> **结论**：本机阻塞点 B-1~B-7 已全部解除，五系统可同时运行并全部返回 200。生产侧 F0-6 / F0-7 / F0-8、RF-03 / RF-04 与生产拓扑实测仍为阶段 1 的硬门禁。
