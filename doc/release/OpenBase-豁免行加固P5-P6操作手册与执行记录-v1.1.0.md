# OpenBase-豁免行加固 P5/P6 操作手册与执行记录-v1.1.0

| 项目 | 内容 |
|------|------|
| 文档名称 | 豁免行加固 P5（Prometheus 接入）/ P6（防火墙启用与规则导出）操作手册与执行记录 |
| 文档编号 | OB-SEC-EXEMPT-P5P6-v1.1.0 |
| 版本 | **v1.1.0** |
| 状态 | **[Final]** |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 所属变更 | G4-T4-2 豁免行加固闭环（L-2 / L-3） |
| 关联执行包 | 《OpenBase-豁免行加固生产窗口执行包-v1.0.0》§10 / §11 |
| 关联权限单 | 《OpenBase-豁免行加固生产窗口访问权限申请单-v1.1.0》（A-6/A-7/A-8/A-9） |
| 执行环境 | 当前可用全栈环境 `192.168.0.157`（生产主机参数待 OPS 提供） |
| 代码基线 | OpenLLM 2.19.1（`8d20a27`） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次发布：P5/P6 逐步操作手册、实际执行命令与结果、证据索引、遗留事项（P6 因非管理员阻塞） |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | P6 经 UAC 提权执行完成：三 Profile 启用 + 默认入站 Block，8001/8020 入站规则落地，全量策略备份与规则导出归档；登记两次失败原因（参数空格拆分、无 BOM 中文解析）与修复方式 |

---

## 1. 结论摘要

| 阶段 | 结论 | 关键判据 | 证据 |
|:----:|------|---------|------|
| **P5** | **PASS** | Prometheus 3.13.4 实例就绪；`openllm` target `UP`；Bearer 抓取无 401/403；标签扫描无敏感维度 | `p5-prometheus.json` |
| **P6** | **PASS** | Domain/Private/Public 全部启用且默认入站 Block；`OpenBase-Security-8001-In` / `8020-In` 落地（TCP，来源 `127.0.0.1`）；`.wfw` 全量备份与规则 JSON 导出完成 | `p6-firewall.json`（含备份 SHA256）、`p6-elevated-run.txt` |

> P6 已在本机完成提权执行。生产环境仍需由 OPS 将 `<OPENBASE_EGRESS_IP>` 与 `<MONITORING_CIDR>` 补入 `RemoteAddress` 白名单后重跑同一脚本。

## 2. 前置条件

| 项 | 要求 | 本次实测 |
|----|------|---------|
| OpenLLM | ≥2.19.1，`/metrics` 已启用 token 鉴权 | 2.19.1，`OPENLLM_METRICS_AUTH_MODE=token` |
| metrics token | 32 字节 hex（64 字符），由密钥管理下发 | 本地窗口生成，长度 64，前缀 `da55`（明文不落盘于证据） |
| Prometheus | 可执行文件 + 可写 TSDB 目录 | 3.13.4 windows-amd64 |
| 网络 | 采集端可访问 `127.0.0.1:8001`（或目标主机 8001） | 回环可达 |
| P6 权限 | 本地管理员 / 目标机 OPS | **已满足**：`jerry` 属 Administrators，经 UAC 提权后 `elevated=True` |

## 3. P5：接入 Prometheus（已执行，PASS）

### 3.1 获取 Prometheus

| 渠道 | 结果 | 处置 |
|------|------|------|
| GitHub Release 直连（2.48.0） | HEAD 200，下载在 5.7MB/99MB 处停滞 | 放弃 |
| BITS 传输 | `Access is denied (0x80070005)`（需管理员） | 放弃 |
| 清华 / 阿里云镜像（2.48 路径） | 404 | 放弃 |
| **清华 TUNA `github-release` 镜像（最新归档）** | **200，100.5MB，45 秒完成** | **采用** |

```powershell
# 下载（也可由 OPS 提供离线包）
& 'C:\Windows\System32\curl.exe' -L --retry 5 --retry-delay 2 -C - `
  --connect-timeout 20 `
  -o 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\prometheus-3.13.4.windows-amd64.tar.gz' `
  'https://mirrors.tuna.tsinghua.edu.cn/github-release/prometheus/prometheus/LatestRelease/prometheus-3.13.4.windows-amd64.tar.gz'

# 解压（本机 PATH 无 tar，必须用绝对路径）
& 'C:\Windows\System32\tar.exe' -xzf `
  'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\prometheus-3.13.4.windows-amd64.tar.gz' `
  -C 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\prometheus'

