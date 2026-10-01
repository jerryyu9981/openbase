/**
 * `basis` 口径折叠控件状态（ADR-06）——OpenBase v1.4.10 §3.2。
 *
 * 规范（UI 设计文档 §4.2）：
 * - **默认收起**（仅显示三项指标）；
 * - 展开控件须维护 `aria-expanded`；
 * - **强制展开场景**：`tag_count = 0`（避免误判为缺陷），强制展开时不可手动收起；
 * - 键盘可达（Tab ＋ Enter／Space 由触发按钮承载）。
 */
import { computed, ref, type ComputedRef, type Ref } from 'vue'

export interface BasisTooltip {
  /** 用户手动展开态（强制展开时保持 false，但 `isExpanded` 仍为 true） */
  expanded: Ref<boolean>
  /** 是否处于强制展开（如 `tag_count = 0`） */
  isForced: ComputedRef<boolean>
  /** 实际展开态（手动 ∨ 强制） */
  isExpanded: ComputedRef<boolean>
  /** 无障碍属性值（'true' / 'false'） */
  ariaExpanded: ComputedRef<'true' | 'false'>
  /** 切换展开（强制展开时为空操作） */
  toggle: () => void
  /** 展开 */
  expand: () => void
  /** 收起（强制展开时为空操作） */
  collapse: () => void
}

/**
 * @param forceExpand 强制展开判据（响应式；缺省恒 false）
 */
export function useBasisTooltip(forceExpand: () => boolean = () => false): BasisTooltip {
  const expanded = ref(false)
  const isForced = computed(() => forceExpand())
  const isExpanded = computed(() => expanded.value || isForced.value)
  const ariaExpanded = computed<'true' | 'false'>(() => (isExpanded.value ? 'true' : 'false'))

  function toggle(): void {
    if (isForced.value) return
    expanded.value = !expanded.value
  }

  function expand(): void {
    expanded.value = true
  }

  function collapse(): void {
    if (!isForced.value) expanded.value = false
  }

  return { expanded, isForced, isExpanded, ariaExpanded, toggle, expand, collapse }
}
