/**
 * S6-T3 FE-R1-1 UI 隔离回归断言（设计草案 §4.3 + §5.2 Q-FE-3b 判定表）
 *
 * 断言口径（四类呈现 + 无白屏）：
 * - 200 且空数据（他域不可见）→ 空态（明确空态文案，非错误态）；
 * - 403 / `PERM_*` / `AUTH_*`（定向越权）→ 页面级 403 提示；
 * - 404 → 「资源不存在」空态；
 * - 5xx → 错误条 + 重试；
 * - 任何分支容器内均有可见文案（无白屏），且不泄漏堆栈/原始 JSON；
 * - `request_id` 仅在页面详情内展示，不落入 URL / localStorage。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { defineComponent, type Component } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { createPinia, setActivePinia, type Pinia } from 'pinia'

import { classifyError, describeError, extractCodePrefix, type ErrorResponse } from '@/core/api/error'
import { http, tokenStore } from '@/core/api/http'
import { dpsApi } from '@/core/api/dps'
import { ragApi } from '@/core/api/rag'
import { llmApi } from '@/core/api/llm'
import PortraitList from '@/modules/portrait/pages/PortraitList.vue'
import PortraitDetail from '@/modules/portrait/pages/PortraitDetail.vue'
import MemoryList from '@/modules/memory/pages/MemoryList.vue'
import KnowledgeList from '@/modules/knowledge/pages/KnowledgeList.vue'
import Conversations from '@/modules/openllm/pages/Conversations.vue'
import ChatView from '@/modules/knowledge/pages/ChatView.vue'
import AppLayout from '@/core/layouts/AppLayout.vue'

let pinia: Pinia

/** 构造契约形状的 axios 错误（消费 http.ts 的 ErrorResponse 契约） */
function apiError(status: number, body: Partial<ErrorResponse> = {}): AxiosError<ErrorResponse> {
  const error = new AxiosError(
    `Request failed with status code ${status}`,
    'ERR_BAD_RESPONSE',
  ) as unknown as AxiosError<ErrorResponse>
  error.response = {
    data: {
      code: body.code ?? `SYS_HTTP_${status}`,
      message: body.message ?? `HTTP ${status}`,
      detail: body.detail ?? null,
      request_id: body.request_id ?? `req-${status}`,
    },
    status,
    statusText: '',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  } as never
  return error
}

async function mountPage(component: Component, path = '/portrait/list'): Promise<{ wrapper: VueWrapper; router: Router }> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/portrait/:id', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push(path)
  const wrapper = mount(component, {
    global: { plugins: [ElementPlus, router, pinia] },
  })
  await flushPromises()
  return { wrapper, router }
}

const healthyPortraitDeps = () => {
  vi.spyOn(dpsApi, 'getDpsHealth').mockResolvedValue({ status: 'healthy', version: 'v2.8.1' })
  vi.spyOn(dpsApi, 'getReportsOverview').mockResolvedValue({ total_profiles: 40, high_risk_count: 8 })
}

function expectNotBlank(wrapper: VueWrapper) {
  expect(wrapper.text().trim().length).toBeGreaterThan(0)
}

function expectNoStackLeak(wrapper: VueWrapper) {
  const text = wrapper.text()
  expect(text).not.toContain('{"')
  expect(text).not.toContain('at Object.')
  expect(text.toLowerCase()).not.toContain('stack')
}

beforeEach(() => {
  localStorage.clear()
  tokenStore.clear()
  pinia = createPinia()
  setActivePinia(pinia)
  vi.restoreAllMocks()
})

