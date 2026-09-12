# ============================================================================
# OpenBase init_openbase_test.ps1 - S7-T1-2 openbase_test 独立测试库初始化
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §2.2 / §4.1
#   Q-S7-D3 openbase_test 建库与隔离形态（专用测试库独立于业务库 openbase）
#   Q-S7-D4 K13 账号矩阵（openbase_app / platform_app / openbase_migrator /
#           openbase_runtime 四账号 NOSUPERUSER + 仅本 schema DML）
#
# 语义：幂等（可重复执行无副作用）——
#   1) 建库：pg_database 存在性守卫，缺失才 CREATE DATABASE openbase_test；
#   2) 建账号：pg_roles 存在性守卫（IF NOT EXISTS 语义），四类账号 NOSUPERUSER；
#   3) 授权：K13 收敛（仅授本 schema USAGE/DML；跨 schema 显式 REVOKE）；
#   4) 迁移：OPENBASE_DB_URL 指向 openbase_test，幂等迁移（create_all，IF NOT EXISTS 兜底）。
#
# 连接参数解析优先级：显式参数 > -EnvFile（默认仓根 .env.shared-infra） > 内置默认。
# 口令仅用于运行期连接，不落日志/不落报告明文；-DryRun 计划输出不含任何口令。
#
# 执行面：
#   A 面（沙箱可判定）：-DryRun 干跑（打印全部幂等语句计划，退出码 0）
#   B 面（联调窗口必需）：真实建库/建账号/授权/迁移（需真实 PG + 建库权限）
#     未执行一律登记 PENDING，禁伪造执行结果。
#
# 执行器：优先 psql 客户端；环境无 psql 时回退 psycopg2（项目既定测试栈依赖）。
#
# 用法：
#   .\scripts\db\init_openbase_test.ps1 -DryRun
#   .\scripts\db\init_openbase_test.ps1 -EnvFile .\.env.shared-infra
#   .\scripts\db\init_openbase_test.ps1 -AdminUrl 'postgresql://<admin>@192.168.0.151:5432/nuct'
#   .\scripts\db\init_openbase_test.ps1 -PgHost 192.168.0.151 -PgPort 5432 -AdminUser nuct -AdminPassword *** -AdminDb nuct
# ============================================================================

[CmdletBinding()]
param(
    [string]$DbName = 'openbase_test',
    [string]$EnvFile = '',
    [string]$PgHost = '',
    [int]$PgPort = 0,
    [string]$AdminUser = '',
    [string]$AdminPassword = '',
    [string]$AdminDb = '',
    [string]$AdminUrl = '',
    [string]$AppUser = 'openbase_app',
    [switch]$SkipMigrate,
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $EnvFile) { $EnvFile = Join-Path $RepoRoot '.env.shared-infra' }

# ---- .env 读取（仅取 KEY=VALUE，忽略注释/空行；口令只驻内存） ----
function Read-DotEnvFile {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $text = $line.Trim()
        if ($text -eq '' -or $text.StartsWith('#')) { continue }
        $separator = $text.IndexOf('=')
        if ($separator -lt 1) { continue }
        $key = $text.Substring(0, $separator).Trim()
        $value = $text.Substring($separator + 1).Trim()
        if ($key) { $map[$key] = $value }
    }
    return $map
}

$dotenv = Read-DotEnvFile -Path $EnvFile
if (-not $PgHost) {
    $PgHost = if ($dotenv.ContainsKey('POSTGRES_HOST') -and $dotenv['POSTGRES_HOST']) { $dotenv['POSTGRES_HOST'] } else { '127.0.0.1' }
}
if ($PgPort -le 0) {
    $PgPort = if ($dotenv.ContainsKey('POSTGRES_PORT') -and $dotenv['POSTGRES_PORT']) { [int]$dotenv['POSTGRES_PORT'] } else { 5432 }
}
if (-not $AdminUser) {
    $AdminUser = if ($dotenv.ContainsKey('POSTGRES_USER') -and $dotenv['POSTGRES_USER']) { $dotenv['POSTGRES_USER'] } else { 'postgres' }
}
if (-not $AdminPassword -and $dotenv.ContainsKey('POSTGRES_PASSWORD')) { $AdminPassword = $dotenv['POSTGRES_PASSWORD'] }
if (-not $AdminDb) {
    $AdminDb = if ($dotenv.ContainsKey('POSTGRES_DB') -and $dotenv['POSTGRES_DB']) { $dotenv['POSTGRES_DB'] } else { 'postgres' }
}

function New-PgUrl {
    param([string]$User, [string]$Password, [string]$HostName, [int]$Port, [string]$Database)
    $credential = $User
    if ($Password) { $credential = "$User" + ":" + [uri]::EscapeDataString($Password) }
    return "postgresql://$credential@${HostName}:$Port/$Database"
}

