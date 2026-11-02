# OpenBase 四系统 API Key 优化 —— D 类部署取证执行记录

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0.2 |
| 文档状态 | [Review] |
| 适用环境 | Dev（本机）/ Pre-Pro / Pro |
| 关联台账 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项统一处置方案-v1.2.0.md`（§6 D 行、§5.4/§5.5） |
| 关联清单 | `...-A2生产配置收口清单-v1.1.7.md`（§4 门禁、§6 漂移自检、§7 验收项） |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.28.0.md`（§10.29~§10.31） |
| 关联批次 | `...-残余项分批推进方案-v1.2.0.md`（E1 模板补齐 / E2 本机原生取证 / E3 本机生产形态，见本文 §5） |
| 覆盖对象 | D-02 / D-04 / D-05 / D-06 / D-07（P4 批 D 全部 5 项） |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.2 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | E3 本机生产形态联动：新增 §5.3 逐项登记 OpenBase D-03/D-05/D-06 两向、DPS K-01/K-02 两向、OpenRAG/OpenMemory K-01 策略层 **8/8** 的取证结果（证据 `evidence/e3/e3-native-20261102.json`）；§3 证据清单补 e3 条目、§4 结论同步 D-05/D-06 判定（本机生产形态 Pass / 真实生产仍 Blocked）；同步关联方案 v1.28.0（§10.31）、关联台账 v1.2.0、A2 v1.1.7、A1 v1.1.5、分批推进方案 v1.2.0 |
| v1.0.1 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | E 批联动：**E1** D-06 登记的 4 处模板漂移全部补齐（OpenBase `.env.shared-infra` 7 键、OpenRAG/OpenMemory `.env.example` 各 3 键、DPS 环境配置说明 v2.8.3 新增 §2.5/§2.6）；**勘误**：DPS 键名为 `IDENTITY_AUTHORITY`（不带 `DPS_` 前缀，源码 `DPS/src/config.py:200`），§2.3 原表「`DPS_IDENTITY_AUTHORITY`」为登记笔误（证据 JSON 原件不改动，以本节勘误为准）；**E2** 本机原生（无 Docker）完成 D-02 重启两向验证（缺私钥拒启 exit=1 / 恢复后启动 200）与 A2 §6.2 端点核对；关联文档版本同步 |
| v1.0.0 | 2026-11-01 | FA-OpenBase-Dev（AI 辅助） | 首版：登记 P4 批 D 五项部署取证的执行方式、本地实测结果、阻塞原因与解除条件；D-02 13 项启动门禁负向矩阵本地全部命中（17 例，含 #6 五个子情形），D-07 Provider 名称唯一性本地实测通过、issuer 唯一性为部署口径；D-06 四仓部署键名核对发现 4 处缺项（OpenBase 生产基线未注入、OpenRAG/OpenMemory 新增 `STATIC_KEY_CHANNEL` 未进模板、DPS 说明缺 `IDENTITY_AUTHORITY`/`STATIC_KEY_CHANNEL`）；D-04 生产执行 Blocked（无生产主机访问权 + 本机 PG 无凭据），已产出导出/分批收敛 SQL；证据落 `evidence/d/` |

---

## 1. 目的与边界

**目的**：把残余项台账 P4 批 D 的 5 项「部署与运维收口」从「待执行」推进到**可复现的证据状态**，并逐项给出 `Pass / Blocked` 判定与解除条件。

**边界**

- 只做**取证与编排口径**，不改业务代码、不改四仓默认值（D-05 仅出模板，D-04 仅出 SQL）。
- 秘密类只记录「键名是否存在」，不记录值；证书/私钥/令牌原文一律不落证据。
- 本机缺失能力（docker / 应用进程 / 本地 Redis / 生产主机访问权）一律标 ⛔，不以「本地不可测」推断「生产已通过」。

**本机环境实测（2026-11-01）**

