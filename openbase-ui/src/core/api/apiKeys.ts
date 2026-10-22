/**
 * 服务级 API Key API（v1.9.1）：OpenBase `/api/v1/auth/api-keys`.
 *
 * 契约要点：
 * - 列表 `ApiKeyOut[]` **不回显明文**（`key` 仅创建响应返回一次）；
 * - 吊销端点为 `DELETE /auth/api-keys/{raw_key}`，以**明文 Key** 定位记录。
 *   因此列表行无法直接删除（没有 id），仅本次会话新建、且仍持有明文的 Key 可吊销。
 */
import { http } from '@/core/api/http'

export interface ApiKeyRecord {
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

  /** 吊销：需传入明文 Key（列表不提供 id） */
  async revoke(rawKey: string): Promise<void> {
    await http.delete(`/auth/api-keys/${encodeURIComponent(rawKey)}`)
  },
}

/** 系统范围可选项（与 PROXY_SYSTEMS 对齐，`*` 表示全部） */
export const API_KEY_SYSTEM_OPTIONS = ['*', 'openllm', 'openrag', 'openmemory', 'dps'] as const
