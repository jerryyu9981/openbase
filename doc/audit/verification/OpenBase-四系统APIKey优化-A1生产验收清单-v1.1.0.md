# OpenBase 四系统 API Key 与授权优化 —— A1 生产验收清单

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.1.0 |
| 文档状态 | [Review] |
| 适用环境 | 生产环境（Pro）/ 准生产（Pre-Pro） |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.22.0.md`（§10.7~§10.25） |
| 验收对象 | OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS 五仓（E0~E3 已实施项） |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.0 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 首版：把方案 §11 残余中的「已完成但未生产实测（V-01~V-07）」转化为可执行的 A1-01~A1-12 验收项，明确前置、步骤、通过标准、证据与签核门禁 |
| v1.0.1 | 2026-10-30 | FA-OpenBase-Dev（AI 辅助） | 同步方案 v1.12.0（§10.15 A3）：A1-12 由「缺失即手工 DDL」改为「启动应用即自动补列」，手工幂等 DDL 降为不启动应用时的可选预置路径；关联方案版本号更新 |
| v1.1.0 | 2026-11-01 | FA-OpenBase-Dev（AI 辅助） | D-01 升版收口：关联方案更新至 v1.22.0（§10.7~§10.25），覆盖 §10.17~§10.25 新增能力——新增 **A1-13 OIDC 登录安全硬化与登出联动**（对应 V-13：多 Provider 路由、PKCE/nonce、state TTL、五种 token 认证方式、SAN/subject 绑定、back-channel logout、`id_token_hint`）与 **A1-14 跨仓生产实测**（对应 V-14）；A1-08 增补 ABAC 变更事后审计（`review_mode=post_audit`）与 SoD 授予强制（409 `PERM_DUTY_CONFLICT`）判定；A1-11 负向启动补齐 ABAC 阈值非正、MCP 工具白名单、OIDC 六类门禁；§7 已知边界同步 ER-24/ER-25 已闭合 |

---

## 1. 目的与范围

本清单用于回答一个门禁问题：**E0~E3 的已实施能力，能否在真实生产拓扑下被证明有效？**

覆盖方案 §11 中 V 类（已完成、仅有单测/SQLite/桩验证）的 7 组能力，并扩展为 14 个可执行验收项：

| 验收项 | 对应残余 | 关键词 |
|---|---|---|
| A1-01 | ER-06、U-02 | 生产配置基线与 RS256 收口 |
| A1-02 | V-03 | JWKS 发布与四仓本地验签 |
| A1-03 | ER-07、V-03 | 换钥 / 多 kid 平滑与未知 kid fail-closed |
| A1-04 | V-04、ER-10 | 吊销收敛时延（四仓） |
| A1-05 | V-01 | 审计链双实例并发串行化 |
| A1-06 | V-02 | 审计 NDJSON 导出容量与上限 |
| A1-07 | V-02、ER-27 | 审计留存清理与链完整性 |
| A1-08 | V-02 | E3 三权分立 / ABAC / IdP 真实权限矩阵 |
| A1-09 | V-07、ER-13 | MCP 三形态凭证与工具级授权 |
| A1-10 | V-05、ER-04 | 离线宽限与断网降级 |
| A1-11 | V-06 | 四仓生产门禁负向启动 |
| A1-12 | V-09、U-03 | 存量库迁移与数据核对 |
| A1-13 | V-13 | OIDC 登录安全硬化与登出联动（真实 IdP） |
| A1-14 | V-14 | 跨仓生产实测（JWKS 验签 / 吊销时延 / 门禁 / 审计字段） |

**不在本清单范围**：多实例中心化配额/异常聚合已由 C-07 实现、其生产取证并入 A1-14；SM2 真实签名、集中审计平台、信创灾备、终端宿主项（TPM/安全启动/固件签名/本地落盘加密/远程擦除）——这些是 U 类未完成项（对应残余台账 P 类），另行立项验收。

---

## 2. 环境与前置条件

### 2.1 拓扑与版本

- [ ] 五仓均为本次候选发布版本，记录每个仓库的 `git rev-parse HEAD`（写入证据 `versions.txt`）。
- [ ] OpenBase 至少 2 个应用实例，**连同一个 PostgreSQL 实例**（审计链串行化前提，ER-18）。
- [ ] Redis 可用（离线宽限时间标记依赖，ER-04）。
- [ ] OpenLLM / OpenRAG / OpenMemory / DPS 均为单实例或受控多实例，能读取 OpenBase JWKS。
- [ ] 四仓 `.env` 中 `*_OPENBASE_JWKS_URL` 指向 OpenBase 生产地址（以各仓 `.env.example` 登记项为准；DPS 为 `DPS_OPENBASE_*`）。

### 2.2 账号与凭证

| 凭证 | 用途 | 要求 |
|---|---|---|
| 超管 JWT（`system:superadmin`） | 审计导出/清理、链校验 | RS256、`kid` 正确、`iss=openbase`、`aud=openbase-api` |
| 服务 Key（`ob_k_*`，`scope.system` 含 `auth`） | 内省、吊销增量 | 不得使用开发态明文静态 Key |
| 普通用户 JWT | 吊销收敛测试 | 可修改密码/可被禁用 |
| ABAC 管理权限账号（`security:admin`） | `/auth/access/check`、`/auth/access/duties` | 生产权限矩阵真实授予 |
| MCP 静态 Key（仅测试窗口） | MCP 兼容形态 | 测试后立即回收 |
| IdP 测试客户端（OIDC） | A1-13 登录与登出联调 | 独立测试租户/client；`client_secret`、私钥、证书只登记「已配置/未配置」，禁止落证据文件 |
| 三权分立职责账号（`system_admin` / `security_admin` / `audit_admin`） | A1-08 SoD 授予冲突判定 | 至少两个可授予账号，用于验证互斥职责叠加被拒（409 `PERM_DUTY_CONFLICT`） |

### 2.3 工具

`curl.exe`、`jq`、`python 3.11+`（含 `httpx`）、`psql`、可读应用日志的权限。

### 2.4 数据与备份

- [ ] 验收前备份 `openbase.audit_logs`、`users`、`service_api_keys`（`pg_dump`，写入证据）。
- [ ] 准备 1 个专用测试租户（如 `a1-test`）与 2 个测试用户，**不触碰生产业务租户**。
- [ ] 记录清理前审计行数：`SELECT count(*) FROM openbase.audit_logs;`

### 2.5 回滚

- [ ] 配置类改动（`jwt_require_rs256`、留存天数等）保留旧值快照，可一键回滚。
- [ ] 留存清理**必须先 dry-run**；真删前再次备份。
- [ ] 任一项判定 `Fail` 且影响面为写入/认证主链时，**停止验收并回滚**，不得带病继续。

---

## 3. 验收项总表

| 编号 | 验收项 | 优先级 | 通过标准（摘要） | 证据文件 |
|---|---|---|---|---|
| A1-01 | 生产配置基线与 RS256 收口 | P0 | 新签发令牌 `alg=RS256` 且有 `kid`；`jwt_require_rs256=true` 下缺配置拒启 | `a1-01.txt` |
| A1-02 | JWKS 发布与四仓验签 | P0 | JWKS 仅公钥；四仓接受 OpenBase 令牌；错误租户/映射即 401 | `a1-02.json` |
| A1-03 | 换钥与未知 kid | P0 | 换 PEM 后新 kid 生效；旧令牌在过渡期仍可验；未知 kid 401 | `a1-03.txt` |
| A1-04 | 吊销收敛时延 | P0 | 内省即时 `active=false`；四仓实测拒绝时延记录在案（≤60s 或书面放宽） | `a1-04.csv` |
| A1-05 | 审计链双实例并发 | P0 | 双实例各写 1000 条后 `verify` 返回 `ok=true`、`checked=2000` | `a1-05.json` |
| A1-06 | 审计导出容量 | P0 | 1 万行 NDJSON 导出成功、行序正确、超限 400、内存/耗时记录 | `a1-06.txt` |
| A1-07 | 留存清理与链完整性 | P0 | `=0` 拒绝；dry-run 只计数；真删后 `verify` 仍 `ok` | `a1-07.json` |
| A1-08 | E3 真实权限矩阵 | P1 | SoD 冲突被识别；ABAC 命中/拒绝可解释；IdP 视图无密钥 | `a1-08.json` |
| A1-09 | MCP 凭证与工具授权 | P1 | 三形态可鉴权；越权调用 403/`-32001`；缺失令牌 401 | `a1-09.txt` |
| A1-10 | 离线宽限与断网降级 | P1 | 宽限内放行、超期拒绝且留痕；Redis 缺失不新增放行 | `a1-10.txt` |
| A1-11 | 生产门禁负向启动 | P0 | 每仓关键项漏配 → 拒绝启动（0 容忍） | `a1-11.txt` |
| A1-12 | 存量迁移与核对 | P0 | 列存在、行数差可解释、链校验 `ok` | `a1-12.txt` |
| A1-13 | OIDC 登录安全硬化与登出联动 | P0（启用 OIDC 时） | 多 Provider 路由正确；PKCE/nonce/state 一次性；五种 token 认证方式按配置生效；SAN/subject 绑定拒启；登出联动与 back-channel 生效 | `a1-13.json` |
| A1-14 | 跨仓生产实测 | P1 | 四仓 JWKS 验签、吊销时延、门禁负向启动、审计字段与 V-02/V-04/V-11 同批取证一致 | `a1-14.csv` |

**判定规则**：每项只允许 `Pass / Fail / Blocked` 三态；`Blocked` 必须写明阻塞原因与解除条件。P0 任一 `Fail` → 不允许上线；P1 `Fail` 需书面豁免并由项目负责人签字。

---

## 4. 详细执行步骤

### A1-01 生产配置基线与 RS256 收口

**前置**：PEM 私钥已只读挂载（`OPENBASE_JWT_RSA_PRIVATE_KEY_PATH`），`OPENBASE_JWT_SIGNING_KID` 非空。

**步骤**：

1. 记录生效配置（脱敏后写入证据，禁止记录私钥/密钥原文）：
   ```powershell
   curl.exe -s -H "Authorization: Bearer $Env:ADMIN_JWT" "$Env:OPENBASE_URL/api/v1/auth/me" | jq '.data.permissions'
   ```
2. 登录获取新令牌，解码头部：
   ```powershell
   $tok = (curl.exe -s -X POST "$Env:OPENBASE_URL/api/v1/auth/login" -H "Content-Type: application/json" -d '{\"username\":\"a1-user\",\"password\":\"...\"}' | jq -r '.access_token')
   # 取 JWT 头部（base64url 解码由验收脚本完成，或用 jwt.io 离线核对）
   ```
3. 核对生产配置：`OPENBASE_JWT_REQUIRE_RS256=true`、`OPENBASE_JWT_ISSUER=openbase`、`OPENBASE_JWT_AUDIENCE=openbase-api`、`OPENBASE_JWT_JWKS_PUBLIC_KEYS` 含过渡公钥（若有）。
4. 负向确认：临时移走 PEM（或改指向不存在路径）后重启 → **必须拒绝启动**；恢复后重启成功。

**通过标准**：

- 新签发令牌 `alg=RS256`、头部含 `kid`、`iss/aud` 正确；
- 生产实例不接受 HS256 令牌（构造旧 HS256 令牌请求 → 401）；
- `jwt_require_rs256=true` 且缺 PEM/kid 时启动失败，日志含明确原因。

**证据**：配置快照（脱敏）、令牌头部、负向启动日志截图/文本。

---

### A1-02 JWKS 发布与四仓本地验签

**步骤**：

1. 拉取 JWKS：
   ```powershell
   curl.exe -s "$Env:OPENBASE_URL/.well-known/jwks.json" | jq '{count:(.keys|length), kids:[.keys[].kid], algs:[.keys[].alg]}'
   ```
2. 校验 JWKS **只含公钥分量**（`kty/n/e`，`use=sig`），断言响应中不出现 `d`/`p`/`q`/`dp`/`dq`/`qi`。
3. 用 A1-01 的令牌分别请求四仓受保护接口，记录状态码与主体解析结果。
4. 反向用例：
   - 篡改 `aud` → 401；
   - 过期令牌（`exp` 已过）→ 401；
   - 主体未在 `*_SUBJECT_MAP` 映射（跨库部署）→ 401（fail-closed，不做猜测式回退）。

**通过标准**：四仓均接受合法令牌；三类反向用例均为 401；JWKS 无私有分量；四仓日志只记录失败原因、不含令牌内容。

**证据**：JWKS 摘要（kid/alg 清单）、四仓请求/响应状态码表、失败日志片段。

---

### A1-03 换钥 / 多 kid 平滑与未知 kid

**步骤**：

1. 记录旧 `kid` 与旧令牌。
2. 生成新 RSA 密钥对，替换 PEM（保持文件路径不变），把**旧公钥**登记到 `OPENBASE_JWT_JWKS_PUBLIC_KEYS`。
3. 触发 `mtime` 缓存失效（无需重启），再次拉取 JWKS，应同时包含新旧 `kid`。
4. 用旧令牌请求四仓 → 仍 200/正常；用新令牌 → 正常；JWKS 按 `kid` 选键。
5. 构造未知 `kid` 令牌 → 下游强制刷新一次 JWKS 后 401。

**通过标准**：换钥期间零中断；旧 kid 在过渡期可用；未知 kid fail-closed；JWKS 双 kid 可见。

**证据**：换钥前后 JWKS、旧/新令牌请求结果、未知 kid 401 记录。

---

### A1-04 吊销收敛时延（四仓）

**前置**：下游已配置吊销同步（`*_REVOCATION_*`，以各仓 `.env.example` 为准）；记录同步节流间隔。

**步骤**：

1. 用测试用户登录取 access token，四仓各请求一次 → 200。
2. 立即调用内省：
   ```powershell
   curl.exe -s -X POST "$Env:OPENBASE_URL/api/v1/auth/introspect" -H "X-API-Key: $Env:SVC_KEY" -H "Content-Type: application/json" -d "{\"token\":\"$tok\"}" | jq '{active,reason,token_version}'
   ```
   期望：吊销前 `active=true`。
3. 触发吊销：测试用户修改密码（`token_version` 自增）或管理面禁用该用户。
4. 再次内省 → **立即** `active=false`（无缓存，ER-08 有意取舍）。
5. 以 5~10s 间隔轮询四仓，直到首次返回 401/403，记录每仓时延（CSV：`repo,start_ts,first_reject_ts,latency_s,interval_config`）。
6. 记录 `GET /api/v1/auth/revocations?since=<游标>&limit=500` 输出，确认目标主体的 `token_version` 变化已下发。

**通过标准**：

- 内省即时反映吊销；
- 四仓均能在**配置节流间隔 + 一次请求**内拒绝；若实测 > 60s，记录实际值并提交放宽申请（ER-10 惰性拉取无后台线程的已知边界）；
- 严格模式（`*_REVOCATION_STRICT=true`）下快照未命中应拒绝（按仓验证）。

**证据**：`a1-04.csv`、内省前后 JSON、revocations 快照片段（脱敏）。

---

### A1-05 审计链双实例并发串行化

**前置**：OpenBase 两个实例连同一 PG；审计落库开关开启（`OPENBASE_AUDIT_DB_PERSIST=1`）。

**步骤**：

1. 记录起始行数：`SELECT count(*) FROM openbase.audit_logs WHERE entry_hash IS NOT NULL;`
2. 起一个并发脚本，两个 base URL 各自 10 线程 × 100 次请求（请求审计主链上的轻量受保护接口，如 `/api/v1/auth/me`，带各自有效超管令牌）：
   ```python
   # a1_concurrency.py（验收脚本，不入库）
   import concurrent.futures, httpx, time
   targets = ["http://openbase-a:8080", "http://openbase-b:8080"]
   headers = {"Authorization": f"Bearer {token}"}
   def hit(base):
       with httpx.Client(base_url=base, headers=headers, timeout=10) as c:
           ok = sum(1 for _ in range(100) if c.get("/api/v1/auth/me").status_code == 200)
       return base, ok
   with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
       print(list(pool.map(hit, [t for t in targets for _ in range(10)])))
   ```
3. 结束后调用链校验：
   ```powershell
   curl.exe -s -H "Authorization: Bearer $Env:ADMIN_JWT" "$Env:OPENBASE_URL/api/v1/audit/chain/verify?limit=10000" | jq '{ok,checked,broken,reason}'
   ```

**通过标准**：`ok=true`；`checked` ≥ 2000 且等于本次新增（链完整覆盖）；无断链/叉链；重复跑 3 轮均通过。

**证据**：`a1-05.json`（verify 响应）、脚本输出、两实例日志中的锁/写序列片段。

---

### A1-06 审计 NDJSON 导出容量与上限

**前置**：库内 ≥ 1 万条带 `entry_hash` 的审计行（不足则先造数，**仅测试租户**）。

**步骤**：

1. 正常导出 1 万行并计时：
   ```powershell
   Measure-Command { curl.exe -s -N -H "Authorization: Bearer $Env:ADMIN_JWT" "$Env:OPENBASE_URL/api/v1/audit/export?limit=10000" -o a1-export.ndjson }
   (Get-Content a1-export.ndjson | Measure-Object -Line).Lines
   ```
2. 校验内容：首行 `id` 最小、末行 `id` 最大；每行含 `prev_hash`/`entry_hash`；`Content-Type: application/x-ndjson`；响应头 `X-Row-Limit: 10000`。
3. 时间过滤：`?since=2026-01-01T00:00:00Z&until=2026-02-01T00:00:00Z` 行数与 SQL 对照一致。
4. 负向：`limit=10001` → 400 `PARAM_INVALID`；`since` 晚于 `until` → 400 `PARAM_INVALID`。
5. 记录导出期间进程内存峰值（`Get-Process` 采样或容器 `stats`）与耗时。

**通过标准**：1 万行导出成功且行序正确；超限/倒置均 400；内存峰值 < 200MB（目标值，可按实例规格调整并以记录为准）；导出过程不影响在线请求错误率。

**证据**：`a1-06.txt`（耗时、行数、内存、HTTP 头、负向响应）。

---

### A1-07 审计留存清理与链完整性

**前置**：`OPENBASE_AUDIT_RETENTION_DAYS=30`（非 0）；已备份审计表。

**步骤**：

1. 先验证未启用语义（若当前配置为 0 可跳过）：临时置 0 → `POST /api/v1/audit/retention/purge` → 期望 `BIZ_CONFIG_CONFLICT`，**不得删除**。
2. 恢复 30 天，dry-run：
   ```powershell
   curl.exe -s -X POST -H "Authorization: Bearer $Env:ADMIN_JWT" "$Env:OPENBASE_URL/api/v1/audit/retention/purge" | jq '.data | {dry_run,retention_days,cutoff,candidate_rows,deleted_rows}'
   ```
   期望 `dry_run=true`、`deleted_rows=0`、`candidate_rows` 与 SQL `count(*) where created_at < cutoff` 一致。
3. 真删：`?dry_run=false` → `deleted_rows == candidate_rows`；核对总行数减少量一致。
4. 链校验：`GET /api/v1/audit/chain/verify` → `ok=true`，`checked = 剩余行数`（删头不断链）。
5. 记录结构化 INFO 日志 `audit.retention.purge` 的字段（request_id/候选/删除数）。

**通过标准**：未启用拒绝；dry-run 只读；真删数量与候选一致；清理后链校验通过；日志可追溯操作人/时间。

**证据**：`a1-07.json`（三次响应 + verify）、清理前后行数 SQL 输出。

---

### A1-08 E3 三权分立 / ABAC / IdP（真实权限矩阵）

**步骤**：

1. 职责清单（`security:admin` 或超管）：
   ```powershell
   curl.exe -s -H "Authorization: Bearer $Env:ADMIN_JWT" "$Env:OPENBASE_URL/api/v1/auth/access/duties" | jq '.data'
   ```
   期望 `mutually_exclusive=true`，三职责权限点基线互不重叠。
2. ABAC 试算（先配置 `OPENBASE_ABAC_POLICIES` 一条 deny + 一条 allow）：
   ```powershell
   curl.exe -s -X POST "$Env:OPENBASE_URL/api/v1/auth/access/check" -H "Authorization: Bearer $Env:ADMIN_JWT" -H "Content-Type: application/json" -d '{"permission":"key:issue","resource_tenant":"a1-test","roles":["developer"]}' | jq '{decision,reason,subject_tenant}'
   ```
   覆盖：命中 deny（`deny_rule_matched`）、无策略（`not_applicable`）、跨租户无显式允许（`cross_tenant_without_allow`）、显式跨租户允许（`allow`）。
3. IdP 视图（配置 1 个 Provider，含 `client_secret`）：
   ```powershell
   curl.exe -s -H "Authorization: Bearer $Env:ADMIN_JWT" "$Env:OPENBASE_URL/api/v1/auth/idp/providers" | Tee-Object -Variable body | Out-Null
   $body | jq '.data'
   ```
   断言响应全文不含 `client_secret` 与密钥原文，仅 `has_client_secret=true`。
4. 真实权限矩阵：用**非** `security:admin` 用户调用上述接口 → 403；用真实授予用户 → 200。
5. SoD 授予强制（G-02）：对同一账号先授予 `system_admin`，再授予 `audit_admin`（或 `security_admin`）→ 必须返回 **409 `PERM_DUTY_CONFLICT`**，错误体含 `conflicts` 明细；改用替换语义单角色授予可正常成功。
6. ABAC 变更事后审计（G-01，裁定 B）：调用 `POST/PUT/DELETE /api/v1/auth/access/policies` 后查 `audit_logs`，确认 `detail.review_mode="post_audit"`；update/delete 的 `detail.previous` 含变更前快照；应用日志出现 `abac policy changed without dual review; post-audit required` WARN。
7. ABAC 规模/耗时基线（G-03）：将 `OPENBASE_ABAC_RULE_SOFT_LIMIT` 临时调小（如 10）并保留 >10 条生效策略 → 日志出现 `abac rule set exceeds soft limit; consider index/cache`；验证后恢复默认 1000。

**通过标准**：三端点按权限矩阵返回；ABAC 四种判定可解释；IdP 视图零密钥泄露；SoD **已在授予路径强制**（互斥职责叠加返回 409，ER-25 已闭合）；ABAC 变更审计带 `post_audit` 标记与改前快照；ABAC 超规则数/超耗时可按阈值告警。

**证据**：`a1-08.json`（三类响应脱敏副本）、403 用例。

---

### A1-09 MCP 三形态凭证与工具级授权

**步骤**：

1. 形态一：静态 `X-API-Key`（仅测试窗口启用）→ `initialize`/`tools/list` 成功；回收后失败。
2. 形态二：服务 Key `ob_k_*`（`scope.system` 含 `mcp`）→ `tools/list` 按 `scope.tools` 过滤，仅返回白名单工具。
3. 形态三：短期 JWT（`type=access`）→ 正常调用；过期/非 access → 401。
4. 越权：`tools/call` 调用不在白名单的工具 → HTTP 403 `PERM_API_KEY_SCOPE`；JSON-RPC 通道返回 `isError=true` 且协议码 `-32001`。
5. stdio 通道：宿主注入 `OPENBASE_MCP_TOKEN_FILE` → 正常；缺失/过期 → 401。

**通过标准**：三形态均可用且互不越权；白名单外工具两种通道均被拒；缺失凭证 fail-closed。

**证据**：`a1-09.txt`（请求/响应状态与协议码、工具过滤清单）。

---

### A1-10 离线宽限与断网降级

**前置**：确认在线态已写入 Redis 时间标记；确认离线宽限配置（默认 72h 量级）。

**步骤**：

1. 预热：正常请求一次，确认 `offline_grace` 相关字段/标记已写入。
2. 模拟失联：断开 OpenBase 到 PG（或阻断 DB 网络，视部署而定），保持 Redis 可用。
3. 宽限内再次请求 → 按策略放行（或只读），日志留痕（不记录令牌原文）。
4. 将时间标记推进至超期（或改配置缩短宽限后重启）→ 超期请求被拒（503/只读放行，按 §10.7 E0 口径）。
5. Redis 同时不可用 → 无离线标记，**不得新增放行**（沿用既有策略）。

**通过标准**：宽限内/超期行为符合文档口径；无标记时不放大权限；留痕字段完整；恢复后自动回到在线判定。

**证据**：`a1-10.txt`（时间线、状态码、日志片段）。

---

### A1-11 四仓生产门禁负向启动

对每个仓库逐项构造「缺配置」并重启，**必须拒绝启动**（非仅 WARN）：

| 仓库 | 负向用例 |
|---|---|
| OpenBase | `OPENBASE_JWT_REQUIRE_RS256=true` 但缺 PEM/kid；`OPENBASE_JWT_ALGORITHM=SM2` 或未知算法；`OPENBASE_ABAC_POLICIES` 非法 JSON；`OPENBASE_ABAC_RULE_SOFT_LIMIT=0` 或 `OPENBASE_ABAC_EVALUATION_WARN_MS=-1`；`OPENBASE_AUDIT_RETENTION_DAYS=10`；`OPENBASE_IDP_PROVIDERS` 名称重复；`OPENBASE_MCP_API_KEY_TOOLS` 非法 JSON/空数组；`OPENBASE_OIDC_STATE_TTL_SECONDS=0`；`OPENBASE_OIDC_SIGNING_ALGORITHMS` 含 `SM2`；`OPENBASE_OIDC_TOKEN_AUTH_METHOD=bogus`；`mtls` 缺证书路径；`tls_client_auth` subject 与证书不匹配 |
| OpenLLM | 生产 profile 下 `TRUSTED_PROXY_SOURCES` 为空 |
| OpenRAG | `enforce_inbound_identity_headers=false`、`trusted_proxy_sources` 为空、`role_fail_closed=false`（分别验证） |
| DPS | 已开启 enforce 时 `TRUSTED_PROXY_SOURCES` 为空 |
| OpenMemory | 网关安全策略缺项（同款口径） |

**通过标准**：每条用例均启动失败且错误信息可定位到具体配置项；恢复正确配置后可正常启动。

**证据**：`a1-11.txt`（每仓每条用例的退出码与错误行）。

---

### A1-12 存量库迁移与数据核对

**前置**：已用生产快照在预生产演练；已备份。

**步骤**：

1. 校验列存在（先启动一次应用，由初始化链幂等迁移自动补列；方案 v1.12.0 §10.15 A3）：
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_schema='openbase' AND table_name='audit_logs'
     AND column_name IN ('prev_hash','entry_hash');
   ```
   若在不启动应用的窗口预置，可执行下方幂等 DDL（列已存在则无副作用；启动后迁移同样跳过）：
   ```sql
   ALTER TABLE openbase.audit_logs ADD COLUMN IF NOT EXISTS prev_hash varchar(64);
   ALTER TABLE openbase.audit_logs ADD COLUMN IF NOT EXISTS entry_hash varchar(64);
   ```
