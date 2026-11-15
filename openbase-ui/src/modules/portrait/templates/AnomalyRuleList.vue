<template>
  <div data-test="anomaly-rule-list">
    <el-alert type="info" show-icon :closable="false" class="mb-12">
      <template #title>异常规则：触发条件 + 严重级别 + 处置动作（运行态按规则名逐条评估）</template>
      <div>条件支持文本表达式（如 <code>psychology:crisis_level == '紧急'</code>）；结构化条件组以只读 JSON 呈现。</div>
    </el-alert>

    <div class="preset-row">
      <span class="muted sm">内置模板：</span>
      <el-button v-for="preset in PRESETS" :key="preset.name" size="small" data-test="anomaly-preset" @click="applyPreset(preset)">
        {{ preset.label }}
      </el-button>
    </div>

    <el-card v-for="(rule, name, index) in rules" :key="String(name) + index" shadow="never" class="rule-card" data-test="anomaly-rule">
      <div class="rule-head">
        <el-input :model-value="String(name)" size="small" class="name-input" placeholder="规则名，如 crisis_alert" data-test="anomaly-name" @update:model-value="(value: string) => renameRule(String(name), value)" />
        <el-select :model-value="String(rule.severity || 'warn')" size="small" class="severity-select" data-test="anomaly-severity" @update:model-value="(value: string) => patchRule(String(name), { severity: String(value) })">
          <el-option label="提示 info" value="info" />
          <el-option label="警告 warn" value="warn" />
          <el-option label="严重 error" value="error" />
        </el-select>
        <el-button link type="danger" size="small" data-test="anomaly-remove" @click="removeRule(String(name))">删除</el-button>
      </div>
      <div class="rule-body">
        <template v-if="isPlainObject(rule.condition)">
          <div class="muted sm">结构化条件组（只读）：</div>
          <pre class="json-view">{{ JSON.stringify(rule.condition, null, 2) }}</pre>
        </template>
        <el-input
          v-else
          :model-value="String(rule.condition || '')"
          size="small"
          placeholder="触发条件，如 behavior 定位越界记录 > 0"
          data-test="anomaly-condition"
          @update:model-value="(value: string) => patchRule(String(name), { condition: value })"
        />
        <el-input
          :model-value="String(rule.action || '')"
          size="small"
          placeholder="处置动作，如 1 小时内触发预警并转介"
          data-test="anomaly-action"
          @update:model-value="(value: string) => patchRule(String(name), { action: value })"
        />
      </div>
    </el-card>

    <el-button size="small" type="primary" plain data-test="anomaly-add" @click="addRule">＋新增异常规则</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isPlainObject, type AnomalyRuleModel } from './model'

const props = defineProps<{ modelValue: Record<string, AnomalyRuleModel> }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, AnomalyRuleModel>): void }>()

const PRESETS = [
  { label: '缺失率过高', name: 'missing_rate', rule: { condition: 'missing_rate > 0.2', action: '阻断画像发布并提示补录', severity: 'error' } },
  { label: '权重越界', name: 'weight_out_of_range', rule: { condition: 'dimension.weight > 1', action: '标记模板并拒绝激活', severity: 'warn' } },
  { label: '标签冲突', name: 'tag_conflict', rule: { condition: 'conflict_tags.length > 0', action: '转人工复核并冻结自动标注', severity: 'warn' } },
]

const rules = computed(() => props.modelValue || {})

function commit(next: Record<string, AnomalyRuleModel>) {
  emit('update:modelValue', next)
}

function renameRule(oldName: string, newName: string) {
  if (!newName.trim() || newName === oldName) return
  const next: Record<string, AnomalyRuleModel> = {}
  for (const [name, rule] of Object.entries(props.modelValue || {})) {
    next[name === oldName ? newName : name] = rule
  }
  commit(next)
}

function patchRule(name: string, changes: Partial<AnomalyRuleModel>) {
  commit({ ...(props.modelValue || {}), [name]: { ...(props.modelValue?.[name] || {}), ...changes } })
}

function removeRule(name: string) {
  const next: Record<string, AnomalyRuleModel> = { ...(props.modelValue || {}) }
  delete next[name]
  commit(next)
}

function addRule() {
  const name = `rule_${Object.keys(props.modelValue || {}).length + 1}`
  commit({ ...(props.modelValue || {}), [name]: { condition: '', action: '', severity: 'warn' } })
}

function applyPreset(preset: (typeof PRESETS)[number]) {
  commit({ ...(props.modelValue || {}), [preset.name]: { ...preset.rule } })
}
</script>

<style scoped>
.mb-12 { margin-bottom: 12px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.preset-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.rule-card { margin-bottom: 10px; }
.rule-head { display: flex; align-items: center; gap: 8px; }
.name-input { width: 220px; }
.severity-select { width: 130px; }
.rule-body { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.json-view { margin: 0; font-size: 12px; max-height: 160px; overflow: auto; }
</style>
