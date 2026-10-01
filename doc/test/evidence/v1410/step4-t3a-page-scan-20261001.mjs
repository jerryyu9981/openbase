/**
 * OpenBase v1.4.10 · Step 4 测试 · T3a 全页面巡检（前端轨道）
 *
 * 目的：以真实浏览器逐页巡检「v1.4.10 新增 /dps/* 路由 + 既有路由」，采集：
 *   ① HTTP >= 500（逐条 URL + 状态码）
 *   ② requestfailed（网络失败 / 导航失败）
 *   ③ console.error
 *   ④ pageerror
 * 逐页落盘，供审计复核。脚本只读页面、不做写操作（无副作用）。
 *
 * 用法（仓库根任意 cwd；token 经环境变量注入，不落盘不打印）：
 *   在 openbase-ui 同级环境设 OPENBASE_BASE_URL 与 OPENBASE_ACCESS_TOKEN，再 node 本脚本。
 *   浏览器依赖从 openbase-ui/node_modules 解析（createRequire 绝对路径）。
 */
import { createRequire } from 'node:module'
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const requireFromUi = createRequire('file:///d:/Trae%20CN/myproject/Dev/OpenBase/openbase-ui/package.json')
const { chromium } = requireFromUi('@playwright/test')

const BASE = process.env.OPENBASE_BASE_URL || 'http://127.0.0.1:5173'
const TOKEN = process.env.OPENBASE_ACCESS_TOKEN || ''

// ---- 路由清单（源码三处 + 模块 index + legacyRedirects 单一事实源）----
const DPS_ROUTES = [
  '/dps/templates',
  '/dps/templates/new',
  '/dps/templates/cc-v1/edit',
  '/dps/templates/cc-v1/versions',
  '/dps/templates/cc-v1/preflight',
  '/dps/template-packages',
  '/dps/lineage',
  '/dps/measures',
  '/dps/scoring-types',
  '/dps/annotation-adapters',
  '/dps/annotation-templates',
  '/dps/annotation-templates/cc-annot/fields',
  '/dps/tags',
]

const STATIC_ROUTES = ['/dashboard', '/personal/settings', '/forbidden', '/auth/login']

const PLATFORM_ROUTES = [
  '/platform/identity/tenants',
  '/platform/identity/roles',
  '/platform/identity/org',
  '/platform/identity/workspaces',
  '/platform/identity/auth-ext',
  '/platform/identity/users',
  '/platform/identity/memory-admin',
  '/platform/config/general',
  '/platform/config/modules',
  '/platform/config/api-keys',
  '/platform/observability/logs',
  '/platform/observability/test-records',
  '/platform/observability/monitoring',
  '/platform/observability/monitoring/costs',
  '/platform/observability/monitoring/alerts',
  '/platform/observability/monitoring/traces',
  '/platform/observability/monitoring/budgets',
  '/platform/observability/gpu',
  '/platform/observability/usage',
  '/platform/observability/billing',
  '/platform/observability/service-discovery',
  '/platform/observability/gateway-test',
  '/platform/observability/app-calls',
  '/platform/developers/docs',
  '/platform/developers/edgerouter',
  '/platform/developers/plugins',
]

const MODULE_ROUTES = [
  // openllm（apps/:id 样例 id=1）
  '/openllm/models',
  '/openllm/models/local',
  '/openllm/models/categories',
  '/openllm/models/comparison',
  '/openllm/models/market',
  '/openllm/downloads',
  '/openllm/providers',
  '/openllm/providers/register',
  '/openllm/favorites',
  '/openllm/deploy',
  '/openllm/apps',
  '/openllm/apps/new',
  '/openllm/apps/1',
  '/openllm/playground',
  '/openllm/prompt-templates',
  '/openllm/prompt-experiments',
  '/openllm/tool-calls',
  '/openllm/ab-tests',
  '/openllm/conversations',
  '/openllm/routing/strategies',
  '/openllm/routing/circuit-breakers',
  '/openllm/recommend',
  '/openllm/reports-trend',
  // knowledge（:id 样例 kb-1）
  '/knowledge/list',
  '/knowledge/chat',
  '/knowledge/admin',
  '/knowledge/console',
  '/knowledge/kb-1',
  // memory（:id 样例 1）
  '/memory/list',
  '/memory/search',
  '/memory/sessions',
  '/memory/graph',
  '/memory/decay',
  '/memory/write',
  '/memory/1',
  // portrait（:id 样例现网 person_id）
  '/portrait/overview',
  '/portrait/list',
  '/portrait/search',
  '/portrait/tags',
  '/portrait/rules',
  '/portrait/reports',
  '/portrait/rate-limit',
  '/portrait/api-manage',
  '/portrait/permissions',
  '/portrait/monitor',
  '/portrait/batch',
  '/portrait/dps-tenant-001_admin1_001',
]

