#!/usr/bin/env powershell
# OpenBase v1.1.0 Pro 环境部署脚本（TD-11-06，BL-111）
# 蓝绿/金丝雀部署 + 上线验证
# 用法: powershell -File scripts/deploy_pro.ps1 -Env pro -Strategy bluegreen

param(
    [string]$Env = "pro",
    [ValidateSet("bluegreen", "canary")][string]$Strategy = "bluegreen",
    [string]$Port = "8765",
    [string]$Version = "1.1.0"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== OpenBase Deploy [$Env] strategy=$Strategy version=$Version ==="

# 1. 环境变量校验（禁止默认密钥）
if (-not $env:OPENBASE_DB_URL) { throw "OPENBASE_DB_URL required (pro 环境必须显式注入)" }
if (-not $env:OPENBASE_JWT_SECRET -or $env:OPENBASE_JWT_SECRET -eq "change-me-in-production") {
    throw "OPENBASE_JWT_SECRET must be set (production secret)"
}

# 2. 版本确认（git tag）
git tag -l "v$Version"
if ($LASTEXITCODE -ne 0) { throw "git tag check failed" }

# 3. 启动服务（蓝绿：新实例 Green 端口）
$greenPort = [int]$Port + 1
Write-Host "--- Starting Green instance on port $greenPort ---"
$proc = Start-Process python -ArgumentList "-m", "uvicorn", "openbase.demo_app:app", "--host", "127.0.0.1", "--port", "$greenPort" -PassThru -WindowStyle Hidden
Write-Host "Green PID: $($proc.Id)"

# 4. 健康检查（最多 60s）
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$greenPort/health" -TimeoutSec 3
        if ($health.status -eq "ok") { $ready = $true; break }
    } catch { }
}
if (-not $ready) { throw "Green health check failed after 60s" }
Write-Host "Green health OK"

# 5. 上线验证（核心 API）
$login = Invoke-RestMethod -Uri "http://127.0.0.1:$greenPort/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'
if (-not $login.access_token) { throw "login verification failed" }
Write-Host "Green login OK (token length $($login.access_token.Length))"

# 6. 蓝绿切换说明（负载均衡流量切换由运维执行）
Write-Host ""
Write-Host "=== Deploy Ready ==="
Write-Host "Green instance running on port $greenPort (PID $($proc.Id))"
Write-Host "Traffic switch: LB/网关将流量切至 Green；异常时切回 Blue（<30s）"
Write-Host "Rollback: 停止 Green 进程 (Stop-Process -Id $($proc.Id))，流量切回 Blue"
Write-Host "Verify: 见 scripts/verify_release.py（上线验证 13 项）"
