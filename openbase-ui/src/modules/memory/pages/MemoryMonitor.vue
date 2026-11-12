<template>
  <PageContainer title="运行监控" description="记忆服务健康探针与运行指标" test-id="memory-monitor-page">
    <div class="page-toolbar">
      <el-select v-model="range" style="width: 160px" data-test="monitor-range" @change="loadMonitor">
        <el-option label="最近 1 小时" value="1h" />
        <el-option label="最近 24 小时" value="24h" />
        <el-option label="最近 7 天" value="7d" />
      </el-select>
      <el-button type="primary" :loading="loading" data-test="monitor-refresh" @click="loadAll">刷新</el-button>
    </div>

    <el-alert
      v-if="monitorError"
      :title="monitorError"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="monitor-error"
      @close="monitorError = ''"
    >
      <template #default>
        <el-button link type="primary" size="small" data-test="monitor-retry" @click="loadMonitor">点击重试</el-button>
      </template>
    </el-alert>

    <el-row :gutter="16" class="mb-16">
      <el-col v-for="probe in probes" :key="probe.key" :xs="24" :sm="8">
        <div :data-test="`health-card-${probe.key}`">
          <el-card v-loading="probe.loading" shadow="hover" class="probe-card">
            <div class="probe-head">
              <span class="probe-label">{{ probe.label }}</span>
              <el-tag size="small" :type="probeTagType(probe)" data-test="probe-status">
                {{ probe.loading ? '检测中' : probe.ok === null ? '未知' : probe.ok ? '正常' : '不可达' }}
              </el-tag>
            </div>
            <div class="probe-status">{{ probe.status || '—' }}</div>
            <div class="probe-message">{{ probe.message || '—' }}</div>
            <el-button
              v-if="probe.ok === false"
              link
              type="primary"
              size="small"
              data-test="probe-retry"
              @click="loadProbe(probe)"
            >
              重新检测
            </el-button>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <el-card v-loading="monitorLoading" data-test="monitor-metrics">
      <template #header>运行指标（最近 {{ rangeLabel }}）</template>
      <el-descriptions v-if="scalarEntries.length" :column="2" border>
        <el-descriptions-item v-for="[key, value] in scalarEntries" :key="key" :label="key">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
      <div v-for="[key, value] in complexEntries" :key="key" class="complex-block">
        <div class="complex-title">{{ key }}</div>
        <pre class="complex-value">{{ stringify(value) }}</pre>
      </div>
      <el-empty
        v-if="!monitorLoading && scalarEntries.length === 0 && complexEntries.length === 0"
        description="暂无监控数据"
        :image-size="60"
        data-test="monitor-empty"
      />
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '@/core/api/http'
import { describeError } from '@/core/api/error'

type ProbeKey = 'health' | 'readiness' | 'liveness'

interface ProbeState {
  key: ProbeKey
  label: string
  loading: boolean
  /** null = 尚未检测；true/false = 正常/不可达 */
  ok: boolean | null
  status: string
  message: string
}

const RANGE_LABELS: Record<string, string> = { '1h': '1 小时', '24h': '24 小时', '7d': '7 天' }

const range = ref('24h')
const loading = ref(false)
const monitorLoading = ref(false)
const monitorError = ref('')
const monitor = ref<Record<string, unknown> | null>(null)

const probes = reactive<ProbeState[]>([
  { key: 'health', label: '健康检查（health）', loading: false, ok: null, status: '', message: '' },
  { key: 'readiness', label: '就绪检查（readiness）', loading: false, ok: null, status: '', message: '' },
  { key: 'liveness', label: '存活检查（liveness）', loading: false, ok: null, status: '', message: '' },
])

const rangeLabel = computed(() => RANGE_LABELS[range.value] || range.value)

/** 标量指标直接以描述列表呈现；数组/对象等结构化数据单独展开 */
const scalarEntries = computed(() => Object.entries(monitor.value || {}).filter(([, value]) => isScalar(value)))
const complexEntries = computed(() => Object.entries(monitor.value || {}).filter(([, value]) => !isScalar(value)))

function isScalar(value: unknown): boolean {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value)
}

function stringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function probeTagType(probe: ProbeState): 'success' | 'danger' | 'info' {
  if (probe.ok === null || probe.loading) return 'info'
  return probe.ok ? 'success' : 'danger'
}

/** 探针响应状态归一：ok/healthy/ready/up/pass/alive 视为正常 */
function isHealthyStatus(status: string): boolean {
  return /^(ok|healthy|ready|up|pass|alive)/i.test(status.trim())
}

async function loadProbe(probe: ProbeState) {
  probe.loading = true
  try {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>(`/memory-proxy/${probe.key}`)
    const payload = (data?.data || {}) as Record<string, unknown>
    const status = String(payload.status ?? payload.state ?? 'ok')
    probe.status = status
    probe.ok = isHealthyStatus(status)
    probe.message = String(payload.message ?? (payload.version ? `版本 ${payload.version}` : ''))
  } catch (err) {
    probe.ok = false
    probe.status = '不可达'
    probe.message = describeError(err).detail || '网络错误'
  } finally {
    probe.loading = false
  }
}

async function loadMonitor() {
  monitorLoading.value = true
  monitorError.value = ''
  try {
    const { data } = await http.get<{ code: number; data: Record<string, unknown> }>('/memory-proxy/monitor', {
      params: { range: range.value },
    })
    monitor.value = (data?.data || null) as Record<string, unknown> | null
  } catch (err) {
    monitor.value = null
    monitorError.value = `运行指标加载失败：${describeError(err).detail || '网络错误'}`
  } finally {
    monitorLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([...probes.map((probe) => loadProbe(probe)), loadMonitor()])
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadAll()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.probe-card { min-height: 132px; }
.probe-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.probe-label { font-weight: 600; font-size: 14px; }
.probe-status { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.probe-message { color: var(--ob-text-secondary); font-size: 12px; min-height: 18px; }
.complex-block { margin-top: 12px; }
.complex-title { font-weight: 600; font-size: 13px; color: #374151; margin-bottom: 4px; }
.complex-value {
  margin: 0; padding: 8px 10px; background: #f9fafb; border-radius: 6px;
  font-size: 12px; color: #6b7280; white-space: pre-wrap; word-break: break-all;
}
</style>
