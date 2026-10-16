<#
.SYNOPSIS
  S7-T6-2 smoke S0-S6 real-execution wrapper (managed-orchestrator bring-up + run scripts/smoke_s0_s6.py).

.DESCRIPTION
  Loads .env.shared-infra (POSTGRES_URL/REDIS_URL/API keys), then drives the service lifecycle EXCLUSIVELY
  through the managed orchestrator `scripts/service-orchestrator.ps1`
  (`-Action stop -Only ...` -> `-Action start -Only ...` -> ... -> `-Action stop -Only ...`), then waits for
  OpenLLM upstream components + OpenBase /health (ready-gate) and runs the smoke runner.

  Lifecycle discipline (SHR gate S7-T1-4 / F-10): `scripts/service-orchestrator.ps1` is the ONLY permitted
  service-lifecycle entry point. This wrapper performs no direct process termination itself; stale listeners
  are released by the orchestrator's `stop` (recorded PID, falling back to the port owner).

  Services started by the orchestrator stay alive only while this command runs (the sandbox recycles child
  processes at command end), which is why start + probe + stop must stay inside this single command.

.EXAMPLE
  .\scripts\run_smoke_s0_s6.ps1
  .\scripts\run_smoke_s0_s6.ps1 -OutDir doc\test\evidence\s7\smoke
#>
[CmdletBinding()]
param(
    [string]$Python,
    [string]$OutDir = "$(Split-Path $PSScriptRoot -Parent)\doc\test\evidence\s7\smoke",
    [string]$OutFile = "",
    # Per-service health wait handed to the orchestrator (OpenLLM cold start can exceed the 60s default)
    [int]$HealthTimeout = 240
)
$ErrorActionPreference = 'Continue'
$OpenBaseRoot = Split-Path $PSScriptRoot -Parent
$Orchestrator = Join-Path $PSScriptRoot 'service-orchestrator.ps1'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Stamp = Get-Date -Format 'yyyyMMddHHmmss'
if (-not $OutFile) { $OutFile = Join-Path $OutDir "smoke-summary-$Stamp.json" }

function Resolve-Python {
    if ($Python -and (Test-Path $Python)) { return $Python }
    $cand = "C:\Users\jerry\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python\python.exe"
    if (Test-Path $cand) { return $cand }
    $shimDir = Join-Path $OpenBaseRoot '.venv\shim'
    if (Test-Path (Join-Path $shimDir 'python.cmd')) { $env:PATH = $shimDir + ';' + $env:PATH; return 'python' }
    return 'python'
}

# load shared-infra env (POSTGRES_URL/REDIS_URL/OPENRAG_API_KEY/OPENMEMORY_API_KEY/...) like the orchestrator
$sharedEnv = Join-Path $OpenBaseRoot '.env.shared-infra'
if (Test-Path $sharedEnv) {
    Get-Content $sharedEnv | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $i = $line.IndexOf('=')
            $k = $line.Substring(0, $i).Trim(); $v = $line.Substring($i + 1).Trim()
            if ($k) { Set-Item -Path ("Env:" + $k) -Value $v }
        }
    }
    Write-Output "loaded .env.shared-infra"
}

$Py = Resolve-Python
Write-Output "python = $Py"

# The managed orchestrator launches services with the bare command `python`; make sure a python.exe is on
# PATH so its Start-Process can resolve it (the sandbox PATH ships no interpreter by default).
$PyDir = Split-Path $Py -Parent
if ($PyDir -and (Test-Path (Join-Path $PyDir 'python.exe'))) { $env:PATH = $PyDir + ';' + $env:PATH }

function Test-Up { param($Url) try { (Invoke-WebRequest $Url -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200 } catch { $false } }

# Managed lifecycle entry (SHR S7-T1-4): this script never terminates processes directly.
function Invoke-Managed {
    param([string]$Action, [string[]]$Services)
    if (-not (Test-Path $Orchestrator)) { Write-Output ("WARN: orchestrator not found: {0}" -f $Orchestrator); return }
    Write-Output ("== orchestrator -Action {0} -Only {1} ==" -f $Action, ($Services -join ','))
    try {
        & $Orchestrator -Action $Action -Only $Services -HealthTimeout $HealthTimeout
    } catch {
        Write-Output ("  orchestrator {0} error: {1}" -f $Action, $_.Exception.Message)
    }
}

$Targets = @('openbase', 'openllm')
Invoke-Managed -Action 'stop' -Services $Targets
Invoke-Managed -Action 'start' -Services $Targets

# ready-gate：OpenLLM 三上游组件 ok + OpenBase /health（消除启动窗口 S0-1/S0-5 抖动；OpenLLM 冷启动实测 >240s）
function Test-LLMReady {
    try {
        $r = Invoke-RestMethod 'http://127.0.0.1:8001/openllm/v1/health' -TimeoutSec 20
        $comp = $null
        if ($r.data -and $r.data.components) { $comp = $r.data.components } elseif ($r.components) { $comp = $r.components }
        if (-not $comp) { return $false }
        foreach ($k in 'openmemory','openrag','dps') {
            $v = $comp.$k
            $ok = ($v -eq 'ok') -or ($null -ne $v -and $v.status -eq 'ok')
            if (-not $ok) { return $false }
        }
        return $true
    } catch { return $false }
}
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    if ((Test-LLMReady) -and (Test-Up 'http://127.0.0.1:8000/health')) { $ready = $true; break }
    Start-Sleep -Seconds 5
}
Write-Output ("ready-gate: ready={0} ({1}s)" -f $ready, ($i * 5))

$env:SMOKE_COMMIT = (git -C $OpenBaseRoot rev-parse --short HEAD 2>$null)
$env:PYTHONIOENCODING = 'utf-8'
& $Py -B (Join-Path $OpenBaseRoot 'scripts\smoke_s0_s6.py') $OutFile
$rc = $LASTEXITCODE

Invoke-Managed -Action 'stop' -Services $Targets
exit $rc
