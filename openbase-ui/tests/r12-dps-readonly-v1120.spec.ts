/**
 * v1.12.0 E 批：XR-DPS-03 三个治理页只读真实化 + XR-LLM-08 工具来源标注。
 * 覆盖：真实端点加载、只读约束（无写入口）、参数透传、运行期内建标签。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import DpsPermissionView from '@/pages/platform/identity/DpsPermissionView.vue'
import DpsRateLimitView from '@/pages/platform/config/DpsRateLimitView.vue'
import DpsApiManageView from '@/pages/platform/developers/DpsApiManageView.vue'
import PluginsView from '@/pages/platform/developers/PluginsView.vue'

function mountPage(component: unknown) {
  return mount(component as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

const roles = [
  {
    id: 1,
    name: 'super_admin',
    description: '超级管理员',
    permissions: '["portrait:read","portrait:create"]',
    is_builtin: 1,
  },
]

const rateStatus = [
  {
    tenant_id: 'tenant-001',
    endpoint: '/api/v2/portrait/list',
    count: 30,
    limit: 1000,
    window: 60,
    utilization: 3,
    source: 'local',
    window_start: '2026-10-24T00:00:00Z',
  },
]

const registry = [
  {
    endpoint: '/api/v2/portrait/list',
    method: 'GET',
    version: 'v2',
    status: 'active',
    sunset_date: null,
    description: '画像列表',
  },
]

const errorCodes = [
  { code: 'PARAM_400', http_status: 400, message: '参数校验失败', category: 'param' },
]

beforeEach(() => vi.clearAllMocks())

describe('v1.12.0 画像数据权限（XR-DPS-03 只读）', () => {
  it('加载角色权限并保持无写入口', async () => {
    mocks.get.mockResolvedValue({ data: { code: 0, data: roles } })

    const wrapper = mountPage(DpsPermissionView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/permissions/roles')
    expect(wrapper.text()).toContain('super_admin')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.find('[data-test="perm-new"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="perm-readonly-notice"]').exists()).toBe(true)
  }, 20000)
})

describe('v1.12.0 画像接口限流（XR-DPS-03 只读）', () => {
  it('加载限流状态并按租户过滤透传参数', async () => {
    mocks.get.mockResolvedValue({ data: { code: 0, data: rateStatus } })

    const wrapper = mountPage(DpsRateLimitView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/rate-limits/status', { params: { tenant_id: undefined } })
    expect(wrapper.text()).toContain('tenant-001')
    expect(wrapper.find('[data-test="rl-new"]').exists()).toBe(false)

    const vm = wrapper.vm as unknown as { tenantId: string; load: () => Promise<void> }
    vm.tenantId = 'tenant-001'
    await vm.load()
    expect(mocks.get).toHaveBeenLastCalledWith('/dps-proxy/rate-limits/status', {
      params: { tenant_id: 'tenant-001' },
    })
  }, 20000)
})

describe('v1.12.0 画像 API 管理（XR-DPS-03 只读）', () => {
  it('加载 API 注册表与错误码，且不提供写入口', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/dps-proxy/api-registry') return Promise.resolve({ data: { code: 0, data: registry } })
      if (url === '/dps-proxy/error-codes') return Promise.resolve({ data: { code: 0, data: errorCodes } })
      return Promise.resolve({ data: { code: 0, data: [] } })
    })

    const wrapper = mountPage(DpsApiManageView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/api-registry', { params: undefined })
    expect(wrapper.text()).toContain('/api/v2/portrait/list')
    expect(wrapper.text()).toContain('画像列表')
    expect(wrapper.find('[data-test="api-new"]').exists()).toBe(false)

    const vm = wrapper.vm as unknown as { errorCodes: Array<{ code: string }>; openErrors: () => void }
    vm.openErrors()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/error-codes', { params: undefined })
    expect(vm.errorCodes[0].code).toBe('PARAM_400')
  }, 20000)
})

describe('v1.12.0 插件工具来源标注（XR-LLM-08）', () => {
  it('运行时注册表工具标注「运行期内建」，DB 插件工具标注「插件注册」', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/proxy/openllm/api/v1/plugins') {
        return Promise.resolve({
          data: { total: 1, items: [{ id: 'db-1', name: 'http_tools', plugin_type: 'external', status: 'enabled', version: '1.0.0' }] },
        })
      }
      if (url === '/proxy/openllm/api/v1/plugins/tools') {
        return Promise.resolve({
          data: {
            total: 2,
            items: [
              { plugin_id: 'db-1', plugin_name: 'http_tools', tool_name: 'http_get', description: 'HTTP 调用', parameters: {} },
              { plugin_id: 'builtin-hello', plugin_name: 'builtin', tool_name: 'hello-world', description: '内建示例', parameters: {} },
            ],
          },
        })
      }
      return Promise.resolve({ data: { total: 0, items: [] } })
    })

    const wrapper = mountPage(PluginsView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/plugins', {
      params: { plugin_type: undefined, status: undefined, limit: 200 },
    })
    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/plugins/tools')
    expect(wrapper.findAll('[data-test="tool-runtime-tag"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('运行期内建')
    expect(wrapper.text()).toContain('插件注册')
  }, 20000)
})
