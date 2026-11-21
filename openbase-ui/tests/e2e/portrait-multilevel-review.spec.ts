/**
 * P4 多级审核走查（headless Chromium 固定视口）
 *
 * 覆盖《治理方案》v1.4.0 §15：
 *   1) 审核队列展示「级数」（第 N/M 级 / 已完成），按钮文案体现本级或终审；
 *   2) 审核详情「审计时间线」展示逐级留痕；
 *   3) 无 pageerror / 非受控 4xx。
 *
 * 数据策略：用 `page.route` 固定标注相关响应（模板列表 / 队列 / 留痕），使断言文案与数据
 * 完全可控、结果确定；认证与其余接口仍走真实后端。前端代理超时已于 v1.4.1 统一为 15s
 * （原 8s 收敛移除），本 stub 不再承担规避超时的职责。
 */
import { expect, test, type Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = resolve(HERE, '../../../doc/test/evidence/s6/ui-e2e')

const ANNOTATION_TEMPLATE = {
  code: 'cor-anno-basic-v1',
  name: '社区矫正对象基础属性标签层标注模板（E2E）',
  template_code: 'cor-persona-intake-v1',
  status: 'active',
  scenario: 'judicial',
  field_schema: [
    { key: 'person_id', label: '主体编号', type: 'string', required: true },
    { key: 'crisis_level', label: '风险等级', type: 'enum', required: false, options: ['一般', '紧急'] },
  ],
}

const MULTI_LEVEL_ROW = {
  id: 'anno-p4-multi-001',
  person_id: 'P4-E2E-SEED',
  person_name: '样例主体',
  annotation_template: 'cor-anno-basic-v1',
  annotation_template_name: '社区矫正对象基础属性标签层标注模板（E2E）',
  profile_template_code: 'cor-persona-intake-v1',
  fields: { person_id: 'P4-E2E-SEED', crisis_level: '紧急' },
  review_status: 'pending',
  review_level: 1,
  review_levels_required: 2,
  created_at: '2026-11-17T10:00:00+08:00',
}

const SINGLE_LEVEL_ROW = {
  ...MULTI_LEVEL_ROW,
  id: 'anno-p4-single-001',
  person_id: 'P4-E2E-SINGLE',
  review_level: 0,
  review_levels_required: 1,
}

const REVIEW_LOG_ITEMS = [
  {
    review_level: 1,
    action: 'approved',
    reviewer: 'u-e2e-1',
    comment: '一级通过',
    created_at: '2026-11-17T10:05:00+08:00',
  },
]

async function loginToken(): Promise<string> {
  const response = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'admin123' }),
  })
  expect(response.ok, `登录失败: ${response.status}`).toBeTruthy()
  const payload = (await response.json()) as { access_token?: string }
  expect(payload.access_token, '登录响应缺少 access_token').toBeTruthy()
  return payload.access_token as string
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

function assertNoUnexpectedResponse(badResponses: string[]) {
  const controlled = /favicon/
  const unexpected = badResponses.filter((entry) => !controlled.test(entry))
  expect(unexpected, `存在失败请求: ${unexpected.join(' | ')}`).toEqual([])
}

async function stubAnnotationApis(page: Page) {
  await page.route('**/api/v1/dps-proxy/annotation-templates**', (route) =>
    route.fulfill({
      json: {
        code: 0,
        message: 'success',
        data: { items: [ANNOTATION_TEMPLATE], total: 1 },
      },
    }),
  )
  await page.route('**/api/v1/dps-proxy/annotations?**', (route) =>
    route.fulfill({
      json: {
        code: 0,
        message: 'success',
        data: {
          items: [MULTI_LEVEL_ROW, SINGLE_LEVEL_ROW],
          total: 2,
          page: 1,
          page_size: 20,
        },
      },
    }),
  )
  await page.route('**/api/v1/dps-proxy/annotations/*/review-log', (route) =>
    route.fulfill({
      json: {
        code: 0,
        message: 'success',
        data: {
          annotation_id: MULTI_LEVEL_ROW.id,
          items: REVIEW_LOG_ITEMS,
          total: REVIEW_LOG_ITEMS.length,
        },
      },
    }),
  )
  // 审核详情对照所需的上游数据（A4：缺失时前端回落队列摘要，但会留下受控 404/500）
  await page.route('**/api/v1/dps-proxy/annotations/anno-p4-multi-001', (route) =>
    route.fulfill({
      json: {
        code: 0,
        message: 'success',
        data: { ...MULTI_LEVEL_ROW, values: MULTI_LEVEL_ROW.fields },
      },
    }),
  )
  await page.route('**/api/v1/dps-proxy/portraits/P4-E2E-SEED', (route) =>
    route.fulfill({
      json: {
        code: 0,
        message: 'success',
        data: { person_id: 'P4-E2E-SEED', name: '样例主体', tags: [], dimensions: [] },
      },
    }),
  )
}

async function openQueue(page: Page, token: string) {
  await stubAnnotationApis(page)
  await seedAuth(page, token)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/portrait/dps/annotations', { waitUntil: 'domcontentloaded' })
  await page.locator('[data-test="annotation-view-toggle"]').getByText('审核收件箱').click()
  await expect(page.locator('[data-test="annotation-queue-table"]')).toBeVisible({ timeout: 20000 })
  await expect(
    page.locator('[data-test="annotation-review-progress-text"]').first(),
  ).toBeVisible({ timeout: 20000 })
}

test('标注队列展示审核进度与按级审核按钮', async ({ page }) => {
  test.setTimeout(60000)
  const { errors, badResponses } = trackErrors(page)
  const token = await loginToken()
  await openQueue(page, token)

  await expect(page.locator('th', { hasText: '级数' })).toBeVisible()

  const progressCells = page.locator('[data-test="annotation-review-progress-text"]')
  await expect(progressCells.nth(0)).toHaveText('1/2')
  await expect(progressCells.nth(1)).toHaveText('0/1')

  // 多级行：本级通过后仅剩最后一级 → 终审通过；切换到单级行后按钮为「通过」
  const approve = page.locator('[data-test="annotation-approve"]')
  await expect(approve).toHaveText('终审通过')
  await page.locator('[data-test="annotation-queue-table"] tbody tr').nth(1).click()
  await expect(approve).toHaveText('通过')

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await page.locator('[data-test="annotation-queue-card"]').screenshot({
    path: resolve(EVIDENCE_DIR, 'p4-review-progress.png'),
  })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})

test('审核记录时间线展示逐级留痕', async ({ page }) => {
  test.setTimeout(60000)
  const { errors, badResponses } = trackErrors(page)
  const token = await loginToken()
  await openQueue(page, token)

  const timeline = page.locator('[data-test="annotation-timeline-card"]')
  await expect(timeline).toBeVisible({ timeout: 20000 })
  await expect(timeline).toContainText('第 1 级')
  await expect(timeline).toContainText('一级通过')
  await expect(timeline).toContainText('u-e2e-1')

  mkdirSync(EVIDENCE_DIR, { recursive: true })
  await timeline.screenshot({ path: resolve(EVIDENCE_DIR, 'p4-review-log.png') })

  expect(errors, `页面出现错误: ${errors.join(' | ')}`).toEqual([])
  assertNoUnexpectedResponse(badResponses)
})
