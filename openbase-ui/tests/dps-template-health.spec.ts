import { describe, expect, it } from 'vitest'
import {
  buildTemplateHealth,
  groupScoringIssuesByTemplate,
  lineageGapIssues,
} from '@/modules/portrait/templates/health'
import type { DpsScoringIssue, DpsTemplateLineage } from '@/core/api/dps'

function scoringIssue(overrides: Partial<DpsScoringIssue> = {}): DpsScoringIssue {
  return {
    code: 'SCORING_TAG_ONLY',
    severity: 'WARN',
    portrait_template: 'cc-v1',
    message: '标签无评分项',
    ...overrides,
  }
}

function lineage(gaps: Array<{ type: string; severity: string; code?: string; message: string }>): DpsTemplateLineage {
  return {
    template_code: 'cc-v1',
    lineage: [],
    bindings: [],
    annotation_templates: [],
    scoring: null,
    gaps: {
      dimensions_without_annotation_source: [],
      unbound_annotation_templates: [],
      bound_annotation_templates_missing: [],
      ownership_mismatches: [],
      tag_outputs_without_scoring_rule: [],
      items: gaps,
    },
  }
}

describe('模板健康度前端组合（A8 降级口径）', () => {
  it('按 portrait_template 归组口径问题，忽略无归属问题', () => {
    const grouped = groupScoringIssuesByTemplate([
      scoringIssue(),
      scoringIssue({ code: 'OTHER', severity: 'BLOCK', portrait_template: 'cc-v2' }),
      scoringIssue({ portrait_template: '' }),
    ])
    expect(Object.keys(grouped).sort()).toEqual(['cc-v1', 'cc-v2'])
    expect(grouped['cc-v2'][0].severity).toBe('BLOCK')
  })

  it('血缘缺口 severity=error 视为阻断，其余为告警', () => {
    const issues = lineageGapIssues(
      lineage([
        { type: 'unbound_annotation', severity: 'error', code: 'at-1', message: '标注模板未绑定维度' },
        { type: 'tag_only', severity: 'warning', code: 'tag:1', message: '标签无评分项' },
      ]),
    )
    expect(issues.map((issue) => issue.level)).toEqual(['block', 'warn'])
    expect(issues[0].source).toBe('lineage')
  })

  it('BLOCK 优先于 WARN，缺口计数独立统计', () => {
    const health = buildTemplateHealth({
      scoringIssues: [scoringIssue({ severity: 'BLOCK' }), scoringIssue({ code: 'W' })],
      lineage: lineage([
        { type: 'gap', severity: 'warning', message: '缺口 1' },
        { type: 'gap', severity: 'warning', message: '缺口 2' },
      ]),
      loaded: true,
    })
    expect(health.level).toBe('block')
    expect(health.block).toBe(1)
    expect(health.warn).toBe(3)
    expect(health.gap).toBe(2)
    expect(health.issues).toHaveLength(4)
  })

  it('无问题且未加载时为 unknown，加载完成才判定为 ok', () => {
    expect(buildTemplateHealth({ loaded: false }).level).toBe('unknown')
    expect(buildTemplateHealth({ loaded: true }).level).toBe('ok')
    expect(buildTemplateHealth({ lineage: lineage([]) }).level).toBe('ok')
  })

  it('仅有口径告警时为 warn，不被 unknown 覆盖', () => {
    const health = buildTemplateHealth({ scoringIssues: [scoringIssue()], loaded: false })
    expect(health.level).toBe('warn')
    expect(health.warn).toBe(1)
  })
})
