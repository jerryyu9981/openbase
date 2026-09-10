# ============================================================================
# OpenBase verify_env_global.ps1 - S7-T1-1 跨仓 verify-env 全局入口
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §2.2 / §4.1
#   Q-S7-D1 verify-env 全局契约落地形态（跨仓统一契约 + 单一全局入口）
#   Q-S7-D2 verify-env 两段式收紧（默认 WARN 非阻断 -> -FailFast/STRICT 强校验）
#
# 契约：scripts/verify-env/contract.global.json
#   - sections：以 OpenBase verify-env 6 组为主结构（非破坏性，contract.json 保留）
#   - repo_overrides：四仓契约键命名对齐（OpenLLM / OpenRAG / DPS / OpenMemory）
#
# 语义（两段式 + 回退）：
#   段 1（状态校验，默认）：WARN 非阻断；exit 0 = 干净 / 1 = 仅 WARN / 2 = 含 ERROR
#   段 2（强校验）：-FailFast 或 OPENBASE_VERIFY_ENV_STRICT=1 时启用强校验语义
#   回退开关：取消 -FailFast / 置 STRICT=0 即回到非阻断（脚本层可回滚）
#
# 执行面：
#   A 面（沙箱可判定）：契约结构对账 + -DryRun 干跑（逐仓编排计划 + 报告）
#   B 面（联调窗口必需）：逐仓真实探活（端口/上游/db）；未执行一律 PENDING，禁伪造
#
# 用法：
#   .\scripts\verify_env_global.ps1 -DryRun -SkipNetwork -SkipDb
#   .\scripts\verify_env_global.ps1 -Repos openbase,openllm -SkipNetwork -SkipDb
#   .\scripts\verify_env_global.ps1 -FailFast -OutputPath out/report.global.json
# ============================================================================

[CmdletBinding()]
param(
    [string[]]$Repos = @('openbase', 'openllm', 'openrag', 'openmemory', 'dps'),
    [string]$ContractPath = '',
    [string]$RepoRoot = '',
    [string]$OutputPath = '',
    [switch]$FailFast,
    [switch]$SkipNetwork,
    [switch]$SkipDb,
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not $ContractPath) { $ContractPath = Join-Path $PSScriptRoot 'verify-env\contract.global.json' }
if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }
if (-not $OutputPath) { $OutputPath = Join-Path $PSScriptRoot 'verify-env-report.global.json' }

# 两段式强校验开关（Q-S7-D2）：-FailFast 或 OPENBASE_VERIFY_ENV_STRICT=1
$strict = [bool]$FailFast -or ($env:OPENBASE_VERIFY_ENV_STRICT -eq '1')

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

$checkedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

# 主结构 6 组 + 四仓覆盖键（对齐目标）
$requiredSections = @(
    'config_single_source',
    'config_deprecated',
    'upstreams',
    'whitelist_matrix',
    'mapping_reconcile',
    'db_checks'
)
$requiredRepos = @('openbase', 'openllm', 'openrag', 'openmemory', 'dps')

# 各仓根目录（沙箱仅 OpenBase 存在；其余仓在联调窗口可达）
$parentRoot = Split-Path $RepoRoot -Parent
$repoRoots = @{
    'openbase'   = $RepoRoot
    'openllm'    = (Join-Path $parentRoot 'OpenLLM')
    'openrag'    = (Join-Path $parentRoot 'OpenRAG')
    'openmemory' = (Join-Path $parentRoot 'OpenMemory')
    'dps'        = (Join-Path $parentRoot 'DPS')
}

# --- 1. 加载全局契约 ---------------------------------------------------------
$contract = $null
if (-not (Test-Path -LiteralPath $ContractPath)) {
    Add-Issue 'ERROR' 'contract' 'GLOBAL_CONTRACT_MISSING' "global contract not found: $ContractPath"
} else {
    try {
        $contract = Get-Content -LiteralPath $ContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Add-Issue 'ERROR' 'contract' 'GLOBAL_CONTRACT_INVALID' "global contract parse failed: $($_.Exception.Message)"
    }
}

if ($null -eq $contract) {
    $reportContract = [pscustomobject]@{ path = $ContractPath; loaded = $false }
} else {
    $reportContract = [pscustomobject]@{
        path           = $ContractPath
        loaded         = $true
        schema_version = $contract.schema_version
    }
    # --- 2. 契约结构对账（6 组主结构 + 5 仓覆盖） ---------------------------
    foreach ($sectionName in $requiredSections) {
        if ($null -eq $contract.sections.PSObject.Properties[$sectionName]) {
            Add-Issue 'ERROR' 'contract' 'GLOBAL_SECTION_MISSING' "contract.sections missing: $sectionName"
        }
    }
    if ($null -eq $contract.repo_overrides) {
        Add-Issue 'ERROR' 'contract' 'GLOBAL_REPO_OVERRIDES_MISSING' 'contract.repo_overrides missing'
    } else {
        foreach ($repoName in $requiredRepos) {
            if ($null -eq $contract.repo_overrides.PSObject.Properties[$repoName]) {
                Add-Issue 'ERROR' 'contract' 'GLOBAL_REPO_OVERRIDE_MISSING' "contract.repo_overrides missing: $repoName"
            }
        }
    }
}