2. 存量策略确认：历史行 `entry_hash IS NULL` 被链校验跳过（不误报）；新写入行必须有哈希。
3. 存量 `ob_k_` 统计：`SELECT count(*) FROM openbase.service_api_keys WHERE expires_at IS NULL;` 记录数量，纳入轮换计划（ER-01）。
4. 迁移前后行数核对；跑 `GET /api/v1/audit/chain/verify` → `ok=true`；抽查 2 条历史行与 2 条新行。
5. 回滚演练：用备份恢复到预生产副本，验证回滚脚本可用。

**通过标准**：列存在；历史 NULL 行不影响校验；行数差 = 删除数（若做过清理）；链校验通过；回滚演练成功。

**证据**：`a1-12.txt`（DDL 输出、行数、verify 响应、回滚记录）。

---

### A1-13 OIDC 登录安全硬化与登出联动（真实 IdP）

**前置**：`OPENBASE_OIDC_ENABLED=true`；`OPENBASE_IDP_PROVIDERS` 登记至少 1 个真实 Provider（含名称唯一与必填项）；若使用多 Provider 需登记 2 个；证书/私钥/`client_secret` 只读挂载并只登记「已配置/未配置」。

**步骤**：

1. 多 Provider 路由：分别请求 `GET /api/v1/auth/oidc/authorize?provider=<name>`，断言 302 指向对应 IdP 授权端点；回调后主体与租户取自该 Provider 配置；请求未登记/未知 `provider` → 400 `PARAM_INVALID`。
2. PKCE / nonce / state 一次性：`authorize` 响应含 `code_challenge`（S256）与 `nonce`；callback 校验 nonce 缺失/不匹配被拒；同一 state 二次回调被拒（Redis 一次性；Redis 不可用时单实例语义）。
3. 五种 token 认证方式（按 IdP 支持逐项验证）：`client_secret_post`、`client_secret_basic`、`private_key_jwt`、`mtls`、`tls_client_auth`——分别确认 token 请求载荷/客户端证书/断言 `iss`/`sub`/`aud` 正确、登录成功，并记录各方式耗时。
4. 证书绑定负向：`tls_client_auth` 的 `OPENBASE_OIDC_CLIENT_CERT_SUBJECT` 与证书不匹配、任一 `_SAN_*` 期望值不在证书内、证书非 PEM → **拒绝启动**（对应 A1-11 门禁）。
5. 登出联动：`POST /api/v1/auth/oidc/logout` → 本地 `token_version` 递增（旧令牌立即 401）；返回 `end_session` URL 且携带 `id_token_hint`（若登录时已保存）；IdP 未声明 `end_session_endpoint` 时为 `null` 且不回滚本地吊销。
6. back-channel logout：`POST /api/v1/auth/oidc/backchannel-logout` 携带合法 logout token → 200 且目标主体存量令牌失效；`jti` 重放、`events`/`nonce`/`sub|sid` 缺失、签名错误 → 拒绝；IdP 未登记回调或不支持 → 404。
7. 日志与响应脱敏：全程检查应用日志与错误响应不含 `client_secret`、私钥、证书原文、ID Token 全文。

