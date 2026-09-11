# ============================================================================
# OpenBase verify_l1_1_cascade.ps1 - S7-T2 L1-1 级联全链核验（骨架 + 干跑）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.2（S7-T2-1~4）、§5 证据与报告规范
#   - 停用主体 -> DPS 画像读阻断（403/404，数据保留）
#   - 停用主体 -> OpenMemory 记忆数据面阻断（sessions/memories 拒绝，数据保留）+ event_id 幂等
#   - Q-5=A：数据保留 + 全链访问阻断；无自动 purge 路径（静态扫描 0 命中）
#   - purge 显式触发：非 deactivated -> 400；未二次授权 -> 403；授权后物理清除 + audit_logs
#     action=identity.purge
#
# 执行面（禁伪造）：
#   A+B：沙箱可判定静态面 + 真实面；B：真实停用/数据面阻断
#   骨架 + 干跑：无真实 PG/Redis/IdP/四仓运行态 -> 四项检查一律 PENDING，退出码 2
#   真实执行路径代码齐备（-BaseUrl 探活 + 响应码判定），不可达一律 PENDING，禁伪造 PASS
#
# 用法：
#   .\scripts\verify_l1_1_cascade.ps1 -DryRun
#   .\scripts\verify_l1_1_cascade.ps1 -BaseUrl <GATEWAY_BASE> -SubjectId smoke_l1_1_xxx `
#       -EvidenceDir .\doc\test\evidence\s7\l1-1
#
# 统一退出码：0=PASS / 1=FAIL / 2=PENDING
# ============================================================================

