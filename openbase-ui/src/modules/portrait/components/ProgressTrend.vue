<template>
  <div class="progress-trend" data-test="progress-trend">
    <div class="trend-head">
      <el-radio-group v-model="periodType" size="small" data-test="progress-period" @change="load">
        <el-radio-button value="day">日</el-radio-button>
        <el-radio-button value="week">周</el-radio-button>
        <el-radio-button value="month">月</el-radio-button>
      </el-radio-group>
      <span class="muted sm">最近 {{ limit }} 个周期</span>
    </div>

    <div v-if="loading" class="muted sm">加载中…</div>
    <el-alert
      v-else-if="error"
      type="warning"
      show-icon
      :closable="false"
      :title="error"
      data-test="progress-trend-error"
    />
    <el-empty
      v-else-if="!ordered.length"
      description="暂无进度快照"
      :image-size="60"
      data-test="progress-trend-empty"
    />
    <template v-else>
      <svg class="trend-chart" viewBox="0 0 320 130" preserveAspectRatio="none" role="img" aria-label="进度趋势">
        <line x1="0" y1="110" x2="320" y2="110" class="axis" />
        <line x1="0" y1="10" x2="320" y2="10" class="axis dashed" />
        <polyline :points="onTimePoints" class="line line-ontime" />
        <polyline :points="completionPoints" class="line line-completion" />
        <circle v-for="(point, index) in onTimeDots" :key="`o-${index}`" :cx="point.x" :cy="point.y" r="2.5" class="dot dot-ontime" />
      </svg>
      <div class="legend">
        <span class="legend-item"><i class="swatch swatch-ontime" />按时率</span>
        <span class="legend-item"><i class="swatch swatch-completion" />完成率</span>
        <span class="legend-item muted">最新：{{ latest.period_key }}</span>
      </div>

      <el-descriptions :column="4" size="small" border class="mt-12" data-test="progress-latest">
        <el-descriptions-item label="按时率">{{ latest.on_time_rate ?? '—' }}%</el-descriptions-item>
        <el-descriptions-item label="完成/总数">
          {{ latest.completed_items ?? 0 }}/{{ latest.total_items ?? 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="逾期">{{ latest.overdue_items ?? 0 }}</el-descriptions-item>
        <el-descriptions-item label="质量/工作量">
          {{ latest.quality_score ?? 0 }} / {{ latest.workload_hours ?? 0 }}h
        </el-descriptions-item>
      </el-descriptions>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { dpsApi, type DpsProgressSnapshot } from '@/core/api/dps'
import { describeError } from '@/core/api/error'

const props = defineProps<{ personId: string; limit?: number }>()

const periodType = ref<'day' | 'week' | 'month'>('week')
const limit = computed(() => props.limit ?? 12)
const items = ref<DpsProgressSnapshot[]>([])
const loading = ref(false)
const error = ref('')

/** 周期键倒序 → 绘图按时间正序 */
const ordered = computed(() => [...items.value].reverse())
const latest = computed<Partial<DpsProgressSnapshot>>(() => items.value[0] || {})

function toPoints(values: number[]): string {
  if (!values.length) return ''
  const step = values.length > 1 ? 300 / (values.length - 1) : 0
  return values
    .map((value, index) => `${index * step + 10},${110 - Math.max(0, Math.min(100, value))}`)
    .join(' ')
}

const onTimePoints = computed(() => toPoints(ordered.value.map((item) => Number(item.on_time_rate || 0))))
const completionPoints = computed(() =>
  toPoints(
    ordered.value.map((item) =>
      item.total_items ? (Number(item.completed_items || 0) / Number(item.total_items)) * 100 : 0,
    ),
  ),
)
const onTimeDots = computed(() =>
  ordered.value.map((item, index) => {
    const step = ordered.value.length > 1 ? 300 / (ordered.value.length - 1) : 0
    return {
      x: index * step + 10,
      y: 110 - Math.max(0, Math.min(100, Number(item.on_time_rate || 0))),
    }
  }),
)

async function load() {
  if (!props.personId) return
  loading.value = true
  error.value = ''
  try {
    const payload = await dpsApi.getProgressTrend(props.personId, {
      period_type: periodType.value,
      limit: limit.value,
    })
    items.value = payload.items || []
  } catch (err) {
    error.value = describeError(err).detail || '进度加载失败（可能未开启 DPS_PROGRESS_ENABLED）'
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.personId, load)
</script>

<style scoped>
.progress-trend { width: 100%; }
.trend-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.trend-chart { width: 100%; height: 130px; }
.axis { stroke: var(--el-border-color); stroke-width: 1; }
.axis.dashed { stroke-dasharray: 3 3; }
.line { fill: none; stroke-width: 2; }
.line-ontime { stroke: var(--el-color-primary); }
.line-completion { stroke: var(--el-color-success); }
.dot-ontime { fill: var(--el-color-primary); }
.legend { display: flex; gap: 16px; align-items: center; font-size: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.swatch { display: inline-block; width: 12px; height: 2px; }
.swatch-ontime { background: var(--el-color-primary); }
.swatch-completion { background: var(--el-color-success); }
.muted { color: var(--el-text-color-secondary); }
.sm { font-size: 12px; }
.mt-12 { margin-top: 12px; }
</style>