| 项 | 实测结果 |
|---|---|
| Docker | ⛔ 未安装（无 `docker` 命令） |
| OpenBase 应用进程 | ⛔ 未运行（无监听进程） |
| 本地 Redis | ⛔ 未运行（`.env` 指向 `192.168.0.151:6380`，不可达性未验证） |
| 本地 PostgreSQL | ✅ `postgresql-x64-17` Running，127.0.0.1:5432，`pg_hba` 为 `scram-sha-256`，无 `pgpass` 且未注入 `POSTGRES_URL` → ⛔ 无可用凭据，无法查询 `openbase` 库 |
| 生产主机访问权 | ⛔ 无（先例：`doc/release/OpenBase-生产环境配置下发单-XR-OPS-07-v1.0.0.md` 明示「本环境无生产主机访问权」） |
| Python 取证环境 | ✅ 3.12.10 / fastapi 0.162.0 / pydantic 2.14.2 / pytest 9.x（临时 venv） |

---

## 2. 逐项执行结果

### 2.1 D-02 A2 基线与门禁执行（Pass，本地口径）

| 项 | 执行方式 | 结果 | 证据 |
|---|---|---|---|
| A2 §4 13 项启动门禁负向样例 | 生产合规基线 + 逐门禁违规覆盖，实例化 `Settings` 断言拒绝启动 | ✅ **17/17 命中**（#6 OIDC token 认证拆 5 个情形：非法方式、mtls 缺证书、private_key_jwt 缺私钥、证书非 PEM、SAN 不匹配） | `evidence/d/d-02-gate-matrix-20261101.json` |
| 正向基线 | 生产合规配置（RS256 PEM + kid、`enforce_token_version=true`、`require_tenant_on_login=true`、MCP 摘要、`audit_retention_days=0` 等） | ✅ 构造成功，13 项门禁全部放行 | 同上 `forward_baseline` |
| 门禁实现位置核对 | 按 `settings.py` 顺序逐项确认方法存在（773/799/836/850/881/906/1023/1042/1067/1092/1107/1117 行 + `validate_production_login_tenant_policy` 1439 行） | ✅ 与 A2 §4 表一致 | 本文件 §2.1 |
| A2 §6.2 端点核对（JWKS/吊销/内省） | 需运行实例 + 可观测 JWKS | ⛔ **Blocked**：本机无运行实例；生产端点核对需生产会话 | 解除条件：Dev 全栈启动或获得生产只读会话 |
| A2 §6.3 负向启动（真实重启） | 临时移走 PEM 后真实重启 | ⛔ **Blocked**：无进程可重启；已用**构造期门禁**替代取证（同上 17 例） | 解除条件：部署环境具备启停权限后补做「真实重启」两向验证 |
| 门禁相关单测回归 | `pytest tests/test_settings.py tests/test_oidc_p1_residuals.py tests/test_oidc_token_auth.py tests/test_oidc_multi_provider.py tests/test_jwt_rs256.py -q` | ✅ **108 passed**（进度 100%，退出码 0） | 命令输出（本机临时 venv） |

### 2.2 D-07 多 Provider issuer 唯一性（部分 Pass / 部署 Blocked）

| 项 | 实测 | 判定 |
|---|---|---|
| Provider **name** 唯一性（启动门禁） | 同名两条 → `ValueError: OPENBASE_IDP_PROVIDERS 的 Provider name 必须唯一` | ✅ Pass |
| Provider 合法登记（不同 name/client） | 两条登记成功（`count=2`） | ✅ Pass |
| 配置层是否存在 `issuer` 字段 | **不存在**（`IdpProviderConfig` 无 issuer 字段；issuer 由 discovery 运行期解析：`oidc.py:212`） | ℹ️ 事实登记 |
| **issuer 唯一性核对** | 需逐个读取 discovery 文档的 `issuer` 并判重 | ⛔ **Blocked**（本机无可达 IdP；生产 IdP 需会话） |
| 同 issuer 多 client 的影响面 | back-channel 登出按 `iss` + `aud` 定位客户端，命中多个时取首个（`oidc.py:1197-1224`） | ⚠️ 需在登记前判重，避免歧义 |

**D-07 登记前置口径（部署执行项）**

