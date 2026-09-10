/**
 * S6-T5 L3-2 贯通冒烟基座断言（设计草案 §4.5 / §5.4 Q-FE-4b / §10.2 Q-S6-D6）
 *
 * 本用例为沙箱内可判定面（A8 只读盘点 + 静态旁路检查），断言：
 * 1. `tests/e2e/fixtures/key-pages.json` 为 Q-FE-4b 9 关键页的**唯一事实源**（E2E 与冒烟脚本同源，防断言漂移）；
 * 2. Playwright 用例与零依赖冒烟脚本均读取同一 fixture；
 * 3. 冒烟脚本**仅**经受信通道入口（`OPENBASE_BASE_URL`）发起请求，并携带受信来源标识 `X-Proxy-Source`；
 * 4. 静态旁路检查：`openbase-ui/src` 内子系统端口字面量仅存在于「显示文案 / mock 数据」白名单（白名单外 = 0）；
 * 5. API 客户端一律经同域 `/api/v1`（无绝对子系统地址直连）；
 * 6. 冒烟脚本 evidence 字段齐备（`openbase_commit` / `ui_version` / `status` / `PENDING`）。
 *
 * 真实受信通道执行（B2）与浏览器级关键页 PASS（B1）不在沙箱内判定，一律 PENDING（禁止伪造）。
 */
import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import keyPages from './e2e/fixtures/key-pages.json'

const here = dirname(fileURLToPath(import.meta.url))
const uiRoot = resolve(here, '..')
const srcRoot = join(uiRoot, 'src')

/** Q-FE-4b 关键页 9 页（画像 3 / 对话 2 / 知识 2 / 记忆 2） */
const EXPECTED_PAGE_PATHS = [
  '/portrait/list',
  '/portrait/overview',
  '/portrait/:id',
  '/openllm/conversations',
  '/knowledge/chat',
  '/knowledge/list',
  '/knowledge/:id',
  '/memory/list',
  '/memory/sessions',
]

const SMOKE_SCRIPT = join(uiRoot, 'scripts', 'smoke_l3_2_ui.mjs')
const PLAYWRIGHT_CONFIG = join(uiRoot, 'playwright.config.ts')

function readText(path: string): string {
  return readFileSync(path, 'utf8')
}

/** 递归收集源码文件（静态旁路检查用） */
function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) walk(full, out)
    else out.push(full)
  }
  return out
}

interface PortHit {
  file: string
  text: string
}

/** 扫描 `src/**` 内「端口字面量」命中行（相对 openbase-ui 的 posix 路径） */
function scanPortLiterals(): PortHit[] {
  const hits: PortHit[] = []
  for (const file of walk(srcRoot)) {
    if (!/\.(ts|vue)$/.test(file)) continue
    const rel = relative(uiRoot, file).replace(/\\/g, '/')
    for (const line of readText(file).split(/\r?\n/)) {
      if (new RegExp(keyPages.static_bypass.port_pattern).test(line)) hits.push({ file: rel, text: line })
    }
  }
  return hits
}

function isWhitelisted(hit: PortHit): boolean {
  return keyPages.static_bypass.whitelist.some(
    (entry) => hit.file.endsWith(entry.path) && hit.text.includes(entry.line_contains),
  )
}

