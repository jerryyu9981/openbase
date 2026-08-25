/**
 * api 层覆盖率补充测试（v1.2.0）：http 拦截器 / authApi 分支
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const requestInterceptor = { use: vi.fn() }
  const responseInterceptor = { use: vi.fn() }
  const mockPost = vi.fn()
  const mockGet = vi.fn()
  return { requestInterceptor, responseInterceptor, mockPost, mockGet }
})

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  const instance = Object.assign(vi.fn(), {
    interceptors: { request: mocks.requestInterceptor, response: mocks.responseInterceptor },
    get: mocks.mockGet,
    post: mocks.mockPost,
  })
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn(() => instance),
      post: mocks.mockPost, // refreshAccessToken 走全局 axios.post
      get: mocks.mockGet,
    },
  }
})

import { http, isApiError, tokenStore } from '@/core/api/http'
import { authApi, modulesApi } from '@/core/api/auth'
import { AxiosError } from 'axios'

describe('http 拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
    tokenStore.clear()
  })

  it('请求拦截器注入 Bearer token', () => {
    tokenStore.set('access-abc')
    const [onFulfilled] = mocks.requestInterceptor.use.mock.calls[0]
    const config = { headers: {} }
    const result = onFulfilled(config)
    expect(result.headers.Authorization).toBe('Bearer access-abc')
  })

  it('请求拦截器无 token 时不注入', () => {
    const [onFulfilled] = mocks.requestInterceptor.use.mock.calls[0]
    const result = onFulfilled({ headers: {} })
    expect(result.headers.Authorization).toBeUndefined()
  })

  it('响应拦截器 401 无 refresh 时直接拒绝', () => {
    const [, onRejected] = mocks.responseInterceptor.use.mock.calls[0]
    const error = { response: { status: 401, data: { message: 'unauthorized' } }, config: { headers: {} }, message: 'err' }
    return onRejected(error).catch((e: unknown) => {
      expect(e).toBe(error)
    })
  })

  it('响应拦截器 401 有 refresh 时触发刷新', async () => {
    tokenStore.set('old-access', 'refresh-token')
    mocks.mockPost.mockResolvedValue({
      data: { code: 0, message: 'ok', data: { access_token: 'new-access' } },
    })
    const [, onRejected] = mocks.responseInterceptor.use.mock.calls[0]
    const error = {
      response: { status: 401, data: { message: 'expired' } },
      config: { headers: {}, _retry: false },
      message: 'err',
    }
    await onRejected(error)
    expect(mocks.mockPost).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      { refresh_token: 'refresh-token' },
    )
    expect(tokenStore.access).toBe('new-access')
    tokenStore.clear()
  })

  it('authApi.login 成功后写入 token', async () => {
    // 后端登录返回扁平 TokenResponse，随后 me() 拉取用户
    mocks.mockPost.mockResolvedValue({
      data: { access_token: 'a1', refresh_token: 'r1', expires_in: 3600 },
    })
    mocks.mockGet.mockResolvedValue({ data: { id: 1, username: 'admin', permissions: ['*'] } })
    const user = await authApi.login('admin', 'admin123')
    expect(user.username).toBe('admin')
    expect(tokenStore.access).toBe('a1')
    expect(tokenStore.refresh).toBe('r1')
  })

  it('authApi.me 返回用户信息', async () => {
    tokenStore.set('token-x')
    mocks.mockGet.mockResolvedValue({ data: { id: 2, username: 'alice', permissions: [] } })
    const user = await authApi.me()
    expect(user.username).toBe('alice')
  })

  it('modulesApi.list 返回模块清单', async () => {
    tokenStore.set('token-x')
    mocks.mockGet.mockResolvedValue({
      data: { code: 0, message: 'ok', data: { items: [{ id: 'memory' }], total: 1 } },
    })
    const items = await modulesApi.list()
    expect(items.length).toBe(1)
    expect(items[0].id).toBe('memory')
  })

  it('isApiError 识别 axios 错误', () => {
    const axiosError = new AxiosError('network', AxiosError.ERR_NETWORK)
    expect(isApiError(axiosError)).toBe(true)
    expect(isApiError(new Error('普通错误'))).toBe(false)
  })
})

describe('http 实例导出', () => {
  it('http 为 axios 实例（create 已调用）', () => {
    expect(http).toBeDefined()
  })
})
