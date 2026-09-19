# ============================================================================
# BL-147-05 端到端串联与接入验收（v1.4.7）— 可复跑的验收执行脚本
#
# 职责（对应《OpenBase-测试计划-v1.4.7》/《OpenBase-测试用例-v1.4.7》）：
#   TT-147-001 环境就绪核验（基础设施可达 + 四仓 R-384 改动就位 + 端口）
#   TT-147-002 采集命名契约实测（复用编排器 -Action namecheck）
#   TT-147-003 网关串联抽样（默认 4 族 × 6 次 = 24 次，逐次取响应头 X-Request-Id）
#   TT-147-004/005/006/007/010 由 scripts/bl147_05_verify_chain.py 完成
#
# 判据口径（2026-09-19 人工裁定）：JSON 合法率与串联比对**限定为四仓应用日志行**；
# uvicorn 等框架自身输出行不纳入（占比在证据中如实披露）。
#
# 用法：
#   .\scripts\bl147_05_e2e_check.ps1                 # 启动服务 → 抽样 → 校验（服务保留运行）
#   .\scripts\bl147_05_e2e_check.ps1 -SkipStart      # 服务已在运行，仅抽样与校验
#   .\scripts\bl147_05_e2e_check.ps1 -StopAfter      # 结束后停止服务
# ============================================================================

