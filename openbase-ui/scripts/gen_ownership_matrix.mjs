/**
 * v1.4.6 统一前端路径级归属矩阵生成器（设计前端架构设计文档 v1.4.6 §3.1 / UI设计文档 v1.4.6 §9.1）
 *
 * 职责（禁止人工转写路径，脚本化可复跑）：
 *   1) 程序化扫描**全部路由声明来源**，逐条提取「现路径 + 组件名称」：
 *      - src/core/router/index.ts（staticRoutes / appChildren 静态路由）；
 *      - src/pages/platform/routes.ts、src/pages/personal/routes.ts（集中声明的平台四域/个人域路由）；
 *      - src/modules/<模块>/index.ts（openllm / knowledge / memory / portrait / gateway 模块路由）。
 *   2) 以 src/core/router/legacyRedirects.ts 为**唯一事实源**推导「目标域 / 目标路径 / 需重定向」三列，
 *      不在脚本内重复维护重定向基线，避免矩阵与运行时重定向代码漂移；
 *   3) 输出四列矩阵（现路径、目标域、目标路径、是否需要重定向）至
 *      doc/design/OpenBase-路径归属矩阵-v1.4.6.md；
 *   4) 自校验：矩阵「需重定向」行与 legacyRedirects.ts 条目差异必须为 0；
 *      未登记路径（非平台域 / 非个人域 / 非业务模块本色 / 非全局静态页 / 非重定向）告警（禁 404）。
 *
 * 退出码：0 = 全部自洽；1 = 存在未登记路径，或矩阵与 legacyRedirects.ts 存在差异。
 * 本脚本不使用任何第三方依赖（Node 原生 fs/path + 手写结构扫描）。
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const UI_ROOT = resolve(HERE, '..')
const SRC_ROOT = join(UI_ROOT, 'src')
const LEGACY_FILE = join(SRC_ROOT, 'core', 'router', 'legacyRedirects.ts')
const OUT_FILE = join(UI_ROOT, '..', 'doc', 'design', 'OpenBase-路径归属矩阵-v1.4.6.md')

/** 模块注册表（对齐后端 DEFAULT_MODULES / 前端 router `moduleRouteLoaders`） */
const MODULE_PREFIXES = {
  openllm: '/openllm',
  knowledge: '/knowledge',
  memory: '/memory',
  portrait: '/portrait',
  gateway: '/gateway',
}

/**
 * 路由声明来源（文件 → 挂载基路径）。
 * base 为 `'/'` 时表示该文件内路径以根为基准（`/auth/login` 绝对，`dashboard` 相对 `/`）；
 * 模块 index.ts 的路径以模块 route_prefix 为基准（`list` → `/memory/list`）。
 */
const ROUTE_SOURCES = [
  { label: 'src/core/router/index.ts', file: join(SRC_ROOT, 'core', 'router', 'index.ts'), base: '/' },
  { label: 'src/pages/platform/routes.ts', file: join(SRC_ROOT, 'pages', 'platform', 'routes.ts'), base: '/' },
  { label: 'src/pages/personal/routes.ts', file: join(SRC_ROOT, 'pages', 'personal', 'routes.ts'), base: '/' },
  ...Object.entries(MODULE_PREFIXES).map(([moduleName, prefix]) => ({
    label: `src/modules/${moduleName}/index.ts`,
    file: join(SRC_ROOT, 'modules', moduleName, 'index.ts'),
    base: prefix,
  })),
]

/**
 * 全局静态页（保留：不迁移、不重定向）。
 * 纳入矩阵并归类（而非静默排除），使「未登记路径 = 0」与路由清单完整可核对。
 */
const GLOBAL_PAGES = {
  '/dashboard': '登录后默认页',
  '/auth/login': '登录页',
  '/auth/oidc/callback': 'OIDC 回调页',
  '/forbidden': '403 无权限页',
}

/** 业务模块本色路径前缀（属名业务模块，不迁移，仅平行呈现） */
const MODULE_OWN_PREFIXES = ['/openllm', '/knowledge', '/memory', '/portrait']

/** 行分类输出顺序（固定顺序，输出稳定且与 locale 排序无关） */
const KIND_ORDER = ['platform', 'personal', 'module-own', 'global', 'redirect', 'pending']

const QUOTES = new Set(["'", '"', '`'])

