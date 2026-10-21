import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router, { bootstrapModuleRoutes } from './core/router'
import { useModuleRegistry } from './core/stores/moduleRegistry'
import './core/styles/tokens.css'
import './core/styles/layout.css'

const app = createApp(App)
app.use(createPinia())

// v1.4.11：模块清单与 `/auth/me` 并行预取，避免两份 8s 响应串行拉长首屏
void useModuleRegistry().prefetch().catch(() => undefined)

/**
 * F-4（Q-FE-4b）：在安装路由器（触发首帧导航）前预热模块路由，
 * 使深链首帧 `router.resolve` 即命中，消除 `[Vue Router warn] No match found`。
 * 失败不阻断启动（内部兜底），守卫仍按幂等语义重试。
 *
 * v1.4.11：预热最多等待 2500ms —— 后端 `/auth/me`、`/modules` 慢时（实测可达 8s+）
 * 不再阻塞首帧，先挂载骨架页，模块路由由守卫在导航阶段继续装载，避免长时间白屏。
 */
const BOOTSTRAP_MAX_WAIT_MS = 2500
const bootstrap = bootstrapModuleRoutes().catch(() => undefined)
const bootstrapDeadline = new Promise<void>((resolve) => {
  window.setTimeout(resolve, BOOTSTRAP_MAX_WAIT_MS)
})

void Promise.race([bootstrap, bootstrapDeadline]).finally(() => {
  app.use(router)
  app.use(ElementPlus, { locale: zhCn })
  app.mount('#app')
})
