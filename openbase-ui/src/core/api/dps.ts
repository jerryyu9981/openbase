/**
 * DPS dps-proxy API 封装（v1.4.5 R-381；v1.4.10 扩展 22 方法 ＋ 2 跨上游协作）
 * 全部走 OpenBase /api/v1/dps-proxy/*，前端不直连 DPS（身份头由 OpenBase proxy 构造注入，前端不可伪造）。
 * 对齐《OpenBase-API接口设计文档-v1.4.5》§1（8 端点）与《OpenBase-API接口设计文档-v1.4.10》§1／§1.1／§3（22 端点）。
 *
 * 前端禁则（API 文档 v1.4.10 §5）：不直连 DPS；不构造身份头；不做权限判定；
 * 不假设 `tag_bindings` 结构（原样透传）；不提供「解除归属」入口（上游无此语义）。
 */
import { http, type ApiSuccess } from '@/core/api/http'
import { withSessionId } from '@/core/session'
import type { ChatMessage } from '@/core/api/llm'

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

/** 画像模板对象（#12；`dimension_config`／`tag_bindings` 等 JSON 配置块原样透传，前端不解析内部结构） */
export interface DpsPortraitTemplate {
  code: string
  name?: string
  profile_type?: string
  subject_type?: string
  /** 继承的父模板 code（深度 ≤2、禁自环／禁成环、父须存在） */
  extends?: string | null
  version?: number
  status?: string
  description?: string
  dimension_config?: unknown
  attributes_schema?: unknown
  tag_bindings?: unknown
  evidence_policy?: unknown
  anomaly_rules?: unknown
  [key: string]: unknown
}

/** 标注字段（`field_schema` 元素；type 仅 5 类） */
export interface DpsAnnotationField {
  key: string
  type: 'string' | 'enum' | 'number' | 'date' | 'list'
  required?: boolean
  /** `type=enum` 必填 */
  options?: string[]
  /** `type=number` 的 [low, high] */
  range?: [number, number] | number[]
  /** 有值即参与标签联动（tag_code = "{dimension}:{key}"） */
  target_dimension?: string
  [key: string]: unknown
}

/** 标注模板对象（#18；`template_code` 为强归属，非空且不可置空） */
export interface DpsAnnotationTemplate {
  code: string
  name?: string
  version?: number
  status?: string
  /** 归属画像模板（强归属，不可置空） */
  template_code?: string
  scenario?: string
  field_schema?: DpsAnnotationField[]
  [key: string]: unknown
}

export interface DpsTemplateFilter {
  status?: string
  profile_type?: string
  subject_type?: string
  page?: number
  page_size?: number
}

export interface DpsAnnotationTemplateFilter {
  template_code?: string
  scenario?: string
  page?: number
  page_size?: number
}

export interface DpsPaged<T> {
  items: T[]
  total?: number
}

/** 模板包（#1；前端不修改包内容，结构校验以 DPS 白名单为准） */
export interface DpsTemplatePackage {
  format_version?: string
  package_hash?: string
  items?: unknown[]
  dependencies?: unknown[]
  package?: Record<string, unknown>
  [key: string]: unknown
}

export interface DpsPackageImportRequest {
  package: Record<string, unknown>
  /** 冲突策略：overwrite／skip／rename（未指定且存在冲突 → 409） */
  conflict_policy?: 'overwrite' | 'skip' | 'rename'
  /** 导入须显式携带；`true` = 预检（不写入） */
  dry_run: boolean
}

export interface DpsPackageImportResult {
  would_create?: number
  would_skip?: number
  would_conflict?: number
  errors?: unknown[]
  created?: number
  skipped?: number
  renamed?: string[]
  identical?: boolean
  [key: string]: unknown
}

export interface DpsTemplateDiffEntry {
  change_type?: 'create' | 'update' | 'delete' | string
  path?: string
  before?: unknown
  after?: unknown
  [key: string]: unknown
}

export interface DpsTemplateDiff {
  code?: string
  from_version?: number
  to_version?: number
  changes?: DpsTemplateDiffEntry[]
  [key: string]: unknown
}

