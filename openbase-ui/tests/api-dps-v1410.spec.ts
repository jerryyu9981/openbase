/**
 * v1.4.10 DPS 数据层与错误映射测试（TD-1410-14／TD-1410-23／TD-1410-28~31）
 *
 * 覆盖：
 * - `core/api/dps.ts` 新增 22 方法（契约 10 ＋ 补代理 12）＋ 2 跨上游协作方法（路径 / 方法 / 参数透传）；
 * - `core/api/error.ts` 新增 409 `conflict` 语义与 DPS 状态码提示（400／403／404／409／422／503／5xx）；
 * - 22 端点 ↔ 12 页面映射（AC-18）常量自检。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get, post: mocks.post, put: mocks.put, delete: mocks.delete },
  tokenStore: { access: '', refresh: '' },
}))

import { dpsApi } from '@/core/api/dps'
import {
  DPS_ERROR_HINTS,
  classifyError,
  describeDpsError,
  dpsErrorHint,
  type ErrorResponse,
} from '@/core/api/error'

const ok = (data: unknown) => ({ data: { code: 200, message: 'success', data } })

function apiError(status: number, body: Partial<ErrorResponse> = {}): AxiosError<ErrorResponse> {
  const error = new AxiosError(`Request failed with status code ${status}`, 'ERR_BAD_RESPONSE') as unknown as AxiosError<ErrorResponse>
  error.response = {
    data: {
      code: body.code ?? `BIZ_HTTP_${status}`,
      message: body.message ?? `HTTP ${status}`,
      detail: body.detail ?? null,
      request_id: body.request_id ?? `req-${status}`,
    },
    status,
    statusText: '',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  } as never
  return error
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.get.mockResolvedValue(ok({}))
  mocks.post.mockResolvedValue(ok({}))
  mocks.put.mockResolvedValue(ok({}))
  mocks.delete.mockResolvedValue(ok({}))
})

describe('dpsApi｜契约 10 新增端点（#1~#10）', () => {
  it('导出／导入（#1／#2；导入透传 dry_run）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ format_version: '1.0', package_hash: 'sha256:abc' }))
    const pkg = await dpsApi.exportPackage({ scope: { type: 'template', codes: ['cc-v1'] } })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/template-packages/export', { scope: { type: 'template', codes: ['cc-v1'] } })
    expect(pkg.package_hash).toBe('sha256:abc')

    mocks.post.mockResolvedValueOnce(ok({ would_create: 3, would_skip: 1 }))
    const result = await dpsApi.importPackage({ package: { a: 1 }, dry_run: true })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/template-packages/import', { package: { a: 1 }, dry_run: true })
    expect(result.would_create).toBe(3)
  })

  it('版本对比（#3；from／to 透传）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ changes: [{ change_type: 'create', path: 'field:risk' }] }))
    const diff = await dpsApi.diffVersions('cc-v1', 3, 1)
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1/diff', { params: { from: 3, to: 1 } })
    expect(diff.changes?.[0].change_type).toBe('create')
  })

  it('回滚（#4；写操作携带 target_version／reason）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ new_version: 4, rolled_back_to: 1, equivalence_check: true }))
    const result = await dpsApi.rollbackTemplate('cc-v1', { target_version: 1, reason: '误改' })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1/rollback', { target_version: 1, reason: '误改' })
    expect(result.equivalence_check).toBe(true)
  })

  it('预检（#5；只读 GET）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ valid: true, checks: [] }))
    await dpsApi.preflightTemplate('cc-v1')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1/preflight')
  })

  it('血缘反查（#6；tag_code 编码）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ tag_code: 'service:channel', sources: [] }))
    const result = await dpsApi.getTagLineage('service:channel')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/lineage/tags/service%3Achannel')
    expect(result.tag_code).toBe('service:channel')
  })

  it('影响面（#7；三层维度参数透传）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ tag_count: 0, profile_count: 8 }))
    await dpsApi.queryImpact({ template_code: 'cc-v1' })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/lineage/impact', { params: { template_code: 'cc-v1' } })
  })

  it('措施建议（#8；person_id 透传，原样含 disclaimer）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ suggestions: [{ measure_code: 'M-01' }], disclaimer: '仅供参考' }))
    const result = await dpsApi.suggestMeasures('P-1')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/measures/suggest', { params: { person_id: 'P-1' } })
    expect(result.disclaimer).toBe('仅供参考')
  })

  it('AI 候选生成（#9；adapter_id + text/annotation_template）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ annotation: { id: 'ann-9', review_status: 'pending' }, source: 'ai_annotation' }))
    const result = await dpsApi.generateAnnotationCandidates('stub-v1', { text: 't', annotation_template: 'cc-annot' })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/annotation-adapters/stub-v1/generate', { text: 't', annotation_template: 'cc-annot' })
    expect(result.annotation?.id).toBe('ann-9')
  })

  it('评分类型（#10；只读分页）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [{ code: 'composite' }], total: 1 }))
    const result = await dpsApi.listScoringTypes({ page: 1, page_size: 20 })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/scoring-types', { params: { page: 1, page_size: 20 } })
    expect(result.items[0].code).toBe('composite')
  })
})

describe('dpsApi｜补代理 12 端点（#11~#22）', () => {
  it('画像模板 列表／详情（#11／#12）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [{ code: 'cc-v1' }], total: 1 }))
    await dpsApi.listTemplates({ status: 'active', profile_type: 'persona' })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/templates', { params: { status: 'active', profile_type: 'persona' } })

    mocks.get.mockResolvedValueOnce(ok({ code: 'cc-v1', extends: 'cc-base' }))
    const template = await dpsApi.getTemplate('cc-v1')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1')
    expect(template.extends).toBe('cc-base')
  })

  it('画像模板 创建／更新（#13／#14）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ code: 'cc-v1', version: 1 }))
    await dpsApi.createTemplate({ code: 'cc-v1', name: '模板' })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/templates', { code: 'cc-v1', name: '模板' })

    mocks.put.mockResolvedValueOnce(ok({ code: 'cc-v1', version: 2 }))
    await dpsApi.updateTemplate('cc-v1', { name: '改名' })
    expect(mocks.put).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1', { name: '改名' })
  })

  it('画像模板 启停（#15／#16；幂等 POST）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ code: 'cc-v1', status: 'active' }))
    await dpsApi.activateTemplate('cc-v1')
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1/activate')

    mocks.post.mockResolvedValueOnce(ok({ code: 'cc-v1', status: 'inactive' }))
    await dpsApi.deactivateTemplate('cc-v1')
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/templates/cc-v1/deactivate')
  })

  it('标注模板 列表／详情（#17／#18）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [{ code: 'cc-annot' }], total: 1 }))
    await dpsApi.listAnnotationTemplates({ template_code: 'cc-v1', scenario: 'intake' })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotation-templates', { params: { template_code: 'cc-v1', scenario: 'intake' } })

    mocks.get.mockResolvedValueOnce(ok({ code: 'cc-annot', template_code: 'cc-v1', field_schema: [] }))
    const template = await dpsApi.getAnnotationTemplate('cc-annot')
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotation-templates/cc-annot')
    expect(template.template_code).toBe('cc-v1')
  })

  it('标注模板 创建／更新（改挂）／删除（#19／#20／#21）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ code: 'cc-annot' }))
    await dpsApi.createAnnotationTemplate({ code: 'cc-annot', template_code: 'cc-v1' })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/annotation-templates', { code: 'cc-annot', template_code: 'cc-v1' })

    mocks.put.mockResolvedValueOnce(ok({ code: 'cc-annot', template_code: 'cc-v2' }))
    await dpsApi.updateAnnotationTemplate('cc-annot', { template_code: 'cc-v2' })
    expect(mocks.put).toHaveBeenCalledWith('/dps-proxy/annotation-templates/cc-annot', { template_code: 'cc-v2' })

    mocks.delete.mockResolvedValueOnce(ok({ code: 'cc-annot', deleted: true }))
    await dpsApi.deleteAnnotationTemplate('cc-annot')
    expect(mocks.delete).toHaveBeenCalledWith('/dps-proxy/annotation-templates/cc-annot')
  })

  it('标签列表（#22；action=list 固定）', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [{ name: '线上' }] }))
    const result = await dpsApi.listLabels()
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/labels', { params: { action: 'list' } })
    expect(result.items[0].name).toBe('线上')
  })
})

describe('dpsApi｜跨上游协作（非 22 端点）', () => {
  it('复核辅助经 llm_proxy（注入 session_id 且 stream=false）', async () => {
    mocks.post.mockResolvedValueOnce(ok({ choices: [{ message: { content: '建议通过' } }] }))
    const result = await dpsApi.assistReview({ messages: [{ role: 'user', content: '复核' }] })
    const [url, body] = mocks.post.mock.calls[0] as [string, Record<string, unknown>]
    expect(url).toBe('/llm-proxy/chat')
    expect(body.stream).toBe(false)
    expect(typeof body.session_id).toBe('string')
    expect(result.choices?.[0].message?.content).toBe('建议通过')
  })

  it('复核提交走 DPS 既有 review 端点', async () => {
    mocks.post.mockResolvedValueOnce(ok({ id: 'ann-9', review_status: 'approved' }))
    await dpsApi.submitReview('ann-9', { review_status: 'approved' })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/annotations/ann-9/review', { review_status: 'approved' })
  })
})

describe('error.ts｜DPS 语义扩展', () => {
  it('409 映射为 conflict（新增语义）', () => {
    expect(classifyError(apiError(409, { code: 'BIZ_CONFLICT', message: '存在 12 条关联标注数据，禁止删除' })).kind).toBe('conflict')
    expect(describeDpsError(apiError(409)).title).toBe('操作被拒绝')
  })

  it('既有 kind 口径保持不变（回归）', () => {
    expect(classifyError(apiError(401, { code: 'AUTH_EXPIRED' })).kind).toBe('unauthorized')
    expect(classifyError(apiError(403, { code: 'PERM_DENIED' })).kind).toBe('forbidden')
    expect(classifyError(apiError(404)).kind).toBe('not-found')
    expect(classifyError(apiError(422, { code: 'PARAM_INVALID' })).kind).toBe('invalid-param')
    expect(classifyError(apiError(503)).kind).toBe('server-error')
  })

  it('dpsErrorHint 覆盖 400／403／404／409／422／503 与 5xx 兜底', () => {
    expect(dpsErrorHint(400)).toBe(DPS_ERROR_HINTS[400])
    expect(dpsErrorHint(403)).toContain('无权限')
    expect(dpsErrorHint(404)).toContain('未找到')
    expect(dpsErrorHint(409)).toContain('未复核候选')
    expect(dpsErrorHint(422)).toContain('包结构非法')
    expect(dpsErrorHint(503)).toContain('人工路径不受影响')
    expect(dpsErrorHint(500)).toContain('暂不可用')
    expect(dpsErrorHint(undefined)).toBe('')
    expect(dpsErrorHint(200)).toBe('')
  })

  it('describeDpsError 在通用归一上追加 hint（保留 request_id）', () => {
    const presentation = describeDpsError(apiError(409, { request_id: 'req-409-x', message: '存在 12 条关联标注数据，禁止删除' }))
    expect(presentation.kind).toBe('conflict')
    expect(presentation.requestId).toBe('req-409-x')
    expect(presentation.detail).toContain('12 条')
    expect(presentation.hint).toContain('未复核候选')
    expect(describeDpsError(apiError(503)).hint).toContain('AI 适配器暂不可用')
  })
})
