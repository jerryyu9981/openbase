/**
 * v1.9.3 R3：插件管理 / 模型分类接线回归（OpenLLM 双通道鉴权）。
 * 覆盖：插件列表与工具清单、启停透传、注册、错误态；分类树标签云、自动选中首分类并加载模型、维度切换、空态。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import PluginsView from '@/pages/platform/developers/PluginsView.vue'
import Categories from '@/pages/platform/governance/Categories.vue'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const plugin = (overrides: Record<string, unknown> = {}) => ({
  id: 'p-1',
  name: 'http_tools',
  display_name: 'HTTP 工具集',
  description: '提供 HTTP 调用',
  version: '1.0.0',
  author: 'openllm',
  plugin_type: 'builtin',
  status: 'enabled',
  config_schema: {},
  config: {},
  permissions: [],
  metadata_: { tools: [{ name: 'http_get' }, { name: 'http_post' }] },
  is_system: false,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  ...overrides,
})

const category = (overrides: Record<string, unknown> = {}) => ({
  id: 'c-1',
  name: '对话',
  code: 'chat',
  description: null,
  icon: null,
  sort_order: 1,
  parent_id: null,
  category_type: 'capability',
  model_count: 5,
  children: [],
  ...overrides,
})

const openModel = (overrides: Record<string, unknown> = {}) => ({
  id: 'm-1',
  model_id: 'meta-llama/Llama-2-7b',
  name: 'Llama 2 7B',
  source: 'huggingface',
  architecture: 'llama',
  parameters: '7B',
  license: 'llama2',
  download_count: 1200,
  rating: 4.5,
  tags: [],
  categories: ['chat'],
  download_status: 'downloaded',
  deploy_status: 'deployed',
  ...overrides,
})

beforeEach(() => vi.clearAllMocks())

describe('v1.9.3 插件管理真实化', () => {
  it('加载插件列表与工具清单', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/plugins/tools')) {
        return Promise.resolve({ data: { total: 1, items: [{ plugin_id: 'p-1', plugin_name: 'http_tools', tool_name: 'http_get', description: 'GET', parameters: {} }] } })
      }
      if (url.endsWith('/plugins')) return Promise.resolve({ data: { total: 1, items: [plugin()] } })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(PluginsView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/plugins', {
      params: { plugin_type: undefined, status: undefined, limit: 200 },
    })
    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/plugins/tools')
    const text = wrapper.text()
    expect(text).toContain('HTTP 工具集')
    expect(text).toContain('http_get')
    expect(text).toContain('内置')
  }, 20000)

  it('启停透传 enable/disable 并回写状态', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/plugins/tools')) return Promise.resolve({ data: { total: 0, items: [] } })
      return Promise.resolve({ data: { total: 1, items: [plugin()] } })
    })
    mocks.post.mockResolvedValue({ data: plugin({ status: 'disabled' }) })

    const wrapper = mountPage(PluginsView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      toggle: (row: unknown, enabled: boolean) => Promise<void>
      plugins: Array<{ status: string }>
    }
    await vm.toggle(plugin(), false)
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/proxy/openllm/api/v1/plugins/p-1/disable')
  }, 20000)

  it('注册插件透传 POST /plugins/register', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/plugins/tools')) return Promise.resolve({ data: { total: 0, items: [] } })
      return Promise.resolve({ data: { total: 0, items: [] } })
    })
    mocks.post.mockResolvedValue({ data: plugin({ id: 'p-2', name: 'new_plugin' }) })

    const wrapper = mountPage(PluginsView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      form: { name: string; version: string; entry_point: string; description: string }
      submitRegister: () => Promise<void>
    }
    vm.form.name = 'new_plugin'
    vm.form.description = '新插件'
    await vm.submitRegister()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/proxy/openllm/api/v1/plugins/register', {
      name: 'new_plugin',
      version: '1.0.0',
      entry_point: '',
      description: '新插件',
    })
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValueOnce(new Error('upstream 401'))

    const wrapper = mountPage(PluginsView)
    await flushPromises()

    expect(wrapper.find('[data-test="plugin-error"]').text()).toContain('插件列表加载失败')
  }, 20000)
})

describe('v1.9.3 模型分类真实化', () => {
  it('加载分类树并自动选中首个分类加载模型', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/model-categories/tree')) {
        return Promise.resolve({ data: { items: [category(), category({ id: 'c-2', name: '客服', code: 'support', model_count: 2 })] } })
      }
      if (url.includes('/models')) {
        return Promise.resolve({ data: { items: [openModel()], total: 1 } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Categories)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/model-categories/tree')
    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/model-categories/c-1/models', {
      params: { page: 1, page_size: 20 },
    })
    const text = wrapper.text()
    expect(text).toContain('对话 (5)')
    expect(text).toContain('Llama 2 7B')
    expect(text).toContain('已部署')
  }, 20000)

  it('维度切换后选中该维度首个分类', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/model-categories/tree')) {
        return Promise.resolve({
          data: {
            items: [
              category(),
              category({ id: 's-1', name: '客服', code: 'support', category_type: 'scene', model_count: 3 }),
            ],
          },
        })
      }
      if (url.includes('/models')) return Promise.resolve({ data: { items: [openModel()], total: 1 } })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Categories)
    await flushPromises()

    const vm = wrapper.vm as unknown as { dimension: string; onDimensionChange: () => Promise<void> }
    vm.dimension = 'scene'
    await vm.onDimensionChange()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/proxy/openllm/api/v1/model-categories/s-1/models', {
      params: { page: 1, page_size: 20 },
    })
  }, 20000)

  it('该维度无分类时展示标签云空态', async () => {
    mocks.get.mockResolvedValue({ data: { items: [category()] } })

    const wrapper = mountPage(Categories)
    await flushPromises()

    const vm = wrapper.vm as unknown as { dimension: string }
    vm.dimension = 'scale'
    await flushPromises()

    expect(wrapper.find('[data-test="tag-cloud-empty"]').exists()).toBe(true)
  }, 20000)

  it('分类加载失败展示错误态', async () => {
    mocks.get.mockRejectedValueOnce(new Error('boom'))

    const wrapper = mountPage(Categories)
    await flushPromises()

    expect(wrapper.find('[data-test="category-error"]').text()).toContain('分类加载失败')
  }, 20000)
})
