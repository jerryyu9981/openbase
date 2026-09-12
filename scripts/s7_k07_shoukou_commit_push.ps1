<#
  s7_k07_shoukou_commit_push.ps1 — OpenBase S7 K07 门禁收口回填一次性提交与推送
  ------------------------------------------------------------------
  背景：S7-T6-4 K07/SYS-1 门禁收口（2026-09-12）——DPS 35 条豁免续期至 2026-12-31
        且两仓补填提交 hash 实证 → gate_verdict PARTIAL→PASS；门禁聚合复跑
        overall=PASS exit=0 pass=20 fail=0 pending=2；本批回填证据与四份文档。
  兼容性：不依赖 PATH——git.exe 自动探测常见绝对路径，探测失败才回退命令名；
          由同级 .bat 用绝对路径调用 powershell.exe。
  范围：仅提交本批 K07 收口回填的 10 个文件（证据 2 + 文档 4 + 断言测试 2 + 本脚本 2）；
        不进入提交面：dogfood-output/**、storage/**、.env*、临时脚本。
  用法：
        .\scripts\s7_k07_shoukou_commit_push.ps1 -DryRun   # 干跑
        .\scripts\s7_k07_shoukou_commit_push.ps1          # 实跑
#>
[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:GIT_TERMINAL_PROMPT = '0'
$env:GIT_OPTIONAL_LOCKS  = '0'
try { $env:GIT_SSH_COMMAND = 'ssh -o BatchMode=yes -o ConnectTimeout=10' } catch { }

# ---- git 可执行文件解析（不依赖 PATH）----
$gitCandidates = @(
    'D:\Git\cmd\git.exe',
    (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
    'C:\Program Files\Git\cmd\git.exe',
    'C:\Program Files (x86)\Git\cmd\git.exe',
    (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe'),
    'C:\ProgramData\chocolatey\bin\git.exe',
    (Join-Path $env:USERPROFILE 'scoop\apps\git\current\cmd\git.exe')
)
$GitExe = $null
foreach ($c in $gitCandidates) { if ($c -and (Test-Path $c)) { $GitExe = $c; break } }
if (-not $GitExe) {
    $reg = 'HKLM:\SOFTWARE\GitForWindows'
    if (Test-Path $reg) {
        $ip = (Get-ItemProperty $reg -ErrorAction SilentlyContinue).InstallPath
        if ($ip) { $cand = Join-Path $ip 'cmd\git.exe'; if (Test-Path $cand) { $GitExe = $cand } }
    }
}
if (-not $GitExe) { $GitExe = 'git' }
function Git { & $GitExe @args }

$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Branch  = 'main'
$Message = 'docs(s7): K07 门禁收口与聚合复跑回填（DPS 35 条豁免续期 + 缺口/未覆盖清零 -> gate verdict PASS；测试报告 v1.0.12 / 分派单 v1.0.8 / 执行单 v1.0.9 / 总收官报告 v1.0.8）'
$Remotes = @('origin', 'backup')
$Files   = @(
    'doc/test/evidence/s7/gate/gate-aggregate.json'
    'doc/test/evidence/s7/gate/k07-finalize.json'
    'doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md'
    'doc/planning/OpenBase-S7-冒烟缺陷分派待办单-v1.0.0.md'
    'doc/planning/OpenBase-S7-沙箱外执行单-v1.0.0.md'
    'doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md'
    'tests/test_s7_t7_signoff.py'
    'tests/test_s7_t8_writeback.py'
    'scripts/s7_k07_shoukou_commit_push.ps1'
    's7-k07-shoukou-commit-push.bat'
)

function Write-Step([string]$Text) { Write-Host "`n== $Text" -ForegroundColor Cyan }

Write-Step '0) 前置检查'
Write-Host ("git         : {0}" -f $GitExe)
Write-Host ("仓根        : {0}" -f $RepoRoot)
Write-Host ("当前分支    : {0}" -f (Git rev-parse --abbrev-ref HEAD))
Write-Host ("当前 HEAD   : {0}" -f (Git rev-parse --short HEAD))

$missing = @()
foreach ($f in $Files) { if (-not (Test-Path (Join-Path $RepoRoot $f))) { $missing += $f } }
if ($missing.Count -gt 0) {
    Write-Host '以下待提交文件缺失，已中止：' -ForegroundColor Red
    $missing | ForEach-Object { Write-Host ("  - {0}" -f $_) }
    exit 1
}
Write-Host ("待提交文件  : {0} 项（全部存在）" -f $Files.Count) -ForegroundColor Green

Write-Step '1) 收口结论自检（证据 JSON 判定）'
$gatePath = Join-Path $RepoRoot 'doc/test/evidence/s7/gate/gate-aggregate.json'
$finPath  = Join-Path $RepoRoot 'doc/test/evidence/s7/gate/k07-finalize.json'
$gate = Get-Content -LiteralPath $gatePath -Raw -Encoding UTF8 | ConvertFrom-Json
$fin  = Get-Content -LiteralPath $finPath  -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ("gate-aggregate.overall_status = {0}（应为 PASS）" -f $gate.overall_status)
Write-Host ("gate-aggregate.exit_code      = {0}（应为 0）" -f $gate.exit_code)
$k07 = $gate.sections | Where-Object { $_.id -eq 'K07-SYS-1' }
Write-Host ("K07-SYS-1.status              = {0}（应为 PASS）" -f $k07.status)
Write-Host ("k07-finalize.gate_verdict     = {0}（应为 PASS）" -f $fin.gate_verdict)
if ($gate.overall_status -ne 'PASS' -or $gate.exit_code -ne 0 -or $k07.status -ne 'PASS' -or $fin.gate_verdict -ne 'PASS') {
    Write-Host '收口结论自检未通过，已中止（勿提交未收口内容）。' -ForegroundColor Red
    exit 1
}

Write-Step '2) git add（逐项显式，禁用 -A；dogfood-output/ 不入提交面）'
if ($DryRun) {
    Write-Host ('将执行: git add -- ' + ($Files -join ' ')) -ForegroundColor Yellow
} else {
    Git add -- @Files
    if ($LASTEXITCODE -ne 0) { Write-Host 'git add 失败，已中止（勿伪造结果）' -ForegroundColor Red; exit 1 }
    Git diff --cached --name-only
}

Write-Step '3) git commit'
Write-Host ("message: {0}" -f $Message)
if ($DryRun) {
    Write-Host '将执行: git commit -m <message>' -ForegroundColor Yellow
} else {
    Git commit -m $Message
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'git commit 失败或无需提交（请检查是否已提交过），已中止。' -ForegroundColor Red
        exit 1
    }
    Write-Host ("新提交: {0}" -f (Git rev-parse --short HEAD)) -ForegroundColor Green
}

Write-Step '4) git push（origin / backup）'
foreach ($r in $Remotes) {
    if ($DryRun) {
        Write-Host ("将执行: git push {0} {1}" -f $r, $Branch) -ForegroundColor Yellow
    } else {
        Write-Host ("-- push {0}" -f $r)
        Git push $r $Branch
        Write-Host ("   exit={0}" -f $LASTEXITCODE)
    }
}

Write-Step '5) 远端校验（ls-remote 与本地 HEAD 比对）'
if (-not $DryRun) {
    $local = (Git rev-parse HEAD)
    foreach ($r in $Remotes) {
        $ls = @(Git ls-remote --heads $r $Branch 2>$null)
        $remoteHash = if ($ls.Count -gt 0) { ($ls[0] -split '\s+')[0] } else { '(未找到/不可达)' }
        $statusTag = if ($remoteHash -eq $local) { 'OK' } else { 'MISMATCH' }
        Write-Host ("{0,-8} {1}  [{2}]" -f $r, $remoteHash, $statusTag)
    }
}

Write-Step '6) 回填信息（请复制给 OpenBase 侧台账）'
if (-not $DryRun) {
    Write-Host '--------------------------------------------------------'
    Write-Host 'repo            = OpenBase'
    Write-Host ("branch          = {0}" -f $Branch)
    Write-Host ("commit_hash     = {0}" -f (Git rev-parse HEAD))
    Write-Host ("commit_short    = {0}" -f (Git rev-parse --short HEAD))
    Write-Host ("files           = {0}" -f $Files.Count)
    Write-Host 'k07_verdict     = PASS (gap 0 / uncovered 0 / exempt 59 valid)'
    Write-Host 'gate_aggregate  = overall=PASS exit=0 pass=20 fail=0 pending=2'
    Write-Host '--------------------------------------------------------'
}
Write-Host "`n完成。" -ForegroundColor Green
