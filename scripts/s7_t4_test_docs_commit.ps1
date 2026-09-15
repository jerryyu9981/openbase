<#
.SYNOPSIS
  S7 批 7~9（联调窗口真实面 + T3 主备演练 + T2-4 purge 正例）提交助手（沙箱外执行）。

.DESCRIPTION
  沙箱内 git 无法写入 .git/objects（实测：`error: unable to write file .git/objects/...: Permission denied`），
  故本脚本一次性完成「显式暂存 → 本地提交」，**明确不推送**（如需推送加 -Push）。

  设计要点：
  - 仅显式列举提交面，**不使用 git add -A**，避免误纳 dogfood-output/、node_modules/、logs/、行尾噪音文件；
  - 支持 -DryRun 干跑校验路径清单（不写库）；
  - 提交后打印 hash 与提交面统计，便于回填测试报告/索引。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\s7_t4_test_docs_commit.ps1 -DryRun
  powershell -ExecutionPolicy Bypass -File scripts\s7_t4_test_docs_commit.ps1
#>
param(
    [switch]$DryRun,
    [switch]$Push
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$paths = @(
    'scripts/s7_t4_test_docs_commit.ps1',
    'openbase/modules/auth/api_keys.py',
    'openbase/modules/mcp/__init__.py',
    'openbase/modules/ai_apps/__init__.py',
    'tests/test_log_reserved_keys.py',
    'doc/test/OpenBase-S7-人工端到端测试日志落盘-测试报告-v1.0.0.md',
    'doc/test/OpenBase-S7-人工端到端测试日志落盘-测试用例-v1.0.0.md',
    'doc/audit/verification/OpenBase-S7-人工端到端测试日志落盘-测试回溯对比审计报告-v1.0.0.md',
    'doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0.md',
    'doc/design/OpenBase-文档地图索引-v1.0.0.md',
    'doc/planning/OpenBase-S7-沙箱外执行单-v1.0.0.md',
    'doc/test/evidence/manual',
    'doc/test/evidence/s7/l1-1/t4',
    'doc/test/evidence/s7/l2-1/t4',
    'doc/test/evidence/s7/l3-1/t4',
    'doc/test/evidence/s7/l2-2/matrix-finalize-t4.json',
    'doc/test/evidence/s7/l3-2/smoke-result-t4.json',
    'doc/test/evidence/s7/smoke/smoke-summary-t4.json',
    'doc/test/evidence/s7/smoke/smoke-summary-t4-noollama.json',
    'doc/test/evidence/s6/ui-e2e/results.json',
    'doc/test/evidence/s6/ui-e2e/results-s6-baseline-20260913.json'
)

if ($DryRun) {
    Write-Host '[DryRun] 校验提交面（不写对象库）...'
    git add --dry-run -- $paths
    Write-Host "[DryRun] exit=$LASTEXITCODE（0 = 路径清单全部有效）"
    exit $LASTEXITCODE
}

$message = @'
fix(logging): 修复 extra 保留键冲突（AD-20260914-02）+ S7-T2/T3 真实面闭环与 Step 4 测试文档

- 修复（P1 既有缺陷）：openbase/modules/auth/api_keys.py、mcp/__init__.py、ai_apps/__init__.py
  共 5 处 logger extra 使用 LogRecord 保留键 name → KeyError → POST /api/v1/auth/api-keys 500；
  改为 key_name / tool_name / server_name / app_name（3 文件 +5/-5）
- 回归（TDD）：新增 tests/test_log_reserved_keys.py（静态防复发扫描 + 端点 200 + 根因级 INFO 复现，4 例；先 RED 后 GREEN）
- Step 4 测试阶段交付：
  * 测试报告 v1.3.0（沙箱面 96% 覆盖率；联调窗口真实面：7 服务 checkall 27 PASS、冒烟 S0-S6 25/2/5、
    T2-1~4 全 PASS、T4-1 PASS、T5-1/2/4 PASS、真实人工 E2E 归因 3/3、前端 E2E 9/9；S7-T3 主备切换演练 T3-1~4 全 PASS
    + 停服窗口内真实上游中断注入）
  * 测试用例 v1.1.0（59 条 TT-LOGS）
  * 测试回溯对比审计报告 v1.3.0（设计→用例→证据回溯 100%、门禁独立复算、P1 缺陷闭环审计、观察项 O-1~O-10）
- 文档同步：DevLogReport v1.5.0（§17 缺陷修复记录）、S7 沙箱外执行单 v1.0.13（P2 面真实执行回填）、文档地图索引 v1.0.18
- 证据：doc/test/evidence/**（t4-*、run-20260914-2146*、run-l2-1-*、s7/l1-1|l2-1|l2-2|l3-1|l3-2 的 t4 证据）
- 纪律：未改动四仓任何文件；dogfood-output/ 与 node_modules/ 未纳入提交面；未执行推送
'@

$msgFile = Join-Path $env:TEMP 's7_t4_commit_msg.txt'
Set-Content -Path $msgFile -Value $message -Encoding UTF8

Write-Host '暂存中（显式路径面）...'
git add -- $paths
if ($LASTEXITCODE -ne 0) { Write-Error "git add 失败 exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host '提交中...'
git commit -F $msgFile
if ($LASTEXITCODE -ne 0) { Write-Error "git commit 失败 exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host '--- 提交结果 ---'
git log -1 --format='%h %s'
git show --stat --oneline HEAD | Select-Object -First 30

if ($Push) {
    Write-Host '推送 origin main ...'
    git push origin main
}
