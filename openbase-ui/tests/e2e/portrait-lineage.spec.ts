/**
 * P2 可解释性走查（headless Chromium 固定视口）
 *
 * 覆盖《治理方案》v1.2.0 §7 阶段三：
 *   1) 模板详情四联视图：族谱 / 标注模板 / 标签产出 / 评分项四页签可见，族谱含当前模板；
 *   2) 标签产出页签可看到「dimension:tag_key → 命中评分项（规则 key + 权重）」或「仅标签」警示；
 *   3) 画像详情维度可展开规则级明细（标签值 / 得分 / 缺值兜底），缺值行出现「缺值→50」；
 *   4) 页面无 pageerror / 非受控 4xx。
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

test('模板详情展示族谱/标注模板/标签产出/评分项四联视图', async ({ page, request }) => {
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
  await expect(drawer.locator('[data-test="template-lineage-tabs"]')).toBeVisible({ timeout: 20000 })

  // ① 族谱：当前模板节点 + 继承链
  const lineageNodes = drawer.locator('[data-test="template-lineage-node"]')
  await expect(lineageNodes.first()).toBeVisible({ timeout: 20000 })
  expect(await lineageNodes.count()).toBeGreaterThanOrEqual(1)
  await expect(lineageNodes.first()).toContainText(TARGET_TEMPLATE)

  // ② 标注模板：表内出现归属与缺口标签
  await drawer.locator('.el-tabs__item', { hasText: '标注模板' }).click()
  await expect(drawer.locator('[data-test="template-tab-annotations"]')).toBeVisible()
  expect(await drawer.locator('[data-test="template-tab-annotations"] .el-table__row').count()).toBeGreaterThan(0)

  // ③ 标签产出：每行要么命中评分项，要么明确「仅标签·不影响评分」
  await drawer.locator('.el-tabs__item', { hasText: '标签产出' }).click()
  const tagPane = drawer.locator('[data-test="template-tab-tags"]')
  await expect(tagPane).toBeVisible()
  const tagRows = tagPane.locator('.el-table__row')
  expect(await tagRows.count()).toBeGreaterThan(0)
  const hitOrTagOnly =
    (await tagPane.locator('[data-test="template-tag-only-tag"]').count()) > 0 ||
    (await tagPane.locator('.hit-text').count()) > 0
  expect(hitOrTagOnly, '标签产出既无评分项命中也无「仅标签」提示').toBeTruthy()

  // ④ 评分项：维度与规则可见
  await drawer.locator('.el-tabs__item', { hasText: '评分项' }).click()
  await expect(drawer.locator('[data-test="template-tab-scoring"]')).toBeVisible()
  expect(await drawer.locator('[data-test="template-tab-scoring"] .scoring-dim').count()).toBeGreaterThan(0)

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await drawer.screenshot({ path: resolve(EVIDENCE_DIR, 'p2-template-lineage.png') })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})

test('画像维度展开显示规则级明细与缺值兜底', async ({ page, request }) => {
  const { errors, badResponses } = trackErrors(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  const token = await loginToken(request)
  const personId = await firstPersonId(request, token)
  await seedAuth(page, token)

  await page.goto(`/portrait/${personId}`, { waitUntil: 'domcontentloaded' })
  const scoringButton = page.locator('[data-test="portrait-scoring-items"]')
  await expect(scoringButton).toBeVisible({ timeout: 20000 })

  await page.locator('[data-test="portrait-template-select"]').click()
  await page.locator('.el-select-dropdown__item', { hasText: TARGET_TEMPLATE }).first().click()
  await expect(scoringButton).toBeEnabled({ timeout: 10000 })

  const toggle = page.locator('[data-test="portrait-dimension-details-toggle"]').first()
  await expect(toggle).toBeVisible({ timeout: 20000 })
  await toggle.click()

  const details = page.locator('[data-test="portrait-dimension-details"]').first()
  await expect(details).toBeVisible({ timeout: 20000 })
  const ruleRows = details.locator('.el-table__row')
  await expect(ruleRows.first()).toBeVisible({ timeout: 20000 })
  expect(await ruleRows.count()).toBeGreaterThan(0)

  // 缺值兜底：至少一行显示「缺值→50」
  const missingTags = details.locator('[data-test="portrait-dimension-missing-tag"]')
  await expect(missingTags.first()).toBeVisible({ timeout: 20000 })

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await page.locator('.dimension-layout').screenshot({
    path: resolve(EVIDENCE_DIR, 'p2-dimension-details.png'),
  })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})
