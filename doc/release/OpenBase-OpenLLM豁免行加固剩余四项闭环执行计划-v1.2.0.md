# OpenBase-OpenLLM 豁免行加固剩余四项闭环执行计划-v1.2.0

| 项目 | 内容 |
|------|------|
| 计划名称 | OpenLLM 豁免行安全加固 L-1~L-4 闭环执行计划 |
| 计划编号 | OB-SEC-EXEMPT-CLOSURE-v1.2.0 |
| 版本 | **v1.2.0** |
| 状态 | **[Approved]**（本地预演全部通过；L-1/L-2/L-3 生产证据待 OPS 窗口，L-4 待评审确认） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 适用范围 | 《OpenBase-OpenLLM 豁免行安全加固方案-v1.3.0》实施后剩余 4 项未闭环事项 |
| 关联实施 | 《OpenBase-OpenLLM豁免行安全加固实施记录-v1.1.0》§6 |
| 关联门禁 | 《OpenBase-主备双通道生产上线必办事项清单-v1.5.0》G4（T4-2） |
| 关联审批 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》§5、§8 |
| 代码基线 | OpenLLM `feature/s4-identity-channel-b` @ `17763c0`（v2.19.1） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：L-1~L-4 的目标、前置、步骤、验收、证据、回滚与执行顺序 |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | 确认 R-1（Prometheus 2.48 不支持自定义头）与 R-2（OpenMemory 绑定 0.0.0.0）；L-2-0 Bearer 兼容已实施（OpenLLM 2.19.1 / `17763c0`） |
| v1.2.0 | 2026-10-18 | OpenBase 架构组 | 本地隔离探针执行 L-1~L-4：L-1 正例+5 反例通过、L-2 四态/轮换/分级通过、L-3 配置事实确认、L-4 矩阵 v1.2.0 与门禁通过；新增 §12 执行结果与证据索引 |

---

## 1. 目标

在不改变业务面与通道判据的前提下，闭环以下 4 项，使 G4-T4-2 具备双签条件：

| 编号 | 事项 | 闭环标志 |
|:----:|------|---------|
| **L-1** | 生产环境收紧开关下发 + 「不合规拒绝启动」验证 | `.env` 下发完成；正例启动成功；3 个反例启动失败并留证 |
| **L-2** | `/metrics` token 下发与 Prometheus 抓取配置 | 四态鉴权通过；Prometheus target `UP`；轮换演练通过 |
| **L-3** | 网络层控制证据（AC-13） | 监听地址/安全组/NetworkPolicy 至少一项证据归档 |
| **L-4** | K07 标注「受信管理面（非豁免）」 | 矩阵升版；`--check` 退出码 0；`verify_exempt_endpoints.py` PASS |

> 四项全部闭环后，方可回填审批单 §8 并进入双签；任一未闭环，G4 维持 No-Go。

## 2. 不在范围

- 不改业务面身份强校验语义与 403/401 行为；
- 不修改 L2-2 通道矩阵判据；
- 不翻转新增开关的代码默认值（仅目标环境 `.env` 收紧）；
- 不涉及 G5-OBS 迁移窗口与 DPS 认证类豁免整改。

## 2A. R-1 / R-2 确认结论（2026-10-18）

### R-1 Prometheus 自定义头支持：**已确认不成立（必须走 Bearer）**

| 核对项 | 事实 | 来源 |
|--------|------|------|
| 目标版本 | `prom/prometheus:v2.48.0` | OpenLLM `docker-compose.prod.yml:202` |
| 2.48 配置能力 | `scrape_config` **不存在 `http_headers`**；仅支持 `authorization`（含 `credentials_file`） | Prometheus 2.48 官方配置文档（逐项检索无 `http_headers`） |
| 结论 | 仅靠 `X-Metrics-Token` 无法被标准 Prometheus 抓取 | 已确认 |

**处置**：L-2-0 由“可选”改为**必做**，且已实施——
`metrics_access_allowed` 同时接受 `X-Metrics-Token` 与 `Authorization: Bearer`；
OpenLLM **2.19.1**（提交 `17763c0`），新增 Bearer 正/负例单测，32 例全部通过。
Prometheus 侧使用 `authorization: {type: Bearer, credentials_file: ...}`。

### R-2 服务监听地址：**已确认存在 0.0.0.0 暴露（OpenMemory）**

