/**
 * T-DM-02：画像列表口径过期（stale）呈现与筛选
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const dpsMocks = vi.hoisted(() => ({
  listPortraits: vi.fn(),
  getDpsHealth: vi.fn(),
  getReportsOverview: vi.fn(),
  calculatePortrait: vi.fn(),
  waitPortraitTask: vi.fn(),
  getPortraitByExternal: vi.fn(),
  deletePortrait: vi.fn(),
  exportPortraitsCsv: vi.fn(),
}))

vi.mock('@/core/api/dps', () => ({ dpsApi: dpsMocks }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ params: {}, query: {} }),
}))

import PortraitList from '@/modules/portrait/pages/PortraitList.vue'

vi.setConfig({ testTimeout: 20_000 })

function mountList() {
  return mount(PortraitList as never, {
    global: {
      plugins: [ElementPlus],
      stubs: {
        PageContainer: { template: '<div><slot /></div>' },
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  dpsMocks.getDpsHealth.mockResolvedValue({ status: 'ok' })
  dpsMocks.getReportsOverview.mockResolvedValue({})
  dpsMocks.listPortraits.mockResolvedValue({
    items: [
      { person_id: 'P-1', name: '过期画像', stale: true, stale_reason: 'version_mismatch' },
      { person_id: 'P-2', name: '一致画像', stale: false },
    ],
    total: 2,
  })
})

describe('T-DM-02 画像口径过期', () => {
  it('stale=true 渲染「口径已过期」标签', async () => {
    const wrapper = mountList()
    await flushPromises()

    const tags = wrapper.findAll('[data-test="portrait-stale-tag"]')
    expect(tags).toHaveLength(1)
    expect(tags[0].text()).toContain('口径已过期')
    expect(wrapper.text()).toContain('一致')
  })

  it('开启「仅看过期」后按默认模板口径请求 stale=true', async () => {
    const wrapper = mountList()
    await flushPromises()

    const input = wrapper.find('[data-test="portrait-stale-switch"] input')
    await input.setValue(true)
    await flushPromises()

    const calls = dpsMocks.listPortraits.mock.calls
    const lastCall = calls[calls.length - 1]?.[0]
    expect(lastCall).toMatchObject({
      template_code: 'dps-correction-v1',
      stale: true,
    })
  })
})
