import { describe, expect, it } from 'vitest'
import {
  buildFieldTagHint,
  dimensionOptionsFromTemplate,
  fieldTagCode,
  fromFieldRows,
  scoringTagCodesFromTemplate,
  toFieldRows,
  validateFieldRows,
  type AnnotationFieldRow,
} from '@/modules/portrait/annotation/fieldSchema'
import type { DpsPortraitTemplate } from '@/core/api/dps'

function row(overrides: Partial<AnnotationFieldRow> = {}): AnnotationFieldRow {
  return {
    key: 'channel',
    type: 'string',
    required: false,
    optionsText: '',
    rangeText: '',
    target_dimension: '',
    ...overrides,
  }
}

const ownerTemplate = {
  code: 'cc-v1',
  dimension_config: {
    dimensions: [
      {
        code: 'service',
        name: '服务维度',
        weight: 0.5,
        rules: [{ key: 'channel', type: 'legacy_map', weight: 1 }],
      },
      { code: 'risk', name: '风险维度', weight: 0.5, rules: [] },
    ],
  },
} as unknown as DpsPortraitTemplate

describe('标注字段设计器模型', () => {
  it('schema 与行模型互转时保留枚举/区间/目标维度', () => {
    const rows = toFieldRows([
      { key: 'channel', type: 'enum', required: true, options: ['线上', '门店'], target_dimension: 'service' },
      { key: 'score', type: 'number', range: [0, 100] },
    ])
    expect(rows[0].optionsText).toBe('线上,门店')
    expect(rows[1].rangeText).toBe('0,100')
    const schema = fromFieldRows(rows)
    expect(schema[0].options).toEqual(['线上', '门店'])
    expect(schema[1].range).toEqual([0, 100])
    expect(schema[0].target_dimension).toBe('service')
  })

  it('校验：字段数为 0、key 缺失/重复、enum 缺 options、区间非法', () => {
    expect(validateFieldRows([])).toContain('至少需要 1 个字段')

    const issues = validateFieldRows([
      row({ key: '' }),
      row({ key: 'a' }),
      row({ key: 'a' }),
      row({ key: 'level', type: 'enum' }),
      row({ key: 'score', type: 'number', rangeText: '100,0' }),
      row({ key: 'amount', type: 'number', rangeText: '0' }),
    ])
    expect(issues).toContain('存在未填写 key 的字段')
    expect(issues).toContain('字段 key 重复：a')
    expect(issues).toContain('字段 level 为 enum 时必须提供 options')
    expect(issues).toContain('字段 score 的 range 下限不得大于上限')
    expect(issues).toContain('字段 amount 的 range 必须是「最小值,最大值」两个数值')
  })

  it('标签编码与提示：命中评分项 / 仅写标签 / 不进画像', () => {
    const scoringTags = scoringTagCodesFromTemplate(ownerTemplate)
    expect([...scoringTags]).toEqual(['service:channel'])
    expect(dimensionOptionsFromTemplate(ownerTemplate).map((item) => item.code)).toEqual(['service', 'risk'])

    expect(fieldTagCode(row({ target_dimension: 'service' }))).toBe('service:channel')
    expect(buildFieldTagHint(row({ target_dimension: 'service' }), scoringTags)).toContain('命中评分项')
    expect(buildFieldTagHint(row({ target_dimension: 'risk' }), scoringTags)).toContain('仅写标签')
    expect(buildFieldTagHint(row(), scoringTags)).toContain('不进画像')
    expect(buildFieldTagHint(row({ key: '', target_dimension: 'service' }), scoringTags)).toContain('填写 key')
  })

  it('字符串形式 dimension_config 也能解析', () => {
    const template = {
      code: 'cc-v2',
      dimension_config: JSON.stringify({ dimensions: [{ code: 'social', name: '社会', rules: [{ tag_code: 'family' }] }] }),
    } as unknown as DpsPortraitTemplate
    expect([...scoringTagCodesFromTemplate(template)]).toEqual(['social:family'])
    expect(dimensionOptionsFromTemplate(template)[0].label).toBe('社会（social）')
  })
})
