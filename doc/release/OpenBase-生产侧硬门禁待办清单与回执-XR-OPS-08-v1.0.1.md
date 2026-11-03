# OpenBase 生产侧硬门禁待办清单与回执 - XR-OPS-08 - v1.0.1

| 项 | 内容 |
|---|---|
| 项目名称 | OpenBase（开放底座）四系统 API Key 与授权治理 |
| 单据编号 | **XR-OPS-08-APIKEY-001-GATE** |
| 文档版本 | v1.0.1 |
| 状态 | **[Review] 待 OPS 接收与人工批准** |
| 适用环境 | 生产环境（Pro）；本清单**不适用于**本机 / 测试实例 |
| 创建日期 | 2026-11-03 |
| 编制 | FA-OpenBase-Dev（AI 辅助） |
| 执行方 | OPS（生产环境）+ 生产 DBA（仅 G-4） |
| 上游单据（唯一事实源） | 《OpenBase-四系统APIKey优化生产窗口执行单与回滚方案-v1.0.5》§3 / §4 阶段 1 / §8 / §11 附录 B |
| 配置键名权威 | 《OpenBase-四系统APIKey优化-A2生产配置收口清单-v1.2.0》§3 |
| 判决口径权威 | 《…-A1生产验收清单-v1.1.8》；A2 v1.2.0 §7 |
| 本单用途 | 把阶段 0 遗留的 **5 类生产侧 Blocked** 拆成可勾选、可回执、可归档的待办项；**闭合后方可启动阶段 1（P-03）** |

> **本单性质**：执行清单，不新增技术方案、不改任何仓库源码与 `.env`。所有取值口径、禁止项、回滚口径以上游执行单 v1.0.5 为准；本单与之冲突时以上游为准。

---

## 1. 门禁总览

| 编号 | 门禁 | 待办主题 | 责任方 | 阻断对象 |
|---|---|---|---|---|
| **G-1** | F0-6 | PEM 私钥 `0600` 只读挂载 | OPS + 安全 | 阶段 1（P-03） |
| **G-2** | F0-7 | 共享网关生产地址与路由参数下发 | 网络 / OPS | 阶段 1（P-03）、阶段 3 网关验证 |
| **G-3** | F0-7 | 共享 IdP 生产参数与 issuer 判重 | IdP 管理员 / OPS | 阶段 1（P-03）、阶段 2 登录链路 |
| **G-4** | F0-8 | DBA 会话、变更单与生产 PG 基线复核 | 生产 DBA | 阶段 1（P-03）、阶段 4（P-01） |
| **G-5** | RF-03 | DPS `.env` 18 键生产基线填值 | OPS + 研发 | 阶段 1（P-03） |
| **G-6** | RF-04 | 四仓注释态键转有效值（58 键） | OPS | 阶段 1（P-03） |

**闭合总量**：G-1~G-4 为能力/授权类前置（4 项），G-5 / G-6 为配置填值类（76 键 = DPS 18 + 四仓 58：OpenBase 9 / OpenLLM 15 / OpenRAG 17 / OpenMemory 17）。

> 计数口径以 §8.3 逐仓受检键数为准（9 + 15 + 17 + 17 + 18 = **76**）；v1.0.3 修订摘要中「共 74 键」为笔误，不影响逐仓清单。

**依赖顺序**：

```
G-4 变更单/会话预约 ─┐
G-2 网关地址 ────────┼→ G-5 / G-6 .env 填值 → 键存在性复核 → 阶段 1（P-03）
G-3 IdP 参数 ────────┤
G-1 PEM 挂载 ────────┘
```

---

## 2. 待办总表（可勾选）

