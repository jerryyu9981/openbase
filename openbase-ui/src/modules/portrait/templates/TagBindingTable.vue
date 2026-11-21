<template>
  <div data-test="tag-binding-table">
    <el-alert type="info" show-icon :closable="false" class="mb-12">
      <template #title>标签绑定：标注模板 → 目标维度（运行态按此把审核通过的标注联动为维度标签）</template>
      <div>同一标注模板重复绑定会提示冲突；未识别的扩展键（如优先级）在保存时原样保留。</div>
    </el-alert>

    <div class="ob-table-scroll">
      <el-table :data="modelValue" stripe empty-text="暂无绑定" data-test="binding-table">
        <el-table-column label="标注模板" min-width="240">
          <template #default="{ row, $index }">
            <el-select
              :model-value="String(row.annotation_template || '')"
              size="small"
              filterable
              allow-create
              default-first-option
              placeholder="选择/输入标注模板"
              data-test="binding-annotation-template"
              @update:model-value="(value: string) => patchRow($index, { annotation_template: String(value || '') })"
            >
              <el-option
                v-for="item in annotationTemplates"
                :key="item.code"
                :label="item.name || item.code"
                :value="item.code"
              >
                <NameCodeLabel :name="item.name" :code="item.code" />
              </el-option>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="绑定维度" min-width="260">
          <template #default="{ row, $index }">
            <el-select
              :model-value="Array.isArray(row.dimensions) ? row.dimensions : []"
              size="small"
              multiple
              filterable
              allow-create
              default-first-option
              collapse-tags
              placeholder="选择维度 code"
              data-test="binding-dimensions"
              @update:model-value="(value: string[]) => patchRow($index, { dimensions: value })"
            >
              <el-option v-for="code in dimensionCodes" :key="code" :label="code" :value="code" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" data-test="binding-remove" @click="removeRow($index)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无绑定" :image-size="60" />
        </template>
      </el-table>
    </div>

    <el-button size="small" type="primary" plain class="mt-8" data-test="binding-add" @click="addRow">＋新增绑定</el-button>
  </div>
</template>

<script setup lang="ts">
import { newBinding, type BindingModel } from './model'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'

const props = withDefaults(
  defineProps<{
    modelValue: BindingModel[]
    dimensionCodes?: string[]
    annotationTemplates?: Array<{ code: string; name?: string }>
  }>(),
  { dimensionCodes: () => [], annotationTemplates: () => [] },
)

const emit = defineEmits<{ (event: 'update:modelValue', value: BindingModel[]): void }>()

function patchRow(index: number, changes: Partial<BindingModel>) {
  // 原行上的扩展键通过 `...row` 保留
  const next = props.modelValue.map((row, position) => (position === index ? { ...row, ...changes } : row))
  emit('update:modelValue', next)
}

function addRow() {
  emit('update:modelValue', [...props.modelValue, newBinding()])
}

function removeRow(index: number) {
  const next = [...props.modelValue]
  next.splice(index, 1)
  emit('update:modelValue', next)
}
</script>

<style scoped>
.mb-12 { margin-bottom: 12px; }
.mt-8 { margin-top: 8px; }
</style>
