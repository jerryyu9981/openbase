/**
 * v1.8.0 A7：模板列表服务端筛选（前端契约）
 *
 * 覆盖：listTemplates 将 keyword/category_id/template_kind/status 原样传给代理，
 * 由 DPS ≥2.16.0 执行服务端筛选（前端不再本地过滤）。
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
  mocks.get.mockResolvedValue(ok({ items: [], total: 0 }))
})

describe('A7 模板服务端筛选', () => {
  it('四个筛选参数原样透传（不再由前端过滤）', async () => {
    await dpsApi.listTemplates({
      status: 'active',
      keyword: 'risk',
      category_id: 'cat-1',
      template_kind: 'component',
    })

    expect(mocks.get).toHaveBeenCalledWith('/dps-proxy/templates', {
      params: {
        status: 'active',
        keyword: 'risk',
        category_id: 'cat-1',
        template_kind: 'component',
      },
    })
  })

  it('未选择筛选时不传空值参数', async () => {
    await dpsApi.listTemplates({ status: undefined, keyword: undefined })

    const [, config] = mocks.get.mock.calls[0]
    expect(config.params).toEqual({ status: undefined, keyword: undefined })
  })

  it('返回值结构保持 items/total', async () => {
    mocks.get.mockResolvedValueOnce(ok({ items: [{ code: 'cc-1', name: '模板' }], total: 1 }))

    const result = await dpsApi.listTemplates({ keyword: 'cc' })

    expect(result.total).toBe(1)
    expect(result.items?.[0]?.code).toBe('cc-1')
  })
})