| 编号 | 待办 | 前置 | 完成判据 | 证据 / 回执 |
|---|---|---|---|---|
| G-1.1 | 私钥 PEM 由密钥管理下发至生产宿主 | 变更单已开 | 文件到位、来源可追溯 | 下发回执（只记路径与指纹，不记内容） |
| G-1.2 | `install -m 600 -o <服务账号> -g <服务组>` 落盘 | G-1.1 | `stat` 显示 `600 <服务账号>:<服务组>` | `stat -c '%a %U:%G %n'` 输出 |
| G-1.3 | 只读挂载与最小权限验证 | G-1.2 | 非 OpenBase 账号读取返回 `EACCES`；OpenBase 可读 | 权限测试输出 |
| G-1.4 | 负向验证：移走 PEM → OpenBase 拒启 | G-1.2 | 进程退出且日志命中 D-02 私钥门禁 | 退出码 + 日志片段（打码） |
| G-1.5 | 日志抽样扫描 PEM 头 | G-1.2 | 无 `BEGIN PRIVATE KEY` / `BEGIN RSA PRIVATE KEY` | 扫描命令与命中数 `0` |
| G-2.1 | 下发 OpenBase 生产对外 base URL 与 JWKS / 吊销端点 | 无 | 三端点可经网关访问并 200 | 字段表（§4.1） |
| G-2.2 | 下发网关超时、代理透传与可信代理网段 | G-2.1 | 网关超时 ≥ `3.0s`；仅网关网段可透传身份 | 网关配置快照 |
| G-2.3 | 五仓路由与端口映射确认 | G-2.1 | 五仓经网关可达（8000/8001/8010/8020/8030） | 路由表 |
| G-3.1 | 下发 IdP issuer 与端点集合 | 无 | 字段齐备、`issuer` 唯一 | 字段表（§5.1） |
| G-3.2 | 下发 client_id / client_secret / redirect_uri / scopes | G-3.1 | 秘密仅在生产 `.env` 或密钥挂载，不落回执 | 「已配置」状态 |
| G-3.3 | `OPENBASE_IDP_PROVIDERS` JSON 组装与判重 | G-3.1 / G-3.2 | `name` 唯一、`issuer` 唯一、JSON 可解析 | 校验输出（不含 secret） |
| G-4.1 | 开变更单并预约 DBA 会话 | 阶段 0 已闭合 | 变更单号 + 窗口 + 执行人已登记 | 变更单号 |
| G-4.2 | 生产实例复核 `service_api_keys` 四列（RF-01 幂等 DDL） | G-4.1 | `ADD COLUMN IF NOT EXISTS` 执行完成，列数 15 | DDL 与 `\d` 输出 |
| G-4.3 | 生产实例重跑 P-01 基线 | G-4.2 | `verdict=BASELINE_CAPTURED`、`missing_required_columns=[]` | 基线 JSON |
| G-5.1 | DPS `.env` 备份 | 无 | `.env.bak-xrops08-<时间戳>` 存在 | 备份路径 |
| G-5.2 | DPS 写入 18 键生产基线 | G-2 / G-3 / G-5.1 | 18 键全部 `present`，无重复 | 回执表（§7.2） |
| G-5.3 | DPS 重启并探活 | G-5.2 | `/health/liveness` 200，日志无致命项 | 探活输出 |
| G-6.1 | 四仓 `.env` 备份 | 无 | 四份备份存在 | 备份路径 |
| G-6.2 | 四仓 58 键由注释态转有效值 | G-2 / G-3 / G-6.1 | 各仓 `commented=0`、`duplicate=0` | 回执表（§8.2） |
| G-6.3 | 四仓重启并探活 | G-6.2 | 四仓 `/health` 200，JWKS/吊销拉取无致命错误 | 探活输出 |
| G-7 | 统一复核与回执归档 | G-1~G-6 | 五仓键存在性复核全绿 + 回执签署 | 回执（§9） |

---

## 3. G-1：F0-6 PEM `0600` 只读挂载

### 3.1 操作步骤

