/**
 * v1.9.4 R4：观察域六页接线回归（成本 / 告警 / 链路 / 预算 / 用量 / 计费）。
 * 覆盖：真实端点与参数透传、写动作、错误态；OpenLLM 侧已改双通道鉴权（JWT OR API Key）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))
vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}))

import Costs from '@/pages/platform/observability/Costs.vue'
import Alerts from '@/pages/platform/observability/Alerts.vue'
import Traces from '@/pages/platform/observability/Traces.vue'
import Budgets from '@/pages/platform/observability/Budgets.vue'
import Usage from '@/pages/platform/observability/Usage.vue'
import BillingView from '@/pages/platform/observability/BillingView.vue'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const OPENLLM = '/proxy/openllm/api/v1'

const costResponse = {
  time_range: '7d',
  start_time: '2026-10-16T00:00:00',
  end_time: '2026-10-23T00:00:00',
  dimensions: {
    model: [{ value: 'gpt-4o', total_cost: 12.5, request_count: 3, avg_cost_per_request: 4.17 }],
    provider: [{ value: 'OpenAI', total_cost: 12.5, request_count: 3, avg_cost_per_request: 4.17 }],
    user: [{ value: 'u-1', total_cost: 12.5, request_count: 3, avg_cost_per_request: 4.17 }],
  },
  trend: [{ timestamp: '2026-10-23 10:00', cost: 12.5, request_count: 3 }],
}

const budget = (overrides: Record<string, unknown> = {}) => ({
  id: 'b-1',
  name: 'AI 研发月度预算',
  description: null,
  scope: 'global',
  scope_id: null,
  period: 'monthly',
  limit_usd: 800,
  current_usage_usd: 640,
  usage_percentage: 80,
  enabled: true,
  is_exceeded: false,
  created_at: '2026-10-01T00:00:00',
  ...overrides,
})

const rule = (overrides: Record<string, unknown> = {}) => ({
  id: 'r-1',
  name: '延迟超过 500ms',
  description: null,
  alert_type: 'latency_spike',
  condition: { metric: 'latency', operator: 'gt', threshold: 500 },
  severity: 'high',
  channels: [],
  provider: null,
  model: null,
  enabled: true,
  cooldown_seconds: 300,
  last_evaluated_at: null,
  last_fired_at: null,
  created_at: '2026-10-01T00:00:00',
  ...overrides,
})

const alertItem = (overrides: Record<string, unknown> = {}) => ({
  id: 'a-1',
  rule_id: 'r-1',
  alert_type: 'latency_spike',
  severity: 'high',
  status: 'firing',
  title: '延迟过高',
  message: 'gpt-4o P99 820ms',
  provider: 'OpenAI',
  model: 'gpt-4o',
  threshold_value: 500,
  actual_value: 820,
  fired_at: '2026-10-23T09:00:00',
  resolved_at: null,
  acknowledged_at: null,
  created_at: '2026-10-23T09:00:00',
  ...overrides,
})

const trace = (overrides: Record<string, unknown> = {}) => ({
  id: 't-1',
  trace_id: 'trace-abc',
  user_id: 'u-1',
  model: 'gpt-4o',
  provider: 'OpenAI',
  request_type: 'chat',
  start_time: '2026-10-23T09:00:00',
  end_time: '2026-10-23T09:00:01',
  latency_ms: 820,
  status: 'success',
  span_count: 2,
  tokens_total: 1200,
  cost: 0.012,
  created_at: '2026-10-23T09:00:00',
  ...overrides,
})

const usageRecord = (overrides: Record<string, unknown> = {}) => ({
  id: 'ur-1',
  organization_id: 'org-1',
  user_id: 'u-1',
  api_key_id: null,
  provider_id: 'p-1',
  model_id: 'gpt-4o',
  request_id: 'req-1',
  request_type: 'chat',
  tokens_input: 800,
  tokens_output: 400,
  tokens_total: 1200,
  cost: 0.012,
  currency: 'USD',
  latency_ms: 820,
  status: 'success',
  error_code: null,
  error_message: null,
  created_at: '2026-10-23T09:00:00',
  ...overrides,
})

const bill = (overrides: Record<string, unknown> = {}) => ({
  id: 'bill-1',
  organization_id: 'org-1',
  team_id: null,
  period_start: '2026-10-01',
  period_end: '2026-10-31',
  total_requests: 120,
  total_tokens_input: 80000,
  total_tokens_output: 40000,
  total_cost: 12.5,
  currency: 'USD',
  details: { model_calls: 120 },
  status: 'pending',
  notes: '月度结算',
  created_at: '2026-10-31T00:00:00',
  ...overrides,
})

beforeEach(() => vi.clearAllMocks())

describe('v1.9.4 成本分析真实化', () => {
  it('加载成本三源并透传维度与时间范围', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/monitoring/costs')) return Promise.resolve({ data: costResponse })
      if (url.endsWith('/monitoring/costs/optimization-suggestions')) {
        return Promise.resolve({
          data: {
            suggestions: [
              {
                type: 'high_cost_model',
                severity: 'medium',
                title: '模型 gpt-4o 成本较高',
                description: '过去 7 天消耗 120 元',
                recommendation: '切换至 gpt-4o-mini',
                potential_savings: '36 元/周',
              },
            ],
            total: 1,
            generated_at: '2026-10-23T10:00:00',
          },
        })
      }
      if (url.endsWith('/budgets')) {
        return Promise.resolve({ data: { budgets: [budget()], total: 1, page: 1, page_size: 100 } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Costs)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/costs`, {
      params: { dimension: ['model', 'provider', 'user'], time_range: '7d' },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/budgets`, { params: { page: 1, page_size: 100 } })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/costs/optimization-suggestions`)
    const text = wrapper.text()
    expect(text).toContain('AI 研发月度预算')
    expect(text).toContain('模型 gpt-4o 成本较高')
  }, 20000)

  it('创建预算透传 POST /budgets（含阈值）', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/monitoring/costs')) return Promise.resolve({ data: costResponse })
      if (url.endsWith('/monitoring/costs/optimization-suggestions')) {
        return Promise.resolve({ data: { suggestions: [], total: 0, generated_at: '' } })
      }
      return Promise.resolve({ data: { budgets: [], total: 0, page: 1, page_size: 100 } })
    })
    mocks.post.mockResolvedValue({ data: budget() })

    const wrapper = mountPage(Costs)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      budgetForm: { name: string; period: string; limit_usd: number; alert_threshold: number }
      saveBudget: () => Promise<void>
    }
    vm.budgetForm.name = '季度预算'
    vm.budgetForm.period = 'quarterly'
    vm.budgetForm.limit_usd = 1200
    vm.budgetForm.alert_threshold = 70
    await vm.saveBudget()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/budgets`, {
      name: '季度预算',
      scope: 'global',
      period: 'quarterly',
      limit_usd: 1200,
      alert_thresholds: [{ type: 'warning', value: 70 }],
    })
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValue(new Error('upstream 500'))

    const wrapper = mountPage(Costs)
    await flushPromises()

    expect(wrapper.find('[data-test="costs-error"]').text()).toContain('加载失败')
  }, 20000)
})

describe('v1.9.4 告警中心真实化', () => {
  it('加载规则与告警历史', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/alerts/rules')) {
        return Promise.resolve({ data: { rules: [rule()], total: 1, page: 1, page_size: 100 } })
      }
      if (url.endsWith('/alerts')) {
        return Promise.resolve({ data: { alerts: [alertItem()], total: 1, page: 1, page_size: 20 } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Alerts)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/alerts/rules`, { params: { page: 1, page_size: 100 } })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/alerts`, {
      params: { status: undefined, page: 1, page_size: 20 },
    })
    const text = wrapper.text()
    expect(text).toContain('延迟超过 500ms')
    expect(text).toContain('gpt-4o P99 820ms')
  }, 20000)

  it('启停透传 PUT /alerts/rules/{id}', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/alerts/rules')) {
        return Promise.resolve({ data: { rules: [rule()], total: 1, page: 1, page_size: 100 } })
      }
      return Promise.resolve({ data: { alerts: [], total: 0, page: 1, page_size: 20 } })
    })
    mocks.put.mockResolvedValue({ data: rule({ enabled: false }) })

    const wrapper = mountPage(Alerts)
    await flushPromises()

    const vm = wrapper.vm as unknown as { toggleRule: (row: unknown) => Promise<void> }
    await vm.toggleRule(rule({ enabled: false }))
    await flushPromises()

    expect(mocks.put).toHaveBeenCalledWith(`${OPENLLM}/alerts/rules/r-1`, { enabled: false })
  }, 20000)

  it('新建规则透传条件对象', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/alerts/rules')) {
        return Promise.resolve({ data: { rules: [], total: 0, page: 1, page_size: 100 } })
      }
      return Promise.resolve({ data: { alerts: [], total: 0, page: 1, page_size: 20 } })
    })
    mocks.post.mockResolvedValue({ data: rule({ id: 'r-2' }) })

    const wrapper = mountPage(Alerts)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      ruleForm: { name: string; alert_type: string; metric: string; operator: string; threshold: number; severity: string }
      saveRule: () => Promise<void>
    }
    vm.ruleForm.name = '成本阈值'
    vm.ruleForm.alert_type = 'cost_threshold'
    vm.ruleForm.metric = 'cost'
    vm.ruleForm.operator = 'gte'
    vm.ruleForm.threshold = 100
    vm.ruleForm.severity = 'critical'
    await vm.saveRule()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/alerts/rules`, {
      name: '成本阈值',
      alert_type: 'cost_threshold',
      condition: { metric: 'cost', operator: 'gte', threshold: 100 },
      severity: 'critical',
      cooldown_seconds: 300,
    })
  }, 20000)

  it('解决告警透传 POST /alerts/{id}/resolve', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/alerts/rules')) {
        return Promise.resolve({ data: { rules: [], total: 0, page: 1, page_size: 100 } })
      }
      return Promise.resolve({ data: { alerts: [alertItem()], total: 1, page: 1, page_size: 20 } })
    })
    mocks.post.mockResolvedValue({ data: alertItem({ status: 'resolved' }) })

    const wrapper = mountPage(Alerts)
    await flushPromises()

    const vm = wrapper.vm as unknown as { resolveHistory: (id: string) => Promise<void> }
    await vm.resolveHistory('a-1')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/alerts/a-1/resolve`, { resolution_note: null })
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValue(new Error('upstream 401'))

    const wrapper = mountPage(Alerts)
    await flushPromises()

    expect(wrapper.find('[data-test="alerts-error"]').text()).toContain('加载失败')
  }, 20000)
})

describe('v1.9.4 链路追踪真实化', () => {
  it('加载统计与列表并透传筛选参数', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/monitoring/traces/statistics')) {
        return Promise.resolve({
          data: {
            time_range: '24h',
            total_count: 10,
            success_count: 9,
            error_count: 1,
            error_rate: 10,
            avg_latency_ms: 320,
            total_tokens: 12000,
            total_cost: 1.2,
          },
        })
      }
      if (url.endsWith('/monitoring/traces')) {
        return Promise.resolve({ data: { traces: [trace()], total: 1, page: 1, page_size: 20 } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Traces)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/traces/statistics`, {
      params: { time_range: '24h' },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/traces`, {
      params: { status: undefined, model: undefined, page: 1, page_size: 20 },
    })
    expect(wrapper.text()).toContain('gpt-4o')
    expect(wrapper.text()).toContain('820')
  }, 20000)

  it('详情抽屉加载 Span 明细', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/monitoring/traces/statistics')) {
        return Promise.resolve({ data: { time_range: '24h', total_count: 0, success_count: 0, error_count: 0, error_rate: 0, avg_latency_ms: 0, total_tokens: 0, total_cost: 0 } })
      }
      if (url.endsWith('/monitoring/traces/trace-abc')) {
        return Promise.resolve({
          data: {
            ...trace(),
            tenant_id: 'tenant-1',
            error_code: null,
            error_message: null,
            spans: [
              {
                span_id: 's-1',
                name: 'llm.chat',
                kind: 'client',
                parent_span_id: null,
                start_time: '2026-10-23T09:00:00',
                end_time: '2026-10-23T09:00:01',
                duration_ms: 820,
                status: 'ok',
                status_message: null,
                attributes: {},
                events: [],
              },
            ],
          },
        })
      }
      return Promise.resolve({ data: { traces: [trace()], total: 1, page: 1, page_size: 20 } })
    })

    const wrapper = mountPage(Traces)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openDetail: (row: unknown) => Promise<void>
      detail: { trace_id: string; spans: Array<{ name: string }> } | null
    }
    await vm.openDetail(trace())
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/monitoring/traces/trace-abc`)
    expect(vm.detail?.trace_id).toBe('trace-abc')
    expect(vm.detail?.spans[0].name).toBe('llm.chat')
  }, 20000)
})

describe('v1.9.4 预算管理真实化', () => {
  it('加载预算列表并展示进度', async () => {
    mocks.get.mockResolvedValue({ data: { budgets: [budget()], total: 1, page: 1, page_size: 100 } })

    const wrapper = mountPage(Budgets)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/budgets`, { params: { page: 1, page_size: 100 } })
    expect(wrapper.text()).toContain('AI 研发月度预算')
    expect(wrapper.text()).toContain('全局')
  }, 20000)

  it('新建预算透传 POST /budgets', async () => {
    mocks.get.mockResolvedValue({ data: { budgets: [], total: 0, page: 1, page_size: 100 } })
    mocks.post.mockResolvedValue({ data: budget() })

    const wrapper = mountPage(Budgets)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      form: { name: string; scope: string; period: string; limit_usd: number; alert_threshold: number }
      submit: () => Promise<void>
    }
    vm.form.name = '年度预算'
    vm.form.scope = 'team'
    vm.form.period = 'yearly'
    vm.form.limit_usd = 5000
    vm.form.alert_threshold = 90
    await vm.submit()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/budgets`, {
      name: '年度预算',
      scope: 'team',
      period: 'yearly',
      limit_usd: 5000,
      alert_thresholds: [{ type: 'warning', value: 90 }],
    })
  }, 20000)

  it('状态抽屉加载预算状态', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/budgets/b-1/status')) {
        return Promise.resolve({
          data: {
            budget_id: 'b-1',
            name: 'AI 研发月度预算',
            scope: 'global',
            period: 'monthly',
            limit_usd: 800,
            current_usage_usd: 640,
            usage_percentage: 80,
            is_exceeded: false,
            remaining_usd: 160,
            days_remaining: 8,
            projected_usage_usd: 790,
          },
        })
      }
      return Promise.resolve({ data: { budgets: [budget()], total: 1, page: 1, page_size: 100 } })
    })

    const wrapper = mountPage(Budgets)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openStatus: (row: unknown) => Promise<void>
      statusDetail: { remaining_usd: number } | null
    }
    await vm.openStatus(budget())
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/budgets/b-1/status`)
    expect(vm.statusDetail?.remaining_usd).toBe(160)
  }, 20000)
})

describe('v1.9.4 用量统计真实化', () => {
  it('加载总览/趋势/明细并透传日期区间', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/usage/summary')) {
        return Promise.resolve({
          data: {
            tenant_id: null,
            period: 'daily',
            group_by: 'day',
            start_date: '2026-09-24',
            end_date: '2026-10-23',
            total_requests: 120,
            total_prompt_tokens: 8000,
            total_completion_tokens: 4000,
            total_tokens: 12000,
            total_cost: 1.2,
            avg_latency_ms: 320,
            status_breakdown: { success: 120 },
            grouped_data: [],
          },
        })
      }
      if (url.endsWith('/usage/trends')) {
        return Promise.resolve({
          data: {
            tenant_id: null,
            dimension: 'time',
            period: 'day',
            series: [{ date: '2026-10-23', requests: 10, input_tokens: 800, output_tokens: 400, total_tokens: 1200, cost: 0.12 }],
            summary: {},
          },
        })
      }
      if (url.endsWith('/usage/detail')) {
        return Promise.resolve({
          data: { tenant_id: null, start_date: '2026-09-24', end_date: '2026-10-23', total: 1, skip: 0, limit: 200, records: [usageRecord()] },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Usage)
    await flushPromises()

    const vm = wrapper.vm as unknown as { dateRange: [string, string] }
    const [start, end] = vm.dateRange
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/usage/summary`, {
      params: { period: 'daily', group_by: 'day', start_date: start, end_date: end },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/usage/trends`, {
      params: { dimension: 'time', period: 'day', start_date: start, end_date: end },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/usage/detail`, {
      params: { start_date: start, end_date: end, skip: 0, limit: 200 },
    })
    expect(wrapper.text()).toContain('req-1')
  }, 20000)

  it('开始日期晚于结束日期时阻断请求', async () => {
    mocks.get.mockResolvedValue({ data: {} })

    const wrapper = mountPage(Usage)
    await flushPromises()
    mocks.get.mockClear()

    const vm = wrapper.vm as unknown as { dateRange: [string, string]; loadUsage: () => Promise<void> }
    vm.dateRange = ['2026-10-23', '2026-10-01']
    await vm.loadUsage()
    await flushPromises()

    expect(mocks.get).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="usage-error"]').text()).toContain('开始日期不能晚于结束日期')
  }, 20000)
})

describe('v1.9.4 计费真实化', () => {
  it('加载统计/配额/账单/趋势四源', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/billing/usage/statistics')) {
        return Promise.resolve({
          data: {
            total_requests: 120,
            total_tokens_input: 80000,
            total_tokens_output: 40000,
            total_cost: 12.5,
            average_latency_ms: 320,
            status_breakdown: { success: 120 },
          },
        })
      }
      if (url.endsWith('/billing/quotas')) {
        return Promise.resolve({
          data: [
            {
              id: 'q-1',
              organization_id: 'org-1',
              team_id: null,
              quota_type: 'api_calls',
              quota_limit: 10000,
              used_amount: 8000,
              usage_percent: 80,
              period: 'monthly',
              alert_threshold: 80,
              is_exceeded: false,
              period_start: '2026-10-01T00:00:00',
              period_end: '2026-10-31T00:00:00',
              created_at: '2026-10-01T00:00:00',
            },
          ],
        })
      }
      if (url.endsWith('/billing/bills')) return Promise.resolve({ data: [bill()] })
      if (url.endsWith('/usage/trends')) {
        return Promise.resolve({
          data: {
            tenant_id: null,
            dimension: 'time',
            period: 'day',
            series: [{ date: '2026-10-23', requests: 10, input_tokens: 800, output_tokens: 400, total_tokens: 1200, cost: 0.12 }],
            summary: {},
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(BillingView)
    await flushPromises()

    const vm = wrapper.vm as unknown as { dateRange: [string, string] }
    const [start, end] = vm.dateRange
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/billing/usage/statistics`, {
      params: { start_date: start, end_date: end },
    })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/billing/quotas`)
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/billing/bills`)
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/usage/trends`, {
      params: { dimension: 'time', period: 'day', start_date: start, end_date: end },
    })
    const text = wrapper.text()
    expect(text).toContain('月度结算')
    expect(text).toContain('api_calls')
  }, 20000)

  it('加载失败展示错误态', async () => {
    mocks.get.mockRejectedValue(new Error('upstream 500'))

    const wrapper = mountPage(BillingView)
    await flushPromises()

    expect(wrapper.find('[data-test="billing-error"]').text()).toContain('计费数据加载失败')
  }, 20000)
})
