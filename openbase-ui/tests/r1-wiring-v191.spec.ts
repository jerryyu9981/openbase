/**
 * v1.9.1 R1：A 类三页真实化回归（用户管理 / API 密钥 / EdgeRouter）。
 * 覆盖：真实端点接线、字段映射、写动作透传、错误态、后端约束下的降级提示。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import UsersView from '@/pages/platform/identity/UsersView.vue'
import ApiKeys from '@/pages/platform/config/ApiKeys.vue'
import EdgeRouterView from '@/pages/platform/developers/EdgeRouterView.vue'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const user = (overrides: Record<string, unknown> = {}) => ({
  id: 2,
  username: 'demo-admin',
  display_name: 'Demo Admin',
  email: 'demo@example.com',
  phone: null,
  status: 1,
  tenant_id: 1,
  roles: ['org_admin'],
  ...overrides,
})

beforeEach(() => vi.clearAllMocks())

describe('v1.9.1 用户管理真实化', () => {
  it('加载 /users 并映射显示名/角色/状态', async () => {
    mocks.get.mockResolvedValue({ data: [user(), user({ id: 1, username: 'admin', display_name: '系统管理员', roles: ['admin'] })] })

    const wrapper = mountPage(UsersView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/users')
    const text = wrapper.text()
    expect(text).toContain('Demo Admin')
    expect(text).toContain('组织管理员')
    expect(text).toContain('系统管理员')
  }, 20000)

  it('停用开关透传 PUT /users/{id} {status:0}', async () => {
    mocks.get.mockResolvedValue({ data: [user()] })
    mocks.put.mockResolvedValue({ data: user({ status: 0 }) })

    const wrapper = mountPage(UsersView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { toggleStatus: (row: unknown, enabled: boolean) => Promise<void> }
    await vm.toggleStatus(user(), false)
    await flushPromises()

    expect(mocks.put).toHaveBeenCalledWith('/users/2', { status: 0 })
  }, 20000)

  it('内置 admin 不可停用（不发请求）', async () => {
    mocks.get.mockResolvedValue({ data: [user({ id: 1, username: 'admin', roles: ['admin'] })] })

    const wrapper = mountPage(UsersView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { remove: (row: unknown) => Promise<void> }
    await vm.remove(user({ id: 1, username: 'admin', roles: ['admin'] }))
    await flushPromises()

    expect(mocks.delete).not.toHaveBeenCalled()
  }, 20000)

  it('列表加载失败展示错误态而非空白', async () => {
    mocks.get.mockRejectedValueOnce(new Error('connection refused'))

    const wrapper = mountPage(UsersView)
    await flushPromises()

    expect(wrapper.find('[data-test="users-error"]').text()).toContain('用户列表加载失败')
  }, 20000)
})

describe('v1.9.1 API 密钥真实化', () => {
  const record = {
    id: 'k-1',
    name: '生产环境密钥',
    scope: { system: ['openllm'], tenants: ['*'] },
    description: '生产用',
    created: 1760000000,
    revoked: false,
  }

  it('加载 /auth/api-keys 并展示访问范围', async () => {
    mocks.get.mockResolvedValue({ data: [record] })

    const wrapper = mountPage(ApiKeys)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/auth/api-keys')
    const text = wrapper.text()
    expect(text).toContain('生产环境密钥')
    expect(text).toContain('openllm')
    expect(text).toContain('有效')
  }, 20000)

  it('创建透传 name/scope，并保留明文供一次性展示', async () => {
    mocks.get.mockResolvedValue({ data: [] })
    mocks.post.mockResolvedValue({ data: { ...record, key: 'ob_k_raw_key', created: 1760000100 } })

    const wrapper = mountPage(ApiKeys)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      form: { name: string; systems: string[]; tenants: string[]; description: string }
      saveKey: () => Promise<void>
      detailRow: { key?: string } | null
      ownedKeys: Record<string, string>
    }
    vm.form.name = '走查密钥'
    vm.form.description = 'e2e'
    await vm.saveKey()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/auth/api-keys', {
      name: '走查密钥',
      scope: { system: ['*'], tenants: ['*'] },
      description: 'e2e',
    })
    expect(vm.detailRow?.key).toBe('ob_k_raw_key')
  }, 20000)

  it('列表项可吊销：按 id 调用 DELETE，已吊销项禁用', async () => {
    mocks.get.mockResolvedValue({ data: [record] })
    mocks.delete.mockResolvedValue({ data: { revoked: 'k-1' } })

    const wrapper = mountPage(ApiKeys)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      canRevoke: (row: unknown) => boolean
      revoke: (row: unknown) => Promise<void>
    }
    expect(vm.canRevoke(record)).toBe(true)
    expect(vm.canRevoke({ ...record, revoked: true })).toBe(false)

    await vm.revoke(record)
    await flushPromises()

    expect(mocks.delete).toHaveBeenCalledWith('/auth/api-keys/by-id/k-1')
  }, 20000)
})

describe('v1.9.1 EdgeRouter 真实化', () => {
  /** 统一的 Edge 端点响应桩：未显式覆盖的端点返回各自空结构，避免 el-table 收到非数组 */
  function mockEdge(overrides: Record<string, unknown> = {}) {
    mocks.get.mockImplementation((url: string, config?: { params?: unknown }) => {
      const key = Object.keys(overrides).find((suffix) => url.endsWith(suffix))
      if (key) {
        const value = overrides[key]
        return Promise.resolve({ data: typeof value === 'function' ? (value as (c?: unknown) => unknown)(config) : value })
      }
      if (url.endsWith('/edge/status')) {
        return Promise.resolve({ data: { status: 'running', version: '2.0.0', uptime_seconds: 1, registered_adapters: [], adapter_count: 0, router_mode: 'inprocess', features: {} } })
      }
      if (url.endsWith('/edge/health')) {
        return Promise.resolve({ data: { status: 'healthy', components: {}, timestamp: 't' } })
      }
      if (url.endsWith('/edge/adapters')) return Promise.resolve({ data: { adapters: [], count: 0 } })
      if (url.endsWith('/edge/organizations')) return Promise.resolve({ data: [] })
      if (url.endsWith('/edge/audit/logs')) {
        return Promise.resolve({ data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 } })
      }
      return Promise.resolve({ data: [] })
    })
  }

  it('概览/组织/适配器并发加载并渲染真实字段', async () => {
    mockEdge({
      '/edge/status': {
        status: 'running',
        version: '2.0.0',
        uptime_seconds: 10894,
        registered_adapters: ['open_memory', 'open_rag'],
        adapter_count: 2,
        router_mode: 'inprocess',
        features: { jwt_enabled: true, quota_enabled: false },
      },
      '/edge/health': { status: 'healthy', components: { route_engine: 'healthy' }, timestamp: 't' },
      '/edge/adapters': {
        adapters: [{ name: 'open_memory', status: 'active', isolation_type: 'user_id', registered_at: null }],
        count: 1,
      },
    })

    const wrapper = mountPage(EdgeRouterView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/edge/status')
    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/edge/adapters')
    expect(wrapper.text()).toContain('running')
    expect(wrapper.text()).toContain('jwt_enabled')
  }, 20000)

  it('切到路由审计时按页请求审计日志', async () => {
    mockEdge()

    const wrapper = mountPage(EdgeRouterView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { onTabChange: (name: string) => void }
    vm.onTabChange('audit')
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/edge/audit/logs', {
      params: { page: 1, page_size: 20 },
    })
  }, 20000)

  it('新增组织透传 POST /edge/organizations', async () => {
    mockEdge()
    mocks.post.mockResolvedValue({
      data: { id: 'o-1', name: 'ai-platform', display_name: 'AI 平台部', description: null, status: 'active', created_at: null },
    })

    const wrapper = mountPage(EdgeRouterView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      orgForm: { name: string; display_name: string; description: string }
      saveOrg: () => Promise<void>
    }
    vm.orgForm.name = 'ai-platform'
    vm.orgForm.display_name = 'AI 平台部'
    await vm.saveOrg()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/proxy/openllm/api/v1/edge/organizations', {
      name: 'ai-platform',
      display_name: 'AI 平台部',
      description: undefined,
    })
  }, 20000)
})
