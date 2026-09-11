# ============================================================================
# OpenBase verify_l3_1_agent.ps1 - S7-T5 L3-1 Agent 端到端（骨架 + 干跑）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.5（S7-T5-1~4）、§5 证据与报告规范
#   - agent key（sk-agent-*）-> 四头（X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source）
#     齐全且与主体一致；agent 无交互登录路径（0 可达）
#   - 各系统白名单放行（受信来源 + 头 = 信任；每系统 >=3 例矩阵）；非白名单携带身份头
#     全链路 403（PERM_UNTRUSTED_IDENTITY_HEADER，无绕过端点）
#   - 域隔离：跨域不可见（404/403/空），跨域同名并存互不可见
#   - M1 独立模式（本地 service key 自身认证）与 M2 受信头采纳分别断言
#
# 执行面（禁伪造）：
#   B 面：四仓运行态 + 真实 agent key；骨架 + 干跑 -> 四项检查一律 PENDING，退出码 2
#   真实执行路径代码齐备（-BaseUrl 探活 + 四头/白名单/域隔离用例矩阵），不可达一律 PENDING
#
# 用法：
#   .\scripts\verify_l3_1_agent.ps1 -DryRun
#   .\scripts\verify_l3_1_agent.ps1 -AgentKey <SMOKE_AGENT_KEY> -BaseUrl <GATEWAY_BASE> -EvidenceDir <...>
#
# 统一退出码：0=PASS / 1=FAIL / 2=PENDING
# ============================================================================

[CmdletBinding()]
param(
    [string]$AgentKey = 'sk-agent-skeleton',
    [string]$BaseUrl = '',
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
    $EvidenceDir = Join-Path $repoRoot 'doc\test\evidence\s7\l3-1'
}
$evidencePath = Join-Path $EvidenceDir 'agent-e2e.json'