/** 返回字符串字面量结束后的下标（未闭合则返回源码末尾） */
function skipString(source, start) {
  const quote = source[start]
  let index = start + 1
  while (index < source.length) {
    if (source[index] === '\\') {
      index += 2
      continue
    }
    if (source[index] === quote) return index + 1
    index += 1
  }
  return source.length
}

/** 返回与 openChar 配对的 closeChar 下标（找不到返回 -1）；字符串字面量内的括号不参与配对 */
function matchPair(source, open, openChar, closeChar) {
  let depth = 0
  let index = open
  while (index < source.length) {
    const char = source[index]
    if (QUOTES.has(char)) {
      index = skipString(source, index)
      continue
    }
    if (char === openChar) depth += 1
    else if (char === closeChar) {
      depth -= 1
      if (depth === 0) return index
    }
    index += 1
  }
  return -1
}

/** 去掉 `//` 与 `/* *\/` 注释（字符串字面量原样保留），避免注释中的引号/括号干扰结构扫描 */
function stripComments(source) {
  let output = ''
  let index = 0
  while (index < source.length) {
    const char = source[index]
    const next = source[index + 1]
    if (char === '/' && next === '/') {
      while (index < source.length && source[index] !== '\n') index += 1
      continue
    }
    if (char === '/' && next === '*') {
      index += 2
      while (index < source.length && !(source[index] === '*' && source[index + 1] === '/')) index += 1
      index += 2
      continue
    }
    if (QUOTES.has(char)) {
      const end = skipString(source, index)
      output += source.slice(index, end)
      index = end
      continue
    }
    output += char
    index += 1
  }
  return output
}

/**
 * 提取「数组元素级」的对象字面量（即一条路由对象）。
 * 逐字符跟踪容器栈：仅当花括号的直接父容器是数组（或文件顶层）时视为路由对象，
 * 从而**逐条**解析而不是跨条贪婪匹配——修复「模块首条路由被后一条路由并吞」的缺陷。
 */
function extractRouteObjectLiterals(source) {
  const cleaned = stripComments(source)
  const blocks = []
  const stack = []
  let index = 0
  while (index < cleaned.length) {
    const char = cleaned[index]
    if (QUOTES.has(char)) {
      index = skipString(cleaned, index)
      continue
    }
    if (char === '[') {
      stack.push('array')
      index += 1
      continue
    }
    if (char === ']') {
      stack.pop()
      index += 1
      continue
    }
    if (char === '{') {
      const parent = stack[stack.length - 1]
      const end = matchPair(cleaned, index, '{', '}')
      if (end === -1) break
      if (parent === undefined || parent === 'array') blocks.push(cleaned.slice(index, end + 1))
      index = end + 1
      continue
    }
    index += 1
  }
  return blocks
}

/** 读取「同级」属性值源码片段：跳过嵌套块，遇到同级 `,` 或块尾即止 */
function readPropertyValue(source, start) {
  let index = start
  while (index < source.length && /\s/.test(source[index])) index += 1
  const valueStart = index
  let depth = 0
  while (index < source.length) {
    const char = source[index]
    if (QUOTES.has(char)) {
      index = skipString(source, index)
      continue
    }
    if (char === '{' || char === '[' || char === '(') {
      depth += 1
      index += 1
      continue
    }
    if (char === '}' || char === ']' || char === ')') {
      depth -= 1
      index += 1
      continue
    }
    if (char === ',' && depth === 0) break
    index += 1
  }
  return { text: source.slice(valueStart, index).trim(), end: index }
}

/** 读取对象字面量的顶层属性（嵌套对象内部属性不参与，避免 meta 等污染） */
function readTopLevelProperties(blockSource) {
  const properties = new Map()
  const inner = blockSource.slice(1, blockSource.length - 1)
  let index = 0
  while (index < inner.length) {
    const char = inner[index]
    if (QUOTES.has(char)) {
      index = skipString(inner, index)
      continue
    }
    if (/[A-Za-z_$]/.test(char)) {
      let keyEnd = index
      while (keyEnd < inner.length && /[\w$]/.test(inner[keyEnd])) keyEnd += 1
      let colon = keyEnd
      while (colon < inner.length && /\s/.test(inner[colon])) colon += 1
      if (inner[colon] === ':') {
        const value = readPropertyValue(inner, colon + 1)
        properties.set(inner.slice(index, keyEnd), value.text)
        index = value.end
        continue
      }
      index = keyEnd
      continue
    }
    index += 1
  }
  return properties
}

