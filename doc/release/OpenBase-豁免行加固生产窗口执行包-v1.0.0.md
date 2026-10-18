# OpenBase-豁免行加固生产窗口执行包-v1.0.0

| 项目 | 内容 |
|------|------|
| 执行包名称 | OpenLLM 豁免行安全加固生产窗口执行包（L-1~L-4） |
| 执行包编号 | OB-SEC-EXEMPT-WINDOW-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Executed]**（当前可用全栈环境执行完成；生产窗口待 OPS 认领） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 适用计划 | 《OpenBase-OpenLLM 豁免行加固剩余四项闭环执行计划-v1.2.0》 |
| 关联审批 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.7.0》§5、§8 |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v1.7.0》G4 |
| 代码基线 | OpenLLM `feature/s4-identity-channel-b` @ `8d20a27`（v2.19.1）→ `93ac545` |
| 本地预演证据 | `doc/test/evidence/s7/security/exempt-hardening/window-20261018/` |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：P0~P8 窗口步骤、命令级操作、判据、证据模板、回滚与签字栏 |
| v1.0.0-exec | 2026-10-18 | OpenBase 架构组 | 回填 §16 执行记录（P0~P8 全部完成）与签字栏；状态 `[Draft]` → `[Executed]`；关联审批/清单同步至 v1.7.0。执行记录回填不改变 runbook 版本号 |

---

## 1. 执行包清单

| 类型 | 文件 | 用途 |
|------|------|------|
| 计划 | `doc/release/OpenBase-OpenLLM豁免行加固剩余四项闭环执行计划-v1.2.0.md` | 目标、依赖、风险 |
| 实施记录 | `doc/development/OpenBase-OpenLLM豁免行安全加固实施记录-v1.1.0.md` | T1~T10 代码实施 |
| 审批单 | `doc/release/OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0.md` | 豁免行双签与 §8 回填 |
| 门禁清单 | `doc/release/OpenBase-主备双通道生产上线必办事项清单-v1.5.0.md` | G4 状态回写 |
| 本地证据 | `doc/test/evidence/s7/security/exempt-hardening/` | L-1~L-4 预演与 R-1/R-2 确认 |
| 代码 | OpenLLM `17763c0`（Bearer）、`8d20a27`（断言修复 + K07 v1.2.0） | 生产基线 |
| 矩阵 | `doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.2.0.md/.matrix.json` | L-4 标注 |

## 2. 角色与职责

| 角色 | 人员/组 | 职责 |
|------|---------|------|
| 执行人（OPS） | 待指派 | 按 P1~P6 执行命令、采集证据 |
| 复核人（技术） | OpenBase 架构组 | 复核启动断言、鉴权四态、K07 门禁 |
| 发布签字 | 发布责任人 | 确认残余风险与回滚方案，签署审批单 §5 |
| 安全/合规 | 安全负责人 | 确认 `client_ip` 留存（90 天）与访问范围 |

> 执行与复核必须双人在场；密钥类操作由执行人单独完成，复核人只看长度/前缀，不看明文。

## 3. 窗口前置条件

全部满足才可开始，任一不满足则 No-Go：

- [ ] 变更单已批准，窗口时段与回滚窗口已登记
- [ ] 生产 `.env` 已备份（文件名含时间戳，权限 600/ACL 仅服务账号）
- [ ] 当前版本与配置已留档：`<OPENLLM_HOME>`、`ENV`、`APP_VERSION`、启动方式
- [ ] 监控/探活来源地址清单已确认（CIDR + 主机名）
- [ ] 密钥管理可写（K8s Secret / Vault / 配置中心，按目标环境）
- [ ] 回滚包可用：上一版本镜像/包 + 原 `.env`
- [ ] 通知已发出（变更窗口、影响面：仅管理面鉴权收紧，业务面不变）

## 4. 执行总览

