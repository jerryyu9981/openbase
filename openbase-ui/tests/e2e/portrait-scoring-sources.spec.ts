/**
 * P1 评分项来源提示走查（headless Chromium 固定视口）
 *
 * 背景：TRAE 内置浏览器在部分环境回报 "Browser viewport is not ready"（零尺寸视口），
 * 导致人工走查超时。本用例改用 Playwright headless + 显式 `setViewportSize`，
 * 使走查可重复执行且不依赖 IDE 浏览器面板。
 *
 * 覆盖（治理方案 v1.1.x §12.4）：
 *   1) 画像详情页可选计算口径模板并打开「查看评分项」弹窗；
 *   2) 弹窗渲染 6 个维度区块；
 *   3) 至少一个维度展示「标注来源」标签；
 *   4) `crime` / `social` 无标注来源时出现警示，且对应维度带「无标注来源」标签；
 *   5) 页面无 pageerror / console.error。
 *
 * 登录态：用例内部调用 `/api/v1/auth/login` 获取 token，按 `ob_access_token` 键注入
 * localStorage（与 `src/core/api/http.ts` 一致），无需人工准备 token。
 */
import { expect, test, type Page, type APIRequestContext } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = resolve(HERE, '../../../doc/test/evidence/s6/ui-e2e')
const FALLBACK_PERSON_ID = 'tenant-1_1'
const TARGET_TEMPLATE = 'cor-persona-risk-v1'

async function loginToken(request: APIRequestContext): Promise<string> {
  const response = await request.post('/api/v1/auth/login', {
    data: { username: 'admin', password: 'admin123' },
  })
  expect(response.ok(), `登录失败: ${response.status()}`).toBeTruthy()
  const payload = (await response.json()) as { access_token?: string }
  expect(payload.access_token, '登录响应缺少 access_token').toBeTruthy()
  return payload.access_token as string
}

async function firstPersonId(request: APIRequestContext, token: string): Promise<string> {
  const response = await request.get('/api/v1/dps-proxy/portraits?page=1&page_size=5', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok()) return FALLBACK_PERSON_ID
  const payload = (await response.json()) as { data?: { items?: Array<{ person_id?: string }> } }
  const personId = payload.data?.items?.find((item) => item.person_id)?.person_id
  return personId || FALLBACK_PERSON_ID
}

async function seedAuth(page: Page, token: string): Promise<void> {
  await page.addInitScript((access: string) => {
    window.localStorage.setItem('ob_access_token', access)
  }, token)
}

test('画像评分项弹窗展示维度标注来源与 crime/social 缺口', async ({ page, request }) => {
  const errors: string[] = []
  const badResponses: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    // 资源 404 由下方 badResponses 精确记录（可区分 favicon 等无关资源）
    if (message.type() === 'error' && !message.text().includes('Failed to load resource')) {
      errors.push(message.text())
    }
  })
  page.on('response', (response) => {
    if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`)
  })
  // 显式视口：绕开 IDE 内置浏览器"零尺寸视口"超时
  await page.setViewportSize({ width: 1440, height: 900 })

  const token = await loginToken(request)
  const personId = await firstPersonId(request, token)
  await seedAuth(page, token)

  await page.goto(`/portrait/${personId}`, { waitUntil: 'domcontentloaded' })
  const scoringButton = page.locator('[data-test="portrait-scoring-items"]')
  await expect(scoringButton).toBeVisible({ timeout: 20000 })

  // 选择模板口径（默认口径下按钮禁用）
  await page.locator('[data-test="portrait-template-select"]').click()
  await page
    .locator('.el-select-dropdown__item', { hasText: TARGET_TEMPLATE })
    .first()
    .click()
  await expect(scoringButton).toBeEnabled({ timeout: 10000 })
  await scoringButton.click()

  const dialog = page.locator('[data-test="portrait-scoring-dialog"]')
  await expect(dialog).toBeVisible({ timeout: 20000 })
  await expect(dialog.locator('.scoring-dim')).toHaveCount(6, { timeout: 20000 })

  // 有来源维度：绿色「标注来源」标签
  const sourceTags = dialog.locator('[data-test="scoring-source-tag"]')
  await expect(sourceTags.first()).toBeVisible()
  expect(await sourceTags.count()).toBeGreaterThanOrEqual(1)

  // 无来源维度：顶部警示 + 维度内「无标注来源」标签（crime / social）
  const gapAlert = dialog.locator('[data-test="scoring-source-gap"]')
  await expect(gapAlert).toBeVisible()
  await expect(gapAlert).toContainText('crime')
  await expect(gapAlert).toContainText('social')
  await expect(dialog.locator('[data-test="scoring-source-gap-tag"]')).toHaveCount(2)

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await dialog.screenshot({
    path: resolve(EVIDENCE_DIR, 'p1-scoring-sources-dialog.png'),
  })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  // 受控 404：favicon 等静态资源；`?template_code=` 口径结果未计算（页面按"尚未计算"空态处理）
  const controlled404 = /favicon|\/dps-proxy\/portraits\/[^/]+\?template_code=/
  const unexpected = badResponses.filter((entry) => !controlled404.test(entry))
  expect(unexpected, `存在失败请求: ${unexpected.join(' | ')}`).toEqual([])
})