describe('S6-T3-4: 错误契约分类（error.ts）', () => {
  it('extractCodePrefix 识别 6 类错误码前缀', () => {
    expect(extractCodePrefix('AUTH_EXPIRED')).toBe('AUTH_')
    expect(extractCodePrefix('PERM_DENIED')).toBe('PERM_')
    expect(extractCodePrefix('PARAM_INVALID')).toBe('PARAM_')
    expect(extractCodePrefix('BIZ_RULE')).toBe('BIZ_')
    expect(extractCodePrefix('SYS_FAULT')).toBe('SYS_')
    expect(extractCodePrefix('STORAGE_FULL')).toBe('STORAGE_')
    expect(extractCodePrefix('UNKNOWN')).toBe('')
    expect(extractCodePrefix(undefined)).toBe('')
  })

  it('按 §5.1/§5.2 判定表映射 kind', () => {
    expect(classifyError(apiError(401, { code: 'AUTH_EXPIRED' })).kind).toBe('unauthorized')
    expect(classifyError(apiError(403, { code: 'PERM_DENIED' })).kind).toBe('forbidden')
    expect(classifyError(apiError(400, { code: 'PERM_DENIED' })).kind).toBe('forbidden')
    expect(classifyError(apiError(404)).kind).toBe('not-found')
    expect(classifyError(apiError(500, { code: 'SYS_FAULT' })).kind).toBe('server-error')
    expect(classifyError(apiError(503)).kind).toBe('server-error')
    expect(classifyError(apiError(422, { code: 'PARAM_INVALID' })).kind).toBe('invalid-param')
    expect(classifyError(apiError(400, { code: 'BIZ_RULE' })).kind).toBe('business')
  })

  it('网络/取消/未知分支', () => {
    const network = new AxiosError('Network Error', 'ERR_NETWORK')
    expect(classifyError(network).kind).toBe('network')
    const canceled = new AxiosError('canceled', AxiosError.ERR_CANCELED)
    expect(classifyError(canceled).kind).toBe('canceled')
    expect(classifyError(new Error('plain')).kind).toBe('unknown')
  })

  it('describeError 输出呈现语义（页面级/可重试/标题）', () => {
    expect(describeError(apiError(403, { code: 'PERM_DENIED', message: '越权' }))).toMatchObject({
      kind: 'forbidden',
      pageLevel: true,
      retryable: false,
      title: '无权限访问该资源',
      detail: '越权',
    })
    expect(describeError(apiError(404))).toMatchObject({ kind: 'not-found', pageLevel: false, title: '资源不存在或已被移除' })
    expect(describeError(apiError(500))).toMatchObject({ kind: 'server-error', retryable: true, title: '加载失败，请稍后重试' })
    expect(describeError(new AxiosError('Network Error', 'ERR_NETWORK'))).toMatchObject({ kind: 'network', retryable: true })
    expect(describeError(new Error('plain'))).toMatchObject({ kind: 'unknown', pageLevel: false, retryable: true })
  })

  it('request_id 仅在返回结构中透出，不写入 URL/localStorage', () => {
    const presentation = describeError(apiError(403, { request_id: 'req-trace-001' }))
    expect(presentation.requestId).toBe('req-trace-001')
    expect(window.location.href).not.toContain('req-trace-001')
    expect(JSON.stringify(localStorage)).not.toContain('req-trace-001')
  })
})