```bash
# 1) 落盘（属主 = OpenBase 服务运行账号；目录建议 root 拥有、服务账号仅可读）
install -m 600 -o <服务账号> -g <服务组> \
  "<密钥管理下发的私钥>" "<挂载绝对路径>/openbase-rs256.pem"

# 2) 权限与属主核验（判据：600 <服务账号>:<服务组>）
stat -c '%a %U:%G %n' "<挂载绝对路径>/openbase-rs256.pem"

# 3) 最小权限验证（非服务账号读取应失败）
sudo -u <其他账号> test -r "<挂载绝对路径>/openbase-rs256.pem"; echo "exit=$?"   # 期望非 0

# 4) 日志扫描（判据：命中数 0）
grep -c -E 'BEGIN (RSA )?PRIVATE KEY' <OpenBase 日志目录>/*.log
```

### 3.2 完成判据

| 判据 | 期望 |
|---|---|
| 权限位 | `600` |
| 属主 / 属组 | `<服务账号>:<服务组>` |
| 只读挂载 | 服务进程不可写；非服务账号不可读 |
| 负向验证 | 移走 PEM 后 OpenBase **拒绝启动**（D-02 私钥门禁命中） |
| 日志 | 无 PEM 头、无私钥内容片段 |
| 启动 | 恢复 PEM 后 `/health` 200、`/api/v1/auth/jwks` 仅返回公钥 |

### 3.3 回滚

恢复原 PEM（或按 `R-03` 恢复 `.env` 与挂载）→ 重启 OpenBase → 复核 `/health` 200。**不得只改权限不重启**。

---

## 4. G-2：F0-7 共享网关生产地址与路由

### 4.1 需下发的字段（OPS 填写）

| 字段 | 填写栏 | 用途 / 校验 |
|---|---|---|
| OpenBase 生产对外 base URL | `__________` | 三下游 `*_JWKS_URL` / `*_REVOCATIONS_URL` 拼接根 |
| JWKS 端点 | `__________`（默认 `<base>/api/v1/auth/jwks`） | 直接访问 200 |
| 吊销端点 | `__________`（默认 `<base>/api/v1/auth/revocations`） | 增量拉取 200 |
| 网关超时 | `__________`（**必须 ≥ 3.0s**） | 需 ≥ `*_JWKS_TIMEOUT_SECONDS=3.0` |
| 可信代理网段（CIDR） | `__________` | `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` 取值依据 |
| 五仓内部路由 | OpenBase `8000` / OpenLLM `8001` / OpenRAG `8010` / OpenMemory `8020` / DPS `8030` | 逐仓经网关可达 |
| `X-Forwarded-*` 透传策略 | `__________` | 身份透传仅限网关来源 |
| TLS 证书 / CA | `__________` | 下游信任链 |

### 4.2 完成判据

- 经网关访问 JWKS / 吊销端点均 200，且响应不含私钥材料。
- 网关超时配置 ≥ `3.0s`（变更前后各取一次快照）。
- 仅可信代理网段可透传身份头；直连请求身份头被丢弃。
- 五仓经网关可达，状态码符合各自健康路由口径（DPS `/health/liveness`、OpenRAG `/openapi.json` 等）。

---

## 5. G-3：F0-7 共享 IdP 生产参数

### 5.1 需下发的字段（IdP 管理员填写）

| 字段 | 填写栏 | 校验点 |
|---|---|---|
| `issuer` | `__________` | **全局唯一**；与三下游 `*_JWT_ISSUER` 完全一致 |
| `authorization_endpoint` | `__________` | 登录往返可用 |
| `token_endpoint` | `__________` | 换取令牌成功 |
| `jwks_uri` | `__________` | 可拉取签名公钥 |
| `client_id` | `__________` | 与 IdP 登记一致 |
| `client_secret` | **仅生产 `.env` / 密钥挂载** | 回执只记「已配置」 |
| `redirect_uri` | `__________` | 与 OpenBase 回调路由完全一致 |
| `scopes` | `__________` | 覆盖 sub / email / roles 所需声明 |
| back-channel logout 端点 | `__________` | 仅一个 Provider 承担，避免定位歧义 |
| 签名算法 | 期望 `RS256` | `OPENBASE_JWT_REQUIRE_RS256=true` |
| 证书 / CA | `__________` | 网关与 OpenBase 均信任 |

