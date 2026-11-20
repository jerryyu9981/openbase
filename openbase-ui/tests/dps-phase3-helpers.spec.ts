import { describe, expect, it } from 'vitest'
import type { DpsAnnotationRow, DpsLineageSource, DpsPortrait, DpsScoringIssue, DpsTemplateLineage } from '@/core/api/dps'
import {
  UNCATEGORIZED_KEY,
  buildTagTree,
  filterTagTree,
  normalizeTagLabel,
  resolveTagCode,
} from '@/modules/portrait/tags/tagTree'
import {
  buildTagChainGroups,
  collectScoringHits,
  tagFieldMatches,
} from '@/modules/portrait/lineage/lineageChain'
import {
  filterScoringIssues,
  resolveScoringFixTarget,
  scoringIssueCodes,
} from '@/modules/portrait/scoring/scoringFix'
import {
  attributeRowsFromObject,
  attributeRowsToObject,
  buildAnnotationTimeline,
  buildPortraitCsv,
  filterPortraitRows,
  matchPortraitConditions,
  parseAttributeValue,
  splitHighlight,
  type PortraitCondition,
} from '@/modules/portrait/portrait/portraitTools'
import { groupMeasureSuggestions, measureSuggestionsCsv } from '@/modules/portrait/measures/measureGroups'

describe('P-07 标签树', () => {
  it('按 category_id / 分类名归组，未匹配归入未分类', () => {
    const tree = buildTagTree(
      [
        { id: 'c1', name: '服务渠道', description: '渠道' },
        { id: 'c2', name: '风险' },
      ],
      [
        normalizeTagLabel({ name: '线上', category_id: 'c1', sort_order: 2 }),
        normalizeTagLabel({ name: '线下', category_id: 'c1', sort_order: 1 }),
        normalizeTagLabel({ name: '高风险', category: '风险' }),
        normalizeTagLabel({ name: '孤立标签' }),
      ],
    )
    expect(tree).toHaveLength(3)
    expect(tree[0].children?.map((item) => item.name)).toEqual(['线下', '线上'])
    expect(tree[1].children?.[0].name).toBe('高风险')
    expect(tree[2].key).toBe(UNCATEGORIZED_KEY)
  })

  it('搜索命中分类名保留全部标签，否则只保留命中标签', () => {
    const tree = buildTagTree(
      [{ id: 'c1', name: '服务渠道' }],
      [normalizeTagLabel({ name: '线上', category_id: 'c1' }), normalizeTagLabel({ name: '线下', category_id: 'c1' })],
    )
    expect(filterTagTree(tree, '服务')[0].children).toHaveLength(2)
    expect(filterTagTree(tree, '线上')[0].children?.map((item) => item.name)).toEqual(['线上'])
    expect(filterTagTree(tree, '不存在')).toHaveLength(0)
  })

  it('resolveTagCode 优先显式 code，其次分类:标签', () => {
    const tree = buildTagTree([{ id: 'c1', name: '服务' }], [normalizeTagLabel({ name: '线上', category_id: 'c1' })])
    const label = tree[0].children?.[0]
    expect(resolveTagCode(label || null)).toBe('服务:线上')
    expect(resolveTagCode({ ...label!, code: 'service:online' })).toBe('service:online')
    expect(resolveTagCode(tree[0])).toBe('')
  })
})

describe('P-07 标签血缘链路', () => {
  const sources: DpsLineageSource[] = [
    { annotation_id: 'a1', template_code: 'cc-v1' },
    { annotation_id: 'a2', template_code: 'cc-v1' },
  ]
  const lineage = {
    template_code: 'cc-v1',
    name: '客服画像',
    annotation_templates: [
      {
        code: 'cc-annot',
        name: '客服标注',
        fields: [
          {
            key: 'channel',
            label: '渠道',
            tag_code: 'service:channel',
            tag_key: 'channel',
            affects_scoring: [{ dimension: 'service', rule_key: 'r1', weight: 0.5, description: '渠道评分' }],
          },
          { key: 'other', label: '其他', tag_code: 'service:other', tag_key: 'other', affects_scoring: [] },
        ],
      },
    ],
  } as unknown as DpsTemplateLineage

  it('字段按 tag_code / tag_key 匹配', () => {
    expect(tagFieldMatches('service:channel', { tag_code: 'service:channel' })).toBe(true)
    expect(tagFieldMatches('service:channel', { tag_key: 'channel' })).toBe(true)
    expect(tagFieldMatches('service:channel', { tag_code: 'service:other' })).toBe(false)
  })

  it('按来源模板分组并汇总评分命中', () => {
    const groups = buildTagChainGroups('service:channel', sources, [lineage])
    expect(groups).toHaveLength(1)
    expect(groups[0].fields).toHaveLength(1)
    expect(groups[0].fields[0].annotationTemplate).toBe('cc-annot')
    expect(groups[0].missingField).toBe(false)
    expect(collectScoringHits(groups)).toHaveLength(1)
  })

  it('血缘缺失时标记缺口，不伪造链路', () => {
    const groups = buildTagChainGroups('service:channel', sources, [null])
    expect(groups[0].missingField).toBe(true)
    expect(groups[0].fields).toHaveLength(0)
  })
})

