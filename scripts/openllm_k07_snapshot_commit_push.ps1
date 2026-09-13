<#
  openllm_k07_snapshot_commit_push.ps1 — OpenLLM K07 openapi 快照落仓（一次性提交与推送）
  ------------------------------------------------------------------
  背景：K07/SYS-1 终验以 OpenLLM 真实 `/openapi.json` 为准（278 路径 / 351 操作）；
        该快照此前未入库 → 无参 CI 无法离线校验，登记为 S7 遗留项
        （见 `doc/planning/OpenBase-S7-沙箱外执行单-v1.0.0.md` §5.4 遗留）。
  行为：
    1) 校验源快照为合法 OpenAPI 且 operations == $ExpectedOperations（默认 351）
    2) 字节级复制到 <OpenLLM>/backend/data/openapi-llm-snapshot.json
    3) 提交面守卫：仅暂存该 1 文件，多于 1 文件立即中止
    4) commit + push origin/backup/github + ls-remote 与本地 HEAD 校验
  使用：
        .\openllm_k07_snapshot_commit_push.ps1 -DryRun   # 干跑（不复制/不提交）
        .\openllm_k07_snapshot_commit_push.ps1           # 实跑
  说明：OpenLLM 仓在受限沙箱内不可写（`backend/data/**` 与 `.git` 均被拦截），
        请在可写环境执行本脚本；本脚本自身随 OpenBase 仓入库。
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'D:\Trae CN\myproject\Dev\OpenLLM',
    [string]$Source = 'd:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\gate\k07-openapi\openllm.openapi.json',
    [int]$ExpectedOperations = 351,
    [string]$Message = 'chore(k07): 落仓 OpenLLM /openapi.json 快照（351 操作，K07 无参 CI 依赖）',
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:GIT_TERMINAL_PROMPT = '0'
$env:GIT_OPTIONAL_LOCKS = '0'

