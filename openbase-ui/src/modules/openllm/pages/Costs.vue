<template>
  <div>
    <div class="page-toolbar">
      <el-radio-group v-model="dimension" data-test="cost-dimension" @change="handleDimensionChange">
        <el-radio-button value="model">模型</el-radio-button>
        <el-radio-button value="provider">提供商</el-radio-button>
        <el-radio-button value="tenant">租户</el-radio-button>
      </el-radio-group>
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
          <el-table-column label="周期" width="100">
            <template #default="{ row }">{{ periodLabel(row.period) }}</template>
          </el-table-column>
          <el-table-column label="额度" width="120">
            <template #default="{ row }">${{ row.limit_amount }}</template>
          </el-table-column>
          <el-table-column label="已用" width="120">
            <template #default="{ row }">${{ row.used_amount }}</template>
          </el-table-column>
          <el-table-column label="进度" min-width="200">
            <template #default="{ row }">
              <el-progress :percentage="usagePercent(row)" :status="usageStatus(row)" data-test="budget-progress" />
            </template>
          </el-table-column>
          <el-table-column label="告警阈值" width="110">
            <template #default="{ row }">{{ row.alert_threshold }}%</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card header="优化建议" data-test="optimization-card">
      <el-empty v-if="suggestions.length === 0" description="暂无优化建议" :image-size="60" data-test="suggestions-empty" />
      <div v-else class="suggestion-list">
        <el-card
          v-for="suggestion in suggestions"
          :key="suggestion.id"
          shadow="never"
          class="suggestion-item"
          data-test="suggestion-item"
        >
          <div class="suggestion-body">
            <div class="suggestion-title">
              {{ suggestion.title }}
              <el-tag size="small" type="success" class="saving-tag">预计节省 {{ suggestion.saving }}</el-tag>
            </div>
            <div class="text-muted">{{ suggestion.detail }}</div>
          </div>
          <el-button
            type="primary"
            size="small"
            :disabled="suggestion.applied"
            data-test="apply-suggestion"
            @click="applySuggestion(suggestion)"
          >
            {{ suggestion.applied ? '已应用' : '一键应用' }}
          </el-button>
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
          <el-input-number v-model="budgetForm.limit_amount" :min="1" :step="100" style="width: 100%" data-test="budget-limit-input" />
        </el-form-item>
        <el-form-item label="告警阈值">
          <el-input-number v-model="budgetForm.alert_threshold" :min="1" :max="100" :step="5" style="width: 100%" data-test="budget-threshold-input" />
          <div class="text-muted">已用额度达到该百分比时触发告警</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="budgetDialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="save-budget" @click="saveBudget">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

interface BudgetRow {
  id: number
  name: string
  period: string
  limit_amount: number
  used_amount: number
  alert_threshold: number
}

interface Suggestion {
  id: number
  title: string
  detail: string
  saving: string
  applied: boolean
}

const dimension = ref('model')
const loading = ref(true)
const errorMessage = ref('')

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const periodLabels: Record<string, string> = { monthly: '月度', quarterly: '季度', yearly: '年度' }
function periodLabel(period: string) {
  return periodLabels[period] || period
}

/** 契约 mock：各维度成本分布（单位 $，不调用真实 API） */
const dimensionData: Record<string, Array<{ name: string; value: number }>> = {
  model: [
    { name: 'gpt-4o', value: 426.5 },
    { name: 'gpt-4o-mini', value: 215.2 },
    { name: 'claude-3-5-sonnet', value: 188.6 },
    { name: 'qwen2.5-7b', value: 96.3 },
    { name: 'bge-m3', value: 45.8 },
  ],
  provider: [
    { name: 'OpenAI', value: 641.7 },
    { name: 'Anthropic', value: 188.6 },
    { name: '本地部署', value: 96.3 },
    { name: 'BAAI', value: 45.8 },
  ],
  tenant: [
    { name: '平台默认租户', value: 512.4 },
    { name: 'AI 研发组', value: 268.9 },
    { name: '数据分析组', value: 123.5 },
    { name: '市场运营组', value: 67.6 },
  ],
}

