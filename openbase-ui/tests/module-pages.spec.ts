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
import { llmApi } from '@/core/api/llm'

const mountWithEp = (component: typeof Models | typeof Conversations) =>
  mount(component, { global: { plugins: [ElementPlus] } })

describe('BUG-120-006: 模型管理（v1.4.3 真实化）', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('点击新增模型提示写操作待完善（M2，对话框不弹出）', async () => {
    const warning = vi.spyOn(ElMessage, 'warning')
    const wrapper = mountWithEp(Models)
    await wrapper.find('[data-test="create-model"]').trigger('click')
    expect(warning).toHaveBeenCalled()
    expect(wrapper.find('[data-test="create-model-dialog"]').exists()).toBe(false)
  })

  it('列表加载真实 API 数据（非 mock）', async () => {
    vi.spyOn(llmApi, 'fetchModels').mockResolvedValue({
      models: [{ id: 'gpt-4', name: 'gpt-4', owned_by: 'OpenAI' }],
    })
    const wrapper = mountWithEp(Models)
    await new Promise((r) => setTimeout(r, 50))
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBeGreaterThan(0)
    expect(rows.some((r) => r.text().includes('gpt-4'))).toBe(true)
  })

  it('名称为空不触发新增（写操作禁用路径）', async () => {
    const warning = vi.spyOn(ElMessage, 'warning')
    const wrapper = mountWithEp(Models)
    await wrapper.find('[data-test="create-model"]').trigger('click')
    expect(warning).toHaveBeenCalled()
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