1. 登记 Provider 前，逐个访问 `discovery_url` 取 `issuer`，形成 issuer 清单并判重。
2. 同一 issuer 对应多个 client 时，视为**同一身份空间**：只允许登记其中一个 Provider 承担 back-channel 登出，其余 Provider 须在发布单中标注「不声明 back-channel」，否则登出定位存在取首条歧义。
3. issuer 清单与判重结果随发布单归档（只记 issuer 值，不记 `client_secret`）。

证据：`evidence/d/d-07-issuer-uniqueness-20261101.json`。

### 2.3 D-06 部署编排与秘密挂载固化（模板核对 Pass / 注入 Blocked）

| 核对项 | 结果 | 证据 |
|---|---|---|
| OpenBase 生产基线键（RS256 私钥路径/kid/require、issuer、IdP 登记、MCP 摘要、服务账号主体映射） | ✅ **E1 已补齐**：`.env.shared-infra` 追加 7 键（注释形态，真实值由 OPS 注入；该文件不被 git 跟踪） | `evidence/d/d-06-template-key-check-20261101.json`（原核对快照）+ `evidence/a2/a2-e1-template-drift-20261102.json` |
| OpenLLM 模板（JWKS/issuer/吊销/服务 Key/主体映射） | ✅ 5/5 存在 | 同上 |
| OpenRAG 模板（JWKS/issuer/吊销/服务 Key） | ✅ 4/4 存在；✅ **E1 已补齐** `OPENRAG_API_STATIC_KEY_CHANNEL` + 应急 bypass 两键（`.env.example`） | 同上 |
| OpenMemory 模板（JWKS/issuer/吊销/服务 Key） | ✅ 4/4 存在；✅ **E1 已补齐** `OPENMEMORY_GATEWAY_STATIC_KEY_CHANNEL` + 应急 bypass 两键（`.env.example`） | 同上 |
| DPS 环境配置说明（JWKS/issuer/吊销/服务 Key/主体映射） | ✅ 5/5 存在；✅ **E1 已补齐** §2.5 `IDENTITY_AUTHORITY`（生产 `openbase`，**无 `DPS_` 前缀**）与 §2.6 `STATIC_KEY_CHANNEL` + 应急 bypass 两键（说明升 v2.8.3） | 同上 |
| 秘密挂载形态（PEM 只读 0600、证书/私钥路径、CA） | ⛔ **Blocked**：无部署主机；口径按 A2 §5 留档（私钥 PEM 只读挂载 0600，禁止内联 env） | 解除条件：获得部署主机后按 A2 §5 逐项挂载并记录挂载权限 |

**D-06 缺项处置**：以上 4 处属**模板/说明漂移**（代码已支持、文档未登记），已由 E1（2026-11-02）全部补齐（见 `evidence/a2/a2-e1-template-drift-20261102.json`）；本记录原表保留 2026-11-01 的缺项快照以便追溯，补齐后的状态以本节 ✅ 标记为准。生产 `.env` 真实注入与秘密只读挂载仍归 E3 窗口。

### 2.4 D-05 显式主体映射部署编排（模板已出 / 注入 Blocked）

| 项 | 结果 |
|---|---|
| 适用范围核定 | **OpenLLM `OPENBASE_SUBJECT_MAP` / DPS `DPS_OPENBASE_SUBJECT_MAP`** 两仓有映射表；OpenRAG / OpenMemory 主体由 JWT `sub` 直通 + 受信来源校验承载（不引入第二套映射）；OpenBase 控制面 `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` 覆盖机器主体 |
| 未映射行为核对 | 两仓均为「未命中即拒绝」（`openbase_jwt.py:164-195` / `src/identity/openbase_jwt.py:164-191`）；OpenRAG/OpenMemory 非受信来源 403 fail-closed |
| 注入模板 | ✅ 已产出：`evidence/d/d-05-subject-map-injection-20261101.md` |
| 映射变更审计 | 口径已定：随发布单记录变更人/时间/增删条数（不记主体明文）；变更后做「映射主体放行 + 未映射主体拒绝」两向冒烟 |
| 生产注入 | ⛔ **Blocked**（无生产主机访问权） |

### 2.5 D-04 存量 `ob_k_` Key 到期收敛（Blocked）

