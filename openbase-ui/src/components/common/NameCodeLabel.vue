<template>
  <span class="ob-name-code" :class="`ob-name-code--${layout}`">
    <span class="ob-name-code__name" :title="displayName">{{ displayName }}</span>
    <span v-if="showCode" class="ob-name-code__code" :title="code || ''">{{ code }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * 名称 + 编码双行/同行展示：默认主显中文名称，编码以次要样式分开展示。
 * 名称缺失时回退显示编码，避免出现空白。
 */
const props = withDefaults(
  defineProps<{
    name?: string | null
    code?: string | null
    /** inline：同行（下拉选项）；stack：上下两行（表格单元格） */
    layout?: 'inline' | 'stack'
  }>(),
  { layout: 'inline' },
)

const displayName = computed(() => {
  const name = String(props.name ?? '').trim()
  const code = String(props.code ?? '').trim()
  return name || code || '-'
})

const showCode = computed(() => {
  const name = String(props.name ?? '').trim()
  const code = String(props.code ?? '').trim()
  return !!code && !!name && name !== code
})
</script>

<style scoped>
.ob-name-code {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
}

.ob-name-code--stack {
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  vertical-align: top;
}

.ob-name-code__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ob-text-primary, #111827);
}

.ob-name-code__code {
  flex: 0 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ob-text-secondary, #6b7280);
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  line-height: 1.4;
}

.ob-name-code--stack .ob-name-code__name {
  max-width: 100%;
}

.ob-name-code--stack .ob-name-code__code {
  max-width: 100%;
  font-size: 11px;
  color: var(--ob-text-disabled, #9ca3af);
}
</style>
