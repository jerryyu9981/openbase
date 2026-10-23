/**
 * v1.10.2（OB-02）：聚合网关测试页交互用例。
 * 覆盖：成功、部分步骤失败、请求超时/异常三类路径。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import GatewayAggregateView from '@/pages/platform/observability/GatewayAggregateView.vue'

function mountPage() {
  return mount(GatewayAggregateView as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => vi.clearAllMocks())

describe('v1.10.2 聚合网关交互', () => {
  it('成功执行：透传步骤/超时/失败策略与映射，渲染结果且无错误条', async () => {
    mocks.post.mockResolvedValue({
      data: { code: 0, data: { result: { model_total: 3, kb_total: 2 }, errors: [] } },
    })

    const wrapper = mountPage()
    await wrapper.find('[data-test="agg-execute"]').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/gateway/aggregate', {
      steps: [
        { id: 'models', system: 'openllm', path: '/models', method: 'GET', timeout_ms: 2000 },
        { id: 'kbs', system: 'openrag', path: '/kb/list', method: 'GET', timeout_ms: 2000 },
      ],
      timeout_ms: 5000,
      on_partial_failure: 'return_errors',
      mapping: { model_total: '${models.data.total}', kb_total: '${kbs.data.total}' },
    })
    expect(wrapper.find('[data-test="agg-result"]').text()).toContain('"model_total": 3')
    expect(wrapper.find('[data-test="agg-errors"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="agg-error"]').exists()).toBe(false)
  }, 20000)

  it('部分失败：展示 errors 列表且保留成功结果', async () => {
    mocks.post.mockResolvedValue({
      data: {
        code: 0,
        data: { result: { model_total: 3 }, errors: ['openrag: connection refused'] },
      },
    })

    const wrapper = mountPage()
    await wrapper.find('[data-test="agg-execute"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="agg-errors"]').text()).toContain('部分步骤失败（1）')
    expect(wrapper.find('[data-test="agg-errors"]').text()).toContain('connection refused')
    expect(wrapper.find('[data-test="agg-result"]').text()).toContain('"model_total": 3')
  }, 20000)

  it('请求超时：展示错误条且不残留结果，按钮回到可执行态', async () => {
    mocks.post.mockRejectedValue(new Error('timeout of 5000ms exceeded'))

    const wrapper = mountPage()
    await wrapper.find('[data-test="agg-execute"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="agg-error"]').text()).toContain('timeout of 5000ms exceeded')
    expect(wrapper.find('[data-test="agg-result"]').exists()).toBe(false)
    const vm = wrapper.vm as unknown as { executing: boolean }
    expect(vm.executing).toBe(false)
  }, 20000)

  it('重置清空结果与错误条', async () => {
    mocks.post.mockResolvedValue({ data: { code: 0, data: { result: { a: 1 }, errors: ['x'] } } })

    const wrapper = mountPage()
    await wrapper.find('[data-test="agg-execute"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-test="agg-result"]').exists()).toBe(true)

    await wrapper.find('[data-test="agg-reset"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="agg-result"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="agg-errors"]').exists()).toBe(false)
  }, 20000)
})
