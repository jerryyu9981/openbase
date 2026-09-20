<#
.SYNOPSIS
  HTTP 响应取证探针：取状态码 / 响应头 / 响应体（含 4xx、5xx 错误体）。

.DESCRIPTION
  本探针为 DEF-BE-147-005 复盘产物。背景（假阳性事故）：
  Windows PowerShell 5.1 下 `Invoke-WebRequest` 在非 2xx 时抛异常，此时
  `$_.Exception.Response.GetResponseStream()` 读到的是 0 字节（该流已被 PS 内部
  错误处理消费；同一响应体实际缓存在 `$_.ErrorDetails.Message`）。据此得出的
  「响应体为空」结论曾污染 DEF-BE-147-005 定位证据。

  因此本探针提供两条可靠口径，并可三方交叉验证：
    A. 默认      ：.NET HttpClient（独立 HTTP 栈，非 2xx 同样返回全部字节）
    B. -Raw      ：原始 socket 抓取（status line + 原始头 + 原始体字节，最权威）
    C. -ViaInvokeWebRequest：PS 原生口径（ErrorDetails 对照 GetResponseStream）

  取证铁律：**禁止以 `GetResponseStream()` 作为「响应体为空」的唯一判据**。

.PARAMETER Uri
  目标 URL，如 http://127.0.0.1:8010/api/v1/collections

.PARAMETER Method
  HTTP 方法，默认 GET。

.PARAMETER Headers
  请求头哈希表，如 @{ 'X-API-Key' = 'xxx' }

.PARAMETER Body
  请求体（可选）。

.PARAMETER ContentType
  请求体 Content-Type，默认 application/json。

.PARAMETER Raw
  使用原始 socket 抓取（打印 status line、原始头、原始体）。

.PARAMETER ViaInvokeWebRequest
  附加 PS 原生口径对照（ErrorDetails vs GetResponseStream）。

.EXAMPLE
  & .\scripts\probe_http_response.ps1 -Uri 'http://127.0.0.1:8010/api/v1/collections' `
      -Headers @{ 'X-API-Key' = 'k'; 'X-Proxy-Source' = 'openbase-rag-proxy'; 'X-Tenant-ID' = 'default' } -Raw
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [string]$Method = 'GET',
    [hashtable]$Headers = @{},
    [string]$Body,
    [string]$ContentType = 'application/json',
    [switch]$Raw,
    [switch]$ViaInvokeWebRequest
)

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Net.Http -ErrorAction SilentlyContinue

# PS5(.NET Framework) 无 Encoding.Latin1 属性，按代码页取 ISO-8859-1（28591，字节级透传用）
$script:Latin1Encoding = [Text.Encoding]::GetEncoding(28591)

function Write-Section {
    param([string]$Title)
    Write-Output ''
    Write-Output ("===== " + $Title + " =====")
}

function Write-Verdict {
    param([string]$Channel, [int]$StatusCode, [int]$BodyLength, [string]$ContentTypeSeen)
    $verdict = if ($BodyLength -gt 0) { 'NON-EMPTY' } else { 'EMPTY' }
    Write-Output ("VERDICT[{0}] status={1} body_bytes={2} body={3} content_type={4}" -f `
        $Channel, $StatusCode, $BodyLength, $verdict, $ContentTypeSeen)
}

