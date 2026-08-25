# OpenBase 统一前端构建部署脚本（v1.2.0）
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root 'dist'
$ReleaseDir = Join-Path $Root 'dist-v1.2.0'

Write-Host '[1/3] 质量门禁：Lint 0 + 测试 100% + 覆盖率 >=80%'
Push-Location $Root
npm run lint
if ($LASTEXITCODE -ne 0) { throw 'Lint 失败' }
npm run test
if ($LASTEXITCODE -ne 0) { throw '单测失败' }
npm run test:coverage
if ($LASTEXITCODE -ne 0) { throw '覆盖率门禁失败' }

Write-Host '[2/3] 构建产物'
npm run build
if ($LASTEXITCODE -ne 0) { throw '构建失败' }

Write-Host '[3/3] 版本目录（保留上一版本用于回滚）'
if (Test-Path $ReleaseDir) { Remove-Item $ReleaseDir -Recurse -Force }
Copy-Item $Dist $ReleaseDir -Recurse
Pop-Location
Write-Host "构建完成：$ReleaseDir（nginx 切换 /ui 指向该目录即可发布/回滚）"
