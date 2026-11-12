/**
 * 批次 5：记忆运行监控页回归
 *
 * 覆盖 AC-MEM-1~4：三探针并发与状态徽标、range 变更仅重拉指标、单探针失败降级、
 * monitor 失败可重试。全部 mock 门户 API。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const httpMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/core/api/http', () => ({ http: httpMocks }))

import MemoryMonitor from '@/modules/memory/pages/MemoryMonitor.vue'

function mountPage() {
  return mount(MemoryMonitor as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  httpMocks.get.mockImplementation((url: string) => {
    if (url === '/memory-proxy/health') {
      return Promise.resolve({ data: { code: 0, data: { status: 'healthy', version: '7.8.0' } } })
    }
    if (url === '/memory-proxy/readiness') {
      return Promise.resolve({ data: { code: 0, data: { status: 'ready' } } })
    }
    if (url === '/memory-proxy/liveness') {
      return Promise.reject(new Error('connect ECONNREFUSED'))
    }
    if (url === '/memory-proxy/monitor') {
      return Promise.resolve({
        data: { code: 0, data: { request_count: 42, hit_rate: 0.93, series: [{ t: '10:00', v: 3 }] } },
      })
    }
    return Promise.resolve({ data: { code: 0, data: {} } })
  })
})

describe('批次 5：记忆运行监控', () => {
  it('并发加载三探针与运行指标并渲染（AC-MEM-2/3/4）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const urls = httpMocks.get.mock.calls.map((call) => call[0])
    expect(urls).toContain('/memory-proxy/health')
    expect(urls).toContain('/memory-proxy/readiness')
    expect(urls).toContain('/memory-proxy/liveness')
    expect(urls).toContain('/memory-proxy/monitor')
    expect(httpMocks.get).toHaveBeenCalledWith('/memory-proxy/monitor', { params: { range: '24h' } })

    expect(wrapper.find('[data-test="health-card-health"]').text()).toContain('正常')
    expect(wrapper.find('[data-test="health-card-readiness"]').text()).toContain('正常')
    // 单探针失败降级：不影响其余卡片，且提供重新检测入口
    expect(wrapper.find('[data-test="health-card-liveness"]').text()).toContain('不可达')
    expect(wrapper.find('[data-test="probe-retry"]').exists()).toBe(true)

    const metrics = wrapper.find('[data-test="monitor-metrics"]').text()
    expect(metrics).toContain('request_count')
    expect(metrics).toContain('42')
    expect(metrics).toContain('series')
  })

  it('切换 range 仅重拉运行指标，不重复探测（AC-MEM-3）', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const healthCallsBefore = httpMocks.get.mock.calls.filter((call) => call[0] === '/memory-proxy/health').length

    const select = wrapper.findComponent({ name: 'ElSelect' })
    await select.vm.$emit('update:modelValue', '7d')
    await select.vm.$emit('change', '7d')
    await flushPromises()

    expect(httpMocks.get).toHaveBeenCalledWith('/memory-proxy/monitor', { params: { range: '7d' } })
    const healthCallsAfter = httpMocks.get.mock.calls.filter((call) => call[0] === '/memory-proxy/health').length
    expect(healthCallsAfter).toBe(healthCallsBefore)
  })

  it('运行指标加载失败展示错误条与重试（AC-MEM-4）', async () => {
    httpMocks.get.mockImplementation((url: string) => {
      if (url === '/memory-proxy/monitor') return Promise.reject(new Error('502'))
      return Promise.resolve({ data: { code: 0, data: { status: 'healthy' } } })
    })
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('[data-test="monitor-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="monitor-retry"]').exists()).toBe(true)
  })
})
