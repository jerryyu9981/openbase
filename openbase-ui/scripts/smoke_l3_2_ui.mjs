#!/usr/bin/env node
/**
 * S6-T5-1 / S6-T5-3：L3-2 贯通冒烟基座（统一前端 → OpenBase 受信通道 → 子系统）
 *
 * 设计依据：《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》§4.5、§5.1~§5.3
 *          Q-FE-5（L3-2 经受信通道端到端、关键页 PASS、无旁路直连、真实 HTTP 双签，不可达即 PENDING）
 *          Q-S6-D6（与 Playwright 共享 tests/e2e/fixtures/key-pages.json，防断言漂移）
 *
 * 职责：
 *   1) 静态旁路检查（沙箱内可判定）：扫描 openbase-ui/src 中子系统端口字面量与绝对 URL，
 *      白名单外命中 = 0；API 客户端必须经同域 `/api/v1`（无绝对子系统地址直连）；
 *   2) 通道探活（`/health`）与登录取 token（env 注入或账号登录）；
 *   3) 逐关键页调用其数据端点，断言 200/空/403（受信通道口径）并记录 `X-Proxy-Source` 来源标识；
 *   4) 越权/跨域探针（无 token → 401/403；跨域头 → 空或 403）；
 *   5) 输出 evidence JSON 至 `doc/test/evidence/s6/l3-2-smoke.json`，含
 *      `openbase_commit` / `ui_version` / `status` / `PENDING` / 时间戳。
 *
 * 纪律：环境不可达一律 `status: PENDING` 并**退出码非 0**；禁止伪造通过或 hash。
 * 退出码约定：0 = PASS；1 = FAIL；2 = PENDING（环境待办）。
 *
 * 仅允许暴露一个入口环境变量：`OPENBASE_BASE_URL`（nginx 同域 `/ui/` + `/api/` 或 gateway）。
 * 本脚本**不使用任何第三方依赖**（Node 原生 fetch + node: 内置模块）。
 */
import { execFileSync } from 'node:child_process'
import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const UI_ROOT = resolve(HERE, '..')
const REPO_ROOT = resolve(UI_ROOT, '..')
const FIXTURE_PATH = join(UI_ROOT, 'tests', 'e2e', 'fixtures', 'key-pages.json')
const EVIDENCE_DIR = join(REPO_ROOT, 'doc', 'test', 'evidence', 's6')
const EVIDENCE_PATH = join(EVIDENCE_DIR, 'l3-2-smoke.json')

const EXIT_PASS = 0
const EXIT_FAIL = 1
const EXIT_PENDING = 2

const TIMEOUT_MS = Number(process.env.OPENBASE_SMOKE_TIMEOUT_MS || 6000)

/** 受信来源标识协议头（P2-1 §3）：以 fixture 为准，此处为兜底常量确保来源标识不被静默丢失 */
const DEFAULT_TRUSTED_SOURCE_HEADER = 'X-Proxy-Source'

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'))
}

function readText(path) {
  return readFileSync(path, 'utf8')
}

/** OpenBase 仓提交号（真实；不可得则 null，绝不伪造） */
function gitCommit() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim()
  } catch {
    return null
  }
}

/** 统一前端承载版本（package.json.version） */
function uiVersion() {
  try {
    return readJson(join(UI_ROOT, 'package.json')).version
  } catch {
    return null
  }
}

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) walk(full, out)
    else out.push(full)
  }
  return out
}

function toPosix(path) {
  return path.replace(/\\/g, '/')
}

function annotate(hits, whitelist) {
  return hits.map((hit) => {
    const entry = whitelist.find((item) => hit.file.endsWith(item.path) && hit.text.includes(item.line_contains))
    return { ...hit, whitelisted: Boolean(entry), reason: entry ? entry.reason : '' }
  })
}

