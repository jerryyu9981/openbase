<template>
  <el-card shadow="never" class="rule-card" :class="{ 'is-invalid': hasError }" data-test="rule-card">
    <div class="rule-head">
      <el-input
        :model-value="ruleKey(modelValue)"
        size="small"
        placeholder="标签 key，如 basic:age_stage"
        class="key-input"
        data-test="rule-key"
        @update:model-value="(value: string) => patch({ key: value, tag_code: undefined })"
      />
      <el-select
        :model-value="modelValue.type || 'legacy_map'"
        size="small"
        class="type-select"
        data-test="rule-type"
        @update:model-value="changeType"
      >
        <el-option v-for="item in RULE_TYPES" :key="item.type" :label="item.label" :value="item.type" />
      </el-select>
      <el-input-number
        :model-value="Number(modelValue.weight ?? 0.2)"
        :min="0"
        :max="1"
        :step="0.05"
        :precision="2"
        size="small"
        class="weight-input"
        data-test="rule-weight"
        @update:model-value="(value: number | undefined) => patch({ weight: Number(value ?? 0) })"
      />
      <el-input
        :model-value="String(modelValue.description || '')"
        size="small"
        placeholder="规则说明（可选）"
        class="desc-input"
        data-test="rule-description"
        @update:model-value="(value: string) => patch({ description: value })"
      />
      <div class="rule-actions">
        <el-button link size="small" data-test="rule-duplicate" @click="emit('duplicate')">复制</el-button>
        <el-button link type="danger" size="small" data-test="rule-remove" @click="emit('remove')">删除</el-button>
      </div>
    </div>

    <div class="rule-hint">{{ typeHint }}</div>

    <!-- 映射表：enum_score / legacy_map / grade_map_score -->
    <div v-if="mappingTypes.includes(activeType)" class="param-block" data-test="rule-mapping">
      <div class="param-title">值 → 分数</div>
      <div v-for="(row, index) in mappingRows" :key="index" class="param-row">
        <el-input
          :model-value="row.key"
          size="small"
          placeholder="枚举值（如 A / 高）"
          class="map-key"
          data-test="rule-mapping-key"
          @update:model-value="(value: string) => renameMapping(index, value)"
        />
        <el-input-number
          :model-value="row.score"
          :min="0"
          :max="100"
          size="small"
          data-test="rule-mapping-score"
          @update:model-value="(value: number | undefined) => updateMappingScore(index, Number(value ?? 0))"
        />
        <el-button link type="danger" size="small" @click="removeMapping(index)">删除</el-button>
      </div>
      <el-button size="small" class="mt-6" data-test="rule-mapping-add" @click="addMapping">＋映射项</el-button>
    </div>

    <!-- 布尔标志 -->
    <div v-if="activeType === 'boolean_flag'" class="param-block">
      <div class="param-row">
        <span class="param-label">为真得分</span>
        <el-input-number
          :model-value="Number(modelValue.true_score ?? 100)"
          :min="0"
          :max="100"
          size="small"
          data-test="rule-true-score"
          @update:model-value="(value: number | undefined) => patch({ true_score: Number(value ?? 0) })"
        />
        <span class="param-label">为假得分</span>
        <el-input-number
          :model-value="Number(modelValue.false_score ?? 0)"
          :min="0"
          :max="100"
          size="small"
          data-test="rule-false-score"
          @update:model-value="(value: number | undefined) => patch({ false_score: Number(value ?? 0) })"
        />
      </div>
    </div>

    <!-- 区间映射 -->
    <div v-if="activeType === 'interval_score'" class="param-block" data-test="rule-intervals">
      <div class="param-title">区间 → 分数（含端点）</div>
      <div v-for="(row, index) in intervalRows" :key="index" class="param-row">
        <el-input
          :model-value="String(row.low)"
          size="small"
          placeholder="下限"
          class="interval-input"
          @update:model-value="(value: string) => updateInterval(index, 0, value)"
        />
        <span class="param-sep">~</span>
        <el-input
          :model-value="String(row.high)"
          size="small"
          placeholder="上限"
          class="interval-input"
          @update:model-value="(value: string) => updateInterval(index, 1, value)"
        />
        <span class="param-sep">→</span>
        <el-input
          :model-value="String(row.score)"
          size="small"
          placeholder="分数"
          class="interval-input"
          @update:model-value="(value: string) => updateInterval(index, 2, value)"
        />
        <el-button link type="danger" size="small" @click="removeInterval(index)">删除</el-button>
      </div>
      <el-button size="small" class="mt-6" data-test="rule-interval-add" @click="addInterval">＋区间</el-button>
    </div>

    <!-- 比率目标 -->
    <div v-if="activeType === 'ratio_target_score'" class="param-block">
      <div class="param-row">
        <span class="param-label">target</span>
        <el-input-number
          :model-value="Number(modelValue.target ?? 1)"
          :min="0.01"
          :max="1"
          :step="0.05"
          :precision="2"
          size="small"
          data-test="rule-target"
          @update:model-value="(value: number | undefined) => patch({ target: Number(value ?? 1) })"
        />
        <span class="param-label">cap</span>
        <el-input-number
          :model-value="Number(modelValue.cap ?? 100)"
          :min="0"
          :max="100"
          size="small"
          data-test="rule-cap"
          @update:model-value="(value: number | undefined) => patch({ cap: Number(value ?? 100) })"
        />
        <span class="param-label">half_floor</span>
        <el-input-number
          :model-value="Number(modelValue.half_floor ?? 0.5)"
          :min="0"
          :max="1"
          :step="0.1"
          :precision="2"
          size="small"
          data-test="rule-half-floor"
          @update:model-value="(value: number | undefined) => patch({ half_floor: Number(value ?? 0.5) })"
        />
      </div>
    </div>

    <!-- 条件组 when -->
    <div class="when-block">
      <el-switch
        :model-value="!!modelValue.when"
        size="small"
        active-text="附加执行条件（when）"
        data-test="rule-when-toggle"
        @update:model-value="toggleWhen"
      />
      <ConditionGroupBuilder
        v-if="modelValue.when"
        :model-value="modelValue.when"
        :fields="fields"
        @update:model-value="(value: ConditionGroup) => patch({ when: value })"
      />
    </div>

    <el-collapse class="json-collapse">
      <el-collapse-item :title="`规则 JSON（只读）`" name="json">
        <pre class="json-view" data-test="rule-json">{{ prettyRule }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ConditionGroupBuilder from './ConditionGroupBuilder.vue'
import {
  RULE_TYPES,
  newConditionGroup,
  ruleKey,
  type ConditionGroup,
  type FieldOption,
  type RuleModel,
} from './model'

const props = withDefaults(
  defineProps<{
    modelValue: RuleModel
    fields?: FieldOption[]
    hasError?: boolean
  }>(),
  { fields: () => [], hasError: false },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: RuleModel): void
  (event: 'remove'): void
  (event: 'duplicate'): void
}>()