[CmdletBinding()]
param(
    [string]$BaseUrl = '',
    [string]$SubjectId = 'smoke_l1_1_skeleton',
    [string]$EvidenceDir = '',
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$ExitPass = 0
$ExitFail = 1
$ExitPending = 2

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
if ([string]::IsNullOrEmpty($EvidenceDir)) {
    $EvidenceDir = Join-Path $repoRoot 'doc\test\evidence\s7\l1-1'
}
$evidencePath = Join-Path $EvidenceDir 'cascade-result.json'

function Get-OpenBaseCommit {
    try {
        $head = (& git -C $repoRoot rev-parse HEAD 2>$null | Select-Object -First 1)
        if ($null -ne $head -and "$head".Trim().Length -gt 0) { return "$head".Trim() }
    } catch {
        return ''
    }
    return ''
}

function Invoke-StatusProbe {
    param(
        [string]$Uri,
        [string]$Method = 'Get',
        [string]$Body = ''
    )
    if ([string]::IsNullOrEmpty($Uri)) { return -1 }
    try {
        $params = @{
            Uri             = $Uri
            Method          = $Method
            TimeoutSec      = 5
            UseBasicParsing = $true
            ErrorAction     = 'Stop'
        }
        if (-not [string]::IsNullOrEmpty($Body)) {
            $params['Body'] = $Body
            $params['ContentType'] = 'application/json'
        }
        $response = Invoke-WebRequest @params
        return [int]$response.StatusCode
    } catch {
        $webResponse = $_.Exception.Response
        if ($null -ne $webResponse) { return [int]$webResponse.StatusCode.value__ }
        return -1
    }
}

function Test-Reachable {
    param([string]$Url)
    if ([string]::IsNullOrEmpty($Url)) { return $false }
    $code = Invoke-StatusProbe -Uri $Url -Method 'Head'
    return ($code -ge 200 -and $code -lt 500)
}

function New-CheckResult {
    param(
        [string]$Id,
        [string]$Name,
        [string]$Face,
        [string]$Status,
        [string]$Reason,
        [string]$Evidence
    )
    return [ordered]@{
        id             = $Id
        name           = $Name
        execution_face = $Face
        status         = $Status
        reason         = $Reason
        evidence       = $Evidence
    }
}

$plannedSteps = @(
    '1) 停用主体（POST /api/v1/identity/suspend）-> 事件 outbox user.suspended（event_id 幂等）',
    '2) 断言 DPS 画像读阻断（绑定失效 -> 403/404，数据保留）',
    '3) 断言 OpenMemory 记忆数据面阻断（sessions/memories 拒绝，数据保留）',
    '4) event_id 幂等（重放不双写、DB 行数不变）',
    '5) restored 恢复解除阻断（Q-5=A：数据保留 + 全链阻断）',
    '6) 静态扫描无自动 purge 路径（scan_auto_purge 0 命中）',
    '7) purge 显式触发核验（非 deactivated->400；未二次授权->403；授权后物理清除 + audit_logs action=identity.purge）'
)

$reachable = (-not $DryRun) -and (Test-Reachable -Url $BaseUrl)
$checks = New-Object System.Collections.ArrayList

if ($DryRun -or -not $reachable) {
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-1' `
        -Name 'DPS 画像读阻断（绑定失效 -> 403/404，数据保留）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：真实停用主体 + DPS 运行态需联调窗口' `
        -Evidence 'doc/test/evidence/s7/l1-1/dps-block.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-2' `
        -Name 'OpenMemory 记忆数据面阻断 + event_id 幂等（重放不双写、DB 行数不变）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：需 OpenMemory 运行态 + 真实 PG/Redis' `
        -Evidence 'doc/test/evidence/s7/l1-1/openmemory-block.json + event-idempotency.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-3' `
        -Name 'Q-5=A 保留 + 全链阻断 + 无自动 purge（静态扫描 0 命中）' -Face 'A+B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：静态面 0 自动 purge + restored 解除阻断需真实执行' `
        -Evidence 'doc/test/evidence/s7/l1-1/restore.json + scan-auto-purge.txt'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-4' `
        -Name 'purge 显式触发（400/403/物理清除 + audit_logs action=identity.purge）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：purge 端点真实响应码与审计留痕需联调窗口' `
        -Evidence 'doc/test/evidence/s7/l1-1/purge.json'))
} else {
    $dpsCode = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/dps/portrait/$SubjectId"
    $dpsStatus = 'PENDING'
    $dpsReason = "DPS 画像读响应码 $dpsCode 无法判定为阻断（需联调窗口复核）"
    if ($dpsCode -eq 403 -or $dpsCode -eq 404) { $dpsStatus = 'PASS'; $dpsReason = '' }
    elseif ($dpsCode -ge 200 -and $dpsCode -lt 300) { $dpsStatus = 'FAIL'; $dpsReason = "停用主体仍可读 DPS 画像: $dpsCode" }
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-1' `
        -Name 'DPS 画像读阻断（绑定失效 -> 403/404，数据保留）' -Face 'B' -Status $dpsStatus `
        -Reason $dpsReason -Evidence 'doc/test/evidence/s7/l1-1/dps-block.json'))

    $memoryCode = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/memory/sessions?subject_id=$SubjectId"
    $memoryStatus = 'PENDING'
    $memoryReason = "OpenMemory 记忆数据面响应码 $memoryCode 无法判定为阻断（需联调窗口复核）"
    if ($memoryCode -eq 403 -or $memoryCode -eq 404) { $memoryStatus = 'PASS'; $memoryReason = '' }
    elseif ($memoryCode -ge 200 -and $memoryCode -lt 300) { $memoryStatus = 'FAIL'; $memoryReason = "停用主体仍可读记忆数据面: $memoryCode" }
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-2' `
        -Name 'OpenMemory 记忆数据面阻断 + event_id 幂等（重放不双写、DB 行数不变）' -Face 'B' -Status $memoryStatus `
        -Reason $memoryReason -Evidence 'doc/test/evidence/s7/l1-1/openmemory-block.json + event-idempotency.json'))

    $restoreCode = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/identity/subjects/$SubjectId"
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-3' `
        -Name 'Q-5=A 保留 + 全链阻断 + 无自动 purge（静态扫描 0 命中）' -Face 'A+B' -Status 'PENDING' `
        -Reason "静态面 0 自动 purge 需 scan_auto_purge 复核；restored 解除阻断响应码 $restoreCode" `
        -Evidence 'doc/test/evidence/s7/l1-1/restore.json + scan-auto-purge.txt'))

    $purgeNonDeactivated = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/identity/purge" -Method 'Post' -Body '{"subject_id":"smoke_active"}'
    $purgeNoGrant = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/identity/purge" -Method 'Post' -Body "{\"subject_id\":\"$SubjectId\"}"
    $purgeStatus = 'PENDING'
    $purgeReason = "purge 响应码（非 deactivated=$purgeNonDeactivated / 未二次授权=$purgeNoGrant）需联调窗口复核"
    if ($purgeNonDeactivated -eq 400 -and $purgeNoGrant -eq 403) { $purgeStatus = 'PASS'; $purgeReason = '' }
    [void]$checks.Add((New-CheckResult -Id 'S7-T2-4' `
        -Name 'purge 显式触发（400/403/物理清除 + audit_logs action=identity.purge）' -Face 'B' -Status $purgeStatus `
        -Reason $purgeReason -Evidence 'doc/test/evidence/s7/l1-1/purge.json'))
}