/** 静态旁路检查（设计草案 §4.5 设计说明 1；沙箱内可判定） */
function scanStaticBypass(fixture) {
  const srcRoot = join(UI_ROOT, 'src')
  const portPattern = new RegExp(fixture.static_bypass.port_pattern)
  const portHits = []
  const urlHits = []

  for (const file of walk(srcRoot)) {
    if (!/\.(ts|vue)$/.test(file)) continue
    const rel = toPosix(relative(UI_ROOT, file))
    readText(file)
      .split(/\r?\n/)
      .forEach((text, index) => {
        const trimmed = text.trim()
        if (portPattern.test(text)) portHits.push({ file: rel, line: index + 1, text: trimmed })
        if (/https?:\/\//.test(text)) urlHits.push({ file: rel, line: index + 1, text: trimmed })
      })
  }

  const portAnnotated = annotate(portHits, fixture.static_bypass.whitelist)
  const urlAnnotated = annotate(urlHits, fixture.static_bypass.absolute_url_whitelist || [])
  const apiClientDir = `${fixture.static_bypass.api_client_dir}/`
  const apiClientAbsoluteUrls = urlAnnotated.filter((hit) => hit.file.startsWith(apiClientDir))

  const unexpectedPorts = portAnnotated.filter((hit) => !hit.whitelisted)
  const unexpectedUrls = urlAnnotated.filter((hit) => !hit.whitelisted)
  const apiBaseUrl = readText(join(UI_ROOT, 'src', 'core', 'api', 'http.ts')).match(/baseURL:\s*'([^']+)'/)?.[1] ?? null

  return {
    scanned_root: 'openbase-ui/src',
    port_pattern: fixture.static_bypass.port_pattern,
    port_matched: portAnnotated.length,
    port_whitelisted: portAnnotated.filter((hit) => hit.whitelisted).length,
    port_unexpected: unexpectedPorts.map((hit) => `${hit.file}:${hit.line}`),
    port_hits: portAnnotated,
    absolute_url_matched: urlAnnotated.length,
    absolute_url_unexpected: unexpectedUrls.map((hit) => `${hit.file}:${hit.line}`),
    absolute_url_hits: urlAnnotated,
    api_client_base_url: apiBaseUrl,
    api_client_absolute_urls: apiClientAbsoluteUrls.map((hit) => `${hit.file}:${hit.line}`),
    pass:
      unexpectedPorts.length === 0 &&
      unexpectedUrls.length === 0 &&
      apiClientAbsoluteUrls.length === 0 &&
      apiBaseUrl === fixture.static_bypass.network_base_url_must_be,
  }
}

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    return await fetch(url, { ...options, signal: controller.signal, redirect: 'manual' })
  } finally {
    clearTimeout(timer)
  }
}

async function request(url, headers) {
  try {
    const response = await fetchWithTimeout(url, { method: 'GET', headers })
    const text = await response.text()
    let body = null
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
    const data = body && typeof body === 'object' ? body.data : undefined
    const itemCount = Array.isArray(data?.items)
      ? data.items.length
      : Array.isArray(data)
        ? data.length
        : typeof data?.total === 'number'
          ? data.total
          : null
    return {
      url,
      reachable: true,
      status: response.status,
      source_header: response.headers.get('x-proxy-source'),
      request_id: body && typeof body === 'object' ? (body.request_id ?? null) : null,
      body_code: body && typeof body === 'object' ? (body.code ?? null) : null,
      item_count: itemCount,
    }
  } catch (error) {
    return {
      url,
      reachable: false,
      status: null,
      error: `${error?.name || 'Error'}: ${error?.message || String(error)}`,
    }
  }
}

function buildHeaders(fixture, token, extra = {}) {
  const headers = {
    Accept: 'application/json',
    [fixture.trusted_source_header || DEFAULT_TRUSTED_SOURCE_HEADER]: fixture.trusted_source_value,
    ...extra,
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function login(baseUrl, fixture) {
  const username = process.env.OPENBASE_USERNAME
  const password = process.env.OPENBASE_PASSWORD
  if (!username || !password) return { token: '', error: 'OPENBASE_USERNAME/OPENBASE_PASSWORD 未配置' }
  const url = `${baseUrl}${fixture.gateway_prefix}/auth/login`
  try {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      headers: buildHeaders(fixture, '', { 'Content-Type': 'application/json' }),
      body: JSON.stringify({ username, password }),
    })
    const text = await response.text()
    let body = null
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
    const token = body?.data?.access_token || body?.access_token || ''
    if (!response.ok || !token) {
      return { token: '', error: `登录失败：HTTP ${response.status}` }
    }
    return { token, error: '' }
  } catch (error) {
    return { token: '', error: `登录请求失败：${error?.message || String(error)}` }
  }
}

function evaluateProbe(probe, expectedStatuses, allowForbidden) {
  if (!probe.reachable) return { result: 'PENDING', detail: probe.error }
  if (expectedStatuses.includes(probe.status)) return { result: 'PASS', detail: `HTTP ${probe.status}` }
  if (allowForbidden && probe.status === 403) return { result: 'PASS', detail: 'HTTP 403（越权收敛，符合 Q-FE-3b）' }
  return { result: 'FAIL', detail: `HTTP ${probe.status}（期望 ${expectedStatuses.join('/')}${allowForbidden ? ' 或 403' : ''}）` }
}

