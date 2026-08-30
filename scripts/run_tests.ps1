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
    [switch]$WithCoverage
)

# UTF-8 输出（PowerShell 5 中文编码）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Continue"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = Split-Path $scriptDir -Parent
Set-Location $root
Write-Host "root: $root"

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
