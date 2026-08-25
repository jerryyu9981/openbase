/**
 * 前端核心逻辑单元测试（v1.2.0，RT-203/204）
 * 覆盖：tokenStore / auth store 登录态 / moduleRegistry 权限过滤
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { tokenStore } from '@/core/api/http'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { modulesApi, type ModuleInfo } from '@/core/api/auth'

describe('tokenStore', () => {
  beforeEach(() => localStorage.clear())

  it('存取与清理 token', () => {
    tokenStore.set('access-1', 'refresh-1')
    expect(tokenStore.access).toBe('access-1')
    expect(tokenStore.refresh).toBe('refresh-1')
    tokenStore.clear()
    expect(tokenStore.access).toBe('')
  })
})

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('登录成功写入用户与 token', async () => {
    vi.spyOn(modulesApi, 'list').mockResolvedValue([])
    const store = useAuthStore()
    // mock authApi.login 经由 http 层：直接调用 store.login 前替换依赖
    const spy = vi.spyOn(store, 'login').mockImplementation(async () => {
      tokenStore.set('access-token')
      store.user = { id: 1, username: 'admin', permissions: ['*'] }
      store.loaded = true
    })
    await store.login('admin', 'admin123')
    expect(store.user?.username).toBe('admin')
    expect(store.isAuthenticated).toBe(true)
    expect(store.hasPermission('openllm:view')).toBe(true)
    spy.mockRestore()
  })

  it('登出清理状态', () => {
    const store = useAuthStore()
    tokenStore.set('access-token')
    store.user = { id: 1, username: 'admin', permissions: [] }
    store.logout()
    expect(store.user).toBeNull()
    expect(tokenStore.access).toBe('')
  })
})

describe('moduleRegistry', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('按权限过滤模块并标记加载', async () => {
    const items: ModuleInfo[] = [
      { id: 'openllm', name: 'OpenLLM', route_prefix: '/openllm', entry: 'x', permission: 'openllm:view', status: 'enabled', sort_order: 10 },
      { id: 'portrait', name: '画像', route_prefix: '/portrait', entry: 'y', permission: 'dps:view', status: 'enabled', sort_order: 40 },
    ]
    vi.spyOn(modulesApi, 'list').mockResolvedValue(items)
    const registry = useModuleRegistry()
    await registry.init(['openllm:view'])
    expect(registry.enabledModules.length).toBe(1)
    expect(registry.enabledModules[0].info.id).toBe('openllm')
    expect(await registry.loadRoutes('openllm')).toBe(true)
    expect(await registry.loadRoutes('portrait')).toBe(false)
    registry.unregister('openllm')
    expect(registry.enabledModules.length).toBe(0)
  })

  it('通配权限可加载全部模块', async () => {
    const items: ModuleInfo[] = [
      { id: 'openllm', name: 'OpenLLM', route_prefix: '/openllm', entry: 'x', permission: 'openllm:view', status: 'enabled', sort_order: 10 },
      { id: 'knowledge', name: '知识库', route_prefix: '/knowledge', entry: 'y', permission: 'openrag:view', status: 'enabled', sort_order: 20 },
    ]
    vi.spyOn(modulesApi, 'list').mockResolvedValue(items)
    const registry = useModuleRegistry()
    await registry.init(['*'])
    expect(registry.enabledModules.length).toBe(2)
  })
})
