<template>
  <PageContainer title="画像系统监控" description="DPS 运行态指标与只读治理视图" test-id="dps-monitor-view-page">
    <div class="page-toolbar">
      <el-button :loading="loading" data-test="dps-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="dps-monitor-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16" class="mb-16">
      <el-col :span="6">
        <el-card shadow="hover" data-test="mon-dep">
          <div class="metric-label">DPS 服务</div>
          <div class="dep-header">
            <span class="metric-value">{{ healthy ? '健康' : '未知/异常' }}</span>
            <el-tag :type="healthy ? 'success' : 'danger'" size="small" data-test="mon-dep-badge">
              {{ healthy ? '健康' : '异常' }}
            </el-tag>
          </div>
          <div class="dep-meta">版本：{{ version || '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" data-test="dps-metric-qps">
          <div class="metric-label">QPS（60 秒窗口）</div>
          <div class="metric-value">{{ formatNumber(metrics?.qps_1m) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" data-test="dps-metric-cpu">
          <div class="metric-label">CPU 使用率（单核）</div>
          <div class="metric-value">{{ formatPercent(metrics?.cpu_percent) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" data-test="dps-metric-memory">
          <div class="metric-label">进程内存</div>
          <div class="metric-value">{{ formatMemory() }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mb-16">
      <el-col :span="12">
        <el-card shadow="hover" data-test="dps-metric-uptime">
          <div class="metric-label">运行时长</div>
          <div class="metric-value">{{ formatUptime(metrics?.uptime_seconds) }}</div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" data-test="dps-metric-requests">
          <div class="metric-label">累计请求数</div>
          <div class="metric-value">{{ formatInteger(metrics?.requests_total) }}</div>
          <div class="dep-meta">采集时间：{{ collectedAt || '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card header="限流状态（只读）" class="mb-16" data-test="dps-rate-limit-card">
      <div class="ob-table-scroll">
        <el-table :data="rateLimits" size="small" stripe data-test="dps-rate-limit-table">
          <template #empty>
            <el-empty description="暂无限流记录" :image-size="50" data-test="dps-rate-limit-empty" />
          </template>
          <el-table-column prop="tenant_id" label="租户" min-width="130" show-overflow-tooltip />
          <el-table-column prop="endpoint" label="端点" min-width="170" show-overflow-tooltip />
          <el-table-column prop="count" label="当前计数" width="100" />
          <el-table-column prop="limit" label="上限" width="90" />
          <el-table-column prop="window" label="窗口(秒)" width="100" />
          <el-table-column label="利用率" width="100">
            <template #default="{ row }">{{ formatPercent(row.utilization) }}</template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="100" />
        </el-table>
      </div>
    </el-card>

    <el-card header="告警规则（只读）" data-test="dps-alert-rules-card">
      <div class="ob-table-scroll">
        <el-table :data="alertRules" size="small" stripe data-test="dps-alert-rules-table">
          <template #empty>
            <el-empty description="暂无告警规则" :image-size="50" data-test="dps-alert-rules-empty" />
          </template>
          <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
          <el-table-column prop="condition" label="条件" min-width="160" show-overflow-tooltip />
          <el-table-column prop="threshold" label="阈值" width="90" />
          <el-table-column prop="duration" label="持续" width="90" />
          <el-table-column prop="notification_channel" label="通知渠道" width="120" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="isRuleEnabled(row.enabled) ? 'success' : 'info'" size="small">
                {{ isRuleEnabled(row.enabled) ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import {
  dpsApi,
  type DpsAlertRule,
  type DpsRateLimitStatus,
  type DpsRuntimeMetrics,
} from '@/core/api/dps'

/**
 * 画像系统监控（v1.12.0 XR-DPS-05 真实化）：四源独立加载——
 * 健康 `/dps-proxy/health`、运行态指标 `/dps-proxy/metrics`、
 * 限流状态 `/dps-proxy/rate-limits/status`、告警规则 `/dps-proxy/alerts/rules`。
 * 全部为只读；单源失败仅提示并保留其余可用区域，不补造数据。
 */
const loading = ref(false)
const errorMessage = ref('')
const status = ref('')
const version = ref('')
const metrics = ref<DpsRuntimeMetrics | null>(null)
const rateLimits = ref<DpsRateLimitStatus[]>([])
const alertRules = ref<DpsAlertRule[]>([])
const collectedAt = ref('')

const healthy = computed(
  () => ['healthy', 'ok'].includes(status.value.toLowerCase()),
)

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : '未知错误'
}

function formatNumber(value?: number | null, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

function formatPercent(value?: number | null): string {
  return value === null || value === undefined ? '—' : `${formatNumber(value)}%`
}

function formatInteger(value?: number | null): string {
  return value === null || value === undefined ? '—' : String(Math.trunc(value))
}

function formatMemory(): string {
  if (!metrics.value || metrics.value.memory_mb === null) return '—'
  const percent = metrics.value.memory_percent
  const suffix = percent === null || percent === undefined ? '' : ` / ${formatNumber(percent)}%`
  return `${formatNumber(metrics.value.memory_mb, 1)} MB${suffix}`
}

function formatUptime(seconds?: number | null): string {
  if (seconds === null || seconds === undefined) return '—'
  const total = Math.max(Math.trunc(seconds), 0)
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60
  if (days > 0) return `${days} 天 ${hours} 小时`
  if (hours > 0) return `${hours} 小时 ${minutes} 分`
  if (minutes > 0) return `${minutes} 分 ${rest} 秒`
  return `${rest} 秒`
}

function isRuleEnabled(enabled: unknown): boolean {
  return enabled === true || enabled === 1 || enabled === '1'
}

async function load() {
  loading.value = true
  errorMessage.value = ''

  const [healthResult, metricsResult, rateLimitResult, rulesResult] = await Promise.allSettled([
    dpsApi.getDpsHealth(),
    dpsApi.getRuntimeMetrics(),
    dpsApi.getRateLimitStatus(),
    dpsApi.getAlertRules(),
  ])

  const failures: string[] = []

  if (healthResult.status === 'fulfilled') {
    status.value = healthResult.value?.status || 'unknown'
    version.value = healthResult.value?.version || ''
  } else {
    status.value = 'unknown'
    version.value = ''
    failures.push(`健康状态加载失败：${errorText(healthResult.reason)}`)
  }

  if (metricsResult.status === 'fulfilled') {
    metrics.value = metricsResult.value
    collectedAt.value = metricsResult.value?.collected_at || ''
  } else {
    metrics.value = null
    collectedAt.value = ''
    failures.push(`运行态指标加载失败：${errorText(metricsResult.reason)}`)
  }

  if (rateLimitResult.status === 'fulfilled') {
    rateLimits.value = rateLimitResult.value || []
  } else {
    rateLimits.value = []
    failures.push(`限流状态加载失败：${errorText(rateLimitResult.reason)}`)
  }

  if (rulesResult.status === 'fulfilled') {
    alertRules.value = rulesResult.value || []
  } else {
    alertRules.value = []
    failures.push(`告警规则加载失败：${errorText(rulesResult.reason)}`)
  }

  errorMessage.value = failures.join('；')
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.metric-label { color: var(--ob-text-secondary); font-size: 12px; }
.metric-value { margin-top: 6px; font-size: 22px; font-weight: 600; }
.dep-header { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; }
.dep-meta { margin-top: 8px; color: var(--ob-text-secondary); font-size: 12px; }
</style>
