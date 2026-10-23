<template>
  <PageContainer title="成本分析" description="按模型/提供商/用户维度的成本拆解（OpenLLM 成本指标）" test-id="costs-page">
    <div class="page-toolbar">
      <el-radio-group v-model="dimension" data-test="cost-dimension" @change="renderChart">
        <el-radio-button value="model">模型</el-radio-button>
        <el-radio-button value="provider">提供商</el-radio-button>
        <el-radio-button value="user">用户</el-radio-button>
      </el-radio-group>
      <el-select v-model="timeRange" style="width: 140px" data-test="cost-range" @change="loadCost">
        <el-option v-for="range in TIME_RANGES" :key="range.value" :label="range.label" :value="range.value" />
      </el-select>
      <el-button data-test="cost-refresh" :loading="loading" @click="loadAll">刷新</el-button>
      <el-button type="primary" data-test="create-budget" @click="openCreateBudget">创建预算</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="costs-error"
      @close="errorMessage = ''"
    />

    <el-card header="成本分布" class="mb-16" data-test="cost-chart-card">
      <div v-loading="loading">
        <el-empty v-if="pieData.length === 0" description="该维度暂无成本数据" :image-size="80" data-test="cost-chart-empty" />
        <div v-else ref="chartRef" class="chart" data-test="cost-chart" />
      </div>
    </el-card>

    <el-card header="预算列表" class="mb-16" data-test="budget-table-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="budgets" stripe data-test="budgets-table">
          <template #empty>
            <el-empty description="暂无预算，点击右上角创建" :image-size="60" data-test="budgets-empty" />
          </template>
          <el-table-column prop="name" label="预算名" min-width="150" />
          <el-table-column label="范围" width="100">
            <template #default="{ row }">{{ scopeLabel(row.scope) }}</template>
          </el-table-column>
          <el-table-column label="周期" width="90">
            <template #default="{ row }">{{ periodLabel(row.period) }}</template>
          </el-table-column>
          <el-table-column label="额度($)" width="110">
            <template #default="{ row }">{{ formatAmount(row.limit_usd) }}</template>
          </el-table-column>
          <el-table-column label="已用($)" width="110">
            <template #default="{ row }">{{ formatAmount(row.current_usage_usd) }}</template>
          </el-table-column>
          <el-table-column label="进度" min-width="200">
            <template #default="{ row }">
              <el-progress
                :percentage="progressPercent(row)"
                :status="row.is_exceeded ? 'exception' : undefined"
                data-test="budget-progress"
              />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_exceeded ? 'danger' : row.enabled ? 'success' : 'info'" size="small">
                {{ row.is_exceeded ? '已超限' : row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card header="优化建议" data-test="optimization-card">
      <el-empty
        v-if="suggestions.length === 0"
        description="暂无优化建议"
        :image-size="60"
        data-test="suggestions-empty"
      />
      <div v-else class="suggestion-list">
        <el-card
          v-for="(suggestion, index) in suggestions"
          :key="`${suggestion.type}-${index}`"
          shadow="never"
          class="suggestion-item"
          data-test="suggestion-item"
        >
          <div class="suggestion-body">
            <div class="suggestion-title">
              {{ suggestion.title }}
              <el-tag size="small" :type="severityType(suggestion.severity)">
                {{ severityLabel(suggestion.severity) }}
              </el-tag>
              <el-tag v-if="suggestion.potential_savings" size="small" type="success" class="saving-tag">
                预计节省 {{ suggestion.potential_savings }}
              </el-tag>
            </div>
            <div class="text-muted">{{ suggestion.description }}</div>
            <div class="suggestion-advice">建议：{{ suggestion.recommendation }}</div>
          </div>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="budgetDialogVisible" title="创建预算" width="520px" data-test="create-budget-dialog">
      <el-form label-width="110px">
        <el-form-item label="预算名" required>
          <el-input v-model="budgetForm.name" placeholder="如：AI 研发月度预算" data-test="budget-name-input" />
        </el-form-item>
        <el-form-item label="周期" required>
          <el-select v-model="budgetForm.period" style="width: 100%" data-test="budget-period-select">
            <el-option label="月度" value="monthly" />
            <el-option label="季度" value="quarterly" />
            <el-option label="年度" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item label="额度($)" required>
          <el-input-number
            v-model="budgetForm.limit_usd"
            :min="1"
            :step="100"
            style="width: 100%"
            data-test="budget-limit-input"
          />
        </el-form-item>
        <el-form-item label="告警阈值">
          <el-input-number
            v-model="budgetForm.alert_threshold"
            :min="1"
            :max="100"
            :step="5"
            style="width: 100%"
            data-test="budget-threshold-input"
          />
          <div class="text-muted">已用额度达到该百分比时触发 warning 告警</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="budgetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="save-budget" @click="saveBudget">创建</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import {
  budgetsApi,
  monitoringApi,
  type LlmBudget,
  type LlmCostAnalysis,
  type LlmOptimizationSuggestion,
} from '@/core/api/governance'

/**
 * 成本分析（v1.9.4 R4 真实化）：数据源 = OpenLLM `/api/v1/monitoring/costs`
 * 与 `/api/v1/budgets`，经 OpenBase 通用代理聚合（双通道鉴权）。
 * 原「一键应用优化建议」为前端假动作（上游无应用端点），本轮移除，仅展示建议内容。
 */
const TIME_RANGES = [
  { value: '1h', label: '1 小时' },
  { value: '6h', label: '6 小时' },
  { value: '24h', label: '24 小时' },
  { value: '7d', label: '7 天' },
  { value: '30d', label: '30 天' },
]

const dimension = ref('model')
const timeRange = ref('7d')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const costData = ref<LlmCostAnalysis | null>(null)
const budgets = ref<LlmBudget[]>([])
const suggestions = ref<LlmOptimizationSuggestion[]>([])

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const dimensionItems = computed(() => costData.value?.dimensions?.[dimension.value] ?? [])
const pieData = computed(() => dimensionItems.value.map((item) => ({ name: item.value, value: item.total_cost })))

const periodLabels: Record<string, string> = {
  daily: '日',
  weekly: '周',
  monthly: '月度',
  quarterly: '季度',
  yearly: '年度',
}
const scopeLabels: Record<string, string> = {
  global: '全局',
  team: '团队',
  project: '项目',
  workspace: '工作区',
  user: '用户',
  api_key: 'API Key',
}

function periodLabel(period: string) {
  return periodLabels[period] || period
}
function scopeLabel(scope: string) {
  return scopeLabels[scope] || scope
}
function formatAmount(amount: number) {
  return Number(amount ?? 0).toFixed(2)
}
function progressPercent(row: LlmBudget) {
  const percent = Number(row.usage_percentage ?? 0)
  return Math.max(0, Math.min(100, Math.round(percent)))
}
function severityType(severity: string) {
  return { critical: 'danger', high: 'danger', medium: 'warning', low: 'info' }[severity] || 'info'
}
function severityLabel(severity: string) {
  return { critical: '严重', high: '高', medium: '中', low: '低' }[severity] || severity
}

function renderChart() {
  if (!chartRef.value || pieData.value.length === 0) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ${c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll' },
    series: [
      {
        name: '成本分布',
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%' },
        data: pieData.value,
      },
    ],
  })
}