### 5.2 完成判据

- 字段齐备；`issuer` 判重通过（仅一个 Provider 承担 back-channel logout）。
- `OPENBASE_IDP_PROVIDERS` JSON 可解析，`name` 唯一、`issuer` 唯一。
- `client_secret` 等秘密未出现在本单、回执、日志、git 中。

---

## 6. G-4：F0-8 DBA 会话、变更单与生产 PG 基线

### 6.1 待办

- [ ] 6.1.1 开变更单：登记**变更单号、回滚窗口、执行人、DBA 值班人**。
- [ ] 6.1.2 预约 DBA 会话（跳板机 / 审批链路），确认生产实例连接串来源。
- [ ] 6.1.3 生产实例复核 `service_api_keys` 四列，执行幂等 DDL（`ADD COLUMN IF NOT EXISTS` ×4：`expires_at` / `last_used_at` / `rotated_from` / `tenant_code`）。
- [ ] 6.1.4 会话参数：`lock_timeout=3s`、`statement_timeout=30s`；**不得**执行 `Base.metadata.create_all`。
- [ ] 6.1.5 重跑 P-01 基线（只读事务，`statement_timeout=5s`）。
- [ ] 6.1.6 归档 DDL 文本、执行时间、影响行数（期望 `0`）。

### 6.2 完成判据

| 判据 | 期望 |
|---|---|
| 列结构 | 15 列，`missing_required_columns=[]` |
| 基线判决 | `verdict=BASELINE_CAPTURED` |
| 无过期键计数 | `baseline_remaining_without_expiry` 已记录 |
| 影响面 | 未跨 schema 操作、未无条件全表 `UPDATE` |

### 6.3 回滚

`ADD COLUMN IF NOT EXISTS` 为幂等增量，**不回退列**；若基线异常，停止后续阶段并按 `R-01` 处置。

---

## 7. G-5：RF-03 —— DPS `.env` 18 键生产基线

### 7.1 前置与步骤

1. 备份：`cp .env .env.bak-xrops08-$(date +%Y%m%d-%H%M%S)`（保留至窗口关闭后 ≥7 天）。
2. 按 A2 v1.2.0 §3 逐键写入 18 键；秘密键只写引用/密文来源，不写进回执。
3. 唯一性校验：每键 `grep -c "^KEY="` 结果必须为 `1`。
4. 重启 DPS → `/health/liveness` 200 → 复核日志无「未配置 JWKS/吊销」致命项。

### 7.2 18 键回执表（OPS 填写）

| # | 键 | 类型 | 状态（已配置 / 未配置 / 保持未设置） | 校验点 |
|---|---|---|---|---|
| 1 | `DPS_OPENBASE_JWKS_URL` | 非秘密 |  | 拉取 200 |
| 2 | `DPS_OPENBASE_JWKS_CACHE_TTL_SECONDS` | 数值 |  | 缓存有效期合理 |
| 3 | `DPS_OPENBASE_JWKS_TIMEOUT_SECONDS` | 数值 |  | `3.0` 且网关超时 ≥ 该值 |
| 4 | `DPS_OPENBASE_JWT_ISSUER` | 非秘密 |  | 与 OpenBase 一致 |
| 5 | `DPS_OPENBASE_JWT_AUDIENCE` | 非秘密 |  | 受众校验通过 |
| 6 | `DPS_OPENBASE_JWT_LEEWAY_SECONDS` | 数值 |  | 时钟偏差容忍 |
| 7 | `DPS_OPENBASE_REVOCATIONS_URL` | 非秘密 |  | 拉取 200 |
| 8 | `DPS_OPENBASE_SERVICE_KEY` | 秘密 |  | 调用 200；吊销后 401 |
| 9 | `DPS_OPENBASE_REVOCATION_SYNC_INTERVAL_SECONDS` | 数值 |  | 同步周期生效 |
| 10 | `DPS_OPENBASE_REVOCATION_STRICT` | 布尔 |  | `true`（不可达时拒绝） |
| 11 | `DPS_OPENBASE_SUBJECT_MAP` | 映射 |  | 映射命中；回滚不清空 |
| 12 | `DPS_OPENBASE_TRUST_LOCAL_SUBJECT` | 布尔 |  | `false` |
| 13 | `IDENTITY_AUTHORITY` | 枚举 |  | `openbase`；**无 `DPS_` 前缀** |
| 14 | `STATIC_KEY_CHANNEL` | 枚举 |  | 阶段 1 保持 `dual`；**无前缀** |
| 15 | `EMERGENCY_BYPASS_KEY` | 秘密 |  | 仅窗口内有效；**无前缀** |
| 16 | `EMERGENCY_BYPASS_EXPIRES_AT` | 时间 |  | 明确到期时间，不得空；**无前缀** |
| 17 | `IDENTITY_ROLE_CONTRACT_URL` | 非秘密 |  | 契约拉取成功；**无前缀** |
| 18 | `DPS_OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED` | 布尔 |  | `true` |

