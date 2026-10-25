# ============================================================================
# OpenBase 多系统服务编排脚本（service-orchestrator.ps1）
#
# 功能：
#   1) start      ：一键启动全部服务（按依赖拓扑 + 端口预检 + 依赖健康检查）
#   2) startcheck ：一键启动 + 启动后自动全量检查（健康探活 + 深度业务端点检查）
#   3) checkall   ：仅执行全量检查（不启动，对已运行服务做深度体检）
#   4) monitor    ：实时健康检测，发现宕机自动重启（自愈）
#   5) status     ：查询全部服务状态（端口占用 / 健康 / PID）
#   6) stop       ：停止全部服务（按记录的 PID，逆拓扑）
#
# 服务/端口/依赖清单（单一事实源）：doc/design/OpenBase-多系统端口统筹方案-v1.0.0.md
#   8000 OpenBase（固定） | 8001 OpenLLM | 8010 OpenRAG | 8020 OpenMemory
#   8030 DPS | 5173 统一前端 | 5432 PG / 6333 Qdrant / 6380 Redis（公共基础设施）
#
# 用法示例：
#   .\scripts\service-orchestrator.ps1 -Action start
#   .\scripts\service-orchestrator.ps1 -Action startcheck        # 一键启动 + 全量检查
#   .\scripts\service-orchestrator.ps1 -Action checkall          # 仅全量检查
#   .\scripts\service-orchestrator.ps1 -Action start -Only openbase,frontend
#   .\scripts\service-orchestrator.ps1 -Action monitor -Interval 15 -MaxRestarts 3
#   .\scripts\service-orchestrator.ps1 -Action status
#   .\scripts\service-orchestrator.ps1 -Action stop
#   .\scripts\service-orchestrator.ps1 -Action start -ServiceLogRoot D:\tmp\svc-logs   # 覆盖服务日志采集根目录
#   .\scripts\service-orchestrator.ps1 -Action namecheck        # 采集文件命名实测（不改动任何服务）
#   .\scripts\service-orchestrator.ps1 -Action dbcheck           # 仅探测共享库主备（不启动任何服务）
#   .\scripts\service-orchestrator.ps1 -Action dbcheck -Json     # 机器可读输出（供脚本/流水线消费）
#   .\scripts\service-orchestrator.ps1 -Action start -DbMode standby   # 强制走备用库通道
#
# 共享库（PostgreSQL）启动期主备（P0，2026-10-25）：
#   - 每次 start/startcheck/monitor 前必探测主用；`-DbMode auto`（默认）异常自动切备用；
#     `-DbMode primary|standby|off` 可强制/关闭。备用以**子进程环境覆盖**生效，不改写 `.env`；
#     主备均不可达 ⇒ 拒绝启动（退出码 2）。探测/覆盖/耗时写 `doc/test/evidence/ops/`。
#
# 主备周期复检与公共设施探测（P1，2026-10-25）：
#   - monitor 每 ≥60s（可用 `-DbRecheckSec` 缩短）复检一次：主用恢复/失联只**提示**，
#     **不自动回切**运行中服务（避免连接池漂移），回切需重启编排；
#   - Redis/Qdrant/Neo4j/MinIO 同批探测，仅提示不阻断（PG 为唯一硬门禁），
#     端点取自 `.env.shared-infra`（`REDIS_HOST` / `QDRANT_HOST` / `NEO4J_HOST` / `MINIO_HOST`）。
#
# 数据面探针与四设施切换（2026-10-25，用户决策）：
#   - 判定升级为**数据面**（`scripts/infra_probe.py`，stdlib）：PG `select 1`、Redis `PING+DBSIZE`、
#     Qdrant `GET /collections`、Neo4j `RETURN 1`、MinIO `health/ready`；探针不可用时显式回落 TCP；
#   - **主用数据面不通即切备用**：PG 为硬门禁（双不可达 exit 2）；四设施切本机备用并 WARN；
#   - **数据面同步问题暂时挂起**：切备用后数据可能为空或落后，切换必然留痕告警；
#   - 备用端点：`127.0.0.1` + 各规范端口，可用 `OPENBASE_*_STANDBY_PORT` 覆盖。
#
# 每次启动前的数据面校验（2026-10-25）：
#   - **全量启动、单服务启动（-Only）、monitor 自愈重启**统一走 `Assert-ServiceDataPlane`；
#   - 按服务依赖校验（openbase/openllm=pg+redis、openrag=pg+qdrant、openmemory=pg+redis+qdrant+neo4j、
#     dps=pg、frontend 无依赖）；共享库（当前通道）不可用 ⇒ 拒绝该服务启动；其它设施 DOWN ⇒ WARN 不阻断；
#   - `-ProbeTtlSec`（默认 60s）内复用上次探测结果，过期则按服务依赖按需重探。
#
# 环境要求：Windows PowerShell 5+；各服务 Python 依赖已安装（各项目自有环境）
#
# 服务日志采集（C-6，消 G-2）：
#   start/monitor 启动子进程时，把每个服务的 stdout/stderr 重定向落盘到
#     <ServiceLogRoot>\<service>\<service>-YYYYMMDD.log      （stdout，纯文本流）
#     <ServiceLogRoot>\<service>\<service>-YYYYMMDD.err.log  （stderr，纯文本流）
#   默认 ServiceLogRoot = OpenBase\logs（与 openbase 侧 C-1 JSONL 落盘同根，
#   便于 C-7 聚合脚本一次扫描）。同日重复启动会把上一轮内容归档为
#   <service>-YYYYMMDD-HHmmss[.err].log，避免重定向覆盖历史输出。
#   仅改动「子进程输出去向」，不改启停/健康检查/拓扑语义。
#
# 命名对齐（R-384 / BL-147-04）：
#   四仓日志已于 v1.4.7 结构化（JSON Lines），故对声明了 JsonStream 的服务，
#   其**结构化流**采集文件改用 .jsonl 扩展名（其余流保持 .log）：
#     结构化流为 stdout 的仓（openrag）      → <svc>-YYYYMMDD.jsonl
#     结构化流为 stderr 的仓（dps/openllm/openmemory）→ <svc>-YYYYMMDD.err.jsonl
#   归档命名同步对齐为 <svc>-YYYYMMDD-HHmmss[.err].<ext>（时间戳置于 .err **之前**）：
#   旧形态 <svc>-YYYYMMDD.err-HHmmss.log 不匹配适配器白名单（会被日志中心漏读），已修正。
#   命名契约的**唯一判据** = openbase/modules/logs/repository.py::REPO_LOG_NAME_RE；
#   可用 `-Action namecheck` 做命名实测（见该动作说明）。
# ============================================================================

[CmdletBinding()]
param(
    [ValidateSet('start', 'startcheck', 'monitor', 'status', 'checkall', 'stop', 'namecheck', 'dbcheck')]
    [string]$Action = 'start',
    [string[]]$Only = @(),
    [int]$Interval = 15,
    [int]$HealthTimeout = 60,
    [int]$MaxRestarts = 3,
    # 沙箱/受限环境日志目录覆盖（默认 OpenBase\logs\service-orchestrator）
    [string]$LogRoot = '',
    # 服务子进程日志采集根目录覆盖（默认 OpenBase\logs，见 C-6）
    [string]$ServiceLogRoot = '',
    # 共享库（PostgreSQL）启动期主备策略：
    #   auto=探测主用，异常切备用（默认）；primary=强制主用；standby=强制备用；off=不探测（兼容旧行为）
    [ValidateSet('auto', 'primary', 'standby', 'off')]
    [string]$DbMode = 'auto',
    # 单端点探测超时（秒）
    [int]$DbProbeTimeoutSec = 3,
    # 仅 dbcheck：输出机器可读 JSON（供脚本/流水线消费，不打印人类摘要）
    [switch]$Json,
    # monitor 周期复检间隔（秒）；0 = 自动推算（不小于 60s），仅供联调缩短
    [int]$DbRecheckSec = 0,
    # 探测层级：auto=优先数据面（探针不可用时回落 TCP）；data=仅数据面；tcp=仅端口/握手
    [ValidateSet('auto', 'data', 'tcp')]
    [string]$ProbeLevel = 'auto',
    # 单服务启动前数据面校验的复用窗口（秒）：窗口内复用上次探测结果，过期则按需重探
    [int]$ProbeTtlSec = 60
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($LogRoot) {
    $LogDir = $LogRoot
} else {
    $LogDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'logs\service-orchestrator'
}
$PidFile = Join-Path $LogDir 'service-pids.json'
$LogFile = Join-Path $LogDir ("orchestrator-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# C-6：服务子进程 stdout/stderr 采集根目录（默认 OpenBase\logs\<service>\）
if ($ServiceLogRoot) {
    $ServiceLogDir = $ServiceLogRoot
} else {
    $ServiceLogDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'logs'
}
New-Item -ItemType Directory -Force -Path $ServiceLogDir | Out-Null

# ---------------------------------------------------------------------------
# 共享基础设施环境注入（.env.shared-infra：POSTGRES_URL/REDIS_URL → 服务进程继承）
# 使 openbase 等服务启动时连接共享 PG/Redis（demo_app init_database 真实建表/种子）
# ---------------------------------------------------------------------------
$SharedInfraFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env.shared-infra'
if (Test-Path $SharedInfraFile) {
    Get-Content $SharedInfraFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z][A-Z0-9_]*)=(.*)\s*$') {
            $k = $Matches[1]
            $v = $Matches[2].Trim().Trim('"').Trim("'")
            if ($v -and -not [Environment]::GetEnvironmentVariable($k, 'Process')) {
                [Environment]::SetEnvironmentVariable($k, $v, 'Process')
            }
        }
    }
}

# ---------------------------------------------------------------------------
# 共享库（PostgreSQL）启动期探测与主备切换（P0，2026-10-25）
#
# 口径：
#   1) 配置文件（.env / .env.shared-infra）**保持主用地址不变**；备用仅在启动期以
#      **子进程环境变量覆盖**生效，不改写任何配置文件；主用恢复后重启即自动回主用。
#   2) 每次 start/startcheck/monitor 前**必探测**；`-Action dbcheck` 为只探测入口。
#   3) 探测判据：`pg_isready`（首选，含服务端握手）→ 不可用/失败回落 **TCP 连通**。
#   4) 失败策略：主备均不可达 ⇒ **不启动任何服务**（退出码 2），避免「半启动」。
#   5) 日志/证据：只记录主机、端口、判定与耗时；DSN **一律脱敏**（口令→***）。
# ---------------------------------------------------------------------------
$ProjectRoot = Split-Path $PSScriptRoot -Parent

function Test-TcpEndpoint {
    param([string]$TargetHost, [int]$TargetPort, [int]$TimeoutSec = 3)

    $startedAt = Get-Date
    if (-not $TargetHost -or $TargetPort -le 0) {
        return @{ Healthy = $false; Method = 'none'; LatencyMs = 0 }
    }
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $task = $client.ConnectAsync($TargetHost, $TargetPort)
        $connected = $task.Wait([TimeSpan]::FromSeconds($TimeoutSec)) -and $client.Connected
        $client.Close()
        return @{
            Healthy   = [bool]$connected
            Method    = 'tcp'
            LatencyMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
        }
    } catch {
        return @{
            Healthy   = $false
            Method    = 'tcp'
            LatencyMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
        }
    }
}

function Test-PostgresEndpoint {
    param([string]$TargetHost, [int]$TargetPort, [int]$TimeoutSec = 3)

    $startedAt = Get-Date
    $pgIsReady = 'D:\PostgreSQL\17\bin\pg_isready.exe'
    if (Test-Path $pgIsReady) {
        try {
            & $pgIsReady -h $TargetHost -p $TargetPort -t $TimeoutSec *> $null
            $exitCode = $LASTEXITCODE
            return @{
                Healthy   = ($exitCode -eq 0)
                Method    = 'pg_isready'
                LatencyMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
            }
        } catch {
            # 回落 TCP 探测（pg_isready 缺失/异常不作为不可达依据）
        }
    }
    if (-not $TargetHost) {
        return @{ Healthy = $false; Method = 'none'; LatencyMs = 0 }
    }
    return (Test-TcpEndpoint -TargetHost $TargetHost -TargetPort $TargetPort -TimeoutSec $TimeoutSec)
}

