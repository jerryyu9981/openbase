import type { DpsLineageScoringHit, DpsLineageSource, DpsTemplateLineage } from '@/core/api/dps'

/**
 * 标签血缘链路（P-07）
 *
 * DPS `GET /portrait/lineage/{tag_code}` 只返回标注来源（template_code/annotation_id），
 * 不直接给出「标注模板 → 字段 → 标签 → 评分项」链路；本模块用
 * `getTemplateLineage(template_code)` 的结果按 tag_code 反查字段与评分命中，
 * 组成可逐节点跳转的链路。模板血缘拉取失败时标记 `missingField`，不以空链冒充完整链路。
 */

export interface TagChainFieldNode {
  annotationTemplate: string
  annotationTemplateName?: string
  fieldKey: string
  fieldLabel: string
  tagKey?: string
  scoringHits: DpsLineageScoringHit[]
}

export interface TagChainGroup {
  templateCode: string
  templateName?: string
  sources: DpsLineageSource[]
  fields: TagChainFieldNode[]
  /** 未找到产出该标签的字段（血缘缺口，需治理） */
  missingField: boolean
}

/** 字段是否产出该标签：优先 tag_code 精确匹配，其次 tag_key 与 tag_code 后缀匹配 */
export function tagFieldMatches(
  tagCode: string,
  field: { tag_code?: string | null; tag_key?: string | null },
): boolean {
  const target = tagCode.trim()
  if (!target) return false
  if (field.tag_code && field.tag_code === target) return true
  const suffix = target.includes(':') ? target.slice(target.indexOf(':') + 1) : target
  return !!field.tag_key && (field.tag_key === target || field.tag_key === suffix)
}

/**
 * 按来源模板分组构建链路。
 * @param sources 血缘来源（同 tag_code）
 * @param lineages 已拉取的模板血缘（`getTemplateLineage` 结果，可缺失/为 null）
 */
export function buildTagChainGroups(
  tagCode: string,
  sources: DpsLineageSource[],
  lineages: Array<DpsTemplateLineage | null | undefined>,
): TagChainGroup[] {
  const sourceGroups = new Map<string, DpsLineageSource[]>()
  for (const source of sources) {
    const code = String(source.template_code || '').trim() || '（未知模板）'
    const list = sourceGroups.get(code) || []
    list.push(source)
    sourceGroups.set(code, list)
  }
  const lineageByCode = new Map<string, DpsTemplateLineage>()
  for (const lineage of lineages) {
    if (lineage?.template_code) lineageByCode.set(lineage.template_code, lineage)
  }
  const groups: TagChainGroup[] = []
  for (const [templateCode, groupSources] of sourceGroups) {
    const lineage = lineageByCode.get(templateCode)
    const fields: TagChainFieldNode[] = []
    for (const annotationTemplate of lineage?.annotation_templates || []) {
      for (const field of annotationTemplate.fields || []) {
        if (!tagFieldMatches(tagCode, field)) continue
        fields.push({
          annotationTemplate: annotationTemplate.code,
          annotationTemplateName: annotationTemplate.name,
          fieldKey: field.key,
          fieldLabel: field.label || field.key,
          tagKey: field.tag_key || undefined,
          scoringHits: field.affects_scoring || [],
        })
      }
    }
    groups.push({
      templateCode,
      templateName: lineage?.name,
      sources: groupSources,
      fields,
      missingField: !lineage || fields.length === 0,
    })
  }
  return groups
}

/** 汇总链路中的评分项（去重：维度 + 规则 key） */
export function collectScoringHits(groups: TagChainGroup[]): DpsLineageScoringHit[] {
  const seen = new Set<string>()
  const result: DpsLineageScoringHit[] = []
  for (const group of groups) {
    for (const field of group.fields) {
      for (const hit of field.scoringHits) {
        const key = `${hit.dimension}:${hit.rule_key}`
        if (seen.has(key)) continue
        seen.add(key)
        result.push(hit)
      }
    }
  }
  return result
}
