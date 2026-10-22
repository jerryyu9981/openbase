/**
 * 逐服务全页面前端 E2E 取证（通过统一前端 openbase-ui 对每个后端服务的页面做端到端遍历）。
 *
 * 覆盖口径（v1.4.11 收口后的信息架构：公共功能五域 + 业务模块，页面清单与侧栏导航一致）：
 *   OpenBase 自身 : /dashboard、/personal/settings、/platform/**（公共功能五域 37 页）
 *   OpenLLM       : /openllm/*（模型中心 5 页 + AI 应用 3 页 + 对话与分析 3 页）
 *   OpenRAG       : /knowledge/*（2 页，详情/管理后台已上收公共域）
 *   OpenMemory    : /memory/*（6 页，详情页需具体 id 故不纳入遍历）
 *   DPS           : /portrait/*（5 页）＋ /portrait/dps/*（12 页模板化能力）
 *
 * 逐页断言（与 S6-T5-2 / Q-FE-4b 同口径）：
 *   1) 导航成功且未被重定向到 /auth/login 或 /dashboard（重定向 = 模块守卫拒绝，记 FAIL）
 *   2) 未触发渲染兜底 [data-test="layout-render-fallback"]
 *   3) 无 pageerror、无 console error、无 console warn
 *   4) 可选：逐页全页截图（--shots <dir>），供人工预览确认
 *
 * 用法（在 openbase-ui 目录，先设 OPENBASE_ACCESS_TOKEN 与 OPENBASE_BASE_URL）：
 *   node scripts/ui_e2e_all_services.mjs
 *   node scripts/ui_e2e_all_services.mjs --service openllm       # 仅跑某服务
 *   node scripts/ui_e2e_all_services.mjs --out <path>
 *   node scripts/ui_e2e_all_services.mjs --shots ../doc/test/evidence/ui-preview
 *
 * 环境变量：
 *   OPENBASE_BASE_URL      前端地址（vite 仅监听 IPv6 回环，须用 http://localhost:5173）
 *   OPENBASE_ACCESS_TOKEN  登录态（与 E2E 同键 ob_access_token）
 *   OPENBASE_REFRESH_TOKEN 可选
 */
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'

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
    // 身份与权限
    ['/platform/identity/tenants', '租户管理'],
    ['/platform/identity/roles', '角色与权限'],
    ['/platform/identity/org', '组织/团队/用户'],
    ['/platform/identity/workspaces', '工作空间'],
    ['/platform/identity/users', '用户管理'],
    ['/platform/identity/memory-admin', '记忆管理席位'],
    ['/platform/identity/auth-ext', '注册/找回密码'],
    ['/platform/identity/dps-permissions', '画像数据权限'],
    // 平台配置与密钥
    ['/platform/config/general', '全局配置'],
    ['/platform/config/modules', '模块开关'],
    ['/platform/config/api-keys', 'API 密钥'],
    ['/platform/config/rate-limits', '画像接口限流'],
    // 可观测与审计
    ['/platform/observability/logs', '日志中心'],
    ['/platform/observability/test-records', '测试记录'],
    ['/platform/observability/monitoring', '统一监控'],
    ['/platform/observability/monitoring/costs', '成本分析'],
    ['/platform/observability/monitoring/alerts', '告警中心'],
    ['/platform/observability/monitoring/traces', '链路追踪'],
    ['/platform/observability/monitoring/budgets', '预算管理'],
    ['/platform/observability/gpu', 'GPU 资源'],
    ['/platform/observability/usage', '用量统计'],
    ['/platform/observability/billing', '计费'],
    ['/platform/observability/service-discovery', '服务发现与编排'],
    ['/platform/observability/gateway-test', '聚合网关测试'],
    ['/platform/observability/app-calls', '应用调用记录'],
    ['/platform/observability/dps-monitor', '画像系统监控'],
    // AI 能力治理
    ['/platform/governance/providers', '提供商管理'],
    ['/platform/governance/model-categories', '模型分类'],
    ['/platform/governance/routing', '路由策略'],
    ['/platform/governance/circuit-breakers', '熔断器'],
    ['/platform/governance/deploy', '模型部署'],
    ['/platform/governance/downloads', '下载管理'],
    ['/platform/governance/tool-calls', '工具调用监控'],
    ['/platform/governance/ab-tests', 'A/B 测试'],
    ['/platform/governance/prompt-templates', 'Prompt 模板'],
    ['/platform/governance/prompt-experiments', 'Prompt 实验'],
    // 开发者资源
    ['/platform/developers/docs', '文档中心'],
    ['/platform/developers/edgerouter', 'EdgeRouter 与适配器'],
    ['/platform/developers/plugins', '插件管理'],
    ['/platform/developers/dps-api', '画像 API 管理'],
    ['/platform/developers/knowledge-admin', '知识库管理后台'],
    ['/platform/developers/knowledge-console', '知识库 API 控制台'],
    // 个人
    ['/personal/settings', '个人设置'],
  ],
  openllm: [
    ['/openllm/models', '模型管理'],
    ['/openllm/models/local', '本地模型'],
    ['/openllm/models/comparison', '模型对比'],
    ['/openllm/models/market', '开源模型市场'],
    ['/openllm/favorites', '我的收藏'],
    ['/openllm/apps', 'AI 应用'],
    ['/openllm/apps/new', '创建应用'],
    ['/openllm/playground', 'Playground'],
    ['/openllm/conversations', '对话管理'],
    ['/openllm/recommend', '模型对比推荐'],
    ['/openllm/reports-trend', '报表趋势'],
  ],
  openrag: [
    ['/knowledge/list', '知识库'],
    ['/knowledge/chat', 'RAG 对话'],
  ],
  openmemory: [
    ['/memory/list', '记忆列表'],
    ['/memory/search', '记忆搜索'],
    ['/memory/sessions', '会话管理'],
    ['/memory/graph', '记忆图谱'],
    ['/memory/decay', '衰减配置'],
    ['/memory/write', '写入记忆'],
  ],
  dps: [
    ['/portrait/overview', '数据总览'],
    ['/portrait/list', '画像列表'],
    ['/portrait/search', '画像搜索'],
    ['/portrait/tags', '标签管理'],
    ['/portrait/rules', '规则引擎'],
    ['/portrait/dps/templates', '模板族管理'],
    ['/portrait/dps/templates/new', '画像模板新建'],
    ['/portrait/dps/template-packages', '模板包导出/导入'],
    ['/portrait/dps/lineage', '标签血缘反查'],
    ['/portrait/dps/measures', '措施建议'],
    ['/portrait/dps/scoring-types', '评分类型'],
    ['/portrait/dps/annotation-adapters', 'AI 标注候选与复核'],
    ['/portrait/dps/annotation-templates', '标注模板管理'],
    ['/portrait/dps/tags', '标签体系查看'],
  ],
}