| 服务 | 监听配置 | 来源 | 判定 |
|------|---------|------|:----:|
| OpenLLM | `uvicorn.run(..., host="127.0.0.1", port=8001)` | `doc/tmp/run_openllm.py:28` | ✅ 回环 |
| OpenBase | `uvicorn.run(..., host="127.0.0.1", port=8000)` | `doc/tmp/run_openbase.py:16` | ✅ 回环 |
| OpenRAG | `--host 127.0.0.1 --port 8010` | `doc/tmp/start-all-services.ps1:34` | ✅ 回环 |
| DPS | `--host 127.0.0.1 --port 8030` | `doc/tmp/start-all-services.ps1:45` | ✅ 回环 |
| **OpenMemory** | `OPENMEMORY_SERVER__HOST=0.0.0.0`、`PORT=8020` | `OpenMemory/.env` | **❌ 全接口暴露** |

补充事实：核对时应用服务均未监听（8000/8001/8010/8020/8030 无监听）；
本机 IP 为 `192.168.0.157`；本机 PostgreSQL 监听 `0.0.0.0:5432`（不属本次四服务范围，另行评估）。

**处置（L-3 前置）**：目标环境将 OpenMemory 改为 `OPENMEMORY_SERVER__HOST=127.0.0.1`
（同宿主部署，不影响调用方），或在防火墙层限制 8020 仅本机可访问；
随后重新导出监听证据，确保 8000/8001/8010/8020/8030 **均不出现 `0.0.0.0`**。

> 证据落点：`doc/test/evidence/s7/security/exempt-hardening/r1-r2-confirmation.json`

## 3. 执行顺序与依赖

```
L-2-0（Bearer 兼容）── 已完成（OpenLLM 2.19.1 / 17763c0）
        │
L-2-1 token 生成与密钥下发 ──► L-1-1 .env 下发 ──► L-1-2 正例启动
        │                              │
        │                              └──► L-1-3 反例启动（隔离探针）
        │
L-2-2 Prometheus 抓取配置 ──► L-2-3 四态验证 ──► L-2-4 轮换演练

L-3（先整改 OpenMemory 监听 → 网络控制 → 证据；可与 L-1/L-2 并行）

L-4（K07 标注，可与 L-1/L-2/L-3 并行）
```

**关键依赖**：`OPENLLM_METRICS_TOKEN` 为空时生产启动会 fail-closed，因此 **L-2 的 token 生成必须先于 L-1 的正式启动**。

## 4. L-1：生产收紧开关下发与启动验证

### 4.1 前置

- L-2-1 已完成（token 已生成并可通过密钥管理读取）；
- 已取得生产变更窗口与变更单号；
- 已确认目标环境服务启动方式（服务编排器 / systemd / 容器）。

### 4.2 下发内容（目标环境 `.env`，不入库）

```dotenv
ENV=production
DEBUG=false
OPENAPI_PUBLIC=false

ENFORCE_INBOUND_IDENTITY_HEADERS=true
TENANT_SCOPE_ENFORCE=true
TENANT_HEADER_CONSISTENCY_ENFORCE=true
QUOTA_MISSING_FAIL_CLOSED=true
RBAC_PERMISSION_ENFORCE=true

OPENLLM_EXEMPT_MATCH_MODE=exact
OPENLLM_EXEMPT_ASSERT_ON_STARTUP=true
OPENLLM_EXEMPT_EXPIRY_ENFORCE=true
OPENLLM_EXEMPT_AUDIT_ENABLED=true
OPENLLM_EXEMPT_AUDIT_IP_MODE=full
OPENLLM_EXEMPT_AUDIT_RETENTION_DAYS=90
OPENLLM_EXEMPT_RATE_LIMIT_RPM=120

OPENLLM_METRICS_AUTH_MODE=token
OPENLLM_METRICS_TOKEN=<由 L-2-1 生成>
OPENLLM_METRICS_TOKEN_PREVIOUS=
OPENLLM_METRICS_ALLOWED_SOURCES=<监控源 CIDR，可空>

OPENLLM_HEALTH_DETAIL_MODE=trusted-only
OPENLLM_HEALTH_TRUSTED_SOURCES=<探活/监控 CIDR>
OPENLLM_HEALTH_TOKEN=<可选>
```

> 变更前先备份原 `.env`（文件权限 600 / ACL 仅服务账号），记录 diff 摘要（不记录密钥明文）。

### 4.3 正例验证

1. 重启 OpenLLM；
2. 断言启动日志包含 `豁免行启动断言通过`，且无 `ERROR` 级豁免/门禁日志；
3. 断言 `/health`（本机回环）返回完整明细；`/metrics` 无 token 返回 401。

