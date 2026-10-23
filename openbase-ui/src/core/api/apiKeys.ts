/**
 * 服务级 API Key API（v1.9.2）：OpenBase `/api/v1/auth/api-keys`.
 *
 * 契约要点：
 * - 列表 `ApiKeyOut[]` **不回显明文**（`key` 仅创建响应返回一次）；
 * - v1.9.2 起每条记录带稳定 `id`，吊销走 `DELETE /auth/api-keys/by-id/{id}`，
 *   前端无需持有明文；原「按明文 Key」端点保留以兼容既有调用方。
 */
import { http } from '@/core/api/http'

export interface ApiKeyRecord {
  id: string
  name: string
  scope: { system?: string[]; tenants?: string[] }
  description: string
  /** 创建时间（Unix 秒） */
  created: number
  revoked: boolean
  /** 明文 Key：仅创建响应返回 */
  key?: string
}

export interface ApiKeyCreatePayload {
  name: string
  scope: { system: string[]; tenants: string[] }
  description?: string
}

export const apiKeysApi = {
  async list(): Promise<ApiKeyRecord[]> {
    const { data } = await http.get<ApiKeyRecord[]>('/auth/api-keys')
    return data
  },

  async create(payload: ApiKeyCreatePayload): Promise<ApiKeyRecord> {
    const { data } = await http.post<ApiKeyRecord>('/auth/api-keys', {
      name: payload.name,
      scope: payload.scope,
      description: payload.description ?? '',
    })
    return data
  },

  /** 按稳定标识吊销（列表已回显 id，无需明文） */
  async revokeById(keyId: string): Promise<void> {
    await http.delete(`/auth/api-keys/by-id/${encodeURIComponent(keyId)}`)
  },

  /** 按明文 Key 吊销（兼容既有调用方） */
  async revoke(rawKey: string): Promise<void> {
    await http.delete(`/auth/api-keys/${encodeURIComponent(rawKey)}`)
  },
}

/** 系统范围可选项（与 PROXY_SYSTEMS 对齐，`*` 表示全部） */
export const API_KEY_SYSTEM_OPTIONS = ['*', 'openllm', 'openrag', 'openmemory', 'dps'] as const
