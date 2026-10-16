<#
.SYNOPSIS
  MTAUTH cross-repo "real-face" execution script (start 6 services + RA-06 real-face + cross-tenant A-write-B-read).

.DESCRIPTION
  Starts and health-checks OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS / OIDC-IdP within the SAME command
  (sandbox recycles child processes at command end, so execution must be atomic) via the managed orchestrator
  `scripts/service-orchestrator.ps1` (SHR gate S7-T1-4 / F-10: the orchestrator is the ONLY permitted
  service-lifecycle entry point; this script performs no direct process termination), then runs the real-face probes:
    §1 OIDC IdP real-face          -- discovery / jwks
    §2 Revocation immediacy (token_version) -- create temp user -> suspend -> reuse old token expects 401
    §3 Cross-repo forward chain    -- rag/memory-proxy upstream reachable
    §4 Cross-tenant A-write-B-read (-IncludeDataPlane) -- tenant A creates a collection; tenant B cannot see it
  Evidence is written to OutDir as JSON; copy the sanitized file into doc/test/evidence/manual/**.

.PARAMETER StartServices
  Start the six services (skip those already online; only processes started here are recycled at the end).

.PARAMETER Python
  Unified interpreter; default auto-detects the sandbox shared interpreter (all repos' deps present), falling back to the OpenBase shim.

.EXAMPLE
  .\scripts\verify_mtauth_realface.ps1 -StartServices -IncludeDataPlane
  .\scripts\verify_mtauth_realface.ps1                      # services already resident
#>
[CmdletBinding()]
param(
    [string]$Base = 'http://127.0.0.1:8000',
    [string]$Idp = 'http://127.0.0.1:8090',
    [string]$AdminUser = 'admin',
    [string]$AdminPass = 'admin123',
    [string]$TenantA = 'tenant-1',
    [string]$TenantB = 'tenant-2',
    [string]$Python,
    [switch]$StartServices,
    [switch]$IncludeDataPlane,
    [string]$OutDir = "$(Split-Path $PSScriptRoot -Parent)\doc\tmp\mtw"
)

$ErrorActionPreference = 'Continue'
$Stamp = Get-Date -Format 'yyyyMMddHHmmss'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OpenBaseRoot = Split-Path $PSScriptRoot -Parent
$Results = [ordered]@{ stamp = $Stamp; ts = (Get-Date).ToString('o'); base = $Base }

function Resolve-Python {
    if ($Python -and (Test-Path $Python)) { return $Python }
    $cand = "C:\Users\jerry\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python\python.exe"
    if (Test-Path $cand) { return $cand }
    $shimDir = Join-Path $OpenBaseRoot '.venv\shim'
    if (Test-Path (Join-Path $shimDir 'python.cmd')) { $env:PATH = $shimDir + ';' + $env:PATH; return 'python' }
    return 'python'
}

function Invoke-Probe {
    param([string]$Method, [string]$Url, $Headers, $Body)
    try {
        $p = @{ Uri = $Url; Method = $Method; TimeoutSec = 15; UseBasicParsing = $true }
        if ($Headers) { $p.Headers = $Headers }
        if ($Body) { $p.Body = $Body; $p.ContentType = 'application/json' }
        $r = Invoke-WebRequest @p
        return @{ status = [int]$r.StatusCode; body = $r.Content }
    } catch {
        $resp = $_.Exception.Response
        if ($resp) {
            try { $sr = New-Object System.IO.StreamReader($resp.GetResponseStream()); return @{ status = [int]$resp.StatusCode; body = $sr.ReadToEnd() } }
            catch { return @{ status = [int]$resp.StatusCode; body = '' } }
        }
        return @{ status = -1; body = [string]$_.Exception.Message }
    }
}
function Rec { param($name, $observed, $expected, $pass)
    $Results[$name] = @{ observed = $observed; expected = $expected; pass = [bool]$pass }
    $flag = 'FAIL'; if ($pass) { $flag = 'PASS' }
    Write-Output ("  [{0}] {1}  observed={2} expected={3}" -f $flag, $name, $observed, $expected)
}

$Py = Resolve-Python
Write-Output "python = $Py"

# The managed orchestrator launches services with the bare command `python`; make sure a python.exe is on
# PATH so its Start-Process can resolve it (the sandbox PATH ships no interpreter by default).
$PyDir = Split-Path $Py -Parent
if ($PyDir -and (Test-Path (Join-Path $PyDir 'python.exe'))) { $env:PATH = $PyDir + ';' + $env:PATH }

# ---- load shared-infra env (POSTGRES_URL/REDIS_URL/...) as service-orchestrator.ps1 does ----
# OpenBase settings resolve the DB/Redis DSN from process env (POSTGRES_URL/REDIS_URL); .env does NOT
# participate in DSN resolution. Without this, db_url falls back to localhost:5432 and every DB write fails.
$sharedEnv = Join-Path $OpenBaseRoot '.env.shared-infra'
if (Test-Path $sharedEnv) {
    Get-Content $sharedEnv | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $i = $line.IndexOf('=')
            $k = $line.Substring(0, $i).Trim()
            $v = $line.Substring($i + 1).Trim()
            if ($k) { Set-Item -Path ("Env:" + $k) -Value $v }
        }
    }
    Write-Output ("loaded .env.shared-infra; POSTGRES_URL={0}" -f $env:POSTGRES_URL)
} else { Write-Output "WARN: .env.shared-infra not found" }

# ---- managed service lifecycle (SHR gate S7-T1-4 / F-10) ----
# scripts/service-orchestrator.ps1 is the ONLY permitted lifecycle entry point; this script never
# terminates processes directly (stale listeners are released by the orchestrator's `stop`, which
# falls back to the port owner when no recorded PID exists).
$Orchestrator = Join-Path $PSScriptRoot 'service-orchestrator.ps1'
$LifecycleTargets = @('openbase', 'openllm', 'openrag', 'openmemory', 'oidc-idp', 'dps')

function Test-Up { param($Url) (Invoke-Probe 'GET' $Url $null $null).status -eq 200 }

function Invoke-Managed {
    param([string]$Action)
    if (-not (Test-Path $Orchestrator)) { Write-Output ("WARN: orchestrator not found: {0}" -f $Orchestrator); return }
    Write-Output ("== orchestrator -Action {0} -Only {1} ==" -f $Action, ($LifecycleTargets -join ','))
    try { & $Orchestrator -Action $Action -Only $LifecycleTargets }
    catch { Write-Output ("  orchestrator {0} error: {1}" -f $Action, $_.Exception.Message) }
}

if ($StartServices) {
    Write-Output "== start services (managed orchestrator, cross-repo) =="
    Invoke-Managed -Action 'stop'
    Invoke-Managed -Action 'start'
    $startHealth = [ordered]@{
        openbase   = 'http://127.0.0.1:8000/health'
        openllm    = 'http://127.0.0.1:8001/health'
        openrag    = 'http://127.0.0.1:8010/api/v1/system/health'
        openmemory = 'http://127.0.0.1:8020/health'
        'oidc-idp' = 'http://127.0.0.1:8090/health'
        dps        = 'http://127.0.0.1:8030/health/liveness'
    }
    foreach ($k in $startHealth.Keys) {
        $up = Test-Up $startHealth[$k]
        Write-Output ("  {0} up={1}" -f $k, $up)
        $Results[("start_" + $k)] = $up
    }
}

# ---- precheck ----
Write-Output "== precheck =="
$pre = @{ openbase = "$Base/health"; idp = "$Idp/.well-known/openid-configuration"; openrag = 'http://127.0.0.1:8010/health'; openmemory = 'http://127.0.0.1:8020/health'; dps = 'http://127.0.0.1:8030/health/liveness'; openllm = 'http://127.0.0.1:8001/health' }
foreach ($k in $pre.Keys) { $r = Invoke-Probe 'GET' $pre[$k] $null $null; Write-Output ("  {0} = {1}" -f $k, $r.status) }

# ---- §1 OIDC IdP real-face ----
Write-Output "== §1 OIDC IdP real-face =="
$disc = Invoke-Probe 'GET' "$Idp/.well-known/openid-configuration" $null $null
$jwks = Invoke-Probe 'GET' "$Idp/jwks" $null $null
$Results.oidc_discovery_body = $disc.body
Rec 'oidc_discovery_200' $disc.status 200 ($disc.status -eq 200)
Rec 'oidc_jwks_200' $jwks.status 200 ($jwks.status -eq 200)

$login = Invoke-Probe 'POST' "$Base/api/v1/auth/login" $null (@{ username = $AdminUser; password = $AdminPass } | ConvertTo-Json -Compress)
Rec 'admin_login_200' $login.status 200 ($login.status -eq 200)
$adminTok = $null; try { $adminTok = ($login.body | ConvertFrom-Json).access_token } catch {}
$adminH = @{ Authorization = ("Bearer " + $adminTok) }
$me = Invoke-Probe 'GET' "$Base/api/v1/auth/me" $adminH $null
Rec 'admin_me_200' $me.status 200 ($me.status -eq 200)

# ---- §2 revocation immediacy ----
Write-Output "== §2 revocation immediacy (token_version) =="
$uname = "probe_$Stamp"
$create = Invoke-Probe 'POST' "$Base/api/v1/users" $adminH (@{ username = $uname; password = 'Probe12345'; display_name = $uname; role = 'viewer' } | ConvertTo-Json -Compress)
Rec 'create_user_2xx' $create.status '2xx' ($create.status -ge 200 -and $create.status -lt 300)
$uid = $null; try { $uid = ($create.body | ConvertFrom-Json).id } catch {}
if ($uid) {
    $ulogin = Invoke-Probe 'POST' "$Base/api/v1/auth/login" $null (@{ username = $uname; password = 'Probe12345' } | ConvertTo-Json -Compress)
    $uTok = $null; try { $uTok = ($ulogin.body | ConvertFrom-Json).access_token } catch {}
    $uH = @{ Authorization = ("Bearer " + $uTok) }
    $before = Invoke-Probe 'GET' "$Base/api/v1/auth/me" $uH $null
    Rec 'user_me_before_200' $before.status 200 ($before.status -eq 200)
    $sus = Invoke-Probe 'POST' "$Base/api/v1/identity/lifecycle/user/$uid/suspend" $adminH '{"reason":"probe revocation immediacy"}'
    Rec 'suspend_2xx' $sus.status '2xx' ($sus.status -ge 200 -and $sus.status -lt 300)
    Start-Sleep -Seconds 1
    $after = Invoke-Probe 'GET' "$Base/api/v1/auth/me" $uH $null
    Rec 'revoked_old_token_401' $after.status 401 ($after.status -eq 401)
    Invoke-Probe 'POST' "$Base/api/v1/identity/lifecycle/user/$uid/deactivate" $adminH '{"confirm":true,"reason":"probe cleanup"}' | Out-Null
} else { $Results.create_user_body = $create.body }

# ---- §3 cross-repo forward chain ----
Write-Output "== §3 cross-repo forward chain =="
$rag = Invoke-Probe 'GET' "$Base/api/v1/rag-proxy/collections" $adminH $null
Rec 'rag_proxy_200' $rag.status 200 ($rag.status -eq 200)
$mem = Invoke-Probe 'GET' "$Base/api/v1/memory-proxy/memories" $adminH $null
Rec 'memory_proxy_200' $mem.status 200 ($mem.status -eq 200)

# ---- §4 A-write-B-read ----
if ($IncludeDataPlane) {
    Write-Output "== §4 cross-tenant A-write-B-read (rag-proxy collections) =="
    $tenants = Invoke-Probe 'GET' "$Base/api/v1/tenants" $adminH $null
    $tlist = @(); try { $tlist = $tenants.body | ConvertFrom-Json } catch {}
    $idOf = @{}
    foreach ($code in @($TenantA, $TenantB)) {
        $hit = $tlist | Where-Object { $_.code -eq $code } | Select-Object -First 1
        if (-not $hit) {
            $c = Invoke-Probe 'POST' "$Base/api/v1/tenants" $adminH (@{ name = ("probe-" + $code + "-" + $Stamp); code = $code } | ConvertTo-Json -Compress)
            Write-Output ("  create tenant {0} -> {1}" -f $code, $c.status)
            try { $hit = $c.body | ConvertFrom-Json } catch {}
        }
        if ($hit) { $idOf[$code] = $hit.id }
    }
    $tokOf = @{}; $uidOf = @{}
    foreach ($code in @($TenantA, $TenantB)) {
        $un = "probe_${code}_$Stamp"
        $u = Invoke-Probe 'POST' "$Base/api/v1/users" $adminH (@{ username = $un; password = 'Probe12345'; display_name = $un; role = 'admin'; tenant_id = $idOf[$code] } | ConvertTo-Json -Compress)
        try { $uidOf[$code] = ($u.body | ConvertFrom-Json).id } catch { $uidOf[$code] = $null }
        $l = Invoke-Probe 'POST' "$Base/api/v1/auth/login" $null (@{ username = $un; password = 'Probe12345' } | ConvertTo-Json -Compress)
        try { $tokOf[$code] = ($l.body | ConvertFrom-Json).access_token } catch { $tokOf[$code] = $null }
    }
    $colName = "probe-a-$Stamp"
    $cA = Invoke-Probe 'POST' "$Base/api/v1/rag-proxy/collections" @{ Authorization = ("Bearer " + $tokOf[$TenantA]) } (@{ name = $colName } | ConvertTo-Json -Compress)
    Rec 'A_write_collection_2xx' $cA.status '2xx' ($cA.status -ge 200 -and $cA.status -lt 300)
    $cAj = $null; try { $cAj = $cA.body | ConvertFrom-Json } catch {}
    $colIdA = $null
    foreach ($obj in @($cAj, $cAj.data)) {
        if ($obj) { foreach ($k in @('id', 'collection_id')) { if ($obj.PSObject.Properties.Name -contains $k) { $colIdA = $obj.$k; break } } }
        if ($colIdA) { break }
    }
    $listB = Invoke-Probe 'GET' "$Base/api/v1/rag-proxy/collections" @{ Authorization = ("Bearer " + $tokOf[$TenantB]) } $null
    $seenByB = $false
    try {
        $lb = $listB.body | ConvertFrom-Json
        $items = $lb; if ($lb.data) { $items = $lb.data }
        if ($items -isnot [array]) { $items = @($items) }
        $seenByB = [bool]($items | Where-Object { $_.name -eq $colName })
    } catch {}
    Rec 'B_cannot_see_A_collection' $seenByB $false (-not $seenByB)
    if ($colIdA) {
        $detB = Invoke-Probe 'GET' "$Base/api/v1/rag-proxy/collections/$colIdA" @{ Authorization = ("Bearer " + $tokOf[$TenantB]) } $null
        Rec 'B_direct_get_A_collection_denied' $detB.status '404/403' ($detB.status -eq 404 -or $detB.status -eq 403)
        Invoke-Probe 'DELETE' "$Base/api/v1/rag-proxy/collections/$colIdA" @{ Authorization = ("Bearer " + $tokOf[$TenantA]) } $null | Out-Null
    } else { $Results.A_collection_id_unresolved = $cA.body }
    foreach ($code in @($TenantA, $TenantB)) {
        if ($uidOf[$code]) { Invoke-Probe 'POST' "$Base/api/v1/identity/lifecycle/user/$($uidOf[$code])/deactivate" $adminH '{"confirm":true,"reason":"probe cleanup"}' | Out-Null }
    }
}

$pass = ($Results.Values | Where-Object { $_ -is [hashtable] -and $_.ContainsKey('pass') } | ForEach-Object { $_.pass }) -notcontains $false
$Results.overall_pass = $pass
$evi = Join-Path $OutDir ("realface-" + $Stamp + ".json")
$Results | ConvertTo-Json -Depth 8 | Set-Content $evi -Encoding UTF8
if ($StartServices) { Invoke-Managed -Action 'stop' }
Write-Output "== result =="
Write-Output ("overall_pass = {0}" -f $pass)
Write-Output ("evidence = {0}" -f $evi)
