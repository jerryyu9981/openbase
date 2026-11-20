/**
 * 批次 5：画像全生命周期回归
 *
 * 覆盖 AC-POR-1~5：计算（异步轮询/同步返回）、按外部 ID 查询跳转、
 * 属性 PATCH（If-Match）与 409 冲突重载。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'

const dpsMocks = vi.hoisted(() => ({
  listPortraits: vi.fn(),
  getDpsHealth: vi.fn(),
  getReportsOverview: vi.fn(),
  calculatePortrait: vi.fn(),
  waitPortraitTask: vi.fn(),
  getPortraitByExternal: vi.fn(),
  getPortrait: vi.fn(),
  updatePortrait: vi.fn(),
  deletePortrait: vi.fn(),
}))

const pushMock = vi.hoisted(() => vi.fn())
const replaceMock = vi.hoisted(() => vi.fn())

vi.mock('@/core/api/dps', () => ({ dpsApi: dpsMocks }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  useRoute: () => ({ params: { id: 'P-1' } }),
}))

import PortraitList from '@/modules/portrait/pages/PortraitList.vue'
import PortraitDetail from '@/modules/portrait/pages/PortraitDetail.vue'

// 全量并发跑时 Element Plus 挂载成本显著上升，显式放宽单用例超时（单跑 ~1s）
vi.setConfig({ testTimeout: 20_000 })

const dialogStub = {
  props: ['modelValue', 'title'],
  template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>',
}
const drawerStub = {
  props: ['modelValue', 'title'],
  template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>',
}

function mountList() {
  return mount(PortraitList as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' }, ElDialog: dialogStub },
      mocks: { $router: { push: pushMock } },
    },
  })
}

function mountDetail() {
  return mount(PortraitDetail as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' }, ElDrawer: drawerStub },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  dpsMocks.listPortraits.mockResolvedValue({ items: [], total: 0 })
  dpsMocks.getDpsHealth.mockResolvedValue({ status: 'ok' })
  dpsMocks.getReportsOverview.mockResolvedValue({})
  dpsMocks.getPortrait.mockResolvedValue({
    person_id: 'P-1',
    name: '张三',
    version: 3,
    attributes: { level: '高' },
    dimensions: {},
  })
  dpsMocks.updatePortrait.mockResolvedValue({ person_id: 'P-1', version: 4 })
  dpsMocks.deletePortrait.mockResolvedValue({ person_id: 'P-1', status: 'deleted', already_deleted: false })
  vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
})

describe('批次 5：画像计算与外部 ID 查询', () => {
  it('异步计算返回 task_id 时轮询至完成并刷新列表（AC-POR-1/2）', async () => {
    dpsMocks.calculatePortrait.mockResolvedValue({ task_id: 'task-1', status: 'pending' })
    dpsMocks.waitPortraitTask.mockResolvedValue({ task_id: 'task-1', status: 'succeeded' })
    const wrapper = mountList()
    await flushPromises()

    await wrapper.find('[data-test="portrait-calculate-open"]').trigger('click')
    await wrapper.find('input[data-test="calc-person-id"]').setValue('P-2')
    await wrapper.find('[data-test="calc-submit"]').trigger('click')
    await flushPromises()

    expect(dpsMocks.calculatePortrait).toHaveBeenCalledWith({ person_id: 'P-2' })
    expect(dpsMocks.waitPortraitTask).toHaveBeenCalledWith('task-1')
    // 初次加载 1 次 + 计算完成后刷新 1 次
    expect(dpsMocks.listPortraits).toHaveBeenCalledTimes(2)
  })

  it('同步返回结果时不轮询，直接刷新（AC-POR-2）', async () => {
    dpsMocks.calculatePortrait.mockResolvedValue({ overall_score: 88 })
    const wrapper = mountList()
    await flushPromises()

    await wrapper.find('[data-test="portrait-calculate-open"]').trigger('click')
    await wrapper.find('input[data-test="calc-person-id"]').setValue('P-3')
    const templateSelect = wrapper.findComponent('[data-test="calc-template-code"]') as unknown as VueWrapper
    templateSelect.vm.$emit('update:modelValue', 'tpl-1')
    await flushPromises()
    await wrapper.find('[data-test="calc-submit"]').trigger('click')
    await flushPromises()

    expect(dpsMocks.calculatePortrait).toHaveBeenCalledWith({ person_id: 'P-3', template_code: 'tpl-1' })
    expect(dpsMocks.waitPortraitTask).not.toHaveBeenCalled()
    expect(dpsMocks.listPortraits).toHaveBeenCalledTimes(2)
  })

  it('按外部 ID 命中后跳转画像详情（AC-POR-3）', async () => {
    dpsMocks.getPortraitByExternal.mockResolvedValue({ person_id: 'P-9' })
    const wrapper = mountList()
    await flushPromises()

    await wrapper.find('[data-test="portrait-external-open"]').trigger('click')
    await wrapper.find('input[data-test="external-id"]').setValue('ext-9')
    await wrapper.find('[data-test="external-submit"]').trigger('click')
    await flushPromises()

    expect(dpsMocks.getPortraitByExternal).toHaveBeenCalledWith('ext-9')
    expect(pushMock).toHaveBeenCalledWith('/portrait/P-9')
  })
})

describe('批次 5：画像属性编辑', () => {
  it('PATCH 携带 If-Match 版本并刷新（AC-POR-4）', async () => {
    const wrapper = mountDetail()
    await flushPromises()

    expect(wrapper.text()).toContain('画像版本')
    await wrapper.find('[data-test="portrait-edit-open"]').trigger('click')
    await wrapper.find('[data-test="portrait-edit-json-mode"]').trigger('click')
    await flushPromises()
    await wrapper.find('textarea[data-test="portrait-edit-json"]').setValue('{"level":"中"}')
    await wrapper.find('[data-test="portrait-edit-save"]').trigger('click')
    await flushPromises()

    expect(dpsMocks.updatePortrait).toHaveBeenCalledWith(
      'P-1',
      { business: { attributes: { level: '中' } } },
      3,
    )
    expect(dpsMocks.getPortrait).toHaveBeenCalledTimes(2)
  })

  it('非法 JSON 前端拦截，不发起 PATCH（AC-POR-5）', async () => {
    const wrapper = mountDetail()
    await flushPromises()

    await wrapper.find('[data-test="portrait-edit-open"]').trigger('click')
    await wrapper.find('[data-test="portrait-edit-json-mode"]').trigger('click')
    await flushPromises()
    await wrapper.find('textarea[data-test="portrait-edit-json"]').setValue('{bad json')
    await wrapper.find('[data-test="portrait-edit-save"]').trigger('click')
    await flushPromises()

    expect(dpsMocks.updatePortrait).not.toHaveBeenCalled()
  })

  it('列表删除画像需确认并刷新（批次 5.1 DELETE）', async () => {
    dpsMocks.listPortraits.mockResolvedValue({
      items: [{ person_id: 'P-1', name: '张三', tags: [] }],
      total: 1,
    })
    const wrapper = mountList()
    await flushPromises()

    await wrapper.find('[data-test="portrait-delete"]').trigger('click')
    await flushPromises()

    expect(ElMessageBox.confirm).toHaveBeenCalled()
    expect(dpsMocks.deletePortrait).toHaveBeenCalledWith('P-1')
    // 初次加载 1 次 + 删除后刷新 1 次
    expect(dpsMocks.listPortraits).toHaveBeenCalledTimes(2)
  })

  it('详情删除画像后返回列表（批次 5.1 DELETE）', async () => {
    const wrapper = mountDetail()
    await flushPromises()

    await wrapper.find('[data-test="portrait-delete-open"]').trigger('click')
    await flushPromises()

    expect(ElMessageBox.confirm).toHaveBeenCalled()
    expect(dpsMocks.deletePortrait).toHaveBeenCalledWith('P-1')
    expect(replaceMock).toHaveBeenCalledWith('/portrait')
  })

  it('409 版本冲突时提示并重新加载（AC-POR-5）', async () => {
    dpsMocks.updatePortrait.mockRejectedValue({ response: { status: 409 } })
    const wrapper = mountDetail()
    await flushPromises()

    await wrapper.find('[data-test="portrait-edit-open"]').trigger('click')
    await wrapper.find('[data-test="portrait-edit-json-mode"]').trigger('click')
    await flushPromises()
    await wrapper.find('textarea[data-test="portrait-edit-json"]').setValue('{"level":"低"}')
    await wrapper.find('[data-test="portrait-edit-save"]').trigger('click')
    await flushPromises()

    expect(dpsMocks.getPortrait).toHaveBeenCalledTimes(2)
  })
})