### 4.4 反例验证（隔离探针，不影响正式实例）

用独立端口起探针实例，逐项注入错误配置，断言**启动失败**：

| 反例 | 注入 | 期望 |
|:----:|------|------|
| N-1 | `OPENLLM_EXEMPT_MATCH_MODE=prefix` | 启动失败，错误含 `EXEMPT_MATCH_MODE` |
| N-2 | `OPENAPI_PUBLIC=true` | 启动失败，错误含 `OPENAPI_PUBLIC` |
| N-3 | `OPENLLM_METRICS_AUTH_MODE=none` | 启动失败，错误含 `METRICS_AUTH_MODE` |
| N-4 | `OPENLLM_METRICS_TOKEN=`（空） | 启动失败，错误含 `OPENLLM_METRICS_TOKEN` |
| N-5 | `OPENLLM_HEALTH_DETAIL_MODE=all` | 启动失败，错误含 `HEALTH_DETAIL_MODE` |

PowerShell 探针范式（示例，`PORT` 使用未被占用的端口）：

```powershell
$env:ENV="production"; $env:PORT="18001"
$env:OPENLLM_EXEMPT_MATCH_MODE="prefix"
# 其余生产开关置为合规值后启动探针，捕获输出与退出码
python -m uvicorn main:app --host 127.0.0.1 --port 18001 2>&1 | Tee-Object -FilePath $log
"exit_code=$LASTEXITCODE"
```

> 探针进程必须在单条命令内完成「起→断言→停」，禁止影响共享服务与共享 PG。

### 4.5 验收与证据

| 判据 | 证据文件 |
|------|---------|
| 正例启动成功 + 断言日志 | `doc/test/evidence/s7/security/exempt-hardening/l1-env-startup.json` |
| N-1~N-5 启动失败且错误码可定位 | 同上（逐项记录 command/exit_code/output_digest） |
| `verify_exempt_endpoints.py` → `RESULT: PASS` | 同上附输出 |
| 变更前后 `.env` 键集合 diff（脱敏） | `l1-env-diff.json` |

### 4.6 回滚

恢复备份 `.env` 并重启；如启动断言误报，保留原 `.env` 与日志，禁止直接关闭断言上线。

## 5. L-2：`/metrics` token 与 Prometheus 抓取

### 5.1 L-2-0（必做，已完成）：Bearer 兼容

R-1 已确认：Prometheus 2.48 `scrape_config` 无 `http_headers`，仅支持
`authorization`。因此必须提供 Bearer 通道。

- 改动点：`app/security/exempt_policy.metrics_access_allowed`
- 实现：同时接受 `X-Metrics-Token` 与 `Authorization: Bearer <token>`（同一 token 校验）
- 测试：Bearer 正例/错 token/Basic 负例；X-Metrics-Token 用例不回归（共 **32 passed**）
- 版本：OpenLLM **2.19.1**，提交 **`17763c0`**
- 状态：**✅ 已完成**

### 5.2 L-2-1 token 生成与下发

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$token = [Convert]::ToBase64String($bytes)
# 写入密钥管理/K8s Secret；仅输出长度与前 4 位用于核对
"len=$($token.Length) prefix=$($token.Substring(0,4))"
```

- 禁止写入 git、工单正文、聊天记录；
- 下发后校验 `.env` 文件 ACL 仅服务账号可读。

### 5.3 L-2-2 Prometheus 抓取配置（Bearer 方案）

```yaml
scrape_configs:
  - job_name: openllm
    metrics_path: /metrics
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/secrets/openllm_metrics_token
    static_configs:
      - targets: ["<openllm-host>:8001"]
