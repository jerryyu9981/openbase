import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { tokenStore } from '@/core/api/http'

/** 公共静态路由 */
export const staticRoutes: RouteRecordRaw[] = [
  { path: '/auth/login', name: 'login', component: () => import('@/pages/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/core/layouts/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/pages/Dashboard.vue'), meta: { title: '仪表盘', icon: 'Odometer' } },
    ],
  },
]

/** 模块路由表注册（模块 index.ts 导出 routes，实现路由级懒加载，RT-203） */
const moduleRouteLoaders: Record<string, () => Promise<{ routes: RouteRecordRaw[] }>> = {
  openllm: () => import('@/modules/openllm'),
  knowledge: () => import('@/modules/knowledge'),
  memory: () => import('@/modules/memory'),
  portrait: () => import('@/modules/portrait'),
}

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
})

/** 挂载已启用模块的路由（AppLayout 下） */
async function mountModuleRoutes() {
  const registry = useModuleRegistry()
  for (const module of registry.enabledModules) {
    const loader = moduleRouteLoaders[module.info.id]
    if (!loader || module.loaded) continue
    try {
      const { routes } = await loader()
      router.addRoute('', {
        path: module.info.route_prefix,
        component: () => import('@/core/layouts/AppLayout.vue'),
        meta: { module: module.info.id, title: module.info.name, icon: module.info.icon },
        children: routes.map((r) => ({ ...r, meta: { ...r.meta, module: module.info.id } })),
      })
      module.loaded = true
    } catch (error) {
      console.error(`[module:${module.info.id}] route load failed`, error)
    }
  }
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (tokenStore.access && to.path === '/auth/login') return { path: '/dashboard' }
    return true
  }
  if (!tokenStore.access) return { path: '/auth/login', query: { redirect: to.fullPath } }
  if (!auth.loaded) await auth.loadMe()
  const registry = useModuleRegistry()
  if (!registry.initialized) {
    await registry.init(auth.permissions)
    await mountModuleRoutes()
    // 模块路由刚注册：若当前导航是注册前解析的（matched 为空）且现在可匹配 → 重导
    const resolved = router.resolve(to.fullPath)
    if (resolved.matched.length > 0 && to.matched.length === 0) {
      return { path: to.fullPath, replace: true }
    }
  }
  if (to.matched.length === 0) return { path: '/dashboard' }
  const moduleId = to.meta.module as string | undefined
  if (moduleId) {
    const found = registry.enabledModules.find((m) => m.info.id === moduleId)
    if (!found) return { path: '/dashboard' }
    const allowed = auth.permissions.includes('*') || auth.permissions.includes(found.info.permission)
    if (!allowed) return { path: '/dashboard' }
  }
  return true
})

export { mountModuleRoutes }
export default router
