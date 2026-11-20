import type { DpsScoringIssue } from '@/core/api/dps'

/**
 * 评分口径问题定位（P-07）
 *
 * 口径体检的问题行需要「去修复」直达：有标注模板 + 字段 → 字段设计器；
 * 仅画像模板 → 模板工作台；两者皆无 → 模板中心。
 */

export interface ScoringFixTarget {
  label: string
  path: string
  kind: 'field' | 'workbench' | 'catalog'
}

export function resolveScoringFixTarget(issue: DpsScoringIssue): ScoringFixTarget {
  const annotationTemplate = String(issue.annotation_template || '').trim()
  if (annotationTemplate) {
    const base = `/portrait/dps/annotation-templates/${encodeURIComponent(annotationTemplate)}/fields`
    const fieldKey = String(issue.field_key || '').trim()
    return {
      label: fieldKey ? '去修复字段' : '去标注模板',
      path: fieldKey ? `${base}?field=${encodeURIComponent(fieldKey)}` : base,
      kind: 'field',
    }
  }
  const portraitTemplate = String(issue.portrait_template || '').trim()
  if (portraitTemplate) {
    return {
      label: '去模板工作台',
      path: `/portrait/dps/templates/${encodeURIComponent(portraitTemplate)}/edit`,
      kind: 'workbench',
    }
  }
  return { label: '去模板中心', path: '/portrait/dps/templates', kind: 'catalog' }
}

export interface ScoringIssueFilter {
  /** 模板关键字：匹配画像模板/标注模板/维度/标签 */
  template?: string
  /** 问题码（精确匹配） */
  code?: string
}

/**
 * 当前页过滤（DPS 报告分页由服务端控制，A12 未提供模板/问题码查询参数，
 * 因此前端仅过滤当前页，页面须明示口径）。
 */
export function filterScoringIssues(issues: DpsScoringIssue[], filter: ScoringIssueFilter): DpsScoringIssue[] {
  const template = (filter.template || '').trim().toLowerCase()
  const code = (filter.code || '').trim()
  return issues.filter((issue) => {
    if (code && issue.code !== code) return false
    if (!template) return true
    return [issue.portrait_template, issue.annotation_template, issue.dimension, issue.tag_code, issue.field_key]
      .map((value) => String(value || '').toLowerCase())
      .some((value) => value.includes(template))
  })
}

export function scoringIssueCodes(issues: DpsScoringIssue[], summary?: Record<string, number>): string[] {
  const codes = new Set<string>(Object.keys(summary || {}))
  for (const issue of issues) if (issue.code) codes.add(issue.code)
  return Array.from(codes).sort((left, right) => left.localeCompare(right))
}