> **前缀陷阱**：第 13~17 项共 5 键在源码 `DPS/src/config.py` 中**不带 `DPS_` 前缀**，误加前缀等同未配置。

### 7.3 闭合判据

`present=18`、`commented=0`、`duplicate=0`，且重启后探活 200。

---

## 8. G-6：RF-04 —— 四仓注释态键转有效值（58 键）

### 8.1 逐仓待办与计数

| 仓 | 受检键 | 当前 present / commented / absent | 待办要点 | 闭合判据 |
|---|---|---|---|---|
| OpenBase | 9 | 0 / 7 / 2 | 7 键转有效值；补 `OPENBASE_ENFORCE_TOKEN_VERSION`、`OPENBASE_OIDC_STATE_TTL_SECONDS` | `commented=0`、`duplicate=0` |
| OpenLLM | 15 | 0 / 12 / 3 | 12 键转有效值；补 `IDENTITY_AUTHORITY`、`OPENBASE_REVOCATION_BACKGROUND_SYNC_ENABLED`、`QUOTA_ALGORITHM` | 同上 |
| OpenRAG | 17 | 2 / 13 / 2 | 13 键转有效值；补 `OPENRAG_IDENTITY_ROLE_CONTRACT_URL`、`..._REVOCATION_BACKGROUND_SYNC_ENABLED` | 同上 |
| OpenMemory | 17 | 0 / 14 / 3 | 14 键转有效值；补 `ALLOW_UNVERIFIED_GATEWAY_TOKEN`、`OPENMEMORY_IDENTITY_ROLE_CONTRACT_URL`、`..._REVOCATION_BACKGROUND_SYNC_ENABLED` | 同上 |

> 逐键取值来源、类型与校验点见上游执行单 v1.0.5 §11.2~§11.5（本单不重复展开，避免双事实源）。

### 8.2 四仓回执表（OPS 填写，键级）

| 仓 | 键 | 状态（已配置 / 未配置 / 保持未设置） | checked_at | checked_by |
|---|---|---|---|---|
| OpenBase | `__________` |  |  |  |
| OpenLLM | `__________` |  |  |  |
| OpenRAG | `__________` |  |  |  |
| OpenMemory | `__________` |  |  |  |

> 秘密键（`*_SERVICE_KEY`、`*_EMERGENCY_BYPASS_KEY`、`OPENBASE_IDP_PROVIDERS` 内 `client_secret`）**只记「已配置」**。

### 8.3 强制禁止项

1. 不得用注释行充当生效值。
2. 不得用测试实例服务 Key 冒充生产 Key。
3. 不得启用 `ALLOW_UNVERIFIED_GATEWAY_TOKEN`（`true` 即视为窗口失败）。
4. 不得放宽 `*_REVOCATION_STRICT` 以绕过同步失败。
5. 不得以「清空主体映射」作为回滚手段。