if (-not $AdminUrl) { $AdminUrl = New-PgUrl -User $AdminUser -Password $AdminPassword -HostName $PgHost -Port $PgPort -Database $AdminDb }
# 目标库管理员连接（建 schema/授权/迁移用；管理员凭据，不入报告）
$TestAdminUrl = New-PgUrl -User $AdminUser -Password $AdminPassword -HostName $PgHost -Port $PgPort -Database $DbName
# 测试库应用连接（运行时口径，隔离业务库 openbase）
$TestDbUrl = New-PgUrl -User $AppUser -Password '' -HostName $PgHost -Port $PgPort -Database $DbName
$TestAdminUrlForMigrate = $TestAdminUrl
$AdminUrlForReport = New-PgUrl -User $AdminUser -Password '' -HostName $PgHost -Port $PgPort -Database $AdminDb

# 幂等建家长语句计划（pg_roles 存在性守卫 + NOSUPERUSER 约束）
$roleNames = @('openbase_app', 'platform_app', 'openbase_migrator', 'openbase_runtime')
$createRoleSql = New-Object System.Collections.ArrayList
foreach ($role in $roleNames) {
    [void]$createRoleSql.Add("DO `$`$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$role') THEN CREATE ROLE $role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END `$`$;")
}
foreach ($role in $roleNames) {
    [void]$createRoleSql.Add("ALTER ROLE $role NOSUPERUSER NOCREATEDB NOCREATEROLE;")
}

# K13 授权（schema 级：仅本 schema USAGE/DML；跨 schema 显式 REVOKE）
$k13SchemaSql = @(
    "CREATE SCHEMA IF NOT EXISTS openbase;",
    "CREATE SCHEMA IF NOT EXISTS platform;",
    "REVOKE ALL ON SCHEMA platform FROM openbase_app, openbase_migrator, openbase_runtime;",
    "REVOKE ALL ON SCHEMA openbase FROM platform_app;",
    "GRANT USAGE ON SCHEMA openbase TO openbase_app, openbase_runtime, openbase_migrator;",
    "GRANT USAGE, CREATE ON SCHEMA openbase TO openbase_migrator;",
    "REVOKE CREATE ON SCHEMA openbase FROM openbase_app, openbase_runtime;",
    "GRANT USAGE ON SCHEMA platform TO platform_app;"
)

# K13 授权（表级：迁移后执行，覆盖已建表；IF NOT EXISTS 幂等）
$k13TableSql = @(
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA openbase TO openbase_app, openbase_runtime, openbase_migrator;",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA platform TO platform_app;"
)

$plan = New-Object System.Collections.ArrayList
[void]$plan.Add("-- [1/4] 建库（pg_database 守卫，幂等）")
[void]$plan.Add("CREATE DATABASE $DbName;  -- 仅当 pg_database 无同名库")
[void]$plan.Add("-- [2/4] 建账号（pg_roles 守卫，IF NOT EXISTS，NOSUPERUSER）+ K13 schema 授权")
$createRoleSql | ForEach-Object { [void]$plan.Add($_) }
$k13SchemaSql | ForEach-Object { [void]$plan.Add($_) }
[void]$plan.Add("-- [3/4] 导出测试连接（隔离业务库 openbase）")
[void]$plan.Add("OPENBASE_DB_URL=$TestDbUrl")
if (-not $SkipMigrate) {
    [void]$plan.Add("-- [4/4] 幂等迁移（create_all）+ 迁移后 K13 表级授权")
    [void]$plan.Add("-- 应用迁移器：init_database(engine, 'openbase')（create_all 幂等 + 内联 apply_identity_migration + 迁移后守卫 U1 身份 7 列）")
    $k13TableSql | ForEach-Object { [void]$plan.Add($_) }
}

Write-Host "[init_openbase_test] database=$DbName dry_run=$DryRun skip_migrate=$SkipMigrate"
Write-Host "[init_openbase_test] target=${PgHost}:$PgPort admin_db=$AdminDb admin_user=$AdminUser env_file=$EnvFile"
Write-Host "[init_openbase_test] admin_url=$AdminUrlForReport"
foreach ($statement in $plan) { Write-Host $statement }

