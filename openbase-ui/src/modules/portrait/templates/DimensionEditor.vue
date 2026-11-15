<template>
  <el-card shadow="never" class="dimension-card" :class="{ 'is-invalid': invalidPaths.has(basePath + '.code') }" data-test="dimension-card">
    <div class="dimension-head">
      <el-input
        :model-value="String(modelValue.code || '')"
        size="small"
        placeholder="维度 code，如 basic"
        class="code-input"
        data-test="dimension-code"
        @update:model-value="(value: string) => patch({ code: value })"
      />
      <el-input
        :model-value="String(modelValue.name || '')"
        size="small"
        placeholder="维度名称，如 基础属性"
        class="name-input"
        data-test="dimension-name"
        @update:model-value="(value: string) => patch({ name: value })"
      />
      <span class="weight-label">权重</span>
      <el-input-number
        :model-value="Number(modelValue.weight ?? 0)"
        :min="0"
        :max="1"
        :step="0.05"
        :precision="2"
        size="small"
        class="weight-input"
        data-test="dimension-weight"
        @update:model-value="(value: number | undefined) => patch({ weight: Number(value ?? 0) })"
      />
      <div class="dimension-actions">
        <el-button link size="small" data-test="dimension-duplicate" @click="emit('duplicate')">复制</el-button>
        <el-button link type="danger" size="small" data-test="dimension-remove" @click="emit('remove')">删除维度</el-button>
      </div>
    </div>

    <div class="rule-list">
      <RuleCardForm
        v-for="(rule, ruleIndex) in rules"
        :key="ruleIndex"
        :model-value="rule"
        :fields="fields"
        :has-error="hasRuleError(ruleIndex)"
        @update:model-value="(value: RuleModel) => updateRule(ruleIndex, value)"
        @remove="removeRule(ruleIndex)"
        @duplicate="duplicateRule(ruleIndex)"
      />
    </div>

    <el-button size="small" type="primary" plain data-test="dimension-add-rule" @click="addRule">＋新增规则</el-button>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import RuleCardForm from './RuleCardForm.vue'
import { newRule, type DimensionModel, type FieldOption, type RuleModel } from './model'

const props = withDefaults(
  defineProps<{
    modelValue: DimensionModel
    index: number
    fields?: FieldOption[]
    invalidPaths?: Set<string>
  }>(),
  { fields: () => [], invalidPaths: () => new Set<string>() },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: DimensionModel): void
  (event: 'remove'): void
  (event: 'duplicate'): void
}>()

const basePath = computed(() => `dimension_config.dimensions[${props.index}]`)
const rules = computed<RuleModel[]>(() => props.modelValue.rules || [])

function patch(changes: Partial<DimensionModel>) {
  emit('update:modelValue', { ...props.modelValue, ...changes })
}

function commitRules(next: RuleModel[]) {
  patch({ rules: next })
}

function hasRuleError(ruleIndex: number): boolean {
  const prefix = `${basePath.value}.rules[${ruleIndex}]`
  return [...props.invalidPaths].some((path) => path === prefix || path.startsWith(`${prefix}.`))
}

function addRule() {
  commitRules([...rules.value, newRule()])
}

function removeRule(ruleIndex: number) {
  const next = [...rules.value]
  next.splice(ruleIndex, 1)
  commitRules(next)
}

function duplicateRule(ruleIndex: number) {
  const source = rules.value[ruleIndex]
  const clone: RuleModel = JSON.parse(JSON.stringify(source || {}))
  clone.key = `${String(source?.key || 'rule')}_copy`
  delete clone.tag_code
  const next = [...rules.value]
  next.splice(ruleIndex + 1, 0, clone)
  commitRules(next)
}

function updateRule(ruleIndex: number, value: RuleModel) {
  const next = [...rules.value]
  next[ruleIndex] = value
  commitRules(next)
}
</script>

<style scoped>
.dimension-card { margin-bottom: 14px; }
.dimension-card.is-invalid { box-shadow: 0 0 0 1px var(--ob-danger) inset; }
.dimension-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.code-input { width: 180px; }
.name-input { width: 200px; }
.weight-label { font-size: 12px; color: var(--ob-text-secondary); }
.weight-input { width: 120px; }
.dimension-actions { display: flex; gap: 4px; margin-left: auto; }
.rule-list { margin-bottom: 8px; }
</style>