function Get-EnvFileValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path $Path)) { return '' }
    # 显式 UTF-8 读取：PS 5.1 的 Get-Content 默认按 ANSI 解码，
    # 遇含中文注释的 .env 会出现行错位/乱码（实测 OpenLLM .env 行号偏移）。
    try {
        $lines = [System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8)
    } catch {
        return ''
    }
    $prefix = $Key + '='
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith($prefix, [System.StringComparison]::Ordinal)) {
            return $trimmed.Substring($prefix.Length).Trim().Trim('"').Trim("'")
        }
    }
    return ''
}

function Set-UrlHostPort {
    param([string]$Url, [string]$TargetHost, [int]$TargetPort)
    if (-not $Url) { return $Url }
    return [regex]::Replace($Url, '@[^/:@]+:\d+', ("@{0}:{1}" -f $TargetHost, $TargetPort))
}

function Hide-DsnSecret {
    param([string]$Value)
    if (-not $Value) { return '' }
    return ($Value -replace '://([^:/@]+):[^@]*@', '://$1:***@')
}

$script:DbResolution = @{
    Ok            = $true
    RequestedMode = $DbMode
    Mode          = 'off'
    Reason        = '未探测（当前动作不探测基础设施）'
    Primary       = @{}
    Standby       = @{}
}
$script:DbOverrides = @{}
$script:DbAppliedEndpoints = @{}
$script:InfraTargets = [ordered]@{}
$script:InfraStatus = [ordered]@{}

# ---------------------------------------------------------------------------
# 数据面探针基础设施（2026-10-25）
#
# 编排侧只做三件事：组装 spec（**不含明文口令**，只给环境变量名）→ 调 stdlib 探针脚本 →
# 读回每个目标的判定。脚本/解释器不可用时显式降级为 TCP（写入 degraded，不静默）。
# ---------------------------------------------------------------------------
$script:ProbeScript = Join-Path $ProjectRoot 'scripts\infra_probe.py'
$script:ProbeResults = @{}
$script:ProbeStamps = @{}
$script:ProbeMode = 'tcp'
$script:ProbeNotes = @()
$script:InfraSwitched = @()
$script:InfraApplied = @{}
$script:InfraStatus = [ordered]@{}

function Get-ProbePython {
    $candidates = @()
    if ($env:OPENBASE_PROBE_PYTHON) { $candidates += $env:OPENBASE_PROBE_PYTHON }
    $candidates += (Join-Path $ProjectRoot '.venv\shim\python.exe')
    $candidates += 'D:\PostgreSQL\17\pgAdmin 4\python\python.exe'
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return ''
}

# 公共设施端点：主用取进程环境（.env.shared-infra 已注入），备用=本机 + 各规范端口
function Get-InfraTargets {
    $standbyHost = if ($env:OPENBASE_INFRA_STANDBY_HOST) { $env:OPENBASE_INFRA_STANDBY_HOST } else { '127.0.0.1' }
    $redisPort = if ($env:OPENBASE_REDIS_STANDBY_PORT) { [int]$env:OPENBASE_REDIS_STANDBY_PORT } else { 6380 }
    $qdrantPort = if ($env:OPENBASE_QDRANT_STANDBY_PORT) { [int]$env:OPENBASE_QDRANT_STANDBY_PORT } else { 6333 }
    $qdrantGrpcPort = if ($env:OPENBASE_QDRANT_STANDBY_GRPC_PORT) { [int]$env:OPENBASE_QDRANT_STANDBY_GRPC_PORT } else { 6334 }
    $neo4jHttpPort = if ($env:NEO4J_HTTP_PORT) { [int]$env:NEO4J_HTTP_PORT } else { 7474 }
    $neo4jBoltPort = if ($env:NEO4J_BOLT_PORT) { [int]$env:NEO4J_BOLT_PORT } else { 7687 }
    $neo4jStandbyHttp = if ($env:OPENBASE_NEO4J_STANDBY_HTTP_PORT) { [int]$env:OPENBASE_NEO4J_STANDBY_HTTP_PORT } else { 7474 }
    $neo4jStandbyBolt = if ($env:OPENBASE_NEO4J_STANDBY_BOLT_PORT) { [int]$env:OPENBASE_NEO4J_STANDBY_BOLT_PORT } else { 7687 }
    $minioPort = if ($env:OPENBASE_MINIO_STANDBY_PORT) { [int]$env:OPENBASE_MINIO_STANDBY_PORT } else { 9000 }

    $candidates = [ordered]@{
        redis  = @{
            Primary  = @{ Host = $env:REDIS_HOST; Port = if ($env:REDIS_PORT) { [int]$env:REDIS_PORT } else { 6380 } }
            Standby  = @{ Host = $standbyHost; Port = $redisPort }
            GrpcPort = 0; HttpPort = 0; StandbyHttpPort = 0
        }
        qdrant = @{
            Primary  = @{ Host = $env:QDRANT_HOST; Port = if ($env:QDRANT_PORT) { [int]$env:QDRANT_PORT } else { 6333 } }
            Standby  = @{ Host = $standbyHost; Port = $qdrantPort }
            GrpcPort = $qdrantGrpcPort; HttpPort = 0; StandbyHttpPort = 0
        }
        neo4j  = @{
            Primary  = @{ Host = $env:NEO4J_HOST; Port = $neo4jBoltPort }
            Standby  = @{ Host = $standbyHost; Port = $neo4jStandbyBolt }
            GrpcPort = 0; HttpPort = $neo4jHttpPort; StandbyHttpPort = $neo4jStandbyHttp
        }
        minio  = @{
            Primary  = @{ Host = $env:MINIO_HOST; Port = if ($env:MINIO_PORT) { [int]$env:MINIO_PORT } else { 9000 } }
            Standby  = @{ Host = $standbyHost; Port = $minioPort }
            GrpcPort = 0; HttpPort = 0; StandbyHttpPort = 0
        }
    }
    $result = [ordered]@{}
    foreach ($name in $candidates.Keys) {
        if ($candidates[$name].Primary.Host) { $result[$name] = $candidates[$name] }
    }
    return $result
}

function New-InfraProbeSpec {
    param(
        [string]$PgPrimaryHost,
        [int]$PgPrimaryPort,
        [string]$PgStandbyHost,
        [int]$PgStandbyPort,
        [hashtable]$Endpoints,
        # 需要纳管进 spec 的设施（默认四类；单服务校验只取该服务依赖的子集）
        [string[]]$Include = @('redis', 'qdrant', 'neo4j', 'minio')
    )

    $targets = [ordered]@{
        pg = [ordered]@{
            primary = @{ host = $PgPrimaryHost; port = $PgPrimaryPort; user_env = 'POSTGRES_USER'; password_env = 'POSTGRES_PASSWORD'; database_env = 'POSTGRES_DB' }
            standby = @{ host = $PgStandbyHost; port = $PgStandbyPort; user_env = 'POSTGRES_USER'; password_env = 'POSTGRES_PASSWORD'; database_env = 'POSTGRES_DB' }
        }
    }
    foreach ($name in $Include) {
        $entry = $Endpoints[$name]
        if (-not $entry) { continue }
        $sides = [ordered]@{}
        foreach ($side in @('Primary', 'Standby')) {
            $endpoint = $entry[$side]
            if (-not $endpoint -or -not $endpoint.Host) { continue }
            $sideKey = $side.ToLower()
            if ($name -eq 'redis') {
                # 缺少口令时不猜：该目标回落 TCP，并在证据里留 degraded 说明
                if (-not $env:REDIS_PASSWORD) {
                    $script:ProbeNotes += ("redis.{0}: 缺少 REDIS_PASSWORD，该目标回落 TCP" -f $sideKey)
                    continue
                }
                $sides[$sideKey] = @{ host = $endpoint.Host; port = $endpoint.Port; password_env = 'REDIS_PASSWORD' }
            } elseif ($name -eq 'qdrant') {
                $item = @{ url = ("http://{0}:{1}" -f $endpoint.Host, $endpoint.Port) }
                if ($env:QDRANT_API_KEY) { $item['api_key_env'] = 'QDRANT_API_KEY' }
                $sides[$sideKey] = $item
            } elseif ($name -eq 'neo4j') {
                if (-not $env:NEO4J_PASSWORD) {
                    $script:ProbeNotes += ("neo4j.{0}: 缺少 NEO4J_PASSWORD，该目标回落 TCP" -f $sideKey)
                    continue
                }
                $httpPort = if ($side -eq 'Primary') { $entry.HttpPort } else { $entry.StandbyHttpPort }
                $sides[$sideKey] = @{ host = $endpoint.Host; http_port = $httpPort; user_env = 'NEO4J_USER'; password_env = 'NEO4J_PASSWORD' }
            } else {
                $sides[$sideKey] = @{ host = $endpoint.Host; port = $endpoint.Port }
            }
        }
        if ($sides.Count -gt 0) { $targets[$name] = $sides }
    }
    return [ordered]@{
        timeout_sec = $DbProbeTimeoutSec
        psql        = 'D:\PostgreSQL\17\bin\psql.exe'
        targets     = $targets
    }
}

function Invoke-DataPlaneProbe {
    param($Spec)

    if ($ProbeLevel -eq 'tcp') { return $null }
    if (-not (Test-Path $script:ProbeScript)) {
        $script:ProbeNotes += '探针脚本缺失，回落 TCP'
        return $null
    }
    $python = Get-ProbePython
    if (-not $python) {
        $script:ProbeNotes += '未找到 Python 解释器，回落 TCP'
        return $null
    }

    $tempRoot = [System.IO.Path]::GetTempPath()
    $token = [guid]::NewGuid().ToString('N')
    $specPath = Join-Path $tempRoot ("openbase-probe-{0}.spec.json" -f $token)
    $outPath = Join-Path $tempRoot ("openbase-probe-{0}.out.json" -f $token)
    try {
        ($Spec | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $specPath -Encoding UTF8
        & $python -S -B $script:ProbeScript --spec $specPath --out $outPath *> $null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outPath)) {
            $script:ProbeNotes += ("探针执行失败（退出码 {0}），回落 TCP" -f $LASTEXITCODE)
            return $null
        }
        $payload = Get-Content -LiteralPath $outPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $results = @{}
        foreach ($property in $payload.targets.PSObject.Properties) {
            $value = $property.Value
            $results[$property.Name] = @{
                Ok        = [bool]$value.ok
                Layer     = [string]$value.layer
                LatencyMs = [int]$value.latency_ms
                Detail    = [string]$value.detail
                Extra     = $value.extra
            }
        }
        # 合并结果（支持分批探测：monitor 只探 PG 时不得冲掉四设施结果）
        $probeAt = Get-Date
        foreach ($key in $results.Keys) {
            $script:ProbeResults[$key] = $results[$key]
            $script:ProbeStamps[$key] = $probeAt
        }
        if ($payload.probe_mode) { $script:ProbeMode = [string]$payload.probe_mode }
        foreach ($note in @($payload.degraded)) {
            if ($note) { $script:ProbeNotes += [string]$note }
        }
        return $payload
    } catch {
        $script:ProbeNotes += ("探针异常：{0}，回落 TCP" -f $_.Exception.Message)
        return $null
    } finally {
        Remove-Item -LiteralPath $specPath, $outPath -ErrorAction SilentlyContinue
    }
}

function Get-TargetHealth {
    param([string]$Key, [string]$TargetHost, [int]$TargetPort, [switch]$Postgres)

    $result = $script:ProbeResults[$Key]
    if ($result) {
        if ($result.Ok) {
            return @{ Healthy = $true; Method = 'data-plane'; LatencyMs = $result.LatencyMs; Detail = $result.Detail }
        }
        if ($result.Layer -eq 'data-plane') {
            # 数据面明确失败：不再回落（避免把「能握手但不可用」判成健康）
            return @{ Healthy = $false; Method = 'data-plane'; LatencyMs = $result.LatencyMs; Detail = $result.Detail }
        }
    }
    if ($ProbeLevel -eq 'data') {
        return @{ Healthy = $false; Method = 'data-plane'; LatencyMs = 0; Detail = '数据面探针不可用（-ProbeLevel data）' }
    }
    if ($Postgres) {
        return (Test-PostgresEndpoint -TargetHost $TargetHost -TargetPort $TargetPort -TimeoutSec $DbProbeTimeoutSec)
    }
    return (Test-TcpEndpoint -TargetHost $TargetHost -TargetPort $TargetPort -TimeoutSec $DbProbeTimeoutSec)
}

