/**
 * F 类缺陷回归测试（v1.2.0 Step4 E2E 发现）：
 * BUG-120-006 Models 新增模型按钮空实现 → 已实现对话框
 * BUG-120-007 Conversations 导出按钮空实现 → 已实现 JSON 下载
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus, { ElMessage } from 'element-plus'
import Models from '@/modules/openllm/pages/Models.vue'
import Conversations from '@/modules/openllm/pages/Conversations.vue'

const mountWithEp = (component: typeof Models | typeof Conversations) =>
  mount(component, { global: { plugins: [ElementPlus] } })

describe('BUG-120-006: 模型管理新增模型', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('点击新增模型弹出对话框', async () => {
    const wrapper = mountWithEp(Models)
    await wrapper.find('[data-test="create-model"]').trigger('click')
    expect(wrapper.find('[data-test="create-model-dialog"]').exists()).toBe(true)
  })

  it('填写表单创建模型成功（列表新增）', async () => {
    const success = vi.spyOn(ElMessage, 'success')
    const wrapper = mountWithEp(Models)
    await wrapper.find('[data-test="create-model"]').trigger('click')
    await wrapper.find('.el-dialog input').setValue('claude-3.5')
    const inputs = wrapper.findAll('.el-form input')
    await inputs[1].setValue('Anthropic')
    await wrapper.find('[data-test="create-model-submit"]').trigger('click')
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.some((r) => r.text().includes('claude-3.5'))).toBe(true)
    expect(success).toHaveBeenCalled()
  })

  it('名称为空时提示且不新增', async () => {
    const warning = vi.spyOn(ElMessage, 'warning')
    const wrapper = mountWithEp(Models)
    await wrapper.find('[data-test="create-model"]').trigger('click')
    await wrapper.find('[data-test="create-model-submit"]').trigger('click')
    expect(warning).toHaveBeenCalled()
    expect(wrapper.findAll('.el-table__row').length).toBe(3)
  })
})

describe('BUG-120-007: 对话导出 JSON', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('点击导出触发下载并提示成功', async () => {
    const createObjectURL = vi.fn(() => 'blob:mock')
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL: vi.fn() })
    const success = vi.spyOn(ElMessage, 'success')
    const wrapper = mountWithEp(Conversations)
    await wrapper.find('[data-test="export-conversations"]').trigger('click')
    expect(createObjectURL).toHaveBeenCalled()
    expect(success).toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})