| 项 | 结果 |
|---|---|
| 本机可执行性 | ⛔ 本地 PG 为 `scram-sha-256` 且无凭据/无 `POSTGRES_URL`，无法导出 `expires_at IS NULL` 清单 |
| 生产可执行性 | ⛔ 无生产主机访问权（XR-OPS-07 先例） |
| 已产出 | ✅ 只读导出 SQL（显式列，不含 `key_hash`/明文）+ 按租户分批 UPDATE（参数化绑定）+ 每批复核 + 执行记录表：`evidence/d/d-04-expired-key-convergence-20261101.sql` |
| 分批与通过标准 | 按 `scope.tenants` 分组、每批 ≤200 行、截止点取批次执行前导出结果；通过标准 = `expires_at IS NULL` 剩余 0（或仅剩随发布单批准的豁免行） |
| 到期提醒联查 | 复用 C-08 到期清单（`service_keys.py:249`），收敛后核对 ≤7 天/已过期可见 |

**解除条件**：获得生产/准生产 DBA 会话 + 变更单，按 SQL 分批执行并逐批回填执行记录；若存在无法收敛的存量 Key，须逐条登记豁免原因与批准人。

---

## 3. 证据清单（`doc/audit/verification/evidence/d/`）

| 文件 | 对应项 | 内容 |
|---|---|---|
| `d-02-gate-matrix-20261101.json` | D-02 | 13 项门禁 17 例负向结果 + 正向基线（含拒绝原因原文，无秘密） |
| `d-07-issuer-uniqueness-20261101.json` | D-07 | Provider 名称唯一性实测 + issuer 口径与影响面 |
| `d-06-template-key-check-20261101.json` | D-05 / D-06 | 五仓部署键名存在性（只记键名与「存在/缺失」） |
| `d-04-expired-key-convergence-20261101.sql` | D-04 | 导出 + 分批收敛 + 复核 SQL |
| `d-05-subject-map-injection-20261101.md` | D-05 | 主体映射注入模板、约束、变更审计口径 |
| `evidence/a2/a2-e1-template-drift-20261102.json` | D-06 / E1 | E1 补齐后四仓模板/说明键名存在性复核（只记键名与「存在/缺失」） |
| `evidence/a2/a2-d02-negative-e2native-20261102.json` | D-02 / E2 | 私钥缺失时本机原生启动拒绝（exit=1，含拒绝原因摘要） |
| `evidence/a2/a2-e2-native-20261102.json` | D-02 / A2-03 / A2-06 / E2 | 生产形态原生实例启动、`/health`、JWKS（仅公钥/kid 一致）、内省与吊销端点无凭证拒绝、日志秘密扫描 |
| `evidence/e3/e3-native-20261102.json` | D-03 / D-05 / D-06 / K-01 / K-02 / E3 | 四仓本机生产形态取证：OpenBase 启动/JWKS/HS256 拒签/缺 RS256 拒启/明文 Key 拒启/密钥文件放行/映射解析；DPS `closed` 拒静态 Key、应急 bypass 放行+审计仅摘要、缺过期拒启、K-02 本地登录 403；OpenRAG/OpenMemory K-01 策略层 8/8（已脱敏） |

---

## 4. 结论

| 编号 | 判定 | 说明 |
|---|---|---|
| D-02 | **Pass（本地口径）/ ⛔ 生产重启与端点核对 Blocked** | 13 项门禁负向矩阵 17/17 命中，正向基线放行；E2/E3 已完成本机原生与生产形态重启两向验证及 A2 §6.2 端点核对；生产拓扑重启仍待部署环境 |
| D-04 | ⛔ **Blocked** | SQL 与分批计划已就绪，待生产 DBA 会话 |
| D-05 | **Pass（编排口径 + E3 解析口径）/ ⛔ 生产注入 Blocked** | 适用范围收敛为两仓映射 + 两仓直通，模板与审计口径已定；E3 已验证 `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` 单条映射解析与启动放行 |
| D-06 | **Pass（模板/说明补齐 + E3 摘要/密钥文件两形态）/ ⛔ 生产注入与 0600 挂载 Blocked** | 4 处模板/说明漂移已全部补齐；E3 已验证生产摘要/密钥文件两形态放行、生产明文 Key 拒启；生产 `.env` 注入与 PEM 0600 只读挂载归真实生产窗口 |
| D-07 | **部分 Pass** | 名称唯一性门禁生效；issuer 判重为登记前置部署动作 |

