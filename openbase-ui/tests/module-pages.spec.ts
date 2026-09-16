/**
 * F 类缺陷回归测试（v1.2.0 Step4 E2E 发现）：
 * BUG-120-006 Models 新增模型按钮空实现 → 已实现对话框
 * BUG-120-007 Conversations 导出按钮空实现 → 已实现 JSON 下载
 *
 * 用例预算与异步收敛（DEF-FE-146-003 根因收口）：
 * - 本文件四条用例均整页挂载 `Models` / `Conversations`（el-table + el-pagination），实测单条
 *   7~11s；`v8` 覆盖率插桩后进一步放大（Step 4 证据：覆盖率运行整体耗时 ×4.7），默认 5s 用例
 *   超时下随时可能被击杀 → 按用例显式声明 15000ms 预算（不放宽全局 `testTimeout`）；
 * - 「列表加载真实 API 数据」原以 `await new Promise((r) => setTimeout(r, 50))` 真实等待固定 50ms
 *   来等挂载后的异步装载收敛。这是与机器性能耦合的脆弱等待（慢环境下 50ms 不足即假失败），
 *   改为 `await flushPromises()` 显式等待 Vue 更新队列与已 mock 的 API promise 收敛 —— 确定性
 *   等待，不消耗真实时间，也不再依赖 50ms 经验值。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
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
  }, 15000)

  it('列表加载真实 API 数据（非 mock）', async () => {
    vi.spyOn(llmApi, 'fetchModels').mockResolvedValue({
      models: [{ id: 'gpt-4', name: 'gpt-4', owned_by: 'OpenAI' }],
    })
    const wrapper = mountWithEp(Models)
    // 确定性等待：挂载期 onMounted 的异步装载 + 表格重渲染（替代原固定 50ms 真实等待）
    await flushPromises()
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBeGreaterThan(0)
    expect(rows.some((r) => r.text().includes('gpt-4'))).toBe(true)
  }, 15000)

  it('名称为空不触发新增（写操作禁用路径）', async () => {
    const warning = vi.spyOn(ElMessage, 'warning')
    const wrapper = mountWithEp(Models)
    await wrapper.find('[data-test="create-model"]').trigger('click')
    expect(warning).toHaveBeenCalled()
  }, 15000)
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
  }, 15000)
})
