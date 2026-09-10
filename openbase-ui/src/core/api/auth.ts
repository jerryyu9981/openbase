/**
 * 认证与模块 API（对齐后端 openapi 契约，类型由 openapi-typescript 生成后可替换）
 */
import { http, tokenStore, type ApiSuccess } from './http'

export interface AuthUser {
  id: number
  username: string
  tenant_id?: string
  permissions: string[]
}

export interface ModuleInfo {
  id: string
  name: string
  icon?: string
  route_prefix: string
  entry: string
  permission: string
  status: 'enabled' | 'disabled'
  sort_order: number
}

/** 解析 OIDC 回调 URL fragment（#access_token=..&refresh_token=..），v1.6.0 */
export function parseOidcHash(hash: string): { access_token: string; refresh_token?: string } {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash
  const params = new URLSearchParams(raw)
  const access_token = params.get('access_token') || ''
  const refresh_token = params.get('refresh_token') || undefined
  return { access_token, refresh_token }
}

/**
 * 解析 OIDC 回调 fragment 中的错误参数（IdP 拒绝 / state 校验失败，v1.6.0）。
 * 返回空串表示无错误参数，调用方按「缺少令牌」兜底提示。
 */
export function parseOidcError(hash: string): { error: string; error_description: string } {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash
  const params = new URLSearchParams(raw)
  return {
    error: params.get('error') || '',
    error_description: params.get('error_description') || '',
  }
}

export const authApi = {
  async login(username: string, password: string): Promise<AuthUser> {
    // 后端登录返回扁平 TokenResponse（v1.1.0 既有契约）
    const { data } = await http.post<{ access_token: string; refresh_token: string }>('/auth/login', {
      username,
      password,
    })
    tokenStore.set(data.access_token, data.refresh_token)
    return this.me()
  },
  async me(): Promise<AuthUser> {
    // 后端 /auth/me 返回扁平 MeResponse
    const { data } = await http.get<AuthUser>('/auth/me')
    return data
  },
}

export const modulesApi = {
  async list(): Promise<ModuleInfo[]> {
    const { data } = await http.get<ApiSuccess<{ items: ModuleInfo[]; total: number }>>('/modules')
    return data.data.items
  },
}