/** 字符串字面量取值（非字面量返回 null） */
function stringLiteral(rawValue) {
  if (typeof rawValue !== 'string') return null
  const match = rawValue.match(/^'([^']*)'$/) || rawValue.match(/^"([^"]*)"$/)
  return match ? match[1] : null
}

/** 组件名：优先取 `() => import('...')` 的 basename，其次取标识符（如 `GenericPage`） */
function componentName(rawValue) {
  if (typeof rawValue !== 'string' || rawValue.length === 0) return '—'
  const imported = rawValue.match(/import\(\s*'([^']+)'\s*\)/) || rawValue.match(/import\(\s*"([^"]+)"\s*\)/)
  if (imported) {
    const base = imported[1].split('/').pop() || ''
    return base.replace(/\.vue$/, '') || '—'
  }
  if (/^[A-Za-z_$][\w$]*$/.test(rawValue)) return rawValue
  return '—'
}

/** 相对路径 → 绝对路径 */
function toAbsolutePath(base, routePath) {
  if (routePath.startsWith('/')) return routePath
  return base === '/' ? `/${routePath}` : `${base}/${routePath}`
}

/** 目标路径 → 归属域（平台四域 / 个人域） */
function domainOf(target) {
  if (target.startsWith('/personal')) return 'personal'
  const matched = target.match(/^\/platform\/([^/]+)/)
  return matched ? matched[1] : null
}

/** 解析 legacyRedirects.ts：`LEGACY_REDIRECTS` 数组内的 [from, to] 条目（唯一事实源） */
function parseLegacyRedirects(source) {
  const cleaned = stripComments(source)
  const declaration = cleaned.indexOf('LEGACY_REDIRECTS')
  if (declaration === -1) throw new Error(`${LEGACY_FILE} 未找到 LEGACY_REDIRECTS 声明`)
  const arrayStart = cleaned.indexOf('[', cleaned.indexOf('=', declaration))
  const arrayEnd = arrayStart === -1 ? -1 : matchPair(cleaned, arrayStart, '[', ']')
  if (arrayStart === -1 || arrayEnd === -1) {
    throw new Error(`${LEGACY_FILE} LEGACY_REDIRECTS 数组解析失败`)
  }
  const entries = []
  const pattern = /\[\s*'([^']+)'\s*,\s*'([^']+)'\s*\]/g
  let match
  const block = cleaned.slice(arrayStart, arrayEnd + 1)
  while ((match = pattern.exec(block)) !== null) entries.push([match[1], match[2]])
  return entries
}

/** 扫描全部声明来源，提取非参数化路由（逐条解析，不丢首条） */
function collectDeclaredRoutes() {
  const routes = []
  const seen = new Set()
  for (const source of ROUTE_SOURCES) {
    let text
    try {
      text = readFileSync(source.file, 'utf-8')
    } catch {
      continue // 模块未落地 / 已下线：跳过
    }
    for (const block of extractRouteObjectLiterals(text)) {
      const properties = readTopLevelProperties(block)
      const routePath = stringLiteral(properties.get('path'))
      if (routePath === null || routePath === '') continue // 模块根 redirect 占位 / 非常量路径
      if (routePath.includes(':')) continue // 参数化详情页不参与迁移
      const absolute = toAbsolutePath(source.base, routePath)
      if (absolute === '/') continue // AppLayout 容器路由（无独立页面）
      if (seen.has(absolute)) continue
      seen.add(absolute)
      routes.push({ path: absolute, component: componentName(properties.get('component')), source: source.label })
    }
  }
  return routes
}

