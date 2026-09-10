/**
 * api 层覆盖率补充测试（v1.2.0）：http 拦截器 / authApi 分支
 *
 * S6-T4 同步（R-7 口径）：401 由整页 `window.location.href` 改为 SPA 收敛
 * `/auth/login?redirect=<站内路径>`，既有断言按新语义更新，并补齐
 * 单飞刷新上限、403 无弹窗/不清态、无 refresh 收敛等边界。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const requestInterceptor = { use: vi.fn() }
  const responseInterceptor = { use: vi.fn() }
  const mockPost = vi.fn()
  const mockGet = vi.fn()
  const instance = Object.assign(vi.fn(), {
    interceptors: { request: requestInterceptor, response: responseInterceptor },
    get: mockGet,
    post: mockPost,
  })
  return { requestInterceptor, responseInterceptor, mockPost, mockGet, instance }
})

const elMessage = vi.hoisted(() => ({ error: vi.fn(), info: vi.fn() }))

vi.mock('element-plus', () => ({ ElMessage: elMessage }))

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn(() => mocks.instance),
      post: mocks.mockPost, // refreshAccessToken 走全局 axios.post
      get: mocks.mockGet,
    },
  }
})

import { http, isApiError, tokenStore, type ErrorResponse } from '@/core/api/http'
import { authApi, modulesApi } from '@/core/api/auth'
import { LOGIN_PATH, registerLoginNavigator, type LoginNavigateTarget } from '@/core/api/redirect'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'

let loginNavigator: ReturnType<typeof vi.fn>

/** 构造真实 AxiosError（携带 ErrorResponse 契约体），供分类断言使用 */
function apiError(status: number, body: Partial<ErrorResponse> = {}, url = '/dps/portraits'): AxiosError<ErrorResponse> {
  const error = new AxiosError(
    `Request failed with status code ${status}`,
    'ERR_BAD_RESPONSE',
  ) as unknown as AxiosError<ErrorResponse>
  error.response = {
    data: {
      code: body.code ?? `SYS_HTTP_${status}`,
      message: body.message ?? `HTTP ${status}`,
      detail: body.detail ?? null,
      request_id: body.request_id ?? `req-${status}`,
    },
    status,
    statusText: '',
    headers: {},
    config: { headers: {}, url } as InternalAxiosRequestConfig,
  } as never
  error.config = { headers: {}, url } as never
  return error
}

function responseRejectHandler(): (error: unknown) => Promise<unknown> {
  const [, onRejected] = mocks.responseInterceptor.use.mock.calls[0]
  return onRejected as (error: unknown) => Promise<unknown>
}

