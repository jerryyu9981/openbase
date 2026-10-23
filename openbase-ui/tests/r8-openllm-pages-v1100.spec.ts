/**
 * v1.10.0（XR-LLM-02）：OpenLLM 四页真实接线回归。
 * 覆盖：本地模型 / 模型对比 / 开源市场 / 我的收藏 —— 均走 OpenBase 通用代理真实端点，0 mock 常量。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import LocalModels from '@/modules/openllm/pages/LocalModels.vue'
import Comparison from '@/modules/openllm/pages/Comparison.vue'
import ModelMarketView from '@/modules/openllm/pages/ModelMarketView.vue'
import Favorites from '@/modules/openllm/pages/Favorites.vue'

const OPENLLM = '/proxy/openllm/api/v1'

function mountPage(component: unknown) {
  return mount(component as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' }, teleport: true },
    },
  })
}

const marketItems = [
  {
    id: 'm-1',
    model_id: 'qwen2.5-7b',
    name: 'Qwen2.5 7B',
    source: 'huggingface',
    parameters: '7B',
    license: 'Apache-2.0',
    download_status: 'not_downloaded',
    deploy_status: 'not_deployed',
    version: 'main',
    tags: ['chat'],
  },
  {
    id: 'm-2',
    model_id: 'llama3.1-8b',
    name: 'Llama 3.1 8B',
    source: 'modelscope',
    parameters: '8B',
    license: 'Llama-3.1',
    download_status: 'downloading',
    deploy_status: 'not_deployed',
    version: 'main',
    tags: ['chat'],
  },
]

beforeEach(() => vi.clearAllMocks())

describe('v1.10.0 本地模型页真实接线', () => {
  it('加载已安装模型 / GPU / 仓库，并调用启停端点', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/local-models`) {
        return Promise.resolve({
          data: [{ name: 'qwen2.5-7b', model: 'qwen2.5-7b', modified_at: '2026-10-20T10:00:00Z', size: 5 * 1024 ** 3, digest: 'sha' }],
        })
      }
      if (url === `${OPENLLM}/local-models/gpu-info`) return Promise.resolve({ data: { available: true, running_models: [] } })
      if (url === `${OPENLLM}/local-models/gpu-allocation/status`) return Promise.resolve({ data: { available: true, gpu_count: 0, gpus: [] } })
      if (url === `${OPENLLM}/local-models/available`) return Promise.resolve({ data: { models: [{ id: 'qwen3-8b', name: 'Qwen3 8B', parameters: '8B' }], categories: [], total_count: 1 } })
      return Promise.resolve({ data: {} })
    })
    mocks.post.mockResolvedValue({ data: {} })

    const wrapper = mountPage(LocalModels)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/local-models`)
    expect(wrapper.text()).toContain('qwen2.5-7b')
    expect(wrapper.text()).toContain('5.0GB')

    const startButton = wrapper.findAll('button').find((btn) => btn.text() === '启动')
    expect(startButton).toBeTruthy()
    await startButton!.trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/local-models/qwen2.5-7b/start`, {})
  }, 20000)

  it('本地模型列表失败时展示错误态', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/local-models`) return Promise.reject(new Error('boom'))
      return Promise.resolve({ data: {} })
    })
    const wrapper = mountPage(LocalModels)
    await flushPromises()
    expect(wrapper.find('[data-test="local-models-error"]').exists()).toBe(true)
  }, 20000)
})

describe('v1.10.0 开源市场页真实接线', () => {
  it('渲染开源模型并提交下载任务', async () => {
    mocks.get.mockResolvedValue({ data: { items: marketItems, total: 2, page: 1, page_size: 100 } })
    mocks.post.mockResolvedValue({ data: {} })

    const wrapper = mountPage(ModelMarketView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models`, { params: { page: 1, page_size: 100 } })
    expect(wrapper.text()).toContain('Qwen2.5 7B')

    await wrapper.find('[data-test="market-download"]').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/qwen2.5-7b/download`, {
      version: 'main',
      resume: true,
    })
  }, 20000)

  it('开源市场加载失败时展示错误态', async () => {
    mocks.get.mockRejectedValue(new Error('500'))
    const wrapper = mountPage(ModelMarketView)
    await flushPromises()
    expect(wrapper.find('[data-test="market-error"]').exists()).toBe(true)
  }, 20000)
})

describe('v1.10.0 我的收藏页真实接线', () => {
  it('按收藏夹分组展示收藏，下载复用开源模型下载端点', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/models/favorites`) {
        return Promise.resolve({
          data: [
            {
              id: 'f-1',
              model_id: 'm-1',
              folder_name: '默认收藏',
              notes: null,
              created_at: '2026-10-21T08:00:00Z',
              model: { id: 'm-1', model_id: 'qwen2.5-7b', name: 'Qwen2.5 7B', source: 'huggingface', parameters: '7B', license: 'Apache-2.0', tags: ['chat'] },
            },
          ],
        })
      }
      if (url === `${OPENLLM}/models/favorite-folders`) {
        return Promise.resolve({ data: { items: [{ name: '默认收藏', count: 1 }] } })
      }
      return Promise.resolve({ data: {} })
    })
    mocks.post.mockResolvedValue({ data: {} })

    const wrapper = mountPage(Favorites)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/models/favorites`, { params: {} })
    expect(wrapper.text()).toContain('1 个收藏模型')
    expect(wrapper.text()).toContain('Qwen2.5 7B')

    await wrapper.find('[data-test="favorite-download"]').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/m-1/download`, {
      version: 'main',
      resume: true,
    })
  }, 20000)

  it('收藏列表加载失败时展示错误态并可重试', async () => {
    mocks.get.mockRejectedValue(new Error('down'))
    const wrapper = mountPage(Favorites)
    await flushPromises()
    expect(wrapper.find('[data-test="favorites-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="favorites-retry"]').exists()).toBe(true)
  }, 20000)
})

describe('v1.10.0 模型对比页真实接线', () => {
  it('模型池来自开源模型列表，加入 2 个模型后调用对比端点', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/open-models`) {
        return Promise.resolve({ data: { items: marketItems, total: 2, page: 1, page_size: 100 } })
      }
      if (url === `${OPENLLM}/models/compare`) {
        return Promise.resolve({ data: { models: marketItems, comparison: { advantages: { 'Qwen2.5 7B': '参数更小' } } } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Comparison)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models`, { params: { page: 1, page_size: 100 } })
    expect(wrapper.find('[data-test="comparison-empty"]').exists()).toBe(true)

    await wrapper.find('[data-test="comparison-add"]').trigger('click')
    await flushPromises()

    const checkboxes = wrapper.findAll('[data-test="comparison-checkbox"] input')
    expect(checkboxes.length).toBe(2)
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)
    await wrapper.find('[data-test="comparison-confirm"]').trigger('click')
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/models/compare`, {
      params: { model_ids: ['m-1', 'm-2'] },
    })
    expect(wrapper.text()).toContain('参数更小')
  }, 20000)

  it('对比失败时展示错误态', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/open-models`) {
        return Promise.resolve({ data: { items: marketItems, total: 2, page: 1, page_size: 100 } })
      }
      return Promise.reject(new Error('compare down'))
    })

    const wrapper = mountPage(Comparison)
    await flushPromises()
    await wrapper.find('[data-test="comparison-add"]').trigger('click')
    await flushPromises()
    const checkboxes = wrapper.findAll('[data-test="comparison-checkbox"] input')
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)
    await wrapper.find('[data-test="comparison-confirm"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="comparison-error"]').exists()).toBe(true)
  }, 20000)
})
