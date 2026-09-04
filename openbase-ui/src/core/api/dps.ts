/**
 * DPS dps-proxy API 封装（v1.4.5 R-381）
 * 全部走 OpenBase /api/v1/dps-proxy/*，前端不直连 DPS（身份头由 OpenBase proxy 构造注入，前端不可伪造）。
 * 对齐《OpenBase-API接口设计文档-v1.4.5》§1（8 端点）
 */
import { http } from '@/core/api/http'

export interface DpsPortrait {
  person_id?: string
  name?: string
  tags?: string[]
  risk_level?: string
  updated_at?: string
  dimensions?: Record<string, unknown>
  [key: string]: unknown
}

export interface DpsTagCategory {
  id?: string
  name?: string
  description?: string
  org_id?: string
  tenant_id?: string
  created_at?: string
  [key: string]: unknown
}

export const dpsApi = {
  /** 画像列表（GET /api/v1/dps-proxy/portraits） */
  async listPortraits(params?: { page?: number; page_size?: number }): Promise<{ items: DpsPortrait[]; total?: number }> {
    const { data } = await http.get<{ code: number; data: { items: DpsPortrait[]; total?: number } }>('/dps-proxy/portraits', { params })
    return data.data
  },

  /** 画像详情（GET /api/v1/dps-proxy/portraits/{person_id}） */
  async getPortrait(personId: string): Promise<DpsPortrait> {
    const { data } = await http.get<{ code: number; data: DpsPortrait }>(`/dps-proxy/portraits/${encodeURIComponent(personId)}`)
    return data.data
  },

  /** 画像计算（POST /api/v1/dps-proxy/portraits/calculate） */
  async calculatePortrait(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    const { data } = await http.post<{ code: number; data: Record<string, unknown> }>('/dps-proxy/portraits/calculate', payload)
    return data.data
  },

  /** 标签分类（GET /api/v1/dps-proxy/tags/categories） */
  async listTagCategories(): Promise<{ items: DpsTagCategory[] }> {
    const { data } = await http.get<{ code: number; data: { items: DpsTagCategory[] } }>('/dps-proxy/tags/categories')
    return data.data
  },

  /** 创建标签分类（POST /api/v1/dps-proxy/tags/categories） */
  async createTagCategory(payload: { name: string; description?: string }): Promise<DpsTagCategory> {
    const { data } = await http.post<{ code: number; data: DpsTagCategory }>('/dps-proxy/tags/categories', payload)
    return data.data
  },

  /** 更新标签分类（PUT /api/v1/dps-proxy/tags/categories/{id}） */
  async updateTagCategory(categoryId: string, payload: { name?: string; description?: string }): Promise<DpsTagCategory> {
    const { data } = await http.put<{ code: number; data: DpsTagCategory }>(`/dps-proxy/tags/categories/${encodeURIComponent(categoryId)}`, payload)
    return data.data
  },

  /** 删除标签分类（DELETE /api/v1/dps-proxy/tags/categories/{id}） */
  async deleteTagCategory(categoryId: string): Promise<unknown> {
    const { data } = await http.delete<{ code: number; data: unknown }>(`/dps-proxy/tags/categories/${encodeURIComponent(categoryId)}`)
    return data.data
  },

  /** 报表概览（GET /api/v1/dps-proxy/reports/overview） */
  async getReportsOverview(): Promise<Record<string, unknown>> {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>('/dps-proxy/reports/overview')
    return data.data
  },

  /** 批量任务状态（GET /api/v1/dps-proxy/batch/tasks/{task_id}） */
  async getBatchTaskStatus(taskId: string): Promise<Record<string, unknown>> {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>(`/dps-proxy/batch/tasks/${encodeURIComponent(taskId)}`)
    return data.data
  },

  /** 审计日志（GET /api/v1/dps-proxy/audit/logs） */
  async listAuditLogs(): Promise<{ items: Record<string, unknown>[] }> {
    const { data } = await http.get<{ code: number; data: { items: Record<string, unknown>[] } }>('/dps-proxy/audit/logs')
    return data.data
  },

  /** 上游健康（GET /api/v1/dps-proxy/health） */
  async getDpsHealth(): Promise<{ status?: string; version?: string }> {
    const { data } = await http.get<{ code: number; data: { status?: string; version?: string } }>('/dps-proxy/health')
    return data.data
  },
}
