/**
 * 通用异步状态（加载／错误／空态）——OpenBase v1.4.10 §3.2 共享逻辑抽取。
 *
 * 设计约束（ADR-05）：页面状态由**组合式函数**承载，**不引入新全局 store**；
 * 每次进入页面重新拉取，不引入前端缓存层（避免与后端口径分叉）。
 *
 * 错误归一复用 `describeDpsError`（通用 8 态 ＋ DPS 专项 `hint`），
 * 使 12 个 DPS 页面按统一 `kind` 渲染空态／错误态／未启用态。
 */
import { ref, type Ref } from 'vue'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

export interface AsyncState<T> {
  /** 最近一次成功的数据（失败时置空） */
  data: Ref<T | null>
  /** 请求进行中 */
  loading: Ref<boolean>
  /** 归一后的错误呈现模型（无错误为 null） */
  error: Ref<DpsErrorPresentation | null>
  /** 是否为空态（依 `isEmpty` 判据；非错误态） */
  isEmpty: Ref<boolean>
  /** 执行异步任务；成功返回结果、失败返回 null（错误已写入 `error`） */
  run: (task: () => Promise<T>) => Promise<T | null>
  /** 复位全部状态 */
  reset: () => void
}

/**
 * 默认空态判据：
 * - null／undefined → 空；
 * - 数组长度为 0 → 空；
 * - 分页结构 `{ items: [] }` → 空。
 */
export function defaultIsEmpty<T>(value: T | null): boolean {
  if (value === null || value === undefined) return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object' && 'items' in (value as Record<string, unknown>)) {
    const items = (value as { items?: unknown }).items
    return Array.isArray(items) && items.length === 0
  }
  return false
}

/**
 * @param isEmptyCheck 自定义空态判据（缺省见 {@link defaultIsEmpty}）
 */
export function useAsyncState<T>(isEmptyCheck: (value: T) => boolean = defaultIsEmpty): AsyncState<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref<DpsErrorPresentation | null>(null)
  const isEmpty = ref(false)

  async function run(task: () => Promise<T>): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      const result = await task()
      data.value = result
      isEmpty.value = isEmptyCheck(result)
      return result
    } catch (caught) {
      data.value = null
      isEmpty.value = false
      error.value = describeDpsError(caught)
      return null
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    data.value = null
    loading.value = false
    error.value = null
    isEmpty.value = false
  }

  return { data, loading, error, isEmpty, run, reset }
}
