# OpenBase-OpenLLM 豁免行加固剩余四项闭环执行计划-v1.0.0

| 项目 | 内容 |
|------|------|
| 计划名称 | OpenLLM 豁免行安全加固 L-1~L-4 闭环执行计划 |
| 计划编号 | OB-SEC-EXEMPT-CLOSURE-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Draft]**（待 OPS / 评审组确认后进入执行窗口） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 适用范围 | 《OpenBase-OpenLLM 豁免行安全加固方案-v1.3.0》实施后剩余 4 项未闭环事项 |
| 关联实施 | 《OpenBase-OpenLLM豁免行安全加固实施记录-v1.1.0》§6 |
| 关联门禁 | 《OpenBase-主备双通道生产上线必办事项清单-v1.5.0》G4（T4-2） |
| 关联审批 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》§5、§8 |
| 代码基线 | OpenLLM `feature/s4-identity-channel-b` @ `cff0a32`（v2.19.0） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：L-1~L-4 的目标、前置、步骤、验收、证据、回滚与执行顺序 |

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

## 3. 执行顺序与依赖

```
L-2-0（可选代码调整：Bearer 兼容）
        │
L-2-1 token 生成与密钥下发 ──► L-1-1 .env 下发 ──► L-1-2 正例启动
        │                              │
        │                              └──► L-1-3 反例启动（隔离探针）
        │
L-2-2 Prometheus 抓取配置 ──► L-2-3 四态验证 ──► L-2-4 轮换演练

L-3（网络控制，可与 L-1/L-2 并行）

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

### 5.1 L-2-0（可选，推荐）：Bearer 兼容

当前实现仅接受 `X-Metrics-Token`。标准 Prometheus 抓取配置原生支持
`authorization: {type: Bearer, credentials_file: ...}`，对自定义头支持有限。
建议补充 **`Authorization: Bearer <token>` 与 `X-Metrics-Token` 双通道**（同一 token 校验），
避免依赖代理注入或非标准抓取器。

- 改动点：`app/security/exempt_policy.metrics_access_allowed`
- 测试：新增 Bearer 正/负例，保持 X-Metrics-Token 用例不回归
- 版本：OpenLLM `2.19.1`（修订号）

> 若监控侧确认支持自定义头（vmagent/代理注入），可跳过本项并在证据中说明。

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
| R-1 | Prometheus 不支持自定义头 | L-2 无法直接落地 | 采用 L-2-0 Bearer 兼容（推荐）或代理注入 |
| R-2 | 服务当前绑定 `0.0.0.0` | 监听面证据不达标 | 改为回环/私网网卡；评估跨主机调用影响 |
| R-3 | token 轮换窗口操作失误 | 抓取中断 | 双 token 重叠 + 先加后删 |
| R-4 | 矩阵重生成与手工 MD 不一致 | K07 对账失败 | 以脚本输出为准，MD 同步后再跑 `--check` |
| R-5 | 生产窗口内反例探针误连共享库 | 污染/干扰 | 探针使用独立端口 + 明确 `DATABASE_URL`；单命令起停 |

---

**计划状态**：[Draft]（待 OPS 确认窗口与监控方案、评审组确认 K07 分类口径后执行）
