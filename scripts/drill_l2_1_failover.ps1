# ============================================================================
# OpenBase drill_l2_1_failover.ps1 - S7-T3 L2-1 主备切换演练（真实面入口）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.3（S7-T3-1~4）、§5 证据与报告规范
#   - B 断 -> A 接管（A 直连接管 + 降级告警产生，业务不中断）
#   - A 断 -> B 维持（B 编排维持，业务不中断）
#   - 单主路径：同一动作同一时刻仅一条主路径（禁双主双写）
#   - 演练报告字段齐备（场景/命令/切换前后路由/告警/回切条件/结论）
#   - 边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）
#
# 执行面（禁伪造）：本脚本仅做参数转发，真实逻辑在 scripts/drill_l2_1_failover.py，
#   驱动 OpenLLM 侧真实通道状态机 app.identity.channel.ChannelStateManager（S4-T7 落点）。
#
# 断言编号映射：S7-T3-1（B 断 -> A 接管）/ S7-T3-2（A 断 -> B 维持）/
#   S7-T3-3（单主路径禁双主双写）/ S7-T3-4（演练报告字段齐备）
#
# 用法：
#   .\scripts\drill_l2_1_failover.ps1 -DryRun
#   .\scripts\drill_l2_1_failover.ps1
#   .\scripts\drill_l2_1_failover.ps1 -OpenLlmBackend 'D:\Trae CN\myproject\Dev\OpenLLM\backend'
#
# 统一退出码：0=PASS / 1=FAIL / 2=PENDING
# ============================================================================

[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$EvidenceDir = '',
    [string]$RepoRoot = '',
    [string]$OpenLlmBackend = '',
    [string]$PythonExe = 'python',
    # 骨架期兼容参数（真实运行器覆盖双场景；此处仅承接传入不入参）
    [string]$Scenario = 'both',
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($RepoRoot)) { $RepoRoot = Split-Path -Parent $scriptDir }
if ([string]::IsNullOrEmpty($EvidenceDir)) {
    $EvidenceDir = Join-Path $RepoRoot 'doc\test\evidence\s7\l2-1'
}

$runner = Join-Path $scriptDir 'drill_l2_1_failover.py'
if (-not (Test-Path -Path $runner)) {
    Write-Host ("[ERROR] 未找到真实运行器: {0}" -f $runner)
    exit 2
}

$runnerArgs = @(
    $runner,
    '--evidence-dir', $EvidenceDir,
    '--repo-root', $RepoRoot,
    '--tool-name', 'drill_l2_1_failover.ps1'
)
if (-not [string]::IsNullOrEmpty($OpenLlmBackend)) {
    $runnerArgs += @('--openllm-backend', $OpenLlmBackend)
}
if ($DryRun) { $runnerArgs += '--dry-run' }

& $PythonExe @runnerArgs
exit $LASTEXITCODE
