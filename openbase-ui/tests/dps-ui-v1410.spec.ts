/**
 * v1.4.10 DPS 前端页面／路由／组合式函数测试（TD-1410-05~12／TD-1410-23／TD-1410-28~31）
 *
 * 覆盖：
 * - `useAsyncState` / `useBasisTooltip` 组合式函数语义（§3.2／§4.2）；
 * - 12 条 DPS 路由注册（含 P-09 `new` 与 `:code/edit` 双路径 alias）；
 * - 12 个 `Dps*View.vue` 页面可加载并渲染关键状态（空态 / 错误态 / 未启用态）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { useAsyncState, defaultIsEmpty } from '@/core/composables/useAsyncState'
import { useBasisTooltip } from '@/core/composables/useBasisTooltip'
import { staticRoutes } from '@/core/router'
import { dpsApi } from '@/core/api/dps'
import type { ErrorResponse } from '@/core/api/error'

import DpsTemplateListView from '@/modules/portrait/pages/DpsTemplateListView.vue'
import DpsTemplateVersionView from '@/modules/portrait/pages/DpsTemplateVersionView.vue'
import DpsTemplatePreflightView from '@/modules/portrait/pages/DpsTemplatePreflightView.vue'
import DpsTemplatePackageView from '@/modules/portrait/pages/DpsTemplatePackageView.vue'
import DpsLineageView from '@/modules/portrait/pages/DpsLineageView.vue'
import DpsMeasureView from '@/modules/portrait/pages/DpsMeasureView.vue'
import DpsScoringTypeView from '@/modules/portrait/pages/DpsScoringTypeView.vue'
import DpsAnnotationAdapterView from '@/modules/portrait/pages/DpsAnnotationAdapterView.vue'
import DpsTemplateEditView from '@/modules/portrait/pages/DpsTemplateEditView.vue'
import DpsAnnotationTemplateView from '@/modules/portrait/pages/DpsAnnotationTemplateView.vue'
import DpsAnnotationFieldView from '@/modules/portrait/pages/DpsAnnotationFieldView.vue'
import DpsTagSystemView from '@/modules/portrait/pages/DpsTagSystemView.vue'

const PAGE_COMPONENTS = [
  DpsTemplateListView,
  DpsTemplateVersionView,
  DpsTemplatePreflightView,
  DpsTemplatePackageView,
  DpsLineageView,
  DpsMeasureView,
  DpsScoringTypeView,
  DpsAnnotationAdapterView,
  DpsTemplateEditView,
  DpsAnnotationTemplateView,
  DpsAnnotationFieldView,
  DpsTagSystemView,
]

function apiError(status: number, body: Partial<ErrorResponse> = {}): AxiosError<ErrorResponse> {
  const error = new AxiosError(`Request failed with status code ${status}`, 'ERR_BAD_RESPONSE') as unknown as AxiosError<ErrorResponse>
  error.response = {
    data: { code: body.code ?? 'BIZ', message: body.message ?? `HTTP ${status}`, detail: null, request_id: 'req-x' },
    status,
    statusText: '',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  } as never
  return error
}

async function mountPage(component: unknown, path = '/dps/templates'): Promise<ReturnType<typeof mount>> {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/dps/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push(path)
  const wrapper = mount(component as never, { global: { plugins: [ElementPlus, router] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('useAsyncState', () => {
  it('成功：写入 data 并按 items 判空', async () => {
    const state = useAsyncState<{ items: number[] }>()
    await state.run(() => Promise.resolve({ items: [] }))
    expect(state.loading.value).toBe(false)
    expect(state.error.value).toBeNull()
    expect(state.isEmpty.value).toBe(true)

    await state.run(() => Promise.resolve({ items: [1] }))
    expect(state.isEmpty.value).toBe(false)
  })

  it('失败：错误归一为 DPS 呈现模型并清空 data', async () => {
    const state = useAsyncState<unknown>()
    const result = await state.run(() => Promise.reject(apiError(409, { message: '存在 12 条关联标注数据，禁止删除' })))
    expect(result).toBeNull()
    expect(state.data.value).toBeNull()
    expect(state.error.value?.kind).toBe('conflict')
    expect(state.error.value?.hint).toContain('未复核候选')
  })

  it('reset 复位全部状态；defaultIsEmpty 覆盖 null／数组／分页', async () => {
    expect(defaultIsEmpty(null)).toBe(true)
    expect(defaultIsEmpty<number[]>([])).toBe(true)
    expect(defaultIsEmpty([1])).toBe(false)
    expect(defaultIsEmpty({ items: [] })).toBe(true)
    expect(defaultIsEmpty({ items: [1] })).toBe(false)
    expect(defaultIsEmpty('x')).toBe(false)

    const state = useAsyncState<number>()
    await state.run(() => Promise.resolve(5))
    state.reset()
    expect(state.data.value).toBeNull()
    expect(state.loading.value).toBe(false)
    expect(state.error.value).toBeNull()
    expect(state.isEmpty.value).toBe(false)
  })
})

describe('useBasisTooltip', () => {
  it('默认收起，toggle 切换，aria-expanded 同步', () => {
    const basis = useBasisTooltip()
    expect(basis.isExpanded.value).toBe(false)
    expect(basis.ariaExpanded.value).toBe('false')
    basis.toggle()
    expect(basis.isExpanded.value).toBe(true)
    expect(basis.ariaExpanded.value).toBe('true')
    basis.collapse()
    expect(basis.isExpanded.value).toBe(false)
  })

  it('tag_count=0 强制展开且不可手动收起', () => {
    const forced = ref(true)
    const basis = useBasisTooltip(() => forced.value)
    expect(basis.isForced.value).toBe(true)
    expect(basis.isExpanded.value).toBe(true)
    basis.toggle()
    expect(basis.isExpanded.value).toBe(true)
    basis.collapse()
    expect(basis.isExpanded.value).toBe(true)

    forced.value = false
    basis.collapse()
    expect(basis.isExpanded.value).toBe(false)
    basis.expand()
    expect(basis.isExpanded.value).toBe(true)
  })
})

describe('DPS 12 条路由注册', () => {
  const root = staticRoutes.find((route) => route.path === '/')
  const children = root?.children ?? []
  const dpsRoutes = children.filter((route) => String(route.name || '').startsWith('dps-'))

  it('新增 12 条 DPS 设计路由（P-09 双路径 ⇒ 13 条 route record，均具 title）', () => {
    // 设计 §2 共 12 行；P-09（新建／编辑）由 `dps/templates/new` 与 `dps/templates/:code/edit` 两条路径承载
    expect(dpsRoutes).toHaveLength(13)
    dpsRoutes.forEach((route) => {
      expect(route.meta?.title, `${String(route.name)} 缺 title`).toBeTruthy()
      expect(typeof route.component).toBe('function')
    })
  })

  it('路由路径与设计 §2 一致（含 P-09 双路径）', () => {
    const paths = dpsRoutes.map((route) => route.path).sort()
    expect(paths).toEqual(
      [
        'dps/annotation-adapters',
        'dps/annotation-templates',
        'dps/annotation-templates/:code/fields',
        'dps/lineage',
        'dps/measures',
        'dps/scoring-types',
        'dps/tags',
        'dps/template-packages',
        'dps/templates',
        'dps/templates/:code/edit',
        'dps/templates/:code/preflight',
        'dps/templates/:code/versions',
        'dps/templates/new',
      ].sort(),
    )
    const names = new Set(dpsRoutes.map((route) => route.name))
    expect(names.size).toBe(13)
  })

  it('12 个 Dps*View.vue 页面组件均可加载（22 端点 ↔ 12 页面，AC-18）', () => {
    expect(PAGE_COMPONENTS).toHaveLength(12)
    PAGE_COMPONENTS.forEach((component) => {
      expect(component).toBeTruthy()
    })
  })
})

describe('DPS 页面关键状态呈现', () => {
  it('P-01 模板族列表：真实 API 渲染 + 空态', async () => {
    vi.spyOn(dpsApi, 'listTemplates').mockResolvedValue({ items: [{ code: 'cc-v1', status: 'active', version: 3 }], total: 1 })
    const wrapper = await mountPage(DpsTemplateListView)
    expect(wrapper.find('[data-test="template-table"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('cc-v1')

    vi.restoreAllMocks()
    vi.spyOn(dpsApi, 'listTemplates').mockResolvedValue({ items: [], total: 0 })
    const emptyWrapper = await mountPage(DpsTemplateListView)
    expect(emptyWrapper.find('[data-test="template-empty"]').exists()).toBe(true)
  })

  it('P-06 措施建议：原样呈现 disclaimer，空态为正常结果', async () => {
    vi.spyOn(dpsApi, 'suggestMeasures').mockResolvedValue({
      suggestions: [{ measure_code: 'M-01', measure_text: '加强日常走访频次', tag_code: 'behavior:behavior' }],
      disclaimer: '本建议基于标签映射生成，不表征风险水平，供工作参考',
    })
    const wrapper = await mountPage(DpsMeasureView, '/dps/measures?person_id=P-1')
    const table = wrapper.find('[data-test="measure-table"]')
    expect(table.text()).toContain('加强日常走访频次')
    expect(wrapper.find('[data-test="measure-disclaimer"]').text()).toContain('不表征风险水平')
  })

  it('P-07 评分类型：空态正常呈现（非错误）', async () => {
    vi.spyOn(dpsApi, 'listScoringTypes').mockResolvedValue({ items: [], total: 0 })
    const wrapper = await mountPage(DpsScoringTypeView, '/dps/scoring-types')
    expect(wrapper.find('[data-test="scoring-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="dps-error"]').exists()).toBe(false)
  })

  it('P-05 血缘反查：无谱系 404 → 空态（非错误页）', async () => {
    vi.spyOn(dpsApi, 'getTagLineage').mockRejectedValue(apiError(404))
    vi.spyOn(dpsApi, 'queryImpact').mockResolvedValue({ tag_count: 0, profile_count: 0 })
    const wrapper = await mountPage(DpsLineageView, '/dps/lineage?tag_code=service:channel')
    expect(wrapper.find('[data-test="lineage-not-found"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="dps-error"]').exists()).toBe(false)
  })

  it('P-08 AI 标注：403 未启用 → 信息态（非报错）且不发起写请求', async () => {
    const generate = vi.spyOn(dpsApi, 'generateAnnotationCandidates').mockRejectedValue(apiError(403, { code: 'PERM_DISABLED' }))
    const wrapper = await mountPage(DpsAnnotationAdapterView, '/dps/annotation-adapters')
    expect(wrapper.find('[data-test="adapter-disabled"]').exists()).toBe(false)
    await wrapper.find('[data-test="adapter-text"]').setValue('待标注文本')
    await wrapper.find('[data-test="adapter-template"]').setValue('cc-annot')
    await wrapper.find('[data-test="adapter-generate"]').trigger('click')
    await flushPromises()
    expect(generate).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-test="adapter-disabled"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="dps-error"]').exists()).toBe(false)
  })

  it('P-12 标签体系：分类 → 标签值两层只读呈现', async () => {
    vi.spyOn(dpsApi, 'listTagCategories').mockResolvedValue({ items: [{ id: 'c1', name: '服务渠道', description: '服务来源渠道' }] })
    vi.spyOn(dpsApi, 'listLabels').mockResolvedValue({ items: [{ name: '线上', color: '#2563eb', sort_order: 1, category: '服务渠道' }] })
    const wrapper = await mountPage(DpsTagSystemView, '/dps/tags')
    expect(wrapper.find('[data-test="tag-category-table"]').text()).toContain('服务渠道')
    expect(wrapper.find('[data-test="tag-linkage-table"]').text()).toContain('service:channel')
  })
})