# 服务 → 基础设施依赖（单服务启动前按此校验；无依赖的服务不校验）
function Get-ServiceInfraDeps {
    param([hashtable]$Svc)

    $map = @{
        openbase   = @('pg', 'redis')
        dps        = @('pg')
        openllm    = @('pg', 'redis')
        openrag    = @('pg', 'qdrant')
        openmemory = @('pg', 'redis', 'qdrant', 'neo4j')
        frontend   = @()
    }
    $name = [string]$Svc.Name
    if ($map.ContainsKey($name)) { return @($map[$name]) }
    return @()
}

# 按需刷新数据面探测（窗口内复用；monitor 自愈重启前也会走这里）
function Update-DataPlaneProbe {
    param([string[]]$Needed = @('pg'))

    if ($DbMode -eq 'off') { return }
    if (-not $script:DbPrimaryEndpoint -or -not $script:DbStandbyEndpoint) { return }

    $stale = @()
    foreach ($name in $Needed) {
        $keys = if ($name -eq 'pg') {
            @('pg.primary', 'pg.standby')
        } else {
            @(("{0}.primary" -f $name), ("{0}.standby" -f $name))
        }
        foreach ($key in $keys) {
            $stamp = $script:ProbeStamps[$key]
            if (-not $stamp -or ((Get-Date) - $stamp).TotalSeconds -ge $ProbeTtlSec) {
                $stale += $name
                break
            }
        }
    }
    if ($stale.Count -eq 0) { return }

    $include = @($Needed | Where-Object { $_ -ne 'pg' } | Select-Object -Unique)
    $spec = New-InfraProbeSpec -PgPrimaryHost $script:DbPrimaryEndpoint.Host -PgPrimaryPort $script:DbPrimaryEndpoint.Port `
        -PgStandbyHost $script:DbStandbyEndpoint.Host -PgStandbyPort $script:DbStandbyEndpoint.Port `
        -Endpoints $script:InfraTargets -Include $include
    Invoke-DataPlaneProbe -Spec $spec | Out-Null
}

# 单服务启动前的数据面校验：共享库不可用 → 拒绝该服务；其它设施不可用 → WARN 但不阻断
function Assert-ServiceDataPlane {
    param([hashtable]$Svc)

    if ($DbMode -eq 'off') { return $true }
    $deps = Get-ServiceInfraDeps -Svc $Svc
    if ($deps.Count -eq 0) { return $true }

    Update-DataPlaneProbe -Needed $deps

    $parts = @()
    $pgBlocked = $false
    foreach ($name in $deps) {
        if ($name -eq 'pg') {
            $channel = if ($script:DbResolution.Mode -eq 'standby') { 'standby' } else { 'primary' }
            $endpoint = if ($channel -eq 'standby') { $script:DbStandbyEndpoint } else { $script:DbPrimaryEndpoint }
            $health = Get-TargetHealth -Key ("pg.{0}" -f $channel) -TargetHost $endpoint.Host `
                -TargetPort $endpoint.Port -Postgres
            if ($health.Healthy) {
                $parts += ("pg=ok({0},{1})" -f $channel, $health.Method)
            } else {
                $parts += ("pg=DOWN({0})" -f $channel)
                $pgBlocked = $true
            }
            continue
        }
        $item = $script:InfraStatus[$name]
        if (-not $item) { $parts += ("{0}=n/a" -f $name); continue }
        if ($item.Healthy) {
            $state = if ($item.Switched) { 'ok(备用)' } else { 'ok' }
            $parts += ("{0}={1}" -f $name, $state)
        } else {
            $parts += ("{0}=DOWN" -f $name)
            Write-Log 'WARN' ("{0} 启动前数据面校验：{1} 不可达（不阻断该服务启动，功能可能降级）" -f $Svc.Name, $name)
        }
    }

    if ($pgBlocked) {
        Write-Log 'ERROR' ("{0} 启动前数据面校验失败：当前通道共享库不可用，拒绝启动该服务（{1}）" -f `
                $Svc.Name, ($parts -join ' / '))
        return $false
    }
    Write-Log 'INFO' ("{0} 启动前数据面校验：{1}" -f $Svc.Name, ($parts -join ' / '))
    return $true
}

# 主用不可用 → 把该设施指向本机备用（进程环境覆盖，子进程继承；不改写任何 .env）
function Set-InfraStandbyOverrides {
    param([string]$Name, $Entry)

    $standbyHost = $Entry.Standby.Host
    $standbyPort = [int]$Entry.Standby.Port
    $applied = @()
    if ($Name -eq 'redis') {
        $env:REDIS_HOST = $standbyHost
        $env:REDIS_PORT = [string]$standbyPort
        $applied += @('REDIS_HOST', 'REDIS_PORT')
        if ($env:REDIS_URL) {
            $env:REDIS_URL = Set-UrlHostPort -Url $env:REDIS_URL -TargetHost $standbyHost -TargetPort $standbyPort
            $applied += 'REDIS_URL'
        }
        if ($env:OPENBASE_REDIS_URL) {
            $env:OPENBASE_REDIS_URL = Set-UrlHostPort -Url $env:OPENBASE_REDIS_URL -TargetHost $standbyHost -TargetPort $standbyPort
            $applied += 'OPENBASE_REDIS_URL'
        }
        if ($env:OPENMEMORY_CACHE__HOST) {
            $env:OPENMEMORY_CACHE__HOST = $standbyHost
            $env:OPENMEMORY_CACHE__PORT = [string]$standbyPort
            $applied += @('OPENMEMORY_CACHE__HOST', 'OPENMEMORY_CACHE__PORT')
        }
        if ($env:OPENRAG_REDIS_URL -and $env:OPENRAG_REDIS_ENABLED -eq 'true') {
            $env:OPENRAG_REDIS_URL = Set-UrlHostPort -Url $env:OPENRAG_REDIS_URL -TargetHost $standbyHost -TargetPort $standbyPort
            $applied += 'OPENRAG_REDIS_URL'
        }
    } elseif ($Name -eq 'qdrant') {
        $grpcPort = if ($Entry.GrpcPort) { [int]$Entry.GrpcPort } else { 6334 }
        $env:QDRANT_HOST = $standbyHost
        $env:QDRANT_PORT = [string]$standbyPort
        $env:QDRANT_GRPC_PORT = [string]$grpcPort
        $env:QDRANT_URL = ("http://{0}:{1}" -f $standbyHost, $standbyPort)
        $env:OPENRAG_QDRANT_URL = $env:QDRANT_URL
        $env:OPENRAG_QDRANT_GRPC_URL = ("{0}:{1}" -f $standbyHost, $grpcPort)
        $applied += @('QDRANT_HOST', 'QDRANT_PORT', 'QDRANT_GRPC_PORT', 'QDRANT_URL', 'OPENRAG_QDRANT_URL', 'OPENRAG_QDRANT_GRPC_URL')
        if ($env:OPENMEMORY_VECTOR__HOST) {
            $env:OPENMEMORY_VECTOR__HOST = $standbyHost
            $env:OPENMEMORY_VECTOR__PORT = [string]$standbyPort
            $applied += @('OPENMEMORY_VECTOR__HOST', 'OPENMEMORY_VECTOR__PORT')
        }
    } elseif ($Name -eq 'neo4j') {
        $env:NEO4J_HOST = $standbyHost
        $env:NEO4J_BOLT_PORT = [string]$standbyPort
        $env:NEO4J_URI = ("bolt://{0}:{1}" -f $standbyHost, $standbyPort)
        $applied += @('NEO4J_HOST', 'NEO4J_BOLT_PORT', 'NEO4J_URI')
        if ($env:OPENMEMORY_GRAPH__URI) {
            $env:OPENMEMORY_GRAPH__URI = $env:NEO4J_URI
            $applied += 'OPENMEMORY_GRAPH__URI'
        }
    } elseif ($Name -eq 'minio') {
        $env:MINIO_HOST = $standbyHost
        $env:MINIO_PORT = [string]$standbyPort
        $env:MINIO_ENDPOINT = ("http://{0}:{1}" -f $standbyHost, $standbyPort)
        $applied += @('MINIO_HOST', 'MINIO_PORT', 'MINIO_ENDPOINT')
    }
    return @($applied)
}

function Invoke-InfraProbe {
    $status = [ordered]@{}
    foreach ($name in $script:InfraTargets.Keys) {
        $entry = $script:InfraTargets[$name]
        $primary = Get-TargetHealth -Key ("{0}.primary" -f $name) -TargetHost $entry.Primary.Host -TargetPort $entry.Primary.Port
        $standby = Get-TargetHealth -Key ("{0}.standby" -f $name) -TargetHost $entry.Standby.Host -TargetPort $entry.Standby.Port

        $switched = $false
        if (-not $primary.Healthy -and $standby.Healthy) {
            $applied = Set-InfraStandbyOverrides -Name $name -Entry $entry
            $script:InfraSwitched += $name
            $script:InfraApplied[$name] = @($applied)
            $switched = $true
        }

        $status[$name] = @{
            Host           = if ($switched) { $entry.Standby.Host } else { $entry.Primary.Host }
            Port           = if ($switched) { $entry.Standby.Port } else { $entry.Primary.Port }
            Healthy        = if ($switched) { [bool]$standby.Healthy } else { [bool]$primary.Healthy }
            Layer          = if ($switched) { $standby.Method } else { $primary.Method }
            LatencyMs      = if ($switched) { $standby.LatencyMs } else { $primary.LatencyMs }
            Detail         = if ($switched) { '主用不可用，已切备用' } else { $primary.Detail }
            Switched       = $switched
            PrimaryHealthy = [bool]$primary.Healthy
            StandbyHealthy = [bool]$standby.Healthy
        }
    }
    $script:InfraStatus = $status
    return $status
}

function Get-InfraSummary {
    if ($script:InfraStatus.Count -eq 0) { return '' }
    $parts = foreach ($name in $script:InfraStatus.Keys) {
        $item = $script:InfraStatus[$name]
        $state = if ($item.Healthy) { if ($item.Switched) { 'ok(备用)' } else { 'ok' } } else { 'DOWN' }
        ("{0}={1}:{2} {3}[{4}]" -f $name, $item.Host, $item.Port, $state, $item.Layer)
    }
    return ('公共设施探测（{0}）：' -f $script:ProbeMode) + ($parts -join ' / ')
}

function Get-InfraDownNames {
    return @($script:InfraStatus.Keys | Where-Object { -not $script:InfraStatus[$_].Healthy })
}

