/**
 * 身份 Agent API（v1.5.0）：OpenBase `/api/v1/identity/agents`.
 *
 * 契约（权限：列表 `identity:view`，写操作 `identity:manage`）：
 * - `GET /identity/agents` → `AgentItem[]`（分页参数 page/page_size，含已软删记录）；
 * - `POST /identity/agents` → 含 `api_key.raw_key`（明文仅返回一次）；
 * - `DELETE /identity/agents/{agentId}` → 软删（status=0 / suspended）并级联吊销有效密钥；
 * - `GET|POST /identity/agents/{agentId}/keys`、`DELETE /identity/agents/{agentId}/keys/{keyId}`。
 */
import { http } from '@/core/api/http'

export interface AgentItem {
  id: number
  username: string
  display_name: string
  subject_type: string
  status: number
  status_state: string
  tenant_id: number | null
  tenant_code: string | null
  created_at: string | null
}

export interface AgentKey {
  id: number
  agent_id: number
  name: string | null
  key_prefix: string
  key_suffix: string | null
  status: string
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  raw_key?: string | null
}

export interface AgentCreatePayload {
  username: string
  display_name: string
  tenant_id?: number
  role?: string
  key_name?: string
}

export interface AgentCreated {
  agent_id: number
  username: string
  display_name: string
  subject_type: string
  credential_type: string
  status_state: string
  tenant_id: number | null
  tenant_code: string | null
  roles: string[]
  api_key: AgentKey
}

export interface AgentRemoved {
  code: number
  agent_id: number
  status: number
  revoked_keys: number
}

export interface AgentKeyCreatePayload {
  name?: string
  expires_at?: string
}

export const agentsApi = {
  async list(params: { page?: number; page_size?: number } = {}): Promise<AgentItem[]> {
    const { data } = await http.get<AgentItem[]>('/identity/agents', { params })
    return data
  },
  async create(payload: AgentCreatePayload): Promise<AgentCreated> {
    const { data } = await http.post<AgentCreated>('/identity/agents', payload)
    return data
  },
  async remove(agentId: number): Promise<AgentRemoved> {
    const { data } = await http.delete<AgentRemoved>(`/identity/agents/${agentId}`)
    return data
  },
  async listKeys(agentId: number): Promise<AgentKey[]> {
    const { data } = await http.get<AgentKey[]>(`/identity/agents/${agentId}/keys`)
    return data
  },
  async issueKey(agentId: number, payload: AgentKeyCreatePayload = {}): Promise<AgentKey> {
    const { data } = await http.post<AgentKey>(`/identity/agents/${agentId}/keys`, payload)
    return data
  },
  async revokeKey(
    agentId: number,
    keyId: number,
  ): Promise<{ revoked: boolean; agent_id: number; key_id: number }> {
    const { data } = await http.delete<{ revoked: boolean; agent_id: number; key_id: number }>(
      `/identity/agents/${agentId}/keys/${keyId}`,
    )
    return data
  },
}
