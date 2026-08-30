/**
 * 网关 API 封装测试（v1.4.0）：gatewayApi 各方法契约
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const get = vi.fn()
  const post = vi.fn()
  const del = vi.fn()
  return { get, post, del }
})

vi.mock('@/core/api/http', () => ({
  http: {
    get: mocks.get,
    post: mocks.post,
    delete: mocks.del,
  },
}))

import { gatewayApi } from '@/core/api/gateway'

describe('gatewayApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listAllServices 调用 GET /services 并返回 systems', async () => {
    mocks.get.mockResolvedValue({
      data: {
        code: 0,
        data: {
          systems: [
            { system: 'openllm', instances: [{ system: 'openllm', instance_id: 'h:8001', host: 'h', port: 8001, weight: 1, healthy: true, last_heartbeat: 0, consecutive_failures: 0, meta: {} }] },
          ],
        },
      },
    })
    const result = await gatewayApi.listAllServices()
    expect(mocks.get).toHaveBeenCalledWith('/services')
    expect(result.systems).toHaveLength(1)
    expect(result.systems[0].system).toBe('openllm')
  })

  it('registerService 调用 POST /services 并返回实例', async () => {
    mocks.post.mockResolvedValue({
      data: {
        code: 0,
        data: { system: 'openllm', instance_id: '10.0.0.5:8001', host: '10.0.0.5', port: 8001, weight: 2, healthy: true, last_heartbeat: 0, consecutive_failures: 0, meta: {} },
      },
    })
    const result = await gatewayApi.registerService({ system: 'openllm', host: '10.0.0.5', port: 8001, weight: 2 })
    expect(mocks.post).toHaveBeenCalledWith('/services', expect.objectContaining({ system: 'openllm' }))
    expect(result.instance_id).toBe('10.0.0.5:8001')
  })

  it('deregisterService 调用 DELETE /services/{system}/{instanceId}', async () => {
    mocks.del.mockResolvedValue({ data: { code: 0, data: { deleted: 'h:8001' } } })
    const result = await gatewayApi.deregisterService('openllm', 'h:8001')
    expect(mocks.del).toHaveBeenCalledWith('/services/openllm/h:8001')
    expect(result.deleted).toBe('h:8001')
  })

  it('health 调用 GET /gateway/health', async () => {
    mocks.get.mockResolvedValue({
      data: { code: 0, data: { systems: [{ system: 'openllm', healthy: true, instance_count: 1, health_rate: 1.0 }] } },
    })
    const result = await gatewayApi.health()
    expect(mocks.get).toHaveBeenCalledWith('/gateway/health')
    expect(result.systems[0].health_rate).toBe(1.0)
  })

  it('ping 调用 GET /gateway/ping', async () => {
    mocks.get.mockResolvedValue({
      data: { code: 0, data: { results: [{ system: 'openllm', reachable: false, latency_ms: null }] } },
    })
    const result = await gatewayApi.ping()
    expect(mocks.get).toHaveBeenCalledWith('/gateway/ping')
    expect(result.results[0].reachable).toBe(false)
  })

  it('aggregate 调用 POST /gateway/aggregate 并返回结果与错误', async () => {
    mocks.post.mockResolvedValue({
      data: { code: 0, data: { result: { model_total: 42 }, errors: [] } },
    })
    const result = await gatewayApi.aggregate({
      steps: [{ id: 'models', system: 'openllm', path: '/models' }],
      mapping: { model_total: '${models.data.total}' },
    })
    expect(mocks.post).toHaveBeenCalledWith('/gateway/aggregate', expect.objectContaining({ steps: expect.any(Array) }))
    expect(result.result.model_total).toBe(42)
  })
})
