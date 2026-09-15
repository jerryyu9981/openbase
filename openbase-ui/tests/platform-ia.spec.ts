/**
 * v1.4.6 IA 重构路由层断言（ADR-146-05/08）
 *
 * 覆盖三条关键契约：
 *  - AC-146-14-1：legacyRedirects 全量映射「旧路径可达且落到预期新路径」（函数式 redirect 保留 query/hash）；
 *  - §3.2 ③：平台权限门禁 —— `meta.permission` 路由无权限 → 403 页（不回退 /dashboard）；
 *  - AC-146-10-2：平台四域路由为静态路由，不因单一模块启停而消失（禁 404）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, type Router, type RouteRecordRaw } from 'vue-router'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { createAppRouter } from '@/core/router'
import { LEGACY_REDIRECTS, legacyRedirectRoutes } from '@/core/router/legacyRedirects'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { useAuthStore } from '@/core/stores/auth'
import { tokenStore } from '@/core/api/http'
import { modulesApi, type ModuleInfo } from '@/core/api/auth'
import { platformRoutes } from '@/pages/platform/routes'

let pinia: Pinia

const MODULE_INFOS: ModuleInfo[] = [
  { id: 'openllm', name: 'OpenLLM', icon: 'ChatDotRound', route_prefix: '/openllm', entry: 'x', permission: 'openllm:view', status: 'enabled', sort_order: 10 },
]

function loginWith(permissions: string[]) {
  tokenStore.set('access-token')
  const auth = useAuthStore()
  auth.user = { id: 1, username: 'tester', permissions }
  auth.loaded = true
  return auth
}

async function setupRouter(permissions: string[]): Promise<Router> {
  vi.spyOn(modulesApi, 'list').mockResolvedValue(MODULE_INFOS)
  loginWith(permissions)
  const registry = useModuleRegistry()
  await registry.init(permissions)
  return createAppRouter(createMemoryHistory()).router
}

beforeEach(() => {
  localStorage.clear()
  tokenStore.clear()
  pinia = createPinia()
  setActivePinia(pinia)
  vi.restoreAllMocks()
})

describe('AC-146-14-1: 旧路径经 legacyRedirects 可达且落到预期新路径（路由表层判定）', () => {
  it('每个旧路径均为已注册顶层路由（禁 404，resolve 即可，不触发重型组件加载）', async () => {
    const router = await setupRouter(['*'])
    for (const [from] of LEGACY_REDIRECTS) {
      expect(router.resolve(from).matched.length).toBeGreaterThan(0)
    }
  })

  it('redirect 函数目标路径 = 预期新路径，且保留 query/hash', async () => {
    const router = await setupRouter(['*'])
    for (const [from, to] of LEGACY_REDIRECTS) {
      const record = router.getRoutes().find((route) => route.path === from)
      expect(record, `旧路径 ${from} 未注册`).toBeDefined()
      expect(record!.redirect, `旧路径 ${from} 非重定向`).toBeDefined()
      const redirectFn = record!.redirect as (toLocation: Record<string, unknown>) => Record<string, unknown>
      const target = redirectFn({ query: { page: '2' }, hash: '#top' })
      expect(target.path).toBe(to)
      expect(target.query).toEqual({ page: '2' })
      expect(target.hash).toBe('#top')
    }
  })

  it('端到端抽样：真实的守卫内导航落到预期新路径（轻量页）', { timeout: 60000 }, async () => {
    const router = await setupRouter(['*'])
    await router.push({ path: '/system/roles', query: { x: '1' } })
    expect(router.currentRoute.value.path).toBe('/platform/identity/roles')
    expect(router.currentRoute.value.query.x).toBe('1')
  })

  it('legacyRedirectRoutes 与纯数据映射一一对应（无重复 from）', () => {
    const froms = legacyRedirectRoutes.map((r) => r.path as string)
    expect(new Set(froms).size).toBe(froms.length)
    expect(froms).toEqual(LEGACY_REDIRECTS.map(([from]) => from))
  })
})

describe('§3.2 ③: 平台权限门禁（meta.permission ↔ 守卫同源）', () => {
  it.each([
    ['/platform/observability/logs'] as const,
    ['/platform/config/modules'] as const,
    ['/platform/observability/test-records'] as const,
  ])('无对应权限码访问 %s → 403 页（不回退 /dashboard）', async (path) => {
    const router = await setupRouter(['openllm:view']) // 无 log:read / module:manage / test:record
    await router.push(path)
    expect(router.currentRoute.value.path).toBe('/forbidden')
  })

  it('含通配权限时平台受限页可达', { timeout: 60000 }, async () => {
    const router = await setupRouter(['*'])
    await router.push('/platform/observability/logs')
    expect(router.currentRoute.value.path).toBe('/platform/observability/logs')
  })

  it('平台路由 meta.permission 与后端权限码同名（契约同源；此处断言无遗漏声明）', () => {
    const flat = (routes: RouteRecordRaw[]): RouteRecordRaw[] =>
      routes.flatMap((r) => (r.children?.length ? flat(r.children) : [r]))
    const leaves = flat(platformRoutes).filter((r) => !r.redirect)
    const permissionMeta = leaves.map((r) => [r.path, (r.meta as { permission?: string })?.permission ?? undefined] as const)
    // log:read 与 module:manage 两条受权叶子必须显式声明
    expect(permissionMeta).toContainEqual(['platform/observability/logs', 'log:read'])
    expect(permissionMeta).toContainEqual(['platform/config/modules', 'module:manage'])
  })
})

describe('AC-146-10-2: 平台四域为静态路由，不受单一模块启停影响', () => {
  it('全部模块停用后平台锚点路由仍可解析（禁 404）', async () => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue(
      MODULE_INFOS.map((m) => ({ ...m, status: 'disabled' as const })),
    )
    loginWith(['*'])
    const registry = useModuleRegistry()
    await registry.init(['*'])
    expect(registry.enabledModules).toEqual([])
    const router = createAppRouter(createMemoryHistory()).router
    for (const [from, to] of [['/system/logs', '/platform/observability/logs'], ['/system/tenants', '/platform/identity/tenants']]) {
      await router.push(from)
      expect(router.currentRoute.value.path).toBe(to)
    }
  })
})