async function main() {
  const startedAt = new Date().toISOString()
  const fixture = readJson(FIXTURE_PATH)
  const commit = gitCommit()
  const version = uiVersion()
  const baseUrl = (process.env.OPENBASE_BASE_URL || '').replace(/\/+$/, '')
  const staticBypass = scanStaticBypass(fixture)

  const report = {
    schema: 'openbase-s6-l3-2-smoke/v1.0.0',
    task: 'S6-T5-1',
    design_ref: 'OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0 §4.5 / Q-FE-5 / Q-S6-D6',
    status: 'PENDING',
    reason: '',
    openbase_commit: commit,
    ui_version: version,
    base_url: baseUrl || null,
    trusted_source: { header: fixture.trusted_source_header, value: fixture.trusted_source_value },
    key_pages_source: 'tests/e2e/fixtures/key-pages.json（Q-S6-D6，与 Playwright 同源）',
    started_at: startedAt,
    finished_at: null,
    static_bypass_check: staticBypass,
    preconditions: { health: [], token_source: null },
    probes: [],
    cross_domain_probes: [],
    pending: [],
  }

  const finalize = (status, reason, exitCode) => {
    report.status = status
    report.reason = reason
    report.finished_at = new Date().toISOString()
    mkdirSync(EVIDENCE_DIR, { recursive: true })
    writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
    process.stdout.write(
      `[S6-T5-1] status=${status} exit=${exitCode}\n  evidence: ${EVIDENCE_PATH}\n  reason: ${reason}\n`,
    )
    process.exit(exitCode)
  }

  // 前置 1：静态旁路检查（与网络可达性无关，始终执行并记录）
  if (!staticBypass.pass) {
    report.pending.push({
      item: 'static-bypass-check',
      reason: '静态旁路检查未通过：白名单外端口字面量或 API 客户端绝对地址',
    })
    finalize('FAIL', '静态旁路检查未通过（白名单外命中见 static_bypass_check）', EXIT_FAIL)
    return
  }

  // 前置 2：受信通道入口
  if (!baseUrl) {
    report.pending.push({
      item: 'OPENBASE_BASE_URL',
      reason: '未配置受信通道入口（nginx 同域 /ui/+ /api/ 或 gateway），无法执行真实双签',
      blocked_by: 'B2',
    })
    finalize('PENDING', 'OPENBASE_BASE_URL 未配置（B2 环境待办，非沙箱）', EXIT_PENDING)
    return
  }

  // 前置 3：通道探活（任一 health 端点返回 HTTP 状态即视为通道可达）
  for (const path of ['/health', `${fixture.gateway_prefix}/health`]) {
    const probe = await request(`${baseUrl}${path}`, buildHeaders(fixture))
    report.preconditions.health.push(probe)
  }
  const reachable = report.preconditions.health.some((probe) => probe.reachable)
  if (!reachable) {
    report.pending.push({
      item: 'trusted-channel',
      reason: '受信通道不可达（health 探活全部网络失败）',
      blocked_by: 'B2',
    })
    finalize('PENDING', `受信通道不可达：${baseUrl}（B2 环境待办，非沙箱）`, EXIT_PENDING)
    return
  }

  // 前置 4：token（env 注入优先，其次账号登录）
  let token = process.env.OPENBASE_ACCESS_TOKEN || ''
  if (token) {
    report.preconditions.token_source = 'OPENBASE_ACCESS_TOKEN'
  } else {
    const loginResult = await login(baseUrl, fixture)
    token = loginResult.token
    report.preconditions.token_source = token ? 'password-login' : null
    if (!token) {
      report.pending.push({
        item: 'auth-token',
        reason: loginResult.error || '缺少 OPENBASE_ACCESS_TOKEN / OPENBASE_USERNAME+OPENBASE_PASSWORD',
        blocked_by: 'B2',
      })
      finalize('PENDING', '缺少受信通道登录凭据，无法执行真实双签（B2 环境待办）', EXIT_PENDING)
      return
    }
  }

  // 关键页数据端点探针（Q-FE-4b 9 页，经 fixture 同源）
  for (const page of fixture.pages) {
    const probe = await request(`${baseUrl}${page.data_endpoint}`, buildHeaders(fixture, token))
    const evaluation = evaluateProbe(probe, page.expect.success_status, page.expect.allow_forbidden)
    report.probes.push({
      page: page.id,
      name: page.name,
      path: page.path,
      data_endpoint: page.data_endpoint,
      result: evaluation.result,
      detail: evaluation.detail,
      status: probe.status,
      source_header: probe.source_header || null,
      source_passthrough: probe.source_header === fixture.trusted_source_value,
      request_id: probe.request_id || null,
      item_count: probe.item_count ?? null,
    })
    if (evaluation.result === 'PENDING') {
      report.pending.push({ item: `page:${page.id}`, reason: evaluation.detail, blocked_by: 'B2' })
    }
  }

  // 越权/跨域探针（§5.2：定向越权 → 403；他域不可见 → 空 200）
  const protectedEndpoint = `${baseUrl}${fixture.pages[0].data_endpoint}`
  const noTokenProbe = await request(protectedEndpoint, buildHeaders(fixture, ''))
  report.cross_domain_probes.push({
    case: 'no-token',
    expectation: '401/403（fail-closed）',
    result: noTokenProbe.status === 401 || noTokenProbe.status === 403 ? 'PASS' : noTokenProbe.reachable ? 'FAIL' : 'PENDING',
    status: noTokenProbe.status,
    detail: noTokenProbe.reachable ? `HTTP ${noTokenProbe.status}` : noTokenProbe.error,
  })
  // 跨域探针（§5.2）：以**规范头 X-Tenant-ID** 声明他域视角——非受信来源携带身份头
  // fail-closed（403 PERM_UNTRUSTED_IDENTITY_HEADER）；受信来源则「他域不可见（空 200）」。
  // 修正记录（AD-TENANT-1）：此前误用非规范头 `X-Tenant-Code`（协议头规范 v1.0 未定义该头，
  // 网关不视其为身份头）→ 恒回本域数据、断言失真；改为规范头后按强校验段口径 fail-closed。
  const crossTenantProbe = await request(
    protectedEndpoint,
    buildHeaders(fixture, token, { 'X-Tenant-ID': 'tenant_other' }),
  )
  const crossTenantDenied = crossTenantProbe.status === 403
  const crossTenantEmpty =
    crossTenantProbe.status === 200 &&
    (crossTenantProbe.item_count === 0 || crossTenantProbe.item_count === null)
  report.cross_domain_probes.push({
    case: 'cross-tenant-header',
    expectation: '403（非受信来源带头 fail-closed）/ 200（空：受信来源且他域不可见）',
    result: crossTenantDenied || crossTenantEmpty ? 'PASS' : crossTenantProbe.reachable ? 'FAIL' : 'PENDING',
    status: crossTenantProbe.status,
    body_code: crossTenantProbe.body_code ?? null,
    item_count: crossTenantProbe.item_count ?? null,
    detail: crossTenantProbe.reachable
      ? `HTTP ${crossTenantProbe.status}${crossTenantProbe.body_code ? ` ${crossTenantProbe.body_code}` : ''}`
      : crossTenantProbe.error,
  })

  const pendingCount = report.pending.length
  const failed = [...report.probes, ...report.cross_domain_probes].filter((item) => item.result === 'FAIL')
  const crossedPending = report.cross_domain_probes.filter((item) => item.result === 'PENDING')

  if (crossedPending.length > 0 && pendingCount === 0 && failed.length === 0) {
    for (const item of crossedPending) report.pending.push({ item: `cross:${item.case}`, reason: item.detail, blocked_by: 'B2' })
    finalize('PENDING', '越权/跨域探针不可达（B2 环境待办）', EXIT_PENDING)
    return
  }
  if (pendingCount > 0) {
    finalize('PENDING', `存在 ${pendingCount} 项环境待办（见 pending 字段）`, EXIT_PENDING)
    return
  }
  if (failed.length > 0) {
    finalize('FAIL', `存在 ${failed.length} 项断言失败（见 probes/cross_domain_probes）`, EXIT_FAIL)
    return
  }
  finalize('PASS', 'L3-2 关键页数据面 / 受信通道来源标识 / 越权收敛 全绿', EXIT_PASS)
}

main().catch((error) => {
  const failure = {
    schema: 'openbase-s6-l3-2-smoke/v1.0.0',
    task: 'S6-T5-1',
    status: 'PENDING',
    reason: `冒烟脚本异常：${error?.message || String(error)}`,
    openbase_commit: null,
    ui_version: null,
    pending: [{ item: 'script-error', reason: String(error?.message || error) }],
    finished_at: new Date().toISOString(),
  }
  try {
    mkdirSync(EVIDENCE_DIR, { recursive: true })
    writeFileSync(EVIDENCE_PATH, `${JSON.stringify(failure, null, 2)}\n`, 'utf8')
  } catch {
    // 忽略证据写入失败（仍以非 0 退出码如实反映）
  }
  process.stderr.write(`[S6-T5-1] PENDING（脚本异常）：${failure.reason}\n`)
  process.exit(EXIT_PENDING)
})
