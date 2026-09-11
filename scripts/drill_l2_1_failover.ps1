# ============================================================================
# OpenBase drill_l2_1_failover.ps1 - S7-T3 L2-1 主备切换演练（骨架 + 干跑）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.3（S7-T3-1~4）、§5 证据与报告规范
#   - B 断 -> A 接管（A 直连接管 + 降级头/告警产生，业务不中断）
#   - A 断 -> B 维持（B 编排维持，业务不中断）
#   - 单主路径：同一动作同一时刻仅一条主路径（S4-T7 ChannelStateManager），禁双主双写
#   - 演练报告：场景/命令/切换前后路由/降级头/告警/回切条件/结论齐备；切换显式触发
#   - 边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）
#
# 执行面（禁伪造）：
#   B 面：真实可注故障运行态 + 切换窗口；骨架 + 干跑 -> 四项检查一律 PENDING，退出码 2
#   真实执行路径代码齐备（-BaseUrl 探活 + 路由/降级头采集），不可达一律 PENDING，禁伪造 PASS
#
# 用法：
#   .\scripts\drill_l2_1_failover.ps1 -DryRun
#   .\scripts\drill_l2_1_failover.ps1 -Scenario b-down -BaseUrl <GATEWAY_BASE> -EvidenceDir <...>
#
# 统一退出码：0=PASS / 1=FAIL / 2=PENDING
# ============================================================================

[CmdletBinding()]
param(
    [ValidateSet('b-down', 'a-down', 'both')]
    [string]$Scenario = 'both',
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
    $EvidenceDir = Join-Path $repoRoot 'doc\test\evidence\s7\l2-1'
}
$evidencePath = Join-Path $EvidenceDir 'failover-drill.json'
$reportPath = Join-Path $EvidenceDir 'drill-report.md'

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
        [string]$Method = 'Get'
    )
    if ([string]::IsNullOrEmpty($Uri)) { return -1 }
    try {
        $response = Invoke-WebRequest -Uri $Uri -Method $Method -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
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

# 场景矩阵（双场景；事件通道不纳入，Q-S7-4）
$scenarioMatrix = @(
    [ordered]@{
        key           = 'b-down'
        label         = '场景 1：B 断 -> A 接管'
        route_before  = 'B 编排（主）'
        route_after   = 'A 直连接管（备转主）'
        degrade_header = 'X-Channel-Degrade: a-direct'
        alert         = 'channel.b.degraded'
        restore_condition = 'B /health 恢复 + 显式切回触发'
    },
    [ordered]@{
        key           = 'a-down'
        label         = '场景 2：A 断 -> B 维持'
        route_before  = 'B 编排（主）'
        route_after   = 'B 编排维持（A 备不可用）'
        degrade_header = 'X-Channel-Degrade: none'
        alert         = 'channel.a.unavailable'
        restore_condition = 'A /health 恢复 + 显式切回触发'
    }
)

$selected = @()
foreach ($item in $scenarioMatrix) {
    if ($Scenario -eq 'both' -or $Scenario -eq $item.key) { $selected += $item }
}

$plannedCommands = @()
foreach ($item in $selected) {
    $plannedCommands += ("pwsh -File scripts/drill_l2_1_failover.ps1 -Scenario {0} -BaseUrl <GATEWAY_BASE> -EvidenceDir <...> -DryRun" -f $item.key)
}

$reachable = (-not $DryRun) -and (Test-Reachable -Url $BaseUrl)
$checks = New-Object System.Collections.ArrayList

if ($DryRun -or -not $reachable) {
    [void]$checks.Add((New-CheckResult -Id 'S7-T3-1' `
        -Name 'B 断 -> A 接管（A 直连接管，降级头/告警产生，业务不中断）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：可注故障运行态 + 切换窗口需联调窗口' `
        -Evidence 'doc/test/evidence/s7/l2-1/drill-report.md（场景 1）+ route-after.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T3-2' `
        -Name 'A 断 -> B 维持（B 编排维持，业务不中断）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：可注故障运行态 + 切换窗口需联调窗口' `
        -Evidence 'doc/test/evidence/s7/l2-1/drill-report.md（场景 2）'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T3-3' `
        -Name '单主路径：同一动作同一时刻仅一条主路径，禁双主双写' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：ChannelStateManager 单主断言需真实运行态' `
        -Evidence 'doc/test/evidence/s7/l2-1/route-before.json + route-after.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T3-4' `
        -Name '演练报告字段齐备（场景/命令/路由/降级头/告警/回切条件/结论）' -Face 'B' -Status 'PENDING' `
        -Reason '干跑/环境不可达：真实切换前后路由/降级头/告警需联调窗口采集' `
        -Evidence 'doc/test/evidence/s7/l2-1/drill-report.md'))
} else {
    # 真实执行路径：采集切换前后路由与降级头（联调窗口受控注故障）
    $healthCode = Invoke-StatusProbe -Uri "$BaseUrl/health"
    foreach ($item in $selected) {
        $checkId = 'S7-T3-1'
        $name = 'B 断 -> A 接管（A 直连接管，降级头/告警产生，业务不中断）'
        if ($item.key -eq 'a-down') {
            $checkId = 'S7-T3-2'
            $name = 'A 断 -> B 维持（B 编排维持，业务不中断）'
        }
        $status = 'PENDING'
        $reason = ("场景 {0} 真实切换需注入故障并采集路由/降级头（health={1}）" -f $item.key, $healthCode)
        if ($healthCode -ge 200 -and $healthCode -lt 500) {
            $reason = ("受信通道可达；场景 {0} 需受控注故障后采集切换前后路由，联调窗口回填" -f $item.key)
        }
        [void]$checks.Add((New-CheckResult -Id $checkId -Name $name -Face 'B' -Status $status `
            -Reason $reason -Evidence 'doc/test/evidence/s7/l2-1/drill-report.md'))
    }
    [void]$checks.Add((New-CheckResult -Id 'S7-T3-3' `
        -Name '单主路径：同一动作同一时刻仅一条主路径，禁双主双写' -Face 'B' -Status 'PENDING' `
        -Reason '单主断言（ChannelStateManager）需真实切换窗口采样，联调窗口回填' `
        -Evidence 'doc/test/evidence/s7/l2-1/route-before.json + route-after.json'))
    [void]$checks.Add((New-CheckResult -Id 'S7-T3-4' `
        -Name '演练报告字段齐备（场景/命令/路由/降级头/告警/回切条件/结论）' -Face 'B' -Status 'PENDING' `
        -Reason '真实降级头/告警采集后写入演练报告 md' `
        -Evidence 'doc/test/evidence/s7/l2-1/drill-report.md'))
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
    $reason = '沙箱无可注故障运行态/无切换窗口：L2-1 主备切换演练属 B 面 -> PENDING；真实执行需联调窗口'
}

