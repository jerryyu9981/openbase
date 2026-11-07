/**
 * v1.5.0 字典 / Agent 两页接线回归。
 *
 * 覆盖：字典类型与字典项加载、删除字典项（确认/取消）、删除类型 409 错误呈现；
 * Agent 列表加载、删除 Agent（确认/取消）、新建返回 raw_key 仅展示一次。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({
  http: mocks,
  TEST_MODE_KEY: 'ob_test_mode',
  tokenStore: { access: '', refresh: '', set: vi.fn(), clear: vi.fn() },
}))

import DictManageView from '@/pages/platform/config/DictManageView.vue'
import AgentsView from '@/pages/platform/identity/AgentsView.vue'
import { useAuthStore } from '@/core/stores/auth'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const dictTypes = [
  { code: 'order_status', name: '订单状态' },
  { code: 'color', name: '颜色' },
]
const dictItems = [{ id: 7, label: '已支付', value: 'paid', sort_order: 1 }]

const agentRows = [
  {
    id: 1,
    username: 'agent-a',
    display_name: '报表助手',
    subject_type: 'agent',
    status: 1,
    status_state: 'active',
    tenant_id: 1,
    tenant_code: 'default',
    created_at: '2026-11-01T08:00:00',
  },
]

function mockDictList(): void {
  mocks.get.mockImplementation((url: string) => {
    if (url === '/dicts') return Promise.resolve({ data: dictTypes })
    if (url === '/dicts/order_status/items') return Promise.resolve({ data: dictItems })
    return Promise.resolve({ data: [] })
  })
}

function loginAs(permissions: string[]): void {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  auth.user = { id: 1, username: 'tester', permissions }
  auth.loaded = true
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
})

describe('v1.5.0 数据字典页', () => {
  it('加载类型列表并默认选中首个类型的字典项', async () => {
    mockDictList()

    const wrapper = mountPage(DictManageView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dicts')
    expect(mocks.get).toHaveBeenCalledWith('/dicts/order_status/items')
    expect(wrapper.text()).toContain('订单状态')
    expect(wrapper.text()).toContain('已支付')
  }, 20000)

  it('删除字典项：确认后 DELETE /dicts/items/{id} 并刷新', async () => {
    mockDictList()
    mocks.delete.mockResolvedValue({ data: { deleted: 1 } })
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)

    const wrapper = mountPage(DictManageView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { removeItem: (row: unknown) => Promise<void> }
    await vm.removeItem(dictItems[0])
    await flushPromises()

    expect(mocks.delete).toHaveBeenCalledWith('/dicts/items/7')
    expect(mocks.get.mock.calls.filter(([url]) => url === '/dicts/order_status/items')).toHaveLength(2)
  }, 20000)

  it('删除字典项：取消二次确认时不发 DELETE', async () => {
    mockDictList()
    vi.spyOn(ElMessageBox, 'confirm').mockRejectedValue('cancel')

    const wrapper = mountPage(DictManageView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { removeItem: (row: unknown) => Promise<void> }
    await vm.removeItem(dictItems[0])

    expect(mocks.delete).not.toHaveBeenCalled()
  }, 20000)

  it('删除类型遇 409：呈现后端「存在字典项」文案且不静默', async () => {
    mockDictList()
    mocks.delete.mockRejectedValue({
      response: { data: { code: 2001, message: '字典类型存在字典项，禁止删除: color' } },
    })
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)

    const wrapper = mountPage(DictManageView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { removeType: (row: unknown) => Promise<void> }
    await vm.removeType(dictTypes[1])
    await flushPromises()

    expect(mocks.delete).toHaveBeenCalledWith('/dicts/color')
    expect(wrapper.text()).toContain('字典类型存在字典项，禁止删除')
  }, 20000)
})

describe('v1.5.0 Agent 管理页', () => {
  it('加载 /identity/agents 并渲染用户名与租户', async () => {
    loginAs(['*'])
    mocks.get.mockResolvedValue({ data: agentRows })

    const wrapper = mountPage(AgentsView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/identity/agents', { params: { page: 1, page_size: 100 } })
    expect(wrapper.text()).toContain('agent-a')
    expect(wrapper.text()).toContain('default')
  }, 20000)

  it('删除 Agent：确认后 DELETE /identity/agents/{id} 并刷新列表', async () => {
    loginAs(['*'])
    mocks.get.mockResolvedValue({ data: agentRows })
    mocks.delete.mockResolvedValue({ data: { code: 0, agent_id: 1, status: 0, revoked_keys: 2 } })
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)

    const wrapper = mountPage(AgentsView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { remove: (row: unknown) => Promise<void> }
    await vm.remove(agentRows[0])
    await flushPromises()

    expect(mocks.delete).toHaveBeenCalledWith('/identity/agents/1')
    expect(mocks.get.mock.calls.filter(([url]) => url === '/identity/agents')).toHaveLength(2)
  }, 20000)

  it('删除 Agent：取消二次确认时不发 DELETE', async () => {
    loginAs(['*'])
    mocks.get.mockResolvedValue({ data: agentRows })
    vi.spyOn(ElMessageBox, 'confirm').mockRejectedValue('cancel')

    const wrapper = mountPage(AgentsView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { remove: (row: unknown) => Promise<void> }
    await vm.remove(agentRows[0])

    expect(mocks.delete).not.toHaveBeenCalled()
  }, 20000)

  it('新建 Agent：展示后端仅返回一次的 api_key.raw_key', async () => {
    loginAs(['*'])
    mocks.get.mockResolvedValue({ data: agentRows })
    mocks.post.mockResolvedValue({
      data: {
        agent_id: 9,
        username: 'agent-new',
        display_name: '新助手',
        subject_type: 'agent',
        credential_type: 'agent_api_key',
        status_state: 'active',
        tenant_id: 1,
        tenant_code: 'default',
        roles: ['viewer'],
        api_key: { id: 3, agent_id: 9, name: '新助手', key_prefix: 'sk-agent-abc', key_suffix: 'xyz', status: 'active', expires_at: null, last_used_at: null, created_at: '2026-11-07T10:00:00', raw_key: 'sk-agent-abc-secret' },
      },
    })

    const wrapper = mountPage(AgentsView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      createForm: { username: string; display_name: string; role: string; key_name: string }
      submitCreate: () => Promise<void>
      revealedKey: string
    }
    vm.createForm = { username: 'agent-new', display_name: '新助手', role: 'viewer', key_name: '' }
    await vm.submitCreate()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/identity/agents', {
      username: 'agent-new',
      display_name: '新助手',
      role: 'viewer',
      key_name: undefined,
    })
    expect(vm.revealedKey).toBe('sk-agent-abc-secret')
  }, 20000)
})
