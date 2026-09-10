#!/usr/bin/env powershell
# OpenBase v1.4.2 回归脚本（BL-142-10 TD-新增-009）
# 用法: powershell -File scripts/run_tests.ps1 [-WithCoverage]
#
# TD-新增-009 处置（脚本化回归执行）：
#  - tests/conftest.py：WindowsSelectorEventLoopPolicy（缓解 event loop 多线程崩溃）
#  - deps/auth.py：延迟导入打破循环导入
#  - pyproject.toml：pytest-asyncio module 级 loop 作用域
#  - 本脚本按文件分组（子进程隔离）执行全量测试，规避 Windows 上
#    starlette BaseHTTPMiddleware + anyio 多实例叠加的 C 层崩溃（单组不崩）。

param(
    [switch]$WithCoverage,
    # S7-T1-2：跨仓统一回归入口（默认单仓 openbase，保持 v1.4.2 行为不变）
    [string[]]$Repos = @('openbase'),
    [switch]$DryRun
)

# UTF-8 输出（PowerShell 5 中文编码）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Continue"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = Split-Path $scriptDir -Parent
Set-Location $root
Write-Host "root: $root"

# ---------------------------------------------------------------------------
# S7-T1-2 跨仓统一回归入口（Q-S7-D3）
#   默认 -Repos openbase = 下方单仓「按文件分组子进程隔离 + ruff」流程（行为不变）。
#   传入多仓 / 非 openbase / -DryRun 时进入跨仓编排（逐仓回归命令表）。
#   真实建库与跨仓实跑属 B 面（联调窗口）；沙箱内 -DryRun 干跑为可判定面。
# ---------------------------------------------------------------------------
# 兼容 -File 传参：单个参数内以逗号分隔的多仓（openbase,openllm）拆分为数组
    $Repos = @($Repos | ForEach-Object { $_ -split ',' } | Where-Object { $_ -ne '' })
    $isCrossRepo = $DryRun -or ($Repos.Count -gt 1) -or ($Repos[0] -ne 'openbase')
if ($isCrossRepo) {
    $siblingRoot = Split-Path $root -Parent
    $repoCommandTable = [ordered]@{
        openbase   = @{ Root = $root;                                  Commands = @('python -m ruff check openbase tests', 'python -m pytest tests') }
        openllm    = @{ Root = (Join-Path $siblingRoot 'OpenLLM\backend');    Commands = @('python -m pytest tests') }
        openrag    = @{ Root = (Join-Path $siblingRoot 'OpenRAG');            Commands = @('python -m pytest tests') }
        openmemory = @{ Root = (Join-Path $siblingRoot 'OpenMemory');         Commands = @('python -m pytest tests') }
        dps        = @{ Root = (Join-Path $siblingRoot 'DPS');                Commands = @('python -m pytest tests') }
    }
    Write-Host "=== S7-T1-2 跨仓统一回归入口（repos=$($Repos -join ',') dry_run=$DryRun）==="
    $pendingRepos = New-Object System.Collections.ArrayList
    $failedRepos = New-Object System.Collections.ArrayList
    foreach ($repoName in $Repos) {
        if (-not $repoCommandTable.Contains($repoName)) {
            Write-Host "[FAIL] 未知仓：$repoName"; exit 1
        }
        $entry = $repoCommandTable[$repoName]
        $present = Test-Path -LiteralPath $entry.Root
        Write-Host "--- repo: $repoName root=$($entry.Root) present=$present ---"
        foreach ($command in $entry.Commands) { Write-Host "    cmd: $command" }
        if ($DryRun -or -not $present) {
            # 干跑/仓不可达：仅输出计划（真实执行属 B 面，登记 PENDING）
            if (-not $present) { [void]$pendingRepos.Add($repoName) }
            continue
        }
        foreach ($command in $entry.Commands) {
            Push-Location $entry.Root
            try {
                Invoke-Expression $command
                if ($LASTEXITCODE -ne 0) { [void]$failedRepos.Add("$repoName :: $command") }
            } finally {
                Pop-Location
            }
        }
    }
    if ($pendingRepos.Count -gt 0) {
        Write-Host "[PENDING] 沙箱不可达仓（联调窗口执行）：$($pendingRepos -join ', ')"
    }
    if ($failedRepos.Count -gt 0) {
        Write-Host "[FAIL] 跨仓回归失败项："
        $failedRepos | ForEach-Object { Write-Host "  $_" }
        exit 1
    }
    Write-Host "[OK] 跨仓统一回归入口完成（dry-run 时仅为计划）"
    exit 0
}

# 静态检查
Write-Host "=== 1/3 ruff ==="
python -m ruff check openbase tests
if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] ruff"; exit 1 }
Write-Host "[OK] ruff"

# 测试文件分组（每组独立进程，规避组合崩溃）
$fileNames = @(Get-ChildItem -Path (Join-Path $root "tests") -Filter "test_*.py" -ErrorAction Stop | Sort-Object Name | ForEach-Object { $_.FullName })
$groups = New-Object System.Collections.ArrayList
for ($i = 0; $i -lt $fileNames.Count; $i += 6) {
    $end = [Math]::Min($i + 5, $fileNames.Count - 1)
    $slice = @($fileNames[$i..$end])
    [void]$groups.Add($slice)
}

Write-Host "=== 2/3 pytest（$($fileNames.Count) 文件 / $($groups.Count) 组，子进程隔离）==="
$totalPass = 0; $totalFail = 0; $totalSkip = 0; $failedItems = New-Object System.Collections.ArrayList
$covArgs = @()
if ($WithCoverage) { $covArgs = @("--cov=openbase", "--cov-report=term", "--cov-append") }

foreach ($group in $groups) {
    $label = ($group | ForEach-Object { Split-Path $_ -Leaf }) -join " "
    Write-Host "--- group: $label ---"
    $output = & python -m pytest @group -p no:cacheprovider @covArgs 2>&1
    $summary = $output | Select-String -Pattern '^\d+ (passed|failed)'
    Write-Host ($summary | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0) {
        $output | Select-String -Pattern '^FAILED ' | ForEach-Object { [void]$failedItems.Add($_.Line) }
    }
    $joined = $output -join "`n"
    $m = [regex]::Match($joined, '(\d+) failed')
    if ($m.Success) { $totalFail += [int]$m.Groups[1].Value }
    $m = [regex]::Match($joined, '(\d+) passed')
    if ($m.Success) { $totalPass += [int]$m.Groups[1].Value }
    $m = [regex]::Match($joined, '(\d+) skipped')
    if ($m.Success) { $totalSkip += [int]$m.Groups[1].Value }
}

Write-Host "=== 3/3 汇总 ==="
Write-Host "passed=$totalPass failed=$totalFail skipped=$totalSkip"
if ($failedItems.Count -gt 0) {
    Write-Host "[FAIL] 失败项："
    $failedItems | ForEach-Object { Write-Host "  $_" }
    exit 1
}
Write-Host "[OK] 全量回归通过（TD-新增-009 脚本化回归）"
