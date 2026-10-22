/**
 * 用户管理 API（v1.9.1）：OpenBase `/api/v1/users`.
 *
 * 契约：后端 `response_model=list[UserOut]` 直接返回数组（非统一信封）。
 * 状态为 `0/1`；角色为 `roles[]`，分配角色走独立端点 `PUT /users/{id}/role`。
 */
import { http } from '@/core/api/http'

export interface PlatformUser {
  id: number
  username: string
  display_name: string
  email: string | null
  phone: string | null
  status: number
  tenant_id: number | null
  roles: string[]
}

export interface UserCreatePayload {
  username: string
  password: string
  display_name: string
  email?: string
  role: string
  tenant_id?: number | null
}

export const usersApi = {
  async list(): Promise<PlatformUser[]> {
    const { data } = await http.get<PlatformUser[]>('/users')
    return data
  },
  async create(payload: UserCreatePayload): Promise<PlatformUser> {
    const { data } = await http.post<PlatformUser>('/users', payload)
    return data
  },
  async update(userId: number, payload: { status?: number; display_name?: string; email?: string }): Promise<PlatformUser> {
    const { data } = await http.put<PlatformUser>(`/users/${userId}`, payload)
    return data
  },
  async assignRole(userId: number, role: string): Promise<PlatformUser> {
    const { data } = await http.put<PlatformUser>(`/users/${userId}/role`, { role })
    return data
  },
  async remove(userId: number): Promise<void> {
    await http.delete(`/users/${userId}`)
  },
}

/** 标准角色码（与 config/role_tier_anchors.json 五码集合一致） */
export const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'org_admin', label: '组织管理员' },
  { value: 'org_member', label: '组织成员' },
  { value: 'user', label: '只读用户' },
  { value: 'viewer', label: '访客（只读）' },
] as const

export function roleLabel(role: string): string {
  return ROLE_OPTIONS.find((item) => item.value === role)?.label ?? role
}

export function roleTagType(role: string): 'danger' | 'warning' | 'success' | 'info' {
  if (role === 'admin') return 'danger'
  if (role === 'org_admin') return 'warning'
  if (role === 'org_member') return 'success'
  return 'info'
}