[CmdletBinding()]
param(
    [int]$PerFamily = 6,
    [int]$HealthTimeout = 600,
    [switch]$SkipStart,
    [switch]$StopAfter,
    [string]$EvidenceDir = 'doc\test\evidence\v147',
    [string]$Username = 'admin',
    [string]$Password = 'admin123'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$evi = Join-Path $root $EvidenceDir
New-Item -ItemType Directory -Force -Path $evi | Out-Null
$orchestrator = Join-Path $PSScriptRoot 'service-orchestrator.ps1'
$verifier = Join-Path $PSScriptRoot 'bl147_05_verify_chain.py'
$envEvidence = Join-Path $evi 'bl147-05-env.txt'
$samplingFile = Join-Path $evi 'bl147-05-sampling.json'
$namecheckFile = Join-Path $evi 'bl147-05-namecheck.txt'

function Write-Step {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Write-Host $line
    Add-Content -Path $envEvidence -Value $line -Encoding UTF8
}

$header = "=== BL-147-05 端到端串联验收环境核验（{0}）===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Set-Content -Path $envEvidence -Value $header -Encoding UTF8
$hostLine = "主机：$env:COMPUTERNAME；PowerShell：$($PSVersionTable.PSVersion)；Python：$(& python --version 2>&1)"
Add-Content -Path $envEvidence -Value $hostLine -Encoding UTF8

Write-Step 'TT-147-001 基础设施可达性预检（共享 PG / Redis / Qdrant）'
$infra = @(
    @{ Name = 'PostgreSQL'; Host = '192.168.0.151'; Port = 5432 },
    @{ Name = 'Redis';      Host = '192.168.0.151'; Port = 6380 },
    @{ Name = 'Qdrant';     Host = '192.168.0.151'; Port = 6333 }
)
foreach ($item in $infra) {
    $ok = Test-NetConnection -ComputerName $item.Host -Port $item.Port -InformationLevel Quiet -WarningAction SilentlyContinue
    "{0,-12} {1}:{2} = {3}" -f $item.Name, $item.Host, $item.Port, $ok | Add-Content -Path $envEvidence -Encoding UTF8
}

Write-Step 'TT-147-001 四仓 R-384 改动就位核验（工作树装配点计数）'
$wiring = @(
    @{ Repo = 'DPS';        File = 'D:\Trae CN\myproject\Dev\DPS\src\rest_api\app.py';                          Pattern = 'setup_dps_logging' },
    @{ Repo = 'OpenLLM';    File = 'D:\Trae CN\myproject\Dev\OpenLLM\backend\main.py';                          Pattern = 'setup_openllm_logging' },
    @{ Repo = 'OpenMemory'; File = 'D:\Trae CN\myproject\Dev\OpenMemory\src\openmemory\api\server.py';          Pattern = 'configure_logging' },
    @{ Repo = 'OpenRAG';    File = 'D:\Trae CN\myproject\Dev\OpenRAG\src\openrag\main.py';                      Pattern = 'LoggingMiddleware' },
    @{ Repo = 'OpenRAG';    File = 'D:\Trae CN\myproject\Dev\OpenRAG\src\openrag\observability\logging.py';     Pattern = 'X-Request-Id' }
)
foreach ($item in $wiring) {
    $count = if (Test-Path $item.File) { (Select-String -Path $item.File -Pattern $item.Pattern -ErrorAction SilentlyContinue | Measure-Object).Count } else { -1 }
    "{0,-12} {1} ← {2} = {3}" -f $item.Repo, (Split-Path $item.File -Leaf), $item.Pattern, $count | Add-Content -Path $envEvidence -Encoding UTF8
}

Write-Step 'TT-147-002 采集命名契约实测（-Action namecheck，读侧动作）'
& $orchestrator -Action namecheck *>&1 | Out-File -FilePath $namecheckFile -Encoding UTF8
"namecheck 退出码 = $LASTEXITCODE" | Add-Content -Path $namecheckFile -Encoding UTF8

if (-not $SkipStart) {
    Write-Step ('启动五方服务 + OIDC IdP（健康检查超时 {0}s；OpenMemory complete 模式约 5~7 分钟）' -f $HealthTimeout)
    & $orchestrator -Action start -HealthTimeout $HealthTimeout *>> $envEvidence
    Write-Step ("编排器启动返回；开始端点健康轮询")
}

$targets = @(
    @{ Name = 'openllm';    Url = 'http://127.0.0.1:8001/health' },
    @{ Name = 'openrag';    Url = 'http://127.0.0.1:8010/api/v1/system/health' },
    @{ Name = 'openmemory'; Url = 'http://127.0.0.1:8020/health' },
    @{ Name = 'dps';        Url = 'http://127.0.0.1:8030/health/liveness' },
    @{ Name = 'openbase';   Url = 'http://127.0.0.1:8000/openapi.json' }
)

function Test-Endpoint {
    param([string]$Url, [int]$TimeoutSec = 5)
    try {
        $resp = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return ($resp.StatusCode -eq 200)
    }
    catch { return $false }
}

Write-Step '五方服务健康轮询'
$deadline = (Get-Date).AddSeconds($HealthTimeout)
$healthy = @{}
while ((Get-Date) -lt $deadline) {
    $allUp = $true
    foreach ($t in $targets) {
        if (-not $healthy[$t.Name]) {
            if (Test-Endpoint -Url $t.Url) { $healthy[$t.Name] = $true }
        }
        if (-not $healthy[$t.Name]) { $allUp = $false }
    }
    if ($allUp) { break }
    Start-Sleep -Seconds 5
}
foreach ($t in $targets) {
    "{0,-12} {1} = {2}" -f $t.Name, $t.Url, $(if ($healthy[$t.Name]) { '健康' } else { '未就绪' }) | Add-Content -Path $envEvidence -Encoding UTF8
}
if (-not $healthy['openbase']) {
    Write-Step 'openbase 未就绪 → 终止抽样（登记环境遗留 H 类）'
    exit 3
}

Write-Step '登录取访问令牌（令牌不落盘，仅记录是否获取成功）'
$token = $null
try {
    $login = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post -ContentType 'application/json' `
        -Body (@{ username = $Username; password = $Password } | ConvertTo-Json -Compress) -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop
    $token = ($login.Content | ConvertFrom-Json).access_token
}
catch {
    Write-Step ("登录失败：{0}" -f $_.Exception.Message)
}
"登录成功 = {0}" -f [bool]$token | Add-Content -Path $envEvidence -Encoding UTF8
if (-not $token) {
    Write-Step '未取得令牌 → 终止抽样'
    exit 4
}

$families = @(
    @{ Name = 'dps';    Paths = @('/api/v1/dps-proxy/reports/overview', '/api/v1/dps-proxy/tags/categories', '/api/v1/dps-proxy/health') },
    @{ Name = 'rag';    Paths = @('/api/v1/rag-proxy/collections', '/api/v1/rag-proxy/health') },
    @{ Name = 'memory'; Paths = @('/api/v1/memory-proxy/monitor', '/api/v1/memory-proxy/health') },
    @{ Name = 'llm';    Paths = @('/api/v1/llm-proxy/models', '/api/v1/llm-proxy/health') }
)

Write-Step ("TT-147-003 网关串联抽样开始（每族 {0} 次）" -f $PerFamily)
$results = @()
$seq = 0
foreach ($family in $families) {
    for ($i = 0; $i -lt $PerFamily; $i++) {
        $seq++
        $path = $family.Paths[$i % $family.Paths.Count]
        $uri = 'http://127.0.0.1:8000' + $path
        $status = $null
        $requestId = $null
        $errorMessage = $null
        $watch = [Diagnostics.Stopwatch]::StartNew()
        try {
            $resp = Invoke-WebRequest -Uri $uri -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
            $status = [int]$resp.StatusCode
            $requestId = @($resp.Headers['X-Request-Id'])[0]
        }
        catch {
            $err = $_.Exception
            if ($err.Response) {
                try { $status = [int]$err.Response.StatusCode } catch { }
                try { $requestId = @($err.Response.Headers['X-Request-Id'])[0] } catch { }
            }
            $errorMessage = $err.Message
        }
        $watch.Stop()
        $results += [ordered]@{
            seq         = $seq
            family      = $family.Name
            path        = $path
            status      = $status
            request_id  = $requestId
            duration_ms = [int]$watch.Elapsed.TotalMilliseconds
            error       = $errorMessage
            sampled_at  = (Get-Date).ToString('s')
        }
        $sampleLine = "[{0}] {1} {2} → status={3} request_id={4} ({5} ms)" -f $seq, $family.Name, $path, $status, $requestId, [int]$watch.Elapsed.TotalMilliseconds
        Add-Content -Path $envEvidence -Value $sampleLine -Encoding UTF8
    }
}

$sampling = [ordered]@{
    generated_at  = (Get-Date).ToString('s')
    base_url      = 'http://127.0.0.1:8000'
    per_family    = $PerFamily
    total_requests = $results.Count
    with_request_id = @($results | Where-Object { $_.request_id }).Count
    requests      = $results
}
$samplingJson = $sampling | ConvertTo-Json -Depth 6
# 无 BOM UTF-8 落盘（PS5 的 Set-Content -Encoding UTF8 会写 BOM）
[System.IO.File]::WriteAllText($samplingFile, $samplingJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Step ("抽样完成：{0} 次，其中带回 X-Request-Id 的 {1} 次" -f $results.Count, $sampling.with_request_id)

Write-Step 'TT-147-004/005/006/007/010 串联一致性 + JSONL 契约 + 可检索 + 兜底校验'
# 校验脚本会向 stderr 输出适配器告警；若保持 ErrorActionPreference=Stop，PS5 会把
# native stderr 当作终止性错误并中断本脚本（首轮实测踩坑），故此处临时降为 Continue。
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& python $verifier --sampling $samplingFile --logs-root (Join-Path $root 'logs') --out-dir $evi
$verifyExit = $LASTEXITCODE
$ErrorActionPreference = $previousPreference
"校验脚本退出码 = $verifyExit" | Add-Content -Path $envEvidence -Encoding UTF8

if ($StopAfter) {
    Write-Step '停止全部服务'
    & $orchestrator -Action stop *>> $envEvidence
}

Write-Step ("BL-147-05 验收执行完成（校验退出码 {0}；0=通过，1=未通过）" -f $verifyExit)
exit $verifyExit