export interface DpsRollbackRequest {
  target_version: number
  reason?: string
}

export interface DpsRollbackResult {
  template_code?: string
  new_version?: number
  rolled_back_to?: number
  equivalence_check?: boolean
  [key: string]: unknown
}

export interface DpsPreflightResult {
  valid?: boolean
  checks?: Array<{ item?: string; passed?: boolean; detail?: string }>
  impact?: DpsImpactResult
  [key: string]: unknown
}

export interface DpsLineageSource {
  annotation_id?: string
  template_code?: string
  source?: string
  adapter_id?: string
  created_at?: string
  [key: string]: unknown
}

export interface DpsLineageResult {
  tag_code?: string
  sources?: DpsLineageSource[]
  [key: string]: unknown
}

/** 影响面查询参数（三层维度；`field_key` 显式不支持 → 400） */
export interface DpsImpactQuery {
  template_code?: string
  annotation_template_code?: string
  tag_code?: string
}

export interface DpsImpactResult {
  tag_count?: number
  profile_count?: number
  annotation_template_count?: number
  annotation_count?: number
  /** 口径说明（原文；`tag_count=0` 时前端须强制展开） */
  basis?: string | Record<string, unknown>
  [key: string]: unknown
}

export interface DpsMeasureSuggestion {
  tag_code?: string
  measure_code?: string
  measure_text?: string
  source_tag?: string
  [key: string]: unknown
}

export interface DpsMeasureResult {
  suggestions?: DpsMeasureSuggestion[]
  /** 免责声明（后端原文，前端不得改写） */
  disclaimer?: string
  [key: string]: unknown
}

export interface DpsScoringType {
  code?: string
  name?: string
  status?: string
  description?: string
  [key: string]: unknown
}

export interface DpsAnnotationGenerateRequest {
  text: string
  annotation_template: string
  [key: string]: unknown
}

export interface DpsAnnotationCandidate {
  annotation?: { id?: string; review_status?: string; [key: string]: unknown }
  source?: string
  adapter_id?: string
  [key: string]: unknown
}

/** 复核提交（DPS 既有端点 `POST /portrait/annotations/{id}/review`） */
export interface DpsReviewSubmitRequest {
  review_status: 'approved' | 'rejected' | 'modified'
  comment?: string
  modified_value?: unknown
}

/** AI 复核辅助（经 llm_proxy → OpenLLM，非本版 22 端点） */
export interface DpsReviewAssistRequest {
  model?: string
  messages: ChatMessage[]
  session_id?: string
}

export interface DpsReviewAssistResult {
  choices?: Array<{ message?: { content?: string }; [key: string]: unknown }>
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

  /* ==================== v1.4.10｜契约 10 新增端点（#1~#10） ==================== */

  /** 模板包导出（POST /dps-proxy/template-packages/export，#1；权限动作 = portrait_template:create） */
  async exportPackage(body: Record<string, unknown>): Promise<DpsTemplatePackage> {
    const { data } = await http.post<ApiSuccess<DpsTemplatePackage>>('/dps-proxy/template-packages/export', body)
    return data.data
  },

  /** 模板包导入（POST /dps-proxy/template-packages/import，#2；须带 `dry_run`，不得默认实做） */
  async importPackage(body: DpsPackageImportRequest): Promise<DpsPackageImportResult> {
    const { data } = await http.post<ApiSuccess<DpsPackageImportResult>>('/dps-proxy/template-packages/import', body)
    return data.data
  },

  /** 版本对比（GET /dps-proxy/templates/{code}/diff?from=&to=，#3） */
  async diffVersions(code: string, from: number | string, to: number | string): Promise<DpsTemplateDiff> {
    const { data } = await http.get<ApiSuccess<DpsTemplateDiff>>(`/dps-proxy/templates/${encodeURIComponent(code)}/diff`, {
      params: { from, to },
    })
    return data.data
  },