# 仅在需要门禁/报告的动作上探测：status/stop/checkall/namecheck 不做探测（避免无谓等待）
if ($DbMode -ne 'off' -and $Action -in @('start', 'startcheck', 'monitor', 'dbcheck')) {
    $primaryHost = $env:POSTGRES_HOST
    $primaryPort = if ($env:POSTGRES_PORT) { [int]$env:POSTGRES_PORT } else { 5432 }
    if (-not $primaryHost -and $env:POSTGRES_URL) {
        $match = [regex]::Match($env:POSTGRES_URL, '@([^/:@]+):(\d+)/')
        if ($match.Success) {
            $primaryHost = $match.Groups[1].Value
            $primaryPort = [int]$match.Groups[2].Value
        }
    }
    $standbyHost = if ($env:OPENBASE_PG_STANDBY_HOST) { $env:OPENBASE_PG_STANDBY_HOST } else { '127.0.0.1' }
    # 备用端口默认 5432（PG 规范端口）；不沿用主用端口，避免主用自定义端口时误指向
    $standbyPort = if ($env:OPENBASE_PG_STANDBY_PORT) { [int]$env:OPENBASE_PG_STANDBY_PORT } else { 5432 }

    # 捕获两侧端点：切备用后 $env:POSTGRES_* 已被改写，周期复检必须用初始快照
    $script:DbPrimaryEndpoint = @{ Host = $primaryHost; Port = $primaryPort }
    $script:DbStandbyEndpoint = @{ Host = $standbyHost; Port = $standbyPort }
    $script:InfraTargets = Get-InfraTargets

    # 一次数据面探测覆盖 5 类 × 主备两端；脚本不可用时自动回落 TCP（证据含 degraded）
    $probeSpec = New-InfraProbeSpec -PgPrimaryHost $primaryHost -PgPrimaryPort $primaryPort `
        -PgStandbyHost $standbyHost -PgStandbyPort $standbyPort -Endpoints $script:InfraTargets
    Invoke-DataPlaneProbe -Spec $probeSpec | Out-Null

    $primaryProbe = if ($primaryHost) {
        Get-TargetHealth -Key 'pg.primary' -TargetHost $primaryHost -TargetPort $primaryPort -Postgres
    } else {
        @{ Healthy = $false; Method = 'none'; LatencyMs = 0; Detail = '未配置主机' }
    }
    $standbyProbe = Get-TargetHealth -Key 'pg.standby' -TargetHost $standbyHost -TargetPort $standbyPort -Postgres

    $resolvedMode = $null
    $reason = ''
    switch ($DbMode) {
        'primary' {
            $resolvedMode = if ($primaryProbe.Healthy) { 'primary' } else { '' }
            $reason = '强制主用（-DbMode primary）'
        }
        'standby' {
            $resolvedMode = if ($standbyProbe.Healthy) { 'standby' } else { '' }
            $reason = '强制备用（-DbMode standby）'
        }
        default {
            if ($primaryProbe.Healthy) {
                $resolvedMode = 'primary'
                $reason = '主用可达'
            } elseif ($standbyProbe.Healthy) {
                $resolvedMode = 'standby'
                $reason = '主用不可达，切备用'
            } else {
                $resolvedMode = ''
                $reason = '主备均不可达'
            }
        }
    }

    if (-not $resolvedMode) {
        $script:DbResolution = @{
            Ok            = $false
            RequestedMode = $DbMode
            Mode          = 'unavailable'
            Reason        = $reason
            Primary       = @{ Host = $primaryHost; Port = $primaryPort } + $primaryProbe
            Standby       = @{ Host = $standbyHost; Port = $standbyPort } + $standbyProbe
        }
    } else {
        $script:DbResolution = @{
            Ok            = $true
            RequestedMode = $DbMode
            Mode          = $resolvedMode
            Reason        = $reason
            Primary       = @{ Host = $primaryHost; Port = $primaryPort } + $primaryProbe
            Standby       = @{ Host = $standbyHost; Port = $standbyPort } + $standbyProbe
        }

        if ($resolvedMode -eq 'standby') {
            # 共享键：OpenBase（POSTGRES_URL）与 DPS（定义期读取 $env:POSTGRES_URL）随之切换
            $standbyUrl = if ($env:OPENBASE_PG_STANDBY_URL) {
                $env:OPENBASE_PG_STANDBY_URL
            } else {
                Set-UrlHostPort -Url $env:POSTGRES_URL -TargetHost $standbyHost -TargetPort $standbyPort
            }
            $env:POSTGRES_HOST = $standbyHost
            $env:POSTGRES_PORT = [string]$standbyPort
            if ($standbyUrl) { $env:POSTGRES_URL = $standbyUrl }

            # OpenBase 若在 .env 显式声明 OPENBASE_DB_URL，同等替换（settings 优先级最高）
            $openbaseDbUrl = Get-EnvFileValue -Path (Join-Path $ProjectRoot '.env') -Key 'OPENBASE_DB_URL'
            if ($openbaseDbUrl) {
                $env:OPENBASE_DB_URL = Set-UrlHostPort -Url $openbaseDbUrl -TargetHost $standbyHost -TargetPort $standbyPort
            }

            # 各仓自有 .env 的数据库键（保留各自 scheme/凭据/库名，仅替换主机端口）
            $openllmDbUrl = Get-EnvFileValue -Path 'D:\Trae CN\myproject\Dev\OpenLLM\backend\.env' -Key 'DATABASE_URL'
            $openragDbUrl = Get-EnvFileValue -Path 'D:\Trae CN\myproject\Dev\OpenRAG\.env' -Key 'OPENRAG_DATABASE_URL'
            $script:DbOverrides = @{
                openllm    = @{ DATABASE_URL = (Set-UrlHostPort -Url $openllmDbUrl -TargetHost $standbyHost -TargetPort $standbyPort) }
                openrag    = @{ OPENRAG_DATABASE_URL = (Set-UrlHostPort -Url $openragDbUrl -TargetHost $standbyHost -TargetPort $standbyPort) }
                openmemory = @{ OPENMEMORY_DB__HOST = $standbyHost; OPENMEMORY_DB__PORT = [string]$standbyPort }
            }
            $script:DbAppliedEndpoints = @{
                openbase   = (Hide-DsnSecret $env:POSTGRES_URL)
                dps        = (Hide-DsnSecret $env:POSTGRES_URL)
                openllm    = (Hide-DsnSecret $script:DbOverrides.openllm.DATABASE_URL)
                openrag    = (Hide-DsnSecret $script:DbOverrides.openrag.OPENRAG_DATABASE_URL)
                openmemory = ("{0}:{1}" -f $standbyHost, $standbyPort)
            }
        }
    }

    # -----------------------------------------------------------------------
    # 四设施：主用数据面不通 ⇒ 切备用（用户决策 2026-10-25）
    #
    # 口径：
    #   1) 只对**有消费方**的设施做覆盖（redis/qdrant/neo4j/minio 的共享键 + 各仓自有键）；
    #   2) 数据面同步问题**暂时挂起**：备用数据可能为空或落后，切换必须 WARN 留痕；
    #   3) 不参与启动门禁（PG 是唯一硬门禁），但切换后仍不可用则保留 DOWN 状态供 dbcheck 呈现。
    # -----------------------------------------------------------------------
    if ($Action -in @('start', 'startcheck', 'monitor', 'dbcheck')) {
        Invoke-InfraProbe | Out-Null
    }
}

$script:DbMonitorState = @{ LastMode = $script:DbResolution.Mode; LastNotice = '' }

# ---------------------------------------------------------------------------
# 服务定义表（名称/端口/启动命令/健康检查候选端点/依赖/依赖类型）
# DepType: hard=依赖未健康则不启动；soft=依赖未健康仅告警（OpenBase 上游软依赖）
# ---------------------------------------------------------------------------
$services = @(
    @{
        Name    = 'openllm'
        Port    = 8001
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenLLM\backend'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8001')
        # DPS 目标系统**租户/组织码值互译表**（`CR-148-029`）：DPS 以
        # `dps-org-001`/`dps-tenant-001` 作为**独立联调演示码空间**（`DPS-S5` §Q-DPS-7，
        # 有意与 OpenBase `tenants.code` 空间隔离并做碰撞防护）→ 本仓 → DPS **直连路径**
        # 必须桥接码值；否则 DPS 侧 403「组织不存在」→ 画像段恒降级
        # （`segment_tokens.profile=0`，实测 2026-09-26）。取值与本仓
        # `OPENBASE_DPS_ORG_MAP`/`OPENBASE_DPS_TENANT_MAP` 对齐（同一联调口径）。
        Env     = @{
            PORT = '8001'
            PYTHONDONTWRITEBYTECODE = '1'
            DPS_ORG_CODE_MAP = '{"org-1":"dps-org-001","11111111-1111-1111-1111-111111111111":"dps-org-001"}'
            DPS_TENANT_CODE_MAP = '{"tenant-1":"dps-tenant-001"}'
        }
        Health  = @('http://127.0.0.1:8001/health', 'http://127.0.0.1:8001/api/v1/system/health')
        Depends = @()
        DepType = 'hard'
        # R-384/BL-147-04：JSON Lines 走 stderr（JsonLineFormatter → StreamHandler()）→ .err.jsonl
        JsonStream = 'stderr'
        Desc    = 'OpenLLM 大模型网关'
        Checks  = @(
            @{ Name = '健康检查';      Method = 'GET'; Path = '/health';              Expect = 200 }
            @{ Name = 'API 状态';     Method = 'GET'; Path = '/api/v1/status';       Expect = 200 }
            # 开源模型列表需 JWT 鉴权，未带 token 返回 401 属正常（端点存在 + 门禁生效）
            @{ Name = '开源模型列表(401=门禁)'; Method = 'GET'; Path = '/api/v1/open-models'; Expect = 401 }
        )
    },
    @{
        Name    = 'openrag'
        Port    = 8010
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenRAG'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'openrag.main:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8010')
        # PYTHONDONTWRITEBYTECODE 绕过沙箱禁止写 __pycache__ 的限制（与 DPS 一致）
        # R-384/BL-147-05 修复（DEF-BE-147-002）：① 开启 JSONL（否则请求日志为 structlog
        # 控制台文本，日志中心看不到「应用日志行」）② 声明受信代理来源，使入站
        # X-Request-Id 走「受信透传复用」分支（否则忽略并本地重生成 → 跨系统串联断链）。
        Env     = @{
            OPENRAG_API_PORT = '8010'
            PYTHONDONTWRITEBYTECODE = '1'
            OPENRAG_LOG_JSON = 'true'
            # 注意：该字段为 list[str]，pydantic-settings 会在 field_validator 之前先按 JSON 解码
            # EnvSettingsSource 的值 → **必须传 JSON 数组形态**；传逗号分隔串会导致
            # SettingsError（首轮实测：OpenRAG 启动即崩、rag-proxy 全 502）。
            #
            # 【受信来源补齐：openbase-orchestrator】OpenLLM 以「真实契约」直连 OpenRAG
            # （OPENRAG_BASE_URL=http://127.0.0.1:8010，B 通道编排出站统一来源
            # = openbase-orchestrator，见 OpenLLM app/identity/outbound.py）；
            # 而 OpenRAG 的 M2 角色守卫按**方法**分类（POST=写），检索端点
            # `POST /api/v1/collections/{id}/query/retrieve` 因此被判「匿名写」→
            # 403 PERM_SERVICE_KEY_WRITE_DENIED（实测日志 m2_anonymous_write_denied）。
            # 仅信任 openbase-rag-proxy 时，OpenLLM 直连检索恒失败 → rag 组件每次降级。
            # 故将 OpenLLM 出站来源一并纳入受信白名单（不改写任何来源常量值）。
            OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES = '["openbase-rag-proxy","openbase-orchestrator"]'
        }
        Health  = @('http://127.0.0.1:8010/api/v1/system/health')
        Depends = @()
        DepType = 'hard'
        # R-384/BL-147-04：JSON Lines 走 stdout（structlog → sys.stdout）→ 采集文件 .jsonl
        JsonStream = 'stdout'
        Desc    = 'OpenRAG 知识库/检索'
        Checks  = @(
            @{ Name = '系统健康';   Method = 'GET'; Path = '/api/v1/system/health';  Expect = 200 }
            # M1 认证落地后业务端点需 X-API-Key（同 OpenRAG .env service_api_key）
            @{ Name = '集合列表';   Method = 'GET'; Path = '/api/v1/collections';     Expect = 200; Headers = @{ 'X-API-Key' = 'openbase-rag-gw-key-20260901' } }
            @{ Name = '系统统计';   Method = 'GET'; Path = '/api/v1/system/stats';    Expect = 200; Headers = @{ 'X-API-Key' = 'openbase-rag-gw-key-20260901' } }
        )
    },
    @{
        Name    = 'openmemory'
        Port    = 8020
        # 服务级健康等待窗口（秒）：本服务 /health 需在四后端初始化（Qdrant/PG/Redis/Neo4j）
        # 与 CPU 模型预热（CLIP ViT-B/32 + faster-whisper base/int8）之后才可用。
        # 冷启动实测 48s / 55s / 125s / 137s（2026-09-20 四次样本），全局默认 60s 窗口会误报超时。
        # 原先仅在注释中声明「健康探测需放宽等待」，未落到代码；此处改为服务级强制生效。
        HealthWait = 300
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenMemory'
        Command = 'python'
        # complete 模式（Qdrant + PG + Redis + Neo4j 真实后端，依赖 192.168.0.151 共享基础设施）。
        # 首次启动会预载 faster-whisper/CLIP 模型，耗时较长（约 2~4 分钟），健康探测需放宽等待
        Args    = @('scripts\start_openmemory.py')
        # PYTHONDONTWRITEBYTECODE 绕过沙箱禁止写 __pycache__ 的限制（与 openrag/dps 一致）
        # R-384/BL-147-05 修复（DEF-BE-147-003）：声明受信代理来源。OpenMemory 的
        # IdentityGate 仅在受信来源下才允许复用入站 X-Request-Id；白名单为空时业务路径
        # （/api/v1/monitor）会本地重生成——而 /health 在 whitelist_paths 内直接放行、
        # 由 StructuredLogMiddleware 回退复用合规头，故此前表现为「探活命中、业务路径不命中」。
        # 同样必须以 JSON 数组形态传值（list[str] 字段先经 pydantic-settings JSON 解码）。
        Env     = @{
            PYTHONDONTWRITEBYTECODE = '1'
            OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES = '["openbase-memory-proxy"]'
            # C1-a（2026-10-08，跨仓修复）：**登记 OpenBase 租户码空间为已配置组织**。
            # 背景（实测）：OpenMemory 的 RBAC 组织策略 fail-closed——未登记组织一律
            # 403「组织 'X' 不存在或未配置策略」（PermissionMatrix.check_permission）。
            # 其 .env 仅登记了 `default`，故 X-Tenant-ID=tenant-1 / tenant-2 → 403，
            # 这直接阻塞 OpenBase 侧「统一码空间终态」（memory 目标无法切换到非保留码）。
            # 登记口径：与 .env 既有条目一致（default_role=user —— 该角色含
            # `*/remember` POST 等写权限，无需额外用户绑定即可读写），并按
            # OPENBASE_PROXY_CODE_MAP 的 memory 目标码空间（tenant-1/tenant-2）逐项登记。
            # 显式声明（非静默）：进程环境变量优先于 .env，故此声明即本联调环境的登记事实。
            OPENMEMORY_RBAC__ORG_POLICIES = '{"default":{"enabled":true,"default_role":"user"},"tenant-1":{"enabled":true,"default_role":"user"},"tenant-2":{"enabled":true,"default_role":"user"}}'
        }
        Health  = @('http://127.0.0.1:8020/health')
        Depends = @()
        DepType = 'hard'
        # R-384/BL-147-04：JSON Lines 走 stderr（JsonLineFormatter → StreamHandler()）→ .err.jsonl
        JsonStream = 'stderr'
        Desc    = 'OpenMemory 记忆服务（complete 模式，Qdrant+PG+Redis+Neo4j）'
        Checks  = @(
            @{ Name = '健康检查';     Method = 'GET'; Path = '/health';             Expect = 200 }
            @{ Name = '就绪探针';     Method = 'GET'; Path = '/health/readiness';   Expect = 200 }
            @{ Name = '存活探针';     Method = 'GET'; Path = '/health/liveness';    Expect = 200 }
            @{ Name = 'V1 健康别名';  Method = 'GET'; Path = '/api/v1/health';      Expect = 200 }
        )
    },
    @{
        Name    = 'oidc-idp'
        Port    = 8090
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenBase'
        Command = 'python'
        # 本地标准 OIDC IdP（scripts/oidc-idp/idp_server.py，开发/联调用，OB-AUTH-OIDC）
        Args    = @('scripts\oidc-idp\idp_server.py')
        Env     = @{ PYTHONDONTWRITEBYTECODE = '1' }
        Health  = @('http://127.0.0.1:8090/health', 'http://127.0.0.1:8090/.well-known/openid-configuration')
        Depends = @()
        DepType = 'hard'
        Desc    = '本地 OIDC IdP（标准授权码流程，演示用户池）'
        Checks  = @(
            @{ Name = '健康检查'; Method = 'GET'; Path = '/health'; Expect = 200 }
            @{ Name = 'Discovery'; Method = 'GET'; Path = '/.well-known/openid-configuration'; Expect = 200 }
            @{ Name = 'JWKS';      Method = 'GET'; Path = '/jwks';  Expect = 200 }
        )
    },
    @{
        Name    = 'dps'
        Port    = 8030
        Cwd     = 'D:\Trae CN\myproject\Dev\DPS'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'rest_api.app:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8030')
        # 强制共享 PostgreSQL（不使用 SQLite）：DATABASE_URL ← 共享 .env.shared-infra 的
        # POSTGRES_URL（上方第 49-60 行已注入进程环境，子进程继承）；
        # SQLITE_FALLBACK=false 禁止任何 SQLite 回退；DPS_DEMO_SEED 不再启用
        # （seed_demo.py 为 SQLite 专用；PG 幂等种子见 DPS scripts/seed-shared-infra.py）。
        Env     = @{
            API_PORT = '8030'
            DATABASE_URL = $env:POSTGRES_URL
            SQLITE_FALLBACK = 'false'
            PYTHONDONTWRITEBYTECODE = '1'
            # R-384/BL-147-05 修复（DEF-BE-147-001）：声明受信代理来源，使入站
            # X-Request-Id 走「受信透传复用」分支（白名单为空时 DPS 会忽略网关 id
            # 并本地重生成 → 跨系统串联断链）。取值示例见 DPS 仓 src/config.py:194。
            TRUSTED_PROXY_SOURCES = 'openbase-dps-proxy,openbase-orchestrator'
        }
        Health  = @('http://127.0.0.1:8030/health/liveness')
        Depends = @()
        DepType = 'hard'
        # R-384/BL-147-04：JSON Lines 走 stderr（JsonLineFormatter → StreamHandler()）→ .err.jsonl
        JsonStream = 'stderr'
        Desc    = 'DPS 数据画像系统'
        Checks  = @(
            @{ Name = '存活探针';   Method = 'GET'; Path = '/health/liveness'; Expect = 200 }
            # DPS /openapi.json 受权限中间件保护，无身份返回 401 属正常（门禁生效）
            @{ Name = 'API 文档(401=门禁)'; Method = 'GET'; Path = '/openapi.json'; Expect = 401 }
        )
    },
    @{
        Name    = 'openbase'
        Port    = 8000
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenBase'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'openbase.demo_app:app', '--host', '127.0.0.1', '--port', '8000')
        # P0-3（评审 Q5）：OpenBase dps_upstream_base 默认已对齐 DPS 源码 8000；本编排将 DPS
        # 置于 8030（同机避免与 OpenBase 8000 冲突），故显式注入环境变量覆盖默认值。
        # P1-1（2026-09-06）：OpenBase 侧 org-1/tenant-1（默认兜底）与 tenant_code claim
        # （tenant-1）→ DPS 预建 code（dps-org-001/dps-tenant-001，共享 PG 种子）映射，
        # 修复 dps-proxy 画像族 403「组织不存在」（DPS 中间件双形态解析并规范化 UUID）。
        Env     = @{
            OPENBASE_DPS_UPSTREAM_BASE = 'http://127.0.0.1:8030'
            OPENBASE_DPS_ORG_MAP = '{"org-1":"dps-org-001","tenant-1":"dps-org-001"}'
            OPENBASE_DPS_TENANT_MAP = '{"org-1":"dps-tenant-001","tenant-1":"dps-tenant-001"}'
            # R-387 收口 + A 批 A1/A2：恢复 rag-proxy 身份头注入，并以**统一码空间登记入口**
            # 显式声明各目标出站租户码（非静默；settings 启动即校验，非法即拒绝启动）。
            # 根因（出站头矩阵实测，doc/test/evidence/manual/）：
            #   ① 仅服务密钥、不注入身份头（v1.4.7 方案 B）→ OpenRAG M2 视作匿名服务密钥写
            #      → 全部写类端点 403 PERM_SERVICE_KEY_WRITE_DENIED（读通写断）；
            #   ② 受信入站但**省略** X-Tenant-ID（主体无租户声明的真实形态）→ 上游按保留码
            #      default 处理 → 读、写皆 400；
            #   ③ 受信入站 + 非保留码（tenant-1）→ 读 200 且写 200（唯一自洽形态）。
            # 故不再声明 OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'（该开关保留为应急回滚杠杆）。
            # 各目标码空间（保留码/兜底码）：**统一码空间终态**（C1-a 闭环后，2026-10-08）——
            # rag 与 memory 兜底码同为非保留码 `tenant-1`，身份空间不再出现保留码 `default`。
            # memory 兜底须为上游已登记组织码：已由本服务块的
            # OPENMEMORY_RBAC__ORG_POLICIES 登记 tenant-1/tenant-2（见上方 C1-a 注释）。
            OPENBASE_PROXY_CODE_MAP = '{"schema_version":1,"source_of_truth":"openbase.tenants.code","targets":{"rag":{"reserved_codes":["default","openrag-local"],"default_tenant_code":"tenant-1"},"memory":{"reserved_codes":[],"default_tenant_code":"tenant-1"}}}'
        }
        Health  = @('http://127.0.0.1:8000/openapi.json')
        Depends = @('openllm', 'openrag', 'openmemory', 'dps')
        DepType = 'soft'
        Desc    = 'OpenBase 统一底座（JWT 门禁 + 四 proxy）'
        Checks  = @(
            @{ Name = 'OpenAPI 文档';  Method = 'GET'; Path = '/openapi.json';    Expect = 200 }
            # 真实健康端点：/health 无需鉴权，返回 {status: ok}。
            # 修正（走查 v1.0.0 次要项）：原用 /api/v1/health 期望 401——该路径**非真实端点**，
            # 其 401 仅来自鉴权门禁对未知 /api 路径的拦截（弱断言/假阳性）→ 改用真实端点。
            @{ Name = '健康检查';      Method = 'GET'; Path = '/health';          Expect = 200 }
            @{ Name = '登录端点';      Method = 'GET'; Path = '/api/v1/auth/login'; Expect = 405 }
        )
    },
    @{
        Name    = 'frontend'
        Port    = 5173
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenBase\openbase-ui'
        Command = 'npm.cmd'   # Windows 下 npm 为 npm.cmd（Start-Process 需带扩展名）
        Args    = @('run', 'dev')
        # 走查 v1.0.0 提示项修复：以 WMI 脱离当前会话启动，规避沙箱 Job Object
        # kill-on-close 导致子进程（vite）随编排器会话结束被回收。
        Detach  = $true
        Env     = @{}
        # vite dev 默认仅绑定 IPv6 回环 ::1，须用 localhost 访问（127.0.0.1 不通）
        Health  = @('http://localhost:5173/')
        CheckBase = 'http://localhost:5173'
        Depends = @('openbase')
        DepType = 'hard'
        Desc    = '统一前端（vite dev，proxy → 8000）'
        Checks  = @(
            @{ Name = '首页 HTML'; Method = 'GET'; Path = '/';          Expect = 200 }
            @{ Name = '入口脚本';  Method = 'GET'; Path = '/index.html'; Expect = 200 }
        )
    }
)

# 备用库通道：把覆盖键合并进各服务 Env（启动时随子进程环境生效；不改写 .env）
if ($script:DbOverrides.Count -gt 0) {
    foreach ($svc in $services) {
        if (-not $script:DbOverrides.ContainsKey($svc.Name)) { continue }
        if (-not $svc.Env) { $svc.Env = @{} }
        foreach ($key in $script:DbOverrides[$svc.Name].Keys) {
            $svc.Env[$key] = $script:DbOverrides[$svc.Name][$key]
        }
    }
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

function Write-Log {
    param([string]$Level, [string]$Message)
    $line = "{0} [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Get-ServiceDef {
    param([string]$Name)
    return $services | Where-Object { $_.Name -eq $Name } | Select-Object -First 1
}

function Get-ServiceLogDir {
    param([string]$Name)
    return (Join-Path $ServiceLogDir $Name)
}

# C-6：准备服务 stdout/stderr 采集文件（R-384/BL-147-04 命名对齐）。
# 命名契约（唯一判据 = openbase/modules/logs/repository.py::REPO_LOG_NAME_RE）：
#   结构化流（JsonStream 声明所在流）→ <svc>-YYYYMMDD.jsonl / <svc>-YYYYMMDD.err.jsonl
#   非结构化流                        → <svc>-YYYYMMDD.log   / <svc>-YYYYMMDD.err.log
# 同日重复启动时先把上一轮非空内容归档为 <svc>-YYYYMMDD-HHmmss[.err].<ext>
# （时间戳须在 .err **之前**，否则适配器按目录扫描会漏读），因为 Start-Process 的
# 重定向是「覆盖写」，不归档会丢历史输出。
function Get-ServiceLogFileName {
    param([hashtable]$Svc, [string]$Day)
    # 结构化流扩展名：声明 JsonStream 的服务，其结构化流采集文件用 .jsonl
    $outExt = if ($Svc.JsonStream -eq 'stdout') { '.jsonl' } else { '.log' }
    $errExt = if ($Svc.JsonStream -eq 'stderr') { '.jsonl' } else { '.log' }
    return @{
        Out = ("{0}-{1}{2}" -f $Svc.Name, $Day, $outExt)
        Err = ("{0}-{1}.err{2}" -f $Svc.Name, $Day, $errExt)
    }
}

function Get-ServiceLogArchiveName {
    param([string]$LeafName, [string]$Stamp)
    # 归档名 = <svc>-<date>-<HHmmss>[.err]<ext>：保留扩展名，时间戳置于 .err 之前
    $leaf = [System.IO.Path]::GetFileName($LeafName)
    $extension = [System.IO.Path]::GetExtension($leaf)                    # .jsonl / .log
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($leaf)          # dps-20260919[.err]
    $isErrStream = $stem.EndsWith('.err')
    $baseName = if ($isErrStream) { $stem.Substring(0, $stem.Length - 4) } else { $stem }
    $errTag = if ($isErrStream) { '.err' } else { '' }
    return ("{0}-{1}{2}{3}" -f $baseName, $Stamp, $errTag, $extension)
}

function Initialize-ServiceLogTarget {
    param([hashtable]$Svc)
    $svcDir = Get-ServiceLogDir $Svc.Name
    New-Item -ItemType Directory -Force -Path $svcDir | Out-Null
    $day = Get-Date -Format 'yyyyMMdd'
    $names = Get-ServiceLogFileName -Svc $Svc -Day $day
    $outPath = Join-Path $svcDir $names.Out
    $errPath = Join-Path $svcDir $names.Err
    $archiveStamp = Get-Date -Format 'HHmmss'
    foreach ($path in @($outPath, $errPath)) {
        if (-not (Test-Path $path)) { continue }
        if ((Get-Item $path).Length -le 0) { continue }
        $archivePath = Join-Path (Split-Path $path -Parent) (Get-ServiceLogArchiveName -LeafName $path -Stamp $archiveStamp)
        Move-Item -Path $path -Destination $archivePath -Force
        Write-Log 'INFO' ("{0} 上一轮日志已归档：{1}" -f $Svc.Name, $archivePath)
    }
    return @{ Out = $outPath; Err = $errPath }
}

function Test-Health {
    param([hashtable]$Svc, [int]$TimeoutSec = 5)
    foreach ($uri in $Svc.Health) {
        try {
            $resp = Invoke-WebRequest -Uri $uri -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) { return $true }
        }
        catch { }
    }
    return $false
}

function Get-PortPid {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { return ($conn | Select-Object -First 1).OwningProcess }
    return $null
}

function Get-LastPid {
    param([string]$Name)
    if (Test-Path $PidFile) {
        try {
            $data = Get-Content $PidFile -Raw | ConvertFrom-Json
            if ($null -ne $data.$Name) { return [int]$data.$Name }
        }
        catch { }
    }
    return $null
}

function Save-Pid {
    param([string]$Name, [int]$ProcessId)
    $data = @{}
    if (Test-Path $PidFile) {
        try {
            $json = Get-Content $PidFile -Raw | ConvertFrom-Json
            foreach ($prop in $json.PSObject.Properties) { $data[$prop.Name] = [int]$prop.Value }
        }
        catch { }
    }
    $data[$Name] = $ProcessId
    ($data | ConvertTo-Json) | Set-Content $PidFile -Encoding UTF8
}

function Remove-Pid {
    param([string]$Name)
    if (Test-Path $PidFile) {
        try {
            $data = @{}
            $json = Get-Content $PidFile -Raw | ConvertFrom-Json
            foreach ($prop in $json.PSObject.Properties) { $data[$prop.Name] = [int]$prop.Value }
            $data.Remove($Name)
            ($data | ConvertTo-Json) | Set-Content $PidFile -Encoding UTF8
        }
        catch { }
    }
}

function Start-DetachedProcess {
    # 走查 v1.0.0 提示项修复：以 WMI Win32_Process.Create + -EncodedCommand 脱离当前会话启动，
    # 规避沙箱 Job Object kill-on-close（子进程随编排器会话结束被回收）。返回新进程 PID。
    param([hashtable]$Svc, [hashtable]$LogTarget)
    $lines = @("Set-Location '$($Svc.Cwd)'")
    foreach ($key in $Svc.Env.Keys) {
        $val = ([string]$Svc.Env[$key]) -replace "'", "''"
        $lines += "`$env:$key = '$val'"
    }
    $quotedArgs = ($Svc.Args | ForEach-Object { "'" + ($_ -replace "'", "''") + "'" }) -join ' '
    $lines += "& '$($Svc.Command)' $quotedArgs 1>'$($LogTarget.Out)' 2>'$($LogTarget.Err)'"
    $inner = $lines -join "`n"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))
    $psExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $startCmd = "`"$psExe`" -NoProfile -NonInteractive -EncodedCommand $encoded"
    $result = ([wmiclass]"\\.\root\cimv2:Win32_Process").Create($startCmd)
    if ($result.ReturnValue -ne 0) {
        throw ("Win32_Process.Create 失败，ReturnValue={0}" -f $result.ReturnValue)
    }
    return [int]$result.ProcessId
}

function Start-Service {
    param([hashtable]$Svc, [switch]$FromMonitor)
    # 1) 端口预检：端口被其他进程占用（非本服务记录 PID）→ 拒绝启动
    $portPid = Get-PortPid $Svc.Port
    $lastPid = Get-LastPid $Svc.Name
    if ($portPid -and $portPid -ne $lastPid) {
        Write-Log 'WARN' ("{0} 端口 {1} 被进程 {2} 占用，跳过启动（视为已运行）" -f $Svc.Name, $Svc.Port, $portPid)
        return $false
    }
    if ($portPid -and $portPid -eq $lastPid) {
        Write-Log 'INFO' ("{0} 已在运行（PID {1}，端口 {2}）" -f $Svc.Name, $portPid, $Svc.Port)
        return $true
    }
    # 2) 数据库/基础设施数据面校验（每次真正启动服务前都执行；start 全量/单服务与 monitor 自愈一致）
    if (-not (Assert-ServiceDataPlane -Svc $Svc)) {
        return $false
    }
    # 3) 依赖健康检查
    foreach ($depName in $Svc.Depends) {
        $dep = Get-ServiceDef $depName
        if (-not $dep) { continue }
        $depHealthy = Test-Health $dep
        if (-not $depHealthy) {
            if ($Svc.DepType -eq 'hard') {
                Write-Log 'ERROR' ("{0} 依赖 {1} 未健康，跳过启动（硬依赖）" -f $Svc.Name, $depName)
                return $false
            }
            Write-Log 'WARN' ("{0} 依赖 {1} 未健康（软依赖，继续尝试启动）" -f $Svc.Name, $depName)
        }
    }
    # 4) 设置环境变量（Start-Process 继承启动瞬间环境，串行启动无污染）
    $oldEnv = @{}
    foreach ($key in $Svc.Env.Keys) {
        $oldEnv[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, [string]$Svc.Env[$key], 'Process')
    }
    try {
        # C-6：把子进程 stdout/stderr 落盘采集（消 G-2），日志路径写编排器日志便于检索
        $logTarget = Initialize-ServiceLogTarget $Svc
        Write-Log 'INFO' ("启动 {0}（{1}）：{2} {3}（cwd={4}）" -f $Svc.Name, $Svc.Desc, $Svc.Command, ($Svc.Args -join ' '), $Svc.Cwd)
        $proc = $null
        $launchedPid = 0
        if ($Svc.Detach) {
            # 走查 v1.0.0 提示项修复：脱离当前会话启动（规避 Job Object kill-on-close）
            $launchedPid = Start-DetachedProcess -Svc $Svc -LogTarget $logTarget
            Save-Pid $Svc.Name $launchedPid
            Write-Log 'INFO' ("{0} 已脱离会话启动（WMI，PID {1}），日志 stdout={2}，stderr={3}" -f $Svc.Name, $launchedPid, $logTarget.Out, $logTarget.Err)
        } else {
            $proc = Start-Process -FilePath $Svc.Command -ArgumentList $Svc.Args -WorkingDirectory $Svc.Cwd -WindowStyle Hidden -RedirectStandardOutput $logTarget.Out -RedirectStandardError $logTarget.Err -PassThru
            $launchedPid = $proc.Id
            Save-Pid $Svc.Name $launchedPid
            Write-Log 'INFO' ("{0} 进程已创建（PID {1}），日志 stdout={2}，stderr={3}" -f $Svc.Name, $launchedPid, $logTarget.Out, $logTarget.Err)
        }
        # 等待窗口：服务级 HealthWait 优先（如 openmemory 冷启动需数分钟），否则用全局 -HealthTimeout。
        # 修复背景：全局 60s 对冷启动慢的服务必然误报超时（且下游「软依赖未健康」告警会提前触发）。
        $wait = if ($Svc.HealthWait) { [int]$Svc.HealthWait } else { $HealthTimeout }
        $waitSource = if ($Svc.HealthWait) { 'service HealthWait' } else { 'global -HealthTimeout' }
        Write-Log 'INFO' ("{0} 等待健康检查（超时 {1}s，来源：{2}）..." -f $Svc.Name, $wait, $waitSource)
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $deadline = (Get-Date).AddSeconds($wait)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 2
            if (Test-Health $Svc) {
                Write-Log 'INFO' ("{0} 健康检查通过 ✅（PID {1}，端口 {2}，冷启动耗时 {3}s）" -f $Svc.Name, $launchedPid, $Svc.Port, [int]$stopwatch.Elapsed.TotalSeconds)
                return $true
            }
            if ($proc -and $proc.HasExited) {
                Write-Log 'ERROR' ("{0} 进程提前退出（exit={1}），请查看 stderr 日志：{2}" -f $Svc.Name, $proc.ExitCode, $logTarget.Err)
                Remove-Pid $Svc.Name
                return $false
            }
        }
        Write-Log 'WARN' ("{0} 健康检查超时（进程仍在，PID {1}，已等待 {2}s/{3}s）" -f $Svc.Name, $launchedPid, [int]$stopwatch.Elapsed.TotalSeconds, $wait)
        return $false
    }
    finally {
        foreach ($key in $oldEnv.Keys) {
            [Environment]::SetEnvironmentVariable($key, $oldEnv[$key], 'Process')
        }
    }
}

function Stop-Service {
    param([hashtable]$Svc)
    $pidToKill = Get-LastPid $Svc.Name
    $portPid = Get-PortPid $Svc.Port
    $target = $null
    if ($pidToKill -and (Get-Process -Id $pidToKill -ErrorAction SilentlyContinue)) { $target = $pidToKill }
    elseif ($portPid) { $target = $portPid }
    if ($target) {
        Stop-Process -Id $target -Force -ErrorAction SilentlyContinue
        Write-Log 'INFO' ("{0} 已停止（PID {1}，端口 {2}）" -f $Svc.Name, $target, $Svc.Port)
        Remove-Pid $Svc.Name
    }
    else {
        Write-Log 'INFO' ("{0} 未运行，无需停止" -f $Svc.Name)
    }
}

function Get-AllStatus {
    foreach ($svc in $services) {
        $portPid = Get-PortPid $svc.Port
        $healthy = Test-Health $svc
        $lastPid = Get-LastPid $svc.Name
        $status = '未启动'
        if ($portPid) { $status = '运行中' }
        if ($healthy) { $status = '健康 ✅' }
        elseif ($portPid) { $status = '运行中（不健康 ⚠️）' }
        $pidInfo = if ($portPid) { "PID=$portPid" } else { 'PID=-' }
        "{0,-11} {1,-6} {2,-30} {3} {4}" -f $svc.Name, $svc.Port, $svc.Desc, $status, $pidInfo
    }
}

# ---------------------------------------------------------------------------
# 拓扑排序（依赖分层，用于 start/stop 顺序）
# ---------------------------------------------------------------------------

$script:topoOrder = @()

function Get-TopoOrder {
    $script:topoOrder = @()
    $visited = @{}
    function Visit([string]$Name) {
        if ($visited[$Name]) { return }
        $visited[$Name] = $true
        $svc = Get-ServiceDef $Name
        foreach ($depName in $svc.Depends) { Visit $depName }
        $script:topoOrder += $Name
    }
    foreach ($svc in $services) { Visit $svc.Name }
    return $script:topoOrder
}

# ---------------------------------------------------------------------------
# Action 分发
# ---------------------------------------------------------------------------

function Get-EvidenceDir {
    if ($env:OPENBASE_EVIDENCE_ROOT) { return $env:OPENBASE_EVIDENCE_ROOT }
    return (Join-Path $ProjectRoot 'doc\test\evidence\ops')
}

function New-EvidencePath {
    param([string]$ActionName)
    $evidenceDir = Get-EvidenceDir
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
    return (Join-Path $evidenceDir ("db-startup-probe-{0}-{1}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'), $ActionName))
}

function New-DbEvidencePayload {
    param([string]$ActionName)
    return [ordered]@{
        schema_version    = 3
        tool              = 'service-orchestrator.ps1'
        action            = $ActionName
        generated_at      = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
        requested_mode    = $script:DbResolution.RequestedMode
        resolved_mode     = $script:DbResolution.Mode
        ok                = $script:DbResolution.Ok
        reason            = $script:DbResolution.Reason
        primary           = $script:DbResolution.Primary
        standby           = $script:DbResolution.Standby
        # 数据面探针原始结果（每目标 ok/layer/detail）+ 已切换设施 + 降级说明
        data_plane        = [ordered]@{
            probe_mode = $script:ProbeMode
            switched   = @($script:InfraSwitched)
            applied    = $script:InfraApplied
            degraded   = @($script:ProbeNotes)
            targets    = $script:ProbeResults
        }
        # 公共设施判定结果（PG 为唯一硬门禁；四设施仅告警/切换）
        dependencies      = $script:InfraStatus
        override_services = @($script:DbOverrides.Keys | Sort-Object)
        applied_endpoints = $script:DbAppliedEndpoints
        note              = '数据面探针（PG select 1 / Redis PING+DBSIZE / Qdrant collections / Neo4j RETURN 1 / MinIO ready）；DSN 脱敏；不改写 .env；切备用的数据同步问题暂时挂起'
    }
}

function Write-DbEvidence {
    param([string]$ActionName)
    $path = New-EvidencePath -ActionName $ActionName
    $payload = New-DbEvidencePayload -ActionName $ActionName
    ($payload | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $path -Encoding UTF8
    return $path
}

function Write-DbRecheckEvidence {
    param([string]$CurrentMode, [string]$DesiredMode, $PrimaryProbe, $StandbyProbe, [string]$Notice)

    $evidenceDir = Get-EvidenceDir
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
    $path = Join-Path $evidenceDir ("db-monitor-recheck-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $payload = [ordered]@{
        schema_version = 1
        tool           = 'service-orchestrator.ps1'
        action         = 'monitor-recheck'
        generated_at   = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
        current_mode   = $CurrentMode
        desired_mode   = $DesiredMode
        notice         = $Notice
        primary        = $PrimaryProbe
        standby        = $StandbyProbe
        dependencies   = $script:InfraStatus
        note           = '周期复检只提示、不自动回切运行中服务（避免连接池漂移）；回切需重启编排'
    }
    ($payload | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $path -Encoding UTF8
    return $path
}

function Get-DbSummary {
    $p = $script:DbResolution.Primary
    $s = $script:DbResolution.Standby
    return ("共享库探测：primary={0}:{1} healthy={2}（{3}，{4}ms）/ standby={5}:{6} healthy={7}（{8}，{9}ms）⇒ mode={10}（{11}）" -f `
        $p.Host, $p.Port, $p.Healthy, $p.Method, $p.LatencyMs, `
        $s.Host, $s.Port, $s.Healthy, $s.Method, $s.LatencyMs, `
        $script:DbResolution.Mode, $script:DbResolution.Reason)
}