function handleResize() {
  chart?.resize()
}

async function loadCost() {
  try {
    // 一次取三个维度，切换维度时本地切换，避免重复请求
    costData.value = await monitoringApi.costs({
      dimension: ['model', 'provider', 'user'],
      time_range: timeRange.value,
    })
    await nextTick()
    renderChart()
  } catch (error) {
    errorMessage.value = `成本数据加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function loadBudgets() {
  try {
    const page = await budgetsApi.list({ page: 1, page_size: 100 })
    budgets.value = page.budgets
  } catch (error) {
    errorMessage.value = `预算列表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function loadSuggestions() {
  try {
    suggestions.value = await monitoringApi.optimizationSuggestions()
  } catch (error) {
    errorMessage.value = `优化建议加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function loadAll() {
  errorMessage.value = ''
  loading.value = true
  try {
    await Promise.all([loadCost(), loadBudgets(), loadSuggestions()])
  } finally {
    loading.value = false
  }
}

// ---------- 创建预算 ----------
const budgetDialogVisible = ref(false)
const budgetForm = reactive({
  name: '',
  period: 'monthly',
  limit_usd: 500,
  alert_threshold: 80,
})

function openCreateBudget() {
  errorMessage.value = ''
  budgetForm.name = ''
  budgetForm.period = 'monthly'
  budgetForm.limit_usd = 500
  budgetForm.alert_threshold = 80
  budgetDialogVisible.value = true
}

async function saveBudget() {
  if (!budgetForm.name.trim()) {
    ElMessage.warning('请输入预算名称')
    return
  }
  if (budgetForm.limit_usd <= 0) {
    errorMessage.value = '预算额度必须大于 0，请重新设置后再创建'
    return
  }
  saving.value = true
  try {
    await budgetsApi.create({
      name: budgetForm.name.trim(),
      scope: 'global',
      period: budgetForm.period,
      limit_usd: budgetForm.limit_usd,
      alert_thresholds: [{ type: 'warning', value: budgetForm.alert_threshold }],
    })
    budgetDialogVisible.value = false
    ElMessage.success('预算已创建')
    await loadBudgets()
  } catch (error) {
    errorMessage.value = `预算创建失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await loadAll()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.chart {
  height: 320px;
}
.text-muted {
  color: var(--ob-text-secondary);
}
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.suggestion-item {
  border: 1px solid var(--el-border-color-lighter);
}
.suggestion-body {
  min-width: 0;
}
.suggestion-title {
  font-weight: 600;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.suggestion-advice {
  margin-top: 6px;
  font-size: 13px;
}
.saving-tag {
  flex-shrink: 0;
}
</style>
