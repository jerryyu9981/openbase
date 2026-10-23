/**
 * v1.12.0 A 批：应用调用记录 / 知识库 API 控制台 / 报表趋势 真实接线回归。
 * 覆盖加载、真实请求参数、筛选与错误态。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))
vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), clear: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}))

import AppCallsView from '@/pages/platform/observability/AppCallsView.vue'
import KnowledgeConsoleView from '@/pages/platform/developers/KnowledgeConsoleView.vue'
import P2ReportTrendView from '@/modules/openllm/pages/P2ReportTrendView.vue'

const OPENLLM = '/proxy/openllm/api/v1'

function mountPage(component: unknown) {
  return mount(component as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

const appsPayload = {
  code: 0,
  message: 'ok',
  data: {
    items: [
      { id: 'app-1', name: '客服助手' },
      { id: 'app-2', name: '知识问答' },
    ],
    total: 2,
  },
}

const callsPayload = (items: unknown[], total = items.length) => ({
  code: 0,
  message: 'ok',
  data: { items, total, page: 1, page_size: 20 },
})

const calls = [
  { id: 'c1', app_id: 'app-1', app_name: '客服助手', status: 'success', latency_ms: 120, total_tokens: 300, version: 'v1' },
  { id: 'c2', app_id: 'app-2', app_name: '知识问答', status: 'error', latency_ms: 500, total_tokens: 80, error_code: 'SYS_500' },
]

beforeEach(() => vi.clearAllMocks())

describe('v1.12.0 应用调用记录（OB-03）', () => {
  it('加载应用与跨应用调用记录', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/ai-apps') return Promise.resolve({ data: appsPayload })
      if (url === '/ai-apps/calls') return Promise.resolve({ data: callsPayload(calls) })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(AppCallsView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/ai-apps')
    expect(mocks.get).toHaveBeenCalledWith('/ai-apps/calls', {
      params: { app_id: undefined, status: undefined, page: 1, page_size: 20 },
    })
    const text = wrapper.text()
    expect(text).toContain('客服助手')
    expect(text).toContain('知识问答')
    expect(text).toContain('SYS_500')
  }, 20000)

  it('按状态筛选时携带 status 参数', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/ai-apps') return Promise.resolve({ data: appsPayload })
      if (url === '/ai-apps/calls') return Promise.resolve({ data: callsPayload([calls[1]]) })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(AppCallsView)
    await flushPromises()

    // 直接驱动筛选模型（el-radio-button 在 jsdom 下 click 不必然触发 v-model）
    const vm = wrapper.vm as unknown as { statusFilter: string }
    vm.statusFilter = 'error'
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/ai-apps/calls', {
      params: { app_id: undefined, status: 'error', page: 1, page_size: 20 },
    })
  }, 20000)

  it('加载失败时展示错误条', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/ai-apps') return Promise.resolve({ data: appsPayload })
      if (url === '/ai-apps/calls') return Promise.reject(new Error('db down'))
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(AppCallsView)
    await flushPromises()

    expect(wrapper.find('[data-test="calls-error"]').exists()).toBe(true)
  }, 20000)
})

describe('v1.12.0 知识库 API 控制台（OB-04）', () => {
  it('加载知识库与健康，并调用真实检索端点', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/rag-proxy/collections') {
        return Promise.resolve({ data: { code: 0, data: { items: [{ id: 'c1', name: '知识库A' }], total: 1 } } })
      }
      if (url === '/rag-proxy/health') {
        return Promise.resolve({ data: { code: 0, data: { status: 'ok', components: { converter: 'ok' } } } })
      }
      return Promise.resolve({ data: {} })
    })
    mocks.post.mockResolvedValue({
      data: { code: 0, data: { items: [{ chunk_id: 'chunk-1', score: 0.92, content: '网关说明' }], total: 1 } },
    })

    const wrapper = mountPage(KnowledgeConsoleView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/rag-proxy/collections', { params: undefined })
    expect(wrapper.find('[data-test="rag-health-tag"]').text()).toBe('ok')
    expect(wrapper.text()).toContain('知识库A')

    await wrapper.find('[data-test="rag-send"]').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/rag-proxy/collections/c1/query/retrieve', {
      query: 'OpenBase 网关',
      top_k: 5,
    })
    expect(wrapper.find('[data-test="rag-response"]').text()).toContain('chunk-1')
    expect(wrapper.find('[data-test="rag-latency"]').exists()).toBe(true)
  }, 20000)

  it('检索失败时展示错误条且不残留结果', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/rag-proxy/collections') {
        return Promise.resolve({ data: { code: 0, data: { items: [{ id: 'c1', name: '知识库A' }], total: 1 } } })
      }
      if (url === '/rag-proxy/health') return Promise.resolve({ data: { code: 0, data: { status: 'ok' } } })
      return Promise.resolve({ data: {} })
    })
    mocks.post.mockRejectedValue(new Error('upstream timeout'))

    const wrapper = mountPage(KnowledgeConsoleView)
    await flushPromises()

    await wrapper.find('[data-test="rag-send"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="rag-console-error"]').text()).toContain('upstream timeout')
    expect(wrapper.find('[data-test="rag-response"]').text()).toContain('等待发送请求')
  }, 20000)
})

describe('v1.12.0 报表趋势（XR-LLM-03 报表部分）', () => {
  const dashboard = {
    overview: {
      total_requests: 1200,
      total_tokens: 500000,
      total_cost: 12.5,
      avg_latency_ms: 320,
      error_rate: 0.8,
      active_users: 4,
      time_range: '30d',
    },
    performance: { by_provider: [], by_model: [], time_series: [] },
    cost: { by_provider: [], by_model: [], by_user: [], trend: [] },
    error: { by_type: [], by_provider: [], active_alerts: [] },
    resource: {},
  }

  it('聚合 KPI、趋势与用户成本排名', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/monitoring/dashboard`) return Promise.resolve({ data: dashboard })
      if (url === `${OPENLLM}/usage/trends`) {
        return Promise.resolve({
          data: {
            tenant_id: null,
            dimension: 'date',
            period: 'day',
            series: [
              { date: '2026-10-20', requests: 100, input_tokens: 1000, output_tokens: 2000, total_tokens: 3000, cost: 1.2 },
              { date: '2026-10-21', requests: 150, input_tokens: 1500, output_tokens: 2500, total_tokens: 4000, cost: 1.8 },
            ],
            summary: {},
          },
        })
      }
      if (url === `${OPENLLM}/monitoring/costs`) {
        return Promise.resolve({
          data: {
            time_range: '30d',
            start_time: '',
            end_time: '',
            dimensions: {
              user: [
                { value: 'u-1', total_cost: 8.5, request_count: 900, avg_cost_per_request: 0.009 },
                { value: 'u-2', total_cost: 2.0, request_count: 300, avg_cost_per_request: 0.007 },
              ],
            },
            trend: [],
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(P2ReportTrendView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/dashboard`, { params: { time_range: '30d' } })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/usage/trends`, {
      params: { dimension: 'date', period: 'day' },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/costs`, {
      params: { dimension: ['user'], time_range: '30d' },
    })

    const text = wrapper.text()
    expect(text).toContain('1,200')
    expect(text).toContain('$12.50')
    expect(text).toContain('u-1')
    expect(wrapper.findAll('[data-test="rep-kpi"]').length).toBe(4)
  }, 20000)

  it('单源失败时提示但仍渲染可用数据', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === `${OPENLLM}/monitoring/dashboard`) return Promise.resolve({ data: dashboard })
      if (url === `${OPENLLM}/usage/trends`) return Promise.reject(new Error('usage down'))
      if (url === `${OPENLLM}/monitoring/costs`) {
        return Promise.resolve({ data: { dimensions: { user: [] }, trend: [], time_range: '30d', start_time: '', end_time: '' } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(P2ReportTrendView)
    await flushPromises()

    expect(wrapper.find('[data-test="rep-error"]').text()).toContain('usage down')
    expect(wrapper.text()).toContain('1,200')
    expect(wrapper.text()).toContain('暂无成本数据')
  }, 20000)
})
