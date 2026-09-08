# ============================================================================
# OpenBase verify-env.ps1 - environment self-check prototype (OB-9 / P2-1 T9)
#
# Contract:  scripts/verify-env/contract.json
#   config_single_source / config_deprecated / upstreams / whitelist_matrix /
#   mapping_reconcile / db_checks  (with tracking.contract_rail marker)
#
# Checks the live settings snapshot (collected by verify-env/snapshot.py)
# against the contract, and emits WARN/ERROR findings into a JSON report
# (default: scripts/verify-env-report.json) so failures are locatable.
#
# Findings (severity):
#   * missing config key / deprecated default configured / jwt weak /
#     upstream port unreachable / whitelist matrix mismatch / db check bit
#     down  -> WARN   (non-blocking prototype; full fail-fast semantics in R3)
#   * dps_code_map validation errors / unresolved conflicts -> ERROR
#     (mapping baseline gate, 0 unresolved required before S7)
#
# Exit codes:
#   0 = clean (no findings)
#   1 = warnings only (report carries details; run not blocked)
#   2 = errors present (baseline gate failed)
#   -FailFast aborts at the first finding: WARN -> 1, ERROR -> 2.
#
# Usage:
#   .\scripts\verify-env.ps1                                  # live snapshot
#   .\scripts\verify-env.ps1 -SnapshotPath snap.json         # offline check
#   .\scripts\verify-env.ps1 -FailFast -OutputPath out/report.json
#   .\scripts\verify-env.ps1 -SkipNetwork -SkipDb            # offline probe
# ============================================================================

[CmdletBinding()]
param(
    [string]$ContractPath = '',
    [string]$SnapshotPath = '',
    [string]$RepoRoot = '',
    [string]$OutputPath = '',
    [switch]$FailFast,
    [switch]$SkipNetwork,
    [switch]$SkipDb
)

$ProgressPreference = 'SilentlyContinue'
if (-not $ContractPath) { $ContractPath = Join-Path $PSScriptRoot 'verify-env\contract.json' }
if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }
if (-not $OutputPath) { $OutputPath = Join-Path $PSScriptRoot 'verify-env-report.json' }

$script:Issues = New-Object System.Collections.ArrayList

function Add-Issue {
    param(
        [Parameter(Mandatory = $true)][string]$Severity,
        [Parameter(Mandatory = $true)][string]$Section,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Message
    )
    [void]$script:Issues.Add([pscustomobject]@{
        severity = $Severity
        section  = $Section
        code     = $Code
        message  = $Message
    })
}

function ConvertTo-Array {
    param($Value)
    if ($null -eq $Value) { return }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        return @($Value)
    }
    return @($Value)
}

$checkedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

# --- 1. load contract -------------------------------------------------------
$contract = $null
if (-not (Test-Path -LiteralPath $ContractPath)) {
    Add-Issue 'ERROR' 'contract' 'CONTRACT_MISSING' "contract.json not found: $ContractPath"
} else {
    try {
        $contract = Get-Content -LiteralPath $ContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Add-Issue 'ERROR' 'contract' 'CONTRACT_INVALID' "contract.json parse failed: $($_.Exception.Message)"
    }
}
if ($null -eq $contract) {
    $reportContract = [pscustomobject]@{ path = $ContractPath; loaded = $false }
} else {
    $reportContract = [pscustomobject]@{ path = $ContractPath; loaded = $true; schema_version = $contract.schema_version }
}