# 版本核验
& 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\prometheus\prometheus-3.13.4.windows-amd64\prometheus.exe' --version
```

实测版本：`prometheus, version 3.13.4 (branch: HEAD, revision: 007a9e9)`，`windows/amd64`。

> 版本差异：执行包原定 2.48.0，镜像不保留旧归档，本次使用 3.13.4。`authorization: {type: Bearer}` 语法在 2.x/3.x 一致，不影响判据；如生产强制 2.48.0，由 OPS 提供离线包即可，配置无需修改。

### 3.2 生成 / 下发 metrics token

```powershell
$dir = 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\prometheus'
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$token = -join ($bytes | ForEach-Object { $_.ToString('x2') })
[IO.File]::WriteAllText("$dir\metrics_token", $token, [Text.UTF8Encoding]::new($false))
```

要求：
- token 仅写入 `credentials_file`，不进入命令行历史、工单、截图；
- 文件权限最小化（生产建议 0600 等价的 ACL）；
- 轮换期通过 `OPENLLM_METRICS_TOKEN_PREVIOUS` 双活，清空后再观察一个抓取周期。

### 3.3 抓取配置

文件：`doc/tmp/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s

scrape_configs:
  - job_name: openllm
    scheme: http
    metrics_path: /metrics
    authorization:
      type: Bearer
      credentials_file: '<PROMETHEUS_DIR>/metrics_token'
    static_configs:
      - targets: ['127.0.0.1:8001']
        labels:
          env: window-20261018
          system: openllm
```

> 生产替换项：`targets` 改为 `<OPENLLM_HOST>:8001`，`credentials_file` 改为 `/etc/prometheus/secrets/openllm_metrics_token`。

### 3.4 静态校验

```powershell
& '<PROMETHEUS_DIR>\promtool.exe' check config '<PROMETHEUS_DIR>\prometheus.yml'
```

实测：`SUCCESS: ... is valid prometheus config file syntax`。

### 3.5 启动（脱离式，避免会话回收）

```powershell
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile `
  -ExecutionPolicy Bypass -File 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\prometheus\start-prometheus.ps1'
```

脚本要点：
- WMI `Win32_Process.Create` 启动，命令行使用 **powershell.exe 绝对路径**（否则 `ReturnValue=9`）；
- 参数：`--config.file`、`--storage.tsdb.path`、`--web.listen-address=127.0.0.1:9090`、`--web.enable-lifecycle`。

就绪探测：

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:9090/-/ready' -UseBasicParsing
# => 200 "Prometheus Server is Ready."
```

### 3.6 `/metrics` 鉴权四态（正向 + 反向）

```powershell
$t = (Get-Content -Raw '<PROMETHEUS_DIR>\metrics_token').Trim()
# 无 token / Bearer 正确 / X-Metrics-Token 正确 / Bearer 错误
```

| 场景 | 实测 |
|------|------|
| 无 token | **401** |
| `Authorization: Bearer <CURRENT>` | **200**（1567 bytes） |
| `X-Metrics-Token: <CURRENT>` | **200** |
| `Authorization: Bearer deadbeef` | **401** |

### 3.7 target UP 与标签扫描

```powershell
# target 状态
Invoke-RestMethod 'http://127.0.0.1:9090/api/v1/targets?state=active'
# => job=openllm health=up lastError=(空)

# up 指标
Invoke-RestMethod 'http://127.0.0.1:9090/api/v1/query?query=up{job="openllm"}'
# => up=1 instance=127.0.0.1:8001

# 标签全集
Invoke-RestMethod 'http://127.0.0.1:9090/api/v1/labels'
```

实测标签：`__name__, env, generation, implementation, instance, job, major, minor, patchlevel, path, system, trusted, version`

敏感维度扫描（`tenant/tenant_id/user/user_id/subject/subject_id/org/org_id/email/token/authorization`）：**0 命中**；`openllm_*` 序列数 4。

### 3.8 轮换验证

CURRENT / PREVIOUS 双活与清空 PREVIOUS 后旧 token 401 已在 `l2-metrics-auth.json` 完成（四态 + 轮换 + 分级），P5 不重复执行，直接引用。

### 3.9 常见失败处置

| 现象 | 原因 | 处置 |
|------|------|------|
| target `DOWN`，`lastError=401` | token 文件含换行/权限不可读/与 `.env` 不一致 | 重新写出无 BOM 单行文件，比对长度与前缀（不看明文） |
| `promtool` 报 `field http_headers not found` | Prometheus 不支持自定义头 | 使用 `authorization.type=Bearer`（本项目已兼容 Bearer 与 `X-Metrics-Token`） |
| 启动 `ReturnValue=9` | WMI 未找到 `powershell.exe` | 使用绝对路径 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` |
| 服务 `HEALTH_DOWN` 且报 `database "openllm" does not exist` | 子进程 CWD 不在 `backend/`，未加载 `.env` | 启动脚本首行 `Set-Location '<OpenLLM>\backend'` |

