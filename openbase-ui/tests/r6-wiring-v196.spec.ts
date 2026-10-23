/**
 * v1.9.6 R6：本地资源与模型市场两页接线回归（GPU 资源 / 下载管理）。
 * 覆盖：真实端点与参数、降级态、暂停/恢复/取消/重试/部署动作、错误态。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import GpuMonitorView from '@/pages/platform/observability/GpuMonitorView.vue'
import DownloadManagerView from '@/pages/platform/governance/DownloadManagerView.vue'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const OPENLLM = '/proxy/openllm/api/v1'

const allocation = {
  available: true,
  gpu_count: 1,
  gpus: [
    {
      gpu_id: 0,
      name: 'NVIDIA A100 40GB',
      total_memory_mb: 40960,
      used_memory_mb: 20480,
      free_memory_mb: 20480,
      utilization: 72,
      allocated_models: [{ model_name: 'qwen2.5-7b', schedule_type: 'exclusive' }],
    },
  ],
  message: null,
}

const downloadTask = (overrides: Record<string, unknown> = {}) => ({
  id: 'task-1',
  model_id: 'model-1',
  model_name: 'llama3-8b',
  status: 'downloading',
  total_size: 5 * 1024 * 1024 * 1024,
  downloaded_size: 2 * 1024 * 1024 * 1024,
  progress: 40,
  download_speed: 18.5 * 1024 * 1024,
  error_message: null,
  retry_count: 0,
  local_path: null,
  created_at: '2026-10-23T10:00:00',
  updated_at: '2026-10-23T10:01:00',
  ...overrides,
})

beforeEach(() => vi.clearAllMocks())

describe('v1.9.6 GPU 资源真实化', () => {
  it('加载分配状态与运行中模型', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/local-models/gpu-allocation/status')) return Promise.resolve({ data: allocation })
      if (url.endsWith('/local-models/gpu-info')) {
        return Promise.resolve({
          data: { available: true, running_models: [{ name: 'qwen2.5-7b', size: 4 * 1024 * 1024 * 1024, gpu: { id: 0 } }] },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(GpuMonitorView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/local-models/gpu-allocation/status`)
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/local-models/gpu-info`)
    const text = wrapper.text()
    expect(text).toContain('NVIDIA A100 40GB')
    expect(text).toContain('qwen2.5-7b')
    expect(text).toContain('20.0 / 40.0 GB')
  }, 20000)

  it('GPU 不可用时展示降级提示与空表', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/gpu-allocation/status')) {
        return Promise.resolve({ data: { available: false, gpu_count: 0, gpus: [], message: 'GPU 监控不可用' } })
      }
      return Promise.resolve({ data: { available: false, running_models: [] } })
    })

    const wrapper = mountPage(GpuMonitorView)
    await flushPromises()

    expect(wrapper.find('[data-test="gpu-no-env"]').text()).toContain('GPU 监控不可用')
    expect(wrapper.text()).toContain('当前环境未检测到 GPU')
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValueOnce(new Error('upstream 502'))

    const wrapper = mountPage(GpuMonitorView)
    await flushPromises()

    expect(wrapper.find('[data-test="gpu-error"]').text()).toContain('GPU 资源加载失败')
  }, 20000)
})

describe('v1.9.6 下载管理真实化', () => {
  it('加载下载任务并格式化大小/速度', async () => {
    mocks.get.mockResolvedValue({
      data: { items: [downloadTask()], total: 1, page: 1, page_size: 20 },
    })

    const wrapper = mountPage(DownloadManagerView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models/downloads`, {
      params: { status: undefined, page: 1, page_size: 20 },
    })
    const text = wrapper.text()
    expect(text).toContain('llama3-8b')
    expect(text).toContain('5.00 GB')
    expect(text).toContain('18.5 MB/s')
  }, 20000)

  it('暂停/恢复/取消/重试/部署分别透传对应端点', async () => {
    mocks.get.mockResolvedValue({
      data: { items: [downloadTask()], total: 1, page: 1, page_size: 20 },
    })

    const wrapper = mountPage(DownloadManagerView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      pause: (row: unknown) => Promise<void>
      resume: (row: unknown) => Promise<void>
      cancel: (row: unknown) => Promise<void>
      retry: (row: unknown) => Promise<void>
      deploy: (row: unknown) => Promise<void>
    }
    const row = downloadTask()

    await vm.pause(row)
    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/model-1/pause-download`, {})

    await vm.resume(row)
    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/model-1/resume-download`, {})

    await vm.cancel(row)
    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/model-1/cancel-download`, {})

    await vm.retry(row)
    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/model-1/download`, {
      version: 'main',
      resume: true,
    })

    await vm.deploy(row)
    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/model-1/deploy`, {
      framework: 'auto',
      quantization: null,
      gpu_devices: null,
      port: 8000,
      max_context_length: 4096,
    })
  }, 20000)

  it('状态筛选透传 status 参数', async () => {
    mocks.get.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 20 } })

    const wrapper = mountPage(DownloadManagerView)
    await flushPromises()
    mocks.get.mockClear()

    const vm = wrapper.vm as unknown as { statusFilter: string; reload: () => void }
    vm.statusFilter = 'failed'
    vm.reload()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models/downloads`, {
      params: { status: 'failed', page: 1, page_size: 20 },
    })
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValueOnce(new Error('upstream 502'))

    const wrapper = mountPage(DownloadManagerView)
    await flushPromises()

    expect(wrapper.find('[data-test="dl-error"]').text()).toContain('下载任务加载失败')
  }, 20000)
})
