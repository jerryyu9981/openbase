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
#
# 环境要求：Windows PowerShell 5+；各服务 Python 依赖已安装（各项目自有环境）
# ============================================================================

[CmdletBinding()]
param(
    [ValidateSet('start', 'startcheck', 'monitor', 'status', 'checkall', 'stop')]
    [string]$Action = 'start',
    [string[]]$Only = @(),
    [int]$Interval = 15,
    [int]$HealthTimeout = 60,
    [int]$MaxRestarts = 3,
    # 沙箱/受限环境日志目录覆盖（默认 OpenBase\logs\service-orchestrator）
    [string]$LogRoot = ''
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
        Env     = @{ PORT = '8001'; PYTHONDONTWRITEBYTECODE = '1' }
        Health  = @('http://127.0.0.1:8001/health', 'http://127.0.0.1:8001/api/v1/system/health')
        Depends = @()
        DepType = 'hard'
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
        Env     = @{ OPENRAG_API_PORT = '8010'; PYTHONDONTWRITEBYTECODE = '1' }
        Health  = @('http://127.0.0.1:8010/api/v1/system/health')
        Depends = @()
        DepType = 'hard'
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
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenMemory'
        Command = 'python'
        # complete 模式（Qdrant + PG + Redis + Neo4j 真实后端，依赖 192.168.0.151 共享基础设施）。
        # 首次启动会预载 faster-whisper/CLIP 模型，耗时较长（约 2~4 分钟），健康探测需放宽等待
        Args    = @('scripts\start_openmemory.py')
        # PYTHONDONTWRITEBYTECODE 绕过沙箱禁止写 __pycache__ 的限制（与 openrag/dps 一致）
        Env     = @{ PYTHONDONTWRITEBYTECODE = '1' }
        Health  = @('http://127.0.0.1:8020/health')
        Depends = @()
        DepType = 'hard'
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
        }
        Health  = @('http://127.0.0.1:8030/health/liveness')
        Depends = @()
        DepType = 'hard'
        Desc    = 'DPS 数据画像系统'
        Checks  = @(
            @{ Name = '存活探针';   Method = 'GET'; Path = '/health/liveness'; Expect = 200 }
            @{ Name = 'API 文档';   Method = 'GET'; Path = '/openapi.json';    Expect = 200 }
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
        Env     = @{ OPENBASE_DPS_UPSTREAM_BASE = 'http://127.0.0.1:8030' }
        Health  = @('http://127.0.0.1:8000/openapi.json')
        Depends = @('openllm', 'openrag', 'openmemory', 'dps')
        DepType = 'soft'
        Desc    = 'OpenBase 统一底座（JWT 门禁 + 四 proxy）'
        Checks  = @(
            @{ Name = 'OpenAPI 文档';  Method = 'GET'; Path = '/openapi.json';    Expect = 200 }
            # /api/v1/health 需 JWT 鉴权，未带 token 返回 401 属正常（端点存在 + 门禁生效）
            @{ Name = '健康端点(401=门禁)'; Method = 'GET'; Path = '/api/v1/health'; Expect = 401 }
            @{ Name = '登录端点';      Method = 'GET'; Path = '/api/v1/auth/login'; Expect = 405 }
        )
    },
    @{
        Name    = 'frontend'
        Port    = 5173
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenBase\openbase-ui'
        Command = 'npm.cmd'   # Windows 下 npm 为 npm.cmd（Start-Process 需带扩展名）
        Args    = @('run', 'dev')
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
    # 2) 依赖健康检查
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
    # 3) 设置环境变量（Start-Process 继承启动瞬间环境，串行启动无污染）
    $oldEnv = @{}
    foreach ($key in $Svc.Env.Keys) {
        $oldEnv[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, [string]$Svc.Env[$key], 'Process')
    }
    try {
        Write-Log 'INFO' ("启动 {0}（{1}）：{2} {3}（cwd={4}）" -f $Svc.Name, $Svc.Desc, $Svc.Command, ($Svc.Args -join ' '), $Svc.Cwd)
        $proc = Start-Process -FilePath $Svc.Command -ArgumentList $Svc.Args -WorkingDirectory $Svc.Cwd -WindowStyle Hidden -PassThru
        Save-Pid $Svc.Name $proc.Id
        Write-Log 'INFO' ("{0} 进程已创建（PID {1}），等待健康检查（超时 {2}s）..." -f $Svc.Name, $proc.Id, $HealthTimeout)
        $deadline = (Get-Date).AddSeconds($HealthTimeout)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 2
            if (Test-Health $Svc) {
                Write-Log 'INFO' ("{0} 健康检查通过 ✅（PID {1}，端口 {2}）" -f $Svc.Name, $proc.Id, $Svc.Port)
                return $true
            }
            if ($proc.HasExited) {
                Write-Log 'ERROR' ("{0} 进程提前退出（exit={1}）" -f $Svc.Name, $proc.ExitCode)
                Remove-Pid $Svc.Name
                return $false
            }
        }
        Write-Log 'WARN' ("{0} 健康检查超时（进程仍在，PID {1}）" -f $Svc.Name, $proc.Id)
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

function Invoke-Start {
    param([switch]$WithCheck)
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
    Write-Log 'INFO' ("监控模式启动：Interval={0}s，MaxRestarts={1}/服务" -f $Interval, $MaxRestarts)
    $restartCount = @{}
    while ($true) {
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
    'stop'       { Invoke-Stop }
}
