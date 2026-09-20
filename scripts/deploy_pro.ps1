#!/usr/bin/env powershell
# OpenBase v1.1.0 Pro 环境部署脚本（TD-11-06，BL-111）
# 蓝绿/金丝雀部署 + 上线验证
# 用法: powershell -File scripts/deploy_pro.ps1 -Env pro -Strategy bluegreen

param(
    [string]$Env = "pro",
    [ValidateSet("bluegreen", "canary")][string]$Strategy = "bluegreen",
    [string]$Port = "8765",
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# 0. 版本解析（T4-1）：未显式传入时取项目版本载体 .devflow/project-config.json，避免默认值过期
if ([string]::IsNullOrWhiteSpace($Version)) {
    $configPath = Join-Path $PWD '.devflow/project-config.json'
    if (-not (Test-Path $configPath)) {
        throw "版本未指定且未找到 $configPath（请用 -Version 显式指定，例如 -Version 1.4.7）"
    }
    $Version = (Get-Content $configPath -Raw | ConvertFrom-Json).project.version
    Write-Host "[info] Version 未指定：取 project-config.json 的 project.version = $Version"
}

# 0.1 端口约束（T4-1）：$Port 为 Blue 端口，Green 自动取 $Port + 1；
#     须与 Pro 环境实际监听端口一致（Dev 默认 8000），部署前请显式确认。
Write-Host "[info] Port(Blue)=$Port  Green=$([int]$Port + 1)；请确认与 Pro 实际端口一致"

Write-Host "=== OpenBase Deploy [$Env] strategy=$Strategy version=$Version ==="

# 1. 环境变量校验（禁止默认/弱密钥；生产强校验与 settings env=production 一致，v1.7.0）
if (-not $env:OPENBASE_DB_URL) { throw "OPENBASE_DB_URL required (pro 环境必须显式注入)" }
$weakJwt = @("", "change-me-in-production", "test-jwt-secret-for-v680")
$secret = [string]$env:OPENBASE_JWT_SECRET
if ($weakJwt -contains $secret -or $secret.Length -lt 32) {
    throw "OPENBASE_JWT_SECRET 必须为 ≥32 字符强随机密钥（禁止空/占位/演示值）。生成：python scripts/gen_jwt_secret.py"
}
if ([string]::IsNullOrEmpty($env:OPENBASE_ENV)) {
    Write-Host "[warn] OPENBASE_ENV 未设置，默认 development；生产建议显式 OPENBASE_ENV=production（settings 将 fail-fast 拒绝弱密钥）"
}

# 2. 版本确认（git tag 存在性真校验：git tag -l 无匹配时仍返回 0，必须判空）
$tag = git tag -l "v$Version"
if (-not $tag) {
    throw "未找到 tag v$Version（发布标签缺失，禁止部署；请先创建并推送 tag）"
}
Write-Host "[ok] tag v$Version 存在"

# 2.1 Green 端口占用检查（避免复用旧实例导致验证假通过）
if (Get-NetTCPConnection -LocalPort ([int]$Port + 1) -State Listen -ErrorAction SilentlyContinue) {
    throw "Green 端口 $([int]$Port + 1) 已被占用，请先停止旧实例或改用其他 -Port"
}

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
Write-Host "Verify  : python scripts/verify_release.py --base-url http://127.0.0.1:$greenPort --expected-version $Version"
Write-Host "          （上线验证脚本，退出码 0 = 可切流；回滚后 15 分钟内须复跑）"