## 4. P6：启用防火墙并导出规则（已执行，PASS）

### 4.1 基线取证（非提权可执行）

```powershell
Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction
Get-NetFirewallRule -DisplayName 'OpenBase-Security-*' -ErrorAction SilentlyContinue
```

变更前基线：

| Profile | Enabled | DefaultInbound |
|---------|:-------:|----------------|
| Domain | True | NotConfigured |
| Private | **False** | NotConfigured |
| Public | **False** | NotConfigured |

`8001/8020` 无显式入站规则；两个端口均绑定 `127.0.0.1`（回环，远程不可达）——防火墙规则属于纵深防御与未来改绑前提。

### 4.2 提权执行

脚本：`doc/tmp/p6-firewall-enable.ps1`（纯 ASCII，见 §4.7 编码约束）；包装器：`doc/tmp/run-p6-elevated.ps1`（输出落 `p6-elevated-run.txt`）。

```powershell
# 方式一：由已提权的终端直接执行
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\p6-firewall-enable.ps1' `
  -AllowSources '127.0.0.1','<OPENBASE_EGRESS_IP>','<MONITORING_CIDR>'

# 方式二：非提权会话发起 UAC 提权（本次采用）
Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' `
  -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File "D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\run-p6-elevated.ps1"' `
  -Verb RunAs -PassThru
```

脚本动作（幂等）：

1. `netsh advfirewall export` 全量策略备份 → `firewall-backup-<ts>.wfw`（可用 `netsh advfirewall import` 回滚）；
2. 快照变更前 profile 状态 → `firewall-profiles-before-<ts>.json`；
3. `Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -DefaultInboundAction Block`；
4. 为 8001/8020 创建 `OpenBase-Security-<port>-In`：Inbound / Allow / TCP / 指定 LocalPort / `-RemoteAddress` 白名单 / `Domain,Private`；
5. 导出 `profiles_after` 与规则明细（含 `local_port`、`remote_address`）→ `p6-firewall.json`，`verdict=PASS`。

执行过程与失败修复：

| 轮次 | 现象 | 根因 | 处置 |
|:----:|------|------|------|
| 1 | `Start-Process -Verb RunAs` 进程立即退出，未写日志 | `-ArgumentList` 数组按空格拼接，路径含空格被截断 | 改为单字符串并内嵌引号 |
| 2 | 提权进程启动后报「字符串缺少终止符」 | 脚本为 UTF-8 无 BOM，Windows PowerShell 5 按 GBK 解析中文致语法错乱 | 脚本改为纯 ASCII，保留 `NOTE` 约束 |
| 3 | **成功** | — | `21:32:57` 产出 `.wfw` 与规则，`verdict=PASS` |

### 4.3 执行结果

| 检查 | 结果 |
|------|------|
| 提权身份 | `elevated=True` |
| Profile（Domain / Private / Public） | 全部 `Enabled=1`（启用） |
| 默认入站 / 出站 | 入站 `4=Block`；出站 `2=Allow` |
| `OpenBase-Security-8001-In` | TCP / 8001 / `127.0.0.1` / `Domain, Private` / Allow / Enabled |
| `OpenBase-Security-8020-In` | TCP / 8020 / `127.0.0.1` / `Domain, Private` / Allow / Enabled |
| 全量策略备份 | `doc/tmp/p6-backup/firewall-backup-20261018-213258.wfw`（774,144 bytes，SHA256 `7A8D8D78…954049`） |
| 回环连通性复验 | `8001/health=200`、`9090/-/ready=200` |

### 4.4 规则导出

- 全量可导入备份：`doc/tmp/p6-backup/firewall-backup-20261018-213258.wfw`（含整机策略，**不入库**；SHA256 与大小记录在 `p6-firewall.json`）
- 结构化明细：`p6-firewall.json`（`profiles_before/after` + 规则 TCP 端口、来源、profile、动作）
- 变更前基线：`p6-inbound-rules-export.json`（启用入站规则 771 条，其中 8001/8020 无规则）
- 执行日志：`p6-elevated-run.txt`

### 4.5 回滚

```powershell
# 方式一：脚本内置回滚（删除 OpenBase-Security-* 并按快照恢复 profile 开关）
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File '<...>\p6-firewall-enable.ps1' -Rollback

