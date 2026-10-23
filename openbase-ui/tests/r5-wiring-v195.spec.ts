/**
 * v1.9.5 R5：治理与 RBAC 七页接线回归。
 * 覆盖：角色/权限目录、工作空间与 Virtual Key、语义路由/熔断器、工具调用、
 * Prompt 模板/版本、Prompt 实验、A/B 测试；OpenLLM 侧已改双通道鉴权。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))
vi.mock('vue-router', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('vue-router')
  return { ...actual, useRoute: () => ({ meta: { title: '路由策略' } }) }
})

import RolesView from '@/pages/platform/identity/RolesView.vue'
import WorkspacesView from '@/pages/platform/identity/WorkspacesView.vue'
import Routing from '@/pages/platform/governance/Routing.vue'
import ToolCallMonitorView from '@/pages/platform/governance/ToolCallMonitorView.vue'
import PromptTemplatesView from '@/pages/platform/governance/PromptTemplatesView.vue'
import PromptExperimentsView from '@/pages/platform/governance/PromptExperimentsView.vue'
import AbTestView from '@/pages/platform/governance/AbTestView.vue'

const globalOptions = {
  plugins: [ElementPlus],
  stubs: { PageContainer: { template: '<div><slot /></div>' } },
}

function mountPage(component: unknown) {
  return mount(component as never, { global: globalOptions })
}

const OPENLLM = '/proxy/openllm/api/v1'

const role = (overrides: Record<string, unknown> = {}) => ({
  id: 'r-1',
  code: 'org_admin',
  name: '组织管理员',
  description: '业务写权限',
  role_type: 'org',
  level: 20,
  scope: 'org',
  organization_id: null,
  metadata_: {},
  is_active: true,
  is_system: false,
  created_at: '2026-10-01T00:00:00',
  updated_at: '2026-10-01T00:00:00',
  ...overrides,
})

const workspace = (overrides: Record<string, unknown> = {}) => ({
  id: 'ws-1',
  name: '默认工作空间',
  description: '平台默认空间',
  owner_id: 'u-1',
  settings: {},
  quota: {},
  status: 'active',
  created_at: '2026-10-01T00:00:00',
  updated_at: '2026-10-01T00:00:00',
  ...overrides,
})

beforeEach(() => vi.clearAllMocks())

describe('v1.9.5 角色与权限真实化', () => {
  it('加载角色列表并展示系统标记', async () => {
    mocks.get.mockResolvedValue({ data: [role(), role({ id: 'r-2', code: 'admin', name: '管理员', is_system: true })] })

    const wrapper = mountPage(RolesView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/roles`, { params: { limit: 200 } })
    expect(wrapper.text()).toContain('组织管理员')
    expect(wrapper.text()).toContain('系统')
  }, 20000)

  it('权限抽屉加载目录与角色详情并保存', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/roles/permissions/catalog')) {
        return Promise.resolve({
          data: [
            { id: 'p-1', code: 'role:read', name: '角色-查看', description: null, resource_type: 'role', action: 'read', scope: 'platform', group_name: '角色权限', is_active: true },
            { id: 'p-2', code: 'role:write', name: '角色-写入', description: null, resource_type: 'role', action: 'write', scope: 'platform', group_name: '角色权限', is_active: true },
          ],
        })
      }
      if (url.endsWith('/roles/r-1')) {
        return Promise.resolve({
          data: { ...role(), permissions: [{ permission_id: 'p-1', code: 'role:read', name: '角色-查看', resource_type: 'role', action: 'read', constraints: {} }] },
        })
      }
      return Promise.resolve({ data: [role()] })
    })
    mocks.put.mockResolvedValue({ data: { ...role(), permissions: [] } })

    const wrapper = mountPage(RolesView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openPerms: (row: unknown) => Promise<void>
      checkedPermIds: string[]
      savePerms: () => Promise<void>
    }
    await vm.openPerms(role())
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/roles/permissions/catalog`)
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/roles/r-1`)
    expect(vm.checkedPermIds).toEqual(['p-1'])

    vm.checkedPermIds = ['p-1', 'p-2']
    await vm.savePerms()
    await flushPromises()

    expect(mocks.put).toHaveBeenCalledWith(`${OPENLLM}/roles/r-1/permissions`, {
      permission_ids: ['p-1', 'p-2'],
    })
  }, 20000)
})

describe('v1.9.5 工作空间真实化', () => {
  it('加载工作空间、资源统计与 Virtual Key', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/workspaces')) return Promise.resolve({ data: [workspace()] })
      if (url.endsWith('/workspaces/ws-1/resources')) {
        return Promise.resolve({
          data: { workspace_id: 'ws-1', member_count: 3, virtual_key_count: 1, total_requests: 10, total_tokens: 1000 },
        })
      }
      if (url.endsWith('/virtual-keys')) {
        return Promise.resolve({
          data: [
            {
              id: 'k-1',
              workspace_id: 'ws-1',
              name: 'default',
              key_prefix: 'sk-abc',
              quota: {},
              rate_limit: {},
              model_whitelist: [],
              permissions: {},
              expires_at: null,
              last_used_at: null,
              usage_stats: {},
              is_active: true,
              created_at: '2026-10-01T00:00:00',
            },
          ],
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(WorkspacesView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/workspaces`, { params: { limit: 200 } })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/workspaces/ws-1/resources`)
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/virtual-keys`, { params: { workspace_id: 'ws-1' } })
    expect(wrapper.text()).toContain('默认工作空间')
    expect(wrapper.text()).toContain('3')
  }, 20000)

  it('创建工作空间透传 POST /workspaces', async () => {
    mocks.get.mockResolvedValue({ data: [] })
    mocks.post.mockResolvedValue({ data: workspace() })

    const wrapper = mountPage(WorkspacesView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      form: { name: string; description: string }
      save: () => Promise<void>
    }
    vm.form.name = '模型组空间'
    vm.form.description = '模型研发'
    await vm.save()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/workspaces`, {
      name: '模型组空间',
      description: '模型研发',
    })
  }, 20000)

  it('已有 Key 时轮换走 POST /virtual-keys/{id}/rotate', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/workspaces')) return Promise.resolve({ data: [workspace()] })
      if (url.endsWith('/workspaces/ws-1/resources')) {
        return Promise.resolve({ data: { workspace_id: 'ws-1', member_count: 1, virtual_key_count: 1, total_requests: 0, total_tokens: 0 } })
      }
      if (url.endsWith('/virtual-keys')) {
        return Promise.resolve({ data: [{ id: 'k-1', workspace_id: 'ws-1', name: 'default', key_prefix: 'sk-abc', quota: {}, rate_limit: {}, model_whitelist: [], permissions: {}, expires_at: null, last_used_at: null, usage_stats: {}, is_active: true, created_at: '' }] })
      }
      return Promise.resolve({ data: {} })
    })
    mocks.post.mockResolvedValue({ data: { id: 'k-1', key: 'sk-new-full-key', key_prefix: 'sk-new' } })

    const wrapper = mountPage(WorkspacesView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      rotateOrCreateKey: (row: unknown) => Promise<void>
      createdKey: string
    }
    await vm.rotateOrCreateKey(workspace())
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/virtual-keys/k-1/rotate`, {})
    expect(vm.createdKey).toBe('sk-new-full-key')
  }, 20000)
})

describe('v1.9.5 路由策略与熔断器真实化', () => {
  it('加载语义路由与熔断器列表', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/routing/semantic')) {
        return Promise.resolve({
          data: {
            total: 1,
            items: [
              {
                id: 'rt-1',
                name: '客服意图路由',
                description: null,
                category: 'chat',
                model_id: null,
                provider_id: null,
                sample_queries: ['怎么退款'],
                enabled: true,
                priority: 10,
                threshold: 0.7,
                metadata: {},
                created_at: null,
                updated_at: null,
              },
            ],
          },
        })
      }
      if (url.endsWith('/routing/circuit-breakers')) {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 'cb-1',
                provider: 'openai',
                model: 'gpt-4o',
                state: 'OPEN',
                failure_count: 5,
                success_count: 10,
                consecutive_successes: 0,
                consecutive_failures: 5,
                error_rate: 0.33,
                last_failure_time: null,
                last_success_time: null,
                last_state_change: null,
                total_calls: 15,
                total_failures: 5,
                total_successes: 10,
                config: {},
                created_at: null,
                updated_at: null,
              },
            ],
            total: 1,
            page: 1,
            page_size: 100,
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(Routing)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/routing/semantic`, { params: { limit: 200 } })
    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/routing/circuit-breakers`, {
      params: { page: 1, page_size: 100 },
    })
    const text = wrapper.text()
    expect(text).toContain('客服意图路由')
    expect(text).toContain('开启')
  }, 20000)

  it('新建策略透传 POST /routing/semantic', async () => {
    mocks.get.mockResolvedValue({ data: { total: 0, items: [] } })

    const wrapper = mountPage(Routing)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      strategyForm: {
        name: string
        category: string
        priority: number
        threshold: number
        sampleQueries: string
        description: string
      }
      saveStrategy: () => Promise<void>
    }
    mocks.post.mockResolvedValue({ data: { id: 'rt-2' } })
    vm.strategyForm.name = '代码路由'
    vm.strategyForm.category = 'code'
    vm.strategyForm.priority = 20
    vm.strategyForm.threshold = 0.8
    vm.strategyForm.sampleQueries = '写一个函数\n修复 bug'
    vm.strategyForm.description = ''
    await vm.saveStrategy()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/routing/semantic`, {
      name: '代码路由',
      category: 'code',
      priority: 20,
      threshold: 0.8,
      sample_queries: ['写一个函数', '修复 bug'],
      description: undefined,
      enabled: true,
    })
  }, 20000)

  it('熔断器重置透传 POST /routing/circuit-breakers/{id}/reset', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/routing/semantic')) return Promise.resolve({ data: { total: 0, items: [] } })
      return Promise.resolve({ data: { items: [], total: 0, page: 1, page_size: 100 } })
    })
    mocks.post.mockResolvedValue({ data: { success: true, message: '已重置', current_state: 'CLOSED' } })

    const wrapper = mountPage(Routing)
    await flushPromises()

    const vm = wrapper.vm as unknown as { resetBreaker: (id: string) => Promise<void> }
    await vm.resetBreaker('cb-1')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/routing/circuit-breakers/cb-1/reset`, {})
  }, 20000)
})

describe('v1.9.5 工具调用真实化', () => {
  it('加载工具调用列表并打开详情', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/tool-calls')) {
        return Promise.resolve({
          data: {
            total: 1,
            items: [
              {
                id: 'tc-1',
                tenant_id: 't-1',
                user_id: 'u-1',
                conversation_id: null,
                plugin_id: 'p-1',
                tool_name: 'web_search',
                input_params: { query: 'OpenBase' },
                output_result: { hits: 3 },
                status: 'success',
                error_message: null,
                token_count: 120,
                latency_ms: 680,
                created_at: '2026-10-23T10:00:00',
                completed_at: '2026-10-23T10:00:01',
              },
            ],
          },
        })
      }
      if (url.endsWith('/tool-calls/tc-1')) {
        return Promise.resolve({
          data: {
            id: 'tc-1',
            tenant_id: 't-1',
            user_id: 'u-1',
            conversation_id: null,
            plugin_id: 'p-1',
            tool_name: 'web_search',
            input_params: { query: 'OpenBase' },
            output_result: { hits: 3 },
            status: 'success',
            error_message: null,
            token_count: 120,
            latency_ms: 680,
            created_at: '2026-10-23T10:00:00',
            completed_at: '2026-10-23T10:00:01',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage(ToolCallMonitorView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/tool-calls`, {
      params: { status: undefined, tool_name: undefined, skip: 0, limit: 20 },
    })
    expect(wrapper.text()).toContain('web_search')

    const vm = wrapper.vm as unknown as {
      openDetail: (row: unknown) => Promise<void>
      currentDetail: { id: string } | null
    }
    await vm.openDetail({ id: 'tc-1' })
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/tool-calls/tc-1`)
    expect(vm.currentDetail?.id).toBe('tc-1')
  }, 20000)
})

describe('v1.9.5 Prompt 模板真实化', () => {
  it('加载模板列表并创建模板', async () => {
    mocks.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 'tpl-1',
            name: '客服助手',
            content: '你好 {{question}}',
            variables: [],
            category: 'chat',
            description: null,
            current_version: 2,
            is_system: false,
            created_by: 'u-1',
            workspace_id: null,
            created_at: '2026-10-01T00:00:00',
            updated_at: '2026-10-01T00:00:00',
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    })

    const wrapper = mountPage(PromptTemplatesView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/prompt-templates`, {
      params: { category: undefined, keyword: undefined, page: 1, page_size: 20 },
    })
    expect(wrapper.text()).toContain('客服助手')
    expect(wrapper.text()).toContain('v2')
  }, 20000)

  it('版本抽屉加载并回滚', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/versions')) {
        return Promise.resolve({
          data: {
            items: [
              { id: 'v-2', template_id: 'tpl-1', version: 2, content: 'v2', changelog: '调整', created_by: 'u-1', created_at: '2026-10-02T00:00:00' },
            ],
            total: 1,
          },
        })
      }
      return Promise.resolve({
        data: {
          items: [
            {
              id: 'tpl-1',
              name: '客服助手',
              content: '你好 {{question}}',
              variables: [],
              category: 'chat',
              description: null,
              current_version: 2,
              is_system: false,
              created_by: 'u-1',
              workspace_id: null,
              created_at: '2026-10-01T00:00:00',
              updated_at: '2026-10-01T00:00:00',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      })
    })
    mocks.post.mockResolvedValue({ data: { id: 'tpl-1', name: '客服助手' } })

    const wrapper = mountPage(PromptTemplatesView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openVersions: (row: unknown) => Promise<void>
      rollback: (version: number) => Promise<void>
      versions: Array<{ version: number }>
    }
    await vm.openVersions({ id: 'tpl-1', name: '客服助手', is_system: false })
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/prompt-templates/tpl-1/versions`)
    expect(vm.versions[0].version).toBe(2)

    await vm.rollback(1)
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/prompt-templates/tpl-1/rollback/1`, {})
  }, 20000)
})

describe('v1.9.5 Prompt 实验真实化', () => {
  it('加载实验并创建（两变体）', async () => {
    mocks.get.mockResolvedValue({
      data: [
        {
          id: 'exp-1',
          name: '开场白优化',
          description: null,
          prompt_template_id: null,
          variants: [{ name: 'A', content: 'a' }, { name: 'B', content: 'b' }],
          status: 'draft',
          metrics: {},
          winner_variant: null,
          created_by: 'u-1',
          created_at: '2026-10-01T00:00:00',
          updated_at: '2026-10-01T00:00:00',
        },
      ],
    })

    const wrapper = mountPage(PromptExperimentsView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/prompt-experiments`, {
      params: { status_filter: undefined, limit: 200 },
    })
    expect(wrapper.text()).toContain('开场白优化')

    const vm = wrapper.vm as unknown as {
      form: { name: string; description: string; variants: Array<{ name: string; content: string }> }
      save: () => Promise<void>
    }
    mocks.post.mockResolvedValue({ data: { id: 'exp-2' } })
    vm.form.name = '新实验'
    vm.form.variants = [
      { name: 'A', content: '内容 A' },
      { name: 'B', content: '内容 B' },
    ]
    await vm.save()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/prompt-experiments`, {
      name: '新实验',
      description: undefined,
      variants: [
        { name: 'A', content: '内容 A' },
        { name: 'B', content: '内容 B' },
      ],
    })
  }, 20000)

  it('报表抽屉加载变体统计', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/report')) {
        return Promise.resolve({
          data: {
            experiment_id: 'exp-1',
            experiment_name: '开场白优化',
            variant_stats: { A: { samples: 10, successes: 9, avg_latency_ms: 120 } },
            recommendation: '建议采用变体 A',
          },
        })
      }
      return Promise.resolve({ data: [] })
    })

    const wrapper = mountPage(PromptExperimentsView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openReport: (row: unknown) => Promise<void>
      reportRows: Array<{ variant: string; successRate: string }>
    }
    await vm.openReport({ id: 'exp-1', name: '开场白优化' })
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/prompt-experiments/exp-1/report`)
    expect(vm.reportRows[0].variant).toBe('A')
    expect(vm.reportRows[0].successRate).toBe('90.0%')
  }, 20000)
})

describe('v1.9.5 A/B 测试真实化', () => {
  it('加载实验并创建（流量拆分）', async () => {
    mocks.get.mockResolvedValue({
      data: [
        {
          id: 'ab-1',
          name: '客服模型 A/B',
          description: null,
          model_a: 'gpt-4o',
          model_b: 'gpt-4o-mini',
          traffic_split: { model_a: 0.5, model_b: 0.5 },
          metrics: {},
          status: 'running',
          start_time: '2026-10-01T00:00:00',
          end_time: null,
          created_by: 'u-1',
          organization_id: null,
          target_config: {},
          created_at: '2026-10-01T00:00:00',
          updated_at: '2026-10-01T00:00:00',
        },
      ],
    })

    const wrapper = mountPage(AbTestView)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/routing/ab-tests`, {
      params: { status_filter: undefined, limit: 200 },
    })
    expect(wrapper.text()).toContain('客服模型 A/B')
    expect(wrapper.text()).toContain('50%')

    const vm = wrapper.vm as unknown as {
      form: { name: string; model_a: string; model_b: string; ratioA: number; description: string }
      save: () => Promise<void>
    }
    mocks.post.mockResolvedValue({ data: { id: 'ab-2' } })
    vm.form.name = '摘要模型对比'
    vm.form.model_a = 'qwen2.5-7b'
    vm.form.model_b = 'llama3-8b'
    vm.form.ratioA = 30
    await vm.save()
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/routing/ab-tests`, {
      name: '摘要模型对比',
      model_a: 'qwen2.5-7b',
      model_b: 'llama3-8b',
      description: undefined,
      traffic_split: { model_a: 0.3, model_b: 0.7 },
    })
  }, 20000)

  it('详情抽屉加载报表指标', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/report')) {
        return Promise.resolve({
          data: {
            test_id: 'ab-1',
            test_name: '客服模型 A/B',
            model_a: 'gpt-4o',
            model_b: 'gpt-4o-mini',
            model_a_stats: { count: 10, success_rate: 0.95 },
            model_b_stats: { count: 12, success_rate: 0.9 },
            significance: { p_value: 0.03, is_significant: true },
            recommendation: '推荐 gpt-4o',
          },
        })
      }
      return Promise.resolve({ data: [] })
    })

    const wrapper = mountPage(AbTestView)
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      openDetail: (row: unknown) => Promise<void>
      metricRows: Array<{ metric: string; valueA: string; valueB: string }>
    }
    await vm.openDetail({ id: 'ab-1', name: '客服模型 A/B', traffic_split: { model_a: 0.5 } })
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/routing/ab-tests/ab-1/report`)
    const countRow = vm.metricRows.find((row) => row.metric === 'count')
    expect(countRow).toEqual({ metric: 'count', valueA: '10', valueB: '12' })
  }, 20000)
})
