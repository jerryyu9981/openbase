# ============================================================================
# OpenBase verify_l1_1_cascade.ps1 - S7-T2 L1-1 级联全链核验（真实面入口）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.2（S7-T2-1~4）、§5 证据与报告规范
#   - 停用主体 -> DPS/OpenMemory/OpenRAG 数据面阻断（403，数据保留）+ event_id 幂等
#   - Q-5=A：数据保留 + 全链访问阻断；restored 解除阻断；无自动 purge 路径
#   - purge 显式触发：非 deactivated -> 400；未二次授权 -> 403；授权后物理清除 + 审计留痕
#
# 执行面（禁伪造）：本脚本仅做参数转发，真实逻辑在 scripts/verify_l1_1_cascade.py
#   （真实 HTTP：lifecycle 迁移 + outbox 事件 + events/apply 消费 + blocked 阻断 + purge 负例/正例）。
#   purge 正例需 CLI 签发一次性授权码（DB 直连），受限执行面下该项保持 PENDING，不伪造 PASS。
#
# 断言编号映射：S7-T2-1（DPS 画像读阻断）/ S7-T2-2（OpenMemory 阻断 + 幂等）/
#   S7-T2-3（Q-5=A 保留 + restored 解除阻断）/ S7-T2-4（purge 显式触发 400/403/物理清除）
#
# 用法：
#   .\scripts\verify_l1_1_cascade.ps1 -DryRun
#   .\scripts\verify_l1_1_cascade.ps1 -BaseUrl http://127.0.0.1:8000
#   .\scripts\verify_l1_1_cascade.ps1 -BaseUrl http://127.0.0.1:8000 -EvidenceDir .\doc\test\evidence\s7\l1-1
#
# 统一退出码：0=PASS / 1=FAIL / 2=PENDING
# ============================================================================

[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$EvidenceDir = '',
    [string]$RepoRoot = '',
    [string]$PythonExe = 'python',
    # 骨架期兼容参数（真实运行器按 --subject-id 受控复用；缺省自动创建冒烟主体）
    [string]$SubjectId = '',
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($RepoRoot)) { $RepoRoot = Split-Path -Parent $scriptDir }
if ([string]::IsNullOrEmpty($EvidenceDir)) {
    $EvidenceDir = Join-Path $RepoRoot 'doc\test\evidence\s7\l1-1'
}

$runner = Join-Path $scriptDir 'verify_l1_1_cascade.py'
if (-not (Test-Path -Path $runner)) {
    Write-Host ("[ERROR] 未找到真实运行器: {0}" -f $runner)
    exit 2
}

$runnerArgs = @(
    $runner,
    '--base-url', $BaseUrl,
    '--evidence-dir', $EvidenceDir,
    '--repo-root', $RepoRoot,
    '--tool-name', 'verify_l1_1_cascade.ps1'
)
if (-not [string]::IsNullOrEmpty($SubjectId) -and $SubjectId -match '^\d+$') {
    $runnerArgs += @('--subject-id', $SubjectId)
}
if ($DryRun) { $runnerArgs += '--dry-run' }

& $PythonExe @runnerArgs
exit $LASTEXITCODE