const mappingTypes = ['enum_score', 'legacy_map', 'grade_map_score']
const activeType = computed(() => String(props.modelValue.type || 'legacy_map'))
const typeHint = computed(() => RULE_TYPES.find((item) => item.type === activeType.value)?.hint || '')
const prettyRule = computed(() => JSON.stringify(props.modelValue, null, 2))

const mappingRows = computed(() =>
  Object.entries(props.modelValue.mapping || {}).map(([key, score]) => ({ key, score: Number(score) })),
)

const intervalRows = computed(() =>
  (Array.isArray(props.modelValue.intervals) ? props.modelValue.intervals : []).map((interval) => ({
    low: interval?.[0] ?? '',
    high: interval?.[1] ?? '',
    score: interval?.[2] ?? '',
  })),
)

function patch(changes: Partial<RuleModel>) {
  const next: RuleModel = { ...props.modelValue, ...changes }
  // 仅在改写 key 时清理旧写法 tag_code，避免其他字段编辑误删标签编码
  if ('key' in changes && !('tag_code' in changes)) delete next.tag_code
  emit('update:modelValue', next)
}

function changeType(type: string) {
  const defaults: Record<string, Partial<RuleModel>> = {
    enum_score: { mapping: props.modelValue.mapping || {} },
    boolean_flag: { true_score: props.modelValue.true_score ?? 100, false_score: props.modelValue.false_score ?? 0 },
    interval_score: { intervals: props.modelValue.intervals || [[0, 60, 40], [61, 100, 80]] },
    ratio_target_score: { target: props.modelValue.target ?? 1, cap: props.modelValue.cap ?? 100, half_floor: props.modelValue.half_floor ?? 0.5 },
    grade_map_score: { mapping: props.modelValue.mapping || { 1: 30, 2: 60, 3: 80, 4: 100 } },
    legacy_map: {},
  }
  const next: RuleModel = { ...props.modelValue, ...(defaults[type] || {}), type }
  // 未知类型或类型切换后，保留原参数但不再显示；JSON 视图可核查
  emit('update:modelValue', next)
}

