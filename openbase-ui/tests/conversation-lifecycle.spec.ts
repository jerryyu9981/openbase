/**
 * 批次 5：上下文（会话）生命周期回归
 *
 * 覆盖 AC-CTX-1~4：打开会话加载历史、发送后回写消息、加载失败可重试、归档会话提示。
 * 全部 mock 门户 API，不依赖后端。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const llmMocks = vi.hoisted(() => ({
  fetchModels: vi.fn(),
  listConversations: vi.fn(),
  listMessages: vi.fn(),
  sendChatStream: vi.fn(),
  createConversation: vi.fn(),
  archiveConversation: vi.fn(),
  deleteConversation: vi.fn(),
}))

const conversationMocks = vi.hoisted(() => ({
  getConversation: vi.fn(),
  appendMessage: vi.fn(),
}))

vi.mock('@/core/api/llm', () => ({ llmApi: llmMocks }))
vi.mock('@/core/api/conversation', () => ({ conversationApi: conversationMocks }))

import Conversations from '@/modules/openllm/pages/Conversations.vue'

// 全量并发跑时 Element Plus 挂载成本显著上升，显式放宽单用例超时（单跑 ~1s）
vi.setConfig({ testTimeout: 20_000 })

function mountPage() {
  return mount(Conversations as never, {
    global: {
      plugins: [ElementPlus],
      stubs: {
        PageContainer: { template: '<div><slot /></div>' },
        // 抽屉改为就地渲染，避免 teleport 与 Element Plus 内部弹层冲突
        ElDrawer: {
          props: ['modelValue', 'title'],
          template: '<div v-if="modelValue" data-test="drawer-stub"><slot /></div>',
        },
      },
    },
  })
}

const baseConversation = {
  id: 'c1',
  title: '需求评审',
  model: 'qwen2.5-7b',
  messages: 2,
  started_at: '2026-11-13T10:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  llmMocks.fetchModels.mockResolvedValue({ models: [] })
  llmMocks.listConversations.mockResolvedValue({ items: [baseConversation] })
  llmMocks.listMessages.mockResolvedValue([
    { role: 'user', content: '历史消息一' },
    { role: 'assistant', content: '历史回复一' },
  ])
  conversationMocks.getConversation.mockResolvedValue({ id: 'c1', title: '需求评审（详情）' })
  conversationMocks.appendMessage.mockResolvedValue({ role: 'assistant', content: 'ok' })
  llmMocks.sendChatStream.mockImplementation(
    async (_payload: unknown, onEvent: (evt: { event: string; data: string }) => void) => {
      onEvent({ event: 'chunk', data: JSON.stringify({ choices: [{ delta: { content: '你好呀' } }] }) })
    },
  )
})

describe('批次 5：会话查看与续聊', () => {
  it('打开会话并发加载详情与历史消息（AC-CTX-1）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="conversation-open"]').trigger('click')
    await flushPromises()

    expect(conversationMocks.getConversation).toHaveBeenCalledWith('c1')
    expect(llmMocks.listMessages).toHaveBeenCalledWith('c1')
    expect(wrapper.text()).toContain('历史消息一')
    expect(wrapper.text()).toContain('历史回复一')
    expect(wrapper.text()).toContain('需求评审（详情）')
  })

  it('发送消息后分别回写用户与助手消息（AC-CTX-2）', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('[data-test="conversation-open"]').trigger('click')
    await flushPromises()

    await wrapper.find('input[data-test="chat-input"]').setValue('你好')
    await wrapper.find('[data-test="chat-send"]').trigger('click')
    await flushPromises()

    expect(conversationMocks.appendMessage).toHaveBeenCalledTimes(2)
    expect(conversationMocks.appendMessage).toHaveBeenNthCalledWith(1, 'c1', {
      role: 'user',
      content: '你好',
      model_name: 'qwen2.5-7b',
    })
    expect(conversationMocks.appendMessage).toHaveBeenNthCalledWith(2, 'c1', {
      role: 'assistant',
      content: '你好呀',
      model_name: 'qwen2.5-7b',
    })
    expect(wrapper.text()).toContain('你好呀')
  })

  it('历史加载失败展示提示条与重试入口（AC-CTX-3）', async () => {
    llmMocks.listMessages.mockRejectedValue(new Error('500'))
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="conversation-open"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="history-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="history-retry"]').exists()).toBe(true)
  })

  it('归档会话展示提示且不发起续聊（AC-CTX-4）', async () => {
    llmMocks.listConversations.mockResolvedValue({
      items: [{ ...baseConversation, archived: true }],
    })
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="conversation-open"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="chat-archived-hint"]').exists()).toBe(true)

    await wrapper.find('input[data-test="chat-input"]').setValue('继续聊')
    await wrapper.find('[data-test="chat-send"]').trigger('click')
    await flushPromises()
    expect(llmMocks.sendChatStream).not.toHaveBeenCalled()
  })
})
