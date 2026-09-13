/**
 * 逐服务全页面前端 E2E 取证（通过统一前端 openbase-ui 对每个后端服务的页面做端到端遍历）。
 *
 * 覆盖口径（页面清单取自各模块 navItems 单一来源，与侧边导航一致）：
 *   OpenBase 自身 : /dashboard、/system/*（租户 + OpenLLM 系统管理 8 页）、/gateway/*
 *   OpenLLM       : /openllm/*（模型中心 15 页 + AI 应用 7 页）
 *   OpenRAG       : /knowledge/*（6 页）
 *   OpenMemory    : /memory/*（8 页）
 *   DPS           : /portrait/*（11 页）
 *
 * 逐页断言（与 S6-T5-2 / Q-FE-4b 同口径）：
 *   1) 导航成功且未被重定向到 /auth/login 或 /dashboard（重定向 = 模块守卫拒绝，记 FAIL）
 *   2) 未触发渲染兜底 [data-test="layout-render-fallback"]
 *   3) 无 pageerror、无 console error、无 console warn
 *
 * 用法（在 openbase-ui 目录，先设 OPENBASE_ACCESS_TOKEN 与 OPENBASE_BASE_URL）：
 *   node scripts/ui_e2e_all_services.mjs
 *   node scripts/ui_e2e_all_services.mjs --service openllm       # 仅跑某服务
 *   node scripts/ui_e2e_all_services.mjs --out <path>
 *
 * 环境变量：
 *   OPENBASE_BASE_URL      前端地址（vite 仅监听 IPv6 回环，须用 http://localhost:5173）
 *   OPENBASE_ACCESS_TOKEN  登录态（与 E2E 同键 ob_access_token）
 *   OPENBASE_REFRESH_TOKEN 可选
 */
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const BASE_URL = process.env.OPENBASE_BASE_URL || 'http://localhost:5173'
const ACCESS_TOKEN = process.env.OPENBASE_ACCESS_TOKEN || ''
const REFRESH_TOKEN = process.env.OPENBASE_REFRESH_TOKEN || ''
const DEFAULT_OUT = '../doc/test/evidence/s6/ui-e2e-all-services.json'

const RENDER_FALLBACK = '[data-test="layout-render-fallback"]'
const NAV_TIMEOUT_MS = 20000
const SETTLE_MS = 1200

const PAGES = {
  openbase: [
    ['/dashboard', '仪表盘'],
    ['/system/tenants', '租户管理'],
    ['/system/roles', '角色权限'],
    ['/system/org', '组织/团队/用户'],
    ['/system/workspaces', '工作空间'],
    ['/system/config', '配置管理'],
    ['/system/audit', '审计日志'],
    ['/system/edgerouter', 'EdgeRouter'],
    ['/system/docs', '文档中心'],
    ['/system/billing', '计费'],
    ['/gateway/services', '服务列表'],
    ['/gateway/aggregate', '聚合测试'],
  ],
  openllm: [
    ['/openllm/models', '模型管理'],
    ['/openllm/models/local', '本地模型'],
    ['/openllm/models/categories', '模型分类'],
    ['/openllm/models/comparison', '模型对比'],
    ['/openllm/models/market', '开源市场'],
    ['/openllm/downloads', '下载管理'],
    ['/openllm/providers', '提供商管理'],
    ['/openllm/favorites', '我的收藏'],
    ['/openllm/usage', '用量统计'],
    ['/openllm/settings', '个人设置'],
    ['/openllm/providers/register', '提供商注册'],
    ['/openllm/api-keys', 'API 密钥'],
    ['/openllm/deploy', '模型部署'],
    ['/openllm/gpu', 'GPU 监控'],
    ['/openllm/adapters', 'EdgeRouter 适配器'],
    ['/openllm/apps', '应用管理'],
    ['/openllm/apps/new', '创建应用'],
    ['/openllm/playground', 'Playground'],
    ['/openllm/prompt-templates', 'Prompt 模板'],
    ['/openllm/prompt-experiments', 'Prompt 实验'],
    ['/openllm/plugins', '插件管理'],
    ['/openllm/tool-calls', '工具调用监控'],
    ['/openllm/ab-tests', 'A/B 测试'],
    ['/openllm/conversations', '对话（OpenLLM 会话）'],
  ],
  openrag: [
    ['/knowledge/list', '知识库'],
    ['/knowledge/chat', 'RAG 对话'],
    ['/knowledge/users', '用户管理'],
    ['/knowledge/settings', '系统配置'],
    ['/knowledge/admin', '管理后台'],
    ['/knowledge/console', '控制台'],
  ],
  openmemory: [
    ['/memory/list', '记忆列表'],
    ['/memory/search', '记忆搜索'],
    ['/memory/sessions', '会话管理'],
    ['/memory/graph', '记忆图谱'],
    ['/memory/api-gateway', 'API 网关'],
    ['/memory/admin', '管理后台'],
    ['/memory/decay', '衰减配置'],
    ['/memory/write', '写入记忆'],
  ],
  dps: [
    ['/portrait/overview', '数据总览'],
    ['/portrait/list', '画像列表'],
    ['/portrait/search', '画像搜索'],
    ['/portrait/tags', '标签管理'],
    ['/portrait/rules', '规则引擎'],
    ['/portrait/reports', '分析报表'],
    ['/portrait/rate-limit', '限流管理'],
    ['/portrait/api-manage', 'API 管理'],
    ['/portrait/permissions', '权限管理'],
    ['/portrait/monitor', '系统监控'],
    ['/portrait/batch', '批量任务'],
  ],
}