function Invoke-ViaHttpClient {
    param([string]$TargetUri, [string]$HttpMethod, [hashtable]$RequestHeaders, [string]$RequestBody, [string]$RequestContentType)

    $handler = New-Object System.Net.Http.HttpClientHandler
    # 探针口径：禁用系统代理与自动重定向，确保观测到「首跳原始响应」
    $handler.UseProxy = $false
    $handler.AllowAutoRedirect = $false
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(30)
    $request = New-Object System.Net.Http.HttpRequestMessage($HttpMethod, $TargetUri)
    foreach ($name in $RequestHeaders.Keys) {
        [void]$request.Headers.TryAddWithoutValidation($name, $RequestHeaders[$name])
    }
    if ($RequestBody) {
        $request.Content = New-Object System.Net.Http.StringContent($RequestBody, [Text.Encoding]::UTF8, $RequestContentType)
    }
    try {
        $response = $client.SendAsync($request).GetAwaiter().GetResult()
        $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $bytes = [Text.Encoding]::UTF8.GetByteCount($text)
        Write-Output ("STATUS=" + [int]$response.StatusCode)
        Write-Output ("RESPONSE_HEADERS=")
        foreach ($h in $response.Headers) { Write-Output ("  {0}: {1}" -f $h.Key, ($h.Value -join ',')) }
        foreach ($h in $response.Content.Headers) { Write-Output ("  {0}: {1}" -f $h.Key, ($h.Value -join ',')) }
        Write-Output ("BODY_UTF8_BYTES=" + $bytes)
        Write-Output ("BODY=" + $text)
        Write-Verdict -Channel 'HttpClient' -StatusCode ([int]$response.StatusCode) -BodyLength $bytes `
            -ContentTypeSeen ([string]$response.Content.Headers.ContentType)
    }
    catch {
        Write-Output ("HTTPCLIENT_ERR=" + $_.Exception.Message)
        $base = $_.Exception.GetBaseException()
        Write-Output ("HTTPCLIENT_BASE_ERR=" + $base.Message)
        $inner = $_.Exception.InnerException
        while ($inner) {
            Write-Output ("HTTPCLIENT_INNER_ERR=" + $inner.Message)
            $inner = $inner.InnerException
        }
    }
    finally {
        if ($request) { $request.Dispose() }
        if ($client) { $client.Dispose() }
    }
}

function Invoke-ViaRawSocket {
    param([string]$TargetUri, [string]$HttpMethod, [hashtable]$RequestHeaders, [string]$RequestBody)

    $target = [Uri]$TargetUri
    $port = if ($target.Port -gt 0) { $target.Port } else { 80 }
    $pathAndQuery = $target.PathAndQuery

    $requestText = "{0} {1} HTTP/1.1`r`nHost: {2}:{3}`r`nConnection: close`r`n" -f `
        $HttpMethod, $pathAndQuery, $target.Host, $port
    foreach ($name in $RequestHeaders.Keys) {
        $requestText += ("{0}: {1}`r`n" -f $name, $RequestHeaders[$name])
    }
    if ($RequestBody) {
        $requestText += ("Content-Type: application/json`r`nContent-Length: {0}`r`n" -f [Text.Encoding]::UTF8.GetByteCount($RequestBody))
    }
    $requestText += "`r`n"
    if ($RequestBody) { $requestText += $RequestBody }

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect($target.Host, $port)
        $stream = $client.GetStream()
        $payload = $script:Latin1Encoding.GetBytes($requestText)
        $stream.Write($payload, 0, $payload.Length)
        $stream.Flush()

        $buffer = New-Object System.IO.MemoryStream
        $chunk = New-Object byte[] 65536
        while ($true) {
            $read = $stream.Read($chunk, 0, $chunk.Length)
            if ($read -le 0) { break }
            $buffer.Write($chunk, 0, $read)
        }
        $all = $buffer.ToArray()
        $allText = $script:Latin1Encoding.GetString($all)
        $splitAt = $allText.IndexOf("`r`n`r`n")
        if ($splitAt -lt 0) {
            Write-Output 'RAWSOCKET_ERR=no header separator observed'
            return
        }
        $head = $allText.Substring(0, $splitAt)
        $bodyLength = $all.Length - ($splitAt + 4)

        Write-Output ('WIRE_HEAD:' + "`n" + $head)
        Write-Output ("WIRE_BODY_BYTES=" + $bodyLength)
        $bodyText = [Text.Encoding]::UTF8.GetString($all, $splitAt + 4, $bodyLength)
        if ($bodyLength -gt 3000) { $bodyText = $bodyText.Substring(0, 3000) + '...(truncated)' }
        Write-Output ("WIRE_BODY=" + $bodyText)

        $statusMatch = [regex]::Match($head, '^HTTP/\d\.\d\s+(\d{3})')
        $statusCode = if ($statusMatch.Success) { [int]$statusMatch.Groups[1].Value } else { 0 }
        Write-Verdict -Channel 'RawSocket' -StatusCode $statusCode -BodyLength $bodyLength -ContentTypeSeen '(see WIRE_HEAD)'
        $buffer.Dispose()
    }
    catch {
        Write-Output ("RAWSOCKET_ERR=" + $_.Exception.Message)
    }
    finally {
        $client.Close()
    }
}

