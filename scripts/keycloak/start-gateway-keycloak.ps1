# 以真实 Keycloak（8080/realms/openbase）启动 OpenBase 网关（OB-AUTH-OIDC v1.5.0）
#
# 用法：powershell -ExecutionPolicy Bypass -File scripts/keycloak/start-gateway-keycloak.ps1
# 前置：Keycloak 已启动并配置 realm（start-keycloak.ps1 + provision_realm.py）
# 说明：以进程级环境变量覆盖 .env 默认（本地 IdP 8090/generic），不改 .env；
#       关闭后按 scripts/service-orchestrator.ps1 或 .env 默认（8090 generic）启动即回切。

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# 注入共享基础设施（.env.shared-infra：POSTGRES_URL/REDIS_URL → 绑定落库链路）
$envFile = Join-Path $Root '.env.shared-infra'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}

# OIDC 对接真实 Keycloak（覆盖 .env 默认）
$env:OPENBASE_OIDC_ENABLED = 'true'
$env:OPENBASE_OIDC_DISCOVERY_URL = 'http://127.0.0.1:8080/realms/openbase/.well-known/openid-configuration'
$env:OPENBASE_OIDC_CLIENT_ID = 'openbase-gw'
$env:OPENBASE_OIDC_CLIENT_SECRET = 'openbase-kc-secret-20260902'
$env:OPENBASE_OIDC_REDIRECT_URI = 'http://127.0.0.1:8000/api/v1/auth/oidc/callback'
$env:OPENBASE_OIDC_PROFILE = 'keycloak'

Write-Host '启动 OpenBase 网关（keycloak profile -> 8080/realms/openbase）...'
Set-Location $Root
python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000