function parseArgs(argv) {
  const args = { service: '', out: '' }
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--service') args.service = argv[i + 1] || ''
    if (argv[i] === '--out') args.out = argv[i + 1] || ''
  }
  return args
}

async function visit(page, path) {
  const consoleErrors = []
  const consoleWarns = []
  const pageErrors = []
  const onConsole = (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
    if (message.type() === 'warning') consoleWarns.push(message.text())
  }
  const onPageError = (error) => pageErrors.push(error.message)
  page.on('console', onConsole)
  page.on('pageerror', onPageError)

  const target = `${BASE_URL}${path}`
  const result = { path, url: target, nav_status: null, final_path: '', fallback_count: 0, console_errors: [], console_warns: [], page_errors: [], result: 'FAIL', detail: '' }
  try {
    const response = await page.goto(target, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT_MS })
    result.nav_status = response ? response.status() : null
    await page.waitForTimeout(SETTLE_MS)
    result.final_path = new URL(page.url()).pathname
    result.fallback_count = await page.locator(RENDER_FALLBACK).count()
    result.console_errors = consoleErrors.slice(0, 5)
    result.console_warns = consoleWarns.slice(0, 5)
    result.page_errors = pageErrors.slice(0, 5)

    const redirectedToLogin = result.final_path.startsWith('/auth/login')
    const bouncedToDashboard = result.final_path === '/dashboard' && path !== '/dashboard'
    if (redirectedToLogin) {
      result.detail = '被重定向到登录页（登录态未生效）'
    } else if (bouncedToDashboard) {
      result.detail = '被模块守卫退回 /dashboard（权限或路由未装载）'
    } else if (result.fallback_count > 0) {
      result.detail = '触发渲染兜底（白屏保护）'
    } else if (result.page_errors.length > 0) {
      result.detail = `pageerror: ${result.page_errors[0]}`
    } else if (result.console_errors.length > 0) {
      result.detail = `console.error: ${result.console_errors[0]}`
    } else if (result.console_warns.length > 0) {
      result.detail = `console.warn: ${result.console_warns[0]}`
    } else {
      result.result = 'PASS'
      result.detail = `HTTP ${result.nav_status} 渲染正常、无 console/page error/warn`
    }
  } catch (error) {
    result.detail = `导航异常: ${error instanceof Error ? error.message : String(error)}`
  } finally {
    page.off('console', onConsole)
    page.off('pageerror', onPageError)
  }
  return result
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  const outPath = resolve(args.out || DEFAULT_OUT)
  const services = args.service ? [args.service] : Object.keys(PAGES)
  const report = {
    schema: 'openbase-ui-e2e-all-services/v1.0.0',
    base_url: BASE_URL,
    token_source: ACCESS_TOKEN ? 'OPENBASE_ACCESS_TOKEN' : '（缺失）',
    started_at: new Date().toISOString(),
    services: {},
    summary: { total: 0, pass: 0, fail: 0 },
  }

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext()
  if (ACCESS_TOKEN) {
    await context.addInitScript(
      ([access, refresh]) => {
        window.localStorage.setItem('ob_access_token', access)
        if (refresh) window.localStorage.setItem('ob_refresh_token', refresh)
      },
      [ACCESS_TOKEN, REFRESH_TOKEN],
    )
  }
  const page = await context.newPage()

  for (const service of services) {
    const pages = PAGES[service]
    if (!pages) {
      console.warn(`[skip] unknown service: ${service}`)
      continue
    }
    const entries = []
    for (const [path, title] of pages) {
      const item = await visit(page, path)
      item.title = title
      entries.push(item)
      const flag = item.result === 'PASS' ? 'PASS' : 'FAIL'
      console.log(`[${flag}] ${service} ${path} (${title}) :: ${item.detail}`)
    }
    const pass = entries.filter((entry) => entry.result === 'PASS').length
    report.services[service] = {
      total: entries.length,
      pass,
      fail: entries.length - pass,
      pages: entries,
    }
    report.summary.total += entries.length
    report.summary.pass += pass
    report.summary.fail += entries.length - pass
  }

  await browser.close()
  report.finished_at = new Date().toISOString()
  mkdirSync(dirname(outPath), { recursive: true })
  writeFileSync(outPath, JSON.stringify(report, null, 2), 'utf-8')

  console.log('\n=== 逐服务前端 E2E 汇总 ===')
  for (const [service, item] of Object.entries(report.services)) {
    console.log(`  ${service}: PASS ${item.pass} / FAIL ${item.fail}（共 ${item.total} 页）`)
  }
  console.log(`  合计: PASS ${report.summary.pass} / FAIL ${report.summary.fail}（共 ${report.summary.total} 页）`)
  console.log(`  evidence: ${outPath}`)
  process.exit(report.summary.fail === 0 ? 0 : 1)
}

main().catch((error) => {
  console.error('[fatal]', error)
  process.exit(2)
})
