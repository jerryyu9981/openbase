<template>
  <div class="ob-mapping-table">
    <el-table :data="rows" size="small" border>
      <el-table-column label="源字段" min-width="180">
        <template #default="{ row }">
          <el-select
            v-model="row.source"
            filterable
            allow-create
            placeholder="选择或输入源字段"
            style="width: 100%"
            @change="sync"
          >
            <el-option v-for="column in sampleColumns" :key="column" :label="column" :value="column" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="目标字段" min-width="180">
        <template #default="{ row }">
          <el-input v-model="row.target" placeholder="如 person_id / name / attributes.phone" @change="sync" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removeRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="ob-mapping-table__actions">
      <el-button size="small" @click="addRow">新增映射</el-button>
      <span class="ob-mapping-table__hint">
        未配置映射时按源字段同名写入；`person_id` 为必填字段。
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

/**
 * 字段映射表（波次 B / B-09）
 *
 * `modelValue` 为 `{源字段: 目标字段}`；组件内部维护可编辑行，变更即回传。
 */
const props = withDefaults(
  defineProps<{
    modelValue?: Record<string, string>
    sampleColumns?: string[]
  }>(),
  {
    modelValue: () => ({}),
    sampleColumns: () => [],
  },
)

const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, string>): void }>()

interface MappingRow {
  source: string
  target: string
}

const rows = ref<MappingRow[]>(
  Object.entries(props.modelValue || {}).map(([source, target]) => ({ source, target })),
)

watch(
  () => props.modelValue,
  (value) => {
    rows.value = Object.entries(value || {}).map(([source, target]) => ({ source, target }))
  },
)

function sync(): void {
  const mapping: Record<string, string> = {}
  for (const row of rows.value) {
    if (row.source && row.target) mapping[row.source] = row.target
  }
  emit('update:modelValue', mapping)
}

function addRow(): void {
  rows.value = [...rows.value, { source: '', target: '' }]
}

function removeRow(index: number): void {
  rows.value = rows.value.filter((_, rowIndex) => rowIndex !== index)
  sync()
}
</script>

<style scoped>
.ob-mapping-table__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.ob-mapping-table__hint {
  color: var(--ob-text-secondary, #6b7280);
  font-size: 12px;
}
</style>