describe('S6-T3-1: 画像关键页跨域呈现', () => {
  it('200 且空数据 → 空态（他域不可见，非错误态）', async () => {
    healthyPortraitDeps()
    vi.spyOn(dpsApi, 'listPortraits').mockResolvedValue({ items: [], total: 0 })
    const { wrapper } = await mountPage(PortraitList)
    const empty = wrapper.find('[data-test="isolation-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('当前租户暂无数据')
    expect(wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(false)
    expectNotBlank(wrapper)
  })

  it('403 → 页面级 403 提示（含 request_id 详情，且不落 URL/localStorage）', async () => {
    healthyPortraitDeps()
    vi.spyOn(dpsApi, 'listPortraits').mockRejectedValue(
      apiError(403, { code: 'PERM_DENIED', message: '无权访问他域画像', request_id: 'req-403-portrait' }),
    )
    const { wrapper } = await mountPage(PortraitList)
    const forbidden = wrapper.find('[data-test="isolation-forbidden"]')
    expect(forbidden.exists()).toBe(true)
    expect(forbidden.text()).toContain('无权限访问')
    expect(wrapper.find('[data-test="error-request-id"]').text()).toContain('req-403-portrait')
    expect(window.location.href).not.toContain('req-403-portrait')
    expect(JSON.stringify(localStorage)).not.toContain('req-403-portrait')
    expectNotBlank(wrapper)
  })

  it('404 → 「资源不存在」空态（非错误态）', async () => {
    healthyPortraitDeps()
    vi.spyOn(dpsApi, 'listPortraits').mockRejectedValue(apiError(404))
    const { wrapper } = await mountPage(PortraitList)
    expect(wrapper.find('[data-test="isolation-not-found"]').text()).toContain('资源不存在')
    expect(wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(false)
    expectNotBlank(wrapper)
  })

  it('5xx → 错误条 + 重试，且不泄漏堆栈/原始 JSON', async () => {
    healthyPortraitDeps()
    vi.spyOn(dpsApi, 'listPortraits').mockRejectedValue(apiError(500, { code: 'SYS_FAULT', message: '内部异常' }))
    const { wrapper } = await mountPage(PortraitList)
    const bar = wrapper.find('[data-test="isolation-error-bar"]')
    expect(bar.exists()).toBe(true)
    expect(bar.text()).toContain('加载失败')
    expect(wrapper.find('[data-test="isolation-retry"]').exists()).toBe(true)
    expectNoStackLeak(wrapper)
    expectNotBlank(wrapper)
  })

  it('5xx 后点击重试恢复数据', async () => {
    healthyPortraitDeps()
    const spy = vi.spyOn(dpsApi, 'listPortraits')
    spy.mockRejectedValueOnce(apiError(500)).mockResolvedValueOnce({
      items: [{ person_id: 'P-1001', name: '测试画像', risk_level: '75', risk_score: 75, tags: ['demo'] }],
      total: 1,
    })
    const { wrapper } = await mountPage(PortraitList)
    expect(wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(true)
    await wrapper.find('[data-test="isolation-retry"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('测试画像')
  })

  it('画像详情 404 / 403 / 5xx 三分支呈现', async () => {
    vi.spyOn(dpsApi, 'getPortrait').mockRejectedValue(apiError(404))
    const notFound = await mountPage(PortraitDetail, '/portrait/P-404')
    expect(notFound.wrapper.find('[data-test="isolation-not-found"]').exists()).toBe(true)
    expectNotBlank(notFound.wrapper)

    vi.restoreAllMocks()
    vi.spyOn(dpsApi, 'getPortrait').mockRejectedValue(apiError(403, { code: 'PERM_DENIED' }))
    const forbidden = await mountPage(PortraitDetail, '/portrait/P-403')
    expect(forbidden.wrapper.find('[data-test="isolation-forbidden"]').exists()).toBe(true)
    expectNotBlank(forbidden.wrapper)

    vi.restoreAllMocks()
    vi.spyOn(dpsApi, 'getPortrait').mockRejectedValue(apiError(500))
    const serverError = await mountPage(PortraitDetail, '/portrait/P-500')
    expect(serverError.wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(true)
    expect(serverError.wrapper.find('[data-test="isolation-retry"]').exists()).toBe(true)
    expectNotBlank(serverError.wrapper)
  })
})

describe('S6-T3-2: 记忆关键页跨域呈现', () => {
  it('200 且空数据 → 空态（隔离生效）', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { code: 0, message: 'ok', data: { items: [], total: 0, page: 1, page_size: 10 } },
    })
    const { wrapper } = await mountPage(MemoryList, '/memory/list')
    const empty = wrapper.find('[data-test="isolation-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('当前租户暂无数据')
    expectNotBlank(wrapper)
  })

  it('403 → 页面级 403；5xx → 错误条 + 重试', async () => {
    vi.spyOn(http, 'get').mockRejectedValue(apiError(403, { code: 'PERM_DENIED', message: '无权查看' }))
    const forbidden = await mountPage(MemoryList, '/memory/list')
    expect(forbidden.wrapper.find('[data-test="isolation-forbidden"]').exists()).toBe(true)
    expectNotBlank(forbidden.wrapper)

    vi.restoreAllMocks()
    vi.spyOn(http, 'get').mockRejectedValue(apiError(500))
    const serverError = await mountPage(MemoryList, '/memory/list')
    expect(serverError.wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(true)
    expect(serverError.wrapper.find('[data-test="isolation-retry"]').exists()).toBe(true)
    expectNotBlank(serverError.wrapper)
  })
})

describe('S6-T3-3: 知识关键页跨域呈现', () => {
  it('200 且空数据 → 空态；403 → 页面级 403；5xx → 错误条 + 重试', async () => {
    vi.spyOn(ragApi, 'listCollections').mockResolvedValue({ items: [], total: 0 })
    const empty = await mountPage(KnowledgeList, '/knowledge/list')
    expect(empty.wrapper.find('[data-test="isolation-empty"]').text()).toContain('当前租户暂无数据')

    vi.restoreAllMocks()
    vi.spyOn(ragApi, 'listCollections').mockRejectedValue(apiError(403, { code: 'PERM_DENIED' }))
    const forbidden = await mountPage(KnowledgeList, '/knowledge/list')
    expect(forbidden.wrapper.find('[data-test="isolation-forbidden"]').exists()).toBe(true)

    vi.restoreAllMocks()
    vi.spyOn(ragApi, 'listCollections').mockRejectedValue(apiError(500))
    const serverError = await mountPage(KnowledgeList, '/knowledge/list')
    expect(serverError.wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(true)
    expect(serverError.wrapper.find('[data-test="isolation-retry"]').exists()).toBe(true)
    expectNotBlank(serverError.wrapper)
  })

  it('RAG 对话流式失败 → 错误条 + 重试，保留已产出内容（不断流成白屏）', async () => {
    vi.spyOn(ragApi, 'listCollections').mockResolvedValue({
      items: [{ id: 'kb-1', name: '知识库一', document_count: 3 }],
    })
    vi.spyOn(ragApi, 'queryStream').mockRejectedValue(apiError(500, { code: 'SYS_FAULT' }))
    const { wrapper } = await mountPage(ChatView, '/knowledge/chat')

    await wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'kb-1')
    await flushPromises()
    await wrapper.find('[data-test="chat-input"]').setValue('隔离测试问题')
    await wrapper.find('[data-test="send-message"]').trigger('click')
    await flushPromises()

    const bar = wrapper.find('[data-test="isolation-error-bar"]')
    expect(bar.exists()).toBe(true)
    expect(bar.text()).toContain('流式')
    expect(wrapper.find('[data-test="isolation-retry"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('隔离测试问题')
    expectNotBlank(wrapper)
  })
})

describe('S6-T3-3: 对话关键页（OpenLLM 会话）呈现', () => {
  it('200 且空数据 → 空态', async () => {
    vi.spyOn(llmApi, 'fetchModels').mockResolvedValue({ models: [] })
    vi.spyOn(llmApi, 'listConversations').mockResolvedValue({ items: [], total: 0 })
    const { wrapper } = await mountPage(Conversations, '/openllm/conversations')
    expect(wrapper.find('[data-test="isolation-empty"]').text()).toContain('当前租户暂无数据')
    expectNotBlank(wrapper)
  })

  it('403 → 页面级 403；5xx → 错误条 + 重试', async () => {
    vi.spyOn(llmApi, 'fetchModels').mockResolvedValue({ models: [] })
    vi.spyOn(llmApi, 'listConversations').mockRejectedValue(apiError(403, { code: 'PERM_DENIED' }))
    const forbidden = await mountPage(Conversations, '/openllm/conversations')
    expect(forbidden.wrapper.find('[data-test="isolation-forbidden"]').exists()).toBe(true)

    vi.restoreAllMocks()
    vi.spyOn(llmApi, 'fetchModels').mockResolvedValue({ models: [] })
    vi.spyOn(llmApi, 'listConversations').mockRejectedValue(apiError(503))
    const serverError = await mountPage(Conversations, '/openllm/conversations')
    expect(serverError.wrapper.find('[data-test="isolation-error-bar"]').exists()).toBe(true)
    expect(serverError.wrapper.find('[data-test="isolation-retry"]').exists()).toBe(true)
    expectNotBlank(serverError.wrapper)
  })
})

describe('S6-T3-4: 渲染异常兜底（防白屏）', () => {
  it('子页面渲染异常时 AppLayout 渲染兜底提示，不白屏', async () => {
    const BoomPage = defineComponent({
      name: 'BoomPage',
      setup() {
        throw new Error('render boom')
      },
      render: () => null,
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/boom', component: BoomPage }],
    })
    await router.push('/boom')
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const wrapper = mount(AppLayout, { global: { plugins: [ElementPlus, router, pinia] } })
    await flushPromises()

    expect(wrapper.find('[data-test="layout-render-fallback"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('页面加载失败')
    expectNotBlank(wrapper)
    errorSpy.mockRestore()
  })
})