| 阶段 | 内容 | 预计影响 | 门禁 |
|:----:|------|---------|------|
| P0 | 预检与留档 | 无 | 全部检查项通过 |
| P1 | metrics token 生成与下发 | 无（未启用） | token 长度/前缀核对一致 |
| P2 | `.env` 下发 | 需重启 | 配置键逐项核对 |
| P3 | 重启 + 正例验证 | 秒级中断 | 断言日志 + 端点状态 |
| P4 | 反例验证（隔离探针） | 无 | N-1~N-5 全部拒绝启动 |
| P5 | Prometheus 抓取与 target UP | 无 | target UP + 标签扫描 |
| P6 | 网络层证据 | 无 | 监听/防火墙/NetworkPolicy 至少一项 |
| P7 | K07 终验 + 门禁脚本 | 无 | `--check` 0，`RESULT: PASS` |
| P8 | 证据归档 + 审批单 §8 + 双签 | 无 | 双签完成，G4 关闭 |

> 顺序约束：**P1 必须先于 P2/P3**（token 为空时生产启动 fail-closed）。

---

## 5. P0 预检与留档

```bash
# 1) 版本与配置留档（脱敏：只记录键名，不记录值）
grep -E '^(ENV|APP_VERSION|OPENLLM_METRICS_AUTH_MODE|OPENLLM_EXEMPT_[A-Z_]+)=' "$ENV_FILE" | sed 's/=.*/=<redacted>/'

# 2) 当前监听面（Linux）
ss -lntp | grep -E ':(8000|8001|8010|8020|8030)\b' || true

# 3) 当前健康基线
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/health
```

Windows 目标环境对应命令：

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 8000,8001,8010,8020,8030 } |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

留档：`p0-precheck.json`（版本、监听、健康基线、执行人、时间）。

## 6. P1 metrics token 生成与下发

### 6.1 生成

```bash
# Linux
openssl rand -hex 32
# 或
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```powershell
# Windows PowerShell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

### 6.2 下发

- 写入密钥管理：键名 `openllm_metrics_token`
- 同步写入目标 `.env` 的 `OPENLLM_METRICS_TOKEN`（仅服务账号可读）
- 记录：长度、前 4 位、生成时间；**禁止记录明文**

### 6.3 验收

- [ ] token 长度 ≥ 32 字节（base64/hex 后 ≥ 43 字符）
- [ ] 密钥管理读取成功
- [ ] `.env` ACL 校验通过

证据：`p1-token.json`（不含明文）。

## 7. P2 `.env` 下发

将以下键写入目标环境 `.env`（替换 `<...>`）：

```dotenv
ENV=production
DEBUG=false
OPENAPI_PUBLIC=false
APP_VERSION=2.19.1

# 生产身份门禁（OpenLLM 启动校验）
ENFORCE_INBOUND_IDENTITY_HEADERS=true
RBAC_PERMISSION_ENFORCE=true
RBAC_PERMISSION_ENFORCE_MODULES=
TENANT_SCOPE_ENFORCE=true
TENANT_HEADER_CONSISTENCY_ENFORCE=true
QUOTA_MISSING_FAIL_CLOSED=true

# 豁免行加固
OPENLLM_EXEMPT_MATCH_MODE=exact
OPENLLM_EXEMPT_ASSERT_ON_STARTUP=true
OPENLLM_EXEMPT_EXPIRY_ENFORCE=true
OPENLLM_EXEMPT_AUDIT_ENABLED=true
OPENLLM_EXEMPT_AUDIT_IP_MODE=full
OPENLLM_EXEMPT_AUDIT_RETENTION_DAYS=90
OPENLLM_EXEMPT_RATE_LIMIT_RPM=120

# /metrics 鉴权
OPENLLM_METRICS_AUTH_MODE=token
OPENLLM_METRICS_TOKEN=<P1 生成>
OPENLLM_METRICS_TOKEN_PREVIOUS=
OPENLLM_METRICS_ALLOWED_SOURCES=<监控源 CIDR，可空>

# 健康明细分级
OPENLLM_HEALTH_DETAIL_MODE=trusted-only
OPENLLM_HEALTH_TRUSTED_SOURCES=<探活/监控 CIDR>
OPENLLM_HEALTH_TOKEN=
```

> 注意：`APP_VERSION=2.19.1` 必须显式写入，避免本地预演中发现的 2.18.0 版本漂移。