**未闭环项全部为环境/权限阻塞，无代码缺口**；解除条件统一为「获得生产（或 Dev 全栈）会话与启停权限」。

---

## 5. E 批联动（2026-11-02）

> 依据《残余项分批推进方案 v1.2.0》§4（E1）、§5（E2）与 §9（E3），**本轮不使用 Docker**：以本机原生进程（`uvicorn` 单进程）+ 生产形态环境变量完成取证；凡需共享 PG/Redis、多实例、真实 IdP 或跨仓生产部署者一律 ⛔ Blocked。

### 5.1 E1（零环境模板补齐）— 5/5 Pass

| 编号 | 动作 | 结果 |
|---|---|---|
| E1-① | OpenBase `.env.shared-infra` 追加生产基线 7 键（注释形态） | ✅ 7 键存在（该文件不被 git 跟踪，真实值由 OPS 注入） |
| E1-② | OpenRAG `.env.example` 追加 K-01 三键 | ✅ 3 键存在 |
| E1-③ | OpenMemory `.env.example` 追加 K-01 三键 | ✅ 3 键存在 |
| E1-④ | DPS 环境配置说明新增 §2.5/§2.6（`IDENTITY_AUTHORITY` / `STATIC_KEY_CHANNEL` + 应急 bypass 两键），升 v2.8.3 | ✅ 键名与 `DPS/src/config.py:200,296` 一致 |
| E1-⑤ | A2 清单修正 DPS 键名前缀笔误（`DPS_IDENTITY_AUTHORITY`/`DPS_STATIC_KEY_CHANNEL` → `IDENTITY_AUTHORITY`/`STATIC_KEY_CHANNEL`） | ✅ 见 A2 v1.1.6 |

证据：`evidence/a2/a2-e1-template-drift-20261102.json`（四仓键名复核，按 `d-06` 同源清单逐项 grep）。

### 5.2 E2（本机原生，无 Docker）

| 项 | 结果 | 证据 |
|---|---|---|
| D-02 负向：私钥 PEM 缺失 → 启动拒绝 | ✅ **拒绝启动**（`exit=1`，`JWT RSA 私钥文件不存在或不可读`） | `a2-d02-negative-e2native-20261102.json` |
| D-02 正向：恢复 PEM → 生产形态启动 | ✅ 启动成功，`/health` 200 | `a2-e2-native-20261102.json` |
| A2-01 生产基线（13 项门禁） | ✅ 本机生产形态全放行（`OPENBASE_ENV=production` + 私钥/kid/require/issuer/租户/主体策略/MCP 摘要齐备） | 同上 |
| A2-03 JWKS | ✅ 200，`key_count=1`、`kty=RSA`、`kid=e2-native-kid`、无任何私钥字段 | 同上 |
| A2-02 端点鉴权 | ✅ 内省无凭证 401、吊销增量（`since=0`/缺省）无凭证 401 | 同上 |
| A2-06 秘密不落日志 | ✅ 进程日志无 `PRIVATE KEY` 头、无 JWT 密钥原文 | 同上 |
| A2-04 / A2-05 | ⛔ **Blocked**：需四仓生产部署与真实服务 Key 权限面取样 | 解除条件：E4 跨仓实测 |
| V-01/02/03/05/06/07/09/13/14 等 A1 实测项 | ⛔ **Blocked**：需共享 PG/Redis、多实例、四仓联调或真实 IdP | 解除条件见《分批推进方案》§5 E2 判定边界 |
| 数据库形态 | ℹ️ 本机 SQLite 初始化因 PG 专用 SQL（schema/`setval`）失败 → 自动回退内存（日志 `database init failed, fallback to memory`），故本机不覆盖 DB 相关语义 | 同上 |

**E2 判定边界**：以上 ✅ 仅为 `Pass（本机口径）`，不替代生产实测。

### 5.3 E3（本机生产形态两向，2026-11-02）

