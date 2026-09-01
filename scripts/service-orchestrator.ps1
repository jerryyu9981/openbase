# ============================================================================
# OpenBase 多系统服务编排脚本（service-orchestrator.ps1）
#
# 功能：
#   1) start   ：一键启动全部服务（按依赖拓扑 + 端口预检 + 依赖健康检查）
#   2) monitor ：实时健康检测，发现宕机自动重启（自愈）
#   3) status  ：查询全部服务状态（端口占用 / 健康 / PID）
#   4) stop    ：停止全部服务（按记录的 PID，逆拓扑）
#
# 服务/端口/依赖清单（单一事实源）：doc/design/OpenBase-多系统端口统筹方案-v1.0.0.md
#   8000 OpenBase（固定） | 8001 OpenLLM | 8010 OpenRAG | 8020 OpenMemory
#   8030 DPS | 5173 统一前端 | 5432 PG / 6333 Qdrant / 6380 Redis（公共基础设施）
#
# 用法示例：
#   .\scripts\service-orchestrator.ps1 -Action start
#   .\scripts\service-orchestrator.ps1 -Action start -Only openbase,frontend
#   .\scripts\service-orchestrator.ps1 -Action monitor -Interval 15 -MaxRestarts 3
#   .\scripts\service-orchestrator.ps1 -Action status
#   .\scripts\service-orchestrator.ps1 -Action stop
#
# 环境要求：Windows PowerShell 5+；各服务 Python 依赖已安装（各项目自有环境）
# ============================================================================

[CmdletBinding()]
param(
    [ValidateSet('start', 'monitor', 'status', 'stop')]
    [string]$Action = 'start',
    [string[]]$Only = @(),
    [int]$Interval = 15,
    [int]$HealthTimeout = 60,
    [int]$MaxRestarts = 3
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$LogDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'logs\service-orchestrator'
$PidFile = Join-Path $LogDir 'service-pids.json'
$LogFile = Join-Path $LogDir ("orchestrator-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

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
        Env     = @{ PORT = '8001' }
        Health  = @('http://127.0.0.1:8001/health', 'http://127.0.0.1:8001/api/v1/system/health')
        Depends = @()
        DepType = 'hard'
        Desc    = 'OpenLLM 大模型网关'
    },
    @{
        Name    = 'openrag'
        Port    = 8010
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenRAG'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'openrag.main:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8010')
        Env     = @{ OPENRAG_API_PORT = '8010' }
        Health  = @('http://127.0.0.1:8010/api/v1/system/health')
        Depends = @()
        DepType = 'hard'
        Desc    = 'OpenRAG 知识库/检索'
    },
    @{
        Name    = 'openmemory'
        Port    = 8020
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenMemory'
        Command = 'python'
        # complete 模式（Qdrant + PG + Redis + Neo4j 真实后端，依赖 192.168.0.151 共享基础设施）。
        # 首次启动会预载 faster-whisper/CLIP 模型，耗时较长（约 2~4 分钟），健康探测需放宽等待
        Args    = @('scripts\start_openmemory.py')
        Env     = @{}
        Health  = @('http://127.0.0.1:8020/health')
        Depends = @()
        DepType = 'hard'
        Desc    = 'OpenMemory 记忆服务（complete 模式，Qdrant+PG+Redis+Neo4j）'
    },
    @{
        Name    = 'dps'
        Port    = 8030
        Cwd     = 'D:\Trae CN\myproject\Dev\DPS'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'rest_api.app:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8030')
        Env     = @{ API_PORT = '8030'; SQLITE_FALLBACK = 'true' }
        Health  = @('http://127.0.0.1:8030/health/liveness')
        Depends = @()
        DepType = 'hard'
        Desc    = 'DPS 数据画像系统（任务书 M4 修复后可用）'
    },
    @{
        Name    = 'openbase'
        Port    = 8000
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenBase'
        Command = 'python'
        Args    = @('-m', 'uvicorn', 'openbase.demo_app:app', '--host', '127.0.0.1', '--port', '8000')
        Env     = @{}
        Health  = @('http://127.0.0.1:8000/openapi.json')
        Depends = @('openllm', 'openrag', 'openmemory', 'dps')
        DepType = 'soft'
        Desc    = 'OpenBase 统一底座（JWT 门禁 + 四 proxy）'
    },
    @{
        Name    = 'frontend'
        Port    = 5173
        Cwd     = 'D:\Trae CN\myproject\Dev\OpenBase\openbase-ui'
        Command = 'npm.cmd'   # Windows 下 npm 为 npm.cmd（Start-Process 需带扩展名）
        Args    = @('run', 'dev')
        Env     = @{}
        Health  = @('http://127.0.0.1:5173/')
        Depends = @('openbase')
        DepType = 'hard'
        Desc    = '统一前端（vite dev，proxy → 8000）'
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
    param([hashtable]$Svc, [int]$TimeoutSec = 3)
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
    'start'   { Invoke-Start }
    'monitor' { Invoke-Monitor }
    'status'  { Invoke-Status }
    'stop'    { Invoke-Stop }
}
