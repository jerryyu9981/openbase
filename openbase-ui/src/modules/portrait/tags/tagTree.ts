import type { DpsTagCategory } from '@/core/api/dps'

/**
 * 标签体系树（P-07）
 *
 * `listLabels` 全量返回、DPS 暂无标签检索/分页（A9），因此前端组装「分类 → 标签值」
 * 两层树并做本地搜索。分类归属优先 `category_id`，兼容旧数据的 `category` 名称。
 */

export interface TagLabelItem {
  name: string
  code?: string
  color?: string
  sort_order?: number
  category?: string
  category_id?: string
  description?: string
  [key: string]: unknown
}

export interface TagTreeNode {
  key: string
  name: string
  kind: 'category' | 'label'
  categoryId?: string
  categoryName?: string
  color?: string
  code?: string
  description?: string
  sortOrder?: number
  children?: TagTreeNode[]
}

export const UNCATEGORIZED_KEY = 'cat:__uncategorized__'

/** 归一化 `listLabels` 原始行：名称兼容 name / value / code */
export function normalizeTagLabel(raw: Record<string, unknown>): TagLabelItem {
  const name = String(raw.name ?? raw.value ?? raw.code ?? raw.tag_code ?? '-')
  const color = raw.color ? String(raw.color) : undefined
  const sortOrder = typeof raw.sort_order === 'number' ? raw.sort_order : Number(raw.sort_order)
  return {
    ...raw,
    name,
    code: raw.code ? String(raw.code) : raw.tag_code ? String(raw.tag_code) : undefined,
    color,
    sort_order: Number.isFinite(sortOrder) ? sortOrder : undefined,
    category: raw.category ? String(raw.category) : undefined,
    category_id: raw.category_id ? String(raw.category_id) : undefined,
    description: raw.description ? String(raw.description) : undefined,
  }
}

function categoryKey(category: DpsTagCategory): string {
  return `cat:${category.id || category.name}`
}

function labelKey(category: string, label: TagLabelItem): string {
  return `label:${category}:${label.name}`
}

function labelNode(categoryKeyValue: string, categoryName: string, categoryId: string | undefined, label: TagLabelItem): TagTreeNode {
  return {
    key: labelKey(categoryKeyValue, label),
    name: label.name,
    kind: 'label',
    categoryId,
    categoryName,
    color: label.color,
    code: label.code,
    description: label.description,
    sortOrder: label.sort_order,
  }
}

function sortLabelNodes(nodes: TagTreeNode[]): TagTreeNode[] {
  return [...nodes].sort((left, right) => {
    const leftOrder = left.sortOrder ?? Number.MAX_SAFE_INTEGER
    const rightOrder = right.sortOrder ?? Number.MAX_SAFE_INTEGER
    if (leftOrder !== rightOrder) return leftOrder - rightOrder
    return left.name.localeCompare(right.name, 'zh-Hans-CN')
  })
}

/**
 * 组装两层树：分类为父节点，标签值为子节点。
 * 未匹配到分类的标签归入「未分类」（仅当存在时展示）。
 */
export function buildTagTree(categories: DpsTagCategory[], labels: TagLabelItem[]): TagTreeNode[] {
  const nodes: TagTreeNode[] = categories.map((category) => ({
    key: categoryKey(category),
    name: category.name || category.id || '未命名分类',
    kind: 'category',
    categoryId: category.id,
    categoryName: category.name,
    code: category.dimension_code || undefined,
    description: category.description,
    children: [] as TagTreeNode[],
  }))
  const byId = new Map<string, TagTreeNode>()
  const byName = new Map<string, TagTreeNode>()
  for (const node of nodes) {
    if (node.categoryId) byId.set(String(node.categoryId), node)
    byName.set(node.name, node)
  }
  const uncategorized: TagLabelItem[] = []
  for (const label of labels) {
    const target =
      (label.category_id ? byId.get(String(label.category_id)) : undefined) ||
      (label.category ? byName.get(label.category) : undefined)
    if (!target) {
      uncategorized.push(label)
      continue
    }
    target.children?.push(labelNode(target.key, target.name, target.categoryId, label))
  }
  for (const node of nodes) {
    node.children = sortLabelNodes(node.children || [])
  }
  if (uncategorized.length) {
    nodes.push({
      key: UNCATEGORIZED_KEY,
      name: '未分类',
      kind: 'category',
      children: sortLabelNodes(
        uncategorized.map((label) => labelNode(UNCATEGORIZED_KEY, '未分类', undefined, label)),
      ),
    })
  }
  return nodes
}

/** 本地搜索：命中分类名保留其全部标签；否则仅保留命中的标签 */
export function filterTagTree(nodes: TagTreeNode[], keyword: string): TagTreeNode[] {
  const trimmed = keyword.trim().toLowerCase()
  if (!trimmed) return nodes
  const result: TagTreeNode[] = []
  for (const node of nodes) {
    const categoryHit =
      node.name.toLowerCase().includes(trimmed) || String(node.code || '').toLowerCase().includes(trimmed)
    if (categoryHit) {
      result.push(node)
      continue
    }
    const children = (node.children || []).filter((child) => {
      return (
        child.name.toLowerCase().includes(trimmed) ||
        String(child.code || '').toLowerCase().includes(trimmed) ||
        String(child.description || '').toLowerCase().includes(trimmed)
      )
    })
    if (children.length) result.push({ ...node, children })
  }
  return result
}

/** 解析标签可反查的 tag_code：优先显式 code，其次「分类:标签值」 */
export function resolveTagCode(node: TagTreeNode | null): string {
  if (!node || node.kind !== 'label') return ''
  if (node.code) return node.code
  if (node.categoryName) return `${node.categoryName}:${node.name}`
  return node.name
}
