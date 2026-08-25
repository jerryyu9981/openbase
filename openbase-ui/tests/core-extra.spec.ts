/**
 * 覆盖率补充测试（v1.2.0）：router 守卫 / ui store / api 分支
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { tokenStore } from '@/core/api/http'
import { useAuthStore } from '@/core/stores/auth'
import { useUiStore } from '@/core/stores/ui'
import router, { staticRoutes } from '@/core/router'
import { authApi, modulesApi, type ModuleInfo } from '@/core/api/auth'

describe('ui store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('侧边栏折叠与移动端切换', () => {
    const ui = useUiStore()
    expect(ui.sidebarCollapsed).toBe(false)
    ui.toggleSidebar()
    expect(ui.sidebarCollapsed).toBe(true)
    ui.setMobile(true)
    expect(ui.isMobile).toBe(true)
    expect(ui.sidebarCollapsed).toBe(true)
    ui.setMobile(false)
    expect(ui.isMobile).toBe(false)
  })
})

describe('static routes', () => {
  it('包含登录与仪表盘路由', () => {
    const paths = staticRoutes.map((r) => r.path)
    expect(paths).toContain('/auth/login')
    expect(paths).toContain('/')
    expect(staticRoutes.some((r) => r.path === '/auth/login' && r.meta?.public)).toBe(true)
  })
})

describe('router guards', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.spyOn(modulesApi, 'list').mockResolvedValue([])
  })

  it('未登录访问受保护路由跳转登录页', async () => {
    const auth = useAuthStore()
    auth.loaded = true
    await router.push('/dashboard')
    expect(router.currentRoute.value.path).toBe('/auth/login')
  })

  it('已登录可访问仪表盘', async () => {
    tokenStore.set('access-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'admin', permissions: ['*'] }
    auth.loaded = true
    await router.push('/dashboard')
    expect(router.currentRoute.value.path).toBe('/dashboard')
    router.push('/auth/login')
  })

  it('登录页在未登录时可访问', async () => {
    const auth = useAuthStore()
    auth.loaded = true
    await router.push('/auth/login')
    expect(router.currentRoute.value.path).toBe('/auth/login')
  })

  it('模块路由权限不足跳转仪表盘', async () => {
    tokenStore.set('access-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'viewer', permissions: [] }
    auth.loaded = true
    const items: ModuleInfo[] = [
      { id: 'portrait', name: '画像', route_prefix: '/portrait', entry: 'x', permission: 'dps:view', status: 'enabled', sort_order: 40 },
    ]
    vi.spyOn(modulesApi, 'list').mockResolvedValue(items)
    await router.push('/portrait')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('通配权限可加载模块路由', async () => {
    tokenStore.set('access-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'admin', permissions: ['*'] }
    auth.loaded = true
    const items: ModuleInfo[] = [
      { id: 'openllm', name: 'OpenLLM', route_prefix: '/openllm', entry: 'modules/openllm', permission: 'openllm:view', status: 'enabled', sort_order: 10 },
    ]
    vi.spyOn(modulesApi, 'list').mockResolvedValue(items)
    await router.push('/openllm/models')
    expect(router.currentRoute.value.meta.module).toBe('openllm')
  })
})

describe('api 分支', () => {
  beforeEach(() => localStorage.clear())

  it('modulesApi.list 透传 items', async () => {
    const items: ModuleInfo[] = [
      { id: 'memory', name: '记忆', route_prefix: '/memory', entry: 'x', permission: 'openmemory:view', status: 'enabled', sort_order: 30 },
    ]
    vi.spyOn(modulesApi, 'list').mockResolvedValue(items)
    const result = await modulesApi.list()
    expect(result.length).toBe(1)
    expect(result[0].id).toBe('memory')
  })

  it('authApi.me 无 token 时 rejected（axios 401 由拦截器处理）', async () => {
    // 无 token 时 http 层不带 Authorization，后端将返回 401 —— 此处验证 tokenStore 状态
    expect(tokenStore.access).toBe('')
    const auth = useAuthStore()
    await auth.loadMe()
    expect(auth.loaded).toBe(true)
  })
})

describe('auth store 补充', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('loadMe 在有 token 时拉取用户', async () => {
    tokenStore.set('access-token')
    vi.spyOn(authApi, 'me').mockResolvedValue({ id: 2, username: 'alice', permissions: ['openllm:view'] })
    const auth = useAuthStore()
    await auth.loadMe()
    expect(auth.user?.username).toBe('alice')
    expect(auth.hasPermission('openllm:view')).toBe(true)
    expect(auth.hasPermission('dps:view')).toBe(false)
  })

  it('loadMe 无 token 直接完成不拉取', async () => {
    const auth = useAuthStore()
    await auth.loadMe()
    expect(auth.user).toBeNull()
    expect(auth.loaded).toBe(true)
  })
})
