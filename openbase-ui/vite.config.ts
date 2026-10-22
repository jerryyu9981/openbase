import { configDefaults, defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import type { ProxyOptions } from 'vite'
import { handleDevProxyError } from './src/core/api/devProxy'

const API_TARGET = 'http://127.0.0.1:8000'

/**
 * `/api` 开发代理（v7.8.0）：
 * 后端未就绪/重启期间，http-proxy 默认返回**空 body 的 500**，浏览器与日志会误判为
 * 服务端 5xx。统一经 `handleDevProxyError` 映射为 **503 + JSON**，与前端
 * `describeError` 的「可重试」语义一致，也便于区分「后端未起」与「后端内部错误」。
 */
export const apiProxy: Record<string, ProxyOptions> = {
  '/api': {
    target: API_TARGET,
    changeOrigin: true,
    configure: (proxy) => {
      proxy.on('error', handleDevProxyError)
    },
  },
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          echarts: ['echarts'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    port: 5173,
    proxy: apiProxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    // S6-T5：Playwright 关键页用例由 `npm run test:e2e` 执行，不计入 vitest（避免双引擎误收集）
    exclude: [...configDefaults.exclude, 'tests/e2e/**'],
    coverage: {
      provider: 'v8',
      include: ['src/core/stores/**', 'src/core/router/**', 'src/core/api/**'],
      thresholds: {
        lines: 80,
        functions: 80,
        statements: 80,
        branches: 70,
      },
    },
  },
})
