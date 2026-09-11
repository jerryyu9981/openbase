import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router, { bootstrapModuleRoutes } from './core/router'
import './core/styles/tokens.css'

const app = createApp(App)
app.use(createPinia())

/**
 * F-4（Q-FE-4b）：在安装路由器（触发首帧导航）前预热模块路由，
 * 使深链首帧 `router.resolve` 即命中，消除 `[Vue Router warn] No match found`。
 * 失败不阻断启动（内部兜底），守卫仍按幂等语义重试。
 */
void bootstrapModuleRoutes().finally(() => {
  app.use(router)
  app.use(ElementPlus, { locale: zhCn })
  app.mount('#app')
})