function Invoke-ViaInvokeWebRequest {
    param([string]$TargetUri, [string]$HttpMethod, [hashtable]$RequestHeaders, [string]$RequestBody, [string]$RequestContentType)

    $params = @{
        Uri             = $TargetUri
        Method          = $HttpMethod
        Headers         = $RequestHeaders
        TimeoutSec      = 30
        UseBasicParsing = $true
        ErrorAction     = 'Stop'
    }
    if ($RequestBody) { $params['Body'] = $RequestBody; $params['ContentType'] = $RequestContentType }

    try {
        $response = Invoke-WebRequest @params
        Write-Output ("PS_STATUS=" + $response.StatusCode)
        Write-Output ("PS_BODY_LEN=" + $response.Content.Length)
        Write-Output ("PS_BODY=" + $response.Content)
        Write-Verdict -Channel 'InvokeWebRequest' -StatusCode ([int]$response.StatusCode) -BodyLength $response.Content.Length -ContentTypeSeen ''
    }
    catch {
        $webResponse = $_.Exception.Response
        if (-not $webResponse) { Write-Output ('PS_ERR=' + $_.Exception.Message); return }

        $statusCode = [int]$webResponse.StatusCode
        Write-Output ("PS_STATUS=" + $statusCode)
        Write-Output ("PS_CONTENT_LENGTH_HEADER=" + $webResponse.Headers['Content-Length'])

        $errorDetailBody = $_.ErrorDetails.Message
        $errorDetailLen = if ($errorDetailBody) { $errorDetailBody.Length } else { 0 }
        Write-Output ("PS_ERRORDETAILS_LEN=" + $errorDetailLen)
        Write-Output ("PS_ERRORDETAILS=" + $errorDetailBody)

        $streamLen = 0
        try {
            $reader = New-Object System.IO.StreamReader($webResponse.GetResponseStream())
            $streamBody = $reader.ReadToEnd()
            $streamLen = $streamBody.Length
            Write-Output ("PS_STREAM_LEN=" + $streamLen)
            Write-Output ("PS_STREAM_BODY=" + $streamBody)
        }
        catch {
            Write-Output ("PS_STREAM_ERR=" + $_.Exception.Message)
        }

        if ($streamLen -eq 0 -and $errorDetailLen -gt 0) {
            Write-Output 'PS_PITFALL=GetResponseStream returned 0 while ErrorDetails holds the body (PS 5.1 consumes error stream). NOT a server-side empty body.'
        }
        Write-Verdict -Channel 'InvokeWebRequest' -StatusCode $statusCode -BodyLength $errorDetailLen -ContentTypeSeen ''
    }
}

Write-Output ("### probe target: {0} {1}" -f $Method, $Uri)
if ($Headers.Count -gt 0) {
    Write-Output ('### request headers: ' + (($Headers.Keys | Sort-Object) -join ','))
}

Write-Section 'A. .NET HttpClient'
Invoke-ViaHttpClient -TargetUri $Uri -HttpMethod $Method -RequestHeaders $Headers -RequestBody $Body -RequestContentType $ContentType

if ($Raw) {
    Write-Section 'B. raw socket（线上原始字节）'
    Invoke-ViaRawSocket -TargetUri $Uri -HttpMethod $Method -RequestHeaders $Headers -RequestBody $Body
}

if ($ViaInvokeWebRequest) {
    Write-Section 'C. Invoke-WebRequest（PS 原生口径对照）'
    Invoke-ViaInvokeWebRequest -TargetUri $Uri -HttpMethod $Method -RequestHeaders $Headers -RequestBody $Body -RequestContentType $ContentType
}
