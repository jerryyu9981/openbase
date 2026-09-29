/**
 * 会话标识提交（v1.4.8 D2 / R-396）
 *
 * 契约（《OpenBase-会话标识提交派单-openbase-ui-v1.0.0》§2）：
 *   - 请求体字段 `session_id`，**可选**；缺省时后端按用户记账；
 *   - 同一会话多轮复用**同一标识**；新建会话生成**新标识**；
 *   - 标识**不含凭据类信息**（随机标识即可）；
 *   - 覆盖 `sendChat` 与 `sendChatStream` 两条调用路径；显式传入时以传入值为准。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
}))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get, post: mocks.post, put: vi.fn(), delete: vi.fn() },
  tokenStore: { set: vi.fn(), clear: vi.fn(), access: '', refresh: '' },
}))

import { llmApi } from '@/core/api/llm'

async function loadSession() {
  try {
    return await import('@/core/session')
  } catch {
    throw new Error('@/core/session 缺失：前端会话标识模块未实现（D2 / R-396）')
  }
}

describe('前端会话标识（D2 / R-396）', () => {
  beforeEach(() => {
    mocks.post.mockReset()
    mocks.get.mockReset()
  })

  it('生成非空标识且同一会话内稳定复用', async () => {
    const session = await loadSession()
    const first = session.getSessionId()
    expect(typeof first).toBe('string')
    expect(first.length).toBeGreaterThan(7)
    expect(session.getSessionId()).toBe(first)
  })

  it('新建会话（重置）后生成新标识', async () => {
    const session = await loadSession()
    const first = session.getSessionId()
    const second = session.resetSessionId()
    expect(second).not.toBe(first)
    expect(session.getSessionId()).toBe(second)
  })

  it('标识不含凭据类信息', async () => {
    const session = await loadSession()
    expect(session.getSessionId()).not.toMatch(/bearer|token|secret|password|sk-/i)
  })

  it('sendChat 请求体携带 session_id', async () => {
    const session = await loadSession()
    mocks.post.mockResolvedValueOnce({ data: { code: 0, data: { choices: [] } } })
    await llmApi.sendChat({ model: 'auto', messages: [{ role: 'user', content: 'hi' }] })
    const [, body] = mocks.post.mock.calls[0]
    expect(body.session_id).toBe(session.getSessionId())
    expect(body.stream).toBe(false)
  })

  it('sendChatStream 请求体携带 session_id', async () => {
    const session = await loadSession()
    mocks.post.mockResolvedValueOnce({ data: {} })
    await llmApi.sendChatStream(
      { model: 'auto', messages: [{ role: 'user', content: 'hi' }] },
      () => {},
    )
    const [, body] = mocks.post.mock.calls[0]
    expect(body.session_id).toBe(session.getSessionId())
    expect(body.stream).toBe(true)
  })

  it('显式传入 session_id 时以传入值为准', async () => {
    mocks.post.mockResolvedValueOnce({ data: { code: 0, data: { choices: [] } } })
    await llmApi.sendChat({
      model: 'auto',
      messages: [],
      session_id: 'sess-explicit',
    })
    const [, body] = mocks.post.mock.calls[0]
    expect(body.session_id).toBe('sess-explicit')
  })
})
