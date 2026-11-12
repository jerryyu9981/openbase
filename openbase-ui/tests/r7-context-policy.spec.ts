/**
 * 批次 4 R7：上下文裁剪策略前端展示与透传回归
 *
 * 覆盖契约：《批次 3 全链路贯通修复规格》§2（context_policy / context_meta）。
 * 纯函数用例 + 设置页权限与保存行为；不依赖后端。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'

import {
  CONTEXT_POLICY_STORAGE_KEY,
  extractContextMeta,
  formatContextMeta,
  loadContextPolicy,
  normalizeContextPolicy,
  saveContextPolicy,
} from '@/core/contextPolicy'
import InferenceSettings from '@/modules/openllm/pages/InferenceSettings.vue'
import { useAuthStore } from '@/core/stores/auth'

function mountPage(permissions: string[]) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.user = { id: 1, username: 'tester', permissions }
  return mount(InferenceSettings as never, {
    global: {
      plugins: [pinia, ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => localStorage.clear())

describe('上下文策略校验（normalizeContextPolicy）', () => {
  it('四种合法策略均被接受', () => {
    for (const strategy of ['recent', 'head_tail', 'system_priority', 'summarize_old']) {
      const policy = normalizeContextPolicy({ strategy, max_tokens: 1024 })
      expect(policy?.strategy).toBe(strategy)
      expect(policy?.max_tokens).toBe(1024)
    }
  })

  it('非法策略回落 recent', () => {
    expect(normalizeContextPolicy({ strategy: 'bogus', max_tokens: 512 })).toEqual({
      strategy: 'recent',
      max_tokens: 512,
    })
  })

  it('max_tokens 越界或非整数被丢弃', () => {
    expect(normalizeContextPolicy({ strategy: 'head_tail', max_tokens: 0 })).toEqual({
      strategy: 'head_tail',
    })
    expect(normalizeContextPolicy({ strategy: 'head_tail', max_tokens: -8 })).toEqual({
      strategy: 'head_tail',
    })
    expect(normalizeContextPolicy({ strategy: 'head_tail', max_tokens: 200001 })).toEqual({
      strategy: 'head_tail',
    })
    expect(normalizeContextPolicy({ strategy: 'head_tail', max_tokens: 12.5 })).toEqual({
      strategy: 'head_tail',
    })
  })

  it('preserve_recent_n 仅 system_priority 输出且范围内保留', () => {
    expect(normalizeContextPolicy({ strategy: 'system_priority', preserve_recent_n: 6 })).toEqual({
      strategy: 'system_priority',
      preserve_recent_n: 6,
    })
    expect(normalizeContextPolicy({ strategy: 'head_tail', preserve_recent_n: 6 })).toEqual({
      strategy: 'head_tail',
    })
    expect(normalizeContextPolicy({ strategy: 'system_priority', preserve_recent_n: 101 })).toEqual({
      strategy: 'system_priority',
    })
  })

  it('等价默认值返回 null（不透传）', () => {
    expect(normalizeContextPolicy({ strategy: 'recent' })).toBeNull()
    expect(normalizeContextPolicy(null)).toBeNull()
    expect(normalizeContextPolicy([])).toBeNull()
    expect(normalizeContextPolicy('recent')).toBeNull()
  })
})

describe('本地策略读写（load/save）', () => {
  it('保存后可读回，null 清除配置', () => {
    saveContextPolicy({ strategy: 'summarize_old', max_tokens: 2048 })
    expect(loadContextPolicy()).toEqual({ strategy: 'summarize_old', max_tokens: 2048 })
    saveContextPolicy(null)
    expect(localStorage.getItem(CONTEXT_POLICY_STORAGE_KEY)).toBeNull()
    expect(loadContextPolicy()).toBeNull()
  })

  it('损坏的 JSON 视为未配置', () => {
    localStorage.setItem(CONTEXT_POLICY_STORAGE_KEY, '{not-json')
    expect(loadContextPolicy()).toBeNull()
  })
})

describe('context_meta 提取与格式化', () => {
  it('支持顶层与 data 包裹两种形态', () => {
    const meta = { strategy: 'head_tail', included_messages: 5, history_messages: 12, budget_tokens: 2048 }
    expect(extractContextMeta({ context_meta: meta })).toEqual(meta)
    expect(extractContextMeta({ data: { context_meta: meta } })).toEqual(meta)
    expect(extractContextMeta({ routing_trace: {} })).toBeNull()
    expect(extractContextMeta(null)).toBeNull()
  })

  it('生成单行摘要', () => {
    expect(
      formatContextMeta({ strategy: 'head_tail', included_messages: 5, history_messages: 12, budget_tokens: 2048 }),
    ).toBe('上下文 首尾保留 · 入参 5/12 条 · 预算 2048 tokens')
    expect(formatContextMeta({ strategy: 'recent', applied: false })).toBe('上下文 保留最近（默认） · 上游未应用')
    expect(formatContextMeta(null)).toBe('')
  })
})

describe('推理设置页', () => {
  it('非管理员只读：无保存按钮并提示权限', () => {
    const wrapper = mountPage([])
    expect(wrapper.find('[data-test="context-policy-readonly"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="context-policy-save"]').exists()).toBe(false)
  })

  it('管理员展示已保存策略，可保存并恢复默认', async () => {
    saveContextPolicy({ strategy: 'summarize_old', max_tokens: 1024 })
    const wrapper = mountPage(['system:config'])
    expect(wrapper.find('[data-test="context-policy-current"]').text()).toContain('早期摘要')
    expect(wrapper.find('[data-test="context-policy-current"]').text()).toContain('预算 1024 tokens')

    await wrapper.find('[data-test="context-policy-save"]').trigger('click')
    expect(loadContextPolicy()).toEqual({ strategy: 'summarize_old', max_tokens: 1024 })

    await wrapper.find('[data-test="context-policy-reset"]').trigger('click')
    expect(loadContextPolicy()).toBeNull()
  })
})
