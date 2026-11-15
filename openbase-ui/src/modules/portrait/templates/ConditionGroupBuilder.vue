<template>
  <div class="condition-group" :class="`depth-${depth}`" data-test="condition-group">
    <div class="group-head">
      <el-radio-group v-model="groupKind" size="small" data-test="condition-kind">
        <el-radio-button value="all">且（全部满足）</el-radio-button>
        <el-radio-button value="any">或（任一满足）</el-radio-button>
      </el-radio-group>
      <span class="expr" data-test="condition-expression">{{ describeCondition(modelValue) }}</span>
      <div class="group-actions">
        <el-button size="small" data-test="condition-add-leaf" @click="addLeaf">＋条件</el-button>
        <el-button v-if="depth < CONDITION_MAX_DEPTH" size="small" data-test="condition-add-group" @click="addGroup">＋条件组</el-button>
      </div>
    </div>

    <div v-for="(node, index) in children" :key="index" class="node-row">
      <template v-if="isConditionGroup(node)">
        <ConditionGroupBuilder
          :model-value="node as ConditionGroup"
          :fields="fields"
          :depth="depth + 1"
          @update:model-value="(next: ConditionGroup) => replaceNode(index, next)"
          @remove="removeNode(index)"
        />
      </template>
      <template v-else>
        <el-select
          :model-value="(node as ConditionLeaf).field"
          filterable
          allow-create
          default-first-option
          placeholder="字段 / 标签 key"
          size="small"
          class="field-select"
          data-test="condition-field"
          @update:model-value="(value: string) => updateLeaf(index, { field: String(value || '') })"
        >
          <el-option v-for="option in fields" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-select
          :model-value="(node as ConditionLeaf).op"
          size="small"
          class="op-select"
          data-test="condition-op"
          @update:model-value="(value: string) => updateLeaf(index, { op: String(value) })"
        >
          <el-option v-for="item in OPERATORS" :key="item.op" :label="item.label" :value="item.op" />
        </el-select>
        <template v-if="!NO_VALUE_OPS.includes((node as ConditionLeaf).op)">
          <el-select
            v-if="ARRAY_VALUE_OPS.includes((node as ConditionLeaf).op) && (node as ConditionLeaf).op !== 'between'"
            :model-value="asArray((node as ConditionLeaf).value)"
            multiple
            filterable
            allow-create
            default-first-option
            collapse-tags
            placeholder="多个取值（回车新增）"
            size="small"
            class="value-select"
            data-test="condition-value-array"
            @update:model-value="(value: string[]) => updateLeaf(index, { value })"
          />
          <div v-else-if="(node as ConditionLeaf).op === 'between'" class="between">
            <el-input
              :model-value="String(asArray((node as ConditionLeaf).value)[0] ?? '')"
              size="small"
              placeholder="下限"
              data-test="condition-value-low"
              @update:model-value="(value: string) => updateBetween(index, 0, value)"
            />
            <span class="between-sep">~</span>
            <el-input
              :model-value="String(asArray((node as ConditionLeaf).value)[1] ?? '')"
              size="small"
              placeholder="上限"
              data-test="condition-value-high"
              @update:model-value="(value: string) => updateBetween(index, 1, value)"
            />
          </div>
          <el-input
            v-else
            :model-value="String((node as ConditionLeaf).value ?? '')"
            size="small"
            placeholder="取值"
            class="value-input"
            data-test="condition-value"
            @update:model-value="(value: string) => updateLeaf(index, { value })"
          />
        </template>
      </template>
      <el-button link type="danger" size="small" data-test="condition-remove-node" @click="removeNode(index)">删除</el-button>
    </div>

    <div v-if="!children.length" class="empty-hint">暂无条件，请点击「＋条件」</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  ARRAY_VALUE_OPS,
  CONDITION_MAX_DEPTH,
  NO_VALUE_OPS,
  OPERATORS,
  describeCondition,
  isConditionGroup,
  newConditionGroup,
  newConditionLeaf,
  type ConditionGroup,
  type ConditionLeaf,
  type ConditionNode,
  type FieldOption,
} from './model'

defineOptions({ name: 'ConditionGroupBuilder' })

const props = withDefaults(
  defineProps<{
    modelValue: ConditionGroup
    fields?: FieldOption[]
    depth?: number
  }>(),
  { fields: () => [], depth: 0 },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: ConditionGroup): void
  (event: 'remove'): void
}>()

const depth = computed(() => props.depth)
const children = computed<ConditionNode[]>(() => {
  const key: 'all' | 'any' = 'all' in props.modelValue ? 'all' : 'any'
  return props.modelValue[key] || []
})
const groupKind = computed<'all' | 'any'>({
  get: () => ('all' in props.modelValue ? 'all' : 'any'),
  set: (kind) => {
    emit('update:modelValue', { [kind]: children.value })
  },
})

function commit(next: ConditionNode[]) {
  const key: 'all' | 'any' = 'all' in props.modelValue ? 'all' : 'any'
  emit('update:modelValue', { [key]: next })
}

function addLeaf() {
  commit([...children.value, newConditionLeaf()])
}

function addGroup() {
  commit([...children.value, newConditionGroup('all')])
}

function removeNode(index: number) {
  const next = [...children.value]
  next.splice(index, 1)
  if (!next.length) {
    emit('remove')
    return
  }
  commit(next)
}

function replaceNode(index: number, node: ConditionNode) {
  const next = [...children.value]
  next[index] = node
  commit(next)
}

function updateLeaf(index: number, patch: Partial<ConditionLeaf>) {
  const current = children.value[index] as ConditionLeaf
  replaceNode(index, { ...current, ...patch })
}

function updateBetween(index: number, position: number, raw: string) {
  const current = children.value[index] as ConditionLeaf
  const values = asArray(current.value).slice(0, 2)
  values[position] = raw
  updateLeaf(index, { value: values })
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}
</script>

<style scoped>
.condition-group {
  border: 1px solid var(--ob-border);
  border-radius: 6px;
  padding: 10px;
  background: var(--ob-bg-subtle, rgba(0, 0, 0, 0.01));
}
.condition-group.depth-0 { background: transparent; }
.group-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.expr { color: var(--ob-text-secondary); font-size: 12px; flex: 1 1 220px; }
.group-actions { display: flex; gap: 6px; }
.node-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
.field-select { width: 220px; }
.op-select { width: 120px; }
.value-input, .value-select { width: 200px; }
.between { display: flex; align-items: center; gap: 6px; }
.between-sep { color: var(--ob-text-secondary); }
.empty-hint { color: var(--ob-text-disabled); font-size: 12px; margin-top: 8px; }
</style>
