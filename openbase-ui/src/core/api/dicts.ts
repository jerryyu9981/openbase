/**
 * 数据字典 API（v1.5.0）：OpenBase `/api/v1/dicts`.
 *
 * 契约：
 * - 类型列表/创建 `GET|POST /dicts` → `{code, name}`；
 * - 字典项列表/创建 `GET|POST /dicts/{typeCode}/items` → `{id, label, value, sort_order}`；
 * - 删除字典项 `DELETE /dicts/items/{itemId}`；
 * - 删除类型 `DELETE /dicts/{typeCode}`（存在字典项 → 409；类型不存在 → 404）。
 */
import { http } from '@/core/api/http'

export interface DictType {
  code: string
  name: string
}

export interface DictItem {
  id: number
  label: string
  value: string
  sort_order: number
}

export interface DictTypeCreatePayload {
  code: string
  name: string
}

export interface DictItemCreatePayload {
  label: string
  value: string
  sort_order?: number
}

export const dictsApi = {
  async listTypes(): Promise<DictType[]> {
    const { data } = await http.get<DictType[]>('/dicts')
    return data
  },
  async createType(payload: DictTypeCreatePayload): Promise<DictType> {
    const { data } = await http.post<DictType>('/dicts', payload)
    return data
  },
  async listItems(typeCode: string): Promise<DictItem[]> {
    const { data } = await http.get<DictItem[]>(`/dicts/${encodeURIComponent(typeCode)}/items`)
    return data
  },
  async createItem(typeCode: string, payload: DictItemCreatePayload): Promise<DictItem> {
    const { data } = await http.post<DictItem>(`/dicts/${encodeURIComponent(typeCode)}/items`, {
      label: payload.label,
      value: payload.value,
      sort_order: payload.sort_order ?? 0,
    })
    return data
  },
  async removeItem(itemId: number): Promise<{ deleted: number }> {
    const { data } = await http.delete<{ deleted: number }>(`/dicts/items/${itemId}`)
    return data
  },
  async removeType(typeCode: string): Promise<{ code: string; deleted: boolean }> {
    const { data } = await http.delete<{ code: string; deleted: boolean }>(
      `/dicts/${encodeURIComponent(typeCode)}`,
    )
    return data
  },
}
