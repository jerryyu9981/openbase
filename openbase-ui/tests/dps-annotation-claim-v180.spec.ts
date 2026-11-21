/**
 * v1.8.0 A2：审核人视角与领取（前端契约）
 *
 * 覆盖：队列查询透传 reviewer=me / level；claimAnnotation 命中
 * ``POST /dps-proxy/annotations/{id}/claim``（幂等结果原样返回）。
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
  vi.clearAllMocks()
})

describe('A2 审核人视角与领取', () => {
  it('队列查询透传 reviewer=me 与级数', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [], total: 0, page: 1, page_size: 20 }))

    await dpsApi.listAnnotations({ reviewer: 'me', level: 2, review_status: 'pending' })

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotations', {
      params: { reviewer: 'me', level: 2, review_status: 'pending' },
    })
  })

  it('领取调用 POST claim，路径编码且返回幂等结果', async () => {
    mocks.post.mockResolvedValueOnce(
      ok({ annotation_id: 'ann-1', reviewer: 'u9', claimed: true, already: false }),
    )

    const result = await dpsApi.claimAnnotation('ann-1')

    expect(mocks.post).toHaveBeenCalledWith('/dps-proxy/annotations/ann-1/claim', {})
    expect(result).toEqual({ annotation_id: 'ann-1', reviewer: 'u9', claimed: true, already: false })
  })

  it('重复领取返回 already=true（前端据此提示）', async () => {
    mocks.post.mockResolvedValueOnce(
      ok({ annotation_id: 'ann-1', reviewer: 'u9', claimed: true, already: true }),
    )

    const result = await dpsApi.claimAnnotation('ann-1')

    expect(result.already).toBe(true)
  })
})
