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

// ---------------------------------------------------------------------------
// EdgeRouter（v1.9.1）：OpenLLM 边缘路由的组织/配额/适配器/审计
// ---------------------------------------------------------------------------

export interface EdgeAdapter {
  name: string
  status: string
  isolation_type: string
  registered_at: string | null
}

export interface EdgeOrganization {
  id: string
  name: string
  display_name: string
  description: string | null
  status: string
  created_at: string | null
}

export interface EdgeQuota {
  id: string
  org_id: string
  resource_type: string
  limit_value: number
  current_usage: number
  warning_threshold: number
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface EdgeAuditLog {
  id: string
  org_id: string
  user_id: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  request_path: string
  request_method: string
  response_status: number
  ip_address: string | null
  timestamp: string | null
}

export interface EdgeAuditPage {
  items: EdgeAuditLog[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface EdgeStatus {
  status: string
  version: string
  uptime_seconds: number
  registered_adapters: string[]
  adapter_count: number
  router_mode: string
  features: Record<string, boolean>
}

export interface EdgeHealth {
  status: string
  components: Record<string, string>
  timestamp: string
}

export const edgeApi = {
  async status(): Promise<EdgeStatus> {
    const { data } = await http.get<EdgeStatus>(`${OPENLLM}/edge/status`)
    return data
  },
  async health(): Promise<EdgeHealth> {
    const { data } = await http.get<EdgeHealth>(`${OPENLLM}/edge/health`)
    return data
  },
  async listAdapters(): Promise<EdgeAdapter[]> {
    const { data } = await http.get<{ adapters: EdgeAdapter[]; count: number }>(`${OPENLLM}/edge/adapters`)
    return data.adapters
  },
  async listOrganizations(): Promise<EdgeOrganization[]> {
    const { data } = await http.get<EdgeOrganization[]>(`${OPENLLM}/edge/organizations`)
    return data
  },
  async createOrganization(payload: {
    name: string
    display_name?: string
    description?: string
  }): Promise<EdgeOrganization> {
    const { data } = await http.post<EdgeOrganization>(`${OPENLLM}/edge/organizations`, payload)
    return data
  },
  async updateOrganization(
    orgId: string,
    payload: { display_name?: string; description?: string },
  ): Promise<EdgeOrganization> {
    const { data } = await http.put<EdgeOrganization>(
      `${OPENLLM}/edge/organizations/${encodeURIComponent(orgId)}`,
      payload,
    )
    return data
  },
  async listQuotas(orgId: string): Promise<EdgeQuota[]> {
    const { data } = await http.get<{ org_id: string; quotas: EdgeQuota[]; total: number }>(
      `${OPENLLM}/edge/quotas/${encodeURIComponent(orgId)}`,
    )
    return data.quotas
  },
  async updateQuota(
    orgId: string,
    payload: { resource_type: string; limit_value?: number; warning_threshold?: number; status?: string },
  ): Promise<void> {
    await http.put(`${OPENLLM}/edge/quotas/${encodeURIComponent(orgId)}`, payload)
  },
  async listAuditLogs(params: { page?: number; page_size?: number } = {}): Promise<EdgeAuditPage> {
    const { data } = await http.get<EdgeAuditPage>(`${OPENLLM}/edge/audit/logs`, { params })
    return data
  },
}

// ---------------------------------------------------------------------------
// 插件与模型分类（v1.9.3 R3）：OpenLLM 双通道鉴权（JWT OR API Key）
// ---------------------------------------------------------------------------

export interface LlmPlugin {
  id: string
  name: string
  display_name: string
  description: string | null
  version: string
  author: string | null
  plugin_type: string
  status: string
  config_schema: Record<string, unknown>
  config: Record<string, unknown>
  permissions: unknown[]
  metadata_: Record<string, unknown>
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface LlmPluginPage {
  total: number
  items: LlmPlugin[]
}

export interface LlmAvailableTool {
  plugin_id: string
  plugin_name: string
  tool_name: string
  description: string | null
  parameters: Record<string, unknown>
}

export interface LlmPluginHealth {
  plugin_id: string
  name: string
  is_healthy: boolean
  status: string
  total_calls: number
  success_calls: number
  failed_calls: number
  avg_latency_ms: number
  tools_count: number
  error: string | null
}

export interface ModelCategory {
  id: string
  name: string
  code: string
  description: string | null
  icon: string | null
  sort_order: number | null
  parent_id: string | null
  category_type: string | null
  model_count: number | null
  children: ModelCategory[]
}

export interface OpenSourceModel {
  id: string
  model_id: string
  name: string
  source: string
  architecture: string | null
  parameters: string | null
  license: string | null
  download_count: number | null
  rating: number | null
  tags: string[]
  categories: string[]
  download_status: string | null
  deploy_status: string | null
}

export interface CategoryModelPage {
  category?: ModelCategory
  items: OpenSourceModel[]
  total: number
}

export const pluginsApi = {
  async list(params: { plugin_type?: string; status?: string; is_system?: boolean; skip?: number; limit?: number } = {}): Promise<LlmPluginPage> {
    const { data } = await http.get<LlmPluginPage>(`${OPENLLM}/plugins`, { params })
    return data
  },
  async listTools(): Promise<LlmAvailableTool[]> {
    const { data } = await http.get<{ total: number; items: LlmAvailableTool[] }>(`${OPENLLM}/plugins/tools`)
    return data.items
  },
  async setEnabled(pluginId: string, enabled: boolean): Promise<LlmPlugin> {
    const action = enabled ? 'enable' : 'disable'
    const { data } = await http.post<LlmPlugin>(`${OPENLLM}/plugins/${pluginId}/${action}`)
    return data
  },
  async health(pluginId: string): Promise<LlmPluginHealth> {
    const { data } = await http.get<LlmPluginHealth>(`${OPENLLM}/plugins/${pluginId}/health`)
    return data
  },
  async register(payload: { name: string; version?: string; description?: string; entry_point?: string }): Promise<LlmPlugin> {
    const { data } = await http.post<LlmPlugin>(`${OPENLLM}/plugins/register`, payload)
    return data
  },
  async remove(pluginId: string): Promise<void> {
    await http.delete(`${OPENLLM}/plugins/${pluginId}`)
  },
}

export const modelCategoriesApi = {
  async tree(): Promise<ModelCategory[]> {
    const { data } = await http.get<{ items: ModelCategory[] }>(`${OPENLLM}/model-categories/tree`)
    return data.items
  },
  async list(params: { type?: string } = {}): Promise<ModelCategory[]> {
    const { data } = await http.get<ModelCategory[]>(`${OPENLLM}/model-categories`, { params })
    return data
  },
  async models(categoryId: string, params: { page?: number; page_size?: number } = {}): Promise<CategoryModelPage> {
    const { data } = await http.get<CategoryModelPage>(
      `${OPENLLM}/model-categories/${encodeURIComponent(categoryId)}/models`,
      { params },
    )
    return data
  },
}