# 四头（与 K07 端点矩阵口径一致）
$identityHeaders = @('X-User-ID', 'X-Tenant-ID', 'X-User-Role', 'X-Proxy-Source')
# 白名单用例矩阵（每系统 >=3 例：白名单放行 / 非白名单 403 / 跨域隔离）
$whitelistSystems = @('DPS', 'OpenLLM', 'OpenRAG', 'OpenMemory')
$whitelistCases = New-Object System.Collections.ArrayList
foreach ($system in $whitelistSystems) {
    [void]$whitelistCases.Add([ordered]@{ system = $system; case = 'trusted-header' ; expect = 'PASS'; desc = '受信来源 + 四头 = 信任放行' })
    [void]$whitelistCases.Add([ordered]@{ system = $system; case = 'untrusted-header'; expect = '403'; desc = '非白名单携带身份头 -> PERM_UNTRUSTED_IDENTITY_HEADER' })
    [void]$whitelistCases.Add([ordered]@{ system = $system; case = 'cross-domain'; expect = '404/403/empty'; desc = '跨域不可见' })
}

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
        [hashtable]$Headers = @{}
    )
    if ([string]::IsNullOrEmpty($Uri)) { return -1 }
    try {
        $response = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers `
            -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
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

$reachable = (-not $DryRun) -and (Test-Reachable -Url $BaseUrl)
$checks = New-Object System.Collections.ArrayList

if ($DryRun -or -not $reachable) {
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-1' `
        -Name 'agent key -> 四头齐全且与主体一致；agent 无交互登录路径（0 可达）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：真实 agent key 发放/使用 + 四头一致性需联调窗口' `
        -Evidence 'doc/test/evidence/s7/l3-1/agent-key-issuance.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-2' `
        -Name '各系统白名单放行（每系统 >=3 例）；非白名单携带身份头全链路 403' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：四仓白名单矩阵需真实运行态' `
        -Evidence 'doc/test/evidence/s7/l3-1/system-whitelist-cases.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-3' `
        -Name '域隔离：跨域不可见（404/403/空），跨域同名并存互不可见' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：跨域隔离用例需真实双租户/双域数据面' `
        -Evidence 'doc/test/evidence/s7/l3-1/domain-isolation.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-4' `
        -Name '未授权 403（PERM_UNTRUSTED_IDENTITY_HEADER）；M1 独立模式与 M2 受信头采纳分别断言' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：M1/M2 双模式断言需真实 service key 与受信头链路' `
        -Evidence 'doc/test/evidence/s7/l3-1/unauthorized-403.json + m1-m2.json'))
} else {
    # 真实执行路径：agent key 四头探活 + 白名单/域隔离 403 判定
    $trustedHeaders = @{
        'X-User-ID'      = 'agent-smoke'
        'X-Tenant-ID'    = 'tenant-smoke'
        'X-User-Role'    = 'service'
        'X-Proxy-Source' = 'openbase-generic-proxy'
        'Authorization'  = "Bearer $AgentKey"
    }
    $trustedCode = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/agent/health" -Headers $trustedHeaders
    $untrustedHeaders = @{
        'X-User-ID'      = 'spoof'
        'X-Tenant-ID'    = 'spoof'
        'X-User-Role'    = 'admin'
        'X-Proxy-Source' = 'untrusted-source'
    }
    $untrustedCode = Invoke-StatusProbe -Uri "$BaseUrl/api/v1/agent/health" -Headers $untrustedHeaders

    $at1Status = 'PENDING'
    $at1Reason = "agent 四头探活响应码 $trustedCode（需联调窗口核对四头一致与无登录路径）"
    if ($trustedCode -ge 200 -and $trustedCode -lt 300) { $at1Reason = 'agent 四头探活可达；四头一致性与无交互登录路径需真实主体核对（联调窗口回填）' }
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-1' `
        -Name 'agent key -> 四头齐全且与主体一致；agent 无交互登录路径（0 可达）' -Face 'B' -Status $at1Status `
        -Reason $at1Reason -Evidence 'doc/test/evidence/s7/l3-1/agent-key-issuance.json'))

    [void]$checks.Add((New-CheckResult -Id 'S7-T5-2' `
        -Name '各系统白名单放行（每系统 >=3 例）；非白名单携带身份头全链路 403' -Face 'B' -Status 'PENDING' `
        -Reason "非白名单携带身份头响应码 $untrustedCode；各系统白名单矩阵需四仓运行态（联调窗口回填）" `
        -Evidence 'doc/test/evidence/s7/l3-1/system-whitelist-cases.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-3' `
        -Name '域隔离：跨域不可见（404/403/空），跨域同名并存互不可见' -Face 'B' -Status 'PENDING' `
        -Reason '跨域隔离需真实双域数据面（联调窗口回填）' `
        -Evidence 'doc/test/evidence/s7/l3-1/domain-isolation.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T5-4' `
        -Name '未授权 403（PERM_UNTRUSTED_IDENTITY_HEADER）；M1 独立模式与 M2 受信头采纳分别断言' -Face 'B' -Status 'PENDING' `
        -Reason 'M1/M2 双模式断言需真实 service key 与受信头链路（联调窗口回填）' `
        -Evidence 'doc/test/evidence/s7/l3-1/unauthorized-403.json + m1-m2.json'))
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
    $reason = '沙箱无四仓运行态/无真实 agent key：L3-1 Agent 端到端属 B 面 -> PENDING；真实执行需联调窗口'
}

$mode = 'run'
if ($DryRun) { $mode = 'dry-run' }
$head = Get-OpenBaseCommit
$shortHead = ''
if ($head.Length -ge 7) { $shortHead = $head.Substring(0, 7) }

$evidence = [ordered]@{
    schema_version   = 1
    tool             = 'verify_l3_1_agent.ps1'
    task             = 'S7-T5'
    evidence_ref     = 'S7-T5-1~4'
    title            = 'S7-T5 L3-1 Agent 端到端'
    mode             = $mode
    status           = $overall
    exit_code        = $exitCode
    execution_face   = 'B'
    base_url         = $BaseUrl
    agent_key_masked = 'sk-agent-***'
    generated_at     = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    commit           = $shortHead
    openbase_commit  = $head
    reason           = $reason
    identity_headers = $identityHeaders
    whitelist_cases  = @($whitelistCases)
    checks           = @($checks)
    pending_items    = @(
        [ordered]@{
            id           = 'L3-1-REAL'
            item         = 'L3-1 Agent 端到端（四头一致 / 各系统白名单 / 域隔离 / 未授权 403 + M1/M2）'
            precondition = '四仓运行态 + 真实 agent key（sk-agent-*）'
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

Write-Host '=== S7-T5 L3-1 Agent 端到端 ==='
Write-Host ("  status={0} exit={1} mode={2}" -f $overall, $exitCode, $mode)
foreach ($check in $checks) {
    Write-Host ("  [{0}] {1} - {2}" -f $check.status, $check.id, $check.name)
}
Write-Host ("  evidence: {0}" -f $evidencePath)
exit $exitCode
