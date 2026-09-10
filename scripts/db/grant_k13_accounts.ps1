# ============================================================================
# OpenBase grant_k13_accounts.ps1 - S7-T1-3 K13 存储账号权限分离（授权收敛）
#
# 设计依据：OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0 §2.2 / §4.1
#   Q-S7-D4 K13 账号矩阵文件与授权脚本落点
# 规则依据：OpenBase-数据隔离实现任务卡-v1.0.0 §K13（R-M3-1/2 -> OB-7）
#   账号矩阵文档：doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md
#
# 收敛口径：
#   1) openbase 应用账号与 platform（DPS 等）账号分离；
#   2) 各自仅授本 schema DML（跨 schema 写 0 成功路径，由 DB 级拒绝保证）；
#   3) 迁移账号与运行时账号分离（迁移账号 DDL / 运行时账号 DML）；
#   4) 不授 superuser（ALTER ROLE ... NOSUPERUSER）。
#
# 执行面：
#   A 面（沙箱可判定）：-DryRun 打印模式干跑（语句计划，退出码 0）
#   B 面（联调窗口必需）：真实授权 + 跨 schema 写拒绝验证（需真实 PG + 授权权限）
#     未执行一律登记 PENDING，禁伪造执行结果。
#
# 用法：
#   .\scripts\db\grant_k13_accounts.ps1 -DryRun
#   .\scripts\db\grant_k13_accounts.ps1 -AdminUrl 'postgresql://postgres@127.0.0.1:5432/postgres'
# ============================================================================

[CmdletBinding()]
param(
    [string]$AdminUrl = '',
    [switch]$DryRun
)

$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# schema x 账号 x 权限矩阵（与 K13 矩阵文档一致）
$accountMatrix = @(
    [pscustomobject]@{ Account = 'openbase_app';      Schema = 'openbase'; Role = '应用账号（运行时）'; Privilege = 'DML' },
    [pscustomobject]@{ Account = 'platform_app';      Schema = 'platform'; Role = 'platform/DPS 应用账号（运行时）'; Privilege = 'DML' },
    [pscustomobject]@{ Account = 'openbase_migrator'; Schema = 'openbase'; Role = '迁移账号'; Privilege = 'DDL+DML' },
    [pscustomobject]@{ Account = 'openbase_runtime';  Schema = 'openbase'; Role = '受限运行时账号'; Privilege = 'DML' }
)

# 授权收敛语句（仅本 schema；不授 superuser；跨 schema 显式 REVOKE）
$statements = New-Object System.Collections.ArrayList
[void]$statements.Add("ALTER ROLE openbase_app NOSUPERUSER;")
[void]$statements.Add("ALTER ROLE platform_app NOSUPERUSER;")
[void]$statements.Add("ALTER ROLE openbase_migrator NOSUPERUSER;")
[void]$statements.Add("ALTER ROLE openbase_runtime NOSUPERUSER;")
[void]$statements.Add("GRANT USAGE ON SCHEMA openbase TO openbase_app, openbase_runtime;")
[void]$statements.Add("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA openbase TO openbase_app, openbase_runtime;")
[void]$statements.Add("GRANT USAGE, CREATE ON SCHEMA openbase TO openbase_migrator;")
[void]$statements.Add("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA openbase TO openbase_migrator;")
[void]$statements.Add("GRANT USAGE ON SCHEMA platform TO platform_app;")
[void]$statements.Add("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA platform TO platform_app;")
# 跨 schema 写拒绝：显式 REVOKE（0 成功路径）
[void]$statements.Add("REVOKE ALL ON SCHEMA platform FROM openbase_app, openbase_migrator, openbase_runtime;")
[void]$statements.Add("REVOKE ALL ON SCHEMA openbase FROM platform_app;")
[void]$statements.Add("REVOKE CREATE ON SCHEMA openbase FROM openbase_app, openbase_runtime;")

Write-Host "[grant_k13_accounts] dry_run=$DryRun accounts=$($accountMatrix.Count)"
Write-Host "=== K13 账号矩阵（schema x 账号 x 权限）==="
foreach ($row in $accountMatrix) {
    Write-Host ("  {0} | schema={1} | role={2} | privilege={3}" -f $row.Account, $row.Schema, $row.Role, $row.Privilege)
}
Write-Host "=== 授权收敛语句 ==="
foreach ($statement in $statements) { Write-Host "  $statement" }

if ($DryRun) {
    Write-Host "[grant_k13_accounts] dry-run 完成：授权收敛语句就绪（真实授权/跨 schema 写拒绝属 B 面，登记 PENDING）"
    exit 0
}

if (-not $AdminUrl) {
    Write-Host "[grant_k13_accounts][ERROR] 未提供 -AdminUrl，无法执行真实授权（沙箱受限）"
    exit 2
}

$sqlText = $statements -join "`n"
$sqlText | & psql $AdminUrl -v ON_ERROR_STOP=1 -f -
if ($LASTEXITCODE -ne 0) { Write-Host "[grant_k13_accounts][ERROR] 授权执行失败"; exit 2 }

Write-Host "[grant_k13_accounts] 授权完成（仅本 schema DML，不授 superuser）"
exit 0