# --- 3. 逐仓编排（干跑 = 计划；真实 = 逐仓复用各仓 verify-env） -------------
$repoResults = New-Object System.Collections.ArrayList
if ($null -ne $contract) {
    foreach ($repoName in $Repos) {
        $root = $repoRoots[$repoName]
        $present = $false
        if ($root -and (Test-Path -LiteralPath $root)) { $present = $true }

        $childScript = ''
        if ($root) { $childScript = Join-Path $root 'scripts\verify-env.ps1' }
        $childArgs = @()
        if ($SkipNetwork) { $childArgs += '-SkipNetwork' }
        if ($SkipDb) { $childArgs += '-SkipDb' }
        $commandText = ''
        if ($childScript) {
            $commandText = ('powershell -File "{0}" {1}' -f $childScript, ($childArgs -join ' ')).Trim()
        }

        $entry = [pscustomobject]@{
            name    = $repoName
            root    = [string]$root
            present = [bool]$present
            status  = ''
            reason  = ''
            command = $commandText
        }

        if (-not $present) {
            $entry.status = 'PENDING'
            $entry.reason = 'repo not present in sandbox (B-face: execute at integration window)'
            if (-not $DryRun) {
                Add-Issue 'WARN' 'orchestrate' 'REPO_NOT_PRESENT' "repo $repoName not reachable at $root (structure ok; live probe pending)"
            }
            [void]$repoResults.Add($entry)
            continue
        }

        if ($DryRun) {
            $entry.status = 'PLANNED'
            $entry.reason = 'dry-run: structure validated, child verify-env not invoked'
            [void]$repoResults.Add($entry)
            continue
        }

        if (-not (Test-Path -LiteralPath $childScript)) {
            $entry.status = 'PENDING'
            $entry.reason = "child verify-env not found: $childScript"
            Add-Issue 'WARN' 'orchestrate' 'CHILD_VERIFY_ENV_MISSING' "repo $repoName child verify-env not found: $childScript"
            [void]$repoResults.Add($entry)
            continue
        }

        Push-Location $root
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $childScript @childArgs | Out-Null
            $childExit = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        if ($childExit -eq 0) {
            $entry.status = 'PASS'
        } elseif ($childExit -eq 1) {
            $entry.status = 'WARN'
            Add-Issue 'WARN' 'orchestrate' 'REPO_VERIFY_WARN' "repo $repoName verify-env returned warnings (exit=1)"
        } else {
            $entry.status = 'ERROR'
            Add-Issue 'ERROR' 'orchestrate' 'REPO_VERIFY_ERROR' "repo $repoName verify-env returned errors (exit=$childExit)"
        }
        [void]$repoResults.Add($entry)
    }
}

# --- 4. 报告 + 退出码（两段式） ---------------------------------------------
$warnings = @($script:Issues | Where-Object { $_.severity -eq 'WARN' }).Count
$errors = @($script:Issues | Where-Object { $_.severity -eq 'ERROR' }).Count
$exitCode = 0
if ($errors -gt 0) { $exitCode = 2 } elseif ($warnings -gt 0) { $exitCode = 1 }

$mode = 'live'
if ($DryRun) { $mode = 'dry-run' }

$report = [pscustomobject]@{
    schema_version  = 1
    checked_at      = $checkedAt
    mode            = $mode
    strict          = [bool]$strict
    contract        = $reportContract
    summary         = [pscustomobject]@{
        warnings  = $warnings
        errors    = $errors
        exit_code = $exitCode
        fail_fast = [bool]$FailFast
    }
    repos           = @($repoResults)
    issues          = @($script:Issues)
}

$reportDir = Split-Path -Parent $OutputPath
if ($reportDir) { New-Item -ItemType Directory -Force -Path $reportDir | Out-Null }
$report | ConvertTo-Json -Depth 12 | Out-File -LiteralPath $OutputPath -Encoding utf8

Write-Host "[verify-env-global] mode=$mode strict=$strict warnings=$warnings errors=$errors exit_code=$exitCode"
Write-Host "[verify-env-global] report: $OutputPath"
foreach ($repoResult in $repoResults) {
    Write-Host "[verify-env-global] repo=$($repoResult.name) status=$($repoResult.status) $($repoResult.reason)"
}

exit $exitCode
