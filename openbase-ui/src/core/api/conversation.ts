/**
 * 会话（上下文）补充 API（批次 5）
 *
 * 复用 OpenBase `/api/v1/llm-proxy/conversations/*`：`llm.ts` 已封装列表/新建/
 * 归档/删除/消息列表，本文件仅补齐「会话详情」与「追加消息」两个生命周期端点。
 *
 * 单独成文件而非并入 `llm.ts`：后者在工作区含批次 4 遗留未提交改动
 * （《批次 5 规格》§1.3 提交边界），避免本批次改动与其混合入库。
 */
import { http } from '@/core/api/http'

/** 会话消息（对齐 OpenLLM MessageListResponse：id/role/content/model_name/token_count/created_at） */
export interface ConversationMessage {
  id?: string
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  model_name?: string
  token_count?: number
  created_at?: string
}

/** 追加消息请求体（对齐 OpenLLM MessageCreate） */
export interface ConversationMessageCreate {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  model_name?: string
}

export const conversationApi = {
  /** 会话详情（GET /api/v1/llm-proxy/conversations/{id}） */
  async getConversation(conversationId: string): Promise<Record<string, unknown>> {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>(
      `/llm-proxy/conversations/${encodeURIComponent(conversationId)}`,
    )
    return data.data
  },

  /** 追加会话消息（POST /api/v1/llm-proxy/conversations/{id}/messages） */
  async appendMessage(
    conversationId: string,
    payload: ConversationMessageCreate,
  ): Promise<ConversationMessage> {
    const { data } = await http.post<{ code: number; data: ConversationMessage }>(
      `/llm-proxy/conversations/${encodeURIComponent(conversationId)}/messages`,
      payload,
    )
    return data.data
  },
}