/** 扫描 `src/**` 内「绝对 URL」字面量 */
function scanAbsoluteUrls(): PortHit[] {
  const hits: PortHit[] = []
  for (const file of walk(srcRoot)) {
    if (!/\.(ts|vue)$/.test(file)) continue
    const rel = relative(uiRoot, file).replace(/\\/g, '/')
    for (const line of readText(file).split(/\r?\n/)) {
      if (/https?:\/\//.test(line)) hits.push({ file: rel, text: line })
    }
  }
  return hits
}

function isWhitelistedUrl(hit: PortHit): boolean {
  return keyPages.static_bypass.absolute_url_whitelist.some(
    (entry) => hit.file.endsWith(entry.path) && hit.text.includes(entry.line_contains),
  )
}

describe('S6-T5-1: L3-2 冒烟基座（fixture 同源）', () => {
  it('key-pages.json 为 Q-FE-4b 关键页 9 页的唯一事实源', () => {
    expect(keyPages.source).toBe('Q-S6-D6')
    expect(keyPages.pages).toHaveLength(9)
    expect(keyPages.pages.map((page) => page.path)).toEqual(EXPECTED_PAGE_PATHS)
    expect(keyPages.trusted_source_header).toBe('X-Proxy-Source')
    expect(keyPages.base_url_env).toBe('OPENBASE_BASE_URL')

    for (const page of keyPages.pages) {
      // 关键页数据一律经受信通道 `/api/v1/**`，禁止旁路
      expect(page.data_endpoint.startsWith('/api/v1/')).toBe(true)
      expect(page.key_element.length).toBeGreaterThan(0)
      expect(Array.isArray(page.accept_states)).toBe(true)
    }
  })

  it('E2E 用例与冒烟脚本读取同一 fixture（Q-S6-D6 防漂移）', () => {
    expect(existsSync(PLAYWRIGHT_CONFIG)).toBe(true)
    expect(readText(PLAYWRIGHT_CONFIG)).toContain('tests/e2e')

    const e2eDir = join(uiRoot, 'tests', 'e2e')
    const specs = readdirSync(e2eDir).filter((name) => name.endsWith('.spec.ts'))
    expect(specs.length).toBeGreaterThan(0)
    for (const spec of specs) {
      expect(readText(join(e2eDir, spec))).toContain('fixtures/key-pages.json')
    }
    expect(readText(SMOKE_SCRIPT)).toContain('fixtures/key-pages.json')
  })

  it('约束：Playwright 证据归档于 doc/test/evidence/s6/ui-e2e（设计草案 §2.5）', () => {
    const config = readText(PLAYWRIGHT_CONFIG)
    expect(config).toContain('doc/test/evidence/s6/ui-e2e')
    // 证据不落 dogfood-output（该目录为不提交噪音）
    expect(config).not.toContain('dogfood-output')
  })
})

describe('S6-T5-1: 冒烟脚本受信通道约束', () => {
  it('仅经网关入口 OPENBASE_BASE_URL，且携带受信来源标识 X-Proxy-Source', () => {
    expect(existsSync(SMOKE_SCRIPT)).toBe(true)
    const script = readText(SMOKE_SCRIPT)
    expect(script).toContain('OPENBASE_BASE_URL')
    expect(script).toContain('X-Proxy-Source')
    // 零依赖：只使用 Node 原生 fetch / node: 模块
    expect(script).toContain("from 'node:")
    expect(script).not.toContain('axios')
  })

  it('evidence 归档字段齐备（openbase_commit / ui_version / status / PENDING）', () => {
    const script = readText(SMOKE_SCRIPT)
    for (const field of ['openbase_commit', 'ui_version', 'status', 'PENDING', 'l3-2-smoke.json']) {
      expect(script).toContain(field)
    }
  })
})

describe('S6-T5-1: 静态旁路检查（子系统中不直连）', () => {
  it('端口字面量仅存在于白名单（显示文案 / mock 数据），白名单外 = 0', () => {
    const hits = scanPortLiterals()
    const unexpected = hits.filter((hit) => !isWhitelisted(hit)).map((hit) => `${hit.file} :: ${hit.text.trim()}`)
    expect(unexpected).toEqual([])
    // 命中全部在白名单内（whitelist 覆盖完整，非空集）
    expect(hits.length).toBeGreaterThan(0)
    for (const hit of hits) expect(isWhitelisted(hit)).toBe(true)
  })

  it('API 客户端一律经同域 /api/v1（无绝对子系统地址）', () => {
    const httpSource = readText(join(srcRoot, 'core', 'api', 'http.ts'))
    expect(httpSource).toContain("baseURL: '/api/v1'")
    for (const file of walk(join(srcRoot, 'core', 'api'))) {
      expect(readText(file)).not.toMatch(/https?:\/\//)
    }
  })

  it('绝对 URL 字面量仅存在于白名单（示例/占位/mock 数据），白名单外 = 0', () => {
    const hits = scanAbsoluteUrls()
    const unexpected = hits.filter((hit) => !isWhitelistedUrl(hit)).map((hit) => `${hit.file} :: ${hit.text.trim()}`)
    expect(unexpected).toEqual([])
    // 网络层强判据：API 客户端目录内不得出现绝对地址
    expect(hits.filter((hit) => hit.file.startsWith('src/core/api/'))).toEqual([])
  })
})