function parseArgs(argv) {
  const args = { service: '', out: '', shots: '' }
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--service') args.service = argv[i + 1] || ''
    if (argv[i] === '--out') args.out = argv[i + 1] || ''
    if (argv[i] === '--shots') args.shots = argv[i + 1] || ''
  }
  return args
}

function slugOf(path) {
  return path.replace(/^\//, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/-+$/, '')
}

async function visit(page, path, shotsDir) {
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
  const result = { path, url: target, nav_status: null, final_path: '', fallback_count: 0, console_errors: [], console_warns: [], page_errors: [], shot: '', result: 'FAIL', detail: '' }
  try {
    const response = await page.goto(target, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT_MS })
    result.nav_status = response ? response.status() : null
    await page.waitForTimeout(SETTLE_MS)
    result.final_path = new URL(page.url()).pathname
    result.fallback_count = await page.locator(RENDER_FALLBACK).count()
    result.console_errors = consoleErrors.slice(0, 5)
    result.console_warns = consoleWarns.slice(0, 5)
    result.page_errors = pageErrors.slice(0, 5)
    if (shotsDir) {
      result.shot = join(shotsDir, `${slugOf(path)}.png`)
      await page.screenshot({ path: result.shot, fullPage: true })
    }

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
  const shotsDir = args.shots ? resolve(args.shots) : ''
  if (shotsDir) mkdirSync(shotsDir, { recursive: true })
  const services = args.service ? [args.service] : Object.keys(PAGES)
  const report = {
    schema: 'openbase-ui-e2e-all-services/v1.0.0',
    base_url: BASE_URL,
    token_source: ACCESS_TOKEN ? 'OPENBASE_ACCESS_TOKEN' : '（缺失）',
    shots_dir: shotsDir || '',
    started_at: new Date().toISOString(),
    services: {},
    summary: { total: 0, pass: 0, fail: 0 },
  }

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
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
      const item = await visit(page, path, shotsDir)
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
