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

// ---------------------------------------------------------------------------
// 观察域（v1.9.4 R4）：成本 / 告警 / 链路 / 预算 / 用量 / 计费
// 上游统一为 OpenLLM 双通道鉴权（JWT OR API Key），经 OpenBase 通用代理聚合。
// ---------------------------------------------------------------------------

export interface LlmCostDimensionItem {
  value: string
  total_cost: number
  request_count: number
  avg_cost_per_request: number
}

export interface LlmCostTrendItem {
  timestamp: string
  cost: number
  request_count: number
}

export interface LlmCostAnalysis {
  time_range: string
  start_time: string
  end_time: string
  dimensions: Record<string, LlmCostDimensionItem[]>
  trend: LlmCostTrendItem[]
}

export interface LlmOptimizationSuggestion {
  type: string
  severity: string
  title: string
  description: string
  recommendation: string
  potential_savings: string | null
}

export const monitoringApi = {
  /** 成本分析（维度：provider/model/user/api_key/workspace） */
  async costs(params: { dimension: string[]; time_range?: string }): Promise<LlmCostAnalysis> {
    const { data } = await http.get<LlmCostAnalysis>(`${OPENLLM}/monitoring/costs`, { params })
    return data
  },
  /** 成本优化建议（最近 7 天） */
  async optimizationSuggestions(): Promise<LlmOptimizationSuggestion[]> {
    const { data } = await http.get<{ suggestions: LlmOptimizationSuggestion[]; total: number; generated_at: string }>(
      `${OPENLLM}/monitoring/costs/optimization-suggestions`,
    )
    return data.suggestions
  },
}

export interface LlmAlertRule {
  id: string
  name: string
  description: string | null
  alert_type: string
  condition: Record<string, unknown>
  severity: string
  channels: Array<Record<string, unknown>>
  provider: string | null
  model: string | null
  enabled: boolean
  cooldown_seconds: number
  last_evaluated_at: string | null
  last_fired_at: string | null
  created_at: string | null
}

export interface LlmAlertRulePayload {
  name: string
  description?: string
  alert_type: string
  condition: Record<string, unknown>
  severity: string
  channels?: Array<Record<string, unknown>>
  provider?: string
  model?: string
  enabled?: boolean
  cooldown_seconds?: number
}

export interface LlmAlertItem {
  id: string
  rule_id: string | null
  alert_type: string
  severity: string
  status: string
  title: string
  message: string
  provider: string | null
  model: string | null
  threshold_value: number | null
  actual_value: number | null
  fired_at: string | null
  resolved_at: string | null
  acknowledged_at: string | null
  created_at: string | null
}

export const alertsApi = {
  async listRules(params: { alert_type?: string; enabled?: boolean; page?: number; page_size?: number } = {}) {
    const { data } = await http.get<{ rules: LlmAlertRule[]; total: number; page: number; page_size: number }>(
      `${OPENLLM}/alerts/rules`,
      { params },
    )
    return data
  },
  async createRule(payload: LlmAlertRulePayload): Promise<LlmAlertRule> {
    const { data } = await http.post<LlmAlertRule>(`${OPENLLM}/alerts/rules`, payload)
    return data
  },
  async updateRule(ruleId: string, payload: Partial<LlmAlertRulePayload>): Promise<LlmAlertRule> {
    const { data } = await http.put<LlmAlertRule>(
      `${OPENLLM}/alerts/rules/${encodeURIComponent(ruleId)}`,
      payload,
    )
    return data
  },
  async removeRule(ruleId: string): Promise<void> {
    await http.delete(`${OPENLLM}/alerts/rules/${encodeURIComponent(ruleId)}`)
  },
  async list(params: { status?: string; severity?: string; alert_type?: string; page?: number; page_size?: number } = {}) {
    const { data } = await http.get<{ alerts: LlmAlertItem[]; total: number; page: number; page_size: number }>(
      `${OPENLLM}/alerts`,
      { params },
    )
    return data
  },
  async resolve(alertId: string, resolutionNote?: string): Promise<LlmAlertItem> {
    const { data } = await http.post<LlmAlertItem>(
      `${OPENLLM}/alerts/${encodeURIComponent(alertId)}/resolve`,
      { resolution_note: resolutionNote ?? null },
    )
    return data
  },
  async acknowledge(alertId: string): Promise<LlmAlertItem> {
    const { data } = await http.post<LlmAlertItem>(
      `${OPENLLM}/alerts/${encodeURIComponent(alertId)}/acknowledge`,
      {},
    )
    return data
  },
}

export interface LlmBudget {
  id: string
  name: string
  description: string | null
  scope: string
  scope_id: string | null
  period: string
  limit_usd: number
  current_usage_usd: number
  usage_percentage: number
  enabled: boolean
  is_exceeded: boolean
  created_at: string | null
}

export interface LlmBudgetStatus {
  budget_id: string
  name: string
  scope: string
  period: string
  limit_usd: number
  current_usage_usd: number
  usage_percentage: number
  is_exceeded: boolean
  remaining_usd: number
  days_remaining: number
  projected_usage_usd: number
}

export interface LlmBudgetPayload {
  name: string
  description?: string
  scope: string
  scope_id?: string
  period: string
  limit_usd: number
  alert_thresholds?: Array<{ type: string; value: number }>
}

