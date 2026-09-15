<template>
  <div>
    <div class="page-toolbar">
      <span class="page-title" data-test="admin-title">记忆维护</span>
      <span class="tab-hint">记忆管理后台：概览统计 + 运行监控（真实 OpenMemory 数据）+ 记忆维护操作</span>
    </div>
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="admin-error"
      @close="errorMsg = ''"
    />
    <div v-loading="loading">
      <el-tabs v-model="activeTab" data-test="admin-tabs" @tab-change="handleTabChange">
        <!-- 记忆概览：真实统计（按存储层级 memory_type：persistent/session/episode） -->
        <el-tab-pane label="记忆概览" name="overview">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="mb-16"
            title="记忆类型说明"
            description="OpenMemory 的 memory_type 表示存储层级（persistent 持久 / session 会话 / episode 情景），非内容模态；内容模态（文本/图像/音频）由写入时的 metadata.source 或标签区分。"
            data-test="admin-type-hint"
          />
          <el-row :gutter="16" class="mb-16">
            <el-col v-for="card in overviewCards" :key="card.label" :xs="12" :lg="6">
              <el-card class="metric-card" data-test="overview-card">
                <div class="metric-label">{{ card.label }}</div>
                <div class="metric-value" :style="card.danger ? 'color: var(--el-color-danger)' : ''">
                  {{ card.value }}<span class="metric-unit">{{ card.unit }}</span>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <el-card class="mb-16">
            <template #header>存储层级分布（memory_type）</template>
            <el-table :data="typeRows" stripe data-test="type-table" empty-text="暂无记忆数据">
              <el-table-column prop="type" label="存储层级" width="180" />
              <el-table-column label="数量" width="140">
                <template #default="{ row }">{{ row.count }}</template>
              </el-table-column>
              <el-table-column label="占比" min-width="220">
                <template #default="{ row }">
                  <el-progress :percentage="row.percent" :stroke-width="10" />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
          <el-card>
            <template #header>内容来源分布（metadata.source）</template>
            <el-table :data="sourceRows" stripe data-test="source-table" empty-text="暂无来源标记">
              <el-table-column prop="source" label="来源" width="200" />
              <el-table-column label="数量" width="140">
                <template #default="{ row }">{{ row.count }}</template>
              </el-table-column>
              <el-table-column label="说明" min-width="220">
                <template #default="{ row }">{{ row.desc }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <!-- 运行监控：真实 /monitor 数据 -->
        <el-tab-pane label="运行监控" name="monitor">
          <div class="page-toolbar">
            <el-select v-model="monitorRange" style="width: 120px" data-test="monitor-range" @change="loadMonitor">
              <el-option label="1 小时" value="1h" />
              <el-option label="6 小时" value="6h" />
              <el-option label="24 小时" value="24h" />
              <el-option label="7 天" value="7d" />
              <el-option label="30 天" value="30d" />
            </el-select>
            <el-button plain :loading="loading" data-test="monitor-refresh" @click="loadMonitor">刷新</el-button>
          </div>
          <el-row :gutter="16" class="mb-16">
            <el-col v-for="card in monitorCards" :key="card.label" :xs="12" :lg="6">
              <el-card class="metric-card" data-test="monitor-card">
                <div class="metric-label">{{ card.label }}</div>
                <div class="metric-value" :style="card.danger ? 'color: var(--el-color-danger)' : ''">
                  {{ card.value }}<span class="metric-unit">{{ card.unit }}</span>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :xs="24" :lg="12">
              <el-card class="mb-16">
                <template #header>状态码分布</template>
                <el-table :data="statusRows" stripe size="small" data-test="status-table">
                  <el-table-column prop="code" label="状态码" width="120" />
                  <el-table-column prop="count" label="数量" min-width="120" />
                </el-table>
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="12">
              <el-card>
                <template #header>高频端点</template>
                <el-table :data="endpointRows" stripe size="small" data-test="endpoint-table">
                  <el-table-column prop="endpoint" label="端点" min-width="180" show-overflow-tooltip />
                  <el-table-column prop="count" label="调用次数" width="110" />
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 记忆维护 -->
        <el-tab-pane label="记忆维护" name="maintain">
          <el-card class="mb-16">
            <template #header>批量清理</template>
            <el-form label-width="140px" @submit.prevent>
              <el-form-item label="按类型清理">
                <el-select v-model="cleanType" style="width: 200px" data-test="clean-type">
                  <el-option label="文本记忆" value="text" />
                  <el-option label="图像记忆" value="image" />
                  <el-option label="音频记忆" value="audio" />
                </el-select>
                <el-button type="danger" plain class="ml-12" :loading="cleaning" data-test="clean-run" @click="cleanByType">
                  清理该类型记忆
                </el-button>
                <span class="tab-hint">将对该类型记忆逐条执行 forget（软删除）</span>
              </el-form-item>
            </el-form>
          </el-card>
          <el-card>
            <template #header>当前记忆清单（按类型过滤）</template>
            <el-table :data="memories" stripe data-test="maintain-table" empty-text="暂无匹配记忆">
              <el-table-column label="记忆内容（摘要）" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">{{ row.content }}</template>
              </el-table-column>
              <el-table-column label="类型" width="100">
                <template #default="{ row }"><el-tag size="small">{{ row.memory_type }}</el-tag></template>
              </el-table-column>
              <el-table-column label="标签" min-width="120">
                <template #default="{ row }">
                  <el-tag v-for="t in row.tags" :key="t" size="small" type="info" class="mr-4">{{ t }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-popconfirm title="确认删除该记忆？" @confirm="removeOne(row.memory_id)">
                    <template #reference>
                      <el-button link type="danger" data-test="maintain-delete">删除</el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!loading && memories.length === 0" description="暂无匹配的记忆" :image-size="60" />
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface MemoryRow {
  memory_id: string
  content: string
  memory_type: string
  tags: string[]
}

interface MemoryListData {
  items: MemoryRow[]
  total: number
}

interface MonitorData {
  range: string
  total_requests: number
  error_count: number
  error_rate: number
  avg_latency_ms: number
  p95_latency_ms: number
  requests_per_minute: number
  status_distribution: Record<string, number>
  top_endpoints: Array<{ endpoint: string; count: number }>
}

const activeTab = ref('overview')
const loading = ref(false)
const cleaning = ref(false)
const errorMsg = ref('')

const memories = ref<MemoryRow[]>([])
const monitor = ref<MonitorData | null>(null)
const monitorRange = ref('24h')
const cleanType = ref('text')

// 概览统计（从真实列表计算，按存储层级 memory_type + 内容来源 source）
const overviewCards = computed(() => {
  const total = memories.value.length
  const layers = new Map<string, number>()
  for (const m of memories.value) {
    layers.set(m.memory_type, (layers.get(m.memory_type) || 0) + 1)
  }
  return [
    { label: '记忆总数', value: total.toLocaleString(), unit: ' 条', danger: false },
    { label: '持久记忆', value: String(layers.get('persistent') || 0), unit: ' 条', danger: false },
    { label: '会话记忆', value: String(layers.get('session') || 0), unit: ' 条', danger: false },
    { label: '情景记忆', value: String(layers.get('episode') || 0), unit: ' 条', danger: false },
  ]
})

const typeRows = computed(() => {
  const layers = new Map<string, number>()
  for (const m of memories.value) {
    layers.set(m.memory_type, (layers.get(m.memory_type) || 0) + 1)
  }
  const total = memories.value.length || 1
  return [...layers.entries()].map(([type, count]) => ({
    type,
    count,
    percent: Math.round((count / total) * 100),
  }))
})

// 内容来源分布：metadata.source（text/image/audio/audio_transcription 等）
const SOURCE_DESC: Record<string, string> = {
  text: '文本记忆（常规 remember）',
  image: '图像记忆（memories/image 上传）',
  audio: '音频记忆（audio/transcribe 转写）',
  audio_transcription: '语音记忆（remember-with-audio）',
  mobile: '移动端写入',
  web: 'Web 端写入',
  default: '未标记来源',
}

const sourceRows = computed(() => {
  const sources = new Map<string, number>()
  for (const m of memories.value) {
    const src = (m as unknown as { metadata?: { source?: string } })?.metadata?.source || 'default'
    sources.set(src, (sources.get(src) || 0) + 1)
  }
  return [...sources.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([source, count]) => ({
      source: source === 'default' ? '（未标记）' : source,
      count,
      desc: SOURCE_DESC[source] || '其他来源',
    }))
})

// 监控卡片（真实 monitor 数据）
const monitorCards = computed(() => {
  const m = monitor.value
  return [
    { label: '请求总数', value: (m?.total_requests ?? 0).toLocaleString(), unit: ' 次', danger: false },
    { label: '错误率', value: ((m?.error_rate ?? 0) * 100).toFixed(1), unit: ' %', danger: (m?.error_rate ?? 0) > 0.01 },
    { label: '平均延迟', value: String(Math.round(m?.avg_latency_ms ?? 0)), unit: ' ms', danger: false },
    { label: 'P95 延迟', value: String(Math.round(m?.p95_latency_ms ?? 0)), unit: ' ms', danger: (m?.p95_latency_ms ?? 0) > 1000 },
  ]
})

const statusRows = computed(() =>
  Object.entries(monitor.value?.status_distribution || {}).map(([code, count]) => ({ code, count })),
)

const endpointRows = computed(() => monitor.value?.top_endpoints || [])

async function loadMemories() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: MemoryListData }>(
      '/memory-proxy/memories',
      { params: { page: 1, page_size: 100 } },
    )
    memories.value = data.data?.items || []
  } catch (e) {
    memories.value = []
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '记忆列表加载失败'
  } finally {
    loading.value = false
  }
}

