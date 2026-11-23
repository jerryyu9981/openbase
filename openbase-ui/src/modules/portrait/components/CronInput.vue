<template>
  <div class="cron-input" data-test="cron-input">
    <div class="row">
      <el-input
        :model-value="modelValue"
        placeholder="分 时 日 月 周，例如 0 3 * * *"
        data-test="cron-input-field"
        @update:model-value="onInput"
      />
      <el-button size="small" :loading="loading" data-test="cron-input-preview" @click="preview">
        预览
      </el-button>
    </div>
    <div v-if="error" class="error sm" data-test="cron-input-error">{{ error }}</div>
    <div v-else-if="nextRuns.length" class="preview sm" data-test="cron-input-next">
      未来 {{ nextRuns.length }} 次：{{ nextRuns.map(formatMoment).join(' / ') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { dpsApi } from '@/core/api/dps'
import { describeError } from '@/core/api/error'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()

const nextRuns = ref<string[]>([])
const loading = ref(false)
const error = ref('')

function onInput(value: string) {
  emit('update:modelValue', value)
  nextRuns.value = []
  error.value = ''
}

function formatMoment(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

async function preview() {
  const expr = String(props.modelValue || '').trim()
  if (!expr) {
    error.value = '请先填写 cron 表达式'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const payload = await dpsApi.previewCron(expr, 5)
    nextRuns.value = payload.next_runs || []
  } catch (err) {
    nextRuns.value = []
    error.value = describeError(err).detail || '表达式非法'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.row { display: flex; gap: 8px; align-items: center; }
.preview { color: var(--el-text-color-secondary); margin-top: 4px; }
.error { color: var(--el-color-danger); margin-top: 4px; }
.sm { font-size: 12px; }
</style>
