<template>
  <div>
    <div class="page-toolbar">
      <span class="page-title" data-test="admin-title">系统管理</span>
      <span class="tab-hint">TD-13-31 管理后台</span>
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
        <el-tab-pane label="存储设置" name="storage">
          <el-card class="mb-16">
            <template #header>存储引擎</template>
            <el-form label-width="110px">
              <el-form-item label="当前引擎">
                <el-select v-model="storageEngine" style="width: 260px" data-test="storage-engine">
                  <el-option label="向量库（Milvus）" value="向量库" />
                  <el-option label="关系库（PostgreSQL）" value="关系库" />
                </el-select>
              </el-form-item>
            </el-form>
            <el-empty v-if="!loading && !storageStats" description="暂无该引擎的存储数据" data-test="storage-empty" />
            <template v-else>
              <div class="storage-info">
                <span class="storage-label">已用容量</span>
                <el-progress
                  :percentage="storageStats?.used ?? 0"
                  :status="(storageStats?.used ?? 0) >= 90 ? 'exception' : undefined"
                  data-test="storage-progress"
                />
                <div class="storage-detail" data-test="storage-detail">
                  共 {{ storageStats?.total }} · {{ storageStats?.detail }}
                </div>
              </div>
              <el-popconfirm title="确认清理该引擎的过期数据？该操作不可撤销" @confirm="clearStorage">
                <template #reference>
                  <el-button type="danger" plain data-test="clear-storage">清理过期数据</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-card>
          <el-card>
            <template #header>容量概览</template>
            <el-table :data="engineRows" data-test="engine-table" empty-text="暂无引擎数据">
              <el-table-column prop="engine" label="引擎" width="180" />
              <el-table-column label="容量使用" min-width="220">
                <template #default="{ row }">
                  <el-progress :percentage="row.used" :color="row.used >= 90 ? '#f56c6c' : undefined" />
                </template>
              </el-table-column>
              <el-table-column prop="detail" label="统计" min-width="200" />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-popconfirm title="确认清理该引擎的过期数据？" @confirm="clearEngine(row)">
                    <template #reference><el-button link type="danger" data-test="clear-engine">清理</el-button></template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="运行监控" name="monitor">
          <el-row :gutter="16">
            <el-col v-for="card in metricCards" :key="card.label" :xs="12" :lg="6">
              <el-card class="metric-card" data-test="metric-card">
                <div class="metric-label">{{ card.label }}</div>
                <div class="metric-value" :style="card.danger ? 'color: var(--el-color-danger)' : ''">
                  {{ card.value }}<span class="metric-unit">{{ card.unit }}</span>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <el-card class="mt-16" header="实时监控曲线（QPS / 内存 / 延迟）" data-test="monitor-chart">
            <div ref="chartRef" class="chart" />
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="配置管理" name="config">
          <el-card class="config-card">
            <template #header>记忆配置</template>
            <el-form label-width="170px" data-test="config-form">
              <el-form-item label="默认记忆保留天数" required>
                <el-input-number v-model="config.retentionDays" :min="1" :max="3650" data-test="retention-days" />
                <span class="form-unit">天</span>
              </el-form-item>
              <el-form-item label="最大记忆条数" required>
                <el-input-number v-model="config.maxMemories" :min="1" :max="100000" :step="100" data-test="max-memories" />
                <span class="form-unit">条</span>
              </el-form-item>
              <el-form-item label="相似度阈值">
                <div class="slider-wrap">
                  <el-slider
                    v-model="config.similarityThreshold"
                    :min="0.5"
                    :max="0.95"
                    :step="0.01"
                    :format-tooltip="(value: number) => value.toFixed(2)"
                    data-test="similarity-threshold"
                  />
                  <span class="slider-value">{{ config.similarityThreshold.toFixed(2) }}</span>
                </div>
                <div class="slider-desc">写入记忆时用于判定是否与已有记忆合并的相似度下限</div>
              </el-form-item>
            </el-form>
            <div class="config-actions">
              <el-button data-test="reset-config" @click="resetConfig">恢复默认</el-button>
              <el-button type="primary" data-test="save-config" @click="saveConfig">保存配置</el-button>
            </div>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

interface StorageStats {
  used: number
  total: string
  detail: string
}

const activeTab = ref('monitor')
const loading = ref(true)
const errorMsg = ref('')

// TD-13-31 管理后台：存储设置
const storageEngine = ref('向量库')
const storageData: Record<string, StorageStats> = {
  向量库: { used: 68, total: '120 GB', detail: '向量条数 8,420,000 · 索引分片 12' },
  关系库: { used: 42, total: '80 GB', detail: '关系条数 1,280,000 · 数据表 96 张' },
}