describe('http 拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
    tokenStore.clear()
    elMessage.error.mockClear()
    elMessage.info.mockClear()
    mocks.mockPost.mockReset()
    mocks.mockGet.mockReset()
    mocks.instance.mockReset()
    loginNavigator = vi.fn()
    registerLoginNavigator(loginNavigator as unknown as (target: LoginNavigateTarget) => void)
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

  it('401 无 refresh 凭证 → 收敛登录（SPA 站内 redirect），不触发刷新', async () => {
    tokenStore.set('stale-access')
    const onRejected = responseRejectHandler()
    const error = apiError(401, { code: 'AUTH_EXPIRED', message: 'expired' })
    await expect(onRejected(error)).rejects.toBe(error)
    expect(mocks.mockPost).not.toHaveBeenCalled()
    expect(tokenStore.access).toBe('')
    expect((error as { bizKind?: string }).bizKind).toBe('unauthorized')
    expect(loginNavigator).toHaveBeenCalledTimes(1)
    const target = loginNavigator.mock.calls[0][0] as LoginNavigateTarget
    expect(target.path).toBe(LOGIN_PATH)
    expect(target.query.redirect.startsWith('/')).toBe(true)
    expect(target.query.redirect.startsWith('//')).toBe(false)
  })

  it('401 有 refresh 时触发刷新并重放原请求', async () => {
    tokenStore.set('old-access', 'refresh-token')
    mocks.mockPost.mockResolvedValue({
      data: { code: 0, message: 'ok', data: { access_token: 'new-access' } },
    })
    const onRejected = responseRejectHandler()
    const error = apiError(401, { code: 'AUTH_EXPIRED', message: 'expired' })
    await onRejected(error)
    expect(mocks.mockPost).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      { refresh_token: 'refresh-token' },
    )
    expect(tokenStore.access).toBe('new-access')
    expect(mocks.instance).toHaveBeenCalledTimes(1)
    expect(loginNavigator).not.toHaveBeenCalled()
    tokenStore.clear()
  })

  it('并发 3 个 401 → 单飞刷新仅 1 次，原请求各重放 1 次（无刷新风暴）', async () => {
    tokenStore.set('old-access', 'refresh-token')
    let releaseRefresh: (() => void) | null = null
    mocks.mockPost.mockImplementation(
      () =>
        new Promise((resolve) => {
          releaseRefresh = () =>
            resolve({ data: { code: 0, message: 'ok', data: { access_token: 'new-access' } } })
        }),
    )
    const onRejected = responseRejectHandler()
    const errors = [0, 1, 2].map(() => apiError(401, { code: 'AUTH_EXPIRED' }))
    const pending = errors.map((error) => onRejected(error))
    expect(mocks.mockPost).toHaveBeenCalledTimes(1)
    expect(releaseRefresh).not.toBeNull()
    ;(releaseRefresh as unknown as () => void)()
    await Promise.all(pending)
    expect(mocks.mockPost).toHaveBeenCalledTimes(1)
    expect(mocks.instance).toHaveBeenCalledTimes(3)
    expect(tokenStore.access).toBe('new-access')
    expect(loginNavigator).not.toHaveBeenCalled()
  })

  it('刷新失败（网络/超时）→ 清态 + 收敛登录，不循环', async () => {
    tokenStore.set('old-access', 'refresh-token')
    mocks.mockPost.mockRejectedValue(new AxiosError('timeout of 15000ms exceeded', 'ECONNABORTED'))
    const onRejected = responseRejectHandler()
    const error = apiError(401, { code: 'AUTH_EXPIRED' })
    await expect(onRejected(error)).rejects.toBe(error)
    expect(tokenStore.access).toBe('')
    expect(loginNavigator).toHaveBeenCalledTimes(1)
    expect((loginNavigator.mock.calls[0][0] as LoginNavigateTarget).path).toBe(LOGIN_PATH)
  })

  it('刷新成功但重放仍 401（_retry 已置位）→ 不再刷新，收敛登录（防无限循环）', async () => {
    tokenStore.set('old-access', 'refresh-token')
    const onRejected = responseRejectHandler()
    const error = apiError(401, { code: 'AUTH_EXPIRED' })
    error.config = { headers: {}, url: '/dps/portraits', _retry: true } as never
    await expect(onRejected(error)).rejects.toBe(error)
    expect(mocks.mockPost).not.toHaveBeenCalled()
    expect(loginNavigator).toHaveBeenCalledTimes(1)
    const target = loginNavigator.mock.calls[0][0] as LoginNavigateTarget
    expect(target.path).toBe(LOGIN_PATH)
    expect(target.query.redirect.startsWith('/')).toBe(true)
    expect(target.query.redirect.startsWith('//')).toBe(false)
  })

  it('403 → 页面级 forbidden：不刷新、不弹全局 toast、不清空本地登录态', async () => {
    tokenStore.set('access-keep', 'refresh-keep')
    const onRejected = responseRejectHandler()
    const error = apiError(403, { code: 'PERM_DENIED', message: '无权访问他域数据', request_id: 'req-403' })
    await expect(onRejected(error)).rejects.toBe(error)
    expect((error as { bizKind?: string }).bizKind).toBe('forbidden')
    expect(mocks.mockPost).not.toHaveBeenCalled()
    expect(mocks.instance).not.toHaveBeenCalled()
    expect(elMessage.error).not.toHaveBeenCalled()
    expect(tokenStore.access).toBe('access-keep')
    expect(tokenStore.refresh).toBe('refresh-keep')
    expect(loginNavigator).not.toHaveBeenCalled()
  })

  it('登录接口自身 401（密码错误）→ 不回跳、不刷新，避免登录页抖动', async () => {
    tokenStore.set('old-access', 'refresh-token')
    const onRejected = responseRejectHandler()
    const error = apiError(401, { code: 'AUTH_BAD_CREDENTIALS', message: '用户名或密码错误' }, '/auth/login')
    await expect(onRejected(error)).rejects.toBe(error)
    expect(loginNavigator).not.toHaveBeenCalled()
    expect(mocks.mockPost).not.toHaveBeenCalled()
    expect(tokenStore.access).toBe('old-access')
  })

  it('响应拦截器对取消类错误（ERR_CANCELED）直接透传且不弹全局错误', async () => {
    const onRejected = responseRejectHandler()
    const cancelError = { __CANCEL__: true, message: 'canceled', config: { headers: {} } }
    await expect(onRejected(cancelError)).rejects.toBe(cancelError)
    expect(elMessage.error).not.toHaveBeenCalled()
  })

  it('响应拦截器对非取消类失败仍弹全局错误并透传', async () => {
    const onRejected = responseRejectHandler()
    const error = { message: 'network down', config: { headers: {} } }
    await expect(onRejected(error)).rejects.toBe(error)
    expect(elMessage.error).toHaveBeenCalledWith('network down')
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