**通过标准**：Provider 路由与参数校验正确；PKCE/nonce/state 三重防护有效；五类认证方式按配置生效且回滚可切回 `client_secret_post`；证书绑定负向拒启；登出本地即时吊销 + IdP 登出 URL/`id_token_hint` 正确；back-channel 幂等防重放；全程无凭据泄露。

**证据**：`a1-13.json`（各步骤状态码、脱敏后的 authorize URL 参数、认证方式对照表、负向启动日志片段）。

---

### A1-14 跨仓生产实测（OpenLLM / OpenRAG / OpenMemory / DPS）

**前置**：四仓均为候选发布版本并记录 `git rev-parse HEAD`；OpenBase JWKS 可达；四仓 `*_OPENBASE_JWKS_URL` / 吊销同步 / 服务 Key 已按 A2 注入。

**步骤**：

1. 本地验签：用 A1-01 令牌分别请求四仓受保护接口 → 200；`aud` 篡改 / 过期 / 未映射主体 → 401（与 A1-02 同批取证）。
2. 吊销收敛：禁用测试用户后记录四仓开始拒绝的时间；内省路径即时生效，惰性拉取路径记录实测间隔（≤60s 或书面放宽，ER-10）。
3. 门禁负向启动：四仓按 A1-11 逐条构造缺配置并重启 → 拒绝启动，错误可定位到具体配置项。
4. 审计字段：抽查四仓审计记录，断言含 `key_id` / `subject` / `tenant` / `entry=proxy|direct`（K-03 落地后生效；未落地仓判 `Blocked` 并注明依赖 K-03）。
5. 身份权威与本地登录：生产固定 `IDENTITY_AUTHORITY=openbase`；验证本地密码登录/自签 JWT 通道已关闭（依赖 K-02/K-06 落地，未落地判 `Blocked`）。
6. 跨实例能力（如启用）：C-07 异常聚合、C-08 到期事件去重、C-09 对账在多实例下的表现与 Redis 降级路径。

