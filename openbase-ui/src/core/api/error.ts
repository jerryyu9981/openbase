/**
 * 统一错误分类工具（S6 设计草案 §2.4 / §5.1 / §5.2 Q-FE-3b）
 *
 * 消费 `http.ts` 的 `ErrorResponse{code,message,detail,request_id}` 契约，
 * 把任意失败映射为页面可消费的呈现语义（空态 / 403 / 404 / 错误条 + 重试），
 * 使关键页可按 `kind` 渲染，避免「把空数据渲染为错误」或「把错误渲染为空」。
 *
 * 约束：`request_id` 仅在页面详情内展示，不得写入 URL、localStorage 或日志。
 */
import axios, { AxiosError } from 'axios'
import type { ErrorResponse } from './http'

/** 复出后端错误契约类型，便于页面/测试统一从 error 模块消费 */
export type { ErrorResponse }

export type ApiErrorKind =
  | 'unauthorized'
  | 'forbidden'
  | 'not-found'
  | 'invalid-param'
  | 'business'
  /** 409：冲突／状态门禁（v1.4.10 新增，如 code 冲突、存在关联标注数据、未复核候选进入下游） */
  | 'conflict'
  | 'server-error'
  | 'network'
  | 'canceled'
  | 'unknown'

/** 后端错误码前缀（AGENTS.md §2 错误码规范） */
export const ERROR_CODE_PREFIXES = ['AUTH_', 'PERM_', 'PARAM_', 'BIZ_', 'SYS_', 'STORAGE_'] as const
export type ErrorCodePrefix = (typeof ERROR_CODE_PREFIXES)[number] | ''

export interface ClassifiedError {
  kind: ApiErrorKind
  code: string
  codePrefix: ErrorCodePrefix
  message: string
  requestId: string
  status?: number
}

export interface ErrorPresentation {
  kind: ApiErrorKind
  /** 页面级标题（空态/错误条共用） */
  title: string
  /** 可与后端 message 合并的明细文案 */
  detail: string
  requestId: string
  retryable: boolean
  /** 是否整页呈现（403/401），而非表格内错误条 */
  pageLevel: boolean
}

/** 提取错误码前缀（未命中返回空串） */
export function extractCodePrefix(code?: string | null): ErrorCodePrefix {
  if (!code) return ''
  return ERROR_CODE_PREFIXES.find((prefix) => code.startsWith(prefix)) ?? ''
}

function isCanceled(error: unknown): boolean {
  return axios.isCancel(error) || (error as AxiosError | undefined)?.code === AxiosError.ERR_CANCELED
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : ''
}

/**
 * 按 §5.1 / §5.2 判定表解析 `kind`。
 * 优先级：401 → unauthorized；`PERM_` 前缀 / 403 → forbidden；
 * 404 → not-found；409 → conflict（v1.4.10）；5xx / `SYS_`|`STORAGE_` → server-error；400/422 → 参数/业务。
 */
export function resolveErrorKind(status?: number, codePrefix: ErrorCodePrefix = ''): ApiErrorKind {
  if (status === 401) return 'unauthorized'
  if (codePrefix === 'PERM_') return 'forbidden'
  if (status === 403) return 'forbidden'
  if (codePrefix === 'AUTH_') return 'forbidden'
  if (status === 404) return 'not-found'
  if (status === 409) return 'conflict'
  if (typeof status === 'number' && status >= 500) return 'server-error'
  if (codePrefix === 'SYS_' || codePrefix === 'STORAGE_') return 'server-error'
  if (status === 400 || status === 422) return codePrefix === 'PARAM_' ? 'invalid-param' : 'business'
  return 'unknown'
}

/** 把任意失败映射为分类结果（消费 ErrorResponse 契约） */
export function classifyError(error: unknown): ClassifiedError {
  if (isCanceled(error)) {
    return { kind: 'canceled', code: '', codePrefix: '', message: messageOf(error) || '请求已取消', requestId: '' }
  }
  if (!axios.isAxiosError<ErrorResponse>(error)) {
    return { kind: 'unknown', code: '', codePrefix: '', message: messageOf(error) || '请求失败', requestId: '' }
  }
  const response = error.response
  if (!response) {
    return { kind: 'network', code: '', codePrefix: '', message: messageOf(error) || '网络异常', requestId: '' }
  }
  const status = response.status
  const body = (response.data ?? {}) as Partial<ErrorResponse>
  const code = typeof body.code === 'string' ? body.code : ''
  const codePrefix = extractCodePrefix(code)
  return {
    kind: resolveErrorKind(status, codePrefix),
    code,
    codePrefix,
    message: body.message || error.message || '请求失败',
    requestId: typeof body.request_id === 'string' ? body.request_id : '',
    status,
  }
}

const KIND_TITLES: Record<ApiErrorKind, string> = {
  unauthorized: '登录已失效，请重新登录',
  forbidden: '无权限访问该资源',
  'not-found': '资源不存在或已被移除',
  'invalid-param': '请求参数有误',
  business: '操作未完成',
  conflict: '操作被拒绝',
  'server-error': '加载失败，请稍后重试',
  network: '网络异常，请检查网络后重试',
  canceled: '请求已取消',
  unknown: '加载失败',
}

const RETRYABLE_KINDS: ApiErrorKind[] = ['server-error', 'network', 'unknown']

/** 生成页面呈现语义（标题 / 明细 / 是否页面级 / 是否可重试 / request_id 详情） */
export function describeError(error: unknown): ErrorPresentation {
  const classified = classifyError(error)
  return {
    kind: classified.kind,
    title: KIND_TITLES[classified.kind],
    detail: classified.message,
    requestId: classified.requestId,
    retryable: RETRYABLE_KINDS.includes(classified.kind),
    pageLevel: classified.kind === 'forbidden' || classified.kind === 'unauthorized',
  }
}

/**
 * DPS 模板化专项错误语义（《前端架构设计文档-v1.4.10》§4 错误码呈现分工表）。
 *
 * 与通用 `describeError` 并存：`kind` 分类口径不变（保持既有 S6 隔离呈现契约），
 * 仅按**状态码**追加可呈现的语义提示，覆盖 400／403／404／409／422／503 与 5xx 兜底。
 */
export const DPS_ERROR_HINTS: Record<number, string> = {
  400: '请求内容不符合校验规则（含字段级原因：字段键不受支持／归属模板未激活／extends 深度超限等）',
  403: '无权限执行该操作，或该能力当前未启用',
  404: '未找到对应资源（模板／版本／血缘谱系不存在）',
  409: '操作被拒绝：存在冲突或未复核候选，不得进入标签／画像路径',
  422: '包结构非法（白名单校验未通过）',
  503: 'AI 适配器暂不可用，人工路径不受影响',
}

/** 按状态码取 DPS 专项提示（未命中返回空串；5xx 走统一兜底文案） */
export function dpsErrorHint(status?: number): string {
  if (typeof status !== 'number') return ''
  if (DPS_ERROR_HINTS[status]) return DPS_ERROR_HINTS[status]
  if (status >= 500) return '服务暂不可用，请稍后重试（不静默降级）'
  return ''
}

/** DPS 页面呈现语义（在通用归一模型上追加 `hint`） */
export interface DpsErrorPresentation extends ErrorPresentation {
  hint: string
}

/** 生成 DPS 页面呈现语义（通用归一 ＋ 状态码专项提示） */
export function describeDpsError(error: unknown): DpsErrorPresentation {
  const classified = classifyError(error)
  return { ...describeError(error), hint: dpsErrorHint(classified.status) }
}
