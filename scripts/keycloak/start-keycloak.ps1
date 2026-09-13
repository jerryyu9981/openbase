# Keycloak 26.7.3 本地启动（真实 Keycloak realm 联调用，OB-AUTH-OIDC v1.5.0）
#
# 依赖：Java 17+（推荐 21，JAVA_HOME 已配置）；发行版已解压于 .runtime/keycloak-26.7.3/
# 用法：powershell -ExecutionPolicy Bypass -File scripts/keycloak/start-keycloak.ps1 [-Port 8080]
# 说明：dev 模式（h2 文件持久于发行版 data/），admin 账号 admin/admin 由 KC_BOOTSTRAP_ADMIN_* 预设；
#       首次启动约 30-60s（Quarkus 构建），就绪后执行 scripts/keycloak/provision_realm.py 配置 realm。
param(
    [int]$Port = 8080
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$KcHome = Join-Path $Root ".runtime\keycloak-26.7.3\keycloak-26.7.3"
$KcBat = Join-Path $KcHome "bin\kc.bat"

if (-not (Test-Path $KcBat)) {
    Write-Error "Keycloak 发行版未找到: $KcBat（先下载 keycloak-26.7.3.zip 解压到 .runtime/keycloak-26.7.3/）"
    exit 1
}

# kc.bat 依赖 findstr 等 System32 工具，确保 PATH 完整
$env:PATH = 'C:\Windows\System32;C:\Windows;' + $env:PATH
$env:KC_BOOTSTRAP_ADMIN_USERNAME = 'admin'
$env:KC_BOOTSTRAP_ADMIN_PASSWORD = 'admin'

Write-Host "启动 Keycloak（$KcHome）端口 $Port ..."
Push-Location $KcHome
try {
    & $KcBat start-dev "--http-port=$Port"
}
finally {
    Pop-Location
}