# --- 2. load snapshot --------------------------------------------------------
$snapshot = $null
$snapshotSource = $SnapshotPath
$tempSnapshot = ''
if ($null -ne $contract) {
    if ($SnapshotPath) {
        if (-not (Test-Path -LiteralPath $SnapshotPath)) {
            Add-Issue 'ERROR' 'snapshot' 'SNAPSHOT_MISSING' "snapshot not found: $SnapshotPath"
        } else {
            try { $snapshot = Get-Content -LiteralPath $SnapshotPath -Raw -Encoding UTF8 | ConvertFrom-Json }
            catch { Add-Issue 'ERROR' 'snapshot' 'SNAPSHOT_INVALID' "snapshot parse failed: $($_.Exception.Message)" }
        }
    } else {
        $helper = Join-Path $PSScriptRoot 'verify-env\snapshot.py'
        $tempSnapshot = Join-Path ([System.IO.Path]::GetTempPath()) ('verify-env-snapshot-{0}.json' -f ([guid]::NewGuid().ToString('N')))
        $pyArgs = @($helper, '--out', $tempSnapshot)
        if ($SkipNetwork) { $pyArgs += '--skip-network' }
        if ($SkipDb) { $pyArgs += '--skip-db' }
        Push-Location $RepoRoot
        try {
            & python @pyArgs
            $pythonExit = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        if ($pythonExit -ne 0 -or -not (Test-Path -LiteralPath $tempSnapshot)) {
            Add-Issue 'ERROR' 'snapshot' 'SNAPSHOT_COLLECT_FAILED' "snapshot collection failed (exit=$pythonExit)"
        } else {
            $snapshotSource = $tempSnapshot
            try { $snapshot = Get-Content -LiteralPath $tempSnapshot -Raw -Encoding UTF8 | ConvertFrom-Json }
            catch { Add-Issue 'ERROR' 'snapshot' 'SNAPSHOT_INVALID' "snapshot parse failed: $($_.Exception.Message)" }
        }
    }
}
if ($tempSnapshot -and (Test-Path -LiteralPath $tempSnapshot)) {
    Remove-Item -LiteralPath $tempSnapshot -Force -ErrorAction SilentlyContinue
}

# --- helper: has-issue-stop check -------------------------------------------
$stop = $false
function Test-FailFastStop {
    if ($FailFast -and $script:Issues.Count -gt 0) { return $true }
    return $false
}

if ($null -ne $contract -and $null -ne $snapshot) {
    # --- 3. config_single_source presence ------------------------------------
    $singleSource = @(ConvertTo-Array $contract.sections.config_single_source)
    $deprecatedKeys = @(ConvertTo-Array $contract.sections.config_deprecated)
    foreach ($key in $singleSource) {
        if ($deprecatedKeys -contains $key) { continue }
        # jwt_secret is never dumped into snapshot (secret hygiene):
        # presence is covered by snapshot.jwt_secret_ok (check #5 below).
        if ($key -eq 'jwt_secret') { continue }
        $present = $false
        if ($null -ne $snapshot.config) {
            $present = $null -ne ($snapshot.config.PSObject.Properties[$key])
        }
        if (-not $present) {
            Add-Issue 'WARN' 'config_single_source' 'CONFIG_KEY_MISSING' "config key missing in settings snapshot: $key (contract config_single_source)"
            if (Test-FailFastStop) { $stop = $true; break }
        }
    }

    # --- 4. deprecated dps_default_* ------------------------------------------
    if (-not $stop) {
        $deprecatedConfigured = $snapshot.deprecated_configured
        if ($null -ne $deprecatedConfigured) {
            foreach ($prop in $deprecatedConfigured.PSObject.Properties) {
                $value = [string]$prop.Value
                if ($value -ne '') {
                    Add-Issue 'WARN' 'config_deprecated' 'DEPRECATED_KEY_USED' "dps_default_* deprecated (OB-8): $($prop.Name)=$value configured; register tenant code in dps_code_map instead"
                    if (Test-FailFastStop) { $stop = $true; break }
                }
            }
        }
    }

    # --- 5. jwt secret strength -------------------------------------------------
    if (-not $stop) {
        if ($null -ne $snapshot.PSObject.Properties['jwt_secret_ok'] -and -not [bool]$snapshot.jwt_secret_ok) {
            Add-Issue 'WARN' 'config_single_source' 'JWT_SECRET_WEAK' 'OPENBASE_JWT_SECRET is missing or weaker than 32 chars (signing fail-closed in production)'
            if (Test-FailFastStop) { $stop = $true }
        }
    }

    # --- 6. upstream reachability (WARN per port) ------------------------------
    if (-not $stop -and -not $SkipNetwork) {
        $reachability = $snapshot.upstreams_reachability
        if ($null -ne $reachability) {
            foreach ($prop in $reachability.PSObject.Properties) {
                if (-not [bool]$prop.Value) {
                    Add-Issue 'WARN' 'upstreams' 'UPSTREAM_UNREACHABLE' "upstream url_key=$($prop.Name) unreachable (settings $($prop.Name); TCP probe failed)"
                    if (Test-FailFastStop) { $stop = $true; break }
                }
            }
        }
    }

    # --- 7. whitelist matrix reconcile (trusted_proxy_sources) -----------------
    if (-not $stop) {
        $expectedWhite = @(@(ConvertTo-Array $contract.sections.whitelist_matrix.trusted_proxy_sources) | Sort-Object -Unique)
        $actualWhite = @(@(ConvertTo-Array $snapshot.trusted_proxy_sources_list) | Sort-Object -Unique)
        $diff = @(Compare-Object $expectedWhite $actualWhite)
        if ($diff.Count -gt 0) {
            $missing = @($diff | Where-Object { $_.SideIndicator -eq '<=' } | ForEach-Object { $_.InputObject }) -join ','
            $extra = @($diff | Where-Object { $_.SideIndicator -eq '=>' } | ForEach-Object { $_.InputObject }) -join ','
            Add-Issue 'WARN' 'whitelist_matrix' 'WHITELIST_MISMATCH' "trusted_proxy_sources mismatch vs contract: expected=[$($expectedWhite -join ',')] actual=[$($actualWhite -join ',')] (missing=[$missing] extra=[$extra])"
            if (Test-FailFastStop) { $stop = $true }
        }
    }

    # --- 8. dps_code_map mapping reconcile ---------------------------------------
    if (-not $stop) {
        $codeMap = $snapshot.dps_code_map
        if ($null -ne $codeMap) {
            $conflicts = @(ConvertTo-Array $codeMap.conflicts)
            foreach ($conflict in $conflicts) {
                $tenantCode = $conflict.tenant_code
                Add-Issue 'ERROR' 'mapping_reconcile' 'DPS_CODE_MAP_CONFLICT' "dps_code_map unresolved conflict: tenant_code=$tenantCode maps different dps org/tenant ids (0 unresolved required before S7)"
                if (Test-FailFastStop) { $stop = $true; break }
            }
            if (-not $stop) {
                $validationErrors = @(ConvertTo-Array $codeMap.validation_errors)
                foreach ($validationError in $validationErrors) {
                    Add-Issue 'ERROR' 'mapping_reconcile' 'DPS_CODE_MAP_INVALID' "dps_code_map validation error: $validationError"
                    if (Test-FailFastStop) { $stop = $true; break }
                }
            }
            if (-not $stop -and $codeMap.PSObject.Properties['known_tenant_codes_from_db'] -and
                -not [bool]$codeMap.known_tenant_codes_from_db) {
                Add-Issue 'WARN' 'mapping_reconcile' 'TENANT_CODES_SAMPLE_UNAVAILABLE' 'tenants.code sample unavailable (DB down); dps_code_map tenants.code hit check skipped - rerun with DB up or use --tenants-json offline reconcile'
                if (Test-FailFastStop) { $stop = $true }
            }
        }
    }

    # --- 9. db check bit -----------------------------------------------------------
    if (-not $stop -and -not $SkipDb) {
        $dbChecks = $snapshot.db_checks
        if ($null -ne $dbChecks -and $dbChecks.PSObject.Properties['probed'] -and [bool]$dbChecks.probed) {
            if (-not [bool]$dbChecks.reachable) {
                Add-Issue 'WARN' 'db_checks' 'DB_CHECK_UNREACHABLE' "db check bit down: schema=$($dbChecks.schema) unreachable (OB-7 connection/schema probe; tenants.code source_of_truth reconcile skipped)"
                if (Test-FailFastStop) { $stop = $true }
            }
        }
    }
}

# --- 10. report + exit code --------------------------------------------------------
$warnings = @($script:Issues | Where-Object { $_.severity -eq 'WARN' }).Count
$errors = @($script:Issues | Where-Object { $_.severity -eq 'ERROR' }).Count
$exitCode = 0
if ($errors -gt 0) { $exitCode = 2 } elseif ($warnings -gt 0) { $exitCode = 1 }

$report = [pscustomobject]@{
    schema_version = 1
    checked_at     = $checkedAt
    contract       = $reportContract
    snapshot_source = $snapshotSource
    summary        = [pscustomobject]@{ warnings = $warnings; errors = $errors; exit_code = $exitCode; fail_fast = [bool]$FailFast }
    issues         = @($script:Issues)
}

$reportDir = Split-Path -Parent $OutputPath
if ($reportDir) { New-Item -ItemType Directory -Force -Path $reportDir | Out-Null }
$reportJson = $report | ConvertTo-Json -Depth 12
$reportJson | Out-File -LiteralPath $OutputPath -Encoding utf8

Write-Host "[verify-env] warnings=$warnings errors=$errors exit_code=$exitCode (fail_fast=$FailFast)"
Write-Host "[verify-env] report: $OutputPath"
foreach ($issue in $script:Issues) {
    Write-Host "[verify-env] $($issue.severity) [$($issue.section)/$($issue.code)] $($issue.message)"
}

exit $exitCode