---

## 9. 统一回执与签署

### 9.1 回执头

| 项 | 填写 |
|---|---|
| 变更单号 |  |
| 窗口起止时间 |  |
| OPS 执行人 / DBA / 复核人 |  |
| 五仓 `git rev-parse HEAD` |  |
| 各仓 `.env` 备份路径（含 `.env.shared-infra`） |  |

### 9.2 门禁回执

| 编号 | 门禁 | 判决（Pass / Fail / Blocked） | 证据路径 | 备注 |
|---|---|---|---|---|
| G-1 | F0-6 PEM `0600` |  |  |  |
| G-2 | F0-7 网关地址 |  |  |  |
| G-3 | F0-7 IdP 参数 |  |  |  |
| G-4 | F0-8 DBA 会话 / 基线 |  |  |  |
| G-5 | RF-03 DPS 18 键 |  |  |  |
| G-6 | RF-04 四仓 58 键 |  |  |  |
| G-7 | 统一复核 |  |  |  |

### 9.3 证据归档

| 证据 | 路径 |
|---|---|
| 门禁回执（本单填写件） | `doc/audit/verification/evidence/xr-ops-08/gates/xr08-gates-receipt-<YYYYMMDD>.md` |
| PEM `stat` / 权限测试 / 负向验证 | `.../gates/xr08-g1-pem-<YYYYMMDD>.txt` |
| 网关与 IdP 字段表（去秘密） | `.../gates/xr08-g2g3-gateway-idp-<YYYYMMDD>.md` |
| DDL 与 P-01 基线 | `.../gates/xr08-g4-dba-baseline-<YYYYMMDD>.json` |
| 键存在性复核（DPS + 四仓） | `.../gates/xr08-g5g6-keys-<YYYYMMDD>.json` |

### 9.4 签署

| 角色 | 姓名 | 签署时间 |
|---|---|---|
| OPS 执行人 |  |  |
| 生产 DBA |  |  |
| 复核人 / 审计 |  |  |

---

## 10. 风险与禁止项

| 风险 | 影响 | 缓解 |
|---|---|---|
| PEM 权限放大或属主错误 | 私钥泄露 | 只读 `0600`、指定属主、仅 OpenBase 挂载、日志抽样扫描 |
| 网关超时 < 3s | JWKS/吊销拉取失败、验签降级 | 变更前后各取快照，确认 ≥ `3.0s` |
| IdP `issuer` 重复 | back-channel 登出定位歧义 | 登记前判重，仅一个 Provider 承担 |
| 生产 PG 长事务锁表 | 五仓读写受阻 | `lock_timeout=3s` / `statement_timeout=30s`，单批 ≤200 行 |
| 服务 Key 多处消费 | 收敛即全下游 401 | 先签新 → 全量替换 → 验证 → 再收敛 |
| 键误加前缀（DPS 5 键） | 等同未配置 | 按 §7.2 清单逐键核对，禁止批量改写 |
| 秘密落盘 | 合规事故 | 秘密只记「已配置」，不写回执/日志/git |
| 以本机结果替代生产 | 验收失真 | 本清单仅在 Pro 环境执行，证据须来自生产实例 |

---

## 11. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.1 | 2026-11-04 | FA-OpenBase-Dev（AI 辅助） | 修正 G-2.3 与 §4.1 的端口映射口径：由过期的「8000/8013/8020/8030/8040」改为与 `scripts/service-orchestrator.ps1` 一致的「OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030」；其余门禁判据与禁止项不变 |
| v1.0.0 | 2026-11-03 | FA-OpenBase-Dev（AI 辅助） | 初始创建：将上游执行单 v1.0.5 阶段 0 遗留的 5 类生产侧 Blocked 拆解为 G-1~G-7 可勾选待办；给出 PEM `0600` 操作与判据、网关/IdP 字段下发表、DBA 会话与基线复核口径、DPS 18 键与四仓 58 键回执表、统一回执签署与证据归档路径 |
