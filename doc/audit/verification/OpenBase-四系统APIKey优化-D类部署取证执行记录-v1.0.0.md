# OpenBase 四系统 API Key 优化 —— D 类部署取证执行记录

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0.0 |
| 文档状态 | [Review] |
| 适用环境 | Dev（本机）/ Pre-Pro / Pro |
| 关联台账 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项统一处置方案-v1.0.9.md`（§6 D 行、§5.4） |
| 关联清单 | `...-A2生产配置收口清单-v1.1.5.md`（§4 门禁、§6 漂移自检、§7 验收项） |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.26.0.md`（§10.29） |
| 覆盖对象 | D-02 / D-04 / D-05 / D-06 / D-07（P4 批 D 全部 5 项） |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
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
| OpenBase 生产基线键（RS256 私钥路径/kid/require、issuer、IdP 登记、MCP 摘要、服务账号主体映射） | ⛔ `.env.shared-infra` 中 **7 个键均缺失** → 生产基线尚未注入 | `evidence/d/d-06-template-key-check-20261101.json` |
| OpenLLM 模板（JWKS/issuer/吊销/服务 Key/主体映射） | ✅ 5/5 存在 | 同上 |
| OpenRAG 模板（JWKS/issuer/吊销/服务 Key） | ✅ 4/4 存在；⛔ `OPENRAG_API_STATIC_KEY_CHANNEL`（K-01 新增）**未进模板** | 同上 |
| OpenMemory 模板（JWKS/issuer/吊销/服务 Key） | ✅ 4/4 存在；⛔ `OPENMEMORY_GATEWAY_STATIC_KEY_CHANNEL`（K-01 新增）**未进模板** | 同上 |
| DPS 环境配置说明（JWKS/issuer/吊销/服务 Key/主体映射） | ✅ 5/5 存在；⛔ `DPS_IDENTITY_AUTHORITY`（K-02 新增）与 `STATIC_KEY_CHANNEL`（K-01 新增）**未进说明** | 同上 |
| 秘密挂载形态（PEM 只读 0600、证书/私钥路径、CA） | ⛔ **Blocked**：无部署主机；口径按 A2 §5 留档（私钥 PEM 只读挂载 0600，禁止内联 env） | 解除条件：获得部署主机后按 A2 §5 逐项挂载并记录挂载权限 |

**D-06 缺项处置**：以上 4 处属**模板/说明漂移**（代码已支持、文档未登记），归入发布窗口前必须补齐的部署编排清单；本记录只登记缺项，不修改各仓默认值或模板文件（避免与发布窗口变更冲突）。

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

---

## 4. 结论

| 编号 | 判定 | 说明 |
|---|---|---|
| D-02 | **Pass（本地口径）/ ⛔ 生产重启与端点核对 Blocked** | 13 项门禁负向矩阵 17/17 命中，正向基线放行；真实重启与 JWKS/吊销端点核对待部署环境 |
| D-04 | ⛔ **Blocked** | SQL 与分批计划已就绪，待生产 DBA 会话 |
| D-05 | **Pass（编排口径）/ ⛔ 注入 Blocked** | 适用范围收敛为两仓映射 + 两仓直通，模板与审计口径已定 |
| D-06 | **部分 Pass（键名核对）/ ⛔ 挂载与注入 Blocked** | 发现 4 处模板/说明漂移需在发布窗口前补齐 |
| D-07 | **部分 Pass** | 名称唯一性门禁生效；issuer 判重为登记前置部署动作 |

**未闭环项全部为环境/权限阻塞，无代码缺口**；解除条件统一为「获得生产（或 Dev 全栈）会话与启停权限」。下一轮推进建议：先在 Dev 全栈（docker + 本地 Redis）补做真实重启、JWKS/吊销端点与挂载权限取证，再随生产窗口执行 D-04 分批收敛与 D-05/D-06 注入。