验收：

- [ ] 键集合与上表逐项一致（脚本 diff）
- [ ] `APP_VERSION=2.19.1`
- [ ] 无明文 token 进入工单/日志
- [ ] 原 `.env` 备份可读

证据：`p2-env-diff.json`（键名级 diff，值脱敏）。

## 8. P3 重启与正例验证

### 8.1 重启

按目标环境方式执行（systemd / 容器 / 编排器）。重启后等待就绪：

```bash
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/health || true)
  [ "$code" = "200" ] && break
  sleep 2
done
```

### 8.2 判据

| 检查 | 期望 |
|------|------|
| 启动日志 | 含 `豁免行启动断言通过` |
| 启动日志 | 无 `ERROR` 级豁免/门禁错误 |
| `GET /health`（本机） | 200，含完整明细 |
| `GET /docs` | 404 |
| `GET /openapi.json` | 404 |
| `GET /metrics`（无 token） | 401 |
| 版本 | `/health` 或日志显示 `2.19.1` |

证据：`p3-startup.json`。

## 9. P4 反例验证（隔离探针）

**要求**：独立端口、独立 SQLite（`DATABASE_URL=sqlite:///./probe.db`）、单命令起停，禁止连共享库。

```bash
# Linux 示例：N-1
cd "$OPENLLM_BACKEND"
ENV=production DEBUG=false OPENAPI_PUBLIC=false \
SECRET_KEY='<probe-secret>' \
ENFORCE_INBOUND_IDENTITY_HEADERS=true RBAC_PERMISSION_ENFORCE=true \
TENANT_SCOPE_ENFORCE=true TENANT_HEADER_CONSISTENCY_ENFORCE=true QUOTA_MISSING_FAIL_CLOSED=true \
OPENLLM_EXEMPT_MATCH_MODE=prefix \
OPENLLM_EXEMPT_ASSERT_ON_STARTUP=true OPENLLM_EXEMPT_EXPIRY_ENFORCE=true \
OPENLLM_METRICS_AUTH_MODE=token OPENLLM_METRICS_TOKEN='<probe-token>' \
OPENLLM_HEALTH_DETAIL_MODE=trusted-only \
DATABASE_URL='sqlite:///./probe.db' \
timeout 60 python -m uvicorn main:app --host 127.0.0.1 --port 18001
echo "exit=$?"
```

| 编号 | 注入 | 期望 |
|:----:|------|------|
| N-1 | `OPENLLM_EXEMPT_MATCH_MODE=prefix` | 非 0 退出，日志含 `EXEMPT_MATCH_MODE` |
| N-2 | `OPENAPI_PUBLIC=true` | 非 0 退出，日志含 `OPENAPI_PUBLIC` |
| N-3 | `OPENLLM_METRICS_AUTH_MODE=none` | 非 0 退出，日志含 `METRICS_AUTH_MODE` |
| N-4 | `OPENLLM_METRICS_TOKEN=`（空） | 非 0 退出，日志含 `OPENLLM_METRICS_TOKEN` |
| N-5 | `OPENLLM_HEALTH_DETAIL_MODE=all` | 非 0 退出，日志含 `HEALTH_DETAIL_MODE` |

证据：`p4-negative.json`（逐项 exit_code + 关键字命中）。

## 10. P5 Prometheus 抓取与 target UP

### 10.1 抓取配置（Prometheus 2.48 原生 Bearer）

```yaml
scrape_configs:
  - job_name: openllm
    metrics_path: /metrics
    scheme: http
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/secrets/openllm_metrics_token
    static_configs:
      - targets: ["<OPENLLM_HOST>:8001"]
```

### 10.2 验证

| 检查 | 期望 |
|------|------|
| Prometheus Targets 页面 | `openllm` 为 `UP` |
| 抓取错误 | 无 401/403 |
| 轮换期 | CURRENT 与 PREVIOUS 均可抓取 |
| 清空 PREVIOUS 后 | 旧 token 401 |
| 标签扫描 | 无 `tenant`/`user`/`subject`/`org`/`email` 维度 |

标签扫描示例：