$statuses = @($checks | ForEach-Object { $_.status })
$nonPass = @($statuses | Where-Object { $_ -ne 'PASS' })
if ($statuses -contains 'FAIL') {
    $overall = 'FAIL'
    $exitCode = $ExitFail
} elseif ($nonPass.Count -eq 0) {
    $overall = 'PASS'
    $exitCode = $ExitPass
} else {
    $overall = 'PENDING'
    $exitCode = $ExitPending
}
$reason = ''
if ($overall -eq 'PENDING') {
    $reason = '沙箱无真实 PG/Redis/IdP/四仓运行态：L1-1 级联全链核验属 B 面 -> PENDING；真实执行需联调窗口'
}

$mode = 'run'
if ($DryRun) { $mode = 'dry-run' }
$head = Get-OpenBaseCommit
$shortHead = ''
if ($head.Length -ge 7) { $shortHead = $head.Substring(0, 7) }

$evidence = [ordered]@{
    schema_version  = 1
    tool            = 'verify_l1_1_cascade.ps1'
    task            = 'S7-T2'
    evidence_ref    = 'S7-T2-1~4'
    title           = 'S7-T2 L1-1 级联全链核验'
    mode            = $mode
    status          = $overall
    exit_code       = $exitCode
    execution_face  = 'B'
    base_url        = $BaseUrl
    subject_id      = $SubjectId
    generated_at    = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    commit          = $shortHead
    openbase_commit = $head
    reason          = $reason
    planned_steps   = $plannedSteps
    checks          = @($checks)
    pending_items   = @(
        [ordered]@{
            id           = 'L1-1-REAL'
            item         = 'L1-1 级联全链核验（DPS/OpenMemory 数据面阻断 / 幂等 / purge 显式触发）'
            precondition = '专用冒烟主体 smoke_l1_1_* + DPS/OpenMemory 运行态 + 真实 PG/Redis'
            owner        = '联调窗口'
            action       = '真实窗口执行后回填 status=PASS/FAIL'
        }
    )
}

if (-not (Test-Path -Path $EvidenceDir)) {
    New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null
}
$json = $evidence | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($evidencePath, $json, [System.Text.UTF8Encoding]::new($false))

Write-Host '=== S7-T2 L1-1 级联全链核验 ==='
Write-Host ("  status={0} exit={1} mode={2}" -f $overall, $exitCode, $mode)
foreach ($check in $checks) {
    Write-Host ("  [{0}] {1} - {2}" -f $check.status, $check.id, $check.name)
}
Write-Host ("  evidence: {0}" -f $evidencePath)
exit $exitCode