function toggleWhen(enabled: boolean | string | number) {
  patch({ when: enabled ? (props.modelValue.when || newConditionGroup()) : undefined })
}

function commitMapping(rows: Array<{ key: string; score: number }>) {
  const mapping: Record<string, number> = {}
  rows.forEach((row) => {
    if (row.key.trim()) mapping[row.key.trim()] = row.score
  })
  patch({ mapping })
}

function addMapping() {
  commitMapping([...mappingRows.value, { key: '', score: 60 }])
}

function removeMapping(index: number) {
  const rows = [...mappingRows.value]
  rows.splice(index, 1)
  commitMapping(rows)
}

function updateMappingScore(index: number, score: number) {
  const rows = mappingRows.value.map((row, position) => (position === index ? { ...row, score } : row))
  commitMapping(rows)
}

function renameMapping(index: number, key: string) {
  const rows = mappingRows.value.map((row, position) => (position === index ? { ...row, key } : row))
  commitMapping(rows)
}

function commitIntervals(rows: Array<{ low: unknown; high: unknown; score: unknown }>) {
  patch({ intervals: rows.map((row) => [toNumber(row.low), toNumber(row.high), toNumber(row.score)]) })
}

function addInterval() {
  commitIntervals([...intervalRows.value, { low: '', high: '', score: '' }])
}

function removeInterval(index: number) {
  const rows = [...intervalRows.value]
  rows.splice(index, 1)
  commitIntervals(rows)
}

function updateInterval(index: number, position: number, raw: string) {
  const keys = ['low', 'high', 'score'] as const
  const rows = intervalRows.value.map((row, rowIndex) =>
    rowIndex === index ? { ...row, [keys[position]]: raw } : row,
  )
  commitIntervals(rows)
}

function toNumber(value: unknown): number | string {
  if (value === '' || value === null || value === undefined) return ''
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : String(value)
}
</script>

<style scoped>
.rule-card { margin-bottom: 10px; }
.rule-card.is-invalid { box-shadow: 0 0 0 1px var(--ob-danger) inset; }
.rule-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.key-input { width: 230px; }
.type-select { width: 150px; }
.weight-input { width: 110px; }
.desc-input { flex: 1 1 180px; min-width: 160px; }
.rule-actions { display: flex; gap: 4px; }
.rule-hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.param-block { margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--ob-border); }
.param-title { font-size: 12px; color: var(--ob-text-secondary); margin-bottom: 6px; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.param-label { font-size: 12px; color: var(--ob-text-secondary); }
.param-sep { color: var(--ob-text-secondary); }
.map-key { width: 200px; }
.interval-input { width: 90px; }
.when-block { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.json-collapse { margin-top: 6px; }
.json-view { margin: 0; font-size: 12px; max-height: 220px; overflow: auto; }
.mt-6 { margin-top: 6px; }
</style>