  /** 版本回滚（POST /dps-proxy/templates/{code}/rollback，#4；写操作，二次确认四要素前置） */
  async rollbackTemplate(code: string, body: DpsRollbackRequest): Promise<DpsRollbackResult> {
    const { data } = await http.post<ApiSuccess<DpsRollbackResult>>(`/dps-proxy/templates/${encodeURIComponent(code)}/rollback`, body)
    return data.data
  },

  /** 预检（GET /dps-proxy/templates/{code}/preflight，#5；只读，不写入） */
  async preflightTemplate(code: string): Promise<DpsPreflightResult> {
    const { data } = await http.get<ApiSuccess<DpsPreflightResult>>(`/dps-proxy/templates/${encodeURIComponent(code)}/preflight`)
    return data.data
  },

  /** 标签血缘反查（GET /dps-proxy/lineage/tags/{tag_code}，#6；无谱系 → 404） */
  async getTagLineage(tagCode: string): Promise<DpsLineageResult> {
    const { data } = await http.get<ApiSuccess<DpsLineageResult>>(`/dps-proxy/lineage/tags/${encodeURIComponent(tagCode)}`)
    return data.data
  },

  /** 影响面查询（GET /dps-proxy/lineage/impact，#7；三层维度，`field_key` 不支持 → 400） */
  async queryImpact(params: DpsImpactQuery): Promise<DpsImpactResult> {
    const { data } = await http.get<ApiSuccess<DpsImpactResult>>('/dps-proxy/lineage/impact', { params })
    return data.data
  },

  /** 措施建议（GET /dps-proxy/measures/suggest?person_id=，#8；只读） */
  async suggestMeasures(personId: string): Promise<DpsMeasureResult> {
    const { data } = await http.get<ApiSuccess<DpsMeasureResult>>('/dps-proxy/measures/suggest', {
      params: { person_id: personId },
    })
    return data.data
  },

  /** AI 标注候选生成（POST /dps-proxy/annotation-adapters/{adapter_id}/generate，#9；默认关闭态零写入） */
  async generateAnnotationCandidates(adapterId: string, body: DpsAnnotationGenerateRequest): Promise<DpsAnnotationCandidate> {
    const { data } = await http.post<ApiSuccess<DpsAnnotationCandidate>>(
      `/dps-proxy/annotation-adapters/${encodeURIComponent(adapterId)}/generate`,
      body,
    )
    return data.data
  },

