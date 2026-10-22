/**
 * v7.8.0 P5：记忆搜索展示图谱命中语义。
 * 覆盖：记忆命中显示 matched_entity；孤立实体结果不提供详情入口。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ post: vi.fn(), push: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: { get: vi.fn(), post: mocks.post, put: vi.fn() } }))

import MemorySearch from '@/modules/memory/pages/MemorySearch.vue'

const envelope = (data: unknown) => ({ data: { code: 0, message: 'success', data } })

beforeEach(() => vi.clearAllMocks())

describe('v7.8.0 记忆搜索图谱命中展示', () => {
  it('记忆命中展示命中实体，实体节点不提供详情入口', async () => {
    mocks.post.mockResolvedValueOnce(
      envelope({
        results: [
          {
            memory_id: '11111111-1111-4111-8111-111111111111',
            content: 'OpenBase 使用 Neo4j',
            score: 0.9,
            memory_type: 'persistent',
            source: 'graph',
            tags: [],
            entities: [],
            metadata: { node_type: 'memory', matched_entity: 'OpenBase' },
          },
          {
            memory_id: 'entity:tenant-1:openbase',
            content: 'OpenBase',
            score: 0.8,
            memory_type: 'graph',
            source: 'graph',
            tags: [],
            entities: [],
            metadata: { node_type: 'custom' },
          },
        ],
      }),
    )

    const wrapper = mount(MemorySearch, {
      global: {
        plugins: [ElementPlus],
        mocks: { $router: { push: mocks.push } },
        stubs: { PageContainer: { template: '<div><slot /></div>' } },
      },
    })
    await wrapper.find('[data-test="search-query"]').setValue('OpenBase')
    await wrapper.find('[data-test="search-run"]').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/memory-proxy/recall', {
      query: 'OpenBase',
      top_k: 10,
      strategy: 'semantic',
    })
    expect(wrapper.text()).toContain('实体：OpenBase')
    expect(wrapper.text()).toContain('实体节点')
    const detailButtons = wrapper.findAll('[data-test="search-detail"]')
    expect(detailButtons.length).toBe(1)
  }, 30000)
})
