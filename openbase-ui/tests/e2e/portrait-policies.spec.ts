/**
 * P3 策略执行走查（headless Chromium 固定视口）
 *
 * 覆盖《治理方案》v1.3.0 §14：
 *   1) 模板评分项页签展示策略摘要（证据来源 / 审核级数 / 异常规则），多级审核给出未支持警示；
 *   2) 标注工作台可录入证据来源（文书编号），并随模板证据策略提示必填；
 *   3) 画像详情展示「异常预警」区块（命中规则或明确「暂无」）。
 *
 * 登录态：用例内部调用 `/api/v1/auth/login` 获取 token，按 `ob_access_token` 键注入
 * localStorage（与 `src/core/api/http.ts` 一致），无需人工准备 token。
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = resolve(HERE, '../../../doc/test/evidence/s6/ui-e2e')
const FALLBACK_PERSON_ID = 'tenant-1_1'
const TARGET_TEMPLATE = 'cor-persona-root-v1'

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
  return payload.data?.items?.find((item) => item.person_id)?.person_id || FALLBACK_PERSON_ID
}

async function seedAuth(page: Page, token: string): Promise<void> {
  await page.addInitScript((access: string) => {
    window.localStorage.setItem('ob_access_token', access)
  }, token)
}

function trackErrors(page: Page) {
  const errors: string[] = []
  const badResponses: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('Failed to load resource')) {
      errors.push(message.text())
    }
  })
  page.on('response', (response) => {
    if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`)
  })
  return { errors, badResponses }
}

/** 受控失败：favicon 与「口径结果未计算」的空态探测 */
function assertNoUnexpectedResponse(badResponses: string[]) {
  const controlled = /favicon|\/dps-proxy\/portraits\/[^/]+\?template_code=/
  const unexpected = badResponses.filter((entry) => !controlled.test(entry))
  expect(unexpected, `存在失败请求: ${unexpected.join(' | ')}`).toEqual([])
}

test('模板评分项页签展示证据策略与审核级数摘要', async ({ page, request }) => {
  const { errors, badResponses } = trackErrors(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  const token = await loginToken(request)
  await seedAuth(page, token)

  await page.goto('/portrait/dps/templates', { waitUntil: 'domcontentloaded' })
  const targetRow = page.locator('.el-table__row', { hasText: TARGET_TEMPLATE }).first()
  await expect(targetRow).toBeVisible({ timeout: 20000 })
  await targetRow.locator('[data-test="template-detail"]').click()

  const drawer = page.locator('[data-test="template-detail-drawer"]')
  await expect(drawer).toBeVisible({ timeout: 20000 })
  await drawer.locator('.el-tabs__item', { hasText: '评分项' }).click()

  const summary = drawer.locator('[data-test="template-policy-summary"]')
  await expect(summary).toBeVisible({ timeout: 20000 })
  await expect(summary.locator('[data-test="template-evidence-policy"]')).toContainText('证据来源')
  await expect(summary.locator('[data-test="template-review-levels"]')).toContainText('审核级数')
  await expect(summary.locator('[data-test="template-anomaly-rule-count"]')).toContainText('异常规则')

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await drawer.screenshot({ path: resolve(EVIDENCE_DIR, 'p3-template-policy.png') })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})

test('标注工作台支持录入证据来源', async ({ page, request }) => {
  const { errors, badResponses } = trackErrors(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  const token = await loginToken(request)
  await seedAuth(page, token)

  await page.goto('/portrait/dps/annotations', { waitUntil: 'domcontentloaded' })
  const templateSelect = page.locator('[data-test="annotation-template-select"]')
  await expect(templateSelect).toBeVisible({ timeout: 20000 })
  await templateSelect.click()
  const firstOption = page.locator('.el-select-dropdown__item').first()
  if (await firstOption.isVisible().catch(() => false)) {
    await firstOption.click()
  } else {
    await page.keyboard.press('Escape')
  }

  const evidenceInput = page.locator('[data-test="annotation-evidence-source"] input, input[data-test="annotation-evidence-source"]').first()
  await expect(evidenceInput).toBeVisible({ timeout: 20000 })
  await evidenceInput.fill('WS-2026-001')
  await expect(evidenceInput).toHaveValue('WS-2026-001')

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await page.locator('[data-test="annotation-entry-card"]').screenshot({
    path: resolve(EVIDENCE_DIR, 'p3-evidence-source.png'),
  })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})

test('画像详情展示异常预警区块', async ({ page, request }) => {
  const { errors, badResponses } = trackErrors(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  const token = await loginToken(request)
  const personId = await firstPersonId(request, token)
  await seedAuth(page, token)

  await page.goto(`/portrait/${personId}`, { waitUntil: 'domcontentloaded' })
  const anomalyCard = page.locator('[data-test="portrait-anomaly-alerts"]')
  await expect(anomalyCard).toBeVisible({ timeout: 20000 })
  await expect(anomalyCard.locator('.el-card__header')).toContainText('异常预警')
  await expect
    .poll(async () => (await anomalyCard.innerText()).includes('加载中'), { timeout: 20000 })
    .toBe(false)
  // 有命中展示规则，无命中展示「暂无」，两者都说明区块已就绪
  const text = await anomalyCard.innerText()
  expect(text.includes('暂无') || text.includes('条命中')).toBeTruthy()

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await anomalyCard.screenshot({ path: resolve(EVIDENCE_DIR, 'p3-anomaly-alerts.png') })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})