const pieData = computed(() => dimensionData[dimension.value] || [])

/** 契约 mock：本地预算数据（不调用真实 API） */
const budgets = ref<BudgetRow[]>([
  { id: 1, name: 'AI 研发月度预算', period: 'monthly', limit_amount: 800, used_amount: 642, alert_threshold: 80 },
  { id: 2, name: '生产环境季度预算', period: 'quarterly', limit_amount: 3000, used_amount: 1200, alert_threshold: 70 },
  { id: 3, name: '数据标注年度预算', period: 'yearly', limit_amount: 12000, used_amount: 4320, alert_threshold: 60 },
])

const suggestions = ref<Suggestion[]>([
  {
    id: 1,
    title: '低优先级任务切换至 gpt-4o-mini',
    detail: '将非关键链路的对话任务批量路由到 gpt-4o-mini，质量差异可忽略',
    saving: '18%',
    applied: false,
  },
  {
    id: 2,
    title: '启用对话级语义缓存',
    detail: '对重复提问启用语义缓存，可显著减少输入 Token 重复计费',
    saving: '22%',
    applied: false,
  },
  {
    id: 3,
    title: '缩容闲置本地模型 qwen2.5-7b',
    detail: '夜间调用量低于 5 rps 持续 30 天，建议缩容至 1 副本',
    saving: '12%',
    applied: false,
  },
  {
    id: 4,
    title: '收紧预算告警阈值',
    detail: 'AI 研发月度预算当前阈值 80% 过于宽松，建议收紧至 70% 提前介入',
    saving: '避免超支',
    applied: false,
  },
])

function usagePercent(row: BudgetRow) {
  if (row.limit_amount <= 0) return 0
  return Math.min(100, Math.round((row.used_amount / row.limit_amount) * 100))
}
function usageStatus(row: BudgetRow) {
  const percent = usagePercent(row)
  if (percent >= row.alert_threshold) return 'exception'
  if (percent >= 80) return 'warning'
  return 'success'
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

async function handleDimensionChange() {
  errorMessage.value = ''
  await nextTick()
  renderChart()
}

// ---------- 创建预算 ----------
const budgetDialogVisible = ref(false)
const budgetForm = reactive({
  name: '',
  period: 'monthly',
  limit_amount: 500,
  alert_threshold: 80,
})

function openCreateBudget() {
  errorMessage.value = ''
  budgetForm.name = ''
  budgetForm.period = 'monthly'
  budgetForm.limit_amount = 500
  budgetForm.alert_threshold = 80
  budgetDialogVisible.value = true
}

function saveBudget() {
  if (!budgetForm.name.trim()) {
    ElMessage.warning('请输入预算名称')
    return
  }
  if (budgetForm.limit_amount <= 0) {
    // 业务规则：额度必须为正数
    errorMessage.value = '预算额度必须大于 0，请重新设置后再创建'
    return
  }
  budgets.value.push({
    id: Date.now(),
    name: budgetForm.name.trim(),
    period: budgetForm.period,
    limit_amount: budgetForm.limit_amount,
    used_amount: 0,
    alert_threshold: budgetForm.alert_threshold,
  })
  budgetDialogVisible.value = false
  ElMessage.success('预算已创建')
}

function applySuggestion(suggestion: Suggestion) {
  suggestion.applied = true
  ElMessage.success(`已应用优化建议：${suggestion.title}`)
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(async () => {
  loading.value = true
  await mockDelay(600) // 契约 mock：模拟加载成本数据
  loading.value = false
  await nextTick()
  renderChart()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--el-border-color-lighter);
}
.suggestion-body {
  flex: 1;
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
.saving-tag {
  flex-shrink: 0;
}
</style>
