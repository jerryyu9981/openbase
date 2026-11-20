/**
 * v1.5.0 DPS 后端能力接入测试（A6/A9/A10/A11/A14）
 *
 * 覆盖：新增 API 封装的方法、路径与参数透传；CSV 导出响应头解析。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

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

const ok = (data: unknown) => ({ data: { code: 200, message: 'success', data } })

beforeEach(() => {
  mocks.get.mockReset()
  mocks.post.mockReset()
})

describe('v1.5.0 DPS 代理与导出 API', () => {
  it('listPortraits 透传 keyword / external_id', async () => {
    mocks.get.mockResolvedValue(ok({ items: [], total: 0 }))
    await dpsApi.listPortraits({ page: 2, page_size: 50, keyword: '张', external_id: 'ext-1' })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/portraits', {
      params: { page: 2, page_size: 50, keyword: '张', external_id: 'ext-1' },
    })
  })

  it('listTags 调用 /dps-proxy/tags 并透传筛选', async () => {
    mocks.get.mockResolvedValue(ok({ items: [], total: 0, page: 1, page_size: 20 }))
    const result = await dpsApi.listTags({ keyword: '在职', category_id: 'c1', page: 1, page_size: 20 })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/tags', {
      params: { keyword: '在职', category_id: 'c1', page: 1, page_size: 20 },
    })
    expect(result.total).toBe(0)
  })

  it('getAuditTimeline 调用 /dps-proxy/audit 并回显实体', async () => {
    mocks.get.mockResolvedValue(
      ok({ items: [], total: 0, page: 1, page_size: 20, entity_type: 'annotation', entity_id: 'a1' }),
    )
    const result = await dpsApi.getAuditTimeline({
      entity_type: 'annotation',
      entity_id: 'a1',
      order: 'asc',
    })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/audit', {
      params: { entity_type: 'annotation', entity_id: 'a1', order: 'asc' },
    })
    expect(result.entity_id).toBe('a1')
  })

  it('generatePersistedAnnotationCandidate 使用持久化端点', async () => {
    mocks.post.mockResolvedValue(
      ok({ batch_id: 'b1', candidate: { id: 'c1', upstream_annotation_id: 'up1' } }),
    )
    const result = await dpsApi.generatePersistedAnnotationCandidate({
      adapter_id: 'a1',
      text: '待标注文本',
      annotation_template: 't1',
    })
    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/annotation-candidates', {
      adapter_id: 'a1',
      text: '待标注文本',
      annotation_template: 't1',
    })
    expect(result.batch_id).toBe('b1')
  })

  it('getLatestAnnotationCandidates 空批次返回空集合', async () => {
    mocks.get.mockResolvedValue(ok({ batch_id: null, items: [], total: 0 }))
    const result = await dpsApi.getLatestAnnotationCandidates({ adapter_id: 'a1' })
    expect(result.items).toEqual([])
    expect(result.batch_id).toBeNull()
  })

  it('exportAnnotationsCsv 解析文件名与截断标记', async () => {
    mocks.get.mockResolvedValue({
      data: new Blob(['\ufeff"a"\r\n'], { type: 'text/csv' }),
      headers: {
        'content-disposition': 'attachment; filename="annotations-20261120120000.csv"',
        'x-export-truncated': 'true',
      },
    })
    const result = await dpsApi.exportAnnotationsCsv({ annotation_template: 't1' })
    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotations/export', {
      params: { annotation_template: 't1' },
      responseType: 'blob',
    })
    expect(result.filename).toBe('annotations-20261120120000.csv')
    expect(result.truncated).toBe(true)
  })
})