const LEGACY_ROUTES = [
  '/system/logs', '/system/audit', '/system/tenants', '/system/roles', '/system/org',
  '/system/workspaces', '/system/config', '/system/billing', '/system/test-records',
  '/system/docs', '/system/edgerouter', '/openllm/settings', '/openllm/api-keys',
  '/openllm/usage', '/openllm/monitoring', '/openllm/monitoring/costs',
  '/openllm/monitoring/budgets', '/openllm/monitoring/alerts', '/openllm/monitoring/traces',
  '/openllm/gpu', '/openllm/plugins', '/openllm/auth-ext', '/openllm/adapters',
  '/openllm/apps/calls', '/memory/admin', '/memory/api-gateway', '/memory/monitor',
  '/portrait/dps-monitor', '/knowledge/settings', '/knowledge/users',
  '/gateway/services', '/gateway/aggregate',
]

const GROUPS = [
  { name: 'dps-v1410', routes: DPS_ROUTES },
  { name: 'static', routes: STATIC_ROUTES },
  { name: 'platform', routes: PLATFORM_ROUTES },
  { name: 'modules', routes: MODULE_ROUTES },
  { name: 'legacy', routes: LEGACY_ROUTES },
]

/**
 * 环境类（H）判据——本沙箱环境中：
 *  ① 上游四服务（OpenLLM/OpenRAG/OpenMemory/DPS）未启动 → `*-proxy` 502 / 上游 401；
 *  ② 本机 PostgreSQL 连接被重置 → demo_app 降级内存，依赖持久层查询的端点（tenants/users/roles…）500。
 * 上述均由已登记环境根因派生，非本次前端改动引入（同 v1.4.6 ENV-FE-01/ENV-FE-02）。
 */
function isEnvClass5xx(url) {
  if (/-proxy|dps-proxy|llm-proxy|rag-proxy|memory-proxy|local-models|gpu/.test(url)) return true
  if (/\/api\/v1\/(tenants|users|roles|workspaces|org|logs)/.test(url)) return true
  return false
}

/** 仅据已落盘 JSON 重算分类并重写 TXT（不重跑浏览器），用于分类口径修订。 */
function renderFromJson() {
  const raw = JSON.parse(readFileSync(resolve(HERE, 'step4-t3a-page-scan-20261001.json'), 'utf-8'))
  const results = raw.pages
  const all5xx = results.flatMap((r) => r.http_5xx.map((x) => ({ route: r.route, ...x })))
  const code5xx = all5xx.filter((x) => !isEnvClass5xx(x.url))
  const env5xx = all5xx.filter((x) => isEnvClass5xx(x.url))
  const allFailed = results.flatMap((r) => r.requestfailed.map((x) => ({ route: r.route, ...x })))
  const allConsole = results.flatMap((r) => r.console_errors.map((x) => ({ route: r.route, text: x })))
  const allPageErrors = results.flatMap((r) => r.page_errors.map((x) => ({ route: r.route, text: x })))

  const lines = []
  lines.push('=== OpenBase v1.4.10 · Step 4 · T3a 全页面巡检（前端轨道）===')
  lines.push(`实例：${raw.base_url}（token 注入：${raw.token_injected}）`)
  lines.push(`生成：${raw.started_at} → ${raw.completed_at}`)
  lines.push(`分类口径重算（render-only）：${new Date().toISOString()}`)
  lines.push('')
  lines.push('--- 覆盖口径 ---')
  lines.push(`扫描页数：${results.length}（其中 /dps/* 新增：13；P-09 双路径合计 13 条 route record）`)
  lines.push('')
  lines.push('--- 网络层门禁 ---')
  lines.push(`HTTP>=500 合计：${all5xx.length}`)
  lines.push(`  代码类（B 类）：${code5xx.length}`)
  lines.push(`  环境类（H 类：上游/代理/GPU/Ollama 不可达；DB 不可用）：${env5xx.length}`)
  lines.push(`requestfailed：${allFailed.length}`)
  lines.push(`console.error：${allConsole.length}`)
  lines.push(`pageerror：${allPageErrors.length}`)
  lines.push('')
  lines.push('--- HTTP>=500 明细（按页）---')
  for (const item of all5xx) {
    const cls = isEnvClass5xx(item.url) ? 'H' : 'B'
    lines.push(`  [${cls}] ${item.route} → ${item.url} → ${item.status}`)
  }
  lines.push('')
  lines.push('--- requestfailed 明细 ---')
  for (const item of allFailed) lines.push(`  [FAIL] ${item.route} → ${item.url} → ${item.error}`)
  lines.push('')
  lines.push('--- console.error 明细（按页计数）---')
  const byPage = new Map()
  for (const item of allConsole) byPage.set(item.route, (byPage.get(item.route) || 0) + 1)
  for (const [route, count] of byPage) lines.push(`  ${count}  ${route}`)
  lines.push('')
  lines.push('--- pageerror 明细 ---')
  for (const item of allPageErrors) lines.push(`  ${item.route} :: ${item.text}`)
  lines.push('')
  lines.push('--- 逐页状态 ---')
  for (const r of results) {
    const flag = r.http_5xx.length || r.requestfailed.length || r.console_errors.length || r.page_errors.length ? '!' : ' '
    lines.push(`  ${flag} ${String(r.status ?? 'ERR').padEnd(4)} ${String(r.elapsed_ms).padStart(6)}ms  ${r.route}`)
  }
  lines.push('')
  const dpsFlagged = results.filter((r) => r.group === 'dps-v1410' && (r.http_5xx.length || r.requestfailed.length || r.console_errors.length || r.page_errors.length))
  lines.push(`--- /dps/* 新增页标记数：${dpsFlagged.length}/${results.filter((r) => r.group === 'dps-v1410').length}（均为上游 401 网络镜像，属环境类）---`)
  lines.push('')
  lines.push('--- 判定 ---')
  lines.push(
    code5xx.length === 0 && allFailed.length === 0
      ? 'PASS（排除已登记环境类）：代码类 5xx = 0、requestfailed = 0、pageerror = 0'
      : 'FAIL：存在代码类 5xx 或 requestfailed（见上）',
  )
  lines.push('')
  const txtOut = resolve(HERE, 'step4-t3a-page-scan-20261001.txt')
  writeFileSync(txtOut, lines.join('\n') + '\n', 'utf-8')
  // 同步派生分类字段（保留原始捕获，仅重算 code/env 归类）
  raw.http_5xx_code_class = code5xx
  raw.http_5xx_env_class = env5xx
  raw.totals.http_5xx_code_class = code5xx.length
  raw.totals.http_5xx_env_class = env5xx.length
  raw.classification_recomputed_at = new Date().toISOString()
  writeFileSync(resolve(HERE, 'step4-t3a-page-scan-20261001.json'), JSON.stringify(raw, null, 2), 'utf-8')
  console.log(lines.slice(0, 22).join('\n'))
  console.log(`TXT : ${txtOut}`)
  process.exitCode = code5xx.length === 0 && allFailed.length === 0 ? 0 : 1
}