/** 单条声明路由的归属判定：重定向 > 全局静态页 > 平台/个人域 > 业务模块本色 > 未登记 */
function describeDeclaredRoute(route, legacyTargets) {
  const redirectTarget = legacyTargets.get(route.path)
  if (redirectTarget) {
    return {
      current: route.path,
      component: route.component,
      target: redirectTarget,
      domain: domainOf(redirectTarget),
      redirect: true,
      kind: 'redirect',
      note: '旧路径，legacyRedirects.ts 承接（禁 404）',
    }
  }
  if (GLOBAL_PAGES[route.path]) {
    return { current: route.path, component: route.component, target: null, domain: '全局静态页', redirect: false, kind: 'global', note: `保留（${GLOBAL_PAGES[route.path]}）` }
  }
  if (route.path.startsWith('/platform/')) {
    return { current: route.path, component: route.component, target: route.path, domain: domainOf(route.path), redirect: false, kind: 'platform', note: '平台四域目标页（归域）' }
  }
  if (route.path.startsWith('/personal/')) {
    return { current: route.path, component: route.component, target: route.path, domain: 'personal', redirect: false, kind: 'personal', note: '个人域目标页（归域）' }
  }
  const isOwn = MODULE_OWN_PREFIXES.some((prefix) => route.path === prefix || route.path.startsWith(`${prefix}/`))
  if (isOwn) {
    return { current: route.path, component: route.component, target: null, domain: '业务模块', redirect: false, kind: 'module-own', note: '本色，不迁移' }
  }
  return {
    current: route.path,
    component: route.component,
    target: null,
    domain: null,
    redirect: false,
    kind: 'pending',
    note: `未登记（来源 ${route.source}）：请在 legacyRedirects.ts 或平台四域路由中归类（禁 404）`,
  }
}

/** 组装矩阵行：声明路由 ∪ legacyRedirects 中已不在路由表的旧路径 */
function buildRows(declaredRoutes, legacyEntries, legacyTargets) {
  const rows = declaredRoutes.map((route) => describeDeclaredRoute(route, legacyTargets))
  const seen = new Set(rows.map((row) => row.current))
  for (const [from, to] of legacyEntries) {
    if (seen.has(from)) continue // 该旧路径仍在路由表中，已由声明路由行承载
    seen.add(from)
    rows.push({
      current: from,
      component: '—',
      target: to,
      domain: domainOf(to),
      redirect: true,
      kind: 'redirect',
      note: '旧路径（已迁出路由表），legacyRedirects.ts 承接（禁 404）',
    })
  }
  return rows
}

/** 统计（各项均由矩阵行派生，保证与矩阵内容自洽） */
function summarize(rows, declaredRoutes, legacyEntries) {
  const legacyOnly = rows.filter((row) => row.kind === 'redirect' && row.component === '—').length
  return {
    rows: rows.length,
    declared: declaredRoutes.length,
    legacy: legacyEntries.length,
    legacyOnly,
    redirected: rows.filter((row) => row.redirect).length,
    platform: rows.filter((row) => row.kind === 'platform').length,
    personal: rows.filter((row) => row.kind === 'personal').length,
    ownModules: rows.filter((row) => row.kind === 'module-own').length,
    globalPages: rows.filter((row) => row.kind === 'global').length,
    unresolved: rows.filter((row) => row.kind === 'pending').length,
  }
}

/** 自校验：矩阵「需重定向」行 vs legacyRedirects.ts 条目（差异应为 0） */
function crossCheckWithLegacy(rows, legacyEntries) {
  const matrixRedirects = rows.filter((row) => row.redirect)
  const missingInMatrix = legacyEntries.filter(
    ([from, to]) => !matrixRedirects.some((row) => row.current === from && row.target === to),
  )
  const extraInMatrix = matrixRedirects.filter(
    (row) => !legacyEntries.some(([from, to]) => from === row.current && to === row.target),
  )
  return { diff: missingInMatrix.length + extraInMatrix.length, missingInMatrix, extraInMatrix }
}

