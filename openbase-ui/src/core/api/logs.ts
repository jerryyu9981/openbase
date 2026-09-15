/**
 * 日志中心 API（对齐《API接口设计文档-v1.4.6》§2/§3）
 *
 * 契约唯一事实源原则（API 文档 §2）：前端不自行派生分类字段，全部以后端返回为准。
 * 多选传参约定（§4「数据获取层」）：module/operation/result/operator 以**重复同名参数**传递
 * （`?module=identity&module=memory`），后端按其 OR 语义解析 —— 用 URLSearchParams 精确实现。
 */
import { http, type ApiSuccess } from './http'

/** 数据源枚举（v1.1.0 新增 repo_log 四仓日志源） */
export type LogSource = 'l1_file' | 'audit_db' | 'test_record' | 'repo_log'

/** module 枚举（API §4.1） */
export type LogModule = 'identity' | 'dps' | 'rag' | 'memory' | 'llm' | 'gateway' | 'testing' | 'other'
/** operation 枚举（API §4.2） */
export type LogOperation = 'auth_login' | 'read' | 'write' | 'delete' | 'config' | 'proxy'
/** result 枚举（API §4.3） */
export type LogResult = 'success' | 'client_error' | 'server_error' | 'unknown'

/** 统一数据契约 LogEntry（API §2，18 字段；1~5 为必需） */
export interface LogEntry {
  ts: string
  source: LogSource
  module: LogModule
  operation: LogOperation
  result: LogResult
  request_id: string | null
  method: string | null
  path: string | null
  status_code: number | null
  duration_ms: number | null
  operator_id: string | null
  tenant_id: string | null
  ip_address: string | null
  case_id: string | null
  step_id: number | string | null
  run_id: string | null
  action: string | null
  summary: Record<string, unknown> | null
}

/** 查询参数（与后端 snake_case 一致） */
export interface LogQuery {
  source: LogSource
  module?: LogModule[]
  operation?: LogOperation[]
  result?: LogResult[]
  operator?: string[]
  q?: string
  from?: string
  to?: string
  case_id?: string
  run_id?: string
  step_id?: number | string
}

/** search 响应（API §3.1） */
export interface LogSearchResponse {
  items: LogEntry[]
  total: number
  page: number
  page_size: number
  source: LogSource
  truncated: boolean
}

/** facets 响应（API §3.2） */
export interface LogFacetsResponse {
  source: LogSource
  module: Record<string, number>
  operation: Record<string, number>
  result: Record<string, number>
  operator: Record<string, number>
  truncated: boolean
}

/** 导出的可读来源标签（UI 展示） */
export const LOG_SOURCE_LABELS: Record<LogSource, string> = {
  l1_file: 'L1 文件',
  audit_db: '审计库',
  test_record: '测试记录',
  repo_log: '四仓日志',
}

export const LOG_SOURCE_OPTIONS = ['l1_file', 'audit_db', 'test_record', 'repo_log'] as const

const PAGE_SIZE_MAX = 100

/**
 * 序列化日志查询为「重复同名参数」的 URLSearchParams。
 * 私有 query 键不透传；未知可选键被忽略（保持与后端契约一致）。
 */
function buildLogParams(query: LogQuery): URLSearchParams {
  const usp = new URLSearchParams()
  usp.append('source', query.source)
  const appendMulti = (key: string, list: readonly string[] | undefined) => {
    list?.forEach((item) => usp.append(key, item))
  }
  appendMulti('module', query.module)
  appendMulti('operation', query.operation)
  appendMulti('result', query.result)
  appendMulti('operator', query.operator)
  if (query.q) usp.append('q', query.q)
  if (query.from) usp.append('from', query.from)
  if (query.to) usp.append('to', query.to)
  if (query.case_id) usp.append('case_id', query.case_id)
  if (query.run_id) usp.append('run_id', query.run_id)
  if (query.step_id !== undefined && query.step_id !== null) usp.append('step_id', String(query.step_id))
  return usp
}

function clampPageSize(pageSize: number | undefined): number {
  if (pageSize === undefined) return 20
  if (pageSize < 1) return 1
  return Math.min(pageSize, PAGE_SIZE_MAX)
}

export const logsApi = {
  async search(query: LogQuery, page = 1, pageSize = 20): Promise<LogSearchResponse> {
    const params = buildLogParams(query)
    params.append('page', String(page))
    params.append('page_size', String(clampPageSize(pageSize)))
    const { data } = await http.get<ApiSuccess<LogSearchResponse>>('/logs/search', { params })
    return data.data
  },
  async facets(query: LogQuery): Promise<LogFacetsResponse> {
    const params = buildLogParams(query)
    const { data } = await http.get<ApiSuccess<LogFacetsResponse>>('/logs/facets', { params })
    return data.data
  },
  /**
   * 导出（responseType blob 触发浏览器下载；Content-Disposition 提供文件名）
   * @param query 当前筛选条件
   * @param format 导出格式
   */
  async export(query: LogQuery, format: 'csv' | 'json'): Promise<Blob> {
    const params = buildLogParams(query)
    params.append('format', format)
    const { data } = await http.get<Blob>('/logs/export', { params, responseType: 'blob' })
    return data
  },
}