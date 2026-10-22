// 单页浏览器核验：导航 → 等待稳定 → 输出可见文本摘要与控制台/网络错误
// 用法：node doc/tmp/check_page.mjs <path> [selector]
import { chromium } from 'playwright'

const BASE = process.env.OPENBASE_BASE_URL || 'http://127.0.0.1:5173'
const TOKEN = process.env.OPENBASE_ACCESS_TOKEN || ''
const target = process.argv[2]
const selector = process.argv[3] || ''

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
if (TOKEN) {
  await context.addInitScript(([access]) => {
    window.localStorage.setItem('ob_access_token', access)
  }, [TOKEN])
}
const page = await context.newPage()
const errors = []
const apiCalls = []
page.on('console', (message) => {
  if (message.type() === 'error' || message.type() === 'warning') errors.push(`${message.type()}: ${message.text()}`)
})
page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
page.on('response', (response) => {
  try {
    const path = new URL(response.url()).pathname
    if (!path.startsWith('/api/')) return
    apiCalls.push(`${response.status()} ${response.request().method()} ${path}`)
    if (response.status() >= 400) errors.push(`api ${response.status()}: ${path}`)
  } catch {}
})
await page.goto(`${BASE}${target}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
await page.waitForTimeout(12000)
const text = (await page.locator('body').innerText()).replace(/\n{2,}/g, '\n').slice(0, 1400)
console.log(`URL=${page.url()}`)
console.log('--- TEXT ---')
console.log(text)
if (selector) {
  const count = await page.locator(selector).count()
  console.log(`--- SELECTOR ${selector} count=${count}`)
}
console.log('--- ERRORS ---')
console.log(errors.length ? errors.join('\n') : '(none)')
console.log('--- API CALLS ---')
console.log(apiCalls.length ? apiCalls.join('\n') : '(none)')
await browser.close()