$mode = 'run'
if ($DryRun) { $mode = 'dry-run' }
$head = Get-OpenBaseCommit
$shortHead = ''
if ($head.Length -ge 7) { $shortHead = $head.Substring(0, 7) }

$evidence = [ordered]@{
    schema_version  = 1
    tool            = 'drill_l2_1_failover.ps1'
    task            = 'S7-T3'
    evidence_ref    = 'S7-T3-1~4'
    title           = 'S7-T3 L2-1 主备切换演练'
    mode            = $mode
    status          = $overall
    exit_code       = $exitCode
    execution_face  = 'B'
    base_url        = $BaseUrl
    scenario        = $Scenario
    generated_at    = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    commit          = $shortHead
    openbase_commit = $head
    reason          = $reason
    planned_commands = $plannedCommands
    scenario_matrix = $selected
    checks          = @($checks)
    pending_items   = @(
        [ordered]@{
            id           = 'L2-1-REAL'
            item         = 'L2-1 主备切换演练（B 断->A 接管 / A 断->B 维持 / 单主禁双写 / 报告）'
            precondition = '可注故障运行态（B 上游可停 / 端口可阻断）+ 切换窗口'
            owner        = '联调窗口'
            action       = '受控窗口执行后回填 status=PASS/FAIL 与演练报告 md'
        }
    )
}

if (-not (Test-Path -Path $EvidenceDir)) {
    New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null
}
$json = $evidence | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($evidencePath, $json, [System.Text.UTF8Encoding]::new($false))

# 演练报告模板（字段齐备：场景/命令/切换前后路由/降级头/告警/回切条件/结论）
$reportLines = New-Object System.Collections.ArrayList
[void]$reportLines.Add('# S7-T3 L2-1 主备切换演练报告')
[void]$reportLines.Add('')
[void]$reportLines.Add(('- 生成时间：{0}' -f (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')))
[void]$reportLines.Add(('- 模式：{0}；场景：{1}；结论：{2}' -f $mode, $Scenario, $overall))
[void]$reportLines.Add(('- OpenBase 提交：{0}' -f $head))
[void]$reportLines.Add('- 边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）')
[void]$reportLines.Add('')
[void]$reportLines.Add('| 场景 | 命令 | 切换前路由 | 切换后路由 | 降级头 | 告警 | 回切条件 | 结论 |')
[void]$reportLines.Add('|------|------|-----------|-----------|--------|------|---------|------|')
foreach ($item in $selected) {
    $command = ("-Scenario {0} -BaseUrl <GATEWAY_BASE> -DryRun" -f $item.key)
    [void]$reportLines.Add(('| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} |' -f `
        $item.label, $command, $item.route_before, $item.route_after, $item.degrade_header, `
        $item.alert, $item.restore_condition, $overall))
}
[void]$reportLines.Add('')
[void]$reportLines.Add('> 未真实执行项保持 PENDING；联调窗口执行后回填真实路由/降级头/告警并更新结论。')
$report = $reportLines -join "`n"
[System.IO.File]::WriteAllText($reportPath, $report, [System.Text.UTF8Encoding]::new($false))

Write-Host '=== S7-T3 L2-1 主备切换演练 ==='
Write-Host ("  status={0} exit={1} mode={2} scenario={3}" -f $overall, $exitCode, $mode, $Scenario)
foreach ($check in $checks) {
    Write-Host ("  [{0}] {1} - {2}" -f $check.status, $check.id, $check.name)
}
Write-Host ("  evidence: {0}" -f $evidencePath)
Write-Host ("  report:   {0}" -f $reportPath)
exit $exitCode
