/**
 * 统一网关 API 封装（v1.4.0）：/api/v1/services + /api/v1/gateway/*
 * 对齐《API 接口设计文档 v1.4.0》§2
 */
import { http } from '@/core/api/http'

export interface ServiceInstance {
  system: string
  instance_id: string
  host: string
  port: number
  weight: number
  healthy: boolean
  last_heartbeat: number
  consecutive_failures: number
  meta: Record<string, unknown>
}

export interface SystemServices {
  system: string
  instances: ServiceInstance[]
}

export interface AggregateStep {
  id: string
  system: string
  path: string
  method?: string
  timeout_ms?: number
}

export interface AggregateRequest {
  steps: AggregateStep[]
  timeout_ms?: number
  on_partial_failure?: 'return_errors' | 'strict' | 'best_effort'
  mapping: Record<string, string>
}

export const gatewayApi = {
  /** 全部服务实例列表（含健康状态） */
  async listAllServices(): Promise<{ systems: SystemServices[] }> {
    const { data } = await http.get<{ code: number; data: { systems: SystemServices[] } }>('/services')
    return data.data
  },

  /** 指定系统实例列表 */
  async listSystemServices(system: string): Promise<{ instances: ServiceInstance[] }> {
    const { data } = await http.get<{ code: number; data: { instances: ServiceInstance[] } }>(`/services/${system}`)
    return data.data
  },

  /** 实例注册 */
  async registerService(payload: {
    system: string
    host: string
    port: number
    weight?: number
    instance_id?: string
  }): Promise<ServiceInstance> {
    const { data } = await http.post<{ code: number; data: ServiceInstance }>('/services', payload)
    return data.data
  },

  /** 实例下线 */
  async deregisterService(system: string, instanceId: string): Promise<{ deleted: string }> {
    const { data } = await http.delete<{ code: number; data: { deleted: string } }>(`/services/${system}/${instanceId}`)
    return data.data
  },

  /** 网关发现层健康状态 */
  async health(): Promise<{ systems: Array<{ system: string; healthy: boolean; instance_count: number; health_rate: number }> }> {
    const { data } = await http.get<{ code: number; data: { systems: Array<{ system: string; healthy: boolean; instance_count: number; health_rate: number }> } }>('/gateway/health')
    return data.data
  },

  /** 四系统连通性一键检测 */
  async ping(): Promise<{ results: Array<{ system: string; reachable: boolean; latency_ms: number | null }> }> {
    const { data } = await http.get<{ code: number; data: { results: Array<{ system: string; reachable: boolean; latency_ms: number | null }> } }>('/gateway/ping')
    return data.data
  },

  /** 聚合编排执行 */
  async aggregate(req: AggregateRequest): Promise<{ result: Record<string, unknown>; errors: string[] }> {
    const { data } = await http.post<{ code: number; data: { result: Record<string, unknown>; errors: string[] } }>('/gateway/aggregate', req)
    return data.data
  },
}
