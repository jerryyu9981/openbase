/**
 * 配置中心 API（v1.9.2）：OpenBase `/api/v1/configs`.
 *
 * 契约：列表 `{items, total}`；单条读取/写入为 `{key, value, level}`；
 * 版本历史 `[{key, version, value}]`；回滚 `POST /configs/{key}/rollback?version=n`；
 * 删除 `DELETE /configs/{key}`（移除覆盖值并回退默认值，版本历史保留）。
 */
import { http } from '@/core/api/http'

export type ConfigLevel = 'system' | 'tenant' | 'user'

export interface ConfigItem {
  key: string
  value: unknown
  level: ConfigLevel
}

export interface ConfigVersion {
  key: string
  version: number
  value: unknown
}

export const configsApi = {
  async list(params: { prefix?: string; level?: string } = {}): Promise<{ items: ConfigItem[]; total: number }> {
    const { data } = await http.get<{ items: ConfigItem[]; total: number }>('/configs', { params })
    return data
  },
  async set(key: string, value: unknown, level: ConfigLevel = 'system'): Promise<ConfigItem> {
    const { data } = await http.post<ConfigItem>('/configs', { key, value, level })
    return data
  },
  async versions(key: string): Promise<ConfigVersion[]> {
    const { data } = await http.get<ConfigVersion[]>(`/configs/${encodeURIComponent(key)}/versions`)
    return data
  },
  async rollback(key: string, version: number): Promise<ConfigItem> {
    const { data } = await http.post<ConfigItem>(`/configs/${encodeURIComponent(key)}/rollback`, null, {
      params: { version },
    })
    return data
  },
  async remove(key: string): Promise<{ deleted: boolean; restored_default: boolean }> {
    const { data } = await http.delete<{ deleted: boolean; restored_default: boolean }>(
      `/configs/${encodeURIComponent(key)}`,
    )
    return data
  },
}