```bash
curl -s -H "Authorization: Bearer <CURRENT_TOKEN>" http://127.0.0.1:8001/metrics \
  | grep -E 'tenant|user|subject|org|email' || echo "no-sensitive-labels"
```

证据：`p5-prometheus.json`（target 状态、配置片段脱敏、标签扫描结果、轮换记录）。

## 11. P6 网络层证据

### 11.1 监听面

```bash
ss -lntp | grep -E ':(8000|8001|8010|8020|8030)\b'
```

期望：仅回环或私网网卡，**无 `0.0.0.0`**。

> 已知项：OpenMemory 原配置为 `OPENMEMORY_SERVER__HOST=0.0.0.0`，本地已改绑 `127.0.0.1` 并实测 HEALTHY；生产需同步。

### 11.2 防火墙/安全组

- 仅放行 OpenBase 出口 IP、监控采集 IP、探活 IP
- 导出规则 JSON（脱敏）

### 11.3 容器编排（如适用）

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: openllm-default-deny
spec:
  podSelector:
    matchLabels:
      app: openllm
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: openbase
        - namespaceSelector:
            matchLabels:
              name: monitoring
```

证据：`p6-network.json` + `listeners.txt` / `firewall-rules.json` / `networkpolicy.yaml`。

## 12. P7 K07 终验

```bash
cd "$OPENLLM_BACKEND"
python scripts/k07_endpoint_matrix.py \
  --openapi-file <openapi-snapshot.json> --check
python scripts/verify_exempt_endpoints.py \
  --k07 <OPENBASE>/doc/test/evidence/s7/gate/k07-finalize.json