function Assert-DbReadyOrExit {
    param([string]$ActionName)

    if ($DbMode -eq 'off') {
        Write-Log 'WARN' '共享库启动探测已关闭（-DbMode off），按配置文件地址启动'
        return
    }
    $evidence = Write-DbEvidence -ActionName $ActionName
    if ($script:DbResolution.Ok) {
        Write-Log 'INFO' (Get-DbSummary)
        if ($script:DbResolution.Mode -eq 'standby') {
            Write-Log 'WARN' ("备用库通道已启用（启动期环境覆盖，不改写 .env），覆盖服务：{0}" -f `
                ((@($script:DbOverrides.Keys) | Sort-Object) -join ','))
        }
        $infraSummary = Get-InfraSummary
        if ($infraSummary) { Write-Log 'INFO' $infraSummary }
        $infraSwitched = @($script:InfraSwitched)
        if ($infraSwitched.Count -gt 0) {
            Write-Log 'WARN' ("公共设施已切备用：{0}（数据面同步问题暂时挂起——备用数据可能为空或落后，请人工核对）" -f ($infraSwitched -join ','))
        }
        $infraDown = Get-InfraDownNames
        if ($infraDown.Count -gt 0) {
            Write-Log 'WARN' ("公共设施不可达：{0}（不阻断启动；可执行 D:\infra\start-infra.ps1 启动本机备用）" -f ($infraDown -join ','))
        }
        if ($script:ProbeMode -ne 'data-plane' -and @($script:ProbeNotes).Count -gt 0) {
            Write-Log 'WARN' ("数据面探针降级为 {0}：{1}" -f $script:ProbeMode, ((@($script:ProbeNotes) | Select-Object -First 3) -join '；'))
        }
        Write-Log 'INFO' "共享库探测证据：$evidence"
        return
    }
    Write-Log 'ERROR' (Get-DbSummary)
    Write-Log 'ERROR' "共享库探测证据：$evidence"
    if ($script:DbResolution.RequestedMode -in @('primary', 'standby')) {
        Write-Log 'ERROR' ("强制模式（{0}）目标不可达，拒绝启动任何服务（退出码 2）" -f $script:DbResolution.RequestedMode)
    } else {
        Write-Log 'ERROR' '主备均不可达，拒绝启动任何服务（退出码 2）；请先恢复主用或启动备用基础设施'
    }
    exit 2
}

function Invoke-DbChannelRecheck {
    # 周期复检（monitor）：只判定 + 提示，**不自动回切**运行中服务。
    if ($DbMode -eq 'off') { return }

    $primary = $script:DbPrimaryEndpoint
    $standby = $script:DbStandbyEndpoint

    # 复检同样走数据面（只探 PG 两端，避免每分钟把四设施也打一遍）
    $pgSpec = New-InfraProbeSpec -PgPrimaryHost $primary.Host -PgPrimaryPort $primary.Port `
        -PgStandbyHost $standby.Host -PgStandbyPort $standby.Port -Endpoints @{}
    Invoke-DataPlaneProbe -Spec $pgSpec | Out-Null

    $primaryProbe = Get-TargetHealth -Key 'pg.primary' -TargetHost $primary.Host -TargetPort $primary.Port -Postgres
    $standbyProbe = Get-TargetHealth -Key 'pg.standby' -TargetHost $standby.Host -TargetPort $standby.Port -Postgres

    $desiredMode = if ($primaryProbe.Healthy) { 'primary' } elseif ($standbyProbe.Healthy) { 'standby' } else { 'unavailable' }
    $currentMode = $script:DbResolution.Mode

    $notice = ''
    $level = 'WARN'
    if ($currentMode -eq 'standby' -and $primaryProbe.Healthy) {
        $notice = ("主用共享库已恢复（{0}:{1}），当前运行在备用通道；回切需在维护窗口重启编排（不自动回切）" -f $primary.Host, $primary.Port)
        $level = 'INFO'
    } elseif ($currentMode -eq 'standby' -and -not $standbyProbe.Healthy) {
        $notice = ("备用库通道亦不可达（primary healthy=false / standby {0}:{1} healthy=false），请立即恢复主用或本机备用" -f $standby.Host, $standby.Port)
        $level = 'ERROR'
    } elseif ($currentMode -eq 'primary' -and -not $primaryProbe.Healthy) {
        $notice = ("主用共享库失联（{0}:{1}），当前连接池仍指向主用；建议重启编排进入备用通道（standby healthy={2}）" -f `
            $primary.Host, $primary.Port, $standbyProbe.Healthy)
        $level = 'ERROR'
    }

    if (-not $notice) {
        $script:DbMonitorState.LastNotice = ''
        return
    }
    if ($script:DbMonitorState.LastNotice -eq $notice) { return }
    $script:DbMonitorState.LastNotice = $notice
    Write-Log $level $notice
    $evidence = Write-DbRecheckEvidence -CurrentMode $currentMode -DesiredMode $desiredMode `
        -PrimaryProbe (@{ Host = $primary.Host; Port = $primary.Port } + $primaryProbe) `
        -StandbyProbe (@{ Host = $standby.Host; Port = $standby.Port } + $standbyProbe) `
        -Notice $notice
    Write-Log 'INFO' "周期复检证据：$evidence"
}

function Invoke-DbCheck {
    param([switch]$AsJson)

    if ($DbMode -eq 'off') {
        if (-not $AsJson) { Write-Log 'WARN' '共享库启动探测已关闭（-DbMode off）' }
        if ($AsJson) {
            $offPayload = [ordered]@{
                schema_version = 3
                action         = 'dbcheck'
                ok             = $true
                requested_mode = $DbMode
                resolved_mode  = 'off'
                reason         = '探测关闭（-DbMode off）'
                data_plane     = [ordered]@{ probe_mode = 'off'; switched = @(); degraded = @(); targets = @{} }
            }
            Write-Host ($offPayload | ConvertTo-Json -Depth 5)
        }
        return 0
    }
    $evidence = Write-DbEvidence -ActionName 'dbcheck'
    if ($AsJson) {
        $payload = New-DbEvidencePayload -ActionName 'dbcheck'
        $payload['evidence_path'] = $evidence
        Write-Host ($payload | ConvertTo-Json -Depth 8)
        if (-not $script:DbResolution.Ok) { return 2 }
        return 0
    }
    Write-Host (Get-DbSummary)
    $infraSummary = Get-InfraSummary
    if ($infraSummary) { Write-Host $infraSummary }
    $infraSwitched = @($script:InfraSwitched)
    if ($infraSwitched.Count -gt 0) {
        Write-Host ("  公共设施已切备用：{0}（数据面同步挂起，备用数据可能为空或落后）" -f ($infraSwitched -join ','))
        foreach ($name in $infraSwitched) {
            $keys = @($script:InfraApplied[$name])
            if ($keys.Count -gt 0) { Write-Host ("    {0,-7} 覆盖键：{1}" -f $name, ($keys -join ',')) }
        }
    }
    $infraDown = Get-InfraDownNames
    if ($infraDown.Count -gt 0) {
        Write-Host ("  公共设施不可达：{0}（不阻断启动；可执行 D:\infra\start-infra.ps1）" -f ($infraDown -join ','))
    }
    if ($script:ProbeMode -ne 'data-plane' -and @($script:ProbeNotes).Count -gt 0) {
        Write-Host ("  数据面探针降级为 {0}：{1}" -f $script:ProbeMode, ((@($script:ProbeNotes) | Select-Object -First 3) -join '；'))
    }
    if ($script:DbAppliedEndpoints.Count -gt 0) {
        Write-Host '  备用通道生效目标（口令已脱敏）：'
        foreach ($key in ($script:DbAppliedEndpoints.Keys | Sort-Object)) {
            Write-Host ("    {0,-11} → {1}" -f $key, $script:DbAppliedEndpoints[$key])
        }
    }
    Write-Host ("  证据：{0}" -f $evidence)
    if (-not $script:DbResolution.Ok) {
        Write-Log 'ERROR' '主备均不可达（dbcheck 判定失败）'
        return 2
    }
    return 0
}

function Invoke-Start {
    param([switch]$WithCheck)
    Assert-DbReadyOrExit -ActionName 'start'
    $targets = if ($Only.Count -gt 0) { $Only } else { ($services | ForEach-Object { $_.Name }) }
    $topo = Get-TopoOrder | Where-Object { $targets -contains $_ }
    Write-Log 'INFO' ("一键启动开始，服务拓扑序：{0}" -f ($topo -join ' → '))
    foreach ($name in $topo) {
        $svc = Get-ServiceDef $name
        if (-not $svc) { Write-Log 'WARN' "未知服务：$name"; continue }
        Start-Service $svc
    }
    Write-Log 'INFO' "一键启动完成，最终状态："
    Get-AllStatus
    if ($WithCheck) {
        Write-Log 'INFO' "开始全量服务检查..."
        Invoke-CheckAll
    }
}

function Invoke-Monitor {
    Assert-DbReadyOrExit -ActionName 'monitor'
    $recheckEvery = if ($DbRecheckSec -gt 0) { $DbRecheckSec } else { [Math]::Max(60, $Interval) }
    Write-Log 'INFO' ("监控模式启动：Interval={0}s，MaxRestarts={1}/服务，共享库周期复检={2}s" -f $Interval, $MaxRestarts, $recheckEvery)
    $restartCount = @{}
    $nextRecheckAt = (Get-Date).AddSeconds($recheckEvery)
    while ($true) {
        if ((Get-Date) -ge $nextRecheckAt) {
            Invoke-DbChannelRecheck
            $nextRecheckAt = (Get-Date).AddSeconds($recheckEvery)
        }
        foreach ($svc in $services) {
            if ($Only.Count -gt 0 -and $Only -notcontains $svc.Name) { continue }
            $healthy = Test-Health $svc
            $portPid = Get-PortPid $svc.Port
            if ($healthy) {
                if ($restartCount.ContainsKey($svc.Name)) { $restartCount.Remove($svc.Name) }
                continue
            }
            if (-not $portPid) {
                # 服务未运行 → 启动
                Write-Log 'WARN' ("检测到 {0} 宕机（端口 {1} 无监听），自动重启..." -f $svc.Name, $svc.Port)
                $ok = Start-Service $svc
                if (-not $ok) {
                    $n = [int]$restartCount[$svc.Name] + 1
                    $restartCount[$svc.Name] = $n
                    Write-Log 'WARN' ("{0} 重启失败（第 {1}/{2} 次）" -f $svc.Name, $n, $MaxRestarts)
                    if ($n -ge $MaxRestarts) {
                        Write-Log 'ERROR' ("{0} 连续重启 {1} 次失败，停止自动重启（需人工介入）" -f $svc.Name, $MaxRestarts)
                        $restartCount[$svc.Name] = 0
                    }
                }
            }
            else {
                Write-Log 'WARN' ("{0} 端口 {1} 有监听但健康检查失败（PID {2}），跳过重启避免误杀" -f $svc.Name, $svc.Port, $portPid)
            }
        }
        Start-Sleep -Seconds $Interval
    }
}

function Invoke-CheckAll {
    param([switch]$OnlyAfterStart)
    $targets = if ($Only.Count -gt 0) { $Only } else { ($services | ForEach-Object { $_.Name }) }
    "===== 全量服务检查报告（{0}）=====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    $totalPass = 0; $totalFail = 0; $totalSkip = 0

    foreach ($svc in $services) {
        if ($targets -notcontains $svc.Name) { continue }
        $baseUrl = if ($svc.CheckBase) { $svc.CheckBase } else { "http://127.0.0.1:{0}" -f $svc.Port }
        $portPid = Get-PortPid $svc.Port
        $up = [bool]$portPid

        ""  # 空行分隔
        "---- [{0}] {1}（端口 {2}）----" -f $svc.Name, $svc.Desc, $svc.Port
        if (-not $up) {
            $totalSkip++
            "  [SKIP] 服务未运行（端口 {0} 无监听）" -f $svc.Port
            continue
        }
        "  [INFO] 端口 {0} 监听中（PID {1}）" -f $svc.Port, $portPid

        # 1) 健康探活
        $healthy = Test-Health $svc
        if ($healthy) {
            $totalPass++
            "  [PASS] 健康探活 OK（{0}）" -f ($svc.Health -join ' / ')
        }
        else {
            $totalFail++
            "  [FAIL] 健康探活失败（{0}）" -f ($svc.Health -join ' / ')
        }

        # 2) 深度业务检查
        if ($svc.Checks) {
            foreach ($check in $svc.Checks) {
                $uri = $baseUrl + $check.Path
                try {
                    $params = @{
                        Uri = $uri
                        Method = $check.Method
                        TimeoutSec = 8
                        UseBasicParsing = $true
                        ErrorAction = 'Stop'
                    }
                    if ($check.Headers) { $params['Headers'] = $check.Headers }
                    $resp = Invoke-WebRequest @params
                    $code = [int]$resp.StatusCode
                    # 405 表示端点存在但方法不允许：对 GET 检查端点存在性场景按预期处理
                    if ($code -eq $check.Expect -or ($code -eq 405 -and $check.Expect -eq 405)) {
                        $totalPass++
                        "  [PASS] {0}（{1} {2} → {3}）" -f $check.Name, $check.Method, $check.Path, $code
                    }
                    else {
                        $totalFail++
                        "  [FAIL] {0}（{1} {2} → {3}，期望 {4}）" -f $check.Name, $check.Method, $check.Path, $code, $check.Expect
                    }
                }
                catch {
                    $err = $_.Exception
                    $msg = $err.Message
                    # 解析 HTTP 错误响应码（如 401/403/404/405）
                    $statusCode = $null
                    if ($err.Response) {
                        try { $statusCode = [int]$err.Response.StatusCode } catch { }
                    }
                    if ($statusCode -eq $check.Expect) {
                        $totalPass++
                        "  [PASS] {0}（{1} {2} → {3}，符合预期）" -f $check.Name, $check.Method, $check.Path, $statusCode
                    }
                    else {
                        $totalFail++
                        $detail = if ($statusCode) { "HTTP $statusCode" } else { $msg }
                        "  [FAIL] {0}（{1} {2} → {3}，期望 {4}）" -f $check.Name, $check.Method, $check.Path, $detail, $check.Expect
                    }
                }
            }
        }
    }

    "" 
    "===== 汇总：PASS {0} | FAIL {1} | SKIP {2} =====" -f $totalPass, $totalFail, $totalSkip
    if ($totalFail -gt 0) {
        Write-Log 'WARN' ("全量检查完成：{0} PASS / {1} FAIL / {2} SKIP" -f $totalPass, $totalFail, $totalSkip)
    }
    else {
        Write-Log 'INFO' ("全量检查完成：{0} PASS / {1} FAIL / {2} SKIP" -f $totalPass, $totalFail, $totalSkip)
    }
}

function Invoke-Status {
    "===== 多系统服务状态（{0}）=====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    "{0,-11} {1,-6} {2,-30} {3} {4}" -f '服务', '端口', '说明', '状态', 'PID'
    Get-AllStatus
    "================================="
    "脚本日志：$LogFile"
}

# R-384/BL-147-04：归档命名自检（**在系统临时目录内**完成，不触碰真实采集目录）。
# 目的：让「同日重复启动 → 归档改名」这条真实路径被实际执行并校验——
# 旧实现产出 <svc>-YYYYMMDD.err-HHmmss.log（适配器白名单不匹配、日志中心漏读），
# 新实现须产出 <svc>-YYYYMMDD-HHmmss[.err].<ext>。
function Test-ServiceLogArchiveSelfCheck {
    param([string]$VerifierPath)
    $selfCheckRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("openbase-namecheck-{0}" -f ([Guid]::NewGuid().ToString('N').Substring(0, 8)))
    $day = Get-Date -Format 'yyyyMMdd'
    $originalRoot = $script:ServiceLogDir
    $archiveLeaves = @()
    try {
        $script:ServiceLogDir = $selfCheckRoot
        foreach ($svc in ($services | Where-Object { $_.JsonStream })) {
            $svcDir = Get-ServiceLogDir $svc.Name
            New-Item -ItemType Directory -Force -Path $svcDir | Out-Null
            $names = Get-ServiceLogFileName -Svc $svc -Day $day
            foreach ($leaf in @($names.Out, $names.Err)) {
                # 造出「上一轮非空内容」→ 触发归档分支
                Set-Content -Path (Join-Path $svcDir $leaf) -Value '{"ts":"2026-01-01T00:00:00Z"}' -Encoding UTF8
            }
            $target = Initialize-ServiceLogTarget $svc
            foreach ($leaf in @($names.Out, $names.Err)) {
                if (Test-Path (Join-Path $svcDir $leaf)) {
                    throw ("归档自检失败：{0}/{1} 未被归档（重定向会覆盖历史输出）" -f $svc.Name, $leaf)
                }
            }
            foreach ($archived in @(Get-ChildItem -Path $svcDir -File)) {
                $archiveLeaves += ("{0}/{1}" -f $svc.Name, $archived.Name)
            }
            if (($target.Out -notlike ("*" + $names.Out)) -or ($target.Err -notlike ("*" + $names.Err))) {
                throw ("归档自检失败：{0} 返回目标与实际命名不一致" -f $svc.Name)
            }
        }
        $cliArgs = @($VerifierPath)
        foreach ($leaf in $archiveLeaves) { $cliArgs += @('--file', $leaf) }
        & python @cliArgs
        if ($LASTEXITCODE -ne 0) {
            throw "归档自检失败：归档文件名存在适配器不可见的形态"
        }
        "  [PASS] 归档自检通过：{0} 个归档文件全部被适配器白名单接受" -f $archiveLeaves.Count
    }
    finally {
        $script:ServiceLogDir = $originalRoot
        if (Test-Path $selfCheckRoot) { Remove-Item -Recurse -Force $selfCheckRoot -ErrorAction SilentlyContinue }
    }
}

# R-384/BL-147-04：采集文件命名实测（**不启停任何服务**；归档自检在系统临时目录内完成）。
# ① 打印各服务将产出的采集文件名（含归档样例），并把四仓条目交由
#    scripts/verify_repo_log_naming.py 以适配器白名单（REPO_LOG_NAME_RE，唯一判据）
#    逐条校验——非 0 退出即抛错（命名漂移不得静默放过）；
# ② 对在盘日志目录做一次实测扫描（修复前旧归档命名按 legacy 登记，不阻断）；
# ③ 归档命名自检（临时目录内实跑 Initialize-ServiceLogTarget）。
function Invoke-NameCheck {
    $day = Get-Date -Format 'yyyyMMdd'
    $stamp = Get-Date -Format 'HHmmss'
    $verifier = Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\verify_repo_log_naming.py'
    if (-not (Test-Path $verifier)) {
        throw "缺少命名校验脚本：$verifier"
    }
    "===== 采集文件命名实测（{0}）=====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    "采集根目录（ServiceLogRoot）：$ServiceLogDir"
    "{0,-11} {1,-10} {2,-30} {3,-30} {4}" -f '服务', '结构化流', 'stdout 采集文件', 'stderr 采集文件', '归档样例（stdout / stderr）'
    $entries = @()
    foreach ($svc in $services) {
        $names = Get-ServiceLogFileName -Svc $svc -Day $day
        $archiveOut = Get-ServiceLogArchiveName -LeafName $names.Out -Stamp $stamp
        $archiveErr = Get-ServiceLogArchiveName -LeafName $names.Err -Stamp $stamp
        $stream = if ($svc.JsonStream) { $svc.JsonStream } else { '-' }
        "{0,-11} {1,-10} {2,-30} {3,-30} {4} / {5}" -f $svc.Name, $stream, $names.Out, $names.Err, $archiveOut, $archiveErr
        foreach ($leaf in @($names.Out, $names.Err, $archiveOut, $archiveErr)) {
            $entries += ("{0}/{1}" -f $svc.Name, $leaf)
        }
    }
    "" 
    "---- ① 编排器命名校验（唯一判据 = REPO_LOG_NAME_RE）----"
    $cliArgs = @($verifier)
    foreach ($entry in $entries) { $cliArgs += @('--file', $entry) }
    & python @cliArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Log 'ERROR' ("采集文件命名实测失败（退出码 {0}）：存在适配器不可见的命名" -f $LASTEXITCODE)
        throw "采集文件命名未对齐：请修正 Get-ServiceLogFileName / Get-ServiceLogArchiveName"
    }
    "" 
    "---- ② 在盘日志实测扫描（历史旧命名按 legacy 登记）----"
    & python $verifier --logs-root $ServiceLogDir --tolerate-legacy-err-archive
    if ($LASTEXITCODE -ne 0) {
        Write-Log 'WARN' ("在盘日志扫描存在不可见文件（退出码 {0}），请核对是否为新命名漂移" -f $LASTEXITCODE)
    }
    "" 
    "---- ③ 归档命名自检（临时目录内实跑归档路径）----"
    Test-ServiceLogArchiveSelfCheck -VerifierPath $verifier
    "" 
    "===== 命名实测完成（① 全部通过；② 结果见上；③ 归档自检已通过）====="
    "脚本日志：$LogFile"
}

function Invoke-Stop {
    $targets = if ($Only.Count -gt 0) { $Only } else { ($services | ForEach-Object { $_.Name }) }
    $topo = Get-TopoOrder | Where-Object { $targets -contains $_ }
    $reverse = @($topo | Select-Object -Last ($topo.Count)) | Select-Object -First $topo.Count
    [array]::Reverse($reverse)
    Write-Log 'INFO' ("停止服务（逆拓扑）：{0}" -f ($reverse -join ' ← '))
    foreach ($name in $reverse) {
        $svc = Get-ServiceDef $name
        if ($svc) { Stop-Service $svc }
    }
    Write-Log 'INFO' '停止完成'
}

switch ($Action) {
    'start'      { Invoke-Start }
    'startcheck' { Invoke-Start -WithCheck }
    'monitor'    { Invoke-Monitor }
    'status'     { Invoke-Status }
    'checkall'   { Invoke-CheckAll }
    'namecheck'  { Invoke-NameCheck }
    'stop'       { Invoke-Stop }
    'dbcheck'    { exit (Invoke-DbCheck -AsJson:$Json) }
}
