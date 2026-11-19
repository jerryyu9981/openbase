import { computed, ref } from 'vue'

/**
 * DPS 通用列表规范（设计文档 §8.1）
 *
 * 统一承载三类本地能力，供标注作业台 / 审核收件箱共用：
 * - 保存视图：筛选条件持久化到 `dps.view.{pageKey}`；
 * - 列设置：显示/隐藏持久化到 `dps.columns.{pageKey}`；
 * - 跨页选择：本页选择的记录 id 集合（配合表格 `reserve-selection`）。
 *
 * 仅做本地持久化，不承担服务端筛选；筛选条件仍由调用方回写路由 query。
 */

export interface DpsSavedView {
  id: string
  name: string
  filters: Record<string, string>
  saved_at: number
}

export interface DpsColumnOption {
  key: string
  label: string
  visible: boolean
}

interface DpsListViewOptions {
  /** 页面标识：用于生成 localStorage 键，如 `annotations-review` */
  pageKey: string
  columns: Array<{ key: string; label: string }>
  /** 默认隐藏的列 key */
  hiddenByDefault?: string[]
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function writeJson(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // 存储不可用（隐私模式/配额）时静默降级，不影响筛选与选择
  }
}

export function useDpsListView(options: DpsListViewOptions) {
  const viewsKey = `dps.view.${options.pageKey}`
  const columnsKey = `dps.columns.${options.pageKey}`

  const savedViews = ref<DpsSavedView[]>(readJson<DpsSavedView[]>(viewsKey, []))
  const columns = ref<DpsColumnOption[]>(
    readJson<DpsColumnOption[]>(
      columnsKey,
      options.columns.map((column) => ({
        ...column,
        visible: !(options.hiddenByDefault || []).includes(column.key),
      })),
    ),
  )
  const activeViewId = ref('')
  const selection = ref<string[]>([])

  const selectedCount = computed(() => selection.value.length)
  const visibleColumnKeys = computed(() =>
    columns.value.filter((column) => column.visible).map((column) => column.key),
  )

  function persistViews() {
    writeJson(viewsKey, savedViews.value)
  }

  function persistColumns() {
    writeJson(columnsKey, columns.value)
  }

  /** 同名视图覆盖更新，避免重复条目 */
  function saveView(name: string, filters: Record<string, string>): DpsSavedView {
    const trimmed = name.trim()
    const existing = savedViews.value.find((view) => view.name === trimmed)
    const next: DpsSavedView = {
      id: existing?.id || `view-${Date.now()}`,
      name: trimmed,
      filters: { ...filters },
      saved_at: Date.now(),
    }
    savedViews.value = existing
      ? savedViews.value.map((view) => (view.id === existing.id ? next : view))
      : [...savedViews.value, next]
    activeViewId.value = next.id
    persistViews()
    return next
  }

  function removeView(id: string) {
    savedViews.value = savedViews.value.filter((view) => view.id !== id)
    if (activeViewId.value === id) activeViewId.value = ''
    persistViews()
  }

  /** 应用保存视图，返回其筛选条件（空视图返回 null） */
  function applyView(id: string): Record<string, string> | null {
    const view = savedViews.value.find((item) => item.id === id)
    if (!view) return null
    activeViewId.value = id
    return { ...view.filters }
  }

  function toggleColumn(key: string) {
    columns.value = columns.value.map((column) =>
      column.key === key ? { ...column, visible: !column.visible } : column,
    )
    persistColumns()
  }

  function columnVisible(key: string): boolean {
    return columns.value.find((column) => column.key === key)?.visible !== false
  }

  function setSelection(ids: string[]) {
    selection.value = Array.from(new Set(ids))
  }

  function clearSelection() {
    selection.value = []
  }

  function isSelected(id: string): boolean {
    return selection.value.includes(id)
  }

  return {
    savedViews,
    activeViewId,
    saveView,
    removeView,
    applyView,
    columns,
    visibleColumnKeys,
    toggleColumn,
    columnVisible,
    selection,
    selectedCount,
    setSelection,
    clearSelection,
    isSelected,
  }
}