# ---- 执行器：psql 优先，缺客户端回退 psycopg2（读取 SQL 文本执行） ----
$script:PsqlPath = (Get-Command psql -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
$script:PySqlRunner = @'
import sys
import psycopg2
url, path = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8-sig") as handle:
    script = handle.read()
conn = psycopg2.connect(url)
conn.autocommit = True
try:
    with conn.cursor() as cur:
        cur.execute(script)
finally:
    conn.close()
print("[psycopg2] sql applied")
'@

function Invoke-PgSql {
    param([string]$Url, [string[]]$SqlStatements, [string]$Label)
    $sqlText = $SqlStatements -join "`n"
    if ($script:PsqlPath) {
        $tmp = Join-Path $env:TEMP ("ob_init_{0}.sql" -f ([guid]::NewGuid().ToString('N')))
        Set-Content -LiteralPath $tmp -Value $sqlText -Encoding UTF8
        try {
            $sqlText | & $script:PsqlPath $Url -v ON_ERROR_STOP=1 -f - | Out-Host
            return $LASTEXITCODE
        } finally {
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        }
    }
    $tmp = Join-Path $env:TEMP ("ob_init_{0}.sql" -f ([guid]::NewGuid().ToString('N')))
    Set-Content -LiteralPath $tmp -Value $sqlText -Encoding UTF8
    try {
        # 输出经 Out-Host 落控制台，避免污染函数返回值（返回值仅退出码）
        $script:PySqlRunner | & python - $Url $tmp | Out-Host
        return $LASTEXITCODE
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}

# ---- 幂等建库（守卫在 Python 侧求值，CREATE DATABASE 不可在事务/DO 块内） ----
$script:PyCreateDbRunner = @'
import sys
import psycopg2
from psycopg2 import sql
url, dbname = sys.argv[1], sys.argv[2]
conn = psycopg2.connect(url)
conn.autocommit = True
try:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if cur.fetchone() is not None:
            print("[skip] database already exists: " + dbname)
        else:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
            print("[create] database created: " + dbname)
finally:
    conn.close()
'@

function New-PgDatabase {
    param([string]$Url, [string]$DbName)
    # 输出经 Out-Host 落控制台，避免污染函数返回值（返回值仅退出码）
    $script:PyCreateDbRunner | & python - $Url $DbName | Out-Host
    return $LASTEXITCODE
}

if ($DryRun) {
    Write-Host "[init_openbase_test] dry-run 完成：结构就绪（真实建库/授权/迁移属 B 面，登记 PENDING）"
    exit 0
}

if (-not $AdminUrl) {
    Write-Host "[init_openbase_test][ERROR] 未提供 -AdminUrl，且无法从 -EnvFile/参数解析管理员连接（沙箱受限）"
    exit 2
}

# ---- 真实执行（联调窗口） ----
$createDbExit = New-PgDatabase -Url $AdminUrl -DbName $DbName
if ($createDbExit -ne 0) { Write-Host "[init_openbase_test][ERROR] 建库失败（管理员连接不可用/无 CREATE DATABASE 权限）"; exit 2 }

$roleExit = Invoke-PgSql -Url $AdminUrl -SqlStatements $createRoleSql.ToArray() -Label 'create-roles'
if ($roleExit -ne 0) { Write-Host "[init_openbase_test][ERROR] 建账号失败（无 CREATE ROLE 权限）"; exit 2 }

$schemaExit = Invoke-PgSql -Url $TestAdminUrl -SqlStatements $k13SchemaSql -Label 'k13-schema'
if ($schemaExit -ne 0) { Write-Host "[init_openbase_test][ERROR] K13 schema 授权失败"; exit 2 }

$env:OPENBASE_DB_URL = $TestAdminUrlForMigrate
Write-Host "[init_openbase_test] OPENBASE_DB_URL=$TestDbUrl (运行时应用连接；迁移使用管理员连接)"

if (-not $SkipMigrate) {
    Push-Location $RepoRoot
    try {
        $script:PyMigrateRunner = @'
import asyncio
import os
import sys

from sqlalchemy import inspect

from openbase.core.db.session import init_db
from openbase.core.db.init import init_database

url = os.environ["OPENBASE_DB_URL"]
if url.startswith("postgresql://") and "+asyncpg" not in url:
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
engine = init_db(url)
# init_database 末尾已内联 apply_identity_migration（U1 身份幂等增量迁移）
asyncio.run(init_database(engine, "openbase"))
print("[migrate] openbase schema/tables ensured（含内联 apply_identity_migration）")

# 迁移链守卫（fail-loud）：U1 身份 7 列必须齐备，缺失即非零退出，避免漂移被静默放过
_REQUIRED_IDENTITY_COLUMNS = (
    "subject_type",
    "credential_type",
    "status_state",
    "status_reason",
    "token_version",
    "tenant_code",
    "on_behalf_of",
)


async def _users_columns():
    async with engine.begin() as conn:
        return await conn.run_sync(
            lambda sync_conn: {
                column["name"]
                for column in inspect(sync_conn).get_columns("users", schema="openbase")
            }
        )


_columns = asyncio.run(_users_columns())
_missing = [name for name in _REQUIRED_IDENTITY_COLUMNS if name not in _columns]
if _missing:
    print(f"[migrate][ERROR] U1 身份列缺失（初始化链漏迁移）: {_missing}")
    sys.exit(3)
print(f"[migrate] U1 identity columns verified: {len(_REQUIRED_IDENTITY_COLUMNS)}/{len(_REQUIRED_IDENTITY_COLUMNS)}")
'@
        $script:PyMigrateRunner | & python -
        if ($LASTEXITCODE -ne 0) { Write-Host "[init_openbase_test][ERROR] 迁移失败（create_all）"; exit 2 }
    } finally {
        Pop-Location
    }

    $tableExit = Invoke-PgSql -Url $TestAdminUrl -SqlStatements $k13TableSql -Label 'k13-table'
    if ($tableExit -ne 0) { Write-Host "[init_openbase_test][ERROR] K13 表级授权失败"; exit 2 }
}

Write-Host "[init_openbase_test] 完成（幂等，可重复执行）"
exit 0
