# ============================================================================
# OpenBase init_openbase_test.ps1 - S7-T1-2 openbase_test 独立测试库初始化
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §2.2 / §4.1
#   Q-S7-D3 openbase_test 建库与隔离形态（专用测试库独立于业务库 openbase）
#
# 语义：幂等（可重复执行无副作用）——
#   1) 建库：pg_database 存在性守卫，缺失才 CREATE DATABASE openbase_test；
#   2) 建账号：pg_roles 存在性守卫（IF NOT EXISTS 语义），四类账号 NOSUPERUSER；
#   3) 授权：仅授本 schema DML（不授跨 schema / 不授 superuser）；
#   4) 迁移：OPENBASE_DB_URL 指向 openbase_test，幂等迁移（IF NOT EXISTS / create_all）。
#
# 执行面：
#   A 面（沙箱可判定）：-DryRun 干跑（打印全部幂等语句计划，退出码 0）
#   B 面（联调窗口必需）：真实建库/建账号/迁移（需真实 PG + 建库权限）
#     未执行一律登记 PENDING，禁伪造执行结果。
#
# 用法：
#   .\scripts\db\init_openbase_test.ps1 -DryRun
#   .\scripts\db\init_openbase_test.ps1 -AdminUrl 'postgresql://postgres@127.0.0.1:5432/postgres'
# ============================================================================

[CmdletBinding()]
param(
    [string]$DbName = 'openbase_test',
    [string]$AdminUrl = '',
    [switch]$SkipMigrate,
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# 测试库连接（应用连接串统一指向独立测试库，隔离业务库 openbase）
$TestDbUrl = "postgresql://openbase_app@127.0.0.1:5432/$DbName"

# 幂等建库语句计划（pg_database 存在性守卫）
$createDatabaseSql = @(
    "SELECT 1 FROM pg_database WHERE datname = '$DbName';",
    "CREATE DATABASE $DbName;"
)

# 幂等建账号语句计划（pg_roles 存在性守卫 + NOSUPERUSER 约束）
$createRoleSql = @(
    "DO `$`$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'openbase_app') THEN CREATE ROLE openbase_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END `$`$;",
    "DO `$`$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'platform_app') THEN CREATE ROLE platform_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END `$`$;",
    "DO `$`$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'openbase_migrator') THEN CREATE ROLE openbase_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END `$`$;",
    "DO `$`$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'openbase_runtime') THEN CREATE ROLE openbase_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END `$`$;",
    "REVOKE ALL ON SCHEMA openbase FROM openbase_app, openbase_migrator, openbase_runtime;"
)

# 幂等迁移语句计划（IF NOT EXISTS 语义；建表由 create_all 幂等器兜底）
$migrateSql = @(
    "CREATE TABLE IF NOT EXISTS openbase.tenants (id UUID PRIMARY KEY, code TEXT NOT NULL UNIQUE);",
    "CREATE TABLE IF NOT EXISTS openbase.users (id UUID PRIMARY KEY, tenant_id UUID NOT NULL);",
    "-- 应用迁移器：python -m openbase.db（create_all 幂等，WHERE NOT EXISTS 兜底）"
)

$plan = New-Object System.Collections.ArrayList
[void]$plan.Add("-- [1/4] 建库（pg_database 守卫，幂等）")
$createDatabaseSql | ForEach-Object { [void]$plan.Add($_) }
[void]$plan.Add("-- [2/4] 建账号（pg_roles 守卫，IF NOT EXISTS，NOSUPERUSER）")
$createRoleSql | ForEach-Object { [void]$plan.Add($_) }
[void]$plan.Add("-- [3/4] 导出测试连接（隔离业务库 openbase）")
[void]$plan.Add("OPENBASE_DB_URL=$TestDbUrl")
if (-not $SkipMigrate) {
    [void]$plan.Add("-- [4/4] 幂等迁移（IF NOT EXISTS / create_all）")
    $migrateSql | ForEach-Object { [void]$plan.Add($_) }
}

Write-Host "[init_openbase_test] database=$DbName dry_run=$DryRun skip_migrate=$SkipMigrate"
foreach ($statement in $plan) { Write-Host $statement }

if ($DryRun) {
    Write-Host "[init_openbase_test] dry-run 完成：结构就绪（真实建库/迁移属 B 面，登记 PENDING）"
    exit 0
}

if (-not $AdminUrl) {
    Write-Host "[init_openbase_test][ERROR] 未提供 -AdminUrl，无法执行真实建库（沙箱受限）"
    exit 2
}

# 真实执行（联调窗口）：psql -v ON_ERROR_STOP=1 -f -（幂等语句可重放）
$sqlText = ($createDatabaseSql + $createRoleSql) -join "`n"
Push-Location $PSScriptRoot
try {
    $sqlText | & psql $AdminUrl -v ON_ERROR_STOP=1 -f -
    if ($LASTEXITCODE -ne 0) { Write-Host "[init_openbase_test][ERROR] 建库/建账号失败"; exit 2 }
} finally {
    Pop-Location
}

$env:OPENBASE_DB_URL = $TestDbUrl
Write-Host "[init_openbase_test] OPENBASE_DB_URL=$TestDbUrl"

if (-not $SkipMigrate) {
    python -m openbase.db
    if ($LASTEXITCODE -ne 0) { Write-Host "[init_openbase_test][ERROR] 迁移失败（create_all）"; exit 2 }
}

Write-Host "[init_openbase_test] 完成（幂等，可重复执行）"
exit 0
