/**
 * v1.9.7 R7：E 类产品裁定落地回归。
 * 覆盖：仪表盘真实聚合、统一监控、个人设置（资料/密码）、DPS 健康、模型部署。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))
vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}))

import Dashboard from '@/pages/Dashboard.vue'
import Monitoring from '@/pages/platform/observability/Monitoring.vue'
import SettingsView from '@/pages/personal/SettingsView.vue'
import DpsMonitorView from '@/pages/platform/observability/DpsMonitorView.vue'
import DeployView from '@/pages/platform/governance/DeployView.vue'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'

const OPENLLM = '/proxy/openllm/api/v1'

function mountPage(component: unknown, pinia?: ReturnType<typeof createPinia>) {
  return mount(component as never, {
    global: {
      plugins: pinia ? [pinia, ElementPlus] : [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

const dashboardPayload = {
  overview: {
    total_requests: 1200,
    total_tokens: 500000,
    total_cost: 12.5,
    avg_latency_ms: 320,
    error_rate: 0.8,
    active_users: 4,
    time_range: '24h',
  },
  performance: {
    by_provider: [],
    by_model: [],
    time_series: [{ timestamp: '2026-10-23 10:00', avg_latency_ms: 300, request_count: 120 }],
  },
  cost: { by_provider: [], by_model: [], by_user: [], trend: [] },
  error: { by_type: [], by_provider: [], active_alerts: [] },
  resource: {},
}

beforeEach(() => vi.clearAllMocks())

describe('v1.9.7 仪表盘真实化', () => {
  it('聚合用户数与 OpenLLM 24h 概览', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/users')) return Promise.resolve({ data: [{ id: 1 }, { id: 2 }, { id: 3 }] })
      if (url.endsWith('/monitoring/dashboard')) return Promise.resolve({ data: dashboardPayload })
      return Promise.resolve({ data: {} })
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'admin', permissions: ['*'], display_name: '管理员' }
    const registry = useModuleRegistry()
    registry.modules = [
      { info: { id: 'openllm', name: 'OpenLLM', route_prefix: '/openllm', entry: '', permission: '*', status: 'enabled', sort_order: 1 }, loaded: true },
    ]

    const wrapper = mountPage(Dashboard, pinia)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/users')
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/dashboard`, { params: { time_range: '24h' } })
    const text = wrapper.text()
    expect(text).toContain('平台用户数')
    expect(text).toContain('3')
    expect(text).toContain('1200')
    expect(text).toContain('$12.50')
    expect(text).toContain('管理员')
  }, 20000)

  it('单源失败时对应卡片显示占位并提示', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/users')) return Promise.reject(new Error('403'))
      return Promise.resolve({ data: dashboardPayload })
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore()

    const wrapper = mountPage(Dashboard, pinia)
    await flushPromises()

    expect(wrapper.find('[data-test="dashboard-error"]').text()).toContain('部分概览数据加载失败')
    expect(wrapper.text()).toContain('—')
  }, 20000)
})

describe('v1.9.7 统一监控真实化', () => {
  it('加载 dashboard 与未解决告警', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/monitoring/dashboard')) return Promise.resolve({ data: dashboardPayload })
      if (url.endsWith('/alerts')) {
        return Promise.resolve({
          data: {
            alerts: [
              {
                id: 'a-1',
                rule_id: null,
                alert_type: 'latency_spike',
                severity: 'high',
                status: 'firing',
                title: '延迟过高',
                message: 'P99 820ms',
                provider: null,
                model: null,
                threshold_value: null,
                actual_value: null,
                fired_at: '2026-10-23T09:00:00',
                resolved_at: null,
                acknowledged_at: null,
                created_at: '2026-10-23T09:00:00',
              },
            ],
            total: 1,
            page: 1,
            page_size: 10,
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Monitoring)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/dashboard`, {
      params: { time_range: '6h' },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/alerts`, {
      params: { status: 'firing', page: 1, page_size: 10 },
    })
    const text = wrapper.text()
    expect(text).toContain('1200')
    expect(text).toContain('延迟过高')
    expect(text).toContain('0.80%')
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValue(new Error('502'))

    const wrapper = mountPage(Monitoring)
    await flushPromises()

    expect(wrapper.find('[data-test="monitoring-error"]').text()).toContain('监控数据加载失败')
  }, 20000)
})

describe('v1.9.7 个人设置真实化', () => {
  it('回填资料并保存', async () => {
    mocks.get.mockResolvedValue({
      data: { id: 1, username: 'alice', permissions: [], display_name: 'Alice', email: 'a@b.com', phone: null },
    })
    mocks.put.mockResolvedValue({
      data: { id: 1, username: 'alice', permissions: [], display_name: 'Alice New', email: 'new@b.com', phone: '138' },
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore()

    const wrapper = mountPage(SettingsView, pinia)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/auth/me')
    const vm = wrapper.vm as unknown as {
      profileForm: { displayName: string; email: string; phone: string }
      handleSaveProfile: () => Promise<void>
    }
    expect(vm.profileForm.displayName).toBe('Alice')

    vm.profileForm.displayName = 'Alice New'
    vm.profileForm.email = 'new@b.com'
    vm.profileForm.phone = '138'
    await vm.handleSaveProfile()
    await flushPromises()

    expect(mocks.put).toHaveBeenCalledWith('/auth/me', {
      display_name: 'Alice New',
      email: 'new@b.com',
      phone: '138',
    })
  }, 20000)

  it('修改密码透传后端并展示后端错误', async () => {
    mocks.get.mockResolvedValue({
      data: { id: 1, username: 'alice', permissions: [], display_name: 'Alice', email: 'a@b.com', phone: null },
    })
    mocks.post.mockRejectedValue({ response: { data: { message: '旧密码不正确' } } })
    const pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore()

    const wrapper = mountPage(SettingsView, pinia)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      passwordForm: { oldPassword: string; newPassword: string; confirmPassword: string }
      handleChangePassword: () => Promise<void>
    }
    vm.passwordForm.oldPassword = 'WrongPass1'
    vm.passwordForm.newPassword = 'NewPass123'
    vm.passwordForm.confirmPassword = 'NewPass123'
    await vm.handleChangePassword()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/auth/change-password', {
      old_password: 'WrongPass1',
      new_password: 'NewPass123',
    })
    expect(wrapper.find('[data-test="password-error"]').text()).toContain('旧密码不正确')
  }, 20000)
})

describe('v1.9.7 DPS 监控收敛', () => {
  it('仅展示健康状态并说明指标未开放', async () => {
    mocks.get.mockResolvedValue({ data: { code: 0, data: { status: 'healthy', version: '1.0.0' } } })

    const wrapper = mountPage(DpsMonitorView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/health')
    expect(wrapper.text()).toContain('健康')
    expect(wrapper.text()).toContain('1.0.0')
    expect(wrapper.find('[data-test="dps-monitor-unavailable"]').exists()).toBe(true)
  }, 20000)
})

describe('v1.9.7 模型部署真实化', () => {
  it('加载模型并透传部署参数', async () => {
    mocks.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 'm-1',
            model_id: 'meta-llama/Llama-2-7b',
            name: 'Llama 2 7B',
            source: 'huggingface',
            parameters: '7B',
            license: 'llama2',
            download_status: 'completed',
            deploy_status: 'not_deployed',
            version: 'main',
            tags: [],
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
      },
    })

    const wrapper = mountPage(DeployView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models`, {
      params: { page: 1, page_size: 100 },
    })
    expect(wrapper.text()).toContain('Llama 2 7B')

    const vm = wrapper.vm as unknown as {
      openDeploy: (row: unknown) => void
      deployForm: { framework: string; quantization: string; gpuDevices: string; port: number; maxContext: number }
      submitDeploy: () => Promise<void>
    }
    mocks.post.mockResolvedValue({ data: {} })
    vm.openDeploy({ id: 'm-1', model_id: 'meta-llama/Llama-2-7b', name: 'Llama 2 7B' })
    vm.deployForm.framework = 'vllm'
    vm.deployForm.gpuDevices = '0,1'
    vm.deployForm.port = 8080
    await vm.submitDeploy()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/open-models/meta-llama%2FLlama-2-7b/deploy`, {
      framework: 'vllm',
      quantization: null,
      gpu_devices: [0, 1],
      port: 8080,
      max_context_length: 4096,
    })
  }, 20000)

  it('状态与日志抽屉加载真实数据', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/deploy-status')) {
        return Promise.resolve({
          data: {
            deployment_id: 'dep-1',
            status: 'running',
            framework: 'vllm',
            port: 8000,
            process_id: 123,
            health_check_url: null,
            is_healthy: true,
            resource_usage: {},
            start_time: '2026-10-23T10:00:00',
            uptime_seconds: 120,
          },
        })
      }
      if (url.endsWith('/logs')) {
        return Promise.resolve({ data: { logs: [{ line: 'started' }] } })
      }
      return Promise.resolve({
        data: {
          items: [
            {
              id: 'm-1',
              model_id: 'meta-llama/Llama-2-7b',
              name: 'Llama 2 7B',
              source: 'huggingface',
              parameters: '7B',
              license: 'llama2',
              download_status: 'completed',
              deploy_status: 'running',
              version: 'main',
              tags: [],
            },
          ],
          total: 1,
          page: 1,
          page_size: 100,
        },
      })
    })

    const wrapper = mountPage(DeployView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openStatus: (row: unknown) => Promise<void>
      openLogs: (row: unknown) => Promise<void>
      deployStatus: { status: string } | null
      deployLogs: Array<Record<string, unknown>>
    }
    const row = { id: 'm-1', model_id: 'meta-llama/Llama-2-7b', name: 'Llama 2 7B' }
    await vm.openStatus(row)
    await vm.openLogs(row)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models/meta-llama%2FLlama-2-7b/deploy-status`)
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/open-models/meta-llama%2FLlama-2-7b/logs`)
    expect(vm.deployStatus?.status).toBe('running')
    expect(vm.deployLogs[0]).toEqual({ line: 'started' })
  }, 20000)
})
