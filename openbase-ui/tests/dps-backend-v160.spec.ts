/**
 * v1.6.0 A4 标注详情接入测试
 *
 * 覆盖：API 封装路径（编码）、详情包络透传、审核人/意见字段可读。
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
})

describe('v1.6.0 A4 标注详情 API', () => {
  it('getAnnotationDetail 调用详情端点并编码路径', async () => {
    mocks.get.mockResolvedValue(
      ok({
        annotation: {
          id: 'a/1',
          person_id: 'PERSON0000001',
          fields: { behavior: '良好' },
          evidence_source: 'WS-1',
          reviewer_id: 'u2',
          review_comment: '证据充分',
          structured: true,
        },
      }),
    )

    const result = await dpsApi.getAnnotationDetail('a/1')

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotations/a%2F1')
    expect(result.annotation.id).toBe('a/1')
    expect(result.annotation.fields).toEqual({ behavior: '良好' })
    expect(result.annotation.reviewer_id).toBe('u2')
    expect(result.annotation.review_comment).toBe('证据充分')
    expect(result.annotation.structured).toBe(true)
  })
})
