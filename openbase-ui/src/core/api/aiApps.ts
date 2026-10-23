/**
 * AI 应用 API（v1.12.0 OB-03）：应用列表与全局调用记录。
 * 后端为 OpenBase 自有模块 `/api/v1/ai-apps`（非代理）。
 */
import { http, type ApiSuccess } from '@/core/api/http'

export interface AiAppItem {
  id: string
  name: string
  description?: string | null
  status?: string
  current_version?: string | null
}

export interface AiAppCall {
  id: string
  app_id: string
  app_name?: string | null
  version?: string | null
  user_id?: number | null
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  latency_ms?: number
  status?: string
  error_code?: string | null
  created_at?: string | null
}

export interface AiAppCallPage {
  items: AiAppCall[]
  total: number
  page: number
  page_size: number
}

export const aiAppsApi = {
  async list(): Promise<AiAppItem[]> {
    const { data } = await http.get<ApiSuccess<{ items: AiAppItem[]; total: number }>>('/ai-apps')
    return data.data.items
  },

  /** 全局调用记录（跨应用，服务端分页） */
  async listCalls(params: {
    app_id?: string
    status?: string
    page?: number
    page_size?: number
  } = {}): Promise<AiAppCallPage> {
    const { data } = await http.get<ApiSuccess<AiAppCallPage>>('/ai-apps/calls', { params })
    return data.data
  },
}
