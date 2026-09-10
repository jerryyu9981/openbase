/**
 * S6-T5-2 关键页 E2E 断言支持（设计草案 §4.5 S6-T5-2 / §5.4 / Q-FE-4b）
 *
 * 关键页 PASS 判据（逐页）：
 *   1) 页面渲染（导航成功、非白屏）；
 *   2) 关键元素可见（`key_element` 或 `accept_states` 受控空态之一可见）；
 *   3) 无渲染兜底触发（`[data-test="layout-render-fallback"]` 计数为 0）；
 *   4) 无 `pageerror`、无 console error；
 *   5) 无 console warn（Q-FE-4b：浏览器层 `console.warn` = 0）。
 *
 * 登录态：由环境变量 `OPENBASE_ACCESS_TOKEN`（可选 `OPENBASE_REFRESH_TOKEN`）注入 localStorage，
 * 与 `src/core/api/http.ts` 的 `ob_access_token` / `ob_refresh_token` 键一致；测试自身不产 token。
 */
import { expect, type Page } from '@playwright/test'

export interface KeyPageDef {
  id: string
  module: string
  name: string
  path: string
  sample_id?: string
  key_element: string
  accept_states: string[]
}

/** 渲染兜底锚点（App.vue/AppLayout.vue `onErrorCaptured`，防白屏） */
export const RENDER_FALLBACK_SELECTOR = '[data-test="layout-render-fallback"]'

/** 注入受控环境登录态（无 token 则不注入，由环境自行处理） */
export async function seedAuthState(page: Page): Promise<void> {
  const accessToken = process.env.OPENBASE_ACCESS_TOKEN
  if (!accessToken) return
  const refreshToken = process.env.OPENBASE_REFRESH_TOKEN || ''
  await page.addInitScript(
    ([access, refresh]: [string, string]) => {
      window.localStorage.setItem('ob_access_token', access)
      if (refresh) window.localStorage.setItem('ob_refresh_token', refresh)
    },
    [accessToken, refreshToken] as [string, string],
  )
}

/** 解析详情页样例路径（`:id` → fixture `sample_id`） */
export function resolvePagePath(pageDef: KeyPageDef): string {
  return pageDef.sample_id ? pageDef.path.replace(':id', pageDef.sample_id) : pageDef.path
}

/** 关键页 PASS 断言（9 页共用口径） */
export async function assertKeyPage(page: Page, pageDef: KeyPageDef): Promise<void> {
  const consoleErrors: string[] = []
  const consoleWarns: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
    if (message.type() === 'warning') consoleWarns.push(message.text())
  })
  page.on('pageerror', (error) => pageErrors.push(error.message))

  const target = resolvePagePath(pageDef)
  const response = await page.goto(target, { waitUntil: 'domcontentloaded' })
  expect(response).not.toBeNull()

  const candidates = [pageDef.key_element, ...pageDef.accept_states]
  await expect
    .poll(
      async () => {
        for (const selector of candidates) {
          const visible = await page
            .locator(selector)
            .first()
            .isVisible()
            .catch(() => false)
          if (visible) return true
        }
        return false
      },
      {
        message: `关键页 ${target} 未渲染关键元素/受控空态（期望其一：${candidates.join(' | ')}）`,
        timeout: 15000,
      },
    )
    .toBe(true)

  // 防白屏：渲染兜底不得触发
  await expect(page.locator(RENDER_FALLBACK_SELECTOR)).toHaveCount(0)

  // Q-FE-4b：无 pageerror / console.error / console.warn
  expect({ pageErrors, consoleErrors, consoleWarns }).toEqual({
    pageErrors: [],
    consoleErrors: [],
    consoleWarns: [],
  })
}
