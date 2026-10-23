/**
 * v1.12.0 C 批（XR-DPS-05）：画像系统监控页真实化回归。
 * 覆盖：四源只读加载、KPI/限流/告警渲染、单源失败降级、无写请求。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import DpsMonitorView from '@/pages/platform/observability/DpsMonitorView.vue'

function mountPage() {
  return mount(DpsMonitorView as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

const metrics = {
  qps_1m: 1.5,
  cpu_percent: 3.2,
  memory_mb: 128.5,
  memory_percent: 0.9,
  uptime_seconds: 3725,
  requests_total: 9,
  collected_at: '2026-10-24T00:00:00+00:00',
}

const rateLimits = [
  {
    tenant_id: 'tenant-001',
    endpoint: '/api/v2/portrait/list',
    count: 30,
    limit: 1000,
    window: 60,
    utilization: 3,
    source: 'local',
  },
]

const alertRules = [
  {
    id: 1,
    name: '高错误率',
    condition: 'error_rate',
    threshold: 0.05,
    duration: '5m',
    notification_channel: 'email',
    enabled: 1,
  },
]

function stubHappyPath() {
  mocks.get.mockImplementation((url: string) => {
    if (url === '/dps-proxy/health') {
      return Promise.resolve({ data: { code: 0, data: { status: 'healthy', version: '2.11.0' } } })
    }
    if (url === '/dps-proxy/metrics') return Promise.resolve({ data: { code: 0, data: metrics } })
    if (url === '/dps-proxy/rate-limits/status') {
      return Promise.resolve({ data: { code: 0, data: rateLimits } })
    }
    if (url === '/dps-proxy/alerts/rules') {
      return Promise.resolve({ data: { code: 0, data: alertRules } })
    }
    return Promise.resolve({ data: { code: 0, data: {} } })
  })
}

beforeEach(() => vi.clearAllMocks())

describe('v1.12.0 画像系统监控（XR-DPS-05）', () => {
  it('四源并行加载并渲染指标、限流与告警规则', async () => {
    stubHappyPath()
    const wrapper = mountPage()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/health')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/metrics')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/rate-limits/status', { params: undefined })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/alerts/rules')

    const text = wrapper.text()
    expect(text).toContain('1.50')
    expect(text).toContain('3.20%')
    expect(text).toContain('128.5 MB')
    expect(text).toContain('1 小时 2 分')
    expect(text).toContain('tenant-001')
    expect(text).toContain('高错误率')
    expect(text).toContain('启用')
    expect(mocks.post).not.toHaveBeenCalled()
  }, 20000)

  it('单源失败时提示错误且保留其他可用区域', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/dps-proxy/health') {
        return Promise.resolve({ data: { code: 0, data: { status: 'healthy', version: '2.11.0' } } })
      }
      if (url === '/dps-proxy/metrics') return Promise.reject(new Error('DPS metrics unavailable'))
      if (url === '/dps-proxy/rate-limits/status') {
        return Promise.resolve({ data: { code: 0, data: rateLimits } })
      }
      if (url === '/dps-proxy/alerts/rules') {
        return Promise.resolve({ data: { code: 0, data: alertRules } })
      }
      return Promise.resolve({ data: { code: 0, data: {} } })
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('[data-test="dps-monitor-error"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('运行态指标加载失败')
    expect(wrapper.text()).toContain('tenant-001')
    expect(wrapper.text()).toContain('高错误率')
  }, 20000)

  it('指标为 null 的内存字段显示占位符而非虚构值', async () => {
    stubHappyPath()
    mocks.get.mockImplementation((url: string) => {
      if (url === '/dps-proxy/metrics') {
        return Promise.resolve({
          data: { code: 0, data: { ...metrics, memory_mb: null, memory_percent: null } },
        })
      }
      if (url === '/dps-proxy/health') {
        return Promise.resolve({ data: { code: 0, data: { status: 'healthy', version: '2.11.0' } } })
      }
      return Promise.resolve({ data: { code: 0, data: [] } })
    })

    const wrapper = mountPage()
    await flushPromises()

    const memoryCard = wrapper.find('[data-test="dps-metric-memory"]')
    expect(memoryCard.text()).toContain('—')
  }, 20000)
})
