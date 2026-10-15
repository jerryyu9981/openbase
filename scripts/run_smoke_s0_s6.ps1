<#
.SYNOPSIS
  S7-T6-2 smoke S0-S6 real-execution wrapper (cross-repo bring-up + run scripts/smoke_s0_s6.py).

.DESCRIPTION
  Loads .env.shared-infra (POSTGRES_URL/REDIS_URL/API keys), brings up OpenLLM(8001) + OpenBase(8000)
  if down (OpenRAG/OpenMemory/DPS/OIDC-IdP assumed resident), then runs the smoke runner and prints
  the summary. Started services are recycled at the end (sandbox recycles children on command end).

.EXAMPLE
  .\scripts\run_smoke_s0_s6.ps1
  .\scripts\run_smoke_s0_s6.ps1 -OutDir doc\test\evidence\s7\smoke
#>
[CmdletBinding()]
param(
    [string]$Python,
    [string]$OutDir = "$(Split-Path $PSScriptRoot -Parent)\doc\test\evidence\s7\smoke",
    [string]$OutFile = ""
)
$ErrorActionPreference = 'Continue'
$OpenBaseRoot = Split-Path $PSScriptRoot -Parent
$DevRoot = Split-Path $OpenBaseRoot -Parent
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

function Test-Up { param($Url) try { (Invoke-WebRequest $Url -TimeoutSec 90 -UseBasicParsing).StatusCode -eq 200 } catch { $false } }

function Clear-Listener {
    param([int]$Port)
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($c) {
        $c.OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
        Write-Host ("  cleared stale listener on {0}" -f $Port)
    }
}

function Start-Svc {
    param([string]$Name, [int]$Port, [string]$Cwd, [string[]]$Args, [string]$Health, [hashtable]$ExtraEnv)
    if (Test-Up $Health) { Write-Host ("{0} already online" -f $Name); return }
    Clear-Listener -Port $Port
    if ($ExtraEnv) { foreach ($k in $ExtraEnv.Keys) { Set-Item -Path ("Env:" + $k) -Value $ExtraEnv[$k] } }
    $err = Join-Path $OutDir ("{0}.{1}.err.log" -f $Name, $Stamp)
    $outf = Join-Path $OutDir ("{0}.{1}.out.log" -f $Name, $Stamp)
    $p = Start-Process -FilePath $Py -ArgumentList $Args -WorkingDirectory $Cwd -PassThru -RedirectStandardOutput $outf -RedirectStandardError $err -WindowStyle Hidden
    $up = $false
    for ($i = 0; $i -lt 120; $i++) { Start-Sleep -Seconds 2; if (Test-Up $Health) { $up = $true; break } }
    Write-Host ("{0} up={1} ({2}s)" -f $Name, $up, ($i * 2))
    if (-not $up) {
        Write-Host ("  {0} NOT UP; err tail:" -f $Name)
        Get-Content $err -Tail 8 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ("    " + $_) }
    }
    return ,$p
}

$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PORT = '8001'
$obEnv = @{
    OPENBASE_DPS_UPSTREAM_BASE = 'http://127.0.0.1:8030'
    OPENBASE_DPS_ORG_MAP = '{"org-1":"dps-org-001","tenant-1":"dps-org-001"}'
    OPENBASE_DPS_TENANT_MAP = '{"org-1":"dps-tenant-001","tenant-1":"dps-tenant-001"}'
    OPENBASE_PROXY_CODE_MAP = '{"schema_version":1,"source_of_truth":"openbase.tenants.code","targets":{"rag":{"reserved_codes":["default","openrag-local"],"default_tenant_code":"tenant-1"},"memory":{"reserved_codes":[],"default_tenant_code":"tenant-1"}}}'
}

$started = @()
$p1 = Start-Svc -Name 'openllm' -Port 8001 -Cwd "$DevRoot\OpenLLM\backend" -Args @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8001') -Health 'http://127.0.0.1:8001/health' -ExtraEnv $null
if ($p1) { $started += $p1 }
$p2 = Start-Svc -Name 'openbase' -Port 8000 -Cwd $OpenBaseRoot -Args @('-m','uvicorn','openbase.demo_app:app','--host','127.0.0.1','--port','8000') -Health 'http://127.0.0.1:8000/health' -ExtraEnv $obEnv
if ($p2) { $started += $p2 }

$env:SMOKE_COMMIT = (git -C $OpenBaseRoot rev-parse --short HEAD 2>$null)
$env:PYTHONIOENCODING = 'utf-8'
& $Py -B (Join-Path $OpenBaseRoot 'scripts\smoke_s0_s6.py') $OutFile
foreach ($p in $started) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
