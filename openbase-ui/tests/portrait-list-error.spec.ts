/**
 * ISSUE-002 回归测试：画像列表页错误静默（数据失败无提示与重试入口）
 *
 * 缺陷基线（走查报告 v1.0.0）：/portrait/list 数据接口失败时页面仅显示空表/空态，
 * 无错误提示与重试入口，与 overview 显式错误提示不一致。
 *
 * 修复验收（走查报告 v1.2.0）：
 * 1. 数据请求失败时展示 el-alert 错误条（画像列表加载失败：{原因}）+「点击重试」；
 * 2. 表体空态随错误状态切换为「加载失败，请点击上方提示条『点击重试』」引导文案，
 *    不再误导性显示「暂无画像数据」；
 * 3. KPI/上游健康度独立降级，不阻断页面渲染；
 * 4. 重试成功后错误条自动消失并恢复数据。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import PortraitList from '@/modules/portrait/pages/PortraitList.vue'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'

const mountList = () =>
  mount(PortraitList, {
    global: {
      plugins: [ElementPlus],
      mocks: { $router: { push: vi.fn() } },
    },
  })

const healthyUpstream = () => {
  vi.spyOn(dpsApi, 'getDpsHealth').mockResolvedValue({ status: 'healthy', version: 'v2.8.1' })
  vi.spyOn(dpsApi, 'getReportsOverview').mockResolvedValue({ total_profiles: 40, high_risk_count: 8 })
}

const sampleRow: DpsPortrait = {
  person_id: 'P-1001',
  name: '测试画像',
  risk_level: '75',
  risk_score: 75,
  updated_at: '2026-09-03T10:00:00',
  tags: ['demo'],
}

describe('ISSUE-002: 画像列表页错误态（静默吞错回归）', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('列表接口失败时展示错误条与错误引导空态，不再误显示"暂无画像数据"', async () => {
    healthyUpstream()
    vi.spyOn(dpsApi, 'listPortraits').mockRejectedValue(new Error('Request failed with status code 502'))
    const wrapper = mountList()
    await flushPromises()

    const alert = wrapper.find('.el-alert--error')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('画像列表加载失败')
    expect(alert.text()).toContain('点击重试')

    // 表体空态切换为错误引导文案（缺陷基线为误导性「暂无画像数据」）
    const empty = wrapper.find('.el-table__empty-block')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('加载失败，请点击上方提示条「点击重试」')
    expect(empty.text()).not.toContain('暂无画像数据')
  })

  it('点击「点击重试」恢复成功后错误条消失并渲染数据', async () => {
    healthyUpstream()
    const listSpy = vi.spyOn(dpsApi, 'listPortraits')
    listSpy
      .mockRejectedValueOnce(new Error('Request failed with status code 502'))
      .mockResolvedValueOnce({ items: [sampleRow], total: 1 })
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.find('.el-alert--error').exists()).toBe(true)

    const retry = wrapper.findAll('button').find((b) => b.text() === '点击重试')
    expect(retry).toBeTruthy()
    await retry!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.el-alert--error').exists()).toBe(false)
    expect(listSpy).toHaveBeenCalledTimes(2)
    expect(wrapper.findAll('.el-table__row').length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('测试画像')
  })

  it('KPI 与上游健康度独立降级/展示，不因列表失败而静默空白', async () => {
    vi.spyOn(dpsApi, 'getDpsHealth').mockResolvedValue({ status: 'healthy', version: 'v2.8.1' })
    vi.spyOn(dpsApi, 'getReportsOverview').mockResolvedValue({ total_profiles: 40, high_risk_count: 8 })
    vi.spyOn(dpsApi, 'listPortraits').mockRejectedValue(new Error('boom'))
    const wrapper = mountList()
    await flushPromises()

    const kpis = wrapper.findAll('[data-test="dps-kpi"]')
    expect(kpis.length).toBe(3)
    expect(kpis[0].text()).toContain('40')
    expect(kpis[2].text()).toContain('healthy')
  })
})
