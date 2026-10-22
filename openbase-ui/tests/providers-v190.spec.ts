/**
 * v1.9.0：提供商管理真实化回归（OpenLLM 聚合通道）。
 * 覆盖：列表渲染（真实字段映射）、模型数统计、状态切换、删除、加载失败提示。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import Providers from '@/pages/platform/governance/Providers.vue'

const provider = (overrides: Record<string, unknown> = {}) => ({
  id: 'p-1',
  provider_name: 'Ollama 本地',
  provider_code: 'ollama-lan',
  provider_type: 'openai',
  api_base_url: 'http://192.168.0.4:11434/v1',
  config: {},
  status: 'active',
  priority: 10,
  health_status: 'healthy',
  last_health_check_at: '2026-10-22T10:00:00Z',
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-01T10:00:00Z',
  ...overrides,
})

function mountPage() {
  return mount(Providers, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => vi.clearAllMocks())

describe('v1.9.0 提供商管理真实化', () => {
  it('经聚合通道加载列表并渲染真实字段与模型数', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/providers')) return Promise.resolve({ data: [provider()] })
      if (url.endsWith('/providers/p-1/models')) return Promise.resolve({ data: [{ id: 'm-1' }, { id: 'm-2' }] })
      return Promise.resolve({ data: [] })
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/providers')
    expect(wrapper.text()).toContain('Ollama 本地')
    expect(wrapper.text()).toContain('192.168.0.4:11434')
    expect(wrapper.text()).toContain('模型数：2')
    expect(wrapper.find('[data-test="provider-empty"]').exists()).toBe(false)
  }, 20000)

  it('状态切换调用上游 update，并回写 status', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/providers')) return Promise.resolve({ data: [provider()] })
      return Promise.resolve({ data: [] })
    })
    mocks.put.mockResolvedValue({ data: provider({ status: 'inactive' }) })

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="provider-toggle"] input').trigger('change')
    await flushPromises()

    expect(mocks.put).toHaveBeenCalledWith('/proxy/openllm/api/v1/providers/p-1', { status: 'inactive' })
  }, 20000)

  it('删除调用上游 delete 并从列表移除', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/providers')) return Promise.resolve({ data: [provider()] })
      return Promise.resolve({ data: [] })
    })
    mocks.delete.mockResolvedValue({ data: {} })

    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.findAll('.provider-card').length).toBe(1)

    const vm = wrapper.vm as unknown as { remove: (target: unknown) => Promise<void> }
    await vm.remove(provider())
    await flushPromises()

    expect(mocks.delete).toHaveBeenCalledWith('/proxy/openllm/api/v1/providers/p-1')
    expect(wrapper.findAll('.provider-card').length).toBe(0)
  }, 20000)

  it('加载失败展示可读错误而非空白页', async () => {
    mocks.get.mockRejectedValueOnce(new Error('upstream openllm unreachable'))

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('[data-test="provider-error"]').text()).toContain('提供商列表加载失败')
  }, 20000)
})
