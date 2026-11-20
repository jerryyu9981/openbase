import type { DpsBatchReviewItemResult, DpsBatchReviewResult } from '@/core/api/dps'

/**
 * 批量复核结果呈现模型（设计文档 §11 AC-AN-7 / AC-RV-3）。
 *
 * 上游逐条返回 `{ok, annotation_id, status, review?, error?}`，失败单条不影响其余条目。
 * 此处只做「真实结果 → 可读行」的映射，不推测未返回的数据：
 * - 通过成功：区分末级（终审通过）与非末级（待下一级）；
 * - 驳回成功：已驳回；
 * - 失败：状态码 + 上游原因，便于审核员逐条核对后重试。
 */

export interface BatchReviewRow {
  annotationId: string
  ok: boolean
  resultLabel: string
  detail: string
}

export type BatchReviewAction = 'approved' | 'rejected'

function errorText(error: unknown): string {
  if (error === null || error === undefined) return ''
  if (typeof error === 'string') return error
  if (typeof error === 'object') {
    const record = error as Record<string, unknown>
    return String(record.message || record.detail || record.error || '')
  }
  return String(error)
}

/** 单条结果 → 结果行；`action` 为本次批量请求的动作 */
export function toBatchReviewRow(item: DpsBatchReviewItemResult, action: BatchReviewAction): BatchReviewRow {
  const annotationId = item.annotation_id ? String(item.annotation_id) : '(未知)'
  if (!item.ok) {
    const reason = errorText(item.error) || '处理失败'
    const code = item.status === undefined || item.status === '' ? '' : `（${item.status}）`
    return { annotationId, ok: false, resultLabel: '失败', detail: `${reason}${code}` }
  }
  if (action === 'rejected') {
    return { annotationId, ok: true, resultLabel: '成功', detail: '已驳回' }
  }
  const review = item.review
  if (review) {
    const level = Math.max(0, Number(review.level ?? 0))
    const required = Math.max(1, Number(review.required ?? 1))
    if (review.finalized) {
      return { annotationId, ok: true, resultLabel: '成功', detail: `终审通过（第 ${level}/${required} 级）` }
    }
    return {
      annotationId,
      ok: true,
      resultLabel: '成功',
      detail: `已通过第 ${level}/${required} 级，待第 ${level + 1} 级`,
    }
  }
  return { annotationId, ok: true, resultLabel: '成功', detail: String(item.status || '已通过') }
}

/** 批量结果 → 逐条结果行（顺序与请求一致；`items` 缺失时为空） */
export function toBatchReviewRows(
  result: DpsBatchReviewResult,
  action: BatchReviewAction,
): BatchReviewRow[] {
  const items = Array.isArray(result.items) ? result.items : []
  return items.map((item) => toBatchReviewRow(item, action))
}

/** 汇总文案（用于结果弹窗顶部提示） */
export function batchReviewSummary(result: DpsBatchReviewResult): string {
  return `共 ${result.total} 条：成功 ${result.succeeded} 条，失败 ${result.failed} 条`
}
