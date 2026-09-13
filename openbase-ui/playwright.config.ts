/**
 * S6-T5-2 Playwright 配置（设计草案 §2.5 E2E 证据链 / §4.5 / Q-FE-4b）
 *
 * - 关键页清单同源：`tests/e2e/fixtures/key-pages.json`（Q-S6-D6）
 * - 入口：`OPENBASE_BASE_URL`（nginx 同域 `/ui/` + `/api/` 或 gateway）；默认 dev 5173 仅为本地默认值
 * - 证据归档：`doc/test/evidence/s6/ui-e2e/`（result JSON / HTML report / 失败截图与 trace），
 *   统一落 `doc/test/evidence/**`，不使用其余临时输出目录
 *
 * 执行面说明：浏览器二进制与四子系统运行态在沙箱内不可得 → 执行结果登记 PENDING（B1），
 * 本配置与用例代码为**可复核交付物**，由非沙箱环境执行回填。
 */
import { defineConfig, devices } from '@playwright/test'

const EVIDENCE_DIR = '../doc/test/evidence/s6/ui-e2e'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  // AD-FE-2（2026-09-13）：本地默认同样固定单 worker。9 页并行时与 CPU 推理型上游争抢资源，
  // 关键元素偶发超出 15s 轮询预算且失败页在多次运行间漂移（实测多 worker：2~4 分钟、8/9）；
  // 串行执行 9 页 13.0s 全绿且可复现。需要并行压测时以 OPENBASE_E2E_WORKERS 显式覆盖。
  workers: Number(process.env.OPENBASE_E2E_WORKERS || 1),
  timeout: 30000,
  expect: { timeout: 10000 },
  reporter: [
    ['list'],
    ['json', { outputFile: `${EVIDENCE_DIR}/results.json` }],
    ['html', { outputFolder: `${EVIDENCE_DIR}/report`, open: 'never' }],
  ],
  outputDir: `${EVIDENCE_DIR}/artifacts`,
  use: {
    baseURL: process.env.OPENBASE_BASE_URL || 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
