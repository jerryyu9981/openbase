/**
 * T-DM-01：画像模板停用后的影响面提示
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import ElementPlus, { ElMessage, ElMessageBox } from 'element-plus'

import { dpsApi } from '@/core/api/dps'
import DpsTemplateListView from '@/modules/portrait/pages/DpsTemplateListView.vue'

vi.setConfig({ testTimeout: 20_000 })

async function mountPage(): Promise<ReturnType<typeof mount>> {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push('/portrait/dps/templates')
  return mount(DpsTemplateListView as never, {
    attachTo: document.body,
    global: { plugins: [ElementPlus, router] },
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(dpsApi, 'listTemplates').mockResolvedValue({
    items: [{ code: 'cc-v1', name: '入矫画像', status: 'active', version: 3 }],
    total: 1,
  })
  vi.spyOn(dpsApi, 'getScoringConsistency').mockResolvedValue({
    total: 0,
    block: 0,
    warn: 0,
    items: [],
    issues: [],
  } as never)
  vi.spyOn(dpsApi, 'getTemplateLineage').mockResolvedValue({ gaps: { items: [] } } as never)
  vi.spyOn(dpsApi, 'listTemplateCategories').mockResolvedValue([])
  vi.spyOn(dpsApi, 'getTemplateCategoryTree').mockResolvedValue([])
  vi.spyOn(dpsApi, 'deactivateTemplate').mockResolvedValue({
    code: 'cc-v1',
    status: 'inactive',
    affected_annotation_templates: 2,
    parent_gate_enforced: true,
  } as never)
  vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
  vi.spyOn(ElMessage, 'success').mockImplementation(() => undefined as never)
  vi.spyOn(ElMessage, 'warning').mockImplementation(() => undefined as never)
  vi.spyOn(ElMessage, 'info').mockImplementation(() => undefined as never)
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('T-DM-01 停用影响面', () => {
  it('停用后提示受影响的标注模板数量', async () => {
    const wrapper = await mountPage()
    await flushPromises()

    await wrapper.find('[data-test="template-more"]').trigger('click')
    await flushPromises()
    const toggle = document.querySelector('[data-test="template-toggle"]') as HTMLElement | null
    expect(toggle).not.toBeNull()
    toggle?.click()
    await flushPromises()

    expect(dpsApi.deactivateTemplate).toHaveBeenCalledWith('cc-v1')
    expect(ElMessage.warning).toHaveBeenCalledWith(
      expect.stringContaining('2 个标注模板'),
    )
    wrapper.unmount()
  })
})
