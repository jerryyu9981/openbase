import type { DpsScoringIssue, DpsTemplateLineage } from '@/core/api/dps'

/**
 * 模板健康度前端组合（设计文档 §7 P-04 / §9 A8 降级口径）。
 *
 * 服务端暂无 `/templates/{code}/health` 聚合接口时，健康度由两部分组合：
 * - 口径问题：`getScoringConsistency` 报告按 `portrait_template` 归组；
 * - 配置缺口：`getTemplateLineage` 的 `gaps.items`。
 *
 * 纯函数便于单测；页面只负责拉取与呈现。
 */

export type TemplateHealthLevel = 'ok' | 'warn' | 'block' | 'unknown'

export interface TemplateHealthIssue {
  level: 'block' | 'warn'
  source: 'scoring' | 'lineage'
  code?: string
  message: string
  tag_code?: string
  annotation_template?: string | null
  field_key?: string | null
}

export interface TemplateHealth {
  level: TemplateHealthLevel
  block: number
  warn: number
  gap: number
  issues: TemplateHealthIssue[]
}

export function groupScoringIssuesByTemplate(issues: DpsScoringIssue[] = []): Record<string, DpsScoringIssue[]> {
  const grouped: Record<string, DpsScoringIssue[]> = {}
  for (const issue of issues) {
    const code = String(issue.portrait_template || '').trim()
    if (!code) continue
    ;(grouped[code] ||= []).push(issue)
  }
  return grouped
}

/** 血缘缺口 → 健康度问题项（`severity=error` 视为阻断，其余为告警） */
export function lineageGapIssues(lineage?: DpsTemplateLineage | null): TemplateHealthIssue[] {
  const items = lineage?.gaps?.items || []
  return items.map((item) => ({
    level: String(item.severity || '').toLowerCase() === 'error' ? 'block' : 'warn',
    source: 'lineage' as const,
    code: item.code,
    message: item.message,
  }))
}

export function buildTemplateHealth(input: {
  scoringIssues?: DpsScoringIssue[]
  lineage?: DpsTemplateLineage | null
  /** false = 血缘/口径数据尚未拉取，无问题时返回 unknown 而非 ok */
  loaded?: boolean
}): TemplateHealth {
  const scoring: TemplateHealthIssue[] = (input.scoringIssues || []).map((issue) => ({
    level: issue.severity === 'BLOCK' ? 'block' : 'warn',
    source: 'scoring' as const,
    code: issue.code,
    message: issue.message || issue.code,
    tag_code: issue.tag_code,
    annotation_template: issue.annotation_template ?? null,
    field_key: issue.field_key ?? null,
  }))
  const gaps = lineageGapIssues(input.lineage)
  const issues = [...scoring, ...gaps]
  const block = issues.filter((issue) => issue.level === 'block').length
  const warn = issues.filter((issue) => issue.level === 'warn').length

  let level: TemplateHealthLevel = 'ok'
  if (block > 0) level = 'block'
  else if (warn > 0) level = 'warn'
  else if (input.loaded === false) level = 'unknown'

  return { level, block, warn, gap: gaps.length, issues }
}
