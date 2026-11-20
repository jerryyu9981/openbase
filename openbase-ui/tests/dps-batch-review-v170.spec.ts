/**
 * v1.7.0 A3 批量审核结果呈现测试
 *
 * 覆盖 AC-AN-7（批量通过/驳回结果逐条反馈）与 AC-RV-3（非末级提示待第 k+1 级）：
 * 成功/失败映射、末级/非末级文案、驳回、缺 ID、空结果。
 */
import { describe, expect, it } from 'vitest'
import {
  batchReviewSummary,
  toBatchReviewRow,
  toBatchReviewRows,
  type BatchReviewRow,
} from '@/modules/portrait/annotation/batchReview'
import type { DpsBatchReviewResult } from '@/core/api/dps'

describe('A3 批量审核结果呈现', () => {
  it('非末级通过：提示待第 k+1 级', () => {
    const row = toBatchReviewRow(
      { annotation_id: 'ann-1', ok: true, status: 'pending', review: { level: 1, required: 3, finalized: false } },
      'approved',
    )
    expect(row).toEqual<BatchReviewRow>({
      annotationId: 'ann-1',
      ok: true,
      resultLabel: '成功',
      detail: '已通过第 1/3 级，待第 2 级',
    })
  })

  it('末级通过：终审通过', () => {
    const row = toBatchReviewRow(
      { annotation_id: 'ann-2', ok: true, status: 'approved', review: { level: 2, required: 2, finalized: true } },
      'approved',
    )
    expect(row.detail).toBe('终审通过（第 2/2 级）')
  })

  it('驳回成功：显示已驳回', () => {
    const row = toBatchReviewRow({ annotation_id: 'ann-3', ok: true, status: 'rejected' }, 'rejected')
    expect(row.resultLabel).toBe('成功')
    expect(row.detail).toBe('已驳回')
  })

  it('失败条目：保留上游原因与状态码，不阻断其余条目', () => {
    const row = toBatchReviewRow({ annotation_id: 'ann-4', ok: false, status: 409, error: '标注状态已变更' }, 'approved')
    expect(row.ok).toBe(false)
    expect(row.resultLabel).toBe('失败')
    expect(row.detail).toBe('标注状态已变更（409）')
  })

  it('缺 annotation_id 时显示占位而非空白', () => {
    const row = toBatchReviewRow({ annotation_id: null, ok: false, error: 'annotation_id 必填' }, 'approved')
    expect(row.annotationId).toBe('(未知)')
    expect(row.detail).toBe('annotation_id 必填')
  })

  it('批量结果逐条映射并给出汇总文案；items 缺失时安全返回空数组', () => {
    const result: DpsBatchReviewResult = {
      total: 2,
      succeeded: 1,
      failed: 1,
      items: [
        { annotation_id: 'ann-a', ok: true, review: { level: 1, required: 1, finalized: true } },
        { annotation_id: 'ann-b', ok: false, status: 404, error: '标注记录不存在' },
      ],
    }
    const rows = toBatchReviewRows(result, 'approved')
    expect(rows).toHaveLength(2)
    expect(rows[0].detail).toBe('终审通过（第 1/1 级）')
    expect(rows[1].ok).toBe(false)
    expect(batchReviewSummary(result)).toBe('共 2 条：成功 1 条，失败 1 条')

    expect(toBatchReviewRows({ total: 0, succeeded: 0, failed: 0, items: undefined as never }, 'approved')).toEqual([])
  })
})
