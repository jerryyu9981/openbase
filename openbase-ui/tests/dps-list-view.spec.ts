import { beforeEach, describe, expect, it } from 'vitest'
import { useDpsListView } from '@/modules/portrait/composables/useDpsListView'

/**
 * DPS 通用列表规范（设计文档 §8.1）：
 * 保存视图、列设置、跨页选择均为本地能力，需保证持久化与损坏数据降级。
 */
describe('useDpsListView', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('保存视图：同名覆盖、按 id 应用、持久化可重载', () => {
    const first = useDpsListView({
      pageKey: 'unit-annotations',
      columns: [{ key: 'person', label: '主体' }],
    })
    const saved = first.saveView('我的待初审', { status: 'pending', template: 'T-1' })
    expect(first.savedViews.value).toHaveLength(1)
    expect(first.activeViewId.value).toBe(saved.id)
    expect(first.applyView(saved.id)).toEqual({ status: 'pending', template: 'T-1' })

    first.saveView('我的待初审', { status: 'all', template: '' })
    expect(first.savedViews.value).toHaveLength(1)
    expect(localStorage.getItem('dps.view.unit-annotations')).toContain('"all"')

    const reloaded = useDpsListView({
      pageKey: 'unit-annotations',
      columns: [{ key: 'person', label: '主体' }],
    })
    expect(reloaded.savedViews.value).toHaveLength(1)
    expect(reloaded.applyView(reloaded.savedViews.value[0].id)).toEqual({ status: 'all', template: '' })
  })

  it('删除视图后不再命中', () => {
    const view = useDpsListView({ pageKey: 'unit-delete', columns: [] })
    const saved = view.saveView('临时视图', { status: 'rejected' })
    view.removeView(saved.id)
    expect(view.savedViews.value).toEqual([])
    expect(view.applyView(saved.id)).toBeNull()
  })

  it('列设置：默认隐藏项、切换后持久化', () => {
    const view = useDpsListView({
      pageKey: 'unit-columns',
      columns: [
        { key: 'person', label: '主体' },
        { key: 'created', label: '提交时间' },
      ],
      hiddenByDefault: ['created'],
    })
    expect(view.columnVisible('person')).toBe(true)
    expect(view.columnVisible('created')).toBe(false)

    view.toggleColumn('created')
    expect(view.columnVisible('created')).toBe(true)

    const reloaded = useDpsListView({
      pageKey: 'unit-columns',
      columns: [
        { key: 'person', label: '主体' },
        { key: 'created', label: '提交时间' },
      ],
      hiddenByDefault: ['created'],
    })
    expect(reloaded.columnVisible('created')).toBe(true)
  })

  it('跨页选择：去重、计数与清空', () => {
    const view = useDpsListView({ pageKey: 'unit-selection', columns: [] })
    view.setSelection(['a', 'b', 'a'])
    expect(view.selection.value).toEqual(['a', 'b'])
    expect(view.selectedCount.value).toBe(2)
    expect(view.isSelected('b')).toBe(true)

    view.setSelection(['b', 'c'])
    expect(view.selection.value).toEqual(['b', 'c'])
    view.clearSelection()
    expect(view.selectedCount.value).toBe(0)
  })

  it('损坏的本地存储回退到默认列与空视图', () => {
    localStorage.setItem('dps.view.unit-broken', '{not-json')
    localStorage.setItem('dps.columns.unit-broken', '{not-json')
    const view = useDpsListView({
      pageKey: 'unit-broken',
      columns: [{ key: 'person', label: '主体' }],
    })
    expect(view.savedViews.value).toEqual([])
    expect(view.columnVisible('person')).toBe(true)
  })
})