> 目的：把「**凡启动服务即可验证**」的门禁与两向语义一次性跑通（对应台账 D-03/D-05/D-06 与 K-01/K-02）。执行方式：本机原生 `uvicorn` + SQLite（`OPENBASE_ENV=production` / DPS 生产形态环境变量），**无 Docker**；证据 `evidence/e3/e3-native-20261102.json`。

| 编号 | 用例 | 结果 | 证据字段 |
|---|---|---|---|
| D-03 正向 | 生产配置 `jwt_require_rs256=true` + PEM 私钥 + kid 启动 | ✅ 启动 200；JWKS `key_count=1`、`kty=[RSA]`、`kids=[e3-native-kid]`、`private_fields=[]` | `openbase_positive` |
| D-03 负向 | HS256 令牌访问 `/api/v1/auth/me` | ✅ **401** `AUTH_401 invalid or expired token`（白名单收敛生效） | `openbase_positive.hs256_negative` |
| D-03 负向 | 缺 RS256 私钥路径/kid 时启动 | ✅ **拒绝启动** `exit=1`（生产要求 RS256 材料） | `d03_negative_missing_rs256_key` |
| D-05 | `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` 单条映射 | ✅ 解析成功并在生产启动放行（`map_entries=1`） | `openbase_positive.settings_probe` |
| D-06 正向 | 生产配 MCP 摘要启动 | ✅ 200（`mcp_hashes_configured=true`） | `openbase_positive.settings_probe` |
| D-06 正向 | 生产配 `OPENBASE_MCP_API_KEYS_FILE` 启动 | ✅ 200 | `d06_positive_keys_file` |
| D-06 负向 | 生产配明文 `OPENBASE_MCP_API_KEYS` | ✅ **拒绝启动** `exit=1`（生产禁止明文静态 Key） | `d06_negative_plaintext_key` |
| D-06 负向 | PEM 只读挂载 0600 | ⛔ **Blocked**：Windows 无 POSIX mode 可核验 | `d06_permission_0600` |
| K-01 | DPS `STATIC_KEY_CHANNEL=closed`，非应急静态 Key 访问 | ✅ **401** `AUTH_STATIC_KEY_CHANNEL_CLOSED`（服务启动成功） | `k01_closed_reject` |
| K-01 | DPS `closed` + 应急 bypass（带未来过期时间） | ✅ 放行（错误码由 `CLOSED` 转为业务侧「缺少组织或租户标识」）；✅ 审计含事件且**无明文 Key** | `k01_emergency_bypass.audit` |
| K-01 负向 | 应急 bypass 缺过期时间 | ✅ **拒绝启动** `exit=1`（`K-01 启动门禁：应急通道必须有明确过期时间`） | `k01_negative_missing_expiry` |
| K-02 | DPS `IDENTITY_AUTHORITY=openbase`，本地密码登录 | ✅ **403** 含 `AUTH_LOCAL_LOGIN_DISABLED` | `k02_openbase_authority` |
| K-01（OpenRAG） | 静态 Key 通道策略层门禁（`dual`/`closed`/非法归一/缺过期拒启） | ✅ **8/8 断言 true** | `rag_gate_check` |
| K-01（OpenMemory） | 静态 Key 通道策略层门禁 | ✅ **8/8 断言 true** | `memory_gate_check` |
| OpenRAG 整服务启动 | 需 aiohttp/qdrant-client/faiss/sentence-transformers 等重依赖 | ⛔ **Blocked**（本机缺依赖；原生导入崩溃 `0xC0000005`） | `blocked_production_items` |
| OpenMemory 整服务启动 | 快速 API 可导入，但完整服务依赖本机缺失 | ⛔ **Blocked** | `blocked_production_items` |

**E3 判定边界**

- ✅ 一律为 `Pass（本机生产形态）`：验证的是**代码门禁与两向语义**，不替代真实生产主机、共享 PG/Redis、多实例与真实 IdP 实测（E4/E5 仍 ⛔ Blocked）。
- 逐项结果与 Blocked 解除条件见《残余项分批推进方案 v1.2.0》§9.4/§9.5。

