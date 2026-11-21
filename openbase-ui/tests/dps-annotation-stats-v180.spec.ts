/**
 * v1.8.0 A1：标注队列聚合统计（前端契约）
 *
 * 覆盖：getAnnotationStats 命中代理静态段 ``/annotations/stats``（不被详情动态段吞掉），
 * group_by 与模板过滤原样透传。
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

describe('A1 标注队列统计', () => {
  it('请求静态段 /annotations/stats 并透传分组', async () => {
    const payload = {
      group_by: 'status',
      total: 3,
      items: [
        { key: 'pending', label: '待审核', count: 2 },
        { key: 'approved', label: '已通过', count: 1 },
      ],
      degraded: false,
    }
    mocks.get.mockResolvedValueOnce(ok(payload))

    const result = await dpsApi.getAnnotationStats({
      group_by: 'status',
      annotation_template: 'ann-1',
    })

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotations/stats', {
      params: { group_by: 'status', annotation_template: 'ann-1' },
    })
    expect(result.items[0]).toEqual({ key: 'pending', label: '待审核', count: 2 })
    expect(result.total).toBe(3)
  })

  it('默认无参数时仍请求统计端点', async () => {
    mocks.get.mockResolvedValueOnce(ok({ group_by: 'status', total: 0, items: [] }))

    await dpsApi.getAnnotationStats()

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/annotations/stats', { params: {} })
  })
})
