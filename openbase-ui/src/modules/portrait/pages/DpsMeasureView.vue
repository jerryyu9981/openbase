<template>
  <PageContainer title="措施建议" description="选择主体 → 查看画像摘要与按维度分组的处理建议" test-id="dps-measure-view-page">
    <div class="page-toolbar">
      <el-autocomplete
        v-model="personId"
        :fetch-suggestions="searchSubjects"
        placeholder="搜索姓名 / person_id / 外部 ID，或直接输入"
        clearable
        style="width: 320px"
        data-test="measure-person"
        @select="onSelectSubject"
        @keyup.enter="load(true)"
      />
      <el-button type="primary" :loading="loading" data-test="measure-run" @click="load(true)">查询建议</el-button>
      <el-button :disabled="!suggestions.length" data-test="measure-export-json" @click="exportJson">导出 JSON</el-button>
      <el-button :disabled="!suggestions.length" data-test="measure-export-csv" @click="exportCsv">导出 CSV</el-button>
      <el-button data-test="measure-lineage" @click="$router.push('/portrait/dps/lineage')">标签血缘</el-button>
    </div>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load(true)">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card shadow="never" class="mb-16" data-test="measure-summary">
      <template #header>
        <div class="card-head">
          <span>画像摘要</span>
          <span class="muted sm">主体选择器支持姓名/ID 模糊（A6 前端降级：前 100 条）</span>
        </div>
      </template>
      <template v-if="profile">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="画像名称">{{ profile.name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="person_id">{{ profile.person_id || personId }}</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskType(profile)" size="small">{{ riskLabel(profile) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="综合评分">{{ overallText }}</el-descriptions-item>
          <el-descriptions-item label="数据完整度">{{ completenessText }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(profile.updated_at) }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="dimensionScores.length" class="dimension-chips">
          <el-tag v-for="dimension in dimensionScores" :key="dimension.code" size="small" type="info">
            {{ dimension.label }}：{{ dimension.score === null ? '未采集' : dimension.score.toFixed(1) }}
          </el-tag>
        </div>
      </template>
      <el-empty v-else description="输入主体并查询后展示画像摘要" :image-size="50" />
    </el-card>

    <el-card header="建议列表（后端原文 · 前端仅按维度分组呈现）" data-test="measure-table">
      <el-empty v-if="!suggestions.length" description="暂无措施建议" :image-size="60" data-test="measure-empty" />
      <div v-for="group in groups" :key="group.dimension" class="measure-group" data-test="measure-group">
        <div class="group-head">
          <span class="group-title">{{ group.label }}</span>
          <span class="muted sm">{{ group.items.length }} 条</span>
        </div>
        <div class="measure-card-list">
          <div v-for="(item, index) in group.items" :key="`${group.dimension}-${index}-${item.measure_code || item.tag_code || ''}`" class="measure-card" data-test="measure-card">
            <div class="measure-text">{{ item.measure_text || '—' }}</div>
            <div class="measure-meta muted sm">
              <span v-if="item.measure_code">措施码 {{ item.measure_code }}</span>
              <span v-if="item.tag_code">标签 {{ item.tag_code }}</span>
              <span v-if="item.source_tag">来源 {{ item.source_tag }}</span>
            </div>
            <div class="measure-actions">
              <el-button link type="primary" size="small" data-test="measure-copy" @click="copySuggestion(item)">复制</el-button>
            </div>
          </div>
        </div>
      </div>

      <el-alert v-if="disclaimer" type="warning" show-icon :closable="false" class="mt-16" data-test="measure-disclaimer">
        <template #title>免责声明（后端原文，前端不得改写）</template>
        <div>{{ disclaimer }}</div>
      </el-alert>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsMeasureSuggestion, type DpsPortrait } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'
import {
  groupMeasureSuggestions,
  measureSuggestionsCsv,
} from '@/modules/portrait/measures/measureGroups'
import { formatDateTime, riskLabelOf, riskScoreOf } from '@/modules/portrait/portrait/portraitTools'

interface SubjectOption {
  value: string
  name?: string
}

const DIMENSION_LABELS: Record<string, string> = {
  basic: '基础属性',
  behavior: '行为特征',
  behavioral: '行为特征',
  psychology: '心理评估',
  psychological: '心理评估',
  social: '社会关系',
  correction: '矫正表现',
  risk: '风险等级',
}

const route = useRoute()
const personId = ref(String(route.query.person_id || ''))
const profile = ref<DpsPortrait | null>(null)

const { data, loading, error, run } = useAsyncState<{ suggestions?: DpsMeasureSuggestion[]; disclaimer?: string }>()

const suggestions = computed(() => data.value?.suggestions || [])
const disclaimer = computed(() => data.value?.disclaimer || '')
const groups = computed(() => groupMeasureSuggestions(suggestions.value))
const overallText = computed(() => {
  const value = Number(profile.value?.overall_score)
  return Number.isFinite(value) ? value.toFixed(1) : '—'
})
const completenessText = computed(() => {
  const value = Number(profile.value?.data_completeness)
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : '—'
})
const dimensionScores = computed(() => {
  const row = profile.value
  if (!row) return []
  return Object.entries(DIMENSION_LABELS).map(([code, label]) => ({
    code,
    label,
    score: toNumber(row[`${code}_score` as keyof DpsPortrait]),
  }))
})

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function riskLabel(row: DpsPortrait): string {
  return riskLabelOf(row)
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const value = riskScoreOf(row)
  if (value < 0) return 'info'
  if (value >= 70) return 'danger'
  if (value >= 40) return 'warning'
  return 'success'
}

function formatTime(value?: string): string {
  return formatDateTime(value)
}

function readRecentSubjects(): SubjectOption[] {
  try {
    const raw = localStorage.getItem('dps.subject.recent')
    const parsed = raw ? (JSON.parse(raw) as Array<{ person_id: string; name?: string }>) : []
    return Array.isArray(parsed)
      ? parsed.map((item) => ({ value: item.person_id, name: item.name })).filter((item) => item.value)
      : []
  } catch {
    return []
  }
}

/** 主体候选：优先服务端检索（A6），DPS 未升级时回退前 100 条本地匹配；追加最近使用 */
async function searchSubjects(keyword: string, callback: (items: SubjectOption[]) => void) {
  const recent = readRecentSubjects()
  const kw = keyword.trim().toLowerCase()
  try {
    let result
    try {
      result = await dpsApi.listPortraits({
        page: 1,
        page_size: 50,
        keyword: keyword.trim() || undefined,
      })
    } catch (caught) {
      if ((caught as { response?: { status?: number } })?.response?.status !== 404) throw caught
      result = await dpsApi.listPortraits({ page: 1, page_size: 100 })
    }
    const matched = (result.items || [])
      .map((row) => ({ value: String(row.person_id || row.id || ''), name: row.name }))
      .filter((item) => item.value)
      .filter((item) => !kw || item.value.toLowerCase().includes(kw) || String(item.name || '').toLowerCase().includes(kw))
    const merged = [...recent, ...matched].filter(
      (item, index, array) => array.findIndex((other) => other.value === item.value) === index,
    )
    callback(merged.slice(0, 20))
  } catch {
    callback(recent)
  }
}

function onSelectSubject(item: SubjectOption) {
  personId.value = item.value
}

async function load(withSummary = false) {
  const target = personId.value.trim()
  if (!target) {
    ElMessage.warning('请选择或输入画像主体')
    return
  }
  personId.value = target
  await run(() => dpsApi.suggestMeasures(target))
  if (!withSummary) return
  profile.value = await dpsApi.getPortrait(target).catch(() => null)
}

function copySuggestion(item: DpsMeasureSuggestion) {
  const text = String(item.measure_text || '')
  if (!text) return
  navigator.clipboard
    ?.writeText(text)
    .then(() => ElMessage.success('建议已复制'))
    .catch(() => ElMessage.info(text))
}

function downloadText(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function exportJson() {
  const payload = {
    person_id: personId.value,
    exported_at: new Date().toISOString(),
    profile: profile.value,
    disclaimer: disclaimer.value,
    suggestions: suggestions.value,
  }
  downloadText(JSON.stringify(payload, null, 2), `dps-measures-${personId.value}.json`, 'application/json;charset=utf-8')
}

function exportCsv() {
  downloadText(`\ufeff${measureSuggestionsCsv(suggestions.value)}`, `dps-measures-${personId.value}.csv`, 'text/csv;charset=utf-8')
}

onMounted(() => {
  if (personId.value) void load(false)
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.dimension-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.measure-group { margin-bottom: 16px; }
.group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.group-title { font-size: 14px; font-weight: 600; }
.measure-card-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.measure-card { border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.measure-text { font-size: 13px; color: var(--ob-text-primary); line-height: 1.6; }
.measure-meta { display: flex; flex-wrap: wrap; gap: 10px; }
.measure-actions { display: flex; justify-content: flex-end; }
</style>
