/**
 * 开发代理契约（v7.8.0）：后端未就绪时，`/api` 代理必须返回 503 + JSON，
 * 而不是 http-proxy 默认的空 500，避免把「上游未启动」误判为服务端 5xx。
 */
import { describe, expect, it, vi } from 'vitest'
import {
  handleDevProxyError,
  UPSTREAM_UNAVAILABLE_CODE,
  UPSTREAM_UNAVAILABLE_MESSAGE,
} from '@/core/api/devProxy'

function makeResponse(overrides: Record<string, unknown> = {}) {
  return {
    headersSent: false,
    writableEnded: false,
    writeHead: vi.fn(),
    end: vi.fn(),
    ...overrides,
  }
}

describe('v7.8.0 开发代理上游不可达语义', () => {
  it('上游连接失败映射为 503 + SYS_UPSTREAM_UNAVAILABLE', () => {
    const response = makeResponse()

    handleDevProxyError(new Error('connect ECONNREFUSED 127.0.0.1:8000'), {}, response)

    expect(response.writeHead).toHaveBeenCalledWith(503, {
      'Content-Type': 'application/json; charset=utf-8',
    })
    expect(response.end).toHaveBeenCalledTimes(1)
    const body = JSON.parse(String(response.end.mock.calls[0][0]))
    expect(body.code).toBe(UPSTREAM_UNAVAILABLE_CODE)
    expect(body.message).toBe(UPSTREAM_UNAVAILABLE_MESSAGE)
    expect(body.data).toBeNull()
  })

  it('响应头已发送时不重复 writeHead，仅收尾响应体', () => {
    const response = makeResponse({ headersSent: true })

    handleDevProxyError(new Error('socket hang up'), {}, response)

    expect(response.writeHead).not.toHaveBeenCalled()
    expect(response.end).toHaveBeenCalledTimes(1)
  })

  it('响应已结束时不重复写入', () => {
    const response = makeResponse({ writableEnded: true })

    handleDevProxyError(new Error('boom'), {}, response)

    expect(response.end).not.toHaveBeenCalled()
  })

  it('非 ServerResponse（socket）时安全跳过', () => {
    expect(() => handleDevProxyError(new Error('boom'), {}, undefined)).not.toThrow()
  })
})