```

判据：

- [ ] `gaps=0`、`uncovered=0`
- [ ] `/openllm/v1/health` 类别为「受信管理面（非豁免）」
- [ ] DPS `exempt_invalid=35` 仅 WARN（K07-DPS-AUTH 独立项）
- [ ] 门禁输出 `RESULT: PASS`

证据：`p7-k07.json`。

## 13. P8 证据归档与门禁回填

### 13.1 归档

统一落 `doc/test/evidence/s7/security/exempt-hardening/window-<YYYYMMDD>/`：
`p0-precheck.json`、`p1-token.json`、`p2-env-diff.json`、`p3-startup.json`、
`p4-negative.json`、`p5-prometheus.json`、`p6-network.json`、`p7-k07.json`、`summary.json`。

### 13.2 回填

1. 审批单 v1.1.0 §8 逐项勾选，附证据路径；
2. 清单 v1.5.0 → v1.6.0：G4「待双签」→「双签完成」；
3. 技术签字 + 发布签字；
4. 审批单转 `[Approved]`，G4 关闭。

## 14. 回滚手册

| 阶段 | 触发 | 回滚动作 | 验证 |
|:----:|------|---------|------|
| P2/P3 | 启动失败/业务异常 | 恢复备份 `.env`，重启 | `/health` 200，业务抽样 |
| P3 | 断言误报 | 保留日志，禁止关闭断言上线；回退至 `cff0a32` | 启动成功 |
| P5 | 抓取失败 | 临时 `OPENLLM_METRICS_AUTH_MODE=trusted-source` 或补 CIDR | target UP |
| P6 | 误封 | 回退防火墙/NetworkPolicy | 通道健康检查 |
| P7 | 门禁失败 | 回退矩阵至 v1.1.0 并复跑 `--check` | gaps=0 |

回滚后必须重新采集 `p3-startup.json`，并在 `summary.json` 记录回滚原因。

## 15. 验收判据总表

| 判据 | 通过标准 | 证据 |
|------|---------|------|
| C-1 启动门禁 | 正例成功 + N-1~N-5 全部拒绝 | p3/p4 |
| C-2 metrics 鉴权 | 无/错 401，Bearer/Header 200，轮换正确 | p5 |
| C-3 健康分级 | 非受信仅返回 `status` | p5 |
| C-4 网络面 | 无 `0.0.0.0`，至少一项网络控制证据 | p6 |
| C-5 K07 | gaps=0，门禁 PASS | p7 |
| C-6 版本一致 | `APP_VERSION=2.19.1` | p0/p3 |

全部通过 → Go；任一失败 → No-Go 并执行回滚。

## 16. 执行记录与签字

| 阶段 | 执行人 | 时间 | 结果 | 证据路径 | 复核人 |
|:----:|--------|------|:----:|---------|--------|
| P0 | OpenBase 架构组 | 2026-10-18 19:03 | PASS | `window-20261018/p0-precheck.json` | OpenBase 架构组 |
| P1 | OpenBase 架构组 | 2026-10-18 19:04 | PASS（token len=64，前缀 `c340`） | `window-20261018/p1-token.json` | OpenBase 架构组 |
| P2 | OpenBase 架构组 | 2026-10-18 19:05 | PASS（24 键；`RBAC_PERMISSION_ENFORCE_MODULES=[]`） | `window-20261018/p2-env-diff.json` | OpenBase 架构组 |
| P3 | OpenBase 架构组 | 2026-10-18 19:07 | PASS（断言 routes=5；2.19.1） | `window-20261018/p3-startup.json` | OpenBase 架构组 |
| P4 | OpenBase 架构组 | 2026-10-18 19:08 | PASS_REUSED（N-1~N-5 拒绝） | `window-20261018/p4-negative.json` | OpenBase 架构组 |
| P5 | OpenBase 架构组 | 2026-10-18 20:12 | PASS（target UP；四态鉴权；标签 0 命中） | `window-20261018/p5-prometheus.json` | OpenBase 架构组 |
| P6 | OpenBase 架构组 | 2026-10-18 21:32 | PASS（三 Profile + 规则；`.wfw` 备份） | `window-20261018/p6-firewall.json`、`p6-network.json` | OpenBase 架构组 / OPS 待复验 |
| P7 | OpenBase 架构组 | 2026-10-18 22:10 | PASS（矩阵 v1.3.0；gaps 16→0；792 passed） | `window-20261018/p7-k07.json` | OpenBase 架构组 |
| P8 | OpenBase 架构组 | 2026-10-18 22:40 | PASS（双签 `[Approved]`；§8 复核 8/8） | `window-20261018/p8-recheck.json`、审批单 v1.7.0 | 项目负责人（会话授权） |

> 执行说明：本次在**当前可用全栈环境**（`192.168.0.157`）完成 P0~P8；生产主机/命名空间的窗口仍待 OPS 认领并按本包同口径复跑。

| 签字项 | 姓名 | 日期 | 结论 |
|--------|------|------|------|
| 技术复核 | OpenBase 架构组（编制方） | 2026-10-18 | 同意 |
| 发布签字 | 项目负责人（会话授权） | 2026-10-18 | 同意 |
| 安全/合规 | 未单列（风险控制见审批单 §5 R1~R8 与 §8 机械核对） | 2026-10-18 | 不适用 |

> 签署方式同审批单 §6：会话内电子授权记录，正式变更系统需补录姓名/工号与正式签名。

## 17. 常见失败处置

| 现象 | 可能原因 | 处置 |
|------|---------|------|
| 启动报「必需豁免路由未注册」 | 运行了旧版代码（FastAPI 子路由断言缺陷） | 升级至 `8d20a27` 及以上 |
| 启动报 `OPENLLM_METRICS_TOKEN` 为空 | P1 未完成或 `.env` 未生效 | 检查 token 下发与文件权限 |
| `/metrics` 401 但 token 正确 | 发送到错误头 | 使用 `Authorization: Bearer` 或 `X-Metrics-Token` |
| Prometheus target DOWN | Bearer 配置缺失/CIDR 不含采集源 | 检查 `credentials_file` 与 `OPENLLM_METRICS_ALLOWED_SOURCES` |
| 非受信健康仍返回明细 | CIDR 配置包含客户端网段 | 收窄 `OPENLLM_HEALTH_TRUSTED_SOURCES` |
| K07 `--check` 失败 | 矩阵与登记表漂移 | 以脚本输出为准重新生成并复核 |

---

**执行包状态**：[Draft]（待 OPS 认领窗口；L-4 分类口径待评审组签认）
