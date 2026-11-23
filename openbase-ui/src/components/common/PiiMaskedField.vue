<template>
  <span class="ob-pii-masked-field" :data-test="props.testId || 'pii-masked-field'">
    <span class="ob-pii-masked-field__value">{{ displayValue }}</span>
    <el-tooltip v-if="isMasked" :content="hint" placement="top">
      <el-tag size="small" type="warning" effect="plain" class="ob-pii-masked-field__tag">
        已脱敏
      </el-tag>
    </el-tooltip>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * PII 掩码字段（波次 B / B-10）
 *
 * 前端只展示后端已脱敏的值，不做本地还原、不缓存明文。
 * `masked` 由接口返回或字段分级判定；`level` 用于提示申请的审批级别。
 */
const props = defineProps<{
  value?: unknown
  masked?: boolean
  level?: string | number
  testId?: string
}>()

const isMasked = computed(() => Boolean(props.masked))

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') return '—'
  return String(props.value)
})

const hint = computed(
  () =>
    `该字段属于 ${String(props.level ?? 'L3')} 敏感级，需「敏感字段查看」权限（dps:pii:view）方可查看明文`,
)
</script>

<style scoped>
.ob-pii-masked-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ob-pii-masked-field__tag {
  cursor: help;
}
</style>
