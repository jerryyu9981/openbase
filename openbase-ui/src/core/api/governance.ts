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

export interface LlmMonitoringOverview {
  total_requests: number
  total_tokens: number
  total_cost: number
  avg_latency_ms: number
  error_rate: number
  active_users: number
  time_range: string
}

export interface LlmMonitoringTimePoint {
  timestamp: string
  avg_latency_ms: number
  request_count: number
}

export interface LlmMonitoringDashboard {
  overview: LlmMonitoringOverview
  performance: {
    by_provider: Array<Record<string, unknown>>
    by_model: Array<Record<string, unknown>>
    time_series: LlmMonitoringTimePoint[]
  }
  cost: {
    by_provider: Array<Record<string, unknown>>
    by_model: Array<Record<string, unknown>>
    by_user: Array<Record<string, unknown>>
    trend: Array<{ timestamp: string; cost: number; request_count: number }>
  }
  error: {
    by_type: Array<Record<string, unknown>>
    by_provider: Array<Record<string, unknown>>
    active_alerts: Array<Record<string, unknown>>
  }
  resource: Record<string, unknown>
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
  /** 监控仪表盘（概览/性能/成本/错误/资源） */
  async dashboard(timeRange = '24h'): Promise<LlmMonitoringDashboard> {
    const { data } = await http.get<LlmMonitoringDashboard>(`${OPENLLM}/monitoring/dashboard`, {
      params: { time_range: timeRange },
    })
    return data
  },
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

// ---------------------------------------------------------------------------
// 治理与 RBAC（v1.9.5 R5）：roles / workspaces / virtual-keys / routing /
// circuit-breakers / tool-calls / prompt-templates / prompt-experiments / ab-tests
// 上游均支持双通道鉴权（JWT OR API Key）。
// ---------------------------------------------------------------------------

export interface LlmRolePermission {
  permission_id: string
  code: string
  name: string
  resource_type: string
  action: string
  constraints: Record<string, unknown>
}

export interface LlmRole {
  id: string
  code: string
  name: string
  description: string | null
  role_type: string
  level: number
  scope: string
  organization_id: string | null
  metadata_: Record<string, unknown>
  is_active: boolean
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface LlmRoleDetail extends LlmRole {
  permissions: LlmRolePermission[]
}

export interface LlmPermissionCatalogItem {
  id: string
  code: string
  name: string
  description: string | null
  resource_type: string
  action: string
  scope: string
  group_name: string | null
  is_active: boolean
}

export const rolesApi = {
  async list(params: { role_type?: string; is_active?: boolean; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<LlmRole[]>(`${OPENLLM}/roles`, { params })
    return data
  },
  async detail(roleId: string): Promise<LlmRoleDetail> {
    const { data } = await http.get<LlmRoleDetail>(`${OPENLLM}/roles/${encodeURIComponent(roleId)}`)
    return data
  },
  async create(payload: {
    code: string
    name: string
    description?: string
    role_type?: string
    level?: number
    scope?: string
  }): Promise<LlmRole> {
    const { data } = await http.post<LlmRole>(`${OPENLLM}/roles`, payload)
    return data
  },
  async update(roleId: string, payload: { name?: string; description?: string; level?: number; scope?: string; is_active?: boolean }) {
    const { data } = await http.put<LlmRole>(`${OPENLLM}/roles/${encodeURIComponent(roleId)}`, payload)
    return data
  },
  async remove(roleId: string): Promise<void> {
    await http.delete(`${OPENLLM}/roles/${encodeURIComponent(roleId)}`)
  },
  async catalog(): Promise<LlmPermissionCatalogItem[]> {
    const { data } = await http.get<LlmPermissionCatalogItem[]>(`${OPENLLM}/roles/permissions/catalog`)
    return data
  },
  async setPermissions(roleId: string, permissionIds: string[]): Promise<LlmRoleDetail> {
    const { data } = await http.put<LlmRoleDetail>(
      `${OPENLLM}/roles/${encodeURIComponent(roleId)}/permissions`,
      { permission_ids: permissionIds },
    )
    return data
  },
}

export interface LlmWorkspace {
  id: string
  name: string
  description: string | null
  owner_id: string
  settings: Record<string, unknown>
  quota: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export interface LlmWorkspaceMember {
  id: string
  workspace_id: string
  user_id: string
  role: string
  joined_at: string
  invited_by: string | null
  username: string | null
  email: string | null
}

export interface LlmWorkspaceResources {
  workspace_id: string
  member_count: number
  virtual_key_count: number
  total_requests: number
  total_tokens: number
}

export interface LlmVirtualKey {
  id: string
  workspace_id: string
  name: string
  key_prefix: string
  quota: Record<string, unknown>
  rate_limit: Record<string, unknown>
  model_whitelist: string[]
  permissions: Record<string, unknown>
  expires_at: string | null
  last_used_at: string | null
  usage_stats: Record<string, unknown>
  is_active: boolean
  created_at: string
}

export interface LlmVirtualKeyCreated extends LlmVirtualKey {
  key: string
}

export const workspacesApi = {
  async list(params: { status_filter?: string; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<LlmWorkspace[]>(`${OPENLLM}/workspaces`, { params })
    return data
  },
  async create(payload: { name: string; description?: string }): Promise<LlmWorkspace> {
    const { data } = await http.post<LlmWorkspace>(`${OPENLLM}/workspaces`, payload)
    return data
  },
  async remove(workspaceId: string): Promise<void> {
    await http.delete(`${OPENLLM}/workspaces/${encodeURIComponent(workspaceId)}`)
  },
  async members(workspaceId: string): Promise<LlmWorkspaceMember[]> {
    const { data } = await http.get<LlmWorkspaceMember[]>(
      `${OPENLLM}/workspaces/${encodeURIComponent(workspaceId)}/members`,
    )
    return data
  },
  async addMember(
    workspaceId: string,
    payload: { user_id?: string; username?: string; role: string },
  ): Promise<LlmWorkspaceMember> {
    const { data } = await http.post<LlmWorkspaceMember>(
      `${OPENLLM}/workspaces/${encodeURIComponent(workspaceId)}/members`,
      payload,
    )
    return data
  },
  async removeMember(workspaceId: string, userId: string): Promise<void> {
    await http.delete(
      `${OPENLLM}/workspaces/${encodeURIComponent(workspaceId)}/members/${encodeURIComponent(userId)}`,
    )
  },
  async resources(workspaceId: string): Promise<LlmWorkspaceResources> {
    const { data } = await http.get<LlmWorkspaceResources>(
      `${OPENLLM}/workspaces/${encodeURIComponent(workspaceId)}/resources`,
    )
    return data
  },
}

export const virtualKeysApi = {
  async list(params: { workspace_id?: string; active_only?: boolean } = {}): Promise<LlmVirtualKey[]> {
    const { data } = await http.get<LlmVirtualKey[]>(`${OPENLLM}/virtual-keys`, { params })
    return data
  },
  async create(workspaceId: string, payload: { name: string }): Promise<LlmVirtualKeyCreated> {
    const { data } = await http.post<LlmVirtualKeyCreated>(`${OPENLLM}/virtual-keys`, payload, {
      params: { workspace_id: workspaceId },
    })
    return data
  },
  async rotate(keyId: string): Promise<LlmVirtualKeyCreated> {
    const { data } = await http.post<LlmVirtualKeyCreated>(
      `${OPENLLM}/virtual-keys/${encodeURIComponent(keyId)}/rotate`,
      {},
    )
    return data
  },
}

export interface LlmSemanticRoute {
  id: string
  name: string
  description: string | null
  category: string
  model_id: string | null
  provider_id: string | null
  sample_queries: string[]
  enabled: boolean
  priority: number
  threshold: number
  metadata: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
}

export interface LlmRouteTestResponse {
  message: string
  result: {
    category: string | null
    route_id: string | null
    model_id: string | null
    provider_id: string | null
    similarity_score: number
    matched: boolean
    from_cache: boolean
    message: string | null
  }
  processing_time_ms: number
}

export interface LlmRouteCacheStats {
  total_requests: number
  cache_hits: number
  cache_misses: number
  hit_rate: number
  hit_rate_percent: number
  evictions: number
  current_size: number
  max_size: number
  ttl_seconds: number
  utilization_percent: number
  avg_lookup_time_ms: number
}

export const routingApi = {
  async list(params: { category?: string; enabled?: boolean; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<{ total: number; items: LlmSemanticRoute[] }>(
      `${OPENLLM}/routing/semantic`,
      { params },
    )
    return data
  },
  async create(payload: {
    name: string
    category: string
    description?: string
    sample_queries: string[]
    enabled?: boolean
    priority?: number
    threshold?: number
  }): Promise<LlmSemanticRoute> {
    const { data } = await http.post<LlmSemanticRoute>(`${OPENLLM}/routing/semantic`, payload)
    return data
  },
  async update(
    routeId: string,
    payload: Partial<{
      name: string
      category: string
      description: string
      sample_queries: string[]
      enabled: boolean
      priority: number
      threshold: number
    }>,
  ): Promise<LlmSemanticRoute> {
    const { data } = await http.put<LlmSemanticRoute>(
      `${OPENLLM}/routing/semantic/${encodeURIComponent(routeId)}`,
      payload,
    )
    return data
  },
  async remove(routeId: string): Promise<void> {
    await http.delete(`${OPENLLM}/routing/semantic/${encodeURIComponent(routeId)}`)
  },
  async test(payload: { message: string; threshold?: number; use_cache?: boolean }): Promise<LlmRouteTestResponse> {
    const { data } = await http.post<LlmRouteTestResponse>(`${OPENLLM}/routing/semantic/test`, payload)
    return data
  },
  async cacheStats(): Promise<LlmRouteCacheStats> {
    const { data } = await http.get<LlmRouteCacheStats>(`${OPENLLM}/routing/semantic/cache/stats`)
    return data
  },
  async clearCache(): Promise<void> {
    await http.post(`${OPENLLM}/routing/semantic/cache/clear`, {})
  },
}

export interface LlmCircuitBreaker {
  id: string
  provider: string
  model: string
  state: string
  failure_count: number
  success_count: number
  consecutive_successes: number
  consecutive_failures: number
  error_rate: number
  last_failure_time: string | null
  last_success_time: string | null
  last_state_change: string | null
  total_calls: number
  total_failures: number
  total_successes: number
  config: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
}

export const circuitBreakersApi = {
  async list(params: { provider?: string; model?: string; state?: string; page?: number; page_size?: number } = {}) {
    const { data } = await http.get<{ items: LlmCircuitBreaker[]; total: number; page: number; page_size: number }>(
      `${OPENLLM}/routing/circuit-breakers`,
      { params },
    )
    return data
  },
  async reset(breakerId: string): Promise<{ success: boolean; message: string; current_state: string }> {
    const { data } = await http.post<{ success: boolean; message: string; current_state: string }>(
      `${OPENLLM}/routing/circuit-breakers/${encodeURIComponent(breakerId)}/reset`,
      {},
    )
    return data
  },
}

export interface LlmToolCall {
  id: string
  tenant_id: string
  user_id: string
  conversation_id: string | null
  plugin_id: string
  tool_name: string
  input_params: Record<string, unknown>
  output_result: Record<string, unknown>
  status: string
  error_message: string | null
  token_count: number
  latency_ms: number
  created_at: string
  completed_at: string | null
}

export const toolCallsApi = {
  async list(params: { status?: string; tool_name?: string; plugin_id?: string; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<{ total: number; items: LlmToolCall[] }>(`${OPENLLM}/tool-calls`, { params })
    return data
  },
  async detail(toolCallId: string): Promise<LlmToolCall> {
    const { data } = await http.get<LlmToolCall>(`${OPENLLM}/tool-calls/${encodeURIComponent(toolCallId)}`)
    return data
  },
}

export interface LlmPromptTemplate {
  id: string
  name: string
  content: string
  variables: Array<{ name: string; description: string | null; required: boolean; default_value: string | null }>
  category: string
  description: string | null
  current_version: number
  is_system: boolean
  created_by: string | null
  workspace_id: string | null
  created_at: string
  updated_at: string
}

export interface LlmPromptVersion {
  id: string
  template_id: string
  version: number
  content: string
  changelog: string | null
  created_by: string | null
  created_at: string
}

export const promptTemplatesApi = {
  async list(params: { category?: string; keyword?: string; page?: number; page_size?: number; include_system?: boolean } = {}) {
    const { data } = await http.get<{
      items: LlmPromptTemplate[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`${OPENLLM}/prompt-templates`, { params })
    return data
  },
  async create(payload: {
    name: string
    content: string
    category: string
    description?: string
    is_system?: boolean
  }): Promise<LlmPromptTemplate> {
    const { data } = await http.post<LlmPromptTemplate>(`${OPENLLM}/prompt-templates`, payload)
    return data
  },
  async update(
    templateId: string,
    payload: { name?: string; content?: string; category?: string; description?: string; changelog?: string },
  ): Promise<LlmPromptTemplate> {
    const { data } = await http.put<LlmPromptTemplate>(
      `${OPENLLM}/prompt-templates/${encodeURIComponent(templateId)}`,
      payload,
    )
    return data
  },
  async remove(templateId: string): Promise<void> {
    await http.delete(`${OPENLLM}/prompt-templates/${encodeURIComponent(templateId)}`)
  },
  async versions(templateId: string): Promise<{ items: LlmPromptVersion[]; total: number }> {
    const { data } = await http.get<{ items: LlmPromptVersion[]; total: number }>(
      `${OPENLLM}/prompt-templates/${encodeURIComponent(templateId)}/versions`,
    )
    return data
  },
  async rollback(templateId: string, version: number): Promise<LlmPromptTemplate> {
    const { data } = await http.post<LlmPromptTemplate>(
      `${OPENLLM}/prompt-templates/${encodeURIComponent(templateId)}/rollback/${version}`,
      {},
    )
    return data
  },
  async importTemplate(payload: { content: string; format: string }): Promise<LlmPromptTemplate> {
    const { data } = await http.post<LlmPromptTemplate>(`${OPENLLM}/prompt-templates/import`, payload)
    return data
  },
}

export interface LlmVariant {
  name: string
  content: string
  variables?: Array<Record<string, unknown>>
}

export interface LlmPromptExperiment {
  id: string
  name: string
  description: string | null
  prompt_template_id: string | null
  variants: LlmVariant[]
  status: string
  metrics: Record<string, unknown>
  winner_variant: string | null
  created_by: string | null
  created_at: string | null
  updated_at: string | null
}

export interface LlmExperimentReport {
  experiment_id: string
  experiment_name: string
  variant_stats: Record<string, Record<string, unknown>>
  recommendation: string | null
}

export const promptExperimentsApi = {
  async list(params: { status_filter?: string; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<LlmPromptExperiment[]>(`${OPENLLM}/prompt-experiments`, { params })
    return data
  },
  async create(payload: { name: string; description?: string; prompt_template_id?: string; variants: LlmVariant[] }) {
    const { data } = await http.post<LlmPromptExperiment>(`${OPENLLM}/prompt-experiments`, payload)
    return data
  },
  async start(experimentId: string): Promise<LlmPromptExperiment> {
    const { data } = await http.post<LlmPromptExperiment>(
      `${OPENLLM}/prompt-experiments/${encodeURIComponent(experimentId)}/start`,
      {},
    )
    return data
  },
  async complete(experimentId: string): Promise<LlmPromptExperiment> {
    const { data } = await http.post<LlmPromptExperiment>(
      `${OPENLLM}/prompt-experiments/${encodeURIComponent(experimentId)}/complete`,
      {},
    )
    return data
  },
  async report(experimentId: string): Promise<LlmExperimentReport> {
    const { data } = await http.get<LlmExperimentReport>(
      `${OPENLLM}/prompt-experiments/${encodeURIComponent(experimentId)}/report`,
    )
    return data
  },
  async remove(experimentId: string): Promise<void> {
    await http.delete(`${OPENLLM}/prompt-experiments/${encodeURIComponent(experimentId)}`)
  },
}

export interface LlmAbTest {
  id: string
  name: string
  description: string | null
  model_a: string
  model_b: string
  traffic_split: Record<string, number>
  metrics: Record<string, unknown>
  status: string
  start_time: string
  end_time: string | null
  created_by: string | null
  organization_id: string | null
  target_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface LlmAbTestReport {
  test_id: string
  test_name: string
  model_a: string
  model_b: string
  model_a_stats: Record<string, unknown>
  model_b_stats: Record<string, unknown>
  significance: Record<string, unknown> | null
  recommendation: string | null
}

export const abTestsApi = {
  async list(params: { status_filter?: string; skip?: number; limit?: number } = {}) {
    const { data } = await http.get<LlmAbTest[]>(`${OPENLLM}/routing/ab-tests`, { params })
    return data
  },
  async create(payload: {
    name: string
    model_a: string
    model_b: string
    description?: string
    traffic_split?: Record<string, number>
  }): Promise<LlmAbTest> {
    const { data } = await http.post<LlmAbTest>(`${OPENLLM}/routing/ab-tests`, payload)
    return data
  },
  async pause(testId: string): Promise<LlmAbTest> {
    const { data } = await http.post<LlmAbTest>(`${OPENLLM}/routing/ab-tests/${encodeURIComponent(testId)}/pause`, {})
    return data
  },
  async resume(testId: string): Promise<LlmAbTest> {
    const { data } = await http.post<LlmAbTest>(`${OPENLLM}/routing/ab-tests/${encodeURIComponent(testId)}/resume`, {})
    return data
  },
  async complete(testId: string): Promise<LlmAbTest> {
    const { data } = await http.post<LlmAbTest>(
      `${OPENLLM}/routing/ab-tests/${encodeURIComponent(testId)}/complete`,
      {},
    )
    return data
  },
  async remove(testId: string): Promise<void> {
    await http.delete(`${OPENLLM}/routing/ab-tests/${encodeURIComponent(testId)}`)
  },
  async report(testId: string): Promise<LlmAbTestReport> {
    const { data } = await http.get<LlmAbTestReport>(
      `${OPENLLM}/routing/ab-tests/${encodeURIComponent(testId)}/report`,
    )
    return data
  },
}

// ---------------------------------------------------------------------------
// 本地资源与模型市场（v1.9.6 R6）：GPU 资源、下载任务、部署
// ---------------------------------------------------------------------------

export interface LlmGpuInfo {
  available: boolean
  running_models: Array<Record<string, unknown>>
}

export interface LlmGpuAllocation {
  gpu_id: number
  name: string
  total_memory_mb: number
  used_memory_mb: number
  free_memory_mb: number
  utilization: number
  allocated_models: Array<{ model_name: string; schedule_type: string }>
}

export interface LlmGpuAllocationStatus {
  available: boolean
  gpu_count: number
  gpus: LlmGpuAllocation[]
  message?: string | null
}

export const localModelsApi = {
  async gpuInfo(): Promise<LlmGpuInfo> {
    const { data } = await http.get<LlmGpuInfo>(`${OPENLLM}/local-models/gpu-info`)
    return data
  },
  async gpuAllocation(): Promise<LlmGpuAllocationStatus> {
    const { data } = await http.get<LlmGpuAllocationStatus>(
      `${OPENLLM}/local-models/gpu-allocation/status`,
    )
    return data
  },
  /** 已安装本地模型列表（v1.10.0 XR-LLM-02） */
  async list(): Promise<LlmLocalModelItem[]> {
    const { data } = await http.get<LlmLocalModelItem[]>(`${OPENLLM}/local-models`)
    return data
  },
  /** 可安装模型仓库（内置清单） */
  async available(params: { search?: string; category?: string } = {}): Promise<LlmLocalModelsAvailable> {
    const { data } = await http.get<LlmLocalModelsAvailable>(`${OPENLLM}/local-models/available`, {
      params,
    })
    return data
  },
  /** Ollama 服务与资源状态 */
  async serviceStatus(): Promise<LlmLocalModelStatus> {
    const { data } = await http.get<LlmLocalModelStatus>(`${OPENLLM}/local-models/status`)
    return data
  },
  async pull(modelName: string): Promise<void> {
    await http.post(`${OPENLLM}/local-models/pull`, { model_name: modelName, stream: false })
  },
  async remove(modelName: string): Promise<void> {
    await http.delete(`${OPENLLM}/local-models/${encodeURIComponent(modelName)}`)
  },
  async start(modelName: string): Promise<void> {
    await http.post(`${OPENLLM}/local-models/${encodeURIComponent(modelName)}/start`, {})
  },
  async stop(modelName: string): Promise<void> {
    await http.post(`${OPENLLM}/local-models/${encodeURIComponent(modelName)}/stop`, {})
  },
  async update(modelName: string): Promise<void> {
    await http.post(`${OPENLLM}/local-models/${encodeURIComponent(modelName)}/update`, {})
  },
}

export interface LlmLocalModelItem {
  name: string
  model: string
  modified_at: string | null
  size: number | null
  digest: string | null
  details?: Record<string, unknown> | null
}

export interface LlmAvailableModel {
  id: string
  name: string
  provider: string
  family: string
  size: number | null
  parameters: string | null
  quantization: string | null
  context_window: number | null
  capabilities: string[]
  description: string | null
  tags: string[]
}

export interface LlmLocalModelsAvailable {
  models: LlmAvailableModel[]
  categories: string[]
  total_count: number
}

export interface LlmLocalModelStatus {
  ollama_running: boolean
  gpu_available: boolean
  gpu_name: string | null
  gpu_memory: string | null
  system_memory: string | null
  disk_free: string | null
}

// ---------------------------------------------------------------------------
// 模型收藏与对比（v1.10.0 XR-LLM-02）：`/models/favorites`、`/models/compare`
// ---------------------------------------------------------------------------

export interface LlmFavoriteModelBrief {
  id: string
  model_id: string
  name: string
  source: string | null
  parameters: string | null
  license: string | null
  tags: string[]
  description?: string | null
}

export interface LlmFavorite {
  id: string
  model_id: string
  folder_name: string | null
  notes: string | null
  model: LlmFavoriteModelBrief | null
  created_at: string | null
}

export const favoritesApi = {
  async folders(): Promise<Array<{ name: string; count: number }>> {
    const { data } = await http.get<{ items: Array<{ name: string; count: number }> }>(
      `${OPENLLM}/models/favorite-folders`,
    )
    return data.items ?? []
  },
  async list(folder?: string): Promise<LlmFavorite[]> {
    const { data } = await http.get<LlmFavorite[]>(`${OPENLLM}/models/favorites`, {
      params: folder ? { folder } : {},
    })
    return data
  },
  async add(modelId: string, payload: { folder_name?: string; notes?: string } = {}): Promise<void> {
    await http.post(`${OPENLLM}/models/${encodeURIComponent(modelId)}/favorite`, payload)
  },
  async remove(modelId: string): Promise<void> {
    await http.delete(`${OPENLLM}/models/${encodeURIComponent(modelId)}/favorite`)
  },
}

export interface LlmModelCompareResult {
  models: Array<Record<string, unknown>>
  comparison: Record<string, unknown>
}

export const modelCompareApi = {
  async compare(modelIds: string[]): Promise<LlmModelCompareResult> {
    const { data } = await http.get<LlmModelCompareResult>(`${OPENLLM}/models/compare`, {
      params: { model_ids: modelIds },
    })
    return data
  },
}

export interface LlmDownloadTask {
  id: string
  model_id: string
  model_name?: string | null
  status: string
  total_size: number | null
  downloaded_size: number | null
  progress: number
  download_speed: number | null
  error_message: string | null
  retry_count: number
  local_path: string | null
  created_at: string | null
  updated_at: string | null
}

export interface LlmMarketModel {
  id: string
  model_id: string
  name: string
  source: string | null
  parameters: string | null
  license: string | null
  download_status: string | null
  deploy_status: string | null
  version: string | null
  tags: string[]
}

export interface LlmDeployStatus {
  deployment_id: string | null
  status: string
  framework: string | null
  port: number | null
  process_id: number | null
  health_check_url: string | null
  is_healthy: boolean
  resource_usage: Record<string, unknown>
  start_time: string | null
  uptime_seconds: number | null
}

export interface LlmDeployLog {
  logs: Array<Record<string, unknown>>
}

export const openModelsApi = {
  async list(params: { page?: number; page_size?: number; source?: string } = {}) {
    const { data } = await http.get<{
      items: LlmMarketModel[]
      total: number
      page: number
      page_size: number
    }>(`${OPENLLM}/open-models`, { params })
    return data
  },
  async downloads(params: { status?: string; page?: number; page_size?: number } = {}) {
    const { data } = await http.get<{
      items: LlmDownloadTask[]
      total: number
      page: number
      page_size: number
    }>(`${OPENLLM}/open-models/downloads`, { params })
    return data
  },
  async startDownload(modelId: string, payload: { version?: string; resume?: boolean } = {}): Promise<void> {
    await http.post(`${OPENLLM}/open-models/${encodeURIComponent(modelId)}/download`, {
      version: payload.version ?? 'main',
      resume: payload.resume ?? true,
    })
  },
  async pauseDownload(modelId: string): Promise<void> {
    await http.post(`${OPENLLM}/open-models/${encodeURIComponent(modelId)}/pause-download`, {})
  },
  async resumeDownload(modelId: string): Promise<void> {
    await http.post(`${OPENLLM}/open-models/${encodeURIComponent(modelId)}/resume-download`, {})
  },
  async cancelDownload(modelId: string): Promise<void> {
    await http.post(`${OPENLLM}/open-models/${encodeURIComponent(modelId)}/cancel-download`, {})
  },
  async deploy(
    modelId: string,
    payload: {
      framework?: string
      quantization?: string | null
      gpu_devices?: number[] | null
      port?: number
      max_context_length?: number
    } = {},
  ): Promise<void> {
    await http.post(`${OPENLLM}/open-models/${encodeURIComponent(modelId)}/deploy`, {
      framework: payload.framework ?? 'auto',
      quantization: payload.quantization ?? null,
      gpu_devices: payload.gpu_devices ?? null,
      port: payload.port ?? 8000,
      max_context_length: payload.max_context_length ?? 4096,
    })
  },
  async deployStatus(modelId: string): Promise<LlmDeployStatus> {
    const { data } = await http.get<LlmDeployStatus>(
      `${OPENLLM}/open-models/${encodeURIComponent(modelId)}/deploy-status`,
    )
    return data
  },
  async stop(modelId: string): Promise<void> {
    await http.post(`${OPENLLM}/open-models/${encodeURIComponent(modelId)}/stop`, {})
  },
  async logs(modelId: string): Promise<LlmDeployLog> {
    const { data } = await http.get<LlmDeployLog>(
      `${OPENLLM}/open-models/${encodeURIComponent(modelId)}/logs`,
    )
    return data
  },
}
