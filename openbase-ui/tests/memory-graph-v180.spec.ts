/**
 * v7.8.0 P6：记忆图谱真实数据源回归。
 * 覆盖：overview 渲染（节点/统计）、空图提示、加载失败提示。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), push: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: { get: mocks.get, post: vi.fn(), put: vi.fn() } }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: mocks.push }) }))

import MemoryGraph from '@/modules/memory/pages/MemoryGraph.vue'

const envelope = (data: unknown) => ({ data: { code: 0, message: 'success', data } })

const overview = {
  nodes: [
    { id: 'mem-1', label: 'OpenBase 使用 Neo4j', node_type: 'memory', memory_type: 'persistent', content: 'OpenBase 使用 Neo4j', updated_at: '2026-10-22T10:00:00Z' },
    { id: 'entity:tenant-1:openbase', label: 'OpenBase', node_type: 'organization', content: 'OpenBase' },
  ],
  edges: [{ source: 'mem-1', target: 'entity:tenant-1:openbase', relation: 'MENTIONS' }],
  stats: { memory_nodes: 1, entity_nodes: 1, edges: 1, outbox_pending: 2, outbox_dead: 0 },
}

function mountGraph() {
  return mount(MemoryGraph, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => vi.clearAllMocks())

describe('v7.8.0 记忆图谱真实数据源', () => {
  it('渲染 overview 统计与节点，展示待投影提示', async () => {
    mocks.get.mockResolvedValueOnce(envelope(overview))

    const wrapper = mountGraph()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/memory-proxy/graph/overview', { params: { limit: 120 } })
    const statsText = wrapper.find('[data-test="graph-stats"]').text()
    expect(statsText).toContain('记忆节点')
    expect(statsText).toContain('实体节点')
    expect(wrapper.find('[data-test="graph-pending-alert"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="graph-empty"]').exists()).toBe(false)
    expect(wrapper.findAll('.graph-node').length).toBe(2)
  }, 20000)

  it('空图谱展示引导文案', async () => {
    mocks.get.mockResolvedValueOnce(
      envelope({ nodes: [], edges: [], stats: { memory_nodes: 0, entity_nodes: 0, edges: 0, outbox_pending: 0, outbox_dead: 0 } }),
    )

    const wrapper = mountGraph()
    await flushPromises()

    expect(wrapper.find('[data-test="graph-empty"]').exists()).toBe(true)
  }, 20000)

  it('加载失败展示错误提示', async () => {
    mocks.get.mockRejectedValueOnce({ response: { data: { message: '图库不可用' } } })

    const wrapper = mountGraph()
    await flushPromises()

    expect(wrapper.find('[data-test="graph-error"]').text()).toContain('图库不可用')
    expect(wrapper.find('[data-test="graph-empty"]').exists()).toBe(true)
  }, 20000)
})