export const budgetsApi = {
  async list(params: { scope?: string; enabled?: boolean; page?: number; page_size?: number } = {}) {
    const { data } = await http.get<{ budgets: LlmBudget[]; total: number; page: number; page_size: number }>(
      `${OPENLLM}/budgets`,
      { params },
    )
    return data
  },
  async create(payload: LlmBudgetPayload): Promise<LlmBudget> {
    const { data } = await http.post<LlmBudget>(`${OPENLLM}/budgets`, payload)
    return data
  },
  async status(budgetId: string): Promise<LlmBudgetStatus> {
    const { data } = await http.get<LlmBudgetStatus>(
      `${OPENLLM}/budgets/${encodeURIComponent(budgetId)}/status`,
    )
    return data
  },
}

export interface LlmTrace {
  id: string
  trace_id: string
  user_id: string | null
  model: string | null
  provider: string | null
  request_type: string | null
  start_time: string | null
  end_time: string | null
  latency_ms: number | null
  status: string
  span_count: number
  tokens_total: number
  cost: number
  created_at: string | null
}

export interface LlmTraceSpan {
  span_id: string
  name: string
  kind: string
  parent_span_id: string | null
  start_time: string | null
  end_time: string | null
  duration_ms: number | null
  status: string
  status_message: string | null
  attributes: Record<string, unknown>
  events: Array<Record<string, unknown>>
}

export interface LlmTraceDetail extends LlmTrace {
  tenant_id: string | null
  error_code: string | null
  error_message: string | null
  spans: LlmTraceSpan[]
}

export interface LlmTraceStatistics {
  time_range: string
  total_count: number
  success_count: number
  error_count: number
  error_rate: number
  avg_latency_ms: number
  total_tokens: number
  total_cost: number
}

export const tracesApi = {
  async list(params: {
    status?: string
    model?: string
    provider?: string
    has_error?: boolean
    page?: number
    page_size?: number
  } = {}) {
    const { data } = await http.get<{ traces: LlmTrace[]; total: number; page: number; page_size: number }>(
      `${OPENLLM}/monitoring/traces`,
      { params },
    )
    return data
  },
  async statistics(timeRange = '24h'): Promise<LlmTraceStatistics> {
    const { data } = await http.get<LlmTraceStatistics>(`${OPENLLM}/monitoring/traces/statistics`, {
      params: { time_range: timeRange },
    })
    return data
  },
  async detail(traceId: string): Promise<LlmTraceDetail> {
    const { data } = await http.get<LlmTraceDetail>(
      `${OPENLLM}/monitoring/traces/${encodeURIComponent(traceId)}`,
    )
    return data
  },
}

export interface LlmUsageSummary {
  tenant_id: string | null
  period: string
  group_by: string
  start_date: string
  end_date: string
  total_requests: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_tokens: number
  total_cost: number
  avg_latency_ms: number
  status_breakdown: Record<string, number>
  grouped_data: Array<Record<string, unknown>>
}

export interface LlmUsageTrendPoint {
  date: string
  requests: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost: number
  avg_latency?: number
}

export interface LlmUsageTrends {
  tenant_id: string | null
  dimension: string
  period: string
  series: LlmUsageTrendPoint[]
  summary: Record<string, unknown>
}

export interface LlmUsageRecord {
  id: string
  organization_id: string
  user_id: string | null
  api_key_id: string | null
  provider_id: string
  model_id: string
  request_id: string
  request_type: string
  tokens_input: number
  tokens_output: number
  tokens_total: number
  cost: number
  currency: string
  latency_ms: number | null
  status: string
  error_code: string | null
  error_message: string | null
  created_at: string | null
}

export const usageApi = {
  async summary(params: { period?: string; group_by?: string; start_date?: string; end_date?: string } = {}) {
    const { data } = await http.get<LlmUsageSummary>(`${OPENLLM}/usage/summary`, { params })
    return data
  },
  async trends(params: { dimension?: string; period?: string; start_date?: string; end_date?: string } = {}) {
    const { data } = await http.get<LlmUsageTrends>(`${OPENLLM}/usage/trends`, { params })
    return data
  },
  async detail(params: { start_date?: string; end_date?: string; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<{
      tenant_id: string | null
      start_date: string | null
      end_date: string | null
      total: number
      skip: number
      limit: number
      records: LlmUsageRecord[]
    }>(`${OPENLLM}/usage/detail`, { params })
    return data
  },
}

export interface LlmQuota {
  id: string
  organization_id: string
  team_id: string | null
  quota_type: string
  quota_limit: number
  used_amount: number
  usage_percent: number
  period: string
  alert_threshold: number
  is_exceeded: boolean
  period_start: string
  period_end: string
  created_at: string
}

export interface LlmBill {
  id: string
  organization_id: string
  team_id: string | null
  period_start: string
  period_end: string
  total_requests: number
  total_tokens_input: number
  total_tokens_output: number
  total_cost: number
  currency: string
  details: Record<string, unknown>
  status: string
  notes: string | null
  created_at: string
}

export interface LlmBillingUsageStatistics {
  total_requests: number
  total_tokens_input: number
  total_tokens_output: number
  total_cost: number
  average_latency_ms: number
  status_breakdown: Record<string, number>
}

export const billingApi = {
  async usageStatistics(params: { start_date?: string; end_date?: string } = {}) {
    const { data } = await http.get<LlmBillingUsageStatistics>(`${OPENLLM}/billing/usage/statistics`, { params })
    return data
  },
  async quotas(): Promise<LlmQuota[]> {
    const { data } = await http.get<LlmQuota[]>(`${OPENLLM}/billing/quotas`)
    return data
  },
  async bills(): Promise<LlmBill[]> {
    const { data } = await http.get<LlmBill[]>(`${OPENLLM}/billing/bills`)
    return data
  },
}