async function loadMonitor() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: MonitorData }>(
      '/memory-proxy/monitor',
      { params: { range: monitorRange.value } },
    )
    monitor.value = data.data || null
  } catch (e) {
    monitor.value = null
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '监控数据加载失败'
  } finally {
    loading.value = false
  }
}

async function removeOne(memoryId: string) {
  try {
    const { data } = await http.post<{ code: number; message: string }>('/memory-proxy/forget', {
      memory_id: memoryId,
      user_id: '',
    })
    if (data.code === 0) {
      ElMessage.success('记忆已删除')
      await loadMemories()
    } else {
      ElMessage.error(data.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error((e as { response?: { data?: { message?: string } } })?.response?.data?.message || '删除失败')
  }
}

async function cleanByType() {
  const targets = memories.value.filter((m) => m.memory_type === cleanType.value)
  if (targets.length === 0) {
    ElMessage.info('该类型暂无记忆')
    return
  }
  cleaning.value = true
  try {
    let ok = 0
    for (const m of targets) {
      try {
        const { data } = await http.post<{ code: number; message: string }>('/memory-proxy/forget', {
          memory_id: m.memory_id,
          user_id: '',
        })
        if (data.code === 0) ok += 1
      } catch {
        // 单条失败继续
      }
    }
    ElMessage.success(`已清理 ${ok}/${targets.length} 条 ${cleanType.value} 记忆`)
    await loadMemories()
  } finally {
    cleaning.value = false
  }
}

function handleTabChange(name: string | number) {
  if (name === 'monitor') loadMonitor()
  if (name === 'maintain' || name === 'overview') loadMemories()
}

onMounted(() => {
  loadMemories()
  loadMonitor()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.page-title { font-size: 16px; font-weight: 600; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.mr-4 { margin-right: 4px; }
.ml-12 { margin-left: 12px; }
.metric-card { text-align: center; }
.metric-label { color: var(--ob-text-secondary); font-size: 13px; }
.metric-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.metric-unit { font-size: 13px; font-weight: 400; color: var(--ob-text-secondary); margin-left: 2px; }
</style>