$gitCandidates = @(
    'D:\Git\cmd\git.exe',
    (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
    'C:\Program Files\Git\cmd\git.exe',
    'C:\Program Files (x86)\Git\cmd\git.exe',
    (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe')
)
$GitExe = $null
foreach ($candidate in $gitCandidates) { if ($candidate -and (Test-Path $candidate)) { $GitExe = $candidate; break } }
if (-not $GitExe) { $GitExe = 'git' }
function Git { & $GitExe @args }

$RelativeTarget = 'backend/data/openapi-llm-snapshot.json'
$Target = Join-Path $RepoRoot ($RelativeTarget -replace '/', '\')
$Remotes = @('origin', 'backup', 'github')

function Write-Step([string]$Text) { Write-Host "`n== $Text" -ForegroundColor Cyan }
function Fail([string]$Text) { Write-Host "[ABORT] $Text" -ForegroundColor Red; exit 2 }

Write-Step '0) 前置检查'
Write-Host ("git      : {0}" -f $GitExe)
Write-Host ("仓库根   : {0}" -f $RepoRoot)
if (-not (Test-Path $RepoRoot)) { Fail "仓库根不存在：$RepoRoot" }
Write-Host ("源快照   : {0}" -f $Source)
Write-Host ("目标快照 : {0}" -f $Target)
$Branch = (Git -C $RepoRoot rev-parse --abbrev-ref HEAD).Trim()
Write-Host ("当前分支 : {0}" -f $Branch)
Write-Host ("远端     : {0}" -f ((Git -C $RepoRoot remote) -join ', '))

Write-Step '1) 源快照校验（合法 OpenAPI + operations 计数）'
if (-not (Test-Path $Source)) { Fail "源快照不存在：$Source" }
$spec = Get-Content -LiteralPath $Source -Raw -Encoding UTF8 | ConvertFrom-Json
$verbs = @('get', 'post', 'put', 'patch', 'delete')
$operations = 0
foreach ($pathItem in $spec.paths.PSObject.Properties) {
    foreach ($verb in $verbs) {
        if ($pathItem.Value.PSObject.Properties.Name -contains $verb) { $operations++ }
    }
}
Write-Host ("openapi={0} title={1} paths={2} operations={3}" -f $spec.openapi, $spec.info.title, $spec.paths.PSObject.Properties.Name.Count, $operations)
if ($operations -ne $ExpectedOperations) { Fail "operations 计数不符：期望 $ExpectedOperations，实测 $operations（源快照可能不是 K07 终验版本）" }
Write-Host ("[OK] 源快照校验通过（operations={0}）" -f $operations)

Write-Step '2) 目标状态比对'
$specHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
if (Test-Path $Target) {
    $targetHash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
    Write-Host ("已存在 ：sha256={0}" -f $targetHash.Substring(0, 16))
    Write-Host ("源快照 ：sha256={0}" -f $specHash.Substring(0, 16))
    if ($targetHash -eq $specHash) { Write-Host '[INFO] 目标与源一致（幂等：仍会走提交校验）' }
} else {
    Write-Host '[INFO] 目标尚不存在（首次落仓）'
}

if ($DryRun) {
    Write-Step '3) 干跑结束（未复制 / 未提交 / 未推送）'
    Write-Host ("计划：复制源快照 -> {0}" -f $Target)
    Write-Host ("计划：git add -- {0}（提交面守卫：仅 1 文件）" -f $RelativeTarget)
    Write-Host ("计划：commit -m `"{0}`"" -f $Message)
    Write-Host ("计划：push {0} {1} + ls-remote 校验" -f ($Remotes -join '/'), $Branch)
    exit 0
}

Write-Step '3) 复制源快照（字节级）'
Copy-Item -LiteralPath $Source -Destination $Target -Force
if (-not (Test-Path $Target)) { Fail "复制失败：$Target" }
$copiedHash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
if ($copiedHash -ne $specHash) { Fail '复制后哈希不一致（字节级校验失败）' }
Write-Host ("[OK] 已落仓 {0}（sha256={1}）" -f $Target, $copiedHash.Substring(0, 16))

Write-Step '4) 暂存 + 提交面守卫'
Git -C $RepoRoot add -- $RelativeTarget
$staged = @((Git -C $RepoRoot diff --cached --name-only) | Where-Object { $_ })
Write-Host ("暂存面：{0}" -f ($staged -join ', '))
if ($staged.Count -ne 1 -or $staged[0] -ne $RelativeTarget) {
    Fail "提交面守卫拦截：期望仅 [$RelativeTarget]，实测 [$($staged -join ', ')]"
}

$statusBefore = @((Git -C $RepoRoot diff --cached --name-status) | Where-Object { $_ })
if ($statusBefore.Count -eq 0) { Write-Host '[INFO] 无暂存改动（快照已入库且字节一致）→ 跳过提交' }
else {
    Write-Step '5) commit'
    Git -C $RepoRoot commit -m $Message
    if ($LASTEXITCODE -ne 0) { Fail 'commit 失败' }
    Git -C $RepoRoot log -n 1 --format='%h %s'
}

$LocalHead = (Git -C $RepoRoot rev-parse HEAD).Trim()
Write-Host ("local HEAD = {0}" -f $LocalHead)

Write-Step '6) push + 远端一致性校验'
foreach ($remote in $Remotes) {
    if (-not ((Git -C $RepoRoot remote) -contains $remote)) { Write-Host ("[skip] 远端不存在：{0}" -f $remote); continue }
    Git -C $RepoRoot push $remote "${Branch}:${Branch}"
    $remoteHead = ((Git -C $RepoRoot ls-remote --heads $remote $Branch) | Select-Object -First 1)
    if ($remoteHead) { $remoteHead = ($remoteHead -split '\s+')[0] } else { $remoteHead = '' }
    $verdict = 'MISMATCH'
    if ($remoteHead -eq $LocalHead) { $verdict = 'OK' }
    Write-Host ("{0,-8} {1}  [{2}]" -f $remote, $remoteHead, $verdict)
}

Write-Host "`n[DONE] OpenLLM K07 快照落仓流程结束（本地 HEAD=$LocalHead）。" -ForegroundColor Green
Write-Host "回填提示：请将提交 hash 与三远端一致性写入 OpenBase 执行单 §5.4 遗留与 k07-finalize.json。" -ForegroundColor Yellow
