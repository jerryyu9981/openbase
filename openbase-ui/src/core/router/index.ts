import { createRouter, createWebHistory, type RouteRecordRaw, type Router, type RouterHistory } from 'vue-router'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { tokenStore } from '@/core/api/http'
import { registerLoginNavigator } from '@/core/api/redirect'
import { platformRoutes } from '@/pages/platform/routes'
import { personalRoutes } from '@/pages/personal/routes'
import { legacyRedirectRoutes } from '@/core/router/legacyRedirects'

/**
 * DPS 模板化 12 页路由（v1.4.10 §2；页面落点 `modules/portrait/pages/Dps*View.vue`）。
 *
 * 页面↔端点映射 100%（22 端点 ↔ 12 页面，TD-1410-23／AC-18）：
 *  - P-01 模板族管理 ↔ #11 #12 #15 #16
 *  - P-02 版本对比与回滚 ↔ #3 #4
 *  - P-03 预检与影响面 ↔ #5 #7
 *  - P-04 包导出／导入 ↔ #1 #2
 *  - P-05 血缘反查与影响面 ↔ #6 #7
 *  - P-06 措施建议 ↔ #8
 *  - P-07 评分类型 ↔ #10
 *  - P-08 AI 标注候选与复核 ↔ #9（＋ llm_proxy／chat ＋ DPS review）
 *  - P-09 画像模板新建／编辑 ↔ #12 #13 #14（`new` 与 `:code/edit` 同页两路径）
 *  - P-10 标注模板管理 ↔ #17 #18 #19 #21
 *  - P-11 标注模板字段与归属 ↔ #12 #18 #20
 *  - P-12 标签体系查看 ↔ #21 #22
 *
 * 路由顺序：静态段（/dps/templates/new、/dps/template-packages、/dps/lineage…）先于同名动态段，
 * 避免被 `:code` 吞并（沿用既有模块内静态先于动态的注册口径）。
 */
const dpsRoutes: RouteRecordRaw[] = [
  { path: 'dps/templates', name: 'dps-template-list', component: () => import('@/modules/portrait/pages/DpsTemplateListView.vue'), meta: { title: '模板族管理' } },
  // P-09：新建与编辑同页；`new` 与 `:code/edit` 为两条路径（同一页面组件）
  { path: 'dps/templates/new', name: 'dps-template-new', component: () => import('@/modules/portrait/pages/DpsTemplateEditView.vue'), meta: { title: '画像模板新建' } },
  { path: 'dps/templates/:code/edit', name: 'dps-template-edit', component: () => import('@/modules/portrait/pages/DpsTemplateEditView.vue'), meta: { title: '画像模板编辑' } },
  { path: 'dps/templates/:code/versions', name: 'dps-template-versions', component: () => import('@/modules/portrait/pages/DpsTemplateVersionView.vue'), meta: { title: '版本对比与回滚' } },
  { path: 'dps/templates/:code/preflight', name: 'dps-template-preflight', component: () => import('@/modules/portrait/pages/DpsTemplatePreflightView.vue'), meta: { title: '预检与影响面' } },
  { path: 'dps/template-packages', name: 'dps-template-packages', component: () => import('@/modules/portrait/pages/DpsTemplatePackageView.vue'), meta: { title: '模板包导出／导入' } },
  { path: 'dps/lineage', name: 'dps-lineage', component: () => import('@/modules/portrait/pages/DpsLineageView.vue'), meta: { title: '标签血缘反查' } },
  { path: 'dps/measures', name: 'dps-measures', component: () => import('@/modules/portrait/pages/DpsMeasureView.vue'), meta: { title: '措施建议' } },
  { path: 'dps/scoring-types', name: 'dps-scoring-types', component: () => import('@/modules/portrait/pages/DpsScoringTypeView.vue'), meta: { title: '评分类型' } },
  { path: 'dps/annotation-adapters', name: 'dps-annotation-adapters', component: () => import('@/modules/portrait/pages/DpsAnnotationAdapterView.vue'), meta: { title: 'AI 标注候选与复核' } },
  { path: 'dps/annotation-templates', name: 'dps-annotation-templates', component: () => import('@/modules/portrait/pages/DpsAnnotationTemplateView.vue'), meta: { title: '标注模板管理' } },
  { path: 'dps/annotation-templates/:code/fields', name: 'dps-annotation-fields', component: () => import('@/modules/portrait/pages/DpsAnnotationFieldView.vue'), meta: { title: '标注模板字段与归属' } },
  { path: 'dps/tags', name: 'dps-tags', component: () => import('@/modules/portrait/pages/DpsTagSystemView.vue'), meta: { title: '标签体系查看' } },
]