# 方式二：整策略回滚
& 'C:\Windows\System32\netsh.exe' advfirewall import 'D:\Trae CN\myproject\Dev\OpenBase\doc\tmp\p6-backup\firewall-backup-20261018-213258.wfw'
```

### 4.6 来源白名单填写规则

| 来源 | 用途 | 说明 |
|------|------|------|
| `127.0.0.1` | 本机采集 | 回环通信本身不过滤，规则用于显式登记 |
| OpenBase 出口 IP | B 通道编排调用 | 由 OPS 按生产网络登记，禁止写成 `Any` |
| 监控采集网段 | Prometheus 抓取 | 与 §3.3 的 `targets` 保持同源 |

禁止项：`0.0.0.0/0`、`Any`、跨环境网段；规则 `Profile` 仅 `Domain,Private`，Public 默认拒绝。

### 4.7 编码约束（重要）

Windows PowerShell 5 将**无 BOM** 的 `.ps1` 按系统 ANSI（中文为 GBK）解析。脚本中出现中文注释/字符串时，多字节序列可能吞掉引号导致「字符串缺少终止符」。本项目脚本统一要求：

- `.ps1` 保持 **ASCII-only**；中文说明写入 Markdown 文档；
- 若必须包含中文，保存为 **UTF-8 with BOM**。

## 5. 执行结果明细

| 项 | 结果 | 证据 |
|----|------|------|
| Prometheus 获取与校验 | PASS（3.13.4，`promtool` SUCCESS） | `p5-prometheus.json` |
| Bearer 抓取 | PASS（`up=1`，`lastError` 空） | 同上 |
| 鉴权四态 | PASS（401/200/200/401） | 同上 |
| 标签脱敏扫描 | PASS（0 命中） | 同上 |
| 防火墙基线取证 | PASS（Domain 启用，Private/Public 关闭） | `p6-firewall-baseline.json` |
| 入站规则清单导出 | PASS（771 条，8001/8020 无规则） | `p6-inbound-rules-export.json` |
| Profile 启用与默认入站 Block | PASS（三 Profile 均启用） | `p6-firewall.json` |
| 8001/8020 入站规则 | PASS（TCP，来源 `127.0.0.1`） | 同上 |
| 全量策略备份 | PASS（`.wfw` 774,144 bytes） | 同上 |
| 变更后连通性 | PASS（8001 / 9090 均 200） | 本次执行输出 |

## 6. 证据索引

目录：`doc/test/evidence/s7/security/exempt-hardening/window-20261018/`

| 文件 | 说明 |
|------|------|
| `p5-prometheus.json` | Prometheus 版本、配置、鉴权四态、target、标签扫描 |
| `p6-firewall.json` | P6 结果（`PASS`）：profiles_before/after、规则明细、备份路径 |
| `p6-firewall-baseline.json` | 非提权 profile 基线 |
| `p6-inbound-rules-export.json` | 启用入站规则清单（变更前，771 条） |
| `firewall-backup-20261018-213258.wfw` | 变更前全量策略备份（774,144 bytes）；含整机策略**不提交**，本地保存于 `doc/tmp/p6-backup/`，SHA256 见 `p6-firewall.json` |
| `firewall-profiles-before-20261018-213258.json` | 变更前 profile 快照 |
| `p6-elevated-run.txt` | 提权执行日志 |
| `p6-network.json` | 监听面与网络控制证据（回环绑定） |
| `summary.json` | 窗口总表（P5=PASS，P6=PASS） |

## 7. 遗留事项

| 编号 | 事项 | 责任方 | 关闭判据 |
|:----:|------|--------|---------|
| P6-1 | 生产来源白名单：补入 `<OPENBASE_EGRESS_IP>`、`<MONITORING_CIDR>` 后在目标机重跑脚本 | OPS | 目标机 `p6-firewall.json` 的 `remote_address` 含生产来源 |
| P6-2 | 将 `.wfw` 全量备份归档至受控存储并登记校验和 | OPS | 备份文件与校验和入库 |
| P6-3 | 目标环境（K8s）NetworkPolicy（如适用） | OPS | 策略 YAML 与 `kubectl get netpol` 证据 |
| P7 | K07 矩阵终验在目标环境复跑 | OpenBase 架构组 | `verify_exempt_endpoints.py --check` gaps=0 |
| P8 | G4-T4-2 双签 | 技术/发布签字人 | 审批单 `[Approved]`，清单升 v1.6.0 |

> 当前运行实例（便于复核）：OpenLLM `127.0.0.1:8001`、Prometheus `127.0.0.1:9090`，均为回环绑定；窗口结束按权限单 §4 回收。

## 8. 变更后安全提示

1. 三个 Profile 均已启用且默认入站 `Block`；依赖入站的运维通道（RDP、文件共享、远程调试端口等）如需保留，应按"最小来源"单独放行，禁止整段放开。
2. 当前 8001/8020 规则仅允许 `127.0.0.1`；服务未改绑 `0.0.0.0` 前，远程采集不可达属预期。
3. 回滚窗口：保留 `doc/tmp/p6-backup/firewall-backup-20261018-213258.wfw` 至变更验收签字后，再按保留策略归档。