function render(rows, stats, checks) {
  const sorted = [...rows].sort(
    (left, right) =>
      KIND_ORDER.indexOf(left.kind) - KIND_ORDER.indexOf(right.kind) || left.current.localeCompare(right.current),
  )
  const body = sorted
    .map((row) => `| ${row.current} | ${row.component} | ${row.domain || '—'} | ${row.target || '—'} | ${row.redirect ? '**是**' : '否'} | ${row.note} |`)
    .join('\n')
  const lines = [
    '# OpenBase 路径归属矩阵 - v1.4.6（脚本生成）',
    '',
    '| 项目 | 内容 |',
    '|------|------|',
    '| 项目名称 | OpenBase（开放底座） |',
    '| 版本号 | v1.4.6 |',
    '| 生成方式 | openbase-ui/scripts/gen_ownership_matrix.mjs（脚本程序化提取，禁人工转写） |',
    `| 生成日期 | ${new Date().toISOString().slice(0, 10)} |`,
    '| 来源 | src/core/router/index.ts + src/pages/platform/routes.ts + src/pages/personal/routes.ts + src/modules/<模块>/index.ts + src/core/router/legacyRedirects.ts（重定向唯一事实源） |',
    '',
    '## 统计',
    '',
    `- 路由条数（不含参数化详情页）：${stats.rows}（声明路由 ${stats.declared} + 旧路径承接条目 ${stats.legacyOnly}）`,
    `- 需重定向（旧路径保持可达）：${stats.redirected}`,
    `- 平台四域目标页（迁移/归域）：${stats.platform}`,
    `- 业务模块本色页（不迁移）：${stats.ownModules}`,
    `- 未登记路径：${stats.unresolved}（应为 0，AC-146-11-2）`,
    `- 个人域目标页（迁移/归域）：${stats.personal}`,
    `- 全局静态页（保留，不迁移）：${stats.globalPages}`,
    `- 与 src/core/router/legacyRedirects.ts 条目差异：${checks.diff}（应为 0，重定向单一事实源自校验）`,
    '',
    '## 全量四列矩阵',
    '',
    '| 现路径 | 组件 | 目标域 | 目标路径 | 需重定向 | 说明 |',
    '|--------|------|--------|----------|:--------:|------|',
    body,
    '',
    '> 注 1：参数化路由（如 `:id` 详情页）按既有语义保留在各自模块，不参与迁移。',
    '> 注 2：全局静态页（/dashboard、/auth/login、/auth/oidc/callback、/forbidden）不迁移、不重定向；纳入矩阵并归类（非静默排除），以保证「未登记路径 = 0」可核对。',
    '> 注 3：「目标域 / 目标路径 / 需重定向」三列由 src/core/router/legacyRedirects.ts 程序化推导，脚本内不重复维护基线。',
    '',
  ]
  return lines.join('\n')
}

function main() {
  const legacyEntries = parseLegacyRedirects(readFileSync(LEGACY_FILE, 'utf-8'))
  const legacyTargets = new Map(legacyEntries)
  const declaredRoutes = collectDeclaredRoutes()
  const rows = buildRows(declaredRoutes, legacyEntries, legacyTargets)
  const stats = summarize(rows, declaredRoutes, legacyEntries)
  const checks = crossCheckWithLegacy(rows, legacyEntries)
  const unresolved = rows.filter((row) => row.kind === 'pending')

  writeFileSync(OUT_FILE, render(rows, stats, checks), 'utf-8')
  console.log(`归属矩阵已生成：${OUT_FILE}`)
  console.log(
    `路由条数=${stats.rows}（声明 ${stats.declared} + 旧路径承接 ${stats.legacyOnly}）` +
      ` 需重定向=${stats.redirected} 平台四域=${stats.platform} 个人域=${stats.personal}` +
      ` 业务本色=${stats.ownModules} 全局静态页=${stats.globalPages} 未登记=${stats.unresolved}`,
  )
  console.log(`与 legacyRedirects.ts 条目差异=${checks.diff}（legacy 条目 ${stats.legacy}）`)

  if (unresolved.length > 0) {
    console.warn('⚠ 以下路径未匹配任何归属规则，请在 §3.1 / legacyRedirects.ts 登记（禁 404）：')
    for (const row of unresolved) console.warn(`  - ${row.current}（${row.source || 'legacy'}）`)
    process.exitCode = 1
  } else {
    console.log('差异核对通过：全部路径已登记（AC-146-11-2）')
  }

  if (checks.diff !== 0) {
    console.warn('⚠ 矩阵「需重定向」行与 legacyRedirects.ts 不一致：')
    for (const [from, to] of checks.missingInMatrix) console.warn(`  - legacy 有而矩阵缺：${from} → ${to}`)
    for (const row of checks.extraInMatrix) console.warn(`  - 矩阵有而 legacy 缺：${row.current} → ${row.target}`)
    process.exitCode = 1
  } else {
    console.log('自校验通过：矩阵「需重定向」行与 legacyRedirects.ts 条目一致（差异 0）')
  }
}

main()