  /** 评分类型列表（GET /dps-proxy/scoring-types，#10；只读） */
  async listScoringTypes(params?: { page?: number; page_size?: number }): Promise<DpsPaged<DpsScoringType>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsScoringType>>>('/dps-proxy/scoring-types', { params })
    return data.data
  },

  /* ==================== v1.4.10｜补代理 12 端点（#11~#22） ==================== */

  /** 画像模板列表（GET /dps-proxy/templates，#11；过滤 status／profile_type／subject_type） */
  async listTemplates(params?: DpsTemplateFilter): Promise<DpsPaged<DpsPortraitTemplate>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsPortraitTemplate>>>('/dps-proxy/templates', { params })
    return data.data
  },

  /** 画像模板详情（GET /dps-proxy/templates/{code}，#12；原样呈现不假设结构） */
  async getTemplate(code: string): Promise<DpsPortraitTemplate> {
    const { data } = await http.get<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}`)
    return data.data
  },

  /** 画像模板创建（POST /dps-proxy/templates，#13；400 含字段级原因／409 `code` 冲突） */
  async createTemplate(body: Partial<DpsPortraitTemplate> & { code: string }): Promise<DpsPortraitTemplate> {
    const { data } = await http.post<ApiSuccess<DpsPortraitTemplate>>('/dps-proxy/templates', body)
    return data.data
  },

  /** 画像模板更新（PUT /dps-proxy/templates/{code}，#14；版本递增 ＋ history 留痕） */
  async updateTemplate(code: string, body: Record<string, unknown>): Promise<DpsPortraitTemplate> {
    const { data } = await http.put<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}`, body)
    return data.data
  },

  /** 画像模板激活（POST /dps-proxy/templates/{code}/activate，#15；写，幂等） */
  async activateTemplate(code: string): Promise<DpsPortraitTemplate> {
    const { data } = await http.post<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}/activate`)
    return data.data
  },

  /** 画像模板停用（POST /dps-proxy/templates/{code}/deactivate，#16；写，幂等） */
  async deactivateTemplate(code: string): Promise<DpsPortraitTemplate> {
    const { data } = await http.post<ApiSuccess<DpsPortraitTemplate>>(`/dps-proxy/templates/${encodeURIComponent(code)}/deactivate`)
    return data.data
  },

  /** 标注模板列表（GET /dps-proxy/annotation-templates，#17；过滤 template_code／scenario） */
  async listAnnotationTemplates(params?: DpsAnnotationTemplateFilter): Promise<DpsPaged<DpsAnnotationTemplate>> {
    const { data } = await http.get<ApiSuccess<DpsPaged<DpsAnnotationTemplate>>>('/dps-proxy/annotation-templates', { params })
    return data.data
  },

  /** 标注模板详情（GET /dps-proxy/annotation-templates/{code}，#18；含 `field_schema`） */
  async getAnnotationTemplate(code: string): Promise<DpsAnnotationTemplate> {
    const { data } = await http.get<ApiSuccess<DpsAnnotationTemplate>>(`/dps-proxy/annotation-templates/${encodeURIComponent(code)}`)
    return data.data
  },

  /** 标注模板创建（POST /dps-proxy/annotation-templates，#19；`template_code` 必填且归属须 active） */
  async createAnnotationTemplate(body: Partial<DpsAnnotationTemplate> & { code: string; template_code: string }): Promise<DpsAnnotationTemplate> {
    const { data } = await http.post<ApiSuccess<DpsAnnotationTemplate>>('/dps-proxy/annotation-templates', body)
    return data.data
  },

  /** 标注模板更新／改挂（PUT /dps-proxy/annotation-templates/{code}，#20；含 `template_code` 即改挂；无解除归属） */
  async updateAnnotationTemplate(code: string, body: Record<string, unknown>): Promise<DpsAnnotationTemplate> {
    const { data } = await http.put<ApiSuccess<DpsAnnotationTemplate>>(`/dps-proxy/annotation-templates/${encodeURIComponent(code)}`, body)
    return data.data
  },

  /** 标注模板删除（DELETE /dps-proxy/annotation-templates/{code}，#21；409 时展示关联标注条数） */
  async deleteAnnotationTemplate(code: string): Promise<{ code?: string; deleted?: boolean }> {
    const { data } = await http.delete<ApiSuccess<{ code?: string; deleted?: boolean }>>(
      `/dps-proxy/annotation-templates/${encodeURIComponent(code)}`,
    )
    return data.data
  },

  /** 标签列表（GET /dps-proxy/labels?action=list，#22；`action` 仅此一种，其余 → 400） */
  async listLabels(): Promise<{ items: Record<string, unknown>[] }> {
    const { data } = await http.get<ApiSuccess<{ items: Record<string, unknown>[] }>>('/dps-proxy/labels', {
      params: { action: 'list' },
    })
    return data.data
  },

  /* ==================== v1.4.10｜跨上游协作（非 22 端点） ==================== */

  /** AI 复核辅助（经 llm_proxy → OpenLLM，A-1410-01；返回建议仅供参考，不自动改变候选状态） */
  async assistReview(payload: DpsReviewAssistRequest): Promise<DpsReviewAssistResult> {
    const body = withSessionId(payload as unknown as Record<string, unknown>)
    const { data } = await http.post<ApiSuccess<DpsReviewAssistResult>>('/llm-proxy/chat', {
      ...body,
      stream: false,
    })
    return data.data
  },

  /** 复核提交（DPS 既有端点 POST /portrait/annotations/{id}/review；409 = 未复核候选不得进入标签/画像路径） */
  async submitReview(annotationId: string, body: DpsReviewSubmitRequest): Promise<Record<string, unknown>> {
    const { data } = await http.post<ApiSuccess<Record<string, unknown>>>(
      `/dps-proxy/annotations/${encodeURIComponent(annotationId)}/review`,
      body,
    )
    return data.data
  },
}