**通过标准**：四仓验签与三类负向一致；吊销时延达标或有书面放宽；四仓门禁 0 容忍；审计字段齐全或明确 `Blocked`；身份权威固定为 OpenBase；Redis 降级不新增放行。

**证据**：`a1-14.csv`（每仓 × 每项 `Pass/Fail/Blocked` + 证据文件名 + 版本 HEAD）。

---

## 5. 证据与判定规范

| 要求 | 说明 |
|---|---|
| 命名 | `doc/audit/verification/evidence/a1-<编号>-<YYYYMMDD>.<ext>`（本清单所在目录下的 `evidence/a1/`） |
| 脱敏 | 禁止保存令牌全文、私钥、`client_secret`、用户密码；仅保存头部字段/摘要/状态码 |
| 判定 | 每项写 `Pass/Fail/Blocked` + 证据文件名 + 执行人 + 时间 |
| 复跑 | 任一项 `Fail` 修复后必须整项复跑，不得只补测失败子步骤 |
| 汇总结论 | 全部 P0 `Pass` 且 P1 无未豁免 `Fail`，方可给出「A1 通过」结论 |

---

## 6. 签核

| 角色 | 姓名 | 结论（Pass/Fail/Blocked） | 日期 | 备注 |
|---|---|---|---|---|
| 执行人（开发/测试） | | | | |
| 评审人（架构/安全） | | | | |
| 批准人（项目负责人） | | | | |

---

## 7. 已知边界与后续

- A1-04 的 60s 为**目标值**，惰性拉取实际间隔以各仓配置为准；超过目标需书面放宽并记录（ER-10）。
- A1-05/A1-06 仅覆盖「同 PG 双实例」；跨库分片不适用（ER-18），如需分片另立设计。
- A1-08 的两个原已知边界已闭合：ABAC 写端点由方案 v1.13.0（§10.16）提供，ER-24 关闭；SoD 授予强制由方案 v1.22.0（§10.25 G-02）提供，互斥职责叠加返回 409 `PERM_DUTY_CONFLICT`，ER-25 关闭。G-01 按裁定 B 为「超管直改 + 事后审计」，**不设审批前置**，本清单只验收审计标记与 WARN，不把「强制第二人签字」判为已实现。
- A1-13/A1-14 依赖真实 IdP 环境与四仓联调窗口；缺环境时判 `Blocked` 并写明解除条件，不得以 mock 结果判 `Pass`。
- SM2、集中审计平台、信创灾备、终端宿主项不在本清单范围（对应残余台账 P 类，触发式立项）。
- 本清单通过后，建议将 V-01~V-14 在方案 v1.22.0 中由「未实测」改为「已实测（附证据编号）」。
