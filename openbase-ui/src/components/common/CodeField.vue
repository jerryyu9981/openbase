<template>
  <div class="ob-code-field">
    <el-input
      :model-value="modelValue"
      :disabled="disabled"
      :placeholder="placeholder"
      style="width: 320px"
      :data-test="testId"
      @update:model-value="onInput"
    >
      <template #append>
        <el-button :disabled="disabled || !canGenerate" @click="onGenerate">由名称生成</el-button>
      </template>
    </el-input>
    <div class="ob-code-field__hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCodeFromName } from '@/core/composables/useCodeFromName'

/**
 * 编码输入（波次 A / A-05）：中文名称主显，编码可留空。
 * - 可确定的 ASCII 名称：提供「由名称生成」一键填充；
 * - 中文名称：提示留空，由服务端按拼音生成（创建后不可修改）。
 */
const props = withDefaults(
  defineProps<{
    modelValue: string
    /** 同表单的中文名称，用于生成候选编码 */
    name?: string
    disabled?: boolean
    placeholder?: string
    testId?: string
  }>(),
  {
    name: '',
    disabled: false,
    placeholder: '可留空，如 cc-persona-v1',
    testId: 'code-field',
  },
)

const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()

const { suggested, canGenerate } = useCodeFromName(() => props.name)

const hint = computed(() => {
  if (props.disabled) return '创建后不可修改'
  if (canGenerate.value) return `将生成：${suggested.value}`
  return '可留空：由服务端按中文名生成，创建后不可修改'
})

function onInput(value: string): void {
  emit('update:modelValue', value)
}

function onGenerate(): void {
  if (canGenerate.value) emit('update:modelValue', suggested.value)
}
</script>

<style scoped>
.ob-code-field {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
}

.ob-code-field__hint {
  color: var(--ob-text-secondary, #6b7280);
  font-size: 12px;
  line-height: 1.4;
}
</style>
