/**
 * S6-T5-2 关键页 E2E：记忆（Q-FE-4b 9 页之 2）
 * 清单同源：tests/e2e/fixtures/key-pages.json（Q-S6-D6）。执行面 = 非沙箱（B1）。
 */
import { test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { assertKeyPage, seedAuthState, type KeyPageDef } from './support/key-page'

const HERE = dirname(fileURLToPath(import.meta.url))
const keyPages = JSON.parse(readFileSync(resolve(HERE, 'fixtures/key-pages.json'), 'utf8')) as {
  pages: KeyPageDef[]
}

const memoryPages = keyPages.pages.filter((pageDef) => pageDef.module === 'memory')

test.describe('S6-T5-2 记忆关键页 PASS（Q-FE-4b）', () => {
  for (const pageDef of memoryPages) {
    test(`${pageDef.name} ${pageDef.path} 渲染且无渲染兜底/无 console error/warn`, async ({ page }) => {
      await seedAuthState(page)
      await assertKeyPage(page, pageDef)
    })
  }
})
