/** DPS 模板版本号展示：后端返回值已带 `v` 前缀（如 `v1`/`v2`），此处避免重复拼接成 `vv1`。 */
export function formatVersion(value: unknown, fallback = '-'): string {
  if (value === null || value === undefined || value === '') return fallback
  const text = String(value)
  return /^v/i.test(text) ? text : `v${text}`
}