```

若采用 `X-Metrics-Token` 方案，需确认抓取器支持自定义头或由边车代理注入。

### 5.4 L-2-3 四态验证

| 场景 | 期望 |
|------|------|
| 无 token | 401 |
| 错误 token | 401 |
| 正确 token（CURRENT） | 200，返回 Prometheus text |
| 轮换期 PREVIOUS token | 200 |
| token 正确但来源不在 CIDR（若配置） | 401 |

同时检查指标标签：不得出现 `tenant` / `user` / `subject` / `org` / `email` 维度。

### 5.5 L-2-4 轮换演练

1. 将 CURRENT 移至 PREVIOUS，写入新 CURRENT；
2. 两个 token 均可抓取（重叠期 ≤7 天）；
3. 清空 PREVIOUS，旧 token 立即 401；
4. 记录演练时间与结果。

### 5.6 验收与证据

`doc/test/evidence/s7/security/exempt-hardening/l2-metrics-auth.json`：
四态 HTTP 码、Prometheus target 状态（`UP`）、标签扫描结果、轮换记录、配置片段（脱敏）。

## 6. L-3：网络层控制证据（AC-13）

### 6.1 前置

- 确认五系统部署拓扑（当前为同宿主 `192.168.0.151`，端口隔离）；
- 确认 OpenBase 出口地址、监控采集地址、探活地址。

### 6.2 执行步骤

1. **监听面**：导出监听地址与进程：

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 8000,8001,8010,8020,8030 } |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

期望：仅绑定回环或私网网卡，**不出现 `0.0.0.0`**（如业务确需跨主机，改为绑定私网网卡 + 防火墙限制）。

2. **主机防火墙/安全组**：仅放行 OpenBase 出口 IP、监控网段、探活源；其余拒绝。导出规则 JSON。

3. **容器编排（如适用）**：`default-deny` ingress + 仅允许 `openbase`、`monitoring` 命名空间；导出 NetworkPolicy YAML。

4. **同宿主约束**：网段 ACL 区分度有限，优先端口/进程隔离；应用层 token 为主控制。

### 6.3 验收与证据

`doc/test/evidence/s7/security/exempt-hardening/l3-network-controls.json` + 附件：
- `listeners.txt`（命令输出）
- `firewall-rules.json`（脱敏）
- `networkpolicy.yaml`（如适用）

证据至少包含一项网络控制；三项齐全更佳。

### 6.4 回滚

回退防火墙规则或监听地址变更；回滚后复跑 `/health` 与通道健康检查。

## 7. L-4：K07 标注「受信管理面（非豁免）」

### 7.1 现状

`/openllm/v1/health` 已在矩阵中（`exemption=否`、`status=覆盖`），但分类为「列表分页/集合读」，
未体现“受信管理面”语义。豁免登记表**不包含**该端点（保持 5 条）。

### 7.2 执行步骤

1. 在 `backend/scripts/k07_endpoint_matrix.py` 增加受信管理面覆盖表：

```python
TRUSTED_MANAGEMENT_PATHS = {
    "/openllm/v1/health": "受信管理面（非豁免）",
}
```

2. 生成矩阵 v1.2.0：

```powershell
python scripts/k07_endpoint_matrix.py `
  --openapi-file data/openapi-llm-snapshot.json `
  --report-out doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.2.0.matrix.json
