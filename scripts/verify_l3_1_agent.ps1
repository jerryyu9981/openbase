# ============================================================================
# OpenBase verify_l3_1_agent.ps1 - S7-T5 L3-1 Agent 端到端（真实面入口）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §4.5（S7-T5-1~4）、§5 证据与报告规范
#   - agent key（sk-agent-*）-> 主体一致；agent 无交互登录路径；suspend 即时失效
#   - 各系统白名单矩阵（DPS/OpenLLM/OpenRAG/OpenMemory 各 >=3 例）；
#     非白名单携带身份头 -> 403 PERM_UNTRUSTED_IDENTITY_HEADER（全链 fail-closed）
#   - 域隔离：跨域不可见（需双域数据面预置，未预置时该项保持 PENDING）
#   - M1 独立模式（ob_k_* 服务密钥 /proxy 自身认证）与 M2 受信头采纳分别断言
#
# 执行面（禁伪造）：本脚本仅做参数转发，真实逻辑在 scripts/verify_l3_1_agent.py
#   （真实 HTTP：agent 签发 + 密钥认证 + 生命周期 + 白名单/非受信头矩阵 + M1/M2）。
#
# 依赖环境开关（OPENBASE_ 前缀，.env）：
#   OPENBASE_TRUSTED_PROXY_SOURCES / OPENBASE_ENFORCE_INBOUND_IDENTITY_HEADERS=true
#
# 断言编号映射：S7-T5-1（agent key 主体一致 + 无交互登录路径）/
#   S7-T5-2（各系统白名单矩阵 + 非白名单 403）/ S7-T5-3（域隔离）/ S7-T5-4（未授权 403 + M1/M2）
#
# 用法：
#   .\scripts\verify_l3_1_agent.ps1 -DryRun
#   .\scripts\verify_l3_1_agent.ps1 -BaseUrl http://127.0.0.1:8000
#
# 统一退出码：0=PASS / 1=FAIL / 2=PENDING
# ============================================================================

[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$EvidenceDir = '',
    [string]$RepoRoot = '',
    [string]$PythonExe = 'python',
    # 骨架期兼容参数（真实运行器自行签发 sk-agent-* 密钥；此处仅承接传入不入参）
    [string]$AgentKey = '',
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($RepoRoot)) { $RepoRoot = Split-Path -Parent $scriptDir }
if ([string]::IsNullOrEmpty($EvidenceDir)) {
    $EvidenceDir = Join-Path $RepoRoot 'doc\test\evidence\s7\l3-1'
}

$runner = Join-Path $scriptDir 'verify_l3_1_agent.py'
if (-not (Test-Path -Path $runner)) {
    Write-Host ("[ERROR] 未找到真实运行器: {0}" -f $runner)
    exit 2
}

$runnerArgs = @(
    $runner,
    '--base-url', $BaseUrl,
    '--evidence-dir', $EvidenceDir,
    '--repo-root', $RepoRoot,
    '--tool-name', 'verify_l3_1_agent.ps1'
)
if ($DryRun) { $runnerArgs += '--dry-run' }

& $PythonExe @runnerArgs
exit $LASTEXITCODE
