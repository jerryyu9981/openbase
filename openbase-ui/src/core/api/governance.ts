/**
 * AI 能力治理 API（v1.9.0）：经 OpenBase 通用代理聚合 OpenLLM 原生接口。
 *
 * 路由：`/api/v1/proxy/openllm/api/v1/<domain>`（OpenBase 注入 OpenLLM API Key +
 * `openbase-llm-proxy` 身份头，下游按 TRUSTED_PROXY_SOURCES 白名单采信）。
 * 响应为 OpenLLM 原生结构（非 OpenBase 信封），故直接返回 `response.data`。
 */
import { http } from '@/core/api/http'

const OPENLLM = '/proxy/openllm/api/v1'

export interface LlmProvider {
  id: string
  provider_name: string
  provider_code: string
  provider_type: string
  api_base_url: string
  config: Record<string, unknown>
  status: string
  priority: number
  health_status: string
  last_health_check_at: string | null
  created_at: string
  updated_at: string
}

export interface ProviderPayload {
  provider_name: string
  provider_code: string
  provider_type: string
  api_base_url: string
  api_key?: string
  priority?: number
}

export const governanceApi = {
  /** 提供商列表 */
  async listProviders(): Promise<LlmProvider[]> {
    const { data } = await http.get<LlmProvider[]>(`${OPENLLM}/providers`)
    return data
  },

  /** 新增提供商 */
  async createProvider(payload: ProviderPayload): Promise<LlmProvider> {
    const { data } = await http.post<LlmProvider>(`${OPENLLM}/providers`, payload)
    return data
  },

  /** 更新提供商（状态切换复用此接口） */
  async updateProvider(
    providerId: string,
    payload: Partial<ProviderPayload> & { status?: string },
  ): Promise<LlmProvider> {
    const { data } = await http.put<LlmProvider>(`${OPENLLM}/providers/${providerId}`, payload)
    return data
  },

  /** 删除提供商 */
  async deleteProvider(providerId: string): Promise<void> {
    await http.delete(`${OPENLLM}/providers/${providerId}`)
  },

  /** 指定提供商的模型列表（用于展示接入模型数） */
  async listProviderModels(providerId: string): Promise<Array<{ id: string; model_name: string }>> {
    const { data } = await http.get<Array<{ id: string; model_name: string }>>(
      `${OPENLLM}/providers/${providerId}/models`,
    )
    return data
  },
}