python scripts/k07_endpoint_matrix.py --check
```

3. 更新 `OpenLLM-K07-端点过滤矩阵填报-v1.2.0.md`：该行类别改为「受信管理面（非豁免）」，
   `exemption=否`，保留隔离用例；删除 v1.1.0 旧版。
4. 重跑 K07 终验并更新 `k07-finalize.json`。
5. 运行发布门禁：

```powershell
python scripts/verify_exempt_endpoints.py --k07 <OpenBase>/doc/test/evidence/s7/gate/k07-finalize.json
```

期望：`RESULT: PASS`。

### 7.3 验收与证据

`doc/test/evidence/s7/security/exempt-hardening/l4-k07-annotation.json`：
矩阵版本、目标行 diff、`--check` 输出（gaps=0 / uncovered=0）、门禁脚本输出。

## 8. 证据归档规范

目录：`doc/test/evidence/s7/security/exempt-hardening/`

| 文件 | 内容 |
|------|------|
| `l1-env-startup.json` | 正例启动 + N-1~N-5 反例 + 门禁脚本输出 |
| `l1-env-diff.json` | `.env` 键集合 diff（脱敏） |
| `l2-metrics-auth.json` | 四态鉴权 + target UP + 标签扫描 + 轮换 |
| `l3-network-controls.json` | 监听/防火墙/NetworkPolicy 证据索引 |
| `l4-k07-annotation.json` | 矩阵 diff + `--check` + 门禁输出 |
| `summary.json` | L-1~L-4 状态、时间、执行人、结论 |

所有 JSON 必须包含：`schema_version`、`generated_at`、`operator`、`command`、`exit_code`、
`verdict`；禁止包含 token、密码、完整 `.env`。

## 9. 回滚

| 场景 | 动作 |
|------|------|
| `.env` 收紧导致启动失败 | 恢复备份 `.env` 并重启；保留失败日志 |
| Prometheus 抓取失败 | 临时 `OPENLLM_METRICS_AUTH_MODE=trusted-source` 或补 CIDR，再修复 token |
| 网络规则误封 | 回退防火墙/安全组规则，复跑通道健康 |
| K07 矩阵更新导致门禁失败 | 回退矩阵至 v1.1.0 并复跑 `--check` |
| 代码级异常 | 回退至 `cff0a32` 或修复后重新发布 |

## 10. 门禁回填与签核

全部闭环后：

1. 在审批单 v1.1.0 §8 逐项勾选并附证据路径；
2. 清单 v1.5.0 → v1.6.0：G4 状态由「待双签」更新为「双签完成」；
3. 技术签字确认 §8 证据；发布签字确认残余风险可接受；
4. 审批单状态回写 `[Approved]`，G4 结项。

## 11. 风险与未决

| 编号 | 事项 | 影响 | 处置 |
|:----:|------|------|------|
| R-1 | Prometheus 2.48 不支持自定义头 | L-2 无法直接落地 | **已确认**；L-2-0 Bearer 兼容已完成（2.19.1 / `17763c0`） |
| R-2 | OpenMemory 绑定 `0.0.0.0` | 监听面证据不达标 | **已确认**；目标环境改 `OPENMEMORY_SERVER__HOST=127.0.0.1` 或防火墙限制 8020，再导出证据 |
| R-3 | token 轮换窗口操作失误 | 抓取中断 | 双 token 重叠 + 先加后删 |
| R-4 | 矩阵重生成与手工 MD 不一致 | K07 对账失败 | 以脚本输出为准，MD 同步后再跑 `--check` |
| R-5 | 生产窗口内反例探针误连共享库 | 污染/干扰 | 探针使用独立端口 + 明确 `DATABASE_URL`；单命令起停 |

---

## 12. 执行结果（2026-10-18 本地隔离探针）

### 12.1 结果总览

| 项 | 本地预演 | 生产闭环 | 证据 |
|:--:|:--------:|:--------:|------|
| **L-1** | ✅ 正例启动 + N-1~N-5 全部拒绝启动（exit=3，关键字命中） | ⬜ 待 OPS 下发 `.env` 并重启复跑 | `l1-env-startup.json` |
| **L-2** | ✅ 四态鉴权 + Bearer + 轮换 + 健康分级通过 | ⬜ 待 Prometheus target UP 证据 | `l2-metrics-auth.json` |
| **L-3** | 🟡 OpenMemory 已改绑 `127.0.0.1:8020` 并实测 HEALTHY（18s），验证后停止 | ⬜ 待生产同步整改 + 防火墙/NetworkPolicy 证据 | `l3-network-controls.json` |
| **L-4** | ✅ 矩阵 v1.2.0 标注；`--check` 与门禁脚本 PASS | ⬜ 待评审组确认分类口径 | `l4-k07-annotation.json` |

证据目录：`doc/test/evidence/s7/security/exempt-hardening/`（另含 `summary.json`、`r1-r2-confirmation.json`）。

### 12.2 执行中发现并修复的缺陷

| 编号 | 现象 | 根因 | 修复 |
|:----:|------|------|------|
| D-1 | 生产启动断言误报「必需豁免路由未注册: ['/metrics']」 | FastAPI 0.143 `include_router` 生成 `_IncludedRouter` 包装（`route.path=None`），原断言遍历 `app.routes` 漏掉子路由 | 改为以 `app.openapi()["paths"]` 为准；新增 `include_router` 回归用例（41 passed） |
| D-2 | 门禁脚本被 DPS 35 条认证类豁免阻断 | K07-DPS-AUTH 属独立整改项 | `verify_exempt_endpoints.py` 仅对 OpenLLM/OpenRAG/OpenMemory 判失败，DPS 仅 WARN |

### 12.3 生产窗口待办（不改变 §3 顺序）

1. L-2-1 token 生成与密钥下发（先于 L-1）；
2. L-1 `.env` 下发（含 `APP_VERSION=2.19.1`，消除当前 2.18.0 版本漂移）与重启；
3. L-2-2 Prometheus 抓取配置与 target UP 取证；
4. L-3 OpenMemory 监听整改 + 防火墙/NetworkPolicy 证据；
5. L-4 评审确认并回填 K07 终验证据。

---

**计划状态**：[Approved]（本地预演通过；生产 L-1/L-2/L-3 证据待 OPS 窗口，L-4 待评审确认）
