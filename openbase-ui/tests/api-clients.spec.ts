/**
 * api 层客户端覆盖补测（S6-T3/T6 Q-S6-D4：优先补 router/** 与 api/**）
 *
 * 以 mock `@/core/api/http` 的方式逐方法打通 dps / rag / llm / auth / gateway 客户端，
 * 补齐 api/** 的函数与语句覆盖（不改门禁阈值）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  tokenSet: vi.fn(),
  tokenClear: vi.fn(),
}))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get, post: mocks.post, put: mocks.put, delete: mocks.delete },
  tokenStore: { set: mocks.tokenSet, clear: mocks.tokenClear, access: '', refresh: '' },
}))

import { authApi, modulesApi } from '@/core/api/auth'
import { dpsApi } from '@/core/api/dps'
import { ragApi } from '@/core/api/rag'
import { llmApi, parseSseStream } from '@/core/api/llm'
import { gatewayApi } from '@/core/api/gateway'

const ok = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

beforeEach(() => {
  vi.clearAllMocks()
  mocks.get.mockResolvedValue(ok({}))
  mocks.post.mockResolvedValue(ok({}))
  mocks.put.mockResolvedValue(ok({}))
  mocks.delete.mockResolvedValue(ok({}))
})

describe('authApi / modulesApi', () => {
  it('login 写入 token 并拉取用户', async () => {
    mocks.post.mockResolvedValueOnce({ data: { access_token: 'a1', refresh_token: 'r1' } })
    mocks.get.mockResolvedValueOnce({ data: { id: 1, username: 'admin', permissions: ['*'] } })
    const user = await authApi.login('admin', 'pw')
    expect(user.username).toBe('admin')
    expect(mocks.tokenSet).toHaveBeenCalledWith('a1', 'r1')
  })

  it('me 返回用户', async () => {
    mocks.get.mockResolvedValueOnce({ data: { id: 2, username: 'alice', permissions: [] } })
    expect((await authApi.me()).username).toBe('alice')
  })

  it('modulesApi.list 返回 items', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [{ id: 'memory' }], total: 1 }))
    const items = await modulesApi.list()
    expect(items[0].id).toBe('memory')
  })
})

describe('dpsApi', () => {
  it('覆盖全部端点', async () => {
    mocks.get.mockResolvedValue(ok({ items: [] }))
    await dpsApi.listPortraits({ page: 1, page_size: 10 })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/portraits', { params: { page: 1, page_size: 10 } })

    mocks.get.mockResolvedValue(ok({ person_id: 'P-1' }))
    expect((await dpsApi.getPortrait('P-1')).person_id).toBe('P-1')

    mocks.post.mockResolvedValue(ok({ ok: true }))
    await dpsApi.calculatePortrait({ person_id: 'P-1' })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/portraits/calculate', { person_id: 'P-1' })

    mocks.get.mockResolvedValue(ok({ items: [] }))
    await dpsApi.listTagCategories()

    mocks.post.mockResolvedValue(ok({ id: 't1' }))
    await dpsApi.createTagCategory({ name: '标签' })

    mocks.put.mockResolvedValue(ok({ id: 't1' }))
    await dpsApi.updateTagCategory('t1', { name: '新标签' })
    expect(mocks.put).toHaveBeenCalledWith('/dps-proxy/tags/categories/t1', { name: '新标签' })

    mocks.delete.mockResolvedValue(ok({ deleted: true }))
    await dpsApi.deleteTagCategory('t1')

    mocks.get.mockResolvedValue(ok({ total_profiles: 1 }))
    await dpsApi.getReportsOverview()

    mocks.get.mockResolvedValue(ok({ status: 'running' }))
    await dpsApi.getBatchTaskStatus('task-1')

    mocks.get.mockResolvedValue(ok({ items: [] }))
    await dpsApi.listAuditLogs()

    mocks.get.mockResolvedValue(ok({ status: 'healthy' }))
    expect((await dpsApi.getDpsHealth()).status).toBe('healthy')
  })
})

describe('ragApi', () => {
  it('覆盖全部端点（含 SSE 流式与兜底）', async () => {
    mocks.get.mockResolvedValue(ok({ items: [] }))
    await ragApi.listCollections({ page: 1, page_size: 10 })

    mocks.post.mockResolvedValue(ok({ id: 'kb-1' }))
    await ragApi.createCollection({ name: 'kb' })

    mocks.get.mockResolvedValue(ok({ id: 'kb-1' }))
    expect((await ragApi.getCollection('kb-1')).id).toBe('kb-1')

    mocks.delete.mockResolvedValue(ok({ deleted: true }))
    await ragApi.deleteCollection('kb-1')

    mocks.post.mockResolvedValue(ok({ status: 'PENDING', document_id: 'd1' }))
    const file = new File(['content'], 'a.txt', { type: 'text/plain' })
    expect((await ragApi.uploadDocument('kb-1', file)).status).toBe('PENDING')

    mocks.get.mockResolvedValue(ok({ items: [] }))
    await ragApi.listDocuments('kb-1', { page: 1 })

    mocks.get.mockResolvedValue(ok({ id: 'd1' }))
    await ragApi.getDocument('kb-1', 'd1')

    mocks.delete.mockResolvedValue(ok({ deleted: true }))
    await ragApi.deleteDocument('kb-1', 'd1')

    mocks.post.mockResolvedValue(ok({ answer: 'a' }))
    await ragApi.query('kb-1', { query: 'q' })

    mocks.post.mockResolvedValue(ok({ items: [] }))
    await ragApi.retrieve('kb-1', { query: 'q', top_k: 3 })

    mocks.get.mockResolvedValue(ok({ status: 'healthy' }))
    expect((await ragApi.getRagHealth()).status).toBe('healthy')

    // 非流式兜底（上游降级）
    const fallbackEvents: unknown[] = []
    mocks.post.mockResolvedValueOnce({ data: {} })
    await ragApi.queryStream('kb-1', { query: 'q' }, (evt) => fallbackEvents.push(evt))
    expect(fallbackEvents).toHaveLength(1)

    // 真实 ReadableStream 分支
    const encoder = new TextEncoder()
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: token\ndata: {"delta":"你好"}\n\nevent: done\ndata: {}\n\n'))
        controller.close()
      },
    })
    const streamEvents: { event: string; data: string }[] = []
    mocks.post.mockResolvedValueOnce({ data: stream })
    await ragApi.queryStream('kb-1', { query: 'q' }, (evt) => streamEvents.push(evt))
    expect(streamEvents.some((evt) => evt.event === 'token')).toBe(true)
  })
})

describe('llmApi', () => {
  it('覆盖全部端点（含 SSE 流式与兜底）', async () => {
    mocks.get.mockResolvedValue(ok({ models: [{ id: 'gpt-4' }] }))
    expect((await llmApi.fetchModels()).models).toHaveLength(1)

    mocks.get.mockResolvedValue(ok({ id: 'gpt-4' }))
    await llmApi.fetchModelDetail('gpt-4')

    mocks.post.mockResolvedValue(ok({ choices: [] }))
    await llmApi.sendChat({ model: 'gpt-4', messages: [{ role: 'user', content: 'hi' }] })

    mocks.get.mockResolvedValue(ok({ status: 'healthy' }))
    await llmApi.getLlmHealth()

    mocks.get.mockResolvedValue(ok({ items: [], total: 0 }))
    await llmApi.listConversations({ skip: 0, limit: 10 })

    mocks.post.mockResolvedValue(ok({ id: 'c1' }))
    await llmApi.createConversation({ title: 't' })

    mocks.post.mockResolvedValue(ok({ id: 'c1', archived: true }))
    await llmApi.archiveConversation('c1', { archived: true })

    mocks.delete.mockResolvedValue(ok({ deleted: true }))
    await llmApi.deleteConversation('c1')

    mocks.get.mockResolvedValue(ok([]))
    await llmApi.listMessages('c1')

    const fallback: unknown[] = []
    mocks.post.mockResolvedValueOnce({ data: {} })
    await llmApi.sendChatStream({ model: 'gpt-4', messages: [] }, (evt) => fallback.push(evt))
    expect(fallback).toHaveLength(1)
  })
})

describe('parseSseStream', () => {
  it('解析 event/data 行并分发事件', async () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: chunk\ndata: {"delta":"a"}'))
        controller.enqueue(encoder.encode('\n\nevent: done\ndata: {}\n\n'))
        controller.close()
      },
    })
    const events: { event: string; data: string }[] = []
    await parseSseStream(stream, (evt) => events.push(evt))
    expect(events.some((evt) => evt.event === 'chunk' && evt.data === '{"delta":"a"}')).toBe(true)
    expect(events.some((evt) => evt.event === 'done')).toBe(true)
  })
})

describe('gatewayApi', () => {
  it('覆盖全部端点', async () => {
    mocks.get.mockResolvedValue(ok({ systems: [] }))
    await gatewayApi.listAllServices()

    mocks.post.mockResolvedValue(ok({ instance_id: 'i1' }))
    await gatewayApi.registerService({ system: 'openllm', host: 'h', port: 1, weight: 1 })

    mocks.delete.mockResolvedValue(ok({ deleted: 'i1' }))
    await gatewayApi.deregisterService('openllm', 'i1')

    mocks.get.mockResolvedValue(ok({ systems: [] }))
    await gatewayApi.health()

    mocks.get.mockResolvedValue(ok({ results: [] }))
    await gatewayApi.ping()

    mocks.post.mockResolvedValue(ok({ result: {}, errors: [] }))
    await gatewayApi.aggregate({ steps: [], mapping: {} })

    expect(mocks.get).toHaveBeenCalledWith('/services')
    expect(mocks.post).toHaveBeenCalledWith('/gateway/aggregate', expect.objectContaining({ steps: [] }))
  })
})
