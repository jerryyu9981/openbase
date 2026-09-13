#!/usr/bin/env powershell
# OpenBase v1.1.0 发布构建脚本（TD-11-05，BL-110 PyPI 发布）
# 用法: powershell -File scripts/build_release.ps1 [-Version 1.1.0] [-Publish]

param(
    [string]$Version = "1.1.0",
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== OpenBase Release Build v$Version ==="

# 1. 质量门禁
Write-Host "--- Quality gates ---"
python -m ruff check openbase tests
if ($LASTEXITCODE -ne 0) { throw "ruff check failed" }

python -m pytest tests -q --tb=short
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

python -m pytest tests -q --cov=openbase --cov-report=term | Select-String "TOTAL"
if ($LASTEXITCODE -ne 0) { throw "coverage run failed" }

# 2. 构建 sdist + wheel
Write-Host "--- Build ---"
python -m build
if ($LASTEXITCODE -ne 0) { throw "build failed" }

# 3. 校验版本号注入
$versions = Get-Content openbase/modules/versions.json -Raw | ConvertFrom-Json
Write-Host "modules versions.json OK ($($versions.modules.PSObject.Properties.Count) modules)"

# 4. 可选发布
if ($Publish) {
    Write-Host "--- Publish to PyPI ---"
    python -m twine upload dist/openbase-$Version*
    if ($LASTEXITCODE -ne 0) { throw "twine upload failed" }
}

Write-Host "=== Build complete: dist/openbase-$Version ==="
Get-ChildItem dist | Select-Object Name, Length
