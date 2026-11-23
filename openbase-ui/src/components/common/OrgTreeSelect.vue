<template>
  <el-tree-select
    :model-value="modelValue"
    :data="treeData"
    :placeholder="placeholder"
    :clearable="clearable"
    check-strictly
    node-key="code"
    :props="{ label: 'label', children: 'children' }"
    style="width: 220px"
    data-test="org-tree-select"
    @update:model-value="onChange"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DpsOrgNode } from '@/core/api/dps'

/**
 * 组织树选择（波次 B / B-10）
 *
 * 选项编码为用户可读的组织名；值仍为 `code`（不把内部 ID 暴露到查询参数）。
 */
const props = withDefaults(
  defineProps<{
    modelValue?: string
    orgs?: DpsOrgNode[]
    placeholder?: string
    clearable?: boolean
  }>(),
  {
    modelValue: '',
    orgs: () => [],
    placeholder: '全部组织',
    clearable: true,
  },
)

const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()

interface OrgOption {
  code: string
  label: string
  children: OrgOption[]
}

function toOption(node: DpsOrgNode): OrgOption {
  return {
    code: node.code,
    label: node.name ? `${node.name}（${node.code}）` : node.code,
    children: (node.children || []).map(toOption),
  }
}

const treeData = computed<OrgOption[]>(() => (props.orgs || []).map(toOption))

function onChange(value: unknown): void {
  emit('update:modelValue', typeof value === 'string' ? value : '')
}
</script>
