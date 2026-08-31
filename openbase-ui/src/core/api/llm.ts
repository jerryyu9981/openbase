/**
 * OpenLLM llm-proxy API 封装（v1.4.3 R-379）
 * 全部走 OpenBase /api/v1/llm-proxy/*，前端零密钥接触（OpenLLM 密钥由 OpenBase 持有）。
 * 对齐《OpenBase-API接口设计文档-v1.4.3》§1（12 端点）
 */
import { http } from '@/core/api/http'

export interface LlmModel {
  id: string
  object?: string
  created?: number
  owned_by?: string
  name?: string
  provider?: string
  type?: string
  capabilities?: string[]
  status?: string
  [key: string]: unknown
}

export interface Conversation {
  id: string
  title?: string
  model?: string
  messages?: number
  started_at?: string
  tokens?: number
  archived?: boolean
  [key: string]: unknown
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatChunk {
  model?: string
  choices?: Array<{ delta?: { content?: string }; message?: { content?: string } }>
  usage?: { total_tokens?: number }
  [key: string]: unknown
}

export interface SseEvent {
  event: string
  data: string
}

/** 解析 SSE ReadableStream，按事件分发（event: routing/chunk/done/error/usage） */
export async function parseSseStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (evt: SseEvent) => void,
): Promise<void> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventName = 'message'
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        const trimmed = line.replace(/\r$/, '')
        if (trimmed === '') {
          // 空行 = 事件结束
          if (eventName || buffer === '') {
            onEvent({ event: eventName, data: '' })
          }
          eventName = 'message'
          continue
        }
        if (trimmed.startsWith('event:')) {
          eventName = trimmed.slice(6).trim()
        } else if (trimmed.startsWith('data:')) {
          onEvent({ event: eventName, data: trimmed.slice(5).trim() })
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export const llmApi = {
  /** 模型列表（GET /api/v1/llm-proxy/models） */
  async fetchModels(): Promise<{ models: LlmModel[] }> {
    const { data } = await http.get<{ code: number; data: { models: LlmModel[] } }>('/llm-proxy/models')
    return data.data
  },

  /** 模型详情（GET /api/v1/llm-proxy/models/{id}） */
  async fetchModelDetail(modelId: string): Promise<LlmModel> {
    const { data } = await http.get<{ code: number; data: LlmModel }>(`/llm-proxy/models/${encodeURIComponent(modelId)}`)
    return data.data
  },

  /** 对话（非流式，POST /api/v1/llm-proxy/chat） */
  async sendChat(payload: { model: string; messages: ChatMessage[] }): Promise<{ choices: ChatChunk['choices'] }> {
    const { data } = await http.post<{ code: number; data: { choices: ChatChunk['choices'] } }>('/llm-proxy/chat', { ...payload, stream: false })
    return data.data
  },

  /**
   * 对话流式（POST /api/v1/llm-proxy/chat/stream）
   * SSE 逐事件透传：event: routing → chunk×N → done
   * adapter: 'fetch'：浏览器端 XHR 不支持 responseType 'stream'，
   * fetch adapter 返回真实 ReadableStream 供 SSE 逐事件消费（TD-新增-011 偿还，v1.4.5）
   */
  async sendChatStream(
    payload: { model: string; messages: ChatMessage[] },
    onEvent: (evt: SseEvent) => void,
  ): Promise<void> {
    const resp = await http.post<ReadableStream<Uint8Array>>(
      '/llm-proxy/chat/stream',
      { ...payload, stream: true },
      { responseType: 'stream', timeout: 120000, adapter: 'fetch' },
    )
    if (resp.data && typeof resp.data.getReader === 'function') {
      await parseSseStream(resp.data, onEvent)
      return
    }
    // 非流式兜底（上游降级非流式时）
    onEvent({ event: 'done', data: JSON.stringify({}) })
  },

  /** 上游健康（GET /api/v1/llm-proxy/health） */
  async getLlmHealth(): Promise<{ status: string; version?: string }> {
    const { data } = await http.get<{ code: number; data: { status: string; version?: string } }>('/llm-proxy/health')
    return data.data
  },

  /** 会话列表（GET /api/v1/llm-proxy/conversations） */
  async listConversations(params?: { status?: string; skip?: number; limit?: number }): Promise<{ items: Conversation[]; total?: number }> {
    const { data } = await http.get<{ code: number; data: { items: Conversation[]; total?: number } }>('/llm-proxy/conversations', { params })
    return data.data
  },

  /** 新建会话（POST /api/v1/llm-proxy/conversations） */
  async createConversation(payload: { title?: string; model?: string; system_prompt?: string }): Promise<Conversation> {
    const { data } = await http.post<{ code: number; data: Conversation }>('/llm-proxy/conversations', payload)
    return data.data
  },

  /** 归档/取消归档（POST /api/v1/llm-proxy/conversations/{id}/archive） */
  async archiveConversation(conversationId: string, payload?: Record<string, unknown>): Promise<Conversation> {
    const { data } = await http.post<{ code: number; data: Conversation }>(
      `/llm-proxy/conversations/${encodeURIComponent(conversationId)}/archive`,
      payload || {},
    )
    return data.data
  },

  /** 删除会话（DELETE /api/v1/llm-proxy/conversations/{id}） */
  async deleteConversation(conversationId: string): Promise<unknown> {
    const { data } = await http.delete<{ code: number; data: unknown }>(`/llm-proxy/conversations/${encodeURIComponent(conversationId)}`)
    return data.data
  },

  /** 会话消息列表（GET /api/v1/llm-proxy/conversations/{id}/messages） */
  async listMessages(conversationId: string): Promise<ChatMessage[]> {
    const { data } = await http.get<{ code: number; data: ChatMessage[] }>(`/llm-proxy/conversations/${encodeURIComponent(conversationId)}/messages`)
    return data.data
  },
}