/**
 * 平台管理四域 + 个人 + DPS 模板化 路由（v1.4.6 IA 重构，ADR-146-08；v1.4.10 追加 DPS 路由）
 * 作为 `/` AppLayout 子路由。与业务模块路由平行；不受单一模块启停影响（AC-146-10-2）。
 * DPS 路由：设计 §2 的 **12 条**（P-09 由 `new`／`:code/edit` **两条路径**承载，同一页面组件）。
 * 旧 `/system/**` 已迁出，交由 legacyRedirectRoutes 顶层承接（禁 404）。
 */
const appChildren: RouteRecordRaw[] = [
  { path: 'dashboard', name: 'dashboard', component: () => import('@/pages/Dashboard.vue'), meta: { title: '仪表盘', icon: 'Odometer' } },
  ...dpsRoutes,
  ...platformRoutes,
  ...personalRoutes,
]

/** 公共静态路由 */
export const staticRoutes: RouteRecordRaw[] = [
  { path: '/auth/login', name: 'login', component: () => import('@/pages/Login.vue'), meta: { public: true } },
  { path: '/auth/oidc/callback', name: 'oidc-callback', component: () => import('@/pages/OidcCallback.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/core/layouts/AppLayout.vue'),
    redirect: '/dashboard',
    children: appChildren,
  },
  // 权限 403 页（平台权限门禁见 guard；无权限跳此页，不回退 /dashboard —— §3.2 ③）
  { path: '/forbidden', name: 'forbidden', component: () => import('@/pages/Forbidden.vue'), meta: { title: '无权限访问' } },
  // 旧路径重定向（顶层承接，禁 404；保留 query/hash，ADR-146-08 §3.1/§3.3）
  ...legacyRedirectRoutes,
]

/** 模块路由表注册（模块 index.ts 导出 routes + navItems，实现路由级懒加载与页内导航，RT-203）。
 * v1.4.6：`gateway` 整体迁入平台管理「可观测与审计」域（ADR-146-08），不再作为业务模块装载。 */
const moduleRouteLoaders: Record<string, () => Promise<{ routes: RouteRecordRaw[]; navItems?: unknown[] }>> = {
  openllm: () => import('@/modules/openllm'),
  knowledge: () => import('@/modules/knowledge'),
  memory: () => import('@/modules/memory'),
  portrait: () => import('@/modules/portrait'),
}

/**
 * 检出子路由越权声明 `meta.navItems` 的条目（S6-T2 设计说明 5 / R-6）。
 *
 * Vue Router 的 `route.meta` 为 matched 链 shallow merge（后者覆盖），
 * 子路由若声明同名 `navItems` 将覆盖父级模块导航 → 模块内导航消失。
 * 该检查在「装载期告警」与「测试期断言」双处使用（子路由禁声明 navItems）。
 */
export function findNavItemsOverrides(routes: RouteRecordRaw[]): string[] {
  return routes
    .filter((route) => route.meta?.navItems !== undefined)
    .map((route) => String(route.path))
}

export interface AppRouterBundle {
  router: Router
  mountModuleRoutes: () => Promise<void>
}

/**
 * 构建应用路由器（可注入 history，便于以 `createMemoryHistory` 做无浏览器回归）。
 *
 * 关键机制（S6 设计草案 §2.2）：模块路由装载**幂等必达**——
 * 守卫内无条件调用 `mountModuleRoutes()`，以 `module.loaded` 与 `router.hasRoute(moduleId)`
 * 双条件跳过重复装载，修复「注册表已初始化但路由未装载 → 深链丢上下文回 /dashboard」。
 */
