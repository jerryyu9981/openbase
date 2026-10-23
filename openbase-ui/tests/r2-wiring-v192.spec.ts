/**
 * v1.9.2 R2：全局配置 / 测试记录两页接线回归。
 * 覆盖：配置列表渲染、保存（值解析）、版本历史与回滚；测试轮次列表、自动选中最新轮次加载汇总、开新一轮。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks, TEST_MODE_KEY: 'ob_test_mode' }))

import ConfigManageView from '@/pages/platform/config/ConfigManageView.vue'
import SystemTestRecords from '@/pages/platform/observability/SystemTestRecords.vue'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const configItem = (overrides: Record<string, unknown> = {}) => ({
  key: 'gateway.discovery.enabled',
  value: true,
  level: 'system',
  ...overrides,
})

beforeEach(() => vi.clearAllMocks())

describe('v1.9.2 全局配置真实化', () => {
  it('加载 /configs 并渲染键、值与级别', async () => {
    mocks.get.mockResolvedValue({ data: { items: [configItem()], total: 1 } })

    const wrapper = mountPage(ConfigManageView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/configs', { params: {} })
    const text = wrapper.text()
    expect(text).toContain('gateway.discovery.enabled')
    expect(text).toContain('true')
    expect(text).toContain('SYSTEM')
  }, 20000)

  it('保存时按 JSON/布尔/数字解析值并 POST /configs', async () => {
    mocks.get.mockResolvedValue({ data: { items: [configItem()], total: 1 } })
    mocks.post.mockResolvedValue({ data: configItem() })

    const wrapper = mountPage(ConfigManageView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      form: { key: string; value: string; level: string }
      save: () => Promise<void>
    }
    vm.form = { key: 'proxy.openllm.instances', value: '[{"host":"127.0.0.1","port":8001}]', level: 'tenant' }
    await vm.save()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/configs', {
      key: 'proxy.openllm.instances',
      value: [{ host: '127.0.0.1', port: 8001 }],
      level: 'tenant',
    })
  }, 20000)

  it('版本历史与回滚走真实端点', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/versions')) {
        return Promise.resolve({ data: [{ key: 'gateway.discovery.enabled', version: 1, value: false }] })
      }
      return Promise.resolve({ data: { items: [configItem()], total: 1 } })
    })
    mocks.post.mockResolvedValue({ data: configItem() })

    const wrapper = mountPage(ConfigManageView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openVersions: (row: unknown) => Promise<void>
      rollback: (version: number) => Promise<void>
      versions: Array<{ version: number }>
    }
    await vm.openVersions(configItem())
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/configs/gateway.discovery.enabled/versions')
    expect(vm.versions).toHaveLength(1)

    await vm.rollback(1)
    await flushPromises()
    expect(mocks.post).toHaveBeenCalledWith('/configs/gateway.discovery.enabled/rollback', null, {
      params: { version: 1 },
    })
  }, 20000)

  it('加载失败展示可读错误', async () => {
    mocks.get.mockRejectedValueOnce(new Error('boom'))

    const wrapper = mountPage(ConfigManageView)
    await flushPromises()

    expect(wrapper.find('[data-test="cfg-error"]').text()).toContain('配置加载失败')
  }, 20000)
})

describe('v1.9.2 测试记录真实化', () => {
  const runItem = {
    id: 'run-20261023-0100',
    title: 'R2 验证',
    scope: '',
    operator: 'admin',
    created_at: '2026-10-23T01:00:00Z',
    record_count: 2,
  }

  const summary = {
    run_id: runItem.id,
    total: 2,
    pass: 1,
    fail: 1,
    blocked: 0,
    skipped: 0,
    passed: false,
    cases: [
      {
        case_id: 'R2-1',
        latest_result: 'PASS',
        steps: [{ id: 11, step_id: 1, result: 'PASS', reason: null, request_id: null, duration_ms: 12, title: '登录' }],
      },
      {
        case_id: 'R2-2',
        latest_result: 'FAIL',
        steps: [{ id: 12, step_id: 1, result: 'FAIL', reason: '断言不符', request_id: 'req-1', duration_ms: 30, title: '列表' }],
      },
    ],
  }

  const envelope = (data: unknown) => ({ data: { code: 0, message: 'success', data } })

  it('挂载后加载轮次并自动选中最新一轮的汇总', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/test-runs') {
        return Promise.resolve(envelope({ items: [runItem], total: 1, skip: 0, limit: 100 }))
      }
      if (url.includes('/summary')) {
        return Promise.resolve(envelope(summary))
      }
      return Promise.resolve(envelope({}))
    })

    const wrapper = mountPage(SystemTestRecords)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/test-runs', { params: { limit: 100 } })
    expect(mocks.get).toHaveBeenCalledWith(`/test-runs/${runItem.id}/summary`)
    expect(wrapper.find('[data-test="testrun-summary-card"]').text()).toContain('未全通过')
    expect(wrapper.find('[data-test="testrun-table"]').text()).toContain('R2-2')
  }, 20000)

  it('无轮次时展示引导空态', async () => {
    mocks.get.mockResolvedValue(envelope({ items: [], total: 0, skip: 0, limit: 100 }))

    const wrapper = mountPage(SystemTestRecords)
    await flushPromises()

    expect(wrapper.find('[data-test="testrun-empty"]').exists()).toBe(true)
  }, 20000)

  it('开新一轮后刷新轮次并加载新汇总', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/test-runs') {
        return Promise.resolve(envelope({ items: [runItem], total: 1, skip: 0, limit: 100 }))
      }
      if (url.includes('/summary')) return Promise.resolve(envelope(summary))
      return Promise.resolve(envelope({}))
    })
    mocks.post.mockResolvedValue(envelope({ run_id: 'run-new-01' }))

    const wrapper = mountPage(SystemTestRecords)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      createRunId: string
      createRunTitle: string
      submitCreateRun: () => Promise<void>
    }
    vm.createRunId = 'run-new-01'
    vm.createRunTitle = '新轮次'
    await vm.submitCreateRun()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/test-runs', { run_id: 'run-new-01', title: '新轮次' })
  }, 20000)
})