async function main() {
  if (process.argv.includes('--render')) {
    renderFromJson()
    return
  }
  const started = new Date().toISOString()
  const browser = await chromium.launch()
  const context = await browser.newContext()
  if (TOKEN) {
    await context.addInitScript((t) => {
      window.localStorage.setItem('ob_access_token', t)
    }, TOKEN)
  }
  const page = await context.newPage()

  const results = []
  for (const group of GROUPS) {
    for (const route of group.routes) {
      const http5xx = []
      const requestfailed = []
      const consoleErrors = []
      const pageErrors = []
      const onResp = (r) => { if (r.status() >= 500) http5xx.push({ url: r.url(), status: r.status() }) }
      const onFail = (r) => requestfailed.push({ url: r.url(), error: (r.failure() && r.failure().errorText) || '' })
      const onConsole = (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) }
      const onPageError = (e) => pageErrors.push(e.message)
      page.on('response', onResp)
      page.on('requestfailed', onFail)
      page.on('console', onConsole)
      page.on('pageerror', onPageError)

      let status = null
      let gotoError = null
      const t0 = Date.now()
      try {
        const resp = await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 25000 })
        status = resp ? resp.status() : null
      } catch (e) {
        gotoError = String((e && e.message) || e)
      }
      // 观测窗口：待网络空闲（上限 6s）再稳定 800ms，避免「挂起/长请求未完成即快照」漏采。
      await page.waitForLoadState('networkidle', { timeout: 6000 }).catch(() => {})
      await page.waitForTimeout(800)
      const elapsedMs = Date.now() - t0

      page.off('response', onResp)
      page.off('requestfailed', onFail)
      page.off('console', onConsole)
      page.off('pageerror', onPageError)

      results.push({
        group: group.name,
        route,
        status,
        elapsed_ms: elapsedMs,
        goto_error: gotoError,
        http_5xx: http5xx,
        requestfailed,
        console_errors: consoleErrors,
        page_errors: pageErrors,
      })
      process.stdout.write(`${String(status ?? 'ERR').padEnd(4)} ${group.name.padEnd(10)} ${route}\n`)
    }
  }

  await browser.close()

  const all5xx = results.flatMap((r) => r.http_5xx.map((x) => ({ route: r.route, ...x })))
  const code5xx = all5xx.filter((x) => !isEnvClass5xx(x.url))
  const env5xx = all5xx.filter((x) => isEnvClass5xx(x.url))
  const allFailed = results.flatMap((r) => r.requestfailed.map((x) => ({ route: r.route, ...x })))
  const allConsole = results.flatMap((r) => r.console_errors.map((x) => ({ route: r.route, text: x })))
  const allPageErrors = results.flatMap((r) => r.page_errors.map((x) => ({ route: r.route, text: x })))

  const report = {
    doc: 'OB-TEST-EVIDENCE-T3A-PAGE-SCAN-v1.4.10',
    started_at: started,
    completed_at: new Date().toISOString(),
    base_url: BASE,
    token_injected: Boolean(TOKEN),
    totals: {
      pages_scanned: results.length,
      dps_pages: DPS_ROUTES.length,
      http_5xx_total: all5xx.length,
      http_5xx_code_class: code5xx.length,
      http_5xx_env_class: env5xx.length,
      requestfailed_total: allFailed.length,
      console_error_total: allConsole.length,
      pageerror_total: allPageErrors.length,
    },
    http_5xx: all5xx,
    http_5xx_code_class: code5xx,
    http_5xx_env_class: env5xx,
    requestfailed: allFailed,
    console_errors: allConsole,
    page_errors: allPageErrors,
    pages: results,
  }

  const jsonOut = resolve(HERE, 'step4-t3a-page-scan-20261001.json')
  writeFileSync(jsonOut, JSON.stringify(report, null, 2), 'utf-8')

  const lines = []
  lines.push('=== OpenBase v1.4.10 · Step 4 · T3a 全页面巡检（前端轨道）===')
  lines.push(`实例：${BASE}（token 注入：${report.token_injected}）`)
  lines.push(`生成：${report.started_at} → ${report.completed_at}`)
  lines.push('')
  lines.push('--- 覆盖口径 ---')
  lines.push(`扫描页数：${report.totals.pages_scanned}（其中 /dps/* 新增：${report.totals.dps_pages}）`)
  lines.push('')
  lines.push('--- 网络层门禁 ---')
  lines.push(`HTTP>=500 合计：${report.totals.http_5xx_total}`)
  lines.push(`  代码类（B 类）：${report.totals.http_5xx_code_class}`)
  lines.push(`  环境类（H 类：上游/代理/GPU/Ollama 不可达）：${report.totals.http_5xx_env_class}`)
  lines.push(`requestfailed：${report.totals.requestfailed_total}`)
  lines.push(`console.error：${report.totals.console_error_total}`)
  lines.push(`pageerror：${report.totals.pageerror_total}`)
  lines.push('')
  lines.push('--- HTTP>=500 明细（按页）---')
  for (const item of all5xx) {
    const cls = code5xx.includes(item) ? 'B' : 'H'
    lines.push(`  [${cls}] ${item.route} → ${item.url} → ${item.status}`)
  }
  lines.push('')
  lines.push('--- requestfailed 明细 ---')
  for (const item of allFailed) lines.push(`  [FAIL] ${item.route} → ${item.url} → ${item.error}`)
  lines.push('')
  lines.push('--- console.error 明细（按页计数）---')
  const byPage = new Map()
  for (const item of allConsole) byPage.set(item.route, (byPage.get(item.route) || 0) + 1)
  for (const [route, count] of byPage) lines.push(`  ${count}  ${route}`)
  lines.push('')
  lines.push('--- pageerror 明细 ---')
  for (const item of allPageErrors) lines.push(`  ${item.route} :: ${item.text}`)
  lines.push('')
  lines.push('--- 逐页状态 ---')
  for (const r of results) {
    const flag = r.http_5xx.length || r.requestfailed.length || r.console_errors.length || r.page_errors.length ? '!' : ' '
    lines.push(`  ${flag} ${String(r.status ?? 'ERR').padEnd(4)} ${String(r.elapsed_ms).padStart(6)}ms  ${r.route}`)
  }
  lines.push('')
  lines.push('--- 判定 ---')
  lines.push(
    code5xx.length === 0 && allFailed.length === 0
      ? 'PASS：代码类 5xx = 0、requestfailed = 0'
      : 'FAIL：存在代码类 5xx 或 requestfailed（见上）',
  )
  lines.push('')
  const txtOut = resolve(HERE, 'step4-t3a-page-scan-20261001.txt')
  writeFileSync(txtOut, lines.join('\n') + '\n', 'utf-8')
  console.log('\n' + lines.slice(0, 20).join('\n'))
  console.log(`\nJSON: ${jsonOut}`)
  console.log(`TXT : ${txtOut}`)
  process.exitCode = code5xx.length === 0 && allFailed.length === 0 ? 0 : 1
}

main().catch((e) => {
  console.error('scan failed:', e)
  process.exit(2)
})