describe('P-07 口径问题定位', () => {
  const issue: DpsScoringIssue = {
    code: 'SC_TAG_NO_RULE',
    severity: 'BLOCK',
    portrait_template: 'cc-v1',
    annotation_template: 'cc-annot',
    field_key: 'channel',
  }

  it('有标注模板+字段 → 字段设计器；仅画像模板 → 工作台；否则模板中心', () => {
    expect(resolveScoringFixTarget(issue).path).toBe('/portrait/dps/annotation-templates/cc-annot/fields?field=channel')
    expect(resolveScoringFixTarget({ ...issue, field_key: null }).path).toBe('/portrait/dps/annotation-templates/cc-annot/fields')
    expect(
      resolveScoringFixTarget({ ...issue, annotation_template: null, field_key: null }).path,
    ).toBe('/portrait/dps/templates/cc-v1/edit')
    expect(
      resolveScoringFixTarget({ ...issue, annotation_template: null, portrait_template: '' }).path,
    ).toBe('/portrait/dps/templates')
  })

  it('按模板关键字与问题码过滤当前页', () => {
    const issues = [issue, { ...issue, code: 'SC_OTHER', tag_code: 'service:score' }]
    expect(filterScoringIssues(issues, { code: 'SC_OTHER' })).toHaveLength(1)
    expect(filterScoringIssues(issues, { template: 'score' })).toHaveLength(1)
    expect(filterScoringIssues(issues, { template: 'cc-annot' })).toHaveLength(2)
    expect(scoringIssueCodes(issues, { SC_TAG_NO_RULE: 1 })).toEqual(['SC_OTHER', 'SC_TAG_NO_RULE'])
  })
})

describe('P-08 画像列表 / 搜索', () => {
  const rows: DpsPortrait[] = [
    { person_id: 'P-1', name: '张三', risk_score: 75, tags: [{ tag_name: '高风险' }], created_at: '2026-01-01T00:00:00Z' },
    { person_id: 'P-2', name: '李四', risk_score: 30, created_at: '2026-02-01T00:00:00Z' },
  ]

  it('关键字过滤与 CSV 转义', () => {
    expect(filterPortraitRows(rows, '李四')).toHaveLength(1)
    const csv = buildPortraitCsv([{ person_id: 'P-3', name: '含,逗号"引号' }])
    expect(csv.split('\r\n')[1]).toContain('"含,逗号""引号"')
  })

  it('高级条件多条件 AND', () => {
    const conditions: PortraitCondition[] = [
      { id: 'c1', field: 'risk', value: 'high' },
      { id: 'c2', field: 'created_after', value: '2025-12-01' },
    ]
    expect(matchPortraitConditions(rows, conditions).map((row) => row.person_id)).toEqual(['P-1'])
    expect(matchPortraitConditions(rows, [{ id: 'c1', field: 'keyword', value: '李' }])).toHaveLength(1)
  })

  it('关键字高亮分段不丢字符', () => {
    const segments = splitHighlight('张三丰张三', '张三')
    expect(segments.map((item) => item.text).join('')).toBe('张三丰张三')
    expect(segments.filter((item) => item.hit)).toHaveLength(2)
    expect(splitHighlight('abc', '')).toEqual([{ text: 'abc', hit: false }])
  })

  it('标注时间线按创建时间倒序并带审核状态', () => {
    const annotations: DpsAnnotationRow[] = [
      { id: 'a1', person_name: '张三', annotation_template: 'cc', review_status: 'pending', review_level: 0, review_levels_required: 2, created_at: '2026-01-01T00:00:00Z' },
      { id: 'a2', person_name: '张三', annotation_template: 'cc', review_status: 'approved', created_at: '2026-02-01T00:00:00Z' },
    ]
    const timeline = buildAnnotationTimeline(annotations)
    expect(timeline.map((item) => item.id)).toEqual(['a2', 'a1'])
    expect(timeline[1].statusLabel).toBe('待审核')
    expect(timeline[1].levelText).toBe('第 0/2 级')
  })

  it('属性字段化往返：JSON 语义解析，空键忽略', () => {
    const rowsValue = attributeRowsFromObject({ level: '高', score: 88, tags: ['a'], active: true, extra: null })
    expect(rowsValue).toHaveLength(5)
    const restored = attributeRowsToObject([...rowsValue, { key: '  ', value: 'ignore' }])
    expect(restored).toEqual({ level: '高', score: 88, tags: ['a'], active: true, extra: null })
    expect(parseAttributeValue('[1,2]')).toEqual([1, 2])
    expect(parseAttributeValue('普通文本')).toBe('普通文本')
    expect(parseAttributeValue('{bad')).toBe('{bad')
  })
})

describe('P-08 措施建议', () => {
  it('按维度分组，未分组置末', () => {
    const groups = groupMeasureSuggestions([
      { measure_text: 'A', tag_code: 'behavior:x' },
      { measure_text: 'B' },
      { measure_text: 'C', tag_code: 'service:y' },
    ])
    expect(groups.map((group) => group.dimension)).toEqual(['behavior', 'service', 'uncategorized'])
    expect(groups[2].label).toBe('未分组')
  })

  it('CSV 含表头与转义', () => {
    const csv = measureSuggestionsCsv([{ measure_code: 'M-1', measure_text: '走访,随访', tag_code: 'behavior:x' }])
    expect(csv.split('\r\n')[0]).toBe('维度,措施码,建议内容,标签,来源标签')
    expect(csv).toContain('"走访,随访"')
  })
})
