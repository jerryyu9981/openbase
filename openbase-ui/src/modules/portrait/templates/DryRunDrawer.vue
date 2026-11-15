<template>
  <el-drawer :model-value="modelValue" title="试运行（dry-run）" size="760px" data-test="dry-run-drawer" @update:model-value="(value: boolean) => emit('update:modelValue', Boolean(value))">
    <div class="dry-run">
      <el-alert type="info" show-icon :closable="false">
        <template #title>样例值 → 逐规则得分 → 维度加权 → 总分</template>
        <div>不写库；缺样例值按 50 分（missing），`when` 不成立跳过（skipped），取值错误标红并给出原因（error）。</div>
      </el-alert>

      <div class="section">
        <div class="section-title">
          <span>样例输入（{标签 key: 值}）</span>
          <el-button size="small" data-test="dry-run-generate" @click="generateSample">按模板生成样例</el-button>
        </div>
        <el-input v-model="sampleText" type="textarea" :rows="8" :placeholder="samplePlaceholder" data-test="dry-run-sample" />
        <div v-if="parseError" class="parse-error" data-test="dry-run-parse-error">{{ parseError }}</div>
      </div>

      <div class="section">
        <el-button type="primary" size="small" :loading="running" data-test="dry-run-run" @click="run">开始试算</el-button>
        <span v-if="report" class="muted sm">耗时 {{ report.elapsed_ms }} ms · 样例覆盖 {{ report.sample_keys.length }} 个 key</span>
      </div>

      <el-alert v-if="callError" type="error" show-icon :closable="false" data-test="dry-run-error">
        <template #title>{{ callError }}</template>
      </el-alert>

      <template v-if="report">
        <div class="overall">
          <div class="overall-score" data-test="dry-run-overall">{{ report.overall_score }}</div>
          <div class="overall-meta">
            <div>总分（维度加权）</div>
            <div class="muted sm">权重合计 {{ report.weight_sum }}<span v-if="report.normalized">（≠1.00，已按实际权重归一）</span></div>
            <div v-if="report.errors.length" class="muted sm">{{ report.errors.length }} 项校验提示（见模板工作台问题清单）</div>
          </div>
        </div>

        <el-card v-for="dimension in report.dimensions" :key="dimension.code" shadow="never" class="dimension-card">
          <div class="dimension-head">
            <strong>{{ dimension.name }}（{{ dimension.code }}）</strong>
            <span class="muted sm">权重 {{ dimension.weight }} · 得分 {{ dimension.score }} · 置信度 {{ (dimension.confidence * 100).toFixed(0) }}%</span>
            <el-tag v-if="dimension.skipped" size="small" type="warning">跳过 {{ dimension.skipped }} 条</el-tag>
          </div>
          <el-table :data="dimension.rules" size="small" data-test="dry-run-rule-table">
            <el-table-column prop="key" label="标签 key" min-width="180" />
            <el-table-column prop="type" label="类型" width="130" />
            <el-table-column label="样例值" width="130">
              <template #default="{ row }">{{ row.value === undefined || row.value === null ? '—' : String(row.value) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="得分" width="80">
              <template #default="{ row }">{{ row.score === null ? '—' : row.score }}</template>
            </el-table-column>
            <el-table-column prop="message" label="说明" min-width="160" show-overflow-tooltip />
          </el-table>
        </el-card>
      </template>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { dpsApi } from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'

interface PreviewRule {
  key: string
  type: string
  weight: number
  value: unknown
  status: string
  when_matched: boolean | null
  score: number | null
  message: string
}

interface PreviewDimension {
  code: string
  name: string
  weight: number
  score: number
  confidence: number
  skipped: number
  rules: PreviewRule[]
}

interface PreviewReport {
  valid: boolean
  errors: Array<{ path: string; message: string }>
  weight_sum: number
  normalized: boolean
  overall_score: number
  dimensions: PreviewDimension[]
  sample_keys: string[]
  elapsed_ms: number
}

const props = defineProps<{
  modelValue: boolean
  templateCode: string
  templatePayload: Record<string, unknown>
}>()

const emit = defineEmits<{ (event: 'update:modelValue', value: boolean): void }>()

const sampleText = ref('{}')
const samplePlaceholder = '{"basic:age_stage": "青壮年"}'
const parseError = ref('')
const callError = ref('')
const running = ref(false)
const report = ref<PreviewReport | null>(null)

watch(
  () => props.modelValue,
  (open) => {
    if (open && sampleText.value === '{}') generateSample()
  },
)

function generateSample() {
  const sample: Record<string, unknown> = {}
  const dimensions = ((props.templatePayload?.dimension_config as { dimensions?: unknown[] })?.dimensions || []) as Array<Record<string, unknown>>
  dimensions.forEach((dimension) => {
    const rules = (dimension.rules || []) as Array<Record<string, unknown>>
    rules.forEach((rule) => {
      const key = String(rule.key ?? rule.tag_code ?? '')
      if (!key) return
      const type = String(rule.type || 'legacy_map')
      if (type === 'enum_score' || type === 'grade_map_score' || type === 'legacy_map') {
        const mapping = (rule.mapping || {}) as Record<string, unknown>
        sample[key] = Object.keys(mapping)[0] ?? 'good'
      } else if (type === 'boolean_flag') {
        sample[key] = true
      } else if (type === 'interval_score') {
        const intervals = (rule.intervals || []) as unknown[]
        const first = intervals[0] as unknown[] | undefined
        sample[key] = first && first.length === 3 ? Math.round((Number(first[0]) + Number(first[1])) / 2) : 60
      } else if (type === 'ratio_target_score') {
        sample[key] = Number(rule.target ?? 1)
      } else {
        sample[key] = 80
      }
    })
  })
  sampleText.value = JSON.stringify(sample, null, 2)
  parseError.value = ''
}

async function run() {
  callError.value = ''
  report.value = null
  let sample: Record<string, unknown> = {}
  try {
    const parsed = JSON.parse(sampleText.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('样例必须是 JSON 对象')
    sample = parsed as Record<string, unknown>
    parseError.value = ''
  } catch (error) {
    parseError.value = `样例 JSON 解析失败：${(error as Error).message}`
    return
  }
  running.value = true
  try {
    report.value = (await dpsApi.previewTemplate(props.templateCode || 'draft', props.templatePayload, sample)) as PreviewReport
  } catch (caught) {
    callError.value = describeDpsError(caught).detail || '试算失败'
  } finally {
    running.value = false
  }
}

function statusLabel(status: string): string {
  return { scored: '已评分', missing: '缺样例', skipped: '跳过', error: '错误' }[status] || status
}

function statusTag(status: string): 'success' | 'warning' | 'info' | 'danger' {
  if (status === 'scored') return 'success'
  if (status === 'missing') return 'warning'
  if (status === 'skipped') return 'info'
  return 'danger'
}
</script>

<style scoped>
.dry-run { display: flex; flex-direction: column; gap: 12px; }
.section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; font-size: 13px; }
.parse-error { color: var(--ob-danger); font-size: 12px; margin-top: 4px; }
.overall { display: flex; align-items: center; gap: 16px; padding: 12px; border: 1px solid var(--ob-border); border-radius: 6px; }
.overall-score { font-size: 34px; font-weight: 600; }
.overall-meta { font-size: 13px; }
.dimension-card { margin-bottom: 10px; }
.dimension-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
</style>