const storageStats = computed<StorageStats | undefined>(() => storageData[storageEngine.value])

const engineRows = computed(() =>
  Object.entries(storageData).map(([engine, stats]) => ({ engine, ...stats })),
)

function clearStorage() {
  const stats = storageStats.value
  const freed = stats ? Math.round(stats.used * 0.18) : 0
  ElMessage.success(`「${storageEngine.value}」清理任务已提交，预计释放约 ${freed} GB 空间`)
}

function clearEngine(row: { engine: string }) {
  ElMessage.success(`「${row.engine}」清理任务已提交`)
}

// TD-13-31 管理后台：运行监控
const metricCards = ref([
  { label: '当前 QPS', value: '1,286', unit: ' req/s', danger: false },
  { label: '内存占用', value: '2.4', unit: ' GB', danger: true },
  { label: 'P95 延迟', value: '186', unit: ' ms', danger: false },
  { label: '存储 IO', value: '68', unit: ' %', danger: false },
])

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const chartData = {
  x: ['10:00', '10:10', '10:20', '10:30', '10:40', '10:50', '11:00', '11:10', '11:20', '11:30', '11:40', '11:50', '12:00'],
  qps: [820, 940, 1105, 980, 1286, 1210, 1350, 1180, 1245, 1390, 1310, 1420, 1286],
  memory: [1.8, 1.9, 2.0, 1.9, 2.1, 2.2, 2.3, 2.2, 2.3, 2.4, 2.3, 2.4, 2.4],
  latency: [120, 145, 168, 152, 186, 175, 205, 178, 190, 210, 195, 220, 186],
}

function renderChart() {
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['QPS', '内存(GB)', '延迟(ms)'], top: 0 },
    grid: { left: 56, right: 24, top: 44, bottom: 30 },
    xAxis: { type: 'category', boundaryGap: false, data: chartData.x },
    yAxis: [
      { type: 'value', name: 'QPS' },
      { type: 'value', name: '内存/延迟' },
    ],
    series: [
      { name: 'QPS', type: 'line', smooth: true, yAxisIndex: 0, data: chartData.qps, areaStyle: { opacity: 0.12 } },
      { name: '内存(GB)', type: 'line', smooth: true, yAxisIndex: 1, data: chartData.memory },
      { name: '延迟(ms)', type: 'line', smooth: true, yAxisIndex: 1, data: chartData.latency },
    ],
  })
}

function handleResize() {
  chart?.resize()
}

function handleTabChange(name: string | number) {
  if (name === 'monitor') {
    window.setTimeout(() => {
      renderChart()
      chart?.resize()
    }, 50)
  }
}

// TD-13-31 管理后台：配置管理
const DEFAULT_CONFIG = { retentionDays: 30, maxMemories: 500, similarityThreshold: 0.72 }
const config = reactive({ ...DEFAULT_CONFIG })

function resetConfig() {
  Object.assign(config, DEFAULT_CONFIG)
  ElMessage.info('已恢复默认配置')
}

function saveConfig() {
  if (config.retentionDays < 1 || config.maxMemories < 1) {
    errorMsg.value = '保留天数与最大记忆条数必须为不小于 1 的正整数'
    return
  }
  errorMsg.value = ''
  ElMessage.success('配置已保存，将于 30 秒后生效')
}

onMounted(() => {
  // 模拟拉取管理数据
  window.setTimeout(() => {
    loading.value = false
    renderChart()
  }, 500)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.page-title { font-size: 16px; font-weight: 600; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.storage-info { margin-bottom: 16px; }
.storage-label { display: block; color: var(--ob-text-secondary); font-size: 13px; margin-bottom: 6px; }
.storage-detail { color: var(--ob-text-secondary); font-size: 13px; margin-top: 6px; }
.metric-card { text-align: center; }
.metric-label { color: var(--ob-text-secondary); font-size: 13px; }
.metric-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.metric-unit { font-size: 13px; font-weight: 400; color: var(--ob-text-secondary); margin-left: 2px; }
.mt-16 { margin-top: 16px; }
.chart { height: 320px; }
.config-card { max-width: 720px; }
.form-unit { margin-left: 8px; color: var(--ob-text-secondary); font-size: 13px; }
.slider-wrap { display: flex; align-items: center; gap: 12px; width: 100%; }
.slider-wrap .el-slider { flex: 1; }
.slider-value { color: var(--ob-text-secondary); font-size: 13px; min-width: 40px; text-align: right; }
.slider-desc { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.config-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 8px; }
</style>