export function createAppRouter(history: RouterHistory = createWebHistory()): AppRouterBundle {
  const router = createRouter({ history, routes: staticRoutes })

  // 401 会话失效收敛：SPA 内 replace 到登录页并保留站内回跳（R-7 口径，替代整页跳转）
  registerLoginNavigator((target) => {
    void router.replace({ path: target.path, query: target.query })
  })

  /** 挂载已启用模块的路由（模块布局承载板块导航 + AppLayout 外层）；幂等、可重试 */
  async function mountModuleRoutes(): Promise<void> {
    const registry = useModuleRegistry()
    for (const module of registry.enabledModules) {
      const loader = moduleRouteLoaders[module.info.id]
      if (!loader) continue
      // 幂等：路由表已注册 → 补标记并跳过（连续调用不重复注册、不触发重名告警）
      if (router.hasRoute(module.info.id)) {
        module.loaded = true
        continue
      }
      try {
        const { routes, navItems } = await loader()
        const overrides = findNavItemsOverrides(routes)
        if (overrides.length > 0) {
          console.warn(
            `[module:${module.info.id}] 子路由不得声明 navItems（覆盖父级导航），已检出：${overrides.join(', ')}`,
          )
        }
        // P2-3 连带（UI-E2E #4 父路由告警）：顶层挂载命名父路由，避免 `Parent route "" not found`。
        // 空路径子路由（模块根 redirect）须显式命名，否则命名父路由会触发
        // `has a child without a name and an empty path` 告警（S6-T2-4 要求 console.warn = 0）。
        router.addRoute({
          name: module.info.id,
          path: module.info.route_prefix,
          component: () => import('@/core/layouts/ModuleLayout.vue'),
          meta: { module: module.info.id, title: module.info.name, icon: module.info.icon, navItems },
          children: routes.map((route, index) => ({
            ...route,
            name: route.name ?? (route.path === '' ? `${module.info.id}-root-${index}` : undefined),
            meta: { ...route.meta, module: module.info.id },
          })),
        })
        module.loaded = true
      } catch (error) {
        console.error(`[module:${module.info.id}] route load failed`, error)
        module.loaded = false
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
    if (!registry.initialized) await registry.init(auth.permissions)
    // 幂等必达：无论 init 是否刚刚执行，都尝试装载（修复「单次装载门」导致深链丢上下文）
    await mountModuleRoutes()
    // 模块路由刚注册：若当前导航是注册前解析的（matched 为空）且现在可匹配 → 重导
    const resolved = router.resolve(to.fullPath)
    if (resolved.matched.length > 0 && to.matched.length === 0) {
      return { path: to.fullPath, replace: true }
    }
    if (to.matched.length === 0) return { path: '/dashboard' }
    // 平台权限门禁（§3.2 ③）：`meta.permission` 路由无权限 → 403 页（不回退 /dashboard）。
    // 权限码与菜单可见性（AppLayout）同源，避免「菜单可见但接口 403」割裂。
    const perm = to.meta.permission as string | undefined
    if (perm && !(auth.permissions.includes('*') || auth.permissions.includes(perm))) {
      return { path: '/forbidden', query: to.path !== '/forbidden' ? { from: to.fullPath } : undefined }
    }
    const moduleId = to.meta.module as string | undefined
    if (moduleId) {
      const found = registry.enabledModules.find((m) => m.info.id === moduleId)
      if (!found) return { path: '/dashboard' }
      const allowed = auth.permissions.includes('*') || auth.permissions.includes(found.info.permission)
      if (!allowed) return { path: '/dashboard' }
    }
    return true
  })

  return { router, mountModuleRoutes }
}

const defaultBundle = createAppRouter()

export const mountModuleRoutes = defaultBundle.mountModuleRoutes
export default defaultBundle.router

/**
 * 应用启动预热：在 `app.use(router)` 触发首帧导航**之前**完成模块路由装载。
 *
 * F-4 / Q-FE-4b：vue-router 在首帧 `router.resolve`（`pushWithRedirect` 内）即对未匹配
 * location 发出 `[Vue Router warn] No match found for location with path …`。该解析发生在
 * `beforeEach` 守卫之前，守卫内的幂等 `mountModuleRoutes()` 无法挽回已产生的告警——
 * 直访深链（E2E `page.goto` / 刷新 / 书签）必然告警。故在安装路由器前先做一次预热装载，
 * 使首帧解析即可命中，从根因消除告警（不放宽 `console.warn=0` 判据、不屏蔽告警）。
 *
 * - 无登录态：直接返回（公共路由 `staticRoutes` 已足够，不触碰模块 API）；
 * - 幂等：`registry.init` / `mountModuleRoutes` 自带幂等（`initialized` / `loaded` 双条件），
 *   重复调用不重复注册；守卫在导航时仍会按幂等语义兜底重试；
 * - 失败不阻断启动：预热异常只记录，交由守卫在导航阶段重试装载。
 *
 * @param bundle 目标路由集合（默认单例；测试可注入 `createMemoryHistory` 实例）
 */
export async function bootstrapModuleRoutes(
  bundle: AppRouterBundle = defaultBundle,
): Promise<void> {
  if (!tokenStore.access) return
  try {
    const auth = useAuthStore()
    if (!auth.loaded) await auth.loadMe()
    const registry = useModuleRegistry()
    if (!registry.initialized) await registry.init(auth.permissions)
    await bundle.mountModuleRoutes()
  } catch (error) {
    // 预热失败不阻断启动：守卫在导航时按幂等语义重试装载（无需在此告警，避免污染 console）
    console.debug('[router] module route bootstrap skipped', error)
  }
}
